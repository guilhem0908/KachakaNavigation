from __future__ import annotations

import argparse
import logging
import sys

from kachaka_navigation.config import get_navigation_settings
from kachaka_navigation.logging_config import configure_logging
from kachaka_navigation.ros2 import Ros2ImageSenderNode
from kachaka_navigation.ros2.availability import import_ros2_core


logger = logging.getLogger(__name__)


def main() -> int:
    configure_logging()
    args = _parse_args()

    try:
        rclpy = import_ros2_core()[0]
        rclpy.init()
        node = Ros2ImageSenderNode(
            input_image_topic=args.input_image_topic,
            output_image_topic=args.output_image_topic,
            image_type=args.image_type,
        )
        try:
            rclpy.spin(node)
        finally:
            node.destroy_node()
            rclpy.shutdown()
        return 0
    except KeyboardInterrupt:
        print()
        logger.info("ROS2 image sender interrupted by user")
        return 130
    except Exception as error:
        logger.exception("ROS2 image sender failed")
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


def _parse_args() -> argparse.Namespace:
    settings = get_navigation_settings()
    parser = argparse.ArgumentParser(
        description="Run the camera/Kachaka-side ROS2 image sender node."
    )
    parser.add_argument("--input-image-topic", default=settings.ros2_camera_input_topic)
    parser.add_argument("--output-image-topic", default=settings.ros2_image_topic)
    parser.add_argument(
        "--image-type",
        choices=["raw", "compressed"],
        default=settings.ros2_image_type,
    )
    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(main())
