#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import math
import traceback
import numpy as np

def package_root():
    return Path(__file__).resolve().parent.parent

root = package_root()
cfg = json.loads((root / "config" / "stage5d_swerve.json").read_text(encoding="utf-8"))
input_path = (root / cfg["output_stage"]).resolve()
s4_report_path = (root / cfg["stage4_report"]).resolve()
preflight_path = (root / cfg["stage5b_preflight"]).resolve()
report_path = (root / cfg["runtime_report"]).resolve()

for p in (input_path, s4_report_path, preflight_path):
    if not p.exists():
        raise SystemExit(f"Required file not found: {p}")

s4 = json.loads(s4_report_path.read_text(encoding="utf-8"))
pre = json.loads(preflight_path.read_text(encoding="utf-8"))
mapping = s4["resolved_mapping"]

from isaacsim import SimulationApp
simulation_app = SimulationApp({"headless": True})

def wrap_pi(x):
    return (x + math.pi) % (2.0 * math.pi) - math.pi

def normalize2(v):
    v = np.asarray(v, dtype=np.float64)
    n = np.linalg.norm(v[:2])
    if n < 1e-12:
        raise RuntimeError(f"Degenerate 2D vector: {v}")
    return np.array([v[0] / n, v[1] / n], dtype=np.float64)

