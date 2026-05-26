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
        locations = robot.get_locations()

        logger.info("Received %s location(s)", len(locations))
        for location in locations:
            print(location)

        return 0
    except Exception:
        logger.exception("Failed to list Kachaka locations")
        _print_troubleshooting_checklist()
        return 1


def _print_troubleshooting_checklist() -> None:
    print(
        "\nCould not list locations. Please check:\n"
        "1. Kachaka is powered on.\n"
        "2. Kachaka is connected to Wi-Fi.\n"
        "3. The Mac is on the same network as Kachaka.\n"
        "4. Kachaka API is enabled in the iPad app.\n"
        "5. The IP address in `.env` is correct.\n"
        "6. The port is 26400.\n",
        file=sys.stderr,
    )


if __name__ == "__main__":
    sys.exit(main())
