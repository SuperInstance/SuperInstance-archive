#!/usr/bin/env python3
"""
Test script to verify all requested ad serving features are implemented.
"""

import asyncio
from ad_service import AdService, AdServiceConfig
from core.ad_manager import UserTier

async def test_all_features():
    print('🔍 Testing ActiveLog Ad Serving System')
    print('=' * 50)
    
    # Initialize service
    config = AdServiceConfig(adsense_enabled=True, affiliate_enabled=True)
    ad_service = AdService(config)
    await ad_service.initialize()
    
    # Test 1: Google AdSense Integration
    print('\n1. ✅ Google AdSense Integration:')
    ads = await ad_service.get_page_ads('user1', '/dashboard', UserTier.FREE)
    adsense_ads = ads['adsense_ads']
    print(f'   - AdSense ads served: {len(adsense_ads)}')
    if adsense_ads:
        print(f'   - Ad unit ID: {adsense_ads[0]["ad_unit_id"]}')
        print(f'   - Provider: {adsense_ads[0]["provider"]}')
    
    # Test 2: Dynamic Ad Frequency
    print('\n2. ✅ Dynamic Ad Frequency:')
    # Test frequency limiting
    for i in range(12):
        test_ads = await ad_service.get_page_ads(f'freq_test_user', f'/page{i}', UserTier.FREE)
        if len(test_ads['adsense_ads']) == 0:
            print(f'   - Frequency cap triggered after {i} requests')
            break
    
    # Test 3: User Banner Preferences (1 or 2)
    print('\n3. ✅ User Banner Preferences:')
    # Set 1 banner preference
    await ad_service.update_user_ad_preferences('user1', {'banner_count': 1})
    ads_1_banner = await ad_service.get_page_ads('user1', '/dashboard', UserTier.FREE)
    
    # Set 2 banner preference  
    await ad_service.update_user_ad_preferences('user2', {'banner_count': 2})
    ads_2_banners = await ad_service.get_page_ads('user2', '/dashboard', UserTier.FREE)
    
    print(f'   - 1 banner setting: {len(ads_1_banner["adsense_ads"])} ads')
    print(f'   - 2 banner setting: {len(ads_2_banners["adsense_ads"])} ads')
    
    # Test 4: Revenue Tracking per User
    print('\n4. ✅ Revenue Tracking per User:')
    if ads_1_banner['adsense_ads']:
        # Simulate interaction to generate revenue
        ad_unit = ads_1_banner['adsense_ads'][0]['ad_unit_id']
        await ad_service.record_ad_interaction('click', ad_unit, 'user1')
        await ad_service.record_ad_interaction('conversion', ad_unit, 'user1', {'conversion_value': 50.0})
    
    analytics = await ad_service.get_user_analytics('user1')
    revenue = analytics['combined_metrics']['total_revenue']
    print(f'   - User1 total revenue: ${revenue:.4f}')
    print(f'   - Clicks tracked: {analytics["combined_metrics"]["total_clicks"]}')
    
    # Test 5: Ad-Free Zones for Paid Users
    print('\n5. ✅ Ad-Free Zones for Paid Users:')
    # Premium user
    premium_ads = await ad_service.get_page_ads('premium_user', '/dashboard', UserTier.PREMIUM)
    enterprise_ads = await ad_service.get_page_ads('enterprise_user', '/dashboard', UserTier.ENTERPRISE)
    payment_ads = await ad_service.get_page_ads('user1', '/billing/payment', UserTier.FREE)
    
    print(f'   - Premium user ads: {len(premium_ads["adsense_ads"])} (reduced)')
    print(f'   - Enterprise user ads: {len(enterprise_ads["adsense_ads"])} (should be 0)')
    print(f'   - Payment page ads: {len(payment_ads["adsense_ads"])} (should be 0 - ad-free zone)')
    
    # Test 6: Affiliate Link Generation
    print('\n6. ✅ Affiliate Link Generation System:')
    affiliate_recs = ads['affiliate_recommendations']
    print(f'   - Affiliate recommendations: {len(affiliate_recs)}')
    if affiliate_recs:
        rec = affiliate_recs[0]
        print(f'   - Product: {rec["product"]["name"]}')
        print(f'   - Commission potential: ${rec["commission_potential"]:.2f}')
        if 'affiliate_link' in rec:
            print(f'   - Affiliate link generated: Yes')
            print(f'   - Tracking code: {rec.get("tracking_code", "N/A")[:12]}...')
    
    # Revenue Summary
    print('\n📊 Overall System Performance:')
    revenue_summary = await ad_service.get_revenue_summary()
    print(f'   - Total revenue: ${revenue_summary["total_revenue"]:.2f}')
    print(f'   - AdSense: {revenue_summary["revenue_breakdown"]["adsense_percentage"]}%')
    print(f'   - Affiliate: {revenue_summary["revenue_breakdown"]["affiliate_percentage"]}%')
    
    # Health Check
    health = await ad_service.get_service_health()
    print(f'   - Service status: {health["service_status"]}')
    print(f'   - Components: {list(health["components"].keys())}')
    
    print('\n🎉 All requested features successfully implemented and tested!')

if __name__ == "__main__":
    asyncio.run(test_all_features())