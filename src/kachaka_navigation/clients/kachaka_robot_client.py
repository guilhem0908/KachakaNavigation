import logging
from typing import Any

from grpc import RpcError, StatusCode
from kachaka_api import KachakaApiClient

from kachaka_navigation.connectivity import ensure_tcp_connection


logger = logging.getLogger(__name__)


class KachakaRobotClient:
    def __init__(self, target: str, connect_timeout_seconds: float = 2.0) -> None:
        logger.info("Initializing Kachaka API client for target %s", target)
        self._target = target
        host, port = self._parse_target(target)
        ensure_tcp_connection(host, port, timeout_seconds=connect_timeout_seconds)
        self._client = KachakaApiClient(target=target)

    def refresh_resolver(self) -> None:
        logger.info("Refreshing Kachaka location/shelf resolver")
        self._client.update_resolver()

    def refresh_locations(self) -> None:
        logger.info("Refreshing Kachaka location resolver")
        self._client.resolver.set_locations(self._client.get_locations())

    def get_robot_pose(self) -> Any:
        logger.info("Requesting robot pose")
        return self._client.get_robot_pose()

    def get_locations(self) -> Any:
        logger.info("Requesting registered locations")
        return self._client.get_locations()

    def get_shelves(self) -> Any:
        logger.info("Requesting registered shelves")
        return self._client.get_shelves()

    def speak(self, text: str) -> Any:
        logger.info("Sending speak command")
        return self._client.speak(text)

    def move_to_location(self, location_id_or_name: str) -> Any:
        logger.info("Moving to location: %s", location_id_or_name)
        return self._client.move_to_location(
            location_id_or_name,
            wait_for_completion=True,
            title=f"Move to {location_id_or_name}",
        )

    def return_home(self) -> Any:
        logger.info("Returning to charger")
        return self._client.return_home(
            wait_for_completion=True,
            title="Return home",
        )

    def dock_shelf(self) -> Any:
        logger.info("Docking shelf")
        return self._client.dock_shelf(
            wait_for_completion=True,
            title="Dock shelf",
        )

    def dock_shelf_at_location(self, location_id_or_name: str) -> Any:
        logger.info("Moving to location %s before docking shelf", location_id_or_name)
        self.move_to_location(location_id_or_name)
        return self.dock_shelf()

    def undock_shelf(self) -> Any:
        logger.info("Undocking shelf")
        return self._client.undock_shelf(
            wait_for_completion=True,
            title="Undock shelf",
        )

    def move_shelf(self, shelf_id_or_name: str, location_id_or_name: str) -> Any:
        logger.info(
            "Moving shelf %s to location %s",
            shelf_id_or_name,
            location_id_or_name,
        )
        return self._client.move_shelf(
            shelf_id_or_name,
            location_id_or_name,
            wait_for_completion=True,
            title=f"Move shelf {shelf_id_or_name} to {location_id_or_name}",
        )

    def return_shelf(self, shelf_id_or_name: str) -> Any:
        logger.info("Returning shelf: %s", shelf_id_or_name)
        return self._client.return_shelf(
            shelf_id_or_name,
            wait_for_completion=True,
            title=f"Return shelf {shelf_id_or_name}",
        )

    def dock_any_shelf_with_registration(
        self,
        location_id_or_name: str,
        dock_forward: bool = False,
    ) -> Any:
        logger.info(
            "Going to location %s and docking any registered shelf",
            location_id_or_name,
        )
        try:
            return self._client.dock_any_shelf_with_registration(
                location_id_or_name,
                dock_forward=dock_forward,
                wait_for_completion=True,
                title=f"Dock shelf at {location_id_or_name}",
            )
        except RpcError as error:
            if not self._is_unavailable_for_robot_model(error):
                raise

            logger.warning(
                "dock_any_shelf_with_registration is unavailable for this robot model. "
                "Falling back to move_to_location + dock_shelf."
            )
            if dock_forward:
                logger.warning(
                    "The --forward option is ignored by the fallback because dock_shelf "
                    "does not expose a dock_forward parameter."
                )
            return self.dock_shelf_at_location(location_id_or_name)

    def cancel_command(self) -> Any:
        logger.info("Canceling current command")
        return self._client.cancel_command()

    @staticmethod
    def _is_unavailable_for_robot_model(error: RpcError) -> bool:
        details = error.details() or ""
        return (
            error.code() == StatusCode.UNAVAILABLE
            and "Unavailable for this robot model" in details
        )

    @staticmethod
    def _parse_target(target: str) -> tuple[str, int]:
        host, separator, port = target.rpartition(":")
        if not separator or not host or not port:
            raise ValueError(f"Invalid Kachaka target: {target!r}")
        return host, int(port)
