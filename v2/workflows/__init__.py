"""
Workflow engine for AutoGen V2.

Provides graph-based workflow orchestration inspired by AutoGen 0.7.x GraphFlow.
"""

from .graph import WorkflowGraph, WorkflowNode
from .executor import WorkflowExecutor
from .conditions import Condition, MessageCountCondition, ContentCondition

__all__ = [
    "WorkflowGraph",
    "WorkflowNode",
    "WorkflowExecutor",
    "Condition",
    "MessageCountCondition",
    "ContentCondition",
]
