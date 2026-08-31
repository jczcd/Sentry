from __future__ import annotations

import math
from pathlib import Path
import sys
import unittest

try:
    import numpy as np
except ModuleNotFoundError:  # Optional until the pinned upstream is fetched.
    np = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ros2_ws" / "src" / "sentinel_core"))
sys.path.insert(0, str(ROOT / "training" / "RMUC-OfflineRL"))

from sentinel_core import observation_schema as ours  # noqa: E402
try:
    from rm_rl.data import features as upstream  # noqa: E402
    from rm_rl.data import schema as schema  # noqa: E402
except ModuleNotFoundError:  # Keep the core workspace testable without vendoring RL.
    upstream = None  # type: ignore[assignment]
    schema = None  # type: ignore[assignment]


TYPE_MAP = (
    {
        ours.TYPE_HERO: schema.TYPE_HERO,
        ours.TYPE_ENGINEER: schema.TYPE_ENGINEER,
        ours.TYPE_INFANTRY3: schema.TYPE_INFANTRY3,
        ours.TYPE_INFANTRY4: schema.TYPE_INFANTRY4,
        ours.TYPE_AERIAL: schema.TYPE_AERIAL,
        ours.TYPE_SENTRY: schema.TYPE_SENTRY,
    }
    if schema is not None
    else {}
)


def upstream_entity(entity: ours.EntitySnapshot) -> upstream.Entity:
    one = lambda value: np.asarray([value], dtype=np.float32)
    return upstream.Entity(
        x=one(entity.x),
        y=one(entity.y),
        z=one(entity.z),
        hp=one(entity.hp),
        maxhp=one(entity.max_hp),
        yaw=one(math.degrees(entity.turret_yaw_rad)),
        power=one(entity.chassis_power_w),
        heat17=one(entity.heat_17),
        heat17_max=one(entity.heat_17_limit),
        heat42_max=one(entity.heat_42_limit),
        ammo17=one(entity.ammo_17_fired),
        coin_left=one(0.0),
        coin_total=one(0.0),
        vuln=one(float(entity.vulnerable)),
        alive=one(float(entity.alive and entity.present)),
    )


def make_entity(
    robot_type: int,
    team: int,
    x: float,
    y: float,
    *,
    ego: bool = False,
) -> ours.EntitySnapshot:
    return ours.EntitySnapshot(
        robot_type=robot_type,
        team=team,
        present=True,
        alive=True,
        visible=True,
        vulnerable=robot_type == ours.TYPE_HERO,
        x=x,
        y=y,
        z=0.3,
        turret_yaw_rad=0.37 if ego else -0.2,
        hp=ours.MAX_HP[robot_type] * 0.8,
        max_hp=ours.MAX_HP[robot_type],
        chassis_power_w=60.0,
        heat_17=35.0,
        heat_17_limit=260.0,
        heat_42_limit=240.0 if robot_type == ours.TYPE_HERO else 0.0,
        ammo_17_fired=23.0,
    )


