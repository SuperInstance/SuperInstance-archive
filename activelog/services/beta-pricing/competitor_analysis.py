"""
Competitor Pricing Analysis System
Monitor and analyze competitor pricing to optimize positioning and strategy
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import sqlite3
import json
import uuid
import asyncio
import aiohttp
from dataclasses import dataclass
from enum import Enum
import statistics
import re

logger = logging.getLogger(__name__)

class CompetitorTier(str, Enum):
    DIRECT = "direct"          # Direct competitors with similar offerings
    INDIRECT = "indirect"      # Indirect competitors in adjacent markets
    SUBSTITUTE = "substitute"  # Substitute solutions

class PricingModel(str, Enum):
    SUBSCRIPTION = "subscription"
    FREEMIUM = "freemium"
    USAGE_BASED = "usage_based"
    ONE_TIME = "one_time"
    TIERED = "tiered"

@dataclass
class CompetitorProduct:
    competitor_name: str
    product_name: str
    pricing_model: PricingModel
    tiers: List[Dict[str, Any]]
    features: List[str]
    market_position: str
    last_updated: datetime

@dataclass
class MarketAnalysis:
    market_segment: str
    price_range: tuple
    median_price: Decimal
    feature_comparison: Dict[str, List[str]]
    positioning_opportunities: List[str]
    competitive_advantage: List[str]

class CompetitorAnalyzer:
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/beta-pricing/data/beta_pricing.db"
        self._initialize_tables()
        
        # Known competitors and their typical pricing patterns
        self.competitor_templates = {
            "salesforce": {
                "pricing_model": "tiered",
                "base_price_range": (25, 300),
                "typical_features": ["CRM", "Analytics", "Automation", "API", "Support"]
            },
            "hubspot": {
                "pricing_model": "freemium",
                "base_price_range": (0, 1200),
                "typical_features": ["Marketing", "Sales", "Service", "CRM", "Analytics"]
            },
            "microsoft": {
                "pricing_model": "subscription",
                "base_price_range": (5, 57),
                "typical_features": ["Office Suite", "Cloud Storage", "Collaboration", "Security"]
            }
        }
        
        self.monitoring_active = False
        self.update_frequency = timedelta(hours=24)  # Daily updates
    
    def _initialize_tables(self):
        """Initialize database tables for competitor analysis"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Competitor pricing table (already exists in main.py, ensuring completeness)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS competitor_pricing (
                id TEXT PRIMARY KEY,
                competitor_name TEXT NOT NULL,
                product_name TEXT NOT NULL,
                pricing_tier TEXT NOT NULL,
                price DECIMAL NOT NULL,
                features TEXT NOT NULL,
                pricing_model TEXT DEFAULT 'subscription',
                currency TEXT DEFAULT 'USD',
                billing_period TEXT DEFAULT 'monthly',
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT NOT NULL
            )
        ''')
        
        # Market analysis table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_analysis (
                id TEXT PRIMARY KEY,
                analysis_date DATE NOT NULL,
                market_segment TEXT NOT NULL,
                competitor_count INTEGER NOT NULL,
                price_min DECIMAL NOT NULL,
                price_max DECIMAL NOT NULL,
                price_median DECIMAL NOT NULL,
                our_position TEXT,
                competitive_gaps TEXT,
                opportunities TEXT,
                data TEXT NOT NULL
            )
        ''')
        
        # Pricing intelligence table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pricing_intelligence (
                id TEXT PRIMARY KEY,
                competitor_name TEXT NOT NULL,
                intelligence_type TEXT NOT NULL, -- price_change, new_tier, feature_update
                old_value TEXT,
                new_value TEXT NOT NULL,
                impact_score REAL DEFAULT 0,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def add_competitor_data(
        self,
        competitor_name: str,
        product_name: str,
        pricing_tiers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Add or update competitor pricing data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            added_tiers = []
            
            for tier_data in pricing_tiers:
                tier_id = f"COMP_{uuid.uuid4().hex[:8].upper()}"
                
                # Validate and normalize pricing data
                price = Decimal(str(tier_data["price"]))
                features = tier_data.get("features", [])
                tier_name = tier_data.get("tier_name", "Standard")
                pricing_model = tier_data.get("pricing_model", "subscription")
                
                competitor_data = {
                    "id": tier_id,
                    "competitor_name": competitor_name,
                    "product_name": product_name,
                    "tier_name": tier_name,
                    "price": float(price),
                    "features": features,
                    "pricing_model": pricing_model,
                    "currency": tier_data.get("currency", "USD"),
                    "billing_period": tier_data.get("billing_period", "monthly"),
                    "last_updated": datetime.now().isoformat()
                }
                
                # Check for existing data to detect changes
                cursor.execute('''
                    SELECT price, features FROM competitor_pricing 
                    WHERE competitor_name = ? AND product_name = ? AND pricing_tier = ?
                    ORDER BY last_updated DESC LIMIT 1
                ''', (competitor_name, product_name, tier_name))
                
                existing = cursor.fetchone()
                
                # Store the data
                cursor.execute('''
                    INSERT INTO competitor_pricing 
                    (id, competitor_name, product_name, pricing_tier, price, features,
                     pricing_model, currency, billing_period, data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    tier_id, competitor_name, product_name, tier_name,
                    float(price), json.dumps(features), pricing_model,
                    competitor_data["currency"], competitor_data["billing_period"],
                    json.dumps(competitor_data)
                ))
                
                # Track pricing intelligence if there are changes
                if existing:
                    old_price, old_features = existing
                    if abs(float(price) - old_price) > 0.01:  # Price change
                        await self._record_intelligence(
                            competitor_name, "price_change",
                            f"${old_price}", f"${float(price)}"
                        )
                
                added_tiers.append(competitor_data)
            
            conn.commit()
            conn.close()
            
            logger.info(f"Added {len(added_tiers)} pricing tiers for {competitor_name}")
            
            return {
                "competitor": competitor_name,
                "product": product_name,
                "tiers_added": len(added_tiers),
                "data": added_tiers
            }
            
        except Exception as e:
            logger.error(f"Error adding competitor data: {str(e)}")
            return {"error": str(e)}
    
    async def get_pricing_analysis(self, category: Optional[str] = None) -> Dict[str, Any]:
        """Get comprehensive competitor pricing analysis"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get recent competitor pricing data
            base_query = '''
                SELECT competitor_name, product_name, pricing_tier, price, features, pricing_model
                FROM competitor_pricing 
                WHERE last_updated >= date('now', '-30 days')
            '''
            
            if category:
                cursor.execute(base_query + ' AND product_name LIKE ?', (f'%{category}%',))
            else:
                cursor.execute(base_query)
            
            pricing_data = cursor.fetchall()
            
            if not pricing_data:
                conn.close()
                return {
                    "message": "No recent competitor data available",
                    "recommendation": "Add competitor pricing data to generate analysis"
                }
            
            # Organize data by competitor
            competitors = {}
            all_prices = []
            
            for comp_name, prod_name, tier, price, features_json, pricing_model in pricing_data:
                if comp_name not in competitors:
                    competitors[comp_name] = {
                        "products": {},
                        "price_range": [float('inf'), 0],
                        "avg_price": 0
                    }
                
                if prod_name not in competitors[comp_name]["products"]:
                    competitors[comp_name]["products"][prod_name] = []
                
                features = json.loads(features_json) if features_json else []
                
                tier_info = {
                    "tier": tier,
                    "price": price,
                    "features": features,
                    "pricing_model": pricing_model
                }
                
                competitors[comp_name]["products"][prod_name].append(tier_info)
                competitors[comp_name]["price_range"][0] = min(competitors[comp_name]["price_range"][0], price)
                competitors[comp_name]["price_range"][1] = max(competitors[comp_name]["price_range"][1], price)
                
                all_prices.append(price)
            
            # Calculate market statistics
            market_stats = self._calculate_market_stats(all_prices)
            
            # Generate competitive positioning
            positioning = await self._analyze_competitive_positioning(competitors)
            
            # Identify pricing opportunities
            opportunities = self._identify_opportunities(competitors, market_stats)
            
            # Get our current pricing for comparison
            our_pricing = await self._get_our_pricing_tiers()
            
            conn.close()
            
            return {
                "analysis_date": datetime.now().isoformat(),
                "market_overview": {
                    "total_competitors": len(competitors),
                    "total_products": sum(len(comp["products"]) for comp in competitors.values()),
                    "price_statistics": market_stats
                },
                "competitor_breakdown": self._format_competitor_breakdown(competitors),
                "competitive_positioning": positioning,
                "pricing_opportunities": opportunities,
                "our_position": our_pricing,
                "recommendations": self._generate_pricing_recommendations(competitors, market_stats, our_pricing)
            }
            
        except Exception as e:
            logger.error(f"Error getting pricing analysis: {str(e)}")
            return {"error": str(e)}
    
    def _calculate_market_stats(self, prices: List[float]) -> Dict[str, Any]:
        """Calculate market pricing statistics"""
        if not prices:
            return {"error": "No pricing data available"}
        
        return {
            "min_price": min(prices),
            "max_price": max(prices),
            "median_price": statistics.median(prices),
            "mean_price": statistics.mean(prices),
            "price_distribution": {
                "under_20": len([p for p in prices if p < 20]) / len(prices) * 100,
                "20_to_50": len([p for p in prices if 20 <= p < 50]) / len(prices) * 100,
                "50_to_100": len([p for p in prices if 50 <= p < 100]) / len(prices) * 100,
                "over_100": len([p for p in prices if p >= 100]) / len(prices) * 100
            },
            "quartiles": {
                "25th": statistics.quantiles(prices, n=4)[0] if len(prices) >= 4 else min(prices),
                "50th": statistics.median(prices),
                "75th": statistics.quantiles(prices, n=4)[2] if len(prices) >= 4 else max(prices)
            }
        }
    
    async def _analyze_competitive_positioning(self, competitors: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze competitive positioning in the market"""
        positioning = {
            "price_leaders": [],
            "premium_players": [],
            "value_players": [],
            "feature_leaders": []
        }
        
        all_prices = []
        for comp_name, comp_data in competitors.items():
            comp_prices = []
            total_features = 0
            
            for product, tiers in comp_data["products"].items():
                for tier in tiers:
                    comp_prices.append(tier["price"])
                    total_features += len(tier["features"])
            
            if comp_prices:
                avg_price = statistics.mean(comp_prices)
                all_prices.append(avg_price)
                
                comp_info = {
                    "name": comp_name,
                    "avg_price": round(avg_price, 2),
                    "price_range": comp_data["price_range"],
                    "avg_features": round(total_features / len(comp_prices), 1)
                }
                
                # Categorize by pricing strategy
                if avg_price < statistics.mean(all_prices) * 0.7:  # Significantly below market
                    positioning["value_players"].append(comp_info)
                elif avg_price > statistics.mean(all_prices) * 1.3:  # Significantly above market
                    positioning["premium_players"].append(comp_info)
                else:
                    positioning["price_leaders"].append(comp_info)
                
                # Feature leadership
                if comp_info["avg_features"] > 8:  # Threshold for feature richness
                    positioning["feature_leaders"].append(comp_info)
        
        return positioning
    
    def _identify_opportunities(self, competitors: Dict[str, Any], market_stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify pricing and positioning opportunities"""
        opportunities = []
        
        # Price gap analysis
        median_price = market_stats["median_price"]
        quartiles = market_stats["quartiles"]
        
        # Gap in pricing tiers
        if quartiles["75th"] - quartiles["25th"] > 50:  # Large price gap
            opportunities.append({
                "type": "pricing_gap",
                "description": f"Large gap between ${quartiles['25th']:.2f} and ${quartiles['75th']:.2f}",
                "recommendation": "Consider positioning in the middle tier",
                "potential_price_point": round((quartiles["25th"] + quartiles["75th"]) / 2, 2)
            })
        
        # Feature-price mismatch opportunities
        feature_price_ratios = []
        for comp_name, comp_data in competitors.items():
            for product, tiers in comp_data["products"].items():
                for tier in tiers:
                    if tier["price"] > 0 and len(tier["features"]) > 0:
                        ratio = tier["price"] / len(tier["features"])
                        feature_price_ratios.append(ratio)
        
        if feature_price_ratios:
            avg_ratio = statistics.mean(feature_price_ratios)
            opportunities.append({
                "type": "feature_value",
                "description": f"Average price per feature: ${avg_ratio:.2f}",
                "recommendation": "Optimize feature bundling to improve value perception"
            })
        
        # Market positioning opportunities
        premium_count = len([c for c in competitors.values() if c["price_range"][1] > median_price * 2])
        if premium_count < len(competitors) * 0.3:  # Less than 30% are premium
            opportunities.append({
                "type": "premium_opportunity",
                "description": "Limited premium options in market",
                "recommendation": "Consider premium positioning with advanced features"
            })
        
        return opportunities
    
    async def _get_our_pricing_tiers(self) -> Dict[str, Any]:
        """Get our current pricing tiers for comparison"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT tier, base_price, beta_price, features_included
                FROM pricing_tiers 
                ORDER BY base_price
            ''')
            
            our_tiers = cursor.fetchall()
            conn.close()
            
            if not our_tiers:
                return {"message": "No internal pricing data available"}
            
            tiers = []
            for tier, base_price, beta_price, features_json in our_tiers:
                features = json.loads(features_json) if features_json else []
                tiers.append({
                    "tier": tier,
                    "base_price": base_price,
                    "beta_price": beta_price,
                    "features": features,
                    "feature_count": len(features)
                })
            
            return {
                "tiers": tiers,
                "price_range": [min(t["base_price"] for t in tiers), max(t["base_price"] for t in tiers)],
                "avg_features": statistics.mean([t["feature_count"] for t in tiers])
            }
            
        except Exception as e:
            logger.error(f"Error getting our pricing: {str(e)}")
            return {"error": str(e)}
    
    def _format_competitor_breakdown(self, competitors: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Format competitor data for response"""
        breakdown = []
        
        for comp_name, comp_data in competitors.items():
            comp_summary = {
                "competitor": comp_name,
                "price_range": comp_data["price_range"],
                "products": []
            }
            
            for product, tiers in comp_data["products"].items():
                product_info = {
                    "product_name": product,
                    "tier_count": len(tiers),
                    "price_range": [min(t["price"] for t in tiers), max(t["price"] for t in tiers)],
                    "pricing_models": list(set(t["pricing_model"] for t in tiers)),
                    "total_features": sum(len(t["features"]) for t in tiers)
                }
                comp_summary["products"].append(product_info)
            
            breakdown.append(comp_summary)
        
        return breakdown
    
    def _generate_pricing_recommendations(
        self, 
        competitors: Dict[str, Any], 
        market_stats: Dict[str, Any],
        our_pricing: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate strategic pricing recommendations"""
        recommendations = []
        
        if "error" in our_pricing or "message" in our_pricing:
            recommendations.append({
                "priority": "high",
                "category": "data_collection",
                "recommendation": "Set up internal pricing tiers for competitive comparison",
                "rationale": "Cannot provide strategic recommendations without baseline pricing"
            })
            return recommendations
        
        median_market_price = market_stats["median_price"]
        our_price_range = our_pricing["price_range"]
        our_avg_price = statistics.mean(our_price_range)
        
        # Price positioning recommendations
        if our_avg_price < median_market_price * 0.8:
            recommendations.append({
                "priority": "medium",
                "category": "pricing_strategy",
                "recommendation": "Consider price increase to align with market median",
                "rationale": f"Current avg price ${our_avg_price:.2f} is below market median ${median_market_price:.2f}",
                "suggested_action": f"Test pricing at ${median_market_price * 0.9:.2f}"
            })
        elif our_avg_price > median_market_price * 1.5:
            recommendations.append({
                "priority": "high",
                "category": "pricing_strategy", 
                "recommendation": "Justify premium pricing with unique value proposition",
                "rationale": f"Current pricing ${our_avg_price:.2f} is significantly above market",
                "suggested_action": "Emphasize premium features and ROI"
            })
        
        # Feature competitiveness
        if "avg_features" in our_pricing and our_pricing["avg_features"] < 5:
            recommendations.append({
                "priority": "medium",
                "category": "product_strategy",
                "recommendation": "Expand feature set to match competitor offerings",
                "rationale": f"Average {our_pricing['avg_features']} features may be below competitive standard"
            })
        
        # Market gap opportunities
        quartiles = market_stats["quartiles"]
        if abs(quartiles["50th"] - quartiles["25th"]) > 20:  # Significant gap in lower tier
            recommendations.append({
                "priority": "low",
                "category": "market_opportunity",
                "recommendation": "Consider entry-level tier to capture price-sensitive segment",
                "rationale": f"Gap between ${quartiles['25th']:.2f} and ${quartiles['50th']:.2f} suggests opportunity"
            })
        
        return recommendations
    
    async def _record_intelligence(
        self, 
        competitor: str, 
        intelligence_type: str,
        old_value: str, 
        new_value: str
    ):
        """Record competitive intelligence"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            intelligence_id = f"INTEL_{uuid.uuid4().hex[:8].upper()}"
            
            # Calculate impact score (simplified)
            impact_score = 0.5  # Default medium impact
            if intelligence_type == "price_change":
                try:
                    old_price = float(old_value.replace('$', ''))
                    new_price = float(new_value.replace('$', ''))
                    change_percent = abs((new_price - old_price) / old_price)
                    impact_score = min(1.0, change_percent * 2)  # Scale impact
                except:
                    pass
            
            intelligence_data = {
                "id": intelligence_id,
                "competitor": competitor,
                "type": intelligence_type,
                "old_value": old_value,
                "new_value": new_value,
                "impact_score": impact_score,
                "detected_at": datetime.now().isoformat()
            }
            
            cursor.execute('''
                INSERT INTO pricing_intelligence 
                (id, competitor_name, intelligence_type, old_value, new_value, impact_score, data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                intelligence_id, competitor, intelligence_type,
                old_value, new_value, impact_score,
                json.dumps(intelligence_data)
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Recorded intelligence: {competitor} {intelligence_type}")
            
        except Exception as e:
            logger.error(f"Error recording intelligence: {str(e)}")
    
    async def get_market_position(self) -> Dict[str, Any]:
        """Get our market position relative to competitors"""
        try:
            analysis = await self.get_pricing_analysis()
            
            if "error" in analysis:
                return analysis
            
            our_pricing = analysis.get("our_position", {})
            market_stats = analysis.get("market_overview", {}).get("price_statistics", {})
            
            if "error" in our_pricing or not market_stats:
                return {
                    "position": "unknown",
                    "message": "Insufficient data for market positioning analysis"
                }
            
            our_avg_price = statistics.mean(our_pricing["price_range"]) if our_pricing.get("price_range") else 0
            market_median = market_stats.get("median_price", 0)
            
            # Determine position
            if our_avg_price > market_median * 1.3:
                position = "premium"
            elif our_avg_price < market_median * 0.7:
                position = "value"
            else:
                position = "competitive"
            
            return {
                "position": position,
                "our_avg_price": round(our_avg_price, 2),
                "market_median": round(market_median, 2),
                "price_percentile": self._calculate_percentile(our_avg_price, market_stats),
                "competitive_gap": round(our_avg_price - market_median, 2),
                "analysis_date": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting market position: {str(e)}")
            return {"error": str(e)}
    
    def _calculate_percentile(self, our_price: float, market_stats: Dict[str, Any]) -> int:
        """Calculate what percentile our pricing is in"""
        quartiles = market_stats.get("quartiles", {})
        
        if our_price <= quartiles.get("25th", 0):
            return 25
        elif our_price <= quartiles.get("50th", 0):
            return 50
        elif our_price <= quartiles.get("75th", 0):
            return 75
        else:
            return 95
    
    async def start_competitor_monitoring(self):
        """Start background competitor monitoring"""
        self.monitoring_active = True
        logger.info("Starting competitor pricing monitoring...")
        
        while self.monitoring_active:
            try:
                # Check for pricing updates (simplified version)
                await self._check_competitor_updates()
                
                # Wait for next update cycle
                await asyncio.sleep(self.update_frequency.total_seconds())
                
            except Exception as e:
                logger.error(f"Error in competitor monitoring: {str(e)}")
                await asyncio.sleep(3600)  # Wait 1 hour on error
    
    async def _check_competitor_updates(self):
        """Check for competitor pricing updates (placeholder for web scraping)"""
        # This would typically involve web scraping or API calls
        # For now, it's a placeholder that could be extended with actual monitoring
        logger.info("Checking competitor updates...")
        
        # In a real implementation, you would:
        # 1. Scrape competitor websites
        # 2. Call competitor APIs if available
        # 3. Parse pricing information
        # 4. Compare with stored data
        # 5. Record any changes
        
        pass
    
    async def stop_monitoring(self):
        """Stop competitor monitoring"""
        self.monitoring_active = False
        logger.info("Stopped competitor monitoring")

# Global instance
competitor_analyzer = CompetitorAnalyzer()