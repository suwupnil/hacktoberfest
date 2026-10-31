"""Tests for Security Report and Hallucination Verifier."""

from pathlib import Path
from claim_sentry.models import Issue, IssueType, VerdictStatus
from claim_sentry.sandbox import ExecutionSandbox
from claim_sentry.ast_scanner import CodebaseSymbolIndex
from claim_sentry.verifiers.security_verifier import SecurityVerifier


def test_detect_hallucinated_symbol_rce():
    repo_dir = Path(__file__).resolve().parent.parent / "examples" / "target_repo"
    sandbox = ExecutionSandbox(repo_dir)
    symbol_index = CodebaseSymbolIndex(repo_dir)
    verifier = SecurityVerifier(sandbox, symbol_index)

    issue = Issue(
        id="SEC-001",
        number=2,
        title="RCE in parse_url_v2() via shell injection",
        body="Attacker can invoke parse_url_v2() with dangerous command injection payload.",
        type=IssueType.SECURITY
    )

    verified = verifier.verify(issue)

    assert verified.verdict == VerdictStatus.FAKE_SLOP
    assert "parse_url_v2() does not exist" in verified.verdict_headline
    assert "FAKE / AI-GENERATED SLOP" in verified.verdict_badge
    assert "parse_url_v2" in verified.evidence.missing_symbols
    # Should suggest similar real symbol 'parse_url'
    assert any("parse_url" in sym for sym in verified.evidence.similar_symbols)


def test_verify_real_symbol_safe():
    repo_dir = Path(__file__).resolve().parent.parent / "examples" / "target_repo"
    sandbox = ExecutionSandbox(repo_dir)
    symbol_index = CodebaseSymbolIndex(repo_dir)
    verifier = SecurityVerifier(sandbox, symbol_index)

    issue = Issue(
        id="SEC-002",
        number=10,
        title="Audit normalize_scheme() for injection",
        body="Report claiming normalize_scheme() might be unsafe.",
        type=IssueType.SECURITY
    )

    verified = verifier.verify(issue)
    assert verified.verdict == VerdictStatus.VERIFIED_TRUE
    assert "Symbol verified in" in verified.verdict_headline
    assert verified.evidence.exit_code == 0
