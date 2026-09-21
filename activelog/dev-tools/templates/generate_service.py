#!/usr/bin/env python3
"""
ActiveLog Service Code Generator
Generates new services from templates with boilerplate code.
"""

import os
import sys
import shutil
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import re


class ServiceGenerator:
    """Generates new services from templates."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.templates_dir = Path(__file__).parent / "service_templates"
        self.available_templates = self._discover_templates()
    
    def _discover_templates(self) -> List[str]:
        """Discover available service templates."""
        if not self.templates_dir.exists():
            return []
        
        templates = []
        for item in self.templates_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                templates.append(item.name)
        
        return templates
    
    def generate_service(
        self,
        service_name: str,
        template_name: str,
        port: Optional[int] = None,
        description: Optional[str] = None
    ):
        """Generate a new service from template."""
        print(f"🏗️  Generating service: {service_name}")
        print(f"📋 Template: {template_name}")
        
        # Validate inputs
        if not self._is_valid_service_name(service_name):
            raise ValueError(f"Invalid service name: {service_name}")
        
        if template_name not in self.available_templates:
            raise ValueError(f"Unknown template: {template_name}. Available: {', '.join(self.available_templates)}")
        
        # Generate port if not provided
        if port is None:
            port = self._find_available_port()
        
        # Prepare template variables
        template_vars = self._prepare_template_variables(
            service_name, port, description
        )
        
        # Create service directory
        service_dir = self.project_root / "services" / service_name
        if service_dir.exists():
            raise ValueError(f"Service directory already exists: {service_dir}")
        
        service_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Copy and process template files
            template_dir = self.templates_dir / template_name
            self._process_template_directory(template_dir, service_dir, template_vars)
            
            # Update project configuration
            self._update_project_config(service_name, port, description)
            
            # Create tests directory
            self._create_test_structure(service_name, template_vars)
            
            # Update documentation
            self._update_documentation(service_name, template_vars)
            
            print(f"✅ Service {service_name} generated successfully!")
            self._print_next_steps(service_name, port)
            
        except Exception as e:
            # Clean up on failure
            if service_dir.exists():
                shutil.rmtree(service_dir)
            raise e
    
    def _is_valid_service_name(self, name: str) -> bool:
        """Validate service name."""
        # Must be valid Python module name
        return re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', name) is not None
    
    def _find_available_port(self) -> int:
        """Find an available port for the service."""
        # Start from 8010 and find the first available port
        used_ports = self._get_used_ports()
        
        for port in range(8010, 8100):
            if port not in used_ports:
                return port
        
        raise RuntimeError("No available ports found")
    
    def _get_used_ports(self) -> set:
        """Get ports already used by other services."""
        used_ports = set()
        
        # Check CLI config
        cli_config = self.project_root / "dev-tools" / "cli" / "config.yml"
        if cli_config.exists():
            import yaml
            with open(cli_config) as f:
                config = yaml.safe_load(f)
                for service_info in config.get('services', {}).values():
                    if 'port' in service_info:
                        used_ports.add(service_info['port'])
        
        return used_ports
    
    def _prepare_template_variables(
        self,
        service_name: str,
        port: int,
        description: Optional[str]
    ) -> Dict[str, Any]:
        """Prepare template variables for substitution."""
        # Convert service_name to different cases
        snake_case = service_name.lower()
        pascal_case = ''.join(word.capitalize() for word in snake_case.split('_'))
        kebab_case = snake_case.replace('_', '-')
        title_case = ' '.join(word.capitalize() for word in snake_case.split('_'))
        
        return {
            'SERVICE_NAME': service_name,
            'SERVICE_NAME_SNAKE': snake_case,
            'SERVICE_NAME_PASCAL': pascal_case,
            'SERVICE_NAME_KEBAB': kebab_case,
            'SERVICE_NAME_TITLE': title_case,
            'SERVICE_NAME_UPPER': snake_case.upper(),
            'SERVICE_PORT': port,
            'SERVICE_DESCRIPTION': description or f"{title_case} Service",
            'GENERATED_DATE': datetime.now().strftime('%Y-%m-%d'),
            'GENERATED_TIMESTAMP': datetime.now().isoformat(),
            'AUTHOR': os.environ.get('USER', 'Developer'),
        }
    
    def _process_template_directory(
        self,
        template_dir: Path,
        output_dir: Path,
        template_vars: Dict[str, Any]
    ):
        """Process template directory recursively."""
        for item in template_dir.iterdir():
            if item.name.startswith('.'):
                continue
            
            # Process filename template variables
            output_name = self._substitute_variables(item.name, template_vars)
            output_path = output_dir / output_name
            
            if item.is_file():
                # Process file content
                self._process_template_file(item, output_path, template_vars)
            elif item.is_dir():
                # Process directory recursively
                output_path.mkdir(exist_ok=True)
                self._process_template_directory(item, output_path, template_vars)
    
    def _process_template_file(
        self,
        template_file: Path,
        output_file: Path,
        template_vars: Dict[str, Any]
    ):
        """Process a single template file."""
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Substitute template variables
            processed_content = self._substitute_variables(content, template_vars)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(processed_content)
                
        except UnicodeDecodeError:
            # Binary file, copy as-is
            shutil.copy2(template_file, output_file)
    
    def _substitute_variables(self, text: str, variables: Dict[str, Any]) -> str:
        """Substitute template variables in text."""
        result = text
        
        for key, value in variables.items():
            # Replace {{VARIABLE}} patterns
            result = result.replace(f'{{{{{key}}}}}', str(value))
        
        return result
    
    def _update_project_config(self, service_name: str, port: int, description: str):
        """Update project configuration files."""
        # Update CLI config
        cli_config_path = self.project_root / "dev-tools" / "cli" / "config.yml"
        
        if cli_config_path.exists():
            import yaml
            
            with open(cli_config_path) as f:
                config = yaml.safe_load(f)
            
            # Add new service
            if 'services' not in config:
                config['services'] = {}
            
            config['services'][service_name] = {
                'port': port,
                'path': f'services/{service_name}',
                'description': description,
                'health_endpoint': '/health',
                'dependencies': ['postgres']  # Default dependencies
            }
            
            with open(cli_config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
        
        # Update docker-compose configuration
        self._update_docker_compose(service_name, port)
    
    def _update_docker_compose(self, service_name: str, port: int):
        """Update Docker Compose configuration."""
        compose_file = self.project_root / "docker-compose.dev.yml"
        
        if compose_file.exists():
            import yaml
            
            with open(compose_file) as f:
                compose_config = yaml.safe_load(f)
            
            # Add service configuration
            if 'services' not in compose_config:
                compose_config['services'] = {}
            
            service_config = {
                'build': {
                    'context': '.',
                    'dockerfile': f'services/{service_name}/Dockerfile'
                },
                'container_name': f'activelog-{service_name}',
                'ports': [f'{port}:{port}'],
                'environment': [
                    'ENVIRONMENT=development',
                    f'SERVICE_NAME={service_name}',
                    'DATABASE_URL=postgresql://activelog:password@postgres:5432/activelog',
                    'REDIS_URL=redis://redis:6379/0'
                ],
                'depends_on': ['postgres', 'redis'],
                'volumes': [f'./services/{service_name}:/app'],
                'networks': ['activelog-network']
            }
            
            compose_config['services'][service_name] = service_config
            
            with open(compose_file, 'w') as f:
                yaml.dump(compose_config, f, default_flow_style=False)
    
    def _create_test_structure(self, service_name: str, template_vars: Dict[str, Any]):
        """Create test structure for the service."""
        tests_dir = self.project_root / "tests" / "services" / service_name
        tests_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test files
        test_files = {
            '__init__.py': '',
            'test_main.py': self._generate_test_main(template_vars),
            'test_models.py': self._generate_test_models(template_vars),
            'test_api.py': self._generate_test_api(template_vars),
            'conftest.py': self._generate_test_conftest(template_vars)
        }
        
        for filename, content in test_files.items():
            test_file = tests_dir / filename
            with open(test_file, 'w') as f:
                f.write(content)
    
    def _generate_test_main(self, template_vars: Dict[str, Any]) -> str:
        """Generate main test file."""
        return f'''"""
