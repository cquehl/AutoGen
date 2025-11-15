"""
Example: Enhanced Team Patterns

Demonstrates the three new team orchestration patterns:
1. GraphFlowTeam - DiGraph-based workflows
2. SequentialTeam - Linear pipelines
3. SwarmTeam - Dynamic agent selection
"""

import asyncio
from v2.teams import SequentialTeam, SwarmTeam


async def demo_sequential_team():
    """Demonstrate sequential team pattern."""
    print("=" * 60)
    print("1. Sequential Team: Research Pipeline")
    print("=" * 60)

    # Mock agents
    class MockAgent:
        def __init__(self, name):
            self.NAME = name
            self.name = name

    researcher = MockAgent("ResearcherAgent")
    analyst = MockAgent("AnalystAgent")
    writer = MockAgent("WriterAgent")

    # Create sequential team
    team = SequentialTeam(
        name="research_pipeline",
        agents=[researcher, analyst, writer],
        carryover_mode="all",  # Pass all context
        max_carryover_messages=5,
        max_rounds=1  # One pass through the pipeline
    )

    print(f"\nTeam: {team.name}")
    print(f"Agents in order: {[a.name for a in team.agents]}")
    print("\nExecution Flow:")
    print("  1. Researcher gathers information")
    print("  2. Analyst analyzes the research (receives researcher's output)")
    print("  3. Writer creates report (receives analyst's output)")
    print("\nCarryover mode: 'all' - each agent sees recent messages")
    print("✅ Perfect for linear data transformation pipelines!\n")


async def demo_swarm_team():
    """Demonstrate swarm team pattern."""
    print("=" * 60)
    print("2. Swarm Team: Dynamic Agent Selection")
    print("=" * 60)

    # Mock agents with capabilities
    class MockAgent:
        def __init__(self, name, category, description):
            self.NAME = name
            self.name = name
            self.CATEGORY = category
            self.DESCRIPTION = description

    data_analyst = MockAgent(
        "DataAnalystAgent",
        "data",
        "Analyzes databases and data"
    )
    weather_agent = MockAgent(
        "WeatherAgent",
        "weather",
        "Provides weather forecasts"
    )
    orchestrator = MockAgent(
        "OrchestratorAgent",
        "coordination",
        "Coordinates multi-agent tasks"
    )

    # Create swarm team with custom selector
    def smart_selector(task, history, agents):
        """Select agent based on task keywords."""
        task_lower = task.lower()

        if "weather" in task_lower or "forecast" in task_lower:
            return "WeatherAgent"
        elif "data" in task_lower or "database" in task_lower:
            return "DataAnalystAgent"
        else:
            return "OrchestratorAgent"

    team = SwarmTeam(
        name="smart_swarm",
        agents=[data_analyst, weather_agent, orchestrator],
        selector_func=smart_selector,
        allow_repeat=True,
        max_rounds=10
    )

    print(f"\nTeam: {team.name}")
    print(f"Available agents: {[a.name for a in team.agents]}")
    print("\nSelector Logic:")
    print("  • Task contains 'weather' → WeatherAgent")
    print("  • Task contains 'data' → DataAnalystAgent")
    print("  • Otherwise → OrchestratorAgent")

    print("\nExample task routing:")
    tasks = [
        "What's the weather like?",
        "Analyze customer data",
        "Create a summary report"
    ]

    for task in tasks:
        selected = smart_selector(task, [], team.agents)
        print(f"  '{task}' → {selected}")

    print("\n✅ Dynamic routing based on capabilities!\n")


async def demo_comparison():
    """Compare team patterns."""
    print("=" * 60)
    print("3. Team Pattern Comparison")
    print("=" * 60)

    print("\n┌─────────────────┬──────────────┬─────────────────────────┬────────────┐")
    print("│ Pattern         │ Execution    │ Best For                │ Complexity │")
    print("├─────────────────┼──────────────┼─────────────────────────┼────────────┤")
    print("│ GraphFlow       │ Graph-based  │ Complex workflows,      │ High       │")
    print("│                 │              │ parallel execution      │            │")
    print("├─────────────────┼──────────────┼─────────────────────────┼────────────┤")
    print("│ Sequential      │ Fixed order  │ Linear pipelines,       │ Low        │")
    print("│                 │              │ chained processing      │            │")
    print("├─────────────────┼──────────────┼─────────────────────────┼────────────┤")
    print("│ Swarm           │ Dynamic      │ Flexible routing,       │ Medium     │")
    print("│                 │              │ capability matching     │            │")
    print("└─────────────────┴──────────────┴─────────────────────────┴────────────┘")

    print("\nWhen to use each pattern:")
    print("\n📊 GraphFlow:")
    print("   - Complex workflows with multiple paths")
    print("   - Need for parallel processing")
    print("   - Conditional routing between agents")
    print("   - Iterative refinement loops")

    print("\n📝 Sequential:")
    print("   - Clear linear progression")
    print("   - Each step builds on previous")
    print("   - Data transformation pipelines")
    print("   - Research → Analysis → Writing")

    print("\n🐝 Swarm:")
    print("   - Uncertain which agent needed upfront")
    print("   - Task-dependent routing")
    print("   - Capability-based selection")
    print("   - Flexible, adaptive workflows")

    print("\n✅ Choose the right pattern for your use case!\n")


async def main():
    """Run all demonstrations."""
    await demo_sequential_team()
    await demo_swarm_team()
    await demo_comparison()


if __name__ == "__main__":
    asyncio.run(main())
