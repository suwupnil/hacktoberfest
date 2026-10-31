"""SSH client connection wrapper using Paramiko."""

import os
from pathlib import Path
from typing import Optional, Tuple
import paramiko


class SSHConnection:
    """Manages an SSH and SFTP session to a remote host."""

    def __init__(
        self,
        host: str,
        port: int = 22,
        user: str = "ubuntu",
        key_path: Optional[str] = None,
        key_data: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 30,
    ):
        self.host = host
        self.port = port
        self.user = user
        self.key_path = os.path.expanduser(key_path) if key_path else None
        self.key_data = key_data
        self.password = password
        self.timeout = timeout
        self.client: Optional[paramiko.SSHClient] = None
        self.sftp: Optional[paramiko.SFTPClient] = None

    def connect(self) -> None:
        """Establish connection to SSH server."""
        if self.client is not None:
            return

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_kwargs = {
            "hostname": self.host,
            "port": self.port,
            "username": self.user,
            "timeout": self.timeout,
        }

        if self.password:
            connect_kwargs["password"] = self.password

        # Attempt to load private key from string or file
        pkey = None
        if self.key_data:
            import io
            for pkey_cls in (paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey):
                try:
                    pkey = pkey_cls.from_private_key(io.StringIO(self.key_data))
                    break
                except Exception:
                    continue

        if not pkey and self.key_path and os.path.exists(self.key_path):
            for pkey_cls in (paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey):
                try:
                    pkey = pkey_cls.from_private_key_file(self.key_path)
                    break
                except Exception:
                    continue

        if pkey:
            connect_kwargs["pkey"] = pkey
        elif self.key_path and os.path.exists(self.key_path):
            connect_kwargs["key_filename"] = self.key_path

        client.connect(**connect_kwargs)
        self.client = client

    def get_sftp(self) -> paramiko.SFTPClient:
        """Retrieve or initialize SFTP client."""
        if self.sftp is None:
            self.connect()
            assert self.client is not None
            self.sftp = self.client.open_sftp()
        return self.sftp

    def execute_command(
        self, command: str, cwd: Optional[str] = None, timeout: int = 120
    ) -> Tuple[int, str, str]:
        """Execute a remote command over SSH channel with timeout."""
        self.connect()
        assert self.client is not None

        if cwd:
            full_command = f"cd {cwd} && {command}"
        else:
            full_command = command

        stdin, stdout, stderr = self.client.exec_command(full_command, timeout=timeout)
        # CRITICAL: Read stdout and stderr completely BEFORE waiting for exit status
        # to prevent deadlock when command produces large outputs exceeding buffer size.
        out_text = stdout.read().decode("utf-8", errors="replace")
        err_text = stderr.read().decode("utf-8", errors="replace")
        exit_code = stdout.channel.recv_exit_status()
        return exit_code, out_text, err_text

    def write_file(self, remote_path: str, content: str) -> None:
        """Write string content to remote file via SFTP or shell cat."""
        try:
            sftp = self.get_sftp()
            # Ensure parent directories exist without cd'ing into nonexistent directories
            remote_dir = os.path.dirname(remote_path)
            if remote_dir:
                self.execute_command(f"mkdir -p '{remote_dir}'", cwd=None)
            with sftp.file(remote_path, "wb") as f:
                f.write(content.encode("utf-8"))
        except Exception:
            # Fallback to shell heredoc if SFTP is restricted
            cmd = f"mkdir -p $(dirname '{remote_path}') && cat << 'EOF_HEREDOC' > '{remote_path}'\n{content}\nEOF_HEREDOC"
            exit_code, out, err = self.execute_command(cmd, cwd=None)
            if exit_code != 0:
                raise RuntimeError(f"Failed to write file {remote_path}: {err}")

    def read_file(self, remote_path: str) -> str:
        """Read content from remote file."""
        try:
            sftp = self.get_sftp()
            with sftp.file(remote_path, "r") as f:
                return f.read().decode("utf-8", errors="replace")
        except Exception:
            exit_code, out, err = self.execute_command(f"cat '{remote_path}'")
            if exit_code != 0:
                raise RuntimeError(f"Failed to read file {remote_path}: {err}")
            return out

    def close(self) -> None:
        """Close connections."""
        if self.sftp:
            try:
                self.sftp.close()
            except Exception:
                pass
            self.sftp = None
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass
            self.client = None
