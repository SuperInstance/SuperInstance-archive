#!/usr/bin/env python3
"""
Runtime Optimizer Service Demo

Demonstrates key functionality of the runtime optimization service.
"""

import asyncio
import aiohttp
import json
import time

BASE_URL = "http://localhost:8431"

async def test_endpoints():
    """Test key service endpoints"""
    async with aiohttp.ClientSession() as session:
        
        print("🚀 Runtime Optimizer Service Demo")
        print("=" * 50)
        
        # 1. Health Check
        print("\n1. Health Check:")
        try:
            async with session.get(f"{BASE_URL}/health") as resp:
                if resp.status == 200:
                    health = await resp.json()
                    print(f"   ✅ Service Status: {health['status']}")
                    print(f"   🔧 Subsystems: {health['subsystems']}")
                else:
                    print(f"   ❌ Health check failed: {resp.status}")
        except Exception as e:
            print(f"   ❌ Connection error: {e}")
            return
        
        # 2. System Status Summary
        print("\n2. System Status Summary:")
        try:
            async with session.get(f"{BASE_URL}/status/summary") as resp:
                summary = await resp.json()
                print(f"   🎯 Resource Tier: {summary.get('resource_tier', 'unknown')}")
                print(f"   🌐 Network Tier: {summary.get('network_tier', 'unknown')}")
                print(f"   📊 CPU Usage: {summary.get('cpu_percent', 0):.1f}%")
                print(f"   💾 Memory Usage: {summary.get('memory_percent', 0):.1f}%")
                print(f"   📋 Active Tasks: {summary.get('active_tasks', 0)}")
                print(f"   ✨ Features Enabled: {summary.get('enabled_features', 0)}/{summary.get('total_features', 0)}")
        except Exception as e:
            print(f"   ❌ Error getting summary: {e}")
        
        # 3. Schedule a Demo Task
        print("\n3. Task Scheduling:")
        task_request = {
            "task_id": "demo_task_001",
            "function_name": "demo_processing",
            "priority": "normal",
            "resource_requirements": {"cpu": 20.0, "memory": 10.0},
            "estimated_duration": 5.0,
            "args": ["test_data"],
            "kwargs": {"mode": "demo"}
        }
        
        try:
            async with session.post(f"{BASE_URL}/resource-manager/tasks/schedule", 
                                  json=task_request) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"   ✅ Task scheduled: {result['task_id']}")
                    
                    # Check task status
                    await asyncio.sleep(2)
                    async with session.get(f"{BASE_URL}/resource-manager/tasks/{result['task_id']}") as status_resp:
                        if status_resp.status == 200:
                            status = await status_resp.json()
                            print(f"   📊 Task Status: {status.get('status', 'unknown')}")
                        else:
                            print(f"   📊 Task Status: Running or completed")
                else:
                    print(f"   ❌ Task scheduling failed: {resp.status}")
        except Exception as e:
            print(f"   ❌ Error scheduling task: {e}")
        
        # 4. Feature Scaling Demo
        print("\n4. Feature Scaling:")
        try:
            async with session.get(f"{BASE_URL}/feature-scaling/status") as resp:
                if resp.status == 200:
                    features = await resp.json()
                    print(f"   📈 Current Tier: {features.get('current_tier', 'unknown')}")
                    print(f"   🔄 Auto Scaling: {'enabled' if features.get('auto_scaling_enabled') else 'disabled'}")
                    
                    feature_list = features.get('features', {})
                    enabled_count = sum(1 for f in feature_list.values() if f.get('enabled', False))
                    print(f"   ✨ Features: {enabled_count}/{len(feature_list)} enabled")
                    
                    # Show a few key features
                    key_features = ['animations', 'textures', 'visual_effects']
                    for feature_name in key_features:
                        if feature_name in feature_list:
                            f = feature_list[feature_name]
                            quality = f.get('quality_level', 0)
                            state = f.get('current_state', 'unknown')
                            print(f"     • {feature_name}: {quality:.1f} quality ({state})")
                else:
                    print(f"   ❌ Feature status failed: {resp.status}")
        except Exception as e:
            print(f"   ❌ Error getting feature status: {e}")
        
        # 5. Network Adaptation Status
        print("\n5. Network Adaptation:")
        try:
            async with session.get(f"{BASE_URL}/network-adaptation/status") as resp:
                if resp.status == 200:
                    network = await resp.json()
                    print(f"   🌐 Tier: {network.get('current_tier', 'unknown')}")
                    print(f"   🔄 Sync Mode: {network.get('sync_mode', 'unknown')}")
                    
                    metrics = network.get('current_metrics', {})
                    print(f"   📊 Bandwidth: {metrics.get('bandwidth_mbps', 0):.1f} Mbps")
                    print(f"   ⏱️  Latency: {metrics.get('latency_ms', 0):.1f} ms")
                    
                    # CDN info
                    cdn_info = network.get('cdn_info', {})
                    if cdn_info:
                        print(f"   🌍 CDN Region: {cdn_info.get('selected_region', 'unknown')}")
                        print(f"   ⚡ CDN Latency: {cdn_info.get('latency_ms', 0):.1f} ms")
                else:
                    print(f"   ❌ Network status failed: {resp.status}")
        except Exception as e:
            print(f"   ❌ Error getting network status: {e}")
        
        # 6. Cost Optimization
        print("\n6. Cost Optimization:")
        try:
            async with session.get(f"{BASE_URL}/cost-optimization/status") as resp:
                if resp.status == 200:
                    cost = await resp.json()
                    current_costs = cost.get('current_costs', {})
                    daily = current_costs.get('daily', {})
                    monthly = current_costs.get('monthly', {})
                    
                    print(f"   💰 Daily Cost: ${daily.get('total_cost', 0):.4f}")
                    print(f"   📅 Monthly Cost: ${monthly.get('total_cost', 0):.4f}")
                    
                    budgets = cost.get('budgets', {})
                    print(f"   📊 Active Budgets: {len(budgets)}")
                    
                    suggestions = cost.get('optimization_suggestions', [])
                    print(f"   💡 Optimization Suggestions: {len(suggestions)}")
                else:
                    print(f"   ❌ Cost status failed: {resp.status}")
        except Exception as e:
            print(f"   ❌ Error getting cost status: {e}")
        
        # 7. Monitoring Dashboard
        print("\n7. Monitoring Dashboard:")
        try:
            async with session.get(f"{BASE_URL}/monitoring/dashboard") as resp:
                if resp.status == 200:
                    monitoring = await resp.json()
                    health = monitoring.get('health', {})
                    print(f"   🏥 Overall Health: {health.get('overall_status', 'unknown')}")
                    
                    individual_checks = health.get('individual_checks', {})
                    healthy_checks = sum(1 for check in individual_checks.values() 
                                       if check.get('status') == 'healthy')
                    print(f"   ✅ Health Checks: {healthy_checks}/{len(individual_checks)} healthy")
                    
                    alerts = monitoring.get('alerts', {})
                    print(f"   🚨 Active Alerts: {alerts.get('active_alerts', 0)}")
                    
                    uptime = monitoring.get('monitoring_info', {}).get('uptime_human', 'unknown')
                    print(f"   ⏰ Uptime: {uptime}")
                else:
                    print(f"   ❌ Monitoring dashboard failed: {resp.status}")
        except Exception as e:
            print(f"   ❌ Error getting monitoring data: {e}")
        
        # 8. Trigger Manual Optimization
        print("\n8. Manual Optimization:")
        try:
            async with session.post(f"{BASE_URL}/optimize/trigger") as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"   🔧 Optimization triggered successfully")
                    print(f"   📊 Resource tier: {result.get('resource_tier', 'unknown')}")
                    print(f"   💡 Cost suggestions: {result.get('cost_suggestions_count', 0)}")
                    print(f"   🌐 Network recommendations: {result.get('network_recommendations_count', 0)}")
                else:
                    print(f"   ❌ Optimization trigger failed: {resp.status}")
        except Exception as e:
            print(f"   ❌ Error triggering optimization: {e}")
        
        print("\n" + "=" * 50)
        print("✅ Demo completed successfully!")
        print(f"🌐 Service running on: {BASE_URL}")
        print("📖 Check README.md for full API documentation")

if __name__ == "__main__":
    asyncio.run(test_endpoints())