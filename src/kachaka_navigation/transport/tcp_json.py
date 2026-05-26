from __future__ import annotations

import logging
import socket
import socketserver
from types import TracebackType

from kachaka_navigation.core.messages import (
    ImageFrame,
    NavigationCommand,
    RobotState,
)
from kachaka_navigation.core.serialization import (
    error_response_to_json,
    request_from_json,
    request_to_json,
    response_from_json,
    response_to_json,
)
from kachaka_navigation.server.navigation_service import NavigationService


logger = logging.getLogger(__name__)


class NavigationTcpClient:
    """Small JSON-lines TCP client used by the robot process."""

    def __init__(
        self,
        host: str,
        port: int,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._host = host
        self._port = port
        self._timeout_seconds = timeout_seconds

    def request_command(
        self,
        frame: ImageFrame,
        state: RobotState | None = None,
    ) -> NavigationCommand:
        request = request_to_json(frame=frame, state=state)
        with socket.create_connection(
            (self._host, self._port),
            timeout=self._timeout_seconds,
        ) as connection:
            connection.settimeout(self._timeout_seconds)
            stream = connection.makefile("rwb")
            stream.write(f"{request}\n".encode("utf-8"))
            stream.flush()

            raw_response = stream.readline()
            if not raw_response:
                raise RuntimeError("Navigation server closed the connection.")

        return response_from_json(raw_response.decode("utf-8"))


class NavigationTcpServer:
    """Threaded JSON-lines TCP server around NavigationService."""

    def __init__(
        self,
        host: str,
        port: int,
        service: NavigationService,
    ) -> None:
        self._server = _ThreadedNavigationServer(
            (host, port),
            _NavigationRequestHandler,
            service,
        )

    @property
    def server_address(self) -> tuple[str, int]:
        host, port = self._server.server_address
        return str(host), int(port)

    def serve_forever(self) -> None:
        host, port = self.server_address
        logger.info("Navigation TCP server listening on %s:%s", host, port)
        self._server.serve_forever()

    def shutdown(self) -> None:
        self._server.shutdown()

    def close(self) -> None:
        self._server.server_close()

    def __enter__(self) -> NavigationTcpServer:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


class _ThreadedNavigationServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        request_handler_class: type[socketserver.StreamRequestHandler],
        service: NavigationService,
    ) -> None:
        super().__init__(server_address, request_handler_class)
        self.service = service


class _NavigationRequestHandler(socketserver.StreamRequestHandler):
    server: _ThreadedNavigationServer

    def handle(self) -> None:
        raw_request = self.rfile.readline()
        if not raw_request:
            return

        try:
            frame, state = request_from_json(raw_request.decode("utf-8"))
            command = self.server.service.predict_command(frame=frame, state=state)
            raw_response = response_to_json(command)
        except Exception as error:
            logger.exception("Navigation request failed")
            raw_response = error_response_to_json(error)

        self.wfile.write(f"{raw_response}\n".encode("utf-8"))
        self.wfile.flush()
