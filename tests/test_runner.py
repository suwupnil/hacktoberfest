"""Tests for command runners (Local, Mock, and SSH)."""

import os
from unittest.mock import MagicMock, patch
from triage.models import CommandResult
from triage.runner import LocalRunner, MockRunner, SSHRunner, create_runner


def test_local_runner_basic_commands(tmp_path):
    runner = LocalRunner(workdir=str(tmp_path))
    res = runner.run("echo 'Hello World'")
    assert res.exit_code == 0
    assert "Hello World" in res.stdout
    assert res.duration >= 0.0


def test_local_runner_file_io(tmp_path):
    runner = LocalRunner(workdir=str(tmp_path))
    test_file = "subdir/test.txt"
    content = "Triage content payload"
    runner.write_file(test_file, content)
    read_back = runner.read_file(test_file)
    assert read_back == content


def test_local_runner_command_failure(tmp_path):
    runner = LocalRunner(workdir=str(tmp_path))
    res = runner.run("false")
    assert res.exit_code != 0


def test_mock_runner():
    runner = MockRunner()
    runner.set_response("bash reproduce.sh", CommandResult(
        command="bash reproduce.sh",
        exit_code=42,
        stdout="Reproduction script executed",
        stderr="Caught expected error",
    ))
    res = runner.run("bash reproduce.sh")
    assert res.exit_code == 42
    assert "Caught expected error" in res.stderr


@patch("paramiko.SSHClient")
def test_ssh_runner_mocked(mock_ssh_client_cls):
    mock_client = MagicMock()
    mock_channel = MagicMock()
    mock_channel.recv_exit_status.return_value = 0

    mock_stdout = MagicMock()
    mock_stdout.channel = mock_channel
    mock_stdout.read.return_value = b"remote output ok"

    mock_stderr = MagicMock()
    mock_stderr.read.return_value = b""

    mock_client.exec_command.return_value = (MagicMock(), mock_stdout, mock_stderr)
    mock_ssh_client_cls.return_value = mock_client

    runner = SSHRunner(host="10.0.0.1", user="testuser")
    res = runner.run("uptime")
    assert res.exit_code == 0
    assert res.stdout == "remote output ok"
    runner.cleanup()


@patch("paramiko.SSHClient")
def test_ssh_client_reads_output_before_exit_status_to_prevent_deadlock(mock_ssh_client_cls):
    """Verify that stdout/stderr are drained BEFORE calling channel.recv_exit_status() to prevent pipe deadlock."""
    call_order = []

    mock_client = MagicMock()
    mock_channel = MagicMock()

    def recv_exit_status():
        call_order.append("recv_exit_status")
        return 0

    def read_stdout():
        call_order.append("read_stdout")
        return b"large buffer drained"

    def read_stderr():
        call_order.append("read_stderr")
        return b""

    mock_channel.recv_exit_status.side_effect = recv_exit_status
    mock_stdout = MagicMock()
    mock_stdout.channel = mock_channel
    mock_stdout.read.side_effect = read_stdout

    mock_stderr = MagicMock()
    mock_stderr.read.side_effect = read_stderr

    mock_client.exec_command.return_value = (MagicMock(), mock_stdout, mock_stderr)
    mock_ssh_client_cls.return_value = mock_client

    runner = SSHRunner(host="10.0.0.1", user="testuser")
    res = runner.run("cat large_file.log")

    assert res.exit_code == 0
    assert "read_stdout" in call_order
    assert "recv_exit_status" in call_order
    # Ensure stdout was read BEFORE recv_exit_status was called
    assert call_order.index("read_stdout") < call_order.index("recv_exit_status")
    runner.cleanup()


@patch("paramiko.SSHClient")
def test_ssh_runner_ensure_dir_avoids_workdir_trap(mock_ssh_client_cls):
    """Verify that ensure_dir does not try to cd into a nonexistent directory."""
    mock_client = MagicMock()
    mock_channel = MagicMock()
    mock_channel.recv_exit_status.return_value = 0

    mock_stdout = MagicMock()
    mock_stdout.channel = mock_channel
    mock_stdout.read.return_value = b""
    mock_stderr = MagicMock()
    mock_stderr.read.return_value = b""

    mock_client.exec_command.return_value = (MagicMock(), mock_stdout, mock_stderr)
    mock_ssh_client_cls.return_value = mock_client

    runner = SSHRunner(host="10.0.0.1", user="testuser", workdir="/tmp/nested/workdir")
    runner.ensure_dir("/tmp/nested/workdir/job123")

    # Inspect the exact command sent to exec_command
    executed_cmd = mock_client.exec_command.call_args[0][0]
    # It must NOT be 'cd /tmp/nested/workdir && mkdir -p ...'
    assert executed_cmd == "mkdir -p '/tmp/nested/workdir/job123'"
    runner.cleanup()


def test_create_runner_factory():
    local = create_runner("local")
    assert isinstance(local, LocalRunner)

    mock = create_runner("mock")
    assert isinstance(mock, MockRunner)
