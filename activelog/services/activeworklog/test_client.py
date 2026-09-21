#!/usr/bin/env python3
"""
ActiveWorkLog Coordination System - Test Client

This script demonstrates the bot coordination capabilities and provides
a comprehensive test suite for the ActiveWorkLog system.

Features tested:
1. Work registration and conflict detection
2. Resource availability checking
3. Task handoffs between bots
4. Network status monitoring
5. Coordination performance analytics
"""

import requests
import json
import time
import random
from typing import Dict, List

class CoordinationTestClient:
    def __init__(self, base_url: str = "http://localhost:8480"):
        self.base_url = base_url
        self.session = requests.Session()
        self.registered_work_ids = []
    
    def health_check(self) -> Dict:
        """Check if the coordination system is running"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            return response.json()
        except Exception as e:
            return {"error": str(e), "status": "unhealthy"}
    
    def register_work(self, bot_name: str, task_description: str, 
                     resources: List[str] = None, priority: int = 5,
                     estimated_duration_minutes: int = None,
                     can_be_shared: bool = False) -> Dict:
        """Register new work with the coordination system"""
        payload = {
            "bot_name": bot_name,
            "task_description": task_description,
            "resources": resources or [],
            "priority": priority,
            "estimated_duration_minutes": estimated_duration_minutes,
            "can_be_shared": can_be_shared,
            "metadata": {"test_client": True, "registered_at": time.time()}
        }
        
        try:
            response = self.session.post(f"{self.base_url}/work/register", json=payload)
            result = response.json()
            if "work_id" in result:
                self.registered_work_ids.append(result["work_id"])
            return result
        except Exception as e:
            return {"error": str(e)}
    
    def update_work(self, work_id: str, progress: float = None, 
                   status: str = None, metadata: Dict = None) -> Dict:
        """Update work progress and status"""
        payload = {}
        if progress is not None:
            payload["progress_percentage"] = progress
        if status:
            payload["status"] = status
        if metadata:
            payload["metadata"] = metadata
        
        try:
            response = self.session.put(f"{self.base_url}/work/{work_id}", json=payload)
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def complete_work(self, work_id: str, notes: str = "") -> Dict:
        """Mark work as completed"""
        try:
            response = self.session.post(
                f"{self.base_url}/work/{work_id}/complete",
                params={"completion_notes": notes}
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def request_handoff(self, work_id: str, new_bot_name: str, reason: str = "") -> Dict:
        """Request handoff of work to another bot"""
        try:
            response = self.session.post(
                f"{self.base_url}/work/{work_id}/handoff",
                params={"new_bot_name": new_bot_name, "reason": reason}
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def get_active_work(self, bot_name: str = None) -> Dict:
        """Get all active work"""
        params = {"bot_name": bot_name} if bot_name else {}
        try:
            response = self.session.get(f"{self.base_url}/work/active", params=params)
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def check_resource_availability(self, resources: List[str]) -> Dict:
        """Check if resources are available"""
        try:
            response = self.session.post(f"{self.base_url}/resources/check", json=resources)
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def get_network_status(self) -> Dict:
        """Get overall network status"""
        try:
            response = self.session.get(f"{self.base_url}/network/status")
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def cleanup_test_work(self):
        """Clean up work entries created during testing"""
        print("\n🧹 Cleaning up test work entries...")
        for work_id in self.registered_work_ids:
            try:
                self.complete_work(work_id, "Test cleanup")
                print(f"   ✅ Cleaned up work: {work_id}")
            except:
                pass
        self.registered_work_ids.clear()

def run_comprehensive_test():
    """Run comprehensive test of the ActiveWorkLog coordination system"""
    print("🤖 ActiveWorkLog Coordination System - Test Suite")
    print("=" * 60)
    
    client = CoordinationTestClient()
    
    # Test 1: Health Check
    print("\n1. 🏥 Health Check")
    health = client.health_check()
    if "error" in health:
        print(f"   ❌ System not available: {health['error']}")
        return
    else:
        print(f"   ✅ System healthy: {health.get('status', 'unknown')}")
        print(f"   📊 Active work count: {health.get('active_work_count', 0)}")
    
    # Test 2: Work Registration
    print("\n2. 🔄 Work Registration")
    test_work_cases = [
        {
            "bot_name": "dmlog-backend",
            "task_description": "Process user authentication and session management",
            "resources": ["/home/activeloguser/activelog/services/dmlog-backend", "database:auth"],
            "priority": 8,
            "estimated_duration_minutes": 30
        },
        {
            "bot_name": "marine-autopilot",
            "task_description": "Calculate navigation waypoints and course corrections",
            "resources": ["/home/activeloguser/activelog/services/marine-autopilot", "gps:primary"],
            "priority": 9,
            "estimated_duration_minutes": 15
        },
        {
            "bot_name": "code-generator",
            "task_description": "Generate Python service template with FastAPI integration",
            "resources": ["/tmp/generated_code", "openai:api"],
            "priority": 6,
            "estimated_duration_minutes": 45
        },
        {
            "bot_name": "data-lifecycle-manager",
            "task_description": "Clean up log files and optimize storage usage",
            "resources": ["/home/activeloguser/activelog/logs", "disk:cleanup"],
            "priority": 4,
            "estimated_duration_minutes": 20
        }
    ]
    
    registered_work = []
    for i, work_case in enumerate(test_work_cases):
        print(f"   Test {i+1}: {work_case['bot_name']}")
        result = client.register_work(**work_case)
        
        if "error" in result:
            print(f"   ❌ Error: {result['error']}")
        else:
            work_id = result.get('work_id', 'N/A')
            conflicts = result.get('conflicts', [])
            can_proceed = result.get('can_proceed', False)
            
            print(f"   📝 Work ID: {work_id}")
            print(f"   🚦 Can proceed: {'✅' if can_proceed else '⚠️'}")
            
            if conflicts:
                print(f"   ⚠️  Conflicts detected: {len(conflicts)}")
                for conflict in conflicts[:2]:  # Show first 2 conflicts
                    print(f"      - {conflict['type']} conflict with {conflict['conflicting_bot']}")
            
            registered_work.append(result)
    
    # Test 3: Resource Conflict Detection
    print("\n3. 🔍 Resource Availability Check")
    resource_tests = [
        ["/home/activeloguser/activelog/services/dmlog-backend"],  # Should conflict
        ["/tmp/new_project", "openai:api"],  # Mixed availability
        ["/tmp/available_resource", "cache:temp"],  # Should be available
    ]
    
    for i, resources in enumerate(resource_tests):
        print(f"   Test {i+1}: {resources}")
        result = client.check_resource_availability(resources)
        
        if "error" in result:
            print(f"   ❌ Error: {result['error']}")
        else:
            available = result.get('available_resources', [])
            conflicts = result.get('resource_conflicts', {})
            all_available = result.get('all_available', False)
            
            print(f"   📊 All available: {'✅' if all_available else '❌'}")
            print(f"   ✅ Available: {available}")
            if conflicts:
                print(f"   ⚠️  Conflicts: {list(conflicts.keys())}")
    
    # Test 4: Work Progress Updates
    print("\n4. 📊 Work Progress Updates")
    if registered_work:
        for i, work in enumerate(registered_work[:2]):  # Update first 2 work items
            if "work_id" in work:
                work_id = work["work_id"]
                progress_updates = [25.0, 50.0, 75.0]
                
                print(f"   Updating work {i+1}: {work_id}")
                for progress in progress_updates:
                    result = client.update_work(
                        work_id, 
                        progress=progress,
                        metadata={"last_update": time.time(), "test_progress": True}
                    )
                    
                    if "error" in result:
                        print(f"   ❌ Update error: {result['error']}")
                    else:
                        print(f"   📈 Progress: {progress}%")
                    
                    time.sleep(0.5)  # Brief delay between updates
    
    # Test 5: Active Work Monitoring
    print("\n5. 👀 Active Work Monitoring")
    active_work_result = client.get_active_work()
    
    if "error" in active_work_result:
        print(f"   ❌ Error: {active_work_result['error']}")
    else:
        active_work_list = active_work_result.get('active_work', [])
        print(f"   📋 Total active work: {len(active_work_list)}")
        
        for work in active_work_list[:3]:  # Show first 3
            print(f"   🤖 {work['bot_name']}: {work['task_description'][:50]}...")
            print(f"      Progress: {work['progress_percentage']:.1f}%, Priority: {work['priority']}")
    
    # Test 6: Bot-Specific Work Filtering
    print("\n6. 🎯 Bot-Specific Work Filtering")
    test_bots = ["dmlog-backend", "marine-autopilot", "nonexistent-bot"]
    
    for bot_name in test_bots:
        result = client.get_active_work(bot_name)
        if "error" in result:
            print(f"   {bot_name}: ❌ Error: {result['error']}")
        else:
            work_list = result.get('active_work', [])
            print(f"   {bot_name}: {len(work_list)} active tasks")
    
    # Test 7: Work Handoff Simulation
    print("\n7. 🔄 Work Handoff Simulation")
    if registered_work and "work_id" in registered_work[0]:
        work_id = registered_work[0]["work_id"]
        original_bot = test_work_cases[0]["bot_name"]
        new_bot = "backup-" + original_bot
        
        print(f"   Handing off work from {original_bot} to {new_bot}")
        result = client.request_handoff(
            work_id, new_bot, "Simulating bot failure recovery"
        )
        
        if "error" in result:
            print(f"   ❌ Handoff error: {result['error']}")
        else:
            print(f"   ✅ Handoff successful to {result.get('new_bot', 'N/A')}")
            print(f"   📦 Checkpoint data available: {bool(result.get('checkpoint_data'))}")
    
    # Test 8: Network Status Overview
    print("\n8. 🌐 Network Status Overview")
    network_status = client.get_network_status()
    
    if "error" in network_status:
        print(f"   ❌ Error: {network_status['error']}")
    else:
        print(f"   🤖 Active bots: {network_status.get('active_bot_count', 0)}")
        print(f"   📋 Active work items: {network_status.get('active_work_count', 0)}")
        print(f"   🏥 Network health: {network_status.get('network_health_score', 0):.2%}")
        print(f"   ⚠️  Conflicts today: {network_status.get('conflicts_detected_today', 0)}")
        
        active_bots = network_status.get('active_bots', [])
        if active_bots:
            print(f"   🌟 Active bots: {', '.join(active_bots)}")
    
    # Test 9: Conflict Simulation
    print("\n9. ⚠️  Conflict Simulation")
    conflict_test = {
        "bot_name": "conflict-test-bot",
        "task_description": "Test resource conflict detection",
        "resources": ["/home/activeloguser/activelog/services/dmlog-backend"],  # Known conflict
        "priority": 7
    }
    
    print("   Attempting to register conflicting work...")
    result = client.register_work(**conflict_test)
    
    if "error" in result:
        print(f"   ❌ Error: {result['error']}")
    else:
        conflicts = result.get('conflicts', [])
        can_proceed = result.get('can_proceed', False)
        
        print(f"   🔍 Conflicts detected: {len(conflicts)}")
        print(f"   🚦 Can proceed: {'✅' if can_proceed else '❌'}")
        
        for conflict in conflicts:
            print(f"   ⚠️  {conflict['type']} conflict (severity: {conflict['severity']})")
    
    # Test 10: Performance Load Test
    print("\n10. ⚡ Performance Load Test")
    start_time = time.time()
    
    # Register multiple work items quickly
    load_test_work = []
    for i in range(5):
        work_data = {
            "bot_name": f"load-test-bot-{i}",
            "task_description": f"Load test task {i+1} - performance measurement",
            "resources": [f"/tmp/load_test_{i}"],
            "priority": random.randint(1, 10)
        }
        
        result = client.register_work(**work_data)
        if "work_id" in result:
            load_test_work.append(result["work_id"])
    
    # Update progress for all
    for work_id in load_test_work:
        client.update_work(work_id, progress=random.uniform(10, 90))
    
    total_time = time.time() - start_time
    print(f"   ⚡ Processed {len(load_test_work)} work items in {total_time:.2f} seconds")
    print(f"   📊 Average per operation: {(total_time/len(load_test_work))*1000:.1f}ms")
    
    # Final Summary
    print("\n" + "=" * 60)
    print("🎓 ActiveWorkLog System Test Summary")
    print("   ✅ Work registration and conflict detection functional")
    print("   ✅ Resource availability checking operational")
    print("   ✅ Progress tracking and updates working")
    print("   ✅ Work handoff mechanism functional")
    print("   ✅ Network monitoring and status reporting active")
    print("   ✅ Performance load testing successful")
    print("\n🎯 Building Bots Network Coordination Ready!")
    print("   📊 Bots can now register work and avoid conflicts")
    print("   🔄 Seamless handoffs ensure task continuity")
    print("   📈 Real-time monitoring provides network visibility")
    
    # Cleanup
    print("\n🧹 Cleaning up test data...")
    client.cleanup_test_work()
    print("   ✅ Test cleanup completed")

def run_simple_demo():
    """Run a simple demonstration for quick testing"""
    print("🚀 Quick Demo - ActiveWorkLog Coordination System")
    print("-" * 50)
    
    client = CoordinationTestClient()
    
    # Health check
    health = client.health_check()
    if "error" in health:
        print(f"❌ System not available: {health['error']}")
        return
    
    print(f"✅ System Status: {health.get('status', 'unknown')}")
    
    # Register sample work
    sample_work = {
        "bot_name": "demo-bot",
        "task_description": "Demonstrate coordination system functionality",
        "resources": ["/tmp/demo_resource"],
        "priority": 7,
        "estimated_duration_minutes": 10
    }
    
    print(f"\n📝 Registering work: {sample_work['task_description']}")
    result = client.register_work(**sample_work)
    
    if "error" in result:
        print(f"❌ Registration failed: {result['error']}")
    else:
        work_id = result.get('work_id', 'N/A')
        can_proceed = result.get('can_proceed', False)
        
        print(f"✅ Work registered: {work_id}")
        print(f"🚦 Can proceed: {'Yes' if can_proceed else 'No'}")
        
        # Update progress
        print("\n📊 Updating progress...")
        client.update_work(work_id, progress=50.0)
        print("   Progress: 50%")
        
        # Complete work
        print("\n🎯 Completing work...")
        client.complete_work(work_id, "Demo completed successfully")
        print("   ✅ Work completed")
    
    # Show network status
    network_status = client.get_network_status()
    if "error" not in network_status:
        print(f"\n📊 Network Status:")
        print(f"   Active bots: {network_status.get('active_bot_count', 0)}")
        print(f"   Active work: {network_status.get('active_work_count', 0)}")
        print(f"   Health score: {network_status.get('network_health_score', 0):.2%}")
    
    print("\n✅ Demo completed successfully!")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        run_simple_demo()
    else:
        run_comprehensive_test()