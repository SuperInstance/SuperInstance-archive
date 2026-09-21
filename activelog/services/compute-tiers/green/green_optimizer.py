#!/usr/bin/env python3
"""
Green Energy Optimizer for ActiveLog Compute Tiers
Intelligent workload scheduling based on renewable energy availability and carbon footprint optimization
"""

import logging
import json
import math
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import requests
import asyncio

logger = logging.getLogger(__name__)

class EnergySource(Enum):
    """Types of energy sources"""
    SOLAR = "solar"
    WIND = "wind"
    HYDRO = "hydro"
    NUCLEAR = "nuclear"
    NATURAL_GAS = "natural_gas"
    COAL = "coal"
    BATTERY_STORAGE = "battery_storage"
    MIXED_RENEWABLE = "mixed_renewable"

class CarbonIntensity(Enum):
    """Carbon intensity levels"""
    VERY_LOW = "very_low"      # <100 gCO2/kWh
    LOW = "low"                # 100-200 gCO2/kWh
    MODERATE = "moderate"      # 200-400 gCO2/kWh
    HIGH = "high"              # 400-600 gCO2/kWh
    VERY_HIGH = "very_high"    # >600 gCO2/kWh

class GreenPreference(Enum):
    """Green energy preference levels"""
    MAXIMUM_GREEN = "maximum_green"        # Only renewable energy
    PREFER_GREEN = "prefer_green"          # Prefer renewable, accept some compromise
    BALANCED = "balanced"                  # Balance green energy with cost/performance
    COST_FIRST = "cost_first"              # Cost priority, green energy secondary
    PERFORMANCE_FIRST = "performance_first" # Performance priority, green energy tertiary

@dataclass
class EnergyProfile:
    """Energy profile for a compute location"""
    location_id: str
    location_name: str
    region: str
    country: str
    timezone: str
    current_energy_mix: Dict[EnergySource, float]  # Percentage by source
    renewable_percentage: float
    carbon_intensity_g_co2_kwh: float
    carbon_intensity_level: CarbonIntensity
    energy_cost_per_kwh: float
    forecast_next_24h: List[Dict[str, Any]]
    last_updated: datetime

@dataclass
class WorkloadCarbonProfile:
    """Carbon footprint profile for a workload"""
    workload_id: str
    estimated_power_consumption_kw: float
    estimated_runtime_hours: float
    flexibility_window_hours: int  # How much workload can be delayed
    carbon_budget_kg_co2: Optional[float]
    green_energy_requirement: GreenPreference
    priority: int  # 1-10, higher means less flexible
    can_be_paused: bool
    can_be_migrated: bool

@dataclass
class GreenOptimization:
    """Green energy optimization recommendation"""
    workload_id: str
    current_location: str
    recommended_actions: List[Dict[str, Any]]
    carbon_footprint_reduction_kg: float
    renewable_energy_percentage: float
    estimated_cost_impact: float
    scheduling_recommendations: Dict[str, Any]
    location_recommendations: List[Dict[str, Any]]
    optimization_confidence: float
    reasoning: str

