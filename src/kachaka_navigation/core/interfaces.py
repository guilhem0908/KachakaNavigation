from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from kachaka_navigation.core.messages import (
    ImageFrame,
    NavigationCommand,
    RobotState,
)


class ImageSource(Protocol):
    """Source of robot camera frames."""

    def frames(self) -> Iterable[ImageFrame]:
        """Yield camera frames in chronological order."""


class NavigationModel(Protocol):
    """Navigation model boundary.

    Model adapters should hide framework-specific details behind this small
    interface so the server can switch between NoMaD and future models.
    """

    @property
    def name(self) -> str:
        """Stable model name used in logs and CLI options."""

    def reset(self) -> None:
        """Reset per-episode state such as image context queues."""

    def predict(
        self,
        frame: ImageFrame,
        state: RobotState | None = None,
    ) -> NavigationCommand:
        """Return the next robot command for a camera frame."""


class CommandTransport(Protocol):
    """Client-side transport used by the robot process."""

    def request_command(
        self,
        frame: ImageFrame,
        state: RobotState | None = None,
    ) -> NavigationCommand:
        """Send one frame to the server and wait for the command response."""


class CommandExecutor(Protocol):
    """Applies navigation commands on the robot side."""

    def execute(self, command: NavigationCommand) -> None:
        """Execute a command or raise a specific error if unsupported."""
