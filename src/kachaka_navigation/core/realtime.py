from __future__ import annotations

from dataclasses import dataclass

from kachaka_navigation.core.messages import ImageFrame


@dataclass(frozen=True, slots=True)
class ImageFreshnessStatus:
    is_fresh: bool
    age_seconds: float | None
    reason: str = ""


@dataclass(frozen=True, slots=True)
class ImageFreshnessPolicy:
    """Rejects stale frames before they reach a navigation model."""

    max_age_seconds: float = 0.5
    require_timestamp: bool = False

    def __post_init__(self) -> None:
        if self.max_age_seconds <= 0:
            raise ValueError("max_age_seconds must be positive.")

    def check(self, frame: ImageFrame, now_seconds: float) -> ImageFreshnessStatus:
        timestamp = frame.timestamp
        if timestamp is None:
            if self.require_timestamp:
                return ImageFreshnessStatus(
                    is_fresh=False,
                    age_seconds=None,
                    reason="Image has no timestamp.",
                )
            return ImageFreshnessStatus(is_fresh=True, age_seconds=None)

        age_seconds = now_seconds - timestamp
        if age_seconds < 0:
            return ImageFreshnessStatus(
                is_fresh=False,
                age_seconds=age_seconds,
                reason="Image timestamp is in the future.",
            )
        if age_seconds > self.max_age_seconds:
            return ImageFreshnessStatus(
                is_fresh=False,
                age_seconds=age_seconds,
                reason=(
                    f"Image is too old: {age_seconds:.3f}s "
                    f"> {self.max_age_seconds:.3f}s."
                ),
            )

        return ImageFreshnessStatus(is_fresh=True, age_seconds=age_seconds)
