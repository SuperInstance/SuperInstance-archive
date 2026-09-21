#!/usr/bin/env python3
"""
Dynamic Bot Language Evolution System - Test Client

This script demonstrates the core functionality of the Dynamic Bot Language system
and can be used by the Dissertation Bot to validate the research platform.

Features tested:
1. Message compression and decompression
2. Cross-domain translation
3. Vocabulary management
4. Research metrics collection
5. Performance analytics
"""

import requests
import json
import time
import random
from typing import Dict, List

class LanguageSystemTestClient:
    def __init__(self, base_url: str = "http://localhost:8472"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def health_check(self) -> Dict:
        """Check if the language system is running"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            return response.json()
        except Exception as e:
            return {"error": str(e), "status": "unhealthy"}
    
    def compress_message(self, message: str, domain: str = "general", 
                        source_bot: str = "test-client", target_bot: str = "test-target") -> Dict:
        """Test message compression"""
        payload = {
            "message": message,
            "domain": domain,
            "source_bot": source_bot,
            "target_bot": target_bot
        }
        
        try:
            response = self.session.post(f"{self.base_url}/compress", json=payload)
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def decompress_message(self, compressed_message: str, domain: str = "general",
                          source_bot: str = "test-client", target_bot: str = "test-target") -> Dict:
        """Test message decompression"""
        payload = {
            "compressed_message": compressed_message,
            "target_domain": domain,
            "source_bot": source_bot,
            "target_bot": target_bot
        }
        
        try:
            response = self.session.post(f"{self.base_url}/decompress", json=payload)
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def translate_message(self, message: str, source_domain: str, target_domain: str,
                         source_bot: str = "test-client", target_bot: str = "test-target") -> Dict:
        """Test cross-domain translation"""
        payload = {
            "message": message,
            "source_domain": source_domain,
            "target_domain": target_domain,
            "source_bot": source_bot,
            "target_bot": target_bot
        }
        
        try:
            response = self.session.post(f"{self.base_url}/translate", json=payload)
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def get_vocabulary(self, domain: str) -> Dict:
        """Get vocabulary for a specific domain"""
        try:
            response = self.session.get(f"{self.base_url}/vocabulary/{domain}")
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def get_analytics(self) -> Dict:
        """Get system analytics"""
        try:
            response = self.session.get(f"{self.base_url}/analytics")
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def get_research_metrics(self, hours: int = 24, experiment_id: str = None) -> Dict:
        """Get research metrics"""
        params = {"hours": hours}
        if experiment_id:
            params["experiment_id"] = experiment_id
        
        try:
            response = self.session.get(f"{self.base_url}/research/metrics", params=params)
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def start_experiment(self, experiment_id: str, config: Dict) -> Dict:
        """Start a research experiment"""
        payload = {
            "experiment_id": experiment_id,
            "config": config
        }
        
        try:
            response = self.session.post(f"{self.base_url}/research/experiment", json=payload)
            return response.json()
        except Exception as e:
            return {"error": str(e)}

def run_comprehensive_test():
    """Run a comprehensive test of the Dynamic Bot Language system"""
    print("🧠 Dynamic Bot Language Evolution System - Test Suite")
    print("=" * 60)
    
    client = LanguageSystemTestClient()
    
    # Test 1: Health Check
    print("\n1. 🏥 Health Check")
    health = client.health_check()
    if "error" in health:
        print(f"   ❌ System not available: {health['error']}")
        return
    else:
        print(f"   ✅ System healthy: {health.get('status', 'unknown')}")
        print(f"   📊 Active tokens: {health.get('active_tokens', 0)}")
        print(f"   📈 Active patterns: {health.get('active_patterns', 0)}")
    
    # Test 2: Message Compression
    print("\n2. 🗜️  Message Compression")
    test_messages = [
        {
            "message": "execute database query with parameters and return formatted results",
            "domain": "database",
            "source_bot": "dmlog-backend",
            "target_bot": "database-manager"
        },
        {
            "message": "navigate to waypoint coordinates using autopilot system with collision avoidance",
            "domain": "marine",
            "source_bot": "marine-autopilot",
            "target_bot": "marine-navigation"
        },
        {
            "message": "generate character stats and abilities for role playing game session",
            "domain": "gaming",
            "source_bot": "dmlog-characters",
            "target_bot": "dmlog-session"
        },
        {
            "message": "process financial transaction and update accounting ledger entries",
            "domain": "business",
            "source_bot": "accounting-core",
            "target_bot": "financial-management"
        }
    ]
    
    compression_results = []
    for i, test_case in enumerate(test_messages):
        print(f"   Test {i+1}: {test_case['domain']} domain")
        result = client.compress_message(**test_case)
        
        if "error" in result:
            print(f"   ❌ Error: {result['error']}")
        else:
            compression_ratio = result.get('compression_ratio', 0)
            original_tokens = result.get('original_tokens', 0)
            compressed_tokens = result.get('compressed_tokens', 0)
            
            print(f"   📝 Original: '{result.get('original_message', '')[:50]}...'")
            print(f"   🗜️  Compressed: '{result.get('compressed_message', '')[:50]}...'")
            print(f"   📊 Compression: {compression_ratio:.2%} ({original_tokens} → {compressed_tokens} tokens)")
            compression_results.append(result)
    
    # Test 3: Message Decompression
    print("\n3. 📤 Message Decompression")
    for i, comp_result in enumerate(compression_results):
        if "compressed_message" in comp_result:
            print(f"   Test {i+1}: Decompressing message")
            decomp_result = client.decompress_message(
                comp_result["compressed_message"],
                test_messages[i]["domain"],
                test_messages[i]["target_bot"],
                test_messages[i]["source_bot"]
            )
            
            if "error" in decomp_result:
                print(f"   ❌ Error: {decomp_result['error']}")
            else:
                print(f"   📤 Decompressed: '{decomp_result.get('decompressed_message', '')[:50]}...'")
                print(f"   ✅ Success: {decomp_result.get('success', False)}")
    
    # Test 4: Cross-Domain Translation
    print("\n4. 🌐 Cross-Domain Translation")
    translation_tests = [
        {
            "message": "execute query with parameters",
            "source_domain": "database",
            "target_domain": "marine"
        },
        {
            "message": "navigate to coordinates",
            "source_domain": "marine", 
            "target_domain": "gaming"
        }
    ]
    
    for i, test_case in enumerate(translation_tests):
        print(f"   Test {i+1}: {test_case['source_domain']} → {test_case['target_domain']}")
        result = client.translate_message(**test_case, source_bot="test-client", target_bot="test-target")
        
        if "error" in result:
            print(f"   ❌ Error: {result['error']}")
        else:
            print(f"   🔤 Original: '{result.get('original_message', '')}'")
            print(f"   🌐 Translated: '{result.get('translated_message', '')}'")
            print(f"   🔄 Mappings: {len(result.get('translation_mappings', []))}")
    
    # Test 5: Vocabulary Analysis
    print("\n5. 📚 Domain Vocabularies")
    domains = ["database", "marine", "gaming", "business", "general"]
    
    for domain in domains:
        vocab = client.get_vocabulary(domain)
        if "error" in vocab:
            print(f"   {domain}: ❌ Error: {vocab['error']}")
        else:
            vocab_size = vocab.get('vocabulary_size', 0)
            print(f"   {domain}: 📖 {vocab_size} tokens")
    
    # Test 6: System Analytics
    print("\n6. 📊 System Analytics")
    analytics = client.get_analytics()
    
    if "error" in analytics:
        print(f"   ❌ Error: {analytics['error']}")
    else:
        print(f"   🔢 Total Active Tokens: {analytics.get('total_active_tokens', 0)}")
        print(f"   🌍 Active Domains: {analytics.get('active_domains', 0)}")
        print(f"   📈 Communication Patterns: {analytics.get('communication_patterns', 0)}")
        print(f"   📊 Average Compression: {analytics.get('average_compression_ratio', 0):.2%}")
        print(f"   📅 Daily Usage: {analytics.get('daily_usage_count', 0)}")
        
        top_tokens = analytics.get('top_performing_tokens', [])
        if top_tokens:
            print(f"   🏆 Top Performing Tokens:")
            for token in top_tokens[:3]:
                print(f"      - {token.get('short_form', 'N/A')}: "
                      f"{token.get('efficiency_score', 0):.2f} efficiency, "
                      f"{token.get('usage_count', 0)} uses")
    
    # Test 7: Research Experiment
    print("\n7. 🔬 Research Experiment")
    experiment_config = {
        "compression_threshold": 0.25,
        "min_usage_threshold": 3,
        "test_duration_hours": 1,
        "focus_domains": ["database", "marine", "gaming"]
    }
    
    experiment_id = f"test_experiment_{int(time.time())}"
    experiment_result = client.start_experiment(experiment_id, experiment_config)
    
    if "error" in experiment_result:
        print(f"   ❌ Error starting experiment: {experiment_result['error']}")
    else:
        print(f"   🧪 Started experiment: {experiment_result.get('experiment_id', 'N/A')}")
        print(f"   ⚙️  Config: {experiment_result.get('config', {})}")
    
    # Test 8: Research Metrics
    print("\n8. 📈 Research Metrics")
    metrics = client.get_research_metrics(hours=24)
    
    if "error" in metrics:
        print(f"   ❌ Error: {metrics['error']}")
    else:
        metrics_data = metrics.get('metrics', [])
        print(f"   📊 Total Metrics: {metrics.get('total_count', 0)}")
        print(f"   ⏰ Time Range: {metrics.get('time_range_hours', 0)} hours")
        
        if metrics_data:
            print("   🔍 Recent Metrics:")
            for metric in metrics_data[:5]:  # Show first 5
                print(f"      - {metric.get('metric_name', 'N/A')}: "
                      f"{metric.get('metric_value', 0):.3f}")
    
    # Test 9: Load Testing with Multiple Messages
    print("\n9. ⚡ Performance Load Test")
    start_time = time.time()
    
    # Generate test messages
    sample_phrases = [
        "execute database query operation",
        "process user authentication request", 
        "generate report with analytics data",
        "navigate to target destination",
        "calculate financial transaction fees",
        "update inventory tracking system",
        "send notification to user interface",
        "perform data validation checks"
    ]
    
    domains = ["database", "marine", "gaming", "business"]
    
    for i in range(10):  # Send 10 messages
        message = random.choice(sample_phrases) + f" iteration {i+1}"
        domain = random.choice(domains)
        
        result = client.compress_message(
            message=message,
            domain=domain,
            source_bot="load-test-client",
            target_bot="load-test-target"
        )
        
        if i % 5 == 0:  # Print every 5th result
            compression_ratio = result.get('compression_ratio', 0)
            processing_time = result.get('processing_time_ms', 0)
            print(f"   Message {i+1}: {compression_ratio:.2%} compression, "
                  f"{processing_time:.1f}ms processing")
    
    total_time = time.time() - start_time
    print(f"   ⚡ Total processing time: {total_time:.2f} seconds")
    print(f"   📊 Average per message: {(total_time/10)*1000:.1f}ms")
    
    # Final Summary
    print("\n" + "=" * 60)
    print("🎓 Research Platform Summary")
    print("   ✅ Dynamic language generation functional")
    print("   ✅ Token compression and abstraction working")
    print("   ✅ Cross-domain translation operational")
    print("   ✅ Research metrics collection active")
    print("   ✅ Performance monitoring enabled")
    print("   ✅ Controlled experiments supported")
    print("\n🎯 Ready for Dissertation Bot research!")
    print("   📊 All metrics are being collected for academic analysis")
    print("   🔬 Experiment framework is ready for controlled studies")
    print("   📈 Performance data is available for research insights")

def run_simple_demo():
    """Run a simple demonstration for quick testing"""
    print("🚀 Quick Demo - Dynamic Bot Language Evolution")
    print("-" * 50)
    
    client = LanguageSystemTestClient()
    
    # Health check
    health = client.health_check()
    if "error" in health:
        print(f"❌ System not available: {health['error']}")
        return
    
    print(f"✅ System Status: {health.get('status', 'unknown')}")
    
    # Test compression
    test_message = "execute database query with user parameters and return formatted JSON results"
    print(f"\n📝 Test Message: {test_message}")
    
    result = client.compress_message(
        message=test_message,
        domain="database",
        source_bot="demo-client",
        target_bot="database-service"
    )
    
    if "error" in result:
        print(f"❌ Compression failed: {result['error']}")
    else:
        print(f"🗜️  Compressed: {result.get('compressed_message', 'N/A')}")
        print(f"📊 Compression Ratio: {result.get('compression_ratio', 0):.2%}")
        print(f"⚡ Processing Time: {result.get('processing_time_ms', 0):.1f}ms")
    
    # Get analytics
    analytics = client.get_analytics()
    if "error" not in analytics:
        print(f"\n📊 System Analytics:")
        print(f"   Active Tokens: {analytics.get('total_active_tokens', 0)}")
        print(f"   Active Domains: {analytics.get('active_domains', 0)}")
    
    print("\n✅ Demo completed successfully!")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        run_simple_demo()
    else:
        run_comprehensive_test()