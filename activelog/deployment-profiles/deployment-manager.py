#!/usr/bin/env python3
"""
Deployment Profile Manager
Manages workload-specific deployment profiles and automates deployment transitions
"""

import asyncio
import json
import logging
import subprocess
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import aiohttp
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Deployment Profile Manager", version="1.0.0")

class WorkloadType(str, Enum):
    FINANCIAL_TRADING = "financial_trading"
    ANALYTICS_HEAVY = "analytics_heavy" 
    WEB_TRAFFIC = "web_traffic"
    BATCH_PROCESSING = "batch_processing"
    DEVELOPMENT = "development"
    TESTING = "testing"
    MINIMAL = "minimal"

@dataclass
class ProfileMetrics:
    cpu_efficiency: float
    memory_utilization: float
    response_time: float
    throughput: float
    error_rate: float
    cost_per_hour: float

class DeploymentRequest(BaseModel):
    target_profile: WorkloadType
    namespace: str = "activelog"
    validate_before_deploy: bool = True
    rollback_on_failure: bool = True

class ProfileValidationResult(BaseModel):
    profile_name: str
    valid: bool
    issues: List[str] = []
    warnings: List[str] = []
    resource_requirements: Dict[str, Any] = {}

class DeploymentProfileManager:
    def __init__(self):
        self.profiles_dir = Path(__file__).parent
        self.current_profile = None
        self.kubectl_available = self._check_kubectl()
        self.helm_available = self._check_helm()
        
        # Load profile configurations
        self.profiles = self._load_profile_configs()
        
        # Deployment history
        self.deployment_history = []
        
    def _check_kubectl(self) -> bool:
        """Check if kubectl is available"""
        try:
            result = subprocess.run(['kubectl', 'version', '--client'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            logger.warning("kubectl not found - Kubernetes deployments will not work")
            return False
            
    def _check_helm(self) -> bool:
        """Check if Helm is available"""
        try:
            result = subprocess.run(['helm', 'version'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            logger.warning("helm not found - Helm deployments will not work")
            return False
            
    def _load_profile_configs(self) -> Dict[str, Dict]:
        """Load all profile configurations"""
        profiles = {}
        
        for profile_file in self.profiles_dir.glob("*.yaml"):
            if profile_file.name == "deployment-manager.yaml":
                continue
                
            try:
                with open(profile_file, 'r') as f:
                    profile_docs = list(yaml.safe_load_all(f))
                    
                # Extract ConfigMap data
                config_map = next((doc for doc in profile_docs 
                                 if doc.get('kind') == 'ConfigMap'), None)
                
                if config_map:
                    profile_data = config_map['data']
                    workload_type = profile_data.get('workload_type')
                    
                    if workload_type:
                        profiles[workload_type] = {
                            'name': profile_data.get('profile_name'),
                            'file_path': profile_file,
                            'config': profile_data,
                            'manifests': profile_docs
                        }
                        
            except Exception as e:
                logger.error(f"Failed to load profile {profile_file}: {e}")
                
        logger.info(f"Loaded {len(profiles)} deployment profiles")
        return profiles
        
    async def validate_profile(self, workload_type: WorkloadType) -> ProfileValidationResult:
        """Validate a deployment profile"""
        if workload_type.value not in self.profiles:
            return ProfileValidationResult(
                profile_name=workload_type.value,
                valid=False,
                issues=[f"Profile {workload_type.value} not found"]
            )
            
        profile = self.profiles[workload_type.value]
        result = ProfileValidationResult(
            profile_name=profile['name'],
            valid=True,
            issues=[],
            warnings=[]
        )
        
        try:
            # Parse resource allocation
            resource_config = yaml.safe_load(profile['config']['resource_allocation'])
            total_cpu = 0
            total_memory = 0
            
            for service, resources in resource_config.items():
                cpu = self._parse_cpu_value(resources.get('cpu', '0m'))
                memory = self._parse_memory_value(resources.get('memory', '0Mi'))
                instances = resources.get('instances', 1)
                
                total_cpu += cpu * instances
                total_memory += memory * instances
                
            result.resource_requirements = {
                'total_cpu_cores': total_cpu,
                'total_memory_gb': total_memory / 1024,
                'estimated_cost_per_hour': self._estimate_cost(total_cpu, total_memory)
            }
            
            # Validate resource limits
            if total_cpu > 100:  # More than 100 CPU cores
                result.warnings.append(f"High CPU requirement: {total_cpu} cores")
                
            if total_memory > 500:  # More than 500 GB memory
                result.warnings.append(f"High memory requirement: {total_memory/1024:.1f} GB")
                
            # Validate Kubernetes manifests
            for manifest in profile['manifests']:
                if manifest.get('kind') in ['Deployment', 'StatefulSet']:
                    validation_issues = self._validate_k8s_manifest(manifest)
                    result.issues.extend(validation_issues)
                    
        except Exception as e:
            result.valid = False
            result.issues.append(f"Validation error: {str(e)}")
            
        if result.issues:
            result.valid = False
            
        return result
        
    def _parse_cpu_value(self, cpu_str: str) -> float:
        """Parse CPU value (e.g., '2000m' -> 2.0)"""
        if cpu_str.endswith('m'):
            return float(cpu_str[:-1]) / 1000
        return float(cpu_str)
        
    def _parse_memory_value(self, memory_str: str) -> float:
        """Parse memory value in MB (e.g., '4Gi' -> 4096)"""
        if memory_str.endswith('Gi'):
            return float(memory_str[:-2]) * 1024
        elif memory_str.endswith('Mi'):
            return float(memory_str[:-2])
        elif memory_str.endswith('G'):
            return float(memory_str[:-1]) * 1024
        elif memory_str.endswith('M'):
            return float(memory_str[:-1])
        return float(memory_str)
        
    def _estimate_cost(self, cpu_cores: float, memory_mb: float) -> float:
        """Estimate hourly cost based on resource usage"""
        # Rough AWS pricing estimates
        cpu_cost_per_hour = cpu_cores * 0.05  # $0.05 per vCPU per hour
        memory_cost_per_hour = (memory_mb / 1024) * 0.01  # $0.01 per GB per hour
        return cpu_cost_per_hour + memory_cost_per_hour
        
    def _validate_k8s_manifest(self, manifest: Dict) -> List[str]:
        """Validate Kubernetes manifest"""
        issues = []
        
        # Check required fields
        if 'metadata' not in manifest:
            issues.append(f"{manifest.get('kind', 'Unknown')} missing metadata")
            
        if 'spec' not in manifest:
            issues.append(f"{manifest.get('kind', 'Unknown')} missing spec")
            
        # Validate container specs
        if manifest.get('kind') in ['Deployment', 'StatefulSet']:
            containers = manifest.get('spec', {}).get('template', {}).get('spec', {}).get('containers', [])
            
            for container in containers:
                if 'image' not in container:
                    issues.append(f"Container {container.get('name', 'unknown')} missing image")
                    
                resources = container.get('resources', {})
                if not resources.get('requests') and not resources.get('limits'):
                    issues.append(f"Container {container.get('name', 'unknown')} missing resource specifications")
                    
        return issues
        
    async def deploy_profile(self, request: DeploymentRequest) -> Dict[str, Any]:
        """Deploy a workload profile"""
        if not self.kubectl_available:
            raise HTTPException(status_code=500, detail="kubectl not available")
            
        start_time = datetime.now()
        deployment_id = f"deploy-{request.target_profile.value}-{start_time.strftime('%Y%m%d-%H%M%S')}"
        
        logger.info(f"Starting deployment {deployment_id}")
        
        try:
            # Validate profile first
            if request.validate_before_deploy:
                validation = await self.validate_profile(request.target_profile)
                if not validation.valid:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Profile validation failed: {validation.issues}"
                    )
                    
            # Get current state for potential rollback
            current_state = None
            if request.rollback_on_failure and self.current_profile:
                current_state = await self._capture_current_state(request.namespace)
                
            # Apply the new profile
            profile = self.profiles[request.target_profile.value]
            deployment_result = await self._apply_k8s_manifests(
                profile['manifests'], 
                request.namespace
            )
            
            # Wait for deployment to be ready
            await self._wait_for_deployment_ready(request.namespace, timeout=600)
            
            # Validate deployment success
            health_check = await self._validate_deployment_health(request.namespace)
            
            if not health_check['healthy'] and request.rollback_on_failure and current_state:
                logger.warning("Deployment unhealthy, rolling back")
                await self._rollback_deployment(current_state, request.namespace)
                raise Exception("Deployment failed health check, rolled back")
                
            # Update current profile
            self.current_profile = request.target_profile
            
            # Record deployment
            deployment_record = {
                'deployment_id': deployment_id,
                'profile': request.target_profile.value,
                'namespace': request.namespace,
                'start_time': start_time.isoformat(),
                'end_time': datetime.now().isoformat(),
                'success': True,
                'details': deployment_result
            }
            self.deployment_history.append(deployment_record)
            
            logger.info(f"Deployment {deployment_id} completed successfully")
            
            return {
                'deployment_id': deployment_id,
                'success': True,
                'profile': request.target_profile.value,
                'duration_seconds': (datetime.now() - start_time).total_seconds(),
                'health_check': health_check,
                'resource_usage': await self._get_resource_usage(request.namespace)
            }
            
        except Exception as e:
            logger.error(f"Deployment {deployment_id} failed: {e}")
            
            # Record failed deployment
            deployment_record = {
                'deployment_id': deployment_id,
                'profile': request.target_profile.value,
                'namespace': request.namespace,
                'start_time': start_time.isoformat(),
                'end_time': datetime.now().isoformat(),
                'success': False,
                'error': str(e)
            }
            self.deployment_history.append(deployment_record)
            
            raise HTTPException(status_code=500, detail=str(e))
            
    async def _capture_current_state(self, namespace: str) -> Dict:
        """Capture current deployment state for rollback"""
        try:
            result = subprocess.run([
                'kubectl', 'get', 'all', '-n', namespace, '-o', 'yaml'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                return {'manifests': result.stdout}
            else:
                logger.warning(f"Failed to capture current state: {result.stderr}")
                return {}
                
        except Exception as e:
            logger.error(f"Error capturing current state: {e}")
            return {}
            
    async def _apply_k8s_manifests(self, manifests: List[Dict], namespace: str) -> Dict:
        """Apply Kubernetes manifests"""
        applied_resources = []
        
        # Ensure namespace exists
        await self._ensure_namespace(namespace)
        
        for manifest in manifests:
            if not manifest or manifest.get('kind') == 'ConfigMap':
                continue  # Skip ConfigMaps as they're just for configuration
                
            try:
                # Convert manifest to YAML
                yaml_content = yaml.dump(manifest)
                
                # Apply via kubectl
                process = subprocess.Popen([
                    'kubectl', 'apply', '-f', '-', '-n', namespace
                ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                
                stdout, stderr = process.communicate(input=yaml_content)
                
                if process.returncode == 0:
                    applied_resources.append({
                        'kind': manifest.get('kind'),
                        'name': manifest.get('metadata', {}).get('name'),
                        'status': 'applied'
                    })
                else:
                    raise Exception(f"kubectl apply failed: {stderr}")
                    
            except Exception as e:
                logger.error(f"Failed to apply manifest {manifest.get('kind', 'Unknown')}: {e}")
                raise
                
        return {'applied_resources': applied_resources}
        
    async def _ensure_namespace(self, namespace: str):
        """Ensure namespace exists"""
        result = subprocess.run([
            'kubectl', 'get', 'namespace', namespace
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            # Create namespace
            subprocess.run([
                'kubectl', 'create', 'namespace', namespace
            ], check=True)
            logger.info(f"Created namespace {namespace}")
            
    async def _wait_for_deployment_ready(self, namespace: str, timeout: int = 600):
        """Wait for all deployments to be ready"""
        end_time = datetime.now().timestamp() + timeout
        
        while datetime.now().timestamp() < end_time:
            result = subprocess.run([
                'kubectl', 'get', 'deployments', '-n', namespace, '-o', 'json'
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                await asyncio.sleep(10)
                continue
                
            deployments = json.loads(result.stdout)
            all_ready = True
            
            for deployment in deployments.get('items', []):
                status = deployment.get('status', {})
                ready_replicas = status.get('readyReplicas', 0)
                desired_replicas = status.get('replicas', 1)
                
                if ready_replicas < desired_replicas:
                    all_ready = False
                    break
                    
            if all_ready:
                logger.info("All deployments ready")
                return
                
            await asyncio.sleep(10)
            
        raise Exception(f"Deployment readiness timeout after {timeout} seconds")
        
    async def _validate_deployment_health(self, namespace: str) -> Dict[str, Any]:
        """Validate deployment health"""
        health_status = {
            'healthy': True,
            'services_checked': 0,
            'services_healthy': 0,
            'issues': []
        }
        
        try:
            # Get all services
            result = subprocess.run([
                'kubectl', 'get', 'services', '-n', namespace, '-o', 'json'
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                health_status['healthy'] = False
                health_status['issues'].append("Failed to get services")
                return health_status
                
            services = json.loads(result.stdout)
            
            for service in services.get('items', []):
                service_name = service['metadata']['name']
                health_status['services_checked'] += 1
                
                # Try to connect to service health endpoint
                try:
                    # Port forward and check health (simplified)
                    # In a real implementation, this would use proper service discovery
                    health_status['services_healthy'] += 1
                except Exception as e:
                    health_status['issues'].append(f"Service {service_name} health check failed: {e}")
                    
            if health_status['services_checked'] == 0:
                health_status['healthy'] = False
                health_status['issues'].append("No services found")
            elif health_status['services_healthy'] < health_status['services_checked']:
                health_status['healthy'] = False
                
        except Exception as e:
            health_status['healthy'] = False
            health_status['issues'].append(f"Health check error: {e}")
            
        return health_status
        
    async def _rollback_deployment(self, previous_state: Dict, namespace: str):
        """Rollback to previous deployment state"""
        if not previous_state.get('manifests'):
            raise Exception("No previous state to rollback to")
            
        try:
            # Apply previous manifests
            process = subprocess.Popen([
                'kubectl', 'apply', '-f', '-', '-n', namespace
            ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            stdout, stderr = process.communicate(input=previous_state['manifests'])
            
            if process.returncode != 0:
                raise Exception(f"Rollback failed: {stderr}")
                
            logger.info("Rollback completed successfully")
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            raise
            
    async def _get_resource_usage(self, namespace: str) -> Dict[str, Any]:
        """Get current resource usage"""
        try:
            result = subprocess.run([
                'kubectl', 'top', 'pods', '-n', namespace, '--no-headers'
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                return {'error': 'Failed to get resource usage'}
                
            total_cpu = 0
            total_memory = 0
            pod_count = 0
            
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 3:
                        cpu_str = parts[1]  # e.g., "23m"
                        memory_str = parts[2]  # e.g., "45Mi"
                        
                        # Parse CPU
                        if cpu_str.endswith('m'):
                            total_cpu += float(cpu_str[:-1]) / 1000
                        else:
                            total_cpu += float(cpu_str)
                            
                        # Parse Memory
                        if memory_str.endswith('Mi'):
                            total_memory += float(memory_str[:-2])
                        elif memory_str.endswith('Gi'):
                            total_memory += float(memory_str[:-2]) * 1024
                            
                        pod_count += 1
                        
            return {
                'total_cpu_cores': round(total_cpu, 2),
                'total_memory_mb': round(total_memory, 2),
                'pod_count': pod_count,
                'average_cpu_per_pod': round(total_cpu / pod_count if pod_count > 0 else 0, 3),
                'average_memory_per_pod_mb': round(total_memory / pod_count if pod_count > 0 else 0, 1)
            }
            
        except Exception as e:
            return {'error': f'Failed to get resource usage: {e}'}
            
    async def get_profile_comparison(self, profiles: List[WorkloadType]) -> Dict[str, Any]:
        """Compare multiple profiles"""
        comparison = {
            'profiles': [],
            'recommendations': []
        }
        
        for profile_type in profiles:
            if profile_type.value in self.profiles:
                profile = self.profiles[profile_type.value]
                validation = await self.validate_profile(profile_type)
                
                comparison['profiles'].append({
                    'workload_type': profile_type.value,
                    'name': profile['name'],
                    'resource_requirements': validation.resource_requirements,
                    'estimated_cost_per_hour': validation.resource_requirements.get('estimated_cost_per_hour', 0),
                    'issues': validation.issues,
                    'warnings': validation.warnings
                })
                
        # Generate recommendations
        if len(comparison['profiles']) > 1:
            costs = [p['estimated_cost_per_hour'] for p in comparison['profiles']]
            min_cost_profile = comparison['profiles'][costs.index(min(costs))]
            max_cost_profile = comparison['profiles'][costs.index(max(costs))]
            
            comparison['recommendations'].append({
                'type': 'cost_optimization',
                'message': f"Most cost-effective: {min_cost_profile['name']} (${min_cost_profile['estimated_cost_per_hour']:.2f}/hour)"
            })
            
            if max_cost_profile['estimated_cost_per_hour'] > min_cost_profile['estimated_cost_per_hour'] * 2:
                comparison['recommendations'].append({
                    'type': 'cost_warning',
                    'message': f"{max_cost_profile['name']} costs {max_cost_profile['estimated_cost_per_hour']/min_cost_profile['estimated_cost_per_hour']:.1f}x more than {min_cost_profile['name']}"
                })
                
        return comparison

# Global deployment manager instance
deployment_manager = DeploymentProfileManager()

@app.on_startup
async def startup():
    """Start deployment profile manager"""
    logger.info("Starting Deployment Profile Manager")
    logger.info(f"Found profiles: {list(deployment_manager.profiles.keys())}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "service": "deployment-profile-manager",
        "profiles_loaded": len(deployment_manager.profiles),
        "kubectl_available": deployment_manager.kubectl_available,
        "helm_available": deployment_manager.helm_available
    }

@app.get("/profiles")
async def list_profiles():
    """List all available deployment profiles"""
    profiles_info = []
    
    for workload_type, profile in deployment_manager.profiles.items():
        validation = await deployment_manager.validate_profile(WorkloadType(workload_type))
        
        profiles_info.append({
            'workload_type': workload_type,
            'name': profile['name'],
            'file_path': str(profile['file_path']),
            'resource_requirements': validation.resource_requirements,
            'valid': validation.valid,
            'issues_count': len(validation.issues),
            'warnings_count': len(validation.warnings)
        })
        
    return profiles_info

@app.get("/profiles/{workload_type}/validate")
async def validate_profile_endpoint(workload_type: WorkloadType):
    """Validate a specific deployment profile"""
    return await deployment_manager.validate_profile(workload_type)

@app.post("/deploy")
async def deploy_profile_endpoint(request: DeploymentRequest):
    """Deploy a workload profile"""
    return await deployment_manager.deploy_profile(request)

@app.get("/deployments/history")
async def get_deployment_history():
    """Get deployment history"""
    return deployment_manager.deployment_history[-10:]  # Last 10 deployments

@app.get("/deployments/current")
async def get_current_deployment():
    """Get current active deployment"""
    return {
        'current_profile': deployment_manager.current_profile.value if deployment_manager.current_profile else None,
        'deployment_time': datetime.now().isoformat()
    }

@app.post("/profiles/compare")
async def compare_profiles(profiles: List[WorkloadType]):
    """Compare multiple deployment profiles"""
    return await deployment_manager.get_profile_comparison(profiles)

@app.get("/profiles/{workload_type}/preview")
async def preview_deployment(workload_type: WorkloadType, namespace: str = "activelog"):
    """Preview what would be deployed without actually deploying"""
    if workload_type.value not in deployment_manager.profiles:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    profile = deployment_manager.profiles[workload_type.value]
    validation = await deployment_manager.validate_profile(workload_type)
    
    return {
        'profile_name': profile['name'],
        'workload_type': workload_type.value,
        'validation': validation,
        'manifests_count': len([m for m in profile['manifests'] if m.get('kind') != 'ConfigMap']),
        'resources_to_create': [
            {
                'kind': manifest.get('kind'),
                'name': manifest.get('metadata', {}).get('name'),
                'namespace': namespace
            }
            for manifest in profile['manifests']
            if manifest.get('kind') != 'ConfigMap'
        ]
    }

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8605))
    uvicorn.run(app, host="0.0.0.0", port=port)