import logging
import sys

from kachaka_navigation.clients.kachaka_robot_client import KachakaRobotClient
from kachaka_navigation.config import get_kachaka_settings
from kachaka_navigation.logging_config import configure_logging


logger = logging.getLogger(__name__)
HOME_LOCATION = "home"


def main() -> int:
    configure_logging()

    if len(sys.argv) != 1:
        print("Usage: python -m kachaka_navigation.scripts.undock_shelf_at_home")
        return 1

    try:
        settings = get_kachaka_settings()
        logger.info("Connecting to Kachaka API at %s", settings.target)

        robot = KachakaRobotClient(settings.target)

        print(robot.move_to_location(HOME_LOCATION))
        print(robot.undock_shelf())

        return 0

    except KeyboardInterrupt:
        print()
        print("Interrupted by user.")
        return 130

    except Exception as error:
        logger.error("undock_shelf_at_home failed: %s", error)
        print()
        print("ERROR: Could not move to home and undock the shelf.")
        print()
        print("Checklist:")
        print("1. Kachaka is powered on and the API is enabled.")
        print("2. The Mac is on the same network as Kachaka.")
        print("3. The IP address in `.env` is still correct.")
        print("4. Kachaka is carrying a shelf.")
        print("5. The home location has enough space to unload the shelf.")
        print()
        print(f"Python error type: {type(error).__name__}")
        print(f"Python error: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
