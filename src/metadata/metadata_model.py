from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class MetadataReport:
    file_info: dict[str, Any] = field(default_factory=dict)
    device_info: dict[str, Any] = field(default_factory=dict)
    optical_parameters: dict[str, Any] = field(default_factory=dict)
    exposure_parameters: dict[str, Any] = field(default_factory=dict)
    image_parameters: dict[str, Any] = field(default_factory=dict)
    gps_direction: dict[str, Any] = field(default_factory=dict)
    derived_geometry: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
