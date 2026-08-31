"""
dataqual.terminal
==================
Renders a DataQualityReport in the terminal.

Design: most people running this don't want to read a stats table for
every column on every run -- they want to know, at a glance, whether the
file is fine and what to look at if it isn't. So the default view is a
short, linter-style summary (score, then only the flagged columns, one
line each). Pass --full for a complete per-column table.
"""
from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich import box

from .core import DataQualityReport


def _score_color(score: float) -> str:
    if score >= 85:
        return "green"
    if score >= 60:
        return "yellow"
    return "red"


def _verdict(score: float) -> str:
    if score >= 85:
        return "looks good"
    if score >= 60:
        return "a few things worth reviewing"
    return "needs attention before cleaning"


def _mark(score: float) -> Text:
    # A colored bullet, not a pass/fail label -- everything in the "issues"
    # list has at least one issue, so labeling some of them "OK" would be
    # contradictory. Color alone carries how serious it is.
    return Text("\u25cf", style=f"bold {_score_color(score)}")


def render(report: DataQualityReport, console: Console | None = None, full: bool = False) -> None:
    console = console or Console()
    color = _score_color(report.overall_score)

    console.print()
    header = Text()
    header.append(report.file_path, style="bold")
    header.append(f"   {report.n_rows:,} rows \u00b7 {report.n_cols} cols \u00b7 {report.memory_mb} MB", style="dim")
    console.print(header)

    if report.n_duplicate_rows:
        console.print(Text(
            f"{report.n_duplicate_rows} duplicate rows ({report.pct_duplicate_rows}%)", style="yellow"
        ))

    score_line = Text()
    score_line.append("Score  ")
    score_line.append(f"{report.overall_score}/100", style=f"bold {color}")
    score_line.append(f"  \u2013 {_verdict(report.overall_score)}", style="dim")
    console.print(score_line)
    console.print()

    for issue in report.global_issues:
        console.print(Text(f"  ! {issue}", style="yellow"))
    if report.global_issues:
        console.print()

    flagged = [c for c in report.columns if c.issues]
    clean = [c for c in report.columns if not c.issues]

    if flagged:
        console.print(Text(f"Issues found ({len(flagged)} of {report.n_cols} columns)", style="bold"))
        name_width = min(max((len(c.name) for c in report.columns), default=10), 28)
        for c in sorted(flagged, key=lambda c: c.quality_score):
            line = Text("  ")
            line.append(_mark(c.quality_score))
            line.append("  ")
            line.append(f"{c.name:<{name_width}}", style="bold")
            line.append(f"  {c.quality_score:>5.1f}  ", style=_score_color(c.quality_score))
            line.append(" \u00b7 ".join(c.issues), style="dim")
            console.print(line)
        console.print()
    else:
        console.print(Text("All columns look clean.", style="bold green"))
        console.print()

    if flagged and clean:
        console.print(Text(f"{len(clean)} clean: {', '.join(c.name for c in clean)}", style="dim"))
        console.print()

    if not full:
        console.print(Text("Run with --full to see stats for every column.", style="dim italic"))
        console.print()
        return

    table = Table(title="All columns", box=box.SIMPLE_HEAVY, show_lines=False)
    table.add_column("Column", style="bold")
    table.add_column("Type")
    table.add_column("Missing", justify="right")
    table.add_column("Unique", justify="right")
    table.add_column("Outliers", justify="right")
    table.add_column("Score", justify="right")

    for c in report.columns:
        sc = _score_color(c.quality_score)
        table.add_row(
            c.name,
            c.dtype,
            f"{c.n_missing} ({c.pct_missing}%)",
            f"{c.n_unique} ({c.pct_unique}%)",
            "-" if c.n_outliers is None else str(c.n_outliers),
            Text(f"{c.quality_score}", style=f"bold {sc}"),
        )
    console.print(table)
    console.print()
