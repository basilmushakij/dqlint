"""The small, factual dataset inspector behind the dqlint command."""

from .core import ColumnReport, DataQualityReport, OutlierReport, analyze, load_file
from .report import build_html, save_html, save_json

__version__ = "0.2.0"

__all__ = [
    "ColumnReport",
    "DataQualityReport",
    "OutlierReport",
    "analyze",
    "build_html",
    "load_file",
    "save_html",
    "save_json",
    "__version__",
]
