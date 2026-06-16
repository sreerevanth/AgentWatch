"""
Central command execution utility for AgentWatch CLI.
Validates arguments against a strict whitelist to prevent command-injection risks.
"""

from __future__ import annotations

import logging
import re
import subprocess
from collections.abc import Sequence

logger = logging.getLogger(__name__)

# A comprehensive whitelist of safe characters for arguments:
# - Alphanumerics: a-z, A-Z, 0-9
# - Whitespace: spaces, tabs, newlines
# - Safe path and url symbols: . _ / \ : = + , % @ ~ ? ! * ( ) " ' $ & [ ] { } # ^ -
# Semicolons (;), pipes (|), redirects (<, >), and backticks (`) are explicitly blocked
# to prevent shell command execution if arguments are ever unsafely evaluated.
ALLOWED_ARG_RE = re.compile(r"^[a-zA-Z0-9_./\\:=+,%@~?!\*()\"\'\s$&[\]{}#^-]*$")


class CommandError(Exception):
    """Raised when command validation fails or execution returns a non-zero exit code."""

    def __init__(
        self,
        message: str,
        returncode: int | None = None,
        stdout: str | None = None,
        stderr: str | None = None,
    ) -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def run(
    args: Sequence[str],
    *,
    check_args: bool = True,
    timeout: float | None = None,
    env: dict[str, str] | None = None,
    cwd: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Execute a command securely with shell=False and argument validation.

    Args:
        args: List of command arguments. First element is the executable.
        check_args: If True, validate each argument against ALLOWED_ARG_RE.
        timeout: Optional timeout in seconds.
        env: Optional environment dictionary override.
        cwd: Optional working directory for the subprocess.

    Returns:
        A subprocess.CompletedProcess containing stdout and stderr.

    Raises:
        CommandError: If validation is enabled and an argument contains forbidden characters,
                     or if the command execution fails with a non-zero exit code.
    """
    if not args:
        raise CommandError("Command arguments cannot be empty.")

    if check_args:
        # Validate each argument against the whitelist
        for idx, arg in enumerate(args):
            if not ALLOWED_ARG_RE.match(arg):
                # Find the invalid characters to include in the error message for clarity
                invalid_chars = sorted(list(set(c for c in arg if not ALLOWED_ARG_RE.match(c))))
                raise CommandError(
                    f"Argument at index {idx} contains forbidden characters: "
                    f"'{''.join(invalid_chars)}'. Argument value: {repr(arg)}"
                )

    logger.debug("Executing command: %s", " ".join(args))

    try:
        # Prefer subprocess.run with shell=False
        result = subprocess.run(  # noqa: S603 # nosec B603
            args,
            shell=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            cwd=cwd,
        )
    except Exception as exc:
        logger.error("Failed to execute command %s: %s", args[0], exc)
        raise CommandError(f"Failed to execute command '{args[0]}': {exc}") from exc

    logger.debug("Command exited with code %d", result.returncode)

    if result.returncode != 0:
        logger.error(
            "Command '%s' failed with exit code %d.\nSTDOUT:\n%s\nSTDERR:\n%s",
            " ".join(args),
            result.returncode,
            result.stdout,
            result.stderr,
        )
        raise CommandError(
            f"Command failed with exit code {result.returncode}.",
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    return result
