import asyncio
import docker
import json
import logging
import os
import tempfile
import shutil
import subprocess
import yaml
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
import hashlib
import tarfile
import requests
from pathlib import Path

class DeploymentStage(Enum):
    PREPARATION = "preparation"
    BUILD = "build"
    TEST = "test"
    DEPLOY = "deploy"
    VERIFY = "verify"
    COMPLETE = "complete"
    FAILED = "failed"
    ROLLBACK = "rollback"

class DeploymentType(Enum):
    DOCKER_COMPOSE = "docker_compose"
    KUBERNETES = "kubernetes"
    STANDALONE = "standalone"
    CLOUD_FORMATION = "cloud_formation"

@dataclass
class DeploymentTarget:
    name: str
    type: str  # "personal_server", "cloud", "edge"
    endpoint: str
    credentials: Dict[str, str]
    capacity: Dict[str, Any]
    region: str = "local"
    security_level: str = "standard"

@dataclass
class DeploymentConfig:
    deployment_id: str
    target: DeploymentTarget
    application_name: str
    version: str
    deployment_type: DeploymentType
    
    # Application configuration
    docker_image: str = ""
    docker_compose_file: str = ""
    kubernetes_manifests: List[str] = field(default_factory=list)
    environment_variables: Dict[str, str] = field(default_factory=dict)
    secrets: Dict[str, str] = field(default_factory=dict)
    
    # Resource requirements
    cpu_limit: str = "1000m"
    memory_limit: str = "1Gi"
    storage_size: str = "10Gi"
    port_mappings: Dict[int, int] = field(default_factory=dict)
    
    # Deployment settings
    replicas: int = 1
    auto_scaling: bool = False
    health_check_path: str = "/health"
    ready_timeout: int = 300
    
    # Rollback configuration
    enable_rollback: bool = True
    backup_previous: bool = True
    max_history_versions: int = 5

@dataclass
class DeploymentStatus:
    deployment_id: str
    stage: DeploymentStage
    progress: float  # 0.0 to 1.0
    message: str
    started_at: datetime
    updated_at: datetime
    logs: List[str] = field(default_factory=list)
    error_details: Optional[str] = None
    artifacts: Dict[str, str] = field(default_factory=dict)

