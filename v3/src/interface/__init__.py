"""
Suntory v3 - Interface Module
Terminal UI and command handling
"""

# Use enhanced TUI with streaming, onboarding, and cost display
from .tui_enhanced import SuntoryTUIEnhanced as SuntoryTUI, main

__all__ = [
    "SuntoryTUI",
    "main",
]
