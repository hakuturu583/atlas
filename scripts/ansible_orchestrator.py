#!/usr/bin/env python3
"""
Ansible Orchestrator CLI
Simplified interface for ATLAS infrastructure deployment using Ansible.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


class AnsibleOrchestrator:
    """Ansible playbook orchestrator for ATLAS deployment."""

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize the orchestrator.

        Args:
            project_root: Project root directory (defaults to parent of script dir)
        """
        if project_root is None:
            script_dir = Path(__file__).parent
            project_root = script_dir.parent

        self.project_root = project_root
        self.playbooks_dir = project_root / "playbooks"
        self.inventory_file = project_root / "inventory.ini"

        # Check if inventory file exists
        if not self.inventory_file.exists():
            print(f"⚠️  Inventory file not found: {self.inventory_file}")
            print(f"   Copy from example: cp inventory.ini.example inventory.ini")
            sys.exit(1)

    def run_playbook(
        self,
        playbook_name: str,
        extra_vars: Optional[dict] = None,
        tags: Optional[List[str]] = None,
        limit: Optional[str] = None,
        check: bool = False,
        verbose: bool = False,
        ask_become_pass: bool = False,
    ) -> int:
        """Run an Ansible playbook.

        Args:
            playbook_name: Name of the playbook (without .yml extension)
            extra_vars: Extra variables to pass to the playbook
            tags: Tags to run
            limit: Limit execution to specific hosts
            check: Run in check mode (dry run)
            verbose: Enable verbose output
            ask_become_pass: Ask for sudo password

        Returns:
            Exit code (0 for success)
        """
        playbook_path = self.playbooks_dir / f"{playbook_name}.yml"

        if not playbook_path.exists():
            print(f"❌ Playbook not found: {playbook_path}")
            return 1

        # Build ansible-playbook command
        cmd = [
            "ansible-playbook",
            str(playbook_path),
            "-i",
            str(self.inventory_file),
        ]

        # Add extra vars
        if extra_vars:
            for key, value in extra_vars.items():
                cmd.extend(["-e", f"{key}={value}"])

        # Add tags
        if tags:
            cmd.extend(["--tags", ",".join(tags)])

        # Add limit
        if limit:
            cmd.extend(["--limit", limit])

        # Add check mode
        if check:
            cmd.append("--check")

        # Add verbose
        if verbose:
            cmd.append("-vvv")

        # Add become password prompt
        if ask_become_pass:
            cmd.append("--ask-become-pass")

        # Display command
        print(f"🚀 Running: {' '.join(cmd)}")
        print()

        # Run command
        try:
            result = subprocess.run(cmd, cwd=self.project_root)
            return result.returncode
        except KeyboardInterrupt:
            print("\n⚠️  Interrupted by user")
            return 130
        except Exception as e:
            print(f"❌ Error running playbook: {e}")
            return 1

    def setup_docker(self, **kwargs) -> int:
        """Setup Docker on all hosts."""
        return self.run_playbook("setup_docker", **kwargs)

    def init_swarm(self, **kwargs) -> int:
        """Initialize Docker Swarm on manager node."""
        return self.run_playbook("init_swarm", **kwargs)

    def join_swarm(self, **kwargs) -> int:
        """Join worker nodes to Swarm."""
        return self.run_playbook("join_swarm", **kwargs)

    def deploy_atlas(self, with_alpamayo: bool = False, **kwargs) -> int:
        """Deploy ATLAS stack."""
        extra_vars = kwargs.pop("extra_vars", {})
        if with_alpamayo:
            extra_vars["build_alpamayo"] = "true"

        return self.run_playbook("deploy_atlas", extra_vars=extra_vars, **kwargs)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ATLAS Ansible Orchestrator - Infrastructure deployment automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Setup Docker on all hosts
  %(prog)s setup-docker

  # Initialize Swarm on manager
  %(prog)s init-swarm

  # Join workers to Swarm
  %(prog)s join-swarm

  # Deploy ATLAS with Alpamayo
  %(prog)s deploy-atlas --with-alpamayo

  # Dry run (check mode)
  %(prog)s setup-docker --check

  # Target specific host
  %(prog)s setup-docker --limit worker-node-1

  # Run with verbose output
  %(prog)s setup-docker --verbose
        """,
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Common arguments for all commands
    common_args = argparse.ArgumentParser(add_help=False)
    common_args.add_argument(
        "--check", action="store_true", help="Run in check mode (dry run)"
    )
    common_args.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    common_args.add_argument(
        "--limit", metavar="HOST", help="Limit execution to specific hosts"
    )
    common_args.add_argument(
        "--tags", metavar="TAG", nargs="+", help="Run only tasks with these tags"
    )
    common_args.add_argument(
        "--ask-become-pass",
        "-K",
        action="store_true",
        help="Ask for sudo password",
    )

    # setup-docker command
    subparsers.add_parser(
        "setup-docker",
        parents=[common_args],
        help="Setup Docker and Docker Compose on all hosts",
    )

    # init-swarm command
    subparsers.add_parser(
        "init-swarm",
        parents=[common_args],
        help="Initialize Docker Swarm on manager node",
    )

    # join-swarm command
    subparsers.add_parser(
        "join-swarm",
        parents=[common_args],
        help="Join worker nodes to Swarm cluster",
    )

    # deploy-atlas command
    deploy_parser = subparsers.add_parser(
        "deploy-atlas",
        parents=[common_args],
        help="Deploy ATLAS stack to Swarm",
    )
    deploy_parser.add_argument(
        "--with-alpamayo",
        action="store_true",
        help="Build and deploy Alpamayo VLA service",
    )

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Initialize orchestrator
    orchestrator = AnsibleOrchestrator()

    # Execute command
    kwargs = {
        "check": args.check,
        "verbose": args.verbose,
        "limit": args.limit,
        "tags": args.tags,
        "ask_become_pass": args.ask_become_pass,
    }

    if args.command == "setup-docker":
        return orchestrator.setup_docker(**kwargs)
    elif args.command == "init-swarm":
        return orchestrator.init_swarm(**kwargs)
    elif args.command == "join-swarm":
        return orchestrator.join_swarm(**kwargs)
    elif args.command == "deploy-atlas":
        return orchestrator.deploy_atlas(
            with_alpamayo=args.with_alpamayo, **kwargs
        )
    else:
        print(f"❌ Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
