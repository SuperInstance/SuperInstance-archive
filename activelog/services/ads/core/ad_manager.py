"""
Ad Manager - Core ad serving system for ActiveLog.
Manages ad placement, frequency, user preferences, and revenue tracking.
"""

import asyncio
import json
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import random

class AdType(Enum):
    BANNER = "banner"
    LEADERBOARD = "leaderboard"
    RECTANGLE = "rectangle"
    SKYSCRAPER = "skyscraper"
    MOBILE_BANNER = "mobile_banner"
    NATIVE = "native"
    VIDEO = "video"
    INTERSTITIAL = "interstitial"

class AdProvider(Enum):
    GOOGLE_ADSENSE = "google_adsense"
    AMAZON_ASSOCIATES = "amazon_associates"
    INTERNAL = "internal"
    AFFILIATE = "affiliate"

class UserTier(Enum):
    FREE = "free"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

@dataclass
class AdSlot:
    """Ad slot configuration."""
    id: str
    name: str
    ad_type: AdType
    dimensions: Tuple[int, int]  # width, height
    provider: AdProvider
    placement: str  # header, sidebar, footer, content
    enabled: bool = True
    min_user_tier: UserTier = UserTier.FREE

@dataclass
class AdImpression:
    """Ad impression tracking data."""
    id: str
    user_id: str
    ad_slot_id: str
    ad_unit_id: str
    provider: AdProvider
    timestamp: datetime
    revenue: float = 0.0
    clicked: bool = False
    converted: bool = False
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None

@dataclass
class UserAdPreferences:
    """User ad preferences and settings."""
    user_id: str
    banner_count: int = 1  # 1 or 2 banners
    ad_free_enabled: bool = False
    targeted_ads: bool = True
    frequency_cap: int = 5  # max ads per hour
    blocked_categories: List[str] = None
    last_updated: datetime = None

@dataclass
class RevenueData:
    """Revenue tracking data."""
    user_id: str
    date: datetime
    impressions: int
    clicks: int
    conversions: int
    revenue: float
    provider: AdProvider

class AdFrequencyManager:
    """Manages ad frequency capping and optimization."""
    
    def __init__(self):
        self.user_impressions = {}  # user_id -> [timestamps]
        self.frequency_caps = {
            UserTier.FREE: 8,      # 8 ads per hour for free users
            UserTier.PREMIUM: 3,   # 3 ads per hour for premium
            UserTier.ENTERPRISE: 0 # no ads for enterprise
        }
    
    async def can_show_ad(self, user_id: str, user_tier: UserTier) -> bool:
        """Check if we can show an ad to the user based on frequency limits."""
        if user_tier == UserTier.ENTERPRISE:
            return False
        
        current_time = datetime.now()
        hour_ago = current_time - timedelta(hours=1)
        
        # Get user impressions in the last hour
        if user_id not in self.user_impressions:
            self.user_impressions[user_id] = []
        
        # Clean old impressions
        self.user_impressions[user_id] = [
            timestamp for timestamp in self.user_impressions[user_id]
            if timestamp > hour_ago
        ]
        
        # Check frequency cap
        impressions_last_hour = len(self.user_impressions[user_id])
        max_impressions = self.frequency_caps.get(user_tier, 5)
        
        return impressions_last_hour < max_impressions
    
    async def record_impression(self, user_id: str) -> None:
        """Record an ad impression for frequency tracking."""
        if user_id not in self.user_impressions:
            self.user_impressions[user_id] = []
        
        self.user_impressions[user_id].append(datetime.now())
    
    async def get_optimal_frequency(self, user_id: str, usage_hours_today: float) -> int:
        """Calculate optimal ad frequency based on user activity."""
        base_frequency = 5
        
        # Adjust based on usage
        if usage_hours_today > 8:
            return min(base_frequency + 3, 10)  # More active users see more ads
        elif usage_hours_today > 4:
            return base_frequency
        else:
            return max(base_frequency - 2, 2)  # Less active users see fewer ads

