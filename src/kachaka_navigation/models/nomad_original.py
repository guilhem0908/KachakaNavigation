"""Adapter for the original NoMaD policy (robodhruv/visualnav-transformer).

This wires the published NoMaD checkpoint into the project's
``ImageFrame -> NavigationCommand`` contract so a Kachaka can be driven directly
on this machine (no ROS required).

Pipeline (mirrors ``deployment/src/explore.py`` from the upstream repo):

    image bytes -> PIL -> context queue -> transform_images
        -> NoMaD vision encoder -> diffusion sampling (DDPMScheduler)
        -> get_action (unnormalize + cumsum) -> chosen waypoint
        -> PD controller -> NavigationCommand.from_velocity(linear_x, angular_z)

The heavy ML dependencies (torch, diffusers, efficientnet, the upstream model
code and the vendored diffusion_policy package) are imported lazily on first use
so that importing this module stays cheap for code paths that do not run NoMaD.
"""
from __future__ import annotations

import io
import logging
import math
import sys
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kachaka_navigation.core.messages import (
    CommandKind,
    ImageFrame,
    NavigationCommand,
    RobotState,
    VelocityCommand,
)

logger = logging.getLogger(__name__)

# Repo root: src/kachaka_navigation/models/nomad_original.py -> parents[3]
_REPO_ROOT = Path(__file__).resolve().parents[3]

# ImageNet normalization used by the upstream transform_images().
_IMAGENET_MEAN = (0.485, 0.456, 0.406)
_IMAGENET_STD = (0.229, 0.224, 0.225)

# Normalized action statistics from the upstream data_config.yaml (action_stats).
_ACTION_MIN = (-2.5, -4.0)
_ACTION_MAX = (5.0, 4.0)

_EPS = 1e-8


class NomadOriginalUnavailableError(RuntimeError):
    """Raised when NoMaD is selected but its code/weights are not available."""


