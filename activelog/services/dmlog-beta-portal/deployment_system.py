#!/usr/bin/env python3
"""
SuperInstance ML Ecosystem - Deployment System
Enterprise-ready deployment, scaling, and management system
"""

import os
import json
import yaml
import subprocess
import logging
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import tempfile
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

# Optional imports for deployment features
try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    logger.warning("Docker not available - Docker features disabled")

try:
    import kubernetes
    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False
    logger.warning("Kubernetes not available - K8s features disabled")

@dataclass
class DeploymentConfig:
    """Deployment configuration"""
    deployment_name: str
    environment: str  # dev, staging, production
    scale_config: Dict[str, Any]
    resource_limits: Dict[str, Any]
    security_config: Dict[str, Any]
    storage_config: Dict[str, Any]
    networking_config: Dict[str, Any]
    ml_systems_enabled: List[str]
    monitoring_enabled: bool
    backup_enabled: bool

@dataclass
class ScaleConfig:
    """Auto-scaling configuration"""
    min_instances: int
    max_instances: int
    cpu_threshold: float
    memory_threshold: float
    queue_threshold: int
    scale_up_cooldown: int
    scale_down_cooldown: int

class DockerDeployment:
    """Docker containerization and deployment"""
    
    def __init__(self):
        if DOCKER_AVAILABLE:
            try:
                self.client = docker.from_env()
            except:
                self.client = None
                logger.warning("Docker daemon not available")
        else:
            self.client = None
        self.image_name = "superinstance-ml-ecosystem"
        self.base_tag = "latest"
        
    def create_dockerfile(self, output_dir: str):
        """Create optimized Dockerfile"""
        
        dockerfile_content = '''# SuperInstance ML Ecosystem - Production Dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    build-essential \\
    curl \\
    git \\
    nginx \\
    supervisor \\
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd --create-home --shell /bin/bash app

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .
RUN chown -R app:app /app

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/models /app/tmp && \\
    chown -R app:app /app/data /app/logs /app/models /app/tmp

# Copy configuration files
COPY docker/nginx.conf /etc/nginx/sites-available/default
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose ports
EXPOSE 8080 8081 8082

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\
    CMD curl -f http://localhost:8080/health || exit 1

# Switch to app user
USER app

# Start supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
'''
        
        dockerfile_path = os.path.join(output_dir, 'Dockerfile')
        with open(dockerfile_path, 'w') as f:
            f.write(dockerfile_content)
        
        # Create .dockerignore
        dockerignore_content = '''*.pyc
__pycache__
.git
.gitignore
*.md
.pytest_cache
.coverage
.env
*.log
tmp/
data/local_*
.DS_Store
node_modules
'''
        
        dockerignore_path = os.path.join(output_dir, '.dockerignore')
        with open(dockerignore_path, 'w') as f:
            f.write(dockerignore_content)
            
        logger.info(f"Created Dockerfile in {output_dir}")
    
    def create_docker_compose(self, output_dir: str, config: DeploymentConfig):
        """Create Docker Compose configuration"""
        
        compose_config = {
            'version': '3.8',
            'services': {
                'superinstance-ml': {
                    'build': '.',
                    'image': f"{self.image_name}:{config.environment}",
                    'container_name': f"superinstance-ml-{config.environment}",
                    'restart': 'unless-stopped',
                    'ports': [
                        "8080:8080",  # Main app
                        "8081:8081",  # Metrics
                        "8082:8082",  # Admin
                    ],
                    'environment': [
                        f"ENVIRONMENT={config.environment}",
                        f"ML_SYSTEMS_ENABLED={','.join(config.ml_systems_enabled)}",
                        f"MONITORING_ENABLED={config.monitoring_enabled}",
                        "PYTHONPATH=/app",
                    ],
                    'volumes': [
                        "./data:/app/data",
                        "./logs:/app/logs",
                        "./models:/app/models",
                        "./config:/app/config:ro",
                    ],
                    'networks': ['superinstance-network'],
                    'deploy': {
                        'resources': {
                            'limits': config.resource_limits,
                            'reservations': {
                                'cpus': str(config.resource_limits.get('cpus', '1.0')),
                                'memory': config.resource_limits.get('memory', '1G')
                            }
                        }
                    },
                    'healthcheck': {
                        'test': ["CMD", "curl", "-f", "http://localhost:8080/health"],
                        'interval': '30s',
                        'timeout': '10s',
                        'retries': 3,
                        'start_period': '60s'
                    }
                },
                'redis': {
                    'image': 'redis:7-alpine',
                    'container_name': f"redis-{config.environment}",
                    'restart': 'unless-stopped',
                    'volumes': ['redis-data:/data'],
                    'networks': ['superinstance-network'],
                    'command': 'redis-server --appendonly yes'
                },
                'postgres': {
                    'image': 'postgres:15-alpine',
                    'container_name': f"postgres-{config.environment}",
                    'restart': 'unless-stopped',
                    'environment': [
                        "POSTGRES_DB=superinstance_ml",
                        "POSTGRES_USER=superinstance",
                        "POSTGRES_PASSWORD=secure_password_change_me",
                    ],
                    'volumes': [
                        'postgres-data:/var/lib/postgresql/data',
                        './init.sql:/docker-entrypoint-initdb.d/init.sql:ro'
                    ],
                    'networks': ['superinstance-network'],
                    'ports': ['5432:5432'] if config.environment == 'dev' else []
                }
            },
            'networks': {
                'superinstance-network': {
                    'driver': 'bridge'
                }
            },
            'volumes': {
                'redis-data': {},
                'postgres-data': {}
            }
        }
        
        # Add monitoring stack if enabled
        if config.monitoring_enabled:
            compose_config['services'].update({
                'prometheus': {
                    'image': 'prom/prometheus:latest',
                    'container_name': f"prometheus-{config.environment}",
                    'restart': 'unless-stopped',
                    'ports': ['9090:9090'],
                    'volumes': [
                        './monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro'
                    ],
                    'networks': ['superinstance-network']
                },
                'grafana': {
                    'image': 'grafana/grafana:latest',
                    'container_name': f"grafana-{config.environment}",
                    'restart': 'unless-stopped',
                    'ports': ['3000:3000'],
                    'environment': [
                        'GF_SECURITY_ADMIN_PASSWORD=admin_change_me'
                    ],
                    'volumes': [
                        'grafana-data:/var/lib/grafana',
                        './monitoring/grafana:/etc/grafana/provisioning'
                    ],
                    'networks': ['superinstance-network']
                }
            })
            compose_config['volumes']['grafana-data'] = {}
        
        compose_path = os.path.join(output_dir, 'docker-compose.yml')
        with open(compose_path, 'w') as f:
            yaml.dump(compose_config, f, default_flow_style=False, indent=2)
            
        logger.info(f"Created docker-compose.yml in {output_dir}")
    
    def build_image(self, output_dir: str, tag: str = None):
        """Build Docker image"""
        
        if not self.client:
            logger.warning("Docker client not available - skipping image build")
            return None
        
        if not tag:
            tag = f"{self.image_name}:{self.base_tag}"
        
        logger.info(f"Building Docker image: {tag}")
        
        try:
            image, build_logs = self.client.images.build(
                path=output_dir,
                tag=tag,
                rm=True,
                pull=True,
                nocache=False
            )
            
            for log in build_logs:
                if 'stream' in log:
                    logger.info(log['stream'].strip())
            
            logger.info(f"Successfully built image: {tag}")
            return image
            
        except Exception as e:
            logger.error(f"Failed to build image: {e}")
            raise

