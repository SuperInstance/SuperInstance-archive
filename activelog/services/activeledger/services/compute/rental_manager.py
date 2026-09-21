"""
Compute Rental System
Manages EC2 instance rentals by day/month with automatic billing
"""

import asyncio
import boto3
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from ...models.database import (
    User, ComputeInstance, Transaction, ComputeInstanceType, ComputeInstanceStatus,
    TransactionType, TransactionStatus
)
from ...config.settings import settings
from ..credits.cc_system import ComputeCreditSystem

logger = logging.getLogger(__name__)

class ComputeRentalManager:
    """Manages compute instance rentals with automatic billing"""
    
    def __init__(self, db: Session):
        self.db = db
        self.cc_system = ComputeCreditSystem(db)
        
        # AWS EC2 client (would need proper credentials in production)
        self.ec2_client = None  # boto3.client('ec2') in production
        
        # Instance pricing (daily rates in CC)
        self.instance_pricing = {
            ComputeInstanceType.T3_MICRO: {
                "hourly_cc": Decimal("2.08"),   # ~$0.0208/hour
                "daily_cc": Decimal("50"),      # ~$0.50/day
                "monthly_cc": Decimal("1200")   # 20% discount for monthly
            },
            ComputeInstanceType.T3_SMALL: {
                "hourly_cc": Decimal("4.16"),
                "daily_cc": Decimal("100"),
                "monthly_cc": Decimal("2400")
            },
            ComputeInstanceType.T3_MEDIUM: {
                "hourly_cc": Decimal("8.32"),
                "daily_cc": Decimal("200"),
                "monthly_cc": Decimal("4800")
            },
            ComputeInstanceType.T3_LARGE: {
                "hourly_cc": Decimal("16.64"),
                "daily_cc": Decimal("400"),
                "monthly_cc": Decimal("9600")
            },
            ComputeInstanceType.M5_LARGE: {
                "hourly_cc": Decimal("19.20"),
                "daily_cc": Decimal("500"),
                "monthly_cc": Decimal("12000")
            },
            ComputeInstanceType.C5_LARGE: {
                "hourly_cc": Decimal("17.00"),
                "daily_cc": Decimal("450"),
                "monthly_cc": Decimal("10800")
            }
        }
    
    async def create_instance_rental(
        self,
        user_id: str,
        instance_type: ComputeInstanceType,
        rental_duration_days: int,
        auto_renew: bool = False
    ) -> ComputeInstance:
        """Create a new compute instance rental"""
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Get pricing for instance type
        pricing = self.instance_pricing.get(instance_type)
        if not pricing:
            raise ValueError(f"Invalid instance type: {instance_type}")
        
        # Calculate rental costs
        if rental_duration_days >= 30:
            # Monthly pricing with discount
            months = rental_duration_days // 30
            remaining_days = rental_duration_days % 30
            
            total_cost_cc = (pricing["monthly_cc"] * months) + (pricing["daily_cc"] * remaining_days)
        else:
            # Daily pricing
            total_cost_cc = pricing["daily_cc"] * rental_duration_days
        
        # Check user balance
        user_balance = await self.cc_system.get_user_balance(user_id)
        if user_balance < total_cost_cc:
            raise ValueError(
                f"Insufficient balance. Required: {total_cost_cc} CC, Available: {user_balance} CC"
            )
        
        # Calculate rental period
        rental_start = datetime.utcnow()
        rental_end = rental_start + timedelta(days=rental_duration_days)
        
        # Create compute instance record
        instance = ComputeInstance(
            user_id=user_id,
            instance_type=instance_type,
            status=ComputeInstanceStatus.PENDING,
            hourly_rate_cc=pricing["hourly_cc"],
            daily_rate_cc=pricing["daily_cc"],
            monthly_rate_cc=pricing["monthly_cc"],
            rental_start=rental_start,
            rental_end=rental_end,
            auto_renew=auto_renew
        )
        
        try:
            # Deduct payment from user balance
            await self.cc_system.deduct_credits(
                user_id,
                total_cost_cc,
                TransactionType.PAYMENT,
                f"Compute rental: {instance_type.value} for {rental_duration_days} days",
                metadata={
                    "instance_type": instance_type.value,
                    "rental_duration_days": rental_duration_days,
                    "rental_start": rental_start.isoformat(),
                    "rental_end": rental_end.isoformat(),
                    "auto_renew": auto_renew
                }
            )
            
            # Launch AWS instance (simulated in this implementation)
            aws_instance_id = await self._launch_aws_instance(instance_type)
            instance.aws_instance_id = aws_instance_id
            instance.aws_region = "us-west-2"
            instance.status = ComputeInstanceStatus.RUNNING
            
            # Update total cost
            instance.total_cost_cc = total_cost_cc
            
            self.db.add(instance)
            self.db.commit()
            
            logger.info(
                f"Created compute rental for user {user_id}: {instance_type.value} "
                f"for {rental_duration_days} days, cost: {total_cost_cc} CC"
            )
            
            return instance
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create compute rental: {str(e)}")
            raise
    
    async def _launch_aws_instance(self, instance_type: ComputeInstanceType) -> str:
        """Launch AWS EC2 instance (simulated)"""
        
        # In production, this would use boto3 to actually launch an instance
        # For now, we'll simulate with a fake instance ID
        import secrets
        fake_instance_id = f"i-{secrets.token_hex(8)}"
        
        logger.info(f"Simulated launch of {instance_type.value} instance: {fake_instance_id}")
        
        # Simulate some delay for instance launch
        await asyncio.sleep(1)
        
        return fake_instance_id
    
    async def terminate_instance(self, instance_id: str, user_id: str) -> bool:
        """Terminate a compute instance"""
        
        instance = (
            self.db.query(ComputeInstance)
            .filter(
                and_(
                    ComputeInstance.id == instance_id,
                    ComputeInstance.user_id == user_id
                )
            )
            .first()
        )
        
        if not instance:
            raise ValueError(f"Instance {instance_id} not found for user {user_id}")
        
        if instance.status == ComputeInstanceStatus.TERMINATED:
            return True
        
        try:
            # Terminate AWS instance (simulated)
            await self._terminate_aws_instance(instance.aws_instance_id)
            
            # Calculate actual usage and costs
            actual_hours = self._calculate_actual_usage_hours(instance)
            actual_cost = actual_hours * instance.hourly_rate_cc
            
            # Update instance record
            instance.status = ComputeInstanceStatus.TERMINATED
            instance.terminated_at = datetime.utcnow()
            instance.total_hours_used = actual_hours
            
            # If user used less than paid for, provide refund
            if actual_cost < instance.total_cost_cc:
                refund_amount = instance.total_cost_cc - actual_cost
                
                await self.cc_system.add_credits(
                    user_id,
                    refund_amount,
                    TransactionType.REFUND,
                    f"Refund for early termination of {instance.instance_type.value}",
                    metadata={
                        "instance_id": instance_id,
                        "actual_hours_used": str(actual_hours),
                        "actual_cost_cc": str(actual_cost),
                        "original_cost_cc": str(instance.total_cost_cc),
                        "refund_amount_cc": str(refund_amount)
                    }
                )
                
                logger.info(f"Refunded {refund_amount} CC to user {user_id} for early termination")
            
            self.db.commit()
            
            logger.info(f"Terminated instance {instance_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to terminate instance {instance_id}: {str(e)}")
            raise
    
    async def _terminate_aws_instance(self, aws_instance_id: str):
        """Terminate AWS EC2 instance (simulated)"""
        
        # In production, this would use boto3 to terminate the instance
        logger.info(f"Simulated termination of AWS instance: {aws_instance_id}")
        await asyncio.sleep(0.5)
    
    def _calculate_actual_usage_hours(self, instance: ComputeInstance) -> Decimal:
        """Calculate actual usage hours for billing"""
        
        if not instance.rental_start:
            return Decimal("0")
        
        end_time = instance.terminated_at or datetime.utcnow()
        usage_delta = end_time - instance.rental_start
        
        # Convert to hours, rounded up to nearest hour
        hours = Decimal(usage_delta.total_seconds() / 3600)
        return hours.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    async def renew_instance(self, instance_id: str, renewal_days: int) -> ComputeInstance:
        """Renew an existing instance rental"""
        
        instance = self.db.query(ComputeInstance).filter(ComputeInstance.id == instance_id).first()
        if not instance:
            raise ValueError(f"Instance {instance_id} not found")
        
        if instance.status != ComputeInstanceStatus.RUNNING:
            raise ValueError(f"Instance {instance_id} is not in running state")
        
        # Calculate renewal cost
        pricing = self.instance_pricing[instance.instance_type]
        
        if renewal_days >= 30:
            months = renewal_days // 30
            remaining_days = renewal_days % 30
            renewal_cost_cc = (pricing["monthly_cc"] * months) + (pricing["daily_cc"] * remaining_days)
        else:
            renewal_cost_cc = pricing["daily_cc"] * renewal_days
        
        # Check user balance
        user_balance = await self.cc_system.get_user_balance(instance.user_id)
        if user_balance < renewal_cost_cc:
            raise ValueError(
                f"Insufficient balance for renewal. Required: {renewal_cost_cc} CC, Available: {user_balance} CC"
            )
        
        try:
            # Deduct renewal payment
            await self.cc_system.deduct_credits(
                instance.user_id,
                renewal_cost_cc,
                TransactionType.PAYMENT,
                f"Compute rental renewal: {instance.instance_type.value} for {renewal_days} days",
                metadata={
                    "instance_id": instance_id,
                    "renewal_duration_days": renewal_days,
                    "renewal_cost_cc": str(renewal_cost_cc)
                }
            )
            
            # Extend rental period
            instance.rental_end = instance.rental_end + timedelta(days=renewal_days)
            instance.total_cost_cc += renewal_cost_cc
            
            self.db.commit()
            
            logger.info(f"Renewed instance {instance_id} for {renewal_days} days, cost: {renewal_cost_cc} CC")
            return instance
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to renew instance {instance_id}: {str(e)}")
            raise
    
    async def process_auto_renewals(self) -> Dict[str, int]:
        """Process automatic renewals for expiring instances"""
        
        # Find instances that expire in the next 24 hours and have auto-renew enabled
        expiring_soon = datetime.utcnow() + timedelta(hours=24)
        
        auto_renew_instances = (
            self.db.query(ComputeInstance)
            .filter(
                and_(
                    ComputeInstance.status == ComputeInstanceStatus.RUNNING,
                    ComputeInstance.auto_renew == True,
                    ComputeInstance.rental_end <= expiring_soon
                )
            )
            .all()
        )
        
        results = {"renewed": 0, "failed": 0, "insufficient_funds": 0}
        
        for instance in auto_renew_instances:
            try:
                # Default to 30-day renewal
                renewal_days = 30
                
                # Check if user has sufficient balance
                pricing = self.instance_pricing[instance.instance_type]
                renewal_cost = pricing["monthly_cc"]
                
                user_balance = await self.cc_system.get_user_balance(instance.user_id)
                
                if user_balance >= renewal_cost:
                    await self.renew_instance(instance.id, renewal_days)
                    results["renewed"] += 1
                else:
                    # Insufficient funds - disable auto-renew and notify
                    instance.auto_renew = False
                    self.db.commit()
                    results["insufficient_funds"] += 1
                    
                    logger.warning(
                        f"Auto-renewal failed for instance {instance.id}: insufficient funds "
                        f"(required: {renewal_cost} CC, available: {user_balance} CC)"
                    )
                
            except Exception as e:
                logger.error(f"Failed to auto-renew instance {instance.id}: {str(e)}")
                results["failed"] += 1
        
        logger.info(f"Auto-renewal processing completed: {results}")
        return results
    
    async def get_user_instances(self, user_id: str) -> List[Dict]:
        """Get all compute instances for a user"""
        
        instances = (
            self.db.query(ComputeInstance)
            .filter(ComputeInstance.user_id == user_id)
            .order_by(desc(ComputeInstance.created_at))
            .all()
        )
        
        result = []
        for instance in instances:
            # Calculate remaining time
            remaining_time = None
            if instance.rental_end and instance.status == ComputeInstanceStatus.RUNNING:
                remaining_delta = instance.rental_end - datetime.utcnow()
                if remaining_delta.total_seconds() > 0:
                    remaining_time = {
                        "days": remaining_delta.days,
                        "hours": remaining_delta.seconds // 3600,
                        "minutes": (remaining_delta.seconds % 3600) // 60
                    }
            
            result.append({
                "instance_id": instance.id,
                "instance_type": instance.instance_type.value,
                "status": instance.status.value,
                "aws_instance_id": instance.aws_instance_id,
                "aws_region": instance.aws_region,
                "rental_start": instance.rental_start.isoformat() if instance.rental_start else None,
                "rental_end": instance.rental_end.isoformat() if instance.rental_end else None,
                "remaining_time": remaining_time,
                "auto_renew": instance.auto_renew,
                "total_cost_cc": float(instance.total_cost_cc),
                "total_hours_used": float(instance.total_hours_used),
                "hourly_rate_cc": float(instance.hourly_rate_cc),
                "daily_rate_cc": float(instance.daily_rate_cc),
                "monthly_rate_cc": float(instance.monthly_rate_cc),
                "created_at": instance.created_at.isoformat(),
                "terminated_at": instance.terminated_at.isoformat() if instance.terminated_at else None
            })
        
        return result
    
    async def get_instance_metrics(self, instance_id: str) -> Dict:
        """Get performance metrics for an instance (simulated)"""
        
        instance = self.db.query(ComputeInstance).filter(ComputeInstance.id == instance_id).first()
        if not instance:
            raise ValueError(f"Instance {instance_id} not found")
        
        # In production, this would fetch real metrics from CloudWatch
        # For now, we'll simulate some metrics
        import random
        
        return {
            "instance_id": instance_id,
            "status": instance.status.value,
            "metrics": {
                "cpu_utilization_percent": round(random.uniform(10, 80), 2),
                "memory_utilization_percent": round(random.uniform(20, 70), 2),
                "network_in_mbps": round(random.uniform(1, 50), 2),
                "network_out_mbps": round(random.uniform(1, 30), 2),
                "disk_read_iops": random.randint(50, 500),
                "disk_write_iops": random.randint(30, 300)
            },
            "cost_analysis": {
                "total_cost_cc": float(instance.total_cost_cc),
                "hours_used": float(instance.total_hours_used),
                "cost_per_hour_actual": float(instance.total_cost_cc / instance.total_hours_used) if instance.total_hours_used > 0 else 0,
                "estimated_monthly_cost": float(instance.hourly_rate_cc * 24 * 30)
            },
            "updated_at": datetime.utcnow().isoformat()
        }
    
    async def get_pricing_info(self) -> Dict:
        """Get current pricing information for all instance types"""
        
        pricing_info = {}
        
        for instance_type, pricing in self.instance_pricing.items():
            # Convert CC to USD for display
            pricing_info[instance_type.value] = {
                "hourly_rate_cc": float(pricing["hourly_cc"]),
                "daily_rate_cc": float(pricing["daily_cc"]),
                "monthly_rate_cc": float(pricing["monthly_cc"]),
                "hourly_rate_usd": float(pricing["hourly_cc"] * settings.compute_credits.cc_to_usd_rate),
                "daily_rate_usd": float(pricing["daily_cc"] * settings.compute_credits.cc_to_usd_rate),
                "monthly_rate_usd": float(pricing["monthly_cc"] * settings.compute_credits.cc_to_usd_rate),
                "monthly_discount_percentage": 20.0,  # 20% discount for monthly billing
                "specifications": self._get_instance_specs(instance_type)
            }
        
        return {
            "pricing": pricing_info,
            "billing_info": {
                "currency": "CC (Compute Credits)",
                "cc_to_usd_rate": float(settings.compute_credits.cc_to_usd_rate),
                "billing_precision": "Per hour usage",
                "minimum_rental": "1 hour",
                "auto_renewal_available": True,
                "early_termination_refund": True
            }
        }
    
    def _get_instance_specs(self, instance_type: ComputeInstanceType) -> Dict:
        """Get instance specifications"""
        
        specs = {
            ComputeInstanceType.T3_MICRO: {
                "vcpus": 2,
                "memory_gb": 1,
                "network_performance": "Low to Moderate",
                "storage": "EBS Only"
            },
            ComputeInstanceType.T3_SMALL: {
                "vcpus": 2,
                "memory_gb": 2,
                "network_performance": "Low to Moderate",
                "storage": "EBS Only"
            },
            ComputeInstanceType.T3_MEDIUM: {
                "vcpus": 2,
                "memory_gb": 4,
                "network_performance": "Low to Moderate",
                "storage": "EBS Only"
            },
            ComputeInstanceType.T3_LARGE: {
                "vcpus": 2,
                "memory_gb": 8,
                "network_performance": "Low to Moderate",
                "storage": "EBS Only"
            },
            ComputeInstanceType.M5_LARGE: {
                "vcpus": 2,
                "memory_gb": 8,
                "network_performance": "Up to 10 Gbps",
                "storage": "EBS Only"
            },
            ComputeInstanceType.C5_LARGE: {
                "vcpus": 2,
                "memory_gb": 4,
                "network_performance": "Up to 10 Gbps",
                "storage": "EBS Only"
            }
        }
        
        return specs.get(instance_type, {})