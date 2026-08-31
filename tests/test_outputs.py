import pandas as pd

from dataqual.cli import main
from dataqual.core import analyze
from dataqual.terminal import render, render_column


def _write_csv(path):
    pd.DataFrame(
        {
            "amount": [1, 2, 3, 4, 100],
            "country": ["TH", "TH", None, "TH", "TH"],
            "empty": [None, None, None, None, None],
        }
    ).to_csv(path, index=False)


def test_default_terminal_output_is_concise_and_factual():
    report = analyze(pd.DataFrame({"value": [1, 2, 3]}), file_path="values.csv")
    output = render(report)

    assert "DATASET" in output
    assert "COLUMNS" in output
    assert "QUALITY" in output
    assert "Possible outliers 0 columns" in output
    assert "values.csv --full" in output
    assert "score" not in output.lower()
    assert "good" not in output.lower()


def test_full_terminal_output_contains_missing_duplicate_and_iqr_evidence():
    report = analyze(
        pd.DataFrame(
            {"amount": [1, 2, 3, 4, 100], "flag": ["x", "x", "x", "x", "x"]}
        ),
        file_path="values.csv",
    )
    output = render(report, full=True)

    assert "COLUMN OVERVIEW" in output
    assert "DUPLICATE ROWS" in output
    assert "exact full-row comparison" in output
    assert "POSSIBLE OUTLIERS" in output
    assert "Lower bound: -1" in output
    assert "Constant columns  1" in output
    assert output.isascii()  # must stay printable on a non-UTF-8 stdout


def test_cli_default_and_full_modes(tmp_path, capsys):
    dataset = tmp_path / "sample.csv"
    _write_csv(dataset)

    assert main([str(dataset)]) == 0
    default = capsys.readouterr().out
    assert "DATASET" in default
    assert "COLUMN OVERVIEW" not in default

    assert main([str(dataset), "--full"]) == 0
    full = capsys.readouterr().out
    assert "COLUMN OVERVIEW" in full
    assert "POSSIBLE OUTLIERS" in full


def test_cli_reports_a_clean_error_for_a_missing_file(capsys):
    assert main(["does_not_exist.csv"]) == 1
    error = capsys.readouterr().err

    assert "File not found" in error
    assert "Traceback" not in error


def test_render_column_shows_outlier_detail_for_a_numeric_column():
    report = analyze(pd.DataFrame({"amount": [1, 2, 3, 4, 100]}))
    output = render_column(next(c for c in report.columns if c.name == "amount"))

    assert "Name       amount" in output
    assert "Type       int64" in output
    assert "Lower bound: -1" in output
    assert "Count: 1 / 5 (20.00%)" in output


def test_render_column_marks_outliers_not_applicable_for_non_numeric():
    report = analyze(pd.DataFrame({"label": ["a", "b", "c"]}))
    output = render_column(next(c for c in report.columns if c.name == "label"))

    assert "Not applicable (non-numeric column)." in output


def test_cli_column_flag_shows_one_column(tmp_path, capsys):
    dataset = tmp_path / "sample.csv"
    _write_csv(dataset)

    assert main([str(dataset), "--column", "amount"]) == 0
    output = capsys.readouterr().out
    assert "Name       amount" in output
    assert "COLUMN OVERVIEW" not in output


def test_cli_column_flag_reports_a_clean_error_for_an_unknown_column(tmp_path, capsys):
    dataset = tmp_path / "sample.csv"
    _write_csv(dataset)

    assert main([str(dataset), "--column", "bogus"]) == 1
    error = capsys.readouterr().err

    assert "No column named 'bogus'" in error
    assert "amount" in error
