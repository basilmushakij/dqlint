"""Deterministic, factual dataset inspection used by every dqlint output."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import pandas as pd

SUPPORTED_FORMATS = {".csv", ".tsv", ".xlsx", ".json", ".parquet"}
IQR_MULTIPLIER = 1.5


class DataLoadError(Exception):
    """A short, user-facing error while reading an input dataset."""

    def __init__(self, title: str, reason: str, install: Optional[str] = None):
        super().__init__(reason)
        self.title = title
        self.reason = reason
        self.install = install


@dataclass
class OutlierReport:
    """Values outside the standard 1.5 × IQR bounds for one numeric column."""

    q1: float
    q3: float
    iqr: float
    lower_bound: float
    upper_bound: float
    count: int
    value_count: int
    percentage: float
    method: str = "IQR (Q1 - 1.5 × IQR to Q3 + 1.5 × IQR)"

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "q1": self.q1,
            "q3": self.q3,
            "iqr": self.iqr,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "count": self.count,
            "value_count": self.value_count,
            "percentage": self.percentage,
        }


@dataclass
class ColumnReport:
    name: str
    dtype: str
    missing_count: int
    missing_percentage: float
    unique_count: int
    is_empty: bool
    is_constant: bool
    outliers: Optional[OutlierReport]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "dtype": self.dtype,
            "missing_count": self.missing_count,
            "missing_percentage": self.missing_percentage,
            "unique_count": self.unique_count,
            "is_empty": self.is_empty,
            "is_constant": self.is_constant,
            "outliers": self.outliers.to_dict() if self.outliers else None,
        }


@dataclass
class DataQualityReport:
    file_path: str
    file_name: str
    file_size_bytes: Optional[int]
    row_count: int
    column_count: int
    duplicate_row_count: int
    duplicate_row_percentage: float
    columns: list[ColumnReport]

    @property
    def missing_column_count(self) -> int:
        return sum(column.missing_count > 0 for column in self.columns)

    @property
    def outlier_column_count(self) -> int:
        return sum(
            column.outliers is not None and column.outliers.count > 0
            for column in self.columns
        )

    @property
    def empty_column_count(self) -> int:
        return sum(column.is_empty for column in self.columns)

    @property
    def constant_column_count(self) -> int:
        return sum(column.is_constant for column in self.columns)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset": {
                "file": self.file_name,
                "path": self.file_path,
                "size_bytes": self.file_size_bytes,
                "rows": self.row_count,
                "columns": self.column_count,
            },
            "columns": [column.to_dict() for column in self.columns],
            "quality": {
                "missing_columns": self.missing_column_count,
                "duplicate_rows": self.duplicate_row_count,
                "duplicate_row_percentage": self.duplicate_row_percentage,
                "outlier_columns": self.outlier_column_count,
                "empty_columns": self.empty_column_count,
                "constant_columns": self.constant_column_count,
            },
        }


def load_file(path: str) -> pd.DataFrame:
    """Load a supported table without inferring or changing its schema."""
    source = Path(path)
    if not source.is_file():
        raise DataLoadError("Unable to read dataset.", f"File not found: {path}")

    extension = source.suffix.lower()
    if extension not in SUPPORTED_FORMATS:
        raise DataLoadError(
            "Unable to read dataset.",
            "Unsupported file format. Supported formats: CSV, TSV, XLSX, JSON, Parquet.",
        )

    try:
        if extension == ".csv":
            return pd.read_csv(source)
        if extension == ".tsv":
            return pd.read_csv(source, sep="\t")
        if extension == ".xlsx":
            return pd.read_excel(source)
        if extension == ".json":
            return pd.read_json(source)
        return pd.read_parquet(source)
    except (ImportError, ModuleNotFoundError) as error:
        if extension == ".xlsx":
            raise DataLoadError(
                "Excel support is unavailable.",
                "XLSX support requires openpyxl.",
                "pip install dqlint[excel]",
            ) from error
        if extension == ".parquet":
            raise DataLoadError(
                "Parquet support is unavailable.",
                "Parquet support requires pyarrow.",
                "pip install dqlint[parquet]",
            ) from error
        raise DataLoadError("Unable to read dataset.", str(error)) from error
    except pd.errors.EmptyDataError as error:
        raise DataLoadError(
            "Unable to read dataset.", "File contains no tabular data."
        ) from error
    except Exception as error:
        raise DataLoadError("Unable to read dataset.", str(error)) from error


def _outlier_report(series: pd.Series) -> Optional[OutlierReport]:
    """Calculate IQR evidence for numeric values; booleans are excluded."""
    values = series.dropna()
    if values.empty:
        return None

    q1 = float(values.quantile(0.25))
    q3 = float(values.quantile(0.75))
    iqr = q3 - q1
    lower_bound = q1 - IQR_MULTIPLIER * iqr
    upper_bound = q3 + IQR_MULTIPLIER * iqr
    count = int(((values < lower_bound) | (values > upper_bound)).sum())
    value_count = int(values.shape[0])

    return OutlierReport(
        q1=q1,
        q3=q3,
        iqr=iqr,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        count=count,
        value_count=value_count,
        percentage=(count / value_count * 100) if value_count else 0.0,
    )


def analyze(
    dataframe: pd.DataFrame,
    file_path: str = "<in-memory>",
    file_size_bytes: Optional[int] = None,
) -> DataQualityReport:
    """Inspect a DataFrame using direct, reproducible pandas measurements."""
    row_count, column_count = dataframe.shape
    if file_size_bytes is None and os.path.isfile(file_path):
        file_size_bytes = os.path.getsize(file_path)

    duplicate_row_count = int(dataframe.duplicated().sum())
    duplicate_row_percentage = (
        duplicate_row_count / row_count * 100 if row_count else 0.0
    )

    columns: list[ColumnReport] = []
    for name in dataframe.columns:
        series = dataframe[name]
        missing_count = int(series.isna().sum())
        unique_count = int(series.nunique(dropna=True))
        is_empty = row_count > 0 and missing_count == row_count
        is_constant = unique_count == 1 and not is_empty
        is_numeric = (
            pd.api.types.is_numeric_dtype(series)
            and not pd.api.types.is_bool_dtype(series)
        )
        columns.append(
            ColumnReport(
                name=str(name),
                dtype=str(series.dtype),
                missing_count=missing_count,
                missing_percentage=(missing_count / row_count * 100)
                if row_count
                else 0.0,
                unique_count=unique_count,
                is_empty=is_empty,
                is_constant=is_constant,
                outliers=_outlier_report(series) if is_numeric else None,
            )
        )

    return DataQualityReport(
        file_path=file_path,
        file_name=Path(file_path).name,
        file_size_bytes=file_size_bytes,
        row_count=row_count,
        column_count=column_count,
        duplicate_row_count=duplicate_row_count,
        duplicate_row_percentage=duplicate_row_percentage,
        columns=columns,
    )
