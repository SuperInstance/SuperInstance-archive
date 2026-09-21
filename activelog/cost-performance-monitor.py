#!/usr/bin/env python3
"""
PersonalLog.ai Cost and Performance Monitor
Real-time monitoring of system costs, performance, and revenue metrics
"""

import asyncio
import json
import time
import psutil
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging
import requests
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    response_time_ms: float
    active_users: int
    entries_created: int
    api_requests: int

@dataclass
class CostMetrics:
    timestamp: datetime
    compute_cost_usd: float
    storage_cost_usd: float
    bandwidth_cost_usd: float
    ai_api_cost_usd: float
    total_cost_usd: float
    estimated_monthly_usd: float

@dataclass
class RevenueMetrics:
    timestamp: datetime
    ad_impressions: int
    ad_clicks: int
    ad_revenue_usd: float
    premium_subscriptions: int
    subscription_revenue_usd: float
    total_revenue_usd: float

class CostPerformanceMonitor:
    """Comprehensive monitoring system for PersonalLog.ai"""
    
    def __init__(self):
        self.backend_url = "http://localhost:8101/api"
        self.ad_service_url = "http://localhost:8080"
        self.monitoring_interval = 30  # seconds
        
        # Cost assumptions (AWS pricing estimates)
        self.cost_rates = {
            "compute_per_hour": 0.0116,  # t3.micro instance
            "storage_per_gb_month": 0.10,  # EBS gp3
            "bandwidth_per_gb": 0.09,  # Data transfer
            "ai_api_per_1k_tokens": 0.002,  # GPT-3.5 equivalent
            "ad_revenue_per_impression": 0.002,  # $2 CPM
            "premium_subscription_monthly": 9.99
        }
        
        # Initialize database
        self.db_path = Path("monitoring/cost_performance.db")
        self.db_path.parent.mkdir(exist_ok=True)
        self.init_monitoring_db()
        
        # Metrics storage
        self.performance_history = []
        self.cost_history = []
        self.revenue_history = []
        
        # System baseline
        self.baseline_metrics = self.collect_system_metrics()
    
    def init_monitoring_db(self):
        """Initialize monitoring database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Performance metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                cpu_usage REAL NOT NULL,
                memory_usage REAL NOT NULL,
                disk_usage REAL NOT NULL,
                response_time_ms REAL DEFAULT 0,
                active_users INTEGER DEFAULT 0,
                entries_created INTEGER DEFAULT 0,
                api_requests INTEGER DEFAULT 0
            )
        ''')
        
        # Cost metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cost_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                compute_cost_usd REAL DEFAULT 0,
                storage_cost_usd REAL DEFAULT 0,
                bandwidth_cost_usd REAL DEFAULT 0,
                ai_api_cost_usd REAL DEFAULT 0,
                total_cost_usd REAL DEFAULT 0,
                estimated_monthly_usd REAL DEFAULT 0
            )
        ''')
        
        # Revenue metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS revenue_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                ad_impressions INTEGER DEFAULT 0,
                ad_clicks INTEGER DEFAULT 0,
                ad_revenue_usd REAL DEFAULT 0,
                premium_subscriptions INTEGER DEFAULT 0,
                subscription_revenue_usd REAL DEFAULT 0,
                total_revenue_usd REAL DEFAULT 0
            )
        ''')
        
        # Alerts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                resolved BOOLEAN DEFAULT FALSE
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Monitoring database initialized")
    
    def collect_system_metrics(self) -> Dict[str, float]:
        """Collect current system performance metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            return {
                "cpu_usage": cpu_percent,
                "memory_usage": memory_percent,
                "disk_usage": disk_percent,
                "memory_mb": memory.used / 1024 / 1024,
                "disk_gb": disk.used / 1024 / 1024 / 1024
            }
        
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return {
                "cpu_usage": 0,
                "memory_usage": 0,
                "disk_usage": 0,
                "memory_mb": 0,
                "disk_gb": 0
            }
    
    async def collect_application_metrics(self) -> Dict[str, Any]:
        """Collect application-specific metrics"""
        try:
            start_time = time.time()
            
            # Test backend response time
            response = requests.get(f"{self.backend_url}/metrics", timeout=5)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                backend_data = response.json()
                return {
                    "response_time_ms": response_time,
                    "requests_served": backend_data["metrics"]["requests_served"],
                    "entries_synced": backend_data["metrics"]["entries_synced"],
                    "ai_insights_generated": backend_data["metrics"]["ai_insights_generated"],
                    "ads_served": backend_data["metrics"]["ads_served"],
                    "database_size_mb": backend_data["database"]["size_mb"],
                    "status": "healthy"
                }
            else:
                return {
                    "response_time_ms": response_time,
                    "status": "error",
                    "error_code": response.status_code
                }
        
        except Exception as e:
            logger.error(f"Error collecting application metrics: {e}")
            return {
                "response_time_ms": 5000,  # Timeout
                "status": "error",
                "error": str(e)
            }
    
    def calculate_costs(self, system_metrics: Dict, app_metrics: Dict) -> CostMetrics:
        """Calculate current operational costs"""
        now = datetime.now()
        
        # Compute cost (hourly rate for running instance)
        compute_cost = self.cost_rates["compute_per_hour"] / 3600  # Per second
        
        # Storage cost (database size)
        storage_gb = app_metrics.get("database_size_mb", 0) / 1024
        storage_cost = (storage_gb * self.cost_rates["storage_per_gb_month"]) / (30 * 24 * 3600)  # Per second
        
        # Bandwidth cost (estimated based on API requests)
        api_requests = app_metrics.get("requests_served", 0)
        estimated_bandwidth_gb = api_requests * 0.001  # 1KB per request estimate
        bandwidth_cost = estimated_bandwidth_gb * self.cost_rates["bandwidth_per_gb"]
        
        # AI API cost (based on insights generated)
        ai_insights = app_metrics.get("ai_insights_generated", 0)
        estimated_tokens = ai_insights * 100  # 100 tokens per insight estimate
        ai_cost = (estimated_tokens / 1000) * self.cost_rates["ai_api_per_1k_tokens"]
        
        total_cost = compute_cost + storage_cost + bandwidth_cost + ai_cost
        monthly_estimate = total_cost * 30 * 24 * 3600  # Scale to monthly
        
        return CostMetrics(
            timestamp=now,
            compute_cost_usd=compute_cost,
            storage_cost_usd=storage_cost,
            bandwidth_cost_usd=bandwidth_cost,
            ai_api_cost_usd=ai_cost,
            total_cost_usd=total_cost,
            estimated_monthly_usd=monthly_estimate
        )
    
    async def calculate_revenue(self, app_metrics: Dict) -> RevenueMetrics:
        """Calculate current revenue metrics"""
        now = datetime.now()
        
        try:
            # Get ad performance data
            ad_response = requests.get(f"{self.ad_service_url}/ml/performance/dashboard", timeout=3)
            if ad_response.status_code == 200:
                ad_data = ad_response.json()
                ad_impressions = ad_data.get("total_impressions", 0)
                ad_clicks = ad_data.get("total_clicks", 0)
            else:
                ad_impressions = app_metrics.get("ads_served", 0)
                ad_clicks = 0
        
        except Exception:
            ad_impressions = app_metrics.get("ads_served", 0)
            ad_clicks = 0
        
        # Calculate ad revenue
        ad_revenue = ad_impressions * self.cost_rates["ad_revenue_per_impression"]
        
        # Premium subscriptions (simulated for demo)
        premium_subs = 0  # Would come from user database
        subscription_revenue = premium_subs * self.cost_rates["premium_subscription_monthly"]
        
        total_revenue = ad_revenue + subscription_revenue
        
        return RevenueMetrics(
            timestamp=now,
            ad_impressions=ad_impressions,
            ad_clicks=ad_clicks,
            ad_revenue_usd=ad_revenue,
            premium_subscriptions=premium_subs,
            subscription_revenue_usd=subscription_revenue,
            total_revenue_usd=total_revenue
        )
    
    def store_metrics(self, performance: PerformanceMetrics, cost: CostMetrics, revenue: RevenueMetrics):
        """Store metrics in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Store performance metrics
            cursor.execute('''
                INSERT INTO performance_metrics 
                (cpu_usage, memory_usage, disk_usage, response_time_ms, active_users, entries_created, api_requests)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                performance.cpu_usage,
                performance.memory_usage,
                performance.disk_usage,
                performance.response_time_ms,
                performance.active_users,
                performance.entries_created,
                performance.api_requests
            ))
            
            # Store cost metrics
            cursor.execute('''
                INSERT INTO cost_metrics 
                (compute_cost_usd, storage_cost_usd, bandwidth_cost_usd, ai_api_cost_usd, total_cost_usd, estimated_monthly_usd)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                cost.compute_cost_usd,
                cost.storage_cost_usd,
                cost.bandwidth_cost_usd,
                cost.ai_api_cost_usd,
                cost.total_cost_usd,
                cost.estimated_monthly_usd
            ))
            
            # Store revenue metrics
            cursor.execute('''
                INSERT INTO revenue_metrics 
                (ad_impressions, ad_clicks, ad_revenue_usd, premium_subscriptions, subscription_revenue_usd, total_revenue_usd)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                revenue.ad_impressions,
                revenue.ad_clicks,
                revenue.ad_revenue_usd,
                revenue.premium_subscriptions,
                revenue.subscription_revenue_usd,
                revenue.total_revenue_usd
            ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error storing metrics: {e}")
        finally:
            conn.close()
    
    def check_alerts(self, performance: PerformanceMetrics, cost: CostMetrics):
        """Check for alert conditions"""
        alerts = []
        
        # Performance alerts
        if performance.cpu_usage > 80:
            alerts.append(("performance", "warning", f"High CPU usage: {performance.cpu_usage:.1f}%"))
        
        if performance.memory_usage > 85:
            alerts.append(("performance", "warning", f"High memory usage: {performance.memory_usage:.1f}%"))
        
        if performance.response_time_ms > 1000:
            alerts.append(("performance", "critical", f"Slow response time: {performance.response_time_ms:.0f}ms"))
        
        # Cost alerts
        if cost.estimated_monthly_usd > 50:
            alerts.append(("cost", "warning", f"Monthly cost projection: ${cost.estimated_monthly_usd:.2f}"))
        
        if cost.estimated_monthly_usd > 100:
            alerts.append(("cost", "critical", f"High monthly cost: ${cost.estimated_monthly_usd:.2f}"))
        
        # Store alerts in database
        if alerts:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for alert_type, severity, message in alerts:
                cursor.execute('''
                    INSERT INTO alerts (alert_type, severity, message)
                    VALUES (?, ?, ?)
                ''', (alert_type, severity, message))
            
            conn.commit()
            conn.close()
        
        return alerts
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive monitoring report"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get latest metrics
        cursor.execute("SELECT * FROM performance_metrics ORDER BY timestamp DESC LIMIT 1")
        latest_perf = cursor.fetchone()
        
        cursor.execute("SELECT * FROM cost_metrics ORDER BY timestamp DESC LIMIT 1")
        latest_cost = cursor.fetchone()
        
        cursor.execute("SELECT * FROM revenue_metrics ORDER BY timestamp DESC LIMIT 1")
        latest_revenue = cursor.fetchone()
        
        # Get hourly averages for the last 24 hours
        cursor.execute('''
            SELECT 
                AVG(cpu_usage) as avg_cpu,
                AVG(memory_usage) as avg_memory,
                AVG(response_time_ms) as avg_response_time,
                SUM(api_requests) as total_requests
            FROM performance_metrics 
            WHERE timestamp > datetime('now', '-24 hours')
        ''')
        daily_stats = cursor.fetchone()
        
        # Get cost trends
        cursor.execute('''
            SELECT 
                AVG(total_cost_usd) as avg_cost_per_second,
                MAX(estimated_monthly_usd) as peak_monthly_estimate
            FROM cost_metrics 
            WHERE timestamp > datetime('now', '-24 hours')
        ''')
        cost_trends = cursor.fetchone()
        
        # Get unresolved alerts
        cursor.execute('''
            SELECT alert_type, severity, message, timestamp 
            FROM alerts 
            WHERE resolved = FALSE 
            ORDER BY timestamp DESC 
            LIMIT 10
        ''')
        active_alerts = cursor.fetchall()
        
        conn.close()
        
        return {
            "report_timestamp": datetime.now().isoformat(),
            "current_status": {
                "cpu_usage": latest_perf[2] if latest_perf else 0,
                "memory_usage": latest_perf[3] if latest_perf else 0,
                "response_time_ms": latest_perf[5] if latest_perf else 0,
                "estimated_monthly_cost": latest_cost[7] if latest_cost else 0,
                "total_revenue": latest_revenue[7] if latest_revenue else 0
            },
            "24h_trends": {
                "avg_cpu_usage": daily_stats[0] if daily_stats[0] else 0,
                "avg_memory_usage": daily_stats[1] if daily_stats[1] else 0,
                "avg_response_time": daily_stats[2] if daily_stats[2] else 0,
                "total_api_requests": daily_stats[3] if daily_stats[3] else 0,
                "avg_cost_per_second": cost_trends[0] if cost_trends[0] else 0,
                "peak_monthly_estimate": cost_trends[1] if cost_trends[1] else 0
            },
            "alerts": {
                "active_count": len(active_alerts),
                "recent_alerts": [
                    {
                        "type": alert[0],
                        "severity": alert[1],
                        "message": alert[2],
                        "timestamp": alert[3]
                    } for alert in active_alerts
                ]
            },
            "profitability": {
                "monthly_cost_estimate": latest_cost[7] if latest_cost else 0,
                "monthly_revenue_estimate": (latest_revenue[7] * 30) if latest_revenue else 0,
                "break_even_users_needed": max(1, int((latest_cost[7] if latest_cost else 0) / (self.cost_rates["premium_subscription_monthly"] * 0.7)))  # 70% conversion assumption
            }
        }
    
    async def monitoring_loop(self):
        """Main monitoring loop"""
        logger.info("🚀 Starting Cost & Performance Monitoring")
        
        while True:
            try:
                # Collect metrics
                system_metrics = self.collect_system_metrics()
                app_metrics = await self.collect_application_metrics()
                
                # Create metric objects
                performance = PerformanceMetrics(
                    timestamp=datetime.now(),
                    cpu_usage=system_metrics["cpu_usage"],
                    memory_usage=system_metrics["memory_usage"],
                    disk_usage=system_metrics["disk_usage"],
                    response_time_ms=app_metrics.get("response_time_ms", 0),
                    active_users=10,  # Beta users count
                    entries_created=app_metrics.get("requests_served", 0),
                    api_requests=app_metrics.get("requests_served", 0)
                )
                
                cost = self.calculate_costs(system_metrics, app_metrics)
                revenue = await self.calculate_revenue(app_metrics)
                
                # Store metrics
                self.store_metrics(performance, cost, revenue)
                
                # Check for alerts
                alerts = self.check_alerts(performance, cost)
                
                # Log current status
                logger.info(f"📊 CPU: {performance.cpu_usage:.1f}% | "
                           f"Mem: {performance.memory_usage:.1f}% | "
                           f"Response: {performance.response_time_ms:.0f}ms | "
                           f"Monthly Est: ${cost.estimated_monthly_usd:.2f}")
                
                if alerts:
                    for alert_type, severity, message in alerts:
                        logger.warning(f"🚨 {severity.upper()} {alert_type}: {message}")
                
                # Store in memory for reporting
                self.performance_history.append(performance)
                self.cost_history.append(cost)
                self.revenue_history.append(revenue)
                
                # Keep only recent history
                if len(self.performance_history) > 1440:  # 24 hours at 1-minute intervals
                    self.performance_history = self.performance_history[-720:]  # Keep 12 hours
                    self.cost_history = self.cost_history[-720:]
                    self.revenue_history = self.revenue_history[-720:]
                
                await asyncio.sleep(self.monitoring_interval)
                
            except KeyboardInterrupt:
                logger.info("⏹️  Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Monitoring error: {e}")
                await asyncio.sleep(5)  # Brief pause before retry

async def main():
    """Main monitoring execution"""
    monitor = CostPerformanceMonitor()
    
    try:
        # Generate initial report
        print("📋 PersonalLog.ai Cost & Performance Monitoring")
        print("=" * 60)
        
        # Run a few monitoring cycles to gather data
        logger.info("Collecting initial metrics...")
        for i in range(3):
            system_metrics = monitor.collect_system_metrics()
            app_metrics = await monitor.collect_application_metrics()
            
            performance = PerformanceMetrics(
                timestamp=datetime.now(),
                cpu_usage=system_metrics["cpu_usage"],
                memory_usage=system_metrics["memory_usage"],
                disk_usage=system_metrics["disk_usage"],
                response_time_ms=app_metrics.get("response_time_ms", 0),
                active_users=10,
                entries_created=app_metrics.get("requests_served", 0),
                api_requests=app_metrics.get("requests_served", 0)
            )
            
            cost = monitor.calculate_costs(system_metrics, app_metrics)
            revenue = await monitor.calculate_revenue(app_metrics)
            
            monitor.store_metrics(performance, cost, revenue)
            
            await asyncio.sleep(2)
        
        # Generate and display report
        report = monitor.generate_report()
        
        print(f"\n⚡ Current Performance:")
        print(f"   CPU Usage: {report['current_status']['cpu_usage']:.1f}%")
        print(f"   Memory Usage: {report['current_status']['memory_usage']:.1f}%")
        print(f"   Response Time: {report['current_status']['response_time_ms']:.0f}ms")
        
        print(f"\n💰 Cost Analysis:")
        print(f"   Estimated Monthly Cost: ${report['current_status']['estimated_monthly_cost']:.2f}")
        print(f"   Break-even Users Needed: {report['profitability']['break_even_users_needed']}")
        
        print(f"\n📊 Revenue Potential:")
        print(f"   Current Revenue: ${report['current_status']['total_revenue']:.4f}")
        print(f"   Monthly Revenue Projection: ${report['profitability']['monthly_revenue_estimate']:.2f}")
        
        print(f"\n🎯 Beta Test Economics:")
        print(f"   • 10 free tier users generating ad revenue")
        print(f"   • Current cost per user: ${(report['current_status']['estimated_monthly_cost'] / 10):.2f}/month")
        print(f"   • Target: $9.99 premium subscription")
        print(f"   • Conversion needed: {(report['profitability']['break_even_users_needed'] / 10 * 100):.1f}% to break even")
        
        if report['alerts']['active_count'] > 0:
            print(f"\n🚨 Active Alerts: {report['alerts']['active_count']}")
            for alert in report['alerts']['recent_alerts']:
                print(f"   • {alert['severity'].upper()}: {alert['message']}")
        else:
            print(f"\n✅ No active alerts")
        
        print(f"\n📈 Monitoring Status: Active")
        print(f"📍 Data stored in: {monitor.db_path}")
        print("=" * 60)
        
        # Save detailed report
        with open("cost-performance-report.json", "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"💾 Detailed report saved to: cost-performance-report.json")
        
    except Exception as e:
        logger.error(f"❌ Monitoring setup failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())