# weather_orchestrator.py
import asyncio
import aioconsole
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.ui import Console
from autogen_core.models import ChatCompletionClient
# from autogen_ext.models.openai import OpenAIChatCompletionClient
# from autogen_ext.models.openai import AzureOpenAIChatCompletionClient


from config.settings import get_azure_llm_config
from agents.weather_agents import create_weather_agent, create_human_user_proxy, create_joke_agent, create_exec_agent

async def run():
    """
    Sets up and runs a human in the loop with the AI team.
    """
    print("\n--- Starting Weather Agent Team Workflow ---")

    # 1. Get the LLM configuration using the updated settings function
    llm_config = get_azure_llm_config()

    component_config = {
        "provider": "azure_openai_chat_completion_client",
        "config": llm_config
    }

    ai_client = ChatCompletionClient.load_component(component_config)

    # ai_client = AzureOpenAIChatCompletionClient(**llm_config)

    # 2. Create the agents
    weather_agent = create_weather_agent(ai_client)
    user_proxy = create_human_user_proxy()
    joke_agent = create_joke_agent(ai_client)
    exec_agent = create_exec_agent(ai_client)

    # 3. Create the Group Chat
    # The agents list defines the participants in the chat.
    termination = TextMentionTermination("TERMINATE")

    team = SelectorGroupChat(
        [weather_agent, user_proxy, joke_agent, exec_agent],
        selector_prompt="""
        You are a helpful agent that interfaces between the Human_Admin and the rest of the team.
        You are a planning agent.
        Your job is to break down complex tasks into smaller, manageable subtasks.
        Your team members are:
            Weather_Agent: Reports local weather forecast
            Human_Admin: Represents the human user, you can ask clearifying questions
            Joke_Agent: Tells funny jokes
            Exec_Agent: The main point of contact between the user and the team, ensures quality from the team

        You only plan and delegate tasks - you do not execute them yourself.

        When assigning tasks, use this format:
        1. <agent> : <task>

        After all tasks are complete, summarize the findings and end with "TERMINATE".
        """,        
        model_client=ai_client,
        termination_condition=termination,
        max_turns=12,
        allow_repeated_speaker=False
    )

    loop = asyncio.get_running_loop()
    print("Welcome to the Agentic Chat. Type your message and press Enter.")
    print("Type 'exit' or TERMINATE or press Ctrl+D to quit.")

    while True:
        try:
        
            user_input = await loop.run_in_executor(None, input, "> ")
            
            if user_input.lower() == 'exit':
                print("Exiting program...")
                break

            if not user_input.strip():
                continue

            print(f"Passing task to agent: '{user_input}")

            # Run the single agent directly with the task
            await Console(team.run_stream(task=user_input))

        except (EOFError, asyncio.CancelledError):
            print("\nExiting program...")
            break

    await ai_client.close()

    # --- END LOOP ---

    # await ai_client.close()

    print("\n--- Weather Agent Team Workflow Finished ---")

if __name__ == "__main__":
    asyncio.run(run())