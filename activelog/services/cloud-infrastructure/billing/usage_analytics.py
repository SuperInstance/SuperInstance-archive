"""
Advanced Usage Analytics and Cost Attribution System
Provides detailed cost breakdowns, resource utilization analysis, and usage insights.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
import json
import logging
import random
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

class AnalyticsPeriod(str, Enum):
    """Time periods for analytics aggregation"""
    HOURLY = "hourly"
    DAILY = "daily" 
    WEEKLY = "weekly"
    MONTHLY = "monthly"

class CostDimension(str, Enum):
    """Dimensions for cost analysis"""
    INSTANCE_TYPE = "instance_type"
    SERVICE = "service"
    REGION = "region"
    AVAILABILITY_ZONE = "availability_zone"
    TAG = "tag"
    DEPARTMENT = "department"
    PROJECT = "project"
    ENVIRONMENT = "environment"
    USER = "user"

@dataclass
class ResourceUtilization:
    """Resource utilization metrics"""
    resource_id: str
    resource_type: str
    utilization_percent: float
    peak_utilization: float
    average_utilization: float
    idle_time_minutes: int
    total_runtime_minutes: int
    cost_efficiency_score: float

@dataclass
class CostAttribution:
    """Cost attribution to specific dimensions"""
    dimension: str
    dimension_value: str
    total_cost: Decimal
    percentage_of_total: float
    resource_count: int
    average_cost_per_resource: Decimal

@dataclass
class UsagePattern:
    """Usage pattern analysis"""
    pattern_type: str
    description: str
    frequency: str
    peak_hours: List[int]
    peak_days: List[int]
    cost_impact: Decimal
    optimization_opportunity: str

@dataclass
class ComparativeAnalysis:
    """Comparative cost analysis between periods"""
    current_period: Dict[str, Any]
    previous_period: Dict[str, Any]
    cost_change: Decimal
    cost_change_percent: float
    usage_change_percent: float
    top_cost_drivers: List[Dict[str, Any]]
    savings_opportunities: List[Dict[str, Any]]

class UsageAnalytics:
    """Advanced usage analytics and cost attribution system"""
    
    def __init__(self, database_manager, billing_engine):
        self.database_manager = database_manager
        self.billing_engine = billing_engine
        
    async def get_detailed_cost_breakdown(
        self, 
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        dimensions: List[CostDimension] = None,
        min_cost_threshold: Decimal = Decimal('0.01')
    ) -> Dict[str, Any]:
        """Get detailed cost breakdown across multiple dimensions"""
        
        if dimensions is None:
            dimensions = [CostDimension.INSTANCE_TYPE, CostDimension.SERVICE, CostDimension.TAG]
            
        billing_records = await self._get_billing_records(user_id, start_date, end_date)
        
        breakdown = {
            'total_cost': Decimal('0'),
            'record_count': len(billing_records),
            'time_period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'duration_days': (end_date - start_date).days
            },
            'dimensions': {}
        }
        
        # Calculate breakdown for each dimension
        for dimension in dimensions:
            dimension_breakdown = await self._calculate_dimension_breakdown(
                billing_records, dimension, min_cost_threshold
            )
            breakdown['dimensions'][dimension.value] = dimension_breakdown
            
        # Calculate total cost  
        total_cost = Decimal('0')
        for record in billing_records:
            if hasattr(record, 'total_cost'):
                total_cost += record.total_cost
            elif hasattr(record, 'cost'):
                total_cost += record.cost
            else:
                # Tuple format - total_cost is at index 8
                total_cost += Decimal(str(record[8])) if len(record) > 8 else Decimal('0')
        breakdown['total_cost'] = total_cost
        
        return breakdown
    
    async def analyze_resource_utilization(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[ResourceUtilization]:
        """Analyze resource utilization efficiency"""
        
        instances = await self._get_user_instances(user_id, start_date, end_date)
        utilization_data = []
        
        for instance in instances:
            # Handle both tuple and object instance formats
            if hasattr(instance, 'instance_id'):
                instance_id = instance.instance_id
                instance_type = instance.instance_type
            else:
                # Tuple format - instance_id at index 0, instance_type at index 2
                instance_id = instance[0] if len(instance) > 0 else "unknown"
                instance_type = instance[2] if len(instance) > 2 else "unknown"
                
            # Get billing records for this instance
            instance_records = await self._get_instance_billing_records(
                instance_id, start_date, end_date
            )
            
            if not instance_records:
                continue
                
            # Calculate utilization metrics
            total_runtime = 0
            total_cost = Decimal('0')
            for record in instance_records:
                if hasattr(record, 'duration_minutes'):
                    total_runtime += record.duration_minutes
                    total_cost += record.total_cost if hasattr(record, 'total_cost') else record.cost
                else:
                    # Tuple format
                    total_runtime += record[6] if len(record) > 6 else 0
                    total_cost += Decimal(str(record[8])) if len(record) > 8 else Decimal('0')
            
            # Mock utilization data (in real system, get from CloudWatch/monitoring)
            avg_cpu = await self._get_average_cpu_utilization(instance_id, start_date, end_date)
            peak_cpu = await self._get_peak_cpu_utilization(instance_id, start_date, end_date)
            
            # Calculate idle time (when utilization < 5%)
            idle_time = await self._calculate_idle_time(instance_id, start_date, end_date)
            
            # Cost efficiency score (utilization vs cost)
            efficiency_score = min(avg_cpu / 70.0 * 100, 100)  # 70% utilization is optimal
            
            utilization = ResourceUtilization(
                resource_id=instance_id,
                resource_type=instance_type,
                utilization_percent=avg_cpu,
                peak_utilization=peak_cpu,
                average_utilization=avg_cpu,
                idle_time_minutes=idle_time,
                total_runtime_minutes=total_runtime,
                cost_efficiency_score=efficiency_score
            )
            
            utilization_data.append(utilization)
            
        return utilization_data
    
    async def detect_usage_patterns(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[UsagePattern]:
        """Detect usage patterns and optimization opportunities"""
        
        billing_records = await self._get_billing_records(user_id, start_date, end_date)
        patterns = []
        
        # Analyze hourly patterns
        hourly_usage = await self._analyze_hourly_patterns(billing_records)
        if hourly_usage['peak_variance'] > 0.5:
            patterns.append(UsagePattern(
                pattern_type="peak_hours",
                description=f"Usage peaks during hours {hourly_usage['peak_hours']}",
                frequency="daily",
                peak_hours=hourly_usage['peak_hours'],
                peak_days=[],
                cost_impact=hourly_usage['cost_impact'],
                optimization_opportunity="Consider scheduling non-critical workloads during off-peak hours"
            ))
        
        # Analyze weekly patterns
        weekly_usage = await self._analyze_weekly_patterns(billing_records)
        if weekly_usage['weekend_variance'] > 0.3:
            patterns.append(UsagePattern(
                pattern_type="weekend_usage",
                description="Significantly different weekend usage patterns",
                frequency="weekly",
                peak_hours=[],
                peak_days=weekly_usage['peak_days'],
                cost_impact=weekly_usage['cost_impact'],
                optimization_opportunity="Consider different scaling policies for weekends"
            ))
        
        # Detect idle resources
        idle_pattern = await self._detect_idle_resources(user_id, billing_records)
        if idle_pattern['idle_cost'] > Decimal('10.00'):
            patterns.append(UsagePattern(
                pattern_type="idle_resources",
                description=f"${idle_pattern['idle_cost']:.2f} spent on underutilized resources",
                frequency="continuous",
                peak_hours=[],
                peak_days=[],
                cost_impact=idle_pattern['idle_cost'],
                optimization_opportunity="Resize or terminate underutilized instances"
            ))
        
        return patterns
    
    async def generate_comparative_analysis(
        self,
        user_id: str,
        current_start: datetime,
        current_end: datetime,
        comparison_period: str = "previous_period"
    ) -> ComparativeAnalysis:
        """Generate comparative cost analysis between periods"""
        
        # Calculate comparison period dates
        period_duration = current_end - current_start
        if comparison_period == "previous_period":
            prev_end = current_start
            prev_start = prev_end - period_duration
        elif comparison_period == "year_over_year":
            prev_start = current_start - timedelta(days=365)
            prev_end = current_end - timedelta(days=365)
        else:
            # Default to previous period
            prev_end = current_start
            prev_start = prev_end - period_duration
        
        # Get billing data for both periods
        current_records = await self._get_billing_records(user_id, current_start, current_end)
        previous_records = await self._get_billing_records(user_id, prev_start, prev_end)
        
        # Calculate metrics for both periods
        current_metrics = await self._calculate_period_metrics(current_records)
        previous_metrics = await self._calculate_period_metrics(previous_records)
        
        # Calculate changes
        cost_change = current_metrics['total_cost'] - previous_metrics['total_cost']
        cost_change_percent = float(
            (cost_change / previous_metrics['total_cost'] * 100) if previous_metrics['total_cost'] > 0 else 0
        )
        
        usage_change_percent = (
            (current_metrics['total_usage_minutes'] - previous_metrics['total_usage_minutes']) /
            previous_metrics['total_usage_minutes'] * 100
        ) if previous_metrics['total_usage_minutes'] > 0 else 0
        
        # Identify top cost drivers
        cost_drivers = await self._identify_cost_drivers(current_records, previous_records)
        
        # Find savings opportunities
        savings_opportunities = await self._identify_savings_opportunities(
            current_records, previous_records
        )
        
        return ComparativeAnalysis(
            current_period=current_metrics,
            previous_period=previous_metrics,
            cost_change=cost_change,
            cost_change_percent=cost_change_percent,
            usage_change_percent=usage_change_percent,
            top_cost_drivers=cost_drivers,
            savings_opportunities=savings_opportunities
        )
    
    async def get_tag_based_cost_allocation(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        tag_key: str
    ) -> Dict[str, CostAttribution]:
        """Allocate costs based on resource tags"""
        
        billing_records = await self._get_billing_records(user_id, start_date, end_date)
        tag_costs = {}
        total_cost = Decimal('0')
        
        for record in billing_records:
            instance = await self._get_instance_by_id(record.instance_id)
            if not instance or not instance.tags:
                tag_value = "untagged"
            else:
                tags = json.loads(instance.tags) if isinstance(instance.tags, str) else instance.tags
                tag_value = tags.get(tag_key, "untagged")
            
            if tag_value not in tag_costs:
                tag_costs[tag_value] = {
                    'total_cost': Decimal('0'),
                    'resource_count': 0,
                    'records': []
                }
            
            tag_costs[tag_value]['total_cost'] += record.cost
            tag_costs[tag_value]['records'].append(record)
            total_cost += record.cost
        
        # Convert to CostAttribution objects
        allocations = {}
        for tag_value, data in tag_costs.items():
            unique_resources = len(set(record.instance_id for record in data['records']))
            percentage = float(data['total_cost'] / total_cost * 100) if total_cost > 0 else 0
            avg_cost_per_resource = data['total_cost'] / unique_resources if unique_resources > 0 else Decimal('0')
            
            allocations[tag_value] = CostAttribution(
                dimension=tag_key,
                dimension_value=tag_value,
                total_cost=data['total_cost'],
                percentage_of_total=percentage,
                resource_count=unique_resources,
                average_cost_per_resource=avg_cost_per_resource
            )
        
        return allocations
    
    # Helper methods
    async def _get_billing_records(self, user_id: str, start_date: datetime, end_date: datetime):
        """Get billing records for user in date range"""
        import aiosqlite
        async with aiosqlite.connect(self.database_manager.db_path) as conn:
            query = """
                SELECT * FROM billing_records 
                WHERE user_id = ? AND start_time >= ? AND end_time <= ?
                ORDER BY start_time DESC
            """
            cursor = await conn.execute(query, (user_id, start_date, end_date))
            return await cursor.fetchall()
    
    async def _calculate_dimension_breakdown(
        self, 
        billing_records, 
        dimension: CostDimension, 
        min_threshold: Decimal
    ) -> List[CostAttribution]:
        """Calculate cost breakdown for a specific dimension"""
        
        dimension_costs = {}
        total_cost = Decimal('0')
        
        for record in billing_records:
            # Handle both tuple and object record formats
            if hasattr(record, 'instance_type'):
                instance_type = record.instance_type
                service_type = getattr(record, 'service_type', 'compute')  
                cost = record.total_cost if hasattr(record, 'total_cost') else record.cost
            else:
                # Tuple format from raw SQL
                instance_type = record[3] if len(record) > 3 else "unknown"
                service_type = record[9] if len(record) > 9 else "compute"
                cost = record[8] if len(record) > 8 else Decimal('0')  # total_cost column
                
            # Get dimension value based on type
            if dimension == CostDimension.INSTANCE_TYPE:
                dim_value = instance_type or "unknown"
            elif dimension == CostDimension.SERVICE:
                dim_value = service_type or "compute"
            else:
                dim_value = "other"  # Simplified for demo
            
            if dim_value not in dimension_costs:
                dimension_costs[dim_value] = {
                    'cost': Decimal('0'),
                    'count': 0
                }
            
            dimension_costs[dim_value]['cost'] += Decimal(str(cost))
            dimension_costs[dim_value]['count'] += 1
            total_cost += Decimal(str(cost))
        
        # Create attributions
        attributions = []
        for dim_value, data in dimension_costs.items():
            if data['cost'] >= min_threshold:
                percentage = float(data['cost'] / total_cost * 100) if total_cost > 0 else 0
                avg_cost = data['cost'] / data['count'] if data['count'] > 0 else Decimal('0')
                
                attributions.append(CostAttribution(
                    dimension=dimension.value,
                    dimension_value=dim_value,
                    total_cost=data['cost'],
                    percentage_of_total=percentage,
                    resource_count=data['count'],
                    average_cost_per_resource=avg_cost
                ))
        
        return sorted(attributions, key=lambda x: x.total_cost, reverse=True)
    
    async def _get_user_instances(self, user_id: str, start_date: datetime, end_date: datetime):
        """Get user instances active during date range"""
        import aiosqlite
        async with aiosqlite.connect(self.database_manager.db_path) as conn:
            query = """
                SELECT * FROM ec2_instances 
                WHERE user_id = ? AND created_at <= ?
            """
            cursor = await conn.execute(query, (user_id, end_date))
            return await cursor.fetchall()
    
    async def _get_instance_billing_records(self, instance_id: str, start_date: datetime, end_date: datetime):
        """Get billing records for specific instance"""
        import aiosqlite
        async with aiosqlite.connect(self.database_manager.db_path) as conn:
            query = """
                SELECT * FROM billing_records 
                WHERE instance_id = ? AND start_time >= ? AND end_time <= ?
            """
            cursor = await conn.execute(query, (instance_id, start_date, end_date))
            return await cursor.fetchall()
    
    async def _get_average_cpu_utilization(self, instance_id: str, start_date: datetime, end_date: datetime) -> float:
        """Get average CPU utilization (mock implementation)"""
        # In real implementation, this would query CloudWatch or monitoring system
        import random
        return random.uniform(20, 80)
    
    async def _get_peak_cpu_utilization(self, instance_id: str, start_date: datetime, end_date: datetime) -> float:
        """Get peak CPU utilization (mock implementation)"""
        avg_cpu = await self._get_average_cpu_utilization(instance_id, start_date, end_date)
        return min(avg_cpu + random.uniform(10, 30), 100)
    
    async def _calculate_idle_time(self, instance_id: str, start_date: datetime, end_date: datetime) -> int:
        """Calculate idle time in minutes (mock implementation)"""
        total_minutes = int((end_date - start_date).total_seconds() / 60)
        avg_cpu = await self._get_average_cpu_utilization(instance_id, start_date, end_date)
        
        # Estimate idle time based on utilization
        if avg_cpu < 5:
            return int(total_minutes * 0.8)  # 80% idle
        elif avg_cpu < 20:
            return int(total_minutes * 0.4)  # 40% idle
        else:
            return int(total_minutes * 0.1)  # 10% idle
    
    async def _analyze_hourly_patterns(self, billing_records) -> Dict[str, Any]:
        """Analyze hourly usage patterns"""
        hourly_costs = {}
        
        for record in billing_records:
            # Handle both tuple and object record formats
            if hasattr(record, 'start_time'):
                start_time = record.start_time
                cost = record.total_cost if hasattr(record, 'total_cost') else record.cost
            else:
                # Tuple format - start_time at index 4, total_cost at index 8
                start_time_str = record[4] if len(record) > 4 else datetime.now().isoformat()
                start_time = datetime.fromisoformat(start_time_str) if isinstance(start_time_str, str) else start_time_str
                cost = record[8] if len(record) > 8 else Decimal('0')
                
            hour = start_time.hour
            if hour not in hourly_costs:
                hourly_costs[hour] = Decimal('0')
            hourly_costs[hour] += Decimal(str(cost))
        
        if not hourly_costs:
            return {'peak_hours': [], 'peak_variance': 0, 'cost_impact': Decimal('0')}
        
        # Find peak hours (top 25% of hours by cost)
        sorted_hours = sorted(hourly_costs.items(), key=lambda x: x[1], reverse=True)
        peak_count = max(1, len(sorted_hours) // 4)
        peak_hours = [hour for hour, cost in sorted_hours[:peak_count]]
        
        # Calculate variance
        costs = list(hourly_costs.values())
        avg_cost = sum(costs) / len(costs)
        variance = sum((cost - avg_cost) ** 2 for cost in costs) / len(costs)
        peak_variance = float(variance) / float(avg_cost) if avg_cost > 0 else 0
        
        # Calculate cost impact of peaks
        peak_cost = sum(hourly_costs.get(hour, Decimal('0')) for hour in peak_hours)
        
        return {
            'peak_hours': peak_hours,
            'peak_variance': peak_variance,
            'cost_impact': peak_cost
        }
    
    async def _analyze_weekly_patterns(self, billing_records) -> Dict[str, Any]:
        """Analyze weekly usage patterns"""
        daily_costs = {}
        
        for record in billing_records:
            # Handle both tuple and object record formats
            if hasattr(record, 'start_time'):
                start_time = record.start_time
                cost = record.total_cost if hasattr(record, 'total_cost') else record.cost
            else:
                # Tuple format - start_time at index 4, total_cost at index 8
                start_time_str = record[4] if len(record) > 4 else datetime.now().isoformat()
                start_time = datetime.fromisoformat(start_time_str) if isinstance(start_time_str, str) else start_time_str
                cost = record[8] if len(record) > 8 else Decimal('0')
                
            day = start_time.weekday()  # 0 = Monday, 6 = Sunday
            if day not in daily_costs:
                daily_costs[day] = Decimal('0')
            daily_costs[day] += Decimal(str(cost))
        
        if not daily_costs:
            return {'peak_days': [], 'weekend_variance': 0, 'cost_impact': Decimal('0')}
        
        # Calculate weekend vs weekday variance
        weekday_cost = sum(daily_costs.get(day, Decimal('0')) for day in range(5))  # Mon-Fri
        weekend_cost = sum(daily_costs.get(day, Decimal('0')) for day in range(5, 7))  # Sat-Sun
        
        total_cost = weekday_cost + weekend_cost
        weekend_variance = float(abs(weekend_cost - weekday_cost) / total_cost) if total_cost > 0 else 0
        
        # Find peak days
        sorted_days = sorted(daily_costs.items(), key=lambda x: x[1], reverse=True)
        peak_days = [day for day, cost in sorted_days[:2]]  # Top 2 days
        
        return {
            'peak_days': peak_days,
            'weekend_variance': weekend_variance,
            'cost_impact': max(weekend_cost, weekday_cost)
        }
    
    async def _detect_idle_resources(self, user_id: str, billing_records) -> Dict[str, Any]:
        """Detect idle/underutilized resources"""
        idle_cost = Decimal('0')
        
        # Group by instance
        instance_costs = {}
        for record in billing_records:
            # Handle both tuple and object record formats
            if hasattr(record, 'instance_id'):
                instance_id = record.instance_id
                cost = record.total_cost if hasattr(record, 'total_cost') else record.cost
            else:
                # Tuple format - instance_id at index 2, total_cost at index 8
                instance_id = record[2] if len(record) > 2 else "unknown"
                cost = record[8] if len(record) > 8 else Decimal('0')
            
            if instance_id not in instance_costs:
                instance_costs[instance_id] = Decimal('0')
            instance_costs[instance_id] += Decimal(str(cost))
        
        # Check utilization for each instance
        if billing_records:
            # Get date range from records
            start_times = []
            end_times = []
            for record in billing_records:
                if hasattr(record, 'start_time'):
                    start_times.append(record.start_time)
                    end_times.append(record.end_time)
                else:
                    start_time_str = record[4] if len(record) > 4 else datetime.now().isoformat()
                    end_time_str = record[5] if len(record) > 5 else datetime.now().isoformat()
                    start_times.append(datetime.fromisoformat(start_time_str) if isinstance(start_time_str, str) else start_time_str)
                    end_times.append(datetime.fromisoformat(end_time_str) if isinstance(end_time_str, str) else end_time_str)
            
            min_start = min(start_times) if start_times else datetime.now()
            max_end = max(end_times) if end_times else datetime.now()
        
        for instance_id, cost in instance_costs.items():
            avg_cpu = await self._get_average_cpu_utilization(
                instance_id, min_start, max_end
            )
            
            # Consider idle if average CPU < 10%
            if avg_cpu < 10:
                idle_cost += cost * Decimal('0.8')  # 80% of cost is waste
        
        return {'idle_cost': idle_cost}
    
    async def _calculate_period_metrics(self, billing_records) -> Dict[str, Any]:
        """Calculate metrics for a period"""
        if not billing_records:
            return {
                'total_cost': Decimal('0'),
                'total_usage_minutes': 0,
                'unique_instances': 0,
                'avg_cost_per_instance': Decimal('0')
            }
        
        total_cost = Decimal('0')
        total_usage = 0
        instance_ids = set()
        
        for record in billing_records:
            # Handle both tuple and object record formats
            if hasattr(record, 'instance_id'):
                instance_id = record.instance_id
                cost = record.total_cost if hasattr(record, 'total_cost') else record.cost
                duration = record.duration_minutes
            else:
                # Tuple format
                instance_id = record[2] if len(record) > 2 else "unknown"
                cost = record[8] if len(record) > 8 else Decimal('0')
                duration = record[6] if len(record) > 6 else 0
                
            total_cost += Decimal(str(cost))
            total_usage += duration
            instance_ids.add(instance_id)
            
        unique_instances = len(instance_ids)
        avg_cost_per_instance = total_cost / unique_instances if unique_instances > 0 else Decimal('0')
        
        return {
            'total_cost': total_cost,
            'total_usage_minutes': total_usage,
            'unique_instances': unique_instances,
            'avg_cost_per_instance': avg_cost_per_instance
        }
    
    async def _identify_cost_drivers(self, current_records, previous_records) -> List[Dict[str, Any]]:
        """Identify top cost drivers between periods"""
        # Group by instance type
        current_by_type = {}
        previous_by_type = {}
        
        for record in current_records:
            instance_type = getattr(record, 'instance_type', 'unknown')
            if instance_type not in current_by_type:
                current_by_type[instance_type] = Decimal('0')
            current_by_type[instance_type] += record.cost
        
        for record in previous_records:
            instance_type = getattr(record, 'instance_type', 'unknown')
            if instance_type not in previous_by_type:
                previous_by_type[instance_type] = Decimal('0')
            previous_by_type[instance_type] += record.cost
        
        # Calculate changes
        drivers = []
        all_types = set(current_by_type.keys()) | set(previous_by_type.keys())
        
        for instance_type in all_types:
            current_cost = current_by_type.get(instance_type, Decimal('0'))
            previous_cost = previous_by_type.get(instance_type, Decimal('0'))
            change = current_cost - previous_cost
            
            if abs(change) > Decimal('1.00'):  # Only significant changes
                drivers.append({
                    'instance_type': instance_type,
                    'cost_change': float(change),
                    'current_cost': float(current_cost),
                    'previous_cost': float(previous_cost)
                })
        
        return sorted(drivers, key=lambda x: abs(x['cost_change']), reverse=True)[:5]
    
    async def _identify_savings_opportunities(self, current_records, previous_records) -> List[Dict[str, Any]]:
        """Identify potential savings opportunities"""
        opportunities = []
        
        # Identify consistent high-cost, low-utilization instances
        instance_costs = {}
        for record in current_records:
            if record.instance_id not in instance_costs:
                instance_costs[record.instance_id] = Decimal('0')
            instance_costs[record.instance_id] += record.cost
        
        for instance_id, cost in instance_costs.items():
            if cost > Decimal('50.00'):  # High cost threshold
                avg_cpu = await self._get_average_cpu_utilization(instance_id, 
                    datetime.now() - timedelta(days=7), datetime.now())
                
                if avg_cpu < 30:  # Low utilization
                    potential_savings = cost * Decimal('0.3')  # 30% savings from right-sizing
                    opportunities.append({
                        'type': 'right_sizing',
                        'instance_id': instance_id,
                        'current_cost': float(cost),
                        'potential_savings': float(potential_savings),
                        'recommendation': f'Consider downsizing instance {instance_id[:8]}... (avg CPU: {avg_cpu:.1f}%)'
                    })
        
        return sorted(opportunities, key=lambda x: x['potential_savings'], reverse=True)[:5]
    
    async def _get_instance_by_id(self, instance_id: str):
        """Get instance by ID"""
        import aiosqlite
        async with aiosqlite.connect(self.database_manager.db_path) as conn:
            query = "SELECT * FROM ec2_instances WHERE instance_id = ?"
            cursor = await conn.execute(query, (instance_id,))
            return await cursor.fetchone()