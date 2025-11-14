"""
Development Team Agents - V2

Atomic, reusable agents for software development.
Each agent has ONE clear responsibility.

Agents:
- Coder: Writes implementation code
- Tester: Writes tests
- Reviewer: Reviews code and provides feedback

All agents share the same tool library for consistency.
"""

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from autogen_core.tools import FunctionTool

from agents.dev_tools import (
    read_source_file,
    write_source_file,
    run_tests,
    check_syntax,
    run_linter,
    list_files,
    get_file_structure,
)


# ============================================================================
# Shared Tool Library
# ============================================================================

def get_dev_tools():
    """Get the shared tool library for all dev agents."""
    return [
        FunctionTool(
            read_source_file,
            description="Read a source code file. Returns content, line count, and file type."
        ),
        FunctionTool(
            write_source_file,
            description="Write content to a source file. Creates backup automatically."
        ),
        FunctionTool(
            run_tests,
            description="Run pytest tests. Can run all tests or specific patterns."
        ),
        FunctionTool(
            check_syntax,
            description="Check Python file syntax without executing. Returns AST analysis."
        ),
        FunctionTool(
            run_linter,
            description="Run linter (pylint, flake8, or black) on a file."
        ),
        FunctionTool(
            list_files,
            description="List files matching a pattern. Supports recursive search."
        ),
        FunctionTool(
            get_file_structure,
            description="Get project directory structure as a tree."
        ),
    ]


# ============================================================================
# Atomic Agent Factories
# ============================================================================

def create_coder_agent(llm_config: dict) -> AssistantAgent:
    """
    Create a Coder agent.

    Responsibility: Write implementation code ONLY.
    - Focuses on clean, working code
    - Follows best practices
    - Does NOT write tests (that's Tester's job)
    - Does NOT review code (that's Reviewer's job)

    Args:
        llm_config: LLM configuration

    Returns:
        AssistantAgent configured as a Coder
    """
    system_message = """You are a Senior Software Engineer specialized in Python development.

**Your ONLY job is to write implementation code.**

Guidelines:
- Write clean, idiomatic Python code
- Use type hints for all function signatures
- Add docstrings to functions and classes
- Handle errors gracefully
- Follow PEP 8 style guidelines
- Keep functions focused and single-purpose

What you DO:
✓ Write implementation code
✓ Read existing code to understand context
✓ Check syntax before finalizing
✓ Use proper error handling

What you DON'T do:
✗ Write tests (Tester does this)
✗ Review code (Reviewer does this)
✗ Run linters (Reviewer does this)

When done with implementation, say: "IMPLEMENTATION_COMPLETE"
"""

    model_client = AzureOpenAIChatCompletionClient(
        azure_deployment=llm_config["model"],
        api_version=llm_config["api_version"],
        azure_endpoint=llm_config["azure_endpoint"],
        api_key=llm_config["api_key"],
        model_capabilities={
            "vision": True,
            "function_calling": True,
            "json_output": True,
        }
    )

    return AssistantAgent(
        name="Coder",
        model_client=model_client,
        tools=get_dev_tools(),
        system_message=system_message,
    )


def create_tester_agent(llm_config: dict) -> AssistantAgent:
    """
    Create a Tester agent.

    Responsibility: Write tests ONLY.
    - Writes comprehensive test cases
    - Covers edge cases and error conditions
    - Uses pytest best practices
    - Does NOT write implementation code

    Args:
        llm_config: LLM configuration

    Returns:
        AssistantAgent configured as a Tester
    """
    system_message = """You are a QA Engineer specialized in Python testing with pytest.

**Your ONLY job is to write tests.**

Guidelines:
- Write comprehensive test cases using pytest
- Cover normal cases, edge cases, and error conditions
- Use clear, descriptive test names
- Use fixtures for setup/teardown
- Test one thing per test function
- Add docstrings explaining what each test verifies

Test Structure:
```python
def test_feature_does_expected_thing():
    \"\"\"Test that feature X does Y when Z.\"\"\"
    # Arrange
    ...
    # Act
    ...
    # Assert
    ...
```

What you DO:
✓ Write test cases
✓ Read implementation code to understand what to test
✓ Run tests to verify they work
✓ Use pytest features (fixtures, parametrize, marks)

What you DON'T do:
✗ Write implementation code (Coder does this)
✗ Review code quality (Reviewer does this)
✗ Fix implementation bugs (report them instead)

When done with tests, say: "TESTS_COMPLETE"
"""

    model_client = AzureOpenAIChatCompletionClient(
        azure_deployment=llm_config["model"],
        api_version=llm_config["api_version"],
        azure_endpoint=llm_config["azure_endpoint"],
        api_key=llm_config["api_key"],
        model_capabilities={
            "vision": True,
            "function_calling": True,
            "json_output": True,
        }
    )

    return AssistantAgent(
        name="Tester",
        model_client=model_client,
        tools=get_dev_tools(),
        system_message=system_message,
    )


