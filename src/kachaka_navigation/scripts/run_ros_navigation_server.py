from __future__ import annotations

import argparse
import logging
import sys

from kachaka_navigation.config import get_navigation_settings
from kachaka_navigation.logging_config import configure_logging
from kachaka_navigation.ros import (
    Ros1ImageTopicSource,
    Ros1JsonCommandPublisher,
)
from kachaka_navigation.scripts.model_cli import (
    add_navigation_model_arguments,
    build_navigation_service_from_args,
)


logger = logging.getLogger(__name__)
DEFAULT_COMMAND_TOPIC = "/kachaka_navigation/command"


def main() -> int:
    configure_logging()
    args = _parse_args()

    try:
        service = build_navigation_service_from_args(args)
        image_source = Ros1ImageTopicSource(
            topic=args.image_topic,
            jpeg_quality=args.jpeg_quality,
        )
        command_publisher = Ros1JsonCommandPublisher(topic=args.command_topic)

        logger.info(
            "Starting ROS navigation server with model %s",
            service.model_name,
        )
        for frame in image_source.frames():
            command = service.predict_command(frame=frame)
            command_publisher.send(command)

        return 0
    except KeyboardInterrupt:
        print()
        logger.info("ROS navigation server interrupted by user")
        return 130
    except Exception as error:
        logger.exception("ROS navigation server failed")
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


def _parse_args() -> argparse.Namespace:
    settings = get_navigation_settings()
    parser = argparse.ArgumentParser(
        description="Run a local ROS1 image-topic navigation server."
    )
    parser.add_argument("--image-topic", default=settings.ros_image_topic)
    parser.add_argument("--command-topic", default=DEFAULT_COMMAND_TOPIC)
    parser.add_argument("--jpeg-quality", type=int, default=85)
    add_navigation_model_arguments(parser)
    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(main())
