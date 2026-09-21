"""
Spot Instance Manager
Manages spot instances for cost optimization with intelligent bidding and interruption handling
"""

import logging
import boto3
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import json
import statistics
import asyncio
from dataclasses import dataclass

from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class SpotInstanceState(Enum):
    OPEN = "open"
    ACTIVE = "active"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    FAILED = "failed"

class InterruptionAction(Enum):
    TERMINATE = "terminate"
    STOP = "stop"
    HIBERNATE = "hibernate"

@dataclass
class SpotPriceHistory:
    instance_type: str
    availability_zone: str
    product_description: str
    spot_price: float
    timestamp: datetime

@dataclass
class SpotRequest:
    request_id: str
    instance_type: str
    max_price: float
    availability_zone: str
    state: SpotInstanceState
    created_at: datetime
    instance_id: Optional[str] = None
    fault_code: Optional[str] = None
    fault_message: Optional[str] = None

class SpotInstanceManager:
    """Manages spot instances for cost optimization"""
    
    def __init__(self, ec2_client):
        self.ec2 = ec2_client
        self.cloudwatch = boto3.client('cloudwatch', region_name=ec2_client.meta.region_name)
        
        # Pricing history cache
        self.price_history_cache = {}
        self.cache_expiry = datetime.utcnow()
        
        # Active spot requests tracking
        self.active_requests: Dict[str, SpotRequest] = {}
        
        # Interruption handling callbacks
        self.interruption_callbacks = []
    
    async def analyze_spot_opportunities(self, instance_types: List[str] = None,
                                       availability_zones: List[str] = None) -> Dict[str, Any]:
        """Analyze spot instance opportunities for cost savings"""
        try:
            if not instance_types:
                instance_types = ['t3.micro', 't3.small', 't3.medium', 't3.large',
                                'm5.large', 'm5.xlarge', 'c5.large', 'c5.xlarge']
            
            if not availability_zones:
                # Get available AZs
                response = self.ec2.describe_availability_zones()
                availability_zones = [az['ZoneName'] for az in response['AvailabilityZones']]
            
            # Get current spot prices
            spot_prices = await self._get_current_spot_prices(instance_types, availability_zones)
            
            # Get on-demand prices for comparison
            on_demand_prices = await self._get_on_demand_prices(instance_types)
            
            # Calculate savings opportunities
            opportunities = []
            
            for instance_type in instance_types:
                for az in availability_zones:
                    spot_price = self._get_spot_price(spot_prices, instance_type, az)
                    on_demand_price = on_demand_prices.get(instance_type, 0)
                    
                    if spot_price and on_demand_price:
                        savings_percent = ((on_demand_price - spot_price) / on_demand_price) * 100
                        
                        if savings_percent > 10:  # Only show significant savings
                            opportunities.append({
                                'instance_type': instance_type,
                                'availability_zone': az,
                                'spot_price': spot_price,
                                'on_demand_price': on_demand_price,
                                'savings_percent': round(savings_percent, 1),
                                'monthly_savings_estimate': round((on_demand_price - spot_price) * 24 * 30, 2)
                            })
            
            # Sort by savings percentage
            opportunities.sort(key=lambda x: x['savings_percent'], reverse=True)
            
            # Get price volatility analysis
            volatility_analysis = await self._analyze_price_volatility(instance_types, availability_zones)
            
            return {
                'opportunities': opportunities[:20],  # Top 20 opportunities
                'volatility_analysis': volatility_analysis,
                'recommendation_summary': self._generate_spot_recommendations(opportunities),
                'analysis_timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze spot opportunities: {e}")
            raise
    
    async def _get_current_spot_prices(self, instance_types: List[str],
                                     availability_zones: List[str]) -> List[SpotPriceHistory]:
        """Get current spot prices from AWS"""
        try:
            # Check cache first
            if (datetime.utcnow() - self.cache_expiry).total_seconds() < 300:  # 5 minutes cache
                cache_key = f"{'-'.join(instance_types)}_{'-'.join(availability_zones)}"
                if cache_key in self.price_history_cache:
                    return self.price_history_cache[cache_key]
            
            response = self.ec2.describe_spot_price_history(
                InstanceTypes=instance_types,
                AvailabilityZones=availability_zones,
                ProductDescriptions=['Linux/UNIX'],
                MaxResults=1000,
                StartTime=datetime.utcnow() - timedelta(hours=1)
            )
            
            spot_prices = []
            for price_data in response['SpotPriceHistory']:
                spot_prices.append(SpotPriceHistory(
                    instance_type=price_data['InstanceType'],
                    availability_zone=price_data['AvailabilityZone'],
                    product_description=price_data['ProductDescription'],
                    spot_price=float(price_data['SpotPrice']),
                    timestamp=price_data['Timestamp']
                ))
            
            # Update cache
            cache_key = f"{'-'.join(instance_types)}_{'-'.join(availability_zones)}"
            self.price_history_cache[cache_key] = spot_prices
            self.cache_expiry = datetime.utcnow()
            
            return spot_prices
            
        except Exception as e:
            logger.error(f"Failed to get spot prices: {e}")
            return []
    
    async def _get_on_demand_prices(self, instance_types: List[str]) -> Dict[str, float]:
        """Get on-demand prices (simplified - in production use Pricing API)"""
        # Simplified pricing - in production, use AWS Pricing API
        on_demand_prices = {
            't3.micro': 0.0104,
            't3.small': 0.0208,
            't3.medium': 0.0416,
            't3.large': 0.0832,
            't3.xlarge': 0.1664,
            'm5.large': 0.096,
            'm5.xlarge': 0.192,
            'm5.2xlarge': 0.384,
            'c5.large': 0.085,
            'c5.xlarge': 0.17,
            'c5.2xlarge': 0.34,
            'r5.large': 0.126,
            'r5.xlarge': 0.252
        }
        
        return {itype: price for itype, price in on_demand_prices.items() if itype in instance_types}
    
    def _get_spot_price(self, spot_prices: List[SpotPriceHistory], 
                       instance_type: str, availability_zone: str) -> Optional[float]:
        """Get the most recent spot price for instance type and AZ"""
        matching_prices = [
            price for price in spot_prices
            if price.instance_type == instance_type and price.availability_zone == availability_zone
        ]
        
        if matching_prices:
            # Return the most recent price
            latest_price = max(matching_prices, key=lambda x: x.timestamp)
            return latest_price.spot_price
        
        return None
    
    def _generate_spot_recommendations(self, opportunities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate spot instance recommendations"""
        if not opportunities:
            return {
                'recommendation': 'No significant spot savings opportunities found',
                'suggested_actions': []
            }
        
        top_opportunity = opportunities[0]
        total_opportunities = len(opportunities)
        avg_savings = statistics.mean([opp['savings_percent'] for opp in opportunities])
        
        recommendations = {
            'recommendation': f'Found {total_opportunities} spot opportunities with average savings of {avg_savings:.1f}%',
            'top_opportunity': {
                'instance_type': top_opportunity['instance_type'],
                'availability_zone': top_opportunity['availability_zone'],
                'savings_percent': top_opportunity['savings_percent']
            },
            'suggested_actions': []
        }
        
        # Generate specific recommendations
        if avg_savings > 70:
            recommendations['suggested_actions'].append({
                'action': 'immediate_conversion',
                'description': 'High savings potential detected. Consider immediate conversion to spot instances.',
                'priority': 'high'
            })
        
        if avg_savings > 50:
            recommendations['suggested_actions'].append({
                'action': 'batch_workload_conversion',
                'description': 'Convert batch processing workloads to spot instances.',
                'priority': 'high'
            })
        
        recommendations['suggested_actions'].append({
            'action': 'diversify_instance_types',
            'description': 'Use multiple instance types and AZs to reduce interruption risk.',
            'priority': 'medium'
        })
        
        recommendations['suggested_actions'].append({
            'action': 'implement_interruption_handling',
            'description': 'Set up proper interruption handling before using spot instances.',
            'priority': 'high'
        })
        
        return recommendations