from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.table import Table


def print_pose_report(data: dict[str, Any]) -> None:
    console = Console()
    pose_table = Table(title="Visual Pose Result", show_header=True, header_style="bold cyan")
    pose_table.add_column("Field", style="bold")
    pose_table.add_column("Value")
    for field in ["image", "yaw", "pitch", "roll", "unit", "confidence", "method", "stage"]:
        pose_table.add_row(field, _display(data.get(field)))
    console.print(pose_table)

    confidence_table = Table(title="Angle Confidence", show_header=True, header_style="bold cyan")
    confidence_table.add_column("Angle", style="bold")
    confidence_table.add_column("Confidence")
    for key, value in data.get("angle_confidence", {}).items():
        confidence_table.add_row(key, _display(value))
    if data.get("angle_confidence"):
        console.print(confidence_table)

    feature_table = Table(title="Geometry Features", show_header=True, header_style="bold cyan")
    feature_table.add_column("Field", style="bold")
    feature_table.add_column("Value")
    feature_table.add_row("features_used", ", ".join(data.get("features_used", [])))
    for section_name in ["line_features", "horizon_features", "vanishing_point_features"]:
        for key, value in data.get(section_name, {}).items():
            if key not in {"lines", "selected_horizon", "selected_vanishing_point"}:
                feature_table.add_row(f"{section_name}.{key}", _display(value))
    console.print(feature_table)

    debug_table = Table(title="Debug Artifacts", show_header=True, header_style="bold cyan")
    debug_table.add_column("Name", style="bold")
    debug_table.add_column("Path")
    for key, value in data.get("debug_artifacts", {}).items():
        debug_table.add_row(key, str(value))
    if not data.get("debug_artifacts"):
        debug_table.add_row("-", "N/A")
    console.print(debug_table)

    warnings = data.get("warnings", [])
    if warnings:
        warning_table = Table(title="Warnings", show_header=True, header_style="bold yellow")
        warning_table.add_column("#", style="bold")
        warning_table.add_column("Message")
        for index, warning in enumerate(warnings, start=1):
            warning_table.add_row(str(index), str(warning))
        console.print(warning_table)


def _display(value: Any) -> str:
    if value is None or value == "":
        return "N/A"
    return str(value)
