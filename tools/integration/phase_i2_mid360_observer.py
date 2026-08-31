#!/usr/bin/env python3
"""PHASE I2 observer: extend truthful PHASE I gates with native RTX 3D cloud evidence."""
from __future__ import annotations

import argparse
import json
import math
import os
import struct
from pathlib import Path

import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import PointCloud2

from phase_i_sensor_observer import Observer as PhaseIObserver, stamp


class Observer(PhaseIObserver):
    _FORMATS = {1: "b", 2: "B", 3: "h", 4: "H", 5: "i", 6: "I", 7: "f", 8: "d"}

    def __init__(self, evidence: Path, report: Path, config: Path, urdf: Path) -> None:
        self.cloud_count = 0
        self.cloud_frames = set()
        self.cloud_field_sets = []
        self.cloud_stamp_last = -1.0
        self.cloud_stamp_ok = True
        self.cloud_first_stamp = None
        self.cloud_total_points = 0
        self.cloud_finite_xyz = 0
        self.cloud_finite_intensity = 0
        self.cloud_time_finite = 0
        self.cloud_time_spans = []
        self.cloud_time_monotonic = True
        self.cloud_z_min = None
        self.cloud_z_max = None
        self.cloud_front_returns = 0
        self.cloud_left_returns = 0
        self.cloud_elevated_returns = 0
        self.cloud_points_while_rotate = 0
        self.cloud_points_while_straight = 0
        super().__init__(evidence, report, config, urdf)
        self.create_subscription(
            PointCloud2,
            self.config["pointcloud"]["topic"],
            self.on_cloud,
            qos_profile_sensor_data,
        )

    @classmethod
    def _read(cls, data: bytes, base: int, field, bigendian: bool):
        return struct.unpack_from(
            (">" if bigendian else "<") + cls._FORMATS[field.datatype], data, base + field.offset
        )[0]

    def on_cloud(self, msg: PointCloud2) -> None:
        value_stamp = stamp(msg.header.stamp)
        if value_stamp <= 0.0 or value_stamp + 1e-9 < self.cloud_stamp_last:
            self.cloud_stamp_ok = False
        self.cloud_stamp_last = value_stamp
        if self.cloud_first_stamp is None:
            self.cloud_first_stamp = value_stamp
        self.cloud_count += 1
        self.cloud_frames.add(msg.header.frame_id)
        fields = {field.name: field for field in msg.fields}
        self.cloud_field_sets.append(sorted(fields))
        required = ("x", "y", "z", "intensity", "time")
        if not all(name in fields for name in required):
            return
        times = []
        count = int(msg.width) * int(msg.height)
        self.cloud_total_points += count
        for index in range(count):
            base = index * msg.point_step
            try:
                x, y, z, intensity, point_time = (
                    float(self._read(msg.data, base, fields[name], msg.is_bigendian)) for name in required
                )
            except (KeyError, struct.error, ValueError):
                return
            if math.isfinite(point_time):
                self.cloud_time_finite += 1
                times.append(point_time)
            if math.isfinite(intensity):
                self.cloud_finite_intensity += 1
            if not all(math.isfinite(v) for v in (x, y, z)):
                continue
            self.cloud_finite_xyz += 1
            self.cloud_z_min = z if self.cloud_z_min is None else min(self.cloud_z_min, z)
            self.cloud_z_max = z if self.cloud_z_max is None else max(self.cloud_z_max, z)
            if 1.5 <= x <= 2.3 and abs(y) <= 0.6 and -0.6 <= z <= 0.6:
                self.cloud_front_returns += 1
            if abs(x) <= 0.7 and 2.1 <= y <= 2.9 and -0.6 <= z <= 0.6:
                self.cloud_left_returns += 1
            if 2.1 <= x <= 2.9 and -2.0 <= y <= -1.0 and 0.03 <= z <= 0.7:
                self.cloud_elevated_returns += 1
        if times:
            self.cloud_time_spans.append(max(times) - min(times))
            self.cloud_time_monotonic &= all(b + 1e-9 >= a for a, b in zip(times, times[1:]))
        if self.command_mode == "rotate":
            self.cloud_points_while_rotate += count
        elif self.command_mode == "straight":
            self.cloud_points_while_straight += count

    def build_report(self) -> dict:
        report = super().build_report()
        topics = dict(self.get_topic_names_and_types())
        cfg = self.config["pointcloud"]
        target = self.config["target_hardware_profile"]
        elapsed = max(0.0, self.cloud_stamp_last - (self.cloud_first_stamp or self.cloud_stamp_last))
        frame_rate = (self.cloud_count - 1) / elapsed if self.cloud_count > 1 and elapsed > 0 else 0.0
        point_rate = self.cloud_total_points / elapsed if elapsed > 0 else 0.0
        points_per_frame = self.cloud_total_points / self.cloud_count if self.cloud_count else 0.0
        fields = self.cloud_field_sets[-1] if self.cloud_field_sets else []
        required_fields = {"x", "y", "z", "intensity", "time"}
        fields_pass = required_fields.issubset(fields)
        finite_ratio = self.cloud_finite_xyz / self.cloud_total_points if self.cloud_total_points else 0.0
        z_span = (self.cloud_z_max - self.cloud_z_min) if self.cloud_z_min is not None else 0.0
        time_span = max(self.cloud_time_spans) if self.cloud_time_spans else 0.0
        expected_period = 1.0 / float(cfg["publish_rate_hz"])
        timing_pass = bool(
            self.cloud_time_finite > 0 and time_span > 1e-5
            and time_span <= expected_period * 1.5 and self.cloud_time_monotonic
        )
        obstacle_pass = bool(
            self.cloud_front_returns > 0 and self.cloud_left_returns > 0 and self.cloud_elevated_returns > 0
        )
        cloud_type_pass = topics.get(cfg["topic"]) == ["sensor_msgs/msg/PointCloud2"]
        cloud_pass = bool(
            self.cloud_count > 0 and cloud_type_pass and self.cloud_frames == {cfg["frame"]}
            and self.cloud_stamp_ok and fields_pass and finite_ratio > 0.9 and z_span > 0.1
            and timing_pass and obstacle_pass and self.cloud_points_while_rotate > 0
            and self.cloud_points_while_straight > 0
        )
        legacy_pass = bool(report["runtime_validation_all_pass"])
        report.update({
            "phase": "PHASE I2",
            "hardware_target": {"model": "Livox Mid-360"},
            "target_profile": target,
            "simulation_profile": {
                "RTX_model": cfg["isaac_config"],
                "scan_pattern": cfg["scan_pattern"],
                "actual_horizontal_fov": cfg["actual_horizontal_fov_deg"],
                "actual_vertical_fov": [cfg["actual_vertical_fov_min_deg"], cfg["actual_vertical_fov_max_deg"]],
                "actual_frame_rate": frame_rate,
                "actual_point_rate": point_rate,
                "range": [cfg["range_min_m"], cfg["range_max_m"]],
            },
            "fidelity_class": self.config["sensor_profile"]["fidelity"],
            "pointcloud": {
                "topic": cfg["topic"], "type": "sensor_msgs/msg/PointCloud2", "frame": cfg["frame"],
                "message_count": self.cloud_count, "fields": fields, "point_count": self.cloud_total_points,
                "finite_xyz_count": self.cloud_finite_xyz, "finite_xyz_ratio": finite_ratio,
                "finite_intensity_count": self.cloud_finite_intensity, "points_per_frame": points_per_frame,
                "actual_points_per_second": point_rate, "actual_frames_per_second": frame_rate,
                "point_time_field": cfg["point_time_field"], "point_time_unit": cfg["point_time_unit"],
                "point_time_source": cfg["point_time_source"], "point_time_span": time_span,
                "point_time_monotonic": self.cloud_time_monotonic, "timestamp_pass": self.cloud_stamp_ok,
                "z_min": self.cloud_z_min, "z_max": self.cloud_z_max, "z_span": z_span,
                "front_return_count": self.cloud_front_returns, "left_return_count": self.cloud_left_returns,
                "elevated_return_count": self.cloud_elevated_returns, "obstacle_pass": obstacle_pass,
                "points_while_rotate": self.cloud_points_while_rotate,
                "points_while_straight": self.cloud_points_while_straight,
                "fields_pass": fields_pass, "timing_pass": timing_pass, "pass": cloud_pass,
            },
            "imu_i2": {
                "topic": self.config["imu"]["topic"], "frame": self.config["imu"]["frame"],
                "target_rate": target["imu_rate_hz"],
                "actual_rate": report["imu"]["message_count"] / elapsed if elapsed > 0 else 0.0,
                "raw_scale": f"metersPerUnit^2={0.001 ** 2:g}", "ros_unit": "m/s^2",
                "acceleration_semantics": self.config["imu"]["acceleration_semantics"],
                "stationary_pass": report["imu"]["stationary_pass"],
                "rotate_pass": report["imu"]["rotate_pass"], "straight_pass": report["imu"]["straight_pass"],
            },
            "extrinsics": {
                "base_to_lidar_source": "diagnostic placeholder; NOT HARDWARE CALIBRATED",
                "base_to_lidar_confidence": self.config["lidar"]["pose_confidence"],
                "lidar_to_imu_source": self.config["mid360_internal_extrinsic"]["source"],
                "lidar_to_imu_translation": self.config["mid360_internal_extrinsic"]["translation_m"],
                "lidar_to_imu_rotation": self.config["mid360_internal_extrinsic"]["rotation_rpy_rad"],
                "axis_transform": self.config["mid360_internal_extrinsic"]["axis_transform"],
                "point_lio_extrinsic_T_m": self.config["mid360_internal_extrinsic"]["point_lio_extrinsic_T_m"],
            },
            "legacy_phase_i_regression_pass": legacy_pass,
            "point_lio_sim_input_contract": {
                "lidar_topic": cfg["topic"], "message_type": "sensor_msgs/msg/PointCloud2",
                "required_fields": ["x", "y", "z", "intensity", "time"],
                "time_field": "time", "time_unit": "seconds", "point_lio_timestamp_unit": "SEC",
                "imu_topic": self.config["imu"]["topic"],
            },
        })
        report["runtime_validation_all_pass"] = bool(legacy_pass and cloud_pass)
        return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--urdf", type=Path, required=True)
    args = parser.parse_args()
    rclpy.init()
    node = Observer(*(p.resolve() for p in (args.evidence, args.report, args.config, args.urdf)))
    try:
        rclpy.spin(node)
    except rclpy.executors.ExternalShutdownException:
        pass
    finally:
        if rclpy.ok():
            node.write()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
