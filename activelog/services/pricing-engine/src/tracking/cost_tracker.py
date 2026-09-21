from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import Dict, List, Optional, Any, Tuple
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import json

from ..database import (
    ComputeCost, User, PricingConfig, ResourceType, 
    ComputeLocation, PricingTier, MembershipAllowance
)

logger = logging.getLogger(__name__)

class ComputeCostTracker:
    """Track compute costs per user with detailed analytics"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def track_compute_usage(
        self,
        user_id: uuid.UUID,
        resource_type: ResourceType,
        location: ComputeLocation,
        units_consumed: Decimal,
        session_id: Optional[str] = None,
        job_metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Track compute usage and calculate real-time costs"""
        
        try:
            # Get user's current tier
            user_tier = await self._get_user_tier(user_id)
            
            # Calculate costs using the pricing engine
            from ..cost_calculator.engine import CostPlusCalculator
            calculator = CostPlusCalculator(self.db)
            
            cost_calculation = await calculator.calculate_price(
                resource_type=resource_type,
                units=units_consumed,
                user_id=user_id,
                location=location,
                tier=user_tier
            )
            
            # Record the cost in database
            cost_record = await calculator.record_cost_calculation(
                user_id=user_id,
                resource_type=resource_type,
                location=location,
                units_consumed=units_consumed,
                calculation_result=cost_calculation,
                session_id=session_id
            )
            
            # Update user's usage statistics
            await self._update_usage_statistics(user_id, cost_calculation)
            
            # Check membership allowance
            allowance_status = await self._check_membership_allowance(
                user_id, Decimal(str(cost_calculation['breakdown']['final_price']))
            )
            
            # Generate usage insights
            insights = await self._generate_usage_insights(user_id)
            
            return {
                "tracking_id": str(cost_record.id),
                "cost_breakdown": cost_calculation['breakdown'],
                "allowance_status": allowance_status,
                "usage_insights": insights,
                "recommendations": await self._generate_cost_recommendations(user_id, cost_calculation),
                "tracked_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to track compute usage: {e}")
            raise
    
    async def get_user_cost_summary(
        self,
        user_id: uuid.UUID,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """Get comprehensive cost summary for a user"""
        
        try:
            start_date = datetime.utcnow() - timedelta(days=period_days)
            
            # Get cost records for the period
            result = await self.db.execute(
                select(ComputeCost).where(
                    and_(
                        ComputeCost.user_id == user_id,
                        ComputeCost.timestamp >= start_date
                    )
                ).order_by(ComputeCost.timestamp.desc())
            )
            cost_records = result.scalars().all()
            
            if not cost_records:
                return {
                    "user_id": str(user_id),
                    "period_days": period_days,
                    "total_cost": 0.0,
                    "total_units": 0.0,
                    "message": "No usage data found for this period"
                }
            
            # Calculate totals and breakdowns
            total_cost = sum(record.final_cost for record in cost_records)
            total_base_cost = sum(record.base_cost for record in cost_records)
            total_units = sum(record.units_consumed for record in cost_records)
            
            # Resource type breakdown
            resource_breakdown = {}
            for record in cost_records:
                rt = record.resource_type.value
                if rt not in resource_breakdown:
                    resource_breakdown[rt] = {
                        "units": Decimal('0'),
                        "cost": Decimal('0'),
                        "sessions": 0
                    }
                resource_breakdown[rt]['units'] += record.units_consumed
                resource_breakdown[rt]['cost'] += record.final_cost
                resource_breakdown[rt]['sessions'] += 1
            
            # Location breakdown
            location_breakdown = {}
            for record in cost_records:
                loc = record.location.value
                if loc not in location_breakdown:
                    location_breakdown[loc] = {
                        "cost": Decimal('0'),
                        "percentage": 0.0
                    }
                location_breakdown[loc]['cost'] += record.final_cost
            
            # Calculate percentages
            for loc_data in location_breakdown.values():
                loc_data['percentage'] = float((loc_data['cost'] / total_cost) * 100) if total_cost > 0 else 0
                loc_data['cost'] = float(loc_data['cost'])
            
            # Peak vs off-peak analysis
            off_peak_records = [r for r in cost_records if r.is_off_peak]
            peak_savings = sum(
                (record.base_cost * (Decimal('1.5') - record.peak_multiplier)) 
                for record in off_peak_records
            )
            
            # Time-based analysis
            daily_costs = {}
            for record in cost_records:
                day = record.timestamp.date().isoformat()
                if day not in daily_costs:
                    daily_costs[day] = Decimal('0')
                daily_costs[day] += record.final_cost
            
            # Convert decimals to floats for JSON serialization
            for rt_data in resource_breakdown.values():
                rt_data['units'] = float(rt_data['units'])
                rt_data['cost'] = float(rt_data['cost'])
            
            return {
                "user_id": str(user_id),
                "period_days": period_days,
                "summary": {
                    "total_cost": float(total_cost),
                    "total_base_cost": float(total_base_cost),
                    "total_units": float(total_units),
                    "total_sessions": len(cost_records),
                    "average_daily_cost": float(total_cost / period_days),
                    "peak_savings_earned": float(peak_savings)
                },
                "breakdowns": {
                    "by_resource_type": resource_breakdown,
                    "by_location": location_breakdown,
                    "daily_costs": {day: float(cost) for day, cost in daily_costs.items()}
                },
                "peak_analysis": {
                    "total_off_peak_sessions": len(off_peak_records),
                    "off_peak_percentage": (len(off_peak_records) / len(cost_records)) * 100,
                    "estimated_peak_savings": float(peak_savings)
                },
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get user cost summary: {e}")
            raise
    
    async def get_organization_cost_tracking(
        self,
        organization_id: str,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """Track costs across all users in an organization"""
        
        try:
            # Get all users in the organization
            result = await self.db.execute(
                select(User).where(User.organization_id == organization_id)
            )
            org_users = result.scalars().all()
            
            if not org_users:
                return {
                    "organization_id": organization_id,
                    "message": "No users found for this organization"
                }
            
            start_date = datetime.utcnow() - timedelta(days=period_days)
            user_ids = [user.id for user in org_users]
            
            # Get cost records for all org users
            result = await self.db.execute(
                select(ComputeCost).where(
                    and_(
                        ComputeCost.user_id.in_(user_ids),
                        ComputeCost.timestamp >= start_date
                    )
                ).order_by(ComputeCost.timestamp.desc())
            )
            cost_records = result.scalars().all()
            
            if not cost_records:
                return {
                    "organization_id": organization_id,
                    "total_users": len(org_users),
                    "period_days": period_days,
                    "message": "No usage data found for this period"
                }
            
            # Calculate organization totals
            total_org_cost = sum(record.final_cost for record in cost_records)
            
            # Per-user breakdown
            user_costs = {}
            for record in cost_records:
                user_id_str = str(record.user_id)
                if user_id_str not in user_costs:
                    user_costs[user_id_str] = {
                        "cost": Decimal('0'),
                        "units": Decimal('0'),
                        "sessions": 0
                    }
                user_costs[user_id_str]['cost'] += record.final_cost
                user_costs[user_id_str]['units'] += record.units_consumed
                user_costs[user_id_str]['sessions'] += 1
            
            # Top users by cost
            sorted_users = sorted(
                user_costs.items(),
                key=lambda x: x[1]['cost'],
                reverse=True
            )
            
            # Department/team breakdown (if metadata available)
            team_breakdown = await self._get_team_cost_breakdown(cost_records)
            
            # Convert to serializable format
            for user_data in user_costs.values():
                user_data['cost'] = float(user_data['cost'])
                user_data['units'] = float(user_data['units'])
            
            return {
                "organization_id": organization_id,
                "period_days": period_days,
                "organization_summary": {
                    "total_cost": float(total_org_cost),
                    "total_users": len(org_users),
                    "active_users": len(user_costs),
                    "average_cost_per_user": float(total_org_cost / len(user_costs)) if user_costs else 0,
                    "total_sessions": sum(data['sessions'] for data in user_costs.values())
                },
                "user_breakdown": dict(sorted_users[:10]),  # Top 10 users
                "team_breakdown": team_breakdown,
                "cost_efficiency": await self._calculate_org_efficiency_metrics(cost_records),
                "recommendations": await self._generate_org_recommendations(organization_id, cost_records)
            }
            
        except Exception as e:
            logger.error(f"Failed to get organization cost tracking: {e}")
            raise
    
    async def track_session_costs(
        self,
        session_id: str,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Track all costs for a specific compute session"""
        
        try:
            result = await self.db.execute(
                select(ComputeCost).where(
                    and_(
                        ComputeCost.session_id == session_id,
                        ComputeCost.user_id == user_id
                    )
                ).order_by(ComputeCost.timestamp.asc())
            )
            session_records = result.scalars().all()
            
            if not session_records:
                return {
                    "session_id": session_id,
                    "message": "No cost records found for this session"
                }
            
            # Calculate session totals
            total_session_cost = sum(record.final_cost for record in session_records)
            session_duration = (session_records[-1].timestamp - session_records[0].timestamp).total_seconds()
            
            # Resource usage during session
            resource_usage = {}
            for record in session_records:
                rt = record.resource_type.value
                if rt not in resource_usage:
                    resource_usage[rt] = {
                        "units": Decimal('0'),
                        "cost": Decimal('0')
                    }
                resource_usage[rt]['units'] += record.units_consumed
                resource_usage[rt]['cost'] += record.final_cost
            
            # Convert to serializable format
            for ru_data in resource_usage.values():
                ru_data['units'] = float(ru_data['units'])
                ru_data['cost'] = float(ru_data['cost'])
            
            return {
                "session_id": session_id,
                "user_id": str(user_id),
                "session_summary": {
                    "total_cost": float(total_session_cost),
                    "duration_seconds": session_duration,
                    "cost_per_second": float(total_session_cost / session_duration) if session_duration > 0 else 0,
                    "total_records": len(session_records)
                },
                "resource_usage": resource_usage,
                "timeline": [
                    {
                        "timestamp": record.timestamp.isoformat(),
                        "resource_type": record.resource_type.value,
                        "units": float(record.units_consumed),
                        "cost": float(record.final_cost)
                    }
                    for record in session_records
                ],
                "session_period": {
                    "start": session_records[0].timestamp.isoformat(),
                    "end": session_records[-1].timestamp.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to track session costs: {e}")
            raise
    
    async def get_cost_trends(
        self,
        user_id: uuid.UUID,
        days: int = 90
    ) -> Dict[str, Any]:
        """Analyze cost trends and patterns for a user"""
        
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            result = await self.db.execute(
                select(ComputeCost).where(
                    and_(
                        ComputeCost.user_id == user_id,
                        ComputeCost.timestamp >= start_date
                    )
                ).order_by(ComputeCost.timestamp.asc())
            )
            cost_records = result.scalars().all()
            
            if len(cost_records) < 2:
                return {
                    "user_id": str(user_id),
                    "message": "Insufficient data for trend analysis"
                }
            
            # Weekly cost aggregation
            weekly_costs = {}
            for record in cost_records:
                week_start = record.timestamp - timedelta(days=record.timestamp.weekday())
                week_key = week_start.date().isoformat()
                
                if week_key not in weekly_costs:
                    weekly_costs[week_key] = Decimal('0')
                weekly_costs[week_key] += record.final_cost
            
            # Calculate trend
            weekly_values = list(weekly_costs.values())
            if len(weekly_values) >= 2:
                recent_avg = sum(weekly_values[-4:]) / len(weekly_values[-4:])  # Last 4 weeks
                older_avg = sum(weekly_values[:-4]) / len(weekly_values[:-4]) if len(weekly_values) > 4 else weekly_values[0]
                
                trend_direction = "increasing" if recent_avg > older_avg else "decreasing" if recent_avg < older_avg else "stable"
                trend_percentage = float(((recent_avg - older_avg) / older_avg) * 100) if older_avg > 0 else 0
            else:
                trend_direction = "insufficient_data"
                trend_percentage = 0
            
            # Usage patterns
            hourly_usage = {}
            for record in cost_records:
                hour = record.timestamp.hour
                if hour not in hourly_usage:
                    hourly_usage[hour] = Decimal('0')
                hourly_usage[hour] += record.final_cost
            
            peak_hour = max(hourly_usage.items(), key=lambda x: x[1])[0] if hourly_usage else 0
            
            return {
                "user_id": str(user_id),
                "analysis_period_days": days,
                "trend_analysis": {
                    "direction": trend_direction,
                    "percentage_change": trend_percentage,
                    "recent_4_week_average": float(recent_avg) if 'recent_avg' in locals() else 0,
                    "confidence": "high" if len(weekly_values) >= 8 else "medium" if len(weekly_values) >= 4 else "low"
                },
                "weekly_costs": {week: float(cost) for week, cost in weekly_costs.items()},
                "usage_patterns": {
                    "peak_usage_hour": peak_hour,
                    "hourly_distribution": {str(hour): float(cost) for hour, cost in hourly_usage.items()},
                    "most_active_days": await self._get_most_active_days(cost_records)
                },
                "projections": await self._calculate_cost_projections(weekly_values)
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze cost trends: {e}")
            raise
    
    async def _get_user_tier(self, user_id: uuid.UUID) -> PricingTier:
        """Get user's pricing tier"""
        
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        return user.membership_tier if user else PricingTier.STANDARD
    
    async def _update_usage_statistics(self, user_id: uuid.UUID, cost_calculation: Dict) -> None:
        """Update user's usage statistics (simplified - would be more comprehensive)"""
        
        # In production, this would update user usage statistics tables
        logger.info(f"Updated usage stats for user {user_id}: ${cost_calculation['breakdown']['final_price']}")
    
    async def _check_membership_allowance(
        self, 
        user_id: uuid.UUID, 
        cost: Decimal
    ) -> Dict[str, Any]:
        """Check user's membership allowance status"""
        
        # Get current billing cycle allowance
        result = await self.db.execute(
            select(MembershipAllowance).where(
                and_(
                    MembershipAllowance.user_id == user_id,
                    MembershipAllowance.billing_cycle_start <= datetime.utcnow(),
                    MembershipAllowance.billing_cycle_end >= datetime.utcnow()
                )
            )
        )
        allowance = result.scalar_one_or_none()
        
        if not allowance:
            return {
                "has_allowance": False,
                "message": "No active membership allowance"
            }
        
        remaining_after = allowance.remaining_allowance - cost
        within_allowance = remaining_after >= 0
        
        if within_allowance:
            # Update allowance
            allowance.used_allowance += cost
            allowance.remaining_allowance = remaining_after
            await self.db.commit()
        
        return {
            "has_allowance": True,
            "monthly_allowance": float(allowance.monthly_allowance),
            "used_allowance": float(allowance.used_allowance),
            "remaining_allowance": float(allowance.remaining_allowance),
            "within_allowance": within_allowance,
            "overage_cost": float(max(Decimal('0'), -remaining_after)) if not within_allowance else 0,
            "overage_rate": float(allowance.overage_rate)
        }
    
    async def _generate_usage_insights(self, user_id: uuid.UUID) -> List[str]:
        """Generate usage insights for the user"""
        
        insights = []
        
        # Get recent usage data
        recent_data = await self.get_user_cost_summary(user_id, 7)
        if 'summary' in recent_data:
            daily_avg = recent_data['summary']['average_daily_cost']
            
            if daily_avg > 10:
                insights.append("High daily usage detected - consider optimization strategies")
            elif daily_avg < 1:
                insights.append("Low usage pattern - explore additional compute opportunities")
            
            if recent_data['peak_analysis']['off_peak_percentage'] < 30:
                insights.append("Consider scheduling more jobs during off-peak hours for savings")
        
        return insights
    
    async def _generate_cost_recommendations(
        self, 
        user_id: uuid.UUID, 
        cost_calculation: Dict
    ) -> List[str]:
        """Generate cost optimization recommendations"""
        
        recommendations = []
        
        # Check if user could benefit from different tier
        if cost_calculation['breakdown']['final_price'] > 50:
            recommendations.append("Consider upgrading to premium tier for better rates")
        
        # Check peak pricing
        if cost_calculation['breakdown']['is_peak_time']:
            recommendations.append("Schedule non-urgent jobs during off-peak hours for discounts")
        
        # Location optimization
        if cost_calculation['location'] == 'cloud':
            recommendations.append("Evaluate local compute options for cost savings")
        
        return recommendations
    
    async def _get_team_cost_breakdown(self, cost_records: List[ComputeCost]) -> Dict[str, Any]:
        """Get team/department cost breakdown from metadata"""
        
        team_costs = {}
        
        for record in cost_records:
            team = "unknown"
            if record.metadata and 'team' in record.metadata:
                team = record.metadata['team']
            
            if team not in team_costs:
                team_costs[team] = Decimal('0')
            team_costs[team] += record.final_cost
        
        return {team: float(cost) for team, cost in team_costs.items()}
    
    async def _calculate_org_efficiency_metrics(self, cost_records: List[ComputeCost]) -> Dict[str, Any]:
        """Calculate efficiency metrics for organization"""
        
        total_cost = sum(record.final_cost for record in cost_records)
        total_units = sum(record.units_consumed for record in cost_records)
        
        off_peak_usage = len([r for r in cost_records if r.is_off_peak])
        efficiency_score = (off_peak_usage / len(cost_records)) * 100 if cost_records else 0
        
        return {
            "cost_per_unit": float(total_cost / total_units) if total_units > 0 else 0,
            "off_peak_usage_percentage": efficiency_score,
            "efficiency_rating": "high" if efficiency_score > 60 else "medium" if efficiency_score > 30 else "low"
        }
    
    async def _generate_org_recommendations(
        self, 
        org_id: str, 
        cost_records: List[ComputeCost]
    ) -> List[str]:
        """Generate recommendations for organization"""
        
        recommendations = []
        total_cost = sum(record.final_cost for record in cost_records)
        
        if total_cost > 1000:
            recommendations.append("Consider bulk billing setup for volume discounts")
        
        off_peak_percentage = len([r for r in cost_records if r.is_off_peak]) / len(cost_records) * 100
        if off_peak_percentage < 40:
            recommendations.append("Implement policies to encourage off-peak usage")
        
        return recommendations
    
    async def _get_most_active_days(self, cost_records: List[ComputeCost]) -> List[str]:
        """Get most active days of week"""
        
        day_usage = {}
        for record in cost_records:
            day = record.timestamp.strftime('%A')
            if day not in day_usage:
                day_usage[day] = Decimal('0')
            day_usage[day] += record.final_cost
        
        sorted_days = sorted(day_usage.items(), key=lambda x: x[1], reverse=True)
        return [day for day, _ in sorted_days[:3]]
    
    async def _calculate_cost_projections(self, weekly_values: List[Decimal]) -> Dict[str, Any]:
        """Calculate cost projections based on trends"""
        
        if len(weekly_values) < 4:
            return {"projection_available": False, "reason": "insufficient_data"}
        
        # Simple linear trend projection
        recent_trend = (weekly_values[-1] - weekly_values[-4]) / 4
        
        next_month_projection = weekly_values[-1] + (recent_trend * 4)
        next_quarter_projection = weekly_values[-1] + (recent_trend * 12)
        
        return {
            "projection_available": True,
            "next_month": float(max(Decimal('0'), next_month_projection)),
            "next_quarter": float(max(Decimal('0'), next_quarter_projection)),
            "confidence": "medium",
            "trend": "increasing" if recent_trend > 0 else "decreasing"
        }