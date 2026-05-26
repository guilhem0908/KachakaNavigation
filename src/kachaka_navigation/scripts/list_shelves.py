import logging
import sys

from kachaka_navigation.clients.kachaka_robot_client import KachakaRobotClient
from kachaka_navigation.config import get_kachaka_settings
from kachaka_navigation.logging_config import configure_logging


logger = logging.getLogger(__name__)


def main() -> int:
    configure_logging()

    try:
        settings = get_kachaka_settings()
        logger.info("Connecting to Kachaka API at %s", settings.target)

        robot = KachakaRobotClient(target=settings.target)
        shelves = robot.get_shelves()

        logger.info("Received %s shelf/shelves", len(shelves))
        for shelf in shelves:
            print(shelf)

        return 0
    except Exception:
        logger.exception("Failed to list Kachaka shelves")
        _print_troubleshooting_checklist()
        return 1


def _print_troubleshooting_checklist() -> None:
    print(
        "\nCould not list shelves. Please check:\n"
        "1. Kachaka is powered on.\n"
        "2. Kachaka is connected to Wi-Fi.\n"
        "3. The Mac is on the same network as Kachaka.\n"
        "4. Kachaka API is enabled in the iPad app.\n"
        "5. The IP address in `.env` is correct.\n"
        "6. At least one shelf is registered in the Kachaka app.\n",
        file=sys.stderr,
    )


if __name__ == "__main__":
    sys.exit(main())
