#!/usr/bin/env python3
"""
ActiveLog Manufacturing Suite - Carbon Footprint Tracker

Comprehensive system for tracking, analyzing, and optimizing carbon emissions
across the entire manufacturing lifecycle from materials to disposal.
"""

import asyncio
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
from pathlib import Path
import aiohttp
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
warnings.filterwarnings('ignore')


class EmissionScope(Enum):
    SCOPE_1 = "scope_1"  # Direct emissions
    SCOPE_2 = "scope_2"  # Indirect energy emissions
    SCOPE_3 = "scope_3"  # Other indirect emissions


class EmissionCategory(Enum):
    RAW_MATERIALS = "raw_materials"
    MANUFACTURING = "manufacturing"
    TRANSPORTATION = "transportation"
    PACKAGING = "packaging"
    ENERGY = "energy"
    WASTE = "waste"
    WATER = "water"
    END_OF_LIFE = "end_of_life"


class TransportMode(Enum):
    TRUCK = "truck"
    RAIL = "rail"
    SHIP = "ship"
    AIR = "air"
    PIPELINE = "pipeline"


class EnergySource(Enum):
    GRID_ELECTRICITY = "grid_electricity"
    RENEWABLE = "renewable"
    NATURAL_GAS = "natural_gas"
    COAL = "coal"
    OIL = "oil"
    NUCLEAR = "nuclear"


class WasteType(Enum):
    LANDFILL = "landfill"
    RECYCLING = "recycling"
    INCINERATION = "incineration"
    COMPOSTING = "composting"
    HAZARDOUS = "hazardous"


@dataclass
class Material:
    material_id: str
    name: str
    category: str
    carbon_factor_kg_co2_per_kg: float
    density_kg_per_m3: Optional[float]
    renewable_content: float  # 0.0 to 1.0
    recyclable: bool
    biodegradable: bool
    source_region: str
    supplier_id: str


@dataclass
class CarbonEmissionRecord:
    emission_id: str
    timestamp: datetime
    scope: EmissionScope
    category: EmissionCategory
    emission_kg_co2: float
    activity_description: str
    activity_quantity: float
    activity_unit: str
    source_id: str  # Material, process, transport, etc.
    calculation_method: str
    confidence_level: float  # 0.0 to 1.0
    verification_status: str


@dataclass
class TransportEmission:
    transport_id: str
    origin: str
    destination: str
    distance_km: float
    mode: TransportMode
    cargo_weight_kg: float
    fuel_consumption: float
    fuel_type: str
    emission_kg_co2: float
    efficiency_improvement: Optional[float] = None


@dataclass
class EnergyConsumption:
    consumption_id: str
    timestamp: datetime
    facility_id: str
    process_id: str
    energy_source: EnergySource
    consumption_kwh: float
    emission_factor_kg_co2_per_kwh: float
    emission_kg_co2: float
    renewable_percentage: float


@dataclass
class WasteGeneration:
    waste_id: str
    timestamp: datetime
    waste_type: WasteType
    quantity_kg: float
    material_composition: Dict[str, float]
    disposal_method: str
    emission_kg_co2: float
    cost_per_kg: float


@dataclass
class ProductCarbonFootprint:
    product_id: str
    product_name: str
    functional_unit: str
    total_emission_kg_co2: float
    scope_breakdown: Dict[EmissionScope, float]
    category_breakdown: Dict[EmissionCategory, float]
    lifecycle_stages: Dict[str, float]
    calculation_date: datetime
    confidence_score: float
    improvement_opportunities: List[str]


@dataclass
class SustainabilityMetrics:
    metrics_date: datetime
    total_emissions_kg_co2: float
    emissions_per_unit: float
    emissions_per_revenue: float
    renewable_energy_percentage: float
    waste_to_landfill_percentage: float
    recycling_rate: float
    carbon_intensity_trend: float
    target_achievement: float


