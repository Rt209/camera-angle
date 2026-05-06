from math import atan, degrees


def compute_fov(sensor_size_mm: float, focal_length_mm: float) -> float:
    if sensor_size_mm <= 0:
        raise ValueError("sensor_size_mm must be greater than 0")
    if focal_length_mm <= 0:
        raise ValueError("focal_length_mm must be greater than 0")
    return degrees(2 * atan(sensor_size_mm / (2 * focal_length_mm)))
