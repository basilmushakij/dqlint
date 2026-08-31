"""dataqual -- a zero-config data quality checker CLI + dashboard."""
from .core import load_file, analyze, DataQualityReport, ColumnReport  # noqa: F401
from .report import build_html, save_html  # noqa: F401

__version__ = "0.1.0"
__all__ = [
    "load_file",
    "analyze",
    "DataQualityReport",
    "ColumnReport",
    "build_html",
    "save_html",
    "__version__",
]
