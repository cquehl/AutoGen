"""
GraphFlow team pattern - DiGraph-based workflow orchestration.

Inspired by AutoGen 0.7.x GraphFlow with concurrent agent execution.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from .base_team import BaseTeam, TeamResult, TeamStatus
from ..workflows.graph import WorkflowGraph
from ..workflows.executor import WorkflowExecutor, ExecutionContext
from ..observability.logger import get_logger

logger = get_logger(__name__)


class GraphFlowTeam(BaseTeam):
    """
    Team that executes agents according to a directed graph workflow.

    Supports:
    - Sequential execution
    - Concurrent execution (fan-out/fan-in)
    - Conditional routing
    - Cycles for iterative workflows

    Example:
        >>> # Create a fan-out/fan-in workflow
        >>> graph = WorkflowGraph()
        >>> graph.add_node("writer", "WriterAgent")
        >>> graph.add_node("editor1", "EditorAgent")
        >>> graph.add_node("editor2", "EditorAgent")
        >>> graph.add_node("reviewer", "ReviewerAgent")
        >>>
        >>> # Fan-out from writer to editors
        >>> graph.add_edge("writer", "editor1")
        >>> graph.add_edge("writer", "editor2")
        >>>
        >>> # Fan-in to reviewer
        >>> graph.add_edge("editor1", "reviewer")
        >>> graph.add_edge("editor2", "reviewer")
        >>>
        >>> team = GraphFlowTeam("editorial", agents, graph)
        >>> result = await team.run("Write an article about AI")
    """

    def __init__(
        self,
        name: str,
        agents: List[Any],
        graph: WorkflowGraph,
        max_concurrent: int = 5,
        max_rounds: int = 20,
        timeout: int = 600,
    ):
        """
        Initialize GraphFlow team.

        Args:
            name: Team name
            agents: List of agents available to the team
            graph: Workflow graph defining agent orchestration
            max_concurrent: Maximum concurrent agent executions
            max_rounds: Maximum number of workflow rounds (for cycles)
            timeout: Maximum execution time in seconds
        """
        super().__init__(name, agents, max_rounds, timeout)
        self.graph = graph
        self.max_concurrent = max_concurrent

        # Validate graph
        errors = self.graph.validate()
        if errors:
            logger.warning(f"Graph validation warnings: {errors}")

        # Create agent name to agent mapping
        self._agent_map = self._build_agent_map()

    def _build_agent_map(self) -> Dict[str, Any]:
        """Build mapping from agent names to agent instances."""
        agent_map = {}
        for agent in self.agents:
            # Try different name attributes
            name = None
            if hasattr(agent, "name"):
                name = agent.name
            elif hasattr(agent, "NAME"):
                name = agent.NAME

            if name:
                agent_map[name] = agent
            else:
                logger.warning(f"Agent has no name attribute: {agent}")

        return agent_map

    async def run(self, task: str, entry_node: Optional[str] = None, **kwargs) -> TeamResult:
        """
        Run the team on a task using the workflow graph.

        Args:
            task: Task description
            entry_node: Specific entry node (defaults to graph entry nodes)
            **kwargs: Additional parameters

        Returns:
            TeamResult with execution results
        """
        result = TeamResult(
            task=task,
            status=TeamStatus.RUNNING,
            start_time=datetime.now(),
        )

        logger.info(f"Starting GraphFlow team '{self.name}' with task: {task[:100]}...")

        try:
            # Create executor
            executor = WorkflowExecutor(
                graph=self.graph,
                agent_registry=self._create_agent_registry(),
                max_concurrent=self.max_concurrent,
                default_timeout=self.timeout,
            )

            # Execute workflow with timeout
            context: ExecutionContext = await asyncio.wait_for(
                executor.execute(task, entry_node=entry_node),
                timeout=self.timeout,
            )

            # Extract results
            result.messages = context.messages
            result.status = TeamStatus.COMPLETED
            result.metadata = {
                "workflow_id": context.workflow_id,
                "node_results": context.node_results,
                "retry_counts": context.retry_counts,
                "state": context.state,
            }

            # Extract final answer from last message
            if context.last_message:
                result.final_answer = context.last_message.get("content", "")

            logger.info(f"GraphFlow team '{self.name}' completed successfully")

        except asyncio.TimeoutError:
            result.status = TeamStatus.FAILED
            result.error = f"Team execution timeout after {self.timeout} seconds"
            logger.error(f"GraphFlow team '{self.name}' timeout")

        except Exception as e:
            result.status = TeamStatus.FAILED
            result.error = str(e)
            logger.error(f"GraphFlow team '{self.name}' failed", exc_info=True)

        finally:
            result.end_time = datetime.now()

        return result

    def _create_agent_registry(self) -> Dict[str, Any]:
        """Create a simple agent registry for the executor."""
        # Simple wrapper to make it compatible with executor expectations
        class SimpleRegistry:
            def __init__(self, agent_map):
                self.agent_map = agent_map

            def get_agent(self, name):
                agent = self.agent_map.get(name)
                if agent:
                    return {"name": name, "instance": agent}
                return None

        return SimpleRegistry(self._agent_map)

    async def run_stream(self, task: str, **kwargs):
        """
        Run with streaming results.

        Yields events as the workflow progresses through nodes.
        """
        yield {
            "type": "team_start",
            "team": self.name,
            "task": task,
            "timestamp": datetime.now().isoformat(),
        }

        # For now, run normally and yield final result
        # A more advanced implementation would stream events from executor
        result = await self.run(task, **kwargs)

        yield {
            "type": "team_complete",
            "team": self.name,
            "result": result.to_dict(),
            "timestamp": datetime.now().isoformat(),
        }

    def visualize(self) -> str:
        """
        Generate a text-based visualization of the workflow graph.

        Returns:
            Text representation of the graph
        """
        lines = [f"GraphFlow Team: {self.name}", "=" * 50]

        # Show nodes
        lines.append("\nNodes:")
        for node_name, node in self.graph._nodes.items():
            lines.append(f"  - {node_name} (agent: {node.agent_name})")

        # Show edges
        lines.append("\nEdges:")
        for edge in self.graph._edges:
            condition = " [conditional]" if edge.condition else ""
            lines.append(f"  - {edge.source} → {edge.target}{condition}")

        # Show entry/exit nodes
        lines.append("\nEntry nodes:")
        for node in self.graph.get_entry_nodes():
            lines.append(f"  - {node}")

        lines.append("\nExit nodes:")
        for node in self.graph.get_exit_nodes():
            lines.append(f"  - {node}")

        return "\n".join(lines)
