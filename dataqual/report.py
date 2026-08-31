"""
dataqual.report
================
Generates a single, self-contained HTML dashboard.

Priorities (in order):
1. Readability -- clean typography, generous spacing, a quick-scan table
   for everything plus a focused detail section only for columns that
   actually have problems (so a clean dataset renders a short, calm page).
2. Light on resources -- no repeating background patterns, no gradients,
   no JS, no webfonts/CDN (system font stack only), minimal DOM per row.
3. Small file size -- whitespace is collapsed before writing to disk.

Icons are real inline SVG (a tiny sprite, reused via <use>), never emoji.
"""
from __future__ import annotations

import html
import re
from datetime import datetime

from .core import DataQualityReport, ColumnReport


def _score_class(score: float) -> str:
    if score >= 85:
        return "ok"
    if score >= 60:
        return "warn"
    return "bad"


_STATUS_LABEL = {"ok": "Good", "warn": "Needs review", "bad": "Poor"}
_ICON_BY_CLASS = {"ok": "i-ok", "warn": "i-warn", "bad": "i-bad"}


def _icon(css_class: str) -> str:
    icon_id = _ICON_BY_CLASS.get(css_class, "i-ok")
    return f'<svg class="ic" viewBox="0 0 10 10"><use href="#{icon_id}"/></svg>'


def _bar(pct: float, cls: str) -> str:
    pct = max(0.0, min(100.0, pct))
    return f'<span class="bar"><span class="bar-fill {cls}" style="width:{pct:.0f}%"></span></span>'


def _fmt_num(n: float) -> str:
    if n == int(n):
        return str(int(n))
    return f"{n:.3g}"


def _table_row(c: ColumnReport) -> str:
    cls = _score_class(c.quality_score)
    return f"""<tr>
<td class="col-name" data-label="Column">{html.escape(c.name)}</td>
<td class="mono dim" data-label="Type">{html.escape(c.dtype)}</td>
<td data-label="Missing">{c.n_missing} <span class="dim">({c.pct_missing}%)</span> {_bar(c.pct_missing, 'bad' if c.pct_missing>30 else ('warn' if c.pct_missing>5 else 'ok'))}</td>
<td data-label="Unique">{c.n_unique} <span class="dim">({c.pct_unique}%)</span></td>
<td class="status {cls}" data-label="Score">{_icon(cls)}<span>{c.quality_score}</span></td>
</tr>"""


def _detail_block(c: ColumnReport) -> str:
    cls = _score_class(c.quality_score)
    issues_html = "".join(f"<li>{html.escape(i)}</li>" for i in c.issues)

    extra = ""
    if c.numeric_stats:
        s = c.numeric_stats
        extra += (
            f'<div class="fact"><span class="dim">Range</span> '
            f'<span class="mono">{_fmt_num(s["min"])} &ndash; {_fmt_num(s["max"])}</span>'
            f'&nbsp;&nbsp;<span class="dim">Mean</span> <span class="mono">{_fmt_num(s["mean"])}</span>'
            f'&nbsp;&nbsp;<span class="dim">Outliers</span> <span class="mono">{c.n_outliers}</span></div>'
        )
    if c.top_values:
        pairs = ", ".join(f"{html.escape(str(v))} ({n})" for v, n in c.top_values[:4])
        extra += f'<div class="fact"><span class="dim">Most common</span> {pairs}</div>'

    return f"""<div class="detail {cls}">
<div class="detail-head"><span class="col-name">{html.escape(c.name)}</span><span class="status {cls}">{_icon(cls)}<span>{c.quality_score}</span></span></div>
{extra}
<ul class="issue-list">{issues_html}</ul>
</div>"""


_SPRITE = """<svg width="0" height="0" style="position:absolute">
<symbol id="i-ok" viewBox="0 0 10 10"><polyline points="1,5.2 4,8.3 9,1.7" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></symbol>
<symbol id="i-warn" viewBox="0 0 10 10"><path d="M5 0.8 L9.4 9.2 L0.6 9.2 Z" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/><rect x="4.35" y="3.4" width="1.3" height="2.8" rx=".5" fill="currentColor"/><circle cx="5" cy="7.4" r=".75" fill="currentColor"/></symbol>
<symbol id="i-bad" viewBox="0 0 10 10"><line x1="1.6" y1="1.6" x2="8.4" y2="8.4" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/><line x1="8.4" y1="1.6" x2="1.6" y2="8.4" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></symbol>
</svg>"""