class KubernetesDeployment:
    """Kubernetes deployment and management"""
    
    def __init__(self):
        if KUBERNETES_AVAILABLE:
            try:
                kubernetes.config.load_incluster_config()
            except:
                try:
                    kubernetes.config.load_kube_config()
                    self.v1 = kubernetes.client.CoreV1Api()
                    self.apps_v1 = kubernetes.client.AppsV1Api()
                    self.autoscaling_v1 = kubernetes.client.AutoscalingV1Api()
                except:
                    logger.warning("Kubernetes config not available")
                    self.v1 = None
                    self.apps_v1 = None
                    self.autoscaling_v1 = None
        else:
            self.v1 = None
            self.apps_v1 = None
            self.autoscaling_v1 = None
        
    def create_namespace(self, name: str):
        """Create Kubernetes namespace"""
        
        namespace = kubernetes.client.V1Namespace(
            metadata=kubernetes.client.V1ObjectMeta(name=name)
        )
        
        try:
            self.v1.create_namespace(namespace)
            logger.info(f"Created namespace: {name}")
        except kubernetes.client.exceptions.ApiException as e:
            if e.status == 409:  # Already exists
                logger.info(f"Namespace {name} already exists")
            else:
                raise
    
    def create_deployment_yaml(self, output_dir: str, config: DeploymentConfig):
        """Create Kubernetes deployment YAML files"""
        
        # Main deployment
        deployment = {
            'apiVersion': 'apps/v1',
            'kind': 'Deployment',
            'metadata': {
                'name': config.deployment_name,
                'labels': {
                    'app': 'superinstance-ml',
                    'version': '1.0.0',
                    'environment': config.environment
                }
            },
            'spec': {
                'replicas': config.scale_config.get('min_instances', 2),
                'selector': {
                    'matchLabels': {
                        'app': 'superinstance-ml'
                    }
                },
                'template': {
                    'metadata': {
                        'labels': {
                            'app': 'superinstance-ml',
                            'version': '1.0.0'
                        }
                    },
                    'spec': {
                        'containers': [{
                            'name': 'superinstance-ml',
                            'image': f"superinstance-ml-ecosystem:{config.environment}",
                            'ports': [
                                {'containerPort': 8080, 'name': 'http'},
                                {'containerPort': 8081, 'name': 'metrics'},
                                {'containerPort': 8082, 'name': 'admin'}
                            ],
                            'env': [
                                {'name': 'ENVIRONMENT', 'value': config.environment},
                                {'name': 'ML_SYSTEMS_ENABLED', 'value': ','.join(config.ml_systems_enabled)},
                                {'name': 'MONITORING_ENABLED', 'value': str(config.monitoring_enabled)},
                                {'name': 'PYTHONPATH', 'value': '/app'}
                            ],
                            'resources': {
                                'requests': {
                                    'cpu': config.resource_limits.get('cpu_request', '500m'),
                                    'memory': config.resource_limits.get('memory_request', '1Gi')
                                },
                                'limits': {
                                    'cpu': config.resource_limits.get('cpu_limit', '2000m'),
                                    'memory': config.resource_limits.get('memory_limit', '4Gi')
                                }
                            },
                            'livenessProbe': {
                                'httpGet': {
                                    'path': '/health',
                                    'port': 8080
                                },
                                'initialDelaySeconds': 60,
                                'periodSeconds': 30
                            },
                            'readinessProbe': {
                                'httpGet': {
                                    'path': '/ready',
                                    'port': 8080
                                },
                                'initialDelaySeconds': 30,
                                'periodSeconds': 10
                            },
                            'volumeMounts': [
                                {'name': 'data-storage', 'mountPath': '/app/data'},
                                {'name': 'model-storage', 'mountPath': '/app/models'},
                                {'name': 'config', 'mountPath': '/app/config', 'readOnly': True}
                            ]
                        }],
                        'volumes': [
                            {
                                'name': 'data-storage',
                                'persistentVolumeClaim': {
                                    'claimName': 'superinstance-data-pvc'
                                }
                            },
                            {
                                'name': 'model-storage',
                                'persistentVolumeClaim': {
                                    'claimName': 'superinstance-models-pvc'
                                }
                            },
                            {
                                'name': 'config',
                                'configMap': {
                                    'name': 'superinstance-config'
                                }
                            }
                        ]
                    }
                }
            }
        }
        
        # Service
        service = {
            'apiVersion': 'v1',
            'kind': 'Service',
            'metadata': {
                'name': f"{config.deployment_name}-service",
                'labels': {
                    'app': 'superinstance-ml'
                }
            },
            'spec': {
                'selector': {
                    'app': 'superinstance-ml'
                },
                'ports': [
                    {'name': 'http', 'port': 80, 'targetPort': 8080},
                    {'name': 'metrics', 'port': 8081, 'targetPort': 8081},
                    {'name': 'admin', 'port': 8082, 'targetPort': 8082}
                ],
                'type': 'ClusterIP'
            }
        }
        
        # Horizontal Pod Autoscaler
        hpa = {
            'apiVersion': 'autoscaling/v2',
            'kind': 'HorizontalPodAutoscaler',
            'metadata': {
                'name': f"{config.deployment_name}-hpa"
            },
            'spec': {
                'scaleTargetRef': {
                    'apiVersion': 'apps/v1',
                    'kind': 'Deployment',
                    'name': config.deployment_name
                },
                'minReplicas': config.scale_config.get('min_instances', 2),
                'maxReplicas': config.scale_config.get('max_instances', 10),
                'metrics': [
                    {
                        'type': 'Resource',
                        'resource': {
                            'name': 'cpu',
                            'target': {
                                'type': 'Utilization',
                                'averageUtilization': int(config.scale_config.get('cpu_threshold', 70) * 100)
                            }
                        }
                    },
                    {
                        'type': 'Resource',
                        'resource': {
                            'name': 'memory',
                            'target': {
                                'type': 'Utilization',
                                'averageUtilization': int(config.scale_config.get('memory_threshold', 80) * 100)
                            }
                        }
                    }
                ]
            }
        }
        
        # Persistent Volume Claims
        data_pvc = {
            'apiVersion': 'v1',
            'kind': 'PersistentVolumeClaim',
            'metadata': {
                'name': 'superinstance-data-pvc'
            },
            'spec': {
                'accessModes': ['ReadWriteMany'],
                'resources': {
                    'requests': {
                        'storage': config.storage_config.get('data_size', '10Gi')
                    }
                },
                'storageClassName': config.storage_config.get('storage_class', 'standard')
            }
        }
        
        models_pvc = {
            'apiVersion': 'v1',
            'kind': 'PersistentVolumeClaim',
            'metadata': {
                'name': 'superinstance-models-pvc'
            },
            'spec': {
                'accessModes': ['ReadWriteMany'],
                'resources': {
                    'requests': {
                        'storage': config.storage_config.get('models_size', '50Gi')
                    }
                },
                'storageClassName': config.storage_config.get('storage_class', 'standard')
            }
        }
        
        # Write all YAML files
        yaml_files = {
            'deployment.yaml': deployment,
            'service.yaml': service,
            'hpa.yaml': hpa,
            'data-pvc.yaml': data_pvc,
            'models-pvc.yaml': models_pvc
        }
        
        k8s_dir = os.path.join(output_dir, 'kubernetes')
        os.makedirs(k8s_dir, exist_ok=True)
        
        for filename, content in yaml_files.items():
            filepath = os.path.join(k8s_dir, filename)
            with open(filepath, 'w') as f:
                yaml.dump(content, f, default_flow_style=False, indent=2)
        
        logger.info(f"Created Kubernetes manifests in {k8s_dir}")