class AdPlacementEngine:
    """Intelligent ad placement system."""
    
    def __init__(self):
        self.ad_slots = self._initialize_ad_slots()
        self.placement_rules = self._load_placement_rules()
    
    def _initialize_ad_slots(self) -> Dict[str, AdSlot]:
        """Initialize available ad slots."""
        slots = {
            'header_banner': AdSlot(
                id='header_banner',
                name='Header Banner',
                ad_type=AdType.LEADERBOARD,
                dimensions=(728, 90),
                provider=AdProvider.GOOGLE_ADSENSE,
                placement='header'
            ),
            'sidebar_banner': AdSlot(
                id='sidebar_banner',
                name='Sidebar Banner',
                ad_type=AdType.SKYSCRAPER,
                dimensions=(160, 600),
                provider=AdProvider.GOOGLE_ADSENSE,
                placement='sidebar'
            ),
            'content_rectangle': AdSlot(
                id='content_rectangle',
                name='Content Rectangle',
                ad_type=AdType.RECTANGLE,
                dimensions=(300, 250),
                provider=AdProvider.GOOGLE_ADSENSE,
                placement='content'
            ),
            'footer_banner': AdSlot(
                id='footer_banner',
                name='Footer Banner',
                ad_type=AdType.BANNER,
                dimensions=(728, 90),
                provider=AdProvider.GOOGLE_ADSENSE,
                placement='footer'
            ),
            'mobile_banner': AdSlot(
                id='mobile_banner',
                name='Mobile Banner',
                ad_type=AdType.MOBILE_BANNER,
                dimensions=(320, 50),
                provider=AdProvider.GOOGLE_ADSENSE,
                placement='mobile_header'
            ),
            'affiliate_sidebar': AdSlot(
                id='affiliate_sidebar',
                name='Affiliate Sidebar',
                ad_type=AdType.NATIVE,
                dimensions=(300, 400),
                provider=AdProvider.AFFILIATE,
                placement='sidebar'
            )
        }
        
        return slots
    
    def _load_placement_rules(self) -> Dict[str, Any]:
        """Load ad placement rules and priorities."""
        return {
            'page_types': {
                'dashboard': ['header_banner', 'sidebar_banner'],
                'module': ['content_rectangle', 'footer_banner'],
                'settings': ['sidebar_banner'],
                'mobile': ['mobile_banner']
            },
            'user_preferences': {
                1: ['header_banner'],  # 1 banner preference
                2: ['header_banner', 'sidebar_banner']  # 2 banner preference
            },
            'high_value_pages': [
                '/dashboard',
                '/modules/fishing',
                '/modules/business',
                '/modules/study'
            ]
        }
    
    async def select_ad_slots(self, user_id: str, page_type: str, 
                             user_preferences: UserAdPreferences,
                             is_mobile: bool = False) -> List[AdSlot]:
        """Select appropriate ad slots for the user and page."""
        if user_preferences.ad_free_enabled:
            return []
        
        available_slots = []
        
        # Get slots based on page type
        if is_mobile:
            page_slots = self.placement_rules['page_types'].get('mobile', [])
        else:
            page_slots = self.placement_rules['page_types'].get(page_type, [])
        
        # Apply user banner count preference
        preference_slots = self.placement_rules['user_preferences'].get(
            user_preferences.banner_count, []
        )
        
        # Combine and prioritize
        slot_ids = list(set(page_slots) & set(preference_slots))
        
        for slot_id in slot_ids:
            if slot_id in self.ad_slots:
                slot = self.ad_slots[slot_id]
                if slot.enabled:
                    available_slots.append(slot)
        
        # Limit based on user preferences
        return available_slots[:user_preferences.banner_count]

