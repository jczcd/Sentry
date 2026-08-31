"""ROS 2 process supervisor for allow-listed training jobs.

The service never invokes a shell. It starts one configured runner argv and
passes only a validated config path and run name to it.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import signal
import subprocess
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy

from sentinel_interfaces.msg import TrainingStatus
from sentinel_interfaces.srv import StartTraining, StopTraining


RUN_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


class TrainingManager(Node):
    def __init__(self) -> None:
        super().__init__("training_manager")
        self.declare_parameter("enabled", False)
        self.declare_parameter(
            "runner_argv", ["python3", "training/run_job.py"]
        )
        self.declare_parameter("working_directory", ".")
        self.declare_parameter("allowed_config_root", "training/jobs")

        working = Path(
            str(self.get_parameter("working_directory").value)
        ).expanduser()
        self._working = working.resolve()
        config_root = Path(
            str(self.get_parameter("allowed_config_root").value)
        ).expanduser()
        if not config_root.is_absolute():
            config_root = self._working / config_root
        self._config_root = config_root.resolve()
        self._process: subprocess.Popen | None = None
        self._state = TrainingStatus.STATE_IDLE
        self._run_name = ""
        self._config_path = ""
        self._exit_code = 0
        self._detail = "idle"
        self._stop_requested_at = 0.0

        qos = QoSProfile(depth=1)
        qos.reliability = ReliabilityPolicy.RELIABLE
        qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
        self._publisher = self.create_publisher(
            TrainingStatus, "/sentry/training/status", qos
        )
        self.create_service(
            StartTraining, "/sentry/training/start", self._start_training
        )
        self.create_service(
            StopTraining, "/sentry/training/stop", self._stop_training
        )
        self.create_timer(0.5, self._poll)
        self._publish()

    def _publish(self) -> None:
        message = TrainingStatus()
        message.header.stamp = self.get_clock().now().to_msg()
        message.state = self._state
        message.pid = self._process.pid if self._process is not None else -1
        message.exit_code = self._exit_code
        message.run_name = self._run_name
        message.config_path = self._config_path
        message.detail = self._detail
        self._publisher.publish(message)

    def _resolve_config(self, text: str) -> Path:
        candidate = Path(text).expanduser()
        if not candidate.is_absolute():
            candidate = self._working / candidate
        candidate = candidate.resolve(strict=True)
        if self._config_root not in candidate.parents:
            raise ValueError(f"config must be below {self._config_root}")
        if candidate.suffix.lower() not in {".yaml", ".yml"}:
            raise ValueError("training config must be YAML")
        if not candidate.is_file():
            raise ValueError("training config is not a file")
        return candidate

    def _start_training(
        self,
        request: StartTraining.Request,
        response: StartTraining.Response,
    ):
        if not bool(self.get_parameter("enabled").value):
            response.accepted = False
            response.pid = -1
            response.reason = "training manager is disabled"
            return response
        if self._process is not None:
            response.accepted = False
            response.pid = self._process.pid
            response.reason = "a training job is already running"
            return response
        if not RUN_NAME.fullmatch(request.run_name):
            response.accepted = False
            response.pid = -1
            response.reason = "invalid run_name"
            return response
        try:
            config = self._resolve_config(request.config_path)
            runner = [
                str(value)
                for value in self.get_parameter("runner_argv").value
            ]
            if not runner:
                raise ValueError("runner_argv is empty")
            command = runner + [
                "--config",
                str(config),
                "--run-name",
                request.run_name,
            ]
            self._state = TrainingStatus.STATE_STARTING
            self._run_name = request.run_name
            self._config_path = str(config)
            self._detail = "starting"
            self._publish()
            self._process = subprocess.Popen(
                command,
                cwd=self._working,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
        except (OSError, ValueError) as exc:
            self._state = TrainingStatus.STATE_FAILED
            self._exit_code = -1
            self._detail = f"start failed: {exc}"
            self._publish()
            response.accepted = False
            response.pid = -1
            response.reason = str(exc)
            return response
        self._state = TrainingStatus.STATE_RUNNING
        self._detail = "running"
        self._publish()
        response.accepted = True
        response.pid = self._process.pid
        response.reason = "training started"
        return response

    def _stop_training(
        self,
        request: StopTraining.Request,
        response: StopTraining.Response,
    ):
        if self._process is None:
            response.accepted = False
            response.reason = "no training job is running"
            return response
        try:
            sig = signal.SIGKILL if request.force else signal.SIGTERM
            os.killpg(self._process.pid, sig)
            self._state = TrainingStatus.STATE_STOPPING
            self._detail = "forced stop" if request.force else "graceful stop"
            self._stop_requested_at = time.monotonic()
            self._publish()
        except ProcessLookupError:
            pass
        response.accepted = True
        response.reason = "stop signal sent"
        return response

    def _poll(self) -> None:
        if self._process is None:
            return
        code = self._process.poll()
        if code is None:
            if (
                self._state == TrainingStatus.STATE_STOPPING
                and time.monotonic() - self._stop_requested_at > 15.0
            ):
                try:
                    os.killpg(self._process.pid, signal.SIGKILL)
                    self._detail = "grace period expired; killed"
                except ProcessLookupError:
                    pass
            self._publish()
            return
        self._exit_code = int(code)
        self._state = (
            TrainingStatus.STATE_SUCCEEDED
            if code == 0
            else TrainingStatus.STATE_FAILED
        )
        self._detail = f"job exited with code {code}"
        self._process = None
        self._publish()

    def destroy_node(self):
        if self._process is not None and self._process.poll() is None:
            try:
                os.killpg(self._process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = TrainingManager()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
