from __future__ import annotations

import pytest

from kachaka_navigation.core.messages import (
    CommandKind,
    ImageFrame,
    NavigationCommand,
)
from kachaka_navigation.robot.nomad_controller import (
    NomadKachakaController,
    VelocityLimits,
    command_to_velocity,
)


def _frame() -> ImageFrame:
    return ImageFrame(data=b"fake-jpeg", encoding="jpeg")


class _FakeModel:
    def __init__(self, command: NavigationCommand) -> None:
        self._command = command
        self.calls = 0

    def predict(self, frame, state=None):  # noqa: ANN001
        self.calls += 1
        return self._command


def test_command_to_velocity_passes_through_velocity_within_limits():
    limits = VelocityLimits(max_linear_speed=0.2, max_angular_speed=0.4)
    command = NavigationCommand.from_velocity(linear_x=0.1, angular_z=-0.2)
    assert command_to_velocity(command, limits) == (0.1, -0.2)


def test_command_to_velocity_clamps_to_limits():
    limits = VelocityLimits(max_linear_speed=0.1, max_angular_speed=0.2)
    command = NavigationCommand.from_velocity(linear_x=5.0, angular_z=-5.0)
    assert command_to_velocity(command, limits) == (0.1, -0.2)


@pytest.mark.parametrize("kind", [CommandKind.STOP, CommandKind.NOOP, CommandKind.CANCEL])
def test_command_to_velocity_stops_for_non_motion_commands(kind):
    limits = VelocityLimits()
    command = NavigationCommand(kind=kind)
    assert command_to_velocity(command, limits) == (0.0, 0.0)


def test_controller_runs_fixed_iterations_and_sends_velocity():
    model = _FakeModel(NavigationCommand.from_velocity(linear_x=0.1, angular_z=0.05))
    sent: list[tuple[float, float]] = []
    controller = NomadKachakaController(
        model=model,
        camera=_frame,
        velocity_sink=lambda v, w: sent.append((v, w)),
        limits=VelocityLimits(max_linear_speed=0.2, max_angular_speed=0.4),
        frame_rate=1000.0,
        sleep=lambda _seconds: None,
    )

    iterations = controller.run(max_iterations=3)

    assert iterations == 3
    assert model.calls == 3
    # 3 driving commands + a final zero-velocity safety stop.
    assert sent[:3] == [(0.1, 0.05)] * 3
    assert sent[-1] == (0.0, 0.0)


def test_controller_always_stops_on_error():
    class _BoomModel:
        def predict(self, frame, state=None):  # noqa: ANN001
            raise RuntimeError("boom")

    sent: list[tuple[float, float]] = []
    controller = NomadKachakaController(
        model=_BoomModel(),
        camera=_frame,
        velocity_sink=lambda v, w: sent.append((v, w)),
        frame_rate=1000.0,
        sleep=lambda _seconds: None,
    )

    with pytest.raises(RuntimeError, match="boom"):
        controller.run(max_iterations=5)

    # Even on failure, the last thing sent must be a stop.
    assert sent[-1] == (0.0, 0.0)


class _GoalReachedModel:
    """Drives for two frames, then reports the goal image as reached."""

    def __init__(self) -> None:
        self.calls = 0

    def predict(self, frame, state=None):  # noqa: ANN001
        self.calls += 1
        if self.calls < 3:
            return NavigationCommand.from_velocity(linear_x=0.1, angular_z=0.0)
        return NavigationCommand(
            kind=CommandKind.STOP,
            metadata={"goal_reached": True, "goal_distance": 1.5},
        )


def test_controller_stops_early_and_runs_action_on_goal_reached():
    sent: list[tuple[float, float]] = []
    actions: list[str] = []
    controller = NomadKachakaController(
        model=_GoalReachedModel(),
        camera=_frame,
        velocity_sink=lambda v, w: sent.append((v, w)),
        frame_rate=1000.0,
        sleep=lambda _seconds: None,
        on_goal_reached=lambda: actions.append("done"),
    )

    iterations = controller.run(max_iterations=10)

    assert iterations == 3  # 2 driving frames + the goal-reached frame
    assert actions == ["done"]
    assert sent[-1] == (0.0, 0.0)


def test_controller_goal_reached_without_action_still_stops():
    sent: list[tuple[float, float]] = []
    controller = NomadKachakaController(
        model=_GoalReachedModel(),
        camera=_frame,
        velocity_sink=lambda v, w: sent.append((v, w)),
        frame_rate=1000.0,
        sleep=lambda _seconds: None,
    )

    iterations = controller.run(max_iterations=10)

    assert iterations == 3
    assert sent[-1] == (0.0, 0.0)


def test_controller_goal_reached_action_failure_does_not_raise():
    def boom() -> None:
        raise RuntimeError("speaker offline")

    sent: list[tuple[float, float]] = []
    controller = NomadKachakaController(
        model=_GoalReachedModel(),
        camera=_frame,
        velocity_sink=lambda v, w: sent.append((v, w)),
        frame_rate=1000.0,
        sleep=lambda _seconds: None,
        on_goal_reached=boom,
    )

    iterations = controller.run(max_iterations=10)  # must not raise

    assert iterations == 3
    assert sent[-1] == (0.0, 0.0)


def test_controller_rejects_non_positive_frame_rate():
    with pytest.raises(ValueError):
        NomadKachakaController(
            model=_FakeModel(NavigationCommand.stop()),
            camera=_frame,
            velocity_sink=lambda v, w: None,
            frame_rate=0.0,
        )
