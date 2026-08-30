from __future__ import annotations

from nav_msgs.msg import Odometry
import rclpy
from rclpy.node import Node

from sentinel_interfaces.msg import BattleEntity, BattleState


MOBILE = (
    BattleEntity.TYPE_HERO,
    BattleEntity.TYPE_ENGINEER,
    BattleEntity.TYPE_INFANTRY3,
    BattleEntity.TYPE_INFANTRY4,
    BattleEntity.TYPE_AERIAL,
    BattleEntity.TYPE_SENTRY,
)

MAX_HP = {
    BattleEntity.TYPE_HERO: 450.0,
    BattleEntity.TYPE_ENGINEER: 250.0,
    BattleEntity.TYPE_INFANTRY3: 400.0,
    BattleEntity.TYPE_INFANTRY4: 400.0,
    BattleEntity.TYPE_AERIAL: 100.0,
    BattleEntity.TYPE_SENTRY: 400.0,
}


def _make_entity(robot_type: int, team: int, x: float, y: float) -> BattleEntity:
    entity = BattleEntity()
    entity.robot_type = robot_type
    entity.team = team
    entity.present = True
    entity.alive = True
    entity.visible = True
    entity.position.x = x
    entity.position.y = y
    entity.hp = MAX_HP[robot_type]
    entity.max_hp = MAX_HP[robot_type]
    entity.heat_17_limit = 260.0 if robot_type in (
        BattleEntity.TYPE_INFANTRY3,
        BattleEntity.TYPE_INFANTRY4,
        BattleEntity.TYPE_SENTRY,
    ) else 0.0
    entity.heat_42_limit = 240.0 if robot_type == BattleEntity.TYPE_HERO else 0.0
    return entity


class MockBattleState(Node):
    def __init__(self) -> None:
        super().__init__("mock_battle_state")
        self._x = 2.0
        self._y = 2.0
        self._elapsed = 0.0
        self._publisher = self.create_publisher(BattleState, "/sentry/battle_state", 10)
        self.create_subscription(Odometry, "/sentry/odom", self._on_odom, 10)
        self.create_timer(1.0, self._tick)

    def _on_odom(self, message: Odometry) -> None:
        self._x = float(message.pose.pose.position.x)
        self._y = float(message.pose.pose.position.y)

    def _tick(self) -> None:
        self._elapsed += 1.0
        state = BattleState()
        state.header.stamp = self.get_clock().now().to_msg()
        state.header.frame_id = "map"
        state.ego_team = BattleEntity.TEAM_RED
        state.ego_type = BattleEntity.TYPE_SENTRY
        state.elapsed_s = self._elapsed
        state.remaining_s = max(450.0 - self._elapsed, 0.0)
        state.ego = _make_entity(
            BattleEntity.TYPE_SENTRY, BattleEntity.TEAM_RED, self._x, self._y
        )
        state.allies = [
            _make_entity(kind, BattleEntity.TEAM_RED, 2.0 + kind, 2.0)
            for kind in MOBILE
        ]
        state.allies[-1] = state.ego
        state.enemies = [
            _make_entity(kind, BattleEntity.TEAM_BLUE, 22.0, 2.0 + kind)
            for kind in MOBILE
        ]
        state.own_base_hp = state.own_base_max_hp = 5000.0
        state.enemy_base_hp = state.enemy_base_max_hp = 5000.0
        state.own_outpost_hp = state.own_outpost_max_hp = 1500.0
        state.enemy_outpost_hp = state.enemy_outpost_max_hp = 1500.0
        state.team_prior = [0.0] * 6
        self._publisher.publish(state)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = MockBattleState()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
