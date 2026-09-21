"""
Pipeline Visualization System
Provides comprehensive sales pipeline visualization and analytics
"""

import sqlite3
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
import statistics


class ChartType(Enum):
    """Chart types for pipeline visualization"""
    FUNNEL = "funnel"
    BAR = "bar"
    PIE = "pie"
    LINE = "line"
    HEATMAP = "heatmap"
    SANKEY = "sankey"


class TimeRange(Enum):
    """Time range options for analytics"""
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    CUSTOM = "custom"


@dataclass
class PipelineStage:
    """Pipeline stage data structure"""
    name: str
    order: int
    probability: float
    opportunity_count: int
    total_value: float
    avg_value: float
    conversion_rate: float
    avg_duration_days: float
    
    
@dataclass
class PipelineMetrics:
    """Pipeline metrics data structure"""
    total_pipeline_value: float
    weighted_pipeline_value: float
    total_opportunities: int
    avg_deal_size: float
    overall_conversion_rate: float
    avg_sales_cycle: float
    velocity: float
    win_rate: float


class PipelineVisualization:
    """Pipeline visualization and analytics system"""
    
    def __init__(self, db_path: str = "data/crm_sales.db"):
        self.db_path = db_path
        
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
        
    def get_pipeline_overview(self, user_id: Optional[str] = None, 
                            team_id: Optional[str] = None,
                            time_range: TimeRange = TimeRange.MONTH) -> Dict[str, Any]:
        """Get complete pipeline overview"""
        
        date_filter = self._get_date_filter(time_range)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Build WHERE clause
            where_conditions = ["o.created_at >= ?"]
            params = [date_filter]
            
            if user_id:
                where_conditions.append("o.assigned_to = ?")
                params.append(user_id)
            if team_id:
                where_conditions.append("o.team_id = ?")
                params.append(team_id)
                
            where_clause = " AND ".join(where_conditions)
            
            # Get pipeline stages with metrics
            stages_query = f"""
                SELECT 
                    ps.name,
                    ps.probability,
                    ps.stage_order,
                    COUNT(o.opportunity_id) as opportunity_count,
                    COALESCE(SUM(o.value), 0) as total_value,
                    COALESCE(AVG(o.value), 0) as avg_value,
                    COALESCE(AVG(JULIANDAY('now') - JULIANDAY(o.created_at)), 0) as avg_age_days
                FROM pipeline_stages ps
                LEFT JOIN opportunities o ON ps.stage_id = o.stage_id 
                    AND {where_clause}
                GROUP BY ps.stage_id, ps.name, ps.probability, ps.stage_order
                ORDER BY ps.stage_order
            """
            
            cursor.execute(stages_query, params)
            stages_data = cursor.fetchall()
            
            # Calculate conversion rates
            stages = []
            for i, stage in enumerate(stages_data):
                conversion_rate = 0.0
                if i < len(stages_data) - 1:  # Not the last stage
                    next_stage_count = stages_data[i + 1]['opportunity_count']
                    if stage['opportunity_count'] > 0:
                        conversion_rate = (next_stage_count / stage['opportunity_count']) * 100
                
                stages.append(PipelineStage(
                    name=stage['name'],
                    order=stage['stage_order'],
                    probability=stage['probability'],
                    opportunity_count=stage['opportunity_count'],
                    total_value=stage['total_value'],
                    avg_value=stage['avg_value'],
                    conversion_rate=conversion_rate,
                    avg_duration_days=stage['avg_age_days']
                ))
            
            # Calculate overall metrics
            metrics = self._calculate_pipeline_metrics(cursor, where_clause, params)
            
            return {
                'stages': [stage.__dict__ for stage in stages],
                'metrics': metrics.__dict__,
                'time_range': time_range.value,
                'generated_at': datetime.utcnow().isoformat()
            }
    
    def get_pipeline_funnel_data(self, user_id: Optional[str] = None,
                               time_range: TimeRange = TimeRange.MONTH) -> Dict[str, Any]:
        """Get data for pipeline funnel visualization"""
        
        date_filter = self._get_date_filter(time_range)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Build WHERE clause
            where_conditions = ["o.created_at >= ?"]
            params = [date_filter]
            
            if user_id:
                where_conditions.append("o.assigned_to = ?")
                params.append(user_id)
                
            where_clause = " AND ".join(where_conditions)
            
            # Get funnel data
            query = f"""
                SELECT 
                    ps.name,
                    ps.stage_order,
                    COUNT(o.opportunity_id) as count,
                    COALESCE(SUM(o.value), 0) as value
                FROM pipeline_stages ps
                LEFT JOIN opportunities o ON ps.stage_id = o.stage_id 
                    AND {where_clause}
                GROUP BY ps.stage_id, ps.name, ps.stage_order
                ORDER BY ps.stage_order
            """
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            funnel_data = []
            for stage in results:
                funnel_data.append({
                    'stage': stage['name'],
                    'count': stage['count'],
                    'value': stage['value'],
                    'order': stage['stage_order']
                })
                
            return {
                'chart_type': ChartType.FUNNEL.value,
                'data': funnel_data,
                'time_range': time_range.value
            }
    
    def get_pipeline_trends(self, time_range: TimeRange = TimeRange.QUARTER,
                          user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get pipeline trends over time"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Calculate time periods
            periods = self._get_time_periods(time_range)
            
            trend_data = []
            for period_start, period_end in periods:
                where_conditions = ["o.created_at >= ? AND o.created_at < ?"]
                params = [period_start, period_end]
                
                if user_id:
                    where_conditions.append("o.assigned_to = ?")
                    params.append(user_id)
                    
                where_clause = " AND ".join(where_conditions)
                
                # Get metrics for this period
                query = f"""
                    SELECT 
                        COUNT(o.opportunity_id) as total_opportunities,
                        COALESCE(SUM(o.value), 0) as total_value,
                        COALESCE(SUM(o.value * ps.probability / 100), 0) as weighted_value,
                        COALESCE(AVG(o.value), 0) as avg_deal_size
                    FROM opportunities o
                    JOIN pipeline_stages ps ON o.stage_id = ps.stage_id
                    WHERE {where_clause}
                """
                
                cursor.execute(query, params)
                result = cursor.fetchone()
                
                trend_data.append({
                    'period': period_start.strftime('%Y-%m-%d'),
                    'total_opportunities': result['total_opportunities'],
                    'total_value': result['total_value'],
                    'weighted_value': result['weighted_value'],
                    'avg_deal_size': result['avg_deal_size']
                })
                
            return {
                'chart_type': ChartType.LINE.value,
                'data': trend_data,
                'time_range': time_range.value
            }
    
    def get_win_loss_analysis(self, time_range: TimeRange = TimeRange.MONTH) -> Dict[str, Any]:
        """Get win/loss analysis"""
        
        date_filter = self._get_date_filter(time_range)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get win/loss data
            query = """
                SELECT 
                    o.status,
                    COUNT(o.opportunity_id) as count,
                    COALESCE(SUM(o.value), 0) as total_value,
                    COALESCE(AVG(o.value), 0) as avg_value,
                    COALESCE(AVG(JULIANDAY(o.updated_at) - JULIANDAY(o.created_at)), 0) as avg_cycle_days
                FROM opportunities o
                WHERE o.created_at >= ? 
                AND o.status IN ('won', 'lost', 'open')
                GROUP BY o.status
            """
            
            cursor.execute(query, [date_filter])
            results = cursor.fetchall()
            
            analysis = {}
            for result in results:
                analysis[result['status']] = {
                    'count': result['count'],
                    'total_value': result['total_value'],
                    'avg_value': result['avg_value'],
                    'avg_cycle_days': result['avg_cycle_days']
                }
            
            # Calculate win rate
            total_closed = analysis.get('won', {}).get('count', 0) + analysis.get('lost', {}).get('count', 0)
            win_rate = (analysis.get('won', {}).get('count', 0) / total_closed * 100) if total_closed > 0 else 0
            
            return {
                'analysis': analysis,
                'win_rate': win_rate,
                'total_closed': total_closed,
                'time_range': time_range.value
            }
    
    def get_sales_velocity(self, time_range: TimeRange = TimeRange.MONTH,
                          user_id: Optional[str] = None) -> Dict[str, Any]:
        """Calculate sales velocity metrics"""
        
        date_filter = self._get_date_filter(time_range)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Build WHERE clause
            where_conditions = ["o.created_at >= ?"]
            params = [date_filter]
            
            if user_id:
                where_conditions.append("o.assigned_to = ?")
                params.append(user_id)
                
            where_clause = " AND ".join(where_conditions)
            
            # Get velocity data
            query = f"""
                SELECT 
                    COUNT(CASE WHEN o.status = 'won' THEN 1 END) as deals_won,
                    COALESCE(AVG(CASE WHEN o.status = 'won' THEN o.value END), 0) as avg_deal_size,
                    COALESCE(AVG(CASE WHEN o.status = 'won' 
                        THEN JULIANDAY(o.updated_at) - JULIANDAY(o.created_at) 
                    END), 0) as avg_sales_cycle,
                    COUNT(o.opportunity_id) as total_opportunities,
                    COALESCE(AVG(ps.probability), 0) as avg_probability
                FROM opportunities o
                JOIN pipeline_stages ps ON o.stage_id = ps.stage_id
                WHERE {where_clause}
            """
            
            cursor.execute(query, params)
            result = cursor.fetchone()
            
            # Calculate velocity: (Number of deals × Average deal size × Win rate) / Sales cycle length
            deals_won = result['deals_won']
            avg_deal_size = result['avg_deal_size']
            avg_sales_cycle = max(result['avg_sales_cycle'], 1)  # Avoid division by zero
            total_opportunities = result['total_opportunities']
            win_rate = (deals_won / total_opportunities) if total_opportunities > 0 else 0
            
            velocity = (deals_won * avg_deal_size * win_rate) / avg_sales_cycle
            
            return {
                'velocity': velocity,
                'deals_won': deals_won,
                'avg_deal_size': avg_deal_size,
                'avg_sales_cycle': avg_sales_cycle,
                'win_rate': win_rate * 100,
                'total_opportunities': total_opportunities,
                'time_range': time_range.value
            }
    
    def get_pipeline_heatmap(self, time_range: TimeRange = TimeRange.MONTH) -> Dict[str, Any]:
        """Get pipeline heatmap data by stage and time period"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get weekly data for heatmap
            query = """
                SELECT 
                    ps.name as stage_name,
                    DATE(o.created_at, 'weekday 0', '-6 days') as week_start,
                    COUNT(o.opportunity_id) as opportunity_count,
                    COALESCE(SUM(o.value), 0) as total_value
                FROM opportunities o
                JOIN pipeline_stages ps ON o.stage_id = ps.stage_id
                WHERE o.created_at >= DATE('now', '-3 months')
                GROUP BY ps.stage_id, ps.name, week_start
                ORDER BY week_start, ps.stage_order
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            # Format for heatmap
            heatmap_data = []
            for result in results:
                heatmap_data.append({
                    'stage': result['stage_name'],
                    'week': result['week_start'],
                    'count': result['opportunity_count'],
                    'value': result['total_value']
                })
                
            return {
                'chart_type': ChartType.HEATMAP.value,
                'data': heatmap_data,
                'time_range': time_range.value
            }
    
    def get_conversion_matrix(self) -> Dict[str, Any]:
        """Get stage-to-stage conversion matrix"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get all stage transitions
            query = """
                SELECT 
                    ps1.name as from_stage,
                    ps2.name as to_stage,
                    COUNT(*) as transition_count
                FROM opportunity_stage_history osh1
                JOIN opportunity_stage_history osh2 ON osh1.opportunity_id = osh2.opportunity_id
                JOIN pipeline_stages ps1 ON osh1.stage_id = ps1.stage_id
                JOIN pipeline_stages ps2 ON osh2.stage_id = ps2.stage_id
                WHERE osh2.changed_at > osh1.changed_at
                AND NOT EXISTS (
                    SELECT 1 FROM opportunity_stage_history osh3 
                    WHERE osh3.opportunity_id = osh1.opportunity_id 
                    AND osh3.changed_at > osh1.changed_at 
                    AND osh3.changed_at < osh2.changed_at
                )
                GROUP BY ps1.stage_id, ps2.stage_id, ps1.name, ps2.name
                ORDER BY ps1.stage_order, ps2.stage_order
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            matrix_data = []
            for result in results:
                matrix_data.append({
                    'from_stage': result['from_stage'],
                    'to_stage': result['to_stage'],
                    'count': result['transition_count']
                })
                
            return {
                'chart_type': ChartType.SANKEY.value,
                'data': matrix_data
            }
    
    def get_pipeline_dashboard(self, user_id: Optional[str] = None,
                             team_id: Optional[str] = None) -> Dict[str, Any]:
        """Get complete pipeline dashboard data"""
        
        return {
            'overview': self.get_pipeline_overview(user_id, team_id),
            'funnel': self.get_pipeline_funnel_data(user_id),
            'trends': self.get_pipeline_trends(TimeRange.QUARTER, user_id),
            'win_loss': self.get_win_loss_analysis(),
            'velocity': self.get_sales_velocity(TimeRange.MONTH, user_id),
            'heatmap': self.get_pipeline_heatmap(),
            'conversion_matrix': self.get_conversion_matrix()
        }
    
    def generate_pipeline_report(self, report_type: str = "executive",
                               time_range: TimeRange = TimeRange.MONTH,
                               user_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate comprehensive pipeline report"""
        
        dashboard_data = self.get_pipeline_dashboard(user_id)
        
        if report_type == "executive":
            return self._generate_executive_report(dashboard_data)
        elif report_type == "detailed":
            return self._generate_detailed_report(dashboard_data)
        elif report_type == "performance":
            return self._generate_performance_report(dashboard_data, user_id)
        else:
            return dashboard_data
    
    def _calculate_pipeline_metrics(self, cursor, where_clause: str, params: List) -> PipelineMetrics:
        """Calculate overall pipeline metrics"""
        
        # Get basic metrics
        metrics_query = f"""
            SELECT 
                COUNT(o.opportunity_id) as total_opportunities,
                COALESCE(SUM(o.value), 0) as total_pipeline_value,
                COALESCE(SUM(o.value * ps.probability / 100), 0) as weighted_pipeline_value,
                COALESCE(AVG(o.value), 0) as avg_deal_size,
                COALESCE(AVG(JULIANDAY('now') - JULIANDAY(o.created_at)), 0) as avg_sales_cycle
            FROM opportunities o
            JOIN pipeline_stages ps ON o.stage_id = ps.stage_id
            WHERE {where_clause}
        """
        
        cursor.execute(metrics_query, params)
        result = cursor.fetchone()
        
        # Calculate win rate
        win_rate_query = f"""
            SELECT 
                COUNT(CASE WHEN o.status = 'won' THEN 1 END) as won_count,
                COUNT(CASE WHEN o.status IN ('won', 'lost') THEN 1 END) as total_closed
            FROM opportunities o
            WHERE {where_clause}
        """
        
        cursor.execute(win_rate_query, params)
        win_data = cursor.fetchone()
        
        win_rate = (win_data['won_count'] / win_data['total_closed'] * 100) if win_data['total_closed'] > 0 else 0
        
        # Calculate velocity
        avg_sales_cycle = max(result['avg_sales_cycle'], 1)
        velocity = (result['total_opportunities'] * result['avg_deal_size'] * (win_rate / 100)) / avg_sales_cycle
        
        # Calculate conversion rate (approximate)
        conversion_rate = win_rate  # Simplified for now
        
        return PipelineMetrics(
            total_pipeline_value=result['total_pipeline_value'],
            weighted_pipeline_value=result['weighted_pipeline_value'],
            total_opportunities=result['total_opportunities'],
            avg_deal_size=result['avg_deal_size'],
            overall_conversion_rate=conversion_rate,
            avg_sales_cycle=result['avg_sales_cycle'],
            velocity=velocity,
            win_rate=win_rate
        )
    
    def _get_date_filter(self, time_range: TimeRange) -> str:
        """Get date filter for time range"""
        
        if time_range == TimeRange.WEEK:
            return (datetime.now() - timedelta(days=7)).isoformat()
        elif time_range == TimeRange.MONTH:
            return (datetime.now() - timedelta(days=30)).isoformat()
        elif time_range == TimeRange.QUARTER:
            return (datetime.now() - timedelta(days=90)).isoformat()
        elif time_range == TimeRange.YEAR:
            return (datetime.now() - timedelta(days=365)).isoformat()
        else:
            return (datetime.now() - timedelta(days=30)).isoformat()
    
    def _get_time_periods(self, time_range: TimeRange) -> List[tuple]:
        """Get time periods for trend analysis"""
        
        periods = []
        end_date = datetime.now()
        
        if time_range == TimeRange.QUARTER:
            # Weekly periods for 3 months
            for i in range(12):
                period_end = end_date - timedelta(weeks=i)
                period_start = period_end - timedelta(weeks=1)
                periods.append((period_start, period_end))
        elif time_range == TimeRange.YEAR:
            # Monthly periods for 1 year
            for i in range(12):
                period_end = end_date - timedelta(days=30*i)
                period_start = period_end - timedelta(days=30)
                periods.append((period_start, period_end))
        else:
            # Daily periods for 1 month
            for i in range(30):
                period_end = end_date - timedelta(days=i)
                period_start = period_end - timedelta(days=1)
                periods.append((period_start, period_end))
                
        return list(reversed(periods))
    
    def _generate_executive_report(self, dashboard_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary report"""
        
        overview = dashboard_data['overview']
        velocity = dashboard_data['velocity']
        win_loss = dashboard_data['win_loss']
        
        return {
            'report_type': 'executive',
            'summary': {
                'total_pipeline_value': overview['metrics']['total_pipeline_value'],
                'weighted_pipeline_value': overview['metrics']['weighted_pipeline_value'],
                'total_opportunities': overview['metrics']['total_opportunities'],
                'win_rate': win_loss['win_rate'],
                'velocity': velocity['velocity'],
                'avg_deal_size': overview['metrics']['avg_deal_size']
            },
            'key_insights': self._generate_key_insights(dashboard_data),
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def _generate_detailed_report(self, dashboard_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed pipeline report"""
        
        return {
            'report_type': 'detailed',
            'full_dashboard': dashboard_data,
            'analysis': self._generate_pipeline_analysis(dashboard_data),
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def _generate_performance_report(self, dashboard_data: Dict[str, Any], user_id: Optional[str]) -> Dict[str, Any]:
        """Generate performance-focused report"""
        
        return {
            'report_type': 'performance',
            'user_id': user_id,
            'performance_metrics': {
                'velocity': dashboard_data['velocity'],
                'win_loss': dashboard_data['win_loss'],
                'conversion_rates': self._calculate_stage_conversion_rates(dashboard_data['overview']['stages'])
            },
            'recommendations': self._generate_performance_recommendations(dashboard_data),
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def _generate_key_insights(self, dashboard_data: Dict[str, Any]) -> List[str]:
        """Generate key insights from dashboard data"""
        
        insights = []
        
        # Analyze pipeline health
        stages = dashboard_data['overview']['stages']
        if stages:
            # Check for bottlenecks
            stage_counts = [stage['opportunity_count'] for stage in stages[:-1]]  # Exclude closed stages
            if stage_counts:
                min_count = min(stage_counts)
                max_count = max(stage_counts)
                if max_count > min_count * 3:
                    bottleneck_stage = min(stages, key=lambda x: x['opportunity_count'])
                    insights.append(f"Bottleneck detected at {bottleneck_stage['name']} stage with only {bottleneck_stage['opportunity_count']} opportunities")
        
        # Analyze win rate
        win_rate = dashboard_data['win_loss']['win_rate']
        if win_rate < 20:
            insights.append("Low win rate indicates need for better lead qualification")
        elif win_rate > 60:
            insights.append("Excellent win rate - consider expanding pipeline")
        
        # Analyze velocity
        velocity = dashboard_data['velocity']['velocity']
        if velocity > 1000:
            insights.append("Strong sales velocity indicates healthy pipeline momentum")
        elif velocity < 100:
            insights.append("Low sales velocity suggests need for process optimization")
            
        return insights
    
    def _generate_pipeline_analysis(self, dashboard_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed pipeline analysis"""
        
        return {
            'stage_analysis': self._analyze_stages(dashboard_data['overview']['stages']),
            'trend_analysis': self._analyze_trends(dashboard_data['trends']['data']),
            'performance_analysis': self._analyze_performance(dashboard_data['velocity'])
        }
    
    def _analyze_stages(self, stages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze pipeline stages"""
        
        total_opportunities = sum(stage['opportunity_count'] for stage in stages)
        total_value = sum(stage['total_value'] for stage in stages)
        
        return {
            'total_opportunities': total_opportunities,
            'total_value': total_value,
            'stage_distribution': [
                {
                    'stage': stage['name'],
                    'percentage': (stage['opportunity_count'] / total_opportunities * 100) if total_opportunities > 0 else 0,
                    'value_percentage': (stage['total_value'] / total_value * 100) if total_value > 0 else 0
                }
                for stage in stages
            ]
        }
    
    def _analyze_trends(self, trend_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze pipeline trends"""
        
        if len(trend_data) < 2:
            return {'trend': 'insufficient_data'}
        
        # Calculate trend direction
        values = [period['total_value'] for period in trend_data]
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        first_avg = statistics.mean(first_half) if first_half else 0
        second_avg = statistics.mean(second_half) if second_half else 0
        
        trend_direction = 'increasing' if second_avg > first_avg else 'decreasing'
        trend_strength = abs(second_avg - first_avg) / first_avg if first_avg > 0 else 0
        
        return {
            'trend_direction': trend_direction,
            'trend_strength': trend_strength,
            'first_half_avg': first_avg,
            'second_half_avg': second_avg
        }
    
    def _analyze_performance(self, velocity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze sales performance"""
        
        performance_score = 0
        factors = []
        
        # Score based on win rate
        win_rate = velocity_data['win_rate']
        if win_rate > 50:
            performance_score += 25
            factors.append("Strong win rate")
        elif win_rate < 20:
            performance_score -= 25
            factors.append("Low win rate needs improvement")
        
        # Score based on deal size
        avg_deal_size = velocity_data['avg_deal_size']
        if avg_deal_size > 10000:
            performance_score += 25
            factors.append("Large average deal size")
        elif avg_deal_size < 1000:
            performance_score -= 15
            factors.append("Small average deal size")
        
        # Score based on sales cycle
        sales_cycle = velocity_data['avg_sales_cycle']
        if sales_cycle < 30:
            performance_score += 20
            factors.append("Fast sales cycle")
        elif sales_cycle > 90:
            performance_score -= 20
            factors.append("Long sales cycle")
        
        return {
            'performance_score': max(0, min(100, 50 + performance_score)),
            'contributing_factors': factors
        }
    
    def _calculate_stage_conversion_rates(self, stages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate conversion rates between stages"""
        
        conversion_rates = []
        for i in range(len(stages) - 1):
            current_stage = stages[i]
            next_stage = stages[i + 1]
            
            conversion_rate = 0.0
            if current_stage['opportunity_count'] > 0:
                conversion_rate = (next_stage['opportunity_count'] / current_stage['opportunity_count']) * 100
            
            conversion_rates.append({
                'from_stage': current_stage['name'],
                'to_stage': next_stage['name'],
                'conversion_rate': conversion_rate
            })
        
        return conversion_rates
    
    def _generate_performance_recommendations(self, dashboard_data: Dict[str, Any]) -> List[str]:
        """Generate performance improvement recommendations"""
        
        recommendations = []
        
        # Analyze conversion rates
        stages = dashboard_data['overview']['stages']
        for i in range(len(stages) - 1):
            if stages[i]['conversion_rate'] < 50:
                recommendations.append(f"Focus on improving conversion from {stages[i]['name']} to {stages[i+1]['name']} (currently {stages[i]['conversion_rate']:.1f}%)")
        
        # Analyze sales cycle
        velocity = dashboard_data['velocity']
        if velocity['avg_sales_cycle'] > 60:
            recommendations.append("Consider streamlining the sales process to reduce average sales cycle")
        
        # Analyze deal size
        if velocity['avg_deal_size'] < 5000:
            recommendations.append("Focus on upselling and cross-selling to increase average deal size")
        
        return recommendations