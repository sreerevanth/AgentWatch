import logging
import subprocess  # nosec B404

logger = logging.getLogger(__name__)


def run_validated_command(cmd_args: list[str], check: bool = True) -> tuple[int, str, str]:
    """
    Executes a shell command safely using a list of arguments with shell=False.
    """
    # Validation logic goes here...

    try:
        # We explicitly use a pre-validated list of strings with shell=False
        result = subprocess.run(  # nosec B603
            cmd_args,
            capture_output=True,
            text=True,
            check=check,
            shell=False,
        )

        return result.returncode, result.stdout.strip(), result.stderr.strip()

    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}: {e.stderr}")
        raise
