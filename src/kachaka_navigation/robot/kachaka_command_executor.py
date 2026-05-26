from __future__ import annotations

import logging

from kachaka_navigation.clients.kachaka_robot_client import KachakaRobotClient
from kachaka_navigation.config import get_kachaka_settings
from kachaka_navigation.core.messages import CommandKind, NavigationCommand


logger = logging.getLogger(__name__)


class UnsupportedRobotCommandError(RuntimeError):
    """Raised when the current Kachaka adapter cannot apply a model command."""


class KachakaCommandExecutor:
    """Maps generic navigation commands onto the existing Kachaka API client."""

    def __init__(self, robot: KachakaRobotClient) -> None:
        self._robot = robot

    @classmethod
    def from_settings(cls) -> KachakaCommandExecutor:
        settings = get_kachaka_settings()
        return cls(KachakaRobotClient(target=settings.target))

    def execute(self, command: NavigationCommand) -> None:
        logger.info("Executing robot command: %s", command.kind.value)

        if command.kind == CommandKind.NOOP:
            return
        if command.kind in {CommandKind.STOP, CommandKind.CANCEL}:
            self._robot.cancel_command()
            return
        if command.kind == CommandKind.MOVE_TO_LOCATION:
            self._robot.move_to_location(command.target)
            return
        if command.kind == CommandKind.RETURN_HOME:
            self._robot.return_home()
            return
        if command.kind == CommandKind.DOCK_SHELF:
            self._robot.dock_shelf()
            return
        if command.kind == CommandKind.UNDOCK_SHELF:
            self._robot.undock_shelf()
            return
        if command.kind == CommandKind.SPEAK:
            self._robot.speak(command.text)
            return

        if command.kind in {CommandKind.VELOCITY, CommandKind.WAYPOINT}:
            raise UnsupportedRobotCommandError(
                f"{command.kind.value!r} is not executable through the current "
                "Kachaka API wrapper. Add a cmd_vel/waypoint executor or extend "
                "KachakaRobotClient before using a continuous navigation model."
            )

        raise UnsupportedRobotCommandError(
            f"Unsupported navigation command: {command.kind.value}"
        )