@dataclass(frozen=True, slots=True)
class NomadOriginalConfig:
    """Configuration for the original NoMaD VisualNav adapter.

    Only ``checkpoint_path`` is required. Hyper-parameters default to the values
    used to train the published checkpoint; when ``model_config_path`` points at
    the upstream ``nomad.yaml`` they are read from it so the architecture always
    matches the weights.
    """

    checkpoint_path: Path
    model_config_path: Path | None = None
    goal_image_path: Path | None = None
    device: str = "cpu"  # "cpu" | "mps" | "cuda" | "auto"
    context_size: int = 3

    # Diffusion / sampling.
    num_diffusion_iters: int = 10
    num_samples: int = 8
    waypoint_index: int = 2

    # Velocity conversion (PD controller). Defaults match the project's safety
    # envelope and the upstream LoCoBot deployment.
    max_linear_speed: float = 0.2  # m/s
    max_angular_speed: float = 0.4  # rad/s
    frame_rate: float = 4.0  # Hz, used to scale waypoints -> velocity
    velocity_duration_seconds: float = 0.5

    # Goal-arrival detection (active only when goal_image_path is set).
    # Two signals are computed every step and logged in the command metadata:
    #   goal_distance   - the model's distance head (temporal distance, ~steps;
    #                     upstream navigate.py treats < 3 as "close"). Can be
    #                     heavily biased on cameras unlike the training data.
    #   goal_similarity - direct cosine similarity between the current frame
    #                     and the goal image (1.0 = identical view). Robust to
    #                     model bias; fires when the robot sees the goal photo.
    # arrival_detector picks which signal declares arrival:
    #   "distance" | "similarity" | "any" (either one)
    # patience = consecutive positive readings required before stopping.
    #
    # goal_similarity_threshold=None enables AUTO-CALIBRATION: the first
    # goal_similarity_baseline_frames readings (taken at the start position)
    # form a baseline B, and the threshold becomes
    # B + goal_similarity_margin * (1 - B) — so the trigger point adapts to
    # how much the start view already resembles the goal photo.
    arrival_detector: str = "distance"
    goal_reached_distance: float = 3.0
    goal_similarity_threshold: float | None = None
    goal_similarity_margin: float = 0.5
    goal_similarity_baseline_frames: int = 5
    goal_reached_patience: int = 2

    # Visual heading assist (goal mode). On cameras far from the training
    # distribution the model's goal encoder cannot localize the goal in its
    # field of view, so it may drive past a clearly visible goal. The assist
    # scans horizontal windows of the current frame for the best match with
    # the goal photo and, when the match is trustworthy, picks the sampled
    # trajectory whose heading points toward it (NoMaD still generates all
    # candidate motions). The gate is CONTRAST-based (best window must beat
    # the mean of the others by goal_visible_contrast) so it needs no absolute
    # calibration; goal_visible_threshold optionally adds an absolute floor.
    goal_heading_assist: bool = True
    goal_bearing_windows: int = 7
    camera_hfov_deg: float = 90.0
    goal_visible_threshold: float | None = None
    goal_visible_contrast: float = 0.05

    # Steering stability. The raw bearing is quantized (window grid) and noisy
    # (diffusion samples, matching jitter); applying it directly makes the
    # robot zigzag. The applied bearing is therefore (1) confirmed over
    # goal_bearing_patience consecutive trusted frames, (2) smoothed with an
    # EMA (goal_bearing_smoothing = weight of the newest measurement), and
    # (3) zeroed inside a deadband so a roughly centered goal yields a
    # perfectly straight line. Angular command = goal_steering_gain * bearing.
    goal_bearing_patience: int = 2
    goal_bearing_smoothing: float = 0.4
    goal_bearing_deadband_deg: float = 3.0
    goal_steering_gain: float = 1.5

    # Crop frames to the 4:3 training aspect ratio before the 96x96 resize
    # (no-op for 4:3 cameras; avoids distortion on wide Kachaka frames).
    center_crop: bool = True
    # How to pick the trajectory among the diffusion samples: "mean" averages
    # all samples (stabler heading), "first" keeps upstream's sample 0.
    waypoint_aggregation: str = "mean"

    # Locations of the upstream model code (vendored under third_party/ by the
    # setup script). Overridable for non-standard layouts.
    visualnav_train_path: Path = field(
        default_factory=lambda: _REPO_ROOT / "third_party" / "visualnav-transformer" / "train"
    )
    diffusion_policy_path: Path = field(
        default_factory=lambda: _REPO_ROOT / "third_party" / "diffusion_policy"
    )

    def __post_init__(self) -> None:
        if self.context_size <= 0:
            raise ValueError("NomadOriginalConfig.context_size must be positive.")
        if self.num_samples <= 0:
            raise ValueError("NomadOriginalConfig.num_samples must be positive.")
        if self.num_diffusion_iters <= 0:
            raise ValueError("NomadOriginalConfig.num_diffusion_iters must be positive.")
        if self.max_linear_speed < 0 or self.max_angular_speed < 0:
            raise ValueError("Speed limits must not be negative.")
        if self.goal_reached_distance < 0:
            raise ValueError("NomadOriginalConfig.goal_reached_distance must not be negative.")
        if self.goal_reached_patience < 1:
            raise ValueError("NomadOriginalConfig.goal_reached_patience must be >= 1.")
        if self.arrival_detector not in {"distance", "similarity", "any"}:
            raise ValueError(
                "NomadOriginalConfig.arrival_detector must be 'distance', "
                "'similarity', or 'any'."
            )
        if self.goal_similarity_threshold is not None and not (
            0 < self.goal_similarity_threshold <= 1
        ):
            raise ValueError(
                "NomadOriginalConfig.goal_similarity_threshold must be in (0, 1] "
                "or None for auto-calibration."
            )
        if not 0 < self.goal_similarity_margin < 1:
            raise ValueError(
                "NomadOriginalConfig.goal_similarity_margin must be in (0, 1)."
            )
        if self.goal_similarity_baseline_frames < 1:
            raise ValueError(
                "NomadOriginalConfig.goal_similarity_baseline_frames must be >= 1."
            )
        if self.goal_bearing_windows < 1:
            raise ValueError(
                "NomadOriginalConfig.goal_bearing_windows must be >= 1."
            )
        if not 0 < self.camera_hfov_deg <= 360:
            raise ValueError(
                "NomadOriginalConfig.camera_hfov_deg must be in (0, 360]."
            )
        if self.goal_visible_threshold is not None and not (
            0 < self.goal_visible_threshold <= 1
        ):
            raise ValueError(
                "NomadOriginalConfig.goal_visible_threshold must be in (0, 1] "
                "or None for auto-calibration."
            )
        if not 0 < self.goal_visible_contrast < 1:
            raise ValueError(
                "NomadOriginalConfig.goal_visible_contrast must be in (0, 1)."
            )
        if self.goal_bearing_patience < 1:
            raise ValueError(
                "NomadOriginalConfig.goal_bearing_patience must be >= 1."
            )
        if not 0 < self.goal_bearing_smoothing <= 1:
            raise ValueError(
                "NomadOriginalConfig.goal_bearing_smoothing must be in (0, 1]."
            )
        if self.goal_bearing_deadband_deg < 0:
            raise ValueError(
                "NomadOriginalConfig.goal_bearing_deadband_deg must not be negative."
            )
        if self.goal_steering_gain <= 0:
            raise ValueError(
                "NomadOriginalConfig.goal_steering_gain must be positive."
            )
        if self.waypoint_aggregation not in {"first", "mean"}:
            raise ValueError(
                "NomadOriginalConfig.waypoint_aggregation must be 'first' or 'mean'."
            )


