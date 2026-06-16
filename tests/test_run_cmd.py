"""Unit tests for run_cmd secure wrapper and speech synthesis utilities."""

from __future__ import annotations

import subprocess
from unittest import mock

import pytest

from agentwatch.cli._utils import run_cmd
from agentwatch.cli._utils.speech import speak


def test_run_cmd_valid_execution():
    """Verify that a valid command execution runs shell=False and returns completed process."""
    mock_result = subprocess.CompletedProcess(
        args=["echo", "hello"], returncode=0, stdout="hello\n", stderr=""
    )

    with mock.patch("subprocess.run", return_value=mock_result) as mock_run:
        result = run_cmd.run(["echo", "hello"])

        assert result.returncode == 0
        assert result.stdout == "hello\n"
        mock_run.assert_called_once_with(
            ["echo", "hello"],
            shell=False,
            capture_output=True,
            text=True,
            timeout=None,
            env=None,
            cwd=None,
        )


def test_run_cmd_invalid_arguments():
    """Verify that forbidden characters in arguments raise CommandError."""
    # Semicolon injection attempt
    with pytest.raises(run_cmd.CommandError, match="contains forbidden characters"):
        run_cmd.run(["echo", "hello; rm -rf /"])

    # Pipe injection attempt
    with pytest.raises(run_cmd.CommandError, match="contains forbidden characters"):
        run_cmd.run(["echo", "hello | sh"])

    # Redirect injection attempt
    with pytest.raises(run_cmd.CommandError, match="contains forbidden characters"):
        run_cmd.run(["echo", "hello > file.txt"])

    # Backtick injection attempt
    with pytest.raises(run_cmd.CommandError, match="contains forbidden characters"):
        run_cmd.run(["echo", "hello `id`"])

    # Verify that check_args=False bypasses character validation
    mock_result = subprocess.CompletedProcess(
        args=["echo", "hello; rm -rf /"], returncode=0, stdout="hello; rm -rf /\n", stderr=""
    )
    with mock.patch("subprocess.run", return_value=mock_result) as mock_run:
        result = run_cmd.run(["echo", "hello; rm -rf /"], check_args=False)
        assert result.returncode == 0
        mock_run.assert_called_once()


def test_run_cmd_whitelist_allowed_characters():
    """Verify that safe characters (including paths, quotes, URLs, brackets) are allowed."""
    mock_result = subprocess.CompletedProcess(
        args=["echo"], returncode=0, stdout="success\n", stderr=""
    )

    # Complex safe args containing quotes, braces, equal sign, paths, URLs with query parameters
    safe_args = [
        "echo",
        "hello world",
        "/path/to/file.txt",
        "C:\\Windows\\System32",
        "https://example.com/api?param1=val&param2=val2",
        "--option=value",
        "[DRY-RUN]",
        "{key: val}",
        "#comment",
        "a+b",
        "a,b",
        "~user",
        "john.doe@example.com",
        "100%",
        "\"double-quoted\"",
        "'single-quoted'",
        "$100",
    ]

    with mock.patch("subprocess.run", return_value=mock_result) as mock_run:
        result = run_cmd.run(safe_args)
        assert result.returncode == 0
        mock_run.assert_called_once()


def test_run_cmd_failure_raises_command_error():
    """Verify that a non-zero exit code raises CommandError with details."""
    mock_result = subprocess.CompletedProcess(
        args=["false"], returncode=1, stdout="", stderr="some error message"
    )

    with mock.patch("subprocess.run", return_value=mock_result):
        with pytest.raises(run_cmd.CommandError) as exc_info:
            run_cmd.run(["false"])

        assert exc_info.value.returncode == 1
        assert exc_info.value.stdout == ""
        assert exc_info.value.stderr == "some error message"
        assert "Command failed with exit code 1" in str(exc_info.value)


def test_run_cmd_execution_exception():
    """Verify that system execution exceptions (like FileNotFoundError) are converted to CommandError."""
    with mock.patch("subprocess.run", side_effect=FileNotFoundError("No such file")):
        with pytest.raises(run_cmd.CommandError) as exc_info:
            run_cmd.run(["invalid_command"])

        assert "Failed to execute command 'invalid_command'" in str(exc_info.value)


def test_speech_darwin_say():
    """Verify Darwin uses 'say' command."""
    mock_result = subprocess.CompletedProcess(args=["say", "hello"], returncode=0)

    with mock.patch("sys.platform", "darwin"), \
         mock.patch("subprocess.run", return_value=mock_result) as mock_run:
        success = speak("hello")
        assert success is True
        mock_run.assert_called_once_with(
            ["say", "hello"],
            shell=False,
            capture_output=True,
            text=True,
            timeout=None,
            env=None,
            cwd=None,
        )


def test_speech_win32_powershell():
    """Verify win32 uses powershell command."""
    mock_result = subprocess.CompletedProcess(args=[], returncode=0)

    with mock.patch("sys.platform", "win32"), \
         mock.patch("subprocess.run", return_value=mock_result) as mock_run:
        success = speak("hello")
        assert success is True
        mock_run.assert_called_once()
        called_args = mock_run.call_args[0][0]
        assert "powershell.exe" in called_args
        assert "System.Speech.Synthesis.SpeechSynthesizer" in called_args[3]


def test_speech_linux_espeak():
    """Verify Linux uses 'espeak' command."""
    mock_result = subprocess.CompletedProcess(args=["espeak", "hello"], returncode=0)

    with mock.patch("sys.platform", "linux"), \
         mock.patch("subprocess.run", return_value=mock_result) as mock_run:
        success = speak("hello")
        assert success is True
        mock_run.assert_called_once_with(
            ["espeak", "hello"],
            shell=False,
            capture_output=True,
            text=True,
            timeout=None,
            env=None,
            cwd=None,
        )


def test_speech_fallback_graceful():
    """Verify speech functions handle exceptions and return False (graceful fallback)."""
    # Force run to raise an exception representing missing utility
    with mock.patch("subprocess.run", side_effect=FileNotFoundError("command not found")):
        success = speak("hello")
        assert success is False