Tests for {template_vars['SERVICE_NAME_TITLE']} service main module.
Generated on {template_vars['GENERATED_DATE']}
"""

import pytest
from fastapi.testclient import TestClient
from {template_vars['SERVICE_NAME_SNAKE']}.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_service_info(client):
    """Test service info endpoint."""
    response = client.get("/info")
    assert response.status_code == 200
    data = response.json()
    assert data["service_name"] == "{template_vars['SERVICE_NAME_SNAKE']}"
    assert "version" in data
'''
    
    def _generate_test_models(self, template_vars: Dict[str, Any]) -> str:
        """Generate models test file."""
        return f'''"""
Tests for {template_vars['SERVICE_NAME_TITLE']} service models.
Generated on {template_vars['GENERATED_DATE']}
"""

import pytest
from pydantic import ValidationError
from {template_vars['SERVICE_NAME_SNAKE']}.models import *


def test_base_model_creation():
    """Test base model creation and validation."""
    # Add your model tests here
    pass


def test_model_validation():
    """Test model validation."""
    # Add validation tests here
    pass
'''
    
    def _generate_test_api(self, template_vars: Dict[str, Any]) -> str:
        """Generate API test file."""
        return f'''"""
Tests for {template_vars['SERVICE_NAME_TITLE']} service API endpoints.
Generated on {template_vars['GENERATED_DATE']}
"""

import pytest
from fastapi.testclient import TestClient
from {template_vars['SERVICE_NAME_SNAKE']}.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Authentication headers fixture."""
    return {{"Authorization": "Bearer test-token"}}