class ObservationSchemaTest(unittest.TestCase):
    def build_snapshot(self, team: int) -> ours.BattleSnapshot:
        ego = make_entity(ours.TYPE_SENTRY, team, 7.0, 4.0, ego=True)
        enemy_team = ours.TEAM_BLUE if team == ours.TEAM_RED else ours.TEAM_RED
        allies = [
            make_entity(kind, team, 3.0 + kind, 1.0 + 0.5 * kind)
            for kind in ours.MOBILE_TYPES
        ]
        allies[-1] = ego
        enemies = [
            make_entity(kind, enemy_team, 18.0 + 0.3 * kind, 4.0 + kind)
            for kind in ours.MOBILE_TYPES
        ]
        return ours.BattleSnapshot(
            ego_team=team,
            ego_type=ours.TYPE_SENTRY,
            ego=ego,
            elapsed_s=1.0,
            remaining_s=449.0,
            allies=allies,
            enemies=enemies,
            own_base_hp=4200.0,
            own_base_max_hp=5000.0,
            own_outpost_hp=1200.0,
            own_outpost_max_hp=1500.0,
            enemy_base_hp=3900.0,
            enemy_base_max_hp=5000.0,
            enemy_outpost_hp=900.0,
            enemy_outpost_max_hp=1500.0,
            own_coin_left=120.0,
            own_coin_total=800.0,
            enemy_coin_total=700.0,
            team_prior=[0.1, 0.2, 0.3, -0.1, -0.2, -0.3],
        )

    def compare_with_upstream(self, team: int) -> None:
        snapshot = self.build_snapshot(team)
        camp = schema.CAMP_RED if team == ours.TEAM_RED else schema.CAMP_BLUE
        enemy_camp = schema.enemy_camp(camp)
        entities: dict[int, upstream.Entity] = {}
        for entity in snapshot.allies:
            entities[schema.robot_id(TYPE_MAP[entity.robot_type], camp)] = (
                upstream_entity(entity)
            )
        for entity in snapshot.enemies:
            entities[schema.robot_id(TYPE_MAP[entity.robot_type], enemy_camp)] = (
                upstream_entity(entity)
            )

        def building(
            robot_type: str,
            owner: str,
            hp: float,
            max_hp: float,
            coin_left: float,
            coin_total: float,
        ) -> None:
            one = lambda value: np.asarray([value], dtype=np.float32)
            entity = upstream.Entity(
                x=one(0.0),
                y=one(0.0),
                z=one(0.0),
                hp=one(hp),
                maxhp=one(max_hp),
                yaw=one(0.0),
                power=one(0.0),
                heat17=one(0.0),
                heat17_max=one(0.0),
                heat42_max=one(0.0),
                ammo17=one(0.0),
                coin_left=one(coin_left),
                coin_total=one(coin_total),
                vuln=one(0.0),
                alive=one(float(hp > 0.0)),
            )
            entities[schema.robot_id(robot_type, owner)] = entity

        building(
            schema.TYPE_BASE,
            camp,
            snapshot.own_base_hp,
            snapshot.own_base_max_hp,
            snapshot.own_coin_left,
            snapshot.own_coin_total,
        )
        building(
            schema.TYPE_OUTPOST,
            camp,
            snapshot.own_outpost_hp,
            snapshot.own_outpost_max_hp,
            0.0,
            0.0,
        )
        building(
            schema.TYPE_BASE,
            enemy_camp,
            snapshot.enemy_base_hp,
            snapshot.enemy_base_max_hp,
            0.0,
            snapshot.enemy_coin_total,
        )
        building(
            schema.TYPE_OUTPOST,
            enemy_camp,
            snapshot.enemy_outpost_hp,
            snapshot.enemy_outpost_max_hp,
            0.0,
            0.0,
        )
        game = upstream.GameArrays(1, entities)
        expected = upstream.build_obs(
            game,
            camp,
            schema.TYPE_SENTRY,
            team_feat=np.asarray(snapshot.team_prior, np.float32),
        )[0]
        actual = np.asarray(ours.build_observation(snapshot), np.float32)
        self.assertEqual(actual.shape, (161,))
        np.testing.assert_allclose(actual, expected, rtol=1e-6, atol=1e-6)

    @unittest.skipUnless(
        np is not None and upstream is not None and schema is not None,
        "pinned RMUC-OfflineRL dependency not fetched",
    )
    def test_matches_upstream_red(self) -> None:
        self.compare_with_upstream(ours.TEAM_RED)

    @unittest.skipUnless(
        np is not None and upstream is not None and schema is not None,
        "pinned RMUC-OfflineRL dependency not fetched",
    )
    def test_matches_upstream_blue(self) -> None:
        self.compare_with_upstream(ours.TEAM_BLUE)

    def test_non_finite_input_is_sanitized(self) -> None:
        snapshot = self.build_snapshot(ours.TEAM_RED)
        snapshot.ego.x = float("nan")
        snapshot.ego.hp = float("inf")
        output = ours.build_observation(snapshot)
        self.assertEqual(len(output), 161)
        self.assertTrue(all(math.isfinite(value) for value in output))


if __name__ == "__main__":
    unittest.main()
