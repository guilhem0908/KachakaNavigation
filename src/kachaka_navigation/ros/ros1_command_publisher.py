from __future__ import annotations

import json
import logging

from kachaka_navigation.core.messages import NavigationCommand
from kachaka_navigation.core.serialization import command_to_dict


logger = logging.getLogger(__name__)


class Ros1JsonCommandPublisher:
    """Publishes NavigationCommand payloads as std_msgs/String JSON."""

    def __init__(
        self,
        topic: str,
        node_name: str = "kachaka_navigation_command_publisher",
        queue_size: int = 1,
    ) -> None:
        rospy, string_message = _import_ros_dependencies()
        if not rospy.core.is_initialized():
            rospy.init_node(node_name, anonymous=True, disable_signals=True)

        self._publisher = rospy.Publisher(topic, string_message, queue_size=queue_size)
        self._message_type = string_message
        self._topic = topic

    def send(self, command: NavigationCommand) -> None:
        payload = json.dumps(command_to_dict(command), separators=(",", ":"))
        self._publisher.publish(self._message_type(data=payload))
        logger.debug("Published navigation command on %s", self._topic)


def _import_ros_dependencies() -> tuple[object, type]:
    try:
        import rospy
        from std_msgs.msg import String
    except ImportError as exc:
        raise RuntimeError(
            "ROS1 command publishing requires rospy and std_msgs to be installed "
            "in the active Python environment."
        ) from exc

    return rospy, String
