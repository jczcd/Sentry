# Artifact manifest

Large or copyrighted artifacts were intentionally not committed. This manifest records what was observed during consolidation.

## Source and transfer artifacts

| Artifact | Size | SHA256 | Integrity | Repository treatment |
|---|---:|---|---|---|
| `Sentry_original_complete_verified.zip` | 117,340,483 B | `e5360dd349d095ff2f2dc5be971ee04c2a10b9032d2e718c344b7cbe64332cb6` | ZIP test PASS | not committed; exceeds normal GitHub file limit |
| embedded `Sentry (1) (1).STEP` | 424,958,367 B | `e4ffba09af148210483a0ef586b8a0332cb9ac472b8747fb6191a5fd29e97eac` | streamed SHA verified | not committed |
| `Sentinel_Migration_4090_20260818.zip` | 18,692 B | `d6909e384c41f682b226d8880fba8240a945bfad9947fead52121a218e6f2bed` | ZIP test PASS | extracted scripts committed under `tools/migration/4090` |
| `Sentinel_5090_Migration_Kit_20260817.zip` | 7,696 B | `0ded0abd7d9034ccf45ef4b30d8deb1558c6b6f16c86e33a1c2680e05f59fc42` | ZIP test PASS | extracted scripts committed under `tools/migration/5090` |
| `Sentinel_Work_Handoff_HighGPU_20260817.zip` | 6,571,959 B | `eeb74d19e067cf5d8de1c4a6a9a868c0ae1b61d4a11ed78e466385620429c111` | ZIP test PASS | text handoff committed; manuals/private chat screenshot omitted |
| `Sentry_Stage5D_OneCommand.zip` | 11,825 B | `df2ac7958fe742ac936ec1b554f165acfd9b74e0d3ab973a521bb9c112253b62` | ZIP test PASS | extracted scripts committed under `tools/isaac/stage5d_builder` |
| available `Sentinel_Recovery_4090_20260818.zip` copy | 43,805,696 B | `f54cb4ce18b61495ad78131a035d87442e072cbfad08eb14501d8287b0b53378` | central directory missing | not committed or trusted |
| available `Sentry_IsaacSim_Linux.zip` copy | 18,270,208 B | `3643cc77f97bc4043783a1c829d3e7164ff08d1cc0538391b6ac89aaa67e4383` | central directory missing | not committed or trusted |

The incomplete copies must not be repaired by guessing. Re-download from the durable source or rebuild from verified source inputs.

## Known model identities

| Model | SHA256 | Status |
|---|---|---|
| historical Stage5C `Sentry_stage5c_joint_drives.usda` | `ffa8ecbf83a047f05cc1e4aeb3005b1fa8c09da651c273bb4a4d03a62a0dcacc` | old protected checkpoint; not present |
| V3 recommended raw Variant A | `3d60faa31c2b183ce260a563575bf57e6707aeb7e34889bceb956f4880fffc67` | reported candidate; not present; manual review required |

## Official references omitted

- RoboMaster 2026 RMUL competition rules V1.2.0;
- RoboMaster 2026 robot construction specification V1.3.0;
- RoboMaster development board C schematics, placement drawings, manuals, and tutorial;
- Livox Mid-360 quick-start guide and user manual;
- remote-desktop installation guide.

Their engineering page references are summarized in `docs/reference/RULES_AND_HARDWARE.md`. Obtain current official copies from the publisher.

## Other intentional omissions

- Isaac Sim installers and caches;
- ROS `build/`, `install/`, and `log/` trees;
- generated USD and screenshots that were not part of the verified latest V3 snapshot;
- raw terminal/chat transcripts containing internal addresses or private UI;
- cloned third-party repositories;
- rosbag, virtual environments, node modules, and crash dumps.