def main():
    import omni.usd
    import omni.timeline
    from pxr import UsdGeom, UsdPhysics, Gf
    from isaacsim.core.prims import SingleArticulation
    from isaacsim.core.utils.types import ArticulationAction

    mpu = float(pre["meters_per_unit"])
    radius_m = float(np.mean([
        pre["wheel_proxy_candidates"][k]["proxy_radius_stage_units"] * mpu
        for k in ("drive_FL", "drive_FR", "drive_RL", "drive_RR")
    ]))

    ctx = omni.usd.get_context()
    timeline = omni.timeline.get_timeline_interface()

    def open_stage():
        timeline.stop()
        for _ in range(3):
            simulation_app.update()
        if not ctx.open_stage(str(input_path)):
            raise RuntimeError(f"Failed to open {input_path}")
        for _ in range(8):
            simulation_app.update()
        stage = ctx.get_stage()
        if stage is None:
            raise RuntimeError("No stage after open_stage")
        return stage

    def init_robot(stage):
        robot = SingleArticulation(
            prim_path=cfg["articulation_root"],
            name="sentry_stage5d",
            reset_xform_properties=False,
        )
        timeline.play()
        for _ in range(30):
            simulation_app.update()
        robot.initialize()
        for _ in range(10):
            simulation_app.update()
        if robot.num_dof != 11:
            raise RuntimeError(f"Expected 11 DOF, got {robot.num_dof}")
        return robot

    def step(n):
        for _ in range(int(n)):
            simulation_app.update()

    def base_frame_measure(stage):
        base = stage.GetPrimAtPath(cfg["articulation_root"])
        xc = UsdGeom.XformCache(Usd.TimeCode.Default())
        m = xc.GetLocalToWorldTransform(base)
        o = m.Transform(Gf.Vec3d(0.0, 0.0, 0.0))
        xp = m.Transform(Gf.Vec3d(1.0, 0.0, 0.0))
        yp = m.Transform(Gf.Vec3d(0.0, 1.0, 0.0))
        x2 = normalize2([float(xp[0]-o[0]), float(xp[1]-o[1])])
        y2 = normalize2([float(yp[0]-o[0]), float(yp[1]-o[1])])
        return {
            "position_m": np.array([float(o[0])*mpu, float(o[1])*mpu, float(o[2])*mpu]),
            "x_world_xy": x2,
            "y_world_xy": y2,
        }

    def wheel_geometry_in_base(stage, drive_path):
        xc = UsdGeom.XformCache(Usd.TimeCode.Default())
        base = stage.GetPrimAtPath(cfg["articulation_root"])
        drive = stage.GetPrimAtPath(drive_path)
        bw = xc.GetLocalToWorldTransform(base)
        dw = xc.GetLocalToWorldTransform(drive)
        binv = bw.GetInverse()

        do = dw.Transform(Gf.Vec3d(0.0, 0.0, 0.0))
        dy = dw.Transform(Gf.Vec3d(0.0, 1.0, 0.0))
        do_b = binv.Transform(do)
        dy_b = binv.Transform(dy)

        axle = np.array([
            float(dy_b[0]-do_b[0]),
            float(dy_b[1]-do_b[1]),
            float(dy_b[2]-do_b[2]),
        ], dtype=np.float64)
        axle /= np.linalg.norm(axle)

        # Positive wheel angular velocity is around drive local +Y.
        # For ground contact with +Z up, positive rolling direction is axle x up.
        roll = np.cross(axle, np.array([0.0, 0.0, 1.0]))
        heading = math.atan2(float(roll[1]), float(roll[0]))

        pos = np.array([
            float(do_b[0])*mpu,
            float(do_b[1])*mpu,
            float(do_b[2])*mpu,
        ])
        return heading, pos, axle.tolist()

    modules = cfg["modules"]

    # ------------------------------------------------------------------
    # A. Runtime-only isolated steer calibration.
    # ------------------------------------------------------------------
    stage = open_stage()
    scene = UsdPhysics.Scene.Get(stage, cfg["physics_scene"])
    if not scene or not scene.GetPrim().IsValid():
        raise RuntimeError("Missing PhysicsScene")
    scene.GetGravityMagnitudeAttr().Set(0.0)

    ground = stage.GetPrimAtPath(cfg["ground_path"])
    ground_col = UsdPhysics.CollisionAPI(ground)
    ground_col.GetCollisionEnabledAttr().Set(False)

    robot = init_robot(stage)
    dof_index = {name: int(robot.get_dof_index(name)) for name in robot.dof_names}

    # Force exact zero state for a clean geometric calibration.
    robot.set_joint_positions(np.zeros(robot.num_dof, dtype=np.float32))
    robot.set_joint_velocities(np.zeros(robot.num_dof, dtype=np.float32))
    step(cfg["calibration"]["settle_frames"])

    def command_pos(name, target):
        robot.apply_action(
            ArticulationAction(
                joint_positions=np.array([float(target)], dtype=np.float32),
                joint_indices=np.array([dof_index[name]], dtype=np.int32),
            )
        )

    def command_vel(name, target):
        robot.apply_action(
            ArticulationAction(
                joint_velocities=np.array([float(target)], dtype=np.float32),
                joint_indices=np.array([dof_index[name]], dtype=np.int32),
            )
        )

    for mod in modules.values():
        command_vel(mod["drive_joint"], 0.0)
        command_pos(mod["steer_joint"], 0.0)
    step(cfg["calibration"]["settle_frames"])

    calibration = {}
    probe_rad = math.radians(float(cfg["calibration"]["steer_probe_deg"]))
    min_heading = math.radians(float(cfg["calibration"]["minimum_heading_change_deg"]))

    print("Stage 5D automatic swerve calibration:", flush=True)
    print("  mode: gravity=0, ground collision disabled (runtime only)", flush=True)

    for module_name, mod in modules.items():
        drive_path = mapping[mod["drive_link_key"]]
        h0, pos0, axle0 = wheel_geometry_in_base(stage, drive_path)

        command_pos(mod["steer_joint"], probe_rad)
        step(cfg["calibration"]["probe_frames"])
        q = float(robot.get_joint_positions()[dof_index[mod["steer_joint"]]])
        h1, _, _ = wheel_geometry_in_base(stage, drive_path)
        dh = wrap_pi(h1 - h0)

        if abs(dh) < min_heading:
            raise RuntimeError(
                f"{module_name} steer calibration heading change too small: "
                f"{math.degrees(dh):.3f} deg"
            )
        steer_sign = 1.0 if (dh / q) > 0.0 else -1.0

        command_pos(mod["steer_joint"], 0.0)
        step(cfg["calibration"]["settle_frames"])

        calibration[module_name] = {
            "zero_positive_roll_heading_rad": h0,
            "zero_positive_roll_heading_deg": math.degrees(h0),
            "steer_positive_heading_sign": steer_sign,
            "module_position_base_m": pos0.tolist(),
            "drive_local_y_axis_base": axle0,
            "probe_joint_position_rad": q,
            "probe_heading_change_deg": math.degrees(dh),
        }

        print(
            f"  {module_name}: pos=({pos0[0]:+.4f},{pos0[1]:+.4f}) m "
            f"zeroHeading={math.degrees(h0):+.2f}° "
            f"steerSign={steer_sign:+.0f}",
            flush=True,
        )

    timeline.stop()
    for _ in range(4):
        simulation_app.update()

    # ------------------------------------------------------------------
    # B. Reopen the pristine Stage5D: normal gravity + ground.
    # ------------------------------------------------------------------
    stage = open_stage()
    robot = init_robot(stage)
    dof_index = {name: int(robot.get_dof_index(name)) for name in robot.dof_names}

    scene = UsdPhysics.Scene.Get(stage, cfg["physics_scene"])
    gm = float(scene.GetGravityMagnitudeAttr().Get())
    ground = stage.GetPrimAtPath(cfg["ground_path"])
    ground_enabled = bool(UsdPhysics.CollisionAPI(ground).GetCollisionEnabledAttr().Get())

    print("", flush=True)
    print("Stage 5D normal-contact runtime:", flush=True)
    print(f"  gravityMagnitude={gm:.3f} stage-units/s^2", flush=True)
    print(f"  groundCollisionEnabled={ground_enabled}", flush=True)
    print(f"  wheelRadius={radius_m*1000.0:.3f} mm", flush=True)

    if gm <= 1000.0 or not ground_enabled:
        raise RuntimeError("Normal-contact Stage5D did not restore gravity/ground.")

    # Let the 20mm Stage5B drop complete before chassis commands.
    step(cfg["runtime"]["ground_settle_frames"])

    def command_many_positions(targets):
        names = list(targets.keys())
        robot.apply_action(
            ArticulationAction(
                joint_positions=np.array([targets[n] for n in names], dtype=np.float32),
                joint_indices=np.array([dof_index[n] for n in names], dtype=np.int32),
            )
        )

    def command_many_velocities(targets):
        names = list(targets.keys())
        robot.apply_action(
            ArticulationAction(
                joint_velocities=np.array([targets[n] for n in names], dtype=np.float32),
                joint_indices=np.array([dof_index[n] for n in names], dtype=np.int32),
            )
        )

    def solve_swerve(vx, vy, wz):
        steer_targets = {}
        wheel_targets = {}
        diagnostic = {}

        for module_name, mod in modules.items():
            cal = calibration[module_name]
            x, y, _ = cal["module_position_base_m"]
            wx = float(vx) - float(wz) * float(y)
            wy = float(vy) + float(wz) * float(x)
            speed = math.hypot(wx, wy)

            if speed < 1e-8:
                desired_heading = cal["zero_positive_roll_heading_rad"]
                joint_target = 0.0
                wheel_omega = 0.0
            else:
                desired_heading = math.atan2(wy, wx)
                delta = wrap_pi(desired_heading - cal["zero_positive_roll_heading_rad"])
                speed_sign = 1.0

                # Swerve optimization: never demand >90° steer if reversing the wheel
                # can represent the same planar wheel velocity.
                if delta > math.pi / 2.0:
                    delta -= math.pi
                    speed_sign = -1.0
                elif delta < -math.pi / 2.0:
                    delta += math.pi
                    speed_sign = -1.0

                joint_target = (
                    cal["steer_positive_heading_sign"] * delta
                )
                wheel_omega = speed_sign * speed / radius_m

            steer_targets[mod["steer_joint"]] = joint_target
            wheel_targets[mod["drive_joint"]] = wheel_omega
            diagnostic[module_name] = {
                "wheel_velocity_body_m_s": [wx, wy],
                "desired_heading_deg": math.degrees(desired_heading),
                "steer_target_deg": math.degrees(joint_target),
                "wheel_target_rad_s": wheel_omega,
            }

        return steer_targets, wheel_targets, diagnostic

    def stop_wheels():
        command_many_velocities({
            mod["drive_joint"]: 0.0 for mod in modules.values()
        })
        step(cfg["runtime"]["stop_frames"])

    def displacement_result(start, end):
        dxy = end["position_m"][:2] - start["position_m"][:2]
        xb = start["x_world_xy"]
        yb = start["y_world_xy"]
        dx_body = float(np.dot(dxy, xb))
        dy_body = float(np.dot(dxy, yb))
        ex = end["x_world_xy"]
        yaw_delta = math.atan2(
            float(xb[0]*ex[1] - xb[1]*ex[0]),
            float(np.dot(xb, ex)),
        )
        return dx_body, dy_body, yaw_delta, float(np.linalg.norm(dxy))

    def evaluate_case(name, dx, dy, dyaw, translation):
        a = cfg["acceptance"]
        dyaw_deg = math.degrees(dyaw)

        if name == "straight":
            return bool(
                dx >= a["straight_min_forward_m"]
                and abs(dy) <= max(0.025, abs(dx) * a["straight_max_lateral_ratio"])
                and abs(dyaw_deg) <= a["straight_max_abs_yaw_deg"]
            )
        if name == "lateral":
            return bool(
                dy >= a["lateral_min_lateral_m"]
                and abs(dx) <= max(0.025, abs(dy) * a["lateral_max_forward_ratio"])
                and abs(dyaw_deg) <= a["lateral_max_abs_yaw_deg"]
            )
        if name == "diagonal":
            return bool(
                dx >= a["diagonal_min_forward_m"]
                and dy >= a["diagonal_min_lateral_m"]
                and abs(dyaw_deg) <= a["diagonal_max_abs_yaw_deg"]
            )
        if name == "rotate":
            return bool(
                dyaw_deg >= a["rotate_min_abs_yaw_deg"]
                and translation <= a["rotate_max_translation_m"]
            )
        raise RuntimeError(f"Unknown test case {name}")

    case_results = {}
    for test in cfg["tests"]:
        name = test["name"]
        vx = float(test["vx_m_s"])
        vy = float(test["vy_m_s"])
        wz = float(test["wz_rad_s"])

        steer_targets, wheel_targets, kine = solve_swerve(vx, vy, wz)

        # First align all four modules simultaneously while wheels are stopped.
        stop_wheels()
        command_many_positions(steer_targets)
        step(cfg["runtime"]["steer_settle_frames"])

        q = np.asarray(robot.get_joint_positions(), dtype=np.float64)
        steer_errors = {}
        steer_pass = True
        for module_name, mod in modules.items():
            idx = dof_index[mod["steer_joint"]]
            actual = float(q[idx])
            target = float(steer_targets[mod["steer_joint"]])
            err_deg = abs(math.degrees(wrap_pi(actual-target)))
            steer_errors[module_name] = {
                "target_deg": math.degrees(target),
                "actual_deg": math.degrees(actual),
                "error_deg": err_deg,
            }
            steer_pass &= err_deg <= float(cfg["runtime"]["max_steer_error_deg"])

        start = base_frame_measure(stage)
        command_many_velocities(wheel_targets)
        step(cfg["runtime"]["motion_frames"])
        stop_wheels()
        end = base_frame_measure(stage)

        dx, dy, dyaw, translation = displacement_result(start, end)
        motion_pass = evaluate_case(name, dx, dy, dyaw, translation)
        passed = bool(steer_pass and motion_pass)

        case_results[name] = {
            "command": {"vx_m_s": vx, "vy_m_s": vy, "wz_rad_s": wz},
            "kinematics": kine,
            "steer_tracking": steer_errors,
            "steer_tracking_pass": steer_pass,
            "body_displacement_m": {"x": dx, "y": dy},
            "yaw_delta_deg": math.degrees(dyaw),
            "translation_norm_m": translation,
            "motion_acceptance_pass": motion_pass,
            "pass": passed,
        }

        print("", flush=True)
        print(
            f"[{name.upper()}] dx={dx:+.4f} m dy={dy:+.4f} m "
            f"dYaw={math.degrees(dyaw):+.2f}° "
            f"steer={'PASS' if steer_pass else 'FAIL'} "
            f"motion={'PASS' if motion_pass else 'FAIL'} "
            f"=> {'PASS' if passed else 'FAIL'}",
            flush=True,
        )

    stop_wheels()
    timeline.pause()

    pass_count = sum(1 for v in case_results.values() if v["pass"])
    all_pass = pass_count == len(case_results)

    report = {
        "source_stage5d": str(input_path),
        "wheel_radius_m": radius_m,
        "calibration": calibration,
        "normal_contact": {
            "gravity_magnitude_stage_units_per_s2": gm,
            "ground_collision_enabled": ground_enabled,
        },
        "test_results": case_results,
        "pass_count": pass_count,
        "expected_count": len(case_results),
        "runtime_validation_all_pass": all_pass,
        "note": (
            "This is the first low-speed swerve baseline. Passing proves coordinated "
            "ground-contact motion, not final dynamics/controller fidelity."
        ),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("", flush=True)
    print(f"Stage 5D RESULT: {pass_count}/{len(case_results)} motion cases PASS", flush=True)
    print(f"[OK] report: {report_path}", flush=True)

    if not all_pass:
        raise RuntimeError(
            f"Stage5D runtime motion validation failed: {pass_count}/{len(case_results)}"
        )

    print("[OK] runtime_validation_all_pass=true", flush=True)
    return 0

code = 1
try:
    code = main()
except BaseException as exc:
    print(f"[FATAL] Stage5D runtime failed: {type(exc).__name__}: {exc}", flush=True)
    traceback.print_exc()
    code = 1
finally:
    try:
        simulation_app.close()
    except Exception:
        pass

raise SystemExit(code)
