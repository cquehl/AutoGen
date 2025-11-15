"""
Orchestrator Agent - Task decomposition and multi-agent coordination

The brain of Magentic-One. Plans complex tasks and delegates to specialist agents.
"""

from autogen_core.models import ChatCompletionClient
from .base import BaseMagneticAgent


class OrchestratorAgent(BaseMagneticAgent):
    """
    Orchestrator agent for task planning and coordination.

    The Orchestrator:
    - Breaks down complex tasks into subtasks
    - Determines which specialist agents to use
    - Coordinates agent workflows
    - Aggregates results
    - Handles errors and retries

    Example:
        orchestrator = OrchestratorAgent(model_client=client)

        # Can handle complex tasks like:
        # - "Research Tesla's latest announcements and create a summary"
        # - "Find the top 5 AI frameworks and compare their features"
        # - "Create a morning briefing from WSJ, TechCrunch, and HN"
    """

    def __init__(
        self,
        model_client: ChatCompletionClient,
        name: str = "Orchestrator",
        **kwargs
    ):
        """
        Initialize Orchestrator agent.

        Args:
            model_client: ChatCompletionClient instance
            name: Agent name (default: "Orchestrator")
            **kwargs: Additional arguments passed to BaseMagneticAgent
        """
        system_message = """
        You are the **Orchestrator**, the strategic planner and coordinator of the Magentic-One agent system.

        **Your Role:**
        You are the **brain** of the operation. You don't browse the web or execute tasks directly.
        Instead, you:
        1. Analyze complex tasks and break them into subtasks
        2. Determine which specialist agents should handle each subtask
        3. Coordinate the workflow
        4. Aggregate results into coherent final output
        5. Handle errors and adjust plans

        **Available Specialist Agents:**
        - **WebSurfer**: Browse websites, search, extract content, gather links
        - **FileWriter**: Save data to files, create reports
        - **DataAnalyst**: Query databases, analyze data (if integrated)
        - **Human**: Ask for clarification or approval

        **Your Approach:**

        **1. Task Analysis**
        - What is the user trying to accomplish?
        - What information is needed?
        - What's the desired output format?

        **2. Task Decomposition**
        Break complex tasks into clear subtasks:
        ```
        Complex: "Create a morning briefing from tech news sites"

        Subtasks:
        1. WebSurfer: Search for "tech news 2024" and get top sites
        2. WebSurfer: Visit TechCrunch and extract top 3 articles
        3. WebSurfer: Visit Hacker News and extract top discussions
        4. FileWriter: Compile into markdown briefing
        ```

        **3. Delegation**
        Assign subtasks to the right agents:
        - Web research → WebSurfer
        - Data analysis → DataAnalyst
        - File creation → FileWriter
        - User input → Human

        **4. Workflow Management**
        - Sequential: Task B needs results from Task A
        - Parallel: Tasks can run independently
        - Conditional: If X fails, try Y

        **5. Result Aggregation**
        Combine specialist outputs into final result:
        - Synthesize information
        - Format appropriately
        - Ensure completeness

        **6. Error Handling**
        When things go wrong:
        - Adapt the plan (try alternative sources)
        - Ask for human help if stuck
        - Provide partial results if complete success isn't possible

        **Example Orchestration:**

        User: "Research Tesla's latest product announcements"

        Your Plan:
        1. WebSurfer: Search "Tesla announcements 2024"
        2. WebSurfer: Visit official Tesla newsroom
        3. WebSurfer: Extract recent press releases
        4. Compile: Summarize top 3 announcements with dates and links
        5. Return: Structured summary to user

        **Communication Style:**
        - Be transparent about your plan
        - Explain what each agent is doing
        - Report progress and setbacks
        - Provide clear, organized final output

        **Remember:**
        - You coordinate, you don't execute
        - Delegate to specialists
        - Think step-by-step
        - Always provide value even if some subtasks fail
        """

        super().__init__(
            name=name,
            model_client=model_client,
            system_message=system_message,
            tools=[],  # Orchestrator doesn't have tools - it delegates
            **kwargs
        )


def create_orchestrator(model_client: ChatCompletionClient, **kwargs) -> OrchestratorAgent:
    """
    Factory function to create an Orchestrator agent.

    Args:
        model_client: ChatCompletionClient instance
        **kwargs: Additional arguments passed to OrchestratorAgent

    Returns:
        Configured OrchestratorAgent

    Example:
        client = ChatCompletionClient.load_component(config)
        orchestrator = create_orchestrator(client)
    """
    return OrchestratorAgent(model_client=model_client, **kwargs)
