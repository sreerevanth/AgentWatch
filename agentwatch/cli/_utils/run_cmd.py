import logging
import subprocess

logger = logging.getLogger(__name__)

def run_validated_command(
    command: list[str], 
    timeout: int | None = 30, 
    check: bool = True
) -> tuple[int, str, str]:
    """Executes a shell command safely, preventing injection."""
    
    # Validation: Ensure the command is strictly a list of strings
    if not isinstance(command, list) or not all(isinstance(arg, str) for arg in command):
        raise ValueError("Command must be a list of strings.")

    try:
        logger.debug(f"Executing: {' '.join(command)}")
        result = subprocess.run( # noqa: S603
            command,
            capture_output=True,  # Fixes UP022
            text=True,
            timeout=timeout,
            check=check,
            shell=False,
        )
        
        return result.returncode, result.stdout.strip(), result.stderr.strip()

    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}: {e.stderr}")
        raise