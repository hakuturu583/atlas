"""
Cluster configuration models for ATLAS deployment
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, IPvAnyAddress
from enum import Enum


class NodeRole(str, Enum):
    """Node role in the cluster."""

    MANAGER = "manager"
    WORKER = "worker"


class DeploymentStatus(str, Enum):
    """Deployment status."""

    IDLE = "idle"
    CONFIGURING = "configuring"
    INSTALLING_DOCKER = "installing_docker"
    INITIALIZING_SWARM = "initializing_swarm"
    JOINING_SWARM = "joining_swarm"
    DEPLOYING_ATLAS = "deploying_atlas"
    COMPLETED = "completed"
    FAILED = "failed"


class NodeConfig(BaseModel):
    """Configuration for a single node."""

    id: str = Field(..., description="Unique node ID")
    hostname: str = Field(..., description="Hostname or display name")
    ip_address: str = Field(..., description="IP address")
    role: NodeRole = Field(..., description="Node role (manager/worker)")
    ssh_user: str = Field(default="ubuntu", description="SSH username")
    ssh_port: int = Field(default=22, description="SSH port")
    ssh_key_path: Optional[str] = Field(
        default=None, description="Path to SSH private key"
    )
    use_password: bool = Field(default=False, description="Use password authentication")
    ssh_password: Optional[str] = Field(
        default=None,
        description="SSH password (sensitive, handle with care)",
    )

    # Node capabilities
    has_gpu: bool = Field(default=False, description="Node has NVIDIA GPU")
    is_carla_host: bool = Field(default=False, description="Preferred CARLA host")
    has_storage: bool = Field(default=False, description="Node has large storage")

    # Metadata
    labels: Dict[str, str] = Field(default_factory=dict, description="Custom labels")


class ClusterConfig(BaseModel):
    """Complete cluster configuration."""

    name: str = Field(default="atlas", description="Cluster name")
    manager_node: NodeConfig = Field(..., description="Manager node configuration")
    worker_nodes: List[NodeConfig] = Field(
        default_factory=list, description="Worker nodes"
    )

    # Deployment options
    deploy_scenario: bool = Field(
        default=False, description="Deploy scenario execution container"
    )
    deploy_ad_stack: bool = Field(
        default=False, description="Deploy AD Stack (VLA dummy)"
    )
    build_alpamayo: bool = Field(
        default=False, description="Build and deploy Alpamayo VLA (requires deploy_ad_stack)"
    )
    local_registry_port: int = Field(
        default=5000, description="Local Docker registry port"
    )
    atlas_project_dir: str = Field(
        default="/opt/atlas", description="Project directory on manager node"
    )


class DeploymentTask(BaseModel):
    """Deployment task progress."""

    task_id: str = Field(..., description="Unique task ID")
    status: DeploymentStatus = Field(..., description="Current status")
    progress: float = Field(default=0.0, description="Progress percentage (0-100)")
    current_step: str = Field(default="", description="Current step description")
    logs: List[str] = Field(default_factory=list, description="Log messages")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    started_at: Optional[str] = Field(default=None, description="Start timestamp")
    completed_at: Optional[str] = Field(default=None, description="Completion timestamp")


class DeploymentRequest(BaseModel):
    """Request to start a deployment."""

    cluster_config: ClusterConfig = Field(..., description="Cluster configuration")
    skip_docker_setup: bool = Field(
        default=False, description="Skip Docker installation"
    )
    skip_swarm_init: bool = Field(
        default=False, description="Skip Swarm initialization"
    )
