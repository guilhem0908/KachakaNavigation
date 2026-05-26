from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TypeAlias


JsonScalar: TypeAlias = str | int | float | bool | None
Metadata: TypeAlias = dict[str, JsonScalar]


class CommandKind(str, Enum):
    """Commands exchanged between the model server and the robot client."""

    NOOP = "noop"
    STOP = "stop"
    VELOCITY = "velocity"
    WAYPOINT = "waypoint"
    MOVE_TO_LOCATION = "move_to_location"
    RETURN_HOME = "return_home"
    DOCK_SHELF = "dock_shelf"
    UNDOCK_SHELF = "undock_shelf"
    CANCEL = "cancel"
    SPEAK = "speak"


@dataclass(frozen=True, slots=True)
class ImageFrame:
    """Camera frame sent from the robot side to the navigation server."""

    data: bytes
    encoding: str
    width: int | None = None
    height: int | None = None
    frame_id: str = ""
    timestamp: float | None = None
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.data:
            raise ValueError("ImageFrame.data must not be empty.")
        if not self.encoding:
            raise ValueError("ImageFrame.encoding must not be empty.")
        if self.width is not None and self.width <= 0:
            raise ValueError("ImageFrame.width must be positive when provided.")
        if self.height is not None and self.height <= 0:
            raise ValueError("ImageFrame.height must be positive when provided.")
        object.__setattr__(self, "metadata", dict(self.metadata))


@dataclass(frozen=True, slots=True)
class RobotState:
    """Optional robot state that can be attached to a frame request."""

    x: float | None = None
    y: float | None = None
    theta: float | None = None
    battery_percent: float | None = None
    carrying_shelf: bool | None = None
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", dict(self.metadata))


@dataclass(frozen=True, slots=True)
class VelocityCommand:
    """Differential-drive velocity command."""

    linear_x: float = 0.0
    angular_z: float = 0.0
    duration_seconds: float | None = None

    def __post_init__(self) -> None:
        if self.duration_seconds is not None and self.duration_seconds < 0:
            raise ValueError("VelocityCommand.duration_seconds must not be negative.")


@dataclass(frozen=True, slots=True)
class WaypointCommand:
    """Local waypoint command expressed in a ROS-style frame."""

    x: float
    y: float
    heading: float | None = None
    frame_id: str = "base_link"
    tolerance_meters: float | None = None

    def __post_init__(self) -> None:
        if self.tolerance_meters is not None and self.tolerance_meters < 0:
            raise ValueError("WaypointCommand.tolerance_meters must not be negative.")


@dataclass(frozen=True, slots=True)
class NavigationCommand:
    """Server response consumed by a robot-side command executor."""

    kind: CommandKind
    velocity: VelocityCommand | None = None
    waypoint: WaypointCommand | None = None
    target: str = ""
    text: str = ""
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", dict(self.metadata))
        if self.kind == CommandKind.VELOCITY and self.velocity is None:
            raise ValueError("A velocity command requires a VelocityCommand payload.")
        if self.kind == CommandKind.WAYPOINT and self.waypoint is None:
            raise ValueError("A waypoint command requires a WaypointCommand payload.")
        if self.kind == CommandKind.MOVE_TO_LOCATION and not self.target:
            raise ValueError("A move_to_location command requires a target.")
        if self.kind == CommandKind.SPEAK and not self.text:
            raise ValueError("A speak command requires text.")

    @classmethod
    def noop(cls, reason: str = "") -> NavigationCommand:
        metadata: Metadata = {"reason": reason} if reason else {}
        return cls(kind=CommandKind.NOOP, metadata=metadata)

    @classmethod
    def stop(cls, reason: str = "") -> NavigationCommand:
        metadata: Metadata = {"reason": reason} if reason else {}
        return cls(kind=CommandKind.STOP, metadata=metadata)

    @classmethod
    def from_velocity(
        cls,
        linear_x: float,
        angular_z: float,
        duration_seconds: float | None = None,
    ) -> NavigationCommand:
        return cls(
            kind=CommandKind.VELOCITY,
            velocity=VelocityCommand(
                linear_x=linear_x,
                angular_z=angular_z,
                duration_seconds=duration_seconds,
            ),
        )

    @classmethod
    def from_waypoint(
        cls,
        x: float,
        y: float,
        heading: float | None = None,
        frame_id: str = "base_link",
    ) -> NavigationCommand:
        return cls(
            kind=CommandKind.WAYPOINT,
            waypoint=WaypointCommand(
                x=x,
                y=y,
                heading=heading,
                frame_id=frame_id,
            ),
        )
