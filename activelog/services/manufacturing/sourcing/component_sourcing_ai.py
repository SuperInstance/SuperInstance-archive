"""
ActiveLog Manufacturing Suite - Component Sourcing AI

AI-powered component sourcing with price optimization, supplier discovery,
and intelligent purchasing recommendations.
"""

import asyncio
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
import aiohttp
import hashlib
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import joblib


class SupplierTier(Enum):
    TIER_1 = "tier_1"  # Primary suppliers
    TIER_2 = "tier_2"  # Secondary suppliers
    TIER_3 = "tier_3"  # Tertiary suppliers


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Component:
    component_id: str
    name: str
    category: str
    specifications: Dict[str, Any]
    quantity_required: int
    target_price: Optional[float] = None
    delivery_deadline: Optional[datetime] = None
    quality_requirements: Optional[Dict[str, Any]] = None


@dataclass
class Supplier:
    supplier_id: str
    name: str
    location: str
    tier: SupplierTier
    reputation_score: float
    capabilities: List[str]
    certifications: List[str]
    lead_time_days: int
    minimum_order_quantity: int
    payment_terms: str
    contact_info: Dict[str, str]


@dataclass
class PriceQuote:
    quote_id: str
    supplier_id: str
    component_id: str
    unit_price: float
    quantity: int
    total_price: float
    validity_period: datetime
    delivery_time: int
    terms_conditions: str
    confidence_score: float


@dataclass
class SourcingRecommendation:
    component_id: str
    recommended_supplier: str
    reasoning: str
    cost_savings: float
    risk_assessment: RiskLevel
    alternatives: List[Dict[str, Any]]
    negotiation_points: List[str]


