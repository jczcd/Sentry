#!/usr/bin/env python3
"""Measure sensor cadence independently in wall and ROS simulation time."""
import argparse
import json
import os
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import Imu, PointCloud2


def seconds(stamp):
    return stamp.sec + stamp.nanosec / 1e9


class Audit(Node):
    def __init__(self, output: Path, target_sim_s: float):
        super().__init__("phase_j_rate_audit")
        self.output = output
        self.target_sim_s = target_sim_s
        self.wall_start = time.monotonic()
        self.sim_start = None
        self.sim_last = None
        self.lidar_stamps = []
        self.imu_stamps = []
        self.create_subscription(Clock, "/clock", self.clock, 100)
        self.create_subscription(PointCloud2, "/sentry/lidar/points", self.lidar, qos_profile_sensor_data)
        self.create_subscription(Imu, "/sentry/imu", self.imu, qos_profile_sensor_data)
        self.create_timer(0.25, self.write)

    def clock(self, msg):
        value = seconds(msg.clock)
        self.sim_start = value if self.sim_start is None and value > 0 else self.sim_start
        self.sim_last = value

    def lidar(self, msg):
        self.lidar_stamps.append(seconds(msg.header.stamp))

    def imu(self, msg):
        self.imu_stamps.append(seconds(msg.header.stamp))

    @staticmethod
    def rate(stamps):
        elapsed = stamps[-1] - stamps[0] if len(stamps) > 1 else 0.0
        return (len(stamps) - 1) / elapsed if elapsed > 0 else 0.0

    def write(self):
        wall_elapsed = time.monotonic() - self.wall_start
        sim_elapsed = (self.sim_last - self.sim_start) if self.sim_start is not None else 0.0
        data = {
            "wall_elapsed_s": wall_elapsed,
            "simulation_elapsed_s": sim_elapsed,
            "real_time_factor": sim_elapsed / wall_elapsed if wall_elapsed > 0 else 0.0,
            "lidar_messages": len(self.lidar_stamps),
            "imu_messages": len(self.imu_stamps),
            "lidar_rate_wall_hz": len(self.lidar_stamps) / wall_elapsed if wall_elapsed > 0 else 0.0,
            "lidar_rate_sim_hz": self.rate(self.lidar_stamps),
            "imu_rate_wall_hz": len(self.imu_stamps) / wall_elapsed if wall_elapsed > 0 else 0.0,
            "imu_rate_sim_hz": self.rate(self.imu_stamps),
            "imu_backend_unique_rate_sim_hz": self.rate(sorted(set(self.imu_stamps))),
            "imu_unique_timestamps": len(set(self.imu_stamps)),
            "imu_duplicate_timestamps": len(self.imu_stamps) - len(set(self.imu_stamps)),
        }
        self.output.parent.mkdir(parents=True, exist_ok=True)
        temp = self.output.with_suffix(".tmp")
        temp.write_text(json.dumps(data, indent=2) + "\n")
        os.replace(temp, self.output)
        if sim_elapsed >= self.target_sim_s and len(self.lidar_stamps) >= 20 and len(self.imu_stamps) >= 100:
            rclpy.shutdown()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--simulation-seconds", type=float, default=5.0)
    args = parser.parse_args()
    rclpy.init()
    node = Audit(args.output.resolve(), args.simulation_seconds)
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.write()
        node.destroy_node()


if __name__ == "__main__":
    main()
