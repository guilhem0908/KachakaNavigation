from kachaka_navigation.core.messages import VelocityCommand
from kachaka_navigation.core.velocity_safety import VelocitySafetyLimits


def test_velocity_limits_clamp_linear_and_angular_values() -> None:
    limits = VelocitySafetyLimits(max_linear_x=0.2, max_angular_z=0.5)

    safe_velocity = limits.clamp(
        VelocityCommand(
            linear_x=1.0,
            angular_z=-2.0,
            duration_seconds=0.1,
        )
    )

    assert safe_velocity.linear_x == 0.2
    assert safe_velocity.angular_z == -0.5
    assert safe_velocity.duration_seconds == 0.1


def test_velocity_limits_apply_default_and_max_duration() -> None:
    limits = VelocitySafetyLimits(
        default_duration_seconds=0.25,
        max_duration_seconds=1.0,
    )

    default_duration = limits.resolve_duration_seconds(VelocityCommand())
    max_duration = limits.resolve_duration_seconds(
        VelocityCommand(duration_seconds=10.0)
    )

    assert default_duration == 0.25
    assert max_duration == 1.0
