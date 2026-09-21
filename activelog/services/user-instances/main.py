"""
User Instances Service - FastAPI service for managing user-isolated EC2 instances
Port: 8476
"""
from fastapi import FastAPI, HTTPException, Depends, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import asyncio
import logging
import os
from datetime import datetime
import uvicorn

from core.instance_manager import UserInstanceManager
from models.instance_models import (
    CreateInstanceRequest, 
    InstanceResponse,
    InstanceStatus,
    UserTier
)
from security.auth_validator import validate_user_token
from monitoring.instance_monitor import InstanceMonitor
from billing.instance_billing import InstanceBilling

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="ActiveLog User Instances Service",
    description="Manages isolated EC2 instances for ActiveLog users",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Initialize services
instance_manager = UserInstanceManager()
instance_monitor = InstanceMonitor()
instance_billing = InstanceBilling()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict[str, Any]:
    """Validate user token and return user information"""
    try:
        user_info = await validate_user_token(credentials.credentials)
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        return user_info
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "user-instances",
        "port": 8476,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/instances", response_model=InstanceResponse)
async def create_user_instance(
    request: CreateInstanceRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a new isolated EC2 instance for the authenticated user
    """
    try:
        user_id = user['user_id']
        tier = request.tier.value
        
        # Validate user can create instance
        if user.get('tier_level', 0) < UserTier[tier].value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User tier insufficient for {tier} instance"
            )
        
        # Check if user already has an active instance
        existing_instance = instance_manager.get_user_instance_status(user_id)
        if existing_instance and existing_instance['state'] in ['pending', 'running']:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already has an active instance"
            )
        
        # Create the instance
        logger.info(f"Creating {tier} instance for user {user_id}")
        instance_data = instance_manager.create_user_instance(user_id, tier)
        
        # Start monitoring
        await instance_monitor.start_monitoring(user_id, instance_data['instance_id'])
        
        # Initialize billing
        await instance_billing.start_billing(user_id, instance_data['instance_id'], tier)
        
        return InstanceResponse(
            instance_id=instance_data['instance_id'],
            user_id=user_id,
            tier=tier,
            status="provisioning",
            vpc_id=instance_data['network']['vpc_id'],
            subnet_id=instance_data['network']['subnet_id'],
            security_group_id=instance_data['config'].security_group_id,
            encryption_key_id=instance_data['config'].encryption_key_id,
            created_at=datetime.utcnow(),
            estimated_monthly_cost=instance_billing.calculate_monthly_cost(tier)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create instance for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create instance"
        )

@app.get("/instances/status", response_model=InstanceStatus)
async def get_instance_status(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get the current status of the user's instance
    """
    try:
        user_id = user['user_id']
        
        instance_status = instance_manager.get_user_instance_status(user_id)
        if not instance_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No instance found for user"
            )
        
        # Get additional monitoring data
        monitoring_data = await instance_monitor.get_instance_metrics(
            instance_status['instance_id']
        )
        
        # Get billing information
        billing_data = await instance_billing.get_current_usage(user_id)
        
        return InstanceStatus(
            instance_id=instance_status['instance_id'],
            state=instance_status['state'],
            public_ip=instance_status.get('public_ip'),
            private_ip=instance_status['private_ip'],
            instance_type=instance_status['instance_type'],
            launch_time=instance_status['launch_time'],
            cpu_utilization=monitoring_data.get('cpu_utilization', 0),
            memory_utilization=monitoring_data.get('memory_utilization', 0),
            network_in=monitoring_data.get('network_in', 0),
            network_out=monitoring_data.get('network_out', 0),
            current_cost=billing_data.get('current_cost', 0.0),
            monthly_estimate=billing_data.get('monthly_estimate', 0.0)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get instance status for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get instance status"
        )

@app.post("/instances/stop")
async def stop_user_instance(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Stop the user's instance (preserves data)
    """
    try:
        user_id = user['user_id']
        
        instance_status = instance_manager.get_user_instance_status(user_id)
        if not instance_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No instance found for user"
            )
        
        if instance_status['state'] != 'running':
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot stop instance in {instance_status['state']} state"
            )
        
        # Stop the instance
        response = instance_manager.ec2_client.stop_instances(
            InstanceIds=[instance_status['instance_id']]
        )
        
        # Update billing
        await instance_billing.pause_billing(user_id)
        
        return {
            "message": "Instance stop initiated",
            "instance_id": instance_status['instance_id'],
            "previous_state": "running",
            "new_state": "stopping"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop instance for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop instance"
        )

@app.post("/instances/start")
async def start_user_instance(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Start the user's stopped instance
    """
    try:
        user_id = user['user_id']
        
        instance_status = instance_manager.get_user_instance_status(user_id)
        if not instance_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No instance found for user"
            )
        
        if instance_status['state'] != 'stopped':
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot start instance in {instance_status['state']} state"
            )
        
        # Start the instance
        response = instance_manager.ec2_client.start_instances(
            InstanceIds=[instance_status['instance_id']]
        )
        
        # Resume billing
        await instance_billing.resume_billing(user_id)
        
        return {
            "message": "Instance start initiated",
            "instance_id": instance_status['instance_id'],
            "previous_state": "stopped",
            "new_state": "pending"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start instance for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start instance"
        )

@app.delete("/instances")
async def terminate_user_instance(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Terminate the user's instance (destroys all data)
    """
    try:
        user_id = user['user_id']
        
        # Terminate instance and clean up resources
        success = instance_manager.terminate_user_instance(user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to terminate instance"
            )
        
        # Stop monitoring and billing
        await instance_monitor.stop_monitoring(user_id)
        await instance_billing.stop_billing(user_id)
        
        return {
            "message": "Instance termination initiated",
            "user_id": user_id,
            "warning": "All data will be permanently deleted"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to terminate instance for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to terminate instance"
        )

@app.get("/instances/billing")
async def get_billing_info(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get detailed billing information for the user's instance
    """
    try:
        user_id = user['user_id']
        
        billing_info = await instance_billing.get_detailed_billing(user_id)
        if not billing_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No billing information found"
            )
        
        return billing_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get billing info for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get billing information"
        )

@app.get("/admin/instances")
async def list_all_instances(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Admin endpoint to list all user instances (requires admin privileges)
    """
    try:
        if not user.get('is_admin', False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        
        # Get all ActiveLog instances
        response = instance_manager.ec2_client.describe_instances(
            Filters=[
                {'Name': 'tag:ActiveLogRole', 'Values': ['orchestrator_only']},
                {'Name': 'instance-state-name', 'Values': ['pending', 'running', 'stopping', 'stopped']}
            ]
        )
        
        instances = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
                instances.append({
                    'instance_id': instance['InstanceId'],
                    'user_id': tags.get('DataOwner'),
                    'tier': tags.get('Tier'),
                    'state': instance['State']['Name'],
                    'instance_type': instance['InstanceType'],
                    'launch_time': instance['LaunchTime'],
                    'public_ip': instance.get('PublicIpAddress'),
                    'private_ip': instance['PrivateIpAddress']
                })
        
        return {
            "total_instances": len(instances),
            "instances": instances
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list instances: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list instances"
        )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8476,
        log_level="info",
        reload=False
    )