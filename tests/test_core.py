import math

import pandas as pd
import pytest

from dataqual.core import analyze


def column(report, name):
    return next(item for item in report.columns if item.name == name)


def test_dataset_shape_and_file_size_are_reported():
    report = analyze(
        pd.DataFrame({"a": [1, 2], "b": ["x", "y"]}),
        file_path="example.csv",
        file_size_bytes=1234,
    )

    assert report.row_count == 2
    assert report.column_count == 2
    assert report.file_name == "example.csv"
    assert report.file_size_bytes == 1234


def test_missing_values_are_counted_without_a_threshold():
    report = analyze(pd.DataFrame({"a": [1, None, 3, None], "b": [1, 2, 3, 4]}))
    a = column(report, "a")

    assert a.missing_count == 2
    assert a.missing_percentage == 50.0
    assert report.missing_column_count == 1


def test_all_null_column_is_empty_not_constant():
    report = analyze(pd.DataFrame({"empty": [None, None, None]}))
    empty = column(report, "empty")

    assert empty.is_empty is True
    assert empty.is_constant is False
    assert empty.unique_count == 0
    assert report.empty_column_count == 1
    assert report.constant_column_count == 0


def test_constant_column_with_nulls_has_one_distinct_non_null_value():
    report = analyze(pd.DataFrame({"country": ["TH", None, "TH", "TH"]}))
    country = column(report, "country")

    assert country.is_empty is False
    assert country.is_constant is True
    assert country.unique_count == 1


def test_non_constant_column_is_not_constant():
    report = analyze(pd.DataFrame({"values": [1, 2, 3]}))

    assert column(report, "values").is_constant is False


def test_exact_duplicate_rows_and_percentage_are_reported():
    report = analyze(pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]}))

    assert report.duplicate_row_count == 1
    assert report.duplicate_row_percentage == pytest.approx(100 / 3)


def test_iqr_outlier_evidence_is_reproducible():
    report = analyze(pd.DataFrame({"amount": [1, 2, 3, 4, 100]}))
    outliers = column(report, "amount").outliers

    assert outliers is not None
    assert outliers.q1 == 2.0
    assert outliers.q3 == 4.0
    assert outliers.iqr == 2.0
    assert outliers.lower_bound == -1.0
    assert outliers.upper_bound == 7.0
    assert outliers.count == 1
    assert outliers.percentage == 20.0
    assert report.outlier_column_count == 1


def test_numeric_column_with_no_outliers_keeps_iqr_evidence():
    report = analyze(pd.DataFrame({"amount": [1, 2, 3, 4]}))
    outliers = column(report, "amount").outliers

    assert outliers is not None
    assert outliers.count == 0
    assert outliers.percentage == 0.0


def test_actual_pandas_dtypes_are_reported_without_inference():
    dataframe = pd.DataFrame(
        {
            "integer": pd.Series([1, 2], dtype="int64"),
            "floating": pd.Series([1.0, 2.0], dtype="float64"),
            "text": pd.Series(["1", "2"], dtype="object"),
            "flag": pd.Series([True, False], dtype="bool"),
            "timestamp": pd.to_datetime(["2026-01-01", "2026-01-02"]),
        }
    )
    report = analyze(dataframe)

    assert column(report, "integer").dtype == "int64"
    assert column(report, "floating").dtype == "float64"
    assert column(report, "text").dtype == "object"
    assert column(report, "flag").dtype == "bool"
    assert column(report, "timestamp").dtype == "datetime64[ns]"
    assert column(report, "text").outliers is None


def test_empty_dataframe_has_no_empty_or_constant_columns():
    report = analyze(pd.DataFrame())

    assert report.row_count == 0
    assert report.column_count == 0
    assert report.empty_column_count == 0
    assert report.constant_column_count == 0
    assert math.isclose(report.duplicate_row_percentage, 0.0)


def test_report_json_structure_contains_only_factual_measurements():
    report = analyze(pd.DataFrame({"value": [1, None]}), file_path="values.csv")
    data = report.to_dict()

    assert data["dataset"]["file"] == "values.csv"
    assert data["quality"]["missing_columns"] == 1
    assert data["columns"][0]["missing_count"] == 1
    assert "score" not in str(data).lower()


def test_duplicate_column_names_raise_a_clear_error():
    dataframe = pd.DataFrame([[1, 2, 3]], columns=["a", "a", "b"])

    with pytest.raises(ValueError, match="Duplicate column names"):
        analyze(dataframe)


def test_outlier_method_text_is_ascii_safe():
    report = analyze(pd.DataFrame({"amount": [1, 2, 3, 4, 100]}))
    outliers = column(report, "amount").outliers

    assert outliers.method.isascii()
