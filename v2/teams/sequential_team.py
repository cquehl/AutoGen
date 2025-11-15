"""
Sequential team pattern - chained agent conversations with carryover.

Inspired by AutoGen 0.7.x sequential chat pattern.
"""

import asyncio
from typing import List, Dict, Any, Optional, AsyncIterator
from datetime import datetime

from .base_team import BaseTeam, TeamResult, TeamStatus
from ..observability.logger import get_logger

logger = get_logger(__name__)


class SequentialTeam(BaseTeam):
    """
    Team that executes agents in a fixed sequence.

    Each agent receives the output from the previous agent as input,
    enabling chained workflows where each step builds on the previous.

    Example:
        >>> team = SequentialTeam(
        ...     "research_pipeline",
        ...     agents=[researcher, analyst, writer],
        ...     carryover_config={"max_messages": 5}
        ... )
        >>> result = await team.run("Research market trends in AI")
        # 1. Researcher gathers information
        # 2. Analyst analyzes the research
        # 3. Writer creates a report
    """

    def __init__(
        self,
        name: str,
        agents: List[Any],
        carryover_mode: str = "last",  # "last", "all", "summary"
        max_carryover_messages: int = 3,
        max_rounds: int = 1,  # Usually just one pass through the sequence
        timeout: int = 600,
    ):
        """
        Initialize sequential team.

        Args:
            name: Team name
            agents: List of agents in execution order
            carryover_mode: How to carry messages between agents
                - "last": Only last message
                - "all": All messages
                - "summary": Summarized context
            max_carryover_messages: Maximum messages to carry over
            max_rounds: Number of times to loop through the sequence
            timeout: Maximum execution time in seconds
        """
        super().__init__(name, agents, max_rounds, timeout)
        self.carryover_mode = carryover_mode
        self.max_carryover_messages = max_carryover_messages

        if not agents:
            raise ValueError("Sequential team requires at least one agent")

    async def run(self, task: str, **kwargs) -> TeamResult:
        """
        Run agents in sequence.

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

        logger.info(f"Starting sequential team '{self.name}' with {len(self.agents)} agents")

        try:
            current_task = task
            all_messages = []

            # Execute rounds
            for round_num in range(self.max_rounds):
                logger.info(f"Sequential team '{self.name}' - Round {round_num + 1}/{self.max_rounds}")

                # Execute each agent in sequence
                for idx, agent in enumerate(self.agents):
                    agent_name = self._get_agent_name(agent)
                    logger.info(f"Executing agent {idx + 1}/{len(self.agents)}: {agent_name}")

                    # Execute agent with timeout
                    agent_result = await asyncio.wait_for(
                        self._execute_agent(agent, current_task, all_messages),
                        timeout=self.timeout // len(self.agents),  # Divide timeout among agents
                    )

                    # Store message
                    message = {
                        "role": "assistant",
                        "name": agent_name,
                        "content": agent_result.get("content", ""),
                        "metadata": {
                            "round": round_num + 1,
                            "sequence_position": idx + 1,
                            "agent": agent_name,
                        },
                        "timestamp": datetime.now().isoformat(),
                    }
                    all_messages.append(message)

                    # Prepare task for next agent
                    current_task = self._prepare_carryover(
                        agent_result.get("content", ""),
                        all_messages,
                    )

                    logger.debug(f"Agent {agent_name} completed")

            result.messages = all_messages
            result.status = TeamStatus.COMPLETED
            result.final_answer = all_messages[-1]["content"] if all_messages else None
            result.metadata = {
                "rounds_completed": self.max_rounds,
                "agents_executed": len(self.agents) * self.max_rounds,
            }

            logger.info(f"Sequential team '{self.name}' completed successfully")

        except asyncio.TimeoutError:
            result.status = TeamStatus.FAILED
            result.error = f"Team execution timeout after {self.timeout} seconds"
            logger.error(f"Sequential team '{self.name}' timeout")

        except Exception as e:
            result.status = TeamStatus.FAILED
            result.error = str(e)
            logger.error(f"Sequential team '{self.name}' failed", exc_info=True)

        finally:
            result.end_time = datetime.now()

        return result

    async def run_stream(self, task: str, **kwargs) -> AsyncIterator[Dict[str, Any]]:
        """
        Run with streaming results, yielding after each agent.

        Yields:
            Event dictionaries with agent results
        """
        yield {
            "type": "team_start",
            "team": self.name,
            "task": task,
            "agents": [self._get_agent_name(a) for a in self.agents],
            "timestamp": datetime.now().isoformat(),
        }

        current_task = task
        all_messages = []

        try:
            for round_num in range(self.max_rounds):
                for idx, agent in enumerate(self.agents):
                    agent_name = self._get_agent_name(agent)

                    yield {
                        "type": "agent_start",
                        "agent": agent_name,
                        "round": round_num + 1,
                        "position": idx + 1,
                        "timestamp": datetime.now().isoformat(),
                    }

                    # Execute agent
                    agent_result = await self._execute_agent(agent, current_task, all_messages)

                    message = {
                        "role": "assistant",
                        "name": agent_name,
                        "content": agent_result.get("content", ""),
                        "metadata": {
                            "round": round_num + 1,
                            "sequence_position": idx + 1,
                        },
                        "timestamp": datetime.now().isoformat(),
                    }
                    all_messages.append(message)

                    yield {
                        "type": "agent_complete",
                        "agent": agent_name,
                        "message": message,
                        "timestamp": datetime.now().isoformat(),
                    }

                    # Prepare for next agent
                    current_task = self._prepare_carryover(
                        agent_result.get("content", ""),
                        all_messages,
                    )

            yield {
                "type": "team_complete",
                "team": self.name,
                "final_answer": all_messages[-1]["content"] if all_messages else None,
                "message_count": len(all_messages),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            yield {
                "type": "team_error",
                "team": self.name,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def _prepare_carryover(self, last_content: str, all_messages: List[Dict[str, Any]]) -> str:
        """
        Prepare carryover content for next agent.

        Args:
            last_content: Content from last agent
            all_messages: All messages so far

        Returns:
            Carryover content for next agent
        """
        if self.carryover_mode == "last":
            return last_content

        elif self.carryover_mode == "all":
            # Include recent messages up to max
            recent_messages = all_messages[-self.max_carryover_messages:]
            context_parts = []
            for msg in recent_messages:
                agent_name = msg.get("name", "Unknown")
                content = msg.get("content", "")
                context_parts.append(f"[{agent_name}]: {content}")

            return "\n\n".join(context_parts)

        elif self.carryover_mode == "summary":
            # Simple summary (in practice, could use LLM to summarize)
            return f"Previous context (last {len(all_messages)} messages):\n{last_content}"

        else:
            return last_content

    async def _execute_agent(
        self,
        agent: Any,
        task: str,
        context_messages: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Execute a single agent.

        Args:
            agent: Agent to execute
            task: Task description
            context_messages: Previous messages for context

        Returns:
            Agent result dictionary
        """
        # Placeholder for actual agent execution
        # In real implementation, this would call the agent's chat/run method
        agent_name = self._get_agent_name(agent)

        # Simulate agent execution
        await asyncio.sleep(0.1)  # Simulate work

        return {
            "content": f"{agent_name} processed: {task[:100]}...",
            "status": "success",
        }

    def _get_agent_name(self, agent: Any) -> str:
        """Get agent name from agent instance."""
        if hasattr(agent, "name"):
            return agent.name
        elif hasattr(agent, "NAME"):
            return agent.NAME
        return f"Agent_{id(agent)}"