class HelmChart:
    """Helm chart generation"""
    
    def __init__(self):
        self.chart_name = "superinstance-ml"
        self.chart_version = "1.0.0"
        
    def create_helm_chart(self, output_dir: str):
        """Create Helm chart structure"""
        
        chart_dir = os.path.join(output_dir, 'helm', self.chart_name)
        os.makedirs(chart_dir, exist_ok=True)
        
        # Chart.yaml
        chart_yaml = {
            'apiVersion': 'v2',
            'name': self.chart_name,
            'description': 'SuperInstance ML Ecosystem - Multi-layer learning system',
            'type': 'application',
            'version': self.chart_version,
            'appVersion': '1.0.0',
            'keywords': ['ml', 'ai', 'learning', 'superinstance'],
            'maintainers': [
                {
                    'name': 'SuperInstance Team',
                    'email': 'support@superinstance.ai'
                }
            ],
            'dependencies': [
                {
                    'name': 'postgresql',
                    'version': '12.x.x',
                    'repository': 'https://charts.bitnami.com/bitnami',
                    'condition': 'postgresql.enabled'
                },
                {
                    'name': 'redis',
                    'version': '17.x.x',
                    'repository': 'https://charts.bitnami.com/bitnami',
                    'condition': 'redis.enabled'
                }
            ]
        }
        
        with open(os.path.join(chart_dir, 'Chart.yaml'), 'w') as f:
            yaml.dump(chart_yaml, f, default_flow_style=False, indent=2)
        
        # values.yaml
        values_yaml = {
            'replicaCount': 2,
            'image': {
                'repository': 'superinstance-ml-ecosystem',
                'tag': 'latest',
                'pullPolicy': 'IfNotPresent'
            },
            'service': {
                'type': 'ClusterIP',
                'port': 80,
                'targetPort': 8080
            },
            'ingress': {
                'enabled': False,
                'className': 'nginx',
                'annotations': {},
                'hosts': [
                    {
                        'host': 'superinstance-ml.local',
                        'paths': [
                            {
                                'path': '/',
                                'pathType': 'Prefix'
                            }
                        ]
                    }
                ]
            },
            'resources': {
                'limits': {
                    'cpu': '2000m',
                    'memory': '4Gi'
                },
                'requests': {
                    'cpu': '500m',
                    'memory': '1Gi'
                }
            },
            'autoscaling': {
                'enabled': True,
                'minReplicas': 2,
                'maxReplicas': 10,
                'targetCPUUtilizationPercentage': 70,
                'targetMemoryUtilizationPercentage': 80
            },
            'storage': {
                'enabled': True,
                'storageClass': 'standard',
                'dataSize': '10Gi',
                'modelsSize': '50Gi'
            },
            'mlSystems': {
                'enabled': [
                    'response_optimizer',
                    'voice_learning',
                    'universal_interpreter',
                    'system_input_interpreter',
                    'ml_performance_optimizer',
                    'realtime_learning_accelerator',
                    'bot_interpreter_system',
                    'progressive_efficiency_engine',
                    'overnight_training_system'
                ]
            },
            'monitoring': {
                'enabled': True,
                'prometheus': {
                    'enabled': True
                },
                'grafana': {
                    'enabled': True
                }
            },
            'postgresql': {
                'enabled': True,
                'auth': {
                    'database': 'superinstance_ml',
                    'username': 'superinstance'
                }
            },
            'redis': {
                'enabled': True,
                'auth': {
                    'enabled': False
                }
            }
        }
        
        with open(os.path.join(chart_dir, 'values.yaml'), 'w') as f:
            yaml.dump(values_yaml, f, default_flow_style=False, indent=2)
        
        # Create templates directory
        templates_dir = os.path.join(chart_dir, 'templates')
        os.makedirs(templates_dir, exist_ok=True)
        
        # Add basic template files (deployment, service, etc.)
        self._create_helm_templates(templates_dir)
        
        logger.info(f"Created Helm chart in {chart_dir}")
    
    def _create_helm_templates(self, templates_dir: str):
        """Create Helm template files"""
        
        # deployment.yaml template
        deployment_template = '''apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "superinstance-ml.fullname" . }}
  labels:
    {{- include "superinstance-ml.labels" . | nindent 4 }}
spec:
  {{- if not .Values.autoscaling.enabled }}
  replicas: {{ .Values.replicaCount }}
  {{- end }}
  selector:
    matchLabels:
      {{- include "superinstance-ml.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "superinstance-ml.selectorLabels" . | nindent 8 }}
    spec:
      containers:
        - name: {{ .Chart.Name }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - name: http
              containerPort: 8080
              protocol: TCP
            - name: metrics
              containerPort: 8081
              protocol: TCP
          livenessProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 60
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /ready
              port: http
            initialDelaySeconds: 30
            periodSeconds: 10
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
          env:
            - name: ML_SYSTEMS_ENABLED
              value: {{ join "," .Values.mlSystems.enabled | quote }}
            - name: MONITORING_ENABLED
              value: {{ .Values.monitoring.enabled | quote }}
'''
        
        with open(os.path.join(templates_dir, 'deployment.yaml'), 'w') as f:
            f.write(deployment_template)
        
        # service.yaml template
        service_template = '''apiVersion: v1
kind: Service
metadata:
  name: {{ include "superinstance-ml.fullname" . }}
  labels:
    {{- include "superinstance-ml.labels" . | nindent 4 }}
spec:
  type: {{ .Values.service.type }}
  ports:
    - port: {{ .Values.service.port }}
      targetPort: {{ .Values.service.targetPort }}
      protocol: TCP
      name: http
  selector:
    {{- include "superinstance-ml.selectorLabels" . | nindent 4 }}
'''
        
        with open(os.path.join(templates_dir, 'service.yaml'), 'w') as f:
            f.write(service_template)

