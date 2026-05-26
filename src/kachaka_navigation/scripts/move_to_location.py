import logging
import sys

from kachaka_navigation.clients.kachaka_robot_client import KachakaRobotClient
from kachaka_navigation.config import get_kachaka_settings
from kachaka_navigation.logging_config import configure_logging


logger = logging.getLogger(__name__)


def main() -> int:
    configure_logging()

    if len(sys.argv) != 2:
        print("Usage:")
        print("  python -m kachaka_navigation.scripts.move_to_location <LOCATION_ID_OR_NAME>")
        print()
        print("Example:")
        print("  python -m kachaka_navigation.scripts.move_to_location home")
        return 1

    target_location = sys.argv[1]

    try:
        settings = get_kachaka_settings()
        logger.info("Connecting to Kachaka API at %s", settings.target)

        robot = KachakaRobotClient(target=settings.target)

        logger.info("Current pose before navigation:")
        logger.info("%s", robot.get_robot_pose())

        logger.info("Moving to location: %s", target_location)
        result = robot.move_to_location(target_location)

        logger.info("Navigation command result:")
        logger.info("%s", result)

        logger.info("Current pose after navigation:")
        logger.info("%s", robot.get_robot_pose())

        return 0

    except KeyboardInterrupt:
        print()
        print("Interrupted by user.")
        return 130

    except Exception as error:
        logger.exception("move_to_location failed")

        print()
        print("ERROR: Could not move Kachaka to the requested location.")
        print()
        print("Checklist:")
        print("1. The location ID exists. Run list_locations first.")
        print("2. Kachaka is not physically blocked.")
        print("3. Kachaka is localized on its map.")
        print("4. Kachaka API is still enabled.")
        print("5. The robot is allowed to leave the dock.")
        print()
        print(f"Python error type: {type(error).__name__}")
        print(f"Python error: {error}")

        return 1


if __name__ == "__main__":
    sys.exit(main())
