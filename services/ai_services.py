# ai_services.py

import time
import openai
from autogen_core.models import UserMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type

@retry(
    wait=wait_random_exponential(min=1, max=10),
    stop=stop_after_attempt(10),
    retry=retry_if_exception_type(openai.InternalServerError)
)
async def call_ai(gemini_client: OpenAIChatCompletionClient, content: str) -> str:
    """
    The central, robust function for making direct AI calls.
    """
    print(f"[{time.strftime('%H:%M:%S')}] Calling AI with content: '{content}'")
    
    response = await gemini_client.create([UserMessage(content=content, source="user")])

    print(f"[{time.strftime('%H:%M:%S')}] Finished response.")
    return response