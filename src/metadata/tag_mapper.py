from __future__ import annotations

from typing import Any

from PIL.ExifTags import GPSTAGS, TAGS


EXPOSURE_PROGRAMS = {
    0: "Not defined",
    1: "Manual",
    2: "Normal program",
    3: "Aperture priority",
    4: "Shutter priority",
    5: "Creative program",
    6: "Action program",
    7: "Portrait mode",
    8: "Landscape mode",
}

METERING_MODES = {
    0: "Unknown",
    1: "Average",
    2: "Center-weighted average",
    3: "Spot",
    4: "Multi-spot",
    5: "Pattern",
    6: "Partial",
    255: "Other",
}

WHITE_BALANCE = {
    0: "Auto",
    1: "Manual",
}

ORIENTATION = {
    1: "Horizontal (normal)",
    2: "Mirrored horizontal",
    3: "Rotated 180",
    4: "Mirrored vertical",
    5: "Mirrored horizontal then rotated 90 CCW",
    6: "Rotated 90 CW",
    7: "Mirrored horizontal then rotated 90 CW",
    8: "Rotated 90 CCW",
}


def decode_exif_tags(raw_exif: dict[int, Any]) -> dict[str, Any]:
    decoded: dict[str, Any] = {}
    for tag_id, value in raw_exif.items():
        name = TAGS.get(tag_id, tag_id)
        if name == "GPSInfo" and isinstance(value, dict):
            decoded[name] = decode_gps_tags(value)
        else:
            decoded[str(name)] = value
    return decoded


def decode_gps_tags(gps_info: dict[int, Any]) -> dict[str, Any]:
    return {str(GPSTAGS.get(key, key)): value for key, value in gps_info.items()}


def enum_label(mapping: dict[int, str], value: Any) -> str:
    if value is None:
        return "N/A"
    try:
        key = int(value)
    except (TypeError, ValueError):
        return str(value)
    return mapping.get(key, str(value))
