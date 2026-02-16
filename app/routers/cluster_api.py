"""
Cluster configuration and deployment API endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.models.cluster import (
    ClusterConfig,
    DeploymentRequest,
    DeploymentTask,
    NodeConfig,
)
from app.services.cluster_manager import cluster_manager

router = APIRouter(prefix="/api/cluster", tags=["cluster"])


@router.post("/deploy")
async def deploy_cluster(request: DeploymentRequest) -> dict:
    """Start cluster deployment.

    Args:
        request: Deployment request

    Returns:
        Task ID for tracking deployment
    """
    try:
        # Save config
        cluster_manager.save_cluster_config(request.cluster_config)

        # Start deployment
        task_id = await cluster_manager.deploy_cluster(
            request.cluster_config,
            skip_docker_setup=request.skip_docker_setup,
            skip_swarm_init=request.skip_swarm_init,
        )

        return {"task_id": task_id, "status": "started"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deployment/{task_id}")
async def get_deployment_status(task_id: str) -> DeploymentTask:
    """Get deployment task status.

    Args:
        task_id: Task ID

    Returns:
        Deployment task status
    """
    task = cluster_manager.get_deployment_status(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return task


@router.get("/deployments")
async def list_deployments() -> List[DeploymentTask]:
    """List all deployment tasks.

    Returns:
        List of deployment tasks
    """
    return cluster_manager.list_deployments()


@router.post("/config/save")
async def save_cluster_config(config: ClusterConfig) -> dict:
    """Save cluster configuration.

    Args:
        config: Cluster configuration

    Returns:
        Success message
    """
    try:
        cluster_manager.save_cluster_config(config)
        return {"status": "success", "name": config.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/{name}")
async def get_cluster_config(name: str) -> ClusterConfig:
    """Get cluster configuration by name.

    Args:
        name: Cluster name

    Returns:
        Cluster configuration
    """
    config = cluster_manager.load_cluster_config(name)
    if config is None:
        raise HTTPException(status_code=404, detail="Configuration not found")

    return config


@router.get("/configs")
async def list_cluster_configs() -> List[str]:
    """List saved cluster configurations.

    Returns:
        List of cluster names
    """
    return cluster_manager.list_cluster_configs()


@router.post("/config/validate")
async def validate_cluster_config(config: ClusterConfig) -> dict:
    """Validate cluster configuration.

    Args:
        config: Cluster configuration

    Returns:
        Validation result
    """
    errors = []

    # Check manager node
    if not config.manager_node.ip_address:
        errors.append("Manager node IP address is required")

    # Check for duplicate IPs
    all_ips = [config.manager_node.ip_address]
    all_ips.extend([w.ip_address for w in config.worker_nodes])
    if len(all_ips) != len(set(all_ips)):
        errors.append("Duplicate IP addresses found")

    # Check for duplicate hostnames
    all_hostnames = [config.manager_node.hostname]
    all_hostnames.extend([w.hostname for w in config.worker_nodes])
    if len(all_hostnames) != len(set(all_hostnames)):
        errors.append("Duplicate hostnames found")

    if errors:
        return {"valid": False, "errors": errors}

    return {"valid": True, "errors": []}
