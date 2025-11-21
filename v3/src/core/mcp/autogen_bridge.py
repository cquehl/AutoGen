"""
MCP-AutoGen Bridge

This module bridges MCP tools to AutoGen's agent tool system, converting
MCP tool definitions to AutoGen-compatible functions and handling execution.
"""

import asyncio
import inspect
import json
from typing import Any, Callable, Dict, List, Optional, Union
from functools import wraps
import logging

from .types import MCPTool, ToolParameter, ToolParameterType, ToolExecutionResult
from .manager import MCPManager, get_mcp_manager
from ..telemetry import LoggerMixin


class MCPAutoGenBridge(LoggerMixin):
    """
    Bridges MCP tools to AutoGen agent tools.

    Converts MCP tool definitions to AutoGen-compatible functions,
    handles parameter validation, and manages execution.
    """

    def __init__(self, mcp_manager: Optional[MCPManager] = None):
        """
        Initialize the bridge.

        Args:
            mcp_manager: Optional MCP manager instance
        """
        super().__init__()
        self.mcp_manager = mcp_manager or get_mcp_manager()
        self._converted_tools: Dict[str, Callable] = {}
        self._tool_metadata: Dict[str, MCPTool] = {}

    def convert_mcp_to_autogen_tool(self, mcp_tool: MCPTool, agent_name: Optional[str] = None) -> Callable:
        """
        Convert an MCP tool to an AutoGen-compatible function.

        Args:
            mcp_tool: MCP tool definition
            agent_name: Optional agent name for permissions

        Returns:
            AutoGen-compatible function
        """
        tool_name = mcp_tool.name

        # Check if already converted
        if tool_name in self._converted_tools:
            return self._converted_tools[tool_name]

        # Create the wrapper function
        @wraps(self._create_tool_function)
        async def tool_wrapper(**kwargs) -> Any:
            """AutoGen tool wrapper for MCP tool execution"""
            return await self._execute_mcp_tool(tool_name, kwargs, agent_name)

        # Add function metadata for AutoGen
        tool_wrapper.__name__ = tool_name.replace("-", "_").replace(".", "_")
        tool_wrapper.__doc__ = self._generate_docstring(mcp_tool)

        # Add parameter annotations for better AutoGen integration
        annotations = self._generate_annotations(mcp_tool)
        tool_wrapper.__annotations__ = annotations

        # Store for reuse
        self._converted_tools[tool_name] = tool_wrapper
        self._tool_metadata[tool_name] = mcp_tool

        self.logger.info(f"Converted MCP tool to AutoGen: {tool_name}")
        return tool_wrapper

    def create_tool_description(self, mcp_tool: MCPTool) -> Dict[str, Any]:
        """
        Generate a tool description for LLM understanding.

        Args:
            mcp_tool: MCP tool definition

        Returns:
            Tool description dictionary for LLM
        """
        # Create parameter schema
        parameters = {
            "type": "object",
            "properties": {},
            "required": []
        }

        for param in mcp_tool.parameters:
            param_schema = self._parameter_to_json_schema(param)
            parameters["properties"][param.name] = param_schema
            if param.required:
                parameters["required"].append(param.name)

        # Create function description for LLM
        description = {
            "name": mcp_tool.name,
            "description": mcp_tool.description,
            "parameters": parameters
        }

        # Add examples if available
        if mcp_tool.examples:
            description["examples"] = mcp_tool.examples

        return description

    def _parameter_to_json_schema(self, param: ToolParameter) -> Dict[str, Any]:
        """Convert a tool parameter to JSON schema"""
        schema: Dict[str, Any] = {
            "description": param.description
        }

        # Map parameter type
        type_mapping = {
            ToolParameterType.STRING: "string",
            ToolParameterType.NUMBER: "number",
            ToolParameterType.BOOLEAN: "boolean",
            ToolParameterType.OBJECT: "object",
            ToolParameterType.ARRAY: "array"
        }
        schema["type"] = type_mapping.get(param.type, "string")

        # Add constraints
        if param.enum:
            schema["enum"] = param.enum
        if param.pattern:
            schema["pattern"] = param.pattern
        if param.min_value is not None:
            schema["minimum"] = param.min_value
        if param.max_value is not None:
            schema["maximum"] = param.max_value
        if param.default is not None:
            schema["default"] = param.default

        return schema

    def _generate_docstring(self, mcp_tool: MCPTool) -> str:
        """Generate a docstring for the converted function"""
        lines = [mcp_tool.description, ""]

        if mcp_tool.parameters:
            lines.append("Parameters:")
            for param in mcp_tool.parameters:
                required = "" if param.required else " (optional)"
                lines.append(f"    {param.name}: {param.description}{required}")

        if mcp_tool.returns:
            lines.append("")
            lines.append("Returns:")
            lines.append(f"    {mcp_tool.returns}")

        if mcp_tool.examples:
            lines.append("")
            lines.append("Examples:")
            for example in mcp_tool.examples[:2]:  # Show max 2 examples
                lines.append(f"    {json.dumps(example, indent=8)}")

        return "\n".join(lines)

    def _generate_annotations(self, mcp_tool: MCPTool) -> Dict[str, type]:
        """Generate type annotations for the converted function"""
        annotations = {}

        for param in mcp_tool.parameters:
            # Map MCP types to Python types
            type_mapping = {
                ToolParameterType.STRING: str,
                ToolParameterType.NUMBER: float,
                ToolParameterType.BOOLEAN: bool,
                ToolParameterType.OBJECT: dict,
                ToolParameterType.ARRAY: list
            }
            param_type = type_mapping.get(param.type, Any)

            # Make optional if not required
            if not param.required:
                param_type = Optional[param_type]

            annotations[param.name] = param_type

        # Return type
        annotations["return"] = Any

        return annotations

    async def _execute_mcp_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        agent_name: Optional[str] = None
    ) -> Any:
        """
        Execute an MCP tool with given arguments.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments
            agent_name: Optional agent name for permissions

        Returns:
            Tool execution result
        """
        try:
            # Validate arguments
            if tool_name in self._tool_metadata:
                self._validate_arguments(self._tool_metadata[tool_name], arguments)

            # Execute via MCP manager
            result = await self.mcp_manager.execute_tool(
                tool_name=tool_name,
                arguments=arguments,
                agent_name=agent_name
            )

            # Return the result data
            if isinstance(result, ToolExecutionResult):
                if result.success:
                    return result.result
                else:
                    raise Exception(result.error_message or "Tool execution failed")
            else:
                return result

        except Exception as e:
            self.logger.error(f"MCP tool execution failed: {tool_name} - {e}")
            raise

    def _validate_arguments(self, tool: MCPTool, arguments: Dict[str, Any]) -> None:
        """Validate tool arguments against parameter definitions"""
        # Check required parameters
        for param in tool.parameters:
            if param.required and param.name not in arguments:
                raise ValueError(f"Missing required parameter: {param.name}")

            if param.name in arguments:
                value = arguments[param.name]

                # Type validation
                if param.type == ToolParameterType.STRING and not isinstance(value, str):
                    raise TypeError(f"Parameter {param.name} must be a string")
                elif param.type == ToolParameterType.NUMBER and not isinstance(value, (int, float)):
                    raise TypeError(f"Parameter {param.name} must be a number")
                elif param.type == ToolParameterType.BOOLEAN and not isinstance(value, bool):
                    raise TypeError(f"Parameter {param.name} must be a boolean")
                elif param.type == ToolParameterType.OBJECT and not isinstance(value, dict):
                    raise TypeError(f"Parameter {param.name} must be an object")
                elif param.type == ToolParameterType.ARRAY and not isinstance(value, list):
                    raise TypeError(f"Parameter {param.name} must be an array")

                # Value constraints
                if param.enum and value not in param.enum:
                    raise ValueError(f"Parameter {param.name} must be one of: {param.enum}")
                if param.min_value is not None and isinstance(value, (int, float)) and value < param.min_value:
                    raise ValueError(f"Parameter {param.name} must be >= {param.min_value}")
                if param.max_value is not None and isinstance(value, (int, float)) and value > param.max_value:
                    raise ValueError(f"Parameter {param.name} must be <= {param.max_value}")

        # Check for unknown parameters
        known_params = {p.name for p in tool.parameters}
        unknown_params = set(arguments.keys()) - known_params
        if unknown_params:
            self.logger.warning(f"Unknown parameters for {tool.name}: {unknown_params}")

    async def execute_with_retry(
        self,
        tool_func: Callable,
        args: Dict[str, Any],
        max_retries: int = 3,
        backoff_base: float = 2.0
    ) -> Any:
        """
        Execute a tool with retry logic.

        Args:
            tool_func: Tool function to execute
            args: Arguments for the tool
            max_retries: Maximum retry attempts
            backoff_base: Base for exponential backoff

        Returns:
            Tool execution result
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                # Execute the tool
                if asyncio.iscoroutinefunction(tool_func):
                    result = await tool_func(**args)
                else:
                    result = tool_func(**args)

                return result

            except Exception as e:
                last_error = e
                self.logger.warning(f"Tool execution attempt {attempt + 1} failed: {e}")

                if attempt < max_retries - 1:
                    # Calculate backoff time
                    wait_time = backoff_base ** attempt
                    self.logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)

        # All retries failed
        raise last_error or Exception("Tool execution failed after all retries")

    def create_autogen_tool_registry(
        self,
        agent_name: str,
        include_descriptions: bool = True
    ) -> Dict[str, Union[Callable, Dict]]:
        """
        Create a complete tool registry for an AutoGen agent.

        Args:
            agent_name: Name of the agent
            include_descriptions: Include tool descriptions for LLM

        Returns:
            Dictionary of tool functions and descriptions
        """
        registry = {}

        # Get available tools for this agent
        tools = asyncio.run(self.mcp_manager.list_tools(agent_name))

        for tool in tools:
            # Convert to AutoGen function
            func = self.convert_mcp_to_autogen_tool(tool, agent_name)
            registry[tool.name] = func

            # Add description if requested
            if include_descriptions:
                registry[f"{tool.name}_description"] = self.create_tool_description(tool)

        self.logger.info(f"Created AutoGen tool registry for {agent_name}: {len(tools)} tools")
        return registry

    def _create_tool_function(self, **kwargs) -> Any:
        """Placeholder function for tool wrapper creation"""
        raise NotImplementedError("This should be wrapped")


class AutoGenToolAdapter:
    """
    Adapter to make MCP tools compatible with AutoGen's tool system.

    This provides a simpler interface for AutoGen agents to use MCP tools.
    """

    def __init__(self, bridge: Optional[MCPAutoGenBridge] = None):
        """
        Initialize the adapter.

        Args:
            bridge: Optional bridge instance
        """
        self.bridge = bridge or MCPAutoGenBridge()
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_tools_for_agent(self, agent_name: str) -> List[Callable]:
        """
        Get list of tool functions for an AutoGen agent.

        Args:
            agent_name: Name of the agent

        Returns:
            List of callable tool functions
        """
        registry = self.bridge.create_autogen_tool_registry(agent_name, include_descriptions=False)
        return list(registry.values())

    def get_tool_descriptions(self, agent_name: str) -> List[Dict[str, Any]]:
        """
        Get tool descriptions for LLM understanding.

        Args:
            agent_name: Name of the agent

        Returns:
            List of tool descriptions
        """
        descriptions = []
        tools = asyncio.run(self.bridge.mcp_manager.list_tools(agent_name))

        for tool in tools:
            desc = self.bridge.create_tool_description(tool)
            descriptions.append(desc)

        return descriptions

    def register_with_agent(self, agent: Any, agent_name: str) -> None:
        """
        Register MCP tools with an AutoGen agent.

        Args:
            agent: AutoGen agent instance
            agent_name: Name of the agent
        """
        # Get tools for this agent
        tools = self.get_tools_for_agent(agent_name)

        # Register each tool with the agent
        for tool_func in tools:
            if hasattr(agent, "register_tool"):
                agent.register_tool(tool_func)
            elif hasattr(agent, "add_tool"):
                agent.add_tool(tool_func)
            else:
                self.logger.warning(f"Agent {agent_name} doesn't support tool registration")

        self.logger.info(f"Registered {len(tools)} MCP tools with agent {agent_name}")