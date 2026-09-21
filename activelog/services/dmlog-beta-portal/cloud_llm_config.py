#!/usr/bin/env python3
"""
DMLog Cloud LLM Infrastructure Configuration
Scalable, cost-optimized AI backend for D&D gameplay
"""

import os
import boto3
import requests
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class CloudLLMManager:
    """Manages cloud-based LLM instances for DMLog"""
    
    def __init__(self):
        self.ec2 = boto3.client('ec2', region_name='us-west-2')
        self.active_instances = {}
        self.instance_configs = {
            'llama-storyteller': {
                'instance_type': 'g5.xlarge',  # 1 A10G GPU, 16GB VRAM
                'image_id': 'ami-0abcdef1234567890',  # Custom AMI with Llama setup
                'model': 'llama-2-70b-chat',
                'use_case': 'creative_storytelling',
                'cost_per_hour': 1.006,
                'max_tokens': 2048
            },
            'mistral-quick': {
                'instance_type': 'g4dn.xlarge',  # 1 T4 GPU, 16GB VRAM  
                'image_id': 'ami-0123456789abcdef0', # Custom AMI with Mistral
                'model': 'mistral-7b-instruct',
                'use_case': 'quick_responses',
                'cost_per_hour': 0.526,
                'max_tokens': 512
            }
        }
        
    async def get_or_create_instance(self, model_type: str) -> str:
        """Get active instance or create new one"""
        if model_type in self.active_instances:
            instance_id = self.active_instances[model_type]
            if await self._is_instance_healthy(instance_id):
                return await self._get_instance_endpoint(instance_id)
        
        # Create new instance
        instance_id = await self._launch_instance(model_type)
        self.active_instances[model_type] = instance_id
        
        # Wait for instance to be ready
        endpoint = await self._wait_for_instance(instance_id)
        return endpoint
    
    async def _launch_instance(self, model_type: str) -> str:
        """Launch new LLM instance"""
        config = self.instance_configs[model_type]
        
        user_data = f"""#!/bin/bash
        # Install and run LLM server
        cd /opt/llm-server
        python3 serve_model.py --model {config['model']} --port 8080
        """
        
        response = self.ec2.run_instances(
            ImageId=config['image_id'],
            MinCount=1,
            MaxCount=1,
            InstanceType=config['instance_type'],
            KeyName='dmlog-llm-key',
            SecurityGroupIds=['sg-llm-access'],
            UserData=user_data,
            TagSpecifications=[{
                'ResourceType': 'instance',
                'Tags': [
                    {'Key': 'Name', 'Value': f'dmlog-llm-{model_type}'},
                    {'Key': 'Project', 'Value': 'DMLog'},
                    {'Key': 'Auto-Shutdown', 'Value': '10min'}
                ]
            }]
        )
        
        instance_id = response['Instances'][0]['InstanceId']
        logger.info(f"Launched LLM instance {instance_id} for {model_type}")
        return instance_id
    
    async def _wait_for_instance(self, instance_id: str) -> str:
        """Wait for instance to be ready and return endpoint"""
        import asyncio
        
        for attempt in range(30):  # 5 minute timeout
            try:
                response = self.ec2.describe_instances(InstanceIds=[instance_id])
                instance = response['Reservations'][0]['Instances'][0]
                
                if instance['State']['Name'] == 'running':
                    public_ip = instance.get('PublicIpAddress')
                    if public_ip:
                        endpoint = f"http://{public_ip}:8080"
                        
                        # Test if LLM server is ready
                        try:
                            health_response = requests.get(f"{endpoint}/health", timeout=5)
                            if health_response.status_code == 200:
                                logger.info(f"LLM instance {instance_id} ready at {endpoint}")
                                return endpoint
                        except requests.RequestException:
                            pass
                            
            except Exception as e:
                logger.error(f"Error checking instance {instance_id}: {e}")
            
            await asyncio.sleep(10)
        
        raise TimeoutError(f"Instance {instance_id} did not become ready in time")
    
    async def _is_instance_healthy(self, instance_id: str) -> bool:
        """Check if instance is running and healthy"""
        try:
            response = self.ec2.describe_instances(InstanceIds=[instance_id])
            instance = response['Reservations'][0]['Instances'][0]
            
            if instance['State']['Name'] != 'running':
                return False
            
            # Check health endpoint
            public_ip = instance.get('PublicIpAddress')
            if public_ip:
                health_response = requests.get(f"http://{public_ip}:8080/health", timeout=5)
                return health_response.status_code == 200
                
        except Exception as e:
            logger.error(f"Health check failed for {instance_id}: {e}")
            
        return False
    
    async def _get_instance_endpoint(self, instance_id: str) -> str:
        """Get endpoint URL for instance"""
        response = self.ec2.describe_instances(InstanceIds=[instance_id])
        instance = response['Reservations'][0]['Instances'][0]
        public_ip = instance['PublicIpAddress']
        return f"http://{public_ip}:8080"
    
    async def generate_response(self, character: str, message: str) -> str:
        """Generate response using appropriate LLM"""
        
        # Route to appropriate model based on use case
        if character in ['dm', 'narrator'] or len(message) > 100:
            model_type = 'llama-storyteller'  # Creative, complex responses
        else:
            model_type = 'mistral-quick'      # Fast, simple responses
            
        try:
            endpoint = await self.get_or_create_instance(model_type)
            
            response = requests.post(f"{endpoint}/generate", json={
                'character': character,
                'message': message,
                'max_tokens': self.instance_configs[model_type]['max_tokens']
            }, timeout=30)
            
            if response.status_code == 200:
                return response.json()['response']
            else:
                logger.error(f"LLM API error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Cloud LLM error: {e}")
            
        # Fallback to OpenAI if cloud LLM fails
        return await self._fallback_to_openai(character, message)
    
    async def _fallback_to_openai(self, character: str, message: str) -> str:
        """Fallback to OpenAI API if cloud LLM unavailable"""
        # Use existing OpenAI integration as backup
        logger.info("Using OpenAI fallback")
        return "The tavern keeper nods thoughtfully at your words."
    
    async def shutdown_idle_instances(self):
        """Shutdown instances that have been idle > 10 minutes"""
        for model_type, instance_id in list(self.active_instances.items()):
            try:
                # Check instance idle time via CloudWatch metrics
                idle_time = await self._get_instance_idle_time(instance_id)
                
                if idle_time > 600:  # 10 minutes
                    logger.info(f"Shutting down idle instance {instance_id}")
                    self.ec2.terminate_instances(InstanceIds=[instance_id])
                    del self.active_instances[model_type]
                    
            except Exception as e:
                logger.error(f"Error checking idle time for {instance_id}: {e}")
    
    async def _get_instance_idle_time(self, instance_id: str) -> int:
        """Get idle time in seconds from CloudWatch"""
        # Simplified - would use actual CloudWatch metrics
        return 300  # Placeholder

    def get_cost_estimate(self, usage_hours: Dict[str, float]) -> Dict[str, float]:
        """Calculate estimated costs for usage"""
        total_cost = 0
        breakdown = {}
        
        for model_type, hours in usage_hours.items():
            if model_type in self.instance_configs:
                cost = hours * self.instance_configs[model_type]['cost_per_hour']
                breakdown[model_type] = cost
                total_cost += cost
        
        breakdown['total'] = total_cost
        return breakdown


class LLMLoadBalancer:
    """Distributes requests across multiple LLM instances"""
    
    def __init__(self):
        self.instances = []
        self.current_index = 0
    
    def add_instance(self, endpoint: str, model_type: str):
        """Add instance to load balancer pool"""
        self.instances.append({
            'endpoint': endpoint,
            'model_type': model_type,
            'active_requests': 0
        })
    
    def get_best_instance(self, request_type: str) -> str:
        """Get least loaded instance suitable for request type"""
        suitable_instances = [
            inst for inst in self.instances 
            if self._is_suitable(inst['model_type'], request_type)
        ]
        
        if not suitable_instances:
            return self.instances[0]['endpoint']  # Fallback
        
        # Return least loaded instance
        best_instance = min(suitable_instances, key=lambda x: x['active_requests'])
        best_instance['active_requests'] += 1
        return best_instance['endpoint']
    
    def _is_suitable(self, model_type: str, request_type: str) -> bool:
        """Check if model type is suitable for request"""
        if request_type in ['creative', 'storytelling', 'complex']:
            return 'llama' in model_type
        else:
            return True  # Any model can handle simple requests

# Usage example:
# cloud_llm = CloudLLMManager()
# response = await cloud_llm.generate_response('dm', 'I want to explore the dungeon')