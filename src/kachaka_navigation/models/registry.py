from __future__ import annotations

from collections.abc import Callable

from kachaka_navigation.core.interfaces import NavigationModel
from kachaka_navigation.models.constant_velocity import (
    ConstantVelocityConfig,
    ConstantVelocityModel,
)
from kachaka_navigation.models.nomad_original import (
    NomadOriginalConfig,
    NomadOriginalModel,
)
from kachaka_navigation.models.noop import NoopNavigationModel


ModelFactory = Callable[[], NavigationModel]


class NavigationModelRegistry:
    """Registry of model factories available to the navigation server."""

    def __init__(self) -> None:
        self._factories: dict[str, ModelFactory] = {}

    def register(self, name: str, factory: ModelFactory) -> None:
        if not name:
            raise ValueError("Model name must not be empty.")
        if name in self._factories:
            raise ValueError(f"Navigation model already registered: {name}")

        self._factories[name] = factory

    def create(self, name: str) -> NavigationModel:
        try:
            factory = self._factories[name]
        except KeyError as exc:
            available = ", ".join(self.names()) or "<none>"
            raise ValueError(
                f"Unknown navigation model {name!r}. Available models: {available}"
            ) from exc

        return factory()

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._factories))


def build_default_registry(
    nomad_config: NomadOriginalConfig | None = None,
    constant_velocity_config: ConstantVelocityConfig | None = None,
) -> NavigationModelRegistry:
    registry = NavigationModelRegistry()
    registry.register(NoopNavigationModel.name, NoopNavigationModel)
    registry.register(
        ConstantVelocityModel.name,
        lambda: ConstantVelocityModel(config=constant_velocity_config),
    )

    if nomad_config is not None:
        registry.register(
            NomadOriginalModel.name,
            lambda: NomadOriginalModel(config=nomad_config),
        )

    return registry
