# Sentry → Isaac Sim (Linux)

> Recovery note: the large `source/Sentry.step` asset is intentionally not stored in Git. Supply a separately verified source whose SHA is recorded in `docs/history/ARTIFACT_MANIFEST.md`. The latest project evidence selected `globalXforms=false`; review `PROJECT_STATE.md` before conversion.

This package originally accompanied a supplied `Sentry.step` assembly and contains an Isaac Sim-native STEP → USD conversion pipeline.

## Detected robot link names in the STEP

The STEP product table already contains useful semantic names, including:

- `base_link`
- `steer_FL_link_M3508 Ver`, `drive_FL_link`
- `steer_FR_link_M3508 Ver`, `drive_FR_link`
- `steer_RL-link_M3508 Ver`, `drive_RL_link`
- `steer_RR_link_M3508 Ver`, `drive_RR_link`
- `yaw1_link`, `yaw2_link`, `yaw_3link`

This is useful because the four swerve steering/drive links and the yaw stages can be found by name after CAD conversion instead of inferred from geometry.

## Recommended environment

- Linux
- NVIDIA Isaac Sim 6.x
- CAD/HOOPS Core converter extension available
- Sufficient RAM for a large CAD assembly

## One-command conversion

From this folder:

```bash
chmod +x run_convert.sh
./run_convert.sh
```

If Isaac Sim is installed somewhere else:

```bash
export ISAAC_SIM_PATH=/path/to/isaac-sim
./run_convert.sh
```

or:

```bash
export ISAAC_SIM_PYTHON=/path/to/isaac-sim/python.sh
./run_convert.sh
```

The conversion defaults to tessellation LOD 1 to keep this large assembly manageable. Increase only if you need more visual detail:

```bash
./run_convert.sh --tess-lod 2
```

## Output

After a successful run:

```text
output/
├── Sentry_raw.usd          # HOOPS CAD conversion result
├── Sentry.usda             # lightweight wrapper, open this in Isaac Sim
├── conversion_result.json  # conversion metadata
└── link_mapping.json       # name-based semantic-link paths
```

Open `output/Sentry.usda` in Isaac Sim with **File → Open**.

## Important: this package does NOT guess joint axes

The CAD converter can preserve assembly geometry and names, but a STEP assembly does not provide enough reliable robotics semantics to blindly author the final PhysX articulation. Do not guess:

- revolute joint axis direction
- joint origin
- limits
- mass/inertia
- which of `yaw_3link` / pitch-related parts should be the pitch stage

The generated `link_mapping.json` is intended as the input to the next physics-authoring pass.

For the final robot physics tree, keep these independent DOFs:

```text
base_link
├── steer_FL -> drive_FL
├── steer_FR -> drive_FR
├── steer_RL -> drive_RL
├── steer_RR -> drive_RR
└── yaw_big -> yaw_small -> (yaw_3 / pitch stage)
```

Only merge fixed visual geometry *within* one link. Never merge across those DOF boundaries.

## If HOOPS Core is missing

Open Isaac Sim and check **Window → Extensions** for the CAD / HOOPS converter extensions. You can also run:

```bash
/path/to/isaac-sim/python.sh scripts/check_environment.py
```

## Why raw CAD and simulation layers are separated

The original CAD source is preserved under `source/`. The USD output is created separately so later mesh optimization, colliders, rigid bodies, joints, ROS 2 graphs and Isaac Lab configuration can be layered on without damaging the source asset.
