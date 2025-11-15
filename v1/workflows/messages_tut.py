# workflows/messages_tut.py

import tenacity
from services.ai_services import call_ai
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.messages import TextMessage

async def run(client: OpenAIChatCompletionClient):
    """
    Agent-Agent Messages
    AgentChat supports many message types for agent-to-agent communication. 
    They belong to subclasses of the base class BaseChatMessage. 
    Concrete subclasses covers basic text and multimodal communication, such as TextMessage and MultiModalMessage.
    """
    print("--- Starting Messages_Tut ---")

    try:
        content="Hello, world!"

        response = await call_ai(client, content)
    
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


        