from __future__ import annotations

import logging
import time
from collections.abc import Iterator

from kachaka_navigation.core.interfaces import (
    CommandExecutor,
    CommandTransport,
    ImageSource,
)
from kachaka_navigation.core.messages import ImageFrame, NavigationCommand


logger = logging.getLogger(__name__)


class RobotNavigationClient:
    """Robot-side loop: image source -> server transport -> command executor."""

    def __init__(
        self,
        image_source: ImageSource,
        transport: CommandTransport,
        command_executor: CommandExecutor,
        min_period_seconds: float = 0.0,
    ) -> None:
        if min_period_seconds < 0:
            raise ValueError("min_period_seconds must not be negative.")

        self._image_source = image_source
        self._transport = transport
        self._command_executor = command_executor
        self._min_period_seconds = min_period_seconds
        self._frame_iterator: Iterator[ImageFrame] | None = None

    def run_once(self) -> NavigationCommand:
        if self._frame_iterator is None:
            self._frame_iterator = iter(self._image_source.frames())

        frame = next(self._frame_iterator)
        command = self._transport.request_command(frame=frame)
        self._command_executor.execute(command)
        return command

    def run_forever(self) -> None:
        for frame in self._image_source.frames():
            started_at = time.monotonic()
            command = self._transport.request_command(frame=frame)
            self._command_executor.execute(command)
            logger.debug("Applied navigation command: %s", command.kind.value)
            self._sleep_for_rate_limit(started_at)

    def _sleep_for_rate_limit(self, started_at: float) -> None:
        elapsed = time.monotonic() - started_at
        remaining = self._min_period_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)
