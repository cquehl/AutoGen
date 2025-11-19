"""
Suntory v3 - Half-Life Inspired Theme
Premium CLI color palette and styling
"""

from rich.theme import Theme

# Half-Life / HEV Suit inspired color palette
HALFLIFE_THEME = Theme({
    # Primary HEV Suit Orange
    "primary": "#FF6600 bold",
    "primary.dim": "#CC5200",

    # Amber alert colors
    "amber": "#FFA500",
    "amber.dim": "#CC8400",

    # Success (green HUD)
    "success": "#00FF00 bold",
    "success.dim": "#00CC00",

    # Error (red damage indicator)
    "error": "#FF0000 bold",
    "error.dim": "#CC0000",

    # Info (blue sci-fi)
    "info": "#00BFFF",
    "info.dim": "#0099CC",

    # Muted terminal text
    "muted": "#888888",
    "muted.dim": "#666666",

    # Alfred's voice (slightly warmer white)
    "alfred": "#FFE4B5",  # Moccasin - refined, butler-like

    # Command highlighting
    "command": "#FF6600 bold",
    "command.arg": "#FFA500",

    # System messages
    "system": "#00BFFF dim",

    # Cost tracking (amber warnings)
    "cost": "#FFA500",
    "cost.warning": "#FF6600 bold",
    "cost.danger": "#FF0000 bold",

    # Agent indicators
    "agent": "#00FF00",
    "agent.thinking": "#FFA500 dim",

    # Progress and status
    "progress.bar": "#FF6600",
    "progress.spinner": "#FFA500",

    # Borders and UI elements
    "panel.border": "#FF6600",
    "panel.title": "#FFA500 bold",
})


# ASCII Art Banner (Half-Life style)
HALFLIFE_BANNER = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ██████╗ ██╗   ██╗███╗   ██╗████████╗ ██████╗ ██████╗ ██╗   ║
║   ██╔════╝██║   ██║████╗  ██║╚══██╔══╝██╔═══██╗██╔══██╗╚██╗  ║
║   ╚█████╗ ██║   ██║██╔██╗ ██║   ██║   ██║   ██║██████╔╝ ╚██╗ ║
║    ╚═══██╗██║   ██║██║╚██╗██║   ██║   ██║   ██║██╔══██╗ ██╔╝ ║
║   ██████╔╝╚██████╔╝██║ ╚████║   ██║   ╚██████╔╝██║  ██║██╔╝  ║
║   ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═╝   ║
║                                                               ║
║   🥃  S Y S T E M   v 3                                       ║
║                                                               ║
║   ALFRED AI CONCIERGE                                         ║
║   Multi-Agent Orchestration Platform                          ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""

# Simplified ASCII (faster rendering)
SIMPLE_BANNER = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   🥃  SUNTORY SYSTEM v3                                       ║
║                                                               ║
║   Alfred AI Concierge                                         ║
║   Multi-Agent Orchestration Platform                          ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""

# HEV Suit style status indicators
HEV_INDICATORS = {
    "online": "● ONLINE",
    "ready": "● READY",
    "processing": "◉ PROCESSING",
    "thinking": "◐ THINKING",
    "warning": "⚠ WARNING",
    "error": "✖ ERROR",
    "success": "✓ SUCCESS",
}


def get_status_indicator(status: str, value: str = "") -> str:
    """Get HEV suit style status indicator"""
    indicator = HEV_INDICATORS.get(status, "●")

    if value:
        return f"{indicator} {value}"
    return indicator
