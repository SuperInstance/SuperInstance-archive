#!/usr/bin/env python3
"""
Cost Calculator System
Comprehensive project cost estimation with materials, labor, and overhead calculations
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum
import sqlite3
import threading
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import uuid
import math


class CostCategory(Enum):
    MATERIALS = "materials"
    LABOR = "labor"
    EQUIPMENT = "equipment"
    OVERHEAD = "overhead"
    SHIPPING = "shipping"
    TAXES = "taxes"
    CONTINGENCY = "contingency"
    PROFIT = "profit"


class EstimationMethod(Enum):
    PARAMETRIC = "parametric"
    ANALOGOUS = "analogous"
    BOTTOM_UP = "bottom_up"
    THREE_POINT = "three_point"
    MONTE_CARLO = "monte_carlo"


class CostAccuracy(Enum):
    ROUGH = "rough"           # -50% to +100%
    BUDGET = "budget"         # -30% to +50%
    DEFINITIVE = "definitive" # -15% to +20%
    DETAILED = "detailed"     # -10% to +15%


@dataclass
class Material:
    id: str
    name: str
    category: str
    unit: str
    unit_cost: Decimal
    supplier_id: Optional[str] = None
    lead_time_days: int = 0
    minimum_order_quantity: int = 1
    waste_factor: float = 0.05  # 5% default waste
    availability: str = "available"
    specifications: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LaborRate:
    id: str
    role: str
    skill_level: str
    hourly_rate: Decimal
    burden_rate: float = 0.30  # 30% burden (benefits, taxes, etc.)
    efficiency_factor: float = 1.0
    location: str = "default"
    effective_date: datetime = field(default_factory=datetime.now)


@dataclass
class Equipment:
    id: str
    name: str
    category: str
    hourly_rate: Optional[Decimal] = None
    daily_rate: Optional[Decimal] = None
    purchase_cost: Optional[Decimal] = None
    depreciation_years: int = 5
    maintenance_factor: float = 0.10  # 10% of cost annually
    utilization_rate: float = 0.80  # 80% utilization


@dataclass
class CostItem:
    id: str
    name: str
    category: CostCategory
    quantity: Decimal
    unit: str
    unit_cost: Decimal
    total_cost: Decimal
    description: str = ""
    source: str = ""  # material_id, labor_rate_id, etc.
    risk_factor: float = 1.0
    confidence_level: float = 1.0
    notes: str = ""


@dataclass
class CostEstimate:
    id: str
    project_name: str
    description: str
    estimation_method: EstimationMethod
    accuracy_level: CostAccuracy
    cost_items: List[CostItem]
    total_cost: Decimal
    contingency_percentage: float
    contingency_amount: Decimal
    final_cost: Decimal
    created_by: str
    created_at: datetime
    updated_at: datetime
    valid_until: Optional[datetime] = None
    assumptions: List[str] = field(default_factory=list)
    exclusions: List[str] = field(default_factory=list)
    risks: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class CostBreakdown:
    materials: Decimal
    labor: Decimal
    equipment: Decimal
    overhead: Decimal
    shipping: Decimal
    taxes: Decimal
    contingency: Decimal
    profit: Decimal
    total: Decimal


class CostDatabase:
    def __init__(self, db_path: str = "costs.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS materials (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                unit TEXT,
                unit_cost REAL,
                supplier_id TEXT,
                lead_time_days INTEGER,
                minimum_order_quantity INTEGER,
                waste_factor REAL,
                availability TEXT,
                specifications TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS labor_rates (
                id TEXT PRIMARY KEY,
                role TEXT NOT NULL,
                skill_level TEXT,
                hourly_rate REAL,
                burden_rate REAL,
                efficiency_factor REAL,
                location TEXT,
                effective_date TEXT,
                created_at TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS equipment (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                hourly_rate REAL,
                daily_rate REAL,
                purchase_cost REAL,
                depreciation_years INTEGER,
                maintenance_factor REAL,
                utilization_rate REAL,
                created_at TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cost_estimates (
                id TEXT PRIMARY KEY,
                project_name TEXT NOT NULL,
                description TEXT,
                estimation_method TEXT,
                accuracy_level TEXT,
                total_cost REAL,
                contingency_percentage REAL,
                contingency_amount REAL,
                final_cost REAL,
                created_by TEXT,
                created_at TEXT,
                updated_at TEXT,
                valid_until TEXT,
                assumptions TEXT,
                exclusions TEXT,
                risks TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cost_items (
                id TEXT PRIMARY KEY,
                estimate_id TEXT,
                name TEXT,
                category TEXT,
                quantity REAL,
                unit TEXT,
                unit_cost REAL,
                total_cost REAL,
                description TEXT,
                source TEXT,
                risk_factor REAL,
                confidence_level REAL,
                notes TEXT,
                FOREIGN KEY (estimate_id) REFERENCES cost_estimates (id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historical_costs (
                id TEXT PRIMARY KEY,
                project_name TEXT,
                category TEXT,
                item_name TEXT,
                quantity REAL,
                unit TEXT,
                unit_cost REAL,
                total_cost REAL,
                date TEXT,
                location TEXT,
                supplier TEXT,
                notes TEXT
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_materials_category ON materials(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_labor_role ON labor_rates(role)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_estimates_project ON cost_estimates(project_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_historical_category ON historical_costs(category)")
        
        conn.commit()
        conn.close()
    
    def add_material(self, material: Material) -> str:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO materials
            (id, name, category, unit, unit_cost, supplier_id, lead_time_days,
             minimum_order_quantity, waste_factor, availability, specifications,
             created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            material.id, material.name, material.category, material.unit,
            float(material.unit_cost), material.supplier_id, material.lead_time_days,
            material.minimum_order_quantity, material.waste_factor, material.availability,
            json.dumps(material.specifications), datetime.now().isoformat(), datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        return material.id
    
    def add_labor_rate(self, labor_rate: LaborRate) -> str:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO labor_rates
            (id, role, skill_level, hourly_rate, burden_rate, efficiency_factor,
             location, effective_date, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            labor_rate.id, labor_rate.role, labor_rate.skill_level,
            float(labor_rate.hourly_rate), labor_rate.burden_rate, labor_rate.efficiency_factor,
            labor_rate.location, labor_rate.effective_date.isoformat(), datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        return labor_rate.id
    
    def get_material(self, material_id: str) -> Optional[Material]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM materials WHERE id = ?", (material_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Material(
                id=row[0], name=row[1], category=row[2], unit=row[3],
                unit_cost=Decimal(str(row[4])), supplier_id=row[5],
                lead_time_days=row[6], minimum_order_quantity=row[7],
                waste_factor=row[8], availability=row[9],
                specifications=json.loads(row[10] or '{}')
            )
        return None
    
    def search_materials(self, category: str = "", name: str = "") -> List[Material]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        sql = "SELECT * FROM materials WHERE 1=1"
        params = []
        
        if category:
            sql += " AND category LIKE ?"
            params.append(f"%{category}%")
        
        if name:
            sql += " AND name LIKE ?"
            params.append(f"%{name}%")
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()
        
        materials = []
        for row in rows:
            materials.append(Material(
                id=row[0], name=row[1], category=row[2], unit=row[3],
                unit_cost=Decimal(str(row[4])), supplier_id=row[5],
                lead_time_days=row[6], minimum_order_quantity=row[7],
                waste_factor=row[8], availability=row[9],
                specifications=json.loads(row[10] or '{}')
            ))
        
        return materials
    
    def get_labor_rates(self, role: str = "", location: str = "") -> List[LaborRate]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        sql = "SELECT * FROM labor_rates WHERE 1=1"
        params = []
        
        if role:
            sql += " AND role LIKE ?"
            params.append(f"%{role}%")
        
        if location:
            sql += " AND location = ?"
            params.append(location)
        
        sql += " ORDER BY effective_date DESC"
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()
        
        labor_rates = []
        for row in rows:
            labor_rates.append(LaborRate(
                id=row[0], role=row[1], skill_level=row[2],
                hourly_rate=Decimal(str(row[3])), burden_rate=row[4],
                efficiency_factor=row[5], location=row[6],
                effective_date=datetime.fromisoformat(row[7])
            ))
        
        return labor_rates
    
    def save_estimate(self, estimate: CostEstimate) -> str:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO cost_estimates
            (id, project_name, description, estimation_method, accuracy_level,
             total_cost, contingency_percentage, contingency_amount, final_cost,
             created_by, created_at, updated_at, valid_until, assumptions, exclusions, risks)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            estimate.id, estimate.project_name, estimate.description,
            estimate.estimation_method.value, estimate.accuracy_level.value,
            float(estimate.total_cost), estimate.contingency_percentage,
            float(estimate.contingency_amount), float(estimate.final_cost),
            estimate.created_by, estimate.created_at.isoformat(),
            estimate.updated_at.isoformat(),
            estimate.valid_until.isoformat() if estimate.valid_until else None,
            json.dumps(estimate.assumptions), json.dumps(estimate.exclusions),
            json.dumps(estimate.risks)
        ))
        
        # Delete existing cost items for this estimate
        cursor.execute("DELETE FROM cost_items WHERE estimate_id = ?", (estimate.id,))
        
        # Insert cost items
        for item in estimate.cost_items:
            cursor.execute("""
                INSERT INTO cost_items
                (id, estimate_id, name, category, quantity, unit, unit_cost,
                 total_cost, description, source, risk_factor, confidence_level, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.id, estimate.id, item.name, item.category.value,
                float(item.quantity), item.unit, float(item.unit_cost),
                float(item.total_cost), item.description, item.source,
                item.risk_factor, item.confidence_level, item.notes
            ))
        
        conn.commit()
        conn.close()
        return estimate.id


