"""
Suntory v3 - Interface Module Entry Point
Run with: python -m src.interface
"""

import asyncio
from .tui_world_class import main

if __name__ == "__main__":
    asyncio.run(main())
