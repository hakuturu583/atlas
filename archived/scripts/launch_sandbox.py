#!/usr/bin/env python3
"""CLI tool for managing CARLA sandbox containers."""

import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.sandbox_manager import sandbox_manager


def cmd_launch(args):
    """Launch a sandbox container."""
    print(f"🚀 Launching sandbox...")

    if args.uuid:
        print(f"   Using UUID: {args.uuid}")
    else:
        print(f"   Generating new UUID...")

    scenario_uuid, result = sandbox_manager.launch_sandbox(
        scenario_uuid=args.uuid,
        env=None
    )

    print(f"\n📦 Sandbox UUID: {scenario_uuid}")
    print(f"   Workspace: sandbox/workspace/{scenario_uuid}")

    if result.returncode == 0:
        print(f"\n✅ Sandbox launched successfully!")
    else:
        print(f"\n❌ Failed to launch sandbox")
        print(f"\nSTDOUT:\n{result.stdout}")
        print(f"\nSTDERR:\n{result.stderr}")
        sys.exit(1)


def cmd_stop(args):
    """Stop a sandbox container."""
    if not args.uuid:
        print("❌ Error: UUID is required for stop command")
        sys.exit(1)

    print(f"🛑 Stopping sandbox {args.uuid}...")

    if args.clean:
        print(f"   Will also remove workspace directory")

    result = sandbox_manager.stop_sandbox(
        scenario_uuid=args.uuid,
        remove_workspace=args.clean,
        force=True
    )

    if result.returncode == 0:
        print(f"✅ Sandbox stopped successfully!")
    else:
        print(f"❌ Failed to stop sandbox")
        print(f"\nSTDOUT:\n{result.stdout}")
        print(f"\nSTDERR:\n{result.stderr}")
        sys.exit(1)


def cmd_stop_all(args):
    """Stop all sandbox containers."""
    print(f"🛑 Stopping all sandboxes...")

    if args.clean:
        print(f"   Will also remove all workspace directories")

    result = sandbox_manager.stop_all_sandboxes(
        remove_workspaces=args.clean,
        force=True
    )

    if result.returncode == 0:
        print(f"✅ All sandboxes stopped successfully!")
    else:
        print(f"❌ Failed to stop sandboxes")
        print(f"\nSTDOUT:\n{result.stdout}")
        print(f"\nSTDERR:\n{result.stderr}")
        sys.exit(1)


def cmd_list(args):
    """List all sandbox workspaces."""
    sandboxes = sandbox_manager.list_sandboxes()

    if not sandboxes:
        print("📭 No sandboxes found")
        return

    print(f"📦 Found {len(sandboxes)} sandbox(es):\n")

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


def cmd_status(args):
    """Get status of a specific sandbox."""
    if not args.uuid:
        print("❌ Error: UUID is required for status command")
        sys.exit(1)

    info = sandbox_manager.get_sandbox_info(args.uuid)

    if not info:
        print(f"❌ Sandbox {args.uuid} not found")
        sys.exit(1)

    status_icon = {
        "running": "🟢",
        "stopped": "🔴",
        "not_created": "⚪"
    }.get(info.status, "❓")

    print(f"{status_icon} Sandbox: {info.uuid}")
    print(f"   Status: {info.status}")
    print(f"   Container: {info.container_name}")
    print(f"   Workspace: {info.workspace_path}")
    print(f"   Build: {info.build_size}")
    print(f"   Output: {info.output_size} ({info.output_files} files)")
    if info.created_at:
        print(f"   Created: {info.created_at.strftime('%Y-%m-%d %H:%M:%S')}")


def cmd_clean(args):
    """Clean up a sandbox workspace."""
    if not args.uuid:
        print("❌ Error: UUID is required for clean command")
        sys.exit(1)

    print(f"🧹 Cleaning sandbox {args.uuid}...")

    if sandbox_manager.cleanup_workspace(args.uuid):
        print(f"✅ Workspace cleaned successfully!")
    else:
        print(f"❌ Failed to clean workspace (not found or in use)")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="CARLA Sandbox Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Launch a new sandbox
  %(prog)s launch

  # Launch with specific UUID
  %(prog)s launch --uuid 550e8400-e29b-41d4-a716-446655440000

  # List all sandboxes
  %(prog)s list

  # Get status of a sandbox
  %(prog)s status --uuid 550e8400-e29b-41d4-a716-446655440000

  # Stop a sandbox
  %(prog)s stop --uuid 550e8400-e29b-41d4-a716-446655440000

  # Stop and clean workspace
  %(prog)s stop --uuid 550e8400-e29b-41d4-a716-446655440000 --clean

  # Stop all sandboxes
  %(prog)s stop-all

  # Clean workspace
  %(prog)s clean --uuid 550e8400-e29b-41d4-a716-446655440000
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Launch command
    parser_launch = subparsers.add_parser("launch", help="Launch a sandbox")
    parser_launch.add_argument("--uuid", "-u", help="Scenario UUID (auto-generated if not provided)")
    parser_launch.set_defaults(func=cmd_launch)

    # Stop command
    parser_stop = subparsers.add_parser("stop", help="Stop a sandbox")
    parser_stop.add_argument("--uuid", "-u", required=True, help="Scenario UUID")
    parser_stop.add_argument("--clean", "-c", action="store_true", help="Also remove workspace")
    parser_stop.set_defaults(func=cmd_stop)

    # Stop-all command
    parser_stop_all = subparsers.add_parser("stop-all", help="Stop all sandboxes")
    parser_stop_all.add_argument("--clean", "-c", action="store_true", help="Also remove all workspaces")
    parser_stop_all.set_defaults(func=cmd_stop_all)

    # List command
    parser_list = subparsers.add_parser("list", help="List all sandboxes")
    parser_list.set_defaults(func=cmd_list)

    # Status command
    parser_status = subparsers.add_parser("status", help="Get sandbox status")
    parser_status.add_argument("--uuid", "-u", required=True, help="Scenario UUID")
    parser_status.set_defaults(func=cmd_status)

    # Clean command
    parser_clean = subparsers.add_parser("clean", help="Clean workspace")
    parser_clean.add_argument("--uuid", "-u", required=True, help="Scenario UUID")
    parser_clean.set_defaults(func=cmd_clean)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    args.func(args)


if __name__ == "__main__":
    main()
