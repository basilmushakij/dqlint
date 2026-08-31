"""Deterministic, factual dataset inspection used by every dqlint output."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

SUPPORTED_FORMATS = {".csv", ".tsv", ".xlsx", ".json", ".parquet"}
IQR_MULTIPLIER = 1.5


class DataLoadError(Exception):
    """A short, user-facing error while reading an input dataset."""

    def __init__(self, title: str, reason: str, hint: Optional[str] = None):
        super().__init__(reason)
        self.title = title
        self.reason = reason
        self.hint = hint


@dataclass
class OutlierReport:
    """Values outside the standard 1.5x IQR bounds for one numeric column."""

    q1: float
    q3: float
    iqr: float
    lower_bound: float
    upper_bound: float
    count: int
    value_count: int
    percentage: float
    method: str = "IQR (Q1 - 1.5x IQR to Q3 + 1.5x IQR)"


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


def load_file(path: str, encoding: Optional[str] = None) -> pd.DataFrame:
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
            return pd.read_csv(source, encoding=encoding)
        if extension == ".tsv":
            return pd.read_csv(source, sep="\t", encoding=encoding)
        if extension == ".xlsx":
            return pd.read_excel(source)
        if extension == ".json":
            return pd.read_json(source, encoding=encoding)
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
    except UnicodeDecodeError as error:
        used = encoding or "utf-8"
        raise DataLoadError(
            "Unable to read dataset.",
            f"File is not valid {used}: {error}",
            "--encoding cp1252 (or another encoding matching the file's actual source)",
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
    duplicate_labels = dataframe.columns[dataframe.columns.duplicated()].unique()
    if len(duplicate_labels):
        raise ValueError(
            "Duplicate column names are not supported: "
            f"{', '.join(str(label) for label in duplicate_labels)}"
        )

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
