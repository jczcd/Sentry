#!/usr/bin/env python3
"""Truthful topic evidence collector for the future Point-LIO runtime gate."""
import argparse
import json
import math
import os
from pathlib import Path

import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import Imu, PointCloud2
from tf2_msgs.msg import TFMessage


class Observer(Node):
    def __init__(self, output: Path):
        super().__init__("phase_j_point_lio_observer")
        self.output = output
        self.counts = {key: 0 for key in ("clock", "gt_odom", "lio_odom", "lidar", "imu", "registered", "tf")}
        self.finite = {"gt_odom": True, "lio_odom": True}
        self.create_subscription(Clock, "/clock", lambda msg: self.hit("clock"), 100)
        self.create_subscription(Odometry, "/sentry/odom", lambda msg: self.odom("gt_odom", msg), 50)
        self.create_subscription(Odometry, "/sentry/lio/odom", lambda msg: self.odom("lio_odom", msg), 50)
        self.create_subscription(PointCloud2, "/sentry/lidar/points", lambda msg: self.hit("lidar"), qos_profile_sensor_data)
        self.create_subscription(Imu, "/sentry/imu", lambda msg: self.hit("imu"), qos_profile_sensor_data)
        self.create_subscription(PointCloud2, "/sentry/lio/cloud_registered", lambda msg: self.hit("registered"), qos_profile_sensor_data)
        self.create_subscription(TFMessage, "/tf", lambda msg: self.hit("tf"), 100)
        self.create_timer(0.5, self.write)

    def hit(self, key):
        self.counts[key] += 1

    def odom(self, key, msg):
        self.hit(key)
        p, q = msg.pose.pose.position, msg.pose.pose.orientation
        self.finite[key] &= all(math.isfinite(v) for v in (p.x, p.y, p.z, q.x, q.y, q.z, q.w))

    def write(self):
        data = {
            "counts": self.counts,
            "finite": self.finite,
            "functional_output_present": self.counts["lio_odom"] > 0 and self.counts["registered"] > 0,
        }
        self.output.parent.mkdir(parents=True, exist_ok=True)
        temp = self.output.with_suffix(".tmp")
        temp.write_text(json.dumps(data, indent=2) + "\n")
        os.replace(temp, self.output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rclpy.init(); node = Observer(args.output.resolve())
    try: rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException): pass
    finally: node.write(); node.destroy_node()


if __name__ == "__main__":
    main()