class NomadOriginalModel:
    """NoMaD policy adapter: camera frames in, velocity commands out."""

    name = "nomad_original"

    def __init__(self, config: NomadOriginalConfig) -> None:
        self._config = config
        self._context: deque[Any] = deque(maxlen=config.context_size + 1)
        self._goal_below_count = 0
        self._similarity_baseline: list[float] = []
        self._similarity_threshold: float | None = None
        self._bearing_ema: float | None = None
        self._assist_streak = 0

        # Lazily initialized heavy state (populated by _ensure_loaded()).
        self._loaded = False
        self._torch: Any = None
        self._np: Any = None
        self._model: Any = None
        self._scheduler: Any = None
        self._device: Any = None
        self._transform: Any = None
        self._goal_tensor: Any = None  # preprocessed goal image, or None (explore)
        self._params: dict[str, Any] = {}

    # -- public API ---------------------------------------------------------

    def reset(self) -> None:
        self._context.clear()
        self._goal_below_count = 0
        self._similarity_baseline.clear()
        self._similarity_threshold = None
        self._bearing_ema = None
        self._assist_streak = 0

    def load(self) -> None:
        """Eagerly load torch + the NoMaD model. Safe to call repeatedly."""
        self._ensure_loaded()

    def predict(
        self,
        frame: ImageFrame,
        state: RobotState | None = None,
    ) -> NavigationCommand:
        self._ensure_loaded()

        pil = self._frame_to_pil(frame)
        self._context.append(pil)

        needed = self._config.context_size + 1
        if len(self._context) < needed:
            return NavigationCommand.stop(
                f"Waiting for NoMaD image context ({len(self._context)}/{needed})."
            )

        linear_x, angular_z, info = self._infer_velocity()
        goal_distance = info.get("goal_distance")
        goal_similarity = info.get("goal_similarity")

        metadata: dict[str, Any] = {
            key: round(value, 3) for key, value in info.items()
        }

        if metadata:  # goal mode: evaluate arrival
            cfg = self._config
            distance_ok = (
                goal_distance is not None
                and goal_distance < cfg.goal_reached_distance
            )
            similarity_threshold = (
                self._resolve_similarity_threshold(goal_similarity)
                if goal_similarity is not None
                else None
            )
            if similarity_threshold is not None:
                metadata["goal_similarity_threshold"] = round(similarity_threshold, 3)
            similarity_ok = (
                goal_similarity is not None
                and similarity_threshold is not None
                and goal_similarity >= similarity_threshold
            )
            if cfg.arrival_detector == "distance":
                arrived_now = distance_ok
            elif cfg.arrival_detector == "similarity":
                arrived_now = similarity_ok
            else:  # "any"
                arrived_now = distance_ok or similarity_ok

            self._goal_below_count = self._goal_below_count + 1 if arrived_now else 0
            if self._goal_below_count >= cfg.goal_reached_patience:
                return NavigationCommand(
                    kind=CommandKind.STOP,
                    metadata={
                        "reason": "Goal reached",
                        "goal_reached": True,
                        **metadata,
                    },
                )

        return NavigationCommand(
            kind=CommandKind.VELOCITY,
            velocity=VelocityCommand(
                linear_x=linear_x,
                angular_z=angular_z,
                duration_seconds=self._config.velocity_duration_seconds,
            ),
            metadata=metadata,
        )

    def _resolve_similarity_threshold(self, similarity: float) -> float | None:
        """Return the similarity threshold, auto-calibrating if configured.

        With a fixed config threshold, returns it directly. In auto mode, the
        first N readings (start position) build a baseline B and the threshold
        becomes B + margin * (1 - B). Returns None while still calibrating —
        the similarity signal cannot declare arrival during that window.
        """
        cfg = self._config
        if cfg.goal_similarity_threshold is not None:
            return cfg.goal_similarity_threshold
        if self._similarity_threshold is not None:
            return self._similarity_threshold

        self._similarity_baseline.append(similarity)
        if len(self._similarity_baseline) < cfg.goal_similarity_baseline_frames:
            return None
        readings = sorted(self._similarity_baseline)
        baseline = readings[len(readings) // 2]  # median
        self._similarity_threshold = baseline + cfg.goal_similarity_margin * (
            1.0 - baseline
        )
        logger.info(
            "Auto-calibrated goal similarity from start position: "
            "baseline=%.3f -> threshold=%.3f",
            baseline,
            self._similarity_threshold,
        )
        return None  # applies from the next frame on

    def _update_bearing_filter(self, bearing: float, trusted: bool) -> float | None:
        """Stabilize the raw bearing before it may steer the robot.

        Returns the bearing to apply, or None while not engaged. Requires
        goal_bearing_patience consecutive trusted readings, smooths with an
        EMA, and zeroes the result inside the deadband so a roughly centered
        goal drives a straight line instead of zigzagging.
        """
        cfg = self._config
        if not trusted:
            self._assist_streak = 0
            self._bearing_ema = None
            return None

        self._assist_streak += 1
        alpha = cfg.goal_bearing_smoothing
        self._bearing_ema = (
            bearing
            if self._bearing_ema is None
            else alpha * bearing + (1 - alpha) * self._bearing_ema
        )
        if self._assist_streak < cfg.goal_bearing_patience:
            return None
        smoothed = self._bearing_ema
        if abs(smoothed) < math.radians(cfg.goal_bearing_deadband_deg):
            return 0.0
        return smoothed

    def _estimate_goal_bearing(self, pil_img: Any) -> tuple[float, float, float]:
        """Locate the goal photo across horizontal windows of the frame.

        Returns (bearing_radians, visibility, contrast). Positive bearing =
        goal to the LEFT of center (robot-frame yaw convention). Visibility is
        the best window's cosine similarity with the goal image; contrast is
        how much it beats the mean of the other windows (0 when the profile is
        flat, i.e. the goal cannot be localized laterally).
        """
        torch = self._torch
        cfg = self._config
        image_size = self._params["image_size"]
        width, height = pil_img.size
        window_width = min(width, int(round(height * 4.0 / 3.0)))
        max_left = width - window_width
        if max_left <= 0 or cfg.goal_bearing_windows == 1:
            offsets = [max(0, max_left // 2)]
        else:
            count = cfg.goal_bearing_windows
            offsets = [round(i * max_left / (count - 1)) for i in range(count)]

        goal_flat = self._goal_tensor.flatten()
        similarities: list[float] = []
        centers: list[float] = []
        for offset in offsets:
            crop = pil_img.crop((offset, 0, offset + window_width, height))
            tensor = self._transform(crop.resize((image_size[0], image_size[1])))
            similarities.append(
                float(
                    torch.nn.functional.cosine_similarity(
                        tensor.flatten(), goal_flat, dim=0
                    ).item()
                )
            )
            # Window center offset from frame center, normalized to [-1, 1].
            centers.append((offset + window_width / 2 - width / 2) / (width / 2))

        best = max(range(len(similarities)), key=similarities.__getitem__)
        best_similarity = similarities[best]
        others = [s for i, s in enumerate(similarities) if i != best]
        contrast = best_similarity - (sum(others) / len(others)) if others else 0.0

        # Image x grows rightward; robot yaw grows leftward -> sign flip.
        bearing = -centers[best] * math.radians(cfg.camera_hfov_deg) / 2.0
        return bearing, best_similarity, contrast

    # -- loading ------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        try:
            import numpy as np
            import torch
            from torchvision import transforms
        except ImportError as exc:  # pragma: no cover - depends on env
            raise NomadOriginalUnavailableError(
                "NoMaD needs PyTorch + torchvision. Install the ML extras, e.g. "
                "`python -m pip install torch torchvision diffusers efficientnet_pytorch "
                "pillow pyyaml einops` (see scripts/setup_nomad.sh)."
            ) from exc

        self._inject_upstream_paths()

        try:
            from diffusers.schedulers.scheduling_ddpm import DDPMScheduler
            from diffusion_policy.model.diffusion.conditional_unet1d import (
                ConditionalUnet1D,
            )
            from vint_train.models.nomad.nomad import DenseNetwork, NoMaD
            from vint_train.models.nomad.nomad_vint import (
                NoMaD_ViNT,
                replace_bn_with_gn,
            )
        except ImportError as exc:
            raise NomadOriginalUnavailableError(
                "Could not import the NoMaD model code. Run `scripts/setup_nomad.sh` "
                "to clone robodhruv/visualnav-transformer into third_party/ and vendor "
                "the diffusion_policy modules. Searched:\n"
                f"  {self._config.visualnav_train_path}\n"
                f"  {self._config.diffusion_policy_path}"
            ) from exc

        params = self._load_params()
        device = _resolve_device(torch, self._config.device)

        vision_encoder = NoMaD_ViNT(
            obs_encoding_size=params["encoding_size"],
            context_size=params["context_size"],
            mha_num_attention_heads=params["mha_num_attention_heads"],
            mha_num_attention_layers=params["mha_num_attention_layers"],
            mha_ff_dim_factor=params["mha_ff_dim_factor"],
        )
        vision_encoder = replace_bn_with_gn(vision_encoder)
        noise_pred_net = ConditionalUnet1D(
            input_dim=2,
            global_cond_dim=params["encoding_size"],
            down_dims=params["down_dims"],
            cond_predict_scale=params["cond_predict_scale"],
        )
        dist_pred_net = DenseNetwork(embedding_dim=params["encoding_size"])
        model = NoMaD(
            vision_encoder=vision_encoder,
            noise_pred_net=noise_pred_net,
            dist_pred_net=dist_pred_net,
        )

        checkpoint_path = Path(self._config.checkpoint_path)
        if not checkpoint_path.exists():
            raise NomadOriginalUnavailableError(
                f"NoMaD checkpoint not found at {checkpoint_path}. Download nomad.pth "
                "(see scripts/setup_nomad.sh)."
            )
        state_dict = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        result = model.load_state_dict(state_dict, strict=False)
        missing = list(result.missing_keys)
        if missing:
            logger.warning(
                "NoMaD checkpoint loaded with %d missing keys (e.g. %s).",
                len(missing),
                missing[:3],
            )
        model.to(device)
        model.eval()

        scheduler = DDPMScheduler(
            num_train_timesteps=self._config.num_diffusion_iters,
            beta_schedule="squaredcos_cap_v2",
            clip_sample=True,
            prediction_type="epsilon",
        )

        transform = transforms.Compose(
            [
                transforms.ToTensor(),
                transforms.Normalize(mean=_IMAGENET_MEAN, std=_IMAGENET_STD),
            ]
        )

        self._torch = torch
        self._np = np
        self._model = model
        self._scheduler = scheduler
        self._device = device
        self._transform = transform
        self._params = params
        self._goal_tensor = self._load_goal_tensor()
        self._loaded = True

        # Keep the context deque sized to the resolved context length.
        if self._context.maxlen != params["context_size"] + 1:
            self._context = deque(self._context, maxlen=params["context_size"] + 1)

        logger.info(
            "NoMaD loaded: device=%s context_size=%d image_size=%s mode=%s "
            "(%.1fM params)",
            device,
            params["context_size"],
            tuple(params["image_size"]),
            "goal" if self._goal_tensor is not None else "exploration",
            sum(p.numel() for p in model.parameters()) / 1e6,
        )

    def _inject_upstream_paths(self) -> None:
        for path in (self._config.visualnav_train_path, self._config.diffusion_policy_path):
            resolved = str(Path(path).resolve())
            if resolved not in sys.path:
                sys.path.insert(0, resolved)

    def _load_params(self) -> dict[str, Any]:
        """Resolve model hyper-parameters from the upstream config when given."""
        params: dict[str, Any] = {
            "encoding_size": 256,
            "context_size": self._config.context_size,
            "mha_num_attention_heads": 4,
            "mha_num_attention_layers": 4,
            "mha_ff_dim_factor": 4,
            "down_dims": [64, 128, 256],
            "cond_predict_scale": False,
            "len_traj_pred": 8,
            "image_size": [96, 96],  # width, height
            "normalize": True,
        }
        config_path = self._config.model_config_path
        if config_path is not None and Path(config_path).exists():
            import yaml

            with open(config_path) as handle:
                loaded = yaml.safe_load(handle) or {}
            for key in (
                "encoding_size",
                "context_size",
                "mha_num_attention_heads",
                "mha_num_attention_layers",
                "mha_ff_dim_factor",
                "down_dims",
                "cond_predict_scale",
                "len_traj_pred",
                "image_size",
                "normalize",
            ):
                if key in loaded and loaded[key] is not None:
                    params[key] = loaded[key]
        return params

    def _load_goal_tensor(self) -> Any:
        goal_path = self._config.goal_image_path
        if goal_path is None:
            return None
        goal_path = Path(goal_path)
        if not goal_path.exists():
            raise NomadOriginalUnavailableError(
                f"NoMaD goal image not found at {goal_path}."
            )
        from PIL import Image as PILImage

        with PILImage.open(goal_path) as image:
            pil = image.convert("RGB")
        tensor = self._transform_image(pil)  # (1, 3, H, W)
        return tensor.to(self._device)

    # -- inference ----------------------------------------------------------

    def _infer_velocity(self) -> tuple[float, float, dict[str, float]]:
        """Run one inference step.

        Returns (linear_x, angular_z, info). In goal mode, info carries
        goal_distance (model distance head), goal_similarity (direct cosine
        similarity with the goal photo), goal_visibility and goal_bearing_deg
        (heading-assist localization of the goal photo in the frame). Empty
        in exploration mode.
        """
        torch = self._torch
        params = self._params
        cfg = self._config

        obs_images = self._transform_context(list(self._context)).to(self._device)

        if self._goal_tensor is not None:
            goal_image = self._goal_tensor
            mask = torch.zeros(1).long().to(self._device)  # attend to goal
        else:
            image_size = params["image_size"]
            goal_image = torch.randn(
                1, 3, image_size[1], image_size[0], device=self._device
            )
            mask = torch.ones(1).long().to(self._device)  # ignore goal -> explore

        len_traj_pred = params["len_traj_pred"]
        info: dict[str, float] = {}
        goal_distance: float | None = None
        goal_bearing: float | None = None
        if self._goal_tensor is not None:
            current = self._transform_image(self._context[-1]).to(self._device)
            info["goal_similarity"] = float(
                torch.nn.functional.cosine_similarity(
                    current.flatten(), self._goal_tensor.flatten(), dim=0
                ).item()
            )
            if cfg.goal_heading_assist:
                bearing, visibility, contrast = self._estimate_goal_bearing(
                    self._context[-1]
                )
                info["goal_visibility"] = visibility
                info["goal_contrast"] = contrast
                info["goal_bearing_deg"] = math.degrees(bearing)
                trusted = contrast >= cfg.goal_visible_contrast and (
                    cfg.goal_visible_threshold is None
                    or visibility >= cfg.goal_visible_threshold
                )
                goal_bearing = self._update_bearing_filter(bearing, trusted)
                if goal_bearing is not None:
                    info["goal_bearing_applied_deg"] = math.degrees(goal_bearing)
        with torch.no_grad():
            obs_cond = self._model(
                "vision_encoder",
                obs_img=obs_images,
                goal_img=goal_image,
                input_goal_mask=mask,
            )
            if self._goal_tensor is not None:
                # The distance head expects the goal-attended (mask=0)
                # embedding, which is exactly obs_cond in goal mode.
                dist_pred = self._model("dist_pred_net", obsgoal_cond=obs_cond)
                goal_distance = float(dist_pred.flatten()[0].item())
            if obs_cond.ndim == 2:
                obs_cond = obs_cond.repeat(cfg.num_samples, 1)
            else:
                obs_cond = obs_cond.repeat(cfg.num_samples, 1, 1)

            naction = torch.randn(
                cfg.num_samples, len_traj_pred, 2, device=self._device
            )
            self._scheduler.set_timesteps(cfg.num_diffusion_iters)
            for k in self._scheduler.timesteps:
                noise_pred = self._model(
                    "noise_pred_net",
                    sample=naction,
                    timestep=k,
                    global_cond=obs_cond,
                )
                naction = self._scheduler.step(
                    model_output=noise_pred, timestep=k, sample=naction
                ).prev_sample

        waypoints = self._get_action(naction)  # (num_samples, len_traj_pred, 2)
        if cfg.waypoint_aggregation == "mean":
            chosen = waypoints.mean(axis=0)[cfg.waypoint_index].astype(float).copy()
        else:
            chosen = waypoints[0][cfg.waypoint_index].astype(float).copy()

        if params["normalize"]:
            chosen *= cfg.max_linear_speed / cfg.frame_rate

        if goal_distance is not None:
            info["goal_distance"] = goal_distance

        v, w = self._pd_controller(float(chosen[0]), float(chosen[1]))
        if goal_bearing is not None:
            # Heading assist engaged: steer proportionally toward the goal
            # photo. Inside the deadband goal_bearing is exactly 0 -> straight.
            w = max(
                -cfg.max_angular_speed,
                min(cfg.goal_steering_gain * goal_bearing, cfg.max_angular_speed),
            )
        logger.debug("NoMaD waypoint=%s -> v=%.3f w=%.3f info=%s", chosen, v, w, info)
        return v, w, info

    def _get_action(self, diffusion_output: Any) -> Any:
        np = self._np
        ndeltas = diffusion_output.reshape(diffusion_output.shape[0], -1, 2)
        ndeltas = ndeltas.cpu().detach().numpy()
        action_min = np.array(_ACTION_MIN)
        action_max = np.array(_ACTION_MAX)
        ndeltas = (ndeltas + 1) / 2
        ndeltas = ndeltas * (action_max - action_min) + action_min
        return np.cumsum(ndeltas, axis=1)

    def _pd_controller(self, dx: float, dy: float) -> tuple[float, float]:
        cfg = self._config
        dt = 1.0 / cfg.frame_rate
        if abs(dx) < _EPS:
            v = 0.0
            w = math.copysign(math.pi / (2 * dt), dy) if abs(dy) >= _EPS else 0.0
        else:
            v = dx / dt
            w = math.atan(dy / dx) / dt
        v = max(0.0, min(v, cfg.max_linear_speed))
        w = max(-cfg.max_angular_speed, min(w, cfg.max_angular_speed))
        return v, w

    # -- image handling -----------------------------------------------------

    def _transform_context(self, pil_imgs: list[Any]) -> Any:
        torch = self._torch
        tensors = [self._transform_image(img) for img in pil_imgs]
        return torch.cat(tensors, dim=1)  # (1, 3*N, H, W)

    def _transform_image(self, pil_img: Any) -> Any:
        torch = self._torch
        image_size = self._params["image_size"]  # width, height
        if self._config.center_crop:
            pil_img = _center_crop_to_aspect(pil_img, 4.0 / 3.0)
        resized = pil_img.resize((image_size[0], image_size[1]))
        tensor = self._transform(resized)
        return torch.unsqueeze(tensor, 0)

    def _frame_to_pil(self, frame: ImageFrame) -> Any:
        from PIL import Image as PILImage

        encoding = (frame.encoding or "").lower()
        if encoding in {"jpeg", "jpg", "png"} or "compressed" in encoding:
            with PILImage.open(io.BytesIO(frame.data)) as image:
                return image.convert("RGB")

        if encoding in {"rgb8", "bgr8", "rgb", "bgr"}:
            if frame.width is None or frame.height is None:
                raise NomadOriginalUnavailableError(
                    "Raw image frames require width and height."
                )
            np = self._np
            array = np.frombuffer(frame.data, dtype=np.uint8).reshape(
                frame.height, frame.width, 3
            )
            if encoding.startswith("bgr"):
                array = array[:, :, ::-1]
            return PILImage.fromarray(array, mode="RGB")

        # Fallback: let PIL sniff the format (handles most encoded buffers).
        with PILImage.open(io.BytesIO(frame.data)) as image:
            return image.convert("RGB")


def _center_crop_to_aspect(pil_img: Any, aspect: float) -> Any:
    """Center-crop a PIL image to the given width/height aspect ratio."""
    width, height = pil_img.size
    current = width / height
    if abs(current - aspect) < 1e-3:
        return pil_img
    if current > aspect:  # too wide: crop the sides
        new_width = int(round(height * aspect))
        left = (width - new_width) // 2
        return pil_img.crop((left, 0, left + new_width, height))
    new_height = int(round(width / aspect))  # too tall: crop top/bottom
    top = (height - new_height) // 2
    return pil_img.crop((0, top, width, top + new_height))


def _resolve_device(torch: Any, name: str) -> Any:
    name = (name or "cpu").lower()
    if name == "auto":
        if torch.cuda.is_available():
            return torch.device("cuda")
        if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")
    if name == "mps" and not (
        getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available()
    ):
        logger.warning("MPS requested but unavailable; falling back to CPU.")
        return torch.device("cpu")
    if name == "cuda" and not torch.cuda.is_available():
        logger.warning("CUDA requested but unavailable; falling back to CPU.")
        return torch.device("cpu")
    return torch.device(name)