class MaterialCostCalculator:
    def __init__(self, database: CostDatabase):
        self.database = database
    
    def calculate_material_cost(self, material_id: str, quantity: Decimal,
                              include_waste: bool = True, bulk_discount: float = 0.0) -> CostItem:
        """Calculate cost for a specific material"""
        material = self.database.get_material(material_id)
        if not material:
            raise ValueError(f"Material not found: {material_id}")
        
        # Adjust quantity for minimum order
        actual_quantity = max(quantity, Decimal(str(material.minimum_order_quantity)))
        
        # Apply waste factor
        if include_waste:
            actual_quantity = actual_quantity * Decimal(str(1 + material.waste_factor))
        
        # Calculate unit cost with bulk discount
        unit_cost = material.unit_cost * Decimal(str(1 - bulk_discount))
        total_cost = actual_quantity * unit_cost
        
        return CostItem(
            id=str(uuid.uuid4()),
            name=material.name,
            category=CostCategory.MATERIALS,
            quantity=actual_quantity,
            unit=material.unit,
            unit_cost=unit_cost,
            total_cost=total_cost,
            description=f"Material: {material.name} ({material.category})",
            source=material_id,
            confidence_level=0.9 if material.availability == "available" else 0.7
        )
    
    def estimate_material_costs_by_category(self, requirements: Dict[str, Dict[str, Any]]) -> List[CostItem]:
        """Estimate material costs based on category requirements"""
        cost_items = []
        
        for category, req in requirements.items():
            materials = self.database.search_materials(category=category)
            if not materials:
                continue
            
            # Use the most cost-effective material in category
            materials.sort(key=lambda x: x.unit_cost)
            selected_material = materials[0]
            
            quantity = Decimal(str(req.get('quantity', 1)))
            cost_item = self.calculate_material_cost(
                selected_material.id, quantity,
                include_waste=req.get('include_waste', True),
                bulk_discount=req.get('bulk_discount', 0.0)
            )
            
            cost_items.append(cost_item)
        
        return cost_items


