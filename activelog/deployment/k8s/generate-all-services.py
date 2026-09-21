#!/usr/bin/env python3
"""
Generate Kubernetes manifests for all ActiveLog services
"""

import os
import yaml

# Service configurations from inventory
SERVICES = [
    # Core Infrastructure Services
    {"name": "api-gateway", "type": "gateway", "port": 8000, "replicas": 3, "cpu": "500m", "memory": "512Mi"},
    {"name": "auth", "type": "authentication", "port": 8001, "replicas": 2, "cpu": "200m", "memory": "256Mi"},
    {"name": "graphql", "type": "api", "port": 8002, "replicas": 2, "cpu": "300m", "memory": "512Mi"},
    
    # Data Management Services
    {"name": "data-manager", "type": "data", "port": 8010, "replicas": 2, "cpu": "400m", "memory": "1Gi"},
    {"name": "data-export", "type": "data", "port": 8011, "replicas": 1, "cpu": "300m", "memory": "512Mi"},
    {"name": "batch-import", "type": "data", "port": 8012, "replicas": 1, "cpu": "400m", "memory": "1Gi"},
    {"name": "metadata", "type": "data", "port": 8013, "replicas": 2, "cpu": "200m", "memory": "256Mi"},
    {"name": "file-processor", "type": "processing", "port": 8014, "replicas": 2, "cpu": "600m", "memory": "1Gi"},
    
    # Synchronization Services
    {"name": "sync-engine", "type": "sync", "port": 8020, "replicas": 3, "cpu": "400m", "memory": "512Mi"},
    {"name": "sync-v2", "type": "sync", "port": 8021, "replicas": 3, "cpu": "500m", "memory": "768Mi"},
    {"name": "file-sync", "type": "sync", "port": 8022, "replicas": 2, "cpu": "300m", "memory": "512Mi"},
    {"name": "p2p-sync", "type": "sync", "port": 8023, "replicas": 2, "cpu": "400m", "memory": "512Mi"},
    {"name": "file-watcher", "type": "monitoring", "port": 8024, "replicas": 2, "cpu": "200m", "memory": "256Mi"},
    
    # AI and ML Services
    {"name": "ai-orchestrator", "type": "ai", "port": 8030, "replicas": 2, "cpu": "1000m", "memory": "2Gi", "gpu": True},
    {"name": "ai-tools", "type": "ai", "port": 8031, "replicas": 2, "cpu": "800m", "memory": "1Gi"},
    {"name": "ml-pipeline", "type": "ml", "port": 8032, "replicas": 2, "cpu": "1000m", "memory": "2Gi", "gpu": True},
    {"name": "predictive", "type": "ml", "port": 8033, "replicas": 1, "cpu": "800m", "memory": "1Gi"},
    {"name": "predictive-ai", "type": "ml", "port": 8034, "replicas": 1, "cpu": "800m", "memory": "1Gi"},
    {"name": "document-ai", "type": "ai", "port": 8035, "replicas": 1, "cpu": "600m", "memory": "1Gi"},
    {"name": "emotional-ai", "type": "ai", "port": 8036, "replicas": 1, "cpu": "400m", "memory": "768Mi"},
    {"name": "education-ai", "type": "ai", "port": 8037, "replicas": 1, "cpu": "400m", "memory": "768Mi"},
    {"name": "cognitive", "type": "ai", "port": 8038, "replicas": 1, "cpu": "600m", "memory": "1Gi"},
    {"name": "social-ai", "type": "ai", "port": 8039, "replicas": 1, "cpu": "400m", "memory": "512Mi"},
    
    # Video and Media Services
    {"name": "video-pipeline", "type": "media", "port": 8040, "replicas": 2, "cpu": "1200m", "memory": "2Gi", "gpu": True},
    {"name": "video-processor", "type": "media", "port": 8041, "replicas": 2, "cpu": "1000m", "memory": "1Gi"},
    {"name": "creative-suite", "type": "media", "port": 8042, "replicas": 1, "cpu": "800m", "memory": "1Gi"},
    
    # Gaming Services
    {"name": "gaming-platform", "type": "gaming", "port": 8070, "replicas": 2, "cpu": "600m", "memory": "1Gi"},
    {"name": "dmlog-core", "type": "gaming", "port": 8071, "replicas": 1, "cpu": "300m", "memory": "512Mi"},
    {"name": "dmlog-characters", "type": "gaming", "port": 8072, "replicas": 1, "cpu": "200m", "memory": "256Mi"},
    {"name": "dmlog-battle", "type": "gaming", "port": 8073, "replicas": 1, "cpu": "300m", "memory": "512Mi"},
    {"name": "dmlog-session", "type": "gaming", "port": 8074, "replicas": 1, "cpu": "200m", "memory": "256Mi"},
    {"name": "dmlog-world", "type": "gaming", "port": 8075, "replicas": 1, "cpu": "300m", "memory": "512Mi"},
    {"name": "dmlog-marketplace", "type": "gaming", "port": 8076, "replicas": 1, "cpu": "200m", "memory": "256Mi"},
    {"name": "dmlog-ai-dm", "type": "gaming", "port": 8077, "replicas": 1, "cpu": "400m", "memory": "768Mi"},
    {"name": "dmlog-player", "type": "gaming", "port": 8078, "replicas": 1, "cpu": "200m", "memory": "256Mi"},
    {"name": "dmlog-templates", "type": "gaming", "port": 8079, "replicas": 1, "cpu": "100m", "memory": "128Mi"},
    {"name": "dmlog-converter", "type": "gaming", "port": 8080, "replicas": 1, "cpu": "200m", "memory": "256Mi"},
]

