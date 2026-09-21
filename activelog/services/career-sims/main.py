#!/usr/bin/env python3
"""
Maritime Career Simulations - Professional Development Games
Educational career progression games focusing on maritime and logistics industries
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging
import math
import random

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, BackgroundTasks
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse, JSONResponse
    import uvicorn
except ImportError:
    print("Warning: FastAPI not installed. Install with: pip install fastapi uvicorn websockets")
    FastAPI = None

# Game Configuration
GAME_CONFIG = {
    "max_players_per_race": 12,
    "race_duration": 300,  # 5 minutes
    "skill_tree_max_level": 50,
    "failure_recovery_bonus": 0.15,
    "industry_update_interval": 30,
    "leaderboard_update_interval": 60
}

class CareerType(Enum):
    FISHING = "fishing"
    TOURISM = "tourism"
    SHIPYARD = "shipyard"
    FREIGHT = "freight"

class DifficultyLevel(Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"
    MASTER = "master"

class EventType(Enum):
    WEATHER_CHANGE = "weather_change"
    MARKET_FLUCTUATION = "market_fluctuation"
    EQUIPMENT_FAILURE = "equipment_failure"
    REGULATORY_CHANGE = "regulatory_change"
    SEASONAL_DEMAND = "seasonal_demand"
    CRISIS_EVENT = "crisis_event"

@dataclass
class Player:
    id: str
    name: str
    career: CareerType
    level: int = 1
    experience: int = 0
    money: float = 10000.0
    reputation: int = 50
    skills: Dict[str, int] = field(default_factory=dict)
    assets: Dict[str, Any] = field(default_factory=dict)
    current_position: str = "entry_level"
    failures: int = 0
    recoveries: int = 0
    achievements: List[str] = field(default_factory=list)
    statistics: Dict[str, float] = field(default_factory=dict)
    last_active: datetime = field(default_factory=datetime.utcnow)
    race_position: int = 0
    race_score: float = 0.0

@dataclass
class CareerPath:
    id: str
    name: str
    positions: List[Dict[str, Any]]
    requirements: Dict[str, Dict[str, Any]]
    salary_progression: Dict[str, float]
    skill_bonuses: Dict[str, Dict[str, float]]
    industry_mechanics: Dict[str, Any]
    tooltips: Dict[str, str]

@dataclass
class IndustryEvent:
    id: str
    type: EventType
    title: str
    description: str
    impact: Dict[str, float]
    duration: int
    probability: float
    educational_content: str

@dataclass
class SkillNode:
    id: str
    name: str
    description: str
    max_level: int
    cost_formula: str
    prerequisites: List[str]
    effects: Dict[str, str]
    career_specific: List[CareerType]

class CareerSimulationManager:
    def __init__(self):
        self.players: Dict[str, Player] = {}
        self.active_connections: Dict[str, WebSocket] = {}
        self.career_paths = self._initialize_career_paths()
        self.skill_trees = self._initialize_skill_trees()
        self.industry_events = self._initialize_industry_events()
        self.active_events: Dict[str, IndustryEvent] = {}
        self.leaderboards: Dict[CareerType, List[Dict[str, Any]]] = {career: [] for career in CareerType}
        self.current_races: Dict[str, Dict[str, Any]] = {}
        self.race_results: List[Dict[str, Any]] = []
        self._background_tasks_started = False
    
    async def start_background_tasks(self):
        """Start background tasks when event loop is available"""
        if not self._background_tasks_started:
            asyncio.create_task(self._industry_update_loop())
            asyncio.create_task(self._leaderboard_update_loop())
            self._background_tasks_started = True
        
    def _initialize_career_paths(self) -> Dict[CareerType, CareerPath]:
        """Initialize all career progression paths"""
        return {
            CareerType.FISHING: CareerPath(
                id="fishing_career",
                name="Commercial Fishing Career",
                positions=[
                    {"id": "deckhand", "name": "Deckhand", "level": 1, "description": "Learn the basics of commercial fishing"},
                    {"id": "able_seaman", "name": "Able Seaman", "level": 5, "description": "Experienced crew member with specialized skills"},
                    {"id": "mate", "name": "First Mate", "level": 15, "description": "Second-in-command, responsible for crew and operations"},
                    {"id": "captain", "name": "Fishing Captain", "level": 25, "description": "Command your own fishing vessel"},
                    {"id": "fleet_manager", "name": "Fleet Manager", "level": 40, "description": "Manage multiple vessels and crews"},
                    {"id": "fleet_owner", "name": "Fleet Owner", "level": 50, "description": "Own and operate a commercial fishing empire"}
                ],
                requirements={
                    "deckhand": {"experience": 0, "skills": {}},
                    "able_seaman": {"experience": 1000, "skills": {"seamanship": 3, "fishing_techniques": 2}},
                    "mate": {"experience": 5000, "skills": {"leadership": 5, "navigation": 4, "seamanship": 6}},
                    "captain": {"experience": 15000, "skills": {"leadership": 8, "navigation": 7, "business": 4}},
                    "fleet_manager": {"experience": 35000, "skills": {"leadership": 12, "business": 8, "logistics": 6}},
                    "fleet_owner": {"experience": 75000, "skills": {"business": 15, "leadership": 15, "finance": 10}}
                },
                salary_progression={
                    "deckhand": 35000, "able_seaman": 45000, "mate": 65000,
                    "captain": 95000, "fleet_manager": 150000, "fleet_owner": 500000
                },
                skill_bonuses={
                    "deckhand": {"fishing_techniques": 1.1, "physical_endurance": 1.2},
                    "able_seaman": {"seamanship": 1.2, "equipment_maintenance": 1.15},
                    "mate": {"leadership": 1.3, "crew_management": 1.25},
                    "captain": {"navigation": 1.4, "weather_prediction": 1.3},
                    "fleet_manager": {"logistics": 1.5, "resource_optimization": 1.4},
                    "fleet_owner": {"business": 1.6, "market_analysis": 1.5}
                },
                industry_mechanics={
                    "seasonal_cycles": True,
                    "weather_dependency": 0.8,
                    "quota_systems": True,
                    "market_volatility": 0.6,
                    "equipment_wear": 0.4
                },
                tooltips={
                    "seasonal_cycles": "Fish populations vary by season. Plan your operations around migration patterns and breeding seasons.",
                    "weather_dependency": "Weather conditions greatly affect fishing success and safety. Monitor forecasts and plan accordingly.",
                    "quota_systems": "Government regulations limit how much you can catch to ensure sustainable fishing practices.",
                    "market_volatility": "Fish prices fluctuate based on supply, demand, and seasonal factors.",
                    "equipment_wear": "Fishing equipment requires regular maintenance. Well-maintained gear performs better and lasts longer."
                }
            ),
            
            CareerType.TOURISM: CareerPath(
                id="tourism_career",
                name="Marine Tourism Career",
                positions=[
                    {"id": "tour_guide", "name": "Marine Tour Guide", "level": 1, "description": "Lead tourists on marine adventures"},
                    {"id": "dive_instructor", "name": "Dive Instructor", "level": 8, "description": "Teach scuba diving and lead underwater tours"},
                    {"id": "charter_captain", "name": "Charter Boat Captain", "level": 18, "description": "Captain charter boats for fishing and sightseeing"},
                    {"id": "resort_manager", "name": "Marine Resort Manager", "level": 30, "description": "Manage waterfront resorts and marine activities"},
                    {"id": "tourism_director", "name": "Regional Tourism Director", "level": 45, "description": "Oversee tourism development for entire regions"},
                    {"id": "tourism_mogul", "name": "Tourism Empire Owner", "level": 60, "description": "Own multiple resorts and tourism operations"}
                ],
                requirements={
                    "tour_guide": {"experience": 0, "skills": {}},
                    "dive_instructor": {"experience": 2000, "skills": {"diving": 5, "safety": 4, "communication": 3}},
                    "charter_captain": {"experience": 8000, "skills": {"navigation": 6, "customer_service": 5, "seamanship": 7}},
                    "resort_manager": {"experience": 20000, "skills": {"hospitality": 8, "business": 6, "staff_management": 7}},
                    "tourism_director": {"experience": 45000, "skills": {"marketing": 10, "business": 12, "regional_planning": 8}},
                    "tourism_mogul": {"experience": 90000, "skills": {"business": 18, "finance": 12, "strategic_planning": 15}}
                },
                salary_progression={
                    "tour_guide": 28000, "dive_instructor": 42000, "charter_captain": 68000,
                    "resort_manager": 120000, "tourism_director": 200000, "tourism_mogul": 800000
                },
                skill_bonuses={
                    "tour_guide": {"communication": 1.2, "local_knowledge": 1.3},
                    "dive_instructor": {"diving": 1.4, "safety": 1.3, "teaching": 1.2},
                    "charter_captain": {"navigation": 1.3, "customer_service": 1.4},
                    "resort_manager": {"hospitality": 1.5, "staff_management": 1.4},
                    "tourism_director": {"marketing": 1.6, "strategic_planning": 1.5},
                    "tourism_mogul": {"business": 1.7, "brand_development": 1.6}
                },
                industry_mechanics={
                    "seasonal_demand": True,
                    "weather_dependency": 0.7,
                    "customer_satisfaction": 0.9,
                    "competition_factor": 0.8,
                    "reputation_impact": 0.85
                },
                tooltips={
                    "seasonal_demand": "Tourism peaks during certain seasons. Plan capacity and pricing accordingly.",
                    "weather_dependency": "Bad weather can cancel tours and affect customer satisfaction.",
                    "customer_satisfaction": "Happy customers leave good reviews and return for more tours.",
                    "competition_factor": "Other tourism operators compete for the same customers.",
                    "reputation_impact": "Your reputation affects bookings and allows premium pricing."
                }
            ),
            
            CareerType.SHIPYARD: CareerPath(
                id="shipyard_career",
                name="Shipyard Management Career",
                positions=[
                    {"id": "apprentice", "name": "Shipyard Apprentice", "level": 1, "description": "Learn basic shipbuilding skills"},
                    {"id": "welder", "name": "Marine Welder", "level": 6, "description": "Specialize in marine welding and fabrication"},
                    {"id": "supervisor", "name": "Production Supervisor", "level": 16, "description": "Supervise shipbuilding teams and projects"},
                    {"id": "project_manager", "name": "Ship Project Manager", "level": 28, "description": "Manage entire ship construction projects"},
                    {"id": "shipyard_manager", "name": "Shipyard Manager", "level": 42, "description": "Oversee entire shipyard operations"},
                    {"id": "shipyard_owner", "name": "Shipyard Owner", "level": 55, "description": "Own and operate multiple shipyard facilities"}
                ],
                requirements={
                    "apprentice": {"experience": 0, "skills": {}},
                    "welder": {"experience": 1500, "skills": {"welding": 4, "blueprint_reading": 3, "safety": 3}},
                    "supervisor": {"experience": 6000, "skills": {"leadership": 5, "quality_control": 4, "project_management": 3}},
                    "project_manager": {"experience": 18000, "skills": {"project_management": 8, "engineering": 6, "budgeting": 5}},
                    "shipyard_manager": {"experience": 40000, "skills": {"operations": 10, "business": 8, "strategic_planning": 7}},
                    "shipyard_owner": {"experience": 80000, "skills": {"business": 15, "finance": 12, "industry_relations": 10}}
                },
                salary_progression={
                    "apprentice": 32000, "welder": 55000, "supervisor": 75000,
                    "project_manager": 110000, "shipyard_manager": 180000, "shipyard_owner": 600000
                },
                skill_bonuses={
                    "apprentice": {"learning_speed": 1.3, "basic_skills": 1.2},
                    "welder": {"welding": 1.4, "precision": 1.3},
                    "supervisor": {"quality_control": 1.4, "team_efficiency": 1.3},
                    "project_manager": {"timeline_management": 1.5, "cost_control": 1.4},
                    "shipyard_manager": {"operational_efficiency": 1.6, "capacity_optimization": 1.5},
                    "shipyard_owner": {"profit_margins": 1.7, "contract_negotiation": 1.6}
                },
                industry_mechanics={
                    "project_complexity": 0.9,
                    "material_costs": 0.8,
                    "deadline_pressure": 0.85,
                    "quality_standards": 0.9,
                    "regulatory_compliance": 0.95
                },
                tooltips={
                    "project_complexity": "Ship projects vary in complexity. More complex ships require higher skills but pay more.",
                    "material_costs": "Steel and other material prices fluctuate, affecting project profitability.",
                    "deadline_pressure": "Clients expect timely delivery. Delays can result in penalties.",
                    "quality_standards": "Ships must meet strict safety and quality standards.",
                    "regulatory_compliance": "Shipbuilding is heavily regulated. Stay current with maritime laws."
                }
            ),
            
            CareerType.FREIGHT: CareerPath(
                id="freight_career",
                name="Freight Logistics Career",
                positions=[
                    {"id": "dock_worker", "name": "Dock Worker", "level": 1, "description": "Handle cargo loading and unloading"},
                    {"id": "crane_operator", "name": "Crane Operator", "level": 7, "description": "Operate heavy machinery for cargo handling"},
                    {"id": "logistics_coordinator", "name": "Logistics Coordinator", "level": 17, "description": "Coordinate freight movements and schedules"},
                    {"id": "port_manager", "name": "Port Operations Manager", "level": 32, "description": "Manage port operations and efficiency"},
                    {"id": "logistics_director", "name": "Regional Logistics Director", "level": 47, "description": "Oversee logistics networks across regions"},
                    {"id": "shipping_mogul", "name": "Global Shipping Executive", "level": 65, "description": "Lead international shipping operations"}
                ],
                requirements={
                    "dock_worker": {"experience": 0, "skills": {}},
                    "crane_operator": {"experience": 1800, "skills": {"machinery_operation": 4, "precision": 3, "safety": 4}},
                    "logistics_coordinator": {"experience": 7500, "skills": {"logistics": 6, "communication": 5, "problem_solving": 4}},
                    "port_manager": {"experience": 22000, "skills": {"operations": 8, "efficiency_optimization": 6, "staff_management": 7}},
                    "logistics_director": {"experience": 50000, "skills": {"strategic_planning": 10, "network_optimization": 8, "business": 9}},
                    "shipping_mogul": {"experience": 100000, "skills": {"global_trade": 15, "finance": 13, "international_relations": 12}}
                },
                salary_progression={
                    "dock_worker": 38000, "crane_operator": 62000, "logistics_coordinator": 72000,
                    "port_manager": 130000, "logistics_director": 220000, "shipping_mogul": 750000
                },
                skill_bonuses={
                    "dock_worker": {"physical_endurance": 1.3, "teamwork": 1.2},
                    "crane_operator": {"precision": 1.4, "machinery_operation": 1.5},
                    "logistics_coordinator": {"route_optimization": 1.4, "scheduling": 1.3},
                    "port_manager": {"throughput_optimization": 1.5, "cost_reduction": 1.4},
                    "logistics_director": {"network_efficiency": 1.6, "capacity_planning": 1.5},
                    "shipping_mogul": {"global_optimization": 1.8, "market_penetration": 1.7}
                },
                industry_mechanics={
                    "cargo_volume": 0.8,
                    "fuel_costs": 0.75,
                    "port_congestion": 0.7,
                    "global_trade": 0.85,
                    "automation_impact": 0.6
                },
                tooltips={
                    "cargo_volume": "Global trade volumes affect demand for logistics services.",
                    "fuel_costs": "Fuel prices significantly impact transportation costs and profitability.",
                    "port_congestion": "Busy ports can cause delays and increase costs.",
                    "global_trade": "International trade policies affect shipping routes and volumes.",
                    "automation_impact": "Automation improves efficiency but requires investment and retraining."
                }
            )
        }
    
    def _initialize_skill_trees(self) -> Dict[str, SkillNode]:
        """Initialize comprehensive skill trees"""
        return {
            # Universal Skills
            "leadership": SkillNode(
                id="leadership",
                name="Leadership",
                description="Ability to lead teams and make decisions",
                max_level=20,
                cost_formula="level * 100 + level^2 * 10",
                prerequisites=[],
                effects={"team_efficiency": "1 + (level * 0.02)", "decision_speed": "1 + (level * 0.015)"},
                career_specific=list(CareerType)
            ),
            "business": SkillNode(
                id="business",
                name="Business Acumen",
                description="Understanding of business operations and strategy",
                max_level=20,
                cost_formula="level * 120 + level^2 * 15",
                prerequisites=[],
                effects={"profit_margin": "1 + (level * 0.025)", "cost_reduction": "1 + (level * 0.02)"},
                career_specific=list(CareerType)
            ),
            "communication": SkillNode(
                id="communication",
                name="Communication",
                description="Effective communication with clients and teams",
                max_level=15,
                cost_formula="level * 80 + level^2 * 8",
                prerequisites=[],
                effects={"customer_satisfaction": "1 + (level * 0.03)", "team_coordination": "1 + (level * 0.02)"},
                career_specific=list(CareerType)
            ),
            
            # Fishing-Specific Skills
            "seamanship": SkillNode(
                id="seamanship",
                name="Seamanship",
                description="Essential maritime skills and knowledge",
                max_level=15,
                cost_formula="level * 90 + level^2 * 12",
                prerequisites=[],
                effects={"safety_rating": "1 + (level * 0.04)", "efficiency": "1 + (level * 0.025)"},
                career_specific=[CareerType.FISHING]
            ),
            "fishing_techniques": SkillNode(
                id="fishing_techniques",
                name="Fishing Techniques",
                description="Advanced fishing methods and equipment usage",
                max_level=18,
                cost_formula="level * 95 + level^2 * 14",
                prerequisites=["seamanship"],
                effects={"catch_rate": "1 + (level * 0.035)", "fish_quality": "1 + (level * 0.02)"},
                career_specific=[CareerType.FISHING]
            ),
            "navigation": SkillNode(
                id="navigation",
                name="Navigation",
                description="Ship navigation and positioning skills",
                max_level=16,
                cost_formula="level * 85 + level^2 * 11",
                prerequisites=[],
                effects={"route_efficiency": "1 + (level * 0.03)", "fuel_savings": "1 + (level * 0.025)"},
                career_specific=[CareerType.FISHING, CareerType.TOURISM, CareerType.FREIGHT]
            ),
            
            # Tourism-Specific Skills
            "hospitality": SkillNode(
                id="hospitality",
                name="Hospitality",
                description="Customer service and guest satisfaction skills",
                max_level=17,
                cost_formula="level * 75 + level^2 * 9",
                prerequisites=[],
                effects={"guest_satisfaction": "1 + (level * 0.04)", "repeat_customers": "1 + (level * 0.03)"},
                career_specific=[CareerType.TOURISM]
            ),
            "diving": SkillNode(
                id="diving",
                name="Professional Diving",
                description="Advanced diving skills and underwater operations",
                max_level=14,
                cost_formula="level * 110 + level^2 * 16",
                prerequisites=["safety"],
                effects={"dive_safety": "1 + (level * 0.05)", "underwater_efficiency": "1 + (level * 0.03)"},
                career_specific=[CareerType.TOURISM]
            ),
            "marketing": SkillNode(
                id="marketing",
                name="Marketing & Promotion",
                description="Promote tourism services and attract customers",
                max_level=18,
                cost_formula="level * 100 + level^2 * 13",
                prerequisites=["communication"],
                effects={"brand_awareness": "1 + (level * 0.035)", "booking_rate": "1 + (level * 0.028)"},
                career_specific=[CareerType.TOURISM]
            ),
            
            # Shipyard-Specific Skills
            "welding": SkillNode(
                id="welding",
                name="Marine Welding",
                description="Specialized welding techniques for ship construction",
                max_level=16,
                cost_formula="level * 95 + level^2 * 13",
                prerequisites=["safety"],
                effects={"weld_quality": "1 + (level * 0.04)", "work_speed": "1 + (level * 0.025)"},
                career_specific=[CareerType.SHIPYARD]
            ),
            "engineering": SkillNode(
                id="engineering",
                name="Marine Engineering",
                description="Engineering principles for ship design and construction",
                max_level=20,
                cost_formula="level * 130 + level^2 * 18",
                prerequisites=[],
                effects={"design_efficiency": "1 + (level * 0.03)", "problem_solving": "1 + (level * 0.035)"},
                career_specific=[CareerType.SHIPYARD]
            ),
            "project_management": SkillNode(
                id="project_management",
                name="Project Management",
                description="Plan and execute complex shipbuilding projects",
                max_level=18,
                cost_formula="level * 115 + level^2 * 15",
                prerequisites=["leadership"],
                effects={"on_time_delivery": "1 + (level * 0.03)", "budget_control": "1 + (level * 0.025)"},
                career_specific=[CareerType.SHIPYARD, CareerType.FREIGHT]
            ),
            
            # Freight-Specific Skills
            "logistics": SkillNode(
                id="logistics",
                name="Logistics Optimization",
                description="Optimize cargo movements and supply chains",
                max_level=19,
                cost_formula="level * 105 + level^2 * 14",
                prerequisites=[],
                effects={"throughput": "1 + (level * 0.03)", "cost_efficiency": "1 + (level * 0.025)"},
                career_specific=[CareerType.FREIGHT]
            ),
            "machinery_operation": SkillNode(
                id="machinery_operation",
                name="Heavy Machinery Operation",
                description="Operate cranes, forklifts, and cargo handling equipment",
                max_level=15,
                cost_formula="level * 90 + level^2 * 12",
                prerequisites=["safety"],
                effects={"operational_speed": "1 + (level * 0.035)", "accident_prevention": "1 + (level * 0.04)"},
                career_specific=[CareerType.FREIGHT, CareerType.SHIPYARD]
            ),
            "global_trade": SkillNode(
                id="global_trade",
                name="International Trade",
                description="Understanding global trade patterns and regulations",
                max_level=17,
                cost_formula="level * 140 + level^2 * 20",
                prerequisites=["business", "communication"],
                effects={"route_optimization": "1 + (level * 0.025)", "regulatory_compliance": "1 + (level * 0.03)"},
                career_specific=[CareerType.FREIGHT]
            ),
            
            # Universal Advanced Skills
            "safety": SkillNode(
                id="safety",
                name="Safety Management",
                description="Workplace safety and risk management",
                max_level=15,
                cost_formula="level * 70 + level^2 * 8",
                prerequisites=[],
                effects={"accident_reduction": "1 + (level * 0.05)", "insurance_savings": "1 + (level * 0.02)"},
                career_specific=list(CareerType)
            ),
            "finance": SkillNode(
                id="finance",
                name="Financial Management",
                description="Financial planning and investment strategies",
                max_level=18,
                cost_formula="level * 125 + level^2 * 17",
                prerequisites=["business"],
                effects={"investment_returns": "1 + (level * 0.025)", "cash_flow": "1 + (level * 0.02)"},
                career_specific=list(CareerType)
            )
        }
    
    def _initialize_industry_events(self) -> List[IndustryEvent]:
        """Initialize realistic industry events"""
        return [
            IndustryEvent(
                id="storm_season",
                type=EventType.WEATHER_CHANGE,
                title="Storm Season Approaches",
                description="Severe weather conditions are forecasted for the next few weeks.",
                impact={"safety_risk": 1.8, "operational_efficiency": 0.6, "insurance_costs": 1.3},
                duration=14,
                probability=0.15,
                educational_content="Storm seasons require careful planning. Experienced mariners know to prepare equipment, secure assets, and sometimes suspend operations for safety."
            ),
            IndustryEvent(
                id="fuel_price_spike",
                type=EventType.MARKET_FLUCTUATION,
                title="Fuel Price Increase",
                description="Oil prices have risen significantly due to global supply constraints.",
                impact={"operational_costs": 1.4, "profit_margins": 0.75, "customer_prices": 1.15},
                duration=30,
                probability=0.2,
                educational_content="Fuel costs are a major expense in maritime operations. Smart operators hedge fuel prices or invest in fuel-efficient technologies."
            ),
            IndustryEvent(
                id="equipment_recall",
                type=EventType.EQUIPMENT_FAILURE,
                title="Safety Equipment Recall",
                description="A major manufacturer has recalled safety equipment due to defects.",
                impact={"safety_rating": 0.8, "equipment_costs": 1.25, "operational_delays": 1.2},
                duration=21,
                probability=0.08,
                educational_content="Equipment failures highlight the importance of regular maintenance and having backup systems. Quality equipment saves money long-term."
            ),
            IndustryEvent(
                id="new_regulations",
                type=EventType.REGULATORY_CHANGE,
                title="New Environmental Regulations",
                description="Government has implemented stricter environmental protection measures.",
                impact={"compliance_costs": 1.35, "operational_restrictions": 1.2, "reputation_bonus": 1.1},
                duration=365,
                probability=0.12,
                educational_content="Maritime industries are increasingly regulated for environmental protection. Proactive compliance can become a competitive advantage."
            ),
            IndustryEvent(
                id="tourism_boom",
                type=EventType.SEASONAL_DEMAND,
                title="Tourism Season Peak",
                description="Tourist season is reaching its peak with high demand for marine activities.",
                impact={"demand": 1.6, "prices": 1.3, "competition": 1.4},
                duration=45,
                probability=0.25,
                educational_content="Tourism has predictable seasonal patterns. Successful operators plan capacity and pricing to maximize revenue during peak periods."
            ),
            IndustryEvent(
                id="port_strike",
                type=EventType.CRISIS_EVENT,
                title="Port Workers Strike",
                description="Labor disputes have led to strikes at major ports, causing delays.",
                impact={"cargo_delays": 2.5, "alternative_routes": 1.8, "costs": 1.4},
                duration=12,
                probability=0.06,
                educational_content="Labor disputes can severely disrupt logistics. Diversified operations and good labor relations help mitigate these risks."
            ),
            IndustryEvent(
                id="fish_shortage",
                type=EventType.MARKET_FLUCTUATION,
                title="Fish Stock Depletion",
                description="Overfishing has led to reduced fish populations in traditional fishing grounds.",
                impact={"catch_rates": 0.4, "prices": 1.8, "travel_distances": 1.6},
                duration=180,
                probability=0.18,
                educational_content="Sustainable fishing practices ensure long-term viability. Overfishing destroys the resource base that the industry depends on."
            ),
            IndustryEvent(
                id="tech_breakthrough",
                type=EventType.MARKET_FLUCTUATION,
                title="New Navigation Technology",
                description="Advanced GPS and sonar systems have become available, improving efficiency.",
                impact={"efficiency": 1.25, "technology_costs": 1.5, "competitive_advantage": 1.3},
                duration=90,
                probability=0.1,
                educational_content="Technology adoption can provide competitive advantages. Early adopters often capture market share, but timing and cost-benefit analysis are crucial."
            )
        ]
    
    async def _industry_update_loop(self):
        """Background task to update industry conditions"""
        while True:
            await asyncio.sleep(GAME_CONFIG["industry_update_interval"])
            
            # Remove expired events
            expired_events = []
            for event_id, event in self.active_events.items():
                if hasattr(event, 'expires_at') and datetime.utcnow() > event.expires_at:
                    expired_events.append(event_id)
            
            for event_id in expired_events:
                del self.active_events[event_id]
                await self._broadcast_to_all({
                    "type": "industry_event_ended",
                    "event_id": event_id
                })
            
            # Check for new events
            for event in self._initialize_industry_events():
                if event.id not in self.active_events and random.random() < event.probability:
                    event.expires_at = datetime.utcnow() + timedelta(days=event.duration)
                    self.active_events[event.id] = event
                    
                    await self._broadcast_to_all({
                        "type": "industry_event_started",
                        "event": asdict(event),
                        "educational_tooltip": event.educational_content
                    })
    
    async def _leaderboard_update_loop(self):
        """Background task to update leaderboards"""
        while True:
            await asyncio.sleep(GAME_CONFIG["leaderboard_update_interval"])
            await self._update_leaderboards()
    
    async def _update_leaderboards(self):
        """Update all career leaderboards"""
        for career in CareerType:
            career_players = [p for p in self.players.values() if p.career == career]
            
            # Sort by multiple criteria: level, experience, money, reputation
            career_players.sort(key=lambda p: (
                p.level * 1000000 + 
                p.experience * 100 + 
                p.money + 
                p.reputation * 10000
            ), reverse=True)
            
            self.leaderboards[career] = [
                {
                    "rank": i + 1,
                    "player_name": p.name,
                    "level": p.level,
                    "position": p.current_position,
                    "experience": p.experience,
                    "money": p.money,
                    "reputation": p.reputation,
                    "achievements": len(p.achievements)
                }
                for i, p in enumerate(career_players[:50])  # Top 50
            ]
        
        # Broadcast updated leaderboards
        await self._broadcast_to_all({
            "type": "leaderboards_updated",
            "leaderboards": {career.value: board for career, board in self.leaderboards.items()}
        })
    
    def calculate_experience_required(self, current_level: int) -> int:
        """Calculate experience required for next level"""
        return int(1000 * (current_level ** 1.5) + 500 * current_level)
    
    def check_level_up(self, player: Player) -> bool:
        """Check if player should level up"""
        required_exp = self.calculate_experience_required(player.level)
        if player.experience >= required_exp:
            player.level += 1
            player.experience -= required_exp
            return True
        return False
    
    def check_promotion(self, player: Player) -> Optional[str]:
        """Check if player qualifies for promotion"""
        career_path = self.career_paths[player.career]
        current_position_index = next(
            (i for i, pos in enumerate(career_path.positions) if pos["id"] == player.current_position),
            0
        )
        
        if current_position_index + 1 < len(career_path.positions):
            next_position = career_path.positions[current_position_index + 1]
            requirements = career_path.requirements[next_position["id"]]
            
            # Check level requirement
            if player.level >= next_position["level"]:
                # Check experience requirement
                if player.experience >= requirements.get("experience", 0):
                    # Check skill requirements
                    skill_requirements_met = True
                    for skill, required_level in requirements.get("skills", {}).items():
                        if player.skills.get(skill, 0) < required_level:
                            skill_requirements_met = False
                            break
                    
                    if skill_requirements_met:
                        return next_position["id"]
        
        return None
    
    def apply_industry_modifiers(self, player: Player, base_value: float, modifier_type: str) -> float:
        """Apply current industry event modifiers"""
        modified_value = base_value
        
        for event in self.active_events.values():
            if modifier_type in event.impact:
                modified_value *= event.impact[modifier_type]
        
        return modified_value
    
    def simulate_work_outcome(self, player: Player, task_type: str) -> Dict[str, Any]:
        """Simulate work performance based on player skills and random factors"""
        career_path = self.career_paths[player.career]
        base_performance = 0.7  # Base 70% performance
        
        # Apply skill bonuses
        for skill_id, skill_level in player.skills.items():
            if skill_id in self.skill_trees:
                skill_node = self.skill_trees[skill_id]
                for effect_name, effect_formula in skill_node.effects.items():
                    if effect_name in task_type:
                        # Simple formula evaluation
                        skill_bonus = 1 + (skill_level * 0.02)
                        base_performance *= skill_bonus
        
        # Apply position bonuses
        position_bonuses = career_path.skill_bonuses.get(player.current_position, {})
        for bonus_type, multiplier in position_bonuses.items():
            if bonus_type in task_type:
                base_performance *= multiplier
        
        # Apply industry event modifiers
        base_performance = self.apply_industry_modifiers(player, base_performance, "efficiency")
        
        # Add some randomness (±20%)
        performance = base_performance * (0.8 + random.random() * 0.4)
        
        # Calculate rewards based on performance
        base_exp = 50
        base_money = career_path.salary_progression[player.current_position] / 365  # Daily wage
        
        experience_gained = int(base_exp * performance)
        money_earned = base_money * performance
        reputation_change = int((performance - 0.8) * 10) if performance > 0.8 else -1
        
        # Check for failures (low performance)
        failure_occurred = performance < 0.5
        if failure_occurred:
            player.failures += 1
            reputation_change = -5
        
        return {
            "performance": performance,
            "experience_gained": experience_gained,
            "money_earned": money_earned,
            "reputation_change": reputation_change,
            "failure_occurred": failure_occurred,
            "industry_modifiers_applied": len(self.active_events)
        }
    
    def handle_failure_recovery(self, player: Player, failure_type: str) -> Dict[str, Any]:
        """Handle failure recovery mechanics"""
        recovery_options = []
        
        if failure_type == "equipment_failure":
            recovery_options = [
                {
                    "id": "emergency_repair",
                    "name": "Emergency Repair",
                    "cost": player.money * 0.1,
                    "time": 2,
                    "success_rate": 0.8,
                    "bonus": "equipment_reliability"
                },
                {
                    "id": "professional_service",
                    "name": "Professional Service",
                    "cost": player.money * 0.2,
                    "time": 4,
                    "success_rate": 0.95,
                    "bonus": "maintenance_knowledge"
                }
            ]
        elif failure_type == "market_loss":
            recovery_options = [
                {
                    "id": "diversify_services",
                    "name": "Diversify Services",
                    "cost": player.money * 0.15,
                    "time": 7,
                    "success_rate": 0.75,
                    "bonus": "market_resilience"
                },
                {
                    "id": "strategic_partnership",
                    "name": "Form Strategic Partnership",
                    "cost": player.reputation * 10,
                    "time": 5,
                    "success_rate": 0.85,
                    "bonus": "network_strength"
                }
            ]
        
        return {
            "failure_type": failure_type,
            "recovery_options": recovery_options,
            "educational_tip": f"Failures are learning opportunities. The maritime industry rewards those who can adapt and recover quickly."
        }
    
    async def start_career_race(self, race_id: str, participants: List[str], duration: int = 300):
        """Start a multiplayer career race"""
        race_data = {
            "id": race_id,
            "participants": participants,
            "start_time": datetime.utcnow(),
            "duration": duration,
            "status": "active",
            "scores": {player_id: 0 for player_id in participants}
        }
        
        self.current_races[race_id] = race_data
        
        # Notify all participants
        for player_id in participants:
            if player_id in self.active_connections:
                await self._send_player_message(player_id, {
                    "type": "race_started",
                    "race_id": race_id,
                    "duration": duration,
                    "participants": len(participants)
                })
        
        # Set race end timer
        asyncio.create_task(self._end_race_timer(race_id, duration))
    
    async def _end_race_timer(self, race_id: str, duration: int):
        """End race after specified duration"""
        await asyncio.sleep(duration)
        
        if race_id in self.current_races:
            await self._end_career_race(race_id)
    
    async def _end_career_race(self, race_id: str):
        """End a career race and determine winners"""
        if race_id not in self.current_races:
            return
        
        race_data = self.current_races[race_id]
        race_data["status"] = "completed"
        race_data["end_time"] = datetime.utcnow()
        
        # Calculate final scores and rankings
        participant_scores = []
        for player_id in race_data["participants"]:
            if player_id in self.players:
                player = self.players[player_id]
                final_score = race_data["scores"][player_id]
                participant_scores.append({
                    "player_id": player_id,
                    "player_name": player.name,
                    "score": final_score,
                    "level_gained": player.level - player.statistics.get("race_start_level", 1),
                    "money_earned": player.money - player.statistics.get("race_start_money", 10000)
                })
        
        # Sort by score
        participant_scores.sort(key=lambda x: x["score"], reverse=True)
        
        # Assign rankings and rewards
        for i, participant in enumerate(participant_scores):
            rank = i + 1
            player_id = participant["player_id"]
            
            if player_id in self.players:
                player = self.players[player_id]
                player.race_position = rank
                
                # Award race completion bonuses
                if rank == 1:
                    bonus_money = 5000
                    bonus_exp = 1000
                    achievement = "race_champion"
                elif rank <= 3:
                    bonus_money = 2500
                    bonus_exp = 500
                    achievement = "race_podium"
                else:
                    bonus_money = 1000
                    bonus_exp = 250
                    achievement = "race_participant"
                
                player.money += bonus_money
                player.experience += bonus_exp
                
                if achievement not in player.achievements:
                    player.achievements.append(achievement)
        
        # Store race results
        self.race_results.append({
            "race_id": race_id,
            "completed_at": race_data["end_time"],
            "duration": race_data["duration"],
            "results": participant_scores
        })
        
        # Notify all participants of results
        for player_id in race_data["participants"]:
            if player_id in self.active_connections:
                await self._send_player_message(player_id, {
                    "type": "race_completed",
                    "race_id": race_id,
                    "results": participant_scores,
                    "your_rank": next(p["rank"] if "rank" in p else i+1 
                                    for i, p in enumerate(participant_scores) 
                                    if p["player_id"] == player_id)
                })
        
        # Clean up
        del self.current_races[race_id]
    
    async def add_player(self, websocket: WebSocket, player_data: Dict[str, Any]) -> str:
        """Add a new player to the game"""
        player_id = str(uuid.uuid4())
        career = CareerType(player_data.get("career", "fishing"))
        
        player = Player(
            id=player_id,
            name=player_data.get("name", f"Player_{player_id[:8]}"),
            career=career
        )
        
        # Initialize career-specific skills
        career_skills = [skill for skill_id, skill in self.skill_trees.items() 
                        if career in skill.career_specific]
        
        for skill in career_skills:
            player.skills[skill.id] = 0
        
        self.players[player_id] = player
        self.active_connections[player_id] = websocket
        
        await self._send_player_message(player_id, {
            "type": "welcome",
            "player": asdict(player),
            "career_path": asdict(self.career_paths[career]),
            "available_skills": {skill_id: asdict(skill) for skill_id, skill in self.skill_trees.items() 
                              if career in skill.career_specific},
            "active_events": {event_id: asdict(event) for event_id, event in self.active_events.items()},
            "educational_tip": "Welcome to your maritime career! Click on tooltips to learn about industry mechanics."
        })
        
        return player_id
    
    async def handle_game_action(self, player_id: str, action: Dict[str, Any]):
        """Handle game actions from players"""
        if player_id not in self.players:
            return
        
        player = self.players[player_id]
        action_type = action.get("type")
        
        if action_type == "work_shift":
            await self._handle_work_shift(player, action)
        elif action_type == "upgrade_skill":
            await self._handle_skill_upgrade(player, action)
        elif action_type == "apply_promotion":
            await self._handle_promotion_application(player)
        elif action_type == "handle_failure":
            await self._handle_failure_recovery_action(player, action)
        elif action_type == "join_race":
            await self._handle_race_join(player, action)
        elif action_type == "get_career_visualization":
            await self._send_career_visualization(player)
        elif action_type == "request_tooltip":
            await self._send_educational_tooltip(player, action)
    
    async def _handle_work_shift(self, player: Player, action: Dict[str, Any]):
        """Handle a work shift simulation"""
        task_type = action.get("task_type", "general_work")
        outcome = self.simulate_work_outcome(player, task_type)
        
        # Apply results
        player.experience += outcome["experience_gained"]
        player.money += outcome["money_earned"]
        player.reputation = max(0, min(100, player.reputation + outcome["reputation_change"]))
        
        # Update statistics
        player.statistics["total_shifts"] = player.statistics.get("total_shifts", 0) + 1
        player.statistics["total_earnings"] = player.statistics.get("total_earnings", 0) + outcome["money_earned"]
        
        # Check for level up
        level_up = self.check_level_up(player)
        
        # Check for promotion
        promotion = self.check_promotion(player)
        
        response = {
            "type": "work_shift_result",
            "outcome": outcome,
            "new_stats": {
                "level": player.level,
                "experience": player.experience,
                "money": player.money,
                "reputation": player.reputation
            },
            "level_up": level_up,
            "promotion_available": promotion is not None
        }
        
        if outcome["failure_occurred"]:
            failure_data = self.handle_failure_recovery(player, "general_failure")
            response["failure_recovery"] = failure_data
        
        await self._send_player_message(player.id, response)
        
        # Update race score if in a race
        for race_id, race_data in self.current_races.items():
            if player.id in race_data["participants"] and race_data["status"] == "active":
                race_data["scores"][player.id] += outcome["performance"] * 100
    
    async def _handle_skill_upgrade(self, player: Player, action: Dict[str, Any]):
        """Handle skill upgrade requests"""
        skill_id = action.get("skill_id")
        
        if skill_id not in self.skill_trees or skill_id not in player.skills:
            await self._send_player_message(player.id, {
                "type": "error",
                "message": "Invalid skill"
            })
            return
        
        skill_node = self.skill_trees[skill_id]
        current_level = player.skills[skill_id]
        
        if current_level >= skill_node.max_level:
            await self._send_player_message(player.id, {
                "type": "error",
                "message": "Skill already at maximum level"
            })
            return
        
        # Calculate cost (simple formula for now)
        cost = (current_level + 1) * 100 + ((current_level + 1) ** 2) * 10
        
        if player.money < cost:
            await self._send_player_message(player.id, {
                "type": "error",
                "message": "Insufficient funds for skill upgrade"
            })
            return
        
        # Check prerequisites
        for prereq in skill_node.prerequisites:
            if player.skills.get(prereq, 0) == 0:
                await self._send_player_message(player.id, {
                    "type": "error",
                    "message": f"Prerequisite skill '{prereq}' required"
                })
                return
        
        # Perform upgrade
        player.money -= cost
        player.skills[skill_id] += 1
        
        await self._send_player_message(player.id, {
            "type": "skill_upgraded",
            "skill_id": skill_id,
            "new_level": player.skills[skill_id],
            "cost": cost,
            "remaining_money": player.money,
            "educational_tip": f"Upgrading {skill_node.name} will improve your {', '.join(skill_node.effects.keys())}"
        })
    
    async def _handle_promotion_application(self, player: Player):
        """Handle promotion applications"""
        promotion = self.check_promotion(player)
        
        if promotion:
            career_path = self.career_paths[player.career]
            new_position = next(pos for pos in career_path.positions if pos["id"] == promotion)
            old_position = player.current_position
            
            player.current_position = promotion
            salary_increase = career_path.salary_progression[promotion] - career_path.salary_progression[old_position]
            
            # Award promotion bonus
            player.money += salary_increase * 0.1  # 10% of annual salary increase
            player.reputation += 10
            
            # Add achievement
            achievement_id = f"promoted_to_{promotion}"
            if achievement_id not in player.achievements:
                player.achievements.append(achievement_id)
            
            await self._send_player_message(player.id, {
                "type": "promotion_successful",
                "old_position": old_position,
                "new_position": promotion,
                "position_name": new_position["name"],
                "salary_increase": salary_increase,
                "bonus_received": salary_increase * 0.1,
                "new_reputation": player.reputation,
                "educational_tip": f"Congratulations on your promotion to {new_position['name']}! This opens up new opportunities and responsibilities."
            })
        else:
            await self._send_player_message(player.id, {
                "type": "promotion_denied",
                "message": "You don't meet the requirements for promotion yet",
                "requirements_tip": "Focus on gaining experience and developing the required skills"
            })
    
    async def _handle_failure_recovery_action(self, player: Player, action: Dict[str, Any]):
        """Handle failure recovery actions"""
        recovery_option = action.get("recovery_option")
        
        # Simulate recovery attempt
        success = random.random() < recovery_option.get("success_rate", 0.5)
        
        if success:
            player.recoveries += 1
            bonus_multiplier = 1 + (GAME_CONFIG["failure_recovery_bonus"])
            
            # Apply recovery bonus based on type
            if "equipment_reliability" in recovery_option.get("bonus", ""):
                player.statistics["equipment_bonus"] = player.statistics.get("equipment_bonus", 1.0) * bonus_multiplier
            elif "market_resilience" in recovery_option.get("bonus", ""):
                player.statistics["market_bonus"] = player.statistics.get("market_bonus", 1.0) * bonus_multiplier
            
            player.reputation += 5
            
            await self._send_player_message(player.id, {
                "type": "recovery_successful",
                "recovery_option": recovery_option,
                "bonus_applied": recovery_option.get("bonus"),
                "reputation_gained": 5,
                "educational_tip": "Successful recovery from failures builds resilience and expertise. These experiences make you a more valuable professional."
            })
        else:
            await self._send_player_message(player.id, {
                "type": "recovery_failed",
                "recovery_option": recovery_option,
                "educational_tip": "Not all recovery attempts succeed. Learn from this experience and consider alternative approaches."
            })
    
    async def _handle_race_join(self, player: Player, action: Dict[str, Any]):
        """Handle race join requests"""
        race_type = action.get("race_type", "general")
        
        # Find or create race
        available_race = None
        for race_id, race_data in self.current_races.items():
            if (race_data["status"] == "waiting" and 
                len(race_data["participants"]) < GAME_CONFIG["max_players_per_race"]):
                available_race = race_id
                break
        
        if not available_race:
            # Create new race
            race_id = str(uuid.uuid4())
            await self.start_career_race(race_id, [player.id], GAME_CONFIG["race_duration"])
        else:
            # Join existing race
            self.current_races[available_race]["participants"].append(player.id)
            self.current_races[available_race]["scores"][player.id] = 0
        
        # Set race start statistics
        player.statistics["race_start_level"] = player.level
        player.statistics["race_start_money"] = player.money
        
        await self._send_player_message(player.id, {
            "type": "race_joined",
            "race_id": available_race or race_id,
            "participants": len(self.current_races[available_race or race_id]["participants"]),
            "educational_tip": "Career races test your ability to progress quickly. Focus on skill development and smart decision-making!"
        })
    
    async def _send_career_visualization(self, player: Player):
        """Send career path visualization data"""
        career_path = self.career_paths[player.career]
        
        # Create visualization data
        visualization_data = {
            "current_position": player.current_position,
            "career_ladder": [],
            "progress_metrics": {
                "level_progress": player.experience / self.calculate_experience_required(player.level),
                "position_progress": 0,
                "skill_mastery": sum(player.skills.values()) / (len(player.skills) * 20) if player.skills else 0
            }
        }
        
        # Build career ladder with progress indicators
        for i, position in enumerate(career_path.positions):
            requirements = career_path.requirements[position["id"]]
            
            # Check if requirements are met
            is_current = position["id"] == player.current_position
            is_completed = False
            can_unlock = False
            
            if player.level > position["level"]:
                is_completed = True
            elif player.level == position["level"] and player.current_position == position["id"]:
                is_current = True
            elif i > 0:  # Not the first position
                prev_position = career_path.positions[i-1]
                if prev_position["id"] == player.current_position:
                    can_unlock = self.check_promotion(player) == position["id"]
            
            visualization_data["career_ladder"].append({
                "position": position,
                "requirements": requirements,
                "salary": career_path.salary_progression[position["id"]],
                "is_current": is_current,
                "is_completed": is_completed,
                "can_unlock": can_unlock,
                "skill_bonuses": career_path.skill_bonuses.get(position["id"], {})
            })
        
        await self._send_player_message(player.id, {
            "type": "career_visualization",
            "data": visualization_data,
            "educational_tip": "Your career path shows the progression from entry-level to leadership positions. Each step requires specific skills and experience."
        })
    
    async def _send_educational_tooltip(self, player: Player, action: Dict[str, Any]):
        """Send educational tooltip content"""
        tooltip_type = action.get("tooltip_type")
        career_path = self.career_paths[player.career]
        
        tooltip_content = career_path.tooltips.get(tooltip_type, "Information not available")
        
        # Add contextual information based on player's current situation
        contextual_info = ""
        if tooltip_type in career_path.industry_mechanics:
            mechanic_value = career_path.industry_mechanics[tooltip_type]
            if isinstance(mechanic_value, float):
                if mechanic_value > 0.8:
                    contextual_info = f" This factor has a high impact ({int(mechanic_value * 100)}%) on your career success."
                elif mechanic_value > 0.5:
                    contextual_info = f" This factor has a moderate impact ({int(mechanic_value * 100)}%) on your operations."
                else:
                    contextual_info = f" This factor has a low impact ({int(mechanic_value * 100)}%) but is still worth monitoring."
        
        await self._send_player_message(player.id, {
            "type": "educational_tooltip",
            "tooltip_type": tooltip_type,
            "content": tooltip_content + contextual_info,
            "related_skills": [skill_id for skill_id, skill in self.skill_trees.items() 
                             if tooltip_type in skill.description.lower() and player.career in skill.career_specific]
        })
    
    async def _send_player_message(self, player_id: str, message: Dict[str, Any]):
        """Send message to specific player"""
        if player_id in self.active_connections:
            try:
                await self.active_connections[player_id].send_text(json.dumps(message, default=str))
            except Exception as e:
                logging.error(f"Error sending message to player {player_id}: {e}")
    
    async def _broadcast_to_all(self, message: Dict[str, Any]):
        """Broadcast message to all connected players"""
        for player_id in list(self.active_connections.keys()):
            await self._send_player_message(player_id, message)
    
    def remove_player(self, player_id: str):
        """Remove player from all active systems"""
        if player_id in self.active_connections:
            del self.active_connections[player_id]
        
        # Remove from any active races
        for race_id, race_data in list(self.current_races.items()):
            if player_id in race_data["participants"]:
                race_data["participants"].remove(player_id)
                if player_id in race_data["scores"]:
                    del race_data["scores"][player_id]
                
                # If race becomes empty, remove it
                if not race_data["participants"]:
                    del self.current_races[race_id]

# Initialize the game manager
game_manager = CareerSimulationManager()

# FastAPI application setup
app = FastAPI(title="Maritime Career Simulations", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8088"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    await game_manager.start_background_tasks()

@app.get("/")
async def get_game_client():
    """Serve the game client interface"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Maritime Career Simulations</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'Arial', sans-serif; 
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
                color: white; 
                min-height: 100vh;
                display: flex;
                flex-direction: column;
            }
            
            .header { 
                background: rgba(0,0,0,0.3); 
                padding: 20px; 
                text-align: center; 
                backdrop-filter: blur(10px);
            }
            .header h1 { font-size: 2.5rem; margin-bottom: 10px; }
            .header p { font-size: 1.1rem; opacity: 0.9; }
            
            .container { 
                flex: 1; 
                display: flex; 
                gap: 20px; 
                padding: 20px; 
                max-width: 1400px; 
                margin: 0 auto; 
                width: 100%;
            }
            
            .sidebar { 
                width: 300px; 
                background: rgba(0,0,0,0.2); 
                border-radius: 15px; 
                padding: 20px;
                backdrop-filter: blur(10px);
                height: fit-content;
            }
            
            .main-content { 
                flex: 1; 
                background: rgba(255,255,255,0.1); 
                border-radius: 15px; 
                padding: 20px;
                backdrop-filter: blur(10px);
            }
            
            .join-form { 
                background: rgba(255,255,255,0.1); 
                padding: 30px; 
                border-radius: 15px; 
                margin: 50px auto; 
                max-width: 500px;
            }
            
            .form-group { margin-bottom: 20px; }
            .form-group label { display: block; margin-bottom: 8px; font-weight: bold; }
            .form-group input, .form-group select { 
                width: 100%; 
                padding: 12px; 
                border: none; 
                border-radius: 8px; 
                background: rgba(255,255,255,0.9); 
                color: #333;
                font-size: 16px;
            }
            
            .btn { 
                padding: 12px 24px; 
                background: linear-gradient(45deg, #4CAF50, #45a049); 
                color: white; 
                border: none; 
                border-radius: 8px; 
                cursor: pointer; 
                font-size: 16px;
                font-weight: bold;
                transition: all 0.3s ease;
                margin: 5px;
            }
            .btn:hover { 
                transform: translateY(-2px); 
                box-shadow: 0 5px 15px rgba(0,0,0,0.3); 
            }
            .btn:disabled { 
                opacity: 0.6; 
                cursor: not-allowed; 
                transform: none;
            }
            
            .stat-card { 
                background: rgba(0,0,0,0.3); 
                padding: 15px; 
                border-radius: 10px; 
                margin: 10px 0; 
                border-left: 4px solid #4CAF50;
            }
            .stat-card h3 { color: #4CAF50; margin-bottom: 10px; }
            
            .progress-bar { 
                background: rgba(0,0,0,0.3); 
                height: 25px; 
                border-radius: 12px; 
                overflow: hidden; 
                margin: 10px 0; 
                position: relative;
            }
            .progress-fill { 
                background: linear-gradient(90deg, #4CAF50, #45a049); 
                height: 100%; 
                transition: width 0.5s ease; 
                border-radius: 12px;
            }
            .progress-text { 
                position: absolute; 
                top: 50%; 
                left: 50%; 
                transform: translate(-50%, -50%); 
                font-weight: bold; 
                font-size: 14px;
                text-shadow: 1px 1px 2px rgba(0,0,0,0.7);
            }
            
            .career-ladder { margin: 20px 0; }
            .career-position { 
                background: rgba(255,255,255,0.1); 
                padding: 15px; 
                margin: 10px 0; 
                border-radius: 10px; 
                border: 2px solid transparent;
                transition: all 0.3s ease;
            }
            .career-position.current { border-color: #FFD700; background: rgba(255,215,0,0.2); }
            .career-position.completed { border-color: #4CAF50; background: rgba(76,175,80,0.2); }
            .career-position.available { border-color: #2196F3; background: rgba(33,150,243,0.2); }
            .career-position:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.3); }
            
            .tooltip { 
                position: relative; 
                cursor: help; 
                border-bottom: 1px dotted #fff;
            }
            .tooltip:hover::after { 
                content: attr(data-tooltip); 
                position: absolute; 
                bottom: 100%; 
                left: 50%; 
                transform: translateX(-50%); 
                background: rgba(0,0,0,0.9); 
                color: white; 
                padding: 10px; 
                border-radius: 5px; 
                white-space: nowrap; 
                z-index: 1000;
            }
            
            .skill-grid { 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
                gap: 15px; 
                margin: 20px 0; 
            }
            .skill-card { 
                background: rgba(0,0,0,0.2); 
                padding: 15px; 
                border-radius: 10px; 
                text-align: center;
                transition: all 0.3s ease;
            }
            .skill-card:hover { background: rgba(0,0,0,0.4); }
            .skill-level { 
                font-size: 24px; 
                font-weight: bold; 
                color: #4CAF50; 
                margin-bottom: 5px; 
            }
            
            .leaderboard { margin: 20px 0; }
            .leaderboard-entry { 
                display: flex; 
                justify-content: space-between; 
                padding: 10px; 
                margin: 5px 0; 
                background: rgba(255,255,255,0.1); 
                border-radius: 5px;
                align-items: center;
            }
            .rank { 
                font-weight: bold; 
                color: #FFD700; 
                min-width: 30px; 
            }
            
            .event-notification { 
                background: rgba(255,165,0,0.3); 
                border-left: 4px solid orange; 
                padding: 15px; 
                margin: 10px 0; 
                border-radius: 5px;
                animation: slideIn 0.5s ease;
            }
            @keyframes slideIn { from { opacity: 0; transform: translateX(-100%); } to { opacity: 1; transform: translateX(0); } }
            
            .race-status { 
                background: rgba(255,0,0,0.2); 
                border: 2px solid #FF4444; 
                padding: 15px; 
                border-radius: 10px; 
                text-align: center; 
                margin: 20px 0;
            }
            
            .hidden { display: none; }
            .fade-in { animation: fadeIn 0.5s ease; }
            @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
            
            .game-area { display: none; }
            
            @media (max-width: 768px) {
                .container { flex-direction: column; padding: 10px; }
                .sidebar { width: 100%; }
                .header h1 { font-size: 2rem; }
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚢 Maritime Career Simulations</h1>
            <p>Build your professional career in the maritime industry</p>
        </div>
        
        <div class="join-form" id="joinForm">
            <h2>Start Your Maritime Career</h2>
            <div class="form-group">
                <label for="playerName">Your Name</label>
                <input type="text" id="playerName" placeholder="Enter your name" required>
            </div>
            <div class="form-group">
                <label for="careerChoice">Choose Your Career Path</label>
                <select id="careerChoice" required>
                    <option value="">Select a career...</option>
                    <option value="fishing">🎣 Commercial Fishing (Deckhand → Fleet Owner)</option>
                    <option value="tourism">🏖️ Marine Tourism (Guide → Tourism Mogul)</option>
                    <option value="shipyard">🔧 Shipyard Management (Apprentice → Owner)</option>
                    <option value="freight">📦 Freight Logistics (Dock Worker → Global Executive)</option>
                </select>
            </div>
            <button class="btn" onclick="startCareer()">Begin Your Career Journey!</button>
        </div>
        
        <div class="container game-area" id="gameArea">
            <div class="sidebar">
                <div class="stat-card">
                    <h3>💰 Financial Status</h3>
                    <div id="moneyDisplay">$10,000</div>
                    <div id="salaryDisplay">Annual Salary: $35,000</div>
                </div>
                
                <div class="stat-card">
                    <h3>📈 Career Progress</h3>
                    <div>Level: <span id="levelDisplay">1</span></div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="expProgress" style="width: 0%"></div>
                        <div class="progress-text" id="expText">0 XP</div>
                    </div>
                    <div>Position: <span id="positionDisplay">Entry Level</span></div>
                    <div>Reputation: <span id="reputationDisplay">50</span>/100</div>
                </div>
                
                <div class="stat-card">
                    <h3>🏆 Achievements</h3>
                    <div id="achievementsList">None yet</div>
                </div>
                
                <div class="stat-card">
                    <h3>⚡ Quick Actions</h3>
                    <button class="btn" onclick="workShift()" id="workBtn">Work Shift</button>
                    <button class="btn" onclick="applyPromotion()" id="promotionBtn">Apply for Promotion</button>
                    <button class="btn" onclick="joinRace()" id="raceBtn">Join Career Race</button>
                    <button class="btn" onclick="showCareerPath()" id="careerBtn">View Career Path</button>
                </div>
            </div>
            
            <div class="main-content">
                <div id="careerVisualization" class="hidden">
                    <h2>🎯 Your Career Path</h2>
                    <div class="career-ladder" id="careerLadder"></div>
                </div>
                
                <div id="skillsSection">
                    <h2>🎓 Skills Development</h2>
                    <div class="skill-grid" id="skillGrid"></div>
                </div>
                
                <div id="industryEvents">
                    <h2>📰 Industry Updates</h2>
                    <div id="eventsList"></div>
                </div>
                
                <div id="raceStatus" class="race-status hidden">
                    <h3>🏁 Career Race in Progress</h3>
                    <div id="raceInfo"></div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="raceProgress" style="width: 0%"></div>
                        <div class="progress-text" id="raceText">Race Progress</div>
                    </div>
                </div>
                
                <div id="leaderboardSection">
                    <h2>🏆 Career Leaderboard</h2>
                    <div class="leaderboard" id="leaderboard"></div>
                </div>
            </div>
        </div>
        
        <script>
            let ws = null;
            let playerId = null;
            let currentCareer = null;
            let playerData = {};
            let raceTimer = null;
            
            function startCareer() {
                const name = document.getElementById('playerName').value;
                const career = document.getElementById('careerChoice').value;
                
                if (!name || !career) {
                    alert('Please enter your name and select a career path');
                    return;
                }
                
                currentCareer = career;
                
                ws = new WebSocket(`ws://localhost:8386/ws`);
                
                ws.onopen = function() {
                    ws.send(JSON.stringify({
                        type: 'join',
                        name: name,
                        career: career
                    }));
                };
                
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    handleGameMessage(data);
                };
                
                ws.onclose = function() {
                    addNotification('Disconnected from server', 'error');
                };
                
                ws.onerror = function(error) {
                    console.error('WebSocket error:', error);
                    addNotification('Connection error', 'error');
                };
            }
            
            function handleGameMessage(data) {
                switch(data.type) {
                    case 'welcome':
                        playerId = data.player.id;
                        playerData = data.player;
                        document.getElementById('joinForm').style.display = 'none';
                        document.getElementById('gameArea').style.display = 'flex';
                        document.getElementById('gameArea').classList.add('fade-in');
                        updatePlayerDisplay();
                        updateSkillsDisplay(data.available_skills);
                        displayIndustryEvents(data.active_events);
                        if (data.educational_tip) {
                            addNotification(data.educational_tip, 'tip');
                        }
                        break;
                        
                    case 'work_shift_result':
                        handleWorkResult(data);
                        break;
                        
                    case 'skill_upgraded':
                        playerData.skills[data.skill_id] = data.new_level;
                        playerData.money = data.remaining_money;
                        updatePlayerDisplay();
                        updateSkillsDisplay();
                        addNotification(`${data.skill_id} upgraded to level ${data.new_level}!`, 'success');
                        if (data.educational_tip) {
                            addNotification(data.educational_tip, 'tip');
                        }
                        break;
                        
                    case 'promotion_successful':
                        playerData.current_position = data.new_position;
                        playerData.money += data.bonus_received;
                        playerData.reputation = data.new_reputation;
                        updatePlayerDisplay();
                        addNotification(`Promoted to ${data.position_name}! Bonus: $${data.bonus_received.toFixed(2)}`, 'success');
                        break;
                        
                    case 'career_visualization':
                        displayCareerVisualization(data.data);
                        break;
                        
                    case 'race_joined':
                        displayRaceStatus(data);
                        break;
                        
                    case 'race_completed':
                        handleRaceComplete(data);
                        break;
                        
                    case 'industry_event_started':
                        addIndustryEvent(data.event);
                        if (data.educational_tooltip) {
                            addNotification(data.educational_tooltip, 'tip');
                        }
                        break;
                        
                    case 'leaderboards_updated':
                        updateLeaderboard(data.leaderboards[currentCareer] || []);
                        break;
                        
                    case 'educational_tooltip':
                        addNotification(data.content, 'tip');
                        break;
                        
                    case 'error':
                        addNotification(data.message, 'error');
                        break;
                }
            }
            
            function updatePlayerDisplay() {
                document.getElementById('moneyDisplay').textContent = `$${playerData.money.toFixed(2)}`;
                document.getElementById('levelDisplay').textContent = playerData.level;
                document.getElementById('positionDisplay').textContent = playerData.current_position.replace('_', ' ');
                document.getElementById('reputationDisplay').textContent = playerData.reputation;
                
                // Update experience progress bar
                const expRequired = calculateExpRequired(playerData.level);
                const expProgress = (playerData.experience / expRequired) * 100;
                document.getElementById('expProgress').style.width = `${Math.min(expProgress, 100)}%`;
                document.getElementById('expText').textContent = `${playerData.experience} / ${expRequired} XP`;
                
                // Update achievements
                const achievementsEl = document.getElementById('achievementsList');
                if (playerData.achievements && playerData.achievements.length > 0) {
                    achievementsEl.innerHTML = playerData.achievements.map(a => `<div>🏆 ${a.replace('_', ' ')}</div>`).join('');
                } else {
                    achievementsEl.innerHTML = 'None yet';
                }
            }
            
            function calculateExpRequired(level) {
                return Math.floor(1000 * Math.pow(level, 1.5) + 500 * level);
            }
            
            function updateSkillsDisplay(skills = null) {
                const skillGrid = document.getElementById('skillGrid');
                skillGrid.innerHTML = '';
                
                const skillsToShow = skills || {};
                Object.keys(playerData.skills || {}).forEach(skillId => {
                    if (!skillsToShow[skillId] && skills) return; // Only show available skills if provided
                    
                    const skillLevel = playerData.skills[skillId] || 0;
                    const maxLevel = skills?.[skillId]?.max_level || 20;
                    const cost = (skillLevel + 1) * 100 + Math.pow(skillLevel + 1, 2) * 10;
                    
                    const skillCard = document.createElement('div');
                    skillCard.className = 'skill-card';
                    skillCard.innerHTML = `
                        <div class="skill-level">${skillLevel}/${maxLevel}</div>
                        <div><strong>${skillId.replace('_', ' ')}</strong></div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${(skillLevel/maxLevel)*100}%"></div>
                        </div>
                        <button class="btn" onclick="upgradeSkill('${skillId}')" ${skillLevel >= maxLevel || playerData.money < cost ? 'disabled' : ''}>
                            Upgrade ($${cost})
                        </button>
                    `;
                    skillGrid.appendChild(skillCard);
                });
            }
            
            function displayCareerVisualization(data) {
                const visualization = document.getElementById('careerVisualization');
                const ladder = document.getElementById('careerLadder');
                
                ladder.innerHTML = '';
                data.career_ladder.forEach(position => {
                    const positionEl = document.createElement('div');
                    positionEl.className = `career-position ${position.is_current ? 'current' : position.is_completed ? 'completed' : position.can_unlock ? 'available' : ''}`;
                    
                    positionEl.innerHTML = `
                        <h3>${position.position.name} (Level ${position.position.level})</h3>
                        <p>${position.position.description}</p>
                        <div><strong>Salary:</strong> $${position.salary.toLocaleString()}/year</div>
                        <div><strong>Requirements:</strong> ${Object.entries(position.requirements.skills || {}).map(([skill, level]) => `${skill}: ${level}`).join(', ')}</div>
                        ${position.is_current ? '<div style="color: gold;">⭐ Current Position</div>' : ''}
                        ${position.can_unlock ? '<div style="color: lightblue;">🚀 Ready to Apply!</div>' : ''}
                    `;
                    
                    ladder.appendChild(positionEl);
                });
                
                visualization.classList.remove('hidden');
            }
            
            function displayIndustryEvents(events) {
                const eventsList = document.getElementById('eventsList');
                eventsList.innerHTML = '';
                
                Object.values(events).forEach(event => {
                    addIndustryEvent(event);
                });
            }
            
            function addIndustryEvent(event) {
                const eventsList = document.getElementById('eventsList');
                const eventEl = document.createElement('div');
                eventEl.className = 'event-notification';
                eventEl.innerHTML = `
                    <h4>${event.title}</h4>
                    <p>${event.description}</p>
                    <small>Impact: ${Object.entries(event.impact).map(([key, value]) => `${key}: ${value > 1 ? '+' : ''}${((value - 1) * 100).toFixed(0)}%`).join(', ')}</small>
                `;
                eventsList.appendChild(eventEl);
            }
            
            function displayRaceStatus(data) {
                const raceStatus = document.getElementById('raceStatus');
                const raceInfo = document.getElementById('raceInfo');
                
                raceInfo.innerHTML = `
                    <div>Race ID: ${data.race_id}</div>
                    <div>Participants: ${data.participants}</div>
                    <div>Duration: ${Math.floor(data.duration / 60)} minutes</div>
                `;
                
                raceStatus.classList.remove('hidden');
                
                // Start race timer
                let timeLeft = data.duration || 300;
                raceTimer = setInterval(() => {
                    timeLeft--;
                    const minutes = Math.floor(timeLeft / 60);
                    const seconds = timeLeft % 60;
                    document.getElementById('raceText').textContent = `${minutes}:${seconds.toString().padStart(2, '0')} remaining`;
                    
                    if (timeLeft <= 0) {
                        clearInterval(raceTimer);
                        raceStatus.classList.add('hidden');
                    }
                }, 1000);
            }
            
            function handleRaceComplete(data) {
                if (raceTimer) {
                    clearInterval(raceTimer);
                }
                
                document.getElementById('raceStatus').classList.add('hidden');
                
                const yourRank = data.your_rank;
                let message = `Race completed! You finished ${yourRank}${getOrdinalSuffix(yourRank)} place.`;
                
                if (yourRank === 1) {
                    message += ' 🏆 Congratulations, Champion!';
                } else if (yourRank <= 3) {
                    message += ' 🥉 Great job reaching the podium!';
                }
                
                addNotification(message, 'success');
                updatePlayerDisplay(); // Update with race rewards
            }
            
            function getOrdinalSuffix(num) {
                const suffixes = ['th', 'st', 'nd', 'rd'];
                const value = num % 100;
                return suffixes[(value - 20) % 10] || suffixes[value] || suffixes[0];
            }
            
            function updateLeaderboard(leaderboard) {
                const leaderboardEl = document.getElementById('leaderboard');
                leaderboardEl.innerHTML = '';
                
                leaderboard.slice(0, 10).forEach(entry => {
                    const entryEl = document.createElement('div');
                    entryEl.className = 'leaderboard-entry';
                    entryEl.innerHTML = `
                        <div><span class="rank">#${entry.rank}</span> ${entry.player_name}</div>
                        <div>Level ${entry.level} ${entry.position.replace('_', ' ')}</div>
                        <div>$${entry.money.toFixed(0)}</div>
                    `;
                    leaderboardEl.appendChild(entryEl);
                });
            }
            
            function addNotification(message, type) {
                // Simple notification system
                const notification = document.createElement('div');
                notification.className = `event-notification`;
                notification.style.position = 'fixed';
                notification.style.top = '20px';
                notification.style.right = '20px';
                notification.style.zIndex = '1000';
                notification.style.maxWidth = '300px';
                notification.innerHTML = message;
                
                if (type === 'error') {
                    notification.style.borderLeftColor = 'red';
                    notification.style.background = 'rgba(255,0,0,0.3)';
                } else if (type === 'success') {
                    notification.style.borderLeftColor = 'green';
                    notification.style.background = 'rgba(0,255,0,0.3)';
                } else if (type === 'tip') {
                    notification.style.borderLeftColor = 'blue';
                    notification.style.background = 'rgba(0,100,255,0.3)';
                }
                
                document.body.appendChild(notification);
                
                setTimeout(() => {
                    notification.remove();
                }, 5000);
            }
            
            function workShift() {
                if (ws) {
                    ws.send(JSON.stringify({
                        type: 'work_shift',
                        task_type: 'general_work'
                    }));
                    
                    document.getElementById('workBtn').disabled = true;
                    setTimeout(() => {
                        document.getElementById('workBtn').disabled = false;
                    }, 3000);
                }
            }
            
            function applyPromotion() {
                if (ws) {
                    ws.send(JSON.stringify({
                        type: 'apply_promotion'
                    }));
                }
            }
            
            function upgradeSkill(skillId) {
                if (ws) {
                    ws.send(JSON.stringify({
                        type: 'upgrade_skill',
                        skill_id: skillId
                    }));
                }
            }
            
            function joinRace() {
                if (ws) {
                    ws.send(JSON.stringify({
                        type: 'join_race',
                        race_type: 'career_progress'
                    }));
                    
                    document.getElementById('raceBtn').disabled = true;
                    setTimeout(() => {
                        document.getElementById('raceBtn').disabled = false;
                    }, 60000); // 1 minute cooldown
                }
            }
            
            function showCareerPath() {
                if (ws) {
                    ws.send(JSON.stringify({
                        type: 'get_career_visualization'
                    }));
                }
            }
            
            function handleWorkResult(data) {
                const outcome = data.outcome;
                playerData.experience = data.new_stats.experience;
                playerData.level = data.new_stats.level;
                playerData.money = data.new_stats.money;
                playerData.reputation = data.new_stats.reputation;
                
                updatePlayerDisplay();
                
                let resultMessage = `Work shift completed! Performance: ${(outcome.performance * 100).toFixed(1)}%<br>`;
                resultMessage += `Earned: $${outcome.money_earned.toFixed(2)}, ${outcome.experience_gained} XP<br>`;
                
                if (data.level_up) {
                    resultMessage += `🎉 Level Up! You are now level ${data.new_stats.level}<br>`;
                }
                
                if (data.promotion_available) {
                    resultMessage += `🚀 You're eligible for promotion! Click "Apply for Promotion"<br>`;
                }
                
                if (outcome.failure_occurred) {
                    resultMessage += `⚠️ Work failure occurred. This affects your reputation.<br>`;
                    if (data.failure_recovery) {
                        resultMessage += `Recovery options are available.`;
                    }
                }
                
                addNotification(resultMessage, outcome.failure_occurred ? 'error' : 'success');
            }
        </script>
    </body>
    </html>
    """)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    player_id = None
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "join":
                player_id = await game_manager.add_player(websocket, {
                    "name": message.get("name"),
                    "career": message.get("career")
                })
            elif player_id:
                await game_manager.handle_game_action(player_id, message)
                
    except WebSocketDisconnect:
        if player_id:
            game_manager.remove_player(player_id)

@app.get("/api/careers")
async def get_career_paths():
    """Get all available career paths"""
    return {
        career.value: asdict(path) 
        for career, path in game_manager.career_paths.items()
    }

@app.get("/api/skills")
async def get_skill_trees():
    """Get all skill trees"""
    return {
        skill_id: asdict(skill) 
        for skill_id, skill in game_manager.skill_trees.items()
    }

@app.get("/api/leaderboards")
async def get_leaderboards():
    """Get current leaderboards for all careers"""
    return game_manager.leaderboards

@app.get("/api/stats")
async def get_game_statistics():
    """Get overall game statistics"""
    return {
        "total_players": len(game_manager.players),
        "active_connections": len(game_manager.active_connections),
        "active_races": len(game_manager.current_races),
        "industry_events": len(game_manager.active_events),
        "career_distribution": {
            career.value: sum(1 for p in game_manager.players.values() if p.career == career)
            for career in CareerType
        }
    }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    config = uvicorn.Config(app, host="0.0.0.0", port=8386, log_level="info")
    server = uvicorn.Server(config)
    asyncio.run(server.serve())