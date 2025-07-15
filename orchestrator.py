# orchestrator.py

import asyncio
from config.settings import check_ip_address, get_gemini_client
from workflows import direct_call, agentic_fibonacci, messages_tut


async def start_workflows():
    """
    Initializes the application and runs the selected workflows.
    """
    # --- 1. Perform Startup Checks & Get Client ---
    print("--- Running Startup Checks ---")
    check_ip_address()
    gemini_client = get_gemini_client()
    print("--- Client Initialized ---\n")

    # --- 2. Run Your Selected Workflows ---
    await direct_call.run(gemini_client)
    # await agentic_fibonacci.run(gemini_client)
    await messages_tut.run(gemini_client)