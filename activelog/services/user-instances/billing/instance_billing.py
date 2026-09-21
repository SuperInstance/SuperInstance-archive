"""
Billing system for user instances
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import json
import sqlite3
import httpx
import os

logger = logging.getLogger(__name__)

class InstanceBilling:
    """
    Manages billing for user instances including cost tracking and estimation
    """
    
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/user-instances/data/billing.db"
        self.billing_tasks = {}
        self._init_database()
        
        # EC2 pricing (USD per hour)
        self.instance_pricing = {
            't3.micro': 0.0104,
            't3.small': 0.0208,
            't3.medium': 0.0416,
            't3.large': 0.0832,
            't3.xlarge': 0.1664,
            'm5.large': 0.096,
            'm5.xlarge': 0.192,
            'm5.2xlarge': 0.384,
            'm5.4xlarge': 0.768
        }
        
        # Storage pricing (USD per GB-month)
        self.storage_pricing = {
            'gp3': 0.08,
            'gp2': 0.10,
            'io1': 0.125,
            'io2': 0.125
        }
        
        # Data transfer pricing (USD per GB)
        self.data_transfer_pricing = 0.09
        
        # KMS pricing (USD per key per month)
        self.kms_pricing = 1.00
    
    def _init_database(self):
        """Initialize SQLite database for billing records"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Billing sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS billing_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    instance_id TEXT NOT NULL,
                    tier TEXT NOT NULL,
                    instance_type TEXT NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    hourly_rate REAL NOT NULL,
                    total_hours REAL DEFAULT 0,
                    compute_cost REAL DEFAULT 0,
                    storage_cost REAL DEFAULT 0,
                    network_cost REAL DEFAULT 0,
                    kms_cost REAL DEFAULT 0,
                    total_cost REAL DEFAULT 0,
                    status TEXT DEFAULT 'active'
                )
            """)
            
            # Usage metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usage_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    instance_id TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    cpu_hours REAL DEFAULT 0,
                    memory_gb_hours REAL DEFAULT 0,
                    storage_gb_hours REAL DEFAULT 0,
                    network_gb_in REAL DEFAULT 0,
                    network_gb_out REAL DEFAULT 0,
                    cost_impact REAL DEFAULT 0
                )
            """)
            
            # Monthly billing summaries table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS monthly_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    month INTEGER NOT NULL,
                    total_compute_cost REAL DEFAULT 0,
                    total_storage_cost REAL DEFAULT 0,
                    total_network_cost REAL DEFAULT 0,
                    total_kms_cost REAL DEFAULT 0,
                    total_cost REAL DEFAULT 0,
                    total_hours REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, year, month)
                )
            """)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to initialize billing database: {e}")
            raise
    
    async def start_billing(self, user_id: str, instance_id: str, tier: str):
        """Start billing session for a user instance"""
        try:
            # Get instance details for pricing
            instance_type = self._get_instance_type_for_tier(tier)
            hourly_rate = self.instance_pricing.get(instance_type, 0.0208)
            
            # Create billing session
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO billing_sessions 
                (user_id, instance_id, tier, instance_type, start_time, hourly_rate, status)
                VALUES (?, ?, ?, ?, ?, ?, 'active')
            """, (user_id, instance_id, tier, instance_type, datetime.utcnow(), hourly_rate))
            
            conn.commit()
            conn.close()
            
            # Start billing tracking task
            task = asyncio.create_task(
                self._billing_tracking_loop(user_id, instance_id)
            )
            self.billing_tasks[user_id] = task
            
            logger.info(f"Started billing for user {user_id} instance {instance_id}")
            
        except Exception as e:
            logger.error(f"Failed to start billing: {e}")
            raise
    
    async def stop_billing(self, user_id: str):
        """Stop billing for a user"""
        try:
            # Cancel billing task
            if user_id in self.billing_tasks:
                self.billing_tasks[user_id].cancel()
                del self.billing_tasks[user_id]
            
            # Update billing session
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE billing_sessions 
                SET end_time = ?, status = 'stopped'
                WHERE user_id = ? AND status = 'active'
            """, (datetime.utcnow(), user_id))
            
            # Calculate final costs
            await self._calculate_session_costs(user_id)
            
            conn.commit()
            conn.close()
            
            logger.info(f"Stopped billing for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to stop billing: {e}")
    
    async def pause_billing(self, user_id: str):
        """Pause billing when instance is stopped"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE billing_sessions 
                SET status = 'paused'
                WHERE user_id = ? AND status = 'active'
            """, (user_id,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to pause billing: {e}")
    
    async def resume_billing(self, user_id: str):
        """Resume billing when instance is started"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE billing_sessions 
                SET status = 'active'
                WHERE user_id = ? AND status = 'paused'
            """, (user_id,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to resume billing: {e}")
    
    def calculate_monthly_cost(self, tier: str) -> float:
        """Calculate estimated monthly cost for a tier"""
        instance_type = self._get_instance_type_for_tier(tier)
        hourly_rate = self.instance_pricing.get(instance_type, 0.0208)
        
        # Assume 730 hours per month (24 * 30.42 average)
        monthly_compute = hourly_rate * 730
        
        # Storage cost (100GB default)
        monthly_storage = 100 * self.storage_pricing['gp3']
        
        # KMS cost
        monthly_kms = self.kms_pricing
        
        # Network estimate (10GB per month)
        monthly_network = 10 * self.data_transfer_pricing
        
        total = monthly_compute + monthly_storage + monthly_kms + monthly_network
        return round(total, 2)
    
    async def get_current_usage(self, user_id: str) -> Dict[str, float]:
        """Get current usage and costs for a user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get active session
            cursor.execute("""
                SELECT * FROM billing_sessions 
                WHERE user_id = ? AND status IN ('active', 'paused')
                ORDER BY start_time DESC LIMIT 1
            """, (user_id,))
            
            session = cursor.fetchone()
            if not session:
                return {}
            
            # Calculate current costs
            current_time = datetime.utcnow()
            start_time = datetime.fromisoformat(session[4])  # start_time column
            
            if session[12] == 'active':  # status column
                hours_running = (current_time - start_time).total_seconds() / 3600
            else:
                hours_running = session[7] if session[7] else 0  # total_hours column
            
            hourly_rate = session[6]  # hourly_rate column
            current_cost = hours_running * hourly_rate
            
            # Monthly estimate
            days_in_month = 30.42
            hours_per_month = 24 * days_in_month
            monthly_estimate = self.calculate_monthly_cost(session[3])  # tier column
            
            conn.close()
            
            return {
                'current_cost': round(current_cost, 4),
                'monthly_estimate': monthly_estimate,
                'hours_running': round(hours_running, 2),
                'hourly_rate': hourly_rate
            }
            
        except Exception as e:
            logger.error(f"Failed to get current usage: {e}")
            return {}
    
    async def get_detailed_billing(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed billing information for a user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get current month summary
            now = datetime.utcnow()
            cursor.execute("""
                SELECT * FROM monthly_summaries 
                WHERE user_id = ? AND year = ? AND month = ?
            """, (user_id, now.year, now.month))
            
            current_month = cursor.fetchone()
            
            # Get all sessions for current month
            month_start = datetime(now.year, now.month, 1)
            cursor.execute("""
                SELECT * FROM billing_sessions 
                WHERE user_id = ? AND start_time >= ?
                ORDER BY start_time DESC
            """, (user_id, month_start))
            
            sessions = cursor.fetchall()
            
            # Get recent usage metrics
            week_ago = now - timedelta(days=7)
            cursor.execute("""
                SELECT * FROM usage_metrics 
                WHERE user_id = ? AND timestamp >= ?
                ORDER BY timestamp DESC LIMIT 100
            """, (user_id, week_ago))
            
            recent_usage = cursor.fetchall()
            
            conn.close()
            
            # Format response
            billing_info = {
                'user_id': user_id,
                'current_month': {
                    'total_cost': current_month[5] if current_month else 0.0,
                    'compute_cost': current_month[3] if current_month else 0.0,
                    'storage_cost': current_month[4] if current_month else 0.0,
                    'total_hours': current_month[7] if current_month else 0.0
                },
                'active_sessions': len([s for s in sessions if s[12] == 'active']),
                'total_sessions': len(sessions),
                'recent_usage_points': len(recent_usage),
                'last_updated': now.isoformat()
            }
            
            return billing_info
            
        except Exception as e:
            logger.error(f"Failed to get detailed billing: {e}")
            return None
    
    async def _billing_tracking_loop(self, user_id: str, instance_id: str):
        """Continuous billing tracking loop"""
        try:
            while True:
                # Update billing calculations
                await self._update_billing_calculations(user_id, instance_id)
                
                # Send billing data to billing service
                await self._send_billing_data(user_id)
                
                # Wait before next update
                await asyncio.sleep(300)  # Update every 5 minutes
                
        except asyncio.CancelledError:
            logger.info(f"Billing tracking cancelled for user {user_id}")
        except Exception as e:
            logger.error(f"Error in billing tracking loop: {e}")
    
    async def _update_billing_calculations(self, user_id: str, instance_id: str):
        """Update billing calculations for a user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get active session
            cursor.execute("""
                SELECT * FROM billing_sessions 
                WHERE user_id = ? AND instance_id = ? AND status = 'active'
            """, (user_id, instance_id))
            
            session = cursor.fetchone()
            if not session:
                return
            
            # Calculate costs
            current_time = datetime.utcnow()
            start_time = datetime.fromisoformat(session[4])
            hours_running = (current_time - start_time).total_seconds() / 3600
            
            compute_cost = hours_running * session[6]  # hourly_rate
            storage_cost = (100 * self.storage_pricing['gp3'] / 730) * hours_running  # Prorated storage
            kms_cost = (self.kms_pricing / 730) * hours_running  # Prorated KMS
            
            total_cost = compute_cost + storage_cost + kms_cost
            
            # Update session
            cursor.execute("""
                UPDATE billing_sessions 
                SET total_hours = ?, compute_cost = ?, storage_cost = ?, 
                    kms_cost = ?, total_cost = ?
                WHERE user_id = ? AND instance_id = ? AND status = 'active'
            """, (hours_running, compute_cost, storage_cost, kms_cost, total_cost, user_id, instance_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to update billing calculations: {e}")
    
    async def _calculate_session_costs(self, user_id: str):
        """Calculate final costs for a billing session"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get the session that was just stopped
            cursor.execute("""
                SELECT * FROM billing_sessions 
                WHERE user_id = ? AND status = 'stopped'
                ORDER BY end_time DESC LIMIT 1
            """, (user_id,))
            
            session = cursor.fetchone()
            if not session:
                return
            
            # Calculate final costs
            start_time = datetime.fromisoformat(session[4])
            end_time = datetime.fromisoformat(session[5]) if session[5] else datetime.utcnow()
            
            total_hours = (end_time - start_time).total_seconds() / 3600
            compute_cost = total_hours * session[6]
            storage_cost = (100 * self.storage_pricing['gp3'] / 730) * total_hours
            kms_cost = (self.kms_pricing / 730) * total_hours
            total_cost = compute_cost + storage_cost + kms_cost
            
            # Update final costs
            cursor.execute("""
                UPDATE billing_sessions 
                SET total_hours = ?, compute_cost = ?, storage_cost = ?, 
                    kms_cost = ?, total_cost = ?
                WHERE id = ?
            """, (total_hours, compute_cost, storage_cost, kms_cost, total_cost, session[0]))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to calculate session costs: {e}")
    
    async def _send_billing_data(self, user_id: str):
        """Send billing data to billing service"""
        try:
            billing_service_url = os.getenv('BILLING_SERVICE_URL', 'http://localhost:8005')
            
            usage_data = await self.get_current_usage(user_id)
            if not usage_data:
                return
            
            billing_payload = {
                'user_id': user_id,
                'service': 'user-instances',
                'timestamp': datetime.utcnow().isoformat(),
                'current_cost': usage_data.get('current_cost', 0.0),
                'monthly_estimate': usage_data.get('monthly_estimate', 0.0),
                'usage_details': usage_data
            }
            
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{billing_service_url}/instance-usage",
                    json=billing_payload,
                    timeout=10.0
                )
                
        except Exception as e:
            logger.debug(f"Failed to send billing data: {e}")
    
    def _get_instance_type_for_tier(self, tier: str) -> str:
        """Get instance type for a given tier"""
        tier_mapping = {
            'starter': 't3.small',
            'professional': 't3.medium',
            'business': 't3.large', 
            'enterprise': 'm5.xlarge',
            'premium': 'm5.2xlarge'
        }
        return tier_mapping.get(tier.lower(), 't3.small')