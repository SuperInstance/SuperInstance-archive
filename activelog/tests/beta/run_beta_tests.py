#!/usr/bin/env python3
"""
ActiveLog Beta Integration Test Runner
Comprehensive test orchestration for the beta integration test suite
"""

import os
import sys
import argparse
import asyncio
import subprocess
import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml
import concurrent.futures

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class BetaTestRunner:
    """Beta integration test runner with advanced orchestration capabilities"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config = self.load_config(config_file)
        self.test_results = {}
        self.start_time = None
        self.end_time = None
        
    def load_config(self, config_file: Optional[str] = None) -> Dict[str, Any]:
        """Load test configuration"""
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return yaml.safe_load(f)
        
        # Default configuration
        return {
            'test_suites': {
                'cross_app_orders': {
                    'file': 'test_cross_app_orders.py',
                    'priority': 1,
                    'timeout': 300,
                    'dependencies': ['services_health_check']
                },
                'user_journey': {
                    'file': 'test_user_journey.py',
                    'priority': 1,
                    'timeout': 600,
                    'dependencies': ['services_health_check']
                },
                'payment_flow': {
                    'file': 'test_payment_flow.py',
                    'priority': 2,
                    'timeout': 300,
                    'dependencies': ['user_journey']
                },
                'migration_tools': {
                    'file': 'test_migration_tools.py',
                    'priority': 2,
                    'timeout': 900,
                    'dependencies': ['services_health_check']
                },
                'compute_marketplace': {
                    'file': 'test_compute_marketplace.py',
                    'priority': 3,
                    'timeout': 600,
                    'dependencies': ['payment_flow']
                },
                'content_pipeline': {
                    'file': 'test_content_pipeline.py',
                    'priority': 3,
                    'timeout': 1200,
                    'dependencies': ['services_health_check']
                },
                'game_engine_integration': {
                    'file': 'test_game_engine_integration.py',
                    'priority': 4,
                    'timeout': 900,
                    'dependencies': ['content_pipeline']
                },
                'adult_learning_adaptations': {
                    'file': 'test_adult_learning_adaptations.py',
                    'priority': 4,
                    'timeout': 600,
                    'dependencies': ['services_health_check']
                }
            },
            'services': {
                'health_check_urls': [
                    'http://localhost:8000/health',  # API Gateway
                    'http://localhost:8300/health',  # DMLog
                    'http://localhost:8301/health',  # MakerLog
                    'http://localhost:8318/health'   # RealLog Pro
                ],
                'startup_wait': 30,
                'health_check_timeout': 10
            },
            'execution': {
                'parallel_execution': True,
                'max_parallel_suites': 3,
                'retry_failed_tests': True,
                'retry_attempts': 2,
                'continue_on_failure': True
            },
            'reporting': {
                'generate_html_report': True,
                'generate_json_report': True,
                'capture_logs': True,
                'capture_screenshots': False,
                'output_directory': 'test_results'
            }
        }
    
    async def check_services_health(self) -> bool:
        """Check if all required services are healthy"""
        import aiohttp
        
        print("🔍 Checking service health...")
        healthy_services = 0
        total_services = len(self.config['services']['health_check_urls'])
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            for url in self.config['services']['health_check_urls']:
                try:
                    async with session.get(url) as response:
                        if response.status == 200:
                            healthy_services += 1
                            print(f"  ✅ {url}")
                        else:
                            print(f"  ❌ {url} (HTTP {response.status})")
                except Exception as e:
                    print(f"  ❌ {url} (Error: {str(e)[:50]}...)")
        
        health_percentage = (healthy_services / total_services) * 100
        print(f"\n📊 Service Health: {healthy_services}/{total_services} ({health_percentage:.1f}%)")
        
        if health_percentage < 80:
            print("⚠️  Warning: Less than 80% of services are healthy")
            return False
        
        return True
    
    def run_test_suite(self, suite_name: str, suite_config: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test suite"""
        print(f"\n🚀 Running test suite: {suite_name}")
        
        test_file = suite_config['file']
        timeout = suite_config.get('timeout', 300)
        
        # Build pytest command
        cmd = [
            'python', '-m', 'pytest',
            test_file,
            '-v',
            '--tb=short',
            f'--timeout={timeout}',
            '--durations=10',
            '--json-report',
            f'--json-report-file=test_results/{suite_name}_report.json'
        ]
        
        # Add markers if specified
        if 'markers' in suite_config:
            for marker in suite_config['markers']:
                cmd.extend(['-m', marker])
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                cwd=Path(__file__).parent,
                capture_output=True,
                text=True,
                timeout=timeout + 60  # Give extra time for pytest overhead
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            return {
                'suite_name': suite_name,
                'status': 'passed' if result.returncode == 0 else 'failed',
                'return_code': result.returncode,
                'duration': duration,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'start_time': start_time,
                'end_time': end_time
            }
            
        except subprocess.TimeoutExpired:
            return {
                'suite_name': suite_name,
                'status': 'timeout',
                'return_code': -1,
                'duration': timeout,
                'error': f'Test suite timed out after {timeout} seconds',
                'start_time': start_time,
                'end_time': time.time()
            }
        except Exception as e:
            return {
                'suite_name': suite_name,
                'status': 'error',
                'return_code': -1,
                'duration': time.time() - start_time,
                'error': str(e),
                'start_time': start_time,
                'end_time': time.time()
            }
    
    def get_execution_order(self) -> List[List[str]]:
        """Determine test execution order based on priorities and dependencies"""
        suites = self.config['test_suites']
        
        # Group by priority
        priority_groups = {}
        for suite_name, suite_config in suites.items():
            priority = suite_config.get('priority', 999)
            if priority not in priority_groups:
                priority_groups[priority] = []
            priority_groups[priority].append(suite_name)
        
        # Return ordered groups
        return [priority_groups[p] for p in sorted(priority_groups.keys())]
    
    def run_parallel_suites(self, suite_names: List[str]) -> List[Dict[str, Any]]:
        """Run multiple test suites in parallel"""
        max_workers = min(
            len(suite_names),
            self.config['execution'].get('max_parallel_suites', 3)
        )
        
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_suite = {}
            for suite_name in suite_names:
                suite_config = self.config['test_suites'][suite_name]
                future = executor.submit(self.run_test_suite, suite_name, suite_config)
                future_to_suite[future] = suite_name
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_suite):
                suite_name = future_to_suite[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    # Log immediate result
                    status_emoji = "✅" if result['status'] == 'passed' else "❌"
                    print(f"  {status_emoji} {suite_name}: {result['status']} ({result['duration']:.1f}s)")
                    
                except Exception as e:
                    error_result = {
                        'suite_name': suite_name,
                        'status': 'error',
                        'error': str(e),
                        'duration': 0
                    }
                    results.append(error_result)
                    print(f"  ❌ {suite_name}: error - {str(e)}")
        
        return results
    
    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate comprehensive test summary report"""
        all_results = []
        for priority_results in self.test_results.values():
            all_results.extend(priority_results)
        
        total_suites = len(all_results)
        passed_suites = len([r for r in all_results if r['status'] == 'passed'])
        failed_suites = len([r for r in all_results if r['status'] == 'failed'])
        error_suites = len([r for r in all_results if r['status'] == 'error'])
        timeout_suites = len([r for r in all_results if r['status'] == 'timeout'])
        
        total_duration = sum(r.get('duration', 0) for r in all_results)
        
        summary = {
            'execution_summary': {
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'end_time': self.end_time.isoformat() if self.end_time else None,
                'total_duration': total_duration,
                'total_suites': total_suites,
                'passed_suites': passed_suites,
                'failed_suites': failed_suites,
                'error_suites': error_suites,
                'timeout_suites': timeout_suites,
                'success_rate': (passed_suites / total_suites * 100) if total_suites > 0 else 0
            },
            'suite_results': all_results,
            'configuration': self.config
        }
        
        return summary
    
    def save_reports(self, summary: Dict[str, Any]) -> None:
        """Save test reports in various formats"""
        output_dir = Path(self.config['reporting']['output_directory'])
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save JSON report
        if self.config['reporting']['generate_json_report']:
            json_file = output_dir / f'beta_test_report_{timestamp}.json'
            with open(json_file, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            print(f"📄 JSON report saved: {json_file}")
        
        # Save HTML report
        if self.config['reporting']['generate_html_report']:
            html_file = output_dir / f'beta_test_report_{timestamp}.html'
            self.generate_html_report(summary, html_file)
            print(f"🌐 HTML report saved: {html_file}")
        
        # Save latest report (overwrite)
        latest_json = output_dir / 'latest_beta_test_report.json'
        with open(latest_json, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
    
    def generate_html_report(self, summary: Dict[str, Any], output_file: Path) -> None:
        """Generate HTML test report"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>ActiveLog Beta Integration Test Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .summary {{ margin: 20px 0; }}
                .suite {{ margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }}
                .passed {{ background-color: #d4edda; }}
                .failed {{ background-color: #f8d7da; }}
                .error {{ background-color: #fff3cd; }}
                .timeout {{ background-color: #e2e3e5; }}
                .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; }}
                .metric {{ background: #f8f9fa; padding: 10px; border-radius: 3px; text-align: center; }}
                pre {{ background: #f8f9fa; padding: 10px; overflow-x: auto; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🧪 ActiveLog Beta Integration Test Report</h1>
                <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="summary">
                <h2>📊 Execution Summary</h2>
                <div class="metrics">
                    <div class="metric">
                        <h3>{summary['execution_summary']['total_suites']}</h3>
                        <p>Total Suites</p>
                    </div>
                    <div class="metric">
                        <h3>{summary['execution_summary']['passed_suites']}</h3>
                        <p>Passed</p>
                    </div>
                    <div class="metric">
                        <h3>{summary['execution_summary']['failed_suites']}</h3>
                        <p>Failed</p>
                    </div>
                    <div class="metric">
                        <h3>{summary['execution_summary']['success_rate']:.1f}%</h3>
                        <p>Success Rate</p>
                    </div>
                    <div class="metric">
                        <h3>{summary['execution_summary']['total_duration']:.1f}s</h3>
                        <p>Total Duration</p>
                    </div>
                </div>
            </div>
            
            <div class="suites">
                <h2>🔍 Test Suite Results</h2>
        """
        
        for result in summary['suite_results']:
            status_class = result['status']
            status_emoji = {
                'passed': '✅',
                'failed': '❌',
                'error': '⚠️',
                'timeout': '⏰'
            }.get(status_class, '❓')
            
            html_content += f"""
                <div class="suite {status_class}">
                    <h3>{status_emoji} {result['suite_name']}</h3>
                    <p><strong>Status:</strong> {result['status'].title()}</p>
                    <p><strong>Duration:</strong> {result.get('duration', 0):.1f} seconds</p>
                    
                    {'<details><summary>Output</summary><pre>' + result.get('stdout', 'No output') + '</pre></details>' if result.get('stdout') else ''}
                    {'<details><summary>Error</summary><pre>' + result.get('stderr', result.get('error', '')) + '</pre></details>' if result.get('stderr') or result.get('error') else ''}
                </div>
            """
        
        html_content += """
            </div>
        </body>
        </html>
        """
        
        with open(output_file, 'w') as f:
            f.write(html_content)
    
    async def run_all_tests(self, selected_suites: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run all beta integration tests"""
        print("🎯 ActiveLog Beta Integration Test Suite")
        print("=" * 50)
        
        self.start_time = datetime.now()
        
        # Check service health first
        if not await self.check_services_health():
            print("❌ Service health check failed. Aborting test execution.")
            return {'error': 'Service health check failed'}
        
        # Filter suites if specified
        suites_to_run = self.config['test_suites']
        if selected_suites:
            suites_to_run = {
                name: config for name, config in suites_to_run.items()
                if name in selected_suites
            }
        
        # Create output directory
        output_dir = Path(self.config['reporting']['output_directory'])
        output_dir.mkdir(exist_ok=True)
        
        # Get execution order
        execution_groups = self.get_execution_order()
        
        # Run tests by priority group
        for priority, group in enumerate(execution_groups, 1):
            # Filter group to only include selected suites
            group_suites = [suite for suite in group if suite in suites_to_run]
            if not group_suites:
                continue
                
            print(f"\n🔄 Priority {priority} - Running {len(group_suites)} suite(s)")
            
            if self.config['execution']['parallel_execution'] and len(group_suites) > 1:
                results = self.run_parallel_suites(group_suites)
            else:
                # Run sequentially
                results = []
                for suite_name in group_suites:
                    suite_config = suites_to_run[suite_name]
                    result = self.run_test_suite(suite_name, suite_config)
                    results.append(result)
                    
                    status_emoji = "✅" if result['status'] == 'passed' else "❌"
                    print(f"  {status_emoji} {suite_name}: {result['status']} ({result['duration']:.1f}s)")
            
            self.test_results[priority] = results
            
            # Check if we should continue after failures
            failed_results = [r for r in results if r['status'] != 'passed']
            if failed_results and not self.config['execution']['continue_on_failure']:
                print(f"⛔ Stopping execution due to {len(failed_results)} failure(s)")
                break
        
        self.end_time = datetime.now()
        
        # Generate and save reports
        summary = self.generate_summary_report()
        self.save_reports(summary)
        
        # Print final summary
        print("\n" + "=" * 50)
        print("🏁 Test Execution Complete")
        print("=" * 50)
        print(f"📊 Results: {summary['execution_summary']['passed_suites']}/{summary['execution_summary']['total_suites']} passed ({summary['execution_summary']['success_rate']:.1f}%)")
        print(f"⏱️  Total Duration: {summary['execution_summary']['total_duration']:.1f} seconds")
        
        return summary


def main():
    """Main entry point for the beta test runner"""
    parser = argparse.ArgumentParser(description='ActiveLog Beta Integration Test Runner')
    
    parser.add_argument(
        '--config',
        type=str,
        help='Path to test configuration file'
    )
    
    parser.add_argument(
        '--suites',
        nargs='+',
        help='Specific test suites to run'
    )
    
    parser.add_argument(
        '--list-suites',
        action='store_true',
        help='List available test suites and exit'
    )
    
    parser.add_argument(
        '--health-check-only',
        action='store_true',
        help='Only run service health checks'
    )
    
    args = parser.parse_args()
    
    # Initialize test runner
    runner = BetaTestRunner(args.config)
    
    # List suites if requested
    if args.list_suites:
        print("Available test suites:")
        for suite_name, suite_config in runner.config['test_suites'].items():
            priority = suite_config.get('priority', 'N/A')
            timeout = suite_config.get('timeout', 'N/A')
            print(f"  {suite_name} (priority: {priority}, timeout: {timeout}s)")
        return
    
    # Run health check only if requested
    if args.health_check_only:
        async def health_check_main():
            await runner.check_services_health()
        asyncio.run(health_check_main())
        return
    
    # Run the full test suite
    async def run_main():
        try:
            summary = await runner.run_all_tests(args.suites)
            
            # Exit with appropriate code
            if 'error' in summary:
                sys.exit(1)
            elif summary['execution_summary']['success_rate'] < 100:
                sys.exit(1)
            else:
                sys.exit(0)
                
        except KeyboardInterrupt:
            print("\n⏹️  Test execution interrupted by user")
            sys.exit(130)
        except Exception as e:
            print(f"\n💥 Unexpected error: {str(e)}")
            sys.exit(1)
    
    asyncio.run(run_main())


if __name__ == '__main__':
    main()