class RevenueTracker:
    """Revenue tracking and analytics system."""
    
    def __init__(self):
        self.revenue_data = []
        self.user_revenue = {}  # user_id -> total_revenue
        self.provider_rates = {
            AdProvider.GOOGLE_ADSENSE: 0.0015,  # $1.50 per 1000 impressions
            AdProvider.AMAZON_ASSOCIATES: 0.002,  # $2.00 per 1000 impressions
            AdProvider.AFFILIATE: 0.005,  # $5.00 per 1000 impressions
            AdProvider.INTERNAL: 0.001   # $1.00 per 1000 impressions
        }
    
    async def calculate_impression_revenue(self, impression: AdImpression) -> float:
        """Calculate revenue for a single impression."""
        base_rate = self.provider_rates.get(impression.provider, 0.001)
        
        # Apply multipliers based on various factors
        multiplier = 1.0
        
        # Time-based multiplier (higher rates during peak hours)
        hour = impression.timestamp.hour
        if 9 <= hour <= 17:  # Business hours
            multiplier *= 1.2
        elif 19 <= hour <= 22:  # Evening peak
            multiplier *= 1.1
        
        # Click bonus
        if impression.clicked:
            multiplier *= 25  # Typical CTR bonus
        
        # Conversion bonus
        if impression.converted:
            multiplier *= 100  # Conversion bonus
        
        revenue = base_rate * multiplier
        
        # Update tracking
        await self._update_revenue_tracking(impression.user_id, revenue, impression.provider)
        
        return revenue
    
    async def _update_revenue_tracking(self, user_id: str, revenue: float, provider: AdProvider):
        """Update revenue tracking data."""
        if user_id not in self.user_revenue:
            self.user_revenue[user_id] = 0.0
        
        self.user_revenue[user_id] += revenue
        
        # Add to daily revenue data
        today = datetime.now().date()
        existing_record = next(
            (r for r in self.revenue_data 
             if r.user_id == user_id and r.date.date() == today and r.provider == provider),
            None
        )
        
        if existing_record:
            existing_record.revenue += revenue
            existing_record.impressions += 1
        else:
            self.revenue_data.append(RevenueData(
                user_id=user_id,
                date=datetime.now(),
                impressions=1,
                clicks=0,
                conversions=0,
                revenue=revenue,
                provider=provider
            ))
    
    async def get_user_revenue_stats(self, user_id: str) -> Dict[str, Any]:
        """Get revenue statistics for a specific user."""
        user_records = [r for r in self.revenue_data if r.user_id == user_id]
        
        if not user_records:
            return {
                "user_id": user_id,
                "total_revenue": 0.0,
                "impressions": 0,
                "clicks": 0,
                "average_cpm": 0.0
            }
        
        total_revenue = sum(r.revenue for r in user_records)
        total_impressions = sum(r.impressions for r in user_records)
        total_clicks = sum(r.clicks for r in user_records)
        
        average_cpm = (total_revenue / total_impressions * 1000) if total_impressions > 0 else 0
        
        return {
            "user_id": user_id,
            "total_revenue": round(total_revenue, 4),
            "impressions": total_impressions,
            "clicks": total_clicks,
            "ctr": round((total_clicks / total_impressions * 100) if total_impressions > 0 else 0, 2),
            "average_cpm": round(average_cpm, 2),
            "revenue_by_provider": self._get_revenue_by_provider(user_records)
        }
    
    def _get_revenue_by_provider(self, records: List[RevenueData]) -> Dict[str, float]:
        """Calculate revenue breakdown by provider."""
        provider_revenue = {}
        for record in records:
            provider_key = record.provider.value
            provider_revenue[provider_key] = provider_revenue.get(provider_key, 0) + record.revenue
        
        return {k: round(v, 4) for k, v in provider_revenue.items()}

