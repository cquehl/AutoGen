# Tests

Basic smoke tests for AutoGen CLI Agent.

## Running Tests

```bash
# Install pytest if not already installed
pip install pytest

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_smoke.py -v

# Run with coverage (requires pytest-cov)
pytest tests/ --cov=. --cov-report=html
```

## Test Categories

- **TestConfiguration**: Configuration loading and error messages
- **TestMemorySystem**: Memory storage, retrieval, search, pruning
- **TestWebToolsSecurity**: URL validation and SSRF prevention
- **TestDataTools**: File and CSV operations
- **TestCLIBasics**: Basic import and setup tests

## Adding New Tests

1. Create a new test file: `test_<feature>.py`
2. Use pytest-style test classes and functions
3. Follow existing naming conventions
4. Add docstrings to explain what's being tested

## Notes

- Tests use temporary directories to avoid affecting real data
- Mock objects are used to avoid requiring real API keys
- Tests focus on critical functionality and security
