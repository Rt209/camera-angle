from dataclasses import dataclass


@dataclass(frozen=True)
class CalibrationProfile:
    name: str
    sensor_width_mm: float
    sensor_height_mm: float


# Future work: load per-device calibration profiles from JSON/YAML.
# Accurate FOV needs sensor dimensions or a calibrated camera model.
