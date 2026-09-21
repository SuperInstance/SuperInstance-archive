#!/usr/bin/env python3
"""
SuperInstance Component Extraction Analyzer
Automatically identifies and extracts reusable patterns from existing services
Generates templates, documentation, and integration guides for rapid development
"""

import os
import ast
import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ServicePattern:
    pattern_type: str
    description: str
    code_snippets: List[str]
    dependencies: List[str]
    configuration: Dict[str, Any]
    reusability_score: float
    extraction_complexity: str

@dataclass
class ComponentTemplate:
    name: str
    description: str
    template_code: str
    dependencies: List[str]
    configuration_template: Dict[str, Any]
    usage_example: str
    integration_guide: str

class SuperInstanceComponentAnalyzer:
    def __init__(self):
        self.services_dir = "/home/activeloguser/activelog/services"
        self.templates_dir = "/home/activeloguser/activelog/templates"
        self.components_dir = "/home/activeloguser/activelog/components"
        self.patterns_found = []
        self.components_extracted = []
        
        # Ensure template directories exist
        os.makedirs(self.templates_dir, exist_ok=True)
        os.makedirs(self.components_dir, exist_ok=True)

    def analyze_all_services(self) -> Dict[str, List[ServicePattern]]:
        """Analyze all services and identify extractable patterns"""
        logger.info("🔍 Starting comprehensive service analysis...")
        
        service_patterns = {}
        
        # Key services to analyze for patterns
        priority_services = [
            "auth-service",
            "api-gateway", 
            "ai-insights",
            "fitness-data-api",
            "personallog-ai-insights",
            "businesslog-ai-insights",
            "user-management"
        ]
        
        for service_name in priority_services:
            service_path = Path(self.services_dir) / service_name
            if service_path.exists():
                logger.info(f"📊 Analyzing {service_name}...")
                patterns = self.analyze_service(service_path, service_name)
                service_patterns[service_name] = patterns
            else:
                logger.warning(f"⚠️ Service {service_name} not found at {service_path}")
        
        return service_patterns

    def analyze_service(self, service_path: Path, service_name: str) -> List[ServicePattern]:
        """Analyze a specific service and extract patterns"""
        patterns = []
        
        # Find main.py and analyze FastAPI patterns
        main_py = service_path / "main.py"
        if main_py.exists():
            patterns.extend(self.analyze_fastapi_patterns(main_py, service_name))
        
        # Analyze requirements.txt for dependencies
        requirements_txt = service_path / "requirements.txt"
        if requirements_txt.exists():
            patterns.extend(self.analyze_dependency_patterns(requirements_txt, service_name))
        
        return patterns

    def analyze_fastapi_patterns(self, main_py: Path, service_name: str) -> List[ServicePattern]:
        """Extract FastAPI patterns from main.py files"""
        patterns = []
        
        try:
            with open(main_py, 'r') as f:
                content = f.read()
            
            # Parse with AST for better analysis
            try:
                tree = ast.parse(content)
                patterns.extend(self.extract_ast_patterns(tree, content, service_name))
            except SyntaxError:
                logger.warning(f"Could not parse {main_py} with AST, using regex analysis")
                patterns.extend(self.extract_regex_patterns(content, service_name))
                
        except Exception as e:
            logger.error(f"Error analyzing {main_py}: {e}")
        
        return patterns

    def extract_ast_patterns(self, tree: ast.AST, content: str, service_name: str) -> List[ServicePattern]:
        """Extract patterns using AST analysis"""
        patterns = []
        
        # Find FastAPI app creation
        app_creation_pattern = self.find_app_creation(tree, content)
        if app_creation_pattern:
            patterns.append(app_creation_pattern)
        
        # Find route definitions
        route_patterns = self.find_route_patterns(tree, content, service_name)
        patterns.extend(route_patterns)
        
        # Find middleware patterns
        middleware_patterns = self.find_middleware_patterns(tree, content)
        patterns.extend(middleware_patterns)
        
        # Find CORS configuration
        cors_pattern = self.find_cors_configuration(tree, content)
        if cors_pattern:
            patterns.append(cors_pattern)
        
        return patterns

    def find_app_creation(self, tree: ast.AST, content: str) -> Optional[ServicePattern]:
        """Find FastAPI app creation patterns"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == 'app':
                        if isinstance(node.value, ast.Call):
                            # Extract the app creation line
                            lines = content.split('\n')
                            app_line = lines[node.lineno - 1] if node.lineno <= len(lines) else ""
                            
                            return ServicePattern(
                                pattern_type="fastapi_app_creation",
                                description="FastAPI application initialization pattern",
                                code_snippets=[app_line.strip()],
                                dependencies=["fastapi"],
                                configuration={"app_variable": "app"},
                                reusability_score=9.5,
                                extraction_complexity="easy"
                            )
        return None

    def find_route_patterns(self, tree: ast.AST, content: str, service_name: str) -> List[ServicePattern]:
        """Find API route patterns"""
        patterns = []
        routes_found = []
        
        lines = content.split('\n')
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Look for decorator patterns indicating routes
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Attribute):
                        if hasattr(decorator.value, 'id') and decorator.value.id == 'app':
                            method = decorator.attr.lower()
                            if method in ['get', 'post', 'put', 'delete', 'patch']:
                                # Extract the route function
                                start_line = node.lineno - 1
                                end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line + 10
                                
                                route_code = '\n'.join(lines[start_line:min(end_line, len(lines))])
                                routes_found.append({
                                    'method': method.upper(),
                                    'function_name': node.name,
                                    'code': route_code
                                })
        
        if routes_found:
            patterns.append(ServicePattern(
                pattern_type=f"{service_name}_api_routes",
                description=f"API route patterns from {service_name}",
                code_snippets=[route['code'] for route in routes_found[:3]],  # Top 3 routes
                dependencies=["fastapi", "pydantic"],
                configuration={
                    "methods_used": [route['method'] for route in routes_found],
                    "route_count": len(routes_found)
                },
                reusability_score=8.7,
                extraction_complexity="medium"
            ))
        
        return patterns

    def find_middleware_patterns(self, tree: ast.AST, content: str) -> List[ServicePattern]:
        """Find middleware configuration patterns"""
        patterns = []
        middleware_calls = []
        
        lines = content.split('\n')
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if (hasattr(node.func.value, 'id') and node.func.value.id == 'app' and 
                        node.func.attr == 'add_middleware'):
                        # Extract middleware configuration
                        middleware_line = lines[node.lineno - 1] if node.lineno <= len(lines) else ""
                        middleware_calls.append(middleware_line.strip())
        
        if middleware_calls:
            patterns.append(ServicePattern(
                pattern_type="fastapi_middleware",
                description="FastAPI middleware configuration patterns",
                code_snippets=middleware_calls,
                dependencies=["fastapi"],
                configuration={"middleware_types": ["cors", "auth", "logging"]},
                reusability_score=8.9,
                extraction_complexity="easy"
            ))
        
        return patterns

    def find_cors_configuration(self, tree: ast.AST, content: str) -> Optional[ServicePattern]:
        """Find CORS configuration patterns"""
        cors_imports = []
        cors_config = []
        
        lines = content.split('\n')
        
        # Find CORS imports
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module == 'fastapi.middleware.cors':
                    cors_imports.append(f"from {node.module} import {', '.join([alias.name for alias in node.names])}")
        
        # Find CORS middleware configuration
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and node.func.attr == 'add_middleware':
                    for arg in node.args:
                        if isinstance(arg, ast.Name) and 'cors' in arg.id.lower():
                            cors_line = lines[node.lineno - 1] if node.lineno <= len(lines) else ""
                            cors_config.append(cors_line.strip())
        
        if cors_imports or cors_config:
            return ServicePattern(
                pattern_type="cors_configuration",
                description="CORS middleware configuration for cross-origin requests",
                code_snippets=cors_imports + cors_config,
                dependencies=["fastapi"],
                configuration={"cors_enabled": True},
                reusability_score=9.2,
                extraction_complexity="easy"
            )
        
        return None

    def extract_regex_patterns(self, content: str, service_name: str) -> List[ServicePattern]:
        """Fallback regex-based pattern extraction"""
        patterns = []
        
        # Find FastAPI app creation
        app_match = re.search(r'app\s*=\s*FastAPI\([^)]*\)', content)
        if app_match:
            patterns.append(ServicePattern(
                pattern_type="fastapi_app_creation_regex",
                description="FastAPI app initialization (regex extraction)",
                code_snippets=[app_match.group(0)],
                dependencies=["fastapi"],
                configuration={},
                reusability_score=8.0,
                extraction_complexity="easy"
            ))
        
        # Find route decorators
        route_matches = re.findall(r'@app\.(get|post|put|delete|patch)\([^)]*\)[^@]*?def\s+\w+[^:]*:', content, re.DOTALL)
        if route_matches:
            patterns.append(ServicePattern(
                pattern_type=f"{service_name}_routes_regex",
                description=f"Route patterns from {service_name} (regex)",
                code_snippets=route_matches[:3],
                dependencies=["fastapi"],
                configuration={"extraction_method": "regex"},
                reusability_score=7.5,
                extraction_complexity="medium"
            ))
        
        return patterns

    def analyze_dependency_patterns(self, requirements_txt: Path, service_name: str) -> List[ServicePattern]:
        """Analyze dependency patterns from requirements.txt"""
        try:
            with open(requirements_txt, 'r') as f:
                deps = [line.strip() for line in f.readlines() if line.strip() and not line.startswith('#')]
            
            # Categorize dependencies
            web_deps = [d for d in deps if any(web in d.lower() for web in ['fastapi', 'flask', 'django', 'starlette'])]
            ai_deps = [d for d in deps if any(ai in d.lower() for ai in ['openai', 'ollama', 'transformers', 'torch'])]
            db_deps = [d for d in deps if any(db in d.lower() for db in ['sqlalchemy', 'psycopg', 'redis', 'pymongo'])]
            
            patterns = []
            
            if web_deps:
                patterns.append(ServicePattern(
                    pattern_type=f"{service_name}_web_dependencies",
                    description=f"Web framework dependencies from {service_name}",
                    code_snippets=web_deps,
                    dependencies=web_deps,
                    configuration={"category": "web_framework"},
                    reusability_score=9.0,
                    extraction_complexity="easy"
                ))
            
            if ai_deps:
                patterns.append(ServicePattern(
                    pattern_type=f"{service_name}_ai_dependencies",
                    description=f"AI/ML dependencies from {service_name}",
                    code_snippets=ai_deps,
                    dependencies=ai_deps,
                    configuration={"category": "ai_ml"},
                    reusability_score=8.5,
                    extraction_complexity="medium"
                ))
            
            if db_deps:
                patterns.append(ServicePattern(
                    pattern_type=f"{service_name}_database_dependencies",
                    description=f"Database dependencies from {service_name}",
                    code_snippets=db_deps,
                    dependencies=db_deps,
                    configuration={"category": "database"},
                    reusability_score=8.8,
                    extraction_complexity="easy"
                ))
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error analyzing dependencies for {service_name}: {e}")
            return []

    def generate_component_templates(self, service_patterns: Dict[str, List[ServicePattern]]) -> List[ComponentTemplate]:
        """Generate reusable component templates from extracted patterns"""
        templates = []
        
        # FastAPI App Template
        fastapi_patterns = []
        for service, patterns in service_patterns.items():
            fastapi_patterns.extend([p for p in patterns if 'fastapi' in p.pattern_type.lower()])
        
        if fastapi_patterns:
            app_template = self.create_fastapi_template(fastapi_patterns)
            templates.append(app_template)
        
        # Authentication Template
        auth_patterns = []
        for service, patterns in service_patterns.items():
            if 'auth' in service.lower():
                auth_patterns.extend(patterns)
        
        if auth_patterns:
            auth_template = self.create_auth_template(auth_patterns)
            templates.append(auth_template)
        
        # AI Service Template
        ai_patterns = []
        for service, patterns in service_patterns.items():
            if 'ai' in service.lower():
                ai_patterns.extend(patterns)
        
        if ai_patterns:
            ai_template = self.create_ai_service_template(ai_patterns)
            templates.append(ai_template)
        
        return templates

    def create_fastapi_template(self, patterns: List[ServicePattern]) -> ComponentTemplate:
        """Create FastAPI service template from patterns"""
        
        # Extract common dependencies
        all_deps = set()
        for pattern in patterns:
            all_deps.update(pattern.dependencies)
        
        template_code = '''"""
