from rich.console import Console, Group
from rich.padding import Padding
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

# Initialize console with support for true color
console = Console(color_system="truecolor")

# --- Color Tokens ---
COLOR_CYAN = "#00E5FF"
COLOR_MUTED_GREEN = "#81C784"
COLOR_RED_CRIMSON = "#FF3B30"
COLOR_MAIN_ACCENT = "#00E5FF"
COLOR_INDIGO = "#5C6BC0"
COLOR_DIM = "dim"
COLOR_WHITE = "white"


def get_real_metrics() -> dict:
    try:
        import httpx

        resp = httpx.get("http://localhost:8000/api/v1/dashboard/summary", timeout=0.5)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        import logging

        logging.debug("Metrics fetch failed: %s", e)
    return {}


def get_top_panel():
    status_text = Text()

    metrics = get_real_metrics()
    if metrics:
        tokens = metrics.get("total_tokens", 0)
        cost = metrics.get("estimated_cost_usd", 0.0)
        active = metrics.get("active_sessions", 0)
        blocked = metrics.get("blocked_sessions", 0)

        tokens_k = tokens / 1000

        status_text.append(
            f"tokens: {tokens_k:.1f}k · cost: ${cost:.3f} · active: {active} · blocked: {blocked}\n",
            style=COLOR_WHITE,
        )
    else:
        status_text.append(
            "tokens: N/A · cost: N/A · active: N/A · blocked: N/A (api offline)\n", style=COLOR_DIM
        )

    status_text.append(
        "▶▶ bypass permissions on (shift+tab to cycle)", style=f"{COLOR_RED_CRIMSON} bold"
    )

    return Panel(status_text, border_style=COLOR_DIM, padding=(0, 1))


def print_header():
    console.print(get_top_panel())


def render_ui():
    # ==========================================
    # 2. Main Body Container Content
    # ==========================================
    main_content = []

    # 3. Accent Badges
    badge_text = Text("∗ Welcome to AgentWatch research preview!", style=COLOR_MAIN_ACCENT)
    badge_panel = Panel(badge_text, border_style=COLOR_MAIN_ACCENT, expand=False, padding=(0, 1))
    main_content.append(badge_panel)

    # 4. 3D Drop-Shadow ASCII Logo
    # Retro double-stamped shadow effect colored in Salmon
    ascii_logo = """
   █████╗  ██████╗ ███████╗███╗   ██╗████████╗██╗    ██╗ █████╗ ████████╗██████╗ ██╗  ██╗
  ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝██║    ██║██╔══██╗╚══██╔══╝██╔════╝ ██║  ██║
  ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   ██║ █╗ ██║███████║   ██║   ██║      ███████║
  ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   ██║███╗██║██╔══██║   ██║   ██║      ██╔══██║
  ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   ╚███╔███╔╝██║  ██║   ██║   ╚██████╗ ██║  ██║
  ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝    ╚══╝╚══╝ ╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝
"""
    logo_text = Text(ascii_logo.strip("\n"), style=f"bold {COLOR_MAIN_ACCENT}")
    main_content.append(Padding(logo_text, (1, 0, 1, 0)))

    # 5. Instructional Content & Links
    login_instruction = Text(
        "Browser didn't open? Use the url below to sign in:\n", style=COLOR_WHITE
    )
    login_url = Text(
        "https://auth.agentwatch.dev/device?user_code=ABCD-EFGH-IJKL-MNOP-QRST-UVWX-YZ01",
        style=COLOR_DIM,
    )
    main_content.append(login_instruction + login_url)

    # Divider
    main_content.append(Padding(Rule(style=COLOR_DIM), (1, 0, 1, 0)))

    # 6. Duplicated Badge & Security Bullet Points
    main_content.append(badge_panel)

    security_title = Text("\nSecurity notes:", style=f"bold {COLOR_WHITE}")
    main_content.append(security_title)

    security_notes = Text()
    security_notes.append(
        "\n1. AgentWatch is currently in research preview\n", style=f"bold {COLOR_WHITE}"
    )
    security_notes.append(
        "   AgentWatch is an experimental AI tool. It may produce incorrect or unexpected results.\n",
        style=COLOR_DIM,
    )

    security_notes.append("2. AgentWatch runs in your terminal\n", style=f"bold {COLOR_WHITE}")
    security_notes.append(
        "   It has the ability to view your files and execute commands on your behalf.\n",
        style=COLOR_DIM,
    )

    security_notes.append("3. Review commands carefully\n", style=f"bold {COLOR_WHITE}")
    security_notes.append(
        "   For your security, we strongly recommend carefully reviewing any commands before allowing AgentWatch to run them.\n",
        style=COLOR_DIM,
    )
    security_notes.append(
        "   Learn more about the AgentWatch security model at: https://agentwatch.dev/security",
        style=COLOR_DIM,
    )

    main_content.append(security_notes)

    # Combine into main container
    main_panel = Panel(Group(*main_content), border_style=COLOR_DIM, padding=(1, 2))

    # ==========================================
    # 7. External Interactive Footer
    # ==========================================
    footer_text = Text("\nPress Enter to continue...", style=f"bold {COLOR_INDIGO}")

    # Render the layout
    console.print(main_panel)
    console.print(footer_text)


if __name__ == "__main__":
    render_ui()
