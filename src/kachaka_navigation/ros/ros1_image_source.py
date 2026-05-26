from __future__ import annotations

import logging
from collections.abc import Iterator
from queue import Queue
from typing import Any

from kachaka_navigation.core.messages import ImageFrame


logger = logging.getLogger(__name__)


class Ros1ImageTopicSource:
    """ROS1 sensor_msgs/Image source compressed to JPEG ImageFrame messages."""

    def __init__(
        self,
        topic: str,
        node_name: str = "kachaka_navigation_image_source",
        queue_size: int = 1,
        jpeg_quality: int = 85,
    ) -> None:
        if queue_size <= 0:
            raise ValueError("queue_size must be positive.")
        if not 1 <= jpeg_quality <= 100:
            raise ValueError("jpeg_quality must be between 1 and 100.")

        self._topic = topic
        self._node_name = node_name
        self._queue: Queue[ImageFrame] = Queue(maxsize=queue_size)
        self._jpeg_quality = jpeg_quality
        self._bridge: Any | None = None
        self._cv2: Any | None = None

    def frames(self) -> Iterator[ImageFrame]:
        rospy, image_message = _import_ros_dependencies()
        if not rospy.core.is_initialized():
            rospy.init_node(self._node_name, anonymous=True, disable_signals=True)

        rospy.Subscriber(self._topic, image_message, self._on_image, queue_size=1)
        logger.info("Subscribed to ROS image topic: %s", self._topic)

        while not rospy.is_shutdown():
            yield self._queue.get()

    def _on_image(self, message: Any) -> None:
        cv2, bridge = self._get_cv_bridge()
        cv_image = bridge.imgmsg_to_cv2(message, desired_encoding="bgr8")
        encode_args = [int(cv2.IMWRITE_JPEG_QUALITY), self._jpeg_quality]
        success, encoded = cv2.imencode(".jpg", cv_image, encode_args)
        if not success:
            logger.warning("Failed to encode ROS image as JPEG")
            return

        frame = ImageFrame(
            data=encoded.tobytes(),
            encoding="jpeg",
            width=int(getattr(message, "width", 0)) or None,
            height=int(getattr(message, "height", 0)) or None,
            frame_id=_frame_id_from_message(message),
            timestamp=_timestamp_from_message(message),
            metadata={"source_topic": self._topic},
        )
        _put_latest(self._queue, frame)

    def _get_cv_bridge(self) -> tuple[Any, Any]:
        if self._bridge is None:
            try:
                import cv2
                from cv_bridge import CvBridge
            except ImportError as exc:
                raise RuntimeError(
                    "ROS image conversion requires cv_bridge and opencv-python "
                    "in the active Python environment."
                ) from exc

            self._bridge = CvBridge()
            self._cv2 = cv2

        if self._cv2 is None or self._bridge is None:
            raise RuntimeError("OpenCV bridge is not initialized.")

        return self._cv2, self._bridge


def _import_ros_dependencies() -> tuple[Any, type]:
    try:
        import rospy
        from sensor_msgs.msg import Image
    except ImportError as exc:
        raise RuntimeError(
            "ROS1 image subscriptions require rospy and sensor_msgs to be "
            "installed in the active Python environment."
        ) from exc

    return rospy, Image


def _frame_id_from_message(message: Any) -> str:
    header = getattr(message, "header", None)
    return str(getattr(header, "frame_id", "")) if header is not None else ""


def _timestamp_from_message(message: Any) -> float | None:
    header = getattr(message, "header", None)
    stamp = getattr(header, "stamp", None) if header is not None else None
    if stamp is None:
        return None
    if hasattr(stamp, "to_sec"):
        return float(stamp.to_sec())
    return None


def _put_latest(queue: Queue[ImageFrame], frame: ImageFrame) -> None:
    if queue.full():
        queue.get_nowait()
    queue.put_nowait(frame)
