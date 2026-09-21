"""
Workload Analyzer
Analyzes workload patterns to provide intelligent scheduling and scaling recommendations
"""

import logging
import boto3
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import statistics
import json
import numpy as np
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class WorkloadPattern(Enum):
    CONSTANT = "constant"
    BUSINESS_HOURS = "business_hours"
    NIGHT_BATCH = "night_batch"
    WEEKEND_HEAVY = "weekend_heavy"
    SEASONAL = "seasonal"
    UNPREDICTABLE = "unpredictable"

@dataclass
class WorkloadMetrics:
    cpu_utilization: float
    memory_utilization: float
    network_in: float
    network_out: float
    disk_read: float
    disk_write: float
    timestamp: datetime

@dataclass
class WorkloadAnalysis:
    instance_id: str
    pattern: WorkloadPattern
    confidence: float
    avg_utilization: Dict[str, float]
    peak_hours: List[int]
    low_hours: List[int]
    recommendations: List[Dict[str, Any]]
    cost_optimization_potential: float

class WorkloadAnalyzer:
    """Analyzes workload patterns for intelligent instance management"""
    
    def __init__(self, cloudwatch_client):
        self.cloudwatch = cloudwatch_client
        self.ec2 = boto3.client('ec2', region_name=cloudwatch_client.meta.region_name)
    
    async def analyze_workload(self, instance_ids: List[str], 
                             time_range_hours: int = 168) -> Dict[str, Any]:
        """Analyze workload patterns for multiple instances"""
        try:
            analyses = {}
            
            for instance_id in instance_ids:
                analysis = await self._analyze_single_instance(instance_id, time_range_hours)
                analyses[instance_id] = analysis
            
            # Generate collective recommendations
            collective_recommendations = self._generate_collective_recommendations(analyses)
            
            return {
                'individual_analyses': {k: self._analysis_to_dict(v) for k, v in analyses.items()},
                'collective_recommendations': collective_recommendations,
                'analysis_period': {
                    'hours': time_range_hours,
                    'start_time': (datetime.utcnow() - timedelta(hours=time_range_hours)).isoformat(),
                    'end_time': datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze workload: {e}")
            raise
    
    async def _analyze_single_instance(self, instance_id: str, 
                                     time_range_hours: int) -> WorkloadAnalysis:
        """Analyze workload pattern for a single instance"""
        try:
            # Get metrics data
            metrics_data = await self._get_metrics_data(instance_id, time_range_hours)
            
            if not metrics_data:
                return WorkloadAnalysis(
                    instance_id=instance_id,
                    pattern=WorkloadPattern.UNPREDICTABLE,
                    confidence=0.0,
                    avg_utilization={},
                    peak_hours=[],
                    low_hours=[],
                    recommendations=[],
                    cost_optimization_potential=0.0
                )
            
            # Calculate average utilization
            avg_utilization = self._calculate_average_utilization(metrics_data)
            
            # Identify pattern
            pattern, confidence = self._identify_pattern(metrics_data)
            
            # Find peak and low hours
            peak_hours, low_hours = self._identify_peak_low_hours(metrics_data)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                instance_id, pattern, avg_utilization, peak_hours, low_hours
            )
            
            # Calculate cost optimization potential
            cost_potential = self._calculate_cost_optimization_potential(
                instance_id, pattern, avg_utilization, peak_hours, low_hours
            )
            
            return WorkloadAnalysis(
                instance_id=instance_id,
                pattern=pattern,
                confidence=confidence,
                avg_utilization=avg_utilization,
                peak_hours=peak_hours,
                low_hours=low_hours,
                recommendations=recommendations,
                cost_optimization_potential=cost_potential
            )
            
        except Exception as e:
            logger.error(f"Failed to analyze instance {instance_id}: {e}")
            raise
    
    async def _get_metrics_data(self, instance_id: str, 
                              time_range_hours: int) -> List[WorkloadMetrics]:
        """Get CloudWatch metrics data for an instance"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=time_range_hours)
            
            metrics_to_fetch = {
                'CPUUtilization': 'Percent',
                'NetworkIn': 'Bytes',
                'NetworkOut': 'Bytes',
                'DiskReadBytes': 'Bytes',
                'DiskWriteBytes': 'Bytes'
            }
            
            all_metrics = {}
            
            for metric_name, unit in metrics_to_fetch.items():
                try:
                    response = self.cloudwatch.get_metric_statistics(
                        Namespace='AWS/EC2',
                        MetricName=metric_name,
                        Dimensions=[
                            {
                                'Name': 'InstanceId',
                                'Value': instance_id
                            }
                        ],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=3600,  # 1 hour periods
                        Statistics=['Average'],
                        Unit=unit
                    )
                    
                    all_metrics[metric_name] = {
                        dp['Timestamp']: dp['Average']
                        for dp in response['Datapoints']
                    }
                    
                except Exception as e:
                    logger.warning(f"Failed to get {metric_name} for {instance_id}: {e}")
                    all_metrics[metric_name] = {}
            
            # Combine metrics by timestamp
            metrics_data = []
            all_timestamps = set()
            for metric_data in all_metrics.values():
                all_timestamps.update(metric_data.keys())
            
            for timestamp in sorted(all_timestamps):
                metrics_data.append(WorkloadMetrics(
                    cpu_utilization=all_metrics.get('CPUUtilization', {}).get(timestamp, 0),
                    memory_utilization=0,  # Would need custom metric
                    network_in=all_metrics.get('NetworkIn', {}).get(timestamp, 0),
                    network_out=all_metrics.get('NetworkOut', {}).get(timestamp, 0),
                    disk_read=all_metrics.get('DiskReadBytes', {}).get(timestamp, 0),
                    disk_write=all_metrics.get('DiskWriteBytes', {}).get(timestamp, 0),
                    timestamp=timestamp
                ))
            
            return metrics_data
            
        except Exception as e:
            logger.error(f"Failed to get metrics data for {instance_id}: {e}")
            return []
    
    def _calculate_average_utilization(self, metrics_data: List[WorkloadMetrics]) -> Dict[str, float]:
        """Calculate average utilization metrics"""
        if not metrics_data:
            return {}
        
        cpu_values = [m.cpu_utilization for m in metrics_data if m.cpu_utilization > 0]
        network_in_values = [m.network_in for m in metrics_data if m.network_in > 0]
        network_out_values = [m.network_out for m in metrics_data if m.network_out > 0]
        disk_read_values = [m.disk_read for m in metrics_data if m.disk_read > 0]
        disk_write_values = [m.disk_write for m in metrics_data if m.disk_write > 0]
        
        return {
            'cpu': statistics.mean(cpu_values) if cpu_values else 0,
            'network_in': statistics.mean(network_in_values) if network_in_values else 0,
            'network_out': statistics.mean(network_out_values) if network_out_values else 0,
            'disk_read': statistics.mean(disk_read_values) if disk_read_values else 0,
            'disk_write': statistics.mean(disk_write_values) if disk_write_values else 0
        }
    
    def _identify_pattern(self, metrics_data: List[WorkloadMetrics]) -> Tuple[WorkloadPattern, float]:
        """Identify workload pattern and confidence level"""
        if not metrics_data or len(metrics_data) < 24:  # Need at least 24 hours of data
            return WorkloadPattern.UNPREDICTABLE, 0.0
        
        # Organize data by hour of day
        hourly_cpu = {}
        for metric in metrics_data:
            hour = metric.timestamp.hour
            if hour not in hourly_cpu:
                hourly_cpu[hour] = []
            hourly_cpu[hour].append(metric.cpu_utilization)
        
        # Calculate average CPU by hour
        avg_hourly_cpu = {
            hour: statistics.mean(values) 
            for hour, values in hourly_cpu.items() 
            if values
        }
        
        if not avg_hourly_cpu:
            return WorkloadPattern.UNPREDICTABLE, 0.0
        
        # Analyze patterns
        cpu_values = list(avg_hourly_cpu.values())
        cpu_std = statistics.stdev(cpu_values) if len(cpu_values) > 1 else 0
        cpu_mean = statistics.mean(cpu_values)
        
        # Constant pattern - low variation
        if cpu_std < 5 and cpu_mean > 10:
            return WorkloadPattern.CONSTANT, 0.9
        
        # Business hours pattern - high during day, low at night
        business_hours = [9, 10, 11, 12, 13, 14, 15, 16, 17]
        night_hours = [22, 23, 0, 1, 2, 3, 4, 5, 6]
        
        business_cpu = [avg_hourly_cpu.get(h, 0) for h in business_hours]
        night_cpu = [avg_hourly_cpu.get(h, 0) for h in night_hours]
        
        if business_cpu and night_cpu:
            avg_business = statistics.mean(business_cpu)
            avg_night = statistics.mean(night_cpu)
            
            if avg_business > avg_night * 1.5 and avg_business > 20:
                return WorkloadPattern.BUSINESS_HOURS, 0.8
        
        # Night batch pattern - high at night, low during day
        if night_cpu and business_cpu:
            if avg_night > avg_business * 1.5 and avg_night > 20:
                return WorkloadPattern.NIGHT_BATCH, 0.8
        
        # Organize data by day of week for weekend analysis
        if len(metrics_data) >= 168:  # At least a week of data
            daily_cpu = {}
            for metric in metrics_data:
                day = metric.timestamp.weekday()  # 0=Monday, 6=Sunday
                if day not in daily_cpu:
                    daily_cpu[day] = []
                daily_cpu[day].append(metric.cpu_utilization)
            
            avg_daily_cpu = {
                day: statistics.mean(values) 
                for day, values in daily_cpu.items() 
                if values
            }
            
            weekday_cpu = [avg_daily_cpu.get(d, 0) for d in range(5)]  # Mon-Fri
            weekend_cpu = [avg_daily_cpu.get(d, 0) for d in [5, 6]]   # Sat-Sun
            
            if weekday_cpu and weekend_cpu:
                avg_weekday = statistics.mean(weekday_cpu)
                avg_weekend = statistics.mean(weekend_cpu)
                
                if avg_weekend > avg_weekday * 1.3 and avg_weekend > 20:
                    return WorkloadPattern.WEEKEND_HEAVY, 0.7
        
        # High variation - unpredictable
        if cpu_std > cpu_mean * 0.5:
            return WorkloadPattern.UNPREDICTABLE, 0.6
        
        # Default to constant if stable but doesn't fit other patterns
        return WorkloadPattern.CONSTANT, 0.5
    
    def _identify_peak_low_hours(self, metrics_data: List[WorkloadMetrics]) -> Tuple[List[int], List[int]]:
        """Identify peak and low usage hours"""
        if not metrics_data:
            return [], []
        
        # Organize data by hour of day
        hourly_cpu = {}
        for metric in metrics_data:
            hour = metric.timestamp.hour
            if hour not in hourly_cpu:
                hourly_cpu[hour] = []
            hourly_cpu[hour].append(metric.cpu_utilization)
        
        # Calculate average CPU by hour
        avg_hourly_cpu = {
            hour: statistics.mean(values) 
            for hour, values in hourly_cpu.items() 
            if values
        }
        
        if not avg_hourly_cpu:
            return [], []
        
        # Find peak hours (top 25%)
        cpu_values = list(avg_hourly_cpu.values())
        cpu_threshold_high = np.percentile(cpu_values, 75)
        cpu_threshold_low = np.percentile(cpu_values, 25)
        
        peak_hours = [
            hour for hour, cpu in avg_hourly_cpu.items() 
            if cpu >= cpu_threshold_high
        ]
        
        low_hours = [
            hour for hour, cpu in avg_hourly_cpu.items() 
            if cpu <= cpu_threshold_low
        ]
        
        return sorted(peak_hours), sorted(low_hours)
    
    def _generate_recommendations(self, instance_id: str, pattern: WorkloadPattern,
                                avg_utilization: Dict[str, float], 
                                peak_hours: List[int], low_hours: List[int]) -> List[Dict[str, Any]]:
        """Generate recommendations based on workload analysis"""
        recommendations = []
        
        cpu_avg = avg_utilization.get('cpu', 0)
        
        # Low utilization recommendations
        if cpu_avg < 10:
            recommendations.append({
                'type': 'rightsizing',
                'priority': 'high',
                'title': 'Consider Smaller Instance Type',
                'description': f'Average CPU utilization is only {cpu_avg:.1f}%. Consider downsizing to save costs.',
                'potential_savings': '30-50%',
                'action': 'resize_instance'
            })
        
        # High utilization recommendations
        elif cpu_avg > 80:
            recommendations.append({
                'type': 'rightsizing',
                'priority': 'high',
                'title': 'Consider Larger Instance Type',
                'description': f'Average CPU utilization is {cpu_avg:.1f}%. Consider upsizing for better performance.',
                'potential_cost_increase': '50-100%',
                'action': 'resize_instance'
            })
        
        # Pattern-specific recommendations
        if pattern == WorkloadPattern.BUSINESS_HOURS:
            recommendations.append({
                'type': 'scheduling',
                'priority': 'high',
                'title': 'Implement Business Hours Scheduling',
                'description': 'Workload follows business hours pattern. Implement auto start/stop scheduling.',
                'potential_savings': '60-75%',
                'action': 'create_schedule',
                'schedule_type': 'business_hours',
                'schedule_params': {
                    'start_hour': min(peak_hours) if peak_hours else 9,
                    'end_hour': max(peak_hours) if peak_hours else 17,
                    'business_days': [0, 1, 2, 3, 4]  # Monday to Friday
                }
            })
        
        elif pattern == WorkloadPattern.NIGHT_BATCH:
            recommendations.append({
                'type': 'scheduling',
                'priority': 'medium',
                'title': 'Night Batch Processing Schedule',
                'description': 'Workload shows night batch pattern. Consider spot instances for cost savings.',
                'potential_savings': '70-90%',
                'action': 'convert_to_spot'
            })
        
        elif pattern == WorkloadPattern.WEEKEND_HEAVY:
            recommendations.append({
                'type': 'scheduling',
                'priority': 'medium',
                'title': 'Weekend Processing Pattern',
                'description': 'Higher utilization on weekends. Consider auto-scaling during weekdays.',
                'potential_savings': '40-60%',
                'action': 'weekend_schedule'
            })
        
        elif pattern == WorkloadPattern.CONSTANT and cpu_avg > 70:
            recommendations.append({
                'type': 'cost_optimization',
                'priority': 'high',
                'title': 'Reserved Instance Opportunity',
                'description': 'Constant high utilization makes this ideal for Reserved Instance pricing.',
                'potential_savings': '30-60%',
                'action': 'analyze_reserved_instance'
            })
        
        # Low hours scheduling
        if low_hours and len(low_hours) >= 8:  # 8+ hours of low usage
            recommendations.append({
                'type': 'scheduling',
                'priority': 'medium',
                'title': 'Low Usage Period Optimization',
                'description': f'Low usage during hours {low_hours}. Consider stopping instance during these periods.',
                'potential_savings': f'{len(low_hours)/24*100:.0f}%',
                'action': 'create_downtime_schedule',
                'schedule_params': {
                    'low_hours': low_hours
                }
            })
        
        return recommendations
    
    def _calculate_cost_optimization_potential(self, instance_id: str, pattern: WorkloadPattern,
                                            avg_utilization: Dict[str, float], 
                                            peak_hours: List[int], 
                                            low_hours: List[int]) -> float:
        """Calculate potential cost savings percentage"""
        cpu_avg = avg_utilization.get('cpu', 0)
        
        savings_potential = 0.0
        
        # Rightsizing savings
        if cpu_avg < 10:
            savings_potential += 40  # 40% potential savings from rightsizing
        elif cpu_avg < 25:
            savings_potential += 25  # 25% potential savings
        
        # Scheduling savings
        if pattern == WorkloadPattern.BUSINESS_HOURS:
            savings_potential += 65  # 65% potential savings from off-hours shutdown
        elif len(low_hours) >= 8:
            savings_potential += (len(low_hours) / 24) * 100  # Proportional savings
        
        # Spot instance savings (for suitable workloads)
        if pattern in [WorkloadPattern.NIGHT_BATCH, WorkloadPattern.WEEKEND_HEAVY]:
            savings_potential += 70  # Up to 70% savings with spot instances
        
        # Reserved instance savings (for constant high utilization)
        if pattern == WorkloadPattern.CONSTANT and cpu_avg > 70:
            savings_potential += 45  # 45% savings with reserved instances
        
        return min(savings_potential, 90)  # Cap at 90% potential savings
    
    def _generate_collective_recommendations(self, analyses: Dict[str, WorkloadAnalysis]) -> List[Dict[str, Any]]:
        """Generate recommendations that apply to multiple instances"""
        collective_recommendations = []
        
        # Group instances by pattern
        pattern_groups = {}
        for instance_id, analysis in analyses.items():
            pattern = analysis.pattern
            if pattern not in pattern_groups:
                pattern_groups[pattern] = []
            pattern_groups[pattern].append((instance_id, analysis))
        
        # Business hours pattern group
        if WorkloadPattern.BUSINESS_HOURS in pattern_groups:
            instances = pattern_groups[WorkloadPattern.BUSINESS_HOURS]
            if len(instances) >= 2:
                collective_recommendations.append({
                    'type': 'batch_scheduling',
                    'priority': 'high',
                    'title': 'Batch Business Hours Scheduling',
                    'description': f'{len(instances)} instances show business hours pattern. Implement coordinated scheduling.',
                    'instances': [inst[0] for inst in instances],
                    'potential_savings': '60-75%',
                    'action': 'create_batch_schedule'
                })
        
        # Low utilization group
        low_util_instances = [
            (instance_id, analysis) 
            for instance_id, analysis in analyses.items()
            if analysis.avg_utilization.get('cpu', 0) < 15
        ]
        
        if len(low_util_instances) >= 3:
            collective_recommendations.append({
                'type': 'rightsizing',
                'priority': 'high',
                'title': 'Bulk Rightsizing Opportunity',
                'description': f'{len(low_util_instances)} instances with low utilization. Consider bulk downsizing.',
                'instances': [inst[0] for inst in low_util_instances],
                'potential_savings': '30-50%',
                'action': 'bulk_rightsize'
            })
        
        # Reserved instance opportunities
        constant_high_util = [
            (instance_id, analysis)
            for instance_id, analysis in analyses.items()
            if analysis.pattern == WorkloadPattern.CONSTANT and analysis.avg_utilization.get('cpu', 0) > 60
        ]
        
        if len(constant_high_util) >= 2:
            collective_recommendations.append({
                'type': 'reserved_instances',
                'priority': 'high',
                'title': 'Reserved Instance Portfolio',
                'description': f'{len(constant_high_util)} instances suitable for Reserved Instance pricing.',
                'instances': [inst[0] for inst in constant_high_util],
                'potential_savings': '30-60%',
                'action': 'analyze_reserved_portfolio'
            })
        
        return collective_recommendations
    
    def _analysis_to_dict(self, analysis: WorkloadAnalysis) -> Dict[str, Any]:
        """Convert WorkloadAnalysis to dictionary for JSON serialization"""
        return {
            'instance_id': analysis.instance_id,
            'pattern': analysis.pattern.value,
            'confidence': analysis.confidence,
            'avg_utilization': analysis.avg_utilization,
            'peak_hours': analysis.peak_hours,
            'low_hours': analysis.low_hours,
            'recommendations': analysis.recommendations,
            'cost_optimization_potential': analysis.cost_optimization_potential
        }
    
    async def get_workload_forecast(self, instance_id: str, 
                                  forecast_hours: int = 24) -> Dict[str, Any]:
        """Generate workload forecast based on historical patterns"""
        try:
            # Get historical data for pattern analysis
            historical_data = await self._get_metrics_data(instance_id, 168)  # 1 week
            
            if not historical_data:
                return {
                    'instance_id': instance_id,
                    'forecast': [],
                    'confidence': 0.0,
                    'message': 'Insufficient historical data for forecasting'
                }
            
            # Simple pattern-based forecasting
            forecast = self._generate_simple_forecast(historical_data, forecast_hours)
            
            return {
                'instance_id': instance_id,
                'forecast_hours': forecast_hours,
                'forecast': forecast,
                'confidence': 0.7,  # Simple model confidence
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate forecast for {instance_id}: {e}")
            raise
    
    def _generate_simple_forecast(self, historical_data: List[WorkloadMetrics], 
                                forecast_hours: int) -> List[Dict[str, Any]]:
        """Generate simple pattern-based forecast"""
        # Group historical data by hour of day
        hourly_patterns = {}
        for metric in historical_data:
            hour = metric.timestamp.hour
            if hour not in hourly_patterns:
                hourly_patterns[hour] = []
            hourly_patterns[hour].append(metric.cpu_utilization)
        
        # Calculate average for each hour
        avg_hourly_cpu = {
            hour: statistics.mean(values) 
            for hour, values in hourly_patterns.items() 
            if values
        }
        
        # Generate forecast
        forecast = []
        current_time = datetime.utcnow()
        
        for i in range(forecast_hours):
            forecast_time = current_time + timedelta(hours=i)
            hour = forecast_time.hour
            
            predicted_cpu = avg_hourly_cpu.get(hour, 10)  # Default to 10% if no data
            
            forecast.append({
                'timestamp': forecast_time.isoformat(),
                'predicted_cpu': predicted_cpu,
                'confidence': 0.7
            })
        
        return forecast