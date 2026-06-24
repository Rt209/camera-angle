from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

from src.shared.output_contract import EvaluationArtifacts


def write_per_frame(
    artifacts: EvaluationArtifacts,
    rows: Iterable[dict[str, Any]],
    columns: list[str],
) -> Path:
    artifacts.directory.mkdir(parents=True, exist_ok=True)
    with artifacts.per_frame.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column) for column in columns})
    return artifacts.per_frame


def write_summary(artifacts: EvaluationArtifacts, summary: dict[str, Any]) -> Path:
    artifacts.directory.mkdir(parents=True, exist_ok=True)
    artifacts.summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return artifacts.summary


def write_report(artifacts: EvaluationArtifacts, markdown: str) -> Path:
    artifacts.directory.mkdir(parents=True, exist_ok=True)
    artifacts.report.write_text(markdown, encoding="utf-8")
    return artifacts.report
