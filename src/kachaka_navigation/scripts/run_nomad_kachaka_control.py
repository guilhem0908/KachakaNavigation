"""Drive a Kachaka directly from this machine with the NoMaD policy.

Pulls the Kachaka front camera over kachaka-api (gRPC), runs NoMaD locally, and
streams base velocities back to the robot. No ROS required.

Examples
--------
Dry-run (connects + perceives, but never moves the robot)::

    python -m kachaka_navigation.scripts.run_nomad_kachaka_control --dry-run --max-iterations 20

Live driving (robot WILL move; keep the area clear and a hand on the e-stop)::

    python -m kachaka_navigation.scripts.run_nomad_kachaka_control \
        --max-linear-speed 0.1 --max-angular-speed 0.3
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from kachaka_navigation.config import PROJECT_ROOT, get_kachaka_settings
from kachaka_navigation.logging_config import configure_logging
from kachaka_navigation.models.nomad_original import (
    NomadOriginalConfig,
    NomadOriginalModel,
)
from kachaka_navigation.robot import (
    NomadKachakaController,
    ReleasableVelocitySink,
    VelocityLimits,
)

logger = logging.getLogger(__name__)

DEFAULT_CHECKPOINT = PROJECT_ROOT / "models" / "nomad_original" / "checkpoints" / "nomad.pth"
DEFAULT_CONFIG = PROJECT_ROOT / "models" / "nomad_original" / "configs" / "nomad.yaml"


def main() -> int:
    configure_logging()
    args = _parse_args()

    model = _build_model(args)
    logger.info("Loading NoMaD model (device=%s)...", args.device)
    model.load()

    if args.self_test:
        return _run_self_test(model, args)

    try:
        from kachaka_navigation.clients.kachaka_robot_client import KachakaRobotClient
    except ImportError as error:  # pragma: no cover - env dependent
        print(f"ERROR: kachaka-api is required: {error}", file=sys.stderr)
        return 1

    target = args.target or get_kachaka_settings().target
    logger.info("Connecting to Kachaka at %s", target)
    robot = KachakaRobotClient(target=target)

    limits = VelocityLimits(
        max_linear_speed=args.max_linear_speed,
        max_angular_speed=args.max_angular_speed,
    )

    live_sink: ReleasableVelocitySink | None = None
    if args.dry_run:
        logger.warning("DRY-RUN: perceiving only, robot will NOT move.")

        def velocity_sink(linear: float, angular: float) -> None:
            logger.info("[dry-run] would set velocity linear=%.3f angular=%.3f", linear, angular)
    else:
        logger.warning(
            "LIVE control: enabling manual control. The robot WILL move. "
            "Keep the area clear; press Ctrl-C to stop."
        )
        robot.set_manual_control_enabled(True)
        live_sink = ReleasableVelocitySink(robot.set_velocity)
        velocity_sink = live_sink

    controller = NomadKachakaController(
        model=model,
        camera=robot.get_front_camera_frame,
        velocity_sink=velocity_sink,
        limits=limits,
        frame_rate=args.frame_rate,
        on_goal_reached=_build_goal_reached_action(robot, args, live_sink),
    )

    max_iterations = args.max_iterations if args.max_iterations > 0 else None
    try:
        iterations = controller.run(max_iterations=max_iterations)
        logger.info("NoMaD control finished after %d iterations", iterations)
        return 0
    except KeyboardInterrupt:
        print()
        logger.info("NoMaD control interrupted by user")
        return 130
    except Exception as error:
        logger.exception("NoMaD control failed")
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    finally:
        if not args.dry_run:
            if live_sink is not None and live_sink.released:
                # return_home already stopped the robot and handed control
                # back; pushing another velocity would silently re-enable
                # manual control (kachaka-api retry) and cancel/undock it.
                logger.info(
                    "Control handed back to the robot; skipping velocity cleanup."
                )
            else:
                try:
                    robot.stop_velocity()
                except Exception:  # pragma: no cover - best-effort cleanup
                    logger.exception("Failed to send final zero velocity.")
                try:
                    robot.set_manual_control_enabled(False)
                    logger.info("Stopped robot and disabled manual control.")
                except Exception:  # pragma: no cover - best-effort cleanup
                    logger.exception("Failed to disable manual control.")


def _run_self_test(model: NomadOriginalModel, args: argparse.Namespace) -> int:
    """Run NoMaD on synthetic frames without a robot, to validate this PC."""
    import io

    import numpy as np
    from PIL import Image

    from kachaka_navigation.core.messages import CommandKind, ImageFrame

    logger.info("SELF-TEST: running NoMaD on synthetic frames (no robot).")
    limits = VelocityLimits(args.max_linear_speed, args.max_angular_speed)
    drove = False
    for i in range(8):
        shift = (i * 12) % 160
        base = np.roll(np.tile(np.linspace(0, 255, 160, dtype=np.uint8), (120, 1)), shift, axis=1)
        rgb = np.stack([base, np.roll(base, 30, 1), np.roll(base, 60, 1)], axis=-1)
        buf = io.BytesIO()
        Image.fromarray(rgb).save(buf, format="JPEG", quality=85)
        frame = ImageFrame(data=buf.getvalue(), encoding="jpeg", width=160, height=120)
        command = model.predict(frame)
        if command.kind == CommandKind.VELOCITY:
            v, w = limits.clamp(command.velocity.linear_x, command.velocity.angular_z)
            drove = True
            logger.info("  frame %2d -> linear=%+.3f m/s  angular=%+.3f rad/s", i, v, w)
        else:
            reason = command.metadata.get("reason", "")
            logger.info("  frame %2d -> %s (%s)", i, command.kind.value, reason)
    if drove:
        logger.info("SELF-TEST OK: NoMaD produced velocity commands on this machine.")
        return 0
    logger.error("SELF-TEST FAILED: no velocity command produced.")
    return 1


def _build_model(args: argparse.Namespace) -> NomadOriginalModel:
    config = NomadOriginalConfig(
        checkpoint_path=args.checkpoint,
        model_config_path=args.config if args.config.exists() else None,
        goal_image_path=args.goal_image,
        device=args.device,
        num_samples=args.num_samples,
        num_diffusion_iters=args.num_diffusion_iters,
        waypoint_index=args.waypoint_index,
        max_linear_speed=args.max_linear_speed,
        max_angular_speed=args.max_angular_speed,
        frame_rate=args.frame_rate,
        arrival_detector=args.arrival_detector,
        goal_reached_distance=args.goal_reached_distance,
        goal_similarity_threshold=args.goal_similarity_threshold,
        goal_reached_patience=args.goal_reached_patience,
        center_crop=not args.no_center_crop,
        waypoint_aggregation=args.waypoint_aggregation,
    )
    return NomadOriginalModel(config)


def _build_goal_reached_action(
    robot,
    args: argparse.Namespace,
    live_sink: ReleasableVelocitySink | None,
):
    """What to do when the model reports the goal image is reached."""
    if args.goal_image is None:
        return None
    action = args.on_goal_reached

    if args.dry_run:
        def dry_run_action() -> None:
            logger.info("[dry-run] goal reached — would run %r action.", action)

        return dry_run_action

    if action == "speak":
        def speak_action() -> None:
            logger.info("Goal reached — speaking.")
            robot.speak(args.goal_reached_text)

        return speak_action

    if action == "return_home":
        def return_home_action() -> None:
            logger.info("Goal reached — returning home.")
            robot.stop_velocity()
            if live_sink is not None:
                live_sink.release()  # no more velocities once control is handed back
            robot.set_manual_control_enabled(False)
            robot.return_home()

        return return_home_action

    def stop_action() -> None:
        logger.info("Goal reached — stopped.")

    return stop_action


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Drive a Kachaka with the NoMaD policy (camera -> NoMaD -> velocity)."
    )
    parser.add_argument("--target", default=None, help="Kachaka host:port (default: from .env).")
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--goal-image",
        type=Path,
        default=None,
        help="Optional goal image for goal-conditioned navigation (default: exploration).",
    )
    parser.add_argument(
        "--arrival-detector",
        choices=["distance", "similarity", "any"],
        default="distance",
        help="Signal used to detect arrival at the goal image: distance = the "
        "model's distance head (can be unusable on out-of-domain cameras); "
        "similarity = direct image similarity with the goal photo (robust); "
        "any = whichever fires first.",
    )
    parser.add_argument(
        "--goal-reached-distance",
        type=float,
        default=3.0,
        help="Predicted temporal distance below which the goal counts as reached "
        "(upstream default 3; raise to 4-6 if the robot stops too late or never).",
    )
    parser.add_argument(
        "--goal-similarity-threshold",
        type=float,
        default=0.8,
        help="Cosine similarity (0-1) with the goal photo above which the goal "
        "counts as reached, for --arrival-detector similarity/any. Calibrate "
        "with the goal_similarity= values in the logs.",
    )
    parser.add_argument(
        "--goal-reached-patience",
        type=int,
        default=2,
        help="Consecutive below-threshold readings required before stopping.",
    )
    parser.add_argument(
        "--on-goal-reached",
        choices=["stop", "speak", "return_home"],
        default="stop",
        help="Action when the goal image is reached: stop (default), speak, or return_home.",
    )
    parser.add_argument(
        "--goal-reached-text",
        default="Objectif atteint",
        help="Text spoken when --on-goal-reached=speak.",
    )
    parser.add_argument(
        "--device",
        default="auto",
        help="auto | cpu | cuda | mps (auto picks CUDA/MPS GPU if available, else CPU)",
    )
    parser.add_argument("--num-samples", type=int, default=8)
    parser.add_argument("--num-diffusion-iters", type=int, default=10)
    parser.add_argument("--waypoint-index", type=int, default=2)
    parser.add_argument(
        "--waypoint-aggregation",
        choices=["mean", "first"],
        default="mean",
        help="mean = average the sampled trajectories (stabler heading); "
        "first = upstream behaviour (sample 0).",
    )
    parser.add_argument(
        "--no-center-crop",
        action="store_true",
        help="Disable the 4:3 center-crop applied before the model resize.",
    )
    parser.add_argument("--max-linear-speed", type=float, default=0.15, help="m/s")
    parser.add_argument("--max-angular-speed", type=float, default=0.3, help="rad/s")
    parser.add_argument("--frame-rate", type=float, default=3.0, help="control loop rate (Hz)")
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=0,
        help="Stop after N iterations (0 = run until Ctrl-C).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perceive and log velocities but never move the robot.",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run NoMaD on synthetic frames without connecting to a robot.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(main())
