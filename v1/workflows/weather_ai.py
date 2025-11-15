# workflows/weather_ai.py

import asyncio
from pyautogen import AssistantAgent, UserProxyAgent

async def run(llm_config: dict):
    """
    A simple agentic workflow that uses the provided llm_config.
    This is a standalone example of a two-agent chat.
    """
    print("\n--- Starting Basic AI Workflow ---")

    # 1. Create an Assistant Agent
    # The agent is configured with the llm_config dictionary.
    assistant = AssistantAgent(
        name="AI_Assistant",
        llm_config=llm_config,
        system_message="You are a helpful AI assistant. Provide a concise answer."
    )

    # 2. Create a User Proxy Agent
    # This agent acts on behalf of the user. `code_execution_config=False` means
    # it won't try to execute any code.
    user_proxy = UserProxyAgent(
        name="User",
        code_execution_config=False,
        human_input_mode="NEVER", # No human input needed for this simple case.
    )

    # 3. Start the conversation
    # The user_proxy initiates the chat with the assistant.
    await user_proxy.a_initiate_chat(
        assistant,
        message="What is the most interesting fact about the planet Jupiter?",
    )

    print("\n--- Basic AI Workflow Finished ---")

