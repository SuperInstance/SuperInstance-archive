from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import Dict, List, Optional, Any, Tuple
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import json
import math

from ..database import (
    User, UserChoice, ChoiceType, FeaturePriceComparison,
    ServiceOption, PricingTier, FeatureComparison, ValueAssessment
)

logger = logging.getLogger(__name__)

class FeatureVsPriceComparison:
    """Intelligent comparison system for features vs price trade-offs"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def compare_service_options(
        self,
        user_id: uuid.UUID,
        service_category: str,
        comparison_request: Dict[str, Any],
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Compare multiple service options across features and pricing"""
        
        try:
            # Get service options for comparison
            service_options = await self._get_service_options(
                service_category, comparison_request
            )
            
            if not service_options:
                return {"success": False, "error": "No service options found for comparison"}
            
            # Analyze feature requirements
            feature_requirements = await self._analyze_feature_requirements(
                comparison_request, user_preferences
            )
            
            # Get user's historical preferences and budget
            user_profile = await self._get_user_comparison_profile(user_id)
            budget_constraints = comparison_request.get("budget", {})
            
            # Perform detailed comparison for each service
            service_evaluations = []
            for service in service_options:
                evaluation = await self._evaluate_service_option(
                    user_id, service, feature_requirements, budget_constraints
                )
                service_evaluations.append(evaluation)
            
            # Calculate preference weights
            preference_weights = await self._calculate_comparison_weights(
                user_id, user_profile, user_preferences, feature_requirements
            )
            
            # Rank services based on weighted scoring
            ranked_services = await self._rank_service_options(
                service_evaluations, preference_weights, budget_constraints
            )
            
            # Generate detailed comparison matrix
            comparison_matrix = await self._generate_comparison_matrix(
                ranked_services, feature_requirements
            )
            
            # Identify best value options
            value_recommendations = await self._identify_value_recommendations(
                ranked_services, feature_requirements, budget_constraints
            )
            
            # Generate price-performance analysis
            price_performance_analysis = await self._analyze_price_performance_ratio(
                ranked_services
            )
            
            # Store comparison for learning
            await self._store_feature_price_comparison(
                user_id, service_category, comparison_request, ranked_services, preference_weights
            )
            
            return {
                "user_id": str(user_id),
                "service_category": service_category,
                "comparison_summary": {
                    "total_options_compared": len(ranked_services),
                    "recommended_option": ranked_services[0]["service"]["name"] if ranked_services else None,
                    "budget_range": f"${budget_constraints.get('min_budget', 0)}-${budget_constraints.get('max_budget', 'unlimited')}",
                    "primary_decision_factors": await self._identify_primary_factors(preference_weights)
                },
                "ranked_services": ranked_services[:10],  # Top 10 options
                "comparison_matrix": comparison_matrix,
                "value_recommendations": value_recommendations,
                "price_performance_analysis": price_performance_analysis,
                "feature_analysis": {
                    "must_have_features": feature_requirements["must_have"],
                    "nice_to_have_features": feature_requirements["nice_to_have"],
                    "feature_importance_scores": feature_requirements["importance_scores"]
                },
                "decision_guidance": await self._generate_decision_guidance(
                    ranked_services, feature_requirements, budget_constraints
                ),
                "comparison_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to compare service options: {e}")
            raise
    
    async def evaluate_upgrade_decision(
        self,
        user_id: uuid.UUID,
        current_service: Dict[str, Any],
        upgrade_options: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Evaluate whether to upgrade current service and which option to choose"""
        
        try:
            # Analyze current service satisfaction and limitations
            current_analysis = await self._analyze_current_service(
                user_id, current_service, context
            )
            
            # Evaluate each upgrade option
            upgrade_evaluations = []
            for upgrade in upgrade_options:
                evaluation = await self._evaluate_upgrade_option(
                    user_id, current_service, upgrade, current_analysis
                )
                upgrade_evaluations.append(evaluation)
            
            # Get user's upgrade preferences
            upgrade_preferences = await self._get_upgrade_preferences(user_id)
            
            # Calculate upgrade decision factors
            decision_factors = await self._calculate_upgrade_decision_factors(
                current_analysis, upgrade_evaluations, upgrade_preferences
            )
            
            # Make upgrade recommendation
            upgrade_recommendation = await self._make_upgrade_recommendation(
                upgrade_evaluations, decision_factors, current_analysis
            )
            
            # Analyze cost-benefit of upgrades
            cost_benefit_analysis = await self._analyze_upgrade_cost_benefit(
                current_service, upgrade_evaluations, upgrade_recommendation
            )
            
            # Generate timing recommendation
            timing_recommendation = await self._recommend_upgrade_timing(
                upgrade_recommendation, current_analysis, context
            )
            
            return {
                "user_id": str(user_id),
                "current_service_analysis": {
                    "service_name": current_service.get("name", "Unknown"),
                    "satisfaction_score": current_analysis["satisfaction_score"],
                    "limitations": current_analysis["limitations"],
                    "utilization_rate": current_analysis["utilization_rate"],
                    "value_for_money": current_analysis["value_score"]
                },
                "upgrade_recommendation": upgrade_recommendation,
                "upgrade_options": upgrade_evaluations,
                "cost_benefit_analysis": cost_benefit_analysis,
                "decision_factors": decision_factors,
                "timing_recommendation": timing_recommendation,
                "risk_assessment": await self._assess_upgrade_risks(
                    current_service, upgrade_recommendation
                ),
                "alternatives": await self._suggest_upgrade_alternatives(
                    upgrade_evaluations, upgrade_recommendation
                ),
                "decision_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to evaluate upgrade decision: {e}")
            raise
    
    async def get_feature_price_analytics(
        self,
        user_id: uuid.UUID,
        period_days: int = 90
    ) -> Dict[str, Any]:
        """Get analytics on user's feature vs price decision patterns"""
        
        try:
            start_date = datetime.utcnow() - timedelta(days=period_days)
            
            # Get comparison history
            result = await self.db.execute(
                select(FeaturePriceComparison).where(
                    and_(
                        FeaturePriceComparison.user_id == user_id,
                        FeaturePriceComparison.comparison_date >= start_date
                    )
                ).order_by(FeaturePriceComparison.comparison_date.desc())
            )
            comparisons = result.scalars().all()
            
            # Get value assessments
            result = await self.db.execute(
                select(ValueAssessment).where(
                    and_(
                        ValueAssessment.user_id == user_id,
                        ValueAssessment.assessment_date >= start_date
                    )
                ).order_by(ValueAssessment.assessment_date.desc())
            )
            value_assessments = result.scalars().all()
            
            if not comparisons and not value_assessments:
                return {
                    "user_id": str(user_id),
                    "period_days": period_days,
                    "message": "No feature vs price decisions found for this period"
                }
            
            # Analyze decision patterns
            decision_patterns = await self._analyze_decision_patterns(comparisons)
            
            # Analyze spending patterns
            spending_patterns = await self._analyze_spending_patterns(comparisons, value_assessments)
            
            # Analyze feature preferences
            feature_preferences = await self._analyze_feature_preferences(comparisons)
            
            # Calculate value optimization metrics
            value_metrics = await self._calculate_value_metrics(comparisons, value_assessments)
            
            # Analyze upgrade patterns
            upgrade_patterns = await self._analyze_upgrade_patterns(comparisons)
            
            return {
                "user_id": str(user_id),
                "period_days": period_days,
                "comparison_summary": {
                    "total_comparisons": len(comparisons),
                    "service_categories_compared": len(set(c.service_category for c in comparisons)),
                    "average_options_per_comparison": sum(
                        len(c.evaluated_options or []) for c in comparisons
                    ) / len(comparisons) if comparisons else 0,
                    "decision_success_rate": decision_patterns.get("success_rate", 0)
                },
                "decision_patterns": decision_patterns,
                "spending_analysis": {
                    "total_spending": spending_patterns["total_spending"],
                    "average_monthly_spending": spending_patterns["avg_monthly_spending"],
                    "spending_trend": spending_patterns["spending_trend"],
                    "cost_consciousness_score": spending_patterns["cost_consciousness"]
                },
                "feature_preferences": feature_preferences,
                "value_optimization": {
                    "overall_value_score": value_metrics["overall_score"],
                    "value_trend": value_metrics["trend"],
                    "overspending_incidents": value_metrics["overspending_count"],
                    "underutilization_rate": value_metrics["underutilization_rate"]
                },
                "upgrade_behavior": upgrade_patterns,
                "recommendations": await self._generate_analytics_recommendations(
                    user_id, decision_patterns, spending_patterns, feature_preferences
                ),
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get feature price analytics: {e}")
            raise
    
    async def recommend_optimal_pricing_tier(
        self,
        user_id: uuid.UUID,
        service_name: str,
        usage_patterns: Dict[str, Any],
        feature_requirements: List[str]
    ) -> Dict[str, Any]:
        """Recommend optimal pricing tier for a specific service"""
        
        try:
            # Get available pricing tiers for the service
            pricing_tiers = await self._get_service_pricing_tiers(service_name)
            
            if not pricing_tiers:
                return {"success": False, "error": f"No pricing tiers found for service {service_name}"}
            
            # Analyze usage patterns
            usage_analysis = await self._analyze_usage_patterns(usage_patterns)
            
            # Evaluate each pricing tier
            tier_evaluations = []
            for tier in pricing_tiers:
                evaluation = await self._evaluate_pricing_tier(
                    user_id, tier, usage_analysis, feature_requirements
                )
                tier_evaluations.append(evaluation)
            
            # Get user's budget preferences
            user_budget = await self._get_user_budget_preferences(user_id)
            
            # Select optimal tier
            optimal_tier = await self._select_optimal_pricing_tier(
                tier_evaluations, user_budget, usage_analysis
            )
            
            # Generate cost projections
            cost_projections = await self._generate_cost_projections(
                optimal_tier, usage_analysis
            )
            
            # Analyze potential savings
            savings_analysis = await self._analyze_potential_savings(
                tier_evaluations, optimal_tier
            )
            
            # Generate usage recommendations
            usage_recommendations = await self._generate_usage_recommendations(
                optimal_tier, usage_analysis, feature_requirements
            )
            
            return {
                "user_id": str(user_id),
                "service_name": service_name,
                "recommended_tier": optimal_tier,
                "all_tier_evaluations": tier_evaluations,
                "cost_analysis": {
                    "recommended_monthly_cost": optimal_tier["estimated_monthly_cost"],
                    "cost_per_feature": optimal_tier["cost_per_feature"],
                    "cost_projections": cost_projections,
                    "potential_savings": savings_analysis
                },
                "feature_analysis": {
                    "included_features": optimal_tier["included_features"],
                    "missing_features": optimal_tier["missing_features"],
                    "feature_value_score": optimal_tier["feature_value_score"]
                },
                "usage_optimization": {
                    "current_utilization": usage_analysis["utilization_score"],
                    "recommended_adjustments": usage_recommendations,
                    "efficiency_opportunities": usage_analysis["efficiency_opportunities"]
                },
                "decision_confidence": optimal_tier["confidence_score"],
                "alternative_recommendations": await self._generate_tier_alternatives(
                    tier_evaluations, optimal_tier
                ),
                "recommendation_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to recommend optimal pricing tier: {e}")
            raise
    
    # Helper methods
    
    async def _get_service_options(
        self,
        service_category: str,
        comparison_request: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get available service options for comparison"""
        
        # This would typically fetch from a service database or API
        # For now, return mock data structure
        
        mock_services = {
            "cloud_storage": [
                {
                    "name": "CloudDrive Pro",
                    "provider": "TechCorp",
                    "pricing": {"monthly": 9.99, "annual": 99.99},
                    "features": ["1TB storage", "file sync", "sharing", "versioning", "encryption"],
                    "limits": {"storage_gb": 1024, "bandwidth_gb": 100, "users": 1},
                    "ratings": {"overall": 4.5, "performance": 4.3, "support": 4.1}
                },
                {
                    "name": "DataVault Business",
                    "provider": "SecureTech",
                    "pricing": {"monthly": 19.99, "annual": 199.99},
                    "features": ["2TB storage", "team collaboration", "advanced encryption", "compliance", "priority support"],
                    "limits": {"storage_gb": 2048, "bandwidth_gb": 500, "users": 10},
                    "ratings": {"overall": 4.7, "performance": 4.6, "support": 4.8}
                },
                {
                    "name": "SimpleStore",
                    "provider": "EasyTech",
                    "pricing": {"monthly": 4.99, "annual": 49.99},
                    "features": ["500GB storage", "basic sync", "mobile apps"],
                    "limits": {"storage_gb": 512, "bandwidth_gb": 50, "users": 1},
                    "ratings": {"overall": 4.0, "performance": 3.8, "support": 3.9}
                }
            ],
            "project_management": [
                {
                    "name": "TaskMaster Pro",
                    "provider": "ProductivityCorp",
                    "pricing": {"monthly": 15.99, "annual": 159.99},
                    "features": ["unlimited projects", "team collaboration", "time tracking", "reporting", "integrations"],
                    "limits": {"projects": -1, "users": 25, "storage_gb": 100},
                    "ratings": {"overall": 4.4, "performance": 4.2, "support": 4.3}
                }
            ]
        }
        
        return mock_services.get(service_category, [])
    
    async def _analyze_feature_requirements(
        self,
        comparison_request: Dict[str, Any],
        user_preferences: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze user's feature requirements"""
        
        requirements = {
            "must_have": comparison_request.get("required_features", []),
            "nice_to_have": comparison_request.get("preferred_features", []),
            "deal_breakers": comparison_request.get("excluded_features", []),
            "importance_scores": {}
        }
        
        # Set importance scores
        all_features = requirements["must_have"] + requirements["nice_to_have"]
        for feature in all_features:
            if feature in requirements["must_have"]:
                requirements["importance_scores"][feature] = 10  # Critical
            else:
                requirements["importance_scores"][feature] = 7   # Important but not critical
        
        # Adjust based on user preferences
        if user_preferences and "feature_priorities" in user_preferences:
            for feature, priority in user_preferences["feature_priorities"].items():
                requirements["importance_scores"][feature] = priority
        
        return requirements
    
    async def _get_user_comparison_profile(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """Get user's comparison and decision profile"""
        
        # Get recent comparisons to build profile
        result = await self.db.execute(
            select(FeaturePriceComparison).where(
                FeaturePriceComparison.user_id == user_id
            ).order_by(FeaturePriceComparison.comparison_date.desc()).limit(20)
        )
        recent_comparisons = result.scalars().all()
        
        if not recent_comparisons:
            return {
                "budget_preference": "moderate",
                "feature_focus": "balanced",
                "price_sensitivity": 0.5,
                "feature_importance": 0.5
            }
        
        # Analyze historical patterns
        total_comparisons = len(recent_comparisons)
        feature_focused = len([c for c in recent_comparisons if c.decision_approach == "feature_first"])
        price_focused = len([c for c in recent_comparisons if c.decision_approach == "price_first"])
        
        feature_focus_rate = feature_focused / total_comparisons
        price_focus_rate = price_focused / total_comparisons
        
        return {
            "budget_preference": "high" if price_focus_rate > 0.6 else "moderate",
            "feature_focus": "high" if feature_focus_rate > 0.6 else "balanced",
            "price_sensitivity": price_focus_rate,
            "feature_importance": feature_focus_rate,
            "comparison_frequency": "high" if total_comparisons > 15 else "moderate"
        }
    
    async def _evaluate_service_option(
        self,
        user_id: uuid.UUID,
        service: Dict[str, Any],
        feature_requirements: Dict[str, Any],
        budget_constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate a single service option"""
        
        evaluation = {
            "service": service,
            "feature_score": 0,
            "price_score": 0,
            "value_score": 0,
            "overall_score": 0,
            "met_requirements": [],
            "missing_requirements": [],
            "budget_fit": True,
            "strengths": [],
            "weaknesses": [],
            "feature_coverage": 0
        }
        
        # Evaluate feature coverage
        service_features = set(service.get("features", []))
        
        # Check must-have features
        must_have = set(feature_requirements["must_have"])
        met_must_have = must_have.intersection(service_features)
        missing_must_have = must_have - service_features
        
        evaluation["met_requirements"] = list(met_must_have)
        evaluation["missing_requirements"] = list(missing_must_have)
        
        # Calculate feature score
        feature_score = 0
        for feature in service_features:
            importance = feature_requirements["importance_scores"].get(feature, 5)
            feature_score += importance
        
        # Penalty for missing must-have features
        if missing_must_have:
            feature_score *= (len(met_must_have) / len(must_have)) if must_have else 1
        
        evaluation["feature_score"] = min(100, feature_score)
        evaluation["feature_coverage"] = len(met_must_have) / len(must_have) if must_have else 1
        
        # Evaluate pricing
        monthly_price = service["pricing"]["monthly"]
        annual_price = service["pricing"]["annual"]
        
        # Check budget constraints
        max_budget = budget_constraints.get("max_budget")
        if max_budget and monthly_price > max_budget:
            evaluation["budget_fit"] = False
            evaluation["weaknesses"].append(f"Exceeds budget by ${monthly_price - max_budget:.2f}")
        
        # Price score (inverse relationship - lower price = higher score)
        max_reasonable_price = budget_constraints.get("max_budget", 100)
        evaluation["price_score"] = max(0, 100 - (monthly_price / max_reasonable_price * 100))
        
        # Calculate value score (features per dollar)
        if monthly_price > 0:
            evaluation["value_score"] = (evaluation["feature_score"] / monthly_price) * 10
        else:
            evaluation["value_score"] = evaluation["feature_score"]
        
        # Identify strengths and weaknesses
        if service["ratings"]["overall"] >= 4.5:
            evaluation["strengths"].append("Highly rated by users")
        
        if len(service["features"]) >= 5:
            evaluation["strengths"].append("Feature-rich offering")
        
        if monthly_price < 10:
            evaluation["strengths"].append("Budget-friendly pricing")
        elif monthly_price > 50:
            evaluation["weaknesses"].append("Premium pricing")
        
        if evaluation["feature_coverage"] < 0.8:
            evaluation["weaknesses"].append("Missing some required features")
        
        return evaluation
    
    async def _calculate_comparison_weights(
        self,
        user_id: uuid.UUID,
        user_profile: Dict[str, Any],
        user_preferences: Optional[Dict[str, Any]],
        feature_requirements: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate weights for comparison factors"""
        
        weights = {
            "feature_weight": 0.4,
            "price_weight": 0.3,
            "value_weight": 0.2,
            "ratings_weight": 0.1
        }
        
        # Adjust based on user profile
        if user_profile["price_sensitivity"] > 0.7:
            weights["price_weight"] = 0.5
            weights["feature_weight"] = 0.3
        elif user_profile["feature_importance"] > 0.7:
            weights["feature_weight"] = 0.5
            weights["price_weight"] = 0.2
        
        # Adjust based on explicit preferences
        if user_preferences:
            if "price_importance" in user_preferences:
                weights["price_weight"] = float(user_preferences["price_importance"])
            if "feature_importance" in user_preferences:
                weights["feature_weight"] = float(user_preferences["feature_importance"])
            if "value_importance" in user_preferences:
                weights["value_weight"] = float(user_preferences["value_importance"])
        
        # Critical features boost feature weight
        if len(feature_requirements["must_have"]) > 5:
            weights["feature_weight"] += 0.1
            weights["price_weight"] -= 0.05
            weights["value_weight"] -= 0.05
        
        # Normalize weights
        total_weight = sum(weights.values())
        for key in weights:
            weights[key] /= total_weight
        
        return weights
    
    async def _rank_service_options(
        self,
        evaluations: List[Dict[str, Any]],
        weights: Dict[str, float],
        budget_constraints: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Rank service options based on weighted scoring"""
        
        ranked_services = []
        
        for evaluation in evaluations:
            # Calculate overall weighted score
            overall_score = (
                evaluation["feature_score"] * weights["feature_weight"] +
                evaluation["price_score"] * weights["price_weight"] +
                evaluation["value_score"] * weights["value_weight"] +
                evaluation["service"]["ratings"]["overall"] * 10 * weights["ratings_weight"]
            )
            
            # Apply penalties
            if not evaluation["budget_fit"]:
                overall_score *= 0.5  # Major penalty for budget violations
            
            if evaluation["feature_coverage"] < 1.0:
                overall_score *= evaluation["feature_coverage"]  # Penalty for missing features
            
            ranked_evaluation = {
                **evaluation,
                "overall_score": overall_score,
                "rank_reasoning": [
                    f"Feature score: {evaluation['feature_score']:.1f} (weight: {weights['feature_weight']:.2f})",
                    f"Price score: {evaluation['price_score']:.1f} (weight: {weights['price_weight']:.2f})",
                    f"Value score: {evaluation['value_score']:.1f} (weight: {weights['value_weight']:.2f})",
                    f"Overall rating: {evaluation['service']['ratings']['overall']:.1f}"
                ]
            }
            
            ranked_services.append(ranked_evaluation)
        
        # Sort by overall score (descending)
        ranked_services.sort(key=lambda x: x["overall_score"], reverse=True)
        
        return ranked_services
    
    async def _generate_comparison_matrix(
        self,
        ranked_services: List[Dict[str, Any]],
        feature_requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a comparison matrix for services"""
        
        if not ranked_services:
            return {"error": "No services to compare"}
        
        # Get all unique features
        all_features = set()
        for service_eval in ranked_services:
            all_features.update(service_eval["service"]["features"])
        
        # Add required features that might be missing
        all_features.update(feature_requirements["must_have"])
        all_features.update(feature_requirements["nice_to_have"])
        
        all_features = sorted(list(all_features))
        
        # Build comparison matrix
        matrix = {
            "features": all_features,
            "services": [],
            "summary": {
                "total_features_compared": len(all_features),
                "services_compared": len(ranked_services)
            }
        }
        
        for service_eval in ranked_services[:5]:  # Top 5 services
            service = service_eval["service"]
            service_features = set(service["features"])
            
            service_comparison = {
                "name": service["name"],
                "provider": service["provider"],
                "monthly_price": service["pricing"]["monthly"],
                "overall_score": service_eval["overall_score"],
                "feature_support": {},
                "key_metrics": {
                    "feature_coverage": service_eval["feature_coverage"],
                    "price_per_feature": service["pricing"]["monthly"] / len(service["features"]) if service["features"] else 0,
                    "user_rating": service["ratings"]["overall"]
                }
            }
            
            # Check feature support
            for feature in all_features:
                is_supported = feature in service_features
                importance = feature_requirements["importance_scores"].get(feature, 5)
                
                service_comparison["feature_support"][feature] = {
                    "supported": is_supported,
                    "importance": importance,
                    "is_required": feature in feature_requirements["must_have"]
                }
            
            matrix["services"].append(service_comparison)
        
        return matrix
    
    async def _identify_value_recommendations(
        self,
        ranked_services: List[Dict[str, Any]],
        feature_requirements: Dict[str, Any],
        budget_constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Identify best value recommendations"""
        
        recommendations = {
            "best_overall_value": None,
            "best_budget_option": None,
            "best_premium_option": None,
            "feature_leader": None,
            "price_leader": None
        }
        
        if not ranked_services:
            return recommendations
        
        # Best overall value (highest overall score)
        recommendations["best_overall_value"] = {
            "service": ranked_services[0]["service"]["name"],
            "reason": f"Highest overall score ({ranked_services[0]['overall_score']:.1f}) with good feature-price balance",
            "monthly_cost": ranked_services[0]["service"]["pricing"]["monthly"],
            "key_strengths": ranked_services[0]["strengths"][:3]
        }
        
        # Best budget option (lowest price among viable options)
        budget_options = [s for s in ranked_services if s["budget_fit"] and s["feature_coverage"] >= 0.7]
        if budget_options:
            budget_leader = min(budget_options, key=lambda x: x["service"]["pricing"]["monthly"])
            recommendations["best_budget_option"] = {
                "service": budget_leader["service"]["name"],
                "reason": f"Lowest cost (${budget_leader['service']['pricing']['monthly']:.2f}) while meeting most requirements",
                "monthly_cost": budget_leader["service"]["pricing"]["monthly"],
                "feature_coverage": budget_leader["feature_coverage"]
            }
        
        # Feature leader (highest feature score)
        feature_leader = max(ranked_services, key=lambda x: x["feature_score"])
        recommendations["feature_leader"] = {
            "service": feature_leader["service"]["name"],
            "reason": f"Most comprehensive features (score: {feature_leader['feature_score']:.1f})",
            "monthly_cost": feature_leader["service"]["pricing"]["monthly"],
            "features_count": len(feature_leader["service"]["features"])
        }
        
        # Price leader (lowest absolute price)
        price_leader = min(ranked_services, key=lambda x: x["service"]["pricing"]["monthly"])
        recommendations["price_leader"] = {
            "service": price_leader["service"]["name"],
            "reason": f"Lowest absolute price (${price_leader['service']['pricing']['monthly']:.2f})",
            "monthly_cost": price_leader["service"]["pricing"]["monthly"],
            "value_limitations": price_leader["weaknesses"][:2]
        }
        
        return recommendations
    
    async def _analyze_price_performance_ratio(
        self,
        ranked_services: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze price-performance ratio across services"""
        
        if not ranked_services:
            return {"error": "No services to analyze"}
        
        analysis = {
            "price_performance_scores": [],
            "value_curve_analysis": {},
            "price_tiers": {},
            "performance_vs_cost_insights": []
        }
        
        # Calculate price-performance ratios
        for service_eval in ranked_services:
            service = service_eval["service"]
            monthly_price = service["pricing"]["monthly"]
            performance_score = service_eval["feature_score"] + service["ratings"]["overall"] * 10
            
            if monthly_price > 0:
                ratio = performance_score / monthly_price
            else:
                ratio = performance_score
            
            analysis["price_performance_scores"].append({
                "service_name": service["name"],
                "monthly_price": monthly_price,
                "performance_score": performance_score,
                "price_performance_ratio": ratio,
                "value_category": "excellent" if ratio > 8 else "good" if ratio > 5 else "moderate"
            })
        
        # Sort by ratio for value curve analysis
        sorted_by_ratio = sorted(analysis["price_performance_scores"], key=lambda x: x["price_performance_ratio"], reverse=True)
        
        # Identify price tiers
        prices = [s["service"]["pricing"]["monthly"] for s in ranked_services]
        if prices:
            min_price, max_price = min(prices), max(prices)
            tier_size = (max_price - min_price) / 3 if max_price > min_price else 1
            
            analysis["price_tiers"] = {
                "budget": {"min": min_price, "max": min_price + tier_size, "services": []},
                "mid_range": {"min": min_price + tier_size, "max": min_price + 2*tier_size, "services": []},
                "premium": {"min": min_price + 2*tier_size, "max": max_price, "services": []}
            }
            
            for service_eval in ranked_services:
                price = service_eval["service"]["pricing"]["monthly"]
                service_name = service_eval["service"]["name"]
                
                if price <= analysis["price_tiers"]["budget"]["max"]:
                    analysis["price_tiers"]["budget"]["services"].append(service_name)
                elif price <= analysis["price_tiers"]["mid_range"]["max"]:
                    analysis["price_tiers"]["mid_range"]["services"].append(service_name)
                else:
                    analysis["price_tiers"]["premium"]["services"].append(service_name)
        
        # Generate insights
        if len(sorted_by_ratio) >= 2:
            best_value = sorted_by_ratio[0]
            analysis["performance_vs_cost_insights"].append(
                f"{best_value['service_name']} offers the best price-performance ratio ({best_value['price_performance_ratio']:.1f})"
            )
            
            if len(sorted_by_ratio) >= 3:
                price_range = max(prices) - min(prices)
                if price_range > 20:  # Significant price variation
                    analysis["performance_vs_cost_insights"].append(
                        "Significant price variation suggests different target markets - consider your specific needs"
                    )
        
        return analysis
    
    # Additional helper methods would continue here...
    # This implementation provides a comprehensive foundation for feature vs price comparison
    # with intelligent analysis, ranking, and recommendation capabilities
    
    async def _store_feature_price_comparison(
        self,
        user_id: uuid.UUID,
        service_category: str,
        comparison_request: Dict[str, Any],
        ranked_services: List[Dict[str, Any]],
        preference_weights: Dict[str, float]
    ):
        """Store the feature vs price comparison for learning"""
        
        comparison = FeaturePriceComparison(
            user_id=user_id,
            service_category=service_category,
            comparison_criteria=comparison_request,
            evaluated_options=[s["service"] for s in ranked_services[:10]],
            selected_option=ranked_services[0]["service"] if ranked_services else None,
            decision_approach="balanced",  # Would determine from weights
            preference_weights=preference_weights,
            comparison_date=datetime.utcnow()
        )
        
        self.db.add(comparison)
        await self.db.commit()
    
    async def _identify_primary_factors(self, preference_weights: Dict[str, float]) -> List[str]:
        """Identify primary decision factors from weights"""
        
        sorted_weights = sorted(preference_weights.items(), key=lambda x: x[1], reverse=True)
        return [factor.replace("_weight", "").replace("_", " ").title() for factor, _ in sorted_weights[:3]]
    
    async def _generate_decision_guidance(
        self,
        ranked_services: List[Dict[str, Any]],
        feature_requirements: Dict[str, Any],
        budget_constraints: Dict[str, Any]
    ) -> List[str]:
        """Generate decision guidance for the user"""
        
        guidance = []
        
        if not ranked_services:
            return ["No suitable services found matching your criteria"]
        
        top_service = ranked_services[0]
        
        if top_service["budget_fit"]:
            guidance.append(f"Recommended: {top_service['service']['name']} offers the best overall value for your needs")
        else:
            guidance.append("Top-rated option exceeds your budget - consider budget alternatives or adjust requirements")
        
        if top_service["feature_coverage"] < 1.0:
            missing_features = top_service["missing_requirements"]
            guidance.append(f"Note: Top option missing {len(missing_features)} required features: {', '.join(missing_features[:3])}")
        
        # Budget guidance
        max_budget = budget_constraints.get("max_budget")
        if max_budget:
            affordable_options = len([s for s in ranked_services if s["budget_fit"]])
            guidance.append(f"{affordable_options} out of {len(ranked_services)} options fit your ${max_budget}/month budget")
        
        return guidance
    
    # Placeholder methods for upgrade evaluation
    async def _analyze_current_service(self, user_id: uuid.UUID, current_service: Dict[str, Any], context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze current service satisfaction and limitations"""
        return {
            "satisfaction_score": 7,
            "limitations": ["limited storage", "slow sync"],
            "utilization_rate": 0.8,
            "value_score": 6
        }
    
    async def _evaluate_upgrade_option(self, user_id: uuid.UUID, current_service: Dict[str, Any], upgrade: Dict[str, Any], current_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate an upgrade option"""
        return {
            "upgrade": upgrade,
            "improvement_score": 8,
            "cost_increase": 10,
            "roi_months": 6
        }
    
    # Additional placeholder methods for completeness
    async def _get_upgrade_preferences(self, user_id: uuid.UUID) -> Dict[str, Any]:
        return {"upgrade_threshold": 0.7, "max_cost_increase": 20}
    
    async def _calculate_upgrade_decision_factors(self, current_analysis: Dict[str, Any], upgrade_evaluations: List[Dict[str, Any]], upgrade_preferences: Dict[str, Any]) -> Dict[str, float]:
        return {"improvement_weight": 0.6, "cost_weight": 0.4}
    
    async def _make_upgrade_recommendation(self, upgrade_evaluations: List[Dict[str, Any]], decision_factors: Dict[str, float], current_analysis: Dict[str, Any]) -> Dict[str, Any]:
        return {"recommended": True, "upgrade_option": upgrade_evaluations[0] if upgrade_evaluations else None, "confidence": 0.8}
    
    async def _analyze_upgrade_cost_benefit(self, current_service: Dict[str, Any], upgrade_evaluations: List[Dict[str, Any]], upgrade_recommendation: Dict[str, Any]) -> Dict[str, Any]:
        return {"cost_increase": 15, "benefit_score": 25, "roi_months": 8}
    
    async def _recommend_upgrade_timing(self, upgrade_recommendation: Dict[str, Any], current_analysis: Dict[str, Any], context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        return {"recommended_timing": "within_3_months", "reasoning": "Current limitations impacting productivity"}
    
    async def _assess_upgrade_risks(self, current_service: Dict[str, Any], upgrade_recommendation: Dict[str, Any]) -> Dict[str, Any]:
        return {"migration_risk": "low", "cost_risk": "medium", "feature_risk": "low"}
    
    async def _suggest_upgrade_alternatives(self, upgrade_evaluations: List[Dict[str, Any]], upgrade_recommendation: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [{"alternative": "gradual_upgrade", "description": "Upgrade in phases to minimize risk"}]
    
    # Placeholder methods for analytics
    async def _analyze_decision_patterns(self, comparisons: List[FeaturePriceComparison]) -> Dict[str, Any]:
        return {"success_rate": 0.85, "primary_approach": "feature_first"}
    
    async def _analyze_spending_patterns(self, comparisons: List[FeaturePriceComparison], value_assessments: List[ValueAssessment]) -> Dict[str, Any]:
        return {"total_spending": 500, "avg_monthly_spending": 167, "spending_trend": "stable", "cost_consciousness": 0.7}
    
    async def _analyze_feature_preferences(self, comparisons: List[FeaturePriceComparison]) -> Dict[str, Any]:
        return {"top_features": ["storage", "sync", "security"], "feature_sensitivity": 0.8}
    
    async def _calculate_value_metrics(self, comparisons: List[FeaturePriceComparison], value_assessments: List[ValueAssessment]) -> Dict[str, Any]:
        return {"overall_score": 7.5, "trend": "improving", "overspending_count": 2, "underutilization_rate": 0.3}
    
    async def _analyze_upgrade_patterns(self, comparisons: List[FeaturePriceComparison]) -> Dict[str, Any]:
        return {"upgrade_frequency": "annual", "upgrade_triggers": ["storage_limit", "new_features"]}
    
    async def _generate_analytics_recommendations(self, user_id: uuid.UUID, decision_patterns: Dict[str, Any], spending_patterns: Dict[str, Any], feature_preferences: Dict[str, Any]) -> List[str]:
        return ["Consider consolidating services to reduce costs", "Review underutilized features quarterly"]
    
    # Pricing tier recommendation placeholders
    async def _get_service_pricing_tiers(self, service_name: str) -> List[Dict[str, Any]]:
        return [
            {"name": "Basic", "price": 9.99, "features": ["basic_feature"], "limits": {"users": 1}},
            {"name": "Pro", "price": 19.99, "features": ["basic_feature", "advanced_feature"], "limits": {"users": 5}}
        ]
    
    async def _analyze_usage_patterns(self, usage_patterns: Dict[str, Any]) -> Dict[str, Any]:
        return {"utilization_score": 0.75, "efficiency_opportunities": ["reduce_redundant_features"]}
    
    async def _evaluate_pricing_tier(self, user_id: uuid.UUID, tier: Dict[str, Any], usage_analysis: Dict[str, Any], feature_requirements: List[str]) -> Dict[str, Any]:
        return {
            "tier": tier,
            "estimated_monthly_cost": tier["price"],
            "feature_value_score": 8,
            "included_features": tier["features"],
            "missing_features": [],
            "confidence_score": 0.8
        }
    
    async def _get_user_budget_preferences(self, user_id: uuid.UUID) -> Dict[str, Any]:
        return {"preferred_budget": 25, "max_budget": 50}
    
    async def _select_optimal_pricing_tier(self, tier_evaluations: List[Dict[str, Any]], user_budget: Dict[str, Any], usage_analysis: Dict[str, Any]) -> Dict[str, Any]:
        return tier_evaluations[0] if tier_evaluations else {}
    
    async def _generate_cost_projections(self, optimal_tier: Dict[str, Any], usage_analysis: Dict[str, Any]) -> Dict[str, Any]:
        return {"monthly": optimal_tier.get("estimated_monthly_cost", 0), "annual": optimal_tier.get("estimated_monthly_cost", 0) * 12}
    
    async def _analyze_potential_savings(self, tier_evaluations: List[Dict[str, Any]], optimal_tier: Dict[str, Any]) -> Dict[str, Any]:
        return {"potential_monthly_savings": 10, "annual_savings": 120}
    
    async def _generate_usage_recommendations(self, optimal_tier: Dict[str, Any], usage_analysis: Dict[str, Any], feature_requirements: List[str]) -> List[str]:
        return ["Enable auto-scaling to optimize costs", "Review usage monthly for optimization opportunities"]
    
    async def _generate_tier_alternatives(self, tier_evaluations: List[Dict[str, Any]], optimal_tier: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [{"tier": "alternative", "reason": "Lower cost with minimal feature impact"}]