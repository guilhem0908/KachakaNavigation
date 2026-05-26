from __future__ import annotations

import argparse
import logging
import sys

from kachaka_navigation.config import get_navigation_settings
from kachaka_navigation.core.interfaces import CommandExecutor
from kachaka_navigation.logging_config import configure_logging
from kachaka_navigation.robot import (
    LoggingCommandExecutor,
    RobotNavigationClient,
)
from kachaka_navigation.ros import Ros1ImageTopicSource
from kachaka_navigation.transport import NavigationTcpClient


logger = logging.getLogger(__name__)


def main() -> int:
    configure_logging()
    args = _parse_args()

    try:
        image_source = Ros1ImageTopicSource(
            topic=args.image_topic,
            jpeg_quality=args.jpeg_quality,
        )
        transport = NavigationTcpClient(
            host=args.server_host,
            port=args.server_port,
            timeout_seconds=args.timeout,
        )
        executor = _build_command_executor(dry_run=args.dry_run)

        client = RobotNavigationClient(
            image_source=image_source,
            transport=transport,
            command_executor=executor,
            min_period_seconds=args.min_period,
        )
        logger.info(
            "Starting robot navigation client against %s:%s",
            args.server_host,
            args.server_port,
        )
        client.run_forever()
        return 0
    except KeyboardInterrupt:
        print()
        logger.info("Robot navigation client interrupted by user")
        return 130
    except Exception as error:
        logger.exception("Robot navigation client failed")
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


def _parse_args() -> argparse.Namespace:
    settings = get_navigation_settings()
    parser = argparse.ArgumentParser(
        description="Run the robot-side image sender and command receiver."
    )
    parser.add_argument("--server-host", default=settings.server_host)
    parser.add_argument("--server-port", type=int, default=settings.server_port)
    parser.add_argument("--image-topic", default=settings.ros_image_topic)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--min-period", type=float, default=0.0)
    parser.add_argument("--jpeg-quality", type=int, default=85)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log commands instead of sending them to Kachaka.",
    )
    return parser.parse_args()


def _build_command_executor(dry_run: bool) -> CommandExecutor:
    if dry_run:
        return LoggingCommandExecutor()

    from kachaka_navigation.robot import KachakaCommandExecutor

    return KachakaCommandExecutor.from_settings()


if __name__ == "__main__":
    sys.exit(main())