def generate_deployment(service):
    """Generate Kubernetes Deployment manifest"""
    name = service["name"]
    service_type = service["type"]
    port = service["port"]
    replicas = service["replicas"]
    cpu = service["cpu"]
    memory = service["memory"]
    gpu = service.get("gpu", False)
    
    # Calculate resource limits (1.5x requests)
    cpu_limit = f"{int(cpu.replace('m', '')) * 3 // 2}m"
    
    if 'Gi' in memory:
        memory_limit = f"{int(memory.replace('Gi', '')) * 3 // 2}Gi"
    elif 'Mi' in memory:
        memory_limit = f"{int(memory.replace('Mi', '')) * 3 // 2}Mi"
    else:
        memory_limit = memory
    
    deployment = {
        'apiVersion': 'apps/v1',
        'kind': 'Deployment',
        'metadata': {
            'name': name,
            'namespace': 'activelog',
            'labels': {
                'app': f'activelog-{name}',
                'component': service_type,
                'version': 'v1'
            }
        },
        'spec': {
            'replicas': replicas,
            'strategy': {
                'type': 'RollingUpdate',
                'rollingUpdate': {
                    'maxSurge': 1,
                    'maxUnavailable': 1
                }
            },
            'selector': {
                'matchLabels': {
                    'app': f'activelog-{name}'
                }
            },
            'template': {
                'metadata': {
                    'labels': {
                        'app': f'activelog-{name}',
                        'component': service_type,
                        'version': 'v1'
                    },
                    'annotations': {
                        'prometheus.io/scrape': 'true',
                        'prometheus.io/port': '9090',
                        'prometheus.io/path': '/metrics',
                        'sidecar.istio.io/inject': 'true'
                    }
                },
                'spec': {
                    'serviceAccountName': f'activelog-{name}',
                    'containers': [{
                        'name': name,
                        'image': f'activelog/{name}:latest',
                        'imagePullPolicy': 'IfNotPresent',
                        'ports': [
                            {
                                'name': 'http',
                                'containerPort': port,
                                'protocol': 'TCP'
                            },
                            {
                                'name': 'metrics',
                                'containerPort': 9090,
                                'protocol': 'TCP'
                            },
                            {
                                'name': 'health',
                                'containerPort': 8080,
                                'protocol': 'TCP'
                            }
                        ],
                        'env': [
                            {'name': 'PORT', 'value': str(port)},
                            {
                                'name': 'NODE_ENV',
                                'valueFrom': {
                                    'configMapKeyRef': {
                                        'name': 'activelog-config',
                                        'key': 'NODE_ENV'
                                    }
                                }
                            },
                            {
                                'name': 'LOG_LEVEL',
                                'valueFrom': {
                                    'configMapKeyRef': {
                                        'name': 'activelog-config',
                                        'key': 'LOG_LEVEL'
                                    }
                                }
                            }
                        ],
                        'resources': {
                            'requests': {
                                'memory': memory,
                                'cpu': cpu
                            },
                            'limits': {
                                'memory': memory_limit,
                                'cpu': cpu_limit
                            }
                        },
                        'livenessProbe': {
                            'httpGet': {
                                'path': '/health',
                                'port': 'health'
                            },
                            'initialDelaySeconds': 30,
                            'periodSeconds': 10,
                            'timeoutSeconds': 5,
                            'failureThreshold': 3
                        },
                        'readinessProbe': {
                            'httpGet': {
                                'path': '/ready',
                                'port': 'health'
                            },
                            'initialDelaySeconds': 5,
                            'periodSeconds': 5,
                            'timeoutSeconds': 3,
                            'failureThreshold': 3
                        },
                        'securityContext': {
                            'allowPrivilegeEscalation': False,
                            'runAsNonRoot': True,
                            'runAsUser': 1000,
                            'capabilities': {
                                'drop': ['ALL']
                            }
                        }
                    }],
                    'terminationGracePeriodSeconds': 30,
                    'dnsPolicy': 'ClusterFirst',
                    'restartPolicy': 'Always'
                }
            }
        }
    }
    
    # Add GPU resources if needed
    if gpu:
        deployment['spec']['template']['spec']['containers'][0]['resources']['limits']['nvidia.com/gpu'] = 1
    
    return deployment

