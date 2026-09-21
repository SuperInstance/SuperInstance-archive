"""
Load test runner and performance analysis
Automates load testing scenarios and analyzes results
"""

import os
import sys
import subprocess
import json
import time
import argparse
from datetime import datetime
import requests
import yaml
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class LoadTestRunner:
    """Manages load test execution and analysis"""
    
    def __init__(self, host="http://localhost:8000", results_dir="load_test_results"):
        self.host = host
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)
        
        # Performance thresholds
        self.thresholds = {
            "max_avg_response_time": 2000,  # ms
            "max_95th_percentile": 5000,    # ms
            "max_failure_rate": 0.05,       # 5%
            "min_rps": 10                   # requests/second
        }
    
    def run_scenario(self, scenario_name, users, spawn_rate, run_time, user_classes=None):
        """Run a specific load test scenario"""
        
        print(f"\n{'='*60}")
        print(f"Running Load Test Scenario: {scenario_name}")
        print(f"Users: {users}, Spawn Rate: {spawn_rate}, Duration: {run_time}")
        print(f"Target: {self.host}")
        print(f"{'='*60}\n")
        
        # Prepare test environment
        self._prepare_test_environment()
        
        # Generate timestamp for this test run
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_id = f"{scenario_name}_{timestamp}"
        
        # Prepare Locust command
        locust_file = Path(__file__).parent / "locustfile.py"
        results_file = self.results_dir / f"{test_id}_stats.json"
        csv_prefix = self.results_dir / f"{test_id}"
        
        cmd = [
            "locust",
            "-f", str(locust_file),
            "--host", self.host,
            "--users", str(users),
            "--spawn-rate", str(spawn_rate),
            "--run-time", run_time,
            "--headless",
            "--print-stats",
            "--html", str(self.results_dir / f"{test_id}_report.html"),
            "--csv", str(csv_prefix),
            "--csv-full-history"
        ]
        
        if user_classes:
            for user_class in user_classes:
                cmd.extend(["--user-class", user_class])
        
        # Run the test
        try:
            print("Starting load test...")
            start_time = time.time()
            
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._parse_time_to_seconds(run_time) + 120  # Add 2 min buffer
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"Load test completed in {duration:.2f} seconds")
            
            # Parse and analyze results
            results = self._parse_locust_output(process.stdout, process.stderr)
            results.update({
                "scenario": scenario_name,
                "timestamp": timestamp,
                "duration": duration,
                "parameters": {
                    "users": users,
                    "spawn_rate": spawn_rate,
                    "run_time": run_time,
                    "host": self.host
                }
            })
            
            # Save results
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            # Analyze performance
            analysis = self._analyze_performance(results)
            
            # Generate report
            self._generate_report(test_id, results, analysis)
            
            return {
                "test_id": test_id,
                "results": results,
                "analysis": analysis,
                "passed": analysis["overall_pass"]
            }
            
        except subprocess.TimeoutExpired:
            print("Load test timed out!")
            return {"error": "Test timed out"}
        except Exception as e:
            print(f"Load test failed: {e}")
            return {"error": str(e)}
    
    def run_all_scenarios(self):
        """Run all predefined load test scenarios"""
        
        scenarios = [
            {
                "name": "light_load",
                "users": 10,
                "spawn_rate": 2,
                "run_time": "3m",
                "description": "Light load with 10 concurrent users"
            },
            {
                "name": "normal_load", 
                "users": 50,
                "spawn_rate": 5,
                "run_time": "5m",
                "description": "Normal load with 50 concurrent users"
            },
            {
                "name": "heavy_load",
                "users": 100,
                "spawn_rate": 10,
                "run_time": "8m",
                "description": "Heavy load with 100 concurrent users"
            },
            {
                "name": "stress_test",
                "users": 200,
                "spawn_rate": 20,
                "run_time": "10m",
                "description": "Stress test with 200 concurrent users"
            }
        ]
        
        results_summary = []
        
        for scenario in scenarios:
            print(f"\n{scenario['description']}")
            result = self.run_scenario(
                scenario["name"],
                scenario["users"],
                scenario["spawn_rate"], 
                scenario["run_time"]
            )
            
            results_summary.append({
                "scenario": scenario["name"],
                "passed": result.get("passed", False),
                "test_id": result.get("test_id"),
                "error": result.get("error")
            })
            
            # Wait between scenarios
            if scenario != scenarios[-1]:
                print("Waiting 60 seconds before next scenario...")
                time.sleep(60)
        
        # Generate summary report
        self._generate_summary_report(results_summary)
        
        return results_summary
    
    def run_custom_scenario(self, config_file):
        """Run custom scenario from configuration file"""
        
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        scenario = config.get("scenario", {})
        
        return self.run_scenario(
            scenario.get("name", "custom"),
            scenario.get("users", 10),
            scenario.get("spawn_rate", 2),
            scenario.get("run_time", "5m"),
            scenario.get("user_classes")
        )
    
    def _prepare_test_environment(self):
        """Prepare the test environment"""
        
        # Check if services are running
        try:
            response = requests.get(f"{self.host}/health", timeout=10)
            if response.status_code != 200:
                print("Warning: Health check failed - services may not be ready")
        except requests.RequestException:
            print("Warning: Could not connect to target host")
        
        # Clean up any previous test data if needed
        # This could include clearing test databases, caches, etc.
        print("Test environment prepared")
    
    def _parse_time_to_seconds(self, time_str):
        """Parse time string (e.g., '5m', '30s') to seconds"""
        if time_str.endswith('s'):
            return int(time_str[:-1])
        elif time_str.endswith('m'):
            return int(time_str[:-1]) * 60
        elif time_str.endswith('h'):
            return int(time_str[:-1]) * 3600
        else:
            return int(time_str)  # Assume seconds
    
    def _parse_locust_output(self, stdout, stderr):
        """Parse Locust output to extract statistics"""
        
        results = {
            "stats": {},
            "errors": [],
            "output": stdout,
            "stderr": stderr
        }
        
        # Parse statistics from stdout
        lines = stdout.split('\n')
        
        for line in lines:
            # Look for request statistics
            if 'Aggregated' in line and 'requests' in line:
                # Parse aggregated stats line
                # This is a simplified parser - in production you'd want more robust parsing
                parts = line.split()
                if len(parts) >= 10:
                    try:
                        results["stats"] = {
                            "total_requests": int(parts[2]),
                            "failures": int(parts[3]),
                            "avg_response_time": float(parts[5]),
                            "min_response_time": float(parts[6]),
                            "max_response_time": float(parts[7]),
                            "rps": float(parts[9]) if len(parts) > 9 else 0
                        }
                    except (ValueError, IndexError):
                        pass
            
            # Look for error information
            if 'ERROR' in line or 'FAILED' in line:
                results["errors"].append(line.strip())
        
        return results
    
    def _analyze_performance(self, results):
        """Analyze performance results against thresholds"""
        
        stats = results.get("stats", {})
        
        analysis = {
            "checks": [],
            "warnings": [],
            "errors": [],
            "overall_pass": True
        }
        
        # Check average response time
        avg_response_time = stats.get("avg_response_time", 0)
        if avg_response_time > self.thresholds["max_avg_response_time"]:
            analysis["errors"].append(
                f"Average response time {avg_response_time:.2f}ms exceeds threshold "
                f"{self.thresholds['max_avg_response_time']}ms"
            )
            analysis["overall_pass"] = False
        else:
            analysis["checks"].append(
                f"Average response time {avg_response_time:.2f}ms within threshold"
            )
        
        # Check failure rate
        total_requests = stats.get("total_requests", 0)
        failures = stats.get("failures", 0)
        failure_rate = failures / max(total_requests, 1)
        
        if failure_rate > self.thresholds["max_failure_rate"]:
            analysis["errors"].append(
                f"Failure rate {failure_rate:.2%} exceeds threshold "
                f"{self.thresholds['max_failure_rate']:.2%}"
            )
            analysis["overall_pass"] = False
        else:
            analysis["checks"].append(
                f"Failure rate {failure_rate:.2%} within threshold"
            )
        
        # Check RPS
        rps = stats.get("rps", 0)
        if rps < self.thresholds["min_rps"]:
            analysis["warnings"].append(
                f"RPS {rps:.2f} below expected threshold {self.thresholds['min_rps']}"
            )
        else:
            analysis["checks"].append(
                f"RPS {rps:.2f} meets threshold"
            )
        
        # Check for errors in test execution
        test_errors = results.get("errors", [])
        if test_errors:
            analysis["errors"].extend(test_errors)
            analysis["overall_pass"] = False
        
        return analysis
    
    def _generate_report(self, test_id, results, analysis):
        """Generate detailed test report"""
        
        report_file = self.results_dir / f"{test_id}_analysis.txt"
        
        with open(report_file, 'w') as f:
            f.write(f"Load Test Analysis Report\n")
            f.write(f"={'='*50}\n\n")
            f.write(f"Test ID: {test_id}\n")
            f.write(f"Timestamp: {results.get('timestamp', 'N/A')}\n")
            f.write(f"Duration: {results.get('duration', 0):.2f} seconds\n")
            f.write(f"Scenario: {results.get('scenario', 'N/A')}\n\n")
            
            # Parameters
            params = results.get('parameters', {})
            f.write(f"Test Parameters:\n")
            f.write(f"  Users: {params.get('users', 'N/A')}\n")
            f.write(f"  Spawn Rate: {params.get('spawn_rate', 'N/A')}\n")
            f.write(f"  Run Time: {params.get('run_time', 'N/A')}\n")
            f.write(f"  Host: {params.get('host', 'N/A')}\n\n")
            
            # Statistics
            stats = results.get('stats', {})
            f.write(f"Performance Statistics:\n")
            f.write(f"  Total Requests: {stats.get('total_requests', 'N/A')}\n")
            f.write(f"  Failures: {stats.get('failures', 'N/A')}\n")
            f.write(f"  Average Response Time: {stats.get('avg_response_time', 'N/A'):.2f}ms\n")
            f.write(f"  Min Response Time: {stats.get('min_response_time', 'N/A'):.2f}ms\n")
            f.write(f"  Max Response Time: {stats.get('max_response_time', 'N/A'):.2f}ms\n")
            f.write(f"  Requests/Second: {stats.get('rps', 'N/A'):.2f}\n\n")
            
            # Analysis
            f.write(f"Performance Analysis:\n")
            f.write(f"  Overall Result: {'PASS' if analysis['overall_pass'] else 'FAIL'}\n\n")
            
            if analysis['checks']:
                f.write(f"  Checks Passed:\n")
                for check in analysis['checks']:
                    f.write(f"    ✓ {check}\n")
                f.write("\n")
            
            if analysis['warnings']:
                f.write(f"  Warnings:\n")
                for warning in analysis['warnings']:
                    f.write(f"    ⚠ {warning}\n")
                f.write("\n")
            
            if analysis['errors']:
                f.write(f"  Errors:\n")
                for error in analysis['errors']:
                    f.write(f"    ✗ {error}\n")
                f.write("\n")
        
        print(f"Detailed report saved to: {report_file}")
    
    def _generate_summary_report(self, results_summary):
        """Generate summary report for all scenarios"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_file = self.results_dir / f"load_test_summary_{timestamp}.txt"
        
        with open(summary_file, 'w') as f:
            f.write(f"Load Test Summary Report\n")
            f.write(f"{'='*60}\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Total Scenarios: {len(results_summary)}\n\n")
            
            passed_count = sum(1 for r in results_summary if r.get('passed', False))
            f.write(f"Results: {passed_count}/{len(results_summary)} scenarios passed\n\n")
            
            for result in results_summary:
                status = "PASS" if result.get('passed', False) else "FAIL"
                error = f" ({result['error']})" if result.get('error') else ""
                f.write(f"  {result['scenario']}: {status}{error}\n")
            
            f.write(f"\nOverall Result: {'PASS' if passed_count == len(results_summary) else 'FAIL'}\n")
        
        print(f"Summary report saved to: {summary_file}")
        
        # Print summary to console
        print(f"\n{'='*60}")
        print(f"LOAD TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Total scenarios: {len(results_summary)}")
        print(f"Passed: {passed_count}")
        print(f"Failed: {len(results_summary) - passed_count}")
        
        for result in results_summary:
            status = "✓" if result.get('passed', False) else "✗"
            print(f"  {status} {result['scenario']}")
        
        overall_result = "PASS" if passed_count == len(results_summary) else "FAIL"
        print(f"\nOVERALL RESULT: {overall_result}")
        print(f"{'='*60}")


def main():
    """Main entry point for load test runner"""
    
    parser = argparse.ArgumentParser(description="ActiveLog Load Test Runner")
    parser.add_argument("--host", default="http://localhost:8000", help="Target host URL")
    parser.add_argument("--scenario", help="Run specific scenario (light_load, normal_load, heavy_load, stress_test)")
    parser.add_argument("--users", type=int, help="Number of concurrent users")
    parser.add_argument("--spawn-rate", type=int, help="User spawn rate per second")
    parser.add_argument("--run-time", help="Test duration (e.g., 5m, 30s)")
    parser.add_argument("--config", help="Load test configuration file")
    parser.add_argument("--all", action="store_true", help="Run all predefined scenarios")
    parser.add_argument("--results-dir", default="load_test_results", help="Results directory")
    
    args = parser.parse_args()
    
    runner = LoadTestRunner(host=args.host, results_dir=args.results_dir)
    
    if args.all:
        # Run all scenarios
        results = runner.run_all_scenarios()
        
        # Exit with error code if any scenario failed
        if not all(r.get('passed', False) for r in results):
            sys.exit(1)
    
    elif args.config:
        # Run custom scenario from config file
        result = runner.run_custom_scenario(args.config)
        
        if not result.get('passed', False):
            sys.exit(1)
    
    elif args.scenario and args.users and args.spawn_rate and args.run_time:
        # Run specific scenario
        result = runner.run_scenario(args.scenario, args.users, args.spawn_rate, args.run_time)
        
        if not result.get('passed', False):
            sys.exit(1)
    
    else:
        print("Error: Must specify either --all, --config, or all of --scenario, --users, --spawn-rate, --run-time")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()