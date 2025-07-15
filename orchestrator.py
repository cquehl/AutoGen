# orchestrator.py

import asyncio

# Setup and Security
from config.settings import check_ip_address, get_gemini_client

# Import the runnable workflows
from workflows import direct_call
from workflows import agentic_fibonacci

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
    #await agentic_fibonacci.run(gemini_client)