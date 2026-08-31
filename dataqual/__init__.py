"""The small, factual dataset inspector behind the dqlint command."""

from .core import ColumnReport, DataQualityReport, OutlierReport, analyze, load_file
from .report import save_json

__version__ = "0.2.0"

__all__ = [
    "ColumnReport",
    "DataQualityReport",
    "OutlierReport",
    "analyze",
    "load_file",
    "save_json",
    "__version__",
]
