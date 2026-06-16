"""
Cross-platform speech synthesis support for the AgentWatch CLI.
Falls back gracefully if voice synthesis utilities are unavailable.
"""

from __future__ import annotations

import logging
import sys

from agentwatch.cli._utils import run_cmd

logger = logging.getLogger(__name__)


def speak(message: str) -> bool:
    """Announce a message verbally using the system's speech synthesis engine.

    This function falls back gracefully if speech synthesis tools are not installed
    or if execution fails.

    Args:
        message: The text to announce verbally.

    Returns:
        True if the speech command ran successfully, False if speech synthesis
        is unavailable or failed.
    """
    # Restrict message strictly to alphanumeric, spaces, and standard punctuation.
    # This prevents any potential command/argument injection.
    safe_msg = "".join(c for c in message if c.isalnum() or c in " ,.!?_")

    try:
        if sys.platform == "darwin":
            # macOS: use native 'say' command
            run_cmd.run(["say", safe_msg])
            return True
        elif sys.platform == "win32":
            # Windows: use PowerShell SpeechSynthesis
            # We use single quotes in the PowerShell string, but safe_msg contains no quotes.
            cmd = [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                f"Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{safe_msg}')",
            ]
            run_cmd.run(cmd, check_args=False)
            return True
        else:
            # Linux / Unix / BSD: try 'espeak'
            run_cmd.run(["espeak", safe_msg])
            return True
    except Exception as exc:
        logger.debug("Speech synthesis failed or is unavailable: %s", exc)
        return False
