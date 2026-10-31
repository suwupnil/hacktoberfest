"""Command runners for local and SSH execution environments."""

from abc import ABC, abstractmethod
import os
from pathlib import Path
import subprocess
import time
from typing import Dict, Optional
from triage.config import settings
from triage.models import CommandResult
from triage.ssh_client import SSHConnection


class CommandRunner(ABC):
    """Abstract command runner interface."""

    @abstractmethod
    def run(self, command: str, cwd: Optional[str] = None, timeout: int = 120) -> CommandResult:
        """Run a shell command."""
        pass

    @abstractmethod
    def write_file(self, path: str, content: str) -> None:
        """Write content to a file."""
        pass

    @abstractmethod
    def read_file(self, path: str) -> str:
        """Read content from a file."""
        pass

    @abstractmethod
    def ensure_dir(self, path: str) -> None:
        """Ensure a directory exists."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources / connections."""
        pass


class SSHRunner(CommandRunner):
    """Executes commands on a remote machine over SSH."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        key_path: Optional[str] = None,
        password: Optional[str] = None,
        workdir: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.host = host or settings.SSH_HOST
        self.port = port or settings.SSH_PORT
        self.user = user or settings.SSH_USER
        self.key_path = key_path or settings.SSH_KEY_PATH
        self.key_data = getattr(settings, "SSH_KEY", None)
        self.password = password or settings.SSH_PASSWORD
        self.workdir = workdir or settings.SSH_REMOTE_WORKDIR
        self.timeout = timeout or settings.SSH_TIMEOUT
        self.ssh = SSHConnection(
            host=self.host,
            port=self.port,
            user=self.user,
            key_path=self.key_path,
            key_data=self.key_data,
            password=self.password,
            timeout=self.timeout,
        )

    def run(self, command: str, cwd: Optional[str] = None, timeout: int = 120) -> CommandResult:
        start_time = time.time()
        effective_cwd = cwd or self.workdir
        exit_code, stdout, stderr = self.ssh.execute_command(command, cwd=effective_cwd, timeout=timeout)
        duration = time.time() - start_time
        return CommandResult(
            command=command,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration=round(duration, 3),
        )

    def write_file(self, path: str, content: str) -> None:
        remote_path = path
        if not path.startswith("/") and self.workdir:
            remote_path = f"{self.workdir}/{path}"
        self.ssh.write_file(remote_path, content)

    def read_file(self, path: str) -> str:
        remote_path = path
        if not path.startswith("/") and self.workdir:
            remote_path = f"{self.workdir}/{path}"
        return self.ssh.read_file(remote_path)

    def ensure_dir(self, path: str) -> None:
        # Create directory with cwd=None so it does not fail if self.workdir does not exist yet
        self.ssh.execute_command(f"mkdir -p '{path}'", cwd=None)

    def cleanup(self) -> None:
        self.ssh.close()


class LocalRunner(CommandRunner):
    """Executes commands locally on the current machine (fallback and local development)."""

    def __init__(self, workdir: Optional[str] = None):
        self.workdir = Path(workdir or "/tmp/triage_workspace").expanduser().resolve()
        self.workdir.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, path: str) -> Path:
        p = Path(path)
        if p.is_absolute():
            return p
        return self.workdir / p

    def run(self, command: str, cwd: Optional[str] = None, timeout: int = 120) -> CommandResult:
        start_time = time.time()
        target_dir = Path(cwd) if cwd else self.workdir
        target_dir.mkdir(parents=True, exist_ok=True)

        try:
            res = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                cwd=str(target_dir),
                timeout=timeout,
            )
            duration = time.time() - start_time
            return CommandResult(
                command=command,
                exit_code=res.returncode,
                stdout=res.stdout,
                stderr=res.stderr,
                duration=round(duration, 3),
            )
        except subprocess.TimeoutExpired:
            return CommandResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=f"Command timed out after {timeout} seconds",
                duration=round(time.time() - start_time, 3),
            )
        except Exception as e:
            return CommandResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                duration=round(time.time() - start_time, 3),
            )

    def write_file(self, path: str, content: str) -> None:
        resolved = self._resolve_path(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")

    def read_file(self, path: str) -> str:
        resolved = self._resolve_path(path)
        return resolved.read_text(encoding="utf-8")

    def ensure_dir(self, path: str) -> None:
        resolved = self._resolve_path(path)
        resolved.mkdir(parents=True, exist_ok=True)

    def cleanup(self) -> None:
        pass


class MockRunner(CommandRunner):
    """Mock runner for testing and simulated environments."""

    def __init__(self):
        self.files: Dict[str, str] = {}
        self.commands_run: list = []
        self.custom_responses: Dict[str, CommandResult] = {}
        self.default_exit_code = 0

    def set_response(self, command_prefix: str, result: CommandResult) -> None:
        self.custom_responses[command_prefix] = result

    def run(self, command: str, cwd: Optional[str] = None, timeout: int = 120) -> CommandResult:
        self.commands_run.append({"command": command, "cwd": cwd})

        for prefix, res in self.custom_responses.items():
            if prefix in command:
                return res

        return CommandResult(
            command=command,
            exit_code=self.default_exit_code,
            stdout="[mock execution stdout]",
            stderr="",
            duration=0.01,
        )

    def write_file(self, path: str, content: str) -> None:
        self.files[path] = content

    def read_file(self, path: str) -> str:
        return self.files.get(path, "")

    def ensure_dir(self, path: str) -> None:
        pass

    def cleanup(self) -> None:
        pass


def create_runner(mode: Optional[str] = None) -> CommandRunner:
    """Create a runner based on mode or environment setting."""
    selected_mode = (mode or settings.EXECUTION_MODE).lower().strip()
    if selected_mode == "local":
        return LocalRunner()
    elif selected_mode == "mock":
        return MockRunner()
    else:
        return SSHRunner()
