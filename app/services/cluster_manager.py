"""
Cluster configuration and deployment management service
"""

import asyncio
import json
import logging
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from app.models.cluster import (
    ClusterConfig,
    DeploymentStatus,
    DeploymentTask,
    NodeConfig,
)

logger = logging.getLogger(__name__)


class ClusterManager:
    """Manages cluster configuration and deployment."""

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize cluster manager.

        Args:
            project_root: Project root directory
        """
        if project_root is None:
            project_root = Path(__file__).parent.parent.parent

        self.project_root = project_root
        self.inventory_dir = project_root / "data" / "inventory"
        self.inventory_dir.mkdir(parents=True, exist_ok=True)

        # Active deployments
        self.deployments: Dict[str, DeploymentTask] = {}

    def generate_inventory(self, config: ClusterConfig) -> str:
        """Generate Ansible inventory from cluster config.

        Args:
            config: Cluster configuration

        Returns:
            Path to generated inventory file
        """
        inventory_path = self.inventory_dir / f"inventory_{config.name}.ini"

        inventory_content = self._build_inventory_content(config)

        inventory_path.write_text(inventory_content)
        logger.info(f"Generated inventory at {inventory_path}")

        return str(inventory_path)

    def _build_inventory_content(self, config: ClusterConfig) -> str:
        """Build inventory file content.

        Args:
            config: Cluster configuration

        Returns:
            Inventory file content
        """
        lines = ["# Auto-generated Ansible inventory for ATLAS cluster", ""]

        # Manager section
        lines.append("[manager]")
        manager = config.manager_node
        manager_line = (
            f"{manager.hostname} "
            f"ansible_host={manager.ip_address} "
            f"ansible_user={manager.ssh_user} "
            f"ansible_port={manager.ssh_port}"
        )
        if manager.ssh_key_path:
            manager_line += f" ansible_ssh_private_key_file={manager.ssh_key_path}"
        lines.append(manager_line)
        lines.append("")

        # Workers section
        if config.worker_nodes:
            lines.append("[workers]")
            for worker in config.worker_nodes:
                worker_line = (
                    f"{worker.hostname} "
                    f"ansible_host={worker.ip_address} "
                    f"ansible_user={worker.ssh_user} "
                    f"ansible_port={worker.ssh_port}"
                )
                if worker.ssh_key_path:
                    worker_line += f" ansible_ssh_private_key_file={worker.ssh_key_path}"
                if worker.has_gpu:
                    worker_line += " gpu=true"
                if worker.is_carla_host:
                    worker_line += " carla=true"
                if worker.has_storage:
                    worker_line += " storage=true"
                lines.append(worker_line)
            lines.append("")

        # Global vars
        lines.append("[all:vars]")
        lines.append("ansible_python_interpreter=/usr/bin/python3")
        lines.append("ansible_ssh_common_args='-o StrictHostKeyChecking=no'")
        lines.append(f"atlas_stack_name={config.name}")
        lines.append(f"atlas_project_dir={config.atlas_project_dir}")
        lines.append(f"local_registry_port={config.local_registry_port}")
        if config.build_alpamayo:
            lines.append("build_alpamayo=true")
        lines.append("")

        return "\n".join(lines)

    async def deploy_cluster(
        self,
        config: ClusterConfig,
        skip_docker_setup: bool = False,
        skip_swarm_init: bool = False,
    ) -> str:
        """Deploy ATLAS cluster using Ansible.

        Args:
            config: Cluster configuration
            skip_docker_setup: Skip Docker installation
            skip_swarm_init: Skip Swarm initialization

        Returns:
            Task ID for tracking deployment progress
        """
        task_id = str(uuid.uuid4())

        deployment_task = DeploymentTask(
            task_id=task_id,
            status=DeploymentStatus.CONFIGURING,
            progress=0.0,
            current_step="Generating inventory",
            started_at=datetime.now().isoformat(),
        )

        self.deployments[task_id] = deployment_task

        # Start deployment in background
        asyncio.create_task(
            self._run_deployment(task_id, config, skip_docker_setup, skip_swarm_init)
        )

        return task_id

    async def _run_deployment(
        self,
        task_id: str,
        config: ClusterConfig,
        skip_docker_setup: bool,
        skip_swarm_init: bool,
    ):
        """Run deployment process.

        Args:
            task_id: Task ID
            config: Cluster configuration
            skip_docker_setup: Skip Docker installation
            skip_swarm_init: Skip Swarm initialization
        """
        task = self.deployments[task_id]

        try:
            # Step 1: Generate inventory
            task.current_step = "Generating inventory"
            task.progress = 5.0
            inventory_path = self.generate_inventory(config)
            task.logs.append(f"✓ Generated inventory: {inventory_path}")

            # Step 2: Setup Docker (optional)
            if not skip_docker_setup:
                task.status = DeploymentStatus.INSTALLING_DOCKER
                task.current_step = "Installing Docker on all nodes"
                task.progress = 10.0
                await self._run_playbook(
                    task, "setup_docker", inventory_path, progress_start=10, progress_end=30
                )

            # Step 3: Initialize Swarm (optional)
            if not skip_swarm_init:
                task.status = DeploymentStatus.INITIALIZING_SWARM
                task.current_step = "Initializing Docker Swarm on manager"
                task.progress = 35.0
                await self._run_playbook(
                    task, "init_swarm", inventory_path, progress_start=35, progress_end=50
                )

                # Step 4: Join workers
                if config.worker_nodes:
                    task.status = DeploymentStatus.JOINING_SWARM
                    task.current_step = "Joining worker nodes to Swarm"
                    task.progress = 55.0
                    await self._run_playbook(
                        task, "join_swarm", inventory_path, progress_start=55, progress_end=70
                    )

            # Step 5: Deploy ATLAS
            task.status = DeploymentStatus.DEPLOYING_ATLAS
            task.current_step = "Deploying ATLAS stack"
            task.progress = 75.0

            # Prepare deployment options
            deploy_options = {
                "deploy_scenario": config.deploy_scenario,
                "deploy_ad_stack": config.deploy_ad_stack,
                "build_alpamayo": config.build_alpamayo,
            }
            task.logs.append(f"  Deployment options: {deploy_options}")

            await self._run_playbook(
                task,
                "deploy_atlas",
                inventory_path,
                progress_start=75,
                progress_end=95,
                extra_vars=deploy_options,
            )

            # Completion
            task.status = DeploymentStatus.COMPLETED
            task.current_step = "Deployment completed"
            task.progress = 100.0
            task.completed_at = datetime.now().isoformat()
            task.logs.append("✓ ATLAS cluster deployed successfully!")

        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            task.status = DeploymentStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now().isoformat()
            task.logs.append(f"✗ Deployment failed: {e}")

    async def _run_playbook(
        self,
        task: DeploymentTask,
        playbook_name: str,
        inventory_path: str,
        progress_start: float,
        progress_end: float,
        extra_vars: Optional[Dict[str, Any]] = None,
    ):
        """Run an Ansible playbook.

        Args:
            task: Deployment task
            playbook_name: Playbook name (without .yml)
            inventory_path: Path to inventory file
            progress_start: Starting progress percentage
            progress_end: Ending progress percentage
            extra_vars: Extra variables to pass to playbook
        """
        playbook_path = self.project_root / "playbooks" / f"{playbook_name}.yml"

        cmd = [
            "ansible-playbook",
            str(playbook_path),
            "-i",
            inventory_path,
        ]

        # Add extra variables if provided
        if extra_vars:
            import json

            extra_vars_json = json.dumps(extra_vars)
            cmd.extend(["--extra-vars", extra_vars_json])

        task.logs.append(f"▶ Running: {' '.join(cmd)}")

        # Run playbook
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(self.project_root),
        )

        # Read output line by line
        line_count = 0
        max_lines = 50  # Estimate
        while True:
            line = await process.stdout.readline()
            if not line:
                break

            line_text = line.decode().strip()
            if line_text:
                task.logs.append(line_text)
                line_count += 1

                # Update progress
                progress_range = progress_end - progress_start
                progress_increment = progress_range / max_lines
                task.progress = min(
                    progress_end, progress_start + (line_count * progress_increment)
                )

        await process.wait()

        if process.returncode != 0:
            raise RuntimeError(
                f"Playbook {playbook_name} failed with exit code {process.returncode}"
            )

        task.progress = progress_end
        task.logs.append(f"✓ {playbook_name} completed")

    def get_deployment_status(self, task_id: str) -> Optional[DeploymentTask]:
        """Get deployment task status.

        Args:
            task_id: Task ID

        Returns:
            Deployment task or None if not found
        """
        return self.deployments.get(task_id)

    def list_deployments(self) -> List[DeploymentTask]:
        """List all deployment tasks.

        Returns:
            List of deployment tasks
        """
        return list(self.deployments.values())

    def save_cluster_config(self, config: ClusterConfig):
        """Save cluster configuration to disk.

        Args:
            config: Cluster configuration
        """
        config_path = self.inventory_dir / f"cluster_{config.name}.json"
        config_path.write_text(config.model_dump_json(indent=2))
        logger.info(f"Saved cluster config to {config_path}")

    def load_cluster_config(self, name: str) -> Optional[ClusterConfig]:
        """Load cluster configuration from disk.

        Args:
            name: Cluster name

        Returns:
            Cluster configuration or None if not found
        """
        config_path = self.inventory_dir / f"cluster_{name}.json"
        if not config_path.exists():
            return None

        return ClusterConfig.model_validate_json(config_path.read_text())

    def list_cluster_configs(self) -> List[str]:
        """List saved cluster configurations.

        Returns:
            List of cluster names
        """
        configs = []
        for path in self.inventory_dir.glob("cluster_*.json"):
            name = path.stem.replace("cluster_", "")
            configs.append(name)
        return configs


# Global instance
cluster_manager = ClusterManager()
