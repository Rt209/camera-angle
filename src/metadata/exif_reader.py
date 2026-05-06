from __future__ import annotations

from pathlib import Path
from typing import Any

from src.geometry.camera_model import CalibrationProfile
from src.geometry.fov import compute_fov
from src.io.image_loader import get_basic_image_info, open_image
from src.metadata.metadata_model import MetadataReport
from src.metadata.tag_mapper import (
    EXPOSURE_PROGRAMS,
    METERING_MODES,
    ORIENTATION,
    WHITE_BALANCE,
    decode_exif_tags,
    enum_label,
)
from src.processing.value_converter import (
    format_aperture,
    format_ev,
    format_exposure_time,
    format_focal_length,
    rational_to_display,
    to_float,
)


class ExifReadError(RuntimeError):
    """Raised when an image cannot be opened or EXIF cannot be inspected."""


def read_metadata(path: Path, calibration: CalibrationProfile | None = None) -> MetadataReport:
    try:
        with open_image(path) as image:
            basic_info = get_basic_image_info(image)
            raw_exif = image.getexif()
            decoded = decode_exif_tags(dict(raw_exif)) if raw_exif else {}
    except Exception as exc:
        raise ExifReadError(f"Could not read image metadata: {exc}") from exc

    report = MetadataReport()
    report.file_info = {
        "path": str(path),
        "filename": path.name,
        "extension": path.suffix.lower(),
        "format": basic_info.get("format") or "N/A",
        "mode": basic_info.get("mode") or "N/A",
    }

    if not decoded:
        report.warnings.append("No EXIF metadata found in this image.")

    report.device_info = _device_info(decoded)
    report.optical_parameters = _optical_parameters(decoded)
    report.exposure_parameters = _exposure_parameters(decoded)
    report.image_parameters = _image_parameters(decoded, basic_info)
    report.gps_direction = _gps_direction(decoded)
    report.derived_geometry = _derived_geometry(decoded, report, calibration)

    return report


def _value(data: dict[str, Any], key: str) -> Any:
    return data.get(key)


def _text(value: Any) -> str:
    if value is None or value == "":
        return "N/A"
    return str(value)


def _device_info(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "Make": _text(_value(data, "Make")),
        "Model": _text(_value(data, "Model")),
        "Software": _text(_value(data, "Software")),
    }


def _optical_parameters(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "FocalLength": format_focal_length(_value(data, "FocalLength")),
        "FNumber": format_aperture(_value(data, "FNumber")),
        "LensModel": _text(_value(data, "LensModel")),
        "FocalLengthIn35mmFilm": (
            f"{_value(data, 'FocalLengthIn35mmFilm')}mm"
            if _value(data, "FocalLengthIn35mmFilm") is not None
            else "N/A"
        ),
    }


def _exposure_parameters(data: dict[str, Any]) -> dict[str, Any]:
    iso = _value(data, "ISOSpeedRatings") or _value(data, "PhotographicSensitivity")
    return {
        "ExposureTime": format_exposure_time(_value(data, "ExposureTime")),
        "ISOSpeedRatings": _text(iso),
        "ExposureBiasValue": format_ev(_value(data, "ExposureBiasValue")),
        "ExposureProgram": enum_label(EXPOSURE_PROGRAMS, _value(data, "ExposureProgram")),
        "WhiteBalance": enum_label(WHITE_BALANCE, _value(data, "WhiteBalance")),
        "Flash": _text(_value(data, "Flash")),
        "MeteringMode": enum_label(METERING_MODES, _value(data, "MeteringMode")),
        "DateTimeOriginal": _text(_value(data, "DateTimeOriginal")),
    }


def _image_parameters(data: dict[str, Any], basic_info: dict[str, Any]) -> dict[str, Any]:
    width = _value(data, "ImageWidth") or _value(data, "ExifImageWidth") or basic_info["image_width"]
    height = _value(data, "ImageLength") or _value(data, "ExifImageHeight") or basic_info["image_height"]
    return {
        "ImageWidth": _text(width),
        "ImageLength": _text(height),
        "XResolution": rational_to_display(_value(data, "XResolution")),
        "YResolution": rational_to_display(_value(data, "YResolution")),
        "Orientation": enum_label(ORIENTATION, _value(data, "Orientation")),
    }


def _gps_direction(data: dict[str, Any]) -> dict[str, Any]:
    gps = _value(data, "GPSInfo") or {}
    return {
        "GPSLatitude": _format_gps_coordinate(gps.get("GPSLatitude"), gps.get("GPSLatitudeRef")),
        "GPSLongitude": _format_gps_coordinate(gps.get("GPSLongitude"), gps.get("GPSLongitudeRef")),
        "GPSAltitude": _format_gps_altitude(gps.get("GPSAltitude"), gps.get("GPSAltitudeRef")),
        "GPSImgDirection": _format_direction(gps.get("GPSImgDirection")),
    }


def _derived_geometry(
    data: dict[str, Any],
    report: MetadataReport,
    calibration: CalibrationProfile | None,
) -> dict[str, Any]:
    focal_length_mm = to_float(_value(data, "FocalLength"))
    geometry: dict[str, Any] = {
        "HorizontalFOV": "N/A",
        "VerticalFOV": "N/A",
        "PitchAngle": "Unavailable from EXIF only",
        "Depth": "Unavailable from a single ordinary EXIF photo",
    }

    if focal_length_mm and calibration:
        geometry["HorizontalFOV"] = f"{compute_fov(calibration.sensor_width_mm, focal_length_mm):.2f} deg"
        geometry["VerticalFOV"] = f"{compute_fov(calibration.sensor_height_mm, focal_length_mm):.2f} deg"
    elif focal_length_mm:
        report.warnings.append(
            "Cannot compute accurate FOV without sensor size or calibration profile."
        )
    else:
        report.warnings.append("Cannot compute FOV because FocalLength is unavailable.")

    if report.gps_direction.get("GPSImgDirection") == "N/A":
        report.warnings.append("GPSImgDirection is unavailable; shooting direction is not inferred.")

    report.warnings.append(
        "Pitch angle and depth require IMU, calibration, horizon/vanishing point analysis, stereo, structured light, or another supported source."
    )
    return geometry


def _format_gps_coordinate(value: Any, ref: Any) -> str:
    if value is None:
        return "N/A"
    try:
        degrees = to_float(value[0]) or 0
        minutes = to_float(value[1]) or 0
        seconds = to_float(value[2]) or 0
        decimal = degrees + minutes / 60 + seconds / 3600
        if ref in {"S", "W"}:
            decimal *= -1
        return f"{decimal:.6f}"
    except (TypeError, IndexError):
        return _text(value)


def _format_gps_altitude(value: Any, ref: Any) -> str:
    altitude = to_float(value)
    if altitude is None:
        return "N/A"
    if ref == 1:
        altitude *= -1
    return f"{altitude:.2f} m"


def _format_direction(value: Any) -> str:
    direction = to_float(value)
    if direction is None:
        return "N/A"
    return f"{direction:.2f} deg"