class EmissionFactorDatabase:
    """Database of emission factors for various materials, processes, and activities"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.factors = {}
        self._initialize_factors()
    
    def _initialize_factors(self):
        """Initialize emission factors database"""
        # Material emission factors (kg CO2 per kg material)
        self.factors['materials'] = {
            'aluminum': 8.24,
            'steel': 1.85,
            'plastic_pp': 1.95,
            'plastic_pe': 1.96,
            'plastic_pet': 2.30,
            'copper': 3.20,
            'glass': 0.85,
            'wood': -0.85,  # Negative for carbon sequestration
            'concrete': 0.93,
            'paper': 0.70,
            'cardboard': 0.63
        }
        
        # Energy emission factors (kg CO2 per kWh)
        self.factors['energy'] = {
            'grid_electricity_us': 0.42,
            'grid_electricity_eu': 0.28,
            'natural_gas': 0.18,
            'coal': 0.82,
            'oil': 0.27,
            'renewable': 0.02,  # Solar/wind with lifecycle emissions
            'nuclear': 0.012
        }
        
        # Transport emission factors (kg CO2 per tonne-km)
        self.factors['transport'] = {
            'truck': 0.096,
            'rail': 0.028,
            'ship': 0.015,
            'air': 0.678,
            'pipeline': 0.004
        }
        
        # Process emission factors (kg CO2 per unit)
        self.factors['processes'] = {
            'injection_molding': 0.5,  # per kg of plastic
            'machining': 0.3,  # per kg of material removed
            'welding': 0.8,  # per meter of weld
            'painting': 1.2,  # per m2 painted
            'assembly': 0.1,  # per assembly operation
            'packaging': 0.05  # per package
        }
        
        # Waste treatment emission factors (kg CO2 per kg waste)
        self.factors['waste_treatment'] = {
            'landfill': 0.57,
            'incineration': 0.025,
            'recycling': -0.5,  # Credit for avoided virgin material
            'composting': 0.15,
            'hazardous_treatment': 2.1
        }
    
    async def get_emission_factor(self, category: str, item: str, region: str = "global") -> float:
        """Get emission factor for specific item"""
        if category in self.factors and item in self.factors[category]:
            base_factor = self.factors[category][item]
            
            # Apply regional adjustments if available
            regional_adjustment = await self._get_regional_adjustment(category, region)
            
            return base_factor * regional_adjustment
        
        # If not found, try to fetch from external API
        return await self._fetch_external_factor(category, item, region)
    
    async def _get_regional_adjustment(self, category: str, region: str) -> float:
        """Get regional adjustment factor"""
        regional_factors = {
            'energy': {
                'us': 1.0,
                'eu': 0.67,
                'china': 1.5,
                'global': 1.0
            },
            'transport': {
                'us': 1.0,
                'eu': 0.9,
                'asia': 1.1,
                'global': 1.0
            }
        }
        
        if category in regional_factors and region.lower() in regional_factors[category]:
            return regional_factors[category][region.lower()]
        
        return 1.0  # Default multiplier
    
    async def _fetch_external_factor(self, category: str, item: str, region: str) -> float:
        """Fetch emission factor from external API if available"""
        # In production, this would connect to emission factor APIs
        # For now, return a default factor based on category
        default_factors = {
            'materials': 2.0,
            'energy': 0.4,
            'transport': 0.1,
            'processes': 0.5,
            'waste_treatment': 0.3
        }
        
        return default_factors.get(category, 1.0)


class CarbonCalculator:
    """Carbon footprint calculation engine"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.emission_factors = EmissionFactorDatabase(db_path)
    
    async def calculate_material_emissions(self, material_id: str, quantity_kg: float,
                                         region: str = "global") -> float:
        """Calculate emissions from material usage"""
        # Get material data
        material = await self._get_material_data(material_id)
        
        if not material:
            # Use generic factor if material not found
            factor = await self.emission_factors.get_emission_factor(
                'materials', 'generic', region
            )
        else:
            factor = material.carbon_factor_kg_co2_per_kg
        
        # Apply regional adjustment
        regional_factor = await self.emission_factors._get_regional_adjustment(
            'materials', region
        )
        
        base_emissions = quantity_kg * factor * regional_factor
        
        # Apply renewable content reduction if applicable
        if material and material.renewable_content > 0:
            renewable_reduction = base_emissions * material.renewable_content * 0.3
            base_emissions -= renewable_reduction
        
        return max(0, base_emissions)
    
    async def calculate_energy_emissions(self, energy_source: EnergySource,
                                       consumption_kwh: float, region: str = "global") -> float:
        """Calculate emissions from energy consumption"""
        factor = await self.emission_factors.get_emission_factor(
            'energy', energy_source.value, region
        )
        
        return consumption_kwh * factor
    
    async def calculate_transport_emissions(self, origin: str, destination: str,
                                          distance_km: float, cargo_kg: float,
                                          mode: TransportMode) -> float:
        """Calculate emissions from transportation"""
        factor = await self.emission_factors.get_emission_factor(
            'transport', mode.value
        )
        
        # Convert cargo weight to tonnes
        cargo_tonnes = cargo_kg / 1000.0
        
        return distance_km * cargo_tonnes * factor
    
    async def calculate_process_emissions(self, process_type: str, quantity: float,
                                        unit: str) -> float:
        """Calculate emissions from manufacturing processes"""
        factor = await self.emission_factors.get_emission_factor(
            'processes', process_type
        )
        
        return quantity * factor
    
    async def calculate_waste_emissions(self, waste_type: WasteType, quantity_kg: float,
                                      material_composition: Dict[str, float]) -> float:
        """Calculate emissions from waste treatment"""
        factor = await self.emission_factors.get_emission_factor(
            'waste_treatment', waste_type.value
        )
        
        base_emissions = quantity_kg * factor
        
        # Adjust for material composition
        if material_composition:
            weighted_emissions = 0
            for material, percentage in material_composition.items():
                material_factor = await self.emission_factors.get_emission_factor(
                    'materials', material
                )
                weighted_emissions += base_emissions * percentage * (material_factor / 2.0)
            
            return weighted_emissions
        
        return base_emissions
    
    async def calculate_product_footprint(self, product_id: str) -> ProductCarbonFootprint:
        """Calculate complete carbon footprint for a product"""
        # Get product data and bill of materials
        product_data = await self._get_product_data(product_id)
        bom = await self._get_bill_of_materials(product_id)
        
        scope_emissions = {scope: 0.0 for scope in EmissionScope}
        category_emissions = {category: 0.0 for category in EmissionCategory}
        lifecycle_emissions = {}
        total_emissions = 0.0
        improvement_opportunities = []
        
        # Calculate material emissions
        materials_emissions = 0.0
        for material_item in bom:
            material_emission = await self.calculate_material_emissions(
                material_item['material_id'],
                material_item['quantity_kg'],
                material_item.get('region', 'global')
            )
            materials_emissions += material_emission
        
        scope_emissions[EmissionScope.SCOPE_3] += materials_emissions
        category_emissions[EmissionCategory.RAW_MATERIALS] = materials_emissions
        lifecycle_emissions['materials'] = materials_emissions
        
        # Calculate manufacturing emissions
        manufacturing_emissions = await self._calculate_manufacturing_emissions(product_id)
        scope_emissions[EmissionScope.SCOPE_1] += manufacturing_emissions['direct']
        scope_emissions[EmissionScope.SCOPE_2] += manufacturing_emissions['energy']
        category_emissions[EmissionCategory.MANUFACTURING] = manufacturing_emissions['total']
        lifecycle_emissions['manufacturing'] = manufacturing_emissions['total']
        
        # Calculate transportation emissions
        transport_emissions = await self._calculate_transport_emissions(product_id)
        scope_emissions[EmissionScope.SCOPE_3] += transport_emissions
        category_emissions[EmissionCategory.TRANSPORTATION] = transport_emissions
        lifecycle_emissions['transportation'] = transport_emissions
        
        # Calculate packaging emissions
        packaging_emissions = await self._calculate_packaging_emissions(product_id)
        scope_emissions[EmissionScope.SCOPE_3] += packaging_emissions
        category_emissions[EmissionCategory.PACKAGING] = packaging_emissions
        lifecycle_emissions['packaging'] = packaging_emissions
        
        # Calculate use phase emissions (if applicable)
        use_emissions = await self._calculate_use_phase_emissions(product_id)
        scope_emissions[EmissionScope.SCOPE_3] += use_emissions
        lifecycle_emissions['use_phase'] = use_emissions
        
        # Calculate end-of-life emissions
        eol_emissions = await self._calculate_end_of_life_emissions(product_id)
        scope_emissions[EmissionScope.SCOPE_3] += eol_emissions
        category_emissions[EmissionCategory.END_OF_LIFE] = eol_emissions
        lifecycle_emissions['end_of_life'] = eol_emissions
        
        total_emissions = sum(scope_emissions.values())
        
        # Identify improvement opportunities
        improvement_opportunities = await self._identify_improvement_opportunities(
            category_emissions, lifecycle_emissions
        )
        
        # Calculate confidence score
        confidence_score = await self._calculate_confidence_score(product_id)
        
        return ProductCarbonFootprint(
            product_id=product_id,
            product_name=product_data.get('name', 'Unknown Product'),
            functional_unit=product_data.get('functional_unit', 'per unit'),
            total_emission_kg_co2=total_emissions,
            scope_breakdown=scope_emissions,
            category_breakdown=category_emissions,
            lifecycle_stages=lifecycle_emissions,
            calculation_date=datetime.now(),
            confidence_score=confidence_score,
            improvement_opportunities=improvement_opportunities
        )
    
    async def _get_material_data(self, material_id: str) -> Optional[Material]:
        """Get material data from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM materials WHERE material_id = ?", (material_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Material(
                material_id=row[0],
                name=row[1],
                category=row[2],
                carbon_factor_kg_co2_per_kg=row[3],
                density_kg_per_m3=row[4],
                renewable_content=row[5],
                recyclable=bool(row[6]),
                biodegradable=bool(row[7]),
                source_region=row[8],
                supplier_id=row[9]
            )
        
        return None
    
    async def _get_product_data(self, product_id: str) -> Dict[str, Any]:
        """Get product data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM products WHERE product_id = ?", (product_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'product_id': row[0],
                'name': row[1],
                'category': row[2],
                'functional_unit': row[3],
                'weight_kg': row[4],
                'volume_m3': row[5]
            }
        
        return {'product_id': product_id, 'name': 'Unknown Product', 'functional_unit': 'per unit'}
    
    async def _get_bill_of_materials(self, product_id: str) -> List[Dict[str, Any]]:
        """Get bill of materials for product"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT material_id, quantity_kg, region
            FROM bill_of_materials 
            WHERE product_id = ?
        """, (product_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'material_id': row[0],
                'quantity_kg': row[1],
                'region': row[2] or 'global'
            }
            for row in rows
        ]
    
    async def _calculate_manufacturing_emissions(self, product_id: str) -> Dict[str, float]:
        """Calculate manufacturing emissions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get manufacturing processes for product
        cursor.execute("""
            SELECT process_type, quantity, unit, energy_kwh, direct_emissions
            FROM manufacturing_processes 
            WHERE product_id = ?
        """, (product_id,))
        
        processes = cursor.fetchall()
        conn.close()
        
        direct_emissions = 0.0
        energy_emissions = 0.0
        
        for process in processes:
            process_type, quantity, unit, energy_kwh, direct_emission = process
            
            # Process emissions
            if direct_emission:
                direct_emissions += direct_emission
            else:
                process_emission = await self.calculate_process_emissions(
                    process_type, quantity, unit
                )
                direct_emissions += process_emission
            
            # Energy emissions
            if energy_kwh:
                energy_emission = await self.calculate_energy_emissions(
                    EnergySource.GRID_ELECTRICITY, energy_kwh
                )
                energy_emissions += energy_emission
        
        return {
            'direct': direct_emissions,
            'energy': energy_emissions,
            'total': direct_emissions + energy_emissions
        }
    
    async def _calculate_transport_emissions(self, product_id: str) -> float:
        """Calculate transportation emissions for product"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT origin, destination, distance_km, mode, cargo_weight_kg
            FROM transportation_routes 
            WHERE product_id = ?
        """, (product_id,))
        
        routes = cursor.fetchall()
        conn.close()
        
        total_transport_emissions = 0.0
        
        for route in routes:
            origin, destination, distance_km, mode, cargo_weight = route
            
            transport_mode = TransportMode(mode)
            emission = await self.calculate_transport_emissions(
                origin, destination, distance_km, cargo_weight, transport_mode
            )
            total_transport_emissions += emission
        
        return total_transport_emissions
    
    async def _calculate_packaging_emissions(self, product_id: str) -> float:
        """Calculate packaging emissions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT material_id, weight_kg
            FROM packaging_materials 
            WHERE product_id = ?
        """, (product_id,))
        
        materials = cursor.fetchall()
        conn.close()
        
        packaging_emissions = 0.0
        
        for material_id, weight_kg in materials:
            emission = await self.calculate_material_emissions(material_id, weight_kg)
            packaging_emissions += emission
        
        return packaging_emissions
    
    async def _calculate_use_phase_emissions(self, product_id: str) -> float:
        """Calculate use phase emissions if product consumes energy"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT energy_consumption_kwh_per_year, product_lifetime_years
            FROM product_use_profile 
            WHERE product_id = ?
        """, (product_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            annual_consumption, lifetime = result
            total_consumption = annual_consumption * lifetime
            
            return await self.calculate_energy_emissions(
                EnergySource.GRID_ELECTRICITY, total_consumption
            )
        
        return 0.0
    
    async def _calculate_end_of_life_emissions(self, product_id: str) -> float:
        """Calculate end-of-life emissions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT bom.material_id, bom.quantity_kg, m.recyclable
            FROM bill_of_materials bom
            JOIN materials m ON bom.material_id = m.material_id
            WHERE bom.product_id = ?
        """, (product_id,))
        
        materials = cursor.fetchall()
        conn.close()
        
        eol_emissions = 0.0
        
        for material_id, quantity_kg, recyclable in materials:
            if recyclable:
                # Assume 70% recycling rate
                recycled_qty = quantity_kg * 0.7
                landfill_qty = quantity_kg * 0.3
                
                recycling_emission = await self.calculate_waste_emissions(
                    WasteType.RECYCLING, recycled_qty, {}
                )
                landfill_emission = await self.calculate_waste_emissions(
                    WasteType.LANDFILL, landfill_qty, {}
                )
                
                eol_emissions += recycling_emission + landfill_emission
            else:
                # All goes to landfill
                landfill_emission = await self.calculate_waste_emissions(
                    WasteType.LANDFILL, quantity_kg, {}
                )
                eol_emissions += landfill_emission
        
        return eol_emissions
    
    async def _identify_improvement_opportunities(self, category_emissions: Dict[EmissionCategory, float],
                                                lifecycle_emissions: Dict[str, float]) -> List[str]:
        """Identify carbon footprint improvement opportunities"""
        opportunities = []
        total_emissions = sum(category_emissions.values())
        
        if total_emissions == 0:
            return opportunities
        
        # Identify highest impact categories
        sorted_categories = sorted(
            category_emissions.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        for category, emissions in sorted_categories[:3]:  # Top 3 categories
            percentage = (emissions / total_emissions) * 100
            
            if category == EmissionCategory.RAW_MATERIALS and percentage > 30:
                opportunities.append("Consider switching to lower-carbon materials")
                opportunities.append("Increase recycled content in materials")
                opportunities.append("Source materials from suppliers with renewable energy")
            
            elif category == EmissionCategory.MANUFACTURING and percentage > 25:
                opportunities.append("Transition to renewable energy in manufacturing")
                opportunities.append("Optimize manufacturing processes for energy efficiency")
                opportunities.append("Implement heat recovery systems")
            
            elif category == EmissionCategory.TRANSPORTATION and percentage > 20:
                opportunities.append("Optimize transportation routes and modes")
                opportunities.append("Use lower-carbon transport modes (rail vs truck)")
                opportunities.append("Source materials and components locally")
            
            elif category == EmissionCategory.PACKAGING and percentage > 15:
                opportunities.append("Reduce packaging materials")
                opportunities.append("Switch to recyclable or biodegradable packaging")
                opportunities.append("Optimize packaging design for transport efficiency")
        
        # Lifecycle-specific opportunities
        if lifecycle_emissions.get('use_phase', 0) > total_emissions * 0.4:
            opportunities.append("Improve product energy efficiency")
            opportunities.append("Design for longer product lifetime")
        
        return opportunities[:5]  # Limit to top 5 opportunities
    
    async def _calculate_confidence_score(self, product_id: str) -> float:
        """Calculate confidence score for carbon footprint calculation"""
        # Simplified confidence calculation based on data availability
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check data completeness
        data_points = 0
        total_possible = 6  # BOM, processes, transport, packaging, use, eol
        
        # BOM completeness
        cursor.execute("SELECT COUNT(*) FROM bill_of_materials WHERE product_id = ?", (product_id,))
        if cursor.fetchone()[0] > 0:
            data_points += 1
        
        # Manufacturing processes
        cursor.execute("SELECT COUNT(*) FROM manufacturing_processes WHERE product_id = ?", (product_id,))
        if cursor.fetchone()[0] > 0:
            data_points += 1
        
        # Transportation
        cursor.execute("SELECT COUNT(*) FROM transportation_routes WHERE product_id = ?", (product_id,))
        if cursor.fetchone()[0] > 0:
            data_points += 1
        
        # Packaging
        cursor.execute("SELECT COUNT(*) FROM packaging_materials WHERE product_id = ?", (product_id,))
        if cursor.fetchone()[0] > 0:
            data_points += 1
        
        # Use profile
        cursor.execute("SELECT COUNT(*) FROM product_use_profile WHERE product_id = ?", (product_id,))
        if cursor.fetchone()[0] > 0:
            data_points += 1
            
        conn.close()
        
        # Base confidence from data completeness
        base_confidence = data_points / total_possible
        
        # Adjust for emission factor quality (simplified)
        factor_quality = 0.8  # Assume good quality factors
        
        return min(1.0, base_confidence * factor_quality)


class SustainabilityAnalyzer:
    """Analyzer for sustainability metrics and trends"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    async def calculate_sustainability_metrics(self, period_days: int = 30) -> SustainabilityMetrics:
        """Calculate comprehensive sustainability metrics"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)
        
        # Total emissions
        total_emissions = await self._get_total_emissions(start_date, end_date)
        
        # Emissions per unit
        units_produced = await self._get_units_produced(start_date, end_date)
        emissions_per_unit = total_emissions / units_produced if units_produced > 0 else 0
        
        # Emissions per revenue
        revenue = await self._get_revenue(start_date, end_date)
        emissions_per_revenue = total_emissions / revenue if revenue > 0 else 0
        
        # Renewable energy percentage
        renewable_percentage = await self._get_renewable_energy_percentage(start_date, end_date)
        
        # Waste metrics
        waste_to_landfill = await self._get_waste_to_landfill_percentage(start_date, end_date)
        recycling_rate = await self._get_recycling_rate(start_date, end_date)
        
        # Carbon intensity trend
        intensity_trend = await self._calculate_carbon_intensity_trend()
        
        # Target achievement
        target_achievement = await self._calculate_target_achievement()
        
        return SustainabilityMetrics(
            metrics_date=datetime.now(),
            total_emissions_kg_co2=total_emissions,
            emissions_per_unit=emissions_per_unit,
            emissions_per_revenue=emissions_per_revenue,
            renewable_energy_percentage=renewable_percentage,
            waste_to_landfill_percentage=waste_to_landfill,
            recycling_rate=recycling_rate,
            carbon_intensity_trend=intensity_trend,
            target_achievement=target_achievement
        )
    
    async def _get_total_emissions(self, start_date: datetime, end_date: datetime) -> float:
        """Get total emissions for period"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT SUM(emission_kg_co2)
            FROM carbon_emissions 
            WHERE timestamp BETWEEN ? AND ?
        """, (start_date, end_date))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result and result[0] else 0.0
    
    async def _get_units_produced(self, start_date: datetime, end_date: datetime) -> int:
        """Get units produced for period"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT SUM(quantity_produced)
            FROM production_records 
            WHERE production_date BETWEEN ? AND ?
        """, (start_date.date(), end_date.date()))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result and result[0] else 0
    
    async def _get_revenue(self, start_date: datetime, end_date: datetime) -> float:
        """Get revenue for period"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT SUM(revenue_amount)
            FROM revenue_records 
            WHERE revenue_date BETWEEN ? AND ?
        """, (start_date.date(), end_date.date()))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result and result[0] else 1.0  # Avoid division by zero
    
    async def _get_renewable_energy_percentage(self, start_date: datetime, end_date: datetime) -> float:
        """Get renewable energy percentage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN energy_source = 'renewable' THEN consumption_kwh ELSE 0 END) as renewable,
                SUM(consumption_kwh) as total
            FROM energy_consumption 
            WHERE timestamp BETWEEN ? AND ?
        """, (start_date, end_date))
        
        result = cursor.fetchone()
        conn.close()
        
        if result and result[1] > 0:
            return (result[0] / result[1]) * 100
        
        return 0.0
    
    async def _get_waste_to_landfill_percentage(self, start_date: datetime, end_date: datetime) -> float:
        """Get percentage of waste going to landfill"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN waste_type = 'landfill' THEN quantity_kg ELSE 0 END) as landfill,
                SUM(quantity_kg) as total
            FROM waste_generation 
            WHERE timestamp BETWEEN ? AND ?
        """, (start_date, end_date))
        
        result = cursor.fetchone()
        conn.close()
        
        if result and result[1] > 0:
            return (result[0] / result[1]) * 100
        
        return 0.0
    
    async def _get_recycling_rate(self, start_date: datetime, end_date: datetime) -> float:
        """Get recycling rate"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN waste_type = 'recycling' THEN quantity_kg ELSE 0 END) as recycled,
                SUM(quantity_kg) as total
            FROM waste_generation 
            WHERE timestamp BETWEEN ? AND ?
        """, (start_date, end_date))
        
        result = cursor.fetchone()
        conn.close()
        
        if result and result[1] > 0:
            return (result[0] / result[1]) * 100
        
        return 0.0
    
    async def _calculate_carbon_intensity_trend(self) -> float:
        """Calculate carbon intensity trend over time"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get monthly carbon intensity for last 6 months
        cursor.execute("""
            SELECT 
                strftime('%Y-%m', ce.timestamp) as month,
                SUM(ce.emission_kg_co2) as emissions,
                SUM(pr.quantity_produced) as production
            FROM carbon_emissions ce
            LEFT JOIN production_records pr ON date(ce.timestamp) = pr.production_date
            WHERE ce.timestamp >= date('now', '-6 months')
            GROUP BY strftime('%Y-%m', ce.timestamp)
            ORDER BY month
        """)
        
        monthly_data = cursor.fetchall()
        conn.close()
        
        if len(monthly_data) < 2:
            return 0.0
        
        # Calculate intensity for each month
        intensities = []
        for month, emissions, production in monthly_data:
            if production and production > 0:
                intensity = emissions / production
                intensities.append(intensity)
        
        if len(intensities) < 2:
            return 0.0
        
        # Calculate trend (slope)
        x = np.arange(len(intensities))
        slope, intercept = np.polyfit(x, intensities, 1)
        
        # Convert to percentage change
        if intensities[0] > 0:
            trend = (slope / intensities[0]) * 100
        else:
            trend = 0.0
        
        return trend
    
    async def _calculate_target_achievement(self) -> float:
        """Calculate carbon reduction target achievement"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current year emissions
        cursor.execute("""
            SELECT SUM(emission_kg_co2)
            FROM carbon_emissions 
            WHERE strftime('%Y', timestamp) = strftime('%Y', 'now')
        """)
        
        current_emissions = cursor.fetchone()[0] or 0
        
        # Get baseline emissions (previous year)
        cursor.execute("""
            SELECT SUM(emission_kg_co2)
            FROM carbon_emissions 
            WHERE strftime('%Y', timestamp) = strftime('%Y', date('now', '-1 year'))
        """)
        
        baseline_emissions = cursor.fetchone()[0] or current_emissions
        
        # Get target reduction percentage (assume 10% annual reduction target)
        target_reduction = 0.10
        target_emissions = baseline_emissions * (1 - target_reduction)
        
        conn.close()
        
        if baseline_emissions > 0 and current_emissions <= target_emissions:
            # Calculate how much of target achieved
            actual_reduction = (baseline_emissions - current_emissions) / baseline_emissions
            achievement = min(1.0, actual_reduction / target_reduction)
            return achievement * 100
        elif baseline_emissions > 0:
            # Behind target
            actual_reduction = (baseline_emissions - current_emissions) / baseline_emissions
            return (actual_reduction / target_reduction) * 100
        
        return 0.0


class CarbonFootprintTracker:
    """Main system for carbon footprint tracking and management"""
    
    def __init__(self, db_path: str = "carbon_footprint.db"):
        self.db_path = db_path
        self.calculator = CarbonCalculator(db_path)
        self.analyzer = SustainabilityAnalyzer(db_path)
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize carbon footprint tracking database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Materials table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS materials (
                material_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                carbon_factor_kg_co2_per_kg REAL,
                density_kg_per_m3 REAL,
                renewable_content REAL,
                recyclable BOOLEAN,
                biodegradable BOOLEAN,
                source_region TEXT,
                supplier_id TEXT
            )
        """)
        
        # Products table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                product_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                functional_unit TEXT,
                weight_kg REAL,
                volume_m3 REAL
            )
        """)
        
        # Bill of materials table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bill_of_materials (
                bom_id TEXT PRIMARY KEY,
                product_id TEXT,
                material_id TEXT,
                quantity_kg REAL,
                region TEXT,
                FOREIGN KEY (product_id) REFERENCES products (product_id),
                FOREIGN KEY (material_id) REFERENCES materials (material_id)
            )
        """)
        
        # Manufacturing processes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS manufacturing_processes (
                process_id TEXT PRIMARY KEY,
                product_id TEXT,
                process_type TEXT,
                quantity REAL,
                unit TEXT,
                energy_kwh REAL,
                direct_emissions REAL,
                FOREIGN KEY (product_id) REFERENCES products (product_id)
            )
        """)
        
        # Transportation routes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transportation_routes (
                route_id TEXT PRIMARY KEY,
                product_id TEXT,
                origin TEXT,
                destination TEXT,
                distance_km REAL,
                mode TEXT,
                cargo_weight_kg REAL,
                FOREIGN KEY (product_id) REFERENCES products (product_id)
            )
        """)
        
        # Packaging materials table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS packaging_materials (
                packaging_id TEXT PRIMARY KEY,
                product_id TEXT,
                material_id TEXT,
                weight_kg REAL,
                FOREIGN KEY (product_id) REFERENCES products (product_id),
                FOREIGN KEY (material_id) REFERENCES materials (material_id)
            )
        """)
        
        # Product use profile table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS product_use_profile (
                profile_id TEXT PRIMARY KEY,
                product_id TEXT,
                energy_consumption_kwh_per_year REAL,
                product_lifetime_years REAL,
                FOREIGN KEY (product_id) REFERENCES products (product_id)
            )
        """)
        
        # Carbon emissions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS carbon_emissions (
                emission_id TEXT PRIMARY KEY,
                timestamp TIMESTAMP,
                scope TEXT,
                category TEXT,
                emission_kg_co2 REAL,
                activity_description TEXT,
                activity_quantity REAL,
                activity_unit TEXT,
                source_id TEXT,
                calculation_method TEXT,
                confidence_level REAL,
                verification_status TEXT
            )
        """)
        
        # Energy consumption table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS energy_consumption (
                consumption_id TEXT PRIMARY KEY,
                timestamp TIMESTAMP,
                facility_id TEXT,
                process_id TEXT,
                energy_source TEXT,
                consumption_kwh REAL,
                emission_factor_kg_co2_per_kwh REAL,
                emission_kg_co2 REAL,
                renewable_percentage REAL
            )
        """)
        
        # Waste generation table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS waste_generation (
                waste_id TEXT PRIMARY KEY,
                timestamp TIMESTAMP,
                waste_type TEXT,
                quantity_kg REAL,
                material_composition TEXT,
                disposal_method TEXT,
                emission_kg_co2 REAL,
                cost_per_kg REAL
            )
        """)
        
        # Production records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS production_records (
                record_id TEXT PRIMARY KEY,
                product_id TEXT,
                production_date DATE,
                quantity_produced INTEGER,
                facility_id TEXT,
                FOREIGN KEY (product_id) REFERENCES products (product_id)
            )
        """)
        
        # Revenue records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS revenue_records (
                record_id TEXT PRIMARY KEY,
                revenue_date DATE,
                revenue_amount REAL,
                product_id TEXT,
                FOREIGN KEY (product_id) REFERENCES products (product_id)
            )
        """)
        
        # Product footprints table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS product_footprints (
                footprint_id TEXT PRIMARY KEY,
                product_id TEXT,
                calculation_date TIMESTAMP,
                total_emission_kg_co2 REAL,
                scope_breakdown TEXT,
                category_breakdown TEXT,
                lifecycle_stages TEXT,
                confidence_score REAL,
                improvement_opportunities TEXT,
                FOREIGN KEY (product_id) REFERENCES products (product_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def record_emission(self, emission: CarbonEmissionRecord) -> str:
        """Record a carbon emission"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO carbon_emissions 
            (emission_id, timestamp, scope, category, emission_kg_co2, activity_description,
             activity_quantity, activity_unit, source_id, calculation_method, 
             confidence_level, verification_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            emission.emission_id, emission.timestamp, emission.scope.value,
            emission.category.value, emission.emission_kg_co2, emission.activity_description,
            emission.activity_quantity, emission.activity_unit, emission.source_id,
            emission.calculation_method, emission.confidence_level, emission.verification_status
        ))
        
        conn.commit()
        conn.close()
        
        return emission.emission_id
    
    async def calculate_product_footprint(self, product_id: str) -> ProductCarbonFootprint:
        """Calculate and store product carbon footprint"""
        footprint = await self.calculator.calculate_product_footprint(product_id)
        
        # Store footprint in database
        await self._store_product_footprint(footprint)
        
        return footprint
    
    async def _store_product_footprint(self, footprint: ProductCarbonFootprint):
        """Store product footprint in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        footprint_id = f"footprint_{footprint.product_id}_{footprint.calculation_date.strftime('%Y%m%d_%H%M%S')}"
        
        cursor.execute("""
            INSERT INTO product_footprints 
            (footprint_id, product_id, calculation_date, total_emission_kg_co2,
             scope_breakdown, category_breakdown, lifecycle_stages, confidence_score,
             improvement_opportunities)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            footprint_id, footprint.product_id, footprint.calculation_date,
            footprint.total_emission_kg_co2,
            json.dumps({k.value: v for k, v in footprint.scope_breakdown.items()}),
            json.dumps({k.value: v for k, v in footprint.category_breakdown.items()}),
            json.dumps(footprint.lifecycle_stages),
            footprint.confidence_score,
            json.dumps(footprint.improvement_opportunities)
        ))
        
        conn.commit()
        conn.close()
    
    async def get_sustainability_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive sustainability dashboard"""
        # Current period metrics
        current_metrics = await self.analyzer.calculate_sustainability_metrics(30)
        
        # Previous period for comparison
        previous_metrics = await self.analyzer.calculate_sustainability_metrics(60)  # Days 31-60
        
        # Top emission sources
        top_sources = await self._get_top_emission_sources()
        
        # Recent footprints
        recent_footprints = await self._get_recent_product_footprints()
        
        # Improvement tracking
        improvement_tracking = await self._get_improvement_tracking()
        
        return {
            'dashboard_date': datetime.now(),
            'current_metrics': asdict(current_metrics),
            'period_comparison': {
                'emissions_change': ((current_metrics.total_emissions_kg_co2 - previous_metrics.total_emissions_kg_co2) / previous_metrics.total_emissions_kg_co2 * 100) if previous_metrics.total_emissions_kg_co2 > 0 else 0,
                'intensity_change': ((current_metrics.emissions_per_unit - previous_metrics.emissions_per_unit) / previous_metrics.emissions_per_unit * 100) if previous_metrics.emissions_per_unit > 0 else 0,
                'renewable_change': current_metrics.renewable_energy_percentage - previous_metrics.renewable_energy_percentage
            },
            'top_emission_sources': top_sources,
            'recent_product_footprints': recent_footprints,
            'improvement_tracking': improvement_tracking
        }
    
    async def _get_top_emission_sources(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top emission sources"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT category, SUM(emission_kg_co2) as total_emissions,
                   COUNT(*) as emission_count
            FROM carbon_emissions 
            WHERE timestamp >= date('now', '-30 days')
            GROUP BY category
            ORDER BY total_emissions DESC
            LIMIT ?
        """, (limit,))
        
        sources = cursor.fetchall()
        conn.close()
        
        return [
            {
                'category': row[0],
                'total_emissions_kg_co2': row[1],
                'emission_count': row[2]
            }
            for row in sources
        ]
    
    async def _get_recent_product_footprints(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent product footprints"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT pf.product_id, p.name, pf.total_emission_kg_co2, 
                   pf.confidence_score, pf.calculation_date
            FROM product_footprints pf
            JOIN products p ON pf.product_id = p.product_id
            ORDER BY pf.calculation_date DESC
            LIMIT ?
        """, (limit,))
        
        footprints = cursor.fetchall()
        conn.close()
        
        return [
            {
                'product_id': row[0],
                'product_name': row[1],
                'total_emission_kg_co2': row[2],
                'confidence_score': row[3],
                'calculation_date': row[4]
            }
            for row in footprints
        ]
    
    async def _get_improvement_tracking(self) -> Dict[str, Any]:
        """Get improvement opportunity tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get most common improvement opportunities
        cursor.execute("""
            SELECT improvement_opportunities
            FROM product_footprints 
            WHERE calculation_date >= date('now', '-90 days')
        """)
        
        all_opportunities = []
        for row in cursor.fetchall():
            if row[0]:
                opportunities = json.loads(row[0])
                all_opportunities.extend(opportunities)
        
        conn.close()
        
        # Count frequency
        opportunity_counts = {}
        for opp in all_opportunities:
            opportunity_counts[opp] = opportunity_counts.get(opp, 0) + 1
        
        # Sort by frequency
        top_opportunities = sorted(
            opportunity_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        return {
            'top_opportunities': [
                {'opportunity': opp, 'frequency': count}
                for opp, count in top_opportunities
            ],
            'total_products_analyzed': len(set(row[0] for row in cursor.fetchall())) if cursor.fetchall() else 0
        }
    
    async def add_sample_data(self):
        """Add sample data for testing"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Sample materials
        sample_materials = [
            ('MAT001', 'Aluminum Alloy 6061', 'metals', 8.24, 2700, 0.3, True, False, 'North America', 'SUPP001'),
            ('MAT002', 'Recycled PET Plastic', 'plastics', 1.8, 1380, 0.8, True, False, 'Europe', 'SUPP002'),
            ('MAT003', 'Steel AISI 1045', 'metals', 1.85, 7850, 0.1, True, False, 'Asia', 'SUPP003'),
            ('MAT004', 'Cardboard Packaging', 'packaging', 0.63, 700, 0.9, True, True, 'Global', 'SUPP004')
        ]
        
        for mat in sample_materials:
            cursor.execute("""
                INSERT OR REPLACE INTO materials VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, mat)
        
        # Sample products
        sample_products = [
            ('PROD001', 'Electronic Device A', 'electronics', 'per unit', 0.5, 0.0002),
            ('PROD002', 'Mechanical Assembly B', 'machinery', 'per unit', 2.3, 0.001),
            ('PROD003', 'Consumer Appliance C', 'appliances', 'per unit', 15.0, 0.05)
        ]
        
        for prod in sample_products:
            cursor.execute("""
                INSERT OR REPLACE INTO products VALUES (?, ?, ?, ?, ?, ?)
            """, prod)
        
        # Sample bill of materials
        sample_bom = [
            ('BOM001', 'PROD001', 'MAT001', 0.2, 'North America'),
            ('BOM002', 'PROD001', 'MAT002', 0.1, 'Europe'),
            ('BOM003', 'PROD002', 'MAT003', 1.8, 'Asia'),
            ('BOM004', 'PROD002', 'MAT001', 0.3, 'North America'),
            ('BOM005', 'PROD003', 'MAT003', 12.0, 'Asia'),
            ('BOM006', 'PROD003', 'MAT002', 2.0, 'Europe')
        ]
        
        for bom in sample_bom:
            cursor.execute("""
                INSERT OR REPLACE INTO bill_of_materials VALUES (?, ?, ?, ?, ?)
            """, bom)
        
        # Sample manufacturing processes
        sample_processes = [
            ('PROC001', 'PROD001', 'injection_molding', 0.1, 'kg', 0.5, None),
            ('PROC002', 'PROD001', 'assembly', 1.0, 'unit', 0.2, None),
            ('PROC003', 'PROD002', 'machining', 0.5, 'kg', 2.0, None),
            ('PROC004', 'PROD002', 'welding', 5.0, 'meter', 1.5, None),
            ('PROC005', 'PROD003', 'stamping', 12.0, 'kg', 8.0, None)
        ]
        
        for proc in sample_processes:
            cursor.execute("""
                INSERT OR REPLACE INTO manufacturing_processes VALUES (?, ?, ?, ?, ?, ?, ?)
            """, proc)
        
        # Sample transportation routes
        sample_transport = [
            ('TRANS001', 'PROD001', 'Factory A', 'Distribution Center', 500, 'truck', 100),
            ('TRANS002', 'PROD002', 'Supplier B', 'Factory A', 1200, 'rail', 500),
            ('TRANS003', 'PROD003', 'Factory C', 'Port', 200, 'truck', 1000)
        ]
        
        for trans in sample_transport:
            cursor.execute("""
                INSERT OR REPLACE INTO transportation_routes VALUES (?, ?, ?, ?, ?, ?, ?)
            """, trans)
        
        # Sample energy consumption
        base_date = datetime.now() - timedelta(days=30)
        for i in range(30):
            consumption_date = base_date + timedelta(days=i)
            
            # Grid electricity
            cursor.execute("""
                INSERT OR REPLACE INTO energy_consumption VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"ENERGY_GRID_{i:03d}", consumption_date, 'FAC001', 'manufacturing',
                'grid_electricity', np.random.normal(1000, 200), 0.42,
                np.random.normal(1000, 200) * 0.42, 15.0
            ))
            
            # Renewable energy
            cursor.execute("""
                INSERT OR REPLACE INTO energy_consumption VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"ENERGY_RENEW_{i:03d}", consumption_date, 'FAC001', 'manufacturing',
                'renewable', np.random.normal(200, 50), 0.02,
                np.random.normal(200, 50) * 0.02, 100.0
            ))
        
        # Sample waste generation
        for i in range(30):
            waste_date = base_date + timedelta(days=i)
            
            cursor.execute("""
                INSERT OR REPLACE INTO waste_generation VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"WASTE_{i:03d}", waste_date, 'recycling', 
                np.random.normal(50, 15), '{"steel": 0.6, "aluminum": 0.3, "plastic": 0.1}',
                'recycling_facility', np.random.normal(50, 15) * (-0.5), 0.05
            ))
        
        # Sample production records
        for i in range(30):
            prod_date = base_date + timedelta(days=i)
            
            for product_id in ['PROD001', 'PROD002', 'PROD003']:
                base_qty = {'PROD001': 100, 'PROD002': 50, 'PROD003': 20}[product_id]
                quantity = max(0, int(np.random.normal(base_qty, base_qty * 0.2)))
                
                cursor.execute("""
                    INSERT OR REPLACE INTO production_records VALUES (?, ?, ?, ?, ?)
                """, (
                    f"PROD_REC_{product_id}_{i:03d}", product_id, prod_date.date(),
                    quantity, 'FAC001'
                ))
        
        conn.commit()
        conn.close()


async def main():
    """Example usage of Carbon Footprint Tracker"""
    tracker = CarbonFootprintTracker()
    
    # Add sample data
    await tracker.add_sample_data()
    print("Added sample data")
    
    # Calculate product footprints
    for product_id in ['PROD001', 'PROD002', 'PROD003']:
        footprint = await tracker.calculate_product_footprint(product_id)
        
        print(f"\nCarbon Footprint - {footprint.product_name} ({product_id}):")
        print(f"Total Emissions: {footprint.total_emission_kg_co2:.2f} kg CO2")
        print(f"Confidence Score: {footprint.confidence_score:.2f}")
        
        print(f"\nScope Breakdown:")
        for scope, emissions in footprint.scope_breakdown.items():
            print(f"  {scope.value}: {emissions:.2f} kg CO2")
        
        print(f"\nCategory Breakdown:")
        for category, emissions in footprint.category_breakdown.items():
            if emissions > 0:
                print(f"  {category.value}: {emissions:.2f} kg CO2")
        
        print(f"\nImprovement Opportunities:")
        for opportunity in footprint.improvement_opportunities[:3]:
            print(f"  - {opportunity}")
    
    # Get sustainability dashboard
    dashboard = await tracker.get_sustainability_dashboard()
    
    print(f"\n" + "="*50)
    print(f"SUSTAINABILITY DASHBOARD")
    print(f"="*50)
    
    current = dashboard['current_metrics']
    print(f"\nCurrent Period (30 days):")
    print(f"Total Emissions: {current['total_emissions_kg_co2']:,.2f} kg CO2")
    print(f"Emissions per Unit: {current['emissions_per_unit']:.2f} kg CO2/unit")
    print(f"Renewable Energy: {current['renewable_energy_percentage']:.1f}%")
    print(f"Recycling Rate: {current['recycling_rate']:.1f}%")
    print(f"Carbon Intensity Trend: {current['carbon_intensity_trend']:.2f}%")
    print(f"Target Achievement: {current['target_achievement']:.1f}%")
    
    print(f"\nTop Emission Sources:")
    for source in dashboard['top_emission_sources'][:5]:
        print(f"  {source['category']}: {source['total_emissions_kg_co2']:,.1f} kg CO2")
    
    print(f"\nTop Improvement Opportunities:")
    for opp in dashboard['improvement_tracking']['top_opportunities'][:3]:
        print(f"  {opp['opportunity']} (frequency: {opp['frequency']})")


if __name__ == "__main__":
    asyncio.run(main())