class PriceIntelligenceEngine:
    """AI engine for price prediction and market analysis"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.model = None
        self.scaler = StandardScaler()
        self.feature_columns = [
            'quantity', 'lead_time', 'supplier_tier_encoded', 
            'market_volatility', 'seasonal_factor', 'demand_index'
        ]
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize or load the price prediction model"""
        try:
            self.model = joblib.load(f"{self.db_path}_price_model.pkl")
            self.scaler = joblib.load(f"{self.db_path}_scaler.pkl")
        except FileNotFoundError:
            self.model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
    
    async def predict_price(self, component: Component, supplier: Supplier, 
                          market_conditions: Dict[str, float]) -> float:
        """Predict component price based on various factors"""
        if self.model is None:
            return 0.0
        
        # Encode supplier tier
        tier_encoding = {
            SupplierTier.TIER_1: 1.0,
            SupplierTier.TIER_2: 0.5,
            SupplierTier.TIER_3: 0.0
        }
        
        features = np.array([[
            component.quantity_required,
            supplier.lead_time_days,
            tier_encoding[supplier.tier],
            market_conditions.get('volatility', 0.1),
            market_conditions.get('seasonal_factor', 1.0),
            market_conditions.get('demand_index', 1.0)
        ]])
        
        if hasattr(self.scaler, 'mean_'):
            features = self.scaler.transform(features)
        
        try:
            predicted_price = self.model.predict(features)[0]
            return max(0.0, predicted_price)
        except:
            return 0.0
    
    async def analyze_market_trends(self, component_category: str) -> Dict[str, float]:
        """Analyze market trends for component category"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get historical price data
        cursor.execute("""
            SELECT price, timestamp FROM price_history 
            WHERE category = ? AND timestamp > date('now', '-90 days')
            ORDER BY timestamp
        """, (component_category,))
        
        price_data = cursor.fetchall()
        conn.close()
        
        if not price_data:
            return {
                'volatility': 0.1,
                'trend': 0.0,
                'seasonal_factor': 1.0,
                'demand_index': 1.0
            }
        
        prices = [float(row[0]) for row in price_data]
        volatility = np.std(prices) / np.mean(prices) if prices else 0.1
        trend = (prices[-1] - prices[0]) / prices[0] if len(prices) > 1 else 0.0
        
        return {
            'volatility': volatility,
            'trend': trend,
            'seasonal_factor': self._calculate_seasonal_factor(),
            'demand_index': self._calculate_demand_index(component_category)
        }
    
    def _calculate_seasonal_factor(self) -> float:
        """Calculate seasonal pricing factor"""
        month = datetime.now().month
        # Higher demand in Q4 and Q1
        if month in [10, 11, 12, 1, 2]:
            return 1.1
        elif month in [6, 7, 8]:
            return 0.9
        return 1.0
    
    def _calculate_demand_index(self, category: str) -> float:
        """Calculate demand index for category"""
        # Simplified demand calculation
        high_demand_categories = ['semiconductors', 'batteries', 'displays']
        if category.lower() in high_demand_categories:
            return 1.2
        return 1.0


class SupplierDiscoveryEngine:
    """AI engine for discovering and evaluating suppliers"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.api_keys = {}
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize supplier database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS suppliers (
                supplier_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                location TEXT,
                tier TEXT,
                reputation_score REAL,
                capabilities TEXT,
                certifications TEXT,
                lead_time_days INTEGER,
                minimum_order_quantity INTEGER,
                payment_terms TEXT,
                contact_info TEXT,
                last_updated TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS supplier_performance (
                supplier_id TEXT,
                component_category TEXT,
                delivery_performance REAL,
                quality_score REAL,
                price_competitiveness REAL,
                communication_score REAL,
                timestamp TIMESTAMP,
                FOREIGN KEY (supplier_id) REFERENCES suppliers (supplier_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def discover_suppliers(self, component: Component) -> List[Supplier]:
        """Discover suppliers for a specific component"""
        suppliers = []
        
        # Search local database
        local_suppliers = await self._search_local_suppliers(component)
        suppliers.extend(local_suppliers)
        
        # Search external supplier databases
        external_suppliers = await self._search_external_suppliers(component)
        suppliers.extend(external_suppliers)
        
        # Score and rank suppliers
        scored_suppliers = await self._score_suppliers(suppliers, component)
        
        return sorted(scored_suppliers, key=lambda s: s.reputation_score, reverse=True)
    
    async def _search_local_suppliers(self, component: Component) -> List[Supplier]:
        """Search local supplier database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM suppliers 
            WHERE capabilities LIKE ? OR capabilities LIKE ?
            ORDER BY reputation_score DESC
        """, (f"%{component.category}%", f"%{component.name}%"))
        
        rows = cursor.fetchall()
        conn.close()
        
        suppliers = []
        for row in rows:
            supplier = Supplier(
                supplier_id=row[0],
                name=row[1],
                location=row[2],
                tier=SupplierTier(row[3]),
                reputation_score=row[4],
                capabilities=json.loads(row[5]) if row[5] else [],
                certifications=json.loads(row[6]) if row[6] else [],
                lead_time_days=row[7],
                minimum_order_quantity=row[8],
                payment_terms=row[9],
                contact_info=json.loads(row[10]) if row[10] else {}
            )
            suppliers.append(supplier)
        
        return suppliers
    
    async def _search_external_suppliers(self, component: Component) -> List[Supplier]:
        """Search external supplier databases and marketplaces"""
        suppliers = []
        
        # Placeholder for external API calls
        # In production, integrate with supplier databases like:
        # - Alibaba API
        # - ThomasNet API
        # - Global Sources API
        # - Industry-specific directories
        
        return suppliers
    
    async def _score_suppliers(self, suppliers: List[Supplier], 
                             component: Component) -> List[Supplier]:
        """Score suppliers based on various factors"""
        for supplier in suppliers:
            # Get performance history
            performance = await self._get_supplier_performance(
                supplier.supplier_id, component.category
            )
            
            # Calculate composite score
            score = self._calculate_supplier_score(supplier, performance, component)
            supplier.reputation_score = score
        
        return suppliers
    
    async def _get_supplier_performance(self, supplier_id: str, 
                                      category: str) -> Dict[str, float]:
        """Get supplier performance metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                AVG(delivery_performance),
                AVG(quality_score),
                AVG(price_competitiveness),
                AVG(communication_score)
            FROM supplier_performance 
            WHERE supplier_id = ? AND component_category = ?
            AND timestamp > date('now', '-365 days')
        """, (supplier_id, category))
        
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0] is not None:
            return {
                'delivery_performance': row[0],
                'quality_score': row[1],
                'price_competitiveness': row[2],
                'communication_score': row[3]
            }
        
        return {
            'delivery_performance': 0.7,
            'quality_score': 0.7,
            'price_competitiveness': 0.7,
            'communication_score': 0.7
        }
    
    def _calculate_supplier_score(self, supplier: Supplier, 
                                performance: Dict[str, float],
                                component: Component) -> float:
        """Calculate composite supplier score"""
        weights = {
            'delivery_performance': 0.3,
            'quality_score': 0.25,
            'price_competitiveness': 0.2,
            'communication_score': 0.1,
            'tier_bonus': 0.1,
            'certification_bonus': 0.05
        }
        
        score = 0.0
        
        # Performance metrics
        for metric, weight in weights.items():
            if metric in performance:
                score += performance[metric] * weight
        
        # Tier bonus
        tier_scores = {
            SupplierTier.TIER_1: 1.0,
            SupplierTier.TIER_2: 0.8,
            SupplierTier.TIER_3: 0.6
        }
        score += tier_scores[supplier.tier] * weights['tier_bonus']
        
        # Certification bonus
        relevant_certs = ['ISO9001', 'ISO14001', 'IATF16949']
        cert_score = len(set(supplier.certifications) & set(relevant_certs)) / len(relevant_certs)
        score += cert_score * weights['certification_bonus']
        
        return min(1.0, score)


