#!/usr/bin/env python3
"""Collect real PHASE I ROS evidence and derive every sensor/TF gate."""
from __future__ import annotations

import argparse
import json
import math
import os
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy, qos_profile_sensor_data
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import Imu, LaserScan
from tf2_msgs.msg import TFMessage


def stamp(value) -> float:
    return value.sec + value.nanosec / 1e9


def yaw(q) -> float:
    return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))


def wrap(value: float) -> float:
    return (value + math.pi) % (2 * math.pi) - math.pi


def norm3(v) -> float:
    return math.sqrt(sum(float(x) ** 2 for x in v))


class Observer(Node):
    def __init__(self, evidence: Path, report: Path, config: Path, urdf: Path) -> None:
        super().__init__("phase_i_sensor_observer")
        self.evidence_path, self.report_path = evidence, report
        self.config = json.loads(config.read_text())
        self.urdf = ET.parse(urdf).getroot()
        self.counts = {"clock": 0, "scan": 0, "imu": 0, "odom": 0, "tf": 0, "tf_static": 0}
        self.last_stamp = {k: -1.0 for k in ("clock", "scan", "imu", "odom", "tf")}
        self.timestamp_ok = {k: True for k in self.last_stamp}
        self.frames = {"scan": set(), "imu": set()}
        self.scan_finite_count = 0
        self.scan_nonzero_finite_count = 0
        self.scan_valid_range_count = 0
        self.scan_front_samples = []
        self.scan_range_min = None
        self.scan_range_max = None
        self.imu_stationary_ang = []
        self.imu_stationary_acc = []
        self.imu_stationary_acc_vectors = []
        self.rotate_ang_z = []
        self.straight_acc_delta = []
        self.stationary_acc_reference = None
        self.latest_odom = None
        self.rotate_start = None
        self.rotate_delta_yaw = 0.0
        self.straight_start = None
        self.straight_dx = 0.0
        self.command_mode = "stationary"
        self.tf_edges = {}

        static_qos = QoSProfile(depth=10)
        static_qos.reliability = ReliabilityPolicy.RELIABLE
        static_qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
        self.create_subscription(Clock, "/clock", self.on_clock, 100)
        self.create_subscription(LaserScan, "/sentry/scan", self.on_scan, qos_profile_sensor_data)
        self.create_subscription(Imu, "/sentry/imu", self.on_imu, qos_profile_sensor_data)
        self.create_subscription(Odometry, "/sentry/odom", self.on_odom, 100)
        self.create_subscription(TFMessage, "/tf", lambda m: self.on_tf(m, False), 100)
        self.create_subscription(TFMessage, "/tf_static", lambda m: self.on_tf(m, True), static_qos)
        self.create_subscription(Twist, "/cmd_vel", self.on_cmd, 50)
        self.create_timer(0.2, self.write)

    def check_stamp(self, key: str, value: float) -> None:
        if value <= 0.0 or value + 1e-9 < self.last_stamp[key]:
            self.timestamp_ok[key] = False
        self.last_stamp[key] = value

    def on_clock(self, msg: Clock) -> None:
        self.counts["clock"] += 1
        self.check_stamp("clock", stamp(msg.clock))

    def on_scan(self, msg: LaserScan) -> None:
        self.counts["scan"] += 1
        self.check_stamp("scan", stamp(msg.header.stamp))
        self.frames["scan"].add(msg.header.frame_id)
        self.scan_range_min, self.scan_range_max = float(msg.range_min), float(msg.range_max)
        finite = [(i, float(v)) for i, v in enumerate(msg.ranges) if math.isfinite(v)]
        self.scan_finite_count += len(finite)
        self.scan_nonzero_finite_count += sum(v > 0.0 for _, v in finite)
        self.scan_valid_range_count += sum(msg.range_min <= v <= msg.range_max for _, v in finite)
        for index, value in finite:
            angle = msg.angle_min + index * msg.angle_increment
            if abs(wrap(angle)) <= math.radians(8.0) and msg.range_min <= value <= msg.range_max:
                self.scan_front_samples.append(value)

    def on_imu(self, msg: Imu) -> None:
        self.counts["imu"] += 1
        self.check_stamp("imu", stamp(msg.header.stamp))
        self.frames["imu"].add(msg.header.frame_id)
        ang = (msg.angular_velocity.x, msg.angular_velocity.y, msg.angular_velocity.z)
        acc = (msg.linear_acceleration.x, msg.linear_acceleration.y, msg.linear_acceleration.z)
        if not all(math.isfinite(v) for v in ang + acc):
            return
        if self.command_mode == "stationary":
            self.imu_stationary_ang.append(norm3(ang))
            self.imu_stationary_acc.append(norm3(acc))
            self.imu_stationary_acc_vectors.append(tuple(acc))
            if len(self.imu_stationary_acc_vectors) >= 20:
                samples = self.imu_stationary_acc_vectors[-50:]
                self.stationary_acc_reference = tuple(sum(v[i] for v in samples) / len(samples) for i in range(3))
        elif self.command_mode == "rotate":
            self.rotate_ang_z.append(float(ang[2]))
        elif self.command_mode == "straight" and self.stationary_acc_reference:
            self.straight_acc_delta.append(norm3(tuple(acc[i] - self.stationary_acc_reference[i] for i in range(3))))

    def on_odom(self, msg: Odometry) -> None:
        self.counts["odom"] += 1
        self.check_stamp("odom", stamp(msg.header.stamp))
        self.latest_odom = msg
        if self.command_mode == "rotate" and self.rotate_start is not None:
            self.rotate_delta_yaw = wrap(yaw(msg.pose.pose.orientation) - self.rotate_start)
        if self.command_mode == "straight" and self.straight_start is not None:
            self.straight_dx = msg.pose.pose.position.x - self.straight_start

    def on_tf(self, msg: TFMessage, is_static: bool) -> None:
        key = "tf_static" if is_static else "tf"
        self.counts[key] += len(msg.transforms)
        for transform in msg.transforms:
            if not is_static:
                self.check_stamp("tf", stamp(transform.header.stamp))
            edge = (transform.header.frame_id, transform.child_frame_id)
            self.tf_edges.setdefault(edge, set()).add(key)

    def on_cmd(self, msg: Twist) -> None:
        previous = self.command_mode
        if msg.angular.z > 0.1 and abs(msg.linear.x) < 0.02 and abs(msg.linear.y) < 0.02:
            self.command_mode = "rotate"
            if previous != "rotate" and self.latest_odom:
                self.rotate_start = yaw(self.latest_odom.pose.pose.orientation)
        elif msg.linear.x > 0.05 and abs(msg.linear.y) < 0.02 and abs(msg.angular.z) < 0.05:
            self.command_mode = "straight"
            if previous != "straight" and self.latest_odom:
                self.straight_start = self.latest_odom.pose.pose.position.x
        elif abs(msg.linear.x) < 1e-4 and abs(msg.linear.y) < 1e-4 and abs(msg.angular.z) < 1e-4:
            # Preserve completed dynamic measurements, but collect initial stationary data.
            if not self.rotate_ang_z and not self.straight_acc_delta:
                self.command_mode = "stationary"

    def tf_gate(self):
        parents = {}
        duplicate = False
        for parent, child in self.tf_edges:
            if child in parents and parents[child] != parent:
                duplicate = True
            parents[child] = parent
        cycle = False
        for start in parents:
            seen, node = set(), start
            while node in parents:
                if node in seen:
                    cycle = True
                    break
                seen.add(node)
                node = parents[node]
        reachable = {"odom"}
        changed = True
        while changed:
            changed = False
            for child, parent in parents.items():
                if parent in reachable and child not in reachable:
                    reachable.add(child)
                    changed = True
        lidar_static = "tf_static" in self.tf_edges.get(("base_link", "lidar_link"), set())
        imu_static = any(
            "tf_static" in self.tf_edges.get((parent, "imu_link"), set())
            for parent in ("base_link", "lidar_link")
        )
        return parents, cycle, duplicate, reachable, lidar_static, imu_static

    def build_report(self) -> dict:
        topics = dict(self.get_topic_names_and_types())
        lidar_cfg, imu_cfg = self.config["lidar"], self.config["imu"]
        obstacle = self.config["diagnostic_obstacles"]
        expected = float(obstacle["front_expected_surface_distance_m"])
        measured = min(self.scan_front_samples) if self.scan_front_samples else None
        error = abs(measured - expected) if measured is not None else None
        obstacle_pass = error is not None and error <= float(obstacle["obstacle_tolerance_m"])
        stationary_ang = max(self.imu_stationary_ang) if self.imu_stationary_ang else None
        stationary_acc = sum(self.imu_stationary_acc) / len(self.imu_stationary_acc) if self.imu_stationary_acc else None
        stationary_pass = bool(
            len(self.imu_stationary_ang) >= 10 and stationary_ang < 0.2
            and stationary_acc is not None and 7.0 <= stationary_acc <= 12.5
        )
        rotate_z = max(self.rotate_ang_z) if self.rotate_ang_z else None
        rotate_pass = bool(rotate_z is not None and rotate_z > 0.08 and self.rotate_delta_yaw > math.radians(5.0))
        straight_response = max(self.straight_acc_delta) if self.straight_acc_delta else None
        stationary_noise = None
        if self.stationary_acc_reference and self.imu_stationary_acc_vectors:
            stationary_noise = max(
                norm3(tuple(v[i] - self.stationary_acc_reference[i] for i in range(3)))
                for v in self.imu_stationary_acc_vectors[-100:]
            )
        straight_threshold = max(0.001, 2.0 * stationary_noise) if stationary_noise is not None else None
        straight_pass = bool(
            straight_response is not None and straight_threshold is not None
            and straight_response > straight_threshold and self.straight_dx > 0.03
        )
        parents, cycle, duplicate, reachable, lidar_static, imu_static = self.tf_gate()
        links = [link.attrib["name"] for link in self.urdf.findall("link")]
        movable = [joint.attrib["name"] for joint in self.urdf.findall("joint") if joint.attrib.get("type") != "fixed"]
        fixed = [joint.attrib["name"] for joint in self.urdf.findall("joint") if joint.attrib.get("type") == "fixed"]
        type_pass = {
            "clock": topics.get("/clock") == ["rosgraph_msgs/msg/Clock"],
            "scan": topics.get("/sentry/scan") == ["sensor_msgs/msg/LaserScan"],
            "imu": topics.get("/sentry/imu") == ["sensor_msgs/msg/Imu"],
            "odom": topics.get("/sentry/odom") == ["nav_msgs/msg/Odometry"],
            "tf": topics.get("/tf") == ["tf2_msgs/msg/TFMessage"],
            "tf_static": topics.get("/tf_static") == ["tf2_msgs/msg/TFMessage"],
        }
        timestamps_valid = all(self.timestamp_ok.values()) and all(self.last_stamp[k] > 0 for k in self.last_stamp)
        scan_pass = bool(
            self.counts["scan"] > 0 and type_pass["scan"] and self.frames["scan"] == {lidar_cfg["frame"]}
            and self.scan_finite_count > 0 and self.scan_nonzero_finite_count > 0
            and self.scan_valid_range_count > 0 and self.timestamp_ok["scan"] and obstacle_pass
        )
        imu_pass = bool(
            self.counts["imu"] > 0 and type_pass["imu"] and self.frames["imu"] == {imu_cfg["frame"]}
            and self.timestamp_ok["imu"] and stationary_pass and rotate_pass and straight_pass
        )
        tf_pass = bool(
            self.counts["tf_static"] >= 2 and lidar_static and imu_static
            and "lidar_link" in reachable and "imu_link" in reachable and not cycle and not duplicate
        )
        phase_h_regression = bool(len(links) == 14 and len(movable) == 11 and len(fixed) == 2)
        all_pass = bool(
            all(type_pass.values()) and min(self.counts.values()) > 0 and scan_pass and imu_pass
            and tf_pass and timestamps_valid and phase_h_regression
        )
        return {
            "sensor_pose_source": "diagnostic placeholders; NOT HARDWARE CALIBRATED",
            "sensor_pose_note": self.config["extrinsics_note"],
            "classification": self.config["classification"],
            "counts": self.counts,
            "topic_types": type_pass,
            "lidar": {
                "topic": lidar_cfg["topic"], "type": "sensor_msgs/msg/LaserScan", "frame": lidar_cfg["frame"],
                "pose": {"xyz_m": lidar_cfg["pose_xyz_m"], "rpy_rad": lidar_cfg["pose_rpy_rad"]},
                "pose_confidence": lidar_cfg["pose_confidence"], "publish_rate_hz": lidar_cfg["publish_rate_hz"],
                "fov_deg": lidar_cfg["horizontal_fov_deg"], "angular_resolution_deg": lidar_cfg["angular_resolution_deg"],
                "range_min_m": lidar_cfg["range_min_m"], "range_max_m": lidar_cfg["range_max_m"],
                "message_count": self.counts["scan"], "finite_return_count": self.scan_finite_count,
                "valid_finite_return_count": self.scan_valid_range_count,
                "obstacle_expected_distance": expected, "obstacle_measured_distance": measured,
                "obstacle_error": error, "obstacle_detection_pass": bool(obstacle_pass), "pass": scan_pass,
            },
            "imu": {
                "topic": imu_cfg["topic"], "type": "sensor_msgs/msg/Imu", "frame": imu_cfg["frame"],
                "pose": {"xyz_m": imu_cfg["pose_xyz_m"], "rpy_rad": imu_cfg["pose_rpy_rad"]},
                "pose_confidence": imu_cfg["pose_confidence"], "publish_rate_hz": imu_cfg["publish_rate_hz"],
                "message_count": self.counts["imu"], "acceleration_semantics": imu_cfg["acceleration_semantics"],
                "stationary_angular_velocity": stationary_ang, "stationary_acceleration_magnitude": stationary_acc,
                "stationary_pass": stationary_pass, "rotate_angular_velocity_z": rotate_z,
                "rotate_odom_delta_yaw_rad": self.rotate_delta_yaw, "rotate_pass": rotate_pass,
                "straight_acceleration_response": straight_response, "straight_odom_dx_m": self.straight_dx,
                "stationary_acceleration_noise": stationary_noise,
                "straight_acceleration_threshold": straight_threshold,
                "straight_pass": straight_pass, "pass": imu_pass,
            },
            "tf": {
                "edges": [{"parent": p, "child": c, "topics": sorted(v)} for (p, c), v in sorted(self.tf_edges.items())],
                "lidar_reachable": "lidar_link" in reachable, "imu_reachable": "imu_link" in reachable,
                "tf_static_count": self.counts["tf_static"], "lidar_static": lidar_static, "imu_static": imu_static,
                "cycle_detected": cycle, "duplicate_parent_detected": duplicate, "parents": parents,
                "pass": tf_pass,
            },
            "urdf": {"link_count": len(links), "movable_joint_count": len(movable), "fixed_joint_count": len(fixed)},
            "phase_h_structural_regression_pass": phase_h_regression,
            "timestamps": self.timestamp_ok,
            "timestamps_valid": timestamps_valid,
            "runtime_validation_all_pass": all_pass,
        }

    def write(self) -> None:
        data = self.build_report()
        for path in (self.evidence_path, self.report_path):
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(path.suffix + ".tmp")
            temporary.write_text(json.dumps(data, indent=2) + "\n")
            os.replace(temporary, path)


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
