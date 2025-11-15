"""
Workflow execution engine with support for concurrent agents.

Inspired by AutoGen 0.7.x GraphFlow execution model.
"""

import asyncio
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .graph import WorkflowGraph, WorkflowNode
from ..observability.logger import get_logger

logger = get_logger(__name__)


class ExecutionStatus(Enum):
    """Status of workflow execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExecutionContext:
    """Context for workflow execution."""
    workflow_id: str
    state: Dict[str, Any] = field(default_factory=dict)
    messages: List[Dict[str, Any]] = field(default_factory=list)
    node_results: Dict[str, Any] = field(default_factory=dict)
    retry_counts: Dict[str, int] = field(default_factory=dict)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: ExecutionStatus = ExecutionStatus.PENDING

    @property
    def last_message(self) -> Optional[Dict[str, Any]]:
        """Get the last message in the context."""
        return self.messages[-1] if self.messages else None

    def add_message(self, message: Dict[str, Any]):
        """Add a message to the context."""
        self.messages.append(message)

    def get_node_result(self, node_name: str) -> Optional[Any]:
        """Get the result of a specific node."""
        return self.node_results.get(node_name)

    def set_node_result(self, node_name: str, result: Any):
        """Set the result of a specific node."""
        self.node_results[node_name] = result

    def increment_retry(self, node_name: str) -> int:
        """Increment retry count for a node and return new count."""
        current = self.retry_counts.get(node_name, 0)
        self.retry_counts[node_name] = current + 1
        return self.retry_counts[node_name]

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for condition evaluation."""
        return {
            "state": self.state,
            "messages": self.messages,
            "last_message": self.last_message,
            "node_results": self.node_results,
            "retry_count": sum(self.retry_counts.values()),
        }


