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
        print("  python -m kachaka_navigation.scripts.return_home")
        return 1

    try:
        settings = get_kachaka_settings()
        logger.info("Connecting to Kachaka API at %s", settings.target)

        robot = KachakaRobotClient(target=settings.target)
        result = robot.return_home()

        print(result)
        return 0

    except KeyboardInterrupt:
        print()
        print("Interrupted by user.")
        return 130

    except Exception as error:
        logger.exception("return_home failed")
        print()
        print("ERROR: Could not return Kachaka to its charger.")
        print()
        print("Checklist:")
        print("1. Kachaka is not physically blocked.")
        print("2. Kachaka is localized on its map.")
        print("3. Kachaka API is still enabled.")
        print("4. The charger is reachable.")
        print()
        print(f"Python error type: {type(error).__name__}")
        print(f"Python error: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
