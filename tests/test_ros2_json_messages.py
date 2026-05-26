from kachaka_navigation.core.messages import CommandKind, NavigationCommand
from kachaka_navigation.ros2.json_messages import (
    command_from_ros_json,
    command_to_ros_json,
)


def test_ros2_command_json_round_trip() -> None:
    command = NavigationCommand.stop("test")

    decoded_command, generated_at = command_from_ros_json(
        command_to_ros_json(command, generated_at=12.0)
    )

    assert decoded_command.kind == CommandKind.STOP
    assert decoded_command.metadata == {"reason": "test"}
    assert generated_at == 12.0
