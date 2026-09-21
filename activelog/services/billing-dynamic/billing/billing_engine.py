"""
Minute-Level Billing Engine
Precise billing with sub-minute granularity and real-time cost tracking
"""

import asyncio
import json
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal, ROUND_HALF_UP
import redis
import uuid
from collections import defaultdict, deque
import math

class BillingStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    SUSPENDED = "suspended"
    ERROR = "error"

class ServiceTier(Enum):
    FREE = "free"
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

@dataclass
class ResourceUsage:
    """Resource usage measurement for billing"""
    timestamp: datetime
    cpu_seconds: float
    memory_mb_seconds: float
    storage_gb_seconds: float
    network_gb: float
    gpu_seconds: float = 0.0
    requests_count: int = 0
    custom_metrics: Dict[str, float] = field(default_factory=dict)

@dataclass
class PricingRules:
    """Pricing rules for different resources and tiers"""
    tier: ServiceTier
    
    # Per-minute pricing (in cents)
    cpu_per_core_minute: Decimal
    memory_per_gb_minute: Decimal
    storage_per_gb_minute: Decimal
    network_per_gb: Decimal
    gpu_per_minute: Decimal
    requests_per_1k: Decimal
    
    # Minimum charges
    minimum_session_charge: Decimal
    minimum_monthly_charge: Decimal
    
    # Discounts and multipliers
    volume_discount_threshold: Decimal  # Usage amount for discount
    volume_discount_rate: Decimal  # Discount percentage
    peak_hour_multiplier: Decimal  # Multiplier for peak hours
    
    # Free tier limits
    free_cpu_minutes: int = 0
    free_memory_gb_minutes: int = 0
    free_storage_gb_minutes: int = 0
    free_network_gb: int = 0
    free_requests: int = 0

@dataclass
class BillingSession:
    """Active billing session tracking resource usage and costs"""
    session_id: str
    user_id: str
    service_type: str
    tier: ServiceTier
    status: BillingStatus
    
    # Session timing
    started_at: datetime
    last_updated: datetime
    stopped_at: Optional[datetime] = None
    
    # Resource tracking
    resource_config: Dict[str, Any] = field(default_factory=dict)
    accumulated_usage: Dict[str, float] = field(default_factory=dict)
    usage_history: List[ResourceUsage] = field(default_factory=list)
    
    # Cost tracking
    accumulated_cost: Decimal = Decimal("0.00")
    cost_breakdown: Dict[str, Decimal] = field(default_factory=dict)
    pricing_rules: Optional[PricingRules] = None
    
    # Billing configuration
    billing_config: Dict[str, Any] = field(default_factory=dict)
    cost_alerts: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadata
    tags: Dict[str, str] = field(default_factory=dict)
    notes: str = ""

