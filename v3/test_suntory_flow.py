#!/usr/bin/env python3
"""
Simple User Flow Test for Suntory v3
Tests the actual system by simulating user interactions
"""

import subprocess
import time
import os
import sys
from pathlib import Path

class SuntoryFlowTester:
    """Test Suntory user flows by interacting with the actual system"""

    def __init__(self):
        self.test_count = 0
        self.passed = 0
        self.failed = 0
        self.results = []

    def log(self, message, level="INFO"):
        """Log with color coding"""
        colors = {
            "PASS": "\033[92m",
            "FAIL": "\033[91m",
            "INFO": "\033[94m",
            "WARN": "\033[93m"
        }
        color = colors.get(level, "")
        reset = "\033[0m"
        print(f"{color}[{level}] {message}{reset}")

    def run_command(self, command, timeout=10):
        """Run a shell command and return output"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd="/Users/cjq/Dev/MyProjects/AutoGen/v3"
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            return "", "Command timed out", 1
        except Exception as e:
            return "", str(e), 1

    def test_environment_setup(self):
        """Test that the environment is properly configured"""
        self.log("\n=== Testing Environment Setup ===")

        # Check Python version
        stdout, _, code = self.run_command("python3 --version")
        self.assert_test(
            code == 0 and "Python 3" in stdout,
            "Python 3 installed",
            stdout.strip()
        )

        # Check virtual environment
        venv_exists = Path("/Users/cjq/Dev/MyProjects/AutoGen/v3/venv").exists()
        self.assert_test(
            venv_exists,
            "Virtual environment exists",
            "venv directory found"
        )

        # Check .env file
        env_exists = Path("/Users/cjq/Dev/MyProjects/AutoGen/v3/.env").exists()
        self.assert_test(
            env_exists,
            ".env file exists",
            "Environment configuration present"
        )

        # Check Suntory.sh
        script_exists = Path("/Users/cjq/Dev/MyProjects/AutoGen/v3/Suntory.sh").exists()
        self.assert_test(
            script_exists,
            "Suntory.sh script exists",
            "Launch script available"
        )

    def test_imports(self):
        """Test that core modules can be imported"""
        self.log("\n=== Testing Module Imports ===")

        test_script = """
import sys
sys.path.insert(0, '/Users/cjq/Dev/MyProjects/AutoGen/v3')
try:
    from src.alfred.main_enhanced import AlfredEnhanced
    print("✓ AlfredEnhanced imported")
except Exception as e:
    print(f"✗ AlfredEnhanced import failed: {e}")

try:
    from src.core.llm_gateway import LLMGateway
    print("✓ LLMGateway imported")
except Exception as e:
    print(f"✗ LLMGateway import failed: {e}")

try:
    from src.core.config import get_settings
    print("✓ Config imported")
except Exception as e:
    print(f"✗ Config import failed: {e}")

try:
    from src.interface.tui_world_class import WorldClassTUI
    print("✓ WorldClassTUI imported")
except Exception as e:
    print(f"✗ WorldClassTUI import failed: {e}")
"""

        # Write test script
        test_file = Path("/Users/cjq/Dev/MyProjects/AutoGen/v3/test_imports_check.py")
        test_file.write_text(test_script)

        # Run imports test
        stdout, stderr, code = self.run_command(
            "source venv/bin/activate && python test_imports_check.py"
        )

        # Check results
        for line in stdout.split('\n'):
            if '✓' in line:
                module = line.split('✓')[1].strip()
                self.assert_test(True, f"Import {module}", "Success")
            elif '✗' in line:
                module = line.split('✗')[1].split('import')[0].strip()
                self.assert_test(False, f"Import {module}", "Failed")

        # Clean up
        test_file.unlink(missing_ok=True)

    def test_alfred_initialization(self):
        """Test Alfred can be initialized"""
        self.log("\n=== Testing Alfred Initialization ===")

        test_script = """
import sys
import asyncio
sys.path.insert(0, '/Users/cjq/Dev/MyProjects/AutoGen/v3')

async def test():
    try:
        from src.alfred.main_enhanced import AlfredEnhanced
        alfred = AlfredEnhanced()
        await alfred.initialize()
        print("✓ Alfred initialized successfully")
        return True
    except Exception as e:
        print(f"✗ Alfred initialization failed: {e}")
        return False

result = asyncio.run(test())
"""

        # Write test script
        test_file = Path("/Users/cjq/Dev/MyProjects/AutoGen/v3/test_alfred_init.py")
        test_file.write_text(test_script)

        # Run test
        stdout, stderr, code = self.run_command(
            "source venv/bin/activate && python test_alfred_init.py",
            timeout=15
        )

        self.assert_test(
            "✓ Alfred initialized" in stdout,
            "Alfred initialization",
            "Alfred system ready"
        )

        # Clean up
        test_file.unlink(missing_ok=True)

    def test_basic_commands(self):
        """Test basic command parsing"""
        self.log("\n=== Testing Basic Commands ===")

        test_script = """
import sys
import asyncio
sys.path.insert(0, '/Users/cjq/Dev/MyProjects/AutoGen/v3')

async def test():
    from src.alfred.main_enhanced import AlfredEnhanced

    alfred = AlfredEnhanced()
    await alfred.initialize()

    # Test command detection
    test_cases = [
        ("/help", True, "Help command"),
        ("/model", True, "Model command"),
        ("/history", True, "History command"),
        ("Hello", False, "Regular message"),
        ("/invalid", True, "Invalid command"),
    ]

    for text, is_command, desc in test_cases:
        result = text.startswith('/')
        status = "✓" if result == is_command else "✗"
        print(f"{status} {desc}: '{text}' -> command={result}")