_CSS = """
:root{--bg:#f7f6f2;--panel:#fff;--ink:#20241f;--dim:#6b6f66;--line:#e4e2da;--ok:#1f7a3d;--ok-bg:#e7f3ea;--warn:#a3660a;--warn-bg:#fbf1e0;--bad:#b23a2e;--bad-bg:#fbe9e7}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{background:var(--bg);color:var(--ink);font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Noto Sans Thai",Arial,sans-serif;-webkit-font-smoothing:antialiased}
.mono{font-family:ui-monospace,"SFMono-Regular",Consolas,"Liberation Mono","Courier New",monospace}
.dim{color:var(--dim);font-size:.92em}
.wrap{max-width:920px;margin:0 auto;padding:36px 24px 56px}
header{margin-bottom:22px}
header h1{margin:0 0 6px;font-size:22px;font-weight:700}
header .file{color:var(--dim);font-size:13.5px;word-break:break-all}
.top{display:flex;align-items:center;gap:22px;flex-wrap:wrap;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:18px 22px;margin:18px 0 20px}
.score-big{display:flex;align-items:baseline;gap:6px}
.score-big .num{font-size:38px;font-weight:700;line-height:1}
.score-big .num.ok{color:var(--ok)}.score-big .num.warn{color:var(--warn)}.score-big .num.bad{color:var(--bad)}
.score-big .of{color:var(--dim);font-size:14px}
.stats{display:flex;gap:26px;flex-wrap:wrap;margin-left:auto}
.stats div{text-align:right}
.stats .v{font-size:16px;font-weight:600}
.stats .l{color:var(--dim);font-size:11.5px;text-transform:uppercase;letter-spacing:.03em}
.panel{border:1px solid var(--line);border-radius:10px;padding:14px 18px;margin:0 0 20px;font-size:14px}
.panel.warn{background:var(--warn-bg);border-color:#eccf98;color:#6b4900}
.panel h2{margin:0 0 8px;font-size:14px;display:flex;align-items:center;gap:7px}
.panel ul{margin:0;padding-left:20px}
.panel li{margin:3px 0}
h2.section{font-size:15px;font-weight:700;margin:26px 0 12px}
table{width:100%;border-collapse:collapse;background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{padding:10px 14px;text-align:left;border-bottom:1px solid var(--line);font-size:13.8px;vertical-align:middle}
th{font-size:11.5px;text-transform:uppercase;letter-spacing:.03em;color:var(--dim);font-weight:600;background:#f2f1ec}
tr:last-child td{border-bottom:none}
tr:nth-child(even) td{background:#fbfaf7}
.col-name{font-weight:600}
.status{display:inline-flex;align-items:center;gap:6px;font-weight:700}
.status.ok{color:var(--ok)}.status.warn{color:var(--warn)}.status.bad{color:var(--bad)}
.ic{width:12px;height:12px;flex:none}
.bar{display:inline-block;width:56px;height:6px;background:#eceae2;border-radius:4px;overflow:hidden;vertical-align:middle;margin-left:6px}
.bar-fill{display:block;height:100%;border-radius:4px}
.bar-fill.ok{background:var(--ok)}.bar-fill.warn{background:var(--warn)}.bar-fill.bad{background:var(--bad)}
.detail{background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--line);border-radius:8px;padding:14px 18px;margin-bottom:12px}
.detail.warn{border-left-color:var(--warn)}
.detail.bad{border-left-color:var(--bad)}
.detail-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.fact{font-size:13.5px;margin:4px 0;color:var(--ink)}
.issue-list{margin:8px 0 0;padding-left:20px;font-size:13.5px}
.issue-list li{margin:3px 0}
footer{margin-top:30px;color:var(--dim);font-size:12px;text-align:center}
@media(max-width:640px){
.top{flex-direction:column;align-items:flex-start}
.stats{margin-left:0}
table,thead,tbody,th,td,tr{display:block}
thead{display:none}
tr{border-bottom:1px solid var(--line);padding:10px 14px}
td{border:none;padding:3px 0;font-size:13.5px}
td:before{content:attr(data-label);display:inline-block;min-width:76px;color:var(--dim);font-size:11px;text-transform:uppercase}
}
"""


def build_html(report: DataQualityReport) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    overall_cls = _score_class(report.overall_score)
    verdict = {
        "ok": "Data quality looks good overall.",
        "warn": "A few things are worth a closer look before cleaning.",
        "bad": "Several columns need attention before this data is usable.",
    }[overall_cls]

    global_issues_block = ""
    if report.global_issues:
        items = "".join(f"<li>{html.escape(i)}</li>" for i in report.global_issues)
        global_issues_block = f'<div class="panel warn"><h2>{_icon("warn")}File-level issues</h2><ul>{items}</ul></div>'

    rows_html = "".join(_table_row(c) for c in report.columns)

    flagged = [c for c in report.columns if c.issues]
    detail_section = ""
    if flagged:
        blocks = "".join(_detail_block(c) for c in sorted(flagged, key=lambda c: c.quality_score))
        detail_section = f'<h2 class="section">Columns that need attention ({len(flagged)})</h2>{blocks}'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Data Quality Report</title>
<style>{_CSS}</style>
</head>
<body>
{_SPRITE}
<div class="wrap">
<header>
<h1>Data quality report</h1>
<div class="file mono">{html.escape(report.file_path)} &middot; generated {generated_at}</div>
</header>

<div class="top">
<div class="score-big"><span class="num {overall_cls}">{report.overall_score}</span><span class="of">/ 100 &nbsp; {verdict}</span></div>
<div class="stats">
<div><div class="v">{report.n_rows:,}</div><div class="l">Rows</div></div>
<div><div class="v">{report.n_cols}</div><div class="l">Columns</div></div>
<div><div class="v">{report.n_duplicate_rows} ({report.pct_duplicate_rows}%)</div><div class="l">Duplicate rows</div></div>
<div><div class="v">{report.memory_mb} MB</div><div class="l">Size</div></div>
</div>
</div>

{global_issues_block}

<h2 class="section">All columns ({report.n_cols})</h2>
<table>
<thead><tr><th>Column</th><th>Type</th><th>Missing</th><th>Unique</th><th>Score</th></tr></thead>
<tbody>{rows_html}</tbody>
</table>

{detail_section}

<footer>dataqual &middot; offline report &middot; no external assets loaded</footer>
</div>
</body>
</html>"""


def _minify(html_text: str) -> str:
    """Collapse whitespace between tags to keep the shipped file small,
    without touching any actual content or CSS rules."""
    lines = [ln.strip() for ln in html_text.splitlines()]
    lines = [ln for ln in lines if ln]
    text = "".join(lines)
    text = re.sub(r">\s+<", "><", text)
    return text


def save_html(report: DataQualityReport, output_path: str) -> str:
    content = _minify(build_html(report))
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    return output_path
