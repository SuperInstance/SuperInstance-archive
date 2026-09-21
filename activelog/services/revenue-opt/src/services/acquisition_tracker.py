import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

class AcquisitionChannel(Enum):
    ORGANIC_SEARCH = "organic_search"
    PAID_SEARCH = "paid_search"
    SOCIAL_MEDIA = "social_media"
    EMAIL_MARKETING = "email_marketing"
    REFERRAL = "referral"
    DIRECT = "direct"
    CONTENT_MARKETING = "content_marketing"
    AFFILIATE = "affiliate"
    DISPLAY_ADS = "display_ads"
    PR = "pr"

@dataclass
class AcquisitionMetrics:
    channel: str
    cost_per_acquisition: float
    lifetime_value: float
    roi: float
    conversion_rate: float
    time_to_conversion: float
    customer_count: int
    total_cost: float
    total_revenue: float
    confidence_score: float

class AcquisitionTracker:
    def __init__(self):
        self.channel_data = {}
        self.customer_journeys = {}
        self.attribution_models = {
            'first_touch': self._first_touch_attribution,
            'last_touch': self._last_touch_attribution,
            'linear': self._linear_attribution,
            'time_decay': self._time_decay_attribution,
            'position_based': self._position_based_attribution
        }
    
    async def track_acquisition_event(self, 
                                    customer_id: str,
                                    channel: str,
                                    campaign: str,
                                    cost: float,
                                    event_type: str = "impression") -> Dict:
        """Track an acquisition event (impression, click, conversion)"""
        try:
            timestamp = datetime.now()
            
            event_data = {
                'customer_id': customer_id,
                'channel': channel,
                'campaign': campaign,
                'cost': cost,
                'event_type': event_type,
                'timestamp': timestamp.isoformat()
            }
            
            # Initialize customer journey if not exists
            if customer_id not in self.customer_journeys:
                self.customer_journeys[customer_id] = {
                    'touchpoints': [],
                    'conversion_date': None,
                    'conversion_value': 0.0,
                    'first_touch': None,
                    'last_touch': None
                }
            
            journey = self.customer_journeys[customer_id]
            
            # Add touchpoint
            journey['touchpoints'].append(event_data)
            
            # Update first and last touch
            if journey['first_touch'] is None:
                journey['first_touch'] = event_data
            journey['last_touch'] = event_data
            
            # Track conversion
            if event_type == "conversion":
                journey['conversion_date'] = timestamp.isoformat()
                journey['conversion_value'] = cost
            
            # Update channel data
            await self._update_channel_metrics(channel, event_data)
            
            return {
                'success': True,
                'event_tracked': event_data,
                'journey_length': len(journey['touchpoints'])
            }
        
        except Exception as e:
            logger.error(f"Error tracking acquisition event: {e}")
            return {'success': False, 'error': str(e)}
    
    async def calculate_channel_cac(self, channel: str, time_period_days: int = 30) -> Dict:
        """Calculate Customer Acquisition Cost for a specific channel"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=time_period_days)
            
            # Get channel data for period
            channel_metrics = await self._get_channel_metrics(channel, start_date, end_date)
            
            total_cost = channel_metrics['total_cost']
            conversions = channel_metrics['conversions']
            
            cac = total_cost / max(conversions, 1)
            
            # Calculate related metrics
            ltv = await self._calculate_channel_ltv(channel)
            roi = (ltv - cac) / cac if cac > 0 else 0
            conversion_rate = conversions / max(channel_metrics['impressions'], 1)
            
            return {
                'success': True,
                'channel': channel,
                'time_period_days': time_period_days,
                'customer_acquisition_cost': cac,
                'lifetime_value': ltv,
                'roi': roi,
                'conversion_rate': conversion_rate,
                'total_cost': total_cost,
                'conversions': conversions,
                'payback_period_months': cac / max(ltv / 12, 1) if ltv > 0 else float('inf')
            }
        
        except Exception as e:
            logger.error(f"Error calculating CAC for channel {channel}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def analyze_attribution(self, 
                                 customer_id: str, 
                                 model: str = "linear",
                                 conversion_value: float = None) -> Dict:
        """Analyze customer acquisition attribution using specified model"""
        try:
            if customer_id not in self.customer_journeys:
                return {'success': False, 'error': 'Customer journey not found'}
            
            journey = self.customer_journeys[customer_id]
            touchpoints = journey['touchpoints']
            
            if not touchpoints:
                return {'success': False, 'error': 'No touchpoints found'}
            
            # Use provided conversion value or default
            value = conversion_value or journey['conversion_value'] or 100.0
            
            # Apply attribution model
            if model in self.attribution_models:
                attribution = self.attribution_models[model](touchpoints, value)
            else:
                return {'success': False, 'error': 'Invalid attribution model'}
            
            # Calculate attribution metrics
            attribution_summary = await self._calculate_attribution_summary(attribution)
            
            return {
                'success': True,
                'customer_id': customer_id,
                'attribution_model': model,
                'conversion_value': value,
                'touchpoints_count': len(touchpoints),
                'attribution_breakdown': attribution,
                'summary': attribution_summary
            }
        
        except Exception as e:
            logger.error(f"Error analyzing attribution: {e}")
            return {'success': False, 'error': str(e)}
    
    async def optimize_channel_mix(self) -> Dict:
        """Optimize marketing channel mix for best ROI"""
        try:
            channel_performance = {}
            
            # Calculate performance metrics for each channel
            for channel in AcquisitionChannel:
                channel_name = channel.value
                metrics = await self.calculate_channel_cac(channel_name)
                
                if metrics['success']:
                    channel_performance[channel_name] = {
                        'cac': metrics['customer_acquisition_cost'],
                        'ltv': metrics['lifetime_value'],
                        'roi': metrics['roi'],
                        'conversion_rate': metrics['conversion_rate'],
                        'payback_period': metrics['payback_period_months']
                    }
            
            if not channel_performance:
                return {'success': False, 'error': 'No channel data available'}
            
            # Generate optimization recommendations
            recommendations = await self._generate_channel_recommendations(channel_performance)
            
            # Calculate optimal budget allocation
            budget_allocation = await self._calculate_optimal_budget_allocation(channel_performance)
            
            return {
                'success': True,
                'channel_performance': channel_performance,
                'recommendations': recommendations,
                'optimal_budget_allocation': budget_allocation,
                'analysis_date': datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error optimizing channel mix: {e}")
            return {'success': False, 'error': str(e)}
    
    async def predict_acquisition_trends(self, forecast_days: int = 30) -> Dict:
        """Predict future acquisition trends based on historical data"""
        try:
            # Get historical data
            historical_data = await self._get_historical_acquisition_data(90)  # Last 90 days
            
            predictions = {}
            
            for channel in historical_data:
                channel_data = historical_data[channel]
                
                # Simple trend analysis (in production, use more sophisticated models)
                daily_conversions = [d['conversions'] for d in channel_data]
                daily_costs = [d['cost'] for d in channel_data]
                
                if len(daily_conversions) < 7:
                    continue
                
                # Calculate trends
                conversion_trend = np.polyfit(range(len(daily_conversions)), daily_conversions, 1)[0]
                cost_trend = np.polyfit(range(len(daily_costs)), daily_costs, 1)[0]
                
                # Predict future metrics
                avg_conversions = np.mean(daily_conversions[-7:])  # Last week average
                avg_cost = np.mean(daily_costs[-7:])
                
                predicted_conversions = max(0, avg_conversions + (conversion_trend * forecast_days))
                predicted_cost = max(0, avg_cost + (cost_trend * forecast_days))
                
                predictions[channel] = {
                    'predicted_conversions': predicted_conversions,
                    'predicted_cost': predicted_cost,
                    'predicted_cac': predicted_cost / max(predicted_conversions, 1),
                    'conversion_trend': 'increasing' if conversion_trend > 0 else 'decreasing',
                    'cost_trend': 'increasing' if cost_trend > 0 else 'decreasing',
                    'confidence': min(1.0, len(daily_conversions) / 30)  # More data = higher confidence
                }
            
            return {
                'success': True,
                'forecast_period_days': forecast_days,
                'predictions': predictions,
                'generated_at': datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error predicting acquisition trends: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _update_channel_metrics(self, channel: str, event_data: Dict):
        """Update channel-level metrics"""
        if channel not in self.channel_data:
            self.channel_data[channel] = {
                'impressions': 0,
                'clicks': 0,
                'conversions': 0,
                'total_cost': 0.0,
                'total_revenue': 0.0
            }
        
        channel_metrics = self.channel_data[channel]
        
        if event_data['event_type'] == 'impression':
            channel_metrics['impressions'] += 1
        elif event_data['event_type'] == 'click':
            channel_metrics['clicks'] += 1
        elif event_data['event_type'] == 'conversion':
            channel_metrics['conversions'] += 1
            channel_metrics['total_revenue'] += event_data['cost']
        
        channel_metrics['total_cost'] += event_data['cost']
    
    async def _get_channel_metrics(self, channel: str, start_date: datetime, end_date: datetime) -> Dict:
        """Get channel metrics for specified time period"""
        # Mock implementation - would query actual database
        return {
            'total_cost': np.random.uniform(1000, 5000),
            'conversions': np.random.randint(10, 100),
            'impressions': np.random.randint(1000, 10000),
            'clicks': np.random.randint(100, 1000)
        }
    
    async def _calculate_channel_ltv(self, channel: str) -> float:
        """Calculate average LTV for customers from specific channel"""
        # Mock implementation - would calculate actual LTV
        channel_multipliers = {
            'organic_search': 1.2,
            'paid_search': 1.0,
            'social_media': 0.8,
            'email_marketing': 1.3,
            'referral': 1.5,
            'direct': 1.4,
            'content_marketing': 1.1,
            'affiliate': 0.9,
            'display_ads': 0.7,
            'pr': 1.6
        }
        
        base_ltv = 150.0  # Base LTV
        multiplier = channel_multipliers.get(channel, 1.0)
        return base_ltv * multiplier
    
    # Attribution model implementations
    def _first_touch_attribution(self, touchpoints: List[Dict], value: float) -> Dict:
        """First-touch attribution model"""
        first_touchpoint = touchpoints[0]
        return {first_touchpoint['channel']: value}
    
    def _last_touch_attribution(self, touchpoints: List[Dict], value: float) -> Dict:
        """Last-touch attribution model"""
        last_touchpoint = touchpoints[-1]
        return {last_touchpoint['channel']: value}
    
    def _linear_attribution(self, touchpoints: List[Dict], value: float) -> Dict:
        """Linear attribution model - equal credit to all touchpoints"""
        attribution = {}
        value_per_touchpoint = value / len(touchpoints)
        
        for touchpoint in touchpoints:
            channel = touchpoint['channel']
            attribution[channel] = attribution.get(channel, 0) + value_per_touchpoint
        
        return attribution
    
    def _time_decay_attribution(self, touchpoints: List[Dict], value: float) -> Dict:
        """Time-decay attribution model - more recent touchpoints get more credit"""
        attribution = {}
        
        # Calculate decay weights (more recent = higher weight)
        weights = [i + 1 for i in range(len(touchpoints))]
        total_weight = sum(weights)
        
        for i, touchpoint in enumerate(touchpoints):
            channel = touchpoint['channel']
            weight = weights[i] / total_weight
            attribution[channel] = attribution.get(channel, 0) + (value * weight)
        
        return attribution
    
    def _position_based_attribution(self, touchpoints: List[Dict], value: float) -> Dict:
        """Position-based attribution model - 40% first, 40% last, 20% middle"""
        attribution = {}
        
        if len(touchpoints) == 1:
            attribution[touchpoints[0]['channel']] = value
        elif len(touchpoints) == 2:
            attribution[touchpoints[0]['channel']] = value * 0.5
            attribution[touchpoints[1]['channel']] = value * 0.5
        else:
            # First touch gets 40%
            first_channel = touchpoints[0]['channel']
            attribution[first_channel] = attribution.get(first_channel, 0) + (value * 0.4)
            
            # Last touch gets 40%
            last_channel = touchpoints[-1]['channel']
            attribution[last_channel] = attribution.get(last_channel, 0) + (value * 0.4)
            
            # Middle touchpoints share 20%
            middle_touchpoints = touchpoints[1:-1]
            if middle_touchpoints:
                value_per_middle = (value * 0.2) / len(middle_touchpoints)
                for touchpoint in middle_touchpoints:
                    channel = touchpoint['channel']
                    attribution[channel] = attribution.get(channel, 0) + value_per_middle
        
        return attribution
    
    async def _calculate_attribution_summary(self, attribution: Dict) -> Dict:
        """Calculate summary statistics for attribution analysis"""
        total_attributed = sum(attribution.values())
        
        summary = {
            'total_attributed_value': total_attributed,
            'channel_count': len(attribution),
            'primary_channel': max(attribution.items(), key=lambda x: x[1])[0] if attribution else None,
            'attribution_distribution': {
                channel: (value / total_attributed) * 100 if total_attributed > 0 else 0
                for channel, value in attribution.items()
            }
        }
        
        return summary
    
    async def _generate_channel_recommendations(self, channel_performance: Dict) -> List[Dict]:
        """Generate optimization recommendations based on channel performance"""
        recommendations = []
        
        # Sort channels by ROI
        sorted_channels = sorted(
            channel_performance.items(),
            key=lambda x: x[1]['roi'],
            reverse=True
        )
        
        # Best performing channels
        if sorted_channels:
            best_channel = sorted_channels[0]
            recommendations.append({
                'type': 'increase_investment',
                'channel': best_channel[0],
                'reason': f'Highest ROI of {best_channel[1]["roi"]:.2f}',
                'priority': 'high'
            })
        
        # Worst performing channels
        if len(sorted_channels) > 1:
            worst_channel = sorted_channels[-1]
            if worst_channel[1]['roi'] < 0:
                recommendations.append({
                    'type': 'reduce_investment',
                    'channel': worst_channel[0],
                    'reason': f'Negative ROI of {worst_channel[1]["roi"]:.2f}',
                    'priority': 'high'
                })
        
        # Channels with long payback periods
        for channel, metrics in channel_performance.items():
            if metrics['payback_period'] > 12:  # More than 12 months
                recommendations.append({
                    'type': 'optimize_conversion',
                    'channel': channel,
                    'reason': f'Long payback period of {metrics["payback_period"]:.1f} months',
                    'priority': 'medium'
                })
        
        return recommendations
    
    async def _calculate_optimal_budget_allocation(self, channel_performance: Dict) -> Dict:
        """Calculate optimal budget allocation across channels"""
        # Simple allocation based on ROI (in production, use more sophisticated optimization)
        total_roi = sum(max(0, metrics['roi']) for metrics in channel_performance.values())
        
        if total_roi == 0:
            # Equal allocation if no positive ROI
            allocation = {channel: 1.0 / len(channel_performance) for channel in channel_performance}
        else:
            allocation = {}
            for channel, metrics in channel_performance.items():
                roi_share = max(0, metrics['roi']) / total_roi
                allocation[channel] = roi_share
        
        return {
            'percentage_allocation': {channel: pct * 100 for channel, pct in allocation.items()},
            'methodology': 'ROI-weighted allocation',
            'total_channels': len(channel_performance)
        }
    
    async def _get_historical_acquisition_data(self, days: int) -> Dict:
        """Get historical acquisition data for trend analysis"""
        # Mock implementation - would query actual database
        channels = [channel.value for channel in AcquisitionChannel]
        historical_data = {}
        
        for channel in channels:
            daily_data = []
            for day in range(days):
                daily_data.append({
                    'date': (datetime.now() - timedelta(days=day)).date().isoformat(),
                    'conversions': np.random.randint(1, 20),
                    'cost': np.random.uniform(50, 500),
                    'impressions': np.random.randint(100, 2000)
                })
            historical_data[channel] = daily_data
        
        return historical_data