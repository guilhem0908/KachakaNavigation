from kachaka_navigation.core.messages import ImageFrame
from kachaka_navigation.core.realtime import ImageFreshnessPolicy


def test_freshness_policy_accepts_recent_frame() -> None:
    frame = ImageFrame(data=b"image", encoding="jpeg", timestamp=10.0)
    policy = ImageFreshnessPolicy(max_age_seconds=0.5)

    status = policy.check(frame, now_seconds=10.2)

    assert status.is_fresh
    assert status.age_seconds is not None
    assert abs(status.age_seconds - 0.2) < 0.001


def test_freshness_policy_rejects_stale_frame() -> None:
    frame = ImageFrame(data=b"image", encoding="jpeg", timestamp=10.0)
    policy = ImageFreshnessPolicy(max_age_seconds=0.5)

    status = policy.check(frame, now_seconds=11.0)

    assert not status.is_fresh
    assert status.reason
