from kachaka_navigation.models import NoopNavigationModel, build_default_registry


def test_default_registry_contains_noop_model() -> None:
    registry = build_default_registry()

    assert registry.names() == (NoopNavigationModel.name,)
    assert registry.create("noop").name == "noop"
