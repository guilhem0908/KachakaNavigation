from __future__ import annotations

from kachaka_navigation.core.messages import (
    ImageFrame,
    NavigationCommand,
    RobotState,
)


class NoopNavigationModel:
    """Fail-safe model used for wiring tests and dry runs."""

    name = "noop"

    def reset(self) -> None:
        return None

    def predict(
        self,
        frame: ImageFrame,
        state: RobotState | None = None,
    ) -> NavigationCommand:
        return NavigationCommand.stop("No navigation model is active.")
