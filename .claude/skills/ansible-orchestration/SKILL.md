---
name: ansible-orchestration
description: >
  This skill should be used when the user asks to "deploy infrastructure",
  "ansible playbook", "ansible実行", "インフラデプロイ", "クラスタ構築",
  "setup docker", "init swarm", "join swarm", or "deploy atlas".
  Orchestrates multi-host deployments using Ansible for Docker Swarm clusters.
---

# Ansible Orchestration Skill

**Role**: Multi-host infrastructure automation using Ansible for ATLAS deployment

## When to Use This Skill

Trigger when the user mentions:
- "ansible"
- "deploy infrastructure"
- "playbook実行"
- "クラスタ構築"
- "setup docker"
- "init swarm"
- "join swarm"
- "deploy atlas"
- "インフラ自動化"

## Main Functions

This skill provides automated infrastructure management for ATLAS deployment:

### 1. Docker Setup (`setup-docker`)

Installs Docker and Docker Compose on target hosts.

**Usage**:
```bash
uv run python scripts/ansible_orchestrator.py setup-docker
```

**What it does**:
- Installs Docker CE and Docker Compose
- Configures Docker daemon
- Adds user to docker group
- Enables Docker service
- Installs NVIDIA Docker (if GPU available)

**Target hosts**: All hosts in inventory

### 2. Swarm Initialization (`init-swarm`)

Initializes Docker Swarm on the manager node.

**Usage**:
```bash
uv run python scripts/ansible_orchestrator.py init-swarm
```

**What it does**:
- Initializes Swarm on manager node
- Generates worker join token
- Saves token to local file
- Labels manager node for deployment

**Target hosts**: Manager node only

### 3. Swarm Join (`join-swarm`)

Joins worker nodes to the Swarm cluster.

**Usage**:
```bash
uv run python scripts/ansible_orchestrator.py join-swarm
```

**What it does**:
- Retrieves join token from manager
- Joins worker nodes to Swarm
- Labels nodes based on capabilities (GPU, storage)

**Target hosts**: Worker nodes

### 4. ATLAS Deployment (`deploy-atlas`)

Deploys ATLAS stack to the Swarm cluster.

**Usage**:
```bash
uv run python scripts/ansible_orchestrator.py deploy-atlas
```

**What it does**:
- Copies project files to manager node
- Builds Docker images
- Pushes images to registry
- Deploys stack using docker-compose.stack.yml

**Target hosts**: Manager node

## Inventory Management

The inventory file (`inventory.ini`) defines the cluster topology:

```ini
[manager]
manager-node ansible_host=192.168.1.10 ansible_user=ubuntu

[workers]
worker-node-1 ansible_host=192.168.1.11 ansible_user=ubuntu gpu=true
worker-node-2 ansible_host=192.168.1.12 ansible_user=ubuntu

[all:vars]
ansible_python_interpreter=/usr/bin/python3
ansible_ssh_common_args='-o StrictHostKeyChecking=no'
```

**Node labels**:
- `gpu=true`: Node has NVIDIA GPU
- `carla=true`: Preferred node for CARLA server
- `storage=true`: Node has large storage for logs/videos

## Workflow Example

**Complete cluster setup**:

```bash
# Step 1: Setup Docker on all nodes
uv run python scripts/ansible_orchestrator.py setup-docker

# Step 2: Initialize Swarm on manager
uv run python scripts/ansible_orchestrator.py init-swarm

# Step 3: Join workers to Swarm
uv run python scripts/ansible_orchestrator.py join-swarm

# Step 4: Deploy ATLAS
uv run python scripts/ansible_orchestrator.py deploy-atlas
```

## Advanced Usage

### Dry Run (Check Mode)

```bash
# See what would be changed without applying
uv run python scripts/ansible_orchestrator.py setup-docker --check
```

### Target Specific Hosts

```bash
# Only setup Docker on specific host
uv run python scripts/ansible_orchestrator.py setup-docker --limit worker-node-1
```

### Run with Tags

```bash
# Only run GPU-related tasks
uv run python scripts/ansible_orchestrator.py setup-docker --tags gpu
```

### Verbose Output

```bash
# Show detailed execution logs
uv run python scripts/ansible_orchestrator.py setup-docker --verbose
```

## Requirements

### Local Machine

- Python 3.10+
- Ansible 2.10+
- SSH access to all nodes
- Inventory file configured

### Target Hosts

- Ubuntu 20.04+ / Debian 11+
- Python 3.8+
- sudo privileges
- Internet access (for package installation)

## Troubleshooting

### SSH Connection Errors

```bash
# Test SSH connectivity
ansible all -m ping -i inventory.ini

# Use password authentication
ansible all -m ping -i inventory.ini --ask-pass

# Use sudo password
ansible all -m ping -i inventory.ini --ask-become-pass
```

### Playbook Execution Errors

```bash
# Run with verbose output
uv run python scripts/ansible_orchestrator.py setup-docker --verbose

# Check syntax before running
ansible-playbook playbooks/setup_docker.yml --syntax-check
```

### Docker Installation Issues

```bash
# Manually check Docker on a node
ssh ubuntu@192.168.1.10 "docker --version"

# Remove and reinstall
uv run python scripts/ansible_orchestrator.py setup-docker --tags remove,install
```

## Security Considerations

### SSH Key Management

Use SSH keys instead of passwords:

```bash
# Generate SSH key
ssh-keygen -t ed25519 -C "atlas-deployment"

# Copy to all nodes
ssh-copy-id -i ~/.ssh/id_ed25519.pub ubuntu@192.168.1.10
```

### Ansible Vault for Secrets

```bash
# Encrypt sensitive variables
ansible-vault encrypt_string 'secret-password' --name 'docker_registry_password'

# Use encrypted variables in playbooks
uv run python scripts/ansible_orchestrator.py deploy-atlas --ask-vault-pass
```

## Files Created by This Skill

- `inventory.ini`: Cluster node inventory
- `playbooks/setup_docker.yml`: Docker installation playbook
- `playbooks/init_swarm.yml`: Swarm initialization playbook
- `playbooks/join_swarm.yml`: Worker join playbook
- `playbooks/deploy_atlas.yml`: ATLAS deployment playbook
- `scripts/ansible_orchestrator.py`: CLI tool for playbook execution
- `.ansible/`: Ansible cache and logs

## Next Steps After Deployment

1. **Verify Cluster**:
   ```bash
   ssh ubuntu@manager-node "docker node ls"
   ```

2. **Check Services**:
   ```bash
   ssh ubuntu@manager-node "docker stack services atlas"
   ```

3. **View Logs**:
   ```bash
   ssh ubuntu@manager-node "docker service logs -f atlas_scenario"
   ```

4. **Run Scenario**:
   ```bash
   ssh ubuntu@manager-node "docker exec -it \$(docker ps -qf 'name=atlas_scenario') python examples/agent_controller_callback.py"
   ```

## Reference

- [Ansible Documentation](https://docs.ansible.com/)
- [Docker Swarm Mode](https://docs.docker.com/engine/swarm/)
- [Ansible Best Practices](https://docs.ansible.com/ansible/latest/tips_tricks/ansible_tips_tricks.html)