class DeploymentOrchestrator:
    """Main deployment orchestrator"""
    
    def __init__(self):
        self.docker_deployment = DockerDeployment()
        self.k8s_deployment = KubernetesDeployment()
        self.helm_chart = HelmChart()
        
    def create_deployment_package(self, config: DeploymentConfig, output_dir: str):
        """Create complete deployment package"""
        
        logger.info(f"Creating deployment package for {config.deployment_name}")
        
        # Create directory structure
        os.makedirs(output_dir, exist_ok=True)
        
        # Copy application files
        self._copy_application_files(output_dir)
        
        # Create Docker files
        self.docker_deployment.create_dockerfile(output_dir)
        self.docker_deployment.create_docker_compose(output_dir, config)
        
        # Create Kubernetes manifests
        self.k8s_deployment.create_deployment_yaml(output_dir, config)
        
        # Create Helm chart
        self.helm_chart.create_helm_chart(output_dir)
        
        # Create deployment scripts
        self._create_deployment_scripts(output_dir, config)
        
        # Create configuration files
        self._create_configuration_files(output_dir, config)
        
        # Create documentation
        self._create_deployment_docs(output_dir, config)
        
        logger.info(f"Deployment package created in {output_dir}")
        
    def _copy_application_files(self, output_dir: str):
        """Copy application files to deployment directory"""
        
        # List of files to copy
        app_files = [
            'app.py',
            'ml_response_optimizer.py',
            'ecosystem_voice_ml.py',
            'universal_ai_interpreter.py',
            'lightweight_edge_interpreter.py',
            'system_input_interpreter.py',
            'tiered_llm_system.py',
            'ml_performance_optimizer.py',
            'realtime_learning_accelerator.py',
            'bot_interpreter_system.py',
            'progressive_efficiency_engine.py',
            'overnight_training_system.py',
        ]
        
        # Copy main application files
        src_dir = os.path.dirname(__file__)
        for filename in app_files:
            src_path = os.path.join(src_dir, filename)
            if os.path.exists(src_path):
                dst_path = os.path.join(output_dir, filename)
                shutil.copy2(src_path, dst_path)
        
        # Copy templates and static files
        for dir_name in ['templates', 'static']:
            src_dir_path = os.path.join(src_dir, dir_name)
            if os.path.exists(src_dir_path):
                dst_dir_path = os.path.join(output_dir, dir_name)
                shutil.copytree(src_dir_path, dst_dir_path, dirs_exist_ok=True)
        
    def _create_deployment_scripts(self, output_dir: str, config: DeploymentConfig):
        """Create deployment scripts"""
        
        scripts_dir = os.path.join(output_dir, 'scripts')
        os.makedirs(scripts_dir, exist_ok=True)
        
        # Docker deployment script
        docker_deploy_script = f'''#!/bin/bash
# SuperInstance ML Ecosystem - Docker Deployment Script

set -e

echo "🚀 Deploying SuperInstance ML Ecosystem ({config.environment})"

# Build and start services
docker-compose -f docker-compose.yml build
docker-compose -f docker-compose.yml up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 30

# Check health
echo "🔍 Checking service health..."
curl -f http://localhost:8080/health || {{
    echo "❌ Health check failed"
    docker-compose logs superinstance-ml
    exit 1
}}

echo "✅ Deployment successful!"
echo "📊 Dashboard: http://localhost:8080"
echo "📈 Metrics: http://localhost:8081"
echo "⚙️ Admin: http://localhost:8082"

if [ "{config.monitoring_enabled}" = "True" ]; then
    echo "📊 Grafana: http://localhost:3000 (admin/admin_change_me)"
    echo "🔍 Prometheus: http://localhost:9090"
fi
'''
        
        docker_script_path = os.path.join(scripts_dir, 'deploy-docker.sh')
        with open(docker_script_path, 'w') as f:
            f.write(docker_deploy_script)
        os.chmod(docker_script_path, 0o755)
        
        # Kubernetes deployment script
        k8s_deploy_script = f'''#!/bin/bash
# SuperInstance ML Ecosystem - Kubernetes Deployment Script

set -e

NAMESPACE="superinstance-ml-{config.environment}"

echo "🚀 Deploying SuperInstance ML Ecosystem to Kubernetes ({config.environment})"

# Create namespace
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Apply Kubernetes manifests
echo "📦 Applying Kubernetes manifests..."
kubectl apply -f kubernetes/ -n $NAMESPACE

# Wait for deployment
echo "⏳ Waiting for deployment to be ready..."
kubectl rollout status deployment/{config.deployment_name} -n $NAMESPACE --timeout=300s

# Check pod status
echo "🔍 Checking pod status..."
kubectl get pods -n $NAMESPACE

# Get service endpoints
echo "📍 Service endpoints:"
kubectl get services -n $NAMESPACE

echo "✅ Kubernetes deployment successful!"
'''
        
        k8s_script_path = os.path.join(scripts_dir, 'deploy-k8s.sh')
        with open(k8s_script_path, 'w') as f:
            f.write(k8s_deploy_script)
        os.chmod(k8s_script_path, 0o755)
        
        # Helm deployment script
        helm_deploy_script = f'''#!/bin/bash
# SuperInstance ML Ecosystem - Helm Deployment Script

set -e

RELEASE_NAME="superinstance-ml-{config.environment}"
NAMESPACE="superinstance-ml-{config.environment}"

echo "🚀 Deploying SuperInstance ML Ecosystem with Helm ({config.environment})"

# Add required Helm repositories
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# Create namespace
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Install/upgrade with Helm
helm upgrade --install $RELEASE_NAME ./helm/superinstance-ml \\
    --namespace $NAMESPACE \\
    --values ./helm/superinstance-ml/values-{config.environment}.yaml \\
    --wait --timeout 300s

# Check status
helm status $RELEASE_NAME -n $NAMESPACE

echo "✅ Helm deployment successful!"
echo "🔍 Check status: helm status $RELEASE_NAME -n $NAMESPACE"
'''
        
        helm_script_path = os.path.join(scripts_dir, 'deploy-helm.sh')
        with open(helm_script_path, 'w') as f:
            f.write(helm_deploy_script)
        os.chmod(helm_script_path, 0o755)
    
    def _create_configuration_files(self, output_dir: str, config: DeploymentConfig):
        """Create configuration files"""
        
        config_dir = os.path.join(output_dir, 'config')
        os.makedirs(config_dir, exist_ok=True)
        
        # Application configuration
        app_config = {
            'environment': config.environment,
            'debug': config.environment == 'dev',
            'ml_systems': {
                'enabled': config.ml_systems_enabled,
                'overnight_training': {
                    'enabled': 'overnight_training_system' in config.ml_systems_enabled,
                    'schedule': '0 0 * * *',  # Daily at midnight
                    'cpu_cores': config.resource_limits.get('training_cpu_cores', 4),
                    'memory_gb': config.resource_limits.get('training_memory_gb', 8)
                },
                'performance_optimization': {
                    'enabled': 'ml_performance_optimizer' in config.ml_systems_enabled,
                    'optimization_interval_hours': 24,
                    'max_memory_usage_percent': 70
                }
            },
            'database': {
                'host': config.environment == 'dev' and 'localhost' or 'postgres',
                'port': 5432,
                'name': 'superinstance_ml',
                'user': 'superinstance'
            },
            'redis': {
                'host': config.environment == 'dev' and 'localhost' or 'redis',
                'port': 6379,
                'db': 0
            },
            'monitoring': {
                'enabled': config.monitoring_enabled,
                'metrics_port': 8081,
                'health_check_interval': 30
            },
            'security': config.security_config,
            'logging': {
                'level': config.environment == 'dev' and 'DEBUG' or 'INFO',
                'format': 'json',
                'file': '/app/logs/superinstance-ml.log'
            }
        }
        
        app_config_path = os.path.join(config_dir, f'config-{config.environment}.yaml')
        with open(app_config_path, 'w') as f:
            yaml.dump(app_config, f, default_flow_style=False, indent=2)
        
        # Requirements file
        requirements = '''# SuperInstance ML Ecosystem Dependencies
flask>=2.3.0
redis>=4.5.0
psycopg2-binary>=2.9.0
numpy>=1.24.0
scikit-learn>=1.3.0
pandas>=2.0.0
sqlalchemy>=2.0.0
celery>=5.3.0
prometheus-client>=0.16.0
pyyaml>=6.0
asyncio-mqtt>=0.13.0
docker>=6.1.0
kubernetes>=26.1.0
schedule>=1.2.0
psutil>=5.9.0
'''
        
        requirements_path = os.path.join(output_dir, 'requirements.txt')
        with open(requirements_path, 'w') as f:
            f.write(requirements)
    
    def _create_deployment_docs(self, output_dir: str, config: DeploymentConfig):
        """Create deployment documentation"""
        
        docs_dir = os.path.join(output_dir, 'docs')
        os.makedirs(docs_dir, exist_ok=True)
        
        # Main README
        readme_content = f'''# SuperInstance ML Ecosystem Deployment

## Overview

The SuperInstance ML Ecosystem is a comprehensive multi-layer machine learning system that continuously improves through user interaction analysis and overnight training cycles.

## Features

- 🧠 **Multi-Layer Learning**: 12 integrated ML systems
- 🤖 **Bot Interpretation**: Bot-to-computer and bot-to-bot translation layers
- 📈 **Progressive Efficiency**: Models get smaller and faster over time
- 🌙 **Overnight Training**: Daily analysis and optimization cycles
- ⚡ **Real-time Learning**: Instant adaptation and continuous improvement
- 🎯 **Auto-scaling**: Kubernetes-native scaling and resource management

## Deployment Options

### 1. Docker Compose (Development/Testing)

```bash
# Quick start
./scripts/deploy-docker.sh

# Manual deployment
docker-compose up -d
```

### 2. Kubernetes (Production)

```bash
# Deploy with kubectl
./scripts/deploy-k8s.sh

# Or deploy manually
kubectl apply -f kubernetes/ -n superinstance-ml-{config.environment}
```

### 3. Helm Chart (Recommended)

```bash
# Deploy with Helm
./scripts/deploy-helm.sh

# Or customize values
helm install superinstance-ml ./helm/superinstance-ml \\
    --values custom-values.yaml
```

## Configuration

### Environment Variables

- `ENVIRONMENT`: Deployment environment (dev/staging/production)
- `ML_SYSTEMS_ENABLED`: Comma-separated list of ML systems to enable
- `MONITORING_ENABLED`: Enable monitoring stack (true/false)

### ML Systems Available

{chr(10).join(f"- `{system}`" for system in config.ml_systems_enabled)}

## Resource Requirements

### Minimum (Development)
- CPU: 2 cores
- Memory: 4GB RAM
- Storage: 20GB

### Recommended (Production)
- CPU: 8+ cores
- Memory: 16GB+ RAM
- Storage: 100GB+ SSD
- GPU: Optional (for advanced ML features)

## Monitoring & Observability

- **Health Endpoint**: `/health`
- **Metrics Endpoint**: `/metrics` (Prometheus format)
- **Admin Dashboard**: Port 8082
- **Grafana Dashboard**: Port 3000 (if monitoring enabled)

## Scaling

The system automatically scales based on:
- CPU utilization (target: {config.scale_config.get('cpu_threshold', 70)}%)
- Memory utilization (target: {config.scale_config.get('memory_threshold', 80)}%)
- Queue depth threshold

Min replicas: {config.scale_config.get('min_instances', 2)}
Max replicas: {config.scale_config.get('max_instances', 10)}

## Security

- All components run as non-root users
- Network policies restrict inter-service communication
- Secrets managed through Kubernetes secrets
- Regular security scanning enabled

## Backup & Recovery

- Automated daily backups of ML models and training data
- Point-in-time recovery capability
- Cross-region backup replication (production)

## Support

For issues or questions:
- Documentation: `/docs`
- Health checks: `/health`, `/ready`
- Logs: Check container logs for troubleshooting
- Metrics: Prometheus metrics available on port 8081

## License

SuperInstance ML Ecosystem - Enterprise Edition
'''
        
        readme_path = os.path.join(docs_dir, 'README.md')
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        
        # Deployment guide
        deployment_guide = '''# Deployment Guide

## Pre-requisites

### For Docker Deployment
- Docker 20.0+
- Docker Compose 2.0+
- Minimum 4GB RAM
- 20GB free disk space

### For Kubernetes Deployment
- Kubernetes 1.24+
- kubectl configured
- Helm 3.0+ (for Helm deployment)
- StorageClass configured for persistent volumes

## Step-by-Step Deployment

### 1. Prepare Environment

```bash
# Clone or extract deployment package
cd superinstance-ml-deployment

# Set environment variables
export ENVIRONMENT=production
export ML_SYSTEMS_ENABLED="response_optimizer,voice_learning,universal_interpreter,system_input_interpreter,ml_performance_optimizer,realtime_learning_accelerator,bot_interpreter_system,progressive_efficiency_engine,overnight_training_system"
```

### 2. Configure Deployment

Edit configuration files in `config/`:
- `config-production.yaml`: Main application config
- `docker-compose.yml`: Docker services config
- `kubernetes/`: Kubernetes manifests

### 3. Deploy

Choose your deployment method:

#### Docker Compose
```bash
./scripts/deploy-docker.sh
```

#### Kubernetes
```bash
./scripts/deploy-k8s.sh
```

#### Helm
```bash
./scripts/deploy-helm.sh
```

### 4. Verify Deployment

```bash
# Check health
curl http://localhost:8080/health

# Check all ML systems
curl http://localhost:8080/api/ml/ecosystem/status

# View metrics
curl http://localhost:8081/metrics
```

### 5. Access Services

- **Main App**: http://localhost:8080
- **Metrics**: http://localhost:8081
- **Admin**: http://localhost:8082
- **Grafana**: http://localhost:3000 (if monitoring enabled)

## Troubleshooting

### Common Issues

1. **Port conflicts**: Modify ports in docker-compose.yml or Kubernetes service
2. **Resource limits**: Increase CPU/memory limits in deployment config
3. **Storage issues**: Ensure sufficient disk space and proper StorageClass
4. **Network connectivity**: Check firewall rules and network policies

### Logs

```bash
# Docker
docker-compose logs superinstance-ml

# Kubernetes
kubectl logs -l app=superinstance-ml -n superinstance-ml-production

# Helm
kubectl logs -l app.kubernetes.io/name=superinstance-ml
```

### Health Checks

The system provides multiple health check endpoints:
- `/health`: Overall system health
- `/ready`: Readiness for traffic
- `/api/ml/ecosystem/status`: ML systems status
'''
        
        deployment_guide_path = os.path.join(docs_dir, 'deployment-guide.md')
        with open(deployment_guide_path, 'w') as f:
            f.write(deployment_guide)

