"""Publish actual Stage5D PhysX state to ROS2 at a simulation-time cadence."""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np


class Stage5DStatePublisher:
    def __init__(self, robot, articulation_path: str, rate_hz: float = 50.0) -> None:
        import omni.usd
        import rclpy
        from nav_msgs.msg import Odometry
        from sensor_msgs.msg import JointState
        from tf2_msgs.msg import TFMessage
        from pxr import UsdGeom

        self.Odometry, self.JointState, self.TFMessage = Odometry, JointState, TFMessage
        self.robot = robot
        self.path = articulation_path
        self.period = 1.0 / rate_hz
        self.last_publish = -self.period
        from isaacsim.core.simulation_manager import SimulationManager
        self.simulation_manager = SimulationManager
        self.stage = omni.usd.get_context().get_stage()
        self.mpu = float(UsdGeom.GetStageMetersPerUnit(self.stage))
        self.initial = UsdGeom.XformCache().GetLocalToWorldTransform(self.stage.GetPrimAtPath(self.path))
        if not rclpy.ok():
            rclpy.init()
        self.node = rclpy.create_node("isaac_stage5d_state_publisher")
        self.odom_pub = self.node.create_publisher(Odometry, "/sentry/odom", 20)
        self.joint_pub = self.node.create_publisher(JointState, "/joint_states", 20)
        self.tf_pub = self.node.create_publisher(TFMessage, "/tf", 20)

    @staticmethod
    def _stamp(seconds: float):
        from builtin_interfaces.msg import Time
        stamp = Time()
        stamp.sec = int(seconds)
        stamp.nanosec = int((seconds - stamp.sec) * 1_000_000_000)
        return stamp

    def update(self) -> None:
        import omni.usd
        from geometry_msgs.msg import TransformStamped
        from pxr import Gf, UsdGeom

        now = float(self.simulation_manager.get_simulation_time())
        if now <= 0.0 or now - self.last_publish + 1e-9 < self.period:
            return
        self.last_publish = now
        matrix = UsdGeom.XformCache().GetLocalToWorldTransform(self.stage.GetPrimAtPath(self.path))
        relative = matrix * self.initial.GetInverse()
        p = relative.ExtractTranslation()
        quat = relative.ExtractRotationQuat()
        imag = quat.GetImaginary()
        stamp = self._stamp(now)

        odom = self.Odometry()
        odom.header.stamp = stamp
        odom.header.frame_id = "odom"
        odom.child_frame_id = "base_link"
        odom.pose.pose.position.x = float(p[0]) * self.mpu
        odom.pose.pose.position.y = float(p[1]) * self.mpu
        odom.pose.pose.position.z = float(p[2]) * self.mpu
        odom.pose.pose.orientation.x = float(imag[0])
        odom.pose.pose.orientation.y = float(imag[1])
        odom.pose.pose.orientation.z = float(imag[2])
        odom.pose.pose.orientation.w = float(quat.GetReal())
        linear_world = self.robot.get_linear_velocity()
        angular_world = self.robot.get_angular_velocity()
        world_to_body = matrix.GetInverse()
        linear_body = world_to_body.TransformDir(Gf.Vec3d(*[float(v) for v in linear_world]))
        angular_body = world_to_body.TransformDir(Gf.Vec3d(*[float(v) for v in angular_world]))
        odom.twist.twist.linear.x, odom.twist.twist.linear.y, odom.twist.twist.linear.z = map(float, linear_body)
        odom.twist.twist.angular.x, odom.twist.twist.angular.y, odom.twist.twist.angular.z = map(float, angular_body)
        self.odom_pub.publish(odom)

        transform = TransformStamped()
        transform.header = odom.header
        transform.child_frame_id = odom.child_frame_id
        transform.transform.translation.x = odom.pose.pose.position.x
        transform.transform.translation.y = odom.pose.pose.position.y
        transform.transform.translation.z = odom.pose.pose.position.z
        transform.transform.rotation = odom.pose.pose.orientation
        tf_message = self.TFMessage()
        tf_message.transforms = [transform]
        self.tf_pub.publish(tf_message)

        joint = self.JointState()
        joint.header.stamp = stamp
        joint.name = list(self.robot.dof_names)
        joint.position = np.asarray(self.robot.get_joint_positions(), dtype=float).tolist()
        joint.velocity = np.asarray(self.robot.get_joint_velocities(), dtype=float).tolist()
        joint.effort = []
        self.joint_pub.publish(joint)

    def close(self) -> None:
        self.node.destroy_node()
