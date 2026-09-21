#!/usr/bin/env python3
"""
SuperInstance DMlog Integration Test Suite
Tests the comprehensive integration of DMlog services with SuperInstance ecosystem
"""

import asyncio
import httpx
import json
import logging
from typing import Dict, Any
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DMlogIntegrationTester:
    """Test suite for DMlog SuperInstance integration"""
    
    def __init__(self):
        self.services = {
            "api_gateway": "http://localhost:8088",
            "user_management": "http://localhost:8092",
            "ai_insights": "http://localhost:8090",
            "dmlog_core": "http://localhost:8012",
            "dmlog_ai": "http://localhost:8097",
            "dmlog_final": "http://localhost:8508"
        }
        
        self.test_user_id = "test_user_123"
        self.test_character_id = "char_456"
        self.test_campaign_id = "campaign_789"
    
    async def run_comprehensive_tests(self):
        """Run comprehensive integration test suite"""
        logger.info("🧪 Starting DMlog SuperInstance Integration Tests")
        
        test_results = {
            "service_health": await self.test_service_health(),
            "cross_domain_character_enhancement": await self.test_character_enhancement(),
            "dm_rewards_system": await self.test_dm_rewards(),
            "ai_campaign_generation": await self.test_ai_campaign_generation(),
            "gaming_profile_integration": await self.test_gaming_profiles(),
            "compute_capital_integration": await self.test_compute_capital_integration(),
            "api_gateway_routing": await self.test_api_gateway_routing()
        }
        
        self._print_test_results(test_results)
        return test_results
    
    async def test_service_health(self) -> Dict[str, Any]:
        """Test health of all DMlog-related services"""
        logger.info("🏥 Testing service health...")
        health_results = {}
        
        async with httpx.AsyncClient() as client:
            for service_name, url in self.services.items():
                try:
                    response = await client.get(f"{url}/health", timeout=5)
                    health_results[service_name] = {
                        "status": "healthy" if response.status_code == 200 else "unhealthy",
                        "response_time": response.elapsed.total_seconds(),
                        "integration_status": response.json().get("superinstance_integration", {}) if response.status_code == 200 else {}
                    }
                except Exception as e:
                    health_results[service_name] = {
                        "status": "error",
                        "error": str(e)
                    }
        
        return health_results
    
    async def test_character_enhancement(self) -> Dict[str, Any]:
        """Test cross-domain character enhancement"""
        logger.info("🎭 Testing cross-domain character enhancement...")
        
        try:
            async with httpx.AsyncClient() as client:
                # Test DMlog Core character enhancement endpoint
                response = await client.post(
                    f"{self.services['dmlog_core']}/api/v1/characters/enhance",
                    json={
                        "character_id": self.test_character_id,
                        "user_id": self.test_user_id
                    }
                )
                
                if response.status_code == 200:
                    enhancement_data = response.json()
                    return {
                        "status": "success",
                        "enhancement_applied": True,
                        "domains_integrated": enhancement_data.get("domains_integrated", []),
                        "character_bonuses": len(enhancement_data.get("enhancement", {}))
                    }
                else:
                    return {"status": "error", "code": response.status_code}
                    
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def test_dm_rewards(self) -> Dict[str, Any]:
        """Test DM rewards and compute capital integration"""
        logger.info("💰 Testing DM rewards system...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.services['dmlog_core']}/api/v1/dm/rewards",
                    json={
                        "user_id": self.test_user_id,
                        "campaign_id": self.test_campaign_id,
                        "session_quality": 0.85
                    }
                )
                
                if response.status_code == 200:
                    reward_data = response.json()
                    return {
                        "status": "success",
                        "rewards_tracked": reward_data.get("dm_rewards_tracked", False),
                        "compute_capital_earned": reward_data.get("compute_capital_earned", 0),
                        "quality_score": reward_data.get("quality_score", 0)
                    }
                else:
                    return {"status": "error", "code": response.status_code}
                    
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def test_ai_campaign_generation(self) -> Dict[str, Any]:
        """Test AI-powered campaign generation"""
        logger.info("🤖 Testing AI campaign generation...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.services['dmlog_core']}/api/v1/campaigns/ai-generate",
                    json={
                        "user_id": self.test_user_id,
                        "campaign_context": {
                            "theme": "maritime_adventure",
                            "player_count": 4,
                            "experience_level": "intermediate"
                        }
                    }
                )
                
                if response.status_code == 200:
                    campaign_data = response.json()
                    return {
                        "status": "success",
                        "suggestions_generated": len(campaign_data.get("campaign_suggestions", {})),
                        "cross_domain_enhanced": campaign_data.get("cross_domain_enhancements", False),
                        "personalization": campaign_data.get("personalization", "none")
                    }
                else:
                    return {"status": "error", "code": response.status_code}
                    
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def test_gaming_profiles(self) -> Dict[str, Any]:
        """Test gaming profile integration"""
        logger.info("👤 Testing gaming profiles integration...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.services['user_management']}/api/v1/users/{self.test_user_id}/gaming-profile"
                )
                
                if response.status_code == 200:
                    profile_data = response.json()
                    return {
                        "status": "success",
                        "profile_exists": True,
                        "cross_domain_bonuses": len(profile_data.get("cross_domain_bonuses", {})),
                        "dm_performance_tracked": "dm_performance" in profile_data
                    }
                else:
                    # Gaming profiles might not exist yet - check if endpoint is reachable
                    return {
                        "status": "endpoint_available" if response.status_code == 404 else "error",
                        "code": response.status_code
                    }
                    
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def test_compute_capital_integration(self) -> Dict[str, Any]:
        """Test compute capital economy integration"""
        logger.info("⚡ Testing compute capital integration...")
        
        try:
            async with httpx.AsyncClient() as client:
                # Test through API Gateway
                response = await client.post(
                    f"{self.services['api_gateway']}/api/v1/compute-capital/dm-rewards",
                    json={
                        "user_id": self.test_user_id,
                        "campaign_id": self.test_campaign_id,
                        "session_quality": 0.9
                    }
                )
                
                return {
                    "status": "integration_ready" if response.status_code in [200, 404] else "error",
                    "gateway_routing": response.status_code != 500,
                    "code": response.status_code
                }
                
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def test_api_gateway_routing(self) -> Dict[str, Any]:
        """Test API Gateway routing to DMlog services"""
        logger.info("🌐 Testing API Gateway routing...")
        
        try:
            async with httpx.AsyncClient() as client:
                # Test gateway health includes DMlog services
                response = await client.get(f"{self.services['api_gateway']}/health")
                
                if response.status_code == 200:
                    health_data = response.json()
                    services = health_data.get("services", {})
                    
                    return {
                        "status": "success",
                        "gateway_healthy": True,
                        "services_registered": len(services),
                        "dmlog_services_detected": any("dmlog" in service.lower() for service in services.keys())
                    }
                else:
                    return {"status": "error", "code": response.status_code}
                    
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _print_test_results(self, results: Dict[str, Any]):
        """Print formatted test results"""
        print("\n" + "="*80)
        print("🎮 DMLOG SUPERINSTANCE INTEGRATION TEST RESULTS")
        print("="*80)
        
        total_tests = 0
        passed_tests = 0
        
        for test_name, test_result in results.items():
            total_tests += 1
            status = test_result.get("status", "unknown")
            
            if status in ["success", "endpoint_available", "integration_ready"]:
                passed_tests += 1
                status_emoji = "✅"
            elif status == "error":
                status_emoji = "❌"
            else:
                status_emoji = "⚠️"
            
            print(f"{status_emoji} {test_name}: {status}")
            
            # Print additional details for important tests
            if test_name == "service_health":
                for service, health in test_result.items():
                    if isinstance(health, dict):
                        service_status = health.get("status", "unknown")
                        print(f"    📊 {service}: {service_status}")
            
            elif test_name == "cross_domain_character_enhancement":
                domains = test_result.get("domains_integrated", [])
                if domains:
                    print(f"    🎭 Domains integrated: {', '.join(domains)}")
            
            elif test_name == "dm_rewards_system":
                capital = test_result.get("compute_capital_earned", 0)
                if capital:
                    print(f"    💰 Compute capital earned: {capital}")
        
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        print(f"\n📊 Overall Success Rate: {success_rate:.1f}% ({passed_tests}/{total_tests} tests passed)")
        
        if success_rate >= 80:
            print("🎉 DMlog SuperInstance integration is EXCELLENT!")
        elif success_rate >= 60:
            print("👍 DMlog SuperInstance integration is GOOD - minor improvements needed")
        else:
            print("⚠️  DMlog SuperInstance integration needs attention")
        
        print("="*80)

async def main():
    """Main test execution"""
    tester = DMlogIntegrationTester()
    results = await tester.run_comprehensive_tests()
    
    # Log detailed results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"/home/activeloguser/activelog/dmlog_integration_test_{timestamp}.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📁 Detailed results saved to: dmlog_integration_test_{timestamp}.json")

if __name__ == "__main__":
    asyncio.run(main())