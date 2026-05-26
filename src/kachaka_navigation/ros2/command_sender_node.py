from __future__ import annotations

import logging

from kachaka_navigation.core.messages import NavigationCommand
from kachaka_navigation.ros2.availability import (
    import_ros2_core,
    import_ros2_node_base,
)
from kachaka_navigation.ros2.json_messages import (
    command_from_ros_json,
    command_to_ros_json,
)


logger = logging.getLogger(__name__)
RosNodeBase = import_ros2_node_base()


class Ros2CommandSenderNode(RosNodeBase):
    """Server node: validates generated trajectories and sends robot commands."""

    def __init__(
        self,
        *,
        trajectory_topic: str,
        robot_command_topic: str,
        max_command_age_seconds: float = 0.5,
        node_name: str = "kachaka_command_sender",
    ) -> None:
        _, _, _, _, _, string_type = import_ros2_core()
        super().__init__(node_name)

        if max_command_age_seconds <= 0:
            raise ValueError("max_command_age_seconds must be positive.")

        self._string_type = string_type
        self._max_command_age_seconds = max_command_age_seconds
        self._publisher = self.create_publisher(string_type, robot_command_topic, 1)
        self._subscription = self.create_subscription(
            string_type,
            trajectory_topic,
            self._on_trajectory,
            1,
        )
        self.get_logger().info(
            f"command_sender subscribed to {trajectory_topic} "
            f"and publishing {robot_command_topic}"
        )

    def _on_trajectory(self, message: object) -> None:
        now_seconds = self._now_seconds()
        try:
            raw_payload = str(getattr(message, "data"))
            command, generated_at = command_from_ros_json(raw_payload)
            if generated_at is not None:
                age_seconds = now_seconds - generated_at
                if age_seconds > self._max_command_age_seconds:
                    command = NavigationCommand.stop(
                        f"Command is too old: {age_seconds:.3f}s "
                        f"> {self._max_command_age_seconds:.3f}s."
                    )
            payload = command_to_ros_json(command, now_seconds)
        except Exception as error:
            logger.exception("Command sender failed")
            payload = command_to_ros_json(
                NavigationCommand.stop(f"Command sender failed: {error}"),
                now_seconds,
            )

        self._publisher.publish(self._string_type(data=payload))

    def _now_seconds(self) -> float:
        return self.get_clock().now().nanoseconds / 1_000_000_000.0
