#!/usr/bin/env python3
"""
Cost Proposal Generation System
Comprehensive cost proposal and pricing analysis for government contracts
"""

import asyncio
import logging
import sqlite3
import json
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import uuid
import math

logger = logging.getLogger(__name__)

class LaborCategory(Enum):
    SENIOR_ENGINEER = "senior_engineer"
    ENGINEER = "engineer"
    JUNIOR_ENGINEER = "junior_engineer"
    PROGRAM_MANAGER = "program_manager"
    PROJECT_MANAGER = "project_manager"
    ANALYST = "analyst"
    SPECIALIST = "specialist"
    TECHNICIAN = "technician"
    ADMIN_SUPPORT = "admin_support"

class CostType(Enum):
    DIRECT_LABOR = "direct_labor"
    INDIRECT_LABOR = "indirect_labor"
    FRINGE_BENEFITS = "fringe_benefits"
    OVERHEAD = "overhead"
    GENERAL_ADMIN = "general_admin"
    MATERIALS = "materials"
    SUBCONTRACTOR = "subcontractor"
    TRAVEL = "travel"
    OTHER_DIRECT_COSTS = "other_direct_costs"
    PROFIT_FEE = "profit_fee"

class ContractVehicle(Enum):
    PRIME_CONTRACT = "prime_contract"
    SUBCONTRACT = "subcontract"
    GSA_SCHEDULE = "gsa_schedule"
    CIO_SP3 = "cio_sp3"
    SEWP = "sewp"
    OASIS = "oasis"

class PricingStrategy(Enum):
    COMPETITIVE = "competitive"
    COST_PLUS = "cost_plus"
    PRICE_TO_WIN = "price_to_win"
    MARKET_RATE = "market_rate"
    GOVERNMENT_ESTIMATE = "government_estimate"

