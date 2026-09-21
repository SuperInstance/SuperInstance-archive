from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import Dict, List, Optional, Any, Tuple
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import json
import hashlib

from ..database import (
    User, UserChoice, ChoiceType, PrivacyConvenienceDecision,
    PrivacySetting, ConvenienceFeature, DataSharingDecision
)

logger = logging.getLogger(__name__)

class PrivacyVsConvenienceOptions:
    """Manage privacy vs convenience trade-offs and provide intelligent recommendations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def evaluate_privacy_convenience_tradeoff(
        self,
        user_id: uuid.UUID,
        feature_request: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Evaluate privacy vs convenience tradeoff for a requested feature"""
        
        try:
            # Analyze the feature's privacy implications
            privacy_analysis = await self._analyze_privacy_implications(feature_request)
            
            # Analyze the convenience benefits
            convenience_analysis = await self._analyze_convenience_benefits(feature_request)
            
            # Get user's privacy preferences and history
            user_privacy_profile = await self._get_user_privacy_profile(user_id)
            privacy_history = await self._get_privacy_decision_history(user_id)
            
            # Generate configuration options
            config_options = await self._generate_privacy_convenience_configs(
                feature_request, privacy_analysis, convenience_analysis
            )
            
            # Evaluate each configuration
            evaluations = []
            for config in config_options:
                evaluation = await self._evaluate_privacy_config(
                    user_id, feature_request, config, privacy_analysis, convenience_analysis
                )
                evaluations.append(evaluation)
            
            # Calculate user preference weights
            preference_weights = await self._calculate_privacy_preference_weights(
                user_id, user_privacy_profile, privacy_history, user_preferences, context
            )
            
            # Select optimal configuration
            optimal_config = await self._select_optimal_privacy_config(
                evaluations, preference_weights, context
            )
            
            # Generate alternatives and recommendations
            alternatives = await self._generate_privacy_alternatives(
                evaluations, optimal_config, preference_weights
            )
            
            privacy_recommendations = await self._generate_privacy_recommendations(
                user_id, feature_request, optimal_config, privacy_analysis
            )
            
            # Store decision for learning
            await self._store_privacy_convenience_decision(
                user_id, feature_request, optimal_config, evaluations, preference_weights
            )
            
            return {
                "user_id": str(user_id),
                "feature_name": feature_request.get("name", "Unknown"),
                "recommended_configuration": optimal_config,
                "privacy_analysis": {
                    "privacy_impact_score": privacy_analysis["privacy_impact_score"],
                    "data_types_accessed": privacy_analysis["data_types"],
                    "third_party_sharing": privacy_analysis["third_party_sharing"],
                    "data_retention_period": privacy_analysis["retention_period"],
                    "anonymization_possible": privacy_analysis["can_anonymize"]
                },
                "convenience_analysis": {
                    "convenience_score": convenience_analysis["convenience_score"],
                    "time_savings": convenience_analysis["time_savings"],
                    "automation_level": convenience_analysis["automation_level"],
                    "user_effort_reduction": convenience_analysis["effort_reduction"]
                },
                "configuration_options": evaluations[:5],
                "alternatives": alternatives,
                "privacy_recommendations": privacy_recommendations,
                "trust_indicators": await self._generate_trust_indicators(
                    feature_request, optimal_config
                ),
                "confidence_score": optimal_config["confidence"],
                "decision_reasoning": optimal_config["reasoning"],
                "decision_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to evaluate privacy vs convenience tradeoff: {e}")
            raise
    
    async def evaluate_data_sharing_request(
        self,
        user_id: uuid.UUID,
        data_sharing_request: Dict[str, Any],
        requesting_service: str
    ) -> Dict[str, Any]:
        """Evaluate a specific data sharing request"""
        
        try:
            # Analyze the data sharing request
            sharing_analysis = await self._analyze_data_sharing_request(
                data_sharing_request, requesting_service
            )
            
            # Get user's data sharing history with this service
            service_history = await self._get_service_sharing_history(user_id, requesting_service)
            
            # Assess trust level for the requesting service
            trust_assessment = await self._assess_service_trust_level(
                requesting_service, user_id
            )
            
            # Generate sharing options
            sharing_options = await self._generate_data_sharing_options(
                data_sharing_request, sharing_analysis, trust_assessment
            )
            
            # Evaluate each sharing option
            evaluations = []
            for option in sharing_options:
                evaluation = await self._evaluate_sharing_option(
                    user_id, data_sharing_request, option, sharing_analysis, trust_assessment
                )
                evaluations.append(evaluation)
            
            # Get user preferences for data sharing
            sharing_preferences = await self._get_data_sharing_preferences(user_id)
            
            # Select recommended sharing option
            recommended_option = await self._select_recommended_sharing_option(
                evaluations, sharing_preferences, trust_assessment
            )
            
            # Generate privacy-preserving alternatives
            privacy_alternatives = await self._generate_privacy_preserving_alternatives(
                data_sharing_request, evaluations
            )
            
            # Store sharing decision
            await self._store_data_sharing_decision(
                user_id, data_sharing_request, requesting_service, 
                recommended_option, evaluations
            )
            
            return {
                "user_id": str(user_id),
                "requesting_service": requesting_service,
                "data_types_requested": sharing_analysis["data_types"],
                "recommended_sharing_option": recommended_option,
                "sharing_risk_assessment": {
                    "privacy_risk_score": sharing_analysis["privacy_risk_score"],
                    "data_sensitivity_level": sharing_analysis["sensitivity_level"],
                    "third_party_access": sharing_analysis["third_party_access"],
                    "data_retention": sharing_analysis["retention_policy"]
                },
                "trust_assessment": trust_assessment,
                "sharing_options": evaluations,
                "privacy_alternatives": privacy_alternatives,
                "user_control_options": await self._generate_user_control_options(
                    data_sharing_request
                ),
                "revocation_instructions": await self._generate_revocation_instructions(
                    requesting_service
                ),
                "decision_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to evaluate data sharing request: {e}")
            raise
    
    async def get_privacy_convenience_analytics(
        self,
        user_id: uuid.UUID,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """Get analytics on user's privacy vs convenience decisions"""
        
        try:
            start_date = datetime.utcnow() - timedelta(days=period_days)
            
            # Get privacy decisions
            result = await self.db.execute(
                select(PrivacyConvenienceDecision).where(
                    and_(
                        PrivacyConvenienceDecision.user_id == user_id,
                        PrivacyConvenienceDecision.decision_date >= start_date
                    )
                ).order_by(PrivacyConvenienceDecision.decision_date.desc())
            )
            privacy_decisions = result.scalars().all()
            
            # Get data sharing decisions
            result = await self.db.execute(
                select(DataSharingDecision).where(
                    and_(
                        DataSharingDecision.user_id == user_id,
                        DataSharingDecision.decision_date >= start_date
                    )
                ).order_by(DataSharingDecision.decision_date.desc())
            )
            sharing_decisions = result.scalars().all()
            
            if not privacy_decisions and not sharing_decisions:
                return {
                    "user_id": str(user_id),
                    "period_days": period_days,
                    "message": "No privacy vs convenience decisions found for this period"
                }
            
            # Analyze privacy decisions
            privacy_analysis = await self._analyze_privacy_decisions(privacy_decisions)
            sharing_analysis = await self._analyze_sharing_decisions(sharing_decisions)
            
            # Calculate privacy score trend
            privacy_trend = await self._calculate_privacy_trend(
                privacy_decisions, sharing_decisions
            )
            
            # Analyze feature usage patterns
            feature_patterns = await self._analyze_feature_usage_patterns(privacy_decisions)
            
            return {
                "user_id": str(user_id),
                "period_days": period_days,
                "privacy_decision_summary": {
                    "total_privacy_decisions": len(privacy_decisions),
                    "privacy_focused_decisions": privacy_analysis["privacy_focused_count"],
                    "convenience_focused_decisions": privacy_analysis["convenience_focused_count"],
                    "balanced_decisions": privacy_analysis["balanced_count"],
                    "dominant_preference": privacy_analysis["dominant_preference"]
                },
                "data_sharing_summary": {
                    "total_sharing_requests": len(sharing_decisions),
                    "data_shared_count": sharing_analysis["shared_count"],
                    "data_denied_count": sharing_analysis["denied_count"],
                    "conditional_sharing_count": sharing_analysis["conditional_count"],
                    "sharing_approval_rate": sharing_analysis["approval_rate"]
                },
                "privacy_metrics": {
                    "current_privacy_score": privacy_trend["current_score"],
                    "privacy_score_trend": privacy_trend["trend"],
                    "data_minimization_rate": privacy_analysis["minimization_rate"],
                    "anonymization_usage_rate": privacy_analysis["anonymization_rate"]
                },
                "convenience_metrics": {
                    "average_convenience_gain": privacy_analysis["avg_convenience_gain"],
                    "time_saved_minutes": privacy_analysis["total_time_saved"],
                    "automation_adoption_rate": privacy_analysis["automation_rate"]
                },
                "feature_usage_patterns": feature_patterns,
                "risk_assessment": {
                    "high_risk_decisions": privacy_analysis["high_risk_count"],
                    "data_exposure_incidents": 0,  # Would track actual incidents
                    "privacy_violations": 0
                },
                "recommendations": await self._generate_privacy_analytics_recommendations(
                    user_id, privacy_decisions, sharing_decisions
                ),
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get privacy convenience analytics: {e}")
            raise
    
    async def update_privacy_preferences(
        self,
        user_id: uuid.UUID,
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update user's privacy preferences"""
        
        try:
            # Validate preferences
            validated_preferences = await self._validate_privacy_preferences(preferences)
            
            # Get or create user privacy settings
            result = await self.db.execute(
                select(PrivacySetting).where(PrivacySetting.user_id == user_id)
            )
            privacy_setting = result.scalar_one_or_none()
            
            if privacy_setting:
                # Update existing settings
                privacy_setting.privacy_level = validated_preferences["privacy_level"]
                privacy_setting.data_sharing_preference = validated_preferences["data_sharing_preference"]
                privacy_setting.anonymization_preference = validated_preferences["anonymization_preference"]
                privacy_setting.third_party_sharing = validated_preferences["third_party_sharing"]
                privacy_setting.data_retention_preference = validated_preferences["data_retention_preference"]
                privacy_setting.updated_date = datetime.utcnow()
            else:
                # Create new settings
                privacy_setting = PrivacySetting(
                    user_id=user_id,
                    privacy_level=validated_preferences["privacy_level"],
                    data_sharing_preference=validated_preferences["data_sharing_preference"],
                    anonymization_preference=validated_preferences["anonymization_preference"],
                    third_party_sharing=validated_preferences["third_party_sharing"],
                    data_retention_preference=validated_preferences["data_retention_preference"],
                    created_date=datetime.utcnow(),
                    updated_date=datetime.utcnow()
                )
                self.db.add(privacy_setting)
            
            await self.db.commit()
            
            # Update personalization models
            await self._update_privacy_personalization_models(user_id, validated_preferences)
            
            return {
                "success": True,
                "user_id": str(user_id),
                "updated_preferences": validated_preferences,
                "effective_date": datetime.utcnow().isoformat(),
                "impact_analysis": await self._analyze_preference_impact(
                    user_id, validated_preferences
                )
            }
            
        except Exception as e:
            logger.error(f"Failed to update privacy preferences: {e}")
            raise
    
    # Helper methods
    
    async def _analyze_privacy_implications(self, feature_request: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the privacy implications of a feature request"""
        
        analysis = {
            "feature_name": feature_request.get("name", "Unknown"),
            "data_types": feature_request.get("data_access", []),
            "third_party_sharing": feature_request.get("third_party_sharing", False),
            "retention_period": feature_request.get("data_retention_days", 365),
            "can_anonymize": feature_request.get("supports_anonymization", True),
            "encryption_supported": feature_request.get("encryption", True),
            "user_control_level": feature_request.get("user_control", "full")
        }
        
        # Calculate privacy impact score (1-10, higher = more impact)
        impact_score = 1
        
        # Data type impact
        sensitive_data_types = ["location", "contacts", "messages", "financial", "health", "biometric"]
        for data_type in analysis["data_types"]:
            if data_type.lower() in sensitive_data_types:
                impact_score += 2
            else:
                impact_score += 1
        
        # Third-party sharing impact
        if analysis["third_party_sharing"]:
            impact_score += 3
        
        # Retention period impact
        if analysis["retention_period"] > 365:  # More than 1 year
            impact_score += 2
        elif analysis["retention_period"] > 90:  # More than 3 months
            impact_score += 1
        
        # User control impact (inverse - less control = higher impact)
        control_scores = {"full": 0, "partial": 1, "limited": 2, "none": 3}
        impact_score += control_scores.get(analysis["user_control_level"], 1)
        
        analysis["privacy_impact_score"] = min(10, impact_score)
        
        # Classify privacy risk level
        if analysis["privacy_impact_score"] <= 3:
            analysis["risk_level"] = "low"
        elif analysis["privacy_impact_score"] <= 6:
            analysis["risk_level"] = "medium"
        else:
            analysis["risk_level"] = "high"
        
        return analysis
    
    async def _analyze_convenience_benefits(self, feature_request: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the convenience benefits of a feature request"""
        
        analysis = {
            "feature_name": feature_request.get("name", "Unknown"),
            "time_savings": feature_request.get("estimated_time_saved_minutes", 0),
            "automation_level": feature_request.get("automation_level", "partial"),
            "effort_reduction": feature_request.get("effort_reduction_percent", 0),
            "frequency_of_use": feature_request.get("expected_daily_uses", 1),
            "user_experience_improvement": feature_request.get("ux_improvement_score", 5)
        }
        
        # Calculate convenience score (1-10)
        convenience_score = 1
        
        # Time savings impact
        if analysis["time_savings"] >= 60:  # 1 hour or more
            convenience_score += 4
        elif analysis["time_savings"] >= 30:  # 30 minutes
            convenience_score += 3
        elif analysis["time_savings"] >= 10:  # 10 minutes
            convenience_score += 2
        elif analysis["time_savings"] > 0:
            convenience_score += 1
        
        # Automation level impact
        automation_scores = {"full": 4, "high": 3, "partial": 2, "minimal": 1, "none": 0}
        convenience_score += automation_scores.get(analysis["automation_level"], 1)
        
        # Effort reduction impact
        if analysis["effort_reduction"] >= 75:
            convenience_score += 3
        elif analysis["effort_reduction"] >= 50:
            convenience_score += 2
        elif analysis["effort_reduction"] >= 25:
            convenience_score += 1
        
        # Frequency multiplier
        if analysis["frequency_of_use"] >= 10:  # Multiple times per day
            convenience_score += 2
        elif analysis["frequency_of_use"] >= 3:  # Few times per day
            convenience_score += 1
        
        analysis["convenience_score"] = min(10, convenience_score)
        
        return analysis
    
    async def _get_user_privacy_profile(self, user_id: uuid.UUID) -> Optional[PrivacySetting]:
        """Get user's privacy profile/settings"""
        
        result = await self.db.execute(
            select(PrivacySetting).where(PrivacySetting.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def _get_privacy_decision_history(self, user_id: uuid.UUID) -> List[PrivacyConvenienceDecision]:
        """Get user's privacy decision history"""
        
        lookback_date = datetime.utcnow() - timedelta(days=90)
        result = await self.db.execute(
            select(PrivacyConvenienceDecision).where(
                and_(
                    PrivacyConvenienceDecision.user_id == user_id,
                    PrivacyConvenienceDecision.decision_date >= lookback_date
                )
            ).order_by(PrivacyConvenienceDecision.decision_date.desc())
        )
        return result.scalars().all()
    
    async def _generate_privacy_convenience_configs(
        self,
        feature_request: Dict[str, Any],
        privacy_analysis: Dict[str, Any],
        convenience_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate different privacy vs convenience configuration options"""
        
        configs = []
        
        # Privacy-first configuration
        configs.append({
            "name": "Privacy-First",
            "privacy_priority": 0.8,
            "convenience_priority": 0.2,
            "data_minimization": True,
            "anonymization": True,
            "third_party_sharing": False,
            "data_retention_days": 30,
            "user_control": "full",
            "encryption": True,
            "audit_logging": True
        })
        
        # Convenience-first configuration
        configs.append({
            "name": "Convenience-First",
            "privacy_priority": 0.2,
            "convenience_priority": 0.8,
            "data_minimization": False,
            "anonymization": False,
            "third_party_sharing": feature_request.get("third_party_sharing", False),
            "data_retention_days": feature_request.get("data_retention_days", 365),
            "user_control": "partial",
            "encryption": True,
            "audit_logging": False
        })
        
        # Balanced configuration
        configs.append({
            "name": "Balanced",
            "privacy_priority": 0.5,
            "convenience_priority": 0.5,
            "data_minimization": True,
            "anonymization": privacy_analysis["can_anonymize"],
            "third_party_sharing": False,
            "data_retention_days": min(180, feature_request.get("data_retention_days", 365)),
            "user_control": "full",
            "encryption": True,
            "audit_logging": True
        })
        
        # Custom configuration based on feature requirements
        if privacy_analysis["risk_level"] == "high":
            configs.append({
                "name": "High-Security",
                "privacy_priority": 0.9,
                "convenience_priority": 0.1,
                "data_minimization": True,
                "anonymization": True,
                "third_party_sharing": False,
                "data_retention_days": 7,  # Very short retention
                "user_control": "full",
                "encryption": True,
                "audit_logging": True
            })
        
        if convenience_analysis["convenience_score"] >= 8:
            configs.append({
                "name": "High-Convenience",
                "privacy_priority": 0.3,
                "convenience_priority": 0.7,
                "data_minimization": False,
                "anonymization": False,
                "third_party_sharing": True,
                "data_retention_days": 730,  # 2 years
                "user_control": "partial",
                "encryption": True,
                "audit_logging": False
            })
        
        return configs
    
    async def _evaluate_privacy_config(
        self,
        user_id: uuid.UUID,
        feature_request: Dict[str, Any],
        config: Dict[str, Any],
        privacy_analysis: Dict[str, Any],
        convenience_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate a privacy configuration"""
        
        evaluation = {
            "configuration": config,
            "privacy_score": 0,
            "convenience_score": 0,
            "security_score": 0,
            "usability_score": 0,
            "overall_score": 0,
            "feasibility": 1.0,
            "reasoning": [],
            "benefits": [],
            "drawbacks": []
        }
        
        # Calculate privacy score
        privacy_score = 5.0  # Base score
        
        if config["data_minimization"]:
            privacy_score += 1.5
            evaluation["benefits"].append("Minimizes data collection")
        
        if config["anonymization"]:
            privacy_score += 1.0
            evaluation["benefits"].append("Uses anonymized data")
        
        if not config["third_party_sharing"]:
            privacy_score += 2.0
            evaluation["benefits"].append("No third-party data sharing")
        else:
            privacy_score -= 1.0
            evaluation["drawbacks"].append("Allows third-party data sharing")
        
        if config["data_retention_days"] <= 30:
            privacy_score += 1.5
        elif config["data_retention_days"] <= 90:
            privacy_score += 1.0
        elif config["data_retention_days"] > 365:
            privacy_score -= 1.0
        
        evaluation["privacy_score"] = min(10, max(0, privacy_score))
        
        # Calculate convenience score
        convenience_score = convenience_analysis["convenience_score"]
        
        # Adjust for configuration restrictions
        if config["data_minimization"]:
            convenience_score *= 0.9  # Slight reduction
        
        if config["anonymization"] and not privacy_analysis["can_anonymize"]:
            convenience_score *= 0.7  # Significant reduction
            evaluation["drawbacks"].append("Anonymization may reduce functionality")
        
        if not config["third_party_sharing"] and feature_request.get("requires_third_party", False):
            convenience_score *= 0.5  # Major reduction
            evaluation["drawbacks"].append("Blocking third-party sharing reduces features")
        
        evaluation["convenience_score"] = convenience_score
        
        # Calculate security score
        security_score = 5.0
        
        if config["encryption"]:
            security_score += 2.0
        
        if config["audit_logging"]:
            security_score += 1.0
        
        if config["user_control"] == "full":
            security_score += 2.0
        elif config["user_control"] == "partial":
            security_score += 1.0
        
        evaluation["security_score"] = min(10, security_score)
        
        # Calculate usability score
        usability_score = 7.0  # Base usability
        
        if config["user_control"] == "full":
            usability_score += 1.0
        elif config["user_control"] == "none":
            usability_score -= 2.0
        
        if config["privacy_priority"] > 0.7:
            usability_score -= 1.0  # Privacy measures may reduce usability
        
        evaluation["usability_score"] = min(10, max(0, usability_score))
        
        # Calculate overall score
        evaluation["overall_score"] = (
            evaluation["privacy_score"] * config["privacy_priority"] +
            evaluation["convenience_score"] * config["convenience_priority"]
        )
        
        # Add reasoning
        evaluation["reasoning"] = [
            f"Privacy priority: {config['privacy_priority']:.1f}",
            f"Convenience priority: {config['convenience_priority']:.1f}",
            f"Privacy score: {evaluation['privacy_score']:.1f}/10",
            f"Convenience score: {evaluation['convenience_score']:.1f}/10"
        ]
        
        return evaluation
    
    async def _calculate_privacy_preference_weights(
        self,
        user_id: uuid.UUID,
        user_privacy_profile: Optional[PrivacySetting],
        privacy_history: List[PrivacyConvenienceDecision],
        user_preferences: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate user preference weights for privacy vs convenience"""
        
        weights = {
            "privacy_weight": 0.5,
            "convenience_weight": 0.4,
            "security_weight": 0.1
        }
        
        # Adjust based on user privacy settings
        if user_privacy_profile:
            privacy_level = user_privacy_profile.privacy_level
            if privacy_level == "high":
                weights["privacy_weight"] = 0.7
                weights["convenience_weight"] = 0.2
                weights["security_weight"] = 0.1
            elif privacy_level == "low":
                weights["privacy_weight"] = 0.2
                weights["convenience_weight"] = 0.7
                weights["security_weight"] = 0.1
        
        # Adjust based on explicit preferences
        if user_preferences:
            if "privacy_importance" in user_preferences:
                weights["privacy_weight"] = float(user_preferences["privacy_importance"])
            if "convenience_importance" in user_preferences:
                weights["convenience_weight"] = float(user_preferences["convenience_importance"])
            if "security_importance" in user_preferences:
                weights["security_weight"] = float(user_preferences["security_importance"])
        
        # Adjust based on historical decisions
        if privacy_history:
            privacy_focused = len([d for d in privacy_history if d.chosen_approach == "privacy_first"])
            convenience_focused = len([d for d in privacy_history if d.chosen_approach == "convenience_first"])
            total_decisions = len(privacy_history)
            
            if privacy_focused > convenience_focused:
                weights["privacy_weight"] += 0.1
                weights["convenience_weight"] -= 0.05
            elif convenience_focused > privacy_focused:
                weights["convenience_weight"] += 0.1
                weights["privacy_weight"] -= 0.05
        
        # Context adjustments
        if context:
            if context.get("sensitive_context", False):
                weights["privacy_weight"] += 0.1
                weights["security_weight"] += 0.05
                weights["convenience_weight"] -= 0.15
            
            if context.get("public_setting", False):
                weights["privacy_weight"] += 0.05
                weights["security_weight"] += 0.05
                weights["convenience_weight"] -= 0.1
        
        # Normalize weights
        total_weight = sum(weights.values())
        for key in weights:
            weights[key] /= total_weight
        
        return weights
    
    async def _select_optimal_privacy_config(
        self,
        evaluations: List[Dict[str, Any]],
        preference_weights: Dict[str, float],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Select optimal privacy configuration"""
        
        if not evaluations:
            return {"error": "No configurations available"}
        
        scored_evaluations = []
        
        for evaluation in evaluations:
            # Calculate weighted score
            weighted_score = (
                evaluation["privacy_score"] * preference_weights["privacy_weight"] +
                evaluation["convenience_score"] * preference_weights["convenience_weight"] +
                evaluation["security_score"] * preference_weights["security_weight"]
            )
            
            # Apply feasibility multiplier
            weighted_score *= evaluation["feasibility"]
            
            # Context adjustments
            if context and context.get("high_risk_scenario", False):
                if evaluation["configuration"]["privacy_priority"] > 0.6:
                    weighted_score *= 1.2  # Boost privacy-focused configs in high-risk scenarios
            
            scored_evaluation = {
                **evaluation,
                "weighted_score": weighted_score,
                "confidence": min(1.0, weighted_score / 10.0 + 0.3)
            }
            
            scored_evaluations.append(scored_evaluation)
        
        # Sort by weighted score
        scored_evaluations.sort(key=lambda x: x["weighted_score"], reverse=True)
        
        optimal = scored_evaluations[0]
        optimal["reasoning"].extend([
            f"Selected based on weighted score: {optimal['weighted_score']:.2f}",
            f"Privacy weight: {preference_weights['privacy_weight']:.2f}",
            f"Convenience weight: {preference_weights['convenience_weight']:.2f}"
        ])
        
        return optimal
    
    async def _generate_privacy_alternatives(
        self,
        evaluations: List[Dict[str, Any]],
        optimal_config: Dict[str, Any],
        preference_weights: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Generate alternative privacy configurations"""
        
        alternatives = []
        
        # Sort evaluations by weighted score
        sorted_evals = sorted(evaluations, key=lambda x: x.get("weighted_score", 0), reverse=True)
        
        # Skip optimal and take next best options
        for eval_config in sorted_evals[1:3]:
            alternative = {
                "name": eval_config["configuration"]["name"],
                "privacy_score": eval_config["privacy_score"],
                "convenience_score": eval_config["convenience_score"],
                "security_score": eval_config["security_score"],
                "trade_offs": await self._compare_privacy_configs(eval_config, optimal_config),
                "when_to_choose": await self._suggest_when_to_choose_privacy_config(eval_config),
                "key_differences": await self._identify_key_config_differences(
                    eval_config["configuration"], optimal_config["configuration"]
                )
            }
            alternatives.append(alternative)
        
        return alternatives
    
    async def _generate_privacy_recommendations(
        self,
        user_id: uuid.UUID,
        feature_request: Dict[str, Any],
        optimal_config: Dict[str, Any],
        privacy_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate privacy recommendations"""
        
        recommendations = []
        
        # Risk-based recommendations
        if privacy_analysis["risk_level"] == "high":
            recommendations.append("This feature accesses sensitive data - consider enabling anonymization")
            recommendations.append("Review data retention settings to minimize long-term privacy risk")
        
        # Configuration-specific recommendations
        if optimal_config["configuration"]["third_party_sharing"]:
            recommendations.append("Third-party sharing is enabled - review which partners receive data")
            recommendations.append("Consider periodic review of data sharing permissions")
        
        if optimal_config["configuration"]["data_retention_days"] > 180:
            recommendations.append("Data is retained for extended periods - consider shorter retention")
        
        if optimal_config["privacy_score"] < 6:
            recommendations.append("Current configuration has moderate privacy protection")
            recommendations.append("Consider enabling additional privacy features if possible")
        
        # User control recommendations
        if optimal_config["configuration"]["user_control"] != "full":
            recommendations.append("Limited user control - consider configurations with more control options")
        
        return recommendations
    
    async def _generate_trust_indicators(
        self,
        feature_request: Dict[str, Any],
        optimal_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate trust indicators for the feature and configuration"""
        
        trust_indicators = {
            "encryption_status": "enabled" if optimal_config["configuration"]["encryption"] else "disabled",
            "audit_logging": "enabled" if optimal_config["configuration"]["audit_logging"] else "disabled",
            "data_minimization": "enabled" if optimal_config["configuration"]["data_minimization"] else "disabled",
            "user_control_level": optimal_config["configuration"]["user_control"],
            "third_party_sharing": optimal_config["configuration"]["third_party_sharing"],
            "data_retention_period": f"{optimal_config['configuration']['data_retention_days']} days"
        }
        
        # Calculate overall trust score
        trust_score = 0
        if trust_indicators["encryption_status"] == "enabled":
            trust_score += 20
        if trust_indicators["audit_logging"] == "enabled":
            trust_score += 15
        if trust_indicators["data_minimization"] == "enabled":
            trust_score += 20
        if trust_indicators["user_control_level"] == "full":
            trust_score += 25
        elif trust_indicators["user_control_level"] == "partial":
            trust_score += 15
        if not trust_indicators["third_party_sharing"]:
            trust_score += 20
        
        trust_indicators["overall_trust_score"] = min(100, trust_score)
        
        return trust_indicators
    
    async def _store_privacy_convenience_decision(
        self,
        user_id: uuid.UUID,
        feature_request: Dict[str, Any],
        optimal_config: Dict[str, Any],
        all_evaluations: List[Dict[str, Any]],
        preference_weights: Dict[str, float]
    ):
        """Store the privacy vs convenience decision"""
        
        decision = PrivacyConvenienceDecision(
            user_id=user_id,
            feature_name=feature_request.get("name", "Unknown"),
            feature_metadata=feature_request,
            chosen_approach=optimal_config["configuration"]["name"].lower().replace(" ", "_").replace("-", "_"),
            selected_configuration=optimal_config,
            alternative_configurations=all_evaluations[:3],
            privacy_score=Decimal(str(optimal_config["privacy_score"])),
            convenience_score=Decimal(str(optimal_config["convenience_score"])),
            preference_weights=preference_weights,
            decision_date=datetime.utcnow()
        )
        
        self.db.add(decision)
        await self.db.commit()
    
    # Additional helper methods for data sharing evaluation...
    
    async def _analyze_data_sharing_request(
        self,
        data_sharing_request: Dict[str, Any],
        requesting_service: str
    ) -> Dict[str, Any]:
        """Analyze a data sharing request"""
        
        analysis = {
            "requesting_service": requesting_service,
            "data_types": data_sharing_request.get("data_types", []),
            "purpose": data_sharing_request.get("purpose", "unspecified"),
            "retention_policy": data_sharing_request.get("retention_days", 365),
            "third_party_access": data_sharing_request.get("third_party_access", False),
            "anonymization_offered": data_sharing_request.get("anonymization", False),
            "user_benefits": data_sharing_request.get("user_benefits", [])
        }
        
        # Calculate privacy risk score
        risk_score = 1
        
        # Risk from data types
        high_risk_data = ["financial", "health", "biometric", "location", "contacts", "messages"]
        for data_type in analysis["data_types"]:
            if data_type.lower() in high_risk_data:
                risk_score += 3
            else:
                risk_score += 1
        
        # Risk from third-party access
        if analysis["third_party_access"]:
            risk_score += 4
        
        # Risk from retention policy
        if analysis["retention_policy"] > 730:  # More than 2 years
            risk_score += 2
        elif analysis["retention_policy"] > 365:  # More than 1 year
            risk_score += 1
        
        # Risk mitigation from anonymization
        if analysis["anonymization_offered"]:
            risk_score -= 2
        
        analysis["privacy_risk_score"] = max(1, min(10, risk_score))
        
        # Classify sensitivity level
        if analysis["privacy_risk_score"] <= 3:
            analysis["sensitivity_level"] = "low"
        elif analysis["privacy_risk_score"] <= 6:
            analysis["sensitivity_level"] = "medium"
        else:
            analysis["sensitivity_level"] = "high"
        
        return analysis
    
    async def _get_service_sharing_history(
        self,
        user_id: uuid.UUID,
        requesting_service: str
    ) -> List[DataSharingDecision]:
        """Get user's data sharing history with a specific service"""
        
        result = await self.db.execute(
            select(DataSharingDecision).where(
                and_(
                    DataSharingDecision.user_id == user_id,
                    DataSharingDecision.requesting_service == requesting_service
                )
            ).order_by(DataSharingDecision.decision_date.desc()).limit(10)
        )
        return result.scalars().all()
    
    async def _assess_service_trust_level(
        self,
        requesting_service: str,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Assess trust level for a requesting service"""
        
        # This would integrate with service reputation databases
        # For now, provide a basic assessment structure
        
        trust_assessment = {
            "service_name": requesting_service,
            "reputation_score": 7,  # Default moderate trust
            "privacy_rating": "B",  # A-F scale
            "data_breach_history": False,
            "compliance_certifications": ["GDPR", "CCPA"],
            "transparency_score": 6,
            "user_control_options": "partial"
        }
        
        # Calculate overall trust score
        trust_score = trust_assessment["reputation_score"]
        
        if trust_assessment["privacy_rating"] in ["A", "A+"]:
            trust_score += 2
        elif trust_assessment["privacy_rating"] in ["D", "F"]:
            trust_score -= 3
        
        if trust_assessment["data_breach_history"]:
            trust_score -= 2
        
        trust_score += len(trust_assessment["compliance_certifications"])
        
        trust_assessment["overall_trust_score"] = max(1, min(10, trust_score))
        
        return trust_assessment
    
    async def _generate_data_sharing_options(
        self,
        data_sharing_request: Dict[str, Any],
        sharing_analysis: Dict[str, Any],
        trust_assessment: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate data sharing options"""
        
        options = []
        
        # Full sharing option
        options.append({
            "name": "Full Sharing",
            "data_types": sharing_analysis["data_types"],
            "anonymization": False,
            "time_limited": False,
            "purpose_limited": False,
            "user_control": "basic"
        })
        
        # Limited sharing option
        options.append({
            "name": "Limited Sharing",
            "data_types": sharing_analysis["data_types"][:3],  # Limit data types
            "anonymization": True,
            "time_limited": True,
            "purpose_limited": True,
            "user_control": "enhanced"
        })
        
        # Conditional sharing option
        options.append({
            "name": "Conditional Sharing",
            "data_types": sharing_analysis["data_types"],
            "anonymization": True,
            "time_limited": True,
            "purpose_limited": True,
            "user_control": "full",
            "conditions": ["user_approval_required", "audit_reports", "revocation_rights"]
        })
        
        # No sharing option
        options.append({
            "name": "No Sharing",
            "data_types": [],
            "anonymization": False,
            "time_limited": False,
            "purpose_limited": False,
            "user_control": "full"
        })
        
        return options
    
    # Additional methods would continue here for complete implementation...
    # Including methods for:
    # - _evaluate_sharing_option
    # - _get_data_sharing_preferences  
    # - _select_recommended_sharing_option
    # - _generate_privacy_preserving_alternatives
    # - _store_data_sharing_decision
    # - _generate_user_control_options
    # - _generate_revocation_instructions
    # - Privacy analytics methods
    # - Preference validation and updates
    # - Model updates and learning
    
    async def _compare_privacy_configs(
        self,
        alternative: Dict[str, Any],
        optimal: Dict[str, Any]
    ) -> List[str]:
        """Compare alternative privacy config with optimal"""
        
        comparisons = []
        
        privacy_diff = alternative["privacy_score"] - optimal["privacy_score"]
        convenience_diff = alternative["convenience_score"] - optimal["convenience_score"]
        
        if privacy_diff > 0:
            comparisons.append(f"{privacy_diff:.1f} points higher privacy protection")
        elif privacy_diff < 0:
            comparisons.append(f"{abs(privacy_diff):.1f} points lower privacy protection")
        
        if convenience_diff > 0:
            comparisons.append(f"{convenience_diff:.1f} points more convenient")
        elif convenience_diff < 0:
            comparisons.append(f"{abs(convenience_diff):.1f} points less convenient")
        
        return comparisons
    
    async def _suggest_when_to_choose_privacy_config(self, config: Dict[str, Any]) -> str:
        """Suggest when to choose this privacy configuration"""
        
        config_name = config["configuration"]["name"].lower()
        
        if "privacy" in config_name:
            return "Choose when handling sensitive data or in high-risk scenarios"
        elif "convenience" in config_name:
            return "Choose when user experience is priority and trust is high"
        elif "balanced" in config_name:
            return "Choose for everyday use with good privacy-convenience balance"
        else:
            return "Choose based on specific privacy and convenience requirements"
    
    async def _identify_key_config_differences(
        self,
        config1: Dict[str, Any],
        config2: Dict[str, Any]
    ) -> List[str]:
        """Identify key differences between configurations"""
        
        differences = []
        
        if config1["data_minimization"] != config2["data_minimization"]:
            differences.append(f"Data minimization: {'enabled' if config1['data_minimization'] else 'disabled'}")
        
        if config1["anonymization"] != config2["anonymization"]:
            differences.append(f"Anonymization: {'enabled' if config1['anonymization'] else 'disabled'}")
        
        if config1["third_party_sharing"] != config2["third_party_sharing"]:
            differences.append(f"Third-party sharing: {'allowed' if config1['third_party_sharing'] else 'blocked'}")
        
        if config1["data_retention_days"] != config2["data_retention_days"]:
            differences.append(f"Data retention: {config1['data_retention_days']} days vs {config2['data_retention_days']} days")
        
        return differences
    
    async def _analyze_privacy_decisions(
        self,
        decisions: List[PrivacyConvenienceDecision]
    ) -> Dict[str, Any]:
        """Analyze privacy decisions"""
        
        if not decisions:
            return {
                "privacy_focused_count": 0,
                "convenience_focused_count": 0,
                "balanced_count": 0,
                "dominant_preference": "unknown",
                "minimization_rate": 0,
                "anonymization_rate": 0,
                "avg_convenience_gain": 0,
                "total_time_saved": 0,
                "automation_rate": 0,
                "high_risk_count": 0
            }
        
        privacy_focused = len([d for d in decisions if "privacy" in d.chosen_approach.lower()])
        convenience_focused = len([d for d in decisions if "convenience" in d.chosen_approach.lower()])
        balanced = len([d for d in decisions if "balanced" in d.chosen_approach.lower()])
        
        # Determine dominant preference
        if privacy_focused > convenience_focused and privacy_focused > balanced:
            dominant_preference = "privacy_focused"
        elif convenience_focused > privacy_focused and convenience_focused > balanced:
            dominant_preference = "convenience_focused"
        elif balanced > privacy_focused and balanced > convenience_focused:
            dominant_preference = "balanced_approach"
        else:
            dominant_preference = "mixed"
        
        # Calculate metrics from configurations
        minimization_enabled = len([
            d for d in decisions 
            if d.selected_configuration and d.selected_configuration.get("configuration", {}).get("data_minimization", False)
        ])
        
        anonymization_enabled = len([
            d for d in decisions 
            if d.selected_configuration and d.selected_configuration.get("configuration", {}).get("anonymization", False)
        ])
        
        return {
            "privacy_focused_count": privacy_focused,
            "convenience_focused_count": convenience_focused,
            "balanced_count": balanced,
            "dominant_preference": dominant_preference,
            "minimization_rate": (minimization_enabled / len(decisions)) * 100,
            "anonymization_rate": (anonymization_enabled / len(decisions)) * 100,
            "avg_convenience_gain": sum(float(d.convenience_score) for d in decisions) / len(decisions),
            "total_time_saved": 0,  # Would calculate from feature metadata
            "automation_rate": 0,  # Would calculate from feature types
            "high_risk_count": len([d for d in decisions if float(d.privacy_score) < 5])
        }
    
    async def _analyze_sharing_decisions(
        self,
        decisions: List[DataSharingDecision]
    ) -> Dict[str, Any]:
        """Analyze data sharing decisions"""
        
        if not decisions:
            return {
                "shared_count": 0,
                "denied_count": 0,
                "conditional_count": 0,
                "approval_rate": 0
            }
        
        shared = len([d for d in decisions if d.sharing_decision == "approved"])
        denied = len([d for d in decisions if d.sharing_decision == "denied"])
        conditional = len([d for d in decisions if d.sharing_decision == "conditional"])
        
        approval_rate = ((shared + conditional) / len(decisions)) * 100
        
        return {
            "shared_count": shared,
            "denied_count": denied,
            "conditional_count": conditional,
            "approval_rate": approval_rate
        }
    
    async def _calculate_privacy_trend(
        self,
        privacy_decisions: List[PrivacyConvenienceDecision],
        sharing_decisions: List[DataSharingDecision]
    ) -> Dict[str, Any]:
        """Calculate privacy score trend"""
        
        all_decisions = len(privacy_decisions) + len(sharing_decisions)
        if all_decisions == 0:
            return {"current_score": 5, "trend": "stable"}
        
        # Simple privacy score calculation
        privacy_score = 5  # Base score
        
        # Factor in privacy decisions
        privacy_focused_decisions = len([
            d for d in privacy_decisions 
            if "privacy" in d.chosen_approach.lower()
        ])
        
        privacy_score += (privacy_focused_decisions / max(1, len(privacy_decisions))) * 3
        
        # Factor in sharing decisions
        denied_sharing = len([d for d in sharing_decisions if d.sharing_decision == "denied"])
        privacy_score += (denied_sharing / max(1, len(sharing_decisions))) * 2
        
        current_score = min(10, privacy_score)
        
        return {
            "current_score": current_score,
            "trend": "increasing" if current_score > 6 else "stable"
        }
    
    async def _analyze_feature_usage_patterns(
        self,
        decisions: List[PrivacyConvenienceDecision]
    ) -> Dict[str, Any]:
        """Analyze feature usage patterns"""
        
        if not decisions:
            return {"insufficient_data": True}
        
        # Group by feature categories
        feature_categories = {}
        for decision in decisions:
            feature_name = decision.feature_name
            category = "other"  # Would classify based on feature metadata
            
            if category not in feature_categories:
                feature_categories[category] = {
                    "count": 0,
                    "privacy_focused": 0,
                    "convenience_focused": 0
                }
            
            feature_categories[category]["count"] += 1
            if "privacy" in decision.chosen_approach.lower():
                feature_categories[category]["privacy_focused"] += 1
            elif "convenience" in decision.chosen_approach.lower():
                feature_categories[category]["convenience_focused"] += 1
        
        return {
            "feature_categories": feature_categories,
            "most_used_category": max(feature_categories.keys(), key=lambda k: feature_categories[k]["count"]) if feature_categories else "none"
        }
    
    async def _generate_privacy_analytics_recommendations(
        self,
        user_id: uuid.UUID,
        privacy_decisions: List[PrivacyConvenienceDecision],
        sharing_decisions: List[DataSharingDecision]
    ) -> List[str]:
        """Generate privacy analytics recommendations"""
        
        recommendations = []
        
        # Analyze privacy vs convenience balance
        privacy_focused = len([d for d in privacy_decisions if "privacy" in d.chosen_approach.lower()])
        convenience_focused = len([d for d in privacy_decisions if "convenience" in d.chosen_approach.lower()])
        
        if convenience_focused > privacy_focused * 2:
            recommendations.append("Consider reviewing privacy settings - many convenience-focused choices detected")
            recommendations.append("Enable data minimization where possible to reduce privacy exposure")
        
        if privacy_focused > convenience_focused * 2:
            recommendations.append("Consider enabling some convenience features with privacy protections")
            recommendations.append("Look for features that offer good privacy-convenience balance")
        
        # Analyze data sharing patterns
        if sharing_decisions:
            approval_rate = len([d for d in sharing_decisions if d.sharing_decision == "approved"]) / len(sharing_decisions)
            if approval_rate > 0.8:
                recommendations.append("High data sharing approval rate - review sharing decisions periodically")
        
        if not recommendations:
            recommendations.append("Privacy decision patterns look well-balanced")
        
        return recommendations
    
    async def _validate_privacy_preferences(self, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Validate privacy preferences"""
        
        validated = {
            "privacy_level": preferences.get("privacy_level", "medium"),
            "data_sharing_preference": preferences.get("data_sharing_preference", "selective"),
            "anonymization_preference": preferences.get("anonymization_preference", True),
            "third_party_sharing": preferences.get("third_party_sharing", False),
            "data_retention_preference": preferences.get("data_retention_preference", 90)
        }
        
        # Validate enum values
        if validated["privacy_level"] not in ["low", "medium", "high"]:
            validated["privacy_level"] = "medium"
        
        if validated["data_sharing_preference"] not in ["never", "selective", "permissive"]:
            validated["data_sharing_preference"] = "selective"
        
        # Validate numeric values
        if not isinstance(validated["data_retention_preference"], int) or validated["data_retention_preference"] < 1:
            validated["data_retention_preference"] = 90
        
        return validated
    
    async def _update_privacy_personalization_models(
        self,
        user_id: uuid.UUID,
        preferences: Dict[str, Any]
    ):
        """Update privacy personalization models"""
        
        # In production, this would update ML models for personalized recommendations
        logger.info(f"Updated privacy personalization for user {user_id}: {preferences}")
        pass
    
    async def _analyze_preference_impact(
        self,
        user_id: uuid.UUID,
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze the impact of preference changes"""
        
        return {
            "affected_features": [],  # Would analyze which features are impacted
            "privacy_improvement": "moderate" if preferences["privacy_level"] == "high" else "minimal",
            "convenience_impact": "minimal" if preferences["privacy_level"] == "low" else "moderate",
            "estimated_adjustment_period": "1-2 weeks"
        }