def create_reviewer_agent(llm_config: dict) -> AssistantAgent:
    """
    Create a Reviewer agent.

    Responsibility: Review code and provide feedback ONLY.
    - Reviews both implementation and tests
    - Checks for bugs, security issues, performance problems
    - Ensures code quality and best practices
    - Does NOT write code (suggests improvements instead)

    Args:
        llm_config: LLM configuration

    Returns:
        AssistantAgent configured as a Reviewer
    """
    system_message = """You are a Principal Engineer doing code review.

**Your ONLY job is to review code and provide feedback.**

Review Checklist:
1. **Correctness**: Does the code work as intended?
2. **Security**: Are there vulnerabilities (injection, SSRF, etc.)?
3. **Performance**: Are there obvious bottlenecks?
4. **Maintainability**: Is the code readable and well-organized?
5. **Testing**: Are tests comprehensive and meaningful?
6. **Style**: Does it follow Python best practices?

Review Format:
```
## Code Review

**✓ Strengths:**
- [What's good about this code]

**⚠️ Issues:**
- [Critical/Major/Minor issues found]

**💡 Suggestions:**
- [Improvements that could be made]

**Verdict:** APPROVE | REQUEST_CHANGES
```

What you DO:
✓ Read implementation and test code
✓ Check syntax and run linters
✓ Run tests to verify they pass
✓ Provide specific, actionable feedback
✓ Approve when code meets quality standards

What you DON'T do:
✗ Write code yourself (suggest changes instead)
✗ Make changes directly (request them)

When done reviewing, say: "REVIEW_COMPLETE" and your verdict (APPROVE or REQUEST_CHANGES)
"""

    model_client = AzureOpenAIChatCompletionClient(
        azure_deployment=llm_config["model"],
        api_version=llm_config["api_version"],
        azure_endpoint=llm_config["azure_endpoint"],
        api_key=llm_config["api_key"],
        model_capabilities={
            "vision": True,
            "function_calling": True,
            "json_output": True,
        }
    )

    return AssistantAgent(
        name="Reviewer",
        model_client=model_client,
        tools=get_dev_tools(),
        system_message=system_message,
    )


# ============================================================================
# Team Factory
# ============================================================================

async def create_dev_team(llm_config: dict, mode: str = "full") -> RoundRobinGroupChat:
    """
    Create a development team.

    Args:
        llm_config: LLM configuration from config.settings
        mode: Team composition mode
            - "full": Coder + Tester + Reviewer (complete workflow)
            - "code": Just Coder (quick implementation)
            - "test": Coder + Tester (implement + test)
            - "review": Coder + Reviewer (implement + review)

    Returns:
        RoundRobinGroupChat team configured for development

    Example:
        ```python
        # Full team for complete feature development
        team = await create_dev_team(llm_config, mode="full")
        await team.run(task="Add rate limiting to web_tools.py")

        # Quick implementation only
        team = await create_dev_team(llm_config, mode="code")
        await team.run(task="Write a function to parse RSS feeds")

        # Implementation + testing
        team = await create_dev_team(llm_config, mode="test")
        await team.run(task="Create a configuration validator")
        ```
    """

    # Create agents based on mode
    coder = create_coder_agent(llm_config)

    if mode == "code":
        agents = [coder]
        termination_keyword = "IMPLEMENTATION_COMPLETE"

    elif mode == "test":
        tester = create_tester_agent(llm_config)
        agents = [coder, tester]
        termination_keyword = "TESTS_COMPLETE"

    elif mode == "review":
        reviewer = create_reviewer_agent(llm_config)
        agents = [coder, reviewer]
        termination_keyword = "APPROVE"

    else:  # mode == "full"
        tester = create_tester_agent(llm_config)
        reviewer = create_reviewer_agent(llm_config)
        agents = [coder, tester, reviewer]
        termination_keyword = "APPROVE"

    # Termination conditions
    termination = TextMentionTermination(termination_keyword) | MaxMessageTermination(20)

    # Create team
    team = RoundRobinGroupChat(
        agents,
        termination_condition=termination,
    )

    return team


# ============================================================================
# Specialized Teams (Pre-configured)
# ============================================================================

async def create_quick_coder(llm_config: dict):
    """Quick code implementation - just the Coder."""
    return await create_dev_team(llm_config, mode="code")


async def create_code_and_test_team(llm_config: dict):
    """Code + Test - Coder and Tester working together."""
    return await create_dev_team(llm_config, mode="test")


async def create_full_dev_team(llm_config: dict):
    """Full development workflow - Coder, Tester, Reviewer."""
    return await create_dev_team(llm_config, mode="full")
