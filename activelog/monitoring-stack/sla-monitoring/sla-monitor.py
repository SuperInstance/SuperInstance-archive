#!/usr/bin/env python3
"""
ActiveLog SLA Monitoring System
Tracks and reports on Service Level Agreements for all ActiveLog services
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
import aiohttp
import asyncpg
from prometheus_client import CollectorRegistry, Gauge, Counter, Histogram, generate_latest
from dataclasses import dataclass
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SLATarget:
    """SLA target definition"""
    name: str
    service: str
    metric_type: str  # availability, latency, error_rate, throughput
    target_value: float
    measurement_window: str  # 1h, 24h, 30d
    alert_threshold: float  # percentage of target before alerting

@dataclass
class SLAStatus:
    """Current SLA status"""
    target: SLATarget
    current_value: float
    target_met: bool
    error_budget_remaining: float
    last_updated: datetime

class PrometheusClient:
    """Client for querying Prometheus metrics"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def query(self, query: str, time_param: Optional[str] = None) -> Dict[str, Any]:
        """Execute Prometheus query"""
        params = {'query': query}
        if time_param:
            params['time'] = time_param
        
        async with self.session.get(f"{self.base_url}/api/v1/query", params=params) as response:
            data = await response.json()
            if data['status'] != 'success':
                raise Exception(f"Prometheus query failed: {data}")
            return data['data']
    
    async def query_range(self, query: str, start: str, end: str, step: str) -> Dict[str, Any]:
        """Execute Prometheus range query"""
        params = {
            'query': query,
            'start': start,
            'end': end,
            'step': step
        }
        
        async with self.session.get(f"{self.base_url}/api/v1/query_range", params=params) as response:
            data = await response.json()
            if data['status'] != 'success':
                raise Exception(f"Prometheus range query failed: {data}")
            return data['data']

class SLACalculator:
    """Calculates SLA metrics from Prometheus data"""
    
    def __init__(self, prometheus_client: PrometheusClient):
        self.prometheus = prometheus_client
    
    async def calculate_availability(self, service: str, window: str) -> float:
        """Calculate service availability percentage"""
        query = f'''
        (
          sum(rate(http_requests_total{{service="{service}"}}[{window}])) -
          sum(rate(http_requests_total{{service="{service}",code=~"5.."}}[{window}]))
        ) / sum(rate(http_requests_total{{service="{service}"}}[{window}])) * 100
        '''
        
        result = await self.prometheus.query(query)
        if result['result']:
            return float(result['result'][0]['value'][1])
        return 0.0
    
    async def calculate_latency_p99(self, service: str, window: str) -> float:
        """Calculate 99th percentile latency"""
        query = f'histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{{service="{service}"}}[{window}])) * 1000'
        
        result = await self.prometheus.query(query)
        if result['result']:
            return float(result['result'][0]['value'][1])
        return 0.0
    
    async def calculate_error_rate(self, service: str, window: str) -> float:
        """Calculate error rate percentage"""
        query = f'''
        sum(rate(http_requests_total{{service="{service}",code=~"[45].."}}[{window}])) /
        sum(rate(http_requests_total{{service="{service}"}}[{window}])) * 100
        '''
        
        result = await self.prometheus.query(query)
        if result['result']:
            return float(result['result'][0]['value'][1])
        return 0.0
    
    async def calculate_throughput(self, service: str, window: str) -> float:
        """Calculate requests per second"""
        query = f'sum(rate(http_requests_total{{service="{service}"}}[{window}]))'
        
        result = await self.prometheus.query(query)
        if result['result']:
            return float(result['result'][0]['value'][1])
        return 0.0

