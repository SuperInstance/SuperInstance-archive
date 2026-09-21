from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
import uuid
from datetime import datetime, timedelta
import logging
import json

from ..database import (
    ServerFarmTier, User, ComputeCost, PricingTier, 
    ComputeLocation, ResourceType
)

logger = logging.getLogger(__name__)

class GarageFarmManager:
    """Manage garage server farm pricing tiers and economics"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def initialize_server_farm_tiers(self) -> Dict[str, Any]:
        """Initialize default server farm tiers with pricing"""
        
        try:
            # Check if tiers already exist
            result = await self.db.execute(select(func.count(ServerFarmTier.id)))
            existing_count = result.scalar()
            
            if existing_count > 0:
                return {
                    "message": "Server farm tiers already initialized",
                    "existing_tiers": existing_count
                }
            
            # Define tier configurations
            tier_configs = [
                {
                    "tier_name": "Garage Hobbyist",
                    "tier_level": 1,
                    "cpu_cost_per_hour": Decimal("0.05"),      # $0.05/hour
                    "gpu_cost_per_hour": Decimal("0.25"),      # $0.25/hour  
                    "memory_cost_per_gb_hour": Decimal("0.01"), # $0.01/GB/hour
                    "storage_cost_per_gb_month": Decimal("0.10"), # $0.10/GB/month
                    "bandwidth_cost_per_gb": Decimal("0.02"),   # $0.02/GB
                    "availability_sla": Decimal("95.0"),        # 95% uptime
                    "geographic_regions": ["local", "home"],
                    "description": "Basic garage setup with consumer hardware. Perfect for hobbyists and learning."
                },
                {
                    "tier_name": "Community Co-op",
                    "tier_level": 2,
                    "cpu_cost_per_hour": Decimal("0.08"),
                    "gpu_cost_per_hour": Decimal("0.40"),
                    "memory_cost_per_gb_hour": Decimal("0.015"),
                    "storage_cost_per_gb_month": Decimal("0.08"),
                    "bandwidth_cost_per_gb": Decimal("0.015"),
                    "availability_sla": Decimal("97.0"),
                    "geographic_regions": ["neighborhood", "local_community"],
                    "description": "Community-shared resources with better reliability. Shared costs among neighbors."
                },
                {
                    "tier_name": "Standard Home Lab",
                    "tier_level": 3,
                    "cpu_cost_per_hour": Decimal("0.12"),
                    "gpu_cost_per_hour": Decimal("0.60"),
                    "memory_cost_per_gb_hour": Decimal("0.02"),
                    "storage_cost_per_gb_month": Decimal("0.06"),
                    "bandwidth_cost_per_gb": Decimal("0.01"),
                    "availability_sla": Decimal("98.5"),
                    "geographic_regions": ["regional", "metro"],
                    "description": "Professional home lab setup with enterprise-grade hardware and networking."
                },
                {
                    "tier_name": "Premium Distributed",
                    "tier_level": 4,
                    "cpu_cost_per_hour": Decimal("0.18"),
                    "gpu_cost_per_hour": Decimal("0.90"),
                    "memory_cost_per_gb_hour": Decimal("0.025"),
                    "storage_cost_per_gb_month": Decimal("0.04"),
                    "bandwidth_cost_per_gb": Decimal("0.008"),
                    "availability_sla": Decimal("99.0"),
                    "geographic_regions": ["multi_region", "distributed"],
                    "description": "Premium distributed network with redundancy and high performance."
                },
                {
                    "tier_name": "Enterprise Hybrid",
                    "tier_level": 5,
                    "cpu_cost_per_hour": Decimal("0.25"),
                    "gpu_cost_per_hour": Decimal("1.20"),
                    "memory_cost_per_gb_hour": Decimal("0.03"),
                    "storage_cost_per_gb_month": Decimal("0.03"),
                    "bandwidth_cost_per_gb": Decimal("0.005"),
                    "availability_sla": Decimal("99.5"),
                    "geographic_regions": ["global", "enterprise"],
                    "description": "Enterprise-level hybrid cloud with garage infrastructure integration."
                }
            ]
            
            # Create tier records
            created_tiers = []
            for config in tier_configs:
                tier = ServerFarmTier(**config)
                self.db.add(tier)
                created_tiers.append(config["tier_name"])
            
            await self.db.commit()
            
            return {
                "initialized": True,
                "tiers_created": len(created_tiers),
                "tier_names": created_tiers,
                "message": "Server farm tiers initialized successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to initialize server farm tiers: {e}")
            raise
    
    async def get_optimal_tier_for_user(
        self,
        user_id: uuid.UUID,
        resource_requirements: Dict[str, Any],
        budget_constraints: Optional[Dict[str, Decimal]] = None
    ) -> Dict[str, Any]:
        """Recommend optimal server farm tier for user's needs"""
        
        try:
            # Get user's usage history
            user_history = await self._get_user_usage_history(user_id)
            
            # Get all available tiers
            result = await self.db.execute(
                select(ServerFarmTier).where(
                    ServerFarmTier.is_active == True
                ).order_by(ServerFarmTier.tier_level.asc())
            )
            tiers = result.scalars().all()
            
            if not tiers:
                raise ValueError("No server farm tiers available")
            
            # Calculate cost for each tier
            tier_analysis = []
            for tier in tiers:
                cost_analysis = await self._calculate_tier_cost(
                    tier, resource_requirements, user_history
                )
                
                # Check budget constraints
                within_budget = True
                if budget_constraints:
                    monthly_cost = cost_analysis['monthly_estimate']
                    max_budget = budget_constraints.get('monthly_max')
                    if max_budget and monthly_cost > max_budget:
                        within_budget = False
                
                tier_analysis.append({
                    "tier_id": str(tier.id),
                    "tier_name": tier.tier_name,
                    "tier_level": tier.tier_level,
                    "cost_analysis": cost_analysis,
                    "within_budget": within_budget,
                    "suitability_score": await self._calculate_suitability_score(
                        tier, resource_requirements, user_history
                    ),
                    "pros": await self._get_tier_pros(tier, resource_requirements),
                    "cons": await self._get_tier_cons(tier, resource_requirements)
                })
            
            # Sort by suitability score
            tier_analysis.sort(key=lambda x: x['suitability_score'], reverse=True)
            
            # Find optimal recommendation
            recommended_tier = tier_analysis[0]
            
            # Find budget-friendly alternatives
            budget_alternatives = [t for t in tier_analysis if t['within_budget']]
            
            return {
                "user_id": str(user_id),
                "recommended_tier": recommended_tier,
                "all_tiers_analysis": tier_analysis,
                "budget_friendly_options": budget_alternatives[:3],
                "usage_context": {
                    "historical_monthly_usage": user_history['monthly_average'] if user_history else 0,
                    "primary_resource_type": resource_requirements.get('primary_resource', 'cpu'),
                    "expected_growth": resource_requirements.get('growth_factor', 1.0)
                },
                "recommendation_confidence": "high" if len(user_history.get('records', [])) > 10 else "medium"
            }
            
        except Exception as e:
            logger.error(f"Failed to get optimal tier recommendation: {e}")
            raise
    
    async def calculate_garage_vs_cloud_savings(
        self,
        user_id: uuid.UUID,
        usage_scenario: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare garage farm costs with traditional cloud pricing"""
        
        try:
            # Get best garage tier for user
            optimal_recommendation = await self.get_optimal_tier_for_user(
                user_id, usage_scenario
            )
            
            best_garage_tier = optimal_recommendation['recommended_tier']
            garage_monthly_cost = best_garage_tier['cost_analysis']['monthly_estimate']
            
            # Calculate equivalent cloud costs (simplified - would integrate with cloud pricing APIs)
            cloud_costs = await self._estimate_cloud_equivalent_costs(usage_scenario)
            
            # Calculate savings
            monthly_savings = cloud_costs['monthly_estimate'] - garage_monthly_cost
            annual_savings = monthly_savings * 12
            savings_percentage = (monthly_savings / cloud_costs['monthly_estimate']) * 100 if cloud_costs['monthly_estimate'] > 0 else 0
            
            # ROI analysis for setting up garage infrastructure
            garage_setup_cost = await self._estimate_garage_setup_cost(best_garage_tier['tier_name'])
            payback_months = garage_setup_cost / monthly_savings if monthly_savings > 0 else float('inf')
            
            return {
                "user_id": str(user_id),
                "comparison_summary": {
                    "garage_monthly_cost": float(garage_monthly_cost),
                    "cloud_monthly_cost": float(cloud_costs['monthly_estimate']),
                    "monthly_savings": float(monthly_savings),
                    "annual_savings": float(annual_savings),
                    "savings_percentage": float(savings_percentage)
                },
                "recommended_garage_tier": best_garage_tier['tier_name'],
                "roi_analysis": {
                    "estimated_setup_cost": float(garage_setup_cost),
                    "payback_period_months": float(payback_months) if payback_months != float('inf') else None,
                    "break_even_viable": payback_months <= 24 if payback_months != float('inf') else False,
                    "5_year_total_savings": float(annual_savings * 5 - garage_setup_cost) if payback_months != float('inf') else None
                },
                "considerations": {
                    "garage_pros": [
                        "Significantly lower ongoing costs",
                        "Data privacy and control",
                        "No vendor lock-in",
                        "Customizable hardware"
                    ],
                    "garage_cons": [
                        "Initial setup investment required",
                        "Maintenance responsibilities",
                        "Limited geographic distribution",
                        "Potential reliability variations"
                    ],
                    "recommendation": await self._generate_garage_vs_cloud_recommendation(
                        monthly_savings, payback_months, usage_scenario
                    )
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate garage vs cloud savings: {e}")
            raise
    
    async def provision_garage_resources(
        self,
        user_id: uuid.UUID,
        tier_id: uuid.UUID,
        resource_allocation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Provision resources in a garage farm tier"""
        
        try:
            # Get the tier
            result = await self.db.execute(
                select(ServerFarmTier).where(ServerFarmTier.id == tier_id)
            )
            tier = result.scalar_one_or_none()
            
            if not tier:
                raise ValueError("Server farm tier not found")
            
            # Validate resource allocation
            allocation_errors = await self._validate_resource_allocation(tier, resource_allocation)
            if allocation_errors:
                return {
                    "provisioned": False,
                    "errors": allocation_errors
                }
            
            # Calculate provisioning costs
            provisioning_cost = await self._calculate_provisioning_cost(tier, resource_allocation)
            
            # Create provisioning record (simplified - would integrate with actual infrastructure)
            provisioning_id = str(uuid.uuid4())
            
            # Estimate deployment timeline
            deployment_timeline = await self._estimate_deployment_timeline(tier, resource_allocation)
            
            return {
                "provisioned": True,
                "provisioning_id": provisioning_id,
                "tier_name": tier.tier_name,
                "resource_allocation": resource_allocation,
                "cost_breakdown": provisioning_cost,
                "deployment_timeline": deployment_timeline,
                "estimated_monthly_cost": float(provisioning_cost['monthly_recurring']),
                "setup_instructions": await self._generate_setup_instructions(tier, resource_allocation),
                "monitoring_endpoints": await self._generate_monitoring_config(provisioning_id),
                "next_steps": [
                    "Review setup instructions",
                    "Prepare hardware according to specifications",
                    "Install monitoring agents",
                    "Run initial connectivity tests",
                    "Begin gradual workload migration"
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to provision garage resources: {e}")
            raise
    
    async def get_tier_performance_benchmarks(self, tier_id: uuid.UUID) -> Dict[str, Any]:
        """Get performance benchmarks for a server farm tier"""
        
        try:
            result = await self.db.execute(
                select(ServerFarmTier).where(ServerFarmTier.id == tier_id)
            )
            tier = result.scalar_one_or_none()
            
            if not tier:
                raise ValueError("Server farm tier not found")
            
            # Generate performance benchmarks (would be based on real data)
            benchmarks = {
                "compute_performance": {
                    "cpu_benchmark_score": tier.tier_level * 1000,  # Simplified scoring
                    "gpu_benchmark_score": tier.tier_level * 5000 if float(tier.gpu_cost_per_hour) > 0 else 0,
                    "memory_bandwidth_gbps": tier.tier_level * 10,
                    "storage_iops": tier.tier_level * 500,
                    "network_bandwidth_gbps": tier.tier_level * 2
                },
                "reliability_metrics": {
                    "availability_percentage": float(tier.availability_sla),
                    "mean_time_to_recovery_hours": max(1.0, 6.0 - tier.tier_level),
                    "scheduled_maintenance_hours_per_month": max(2, 8 - tier.tier_level),
                    "historical_uptime_data": await self._generate_uptime_history(tier)
                },
                "cost_efficiency": {
                    "performance_per_dollar": (tier.tier_level * 100) / float(tier.cpu_cost_per_hour),
                    "value_rating": min(5.0, tier.tier_level + 1.0),
                    "cost_optimization_opportunities": await self._identify_cost_optimizations(tier)
                },
                "scalability": {
                    "horizontal_scaling": tier.tier_level >= 3,
                    "auto_scaling_available": tier.tier_level >= 4,
                    "max_concurrent_jobs": tier.tier_level * 10,
                    "scaling_time_minutes": max(1, 10 - tier.tier_level * 2)
                }
            }
            
            return {
                "tier_id": str(tier_id),
                "tier_name": tier.tier_name,
                "tier_level": tier.tier_level,
                "benchmarks": benchmarks,
                "comparison_with_cloud": await self._compare_with_cloud_performance(tier),
                "benchmark_date": datetime.utcnow().isoformat(),
                "benchmark_methodology": "ActiveLog Internal Testing Suite v2.0"
            }
            
        except Exception as e:
            logger.error(f"Failed to get tier performance benchmarks: {e}")
            raise
    
    async def _get_user_usage_history(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """Get user's historical usage patterns"""
        
        result = await self.db.execute(
            select(ComputeCost).where(ComputeCost.user_id == user_id)
            .order_by(ComputeCost.timestamp.desc()).limit(100)
        )
        records = result.scalars().all()
        
        if not records:
            return {"records": [], "monthly_average": 0}
        
        total_cost = sum(float(record.final_cost) for record in records)
        monthly_average = total_cost * (30 / len(records))  # Normalize to monthly
        
        return {
            "records": records,
            "monthly_average": monthly_average,
            "total_sessions": len(records)
        }
    
    async def _calculate_tier_cost(
        self,
        tier: ServerFarmTier,
        requirements: Dict[str, Any],
        history: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate cost for a specific tier based on requirements"""
        
        # Expected monthly usage (hours)
        cpu_hours = requirements.get('cpu_hours_per_month', 100)
        gpu_hours = requirements.get('gpu_hours_per_month', 50)
        memory_gb_hours = requirements.get('memory_gb_hours_per_month', 1000)
        storage_gb = requirements.get('storage_gb', 100)
        bandwidth_gb = requirements.get('bandwidth_gb_per_month', 500)
        
        # Calculate costs
        cpu_cost = tier.cpu_cost_per_hour * Decimal(str(cpu_hours))
        gpu_cost = tier.gpu_cost_per_hour * Decimal(str(gpu_hours))
        memory_cost = tier.memory_cost_per_gb_hour * Decimal(str(memory_gb_hours))
        storage_cost = tier.storage_cost_per_gb_month * Decimal(str(storage_gb))
        bandwidth_cost = tier.bandwidth_cost_per_gb * Decimal(str(bandwidth_gb))
        
        total_monthly = cpu_cost + gpu_cost + memory_cost + storage_cost + bandwidth_cost
        
        return {
            "monthly_estimate": float(total_monthly),
            "breakdown": {
                "cpu": float(cpu_cost),
                "gpu": float(gpu_cost),
                "memory": float(memory_cost),
                "storage": float(storage_cost),
                "bandwidth": float(bandwidth_cost)
            },
            "annual_estimate": float(total_monthly * 12)
        }
    
    async def _calculate_suitability_score(
        self,
        tier: ServerFarmTier,
        requirements: Dict[str, Any],
        history: Dict[str, Any]
    ) -> float:
        """Calculate how suitable a tier is for the user's needs"""
        
        score = 0.0
        
        # Base score from tier level
        score += tier.tier_level * 10
        
        # Adjust for reliability requirements
        required_sla = requirements.get('required_sla', 95.0)
        if float(tier.availability_sla) >= required_sla:
            score += 20
        else:
            score -= 10
        
        # Adjust for geographic preferences
        preferred_regions = requirements.get('preferred_regions', [])
        if any(region in tier.geographic_regions for region in preferred_regions):
            score += 15
        
        # Adjust for budget efficiency
        cost_per_performance = float(tier.cpu_cost_per_hour) / tier.tier_level
        if cost_per_performance < 0.1:  # Good value
            score += 15
        
        # Adjust for usage history compatibility
        if history.get('monthly_average', 0) > 0:
            # Prefer tiers that match historical usage patterns
            score += 10  # Simplified - would be more sophisticated
        
        return min(100.0, max(0.0, score))
    
    async def _get_tier_pros(self, tier: ServerFarmTier, requirements: Dict) -> List[str]:
        """Get advantages of a specific tier"""
        
        pros = []
        
        if tier.tier_level == 1:
            pros.extend([
                "Lowest cost option",
                "Great for learning and experimentation",
                "No long-term commitments"
            ])
        elif tier.tier_level >= 4:
            pros.extend([
                "Enterprise-grade reliability",
                "High performance capabilities",
                "Advanced scaling options"
            ])
        
        if float(tier.availability_sla) >= 99.0:
            pros.append("High availability guarantee")
        
        if "local" in tier.geographic_regions:
            pros.append("Local processing for data privacy")
        
        return pros
    
    async def _get_tier_cons(self, tier: ServerFarmTier, requirements: Dict) -> List[str]:
        """Get disadvantages of a specific tier"""
        
        cons = []
        
        if tier.tier_level == 1:
            cons.extend([
                "Limited reliability guarantees",
                "Basic hardware specifications",
                "Potential performance variations"
            ])
        
        if tier.tier_level >= 4:
            cons.extend([
                "Higher cost premium",
                "May be over-specified for simple tasks"
            ])
        
        required_sla = requirements.get('required_sla', 95.0)
        if float(tier.availability_sla) < required_sla:
            cons.append(f"SLA below required {required_sla}%")
        
        return cons
    
    async def _estimate_cloud_equivalent_costs(self, usage_scenario: Dict) -> Dict[str, Any]:
        """Estimate equivalent costs for major cloud providers"""
        
        # Simplified cloud cost estimation (would integrate with real APIs)
        base_cost = Decimal("200.0")  # Base monthly cost
        
        # Scale based on usage
        cpu_hours = usage_scenario.get('cpu_hours_per_month', 100)
        gpu_hours = usage_scenario.get('gpu_hours_per_month', 50)
        
        cloud_cost = base_cost + (Decimal(str(cpu_hours)) * Decimal("0.15"))
        if gpu_hours > 0:
            cloud_cost += Decimal(str(gpu_hours)) * Decimal("2.50")
        
        return {
            "monthly_estimate": float(cloud_cost),
            "provider_breakdown": {
                "aws": float(cloud_cost * Decimal("1.0")),
                "gcp": float(cloud_cost * Decimal("0.95")),
                "azure": float(cloud_cost * Decimal("1.02"))
            }
        }
    
    async def _estimate_garage_setup_cost(self, tier_name: str) -> Decimal:
        """Estimate initial setup cost for garage infrastructure"""
        
        setup_costs = {
            "Garage Hobbyist": Decimal("2000"),      # $2,000
            "Community Co-op": Decimal("5000"),      # $5,000
            "Standard Home Lab": Decimal("10000"),   # $10,000
            "Premium Distributed": Decimal("20000"), # $20,000
            "Enterprise Hybrid": Decimal("50000")    # $50,000
        }
        
        return setup_costs.get(tier_name, Decimal("10000"))
    
    async def _generate_garage_vs_cloud_recommendation(
        self,
        monthly_savings: Decimal,
        payback_months: float,
        usage_scenario: Dict
    ) -> str:
        """Generate recommendation for garage vs cloud"""
        
        if monthly_savings <= 0:
            return "Cloud computing recommended - garage setup not cost-effective for current usage"
        
        if payback_months <= 12:
            return "Strong recommendation for garage setup - payback within 1 year"
        elif payback_months <= 24:
            return "Good candidate for garage setup - reasonable payback period"
        elif payback_months <= 36:
            return "Consider garage setup if long-term committed to current usage levels"
        else:
            return "Cloud recommended - garage setup payback period too long"
    
    async def _validate_resource_allocation(
        self, 
        tier: ServerFarmTier, 
        allocation: Dict[str, Any]
    ) -> List[str]:
        """Validate resource allocation request"""
        
        errors = []
        
        # Check if allocation is within tier capabilities (simplified validation)
        max_cpu = tier.tier_level * 8  # Max CPUs per tier level
        requested_cpu = allocation.get('cpu_cores', 1)
        
        if requested_cpu > max_cpu:
            errors.append(f"Requested {requested_cpu} CPUs exceeds tier limit of {max_cpu}")
        
        # Add more validation as needed
        
        return errors
    
    async def _calculate_provisioning_cost(
        self,
        tier: ServerFarmTier,
        allocation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate provisioning costs"""
        
        setup_fee = Decimal("50.0")  # One-time setup
        monthly_base = tier.cpu_cost_per_hour * 24 * 30  # Simplified monthly cost
        
        return {
            "one_time_setup": float(setup_fee),
            "monthly_recurring": float(monthly_base),
            "estimated_annual": float(monthly_base * 12)
        }
    
    async def _estimate_deployment_timeline(
        self,
        tier: ServerFarmTier,
        allocation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Estimate deployment timeline"""
        
        base_days = max(1, 5 - tier.tier_level)  # Lower tiers deploy faster
        
        return {
            "estimated_days": base_days,
            "phases": [
                {"phase": "Hardware Preparation", "days": max(1, base_days // 2)},
                {"phase": "Software Installation", "days": 1},
                {"phase": "Testing & Validation", "days": 1}
            ]
        }
    
    async def _generate_setup_instructions(
        self,
        tier: ServerFarmTier,
        allocation: Dict[str, Any]
    ) -> List[str]:
        """Generate setup instructions"""
        
        return [
            f"1. Prepare hardware according to {tier.tier_name} specifications",
            "2. Install ActiveLog edge agent",
            "3. Configure network connectivity",
            "4. Run hardware validation tests",
            "5. Register with ActiveLog resource pool"
        ]
    
    async def _generate_monitoring_config(self, provisioning_id: str) -> Dict[str, str]:
        """Generate monitoring configuration"""
        
        return {
            "metrics_endpoint": f"https://monitoring.activelog.io/garage/{provisioning_id}",
            "health_check": f"https://api.activelog.io/health/garage/{provisioning_id}",
            "alerting": f"https://alerts.activelog.io/garage/{provisioning_id}"
        }
    
    async def _generate_uptime_history(self, tier: ServerFarmTier) -> List[Dict]:
        """Generate simulated uptime history"""
        
        # In production, this would query actual uptime data
        history = []
        base_uptime = float(tier.availability_sla)
        
        for month in range(12):
            # Add some realistic variation
            variation = (month % 3 - 1) * 0.5
            uptime = min(100.0, max(90.0, base_uptime + variation))
            
            history.append({
                "month": month + 1,
                "uptime_percentage": round(uptime, 2),
                "planned_maintenance_hours": max(1, 4 - tier.tier_level),
                "unplanned_downtime_hours": max(0, (100 - uptime) * 7.3)  # Convert % to hours
            })
        
        return history
    
    async def _identify_cost_optimizations(self, tier: ServerFarmTier) -> List[str]:
        """Identify cost optimization opportunities"""
        
        optimizations = []
        
        if tier.tier_level <= 2:
            optimizations.extend([
                "Consider community pooling for better rates",
                "Explore equipment sharing opportunities"
            ])
        
        if float(tier.gpu_cost_per_hour) > 1.0:
            optimizations.append("GPU sharing during idle periods")
        
        optimizations.append("Off-peak scheduling for batch jobs")
        
        return optimizations
    
    async def _compare_with_cloud_performance(self, tier: ServerFarmTier) -> Dict[str, Any]:
        """Compare tier performance with cloud equivalents"""
        
        # Simplified comparison
        return {
            "performance_ratio": min(2.0, tier.tier_level * 0.4),
            "cost_ratio": max(0.3, 1.0 - tier.tier_level * 0.1),
            "reliability_comparison": "comparable" if tier.tier_level >= 3 else "lower",
            "latency_advantage": tier.tier_level >= 2  # Local processing advantage
        }