def test_api_endpoints(client, auth_headers):
    """Test main API endpoints."""
    # Add your API tests here
    pass


def test_authentication_required(client):
    """Test that authentication is required for protected endpoints."""
    # Add authentication tests here
    pass
'''
    
    def _generate_test_conftest(self, template_vars: Dict[str, Any]) -> str:
        """Generate conftest.py for tests."""
        return f'''"""
Test configuration for {template_vars['SERVICE_NAME_TITLE']} service.
Generated on {template_vars['GENERATED_DATE']}
"""

import pytest
import asyncio
from unittest.mock import Mock
from {template_vars['SERVICE_NAME_SNAKE']}.database import get_database


@pytest.fixture
def mock_db():
    """Mock database fixture."""
    return Mock()


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def override_dependencies(mock_db):
    """Override dependencies for testing."""
    from {template_vars['SERVICE_NAME_SNAKE']}.main import app
    
    app.dependency_overrides[get_database] = lambda: mock_db
    yield
    app.dependency_overrides.clear()
'''
    
    def _update_documentation(self, service_name: str, template_vars: Dict[str, Any]):
        """Update documentation with new service."""
        # Create service README
        service_readme = self.project_root / "services" / service_name / "README.md"
        
        readme_content = f'''# {template_vars['SERVICE_NAME_TITLE']}

{template_vars['SERVICE_DESCRIPTION']}

## Overview

This service was generated on {template_vars['GENERATED_DATE']} using the ActiveLog service generator.

## Configuration

- **Port**: {template_vars['SERVICE_PORT']}
- **Health Check**: `GET /health`
- **API Documentation**: `GET /docs`

## Development

### Running the Service

```bash
# Using the CLI
python dev-tools/cli/activelog_cli.py services start {service_name}

# Direct execution
cd services/{service_name}
python -m uvicorn main:app --host 0.0.0.0 --port {template_vars['SERVICE_PORT']} --reload
```

### Testing

```bash
# Run service tests
python -m pytest tests/services/{service_name}/

# Run with coverage
python -m pytest tests/services/{service_name}/ --cov=services/{service_name}
```

### API Endpoints

- `GET /health` - Health check
- `GET /info` - Service information
- `GET /docs` - API documentation (Swagger UI)
- `GET /redoc` - API documentation (ReDoc)

## Dependencies

- FastAPI
- Pydantic
- SQLAlchemy (if using database)
- Redis (if using caching)

## Environment Variables

- `DATABASE_URL` - Database connection string
- `REDIS_URL` - Redis connection string
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `ENVIRONMENT` - Environment (development, staging, production)

## Contributing

1. Make changes to the service code
2. Add/update tests
3. Run tests and ensure they pass
4. Update documentation if needed
5. Submit a pull request

## Generated Files

This service was generated from the `{template_vars.get("TEMPLATE_NAME", "default")}` template and includes:

- FastAPI application setup
- Basic API endpoints
- Database models (if applicable)
- Test structure
- Docker configuration
- Documentation

## Next Steps

