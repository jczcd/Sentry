# Sentry Stage 5D — One Command Swerve Motion Baseline

> Historical tool warning: this repository does not contain a currently valid Stage5C or prerequisite reports. Do not run this tool against V2 or treat its historical 4/4 result as current evidence. Complete the V3 visual and articulation Gates first.

Input:

- `output/Sentry_stage5c_joint_drives.usda`
- `output/stage4_report.json`
- `output/stage5b_preflight.json`

Formal command:

```bash
./run_stage5d.sh
```

The command automatically:

1. Reads the exact Stage5B wheel collision radius.
2. Creates a Stage5D overlay.
3. Applies one diagnostic tire/ground physics material.
4. Strengthens only the four steer drives and four wheel velocity drives.
5. Starts an isolated runtime calibration:
   - gravity = 0
   - ground collision = OFF
   - measures each module's actual zero rolling heading
   - probes +10 deg steer to identify the physical sign of each steer DOF
6. Reopens the pristine Stage5D.
7. Restores the normal Stage5B gravity and ground.
8. Lets the robot settle.
9. Solves four-swerve inverse kinematics.
10. Uses shortest-path steer optimization (180 deg heading flip + wheel-speed reversal).
11. Runs four low-speed ground tests:
    - straight
    - lateral
    - diagonal
    - in-place rotate
12. Measures chassis displacement and yaw from the actual USD/PhysX transforms.
13. Reads `stage5d_runtime_report.json` before allowing the shell to print PASS.

Optional preflight:

```bash
./run_stage5d.sh --dry-run
```

Outputs:

- `output/Sentry_stage5d_swerve.usda`
- `output/stage5d_build_report.json`
- `output/stage5d_runtime_report.json`

Important:
Stage5D proves only the first low-speed coordinated swerve baseline.
Friction coefficients, masses and actuator gains are still diagnostic values and
must not be treated as final RoboMaster physical parameters or RL training truth.
