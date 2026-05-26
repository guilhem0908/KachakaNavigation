from __future__ import annotations

import logging
from typing import Any

from kachaka_navigation.core.interfaces import CommandExecutor
from kachaka_navigation.core.messages import (
    CommandKind,
    NavigationCommand,
    VelocityCommand,
)
from kachaka_navigation.core.velocity_safety import VelocitySafetyLimits
from kachaka_navigation.robot import LoggingCommandExecutor
from kachaka_navigation.ros2.availability import (
    import_ros2_core,
    import_ros2_node_base,
    import_twist_message,
)
from kachaka_navigation.ros2.json_messages import command_from_ros_json


logger = logging.getLogger(__name__)
RosNodeBase = import_ros2_node_base()


class Ros2KachakaCommandExecutorNode(RosNodeBase):
    """Kachaka-side node: robot command topic -> Kachaka executors."""

    def __init__(
        self,
        *,
        robot_command_topic: str,
        dry_run: bool = False,
        enable_api_commands: bool = True,
        enable_velocity_control: bool = False,
        cmd_vel_topic: str = "/kachaka/manual_control/cmd_vel",
        cmd_vel_publish_rate_hz: float = 20.0,
        velocity_limits: VelocitySafetyLimits | None = None,
        node_name: str = "kachaka_command_executor",
    ) -> None:
        _, _, _, _, _, string_type = import_ros2_core()
        super().__init__(node_name)

        self._executor = _build_executor(
            dry_run=dry_run,
            enable_api_commands=enable_api_commands,
        )
        self._dry_run = dry_run
        self._enable_velocity_control = enable_velocity_control
        self._velocity_limits = velocity_limits or VelocitySafetyLimits()
        self._active_velocity: VelocityCommand | None = None
        self._active_velocity_until_seconds = 0.0
        self._cmd_vel_publisher: Any | None = None
        self._twist_type: type[Any] | None = None

        if enable_velocity_control and not dry_run:
            if cmd_vel_publish_rate_hz <= 0:
                raise ValueError("cmd_vel_publish_rate_hz must be positive.")
            self._twist_type = import_twist_message()
            self._cmd_vel_publisher = self.create_publisher(
                self._twist_type,
                cmd_vel_topic,
                1,
            )
            self.create_timer(
                1.0 / cmd_vel_publish_rate_hz,
                self._publish_active_velocity,
            )
            self.get_logger().warning(
                f"low-level velocity control enabled on {cmd_vel_topic}"
            )
        elif enable_velocity_control and dry_run:
            self.get_logger().info("velocity control requested but dry-run is active")

        self._subscription = self.create_subscription(
            string_type,
            robot_command_topic,
            self._on_command,
            1,
        )
        self.get_logger().info(f"command_executor subscribed to {robot_command_topic}")

    def _on_command(self, message: object) -> None:
        try:
            command, _ = command_from_ros_json(str(getattr(message, "data")))
            if self._handle_velocity_command(command):
                return
            if command.kind in {CommandKind.STOP, CommandKind.CANCEL}:
                self._stop_velocity()
            self._executor.execute(command)
        except Exception as error:
            logger.exception("Could not execute Kachaka command")
            self.get_logger().error(f"Could not execute Kachaka command: {error}")

    def _handle_velocity_command(self, command: NavigationCommand) -> bool:
        if command.kind != CommandKind.VELOCITY:
            return False

        if command.velocity is None:
            raise ValueError("Velocity command is missing its payload.")
        if self._dry_run:
            self.get_logger().info(f"dry-run velocity command: {command.velocity}")
            return True
        if not self._enable_velocity_control:
            self.get_logger().error(
                "velocity command ignored because velocity control is disabled"
            )
            return True

        safe_velocity = self._velocity_limits.clamp(command.velocity)
        duration_seconds = self._velocity_limits.resolve_duration_seconds(safe_velocity)
        self._active_velocity = safe_velocity
        self._active_velocity_until_seconds = self._now_seconds() + duration_seconds
        self._publish_velocity(safe_velocity)
        return True

    def _publish_active_velocity(self) -> None:
        if self._active_velocity is None:
            return

        if self._now_seconds() > self._active_velocity_until_seconds:
            self._stop_velocity()
            return

        self._publish_velocity(self._active_velocity)

    def _stop_velocity(self) -> None:
        self._active_velocity = None
        if self._cmd_vel_publisher is not None:
            self._publish_velocity(VelocityCommand())

    def _publish_velocity(self, velocity: VelocityCommand) -> None:
        if self._cmd_vel_publisher is None or self._twist_type is None:
            return

        message = self._twist_type()
        message.linear.x = float(velocity.linear_x)
        message.angular.z = float(velocity.angular_z)
        self._cmd_vel_publisher.publish(message)

    def _now_seconds(self) -> float:
        return self.get_clock().now().nanoseconds / 1_000_000_000.0


def _build_executor(
    dry_run: bool,
    enable_api_commands: bool,
) -> CommandExecutor:
    if dry_run or not enable_api_commands:
        return LoggingCommandExecutor()

    from kachaka_navigation.robot import KachakaCommandExecutor

    return KachakaCommandExecutor.from_settings()
