"""AgentWatch CLI Animator.

Handles loading states, terminal progress animations, and audible safety notifications.
"""

from __future__ import annotations

import asyncio
import sys

from agentwatch.cli._utils.speech import speak


class CLIAnimator:
    """Provides visual console animations and audio-synthesis alerts."""

    def __init__(self, message: str = "Processing") -> None:
        self.message = message
        self._active = False
        self._task: asyncio.Task | None = None

    async def _animate(self) -> None:
        chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        idx = 0
        while self._active:
            sys.stdout.write(f"\r{chars[idx]} {self.message}...")
            sys.stdout.flush()
            idx = (idx + 1) % len(chars)
            try:
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break

    def start(self) -> None:
        """Start the terminal loading spinner."""
        self._active = True
        self._task = asyncio.create_task(self._animate())

    async def stop(self) -> None:
        """Stop the terminal loading spinner and clear the line."""
        self._active = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

    def announce_block(self, tool_name: str) -> None:
        """Announce that a tool execution was blocked by the safety engine."""
        msg = f"Safety block triggered for tool {tool_name}"
        sys.stdout.write(f"\n🚫 [BLOCKED] {msg}\n")
        sys.stdout.flush()
        speak(msg)
