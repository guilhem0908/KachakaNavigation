from __future__ import annotations

import argparse
from pathlib import Path

from kachaka_navigation.models import (
    NomadOriginalConfig,
    NomadOriginalModel,
    build_default_registry,
)
from kachaka_navigation.server import NavigationService


def add_navigation_model_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--model", default="noop")
    parser.add_argument(
        "--nomad-checkpoint",
        type=Path,
        help="Path to the original NoMaD checkpoint.",
    )
    parser.add_argument(
        "--nomad-config",
        type=Path,
        help="Path to the original NoMaD model config.",
    )
    parser.add_argument(
        "--nomad-goal-image",
        type=Path,
        help="Goal image used by the NoMaD adapter.",
    )
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--context-size", type=int, default=5)


def build_navigation_service_from_args(args: argparse.Namespace) -> NavigationService:
    registry = build_default_registry(_nomad_config_from_args(args))
    return NavigationService(model=registry.create(args.model))


def _nomad_config_from_args(args: argparse.Namespace) -> NomadOriginalConfig | None:
    if args.model != NomadOriginalModel.name:
        return None
    if args.nomad_checkpoint is None:
        raise ValueError("--nomad-checkpoint is required for nomad_original.")

    return NomadOriginalConfig(
        checkpoint_path=args.nomad_checkpoint,
        model_config_path=args.nomad_config,
        goal_image_path=args.nomad_goal_image,
        device=args.device,
        context_size=args.context_size,
    )
