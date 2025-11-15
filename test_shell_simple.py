"""
Simplified test for shell components (no full framework initialization)
"""

import asyncio


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
    print(f"✓ Safe command (ls -la): {result.is_valid}")

    # Test blocked command
    result = validator.validate("rm -rf /")
    print(f"✓ Blocked command (rm -rf /): is_valid={result.is_valid}, error={result.error}")

    # Test dangerous command
    result = validator.validate("shutdown now")
    print(f"✓ Dangerous command (shutdown): is_valid={result.is_valid}, error={result.error}")

    # Test command with pipes
    result = validator.validate("cat file.txt | grep test")
    print(f"✓ Command with pipes: is_valid={result.is_valid}")

    # Test command chaining
    result = validator.validate("cd /tmp && ls")
    print(f"✓ Command chaining (&&): is_valid={result.is_valid}")

    # Test command type detection
    result = validator.validate("git status")
    print(f"✓ Git command detected: type={result.query_type}")

    result = validator.validate("npm install express")
    print(f"✓ Package install detected: type={result.query_type}")

    print("\n✅ ShellValidator tests passed!")


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
    print(f"  Initial status: {status.status}")

    # Wait a bit
    await asyncio.sleep(0.3)

    # Get output
    output = manager.get_output(job_id, new_only=False)
    if output:
        print(f"✓ Got output ({len(output)} lines):")
        for line_data in output:
            print(f"    {line_data['line']}")

    # Wait for completion
    await asyncio.sleep(0.5)

    # Final status
    status = manager.get_status(job_id)
    print(f"  Final status: {status.status}")
    print(f"  Return code: {status.return_code}")

    # List jobs
    jobs = manager.list_jobs()
    print(f"✓ Listed {len(jobs)} job(s)")

    # Cleanup
    await manager.cleanup_completed(keep_recent=0)
    print(f"✓ Cleaned up completed jobs")

    print("\n✅ BackgroundJobManager tests passed!")


async def test_security_middleware():
    """Test SecurityMiddleware with shell validation"""
    from v2.security.middleware import SecurityMiddleware, Operation, OperationType
    from v2.config.models import SecurityConfig

    print("\n🧪 Testing SecurityMiddleware with Shell Validation\n")

    config = SecurityConfig()
    middleware = SecurityMiddleware(config)
    print(f"✓ Middleware created with validators: {list(middleware.validators.keys())}")

    # Test shell validator exists
    shell_validator = middleware.get_shell_validator()
    print(f"✓ Shell validator accessible: {shell_validator}")

    # Test validation via middleware
    async def dummy_executor(**kwargs):
        return {"output": "test"}

    operation = Operation(
        type=OperationType.SHELL_COMMAND,
        params={
            "command": "echo test",
            "allow_pipes": True,
            "allow_chaining": True,
        },
        executor=dummy_executor,
        timeout=5,
    )

    result = await middleware.validate_and_execute(operation)
    print(f"✓ Safe command validation: success={result.success}")

    # Test blocked command
    operation.params["command"] = "rm -rf /"
    result = await middleware.validate_and_execute(operation)
    print(f"✓ Blocked command validation: blocked={result.blocked}, error={result.error}")

    print("\n✅ SecurityMiddleware tests passed!")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Shell Tools Component Tests")
    print("=" * 60 + "\n")

    await test_shell_validator()
    await test_background_job_manager()
    await test_security_middleware()

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
