from fractions import Fraction

from src.processing.value_converter import (
    format_aperture,
    format_ev,
    format_exposure_time,
    format_focal_length,
    to_float,
)


def test_to_float_converts_fraction() -> None:
    assert to_float(Fraction(1, 120)) == 1 / 120


def test_format_exposure_time_as_fraction() -> None:
    assert format_exposure_time(Fraction(1, 120)) == "1/120s"


def test_format_aperture() -> None:
    assert format_aperture(Fraction(9, 5)) == "f/1.8"


def test_format_focal_length() -> None:
    assert format_focal_length(Fraction(24, 1)) == "24mm"


def test_format_ev() -> None:
    assert format_ev(Fraction(-1, 3)) == "-0.33 EV"
