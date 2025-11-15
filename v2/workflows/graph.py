"""
Directed graph implementation for workflow orchestration.

Inspired by AutoGen 0.7.x GraphFlow pattern.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any, Callable
import networkx as nx
from enum import Enum


class ExecutionMode(Enum):
    """Execution mode for workflow nodes."""
    SEQUENTIAL = "sequential"  # Execute one at a time
    CONCURRENT = "concurrent"  # Execute multiple nodes in parallel


@dataclass
class WorkflowEdge:
    """Represents an edge in the workflow graph."""
    source: str
    target: str
    condition: Optional[Callable[[Any], bool]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowNode:
    """Represents a node in the workflow graph."""
    name: str
    agent_name: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, WorkflowNode):
            return self.name == other.name
        return False


class WorkflowGraph:
    """
    Directed graph for workflow orchestration.

    Supports:
    - Sequential execution
    - Concurrent execution (fan-out/fan-in)
    - Conditional routing
    - Cycles (for iterative workflows)

    Example:
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
    """

    def __init__(self):
        """Initialize an empty workflow graph."""
        self._graph = nx.DiGraph()
        self._nodes: Dict[str, WorkflowNode] = {}
        self._edges: List[WorkflowEdge] = []

    def add_node(self, node_name: str, agent_name: str, **metadata) -> "WorkflowGraph":
        """
        Add a node to the workflow graph.

        Args:
            node_name: Unique identifier for the node
            agent_name: Name of the agent to use for this node
            **metadata: Additional metadata for the node

        Returns:
            Self for method chaining

        Raises:
            ValueError: If node with same name already exists
        """
        if node_name in self._nodes:
            raise ValueError(f"Node '{node_name}' already exists in graph")

        node = WorkflowNode(name=node_name, agent_name=agent_name, metadata=metadata)
        self._nodes[node_name] = node
        self._graph.add_node(node_name, node=node)
        return self

    def add_edge(
        self,
        source: str,
        target: str,
        condition: Optional[Callable[[Any], bool]] = None,
        **metadata
    ) -> "WorkflowGraph":
        """
        Add an edge between two nodes.

        Args:
            source: Source node name
            target: Target node name
            condition: Optional condition function that must return True for edge to be traversed
            **metadata: Additional metadata for the edge

        Returns:
            Self for method chaining

        Raises:
            ValueError: If source or target node doesn't exist or if self-loop detected
        """
        if source not in self._nodes:
            raise ValueError(f"Source node '{source}' not found in graph")
        if target not in self._nodes:
            raise ValueError(f"Target node '{target}' not found in graph")
        if source == target:
            raise ValueError(f"Self-loops not allowed: {source} -> {target}")

        edge = WorkflowEdge(source=source, target=target, condition=condition, metadata=metadata)
        self._edges.append(edge)
        self._graph.add_edge(source, target, edge=edge)
        return self

    def get_node(self, node_name: str) -> Optional[WorkflowNode]:
        """Get a node by name."""
        return self._nodes.get(node_name)

    def get_successors(self, node_name: str) -> List[str]:
        """Get all successor nodes for a given node."""
        return list(self._graph.successors(node_name))

    def get_predecessors(self, node_name: str) -> List[str]:
        """Get all predecessor nodes for a given node."""
        return list(self._graph.predecessors(node_name))

    def get_edges_from(self, node_name: str) -> List[WorkflowEdge]:
        """Get all edges originating from a node."""
        edges = []
        for successor in self.get_successors(node_name):
            edge_data = self._graph.get_edge_data(node_name, successor)
            if edge_data:
                edges.append(edge_data["edge"])
        return edges

    def get_entry_nodes(self) -> List[str]:
        """Get nodes with no predecessors (entry points)."""
        return [node for node in self._nodes.keys() if self._graph.in_degree(node) == 0]

    def get_exit_nodes(self) -> List[str]:
        """Get nodes with no successors (exit points)."""
        return [node for node in self._nodes.keys() if self._graph.out_degree(node) == 0]

    def is_cyclic(self) -> bool:
        """Check if the graph contains cycles."""
        try:
            nx.find_cycle(self._graph)
            return True
        except nx.NetworkXNoCycle:
            return False

    def topological_sort(self) -> List[str]:
        """
        Return nodes in topological order.

        Raises:
            ValueError: If graph contains cycles
        """
        if self.is_cyclic():
            raise ValueError("Cannot perform topological sort on a graph with cycles")
        return list(nx.topological_sort(self._graph))

    def validate(self) -> List[str]:
        """
        Validate the workflow graph.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check for disconnected components
        if not nx.is_weakly_connected(self._graph):
            errors.append("Graph contains disconnected components")

        # Check for entry nodes
        entry_nodes = self.get_entry_nodes()
        if not entry_nodes:
            errors.append("Graph has no entry nodes (all nodes have predecessors)")

        # Check for exit nodes (warning, not error)
        exit_nodes = self.get_exit_nodes()
        if not exit_nodes and not self.is_cyclic():
            errors.append("Graph has no exit nodes (all nodes have successors)")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the graph to a dictionary."""
        return {
            "nodes": [
                {
                    "name": node.name,
                    "agent_name": node.agent_name,
                    "metadata": node.metadata,
                }
                for node in self._nodes.values()
            ],
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "metadata": edge.metadata,
                    # Note: conditions are not serialized (would need custom serialization)
                }
                for edge in self._edges
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowGraph":
        """Deserialize a graph from a dictionary."""
        graph = cls()

        # Add nodes
        for node_data in data["nodes"]:
            graph.add_node(
                node_data["name"],
                node_data["agent_name"],
                **node_data.get("metadata", {})
            )

        # Add edges
        for edge_data in data["edges"]:
            graph.add_edge(
                edge_data["source"],
                edge_data["target"],
                **edge_data.get("metadata", {})
            )

        return graph

    def __repr__(self) -> str:
        return f"WorkflowGraph(nodes={len(self._nodes)}, edges={len(self._edges)})"


class WorkflowGraphBuilder:
    """
    Builder pattern for constructing workflow graphs.

    Example:
        >>> builder = WorkflowGraphBuilder()
        >>> graph = (builder
        ...     .add_node("start", "InitAgent")
        ...     .add_node("process", "ProcessAgent")
        ...     .add_node("end", "EndAgent")
        ...     .add_edge("start", "process")
        ...     .add_edge("process", "end")
        ...     .build())
    """

    def __init__(self):
        """Initialize the builder."""
        self._graph = WorkflowGraph()

    def add_node(self, node_name: str, agent_name: str, **metadata) -> "WorkflowGraphBuilder":
        """Add a node to the graph."""
        self._graph.add_node(node_name, agent_name, **metadata)
        return self

    def add_edge(
        self,
        source: str,
        target: str,
        condition: Optional[Callable[[Any], bool]] = None,
        **metadata
    ) -> "WorkflowGraphBuilder":
        """Add an edge to the graph."""
        self._graph.add_edge(source, target, condition, **metadata)
        return self

    def build(self) -> WorkflowGraph:
        """Build and validate the workflow graph."""
        errors = self._graph.validate()
        if errors:
            raise ValueError(f"Invalid workflow graph: {', '.join(errors)}")
        return self._graph