class LaborCostCalculator:
    def __init__(self, database: CostDatabase):
        self.database = database
    
    def calculate_labor_cost(self, role: str, hours: Decimal, location: str = "default",
                           skill_level: str = "", overtime_factor: float = 1.0) -> CostItem:
        """Calculate labor cost for a specific role"""
        labor_rates = self.database.get_labor_rates(role=role, location=location)
        if not labor_rates:
            raise ValueError(f"No labor rates found for role: {role}")
        
        # Filter by skill level if specified
        if skill_level:
            filtered_rates = [lr for lr in labor_rates if lr.skill_level == skill_level]
            if filtered_rates:
                labor_rates = filtered_rates
        
        # Use the most recent rate
        labor_rate = labor_rates[0]
        
        # Calculate effective hourly rate with burden
        effective_rate = labor_rate.hourly_rate * Decimal(str(1 + labor_rate.burden_rate))
        
        # Apply efficiency and overtime factors
        effective_rate = effective_rate / Decimal(str(labor_rate.efficiency_factor))
        effective_rate = effective_rate * Decimal(str(overtime_factor))
        
        total_cost = hours * effective_rate
        
        return CostItem(
            id=str(uuid.uuid4()),
            name=f"{role} ({skill_level or 'standard'})",
            category=CostCategory.LABOR,
            quantity=hours,
            unit="hours",
            unit_cost=effective_rate,
            total_cost=total_cost,
            description=f"Labor: {role} at {location}",
            source=labor_rate.id,
            confidence_level=0.85
        )
    
    def estimate_project_labor(self, labor_requirements: List[Dict[str, Any]]) -> List[CostItem]:
        """Estimate labor costs for a project"""
        cost_items = []
        
        for req in labor_requirements:
            role = req['role']
            hours = Decimal(str(req['hours']))
            location = req.get('location', 'default')
            skill_level = req.get('skill_level', '')
            overtime_factor = req.get('overtime_factor', 1.0)
            
            try:
                cost_item = self.calculate_labor_cost(
                    role, hours, location, skill_level, overtime_factor
                )
                cost_items.append(cost_item)
            except ValueError as e:
                logging.warning(f"Could not calculate labor cost: {e}")
                
                # Create placeholder cost item
                placeholder_item = CostItem(
                    id=str(uuid.uuid4()),
                    name=f"{role} (estimated)",
                    category=CostCategory.LABOR,
                    quantity=hours,
                    unit="hours",
                    unit_cost=Decimal("50.00"),  # Default estimate
                    total_cost=hours * Decimal("50.00"),
                    description=f"Estimated labor: {role}",
                    confidence_level=0.5,
                    notes="No specific rate found - using estimate"
                )
                cost_items.append(placeholder_item)
        
        return cost_items


