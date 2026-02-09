#!/usr/bin/env python3
"""
Automatic sandbox launcher with guaranteed startup.

This script launches a CARLA sandbox with full validation:
- Checks CARLA server connectivity
- Auto-generates UUID
- Creates workspace directories
- Waits for container to be ready
- Validates successful startup
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services import sandbox_launcher


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Automatic CARLA Sandbox Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This launcher provides guaranteed startup with validation:

1. Checks CARLA server connectivity (localhost:2000)
2. Auto-generates UUID for the scenario
3. Creates workspace directories
4. Launches sandbox container
5. Waits for container to be ready
6. Validates successful startup

Examples:
  # Launch with all validations
  %(prog)s

  # Launch with specific UUID
  %(prog)s --uuid 550e8400-e29b-41d4-a716-446655440000

  # Launch without CARLA check (for testing)
  %(prog)s --no-check-carla

  # Launch with custom timeout
  %(prog)s --timeout 180
        """
    )

    parser.add_argument(
        "--uuid", "-u",
        help="Scenario UUID (auto-generated if not provided)"
    )
    parser.add_argument(
        "--carla-host",
        default="localhost",
        help="CARLA server host (default: localhost)"
    )
    parser.add_argument(
        "--carla-port",
        type=int,
        default=2000,
        help="CARLA server port (default: 2000)"
    )
    parser.add_argument(
        "--timeout", "-t",
        type=float,
        default=120.0,
        help="Container startup timeout in seconds (default: 120)"
    )
    parser.add_argument(
        "--no-check-carla",
        action="store_true",
        help="Skip CARLA server connectivity check"
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Don't wait for container to be ready"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed logs"
    )

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        import logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    print("=" * 70)
    print("🚀 CARLA Sandbox Automatic Launcher")
    print("=" * 70)
    print()

    # Update launcher configuration
    sandbox_launcher.carla_host = args.carla_host
    sandbox_launcher.carla_port = args.carla_port

    # Launch with validation
    print("📋 Configuration:")
    print(f"   CARLA Server: {args.carla_host}:{args.carla_port}")
    print(f"   UUID: {args.uuid or '(auto-generate)'}")
    print(f"   Check CARLA: {not args.no_check_carla}")
    print(f"   Wait for ready: {not args.no_wait}")
    print(f"   Timeout: {args.timeout}s")
    print()

    print("🔄 Launching sandbox...")
    print()

    result = sandbox_launcher.launch_with_validation(
        scenario_uuid=args.uuid,
        check_carla=not args.no_check_carla,
        wait_for_ready=not args.no_wait,
        timeout=args.timeout
    )

    # Display results
    print("=" * 70)
    if result.success:
        print("✅ Sandbox launched successfully!")
    else:
        print("❌ Sandbox launch failed")
    print("=" * 70)
    print()

    print("📦 Sandbox Information:")
    print(f"   UUID: {result.uuid}")
    print(f"   Container: {result.container_name}")
    print(f"   Workspace: {result.workspace_path}")
    print(f"   Status: {'Running' if result.container_running else 'Not Running'}")
    print()

    if result.carla_connected is not None:
        carla_status = "Connected ✓" if result.carla_connected else "Not Connected ✗"
        print(f"   CARLA: {carla_status}")
        print()

    if result.error_message:
        print("⚠️  Error Details:")
        print(f"   {result.error_message}")
        print()

    if args.verbose and result.logs:
        print("📝 Logs:")
        print("-" * 70)
        print(result.logs)
        print("-" * 70)
        print()

    if result.success:
        print("💡 Next Steps:")
        print(f"   - Check status: uv run python scripts/launch_sandbox.py status --uuid {result.uuid}")
        print(f"   - View output: ls -lh {result.workspace_path}/output/")
        print(f"   - Stop sandbox: uv run python scripts/launch_sandbox.py stop --uuid {result.uuid}")
        print()

        sys.exit(0)
    else:
        print("💡 Troubleshooting:")
        if result.carla_connected is False:
            print("   - Make sure CARLA server is running:")
            print("     cd /path/to/carla && ./CarlaUE4.sh")
        print("   - Check Docker status: docker ps")
        print("   - View logs with --verbose flag")
        print()

        sys.exit(1)


if __name__ == "__main__":
    main()
