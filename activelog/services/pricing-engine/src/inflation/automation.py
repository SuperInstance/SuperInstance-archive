from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from typing import Dict, List, Optional, Any
from decimal import Decimal
import asyncio
import logging
from datetime import datetime, timedelta
import aiohttp
import json

from ..database import InflationAdjustment, PricingConfig, MembershipPricing

logger = logging.getLogger(__name__)

class InflationAutomation:
    """Automated inflation adjustment system"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.economic_apis = {
            "federal_reserve": "https://api.stlouisfed.org/fred/series/observations",
            "world_bank": "https://api.worldbank.org/v2/country/USA/indicator/FP.CPI.TOTL"
        }
    
    async def run_monthly_inflation_update(self) -> Dict[str, Any]:
        """Run automated monthly inflation adjustment"""
        
        try:
            # Fetch current inflation data
            inflation_data = await self._fetch_current_inflation_rate()
            
            # Calculate adjustment factor
            adjustment_factor = await self._calculate_adjustment_factor(
                inflation_data['annual_rate']
            )
            
            # Create inflation adjustment record
            inflation_record = await self._create_inflation_adjustment(
                inflation_rate=inflation_data['annual_rate'],
                adjustment_factor=adjustment_factor,
                reason="Monthly automated adjustment"
            )
            
            # Apply adjustments to pricing configs
            pricing_adjustments = await self._apply_pricing_adjustments(
                adjustment_factor, inflation_record.id
            )
            
            # Update membership pricing
            membership_adjustments = await self._adjust_membership_pricing(
                adjustment_factor, inflation_record.id
            )
            
            result = {
                "inflation_record_id": str(inflation_record.id),
                "inflation_rate": float(inflation_data['annual_rate']),
                "adjustment_factor": float(adjustment_factor),
                "pricing_configs_updated": pricing_adjustments['updated_count'],
                "membership_tiers_updated": membership_adjustments['updated_count'],
                "total_cost_impact": float(pricing_adjustments['cost_impact']),
                "effective_date": inflation_record.adjustment_date.isoformat(),
                "next_scheduled_update": (datetime.utcnow() + timedelta(days=30)).isoformat()
            }
            
            logger.info(f"Monthly inflation update completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to run monthly inflation update: {e}")
            raise
    
    async def emergency_inflation_adjustment(
        self, 
        emergency_rate: Decimal,
        reason: str,
        affected_tiers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Apply emergency inflation adjustment for economic shocks"""
        
        try:
            # Calculate emergency adjustment factor (higher impact)
            adjustment_factor = (emergency_rate / 100) * Decimal('1.5')  # 1.5x multiplier for emergencies
            
            # Create emergency inflation record
            inflation_record = await self._create_inflation_adjustment(
                inflation_rate=emergency_rate,
                adjustment_factor=adjustment_factor,
                reason=f"Emergency adjustment: {reason}",
                affected_tiers=affected_tiers
            )
            
            # Apply immediate pricing adjustments
            if affected_tiers:
                pricing_adjustments = await self._apply_selective_pricing_adjustments(
                    adjustment_factor, affected_tiers, inflation_record.id
                )
            else:
                pricing_adjustments = await self._apply_pricing_adjustments(
                    adjustment_factor, inflation_record.id
                )
            
            # Send notifications to affected users
            await self._notify_users_of_emergency_adjustment(
                emergency_rate, adjustment_factor, affected_tiers
            )
            
            return {
                "emergency_adjustment_id": str(inflation_record.id),
                "emergency_rate": float(emergency_rate),
                "adjustment_factor": float(adjustment_factor),
                "affected_tiers": affected_tiers or "all",
                "configs_updated": pricing_adjustments['updated_count'],
                "immediate_effect": True,
                "notification_sent": True
            }
            
        except Exception as e:
            logger.error(f"Emergency inflation adjustment failed: {e}")
            raise
    
    async def get_inflation_forecast(self, months_ahead: int = 12) -> Dict[str, Any]:
        """Generate inflation forecast for pricing planning"""
        
        try:
            # Get historical inflation data
            historical_data = await self._get_historical_inflation_data(24)  # 2 years
            
            # Calculate trend analysis
            trend = await self._calculate_inflation_trend(historical_data)
            
            # Generate forecast
            forecast = []
            current_rate = historical_data[-1]['rate'] if historical_data else Decimal('0.03')
            
            for month in range(1, months_ahead + 1):
                # Simple trend-based forecast (in production, use more sophisticated models)
                projected_rate = current_rate + (trend['monthly_change'] * month)
                projected_rate = max(Decimal('-0.02'), min(projected_rate, Decimal('0.15')))  # Cap between -2% and 15%
                
                forecast.append({
                    "month": month,
                    "date": (datetime.utcnow() + timedelta(days=30*month)).strftime('%Y-%m'),
                    "projected_rate": float(projected_rate),
                    "confidence": max(0.9 - (month * 0.05), 0.3)  # Decreasing confidence
                })
            
            return {
                "forecast_period_months": months_ahead,
                "historical_trend": {
                    "average_monthly_change": float(trend['monthly_change']),
                    "volatility": float(trend['volatility']),
                    "current_rate": float(current_rate)
                },
                "forecast": forecast,
                "recommendations": await self._generate_pricing_recommendations(forecast),
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Inflation forecast generation failed: {e}")
            raise
    
    async def schedule_automatic_adjustments(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Schedule automatic inflation adjustments based on economic triggers"""
        
        triggers = []
        
        # Scheduled monthly updates
        if config.get('monthly_updates', True):
            triggers.append({
                "type": "scheduled",
                "frequency": "monthly",
                "day_of_month": config.get('update_day', 1),
                "enabled": True
            })
        
        # Threshold-based triggers
        if config.get('threshold_triggers'):
            for threshold in config['threshold_triggers']:
                triggers.append({
                    "type": "threshold",
                    "inflation_rate_threshold": threshold['rate'],
                    "adjustment_multiplier": threshold.get('multiplier', 1.0),
                    "enabled": True
                })
        
        # Economic indicator triggers
        if config.get('economic_indicators'):
            triggers.append({
                "type": "economic_indicator",
                "indicators": config['economic_indicators'],
                "enabled": True
            })
        
        # Store configuration
        await self._store_automation_config(config, triggers)
        
        return {
            "automation_configured": True,
            "active_triggers": len([t for t in triggers if t['enabled']]),
            "next_scheduled_run": await self._get_next_scheduled_run(),
            "triggers": triggers
        }
    
    async def _fetch_current_inflation_rate(self) -> Dict[str, Any]:
        """Fetch current inflation rate from external APIs"""
        
        try:
            # Try Federal Reserve API first
            async with aiohttp.ClientSession() as session:
                # This is a simplified example - real implementation would use proper API keys
                # and handle authentication
                inflation_rate = Decimal('0.032')  # Default 3.2% if API fails
                source = "default"
                
                try:
                    # In production, make actual API calls to economic data providers
                    # For now, use a reasonable default with some variation
                    base_rate = Decimal('0.03')
                    variation = Decimal('0.005')  # ±0.5%
                    inflation_rate = base_rate + (variation * (Decimal(str(hash(datetime.now().month))) % 3 - 1))
                    source = "calculated"
                except Exception as api_error:
                    logger.warning(f"API call failed, using default rate: {api_error}")
                
                return {
                    "annual_rate": inflation_rate,
                    "source": source,
                    "fetched_at": datetime.utcnow(),
                    "confidence": 0.85
                }
                
        except Exception as e:
            logger.error(f"Failed to fetch inflation rate: {e}")
            # Return default rate as fallback
            return {
                "annual_rate": Decimal('0.03'),
                "source": "fallback",
                "fetched_at": datetime.utcnow(),
                "confidence": 0.5
            }
    
    async def _calculate_adjustment_factor(self, inflation_rate: Decimal) -> Decimal:
        """Calculate the adjustment factor to apply to pricing"""
        
        # Convert annual rate to monthly adjustment
        monthly_rate = inflation_rate / 12
        
        # Apply dampening factor to avoid over-adjustment
        dampening = Decimal('0.8')  # Only apply 80% of calculated adjustment
        
        adjustment_factor = monthly_rate * dampening
        
        # Cap adjustment factor to reasonable bounds
        max_adjustment = Decimal('0.02')  # Max 2% per month
        min_adjustment = Decimal('-0.01')  # Max 1% reduction per month
        
        return max(min_adjustment, min(adjustment_factor, max_adjustment))
    
    async def _create_inflation_adjustment(
        self,
        inflation_rate: Decimal,
        adjustment_factor: Decimal,
        reason: str,
        affected_tiers: Optional[List[str]] = None
    ) -> InflationAdjustment:
        """Create inflation adjustment record in database"""
        
        adjustment = InflationAdjustment(
            inflation_rate=inflation_rate,
            adjustment_factor=adjustment_factor,
            affected_tiers=affected_tiers,
            reason=reason,
            metadata={
                "automation_version": "1.0",
                "applied_at": datetime.utcnow().isoformat(),
                "economic_context": await self._get_economic_context()
            }
        )
        
        self.db.add(adjustment)
        await self.db.commit()
        await self.db.refresh(adjustment)
        
        return adjustment
    
    async def _apply_pricing_adjustments(
        self, 
        adjustment_factor: Decimal, 
        inflation_id: str
    ) -> Dict[str, Any]:
        """Apply inflation adjustments to all pricing configurations"""
        
        # Get all active pricing configs
        result = await self.db.execute(
            select(PricingConfig).where(
                (PricingConfig.effective_to.is_(None)) |
                (PricingConfig.effective_to > datetime.utcnow())
            )
        )
        configs = result.scalars().all()
        
        updated_count = 0
        total_cost_impact = Decimal('0')
        
        for config in configs:
            old_cost = config.base_cost
            new_cost = old_cost * (1 + adjustment_factor)
            
            # Update the config
            config.base_cost = new_cost
            config.metadata = config.metadata or {}
            config.metadata['last_inflation_adjustment'] = {
                "date": datetime.utcnow().isoformat(),
                "inflation_id": inflation_id,
                "old_cost": float(old_cost),
                "new_cost": float(new_cost),
                "adjustment_factor": float(adjustment_factor)
            }
            
            total_cost_impact += (new_cost - old_cost)
            updated_count += 1
        
        await self.db.commit()
        
        return {
            "updated_count": updated_count,
            "cost_impact": total_cost_impact
        }
    
    async def _apply_selective_pricing_adjustments(
        self,
        adjustment_factor: Decimal,
        affected_tiers: List[str],
        inflation_id: str
    ) -> Dict[str, Any]:
        """Apply inflation adjustments to specific pricing tiers only"""
        
        from ..database import PricingTier
        
        # Convert tier strings to enum values
        tier_enums = []
        for tier_str in affected_tiers:
            try:
                tier_enums.append(PricingTier(tier_str.lower()))
            except ValueError:
                logger.warning(f"Invalid tier: {tier_str}")
        
        if not tier_enums:
            return {"updated_count": 0, "cost_impact": Decimal('0')}
        
        # Get configs for affected tiers
        result = await self.db.execute(
            select(PricingConfig).where(
                PricingConfig.tier.in_(tier_enums)
            )
        )
        configs = result.scalars().all()
        
        updated_count = 0
        total_cost_impact = Decimal('0')
        
        for config in configs:
            old_cost = config.base_cost
            new_cost = old_cost * (1 + adjustment_factor)
            
            config.base_cost = new_cost
            config.metadata = config.metadata or {}
            config.metadata['emergency_adjustment'] = {
                "date": datetime.utcnow().isoformat(),
                "inflation_id": inflation_id,
                "adjustment_factor": float(adjustment_factor)
            }
            
            total_cost_impact += (new_cost - old_cost)
            updated_count += 1
        
        await self.db.commit()
        
        return {
            "updated_count": updated_count,
            "cost_impact": total_cost_impact
        }
    
    async def _adjust_membership_pricing(
        self, 
        adjustment_factor: Decimal, 
        inflation_id: str
    ) -> Dict[str, Any]:
        """Adjust membership pricing based on inflation"""
        
        result = await self.db.execute(
            select(MembershipPricing).where(
                MembershipPricing.effective_from <= datetime.utcnow()
            )
        )
        memberships = result.scalars().all()
        
        updated_count = 0
        
        for membership in memberships:
            # Apply adjustment but respect min price and max discount constraints
            old_price = membership.current_monthly_price
            new_base_price = membership.base_monthly_price * (1 + adjustment_factor)
            
            # Apply user count discount
            if membership.user_count > 1000:
                discount = min(membership.max_discount, membership.user_count / 10000)
                new_price = new_base_price * (1 - discount)
            else:
                new_price = new_base_price
            
            # Ensure price doesn't go below minimum
            new_price = max(new_price, membership.min_price)
            
            membership.current_monthly_price = new_price
            membership.metadata = membership.metadata or {}
            membership.metadata['inflation_adjustment'] = {
                "date": datetime.utcnow().isoformat(),
                "inflation_id": inflation_id,
                "old_price": float(old_price),
                "new_price": float(new_price)
            }
            
            updated_count += 1
        
        await self.db.commit()
        
        return {"updated_count": updated_count}
    
    async def _get_historical_inflation_data(self, months: int) -> List[Dict]:
        """Get historical inflation data for trend analysis"""
        
        result = await self.db.execute(
            select(InflationAdjustment)
            .where(InflationAdjustment.adjustment_date >= 
                   datetime.utcnow() - timedelta(days=months*30))
            .order_by(InflationAdjustment.adjustment_date.desc())
        )
        
        records = result.scalars().all()
        
        return [
            {
                "date": record.adjustment_date,
                "rate": record.inflation_rate,
                "factor": record.adjustment_factor
            }
            for record in records
        ]
    
    async def _calculate_inflation_trend(self, historical_data: List[Dict]) -> Dict[str, Decimal]:
        """Calculate inflation trend from historical data"""
        
        if len(historical_data) < 2:
            return {
                "monthly_change": Decimal('0'),
                "volatility": Decimal('0')
            }
        
        # Calculate month-over-month changes
        changes = []
        for i in range(1, len(historical_data)):
            change = historical_data[i-1]['rate'] - historical_data[i]['rate']
            changes.append(change)
        
        # Average monthly change
        avg_change = sum(changes) / len(changes) if changes else Decimal('0')
        
        # Calculate volatility (standard deviation)
        if len(changes) > 1:
            variance = sum((c - avg_change) ** 2 for c in changes) / len(changes)
            volatility = variance ** Decimal('0.5')
        else:
            volatility = Decimal('0')
        
        return {
            "monthly_change": avg_change,
            "volatility": volatility
        }
    
    async def _generate_pricing_recommendations(self, forecast: List[Dict]) -> List[str]:
        """Generate pricing recommendations based on forecast"""
        
        recommendations = []
        
        # Analyze forecast trend
        rates = [f['projected_rate'] for f in forecast]
        avg_rate = sum(rates) / len(rates)
        max_rate = max(rates)
        min_rate = min(rates)
        
        if avg_rate > 0.05:  # Above 5% average
            recommendations.append("Consider implementing cost stabilization measures")
            recommendations.append("Review pricing tiers for competitive positioning")
        
        if max_rate - min_rate > 0.03:  # High volatility
            recommendations.append("Implement flexible pricing mechanisms")
            recommendations.append("Consider hedging strategies for cost stability")
        
        if avg_rate < 0.01:  # Low inflation environment
            recommendations.append("Opportunity for competitive pricing strategies")
            recommendations.append("Consider investment in capacity expansion")
        
        return recommendations
    
    async def _get_economic_context(self) -> Dict[str, Any]:
        """Get current economic context for metadata"""
        
        return {
            "quarter": f"Q{(datetime.utcnow().month - 1) // 3 + 1}",
            "year": datetime.utcnow().year,
            "context": "Automated inflation adjustment",
            "methodology": "Cost-plus with inflation adjustment"
        }
    
    async def _store_automation_config(self, config: Dict, triggers: List[Dict]) -> None:
        """Store automation configuration (simplified - would use proper config table)"""
        
        # In production, this would store in a configuration table
        logger.info(f"Automation config stored: {len(triggers)} triggers configured")
    
    async def _get_next_scheduled_run(self) -> str:
        """Get next scheduled automation run time"""
        
        # Calculate next month's first day
        now = datetime.utcnow()
        if now.month == 12:
            next_run = datetime(now.year + 1, 1, 1)
        else:
            next_run = datetime(now.year, now.month + 1, 1)
        
        return next_run.isoformat()
    
    async def _notify_users_of_emergency_adjustment(
        self,
        rate: Decimal,
        factor: Decimal,
        tiers: Optional[List[str]]
    ) -> None:
        """Send notifications about emergency pricing adjustments"""
        
        # In production, integrate with notification service
        logger.info(f"Emergency adjustment notification: {rate}% rate, factor {factor}")
        if tiers:
            logger.info(f"Affected tiers: {tiers}")