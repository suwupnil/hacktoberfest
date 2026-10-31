"""Unit tests for URL validator."""

from url_toolkit.validator import is_valid_url


def test_valid_urls():
    assert is_valid_url("https://example.com") is True
    assert is_valid_url("http://google.com/search") is True


def test_invalid_urls():
    assert is_valid_url("") is False
    assert is_valid_url("not_a_url") is False
    assert is_valid_url(None) is False
