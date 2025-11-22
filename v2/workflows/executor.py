"""
Workflow execution engine with support for concurrent agents.

Inspired by AutoGen 0.7.x GraphFlow execution model.
"""

import asyncio
import uuid
from typing import Dict, List, Any, Optional, Set, Protocol
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


class AgentProtocol(Protocol):
    """Protocol for agent instances."""

    @property
    def name(self) -> str:
        """Agent name."""
        ...

    async def arun(self, task: str, **kwargs) -> str:
        """Async run method."""
        ...


@dataclass
class ExecutionContext:
    """Context for workflow execution with thread-safe operations."""
    workflow_id: str
    state: Dict[str, Any] = field(default_factory=dict)
    messages: List[Dict[str, Any]] = field(default_factory=list)
    node_results: Dict[str, Any] = field(default_factory=dict)
    retry_counts: Dict[str, int] = field(default_factory=dict)
    failure_counts: Dict[str, int] = field(default_factory=dict)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: ExecutionStatus = ExecutionStatus.PENDING

    def __post_init__(self):
        """Initialize locks for thread-safe operations."""
        self._message_lock = asyncio.Lock()
        self._result_lock = asyncio.Lock()
        self._retry_lock = asyncio.Lock()

    @property
    def last_message(self) -> Optional[Dict[str, Any]]:
        """Get the last message in the context."""
        return self.messages[-1] if self.messages else None

    async def add_message(self, message: Dict[str, Any]):
        """Thread-safe message addition."""
        async with self._message_lock:
            self.messages.append(message)

    async def get_node_result(self, node_name: str) -> Optional[Any]:
        """Thread-safe result retrieval."""
        async with self._result_lock:
            return self.node_results.get(node_name)

    async def set_node_result(self, node_name: str, result: Any):
        """Thread-safe result storage."""
        async with self._result_lock:
            self.node_results[node_name] = result

    async def increment_retry(self, node_name: str) -> int:
        """Thread-safe retry count increment."""
        async with self._retry_lock:
            current = self.retry_counts.get(node_name, 0)
            self.retry_counts[node_name] = current + 1
            return self.retry_counts[node_name]

    async def increment_failure(self, node_name: str) -> int:
        """Thread-safe failure count increment."""
        async with self._retry_lock:
            current = self.failure_counts.get(node_name, 0)
            self.failure_counts[node_name] = current + 1
            return self.failure_counts[node_name]

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for condition evaluation."""
        return {
            "state": self.state,
            "messages": self.messages.copy(),  # Snapshot
            "last_message": self.last_message,
            "node_results": self.node_results.copy(),  # Snapshot
            "retry_count": sum(self.retry_counts.values()),
        }


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""
    pass


class WorkflowExecutor:
    """
    Executes workflows defined by WorkflowGraph.

    Supports:
    - Sequential execution
    - Concurrent execution (fan-out/fan-in)
    - Conditional routing
    - Error handling with retries
    - Circuit breaker pattern
    """

    def __init__(
        self,
        graph: WorkflowGraph,
        agent_registry: Any,  # AgentRegistry instance
        max_concurrent: int = 10,
        default_timeout: int = 300,
        max_retries: int = 3,
        circuit_breaker_threshold: int = 5,
    ):
        """
        Initialize workflow executor.

        Args:
            graph: Workflow graph to execute
            agent_registry: Registry for resolving agent names
            max_concurrent: Maximum number of concurrent agent executions
            default_timeout: Default timeout for agent execution (seconds)
            max_retries: Maximum retry attempts per node
            circuit_breaker_threshold: Failures before circuit opens
        """
        self.graph = graph
        self.agent_registry = agent_registry
        self.max_concurrent = max_concurrent
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self.circuit_breaker_threshold = circuit_breaker_threshold

        # Lazy initialization of semaphore (must be created in event loop)
        self._semaphore: Optional[asyncio.Semaphore] = None

    async def _ensure_semaphore(self) -> asyncio.Semaphore:
        """Ensure semaphore is created in the event loop context."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        return self._semaphore

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

        Raises:
            ValueError: If no entry nodes found
            CircuitBreakerOpen: If circuit breaker opens
        """
        context = ExecutionContext(
            workflow_id=f"workflow_{uuid.uuid4().hex[:12]}",
            state=initial_state or {},
            status=ExecutionStatus.RUNNING,
            start_time=datetime.now(),
        )

        await context.add_message({
            "role": "user",
            "content": task,
            "timestamp": datetime.now().isoformat(),
        })

        logger.info(f"Starting workflow execution: {context.workflow_id}")

        try:
            if entry_node:
                entry_nodes = [entry_node]
            else:
                entry_nodes = self.graph.get_entry_nodes()

            if not entry_nodes:
                raise ValueError("No entry nodes found in workflow graph")

            await self._execute_nodes(entry_nodes, context)

            context.status = ExecutionStatus.COMPLETED
            logger.info(f"Workflow execution completed: {context.workflow_id}")

        except CircuitBreakerOpen as e:
            context.status = ExecutionStatus.FAILED
            logger.error(f"Workflow circuit breaker opened: {context.workflow_id}")
            raise

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

        nodes_to_execute = [n for n in node_names if n not in visited]
        if not nodes_to_execute:
            return

        for node_name in nodes_to_execute:
            visited.add(node_name)

        if len(nodes_to_execute) > 1:
            logger.info(f"Executing {len(nodes_to_execute)} nodes concurrently: {nodes_to_execute}")
            tasks = [
                self._execute_single_node(node_name, context)
                for node_name in nodes_to_execute
            ]
            # Use return_exceptions to handle errors gracefully
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Check for failures
            for node_name, result in zip(nodes_to_execute, results):
                if isinstance(result, Exception):
                    logger.error(f"Node {node_name} failed: {result}")
                    # Re-raise if it's a critical error
                    if isinstance(result, (CircuitBreakerOpen, asyncio.CancelledError)):
                        raise result
        else:
            await self._execute_single_node(nodes_to_execute[0], context)

        all_next_nodes = []
        for node_name in nodes_to_execute:
            next_nodes = await self._get_next_nodes(node_name, context)
            all_next_nodes.extend(next_nodes)

        # Remove duplicates while preserving order
        unique_next_nodes = list(dict.fromkeys(all_next_nodes))

        if unique_next_nodes:
            await self._execute_nodes(unique_next_nodes, context, visited)

    async def _execute_single_node(self, node_name: str, context: ExecutionContext):
        """
        Execute a single node with retry logic and circuit breaker.

        Args:
            node_name: Name of the node to execute
            context: Execution context

        Raises:
            CircuitBreakerOpen: If node has failed too many times
            Exception: If execution fails after all retries
        """
        node = self.graph.get_node(node_name)
        if not node:
            raise ValueError(f"Node '{node_name}' not found in graph")

        failure_count = context.failure_counts.get(node_name, 0)
        if failure_count >= self.circuit_breaker_threshold:
            raise CircuitBreakerOpen(
                f"Circuit breaker open for node '{node_name}' "
                f"({failure_count} failures)"
            )

        logger.info(f"Executing node: {node_name} (agent: {node.agent_name})")

        semaphore = await self._ensure_semaphore()
        last_error = None

        for attempt in range(self.max_retries):
            async with semaphore:
                try:
                    agent = await self._get_agent(node.agent_name)
                    task = await self._build_task_for_node(node, context)

                    result = await asyncio.wait_for(
                        self._run_agent(agent, task, context),
                        timeout=self.default_timeout,
                    )

                    # Thread-safe result storage
                    await context.set_node_result(node_name, result)

                    # Thread-safe message addition
                    await context.add_message({
                        "role": "assistant",
                        "name": node.agent_name,
                        "content": result.get("content", str(result)),
                        "node": node_name,
                        "timestamp": datetime.now().isoformat(),
                        "metadata": {
                            "attempt": attempt + 1,
                            "success": True,
                        }
                    })

                    logger.info(f"Node execution completed: {node_name} (attempt {attempt + 1})")
                    return

                except asyncio.TimeoutError as e:
                    last_error = e
                    logger.warning(f"Node execution timeout: {node_name} (attempt {attempt + 1})")
                    await context.increment_retry(node_name)

                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff

                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"Node execution failed: {node_name} (attempt {attempt + 1}): {e}"
                    )
                    await context.increment_retry(node_name)

                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff

        await context.increment_failure(node_name)
        logger.error(
            f"Node execution failed after {self.max_retries} attempts: {node_name}",
            exc_info=last_error
        )
        raise last_error or Exception(f"Node {node_name} failed after {self.max_retries} retries")

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
            if edge.condition:
                try:
                    if edge.condition(context.to_dict()):
                        next_nodes.append(edge.target)
                        logger.debug(f"Edge condition met: {current_node} -> {edge.target}")
                    else:
                        logger.debug(f"Edge condition not met: {current_node} -> {edge.target}")
                except Exception as e:
                    logger.error(
                        f"Error evaluating edge condition: {current_node} -> {edge.target}",
                        exc_info=True
                    )
            else:
                next_nodes.append(edge.target)  # No condition, always traverse

        return next_nodes

    async def _get_agent(self, agent_name: str) -> AgentProtocol:
        """
        Get agent instance from registry.

        Args:
            agent_name: Name of the agent

        Returns:
            Agent instance

        Raises:
            ValueError: If agent not found or doesn't have required methods
        """
        agent_metadata = self.agent_registry.get_agent(agent_name)
        if not agent_metadata:
            raise ValueError(f"Agent '{agent_name}' not found in registry")

        if isinstance(agent_metadata, dict):
            agent = agent_metadata.get("instance") or agent_metadata.get("agent_class")
        else:
            agent = agent_metadata

        if agent is None:
            raise ValueError(f"No agent instance found for '{agent_name}'")

        return agent

    async def _build_task_for_node(
        self,
        node: WorkflowNode,
        context: ExecutionContext
    ) -> str:
        """
        Build task description for a node based on context.

        Args:
            node: Workflow node
            context: Execution context

        Returns:
            Task string for the agent
        """
        # TODO: More sophisticated implementations could build context-aware prompts
        # from multiple messages or node-specific context
        if context.last_message:
            return context.last_message.get("content", "")
        return ""

    async def _run_agent(
        self,
        agent: AgentProtocol,
        task: str,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """
        Run an agent and return the result.

        Args:
            agent: Agent instance
            task: Task description
            context: Execution context

        Returns:
            Result dictionary with 'content' and optional metadata

        Raises:
            ValueError: If agent doesn't have a compatible run method
        """
        try:
            if hasattr(agent, 'arun'):
                result = await agent.arun(task)
            elif hasattr(agent, 'run'):
                result = await asyncio.to_thread(agent.run, task)
            else:
                raise ValueError(
                    f"Agent {getattr(agent, 'name', 'unknown')} has no run() or arun() method"
                )

            if isinstance(result, str):
                return {"content": result, "status": "success"}
            elif isinstance(result, dict):
                if "content" not in result:
                    result["content"] = str(result)
                return result
            else:
                return {"content": str(result), "status": "success"}

        except Exception as e:
            logger.error(f"Agent execution error: {e}", exc_info=True)
            raise
