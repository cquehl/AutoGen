"""
Suntory v3 - Interface Module
Terminal UI and command handling
"""

# Use world-class TUI with Half-Life theme, autocomplete, and premium UX
from .tui_world_class import WorldClassTUI as SuntoryTUI, main

__all__ = [
    "SuntoryTUI",
    "main",
]
