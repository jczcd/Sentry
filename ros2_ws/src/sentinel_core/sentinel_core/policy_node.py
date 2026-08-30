from __future__ import annotations

import math
import os
from pathlib import Path
import sys

import rclpy
from rclpy.node import Node

from sentinel_interfaces.msg import PolicyObservation, TacticalCommand


class PolicyNode(Node):
    def __init__(self) -> None:
        super().__init__("policy")
        self.declare_parameter("backend", "mock")
        self.declare_parameter("policy_dir", "")
        self.declare_parameter("rmuc_rl_path", "")
        self.declare_parameter("device", "cpu")
        self.declare_parameter("camp", "红")
        self.declare_parameter("mock_goal_dx", 0.8)
        self.declare_parameter("mock_goal_dy", 0.0)

        self._backend = str(self.get_parameter("backend").value)
        self._sequence = 0
        self._runner = None
        self._publisher = self.create_publisher(
            TacticalCommand, "/sentry/policy/command", 10
        )
        self.create_subscription(
            PolicyObservation, "/sentry/policy/observation", self._on_observation, 10
        )
        if self._backend == "rmuc_offline_rl":
            self._load_runner()
        elif self._backend != "mock":
            raise ValueError(f"unsupported policy backend: {self._backend}")

    def _load_runner(self) -> None:
        project_path = str(self.get_parameter("rmuc_rl_path").value).strip()
        if project_path:
            sys.path.insert(0, str(Path(project_path).expanduser().resolve()))
        policy_dir = str(self.get_parameter("policy_dir").value).strip()
        if not policy_dir:
            self.get_logger().error(
                "policy_dir is empty; learned policy will stay safe-idle"
            )
            return
        try:
            from rm_rl.deploy import MLPPolicyRunner

            self._runner = MLPPolicyRunner(
                os.path.expanduser(policy_dir),
                device=str(self.get_parameter("device").value),
                camp=str(self.get_parameter("camp").value),
            )
            info = self._runner.info
            if (
                info.get("action_mode") != "tactical"
                or int(info.get("obs_dim", -1)) != 161
                or int(info.get("act_dim", -1)) != 10
            ):
                raise ValueError(
                    "checkpoint must use tactical mode with obs_dim=161 "
                    "and act_dim=10"
                )
            self.get_logger().info(f"loaded policy from {policy_dir}")
        except Exception as exc:  # keep the rest of the safety stack alive
            self.get_logger().error(f"failed to load policy: {exc!r}")
            self._runner = None

    def _mock_command(self) -> dict:
        return {
            "goal_dx": float(self.get_parameter("mock_goal_dx").value),
            "goal_dy": float(self.get_parameter("mock_goal_dy").value),
            "fire": 0.0,
            "target": None,
            "target_conf": 1.0,
            "target_probs": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
        }

    @staticmethod
    def _finite(value, default: float = 0.0) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return default
        return parsed if math.isfinite(parsed) else default

    @classmethod
    def _target_slot(cls, value) -> int:
        if value is None:
            return TacticalCommand.NO_TARGET
        try:
            target = int(value)
        except (TypeError, ValueError):
            return TacticalCommand.NO_TARGET
        return target if 0 <= target <= 5 else TacticalCommand.NO_TARGET

    def _on_observation(self, message: PolicyObservation) -> None:
        if int(message.schema_version) != int(PolicyObservation.SCHEMA_VERSION):
            self.get_logger().error(
                f"observation schema {message.schema_version} is unsupported"
            )
            return

        command = self._mock_command()
        if self._backend == "rmuc_offline_rl" and self._runner is not None:
            try:
                import numpy as np

                command = self._runner.step(
                    np.asarray(message.features, dtype=np.float32)
                )
            except Exception as exc:
                self.get_logger().error(f"policy inference failed: {exc!r}")
                command = {
                    "goal_dx": 0.0,
                    "goal_dy": 0.0,
                    "fire": 0.0,
                    "target": None,
                    "target_conf": 0.0,
                    "target_probs": [0.0] * 6 + [1.0],
                }

        output = TacticalCommand()
        output.header = message.header
        output.sequence = self._sequence
        self._sequence = (self._sequence + 1) & 0xFFFFFFFF
        # Keep malformed learned-policy output from becoming a navigation goal.
        output.goal_offset_field.x = max(
            min(self._finite(command.get("goal_dx", 0.0)), 5.0), -5.0
        )
        output.goal_offset_field.y = max(
            min(self._finite(command.get("goal_dy", 0.0)), 5.0), -5.0
        )
        output.goal_offset_field.z = 0.0
        output.weapons_free = self._finite(command.get("fire", 0.0)) > 0.5
        output.target_slot = self._target_slot(command.get("target"))
        output.target_confidence = max(
            min(self._finite(command.get("target_conf", 0.0)), 1.0), 0.0
        )
        probabilities = list(command.get("target_probs", [0.0] * 6 + [1.0]))
        probabilities = probabilities[:7] + [0.0] * max(0, 7 - len(probabilities))
        probabilities = [max(self._finite(value), 0.0) for value in probabilities]
        total = sum(probabilities)
        if total <= 0.0:
            probabilities = [0.0] * 6 + [1.0]
        else:
            probabilities = [value / total for value in probabilities]
        output.target_probabilities = probabilities
        output.source = self._backend
        self._publisher.publish(output)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = PolicyNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
