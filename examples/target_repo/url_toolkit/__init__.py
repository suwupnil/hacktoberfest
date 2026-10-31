"""url_toolkit: Fast, lightweight URL parsing and validation library."""

from .parser import parse_url
from .validator import is_valid_url

__version__ = "2.4.1"
__all__ = ["parse_url", "is_valid_url"]
