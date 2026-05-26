from kachaka_navigation.core.messages import CommandKind, ImageFrame
from kachaka_navigation.models import NoopNavigationModel
from kachaka_navigation.server import NavigationService


def test_navigation_service_returns_stop_for_noop_model() -> None:
    service = NavigationService(NoopNavigationModel())
    frame = ImageFrame(data=b"image", encoding="jpeg")

    command = service.predict_command(frame)

    assert command.kind == CommandKind.STOP
