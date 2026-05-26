import socket
from dataclasses import dataclass


DEFAULT_CONNECT_TIMEOUT_SECONDS = 2.0


class KachakaConnectionError(ConnectionError):
    pass


@dataclass(frozen=True)
class ConnectivityCheck:
    host: str
    port: int
    ok: bool
    error: str = ""


def check_tcp_connection(
    host: str,
    port: int,
    timeout_seconds: float = DEFAULT_CONNECT_TIMEOUT_SECONDS,
) -> ConnectivityCheck:
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return ConnectivityCheck(host=host, port=port, ok=True)
    except OSError as error:
        return ConnectivityCheck(
            host=host,
            port=port,
            ok=False,
            error=str(error),
        )


def ensure_tcp_connection(
    host: str,
    port: int,
    timeout_seconds: float = DEFAULT_CONNECT_TIMEOUT_SECONDS,
) -> None:
    check = check_tcp_connection(host, port, timeout_seconds=timeout_seconds)
    if check.ok:
        return

    raise KachakaConnectionError(
        f"Could not connect to Kachaka API at {host}:{port} "
        f"within {timeout_seconds:.1f}s. Details: {check.error}"
    )
