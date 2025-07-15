# workflows/agentic_fibonacci.py

from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

async def run(client: OpenAIChatCompletionClient):
    """
    Executes an agentic workflow to create a Fibonacci plot.
    """
    print("\n--- Starting Agentic Fibonacci Workflow ---")

    llm_config = {
        "model_client": client,
        "temperature": 0.7,
    }

    assistant = AssistantAgent(
        name="CodeAssistant",
        system_message="You are a helpful assistant that writes Python code to solve problems.",
        llm_config=llm_config
    )

    user_proxy = UserProxyAgent(
        name="UserProxy",
        code_execution_config={"work_dir": "coding", "use_docker": False},
        human_input_mode="TERMINATE"
    )

    await user_proxy.initiate_chat(
        assistant,
        message="Create a plot of the first 20 Fibonacci numbers and save it as 'fibonacci_plot.png'."
    )
    print("--- Agentic Fibonacci Workflow Finished ---")