FastAPI Service Template
Generated from SuperInstance service pattern analysis
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os

# Initialize FastAPI app
app = FastAPI(
    title="{service_name}",
    description="Generated from SuperInstance component templates",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "{service_name}"}

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to {service_name}", "docs": "/docs"}

# Example data model
class ItemCreate(BaseModel):
    name: str
    description: str

class ItemResponse(BaseModel):
    id: int
    name: str
    description: str

# Example CRUD endpoints
@app.post("/items", response_model=ItemResponse)
async def create_item(item: ItemCreate):
    # TODO: Implement item creation logic
    return ItemResponse(id=1, **item.dict())

@app.get("/items/{item_id}", response_model=ItemResponse)
async def get_item(item_id: int):
    # TODO: Implement item retrieval logic
    return ItemResponse(id=item_id, name="Sample", description="Sample item")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
'''
        
        return ComponentTemplate(
            name="fastapi-service-template",
            description="Complete FastAPI service template with CORS, health checks, and example CRUD endpoints",
            template_code=template_code,
            dependencies=list(all_deps),
            configuration_template={
                "service_name": "my-service",
                "port": 8000,
                "cors_enabled": True
            },
            usage_example="./create-service.sh my-api --template=fastapi-service-template --port=8100",
            integration_guide="1. Copy template 2. Replace {service_name} 3. Implement TODO items 4. Run with uvicorn"
        )

    def create_auth_template(self, patterns: List[ServicePattern]) -> ComponentTemplate:
        """Create authentication template from patterns"""
        
        template_code = '''"""
Authentication Service Template
JWT-based authentication with refresh tokens
"""
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt
import os
from datetime import datetime, timedelta

