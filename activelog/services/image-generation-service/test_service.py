#!/usr/bin/env python3
"""
Test script for the Comprehensive Image Generation Service
Validates core functionality and integration points
"""

import asyncio
import json
import logging
import aiohttp
import time
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageGenerationServiceTester:
    """Test suite for the image generation service"""
    
    def __init__(self, service_url: str = "http://localhost:8480"):
        self.service_url = service_url
        self.test_results = []
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run comprehensive test suite"""
        
        logger.info("🧪 Starting Comprehensive Image Generation Service Tests")
        logger.info("=" * 60)
        
        # Test service health
        await self.test_service_health()
        
        # Test style analysis
        await self.test_style_analysis()
        
        # Test prompt optimization
        await self.test_prompt_optimization()
        
        # Test model recommendations
        await self.test_model_recommendations()
        
        # Test analytics endpoints
        await self.test_analytics()
        
        # Test configuration endpoints
        await self.test_configuration_endpoints()
        
        # Generate test report
        return self.generate_test_report()
    
    async def test_service_health(self):
        """Test basic service health and status"""
        
        logger.info("🏥 Testing service health...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.service_url}/") as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Check required fields
                        required_fields = ["service", "status", "capabilities", "statistics"]
                        missing_fields = [f for f in required_fields if f not in data]
                        
                        if not missing_fields:
                            self.test_results.append({
                                "test": "service_health",
                                "status": "PASS",
                                "message": "Service is healthy and responsive",
                                "details": {
                                    "service": data["service"],
                                    "version": data.get("version", "unknown"),
                                    "capabilities": len(data["capabilities"]["features"])
                                }
                            })
                            logger.info("✅ Service health check passed")
                        else:
                            self.test_results.append({
                                "test": "service_health",
                                "status": "FAIL",
                                "message": f"Missing required fields: {missing_fields}",
                                "details": data
                            })
                            logger.error(f"❌ Health check failed - missing fields: {missing_fields}")
                    else:
                        self.test_results.append({
                            "test": "service_health",
                            "status": "FAIL", 
                            "message": f"Service returned status {response.status}",
                            "details": {"status_code": response.status}
                        })
                        logger.error(f"❌ Service health check failed - status {response.status}")
                        
        except Exception as e:
            self.test_results.append({
                "test": "service_health",
                "status": "ERROR",
                "message": f"Connection error: {str(e)}",
                "details": {"error": str(e)}
            })
            logger.error(f"❌ Service health check error: {e}")
    
    async def test_style_analysis(self):
        """Test style detection and analysis"""
        
        logger.info("🎨 Testing style analysis...")
        
        test_cases = [
            {
                "prompt": "Photorealistic portrait of a person in natural lighting",
                "expected_style": "photorealistic"
            },
            {
                "prompt": "Oil painting of a landscape with brush strokes visible",
                "expected_style": "artistic"
            },
            {
                "prompt": "Anime character with big eyes and colorful hair",
                "expected_style": "anime"
            },
            {
                "prompt": "Futuristic cyberpunk cityscape with neon lights",
                "expected_style": "sci_fi"
            }
        ]
        
        passed_tests = 0
        
        try:
            async with aiohttp.ClientSession() as session:
                for i, test_case in enumerate(test_cases):
                    payload = {
                        "prompt": test_case["prompt"],
                        "user_id": "test_user"
                    }
                    
                    async with session.post(
                        f"{self.service_url}/analyze/style",
                        json=payload
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            # Check if expected style is detected
                            detected_styles = data.get("detected_styles", {})
                            primary_style = data.get("primary_style")
                            expected = test_case["expected_style"]
                            
                            if expected in detected_styles or primary_style == expected:
                                passed_tests += 1
                                logger.info(f"✅ Style analysis test {i+1} passed: {expected} detected")
                            else:
                                logger.warning(f"⚠️  Style analysis test {i+1} partial: expected {expected}, got {primary_style}")
                        else:
                            logger.error(f"❌ Style analysis test {i+1} failed - status {response.status}")
                            
                self.test_results.append({
                    "test": "style_analysis",
                    "status": "PASS" if passed_tests == len(test_cases) else "PARTIAL" if passed_tests > 0 else "FAIL",
                    "message": f"Passed {passed_tests}/{len(test_cases)} style analysis tests",
                    "details": {"passed": passed_tests, "total": len(test_cases)}
                })
                
        except Exception as e:
            self.test_results.append({
                "test": "style_analysis",
                "status": "ERROR",
                "message": f"Style analysis error: {str(e)}",
                "details": {"error": str(e)}
            })
            logger.error(f"❌ Style analysis test error: {e}")
    
    async def test_prompt_optimization(self):
        """Test prompt enhancement and optimization"""
        
        logger.info("✨ Testing prompt optimization...")
        
        test_prompts = [
            {
                "original": "cat picture",
                "focus": "quality",
                "min_improvement_score": 0.5
            },
            {
                "original": "modern office",
                "focus": "specificity", 
                "min_improvement_score": 0.3
            },
            {
                "original": "artistic drawing",
                "focus": "creativity",
                "min_improvement_score": 0.4
            }
        ]
        
        passed_tests = 0
        
        try:
            async with aiohttp.ClientSession() as session:
                for i, test_case in enumerate(test_prompts):
                    payload = {
                        "original_prompt": test_case["original"],
                        "improvement_focus": test_case["focus"],
                        "user_id": "test_user"
                    }
                    
                    async with session.post(
                        f"{self.service_url}/optimize/prompt",
                        json=payload
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            # Check optimization results
                            original = data.get("original_prompt")
                            optimized = data.get("optimized_prompt")
                            improvements = data.get("improvements", [])
                            enhancement_score = data.get("enhancement_score", 0)
                            
                            if (len(optimized) > len(original) and 
                                len(improvements) > 0 and 
                                enhancement_score >= test_case["min_improvement_score"]):
                                passed_tests += 1
                                logger.info(f"✅ Prompt optimization test {i+1} passed")
                                logger.info(f"   Original: {original}")
                                logger.info(f"   Optimized: {optimized[:100]}...")
                            else:
                                logger.warning(f"⚠️  Prompt optimization test {i+1} insufficient improvement")
                        else:
                            logger.error(f"❌ Prompt optimization test {i+1} failed - status {response.status}")
                            
                self.test_results.append({
                    "test": "prompt_optimization",
                    "status": "PASS" if passed_tests == len(test_prompts) else "PARTIAL" if passed_tests > 0 else "FAIL",
                    "message": f"Passed {passed_tests}/{len(test_prompts)} prompt optimization tests",
                    "details": {"passed": passed_tests, "total": len(test_prompts)}
                })
                
        except Exception as e:
            self.test_results.append({
                "test": "prompt_optimization",
                "status": "ERROR",
                "message": f"Prompt optimization error: {str(e)}",
                "details": {"error": str(e)}
            })
            logger.error(f"❌ Prompt optimization test error: {e}")
    
    async def test_model_recommendations(self):
        """Test model recommendation system"""
        
        logger.info("🤖 Testing model recommendations...")
        
        test_cases = [
            {
                "prompt": "Professional headshot photo for LinkedIn",
                "expected_models": ["dall-e-3"]
            },
            {
                "prompt": "Anime character design with vibrant colors", 
                "expected_models": ["stable-diffusion"]
            },
            {
                "prompt": "Abstract geometric art composition",
                "expected_models": ["stable-diffusion"]
            }
        ]
        
        passed_tests = 0
        
        try:
            async with aiohttp.ClientSession() as session:
                for i, test_case in enumerate(test_cases):
                    # Test via style analysis (which includes model recommendations)
                    payload = {
                        "prompt": test_case["prompt"],
                        "user_id": "test_user"
                    }
                    
                    async with session.post(
                        f"{self.service_url}/analyze/style",
                        json=payload
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            recommended_model = data.get("recommended_model")
                            
                            if recommended_model in test_case["expected_models"]:
                                passed_tests += 1
                                logger.info(f"✅ Model recommendation test {i+1} passed: {recommended_model}")
                            else:
                                logger.warning(f"⚠️  Model recommendation test {i+1}: got {recommended_model}, expected one of {test_case['expected_models']}")
                        else:
                            logger.error(f"❌ Model recommendation test {i+1} failed - status {response.status}")
                            
                self.test_results.append({
                    "test": "model_recommendations",
                    "status": "PASS" if passed_tests == len(test_cases) else "PARTIAL" if passed_tests > 0 else "FAIL",
                    "message": f"Passed {passed_tests}/{len(test_cases)} model recommendation tests",
                    "details": {"passed": passed_tests, "total": len(test_cases)}
                })
                
        except Exception as e:
            self.test_results.append({
                "test": "model_recommendations",
                "status": "ERROR",
                "message": f"Model recommendation error: {str(e)}",
                "details": {"error": str(e)}
            })
            logger.error(f"❌ Model recommendation test error: {e}")
    
    async def test_analytics(self):
        """Test analytics endpoints"""
        
        logger.info("📊 Testing analytics endpoints...")
        
        endpoints_to_test = [
            ("/analytics/system", "system_analytics"),
            ("/analytics/user/test_user", "user_analytics"),
            ("/models", "model_info"),
            ("/styles", "style_info")
        ]
        
        passed_tests = 0
        
        try:
            async with aiohttp.ClientSession() as session:
                for endpoint, test_name in endpoints_to_test:
                    async with session.get(f"{self.service_url}{endpoint}") as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            if data and isinstance(data, dict):
                                passed_tests += 1
                                logger.info(f"✅ Analytics endpoint {endpoint} passed")
                            else:
                                logger.warning(f"⚠️  Analytics endpoint {endpoint} returned empty/invalid data")
                        else:
                            logger.error(f"❌ Analytics endpoint {endpoint} failed - status {response.status}")
                            
                self.test_results.append({
                    "test": "analytics_endpoints",
                    "status": "PASS" if passed_tests == len(endpoints_to_test) else "PARTIAL" if passed_tests > 0 else "FAIL",
                    "message": f"Passed {passed_tests}/{len(endpoints_to_test)} analytics endpoint tests",
                    "details": {"passed": passed_tests, "total": len(endpoints_to_test)}
                })
                
        except Exception as e:
            self.test_results.append({
                "test": "analytics_endpoints",
                "status": "ERROR",
                "message": f"Analytics endpoints error: {str(e)}",
                "details": {"error": str(e)}
            })
            logger.error(f"❌ Analytics endpoints test error: {e}")
    
    async def test_configuration_endpoints(self):
        """Test configuration and info endpoints"""
        
        logger.info("⚙️  Testing configuration endpoints...")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test models endpoint
                async with session.get(f"{self.service_url}/models") as response:
                    models_ok = response.status == 200
                    if models_ok:
                        data = await response.json()
                        models_ok = "available_models" in data
                
                # Test styles endpoint
                async with session.get(f"{self.service_url}/styles") as response:
                    styles_ok = response.status == 200
                    if styles_ok:
                        data = await response.json()
                        styles_ok = "supported_styles" in data
                
                if models_ok and styles_ok:
                    self.test_results.append({
                        "test": "configuration_endpoints",
                        "status": "PASS",
                        "message": "Configuration endpoints working correctly",
                        "details": {"models_endpoint": models_ok, "styles_endpoint": styles_ok}
                    })
                    logger.info("✅ Configuration endpoints test passed")
                else:
                    self.test_results.append({
                        "test": "configuration_endpoints",
                        "status": "FAIL",
                        "message": "Some configuration endpoints failed",
                        "details": {"models_endpoint": models_ok, "styles_endpoint": styles_ok}
                    })
                    logger.error("❌ Configuration endpoints test failed")
                        
        except Exception as e:
            self.test_results.append({
                "test": "configuration_endpoints",
                "status": "ERROR", 
                "message": f"Configuration endpoints error: {str(e)}",
                "details": {"error": str(e)}
            })
            logger.error(f"❌ Configuration endpoints test error: {e}")
    
    def generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["status"] == "PASS"])
        partial_tests = len([r for r in self.test_results if r["status"] == "PARTIAL"])
        failed_tests = len([r for r in self.test_results if r["status"] == "FAIL"])
        error_tests = len([r for r in self.test_results if r["status"] == "ERROR"])
        
        success_rate = (passed_tests + (partial_tests * 0.5)) / total_tests if total_tests > 0 else 0
        
        report = {
            "test_summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "partial": partial_tests,
                "failed": failed_tests,
                "errors": error_tests,
                "success_rate": round(success_rate * 100, 1)
            },
            "overall_status": "HEALTHY" if success_rate >= 0.8 else "DEGRADED" if success_rate >= 0.5 else "UNHEALTHY",
            "test_results": self.test_results,
            "recommendations": self._generate_recommendations()
        }
        
        return report
    
    def _generate_recommendations(self) -> list:
        """Generate recommendations based on test results"""
        
        recommendations = []
        
        # Check for failed tests
        failed_tests = [r for r in self.test_results if r["status"] in ["FAIL", "ERROR"]]
        
        if failed_tests:
            recommendations.append("Address failing tests to improve service reliability")
        
        # Check for partial tests
        partial_tests = [r for r in self.test_results if r["status"] == "PARTIAL"]
        
        if partial_tests:
            recommendations.append("Investigate partial test failures for potential improvements")
        
        # General recommendations
        if not any(r["test"] == "service_health" and r["status"] == "PASS" for r in self.test_results):
            recommendations.append("Service health check failed - verify service is running and accessible")
        
        if not recommendations:
            recommendations.append("All tests passed - service is functioning well")
        
        return recommendations

    def print_test_report(self, report: Dict[str, Any]):
        """Print formatted test report"""
        
        print("\n" + "=" * 60)
        print("🧪 COMPREHENSIVE IMAGE GENERATION SERVICE TEST REPORT")
        print("=" * 60)
        
        summary = report["test_summary"]
        print(f"\n📊 Test Summary:")
        print(f"   Total Tests: {summary['total_tests']}")
        print(f"   Passed: {summary['passed']} ✅")
        print(f"   Partial: {summary['partial']} ⚠️")
        print(f"   Failed: {summary['failed']} ❌")
        print(f"   Errors: {summary['errors']} 💥")
        print(f"   Success Rate: {summary['success_rate']}%")
        
        status = report["overall_status"]
        status_emoji = "🟢" if status == "HEALTHY" else "🟡" if status == "DEGRADED" else "🔴"
        print(f"\n{status_emoji} Overall Status: {status}")
        
        print(f"\n📝 Test Details:")
        for result in report["test_results"]:
            status_emoji = {"PASS": "✅", "PARTIAL": "⚠️", "FAIL": "❌", "ERROR": "💥"}.get(result["status"], "❓")
            print(f"   {status_emoji} {result['test']}: {result['message']}")
        
        if report["recommendations"]:
            print(f"\n💡 Recommendations:")
            for rec in report["recommendations"]:
                print(f"   • {rec}")
        
        print("\n" + "=" * 60)

async def main():
    """Run the test suite"""
    
    # Configuration
    service_url = "http://localhost:8480"
    
    # Create tester
    tester = ImageGenerationServiceTester(service_url)
    
    # Run tests
    start_time = time.time()
    report = await tester.run_all_tests()
    end_time = time.time()
    
    # Add timing to report
    report["test_duration_seconds"] = round(end_time - start_time, 2)
    
    # Print report
    tester.print_test_report(report)
    
    # Save report to file
    import os
    report_path = os.path.join(os.path.dirname(__file__), "test_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"\n📄 Full test report saved to: {report_path}")
    
    # Return appropriate exit code
    if report["overall_status"] == "HEALTHY":
        return 0
    elif report["overall_status"] == "DEGRADED":
        return 1
    else:
        return 2

if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)