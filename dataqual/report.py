"""JSON serialisation for the canonical report."""
from __future__ import annotations

import json

from .core import DataQualityReport


def save_json(report: DataQualityReport, output_path: str) -> str:
    with open(output_path, "w", encoding="utf-8") as output:
        json.dump(report.to_dict(), output, indent=2, ensure_ascii=False, allow_nan=False)
        output.write("\n")
    return output_path
