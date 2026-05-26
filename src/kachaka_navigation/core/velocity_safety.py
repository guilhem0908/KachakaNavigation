from __future__ import annotations

from dataclasses import dataclass

from kachaka_navigation.core.messages import VelocityCommand


@dataclass(frozen=True, slots=True)
class VelocitySafetyLimits:
    """Bounds and dead-man timing for low-level velocity control."""

    max_linear_x: float = 0.2
    max_angular_z: float = 0.5
    default_duration_seconds: float = 0.25
    max_duration_seconds: float = 1.0

    def __post_init__(self) -> None:
        if self.max_linear_x <= 0:
            raise ValueError("max_linear_x must be positive.")
        if self.max_angular_z <= 0:
            raise ValueError("max_angular_z must be positive.")
        if self.default_duration_seconds <= 0:
            raise ValueError("default_duration_seconds must be positive.")
        if self.max_duration_seconds <= 0:
            raise ValueError("max_duration_seconds must be positive.")
        if self.default_duration_seconds > self.max_duration_seconds:
            raise ValueError(
                "default_duration_seconds must be lower than max_duration_seconds."
            )

    def clamp(self, velocity: VelocityCommand) -> VelocityCommand:
        return VelocityCommand(
            linear_x=_clamp(
                velocity.linear_x,
                -self.max_linear_x,
                self.max_linear_x,
            ),
            angular_z=_clamp(
                velocity.angular_z,
                -self.max_angular_z,
                self.max_angular_z,
            ),
            duration_seconds=self.resolve_duration_seconds(velocity),
        )

    def resolve_duration_seconds(self, velocity: VelocityCommand) -> float:
        duration = velocity.duration_seconds
        if duration is None:
            return self.default_duration_seconds
        return min(duration, self.max_duration_seconds)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))
