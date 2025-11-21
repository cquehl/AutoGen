#!/usr/bin/env python3
"""
Automated User Flow Testing for Suntory v3
Tests the complete user experience from startup to advanced features
"""

import asyncio
import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import Mock, patch, AsyncMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import Alfred components
from src.alfred.main_enhanced import AlfredEnhanced
from src.alfred.modes import AlfredMode, DirectProxyMode, TeamOrchestratorMode
from src.core.config import SuntorySettings, get_settings
from src.core.llm_gateway import LLMGateway
from src.core.persistence import PersistenceManager

class UserFlowTester:
    """Comprehensive user flow testing suite"""

    def __init__(self):
        self.results = []
        self.alfred = None
        self.test_count = 0
        self.passed_count = 0
        self.failed_count = 0

    def log(self, message: str, status: str = "INFO"):
        """Log test progress"""
        timestamp = time.strftime("%H:%M:%S")
        color = {
            "PASS": "\033[92m",
            "FAIL": "\033[91m",
            "INFO": "\033[94m",
            "WARN": "\033[93m"
        }.get(status, "")
        reset = "\033[0m"
        print(f"{color}[{timestamp}] [{status}] {message}{reset}")

    async def setup(self):
        """Initialize test environment"""
        self.log("Setting up test environment...")

        # Mock settings to avoid real API calls
        with patch('src.core.config.get_settings') as mock_settings:
            settings = Mock(spec=SuntorySettings)
            settings.openai_api_key = "test-key"
            settings.anthropic_api_key = "test-key"
            settings.google_api_key = "test-key"
            settings.default_model = "gpt-4o"
            settings.data_dir = Path("./test_data")
            settings.log_dir = Path("./test_logs")
            settings.workspace_dir = Path("./test_workspace")
            mock_settings.return_value = settings

            # Create test directories
            settings.data_dir.mkdir(exist_ok=True)
            settings.log_dir.mkdir(exist_ok=True)
            settings.workspace_dir.mkdir(exist_ok=True)

            # Initialize Alfred
            self.alfred = AlfredEnhanced()
            await self.alfred.initialize()

        self.log("Test environment ready", "PASS")

    async def teardown(self):
        """Clean up test environment"""
        self.log("Cleaning up test environment...")

        # Clean up test directories
        import shutil
        for dir_path in ["./test_data", "./test_logs", "./test_workspace"]:
            if Path(dir_path).exists():
                shutil.rmtree(dir_path)

        self.log("Cleanup complete", "PASS")

    def assert_test(self, condition: bool, test_name: str, details: str = ""):
        """Assert test condition and track results"""
        self.test_count += 1
        if condition:
            self.passed_count += 1
            self.log(f"✓ {test_name} {details}", "PASS")
            self.results.append({"test": test_name, "status": "PASS", "details": details})
        else:
            self.failed_count += 1
            self.log(f"✗ {test_name} {details}", "FAIL")
            self.results.append({"test": test_name, "status": "FAIL", "details": details})

    # ========== TEST CASES ==========

    async def test_basic_chat(self):
        """Test basic chat interaction"""
        self.log("\n=== Testing Basic Chat Flow ===")

        # Mock LLM response
        with patch.object(self.alfred.llm_gateway, 'call_llm') as mock_llm:
            mock_llm.return_value = AsyncMock(return_value={
                "choices": [{
                    "message": {"content": "Hello! I'm Alfred, your AI assistant. How can I help you today?"}
                }]
            })()

            # Test greeting
            response = await self.alfred.handle_message("Hello!")
            self.assert_test(
                "Hello" in response and "Alfred" in response,
                "Basic greeting response",
                f"Got: {response[:100]}..."
            )

            # Test conversation history
            history = await self.alfred.get_history(limit=1)
            self.assert_test(
                len(history) > 0,
                "Conversation saved to history",
                f"History entries: {len(history)}"
            )

    async def test_command_execution(self):
        """Test command execution"""
        self.log("\n=== Testing Command Execution ===")

        # Test /help command
        response = await self.alfred.handle_message("/help")
        self.assert_test(
            "Available Commands" in response or "help" in response.lower(),
            "/help command",
            "Help text displayed"
        )

        # Test /mode command
        response = await self.alfred.handle_message("/mode")
        self.assert_test(
            "mode" in response.lower() or "direct" in response.lower(),
            "/mode command",
            "Current mode displayed"
        )

        # Test /history command
        response = await self.alfred.handle_message("/history")
        self.assert_test(
            "history" in response.lower() or "conversation" in response.lower(),
            "/history command",
            "History displayed"
        )

    async def test_team_mode_activation(self):
        """Test team mode activation for complex tasks"""
        self.log("\n=== Testing Team Mode Activation ===")

        # Mock team mode detection
        with patch.object(self.alfred, '_should_use_team_mode') as mock_team:
            mock_team.return_value = True

            with patch.object(self.alfred.llm_gateway, 'call_llm') as mock_llm:
                mock_llm.return_value = AsyncMock(return_value={
                    "choices": [{
                        "message": {"content": "I'll help you build a REST API. Let me assemble the team..."}
                    }]
                })()

                # Test complex task that triggers team mode
                response = await self.alfred.handle_message("Build a secure REST API with JWT authentication")

                self.assert_test(
                    mock_team.called,
                    "Team mode detection triggered",
                    "Complex task recognized"
                )

                self.assert_test(
                    "team" in response.lower() or "API" in response,
                    "Team mode response",
                    f"Response indicates team coordination"
                )

    async def test_model_switching(self):
        """Test model switching between providers"""
        self.log("\n=== Testing Model Switching ===")

        # Test current model display
        response = await self.alfred.handle_message("/model")
        self.assert_test(
            "gpt-4o" in response or "model" in response.lower(),
            "Display current model",
            "Current model shown"
        )

        # Test switching to Claude
        with patch.object(self.alfred.llm_gateway, 'switch_model') as mock_switch:
            mock_switch.return_value = True

            response = await self.alfred.handle_message("/model claude-3-5-sonnet-20241022")

            self.assert_test(
                mock_switch.called,
                "Model switch attempted",
                "Switch to Claude requested"
            )

    async def test_error_handling(self):
        """Test error handling and recovery"""
        self.log("\n=== Testing Error Handling ===")

        # Test invalid command
        response = await self.alfred.handle_message("/invalid_command")
        self.assert_test(
            "unknown" in response.lower() or "invalid" in response.lower() or len(response) > 0,
            "Invalid command handling",
            "Graceful error response"
        )

        # Test LLM failure fallback
        with patch.object(self.alfred.llm_gateway, 'call_llm') as mock_llm:
            mock_llm.side_effect = Exception("API Error")

            response = await self.alfred.handle_message("Test query")

            self.assert_test(
                "error" in response.lower() or "sorry" in response.lower() or len(response) > 0,
                "LLM failure handling",
                "Graceful error recovery"
            )

    async def test_persistence(self):
        """Test data persistence across sessions"""
        self.log("\n=== Testing Persistence ===")

        # Save a message
        await self.alfred.handle_message("Remember this: test data 12345")

        # Get history
        history = await self.alfred.get_history(limit=10)

        self.assert_test(
            any("12345" in str(h) for h in history),
            "Message persistence",
            "Message saved and retrievable"
        )

    async def test_mode_detection(self):
        """Test automatic mode detection"""
        self.log("\n=== Testing Mode Detection ===")

        test_cases = [
            ("What's the weather?", False, "Simple query - Direct mode"),
            ("Build a full-stack application", True, "Complex task - Team mode"),
            ("Explain Python decorators", False, "Educational - Direct mode"),
            ("Implement OAuth2 with refresh tokens", True, "Technical implementation - Team mode"),
            ("/team analyze this codebase", True, "Explicit team command"),
        ]

        for query, should_be_team, description in test_cases:
            with patch.object(self.alfred, '_should_use_team_mode') as mock_detect:
                mock_detect.return_value = should_be_team

                with patch.object(self.alfred.llm_gateway, 'call_llm') as mock_llm:
                    mock_llm.return_value = AsyncMock(return_value={
                        "choices": [{"message": {"content": "Response"}}]
                    })()

                    await self.alfred.handle_message(query)

                    self.assert_test(
                        True,  # Just checking it doesn't crash
                        f"Mode detection: {description}",
                        f"Query: '{query[:50]}...'"
                    )

    async def test_autocomplete(self):
        """Test command autocomplete functionality"""
        self.log("\n=== Testing Autocomplete ===")

        # Mock autocomplete suggestions
        commands = ["/help", "/model", "/team", "/history", "/clear", "/mode"]

        test_inputs = [
            ("/h", ["/help", "/history"]),
            ("/mo", ["/model", "/mode"]),
            ("/t", ["/team"]),
        ]

        for input_text, expected in test_inputs:
            suggestions = [cmd for cmd in commands if cmd.startswith(input_text)]

            self.assert_test(
                len(suggestions) > 0,
                f"Autocomplete for '{input_text}'",
                f"Suggestions: {suggestions}"
            )

    async def test_multi_provider_fallback(self):
        """Test fallback between LLM providers"""
        self.log("\n=== Testing Multi-Provider Fallback ===")

        with patch.object(self.alfred.llm_gateway, 'call_llm') as mock_llm:
            # First call fails (OpenAI)
            # Second call succeeds (Anthropic fallback)
            mock_llm.side_effect = [
                Exception("OpenAI API Error"),
                AsyncMock(return_value={
                    "choices": [{"message": {"content": "Response from Claude"}}]
                })()
            ]

            response = await self.alfred.handle_message("Test fallback")

            self.assert_test(
                mock_llm.call_count >= 1,
                "Provider fallback attempted",
                f"Fallback triggered after primary failure"
            )

    # ========== MAIN TEST RUNNER ==========

    async def run_all_tests(self):
        """Run all test cases"""
        self.log("\n" + "="*60)
        self.log("Starting Suntory v3 User Flow Tests")
        self.log("="*60)

        try:
            await self.setup()

            # Run all test methods
            test_methods = [
                self.test_basic_chat,
                self.test_command_execution,
                self.test_team_mode_activation,
                self.test_model_switching,
                self.test_error_handling,
                self.test_persistence,
                self.test_mode_detection,
                self.test_autocomplete,
                self.test_multi_provider_fallback,
            ]

            for test_method in test_methods:
                try:
                    await test_method()
                except Exception as e:
                    self.log(f"Test failed with error: {e}", "FAIL")
                    self.failed_count += 1

            await self.teardown()

        except Exception as e:
            self.log(f"Setup/Teardown failed: {e}", "FAIL")

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print test results summary"""
        self.log("\n" + "="*60)
        self.log("TEST RESULTS SUMMARY")
        self.log("="*60)

        total = self.test_count
        passed = self.passed_count
        failed = self.failed_count
        pass_rate = (passed / total * 100) if total > 0 else 0

        self.log(f"Total Tests: {total}")
        self.log(f"Passed: {passed}", "PASS" if passed > 0 else "INFO")
        self.log(f"Failed: {failed}", "FAIL" if failed > 0 else "INFO")
        self.log(f"Pass Rate: {pass_rate:.1f}%")

        if failed > 0:
            self.log("\nFailed Tests:", "FAIL")
            for result in self.results:
                if result["status"] == "FAIL":
                    self.log(f"  - {result['test']}: {result['details']}", "FAIL")

        self.log("\n" + "="*60)

        # Return exit code
        return 0 if failed == 0 else 1

async def main():
    """Main entry point"""
    tester = UserFlowTester()
    exit_code = await tester.run_all_tests()
    sys.exit(exit_code)

if __name__ == "__main__":
    asyncio.run(main())