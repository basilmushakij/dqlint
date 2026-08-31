"""Small, plain-text terminal reports for dqlint."""
from __future__ import annotations

from typing import Optional

from .core import ColumnReport, DataQualityReport, OutlierReport

RULE = "-" * 36


def _format_size(size_bytes: Optional[int]) -> str:
    if size_bytes is None:
        return "Unknown"
    units = ("bytes", "KiB", "MiB", "GiB")
    size = float(size_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{int(size):,} {unit}" if unit == "bytes" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GiB"


def _format_percent(value: float) -> str:
    return f"{value:.2f}%"


def _number(value: float) -> str:
    return f"{value:.6g}"


def _section(title: str) -> list[str]:
    return ["", title, RULE, ""]


def _column_line(column: ColumnReport) -> str:
    return f"  {column.name:<22} {column.dtype}"


def _outlier_lines(column: ColumnReport, outliers: OutlierReport) -> list[str]:
    return [
        column.name,
        f"  Method: {outliers.method}",
        f"  Q1: {_number(outliers.q1)}",
        f"  Q3: {_number(outliers.q3)}",
        f"  IQR: {_number(outliers.iqr)}",
        f"  Lower bound: {_number(outliers.lower_bound)}",
        f"  Upper bound: {_number(outliers.upper_bound)}",
        f"  Count: {outliers.count:,} / {outliers.value_count:,} ({_format_percent(outliers.percentage)})",
        "",
    ]


def render(report: DataQualityReport, full: bool = False) -> str:
    """Return the concise default report, with factual detail in full mode."""
    lines = ["dqlint", RULE]
    lines.extend(
        [
            "",
            "DATASET",
            f"  File       {report.file_name}",
            f"  Size       {_format_size(report.file_size_bytes)}",
            f"  Rows       {report.row_count:,}",
            f"  Columns    {report.column_count:,}",
        ]
    )
    lines.extend(_section("COLUMNS"))
    lines.extend(_column_line(column) for column in report.columns)
    lines.extend(_section("QUALITY"))
    lines.extend(
        [
            f"  Missing values    {report.missing_column_count:,} columns",
            f"  Duplicate rows    {report.duplicate_row_count:,}",
            f"  Possible outliers {report.outlier_column_count:,} columns",
            f"  Empty columns     {report.empty_column_count:,}",
            f"  Constant columns  {report.constant_column_count:,}",
            "",
            RULE,
        ]
    )

    if not full:
        lines.extend(
            [
                "",
                "Use:",
                "",
                f"  dqlint {report.file_name} --full",
                "",
                "for column-level details.",
            ]
        )
        return "\n".join(lines)

    lines.extend(_section("COLUMN OVERVIEW"))
    lines.append(f"  {'Column':<22} {'Type':<18} {'Missing':>18} {'Unique':>12}")
    for column in report.columns:
        missing = f"{column.missing_count:,} ({_format_percent(column.missing_percentage)})"
        lines.append(
            f"  {column.name:<22} {column.dtype:<18} {missing:>18} {column.unique_count:>12,}"
        )

    lines.extend(_section("DUPLICATE ROWS"))
    lines.extend(
        [
            f"  {report.duplicate_row_count:,} / {report.row_count:,} ({_format_percent(report.duplicate_row_percentage)})",
            "  Method: exact full-row comparison",
        ]
    )

    missing_columns = [column for column in report.columns if column.missing_count]
    lines.extend(_section("MISSING VALUES"))
    if missing_columns:
        for column in missing_columns:
            lines.append(
                f"  {column.name}: {column.missing_count:,} / {report.row_count:,} "
                f"({_format_percent(column.missing_percentage)})"
            )
    else:
        lines.append("  No missing values detected.")

    empty_columns = [column for column in report.columns if column.is_empty]
    lines.extend(_section("EMPTY COLUMNS"))
    lines.extend(f"  {column.name}" for column in empty_columns)
    if not empty_columns:
        lines.append("  None detected.")

    constant_columns = [column for column in report.columns if column.is_constant]
    lines.extend(_section("CONSTANT COLUMNS"))
    lines.extend(f"  {column.name}" for column in constant_columns)
    if not constant_columns:
        lines.append("  None detected.")

    outlier_columns = [
        column
        for column in report.columns
        if column.outliers is not None and column.outliers.count > 0
    ]
    lines.extend(_section("POSSIBLE OUTLIERS"))
    if outlier_columns:
        for column in outlier_columns:
            lines.extend(_outlier_lines(column, column.outliers))
    else:
        lines.append("  No values outside the IQR bounds detected.")

    return "\n".join(lines)
