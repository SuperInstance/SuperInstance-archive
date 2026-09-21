#!/usr/bin/env python3
"""
ActiveLog Cost Tracking System
Monitors and tracks costs across all infrastructure and services
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
import aiohttp
import asyncpg
from prometheus_client import CollectorRegistry, Gauge, Counter, generate_latest
from dataclasses import dataclass
import yaml
import boto3
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class CostData:
    """Cost data point"""
    service: str
    resource_type: str
    cost: float
    currency: str
    period_start: datetime
    period_end: datetime
    tags: Dict[str, str]

@dataclass
class Budget:
    """Budget definition"""
    name: str
    service: str
    amount: float
    period: str  # daily, weekly, monthly, yearly
    alert_thresholds: List[float]  # [50, 80, 95] - percentages

class AWSCostCollector:
    """Collects cost data from AWS Cost Explorer"""
    
    def __init__(self, profile_name: Optional[str] = None):
        self.session = boto3.Session(profile_name=profile_name)
        self.cost_explorer = self.session.client('ce')
    
    async def get_cost_and_usage(self, start_date: str, end_date: str, 
                                granularity: str = 'DAILY') -> List[CostData]:
        """Get cost and usage data from AWS"""
        try:
            response = self.cost_explorer.get_cost_and_usage(
                TimePeriod={'Start': start_date, 'End': end_date},
                Granularity=granularity,
                Metrics=['BlendedCost', 'UnblendedCost', 'UsageQuantity'],
                GroupBy=[
                    {'Type': 'DIMENSION', 'Key': 'SERVICE'},
                    {'Type': 'TAG', 'Key': 'Environment'},
                    {'Type': 'TAG', 'Key': 'Component'}
                ]
            )
            
            cost_data = []
            for result in response['ResultsByTime']:
                period_start = datetime.fromisoformat(result['TimePeriod']['Start'])
                period_end = datetime.fromisoformat(result['TimePeriod']['End'])
                
                for group in result['Groups']:
                    service = group['Keys'][0] if group['Keys'] else 'Unknown'
                    environment = group['Keys'][1] if len(group['Keys']) > 1 else 'Unknown'
                    component = group['Keys'][2] if len(group['Keys']) > 2 else 'Unknown'
                    
                    blended_cost = float(group['Metrics']['BlendedCost']['Amount'])
                    
                    cost_data.append(CostData(
                        service=service,
                        resource_type='aws_service',
                        cost=blended_cost,
                        currency=group['Metrics']['BlendedCost']['Unit'],
                        period_start=period_start,
                        period_end=period_end,
                        tags={'environment': environment, 'component': component}
                    ))
            
            return cost_data
            
        except Exception as e:
            logger.error(f"Failed to get AWS cost data: {e}")
            return []
    
    async def get_reserved_instance_utilization(self) -> Dict[str, Any]:
        """Get Reserved Instance utilization data"""
        try:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            response = self.cost_explorer.get_reserved_instance_utilization(
                TimePeriod={'Start': start_date, 'End': end_date},
                GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
            )
            
            utilization_data = {}
            for result in response['UtilizationsByTime']:
                for group in result['Groups']:
                    service = group['Key']
                    utilization = group['Utilization']
                    utilization_data[service] = {
                        'utilization_percentage': float(utilization['UtilizationPercentage']),
                        'purchased_hours': float(utilization['PurchasedHours']),
                        'used_hours': float(utilization['UsedHours']),
                        'unused_hours': float(utilization['UnusedHours'])
                    }
            
            return utilization_data
            
        except Exception as e:
            logger.error(f"Failed to get RI utilization: {e}")
            return {}

class PrometheusMetricsCollector:
    """Collects infrastructure metrics for cost attribution"""
    
    def __init__(self, prometheus_url: str):
        self.prometheus_url = prometheus_url.rstrip('/')
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def query(self, query: str) -> Dict[str, Any]:
        """Execute Prometheus query"""
        params = {'query': query}
        async with self.session.get(f"{self.prometheus_url}/api/v1/query", params=params) as response:
            data = await response.json()
            if data['status'] != 'success':
                raise Exception(f"Prometheus query failed: {data}")
            return data['data']
    
    async def get_resource_usage_metrics(self) -> Dict[str, Any]:
        """Get resource usage metrics for cost attribution"""
        metrics = {}
        
        # CPU usage by service
        cpu_query = 'sum by (service) (rate(container_cpu_usage_seconds_total[1h]))'
        cpu_result = await self.query(cpu_query)
        metrics['cpu_usage'] = {
            result['metric']['service']: float(result['value'][1])
            for result in cpu_result.get('result', [])
        }
        
        # Memory usage by service
        memory_query = 'sum by (service) (container_memory_usage_bytes)'
        memory_result = await self.query(memory_query)
        metrics['memory_usage'] = {
            result['metric']['service']: float(result['value'][1])
            for result in memory_result.get('result', [])
        }
        
        # Network I/O by service
        network_query = 'sum by (service) (rate(container_network_transmit_bytes_total[1h]) + rate(container_network_receive_bytes_total[1h]))'
        network_result = await self.query(network_query)
        metrics['network_io'] = {
            result['metric']['service']: float(result['value'][1])
            for result in network_result.get('result', [])
        }
        
        # Storage usage by service
        storage_query = 'sum by (service) (container_fs_usage_bytes)'
        storage_result = await self.query(storage_query)
        metrics['storage_usage'] = {
            result['metric']['service']: float(result['value'][1])
            for result in storage_result.get('result', [])
        }
        
        return metrics

class CostOptimizationAnalyzer:
    """Analyzes costs and provides optimization recommendations"""
    
    def __init__(self):
        self.recommendations = []
    
    def analyze_resource_utilization(self, usage_metrics: Dict[str, Any], 
                                   cost_data: List[CostData]) -> List[Dict[str, Any]]:
        """Analyze resource utilization and identify optimization opportunities"""
        recommendations = []
        
        # Create cost lookup by service
        cost_by_service = {}
        for cost in cost_data:
            service = cost.service
            if service not in cost_by_service:
                cost_by_service[service] = 0
            cost_by_service[service] += cost.cost
        
        # Analyze CPU utilization
        for service, cpu_usage in usage_metrics.get('cpu_usage', {}).items():
            if cpu_usage < 0.2:  # Less than 20% CPU utilization
                cost = cost_by_service.get(service, 0)
                recommendations.append({
                    'type': 'underutilized_cpu',
                    'service': service,
                    'current_utilization': cpu_usage,
                    'estimated_savings': cost * 0.3,  # 30% potential savings
                    'recommendation': f'Consider downsizing CPU allocation for {service}',
                    'severity': 'medium' if cost > 100 else 'low'
                })
        
        # Analyze memory utilization
        for service, memory_usage in usage_metrics.get('memory_usage', {}).items():
            if memory_usage < 0.5 * 1024 * 1024 * 1024:  # Less than 500MB
                cost = cost_by_service.get(service, 0)
                recommendations.append({
                    'type': 'underutilized_memory',
                    'service': service,
                    'current_usage_gb': memory_usage / (1024 * 1024 * 1024),
                    'estimated_savings': cost * 0.2,  # 20% potential savings
                    'recommendation': f'Consider reducing memory allocation for {service}',
                    'severity': 'low'
                })
        
        return recommendations
    
    def analyze_cost_trends(self, historical_costs: List[CostData]) -> Dict[str, Any]:
        """Analyze cost trends and identify anomalies"""
        if len(historical_costs) < 7:  # Need at least a week of data
            return {'trends': [], 'anomalies': []}
        
        # Group costs by service and date
        df = pd.DataFrame([
            {
                'service': cost.service,
                'date': cost.period_start.date(),
                'cost': cost.cost
            }
            for cost in historical_costs
        ])
        
        trends = []
        anomalies = []
        
        for service in df['service'].unique():
            service_data = df[df['service'] == service].sort_values('date')
            
            if len(service_data) >= 7:
                # Calculate week-over-week growth
                recent_week = service_data.tail(7)['cost'].mean()
                previous_week = service_data.iloc[-14:-7]['cost'].mean() if len(service_data) >= 14 else 0
                
                if previous_week > 0:
                    growth_rate = ((recent_week - previous_week) / previous_week) * 100
                    
                    trends.append({
                        'service': service,
                        'growth_rate': growth_rate,
                        'recent_average': recent_week,
                        'previous_average': previous_week
                    })
                    
                    # Flag high growth rates as anomalies
                    if growth_rate > 50:  # More than 50% increase
                        anomalies.append({
                            'service': service,
                            'type': 'cost_spike',
                            'growth_rate': growth_rate,
                            'description': f'Cost increased by {growth_rate:.1f}% in the last week'
                        })
        
        return {'trends': trends, 'anomalies': anomalies}

class CostTracker:
    """Main cost tracking service"""
    
    def __init__(self, config_path: str):
        self.config = self.load_config(config_path)
        self.aws_collector = AWSCostCollector() if self.config.get('aws', {}).get('enabled') else None
        self.prometheus_collector = PrometheusMetricsCollector(self.config['prometheus']['url'])
        self.optimizer = CostOptimizationAnalyzer()
        
        # Prometheus metrics for cost tracking
        self.registry = CollectorRegistry()
        self.cost_gauge = Gauge(
            'activelog_cost_total',
            'Total cost by service and resource type',
            ['service', 'resource_type', 'currency'],
            registry=self.registry
        )
        self.budget_usage_gauge = Gauge(
            'activelog_budget_usage_percentage',
            'Budget usage percentage',
            ['budget_name', 'service'],
            registry=self.registry
        )
        self.optimization_savings_gauge = Gauge(
            'activelog_optimization_potential_savings',
            'Potential cost savings from optimization',
            ['service', 'optimization_type'],
            registry=self.registry
        )
        
        # Database connection
        self.db_pool = None
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
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
        
        # Create cost tracking tables
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS cost_data (
                    id SERIAL PRIMARY KEY,
                    service VARCHAR(100) NOT NULL,
                    resource_type VARCHAR(50) NOT NULL,
                    cost DECIMAL(10,2) NOT NULL,
                    currency VARCHAR(3) NOT NULL,
                    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
                    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
                    tags JSONB,
                    collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS budgets (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    service VARCHAR(100) NOT NULL,
                    amount DECIMAL(10,2) NOT NULL,
                    period VARCHAR(20) NOT NULL,
                    alert_thresholds INTEGER[],
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS cost_optimizations (
                    id SERIAL PRIMARY KEY,
                    service VARCHAR(100) NOT NULL,
                    optimization_type VARCHAR(50) NOT NULL,
                    potential_savings DECIMAL(10,2) NOT NULL,
                    description TEXT,
                    severity VARCHAR(20),
                    identified_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    resolved BOOLEAN DEFAULT FALSE
                )
            ''')
    
    async def collect_aws_costs(self):
        """Collect costs from AWS"""
        if not self.aws_collector:
            return
        
        logger.info("Collecting AWS cost data...")
        
        # Get yesterday's costs (most recent complete data)
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        cost_data = await self.aws_collector.get_cost_and_usage(start_date, end_date)
        
        # Store in database
        async with self.db_pool.acquire() as conn:
            for cost in cost_data:
                await conn.execute('''
                    INSERT INTO cost_data 
                    (service, resource_type, cost, currency, period_start, period_end, tags)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT DO NOTHING
                ''', 
                cost.service, cost.resource_type, cost.cost, cost.currency,
                cost.period_start, cost.period_end, json.dumps(cost.tags)
                )
        
        logger.info(f"Stored {len(cost_data)} AWS cost records")
    
    async def update_prometheus_metrics(self):
        """Update Prometheus metrics with current cost data"""
        async with self.db_pool.acquire() as conn:
            # Get recent cost data
            costs = await conn.fetch('''
                SELECT service, resource_type, currency, SUM(cost) as total_cost
                FROM cost_data 
                WHERE period_start >= NOW() - INTERVAL '24 hours'
                GROUP BY service, resource_type, currency
            ''')
            
            for cost in costs:
                self.cost_gauge.labels(
                    service=cost['service'],
                    resource_type=cost['resource_type'],
                    currency=cost['currency']
                ).set(float(cost['total_cost']))
    
    async def check_budgets(self):
        """Check budget usage and generate alerts"""
        async with self.db_pool.acquire() as conn:
            budgets = await conn.fetch('SELECT * FROM budgets')
            
            for budget in budgets:
                # Calculate current spending for the budget period
                if budget['period'] == 'monthly':
                    period_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                elif budget['period'] == 'weekly':
                    days_since_monday = datetime.now().weekday()
                    period_start = datetime.now() - timedelta(days=days_since_monday)
                    period_start = period_start.replace(hour=0, minute=0, second=0, microsecond=0)
                elif budget['period'] == 'daily':
                    period_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                else:
                    continue
                
                current_spending = await conn.fetchval('''
                    SELECT COALESCE(SUM(cost), 0)
                    FROM cost_data 
                    WHERE service = $1 AND period_start >= $2
                ''', budget['service'], period_start)
                
                usage_percentage = (float(current_spending) / float(budget['amount'])) * 100
                
                self.budget_usage_gauge.labels(
                    budget_name=budget['name'],
                    service=budget['service']
                ).set(usage_percentage)
                
                logger.info(
                    f"Budget {budget['name']} ({budget['service']}): "
                    f"{usage_percentage:.1f}% used (${current_spending:.2f}/${budget['amount']:.2f})"
                )
    
    async def run_optimization_analysis(self):
        """Run cost optimization analysis"""
        logger.info("Running cost optimization analysis...")
        
        async with self.prometheus_collector:
            # Get resource usage metrics
            usage_metrics = await self.prometheus_collector.get_resource_usage_metrics()
            
            # Get recent cost data
            async with self.db_pool.acquire() as conn:
                cost_records = await conn.fetch('''
                    SELECT service, resource_type, cost, currency, period_start, period_end, tags
                    FROM cost_data 
                    WHERE period_start >= NOW() - INTERVAL '30 days'
                    ORDER BY period_start DESC
                ''')
                
                cost_data = [
                    CostData(
                        service=record['service'],
                        resource_type=record['resource_type'],
                        cost=float(record['cost']),
                        currency=record['currency'],
                        period_start=record['period_start'],
                        period_end=record['period_end'],
                        tags=json.loads(record['tags']) if record['tags'] else {}
                    )
                    for record in cost_records
                ]
            
            # Analyze utilization
            recommendations = self.optimizer.analyze_resource_utilization(usage_metrics, cost_data)
            
            # Store optimization recommendations
            async with self.db_pool.acquire() as conn:
                for rec in recommendations:
                    await conn.execute('''
                        INSERT INTO cost_optimizations 
                        (service, optimization_type, potential_savings, description, severity)
                        VALUES ($1, $2, $3, $4, $5)
                    ''', 
                    rec['service'], rec['type'], rec['estimated_savings'],
                    rec['recommendation'], rec['severity']
                    )
                    
                    # Update Prometheus metrics
                    self.optimization_savings_gauge.labels(
                        service=rec['service'],
                        optimization_type=rec['type']
                    ).set(rec['estimated_savings'])
            
            logger.info(f"Identified {len(recommendations)} cost optimization opportunities")
    
    async def monitoring_loop(self):
        """Main monitoring loop"""
        while True:
            try:
                await self.collect_aws_costs()
                await self.check_budgets()
                await self.update_prometheus_metrics()
                
                # Run optimization analysis every 4 hours
                if datetime.now().hour % 4 == 0:
                    await self.run_optimization_analysis()
                
                # Wait for next cycle (hourly)
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error in cost tracking loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def run(self):
        """Run the cost tracker"""
        await self.connect_database()
        await self.monitoring_loop()

def main():
    """Main entry point"""
    config_path = os.getenv('COST_CONFIG_PATH', 'cost-config.yml')
    tracker = CostTracker(config_path)
    
    try:
        asyncio.run(tracker.run())
    except KeyboardInterrupt:
        logger.info("Cost tracker stopped by user")
    except Exception as e:
        logger.error(f"Cost tracker crashed: {e}")
        raise

if __name__ == '__main__':
    main()