"""
Frontend Competition Analytics System
Comprehensive competitive intelligence and market analysis for frontend assets
"""

from typing import Dict, List, Optional, Any, Union, Set
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from enum import Enum
import uuid
import asyncio
import logging
import json
import sqlite3
import numpy as np
import aiohttp
from statistics import mean, median, stdev
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)

class CompetitorTier(str, Enum):
    DIRECT = "direct"           # Direct feature/market competitors
    INDIRECT = "indirect"       # Similar domain/audience
    SUBSTITUTE = "substitute"   # Alternative solutions
    EMERGING = "emerging"       # New/potential competitors

class AnalysisType(str, Enum):
    TECHNICAL = "technical"     # Technical comparison
    MARKET = "market"          # Market position analysis
    FEATURE = "feature"        # Feature comparison
    PERFORMANCE = "performance" # Performance benchmarking
    SEO = "seo"               # SEO competitive analysis
    SOCIAL = "social"         # Social media presence
    PRICING = "pricing"       # Pricing analysis
    FUNDING = "funding"       # Investment/funding analysis

class CompetitorProfile(BaseModel):
    id: str
    name: str
    url: str
    description: str = ""
    
    # Classification
    tier: CompetitorTier
    category: str
    tags: List[str] = []
    
    # Technical details
    framework: Optional[str] = None
    tech_stack: List[str] = []
    hosting_provider: Optional[str] = None
    cdn_provider: Optional[str] = None
    
    # Market data
    estimated_users: int = 0
    estimated_revenue: float = 0.0
    pricing_model: str = "unknown"
    target_market: List[str] = []
    
    # Performance metrics
    performance_score: float = 0.0
    seo_score: float = 0.0
    social_presence_score: float = 0.0
    
    # Business intelligence
    funding_stage: str = "unknown"
    employee_count: int = 0
    founded_date: Optional[datetime] = None
    headquarters: str = ""
    
    # Tracking
    discovery_date: datetime
    last_analyzed: datetime
    analysis_frequency_hours: int = 168  # Weekly by default
    
    # Status
    active: bool = True
    confidence_score: float = 0.0  # 0-1, how confident we are in the data

class CompetitiveFeature(BaseModel):
    id: str
    name: str
    category: str
    description: str = ""
    
    # Implementation details
    our_implementation: Optional[str] = None
    our_quality_score: float = 0.0
    
    # Competitor implementations
    competitor_implementations: Dict[str, Dict[str, Any]] = {}  # competitor_id -> implementation details
    
    # Analysis
    feature_importance: float = 1.0  # 1-5 scale
    differentiation_opportunity: float = 0.0  # 0-1 scale
    implementation_difficulty: str = "medium"  # low, medium, high
    
    created_at: datetime
    updated_at: datetime

class MarketAnalysis(BaseModel):
    id: str
    frontend_id: str
    analysis_type: AnalysisType
    
    # Analysis scope
    competitors_analyzed: List[str] = []
    analysis_date: datetime
    data_collection_period: int = 30  # days
    
    # Results
    market_position: Dict[str, Any] = {}
    competitive_gaps: List[Dict[str, Any]] = []
    opportunities: List[Dict[str, Any]] = []
    threats: List[Dict[str, Any]] = []
    
    # Metrics comparison
    our_metrics: Dict[str, float] = {}
    competitor_metrics: Dict[str, Dict[str, float]] = {}
    market_averages: Dict[str, float] = {}
    
    # Insights
    key_insights: List[str] = []
    recommendations: List[Dict[str, Any]] = []
    confidence_level: float = 0.8
    
    # Metadata
    analyst_notes: str = ""
    data_sources: List[str] = []

class TrendAnalysis(BaseModel):
    id: str
    trend_name: str
    category: str  # technology, market, user_behavior, etc.
    
    # Trend details
    description: str
    current_adoption: float = 0.0  # 0-1 scale
    growth_rate: float = 0.0  # monthly growth rate
    
    # Impact assessment
    relevance_to_us: float = 0.0  # 0-1 scale
    potential_impact: str = "medium"  # low, medium, high
    time_to_mainstream: int = 12  # months
    
    # Competitor adoption
    competitors_adopting: List[str] = []
    adoption_timeline: Dict[str, datetime] = {}
    
    # Strategic implications
    strategic_response: Optional[str] = None
    implementation_priority: str = "medium"  # low, medium, high
    resource_requirements: Dict[str, Any] = {}
    
    discovered_date: datetime
    last_updated: datetime

