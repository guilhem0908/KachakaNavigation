from __future__ import annotations

import json

from kachaka_navigation.core.messages import NavigationCommand
from kachaka_navigation.core.serialization import command_from_dict, command_to_dict


def command_to_ros_json(command: NavigationCommand, generated_at: float) -> str:
    payload = {
        "type": "navigation_command",
        "generated_at": generated_at,
        "command": command_to_dict(command),
    }
    return json.dumps(payload, separators=(",", ":"))


def command_from_ros_json(raw_payload: str) -> tuple[NavigationCommand, float | None]:
    payload = json.loads(raw_payload)
    if payload.get("type") != "navigation_command":
        raise ValueError(f"Unsupported ROS command type: {payload.get('type')!r}")

    generated_at = payload.get("generated_at")
    return command_from_dict(payload["command"]), generated_at
