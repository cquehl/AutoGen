"""
Suntory v3 - Alfred Module
The Distinguished AI Concierge
"""

from .main import Alfred
from .modes import AlfredMode, get_direct_mode, get_team_mode
from .personality import get_alfred_personality

__all__ = [
    "Alfred",
    "AlfredMode",
    "get_direct_mode",
    "get_team_mode",
    "get_alfred_personality",
]
