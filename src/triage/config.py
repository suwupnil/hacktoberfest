"""Configuration and environment settings management."""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Automatically load .env if present
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = ROOT_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()


class Settings:
    """System settings loaded from environment variables."""

    # Main Agent (qwen3.5:9b)
    MAIN_AGENT_URL: str = os.getenv("MAIN_AGENT_URL", "http://localhost:11434/v1")
    MAIN_AGENT_NAME: str = os.getenv("MAIN_AGENT_NAME", "qwen3.5:9b")
    MAIN_AGENT_API_KEY: Optional[str] = os.getenv("MAIN_AGENT_API_KEY", None)

    # Decisions Model (clef-flash)
    DECISIONS_MODEL_URL: str = os.getenv("DECISIONS_MODEL_URL", "http://localhost:11435/v1")
    DECISIONS_MODEL_NAME: str = os.getenv("DECISIONS_MODEL_NAME", "clef-flash")
    DECISIONS_MODEL_API_KEY: Optional[str] = os.getenv("DECISIONS_MODEL_API_KEY", None)

    # SSH Remote Environment Configuration
    SSH_HOST: str = os.getenv("SSH_HOST", "127.0.0.1")
    SSH_PORT: int = int(os.getenv("SSH_PORT", "22"))
    SSH_USER: str = os.getenv("SSH_USER", "ubuntu")
    SSH_KEY_PATH: str = os.getenv("SSH_KEY_PATH", "~/.ssh/id_rsa")
    SSH_KEY: Optional[str] = os.getenv("SSH_KEY", None)
    SSH_PASSWORD: Optional[str] = os.getenv("SSH_PASSWORD", None)
    SSH_REMOTE_WORKDIR: str = os.getenv("SSH_REMOTE_WORKDIR", "/tmp/triage_workspace")
    SSH_TIMEOUT: int = int(os.getenv("SSH_TIMEOUT", "30"))

    # Execution Mode: "ssh" or "local"
    EXECUTION_MODE: str = os.getenv("EXECUTION_MODE", "ssh")

    # Offline / Mock LLM Mode
    FORCE_MOCK_LLM: bool = os.getenv("FORCE_MOCK_LLM", "false").lower() in ("true", "1", "yes")

    @classmethod
    def as_dict(cls) -> dict:
        return {
            "MAIN_AGENT_URL": cls.MAIN_AGENT_URL,
            "MAIN_AGENT_NAME": cls.MAIN_AGENT_NAME,
            "DECISIONS_MODEL_URL": cls.DECISIONS_MODEL_URL,
            "DECISIONS_MODEL_NAME": cls.DECISIONS_MODEL_NAME,
            "SSH_HOST": cls.SSH_HOST,
            "SSH_PORT": cls.SSH_PORT,
            "SSH_USER": cls.SSH_USER,
            "SSH_KEY_PATH": cls.SSH_KEY_PATH,
            "SSH_KEY": "***" if cls.SSH_KEY else None,
            "SSH_REMOTE_WORKDIR": cls.SSH_REMOTE_WORKDIR,
            "EXECUTION_MODE": cls.EXECUTION_MODE,
            "FORCE_MOCK_LLM": cls.FORCE_MOCK_LLM,
        }


settings = Settings()