def generate_service(service):
    """Generate Kubernetes Service manifest"""
    name = service["name"]
    service_type = service["type"]
    port = service["port"]
    
    return {
        'apiVersion': 'v1',
        'kind': 'Service',
        'metadata': {
            'name': name,
            'namespace': 'activelog',
            'labels': {
                'app': f'activelog-{name}',
                'component': service_type
            },
            'annotations': {
                'prometheus.io/scrape': 'true',
                'prometheus.io/port': '9090'
            }
        },
        'spec': {
            'type': 'ClusterIP',
            'ports': [
                {
                    'name': 'http',
                    'port': port,
                    'targetPort': 'http',
                    'protocol': 'TCP'
                },
                {
                    'name': 'metrics',
                    'port': 9090,
                    'targetPort': 'metrics',
                    'protocol': 'TCP'
                }
            ],
            'selector': {
                'app': f'activelog-{name}'
            }
        }
    }

def generate_hpa(service):
    """Generate Horizontal Pod Autoscaler"""
    name = service["name"]
    replicas = service["replicas"]
    max_replicas = min(replicas * 4, 20)  # 4x scaling max, cap at 20
    
    return {
        'apiVersion': 'autoscaling/v2',
        'kind': 'HorizontalPodAutoscaler',
        'metadata': {
            'name': f'{name}-hpa',
            'namespace': 'activelog'
        },
        'spec': {
            'scaleTargetRef': {
                'apiVersion': 'apps/v1',
                'kind': 'Deployment',
                'name': name
            },
            'minReplicas': replicas,
            'maxReplicas': max_replicas,
            'metrics': [
                {
                    'type': 'Resource',
                    'resource': {
                        'name': 'cpu',
                        'target': {
                            'type': 'Utilization',
                            'averageUtilization': 70
                        }
                    }
                },
                {
                    'type': 'Resource',
                    'resource': {
                        'name': 'memory',
                        'target': {
                            'type': 'Utilization',
                            'averageUtilization': 80
                        }
                    }
                }
            ],
            'behavior': {
                'scaleDown': {
                    'stabilizationWindowSeconds': 300,
                    'policies': [
                        {
                            'type': 'Percent',
                            'value': 50,
                            'periodSeconds': 60
                        }
                    ]
                },
                'scaleUp': {
                    'stabilizationWindowSeconds': 60,
                    'policies': [
                        {
                            'type': 'Percent',
                            'value': 100,
                            'periodSeconds': 15
                        },
                        {
                            'type': 'Pods',
                            'value': 2,
                            'periodSeconds': 60
                        }
                    ]
                }
            }
        }
    }

def generate_service_account(service):
    """Generate ServiceAccount"""
    name = service["name"]
    
    return {
        'apiVersion': 'v1',
        'kind': 'ServiceAccount',
        'metadata': {
            'name': f'activelog-{name}',
            'namespace': 'activelog',
            'labels': {
                'app': f'activelog-{name}'
            }
        }
    }

def generate_pdb(service):
    """Generate Pod Disruption Budget"""
    name = service["name"]
    replicas = service["replicas"]
    min_available = max(1, replicas // 2)
    
    return {
        'apiVersion': 'policy/v1',
        'kind': 'PodDisruptionBudget',
        'metadata': {
            'name': f'{name}-pdb',
            'namespace': 'activelog'
        },
        'spec': {
            'minAvailable': min_available,
            'selector': {
                'matchLabels': {
                    'app': f'activelog-{name}'
                }
            }
        }
    }

def main():
    """Generate all service manifests"""
    os.makedirs('./services', exist_ok=True)
    
    for service in SERVICES:
        name = service["name"]
        
        # Generate all manifests for this service
        manifests = [
            generate_deployment(service),
            generate_service(service),
            generate_service_account(service),
            generate_hpa(service),
            generate_pdb(service)
        ]
        
        # Write to file
        filename = f'./services/{name}.yaml'
        with open(filename, 'w') as f:
            for i, manifest in enumerate(manifests):
                if i > 0:
                    f.write('---\n')
                yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)
        
        print(f"Generated manifests for {name}")
    
    print(f"\nGenerated manifests for {len(SERVICES)} services")

if __name__ == '__main__':
    main()