class CompetitionAnalyticsManager:
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/frontend-market/data/competition_analytics.db"
        self.init_database()
        
        # Analysis configurations
        self.analysis_weights = {
            AnalysisType.TECHNICAL: 0.25,
            AnalysisType.MARKET: 0.20,
            AnalysisType.FEATURE: 0.20,
            AnalysisType.PERFORMANCE: 0.15,
            AnalysisType.SEO: 0.10,
            AnalysisType.PRICING: 0.10
        }
        
        # Competitor discovery sources
        self.discovery_sources = [
            "builtwith.com",
            "crunchbase.com",
            "producthunt.com",
            "github.com",
            "similarweb.com",
            "alexa.com"
        ]
    
    def init_database(self):
        """Initialize competition analytics database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Competitors table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS competitors (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                tier TEXT NOT NULL,
                category TEXT NOT NULL,
                active BOOLEAN DEFAULT TRUE,
                discovery_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_analyzed TIMESTAMP,
                data TEXT NOT NULL
            )
        ''')
        
        # Competitive features table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS competitive_features (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                feature_importance REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT NOT NULL
            )
        ''')
        
        # Market analyses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_analyses (
                id TEXT PRIMARY KEY,
                frontend_id TEXT NOT NULL,
                analysis_type TEXT NOT NULL,
                analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                confidence_level REAL DEFAULT 0.8,
                data TEXT NOT NULL
            )
        ''')
        
        # Trend analyses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trend_analyses (
                id TEXT PRIMARY KEY,
                trend_name TEXT NOT NULL,
                category TEXT NOT NULL,
                current_adoption REAL DEFAULT 0.0,
                growth_rate REAL DEFAULT 0.0,
                potential_impact TEXT DEFAULT 'medium',
                discovered_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT NOT NULL
            )
        ''')
        
        # Competitor tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS competitor_metrics (
                id TEXT PRIMARY KEY,
                competitor_id TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                measurement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_source TEXT,
                FOREIGN KEY (competitor_id) REFERENCES competitors (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def discover_competitors(self, frontend_id: str, 
                                 discovery_criteria: Dict[str, Any]) -> List[CompetitorProfile]:
        """Discover new competitors using various data sources"""
        
        discovered_competitors = []
        
        # Extract search terms
        keywords = discovery_criteria.get("keywords", [])
        category = discovery_criteria.get("category", "")
        target_urls = discovery_criteria.get("target_urls", [])
        
        # GitHub repository discovery
        github_competitors = await self._discover_from_github(keywords, category)
        discovered_competitors.extend(github_competitors)
        
        # Product Hunt discovery
        ph_competitors = await self._discover_from_producthunt(keywords)
        discovered_competitors.extend(ph_competitors)
        
        # Similar website discovery
        similar_competitors = await self._discover_similar_websites(target_urls)
        discovered_competitors.extend(similar_competitors)
        
        # Web scraping for feature competitors
        feature_competitors = await self._discover_feature_competitors(keywords, category)
        discovered_competitors.extend(feature_competitors)
        
        # Remove duplicates and store
        unique_competitors = {}
        for competitor in discovered_competitors:
            url_key = competitor.url.lower()
            if url_key not in unique_competitors:
                unique_competitors[url_key] = competitor
        
        # Store new competitors
        stored_competitors = []
        for competitor in unique_competitors.values():
            stored_competitor = await self._store_competitor(competitor)
            stored_competitors.append(stored_competitor)
        
        logger.info(f"Discovered {len(stored_competitors)} new competitors for frontend {frontend_id}")
        return stored_competitors
    
    async def _discover_from_github(self, keywords: List[str], category: str) -> List[CompetitorProfile]:
        """Discover competitors from GitHub repositories"""
        
        competitors = []
        
        # Simulate GitHub API search
        for keyword in keywords[:3]:  # Limit to avoid rate limits
            # Mock GitHub repository data
            mock_repos = [
                {
                    "name": f"{keyword}-frontend",
                    "url": f"https://github.com/company/{keyword}-app",
                    "description": f"Modern {keyword} application built with React",
                    "stars": np.random.randint(100, 5000),
                    "language": np.random.choice(["TypeScript", "JavaScript", "Vue", "React"]),
                    "created_at": datetime.now() - timedelta(days=np.random.randint(30, 365))
                }
                for _ in range(3)
            ]
            
            for repo in mock_repos:
                competitor = CompetitorProfile(
                    id=f"COMP_{uuid.uuid4().hex[:8].upper()}",
                    name=repo["name"],
                    url=repo["url"],
                    description=repo["description"],
                    tier=CompetitorTier.INDIRECT,
                    category=category,
                    framework=repo["language"],
                    tech_stack=[repo["language"], "Node.js", "Express"],
                    discovery_date=datetime.now(),
                    last_analyzed=datetime.now(),
                    confidence_score=0.7
                )
                competitors.append(competitor)
        
        return competitors
    
    async def _discover_from_producthunt(self, keywords: List[str]) -> List[CompetitorProfile]:
        """Discover competitors from Product Hunt"""
        
        competitors = []
        
        # Simulate Product Hunt discovery
        for keyword in keywords[:2]:
            mock_products = [
                {
                    "name": f"{keyword.title()}Builder",
                    "url": f"https://{keyword}builder.com",
                    "description": f"Build amazing {keyword} experiences",
                    "votes": np.random.randint(50, 1000),
                    "comments": np.random.randint(5, 100)
                }
                for _ in range(2)
            ]
            
            for product in mock_products:
                competitor = CompetitorProfile(
                    id=f"COMP_{uuid.uuid4().hex[:8].upper()}",
                    name=product["name"],
                    url=product["url"],
                    description=product["description"],
                    tier=CompetitorTier.DIRECT,
                    category="saas",
                    estimated_users=product["votes"] * 10,
                    social_presence_score=min(product["comments"] / 10, 5.0),
                    discovery_date=datetime.now(),
                    last_analyzed=datetime.now(),
                    confidence_score=0.8
                )
                competitors.append(competitor)
        
        return competitors
    
    async def _discover_similar_websites(self, target_urls: List[str]) -> List[CompetitorProfile]:
        """Discover similar websites using web analysis"""
        
        competitors = []
        
        # Simulate similar website discovery
        for url in target_urls:
            domain = url.split("//")[-1].split("/")[0]
            
            # Mock similar websites
            similar_sites = [
                f"similar-{domain}",
                f"alternative-to-{domain}",
                f"{domain.replace('.com', '')}-competitor.com"
            ]
            
            for site in similar_sites:
                competitor = CompetitorProfile(
                    id=f"COMP_{uuid.uuid4().hex[:8].upper()}",
                    name=site.split(".")[0].replace("-", " ").title(),
                    url=f"https://{site}",
                    description=f"Similar service to {domain}",
                    tier=CompetitorTier.DIRECT,
                    category="web_app",
                    estimated_users=np.random.randint(1000, 50000),
                    performance_score=np.random.uniform(60, 95),
                    discovery_date=datetime.now(),
                    last_analyzed=datetime.now(),
                    confidence_score=0.6
                )
                competitors.append(competitor)
        
        return competitors[:5]  # Limit results
    
    async def _discover_feature_competitors(self, keywords: List[str], category: str) -> List[CompetitorProfile]:
        """Discover competitors with similar features"""
        
        competitors = []
        
        # Feature-based competitor discovery simulation
        feature_patterns = {
            "dashboard": ["analytics", "metrics", "reporting"],
            "ecommerce": ["cart", "checkout", "payments"],
            "social": ["feed", "messaging", "profiles"],
            "productivity": ["tasks", "calendar", "collaboration"]
        }
        
        related_features = feature_patterns.get(category, keywords)
        
        for feature in related_features[:3]:
            competitor = CompetitorProfile(
                id=f"COMP_{uuid.uuid4().hex[:8].upper()}",
                name=f"{feature.title()}Pro",
                url=f"https://{feature}pro.com",
                description=f"Professional {feature} solution",
                tier=CompetitorTier.SUBSTITUTE,
                category=category,
                tags=[feature, category, "saas"],
                pricing_model="subscription",
                estimated_revenue=np.random.uniform(10000, 500000),
                discovery_date=datetime.now(),
                last_analyzed=datetime.now(),
                confidence_score=0.5
            )
            competitors.append(competitor)
        
        return competitors
    
    async def analyze_competitive_landscape(self, frontend_id: str, 
                                          analysis_types: List[AnalysisType] = None) -> MarketAnalysis:
        """Perform comprehensive competitive landscape analysis"""
        
        if analysis_types is None:
            analysis_types = [AnalysisType.MARKET, AnalysisType.FEATURE, AnalysisType.PERFORMANCE]
        
        analysis_id = f"ANALYSIS_{uuid.uuid4().hex[:8].upper()}"
        
        # Get active competitors
        competitors = await self._get_active_competitors(frontend_id)
        
        # Perform different types of analysis
        combined_results = {
            "market_position": {},
            "competitive_gaps": [],
            "opportunities": [],
            "threats": [],
            "our_metrics": {},
            "competitor_metrics": {},
            "market_averages": {},
            "key_insights": [],
            "recommendations": []
        }
        
        for analysis_type in analysis_types:
            if analysis_type == AnalysisType.MARKET:
                market_results = await self._analyze_market_position(frontend_id, competitors)
                combined_results["market_position"].update(market_results)
                
            elif analysis_type == AnalysisType.FEATURE:
                feature_results = await self._analyze_feature_comparison(frontend_id, competitors)
                combined_results["competitive_gaps"].extend(feature_results.get("gaps", []))
                combined_results["opportunities"].extend(feature_results.get("opportunities", []))
                
            elif analysis_type == AnalysisType.PERFORMANCE:
                perf_results = await self._analyze_performance_comparison(frontend_id, competitors)
                combined_results["our_metrics"].update(perf_results.get("our_metrics", {}))
                combined_results["competitor_metrics"].update(perf_results.get("competitor_metrics", {}))
                combined_results["market_averages"].update(perf_results.get("averages", {}))
                
            elif analysis_type == AnalysisType.PRICING:
                pricing_results = await self._analyze_pricing_landscape(competitors)
                combined_results["market_position"]["pricing"] = pricing_results
                
            elif analysis_type == AnalysisType.SEO:
                seo_results = await self._analyze_seo_competition(frontend_id, competitors)
                combined_results["threats"].extend(seo_results.get("threats", []))
                combined_results["opportunities"].extend(seo_results.get("opportunities", []))
        
        # Generate insights and recommendations
        insights = await self._generate_insights(combined_results, competitors)
        combined_results["key_insights"] = insights["insights"]
        combined_results["recommendations"] = insights["recommendations"]
        
        # Create analysis record
        analysis = MarketAnalysis(
            id=analysis_id,
            frontend_id=frontend_id,
            analysis_type=analysis_types[0] if len(analysis_types) == 1 else AnalysisType.MARKET,
            competitors_analyzed=[c.id for c in competitors],
            analysis_date=datetime.now(),
            **combined_results
        )
        
        # Store analysis
        await self._store_market_analysis(analysis)
        
        logger.info(f"Completed competitive landscape analysis {analysis_id} for frontend {frontend_id}")
        return analysis
    
    async def _analyze_market_position(self, frontend_id: str, 
                                     competitors: List[CompetitorProfile]) -> Dict[str, Any]:
        """Analyze market position relative to competitors"""
        
        # Simulate market position analysis
        total_market_size = sum(c.estimated_users for c in competitors) + 10000  # +our users
        our_market_share = 10000 / total_market_size * 100
        
        # Competitor market shares
        competitor_shares = {}
        for competitor in competitors[:5]:  # Top 5 competitors
            share = competitor.estimated_users / total_market_size * 100
            competitor_shares[competitor.name] = share
        
        # Market concentration
        top_3_share = sum(sorted(competitor_shares.values(), reverse=True)[:3])
        market_concentration = "high" if top_3_share > 60 else "medium" if top_3_share > 40 else "low"
        
        # Growth trends
        avg_competitor_growth = np.random.uniform(5, 25)  # 5-25% annual growth
        
        return {
            "our_market_share": our_market_share,
            "competitor_shares": competitor_shares,
            "market_size": total_market_size,
            "market_concentration": market_concentration,
            "growth_rate": avg_competitor_growth,
            "position_ranking": len([c for c in competitors if c.estimated_users > 10000]) + 1
        }
    
    async def _analyze_feature_comparison(self, frontend_id: str, 
                                        competitors: List[CompetitorProfile]) -> Dict[str, Any]:
        """Analyze feature comparison with competitors"""
        
        # Get competitive features
        competitive_features = await self._get_competitive_features()
        
        gaps = []
        opportunities = []
        
        for feature in competitive_features:
            # Count how many competitors have this feature
            competitor_implementations = len([
                c for c in competitors 
                if c.id in feature.competitor_implementations
            ])
            
            competitor_coverage = competitor_implementations / len(competitors) if competitors else 0
            
            # Identify gaps (features we're missing that competitors have)
            if not feature.our_implementation and competitor_coverage > 0.3:
                gaps.append({
                    "feature": feature.name,
                    "category": feature.category,
                    "competitor_coverage": competitor_coverage,
                    "importance": feature.feature_importance,
                    "implementation_difficulty": feature.implementation_difficulty
                })
            
            # Identify opportunities (features few competitors have)
            elif feature.our_implementation and competitor_coverage < 0.2:
                opportunities.append({
                    "feature": feature.name,
                    "category": feature.category,
                    "differentiation_potential": 1 - competitor_coverage,
                    "our_quality": feature.our_quality_score
                })
        
        return {
            "gaps": gaps,
            "opportunities": opportunities,
            "feature_coverage": {
                "ours": len([f for f in competitive_features if f.our_implementation]),
                "avg_competitor": mean([
                    len([f for f in competitive_features if c.id in f.competitor_implementations])
                    for c in competitors
                ]) if competitors else 0
            }
        }
    
    async def _analyze_performance_comparison(self, frontend_id: str, 
                                           competitors: List[CompetitorProfile]) -> Dict[str, Any]:
        """Analyze performance metrics comparison"""
        
        # Our simulated metrics
        our_metrics = {
            "performance_score": 78.5,
            "load_time": 2.3,
            "seo_score": 85.2,
            "accessibility_score": 92.1,
            "mobile_score": 88.7
        }
        
        # Competitor metrics
        competitor_metrics = {}
        for competitor in competitors:
            competitor_metrics[competitor.id] = {
                "performance_score": competitor.performance_score or np.random.uniform(60, 95),
                "load_time": np.random.uniform(1.5, 4.0),
                "seo_score": competitor.seo_score or np.random.uniform(65, 95),
                "accessibility_score": np.random.uniform(70, 95),
                "mobile_score": np.random.uniform(75, 95)
            }
        
        # Calculate market averages
        all_competitor_metrics = list(competitor_metrics.values())
        market_averages = {}
        
        if all_competitor_metrics:
            for metric in our_metrics.keys():
                values = [comp_metrics[metric] for comp_metrics in all_competitor_metrics]
                market_averages[metric] = mean(values)
        
        return {
            "our_metrics": our_metrics,
            "competitor_metrics": competitor_metrics,
            "averages": market_averages,
            "rankings": {
                metric: len([
                    comp for comp in all_competitor_metrics 
                    if comp[metric] > our_metrics[metric]
                ]) + 1
                for metric in our_metrics.keys()
            }
        }
    
    async def _analyze_pricing_landscape(self, competitors: List[CompetitorProfile]) -> Dict[str, Any]:
        """Analyze competitive pricing landscape"""
        
        pricing_data = {}
        pricing_models = {}
        
        for competitor in competitors:
            if competitor.estimated_revenue > 0:
                # Estimate pricing from revenue and user base
                if competitor.estimated_users > 0:
                    arpu = competitor.estimated_revenue / competitor.estimated_users
                    pricing_data[competitor.name] = arpu
                
                pricing_models[competitor.name] = competitor.pricing_model
        
        if pricing_data:
            pricing_analysis = {
                "avg_price": mean(pricing_data.values()),
                "price_range": {
                    "min": min(pricing_data.values()),
                    "max": max(pricing_data.values())
                },
                "pricing_models": pricing_models,
                "price_distribution": pricing_data
            }
        else:
            pricing_analysis = {"message": "Insufficient pricing data available"}
        
        return pricing_analysis
    
    async def _analyze_seo_competition(self, frontend_id: str, 
                                     competitors: List[CompetitorProfile]) -> Dict[str, Any]:
        """Analyze SEO competitive landscape"""
        
        threats = []
        opportunities = []
        
        # Analyze competitor SEO strength
        strong_seo_competitors = [
            c for c in competitors 
            if c.seo_score and c.seo_score > 80
        ]
        
        if len(strong_seo_competitors) > len(competitors) * 0.5:
            threats.append({
                "type": "seo_competition",
                "description": "High SEO competition in market",
                "severity": "medium",
                "competitors": [c.name for c in strong_seo_competitors[:3]]
            })
        
        # Identify SEO opportunities
        weak_seo_competitors = [
            c for c in competitors 
            if c.seo_score and c.seo_score < 70
        ]
        
        if len(weak_seo_competitors) > 2:
            opportunities.append({
                "type": "seo_opportunity",
                "description": "SEO improvement opportunity vs competitors",
                "potential": "high",
                "weak_competitors": len(weak_seo_competitors)
            })
        
        return {
            "threats": threats,
            "opportunities": opportunities,
            "seo_landscape": {
                "avg_seo_score": mean([c.seo_score for c in competitors if c.seo_score]),
                "strong_competitors": len(strong_seo_competitors),
                "weak_competitors": len(weak_seo_competitors)
            }
        }
    
    async def track_competitor_trends(self, competitor_ids: List[str] = None) -> List[TrendAnalysis]:
        """Track and analyze competitor trends"""
        
        if competitor_ids is None:
            # Get all active competitors
            competitors = await self._get_all_active_competitors()
            competitor_ids = [c.id for c in competitors[:10]]  # Limit to top 10
        
        trends = []
        
        # Technology trends
        tech_trends = await self._analyze_technology_trends(competitor_ids)
        trends.extend(tech_trends)
        
        # Feature trends
        feature_trends = await self._analyze_feature_trends(competitor_ids)
        trends.extend(feature_trends)
        
        # Market trends
        market_trends = await self._analyze_market_trends(competitor_ids)
        trends.extend(market_trends)
        
        # Store trends
        for trend in trends:
            await self._store_trend_analysis(trend)
        
        logger.info(f"Analyzed {len(trends)} competitive trends")
        return trends
    
    async def _analyze_technology_trends(self, competitor_ids: List[str]) -> List[TrendAnalysis]:
        """Analyze technology adoption trends among competitors"""
        
        competitors = await self._get_competitors_by_ids(competitor_ids)
        
        # Count technology adoption
        tech_adoption = {}
        for competitor in competitors:
            for tech in competitor.tech_stack:
                if tech not in tech_adoption:
                    tech_adoption[tech] = []
                tech_adoption[tech].append(competitor.id)
        
        trends = []
        
        # Identify trending technologies
        for tech, adopters in tech_adoption.items():
            adoption_rate = len(adopters) / len(competitors)
            
            if adoption_rate > 0.3:  # 30%+ adoption
                trend = TrendAnalysis(
                    id=f"TREND_{uuid.uuid4().hex[:8].upper()}",
                    trend_name=f"{tech} Adoption",
                    category="technology",
                    description=f"Increasing adoption of {tech} among competitors",
                    current_adoption=adoption_rate,
                    growth_rate=np.random.uniform(5, 20),  # Estimated monthly growth
                    relevance_to_us=0.8 if tech in ["React", "Vue", "TypeScript"] else 0.5,
                    potential_impact="high" if adoption_rate > 0.6 else "medium",
                    competitors_adopting=adopters,
                    discovered_date=datetime.now(),
                    last_updated=datetime.now()
                )
                trends.append(trend)
        
        return trends
    
    async def _analyze_feature_trends(self, competitor_ids: List[str]) -> List[TrendAnalysis]:
        """Analyze feature adoption trends"""
        
        # Simulate feature trend analysis
        trending_features = [
            {
                "name": "AI-powered Analytics",
                "adoption": 0.4,
                "growth": 15.2,
                "impact": "high"
            },
            {
                "name": "Real-time Collaboration",
                "adoption": 0.6,
                "growth": 8.5,
                "impact": "medium"
            },
            {
                "name": "Progressive Web App",
                "adoption": 0.3,
                "growth": 12.0,
                "impact": "medium"
            }
        ]
        
        trends = []
        
        for feature in trending_features:
            trend = TrendAnalysis(
                id=f"TREND_{uuid.uuid4().hex[:8].upper()}",
                trend_name=feature["name"],
                category="feature",
                description=f"Growing adoption of {feature['name']} functionality",
                current_adoption=feature["adoption"],
                growth_rate=feature["growth"],
                relevance_to_us=0.8,
                potential_impact=feature["impact"],
                time_to_mainstream=int(12 / (feature["growth"] / 10)),  # Rough estimate
                discovered_date=datetime.now(),
                last_updated=datetime.now()
            )
            trends.append(trend)
        
        return trends
    
    async def _analyze_market_trends(self, competitor_ids: List[str]) -> List[TrendAnalysis]:
        """Analyze market behavior trends"""
        
        market_trends_data = [
            {
                "name": "Freemium Model Adoption",
                "adoption": 0.7,
                "growth": 5.2,
                "impact": "high"
            },
            {
                "name": "Mobile-First Development",
                "adoption": 0.8,
                "growth": 3.1,
                "impact": "medium"
            }
        ]
        
        trends = []
        
        for trend_data in market_trends_data:
            trend = TrendAnalysis(
                id=f"TREND_{uuid.uuid4().hex[:8].upper()}",
                trend_name=trend_data["name"],
                category="market",
                description=f"Market trend: {trend_data['name']}",
                current_adoption=trend_data["adoption"],
                growth_rate=trend_data["growth"],
                relevance_to_us=0.9,
                potential_impact=trend_data["impact"],
                discovered_date=datetime.now(),
                last_updated=datetime.now()
            )
            trends.append(trend)
        
        return trends
    
    async def _generate_insights(self, analysis_results: Dict[str, Any], 
                               competitors: List[CompetitorProfile]) -> Dict[str, Any]:
        """Generate strategic insights from competitive analysis"""
        
        insights = []
        recommendations = []
        
        # Market position insights
        if "market_position" in analysis_results:
            market_pos = analysis_results["market_position"]
            if "our_market_share" in market_pos:
                if market_pos["our_market_share"] < 5:
                    insights.append("Low market share indicates significant growth opportunity")
                    recommendations.append({
                        "category": "market_expansion",
                        "priority": "high",
                        "recommendation": "Invest in user acquisition and market expansion",
                        "expected_impact": "increase market share by 2-3x"
                    })
        
        # Performance insights
        if "our_metrics" in analysis_results and "market_averages" in analysis_results:
            our_metrics = analysis_results["our_metrics"]
            averages = analysis_results["market_averages"]
            
            for metric, our_value in our_metrics.items():
                avg_value = averages.get(metric, 0)
                if avg_value > 0:
                    if our_value < avg_value * 0.9:  # 10% below average
                        insights.append(f"Below-average performance in {metric}")
                        recommendations.append({
                            "category": "performance",
                            "priority": "medium",
                            "recommendation": f"Improve {metric} to match market standards",
                            "current_gap": f"{((avg_value - our_value) / avg_value * 100):.1f}%"
                        })
                    elif our_value > avg_value * 1.1:  # 10% above average
                        insights.append(f"Competitive advantage in {metric}")
        
        # Gap analysis insights
        gaps = analysis_results.get("competitive_gaps", [])
        high_priority_gaps = [g for g in gaps if g.get("importance", 0) > 3]
        
        if high_priority_gaps:
            insights.append(f"Missing {len(high_priority_gaps)} high-priority features")
            recommendations.append({
                "category": "product_development",
                "priority": "high",
                "recommendation": "Prioritize development of missing key features",
                "features": [g["feature"] for g in high_priority_gaps[:3]]
            })
        
        # Opportunity insights
        opportunities = analysis_results.get("opportunities", [])
        if opportunities:
            insights.append(f"Identified {len(opportunities)} differentiation opportunities")
            recommendations.append({
                "category": "competitive_advantage",
                "priority": "medium",
                "recommendation": "Leverage unique features for competitive positioning",
                "opportunities": len(opportunities)
            })
        
        return {
            "insights": insights,
            "recommendations": recommendations
        }
    
    async def _get_active_competitors(self, frontend_id: str) -> List[CompetitorProfile]:
        """Get active competitors for a frontend"""
        
        # For demo, return mock competitors
        # In production, this would filter by category/relevance
        return await self._get_all_active_competitors()
    
    async def _get_all_active_competitors(self) -> List[CompetitorProfile]:
        """Get all active competitors"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT data FROM competitors 
            WHERE active = TRUE 
            ORDER BY last_analyzed DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        return [CompetitorProfile(**json.loads(result[0])) for result in results]
    
    async def _get_competitors_by_ids(self, competitor_ids: List[str]) -> List[CompetitorProfile]:
        """Get competitors by their IDs"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        placeholders = ",".join("?" * len(competitor_ids))
        cursor.execute(f'''
            SELECT data FROM competitors 
            WHERE id IN ({placeholders})
        ''', competitor_ids)
        
        results = cursor.fetchall()
        conn.close()
        
        return [CompetitorProfile(**json.loads(result[0])) for result in results]
    
    async def _get_competitive_features(self) -> List[CompetitiveFeature]:
        """Get all competitive features"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT data FROM competitive_features')
        results = cursor.fetchall()
        conn.close()
        
        return [CompetitiveFeature(**json.loads(result[0])) for result in results]
    
    async def _store_competitor(self, competitor: CompetitorProfile) -> CompetitorProfile:
        """Store competitor in database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO competitors 
            (id, name, url, tier, category, active, discovery_date, last_analyzed, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            competitor.id, competitor.name, competitor.url,
            competitor.tier.value, competitor.category, competitor.active,
            competitor.discovery_date.isoformat(),
            competitor.last_analyzed.isoformat(),
            competitor.model_dump_json()
        ))
        
        conn.commit()
        conn.close()
        
        return competitor
    
    async def _store_market_analysis(self, analysis: MarketAnalysis):
        """Store market analysis in database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO market_analyses 
            (id, frontend_id, analysis_type, analysis_date, confidence_level, data)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            analysis.id, analysis.frontend_id, analysis.analysis_type.value,
            analysis.analysis_date.isoformat(), analysis.confidence_level,
            analysis.model_dump_json()
        ))
        
        conn.commit()
        conn.close()
    
    async def _store_trend_analysis(self, trend: TrendAnalysis):
        """Store trend analysis in database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO trend_analyses 
            (id, trend_name, category, current_adoption, growth_rate, 
             potential_impact, discovered_date, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trend.id, trend.trend_name, trend.category,
            trend.current_adoption, trend.growth_rate,
            trend.potential_impact, trend.discovered_date.isoformat(),
            trend.model_dump_json()
        ))
        
        conn.commit()
        conn.close()
    
    async def generate_competitive_report(self, frontend_id: str) -> Dict[str, Any]:
        """Generate comprehensive competitive intelligence report"""
        
        # Get latest analysis
        analysis = await self.analyze_competitive_landscape(frontend_id)
        
        # Get trends
        trends = await self.track_competitor_trends()
        
        # Get active competitors
        competitors = await self._get_active_competitors(frontend_id)
        
        report = {
            "report_id": f"COMP_REPORT_{uuid.uuid4().hex[:8].upper()}",
            "frontend_id": frontend_id,
            "generated_at": datetime.now().isoformat(),
            
            "executive_summary": {
                "competitors_tracked": len(competitors),
                "market_position": analysis.market_position,
                "key_insights": analysis.key_insights[:5],
                "top_recommendations": analysis.recommendations[:3]
            },
            
            "competitive_landscape": {
                "direct_competitors": len([c for c in competitors if c.tier == CompetitorTier.DIRECT]),
                "indirect_competitors": len([c for c in competitors if c.tier == CompetitorTier.INDIRECT]),
                "emerging_threats": len([c for c in competitors if c.tier == CompetitorTier.EMERGING])
            },
            
            "performance_comparison": {
                "our_metrics": analysis.our_metrics,
                "market_averages": analysis.market_averages,
                "competitive_gaps": len(analysis.competitive_gaps),
                "opportunities": len(analysis.opportunities)
            },
            
            "trend_analysis": {
                "active_trends": len(trends),
                "high_impact_trends": len([t for t in trends if t.potential_impact == "high"]),
                "technology_trends": len([t for t in trends if t.category == "technology"]),
                "feature_trends": len([t for t in trends if t.category == "feature"])
            },
            
            "strategic_recommendations": analysis.recommendations,
            
            "next_steps": [
                "Monitor top 3 direct competitors weekly",
                "Implement high-priority missing features",
                "Track technology adoption trends",
                "Update competitive analysis monthly"
            ]
        }
        
        return report

# Global instance
competition_analytics_manager = CompetitionAnalyticsManager()