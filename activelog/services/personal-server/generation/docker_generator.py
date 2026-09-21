import asyncio
import json
import logging
import os
import tempfile
import shutil
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum
import hashlib
import yaml

class ImageType(Enum):
    MINIMAL = "minimal"
    STANDARD = "standard"
    PERFORMANCE = "performance"
    DEVELOPMENT = "development"

class BaseImage(Enum):
    ALPINE = "alpine:3.18"
    UBUNTU = "ubuntu:22.04"
    PYTHON_ALPINE = "python:3.11-alpine"
    PYTHON_SLIM = "python:3.11-slim"
    NODE_ALPINE = "node:18-alpine"

@dataclass
class DockerConfig:
    base_image: str
    packages: List[str]
    python_packages: List[str]
    node_packages: List[str]
    environment_vars: Dict[str, str]
    exposed_ports: List[int]
    volumes: List[str]
    commands: List[str]
    health_check: Optional[str]
    security_options: List[str]

@dataclass
class ImageBuild:
    dockerfile_content: str
    build_context: Dict[str, str]
    estimated_size_mb: int
    build_time_estimate: int
    security_score: float
    optimization_level: str

class CustomDockerGenerator:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Base configurations for different image types
        self.base_configs = {
            ImageType.MINIMAL: {
                "base_image": BaseImage.ALPINE.value,
                "security_level": "high",
                "optimization": "size"
            },
            ImageType.STANDARD: {
                "base_image": BaseImage.PYTHON_SLIM.value,
                "security_level": "medium",
                "optimization": "balanced"
            },
            ImageType.PERFORMANCE: {
                "base_image": BaseImage.UBUNTU.value,
                "security_level": "medium",
                "optimization": "performance"
            },
            ImageType.DEVELOPMENT: {
                "base_image": BaseImage.UBUNTU.value,
                "security_level": "low",
                "optimization": "features"
            }
        }
        
        # Security hardening templates
        self.security_templates = {
            "high": [
                "USER 1001:1001",
                "RUN addgroup -g 1001 appgroup && adduser -u 1001 -G appgroup -s /bin/sh -D appuser",
                "--security-opt=no-new-privileges:true",
                "--cap-drop=ALL",
                "--cap-add=NET_BIND_SERVICE"
            ],
            "medium": [
                "USER 1000:1000",
                "RUN groupadd -r appgroup && useradd -r -g appgroup appuser",
                "--security-opt=no-new-privileges:true"
            ],
            "low": []
        }

    async def analyze_application_requirements(self, usage_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze application to determine Docker requirements"""
        try:
            features = usage_data.get("features", {})
            dependencies = usage_data.get("dependencies", {})
            performance_data = usage_data.get("performance", {})
            
            analysis = {
                "runtime_requirements": self._analyze_runtime_requirements(features),
                "dependency_analysis": self._analyze_dependencies(dependencies),
                "performance_requirements": self._analyze_performance_requirements(performance_data),
                "security_requirements": self._analyze_security_requirements(features),
                "storage_requirements": self._analyze_storage_requirements(usage_data),
                "network_requirements": self._analyze_network_requirements(usage_data)
            }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing application requirements: {e}")
            return {}

    def _analyze_runtime_requirements(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze what runtime components are needed"""
        requirements = {
            "python": False,
            "node": False,
            "database": False,
            "redis": False,
            "nginx": False,
            "ssl": False,
            "background_jobs": False
        }
        
        # Python requirements
        if any(features.get(f, 0) > 0 for f in ["api_endpoints", "data_processing", "ml_features"]):
            requirements["python"] = True
        
        # Node.js requirements
        if features.get("frontend_components", 0) > 0 or features.get("real_time_features", 0) > 0:
            requirements["node"] = True
        
        # Database requirements
        if features.get("database_operations", 0) > 100:
            requirements["database"] = True
        
        # Redis requirements
        if features.get("caching", 0) > 50 or features.get("session_management", 0) > 0:
            requirements["redis"] = True
        
        # Web server requirements
        if features.get("web_interface", 0) > 0:
            requirements["nginx"] = True
        
        # SSL requirements
        if features.get("secure_endpoints", 0) > 0:
            requirements["ssl"] = True
        
        # Background job requirements
        if features.get("background_jobs", 0) > 10:
            requirements["background_jobs"] = True
        
        return requirements

    def _analyze_dependencies(self, dependencies: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze dependency requirements"""
        python_deps = dependencies.get("python", [])
        node_deps = dependencies.get("node", [])
        system_deps = dependencies.get("system", [])
        
        analysis = {
            "python_packages": python_deps,
            "node_packages": node_deps,
            "system_packages": system_deps,
            "heavy_dependencies": self._identify_heavy_dependencies(python_deps + node_deps),
            "security_sensitive": self._identify_security_sensitive_deps(python_deps + node_deps)
        }
        
        return analysis

    def _identify_heavy_dependencies(self, packages: List[str]) -> List[str]:
        """Identify dependencies that significantly increase image size"""
        heavy_deps = [
            "tensorflow", "pytorch", "opencv-python", "pandas", "numpy",
            "scipy", "matplotlib", "pillow", "scikit-learn"
        ]
        return [dep for dep in packages if any(heavy in dep.lower() for heavy in heavy_deps)]

    def _identify_security_sensitive_deps(self, packages: List[str]) -> List[str]:
        """Identify security-sensitive dependencies"""
        sensitive_deps = [
            "requests", "urllib3", "cryptography", "jwt", "oauth",
            "flask", "django", "fastapi", "sqlalchemy"
        ]
        return [dep for dep in packages if any(sensitive in dep.lower() for sensitive in sensitive_deps)]

    def _analyze_performance_requirements(self, performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze performance requirements"""
        return {
            "cpu_intensive": performance_data.get("cpu_usage_avg", 0) > 70,
            "memory_intensive": performance_data.get("memory_usage_avg", 0) > 60,
            "io_intensive": performance_data.get("disk_io_avg", 0) > 50,
            "network_intensive": performance_data.get("network_usage_avg", 0) > 100,
            "startup_time_critical": performance_data.get("startup_time_ms", 5000) > 3000,
            "concurrent_connections": performance_data.get("max_concurrent", 10)
        }

    def _analyze_security_requirements(self, features: Dict[str, Any]) -> Dict[str, str]:
        """Analyze security requirements"""
        security_level = "low"
        
        if features.get("secure_endpoints", 0) > 0 or features.get("user_authentication", 0) > 0:
            security_level = "medium"
        
        if features.get("sensitive_data", 0) > 0 or features.get("payment_processing", 0) > 0:
            security_level = "high"
        
        return {"level": security_level}

    def _analyze_storage_requirements(self, usage_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze storage requirements"""
        return {
            "persistent_storage": usage_data.get("persistent_data", False),
            "log_volume": usage_data.get("log_volume_mb_day", 100),
            "temp_storage": usage_data.get("temp_files", False),
            "backup_required": usage_data.get("backup_required", False)
        }

    def _analyze_network_requirements(self, usage_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze network requirements"""
        return {
            "external_apis": usage_data.get("external_api_calls", 0) > 0,
            "websockets": usage_data.get("real_time_features", 0) > 0,
            "static_files": usage_data.get("static_file_serving", False),
            "cdn_integration": usage_data.get("cdn_usage", False)
        }

    async def generate_dockerfile(
        self,
        requirements: Dict[str, Any],
        image_type: ImageType = ImageType.STANDARD,
        optimization_target: str = "balanced"
    ) -> ImageBuild:
        """Generate optimized Dockerfile based on requirements"""
        try:
            base_config = self.base_configs[image_type]
            
            # Build Docker configuration
            docker_config = DockerConfig(
                base_image=base_config["base_image"],
                packages=self._get_system_packages(requirements),
                python_packages=requirements.get("dependency_analysis", {}).get("python_packages", []),
                node_packages=requirements.get("dependency_analysis", {}).get("node_packages", []),
                environment_vars=self._get_environment_variables(requirements),
                exposed_ports=self._get_exposed_ports(requirements),
                volumes=self._get_volumes(requirements),
                commands=self._get_startup_commands(requirements),
                health_check=self._get_health_check(requirements),
                security_options=self._get_security_options(base_config["security_level"])
            )
            
            # Generate Dockerfile content
            dockerfile_content = self._build_dockerfile(docker_config, optimization_target)
            
            # Build additional context files
            build_context = self._generate_build_context(docker_config, requirements)
            
            # Calculate estimates
            size_estimate = self._estimate_image_size(docker_config)
            build_time_estimate = self._estimate_build_time(docker_config)
            security_score = self._calculate_security_score(docker_config, base_config["security_level"])
            
            return ImageBuild(
                dockerfile_content=dockerfile_content,
                build_context=build_context,
                estimated_size_mb=size_estimate,
                build_time_estimate=build_time_estimate,
                security_score=security_score,
                optimization_level=optimization_target
            )
            
        except Exception as e:
            self.logger.error(f"Error generating Dockerfile: {e}")
            raise

    def _get_system_packages(self, requirements: Dict[str, Any]) -> List[str]:
        """Get required system packages"""
        packages = ["ca-certificates", "curl", "wget"]
        
        runtime_reqs = requirements.get("runtime_requirements", {})
        
        if runtime_reqs.get("python"):
            packages.extend(["python3", "python3-pip", "python3-dev", "gcc", "musl-dev"])
        
        if runtime_reqs.get("node"):
            packages.extend(["nodejs", "npm"])
        
        if runtime_reqs.get("database"):
            packages.extend(["postgresql-client", "mysql-client"])
        
        if runtime_reqs.get("ssl"):
            packages.extend(["openssl", "openssl-dev"])
        
        if runtime_reqs.get("nginx"):
            packages.extend(["nginx"])
        
        return packages

    def _get_environment_variables(self, requirements: Dict[str, Any]) -> Dict[str, str]:
        """Get required environment variables"""
        env_vars = {
            "PYTHONUNBUFFERED": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "TZ": "UTC"
        }
        
        if requirements.get("runtime_requirements", {}).get("python"):
            env_vars["PYTHONPATH"] = "/app"
        
        return env_vars

    def _get_exposed_ports(self, requirements: Dict[str, Any]) -> List[int]:
        """Get ports that need to be exposed"""
        ports = []
        
        runtime_reqs = requirements.get("runtime_requirements", {})
        
        if runtime_reqs.get("python") or runtime_reqs.get("node"):
            ports.append(8000)  # Application port
        
        if runtime_reqs.get("nginx"):
            ports.extend([80, 443])
        
        return ports

    def _get_volumes(self, requirements: Dict[str, Any]) -> List[str]:
        """Get required volume mounts"""
        volumes = []
        
        storage_reqs = requirements.get("storage_requirements", {})
        
        if storage_reqs.get("persistent_storage"):
            volumes.append("/app/data")
        
        if storage_reqs.get("log_volume", 0) > 50:
            volumes.append("/app/logs")
        
        return volumes

    def _get_startup_commands(self, requirements: Dict[str, Any]) -> List[str]:
        """Get startup commands"""
        commands = []
        
        runtime_reqs = requirements.get("runtime_requirements", {})
        
        if runtime_reqs.get("nginx"):
            commands.append("nginx -g 'daemon off;' &")
        
        if runtime_reqs.get("python"):
            commands.append("python3 /app/main.py")
        elif runtime_reqs.get("node"):
            commands.append("node /app/server.js")
        
        return commands

    def _get_health_check(self, requirements: Dict[str, Any]) -> Optional[str]:
        """Generate health check command"""
        runtime_reqs = requirements.get("runtime_requirements", {})
        
        if runtime_reqs.get("python") or runtime_reqs.get("node"):
            return "curl -f http://localhost:8000/health || exit 1"
        
        return None

    def _get_security_options(self, security_level: str) -> List[str]:
        """Get security options for the container"""
        return self.security_templates.get(security_level, [])

    def _build_dockerfile(self, config: DockerConfig, optimization: str) -> str:
        """Build the Dockerfile content"""
        dockerfile_lines = []
        
        # Base image
        dockerfile_lines.append(f"FROM {config.base_image}")
        dockerfile_lines.append("")
        
        # Metadata
        dockerfile_lines.extend([
            "LABEL maintainer=\"ActiveLog Personal Server\"",
            f"LABEL optimization=\"{optimization}\"",
            "LABEL security=\"hardened\"",
            ""
        ])
        
        # Environment variables
        for key, value in config.environment_vars.items():
            dockerfile_lines.append(f"ENV {key}={value}")
        dockerfile_lines.append("")
        
        # System packages installation (optimized)
        if config.packages:
            if "alpine" in config.base_image:
                dockerfile_lines.extend([
                    "RUN apk update && \\",
                    f"    apk add --no-cache {' '.join(config.packages)} && \\",
                    "    rm -rf /var/cache/apk/*",
                    ""
                ])
            else:
                dockerfile_lines.extend([
                    "RUN apt-get update && \\",
                    f"    apt-get install -y --no-install-recommends {' '.join(config.packages)} && \\",
                    "    apt-get clean && \\",
                    "    rm -rf /var/lib/apt/lists/*",
                    ""
                ])
        
        # Python packages installation
        if config.python_packages:
            dockerfile_lines.extend([
                "COPY requirements.txt /tmp/",
                "RUN pip install --no-cache-dir --upgrade pip && \\",
                "    pip install --no-cache-dir -r /tmp/requirements.txt && \\",
                "    rm /tmp/requirements.txt",
                ""
            ])
        
        # Node packages installation
        if config.node_packages:
            dockerfile_lines.extend([
                "COPY package.json package-lock.json /tmp/",
                "RUN cd /tmp && npm ci --only=production && \\",
                "    npm cache clean --force",
                ""
            ])
        
        # Security hardening
        security_opts = [opt for opt in config.security_options if not opt.startswith("--")]
        if security_opts:
            dockerfile_lines.extend(security_opts)
            dockerfile_lines.append("")
        
        # Working directory
        dockerfile_lines.extend([
            "WORKDIR /app",
            ""
        ])
        
        # Application files
        dockerfile_lines.extend([
            "COPY . /app/",
            ""
        ])
        
        # Volumes
        for volume in config.volumes:
            dockerfile_lines.append(f"VOLUME [\"/{volume}\"]")
        if config.volumes:
            dockerfile_lines.append("")
        
        # Exposed ports
        for port in config.exposed_ports:
            dockerfile_lines.append(f"EXPOSE {port}")
        if config.exposed_ports:
            dockerfile_lines.append("")
        
        # Health check
        if config.health_check:
            dockerfile_lines.extend([
                f"HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\",
                f"    CMD {config.health_check}",
                ""
            ])
        
        # Startup command
        if config.commands:
            if len(config.commands) == 1:
                dockerfile_lines.append(f"CMD [\"{config.commands[0]}\"]")
            else:
                dockerfile_lines.append("CMD [\"sh\", \"-c\", \"" + " && ".join(config.commands) + "\"]")
        
        return "\n".join(dockerfile_lines)

    def _generate_build_context(self, config: DockerConfig, requirements: Dict[str, Any]) -> Dict[str, str]:
        """Generate additional build context files"""
        context = {}
        
        # requirements.txt
        if config.python_packages:
            context["requirements.txt"] = "\n".join(config.python_packages)
        
        # package.json
        if config.node_packages:
            package_json = {
                "name": "activelog-personal-server",
                "version": "1.0.0",
                "dependencies": {pkg: "latest" for pkg in config.node_packages}
            }
            context["package.json"] = json.dumps(package_json, indent=2)
        
        # nginx.conf
        runtime_reqs = requirements.get("runtime_requirements", {})
        if runtime_reqs.get("nginx"):
            context["nginx.conf"] = self._generate_nginx_config(requirements)
        
        # entrypoint.sh
        if len(config.commands) > 1:
            entrypoint = "#!/bin/sh\nset -e\n\n" + "\n".join(config.commands)
            context["entrypoint.sh"] = entrypoint
        
        # docker-compose.yml for development
        context["docker-compose.yml"] = self._generate_docker_compose(config, requirements)
        
        return context

    def _generate_nginx_config(self, requirements: Dict[str, Any]) -> str:
        """Generate nginx configuration"""
        return """
events {
    worker_connections 1024;
}

http {
    upstream app {
        server 127.0.0.1:8000;
    }
    
    server {
        listen 80;
        
        location / {
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
        
        location /health {
            access_log off;
            proxy_pass http://app;
        }
    }
}
"""

    def _generate_docker_compose(self, config: DockerConfig, requirements: Dict[str, Any]) -> str:
        """Generate docker-compose.yml for development"""
        compose_config = {
            "version": "3.8",
            "services": {
                "app": {
                    "build": ".",
                    "ports": [f"{port}:{port}" for port in config.exposed_ports],
                    "environment": config.environment_vars,
                    "volumes": ["./:/app"] if requirements.get("storage_requirements", {}).get("persistent_storage") else [],
                    "restart": "unless-stopped"
                }
            }
        }
        
        # Add database service if required
        if requirements.get("runtime_requirements", {}).get("database"):
            compose_config["services"]["db"] = {
                "image": "postgres:13-alpine",
                "environment": {
                    "POSTGRES_DB": "activelog",
                    "POSTGRES_USER": "user",
                    "POSTGRES_PASSWORD": "password"
                },
                "volumes": ["postgres_data:/var/lib/postgresql/data"],
                "restart": "unless-stopped"
            }
            compose_config["volumes"] = {"postgres_data": {}}
        
        # Add Redis service if required
        if requirements.get("runtime_requirements", {}).get("redis"):
            compose_config["services"]["redis"] = {
                "image": "redis:7-alpine",
                "restart": "unless-stopped"
            }
        
        return yaml.dump(compose_config, default_flow_style=False)

    def _estimate_image_size(self, config: DockerConfig) -> int:
        """Estimate final image size in MB"""
        base_sizes = {
            "alpine": 5,
            "ubuntu": 70,
            "python:3.11-alpine": 45,
            "python:3.11-slim": 120,
            "node:18-alpine": 110
        }
        
        base_size = 50  # Default fallback
        for base, size in base_sizes.items():
            if base in config.base_image:
                base_size = size
                break
        
        # Add package overhead
        package_overhead = len(config.packages) * 2
        python_overhead = len(config.python_packages) * 5
        node_overhead = len(config.node_packages) * 3
        
        total_size = base_size + package_overhead + python_overhead + node_overhead
        
        return min(total_size, 2000)  # Cap at 2GB

    def _estimate_build_time(self, config: DockerConfig) -> int:
        """Estimate build time in seconds"""
        base_time = 60  # Base build time
        
        # Add time for packages
        package_time = len(config.packages) * 5
        python_time = len(config.python_packages) * 10
        node_time = len(config.node_packages) * 8
        
        total_time = base_time + package_time + python_time + node_time
        
        return min(total_time, 1800)  # Cap at 30 minutes

    def _calculate_security_score(self, config: DockerConfig, security_level: str) -> float:
        """Calculate security score (0-1)"""
        score = 0.5  # Base score
        
        # Security level bonus
        level_bonus = {"high": 0.3, "medium": 0.2, "low": 0.0}
        score += level_bonus.get(security_level, 0)
        
        # Non-root user bonus
        if any("USER" in opt for opt in config.security_options):
            score += 0.1
        
        # Health check bonus
        if config.health_check:
            score += 0.05
        
        # Minimal base image bonus
        if "alpine" in config.base_image:
            score += 0.05
        
        return min(score, 1.0)

    async def generate_multi_stage_dockerfile(
        self,
        requirements: Dict[str, Any],
        stages: List[str] = None
    ) -> ImageBuild:
        """Generate multi-stage Dockerfile for optimal size"""
        if stages is None:
            stages = ["build", "runtime"]
        
        # Build stage for compilation
        build_stage = self._generate_build_stage(requirements)
        
        # Runtime stage for execution
        runtime_stage = self._generate_runtime_stage(requirements)
        
        # Combine stages
        dockerfile_content = f"{build_stage}\n\n{runtime_stage}"
        
        # Reduced size estimate for multi-stage
        single_stage = await self.generate_dockerfile(requirements)
        size_reduction = 0.4  # 40% size reduction typically
        
        return ImageBuild(
            dockerfile_content=dockerfile_content,
            build_context=single_stage.build_context,
            estimated_size_mb=int(single_stage.estimated_size_mb * (1 - size_reduction)),
            build_time_estimate=single_stage.build_time_estimate + 30,  # Extra time for multi-stage
            security_score=single_stage.security_score + 0.05,  # Slight security bonus
            optimization_level="multi-stage"
        )

    def _generate_build_stage(self, requirements: Dict[str, Any]) -> str:
        """Generate build stage for multi-stage Dockerfile"""
        lines = [
            "# Build stage",
            "FROM python:3.11-slim as builder",
            "",
            "WORKDIR /app",
            "COPY requirements.txt .",
            "",
            "RUN pip install --user --no-cache-dir -r requirements.txt",
            ""
        ]
        
        return "\n".join(lines)

    def _generate_runtime_stage(self, requirements: Dict[str, Any]) -> str:
        """Generate runtime stage for multi-stage Dockerfile"""
        lines = [
            "# Runtime stage",
            "FROM python:3.11-alpine",
            "",
            "RUN addgroup -g 1001 appgroup && adduser -u 1001 -G appgroup -s /bin/sh -D appuser",
            "",
            "WORKDIR /app",
            "",
            "COPY --from=builder /root/.local /root/.local",
            "COPY . .",
            "",
            "USER appuser",
            "EXPOSE 8000",
            "",
            'CMD ["python", "main.py"]'
        ]
        
        return "\n".join(lines)

    async def optimize_for_size(self, requirements: Dict[str, Any]) -> ImageBuild:
        """Generate size-optimized Docker image"""
        return await self.generate_dockerfile(
            requirements,
            image_type=ImageType.MINIMAL,
            optimization_target="size"
        )

    async def optimize_for_security(self, requirements: Dict[str, Any]) -> ImageBuild:
        """Generate security-optimized Docker image"""
        # Force high security level
        if "security_requirements" not in requirements:
            requirements["security_requirements"] = {}
        requirements["security_requirements"]["level"] = "high"
        
        return await self.generate_dockerfile(
            requirements,
            image_type=ImageType.MINIMAL,
            optimization_target="security"
        )

    async def save_build_artifacts(self, image_build: ImageBuild, output_dir: str) -> Dict[str, str]:
        """Save all build artifacts to output directory"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # Save Dockerfile
            dockerfile_path = os.path.join(output_dir, "Dockerfile")
            with open(dockerfile_path, 'w') as f:
                f.write(image_build.dockerfile_content)
            
            # Save build context files
            saved_files = {"Dockerfile": dockerfile_path}
            
            for filename, content in image_build.build_context.items():
                file_path = os.path.join(output_dir, filename)
                with open(file_path, 'w') as f:
                    f.write(content)
                saved_files[filename] = file_path
            
            # Save build metadata
            metadata = {
                "estimated_size_mb": image_build.estimated_size_mb,
                "build_time_estimate": image_build.build_time_estimate,
                "security_score": image_build.security_score,
                "optimization_level": image_build.optimization_level
            }
            
            metadata_path = os.path.join(output_dir, "build_metadata.json")
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            saved_files["metadata"] = metadata_path
            
            return saved_files
            
        except Exception as e:
            self.logger.error(f"Error saving build artifacts: {e}")
            raise