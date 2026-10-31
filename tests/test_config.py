"""Tests for configuration and environment variables."""

import os
from triage.config import Settings, settings


def test_settings_loaded():
    assert settings.MAIN_AGENT_NAME is not None
    assert settings.DECISIONS_MODEL_NAME is not None
    assert settings.SSH_HOST is not None
    assert settings.SSH_PORT == 22
    assert settings.SSH_USER is not None
    assert settings.SSH_KEY_PATH is not None


def test_settings_as_dict():
    d = settings.as_dict()
    assert "MAIN_AGENT_URL" in d
    assert "DECISIONS_MODEL_URL" in d
    assert "SSH_HOST" in d
    assert "SSH_KEY_PATH" in d
    assert "EXECUTION_MODE" in d