class WorkflowExecutor:
    """
    Executes workflows defined by WorkflowGraph.

    Supports:
    - Sequential execution
    - Concurrent execution (fan-out/fan-in)
    - Conditional routing
    - Error handling and retries
    """

    def __init__(
        self,
        graph: WorkflowGraph,
        agent_registry: Any,  # AgentRegistry instance
        max_concurrent: int = 10,
        default_timeout: int = 300,
    ):
        """
        Initialize workflow executor.

        Args:
            graph: Workflow graph to execute
            agent_registry: Registry for resolving agent names
            max_concurrent: Maximum number of concurrent agent executions
            default_timeout: Default timeout for agent execution (seconds)
        """
        self.graph = graph
        self.agent_registry = agent_registry
        self.max_concurrent = max_concurrent
        self.default_timeout = default_timeout
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def execute(
        self,
        task: str,
        initial_state: Optional[Dict[str, Any]] = None,
        entry_node: Optional[str] = None,
    ) -> ExecutionContext:
        """
        Execute the workflow.

        Args:
            task: Initial task description
            initial_state: Initial workflow state
            entry_node: Specific entry node (defaults to graph entry nodes)

        Returns:
            ExecutionContext with results
        """
        # Initialize context
        context = ExecutionContext(
            workflow_id=f"workflow_{datetime.now().timestamp()}",
            state=initial_state or {},
            status=ExecutionStatus.RUNNING,
            start_time=datetime.now(),
        )

        # Add initial task message
        context.add_message({
            "role": "user",
            "content": task,
            "timestamp": datetime.now().isoformat(),
        })

        logger.info(f"Starting workflow execution: {context.workflow_id}")

        try:
            # Determine entry nodes
            if entry_node:
                entry_nodes = [entry_node]
            else:
                entry_nodes = self.graph.get_entry_nodes()

            if not entry_nodes:
                raise ValueError("No entry nodes found in workflow graph")

            # Execute from entry nodes
            await self._execute_nodes(entry_nodes, context)

            context.status = ExecutionStatus.COMPLETED
            logger.info(f"Workflow execution completed: {context.workflow_id}")

        except Exception as e:
            context.status = ExecutionStatus.FAILED
            logger.error(f"Workflow execution failed: {context.workflow_id}", exc_info=True)
            raise

        finally:
            context.end_time = datetime.now()

        return context

    async def _execute_nodes(
        self,
        node_names: List[str],
        context: ExecutionContext,
        visited: Optional[Set[str]] = None,
    ):
        """
        Execute a list of nodes (potentially in parallel).

        Args:
            node_names: List of node names to execute
            context: Execution context
            visited: Set of already visited nodes (for cycle detection)
        """
        if visited is None:
            visited = set()

        # Filter out already visited nodes
        nodes_to_execute = [n for n in node_names if n not in visited]
        if not nodes_to_execute:
            return

        # Mark nodes as visited
        for node_name in nodes_to_execute:
            visited.add(node_name)

        # Execute nodes concurrently if multiple
        if len(nodes_to_execute) > 1:
            logger.info(f"Executing {len(nodes_to_execute)} nodes concurrently: {nodes_to_execute}")
            tasks = [
                self._execute_single_node(node_name, context)
                for node_name in nodes_to_execute
            ]
            await asyncio.gather(*tasks)
        else:
            # Single node execution
            await self._execute_single_node(nodes_to_execute[0], context)

        # Find next nodes to execute
        all_next_nodes = []
        for node_name in nodes_to_execute:
            next_nodes = await self._get_next_nodes(node_name, context)
            all_next_nodes.extend(next_nodes)

        # Remove duplicates while preserving order
        unique_next_nodes = list(dict.fromkeys(all_next_nodes))

        # Continue execution if there are next nodes
        if unique_next_nodes:
            await self._execute_nodes(unique_next_nodes, context, visited)

    async def _execute_single_node(self, node_name: str, context: ExecutionContext):
        """
        Execute a single node.

        Args:
            node_name: Name of the node to execute
            context: Execution context
        """
        node = self.graph.get_node(node_name)
        if not node:
            raise ValueError(f"Node '{node_name}' not found in graph")

        logger.info(f"Executing node: {node_name} (agent: {node.agent_name})")

        async with self._semaphore:
            try:
                # Get agent instance
                agent = await self._get_agent(node.agent_name)

                # Build task from context
                task = self._build_task_for_node(node, context)

                # Execute agent with timeout
                result = await asyncio.wait_for(
                    self._run_agent(agent, task, context),
                    timeout=self.default_timeout,
                )

                # Store result
                context.set_node_result(node_name, result)

                # Add result to messages
                context.add_message({
                    "role": "assistant",
                    "name": node.agent_name,
                    "content": result.get("content", ""),
                    "node": node_name,
                    "timestamp": datetime.now().isoformat(),
                })

                logger.info(f"Node execution completed: {node_name}")

            except asyncio.TimeoutError:
                logger.error(f"Node execution timeout: {node_name}")
                raise
            except Exception as e:
                logger.error(f"Node execution failed: {node_name}", exc_info=True)
                raise

    async def _get_next_nodes(self, current_node: str, context: ExecutionContext) -> List[str]:
        """
        Determine next nodes based on edge conditions.

        Args:
            current_node: Current node name
            context: Execution context

        Returns:
            List of next node names
        """
        next_nodes = []
        edges = self.graph.get_edges_from(current_node)

        for edge in edges:
            # Evaluate condition if present
            if edge.condition:
                try:
                    if edge.condition(context.to_dict()):
                        next_nodes.append(edge.target)
                        logger.debug(f"Edge condition met: {current_node} -> {edge.target}")
                    else:
                        logger.debug(f"Edge condition not met: {current_node} -> {edge.target}")
                except Exception as e:
                    logger.error(f"Error evaluating edge condition: {current_node} -> {edge.target}", exc_info=True)
            else:
                # No condition, always traverse
                next_nodes.append(edge.target)

        return next_nodes

    async def _get_agent(self, agent_name: str) -> Any:
        """Get agent instance from registry."""
        # This would use the agent registry to get/create agent instance
        # For now, this is a placeholder
        agent_metadata = self.agent_registry.get_agent(agent_name)
        if not agent_metadata:
            raise ValueError(f"Agent '{agent_name}' not found in registry")
        return agent_metadata

    def _build_task_for_node(self, node: WorkflowNode, context: ExecutionContext) -> str:
        """Build task description for a node based on context."""
        # Use the last message as the task
        # More sophisticated implementations could build context-aware prompts
        if context.last_message:
            return context.last_message.get("content", "")
        return ""

    async def _run_agent(self, agent: Any, task: str, context: ExecutionContext) -> Dict[str, Any]:
        """
        Run an agent and return the result.

        This is a simplified implementation. In practice, this would integrate
        with the actual agent execution framework.
        """
        # Placeholder for actual agent execution
        # In real implementation, this would call the agent's chat/run method
        return {
            "content": f"Agent {agent.get('name', 'unknown')} executed with task: {task[:100]}...",
            "status": "success",
        }
