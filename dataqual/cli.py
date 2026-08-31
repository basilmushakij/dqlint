"""
dataqual.cli
============
Command-line entry point.

Usage:
    dataqual data.csv                          # shortcut for `check`
    dataqual check data.csv
    dataqual check data.csv --full
    dataqual check data.csv --html report.html
    dataqual check data.csv --html report.html --open
"""
from __future__ import annotations

import sys
import webbrowser

import click
from rich.console import Console

from . import __version__
from .core import load_file, analyze
from .terminal import render
from .report import save_html


class DefaultGroup(click.Group):
    """Lets `dataqual <file>` work as a shortcut for `dataqual check <file>`,
    so you don't have to type the subcommand on every run."""

    default_command = "check"

    def resolve_command(self, ctx, args):
        try:
            return super().resolve_command(ctx, args)
        except click.UsageError:
            return super().resolve_command(ctx, [self.default_command, *args])


@click.group(cls=DefaultGroup)
@click.version_option(version=__version__, prog_name="dataqual")
def main() -> None:
    """dataqual -- a data quality checker for CSV / Excel / JSON / Parquet files.

    Quick start:

        dataqual data.csv
    """


@main.command()
@click.argument("file_path", type=str)
@click.option("--html", "html_path", type=str, default=None,
              help="Save an HTML dashboard to this path.")
@click.option("--open", "open_browser", is_flag=True,
              help="Open the HTML dashboard in your browser once it's generated.")
@click.option("--full", "full", is_flag=True,
              help="Show stats for every column, not just the flagged ones.")
@click.option("--quiet", "-q", is_flag=True,
              help="Don't print to the terminal (useful with --html, or in scripts).")
def check(file_path: str, html_path: str | None, open_browser: bool, full: bool, quiet: bool) -> None:
    """Check the data quality of FILE_PATH."""
    console = Console()
    try:
        df = load_file(file_path)
        report = analyze(df, file_path=file_path)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)

    if not quiet:
        render(report, console=console, full=full)

    if html_path:
        save_html(report, html_path)
        console.print(f"[bold green]Saved[/bold green] HTML dashboard to: [underline]{html_path}[/underline]")
        if open_browser:
            webbrowser.open(f"file://{html_path}")

    # Exit code reflects data quality, so this can gate a CI pipeline.
    sys.exit(0 if report.overall_score >= 60 else 2)


if __name__ == "__main__":
    main()
