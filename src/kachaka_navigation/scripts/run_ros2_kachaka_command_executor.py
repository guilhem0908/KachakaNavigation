from __future__ import annotations

import argparse
import logging
import sys

from kachaka_navigation.config import get_navigation_settings
from kachaka_navigation.core.velocity_safety import VelocitySafetyLimits
from kachaka_navigation.logging_config import configure_logging
from kachaka_navigation.ros2 import Ros2KachakaCommandExecutorNode
from kachaka_navigation.ros2.availability import import_ros2_core


logger = logging.getLogger(__name__)


def main() -> int:
    configure_logging()
    args = _parse_args()

    try:
        rclpy = import_ros2_core()[0]
        rclpy.init()
        node = Ros2KachakaCommandExecutorNode(
            robot_command_topic=args.robot_command_topic,
            dry_run=args.dry_run,
            enable_api_commands=not args.disable_kachaka_api,
            enable_velocity_control=args.enable_velocity_control,
            cmd_vel_topic=args.cmd_vel_topic,
            cmd_vel_publish_rate_hz=args.cmd_vel_publish_rate,
            velocity_limits=VelocitySafetyLimits(
                max_linear_x=args.max_linear_speed,
                max_angular_z=args.max_angular_speed,
                default_duration_seconds=args.velocity_timeout,
                max_duration_seconds=args.max_velocity_duration,
            ),
        )
        try:
            rclpy.spin(node)
        finally:
            node.destroy_node()
            rclpy.shutdown()
        return 0
    except KeyboardInterrupt:
        print()
        logger.info("ROS2 Kachaka command executor interrupted by user")
        return 130
    except Exception as error:
        logger.exception("ROS2 Kachaka command executor failed")
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


def _parse_args() -> argparse.Namespace:
    settings = get_navigation_settings()
    parser = argparse.ArgumentParser(
        description="Run the Kachaka-side ROS2 command executor node."
    )
    parser.add_argument("--robot-command-topic", default=settings.ros2_robot_command_topic)
    parser.add_argument("--cmd-vel-topic", default=settings.ros2_cmd_vel_topic)
    parser.add_argument(
        "--enable-velocity-control",
        action="store_true",
        help="Publish velocity commands as geometry_msgs/Twist.",
    )
    parser.add_argument(
        "--disable-kachaka-api",
        action="store_true",
        help="Do not execute high-level Kachaka API commands.",
    )
    parser.add_argument(
        "--cmd-vel-publish-rate",
        type=float,
        default=settings.cmd_vel_publish_rate_hz,
    )
    parser.add_argument(
        "--velocity-timeout",
        type=float,
        default=settings.velocity_command_timeout_seconds,
    )
    parser.add_argument("--max-velocity-duration", type=float, default=1.0)
    parser.add_argument("--max-linear-speed", type=float, default=settings.max_linear_speed_mps)
    parser.add_argument(
        "--max-angular-speed",
        type=float,
        default=settings.max_angular_speed_radps,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log commands instead of sending them to Kachaka.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(main())