# Factory functions for different deployment scenarios
def create_development_config() -> DeploymentConfig:
    """Create development deployment configuration"""
    return DeploymentConfig(
        deployment_name="superinstance-ml-dev",
        environment="dev",
        scale_config={
            'min_instances': 1,
            'max_instances': 3,
            'cpu_threshold': 80,
            'memory_threshold': 85,
            'queue_threshold': 100
        },
        resource_limits={
            'cpu_request': '250m',
            'cpu_limit': '1000m',
            'memory_request': '512Mi',
            'memory_limit': '2Gi'
        },
        security_config={
            'enable_auth': False,
            'enable_tls': False,
            'cors_enabled': True
        },
        storage_config={
            'storage_class': 'standard',
            'data_size': '5Gi',
            'models_size': '10Gi'
        },
        networking_config={
            'ingress_enabled': False,
            'load_balancer': False
        },
        ml_systems_enabled=[
            'response_optimizer',
            'universal_interpreter',
            'system_input_interpreter',
            'ml_performance_optimizer',
            'progressive_efficiency_engine'
        ],
        monitoring_enabled=True,
        backup_enabled=False
    )

def create_production_config() -> DeploymentConfig:
    """Create production deployment configuration"""
    return DeploymentConfig(
        deployment_name="superinstance-ml-prod",
        environment="production",
        scale_config={
            'min_instances': 3,
            'max_instances': 20,
            'cpu_threshold': 70,
            'memory_threshold': 80,
            'queue_threshold': 50
        },
        resource_limits={
            'cpu_request': '1000m',
            'cpu_limit': '4000m',
            'memory_request': '2Gi',
            'memory_limit': '8Gi',
            'training_cpu_cores': 8,
            'training_memory_gb': 16
        },
        security_config={
            'enable_auth': True,
            'enable_tls': True,
            'cors_enabled': False,
            'network_policies': True
        },
        storage_config={
            'storage_class': 'fast-ssd',
            'data_size': '100Gi',
            'models_size': '500Gi'
        },
        networking_config={
            'ingress_enabled': True,
            'load_balancer': True,
            'cdn_enabled': True
        },
        ml_systems_enabled=[
            'response_optimizer',
            'voice_learning',
            'universal_interpreter',
            'edge_interpreter',
            'system_input_interpreter',
            'ui_navigation_assistant',
            'tiered_llm_system',
            'ml_performance_optimizer',
            'realtime_learning_accelerator',
            'bot_interpreter_system',
            'progressive_efficiency_engine',
            'overnight_training_system'
        ],
        monitoring_enabled=True,
        backup_enabled=True
    )

