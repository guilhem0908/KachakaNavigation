from __future__ import annotations

import argparse
import logging
import sys

from kachaka_navigation.config import get_navigation_settings
from kachaka_navigation.logging_config import configure_logging
from kachaka_navigation.ros2 import Ros2CommandSenderNode
from kachaka_navigation.ros2.availability import import_ros2_core


logger = logging.getLogger(__name__)


def main() -> int:
    configure_logging()
    args = _parse_args()

    try:
        rclpy = import_ros2_core()[0]
        rclpy.init()
        node = Ros2CommandSenderNode(
            trajectory_topic=args.trajectory_topic,
            robot_command_topic=args.robot_command_topic,
            max_command_age_seconds=args.max_command_age,
        )
        try:
            rclpy.spin(node)
        finally:
            node.destroy_node()
            rclpy.shutdown()
        return 0
    except KeyboardInterrupt:
        print()
        logger.info("ROS2 command sender interrupted by user")
        return 130
    except Exception as error:
        logger.exception("ROS2 command sender failed")
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


def _parse_args() -> argparse.Namespace:
    settings = get_navigation_settings()
    parser = argparse.ArgumentParser(
        description="Run the server-side ROS2 command sender node."
    )
    parser.add_argument("--trajectory-topic", default=settings.ros2_trajectory_topic)
    parser.add_argument("--robot-command-topic", default=settings.ros2_robot_command_topic)
    parser.add_argument("--max-command-age", type=float, default=settings.max_image_age_seconds)
    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(main())
