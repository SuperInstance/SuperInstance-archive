from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from ..database import (
    PricingConfig, ComputeCost, User, ResourceType, 
    PricingTier, ComputeLocation, InflationAdjustment
)

logger = logging.getLogger(__name__)

class CostPlusCalculator:
    """Cost-plus pricing calculator with $2 markup and inflation adjustments"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.default_markup = Decimal('2.0')  # $2 default markup
    
    async def calculate_price(
        self,
        resource_type: ResourceType,
        units: Decimal,
        user_id: Optional[uuid.UUID] = None,
        location: ComputeLocation = ComputeLocation.CLOUD,
        tier: Optional[PricingTier] = None,
        include_peak_pricing: bool = True
    ) -> Dict[str, Any]:
        """Calculate final price using cost-plus methodology"""
        
        try:
            # Get user's tier if not provided
            if not tier and user_id:
                tier = await self._get_user_tier(user_id)
            elif not tier:
                tier = PricingTier.STANDARD
            
            # Get base cost configuration
            base_config = await self._get_pricing_config(resource_type, tier)
            if not base_config:
                raise ValueError(f"No pricing config found for {resource_type} in {tier} tier")
            
            # Apply inflation adjustment
            inflation_adjusted_cost = await self._apply_inflation_adjustment(
                base_config.base_cost, base_config.created_at
            )
            
            # Calculate base cost for units
            total_base_cost = inflation_adjusted_cost * units
            
            # Add markup (default $2 or configured amount)
            markup_amount = base_config.markup_amount or self.default_markup
            total_markup = markup_amount * units
            
            # Calculate subtotal
            subtotal = total_base_cost + total_markup
            
            # Apply peak pricing if enabled
            peak_multiplier = Decimal('1.0')
            is_peak = False
            if include_peak_pricing:
                peak_data = await self._get_peak_pricing_multiplier(datetime.utcnow())
                peak_multiplier = peak_data['multiplier']
                is_peak = peak_data['is_peak']
            
            # Calculate final price
            final_price = subtotal * peak_multiplier
            
            # Calculate savings for off-peak
            peak_savings = Decimal('0')
            if not is_peak and peak_multiplier < 1:
                peak_savings = subtotal - final_price
            
            calculation_result = {
                "resource_type": resource_type.value,
                "units": float(units),
                "tier": tier.value,
                "location": location.value,
                "breakdown": {
                    "base_cost_per_unit": float(base_config.base_cost),
                    "inflation_adjusted_cost_per_unit": float(inflation_adjusted_cost),
                    "markup_per_unit": float(markup_amount),
                    "total_base_cost": float(total_base_cost),
                    "total_markup": float(total_markup),
                    "subtotal": float(subtotal),
                    "peak_multiplier": float(peak_multiplier),
                    "is_peak_time": is_peak,
                    "peak_savings": float(peak_savings),
                    "final_price": float(final_price)
                },
                "metadata": {
                    "config_id": str(base_config.id),
                    "calculation_timestamp": datetime.utcnow().isoformat(),
                    "inflation_rate_applied": await self._get_current_inflation_rate()
                }
            }
            
            return calculation_result
            
        except Exception as e:
            logger.error(f"Error calculating price: {e}")
            raise
    
    async def calculate_bulk_pricing(
        self,
        resource_requests: List[Dict[str, Any]],
        user_id: Optional[uuid.UUID] = None,
        apply_bulk_discount: bool = True
    ) -> Dict[str, Any]:
        """Calculate pricing for multiple resources with bulk discounts"""
        
        individual_calculations = []
        total_cost = Decimal('0')
        total_base_cost = Decimal('0')
        total_markup = Decimal('0')
        
        # Calculate each resource individually
        for request in resource_requests:
            calc = await self.calculate_price(
                resource_type=ResourceType(request['resource_type']),
                units=Decimal(str(request['units'])),
                user_id=user_id,
                location=ComputeLocation(request.get('location', 'cloud')),
                tier=PricingTier(request.get('tier')) if request.get('tier') else None,
                include_peak_pricing=request.get('include_peak_pricing', True)
            )
            
            individual_calculations.append(calc)
            total_cost += Decimal(str(calc['breakdown']['final_price']))
            total_base_cost += Decimal(str(calc['breakdown']['total_base_cost']))
            total_markup += Decimal(str(calc['breakdown']['total_markup']))
        
        # Apply bulk discount if enabled
        bulk_discount = Decimal('0')
        bulk_discount_rate = Decimal('0')
        
        if apply_bulk_discount and len(resource_requests) > 1:
            bulk_discount_rate = self._calculate_bulk_discount_rate(total_cost)
            bulk_discount = total_cost * bulk_discount_rate
        
        final_total = total_cost - bulk_discount
        
        return {
            "bulk_calculation": {
                "total_resources": len(resource_requests),
                "total_base_cost": float(total_base_cost),
                "total_markup": float(total_markup),
                "subtotal": float(total_cost),
                "bulk_discount_rate": float(bulk_discount_rate),
                "bulk_discount_amount": float(bulk_discount),
                "final_total": float(final_total),
                "average_markup_percentage": float((total_markup / total_base_cost) * 100) if total_base_cost > 0 else 0
            },
            "individual_calculations": individual_calculations,
            "calculation_metadata": {
                "bulk_discount_applied": bulk_discount > 0,
                "calculation_timestamp": datetime.utcnow().isoformat()
            }
        }
    
    async def record_cost_calculation(
        self,
        user_id: uuid.UUID,
        resource_type: ResourceType,
        location: ComputeLocation,
        units_consumed: Decimal,
        calculation_result: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> ComputeCost:
        """Record a cost calculation in the database"""
        
        user_tier = await self._get_user_tier(user_id)
        
        cost_record = ComputeCost(
            user_id=user_id,
            resource_type=resource_type,
            location=location,
            units_consumed=units_consumed,
            base_cost=Decimal(str(calculation_result['breakdown']['total_base_cost'])),
            final_cost=Decimal(str(calculation_result['breakdown']['final_price'])),
            pricing_tier=user_tier,
            is_off_peak=not calculation_result['breakdown']['is_peak_time'],
            peak_multiplier=Decimal(str(calculation_result['breakdown']['peak_multiplier'])),
            session_id=session_id,
            metadata=calculation_result.get('metadata', {})
        )
        
        self.db.add(cost_record)
        await self.db.commit()
        await self.db.refresh(cost_record)
        
        return cost_record
    
    async def get_pricing_breakdown_by_tier(
        self,
        resource_type: ResourceType,
        units: Decimal = Decimal('1')
    ) -> Dict[str, Any]:
        """Get pricing breakdown across all tiers for comparison"""
        
        tier_comparisons = {}
        
        for tier in PricingTier:
            try:
                calc = await self.calculate_price(
                    resource_type=resource_type,
                    units=units,
                    tier=tier,
                    include_peak_pricing=False  # For base comparison
                )
                tier_comparisons[tier.value] = calc
            except ValueError:
                # Skip tiers without pricing configs
                continue
        
        return {
            "resource_type": resource_type.value,
            "units": float(units),
            "tier_comparisons": tier_comparisons,
            "comparison_timestamp": datetime.utcnow().isoformat()
        }
    
    async def update_pricing_config(
        self,
        config_name: str,
        base_cost: Optional[Decimal] = None,
        markup_amount: Optional[Decimal] = None,
        tier: Optional[PricingTier] = None,
        resource_type: Optional[ResourceType] = None
    ) -> PricingConfig:
        """Update or create pricing configuration"""
        
        # Try to find existing config
        result = await self.db.execute(
            select(PricingConfig).where(PricingConfig.config_name == config_name)
        )
        config = result.scalar_one_or_none()
        
        if config:
            # Update existing
            if base_cost is not None:
                config.base_cost = base_cost
            if markup_amount is not None:
                config.markup_amount = markup_amount
            if tier is not None:
                config.tier = tier
            if resource_type is not None:
                config.resource_type = resource_type
        else:
            # Create new
            if not all([base_cost, tier, resource_type]):
                raise ValueError("base_cost, tier, and resource_type required for new config")
            
            config = PricingConfig(
                config_name=config_name,
                base_cost=base_cost,
                markup_amount=markup_amount or self.default_markup,
                tier=tier,
                resource_type=resource_type
            )
            self.db.add(config)
        
        await self.db.commit()
        await self.db.refresh(config)
        
        return config
    
    async def _get_pricing_config(
        self, 
        resource_type: ResourceType, 
        tier: PricingTier
    ) -> Optional[PricingConfig]:
        """Get pricing configuration for resource and tier"""
        
        result = await self.db.execute(
            select(PricingConfig).where(
                and_(
                    PricingConfig.resource_type == resource_type,
                    PricingConfig.tier == tier,
                    PricingConfig.effective_from <= datetime.utcnow(),
                    PricingConfig.effective_to.is_(None) | (PricingConfig.effective_to > datetime.utcnow())
                )
            ).order_by(PricingConfig.effective_from.desc())
        )
        
        return result.scalar_one_or_none()
    
    async def _get_user_tier(self, user_id: uuid.UUID) -> PricingTier:
        """Get user's pricing tier"""
        
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        return user.membership_tier if user else PricingTier.STANDARD
    
    async def _apply_inflation_adjustment(
        self, 
        base_cost: Decimal, 
        config_created_date: datetime
    ) -> Decimal:
        """Apply inflation adjustment to base cost"""
        
        # Get the most recent inflation adjustment
        result = await self.db.execute(
            select(InflationAdjustment).order_by(InflationAdjustment.adjustment_date.desc())
        )
        inflation_adj = result.scalar_one_or_none()
        
        if not inflation_adj:
            return base_cost
        
        # Calculate months since config creation
        months_elapsed = (datetime.utcnow() - config_created_date).days / 30.0
        
        # Apply compound inflation
        inflation_factor = (1 + inflation_adj.adjustment_factor) ** (months_elapsed / 12.0)
        
        return base_cost * Decimal(str(inflation_factor))
    
    async def _get_current_inflation_rate(self) -> float:
        """Get current inflation rate"""
        
        result = await self.db.execute(
            select(InflationAdjustment).order_by(InflationAdjustment.adjustment_date.desc())
        )
        inflation_adj = result.scalar_one_or_none()
        
        return float(inflation_adj.inflation_rate) if inflation_adj else 0.03  # 3% default
    
    async def _get_peak_pricing_multiplier(self, timestamp: datetime) -> Dict[str, Any]:
        """Get peak pricing multiplier for given timestamp"""
        
        # Import here to avoid circular imports
        from ..peak_pricing.scheduler import PeakPricingScheduler
        
        scheduler = PeakPricingScheduler(self.db)
        return await scheduler.get_pricing_multiplier(timestamp)
    
    def _calculate_bulk_discount_rate(self, total_cost: Decimal) -> Decimal:
        """Calculate bulk discount rate based on total cost"""
        
        if total_cost >= 1000:  # $1000+
            return Decimal('0.15')  # 15% discount
        elif total_cost >= 500:  # $500+
            return Decimal('0.10')  # 10% discount
        elif total_cost >= 200:  # $200+
            return Decimal('0.05')  # 5% discount
        else:
            return Decimal('0')     # No discount