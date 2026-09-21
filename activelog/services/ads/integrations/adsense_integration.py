"""
Google AdSense Integration - Advanced AdSense management and optimization.
Features: Auto-optimization, A/B testing, performance monitoring, and compliance.
"""

import asyncio
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import aiohttp
import base64

@dataclass
class AdSenseAccount:
    """AdSense account configuration."""
    client_id: str
    publisher_id: str
    api_key: str
    account_id: str
    currency: str = "USD"
    timezone: str = "America/New_York"

@dataclass
class AdUnit:
    """AdSense ad unit configuration."""
    id: str
    name: str
    code: str
    ad_client: str
    ad_slot: str
    size: str
    status: str = "ACTIVE"
    created_date: datetime = None

@dataclass
class AdPerformance:
    """Ad performance metrics."""
    ad_unit_id: str
    date: datetime
    impressions: int
    clicks: int
    revenue: float
    ctr: float
    rpm: float
    coverage: float

class AdSenseAPI:
    """Google AdSense API client."""
    
    def __init__(self, account: AdSenseAccount):
        self.account = account
        self.base_url = "https://www.googleapis.com/adsense/v2"
        self.session = None
    
    async def initialize(self):
        """Initialize the API client."""
        self.session = aiohttp.ClientSession()
        print("🔗 AdSense API client initialized")
    
    async def close(self):
        """Close the API client."""
        if self.session:
            await self.session.close()
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get AdSense account information."""
        # Mock implementation - in real usage, make actual API calls
        return {
            "account_id": self.account.account_id,
            "name": "ActiveLog Publisher",
            "currency": self.account.currency,
            "timezone": self.account.timezone,
            "status": "READY",
            "creation_time": "2024-01-01T00:00:00Z"
        }
    
    async def list_ad_units(self) -> List[AdUnit]:
        """List all ad units."""
        # Mock implementation
        mock_units = [
            AdUnit(
                id="ad_unit_1",
                name="Header Banner",
                code="ca-pub-1234567890123456",
                ad_client="ca-pub-1234567890123456",
                ad_slot="1234567890",
                size="728x90",
                created_date=datetime.now() - timedelta(days=30)
            ),
            AdUnit(
                id="ad_unit_2",
                name="Sidebar Rectangle",
                code="ca-pub-1234567890123456",
                ad_client="ca-pub-1234567890123456",
                ad_slot="2345678901",
                size="300x250",
                created_date=datetime.now() - timedelta(days=25)
            ),
            AdUnit(
                id="ad_unit_3",
                name="Mobile Banner",
                code="ca-pub-1234567890123456",
                ad_client="ca-pub-1234567890123456",
                ad_slot="3456789012",
                size="320x50",
                created_date=datetime.now() - timedelta(days=20)
            )
        ]
        
        return mock_units
    
    async def create_ad_unit(self, name: str, size: str) -> AdUnit:
        """Create a new ad unit."""
        # Mock implementation
        ad_unit = AdUnit(
            id=f"ad_unit_{datetime.now().timestamp()}",
            name=name,
            code=self.account.client_id,
            ad_client=self.account.client_id,
            ad_slot=str(int(datetime.now().timestamp())),
            size=size,
            created_date=datetime.now()
        )
        
        print(f"✅ Created ad unit: {name} ({size})")
        return ad_unit
    
    async def get_performance_report(self, start_date: datetime, end_date: datetime,
                                   ad_unit_ids: Optional[List[str]] = None) -> List[AdPerformance]:
        """Get performance report for ad units."""
        # Mock implementation with realistic data
        mock_performance = []
        
        # Generate mock data for each day in range
        current_date = start_date
        while current_date <= end_date:
            # Simulate performance for each ad unit
            units = ad_unit_ids or ["ad_unit_1", "ad_unit_2", "ad_unit_3"]
            
            for unit_id in units:
                # Generate realistic mock metrics
                base_impressions = 1000 + int(unit_id[-1]) * 200
                daily_variance = 0.8 + (hash(f"{unit_id}{current_date}") % 100) / 250
                
                impressions = int(base_impressions * daily_variance)
                clicks = int(impressions * 0.02)  # 2% CTR
                revenue = impressions * 0.001 + clicks * 0.05  # $1 CPM + $0.05 CPC
                ctr = (clicks / impressions * 100) if impressions > 0 else 0
                rpm = (revenue / impressions * 1000) if impressions > 0 else 0
                coverage = 95.0 + (hash(f"{unit_id}{current_date}") % 10)
                
                performance = AdPerformance(
                    ad_unit_id=unit_id,
                    date=current_date,
                    impressions=impressions,
                    clicks=clicks,
                    revenue=round(revenue, 2),
                    ctr=round(ctr, 2),
                    rpm=round(rpm, 2),
                    coverage=min(coverage, 100.0)
                )
                
                mock_performance.append(performance)
            
            current_date += timedelta(days=1)
        
        return mock_performance
    
    async def update_ad_unit_targeting(self, ad_unit_id: str, 
                                     targeting_config: Dict[str, Any]) -> bool:
        """Update ad unit targeting configuration."""
        # Mock implementation
        print(f"📊 Updated targeting for {ad_unit_id}: {targeting_config}")
        return True
    
    async def pause_ad_unit(self, ad_unit_id: str) -> bool:
        """Pause an ad unit."""
        print(f"⏸️ Paused ad unit: {ad_unit_id}")
        return True
    
    async def resume_ad_unit(self, ad_unit_id: str) -> bool:
        """Resume an ad unit."""
        print(f"▶️ Resumed ad unit: {ad_unit_id}")
        return True

class AdOptimizer:
    """Automatic ad optimization system."""
    
    def __init__(self, adsense_api: AdSenseAPI):
        self.api = adsense_api
        self.optimization_rules = self._load_optimization_rules()
        self.ab_tests = {}
    
    def _load_optimization_rules(self) -> Dict[str, Any]:
        """Load optimization rules and thresholds."""
        return {
            "performance_thresholds": {
                "min_ctr": 1.0,  # Minimum 1% CTR
                "min_rpm": 0.50,  # Minimum $0.50 RPM
                "min_coverage": 85.0,  # Minimum 85% ad coverage
                "max_ctr": 10.0   # Maximum 10% CTR (suspicious)
            },
            "optimization_triggers": {
                "low_performance_days": 7,  # Days of low performance before action
                "high_performance_days": 3,  # Days of high performance before scaling
                "minimum_impressions": 1000  # Minimum impressions for valid data
            },
            "actions": {
                "pause_underperforming": True,
                "increase_frequency_high_performing": True,
                "adjust_targeting": True,
                "create_similar_units": True
            }
        }
    
    async def analyze_performance(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Analyze ad performance and generate recommendations."""
        performance_data = await self.api.get_performance_report(start_date, end_date)
        
        if not performance_data:
            return {"error": "No performance data available"}
        
        # Group by ad unit
        unit_performance = {}
        for perf in performance_data:
            unit_id = perf.ad_unit_id
            if unit_id not in unit_performance:
                unit_performance[unit_id] = []
            unit_performance[unit_id].append(perf)
        
        # Analyze each unit
        analysis_results = {}
        recommendations = []
        
        for unit_id, performances in unit_performance.items():
            unit_analysis = await self._analyze_unit_performance(unit_id, performances)
            analysis_results[unit_id] = unit_analysis
            
            # Generate recommendations
            unit_recommendations = await self._generate_recommendations(unit_id, unit_analysis)
            recommendations.extend(unit_recommendations)
        
        return {
            "analysis_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "unit_analysis": analysis_results,
            "recommendations": recommendations,
            "summary": self._generate_summary(analysis_results),
            "generated_at": datetime.now().isoformat()
        }
    
    async def _analyze_unit_performance(self, unit_id: str, 
                                      performances: List[AdPerformance]) -> Dict[str, Any]:
        """Analyze performance for a specific ad unit."""
        if not performances:
            return {"error": "No performance data"}
        
        # Calculate aggregated metrics
        total_impressions = sum(p.impressions for p in performances)
        total_clicks = sum(p.clicks for p in performances)
        total_revenue = sum(p.revenue for p in performances)
        
        avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        avg_rpm = (total_revenue / total_impressions * 1000) if total_impressions > 0 else 0
        avg_coverage = sum(p.coverage for p in performances) / len(performances)
        
        # Performance trends
        recent_performances = performances[-3:]  # Last 3 days
        if len(recent_performances) >= 2:
            recent_rpm = sum(p.rpm for p in recent_performances) / len(recent_performances)
            previous_rpm = sum(p.rpm for p in performances[:-3]) / len(performances[:-3]) if len(performances) > 3 else recent_rpm
            trend = "improving" if recent_rpm > previous_rpm * 1.1 else "declining" if recent_rpm < previous_rpm * 0.9 else "stable"
        else:
            trend = "insufficient_data"
        
        # Performance rating
        thresholds = self.optimization_rules["performance_thresholds"]
        rating = "excellent"
        if avg_ctr < thresholds["min_ctr"] or avg_rpm < thresholds["min_rpm"] or avg_coverage < thresholds["min_coverage"]:
            rating = "poor"
        elif avg_ctr < thresholds["min_ctr"] * 1.5 or avg_rpm < thresholds["min_rpm"] * 1.5:
            rating = "average"
        elif avg_ctr > thresholds["max_ctr"]:
            rating = "suspicious"
        else:
            rating = "good"
        
        return {
            "unit_id": unit_id,
            "days_analyzed": len(performances),
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "total_revenue": round(total_revenue, 2),
            "average_ctr": round(avg_ctr, 2),
            "average_rpm": round(avg_rpm, 2),
            "average_coverage": round(avg_coverage, 1),
            "trend": trend,
            "rating": rating,
            "meets_thresholds": rating in ["good", "excellent"]
        }
    
    async def _generate_recommendations(self, unit_id: str, 
                                      analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate optimization recommendations for an ad unit."""
        recommendations = []
        
        if analysis.get("rating") == "poor":
            recommendations.append({
                "type": "performance_warning",
                "unit_id": unit_id,
                "priority": "high",
                "action": "review_placement",
                "description": f"Ad unit {unit_id} is underperforming. Consider reviewing placement and targeting.",
                "metrics": {
                    "ctr": analysis.get("average_ctr", 0),
                    "rpm": analysis.get("average_rpm", 0)
                }
            })
            
            if analysis.get("average_coverage", 0) < 85:
                recommendations.append({
                    "type": "coverage_improvement",
                    "unit_id": unit_id,
                    "priority": "medium",
                    "action": "optimize_targeting",
                    "description": f"Low ad coverage ({analysis.get('average_coverage', 0):.1f}%). Broaden targeting criteria.",
                    "current_coverage": analysis.get("average_coverage", 0)
                })
        
        elif analysis.get("rating") == "excellent":
            recommendations.append({
                "type": "scaling_opportunity",
                "unit_id": unit_id,
                "priority": "medium",
                "action": "create_similar_units",
                "description": f"Ad unit {unit_id} is performing excellently. Consider creating similar units.",
                "metrics": {
                    "ctr": analysis.get("average_ctr", 0),
                    "rpm": analysis.get("average_rpm", 0)
                }
            })
        
        elif analysis.get("rating") == "suspicious":
            recommendations.append({
                "type": "fraud_investigation",
                "unit_id": unit_id,
                "priority": "critical",
                "action": "investigate_traffic",
                "description": f"Unusually high CTR ({analysis.get('average_ctr', 0):.2f}%). Investigate for invalid traffic.",
                "ctr": analysis.get("average_ctr", 0)
            })
        
        # Trend-based recommendations
        if analysis.get("trend") == "declining":
            recommendations.append({
                "type": "trend_alert",
                "unit_id": unit_id,
                "priority": "medium",
                "action": "refresh_creative",
                "description": f"Performance declining for {unit_id}. Consider refreshing ad creative or placement.",
                "trend": "declining"
            })
        
        return recommendations
    
    def _generate_summary(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overall performance summary."""
        total_units = len(analysis_results)
        
        ratings = [analysis.get("rating", "unknown") for analysis in analysis_results.values()]
        rating_counts = {
            "excellent": ratings.count("excellent"),
            "good": ratings.count("good"),
            "average": ratings.count("average"),
            "poor": ratings.count("poor"),
            "suspicious": ratings.count("suspicious")
        }
        
        total_revenue = sum(analysis.get("total_revenue", 0) for analysis in analysis_results.values())
        total_impressions = sum(analysis.get("total_impressions", 0) for analysis in analysis_results.values())
        
        return {
            "total_ad_units": total_units,
            "rating_distribution": rating_counts,
            "total_revenue": round(total_revenue, 2),
            "total_impressions": total_impressions,
            "average_performance": "good" if rating_counts["good"] + rating_counts["excellent"] > total_units * 0.7 else "needs_improvement"
        }
    
    async def auto_optimize(self, unit_id: str, analysis: Dict[str, Any]) -> List[str]:
        """Automatically apply optimization actions."""
        actions_taken = []
        
        if not self.optimization_rules["actions"].get("pause_underperforming", False):
            return actions_taken
        
        # Auto-pause underperforming units
        if analysis.get("rating") == "poor" and analysis.get("total_impressions", 0) > 5000:
            await self.api.pause_ad_unit(unit_id)
            actions_taken.append(f"Paused underperforming unit {unit_id}")
        
        # Auto-adjust targeting for low coverage
        if analysis.get("average_coverage", 0) < 80:
            targeting_config = {
                "geographic_targeting": "broader",
                "demographic_targeting": "expanded",
                "content_targeting": "relaxed"
            }
            await self.api.update_ad_unit_targeting(unit_id, targeting_config)
            actions_taken.append(f"Broadened targeting for {unit_id}")
        
        # Flag suspicious activity
        if analysis.get("rating") == "suspicious":
            actions_taken.append(f"Flagged {unit_id} for manual review (suspicious CTR)")
        
        return actions_taken

class AdSenseCompliance:
    """AdSense policy compliance monitoring."""
    
    def __init__(self):
        self.policy_rules = self._load_policy_rules()
        self.compliance_history = []
    
    def _load_policy_rules(self) -> Dict[str, Any]:
        """Load AdSense policy rules and guidelines."""
        return {
            "content_policies": {
                "prohibited_content": [
                    "adult_content",
                    "violence",
                    "illegal_activities",
                    "copyrighted_material",
                    "misleading_content"
                ],
                "restricted_content": [
                    "alcohol",
                    "gambling",
                    "healthcare",
                    "political_content"
                ]
            },
            "traffic_policies": {
                "max_ctr_threshold": 8.0,  # Suspicious if CTR > 8%
                "min_session_duration": 10,  # Minimum 10 seconds
                "max_bounce_rate": 85,  # Maximum 85% bounce rate
                "geographic_distribution_min": 5  # At least 5% from different regions
            },
            "placement_policies": {
                "min_distance_from_nav": 150,  # pixels
                "max_ads_per_page": 3,
                "prohibited_placements": [
                    "popup",
                    "email",
                    "software",
                    "exit_intent"
                ]
            }
        }
    
    async def check_content_compliance(self, page_content: str, page_url: str) -> Dict[str, Any]:
        """Check content compliance with AdSense policies."""
        violations = []
        warnings = []
        
        content_lower = page_content.lower()
        
        # Check for prohibited content
        prohibited_keywords = {
            "adult_content": ["adult", "xxx", "porn", "sex", "explicit"],
            "violence": ["violence", "weapon", "gun", "knife", "blood"],
            "illegal_activities": ["drug", "illegal", "piracy", "hack"],
            "gambling": ["casino", "bet", "poker", "gambling", "lottery"]
        }
        
        for category, keywords in prohibited_keywords.items():
            for keyword in keywords:
                if keyword in content_lower:
                    if category in self.policy_rules["content_policies"]["prohibited_content"]:
                        violations.append({
                            "type": "prohibited_content",
                            "category": category,
                            "keyword": keyword,
                            "severity": "high"
                        })
                    elif category in self.policy_rules["content_policies"]["restricted_content"]:
                        warnings.append({
                            "type": "restricted_content",
                            "category": category,
                            "keyword": keyword,
                            "severity": "medium"
                        })
        
        compliance_score = max(0, 100 - len(violations) * 30 - len(warnings) * 10)
        
        return {
            "page_url": page_url,
            "compliance_score": compliance_score,
            "violations": violations,
            "warnings": warnings,
            "recommendations": self._generate_compliance_recommendations(violations, warnings),
            "checked_at": datetime.now().isoformat()
        }
    
    async def check_traffic_compliance(self, performance_data: List[AdPerformance]) -> Dict[str, Any]:
        """Check traffic compliance with AdSense policies."""
        violations = []
        warnings = []
        
        for perf in performance_data:
            # Check CTR thresholds
            if perf.ctr > self.policy_rules["traffic_policies"]["max_ctr_threshold"]:
                violations.append({
                    "type": "suspicious_ctr",
                    "ad_unit_id": perf.ad_unit_id,
                    "ctr": perf.ctr,
                    "date": perf.date.isoformat(),
                    "severity": "high"
                })
            elif perf.ctr > self.policy_rules["traffic_policies"]["max_ctr_threshold"] * 0.8:
                warnings.append({
                    "type": "high_ctr",
                    "ad_unit_id": perf.ad_unit_id,
                    "ctr": perf.ctr,
                    "date": perf.date.isoformat(),
                    "severity": "medium"
                })
        
        return {
            "traffic_violations": violations,
            "traffic_warnings": warnings,
            "compliance_status": "compliant" if not violations else "violations_detected",
            "checked_at": datetime.now().isoformat()
        }
    
    def _generate_compliance_recommendations(self, violations: List[Dict], 
                                           warnings: List[Dict]) -> List[str]:
        """Generate compliance improvement recommendations."""
        recommendations = []
        
        if violations:
            recommendations.append("Immediately review and remove content that violates AdSense policies")
            recommendations.append("Consider implementing content moderation systems")
        
        if warnings:
            recommendations.append("Review flagged content and consider adding disclaimers or age restrictions")
            recommendations.append("Monitor content closely to prevent policy violations")
        
        if not violations and not warnings:
            recommendations.append("Content appears compliant - continue monitoring")
        
        return recommendations

class AdSenseIntegration:
    """Main AdSense integration orchestrator."""
    
    def __init__(self, account: AdSenseAccount):
        self.account = account
        self.api = AdSenseAPI(account)
        self.optimizer = None
        self.compliance = AdSenseCompliance()
        self.ad_units = []
        
        print("🚀 AdSense Integration initialized")
    
    async def initialize(self):
        """Initialize the AdSense integration."""
        await self.api.initialize()
        self.optimizer = AdOptimizer(self.api)
        
        # Load existing ad units
        self.ad_units = await self.api.list_ad_units()
        
        print(f"✅ Loaded {len(self.ad_units)} ad units")
    
    async def create_optimized_ad_unit(self, name: str, size: str, 
                                     placement: str) -> Dict[str, Any]:
        """Create a new optimized ad unit."""
        # Create the ad unit
        ad_unit = await self.api.create_ad_unit(name, size)
        
        # Add to tracking
        self.ad_units.append(ad_unit)
        
        # Generate ad code
        ad_code = self._generate_ad_code(ad_unit, placement)
        
        return {
            "ad_unit": asdict(ad_unit),
            "ad_code": ad_code,
            "placement_recommendations": self._get_placement_recommendations(size, placement)
        }
    
    def _generate_ad_code(self, ad_unit: AdUnit, placement: str) -> str:
        """Generate optimized ad code for the unit."""
        return f"""
<!-- AdSense Ad Unit: {ad_unit.name} -->
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ad_unit.ad_client}"
     crossorigin="anonymous"></script>
<ins class="adsbygoogle activelog-ad-{placement}"
     style="display:block"
     data-ad-client="{ad_unit.ad_client}"
     data-ad-slot="{ad_unit.ad_slot}"
     data-ad-format="auto"
     data-full-width-responsive="true"></ins>
<script>
     (adsbygoogle = window.adsbygoogle || []).push({{}});
</script>
<!-- End AdSense Ad Unit -->
        """.strip()
    
    def _get_placement_recommendations(self, size: str, placement: str) -> List[str]:
        """Get placement recommendations for optimal performance."""
        recommendations = []
        
        if size == "728x90":  # Leaderboard
            recommendations.extend([
                "Place above the fold for maximum visibility",
                "Ensure adequate spacing from navigation elements",
                "Consider responsive sizing for mobile devices"
            ])
        elif size == "300x250":  # Rectangle
            recommendations.extend([
                "Integrate naturally within content",
                "Place after the first paragraph for engagement",
                "Avoid placing too close to other ads"
            ])
        elif size == "320x50":  # Mobile banner
            recommendations.extend([
                "Fixed position at top or bottom of screen",
                "Ensure it doesn't interfere with navigation",
                "Test on multiple device sizes"
            ])
        
        return recommendations
    
    async def run_optimization_cycle(self) -> Dict[str, Any]:
        """Run a complete optimization cycle."""
        print("🔄 Running optimization cycle...")
        
        # Get performance data for last 7 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        # Analyze performance
        analysis = await self.optimizer.analyze_performance(start_date, end_date)
        
        # Apply auto-optimizations
        optimization_actions = []
        for unit_id, unit_analysis in analysis.get("unit_analysis", {}).items():
            actions = await self.optimizer.auto_optimize(unit_id, unit_analysis)
            optimization_actions.extend(actions)
        
        return {
            "optimization_cycle": {
                "period": f"{start_date.date()} to {end_date.date()}",
                "analysis": analysis,
                "actions_taken": optimization_actions,
                "next_cycle": (datetime.now() + timedelta(days=1)).isoformat()
            }
        }
    
    async def check_compliance(self, page_content: str, page_url: str) -> Dict[str, Any]:
        """Check comprehensive compliance for a page."""
        # Content compliance
        content_compliance = await self.compliance.check_content_compliance(page_content, page_url)
        
        # Traffic compliance (using recent performance data)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=3)
        performance_data = await self.api.get_performance_report(start_date, end_date)
        traffic_compliance = await self.compliance.check_traffic_compliance(performance_data)
        
        overall_compliance = {
            "page_url": page_url,
            "content_compliance": content_compliance,
            "traffic_compliance": traffic_compliance,
            "overall_status": "compliant" if content_compliance["compliance_score"] > 80 and traffic_compliance["compliance_status"] == "compliant" else "issues_detected",
            "checked_at": datetime.now().isoformat()
        }
        
        return overall_compliance
    
    async def get_revenue_report(self, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive revenue report."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        performance_data = await self.api.get_performance_report(start_date, end_date)
        
        if not performance_data:
            return {"error": "No performance data available"}
        
        # Aggregate data
        total_impressions = sum(p.impressions for p in performance_data)
        total_clicks = sum(p.clicks for p in performance_data)
        total_revenue = sum(p.revenue for p in performance_data)
        
        # Group by ad unit
        unit_performance = {}
        for perf in performance_data:
            unit_id = perf.ad_unit_id
            if unit_id not in unit_performance:
                unit_performance[unit_id] = {
                    "impressions": 0,
                    "clicks": 0,
                    "revenue": 0.0
                }
            
            unit_performance[unit_id]["impressions"] += perf.impressions
            unit_performance[unit_id]["clicks"] += perf.clicks
            unit_performance[unit_id]["revenue"] += perf.revenue
        
        # Calculate metrics
        overall_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        overall_rpm = (total_revenue / total_impressions * 1000) if total_impressions > 0 else 0
        
        return {
            "report_period": f"{start_date.date()} to {end_date.date()}",
            "summary": {
                "total_revenue": round(total_revenue, 2),
                "total_impressions": total_impressions,
                "total_clicks": total_clicks,
                "overall_ctr": round(overall_ctr, 2),
                "overall_rpm": round(overall_rpm, 2),
                "daily_average_revenue": round(total_revenue / days, 2)
            },
            "unit_breakdown": {
                unit_id: {
                    **metrics,
                    "ctr": round((metrics["clicks"] / metrics["impressions"] * 100) if metrics["impressions"] > 0 else 0, 2),
                    "rpm": round((metrics["revenue"] / metrics["impressions"] * 1000) if metrics["impressions"] > 0 else 0, 2)
                }
                for unit_id, metrics in unit_performance.items()
            },
            "generated_at": datetime.now().isoformat()
        }

# CLI interface for testing
async def main():
    """CLI interface for AdSense Integration testing."""
    
    # Initialize AdSense account
    account = AdSenseAccount(
        client_id="ca-pub-1234567890123456",
        publisher_id="pub-1234567890123456",
        api_key="mock_api_key",
        account_id="accounts/pub-1234567890123456"
    )
    
    adsense = AdSenseIntegration(account)
    await adsense.initialize()
    
    print("🚀 AdSense Integration Test Suite")
    print("=" * 40)
    
    # Test 1: Create optimized ad units
    print("\n1. Creating optimized ad units...")
    
    header_unit = await adsense.create_optimized_ad_unit("Header Banner", "728x90", "header")
    sidebar_unit = await adsense.create_optimized_ad_unit("Sidebar Rectangle", "300x250", "sidebar")
    mobile_unit = await adsense.create_optimized_ad_unit("Mobile Banner", "320x50", "mobile")
    
    print(f"✅ Created 3 ad units")
    
    # Test 2: Run optimization cycle
    print("\n2. Running optimization cycle...")
    
    optimization_result = await adsense.run_optimization_cycle()
    print(f"✅ Optimization completed: {len(optimization_result['optimization_cycle']['actions_taken'])} actions taken")
    
    # Test 3: Check compliance
    print("\n3. Checking compliance...")
    
    sample_content = """
    Welcome to ActiveLog - your comprehensive activity tracking platform.
    Track your fishing trips, manage business expenses, and organize your digital life.
    Our platform helps you stay organized and productive.
    """
    
    compliance_result = await adsense.check_compliance(sample_content, "/dashboard")
    print(f"✅ Compliance check: {compliance_result['overall_status']}")
    print(f"   Content score: {compliance_result['content_compliance']['compliance_score']}/100")
    
    # Test 4: Generate revenue report
    print("\n4. Generating revenue report...")
    
    revenue_report = await adsense.get_revenue_report(30)
    print(f"✅ Revenue report: ${revenue_report['summary']['total_revenue']} over 30 days")
    print(f"   Total impressions: {revenue_report['summary']['total_impressions']:,}")
    print(f"   Overall CTR: {revenue_report['summary']['overall_ctr']}%")
    print(f"   Overall RPM: ${revenue_report['summary']['overall_rpm']}")
    
    # Test 5: Display ad codes
    print("\n5. Generated ad codes:")
    print("Header Banner Code:")
    print(header_unit['ad_code'][:100] + "...")
    
    # Test 6: Performance analysis
    print("\n6. Performance analysis summary:")
    if 'analysis' in optimization_result['optimization_cycle']:
        analysis = optimization_result['optimization_cycle']['analysis']
        if 'summary' in analysis:
            summary = analysis['summary']
            print(f"   Total ad units analyzed: {summary['total_ad_units']}")
            print(f"   Total revenue: ${summary['total_revenue']}")
            print(f"   Overall performance: {summary['average_performance']}")
    
    # Cleanup
    await adsense.api.close()
    
    print("\n🎉 AdSense Integration tests completed!")

if __name__ == "__main__":
    asyncio.run(main())