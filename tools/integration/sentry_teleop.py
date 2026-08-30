#!/usr/bin/env python3
"""Low-speed watchdog keyboard teleop for the Sentinel safety input."""
import argparse
import curses
import time

import rclpy
from geometry_msgs.msg import Twist


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--linear", type=float, default=0.12)
    parser.add_argument("--angular", type=float, default=0.35)
    parser.add_argument("--timeout", type=float, default=0.30)
    args = parser.parse_args()
    rclpy.init()
    node = rclpy.create_node("sentinel_keyboard_teleop")
    publisher = node.create_publisher(Twist, "/cmd_vel", 10)
    active = {}

    def zero() -> None:
        publisher.publish(Twist())
        rclpy.spin_once(node, timeout_sec=0.0)

    def run(screen) -> None:
        nonlocal active
        curses.curs_set(0)
        screen.nodelay(True)
        screen.addstr("W/S forward  A/D strafe  Q/E rotate  SPACE/X stop  Ctrl+C quit\n")
        screen.addstr(f"linear={args.linear:.3f} m/s angular={args.angular:.3f} rad/s\n")
        while rclpy.ok():
            now = time.monotonic()
            try:
                key = screen.get_wch()
                if isinstance(key, str):
                    key = key.lower()
                    if key in "wasdqe":
                        active[key] = now
                    elif key in (" ", "x"):
                        active.clear()
                        zero()
            except curses.error:
                pass
            active = {key: stamp for key, stamp in active.items() if now - stamp <= args.timeout}
            msg = Twist()
            msg.linear.x = args.linear * (int("w" in active) - int("s" in active))
            msg.linear.y = args.linear * (int("a" in active) - int("d" in active))
            msg.angular.z = args.angular * (int("q" in active) - int("e" in active))
            publisher.publish(msg)
            rclpy.spin_once(node, timeout_sec=0.0)
            time.sleep(0.05)

    try:
        curses.wrapper(run)
    except KeyboardInterrupt:
        pass
    finally:
        for _ in range(3):
            zero()
            time.sleep(0.03)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
