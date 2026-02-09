"""Sandbox management service for CARLA scenarios."""

import subprocess
import uuid
import time
import socket
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class SandboxInfo:
    """Sandbox container information."""
    uuid: str
    container_name: str
    status: str  # "running", "stopped", "not_created"
    workspace_path: Path
    build_size: str
    output_size: str
    output_files: int
    created_at: Optional[datetime] = None


@dataclass
class LaunchResult:
    """Sandbox launch result with detailed status."""
    success: bool
    uuid: str
    container_name: str
    workspace_path: Path
    error_message: Optional[str] = None
    build_successful: Optional[bool] = None
    container_running: bool = False
    carla_connected: Optional[bool] = None
    logs: str = ""


class SandboxManager:
    """Manages CARLA sandbox containers."""

    def __init__(self, sandbox_dir: Optional[Path] = None):
        """Initialize sandbox manager.

        Args:
            sandbox_dir: Path to sandbox directory (default: ./sandbox)
        """
        self.sandbox_dir = sandbox_dir or Path("sandbox")
        self.workspace_dir = self.sandbox_dir / "workspace"
        self.run_script = self.sandbox_dir / "run.sh"
        self.shutdown_script = self.sandbox_dir / "shutdown.sh"

        # Ensure workspace directory exists
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

    def generate_uuid(self) -> str:
        """Generate a new UUID for a scenario.

        Returns:
            UUID string in lowercase
        """
        return str(uuid.uuid4())

    def launch_sandbox(
        self,
        scenario_uuid: Optional[str] = None,
        env: Optional[Dict[str, str]] = None
    ) -> tuple[str, subprocess.CompletedProcess]:
        """Launch a sandbox container.

        Args:
            scenario_uuid: UUID for the scenario (auto-generated if None)
            env: Additional environment variables

        Returns:
            Tuple of (uuid, subprocess result)
        """
        if scenario_uuid is None:
            scenario_uuid = self.generate_uuid()

        cmd = [str(self.run_script), scenario_uuid]

        # Merge environment variables
        run_env = {}
        if env:
            run_env.update(env)

        result = subprocess.run(
            cmd,
            cwd=str(self.sandbox_dir),
            env=run_env or None,
            capture_output=True,
            text=True
        )

        return scenario_uuid, result

    def stop_sandbox(
        self,
        scenario_uuid: str,
        remove_workspace: bool = False,
        force: bool = True
    ) -> subprocess.CompletedProcess:
        """Stop a sandbox container.

        Args:
            scenario_uuid: UUID of the scenario to stop
            remove_workspace: If True, also remove workspace directory
            force: If True, skip confirmation prompts

        Returns:
            Subprocess result
        """
        cmd = [str(self.shutdown_script), scenario_uuid]

        if remove_workspace:
            cmd.append("-v")
        if force:
            cmd.append("-f")

        result = subprocess.run(
            cmd,
            cwd=str(self.sandbox_dir),
            capture_output=True,
            text=True
        )

        return result

    def stop_all_sandboxes(
        self,
        remove_workspaces: bool = False,
        force: bool = True
    ) -> subprocess.CompletedProcess:
        """Stop all sandbox containers.

        Args:
            remove_workspaces: If True, also remove all workspace directories
            force: If True, skip confirmation prompts

        Returns:
            Subprocess result
        """
        cmd = [str(self.shutdown_script), "-a"]

        if remove_workspaces:
            cmd.append("-v")
        if force:
            cmd.append("-f")

        result = subprocess.run(
            cmd,
            cwd=str(self.sandbox_dir),
            capture_output=True,
            text=True
        )

        return result

    def get_sandbox_status(self, scenario_uuid: str) -> str:
        """Get the status of a sandbox container.

        Args:
            scenario_uuid: UUID of the scenario

        Returns:
            Status string: "running", "stopped", or "not_created"
        """
        container_name = f"carla-scenario-{scenario_uuid}"

        # Check if container exists and is running
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name=^{container_name}$", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0 and container_name in result.stdout:
            return "running"

        # Check if container exists but stopped
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", f"name=^{container_name}$", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0 and container_name in result.stdout:
            return "stopped"

        return "not_created"

    def list_sandboxes(self) -> List[SandboxInfo]:
        """List all sandbox workspaces.

        Returns:
            List of SandboxInfo objects
        """
        sandboxes = []

        if not self.workspace_dir.exists():
            return sandboxes

        for uuid_dir in self.workspace_dir.iterdir():
            if not uuid_dir.is_dir() or uuid_dir.name.startswith('.'):
                continue

            scenario_uuid = uuid_dir.name
            container_name = f"carla-scenario-{scenario_uuid}"

            # Get workspace sizes
            build_dir = uuid_dir / "build"
            output_dir = uuid_dir / "output"

            build_size = self._get_dir_size(build_dir)
            output_size = self._get_dir_size(output_dir)
            output_files = len(list(output_dir.glob("*"))) if output_dir.exists() else 0

            # Get container status
            status = self.get_sandbox_status(scenario_uuid)

            # Get creation time (approximate from directory mtime)
            created_at = datetime.fromtimestamp(uuid_dir.stat().st_mtime)

            sandboxes.append(SandboxInfo(
                uuid=scenario_uuid,
                container_name=container_name,
                status=status,
                workspace_path=uuid_dir,
                build_size=build_size,
                output_size=output_size,
                output_files=output_files,
                created_at=created_at
            ))

        # Sort by creation time (newest first)
        sandboxes.sort(key=lambda x: x.created_at or datetime.min, reverse=True)

        return sandboxes

    def get_sandbox_info(self, scenario_uuid: str) -> Optional[SandboxInfo]:
        """Get information about a specific sandbox.

        Args:
            scenario_uuid: UUID of the scenario

        Returns:
            SandboxInfo object or None if not found
        """
        uuid_dir = self.workspace_dir / scenario_uuid

        if not uuid_dir.exists():
            return None

        container_name = f"carla-scenario-{scenario_uuid}"

        # Get workspace sizes
        build_dir = uuid_dir / "build"
        output_dir = uuid_dir / "output"

        build_size = self._get_dir_size(build_dir)
        output_size = self._get_dir_size(output_dir)
        output_files = len(list(output_dir.glob("*"))) if output_dir.exists() else 0

        # Get container status
        status = self.get_sandbox_status(scenario_uuid)

        # Get creation time
        created_at = datetime.fromtimestamp(uuid_dir.stat().st_mtime)

        return SandboxInfo(
            uuid=scenario_uuid,
            container_name=container_name,
            status=status,
            workspace_path=uuid_dir,
            build_size=build_size,
            output_size=output_size,
            output_files=output_files,
            created_at=created_at
        )

    def cleanup_workspace(self, scenario_uuid: str) -> bool:
        """Remove a sandbox workspace directory.

        Args:
            scenario_uuid: UUID of the scenario

        Returns:
            True if successful, False otherwise
        """
        uuid_dir = self.workspace_dir / scenario_uuid

        if not uuid_dir.exists():
            return False

        # Make sure container is stopped first
        status = self.get_sandbox_status(scenario_uuid)
        if status == "running":
            self.stop_sandbox(scenario_uuid, remove_workspace=False, force=True)

        # Remove workspace directory
        import shutil
        shutil.rmtree(uuid_dir)

        return True

    def _get_dir_size(self, path: Path) -> str:
        """Get human-readable directory size.

        Args:
            path: Path to directory

        Returns:
            Size string like "128M", "1.2G", etc.
        """
        if not path.exists():
            return "0"

        result = subprocess.run(
            ["du", "-sh", str(path)],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            size = result.stdout.split()[0]
            return size

        return "unknown"


class SandboxLauncher:
    """High-level sandbox launcher with guaranteed startup."""

    def __init__(
        self,
        manager: Optional[SandboxManager] = None,
        carla_host: str = "localhost",
        carla_port: int = 2000
    ):
        """Initialize launcher.

        Args:
            manager: SandboxManager instance (uses global if None)
            carla_host: CARLA server host
            carla_port: CARLA server port
        """
        self.manager = manager or SandboxManager()
        self.carla_host = carla_host
        self.carla_port = carla_port

    def check_carla_server(self, timeout: float = 2.0) -> bool:
        """Check if CARLA server is running and accessible.

        Args:
            timeout: Connection timeout in seconds

        Returns:
            True if CARLA is accessible, False otherwise
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((self.carla_host, self.carla_port))
            sock.close()
            return result == 0
        except Exception as e:
            logger.debug(f"CARLA server check failed: {e}")
            return False

    def wait_for_container(
        self,
        scenario_uuid: str,
        timeout: float = 60.0,
        poll_interval: float = 1.0
    ) -> bool:
        """Wait for container to be running.

        Args:
            scenario_uuid: Scenario UUID
            timeout: Maximum wait time in seconds
            poll_interval: Time between status checks

        Returns:
            True if container is running, False on timeout
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            status = self.manager.get_sandbox_status(scenario_uuid)
            if status == "running":
                logger.info(f"Container for {scenario_uuid} is running")
                return True

            logger.debug(f"Container status: {status}, waiting...")
            time.sleep(poll_interval)

        logger.error(f"Container start timeout for {scenario_uuid}")
        return False

    def launch_with_validation(
        self,
        scenario_uuid: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        check_carla: bool = True,
        wait_for_ready: bool = True,
        timeout: float = 120.0
    ) -> LaunchResult:
        """Launch sandbox with full validation and guaranteed startup.

        Args:
            scenario_uuid: UUID for scenario (auto-generated if None)
            env: Additional environment variables
            check_carla: If True, check CARLA server before launching
            wait_for_ready: If True, wait for container to be ready
            timeout: Maximum wait time for container startup

        Returns:
            LaunchResult with detailed status
        """
        # Generate UUID if not provided
        if scenario_uuid is None:
            scenario_uuid = self.manager.generate_uuid()

        container_name = f"carla-scenario-{scenario_uuid}"
        workspace_path = self.manager.workspace_dir / scenario_uuid

        logger.info(f"Launching sandbox: {scenario_uuid}")

        # Pre-launch checks
        if check_carla:
            logger.info("Checking CARLA server...")
            if not self.check_carla_server():
                logger.warning("CARLA server is not accessible")
                return LaunchResult(
                    success=False,
                    uuid=scenario_uuid,
                    container_name=container_name,
                    workspace_path=workspace_path,
                    error_message="CARLA server is not accessible at "
                                  f"{self.carla_host}:{self.carla_port}",
                    carla_connected=False
                )
            logger.info("CARLA server is accessible ✓")

        # Ensure workspace directory exists
        workspace_path.mkdir(parents=True, exist_ok=True)
        (workspace_path / "build").mkdir(exist_ok=True)
        (workspace_path / "output").mkdir(exist_ok=True)

        # Launch sandbox
        logger.info("Starting sandbox container...")
        uuid_returned, result = self.manager.launch_sandbox(
            scenario_uuid=scenario_uuid,
            env=env
        )

        # Check if launch script succeeded
        if result.returncode != 0:
            logger.error(f"Launch script failed with code {result.returncode}")
            return LaunchResult(
                success=False,
                uuid=scenario_uuid,
                container_name=container_name,
                workspace_path=workspace_path,
                error_message=f"Launch script failed: {result.stderr}",
                logs=result.stdout + "\n" + result.stderr
            )

        # Wait for container to be running
        if wait_for_ready:
            logger.info("Waiting for container to be ready...")
            if not self.wait_for_container(scenario_uuid, timeout=timeout):
                return LaunchResult(
                    success=False,
                    uuid=scenario_uuid,
                    container_name=container_name,
                    workspace_path=workspace_path,
                    error_message="Container failed to start within timeout",
                    logs=result.stdout + "\n" + result.stderr
                )

        # Final status check
        status = self.manager.get_sandbox_status(scenario_uuid)
        container_running = (status == "running")

        # Check if workspace was created
        workspace_exists = workspace_path.exists()

        logger.info(f"Sandbox launch completed: {scenario_uuid}")
        logger.info(f"  Container running: {container_running}")
        logger.info(f"  Workspace exists: {workspace_exists}")

        return LaunchResult(
            success=container_running,
            uuid=scenario_uuid,
            container_name=container_name,
            workspace_path=workspace_path,
            container_running=container_running,
            carla_connected=check_carla,
            logs=result.stdout + "\n" + result.stderr
        )

    def launch_and_wait(
        self,
        scenario_uuid: Optional[str] = None,
        timeout: float = 120.0
    ) -> LaunchResult:
        """Convenience method: launch with all validations enabled.

        Args:
            scenario_uuid: UUID for scenario (auto-generated if None)
            timeout: Maximum wait time

        Returns:
            LaunchResult with detailed status
        """
        return self.launch_with_validation(
            scenario_uuid=scenario_uuid,
            check_carla=True,
            wait_for_ready=True,
            timeout=timeout
        )


# Global instances
sandbox_manager = SandboxManager()
sandbox_launcher = SandboxLauncher()
