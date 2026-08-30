# Recovery and development timeline

This chronology separates historical progress from currently valid evidence.

## 2026-08-15 - Historical Stage5D and sensor work

- Earlier project logs reported Stage5D straight, lateral, diagonal, and rotation tests 4/4 PASS.
- ROS topics, safety limits, sensor fields, Point-LIO parser behavior, and TF ownership were investigated.
- Mid-360 simulation was described as a geometric baseline, not hardware-equivalent scan truth.
- A global 200 Hz PhysX experiment was rejected after RTX LiDAR device loss/crashes.

Status today: useful reconstruction evidence, not a current model PASS.

## 2026-08-17 - High-GPU handoff

- A handoff package recorded old-machine paths, expected Stage5C hash, migration steps, and next tasks.
- The package expected the live project to be packed separately; it was not itself the full workspace.
- Text records are retained under `archive/handoff/2026-08-17-highgpu`.

## 2026-08-18 - Recovery package audit

- Audit concluded that the available package was a recovery kit, not the original ROS/Isaac workspace.
- It contained CAD import scripts, a Stage5D builder, handoff documents, and migration tools.
- Original Stage5C, Stage5D, integration nodes, and runtime reports were absent.
- Therefore the old Stage5D 4/4 result could not certify the recovered system.

## 2026-08-19 - Visual invalidation during reconstruction

- Human GUI inspection found the converted/recovered assembly spatially exploded or radial.
- Earlier visual PASS statements were withdrawn.
- Dependent raw USD, wrapper, stage, and recovery outputs were marked invalid for physics.
- Subsequent work focused on source integrity and independent CAD/transform diagnosis.

## 2026-08-22 - V2 withdrawn, V3 raw candidate selected

- An automated V2 validation temporarily reported geometry, joints, PhysX, and packaging PASS.
- Human inspection overruled it: V2 and its FULL package were marked `INVALID_VISUAL_ASSEMBLY`.
- The canonical STEP hash was confirmed as `e4ffba09af148210483a0ef586b8a0332cb9ac472b8747fb6191a5fd29e97eac`.
- OpenCascade/XDE independently found one root and 136 assembly occurrences, with four wheel modules and a continuous gimbal chain.
- A controlled HOOPS A/B comparison selected:
  - Variant A, `globalXforms=false`: recommended;
  - Variant B, `globalXforms=true`: exploded and rejected.
- Latest state became `MANUAL_VISUAL_APPROVAL_REQUIRED`.

Known but unavailable V3 artifacts included:

- `tools/finalize_hoops_ab_v3.py`;
- `tools/run_v3_visual_review.sh`;
- `reports/INDEPENDENT_CAD_SOURCE_VERDICT_V3.md`;
- `reports/HOOPS_AB_GEOMETRY_V3.json`;
- `reports/V3_RAW_VISUAL_REVIEW_REQUIRED.md`;
- `Sentry_IsaacSim_Linux/output/model_baseline_v3/raw_conversion/variant_a_global_xforms_false/Sentry_raw_v3_A.usd`.

Do not reconstruct those files from transcript fragments. Recover the originals or perform a new reproducible run.

## 2026-08-27 - Harness master framework

- The project was re-scoped around Phase 1 swerve foundations, a single Mid-360, one NUC, an STM32 lower controller, traditional baselines, independent safety, and only later RL.
- The framework is preserved as `HARNESS_RMUL_SENTRY_MASTER_FRAMEWORK.md`.

## 2026-08-30 - GitHub consolidation

- Historical tools and handoffs were collected without large binaries or official manuals.
- Current truth and invalidations were promoted to top-level documentation.
- A hardware-independent C++17 swerve core and host tests were added.
- ROS/MCP, Sim-to-Real, TF, control ownership, lower-controller, rules, and Gate contracts were made explicit.
