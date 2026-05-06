from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def to_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def write_json(data: dict[str, Any], output_path: Path) -> None:
    output_path.write_text(to_json(data), encoding="utf-8")
