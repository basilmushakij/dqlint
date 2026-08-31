# dqlint

Quick, factual first look at a dataset before you clean, transform, or model it.

`dqlint` reports observations -- rows, columns, dtypes, missing values, duplicates,
possible outliers, empty/constant columns. It does not determine whether your data
is correct, incorrect, or usable; it does not modify your file. You decide what
the numbers mean.

## Install

```bash
git clone https://github.com/basilmushakij/dqlint.git
cd dqlint
pip install .
```

## Usage

```bash
dqlint data.csv                          # concise summary
dqlint data.csv --full                   # every column, plus duplicate/outlier evidence
dqlint data.csv --json report.json       # also write the report as JSON
```

Optional formats:

```bash
pip install '.[excel]'    # XLSX
pip install '.[parquet]'  # Parquet
```

## Example output

```text
dqlint
------------------------------------

DATASET
  File       sales.csv
  Size       18.4 MiB
  Rows       125,430
  Columns    7

COLUMNS
------------------------------------

  customer_id            int64
  product_name           object
  price                  float64

QUALITY
------------------------------------

  Missing values    2 columns
  Duplicate rows    1,284
  Possible outliers 1 columns
  Empty columns     0
  Constant columns  1

------------------------------------

Use:

  dqlint sales.csv --full

for column-level details.
```

`--full` adds a per-column table (type, missing, unique), duplicate-row evidence,
which columns are empty or constant, and the IQR values behind possible outliers.

## Python API

```python
from dataqual import analyze, load_file

report = analyze(load_file("data.csv"), file_path="data.csv")
report.missing_column_count   # e.g. gate a pipeline on this
report.to_dict()              # same data the --json output writes
```