1. Customize the generated code for your specific requirements
2. Add your business logic
3. Implement additional API endpoints
4. Add comprehensive tests
5. Update documentation
'''
        
        with open(service_readme, 'w') as f:
            f.write(readme_content)
        
        # Update main project documentation
        self._update_main_documentation(service_name, template_vars)
    
    def _update_main_documentation(self, service_name: str, template_vars: Dict[str, Any]):
        """Update main project documentation."""
        services_doc = self.project_root / "docs" / "services.md"
        
        # Create services documentation if it doesn't exist
        if not services_doc.exists():
            services_doc.parent.mkdir(exist_ok=True)
            with open(services_doc, 'w') as f:
                f.write("# ActiveLog Services\\n\\n")
        
        # Add service to documentation
        service_entry = f'''
## {template_vars['SERVICE_NAME_TITLE']}

**Port**: {template_vars['SERVICE_PORT']}  
**Path**: `services/{service_name}/`  
**Description**: {template_vars['SERVICE_DESCRIPTION']}

- Health Check: `GET /health`
- API Docs: `GET /docs`
- Generated: {template_vars['GENERATED_DATE']}

'''
        
        with open(services_doc, 'a') as f:
            f.write(service_entry)
    
    def _print_next_steps(self, service_name: str, port: int):
        """Print next steps after service generation."""
        print(f"\\n📋 Next Steps for {service_name}:")
        print(f"1. Navigate to the service directory:")
        print(f"   cd services/{service_name}")
        
        print(f"\\n2. Review and customize the generated code:")
        print(f"   - main.py (FastAPI application)")
        print(f"   - models.py (Data models)")
        print(f"   - database.py (Database configuration)")
        print(f"   - requirements.txt (Dependencies)")
        
        print(f"\\n3. Install dependencies:")
        print(f"   pip install -r services/{service_name}/requirements.txt")
        
        print(f"\\n4. Start the service:")
        print(f"   python dev-tools/cli/activelog_cli.py services start {service_name}")
        
        print(f"\\n5. Test the service:")
        print(f"   curl http://localhost:{port}/health")
        print(f"   curl http://localhost:{port}/docs")
        
        print(f"\\n6. Run tests:")
        print(f"   python -m pytest tests/services/{service_name}/")
        
        print(f"\\n🔗 Service URLs:")
        print(f"   Health: http://localhost:{port}/health")
        print(f"   API Docs: http://localhost:{port}/docs")
        print(f"   ReDoc: http://localhost:{port}/redoc")


def create_default_templates():
    """Create default service templates."""
    templates_dir = Path(__file__).parent / "service_templates"
    templates_dir.mkdir(exist_ok=True)
    
    # FastAPI template
    create_fastapi_template(templates_dir / "fastapi")
    
    # Flask template
    create_flask_template(templates_dir / "flask")
    
    # gRPC template
    create_grpc_template(templates_dir / "grpc")
    
    # Celery worker template
    create_celery_template(templates_dir / "celery_worker")


def create_fastapi_template(template_dir: Path):
    """Create FastAPI service template."""
    template_dir.mkdir(exist_ok=True)
    
    # Main application file
    main_py = '''"""
{{SERVICE_NAME_TITLE}} Service
{{SERVICE_DESCRIPTION}}

Generated on {{GENERATED_DATE}} by {{AUTHOR}}
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
from datetime import datetime
from typing import Dict, Any

from .models import HealthResponse, ServiceInfoResponse
from .database import get_database, init_database
from .config import settings

# Setup logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="{{SERVICE_NAME_TITLE}}",
    description="{{SERVICE_DESCRIPTION}}",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8088"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup."""
    logger.info("Starting {{SERVICE_NAME_TITLE}} service...")
    await init_database()
    logger.info("{{SERVICE_NAME_TITLE}} service started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down {{SERVICE_NAME_TITLE}} service...")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service="{{SERVICE_NAME_SNAKE}}",
        timestamp=datetime.utcnow(),
        version="1.0.0"
    )


@app.get("/info", response_model=ServiceInfoResponse)
async def service_info():
    """Service information endpoint."""
    return ServiceInfoResponse(
        service_name="{{SERVICE_NAME_SNAKE}}",
        version="1.0.0",
        description="{{SERVICE_DESCRIPTION}}",
        port={{SERVICE_PORT}},
        environment=settings.environment,
        generated_date="{{GENERATED_DATE}}"
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "{{SERVICE_NAME_TITLE}} API", "docs": "/docs"}


# Add your API routes here
@app.get("/api/v1/{{SERVICE_NAME_KEBAB}}")
async def list_items(db = Depends(get_database)):
    """List items endpoint."""
    # Implement your business logic here
    return {"items": [], "total": 0}


