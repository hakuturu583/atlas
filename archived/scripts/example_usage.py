#!/usr/bin/env python3
"""
Example usage of SandboxManager in Python code.

This demonstrates how to use the SandboxManager programmatically
from your Python application.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services import sandbox_manager


def example_launch_and_monitor():
    """Example: Launch a sandbox and monitor it."""
    print("=" * 60)
    print("Example: Launch and Monitor Sandbox")
    print("=" * 60)

    # Generate UUID
    uuid = sandbox_manager.generate_uuid()
    print(f"\n📋 Generated UUID: {uuid}")

    # Launch sandbox (this will run the sandbox/run.sh script)
    print(f"\n🚀 Launching sandbox...")
    # Note: This will actually run the sandbox, so make sure CARLA is running!
    # uuid, result = sandbox_manager.launch_sandbox(scenario_uuid=uuid)
    #
    # if result.returncode == 0:
    #     print(f"✅ Sandbox launched successfully!")
    # else:
    #     print(f"❌ Failed to launch sandbox")
    #     print(f"STDERR: {result.stderr}")
    #     return

    # For this example, we'll skip actual launch and just demonstrate other APIs
    print(f"   (Skipping actual launch for safety)")

    # Check status
    print(f"\n📊 Checking sandbox status...")
    status = sandbox_manager.get_sandbox_status(uuid)
    print(f"   Status: {status}")


def example_list_sandboxes():
    """Example: List all sandboxes."""
    print("\n" + "=" * 60)
    print("Example: List All Sandboxes")
    print("=" * 60)

    sandboxes = sandbox_manager.list_sandboxes()

    if not sandboxes:
        print("\n📭 No sandboxes found")
        return

    print(f"\n📦 Found {len(sandboxes)} sandbox(es):\n")

    for sb in sandboxes:
        status_icon = {
            "running": "🟢",
            "stopped": "🔴",
            "not_created": "⚪"
        }.get(sb.status, "❓")

        print(f"{status_icon} UUID: {sb.uuid}")
        print(f"   Status: {sb.status}")
        print(f"   Container: {sb.container_name}")
        print(f"   Build: {sb.build_size}")
        print(f"   Output: {sb.output_size} ({sb.output_files} files)")
        if sb.created_at:
            print(f"   Created: {sb.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print()


def example_get_info():
    """Example: Get info for a specific sandbox."""
    print("\n" + "=" * 60)
    print("Example: Get Sandbox Info")
    print("=" * 60)

    # Get first sandbox if exists
    sandboxes = sandbox_manager.list_sandboxes()

    if not sandboxes:
        print("\n📭 No sandboxes found. Create one first!")
        return

    uuid = sandboxes[0].uuid
    print(f"\n📋 Getting info for: {uuid}")

    info = sandbox_manager.get_sandbox_info(uuid)

    if info:
        print(f"\n✅ Sandbox Info:")
        print(f"   UUID: {info.uuid}")
        print(f"   Status: {info.status}")
        print(f"   Container: {info.container_name}")
        print(f"   Workspace: {info.workspace_path}")
        print(f"   Build: {info.build_size}")
        print(f"   Output: {info.output_size} ({info.output_files} files)")
        if info.created_at:
            print(f"   Created: {info.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print(f"\n❌ Sandbox not found")


def example_integration_with_scenario_manager():
    """Example: Integration with ScenarioManager."""
    print("\n" + "=" * 60)
    print("Example: Integration with ScenarioManager")
    print("=" * 60)

    from app.services import scenario_manager
    from app.models.scenario import Scenario

    # Generate UUID for new scenario
    sandbox_uuid = sandbox_manager.generate_uuid()
    print(f"\n📋 Generated sandbox UUID: {sandbox_uuid}")

    # Create scenario with sandbox UUID
    scenario = Scenario(
        id=f"scenario_{sandbox_uuid[:8]}",
        name="Test Scenario",
        description="Example scenario with sandbox integration",
        sandbox_uuid=sandbox_uuid,
        workspace_path=f"sandbox/workspace/{sandbox_uuid}"
    )

    print(f"\n📝 Created scenario:")
    print(f"   ID: {scenario.id}")
    print(f"   Name: {scenario.name}")
    print(f"   Sandbox UUID: {scenario.sandbox_uuid}")
    print(f"   Workspace: {scenario.workspace_path}")

    # Save scenario
    scenario_manager.create_scenario(scenario)
    print(f"\n✅ Scenario saved to data/scenarios/{scenario.id}.json")

    # Later, you can launch sandbox using the stored UUID
    # uuid, result = sandbox_manager.launch_sandbox(scenario_uuid=scenario.sandbox_uuid)


def main():
    """Main entry point."""
    print("\n🎯 SandboxManager Usage Examples\n")

    try:
        # Example 1: List sandboxes
        example_list_sandboxes()

        # Example 2: Get specific sandbox info
        example_get_info()

        # Example 3: Launch and monitor (commented out for safety)
        # example_launch_and_monitor()

        # Example 4: Integration with ScenarioManager
        example_integration_with_scenario_manager()

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 60)
    print("✅ Examples completed!")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
