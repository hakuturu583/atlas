#!/usr/bin/env python3
"""
Example: Automatic sandbox launch with validation.

This demonstrates the high-level SandboxLauncher API for guaranteed startup.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services import sandbox_launcher


def example_simple_launch():
    """Example 1: Simple launch with all defaults."""
    print("=" * 70)
    print("Example 1: Simple Launch (all validations enabled)")
    print("=" * 70)
    print()

    # Launch with all validations
    result = sandbox_launcher.launch_and_wait()

    if result.success:
        print(f"✅ Success! Sandbox UUID: {result.uuid}")
        print(f"   Container: {result.container_name}")
        print(f"   Workspace: {result.workspace_path}")
    else:
        print(f"❌ Failed: {result.error_message}")

    return result


def example_custom_launch():
    """Example 2: Launch with custom configuration."""
    print("\n" + "=" * 70)
    print("Example 2: Custom Configuration")
    print("=" * 70)
    print()

    # Launch with specific UUID and custom timeout
    my_uuid = "test-scenario-001"

    result = sandbox_launcher.launch_with_validation(
        scenario_uuid=my_uuid,
        check_carla=True,
        wait_for_ready=True,
        timeout=180.0  # 3 minutes timeout
    )

    if result.success:
        print(f"✅ Launched with UUID: {result.uuid}")
    else:
        print(f"❌ Failed: {result.error_message}")

    return result


def example_without_carla_check():
    """Example 3: Launch without CARLA check (for testing)."""
    print("\n" + "=" * 70)
    print("Example 3: Launch Without CARLA Check")
    print("=" * 70)
    print()

    result = sandbox_launcher.launch_with_validation(
        check_carla=False,  # Skip CARLA connectivity check
        wait_for_ready=True,
        timeout=60.0
    )

    if result.success:
        print(f"✅ Container started: {result.container_name}")
        print(f"   Status: {'Running' if result.container_running else 'Stopped'}")
    else:
        print(f"❌ Failed: {result.error_message}")

    return result


def example_with_scenario_manager():
    """Example 4: Integration with ScenarioManager."""
    print("\n" + "=" * 70)
    print("Example 4: Integration with ScenarioManager")
    print("=" * 70)
    print()

    from app.services import scenario_manager
    from app.models.scenario import Scenario

    # Launch sandbox first
    result = sandbox_launcher.launch_and_wait()

    if not result.success:
        print(f"❌ Failed to launch sandbox: {result.error_message}")
        return None

    # Create scenario with sandbox info
    scenario = Scenario(
        id=f"scenario_{result.uuid[:8]}",
        name="Auto-launched Scenario",
        description="Example scenario with automatic sandbox launch",
        sandbox_uuid=result.uuid,
        container_status="running" if result.container_running else "stopped",
        workspace_path=str(result.workspace_path)
    )

    # Save scenario
    scenario_manager.create_scenario(scenario)

    print(f"✅ Created scenario: {scenario.id}")
    print(f"   Sandbox UUID: {scenario.sandbox_uuid}")
    print(f"   Status: {scenario.container_status}")
    print(f"   Workspace: {scenario.workspace_path}")

    return scenario


def example_error_handling():
    """Example 5: Proper error handling."""
    print("\n" + "=" * 70)
    print("Example 5: Error Handling")
    print("=" * 70)
    print()

    try:
        result = sandbox_launcher.launch_and_wait(timeout=30.0)

        if result.success:
            print(f"✅ Success")
            # Do something with the sandbox
            print(f"   Working with sandbox: {result.uuid}")

        else:
            # Handle specific errors
            if result.carla_connected is False:
                print("⚠️  CARLA server is not running")
                print("   Please start CARLA first:")
                print("   cd /path/to/carla && ./CarlaUE4.sh")

            elif not result.container_running:
                print("⚠️  Container failed to start")
                if result.logs:
                    print(f"   Logs: {result.logs[:200]}...")

            else:
                print(f"⚠️  Unknown error: {result.error_message}")

    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all examples."""
    print("\n🎯 SandboxLauncher Examples\n")

    print("NOTE: These examples will actually launch sandboxes!")
    print("      Make sure CARLA server is running first.")
    print()

    input("Press Enter to continue (Ctrl+C to cancel)...")
    print()

    try:
        # Run examples
        example_simple_launch()

        # Uncomment to run other examples
        # example_custom_launch()
        # example_without_carla_check()
        # example_with_scenario_manager()
        # example_error_handling()

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("✅ Examples completed!")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
