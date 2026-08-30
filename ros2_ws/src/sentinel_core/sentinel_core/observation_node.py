from __future__ import annotations

import rclpy
from rclpy.node import Node

from sentinel_interfaces.msg import BattleState, PolicyObservation

from .observation_schema import (
    BattleSnapshot,
    EntitySnapshot,
    SCHEMA_VERSION,
    build_observation,
)


def _entity(message) -> EntitySnapshot:
    return EntitySnapshot(
        robot_type=int(message.robot_type),
        team=int(message.team),
        present=bool(message.present),
        alive=bool(message.alive),
        visible=bool(message.visible),
        vulnerable=bool(message.vulnerable),
        x=float(message.position.x),
        y=float(message.position.y),
        z=float(message.position.z),
        turret_yaw_rad=float(message.turret_yaw_rad),
        hp=float(message.hp),
        max_hp=float(message.max_hp),
        chassis_power_w=float(message.chassis_power_w),
        heat_17=float(message.heat_17),
        heat_17_limit=float(message.heat_17_limit),
        heat_42_limit=float(message.heat_42_limit),
        ammo_17_fired=float(message.ammo_17_fired),
    )


class BattleObservationNode(Node):
    def __init__(self) -> None:
        super().__init__("battle_observation")
        self._publisher = self.create_publisher(
            PolicyObservation, "/sentry/policy/observation", 10
        )
        self.create_subscription(BattleState, "/sentry/battle_state", self._on_state, 10)

    def _on_state(self, message: BattleState) -> None:
        snapshot = BattleSnapshot(
            ego_team=int(message.ego_team),
            ego_type=int(message.ego_type),
            ego=_entity(message.ego),
            elapsed_s=float(message.elapsed_s),
            remaining_s=float(message.remaining_s),
            allies=[_entity(item) for item in message.allies],
            enemies=[_entity(item) for item in message.enemies],
            own_base_hp=float(message.own_base_hp),
            own_base_max_hp=float(message.own_base_max_hp),
            own_outpost_hp=float(message.own_outpost_hp),
            own_outpost_max_hp=float(message.own_outpost_max_hp),
            enemy_base_hp=float(message.enemy_base_hp),
            enemy_base_max_hp=float(message.enemy_base_max_hp),
            enemy_outpost_hp=float(message.enemy_outpost_hp),
            enemy_outpost_max_hp=float(message.enemy_outpost_max_hp),
            own_coin_left=float(message.own_coin_left),
            own_coin_total=float(message.own_coin_total),
            enemy_coin_total=float(message.enemy_coin_total),
            team_prior=list(message.team_prior),
        )
        output = PolicyObservation()
        output.header = message.header
        output.schema_version = SCHEMA_VERSION
        output.features = build_observation(snapshot)
        self._publisher.publish(output)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = BattleObservationNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
