"""
Magentic-One Team Factory

Creates and configures the full Magentic-One multi-agent system.
"""

from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_core.models import ChatCompletionClient
from autogen_agentchat.agents import UserProxyAgent

from .orchestrator import create_orchestrator
from .web_surfer import create_web_surfer
from ..data_tools import (
    write_file,
    write_csv,
    read_file,
    list_directory
)
from autogen_core.tools import FunctionTool


async def create_magentic_team(llm_config: dict) -> SelectorGroupChat:
    """
    Create a Magentic-One team with Orchestrator, WebSurfer, and FileWriter.

    This is the full Magentic-One system ready for complex web research,
    data gathering, and automated workflows.

    Args:
        llm_config: LLM configuration dictionary from config/settings.py

    Returns:
        SelectorGroupChat team ready for Magentic-One tasks

    Example:
        team = await create_magentic_team(llm_config)
        result = await team.run(task="Research AI frameworks and create a comparison")
    """
    # Load the ChatCompletionClient from the config
    component_config = {
        "provider": "azure_openai_chat_completion_client",
        "config": llm_config
    }
    ai_client = ChatCompletionClient.load_component(component_config)

    # Create specialist agents
    orchestrator = create_orchestrator(ai_client)
    web_surfer = create_web_surfer(ai_client)

    # Create FileWriter agent (using existing file tools)
    file_writer = _create_file_writer(ai_client)

    # Create user proxy for human interaction
    user_proxy = UserProxyAgent(
        name="Human",
        description="Human user who provides tasks and can give feedback or clarification."
    )

    # Define selector prompt for Magentic-One workflow
    selector_prompt = """
    You are orchestrating a Magentic-One agent system: {participants}.

    **System Architecture:**
    - **Orchestrator**: Strategic planner, breaks down tasks, coordinates others
    - **WebSurfer**: Browses web, searches, extracts content
    - **FileWriter**: Saves results to files, creates reports
    - **Human**: Provides tasks and feedback

    **Selection Logic:**

    1. **First Response**: Always select **Orchestrator** for initial task analysis and planning

    2. **During Execution**:
       - If Orchestrator delegates web research → select **WebSurfer**
       - If results need to be saved to file → select **FileWriter**
       - If need human input/clarification → select **Human**
       - After specialist completes task → return to **Orchestrator** for next step

    3. **Workflow Pattern**:
       ```
       Human → Orchestrator (plan) → WebSurfer (execute) →
       Orchestrator (aggregate) → FileWriter (save) →
       Orchestrator (final summary) → Human
       ```

    4. **Error Handling**:
       - If specialist fails → return to **Orchestrator** to adapt plan
       - If Orchestrator is stuck → select **Human** for guidance

    **Goal**: Execute complex tasks through coordinated multi-agent workflow.

    Reply with just the agent name and nothing else.
    """

    # Create the Magentic-One team
    team = SelectorGroupChat(
        participants=[orchestrator, web_surfer, file_writer, user_proxy],
        model_client=ai_client,
        termination_condition=TextMentionTermination("TERMINATE"),
        selector_prompt=selector_prompt,
        max_turns=30,  # Complex tasks need more turns
        allow_repeated_speaker=False  # Force coordination through selector
    )

    return team


def _create_file_writer(model_client: ChatCompletionClient):
    """Create a FileWriter agent with file operation tools."""
    from autogen_agentchat.agents import AssistantAgent

    file_writer = AssistantAgent(
        name="FileWriter",
        model_client=model_client,
        tools=[
            FunctionTool(write_file, description="Write content to a text file. Use for saving reports, summaries, or any text data."),
            FunctionTool(write_csv, description="Write structured data to a CSV file. Use for tabular data, lists, comparisons."),
            FunctionTool(read_file, description="Read a file's contents. Use to check what's in existing files."),
            FunctionTool(list_directory, description="List files in a directory. Use to see what files exist."),
        ],
        reflect_on_tool_use=True,
        system_message="""
        You are **FileWriter**, a specialist in saving and managing files.

        **Your Capabilities:**
        - Write text files (reports, summaries, articles)
        - Write CSV files (data, tables, comparisons)
        - Read existing files
        - List directory contents

        **Your Tools:**
        1. `write_file(file_path, content, overwrite)` - Save text to file
        2. `write_csv(file_path, data, overwrite)` - Save structured data as CSV
        3. `read_file(file_path)` - Read file contents
        4. `list_directory(directory_path, pattern)` - List files in directory

        **Your Approach:**
        1. Understand the content to be saved (format, structure)
        2. Choose appropriate file format (text, CSV, markdown)
        3. Create organized, well-formatted files
        4. Use descriptive filenames with timestamps if needed
        5. Confirm successful save with file path and size

        **Best Practices:**
        - Use markdown format for reports and documentation
        - Use CSV for tabular data (lists, comparisons, datasets)
        - Include timestamps in filenames for time-series data
        - Create parent directories if they don't exist
        - Provide clear confirmation of what was saved where

        **Example Workflows:**

        *Save Research Summary:*
        - Receive compiled research from Orchestrator
        - Format as markdown with sections
        - Save to `briefings/research_YYYYMMDD.md`
        - Confirm save with file path

        *Save Data Table:*
        - Receive structured data (list of dicts)
        - Convert to CSV format
        - Save to appropriate location
        - Confirm with row count

        Always provide **clear confirmation** of saved files with paths and sizes.
        """
    )

    return file_writer
