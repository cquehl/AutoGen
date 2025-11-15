# workflows/direct_call.py

import tenacity
# This is the corrected import line
from services.ai_services import call_ai
from autogen_ext.models.openai import OpenAIChatCompletionClient

async def run(client: OpenAIChatCompletionClient):
    """
    Executes a direct, single-turn query to the AI model.
    """
    print("--- Starting Direct Call Workflow ---")

    try:
        response = await call_ai(client, "What is the capital of Ohio?")
    
        print("\n--- Direct Call AI Response ---")
        if response.content:
            print(response.content)
        else:
            print("No response received.")
    except tenacity.RetryError:
        print("\n[ERROR] The AI service is unavailable after multiple retries. Please try again later.")    
        
    finally:
        print("---------------------------------")
        print("--- Direct Call Workflow Finished ---")