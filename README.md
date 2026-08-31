# dataqual

A **data quality checker** you run before you start cleaning data. Point it
at a file and get back a straight-to-the-point summary: what's missing,
what's duplicated, what looks like an outlier, and what's not worth keeping
as a column at all -- in the terminal, or as a shareable HTML dashboard.

No more re-writing `df.isna().sum()`, `df.describe()`, and a duplicate-row
check every time a new file lands on your desk. One command does it.

## What it looks like

```
$ dataqual users.csv

users.csv   500 rows · 10 cols · 0.165 MB
6 duplicate rows (1.2%)
Score  92.4/100  – looks good

Issues found (4 of 10 columns)
  ●  referral_source   64.0  60.0% missing (high)
  ●  internal_flag     70.0  constant value, no variation
  ●  email             96.9  5.2% missing
  ●  monthly_spend     98.7  outliers detected (~2.6%)

6 clean: user_id, signup_date, country_code, plan, age, is_active

Run with --full to see stats for every column.
```

Only flags what's actually worth looking at -- if a dataset is clean, the
output is short. Add `--html report.html` for a dashboard you can open in a
browser or send to someone else.

## Install

Requires Python 3.9+.

```bash
git clone https://github.com/basilmushakij/dqlint.git
cd dqlint
pip install .
```

For local development, install in editable mode instead:

```bash
pip install -e .
```

This gives you the `dataqual` command anywhere on your machine.

## Usage

```bash
# check a file (the "check" subcommand is optional -- this is the shortcut)
dataqual data.csv

# same thing, spelled out
dataqual check data.csv

# see stats for every column, not just the flagged ones
dataqual data.csv --full

# also generate an HTML dashboard
dataqual data.csv --html report.html

# generate the dashboard and open it in your browser
dataqual data.csv --html report.html --open

# just generate the HTML, skip the terminal output (good for scripts/CI)
dataqual data.csv --html report.html --quiet
```

Supported file types: `.csv` `.tsv` `.xlsx` `.xls` `.json` `.parquet`

### Using it in CI/CD

`dataqual check` exits with:
- `0` -- overall score >= 60
- `2` -- overall score < 60 (data has real problems)
- `1` -- an error occurred (file not found / couldn't be read)

That means you can gate a pipeline on it:

```yaml
- name: Check data quality
  run: dataqual data/latest.csv --quiet
```

## What it checks

Per column:
- Missing values -- count and percentage
- Unique values and percent-unique (high percent-unique often means an ID-like column, but that's left for you to judge from the number)
- Columns that never change (constant value, zero information)
- Outliers, using the IQR method, for numeric columns
- Basic stats (min, max, mean, median, std) for numeric columns
- Most common values, for text/categorical columns

At the file level:
- Fully duplicated rows
- Memory footprint
- An overall score (0-100), averaged across columns and penalized for
  duplicate rows

## Using it as a Python library

```python
from dataqual import load_file, analyze, save_html

df = load_file("data.csv")
report = analyze(df, file_path="data.csv")

print(report.overall_score)
for col in report.columns:
    print(col.name, col.quality_score, col.issues)

save_html(report, "report.html")
```

## Project structure

```
dataqual/
├── dataqual/
│   ├── __init__.py
│   ├── core.py        # the analysis logic
│   ├── terminal.py     # terminal output (rich)
│   ├── report.py       # HTML dashboard generator
│   └── cli.py          # command-line interface (click)
├── examples/
│   └── sample_sales.csv
├── tests/
│   └── test_core.py
├── pyproject.toml
└── README.md
```

## Ideas for later

- [ ] Schema validation against an expected type/range definition
- [ ] Compare two files (before/after cleaning)
- [ ] JSON export for piping into other tools
- [ ] Chunked/streaming reads for very large files

## License

MIT
