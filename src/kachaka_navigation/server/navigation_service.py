from __future__ import annotations

import logging

from kachaka_navigation.core.interfaces import NavigationModel
from kachaka_navigation.core.messages import (
    ImageFrame,
    NavigationCommand,
    RobotState,
)


logger = logging.getLogger(__name__)


class NavigationService:
    """Runs one navigation model behind a stable server-facing API."""

    def __init__(self, model: NavigationModel) -> None:
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model.name

    def reset(self) -> None:
        logger.info("Resetting navigation model: %s", self.model_name)
        self._model.reset()

    def predict_command(
        self,
        frame: ImageFrame,
        state: RobotState | None = None,
    ) -> NavigationCommand:
        try:
            return self._model.predict(frame=frame, state=state)
        except Exception as error:
            logger.exception("Navigation model %s failed", self.model_name)
            return NavigationCommand.stop(
                f"Navigation model {self.model_name} failed: {error}"
            )
