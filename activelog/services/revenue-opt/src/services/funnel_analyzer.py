import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

class FunnelStage(Enum):
    AWARENESS = "awareness"
    INTEREST = "interest"
    CONSIDERATION = "consideration"
    INTENT = "intent"
    EVALUATION = "evaluation"
    PURCHASE = "purchase"
    RETENTION = "retention"
    ADVOCACY = "advocacy"

@dataclass
class FunnelStageMetrics:
    stage: str
    total_users: int
    converted_users: int
    conversion_rate: float
    drop_off_rate: float
    average_time_in_stage: float
    revenue_impact: float
    top_drop_off_reasons: List[str]

@dataclass
class CohortFunnelAnalysis:
    cohort_id: str
    cohort_date: str
    total_users: int
    stage_metrics: Dict[str, FunnelStageMetrics]
    overall_conversion_rate: float
    average_conversion_time: float
    revenue_per_user: float

class FunnelAnalyzer:
    def __init__(self):
        self.default_funnel = [
            FunnelStage.AWARENESS,
            FunnelStage.INTEREST,
            FunnelStage.CONSIDERATION,
            FunnelStage.INTENT,
            FunnelStage.EVALUATION,
            FunnelStage.PURCHASE
        ]
        self.user_journeys = {}
        self.cohort_data = {}
        self.funnel_configurations = {}
    
    async def define_custom_funnel(self, funnel_name: str, stages: List[str], stage_configs: Dict) -> Dict:
        """Define a custom conversion funnel"""
        try:
            funnel_config = {
                'name': funnel_name,
                'stages': stages,
                'stage_configs': stage_configs,
                'created_at': datetime.now().isoformat()
            }
            
            self.funnel_configurations[funnel_name] = funnel_config
            
            return {
                'success': True,
                'funnel_name': funnel_name,
                'stages': stages,
                'config': funnel_config
            }
        
        except Exception as e:
            logger.error(f"Error defining custom funnel: {e}")
            return {'success': False, 'error': str(e)}
    
    async def track_user_journey(self, user_id: str, stage: str, metadata: Dict = None) -> Dict:
        """Track a user's progression through the funnel"""
        try:
            timestamp = datetime.now()
            
            if user_id not in self.user_journeys:
                self.user_journeys[user_id] = {
                    'user_id': user_id,
                    'stages': [],
                    'first_seen': timestamp.isoformat(),
                    'last_updated': timestamp.isoformat(),
                    'conversion_completed': False,
                    'total_revenue': 0.0
                }
            
            journey = self.user_journeys[user_id]
            
            # Add stage progression
            stage_entry = {
                'stage': stage,
                'timestamp': timestamp.isoformat(),
                'metadata': metadata or {}
            }
            
            journey['stages'].append(stage_entry)
            journey['last_updated'] = timestamp.isoformat()
            
            # Check if this is a conversion
            if stage == FunnelStage.PURCHASE.value:
                journey['conversion_completed'] = True
                if metadata and 'revenue' in metadata:
                    journey['total_revenue'] += metadata['revenue']
            
            return {
                'success': True,
                'user_id': user_id,
                'current_stage': stage,
                'journey_length': len(journey['stages']),
                'conversion_completed': journey['conversion_completed']
            }
        
        except Exception as e:
            logger.error(f"Error tracking user journey: {e}")
            return {'success': False, 'error': str(e)}
    
    async def analyze_funnel_performance(self, 
                                       funnel_name: str = "default",
                                       time_period_days: int = 30,
                                       cohort_analysis: bool = True) -> Dict:
        """Perform comprehensive funnel analysis"""
        try:
            # Get funnel configuration
            if funnel_name == "default":
                stages = [stage.value for stage in self.default_funnel]
            else:
                if funnel_name not in self.funnel_configurations:
                    return {'success': False, 'error': 'Funnel configuration not found'}
                stages = self.funnel_configurations[funnel_name]['stages']
            
            # Get user journeys for analysis period
            end_date = datetime.now()
            start_date = end_date - timedelta(days=time_period_days)
            
            relevant_journeys = await self._get_journeys_in_period(start_date, end_date)
            
            # Analyze each stage
            stage_metrics = {}
            for i, stage in enumerate(stages):
                metrics = await self._analyze_stage_performance(
                    stage, relevant_journeys, stages[:i+1]
                )
                stage_metrics[stage] = metrics
            
            # Calculate overall funnel metrics
            overall_metrics = await self._calculate_overall_funnel_metrics(relevant_journeys, stages)
            
            # Identify bottlenecks
            bottlenecks = await self._identify_bottlenecks(stage_metrics)
            
            # Generate optimization recommendations
            recommendations = await self._generate_optimization_recommendations(stage_metrics, bottlenecks)
            
            # Cohort analysis if requested
            cohort_analysis_results = None
            if cohort_analysis:
                cohort_analysis_results = await self._perform_cohort_analysis(relevant_journeys, stages)
            
            return {
                'success': True,
                'funnel_name': funnel_name,
                'analysis_period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': time_period_days
                },
                'stage_metrics': stage_metrics,
                'overall_metrics': overall_metrics,
                'bottlenecks': bottlenecks,
                'recommendations': recommendations,
                'cohort_analysis': cohort_analysis_results
            }
        
        except Exception as e:
            logger.error(f"Error analyzing funnel performance: {e}")
            return {'success': False, 'error': str(e)}
    
    async def identify_drop_off_points(self, funnel_name: str = "default") -> List[Dict]:
        """Identify major drop-off points in the funnel"""
        try:
            # Get all user journeys
            all_journeys = list(self.user_journeys.values())
            
            if funnel_name == "default":
                stages = [stage.value for stage in self.default_funnel]
            else:
                stages = self.funnel_configurations[funnel_name]['stages']
            
            drop_off_points = []
            
            for i in range(len(stages) - 1):
                current_stage = stages[i]
                next_stage = stages[i + 1]
                
                # Count users who reached current stage
                current_stage_users = len([
                    j for j in all_journeys 
                    if any(s['stage'] == current_stage for s in j['stages'])
                ])
                
                # Count users who reached next stage
                next_stage_users = len([
                    j for j in all_journeys 
                    if any(s['stage'] == next_stage for s in j['stages'])
                ])
                
                if current_stage_users > 0:
                    drop_off_rate = (current_stage_users - next_stage_users) / current_stage_users
                    
                    if drop_off_rate > 0.1:  # Significant drop-off (>10%)
                        # Analyze reasons for drop-off
                        drop_off_reasons = await self._analyze_drop_off_reasons(current_stage, next_stage)
                        
                        drop_off_points.append({
                            'from_stage': current_stage,
                            'to_stage': next_stage,
                            'users_at_current_stage': current_stage_users,
                            'users_at_next_stage': next_stage_users,
                            'drop_off_count': current_stage_users - next_stage_users,
                            'drop_off_rate': drop_off_rate,
                            'severity': 'high' if drop_off_rate > 0.3 else 'medium' if drop_off_rate > 0.2 else 'low',
                            'potential_reasons': drop_off_reasons
                        })
            
            # Sort by drop-off rate (highest first)
            drop_off_points.sort(key=lambda x: x['drop_off_rate'], reverse=True)
            
            return drop_off_points
        
        except Exception as e:
            logger.error(f"Error identifying drop-off points: {e}")
            return []
    
    async def calculate_stage_conversion_rates(self, time_period_days: int = 30) -> Dict[str, float]:
        """Calculate conversion rates for each funnel stage"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=time_period_days)
            
            relevant_journeys = await self._get_journeys_in_period(start_date, end_date)
            
            stage_conversion_rates = {}
            stages = [stage.value for stage in self.default_funnel]
            
            for stage in stages:
                # Count users who reached this stage
                users_in_stage = len([
                    j for j in relevant_journeys 
                    if any(s['stage'] == stage for s in j['stages'])
                ])
                
                # Count users who converted (reached purchase stage)
                converted_users = len([
                    j for j in relevant_journeys 
                    if any(s['stage'] == stage for s in j['stages']) and j['conversion_completed']
                ])
                
                conversion_rate = converted_users / max(users_in_stage, 1)
                stage_conversion_rates[stage] = conversion_rate
            
            return stage_conversion_rates
        
        except Exception as e:
            logger.error(f"Error calculating stage conversion rates: {e}")
            return {}
    
    async def optimize_funnel_stage(self, stage: str, optimization_type: str = "conversion_rate") -> Dict:
        """Generate specific optimization recommendations for a funnel stage"""
        try:
            # Analyze current stage performance
            stage_data = await self._get_stage_performance_data(stage)
            
            optimizations = []
            
            if optimization_type == "conversion_rate":
                optimizations.extend(await self._generate_conversion_rate_optimizations(stage, stage_data))
            elif optimization_type == "time_in_stage":
                optimizations.extend(await self._generate_time_optimization(stage, stage_data))
            elif optimization_type == "drop_off_reduction":
                optimizations.extend(await self._generate_drop_off_reduction_optimizations(stage, stage_data))
            
            # Prioritize optimizations by impact and effort
            prioritized_optimizations = await self._prioritize_optimizations(optimizations)
            
            return {
                'success': True,
                'stage': stage,
                'optimization_type': optimization_type,
                'current_performance': stage_data,
                'optimizations': prioritized_optimizations
            }
        
        except Exception as e:
            logger.error(f"Error optimizing funnel stage: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _get_journeys_in_period(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get user journeys within specified time period"""
        relevant_journeys = []
        
        for journey in self.user_journeys.values():
            first_seen = datetime.fromisoformat(journey['first_seen'])
            if start_date <= first_seen <= end_date:
                relevant_journeys.append(journey)
        
        return relevant_journeys
    
    async def _analyze_stage_performance(self, stage: str, journeys: List[Dict], previous_stages: List[str]) -> FunnelStageMetrics:
        """Analyze performance metrics for a specific stage"""
        # Count users who reached this stage
        users_in_stage = [j for j in journeys if any(s['stage'] == stage for s in j['stages'])]
        total_users = len(users_in_stage)
        
        # Count users who progressed beyond this stage
        next_stage_index = len(previous_stages)
        if next_stage_index < len(self.default_funnel):
            next_stages = [s.value for s in self.default_funnel[next_stage_index:]]
            converted_users = len([
                j for j in users_in_stage 
                if any(any(s['stage'] == ns for ns in next_stages) for s in j['stages'])
            ])
        else:
            converted_users = len([j for j in users_in_stage if j['conversion_completed']])
        
        conversion_rate = converted_users / max(total_users, 1)
        drop_off_rate = 1 - conversion_rate
        
        # Calculate average time in stage (mock calculation)
        average_time_in_stage = np.random.uniform(1, 7) if total_users > 0 else 0
        
        # Calculate revenue impact
        revenue_impact = sum(j['total_revenue'] for j in users_in_stage)
        
        # Identify top drop-off reasons (mock data)
        drop_off_reasons = await self._get_drop_off_reasons_for_stage(stage)
        
        return FunnelStageMetrics(
            stage=stage,
            total_users=total_users,
            converted_users=converted_users,
            conversion_rate=conversion_rate,
            drop_off_rate=drop_off_rate,
            average_time_in_stage=average_time_in_stage,
            revenue_impact=revenue_impact,
            top_drop_off_reasons=drop_off_reasons
        )
    
    async def _calculate_overall_funnel_metrics(self, journeys: List[Dict], stages: List[str]) -> Dict:
        """Calculate overall funnel performance metrics"""
        total_users = len(journeys)
        converted_users = len([j for j in journeys if j['conversion_completed']])
        
        overall_conversion_rate = converted_users / max(total_users, 1)
        
        # Calculate average time to conversion
        conversion_times = []
        for journey in journeys:
            if journey['conversion_completed'] and len(journey['stages']) >= 2:
                first_stage = datetime.fromisoformat(journey['stages'][0]['timestamp'])
                last_stage = datetime.fromisoformat(journey['stages'][-1]['timestamp'])
                conversion_time = (last_stage - first_stage).total_seconds() / 3600  # Hours
                conversion_times.append(conversion_time)
        
        average_conversion_time = np.mean(conversion_times) if conversion_times else 0
        
        # Calculate revenue metrics
        total_revenue = sum(j['total_revenue'] for j in journeys)
        revenue_per_user = total_revenue / max(total_users, 1)
        
        return {
            'total_users': total_users,
            'converted_users': converted_users,
            'overall_conversion_rate': overall_conversion_rate,
            'average_conversion_time_hours': average_conversion_time,
            'total_revenue': total_revenue,
            'revenue_per_user': revenue_per_user
        }
    
    async def _identify_bottlenecks(self, stage_metrics: Dict) -> List[Dict]:
        """Identify bottleneck stages in the funnel"""
        bottlenecks = []
        
        for stage, metrics in stage_metrics.items():
            # Consider a stage a bottleneck if drop-off rate > 50% or conversion rate < 20%
            if metrics.drop_off_rate > 0.5 or metrics.conversion_rate < 0.2:
                severity = 'critical' if metrics.drop_off_rate > 0.7 else 'high' if metrics.drop_off_rate > 0.5 else 'medium'
                
                bottlenecks.append({
                    'stage': stage,
                    'severity': severity,
                    'drop_off_rate': metrics.drop_off_rate,
                    'conversion_rate': metrics.conversion_rate,
                    'users_affected': metrics.total_users - metrics.converted_users,
                    'revenue_at_risk': metrics.revenue_impact * (1 - metrics.conversion_rate)
                })
        
        # Sort by severity and revenue impact
        bottlenecks.sort(key=lambda x: (x['severity'], x['revenue_at_risk']), reverse=True)
        
        return bottlenecks
    
    async def _generate_optimization_recommendations(self, stage_metrics: Dict, bottlenecks: List[Dict]) -> List[Dict]:
        """Generate optimization recommendations based on analysis"""
        recommendations = []
        
        for bottleneck in bottlenecks[:3]:  # Top 3 bottlenecks
            stage = bottleneck['stage']
            
            if stage == FunnelStage.AWARENESS.value:
                recommendations.append({
                    'stage': stage,
                    'type': 'traffic_optimization',
                    'recommendation': 'Increase top-of-funnel traffic through SEO and paid advertising',
                    'potential_impact': 'high',
                    'effort': 'medium'
                })
            elif stage == FunnelStage.INTEREST.value:
                recommendations.append({
                    'stage': stage,
                    'type': 'content_optimization',
                    'recommendation': 'Improve landing page content and value proposition clarity',
                    'potential_impact': 'high',
                    'effort': 'low'
                })
            elif stage == FunnelStage.CONSIDERATION.value:
                recommendations.append({
                    'stage': stage,
                    'type': 'social_proof',
                    'recommendation': 'Add testimonials, reviews, and trust signals',
                    'potential_impact': 'medium',
                    'effort': 'low'
                })
            elif stage == FunnelStage.EVALUATION.value:
                recommendations.append({
                    'stage': stage,
                    'type': 'friction_reduction',
                    'recommendation': 'Simplify evaluation process and provide comparison tools',
                    'potential_impact': 'high',
                    'effort': 'medium'
                })
            elif stage == FunnelStage.PURCHASE.value:
                recommendations.append({
                    'stage': stage,
                    'type': 'checkout_optimization',
                    'recommendation': 'Optimize checkout flow and reduce form fields',
                    'potential_impact': 'high',
                    'effort': 'medium'
                })
        
        return recommendations
    
    async def _perform_cohort_analysis(self, journeys: List[Dict], stages: List[str]) -> Dict:
        """Perform cohort analysis on funnel performance"""
        # Group journeys by month
        cohorts = {}
        
        for journey in journeys:
            first_seen = datetime.fromisoformat(journey['first_seen'])
            cohort_key = f"{first_seen.year}-{first_seen.month:02d}"
            
            if cohort_key not in cohorts:
                cohorts[cohort_key] = []
            
            cohorts[cohort_key].append(journey)
        
        # Analyze each cohort
        cohort_analysis = {}
        
        for cohort_key, cohort_journeys in cohorts.items():
            total_users = len(cohort_journeys)
            converted_users = len([j for j in cohort_journeys if j['conversion_completed']])
            
            overall_conversion_rate = converted_users / max(total_users, 1)
            
            # Calculate stage metrics for cohort
            stage_metrics = {}
            for stage in stages:
                metrics = await self._analyze_stage_performance(stage, cohort_journeys, stages[:stages.index(stage)+1])
                stage_metrics[stage] = metrics.__dict__
            
            cohort_analysis[cohort_key] = {
                'total_users': total_users,
                'converted_users': converted_users,
                'overall_conversion_rate': overall_conversion_rate,
                'stage_metrics': stage_metrics
            }
        
        return cohort_analysis
    
    async def _analyze_drop_off_reasons(self, current_stage: str, next_stage: str) -> List[str]:
        """Analyze reasons for drop-off between stages"""
        # Mock implementation - would analyze actual user behavior data
        drop_off_reasons = {
            (FunnelStage.AWARENESS.value, FunnelStage.INTEREST.value): [
                'Poor ad targeting', 'Irrelevant landing page', 'Slow page load'
            ],
            (FunnelStage.INTEREST.value, FunnelStage.CONSIDERATION.value): [
                'Unclear value proposition', 'Missing social proof', 'Complex messaging'
            ],
            (FunnelStage.CONSIDERATION.value, FunnelStage.INTENT.value): [
                'Price concerns', 'Feature comparison needed', 'Trust issues'
            ],
            (FunnelStage.INTENT.value, FunnelStage.EVALUATION.value): [
                'Long evaluation process', 'Missing information', 'Competitor research'
            ],
            (FunnelStage.EVALUATION.value, FunnelStage.PURCHASE.value): [
                'Checkout friction', 'Payment issues', 'Last-minute doubts'
            ]
        }
        
        return drop_off_reasons.get((current_stage, next_stage), ['Unknown factors'])
    
    async def _get_drop_off_reasons_for_stage(self, stage: str) -> List[str]:
        """Get top drop-off reasons for a specific stage"""
        # Mock implementation
        stage_reasons = {
            FunnelStage.AWARENESS.value: ['Poor targeting', 'Ad fatigue', 'Irrelevant content'],
            FunnelStage.INTEREST.value: ['Unclear value prop', 'Poor UX', 'Slow loading'],
            FunnelStage.CONSIDERATION.value: ['Price sensitivity', 'Feature gaps', 'Competitor comparison'],
            FunnelStage.INTENT.value: ['Trust concerns', 'Complex process', 'Information overload'],
            FunnelStage.EVALUATION.value: ['Long sales cycle', 'Budget constraints', 'Decision paralysis'],
            FunnelStage.PURCHASE.value: ['Checkout friction', 'Payment failures', 'Security concerns']
        }
        
        return stage_reasons.get(stage, ['Various factors'])
    
    async def _get_stage_performance_data(self, stage: str) -> Dict:
        """Get detailed performance data for a stage"""
        # Mock implementation
        return {
            'conversion_rate': np.random.uniform(0.1, 0.8),
            'average_time_in_stage': np.random.uniform(1, 10),
            'drop_off_rate': np.random.uniform(0.2, 0.7),
            'user_count': np.random.randint(100, 1000)
        }
    
    async def _generate_conversion_rate_optimizations(self, stage: str, stage_data: Dict) -> List[Dict]:
        """Generate conversion rate optimization recommendations"""
        return [
            {
                'type': 'A/B_test_cta',
                'description': f'Test different CTAs for {stage} stage',
                'potential_impact': 'medium',
                'effort': 'low'
            },
            {
                'type': 'personalization',
                'description': f'Add personalized content for {stage}',
                'potential_impact': 'high',
                'effort': 'high'
            }
        ]
    
    async def _generate_time_optimization(self, stage: str, stage_data: Dict) -> List[Dict]:
        """Generate time-in-stage optimization recommendations"""
        return [
            {
                'type': 'streamline_process',
                'description': f'Reduce steps in {stage} stage',
                'potential_impact': 'medium',
                'effort': 'medium'
            }
        ]
    
    async def _generate_drop_off_reduction_optimizations(self, stage: str, stage_data: Dict) -> List[Dict]:
        """Generate drop-off reduction recommendations"""
        return [
            {
                'type': 'exit_intent_popup',
                'description': f'Add exit-intent intervention for {stage}',
                'potential_impact': 'medium',
                'effort': 'low'
            }
        ]
    
    async def _prioritize_optimizations(self, optimizations: List[Dict]) -> List[Dict]:
        """Prioritize optimization recommendations by impact and effort"""
        impact_scores = {'high': 3, 'medium': 2, 'low': 1}
        effort_scores = {'low': 3, 'medium': 2, 'high': 1}
        
        for opt in optimizations:
            impact = impact_scores.get(opt.get('potential_impact', 'low'), 1)
            effort = effort_scores.get(opt.get('effort', 'high'), 1)
            opt['priority_score'] = impact * effort
        
        return sorted(optimizations, key=lambda x: x['priority_score'], reverse=True)