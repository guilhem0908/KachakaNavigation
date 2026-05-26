from __future__ import annotations

import argparse
import logging
import sys

from kachaka_navigation.config import get_navigation_settings
from kachaka_navigation.logging_config import configure_logging
from kachaka_navigation.scripts.model_cli import (
    add_navigation_model_arguments,
    build_navigation_service_from_args,
)
from kachaka_navigation.transport import NavigationTcpServer


logger = logging.getLogger(__name__)


def main() -> int:
    configure_logging()
    args = _parse_args()

    try:
        service = build_navigation_service_from_args(args)

        with NavigationTcpServer(args.host, args.port, service) as server:
            host, port = server.server_address
            logger.info(
                "Starting navigation server with model %s on %s:%s",
                service.model_name,
                host,
                port,
            )
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                print()
                logger.info("Navigation server interrupted by user")

        return 0
    except Exception as error:
        logger.exception("Navigation server failed")
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


def _parse_args() -> argparse.Namespace:
    settings = get_navigation_settings()
    parser = argparse.ArgumentParser(
        description="Run the model-side TCP navigation server."
    )
    parser.add_argument("--host", default=settings.server_bind_host)
    parser.add_argument("--port", type=int, default=settings.server_port)
    add_navigation_model_arguments(parser)
    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(main())