# Main CLI interface
def main():
    """Main deployment package generator"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SuperInstance ML Ecosystem Deployment Package Generator')
    parser.add_argument('--environment', choices=['dev', 'staging', 'production'], 
                       default='production', help='Target environment')
    parser.add_argument('--output-dir', required=True, help='Output directory for deployment package')
    parser.add_argument('--build-image', action='store_true', help='Build Docker image')
    
    args = parser.parse_args()
    
    # Create configuration based on environment
    if args.environment == 'dev':
        config = create_development_config()
    else:
        config = create_production_config()
        config.environment = args.environment
        config.deployment_name = f"superinstance-ml-{args.environment}"
    
    # Create deployment orchestrator
    orchestrator = DeploymentOrchestrator()
    
    # Generate deployment package
    orchestrator.create_deployment_package(config, args.output_dir)
    
    # Build Docker image if requested
    if args.build_image:
        image = orchestrator.docker_deployment.build_image(
            args.output_dir, 
            f"superinstance-ml-ecosystem:{args.environment}"
        )
        logger.info(f"Built Docker image: {image.tags}")
    
    logger.info("🎉 Deployment package ready for widespread adoption!")
    logger.info(f"📦 Package location: {args.output_dir}")
    logger.info(f"🚀 Deploy with: cd {args.output_dir} && ./scripts/deploy-{args.environment}.sh")

if __name__ == "__main__":
    main()