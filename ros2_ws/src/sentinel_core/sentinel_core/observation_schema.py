"""Pure-Python implementation of the RMUC-OfflineRL 161-D observation schema."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Iterable


TEAM_RED = 0
TEAM_BLUE = 1

TYPE_HERO = 1
TYPE_ENGINEER = 2
TYPE_INFANTRY3 = 3
TYPE_INFANTRY4 = 4
TYPE_AERIAL = 5
TYPE_SENTRY = 6
TYPE_BASE = 7
TYPE_OUTPOST = 8

MOBILE_TYPES = (
    TYPE_HERO,
    TYPE_ENGINEER,
    TYPE_INFANTRY3,
    TYPE_INFANTRY4,
    TYPE_AERIAL,
    TYPE_SENTRY,
)

MAX_HP = {
    TYPE_HERO: 450.0,
    TYPE_ENGINEER: 250.0,
    TYPE_INFANTRY3: 400.0,
    TYPE_INFANTRY4: 400.0,
    TYPE_AERIAL: 100.0,
    TYPE_SENTRY: 400.0,
    TYPE_BASE: 5000.0,
    TYPE_OUTPOST: 1500.0,
}

FIELD_X = 28.0
FIELD_Y = 15.0
FIELD_Z = 6.0
FIELD_DIAG = math.hypot(FIELD_X, FIELD_Y)
POWER_NORM = 120.0
AMMO_NORM = 400.0
COIN_NORM = 4000.0
HEAT17_MAX_REF = 260.0
HEAT42_MAX_REF = 240.0
FEATURE_COUNT = 161
SCHEMA_VERSION = 1
MATCH_DURATION_S = 450.0


@dataclass(slots=True)
class EntitySnapshot:
    robot_type: int
    team: int = TEAM_RED
    present: bool = False
    alive: bool = False
    visible: bool = False
    vulnerable: bool = False
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    turret_yaw_rad: float = 0.0
    hp: float = 0.0
    max_hp: float = 0.0
    chassis_power_w: float = 0.0
    heat_17: float = 0.0
    heat_17_limit: float = 0.0
    heat_42_limit: float = 0.0
    ammo_17_fired: float = 0.0


@dataclass(slots=True)
class BattleSnapshot:
    ego_team: int
    ego_type: int
    ego: EntitySnapshot
    elapsed_s: float = 0.0
    remaining_s: float = 450.0
    allies: list[EntitySnapshot] = field(default_factory=list)
    enemies: list[EntitySnapshot] = field(default_factory=list)
    own_base_hp: float = 5000.0
    own_base_max_hp: float = 5000.0
    own_outpost_hp: float = 1500.0
    own_outpost_max_hp: float = 1500.0
    enemy_base_hp: float = 5000.0
    enemy_base_max_hp: float = 5000.0
    enemy_outpost_hp: float = 1500.0
    enemy_outpost_max_hp: float = 1500.0
    own_coin_left: float = 0.0
    own_coin_total: float = 0.0
    enemy_coin_total: float = 0.0
    team_prior: list[float] = field(default_factory=lambda: [0.0] * 6)


def _finite(value: float, default: float = 0.0) -> float:
    value = float(value)
    return value if math.isfinite(value) else default


def _clip(value: float, low: float, high: float) -> float:
    return min(max(_finite(value), low), high)


def _safe_frac(num: float, den: float) -> float:
    den = _finite(den)
    if abs(den) < 1.0e-6:
        den = 1.0
    return _clip(_finite(num) / den, 0.0, 1.5)


def _entity_for_type(
    entities: Iterable[EntitySnapshot], robot_type: int, team: int
) -> EntitySnapshot:
    for entity in entities:
        if entity.robot_type == robot_type and entity.team == team and entity.present:
            return entity
    return EntitySnapshot(
        robot_type=robot_type,
        team=team,
        max_hp=MAX_HP.get(robot_type, 1.0),
    )


def _canonical_xy(x: float, y: float, mirror: bool) -> tuple[float, float]:
    if mirror:
        return FIELD_X - _finite(x), FIELD_Y - _finite(y)
    return _finite(x), _finite(y)


def _capability(entity: EntitySnapshot) -> tuple[float, float, float, float]:
    max_ref = MAX_HP.get(entity.robot_type, 400.0)
    entity_max = entity.max_hp if entity.max_hp > 0.0 else max_ref
    return (
        _safe_frac(entity_max, max_ref),
        _finite(entity.heat_17_limit) / HEAT17_MAX_REF,
        _finite(entity.heat_42_limit) / HEAT42_MAX_REF,
        _finite(entity.chassis_power_w) / POWER_NORM,
    )


def build_observation(snapshot: BattleSnapshot) -> list[float]:
    """Build one observation matching RMUC-OfflineRL ``features.py`` exactly."""

    mirror = snapshot.ego_team == TEAM_BLUE
    ego = snapshot.ego
    ex, ey = _canonical_xy(ego.x, ego.y, mirror)
    yaw = _finite(ego.turret_yaw_rad) + (math.pi if mirror else 0.0)
    ego_max_hp = ego.max_hp if ego.max_hp > 0.0 else MAX_HP.get(ego.robot_type, 1.0)
    heat_limit = ego.heat_17_limit if ego.heat_17_limit > 0.0 else 1.0

    features: list[float] = [
        ex / FIELD_X * 2.0 - 1.0,
        ey / FIELD_Y * 2.0 - 1.0,
        _finite(ego.z) / FIELD_Z,
        _safe_frac(ego.hp, ego_max_hp),
        float(ego.alive),
        float(ego.vulnerable),
        _safe_frac(ego.heat_17, heat_limit),
        _safe_frac(heat_limit - ego.heat_17, heat_limit),
        _finite(ego.chassis_power_w) / POWER_NORM,
        math.sin(yaw),
        math.cos(yaw),
        _finite(ego.ammo_17_fired) / AMMO_NORM,
        _safe_frac(ego_max_hp, MAX_HP.get(ego.robot_type, ego_max_hp)),
        _finite(ego.heat_17_limit) / HEAT17_MAX_REF,
        _finite(ego.heat_42_limit) / HEAT42_MAX_REF,
    ]

    elapsed = max(_finite(snapshot.elapsed_s), 0.0)
    features.extend(
        (
            elapsed / MATCH_DURATION_S,
            _clip(1.0 - elapsed / MATCH_DURATION_S, 0.0, 1.0),
        )
    )

    allies = list(snapshot.allies)
    if not any(
        entity.present
        and entity.robot_type == snapshot.ego_type
        and entity.team == snapshot.ego_team
        for entity in allies
    ):
        allies.append(ego)

    for robot_type in MOBILE_TYPES:
        ally = _entity_for_type(allies, robot_type, snapshot.ego_team)
        ax, ay = _canonical_xy(ally.x, ally.y, mirror)
        alive = float(ally.alive and ally.present)
        rx = (ax - ex) * alive
        ry = (ay - ey) * alive
        ally_max_hp = ally.max_hp if ally.max_hp > 0.0 else MAX_HP[robot_type]
        features.extend(
            (
                rx / FIELD_X,
                ry / FIELD_Y,
                math.hypot(rx, ry) / FIELD_DIAG,
                _safe_frac(ally.hp, ally_max_hp),
                alive,
                *_capability(ally),
            )
        )

    enemy_team = TEAM_RED if snapshot.ego_team == TEAM_BLUE else TEAM_BLUE
    for robot_type in MOBILE_TYPES:
        enemy = _entity_for_type(snapshot.enemies, robot_type, enemy_team)
        px, py = _canonical_xy(enemy.x, enemy.y, mirror)
        known = float(enemy.present and enemy.alive and enemy.visible)
        rx = (px - ex) * known
        ry = (py - ey) * known
        enemy_max_hp = enemy.max_hp if enemy.max_hp > 0.0 else MAX_HP[robot_type]
        features.extend(
            (
                rx / FIELD_X,
                ry / FIELD_Y,
                math.hypot(rx, ry) / FIELD_DIAG if known else 1.0,
                _safe_frac(enemy.hp, enemy_max_hp),
                float(enemy.alive and enemy.present),
                float(enemy.vulnerable),
                known,
                *_capability(enemy),
                0.0,  # empirical visibility prior; inject here when available
            )
        )

    features.extend(
        (
            _safe_frac(snapshot.own_base_hp, snapshot.own_base_max_hp),
            float(snapshot.own_base_hp > 0.0),
            _safe_frac(snapshot.own_outpost_hp, snapshot.own_outpost_max_hp),
            float(snapshot.own_outpost_hp > 0.0),
            _safe_frac(snapshot.enemy_base_hp, snapshot.enemy_base_max_hp),
            float(snapshot.enemy_base_hp > 0.0),
            _safe_frac(snapshot.enemy_outpost_hp, snapshot.enemy_outpost_max_hp),
            float(snapshot.enemy_outpost_hp > 0.0),
            _finite(snapshot.own_coin_left) / COIN_NORM,
            _finite(snapshot.own_coin_total) / COIN_NORM,
            _finite(snapshot.enemy_coin_total) / COIN_NORM,
            (_finite(snapshot.own_coin_total) - _finite(snapshot.enemy_coin_total))
            / COIN_NORM,
        )
    )

    prior = list(snapshot.team_prior[:6])
    prior.extend([0.0] * (6 - len(prior)))
    features.extend(_finite(value) for value in prior)

    features = [_finite(value) for value in features]
    if len(features) != FEATURE_COUNT:
        raise RuntimeError(f"observation schema drift: {len(features)} != {FEATURE_COUNT}")
    return features
