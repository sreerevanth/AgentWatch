import logging
import subprocess  # nosec B404

logger = logging.getLogger(__name__)


def run_validated_command(
    cmd_args: list[str], check: bool = True, timeout: int | float | None = 30.0
) -> tuple[int, str, str]:
    """
    Executes a shell command safely using a list of arguments with shell=False.
    Validates that the command is a non-empty list of strings to prevent injection.
    Uses a bounded timeout by default to avoid hanging subprocesses.
    """
    # Validation Logic: Enforce strict list of strings
    if not cmd_args or not isinstance(cmd_args, list):
        raise ValueError("Command arguments must be provided as a non-empty list.")

    if not all(isinstance(arg, str) for arg in cmd_args):
        raise ValueError("All command arguments must be strings.")

    try:
        # We explicitly use a pre-validated list of strings with shell=False
        result = subprocess.run(  # noqa: S603 # nosec B603
            cmd_args,
            capture_output=True,
            text=True,
            check=check,
            shell=False,
            timeout=timeout,
        )

        return result.returncode, result.stdout.strip(), result.stderr.strip()

    except subprocess.TimeoutExpired as e:
        logger.error(f"Command timed out after {timeout} seconds: {e}")
        raise
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}: {e.stderr}")
        raise
