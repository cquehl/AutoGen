#!/usr/bin/env python3
"""
Validation script for V2 architecture components.
Tests that all new V2 modules can be imported and basic functionality works.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_imports():
    """Test that all V2 modules can be imported."""
    print("Testing V2 module imports...")

    try:
        # Core modules
        from v2.core.container import Container, get_container
        print("✓ v2.core.container")

        from v2.core.base_agent import BaseAgent
        print("✓ v2.core.base_agent")

        from v2.core.base_tool import BaseTool
        print("✓ v2.core.base_tool")

        # Memory modules
        from v2.memory.agent_memory import AgentMemory, InMemoryStore, FileStore
        print("✓ v2.memory.agent_memory")

        from v2.memory.conversation_history import ConversationHistory
        print("✓ v2.memory.conversation_history")

        from v2.memory.state_manager import StateManager, AgentState
        print("✓ v2.memory.state_manager")

        # Messaging modules
        from v2.messaging.message_bus import MessageBus, Message
        print("✓ v2.messaging.message_bus")

        from v2.messaging.events import Event, EventType
        print("✓ v2.messaging.events")

        from v2.messaging.handlers import LoggingHandler, MetricsHandler
        print("✓ v2.messaging.handlers")

        # Workflow modules
        from v2.workflows.graph import WorkflowGraph, WorkflowNode, WorkflowEdge
        print("✓ v2.workflows.graph")

        from v2.workflows.executor import WorkflowExecutor, ExecutionContext
        print("✓ v2.workflows.executor")

        from v2.workflows.conditions import (
            MessageCountCondition,
            ContentCondition,
            StateCondition
        )
        print("✓ v2.workflows.conditions")

        # Team modules
        from v2.teams.base_team import BaseTeam
        print("✓ v2.teams.base_team")

        from v2.teams.graph_flow_team import GraphFlowTeam
        print("✓ v2.teams.graph_flow_team")

        from v2.teams.sequential_team import SequentialTeam
        print("✓ v2.teams.sequential_team")

        from v2.teams.swarm_team import SwarmTeam
        print("✓ v2.teams.swarm_team")

        print("\n✅ All imports successful!")
        return True

    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_basic_functionality():
    """Test basic functionality of key components."""
    print("\n" + "="*60)
    print("Testing basic functionality...")
    print("="*60)

    try:
        # Test 1: Memory system
        print("\n[1] Testing memory system...")
        from v2.memory.agent_memory import AgentMemory, InMemoryStore

        memory = AgentMemory("test_agent", store=InMemoryStore())
        await memory.save("key1", "value1")
        value = await memory.load("key1")
        assert value == "value1", f"Expected 'value1', got {value}"
        print("   ✓ Memory save/load works")

        # Test 2: Message bus
        print("\n[2] Testing message bus...")
        from v2.messaging.message_bus import MessageBus
        from v2.messaging.events import AgentMessageEvent, EventType

        bus = MessageBus()
        event_received = []

        async def handler(event):
            event_received.append(event)

        bus.subscribe(EventType.AGENT_MESSAGE, handler)

        await bus.publish(AgentMessageEvent(
            agent_name="test_agent",
            role="assistant",
            content="test message"
        ))

        # Give event loop a chance to process
        await asyncio.sleep(0.1)

        assert len(event_received) == 1, f"Expected 1 event, got {len(event_received)}"
        print("   ✓ Message bus pub/sub works")

        # Test 3: Workflow graph
        print("\n[3] Testing workflow graph...")
        from v2.workflows.graph import WorkflowGraph

        graph = WorkflowGraph()
        graph.add_node("node1", "Agent1")
        graph.add_node("node2", "Agent2")
        graph.add_edge("node1", "node2")

        successors = graph.get_successors("node1")
        assert "node2" in successors, f"Expected 'node2' in successors, got {successors}"
        print("   ✓ Workflow graph construction works")

        # Test 4: Graph validation
        print("\n[4] Testing graph validation...")
        try:
            graph.add_node("node1", "Agent1")  # Duplicate
            assert False, "Should have raised ValueError for duplicate node"
        except ValueError as e:
            print(f"   ✓ Duplicate node validation works: {e}")

        try:
            graph.add_edge("node1", "node1")  # Self-loop
            assert False, "Should have raised ValueError for self-loop"
        except ValueError as e:
            print(f"   ✓ Self-loop validation works: {e}")

        # Test 5: Container thread safety
        print("\n[5] Testing container singleton...")
        from v2.core.container import get_container, reset_container

        container1 = get_container()
        container2 = get_container()
        assert container1 is container2, "Container should be singleton"
        print("   ✓ Container singleton works")

        reset_container()
        container3 = get_container()
        assert container3 is not container1, "Reset should create new container"
        print("   ✓ Container reset works")

        # Test 6: File path validation
        print("\n[6] Testing path traversal prevention...")
        from v2.memory.agent_memory import FileStore
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileStore(base_path=tmpdir)

            try:
                # Try path traversal
                store._get_agent_file("../etc/passwd")
                assert False, "Should have blocked path traversal"
            except ValueError as e:
                print(f"   ✓ Path traversal blocked: {e}")

            try:
                # Try invalid characters
                store._get_agent_file("agent;rm -rf /")
                assert False, "Should have blocked invalid characters"
            except ValueError as e:
                print(f"   ✓ Invalid characters blocked: {e}")

        print("\n✅ All functionality tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_critical_fixes():
    """Verify that critical fixes are properly implemented."""
    print("\n" + "="*60)
    print("Verifying critical fixes...")
    print("="*60)

    try:
        # Fix 1: Async semaphore lazy initialization
        print("\n[1] Verifying async semaphore lazy initialization...")
        from v2.workflows.executor import WorkflowExecutor
        from v2.workflows.graph import WorkflowGraph
        from v2.agents.registry import AgentRegistry

        graph = WorkflowGraph()
        registry = AgentRegistry(settings=None, tool_registry=None)
        executor = WorkflowExecutor(graph, registry)

        # Semaphore should be None initially
        assert executor._semaphore is None, "Semaphore should be None initially"
        print("   ✓ Semaphore lazy initialization verified")

        # Fix 2: Datetime default factory
        print("\n[2] Verifying datetime default factory...")
        from v2.messaging.events import AgentMessageEvent
        import time

        event1 = AgentMessageEvent(agent_name="a1", role="user", content="test1")
        time.sleep(0.01)
        event2 = AgentMessageEvent(agent_name="a2", role="user", content="test2")

        # Timestamps should be different
        assert event1.timestamp != event2.timestamp, "Timestamps should be unique"
        print("   ✓ Datetime default factory verified")

        # Fix 3: Thread-safe container
        print("\n[3] Verifying thread-safe container...")
        from v2.core.container import get_container, reset_container
        import threading

        reset_container()
        containers = []

        def get_in_thread():
            containers.append(get_container())

        threads = [threading.Thread(target=get_in_thread) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads should get the same container
        assert all(c is containers[0] for c in containers), "All containers should be same instance"
        print("   ✓ Thread-safe container verified")

        # Fix 4: LRU cache with size limits
        print("\n[4] Verifying LRU cache with size limits...")
        from v2.memory.agent_memory import AgentMemory, InMemoryStore

        memory = AgentMemory("test", store=InMemoryStore(), max_cache_size=3)
        await memory.save("k1", "v1")
        await memory.save("k2", "v2")
        await memory.save("k3", "v3")
        await memory.save("k4", "v4")  # Should evict k1

        cache = memory.get_cache()
        assert len(cache) == 3, f"Cache should have 3 items, has {len(cache)}"
        assert "k1" not in cache, "Oldest item should be evicted"
        assert "k4" in cache, "Newest item should be in cache"
        print("   ✓ LRU cache verified")

        print("\n✅ All critical fixes verified!")
        return True

    except Exception as e:
        print(f"\n❌ Critical fix verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all validation tests."""
    print("="*60)
    print("V2 Architecture Validation")
    print("="*60)

    results = []

    # Test imports
    results.append(await test_imports())

    # Test basic functionality
    results.append(await test_basic_functionality())

    # Test critical fixes
    results.append(await test_critical_fixes())

    # Summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)

    total = len(results)
    passed = sum(results)
    failed = total - passed

    print(f"\nTotal test suites: {total}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")

    if all(results):
        print("\n🎉 ALL VALIDATION TESTS PASSED! V2 architecture is ready.")
        return 0
    else:
        print("\n⚠️  SOME VALIDATION TESTS FAILED. Please review the output above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
