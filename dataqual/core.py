"""
dataqual.core
=============
Core data-quality analysis engine. Pure logic, no printing/formatting here,
so it can be reused by the terminal reporter, the HTML reporter, or imported
directly in a notebook / script.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import pandas as pd
import numpy as np


SUPPORTED_EXTENSIONS = {".csv", ".tsv", ".xlsx", ".xls", ".json", ".parquet"}


def load_file(path: str) -> pd.DataFrame:
    """Load a tabular file into a pandas DataFrame based on its extension."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    ext = os.path.splitext(path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    if ext == ".csv":
        return pd.read_csv(path)
    if ext == ".tsv":
        return pd.read_csv(path, sep="\t")
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(path)
    if ext == ".json":
        return pd.read_json(path)
    if ext == ".parquet":
        return pd.read_parquet(path)

    raise ValueError(f"Unsupported file type '{ext}'")


@dataclass
class ColumnReport:
    name: str
    dtype: str
    n_missing: int
    pct_missing: float
    n_unique: int
    pct_unique: float
    is_constant: bool
    is_high_cardinality: bool
    numeric_stats: dict[str, Any] | None = None
    n_outliers: int | None = None
    top_values: list[tuple[Any, int]] = field(default_factory=list)
    quality_score: float = 100.0
    issues: list[str] = field(default_factory=list)


@dataclass
class DataQualityReport:
    file_path: str
    n_rows: int
    n_cols: int
    memory_mb: float
    n_duplicate_rows: int
    pct_duplicate_rows: float
    overall_score: float
    columns: list[ColumnReport]
    global_issues: list[str] = field(default_factory=list)


HIGH_CARDINALITY_RATIO = 0.9  # unique/rows above this -> likely ID-like column
OUTLIER_IQR_MULTIPLIER = 1.5


def _numeric_stats(series: pd.Series) -> tuple[dict[str, Any], int]:
    clean = series.dropna()
    if clean.empty:
        return {}, 0

    q1, q3 = clean.quantile(0.25), clean.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - OUTLIER_IQR_MULTIPLIER * iqr
    upper = q3 + OUTLIER_IQR_MULTIPLIER * iqr
    n_outliers = int(((clean < lower) | (clean > upper)).sum())

    stats = {
        "min": float(clean.min()),
        "max": float(clean.max()),
        "mean": float(clean.mean()),
        "median": float(clean.median()),
        "std": float(clean.std()) if len(clean) > 1 else 0.0,
        "q1": float(q1),
        "q3": float(q3),
    }
    return stats, n_outliers


def _column_score(pct_missing: float, is_constant: bool,
                   outlier_ratio: float) -> tuple[float, list[str]]:
    score = 100.0
    issues = []

    if pct_missing > 0:
        penalty = min(40, pct_missing * 0.6)
        score -= penalty
        if pct_missing >= 50:
            issues.append(f"{pct_missing:.1f}% missing (high)")
        elif pct_missing >= 5:
            issues.append(f"{pct_missing:.1f}% missing")

    if is_constant:
        score -= 30
        issues.append("constant value, no variation")

    if outlier_ratio > 0:
        penalty = min(20, outlier_ratio * 100 * 0.5)
        score -= penalty
        # A handful of extreme values matter even if they're a tiny fraction
        # of the column, so this is deliberately a low bar (not just >=5%).
        if outlier_ratio >= 0.01:
            issues.append(f"outliers detected (~{outlier_ratio*100:.1f}%)")

    return max(0.0, score), issues


def analyze(df: pd.DataFrame, file_path: str = "<in-memory>") -> DataQualityReport:
    n_rows, n_cols = df.shape
    memory_mb = df.memory_usage(deep=True).sum() / (1024 ** 2)

    n_dup = int(df.duplicated().sum())
    pct_dup = (n_dup / n_rows * 100) if n_rows else 0.0

    col_reports: list[ColumnReport] = []
    global_issues: list[str] = []

    if n_rows == 0:
        global_issues.append("File has no data (0 rows)")

    for col in df.columns:
        series = df[col]
        n_missing = int(series.isna().sum())
        pct_missing = (n_missing / n_rows * 100) if n_rows else 0.0
        n_unique = int(series.nunique(dropna=True))
        pct_unique = (n_unique / n_rows * 100) if n_rows else 0.0
        is_constant = n_unique <= 1 and n_rows > 0
        is_numeric = pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series)
        # Continuous numeric columns (e.g. amounts, measurements) are expected
        # to be near-100% unique -- that's not an "ID column" smell the way it
        # is for a string/integer column, so only flag high cardinality there.
        is_high_card = (
            n_rows > 0
            and (n_unique / n_rows) >= HIGH_CARDINALITY_RATIO
            and n_unique > 1
            and not pd.api.types.is_float_dtype(series)
        )

        numeric_stats = None
        n_outliers = None
        outlier_ratio = 0.0
        if is_numeric:
            numeric_stats, n_outliers = _numeric_stats(series)
            n_non_null = n_rows - n_missing
            outlier_ratio = (n_outliers / n_non_null) if n_non_null else 0.0

        top_values = []
        if not is_numeric:
            vc = series.value_counts(dropna=True).head(5)
            top_values = list(zip(vc.index.tolist(), vc.values.tolist()))

        score, issues = _column_score(pct_missing, is_constant, outlier_ratio)

        col_reports.append(ColumnReport(
            name=str(col),
            dtype=str(series.dtype),
            n_missing=n_missing,
            pct_missing=round(pct_missing, 2),
            n_unique=n_unique,
            pct_unique=round(pct_unique, 2),
            is_constant=is_constant,
            is_high_cardinality=is_high_card,
            numeric_stats=numeric_stats,
            n_outliers=n_outliers,
            top_values=top_values,
            quality_score=round(score, 1),
            issues=issues,
        ))

    if pct_dup > 0:
        global_issues.append(f"{n_dup} duplicate rows found ({pct_dup:.1f}%)")

    if col_reports:
        overall_score = round(sum(c.quality_score for c in col_reports) / len(col_reports), 1)
    else:
        overall_score = 0.0
    overall_score = max(0.0, overall_score - min(15, pct_dup * 0.3))

    return DataQualityReport(
        file_path=file_path,
        n_rows=n_rows,
        n_cols=n_cols,
        memory_mb=round(memory_mb, 3),
        n_duplicate_rows=n_dup,
        pct_duplicate_rows=round(pct_dup, 2),
        overall_score=round(overall_score, 1),
        columns=col_reports,
        global_issues=global_issues,
    )
