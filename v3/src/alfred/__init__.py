"""
Suntory v3 - Alfred Module
The Distinguished AI Concierge
"""

# Use enhanced version with streaming, errors, and cost tracking
from .main_enhanced import AlfredEnhanced as Alfred
from .modes import AlfredMode, get_direct_mode, get_team_mode
from .personality import get_alfred_personality

__all__ = [
    "Alfred",
    "AlfredMode",
    "get_direct_mode",
    "get_team_mode",
    "get_alfred_personality",
]
