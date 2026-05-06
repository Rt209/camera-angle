from __future__ import annotations

from fractions import Fraction
from typing import Any

from PIL.TiffImagePlugin import IFDRational


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, IFDRational):
        return float(value)
    if isinstance(value, Fraction):
        return float(value)
    if isinstance(value, tuple) and len(value) == 2:
        numerator, denominator = value
        if denominator == 0:
            return None
        return float(numerator) / float(denominator)
    if isinstance(value, (int, float)):
        return float(value)

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def format_exposure_time(value: Any) -> str:
    number = to_float(value)
    if number is None or number <= 0:
        return "N/A"
    if number < 1:
        denominator = round(1 / number)
        return f"1/{denominator}s"
    return f"{number:g}s"


def format_aperture(value: Any) -> str:
    number = to_float(value)
    if number is None:
        return "N/A"
    return f"f/{number:.1f}".rstrip("0").rstrip(".")


def format_focal_length(value: Any) -> str:
    number = to_float(value)
    if number is None:
        return "N/A"
    display = f"{number:.1f}".rstrip("0").rstrip(".")
    return f"{display}mm"


def format_ev(value: Any) -> str:
    number = to_float(value)
    if number is None:
        return "N/A"
    return f"{number:+.2f} EV"


def rational_to_display(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, IFDRational):
        return str(value)
    if isinstance(value, tuple) and len(value) == 2:
        return f"{value[0]}/{value[1]}"
    return str(value)
