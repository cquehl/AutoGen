# weather_orchestrator.py
import asyncio
import aioconsole
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.ui import Console
from autogen_core.models import ChatCompletionClient

from config.settings import get_azure_llm_config, get_gemini_llm_config
from agents.weather_agents import create_weather_agent, create_human_user_proxy, create_joke_agent, create_exec_agent

async def run():
    # SET THIS FLAG TO TRUE FOR GEMINI, FALSE FOR AZURE
    USE_GEMINI = False

    print("\nInitializing agentic systems...")
    await asyncio.sleep(1)
    print("All protocols online. Welcome back.")
    
    # 1. Select the LLM configuration based on the flag
    if USE_GEMINI:
        # Note: To make Gemini work, you'd need to find its "well-known provider" string
        llm_config = get_gemini_llm_config()
        provider_string = "google_gemini_chat_completion_client" # This is a guess, might need to be verified
    else:
        llm_config = get_azure_llm_config()
        provider_string = "azure_openai_chat_completion_client" # This is the correct key for Azure

    # 2. Create the client object using the correct component structure
    component_config = {
        "provider": provider_string,
        "config": llm_config
    }
    ai_client = ChatCompletionClient.load_component(component_config)

    # 3. Create agents by passing the initialized client object
    weather_agent = create_weather_agent(ai_client)
    user_proxy = create_human_user_proxy()
    joke_agent = create_joke_agent(ai_client)
    exec_agent = create_exec_agent(ai_client)

    # 4. Create the Group Chat, passing the client object
    team = SelectorGroupChat(
        [weather_agent, user_proxy, joke_agent, exec_agent],
        model_client=ai_client,
        termination_condition=TextMentionTermination("TERMINATE"),
    )

    while True:
        try:
            user_input = await aioconsole.ainput("Awaiting your command... ")
            if user_input.lower() == 'exit':
                break
            if not user_input.strip():
                continue
            print(f"Understood. Processing request: '{user_input}'")
            await Console(team.run_stream(task=user_input))
        except (EOFError, asyncio.CancelledError):
            break

    await ai_client.close()
    print("\nShutting down. It was a pleasure assisting you.")

if __name__ == "__main__":
    asyncio.run(run())