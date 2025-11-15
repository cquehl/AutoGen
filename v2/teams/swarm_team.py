"""
Swarm team pattern - dynamic agent selection based on task requirements.

Inspired by OpenAI Swarm and AutoGen's dynamic agent selection patterns.
"""

import asyncio
from typing import List, Dict, Any, Optional, Callable, AsyncIterator
from datetime import datetime

from .base_team import BaseTeam, TeamResult, TeamStatus
from ..observability.logger import get_logger

logger = get_logger(__name__)


class SwarmTeam(BaseTeam):
    """
    Team that dynamically selects agents based on task requirements.

    Unlike sequential or graph-based teams, swarm teams use a selector
    function to determine which agent should handle each step, allowing
    for flexible, context-aware agent orchestration.

    Example:
        >>> def selector(task, history, agents):
        ...     if "data" in task.lower():
        ...         return "data_analyst"
        ...     elif "weather" in task.lower():
        ...         return "weather_agent"
        ...     return "orchestrator"
        >>>
        >>> team = SwarmTeam(
        ...     "smart_swarm",
        ...     agents=[data_analyst, weather_agent, orchestrator],
        ...     selector_func=selector
        ... )
    """

    def __init__(
        self,
        name: str,
        agents: List[Any],
        selector_func: Optional[Callable] = None,
        allow_repeat: bool = True,
        max_rounds: int = 10,
        timeout: int = 600,
    ):
        """
        Initialize swarm team.

        Args:
            name: Team name
            agents: List of available agents
            selector_func: Function to select next agent
                Signature: (task: str, history: List, agents: List) -> str
            allow_repeat: Whether same agent can be selected multiple times
            max_rounds: Maximum conversation rounds
            timeout: Maximum execution time in seconds
        """
        super().__init__(name, agents, max_rounds, timeout)
        self.selector_func = selector_func or self._default_selector
        self.allow_repeat = allow_repeat

        # Build agent capabilities map
        self._capabilities = self._build_capabilities_map()

    def _build_capabilities_map(self) -> Dict[str, List[str]]:
        """Build a map of agent names to their capabilities/keywords."""
        capabilities = {}

        for agent in self.agents:
            agent_name = self._get_agent_name(agent)

            # Extract capabilities from agent metadata
            caps = []
            if hasattr(agent, "CATEGORY"):
                caps.append(agent.CATEGORY.lower())
            if hasattr(agent, "DESCRIPTION"):
                # Extract keywords from description
                desc = agent.DESCRIPTION.lower()
                caps.extend(desc.split())

            capabilities[agent_name] = caps

        return capabilities

    def _default_selector(
        self,
        task: str,
        history: List[Dict[str, Any]],
        agents: List[Any],
    ) -> Optional[str]:
        """
        Default agent selector based on keyword matching.

        Args:
            task: Current task description
            history: Conversation history
            agents: Available agents

        Returns:
            Selected agent name or None
        """
        task_lower = task.lower()

        # Score each agent based on capability match
        scores = {}
        for agent in agents:
            agent_name = self._get_agent_name(agent)
            capabilities = self._capabilities.get(agent_name, [])

            score = sum(1 for cap in capabilities if cap in task_lower)
            scores[agent_name] = score

        # Select highest scoring agent
        if scores:
            best_agent = max(scores.items(), key=lambda x: x[1])
            if best_agent[1] > 0:  # Only return if there's a match
                return best_agent[0]

        # Fallback to first agent if no matches
        if agents:
            return self._get_agent_name(agents[0])

        return None

    async def run(self, task: str, **kwargs) -> TeamResult:
        """
        Run swarm team with dynamic agent selection.

        Args:
            task: Initial task description
            **kwargs: Additional parameters

        Returns:
            TeamResult with execution results
        """
        result = TeamResult(
            task=task,
            status=TeamStatus.RUNNING,
            start_time=datetime.now(),
        )

        logger.info(f"Starting swarm team '{self.name}' with {len(self.agents)} agents")

        try:
            messages = []
            current_task = task
            used_agents = set()
            rounds_completed = 0

            # Add initial user message
            messages.append({
                "role": "user",
                "content": task,
                "timestamp": datetime.now().isoformat(),
            })

            # Execute rounds with dynamic agent selection
            while rounds_completed < self.max_rounds:
                # Select next agent
                available_agents = self.agents if self.allow_repeat else [
                    a for a in self.agents
                    if self._get_agent_name(a) not in used_agents
                ]

                if not available_agents:
                    logger.info("No more available agents")
                    break

                selected_name = self.selector_func(current_task, messages, available_agents)
                if not selected_name:
                    logger.info("No agent selected, ending swarm")
                    break

                # Get selected agent
                selected_agent = self.get_agent_by_name(selected_name)
                if not selected_agent:
                    logger.warning(f"Selected agent '{selected_name}' not found")
                    break

                logger.info(f"Round {rounds_completed + 1}: Selected agent '{selected_name}'")
                used_agents.add(selected_name)

                # Execute agent
                agent_result = await asyncio.wait_for(
                    self._execute_agent(selected_agent, current_task, messages),
                    timeout=self.timeout // self.max_rounds,
                )

                # Add agent response to messages
                message = {
                    "role": "assistant",
                    "name": selected_name,
                    "content": agent_result.get("content", ""),
                    "metadata": {
                        "round": rounds_completed + 1,
                        "selection_score": agent_result.get("score", 0),
                    },
                    "timestamp": datetime.now().isoformat(),
                }
                messages.append(message)

                # Check if task is complete
                if self._is_task_complete(agent_result, messages):
                    logger.info("Task marked as complete by agent")
                    break

                # Prepare next task
                current_task = agent_result.get("next_task", agent_result.get("content", ""))
                rounds_completed += 1

            result.messages = messages
            result.status = TeamStatus.COMPLETED
            result.final_answer = messages[-1]["content"] if messages else None
            result.metadata = {
                "rounds_completed": rounds_completed,
                "agents_used": list(used_agents),
                "total_agents": len(self.agents),
            }

            logger.info(f"Swarm team '{self.name}' completed after {rounds_completed} rounds")

        except asyncio.TimeoutError:
            result.status = TeamStatus.FAILED
            result.error = f"Team execution timeout after {self.timeout} seconds"
            logger.error(f"Swarm team '{self.name}' timeout")

        except Exception as e:
            result.status = TeamStatus.FAILED
            result.error = str(e)
            logger.error(f"Swarm team '{self.name}' failed", exc_info=True)

        finally:
            result.end_time = datetime.now()

        return result

    async def run_stream(self, task: str, **kwargs) -> AsyncIterator[Dict[str, Any]]:
        """
        Run with streaming results.

        Yields events for each agent selection and execution.
        """
        yield {
            "type": "team_start",
            "team": self.name,
            "task": task,
            "timestamp": datetime.now().isoformat(),
        }

        messages = []
        current_task = task
        used_agents = set()
        rounds_completed = 0

        try:
            while rounds_completed < self.max_rounds:
                # Select next agent
                available_agents = self.agents if self.allow_repeat else [
                    a for a in self.agents
                    if self._get_agent_name(a) not in used_agents
                ]

                if not available_agents:
                    break

                selected_name = self.selector_func(current_task, messages, available_agents)
                if not selected_name:
                    break

                selected_agent = self.get_agent_by_name(selected_name)
                if not selected_agent:
                    break

                yield {
                    "type": "agent_selected",
                    "agent": selected_name,
                    "round": rounds_completed + 1,
                    "timestamp": datetime.now().isoformat(),
                }

                used_agents.add(selected_name)

                # Execute agent
                agent_result = await self._execute_agent(selected_agent, current_task, messages)

                message = {
                    "role": "assistant",
                    "name": selected_name,
                    "content": agent_result.get("content", ""),
                    "timestamp": datetime.now().isoformat(),
                }
                messages.append(message)

                yield {
                    "type": "agent_complete",
                    "agent": selected_name,
                    "message": message,
                    "timestamp": datetime.now().isoformat(),
                }

                if self._is_task_complete(agent_result, messages):
                    break

                current_task = agent_result.get("next_task", agent_result.get("content", ""))
                rounds_completed += 1

            yield {
                "type": "team_complete",
                "team": self.name,
                "final_answer": messages[-1]["content"] if messages else None,
                "rounds": rounds_completed,
                "agents_used": list(used_agents),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            yield {
                "type": "team_error",
                "team": self.name,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def _is_task_complete(self, agent_result: Dict[str, Any], messages: List[Dict[str, Any]]) -> bool:
        """
        Determine if task is complete.

        Args:
            agent_result: Result from last agent execution
            messages: All messages so far

        Returns:
            True if task is complete
        """
        # Check if agent explicitly marked task as complete
        if agent_result.get("task_complete"):
            return True

        # Check for completion keywords in response
        content = agent_result.get("content", "").lower()
        completion_keywords = ["task complete", "finished", "done", "final answer"]
        return any(keyword in content for keyword in completion_keywords)

    async def _execute_agent(
        self,
        agent: Any,
        task: str,
        history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Execute a single agent.

        Args:
            agent: Agent to execute
            task: Task description
            history: Conversation history

        Returns:
            Agent result dictionary
        """
        # Placeholder for actual agent execution
        agent_name = self._get_agent_name(agent)

        # Simulate agent execution
        await asyncio.sleep(0.1)

        return {
            "content": f"{agent_name} processed: {task[:100]}...",
            "status": "success",
            "task_complete": False,
        }

    def _get_agent_name(self, agent: Any) -> str:
        """Get agent name from agent instance."""
        if hasattr(agent, "name"):
            return agent.name
        elif hasattr(agent, "NAME"):
            return agent.NAME
        return f"Agent_{id(agent)}"
