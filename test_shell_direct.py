"""
Direct import test for shell components (bypassing package __init__)
"""

import sys
import asyncio
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_shell_validator():
    """Test ShellValidator directly"""
    from v2.security.validators.shell_validator import ShellValidator
    from v2.config.models import SecurityConfig

    print("🧪 Testing ShellValidator\n")

    # Create config
    config = SecurityConfig()
    validator = ShellValidator(config)

    # Test safe command
    result = validator.validate("ls -la")
    assert result.is_valid
    print(f"✓ Safe command (ls -la): PASS")

    # Test blocked command
    result = validator.validate("rm -rf /")
    assert not result.is_valid
    assert "Blocked command pattern" in result.error
    print(f"✓ Blocked command (rm -rf /): PASS")

    # Test dangerous command
    result = validator.validate("shutdown now")
    assert not result.is_valid
    print(f"✓ Dangerous command (shutdown): PASS")

    # Test command with pipes
    result = validator.validate("cat file.txt | grep test")
    assert result.is_valid
    print(f"✓ Command with pipes: PASS")

    # Test command chaining
    result = validator.validate("cd /tmp && ls")
    assert result.is_valid
    print(f"✓ Command chaining (&&): PASS")

    # Test command type detection
    result = validator.validate("git status")
    assert result.query_type == "git"
    print(f"✓ Git command detected: PASS")

    result = validator.validate("npm install express")
    assert result.query_type == "package_install"
    print(f"✓ Package install detected: PASS")

    print("\n✅ ShellValidator: ALL TESTS PASSED!")


async def test_background_job_manager():
    """Test BackgroundJobManager directly"""
    from v2.tools.shell.background_job_manager import BackgroundJobManager, JobStatus

    print("\n🧪 Testing BackgroundJobManager\n")

    manager = BackgroundJobManager(max_jobs=5, max_output_lines=100)
    print(f"✓ Manager created (max_jobs={manager.max_jobs})")

    # Start a simple job
    job_id = await manager.start_job("echo 'Test output' && sleep 0.5 && echo 'Done'")
    print(f"✓ Job started: {job_id}")

    # Check initial status
    status = manager.get_status(job_id)
    assert status.status == JobStatus.RUNNING
    print(f"  Initial status: {status.status} ✓")

    # Wait a bit
    await asyncio.sleep(0.3)

    # Get output
    output = manager.get_output(job_id, new_only=False)
    assert output is not None
    print(f"✓ Got output ({len(output)} lines)")

    # Wait for completion
    await asyncio.sleep(0.8)

    # Final status
    status = manager.get_status(job_id)
    assert status.status in [JobStatus.COMPLETED, JobStatus.FAILED]
    print(f"  Final status: {status.status} ✓")

    # List jobs
    jobs = manager.list_jobs()
    assert len(jobs) >= 1
    print(f"✓ Listed {len(jobs)} job(s)")

    # Cleanup
    await manager.cleanup_completed(keep_recent=0)
    print(f"✓ Cleaned up completed jobs")

    print("\n✅ BackgroundJobManager: ALL TESTS PASSED!")


async def test_bash_tool():
    """Test BashTool structure (without full container)"""
    from v2.tools.shell.bash_tool import BashTool
    from v2.core.base_tool import ToolCategory

    print("\n🧪 Testing BashTool Structure\n")

    # Check class attributes
    assert BashTool.NAME == "shell.bash"
    assert BashTool.CATEGORY == ToolCategory.SHELL
    assert BashTool.REQUIRES_SECURITY_VALIDATION == True
    print(f"✓ BashTool metadata correct")
    print(f"  Name: {BashTool.NAME}")
    print(f"  Category: {BashTool.CATEGORY.value}")
    print(f"  Requires Security: {BashTool.REQUIRES_SECURITY_VALIDATION}")

    # Check parameter validation
    tool = BashTool(security_middleware=None, default_timeout=120, max_timeout=600)

    # Valid params
    is_valid, error = tool.validate_params(command="echo test")
    assert is_valid
    print(f"✓ Valid params accepted")

    # Invalid params (no command)
    is_valid, error = tool.validate_params()
    assert not is_valid
    assert error == "command is required"
    print(f"✓ Missing params rejected")

    # Invalid timeout
    is_valid, error = tool.validate_params(command="test", timeout=9999)
    assert not is_valid
    print(f"✓ Invalid timeout rejected")

    # Check schema
    schema = tool._get_parameters_schema()
    assert "command" in schema["properties"]
    assert "timeout" in schema["properties"]
    print(f"✓ Parameters schema complete")

    print("\n✅ BashTool: ALL TESTS PASSED!")


async def main():
    """Run all tests"""
    print("=" * 70)
    print(" " * 15 + "🚀 Shell Tools Component Tests")
    print("=" * 70 + "\n")

    try:
        await test_shell_validator()
        await test_background_job_manager()
        await test_bash_tool()

        print("\n" + "=" * 70)
        print(" " * 20 + "✅ ALL TESTS PASSED!")
        print("=" * 70)
        return 0

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
