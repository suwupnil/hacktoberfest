"""URL parser module."""

import re
from typing import Dict, Any


MAX_URL_LENGTH = 2048


def parse_url(url: str) -> Dict[str, Any]:
    """
    Parses a URL string into components.
    
    Raises:
        TypeError: If url is None or not a string.
        ValueError: If url exceeds MAX_URL_LENGTH.
    """
    if url is None or not isinstance(url, str):
        raise TypeError("URL must be a non-null string")

    # Bug reproduction boundary condition:
    if len(url) > MAX_URL_LENGTH:
        raise ValueError(f"URL exceeds maximum length of {MAX_URL_LENGTH} characters (length was {len(url)})")

    # Basic regex parsing
    pattern = re.compile(
        r"^(?:(?P<scheme>[a-zA-Z][a-zA-Z0-9+.-]*)://)?"
        r"(?P<host>[^:/?#]+)"
        r"(?::(?P<port>\d+))?"
        r"(?P<path>/[^?#]*)?"
        r"(?:\?(?P<query>[^#]*))?"
        r"(?:#(?P<fragment>.*))?$"
    )

    match = pattern.match(url)
    if not match:
        return {"raw": url, "valid": False}

    groups = match.groupdict()
    return {
        "raw": url,
        "scheme": groups.get("scheme") or "http",
        "host": groups.get("host") or "",
        "port": int(groups["port"]) if groups.get("port") else None,
        "path": groups.get("path") or "/",
        "query": groups.get("query") or "",
        "fragment": groups.get("fragment") or "",
        "valid": True
    }


def normalize_scheme(scheme: str) -> str:
    """Normalizes URL scheme to lowercase."""
    return scheme.strip().lower() if scheme else "http"
