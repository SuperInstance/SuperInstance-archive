#!/usr/bin/env python3
"""
Security scanning tool using Bandit for ActiveLog codebase.
Scans all Python files for security vulnerabilities and generates reports.
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


class SecurityScanner:
    """Security scanner using Bandit for vulnerability detection."""
    
    def __init__(self, project_root: str):
        """
        Initialize security scanner.
        
        Args:
            project_root: Root directory of the project to scan
        """
        self.project_root = Path(project_root)
        self.output_dir = self.project_root / "security-audit" / "reports"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Scan configuration
        self.scan_config = {
            'exclude_dirs': [
                'venv', '__pycache__', '.git', 'node_modules',
                'tests', 'test_', '.pytest_cache', 'migrations'
            ],
            'severity_levels': ['LOW', 'MEDIUM', 'HIGH'],
            'confidence_levels': ['LOW', 'MEDIUM', 'HIGH']
        }
    
    def find_python_files(self) -> List[Path]:
        """
        Find all Python files in the project.
        
        Returns:
            List of Python file paths
        """
        python_files = []
        
        for root, dirs, files in os.walk(self.project_root):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if not any(
                excl in d for excl in self.scan_config['exclude_dirs']
            )]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    # Skip test files and migrations
                    if not any(excl in str(file_path) for excl in 
                              ['test_', '_test.py', 'migrations/']):
                        python_files.append(file_path)
        
        return python_files
    
    def run_bandit_scan(self, target_paths: List[Path]) -> Dict[str, Any]:
        """
        Run Bandit security scan on specified paths.
        
        Args:
            target_paths: List of file/directory paths to scan
            
        Returns:
            Scan results as dictionary
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_output = self.output_dir / f"bandit_scan_{timestamp}.json"
        
        # Build bandit command
        cmd = [
            'bandit',
            '-r',  # Recursive
            '-f', 'json',  # JSON output format
            '-o', str(json_output),  # Output file
            '--severity-level', 'low',  # Include all severity levels
            '--confidence-level', 'low',  # Include all confidence levels
        ]
        
        # Add target paths
        for path in target_paths:
            cmd.append(str(path))
        
        try:
            # Run bandit scan
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=300  # 5 minute timeout
            )
            
            # Load results
            if json_output.exists():
                with open(json_output, 'r') as f:
                    scan_results = json.load(f)
            else:
                scan_results = {'results': [], 'metrics': {}}
            
            # Add command info to results
            scan_results['scan_info'] = {
                'timestamp': timestamp,
                'command': ' '.join(cmd),
                'exit_code': result.returncode,
                'stderr': result.stderr,
                'target_paths': [str(p) for p in target_paths]
            }
            
            return scan_results
            
        except subprocess.TimeoutExpired:
            return {
                'error': 'Scan timeout after 5 minutes',
                'scan_info': {'timestamp': timestamp}
            }
        except Exception as e:
            return {
                'error': str(e),
                'scan_info': {'timestamp': timestamp}
            }
    
    def generate_summary_report(self, scan_results: Dict[str, Any]) -> str:
        """
        Generate human-readable summary report.
        
        Args:
            scan_results: Results from bandit scan
            
        Returns:
            Summary report as string
        """
        if 'error' in scan_results:
            return f"Scan failed: {scan_results['error']}"
        
        results = scan_results.get('results', [])
        metrics = scan_results.get('metrics', {})
        scan_info = scan_results.get('scan_info', {})
        
        # Count issues by severity and confidence
        severity_counts = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        confidence_counts = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        test_ids = set()
        
        for issue in results:
            severity = issue.get('issue_severity', 'UNKNOWN')
            confidence = issue.get('issue_confidence', 'UNKNOWN')
            test_id = issue.get('test_id', 'UNKNOWN')
            
            if severity in severity_counts:
                severity_counts[severity] += 1
            if confidence in confidence_counts:
                confidence_counts[confidence] += 1
            test_ids.add(test_id)
        
        # Generate report
        report_lines = [
            "=" * 80,
            "ACTIVELOG SECURITY SCAN REPORT",
            "=" * 80,
            f"Scan Timestamp: {scan_info.get('timestamp', 'Unknown')}",
            f"Exit Code: {scan_info.get('exit_code', 'Unknown')}",
            "",
            "SUMMARY:",
            f"  Total Issues Found: {len(results)}",
            f"  Files Scanned: {metrics.get('_totals', {}).get('loc', 'Unknown')} lines of code",
            "",
            "SEVERITY BREAKDOWN:",
            f"  HIGH:   {severity_counts['HIGH']:3d} issues",
            f"  MEDIUM: {severity_counts['MEDIUM']:3d} issues", 
            f"  LOW:    {severity_counts['LOW']:3d} issues",
            "",
            "CONFIDENCE BREAKDOWN:",
            f"  HIGH:   {confidence_counts['HIGH']:3d} issues",
            f"  MEDIUM: {confidence_counts['MEDIUM']:3d} issues",
            f"  LOW:    {confidence_counts['LOW']:3d} issues",
            "",
            f"UNIQUE TEST TYPES: {len(test_ids)}",
            "",
        ]
        
        # Add detailed issues if any
        if results:
            report_lines.extend([
                "DETAILED ISSUES:",
                "-" * 40,
            ])
            
            # Group by severity
            for severity in ['HIGH', 'MEDIUM', 'LOW']:
                severity_issues = [r for r in results if r.get('issue_severity') == severity]
                if severity_issues:
                    report_lines.append(f"\n{severity} SEVERITY ISSUES:")
                    
                    for issue in severity_issues[:10]:  # Limit to first 10 per severity
                        filename = issue.get('filename', 'Unknown')
                        line_number = issue.get('line_number', 'Unknown')
                        test_name = issue.get('test_name', 'Unknown')
                        test_id = issue.get('test_id', 'Unknown')
                        confidence = issue.get('issue_confidence', 'Unknown')
                        
                        report_lines.extend([
                            f"  File: {filename}:{line_number}",
                            f"  Test: {test_name} ({test_id})",
                            f"  Confidence: {confidence}",
                            f"  Issue: {issue.get('issue_text', 'No description')}",
                            ""
                        ])
                    
                    if len(severity_issues) > 10:
                        report_lines.append(f"  ... and {len(severity_issues) - 10} more {severity} issues")
        else:
            report_lines.append("No security issues found! ✅")
        
        # Add recommendations
        report_lines.extend([
            "",
            "RECOMMENDATIONS:",
            "- Review all HIGH severity issues immediately",
            "- Address MEDIUM severity issues in next sprint",
            "- Consider LOW severity issues for future improvements",
            "- Run this scan regularly as part of CI/CD pipeline",
            "- Review and update security policies based on findings",
            "",
            "For detailed analysis, review the JSON report in the reports directory.",
            "=" * 80
        ])
        
        return "\n".join(report_lines)
    
    def save_summary_report(self, summary: str, timestamp: str):
        """Save summary report to file."""
        summary_file = self.output_dir / f"security_summary_{timestamp}.txt"
        with open(summary_file, 'w') as f:
            f.write(summary)
        return summary_file
    
    def scan_project(self) -> Dict[str, Any]:
        """
        Run complete security scan of the project.
        
        Returns:
            Complete scan results
        """
        print("🔍 Starting ActiveLog Security Scan...")
        
        # Find Python files
        python_files = self.find_python_files()
        print(f"Found {len(python_files)} Python files to scan")
        
        if not python_files:
            return {
                'error': 'No Python files found to scan',
                'scan_info': {'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S")}
            }
        
        # Group files by service/directory for better organization
        service_dirs = set()
        for f in python_files:
            rel_path = f.relative_to(self.project_root)
            if len(rel_path.parts) > 1:
                service_dirs.add(self.project_root / rel_path.parts[0])
            else:
                service_dirs.add(self.project_root)
        
        print(f"Scanning {len(service_dirs)} directories...")
        
        # Run scan
        scan_results = self.run_bandit_scan(list(service_dirs))
        
        # Generate and save reports
        if 'error' not in scan_results:
            summary = self.generate_summary_report(scan_results)
            timestamp = scan_results['scan_info']['timestamp']
            summary_file = self.save_summary_report(summary, timestamp)
            
            print(f"✅ Scan completed!")
            print(f"📄 Summary report: {summary_file}")
            print(f"📊 JSON report: {self.output_dir}/bandit_scan_{timestamp}.json")
            
            # Print summary to console
            print("\n" + summary)
        else:
            print(f"❌ Scan failed: {scan_results['error']}")
        
        return scan_results


def main():
    """Main entry point for security scanner."""
    parser = argparse.ArgumentParser(description='ActiveLog Security Scanner')
    parser.add_argument(
        '--project-root', 
        default='/home/activeloguser/activelog',
        help='Root directory of the project to scan'
    )
    parser.add_argument(
        '--install-bandit',
        action='store_true',
        help='Install bandit if not already installed'
    )
    
    args = parser.parse_args()
    
    # Check if bandit is installed
    try:
        subprocess.run(['bandit', '--version'], 
                      capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        if args.install_bandit:
            print("Installing bandit...")
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'bandit'], 
                          check=True)
        else:
            print("❌ Bandit not found. Install with: pip install bandit")
            print("   Or run with --install-bandit flag")
            sys.exit(1)
    
    # Initialize and run scanner
    scanner = SecurityScanner(args.project_root)
    results = scanner.scan_project()
    
    # Exit with appropriate code
    if 'error' in results:
        sys.exit(1)
    
    # Check if any HIGH severity issues found
    high_severity_count = sum(1 for r in results.get('results', []) 
                             if r.get('issue_severity') == 'HIGH')
    
    if high_severity_count > 0:
        print(f"\n⚠️  Found {high_severity_count} HIGH severity security issues!")
        print("   Please address these before deploying to production.")
        sys.exit(2)  # Different exit code for security issues
    
    print("\n✅ No high-severity security issues found!")


if __name__ == "__main__":
    main()