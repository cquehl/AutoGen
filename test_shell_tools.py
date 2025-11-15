"""
Quick test for shell tools implementation
"""

import asyncio
from v2.core.container import get_container


async def test_shell_tools():
    """Test shell tools basic functionality"""
    print("🧪 Testing Shell Tools Implementation\n")

    # Get container
    container = get_container()
    print("✓ Container initialized")

    # Get security middleware
    security = container.get_security_middleware()
    print("✓ Security middleware initialized")
    print(f"  Validators: {list(security.validators.keys())}")

    # Get background job manager
    job_manager = container.get_background_job_manager()
    print(f"✓ Background job manager initialized (max_jobs={job_manager.max_jobs})")

    # Get tool registry
    tool_registry = container.get_tool_registry()
    print(f"✓ Tool registry initialized ({len(tool_registry._tools)} tools)")

    # Try to create BashTool
    try:
        bash_tool = tool_registry.create_tool("shell.bash")
        print(f"✓ BashTool created successfully")
        print(f"  Name: {bash_tool.NAME}")
        print(f"  Description: {bash_tool.DESCRIPTION}")
        print(f"  Category: {bash_tool.CATEGORY}")
        print(f"  Requires Security: {bash_tool.REQUIRES_SECURITY_VALIDATION}")
    except Exception as e:
        print(f"✗ Failed to create BashTool: {e}")
        return

    # Test simple command
    print("\n🔧 Testing simple command execution...")
    try:
        result = await bash_tool.execute(command="echo 'Hello from AutoGen V2!'")
        if result.success:
            print(f"✓ Command executed successfully")
            print(f"  stdout: {result.data.get('stdout', '').strip()}")
            print(f"  return_code: {result.data.get('return_code')}")
        else:
            print(f"✗ Command failed: {result.error}")
    except Exception as e:
        print(f"✗ Exception during command execution: {e}")

    # Test blocked command
    print("\n🔒 Testing security validation (blocked command)...")
    try:
        result = await bash_tool.execute(command="rm -rf /")
        if not result.success:
            print(f"✓ Dangerous command blocked as expected")
            print(f"  Error: {result.error}")
        else:
            print(f"✗ WARNING: Dangerous command was NOT blocked!")
    except Exception as e:
        print(f"✗ Exception during blocked command test: {e}")

    # Test background job manager
    print("\n⏳ Testing background job manager...")
    try:
        job_id = await job_manager.start_job("echo 'Background job test' && sleep 1 && echo 'Done'")
        print(f"✓ Background job started: {job_id}")

        # Wait a bit and check status
        await asyncio.sleep(0.5)
        status = job_manager.get_status(job_id)
        print(f"  Status: {status.status}")

        # Get output
        output = job_manager.get_output(job_id, new_only=False)
        if output:
            print(f"  Output lines: {len(output)}")
            for line_data in output[:3]:  # Show first 3 lines
                print(f"    - {line_data['line']}")

        # Wait for completion
        await asyncio.sleep(1.5)
        status = job_manager.get_status(job_id)
        print(f"  Final status: {status.status}")

    except Exception as e:
        print(f"✗ Background job test failed: {e}")

    print("\n✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(test_shell_tools())
