from __future__ import annotations

import math
import time

from geometry_msgs.msg import Twist
import rclpy
from rclpy.node import Node

from sentinel_interfaces.msg import TacticalCommand


class MockNavController(Node):
    def __init__(self) -> None:
        super().__init__("mock_nav_controller")
        self.declare_parameter("kp", 0.8)
        self.declare_parameter("max_speed", 0.6)
        self.declare_parameter("timeout_s", 1.5)
        self._command = TacticalCommand()
        self._last_command = 0.0
        self._publisher = self.create_publisher(Twist, "/cmd_vel", 20)
        self.create_subscription(
            TacticalCommand, "/sentry/policy/command", self._on_command, 10
        )
        self.create_timer(0.05, self._tick)

    def _on_command(self, message: TacticalCommand) -> None:
        self._command = message
        self._last_command = time.monotonic()

    def _tick(self) -> None:
        output = Twist()
        if time.monotonic() - self._last_command <= float(
            self.get_parameter("timeout_s").value
        ):
            kp = float(self.get_parameter("kp").value)
            output.linear.x = kp * self._command.goal_offset_field.x
            output.linear.y = kp * self._command.goal_offset_field.y
            speed = math.hypot(output.linear.x, output.linear.y)
            maximum = float(self.get_parameter("max_speed").value)
            if speed > maximum > 0.0:
                scale = maximum / speed
                output.linear.x *= scale
                output.linear.y *= scale
        self._publisher.publish(output)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = MockNavController()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