class GreenEnergyOptimizer:
    """Optimizes compute workloads for green energy usage and carbon footprint reduction"""
    
    def __init__(self, config):
        self.config = config
        
        # Energy profiles for different compute locations
        self.energy_profiles: Dict[str, EnergyProfile] = {}
        
        # Active workloads and their carbon profiles
        self.active_workloads: Dict[str, WorkloadCarbonProfile] = {}
        
        # Historical green energy data
        self.green_energy_history: List[Dict[str, Any]] = []
        
        # Initialize energy profiles
        self._initialize_energy_profiles()
        
        # Carbon intensity thresholds
        self.carbon_intensity_thresholds = {
            CarbonIntensity.VERY_LOW: 100,
            CarbonIntensity.LOW: 200,
            CarbonIntensity.MODERATE: 400,
            CarbonIntensity.HIGH: 600,
            CarbonIntensity.VERY_HIGH: float('inf')
        }
        
        # Energy source carbon intensities (gCO2/kWh)
        self.energy_source_carbon_intensity = {
            EnergySource.SOLAR: 48,
            EnergySource.WIND: 26,
            EnergySource.HYDRO: 24,
            EnergySource.NUCLEAR: 12,
            EnergySource.NATURAL_GAS: 490,
            EnergySource.COAL: 820,
            EnergySource.BATTERY_STORAGE: 50,  # Depends on charging source
            EnergySource.MIXED_RENEWABLE: 35
        }

    def _initialize_energy_profiles(self):
        """Initialize energy profiles for compute locations"""
        energy_profiles_data = [
            {
                'location_id': 'us_west_2',
                'location_name': 'US West (Oregon)',
                'region': 'us-west-2',
                'country': 'USA',
                'timezone': 'America/Los_Angeles',
                'current_energy_mix': {
                    EnergySource.HYDRO: 60.0,
                    EnergySource.WIND: 15.0,
                    EnergySource.SOLAR: 10.0,
                    EnergySource.NUCLEAR: 8.0,
                    EnergySource.NATURAL_GAS: 7.0
                },
                'renewable_percentage': 85.0,
                'carbon_intensity': 95,
                'energy_cost': 0.11
            },
            {
                'location_id': 'us_east_1',
                'location_name': 'US East (N. Virginia)',
                'region': 'us-east-1',
                'country': 'USA',
                'timezone': 'America/New_York',
                'current_energy_mix': {
                    EnergySource.NATURAL_GAS: 40.0,
                    EnergySource.NUCLEAR: 25.0,
                    EnergySource.WIND: 12.0,
                    EnergySource.SOLAR: 8.0,
                    EnergySource.COAL: 15.0
                },
                'renewable_percentage': 20.0,
                'carbon_intensity': 385,
                'energy_cost': 0.13
            },
            {
                'location_id': 'eu_west_1',
                'location_name': 'EU West (Ireland)',
                'region': 'eu-west-1',
                'country': 'Ireland',
                'timezone': 'Europe/Dublin',
                'current_energy_mix': {
                    EnergySource.WIND: 35.0,
                    EnergySource.NATURAL_GAS: 30.0,
                    EnergySource.HYDRO: 5.0,
                    EnergySource.SOLAR: 2.0,
                    EnergySource.COAL: 8.0,
                    EnergySource.MIXED_RENEWABLE: 20.0
                },
                'renewable_percentage': 62.0,
                'carbon_intensity': 195,
                'energy_cost': 0.25
            },
            {
                'location_id': 'eu_north_1',
                'location_name': 'EU North (Stockholm)',
                'region': 'eu-north-1',
                'country': 'Sweden',
                'timezone': 'Europe/Stockholm',
                'current_energy_mix': {
                    EnergySource.HYDRO: 45.0,
                    EnergySource.NUCLEAR: 35.0,
                    EnergySource.WIND: 18.0,
                    EnergySource.SOLAR: 2.0
                },
                'renewable_percentage': 65.0,
                'carbon_intensity': 85,
                'energy_cost': 0.22
            },
            {
                'location_id': 'ap_southeast_2',
                'location_name': 'Asia Pacific (Sydney)',
                'region': 'ap-southeast-2',
                'country': 'Australia',
                'timezone': 'Australia/Sydney',
                'current_energy_mix': {
                    EnergySource.COAL: 45.0,
                    EnergySource.NATURAL_GAS: 20.0,
                    EnergySource.HYDRO: 15.0,
                    EnergySource.WIND: 12.0,
                    EnergySource.SOLAR: 8.0
                },
                'renewable_percentage': 35.0,
                'carbon_intensity': 520,
                'energy_cost': 0.18
            },
            {
                'location_id': 'ca_central_1',
                'location_name': 'Canada Central',
                'region': 'ca-central-1',
                'country': 'Canada',
                'timezone': 'America/Toronto',
                'current_energy_mix': {
                    EnergySource.HYDRO: 70.0,
                    EnergySource.NUCLEAR: 15.0,
                    EnergySource.WIND: 8.0,
                    EnergySource.SOLAR: 2.0,
                    EnergySource.NATURAL_GAS: 5.0
                },
                'renewable_percentage': 80.0,
                'carbon_intensity': 75,
                'energy_cost': 0.15
            }
        ]
        
        # Convert to energy profiles
        for profile_data in energy_profiles_data:
            # Convert energy mix
            energy_mix = {}
            for source_name, percentage in profile_data['current_energy_mix'].items():
                if isinstance(source_name, str):
                    source_name = EnergySource(source_name)
                energy_mix[source_name] = percentage
            
            # Determine carbon intensity level
            carbon_intensity = profile_data['carbon_intensity']
            intensity_level = CarbonIntensity.VERY_HIGH
            for level, threshold in self.carbon_intensity_thresholds.items():
                if carbon_intensity <= threshold:
                    intensity_level = level
                    break
            
            # Generate forecast (simplified)
            forecast = self._generate_energy_forecast(profile_data)
            
            profile = EnergyProfile(
                location_id=profile_data['location_id'],
                location_name=profile_data['location_name'],
                region=profile_data['region'],
                country=profile_data['country'],
                timezone=profile_data['timezone'],
                current_energy_mix=energy_mix,
                renewable_percentage=profile_data['renewable_percentage'],
                carbon_intensity_g_co2_kwh=carbon_intensity,
                carbon_intensity_level=intensity_level,
                energy_cost_per_kwh=profile_data['energy_cost'],
                forecast_next_24h=forecast,
                last_updated=datetime.utcnow()
            )
            
            self.energy_profiles[profile.location_id] = profile

    def _generate_energy_forecast(self, profile_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate simplified 24-hour energy forecast"""
        forecast = []
        base_renewable = profile_data['renewable_percentage']
        base_carbon = profile_data['carbon_intensity']
        
        # Generate hourly forecasts
        for hour in range(24):
            # Simulate renewable energy variations (solar peaks during day)
            if profile_data.get('current_energy_mix', {}).get(EnergySource.SOLAR, 0) > 5:
                # Solar-heavy locations have daytime renewable peaks
                solar_factor = max(0, math.sin((hour - 6) * math.pi / 12)) if 6 <= hour <= 18 else 0
                renewable_adjustment = solar_factor * 20  # Up to 20% boost during peak sun
            else:
                renewable_adjustment = (hash(str(hour)) % 10 - 5)  # Random ±5% variation
            
            adjusted_renewable = max(0, min(100, base_renewable + renewable_adjustment))
            
            # Carbon intensity inversely related to renewable percentage
            renewable_factor = adjusted_renewable / 100
            carbon_reduction = (adjusted_renewable - base_renewable) * 2  # 2 gCO2/kWh per % renewable
            adjusted_carbon = max(50, base_carbon - carbon_reduction)
            
            forecast.append({
                'hour': hour,
                'timestamp': (datetime.utcnow() + timedelta(hours=hour)).isoformat(),
                'renewable_percentage': round(adjusted_renewable, 1),
                'carbon_intensity_g_co2_kwh': round(adjusted_carbon, 0),
                'relative_cost_multiplier': 1.0 + (random_variation := (hash(str(hour * 7)) % 20 - 10) / 100),  # ±10%
                'green_score': round(adjusted_renewable * (1 - adjusted_carbon / 1000), 1)  # Composite green score
            })
        
        return forecast

    def optimize_for_green_energy(self, workload_flexibility: Dict[str, Any],
                                 green_preferences: Dict[str, Any] = None) -> GreenOptimization:
        """Optimize workload for green energy usage"""
        try:
            # Parse workload and preferences
            workload_profile = self._parse_workload_flexibility(workload_flexibility)
            preferences = green_preferences or {}
            
            # Get current location energy profile
            current_location = workload_flexibility.get('current_location', 'us_west_2')
            current_profile = self.energy_profiles.get(current_location)
            
            if not current_profile:
                return self._create_error_optimization(
                    workload_profile.workload_id,
                    f"Energy profile not found for location {current_location}"
                )
            
            # Analyze current carbon footprint
            current_carbon_footprint = self._calculate_carbon_footprint(workload_profile, current_profile)
            
            # Generate optimization recommendations
            recommendations = self._generate_green_recommendations(workload_profile, current_profile, preferences)
            
            # Find alternative locations
            location_alternatives = self._find_green_alternatives(workload_profile, current_location)
            
            # Generate scheduling recommendations
            scheduling_recommendations = self._generate_green_scheduling(workload_profile, current_profile)
            
            # Calculate potential carbon reduction
            best_alternative = location_alternatives[0] if location_alternatives else None
            carbon_reduction = 0.0
            
            if best_alternative:
                alternative_profile = self.energy_profiles[best_alternative['location_id']]
                alternative_footprint = self._calculate_carbon_footprint(workload_profile, alternative_profile)
                carbon_reduction = current_carbon_footprint - alternative_footprint
            
            # Calculate renewable energy percentage for recommended solution
            if best_alternative:
                renewable_percentage = self.energy_profiles[best_alternative['location_id']].renewable_percentage
            else:
                renewable_percentage = current_profile.renewable_percentage
            
            # Estimate cost impact
            cost_impact = self._estimate_green_cost_impact(workload_profile, recommendations, best_alternative)
            
            # Calculate confidence score
            confidence_score = self._calculate_green_confidence(workload_profile, recommendations, location_alternatives)
            
            # Generate reasoning
            reasoning = self._generate_green_reasoning(workload_profile, recommendations, best_alternative, preferences)
            
            return GreenOptimization(
                workload_id=workload_profile.workload_id,
                current_location=current_location,
                recommended_actions=recommendations,
                carbon_footprint_reduction_kg=carbon_reduction,
                renewable_energy_percentage=renewable_percentage,
                estimated_cost_impact=cost_impact,
                scheduling_recommendations=scheduling_recommendations,
                location_recommendations=location_alternatives,
                optimization_confidence=confidence_score,
                reasoning=reasoning
            )
            
        except Exception as e:
            logger.error(f"Failed to optimize for green energy: {e}")
            return self._create_error_optimization(
                workload_flexibility.get('workload_id', 'unknown'),
                f"Optimization error: {str(e)}"
            )

    def _parse_workload_flexibility(self, flexibility_data: Dict[str, Any]) -> WorkloadCarbonProfile:
        """Parse workload flexibility and carbon requirements"""
        return WorkloadCarbonProfile(
            workload_id=flexibility_data.get('workload_id', f'green_workload_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}'),
            estimated_power_consumption_kw=flexibility_data.get('estimated_power_consumption_kw', 2.0),
            estimated_runtime_hours=flexibility_data.get('estimated_runtime_hours', 1.0),
            flexibility_window_hours=flexibility_data.get('flexibility_window_hours', 12),
            carbon_budget_kg_co2=flexibility_data.get('carbon_budget_kg_co2'),
            green_energy_requirement=GreenPreference(flexibility_data.get('green_energy_requirement', 'balanced')),
            priority=flexibility_data.get('priority', 5),
            can_be_paused=flexibility_data.get('can_be_paused', False),
            can_be_migrated=flexibility_data.get('can_be_migrated', True)
        )

    def _calculate_carbon_footprint(self, workload: WorkloadCarbonProfile, energy_profile: EnergyProfile) -> float:
        """Calculate carbon footprint in kg CO2"""
        energy_consumption_kwh = workload.estimated_power_consumption_kw * workload.estimated_runtime_hours
        carbon_intensity_kg_co2_kwh = energy_profile.carbon_intensity_g_co2_kwh / 1000  # Convert g to kg
        
        return energy_consumption_kwh * carbon_intensity_kg_co2_kwh

    def _generate_green_recommendations(self, workload: WorkloadCarbonProfile, 
                                      current_profile: EnergyProfile,
                                      preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate green energy optimization recommendations"""
        recommendations = []
        
        # Scheduling recommendations based on energy forecast
        optimal_hours = self._find_optimal_green_hours(current_profile)
        if optimal_hours and workload.flexibility_window_hours > 0:
            recommendations.append({
                'type': 'schedule_optimization',
                'action': 'delay_to_green_window',
                'details': {
                    'optimal_start_hours': optimal_hours,
                    'carbon_reduction_kg': self._estimate_scheduling_carbon_reduction(workload, current_profile, optimal_hours),
                    'renewable_percentage_during_window': optimal_hours[0]['renewable_percentage']
                },
                'priority': 'high' if workload.green_energy_requirement in [GreenPreference.MAXIMUM_GREEN, GreenPreference.PREFER_GREEN] else 'medium'
            })
        
        # Instance type optimization
        if current_profile.renewable_percentage < 70:
            recommendations.append({
                'type': 'instance_optimization',
                'action': 'select_energy_efficient_instances',
                'details': {
                    'recommended_families': ['t3', 'm5', 'c5'],  # More energy efficient
                    'avoid_families': ['m4', 'c4'],  # Less energy efficient
                    'estimated_power_reduction_percent': 15
                },
                'priority': 'medium'
            })
        
        # Workload consolidation
        recommendations.append({
            'type': 'workload_consolidation',
            'action': 'consolidate_to_fewer_instances',
            'details': {
                'consolidation_ratio': 1.5,  # Use 1.5x fewer instances with higher utilization
                'estimated_power_reduction_percent': 20,
                'trade_off': 'slightly higher utilization per instance'
            },
            'priority': 'low'
        })
        
        # Auto-scaling optimization
        if workload.can_be_paused:
            recommendations.append({
                'type': 'auto_scaling',
                'action': 'green_aware_scaling',
                'details': {
                    'scale_down_during': 'high_carbon_periods',
                    'scale_up_during': 'high_renewable_periods',
                    'carbon_intensity_threshold': 300  # gCO2/kWh
                },
                'priority': 'high' if workload.green_energy_requirement == GreenPreference.MAXIMUM_GREEN else 'medium'
            })
        
        # Spot instance usage during green periods
        recommendations.append({
            'type': 'spot_instance_optimization',
            'action': 'use_spot_during_green_periods',
            'details': {
                'spot_usage_strategy': 'green_periods_only',
                'estimated_cost_savings_percent': 60,
                'estimated_carbon_reduction_kg': self._calculate_carbon_footprint(workload, current_profile) * 0.1
            },
            'priority': 'medium'
        })
        
        return recommendations

    def _find_optimal_green_hours(self, energy_profile: EnergyProfile) -> List[Dict[str, Any]]:
        """Find optimal hours for green energy usage"""
        # Sort forecast by green score (renewable percentage and low carbon intensity)
        forecast = energy_profile.forecast_next_24h
        sorted_hours = sorted(forecast, key=lambda x: x['green_score'], reverse=True)
        
        # Return top 6 hours (allowing for some flexibility)
        return sorted_hours[:6]

    def _estimate_scheduling_carbon_reduction(self, workload: WorkloadCarbonProfile, 
                                            energy_profile: EnergyProfile,
                                            optimal_hours: List[Dict[str, Any]]) -> float:
        """Estimate carbon reduction from optimal scheduling"""
        if not optimal_hours:
            return 0.0
        
        # Current carbon footprint
        current_carbon = self._calculate_carbon_footprint(workload, energy_profile)
        
        # Carbon footprint during optimal hour
        optimal_hour = optimal_hours[0]
        optimal_carbon_intensity = optimal_hour['carbon_intensity_g_co2_kwh'] / 1000  # Convert to kg/kWh
        energy_consumption = workload.estimated_power_consumption_kw * workload.estimated_runtime_hours
        optimal_carbon = energy_consumption * optimal_carbon_intensity
        
        return max(0, current_carbon - optimal_carbon)

    def _find_green_alternatives(self, workload: WorkloadCarbonProfile, 
                               current_location: str) -> List[Dict[str, Any]]:
        """Find alternative locations with better green energy profiles"""
        alternatives = []
        
        # Only consider migration if workload allows it
        if not workload.can_be_migrated:
            return alternatives
        
        current_profile = self.energy_profiles.get(current_location)
        if not current_profile:
            return alternatives
        
        # Evaluate all other locations
        for location_id, profile in self.energy_profiles.items():
            if location_id == current_location:
                continue
            
            # Calculate carbon footprint at alternative location
            alt_carbon_footprint = self._calculate_carbon_footprint(workload, profile)
            current_carbon_footprint = self._calculate_carbon_footprint(workload, current_profile)
            
            carbon_reduction = current_carbon_footprint - alt_carbon_footprint
            
            # Only consider alternatives with meaningful carbon reduction
            if carbon_reduction > 0.1:  # At least 0.1 kg CO2 reduction
                # Estimate migration cost and complexity
                migration_cost_factor = self._estimate_migration_cost_factor(current_location, location_id)
                
                alternatives.append({
                    'location_id': location_id,
                    'location_name': profile.location_name,
                    'carbon_reduction_kg': carbon_reduction,
                    'renewable_percentage': profile.renewable_percentage,
                    'carbon_intensity': profile.carbon_intensity_g_co2_kwh,
                    'migration_cost_factor': migration_cost_factor,
                    'migration_complexity': self._assess_migration_complexity(current_location, location_id),
                    'recommendation_score': self._calculate_location_score(profile, carbon_reduction, migration_cost_factor)
                })
        
        # Sort by recommendation score
        alternatives.sort(key=lambda x: x['recommendation_score'], reverse=True)
        
        return alternatives[:5]  # Return top 5 alternatives

    def _estimate_migration_cost_factor(self, from_location: str, to_location: str) -> float:
        """Estimate relative cost factor for migrating workload between locations"""
        # Base migration cost factors
        base_cost_factors = {
            ('us_west_2', 'us_east_1'): 1.05,  # Same country, low cost
            ('us_west_2', 'ca_central_1'): 1.10,  # Neighboring country
            ('us_west_2', 'eu_west_1'): 1.25,  # Cross-continental
            ('us_east_1', 'eu_west_1'): 1.20,  # Cross-continental
            ('eu_west_1', 'eu_north_1'): 1.08,  # Same continent
            ('ap_southeast_2', 'us_west_2'): 1.30,  # Cross-continental, high distance
        }
        
        # Check both directions
        key = (from_location, to_location)
        reverse_key = (to_location, from_location)
        
        if key in base_cost_factors:
            return base_cost_factors[key]
        elif reverse_key in base_cost_factors:
            return base_cost_factors[reverse_key]
        else:
            # Default based on region similarity
            if from_location.startswith('us') and to_location.startswith('us'):
                return 1.05
            elif from_location.startswith('eu') and to_location.startswith('eu'):
                return 1.08
            else:
                return 1.20  # Different continents

    def _assess_migration_complexity(self, from_location: str, to_location: str) -> str:
        """Assess complexity of migrating between locations"""
        same_provider = True  # Assume same cloud provider
        
        if from_location.startswith('us') and to_location.startswith('us'):
            return 'low'
        elif from_location.startswith('eu') and to_location.startswith('eu'):
            return 'low'
        elif 'us' in from_location and 'ca' in to_location or 'ca' in from_location and 'us' in to_location:
            return 'medium'
        else:
            return 'high'

    def _calculate_location_score(self, profile: EnergyProfile, carbon_reduction: float, 
                                migration_cost_factor: float) -> float:
        """Calculate recommendation score for location"""
        # Base score from renewable percentage
        renewable_score = profile.renewable_percentage
        
        # Carbon reduction score
        carbon_score = min(100, carbon_reduction * 100)  # Scale carbon reduction
        
        # Cost penalty
        cost_penalty = (migration_cost_factor - 1) * 100  # Convert to percentage penalty
        
        # Combined score
        score = renewable_score + carbon_score - cost_penalty
        
        return score

    def _generate_green_scheduling(self, workload: WorkloadCarbonProfile, 
                                 energy_profile: EnergyProfile) -> Dict[str, Any]:
        """Generate green energy scheduling recommendations"""
        optimal_hours = self._find_optimal_green_hours(energy_profile)
        
        scheduling = {
            'current_carbon_intensity': energy_profile.carbon_intensity_g_co2_kwh,
            'optimal_scheduling_available': len(optimal_hours) > 0,
            'flexibility_window_hours': workload.flexibility_window_hours,
            'recommendations': []
        }
        
        if optimal_hours and workload.flexibility_window_hours > 0:
            best_hour = optimal_hours[0]
            
            scheduling['recommendations'] = [
                {
                    'action': 'delay_start',
                    'recommended_start_time': best_hour['timestamp'],
                    'hours_to_delay': best_hour['hour'],
                    'expected_renewable_percentage': best_hour['renewable_percentage'],
                    'expected_carbon_intensity': best_hour['carbon_intensity_g_co2_kwh'],
                    'carbon_reduction_kg': self._estimate_scheduling_carbon_reduction(workload, energy_profile, optimal_hours)
                }
            ]
            
            # Add multiple options if high flexibility
            if workload.flexibility_window_hours >= 12:
                for hour_option in optimal_hours[1:3]:  # Next 2 best options
                    scheduling['recommendations'].append({
                        'action': 'alternative_start',
                        'recommended_start_time': hour_option['timestamp'],
                        'hours_to_delay': hour_option['hour'],
                        'expected_renewable_percentage': hour_option['renewable_percentage'],
                        'expected_carbon_intensity': hour_option['carbon_intensity_g_co2_kwh'],
                        'carbon_reduction_kg': workload.estimated_power_consumption_kw * workload.estimated_runtime_hours * 
                                               (energy_profile.carbon_intensity_g_co2_kwh - hour_option['carbon_intensity_g_co2_kwh']) / 1000
                    })
        
        return scheduling

    def _estimate_green_cost_impact(self, workload: WorkloadCarbonProfile, 
                                  recommendations: List[Dict[str, Any]],
                                  best_alternative: Optional[Dict[str, Any]]) -> float:
        """Estimate cost impact of green optimizations"""
        cost_impact = 0.0
        
        # Migration cost
        if best_alternative:
            migration_cost_factor = best_alternative['migration_cost_factor']
            base_cost = workload.estimated_power_consumption_kw * workload.estimated_runtime_hours * 0.15  # Assume $0.15/kWh base
            migration_cost = base_cost * (migration_cost_factor - 1)
            cost_impact += migration_cost
        
        # Spot instance savings
        for rec in recommendations:
            if rec['type'] == 'spot_instance_optimization':
                savings_percent = rec['details']['estimated_cost_savings_percent']
                base_compute_cost = 10.0  # Assume $10 base cost
                cost_impact -= base_compute_cost * (savings_percent / 100)
        
        # Consolidation savings
        for rec in recommendations:
            if rec['type'] == 'workload_consolidation':
                power_reduction = rec['details']['estimated_power_reduction_percent']
                energy_cost_reduction = workload.estimated_power_consumption_kw * workload.estimated_runtime_hours * 0.15 * (power_reduction / 100)
                cost_impact -= energy_cost_reduction
        
        return round(cost_impact, 2)

    def _calculate_green_confidence(self, workload: WorkloadCarbonProfile,
                                  recommendations: List[Dict[str, Any]],
                                  alternatives: List[Dict[str, Any]]) -> float:
        """Calculate confidence score for green optimization"""
        confidence = 0.7  # Base confidence
        
        # Boost confidence if workload is flexible
        if workload.flexibility_window_hours > 6:
            confidence += 0.1
        
        if workload.can_be_migrated:
            confidence += 0.1
        
        if workload.can_be_paused:
            confidence += 0.05
        
        # Boost confidence if good alternatives exist
        if alternatives and alternatives[0]['carbon_reduction_kg'] > 1.0:
            confidence += 0.1
        
        # Reduce confidence for high-priority workloads (less flexibility)
        if workload.priority <= 2:
            confidence -= 0.1
        
        # Boost confidence for clear green preferences
        if workload.green_energy_requirement in [GreenPreference.MAXIMUM_GREEN, GreenPreference.PREFER_GREEN]:
            confidence += 0.05
        
        return min(1.0, max(0.0, confidence))

    def _generate_green_reasoning(self, workload: WorkloadCarbonProfile,
                                recommendations: List[Dict[str, Any]],
                                best_alternative: Optional[Dict[str, Any]],
                                preferences: Dict[str, Any]) -> str:
        """Generate reasoning for green optimization decisions"""
        reasons = []
        
        # Green preference reasoning
        reasons.append(f"Optimizing for {workload.green_energy_requirement.value} energy preference")
        
        # Current carbon footprint
        current_carbon = workload.estimated_power_consumption_kw * workload.estimated_runtime_hours * 0.5  # Rough estimate
        reasons.append(f"Current estimated carbon footprint: {current_carbon:.2f} kg CO2")
        
        # Flexibility reasoning
        if workload.flexibility_window_hours > 0:
            reasons.append(f"Workload has {workload.flexibility_window_hours}h flexibility window for green scheduling")
        
        # Migration reasoning
        if best_alternative:
            renewable_improvement = best_alternative['renewable_percentage']
            reasons.append(f"Migration to {best_alternative['location_name']} could achieve {renewable_improvement}% renewable energy")
        
        # Scheduling reasoning
        if any(rec['type'] == 'schedule_optimization' for rec in recommendations):
            reasons.append("Optimal timing can leverage periods of high renewable energy availability")
        
        # Instance optimization reasoning
        if any(rec['type'] == 'instance_optimization' for rec in recommendations):
            reasons.append("Energy-efficient instance types can reduce overall power consumption")
        
        # Budget reasoning
        if workload.carbon_budget_kg_co2:
            reasons.append(f"Working within carbon budget of {workload.carbon_budget_kg_co2} kg CO2")
        
        return "; ".join(reasons)

    def _create_error_optimization(self, workload_id: str, error_message: str) -> GreenOptimization:
        """Create error optimization result"""
        return GreenOptimization(
            workload_id=workload_id,
            current_location="unknown",
            recommended_actions=[],
            carbon_footprint_reduction_kg=0.0,
            renewable_energy_percentage=0.0,
            estimated_cost_impact=0.0,
            scheduling_recommendations={},
            location_recommendations=[],
            optimization_confidence=0.0,
            reasoning=f"Error: {error_message}"
        )

    async def monitor_green_opportunities(self):
        """Monitor green energy opportunities continuously"""
        try:
            # Update energy profiles with latest data
            await self._update_energy_profiles()
            
            # Check active workloads for optimization opportunities
            for workload_id, workload in self.active_workloads.items():
                # Skip if workload is not flexible
                if workload.flexibility_window_hours == 0 and not workload.can_be_migrated:
                    continue
                
                # Check if current conditions are suboptimal
                current_location = 'us_west_2'  # Default, would be tracked per workload
                current_profile = self.energy_profiles.get(current_location)
                
                if current_profile and current_profile.carbon_intensity_g_co2_kwh > 300:
                    logger.info(f"High carbon intensity ({current_profile.carbon_intensity_g_co2_kwh} gCO2/kWh) "
                              f"for workload {workload_id} - considering optimization")
            
            # Update historical data
            self._update_green_energy_history()
            
            logger.debug("Green energy monitoring cycle completed")
            
        except Exception as e:
            logger.error(f"Error in green energy monitoring: {e}")

    async def _update_energy_profiles(self):
        """Update energy profiles with latest data"""
        for location_id, profile in self.energy_profiles.items():
            try:
                # In production, this would fetch real-time energy data
                # For now, simulate profile updates
                
                # Update forecast
                profile.forecast_next_24h = self._generate_energy_forecast({
                    'current_energy_mix': profile.current_energy_mix,
                    'renewable_percentage': profile.renewable_percentage,
                    'carbon_intensity': profile.carbon_intensity_g_co2_kwh
                })
                
                profile.last_updated = datetime.utcnow()
                
                logger.debug(f"Updated energy profile for {location_id}")
                
            except Exception as e:
                logger.error(f"Failed to update energy profile for {location_id}: {e}")

    def _update_green_energy_history(self):
        """Update historical green energy data"""
        timestamp = datetime.utcnow()
        
        # Record current state of all locations
        history_entry = {
            'timestamp': timestamp.isoformat(),
            'locations': {}
        }
        
        for location_id, profile in self.energy_profiles.items():
            history_entry['locations'][location_id] = {
                'renewable_percentage': profile.renewable_percentage,
                'carbon_intensity': profile.carbon_intensity_g_co2_kwh,
                'energy_cost': profile.energy_cost_per_kwh
            }
        
        self.green_energy_history.append(history_entry)
        
        # Keep only last 7 days of history
        cutoff_time = timestamp - timedelta(days=7)
        self.green_energy_history = [
            entry for entry in self.green_energy_history
            if datetime.fromisoformat(entry['timestamp']) >= cutoff_time
        ]

    def get_green_energy_status(self) -> Dict[str, Any]:
        """Get current green energy status across all locations"""
        try:
            status = {
                'timestamp': datetime.utcnow().isoformat(),
                'locations': {},
                'global_summary': {
                    'avg_renewable_percentage': 0,
                    'avg_carbon_intensity': 0,
                    'greenest_location': None,
                    'least_green_location': None
                },
                'recommendations_summary': {
                    'locations_with_high_renewable': [],
                    'locations_with_low_carbon': [],
                    'best_times_for_scheduling': []
                }
            }
            
            renewable_percentages = []
            carbon_intensities = []
            
            # Process each location
            for location_id, profile in self.energy_profiles.items():
                location_status = {
                    'location_name': profile.location_name,
                    'region': profile.region,
                    'country': profile.country,
                    'renewable_percentage': profile.renewable_percentage,
                    'carbon_intensity_g_co2_kwh': profile.carbon_intensity_g_co2_kwh,
                    'carbon_intensity_level': profile.carbon_intensity_level.value,
                    'energy_cost_per_kwh': profile.energy_cost_per_kwh,
                    'energy_mix': {source.value: percentage for source, percentage in profile.current_energy_mix.items()},
                    'next_green_window': self._find_next_green_window(profile)
                }
                
                status['locations'][location_id] = location_status
                renewable_percentages.append(profile.renewable_percentage)
                carbon_intensities.append(profile.carbon_intensity_g_co2_kwh)
            
            # Calculate global summary
            if renewable_percentages:
                status['global_summary']['avg_renewable_percentage'] = round(sum(renewable_percentages) / len(renewable_percentages), 1)
                status['global_summary']['avg_carbon_intensity'] = round(sum(carbon_intensities) / len(carbon_intensities), 0)
                
                # Find greenest and least green locations
                greenest_location = max(self.energy_profiles.items(), key=lambda x: x[1].renewable_percentage)
                least_green_location = min(self.energy_profiles.items(), key=lambda x: x[1].renewable_percentage)
                
                status['global_summary']['greenest_location'] = {
                    'location_id': greenest_location[0],
                    'location_name': greenest_location[1].location_name,
                    'renewable_percentage': greenest_location[1].renewable_percentage
                }
                
                status['global_summary']['least_green_location'] = {
                    'location_id': least_green_location[0],
                    'location_name': least_green_location[1].location_name,
                    'renewable_percentage': least_green_location[1].renewable_percentage
                }
            
            # Generate recommendations
            for location_id, profile in self.energy_profiles.items():
                if profile.renewable_percentage > 70:
                    status['recommendations_summary']['locations_with_high_renewable'].append({
                        'location_id': location_id,
                        'location_name': profile.location_name,
                        'renewable_percentage': profile.renewable_percentage
                    })
                
                if profile.carbon_intensity_g_co2_kwh < 200:
                    status['recommendations_summary']['locations_with_low_carbon'].append({
                        'location_id': location_id,
                        'location_name': profile.location_name,
                        'carbon_intensity': profile.carbon_intensity_g_co2_kwh
                    })
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get green energy status: {e}")
            return {'error': str(e)}

    def _find_next_green_window(self, profile: EnergyProfile) -> Dict[str, Any]:
        """Find the next optimal green energy window"""
        if not profile.forecast_next_24h:
            return {}
        
        # Find the hour with highest green score in the next 12 hours
        next_12h = profile.forecast_next_24h[:12]
        best_hour = max(next_12h, key=lambda x: x['green_score'])
        
        return {
            'start_time': best_hour['timestamp'],
            'hours_from_now': best_hour['hour'],
            'renewable_percentage': best_hour['renewable_percentage'],
            'carbon_intensity': best_hour['carbon_intensity_g_co2_kwh'],
            'green_score': best_hour['green_score']
        }

    def get_carbon_footprint_report(self, workload_ids: List[str] = None) -> Dict[str, Any]:
        """Generate carbon footprint report for workloads"""
        try:
            report = {
                'timestamp': datetime.utcnow().isoformat(),
                'report_period': '24_hours',
                'workloads_analyzed': 0,
                'total_carbon_footprint_kg': 0.0,
                'average_renewable_percentage': 0.0,
                'workload_details': [],
                'optimization_opportunities': {
                    'scheduling_optimizations': 0,
                    'location_migrations': 0,
                    'instance_optimizations': 0,
                    'total_potential_reduction_kg': 0.0
                }
            }
            
            # Analyze specified workloads or all active workloads
            workloads_to_analyze = workload_ids or list(self.active_workloads.keys())
            
            for workload_id in workloads_to_analyze:
                if workload_id in self.active_workloads:
                    workload = self.active_workloads[workload_id]
                    
                    # Use default location for analysis
                    location = 'us_west_2'
                    profile = self.energy_profiles.get(location)
                    
                    if profile:
                        carbon_footprint = self._calculate_carbon_footprint(workload, profile)
                        
                        workload_detail = {
                            'workload_id': workload_id,
                            'current_location': location,
                            'estimated_carbon_footprint_kg': carbon_footprint,
                            'renewable_percentage': profile.renewable_percentage,
                            'carbon_intensity': profile.carbon_intensity_g_co2_kwh,
                            'optimization_potential': self._assess_optimization_potential(workload)
                        }
                        
                        report['workload_details'].append(workload_detail)
                        report['total_carbon_footprint_kg'] += carbon_footprint
                        report['workloads_analyzed'] += 1
            
            # Calculate averages
            if report['workloads_analyzed'] > 0:
                total_renewable = sum(detail['renewable_percentage'] for detail in report['workload_details'])
                report['average_renewable_percentage'] = round(total_renewable / report['workloads_analyzed'], 1)
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate carbon footprint report: {e}")
            return {'error': str(e)}

    def _assess_optimization_potential(self, workload: WorkloadCarbonProfile) -> Dict[str, Any]:
        """Assess optimization potential for a workload"""
        potential = {
            'scheduling_optimization': workload.flexibility_window_hours > 0,
            'location_migration': workload.can_be_migrated,
            'instance_optimization': True,  # Always possible
            'auto_scaling_optimization': workload.can_be_paused,
            'estimated_reduction_potential': 'low'
        }
        
        # Estimate reduction potential
        if workload.green_energy_requirement == GreenPreference.MAXIMUM_GREEN and workload.can_be_migrated:
            potential['estimated_reduction_potential'] = 'high'
        elif workload.flexibility_window_hours > 6 or workload.can_be_migrated:
            potential['estimated_reduction_potential'] = 'medium'
        
        return potential