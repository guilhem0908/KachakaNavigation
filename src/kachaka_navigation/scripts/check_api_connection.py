import logging
import sys

from kachaka_navigation.config import get_kachaka_settings
from kachaka_navigation.connectivity import check_tcp_connection
from kachaka_navigation.logging_config import configure_logging


logger = logging.getLogger(__name__)


def main() -> int:
    configure_logging()

    if len(sys.argv) != 1:
        print("Usage:")
        print("  python -m kachaka_navigation.scripts.check_api_connection")
        return 1

    try:
        settings = get_kachaka_settings()
    except Exception as error:
        logger.error("Could not read Kachaka settings: %s", error)
        print(f"ERROR: {error}")
        return 1

    logger.info("Checking TCP connection to %s", settings.target)
    check = check_tcp_connection(settings.host, settings.port)

    if check.ok:
        print(f"OK: Kachaka API port is reachable at {settings.target}")
        return 0

    print(f"ERROR: Kachaka API port is not reachable at {settings.target}")
    print()
    print("Checklist:")
    print("1. Kachaka is powered on.")
    print("2. Kachaka API is enabled in the app.")
    print("3. The Mac is on the same Wi-Fi/network as Kachaka.")
    print("4. The IP address in `.env` is still correct.")
    print("5. The port is 26400.")
    print()
    print(f"Network error: {check.error}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
