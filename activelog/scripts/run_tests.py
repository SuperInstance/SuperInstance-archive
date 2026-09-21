#!/usr/bin/env python3
"""
Test runner script with coverage reporting and test management
"""

import os
import sys
import subprocess
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestRunner:
    """Manages test execution and reporting"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.tests_dir = project_root / "tests"
        self.coverage_dir = self.tests_dir / "coverage"
        self.logs_dir = self.tests_dir / "logs"
        
        # Ensure directories exist
        self.coverage_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        
        self.test_results = {}
        
    def run_unit_tests(
        self, 
        verbose: bool = True, 
        coverage: bool = True,
        parallel: bool = False,
        markers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Run unit tests"""
        
        print("🧪 Running Unit Tests...")
        
        cmd = ["python", "-m", "pytest", "tests/unit/"]
        
        if verbose:
            cmd.append("-v")
        
        if coverage:
            cmd.extend([
                "--cov=activelog",
                "--cov=services", 
                "--cov-report=term-missing",
                f"--cov-report=html:{self.coverage_dir}/unit/html",
                f"--cov-report=xml:{self.coverage_dir}/unit/coverage.xml"
            ])
        
        if parallel:
            try:
                import pytest_xdist
                cmd.extend(["-n", "auto"])
            except ImportError:
                print("Warning: pytest-xdist not installed, running sequentially")
        
        if markers:
            for marker in markers:
                cmd.extend(["-m", marker])
        
        # Add markers for unit tests
        cmd.extend(["-m", "unit"])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        return {
            "test_type": "unit",
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0
        }
    
    def run_integration_tests(
        self, 
        verbose: bool = True,
        coverage: bool = True,
        markers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Run integration tests"""
        
        print("🔗 Running Integration Tests...")
        
        cmd = ["python", "-m", "pytest", "tests/integration/"]
        
        if verbose:
            cmd.append("-v")
        
        if coverage:
            cmd.extend([
                "--cov=activelog",
                "--cov=services",
                "--cov-append",
                f"--cov-report=html:{self.coverage_dir}/integration/html",
                f"--cov-report=xml:{self.coverage_dir}/integration/coverage.xml"
            ])
        
        if markers:
            for marker in markers:
                cmd.extend(["-m", marker])
        
        # Add markers for integration tests
        cmd.extend(["-m", "integration"])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        return {
            "test_type": "integration", 
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0
        }
    
    def run_e2e_tests(
        self,
        verbose: bool = True,
        headless: bool = True,
        browser: str = "chromium",
        markers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Run end-to-end tests"""
        
        print("🌐 Running End-to-End Tests...")
        
        # Check if Playwright is installed
        try:
            import playwright
        except ImportError:
            return {
                "test_type": "e2e",
                "exit_code": 1,
                "stdout": "",
                "stderr": "Playwright not installed. Run: pip install playwright && playwright install",
                "success": False
            }
        
        cmd = ["python", "-m", "pytest", "tests/e2e/"]
        
        if verbose:
            cmd.append("-v")
        
        if markers:
            for marker in markers:
                cmd.extend(["-m", marker])
        
        # Add markers for e2e tests
        cmd.extend(["-m", "e2e"])
        
        # Set environment variables for E2E tests
        env = os.environ.copy()
        env["PLAYWRIGHT_BROWSER"] = browser
        env["PLAYWRIGHT_HEADLESS"] = "true" if headless else "false"
        
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        
        return {
            "test_type": "e2e",
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0
        }
    
    def run_load_tests(self, scenario: str = "light") -> Dict[str, Any]:
        """Run load tests using Locust"""
        
        print(f"⚡ Running Load Tests ({scenario} scenario)...")
        
        load_script = self.project_root / "tests" / "load" / "run_load_tests.py"
        
        if not load_script.exists():
            return {
                "test_type": "load",
                "exit_code": 1,
                "stdout": "",
                "stderr": f"Load test script not found: {load_script}",
                "success": False
            }
        
        cmd = ["python", str(load_script), "--scenario", scenario]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        return {
            "test_type": "load",
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0
        }
    
    def run_security_tests(
        self,
        verbose: bool = True,
        coverage: bool = True
    ) -> Dict[str, Any]:
        """Run security-focused tests"""
        
        print("🔒 Running Security Tests...")
        
        cmd = ["python", "-m", "pytest"]
        
        if verbose:
            cmd.append("-v")
        
        if coverage:
            cmd.extend([
                "--cov=activelog",
                "--cov=services",
                "--cov-append",
                f"--cov-report=html:{self.coverage_dir}/security/html",
                f"--cov-report=xml:{self.coverage_dir}/security/coverage.xml"
            ])
        
        # Run tests with security marker
        cmd.extend(["-m", "security"])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        return {
            "test_type": "security",
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0
        }
    
    def run_smoke_tests(self, verbose: bool = True) -> Dict[str, Any]:
        """Run smoke tests for quick validation"""
        
        print("💨 Running Smoke Tests...")
        
        cmd = ["python", "-m", "pytest", "-m", "smoke"]
        
        if verbose:
            cmd.append("-v")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        return {
            "test_type": "smoke",
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0
        }
    
    def generate_coverage_report(self, output_format: str = "html") -> Dict[str, Any]:
        """Generate comprehensive coverage report"""
        
        print("📊 Generating Coverage Report...")
        
        cmd = ["python", "-m", "coverage"]
        
        if output_format == "html":
            cmd.extend(["html", "--directory", str(self.coverage_dir / "html")])
        elif output_format == "xml":
            cmd.extend(["xml", "--output", str(self.coverage_dir / "coverage.xml")])
        elif output_format == "json":
            cmd.extend(["json", "--output", str(self.coverage_dir / "coverage.json")])
        elif output_format == "report":
            cmd.append("report")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        return {
            "operation": f"coverage_{output_format}",
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0
        }
    
    def analyze_coverage(self) -> Dict[str, Any]:
        """Analyze coverage data and provide insights"""
        
        coverage_json = self.coverage_dir / "coverage.json"
        
        if not coverage_json.exists():
            return {"error": "Coverage JSON file not found"}
        
        try:
            with open(coverage_json) as f:
                coverage_data = json.load(f)
            
            # Extract key metrics
            summary = coverage_data.get("totals", {})
            
            files_coverage = []
            for file_path, file_data in coverage_data.get("files", {}).items():
                file_coverage = {
                    "file": file_path,
                    "line_coverage": file_data.get("summary", {}).get("percent_covered", 0),
                    "branch_coverage": file_data.get("summary", {}).get("percent_covered_display", "N/A"),
                    "missing_lines": len(file_data.get("missing_lines", [])),
                    "excluded_lines": len(file_data.get("excluded_lines", []))
                }
                files_coverage.append(file_coverage)
            
            # Sort by coverage percentage
            files_coverage.sort(key=lambda x: x["line_coverage"])
            
            analysis = {
                "overall": {
                    "line_coverage": summary.get("percent_covered", 0),
                    "branch_coverage": summary.get("branch_percent_covered", 0),
                    "total_statements": summary.get("num_statements", 0),
                    "missing_statements": summary.get("missing_lines", 0),
                    "covered_statements": summary.get("covered_lines", 0)
                },
                "files": files_coverage,
                "low_coverage_files": [f for f in files_coverage if f["line_coverage"] < 70],
                "high_coverage_files": [f for f in files_coverage if f["line_coverage"] > 90],
                "recommendations": []
            }
            
            # Generate recommendations
            if analysis["overall"]["line_coverage"] < 80:
                analysis["recommendations"].append("Overall coverage is below 80%. Focus on increasing test coverage.")
            
            if len(analysis["low_coverage_files"]) > 0:
                analysis["recommendations"].append(f"{len(analysis['low_coverage_files'])} files have low coverage (<70%). Prioritize testing these files.")
            
            return analysis
            
        except Exception as e:
            return {"error": f"Failed to analyze coverage: {str(e)}"}
    
    def run_all_tests(
        self, 
        include_e2e: bool = False,
        include_load: bool = False,
        verbose: bool = True,
        coverage: bool = True
    ) -> Dict[str, Any]:
        """Run all test suites"""
        
        print("🚀 Running All Tests...")
        
        results = {
            "start_time": datetime.now().isoformat(),
            "test_results": [],
            "overall_success": True
        }
        
        # Run unit tests
        unit_result = self.run_unit_tests(verbose=verbose, coverage=coverage)
        results["test_results"].append(unit_result)
        if not unit_result["success"]:
            results["overall_success"] = False
        
        # Run integration tests
        integration_result = self.run_integration_tests(verbose=verbose, coverage=coverage)
        results["test_results"].append(integration_result)
        if not integration_result["success"]:
            results["overall_success"] = False
        
        # Run security tests
        security_result = self.run_security_tests(verbose=verbose, coverage=coverage)
        results["test_results"].append(security_result)
        if not security_result["success"]:
            results["overall_success"] = False
        
        # Optionally run E2E tests
        if include_e2e:
            e2e_result = self.run_e2e_tests(verbose=verbose)
            results["test_results"].append(e2e_result)
            if not e2e_result["success"]:
                results["overall_success"] = False
        
        # Optionally run load tests
        if include_load:
            load_result = self.run_load_tests()
            results["test_results"].append(load_result)
            if not load_result["success"]:
                results["overall_success"] = False
        
        # Generate coverage reports
        if coverage:
            html_report = self.generate_coverage_report("html")
            xml_report = self.generate_coverage_report("xml")
            json_report = self.generate_coverage_report("json")
            
            results["coverage_reports"] = [html_report, xml_report, json_report]
            
            # Analyze coverage
            coverage_analysis = self.analyze_coverage()
            results["coverage_analysis"] = coverage_analysis
        
        results["end_time"] = datetime.now().isoformat()
        
        return results
    
    def print_summary(self, results: Dict[str, Any]) -> None:
        """Print a summary of test results"""
        
        print("\n" + "="*80)
        print("📋 TEST EXECUTION SUMMARY")
        print("="*80)
        
        for test_result in results.get("test_results", []):
            test_type = test_result["test_type"].upper()
            status = "✅ PASSED" if test_result["success"] else "❌ FAILED"
            print(f"{test_type:15} {status}")
        
        if "coverage_analysis" in results:
            analysis = results["coverage_analysis"]
            if "overall" in analysis:
                coverage = analysis["overall"]["line_coverage"]
                print(f"{'COVERAGE':15} {coverage:.1f}%")
        
        overall_status = "✅ ALL PASSED" if results["overall_success"] else "❌ SOME FAILED"
        print(f"\n{'OVERALL':15} {overall_status}")
        
        print("="*80)
        
        # Print recommendations if available
        if "coverage_analysis" in results and "recommendations" in results["coverage_analysis"]:
            recommendations = results["coverage_analysis"]["recommendations"]
            if recommendations:
                print("\n💡 RECOMMENDATIONS:")
                for i, rec in enumerate(recommendations, 1):
                    print(f"  {i}. {rec}")
                print()


def main():
    """Main entry point"""
    
    parser = argparse.ArgumentParser(description="ActiveLog Test Runner")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--e2e", action="store_true", help="Run E2E tests only")
    parser.add_argument("--load", action="store_true", help="Run load tests only")
    parser.add_argument("--security", action="store_true", help="Run security tests only")
    parser.add_argument("--smoke", action="store_true", help="Run smoke tests only")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--coverage", action="store_true", default=True, help="Enable coverage reporting")
    parser.add_argument("--no-coverage", action="store_true", help="Disable coverage reporting")
    parser.add_argument("--verbose", "-v", action="store_true", default=True, help="Verbose output")
    parser.add_argument("--quiet", "-q", action="store_true", help="Quiet output")
    parser.add_argument("--parallel", "-n", action="store_true", help="Run tests in parallel")
    parser.add_argument("--markers", "-m", nargs="+", help="Run tests with specific markers")
    parser.add_argument("--browser", default="chromium", choices=["chromium", "firefox", "webkit"], help="Browser for E2E tests")
    parser.add_argument("--headless", action="store_true", default=True, help="Run E2E tests headless")
    parser.add_argument("--load-scenario", default="light", choices=["light", "normal", "heavy", "stress"], help="Load test scenario")
    
    args = parser.parse_args()
    
    # Handle coverage settings
    coverage_enabled = args.coverage and not args.no_coverage
    verbose = args.verbose and not args.quiet
    
    runner = TestRunner(project_root)
    
    try:
        if args.all:
            results = runner.run_all_tests(
                include_e2e=True,
                include_load=True,
                verbose=verbose,
                coverage=coverage_enabled
            )
        elif args.unit:
            results = {"test_results": [runner.run_unit_tests(verbose=verbose, coverage=coverage_enabled, parallel=args.parallel, markers=args.markers)]}
        elif args.integration:
            results = {"test_results": [runner.run_integration_tests(verbose=verbose, coverage=coverage_enabled, markers=args.markers)]}
        elif args.e2e:
            results = {"test_results": [runner.run_e2e_tests(verbose=verbose, headless=args.headless, browser=args.browser, markers=args.markers)]}
        elif args.load:
            results = {"test_results": [runner.run_load_tests(scenario=args.load_scenario)]}
        elif args.security:
            results = {"test_results": [runner.run_security_tests(verbose=verbose, coverage=coverage_enabled)]}
        elif args.smoke:
            results = {"test_results": [runner.run_smoke_tests(verbose=verbose)]}
        else:
            # Default: run unit and integration tests
            unit_result = runner.run_unit_tests(verbose=verbose, coverage=coverage_enabled, parallel=args.parallel, markers=args.markers)
            integration_result = runner.run_integration_tests(verbose=verbose, coverage=coverage_enabled, markers=args.markers)
            
            results = {
                "test_results": [unit_result, integration_result],
                "overall_success": unit_result["success"] and integration_result["success"]
            }
            
            if coverage_enabled:
                html_report = runner.generate_coverage_report("html")
                xml_report = runner.generate_coverage_report("xml") 
                json_report = runner.generate_coverage_report("json")
                
                results["coverage_reports"] = [html_report, xml_report, json_report]
                results["coverage_analysis"] = runner.analyze_coverage()
        
        # Print summary
        runner.print_summary(results)
        
        # Save results to file
        results_file = runner.logs_dir / f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        # Exit with appropriate code
        if results.get("overall_success", True):
            print(f"\n✅ All tests passed! Results saved to {results_file}")
            sys.exit(0)
        else:
            print(f"\n❌ Some tests failed. Results saved to {results_file}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Test runner failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()