class MinuteLevelBillingEngine:
    """
    High-precision billing engine that tracks resource usage and costs
    at sub-minute intervals with real-time cost calculation
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.logger = logging.getLogger(__name__)
        
        # Active billing sessions
        self.active_sessions: Dict[str, BillingSession] = {}
        
        # Usage tracking
        self.usage_queue: deque = deque(maxlen=10000)  # Recent usage records
        self.cost_calculation_interval = 10  # seconds
        
        # Pricing configuration
        self.pricing_rules = self._initialize_pricing_rules()
        
        # Billing processor state
        self.billing_processor_running = False
        self.last_cost_calculation = time.time()
        
        # Performance metrics
        self.metrics = {
            "sessions_processed": 0,
            "total_cost_calculated": Decimal("0.00"),
            "average_processing_time": 0.0,
            "error_count": 0
        }

    def _initialize_pricing_rules(self) -> Dict[ServiceTier, PricingRules]:
        """Initialize pricing rules for different service tiers"""
        return {
            ServiceTier.FREE: PricingRules(
                tier=ServiceTier.FREE,
                cpu_per_core_minute=Decimal("0.00"),
                memory_per_gb_minute=Decimal("0.00"),
                storage_per_gb_minute=Decimal("0.00"),
                network_per_gb=Decimal("0.00"),
                gpu_per_minute=Decimal("0.00"),
                requests_per_1k=Decimal("0.00"),
                minimum_session_charge=Decimal("0.00"),
                minimum_monthly_charge=Decimal("0.00"),
                volume_discount_threshold=Decimal("0.00"),
                volume_discount_rate=Decimal("0.00"),
                peak_hour_multiplier=Decimal("1.00"),
                free_cpu_minutes=100,
                free_memory_gb_minutes=200,
                free_storage_gb_minutes=1000,
                free_network_gb=1,
                free_requests=10000
            ),
            ServiceTier.BASIC: PricingRules(
                tier=ServiceTier.BASIC,
                cpu_per_core_minute=Decimal("0.0167"),  # $0.01 per core hour
                memory_per_gb_minute=Decimal("0.0083"),  # $0.005 per GB hour
                storage_per_gb_minute=Decimal("0.0002"),  # $0.012 per GB month
                network_per_gb=Decimal("0.90"),  # $0.009 per GB
                gpu_per_minute=Decimal("0.40"),  # $0.24 per GPU hour
                requests_per_1k=Decimal("0.20"),  # $0.0002 per request
                minimum_session_charge=Decimal("0.01"),  # 1 cent minimum
                minimum_monthly_charge=Decimal("5.00"),
                volume_discount_threshold=Decimal("100.00"),
                volume_discount_rate=Decimal("0.10"),  # 10% discount
                peak_hour_multiplier=Decimal("1.50")  # 50% more during peak
            ),
            ServiceTier.STANDARD: PricingRules(
                tier=ServiceTier.STANDARD,
                cpu_per_core_minute=Decimal("0.0125"),  # $0.0075 per core hour (25% discount)
                memory_per_gb_minute=Decimal("0.0063"),  # 25% discount
                storage_per_gb_minute=Decimal("0.0002"),
                network_per_gb=Decimal("0.80"),  # 11% discount
                gpu_per_minute=Decimal("0.35"),  # 12.5% discount
                requests_per_1k=Decimal("0.15"),  # 25% discount
                minimum_session_charge=Decimal("0.01"),
                minimum_monthly_charge=Decimal("15.00"),
                volume_discount_threshold=Decimal("200.00"),
                volume_discount_rate=Decimal("0.15"),  # 15% discount
                peak_hour_multiplier=Decimal("1.25")  # 25% more during peak
            ),
            ServiceTier.PREMIUM: PricingRules(
                tier=ServiceTier.PREMIUM,
                cpu_per_core_minute=Decimal("0.0100"),  # 40% discount
                memory_per_gb_minute=Decimal("0.0050"),  # 40% discount
                storage_per_gb_minute=Decimal("0.0001"),  # 50% discount
                network_per_gb=Decimal("0.60"),  # 33% discount
                gpu_per_minute=Decimal("0.30"),  # 25% discount
                requests_per_1k=Decimal("0.10"),  # 50% discount
                minimum_session_charge=Decimal("0.01"),
                minimum_monthly_charge=Decimal("50.00"),
                volume_discount_threshold=Decimal("500.00"),
                volume_discount_rate=Decimal("0.20"),  # 20% discount
                peak_hour_multiplier=Decimal("1.00")  # No peak pricing
            ),
            ServiceTier.ENTERPRISE: PricingRules(
                tier=ServiceTier.ENTERPRISE,
                cpu_per_core_minute=Decimal("0.0075"),  # 55% discount
                memory_per_gb_minute=Decimal("0.0038"),  # 54% discount
                storage_per_gb_minute=Decimal("0.0001"),  # 50% discount
                network_per_gb=Decimal("0.40"),  # 56% discount
                gpu_per_minute=Decimal("0.25"),  # 38% discount
                requests_per_1k=Decimal("0.05"),  # 75% discount
                minimum_session_charge=Decimal("0.00"),  # No minimum
                minimum_monthly_charge=Decimal("200.00"),
                volume_discount_threshold=Decimal("1000.00"),
                volume_discount_rate=Decimal("0.25"),  # 25% discount
                peak_hour_multiplier=Decimal("1.00")  # No peak pricing
            )
        }

    async def start_billing_session(
        self,
        user_id: str,
        service_type: str,
        resource_config: Dict[str, Any] = None,
        billing_config: Dict[str, Any] = None,
        tier: ServiceTier = ServiceTier.BASIC
    ) -> str:
        """Start a new billing session with specified configuration"""
        try:
            session_id = f"session_{user_id}_{int(time.time())}_{str(uuid.uuid4())[:8]}"
            
            # Create billing session
            session = BillingSession(
                session_id=session_id,
                user_id=user_id,
                service_type=service_type,
                tier=tier,
                status=BillingStatus.ACTIVE,
                started_at=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc),
                resource_config=resource_config or {},
                billing_config=billing_config or {},
                pricing_rules=self.pricing_rules[tier]
            )
            
            # Initialize accumulated usage
            session.accumulated_usage = {
                "cpu_seconds": 0.0,
                "memory_mb_seconds": 0.0,
                "storage_gb_seconds": 0.0,
                "network_gb": 0.0,
                "gpu_seconds": 0.0,
                "requests_count": 0
            }
            
            # Initialize cost breakdown
            session.cost_breakdown = {
                "cpu_cost": Decimal("0.00"),
                "memory_cost": Decimal("0.00"),
                "storage_cost": Decimal("0.00"),
                "network_cost": Decimal("0.00"),
                "gpu_cost": Decimal("0.00"),
                "requests_cost": Decimal("0.00"),
                "minimum_charge": Decimal("0.00"),
                "discounts": Decimal("0.00"),
                "peak_surcharge": Decimal("0.00")
            }
            
            # Store session
            self.active_sessions[session_id] = session
            
            # Store in Redis if available
            if self.redis_client:
                await self._store_session_in_redis(session)
            
            self.logger.info(f"Started billing session {session_id} for user {user_id}")
            return session_id
            
        except Exception as e:
            self.logger.error(f"Failed to start billing session: {e}")
            raise

    async def stop_billing_session(self, session_id: str) -> Dict[str, Any]:
        """Stop billing session and generate final bill"""
        try:
            if session_id not in self.active_sessions:
                raise ValueError(f"Session {session_id} not found")
            
            session = self.active_sessions[session_id]
            session.status = BillingStatus.STOPPED
            session.stopped_at = datetime.now(timezone.utc)
            session.last_updated = datetime.now(timezone.utc)
            
            # Perform final cost calculation
            await self._calculate_session_cost(session)
            
            # Apply minimum charges
            await self._apply_minimum_charges(session)
            
            # Generate final bill
            final_bill = await self._generate_final_bill(session)
            
            # Archive session
            await self._archive_session(session)
            
            # Remove from active sessions
            del self.active_sessions[session_id]
            
            self.logger.info(f"Stopped billing session {session_id}, final cost: ${session.accumulated_cost}")
            return final_bill
            
        except Exception as e:
            self.logger.error(f"Failed to stop billing session {session_id}: {e}")
            raise

    async def record_usage(self, session_id: str, usage: ResourceUsage):
        """Record resource usage for a billing session"""
        try:
            if session_id not in self.active_sessions:
                self.logger.warning(f"Usage recorded for unknown session {session_id}")
                return
            
            session = self.active_sessions[session_id]
            
            if session.status != BillingStatus.ACTIVE:
                self.logger.warning(f"Usage recorded for inactive session {session_id}")
                return
            
            # Add usage to session history
            session.usage_history.append(usage)
            
            # Update accumulated usage
            session.accumulated_usage["cpu_seconds"] += usage.cpu_seconds
            session.accumulated_usage["memory_mb_seconds"] += usage.memory_mb_seconds
            session.accumulated_usage["storage_gb_seconds"] += usage.storage_gb_seconds
            session.accumulated_usage["network_gb"] += usage.network_gb
            session.accumulated_usage["gpu_seconds"] += usage.gpu_seconds
            session.accumulated_usage["requests_count"] += usage.requests_count
            
            # Update last updated time
            session.last_updated = datetime.now(timezone.utc)
            
            # Add to usage queue for processing
            self.usage_queue.append((session_id, usage))
            
            # Store in Redis if available
            if self.redis_client:
                await self._update_session_usage_in_redis(session_id, usage)
            
        except Exception as e:
            self.logger.error(f"Failed to record usage for session {session_id}: {e}")
            self.metrics["error_count"] += 1

    async def pause_billing_session(self, session_id: str):
        """Pause billing for a session"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session.status = BillingStatus.PAUSED
            session.last_updated = datetime.now(timezone.utc)
            
            self.logger.info(f"Paused billing session {session_id}")

    async def resume_billing_session(self, session_id: str):
        """Resume billing for a paused session"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            if session.status == BillingStatus.PAUSED:
                session.status = BillingStatus.ACTIVE
                session.last_updated = datetime.now(timezone.utc)
                
                self.logger.info(f"Resumed billing session {session_id}")

    async def get_session_details(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a billing session"""
        try:
            if session_id not in self.active_sessions:
                return None
            
            session = self.active_sessions[session_id]
            
            # Calculate current cost
            await self._calculate_session_cost(session)
            
            # Calculate session duration
            duration = session.last_updated - session.started_at
            
            return {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "service_type": session.service_type,
                "tier": session.tier.value,
                "status": session.status.value,
                "started_at": session.started_at.isoformat(),
                "last_updated": session.last_updated.isoformat(),
                "duration_minutes": duration.total_seconds() / 60,
                "resource_config": session.resource_config,
                "accumulated_usage": session.accumulated_usage,
                "accumulated_cost": float(session.accumulated_cost),
                "cost_breakdown": {k: float(v) for k, v in session.cost_breakdown.items()},
                "usage_history_count": len(session.usage_history),
                "cost_alerts": session.cost_alerts
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get session details for {session_id}: {e}")
            return None

    async def get_user_current_bill(self, user_id: str) -> Dict[str, Any]:
        """Get current accumulated bill for a user across all active sessions"""
        try:
            user_sessions = [
                session for session in self.active_sessions.values()
                if session.user_id == user_id
            ]
            
            if not user_sessions:
                return {
                    "user_id": user_id,
                    "active_sessions": 0,
                    "total_cost": 0.0,
                    "sessions": []
                }
            
            total_cost = Decimal("0.00")
            session_details = []
            
            for session in user_sessions:
                # Calculate current cost for session
                await self._calculate_session_cost(session)
                total_cost += session.accumulated_cost
                
                session_details.append({
                    "session_id": session.session_id,
                    "service_type": session.service_type,
                    "status": session.status.value,
                    "cost": float(session.accumulated_cost),
                    "duration_minutes": (session.last_updated - session.started_at).total_seconds() / 60
                })
            
            return {
                "user_id": user_id,
                "active_sessions": len(user_sessions),
                "total_cost": float(total_cost),
                "sessions": session_details,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get current bill for user {user_id}: {e}")
            return {"error": str(e)}

    async def _calculate_session_cost(self, session: BillingSession):
        """Calculate current cost for a billing session"""
        try:
            if not session.pricing_rules:
                return
            
            pricing = session.pricing_rules
            
            # Convert accumulated usage to billable units
            cpu_minutes = session.accumulated_usage["cpu_seconds"] / 60.0
            memory_gb_minutes = session.accumulated_usage["memory_mb_seconds"] / (1024 * 60)
            storage_gb_minutes = session.accumulated_usage["storage_gb_seconds"] / 60.0
            network_gb = session.accumulated_usage["network_gb"]
            gpu_minutes = session.accumulated_usage["gpu_seconds"] / 60.0
            requests_thousands = session.accumulated_usage["requests_count"] / 1000.0
            
            # Apply free tier limits
            billable_cpu_minutes = max(0, cpu_minutes - pricing.free_cpu_minutes)
            billable_memory_gb_minutes = max(0, memory_gb_minutes - pricing.free_memory_gb_minutes)
            billable_storage_gb_minutes = max(0, storage_gb_minutes - pricing.free_storage_gb_minutes)
            billable_network_gb = max(0, network_gb - pricing.free_network_gb)
            billable_gpu_minutes = gpu_minutes  # No free GPU typically
            billable_requests_thousands = max(0, requests_thousands - (pricing.free_requests / 1000.0))
            
            # Calculate base costs
            session.cost_breakdown["cpu_cost"] = Decimal(str(billable_cpu_minutes)) * pricing.cpu_per_core_minute
            session.cost_breakdown["memory_cost"] = Decimal(str(billable_memory_gb_minutes)) * pricing.memory_per_gb_minute
            session.cost_breakdown["storage_cost"] = Decimal(str(billable_storage_gb_minutes)) * pricing.storage_per_gb_minute
            session.cost_breakdown["network_cost"] = Decimal(str(billable_network_gb)) * pricing.network_per_gb
            session.cost_breakdown["gpu_cost"] = Decimal(str(billable_gpu_minutes)) * pricing.gpu_per_minute
            session.cost_breakdown["requests_cost"] = Decimal(str(billable_requests_thousands)) * pricing.requests_per_1k
            
            # Calculate subtotal
            subtotal = sum([
                session.cost_breakdown["cpu_cost"],
                session.cost_breakdown["memory_cost"],
                session.cost_breakdown["storage_cost"],
                session.cost_breakdown["network_cost"],
                session.cost_breakdown["gpu_cost"],
                session.cost_breakdown["requests_cost"]
            ])
            
            # Apply peak hour multiplier
            peak_multiplier = await self._calculate_peak_hour_multiplier(session, pricing)
            if peak_multiplier > Decimal("1.00"):
                peak_surcharge = subtotal * (peak_multiplier - Decimal("1.00"))
                session.cost_breakdown["peak_surcharge"] = peak_surcharge
                subtotal += peak_surcharge
            
            # Apply volume discounts
            discount = await self._calculate_volume_discount(session, pricing, subtotal)
            if discount > Decimal("0.00"):
                session.cost_breakdown["discounts"] = -discount
                subtotal -= discount
            
            # Update accumulated cost
            session.accumulated_cost = subtotal
            
        except Exception as e:
            self.logger.error(f"Failed to calculate cost for session {session.session_id}: {e}")
            self.metrics["error_count"] += 1

    async def _calculate_peak_hour_multiplier(
        self, 
        session: BillingSession, 
        pricing: PricingRules
    ) -> Decimal:
        """Calculate peak hour multiplier based on session timing"""
        try:
            # Define peak hours (9 AM to 6 PM UTC)
            current_hour = datetime.now(timezone.utc).hour
            
            if 9 <= current_hour <= 18:  # Peak hours
                return pricing.peak_hour_multiplier
            else:
                return Decimal("1.00")
                
        except Exception:
            return Decimal("1.00")

    async def _calculate_volume_discount(
        self,
        session: BillingSession,
        pricing: PricingRules,
        subtotal: Decimal
    ) -> Decimal:
        """Calculate volume discount based on usage"""
        try:
            if subtotal >= pricing.volume_discount_threshold:
                return subtotal * pricing.volume_discount_rate
            return Decimal("0.00")
            
        except Exception:
            return Decimal("0.00")

    async def _apply_minimum_charges(self, session: BillingSession):
        """Apply minimum charges to session"""
        try:
            if not session.pricing_rules:
                return
            
            minimum_charge = session.pricing_rules.minimum_session_charge
            
            if session.accumulated_cost < minimum_charge:
                session.cost_breakdown["minimum_charge"] = minimum_charge - session.accumulated_cost
                session.accumulated_cost = minimum_charge
                
        except Exception as e:
            self.logger.error(f"Failed to apply minimum charges for session {session.session_id}: {e}")

    async def _generate_final_bill(self, session: BillingSession) -> Dict[str, Any]:
        """Generate final bill for completed session"""
        try:
            duration = session.stopped_at - session.started_at if session.stopped_at else timedelta(0)
            
            return {
                "bill_id": f"bill_{session.session_id}_{int(time.time())}",
                "session_id": session.session_id,
                "user_id": session.user_id,
                "service_type": session.service_type,
                "tier": session.tier.value,
                "billing_period": {
                    "started_at": session.started_at.isoformat(),
                    "stopped_at": session.stopped_at.isoformat() if session.stopped_at else None,
                    "duration_minutes": duration.total_seconds() / 60
                },
                "resource_usage": session.accumulated_usage,
                "cost_breakdown": {k: float(v) for k, v in session.cost_breakdown.items()},
                "total_cost": float(session.accumulated_cost),
                "currency": "USD",
                "pricing_rules": {
                    "tier": session.tier.value,
                    "cpu_per_core_minute": float(session.pricing_rules.cpu_per_core_minute),
                    "memory_per_gb_minute": float(session.pricing_rules.memory_per_gb_minute),
                    "storage_per_gb_minute": float(session.pricing_rules.storage_per_gb_minute),
                    "network_per_gb": float(session.pricing_rules.network_per_gb)
                },
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "status": "final"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate final bill for session {session.session_id}: {e}")
            return {"error": str(e)}

    async def start_billing_processor(self):
        """Start background billing processor"""
        if self.billing_processor_running:
            return
        
        self.billing_processor_running = True
        self.logger.info("Starting billing processor")
        
        try:
            while self.billing_processor_running:
                start_time = time.time()
                
                # Process usage queue
                await self._process_usage_queue()
                
                # Calculate costs for active sessions
                await self._process_active_sessions()
                
                # Check for cost alerts
                await self._check_cost_alerts()
                
                # Update metrics
                processing_time = time.time() - start_time
                self.metrics["average_processing_time"] = (
                    self.metrics["average_processing_time"] * 0.9 + processing_time * 0.1
                )
                
                # Wait for next cycle
                await asyncio.sleep(self.cost_calculation_interval)
                
        except asyncio.CancelledError:
            self.logger.info("Billing processor cancelled")
        except Exception as e:
            self.logger.error(f"Billing processor error: {e}")
        finally:
            self.billing_processor_running = False

    async def _process_usage_queue(self):
        """Process pending usage records"""
        try:
            processed = 0
            while self.usage_queue and processed < 100:  # Process up to 100 records per cycle
                session_id, usage = self.usage_queue.popleft()
                
                if session_id in self.active_sessions:
                    session = self.active_sessions[session_id]
                    await self._calculate_session_cost(session)
                
                processed += 1
            
            if processed > 0:
                self.metrics["sessions_processed"] += processed
                
        except Exception as e:
            self.logger.error(f"Error processing usage queue: {e}")

    async def _process_active_sessions(self):
        """Process all active sessions for cost calculation"""
        try:
            current_time = time.time()
            
            # Only recalculate if enough time has passed
            if current_time - self.last_cost_calculation < self.cost_calculation_interval:
                return
            
            for session in self.active_sessions.values():
                if session.status == BillingStatus.ACTIVE:
                    await self._calculate_session_cost(session)
            
            self.last_cost_calculation = current_time
            
        except Exception as e:
            self.logger.error(f"Error processing active sessions: {e}")

    async def _check_cost_alerts(self):
        """Check for cost threshold alerts"""
        try:
            for session in self.active_sessions.values():
                for alert_config in session.cost_alerts:
                    threshold = Decimal(str(alert_config.get("threshold", 0)))
                    
                    if session.accumulated_cost >= threshold:
                        # Trigger alert (would integrate with notification system)
                        alert = {
                            "alert_id": f"cost_alert_{session.session_id}_{int(time.time())}",
                            "session_id": session.session_id,
                            "user_id": session.user_id,
                            "alert_type": "cost_threshold",
                            "threshold": float(threshold),
                            "current_cost": float(session.accumulated_cost),
                            "triggered_at": datetime.now(timezone.utc).isoformat()
                        }
                        
                        self.logger.warning(f"Cost alert triggered: {alert}")
                        
                        # Remove triggered alert to prevent spam
                        session.cost_alerts.remove(alert_config)
                        
        except Exception as e:
            self.logger.error(f"Error checking cost alerts: {e}")

    async def _store_session_in_redis(self, session: BillingSession):
        """Store billing session in Redis"""
        try:
            if not self.redis_client:
                return
            
            session_data = {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "service_type": session.service_type,
                "tier": session.tier.value,
                "status": session.status.value,
                "started_at": session.started_at.isoformat(),
                "accumulated_cost": float(session.accumulated_cost)
            }
            
            await self.redis_client.hset(
                f"billing_session:{session.session_id}",
                mapping=session_data
            )
            
            # Set expiration (30 days)
            await self.redis_client.expire(f"billing_session:{session.session_id}", 2592000)
            
        except Exception as e:
            self.logger.error(f"Failed to store session in Redis: {e}")

    async def _update_session_usage_in_redis(self, session_id: str, usage: ResourceUsage):
        """Update session usage in Redis"""
        try:
            if not self.redis_client:
                return
            
            usage_key = f"billing_usage:{session_id}"
            
            # Store usage record
            usage_data = {
                "timestamp": usage.timestamp.isoformat(),
                "cpu_seconds": usage.cpu_seconds,
                "memory_mb_seconds": usage.memory_mb_seconds,
                "storage_gb_seconds": usage.storage_gb_seconds,
                "network_gb": usage.network_gb,
                "gpu_seconds": usage.gpu_seconds,
                "requests_count": usage.requests_count
            }
            
            # Add to sorted set with timestamp as score
            await self.redis_client.zadd(
                usage_key,
                {json.dumps(usage_data): usage.timestamp.timestamp()}
            )
            
            # Keep only recent usage (last 24 hours)
            cutoff = time.time() - 86400
            await self.redis_client.zremrangebyscore(usage_key, 0, cutoff)
            
        except Exception as e:
            self.logger.error(f"Failed to update session usage in Redis: {e}")

    async def _archive_session(self, session: BillingSession):
        """Archive completed billing session"""
        try:
            # Store in Redis for historical data
            if self.redis_client:
                archive_key = f"billing_archive:{session.user_id}:{session.session_id}"
                
                archive_data = {
                    "session_id": session.session_id,
                    "user_id": session.user_id,
                    "service_type": session.service_type,
                    "tier": session.tier.value,
                    "started_at": session.started_at.isoformat(),
                    "stopped_at": session.stopped_at.isoformat() if session.stopped_at else None,
                    "total_cost": float(session.accumulated_cost),
                    "resource_usage": json.dumps(session.accumulated_usage),
                    "cost_breakdown": json.dumps({k: float(v) for k, v in session.cost_breakdown.items()})
                }
                
                await self.redis_client.hset(archive_key, mapping=archive_data)
                
                # Set long-term expiration (1 year)
                await self.redis_client.expire(archive_key, 31536000)
            
            # Update total metrics
            self.metrics["total_cost_calculated"] += session.accumulated_cost
            
        except Exception as e:
            self.logger.error(f"Failed to archive session {session.session_id}: {e}")

    async def cleanup_old_data(self) -> Dict[str, Any]:
        """Clean up old billing data"""
        try:
            cleaned_sessions = 0
            
            # Clean up old Redis keys
            if self.redis_client:
                # Find old session keys
                cursor = 0
                while True:
                    cursor, keys = await self.redis_client.scan(
                        cursor=cursor,
                        match="billing_session:*",
                        count=100
                    )
                    
                    for key in keys:
                        # Check if session is old (more than 30 days)
                        ttl = await self.redis_client.ttl(key)
                        if ttl == -1:  # No expiration set
                            await self.redis_client.delete(key)
                            cleaned_sessions += 1
                    
                    if cursor == 0:
                        break
            
            return {
                "cleaned_sessions": cleaned_sessions,
                "cleaned_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to clean up old data: {e}")
            return {"error": str(e)}

    async def get_status(self) -> Dict[str, Any]:
        """Get billing engine status"""
        return {
            "status": "running" if self.billing_processor_running else "stopped",
            "active_sessions": len(self.active_sessions),
            "usage_queue_size": len(self.usage_queue),
            "metrics": {
                "sessions_processed": self.metrics["sessions_processed"],
                "total_cost_calculated": float(self.metrics["total_cost_calculated"]),
                "average_processing_time": self.metrics["average_processing_time"],
                "error_count": self.metrics["error_count"]
            },
            "last_cost_calculation": self.last_cost_calculation,
            "redis_connected": self.redis_client is not None
        }

    async def shutdown(self):
        """Shutdown billing engine gracefully"""
        try:
            self.logger.info("Shutting down billing engine...")
            
            # Stop billing processor
            self.billing_processor_running = False
            
            # Archive all active sessions
            for session in self.active_sessions.values():
                session.status = BillingStatus.STOPPED
                session.stopped_at = datetime.now(timezone.utc)
                await self._calculate_session_cost(session)
                await self._archive_session(session)
            
            self.logger.info("Billing engine shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during billing engine shutdown: {e}")