class CostProposalSystem:
    def __init__(self):
        self.db_path = "data/cost_proposals.db"
        self.labor_rates = {}
        self.indirect_rates = {}
        self.escalation_factors = {}
        self.market_data = {}

    async def initialize(self):
        """Initialize cost proposal system"""
        try:
            await self._create_database_schema()
            await self._load_labor_rates()
            await self._load_indirect_rates()
            await self._load_escalation_factors()
            await self._load_market_data()
            logger.info("Cost Proposal System initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Cost Proposal System: {e}")
            raise

    async def _create_database_schema(self):
        """Create database tables for cost proposals"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Cost proposals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cost_proposals (
                id TEXT PRIMARY KEY,
                rfp_id TEXT NOT NULL,
                proposal_name TEXT NOT NULL,
                contract_type TEXT NOT NULL,
                contract_vehicle TEXT,
                performance_period_months INTEGER,
                base_period_months INTEGER,
                option_periods TEXT,
                pricing_strategy TEXT NOT NULL,
                total_contract_value REAL NOT NULL,
                direct_labor_cost REAL DEFAULT 0.0,
                indirect_cost REAL DEFAULT 0.0,
                material_cost REAL DEFAULT 0.0,
                subcontractor_cost REAL DEFAULT 0.0,
                travel_cost REAL DEFAULT 0.0,
                other_direct_cost REAL DEFAULT 0.0,
                overhead_rate REAL DEFAULT 0.0,
                ga_rate REAL DEFAULT 0.0,
                profit_fee_rate REAL DEFAULT 0.0,
                profit_fee_amount REAL DEFAULT 0.0,
                escalation_applied BOOLEAN DEFAULT 0,
                competitive_analysis TEXT,
                risk_assessment TEXT,
                assumptions TEXT,
                status TEXT NOT NULL DEFAULT 'draft',
                version INTEGER DEFAULT 1,
                created_by TEXT,
                approved_by TEXT,
                audit_trail TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Labor estimates table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS labor_estimates (
                id TEXT PRIMARY KEY,
                proposal_id TEXT NOT NULL,
                labor_category TEXT NOT NULL,
                base_rate REAL NOT NULL,
                loaded_rate REAL NOT NULL,
                hours_year1 REAL DEFAULT 0.0,
                hours_year2 REAL DEFAULT 0.0,
                hours_year3 REAL DEFAULT 0.0,
                hours_year4 REAL DEFAULT 0.0,
                hours_year5 REAL DEFAULT 0.0,
                total_hours REAL NOT NULL,
                total_cost REAL NOT NULL,
                escalation_rate REAL DEFAULT 0.0,
                location_factor REAL DEFAULT 1.0,
                clearance_required TEXT,
                skill_premium REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (proposal_id) REFERENCES cost_proposals (id)
            )
        """)
        
        # Material estimates table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS material_estimates (
                id TEXT PRIMARY KEY,
                proposal_id TEXT NOT NULL,
                item_description TEXT NOT NULL,
                item_category TEXT,
                unit_of_measure TEXT,
                quantity REAL NOT NULL,
                unit_cost REAL NOT NULL,
                total_cost REAL NOT NULL,
                vendor_source TEXT,
                delivery_schedule TEXT,
                risk_factor REAL DEFAULT 1.0,
                contingency_percentage REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (proposal_id) REFERENCES cost_proposals (id)
            )
        """)
        
        # Subcontractor estimates table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subcontractor_estimates (
                id TEXT PRIMARY KEY,
                proposal_id TEXT NOT NULL,
                subcontractor_name TEXT NOT NULL,
                work_description TEXT NOT NULL,
                subcontract_value REAL NOT NULL,
                percentage_of_total REAL,
                small_business_type TEXT,
                past_performance_rating TEXT,
                risk_assessment TEXT,
                payment_terms TEXT,
                deliverables TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (proposal_id) REFERENCES cost_proposals (id)
            )
        """)
        
        # Travel estimates table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS travel_estimates (
                id TEXT PRIMARY KEY,
                proposal_id TEXT NOT NULL,
                travel_purpose TEXT NOT NULL,
                destination TEXT NOT NULL,
                travelers_count INTEGER DEFAULT 1,
                trips_per_year INTEGER DEFAULT 1,
                duration_days REAL NOT NULL,
                airfare_cost REAL DEFAULT 0.0,
                lodging_cost REAL DEFAULT 0.0,
                meals_incidentals REAL DEFAULT 0.0,
                ground_transport REAL DEFAULT 0.0,
                rental_car REAL DEFAULT 0.0,
                total_trip_cost REAL NOT NULL,
                annual_travel_cost REAL NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (proposal_id) REFERENCES cost_proposals (id)
            )
        """)
        
        # Competitive analysis table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS competitive_analysis (
                id TEXT PRIMARY KEY,
                proposal_id TEXT NOT NULL,
                competitor_name TEXT NOT NULL,
                estimated_price REAL,
                pricing_strategy TEXT,
                strengths TEXT,
                weaknesses TEXT,
                market_position TEXT,
                win_probability REAL DEFAULT 0.0,
                intelligence_source TEXT,
                confidence_level TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (proposal_id) REFERENCES cost_proposals (id)
            )
        """)
        
        # Price sensitivity analysis table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_sensitivity (
                id TEXT PRIMARY KEY,
                proposal_id TEXT NOT NULL,
                scenario_name TEXT NOT NULL,
                price_point REAL NOT NULL,
                win_probability REAL NOT NULL,
                profit_margin REAL NOT NULL,
                risk_level TEXT,
                recommended BOOLEAN DEFAULT 0,
                analysis_notes TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (proposal_id) REFERENCES cost_proposals (id)
            )
        """)
        
        conn.commit()
        conn.close()

    async def _load_labor_rates(self):
        """Load current labor rates by category and location"""
        self.labor_rates = {
            LaborCategory.SENIOR_ENGINEER.value: {
                "base_rate": Decimal('95.00'),
                "clearance_premium": Decimal('15.00'),
                "location_factors": {
                    "DC_Metro": Decimal('1.25'),
                    "San_Francisco": Decimal('1.40'),
                    "Austin": Decimal('1.10'),
                    "General": Decimal('1.00')
                }
            },
            LaborCategory.ENGINEER.value: {
                "base_rate": Decimal('75.00'),
                "clearance_premium": Decimal('12.00'),
                "location_factors": {
                    "DC_Metro": Decimal('1.20'),
                    "San_Francisco": Decimal('1.35'),
                    "Austin": Decimal('1.08'),
                    "General": Decimal('1.00')
                }
            },
            LaborCategory.JUNIOR_ENGINEER.value: {
                "base_rate": Decimal('55.00'),
                "clearance_premium": Decimal('8.00'),
                "location_factors": {
                    "DC_Metro": Decimal('1.15'),
                    "San_Francisco": Decimal('1.30'),
                    "Austin": Decimal('1.05'),
                    "General": Decimal('1.00')
                }
            },
            LaborCategory.PROGRAM_MANAGER.value: {
                "base_rate": Decimal('125.00'),
                "clearance_premium": Decimal('20.00'),
                "location_factors": {
                    "DC_Metro": Decimal('1.30'),
                    "San_Francisco": Decimal('1.45'),
                    "Austin": Decimal('1.12'),
                    "General": Decimal('1.00')
                }
            },
            LaborCategory.PROJECT_MANAGER.value: {
                "base_rate": Decimal('95.00'),
                "clearance_premium": Decimal('15.00'),
                "location_factors": {
                    "DC_Metro": Decimal('1.25'),
                    "San_Francisco": Decimal('1.40'),
                    "Austin": Decimal('1.10'),
                    "General": Decimal('1.00')
                }
            },
            LaborCategory.ANALYST.value: {
                "base_rate": Decimal('65.00'),
                "clearance_premium": Decimal('10.00'),
                "location_factors": {
                    "DC_Metro": Decimal('1.18'),
                    "San_Francisco": Decimal('1.32'),
                    "Austin": Decimal('1.07'),
                    "General": Decimal('1.00')
                }
            }
        }

    async def _load_indirect_rates(self):
        """Load indirect cost rates"""
        self.indirect_rates = {
            "fringe_benefits": Decimal('0.32'),  # 32%
            "overhead": Decimal('0.85'),         # 85%
            "general_admin": Decimal('0.15'),    # 15%
            "profit_fee_cost_plus": Decimal('0.07'),  # 7%
            "profit_fee_fixed_price": Decimal('0.12') # 12%
        }

    async def _load_escalation_factors(self):
        """Load escalation factors by year"""
        self.escalation_factors = {
            "labor": {
                2024: Decimal('1.00'),
                2025: Decimal('1.035'),  # 3.5%
                2026: Decimal('1.071'),  # 3.5%
                2027: Decimal('1.108'),  # 3.5%
                2028: Decimal('1.146'),  # 3.5%
            },
            "materials": {
                2024: Decimal('1.00'),
                2025: Decimal('1.025'),  # 2.5%
                2026: Decimal('1.051'),  # 2.5%
                2027: Decimal('1.077'),  # 2.5%
                2028: Decimal('1.103'),  # 2.5%
            }
        }

    async def _load_market_data(self):
        """Load market intelligence data"""
        self.market_data = {
            "average_win_rates": {
                "prime_contracts": 0.15,
                "subcontracts": 0.35,
                "idiq_task_orders": 0.25
            },
            "typical_profit_margins": {
                "cost_plus": (0.05, 0.08),
                "fixed_price": (0.08, 0.15),
                "time_materials": (0.10, 0.18)
            },
            "competitive_factors": {
                "price_weight": 0.30,
                "technical_weight": 0.50,
                "past_performance_weight": 0.20
            }
        }

    async def generate_proposal(self, proposal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive cost proposal"""
        try:
            proposal_id = str(uuid.uuid4())
            
            # Extract key parameters
            contract_opportunity = proposal_data.get("contract_opportunity", {})
            cost_elements = proposal_data.get("cost_elements", [])
            pricing_strategy = proposal_data.get("pricing_strategy", PricingStrategy.COMPETITIVE.value)
            
            # Calculate direct labor costs
            labor_costs = await self._calculate_labor_costs(proposal_id, cost_elements.get("labor", []))
            
            # Calculate material costs
            material_costs = await self._calculate_material_costs(proposal_id, cost_elements.get("materials", []))
            
            # Calculate subcontractor costs
            subcontractor_costs = await self._calculate_subcontractor_costs(proposal_id, cost_elements.get("subcontractors", []))
            
            # Calculate travel costs
            travel_costs = await self._calculate_travel_costs(proposal_id, cost_elements.get("travel", []))
            
            # Calculate indirect costs
            indirect_costs = await self._calculate_indirect_costs(labor_costs["total"])
            
            # Apply escalation if multi-year contract
            performance_period = contract_opportunity.get("performance_period_months", 12)
            if performance_period > 12:
                escalated_costs = await self._apply_escalation(
                    labor_costs, material_costs, performance_period
                )
            else:
                escalated_costs = {
                    "labor": labor_costs,
                    "materials": material_costs
                }
            
            # Calculate total contract value
            total_direct_costs = (
                escalated_costs["labor"]["total"] +
                material_costs["total"] +
                subcontractor_costs["total"] +
                travel_costs["total"]
            )
            
            total_indirect_costs = indirect_costs["total"]
            subtotal = total_direct_costs + total_indirect_costs
            
            # Calculate profit/fee
            profit_fee = await self._calculate_profit_fee(subtotal, contract_opportunity.get("contract_type"))
            
            # Total contract value
            total_contract_value = subtotal + profit_fee["amount"]
            
            # Perform competitive analysis
            competitive_analysis = await self._perform_competitive_analysis(
                proposal_id, total_contract_value, contract_opportunity
            )
            
            # Generate price-to-win analysis
            price_to_win = await self._analyze_price_to_win(
                proposal_id, total_contract_value, competitive_analysis
            )
            
            # Store proposal in database
            await self._store_proposal(
                proposal_id, contract_opportunity, labor_costs, indirect_costs,
                material_costs, subcontractor_costs, travel_costs, profit_fee,
                total_contract_value, pricing_strategy
            )
            
            # Generate final proposal package
            proposal_package = {
                "proposal_id": proposal_id,
                "contract_opportunity": contract_opportunity,
                "pricing_strategy": pricing_strategy,
                "cost_breakdown": {
                    "direct_labor": {
                        "amount": float(escalated_costs["labor"]["total"]),
                        "details": escalated_costs["labor"]["categories"]
                    },
                    "indirect_costs": {
                        "amount": float(total_indirect_costs),
                        "breakdown": indirect_costs["breakdown"]
                    },
                    "materials": {
                        "amount": float(material_costs["total"]),
                        "details": material_costs.get("items", [])
                    },
                    "subcontractors": {
                        "amount": float(subcontractor_costs["total"]),
                        "details": subcontractor_costs.get("vendors", [])
                    },
                    "travel": {
                        "amount": float(travel_costs["total"]),
                        "details": travel_costs.get("trips", [])
                    },
                    "profit_fee": {
                        "rate": float(profit_fee["rate"]),
                        "amount": float(profit_fee["amount"])
                    }
                },
                "total_contract_value": float(total_contract_value),
                "competitive_analysis": competitive_analysis,
                "price_to_win_analysis": price_to_win,
                "risk_assessment": await self._assess_pricing_risks(total_contract_value, competitive_analysis),
                "recommendations": await self._generate_pricing_recommendations(
                    total_contract_value, competitive_analysis, price_to_win
                )
            }
            
            logger.info(f"Cost proposal generated: {proposal_id} - ${total_contract_value:,.2f}")
            return proposal_package
            
        except Exception as e:
            logger.error(f"Error generating cost proposal: {e}")
            return {"error": str(e)}

    async def _calculate_labor_costs(self, proposal_id: str, labor_estimates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate direct labor costs"""
        total_cost = Decimal('0')
        categories = {}
        
        for estimate in labor_estimates:
            category = estimate.get("labor_category")
            hours = Decimal(str(estimate.get("total_hours", 0)))
            location = estimate.get("location", "General")
            clearance_required = estimate.get("clearance_required", False)
            
            if category in self.labor_rates:
                rate_info = self.labor_rates[category]
                base_rate = rate_info["base_rate"]
                
                # Apply location factor
                location_factor = rate_info["location_factors"].get(location, Decimal('1.00'))
                adjusted_rate = base_rate * location_factor
                
                # Add clearance premium if required
                if clearance_required:
                    adjusted_rate += rate_info["clearance_premium"]
                
                # Calculate loaded rate (with fringe benefits)
                fringe_rate = self.indirect_rates["fringe_benefits"]
                loaded_rate = adjusted_rate * (Decimal('1') + fringe_rate)
                
                # Calculate total cost for this category
                category_cost = loaded_rate * hours
                total_cost += category_cost
                
                categories[category] = {
                    "base_rate": float(base_rate),
                    "loaded_rate": float(loaded_rate),
                    "hours": float(hours),
                    "total_cost": float(category_cost),
                    "location_factor": float(location_factor),
                    "clearance_premium": float(rate_info["clearance_premium"]) if clearance_required else 0.0
                }
        
        return {
            "total": total_cost,
            "categories": categories
        }

    async def _calculate_material_costs(self, proposal_id: str, material_estimates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate material costs"""
        total_cost = Decimal('0')
        items = []
        
        for estimate in material_estimates:
            quantity = Decimal(str(estimate.get("quantity", 0)))
            unit_cost = Decimal(str(estimate.get("unit_cost", 0)))
            risk_factor = Decimal(str(estimate.get("risk_factor", 1.0)))
            contingency = Decimal(str(estimate.get("contingency_percentage", 0))) / 100
            
            base_cost = quantity * unit_cost * risk_factor
            contingency_amount = base_cost * contingency
            item_total = base_cost + contingency_amount
            
            total_cost += item_total
            
            items.append({
                "description": estimate.get("item_description"),
                "quantity": float(quantity),
                "unit_cost": float(unit_cost),
                "base_cost": float(base_cost),
                "contingency": float(contingency_amount),
                "total_cost": float(item_total)
            })
        
        return {
            "total": total_cost,
            "items": items
        }

    async def _calculate_subcontractor_costs(self, proposal_id: str, subcontractor_estimates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate subcontractor costs"""
        total_cost = Decimal('0')
        vendors = []
        
        for estimate in subcontractor_estimates:
            subcontract_value = Decimal(str(estimate.get("subcontract_value", 0)))
            total_cost += subcontract_value
            
            vendors.append({
                "name": estimate.get("subcontractor_name"),
                "work_description": estimate.get("work_description"),
                "value": float(subcontract_value),
                "small_business_type": estimate.get("small_business_type"),
                "risk_assessment": estimate.get("risk_assessment")
            })
        
        return {
            "total": total_cost,
            "vendors": vendors
        }

    async def _calculate_travel_costs(self, proposal_id: str, travel_estimates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate travel costs"""
        total_cost = Decimal('0')
        trips = []
        
        for estimate in travel_estimates:
            travelers = Decimal(str(estimate.get("travelers_count", 1)))
            trips_per_year = Decimal(str(estimate.get("trips_per_year", 1)))
            
            trip_costs = (
                Decimal(str(estimate.get("airfare_cost", 0))) +
                Decimal(str(estimate.get("lodging_cost", 0))) +
                Decimal(str(estimate.get("meals_incidentals", 0))) +
                Decimal(str(estimate.get("ground_transport", 0))) +
                Decimal(str(estimate.get("rental_car", 0)))
            )
            
            annual_cost = trip_costs * travelers * trips_per_year
            total_cost += annual_cost
            
            trips.append({
                "purpose": estimate.get("travel_purpose"),
                "destination": estimate.get("destination"),
                "annual_cost": float(annual_cost),
                "trip_cost": float(trip_costs),
                "travelers": int(travelers),
                "trips_per_year": int(trips_per_year)
            })
        
        return {
            "total": total_cost,
            "trips": trips
        }

    async def _calculate_indirect_costs(self, direct_labor_base: Decimal) -> Dict[str, Any]:
        """Calculate indirect costs (overhead and G&A)"""
        overhead_rate = self.indirect_rates["overhead"]
        ga_rate = self.indirect_rates["general_admin"]
        
        overhead_amount = direct_labor_base * overhead_rate
        overhead_base = direct_labor_base + overhead_amount
        ga_amount = overhead_base * ga_rate
        
        total_indirect = overhead_amount + ga_amount
        
        return {
            "total": total_indirect,
            "breakdown": {
                "overhead": {
                    "rate": float(overhead_rate),
                    "base": float(direct_labor_base),
                    "amount": float(overhead_amount)
                },
                "general_admin": {
                    "rate": float(ga_rate),
                    "base": float(overhead_base),
                    "amount": float(ga_amount)
                }
            }
        }

    async def _apply_escalation(self, labor_costs: Dict[str, Any], 
                               material_costs: Dict[str, Any], 
                               performance_period_months: int) -> Dict[str, Any]:
        """Apply escalation factors for multi-year contracts"""
        current_year = datetime.now().year
        years_in_contract = math.ceil(performance_period_months / 12)
        
        escalated_labor = Decimal(str(labor_costs["total"]))
        escalated_materials = Decimal(str(material_costs["total"]))
        
        # Apply yearly escalation
        for year_offset in range(1, years_in_contract):
            escalation_year = current_year + year_offset
            
            if escalation_year in self.escalation_factors["labor"]:
                labor_factor = self.escalation_factors["labor"][escalation_year]
                escalated_labor *= labor_factor
            
            if escalation_year in self.escalation_factors["materials"]:
                materials_factor = self.escalation_factors["materials"][escalation_year]
                escalated_materials *= materials_factor
        
        return {
            "labor": {
                "total": escalated_labor,
                "categories": labor_costs["categories"],
                "escalation_applied": True,
                "escalation_years": years_in_contract
            },
            "materials": {
                "total": escalated_materials,
                "items": material_costs["items"],
                "escalation_applied": True,
                "escalation_years": years_in_contract
            }
        }

    async def _calculate_profit_fee(self, subtotal: Decimal, contract_type: str) -> Dict[str, Any]:
        """Calculate profit/fee based on contract type"""
        if contract_type == "cost_plus":
            fee_rate = self.indirect_rates["profit_fee_cost_plus"]
        else:
            fee_rate = self.indirect_rates["profit_fee_fixed_price"]
        
        fee_amount = subtotal * fee_rate
        
        return {
            "rate": fee_rate,
            "amount": fee_amount,
            "contract_type": contract_type
        }

    async def _perform_competitive_analysis(self, proposal_id: str, 
                                          our_price: Decimal,
                                          contract_opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Perform competitive analysis"""
        # Simulate competitive intelligence
        competitors = [
            {
                "name": "TechCorp Solutions",
                "estimated_price": float(our_price * Decimal('0.95')),
                "strengths": ["Lower overhead", "Established presence"],
                "weaknesses": ["Limited technical depth"],
                "win_probability": 0.25
            },
            {
                "name": "Government Systems Inc",
                "estimated_price": float(our_price * Decimal('1.08')),
                "strengths": ["Past performance", "Technical expertise"],
                "weaknesses": ["Higher rates"],
                "win_probability": 0.20
            },
            {
                "name": "Federal Solutions LLC",
                "estimated_price": float(our_price * Decimal('0.88')),
                "strengths": ["Aggressive pricing", "Small business"],
                "weaknesses": ["Limited capacity"],
                "win_probability": 0.30
            }
        ]
        
        # Calculate our position
        competitor_prices = [c["estimated_price"] for c in competitors]
        our_price_float = float(our_price)
        
        price_rank = sum(1 for price in competitor_prices if price < our_price_float) + 1
        
        return {
            "our_price": our_price_float,
            "our_rank": price_rank,
            "total_competitors": len(competitors),
            "competitors": competitors,
            "market_average": sum(competitor_prices) / len(competitor_prices),
            "price_spread": {
                "lowest": min(competitor_prices + [our_price_float]),
                "highest": max(competitor_prices + [our_price_float]),
                "range_percentage": ((max(competitor_prices) - min(competitor_prices)) / min(competitor_prices)) * 100
            }
        }

    async def _analyze_price_to_win(self, proposal_id: str, 
                                   current_price: Decimal,
                                   competitive_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze price-to-win scenarios"""
        scenarios = []
        
        # Get competitive price points
        competitor_prices = [c["estimated_price"] for c in competitive_analysis["competitors"]]
        market_low = min(competitor_prices)
        market_avg = competitive_analysis["market_average"]
        
        # Generate scenarios
        scenarios.append({
            "name": "Aggressive Pricing",
            "price": market_low * 0.95,
            "win_probability": 0.65,
            "profit_margin": self._calculate_margin_at_price(current_price, market_low * 0.95),
            "risk_level": "HIGH",
            "recommended": False,
            "notes": "Below market minimum, high execution risk"
        })
        
        scenarios.append({
            "name": "Competitive Pricing",
            "price": market_low * 1.02,
            "win_probability": 0.45,
            "profit_margin": self._calculate_margin_at_price(current_price, market_low * 1.02),
            "risk_level": "MEDIUM",
            "recommended": True,
            "notes": "Slightly above lowest competitor, good balance"
        })
        
        scenarios.append({
            "name": "Market Average",
            "price": market_avg,
            "win_probability": 0.30,
            "profit_margin": self._calculate_margin_at_price(current_price, market_avg),
            "risk_level": "LOW",
            "recommended": False,
            "notes": "Safe pricing but lower win probability"
        })
        
        scenarios.append({
            "name": "Current Proposal",
            "price": float(current_price),
            "win_probability": 0.25,
            "profit_margin": self._calculate_margin_at_price(current_price, current_price),
            "risk_level": "LOW",
            "recommended": False,
            "notes": "Full cost recovery, lowest win chance"
        })
        
        # Find recommended scenario
        recommended_scenario = next((s for s in scenarios if s["recommended"]), scenarios[0])
        
        return {
            "scenarios": scenarios,
            "recommended_price": recommended_scenario["price"],
            "recommended_scenario": recommended_scenario["name"],
            "price_reduction_needed": float(current_price) - recommended_scenario["price"],
            "win_probability_improvement": recommended_scenario["win_probability"] - 0.25
        }

    def _calculate_margin_at_price(self, cost_price: Decimal, target_price: float) -> float:
        """Calculate profit margin at target price"""
        if target_price <= 0:
            return -100.0
        
        margin = (target_price - float(cost_price)) / target_price * 100
        return round(margin, 2)

    async def _assess_pricing_risks(self, total_price: Decimal, 
                                   competitive_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Assess pricing risks"""
        risks = []
        risk_score = 0
        
        # Price competitiveness risk
        our_rank = competitive_analysis["our_rank"]
        if our_rank > 2:
            risks.append({
                "category": "Price Competitiveness",
                "level": "HIGH",
                "description": f"Ranked #{our_rank} out of {competitive_analysis['total_competitors'] + 1} bidders",
                "mitigation": "Consider value engineering or pricing strategy adjustment"
            })
            risk_score += 30
        
        # Technical risk
        risks.append({
            "category": "Technical Execution",
            "level": "MEDIUM",
            "description": "Complex technical requirements may impact cost",
            "mitigation": "Detailed technical risk assessment and contingency planning"
        })
        risk_score += 20
        
        # Performance risk
        risks.append({
            "category": "Performance Period",
            "level": "MEDIUM", 
            "description": "Multi-year performance increases execution risk",
            "mitigation": "Strong project management and milestone tracking"
        })
        risk_score += 15
        
        return {
            "overall_risk_score": risk_score,
            "risk_level": "HIGH" if risk_score > 60 else "MEDIUM" if risk_score > 30 else "LOW",
            "identified_risks": risks,
            "mitigation_plan": [
                "Regular competitive intelligence monitoring",
                "Robust project management processes",
                "Active risk management program",
                "Strong subcontractor management"
            ]
        }

    async def _generate_pricing_recommendations(self, total_price: Decimal,
                                              competitive_analysis: Dict[str, Any],
                                              price_to_win: Dict[str, Any]) -> List[str]:
        """Generate pricing recommendations"""
        recommendations = []
        
        our_rank = competitive_analysis["our_rank"]
        recommended_price = price_to_win["recommended_price"]
        
        if our_rank > 2:
            recommendations.append(f"Consider pricing adjustment to ${recommended_price:,.2f} to improve competitiveness")
        
        if price_to_win["price_reduction_needed"] > 0:
            recommendations.append("Explore value engineering opportunities to reduce costs")
        
        recommendations.extend([
            "Strengthen technical proposal to justify pricing premium",
            "Emphasize past performance and team qualifications",
            "Consider teaming arrangements to improve competitive position",
            "Develop robust risk management plan",
            "Prepare comprehensive cost volume analysis",
            "Plan for potential contract negotiations"
        ])
        
        return recommendations

    async def _store_proposal(self, proposal_id: str, contract_opportunity: Dict[str, Any],
                             labor_costs: Dict[str, Any], indirect_costs: Dict[str, Any],
                             material_costs: Dict[str, Any], subcontractor_costs: Dict[str, Any],
                             travel_costs: Dict[str, Any], profit_fee: Dict[str, Any],
                             total_value: Decimal, pricing_strategy: str):
        """Store proposal in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO cost_proposals (
                id, rfp_id, proposal_name, contract_type, performance_period_months,
                pricing_strategy, total_contract_value, direct_labor_cost,
                indirect_cost, material_cost, subcontractor_cost, travel_cost,
                overhead_rate, ga_rate, profit_fee_rate, profit_fee_amount,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            proposal_id, contract_opportunity.get("rfp_id"),
            contract_opportunity.get("title", "Untitled Proposal"),
            contract_opportunity.get("contract_type", "fixed_price"),
            contract_opportunity.get("performance_period_months", 12),
            pricing_strategy, float(total_value),
            float(labor_costs["total"]), float(indirect_costs["total"]),
            float(material_costs["total"]), float(subcontractor_costs["total"]),
            float(travel_costs["total"]), float(self.indirect_rates["overhead"]),
            float(self.indirect_rates["general_admin"]), float(profit_fee["rate"]),
            float(profit_fee["amount"]), now, now
        ))
        
        conn.commit()
        conn.close()

    async def get_pricing_breakdown(self, proposal_id: str) -> Dict[str, Any]:
        """Get detailed pricing breakdown for proposal"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM cost_proposals WHERE id = ?", (proposal_id,))
            proposal = cursor.fetchone()
            
            if not proposal:
                return {"error": "Proposal not found"}
            
            # Get labor details
            cursor.execute("SELECT * FROM labor_estimates WHERE proposal_id = ?", (proposal_id,))
            labor_details = []
            for row in cursor.fetchall():
                labor_details.append({
                    "labor_category": row[2],
                    "base_rate": row[3],
                    "loaded_rate": row[4],
                    "total_hours": row[10],
                    "total_cost": row[11]
                })
            
            # Get material details
            cursor.execute("SELECT * FROM material_estimates WHERE proposal_id = ?", (proposal_id,))
            material_details = []
            for row in cursor.fetchall():
                material_details.append({
                    "description": row[2],
                    "quantity": row[4],
                    "unit_cost": row[5],
                    "total_cost": row[6]
                })
            
            conn.close()
            
            return {
                "proposal_id": proposal_id,
                "total_contract_value": proposal[7],
                "cost_breakdown": {
                    "direct_labor": proposal[8],
                    "indirect_costs": proposal[9],
                    "materials": proposal[10],
                    "subcontractors": proposal[11],
                    "travel": proposal[12],
                    "profit_fee": proposal[16]
                },
                "labor_details": labor_details,
                "material_details": material_details,
                "rates": {
                    "overhead_rate": proposal[13],
                    "ga_rate": proposal[14],
                    "profit_fee_rate": proposal[15]
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting pricing breakdown: {e}")
            return {"error": str(e)}

    async def update_pricing(self, proposal_id: str, pricing_updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update proposal pricing"""
        try:
            # Regenerate proposal with updated parameters
            updated_proposal = await self.generate_proposal(pricing_updates)
            
            # Update database record
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE cost_proposals 
                SET total_contract_value = ?, updated_at = ?, version = version + 1
                WHERE id = ?
            """, (
                updated_proposal.get("total_contract_value", 0),
                datetime.now().isoformat(),
                proposal_id
            ))
            
            conn.commit()
            conn.close()
            
            return updated_proposal
            
        except Exception as e:
            logger.error(f"Error updating pricing: {e}")
            return {"error": str(e)}

# Global instance
proposal_system = CostProposalSystem()