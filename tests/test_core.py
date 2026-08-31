import pandas as pd
import pytest

from dataqual.core import analyze


def test_analyze_basic_shape():
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    report = analyze(df, file_path="test.csv")
    assert report.n_rows == 3
    assert report.n_cols == 2
    assert len(report.columns) == 2


def test_missing_values_detected():
    df = pd.DataFrame({"a": [1, None, 3, None]})
    report = analyze(df)
    col = report.columns[0]
    assert col.n_missing == 2
    assert col.pct_missing == 50.0


def test_constant_column_flagged():
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["same", "same", "same"]})
    report = analyze(df)
    b_col = [c for c in report.columns if c.name == "b"][0]
    assert b_col.is_constant is True
    assert any("constant" in i for i in b_col.issues)


def test_duplicate_rows_detected():
    df = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
    report = analyze(df)
    assert report.n_duplicate_rows == 1


def test_outlier_detection():
    df = pd.DataFrame({"a": [10, 11, 12, 13, 11, 10, 500]})
    report = analyze(df)
    col = report.columns[0]
    assert col.n_outliers is not None
    assert col.n_outliers >= 1


def test_empty_dataframe():
    df = pd.DataFrame()
    report = analyze(df)
    assert report.n_rows == 0
    assert report.overall_score == 0.0


def test_high_cardinality_flagged():
    df = pd.DataFrame({"id": list(range(20))})
    report = analyze(df)
    col = report.columns[0]
    assert col.is_high_cardinality is True
