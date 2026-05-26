from kachaka_navigation.core.messages import (
    CommandKind,
    ImageFrame,
    NavigationCommand,
    RobotState,
)
from kachaka_navigation.core.serialization import (
    request_from_json,
    request_to_json,
    response_from_json,
    response_to_json,
)


def test_request_round_trip_keeps_frame_and_state() -> None:
    frame = ImageFrame(
        data=b"jpeg-bytes",
        encoding="jpeg",
        width=640,
        height=480,
        frame_id="camera",
    )
    state = RobotState(x=1.0, y=2.0, theta=0.5)

    decoded_frame, decoded_state = request_from_json(request_to_json(frame, state))

    assert decoded_frame == frame
    assert decoded_state == state


def test_response_round_trip_keeps_command() -> None:
    command = NavigationCommand.from_velocity(linear_x=0.1, angular_z=0.2)

    decoded = response_from_json(response_to_json(command))

    assert decoded.kind == CommandKind.VELOCITY
    assert decoded.velocity == command.velocity
