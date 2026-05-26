from __future__ import annotations

import logging

from kachaka_navigation.core.messages import NavigationCommand


logger = logging.getLogger(__name__)


class LoggingCommandExecutor:
    """Dry-run executor that logs commands without touching the robot."""

    def execute(self, command: NavigationCommand) -> None:
        logger.info("Dry-run robot command: %s", command)
