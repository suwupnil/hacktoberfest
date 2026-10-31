"""Tests for Locked-Down Sandbox Execution Engine."""

import os
from pathlib import Path
import pytest
from claim_sentry.sandbox import ExecutionSandbox, get_sanitized_env, count_exposed_secrets


def test_secrets_stripped_from_environment():
    # Inject fake sensitive environment variables
    os.environ["GITHUB_TOKEN"] = "ghp_super_secret_token_12345"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "aws_secret_key_9999"
    os.environ["DATABASE_PASSWORD"] = "ultra_secure_db_pass"
    os.environ["OPENAI_API_KEY"] = "sk-fake-openai-key"

    sanitized = get_sanitized_env()

    # Assert none of the sensitive keys exist in sanitized environment
    assert "GITHUB_TOKEN" not in sanitized
    assert "AWS_SECRET_ACCESS_KEY" not in sanitized
    assert "DATABASE_PASSWORD" not in sanitized
    assert "OPENAI_API_KEY" not in sanitized

    # Verify secret counter is 0
    assert count_exposed_secrets(sanitized) == 0


def test_network_blocked_in_sandbox(tmp_path):
    sandbox = ExecutionSandbox(tmp_path)
    
    # Python script that attempts to open a network socket
    network_script = """
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("8.8.8.8", 53))
print("CONNECTED_FAIL")
"""
    result = sandbox.run_script(network_script)
    assert result["exit_code"] != 0
    assert "SandboxNetworkBlocked" in result["stderr"] or "Network access is strictly BLOCKED" in result["stderr"]
    assert result["network_bytes_sent"] == 0
    assert result["secrets_exposed_count"] == 0


def test_sandbox_timeout_limit(tmp_path):
    sandbox = ExecutionSandbox(tmp_path, timeout_seconds=1.5)
    infinite_loop_script = """
import time
while True:
    time.sleep(0.1)
"""
    result = sandbox.run_script(infinite_loop_script)
    assert result["exit_code"] == 124
    assert "TIMEOUT" in result["stderr"]
