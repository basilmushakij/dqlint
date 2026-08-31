import json

import pandas as pd

from dataqual.cli import main
from dataqual.core import analyze
from dataqual.report import build_html, save_json
from dataqual.terminal import render


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


def test_html_escapes_user_controlled_column_names():
    report = analyze(pd.DataFrame({"<script>alert(1)</script>": [1, 2]}))
    output = build_html(report)

    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in output
    assert "<script>alert(1)</script>" not in output
    assert "score" not in output.lower()


def test_json_serializes_the_canonical_report(tmp_path):
    path = tmp_path / "report.json"
    report = analyze(pd.DataFrame({"value": [1, None]}), file_path="values.csv")

    save_json(report, str(path))
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["dataset"]["rows"] == 2
    assert data["columns"][0]["missing_count"] == 1
    assert data["quality"]["missing_columns"] == 1


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


def test_cli_writes_json_and_html_without_overwriting_input(tmp_path, capsys):
    dataset = tmp_path / "sample.csv"
    json_path = tmp_path / "report.json"
    html_path = tmp_path / "report.html"
    _write_csv(dataset)

    assert main([str(dataset), "--json", str(json_path), "--html", str(html_path)]) == 0
    capsys.readouterr()
    assert json.loads(json_path.read_text(encoding="utf-8"))["dataset"]["rows"] == 5
    assert "dqlint" in html_path.read_text(encoding="utf-8")

    assert main([str(dataset), "--json", str(dataset)]) == 1
    error = capsys.readouterr().err
    assert "must not overwrite the input dataset" in error
