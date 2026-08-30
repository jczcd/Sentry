from __future__ import annotations

import math
import time

from geometry_msgs.msg import TransformStamped, Twist
from nav_msgs.msg import Odometry
import rclpy
from rclpy.node import Node
from tf2_ros import StaticTransformBroadcaster, TransformBroadcaster

from sentinel_interfaces.msg import HardwareState


class MockHardware(Node):
    def __init__(self) -> None:
        super().__init__("mock_hardware")
        self.declare_parameter("publish_map_to_odom", True)
        self.declare_parameter("initial_x", 2.0)
        self.declare_parameter("initial_y", 2.0)
        self._x = float(self.get_parameter("initial_x").value)
        self._y = float(self.get_parameter("initial_y").value)
        self._yaw = 0.0
        self._cmd = Twist()
        self._last_tick = time.monotonic()
        self._odom_pub = self.create_publisher(Odometry, "/sentry/odom", 20)
        self._state_pub = self.create_publisher(HardwareState, "/sentry/hardware_state", 10)
        self._tf = TransformBroadcaster(self)
        self.create_subscription(Twist, "/sentry/cmd_vel_safe", self._on_cmd, 20)
        self.create_timer(0.01, self._tick)
        self.create_timer(0.1, self._publish_state)
        if bool(self.get_parameter("publish_map_to_odom").value):
            static = StaticTransformBroadcaster(self)
            transform = TransformStamped()
            transform.header.stamp = self.get_clock().now().to_msg()
            transform.header.frame_id = "map"
            transform.child_frame_id = "odom"
            transform.transform.rotation.w = 1.0
            static.sendTransform(transform)
            self._static_tf = static

    def _on_cmd(self, message: Twist) -> None:
        self._cmd = message

    def _tick(self) -> None:
        now = time.monotonic()
        dt = min(max(now - self._last_tick, 0.0), 0.05)
        self._last_tick = now
        self._x += self._cmd.linear.x * dt
        self._y += self._cmd.linear.y * dt
        self._yaw += self._cmd.angular.z * dt
        half = self._yaw * 0.5

        odom = Odometry()
        odom.header.stamp = self.get_clock().now().to_msg()
        odom.header.frame_id = "odom"
        odom.child_frame_id = "base_link"
        odom.pose.pose.position.x = self._x
        odom.pose.pose.position.y = self._y
        odom.pose.pose.orientation.z = math.sin(half)
        odom.pose.pose.orientation.w = math.cos(half)
        odom.twist.twist = self._cmd
        self._odom_pub.publish(odom)

        transform = TransformStamped()
        transform.header = odom.header
        transform.child_frame_id = odom.child_frame_id
        transform.transform.translation.x = self._x
        transform.transform.translation.y = self._y
        transform.transform.rotation = odom.pose.pose.orientation
        self._tf.sendTransform(transform)

    def _publish_state(self) -> None:
        state = HardwareState()
        state.header.stamp = self.get_clock().now().to_msg()
        state.online = True
        state.estop = False
        state.heat_17 = 20.0
        state.heat_17_limit = 260.0
        state.ammo_remaining = 400.0
        state.battery_voltage = 24.0
        self._state_pub.publish(state)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = MockHardware()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
