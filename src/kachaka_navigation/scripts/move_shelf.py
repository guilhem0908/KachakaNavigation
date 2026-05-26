import logging
import sys

from kachaka_navigation.clients.kachaka_robot_client import KachakaRobotClient
from kachaka_navigation.config import get_kachaka_settings
from kachaka_navigation.logging_config import configure_logging


logger = logging.getLogger(__name__)


def main() -> int:
    configure_logging()

    if len(sys.argv) != 3:
        print("Usage:")
        print(
            "  python -m kachaka_navigation.scripts.move_shelf "
            "<SHELF_ID_OR_NAME> <LOCATION_ID_OR_NAME>"
        )
        print()
        print("Example:")
        print("  python -m kachaka_navigation.scripts.move_shelf S01 L02")
        return 1

    shelf_id_or_name = sys.argv[1]
    location_id_or_name = sys.argv[2]

    try:
        settings = get_kachaka_settings()
        logger.info("Connecting to Kachaka API at %s", settings.target)

        robot = KachakaRobotClient(target=settings.target)

        move_result = robot.move_shelf(shelf_id_or_name, location_id_or_name)
        print("Move shelf result:")
        print(move_result)

        undock_result = robot.undock_shelf()
        print("Undock shelf result:")
        print(undock_result)

        return 0

    except KeyboardInterrupt:
        print()
        print("Interrupted by user.")
        return 130

    except Exception as error:
        logger.exception("move_shelf failed")
        print()
        print("ERROR: Could not move the requested shelf.")
        print()
        print("Checklist:")
        print("1. The shelf ID exists. Run list_shelves first.")
        print("2. The location ID exists. Run list_locations first.")
        print("3. Kachaka is not physically blocked.")
        print("4. Kachaka is localized on its map.")
        print("5. Kachaka API is still enabled.")
        print()
        print(f"Python error type: {type(error).__name__}")
        print(f"Python error: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
