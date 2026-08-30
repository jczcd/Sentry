"""Isaac-side continuous Stage5D controller using the installed ROS2 Twist OGN node."""
from __future__ import annotations

import json
import math
import os
import time
from pathlib import Path

import numpy as np


def wrap(value: float) -> float:
    return (value + math.pi) % (2.0 * math.pi) - math.pi


class Stage5DSwerveController:
    CASE_NAMES = ("straight", "lateral", "diagonal", "rotate", "watchdog")

    def __init__(self, report_path: Path, evidence_path: Path) -> None:
        import omni.graph.core as og

        self.og = og
        self.report_path = report_path
        self.evidence_path = evidence_path
        sim_root = Path(os.environ["SENTINEL_SIM_ROOT"])
        self.config = json.loads((sim_root / "config/stage5d_swerve.json").read_text())
        self.build = json.loads((sim_root / "output/stage5d_build_report.json").read_text())
        prior = json.loads((sim_root / "output/stage5d_runtime_report.json").read_text())
        self.calibration = prior["calibration"]
        self.modules = list(self.config["modules"])
        self.robot = None
        self.indices = {}
        self.last_steer = {module: 0.0 for module in self.modules}
        self.active = None
        self.stop_frames = 0
        self.done = False
        self.safe_command_control_ticks = 0
        self.report = {
            "topic_input": "/cmd_vel",
            "topic_safe": "/sentry/cmd_vel_safe",
            "ROS_DOMAIN_ID": os.environ.get("ROS_DOMAIN_ID"),
            "RMW_IMPLEMENTATION": os.environ.get("RMW_IMPLEMENTATION"),
            "received_raw_msg_count": 0,
            "received_safe_msg_count": 0,
            "safe_command_control_ticks": 0,
            "watchdog_timeout_s": 0.5,
            "watchdog_triggered": False,
            "watchdog_pass": False,
            "tests": [],
            "pass_count": 0,
            "expected_count": 4,
            "last_command_zero": False,
            "runtime_validation_all_pass": False,
        }
        keys = og.Controller.Keys
        og.Controller.edit(
            {"graph_path": "/SentinelROS/SwerveCommand", "evaluator_name": "execution"},
            {
                keys.CREATE_NODES: [
                    ("Tick", "omni.graph.action.OnPlaybackTick"),
                    ("Context", "isaacsim.ros2.bridge.ROS2Context"),
                    ("SubscribeTwist", "isaacsim.ros2.bridge.ROS2SubscribeTwist"),
                ],
                keys.CONNECT: [
                    ("Tick.outputs:tick", "SubscribeTwist.inputs:execIn"),
                    ("Context.outputs:context", "SubscribeTwist.inputs:context"),
                ],
                keys.SET_VALUES: [
                    ("Context.inputs:useDomainIDEnvVar", True),
                    ("SubscribeTwist.inputs:topicName", "/sentry/cmd_vel_safe"),
                    ("SubscribeTwist.inputs:queueSize", 20),
                ],
            },
        )
        self.linear_attr = og.Controller.attribute(
            "/SentinelROS/SwerveCommand/SubscribeTwist.outputs:linearVelocity"
        )
        self.angular_attr = og.Controller.attribute(
            "/SentinelROS/SwerveCommand/SubscribeTwist.outputs:angularVelocity"
        )

    def initialize(self) -> None:
        from isaacsim.core.prims import SingleArticulation

        self.robot = SingleArticulation(
            self.build["articulation_root"],
            name="sentinel_phase_f_swerve",
            reset_xform_properties=False,
        )
        self.robot.initialize()
        self.indices = {name: int(self.robot.get_dof_index(name)) for name in self.robot.dof_names}
        self._command_zero()

    def _pose(self) -> dict:
        import omni.usd
        from pxr import Gf, UsdGeom

        stage = omni.usd.get_context().get_stage()
        matrix = UsdGeom.XformCache().GetLocalToWorldTransform(
            stage.GetPrimAtPath(self.build["articulation_root"])
        )
        p = matrix.ExtractTranslation()
        x = matrix.TransformDir(Gf.Vec3d(1, 0, 0)).GetNormalized()
        y = matrix.TransformDir(Gf.Vec3d(0, 1, 0)).GetNormalized()
        mpu = self.build["meters_per_unit"]
        return {
            "position_world_m": [float(p[i]) * mpu for i in range(3)],
            "x_axis_world": [float(x[i]) for i in range(3)],
            "y_axis_world": [float(y[i]) for i in range(3)],
            "yaw_rad": math.atan2(float(x[1]), float(x[0])),
        }

    def _targets(self, vx: float, vy: float, wz: float):
        steer, wheel = {}, {}
        radius = self.build["wheel_radius_m"]
        q = np.asarray(self.robot.get_joint_positions(), dtype=float)
        for module in self.modules:
            spec = self.config["modules"][module]
            x, y = self.build["module_geometry"][module]["position_m"]
            vix, viy = vx - wz * y, vy + wz * x
            speed = math.hypot(vix, viy)
            if speed < 1e-5:
                joint = self.last_steer[module]
            else:
                desired = math.atan2(viy, vix)
                cal = self.calibration[module]
                joint = wrap(desired - cal["zero_heading_rad"]) / cal["steer_positive_heading_sign"]
                joint = wrap(joint)
                current = float(q[self.indices[spec["steer_joint"]]])
                delta = wrap(joint - current)
                if delta > math.pi / 2:
                    joint = wrap(joint - math.pi)
                    speed *= -1
                elif delta < -math.pi / 2:
                    joint = wrap(joint + math.pi)
                    speed *= -1
                self.last_steer[module] = joint
            steer[spec["steer_joint"]] = joint
            error = wrap(joint - float(q[self.indices[spec["steer_joint"]]]))
            scale = max(0.0, math.cos(error))
            sign = self.calibration[module]["drive_positive_response_sign"]
            wheel[spec["drive_joint"]] = speed / radius / sign * scale
        return steer, wheel

    def _apply(self, steer: dict, wheel: dict) -> None:
        from isaacsim.core.utils.types import ArticulationAction

        sn, wn = list(steer), list(wheel)
        self.robot.apply_action(ArticulationAction(
            joint_positions=np.array([steer[n] for n in sn], dtype=np.float32),
            joint_indices=np.array([self.indices[n] for n in sn], dtype=np.int32),
        ))
        self.robot.apply_action(ArticulationAction(
            joint_velocities=np.array([wheel[n] for n in wn], dtype=np.float32),
            joint_indices=np.array([self.indices[n] for n in wn], dtype=np.int32),
        ))

    def _command_zero(self) -> None:
        steer, wheel = self._targets(0.0, 0.0, 0.0)
        self._apply(steer, wheel)

    def _gate(self, name: str, dx: float, dy: float, dyaw: float) -> bool:
        gate = self.config["acceptance"][name]
        deg = abs(math.degrees(dyaw))
        if name == "straight":
            return dx > gate["forward_min_m"] and abs(dy) <= max(gate["cross_min_limit_m"], dx * gate["cross_ratio"]) and deg <= gate["yaw_max_degrees"]
        if name == "lateral":
            return dy > gate["lateral_min_m"] and abs(dx) <= max(gate["cross_min_limit_m"], dy * gate["cross_ratio"]) and deg <= gate["yaw_max_degrees"]
        if name == "diagonal":
            return dx > gate["forward_min_m"] and dy > gate["lateral_min_m"] and deg <= gate["yaw_max_degrees"]
        return dyaw > math.radians(gate["yaw_min_degrees"]) and math.hypot(dx, dy) <= gate["translation_max_m"]

    def _finalize(self) -> None:
        end = self._pose()
        episode = self.active
        start = episode["base_start_pose"]
        delta = [end["position_world_m"][i] - start["position_world_m"][i] for i in range(3)]
        dx = sum(delta[i] * start["x_axis_world"][i] for i in range(3))
        dy = sum(delta[i] * start["y_axis_world"][i] for i in range(3))
        dyaw = wrap(end["yaw_rad"] - start["yaw_rad"])
        episode.update(base_end_pose=end, dx_body_m=dx, dy_body_m=dy,
                       delta_yaw_rad=dyaw, delta_yaw_deg=math.degrees(dyaw))
        if episode["name"] == "watchdog":
            qd = np.asarray(self.robot.get_joint_velocities(), dtype=float)
            stopped = max(abs(float(qd[self.indices[self.config["modules"][m]["drive_joint"]]])) for m in self.modules) < 0.15
            evidence = json.loads(self.evidence_path.read_text())
            last_raw = evidence.get("last_raw_msg_monotonic")
            elapsed = time.monotonic() - last_raw if last_raw is not None else 0.0
            triggered = bool(self.active and last_raw is not None and elapsed >= self.report["watchdog_timeout_s"])
            self.report["watchdog_triggered"] = triggered
            self.report["watchdog_pass"] = bool(triggered and stopped)
            self.report["watchdog"] = {
                **episode,
                "time_since_last_raw_msg_s": elapsed,
                "wheel_stopped": bool(stopped),
            }
        else:
            episode["case_pass"] = bool(self._gate(episode["name"], dx, dy, dyaw))
            self.report["tests"].append(episode)
        self.active = None
        if len(self.report["tests"]) == 4 and "watchdog" in self.report:
            self.report["pass_count"] = sum(t["case_pass"] for t in self.report["tests"])
            self.report["last_command_zero"] = True
            evidence = json.loads(self.evidence_path.read_text())
            self.report["received_raw_msg_count"] = evidence.get("received_raw_msg_count", 0)
            self.report["received_safe_msg_count"] = evidence.get("received_safe_msg_count", 0)
            self.report["safe_command_control_ticks"] = self.safe_command_control_ticks
            self.report["clock_pass"] = evidence.get("clock_pass", False)
            self.report["safe_topic_type_pass"] = evidence.get("safe_topic_type_pass", False)
            self.report["ros_evidence"] = evidence
            self.report["runtime_validation_all_pass"] = bool(
                self.report["pass_count"] == self.report["expected_count"] == 4
                and self.report["watchdog_pass"]
                and self.report["received_raw_msg_count"] > 0
                and self.report["received_safe_msg_count"] > 0
                and self.report["clock_pass"] is True
                and self.report["safe_topic_type_pass"] is True
            )
            self.report_path.parent.mkdir(parents=True, exist_ok=True)
            self.report_path.write_text(json.dumps(self.report, indent=2) + "\n")
            self.done = True

    def update(self) -> None:
        linear = self.og.Controller.get(self.linear_attr)
        angular = self.og.Controller.get(self.angular_attr)
        vx, vy, wz = float(linear[0]), float(linear[1]), float(angular[2])
        nonzero = math.hypot(vx, vy) > 1e-4 or abs(wz) > 1e-4
        if nonzero:
            self.safe_command_control_ticks += 1
            self.stop_frames = 0
            if self.active is None:
                index = len(self.report["tests"])
                name = self.CASE_NAMES[index]
                self.active = {"name": name, "command": {"vx": vx, "vy": vy, "wz": wz}, "base_start_pose": self._pose()}
            steer, wheel = self._targets(vx, vy, wz)
            self._apply(steer, wheel)
        else:
            self._command_zero()
            if self.active is not None:
                self.stop_frames += 1
                if self.stop_frames >= 60:
                    self._finalize()
