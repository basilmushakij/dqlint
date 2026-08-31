# dqlint

Quick, factual first look at a dataset before you clean, transform, or model it.

## Install

```bash
git clone https://github.com/basilmushakij/dqlint.git
cd dqlint
pip install .
```

## Usage

```bash
dqlint data.csv
dqlint data.csv --full
dqlint data.csv --html report.html
dqlint data.csv --json report.json
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

`--full` adds per-column missing/unique counts, duplicate-row evidence, and the IQR values behind possible outliers.

## Python API

```python
from dataqual import analyze, load_file

report = analyze(load_file("data.csv"), file_path="data.csv")
report.missing_column_count   # e.g. gate a pipeline on this
report.to_dict()              # same data the --json output writes
```
