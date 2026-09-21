"""
Advanced Report Generation System
Generates comprehensive cost and usage reports in multiple formats.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
import json
import csv
import io
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)

class ReportFormat(str, Enum):
    """Supported report formats"""
    JSON = "json"
    CSV = "csv"
    PDF = "pdf"
    EXCEL = "excel"
    HTML = "html"

class ReportType(str, Enum):
    """Types of reports available"""
    COST_SUMMARY = "cost_summary"
    DETAILED_BILLING = "detailed_billing"
    RESOURCE_UTILIZATION = "resource_utilization"
    COMPARATIVE_ANALYSIS = "comparative_analysis"
    OPTIMIZATION_REPORT = "optimization_report"
    EXECUTIVE_SUMMARY = "executive_summary"
    DEPARTMENT_BREAKDOWN = "department_breakdown"
    TREND_ANALYSIS = "trend_analysis"

@dataclass
class ReportRequest:
    """Report generation request"""
    report_type: ReportType
    format: ReportFormat
    start_date: datetime
    end_date: datetime
    filters: Optional[Dict[str, Any]] = None
    include_charts: bool = True
    include_recommendations: bool = True
    custom_fields: Optional[List[str]] = None

@dataclass
class ReportMetadata:
    """Report metadata"""
    report_id: str
    report_type: ReportType
    format: ReportFormat
    generated_at: datetime
    generated_by: str
    time_range: Dict[str, datetime]
    total_records: int
    file_size_bytes: Optional[int] = None
    generation_time_seconds: Optional[float] = None

@dataclass
class ExecutiveSummary:
    """Executive summary data"""
    total_cost: Decimal
    cost_change_percent: float
    top_cost_driver: str
    potential_savings: Decimal
    resource_efficiency_score: float
    key_insights: List[str]
    recommendations: List[str]

class ReportGenerator:
    """Advanced report generation system"""
    
    def __init__(self, database_manager, usage_analytics, billing_engine):
        self.database_manager = database_manager
        self.usage_analytics = usage_analytics
        self.billing_engine = billing_engine
    
    async def generate_report(
        self, 
        user_id: str,
        request: ReportRequest
    ) -> Dict[str, Any]:
        """Generate a comprehensive report based on request parameters"""
        
        start_time = datetime.now()
        report_id = f"rpt_{int(start_time.timestamp())}_{user_id[:8]}"
        
        try:
            logger.info(f"Generating {request.report_type} report for user {user_id}")
            
            # Generate report data based on type
            if request.report_type == ReportType.COST_SUMMARY:
                report_data = await self._generate_cost_summary(user_id, request)
            elif request.report_type == ReportType.DETAILED_BILLING:
                report_data = await self._generate_detailed_billing(user_id, request)
            elif request.report_type == ReportType.RESOURCE_UTILIZATION:
                report_data = await self._generate_utilization_report(user_id, request)
            elif request.report_type == ReportType.COMPARATIVE_ANALYSIS:
                report_data = await self._generate_comparative_report(user_id, request)
            elif request.report_type == ReportType.OPTIMIZATION_REPORT:
                report_data = await self._generate_optimization_report(user_id, request)
            elif request.report_type == ReportType.EXECUTIVE_SUMMARY:
                report_data = await self._generate_executive_summary(user_id, request)
            elif request.report_type == ReportType.TREND_ANALYSIS:
                report_data = await self._generate_trend_analysis(user_id, request)
            else:
                raise ValueError(f"Unsupported report type: {request.report_type}")
            
            # Format the report
            formatted_report = await self._format_report(report_data, request.format)
            
            # Create metadata
            generation_time = (datetime.now() - start_time).total_seconds()
            metadata = ReportMetadata(
                report_id=report_id,
                report_type=request.report_type,
                format=request.format,
                generated_at=start_time,
                generated_by=user_id,
                time_range={
                    'start': request.start_date,
                    'end': request.end_date
                },
                total_records=len(report_data.get('records', [])),
                generation_time_seconds=generation_time
            )
            
            return {
                'metadata': asdict(metadata),
                'data': report_data,
                'formatted_output': formatted_report,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return {
                'error': str(e),
                'success': False,
                'report_id': report_id
            }
    
    async def _generate_cost_summary(self, user_id: str, request: ReportRequest) -> Dict[str, Any]:
        """Generate cost summary report"""
        
        # Get billing records
        billing_records = await self._get_billing_records(user_id, request.start_date, request.end_date)
        
        # Calculate summary metrics
        total_cost = sum(record.cost for record in billing_records)
        unique_instances = len(set(record.instance_id for record in billing_records))
        total_usage_hours = sum(record.duration_minutes for record in billing_records) / 60
        
        # Get cost breakdown by service
        service_costs = {}
        instance_type_costs = {}
        daily_costs = {}
        
        for record in billing_records:
            # Service breakdown
            service = getattr(record, 'service_type', 'compute')
            service_costs[service] = service_costs.get(service, Decimal('0')) + record.cost
            
            # Instance type breakdown
            instance_type = getattr(record, 'instance_type', 'unknown')
            instance_type_costs[instance_type] = instance_type_costs.get(instance_type, Decimal('0')) + record.cost
            
            # Daily breakdown
            date_key = record.start_time.date().isoformat()
            daily_costs[date_key] = daily_costs.get(date_key, Decimal('0')) + record.cost
        
        # Get top cost drivers
        top_services = sorted(service_costs.items(), key=lambda x: x[1], reverse=True)[:5]
        top_instance_types = sorted(instance_type_costs.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Calculate trends
        period_days = (request.end_date - request.start_date).days
        avg_daily_cost = total_cost / period_days if period_days > 0 else Decimal('0')
        
        return {
            'summary': {
                'total_cost': float(total_cost),
                'unique_instances': unique_instances,
                'total_usage_hours': total_usage_hours,
                'average_daily_cost': float(avg_daily_cost),
                'period_days': period_days
            },
            'breakdowns': {
                'by_service': [
                    {'service': service, 'cost': float(cost), 'percentage': float(cost / total_cost * 100) if total_cost > 0 else 0}
                    for service, cost in top_services
                ],
                'by_instance_type': [
                    {'instance_type': itype, 'cost': float(cost), 'percentage': float(cost / total_cost * 100) if total_cost > 0 else 0}
                    for itype, cost in top_instance_types
                ]
            },
            'daily_trend': [
                {'date': date, 'cost': float(cost)}
                for date, cost in sorted(daily_costs.items())
            ],
            'records': billing_records  # For record count in metadata
        }
    
    async def _generate_detailed_billing(self, user_id: str, request: ReportRequest) -> Dict[str, Any]:
        """Generate detailed billing report with line items"""
        
        billing_records = await self._get_billing_records(user_id, request.start_date, request.end_date)
        
        # Process each record for detailed view
        detailed_records = []
        for record in billing_records:
            instance = await self._get_instance_details(record.instance_id)
            
            detailed_record = {
                'instance_id': record.instance_id,
                'instance_type': getattr(record, 'instance_type', 'unknown'),
                'service_type': getattr(record, 'service_type', 'compute'),
                'start_time': record.start_time.isoformat(),
                'end_time': record.end_time.isoformat(),
                'duration_minutes': record.duration_minutes,
                'duration_hours': round(record.duration_minutes / 60, 2),
                'cost_per_minute': float(record.cost / record.duration_minutes) if record.duration_minutes > 0 else 0,
                'total_cost': float(record.cost),
                'tags': json.loads(instance.tags) if instance and instance.tags else {},
                'region': getattr(instance, 'region', 'us-west-2') if instance else 'us-west-2'
            }
            detailed_records.append(detailed_record)
        
        # Sort by cost descending
        detailed_records.sort(key=lambda x: x['total_cost'], reverse=True)
        
        # Calculate aggregates
        total_cost = sum(record['total_cost'] for record in detailed_records)
        total_hours = sum(record['duration_hours'] for record in detailed_records)
        
        return {
            'summary': {
                'total_cost': total_cost,
                'total_hours': total_hours,
                'record_count': len(detailed_records),
                'average_cost_per_hour': total_cost / total_hours if total_hours > 0 else 0
            },
            'line_items': detailed_records,
            'records': billing_records
        }
    
    async def _generate_utilization_report(self, user_id: str, request: ReportRequest) -> Dict[str, Any]:
        """Generate resource utilization report"""
        
        utilization_data = await self.usage_analytics.analyze_resource_utilization(
            user_id, request.start_date, request.end_date
        )
        
        # Calculate efficiency metrics
        total_resources = len(utilization_data)
        efficient_resources = len([u for u in utilization_data if u.cost_efficiency_score > 70])
        underutilized_resources = len([u for u in utilization_data if u.utilization_percent < 30])
        
        efficiency_rate = (efficient_resources / total_resources * 100) if total_resources > 0 else 0
        
        # Calculate potential savings from underutilized resources
        potential_savings = Decimal('0')
        for util in utilization_data:
            if util.utilization_percent < 30 and util.idle_time_minutes > 0:
                # Estimate 50% savings from right-sizing
                runtime_cost = await self._estimate_runtime_cost(util.resource_id, util.total_runtime_minutes)
                potential_savings += runtime_cost * Decimal('0.5')
        
        # Group by resource type
        by_type = {}
        for util in utilization_data:
            resource_type = util.resource_type
            if resource_type not in by_type:
                by_type[resource_type] = {
                    'count': 0,
                    'total_utilization': 0,
                    'total_efficiency': 0,
                    'total_idle_time': 0
                }
            
            by_type[resource_type]['count'] += 1
            by_type[resource_type]['total_utilization'] += util.utilization_percent
            by_type[resource_type]['total_efficiency'] += util.cost_efficiency_score
            by_type[resource_type]['total_idle_time'] += util.idle_time_minutes
        
        # Calculate averages
        type_summary = []
        for resource_type, data in by_type.items():
            type_summary.append({
                'resource_type': resource_type,
                'count': data['count'],
                'avg_utilization': round(data['total_utilization'] / data['count'], 2),
                'avg_efficiency': round(data['total_efficiency'] / data['count'], 2),
                'total_idle_hours': round(data['total_idle_time'] / 60, 2)
            })
        
        return {
            'summary': {
                'total_resources': total_resources,
                'efficient_resources': efficient_resources,
                'underutilized_resources': underutilized_resources,
                'efficiency_rate': round(efficiency_rate, 2),
                'potential_savings': float(potential_savings)
            },
            'by_resource_type': type_summary,
            'detailed_utilization': [asdict(util) for util in utilization_data],
            'records': utilization_data
        }
    
    async def _generate_comparative_report(self, user_id: str, request: ReportRequest) -> Dict[str, Any]:
        """Generate comparative analysis report"""
        
        comparison_period = request.filters.get('comparison_period', 'previous_period') if request.filters else 'previous_period'
        
        analysis = await self.usage_analytics.generate_comparative_analysis(
            user_id, request.start_date, request.end_date, comparison_period
        )
        
        # Add insights based on the analysis
        insights = []
        if analysis.cost_change_percent > 20:
            insights.append(f"Significant cost increase of {analysis.cost_change_percent:.1f}%")
        elif analysis.cost_change_percent < -10:
            insights.append(f"Cost reduction of {abs(analysis.cost_change_percent):.1f}%")
        
        if analysis.usage_change_percent > 50:
            insights.append(f"Usage increased by {analysis.usage_change_percent:.1f}%")
        
        if len(analysis.savings_opportunities) > 0:
            total_potential = sum(opp['potential_savings'] for opp in analysis.savings_opportunities)
            insights.append(f"${total_potential:.2f} in potential savings identified")
        
        return {
            'comparison': asdict(analysis),
            'insights': insights,
            'recommendations': [
                opp['recommendation'] for opp in analysis.savings_opportunities[:3]
            ],
            'records': []  # Comparative analysis doesn't have raw records
        }
    
    async def _generate_optimization_report(self, user_id: str, request: ReportRequest) -> Dict[str, Any]:
        """Generate optimization recommendations report"""
        
        # Get usage patterns
        patterns = await self.usage_analytics.detect_usage_patterns(
            user_id, request.start_date, request.end_date
        )
        
        # Get utilization data
        utilization_data = await self.usage_analytics.analyze_resource_utilization(
            user_id, request.start_date, request.end_date
        )
        
        # Generate recommendations
        recommendations = []
        potential_savings = Decimal('0')
        
        # Right-sizing recommendations
        underutilized = [u for u in utilization_data if u.utilization_percent < 30]
        for util in underutilized:
            savings = await self._calculate_rightsizing_savings(util)
            recommendations.append({
                'type': 'right_sizing',
                'priority': 'high',
                'resource': util.resource_id,
                'current_cost_monthly': float(savings['current_monthly']),
                'optimized_cost_monthly': float(savings['optimized_monthly']),
                'potential_savings_monthly': float(savings['monthly_savings']),
                'description': f"Downsize {util.resource_type} (avg utilization: {util.utilization_percent:.1f}%)",
                'effort_level': 'low'
            })
            potential_savings += savings['monthly_savings']
        
        # Scheduling recommendations from patterns
        for pattern in patterns:
            if pattern.pattern_type == "peak_hours":
                recommendations.append({
                    'type': 'scheduling',
                    'priority': 'medium',
                    'potential_savings_monthly': float(pattern.cost_impact * 12),
                    'description': f"Schedule non-critical workloads outside peak hours {pattern.peak_hours}",
                    'effort_level': 'medium'
                })
        
        # Reserved instance recommendations (mock)
        high_usage_instances = [u for u in utilization_data if u.total_runtime_minutes > 20160]  # >2 weeks
        for util in high_usage_instances:
            savings = float(util.cost_efficiency_score * 0.3)  # 30% savings estimate
            recommendations.append({
                'type': 'reserved_instances',
                'priority': 'medium',
                'resource': util.resource_id,
                'potential_savings_monthly': savings,
                'description': f"Consider reserved instances for {util.resource_type} (high usage: {util.total_runtime_minutes/60:.0f}h)",
                'effort_level': 'low'
            })
        
        # Sort by potential savings
        recommendations.sort(key=lambda x: x.get('potential_savings_monthly', 0), reverse=True)
        
        return {
            'summary': {
                'total_recommendations': len(recommendations),
                'total_potential_savings_monthly': float(potential_savings),
                'total_potential_savings_annual': float(potential_savings * 12),
                'high_priority_count': len([r for r in recommendations if r.get('priority') == 'high'])
            },
            'recommendations': recommendations[:20],  # Top 20 recommendations
            'optimization_score': self._calculate_optimization_score(utilization_data, patterns),
            'records': patterns + utilization_data
        }
    
    async def _generate_executive_summary(self, user_id: str, request: ReportRequest) -> Dict[str, Any]:
        """Generate executive summary report"""
        
        # Get comprehensive data
        billing_records = await self._get_billing_records(user_id, request.start_date, request.end_date)
        utilization_data = await self.usage_analytics.analyze_resource_utilization(
            user_id, request.start_date, request.end_date
        )
        patterns = await self.usage_analytics.detect_usage_patterns(
            user_id, request.start_date, request.end_date
        )
        
        # Calculate key metrics
        total_cost = sum(record.cost for record in billing_records)
        
        # Previous period comparison (simplified)
        prev_start = request.start_date - (request.end_date - request.start_date)
        prev_end = request.start_date
        prev_records = await self._get_billing_records(user_id, prev_start, prev_end)
        prev_cost = sum(record.cost for record in prev_records)
        
        cost_change_percent = float((total_cost - prev_cost) / prev_cost * 100) if prev_cost > 0 else 0
        
        # Efficiency metrics
        avg_efficiency = sum(u.cost_efficiency_score for u in utilization_data) / len(utilization_data) if utilization_data else 0
        
        # Top cost driver
        instance_costs = {}
        for record in billing_records:
            itype = getattr(record, 'instance_type', 'unknown')
            instance_costs[itype] = instance_costs.get(itype, Decimal('0')) + record.cost
        
        top_cost_driver = max(instance_costs.items(), key=lambda x: x[1])[0] if instance_costs else "N/A"
        
        # Potential savings
        potential_savings = sum(pattern.cost_impact for pattern in patterns if pattern.cost_impact > 0)
        
        # Key insights
        insights = [
            f"Total infrastructure spend: ${total_cost:.2f}",
            f"Average resource efficiency: {avg_efficiency:.1f}%",
            f"Primary cost driver: {top_cost_driver}",
        ]
        
        if cost_change_percent > 0:
            insights.append(f"Cost increased by {cost_change_percent:.1f}% vs previous period")
        else:
            insights.append(f"Cost decreased by {abs(cost_change_percent):.1f}% vs previous period")
        
        # Recommendations
        recommendations = [
            "Monitor resource utilization to identify optimization opportunities",
            f"Consider right-sizing underutilized {top_cost_driver} instances",
            "Implement automated scaling policies for variable workloads"
        ]
        
        if potential_savings > 0:
            recommendations.insert(0, f"Address ${potential_savings:.2f} in identified waste")
        
        summary = ExecutiveSummary(
            total_cost=total_cost,
            cost_change_percent=cost_change_percent,
            top_cost_driver=top_cost_driver,
            potential_savings=potential_savings,
            resource_efficiency_score=avg_efficiency,
            key_insights=insights,
            recommendations=recommendations
        )
        
        return {
            'executive_summary': asdict(summary),
            'kpi_dashboard': {
                'total_cost': float(total_cost),
                'cost_change_percent': cost_change_percent,
                'efficiency_score': avg_efficiency,
                'potential_savings': float(potential_savings),
                'resource_count': len(utilization_data)
            },
            'records': billing_records
        }
    
    async def _generate_trend_analysis(self, user_id: str, request: ReportRequest) -> Dict[str, Any]:
        """Generate trend analysis report"""
        
        billing_records = await self._get_billing_records(user_id, request.start_date, request.end_date)
        
        # Group by day/week/month based on period length
        period_days = (request.end_date - request.start_date).days
        
        if period_days <= 7:
            # Daily trend
            trend_data = await self._calculate_daily_trends(billing_records)
        elif period_days <= 60:
            # Weekly trend
            trend_data = await self._calculate_weekly_trends(billing_records)
        else:
            # Monthly trend
            trend_data = await self._calculate_monthly_trends(billing_records)
        
        # Calculate trend statistics
        costs = [data['cost'] for data in trend_data['trend']]
        if len(costs) > 1:
            trend_direction = "increasing" if costs[-1] > costs[0] else "decreasing"
            trend_slope = (costs[-1] - costs[0]) / len(costs) if len(costs) > 1 else 0
        else:
            trend_direction = "stable"
            trend_slope = 0
        
        # Forecast next period (simple linear extrapolation)
        if len(costs) >= 3 and trend_slope != 0:
            forecast = costs[-1] + trend_slope
        else:
            forecast = costs[-1] if costs else 0
        
        return {
            'trend_analysis': trend_data,
            'statistics': {
                'trend_direction': trend_direction,
                'trend_slope': trend_slope,
                'forecast_next_period': forecast,
                'volatility': self._calculate_volatility(costs)
            },
            'records': billing_records
        }
    
    # Helper methods
    async def _get_billing_records(self, user_id: str, start_date: datetime, end_date: datetime):
        """Get billing records for the specified period"""
        import aiosqlite
        async with aiosqlite.connect(self.database_manager.db_path) as conn:
            query = """
                SELECT * FROM billing_records 
                WHERE user_id = ? AND start_time >= ? AND end_time <= ?
                ORDER BY start_time DESC
            """
            cursor = await conn.execute(query, (user_id, start_date, end_date))
            return await cursor.fetchall()
    
    async def _get_instance_details(self, instance_id: str):
        """Get instance details by ID"""
        import aiosqlite
        async with aiosqlite.connect(self.database_manager.db_path) as conn:
            query = "SELECT * FROM ec2_instances WHERE instance_id = ?"
            cursor = await conn.execute(query, (instance_id,))
            return await cursor.fetchone()
    
    async def _estimate_runtime_cost(self, instance_id: str, runtime_minutes: int) -> Decimal:
        """Estimate the cost for a given runtime (mock implementation)"""
        # In real implementation, this would calculate based on instance type and pricing
        return Decimal(str(runtime_minutes * 0.01))  # $0.01 per minute estimate
    
    async def _calculate_rightsizing_savings(self, util) -> Dict[str, Decimal]:
        """Calculate potential savings from right-sizing"""
        # Mock calculation - in real implementation would use actual pricing
        current_monthly = Decimal('100')  # Estimate based on utilization
        optimized_monthly = current_monthly * Decimal('0.6')  # 40% savings
        savings = current_monthly - optimized_monthly
        
        return {
            'current_monthly': current_monthly,
            'optimized_monthly': optimized_monthly,
            'monthly_savings': savings
        }
    
    def _calculate_optimization_score(self, utilization_data, patterns) -> float:
        """Calculate overall optimization score (0-100)"""
        if not utilization_data:
            return 50.0  # Default score
        
        avg_efficiency = sum(u.cost_efficiency_score for u in utilization_data) / len(utilization_data)
        
        # Penalize for waste patterns
        waste_penalty = len([p for p in patterns if 'idle' in p.pattern_type or 'underutilized' in p.description]) * 10
        
        score = max(0, avg_efficiency - waste_penalty)
        return min(100, score)
    
    async def _calculate_daily_trends(self, billing_records) -> Dict[str, Any]:
        """Calculate daily cost trends"""
        daily_costs = {}
        
        for record in billing_records:
            date_key = record.start_time.date().isoformat()
            if date_key not in daily_costs:
                daily_costs[date_key] = Decimal('0')
            daily_costs[date_key] += record.cost
        
        trend = [
            {'period': date, 'cost': float(cost)}
            for date, cost in sorted(daily_costs.items())
        ]
        
        return {
            'period_type': 'daily',
            'trend': trend,
            'total_periods': len(trend)
        }
    
    async def _calculate_weekly_trends(self, billing_records) -> Dict[str, Any]:
        """Calculate weekly cost trends"""
        weekly_costs = {}
        
        for record in billing_records:
            # Get the start of the week (Monday)
            week_start = record.start_time.date() - timedelta(days=record.start_time.weekday())
            week_key = week_start.isoformat()
            
            if week_key not in weekly_costs:
                weekly_costs[week_key] = Decimal('0')
            weekly_costs[week_key] += record.cost
        
        trend = [
            {'period': f"Week of {date}", 'cost': float(cost)}
            for date, cost in sorted(weekly_costs.items())
        ]
        
        return {
            'period_type': 'weekly',
            'trend': trend,
            'total_periods': len(trend)
        }
    
    async def _calculate_monthly_trends(self, billing_records) -> Dict[str, Any]:
        """Calculate monthly cost trends"""
        monthly_costs = {}
        
        for record in billing_records:
            month_key = record.start_time.strftime('%Y-%m')
            
            if month_key not in monthly_costs:
                monthly_costs[month_key] = Decimal('0')
            monthly_costs[month_key] += record.cost
        
        trend = [
            {'period': date, 'cost': float(cost)}
            for date, cost in sorted(monthly_costs.items())
        ]
        
        return {
            'period_type': 'monthly',
            'trend': trend,
            'total_periods': len(trend)
        }
    
    def _calculate_volatility(self, costs: List[float]) -> float:
        """Calculate cost volatility (coefficient of variation)"""
        if len(costs) < 2:
            return 0.0
        
        mean = sum(costs) / len(costs)
        variance = sum((cost - mean) ** 2 for cost in costs) / len(costs)
        std_dev = variance ** 0.5
        
        return (std_dev / mean * 100) if mean > 0 else 0.0
    
    async def _format_report(self, data: Dict[str, Any], format: ReportFormat) -> Union[str, bytes]:
        """Format report data according to specified format"""
        
        if format == ReportFormat.JSON:
            return json.dumps(data, indent=2, default=str)
        
        elif format == ReportFormat.CSV:
            return await self._generate_csv(data)
        
        elif format == ReportFormat.HTML:
            return await self._generate_html(data)
        
        else:
            # For now, default to JSON for unsupported formats
            return json.dumps(data, indent=2, default=str)
    
    async def _generate_csv(self, data: Dict[str, Any]) -> str:
        """Generate CSV format report"""
        output = io.StringIO()
        
        # Handle different data structures
        if 'line_items' in data:
            # Detailed billing report
            fieldnames = ['instance_id', 'instance_type', 'start_time', 'duration_hours', 'total_cost']
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for item in data['line_items']:
                writer.writerow({
                    'instance_id': item['instance_id'],
                    'instance_type': item['instance_type'],
                    'start_time': item['start_time'],
                    'duration_hours': item['duration_hours'],
                    'total_cost': item['total_cost']
                })
        
        elif 'daily_trend' in data:
            # Cost summary with trends
            fieldnames = ['date', 'cost']
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for trend_item in data['daily_trend']:
                writer.writerow(trend_item)
        
        else:
            # Generic format
            fieldnames = ['metric', 'value']
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for key, value in data.get('summary', {}).items():
                writer.writerow({'metric': key, 'value': value})
        
        return output.getvalue()
    
    async def _generate_html(self, data: Dict[str, Any]) -> str:
        """Generate HTML format report"""
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Cloud Infrastructure Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #f4f4f4; padding: 20px; margin-bottom: 20px; }}
                .summary {{ background: #e8f4fd; padding: 15px; margin-bottom: 20px; }}
                .metric {{ display: inline-block; margin: 10px; padding: 10px; background: white; border: 1px solid #ddd; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Cloud Infrastructure Report</h1>
                <p>Generated: {generated_at}</p>
            </div>
            
            <div class="summary">
                <h2>Summary</h2>
                {summary_content}
            </div>
            
            {detail_content}
        </body>
        </html>
        """
        
        # Generate summary content
        summary_content = ""
        if 'summary' in data:
            for key, value in data['summary'].items():
                summary_content += f'<div class="metric"><strong>{key.replace("_", " ").title()}:</strong> {value}</div>'
        
        # Generate detail content
        detail_content = ""
        if 'line_items' in data:
            detail_content = "<h2>Detailed Billing</h2><table><tr><th>Instance ID</th><th>Instance Type</th><th>Duration (h)</th><th>Cost</th></tr>"
            for item in data['line_items'][:50]:  # Limit to first 50 items
                detail_content += f"<tr><td>{item['instance_id'][:12]}...</td><td>{item['instance_type']}</td><td>{item['duration_hours']}</td><td>${item['total_cost']:.2f}</td></tr>"
            detail_content += "</table>"
        
        return html_template.format(
            generated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            summary_content=summary_content,
            detail_content=detail_content
        )