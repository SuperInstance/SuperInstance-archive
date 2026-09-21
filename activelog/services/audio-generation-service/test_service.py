#!/usr/bin/env python3
"""
Test Suite for Comprehensive Audio Generation Service
Building Bots Network - Audio Construction Excellence Testing
"""

import asyncio
import json
import requests
import time
from typing import Dict, Any, List
import sys
import os

# Service configuration
SERVICE_URL = "http://localhost:8485"
TEST_TIMEOUT = 30

# Test colors
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_banner():
    """Print test banner"""
    print(f"{Colors.PURPLE}{Colors.BOLD}")
    print("████████████████████████████████████████████████████████████")
    print("█                                                          █")
    print("█    🏗️  BUILDING BOTS NETWORK - AUDIO SERVICE TESTS      █")
    print("█                                                          █")
    print("█    Testing: Audio Construction Excellence               █")
    print("█    Mission: Comprehensive Service Validation           █")
    print("█                                                          █")
    print("████████████████████████████████████████████████████████████")
    print(f"{Colors.END}")
    print()

def print_test_header(test_name: str):
    """Print test section header"""
    print(f"{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}🧪 {test_name}{Colors.END}")
    print(f"{Colors.CYAN}{'='*60}{Colors.END}")

def print_success(message: str):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def print_error(message: str):
    """Print error message"""
    print(f"{Colors.RED}❌ {message}{Colors.END}")

