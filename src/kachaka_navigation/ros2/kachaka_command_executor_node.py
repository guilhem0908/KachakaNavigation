from __future__ import annotations

import logging

from kachaka_navigation.core.interfaces import CommandExecutor
from kachaka_navigation.robot import LoggingCommandExecutor
from kachaka_navigation.ros2.availability import (
    import_ros2_core,
    import_ros2_node_base,
)
from kachaka_navigation.ros2.json_messages import command_from_ros_json


logger = logging.getLogger(__name__)
RosNodeBase = import_ros2_node_base()


class Ros2KachakaCommandExecutorNode(RosNodeBase):
    """Kachaka-side node: robot command topic -> Kachaka API executor."""

    def __init__(
        self,
        *,
        robot_command_topic: str,
        dry_run: bool = False,
        node_name: str = "kachaka_command_executor",
    ) -> None:
        _, _, _, _, _, string_type = import_ros2_core()
        super().__init__(node_name)

        self._executor = _build_executor(dry_run=dry_run)
        self._subscription = self.create_subscription(
            string_type,
            robot_command_topic,
            self._on_command,
            1,
        )
        self.get_logger().info(f"command_executor subscribed to {robot_command_topic}")

    def _on_command(self, message: object) -> None:
        try:
            command, _ = command_from_ros_json(str(getattr(message, "data")))
            self._executor.execute(command)
        except Exception as error:
            logger.exception("Could not execute Kachaka command")
            self.get_logger().error(f"Could not execute Kachaka command: {error}")


def _build_executor(dry_run: bool) -> CommandExecutor:
    if dry_run:
        return LoggingCommandExecutor()

    from kachaka_navigation.robot import KachakaCommandExecutor

    return KachakaCommandExecutor.from_settings()
