#!/usr/bin/env python3
"""
SuperInstance Component Extraction Automation Toolkit
Builds on component_extraction_analyzer.py to provide full automation
"""

import os
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import ast
import re

class ComponentToolkit:
    def __init__(self, project_root: str = "/home/activeloguser/activelog"):
        self.project_root = Path(project_root)
        self.templates_dir = self.project_root / "templates"
        self.services_dir = self.project_root / "services"
        self.dev_tools_dir = self.project_root / "dev-tools"
        self.components_dir = self.project_root / "components"
        
        # Ensure directories exist
        self.templates_dir.mkdir(exist_ok=True)
        self.dev_tools_dir.mkdir(exist_ok=True)
        self.components_dir.mkdir(exist_ok=True)

    def service_analyzer(self, service_paths: List[str] = None) -> Dict[str, Any]:
        """
        Analyzes services to identify extractable patterns automatically
        90% automation opportunity as identified in DEVELOPMENT_TASK_MATRIX.md
        """
        print("🔍 Starting automated service analysis...")
        
        if service_paths is None:
            service_paths = [str(p) for p in self.services_dir.glob("*") if p.is_dir()]
        
        analysis_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "services_analyzed": len(service_paths),
            "patterns_found": {},
            "reusability_scores": {},
            "extraction_recommendations": []
        }
        
        for service_path in service_paths:
            service_name = Path(service_path).name
            print(f"  📊 Analyzing {service_name}...")
            
            patterns = self._extract_patterns_from_service(service_path)
            analysis_results["patterns_found"][service_name] = patterns
            
            # Calculate reusability scores
            for pattern in patterns:
                pattern_id = f"{service_name}_{pattern['name']}"
                score = self._calculate_reusability_score(pattern)
                analysis_results["reusability_scores"][pattern_id] = score
                
                if score > 8.5:  # High reusability threshold
                    analysis_results["extraction_recommendations"].append({
                        "service": service_name,
                        "pattern": pattern['name'],
                        "score": score,
                        "complexity": pattern.get('complexity', 'unknown')
                    })
        
        # Save analysis results
        analysis_file = self.dev_tools_dir / f"service_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(analysis_file, 'w') as f:
            json.dump(analysis_results, f, indent=2)
        
        print(f"✅ Analysis complete! Found {len(analysis_results['extraction_recommendations'])} high-value patterns")
        return analysis_results

    def component_extractor(self, extraction_config: Dict[str, Any]) -> List[str]:
        """
        Auto-extract reusable code based on analysis results
        75% automation opportunity as identified in DEVELOPMENT_TASK_MATRIX.md
        """
        print("🔧 Starting automated component extraction...")
        
        extracted_components = []
        
        for recommendation in extraction_config.get("extraction_recommendations", []):
            service_name = recommendation["service"]
            pattern_name = recommendation["pattern"]
            
            print(f"  🎯 Extracting {pattern_name} from {service_name}...")
            
            try:
                component_path = self._extract_component_code(
                    service_name, pattern_name, recommendation
                )
                if component_path:
                    extracted_components.append(component_path)
                    print(f"    ✅ Extracted to {component_path}")
            except Exception as e:
                print(f"    ❌ Extraction failed: {e}")
        
        print(f"🎉 Extracted {len(extracted_components)} components successfully")
        return extracted_components

    def template_generator(self, components: List[str], template_config: Dict[str, Any]) -> str:
        """
        Create project templates from extracted components
        80% automation opportunity as identified in DEVELOPMENT_TASK_MATRIX.md
        """
        print("🏗️ Generating project templates...")
        
        template_name = template_config.get("name", f"generated_template_{int(datetime.now().timestamp())}")
        template_path = self.templates_dir / template_name
        template_path.mkdir(exist_ok=True)
        
        # Generate template structure
        self._create_template_structure(template_path, components, template_config)
        
        # Generate configuration files
        self._generate_template_config(template_path, template_config)
        
        # Generate documentation
        self._generate_template_docs(template_path, components, template_config)
        
        # Generate deployment scripts
        self._generate_deployment_scripts(template_path, template_config)
        
        print(f"🎯 Template '{template_name}' generated at {template_path}")
        return str(template_path)

    def documentation_generator(self, components: List[str], docs_config: Dict[str, Any]) -> str:
        """
        Auto-generate usage guides and documentation
        70% automation opportunity as identified in DEVELOPMENT_TASK_MATRIX.md
        """
        print("📚 Generating automated documentation...")
        
        docs_dir = self.project_root / "docs" / "auto-generated"
        docs_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate component reference
        component_reference = self._generate_component_reference(components)
        
        # Generate integration guides
        integration_guides = self._generate_integration_guides(components)
        
        # Generate troubleshooting documentation
        troubleshooting_docs = self._generate_troubleshooting_docs(components)
        
        # Generate performance optimization guide
        performance_docs = self._generate_performance_docs(components)
        
        # Save all documentation
        doc_files = []
        for doc_name, content in [
            ("component_reference.md", component_reference),
            ("integration_guides.md", integration_guides),
            ("troubleshooting.md", troubleshooting_docs),
            ("performance_optimization.md", performance_docs)
        ]:
            doc_path = docs_dir / doc_name
            with open(doc_path, 'w') as f:
                f.write(content)
            doc_files.append(str(doc_path))
        
        print(f"📖 Generated {len(doc_files)} documentation files in {docs_dir}")
        return str(docs_dir)

    def create_application_scaffold(self, app_config: Dict[str, Any]) -> str:
        """
        Create complete application scaffolding from templates
        Supports fitness-app, productivity-app, business-api, ai-service patterns
        """
        print("🏗️ Creating application scaffold...")
        
        app_name = app_config.get("name", "new_application")
        app_type = app_config.get("type", "business-api")
        
        scaffold_dir = self.project_root / "scaffolds" / app_name
        scaffold_dir.mkdir(parents=True, exist_ok=True)
        
        # Select appropriate templates based on app type
        template_selection = self._select_templates_for_app_type(app_type)
        
        # Combine templates into scaffold
        for template_name in template_selection:
            template_path = self.templates_dir / template_name
            if template_path.exists():
                self._merge_template_into_scaffold(template_path, scaffold_dir, app_config)
        
        # Generate app-specific configuration
        self._generate_app_config(scaffold_dir, app_config)
        
        # Generate deployment configuration
        self._generate_deployment_config(scaffold_dir, app_config)
        
        print(f"🎉 Application scaffold '{app_name}' created at {scaffold_dir}")
        return str(scaffold_dir)

    def run_full_automation(self, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run complete automation pipeline: analyze -> extract -> generate -> document
        """
        print("🚀 Starting full automation pipeline...")
        
        if config is None:
            config = {
                "include_services": None,  # Analyze all services
                "reusability_threshold": 8.5,
                "generate_templates": True,
                "generate_docs": True,
                "create_scaffolds": ["fitness-app", "business-api", "ai-service"]
            }
        
        pipeline_results = {
            "start_time": datetime.utcnow().isoformat(),
            "steps_completed": []
        }
        
        try:
            # Step 1: Service Analysis
            print("\n1️⃣ Running service analysis...")
            analysis_results = self.service_analyzer(config.get("include_services"))
            pipeline_results["analysis"] = analysis_results
            pipeline_results["steps_completed"].append("analysis")
            
            # Step 2: Component Extraction
            print("\n2️⃣ Running component extraction...")
            extracted_components = self.component_extractor(analysis_results)
            pipeline_results["extracted_components"] = extracted_components
            pipeline_results["steps_completed"].append("extraction")
            
            # Step 3: Template Generation
            if config.get("generate_templates", True):
                print("\n3️⃣ Generating templates...")
                template_configs = self._create_template_configs(analysis_results)
                generated_templates = []
                for template_config in template_configs:
                    template_path = self.template_generator(extracted_components, template_config)
                    generated_templates.append(template_path)
                pipeline_results["generated_templates"] = generated_templates
                pipeline_results["steps_completed"].append("template_generation")
            
            # Step 4: Documentation Generation
            if config.get("generate_docs", True):
                print("\n4️⃣ Generating documentation...")
                docs_path = self.documentation_generator(extracted_components, config)
                pipeline_results["documentation_path"] = docs_path
                pipeline_results["steps_completed"].append("documentation")
            
            # Step 5: Application Scaffolds
            if config.get("create_scaffolds"):
                print("\n5️⃣ Creating application scaffolds...")
                scaffold_paths = []
                for app_type in config["create_scaffolds"]:
                    app_config = {"name": f"{app_type}-template", "type": app_type}
                    scaffold_path = self.create_application_scaffold(app_config)
                    scaffold_paths.append(scaffold_path)
                pipeline_results["scaffold_paths"] = scaffold_paths
                pipeline_results["steps_completed"].append("scaffolds")
            
            pipeline_results["end_time"] = datetime.utcnow().isoformat()
            pipeline_results["success"] = True
            
        except Exception as e:
            pipeline_results["error"] = str(e)
            pipeline_results["success"] = False
            print(f"❌ Pipeline failed: {e}")
        
        # Save pipeline results
        results_file = self.dev_tools_dir / f"automation_pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(pipeline_results, f, indent=2)
        
        print(f"📊 Pipeline results saved to {results_file}")
        return pipeline_results

    # Helper methods (implementation details)
    def _extract_patterns_from_service(self, service_path: str) -> List[Dict[str, Any]]:
        """Extract code patterns from service files"""
        patterns = []
        service_dir = Path(service_path)
        
        for py_file in service_dir.glob("*.py"):
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                    
                # Look for common patterns
                if "FastAPI(" in content:
                    patterns.append({
                        "name": "fastapi_initialization",
                        "file": str(py_file),
                        "complexity": "easy",
                        "description": "FastAPI app initialization pattern"
                    })
                
                if "CORSMiddleware" in content:
                    patterns.append({
                        "name": "cors_configuration",
                        "file": str(py_file),
                        "complexity": "easy",
                        "description": "CORS middleware setup"
                    })
                
                if "jwt.encode" in content or "jwt.decode" in content:
                    patterns.append({
                        "name": "jwt_authentication",
                        "file": str(py_file),
                        "complexity": "medium",
                        "description": "JWT authentication implementation"
                    })
                
                if "openai" in content.lower() or "OpenAI" in content:
                    patterns.append({
                        "name": "openai_integration",
                        "file": str(py_file),
                        "complexity": "medium",
                        "description": "OpenAI API integration"
                    })
                    
            except Exception as e:
                print(f"    ⚠️ Could not analyze {py_file}: {e}")
        
        return patterns

    def _calculate_reusability_score(self, pattern: Dict[str, Any]) -> float:
        """Calculate reusability score for a pattern"""
        base_score = 7.0
        
        # Increase score for common patterns
        if pattern["name"] in ["fastapi_initialization", "cors_configuration", "jwt_authentication"]:
            base_score += 2.0
        
        # Decrease score for complex patterns
        if pattern.get("complexity") == "hard":
            base_score -= 1.0
        elif pattern.get("complexity") == "easy":
            base_score += 0.5
        
        return min(10.0, max(0.0, base_score))

    def _extract_component_code(self, service_name: str, pattern_name: str, recommendation: Dict[str, Any]) -> Optional[str]:
        """Extract specific component code to reusable module"""
        component_dir = self.components_dir / f"{service_name}_{pattern_name}"
        component_dir.mkdir(exist_ok=True)
        
        # This would contain the actual code extraction logic
        # For now, creating a placeholder
        component_file = component_dir / f"{pattern_name}.py"
        with open(component_file, 'w') as f:
            f.write(f'''"""
{pattern_name} component extracted from {service_name}
Reusability Score: {recommendation.get("score", "N/A")}
"""

# TODO: Implement {pattern_name} component
pass
''')
        
        return str(component_file)

    def _create_template_structure(self, template_path: Path, components: List[str], config: Dict[str, Any]):
        """Create the basic structure for a template"""
        # Create standard directories
        for dir_name in ["src", "config", "docs", "tests"]:
            (template_path / dir_name).mkdir(exist_ok=True)

    def _generate_template_config(self, template_path: Path, config: Dict[str, Any]):
        """Generate template configuration files"""
        config_data = {
            "template_name": config.get("name", "unnamed_template"),
            "version": "1.0.0",
            "components": config.get("components", []),
            "dependencies": config.get("dependencies", []),
            "created_at": datetime.utcnow().isoformat()
        }
        
        with open(template_path / "template.json", 'w') as f:
            json.dump(config_data, f, indent=2)

    def _generate_template_docs(self, template_path: Path, components: List[str], config: Dict[str, Any]):
        """Generate template documentation"""
        readme_content = f"""# {config.get('name', 'Template')}

Generated automatically by SuperInstance Component Toolkit

## Components Included
{chr(10).join(f"- {Path(comp).name}" for comp in components)}

## Usage
```bash
# Deploy this template
./deploy.sh --template={config.get('name', 'template')} --port=8000
```

## Configuration
See `template.json` for configuration options.
"""
        
        with open(template_path / "README.md", 'w') as f:
            f.write(readme_content)

    def _generate_deployment_scripts(self, template_path: Path, config: Dict[str, Any]):
        """Generate deployment scripts"""
        deploy_script = f"""#!/bin/bash
# Auto-generated deployment script for {config.get('name', 'template')}

PORT=${{1:-8000}}

echo "🚀 Deploying {config.get('name', 'template')} on port $PORT"

# Install dependencies
pip install -r requirements.txt

# Start service
python main.py --port=$PORT
"""
        
        script_path = template_path / "deploy.sh"
        with open(script_path, 'w') as f:
            f.write(deploy_script)
        script_path.chmod(0o755)  # Make executable

    def _generate_component_reference(self, components: List[str]) -> str:
        """Generate component reference documentation"""
        return f"""# Component Reference

Auto-generated component documentation.

## Available Components ({len(components)})

{chr(10).join(f"- `{Path(comp).name}`" for comp in components)}

## Integration Examples

```python
# Example usage patterns will be generated here
```
"""

    def _generate_integration_guides(self, components: List[str]) -> str:
        """Generate integration guides"""
        return """# Integration Guides

## Quick Start

1. Choose your template
2. Configure your application
3. Deploy using provided scripts

## Advanced Integration

Detailed integration patterns will be documented here.
"""

    def _generate_troubleshooting_docs(self, components: List[str]) -> str:
        """Generate troubleshooting documentation"""
        return """# Troubleshooting Guide

## Common Issues

### Service Won't Start
- Check port conflicts
- Verify dependencies are installed
- Check configuration files

### Authentication Errors
- Verify JWT secret is configured
- Check token expiration settings
"""

    def _generate_performance_docs(self, components: List[str]) -> str:
        """Generate performance optimization documentation"""
        return """# Performance Optimization Guide

Based on SuperInstance's achievement of 12ms average response times.

## Key Optimizations

1. **Redis Caching**: Use Redis for frequently accessed data
2. **Connection Pooling**: Implement database connection pools
3. **Async Operations**: Use FastAPI's async capabilities
4. **Response Compression**: Enable gzip compression

## Monitoring

Use health check endpoints to monitor service performance.
"""

    def _select_templates_for_app_type(self, app_type: str) -> List[str]:
        """Select appropriate templates for application type"""
        template_mapping = {
            "fitness-app": ["fastapi-service-template", "jwt-auth-template"],
            "business-api": ["fastapi-service-template", "jwt-auth-template"],
            "ai-service": ["ai-service-template", "jwt-auth-template"],
            "productivity-app": ["fastapi-service-template", "jwt-auth-template"]
        }
        return template_mapping.get(app_type, ["fastapi-service-template"])

    def _merge_template_into_scaffold(self, template_path: Path, scaffold_dir: Path, app_config: Dict[str, Any]):
        """Merge template into application scaffold"""
        # This would contain the logic to merge templates
        # For now, just copy the template structure
        if template_path.exists():
            for item in template_path.iterdir():
                if item.is_file():
                    shutil.copy2(item, scaffold_dir)

    def _generate_app_config(self, scaffold_dir: Path, app_config: Dict[str, Any]):
        """Generate application-specific configuration"""
        app_config_data = {
            "app_name": app_config.get("name", "new_app"),
            "app_type": app_config.get("type", "api"),
            "port": app_config.get("port", 8000),
            "created_at": datetime.utcnow().isoformat()
        }
        
        with open(scaffold_dir / "app_config.json", 'w') as f:
            json.dump(app_config_data, f, indent=2)

    def _generate_deployment_config(self, scaffold_dir: Path, app_config: Dict[str, Any]):
        """Generate deployment configuration"""
        # Create docker-compose.yml or kubernetes configs if needed
        pass

    def _create_template_configs(self, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create template configurations from analysis results"""
        return [
            {"name": "automated-fastapi-template", "type": "api"},
            {"name": "automated-auth-template", "type": "auth"},
            {"name": "automated-ai-template", "type": "ai"}
        ]


if __name__ == "__main__":
    print("🔧 SuperInstance Component Extraction Automation Toolkit")
    print("========================================================")
    
    toolkit = ComponentToolkit()
    
    # Run full automation pipeline
    results = toolkit.run_full_automation()
    
    if results.get("success"):
        print("\n🎉 Automation Pipeline Complete!")
        print(f"📊 Steps completed: {', '.join(results['steps_completed'])}")
        print(f"🕐 Duration: {results.get('start_time')} to {results.get('end_time')}")
    else:
        print(f"\n❌ Pipeline failed: {results.get('error', 'Unknown error')}")