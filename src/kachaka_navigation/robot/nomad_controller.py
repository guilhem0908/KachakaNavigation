"""Native control loop: Kachaka camera -> NoMaD -> base velocity.

This drives a Kachaka directly from this machine over kachaka-api (gRPC), with no
ROS in the loop. The camera source and velocity sink are injected so the loop can
be unit-tested with fakes.
"""
from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass

from kachaka_navigation.core.messages import (
    CommandKind,
    ImageFrame,
    NavigationCommand,
)

logger = logging.getLogger(__name__)

CameraSource = Callable[[], ImageFrame]
VelocitySink = Callable[[float, float], None]


@dataclass(frozen=True, slots=True)
class VelocityLimits:
    max_linear_speed: float = 0.2
    max_angular_speed: float = 0.4

    def clamp(self, linear: float, angular: float) -> tuple[float, float]:
        linear = max(-self.max_linear_speed, min(linear, self.max_linear_speed))
        angular = max(-self.max_angular_speed, min(angular, self.max_angular_speed))
        return linear, angular


def command_to_velocity(
    command: NavigationCommand,
    limits: VelocityLimits,
) -> tuple[float, float]:
    """Map a NavigationCommand onto a clamped (linear, angular) base velocity."""
    if command.kind == CommandKind.VELOCITY and command.velocity is not None:
        return limits.clamp(command.velocity.linear_x, command.velocity.angular_z)
    if command.kind in {CommandKind.STOP, CommandKind.NOOP, CommandKind.CANCEL}:
        return 0.0, 0.0
    logger.warning(
        "NoMaD controller received non-velocity command %s; stopping.",
        command.kind.value,
    )
    return 0.0, 0.0


class NomadKachakaController:
    """Pull a frame, run the model, send a velocity, repeat at a fixed rate."""

    def __init__(
        self,
        *,
        model: object,
        camera: CameraSource,
        velocity_sink: VelocitySink,
        limits: VelocityLimits | None = None,
        frame_rate: float = 4.0,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if frame_rate <= 0:
            raise ValueError("frame_rate must be positive.")
        self._model = model
        self._camera = camera
        self._velocity_sink = velocity_sink
        self._limits = limits or VelocityLimits()
        self._period = 1.0 / frame_rate
        self._clock = clock
        self._sleep = sleep

    def step(self) -> tuple[NavigationCommand, float, float]:
        """Run one perception->action cycle. Returns (command, linear, angular)."""
        frame = self._camera()
        command = self._model.predict(frame)
        linear, angular = command_to_velocity(command, self._limits)
        self._velocity_sink(linear, angular)
        return command, linear, angular

    def run(self, max_iterations: int | None = None) -> int:
        """Run the control loop. Guarantees a zero-velocity stop on exit.

        Returns the number of iterations executed.
        """
        iterations = 0
        try:
            while max_iterations is None or iterations < max_iterations:
                start = self._clock()
                try:
                    command, linear, angular = self.step()
                    logger.info(
                        "iter=%d kind=%s -> linear=%.3f angular=%.3f",
                        iterations,
                        command.kind.value,
                        linear,
                        angular,
                    )
                except Exception:
                    logger.exception("NoMaD control step failed; stopping robot.")
                    self._safe_stop()
                    raise
                iterations += 1
                elapsed = self._clock() - start
                remaining = self._period - elapsed
                if remaining > 0:
                    self._sleep(remaining)
        finally:
            self._safe_stop()
        return iterations

    def _safe_stop(self) -> None:
        try:
            self._velocity_sink(0.0, 0.0)
        except Exception:  # pragma: no cover - best-effort stop
            logger.exception("Failed to send zero-velocity stop.")