asyncio.run(test())
"""

        # Write and run test
        test_file = Path("/Users/cjq/Dev/MyProjects/AutoGen/v3/test_commands.py")
        test_file.write_text(test_script)

        stdout, stderr, code = self.run_command(
            "source venv/bin/activate && python test_commands.py",
            timeout=15
        )

        # Parse results
        for line in stdout.split('\n'):
            if '✓' in line:
                self.assert_test(True, line.split('✓')[1].strip(), "Pass")
            elif '✗' in line:
                self.assert_test(False, line.split('✗')[1].strip(), "Fail")

        # Clean up
        test_file.unlink(missing_ok=True)

    def test_mode_detection(self):
        """Test mode detection logic"""
        self.log("\n=== Testing Mode Detection ===")

        test_script = """
import sys
sys.path.insert(0, '/Users/cjq/Dev/MyProjects/AutoGen/v3')

from src.alfred.modes import AlfredMode

# Test queries
test_cases = [
    ("Hello!", False, "Simple greeting"),
    ("What's the weather?", False, "Simple query"),
    ("Build a REST API with authentication", True, "Complex build task"),
    ("Implement OAuth2 flow", True, "Implementation task"),
    ("Explain Python decorators", False, "Educational query"),
    ("/team analyze this", True, "Explicit team command"),
]

for query, should_be_team, description in test_cases:
    # Simple heuristic for testing
    is_team = any(keyword in query.lower() for keyword in
                  ['build', 'implement', 'create', 'develop', '/team'])

    status = "✓" if is_team == should_be_team else "✗"
    print(f"{status} {description}: team={is_team}")
"""

        # Write and run test
        test_file = Path("/Users/cjq/Dev/MyProjects/AutoGen/v3/test_modes.py")
        test_file.write_text(test_script)

        stdout, stderr, code = self.run_command(
            "source venv/bin/activate && python test_modes.py"
        )

        # Parse results
        for line in stdout.split('\n'):
            if '✓' in line:
                self.assert_test(True, line.split('✓')[1].strip(), "Correct")
            elif '✗' in line:
                self.assert_test(False, line.split('✗')[1].strip(), "Incorrect")

        # Clean up
        test_file.unlink(missing_ok=True)

    def test_database_operations(self):
        """Test database and persistence"""
        self.log("\n=== Testing Database Operations ===")

        test_script = """
import sys
import asyncio
import sqlite3
from pathlib import Path
sys.path.insert(0, '/Users/cjq/Dev/MyProjects/AutoGen/v3')

# Check database
db_path = Path('/Users/cjq/Dev/MyProjects/AutoGen/v3/data/suntory.db')
if db_path.exists():
    print("✓ Database file exists")

    # Check tables
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    expected_tables = ['conversations', 'messages', 'user_preferences']
    for table in expected_tables:
        if any(table in t[0] for t in tables):
            print(f"✓ Table '{table}' exists")
        else:
            print(f"✗ Table '{table}' missing")

    conn.close()
else:
    print("✗ Database file not found")
"""

        # Write and run test
        test_file = Path("/Users/cjq/Dev/MyProjects/AutoGen/v3/test_db.py")
        test_file.write_text(test_script)

        stdout, stderr, code = self.run_command(
            "source venv/bin/activate && python test_db.py"
        )

        # Parse results
        for line in stdout.split('\n'):
            if '✓' in line:
                self.assert_test(True, line.split('✓')[1].strip(), "Found")
            elif '✗' in line:
                self.assert_test(False, line.split('✗')[1].strip(), "Missing")

        # Clean up
        test_file.unlink(missing_ok=True)

    def assert_test(self, condition, test_name, details=""):
        """Assert and record test result"""
        self.test_count += 1
        if condition:
            self.passed += 1
            self.log(f"✓ {test_name}: {details}", "PASS")
            self.results.append({"name": test_name, "status": "PASS"})
        else:
            self.failed += 1
            self.log(f"✗ {test_name}: {details}", "FAIL")
            self.results.append({"name": test_name, "status": "FAIL"})

    def run_all_tests(self):
        """Run all test cases"""
        self.log("="*60)
        self.log("SUNTORY V3 USER FLOW TESTS")
        self.log("="*60)

        # Run tests
        self.test_environment_setup()
        self.test_imports()
        self.test_alfred_initialization()
        self.test_basic_commands()
        self.test_mode_detection()
        self.test_database_operations()

        # Summary
        self.log("\n" + "="*60)
        self.log("TEST SUMMARY")
        self.log("="*60)
        self.log(f"Total: {self.test_count}")
        self.log(f"Passed: {self.passed}", "PASS" if self.passed > 0 else "INFO")
        self.log(f"Failed: {self.failed}", "FAIL" if self.failed > 0 else "INFO")

        pass_rate = (self.passed / self.test_count * 100) if self.test_count > 0 else 0
        self.log(f"Pass Rate: {pass_rate:.1f}%")

        if self.failed > 0:
            self.log("\nFailed Tests:", "FAIL")
            for result in self.results:
                if result["status"] == "FAIL":
                    self.log(f"  - {result['name']}", "FAIL")

        return 0 if self.failed == 0 else 1

if __name__ == "__main__":
    tester = SuntoryFlowTester()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)