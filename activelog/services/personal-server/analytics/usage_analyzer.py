"""
ActiveLog Personal Server - Usage Pattern Analyzer
Analyzes user's FishingLog/BusinessLog usage patterns to optimize personal server deployment
"""

from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone, timedelta
import asyncio
import json
import statistics
from collections import defaultdict, Counter
import numpy as np

class UsageFrequency(Enum):
    """Usage frequency categories"""
    NEVER = "never"
    RARE = "rare"           # < 1x per month
    OCCASIONAL = "occasional" # 1-4x per month  
    REGULAR = "regular"     # 1-7x per week
    FREQUENT = "frequent"   # Daily
    INTENSIVE = "intensive" # Multiple times per day

class FeatureCategory(Enum):
    """Categories of application features"""
    CORE = "core"                    # Essential features
    DATA_ENTRY = "data_entry"        # Data input/logging
    REPORTING = "reporting"          # Reports and analytics
    EXPORT_IMPORT = "export_import"  # Data exchange
    COLLABORATION = "collaboration"  # Multi-user features
    AUTOMATION = "automation"        # Automated processes
    INTEGRATION = "integration"      # Third-party integrations
    ADVANCED = "advanced"           # Power user features
    MOBILE = "mobile"               # Mobile-specific features
    OFFLINE = "offline"             # Offline capabilities

@dataclass
class FeatureUsage:
    """Usage statistics for a specific feature"""
    feature_name: str
    category: FeatureCategory
    usage_frequency: UsageFrequency
    total_uses: int
    unique_days_used: int
    average_session_duration: float  # minutes
    peak_usage_hours: List[int]      # Hours of day (0-23)
    data_volume_mb: float
    cpu_intensity: float             # 0-1 scale
    memory_usage_mb: float
    network_usage_mb: float
    storage_requirements_mb: float
    user_satisfaction_score: float   # 0-10 scale if available

@dataclass
class ApplicationUsageProfile:
    """Complete usage profile for an application"""
    application_name: str
    user_id: str
    analysis_period_days: int
    total_sessions: int
    total_active_hours: float
    features_used: Dict[str, FeatureUsage]
    usage_patterns: Dict[str, Any]
    resource_requirements: Dict[str, float]
    optimization_opportunities: List[str]

