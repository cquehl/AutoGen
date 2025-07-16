# services/ai_services.py

import time
import openai
from autogen_agentchat.agents import AssistantAgent
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type

@retry(
    wait=wait_random_exponential(min=1, max=10),
    stop=stop_after_attempt(10),
    # You may need to adjust the exception type based on the underlying HTTP library
    # used by pyautogen, e.g., for connection errors.
    retry=retry_if_exception_type(openai.InternalServerError)
)
async def call_ai(llm_config: dict, content: str) -> str:
    """
    The central, robust function for making direct AI calls using the
    modern llm_config pattern. It creates a temporary agent to handle the request.
    """
    print(f"[{time.strftime('%H:%M:%S')}] Calling AI with content: '{content}'")
    
    # Create a temporary, stateless agent to make the call.
    # This is the modern replacement for calling a client directly.
    temp_assistant = AssistantAgent(
        name="temp_assistant",
        llm_config=llm_config,
        system_message="You are a helpful AI assistant. Respond directly to the user's query.",
    )

    # Use the agent's `aask` method to get a response.
    # This replaces the direct `client.create()` call.
    # The agent handles message formatting internally.
    response = await temp_assistant.aask(content)

    print(f"[{time.strftime('%H:%M:%S')}] Finished response.")
    
    # The response from aask is a dictionary, so we need to extract the content
    if isinstance(response, dict) and "content" in response:
        return response["content"].strip()
    
    return str(response)

