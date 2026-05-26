from __future__ import annotations

import logging
from typing import Any

from kachaka_navigation.core.messages import NavigationCommand
from kachaka_navigation.core.realtime import ImageFreshnessPolicy
from kachaka_navigation.ros2.availability import (
    import_ros2_core,
    import_ros2_node_base,
)
from kachaka_navigation.ros2.conversion import (
    Ros2ImageFrameConverter,
    compressed_ros_image_to_frame,
)
from kachaka_navigation.ros2.json_messages import command_to_ros_json
from kachaka_navigation.ros2.qos import sensor_qos_profile
from kachaka_navigation.server import NavigationService


logger = logging.getLogger(__name__)
RosNodeBase = import_ros2_node_base()


class Ros2TrajectoryGeneratorNode(RosNodeBase):
    """Server node: image topic -> navigation model -> trajectory topic."""

    def __init__(
        self,
        *,
        service: NavigationService,
        image_topic: str,
        trajectory_topic: str,
        image_type: str = "raw",
        jpeg_quality: int = 85,
        max_image_age_seconds: float = 0.5,
        node_name: str = "kachaka_trajectory_generator",
    ) -> None:
        _, _, qos_profile_sensor_data, raw_image_type, compressed_image_type, string_type = (
            import_ros2_core()
        )
        super().__init__(node_name)

        if image_type not in {"raw", "compressed"}:
            raise ValueError("image_type must be either 'raw' or 'compressed'.")
        if not 1 <= jpeg_quality <= 100:
            raise ValueError("jpeg_quality must be between 1 and 100.")

        self._service = service
        self._image_topic = image_topic
        self._image_type = image_type
        self._image_converter = Ros2ImageFrameConverter(jpeg_quality=jpeg_quality)
        self._string_type = string_type
        self._freshness_policy = ImageFreshnessPolicy(
            max_age_seconds=max_image_age_seconds,
            require_timestamp=False,
        )

        ros_image_type = compressed_image_type if image_type == "compressed" else raw_image_type
        self._publisher = self.create_publisher(string_type, trajectory_topic, 1)
        self._subscription = self.create_subscription(
            ros_image_type,
            image_topic,
            self._on_image,
            sensor_qos_profile(qos_profile_sensor_data),
        )
        self.get_logger().info(
            f"trajectory_generator subscribed to {image_topic} "
            f"({image_type}) and publishing {trajectory_topic}"
        )

    def _on_image(self, message: Any) -> None:
        now_seconds = self._now_seconds()
        try:
            frame = self._image_frame_from_message(message, now_seconds)
            freshness = self._freshness_policy.check(frame, now_seconds)
            if freshness.is_fresh:
                command = self._service.predict_command(frame=frame)
            else:
                self.get_logger().warning(freshness.reason)
                command = NavigationCommand.stop(freshness.reason)
        except Exception as error:
            logger.exception("Trajectory generation failed")
            command = NavigationCommand.stop(f"Trajectory generation failed: {error}")

        self._publisher.publish(
            self._string_type(data=command_to_ros_json(command, now_seconds))
        )

    def _image_frame_from_message(self, message: Any, received_at_seconds: float) -> Any:
        if self._image_type == "compressed":
            return compressed_ros_image_to_frame(
                message,
                received_at_seconds=received_at_seconds,
                source_topic=self._image_topic,
            )

        return self._image_converter.raw_image_to_frame(
            message,
            received_at_seconds=received_at_seconds,
            source_topic=self._image_topic,
        )

    def _now_seconds(self) -> float:
        return self.get_clock().now().nanoseconds / 1_000_000_000.0
