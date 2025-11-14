# Development Team - V2

**Atomic, reusable agents for software development tasks.**

## Design Philosophy

### ✨ V2 Improvements

**Atomic Agents:**
- Each agent has ONE clear responsibility
- No overlapping duties
- Easy to understand and predict

**Reusable Tools:**
- Shared tool library used by all agents
- Consistent behavior across agents
- Easy to extend with new tools

**Composable Teams:**
- Mix and match agents for different workflows
- Scale from quick coding to full development
- Flexible team modes

## Agents

### 👨‍💻 Coder
**Responsibility:** Write implementation code ONLY

- Writes clean, idiomatic Python code
- Uses type hints and docstrings
- Handles errors gracefully
- Follows PEP 8 guidelines
- Does NOT write tests or review code

### 🧪 Tester
**Responsibility:** Write tests ONLY

- Writes comprehensive pytest test cases
- Covers edge cases and error conditions
- Uses fixtures and parametrize
- Does NOT write implementation code
- Runs tests to verify they work

### 👀 Reviewer
**Responsibility:** Review code and provide feedback ONLY

- Reviews implementation and tests
- Checks for bugs, security, performance
- Ensures code quality and best practices
- Does NOT write code (suggests changes)
- Approves or requests changes

## Team Modes

### 🚀 dev-quick (Coder only)
**Use for:** Quick implementation without tests/review

```bash
./cli.py --team dev-quick "Write a function to validate email addresses"
```

**Workflow:**
1. Coder writes implementation
2. Done ✓

**Best for:**
- Prototypes
- Quick scripts
- Exploratory code

### 🔬 dev-test (Coder + Tester)
**Use for:** Implementation with testing

```bash
./cli.py --team dev-test "Create a configuration validator for .env files"
```

**Workflow:**
1. Coder writes implementation
2. Tester writes comprehensive tests
3. Tester runs tests
4. Done ✓

**Best for:**
- New features
- Utility functions
- Library code

### ✅ dev (Full: Coder + Tester + Reviewer)
**Use for:** Complete development workflow

```bash
./cli.py --team dev "Add rate limiting to web_tools.py"
```

**Workflow:**
1. Coder writes implementation
2. Tester writes tests
3. Reviewer checks both
4. Reviewer approves or requests changes
5. Done ✓

**Best for:**
- Production features
- Critical code
- Security-sensitive changes

## Shared Tool Library

All agents have access to these tools:

### 📖 read_source_file
Read source code with metadata
```python
result = await read_source_file("agents/web_tools.py")
# Returns: content, lines, file_type, path
```

### ✏️ write_source_file
Write code (creates automatic backup)
```python
result = await write_source_file("new_feature.py", code_content)
# Creates: new_feature.py + new_feature.py.bak
```

### 🧪 run_tests
Run pytest with options
```python
result = await run_tests("tests/", pattern="test_*.py", verbose=True)
# Returns: passed, failed, output
```

### ✅ check_syntax
Validate Python syntax and AST
```python
result = await check_syntax("my_code.py")
# Returns: valid, errors, functions, classes
```

### 🔍 run_linter
Run pylint, flake8, or black
```python
result = await run_linter("my_code.py", tool="pylint")
# Returns: issues_found, output, clean
```

### 📁 list_files
Find files by pattern
```python
result = await list_files("agents/", pattern="*.py", recursive=True)
# Returns: files with metadata
```

### 🌳 get_file_structure
Get project tree structure
```python
result = await get_file_structure(".", max_depth=3)
# Returns: directory tree
```

## Usage Examples

### Example 1: Add a New Feature

```bash
./cli.py --team dev "Add a function to parse RSS feeds to web_tools.py"
```

**What happens:**
1. **Coder** reads existing code, writes new `parse_rss_feed()` function
2. **Tester** writes tests in `tests/test_web_tools.py` covering:
   - Valid RSS feed parsing
   - Invalid XML handling
   - Network errors
   - Edge cases (empty feeds, malformed data)
3. **Reviewer** examines both:
   - Checks implementation for bugs
   - Verifies test coverage
   - Suggests improvements
   - Approves when ready

### Example 2: Quick Prototype

```bash
./cli.py --team dev-quick "Write a function to calculate word frequency in text"
```

**What happens:**
1. **Coder** writes implementation with docstring
2. Done ✓ (fast, no tests)

### Example 3: Refactor with Tests

