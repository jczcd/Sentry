#!/usr/bin/env python3
"""Collect real ROS graph/message evidence for the PHASE F integration test."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time

from geometry_msgs.msg import Twist
import rclpy
from rclpy.node import Node
from rosgraph_msgs.msg import Clock


class EvidenceObserver(Node):
    def __init__(self, output: Path) -> None:
        super().__init__("phase_f_topic_observer")
        self.output = output
        self.started_monotonic = time.monotonic()
        self.raw_count = 0
        self.safe_count = 0
        self.clock_count = 0
        self.last_raw_monotonic = None
        self.last_safe_monotonic = None
        self.create_subscription(Twist, "/cmd_vel", self._raw, 50)
        self.create_subscription(Twist, "/sentry/cmd_vel_safe", self._safe, 100)
        self.create_subscription(Clock, "/clock", self._on_clock, 100)
        self.create_timer(0.2, self.write)

    def _raw(self, _message: Twist) -> None:
        self.raw_count += 1
        self.last_raw_monotonic = time.monotonic()

    def _safe(self, _message: Twist) -> None:
        self.safe_count += 1
        self.last_safe_monotonic = time.monotonic()

    def _on_clock(self, _message: Clock) -> None:
        self.clock_count += 1

    def write(self) -> None:
        graph = dict(self.get_topic_names_and_types())
        safe_types = graph.get("/sentry/cmd_vel_safe", [])
        evidence = {
            "observer_started_monotonic": self.started_monotonic,
            "observed_monotonic": time.monotonic(),
            "received_raw_msg_count": self.raw_count,
            "received_safe_msg_count": self.safe_count,
            "received_clock_msg_count": self.clock_count,
            "last_raw_msg_monotonic": self.last_raw_monotonic,
            "last_safe_msg_monotonic": self.last_safe_monotonic,
            "clock_pass": self.clock_count > 0,
            "safe_topic_types": safe_types,
            "safe_topic_type_pass": safe_types == ["geometry_msgs/msg/Twist"],
        }
        self.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.output.with_suffix(self.output.suffix + ".tmp")
        temporary.write_text(json.dumps(evidence, indent=2) + "\n")
        os.replace(temporary, self.output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rclpy.init()
    node = EvidenceObserver(args.output.resolve())
    try:
        rclpy.spin(node)
    finally:
        node.write()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
