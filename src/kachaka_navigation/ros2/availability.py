from __future__ import annotations

from typing import Any


def import_ros2_core() -> tuple[Any, type[Any], Any, type[Any], type[Any], type[Any]]:
    try:
        import rclpy
        from rclpy.node import Node
        from rclpy.qos import qos_profile_sensor_data
        from sensor_msgs.msg import CompressedImage, Image
        from std_msgs.msg import String
    except ImportError as exc:
        raise RuntimeError(
            "ROS2 support requires rclpy, sensor_msgs, std_msgs, and a sourced "
            "ROS2 environment. Use the ROS2 Docker image or source your ROS2 "
            "installation before running this node."
        ) from exc

    return rclpy, Node, qos_profile_sensor_data, Image, CompressedImage, String


def import_ros2_node_base() -> type[Any]:
    try:
        from rclpy.node import Node
    except ImportError:
        return object

    return Node
