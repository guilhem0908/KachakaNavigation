"""Capture a still image from a Kachaka camera and save it to disk.

Examples
--------
    python -m kachaka_navigation.scripts.capture_camera_image -o photo.jpg
    python -m kachaka_navigation.scripts.capture_camera_image -c back -o back.jpg

Use it to grab a goal image for goal-conditioned NoMaD navigation:
    python -m kachaka_navigation.scripts.capture_camera_image \
        -o models/nomad_original/goals/goal.jpg
    python -m kachaka_navigation.scripts.run_nomad_kachaka_control \
        --goal-image models/nomad_original/goals/goal.jpg
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from kachaka_navigation.config import get_kachaka_settings
from kachaka_navigation.logging_config import configure_logging

logger = logging.getLogger(__name__)


def main() -> int:
    configure_logging()
    args = _parse_args()

    try:
        from kachaka_navigation.clients.kachaka_robot_client import KachakaRobotClient
    except ImportError as error:  # pragma: no cover - env dependent
        print(f"ERROR: kachaka-api is required: {error}", file=sys.stderr)
        return 1

    target = args.target or get_kachaka_settings().target
    logger.info("Connecting to Kachaka at %s", target)

    try:
        robot = KachakaRobotClient(target=target)
        frame = robot.get_camera_frame(args.camera)
    except Exception as error:
        logger.exception("Failed to capture camera image")
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    output = Path(args.output)
    if output.parent != Path(""):
        output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(frame.data)
    print(
        f"Saved {args.camera} camera image: {len(frame.data)} bytes "
        f"({frame.encoding}) -> {output}"
    )
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture a still image from a Kachaka camera and save it."
    )
    parser.add_argument(
        "--output",
        "-o",
        default="kachaka_photo.jpg",
        help="Output file path (default: kachaka_photo.jpg).",
    )
    parser.add_argument(
        "--camera",
        "-c",
        default="front",
        choices=["front", "back", "tof"],
        help="Which camera to use (default: front).",
    )
    parser.add_argument(
        "--target",
        default=None,
        help="Kachaka host:port (default: from .env).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(main())
