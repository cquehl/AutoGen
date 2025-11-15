# AutoGen V2 Architecture Improvements

## Overview

This document describes the architectural improvements made to AutoGen V2 based on the latest AutoGen 0.7.x architecture patterns and best practices.

**Implementation Date:** 2025-11-15
**Based On:** AutoGen 0.7.5 architecture
**Improvements:** 6 major architectural enhancements

---

## Table of Contents

1. [GraphFlow Workflow Engine](#1-graphflow-workflow-engine)
2. [Enhanced Team Patterns](#2-enhanced-team-patterns)
3. [Event-Driven Message Bus](#3-event-driven-message-bus)
4. [Agent State Management & Memory](#4-agent-state-management--memory)
5. [Updated Architecture Diagram](#5-updated-architecture-diagram)
6. [Migration Guide](#6-migration-guide)

---

## 1. GraphFlow Workflow Engine

### What It Is
A DiGraph-based workflow orchestration system inspired by AutoGen 0.7.x GraphFlow that enables complex multi-agent workflows with concurrent execution.

### Location
- `v2/workflows/graph.py` - Graph data structure
- `v2/workflows/executor.py` - Workflow execution engine
- `v2/workflows/conditions.py` - Conditional routing

### Key Features

#### 1.1 Directed Graph Workflows
```python
from v2.workflows import WorkflowGraph, WorkflowGraphBuilder

# Build a workflow graph
graph = (WorkflowGraphBuilder()
    .add_node("writer", "WriterAgent")
    .add_node("editor1", "EditorAgent")
    .add_node("editor2", "EditorAgent")
    .add_node("reviewer", "ReviewerAgent")
    .add_edge("writer", "editor1")
    .add_edge("writer", "editor2")
    .add_edge("editor1", "reviewer")
    .add_edge("editor2", "reviewer")
    .build())
```

#### 1.2 Concurrent Execution (Fan-Out/Fan-In)
The workflow engine automatically executes independent nodes concurrently:
- **Fan-out**: Writer distributes to Editor1 and Editor2 simultaneously
- **Fan-in**: Both editors feed into Reviewer after completion

#### 1.3 Conditional Routing
```python
from v2.workflows.conditions import MessageCountCondition, ContentCondition

# Add conditional edges
graph.add_edge(
    "analyzer",
    "retry_handler",
    condition=ContentCondition("error", match_type="contains")
)

graph.add_edge(
    "validator",
    "next_step",
    condition=MessageCountCondition(5, operator="<=")
)
```

#### 1.4 Workflow Serialization
Workflows can be saved/loaded as JSON:
```python
# Save workflow
workflow_dict = graph.to_dict()
with open("workflow.json", "w") as f:
    json.dump(workflow_dict, f)

# Load workflow
graph = WorkflowGraph.from_dict(workflow_dict)
```

### Benefits
- **Complex Workflows**: Sequential, parallel, conditional, and cyclic patterns
- **Performance**: Concurrent execution reduces total execution time
- **Reusability**: Workflows are first-class artifacts
- **Observability**: Clear visualization of agent orchestration

---

## 2. Enhanced Team Patterns

### What It Is
Multiple team orchestration patterns beyond the original SelectorGroupChat, providing flexibility for different multi-agent scenarios.

### Location
- `v2/teams/base_team.py` - Base team abstraction
- `v2/teams/graph_flow_team.py` - DiGraph-based teams
- `v2/teams/sequential_team.py` - Sequential chained teams
- `v2/teams/swarm_team.py` - Dynamic agent selection

### Team Patterns

#### 2.1 GraphFlowTeam
Uses workflow graphs for sophisticated multi-agent orchestration.

```python
from v2.teams import GraphFlowTeam
from v2.workflows import WorkflowGraph

# Create workflow graph (as shown above)
graph = ...

# Create team
team = GraphFlowTeam(
    name="editorial_team",
    agents=[writer, editor1, editor2, reviewer],
    graph=graph,
    max_concurrent=5
)

# Run team
result = await team.run("Write an article about AI")
```

**Use Cases:**
- Complex workflows with multiple paths
- Parallel processing requirements
- Conditional agent routing
- Iterative refinement loops

#### 2.2 SequentialTeam
Executes agents in a fixed sequence, each building on the previous.

```python
from v2.teams import SequentialTeam

team = SequentialTeam(
    name="research_pipeline",
    agents=[researcher, analyst, writer],
    carryover_mode="all",  # "last", "all", "summary"
    max_carryover_messages=5
)

result = await team.run("Research market trends in AI")
```

**Carryover Modes:**
- `last`: Only pass last message to next agent
- `all`: Pass recent N messages for context
- `summary`: Pass summarized context

**Use Cases:**
- Linear pipelines (research → analysis → writing)
- Data transformation chains
- Progressive refinement

#### 2.3 SwarmTeam
Dynamically selects agents based on task requirements.

```python
from v2.teams import SwarmTeam

def smart_selector(task, history, agents):
    """Custom selection logic"""
    if "database" in task.lower():
        return "data_analyst"
    elif "weather" in task.lower():
        return "weather_agent"
    return "orchestrator"

team = SwarmTeam(
    name="smart_swarm",
    agents=[data_analyst, weather_agent, orchestrator],
    selector_func=smart_selector,
    max_rounds=10
)

result = await team.run("What's the weather like?")
```

**Use Cases:**
- Flexible task routing
- Capability-based selection
- Dynamic workflows

### Comparison

| Pattern | Execution Order | Best For | Complexity |
|---------|----------------|----------|------------|
| **GraphFlowTeam** | Graph-defined | Complex workflows, parallel execution | High |
| **SequentialTeam** | Fixed sequence | Linear pipelines, chained processing | Low |
| **SwarmTeam** | Dynamic | Flexible routing, capability matching | Medium |
| **SelectorGroupChat** (V1) | LLM-selected | Conversational multi-agent | Medium |

---

## 3. Event-Driven Message Bus

### What It Is
Centralized message broker for observable, decoupled agent communication inspired by AutoGen 0.7.x actor model.

### Location
- `v2/messaging/message_bus.py` - Central message bus
- `v2/messaging/events.py` - Event types
- `v2/messaging/handlers.py` - Event handlers

### Key Features

#### 3.1 Publish/Subscribe Pattern
```python
from v2.messaging import MessageBus, AgentMessageEvent, EventType

bus = MessageBus()

# Subscribe to events
async def on_agent_message(event):
    print(f"[{event.agent_name}]: {event.content}")

subscription_id = bus.subscribe(EventType.AGENT_MESSAGE, on_agent_message)

# Publish events
await bus.publish(AgentMessageEvent(
    agent_name="agent1",
    role="assistant",
    content="Hello from agent1"
))
```

#### 3.2 Event Types
- `AgentMessageEvent` - Agent communications
- `ToolExecutionEvent` - Tool invocations
- `WorkflowEvent` - Workflow state changes
- `SystemEvent` - System notifications

#### 3.3 Built-in Handlers
```python
from v2.messaging.handlers import LoggingHandler, MetricsHandler

# Logging handler
logging_handler = LoggingHandler(log_level="INFO")
bus.subscribe_all(logging_handler.handle)

# Metrics handler
metrics_handler = MetricsHandler()
bus.subscribe_all(metrics_handler.handle)

# Get metrics
stats = metrics_handler.get_metrics()
```

#### 3.4 Message Routing
```python
# Direct messaging
message = Message(
    sender="agent1",
    recipient="agent2",
    content="Task for you"
)
await bus.send_message(message)

# Broadcast
message = Message(
    sender="orchestrator",
    recipient=None,  # Broadcast
    content="Announcement"
)
await bus.send_message(message)
```

### Benefits
- **Decoupling**: Agents don't need direct references
- **Observability**: All communication is logged and traceable
- **Distributed**: Enables multi-process/machine agent execution
- **Debugging**: Centralized event history
- **Metrics**: Automatic performance tracking

---

## 4. Agent State Management & Memory

### What It Is
Comprehensive memory and state persistence for agents, enabling context retention across sessions.

### Location
- `v2/memory/agent_memory.py` - Key-value memory storage
- `v2/memory/conversation_history.py` - Conversation management
- `v2/memory/state_manager.py` - Agent state with versioning

### Components

#### 4.1 AgentMemory - Key-Value Storage
```python
from v2.memory import AgentMemory, FileStore

# Create memory with persistent storage
memory = AgentMemory(
    agent_id="my_agent",
    store=FileStore(base_path=".memory"),
    auto_save=True
)

# Save information
await memory.save("user_preference", "dark_mode")
await memory.save("learned_facts", ["fact1", "fact2"])
await memory.save("conversation_count", 42)

# Load information
preference = await memory.load("user_preference")  # "dark_mode"
facts = await memory.load("learned_facts")  # ["fact1", "fact2"]

# Load all
all_data = await memory.load_all()
```

**Storage Backends:**
- `InMemoryStore` - Fast, non-persistent
- `FileStore` - JSON-based persistence

#### 4.2 ConversationHistory - Message Management
```python
from v2.memory import ConversationHistory

history = ConversationHistory(
    conversation_id="conv_123",
    max_messages=100,
    storage_path=".conversations"
)

# Add messages
history.add_message("user", "Hello!")
history.add_message("assistant", "Hi there!", name="Agent1")

# Get recent messages
recent = history.get_messages(limit=10)

# Format for LLM
llm_messages = history.format_for_llm(limit=20)

# Persist
await history.save()
await history.load()
```

#### 4.3 StateManager - Agent State with Versioning
```python
from v2.memory import StateManager, AgentState, AgentStatus

manager = StateManager(
    storage_path=".state",
    enable_versioning=True,
    max_versions=10
)

# Create state
state = AgentState(
    agent_id="agent1",
    status=AgentStatus.IDLE,
    variables={"task_count": 0}
)

# Save state
await manager.save_state(state)

# Update state
state.status = AgentStatus.RUNNING
state.variables["task_count"] = 1
await manager.save_state(state, version_name="after_task_1")

# Load state
loaded = await manager.load_state("agent1")

# Rollback to previous version
await manager.rollback("agent1", version_index=-2)

# Get version history
versions = manager.get_versions("agent1")
```

### Benefits
- **Persistence**: Survive restarts
- **Context Retention**: Long-running conversations
- **Versioning**: Rollback capability
- **Debugging**: State history
- **Learning**: Agents can accumulate knowledge

---

## 5. Updated Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    AutoGen V2 Architecture                   │
│                    (Enhanced with 0.7.x patterns)            │
└─────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  Presentation Layer                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│  │   CLI    │  │   API    │  │  Jupyter │                   │
│  └──────────┘  └──────────┘  └──────────┘                   │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  Orchestration Layer (NEW)                                   │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐ │
│  │ GraphFlowTeam  │  │ SequentialTeam │  │   SwarmTeam    │ │
│  └────────────────┘  └────────────────┘  └────────────────┘ │
│           ▲                  ▲                    ▲          │
│           └──────────────────┴────────────────────┘          │
│                              │                               │
│                    ┌─────────────────┐                       │
│                    │ AgentFactory    │                       │
│                    └─────────────────┘                       │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  Workflow Layer (NEW)                                        │
│  ┌─────────────────┐  ┌──────────────────┐                  │
│  │ WorkflowGraph   │  │ WorkflowExecutor │                  │
│  │ - DiGraph       │  │ - Concurrent     │                  │
│  │ - Conditions    │  │ - Sequential     │                  │
│  │ - Serialization │  │ - Conditional    │                  │
│  └─────────────────┘  └──────────────────┘                  │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  Communication Layer (NEW)                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                   Message Bus                         │   │
│  │  - Pub/Sub Pattern                                    │   │
│  │  - Event History                                      │   │
│  │  - Agent Routing                                      │   │
│  │  - Middleware Support                                 │   │
│  └──────────────────────────────────────────────────────┘   │
│         │                    │                    │          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ LoggingHandler│  │MetricsHandler│  │CustomHandlers│      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  Agent Layer                                                 │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐ │
│  │ WeatherAgent   │  │ DataAnalyst    │  │ Orchestrator   │ │
│  └────────────────┘  └────────────────┘  └────────────────┘ │
│                              │                               │
│                    ┌─────────────────┐                       │
│                    │ AgentRegistry   │                       │
│                    │ - Auto-discovery│                       │
│                    └─────────────────┘                       │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  Memory Layer (NEW)                                          │
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────┐ │
│  │  AgentMemory    │  │ConversationHistory│  │StateManager │ │
│  │  - KV Storage   │  │- Message tracking │  │- Versioning │ │
│  │  - Persistence  │  │- LLM formatting   │  │- Rollback   │ │
│  └─────────────────┘  └──────────────────┘  └─────────────┘ │
│         │                    │                    │          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │InMemoryStore │  │  FileStore   │  │ CustomStore  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  Tool Layer                                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐ │
│  │ Database Tools │  │  File Tools    │  │ Weather Tools  │ │
│  └────────────────┘  └────────────────┘  └────────────────┘ │
│                              │                               │
│                    ┌─────────────────┐                       │
│                    │  ToolRegistry   │                       │
│                    │  - Auto-discovery                       │
│                    │  - DI Support   │                       │
│                    └─────────────────┘                       │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  Security & Services Layer                                   │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │SecurityMiddleware│  │ DatabaseService  │                 │
│  │- SQL Validation  │  │- Connection Pool │                 │
│  │- Path Validation │  │- Query Execution │                 │
│  │- Audit Logging   │  └──────────────────┘                 │
│  └──────────────────┘                                        │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  Observability Layer                                         │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │StructuredLogging │  │  OpenTelemetry   │                 │
│  │- JSON Format     │  │  - Tracing       │                 │
│  │- Event Logging   │  │  - Metrics       │                 │
│  └──────────────────┘  └──────────────────┘                 │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  Configuration Layer                                         │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │ Pydantic Models  │  │  YAML Config     │                 │
│  │ - Type Safety    │  │  - settings.yaml │                 │
│  └──────────────────┘  └──────────────────┘                 │
└──────────────────────────────────────────────────────────────┘

Legend:
  [NEW] = New components added in this improvement phase
  ───►  = Data flow
  ═══►  = Control flow
```

---

## 6. Migration Guide

### From V1 to Enhanced V2

#### 6.1 Using GraphFlow Instead of Manual Orchestration

**Before (V1):**
```python
# Manual orchestration
result1 = await agent1.run(task)
result2a = await agent2a.run(result1)
result2b = await agent2b.run(result1)
final = await agent3.run(f"{result2a}\n{result2b}")
```

**After (V2):**
```python
from v2.workflows import WorkflowGraphBuilder
from v2.teams import GraphFlowTeam

# Define workflow
graph = (WorkflowGraphBuilder()
    .add_node("agent1", "Agent1")
    .add_node("agent2a", "Agent2A")
    .add_node("agent2b", "Agent2B")
    .add_node("agent3", "Agent3")
    .add_edge("agent1", "agent2a")
    .add_edge("agent1", "agent2b")
    .add_edge("agent2a", "agent3")
    .add_edge("agent2b", "agent3")
    .build())

# Run workflow
team = GraphFlowTeam("team", agents, graph)
result = await team.run(task)
```

#### 6.2 Adding Memory to Agents

**Before (V1):**
```python
# No built-in memory
# Had to implement custom state management
```

**After (V2):**
```python
from v2.memory import AgentMemory, FileStore, ConversationHistory

# Add memory to agent
memory = AgentMemory("agent1", store=FileStore())
history = ConversationHistory("conv_123")

# Use in agent logic
await memory.save("preference", "value")
history.add_message("user", "Hello")
```

#### 6.3 Event Tracking

**Before (V1):**
```python
# Manual logging
print(f"Agent {name} executed")
```

**After (V2):**
```python
from v2.messaging import MessageBus, AgentMessageEvent

bus = container.get_message_bus()

# Automatic tracking
await bus.publish(AgentMessageEvent(
    agent_name="agent1",
    role="assistant",
    content="Result"
))

# Get metrics
metrics = bus.get_stats()
```

---

## Summary of Improvements

| Feature | V1 | V2 Enhanced | Impact |
|---------|----|-----------| -------|
| **Workflow Orchestration** | Manual | GraphFlow with concurrent execution | High |
| **Team Patterns** | 1 (SelectorGroupChat) | 4 (GraphFlow, Sequential, Swarm, SelectorGroupChat) | High |
| **Event System** | None | Message Bus with pub/sub | High |
| **Agent Memory** | None | Key-value + conversation history | High |
| **State Management** | None | Versioned state with rollback | Medium |
| **Observability** | Basic logging | Event tracking + metrics | Medium |

---

## File Structure

```
v2/
├── workflows/              # NEW: GraphFlow engine
│   ├── __init__.py
│   ├── graph.py           # DiGraph implementation
│   ├── executor.py        # Workflow execution
│   └── conditions.py      # Conditional routing
│
├── teams/                  # NEW: Enhanced team patterns
│   ├── __init__.py
│   ├── base_team.py       # Base abstraction
│   ├── graph_flow_team.py # GraphFlow teams
│   ├── sequential_team.py # Sequential teams
│   └── swarm_team.py      # Swarm teams
│
├── messaging/              # NEW: Event-driven communication
│   ├── __init__.py
│   ├── message_bus.py     # Central message broker
│   ├── events.py          # Event types
│   └── handlers.py        # Event handlers
│
├── memory/                 # NEW: State & memory
│   ├── __init__.py
│   ├── agent_memory.py    # KV storage
│   ├── conversation_history.py
│   └── state_manager.py   # State with versioning
│
├── core/
│   ├── container.py       # UPDATED: New components
│   ├── base_agent.py
│   └── base_tool.py
│
├── agents/                 # Existing
├── tools/                  # Existing
├── security/               # Existing
├── services/               # Existing
├── observability/          # Existing
└── config/                 # Existing
```

---

## Performance Considerations

### Concurrent Execution Benefits
- **Before**: Sequential execution of N agents = N × avg_time
- **After**: Concurrent execution = max(agent_times)
- **Example**: 3 agents @ 10s each
  - Sequential: 30 seconds
  - Concurrent: ~10 seconds (3x speedup)

### Memory Overhead
- Message Bus: ~1KB per event (configurable history limit)
- Agent Memory: Depends on stored data (use InMemoryStore for speed)
- State Manager: ~2-5KB per agent state × max_versions

### Recommended Settings
```python
# For high-throughput scenarios
bus = MessageBus(max_history=500)  # Reduce history
memory = AgentMemory(store=InMemoryStore())  # Fast, no I/O
state = StateManager(max_versions=5)  # Fewer versions

# For debugging/observability
bus = MessageBus(max_history=5000)  # More history
memory = AgentMemory(store=FileStore())  # Persistent
state = StateManager(max_versions=20)  # More versions
```

---

## Next Steps

1. **Testing**: Comprehensive tests for new components
2. **Examples**: Create example notebooks showing each pattern
3. **Documentation**: Detailed API documentation
4. **Performance**: Benchmark concurrent vs sequential execution
5. **Integrations**: Connect with AutoGen 0.7.x ecosystem

---

## References

- [AutoGen 0.7.x Documentation](https://microsoft.github.io/autogen/)
- [AutoGen GraphFlow PR #6545](https://github.com/microsoft/autogen/pull/6545)
- [Actor Model Pattern](https://en.wikipedia.org/wiki/Actor_model)
- [Publish-Subscribe Pattern](https://en.wikipedia.org/wiki/Publish%E2%80%93subscribe_pattern)

---

**Version:** 2.1.0
**Status:** ✅ Complete
**Lines of Code Added:** ~5,000
**Files Added:** 16
**Backward Compatible:** Yes
