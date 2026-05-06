from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.table import Table


SECTION_TITLES = {
    "file_info": "File Info",
    "device_info": "Device Info",
    "optical_parameters": "Optical Parameters",
    "exposure_parameters": "Exposure Parameters",
    "image_parameters": "Image Parameters",
    "gps_direction": "GPS / Direction",
    "derived_geometry": "Derived Geometry",
}


def print_report(data: dict[str, Any]) -> None:
    console = Console()
    for key, title in SECTION_TITLES.items():
        table = Table(title=title, show_header=True, header_style="bold cyan")
        table.add_column("Field", style="bold")
        table.add_column("Value")
        section = data.get(key, {})
        for field, value in section.items():
            table.add_row(str(field), _display(value))
        console.print(table)

    warnings = data.get("warnings", [])
    warning_table = Table(title="Warnings", show_header=True, header_style="bold yellow")
    warning_table.add_column("#", style="bold")
    warning_table.add_column("Message")
    if warnings:
        for index, warning in enumerate(warnings, start=1):
            warning_table.add_row(str(index), str(warning))
    else:
        warning_table.add_row("-", "N/A")
    console.print(warning_table)


def _display(value: Any) -> str:
    if value is None or value == "":
        return "N/A"
    return str(value)
