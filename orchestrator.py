# orchestrator.py

import asyncio
from config.settings import check_ip_address, get_gemini_client, get_azure_openai_client
from workflows import direct_call, agentic_fibonacci, messages_tut, weather_ai



async def start_workflows():
    """
    Initializes the application and runs the selected workflows.
    """
    use_gemini = False

    # --- 1. Perform Startup Checks & Get Client ---
    print("--- Running Startup Checks ---")
    
    if use_gemini:
        print("Using Gemini client.")
        check_ip_address()
        ai_client = get_gemini_client()
    else:
        print("Using Azure client.")
        ai_client = get_azure_openai_client()
    print("--- Client Initialized ---\n")


    # --- 2. Run Your Selected Workflows ---
    await direct_call.run(ai_client)
    # await agentic_fibonacci.run(gemini_client)
    # await messages_tut.run(gemini_client)
    # await weather_ai.run(gemini_client)