@app.post("/api/v1/{{SERVICE_NAME_KEBAB}}")
async def create_item(db = Depends(get_database)):
    """Create item endpoint."""
    # Implement your business logic here
    return {"message": "Item created"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port={{SERVICE_PORT}})
'''
    
    with open(template_dir / "main.py", 'w') as f:
        f.write(main_py)
    
    # Models file
    models_py = '''"""
Pydantic models for {{SERVICE_NAME_TITLE}} service.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Any


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    service: str
    timestamp: datetime
    version: str


class ServiceInfoResponse(BaseModel):
    """Service information response model."""
    service_name: str
    version: str
    description: str
    port: int
    environment: str
    generated_date: str


class BaseItem(BaseModel):
    """Base item model."""
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CreateItemRequest(BaseModel):
    """Create item request model."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)


class ItemResponse(BaseItem):
    """Item response model."""
    id: str
    created_at: datetime
    updated_at: datetime


class ListItemsResponse(BaseModel):
    """List items response model."""
    items: List[ItemResponse]
    total: int
    page: int = 1
    per_page: int = 50
'''
    
    with open(template_dir / "models.py", 'w') as f:
        f.write(models_py)
    
    # Database configuration
    database_py = '''"""
Database configuration for {{SERVICE_NAME_TITLE}} service.
"""

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, String, DateTime, Text
import uuid
from datetime import datetime

from .config import settings

# Database engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
    pool_pre_ping=True
)

# Session factory
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Base model
Base = declarative_base()


class BaseModel(Base):
    """Base model with common fields."""
    __abstract__ = True
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Item(BaseModel):
    """Example item model."""
    __tablename__ = "{{SERVICE_NAME_SNAKE}}_items"
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)


async def init_database():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_database() -> AsyncSession:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
'''
    
    with open(template_dir / "database.py", 'w') as f:
        f.write(database_py)
    
    # Configuration
    config_py = '''"""
Configuration for {{SERVICE_NAME_TITLE}} service.
"""

import os
from pydantic import BaseSettings


class Settings(BaseSettings):
    """Service settings."""
    
    # Service configuration
    service_name: str = "{{SERVICE_NAME_SNAKE}}"
    port: int = {{SERVICE_PORT}}
    environment: str = "development"
    log_level: str = "INFO"
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./{{SERVICE_NAME_SNAKE}}.db"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Security
    secret_key: str = "your-secret-key-here"
    
    class Config:
        env_file = ".env"
        env_prefix = "{{SERVICE_NAME_UPPER}}_"


settings = Settings()
'''
    
    with open(template_dir / "config.py", 'w') as f:
        f.write(config_py)
    
    # Requirements
    requirements_txt = '''fastapi>=0.104.1
uvicorn[standard]>=0.24.0
pydantic>=2.5.0
sqlalchemy[asyncio]>=2.0.23
aiosqlite>=0.19.0
redis>=5.0.1
python-multipart>=0.0.6
python-dotenv>=1.0.0
'''
    
    with open(template_dir / "requirements.txt", 'w') as f:
        f.write(requirements_txt)
    
    # Dockerfile
    dockerfile = '''FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

