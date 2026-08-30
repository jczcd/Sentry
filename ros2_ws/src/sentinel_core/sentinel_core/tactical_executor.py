from __future__ import annotations

import math
import time

from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import Odometry
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.time import Time
from std_msgs.msg import Bool, Int8
from tf2_ros import Buffer, TransformException, TransformListener

from sentinel_interfaces.msg import TacticalCommand


class TacticalExecutor(Node):
    def __init__(self) -> None:
        super().__init__("tactical_executor")
        self.declare_parameter("send_nav2_goal", True)
        self.declare_parameter("goal_frame", "map")
        self.declare_parameter("min_goal_interval_s", 0.8)
        self.declare_parameter("min_goal_offset_m", 0.2)
        self.declare_parameter("max_command_age_s", 1.5)
        self._send_nav2_goal = bool(self.get_parameter("send_nav2_goal").value)
        self._odom: Odometry | None = None
        self._odom_time = 0.0
        self._last_goal_time = 0.0
        self._goal_handle = None
        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)

        self._weapons_pub = self.create_publisher(
            Bool, "/sentry/weapons_free_request", 10
        )
        self._target_pub = self.create_publisher(Int8, "/sentry/target_request", 10)
        self._debug_goal_pub = self.create_publisher(PoseStamped, "/sentry/goal_debug", 10)
        self.create_subscription(Odometry, "/sentry/odom", self._on_odom, 20)
        self.create_subscription(
            TacticalCommand, "/sentry/policy/command", self._on_command, 10
        )
        self._nav_client = ActionClient(self, NavigateToPose, "/sentry/navigate_to_pose")

    def _on_odom(self, message: Odometry) -> None:
        self._odom = message
        self._odom_time = time.monotonic()

    def _on_command(self, message: TacticalCommand) -> None:
        target_slot = int(message.target_slot)
        target_valid = 0 <= target_slot <= 5
        weapons = Bool()
        weapons.data = bool(message.weapons_free) and target_valid
        self._weapons_pub.publish(weapons)
        target = Int8()
        target.data = target_slot if target_valid else -1
        self._target_pub.publish(target)

        if not self._send_nav2_goal or self._odom is None:
            return
        now = time.monotonic()
        if now - self._odom_time > 0.5:
            self.get_logger().warning(
                "odometry is stale; tactical goal was not sent",
                throttle_duration_sec=2.0,
            )
            return
        if now - self._last_goal_time < float(
            self.get_parameter("min_goal_interval_s").value
        ):
            return

        dx = float(message.goal_offset_field.x)
        dy = float(message.goal_offset_field.y)
        if not math.isfinite(dx) or not math.isfinite(dy):
            self.get_logger().warning(
                "rejecting non-finite tactical navigation offset",
                throttle_duration_sec=2.0,
            )
            return
        max_offset = 5.0
        dx = max(min(dx, max_offset), -max_offset)
        dy = max(min(dy, max_offset), -max_offset)
        if math.hypot(dx, dy) < float(
            self.get_parameter("min_goal_offset_m").value
        ):
            return
        if not self._nav_client.server_is_ready():
            self.get_logger().warning(
                "Nav2 action server is not ready",
                throttle_duration_sec=2.0,
            )
            return

        pose = self._goal_pose(dx, dy)
        if pose is None:
            return
        self._debug_goal_pub.publish(pose)

        goal = NavigateToPose.Goal()
        goal.pose = pose
        future = self._nav_client.send_goal_async(goal)
        future.add_done_callback(self._on_goal_response)
        self._last_goal_time = now

    def _goal_pose(self, dx: float, dy: float) -> PoseStamped | None:
        assert self._odom is not None
        goal_frame = str(self.get_parameter("goal_frame").value)
        odom_frame = self._odom.header.frame_id or "odom"
        x = float(self._odom.pose.pose.position.x)
        y = float(self._odom.pose.pose.position.y)
        orientation = self._odom.pose.pose.orientation
        yaw = math.atan2(
            2.0
            * (
                orientation.w * orientation.z
                + orientation.x * orientation.y
            ),
            1.0
            - 2.0
            * (
                orientation.y * orientation.y
                + orientation.z * orientation.z
            ),
        )
        if odom_frame != goal_frame:
            try:
                transform = self._tf_buffer.lookup_transform(
                    goal_frame,
                    odom_frame,
                    Time(),
                )
            except TransformException as exc:
                self.get_logger().warning(
                    f"cannot transform tactical goal to {goal_frame}: {exc}",
                    throttle_duration_sec=2.0,
                )
                return None
            translation = transform.transform.translation
            rotation = transform.transform.rotation
            transform_yaw = math.atan2(
                2.0
                * (
                    rotation.w * rotation.z
                    + rotation.x * rotation.y
                ),
                1.0
                - 2.0
                * (
                    rotation.y * rotation.y
                    + rotation.z * rotation.z
                ),
            )
            cosine = math.cos(transform_yaw)
            sine = math.sin(transform_yaw)
            x, y = (
                float(translation.x) + cosine * x - sine * y,
                float(translation.y) + sine * x + cosine * y,
            )
            yaw += transform_yaw

        pose = PoseStamped()
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.header.frame_id = goal_frame
        pose.pose.position.x = x + dx
        pose.pose.position.y = y + dy
        pose.pose.position.z = 0.0
        pose.pose.orientation.z = math.sin(yaw * 0.5)
        pose.pose.orientation.w = math.cos(yaw * 0.5)
        return pose

    def _on_goal_response(self, future) -> None:
        try:
            handle = future.result()
        except Exception as exc:
            self.get_logger().error(f"Nav2 goal request failed: {exc!r}")
            return
        if not handle.accepted:
            self.get_logger().warning("Nav2 rejected tactical goal")
            return
        if self._goal_handle is not None:
            self._goal_handle.cancel_goal_async()
        self._goal_handle = handle


def main(args=None) -> None:
    rclpy.init(args=args)
    node = TacticalExecutor()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
