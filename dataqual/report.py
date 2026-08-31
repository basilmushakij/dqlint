"""Self-contained HTML and JSON serialisation for the canonical report."""
from __future__ import annotations

import html
import json
from typing import Iterable

from .core import ColumnReport, DataQualityReport


def _number(value: float) -> str:
    return f"{value:.6g}"


def _percent(value: float) -> str:
    return f"{value:.2f}%"


def _rows(columns: Iterable[ColumnReport]) -> str:
    return "".join(
        "<tr>"
        f"<td>{html.escape(column.name)}</td>"
        f"<td>{html.escape(column.dtype)}</td>"
        f"<td>{column.missing_count:,} ({_percent(column.missing_percentage)})</td>"
        f"<td>{column.unique_count:,}</td>"
        f"<td>{'Yes' if column.is_empty else 'No'}</td>"
        f"<td>{'Yes' if column.is_constant else 'No'}</td>"
        "</tr>"
        for column in columns
    )


def build_html(report: DataQualityReport) -> str:
    """Build a deterministic, offline HTML view of the same factual report."""
    outlier_blocks = []
    for column in report.columns:
        outliers = column.outliers
        if outliers is None or not outliers.count:
            continue
        outlier_blocks.append(
            "<section><h3>" + html.escape(column.name) + "</h3>"
            "<dl>"
            f"<dt>Method</dt><dd>{html.escape(outliers.method)}</dd>"
            f"<dt>Q1</dt><dd>{_number(outliers.q1)}</dd>"
            f"<dt>Q3</dt><dd>{_number(outliers.q3)}</dd>"
            f"<dt>IQR</dt><dd>{_number(outliers.iqr)}</dd>"
            f"<dt>Lower bound</dt><dd>{_number(outliers.lower_bound)}</dd>"
            f"<dt>Upper bound</dt><dd>{_number(outliers.upper_bound)}</dd>"
            f"<dt>Count</dt><dd>{outliers.count:,} / {outliers.value_count:,} ({_percent(outliers.percentage)})</dd>"
            "</dl></section>"
        )
    outliers_html = "".join(outlier_blocks) or "<p>No values outside the IQR bounds detected.</p>"

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>dqlint report: {html.escape(report.file_name)}</title>
<style>
body{{font:16px/1.5 system-ui,sans-serif;color:#20242b;max-width:960px;margin:2rem auto;padding:0 1rem}}
h1,h2,h3{{margin-bottom:.4rem}} section{{margin:2rem 0}} table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #d8dde3;padding:.45rem;text-align:left}} th{{background:#f2f4f7}}
dl{{display:grid;grid-template-columns:max-content 1fr;gap:.25rem 1rem}} dt{{font-weight:600}} dd{{margin:0}}
</style>
</head>
<body>
<h1>dqlint</h1>
<section><h2>Dataset</h2>
<dl>
<dt>File</dt><dd>{html.escape(report.file_name)}</dd>
<dt>Size</dt><dd>{report.file_size_bytes if report.file_size_bytes is not None else 'Unknown'} bytes</dd>
<dt>Rows</dt><dd>{report.row_count:,}</dd>
<dt>Columns</dt><dd>{report.column_count:,}</dd>
</dl></section>
<section><h2>Quality facts</h2>
<dl>
<dt>Columns with missing values</dt><dd>{report.missing_column_count:,}</dd>
<dt>Duplicate rows</dt><dd>{report.duplicate_row_count:,} / {report.row_count:,} ({_percent(report.duplicate_row_percentage)})</dd>
<dt>Duplicate method</dt><dd>exact full-row comparison</dd>
<dt>Columns with possible outliers</dt><dd>{report.outlier_column_count:,}</dd>
<dt>Empty columns</dt><dd>{report.empty_column_count:,}</dd>
<dt>Constant columns</dt><dd>{report.constant_column_count:,}</dd>
</dl></section>
<section><h2>Columns</h2>
<table><thead><tr><th>Column</th><th>Type</th><th>Missing</th><th>Unique</th><th>Empty</th><th>Constant</th></tr></thead>
<tbody>{_rows(report.columns)}</tbody></table></section>
<section><h2>Possible outliers</h2>{outliers_html}</section>
</body></html>"""


def save_html(report: DataQualityReport, output_path: str) -> str:
    with open(output_path, "w", encoding="utf-8") as output:
        output.write(build_html(report))
    return output_path


def save_json(report: DataQualityReport, output_path: str) -> str:
    with open(output_path, "w", encoding="utf-8") as output:
        json.dump(report.to_dict(), output, indent=2, ensure_ascii=False, allow_nan=False)
        output.write("\n")
    return output_path
