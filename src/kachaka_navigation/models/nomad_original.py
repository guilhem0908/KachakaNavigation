from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path

from kachaka_navigation.core.messages import (
    ImageFrame,
    NavigationCommand,
    RobotState,
)


class NomadOriginalUnavailableError(RuntimeError):
    """Raised when the NoMaD adapter is selected before it is wired."""


@dataclass(frozen=True, slots=True)
class NomadOriginalConfig:
    """Configuration for the original NoMaD VisualNav adapter."""

    checkpoint_path: Path
    model_config_path: Path | None = None
    goal_image_path: Path | None = None
    device: str = "cpu"
    context_size: int = 5


class NomadOriginalModel:
    """Adapter boundary for robodhruv/visualnav-transformer NoMaD.

    The original project is ROS-oriented: camera images are accumulated into a
    context queue, NoMaD predicts a local waypoint, and a controller translates
    that waypoint into robot motion. This class keeps that contract isolated so
    the Kachaka transport and command execution code do not depend on PyTorch,
    ROS, or the original repository layout.
    """

    name = "nomad_original"

    def __init__(self, config: NomadOriginalConfig) -> None:
        if config.context_size <= 0:
            raise ValueError("NomadOriginalConfig.context_size must be positive.")

        self._config = config
        self._context: deque[ImageFrame] = deque(maxlen=config.context_size)

    def reset(self) -> None:
        self._context.clear()

    def predict(
        self,
        frame: ImageFrame,
        state: RobotState | None = None,
    ) -> NavigationCommand:
        self._context.append(frame)
        if len(self._context) < self._config.context_size:
            return NavigationCommand.stop(
                "Waiting for enough image context for NoMaD."
            )

        raise NomadOriginalUnavailableError(
            "NoMaD original is selected, but the PyTorch VisualNav adapter is "
            "not wired yet. Clone robodhruv/visualnav-transformer, load the "
            "NoMaD checkpoint in this class, and convert the predicted waypoint "
            "to NavigationCommand.waypoint(...)."
        )
