# weather_orchestrator.py
import asyncio
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.ui import Console
# from autogen_agentchat.messages import TextMessage
# from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
# from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient


from config.settings import get_azure_llm_config
from agents.weather_agents import create_weather_agent, create_human_user_proxy

async def run():
    """
    Sets up and runs a group chat between a weather agent and a human user proxy.
    """
    print("\n--- Starting Weather Agent Team Workflow ---")

    # 1. Get the LLM configuration using the updated settings function
    llm_config = get_azure_llm_config()
    ai_client = AzureOpenAIChatCompletionClient(**llm_config)

    # 2. Create the agents
    weather_agent = create_weather_agent(ai_client)
    user_proxy = create_human_user_proxy()

    # 3. Create the Group Chat
    # The agents list defines the participants in the chat.
    termination = TextMentionTermination("TERMINATE")

    team = SelectorGroupChat(
        [weather_agent, user_proxy],
        model_client=ai_client,
        termination_condition=termination,
        max_turns=12,
        allow_repeated_speaker=False
    )
    await Console(team.run_stream(task="Report the weather."))

    # 4. Start the conversation
    # The user_proxy initiates the chat, which will immediately prompt you for input
    # because its human_input_mode is set to "ALWAYS".
    await Console(
        team.run_stream(
            task="What is the weather like?"
        )
    )

    print("\n--- Weather Agent Team Workflow Finished ---")

if __name__ == "__main__":
    asyncio.run(run())