class AdManager:
    """Main ad management system orchestrator."""
    
    def __init__(self):
        self.frequency_manager = AdFrequencyManager()
        self.placement_engine = AdPlacementEngine()
        self.revenue_tracker = RevenueTracker()
        self.user_preferences = {}  # user_id -> UserAdPreferences
        self.ad_zones = self._define_ad_zones()
        
        print("📊 Ad Manager initialized")
    
    def _define_ad_zones(self) -> Dict[str, Dict[str, Any]]:
        """Define ad-free zones and special ad handling."""
        return {
            'ad_free_zones': {
                'payment_pages': ['/billing', '/payment', '/checkout'],
                'user_privacy': ['/privacy', '/data-export', '/account-delete'],
                'admin_areas': ['/admin', '/system', '/diagnostics'],
                'premium_features': ['/premium/', '/enterprise/']
            },
            'reduced_ad_zones': {
                'onboarding': ['/welcome', '/setup', '/tutorial'],
                'support': ['/help', '/support', '/contact']
            }
        }
    
    async def set_user_preferences(self, user_id: str, banner_count: int = 1, 
                                  ad_free_enabled: bool = False,
                                  targeted_ads: bool = True) -> None:
        """Set user ad preferences."""
        if banner_count not in [1, 2]:
            banner_count = 1
        
        self.user_preferences[user_id] = UserAdPreferences(
            user_id=user_id,
            banner_count=banner_count,
            ad_free_enabled=ad_free_enabled,
            targeted_ads=targeted_ads,
            frequency_cap=5,
            blocked_categories=[],
            last_updated=datetime.now()
        )
        
        print(f"👤 Updated ad preferences for {user_id}: {banner_count} banners, ad-free: {ad_free_enabled}")
    
    async def get_ads_for_page(self, user_id: str, page_path: str, user_tier: UserTier,
                              page_type: str = "dashboard", is_mobile: bool = False,
                              usage_hours_today: float = 0) -> List[Dict[str, Any]]:
        """Get ads to display for a specific page and user."""
        
        # Check if page is in ad-free zone
        if self._is_ad_free_zone(page_path):
            return []
        
        # Check user tier and ad-free status
        if user_tier == UserTier.ENTERPRISE:
            return []
        
        user_prefs = self.user_preferences.get(user_id, UserAdPreferences(user_id=user_id))
        if user_prefs.ad_free_enabled:
            return []
        
        # Check frequency limits
        can_show = await self.frequency_manager.can_show_ad(user_id, user_tier)
        if not can_show:
            return []
        
        # Get appropriate ad slots
        ad_slots = await self.placement_engine.select_ad_slots(
            user_id, page_type, user_prefs, is_mobile
        )
        
        # Generate ad configurations
        ads = []
        for slot in ad_slots:
            ad_config = await self._generate_ad_config(slot, user_id, user_prefs)
            if ad_config:
                ads.append(ad_config)
                # Record impression
                await self.frequency_manager.record_impression(user_id)
        
        return ads
    
    def _is_ad_free_zone(self, page_path: str) -> bool:
        """Check if the page is in an ad-free zone."""
        for zone_paths in self.ad_zones['ad_free_zones'].values():
            for path in zone_paths:
                if page_path.startswith(path):
                    return True
        return False
    
    async def _generate_ad_config(self, slot: AdSlot, user_id: str, 
                                 user_prefs: UserAdPreferences) -> Dict[str, Any]:
        """Generate ad configuration for a specific slot."""
        ad_unit_id = f"ad_{slot.id}_{user_id}_{int(datetime.now().timestamp())}"
        
        # Create impression record
        impression = AdImpression(
            id=ad_unit_id,
            user_id=user_id,
            ad_slot_id=slot.id,
            ad_unit_id=ad_unit_id,
            provider=slot.provider,
            timestamp=datetime.now()
        )
        
        # Calculate potential revenue
        revenue = await self.revenue_tracker.calculate_impression_revenue(impression)
        impression.revenue = revenue
        
        return {
            'ad_unit_id': ad_unit_id,
            'slot_id': slot.id,
            'slot_name': slot.name,
            'ad_type': slot.ad_type.value,
            'dimensions': {
                'width': slot.dimensions[0],
                'height': slot.dimensions[1]
            },
            'placement': slot.placement,
            'provider': slot.provider.value,
            'targeting_enabled': user_prefs.targeted_ads,
            'estimated_revenue': revenue,
            'config': self._get_provider_config(slot.provider, slot, user_prefs)
        }
    
    def _get_provider_config(self, provider: AdProvider, slot: AdSlot, 
                           user_prefs: UserAdPreferences) -> Dict[str, Any]:
        """Get provider-specific configuration."""
        if provider == AdProvider.GOOGLE_ADSENSE:
            return {
                'data_ad_client': 'ca-pub-1234567890123456',  # Mock AdSense client ID
                'data_ad_slot': f'slot_{slot.id}',
                'data_ad_format': 'auto',
                'data_full_width_responsive': 'true',
                'data_npa': '0' if user_prefs.targeted_ads else '1'
            }
        elif provider == AdProvider.AMAZON_ASSOCIATES:
            return {
                'associate_id': 'activelog-20',
                'ad_type': 'banner',
                'marketplace': 'amazon',
                'region': 'US',
                'placement': slot.placement,
                'tracking_id': f'al_{slot.id}'
            }
        elif provider == AdProvider.AFFILIATE:
            return {
                'affiliate_network': 'various',
                'content_type': 'contextual',
                'placement': slot.placement
            }
        else:
            return {}
    
    async def record_ad_click(self, ad_unit_id: str, user_id: str) -> Dict[str, Any]:
        """Record an ad click event."""
        # Find the impression
        impression_found = False
        for record in self.revenue_tracker.revenue_data:
            if record.user_id == user_id:
                record.clicks += 1
                impression_found = True
                break
        
        if impression_found:
            # Calculate click revenue bonus
            click_bonus = 0.05  # $0.05 per click
            await self.revenue_tracker._update_revenue_tracking(
                user_id, click_bonus, AdProvider.GOOGLE_ADSENSE
            )
            
            print(f"🖱️ Ad click recorded for {user_id}: +${click_bonus}")
            
            return {
                "success": True,
                "ad_unit_id": ad_unit_id,
                "click_bonus": click_bonus,
                "timestamp": datetime.now().isoformat()
            }
        
        return {"success": False, "error": "Impression not found"}
    
    async def record_ad_conversion(self, ad_unit_id: str, user_id: str, 
                                  conversion_value: float = 0.0) -> Dict[str, Any]:
        """Record an ad conversion event."""
        # Find the impression
        impression_found = False
        for record in self.revenue_tracker.revenue_data:
            if record.user_id == user_id:
                record.conversions += 1
                impression_found = True
                break
        
        if impression_found:
            # Calculate conversion revenue bonus
            conversion_bonus = max(conversion_value * 0.1, 1.0)  # 10% of conversion or $1 minimum
            await self.revenue_tracker._update_revenue_tracking(
                user_id, conversion_bonus, AdProvider.GOOGLE_ADSENSE
            )
            
            print(f"💰 Ad conversion recorded for {user_id}: +${conversion_bonus}")
            
            return {
                "success": True,
                "ad_unit_id": ad_unit_id,
                "conversion_bonus": conversion_bonus,
                "conversion_value": conversion_value,
                "timestamp": datetime.now().isoformat()
            }
        
        return {"success": False, "error": "Impression not found"}
    
    async def get_user_ad_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive ad analytics for a user."""
        revenue_stats = await self.revenue_tracker.get_user_revenue_stats(user_id)
        user_prefs = self.user_preferences.get(user_id, UserAdPreferences(user_id=user_id))
        
        # Get recent impressions
        recent_impressions = len(self.frequency_manager.user_impressions.get(user_id, []))
        
        return {
            "user_id": user_id,
            "preferences": asdict(user_prefs),
            "revenue_stats": revenue_stats,
            "recent_impressions_hour": recent_impressions,
            "total_lifetime_revenue": self.revenue_tracker.user_revenue.get(user_id, 0.0),
            "ad_zones_active": not self._is_ad_free_user(user_id),
            "generated_at": datetime.now().isoformat()
        }
    
    def _is_ad_free_user(self, user_id: str) -> bool:
        """Check if user has ad-free access."""
        user_prefs = self.user_preferences.get(user_id)
        return user_prefs and user_prefs.ad_free_enabled
    
    async def get_revenue_summary(self, start_date: Optional[datetime] = None,
                                 end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get revenue summary for the specified period."""
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
        
        period_records = [
            r for r in self.revenue_tracker.revenue_data
            if start_date <= r.date <= end_date
        ]
        
        if not period_records:
            return {
                "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
                "total_revenue": 0.0,
                "total_impressions": 0,
                "total_clicks": 0
            }
        
        total_revenue = sum(r.revenue for r in period_records)
        total_impressions = sum(r.impressions for r in period_records)
        total_clicks = sum(r.clicks for r in period_records)
        total_conversions = sum(r.conversions for r in period_records)
        
        # Group by provider
        provider_stats = {}
        for record in period_records:
            provider = record.provider.value
            if provider not in provider_stats:
                provider_stats[provider] = {
                    "revenue": 0.0,
                    "impressions": 0,
                    "clicks": 0,
                    "conversions": 0
                }
            
            provider_stats[provider]["revenue"] += record.revenue
            provider_stats[provider]["impressions"] += record.impressions
            provider_stats[provider]["clicks"] += record.clicks
            provider_stats[provider]["conversions"] += record.conversions
        
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_revenue": round(total_revenue, 2),
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "total_conversions": total_conversions,
            "average_cpm": round((total_revenue / total_impressions * 1000) if total_impressions > 0 else 0, 2),
            "average_ctr": round((total_clicks / total_impressions * 100) if total_impressions > 0 else 0, 2),
            "conversion_rate": round((total_conversions / total_clicks * 100) if total_clicks > 0 else 0, 2),
            "provider_breakdown": provider_stats,
            "unique_users": len(set(r.user_id for r in period_records)),
            "generated_at": datetime.now().isoformat()
        }

