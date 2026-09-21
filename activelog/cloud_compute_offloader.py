#!/usr/bin/env python3
"""
Cloud Compute Offloader for ActiveLog
Enables low-end and old devices to offload intensive computations to cloud services
"""

import os
import sys
import json
import asyncio
import aiohttp
import hashlib
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import base64
import gzip
import pickle

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CloudProvider:
    name: str
    endpoint: str
    api_key: str
    region: str
    capabilities: List[str]
    cost_per_hour: float
    max_concurrent_tasks: int
    latency_ms: float

@dataclass 
class OffloadTask:
    task_id: str
    task_type: str
    priority: str
    input_data: Dict[str, Any]
    device_fallback: bool
    max_wait_time: int
    created_at: datetime
    estimated_cost: float

class CloudComputeOffloader:
    def __init__(self):
        self.cloud_providers = self._load_cloud_providers()
        self.task_queue = asyncio.Queue()
        self.active_tasks = {}
        self.results_cache = {}
        self.device_capabilities = self._assess_device_capabilities()
        self.offload_threshold = self._determine_offload_threshold()
        self.stats = {
            'tasks_offloaded': 0,
            'tasks_local': 0,
            'cloud_compute_time': 0,
            'local_compute_time': 0,
            'cost_saved': 0,
            'bandwidth_used': 0
        }
        
        logger.info(f"Cloud offloader initialized for {self.device_capabilities['tier']} device")
    
    def _load_cloud_providers(self) -> List[CloudProvider]:
        """Load cloud provider configurations"""
        config_file = Path("cloud_providers.json")
        
        if config_file.exists():
            with open(config_file) as f:
                provider_configs = json.load(f)
        else:
            # Create default cloud provider configurations
            provider_configs = {
                "aws_lambda": {
                    "endpoint": "https://lambda.us-east-1.amazonaws.com/2015-03-31/functions",
                    "api_key": "YOUR_AWS_KEY",
                    "region": "us-east-1", 
                    "capabilities": ["ml_inference", "data_processing", "image_processing", "nlp"],
                    "cost_per_hour": 0.0000166,
                    "max_concurrent_tasks": 1000,
                    "latency_ms": 150
                },
                "google_cloud_run": {
                    "endpoint": "https://run.googleapis.com/apis/serving.knative.dev/v1",
                    "api_key": "YOUR_GOOGLE_KEY",
                    "region": "us-central1",
                    "capabilities": ["ml_inference", "data_processing", "vision_api", "speech_api"],
                    "cost_per_hour": 0.000024,
                    "max_concurrent_tasks": 200,
                    "latency_ms": 200
                },
                "azure_functions": {
                    "endpoint": "https://management.azure.com/subscriptions",
                    "api_key": "YOUR_AZURE_KEY", 
                    "region": "eastus",
                    "capabilities": ["ml_inference", "cognitive_services", "data_processing"],
                    "cost_per_hour": 0.000016,
                    "max_concurrent_tasks": 500,
                    "latency_ms": 180
                },
                "edge_compute": {
                    "endpoint": "https://edge-compute.activelog.ai/api/v1",
                    "api_key": "EDGE_COMPUTE_KEY",
                    "region": "global",
                    "capabilities": ["lightweight_ml", "data_processing", "caching"],
                    "cost_per_hour": 0.00001,
                    "max_concurrent_tasks": 50,
                    "latency_ms": 50
                }
            }
            
            with open(config_file, 'w') as f:
                json.dump(provider_configs, f, indent=2)
        
        providers = []
        for name, config in provider_configs.items():
            providers.append(CloudProvider(
                name=name,
                endpoint=config["endpoint"],
                api_key=config["api_key"],
                region=config["region"],
                capabilities=config["capabilities"],
                cost_per_hour=config["cost_per_hour"],
                max_concurrent_tasks=config["max_concurrent_tasks"],
                latency_ms=config["latency_ms"]
            ))
        
        return providers
    
    def _assess_device_capabilities(self) -> Dict[str, Any]:
        """Assess current device capabilities"""
        import psutil
        import platform
        
        cpu_count = psutil.cpu_count(logical=False)
        memory_gb = psutil.virtual_memory().total / (1024**3)
        
        # Determine device tier
        if cpu_count >= 4 and memory_gb >= 8:
            tier = "high"
            offload_threshold = 0.3  # Offload 30% of intensive tasks
        elif cpu_count >= 2 and memory_gb >= 4:
            tier = "medium" 
            offload_threshold = 0.6  # Offload 60% of intensive tasks
        else:
            tier = "low"
            offload_threshold = 0.9  # Offload 90% of intensive tasks
        
        return {
            "tier": tier,
            "cpu_cores": cpu_count,
            "memory_gb": memory_gb,
            "platform": platform.system().lower(),
            "architecture": platform.machine().lower(),
            "offload_threshold": offload_threshold,
            "can_handle_ml": memory_gb >= 4 and cpu_count >= 2,
            "can_handle_image_processing": memory_gb >= 2,
            "can_handle_data_processing": memory_gb >= 1
        }
    
    def _determine_offload_threshold(self) -> float:
        """Determine when to offload tasks based on device capabilities"""
        return self.device_capabilities["offload_threshold"]
    
    def should_offload_task(self, task_type: str, data_size_mb: float = 0) -> bool:
        """Determine if a task should be offloaded to cloud"""
        
        # Always offload for very low-end devices
        if self.device_capabilities["tier"] == "low":
            return True
        
        # Task-specific decisions
        task_offload_rules = {
            "ml_inference": not self.device_capabilities["can_handle_ml"],
            "image_processing": data_size_mb > 10 or not self.device_capabilities["can_handle_image_processing"],
            "data_processing": data_size_mb > 50 or not self.device_capabilities["can_handle_data_processing"],
            "nlp_processing": True,  # Always offload NLP for better accuracy
            "video_processing": True,  # Always offload video processing
            "large_dataset_analysis": data_size_mb > 100,
            "real_time_ai": self.device_capabilities["tier"] in ["low", "medium"]
        }
        
        return task_offload_rules.get(task_type, False)
    
    async def select_optimal_provider(self, task_type: str, priority: str = "medium") -> Optional[CloudProvider]:
        """Select the best cloud provider for a specific task"""
        suitable_providers = [
            p for p in self.cloud_providers 
            if task_type in p.capabilities and p.api_key != "YOUR_" + p.name.upper() + "_KEY"
        ]
        
        if not suitable_providers:
            return None
        
        # Score providers based on latency, cost, and availability
        scored_providers = []
        for provider in suitable_providers:
            # Check availability (simplified)
            availability_score = 1.0  # Assume available for now
            
            # Calculate score (lower is better)
            latency_score = provider.latency_ms / 1000  # Normalize to seconds
            cost_score = provider.cost_per_hour * 100  # Normalize
            
            if priority == "high":
                total_score = latency_score * 0.7 + cost_score * 0.3
            elif priority == "low":
                total_score = latency_score * 0.3 + cost_score * 0.7
            else:  # medium
                total_score = latency_score * 0.5 + cost_score * 0.5
            
            scored_providers.append((provider, total_score))
        
        # Return provider with lowest (best) score
        scored_providers.sort(key=lambda x: x[1])
        return scored_providers[0][0]
    
    async def create_offload_task(self, task_type: str, input_data: Dict[str, Any], 
                                 priority: str = "medium", device_fallback: bool = True) -> str:
        """Create a new offload task"""
        task_id = hashlib.sha256(
            (task_type + str(time.time()) + str(input_data)).encode()
        ).hexdigest()[:16]
        
        task = OffloadTask(
            task_id=task_id,
            task_type=task_type,
            priority=priority,
            input_data=input_data,
            device_fallback=device_fallback,
            max_wait_time=300,  # 5 minutes max
            created_at=datetime.now(),
            estimated_cost=0.0
        )
        
        await self.task_queue.put(task)
        logger.info(f"Created offload task {task_id} for {task_type}")
        return task_id
    
    async def compress_data(self, data: Any) -> bytes:
        """Compress data for efficient transmission"""
        serialized = pickle.dumps(data)
        compressed = gzip.compress(serialized)
        return base64.b64encode(compressed)
    
    async def decompress_data(self, compressed_data: bytes) -> Any:
        """Decompress received data"""
        decoded = base64.b64decode(compressed_data)
        decompressed = gzip.decompress(decoded)
        return pickle.loads(decompressed)
    
    async def execute_cloud_task(self, task: OffloadTask, provider: CloudProvider) -> Optional[Dict[str, Any]]:
        """Execute a task on a cloud provider"""
        start_time = time.time()
        
        try:
            # Compress input data
            compressed_input = await self.compress_data(task.input_data)
            
            # Prepare request
            request_data = {
                "task_id": task.task_id,
                "task_type": task.task_type,
                "input_data": compressed_input.decode('utf-8'),
                "priority": task.priority,
                "device_info": {
                    "tier": self.device_capabilities["tier"],
                    "capabilities": self.device_capabilities
                }
            }
            
            headers = {
                "Authorization": f"Bearer {provider.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "ActiveLog-CloudOffloader/1.0"
            }
            
            # Execute cloud request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{provider.endpoint}/execute",
                    json=request_data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=task.max_wait_time)
                ) as response:
                    
                    if response.status == 200:
                        result_data = await response.json()
                        
                        # Decompress result if needed
                        if "compressed_result" in result_data:
                            result = await self.decompress_data(result_data["compressed_result"].encode())
                        else:
                            result = result_data["result"]
                        
                        execution_time = time.time() - start_time
                        
                        # Update statistics
                        self.stats["tasks_offloaded"] += 1
                        self.stats["cloud_compute_time"] += execution_time
                        self.stats["bandwidth_used"] += len(compressed_input) + len(await response.read())
                        
                        # Cache result for potential reuse
                        cache_key = hashlib.sha256(str(task.input_data).encode()).hexdigest()
                        self.results_cache[cache_key] = {
                            "result": result,
                            "timestamp": datetime.now(),
                            "provider": provider.name,
                            "execution_time": execution_time
                        }
                        
                        logger.info(f"Cloud task {task.task_id} completed in {execution_time:.2f}s via {provider.name}")
                        
                        return {
                            "success": True,
                            "result": result,
                            "execution_time": execution_time,
                            "provider": provider.name,
                            "cost": provider.cost_per_hour * (execution_time / 3600)
                        }
                    
                    else:
                        logger.error(f"Cloud task {task.task_id} failed with status {response.status}")
                        return None
        
        except asyncio.TimeoutError:
            logger.warning(f"Cloud task {task.task_id} timed out on {provider.name}")
            return None
        except Exception as e:
            logger.error(f"Cloud task {task.task_id} error on {provider.name}: {e}")
            return None
    
    async def execute_local_fallback(self, task: OffloadTask) -> Optional[Dict[str, Any]]:
        """Execute task locally as fallback"""
        start_time = time.time()
        
        logger.info(f"Executing task {task.task_id} locally as fallback")
        
        try:
            # Simplified local execution (placeholder implementations)
            if task.task_type == "ml_inference":
                result = await self._local_ml_inference(task.input_data)
            elif task.task_type == "image_processing":
                result = await self._local_image_processing(task.input_data)
            elif task.task_type == "data_processing":
                result = await self._local_data_processing(task.input_data)
            else:
                logger.warning(f"No local fallback for task type {task.task_type}")
                return None
            
            execution_time = time.time() - start_time
            
            # Update statistics
            self.stats["tasks_local"] += 1
            self.stats["local_compute_time"] += execution_time
            
            logger.info(f"Local task {task.task_id} completed in {execution_time:.2f}s")
            
            return {
                "success": True,
                "result": result,
                "execution_time": execution_time,
                "provider": "local",
                "cost": 0.0
            }
        
        except Exception as e:
            logger.error(f"Local fallback failed for task {task.task_id}: {e}")
            return None
    
    async def _local_ml_inference(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simplified local ML inference"""
        # Placeholder for lightweight local ML
        await asyncio.sleep(2)  # Simulate processing time
        return {
            "prediction": "local_prediction",
            "confidence": 0.85,
            "model_used": "lightweight_local"
        }
    
    async def _local_image_processing(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simplified local image processing"""
        # Placeholder for basic image processing
        await asyncio.sleep(1)  # Simulate processing time
        return {
            "processed": True,
            "transformations": ["resize", "normalize"],
            "output_size": "optimized_for_device"
        }
    
    async def _local_data_processing(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simplified local data processing"""
        # Placeholder for basic data processing
        await asyncio.sleep(0.5)  # Simulate processing time
        return {
            "processed_records": len(input_data.get("data", [])),
            "summary": "local_processing_complete"
        }
    
    async def process_task_queue(self):
        """Process offload tasks from queue"""
        while True:
            try:
                # Get task from queue
                task = await self.task_queue.get()
                self.active_tasks[task.task_id] = task
                
                # Check cache first
                cache_key = hashlib.sha256(str(task.input_data).encode()).hexdigest()
                if cache_key in self.results_cache:
                    cached_result = self.results_cache[cache_key]
                    if (datetime.now() - cached_result["timestamp"]).seconds < 3600:  # 1 hour cache
                        logger.info(f"Using cached result for task {task.task_id}")
                        continue
                
                # Select provider
                provider = await self.select_optimal_provider(task.task_type, task.priority)
                
                result = None
                if provider:
                    # Try cloud execution
                    result = await self.execute_cloud_task(task, provider)
                
                # Fallback to local if cloud failed and fallback enabled
                if not result and task.device_fallback:
                    result = await self.execute_local_fallback(task)
                
                # Store result
                if result:
                    self.active_tasks[task.task_id] = result
                else:
                    logger.error(f"Task {task.task_id} failed completely")
                
                self.task_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing task queue: {e}")
                await asyncio.sleep(1)
    
    def create_cloud_ready_services(self) -> Dict[str, str]:
        """Create cloud-ready service configurations"""
        
        # Thin client configuration for low-end devices
        thin_client_config = {
            "mode": "thin_client",
            "local_services": ["auth", "api-gateway"],  # Only essential services
            "cloud_services": ["ai-orchestrator", "metadata", "backup", "analytics"],
            "offload_rules": {
                "ml_tasks": "always",
                "large_file_processing": "always", 
                "data_analytics": "if_data_size > 10MB",
                "image_processing": "if_resolution > 1080p",
                "video_processing": "always"
            },
            "cache_strategy": "aggressive",
            "bandwidth_optimization": True,
            "compression": "high"
        }
        
        # Progressive Web App configuration
        pwa_config = {
            "service_worker": {
                "cache_strategy": "cache_first",
                "offline_fallbacks": True,
                "background_sync": True,
                "push_notifications": False  # Disabled for battery
            },
            "manifest": {
                "display": "standalone",
                "start_url": "/",
                "theme_color": "#2196F3",
                "background_color": "#ffffff",
                "icons": [
                    {"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
                    {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"}
                ]
            },
            "performance": {
                "lazy_loading": True,
                "code_splitting": True,
                "tree_shaking": True,
                "compression": "gzip"
            }
        }
        
        # Edge computing configuration
        edge_config = {
            "edge_nodes": [
                "https://edge-us-east.activelog.ai",
                "https://edge-eu-west.activelog.ai",
                "https://edge-asia-pacific.activelog.ai"
            ],
            "load_balancing": "latency_based",
            "failover": "automatic",
            "data_locality": True,
            "privacy_compliance": "gdpr_ccpa_compliant"
        }
        
        return {
            "thin_client.json": json.dumps(thin_client_config, indent=2),
            "pwa_config.json": json.dumps(pwa_config, indent=2),
            "edge_config.json": json.dumps(edge_config, indent=2)
        }
    
    def generate_deployment_scripts(self) -> Dict[str, str]:
        """Generate deployment scripts for different scenarios"""
        
        # Docker Compose for cloud deployment
        docker_compose = """version: '3.8'

services:
  activelog-compute:
    image: activelog/compute:latest
    environment:
      - CLOUD_MODE=true
      - DEVICE_TIER=cloud
    ports:
      - "8000-8010:8000-8010"
    resources:
      limits:
        cpus: '2.0'
        memory: 4G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
  
  activelog-thin-client:
    image: activelog/thin-client:latest
    environment:
      - CLOUD_ENDPOINT=http://activelog-compute:8000
      - DEVICE_TIER=thin
    ports:
      - "3000:3000"
    depends_on:
      - activelog-compute
    resources:
      limits:
        cpus: '0.5'
        memory: 512M
"""
        
        # Kubernetes deployment
        k8s_deployment = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: activelog-cloud
spec:
  replicas: 3
  selector:
    matchLabels:
      app: activelog-cloud
  template:
    metadata:
      labels:
        app: activelog-cloud
    spec:
      containers:
      - name: activelog
        image: activelog/cloud:latest
        ports:
        - containerPort: 8000
        env:
        - name: CLOUD_MODE
          value: "true"
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: activelog-service
spec:
  selector:
    app: activelog-cloud
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: LoadBalancer
"""
        
        # AWS Lambda deployment script
        lambda_deploy = """#!/bin/bash
# Deploy ActiveLog to AWS Lambda for serverless compute offloading

# Package application
zip -r activelog-lambda.zip . -x "*.git*" "node_modules/*" "__pycache__/*" "*.pyc"

# Create Lambda function
aws lambda create-function \\
    --function-name activelog-compute-offloader \\
    --runtime python3.11 \\
    --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-execution-role \\
    --handler lambda_handler.handler \\
    --zip-file fileb://activelog-lambda.zip \\
    --timeout 300 \\
    --memory-size 1024 \\
    --environment Variables='{
        "CLOUD_MODE":"true",
        "DEVICE_OFFLOAD":"true"
    }'

# Create API Gateway
aws apigateway create-rest-api \\
    --name activelog-compute-api \\
    --description "ActiveLog Compute Offloading API"

echo "Deployment complete. Update your cloud_providers.json with the endpoint."
"""
        
        return {
            "docker-compose.cloud.yml": docker_compose,
            "k8s-deployment.yaml": k8s_deployment, 
            "deploy-lambda.sh": lambda_deploy
        }
    
    async def create_optimization_suite(self):
        """Create complete optimization suite for cloud compute offloading"""
        
        # Create configurations
        configs = self.create_cloud_ready_services()
        for filename, content in configs.items():
            with open(filename, 'w') as f:
                f.write(content)
        
        # Create deployment scripts
        deploy_scripts = self.generate_deployment_scripts()
        deploy_dir = Path("deployment")
        deploy_dir.mkdir(exist_ok=True)
        
        for filename, content in deploy_scripts.items():
            script_file = deploy_dir / filename
            with open(script_file, 'w') as f:
                f.write(content)
            
            if filename.endswith('.sh'):
                os.chmod(script_file, 0o755)
        
        # Create cloud offloader configuration
        offloader_config = {
            "device_assessment": self.device_capabilities,
            "cloud_providers": [asdict(p) for p in self.cloud_providers],
            "offload_rules": {
                "automatic_offloading": True,
                "cost_limit_per_hour": 1.0,  # $1/hour max
                "bandwidth_limit_mb": 1000,  # 1GB/hour max
                "latency_threshold_ms": 2000,
                "fallback_enabled": True
            },
            "optimization_settings": {
                "compression_enabled": True,
                "caching_enabled": True,
                "batch_processing": True,
                "priority_queue": True
            }
        }
        
        with open("cloud_offloader_config.json", 'w') as f:
            json.dump(offloader_config, f, indent=2)
        
        # Create startup script for thin client mode
        thin_client_script = f"""#!/bin/bash
# ActiveLog Thin Client Startup Script
# Optimized for {self.device_capabilities['tier']} devices

echo "🌐 Starting ActiveLog Thin Client Mode..."
echo "Device tier: {self.device_capabilities['tier']}"
echo "Offload threshold: {self.offload_threshold:.0%}"

# Set environment variables
export ACTIVELOG_MODE="thin_client"
export CLOUD_OFFLOAD_ENABLED="true"
export DEVICE_TIER="{self.device_capabilities['tier']}"

# Start only essential services locally
echo "Starting essential local services..."
cd services/auth && python3 main.py &
AUTH_PID=$!

cd ../../services/api-gateway && python3 main.py &
GATEWAY_PID=$!

# Start cloud offloader
echo "Starting cloud compute offloader..."
python3 cloud_compute_offloader.py &
OFFLOADER_PID=$!

# Start lightweight frontend
echo "Starting optimized frontend..."
cd frontend && npm run build:thin && npm run serve:thin &
FRONTEND_PID=$!

echo "Essential services started:"
echo "- Auth Service (PID: $AUTH_PID)"  
echo "- API Gateway (PID: $GATEWAY_PID)"
echo "- Cloud Offloader (PID: $OFFLOADER_PID)"
echo "- Thin Frontend (PID: $FRONTEND_PID)"

echo ""
echo "🎉 ActiveLog Thin Client ready!"
echo "Local interface: http://localhost:3000"
echo "Cloud compute: Enabled"
echo "Estimated cost: $0.01-0.10/hour depending on usage"
"""
        
        with open("start_thin_client.sh", 'w') as f:
            f.write(thin_client_script)
        os.chmod("start_thin_client.sh", 0o755)
        
        logger.info("✅ Cloud compute offloading suite created successfully")
    
    def print_optimization_summary(self):
        """Print summary of cloud optimizations"""
        print("\n🌐 Cloud Compute Offloading Summary")
        print("=" * 60)
        print(f"Device Tier: {self.device_capabilities['tier']}")
        print(f"Offload Threshold: {self.offload_threshold:.0%}")
        print(f"Available Providers: {len(self.cloud_providers)}")
        print()
        
        print("📋 Offloading Strategy:")
        if self.device_capabilities["tier"] == "low":
            print("• Offload 90% of intensive tasks to cloud")
            print("• Run only auth and API gateway locally")
            print("• Use aggressive caching and compression")
            print("• Estimated cost: $0.05-0.20/hour")
        elif self.device_capabilities["tier"] == "medium":
            print("• Offload 60% of intensive tasks to cloud")
            print("• Run core services locally")
            print("• Balance between local and cloud compute")
            print("• Estimated cost: $0.02-0.10/hour")
        else:
            print("• Offload 30% of intensive tasks to cloud")
            print("• Run most services locally")
            print("• Use cloud for specialized tasks only")
            print("• Estimated cost: $0.01-0.05/hour")
        
        print(f"\n🛠️ Available Configurations:")
        print("• thin_client.json - Minimal local footprint")
        print("• pwa_config.json - Progressive web app setup")
        print("• edge_config.json - Edge computing configuration")
        print("• deployment/ - Cloud deployment scripts")
        
        print(f"\n🚀 Quick Start:")
        print("1. Configure cloud providers in cloud_providers.json")
        print("2. Run: ./start_thin_client.sh")
        print("3. Access via http://localhost:3000")
        print("4. Monitor usage and costs in dashboard")

async def main():
    """Main cloud offloader setup"""
    offloader = CloudComputeOffloader()
    
    # Create optimization suite
    await offloader.create_optimization_suite()
    
    # Print summary  
    offloader.print_optimization_summary()
    
    # Start task processor
    print(f"\n🔄 Starting cloud compute task processor...")
    print("Press Ctrl+C to stop")
    
    try:
        await offloader.process_task_queue()
    except KeyboardInterrupt:
        print("\n👋 Cloud compute offloader stopped")

if __name__ == "__main__":
    asyncio.run(main())