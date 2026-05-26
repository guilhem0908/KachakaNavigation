from __future__ import annotations

from typing import Any

from kachaka_navigation.ros2.availability import (
    import_ros2_core,
    import_ros2_node_base,
)
from kachaka_navigation.ros2.qos import sensor_qos_profile


RosNodeBase = import_ros2_node_base()


class Ros2ImageSenderNode(RosNodeBase):
    """Kachaka/camera-side node: relay any camera topic to the server image topic."""

    def __init__(
        self,
        *,
        input_image_topic: str,
        output_image_topic: str,
        image_type: str = "raw",
        node_name: str = "kachaka_image_sender",
    ) -> None:
        _, _, qos_profile_sensor_data, raw_image_type, compressed_image_type, _ = (
            import_ros2_core()
        )
        super().__init__(node_name)

        if image_type not in {"raw", "compressed"}:
            raise ValueError("image_type must be either 'raw' or 'compressed'.")

        ros_image_type = compressed_image_type if image_type == "compressed" else raw_image_type
        qos_profile = sensor_qos_profile(qos_profile_sensor_data)
        self._publisher = self.create_publisher(ros_image_type, output_image_topic, qos_profile)
        self._subscription = self.create_subscription(
            ros_image_type,
            input_image_topic,
            self._on_image,
            qos_profile,
        )
        self.get_logger().info(
            f"image_sender relaying {input_image_topic} "
            f"({image_type}) to {output_image_topic}"
        )

    def _on_image(self, message: Any) -> None:
        self._publisher.publish(message)