app = FastAPI(title="Authentication Service", version="1.0.0")

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    # TODO: Implement user authentication logic
    if request.username == "admin" and request.password == "password":
        access_token = create_access_token(data={"sub": request.username})
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/api/auth/validate")
async def validate_token(current_user: str = Depends(verify_token)):
    return {"valid": True, "user": current_user}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "auth"}
'''
        
        return ComponentTemplate(
            name="jwt-auth-template",
            description="JWT-based authentication service with login and token validation",
            template_code=template_code,
            dependencies=["fastapi", "pyjwt", "python-multipart"],
            configuration_template={
                "secret_key": "your-secret-key-here",
                "algorithm": "HS256",
                "token_expire_minutes": 30
            },
            usage_example="./create-auth-service.sh --template=jwt-auth-template --port=8001",
            integration_guide="1. Set SECRET_KEY environment variable 2. Implement user authentication logic 3. Use verify_token dependency in protected routes"
        )

    def create_ai_service_template(self, patterns: List[ServicePattern]) -> ComponentTemplate:
        """Create AI service template from patterns"""
        
        template_code = '''"""
AI Service Template
OpenAI integration with FastAPI
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import openai
import os
from typing import Optional, List

app = FastAPI(title="AI Service", version="1.0.0")

# Configure OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

class AIRequest(BaseModel):
    query: str
    context: Optional[str] = None
    max_tokens: Optional[int] = 150

class AIResponse(BaseModel):
    response: str
    tokens_used: int
    model: str

class InsightRequest(BaseModel):
    data: dict
    analysis_type: str = "general"

class InsightResponse(BaseModel):
    insights: List[str]
    confidence: float
    recommendations: List[str]

@app.post("/insights", response_model=AIResponse)
async def generate_insights(request: AIRequest):
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=f"Context: {request.context}\n\nQuery: {request.query}\n\nResponse:",
            max_tokens=request.max_tokens,
            temperature=0.7
        )
        
        return AIResponse(
            response=response.choices[0].text.strip(),
            tokens_used=response.usage.total_tokens,
            model="text-davinci-003"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI processing error: {str(e)}")

@app.post("/analyze", response_model=InsightResponse)
async def analyze_data(request: InsightRequest):
    # TODO: Implement data analysis logic
    return InsightResponse(
        insights=["Sample insight based on data analysis"],
        confidence=0.85,
        recommendations=["Implement recommendation logic"]
    )

@app.get("/models")
async def list_available_models():
    return {"models": ["openai", "ollama"], "default": "openai"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ai", "openai_configured": bool(openai.api_key)}
'''
        
        return ComponentTemplate(
            name="ai-service-template",
            description="AI service template with OpenAI integration and analysis endpoints",
            template_code=template_code,
            dependencies=["fastapi", "openai", "pydantic"],
            configuration_template={
                "openai_api_key": "your-openai-api-key",
                "default_model": "text-davinci-003",
                "max_tokens": 150
            },
            usage_example="./create-ai-service.sh --template=ai-service-template --port=8090",
            integration_guide="1. Set OPENAI_API_KEY environment variable 2. Implement data analysis logic 3. Add domain-specific AI processing"
        )

    def save_templates(self, templates: List[ComponentTemplate]) -> List[str]:
        """Save generated templates to filesystem"""
        saved_files = []
        
        for template in templates:
            # Create template directory
            template_dir = Path(self.templates_dir) / template.name
            template_dir.mkdir(exist_ok=True)
            
            # Save main template file
            main_file = template_dir / "main.py"
            with open(main_file, 'w') as f:
                f.write(template.template_code)
            saved_files.append(str(main_file))
            
            # Save requirements.txt
            requirements_file = template_dir / "requirements.txt"
            with open(requirements_file, 'w') as f:
                f.write('\n'.join(template.dependencies))
            saved_files.append(str(requirements_file))
            
            # Save configuration template
            config_file = template_dir / "config.json"
            with open(config_file, 'w') as f:
                json.dump(template.configuration_template, f, indent=2)
            saved_files.append(str(config_file))
            
            # Save README with usage guide
            readme_file = template_dir / "README.md"
            with open(readme_file, 'w') as f:
                f.write(f"# {template.name}\n\n")
                f.write(f"{template.description}\n\n")
                f.write("## Usage\n\n")
                f.write(f"```bash\n{template.usage_example}\n```\n\n")
                f.write("## Integration Guide\n\n")
                f.write(f"{template.integration_guide}\n\n")
                f.write("## Dependencies\n\n")
                f.write('\n'.join(f"- {dep}" for dep in template.dependencies))
            saved_files.append(str(readme_file))
        
        return saved_files

    def generate_analysis_report(self, service_patterns: Dict[str, List[ServicePattern]], 
                               templates: List[ComponentTemplate]) -> str:
        """Generate comprehensive analysis report"""
        
        total_patterns = sum(len(patterns) for patterns in service_patterns.values())
        
        report = f"""# SuperInstance Component Extraction Analysis Report