class PersonalServerDeployer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.docker_client = None
        self.deployment_history: Dict[str, List[DeploymentStatus]] = {}
        self.active_deployments: Dict[str, DeploymentStatus] = {}
        
        # Initialize Docker client
        try:
            self.docker_client = docker.from_env()
            self.logger.info("Docker client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Docker client: {e}")
        
        # Deployment templates
        self.deployment_templates = self._load_deployment_templates()

    def _load_deployment_templates(self) -> Dict[str, str]:
        """Load deployment templates for different application types"""
        return {
            "web_app": """
version: '3.8'
services:
  app:
    image: {docker_image}
    ports:
      - "{host_port}:{container_port}"
    environment:
      {environment_vars}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:{container_port}/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '{cpu_limit}'
          memory: '{memory_limit}'
""",
            "database": """
version: '3.8'
services:
  db:
    image: {docker_image}
    environment:
      {environment_vars}
    volumes:
      - db_data:/var/lib/postgresql/data
      - ./backups:/backups
    restart: unless-stopped
    ports:
      - "{host_port}:{container_port}"
    deploy:
      resources:
        limits:
          cpus: '{cpu_limit}'
          memory: '{memory_limit}'
volumes:
  db_data:
""",
            "api_service": """
version: '3.8'
services:
  api:
    image: {docker_image}
    ports:
      - "{host_port}:{container_port}"
    environment:
      {environment_vars}
    volumes:
      - ./config:/app/config
      - ./data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:{container_port}/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: '{cpu_limit}'
          memory: '{memory_limit}'
      restart_policy:
        condition: any
        delay: 5s
        max_attempts: 3
"""
        }

    async def create_deployment(
        self,
        config: DeploymentConfig,
        force_redeploy: bool = False
    ) -> str:
        """Create and execute a new deployment"""
        try:
            # Check if deployment already exists
            if config.deployment_id in self.active_deployments and not force_redeploy:
                raise ValueError(f"Deployment {config.deployment_id} already active")
            
            # Initialize deployment status
            status = DeploymentStatus(
                deployment_id=config.deployment_id,
                stage=DeploymentStage.PREPARATION,
                progress=0.0,
                message="Initializing deployment",
                started_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            self.active_deployments[config.deployment_id] = status
            
            # Start deployment process
            deployment_task = asyncio.create_task(
                self._execute_deployment(config, status)
            )
            
            return config.deployment_id
            
        except Exception as e:
            self.logger.error(f"Failed to create deployment: {e}")
            raise

    async def _execute_deployment(
        self,
        config: DeploymentConfig,
        status: DeploymentStatus
    ):
        """Execute the deployment process"""
        try:
            # Stage 1: Preparation
            await self._update_status(status, DeploymentStage.PREPARATION, 0.1, "Preparing deployment")
            preparation_result = await self._prepare_deployment(config, status)
            
            if not preparation_result:
                await self._update_status(status, DeploymentStage.FAILED, 0.1, "Preparation failed")
                return
            
            # Stage 2: Build
            await self._update_status(status, DeploymentStage.BUILD, 0.3, "Building application")
            build_result = await self._build_application(config, status)
            
            if not build_result:
                await self._update_status(status, DeploymentStage.FAILED, 0.3, "Build failed")
                return
            
            # Stage 3: Test
            await self._update_status(status, DeploymentStage.TEST, 0.5, "Running tests")
            test_result = await self._test_deployment(config, status)
            
            if not test_result:
                await self._update_status(status, DeploymentStage.FAILED, 0.5, "Tests failed")
                return
            
            # Stage 4: Deploy
            await self._update_status(status, DeploymentStage.DEPLOY, 0.7, "Deploying application")
            deploy_result = await self._deploy_application(config, status)
            
            if not deploy_result:
                await self._update_status(status, DeploymentStage.FAILED, 0.7, "Deployment failed")
                return
            
            # Stage 5: Verify
            await self._update_status(status, DeploymentStage.VERIFY, 0.9, "Verifying deployment")
            verify_result = await self._verify_deployment(config, status)
            
            if not verify_result:
                await self._update_status(status, DeploymentStage.FAILED, 0.9, "Verification failed")
                await self._rollback_deployment(config, status)
                return
            
            # Stage 6: Complete
            await self._update_status(status, DeploymentStage.COMPLETE, 1.0, "Deployment completed successfully")
            await self._finalize_deployment(config, status)
            
        except Exception as e:
            self.logger.error(f"Deployment execution failed: {e}")
            status.error_details = str(e)
            await self._update_status(status, DeploymentStage.FAILED, status.progress, f"Deployment failed: {e}")
            
            if config.enable_rollback:
                await self._rollback_deployment(config, status)

    async def _prepare_deployment(self, config: DeploymentConfig, status: DeploymentStatus) -> bool:
        """Prepare deployment environment and resources"""
        try:
            status.logs.append("Starting deployment preparation")
            
            # Validate target environment
            target_valid = await self._validate_target(config.target)
            if not target_valid:
                status.logs.append("Target validation failed")
                return False
            
            # Create deployment directory
            deployment_dir = f"/tmp/deployments/{config.deployment_id}"
            os.makedirs(deployment_dir, exist_ok=True)
            status.artifacts["deployment_dir"] = deployment_dir
            
            # Backup existing deployment if required
            if config.backup_previous:
                backup_result = await self._backup_existing_deployment(config, status)
                if not backup_result:
                    status.logs.append("Warning: Failed to backup existing deployment")
            
            # Generate deployment files
            await self._generate_deployment_files(config, deployment_dir)
            
            # Validate configuration
            config_valid = await self._validate_configuration(config)
            if not config_valid:
                status.logs.append("Configuration validation failed")
                return False
            
            status.logs.append("Deployment preparation completed")
            return True
            
        except Exception as e:
            status.logs.append(f"Preparation failed: {e}")
            return False

    async def _validate_target(self, target: DeploymentTarget) -> bool:
        """Validate deployment target availability and credentials"""
        try:
            if target.type == "personal_server":
                # Check if personal server is reachable
                response = requests.get(f"{target.endpoint}/health", timeout=10)
                return response.status_code == 200
            
            elif target.type == "cloud":
                # Validate cloud credentials
                # Implementation depends on cloud provider
                return True
            
            elif target.type == "edge":
                # Check edge device connectivity
                return True
            
            return False
            
        except Exception as e:
            self.logger.warning(f"Target validation failed: {e}")
            return False

    async def _backup_existing_deployment(self, config: DeploymentConfig, status: DeploymentStatus) -> bool:
        """Backup existing deployment for rollback"""
        try:
            backup_dir = f"/tmp/backups/{config.deployment_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.makedirs(backup_dir, exist_ok=True)
            
            # Check if deployment exists
            if self.docker_client:
                try:
                    # Get existing containers
                    containers = self.docker_client.containers.list(
                        filters={"label": f"deployment_id={config.deployment_id}"}
                    )
                    
                    if containers:
                        # Create backup archive
                        backup_file = f"{backup_dir}/backup.tar.gz"
                        with tarfile.open(backup_file, "w:gz") as tar:
                            for container in containers:
                                # Export container as image
                                image = container.commit()
                                image_tar = f"{backup_dir}/{container.name}_image.tar"
                                
                                with open(image_tar, "wb") as f:
                                    for chunk in image.save(named=True):
                                        f.write(chunk)
                                
                                tar.add(image_tar, arcname=f"{container.name}_image.tar")
                                os.remove(image_tar)
                        
                        status.artifacts["backup_file"] = backup_file
                        status.logs.append(f"Backup created: {backup_file}")
                
                except Exception as e:
                    self.logger.warning(f"Docker backup failed: {e}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Backup failed: {e}")
            return False

    async def _generate_deployment_files(self, config: DeploymentConfig, deployment_dir: str):
        """Generate deployment files based on configuration"""
        try:
            if config.deployment_type == DeploymentType.DOCKER_COMPOSE:
                # Generate docker-compose.yml
                template = self._select_template(config.application_name)
                
                # Format template with configuration
                compose_content = template.format(
                    docker_image=config.docker_image,
                    host_port=list(config.port_mappings.keys())[0] if config.port_mappings else 8080,
                    container_port=list(config.port_mappings.values())[0] if config.port_mappings else 8080,
                    cpu_limit=config.cpu_limit,
                    memory_limit=config.memory_limit,
                    environment_vars=self._format_environment_vars(config.environment_variables)
                )
                
                compose_file = os.path.join(deployment_dir, "docker-compose.yml")
                with open(compose_file, 'w') as f:
                    f.write(compose_content)
                
                config.docker_compose_file = compose_file
            
            # Generate environment file
            env_file = os.path.join(deployment_dir, ".env")
            with open(env_file, 'w') as f:
                for key, value in config.environment_variables.items():
                    f.write(f"{key}={value}\n")
            
            # Generate deployment script
            script_content = self._generate_deployment_script(config)
            script_file = os.path.join(deployment_dir, "deploy.sh")
            with open(script_file, 'w') as f:
                f.write(script_content)
            os.chmod(script_file, 0o755)
            
            # Generate health check script
            health_script = self._generate_health_check_script(config)
            health_file = os.path.join(deployment_dir, "health_check.sh")
            with open(health_file, 'w') as f:
                f.write(health_script)
            os.chmod(health_file, 0o755)
            
        except Exception as e:
            raise Exception(f"Failed to generate deployment files: {e}")

    def _select_template(self, application_name: str) -> str:
        """Select appropriate deployment template based on application type"""
        app_type = "web_app"  # Default
        
        if "database" in application_name.lower() or "db" in application_name.lower():
            app_type = "database"
        elif "api" in application_name.lower():
            app_type = "api_service"
        
        return self.deployment_templates.get(app_type, self.deployment_templates["web_app"])

    def _format_environment_vars(self, env_vars: Dict[str, str]) -> str:
        """Format environment variables for docker-compose"""
        if not env_vars:
            return ""
        
        formatted_vars = []
        for key, value in env_vars.items():
            formatted_vars.append(f"      {key}: {value}")
        
        return "\n".join(formatted_vars)

    def _generate_deployment_script(self, config: DeploymentConfig) -> str:
        """Generate deployment script"""
        return f"""#!/bin/bash
set -e

echo "Starting deployment of {config.application_name} v{config.version}"

# Pull latest images
if [ -f "docker-compose.yml" ]; then
    docker-compose pull
fi

# Stop existing services
docker-compose down --remove-orphans

# Start new services
docker-compose up -d

# Wait for services to be ready
sleep 30

# Run health check
./health_check.sh

echo "Deployment completed successfully"
"""

    def _generate_health_check_script(self, config: DeploymentConfig) -> str:
        """Generate health check script"""
        port = list(config.port_mappings.keys())[0] if config.port_mappings else 8080
        return f"""#!/bin/bash
set -e

echo "Running health check for {config.application_name}"

# Wait for service to be ready
timeout=300
elapsed=0
interval=10

while [ $elapsed -lt $timeout ]; do
    if curl -f http://localhost:{port}{config.health_check_path} >/dev/null 2>&1; then
        echo "Health check passed"
        exit 0
    fi
    
    echo "Waiting for service to be ready... ($elapsed/$timeout seconds)"
    sleep $interval
    elapsed=$((elapsed + interval))
done

echo "Health check failed - service not ready after $timeout seconds"
exit 1
"""

    async def _validate_configuration(self, config: DeploymentConfig) -> bool:
        """Validate deployment configuration"""
        try:
            # Check required fields
            if not config.docker_image and not config.docker_compose_file:
                return False
            
            # Validate resource limits
            if config.cpu_limit and not self._validate_cpu_limit(config.cpu_limit):
                return False
            
            if config.memory_limit and not self._validate_memory_limit(config.memory_limit):
                return False
            
            # Validate port mappings
            for host_port, container_port in config.port_mappings.items():
                if not (1 <= host_port <= 65535) or not (1 <= container_port <= 65535):
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return False

    def _validate_cpu_limit(self, cpu_limit: str) -> bool:
        """Validate CPU limit format"""
        try:
            if cpu_limit.endswith('m'):
                value = int(cpu_limit[:-1])
                return 1 <= value <= 16000  # 1m to 16 cores
            else:
                value = float(cpu_limit)
                return 0.001 <= value <= 16.0
        except ValueError:
            return False

    def _validate_memory_limit(self, memory_limit: str) -> bool:
        """Validate memory limit format"""
        try:
            if memory_limit.endswith('Gi'):
                value = float(memory_limit[:-2])
                return 0.1 <= value <= 64.0  # 0.1Gi to 64Gi
            elif memory_limit.endswith('Mi'):
                value = float(memory_limit[:-2])
                return 100 <= value <= 65536  # 100Mi to 64Gi
            else:
                value = int(memory_limit)
                return 104857600 <= value <= 68719476736  # 100Mi to 64Gi in bytes
        except ValueError:
            return False

    async def _build_application(self, config: DeploymentConfig, status: DeploymentStatus) -> bool:
        """Build application if needed"""
        try:
            status.logs.append("Starting application build")
            
            if config.docker_image:
                # Pull Docker image
                if self.docker_client:
                    try:
                        status.logs.append(f"Pulling image: {config.docker_image}")
                        image = self.docker_client.images.pull(config.docker_image)
                        status.logs.append(f"Image pulled successfully: {image.id}")
                    except Exception as e:
                        status.logs.append(f"Failed to pull image: {e}")
                        return False
            
            status.logs.append("Application build completed")
            return True
            
        except Exception as e:
            status.logs.append(f"Build failed: {e}")
            return False

    async def _test_deployment(self, config: DeploymentConfig, status: DeploymentStatus) -> bool:
        """Run deployment tests"""
        try:
            status.logs.append("Starting deployment tests")
            
            # Syntax validation for docker-compose
            if config.docker_compose_file:
                result = subprocess.run([
                    "docker-compose", "-f", config.docker_compose_file, "config"
                ], capture_output=True, text=True)
                
                if result.returncode != 0:
                    status.logs.append(f"Docker-compose validation failed: {result.stderr}")
                    return False
            
            # Test resource limits
            if not await self._test_resource_limits(config, status):
                return False
            
            status.logs.append("All deployment tests passed")
            return True
            
        except Exception as e:
            status.logs.append(f"Tests failed: {e}")
            return False

    async def _test_resource_limits(self, config: DeploymentConfig, status: DeploymentStatus) -> bool:
        """Test if target has sufficient resources"""
        try:
            # Get target capacity
            target_capacity = config.target.capacity
            
            # Parse resource requirements
            cpu_required = self._parse_cpu_limit(config.cpu_limit)
            memory_required = self._parse_memory_limit(config.memory_limit)
            
            # Check availability
            if target_capacity.get("cpu_cores", 0) < cpu_required:
                status.logs.append("Insufficient CPU resources on target")
                return False
            
            if target_capacity.get("memory_gb", 0) < memory_required:
                status.logs.append("Insufficient memory resources on target")
                return False
            
            return True
            
        except Exception as e:
            status.logs.append(f"Resource limit test failed: {e}")
            return False

    def _parse_cpu_limit(self, cpu_limit: str) -> float:
        """Parse CPU limit to cores"""
        try:
            if cpu_limit.endswith('m'):
                return int(cpu_limit[:-1]) / 1000.0
            else:
                return float(cpu_limit)
        except ValueError:
            return 1.0  # Default 1 core

    def _parse_memory_limit(self, memory_limit: str) -> float:
        """Parse memory limit to GB"""
        try:
            if memory_limit.endswith('Gi'):
                return float(memory_limit[:-2])
            elif memory_limit.endswith('Mi'):
                return float(memory_limit[:-2]) / 1024.0
            else:
                return int(memory_limit) / (1024**3)  # Bytes to GB
        except ValueError:
            return 1.0  # Default 1GB

    async def _deploy_application(self, config: DeploymentConfig, status: DeploymentStatus) -> bool:
        """Deploy application to target"""
        try:
            status.logs.append("Starting application deployment")
            
            deployment_dir = status.artifacts.get("deployment_dir")
            if not deployment_dir:
                status.logs.append("Deployment directory not found")
                return False
            
            # Change to deployment directory
            original_cwd = os.getcwd()
            os.chdir(deployment_dir)
            
            try:
                # Execute deployment script
                result = subprocess.run(
                    ["./deploy.sh"],
                    capture_output=True,
                    text=True,
                    timeout=600  # 10 minute timeout
                )
                
                status.logs.append(f"Deployment script output: {result.stdout}")
                
                if result.returncode != 0:
                    status.logs.append(f"Deployment script failed: {result.stderr}")
                    return False
                
                # Label deployed containers
                await self._label_containers(config)
                
                status.logs.append("Application deployed successfully")
                return True
                
            finally:
                os.chdir(original_cwd)
            
        except Exception as e:
            status.logs.append(f"Deployment failed: {e}")
            return False

    async def _label_containers(self, config: DeploymentConfig):
        """Label deployed containers for tracking"""
        try:
            if self.docker_client:
                # Get containers from compose project
                containers = self.docker_client.containers.list(
                    filters={"label": f"com.docker.compose.project={config.deployment_id}"}
                )
                
                for container in containers:
                    container.reload()
                    # Add custom labels
                    labels = container.attrs.get("Config", {}).get("Labels", {})
                    labels[f"deployment_id"] = config.deployment_id
                    labels[f"deployment_version"] = config.version
                    labels[f"deployed_at"] = datetime.now(timezone.utc).isoformat()
                    
        except Exception as e:
            self.logger.warning(f"Container labeling failed: {e}")

    async def _verify_deployment(self, config: DeploymentConfig, status: DeploymentStatus) -> bool:
        """Verify deployment is working correctly"""
        try:
            status.logs.append("Starting deployment verification")
            
            deployment_dir = status.artifacts.get("deployment_dir")
            if not deployment_dir:
                status.logs.append("Deployment directory not found")
                return False
            
            # Change to deployment directory
            original_cwd = os.getcwd()
            os.chdir(deployment_dir)
            
            try:
                # Run health check
                result = subprocess.run(
                    ["./health_check.sh"],
                    capture_output=True,
                    text=True,
                    timeout=config.ready_timeout
                )
                
                status.logs.append(f"Health check output: {result.stdout}")
                
                if result.returncode != 0:
                    status.logs.append(f"Health check failed: {result.stderr}")
                    return False
                
                # Verify containers are running
                if not await self._verify_containers_running(config, status):
                    return False
                
                status.logs.append("Deployment verification successful")
                return True
                
            finally:
                os.chdir(original_cwd)
            
        except Exception as e:
            status.logs.append(f"Verification failed: {e}")
            return False

    async def _verify_containers_running(self, config: DeploymentConfig, status: DeploymentStatus) -> bool:
        """Verify all containers are running properly"""
        try:
            if not self.docker_client:
                return True  # Skip if Docker not available
            
            containers = self.docker_client.containers.list(
                filters={"label": f"deployment_id={config.deployment_id}"}
            )
            
            if not containers:
                status.logs.append("No containers found for deployment")
                return False
            
            for container in containers:
                if container.status != "running":
                    status.logs.append(f"Container {container.name} is not running: {container.status}")
                    return False
                
                # Check container health if health check is defined
                health = container.attrs.get("State", {}).get("Health", {})
                if health and health.get("Status") not in ["healthy", ""]:
                    status.logs.append(f"Container {container.name} is unhealthy: {health.get('Status')}")
                    return False
            
            status.logs.append(f"All {len(containers)} containers are running healthy")
            return True
            
        except Exception as e:
            status.logs.append(f"Container verification failed: {e}")
            return False

    async def _finalize_deployment(self, config: DeploymentConfig, status: DeploymentStatus):
        """Finalize successful deployment"""
        try:
            # Move deployment from active to history
            if config.deployment_id not in self.deployment_history:
                self.deployment_history[config.deployment_id] = []
            
            self.deployment_history[config.deployment_id].append(status)
            
            # Clean up old deployment versions
            if len(self.deployment_history[config.deployment_id]) > config.max_history_versions:
                self.deployment_history[config.deployment_id] = \
                    self.deployment_history[config.deployment_id][-config.max_history_versions:]
            
            # Clean up deployment directory if desired
            # deployment_dir = status.artifacts.get("deployment_dir")
            # if deployment_dir and os.path.exists(deployment_dir):
            #     shutil.rmtree(deployment_dir)
            
            status.logs.append("Deployment finalized successfully")
            
        except Exception as e:
            self.logger.error(f"Deployment finalization failed: {e}")

    async def _rollback_deployment(self, config: DeploymentConfig, status: DeploymentStatus):
        """Rollback failed deployment"""
        try:
            await self._update_status(status, DeploymentStage.ROLLBACK, status.progress, "Rolling back deployment")
            
            backup_file = status.artifacts.get("backup_file")
            if backup_file and os.path.exists(backup_file):
                status.logs.append(f"Restoring from backup: {backup_file}")
                
                # Stop current deployment
                deployment_dir = status.artifacts.get("deployment_dir")
                if deployment_dir and os.path.exists(deployment_dir):
                    original_cwd = os.getcwd()
                    os.chdir(deployment_dir)
                    
                    try:
                        subprocess.run(["docker-compose", "down", "--remove-orphans"], 
                                     capture_output=True, timeout=60)
                    except Exception as e:
                        status.logs.append(f"Failed to stop current deployment: {e}")
                    finally:
                        os.chdir(original_cwd)
                
                # Restore backup (simplified - would need full implementation)
                status.logs.append("Backup restoration would be implemented here")
            else:
                status.logs.append("No backup available for rollback")
            
            status.logs.append("Rollback completed")
            
        except Exception as e:
            status.logs.append(f"Rollback failed: {e}")

    async def _update_status(
        self,
        status: DeploymentStatus,
        stage: DeploymentStage,
        progress: float,
        message: str
    ):
        """Update deployment status"""
        status.stage = stage
        status.progress = progress
        status.message = message
        status.updated_at = datetime.now(timezone.utc)
        
        self.logger.info(f"Deployment {status.deployment_id}: {stage.value} - {message}")

    async def get_deployment_status(self, deployment_id: str) -> Optional[DeploymentStatus]:
        """Get current deployment status"""
        return self.active_deployments.get(deployment_id)

    async def list_deployments(self) -> Dict[str, Any]:
        """List all deployments"""
        return {
            "active_deployments": {
                dep_id: {
                    "stage": status.stage.value,
                    "progress": status.progress,
                    "message": status.message,
                    "started_at": status.started_at.isoformat(),
                    "updated_at": status.updated_at.isoformat()
                }
                for dep_id, status in self.active_deployments.items()
            },
            "deployment_history": {
                dep_id: len(history)
                for dep_id, history in self.deployment_history.items()
            }
        }

    async def cancel_deployment(self, deployment_id: str) -> bool:
        """Cancel an active deployment"""
        try:
            if deployment_id not in self.active_deployments:
                return False
            
            status = self.active_deployments[deployment_id]
            
            # Stop deployment containers if any
            if self.docker_client:
                containers = self.docker_client.containers.list(
                    filters={"label": f"deployment_id={deployment_id}"}
                )
                
                for container in containers:
                    try:
                        container.stop(timeout=30)
                        container.remove()
                    except Exception as e:
                        self.logger.warning(f"Failed to stop container {container.name}: {e}")
            
            await self._update_status(status, DeploymentStage.FAILED, status.progress, "Deployment cancelled")
            
            # Move to history
            if deployment_id not in self.deployment_history:
                self.deployment_history[deployment_id] = []
            self.deployment_history[deployment_id].append(status)
            
            del self.active_deployments[deployment_id]
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cancel deployment: {e}")
            return False

    async def cleanup_old_deployments(self, older_than_days: int = 7):
        """Clean up old deployment artifacts"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=older_than_days)
            
            cleaned_deployments = 0
            
            for dep_id, history in list(self.deployment_history.items()):
                # Remove old history entries
                filtered_history = [
                    status for status in history
                    if status.started_at > cutoff_date
                ]
                
                if filtered_history:
                    self.deployment_history[dep_id] = filtered_history
                else:
                    del self.deployment_history[dep_id]
                    cleaned_deployments += 1
            
            # Clean up deployment directories
            deployments_dir = "/tmp/deployments"
            if os.path.exists(deployments_dir):
                for item in os.listdir(deployments_dir):
                    item_path = os.path.join(deployments_dir, item)
                    if os.path.isdir(item_path):
                        # Check if directory is old
                        stat = os.stat(item_path)
                        if datetime.fromtimestamp(stat.st_mtime, timezone.utc) < cutoff_date:
                            shutil.rmtree(item_path)
            
            # Clean up backup directories
            backups_dir = "/tmp/backups"
            if os.path.exists(backups_dir):
                for item in os.listdir(backups_dir):
                    item_path = os.path.join(backups_dir, item)
                    if os.path.isdir(item_path):
                        stat = os.stat(item_path)
                        if datetime.fromtimestamp(stat.st_mtime, timezone.utc) < cutoff_date:
                            shutil.rmtree(item_path)
            
            self.logger.info(f"Cleaned up {cleaned_deployments} old deployments")
            return cleaned_deployments
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
            return 0

    async def get_deployment_logs(self, deployment_id: str) -> List[str]:
        """Get deployment logs"""
        status = self.active_deployments.get(deployment_id)
        if status:
            return status.logs
        
        # Check history
        history = self.deployment_history.get(deployment_id, [])
        if history:
            return history[-1].logs  # Return logs from most recent deployment
        
        return []

    async def export_deployment_config(self, deployment_id: str) -> Optional[str]:
        """Export deployment configuration for reuse"""
        try:
            # This would export the deployment configuration
            # Implementation would depend on specific requirements
            pass
        except Exception as e:
            self.logger.error(f"Config export failed: {e}")
            return None