# CLI interface for testing
async def main():
    """CLI interface for Ad Manager testing."""
    ad_manager = AdManager()
    
    print("📊 Ad Manager Test Suite")
    print("=" * 40)
    
    # Test 1: Set user preferences
    print("\n1. Setting user preferences...")
    await ad_manager.set_user_preferences("user1", banner_count=2, ad_free_enabled=False)
    await ad_manager.set_user_preferences("user2", banner_count=1, ad_free_enabled=False)
    await ad_manager.set_user_preferences("premium_user", banner_count=1, ad_free_enabled=True)
    print("✅ User preferences set")
    
    # Test 2: Get ads for different pages
    print("\n2. Getting ads for different pages...")
    
    # Dashboard page for free user
    ads_dashboard = await ad_manager.get_ads_for_page(
        "user1", "/dashboard", UserTier.FREE, "dashboard", usage_hours_today=4.5
    )
    print(f"✅ Dashboard ads for user1: {len(ads_dashboard)} ads")
    
    # Mobile page
    ads_mobile = await ad_manager.get_ads_for_page(
        "user2", "/modules/fishing", UserTier.FREE, "module", is_mobile=True
    )
    print(f"✅ Mobile ads for user2: {len(ads_mobile)} ads")
    
    # Premium user (should get no ads due to ad-free)
    ads_premium = await ad_manager.get_ads_for_page(
        "premium_user", "/dashboard", UserTier.PREMIUM, "dashboard"
    )
    print(f"✅ Premium user ads: {len(ads_premium)} ads (should be 0)")
    
    # Ad-free zone (payment page)
    ads_payment = await ad_manager.get_ads_for_page(
        "user1", "/billing/payment", UserTier.FREE, "dashboard"
    )
    print(f"✅ Payment page ads: {len(ads_payment)} ads (should be 0)")
    
    # Test 3: Simulate ad interactions
    print("\n3. Simulating ad interactions...")
    
    # Simulate some clicks and conversions
    if ads_dashboard:
        ad_unit_id = ads_dashboard[0]['ad_unit_id']
        
        # Record click
        click_result = await ad_manager.record_ad_click(ad_unit_id, "user1")
        print(f"✅ Click recorded: {click_result['success']}")
        
        # Record conversion
        conversion_result = await ad_manager.record_ad_conversion(ad_unit_id, "user1", 25.99)
        print(f"✅ Conversion recorded: {conversion_result['success']}")
    
    # Test 4: Frequency capping
    print("\n4. Testing frequency capping...")
    
    # Try to get ads multiple times quickly
    for i in range(10):
        ads = await ad_manager.get_ads_for_page(
            "user2", "/dashboard", UserTier.FREE, "dashboard"
        )
        if len(ads) == 0:
            print(f"✅ Frequency cap triggered after {i} requests")
            break
    
    # Test 5: Get user analytics
    print("\n5. Getting user analytics...")
    
    analytics_user1 = await ad_manager.get_user_ad_analytics("user1")
    print(f"✅ User1 analytics: ${analytics_user1['total_lifetime_revenue']:.4f} revenue, {analytics_user1['revenue_stats']['impressions']} impressions")
    
    analytics_premium = await ad_manager.get_user_ad_analytics("premium_user")
    print(f"✅ Premium user analytics: Ad-free = {not analytics_premium['ad_zones_active']}")
    
    # Test 6: Revenue summary
    print("\n6. Getting revenue summary...")
    
    revenue_summary = await ad_manager.get_revenue_summary()
    print(f"✅ Revenue summary: ${revenue_summary['total_revenue']} from {revenue_summary['total_impressions']} impressions")
    print(f"   Average CPM: ${revenue_summary['average_cpm']}")
    print(f"   CTR: {revenue_summary['average_ctr']}%")
    
    # Test 7: Test different user tiers
    print("\n7. Testing different user tiers...")
    
    # Enterprise user (should get no ads)
    ads_enterprise = await ad_manager.get_ads_for_page(
        "enterprise_user", "/dashboard", UserTier.ENTERPRISE, "dashboard"
    )
    print(f"✅ Enterprise user ads: {len(ads_enterprise)} ads (should be 0)")
    
    print("\n🎉 Ad Manager tests completed!")
    
    # Display final statistics
    print("\n📈 Final Statistics:")
    print(f"Users with preferences: {len(ad_manager.user_preferences)}")
    print(f"Total revenue records: {len(ad_manager.revenue_tracker.revenue_data)}")
    print(f"Available ad slots: {len(ad_manager.placement_engine.ad_slots)}")

if __name__ == "__main__":
    asyncio.run(main())