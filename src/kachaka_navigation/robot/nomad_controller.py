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


class ReleasableVelocitySink:
    """Velocity sink that can be permanently released (then drops commands).

    Needed when control is handed back to the robot mid-session (e.g.
    return_home after reaching a goal): kachaka-api's set_robot_velocity
    silently re-enables manual control and retries when a send fails, which
    would cancel the running command — or drive a freshly docked robot off
    its charger. Once released, velocity commands are dropped instead.
    """

    def __init__(self, sink: VelocitySink) -> None:
        self._sink = sink
        self._released = False

    @property
    def released(self) -> bool:
        return self._released

    def release(self) -> None:
        self._released = True

    def __call__(self, linear: float, angular: float) -> None:
        if self._released:
            logger.debug(
                "Velocity sink released; dropping (%.3f, %.3f).", linear, angular
            )
            return
        self._sink(linear, angular)


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
        on_goal_reached: Callable[[], None] | None = None,
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
        self._on_goal_reached = on_goal_reached

    def step(self) -> tuple[NavigationCommand, float, float]:
        """Run one perception->action cycle. Returns (command, linear, angular)."""
        frame = self._camera()
        command = self._model.predict(frame)
        linear, angular = command_to_velocity(command, self._limits)
        self._velocity_sink(linear, angular)
        return command, linear, angular

    def run(self, max_iterations: int | None = None) -> int:
        """Run the control loop. Guarantees a zero-velocity stop on exit.

        Exits early when the model reports the goal image has been reached
        (command metadata ``goal_reached``), running the ``on_goal_reached``
        action if one was provided. Returns the number of iterations executed.
        """
        iterations = 0
        try:
            while max_iterations is None or iterations < max_iterations:
                start = self._clock()
                try:
                    command, linear, angular = self.step()
                    extras = "".join(
                        f" {key}={command.metadata[key]}"
                        for key in (
                            "goal_distance",
                            "goal_similarity",
                            "goal_visibility",
                            "goal_contrast",
                            "goal_bearing_deg",
                        )
                        if command.metadata.get(key) is not None
                    )
                    logger.info(
                        "iter=%d kind=%s -> linear=%.3f angular=%.3f%s",
                        iterations,
                        command.kind.value,
                        linear,
                        angular,
                        extras,
                    )
                except Exception:
                    logger.exception("NoMaD control step failed; stopping robot.")
                    self._safe_stop()
                    raise
                iterations += 1
                if command.metadata.get("goal_reached"):
                    logger.info(
                        "Goal reached (predicted distance %s); stopping.",
                        command.metadata.get("goal_distance"),
                    )
                    self._safe_stop()
                    if self._on_goal_reached is not None:
                        try:
                            self._on_goal_reached()
                        except Exception:
                            logger.exception("on_goal_reached action failed.")
                    break
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