class OverheadCalculator:
    def __init__(self):
        self.overhead_rates = {
            'facilities': 0.15,      # 15% of direct costs
            'utilities': 0.05,       # 5% of direct costs
            'insurance': 0.03,       # 3% of direct costs
            'administration': 0.10,   # 10% of direct costs
            'general': 0.05          # 5% of direct costs
        }
    
    def calculate_overhead(self, direct_costs: Decimal, overhead_rate: float = None) -> List[CostItem]:
        """Calculate overhead costs"""
        if overhead_rate is None:
            overhead_rate = sum(self.overhead_rates.values())
        
        cost_items = []
        
        if overhead_rate > 0:
            total_overhead = direct_costs * Decimal(str(overhead_rate))
            
            overhead_item = CostItem(
                id=str(uuid.uuid4()),
                name="Project Overhead",
                category=CostCategory.OVERHEAD,
                quantity=Decimal("1"),
                unit="lump sum",
                unit_cost=total_overhead,
                total_cost=total_overhead,
                description=f"Overhead ({overhead_rate*100:.1f}% of direct costs)",
                confidence_level=0.8
            )
            cost_items.append(overhead_item)
        
        return cost_items


class RiskAnalyzer:
    def __init__(self):
        self.risk_factors = {
            'schedule_risk': {'weight': 0.3, 'impact_range': (0.05, 0.25)},
            'technical_risk': {'weight': 0.25, 'impact_range': (0.10, 0.40)},
            'market_risk': {'weight': 0.20, 'impact_range': (0.05, 0.20)},
            'supplier_risk': {'weight': 0.15, 'impact_range': (0.05, 0.30)},
            'regulatory_risk': {'weight': 0.10, 'impact_range': (0.10, 0.50)}
        }
    
    def analyze_project_risks(self, project_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze project risks and their cost impact"""
        risks = []
        
        # Schedule Risk
        duration_months = project_data.get('duration_months', 6)
        if duration_months > 12:
            risk_impact = 0.15  # 15% cost increase for long projects
            risks.append({
                'type': 'schedule_risk',
                'description': 'Extended project timeline increases costs',
                'probability': 0.6,
                'impact': risk_impact,
                'mitigation': 'Implement milestone-based tracking'
            })
        
        # Technical Risk
        complexity = project_data.get('technical_complexity', 'medium')
        complexity_map = {'low': 0.05, 'medium': 0.10, 'high': 0.20, 'very_high': 0.35}
        if complexity in complexity_map:
            risks.append({
                'type': 'technical_risk',
                'description': f'Technical complexity: {complexity}',
                'probability': 0.4 if complexity == 'low' else 0.7,
                'impact': complexity_map[complexity],
                'mitigation': 'Prototype critical components early'
            })
        
        # Market Risk
        if project_data.get('new_market', False):
            risks.append({
                'type': 'market_risk',
                'description': 'Entering new market segment',
                'probability': 0.5,
                'impact': 0.15,
                'mitigation': 'Conduct market research and validation'
            })
        
        return risks
    
    def calculate_contingency(self, base_cost: Decimal, risks: List[Dict[str, Any]],
                            accuracy_level: CostAccuracy) -> Tuple[float, Decimal]:
        """Calculate contingency percentage and amount"""
        # Base contingency by accuracy level
        base_contingency = {
            CostAccuracy.ROUGH: 0.30,      # 30%
            CostAccuracy.BUDGET: 0.20,     # 20%
            CostAccuracy.DEFINITIVE: 0.15, # 15%
            CostAccuracy.DETAILED: 0.10    # 10%
        }
        
        contingency_pct = base_contingency.get(accuracy_level, 0.20)
        
        # Add risk-based contingency
        risk_adjustment = 0.0
        for risk in risks:
            expected_impact = risk['probability'] * risk['impact']
            risk_adjustment += expected_impact
        
        final_contingency_pct = contingency_pct + risk_adjustment
        contingency_amount = base_cost * Decimal(str(final_contingency_pct))
        
        return final_contingency_pct, contingency_amount


class CostCalculator:
    def __init__(self, data_dir: str = "cost_data"):
        self.data_dir = data_dir
        self.database = CostDatabase()
        self.material_calculator = MaterialCostCalculator(self.database)
        self.labor_calculator = LaborCostCalculator(self.database)
        self.overhead_calculator = OverheadCalculator()
        self.risk_analyzer = RiskAnalyzer()
        
        # Callbacks
        self.on_estimate_created: Optional[Callable] = None
        self.on_cost_updated: Optional[Callable] = None
        
        # Ensure directory exists
        os.makedirs(data_dir, exist_ok=True)
        
        logging.info("Cost Calculator initialized")
    
    def create_estimate(self, project_data: Dict[str, Any]) -> CostEstimate:
        """Create a comprehensive cost estimate"""
        try:
            estimate_id = str(uuid.uuid4())
            cost_items = []
            
            # Calculate material costs
            if 'materials' in project_data:
                if isinstance(project_data['materials'], list):
                    # Specific materials list
                    for material_req in project_data['materials']:
                        cost_item = self.material_calculator.calculate_material_cost(
                            material_req['id'],
                            Decimal(str(material_req['quantity'])),
                            material_req.get('include_waste', True),
                            material_req.get('bulk_discount', 0.0)
                        )
                        cost_items.append(cost_item)
                else:
                    # Category-based materials
                    material_items = self.material_calculator.estimate_material_costs_by_category(
                        project_data['materials']
                    )
                    cost_items.extend(material_items)
            
            # Calculate labor costs
            if 'labor' in project_data:
                labor_items = self.labor_calculator.estimate_project_labor(project_data['labor'])
                cost_items.extend(labor_items)
            
            # Calculate direct costs (materials + labor + equipment)
            direct_cost = sum(item.total_cost for item in cost_items)
            
            # Calculate overhead
            overhead_rate = project_data.get('overhead_rate', None)
            overhead_items = self.overhead_calculator.calculate_overhead(direct_cost, overhead_rate)
            cost_items.extend(overhead_items)
            
            # Calculate shipping if specified
            if 'shipping' in project_data:
                shipping_cost = Decimal(str(project_data['shipping']['cost']))
                shipping_item = CostItem(
                    id=str(uuid.uuid4()),
                    name="Shipping & Logistics",
                    category=CostCategory.SHIPPING,
                    quantity=Decimal("1"),
                    unit="lump sum",
                    unit_cost=shipping_cost,
                    total_cost=shipping_cost,
                    description=project_data['shipping'].get('description', 'Shipping costs'),
                    confidence_level=0.9
                )
                cost_items.append(shipping_item)
            
            # Calculate base total
            base_total = sum(item.total_cost for item in cost_items)
            
            # Analyze risks and calculate contingency
            risks = self.risk_analyzer.analyze_project_risks(project_data)
            accuracy_level = CostAccuracy(project_data.get('accuracy_level', 'budget'))
            contingency_pct, contingency_amount = self.risk_analyzer.calculate_contingency(
                base_total, risks, accuracy_level
            )
            
            # Add contingency as cost item
            contingency_item = CostItem(
                id=str(uuid.uuid4()),
                name="Contingency",
                category=CostCategory.CONTINGENCY,
                quantity=Decimal("1"),
                unit="percentage",
                unit_cost=contingency_amount,
                total_cost=contingency_amount,
                description=f"Risk contingency ({contingency_pct*100:.1f}%)",
                confidence_level=0.7
            )
            cost_items.append(contingency_item)
            
            # Calculate final cost
            final_cost = base_total + contingency_amount
            
            # Create estimate
            estimate = CostEstimate(
                id=estimate_id,
                project_name=project_data['project_name'],
                description=project_data.get('description', ''),
                estimation_method=EstimationMethod(project_data.get('estimation_method', 'bottom_up')),
                accuracy_level=accuracy_level,
                cost_items=cost_items,
                total_cost=base_total,
                contingency_percentage=contingency_pct,
                contingency_amount=contingency_amount,
                final_cost=final_cost,
                created_by=project_data.get('created_by', 'system'),
                created_at=datetime.now(),
                updated_at=datetime.now(),
                valid_until=datetime.now() + timedelta(days=project_data.get('validity_days', 30)),
                assumptions=project_data.get('assumptions', []),
                exclusions=project_data.get('exclusions', []),
                risks=[asdict(risk) for risk in risks] if risks else []
            )
            
            # Save to database
            self.database.save_estimate(estimate)
            
            # Trigger callback
            if self.on_estimate_created:
                self.on_estimate_created(estimate)
            
            logging.info(f"Cost estimate created: {estimate.project_name} - ${final_cost:,.2f}")
            return estimate
            
        except Exception as e:
            logging.error(f"Error creating cost estimate: {e}")
            raise
    
    def generate_cost_breakdown(self, estimate: CostEstimate) -> CostBreakdown:
        """Generate cost breakdown by category"""
        breakdown = CostBreakdown(
            materials=Decimal("0"),
            labor=Decimal("0"),
            equipment=Decimal("0"),
            overhead=Decimal("0"),
            shipping=Decimal("0"),
            taxes=Decimal("0"),
            contingency=Decimal("0"),
            profit=Decimal("0"),
            total=Decimal("0")
        )
        
        for item in estimate.cost_items:
            if item.category == CostCategory.MATERIALS:
                breakdown.materials += item.total_cost
            elif item.category == CostCategory.LABOR:
                breakdown.labor += item.total_cost
            elif item.category == CostCategory.EQUIPMENT:
                breakdown.equipment += item.total_cost
            elif item.category == CostCategory.OVERHEAD:
                breakdown.overhead += item.total_cost
            elif item.category == CostCategory.SHIPPING:
                breakdown.shipping += item.total_cost
            elif item.category == CostCategory.TAXES:
                breakdown.taxes += item.total_cost
            elif item.category == CostCategory.CONTINGENCY:
                breakdown.contingency += item.total_cost
            elif item.category == CostCategory.PROFIT:
                breakdown.profit += item.total_cost
        
        breakdown.total = estimate.final_cost
        return breakdown
    
    def compare_estimates(self, estimate_ids: List[str]) -> Dict[str, Any]:
        """Compare multiple cost estimates"""
        # This would load estimates from database and compare them
        # Simplified implementation
        comparison = {
            'estimates': estimate_ids,
            'comparison_date': datetime.now().isoformat(),
            'summary': {
                'lowest_cost': None,
                'highest_cost': None,
                'average_cost': None,
                'cost_variance': None
            }
        }
        
        return comparison
    
    def sensitivity_analysis(self, estimate: CostEstimate, 
                           variables: List[str] = None) -> Dict[str, Any]:
        """Perform sensitivity analysis on cost estimate"""
        if not variables:
            variables = ['materials', 'labor', 'overhead']
        
        analysis = {
            'base_estimate': float(estimate.final_cost),
            'sensitivity_results': {},
            'analysis_date': datetime.now().isoformat()
        }
        
        # Test ±10% and ±20% variations
        for variable in variables:
            analysis['sensitivity_results'][variable] = {}
            
            for variation in [-0.20, -0.10, 0.10, 0.20]:
                # Calculate impact (simplified)
                category_total = sum(
                    item.total_cost for item in estimate.cost_items
                    if variable in item.category.value
                )
                
                variation_impact = category_total * Decimal(str(variation))
                new_total = estimate.final_cost + variation_impact
                
                analysis['sensitivity_results'][variable][f"{variation:+.0%}"] = {
                    'new_total': float(new_total),
                    'impact': float(variation_impact),
                    'percentage_change': float((new_total - estimate.final_cost) / estimate.final_cost)
                }
        
        return analysis
    
    def load_sample_data(self):
        """Load sample materials and labor rates for testing"""
        # Sample materials
        materials = [
            Material("mat_001", "Steel Sheet 1mm", "metals", "m2", Decimal("15.50")),
            Material("mat_002", "Aluminum Extrusion", "metals", "m", Decimal("8.25")),
            Material("mat_003", "PVC Pipe 50mm", "plastics", "m", Decimal("3.75")),
            Material("mat_004", "Electronic PCB", "electronics", "pcs", Decimal("12.00")),
            Material("mat_005", "Fastener M6", "hardware", "pcs", Decimal("0.25"))
        ]
        
        for material in materials:
            self.database.add_material(material)
        
        # Sample labor rates
        labor_rates = [
            LaborRate("lab_001", "Welder", "certified", Decimal("35.00")),
            LaborRate("lab_002", "Machinist", "experienced", Decimal("42.00")),
            LaborRate("lab_003", "Engineer", "senior", Decimal("75.00")),
            LaborRate("lab_004", "Technician", "standard", Decimal("28.00")),
            LaborRate("lab_005", "Project Manager", "senior", Decimal("85.00"))
        ]
        
        for labor_rate in labor_rates:
            self.database.add_labor_rate(labor_rate)
        
        logging.info("Sample cost data loaded")
    
    def export_estimate(self, estimate_id: str, format: str = 'json') -> Optional[str]:
        """Export cost estimate to file"""
        # This would retrieve the estimate and export it
        # Simplified implementation
        export_path = os.path.join(self.data_dir, f"estimate_{estimate_id}.{format}")
        
        if format == 'json':
            # Would export actual estimate data
            with open(export_path, 'w') as f:
                json.dump({'estimate_id': estimate_id, 'exported_at': datetime.now().isoformat()}, f, indent=2)
        
        return export_path
    
    def get_cost_trends(self, category: str = None, days: int = 90) -> Dict[str, Any]:
        """Get cost trends over time"""
        # This would analyze historical cost data
        # Simplified implementation
        trends = {
            'category': category or 'all',
            'period_days': days,
            'trend_direction': 'stable',
            'average_change_percent': 0.0,
            'analysis_date': datetime.now().isoformat()
        }
        
        return trends


# Demo function
async def demo_cost_calculator():
    """Demonstrate Cost Calculator functionality"""
    print("=== Cost Calculator Demo ===")
    
    calculator = CostCalculator()
    
    # Set up callbacks
    calculator.on_estimate_created = lambda est: print(f"Estimate created: {est.project_name} - ${est.final_cost:,.2f}")
    
    # Load sample data
    calculator.load_sample_data()
    
    # Create sample project estimate
    project_data = {
        'project_name': 'Custom Manufacturing Project',
        'description': 'Manufacturing of 100 custom metal brackets',
        'estimation_method': 'bottom_up',
        'accuracy_level': 'budget',
        'materials': [
            {'id': 'mat_001', 'quantity': 50, 'include_waste': True},
            {'id': 'mat_005', 'quantity': 400, 'bulk_discount': 0.05}
        ],
        'labor': [
            {'role': 'Welder', 'hours': 20, 'skill_level': 'certified'},
            {'role': 'Machinist', 'hours': 15, 'skill_level': 'experienced'},
            {'role': 'Engineer', 'hours': 5, 'skill_level': 'senior'}
        ],
        'shipping': {
            'cost': 150.00,
            'description': 'Ground shipping to customer site'
        },
        'technical_complexity': 'medium',
        'duration_months': 2,
        'created_by': 'demo_user',
        'assumptions': [
            'Material prices remain stable',
            'No design changes during production'
        ],
        'exclusions': [
            'Customer site installation',
            'Extended warranty coverage'
        ]
    }
    
    # Create estimate
    estimate = calculator.create_estimate(project_data)
    
    # Generate breakdown
    breakdown = calculator.generate_cost_breakdown(estimate)
    print(f"Cost breakdown - Materials: ${breakdown.materials:,.2f}, Labor: ${breakdown.labor:,.2f}")
    
    # Perform sensitivity analysis
    sensitivity = calculator.sensitivity_analysis(estimate)
    print(f"Sensitivity analysis completed for {len(sensitivity['sensitivity_results'])} variables")
    
    # Export estimate
    export_path = calculator.export_estimate(estimate.id)
    print(f"Estimate exported to: {export_path}")
    
    print("Cost Calculator demo completed")


if __name__ == "__main__":
    asyncio.run(demo_cost_calculator())