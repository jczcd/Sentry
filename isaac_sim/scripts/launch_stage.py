#!/usr/bin/env python3
"""Open a migrated Sentinel stage and ensure a ROS 2 simulation clock exists.

Run this with Isaac Sim's ``python.sh``. The robot-specific ROS graphs are kept
inside the migrated USD because their prim targets cannot be inferred safely.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--no-clock", action="store_true")
    parser.add_argument("--enable-swerve-control", action="store_true")
    parser.add_argument("--phase-f-report", type=Path)
    parser.add_argument("--phase-f-evidence", type=Path)
    parser.add_argument("--enable-state-publishers", action="store_true")
    parser.add_argument("--state-publish-rate-hz", type=float, default=50.0)
    parser.add_argument("--enable-sensors", action="store_true")
    parser.add_argument("--sensor-config", type=Path)
    parser.add_argument("--disable-legacy-scan", action="store_true")
    parser.add_argument("--show-lidar-debug", action="store_true")
    parser.add_argument("--pointcloud-rate-hz", type=float)
    parser.add_argument("--diagnostic-environment", action="store_true")
    return parser.parse_args()


def create_clock_graph() -> None:
    import omni.graph.core as og

    graph_path = "/SentinelROS/Clock"
    try:
        og.Controller.edit(
            {"graph_path": graph_path, "evaluator_name": "execution"},
            {
                og.Controller.Keys.CREATE_NODES: [
                    ("OnPlaybackTick", "omni.graph.action.OnPlaybackTick"),
                    ("ROS2Context", "isaacsim.ros2.bridge.ROS2Context"),
                    (
                        "ReadSimTime",
                        "isaacsim.core.nodes.IsaacReadSimulationTime",
                    ),
                    (
                        "PublishClock",
                        "isaacsim.ros2.bridge.ROS2PublishClock",
                    ),
                ],
                og.Controller.Keys.CONNECT: [
                    (
                        "OnPlaybackTick.outputs:tick",
                        "PublishClock.inputs:execIn",
                    ),
                    (
                        "ReadSimTime.outputs:simulationTime",
                        "PublishClock.inputs:timeStamp",
                    ),
                    (
                        "ROS2Context.outputs:context",
                        "PublishClock.inputs:context",
                    ),
                ],
                og.Controller.Keys.SET_VALUES: [
                    ("ReadSimTime.inputs:resetOnStop", False),
                    ("ROS2Context.inputs:useDomainIDEnvVar", True),
                    ("PublishClock.inputs:topicName", "/clock"),
                ],
            },
        )
    except Exception as exc:
        # An authored graph with the same path is expected on subsequent opens.
        print(f"[sentinel] clock graph not created: {exc}", file=sys.stderr)


def main() -> int:
    args = parse_args()
    stage = args.stage.expanduser().resolve()
    if not stage.is_file() or stage.suffix.lower() not in {".usd", ".usda", ".usdc"}:
        print(f"invalid USD stage: {stage}", file=sys.stderr)
        return 2
    os.environ.setdefault("RMW_IMPLEMENTATION", "rmw_fastrtps_cpp")
    workspace = Path(__file__).resolve().parents[2]
    fastdds_profile = workspace / "config" / "fastdds.xml"
    if fastdds_profile.is_file():
        os.environ.setdefault(
            "FASTRTPS_DEFAULT_PROFILES_FILE",
            str(fastdds_profile),
        )

    from isaacsim import SimulationApp

    app = SimulationApp(launch_config={"headless": args.headless})
    try:
        from isaacsim.core.utils.extensions import enable_extension

        enable_extension("isaacsim.ros2.bridge")
        enable_extension("isaacsim.ros2.nodes")
        if args.enable_sensors:
            enable_extension("isaacsim.sensors.experimental.rtx")
            enable_extension("isaacsim.sensors.experimental.physics")
            if args.show_lidar_debug:
                enable_extension("isaacsim.sensors.rtx.nodes")
        app.update()

        from isaacsim.core.utils.stage import open_stage
        import omni.timeline
        import omni.usd

        result = open_stage(str(stage))
        opened = result[0] if isinstance(result, tuple) else bool(result)
        if not opened:
            print(f"failed to open stage: {stage}", file=sys.stderr)
            return 3
        app.update()
        if omni.usd.get_context().get_stage() is None:
            print(f"stage context is empty after opening: {stage}", file=sys.stderr)
            return 3
        if not args.no_clock:
            create_clock_graph()
            app.update()

        print(
            "[sentinel] stage ready; ROS_DOMAIN_ID="
            + os.environ.get("ROS_DOMAIN_ID", "<unset>")
        )
        timeline = omni.timeline.get_timeline_interface()
        timeline.play()
        controller = None
        if args.enable_swerve_control:
            if args.phase_f_report is None or args.phase_f_evidence is None:
                print("--phase-f-report and --phase-f-evidence are required with swerve control", file=sys.stderr)
                return 4
            from stage5d_swerve_controller import Stage5DSwerveController

            controller = Stage5DSwerveController(
                args.phase_f_report.resolve(), args.phase_f_evidence.resolve()
            )
            for _ in range(40):
                app.update()
            controller.initialize()
            print("[sentinel] Stage5D swerve subscriber ready: /sentry/cmd_vel_safe")
        state_publisher = None
        if args.enable_state_publishers:
            from isaacsim.core.prims import SingleArticulation
            from stage5d_state_publisher import Stage5DStatePublisher

            if controller:
                state_robot = controller.robot
                articulation_path = controller.build["articulation_root"]
                for _ in range(180):
                    app.update()
                    controller.update()
            else:
                articulation_path = "/Sentry/Sentry_raw/base_link"
                state_robot = SingleArticulation(articulation_path, reset_xform_properties=False)
                for _ in range(180):
                    app.update()
                state_robot.initialize()
            state_publisher = Stage5DStatePublisher(
                state_robot, articulation_path, args.state_publish_rate_hz
            )
            print("[sentinel] state publishers ready: /sentry/odom /joint_states /tf")
        sensor_manager = None
        if args.enable_sensors:
            from stage5d_sensor_manager import Stage5DSensorManager

            sensor_config = args.sensor_config or workspace / "isaac_sim/config/phase_i_sensors.json"
            articulation_path = (
                controller.build["articulation_root"]
                if controller
                else "/Sentry/Sentry_raw/base_link"
            )
            sensor_manager = Stage5DSensorManager(
                articulation_path,
                sensor_config.resolve(),
                enable_legacy_scan=not args.disable_legacy_scan,
                show_lidar_debug=args.show_lidar_debug,
                pointcloud_rate_hz=args.pointcloud_rate_hz,
                diagnostic_environment=args.diagnostic_environment,
            )
            sensor_manager.start_physics_sampling()
            print("[sentinel] sensors ready: /sentry/lidar/points /sentry/scan /sentry/imu")
        while app.is_running() and not (controller and controller.done):
            app.update()
            if controller:
                controller.update()
            if state_publisher:
                state_publisher.update()
            if sensor_manager:
                sensor_manager.update()
        timeline.stop()
        if state_publisher:
            state_publisher.close()
        if sensor_manager:
            sensor_manager.close()
    finally:
        app.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
