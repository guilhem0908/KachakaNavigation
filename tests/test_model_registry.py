from kachaka_navigation.models import (
    ConstantVelocityModel,
    NoopNavigationModel,
    build_default_registry,
)


def test_default_registry_contains_builtin_models() -> None:
    registry = build_default_registry()

    assert registry.names() == (
        ConstantVelocityModel.name,
        NoopNavigationModel.name,
    )
    assert registry.create("noop").name == "noop"
