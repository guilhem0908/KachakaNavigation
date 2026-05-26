from __future__ import annotations

import argparse
import logging
import sys

from kachaka_navigation.config import get_navigation_settings
from kachaka_navigation.logging_config import configure_logging
from kachaka_navigation.ros2 import Ros2TrajectoryGeneratorNode
from kachaka_navigation.ros2.availability import import_ros2_core
from kachaka_navigation.scripts.model_cli import (
    add_navigation_model_arguments,
    build_navigation_service_from_args,
)


logger = logging.getLogger(__name__)


def main() -> int:
    configure_logging()
    args = _parse_args()

    try:
        rclpy = import_ros2_core()[0]
        rclpy.init()
        service = build_navigation_service_from_args(args)
        node = Ros2TrajectoryGeneratorNode(
            service=service,
            image_topic=args.image_topic,
            trajectory_topic=args.trajectory_topic,
            image_type=args.image_type,
            jpeg_quality=args.jpeg_quality,
            max_image_age_seconds=args.max_image_age,
        )
        try:
            rclpy.spin(node)
        finally:
            node.destroy_node()
            rclpy.shutdown()
        return 0
    except KeyboardInterrupt:
        print()
        logger.info("ROS2 trajectory generator interrupted by user")
        return 130
    except Exception as error:
        logger.exception("ROS2 trajectory generator failed")
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


def _parse_args() -> argparse.Namespace:
    settings = get_navigation_settings()
    parser = argparse.ArgumentParser(
        description="Run the server-side ROS2 trajectory generator node."
    )
    parser.add_argument("--image-topic", default=settings.ros2_image_topic)
    parser.add_argument("--trajectory-topic", default=settings.ros2_trajectory_topic)
    parser.add_argument(
        "--image-type",
        choices=["raw", "compressed"],
        default=settings.ros2_image_type,
    )
    parser.add_argument("--jpeg-quality", type=int, default=85)
    parser.add_argument("--max-image-age", type=float, default=settings.max_image_age_seconds)
    add_navigation_model_arguments(parser)
    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(main())
