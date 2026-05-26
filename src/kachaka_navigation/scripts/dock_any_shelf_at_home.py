import logging
import sys

from kachaka_navigation.clients.kachaka_robot_client import KachakaRobotClient
from kachaka_navigation.config import get_kachaka_settings
from kachaka_navigation.logging_config import configure_logging


logger = logging.getLogger(__name__)
HOME_LOCATION = "home"


def main() -> int:
    configure_logging()

    if len(sys.argv) not in {1, 2}:
        print("Usage:")
        print("  python -m kachaka_navigation.scripts.dock_any_shelf_at_home")
        print("  python -m kachaka_navigation.scripts.dock_any_shelf_at_home --forward")
        return 1

    if len(sys.argv) == 2 and sys.argv[1] != "--forward":
        print("Usage:")
        print("  python -m kachaka_navigation.scripts.dock_any_shelf_at_home")
        print("  python -m kachaka_navigation.scripts.dock_any_shelf_at_home --forward")
        return 1

    dock_forward = len(sys.argv) == 2

    try:
        settings = get_kachaka_settings()
        logger.info("Connecting to Kachaka API at %s", settings.target)

        robot = KachakaRobotClient(settings.target)

        if dock_forward:
            print("Warning: --forward is ignored by this robot-compatible command.")

        result = robot.dock_shelf_at_location(HOME_LOCATION)

        print(result)
        return 0

    except KeyboardInterrupt:
        print()
        print("Interrupted by user.")
        return 130

    except Exception as error:
        logger.error("dock_any_shelf_at_home failed: %s", error)
        print()
        print("ERROR: Could not move to home and dock the shelf.")
        print()
        print("Checklist:")
        print("1. Kachaka is powered on and the API is enabled.")
        print("2. The Mac is on the same network as Kachaka.")
        print("3. The IP address in `.env` is still correct.")
        print("4. Kachaka is not physically blocked and can reach the shelf.")
        print()
        print(f"Python error type: {type(error).__name__}")
        print(f"Python error: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