# Expose port
EXPOSE {{SERVICE_PORT}}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:{{SERVICE_PORT}}/health || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{{SERVICE_PORT}}"]
'''
    
    with open(template_dir / "Dockerfile", 'w') as f:
        f.write(dockerfile)
    
    # __init__.py
    with open(template_dir / "__init__.py", 'w') as f:
        f.write('"""{{SERVICE_NAME_TITLE}} Service Package"""\\n')


def create_flask_template(template_dir: Path):
    """Create Flask service template."""
    template_dir.mkdir(exist_ok=True)
    
    # Main application
    app_py = '''"""
{{SERVICE_NAME_TITLE}} Flask Service
{{SERVICE_DESCRIPTION}}
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
import os
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
CORS(app)

# Configuration
app.config['SERVICE_NAME'] = '{{SERVICE_NAME_SNAKE}}'
app.config['SERVICE_PORT'] = {{SERVICE_PORT}}
app.config['VERSION'] = '1.0.0'


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': '{{SERVICE_NAME_SNAKE}}',
        'timestamp': datetime.utcnow().isoformat(),
        'version': app.config['VERSION']
    })


@app.route('/info', methods=['GET'])
def service_info():
    """Service information endpoint."""
    return jsonify({
        'service_name': '{{SERVICE_NAME_SNAKE}}',
        'version': app.config['VERSION'],
        'description': '{{SERVICE_DESCRIPTION}}',
        'port': {{SERVICE_PORT}},
        'generated_date': '{{GENERATED_DATE}}'
    })


@app.route('/', methods=['GET'])
def root():
    """Root endpoint."""
    return jsonify({
        'message': '{{SERVICE_NAME_TITLE}} API',
        'version': app.config['VERSION']
    })


@app.route('/api/v1/{{SERVICE_NAME_KEBAB}}', methods=['GET'])
def list_items():
    """List items endpoint."""
    return jsonify({
        'items': [],
        'total': 0
    })


@app.route('/api/v1/{{SERVICE_NAME_KEBAB}}', methods=['POST'])
def create_item():
    """Create item endpoint."""
    data = request.get_json()
    # Implement your business logic here
    return jsonify({
        'message': 'Item created',
        'data': data
    }), 201


if __name__ == '__main__':
    app.run(host='0.0.0.0', port={{SERVICE_PORT}}, debug=True)
'''
    
    with open(template_dir / "app.py", 'w') as f:
        f.write(app_py)
    
    # Requirements for Flask
    requirements_txt = '''Flask>=3.0.0
Flask-CORS>=4.0.0
python-dotenv>=1.0.0
gunicorn>=21.2.0
'''
    
    with open(template_dir / "requirements.txt", 'w') as f:
        f.write(requirements_txt)


def create_grpc_template(template_dir: Path):
    """Create gRPC service template."""
    template_dir.mkdir(exist_ok=True)
    
    # gRPC server
    server_py = '''"""
{{SERVICE_NAME_TITLE}} gRPC Service
{{SERVICE_DESCRIPTION}}
"""

import grpc
from concurrent import futures
import logging
import time
from datetime import datetime

# Import generated protobuf classes (you'll need to generate these)
# import {{SERVICE_NAME_SNAKE}}_pb2
# import {{SERVICE_NAME_SNAKE}}_pb2_grpc

logger = logging.getLogger(__name__)


class {{SERVICE_NAME_PASCAL}}Service:
    """{{SERVICE_NAME_TITLE}} gRPC service implementation."""
    
    def GetHealth(self, request, context):
        """Health check method."""
        # return {{SERVICE_NAME_SNAKE}}_pb2.HealthResponse(
        #     status="healthy",
        #     service="{{SERVICE_NAME_SNAKE}}",
        #     timestamp=datetime.utcnow().isoformat()
        # )
        pass
    
    def GetServiceInfo(self, request, context):
        """Service info method."""
        # return {{SERVICE_NAME_SNAKE}}_pb2.ServiceInfoResponse(
        #     service_name="{{SERVICE_NAME_SNAKE}}",
        #     version="1.0.0",
        #     description="{{SERVICE_DESCRIPTION}}"
        # )
        pass


def serve():
    """Start the gRPC server."""
    port = {{SERVICE_PORT}}
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    
    # Add service to server
    # {{SERVICE_NAME_SNAKE}}_pb2_grpc.add_{{SERVICE_NAME_PASCAL}}ServiceServicer_to_server(
    #     {{SERVICE_NAME_PASCAL}}Service(), server
    # )
    
    listen_addr = f'[::]:{port}'
    server.add_insecure_port(listen_addr)
    
    logger.info(f"Starting gRPC server on {listen_addr}")
    server.start()
    
    try:
        while True:
            time.sleep(86400)  # One day
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    serve()
'''
    
    with open(template_dir / "server.py", 'w') as f:
        f.write(server_py)
    
    # Protocol buffer definition
    proto_file = '''syntax = "proto3";

package {{SERVICE_NAME_SNAKE}};

// Health check service
service HealthService {
    rpc GetHealth(HealthRequest) returns (HealthResponse);
}

// Main service
service {{SERVICE_NAME_PASCAL}}Service {
    rpc GetServiceInfo(ServiceInfoRequest) returns (ServiceInfoResponse);
    rpc ListItems(ListItemsRequest) returns (ListItemsResponse);
    rpc CreateItem(CreateItemRequest) returns (CreateItemResponse);
}

// Messages
message HealthRequest {}

message HealthResponse {
    string status = 1;
    string service = 2;
    string timestamp = 3;
}

message ServiceInfoRequest {}

message ServiceInfoResponse {
    string service_name = 1;
    string version = 2;
    string description = 3;
}

message ListItemsRequest {
    int32 page = 1;
    int32 per_page = 2;
}

message ListItemsResponse {
    repeated Item items = 1;
    int32 total = 2;
}

message CreateItemRequest {
    string name = 1;
    string description = 2;
}

message CreateItemResponse {
    Item item = 1;
}

message Item {
    string id = 1;
    string name = 2;
    string description = 3;
    string created_at = 4;
    string updated_at = 5;
}
'''
    
    with open(template_dir / "{{SERVICE_NAME_SNAKE}}.proto", 'w') as f:
        f.write(proto_file)
    
    # gRPC requirements
    requirements_txt = '''grpcio>=1.59.0
grpcio-tools>=1.59.0
protobuf>=4.24.0
'''
    
    with open(template_dir / "requirements.txt", 'w') as f:
        f.write(requirements_txt)


def create_celery_template(template_dir: Path):
    """Create Celery worker template."""
    template_dir.mkdir(exist_ok=True)
    
    # Celery worker
    worker_py = '''"""
{{SERVICE_NAME_TITLE}} Celery Worker
{{SERVICE_DESCRIPTION}}
"""

from celery import Celery
import logging
import os
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Celery configuration
celery_app = Celery(
    '{{SERVICE_NAME_SNAKE}}',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
    include=['{{SERVICE_NAME_SNAKE}}.tasks']
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_routes={
        '{{SERVICE_NAME_SNAKE}}.tasks.*': {'queue': '{{SERVICE_NAME_SNAKE}}'},
    }
)


@celery_app.task(bind=True)
def health_check(self):
    """Health check task."""
    return {
        'status': 'healthy',
        'worker': '{{SERVICE_NAME_SNAKE}}',
        'timestamp': datetime.utcnow().isoformat(),
        'task_id': self.request.id
    }


@celery_app.task(bind=True)
def process_item(self, item_data: Dict[str, Any]):
    """Process item task."""
    logger.info(f"Processing item: {item_data}")
    
    try:
        # Implement your processing logic here
        result = {
            'status': 'completed',
            'item_id': item_data.get('id'),
            'processed_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Item processed successfully: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing item: {e}")
        self.retry(countdown=60, max_retries=3)


@celery_app.task(bind=True)
def batch_process_items(self, items_data: list):
    """Batch process multiple items."""
    logger.info(f"Processing batch of {len(items_data)} items")
    
    results = []
    for item_data in items_data:
        try:
            # Process each item
            result = process_item.delay(item_data)
            results.append(result.id)
        except Exception as e:
            logger.error(f"Error queuing item for processing: {e}")
            results.append(None)
    
    return {
        'status': 'batch_queued',
        'total_items': len(items_data),
        'task_ids': results,
        'queued_at': datetime.utcnow().isoformat()
    }


if __name__ == '__main__':
    celery_app.start()
'''
    
    with open(template_dir / "worker.py", 'w') as f:
        f.write(worker_py)
    
    # Celery requirements
    requirements_txt = '''celery[redis]>=5.3.0
redis>=5.0.1
'''
    
    with open(template_dir / "requirements.txt", 'w') as f:
        f.write(requirements_txt)


def main():
    """Main function for service generation."""
    parser = argparse.ArgumentParser(description="Generate a new ActiveLog service")
    parser.add_argument('--name', help='Service name')
    parser.add_argument('--template', default='fastapi', help='Service template')
    parser.add_argument('--port', type=int, help='Service port')
    parser.add_argument('--description', help='Service description')
    parser.add_argument('--create-templates', action='store_true', help='Create default templates')
    
    args = parser.parse_args()
    
    project_root = Path(__file__).parent.parent.parent
    
    if args.create_templates:
        print("📋 Creating default service templates...")
        create_default_templates()
        print("✅ Default templates created!")
        return
    
    if not args.name:
        print("❌ Service name is required when not creating templates")
        parser.print_help()
        sys.exit(1)
    
    generator = ServiceGenerator(project_root)
    
    try:
        generator.generate_service(
            service_name=args.name,
            template_name=args.template,
            port=args.port,
            description=args.description
        )
    except Exception as e:
        print(f"❌ Service generation failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()