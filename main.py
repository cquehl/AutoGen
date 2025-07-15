# main.py

import asyncio
import orchestrator

async def main():
    """The main entry point that starts the orchestrator."""
    print("Main ---- Starting")
    await orchestrator.start_workflows()

# This is the standard way to run the main async function
if __name__ == "__main__":
    asyncio.run(main())