"""
Transparent Cost-Plus Pricing Calculator
Shows exact costs and 15% markup breakdown
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session

from ...models.database import User, PricingCalculation
from ...config.settings import settings, PRICING_COMPONENTS, COST_PLUS_MARKUP

logger = logging.getLogger(__name__)

class CostPlusCalculator:
    """Transparent cost-plus pricing calculator with detailed breakdowns"""
    
    def __init__(self, db: Session):
        self.db = db
        self.markup_rate = COST_PLUS_MARKUP
        self.pricing_components = PRICING_COMPONENTS
        
    def calculate_storage_costs(
        self,
        storage_gb: Decimal,
        billing_days: int = 30
    ) -> Dict[str, Decimal]:
        """Calculate storage costs with transparent breakdown"""
        
        # Get actual costs (simulated AWS S3 pricing)
        actual_cost_per_gb_per_month = Decimal("0.023")  # $0.023/GB/month S3 Standard
        
        # Calculate base costs
        base_cost_usd = storage_gb * actual_cost_per_gb_per_month * (billing_days / 30)
        
        # Apply markup
        markup_amount_usd = base_cost_usd * self.markup_rate
        total_cost_usd = base_cost_usd + markup_amount_usd
        
        # Convert to CC (1 CC = $0.01)
        base_cost_cc = base_cost_usd / settings.compute_credits.cc_to_usd_rate
        markup_cc = markup_amount_usd / settings.compute_credits.cc_to_usd_rate
        total_cc = total_cost_usd / settings.compute_credits.cc_to_usd_rate
        
        return {
            "storage_gb": storage_gb,
            "billing_days": billing_days,
            "base_cost_usd": base_cost_usd.quantize(Decimal("0.0001")),
            "markup_usd": markup_amount_usd.quantize(Decimal("0.0001")),
            "total_cost_usd": total_cost_usd.quantize(Decimal("0.0001")),
            "base_cost_cc": base_cost_cc.quantize(Decimal("0.00000001")),
            "markup_cc": markup_cc.quantize(Decimal("0.00000001")),
            "total_cost_cc": total_cc.quantize(Decimal("0.00000001")),
            "markup_percentage": float(self.markup_rate * 100),
            "actual_provider_cost_per_gb": actual_cost_per_gb_per_month
        }
    
    def calculate_compute_costs(
        self,
        compute_hours: Decimal,
        instance_type: str = "t3.medium"
    ) -> Dict[str, Decimal]:
        """Calculate compute costs with transparent breakdown"""
        
        # Actual AWS EC2 pricing (per hour)
        ec2_rates = {
            "t3.micro": Decimal("0.0104"),    # $0.0104/hour
            "t3.small": Decimal("0.0208"),    # $0.0208/hour
            "t3.medium": Decimal("0.0416"),   # $0.0416/hour
            "t3.large": Decimal("0.0832"),    # $0.0832/hour
            "m5.large": Decimal("0.096"),     # $0.096/hour
            "c5.large": Decimal("0.085")      # $0.085/hour
        }
        
        actual_rate_per_hour = ec2_rates.get(instance_type, ec2_rates["t3.medium"])
        
        # Calculate base costs
        base_cost_usd = compute_hours * actual_rate_per_hour
        
        # Apply markup
        markup_amount_usd = base_cost_usd * self.markup_rate
        total_cost_usd = base_cost_usd + markup_amount_usd
        
        # Convert to CC
        base_cost_cc = base_cost_usd / settings.compute_credits.cc_to_usd_rate
        markup_cc = markup_amount_usd / settings.compute_credits.cc_to_usd_rate
        total_cc = total_cost_usd / settings.compute_credits.cc_to_usd_rate
        
        return {
            "compute_hours": compute_hours,
            "instance_type": instance_type,
            "base_cost_usd": base_cost_usd.quantize(Decimal("0.0001")),
            "markup_usd": markup_amount_usd.quantize(Decimal("0.0001")),
            "total_cost_usd": total_cost_usd.quantize(Decimal("0.0001")),
            "base_cost_cc": base_cost_cc.quantize(Decimal("0.00000001")),
            "markup_cc": markup_cc.quantize(Decimal("0.00000001")),
            "total_cost_cc": total_cc.quantize(Decimal("0.00000001")),
            "markup_percentage": float(self.markup_rate * 100),
            "actual_provider_rate_per_hour": actual_rate_per_hour
        }
    
    def calculate_bandwidth_costs(
        self,
        bandwidth_gb: Decimal
    ) -> Dict[str, Decimal]:
        """Calculate bandwidth costs with transparent breakdown"""
        
        # Actual AWS CloudFront pricing
        actual_cost_per_gb = Decimal("0.085")  # $0.085/GB first 10TB
        
        # Calculate base costs
        base_cost_usd = bandwidth_gb * actual_cost_per_gb
        
        # Apply markup
        markup_amount_usd = base_cost_usd * self.markup_rate
        total_cost_usd = base_cost_usd + markup_amount_usd
        
        # Convert to CC
        base_cost_cc = base_cost_usd / settings.compute_credits.cc_to_usd_rate
        markup_cc = markup_amount_usd / settings.compute_credits.cc_to_usd_rate
        total_cc = total_cost_usd / settings.compute_credits.cc_to_usd_rate
        
        return {
            "bandwidth_gb": bandwidth_gb,
            "base_cost_usd": base_cost_usd.quantize(Decimal("0.0001")),
            "markup_usd": markup_amount_usd.quantize(Decimal("0.0001")),
            "total_cost_usd": total_cost_usd.quantize(Decimal("0.0001")),
            "base_cost_cc": base_cost_cc.quantize(Decimal("0.00000001")),
            "markup_cc": markup_cc.quantize(Decimal("0.00000001")),
            "total_cost_cc": total_cc.quantize(Decimal("0.00000001")),
            "markup_percentage": float(self.markup_rate * 100),
            "actual_provider_cost_per_gb": actual_cost_per_gb
        }
    
    def calculate_api_costs(
        self,
        api_calls: int
    ) -> Dict[str, Decimal]:
        """Calculate API costs with transparent breakdown"""
        
        # Actual AWS API Gateway pricing
        actual_cost_per_million = Decimal("3.50")  # $3.50 per million calls
        
        # Calculate base costs
        base_cost_usd = (Decimal(api_calls) / 1000000) * actual_cost_per_million
        
        # Apply markup
        markup_amount_usd = base_cost_usd * self.markup_rate
        total_cost_usd = base_cost_usd + markup_amount_usd
        
        # Convert to CC
        base_cost_cc = base_cost_usd / settings.compute_credits.cc_to_usd_rate
        markup_cc = markup_amount_usd / settings.compute_credits.cc_to_usd_rate
        total_cc = total_cost_usd / settings.compute_credits.cc_to_usd_rate
        
        return {
            "api_calls": api_calls,
            "base_cost_usd": base_cost_usd.quantize(Decimal("0.0001")),
            "markup_usd": markup_amount_usd.quantize(Decimal("0.0001")),
            "total_cost_usd": total_cost_usd.quantize(Decimal("0.0001")),
            "base_cost_cc": base_cost_cc.quantize(Decimal("0.00000001")),
            "markup_cc": markup_cc.quantize(Decimal("0.00000001")),
            "total_cost_cc": total_cc.quantize(Decimal("0.00000001")),
            "markup_percentage": float(self.markup_rate * 100),
            "actual_provider_cost_per_million": actual_cost_per_million
        }
    
    async def calculate_comprehensive_costs(
        self,
        storage_gb: Decimal = Decimal("0"),
        compute_hours: Decimal = Decimal("0"),
        bandwidth_gb: Decimal = Decimal("0"),
        api_calls: int = 0,
        instance_type: str = "t3.medium",
        billing_days: int = 30
    ) -> Dict:
        """Calculate comprehensive cost breakdown for all services"""
        
        # Calculate individual component costs
        storage_costs = self.calculate_storage_costs(storage_gb, billing_days)
        compute_costs = self.calculate_compute_costs(compute_hours, instance_type)
        bandwidth_costs = self.calculate_bandwidth_costs(bandwidth_gb)
        api_costs = self.calculate_api_costs(api_calls)
        
        # Calculate totals
        total_base_cost_usd = (
            storage_costs["base_cost_usd"] +
            compute_costs["base_cost_usd"] +
            bandwidth_costs["base_cost_usd"] +
            api_costs["base_cost_usd"]
        )
        
        total_markup_usd = (
            storage_costs["markup_usd"] +
            compute_costs["markup_usd"] +
            bandwidth_costs["markup_usd"] +
            api_costs["markup_usd"]
        )
        
        total_cost_usd = total_base_cost_usd + total_markup_usd
        
        total_base_cost_cc = (
            storage_costs["base_cost_cc"] +
            compute_costs["base_cost_cc"] +
            bandwidth_costs["base_cost_cc"] +
            api_costs["base_cost_cc"]
        )
        
        total_markup_cc = (
            storage_costs["markup_cc"] +
            compute_costs["markup_cc"] +
            bandwidth_costs["markup_cc"] +
            api_costs["markup_cc"]
        )
        
        total_cost_cc = total_base_cost_cc + total_markup_cc
        
        return {
            "billing_period": {
                "days": billing_days,
                "start_date": datetime.utcnow().date().isoformat(),
                "end_date": (datetime.utcnow() + timedelta(days=billing_days)).date().isoformat()
            },
            "usage": {
                "storage_gb": float(storage_gb),
                "compute_hours": float(compute_hours),
                "instance_type": instance_type,
                "bandwidth_gb": float(bandwidth_gb),
                "api_calls": api_calls
            },
            "component_breakdown": {
                "storage": storage_costs,
                "compute": compute_costs,
                "bandwidth": bandwidth_costs,
                "api": api_costs
            },
            "totals": {
                "base_cost_usd": float(total_base_cost_usd),
                "markup_usd": float(total_markup_usd),
                "total_cost_usd": float(total_cost_usd),
                "base_cost_cc": float(total_base_cost_cc),
                "markup_cc": float(total_markup_cc),
                "total_cost_cc": float(total_cost_cc),
                "markup_percentage": float(self.markup_rate * 100)
            },
            "transparency_note": (
                f"All costs are calculated using actual cloud provider rates plus a transparent "
                f"{float(self.markup_rate * 100)}% markup. Base costs reflect real infrastructure "
                f"expenses from AWS/Google Cloud."
            )
        }
    
    async def save_pricing_calculation(
        self,
        user_id: str,
        storage_gb: Decimal,
        compute_hours: Decimal,
        bandwidth_gb: Decimal,
        api_calls: int,
        total_cost_cc: Decimal,
        billing_start: datetime,
        billing_end: datetime
    ) -> PricingCalculation:
        """Save pricing calculation to database for audit trail"""
        
        # Calculate base costs and markup
        calculation = await self.calculate_comprehensive_costs(
            storage_gb, compute_hours, bandwidth_gb, api_calls
        )
        
        base_costs_cc = Decimal(str(calculation["totals"]["base_cost_cc"]))
        markup_cc = Decimal(str(calculation["totals"]["markup_cc"]))
        
        pricing_calc = PricingCalculation(
            user_id=user_id,
            storage_gb=storage_gb,
            compute_hours=compute_hours,
            bandwidth_gb=bandwidth_gb,
            api_calls=api_calls,
            base_costs_cc=base_costs_cc,
            markup_cc=markup_cc,
            total_cost_cc=total_cost_cc,
            billing_start=billing_start,
            billing_end=billing_end
        )
        
        self.db.add(pricing_calc)
        self.db.commit()
        
        logger.info(f"Saved pricing calculation for user {user_id}: {total_cost_cc} CC")
        return pricing_calc
    
    async def get_cost_projections(
        self,
        current_usage: Dict,
        projection_months: int = 12
    ) -> Dict:
        """Generate cost projections based on current usage patterns"""
        
        # Calculate current monthly costs
        monthly_calculation = await self.calculate_comprehensive_costs(
            storage_gb=Decimal(str(current_usage.get("storage_gb", 0))),
            compute_hours=Decimal(str(current_usage.get("compute_hours", 0))),
            bandwidth_gb=Decimal(str(current_usage.get("bandwidth_gb", 0))),
            api_calls=current_usage.get("api_calls", 0),
            billing_days=30
        )
        
        monthly_cost_cc = Decimal(str(monthly_calculation["totals"]["total_cost_cc"]))
        
        # Project costs with growth assumptions
        projections = []
        for month in range(1, projection_months + 1):
            # Assume 10% monthly growth in usage
            growth_factor = Decimal("1.1") ** month
            
            projected_monthly_cost = monthly_cost_cc * growth_factor
            
            projections.append({
                "month": month,
                "growth_factor": float(growth_factor),
                "projected_cost_cc": float(projected_monthly_cost),
                "projected_cost_usd": float(projected_monthly_cost * settings.compute_credits.cc_to_usd_rate),
                "cumulative_cost_cc": float(sum(
                    monthly_cost_cc * (Decimal("1.1") ** m) for m in range(1, month + 1)
                ))
            })
        
        return {
            "current_monthly_cost_cc": float(monthly_cost_cc),
            "current_monthly_cost_usd": float(monthly_cost_cc * settings.compute_credits.cc_to_usd_rate),
            "projection_months": projection_months,
            "growth_assumption": "10% monthly growth",
            "monthly_projections": projections,
            "total_projected_cost_cc": float(sum(p["projected_cost_cc"] for p in projections)),
            "average_monthly_cost_cc": float(sum(p["projected_cost_cc"] for p in projections) / projection_months)
        }
    
    async def compare_with_competitors(
        self,
        storage_gb: Decimal,
        compute_hours: Decimal,
        bandwidth_gb: Decimal,
        api_calls: int
    ) -> Dict:
        """Compare ActiveLedger pricing with major competitors"""
        
        # Get ActiveLedger pricing
        activelog_costs = await self.calculate_comprehensive_costs(
            storage_gb, compute_hours, bandwidth_gb, api_calls
        )
        
        # Competitor pricing (simplified estimates)
        aws_direct_cost = (
            storage_gb * Decimal("0.023") +  # S3
            compute_hours * Decimal("0.0416") +  # EC2 t3.medium
            bandwidth_gb * Decimal("0.085") +  # CloudFront
            (Decimal(api_calls) / 1000000) * Decimal("3.50")  # API Gateway
        )
        
        # Google Cloud (roughly similar)
        gcp_cost = aws_direct_cost * Decimal("0.95")  # Slightly cheaper
        
        # Azure (roughly similar)
        azure_cost = aws_direct_cost * Decimal("1.05")  # Slightly more expensive
        
        # Convert to USD for comparison
        activelog_usd = Decimal(str(activelog_costs["totals"]["total_cost_usd"]))
        
        return {
            "usage_scenario": {
                "storage_gb": float(storage_gb),
                "compute_hours": float(compute_hours),
                "bandwidth_gb": float(bandwidth_gb),
                "api_calls": api_calls
            },
            "cost_comparison_usd": {
                "activelog": {
                    "total": float(activelog_usd),
                    "base_cost": float(activelog_costs["totals"]["base_cost_usd"]),
                    "markup": float(activelog_costs["totals"]["markup_usd"]),
                    "markup_percentage": float(self.markup_rate * 100)
                },
                "aws_direct": float(aws_direct_cost),
                "google_cloud": float(gcp_cost),
                "microsoft_azure": float(azure_cost)
            },
            "value_proposition": {
                "vs_aws_direct": f"{float((activelog_usd / aws_direct_cost - 1) * 100):.1f}% more expensive",
                "transparency": "Full cost breakdown with transparent 15% markup",
                "additional_value": [
                    "Unified billing across all services",
                    "CC credit system for flexible payments",
                    "No hidden fees or surprise charges",
                    "Detailed cost breakdowns",
                    "Multi-currency support"
                ]
            }
        }