#!/usr/bin/env python3
"""
Simple API Test Script
Tests the Content Studio API with small tasks
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("\n" + "="*60)
    print("TEST 1: Health Check")
    print("="*60)

    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_status():
    """Test status endpoint"""
    print("\n" + "="*60)
    print("TEST 2: System Status")
    print("="*60)

    try:
        response = requests.get(f"{BASE_URL}/api/status")
        print(f"Status Code: {response.status_code}")
        data = response.json()

        # Print key info
        if "orchestrator" in data:
            print(f"\nOrchestrator Ready: {data['orchestrator'].get('ready')}")

        if "bots" in data:
            print(f"Total Bots: {len(data['bots'])}")

        if "resources" in data:
            print(f"CPU Cores: {data['resources'].get('cpu', {}).get('total_cores')}")
            print(f"GPU Available: {data['resources'].get('gpu', {}).get('available')}")

        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_agents():
    """Test agents endpoint"""
    print("\n" + "="*60)
    print("TEST 3: List All Agents")
    print("="*60)

    try:
        response = requests.get(f"{BASE_URL}/api/agents")
        print(f"Status Code: {response.status_code}")
        data = response.json()

        if "agents" in data:
            print(f"\nTotal Agents: {len(data['agents'])}")
            print("\nAgent List:")
            for agent_id, status in data['agents'].items():
                state = status.get('status', 'unknown')
                print(f"  • {agent_id}: {state}")

        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_small_request():
    """Test with a small request"""
    print("\n" + "="*60)
    print("TEST 4: Small Task Request")
    print("="*60)

    try:
        payload = {
            "message": "Summarize Story 1",
            "user_id": "test_user"
        }

        print(f"\nSending request: {payload['message']}")

        response = requests.post(
            f"{BASE_URL}/api/request",
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")

            if data.get("success"):
                print("\n✅ Request successfully submitted to system!")
                print(f"Project: {data.get('result', {}).get('project')}")
                print(f"Total Tasks: {data.get('result', {}).get('total_tasks')}")
                print(f"Agents Assigned: {data.get('result', {}).get('agents')}")
                return True
            else:
                print(f"\n⚠️ Request failed: {data.get('error')}")
                return False
        else:
            print(f"Error: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print(" "*20 + "🧪 API TEST SUITE")
    print("="*70)
    print("\nTesting Content Studio API at:", BASE_URL)
    print("\nMake sure the server is running with: python run_studio.py")

    # Wait a moment for user to read
    time.sleep(2)

    results = []

    # Run tests
    results.append(("Health Check", test_health()))
    time.sleep(1)

    results.append(("System Status", test_status()))
    time.sleep(1)

    results.append(("List Agents", test_agents()))
    time.sleep(1)

    results.append(("Small Request", test_small_request()))

    # Print summary
    print("\n" + "="*70)
    print(" "*25 + "📊 TEST SUMMARY")
    print("="*70 + "\n")

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")

    total = len(results)
    passed_count = sum(1 for _, p in results if p)

    print(f"\nTotal: {passed_count}/{total} tests passed")

    if passed_count == total:
        print("\n🎉 All tests passed! System is working correctly.")
    else:
        print(f"\n⚠️ {total - passed_count} test(s) failed. Check errors above.")

    print("\n" + "="*70)


if __name__ == "__main__":
    main()
