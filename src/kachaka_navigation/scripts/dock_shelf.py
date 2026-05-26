import logging
import sys

from kachaka_navigation.clients.kachaka_robot_client import KachakaRobotClient
from kachaka_navigation.config import get_kachaka_settings
from kachaka_navigation.logging_config import configure_logging


logger = logging.getLogger(__name__)


def main() -> int:
    configure_logging()

    if len(sys.argv) != 1:
        print("Usage:")
        print("  python -m kachaka_navigation.scripts.dock_shelf")
        return 1

    try:
        settings = get_kachaka_settings()
        logger.info("Connecting to Kachaka API at %s", settings.target)

        robot = KachakaRobotClient(target=settings.target)
        result = robot.dock_shelf()

        print(result)
        return 0

    except KeyboardInterrupt:
        print()
        print("Interrupted by user.")
        return 130

    except Exception as error:
        logger.exception("dock_shelf failed")
        print()
        print("ERROR: Could not dock the shelf.")
        print()
        print("Checklist:")
        print("1. The shelf is in front of Kachaka.")
        print("2. Kachaka is not physically blocked.")
        print("3. Kachaka API is still enabled.")
        print()
        print(f"Python error type: {type(error).__name__}")
        print(f"Python error: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
