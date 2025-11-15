"""
Example: GraphFlow Team with Concurrent Execution

This example demonstrates the new GraphFlow workflow pattern inspired by
AutoGen 0.7.x, showing concurrent agent execution with fan-out/fan-in patterns.
"""

import asyncio
from v2.workflows import WorkflowGraphBuilder
from v2.teams import GraphFlowTeam


async def main():
    """
    Demonstrates a content creation workflow:

    Writer → (Editor1, Editor2) → Reviewer

    The two editors work in parallel (concurrent execution), then both
    feed into the final reviewer.
    """

    # Step 1: Build the workflow graph
    print("=" * 60)
    print("GraphFlow Example: Content Creation Pipeline")
    print("=" * 60)

    graph = (WorkflowGraphBuilder()
        # Add nodes for each agent
        .add_node("writer", "WriterAgent",
                  description="Creates initial draft")
        .add_node("editor1", "EditorAgent",
                  description="Edits for clarity")
        .add_node("editor2", "EditorAgent",
                  description="Edits for grammar")
        .add_node("reviewer", "ReviewerAgent",
                  description="Final quality check")

        # Fan-out: Writer → Editor1 and Editor2 (concurrent)
        .add_edge("writer", "editor1")
        .add_edge("writer", "editor2")

        # Fan-in: Both editors → Reviewer
        .add_edge("editor1", "reviewer")
        .add_edge("editor2", "reviewer")

        .build())

    print("\nWorkflow Graph:")
    print(f"  Nodes: {len(graph._nodes)}")
    print(f"  Edges: {len(graph._edges)}")
    print(f"  Entry nodes: {graph.get_entry_nodes()}")
    print(f"  Exit nodes: {graph.get_exit_nodes()}")

    # Step 2: Create mock agents (in real scenario, these would be actual agents)
    class MockAgent:
        def __init__(self, name):
            self.NAME = name
            self.name = name

    agents = [
        MockAgent("WriterAgent"),
        MockAgent("EditorAgent"),
        MockAgent("ReviewerAgent"),
    ]

    # Step 3: Create GraphFlow team
    team = GraphFlowTeam(
        name="content_team",
        agents=agents,
        graph=graph,
        max_concurrent=5,  # Allow up to 5 concurrent executions
        timeout=300
    )

    print("\nTeam Configuration:")
    print(f"  Name: {team.name}")
    print(f"  Agents: {len(team.agents)}")
    print(f"  Max concurrent: {team.max_concurrent}")

    # Step 4: Visualize the workflow
    print("\n" + team.visualize())

    # Step 5: Run the team (in real scenario)
    print("\nExecution Flow:")
    print("  1. Writer creates draft")
    print("  2. Editor1 and Editor2 edit concurrently (PARALLEL)")
    print("  3. Reviewer receives both edits and produces final version")
    print("\n✅ GraphFlow enables automatic parallelization!")

    # Example with conditional routing
    print("\n" + "=" * 60)
    print("Advanced: Conditional Routing")
    print("=" * 60)

    from v2.workflows.conditions import ContentCondition, MessageCountCondition

    graph_with_conditions = (WorkflowGraphBuilder()
        .add_node("analyzer", "AnalyzerAgent")
        .add_node("success_handler", "SuccessAgent")
        .add_node("error_handler", "ErrorAgent")
        .add_node("retry_handler", "RetryAgent")

        # Route to success if content contains "success"
        .add_edge(
            "analyzer",
            "success_handler",
            condition=ContentCondition("success", match_type="contains")
        )

        # Route to error handler if content contains "error"
        .add_edge(
            "analyzer",
            "error_handler",
            condition=ContentCondition("error", match_type="contains")
        )

        # Route to retry if less than 3 messages
        .add_edge(
            "analyzer",
            "retry_handler",
            condition=MessageCountCondition(3, operator="<")
        )

        .build())

    print("\nConditional routing allows dynamic workflow paths based on:")
    print("  • Message content")
    print("  • Message count")
    print("  • Agent state")
    print("  • Custom lambda functions")
    print("\n✅ Workflows can adapt to runtime conditions!")


if __name__ == "__main__":
    asyncio.run(main())
