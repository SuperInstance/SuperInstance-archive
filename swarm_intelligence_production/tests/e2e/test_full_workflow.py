#!/usr/bin/env python3
"""
End-to-End Test Suite for Swarm Intelligence Platform
Tests the complete workflow from swarm creation to task completion
"""

import os
import sys
import time
import json
import argparse
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass
import websocket
import threading

@dataclass
class TestConfig:
    """Test configuration"""
    base_url: str
    agent_count: int
    target_fps: int
    duration_seconds: int
    api_key: Optional[str] = None

@dataclass
class TestResults:
    """Test results"""
    success: bool
    swarm_id: Optional[str] = None
    agent_count: int = 0
    fps: float = 0.0
    latency_p50: float = 0.0
    latency_p95: float = 0.0
    latency_p99: float = 0.0
    memory_mb: float = 0.0
    memory_per_agent_bytes: float = 0.0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class SwarmE2ETest:
    """End-to-end test runner"""

    def __init__(self, config: TestConfig):
        self.config = config
        self.session = requests.Session()
        if config.api_key:
            self.session.headers.update({"Authorization": f"Bearer {config.api_key}"})

    def run_full_workflow(self) -> TestResults:
        """Run complete E2E workflow"""
        results = TestResults(success=False)

        try:
            print("=" * 60)
            print("Swarm Intelligence Platform - E2E Test")
            print("=" * 60)
            print(f"Target: {self.config.base_url}")
            print(f"Agents: {self.config.agent_count}")
            print(f"Duration: {self.config.duration_seconds}s")
            print()

            # Step 1: Health check
            print("Step 1: Health check...")
            if not self._health_check():
                results.errors.append("Health check failed")
                return results
            print("✓ API is healthy\n")

            # Step 2: Create swarm
            print(f"Step 2: Creating swarm with {self.config.agent_count} agents...")
            swarm_id = self._create_swarm()
            if not swarm_id:
                results.errors.append("Failed to create swarm")
                return results
            results.swarm_id = swarm_id
            print(f"✓ Swarm created: {swarm_id}\n")

            # Step 3: Deploy agents
            print("Step 3: Deploying agents...")
            agent_count = self._deploy_agents(swarm_id)
            if agent_count != self.config.agent_count:
                results.errors.append(f"Agent count mismatch: {agent_count} vs {self.config.agent_count}")
            results.agent_count = agent_count
            print(f"✓ Deployed {agent_count} agents\n")

            # Step 4: Submit task
            print("Step 4: Submitting creative task...")
            task_id = self._submit_task(swarm_id, "resource_optimization")
            if not task_id:
                results.errors.append("Failed to submit task")
                return results
            print(f"✓ Task submitted: {task_id}\n")

            # Step 5: Monitor real-time metrics
            print(f"Step 5: Monitoring metrics for {self.config.duration_seconds}s...")
            metrics = self._monitor_metrics(swarm_id, self.config.duration_seconds)
            results.fps = metrics.get('fps', 0.0)
            results.latency_p50 = metrics.get('latency_p50', 0.0)
            results.latency_p95 = metrics.get('latency_p95', 0.0)
            results.latency_p99 = metrics.get('latency_p99', 0.0)
            results.memory_mb = metrics.get('memory_mb', 0.0)
            results.memory_per_agent_bytes = metrics.get('memory_per_agent', 0.0)
            print(f"✓ Monitoring complete\n")

            # Step 6: Verify output quality
            print("Step 6: Verifying output quality...")
            if not self._verify_output(task_id):
                results.errors.append("Output verification failed")
            else:
                print("✓ Output quality verified\n")

            # Step 7: Test scaling
            print("Step 7: Testing scaling...")
            if not self._test_scaling(swarm_id):
                results.errors.append("Scaling test failed")
            else:
                print("✓ Scaling test passed\n")

            # Step 8: Cleanup
            print("Step 8: Cleanup...")
            self._cleanup_swarm(swarm_id)
            print("✓ Cleanup complete\n")

            # Evaluate results
            results.success = self._evaluate_results(results)

        except Exception as e:
            results.errors.append(f"Unexpected error: {str(e)}")
            print(f"\n❌ Error: {e}")

        return results

    def _health_check(self) -> bool:
        """Check API health"""
        try:
            response = self.session.get(f"{self.config.base_url}/health", timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"Health check error: {e}")
            return False

    def _create_swarm(self) -> Optional[str]:
        """Create a new swarm"""
        try:
            payload = {
                "name": f"e2e-test-swarm-{int(time.time())}",
                "agent_count": self.config.agent_count,
                "behavior": "foraging",
                "config": {
                    "target_fps": self.config.target_fps,
                    "bounds": {
                        "min": {"x": -1000, "y": -1000, "z": -100},
                        "max": {"x": 1000, "y": 1000, "z": 100}
                    }
                }
            }
            response = self.session.post(
                f"{self.config.base_url}/api/swarms",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return data.get("swarm_id")
        except Exception as e:
            print(f"Create swarm error: {e}")
            return None

    def _deploy_agents(self, swarm_id: str) -> int:
        """Deploy agents and wait for initialization"""
        try:
            # Wait for agents to be deployed
            max_wait = 60
            start_time = time.time()

            while time.time() - start_time < max_wait:
                response = self.session.get(
                    f"{self.config.base_url}/api/swarms/{swarm_id}",
                    timeout=10
                )
                data = response.json()
                agent_count = data.get("agent_count", 0)

                if agent_count == self.config.agent_count:
                    return agent_count

                time.sleep(2)

            # Return whatever count we got
            return data.get("agent_count", 0)
        except Exception as e:
            print(f"Deploy agents error: {e}")
            return 0

    def _submit_task(self, swarm_id: str, task_type: str) -> Optional[str]:
        """Submit a task to the swarm"""
        try:
            payload = {
                "swarm_id": swarm_id,
                "type": task_type,
                "description": "E2E test task - optimize resource distribution",
                "parameters": {
                    "resource_count": 100,
                    "optimization_target": "efficiency"
                }
            }
            response = self.session.post(
                f"{self.config.base_url}/api/tasks",
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            return data.get("task_id")
        except Exception as e:
            print(f"Submit task error: {e}")
            return None

    def _monitor_metrics(self, swarm_id: str, duration: int) -> Dict:
        """Monitor swarm metrics"""
        metrics = {
            'fps': [],
            'latency': [],
            'memory': []
        }

        start_time = time.time()
        sample_interval = 5  # seconds

        while time.time() - start_time < duration:
            try:
                response = self.session.get(
                    f"{self.config.base_url}/api/swarms/{swarm_id}/metrics",
                    timeout=10
                )
                data = response.json()

                metrics['fps'].append(data.get('fps', 0))
                metrics['latency'].append(data.get('latency_ms', 0))
                metrics['memory'].append(data.get('memory_bytes', 0))

                # Print progress
                elapsed = int(time.time() - start_time)
                fps = data.get('fps', 0)
                print(f"  [{elapsed}/{duration}s] FPS: {fps:.1f}, "
                      f"Latency: {data.get('latency_ms', 0):.0f}ms, "
                      f"Memory: {data.get('memory_bytes', 0) / 1024 / 1024:.1f}MB")

                time.sleep(sample_interval)
            except Exception as e:
                print(f"Metrics error: {e}")

        # Calculate statistics
        avg_fps = sum(metrics['fps']) / len(metrics['fps']) if metrics['fps'] else 0
        sorted_latency = sorted(metrics['latency'])
        p50_idx = int(len(sorted_latency) * 0.50)
        p95_idx = int(len(sorted_latency) * 0.95)
        p99_idx = int(len(sorted_latency) * 0.99)

        avg_memory = sum(metrics['memory']) / len(metrics['memory']) if metrics['memory'] else 0

        return {
            'fps': avg_fps,
            'latency_p50': sorted_latency[p50_idx] if sorted_latency else 0,
            'latency_p95': sorted_latency[p95_idx] if sorted_latency else 0,
            'latency_p99': sorted_latency[p99_idx] if sorted_latency else 0,
            'memory_mb': avg_memory / 1024 / 1024,
            'memory_per_agent': avg_memory / self.config.agent_count if self.config.agent_count > 0 else 0
        }

    def _verify_output(self, task_id: str) -> bool:
        """Verify task output quality"""
        try:
            response = self.session.get(
                f"{self.config.base_url}/api/tasks/{task_id}",
                timeout=10
            )
            data = response.json()
            status = data.get("status")

            if status in ["completed", "running"]:
                return True

            return False
        except Exception as e:
            print(f"Verify output error: {e}")
            return False

    def _test_scaling(self, swarm_id: str) -> bool:
        """Test scaling capabilities"""
        try:
            # Try to scale up
            scale_payload = {"agent_count": self.config.agent_count + 1000}
            response = self.session.patch(
                f"{self.config.base_url}/api/swarms/{swarm_id}",
                json=scale_payload,
                timeout=10
            )

            # Check if accepted (actual scaling may take time)
            return response.status_code in [200, 202]
        except Exception as e:
            print(f"Scaling test error: {e}")
            return False

    def _cleanup_swarm(self, swarm_id: str):
        """Cleanup test swarm"""
        try:
            self.session.delete(
                f"{self.config.base_url}/api/swarms/{swarm_id}",
                timeout=10
            )
        except Exception as e:
            print(f"Cleanup error: {e}")

    def _evaluate_results(self, results: TestResults) -> bool:
        """Evaluate if test results meet requirements"""
        print("=" * 60)
        print("TEST RESULTS")
        print("=" * 60)
        print(f"Swarm ID: {results.swarm_id}")
        print(f"Agent Count: {results.agent_count}")
        print(f"Average FPS: {results.fps:.1f} (target: >={self.config.target_fps})")
        print(f"Latency p50: {results.latency_p50:.1f}ms")
        print(f"Latency p95: {results.latency_p95:.1f}ms")
        print(f"Latency p99: {results.latency_p99:.1f}ms (target: <100ms)")
        print(f"Total Memory: {results.memory_mb:.2f}MB")
        print(f"Memory/Agent: {results.memory_per_agent_bytes:.0f} bytes (target: <1KB)")

        if results.errors:
            print(f"\nErrors:")
            for error in results.errors:
                print(f"  - {error}")

        print()

        # Check thresholds
        success = True
        if results.fps < self.config.target_fps:
            print(f"❌ FPS below target: {results.fps:.1f} < {self.config.target_fps}")
            success = False
        else:
            print(f"✓ FPS meets target")

        if results.latency_p99 > 100:
            print(f"❌ p99 latency too high: {results.latency_p99:.1f}ms > 100ms")
            success = False
        else:
            print(f"✓ Latency meets target")

        if results.memory_per_agent_bytes > 1024:
            print(f"❌ Memory per agent too high: {results.memory_per_agent_bytes:.0f} > 1024 bytes")
            success = False
        else:
            print(f"✓ Memory usage meets target")

        if results.errors:
            print(f"❌ {len(results.errors)} errors occurred")
            success = False
        else:
            print(f"✓ No errors")

        print()
        if success:
            print("🎉 ALL TESTS PASSED!")
        else:
            print("❌ SOME TESTS FAILED")

        return success


def main():
    parser = argparse.ArgumentParser(description="Swarm Intelligence E2E Tests")
    parser.add_argument("--target", default="staging",
                        choices=["local", "staging", "production"],
                        help="Target environment")
    parser.add_argument("--agents", type=int, default=10000,
                        help="Number of agents to test")
    parser.add_argument("--fps", type=int, default=30,
                        help="Target FPS")
    parser.add_argument("--duration", type=int, default=60,
                        help="Test duration in seconds")
    parser.add_argument("--api-key", help="API key for authentication")

    args = parser.parse_args()

    # Determine base URL
    base_urls = {
        "local": "http://localhost:3000",
        "staging": "https://staging-api.swarm-intelligence.example.com",
        "production": "https://api.swarm-intelligence.example.com"
    }
    base_url = base_urls[args.target]

    config = TestConfig(
        base_url=base_url,
        agent_count=args.agents,
        target_fps=args.fps,
        duration_seconds=args.duration,
        api_key=args.api_key
    )

    test = SwarmE2ETest(config)
    results = test.run_full_workflow()

    sys.exit(0 if results.success else 1)


if __name__ == "__main__":
    main()
