import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:

    def load_dotenv(_dotenv_path: Path) -> bool:
        return False


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"
DEFAULT_KACHAKA_PORT = 26400
DEFAULT_NAVIGATION_SERVER_BIND_HOST = "0.0.0.0"
DEFAULT_NAVIGATION_SERVER_HOST = "127.0.0.1"
DEFAULT_NAVIGATION_SERVER_PORT = 8765
DEFAULT_ROS_IMAGE_TOPIC = "/usb_cam/image_raw"
DEFAULT_ROS2_CAMERA_INPUT_TOPIC = "/camera/image_raw"
DEFAULT_ROS2_IMAGE_TOPIC = "/kachaka_navigation/image"
DEFAULT_ROS2_IMAGE_TYPE = "raw"
DEFAULT_ROS2_ROBOT_COMMAND_TOPIC = "/kachaka_navigation/robot_command"
DEFAULT_ROS2_TRAJECTORY_TOPIC = "/kachaka_navigation/trajectory"
DEFAULT_MAX_IMAGE_AGE_SECONDS = 0.5


@dataclass(frozen=True)
class KachakaSettings:
    host: str
    port: int
    speak_on_success: bool

    @property
    def target(self) -> str:
        return f"{self.host}:{self.port}"


@dataclass(frozen=True)
class NavigationSettings:
    server_bind_host: str
    server_host: str
    server_port: int
    ros_image_topic: str
    ros2_camera_input_topic: str
    ros2_image_topic: str
    ros2_image_type: str
    ros2_trajectory_topic: str
    ros2_robot_command_topic: str
    max_image_age_seconds: float


def get_kachaka_settings() -> KachakaSettings:
    load_dotenv(ENV_FILE)

    host = _get_required_env("KACHAKA_HOST")
    port = _get_int_env("KACHAKA_PORT", DEFAULT_KACHAKA_PORT)
    speak_on_success = _get_bool_env("KACHAKA_SPEAK_ON_SUCCESS", default=True)

    return KachakaSettings(
        host=host,
        port=port,
        speak_on_success=speak_on_success,
    )


def get_navigation_settings() -> NavigationSettings:
    load_dotenv(ENV_FILE)

    return NavigationSettings(
        server_bind_host=_get_str_env(
            "NAV_SERVER_BIND_HOST",
            DEFAULT_NAVIGATION_SERVER_BIND_HOST,
        ),
        server_host=_get_str_env(
            "NAV_SERVER_HOST",
            DEFAULT_NAVIGATION_SERVER_HOST,
        ),
        server_port=_get_int_env(
            "NAV_SERVER_PORT",
            DEFAULT_NAVIGATION_SERVER_PORT,
        ),
        ros_image_topic=_get_str_env("ROS_IMAGE_TOPIC", DEFAULT_ROS_IMAGE_TOPIC),
        ros2_camera_input_topic=_get_str_env(
            "ROS2_CAMERA_INPUT_TOPIC",
            DEFAULT_ROS2_CAMERA_INPUT_TOPIC,
        ),
        ros2_image_topic=_get_str_env("ROS2_IMAGE_TOPIC", DEFAULT_ROS2_IMAGE_TOPIC),
        ros2_image_type=_get_str_env("ROS2_IMAGE_TYPE", DEFAULT_ROS2_IMAGE_TYPE),
        ros2_trajectory_topic=_get_str_env(
            "ROS2_TRAJECTORY_TOPIC",
            DEFAULT_ROS2_TRAJECTORY_TOPIC,
        ),
        ros2_robot_command_topic=_get_str_env(
            "ROS2_ROBOT_COMMAND_TOPIC",
            DEFAULT_ROS2_ROBOT_COMMAND_TOPIC,
        ),
        max_image_age_seconds=_get_float_env(
            "MAX_IMAGE_AGE_SECONDS",
            DEFAULT_MAX_IMAGE_AGE_SECONDS,
        ),
    )


def _get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(
            f"{name} is required. Copy .env.example to .env and set the real Kachaka host."
        )
    return value


def _get_str_env(name: str, default: str) -> str:
    value = os.getenv(name, "").strip()
    return value or default


def _get_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default

    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer. Current value: {raw_value!r}") from exc


def _get_float_env(name: str, default: float) -> float:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default

    try:
        return float(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a float. Current value: {raw_value!r}") from exc


def _get_bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name, "").strip().lower()
    if not raw_value:
        return default

    if raw_value in {"1", "true", "yes", "y", "on"}:
        return True
    if raw_value in {"0", "false", "no", "n", "off"}:
        return False

    raise ValueError(
        f"{name} must be a boolean value such as true/false, yes/no, or 1/0. "
        f"Current value: {raw_value!r}"
    )
