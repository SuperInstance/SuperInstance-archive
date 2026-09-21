"""
Call Routing Logic System
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from ..database import CallRouting, BusinessHours, CallRoutingType


class CallRouter:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        
        # Default routing keywords
        self.routing_keywords = {
            CallRoutingType.SALES: [
                "buy", "purchase", "price", "cost", "quote", "demo", "trial",
                "sales", "pricing", "plan", "package", "subscription"
            ],
            CallRoutingType.SUPPORT: [
                "help", "problem", "issue", "error", "trouble", "broken",
                "support", "fix", "not working", "bug", "assistance"
            ],
            CallRoutingType.BILLING: [
                "bill", "billing", "payment", "charge", "invoice", "refund",
                "account", "balance", "subscription", "cancel", "upgrade"
            ],
            CallRoutingType.TECHNICAL: [
                "technical", "setup", "configuration", "install", "integration",
                "api", "developer", "code", "programming", "database"
            ],
            CallRoutingType.APPOINTMENT: [
                "appointment", "schedule", "book", "meeting", "consultation",
                "reservation", "available", "calendar", "time slot"
            ],
            CallRoutingType.EMERGENCY: [
                "emergency", "urgent", "critical", "immediately", "asap",
                "down", "outage", "security", "breach", "hack"
            ]
        }
        
        # Routing priorities (higher number = higher priority)
        self.routing_priorities = {
            CallRoutingType.EMERGENCY: 10,
            CallRoutingType.BILLING: 7,
            CallRoutingType.TECHNICAL: 6,
            CallRoutingType.SUPPORT: 5,
            CallRoutingType.APPOINTMENT: 4,
            CallRoutingType.SALES: 3,
            CallRoutingType.GENERAL: 1
        }
    
    async def analyze_routing_intent(
        self,
        message: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Analyze message to determine routing intent"""
        
        message_lower = message.lower()
        routing_scores = {}
        
        # Score each routing category
        for category, keywords in self.routing_keywords.items():
            score = 0
            matched_keywords = []
            
            for keyword in keywords:
                if keyword in message_lower:
                    score += 1
                    matched_keywords.append(keyword)
            
            if score > 0:
                # Apply context boost if available
                if context:
                    score = self._apply_context_boost(score, category, context)
                
                routing_scores[category] = {
                    "score": score,
                    "matched_keywords": matched_keywords,
                    "priority": self.routing_priorities.get(category, 1)
                }
        
        # Determine best routing
        if routing_scores:
            # Sort by priority first, then by score
            best_category = max(
                routing_scores.keys(),
                key=lambda x: (routing_scores[x]["priority"], routing_scores[x]["score"])
            )
            
            confidence = min(1.0, routing_scores[best_category]["score"] / 3)
            
            return {
                "recommended_routing": best_category.value,
                "confidence": confidence,
                "all_scores": {k.value: v for k, v in routing_scores.items()},
                "matched_keywords": routing_scores[best_category]["matched_keywords"],
                "routing_reason": f"Detected {best_category.value} intent from keywords"
            }
        
        return {
            "recommended_routing": CallRoutingType.GENERAL.value,
            "confidence": 0.5,
            "all_scores": {},
            "matched_keywords": [],
            "routing_reason": "No specific intent detected, using general routing"
        }
    
    async def get_routing_destination(
        self,
        routing_category: str,
        business_hours_only: bool = True
    ) -> Dict[str, Any]:
        """Get routing destination for category"""
        
        # Get routing rules from database
        stmt = select(CallRouting).where(
            CallRouting.category == routing_category,
            CallRouting.is_active == True
        ).order_by(CallRouting.priority.desc())
        
        if business_hours_only:
            stmt = stmt.where(CallRouting.business_hours_only == True)
        
        result = await self.db.execute(stmt)
        routing_rules = result.scalars().all()
        
        if not routing_rules:
            return {
                "destination": "general_queue",
                "routing_type": "default",
                "estimated_wait_time": "5-10 minutes"
            }
        
        # Use the highest priority rule
        best_rule = routing_rules[0]
        
        return {
            "destination": best_rule.destination,
            "routing_type": "rule_based",
            "rule_name": best_rule.routing_rule,
            "estimated_wait_time": self._estimate_wait_time(routing_category),
            "success_rate": best_rule.success_rate
        }
    
    async def get_routing_rules(self) -> List[Dict[str, Any]]:
        """Get all active routing rules"""
        
        stmt = select(CallRouting).where(
            CallRouting.is_active == True
        ).order_by(CallRouting.category, CallRouting.priority.desc())
        
        result = await self.db.execute(stmt)
        rules = result.scalars().all()
        
        routing_rules = []
        for rule in rules:
            routing_rules.append({
                "id": str(rule.id),
                "rule_name": rule.routing_rule,
                "category": rule.category.value,
                "keywords": rule.keywords,
                "conditions": rule.conditions,
                "destination": rule.destination,
                "priority": rule.priority,
                "business_hours_only": rule.business_hours_only,
                "success_rate": rule.success_rate,
                "is_active": rule.is_active
            })
        
        return routing_rules
    
    async def update_routing_rule(
        self,
        rule_id: str,
        keywords: List[str] = None,
        conditions: Dict[str, Any] = None,
        destination: str = None,
        priority: int = None,
        is_active: bool = None
    ) -> Dict[str, Any]:
        """Update routing rule"""
        
        update_values = {}
        
        if keywords is not None:
            update_values["keywords"] = keywords
        if conditions is not None:
            update_values["conditions"] = conditions
        if destination is not None:
            update_values["destination"] = destination
        if priority is not None:
            update_values["priority"] = priority
        if is_active is not None:
            update_values["is_active"] = is_active
        
        if update_values:
            stmt = update(CallRouting).where(
                CallRouting.id == rule_id
            ).values(**update_values)
            
            await self.db.execute(stmt)
            await self.db.commit()
        
        return {"status": "updated", "rule_id": rule_id}
    
    async def create_routing_rule(
        self,
        rule_name: str,
        category: str,
        keywords: List[str],
        destination: str,
        conditions: Dict[str, Any] = None,
        priority: int = 1,
        business_hours_only: bool = True
    ) -> Dict[str, Any]:
        """Create new routing rule"""
        
        try:
            category_enum = CallRoutingType(category)
        except ValueError:
            raise ValueError(f"Invalid category: {category}")
        
        new_rule = CallRouting(
            routing_rule=rule_name,
            category=category_enum,
            keywords=keywords,
            conditions=conditions or {},
            destination=destination,
            priority=priority,
            business_hours_only=business_hours_only,
            success_rate=0.0  # Will be updated as rule is used
        )
        
        self.db.add(new_rule)
        await self.db.commit()
        
        return {
            "status": "created",
            "rule_id": str(new_rule.id),
            "rule_name": rule_name,
            "category": category
        }
    
    async def optimize_routing_rules(self) -> Dict[str, Any]:
        """Analyze and optimize routing rules based on performance"""
        
        # Get all rules with their performance data
        stmt = select(CallRouting)
        result = await self.db.execute(stmt)
        rules = result.scalars().all()
        
        recommendations = []
        optimizations_applied = 0
        
        for rule in rules:
            # Analyze rule performance
            if rule.success_rate < 0.7 and rule.success_rate > 0:  # Has data but poor performance
                recommendations.append({
                    "rule_id": str(rule.id),
                    "issue": "Low success rate",
                    "current_rate": rule.success_rate,
                    "recommendation": "Review keywords and conditions",
                    "priority": "high"
                })
            
            # Check for unused rules
            # if rule.usage_count == 0:  # Would need to add usage tracking
            #     recommendations.append({
            #         "rule_id": str(rule.id),
            #         "issue": "Unused rule",
            #         "recommendation": "Consider deactivating or updating keywords",
            #         "priority": "low"
            #     })
        
        # Auto-optimization: Disable very poor performing rules
        for rule in rules:
            if rule.success_rate < 0.3 and rule.success_rate > 0:
                stmt = update(CallRouting).where(
                    CallRouting.id == rule.id
                ).values(is_active=False)
                await self.db.execute(stmt)
                optimizations_applied += 1
        
        if optimizations_applied > 0:
            await self.db.commit()
        
        return {
            "recommendations": recommendations,
            "auto_optimizations_applied": optimizations_applied,
            "total_rules_analyzed": len(rules),
            "improvement_areas": self._identify_improvement_areas(rules)
        }
    
    async def get_routing_analytics(self) -> Dict[str, Any]:
        """Get routing performance analytics"""
        
        stmt = select(CallRouting)
        result = await self.db.execute(stmt)
        rules = result.scalars().all()
        
        if not rules:
            return {"total_rules": 0}
        
        # Calculate metrics
        active_rules = [r for r in rules if r.is_active]
        avg_success_rate = sum(r.success_rate for r in rules if r.success_rate > 0) / max(1, len([r for r in rules if r.success_rate > 0]))
        
        # Category distribution
        category_dist = {}
        for rule in rules:
            category = rule.category.value
            if category not in category_dist:
                category_dist[category] = {"count": 0, "avg_success": 0}
            category_dist[category]["count"] += 1
            if rule.success_rate > 0:
                category_dist[category]["avg_success"] = (
                    category_dist[category]["avg_success"] + rule.success_rate
                ) / 2
        
        return {
            "total_rules": len(rules),
            "active_rules": len(active_rules),
            "average_success_rate": avg_success_rate,
            "category_distribution": category_dist,
            "top_performing_rules": self._get_top_performing_rules(rules),
            "routing_effectiveness": self._calculate_routing_effectiveness(rules)
        }
    
    # Private methods
    def _apply_context_boost(
        self,
        score: float,
        category: CallRoutingType,
        context: Dict[str, Any]
    ) -> float:
        """Apply context-based score boost"""
        
        # Boost based on previous interactions
        if "previous_category" in context:
            if context["previous_category"] == category.value:
                score *= 1.2  # 20% boost for consistency
        
        # Boost based on user profile
        if "user_type" in context:
            if context["user_type"] == "enterprise" and category == CallRoutingType.TECHNICAL:
                score *= 1.1
            elif context["user_type"] == "trial" and category == CallRoutingType.SALES:
                score *= 1.1
        
        # Boost based on urgency indicators
        if "urgency" in context and context["urgency"] > 0.7:
            if category == CallRoutingType.EMERGENCY:
                score *= 1.5
        
        return score
    
    def _estimate_wait_time(self, routing_category: str) -> str:
        """Estimate wait time for routing category"""
        
        # Mock wait time estimation (in production, use real queue data)
        wait_times = {
            "emergency": "immediate",
            "billing": "2-5 minutes",
            "technical": "5-10 minutes",
            "support": "3-7 minutes",
            "appointment": "1-3 minutes",
            "sales": "2-5 minutes",
            "general": "5-15 minutes"
        }
        
        return wait_times.get(routing_category, "5-10 minutes")
    
    def _identify_improvement_areas(self, rules: List[CallRouting]) -> List[str]:
        """Identify areas for routing improvement"""
        
        improvements = []
        
        # Check for missing categories
        covered_categories = set(rule.category for rule in rules if rule.is_active)
        all_categories = set(CallRoutingType)
        missing_categories = all_categories - covered_categories
        
        if missing_categories:
            improvements.append(f"Add rules for missing categories: {[c.value for c in missing_categories]}")
        
        # Check for low-performing categories
        category_performance = {}
        for rule in rules:
            if rule.success_rate > 0:
                category = rule.category.value
                if category not in category_performance:
                    category_performance[category] = []
                category_performance[category].append(rule.success_rate)
        
        for category, rates in category_performance.items():
            avg_rate = sum(rates) / len(rates)
            if avg_rate < 0.6:
                improvements.append(f"Improve {category} routing performance (current: {avg_rate:.1%})")
        
        # Check for keyword overlap
        all_keywords = []
        for rule in rules:
            all_keywords.extend(rule.keywords)
        
        if len(all_keywords) != len(set(all_keywords)):
            improvements.append("Review keyword overlap between rules")
        
        return improvements or ["Routing configuration appears optimal"]
    
    def _get_top_performing_rules(self, rules: List[CallRouting]) -> List[Dict[str, Any]]:
        """Get top performing routing rules"""
        
        performing_rules = [r for r in rules if r.success_rate > 0]
        sorted_rules = sorted(performing_rules, key=lambda x: x.success_rate, reverse=True)
        
        return [
            {
                "rule_name": rule.routing_rule,
                "category": rule.category.value,
                "success_rate": rule.success_rate,
                "destination": rule.destination
            }
            for rule in sorted_rules[:5]
        ]
    
    def _calculate_routing_effectiveness(self, rules: List[CallRouting]) -> float:
        """Calculate overall routing effectiveness"""
        
        if not rules:
            return 0.0
        
        # Weight by priority and activity
        weighted_sum = 0
        total_weight = 0
        
        for rule in rules:
            if rule.is_active and rule.success_rate > 0:
                weight = rule.priority
                weighted_sum += rule.success_rate * weight
                total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0