class UsagePatternAnalyzer:
    """
    Analyzes user's application usage patterns to identify optimization opportunities
    for personal server deployment
    """
    
    def __init__(self):
        # Feature definitions for different applications
        self.application_features = self._initialize_application_features()
        self.usage_thresholds = self._initialize_usage_thresholds()
        self.optimization_rules = self._initialize_optimization_rules()
        
    def _initialize_application_features(self) -> Dict[str, Dict[str, Any]]:
        """Initialize feature definitions for different applications"""
        return {
            "FishingLog": {
                "catch_logging": {
                    "category": FeatureCategory.DATA_ENTRY,
                    "cpu_intensity": 0.2,
                    "memory_usage": 50,
                    "storage_per_entry": 2.5,
                    "network_usage": 1.0
                },
                "species_database": {
                    "category": FeatureCategory.CORE,
                    "cpu_intensity": 0.3,
                    "memory_usage": 100,
                    "storage_per_entry": 0.5,
                    "network_usage": 0.1
                },
                "location_tracking": {
                    "category": FeatureCategory.CORE,
                    "cpu_intensity": 0.4,
                    "memory_usage": 80,
                    "storage_per_entry": 1.0,
                    "network_usage": 2.0
                },
                "weather_integration": {
                    "category": FeatureCategory.INTEGRATION,
                    "cpu_intensity": 0.3,
                    "memory_usage": 60,
                    "storage_per_entry": 0.5,
                    "network_usage": 5.0
                },
                "photo_management": {
                    "category": FeatureCategory.DATA_ENTRY,
                    "cpu_intensity": 0.6,
                    "memory_usage": 200,
                    "storage_per_entry": 5000,  # 5MB per photo
                    "network_usage": 10.0
                },
                "trip_reports": {
                    "category": FeatureCategory.REPORTING,
                    "cpu_intensity": 0.4,
                    "memory_usage": 150,
                    "storage_per_entry": 100,
                    "network_usage": 2.0
                },
                "catch_statistics": {
                    "category": FeatureCategory.REPORTING,
                    "cpu_intensity": 0.7,
                    "memory_usage": 300,
                    "storage_per_entry": 50,
                    "network_usage": 1.0
                },
                "data_export": {
                    "category": FeatureCategory.EXPORT_IMPORT,
                    "cpu_intensity": 0.5,
                    "memory_usage": 250,
                    "storage_per_entry": 0,
                    "network_usage": 20.0
                },
                "mobile_sync": {
                    "category": FeatureCategory.MOBILE,
                    "cpu_intensity": 0.3,
                    "memory_usage": 100,
                    "storage_per_entry": 0,
                    "network_usage": 15.0
                },
                "offline_mode": {
                    "category": FeatureCategory.OFFLINE,
                    "cpu_intensity": 0.4,
                    "memory_usage": 500,
                    "storage_per_entry": 0,
                    "network_usage": 0
                }
            },
            
            "BusinessLog": {
                "transaction_logging": {
                    "category": FeatureCategory.DATA_ENTRY,
                    "cpu_intensity": 0.3,
                    "memory_usage": 75,
                    "storage_per_entry": 5.0,
                    "network_usage": 2.0
                },
                "financial_reporting": {
                    "category": FeatureCategory.REPORTING,
                    "cpu_intensity": 0.8,
                    "memory_usage": 400,
                    "storage_per_entry": 200,
                    "network_usage": 5.0
                },
                "tax_preparation": {
                    "category": FeatureCategory.ADVANCED,
                    "cpu_intensity": 0.9,
                    "memory_usage": 600,
                    "storage_per_entry": 500,
                    "network_usage": 10.0
                },
                "invoice_generation": {
                    "category": FeatureCategory.AUTOMATION,
                    "cpu_intensity": 0.4,
                    "memory_usage": 150,
                    "storage_per_entry": 50,
                    "network_usage": 3.0
                },
                "expense_tracking": {
                    "category": FeatureCategory.DATA_ENTRY,
                    "cpu_intensity": 0.2,
                    "memory_usage": 60,
                    "storage_per_entry": 3.0,
                    "network_usage": 1.0
                },
                "customer_management": {
                    "category": FeatureCategory.CORE,
                    "cpu_intensity": 0.3,
                    "memory_usage": 100,
                    "storage_per_entry": 10.0,
                    "network_usage": 2.0
                },
                "inventory_tracking": {
                    "category": FeatureCategory.CORE,
                    "cpu_intensity": 0.4,
                    "memory_usage": 200,
                    "storage_per_entry": 8.0,
                    "network_usage": 1.5
                },
                "bank_integration": {
                    "category": FeatureCategory.INTEGRATION,
                    "cpu_intensity": 0.6,
                    "memory_usage": 300,
                    "storage_per_entry": 20.0,
                    "network_usage": 25.0
                },
                "multi_user_access": {
                    "category": FeatureCategory.COLLABORATION,
                    "cpu_intensity": 0.5,
                    "memory_usage": 400,
                    "storage_per_entry": 0,
                    "network_usage": 30.0
                },
                "backup_sync": {
                    "category": FeatureCategory.CORE,
                    "cpu_intensity": 0.3,
                    "memory_usage": 200,
                    "storage_per_entry": 0,
                    "network_usage": 50.0
                }
            }
        }
    
    def _initialize_usage_thresholds(self) -> Dict[str, Any]:
        """Initialize thresholds for usage frequency classification"""
        return {
            "frequency_thresholds": {
                UsageFrequency.NEVER: 0,
                UsageFrequency.RARE: 1,         # 1 use per month
                UsageFrequency.OCCASIONAL: 4,   # 4 uses per month
                UsageFrequency.REGULAR: 7,      # 7 uses per month (weekly)
                UsageFrequency.FREQUENT: 30,    # Daily
                UsageFrequency.INTENSIVE: 60    # Multiple times per day
            },
            "resource_thresholds": {
                "low_cpu": 0.3,
                "medium_cpu": 0.6,
                "high_cpu": 0.8,
                "low_memory": 100,      # MB
                "medium_memory": 300,
                "high_memory": 500,
                "low_storage": 100,     # MB per month
                "medium_storage": 1000,
                "high_storage": 10000,
                "low_network": 10,      # MB per month
                "medium_network": 100,
                "high_network": 1000
            }
        }
    
    def _initialize_optimization_rules(self) -> List[Dict[str, Any]]:
        """Initialize optimization rules based on usage patterns"""
        return [
            {
                "name": "remove_unused_features",
                "condition": lambda usage: usage.usage_frequency == UsageFrequency.NEVER,
                "savings": {"cpu": 0.1, "memory": 0.2, "storage": 0.3},
                "description": "Remove completely unused features"
            },
            {
                "name": "optimize_rare_features",
                "condition": lambda usage: usage.usage_frequency == UsageFrequency.RARE,
                "savings": {"cpu": 0.05, "memory": 0.1, "storage": 0.1},
                "description": "Optimize rarely used features for lower resource usage"
            },
            {
                "name": "cache_frequent_features",
                "condition": lambda usage: usage.usage_frequency in [UsageFrequency.FREQUENT, UsageFrequency.INTENSIVE],
                "optimization": {"memory": 1.2, "cpu": 0.8},
                "description": "Add caching for frequently used features"
            },
            {
                "name": "offline_capable_features",
                "condition": lambda usage: usage.network_usage_mb > 50,
                "optimization": {"storage": 1.3, "network": 0.3},
                "description": "Make network-heavy features work offline"
            }
        ]
    
    async def analyze_user_patterns(self, user_id: str, applications: List[str],
                                  period_days: int = 30) -> Dict[str, Any]:
        """
        Analyze user's usage patterns across specified applications
        """
        
        analysis_results = {
            "user_id": user_id,
            "analysis_period": period_days,
            "applications": {},
            "cross_app_insights": {},
            "optimization_suggestions": [],
            "recommended_tier": "standard",
            "potential_cost_savings": {}
        }
        
        # Analyze each application
        app_profiles = {}
        for app_name in applications:
            if app_name in self.application_features:
                profile = await self._analyze_application_usage(
                    user_id, app_name, period_days
                )
                app_profiles[app_name] = profile
                analysis_results["applications"][app_name] = profile
        
        # Perform cross-application analysis
        if len(app_profiles) > 1:
            cross_insights = await self._analyze_cross_application_patterns(app_profiles)
            analysis_results["cross_app_insights"] = cross_insights
        
        # Generate optimization suggestions
        optimization_suggestions = await self._generate_optimization_suggestions(app_profiles)
        analysis_results["optimization_suggestions"] = optimization_suggestions
        
        # Calculate recommended tier
        recommended_tier = await self._calculate_recommended_tier(app_profiles)
        analysis_results["recommended_tier"] = recommended_tier
        
        # Estimate cost savings
        cost_savings = await self._estimate_cost_savings(app_profiles, optimization_suggestions)
        analysis_results["potential_cost_savings"] = cost_savings
        
        return analysis_results
    
    async def _analyze_application_usage(self, user_id: str, app_name: str,
                                       period_days: int) -> ApplicationUsageProfile:
        """Analyze usage patterns for a specific application"""
        
        # This would normally connect to actual usage data
        # For now, we'll simulate realistic usage patterns
        usage_data = await self._simulate_usage_data(user_id, app_name, period_days)
        
        features_used = {}
        total_sessions = usage_data["total_sessions"]
        total_active_hours = usage_data["total_active_hours"]
        
        # Analyze each feature
        app_features = self.application_features[app_name]
        for feature_name, feature_config in app_features.items():
            
            # Simulate feature usage based on user patterns
            feature_usage = await self._analyze_feature_usage(
                feature_name, feature_config, usage_data, period_days
            )
            features_used[feature_name] = feature_usage
        
        # Calculate resource requirements
        resource_requirements = self._calculate_resource_requirements(features_used)
        
        # Identify optimization opportunities
        optimization_opportunities = self._identify_feature_optimizations(features_used)
        
        # Extract usage patterns
        usage_patterns = {
            "peak_hours": usage_data.get("peak_hours", [9, 10, 11, 14, 15, 16]),
            "usage_distribution": usage_data.get("usage_distribution", {}),
            "session_patterns": usage_data.get("session_patterns", {}),
            "seasonal_trends": usage_data.get("seasonal_trends", {})
        }
        
        return ApplicationUsageProfile(
            application_name=app_name,
            user_id=user_id,
            analysis_period_days=period_days,
            total_sessions=total_sessions,
            total_active_hours=total_active_hours,
            features_used=features_used,
            usage_patterns=usage_patterns,
            resource_requirements=resource_requirements,
            optimization_opportunities=optimization_opportunities
        )
    
    async def _simulate_usage_data(self, user_id: str, app_name: str,
                                 period_days: int) -> Dict[str, Any]:
        """Simulate realistic usage data for analysis"""
        
        # Create deterministic but varied usage patterns based on user_id
        import hashlib
        user_hash = int(hashlib.md5(f"{user_id}_{app_name}".encode()).hexdigest(), 16)
        np.random.seed(user_hash % 2**32)
        
        # Generate usage patterns
        if app_name == "FishingLog":
            # Fishing is seasonal and weekend-heavy
            base_sessions_per_month = np.random.randint(4, 20)  # 4-20 fishing trips per month
            sessions = int(base_sessions_per_month * (period_days / 30))
            active_hours = sessions * np.random.uniform(2, 6)  # 2-6 hours per trip
            peak_hours = [6, 7, 8, 17, 18, 19]  # Early morning and evening
            
        elif app_name == "BusinessLog":
            # Business use is more regular, weekday-heavy
            base_sessions_per_month = np.random.randint(15, 45)  # 15-45 business sessions per month
            sessions = int(base_sessions_per_month * (period_days / 30))
            active_hours = sessions * np.random.uniform(0.5, 2.0)  # 30min-2hours per session
            peak_hours = [9, 10, 11, 14, 15, 16]  # Business hours
        
        else:
            # Default pattern
            sessions = int(np.random.uniform(10, 30) * (period_days / 30))
            active_hours = sessions * np.random.uniform(1, 3)
            peak_hours = [9, 10, 11, 14, 15, 16]
        
        return {
            "total_sessions": sessions,
            "total_active_hours": active_hours,
            "peak_hours": peak_hours,
            "usage_distribution": {
                "weekday": np.random.uniform(0.6, 0.8),
                "weekend": np.random.uniform(0.2, 0.4)
            },
            "session_patterns": {
                "average_duration": active_hours / max(sessions, 1),
                "max_concurrent": 1  # Single user for personal server
            },
            "seasonal_trends": {
                "spring": np.random.uniform(0.8, 1.2),
                "summer": np.random.uniform(0.9, 1.3),
                "fall": np.random.uniform(0.7, 1.1),
                "winter": np.random.uniform(0.5, 0.9)
            }
        }
    
    async def _analyze_feature_usage(self, feature_name: str, feature_config: Dict[str, Any],
                                   usage_data: Dict[str, Any], period_days: int) -> FeatureUsage:
        """Analyze usage patterns for a specific feature"""
        
        total_sessions = usage_data["total_sessions"]
        
        # Simulate feature usage based on category and total sessions
        category = FeatureCategory(feature_config["category"])
        
        if category == FeatureCategory.CORE:
            # Core features used in most sessions
            usage_probability = np.random.uniform(0.8, 0.95)
        elif category == FeatureCategory.DATA_ENTRY:
            # Data entry used frequently
            usage_probability = np.random.uniform(0.6, 0.9)
        elif category == FeatureCategory.REPORTING:
            # Reporting used less frequently
            usage_probability = np.random.uniform(0.2, 0.5)
        elif category == FeatureCategory.ADVANCED:
            # Advanced features used rarely
            usage_probability = np.random.uniform(0.05, 0.3)
        elif category == FeatureCategory.INTEGRATION:
            # Integration features vary widely
            usage_probability = np.random.uniform(0.1, 0.7)
        else:
            # Default probability
            usage_probability = np.random.uniform(0.3, 0.7)
        
        total_uses = int(total_sessions * usage_probability)
        unique_days_used = min(total_uses, period_days)
        
        # Classify usage frequency
        monthly_uses = (total_uses / period_days) * 30
        usage_frequency = self._classify_usage_frequency(monthly_uses)
        
        # Calculate resource usage
        avg_session_duration = np.random.uniform(5, 30)  # 5-30 minutes
        data_volume = total_uses * feature_config.get("storage_per_entry", 1.0) / 1024  # Convert to MB
        network_usage = total_uses * feature_config.get("network_usage", 1.0)
        
        return FeatureUsage(
            feature_name=feature_name,
            category=category,
            usage_frequency=usage_frequency,
            total_uses=total_uses,
            unique_days_used=unique_days_used,
            average_session_duration=avg_session_duration,
            peak_usage_hours=usage_data["peak_hours"],
            data_volume_mb=data_volume,
            cpu_intensity=feature_config.get("cpu_intensity", 0.3),
            memory_usage_mb=feature_config.get("memory_usage", 100),
            network_usage_mb=network_usage,
            storage_requirements_mb=data_volume,
            user_satisfaction_score=np.random.uniform(7.0, 9.5)  # Generally satisfied users
        )
    
    def _classify_usage_frequency(self, monthly_uses: float) -> UsageFrequency:
        """Classify usage frequency based on monthly usage count"""
        
        thresholds = self.usage_thresholds["frequency_thresholds"]
        
        if monthly_uses >= thresholds[UsageFrequency.INTENSIVE]:
            return UsageFrequency.INTENSIVE
        elif monthly_uses >= thresholds[UsageFrequency.FREQUENT]:
            return UsageFrequency.FREQUENT
        elif monthly_uses >= thresholds[UsageFrequency.REGULAR]:
            return UsageFrequency.REGULAR
        elif monthly_uses >= thresholds[UsageFrequency.OCCASIONAL]:
            return UsageFrequency.OCCASIONAL
        elif monthly_uses >= thresholds[UsageFrequency.RARE]:
            return UsageFrequency.RARE
        else:
            return UsageFrequency.NEVER
    
    def _calculate_resource_requirements(self, features_used: Dict[str, FeatureUsage]) -> Dict[str, float]:
        """Calculate total resource requirements based on feature usage"""
        
        total_cpu = 0
        total_memory = 0
        total_storage = 0
        total_network = 0
        
        for feature_usage in features_used.values():
            if feature_usage.usage_frequency != UsageFrequency.NEVER:
                # Weight by usage frequency
                frequency_weight = self._get_frequency_weight(feature_usage.usage_frequency)
                
                total_cpu += feature_usage.cpu_intensity * frequency_weight
                total_memory += feature_usage.memory_usage_mb * frequency_weight
                total_storage += feature_usage.storage_requirements_mb
                total_network += feature_usage.network_usage_mb
        
        return {
            "cpu_utilization": min(total_cpu, 1.0),  # Cap at 100%
            "memory_mb": total_memory,
            "storage_mb": total_storage,
            "network_mb_monthly": total_network,
            "peak_memory_mb": total_memory * 1.5,  # Account for peak usage
            "recommended_cores": max(1, int(total_cpu / 0.7)),  # Leave 30% headroom
            "recommended_memory_gb": max(2, int(total_memory / 1024 * 1.3))  # 30% headroom
        }
    
    def _get_frequency_weight(self, frequency: UsageFrequency) -> float:
        """Get weight multiplier based on usage frequency"""
        
        weights = {
            UsageFrequency.NEVER: 0.0,
            UsageFrequency.RARE: 0.1,
            UsageFrequency.OCCASIONAL: 0.3,
            UsageFrequency.REGULAR: 0.6,
            UsageFrequency.FREQUENT: 0.9,
            UsageFrequency.INTENSIVE: 1.0
        }
        
        return weights.get(frequency, 0.5)
    
    def _identify_feature_optimizations(self, features_used: Dict[str, FeatureUsage]) -> List[str]:
        """Identify optimization opportunities for features"""
        
        optimizations = []
        
        for feature_name, feature_usage in features_used.items():
            # Apply optimization rules
            for rule in self.optimization_rules:
                if rule["condition"](feature_usage):
                    optimizations.append(f"{rule['name']}: {feature_name} - {rule['description']}")
        
        # Add specific optimizations based on patterns
        unused_features = [name for name, usage in features_used.items() 
                          if usage.usage_frequency == UsageFrequency.NEVER]
        
        if len(unused_features) > 3:
            optimizations.append(f"Remove {len(unused_features)} unused features to reduce resource usage")
        
        high_network_features = [name for name, usage in features_used.items()
                               if usage.network_usage_mb > 100]
        
        if high_network_features:
            optimizations.append(f"Optimize network usage for: {', '.join(high_network_features)}")
        
        return optimizations
    
    async def _analyze_cross_application_patterns(self, app_profiles: Dict[str, ApplicationUsageProfile]) -> Dict[str, Any]:
        """Analyze patterns across multiple applications"""
        
        cross_insights = {
            "shared_peak_hours": [],
            "resource_overlap": {},
            "complementary_usage": [],
            "optimization_synergies": []
        }
        
        # Find shared peak hours
        all_peak_hours = []
        for profile in app_profiles.values():
            if "peak_hours" in profile.usage_patterns:
                all_peak_hours.extend(profile.usage_patterns["peak_hours"])
        
        if all_peak_hours:
            hour_counts = Counter(all_peak_hours)
            shared_peaks = [hour for hour, count in hour_counts.items() if count > 1]
            cross_insights["shared_peak_hours"] = shared_peaks
        
        # Analyze resource overlap
        total_resources = defaultdict(float)
        for profile in app_profiles.values():
            for resource, value in profile.resource_requirements.items():
                total_resources[resource] += value
        
        cross_insights["resource_overlap"] = dict(total_resources)
        
        # Identify complementary usage (apps used at different times)
        app_schedules = {}
        for app_name, profile in app_profiles.items():
            if "peak_hours" in profile.usage_patterns:
                app_schedules[app_name] = set(profile.usage_patterns["peak_hours"])
        
        for app1, hours1 in app_schedules.items():
            for app2, hours2 in app_schedules.items():
                if app1 != app2:
                    overlap = len(hours1.intersection(hours2))
                    if overlap < 2:  # Minimal overlap
                        cross_insights["complementary_usage"].append(f"{app1} and {app2} have complementary usage patterns")
        
        return cross_insights
    
    async def _generate_optimization_suggestions(self, app_profiles: Dict[str, ApplicationUsageProfile]) -> List[Dict[str, Any]]:
        """Generate comprehensive optimization suggestions"""
        
        suggestions = []
        
        # Analyze total resource usage
        total_cpu = sum(profile.resource_requirements.get("cpu_utilization", 0) 
                       for profile in app_profiles.values())
        total_memory = sum(profile.resource_requirements.get("memory_mb", 0) 
                          for profile in app_profiles.values())
        total_storage = sum(profile.resource_requirements.get("storage_mb", 0) 
                           for profile in app_profiles.values())
        
        # Server sizing suggestions
        if total_cpu < 0.3:
            suggestions.append({
                "type": "server_sizing",
                "priority": "high",
                "suggestion": "Use micro instance - current CPU usage is very low",
                "potential_savings": "60-70% cost reduction",
                "technical_details": f"Current CPU utilization: {total_cpu:.1%}"
            })
        elif total_cpu > 0.8:
            suggestions.append({
                "type": "server_sizing", 
                "priority": "high",
                "suggestion": "Consider larger instance or optimization - high CPU usage",
                "potential_savings": "Improved performance, avoid slowdowns",
                "technical_details": f"Current CPU utilization: {total_cpu:.1%}"
            })
        
        # Memory optimization
        if total_memory < 1024:  # Less than 1GB
            suggestions.append({
                "type": "memory_optimization",
                "priority": "medium",
                "suggestion": "2GB RAM sufficient - optimize for cost",
                "potential_savings": "30-40% memory cost reduction",
                "technical_details": f"Current memory usage: {total_memory:.0f}MB"
            })
        
        # Storage optimization
        if total_storage < 5000:  # Less than 5GB
            suggestions.append({
                "type": "storage_optimization",
                "priority": "low",
                "suggestion": "Use SSD storage for better performance at minimal cost increase",
                "potential_savings": "50% faster data access",
                "technical_details": f"Current storage: {total_storage/1024:.1f}GB"
            })
        
        # Feature-specific optimizations
        for app_name, profile in app_profiles.values():
            for optimization in profile.optimization_opportunities:
                suggestions.append({
                    "type": "feature_optimization",
                    "priority": "medium", 
                    "suggestion": f"{app_name}: {optimization}",
                    "application": app_name
                })
        
        return suggestions
    
    async def _calculate_recommended_tier(self, app_profiles: Dict[str, ApplicationUsageProfile]) -> str:
        """Calculate recommended server tier based on usage analysis"""
        
        # Calculate total resource requirements
        total_cpu = sum(profile.resource_requirements.get("cpu_utilization", 0) 
                       for profile in app_profiles.values())
        total_memory = sum(profile.resource_requirements.get("memory_mb", 0) 
                          for profile in app_profiles.values())
        total_storage = sum(profile.resource_requirements.get("storage_mb", 0) 
                           for profile in app_profiles.values())
        
        # Calculate usage intensity
        total_sessions = sum(profile.total_sessions for profile in app_profiles.values())
        total_hours = sum(profile.total_active_hours for profile in app_profiles.values())
        
        # Tier calculation logic
        if total_cpu < 0.2 and total_memory < 512 and total_sessions < 20:
            return "micro"
        elif total_cpu < 0.4 and total_memory < 1024 and total_sessions < 50:
            return "small"
        elif total_cpu < 0.6 and total_memory < 2048 and total_sessions < 100:
            return "standard"
        elif total_cpu < 0.8 and total_memory < 4096:
            return "large"
        else:
            return "xlarge"
    
    async def _estimate_cost_savings(self, app_profiles: Dict[str, ApplicationUsageProfile],
                                   optimization_suggestions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Estimate potential cost savings from optimizations"""
        
        # Base costs (simplified)
        base_monthly_cost = 50.0  # $50/month for standard server
        
        # Calculate potential savings from suggestions
        total_savings = 0
        savings_breakdown = {}
        
        for suggestion in optimization_suggestions:
            if "potential_savings" in suggestion and "%" in suggestion["potential_savings"]:
                # Extract percentage savings
                import re
                percentage_match = re.search(r'(\d+)-?(\d+)?%', suggestion["potential_savings"])
                if percentage_match:
                    min_pct = int(percentage_match.group(1))
                    max_pct = int(percentage_match.group(2)) if percentage_match.group(2) else min_pct
                    avg_pct = (min_pct + max_pct) / 2
                    
                    suggestion_savings = base_monthly_cost * (avg_pct / 100)
                    total_savings += suggestion_savings
                    savings_breakdown[suggestion["type"]] = suggestion_savings
        
        return {
            "base_monthly_cost": base_monthly_cost,
            "optimized_monthly_cost": max(10, base_monthly_cost - total_savings),
            "monthly_savings": total_savings,
            "annual_savings": total_savings * 12,
            "savings_percentage": (total_savings / base_monthly_cost) * 100,
            "savings_breakdown": savings_breakdown,
            "payback_period_months": 0  # Personal server deployment
        }
    
    async def health_check(self) -> bool:
        """Health check for the usage analyzer"""
        try:
            # Verify data structures are initialized
            assert self.application_features is not None
            assert self.usage_thresholds is not None
            assert self.optimization_rules is not None
            
            # Verify we can process basic analysis
            test_result = await self._simulate_usage_data("test_user", "FishingLog", 30)
            assert isinstance(test_result, dict)
            assert "total_sessions" in test_result
            
            return True
            
        except Exception as e:
            logger.error(f"Usage analyzer health check failed: {e}")
            return False