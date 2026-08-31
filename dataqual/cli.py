"""Command-line entry point for dqlint."""
from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from . import __version__
from .core import DataLoadError, analyze, load_file
from .terminal import render, render_column


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dqlint",
        description="Quickly inspect factual properties of a dataset.",
    )
    parser.add_argument("file_path", help="CSV, TSV, XLSX, JSON, or Parquet dataset")
    parser.add_argument("--full", action="store_true", help="Show column-level details.")
    parser.add_argument("--columns", action="store_true", help="List column names only, one per line.")
    parser.add_argument("--column", metavar="NAME", help="Show detail for one column only.")
    parser.add_argument("--version", action="version", version=f"dqlint {__version__}")
    return parser


def _print_error(title: str, reason: str, install: Optional[str] = None) -> None:
    print(f"ERROR: {title}", file=sys.stderr)
    print("", file=sys.stderr)
    print("Reason:", file=sys.stderr)
    print(reason, file=sys.stderr)
    if install:
        print("", file=sys.stderr)
        print("Install:", file=sys.stderr)
        print(install, file=sys.stderr)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run dqlint and return a process-style exit code for easy testing."""
    args = _parser().parse_args(argv)

    try:
        dataframe = load_file(args.file_path)
        report = analyze(dataframe, file_path=args.file_path)
    except DataLoadError as error:
        _print_error(error.title, error.reason, error.install)
        return 1

    if args.columns:
        for column in report.columns:
            print(column.name)
        return 0

    if args.column:
        column = next((c for c in report.columns if c.name == args.column), None)
        if column is None:
            available = ", ".join(c.name for c in report.columns)
            _print_error(
                "Unable to find column.",
                f"No column named '{args.column}'. Available columns: {available}",
            )
            return 1
        print(render_column(column))
        return 0

    print(render(report, full=args.full))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