class SLAMonitor:
    """Main SLA monitoring service"""
    
    def __init__(self, config_path: str):
        self.config = self.load_config(config_path)
        self.targets = self.load_sla_targets()
        self.prometheus_client = PrometheusClient(self.config['prometheus']['url'])
        self.calculator = SLACalculator(self.prometheus_client)
        
        # Prometheus metrics for SLA monitoring
        self.registry = CollectorRegistry()
        self.sla_status = Gauge(
            'activelog_sla_status',
            'Current SLA status (1=met, 0=violated)',
            ['service', 'sla_name', 'metric_type'],
            registry=self.registry
        )
        self.sla_current_value = Gauge(
            'activelog_sla_current_value',
            'Current value of SLA metric',
            ['service', 'sla_name', 'metric_type'],
            registry=self.registry
        )
        self.sla_target_value = Gauge(
            'activelog_sla_target_value',
            'Target value of SLA metric',
            ['service', 'sla_name', 'metric_type'],
            registry=self.registry
        )
        self.sla_error_budget = Gauge(
            'activelog_sla_error_budget_remaining',
            'Remaining error budget percentage',
            ['service', 'sla_name', 'metric_type'],
            registry=self.registry
        )
        self.sla_violations = Counter(
            'activelog_sla_violations_total',
            'Total number of SLA violations',
            ['service', 'sla_name', 'metric_type'],
            registry=self.registry
        )
        
        # Database connection
        self.db_pool = None
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def load_sla_targets(self) -> List[SLATarget]:
        """Load SLA targets from configuration"""
        targets = []
        for target_config in self.config['sla_targets']:
            target = SLATarget(
                name=target_config['name'],
                service=target_config['service'],
                metric_type=target_config['metric_type'],
                target_value=target_config['target_value'],
                measurement_window=target_config['measurement_window'],
                alert_threshold=target_config.get('alert_threshold', 0.9)
            )
            targets.append(target)
        return targets
    
    async def connect_database(self):
        """Connect to PostgreSQL database"""
        db_config = self.config['database']
        self.db_pool = await asyncpg.create_pool(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database'],
            min_size=2,
            max_size=10
        )
        
        # Create SLA monitoring tables if they don't exist
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS sla_measurements (
                    id SERIAL PRIMARY KEY,
                    service VARCHAR(100) NOT NULL,
                    sla_name VARCHAR(100) NOT NULL,
                    metric_type VARCHAR(50) NOT NULL,
                    current_value DOUBLE PRECISION NOT NULL,
                    target_value DOUBLE PRECISION NOT NULL,
                    target_met BOOLEAN NOT NULL,
                    error_budget_remaining DOUBLE PRECISION NOT NULL,
                    measurement_time TIMESTAMP WITH TIME ZONE NOT NULL,
                    measurement_window VARCHAR(20) NOT NULL
                )
            ''')
            
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_sla_measurements_service_time 
                ON sla_measurements (service, measurement_time DESC)
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS sla_violations (
                    id SERIAL PRIMARY KEY,
                    service VARCHAR(100) NOT NULL,
                    sla_name VARCHAR(100) NOT NULL,
                    metric_type VARCHAR(50) NOT NULL,
                    violation_start TIMESTAMP WITH TIME ZONE NOT NULL,
                    violation_end TIMESTAMP WITH TIME ZONE,
                    duration_minutes INTEGER,
                    severity VARCHAR(20) NOT NULL,
                    resolved BOOLEAN DEFAULT FALSE
                )
            ''')
    
    async def calculate_sla_status(self, target: SLATarget) -> SLAStatus:
        """Calculate current SLA status for a target"""
        current_value = 0.0
        
        try:
            if target.metric_type == 'availability':
                current_value = await self.calculator.calculate_availability(
                    target.service, target.measurement_window
                )
            elif target.metric_type == 'latency':
                current_value = await self.calculator.calculate_latency_p99(
                    target.service, target.measurement_window
                )
            elif target.metric_type == 'error_rate':
                current_value = await self.calculator.calculate_error_rate(
                    target.service, target.measurement_window
                )
            elif target.metric_type == 'throughput':
                current_value = await self.calculator.calculate_throughput(
                    target.service, target.measurement_window
                )
        except Exception as e:
            logger.error(f"Failed to calculate {target.metric_type} for {target.service}: {e}")
            current_value = 0.0
        
        # Determine if target is met
        target_met = False
        if target.metric_type in ['availability', 'throughput']:
            target_met = current_value >= target.target_value
        else:  # latency, error_rate (lower is better)
            target_met = current_value <= target.target_value
        
        # Calculate error budget remaining
        if target.metric_type == 'availability':
            error_budget = 100 - target.target_value  # e.g., if target is 99.9%, budget is 0.1%
            current_unavailability = 100 - current_value
            error_budget_remaining = max(0, (error_budget - current_unavailability) / error_budget * 100)
        elif target.metric_type == 'error_rate':
            error_budget_remaining = max(0, (target.target_value - current_value) / target.target_value * 100)
        else:
            error_budget_remaining = 100 if target_met else 0
        
        return SLAStatus(
            target=target,
            current_value=current_value,
            target_met=target_met,
            error_budget_remaining=error_budget_remaining,
            last_updated=datetime.now(timezone.utc)
        )
    
    async def record_sla_measurement(self, status: SLAStatus):
        """Record SLA measurement to database"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO sla_measurements 
                (service, sla_name, metric_type, current_value, target_value, 
                 target_met, error_budget_remaining, measurement_time, measurement_window)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ''', 
            status.target.service,
            status.target.name,
            status.target.metric_type,
            status.current_value,
            status.target.target_value,
            status.target_met,
            status.error_budget_remaining,
            status.last_updated,
            status.target.measurement_window
            )
    
    async def check_sla_violation(self, status: SLAStatus):
        """Check and record SLA violations"""
        if not status.target_met:
            # Check if this is a new violation
            async with self.db_pool.acquire() as conn:
                existing = await conn.fetchrow('''
                    SELECT id FROM sla_violations 
                    WHERE service = $1 AND sla_name = $2 AND metric_type = $3 
                    AND resolved = FALSE
                    ORDER BY violation_start DESC LIMIT 1
                ''', status.target.service, status.target.name, status.target.metric_type)
                
                if not existing:
                    # New violation
                    severity = 'high' if status.error_budget_remaining < 10 else 'medium'
                    await conn.execute('''
                        INSERT INTO sla_violations 
                        (service, sla_name, metric_type, violation_start, severity)
                        VALUES ($1, $2, $3, $4, $5)
                    ''', 
                    status.target.service,
                    status.target.name,
                    status.target.metric_type,
                    status.last_updated,
                    severity
                    )
                    
                    self.sla_violations.labels(
                        service=status.target.service,
                        sla_name=status.target.name,
                        metric_type=status.target.metric_type
                    ).inc()
        else:
            # Check if we need to resolve an existing violation
            async with self.db_pool.acquire() as conn:
                violation = await conn.fetchrow('''
                    SELECT id, violation_start FROM sla_violations 
                    WHERE service = $1 AND sla_name = $2 AND metric_type = $3 
                    AND resolved = FALSE
                    ORDER BY violation_start DESC LIMIT 1
                ''', status.target.service, status.target.name, status.target.metric_type)
                
                if violation:
                    duration_minutes = int((status.last_updated - violation['violation_start']).total_seconds() / 60)
                    await conn.execute('''
                        UPDATE sla_violations 
                        SET violation_end = $1, duration_minutes = $2, resolved = TRUE
                        WHERE id = $3
                    ''', status.last_updated, duration_minutes, violation['id'])
    
    async def update_prometheus_metrics(self, status: SLAStatus):
        """Update Prometheus metrics with current SLA status"""
        labels = {
            'service': status.target.service,
            'sla_name': status.target.name,
            'metric_type': status.target.metric_type
        }
        
        self.sla_status.labels(**labels).set(1 if status.target_met else 0)
        self.sla_current_value.labels(**labels).set(status.current_value)
        self.sla_target_value.labels(**labels).set(status.target.target_value)
        self.sla_error_budget.labels(**labels).set(status.error_budget_remaining)
    
    async def monitor_slas(self):
        """Main SLA monitoring loop"""
        logger.info("Starting SLA monitoring...")
        
        async with self.prometheus_client:
            while True:
                try:
                    for target in self.targets:
                        logger.info(f"Checking SLA: {target.name} for service {target.service}")
                        
                        status = await self.calculate_sla_status(target)
                        await self.record_sla_measurement(status)
                        await self.check_sla_violation(status)
                        await self.update_prometheus_metrics(status)
                        
                        logger.info(
                            f"SLA {target.name}: {status.current_value:.2f} "
                            f"(target: {target.target_value}, met: {status.target_met}, "
                            f"budget: {status.error_budget_remaining:.1f}%)"
                        )
                        
                        # Small delay between targets
                        await asyncio.sleep(1)
                    
                    # Wait for next monitoring cycle
                    await asyncio.sleep(self.config.get('monitoring_interval', 300))  # 5 minutes default
                    
                except Exception as e:
                    logger.error(f"Error in SLA monitoring loop: {e}")
                    await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def get_sla_report(self, service: Optional[str] = None, 
                           hours: int = 24) -> Dict[str, Any]:
        """Generate SLA report"""
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        query_conditions = ["measurement_time >= $1"]
        params = [since]
        
        if service:
            query_conditions.append("service = $2")
            params.append(service)
        
        where_clause = " AND ".join(query_conditions)
        
        async with self.db_pool.acquire() as conn:
            # Get current SLA status
            current_status = await conn.fetch(f'''
                SELECT DISTINCT ON (service, sla_name) 
                    service, sla_name, metric_type, current_value, target_value,
                    target_met, error_budget_remaining, measurement_time
                FROM sla_measurements 
                WHERE {where_clause}
                ORDER BY service, sla_name, measurement_time DESC
            ''', *params)
            
            # Get violations in the period
            violations = await conn.fetch(f'''
                SELECT service, sla_name, metric_type, violation_start, 
                       violation_end, duration_minutes, severity, resolved
                FROM sla_violations 
                WHERE violation_start >= $1
                {" AND service = $2" if service else ""}
                ORDER BY violation_start DESC
            ''', *params)
        
        report = {
            'period_hours': hours,
            'report_time': datetime.now(timezone.utc).isoformat(),
            'current_status': [dict(row) for row in current_status],
            'violations': [dict(row) for row in violations],
            'summary': {
                'total_slas': len(current_status),
                'slas_met': sum(1 for row in current_status if row['target_met']),
                'total_violations': len(violations),
                'unresolved_violations': sum(1 for row in violations if not row['resolved'])
            }
        }
        
        return report
    
    async def run(self):
        """Run the SLA monitor"""
        await self.connect_database()
        await self.monitor_slas()

def main():
    """Main entry point"""
    config_path = os.getenv('SLA_CONFIG_PATH', '/etc/activelog/sla-monitor.yml')
    monitor = SLAMonitor(config_path)
    
    try:
        asyncio.run(monitor.run())
    except KeyboardInterrupt:
        logger.info("SLA monitor stopped by user")
    except Exception as e:
        logger.error(f"SLA monitor crashed: {e}")
        raise

if __name__ == '__main__':
    main()