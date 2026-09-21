#!/usr/bin/env python3

import subprocess
import json
import re
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import ast

class ActiveLogAuditReporter:
    def __init__(self, activelog_root: str = "/home/activeloguser/activelog"):
        self.activelog_root = Path(activelog_root)
        self.audit_data = {}
        self.report_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
    def run_audit_script(self) -> str:
        """Run the audit_system.sh script and capture output"""
        try:
            result = subprocess.run(
                [str(self.activelog_root / "audit_system.sh")],
                capture_output=True,
                text=True,
                cwd=self.activelog_root
            )
            return result.stdout
        except Exception as e:
            return f"Error running audit script: {e}"
    
    def parse_audit_output(self, output: str) -> Dict[str, Any]:
        """Parse the structured audit output"""
        sections = {}
        current_section = None
        current_content = []
        
        lines = output.split('\n')
        for line in lines:
            if '_START' in line:
                current_section = line.replace('_START', '').strip()
                current_content = []
            elif '_END' in line:
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                current_section = None
                current_content = []
            elif current_section:
                current_content.append(line)
        
        return sections
    
    def analyze_services(self) -> Dict[str, Any]:
        """Analyze services and create dependency graph"""
        services = {}
        services_dir = self.activelog_root / "services"
        
        if services_dir.exists():
            for service_path in services_dir.iterdir():
                if service_path.is_dir():
                    service_name = service_path.name
                    services[service_name] = self.analyze_service(service_path)
        
        return services
    
    def analyze_service(self, service_path: Path) -> Dict[str, Any]:
        """Analyze individual service"""
        service_info = {
            'name': service_path.name,
            'path': str(service_path),
            'files': [],
            'dependencies': [],
            'api_endpoints': [],
            'description': '',
            'dockerized': False,
            'ai_integrations': []
        }
        
        # Check for Docker files
        if (service_path / "Dockerfile").exists() or (service_path / "docker-compose.yml").exists():
            service_info['dockerized'] = True
        
        # Analyze Python files
        for py_file in service_path.glob("**/*.py"):
            service_info['files'].append(str(py_file.relative_to(service_path)))
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Extract imports for dependencies
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                service_info['dependencies'].append(alias.name)
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                service_info['dependencies'].append(node.module)
                except:
                    pass
                
                # Look for AI integrations
                ai_keywords = ['openai', 'anthropic', 'huggingface', 'transformers', 'torch', 'tensorflow', 'mediapipe']
                for keyword in ai_keywords:
                    if keyword in content.lower():
                        service_info['ai_integrations'].append(keyword)
                
                # Extract API endpoints (Flask/FastAPI style)
                endpoints = re.findall(r'@app\.route\(["\']([^"\']+)["\']', content)
                endpoints += re.findall(r'@[^.]+\.(?:get|post|put|delete)\(["\']([^"\']+)["\']', content)
                service_info['api_endpoints'].extend(endpoints)
                
                # Try to extract service description from docstrings
                if not service_info['description']:
                    docstring_match = re.search(r'"""([^"]+)"""', content)
                    if docstring_match:
                        service_info['description'] = docstring_match.group(1).strip()
                        
            except Exception as e:
                continue
        
        # Clean up duplicates
        service_info['dependencies'] = list(set(service_info['dependencies']))
        service_info['api_endpoints'] = list(set(service_info['api_endpoints']))
        service_info['ai_integrations'] = list(set(service_info['ai_integrations']))
        
        return service_info
    
    def find_todos_and_fixmes(self) -> List[Dict[str, str]]:
        """Find all TODO and FIXME comments in code"""
        todos = []
        
        for file_path in self.activelog_root.glob("**/*"):
            if file_path.is_file() and file_path.suffix in ['.py', '.js', '.ts', '.tsx', '.jsx']:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        for i, line in enumerate(lines, 1):
                            if re.search(r'(TODO|FIXME|HACK|BUG)', line, re.IGNORECASE):
                                todos.append({
                                    'file': str(file_path.relative_to(self.activelog_root)),
                                    'line': i,
                                    'content': line.strip(),
                                    'type': re.search(r'(TODO|FIXME|HACK|BUG)', line, re.IGNORECASE).group(1).upper()
                                })
                except:
                    continue
        
        return todos
    
    def check_security_issues(self) -> List[Dict[str, str]]:
        """Check for potential security issues"""
        security_issues = []
        
        # Patterns that might indicate security issues
        security_patterns = {
            'hardcoded_key': r'(?i)(api_key|secret|password|token)\s*=\s*["\'][^"\']{10,}["\']',
            'exposed_secret': r'(?i)(sk-|pk_|ghp_|gho_|ghu_|ghs_)',
            'sql_injection': r'(?i)(execute|query)\s*\(\s*["\'].*%.*["\']',
            'dangerous_eval': r'(?i)(eval|exec)\s*\(',
            'weak_crypto': r'(?i)(md5|sha1)\s*\(',
        }
        
        for file_path in self.activelog_root.glob("**/*"):
            if file_path.is_file() and file_path.suffix in ['.py', '.js', '.ts', '.env']:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.split('\n')
                        
                        for pattern_name, pattern in security_patterns.items():
                            matches = re.finditer(pattern, content, re.MULTILINE)
                            for match in matches:
                                line_num = content[:match.start()].count('\n') + 1
                                security_issues.append({
                                    'file': str(file_path.relative_to(self.activelog_root)),
                                    'line': line_num,
                                    'issue_type': pattern_name,
                                    'content': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                                    'severity': 'HIGH' if pattern_name in ['hardcoded_key', 'exposed_secret'] else 'MEDIUM'
                                })
                except:
                    continue
        
        return security_issues
    
    def find_frontend_components(self) -> List[Dict[str, str]]:
        """Find all frontend components"""
        components = []
        
        for file_path in self.activelog_root.glob("**/*"):
            if file_path.is_file() and file_path.suffix in ['.jsx', '.tsx', '.vue', '.svelte']:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Extract component names from React/Vue components
                    component_matches = re.findall(r'(?:function|const|class)\s+([A-Z][a-zA-Z0-9]*)', content)
                    for component_name in component_matches:
                        components.append({
                            'name': component_name,
                            'file': str(file_path.relative_to(self.activelog_root)),
                            'type': file_path.suffix[1:]  # Remove the dot
                        })
                        
                except:
                    continue
        
        return components
    
    def generate_service_dependency_graph(self, services: Dict[str, Any]) -> Dict[str, List[str]]:
        """Generate service dependency graph"""
        graph = {}
        
        for service_name, service_info in services.items():
            dependencies = []
            
            # Check if this service depends on other services
            for dep in service_info['dependencies']:
                for other_service in services.keys():
                    if other_service.lower() in dep.lower() or dep.lower() in other_service.lower():
                        dependencies.append(other_service)
            
            graph[service_name] = dependencies
        
        return graph
    
    def create_json_report(self, data: Dict[str, Any]) -> str:
        """Create JSON version of the report"""
        return json.dumps(data, indent=2, default=str)
    
    def create_markdown_report(self, data: Dict[str, Any]) -> str:
        """Create Markdown version of the report"""
        md = f"""# ActiveLog System Audit Report

**Generated:** {self.report_timestamp}

## Executive Summary

- **Total Services:** {len(data.get('services', {}))}
- **Dockerized Services:** {sum(1 for s in data.get('services', {}).values() if s.get('dockerized', False))}
- **Total Code Files:** {sum(len(s.get('files', [])) for s in data.get('services', {}).values())}
- **Security Issues Found:** {len(data.get('security_issues', []))}
- **TODO/FIXME Items:** {len(data.get('todos_fixmes', []))}

## Services Overview

"""
        
        for service_name, service_info in data.get('services', {}).items():
            md += f"""### {service_name}

**Description:** {service_info.get('description', 'No description available')}
**Dockerized:** {'✅ Yes' if service_info.get('dockerized') else '❌ No'}
**Files:** {len(service_info.get('files', []))}
**Dependencies:** {len(service_info.get('dependencies', []))}
**API Endpoints:** {len(service_info.get('api_endpoints', []))}
**AI Integrations:** {', '.join(service_info.get('ai_integrations', [])) or 'None'}

"""
            
            if service_info.get('api_endpoints'):
                md += "**API Endpoints:**\n"
                for endpoint in service_info.get('api_endpoints', []):
                    md += f"- `{endpoint}`\n"
                md += "\n"
        
        md += "## Service Dependency Graph\n\n"
        for service, deps in data.get('dependency_graph', {}).items():
            if deps:
                md += f"- **{service}** depends on: {', '.join(deps)}\n"
            else:
                md += f"- **{service}** has no internal dependencies\n"
        
        if data.get('frontend_components'):
            md += "\n## Frontend Components\n\n"
            for component in data.get('frontend_components', []):
                md += f"- **{component['name']}** ({component['type']}) in `{component['file']}`\n"
        
        if data.get('security_issues'):
            md += "\n## Security Issues\n\n"
            for issue in data.get('security_issues', []):
                md += f"- **{issue['severity']}** {issue['issue_type']} in `{issue['file']}:{issue['line']}`\n"
        
        if data.get('todos_fixmes'):
            md += "\n## TODO/FIXME Items\n\n"
            for todo in data.get('todos_fixmes', []):
                md += f"- **{todo['type']}** `{todo['file']}:{todo['line']}` - {todo['content']}\n"
        
        md += f"\n## Raw Audit Output\n\n```\n{data.get('raw_output', '')}\n```\n"
        
        return md
    
    def run_full_audit(self):
        """Run the complete audit process"""
        print("Running ActiveLog audit script...")
        raw_output = self.run_audit_script()
        
        print("Analyzing services...")
        services = self.analyze_services()
        
        print("Generating dependency graph...")
        dependency_graph = self.generate_service_dependency_graph(services)
        
        print("Finding TODO/FIXME comments...")
        todos_fixmes = self.find_todos_and_fixmes()
        
        print("Checking for security issues...")
        security_issues = self.check_security_issues()
        
        print("Finding frontend components...")
        frontend_components = self.find_frontend_components()
        
        # Compile all data
        audit_data = {
            'timestamp': self.report_timestamp,
            'raw_output': raw_output,
            'parsed_sections': self.parse_audit_output(raw_output),
            'services': services,
            'dependency_graph': dependency_graph,
            'todos_fixmes': todos_fixmes,
            'security_issues': security_issues,
            'frontend_components': frontend_components,
            'summary': {
                'total_services': len(services),
                'dockerized_services': sum(1 for s in services.values() if s.get('dockerized', False)),
                'total_security_issues': len(security_issues),
                'high_severity_security_issues': len([i for i in security_issues if i['severity'] == 'HIGH']),
                'total_todos': len(todos_fixmes),
                'frontend_components_count': len(frontend_components)
            }
        }
        
        # Generate reports
        print("Generating JSON report...")
        json_report = self.create_json_report(audit_data)
        with open(self.activelog_root / "AUDIT_REPORT.json", 'w') as f:
            f.write(json_report)
        
        print("Generating Markdown report...")
        markdown_report = self.create_markdown_report(audit_data)
        with open(self.activelog_root / "AUDIT_REPORT.md", 'w') as f:
            f.write(markdown_report)
        
        print(f"Audit completed! Reports saved:")
        print(f"- JSON: {self.activelog_root}/AUDIT_REPORT.json")
        print(f"- Markdown: {self.activelog_root}/AUDIT_REPORT.md")
        
        return audit_data

if __name__ == "__main__":
    reporter = ActiveLogAuditReporter()
    reporter.run_full_audit()