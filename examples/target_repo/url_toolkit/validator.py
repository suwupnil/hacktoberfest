"""URL validator module."""

from .parser import parse_url


def is_valid_url(url: str) -> bool:
    """Checks if a URL has a valid scheme and host."""
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = parse_url(url)
        if not parsed.get("valid"):
            return False
        scheme = parsed.get("scheme", "")
        host = parsed.get("host", "")
        # Require http/https scheme and a plausible host
        if scheme not in {"http", "https"}:
            return False
        if not host or ("." not in host and host != "localhost"):
            return False
        return True
    except Exception:
        return False
