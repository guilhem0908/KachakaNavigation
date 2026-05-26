from __future__ import annotations

from typing import Any

from kachaka_navigation.core.messages import ImageFrame


class Ros2ImageFrameConverter:
    def __init__(self, jpeg_quality: int = 85) -> None:
        if not 1 <= jpeg_quality <= 100:
            raise ValueError("jpeg_quality must be between 1 and 100.")

        self._jpeg_quality = jpeg_quality
        self._bridge: Any | None = None
        self._cv2: Any | None = None

    def raw_image_to_frame(
        self,
        message: Any,
        *,
        received_at_seconds: float,
        source_topic: str,
    ) -> ImageFrame:
        cv2, bridge = self._get_raw_image_dependencies()
        cv_image = bridge.imgmsg_to_cv2(message, desired_encoding="bgr8")
        success, encoded = cv2.imencode(
            ".jpg",
            cv_image,
            [int(cv2.IMWRITE_JPEG_QUALITY), self._jpeg_quality],
        )
        if not success:
            raise RuntimeError("Could not encode ROS2 Image as JPEG.")

        return ImageFrame(
            data=encoded.tobytes(),
            encoding="jpeg",
            width=int(getattr(message, "width", 0)) or None,
            height=int(getattr(message, "height", 0)) or None,
            frame_id=_frame_id_from_message(message),
            timestamp=_timestamp_from_message(message) or received_at_seconds,
            metadata={
                "received_at": received_at_seconds,
                "source_topic": source_topic,
                "source_type": "sensor_msgs/Image",
            },
        )

    def _get_raw_image_dependencies(self) -> tuple[Any, Any]:
        if self._bridge is None or self._cv2 is None:
            try:
                import cv2
                from cv_bridge import CvBridge
            except ImportError as exc:
                raise RuntimeError(
                    "Raw ROS2 Image conversion requires cv_bridge and OpenCV. "
                    "Use image-type=compressed to avoid cv_bridge."
                ) from exc

            self._cv2 = cv2
            self._bridge = CvBridge()

        return self._cv2, self._bridge


def raw_ros_image_to_frame(
    message: Any,
    *,
    jpeg_quality: int,
    received_at_seconds: float,
    source_topic: str,
) -> ImageFrame:
    return Ros2ImageFrameConverter(jpeg_quality).raw_image_to_frame(
        message,
        received_at_seconds=received_at_seconds,
        source_topic=source_topic,
    )


def compressed_ros_image_to_frame(
    message: Any,
    *,
    received_at_seconds: float,
    source_topic: str,
) -> ImageFrame:
    image_format = str(getattr(message, "format", "") or "compressed")
    return ImageFrame(
        data=bytes(getattr(message, "data", b"")),
        encoding=image_format,
        frame_id=_frame_id_from_message(message),
        timestamp=_timestamp_from_message(message) or received_at_seconds,
        metadata={
            "received_at": received_at_seconds,
            "source_topic": source_topic,
            "source_type": "sensor_msgs/CompressedImage",
        },
    )


def _frame_id_from_message(message: Any) -> str:
    header = getattr(message, "header", None)
    return str(getattr(header, "frame_id", "")) if header is not None else ""


def _timestamp_from_message(message: Any) -> float | None:
    header = getattr(message, "header", None)
    stamp = getattr(header, "stamp", None) if header is not None else None
    if stamp is None:
        return None

    seconds = float(getattr(stamp, "sec", 0))
    nanoseconds = float(getattr(stamp, "nanosec", 0))
    timestamp = seconds + nanoseconds / 1_000_000_000.0
    return timestamp if timestamp > 0 else None
