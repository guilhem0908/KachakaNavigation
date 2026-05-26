from __future__ import annotations

from dataclasses import dataclass

from kachaka_navigation.core.messages import (
    ImageFrame,
    NavigationCommand,
    RobotState,
)


@dataclass(frozen=True, slots=True)
class ConstantVelocityConfig:
    linear_x: float = 0.05
    angular_z: float = 0.0
    duration_seconds: float = 0.2


class ConstantVelocityModel:
    """Small test model that emits a fixed low-level velocity command."""

    name = "constant_velocity"

    def __init__(self, config: ConstantVelocityConfig | None = None) -> None:
        self._config = config or ConstantVelocityConfig()

    def reset(self) -> None:
        return None

    def predict(
        self,
        frame: ImageFrame,
        state: RobotState | None = None,
    ) -> NavigationCommand:
        return NavigationCommand.from_velocity(
            linear_x=self._config.linear_x,
            angular_z=self._config.angular_z,
            duration_seconds=self._config.duration_seconds,
        )
