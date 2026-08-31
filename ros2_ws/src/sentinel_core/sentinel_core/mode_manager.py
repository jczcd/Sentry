from __future__ import annotations

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Bool, UInt8

from sentinel_interfaces.msg import SystemStatus
from sentinel_interfaces.srv import SetEstop, SetMode


MODE_BY_NAME = {
    "sim": SystemStatus.MODE_SIM,
    "hil": SystemStatus.MODE_HIL,
    "real": SystemStatus.MODE_REAL,
}


class ModeManager(Node):
    def __init__(self) -> None:
        super().__init__("mode_manager")
        self.declare_parameter("initial_mode", "sim")
        self.declare_parameter("initial_estop", True)
        name = str(self.get_parameter("initial_mode").value).lower()
        if name not in MODE_BY_NAME:
            raise ValueError(f"invalid initial_mode: {name}")
        self._mode = MODE_BY_NAME[name]
        self._estop = bool(self.get_parameter("initial_estop").value)

        qos = QoSProfile(depth=1)
        qos.reliability = ReliabilityPolicy.RELIABLE
        qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
        self._mode_pub = self.create_publisher(UInt8, "/sentry/system_mode", qos)
        self._estop_pub = self.create_publisher(Bool, "/sentry/estop", qos)
        self.create_service(SetMode, "/sentry/set_mode", self._set_mode)
        self.create_service(SetEstop, "/sentry/set_estop", self._set_estop)
        self._publish()

    def _publish(self) -> None:
        mode = UInt8()
        mode.data = self._mode
        self._mode_pub.publish(mode)
        estop = Bool()
        estop.data = self._estop
        self._estop_pub.publish(estop)

    def _set_mode(self, request: SetMode.Request, response: SetMode.Response):
        requested = int(request.mode)
        if requested not in MODE_BY_NAME.values():
            response.accepted = False
            response.reason = "mode must be SIM(0), HIL(1), or REAL(2)"
            return response
        if requested != self._mode and not self._estop:
            response.accepted = False
            response.reason = "engage e-stop before changing mode"
            return response
        self._mode = requested
        self._publish()
        response.accepted = True
        response.reason = "mode updated"
        return response

    def _set_estop(
        self, request: SetEstop.Request, response: SetEstop.Response
    ):
        self._estop = bool(request.engaged)
        self._publish()
        response.accepted = True
        response.reason = "e-stop engaged" if self._estop else "e-stop released"
        return response


def main(args=None) -> None:
    rclpy.init(args=args)
    node = ModeManager()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
