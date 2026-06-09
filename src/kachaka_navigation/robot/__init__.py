from kachaka_navigation.robot.logging_command_executor import LoggingCommandExecutor
from kachaka_navigation.robot.navigation_client import RobotNavigationClient
from kachaka_navigation.robot.nomad_controller import (
    NomadKachakaController,
    VelocityLimits,
    command_to_velocity,
)

__all__ = [
    "KachakaCommandExecutor",
    "LoggingCommandExecutor",
    "NomadKachakaController",
    "RobotNavigationClient",
    "UnsupportedRobotCommandError",
    "VelocityLimits",
    "command_to_velocity",
]


def __getattr__(name: str) -> object:
    if name in {"KachakaCommandExecutor", "UnsupportedRobotCommandError"}:
        from kachaka_navigation.robot.kachaka_command_executor import (
            KachakaCommandExecutor,
            UnsupportedRobotCommandError,
        )

        values = {
            "KachakaCommandExecutor": KachakaCommandExecutor,
            "UnsupportedRobotCommandError": UnsupportedRobotCommandError,
        }
        return values[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