class ComponentSourcingAI:
    """Main AI system for component sourcing and optimization"""
    
    def __init__(self, db_path: str = "sourcing.db"):
        self.db_path = db_path
        self.price_engine = PriceIntelligenceEngine(db_path)
        self.supplier_engine = SupplierDiscoveryEngine(db_path)
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize main database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sourcing_requests (
                request_id TEXT PRIMARY KEY,
                component_data TEXT,
                status TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                component_id TEXT,
                category TEXT,
                supplier_id TEXT,
                price REAL,
                quantity INTEGER,
                timestamp TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_intelligence (
                category TEXT PRIMARY KEY,
                volatility REAL,
                trend REAL,
                demand_index REAL,
                last_updated TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def optimize_bom(self, bom_data: List[Component]) -> List[SourcingRecommendation]:
        """Optimize bill of materials sourcing"""
        recommendations = []
        
        for component in bom_data:
            # Find suppliers
            suppliers = await self.supplier_engine.discover_suppliers(component)
            
            if not suppliers:
                continue
            
            # Get market conditions
            market_conditions = await self.price_engine.analyze_market_trends(
                component.category
            )
            
            # Generate quotes
            quotes = await self._generate_quotes(component, suppliers, market_conditions)
            
            # Create recommendation
            recommendation = await self._create_recommendation(
                component, suppliers, quotes, market_conditions
            )
            
            recommendations.append(recommendation)
        
        return recommendations
    
    async def _generate_quotes(self, component: Component, suppliers: List[Supplier],
                             market_conditions: Dict[str, float]) -> List[PriceQuote]:
        """Generate price quotes from suppliers"""
        quotes = []
        
        for supplier in suppliers[:5]:  # Top 5 suppliers
            predicted_price = await self.price_engine.predict_price(
                component, supplier, market_conditions
            )
            
            quote = PriceQuote(
                quote_id=f"quote_{component.component_id}_{supplier.supplier_id}",
                supplier_id=supplier.supplier_id,
                component_id=component.component_id,
                unit_price=predicted_price,
                quantity=component.quantity_required,
                total_price=predicted_price * component.quantity_required,
                validity_period=datetime.now() + timedelta(days=30),
                delivery_time=supplier.lead_time_days,
                terms_conditions="Standard terms",
                confidence_score=0.8
            )
            
            quotes.append(quote)
        
        return sorted(quotes, key=lambda q: q.total_price)
    
    async def _create_recommendation(self, component: Component, suppliers: List[Supplier],
                                   quotes: List[PriceQuote], 
                                   market_conditions: Dict[str, float]) -> SourcingRecommendation:
        """Create sourcing recommendation"""
        if not quotes:
            return SourcingRecommendation(
                component_id=component.component_id,
                recommended_supplier="None found",
                reasoning="No suppliers available",
                cost_savings=0.0,
                risk_assessment=RiskLevel.HIGH,
                alternatives=[],
                negotiation_points=[]
            )
        
        best_quote = quotes[0]
        best_supplier = next(s for s in suppliers if s.supplier_id == best_quote.supplier_id)
        
        # Calculate cost savings vs target price
        cost_savings = 0.0
        if component.target_price:
            cost_savings = (component.target_price - best_quote.unit_price) * component.quantity_required
        
        # Assess risk
        risk = self._assess_sourcing_risk(best_supplier, market_conditions)
        
        # Generate alternatives
        alternatives = []
        for quote in quotes[1:4]:  # Next 3 best options
            alt_supplier = next(s for s in suppliers if s.supplier_id == quote.supplier_id)
            alternatives.append({
                'supplier_name': alt_supplier.name,
                'unit_price': quote.unit_price,
                'total_price': quote.total_price,
                'lead_time': quote.delivery_time,
                'reputation_score': alt_supplier.reputation_score
            })
        
        # Generate negotiation points
        negotiation_points = self._generate_negotiation_points(
            component, best_supplier, best_quote, market_conditions
        )
        
        reasoning = f"Recommended {best_supplier.name} based on optimal balance of price (${best_quote.unit_price:.2f}), quality (score: {best_supplier.reputation_score:.2f}), and delivery time ({best_quote.delivery_time} days)"
        
        return SourcingRecommendation(
            component_id=component.component_id,
            recommended_supplier=best_supplier.name,
            reasoning=reasoning,
            cost_savings=cost_savings,
            risk_assessment=risk,
            alternatives=alternatives,
            negotiation_points=negotiation_points
        )
    
    def _assess_sourcing_risk(self, supplier: Supplier, 
                            market_conditions: Dict[str, float]) -> RiskLevel:
        """Assess sourcing risk for supplier"""
        risk_score = 0.0
        
        # Supplier reputation risk
        if supplier.reputation_score < 0.5:
            risk_score += 0.3
        elif supplier.reputation_score < 0.7:
            risk_score += 0.1
        
        # Market volatility risk
        if market_conditions['volatility'] > 0.3:
            risk_score += 0.2
        elif market_conditions['volatility'] > 0.15:
            risk_score += 0.1
        
        # Geographic risk (simplified)
        high_risk_locations = ['region_a', 'region_b']
        if any(region in supplier.location.lower() for region in high_risk_locations):
            risk_score += 0.2
        
        # Lead time risk
        if supplier.lead_time_days > 60:
            risk_score += 0.2
        elif supplier.lead_time_days > 30:
            risk_score += 0.1
        
        if risk_score >= 0.6:
            return RiskLevel.CRITICAL
        elif risk_score >= 0.4:
            return RiskLevel.HIGH
        elif risk_score >= 0.2:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _generate_negotiation_points(self, component: Component, supplier: Supplier,
                                   quote: PriceQuote, 
                                   market_conditions: Dict[str, float]) -> List[str]:
        """Generate negotiation talking points"""
        points = []
        
        if component.quantity_required > supplier.minimum_order_quantity * 2:
            points.append("Large volume order - request volume discount")
        
        if market_conditions['trend'] < -0.05:
            points.append("Market prices declining - leverage downward trend")
        
        if supplier.lead_time_days > 45:
            points.append("Long lead time - negotiate expedited delivery options")
        
        if supplier.reputation_score < 0.8:
            points.append("Request performance guarantees and SLA terms")
        
        points.append("Negotiate payment terms for improved cash flow")
        points.append("Discuss long-term partnership for price stability")
        
        return points
    
    async def track_price_changes(self, component_id: str, supplier_id: str, 
                                new_price: float, quantity: int):
        """Track price changes for market intelligence"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO price_history 
            (component_id, supplier_id, price, quantity, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (component_id, supplier_id, new_price, quantity, datetime.now()))
        
        conn.commit()
        conn.close()
    
    async def get_sourcing_insights(self, category: str) -> Dict[str, Any]:
        """Get market insights for component category"""
        market_conditions = await self.price_engine.analyze_market_trends(category)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get recent price statistics
        cursor.execute("""
            SELECT 
                AVG(price) as avg_price,
                MIN(price) as min_price,
                MAX(price) as max_price,
                COUNT(*) as quote_count
            FROM price_history 
            WHERE category = ? AND timestamp > date('now', '-30 days')
        """, (category,))
        
        price_stats = cursor.fetchone()
        conn.close()
        
        return {
            'category': category,
            'market_conditions': market_conditions,
            'price_statistics': {
                'average_price': price_stats[0] if price_stats[0] else 0.0,
                'minimum_price': price_stats[1] if price_stats[1] else 0.0,
                'maximum_price': price_stats[2] if price_stats[2] else 0.0,
                'quote_count': price_stats[3] if price_stats[3] else 0
            },
            'insights': self._generate_market_insights(market_conditions)
        }
    
    def _generate_market_insights(self, market_conditions: Dict[str, float]) -> List[str]:
        """Generate actionable market insights"""
        insights = []
        
        if market_conditions['trend'] > 0.1:
            insights.append("Prices trending upward - consider accelerating purchases")
        elif market_conditions['trend'] < -0.1:
            insights.append("Prices trending downward - consider delaying non-urgent purchases")
        
        if market_conditions['volatility'] > 0.2:
            insights.append("High market volatility - implement hedging strategies")
        
        if market_conditions['demand_index'] > 1.1:
            insights.append("High demand period - expect longer lead times")
        
        if market_conditions['seasonal_factor'] > 1.05:
            insights.append("Seasonal price premium active - evaluate timing")
        
        return insights


async def main():
    """Example usage of Component Sourcing AI"""
    sourcing_ai = ComponentSourcingAI()
    
    # Example components for BOM optimization
    components = [
        Component(
            component_id="MCU001",
            name="ARM Cortex-M4 Microcontroller",
            category="semiconductors",
            specifications={"architecture": "ARM", "frequency": "168MHz"},
            quantity_required=1000,
            target_price=5.50,
            delivery_deadline=datetime.now() + timedelta(days=45)
        ),
        Component(
            component_id="CAP001", 
            name="Ceramic Capacitor 100nF",
            category="passive_components",
            specifications={"capacitance": "100nF", "voltage": "50V"},
            quantity_required=5000,
            target_price=0.05
        )
    ]
    
    # Optimize BOM
    recommendations = await sourcing_ai.optimize_bom(components)
    
    for rec in recommendations:
        print(f"\nComponent: {rec.component_id}")
        print(f"Recommended Supplier: {rec.recommended_supplier}")
        print(f"Reasoning: {rec.reasoning}")
        print(f"Cost Savings: ${rec.cost_savings:.2f}")
        print(f"Risk Level: {rec.risk_assessment.value}")
        print(f"Negotiation Points: {', '.join(rec.negotiation_points)}")
    
    # Get market insights
    insights = await sourcing_ai.get_sourcing_insights("semiconductors")
    print(f"\nMarket Insights for Semiconductors:")
    print(f"Volatility: {insights['market_conditions']['volatility']:.3f}")
    print(f"Trend: {insights['market_conditions']['trend']:.3f}")
    for insight in insights['insights']:
        print(f"- {insight}")


if __name__ == "__main__":
    asyncio.run(main())