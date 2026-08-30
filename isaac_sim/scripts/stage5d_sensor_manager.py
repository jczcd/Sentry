"""Runtime-only PHASE I RTX LiDAR and physics IMU integration."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np


class Stage5DSensorManager:
    """Create diagnostic sensors/obstacles without saving the opened stage."""

    def __init__(
        self,
        articulation_path: str,
        config_path: Path,
        enable_legacy_scan: bool = True,
        show_lidar_debug: bool = False,
        pointcloud_rate_hz: float | None = None,
        diagnostic_environment: bool = False,
    ) -> None:
        import omni.usd
        import rclpy
        from isaacsim.core.simulation_manager import SimulationManager
        from isaacsim.sensors.experimental.physics import IMU, IMUSensor
        from isaacsim.sensors.experimental.rtx import Lidar, LidarSensor
        from pxr import Gf, UsdGeom
        from sensor_msgs.msg import Imu
        from rclpy.qos import qos_profile_sensor_data

        self.config = json.loads(config_path.read_text())
        self.simulation_manager = SimulationManager
        self.stage = omni.usd.get_context().get_stage()
        self.mpu = float(UsdGeom.GetStageMetersPerUnit(self.stage))
        self.articulation_path = articulation_path
        self.lidar_path = articulation_path + "/PhaseI_Lidar"
        self.pointcloud_lidar_path = articulation_path + "/PhaseI2_PointCloudLidar"
        self.imu_path = articulation_path + "/PhaseI_Imu"
        lidar_cfg = self.config["lidar"]
        pointcloud_cfg = self.config["pointcloud"]
        pointcloud_rate = float(pointcloud_rate_hz or pointcloud_cfg["publish_rate_hz"])
        imu_cfg = self.config["imu"]

        # Python transform APIs use stage units for local translations.
        lidar_translation = np.asarray([lidar_cfg["pose_xyz_m"]], dtype=float) / self.mpu
        imu_translation = np.asarray([imu_cfg["pose_xyz_m"]], dtype=float) / self.mpu
        self.lidar_sensor = None
        self.lidar_writer_name = "RtxLidarROS2PublishLaserScan"
        if enable_legacy_scan:
            self.lidar = Lidar.create(
                path=self.lidar_path,
                config=lidar_cfg["isaac_config"],
                tick_rate=float(lidar_cfg["publish_rate_hz"]),
                translations=lidar_translation,
                attributes={
                    "omni:sensor:Core:scanRateBaseHz": float(lidar_cfg["publish_rate_hz"]),
                    "omni:sensor:Core:nearRangeM": float(lidar_cfg["range_min_m"]),
                    "omni:sensor:Core:farRangeM": float(lidar_cfg["range_max_m"]),
                },
            )
            self.lidar_sensor = LidarSensor(self.lidar, annotators=[])
            self.lidar_sensor.attach_writer(
                self.lidar_writer_name,
                topicName=lidar_cfg["topic"],
                frameId=lidar_cfg["frame"],
                horizontalFov=float(lidar_cfg["horizontal_fov_deg"]),
                horizontalResolution=float(lidar_cfg["angular_resolution_deg"]),
                depthRange=[float(lidar_cfg["range_min_m"]), float(lidar_cfg["range_max_m"])],
                rotationRate=float(lidar_cfg["publish_rate_hz"]),
                azimuthRange=[-180.0, 180.0],
            )

        pointcloud_translation = np.asarray([pointcloud_cfg["pose_xyz_m"]], dtype=float) / self.mpu
        self.pointcloud_lidar = Lidar.create(
            path=self.pointcloud_lidar_path,
            config=pointcloud_cfg["isaac_config"],
            tick_rate=pointcloud_rate,
            translations=pointcloud_translation,
            aux_output_level="NONE",
            attributes={
                "omni:sensor:Core:scanRateBaseHz": pointcloud_rate,
                "omni:sensor:Core:nearRangeM": float(pointcloud_cfg["range_min_m"]),
                "omni:sensor:Core:farRangeM": float(pointcloud_cfg["range_max_m"]),
            },
        )
        self.pointcloud_sensor = LidarSensor(self.pointcloud_lidar, annotators=[])
        self.debug_writer_name = "draw-point-cloud"
        self.show_lidar_debug = show_lidar_debug
        if self.show_lidar_debug:
            self.pointcloud_sensor.attach_writer(self.debug_writer_name)

        self.imu_sensor = IMUSensor(
            IMU.create(
                self.imu_path,
                translations=imu_translation,
                linear_acceleration_filter_size=1,
                angular_velocity_filter_size=1,
                orientation_filter_size=1,
            )
        )
        if not rclpy.ok():
            rclpy.init()
        self.node = rclpy.create_node("isaac_stage5d_sensor_manager")
        from mid360_sim_adapter import Mid360SimAdapter
        self.pointcloud_adapter = Mid360SimAdapter(
            self.node,
            pointcloud_cfg["topic"],
            pointcloud_cfg["frame"],
            self.simulation_manager,
        )
        self.pointcloud_adapter.attach(self.pointcloud_sensor)
        self.imu_pub = self.node.create_publisher(Imu, imu_cfg["topic"], qos_profile_sensor_data)
        self.Imu = Imu
        self.imu_target_period = 1.0 / float(imu_cfg["publish_rate_hz"])
        self.last_imu_sensor_time = -1.0
        self.physics_step_count = 0
        self._physics_callback_id = None
        self.read_gravity = bool(imu_cfg["read_gravity"])
        self.imu_frame = imu_cfg["frame"]
        self._create_diagnostic_obstacles(Gf, UsdGeom)
        if diagnostic_environment:
            self._create_extended_environment(Gf, UsdGeom)

    def start_physics_sampling(self) -> None:
        """Publish each distinct backend IMU reading without changing physics dt."""
        from isaacsim.core.simulation_manager import IsaacEvents

        if self._physics_callback_id is None:
            self._physics_callback_id = self.simulation_manager.register_callback(
                self._on_physics_step,
                event=IsaacEvents.POST_PHYSICS_STEP,
            )

    def _create_diagnostic_obstacles(self, Gf, UsdGeom) -> None:
        cfg = self.config["diagnostic_obstacles"]
        base = UsdGeom.XformCache().GetLocalToWorldTransform(
            self.stage.GetPrimAtPath(self.articulation_path)
        )
        lidar_local = Gf.Vec3d(*[v / self.mpu for v in self.config["lidar"]["pose_xyz_m"]])
        lidar_world = base.Transform(lidar_local)
        for name, center_key, size_key in (
            ("FrontBox", "front_center_xyz_lidar_m", "front_size_xyz_m"),
            ("LeftBox", "left_center_xyz_lidar_m", "left_size_xyz_m"),
            ("ElevatedBox", "elevated_center_xyz_lidar_m", "elevated_size_xyz_m"),
        ):
            offset = Gf.Vec3d(*[v / self.mpu for v in cfg[center_key]])
            center = lidar_world + base.TransformDir(offset)
            size = [v / self.mpu for v in cfg[size_key]]
            cube = UsdGeom.Cube.Define(self.stage, "/PhaseI_Diagnostic/" + name)
            cube.CreateSizeAttr(1.0)
            xform = UsdGeom.Xformable(cube)
            xform.AddTranslateOp().Set(center)
            xform.AddScaleOp().Set(Gf.Vec3d(*size))
            cube.CreateDisplayColorAttr([(0.9, 0.15, 0.1)])

    def _create_extended_environment(self, Gf, UsdGeom) -> None:
        """Create an asymmetric runtime-only corridor for LIO and GUI checks."""
        base = UsdGeom.XformCache().GetLocalToWorldTransform(
            self.stage.GetPrimAtPath(self.articulation_path)
        )
        lidar_local = Gf.Vec3d(*[v / self.mpu for v in self.config["lidar"]["pose_xyz_m"]])
        lidar_world = base.Transform(lidar_local)
        geometry = (
            ("FrontWall", (5.0, 0.4, 0.6), (0.25, 6.0, 2.4)),
            ("LeftWall", (1.5, 3.2, 0.4), (7.0, 0.25, 2.0)),
            ("RightWallShort", (2.7, -2.4, 0.15), (3.0, 0.25, 1.5)),
            ("AsymmetricBox", (3.2, 1.1, -0.1), (0.8, 0.6, 1.4)),
            ("ElevatedBeam", (2.1, -1.2, 1.0), (1.2, 0.45, 0.35)),
        )
        for name, offset_m, size_m in geometry:
            center = lidar_world + base.TransformDir(
                Gf.Vec3d(*[value / self.mpu for value in offset_m])
            )
            cube = UsdGeom.Cube.Define(self.stage, "/PhaseJ_Diagnostic/" + name)
            cube.CreateSizeAttr(1.0)
            xform = UsdGeom.Xformable(cube)
            xform.AddTranslateOp().Set(center)
            xform.AddScaleOp().Set(Gf.Vec3d(*[value / self.mpu for value in size_m]))
            cube.CreateDisplayColorAttr([(0.15, 0.45, 0.9)])

    @staticmethod
    def _stamp(seconds: float):
        from builtin_interfaces.msg import Time
        stamp = Time()
        stamp.sec = int(seconds)
        stamp.nanosec = int((seconds - stamp.sec) * 1_000_000_000)
        return stamp

    def _on_physics_step(self, step_dt, context) -> None:
        self.physics_step_count += 1
        data = self.imu_sensor.get_data(read_gravity=self.read_gravity)
        sensor_time = float(data.get("time", 0.0))
        if sensor_time <= 0.0 or sensor_time <= self.last_imu_sensor_time + 1e-12:
            return
        values = np.concatenate(
            (data["linear_acceleration"], data["angular_velocity"], data["orientation"])
        )
        if not np.all(np.isfinite(values)):
            return
        self.last_imu_sensor_time = sensor_time
        msg = self.Imu()
        msg.header.stamp = self._stamp(sensor_time)
        msg.header.frame_id = self.imu_frame
        # Isaac 6.0.1 experimental IMU on this millimeter-composed stage returns
        # acceleration scaled by 1/metersPerUnit^2 (stationary support is
        # 9.81e6 at mpu=0.001). Convert the observed backend units to ROS SI.
        acc = np.asarray(data["linear_acceleration"], dtype=float) * (self.mpu ** 2)
        ang = data["angular_velocity"]
        quat = data["orientation"]  # Isaac experimental API: w, x, y, z.
        msg.linear_acceleration.x, msg.linear_acceleration.y, msg.linear_acceleration.z = map(float, acc)
        msg.angular_velocity.x, msg.angular_velocity.y, msg.angular_velocity.z = map(float, ang)
        msg.orientation.w = float(quat[0])
        msg.orientation.x = float(quat[1])
        msg.orientation.y = float(quat[2])
        msg.orientation.z = float(quat[3])
        msg.orientation_covariance = [0.0] * 9
        msg.angular_velocity_covariance = [0.0] * 9
        msg.linear_acceleration_covariance = [0.0] * 9
        self.imu_pub.publish(msg)

    def update(self) -> None:
        import rclpy

        rclpy.spin_once(self.node, timeout_sec=0.0)

    def close(self) -> None:
        if self._physics_callback_id is not None:
            self.simulation_manager.deregister_callback(self._physics_callback_id)
            self._physics_callback_id = None
        if self.show_lidar_debug:
            self.pointcloud_sensor.detach_writer(self.debug_writer_name)
        if self.lidar_sensor is not None:
            self.lidar_sensor.detach_writer(self.lidar_writer_name)
        self.node.destroy_node()
