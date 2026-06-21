from src.contexts.geometry_features.domain.line_feature_set import LineFeatureSet
from src.contexts.geometry_features.domain.line_segment import LineSegment
from src.contexts.pose_estimation.services.roll_estimator import estimate_roll


def test_estimate_roll_from_near_horizontal_lines() -> None:
    lines = [
        LineSegment.from_points(0, 10, 200, 20, 20.0, 20.0),
        LineSegment.from_points(0, 40, 160, 48, 20.0, 20.0),
    ]
    estimate = estimate_roll(LineFeatureSet(detected_lines=lines, filtered_lines=lines))

    assert estimate.roll is not None
    assert -4.0 <= estimate.roll <= -2.0
    assert estimate.confidence > 0


def test_estimate_roll_returns_none_without_candidates() -> None:
    lines = [
        LineSegment.from_points(0, 0, 100, 100, 20.0, 20.0),
    ]
    estimate = estimate_roll(LineFeatureSet(detected_lines=lines, filtered_lines=lines))

    assert estimate.roll is None
    assert estimate.confidence == 0.0
