"""Unit tests for URL parser."""

import pytest
from url_toolkit.parser import parse_url, normalize_scheme


def test_parse_simple_url():
    res = parse_url("https://example.com/api/test?q=1#section")
    assert res["valid"] is True
    assert res["scheme"] == "https"
    assert res["host"] == "example.com"
    assert res["path"] == "/api/test"
    assert res["query"] == "q=1"
    assert res["fragment"] == "section"


def test_parse_with_port():
    res = parse_url("http://localhost:8080/metrics")
    assert res["port"] == 8080
    assert res["host"] == "localhost"


def test_parse_none_raises():
    with pytest.raises(TypeError):
        parse_url(None)


def test_normalize_scheme():
    assert normalize_scheme("HTTPS") == "https"
    assert normalize_scheme("  HTTP  ") == "http"
