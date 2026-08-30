#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import argparse
import json
import os
import traceback

def package_root():
    return Path(__file__).resolve().parent.parent

def parse_args():
    root = package_root()
    p = argparse.ArgumentParser()
    p.add_argument("--config", default=str(root / "config" / "stage5d_swerve.json"))
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--report", default=str(root / "output" / "stage5d_build_report.json"))
    return p.parse_args()

args = parse_args()
root = package_root()
cfg_path = Path(args.config).resolve()
cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

input_path = (root / cfg["input_stage"]).resolve()
output_path = (root / cfg["output_stage"]).resolve()
s4_report_path = (root / cfg["stage4_report"]).resolve()
s5b_preflight_path = (root / cfg["stage5b_preflight"]).resolve()
report_path = Path(args.report).resolve()

for p in (input_path, s4_report_path, s5b_preflight_path):
    if not p.exists():
        raise SystemExit(f"Required file not found: {p}")

from isaacsim import SimulationApp
simulation_app = SimulationApp({"headless": True})

def main():
    from pxr import Usd, UsdGeom, UsdPhysics, UsdShade, Sdf

    s4 = json.loads(s4_report_path.read_text(encoding="utf-8"))
    pre = json.loads(s5b_preflight_path.read_text(encoding="utf-8"))
    mapping = s4["resolved_mapping"]

    stage = Usd.Stage.Open(str(input_path))
    if stage is None:
        raise RuntimeError(f"Cannot open Stage5C: {input_path}")

    up = str(UsdGeom.GetStageUpAxis(stage))
    mpu = float(UsdGeom.GetStageMetersPerUnit(stage))
    if up != "Z" or abs(mpu - 0.001) > 1e-12:
        raise RuntimeError(f"Invalid stage metrics: upAxis={up}, metersPerUnit={mpu}")

    # Extract the exact Stage5B wheel-proxy radius instead of duplicating a magic number.
    radii_stage = []
    for key in ("drive_FL", "drive_FR", "drive_RL", "drive_RR"):
        radii_stage.append(
            float(pre["wheel_proxy_candidates"][key]["proxy_radius_stage_units"])
        )
    radius_stage_mean = sum(radii_stage) / len(radii_stage)
    radius_m = radius_stage_mean * mpu

    # Validate expected collider/joint inputs.
    module_checks = {}
    for name, mod in cfg["modules"].items():
        steer_path = Sdf.Path("/Sentry/PhysicsJoints").AppendChild(mod["steer_joint"])
        drive_path = Sdf.Path("/Sentry/PhysicsJoints").AppendChild(mod["drive_joint"])
        steer = UsdPhysics.RevoluteJoint.Get(stage, steer_path)
        drive = UsdPhysics.RevoluteJoint.Get(stage, drive_path)
        wheel_col = Sdf.Path(mapping[mod["drive_link_key"]]).AppendChild("Stage5B_WheelCollider")
        wheel_col_prim = stage.GetPrimAtPath(wheel_col)

        module_checks[name] = {
            "steer_joint": str(steer_path),
            "drive_joint": str(drive_path),
            "wheel_collider": str(wheel_col),
            "steer_valid": bool(steer and steer.GetPrim().IsValid()),
            "drive_valid": bool(drive and drive.GetPrim().IsValid()),
            "wheel_collider_valid": bool(wheel_col_prim and wheel_col_prim.IsValid()),
        }

    ground = stage.GetPrimAtPath(cfg["ground_path"])
    ground_ok = bool(
        ground
        and ground.IsValid()
        and ground.HasAPI(UsdPhysics.CollisionAPI)
    )
    articulation = stage.GetPrimAtPath(cfg["articulation_root"])
    art_ok = bool(
        articulation
        and articulation.IsValid()
        and articulation.HasAPI(UsdPhysics.ArticulationRootAPI)
    )
    modules_ok = all(
        c["steer_valid"] and c["drive_valid"] and c["wheel_collider_valid"]
        for c in module_checks.values()
    )

    print("Stage 5D preflight:", flush=True)
    print(f"  input={input_path}", flush=True)
    print(f"  upAxis={up}, metersPerUnit={mpu}", flush=True)
    print(f"  wheel radius from Stage5B={radius_m*1000.0:.3f} mm", flush=True)
    print(f"  articulation root={'PASS' if art_ok else 'FAIL'}", flush=True)
    print(f"  ground collider={'PASS' if ground_ok else 'FAIL'}", flush=True)
    for name, c in module_checks.items():
        print(
            f"  {name}: steer={'PASS' if c['steer_valid'] else 'FAIL'} "
            f"drive={'PASS' if c['drive_valid'] else 'FAIL'} "
            f"wheelCollider={'PASS' if c['wheel_collider_valid'] else 'FAIL'}",
            flush=True,
        )

    preflight_ok = art_ok and ground_ok and modules_ok
    if not preflight_ok:
        raise RuntimeError("Stage5D preflight failed.")

    if args.dry_run:
        report = {
            "mode": "dry_run",
            "source_stage5c": str(input_path),
            "wheel_radius_m": radius_m,
            "module_checks": module_checks,
            "articulation_root_pass": art_ok,
            "ground_pass": ground_ok,
            "validation_all_pass": preflight_ok,
        }
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print("[OK] Stage 5D dry-run passed.", flush=True)
        return 0

    if output_path.exists():
        output_path.unlink()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rel_source = os.path.relpath(str(input_path), str(output_path.parent))
    layer = Sdf.Layer.CreateNew(str(output_path))
    layer.subLayerPaths = [rel_source]
    layer.Save()

    out = Usd.Stage.Open(str(output_path))
    if out is None:
        raise RuntimeError(f"Cannot create Stage5D overlay: {output_path}")
    out.SetEditTarget(out.GetRootLayer())
    UsdGeom.SetStageUpAxis(out, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(out, mpu)
    sentry = out.GetPrimAtPath("/Sentry")
    if sentry and sentry.IsValid():
        out.SetDefaultPrim(sentry)

    # Debug tire/ground material. This is deliberately simple/isotropic for Stage5D.
    mat_cfg = cfg["physics_material"]
    mat = UsdShade.Material.Define(out, mat_cfg["path"])
    mat_api = UsdPhysics.MaterialAPI.Apply(mat.GetPrim())
    mat_api.CreateStaticFrictionAttr().Set(float(mat_cfg["static_friction"]))
    mat_api.CreateDynamicFrictionAttr().Set(float(mat_cfg["dynamic_friction"]))
    mat_api.CreateRestitutionAttr().Set(float(mat_cfg["restitution"]))

    def bind_physics_material(prim):
        # Special-purpose material binding relationship defined by USD Shade.
        rel = prim.CreateRelationship("material:binding:physics", custom=False)
        rel.SetTargets([mat.GetPath()])

    bound = []
    ground_out = out.GetPrimAtPath(cfg["ground_path"])
    bind_physics_material(ground_out)
    bound.append(str(ground_out.GetPath()))

    # Stronger on-ground diagnostic drive gains for steering/wheels only.
    steer_gain = cfg["drive_gains"]["steer"]
    wheel_gain = cfg["drive_gains"]["wheel"]

    for name, mod in cfg["modules"].items():
        steer_path = Sdf.Path("/Sentry/PhysicsJoints").AppendChild(mod["steer_joint"])
        drive_path = Sdf.Path("/Sentry/PhysicsJoints").AppendChild(mod["drive_joint"])

        steer_drive = UsdPhysics.DriveAPI.Get(out.GetPrimAtPath(steer_path), "angular")
        steer_drive.GetStiffnessAttr().Set(float(steer_gain["stiffness"]))
        steer_drive.GetDampingAttr().Set(float(steer_gain["damping"]))
        steer_drive.GetMaxForceAttr().Set(float(steer_gain["max_force"]))

        wheel_drive = UsdPhysics.DriveAPI.Get(out.GetPrimAtPath(drive_path), "angular")
        wheel_drive.GetStiffnessAttr().Set(float(wheel_gain["stiffness"]))
        wheel_drive.GetDampingAttr().Set(float(wheel_gain["damping"]))
        wheel_drive.GetMaxForceAttr().Set(float(wheel_gain["max_force"]))

        wheel_col = Sdf.Path(mapping[mod["drive_link_key"]]).AppendChild("Stage5B_WheelCollider")
        wheel_prim = out.GetPrimAtPath(wheel_col)
        bind_physics_material(wheel_prim)
        bound.append(str(wheel_col))

    out.GetRootLayer().Save()
    for _ in range(2):
        simulation_app.update()

    chk = Usd.Stage.Open(str(output_path))
    if chk is None:
        raise RuntimeError("Could not reopen Stage5D output")

    metrics_ok = (
        str(UsdGeom.GetStageUpAxis(chk)) == "Z"
        and abs(float(UsdGeom.GetStageMetersPerUnit(chk)) - mpu) < 1e-12
    )

    mat_chk = UsdPhysics.MaterialAPI.Get(chk, Sdf.Path(mat_cfg["path"]))
    mat_ok = bool(mat_chk and mat_chk.GetPrim().IsValid())
    if mat_ok:
        mat_ok &= abs(float(mat_chk.GetStaticFrictionAttr().Get()) - float(mat_cfg["static_friction"])) < 1e-6
        mat_ok &= abs(float(mat_chk.GetDynamicFrictionAttr().Get()) - float(mat_cfg["dynamic_friction"])) < 1e-6

    binding_ok = True
    for p in bound:
        prim = chk.GetPrimAtPath(p)
        rel = prim.GetRelationship("material:binding:physics")
        binding_ok &= bool(rel and [str(x) for x in rel.GetTargets()] == [mat_cfg["path"]])

    drive_ok = True
    for name, mod in cfg["modules"].items():
        steer_path = Sdf.Path("/Sentry/PhysicsJoints").AppendChild(mod["steer_joint"])
        drive_path = Sdf.Path("/Sentry/PhysicsJoints").AppendChild(mod["drive_joint"])
        sd = UsdPhysics.DriveAPI.Get(chk.GetPrimAtPath(steer_path), "angular")
        wd = UsdPhysics.DriveAPI.Get(chk.GetPrimAtPath(drive_path), "angular")
        drive_ok &= abs(float(sd.GetStiffnessAttr().Get()) - float(steer_gain["stiffness"])) < 1e-6
        drive_ok &= abs(float(wd.GetDampingAttr().Get()) - float(wheel_gain["damping"])) < 1e-6

    all_ok = bool(metrics_ok and mat_ok and binding_ok and drive_ok)

    report = {
        "source_stage5c": str(input_path),
        "output_stage5d": str(output_path),
        "wheel_radius_m": radius_m,
        "physics_material": mat_cfg,
        "physics_material_bound_prims": bound,
        "stage_metrics_validation_pass": metrics_ok,
        "physics_material_validation_pass": mat_ok,
        "binding_validation_pass": binding_ok,
        "drive_gain_validation_pass": drive_ok,
        "validation_all_pass": all_ok,
        "note": "Stage5D material/gains are diagnostic baselines, not final dynamics.",
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if not all_ok:
        raise RuntimeError(f"Stage5D post-save validation failed: {report_path}")

    print("", flush=True)
    print("[OK] Stage 5D build validation_all_pass=true", flush=True)
    print(f"[OK] Wheel radius={radius_m*1000.0:.3f} mm", flush=True)
    print(
        f"[OK] Tire/Ground friction static={mat_cfg['static_friction']} "
        f"dynamic={mat_cfg['dynamic_friction']}",
        flush=True,
    )
    print(f"[OK] Output: {output_path}", flush=True)
    print(f"[OK] Report: {report_path}", flush=True)
    return 0

code = 1
try:
    code = main()
except BaseException as exc:
    print(f"[FATAL] Stage5D build failed: {type(exc).__name__}: {exc}", flush=True)
    traceback.print_exc()
    code = 1
finally:
    try:
        simulation_app.close()
    except Exception:
        pass

raise SystemExit(code)
