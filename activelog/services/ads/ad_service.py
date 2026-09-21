"""
Ad Service - Main orchestrator for the ActiveLog advertising system.
Integrates ad management, AdSense, affiliate links, and revenue tracking.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

# Import our ad components
from core.ad_manager import AdManager, UserTier, UserAdPreferences
from integrations.adsense_integration import AdSenseIntegration, AdSenseAccount
from affiliate.affiliate_manager import AffiliateManager, AffiliateNetwork

@dataclass
class AdServiceConfig:
    """Ad service configuration."""
    adsense_enabled: bool = True
    affiliate_enabled: bool = True
    frequency_optimization: bool = True
    compliance_monitoring: bool = True
    revenue_tracking: bool = True
    debug_mode: bool = False

class AdService:
    """Main advertising service for ActiveLog."""
    
    def __init__(self, config: AdServiceConfig = None):
        self.config = config or AdServiceConfig()
        
        # Initialize components
        self.ad_manager = AdManager()
        self.adsense_integration = None
        self.affiliate_manager = AffiliateManager()
        
        # Service state
        self.is_initialized = False
        self.daily_stats = {}
        
        print("📊 ActiveLog Ad Service initialized")
    
    async def initialize(self):
        """Initialize the ad service and all components."""
        if self.is_initialized:
            return
        
        print("🚀 Initializing Ad Service components...")
        
        # Initialize AdSense if enabled
        if self.config.adsense_enabled:
            adsense_account = AdSenseAccount(
                client_id="ca-pub-1234567890123456",
                publisher_id="pub-1234567890123456",
                api_key="mock_adsense_api_key",
                account_id="accounts/pub-1234567890123456"
            )
            
            self.adsense_integration = AdSenseIntegration(adsense_account)
            await self.adsense_integration.initialize()
            print("✅ AdSense integration initialized")
        
        # Set up default user tiers and preferences
        await self._setup_default_configurations()
        
        self.is_initialized = True
        print("✅ Ad Service fully initialized")
    
    async def _setup_default_configurations(self):
        """Set up default ad configurations."""
        # Set up some example user preferences
        default_users = [
            ("free_user_1", 2, False, UserTier.FREE),
            ("free_user_2", 1, False, UserTier.FREE),
            ("premium_user", 1, True, UserTier.PREMIUM),
            ("enterprise_user", 0, True, UserTier.ENTERPRISE)
        ]
        
        for user_id, banner_count, ad_free, tier in default_users:
            await self.ad_manager.set_user_preferences(
                user_id, banner_count, ad_free
            )
    
    async def get_page_ads(self, user_id: str, page_path: str, user_tier: UserTier,
                          page_type: str = "dashboard", is_mobile: bool = False,
                          usage_hours_today: float = 0) -> Dict[str, Any]:
        """Get all ads for a page (AdSense + Affiliate recommendations)."""
        if not self.is_initialized:
            await self.initialize()
        
        result = {
            "user_id": user_id,
            "page_path": page_path,
            "adsense_ads": [],
            "affiliate_recommendations": [],
            "total_ads": 0,
            "estimated_revenue": 0.0,
            "ad_free_user": user_tier == UserTier.ENTERPRISE
        }
        
        try:
            # Get AdSense ads
            adsense_ads = await self.ad_manager.get_ads_for_page(
                user_id, page_path, user_tier, page_type, is_mobile, usage_hours_today
            )
            result["adsense_ads"] = adsense_ads
            
            # Get affiliate recommendations if not ad-free
            if user_tier != UserTier.ENTERPRISE:
                module = self._extract_module_from_path(page_path)
                context = self._determine_context(page_path, page_type)
                
                affiliate_recs = await self.affiliate_manager.get_smart_recommendations(
                    user_id, module, context
                )
                result["affiliate_recommendations"] = affiliate_recs
            
            # Calculate totals
            result["total_ads"] = len(adsense_ads) + len(result["affiliate_recommendations"])
            result["estimated_revenue"] = sum(
                ad.get("estimated_revenue", 0) for ad in adsense_ads
            ) + sum(
                rec.get("commission_potential", 0) for rec in result["affiliate_recommendations"]
            )
            
            # Update daily stats
            await self._update_daily_stats(user_id, result["total_ads"], result["estimated_revenue"])
            
        except Exception as e:
            result["error"] = f"Error getting ads: {str(e)}"
            if self.config.debug_mode:
                print(f"❌ Error in get_page_ads: {e}")
        
        return result
    
    def _extract_module_from_path(self, page_path: str) -> str:
        """Extract module name from page path."""
        if "/modules/" in page_path:
            parts = page_path.split("/modules/")
            if len(parts) > 1:
                return parts[1].split("/")[0]
        
        # Default mappings
        path_module_map = {
            "/fishing": "fishing",
            "/business": "business",
            "/study": "study",
            "/player": "player",
            "/real": "real",
            "/maker": "maker",
            "/marine": "marine",
            "/dm": "dm"
        }
        
        for path, module in path_module_map.items():
            if path in page_path:
                return module
        
        return "general"
    
    def _determine_context(self, page_path: str, page_type: str) -> str:
        """Determine context for affiliate recommendations."""
        # Context based on page content
        if "receipt" in page_path or "expense" in page_path:
            return "expense_tracking"
        elif "fishing" in page_path or "trip" in page_path:
            return "fishing_trip"
        elif "study" in page_path or "assignment" in page_path:
            return "study_session"
        elif "gaming" in page_path or "stream" in page_path:
            return "gaming_stream"
        elif "video" in page_path or "edit" in page_path:
            return "video_editing"
        else:
            return "general"
    
    async def _update_daily_stats(self, user_id: str, ad_count: int, estimated_revenue: float):
        """Update daily statistics."""
        today = datetime.now().date()
        
        if today not in self.daily_stats:
            self.daily_stats[today] = {
                "unique_users": set(),
                "total_ads_served": 0,
                "estimated_revenue": 0.0,
                "user_breakdown": {}
            }
        
        daily = self.daily_stats[today]
        daily["unique_users"].add(user_id)
        daily["total_ads_served"] += ad_count
        daily["estimated_revenue"] += estimated_revenue
        
        if user_id not in daily["user_breakdown"]:
            daily["user_breakdown"][user_id] = {"ads": 0, "revenue": 0.0}
        
        daily["user_breakdown"][user_id]["ads"] += ad_count
        daily["user_breakdown"][user_id]["revenue"] += estimated_revenue
    
    async def record_ad_interaction(self, interaction_type: str, ad_unit_id: str, 
                                   user_id: str, additional_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Record ad interaction (click, conversion, etc.)."""
        try:
            if interaction_type == "click":
                # Handle both AdSense and affiliate clicks
                if additional_data and "tracking_code" in additional_data:
                    # Affiliate click
                    result = await self.affiliate_manager.record_link_click(
                        additional_data["tracking_code"], user_id
                    )
                else:
                    # AdSense click
                    result = await self.ad_manager.record_ad_click(ad_unit_id, user_id)
                
            elif interaction_type == "conversion":
                # Handle conversions
                conversion_value = additional_data.get("conversion_value", 0.0) if additional_data else 0.0
                
                if additional_data and "tracking_code" in additional_data:
                    # Affiliate conversion
                    result = await self.affiliate_manager.record_commission(
                        additional_data["tracking_code"], 
                        conversion_value,
                        additional_data.get("commission_rate")
                    )
                else:
                    # AdSense conversion
                    result = await self.ad_manager.record_ad_conversion(
                        ad_unit_id, user_id, conversion_value
                    )
            
            else:
                result = {"error": f"Unknown interaction type: {interaction_type}"}
            
            return result
            
        except Exception as e:
            return {"error": f"Error recording interaction: {str(e)}"}
    
    async def update_user_ad_preferences(self, user_id: str, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Update user ad preferences."""
        try:
            banner_count = preferences.get("banner_count", 1)
            ad_free_enabled = preferences.get("ad_free_enabled", False)
            targeted_ads = preferences.get("targeted_ads", True)
            
            await self.ad_manager.set_user_preferences(
                user_id, banner_count, ad_free_enabled, targeted_ads
            )
            
            return {
                "success": True,
                "user_id": user_id,
                "updated_preferences": preferences,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"error": f"Error updating preferences: {str(e)}"}
    
    async def get_user_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive user ad analytics."""
        try:
            # Get AdSense analytics
            adsense_analytics = await self.ad_manager.get_user_ad_analytics(user_id)
            
            # Get affiliate analytics
            affiliate_analytics = await self.affiliate_manager.get_performance_analytics(user_id=user_id)
            
            # Combine analytics
            combined_analytics = {
                "user_id": user_id,
                "adsense": adsense_analytics,
                "affiliate": affiliate_analytics,
                "combined_metrics": {
                    "total_revenue": (
                        adsense_analytics.get("total_lifetime_revenue", 0) + 
                        affiliate_analytics.get("summary", {}).get("total_revenue", 0)
                    ),
                    "total_clicks": (
                        adsense_analytics.get("revenue_stats", {}).get("clicks", 0) + 
                        affiliate_analytics.get("click_stats", {}).get("total_clicks", 0)
                    ),
                    "total_impressions": adsense_analytics.get("revenue_stats", {}).get("impressions", 0)
                },
                "generated_at": datetime.now().isoformat()
            }
            
            return combined_analytics
            
        except Exception as e:
            return {"error": f"Error getting analytics: {str(e)}"}
    
    async def get_revenue_summary(self, start_date: Optional[datetime] = None,
                                 end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get comprehensive revenue summary."""
        try:
            # Get AdSense revenue
            adsense_summary = await self.ad_manager.get_revenue_summary(start_date, end_date)
            
            # Get affiliate revenue
            days = 30
            if start_date and end_date:
                days = (end_date - start_date).days
            
            affiliate_summary = await self.affiliate_manager.get_performance_analytics(days=days)
            
            # Combine summaries
            combined_summary = {
                "period": adsense_summary.get("period", {}),
                "adsense_revenue": adsense_summary,
                "affiliate_revenue": affiliate_summary,
                "total_revenue": (
                    adsense_summary.get("total_revenue", 0) + 
                    affiliate_summary.get("summary", {}).get("total_revenue", 0)
                ),
                "revenue_breakdown": {
                    "adsense_percentage": 0,
                    "affiliate_percentage": 0
                },
                "generated_at": datetime.now().isoformat()
            }
            
            # Calculate percentages
            total = combined_summary["total_revenue"]
            if total > 0:
                combined_summary["revenue_breakdown"]["adsense_percentage"] = round(
                    (adsense_summary.get("total_revenue", 0) / total) * 100, 1
                )
                combined_summary["revenue_breakdown"]["affiliate_percentage"] = round(
                    (affiliate_summary.get("summary", {}).get("total_revenue", 0) / total) * 100, 1
                )
            
            return combined_summary
            
        except Exception as e:
            return {"error": f"Error getting revenue summary: {str(e)}"}
    
    async def run_optimization_cycle(self) -> Dict[str, Any]:
        """Run comprehensive optimization cycle."""
        try:
            optimization_results = {
                "cycle_start": datetime.now().isoformat(),
                "adsense_optimization": {},
                "affiliate_optimization": {},
                "overall_recommendations": []
            }
            
            # Run AdSense optimization
            if self.adsense_integration:
                adsense_opt = await self.adsense_integration.run_optimization_cycle()
                optimization_results["adsense_optimization"] = adsense_opt
            
            # Run affiliate optimization
            affiliate_opt = await self.affiliate_manager.optimize_affiliate_strategy()
            optimization_results["affiliate_optimization"] = affiliate_opt
            
            # Generate overall recommendations
            overall_recs = await self._generate_overall_recommendations(
                optimization_results["adsense_optimization"],
                optimization_results["affiliate_optimization"]
            )
            optimization_results["overall_recommendations"] = overall_recs
            
            optimization_results["cycle_end"] = datetime.now().isoformat()
            
            return optimization_results
            
        except Exception as e:
            return {"error": f"Error in optimization cycle: {str(e)}"}
    
    async def _generate_overall_recommendations(self, adsense_opt: Dict, affiliate_opt: Dict) -> List[Dict[str, Any]]:
        """Generate overall optimization recommendations."""
        recommendations = []
        
        # Analyze revenue balance
        if adsense_opt and affiliate_opt:
            adsense_revenue = adsense_opt.get("optimization_cycle", {}).get("analysis", {}).get("summary", {}).get("total_revenue", 0)
            affiliate_revenue = affiliate_opt.get("optimization_analysis", {}).get("key_metrics", {}).get("total_revenue", 0)
            
            total_revenue = adsense_revenue + affiliate_revenue
            
            if total_revenue > 0:
                adsense_percentage = (adsense_revenue / total_revenue) * 100
                
                if adsense_percentage > 80:
                    recommendations.append({
                        "type": "revenue_diversification",
                        "priority": "medium",
                        "recommendation": "Consider increasing affiliate marketing efforts to diversify revenue streams",
                        "current_split": f"{adsense_percentage:.1f}% AdSense, {100-adsense_percentage:.1f}% Affiliate"
                    })
                elif adsense_percentage < 20:
                    recommendations.append({
                        "type": "adsense_optimization",
                        "priority": "medium", 
                        "recommendation": "AdSense revenue is low compared to affiliate. Review ad placements and optimization",
                        "current_split": f"{adsense_percentage:.1f}% AdSense, {100-adsense_percentage:.1f}% Affiliate"
                    })
        
        # Check daily stats for patterns
        if self.daily_stats:
            recent_days = list(self.daily_stats.keys())[-7:]  # Last 7 days
            avg_daily_revenue = sum(
                self.daily_stats[day]["estimated_revenue"] for day in recent_days
            ) / len(recent_days) if recent_days else 0
            
            if avg_daily_revenue < 5.0:  # Less than $5 per day
                recommendations.append({
                    "type": "revenue_growth",
                    "priority": "high",
                    "recommendation": "Daily revenue is below target. Consider increasing ad frequency or improving targeting",
                    "current_daily_average": round(avg_daily_revenue, 2)
                })
        
        return recommendations
    
    async def get_service_health(self) -> Dict[str, Any]:
        """Get comprehensive service health status."""
        health = {
            "service_status": "healthy",
            "initialized": self.is_initialized,
            "components": {
                "ad_manager": "healthy",
                "adsense_integration": "healthy" if self.adsense_integration else "disabled",
                "affiliate_manager": "healthy"
            },
            "daily_stats": {},
            "configuration": asdict(self.config),
            "last_check": datetime.now().isoformat()
        }
        
        # Add daily stats summary
        if self.daily_stats:
            today = datetime.now().date()
            if today in self.daily_stats:
                today_stats = self.daily_stats[today]
                health["daily_stats"] = {
                    "unique_users_today": len(today_stats["unique_users"]),
                    "total_ads_served_today": today_stats["total_ads_served"],
                    "estimated_revenue_today": round(today_stats["estimated_revenue"], 2)
                }
        
        return health
    
    async def check_compliance(self, page_content: str, page_url: str) -> Dict[str, Any]:
        """Check advertising compliance for a page."""
        if not self.adsense_integration:
            return {"error": "AdSense integration not available"}
        
        try:
            compliance_result = await self.adsense_integration.check_compliance(page_content, page_url)
            return compliance_result
        except Exception as e:
            return {"error": f"Error checking compliance: {str(e)}"}

# CLI interface for testing
async def main():
    """CLI interface for Ad Service testing."""
    
    # Initialize ad service
    config = AdServiceConfig(
        adsense_enabled=True,
        affiliate_enabled=True,
        frequency_optimization=True,
        debug_mode=True
    )
    
    ad_service = AdService(config)
    await ad_service.initialize()
    
    print("📊 Ad Service Test Suite")
    print("=" * 50)
    
    # Test 1: Get ads for different pages and users
    print("\n1. Getting ads for different pages...")
    
    # Free user on dashboard
    dashboard_ads = await ad_service.get_page_ads(
        "free_user_1", "/dashboard", UserTier.FREE, "dashboard", usage_hours_today=3.5
    )
    print(f"✅ Dashboard ads (free user): {dashboard_ads['total_ads']} ads, ${dashboard_ads['estimated_revenue']:.3f} estimated revenue")
    
    # Premium user on fishing module
    fishing_ads = await ad_service.get_page_ads(
        "premium_user", "/modules/fishing", UserTier.PREMIUM, "module"
    )
    print(f"✅ Fishing module ads (premium): {fishing_ads['total_ads']} ads")
    
    # Enterprise user (should get no ads)
    enterprise_ads = await ad_service.get_page_ads(
        "enterprise_user", "/dashboard", UserTier.ENTERPRISE, "dashboard"
    )
    print(f"✅ Enterprise user ads: {enterprise_ads['total_ads']} ads (should be 0)")
    
    # Mobile user
    mobile_ads = await ad_service.get_page_ads(
        "free_user_2", "/modules/business", UserTier.FREE, "module", is_mobile=True
    )
    print(f"✅ Mobile ads: {mobile_ads['total_ads']} ads")
    
    # Test 2: Record interactions
    print("\n2. Recording ad interactions...")
    
    if dashboard_ads["adsense_ads"]:
        ad_unit_id = dashboard_ads["adsense_ads"][0]["ad_unit_id"]
        
        # Record click
        click_result = await ad_service.record_ad_interaction(
            "click", ad_unit_id, "free_user_1"
        )
        print(f"✅ AdSense click recorded: {click_result.get('success', False)}")
        
        # Record conversion
        conversion_result = await ad_service.record_ad_interaction(
            "conversion", ad_unit_id, "free_user_1", {"conversion_value": 89.99}
        )
        print(f"✅ AdSense conversion recorded: ${conversion_result.get('click_bonus', 0):.2f}")
    
    if dashboard_ads["affiliate_recommendations"]:
        tracking_code = dashboard_ads["affiliate_recommendations"][0].get("tracking_code")
        if tracking_code:
            # Record affiliate click
            affiliate_click = await ad_service.record_ad_interaction(
                "click", "", "free_user_1", {"tracking_code": tracking_code}
            )
            print(f"✅ Affiliate click recorded: {affiliate_click.get('success', False)}")
    
    # Test 3: Update user preferences
    print("\n3. Updating user preferences...")
    
    prefs_update = await ad_service.update_user_ad_preferences(
        "free_user_1",
        {"banner_count": 1, "ad_free_enabled": False, "targeted_ads": True}
    )
    print(f"✅ Preferences updated: {prefs_update.get('success', False)}")
    
    # Test 4: Get user analytics
    print("\n4. Getting user analytics...")
    
    user_analytics = await ad_service.get_user_analytics("free_user_1")
    if "error" not in user_analytics:
        combined_metrics = user_analytics["combined_metrics"]
        print(f"✅ User analytics: ${combined_metrics['total_revenue']:.4f} total revenue, {combined_metrics['total_clicks']} clicks")
    else:
        print(f"⚠️ Analytics error: {user_analytics['error']}")
    
    # Test 5: Revenue summary
    print("\n5. Getting revenue summary...")
    
    revenue_summary = await ad_service.get_revenue_summary()
    if "error" not in revenue_summary:
        print(f"✅ Revenue summary: ${revenue_summary['total_revenue']:.2f} total")
        print(f"   AdSense: {revenue_summary['revenue_breakdown']['adsense_percentage']}%")
        print(f"   Affiliate: {revenue_summary['revenue_breakdown']['affiliate_percentage']}%")
    else:
        print(f"⚠️ Revenue summary error: {revenue_summary['error']}")
    
    # Test 6: Optimization cycle
    print("\n6. Running optimization cycle...")
    
    optimization = await ad_service.run_optimization_cycle()
    if "error" not in optimization:
        print(f"✅ Optimization completed: {len(optimization['overall_recommendations'])} recommendations")
        for rec in optimization['overall_recommendations']:
            print(f"   - {rec['recommendation']} (Priority: {rec['priority']})")
    else:
        print(f"⚠️ Optimization error: {optimization['error']}")
    
    # Test 7: Service health
    print("\n7. Checking service health...")
    
    health = await ad_service.get_service_health()
    print(f"✅ Service health: {health['service_status']}")
    print(f"   Components: {health['components']}")
    if health.get("daily_stats"):
        stats = health["daily_stats"]
        print(f"   Today: {stats['unique_users_today']} users, {stats['total_ads_served_today']} ads, ${stats['estimated_revenue_today']:.2f}")
    
    # Test 8: Compliance check
    print("\n8. Checking compliance...")
    
    sample_content = """
    Welcome to ActiveLog - track your activities and stay organized.
    Our platform helps you manage fishing trips, business expenses, and more.
    """
    
    compliance = await ad_service.check_compliance(sample_content, "/dashboard")
    if "error" not in compliance:
        print(f"✅ Compliance check: {compliance['overall_status']}")
        print(f"   Content score: {compliance['content_compliance']['compliance_score']}/100")
    else:
        print(f"⚠️ Compliance error: {compliance['error']}")
    
    print("\n🎉 Ad Service tests completed!")

if __name__ == "__main__":
    asyncio.run(main())