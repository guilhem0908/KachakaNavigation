from __future__ import annotations

import base64
import json
from typing import Any

from kachaka_navigation.core.messages import (
    CommandKind,
    ImageFrame,
    NavigationCommand,
    RobotState,
    VelocityCommand,
    WaypointCommand,
)


def image_frame_to_dict(frame: ImageFrame) -> dict[str, Any]:
    return {
        "data_b64": base64.b64encode(frame.data).decode("ascii"),
        "encoding": frame.encoding,
        "width": frame.width,
        "height": frame.height,
        "frame_id": frame.frame_id,
        "timestamp": frame.timestamp,
        "metadata": dict(frame.metadata),
    }


def image_frame_from_dict(payload: dict[str, Any]) -> ImageFrame:
    return ImageFrame(
        data=base64.b64decode(payload["data_b64"]),
        encoding=str(payload["encoding"]),
        width=payload.get("width"),
        height=payload.get("height"),
        frame_id=str(payload.get("frame_id", "")),
        timestamp=payload.get("timestamp"),
        metadata=dict(payload.get("metadata", {})),
    )


def robot_state_to_dict(state: RobotState) -> dict[str, Any]:
    return {
        "x": state.x,
        "y": state.y,
        "theta": state.theta,
        "battery_percent": state.battery_percent,
        "carrying_shelf": state.carrying_shelf,
        "metadata": dict(state.metadata),
    }


def robot_state_from_dict(payload: dict[str, Any] | None) -> RobotState | None:
    if payload is None:
        return None

    return RobotState(
        x=payload.get("x"),
        y=payload.get("y"),
        theta=payload.get("theta"),
        battery_percent=payload.get("battery_percent"),
        carrying_shelf=payload.get("carrying_shelf"),
        metadata=dict(payload.get("metadata", {})),
    )


def command_to_dict(command: NavigationCommand) -> dict[str, Any]:
    return {
        "kind": command.kind.value,
        "velocity": _velocity_to_dict(command.velocity),
        "waypoint": _waypoint_to_dict(command.waypoint),
        "target": command.target,
        "text": command.text,
        "metadata": dict(command.metadata),
    }


def command_from_dict(payload: dict[str, Any]) -> NavigationCommand:
    return NavigationCommand(
        kind=CommandKind(payload["kind"]),
        velocity=_velocity_from_dict(payload.get("velocity")),
        waypoint=_waypoint_from_dict(payload.get("waypoint")),
        target=str(payload.get("target", "")),
        text=str(payload.get("text", "")),
        metadata=dict(payload.get("metadata", {})),
    )


def request_to_json(frame: ImageFrame, state: RobotState | None = None) -> str:
    payload = {
        "type": "frame",
        "frame": image_frame_to_dict(frame),
        "state": robot_state_to_dict(state) if state is not None else None,
    }
    return json.dumps(payload, separators=(",", ":"))


def request_from_json(raw_request: str) -> tuple[ImageFrame, RobotState | None]:
    payload = json.loads(raw_request)
    if payload.get("type") != "frame":
        raise ValueError(f"Unsupported request type: {payload.get('type')!r}")

    return (
        image_frame_from_dict(payload["frame"]),
        robot_state_from_dict(payload.get("state")),
    )


def response_to_json(command: NavigationCommand) -> str:
    payload = {
        "type": "command",
        "command": command_to_dict(command),
    }
    return json.dumps(payload, separators=(",", ":"))


def response_from_json(raw_response: str) -> NavigationCommand:
    payload = json.loads(raw_response)
    response_type = payload.get("type")
    if response_type == "error":
        raise RuntimeError(str(payload.get("error", "Unknown navigation server error.")))
    if response_type != "command":
        raise ValueError(f"Unsupported response type: {response_type!r}")

    return command_from_dict(payload["command"])


def error_response_to_json(error: Exception) -> str:
    payload = {
        "type": "error",
        "error": str(error),
    }
    return json.dumps(payload, separators=(",", ":"))


def _velocity_to_dict(velocity: VelocityCommand | None) -> dict[str, Any] | None:
    if velocity is None:
        return None

    return {
        "linear_x": velocity.linear_x,
        "angular_z": velocity.angular_z,
        "duration_seconds": velocity.duration_seconds,
    }


def _velocity_from_dict(payload: dict[str, Any] | None) -> VelocityCommand | None:
    if payload is None:
        return None

    return VelocityCommand(
        linear_x=float(payload.get("linear_x", 0.0)),
        angular_z=float(payload.get("angular_z", 0.0)),
        duration_seconds=payload.get("duration_seconds"),
    )


def _waypoint_to_dict(waypoint: WaypointCommand | None) -> dict[str, Any] | None:
    if waypoint is None:
        return None

    return {
        "x": waypoint.x,
        "y": waypoint.y,
        "heading": waypoint.heading,
        "frame_id": waypoint.frame_id,
        "tolerance_meters": waypoint.tolerance_meters,
    }


def _waypoint_from_dict(payload: dict[str, Any] | None) -> WaypointCommand | None:
    if payload is None:
        return None

    return WaypointCommand(
        x=float(payload["x"]),
        y=float(payload["y"]),
        heading=payload.get("heading"),
        frame_id=str(payload.get("frame_id", "base_link")),
        tolerance_meters=payload.get("tolerance_meters"),
    )
