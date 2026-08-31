"""Command-line entry point for dqlint."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from . import __version__
from .core import DataLoadError, analyze, load_file
from .report import save_html, save_json
from .terminal import render


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dqlint",
        description="Quickly inspect factual properties of a dataset.",
    )
    parser.add_argument("file_path", help="CSV, TSV, XLSX, JSON, or Parquet dataset")
    parser.add_argument("--full", action="store_true", help="Show column-level details.")
    parser.add_argument("--html", metavar="PATH", help="Write a self-contained HTML report.")
    parser.add_argument("--json", metavar="PATH", help="Write the report as JSON.")
    parser.add_argument("--version", action="version", version=f"dqlint {__version__}")
    return parser


def _check_output_paths(input_path: str, outputs: Sequence[Optional[str]]) -> Optional[str]:
    source = Path(input_path).resolve()
    paths = [Path(path).resolve() for path in outputs if path]
    if source in paths:
        return "An output path must not overwrite the input dataset."
    if len(paths) != len(set(paths)):
        return "HTML and JSON output paths must be different."
    return None


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
    output_error = _check_output_paths(args.file_path, (args.html, args.json))
    if output_error:
        _print_error("Unable to write report.", output_error)
        return 1

    try:
        dataframe = load_file(args.file_path)
        report = analyze(dataframe, file_path=args.file_path)
        if args.html:
            save_html(report, args.html)
        if args.json:
            save_json(report, args.json)
    except DataLoadError as error:
        _print_error(error.title, error.reason, error.install)
        return 1
    except OSError as error:
        _print_error("Unable to write report.", str(error))
        return 1

    print(render(report, full=args.full))
    if args.html:
        print(f"\nHTML report written: {args.html}")
    if args.json:
        print(f"JSON report written: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
