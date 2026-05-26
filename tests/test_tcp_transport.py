from __future__ import annotations

from threading import Thread

from kachaka_navigation.core.messages import CommandKind, ImageFrame
from kachaka_navigation.models import NoopNavigationModel
from kachaka_navigation.server import NavigationService
from kachaka_navigation.transport import NavigationTcpClient, NavigationTcpServer


def test_tcp_client_gets_command_from_navigation_server() -> None:
    service = NavigationService(NoopNavigationModel())
    server = NavigationTcpServer("127.0.0.1", 0, service)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        host, port = server.server_address
        client = NavigationTcpClient(host=host, port=port)
        command = client.request_command(ImageFrame(data=b"image", encoding="jpeg"))
    finally:
        server.shutdown()
        server.close()
        thread.join(timeout=1.0)

    assert command.kind == CommandKind.STOP