def print_warning(message: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")

def print_info(message: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.END}")

def wait_for_service(max_wait: int = 30) -> bool:
    """Wait for service to be available"""
    print_info(f"Waiting for service at {SERVICE_URL}...")
    
    for i in range(max_wait):
        try:
            response = requests.get(f"{SERVICE_URL}/", timeout=5)
            if response.status_code == 200:
                print_success("Service is available!")
                return True
        except requests.exceptions.RequestException:
            pass
        
        if i < max_wait - 1:  # Don't sleep on the last iteration
            time.sleep(1)
    
    print_error("Service is not available after waiting")
    return False

class AudioServiceTester:
    """Comprehensive test suite for the audio service"""
    
    def __init__(self, service_url: str):
        self.service_url = service_url
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
    
    def run_test(self, test_name: str, test_func):
        """Run a single test with error handling"""
        self.total_tests += 1
        print(f"\n{Colors.BLUE}🔍 Testing: {test_name}{Colors.END}")
        
        try:
            result = test_func()
            if result:
                print_success(f"{test_name} - PASSED")
                self.passed_tests += 1
                self.test_results.append((test_name, "PASSED", None))
            else:
                print_error(f"{test_name} - FAILED")
                self.test_results.append((test_name, "FAILED", "Test returned False"))
        except Exception as e:
            print_error(f"{test_name} - ERROR: {str(e)}")
            self.test_results.append((test_name, "ERROR", str(e)))
    
    def test_service_health(self) -> bool:
        """Test basic service health"""
        try:
            response = requests.get(f"{self.service_url}/", timeout=10)
            data = response.json()
            
            # Check response structure
            required_keys = ["service", "status", "capabilities", "mission"]
            for key in required_keys:
                if key not in data:
                    print_error(f"Missing key in health response: {key}")
                    return False
            
            if data["status"] != "operational":
                print_error(f"Service status is not operational: {data['status']}")
                return False
            
            if "building_bots_network" not in str(data).lower():
                print_warning("Building bots network not mentioned in health response")
            
            print_info(f"Service version: {data.get('version', 'unknown')}")
            return True
            
        except Exception as e:
            print_error(f"Health check failed: {e}")
            return False
    
    def test_voice_catalog(self) -> bool:
        """Test voice catalog endpoint"""
        try:
            response = requests.get(f"{self.service_url}/voices", timeout=10)
            data = response.json()
            
            if "voice_catalog" not in data:
                print_error("No voice_catalog in response")
                return False
            
            # Check for voice categories
            voice_catalog = data["voice_catalog"]
            if "openai" not in voice_catalog and "local" not in voice_catalog:
                print_error("No voice categories found")
                return False
            
            total_voices = sum(len(voices) for voices in voice_catalog.values())
            print_info(f"Total voices available: {total_voices}")
            
            return total_voices > 0
            
        except Exception as e:
            print_error(f"Voice catalog test failed: {e}")
            return False
    
    def test_language_support(self) -> bool:
        """Test language support endpoint"""
        try:
            response = requests.get(f"{self.service_url}/languages", timeout=10)
            data = response.json()
            
            if "supported_languages" not in data:
                print_error("No supported_languages in response")
                return False
            
            languages = data["supported_languages"]
            if not isinstance(languages, list) or len(languages) == 0:
                print_error("No languages in list")
                return False
            
            print_info(f"Languages supported: {len(languages)}")
            print_info(f"Sample languages: {', '.join(languages[:5])}")
            
            return True
            
        except Exception as e:
            print_error(f"Language support test failed: {e}")
            return False
    
    def test_model_information(self) -> bool:
        """Test models information endpoint"""
        try:
            response = requests.get(f"{self.service_url}/models", timeout=10)
            data = response.json()
            
            if "available_models" not in data:
                print_error("No available_models in response")
                return False
            
            models = data["available_models"]
            if not isinstance(models, dict) or len(models) == 0:
                print_error("No models in response")
                return False
            
            # Check for expected models
            expected_models = ["openai-tts", "festival", "espeak", "piper"]
            found_models = [model for model in expected_models if model in models]
            
            print_info(f"Models found: {', '.join(found_models)}")
            
            return len(found_models) > 0
            
        except Exception as e:
            print_error(f"Model information test failed: {e}")
            return False
    
    def test_building_bots_mission(self) -> bool:
        """Test building bots mission endpoint"""
        try:
            response = requests.get(f"{self.service_url}/building-bots/mission", timeout=10)
            data = response.json()
            
            required_keys = ["mission", "network_status", "audio_specialization"]
            for key in required_keys:
                if key not in data:
                    print_error(f"Missing key in mission response: {key}")
                    return False
            
            mission = data["mission"]
            if "audio construction" not in str(mission).lower():
                print_error("Mission doesn't mention audio construction")
                return False
            
            if data["network_status"] != "operational":
                print_warning(f"Network status is not operational: {data['network_status']}")
            
            print_info(f"Mission: {mission.get('primary', 'Not specified')}")
            return True
            
        except Exception as e:
            print_error(f"Building bots mission test failed: {e}")
            return False
    
    def test_speech_generation(self) -> bool:
        """Test basic speech generation"""
        try:
            # Test data
            test_data = {
                "text": "Hello, this is a test of the building bots audio generation service.",
                "user_id": "test_user",
                "voice_id": "alloy",
                "language": "en",
                "quality": "standard",
                "format": "mp3",
                "enhance_audio": False  # Disable to avoid processing delays
            }
            
            print_info("Sending speech generation request...")
            response = requests.post(
                f"{self.service_url}/generate/speech", 
                json=test_data, 
                timeout=30
            )
            
            if response.status_code != 200:
                print_error(f"HTTP error: {response.status_code}")
                return False
            
            data = response.json()
            
            # Check response structure
            required_keys = ["success", "audio_id", "model_used"]
            for key in required_keys:
                if key not in data:
                    print_error(f"Missing key in response: {key}")
                    return False
            
            if not data["success"]:
                print_error(f"Generation failed: {data.get('error', 'Unknown error')}")
                return False
            
            print_info(f"Audio generated with model: {data['model_used']}")
            print_info(f"Audio ID: {data['audio_id']}")
            
            if "building_bots_integration" in data:
                print_success("Building bots integration confirmed")
            
            return True
            
        except Exception as e:
            print_error(f"Speech generation test failed: {e}")
            return False
    
    def test_batch_generation(self) -> bool:
        """Test batch audio generation"""
        try:
            # Test data
            test_data = {
                "texts": [
                    "First test audio for batch generation.",
                    "Second test audio for the building bots network.",
                    "Third test demonstrating batch capabilities."
                ],
                "user_id": "test_user",
                "language": "en",
                "format": "mp3",
                "priority": 5
            }
            
            print_info("Sending batch generation request...")
            response = requests.post(
                f"{self.service_url}/generate/batch", 
                json=test_data, 
                timeout=60
            )
            
            if response.status_code != 200:
                print_error(f"HTTP error: {response.status_code}")
                return False
            
            data = response.json()
            
            if not data.get("success"):
                print_error(f"Batch generation failed: {data.get('error', 'Unknown error')}")
                return False
            
            expected_count = len(test_data["texts"])
            actual_count = data.get("successful_generations", 0)
            
            print_info(f"Batch results: {actual_count}/{expected_count} successful")
            
            return actual_count > 0
            
        except Exception as e:
            print_error(f"Batch generation test failed: {e}")
            return False
    
    def test_music_generation(self) -> bool:
        """Test music generation"""
        try:
            # Test data
            test_data = {
                "description": "Short upbeat electronic music for testing the building bots system",
                "user_id": "test_user",
                "duration": 10.0,  # Short duration for testing
                "genre": "electronic",
                "mood": "upbeat"
            }
            
            print_info("Sending music generation request...")
            response = requests.post(
                f"{self.service_url}/generate/music", 
                json=test_data, 
                timeout=30
            )
            
            if response.status_code != 200:
                print_error(f"HTTP error: {response.status_code}")
                return False
            
            data = response.json()
            
            if not data.get("success"):
                print_error(f"Music generation failed: {data.get('error', 'Unknown error')}")
                return False
            
            print_info(f"Music generated: {data.get('duration', 0)} seconds")
            print_info(f"Model used: {data.get('model_used', 'unknown')}")
            
            return True
            
        except Exception as e:
            print_error(f"Music generation test failed: {e}")
            return False
    
    def test_system_analytics(self) -> bool:
        """Test system analytics endpoint"""
        try:
            response = requests.get(f"{self.service_url}/analytics/system", timeout=10)
            data = response.json()
            
            required_sections = ["overview", "building_bots_network"]
            for section in required_sections:
                if section not in data:
                    print_error(f"Missing section in analytics: {section}")
                    return False
            
            overview = data["overview"]
            building_bots = data["building_bots_network"]
            
            print_info(f"Total generations: {overview.get('total_generations', 0)}")
            print_info(f"Network status: {building_bots.get('network_status', 'unknown')}")
            
            return True
            
        except Exception as e:
            print_error(f"System analytics test failed: {e}")
            return False
    
    def test_feedback_submission(self) -> bool:
        """Test feedback submission"""
        try:
            # Test data
            feedback_data = {
                "audio_id": "test_audio_123",
                "user_id": "test_user",
                "quality_score": 8.5,
                "voice_naturalness": 8.0,
                "clarity": 9.0,
                "overall_satisfaction": 8.2,
                "comments": "Test feedback for building bots network service"
            }
            
            response = requests.post(
                f"{self.service_url}/feedback", 
                json=feedback_data, 
                timeout=10
            )
            
            if response.status_code != 200:
                print_error(f"HTTP error: {response.status_code}")
                return False
            
            data = response.json()
            
            if "message" not in data or "successfully" not in data["message"].lower():
                print_error("Feedback submission not acknowledged")
                return False
            
            print_info("Feedback submitted and acknowledged")
            return True
            
        except Exception as e:
            print_error(f"Feedback submission test failed: {e}")
            return False
    
    def run_all_tests(self):
        """Run all test suites"""
        print_test_header("BASIC SERVICE TESTS")
        self.run_test("Service Health Check", self.test_service_health)
        self.run_test("Voice Catalog", self.test_voice_catalog)
        self.run_test("Language Support", self.test_language_support)
        self.run_test("Model Information", self.test_model_information)
        self.run_test("Building Bots Mission", self.test_building_bots_mission)
        
        print_test_header("AUDIO GENERATION TESTS")
        self.run_test("Speech Generation", self.test_speech_generation)
        self.run_test("Batch Generation", self.test_batch_generation)
        self.run_test("Music Generation", self.test_music_generation)
        
        print_test_header("ANALYTICS AND FEEDBACK TESTS")
        self.run_test("System Analytics", self.test_system_analytics)
        self.run_test("Feedback Submission", self.test_feedback_submission)
        
        self.print_summary()
    
    def print_summary(self):
        """Print test results summary"""
        print()
        print(f"{Colors.CYAN}{'='*60}{Colors.END}")
        print(f"{Colors.CYAN}{Colors.BOLD}🏗️  TEST RESULTS SUMMARY{Colors.END}")
        print(f"{Colors.CYAN}{'='*60}{Colors.END}")
        print()
        
        # Overall results
        success_rate = (self.passed_tests / self.total_tests) * 100 if self.total_tests > 0 else 0
        
        if success_rate == 100:
            status_color = Colors.GREEN
            status_icon = "✅"
            status_text = "EXCELLENT"
        elif success_rate >= 80:
            status_color = Colors.YELLOW
            status_icon = "⚠️"
            status_text = "GOOD"
        else:
            status_color = Colors.RED
            status_icon = "❌"
            status_text = "NEEDS ATTENTION"
        
        print(f"{status_color}{Colors.BOLD}{status_icon} Overall Status: {status_text}{Colors.END}")
        print(f"{Colors.BLUE}Tests Passed: {self.passed_tests}/{self.total_tests} ({success_rate:.1f}%){Colors.END}")
        print()
        
        # Detailed results
        print(f"{Colors.BOLD}Detailed Results:{Colors.END}")
        for test_name, status, error in self.test_results:
            if status == "PASSED":
                print(f"  {Colors.GREEN}✅ {test_name}{Colors.END}")
            elif status == "FAILED":
                print(f"  {Colors.RED}❌ {test_name}{Colors.END}")
                if error:
                    print(f"     {Colors.RED}   └─ {error}{Colors.END}")
            else:  # ERROR
                print(f"  {Colors.RED}🔥 {test_name} (ERROR){Colors.END}")
                if error:
                    print(f"     {Colors.RED}   └─ {error}{Colors.END}")
        
        print()
        
        # Building Bots Network status
        print(f"{Colors.PURPLE}{Colors.BOLD}🏗️  Building Bots Network Status:{Colors.END}")
        if success_rate >= 90:
            print(f"  {Colors.GREEN}✅ Audio Construction Excellence: ACHIEVED{Colors.END}")
            print(f"  {Colors.GREEN}✅ System Integration: OPERATIONAL{Colors.END}")
            print(f"  {Colors.GREEN}✅ Service Quality: MEETS STANDARDS{Colors.END}")
        elif success_rate >= 70:
            print(f"  {Colors.YELLOW}⚠️  Audio Construction Excellence: PARTIAL{Colors.END}")
            print(f"  {Colors.YELLOW}⚠️  System Integration: FUNCTIONAL{Colors.END}")
            print(f"  {Colors.YELLOW}⚠️  Service Quality: ACCEPTABLE{Colors.END}")
        else:
            print(f"  {Colors.RED}❌ Audio Construction Excellence: REQUIRES WORK{Colors.END}")
            print(f"  {Colors.RED}❌ System Integration: ISSUES DETECTED{Colors.END}")
            print(f"  {Colors.RED}❌ Service Quality: BELOW STANDARDS{Colors.END}")
        
        print()
        print(f"{Colors.CYAN}{'='*60}{Colors.END}")
        
        # Return exit code
        return 0 if success_rate >= 80 else 1

def main():
    """Main test execution"""
    print_banner()
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print("Usage: python3 test_service.py [--wait] [--service-url URL]")
            print()
            print("Options:")
            print("  --wait          Wait for service to become available")
            print("  --service-url   Override default service URL")
            print("  --help, -h      Show this help message")
            return 0
    
    # Parse arguments
    wait_for_service_flag = "--wait" in sys.argv
    service_url = SERVICE_URL
    
    if "--service-url" in sys.argv:
        url_index = sys.argv.index("--service-url") + 1
        if url_index < len(sys.argv):
            service_url = sys.argv[url_index]
    
    print_info(f"Testing service at: {service_url}")
    
    # Wait for service if requested
    if wait_for_service_flag:
        if not wait_for_service():
            print_error("Service not available, cannot run tests")
            return 1
    
    # Run tests
    tester = AudioServiceTester(service_url)
    exit_code = tester.run_all_tests()
    
    return exit_code

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)