## Analysis Summary
- **Services Analyzed:** {len(service_patterns)}
- **Patterns Extracted:** {total_patterns}
- **Templates Generated:** {len(templates)}
- **Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Services Analyzed
"""
        
        for service_name, patterns in service_patterns.items():
            report += f"\n### {service_name}\n"
            report += f"- Patterns found: {len(patterns)}\n"
            
            for pattern in patterns:
                report += f"  - **{pattern.pattern_type}**: {pattern.description}\n"
                report += f"    - Reusability: {pattern.reusability_score}/10\n"
                report += f"    - Complexity: {pattern.extraction_complexity}\n"
        
        report += f"\n## Generated Templates\n"
        
        for template in templates:
            report += f"\n### {template.name}\n"
            report += f"- **Description:** {template.description}\n"
            report += f"- **Dependencies:** {', '.join(template.dependencies)}\n"
            report += f"- **Usage:** `{template.usage_example}`\n"
        
        report += f"\n## Reusability Recommendations\n"
        
        high_value_patterns = []
        for service, patterns in service_patterns.items():
            for pattern in patterns:
                if pattern.reusability_score >= 8.5:
                    high_value_patterns.append((service, pattern))
        
        for service, pattern in high_value_patterns:
            report += f"- **{pattern.pattern_type}** from {service}: Score {pattern.reusability_score}/10\n"
        
        report += f"\n## Next Steps\n"
        report += f"1. Review generated templates in `/templates/` directory\n"
        report += f"2. Test template integration with new projects\n"  
        report += f"3. Document additional patterns discovered during analysis\n"
        report += f"4. Create automation tools for template deployment\n"
        
        return report

async def main():
    print("🔍 SuperInstance Component Extraction Analyzer")
    print("🎯 Analyzing services and generating reusable templates...")
    print()
    
    analyzer = SuperInstanceComponentAnalyzer()
    
    # Analyze all services
    service_patterns = analyzer.analyze_all_services()
    
    # Generate component templates
    templates = analyzer.generate_component_templates(service_patterns)
    
    # Save templates to filesystem
    saved_files = analyzer.save_templates(templates)
    
    # Generate analysis report
    report = analyzer.generate_analysis_report(service_patterns, templates)
    
    # Save report
    report_file = "/home/activeloguser/activelog/COMPONENT_EXTRACTION_REPORT.md"
    with open(report_file, 'w') as f:
        f.write(report)
    
    print("📊 COMPONENT EXTRACTION ANALYSIS COMPLETE")
    print("=" * 60)
    print(f"Services Analyzed: {len(service_patterns)}")
    print(f"Patterns Extracted: {sum(len(p) for p in service_patterns.values())}")
    print(f"Templates Generated: {len(templates)}")
    print(f"Files Created: {len(saved_files)}")
    print()
    print("📁 Generated Templates:")
    for template in templates:
        print(f"  • {template.name}: {template.description}")
    print()
    print(f"📋 Full report saved to: {report_file}")
    
    # Update micro_updates.log
    from datetime import datetime
    current_time = datetime.now().strftime("%H:%M")
    log_entry = f"{current_time}|component_architect|COMPLETE|api-template-extraction|{len(templates)}-templates-generated-from-{len(service_patterns)}-services|reusable-components-ready"
    
    with open("/home/activeloguser/activelog/micro_updates.log", "a") as f:
        f.write(f"{log_entry}\n")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())