```bash
./cli.py --team dev-test "Refactor memory_manager.py to use async/await"
```

**What happens:**
1. **Coder** refactors code to use async
2. **Tester** updates existing tests and adds new ones
3. **Tester** runs tests to verify refactoring worked

### Example 4: Security Review

```bash
./cli.py --team dev "Review agents/magentic_one/tools/web_tools.py for security issues"
```

**Workflow:**
1. **Reviewer** reads code
2. **Reviewer** runs linters
3. **Reviewer** checks for:
   - SQL injection
   - XSS vulnerabilities
   - SSRF (already fixed!)
   - Input validation
4. **Reviewer** provides detailed feedback

## Interactive Mode

You can also use the dev team in interactive mode:

```bash
./cli.py --team dev

You: Add a CSV export function to data_tools.py
[Coder implements]
[Tester writes tests]
[Reviewer reviews]

You: Now add error handling for large files
[Team iterates...]
```

## Tips & Best Practices

### 🎯 Choose the Right Mode

- **dev-quick**: Prototypes, scripts, exploration
- **dev-test**: Features, utilities, libraries
- **dev**: Production code, critical features

### 📝 Be Specific in Requests

**Good:**
```
Add rate limiting to navigate_to_url() in web_tools.py:
- 10 requests per minute default
- Configurable per domain
- Respect Retry-After headers
```

**Less Good:**
```
Add rate limiting
```

### 🔄 Iterative Development

```bash
# Start with quick implementation
./cli.py --team dev-quick "Sketch out RSS feed parser"

# Add tests
./cli.py --team dev-test "Complete RSS parser with tests"

# Full review
./cli.py --team dev "Final review and security check"
```

### 🧪 Test-Driven Development

```bash
./cli.py --team dev "Write tests first, then implementation for email validator"
```

The team will adapt and Tester can write tests first!

## Extending the Team

### Add New Tools

Edit `agents/dev_tools.py`:

```python
async def format_code(file_path: str) -> Dict[str, Any]:
    """Auto-format code with black."""
    # Implementation
    ...

# Add to get_dev_tools():
FunctionTool(format_code, description="...")
```

Now ALL agents can use it!

### Add New Agents

Edit `agents/dev_agents.py`:

```python
def create_documenter_agent(llm_config: dict) -> AssistantAgent:
    """Agent that writes documentation."""
    return AssistantAgent(
        name="Documenter",
        tools=get_dev_tools(),  # Same tools!
        system_message="You write clear documentation..."
    )
```

### Custom Team Modes

```python
async def create_doc_team(llm_config: dict):
    """Coder + Documenter."""
    coder = create_coder_agent(llm_config)
    documenter = create_documenter_agent(llm_config)

    return RoundRobinGroupChat(
        [coder, documenter],
        termination_condition=TextMentionTermination("DOCUMENTED")
    )
```

## Architecture Benefits

### ✅ Atomic Responsibilities
- Clear, single-purpose agents
- No confusion about who does what
- Easy to debug and improve

### ✅ Shared Tools
- Consistent behavior
- Less code duplication
- Easy to add capabilities

### ✅ Composable
- Mix agents for different workflows
- Scale complexity as needed
- Reuse agents in different teams

### ✅ Testable
- Each agent's behavior is predictable
- Tools can be tested independently
- Integration is straightforward

## Comparison with V1 (What Changed)

### V1 Issues:
- ❌ Too many agents (5+)
- ❌ Overlapping responsibilities
- ❌ Complex orchestration
- ❌ Hard to understand flow

### V2 Solutions:
- ✅ Just 3 agents (atomic)
- ✅ Clear single responsibilities
- ✅ Simple round-robin flow
- ✅ Predictable, easy to understand

### Performance:
- **V1**: 5 agents × complex orchestration = slow, unpredictable
- **V2**: 1-3 agents × clear flow = fast, reliable

## Future Enhancements

Ideas for extending the dev team:

1. **Documenter Agent** - Writes docs and READMEs
2. **Performance Analyzer** - Profiles and optimizes code
3. **Security Scanner** - Deep security analysis
4. **Migration Agent** - Helps upgrade dependencies
5. **API Designer** - Designs REST/GraphQL APIs

All would share the same tool library!

---

**Built with:** AutoGen 0.6+, Azure OpenAI, Rich CLI

**Philosophy:** Do one thing well, compose for complexity
