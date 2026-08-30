# Sentinel project state

Consolidated: 2026-08-30

## Executive status

| Area | Current status | Meaning |
|---|---|---|
| Repository | `INITIAL_CONSOLIDATION` | Historical assets and the Phase 1 shared core are now collected in one repository. |
| Canonical CAD source | `ARCHIVE_VERIFIED_NOT_COMMITTED` | The source ZIP and embedded STEP pass integrity checks, but exceed normal Git limits. |
| Model V2 | `INVALID_VISUAL_ASSEMBLY` | The earlier all-PASS conclusion was withdrawn after human GUI inspection found an exploded/radial assembly. |
| Model V3 raw candidate | `MANUAL_VISUAL_APPROVAL_REQUIRED` | Independent OCCT/XDE evidence selected HOOPS Variant A with `globalXforms=false`; human Isaac review is still required. |
| Current Stage5C/Stage5D | `NOT_RECOVERED_IN_THIS_REPOSITORY` | No current valid Stage5C/Stage5D USD or runtime report is present here. |
| Historical Stage5D | `HISTORICAL_ONLY` | Straight/lateral/diagonal/rotate were reported 4/4 PASS on an older baseline; this is not current Gate evidence. |
| Swerve common core | `HOST_TESTABLE` | C++17 IK/FK, steering optimization, zero hold, and saturation are present. Hardware geometry remains unmeasured. |
| ROS/Isaac integration | `CONTRACT_ONLY` | Interfaces and ownership are documented; the full live workspace was not available to commit. |
| STM32 integration | `DESIGN_ONLY` | The MCU boundary, state machine, watchdog, and protocol are specified but firmware is not yet implemented here. |

## Latest trustworthy model decision

The latest recovered transcript, dated 2026-08-22, records:

- canonical STEP SHA256: `e4ffba09af148210483a0ef586b8a0332cb9ac472b8747fb6191a5fd29e97eac`;
- one root product and 136 assembly occurrences validated independently with OpenCascade/XDE;
- HOOPS Variant A, `globalXforms=false`: `PASS_RECOMMENDED_RAW_CANDIDATE`;
- HOOPS Variant B, `globalXforms=true`: `FAIL_EXPLODED_VISUAL_ASSEMBLY`;
- recommended raw V3 USD SHA256: `3d60faa31c2b183ce260a563575bf57e6707aeb7e34889bceb956f4880fffc67`;
- final state: `MANUAL_VISUAL_APPROVAL_REQUIRED`.

The actual V3 scripts, reports, screenshots, and USD were not present in the available workspace snapshot. Their known names are preserved in `docs/history/TIMELINE.md`; do not invent or regenerate them without the original source or a new evidence run.

## Historical checkpoint that must not be confused with current state

An earlier project handoff records:

- 11 revolute DOF: four steer, four drive, `yaw_big`, `yaw_small`, `pitch`;
- articulation root `/Sentry/Sentry_raw/base_link` under wrapper `/Sentry`;
- historical Stage5C SHA256 `ffa8ecbf83a047f05cc1e4aeb3005b1fa8c09da651c273bb4a4d03a62a0dcacc`;
- historical Stage5D straight/lateral/diagonal/rotate 4/4 PASS;
- command limits `|vx| <= 0.20 m/s`, `|vy| <= 0.20 m/s`, `|wz| <= 0.60 rad/s` and command timeout `0.5 s` used as a diagnostic baseline;
- `/sentry/odom`, `/tf`, and `/joint_states` reported around 50 Hz;
- a deferred `/tf_static` issue caused by dual-parent proposals for `base_link`.

These facts remain useful for reconstruction, but the later visual invalidation means they cannot certify the current model.

## Current blockers

1. Open the exact V3 Variant A candidate in Isaac Sim and record explicit human visual approval or rejection.
2. Recover the latest V3 source scripts/reports from the original machine, if still available.
3. Measure physical swerve geometry, wheel radius, gear ratios, encoder directions, and steering zeros.
4. Recreate a valid semantic-link and articulation baseline only after visual approval.
5. Re-run Stage5C drive tests and Stage5D 4/4 tests on the newly accepted model.
6. Implement and verify the ROS virtual lower controller and real hardware bridge against the same interface.

## Next Gate

The next allowed Gate is model visual approval, followed by Phase 1 swerve verification. Mid-360, Point-LIO, Nav2, behavior trees, and RL remain downstream work.
