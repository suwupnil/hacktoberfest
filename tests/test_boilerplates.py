"""Tests for boilerplate environments catalog and registration."""

from triage.boilerplates import (
    BOILERPLATE_CATALOG,
    get_boilerplate,
    list_boilerplates,
    register_boilerplate,
    get_catalog_summary,
    detect_heuristic_boilerplate,
)
from triage.models import BoilerplateEnvironment


def test_catalog_contains_popular_environments():
    expected_envs = ["cpp-boost", "cpp-cmake", "python-pytest", "node-npm", "rust-cargo", "go-test"]
    for env_id in expected_envs:
        bp = get_boilerplate(env_id)
        assert bp is not None, f"Environment {env_id} must exist in catalog"
        assert len(bp.setup_commands) > 0
        assert bp.test_runner_command != ""


def test_list_boilerplates():
    bps = list_boilerplates()
    assert len(bps) >= 6
    ids = [b.id for b in bps]
    assert "cpp-boost" in ids
    assert "python-pytest" in ids


def test_register_custom_boilerplate():
    custom = BoilerplateEnvironment(
        id="custom-haskell-cabal",
        name="Haskell Cabal Environment",
        description="Environment for Haskell projects",
        languages=["haskell", "hs"],
        setup_commands=["cabal update"],
        test_runner_command="cabal test",
    )
    register_boilerplate(custom)
    fetched = get_boilerplate("custom-haskell-cabal")
    assert fetched is not None
    assert fetched.name == "Haskell Cabal Environment"


def test_catalog_summary():
    summary = get_catalog_summary()
    assert "cpp-boost" in summary
    assert "python-pytest" in summary


def test_detect_heuristic():
    assert detect_heuristic_boilerplate("https://github.com/boostorg/boost", "odd hex decoding") == "cpp-boost"
    assert detect_heuristic_boilerplate("https://github.com/psf/requests", "http header parsing") == "python-pytest"
    assert detect_heuristic_boilerplate("https://github.com/expressjs/express", "router middleware") == "node-npm"
