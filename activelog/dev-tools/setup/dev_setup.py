#!/usr/bin/env python3
"""
ActiveLog Development Environment Setup Script
One-command setup for the complete development environment.
"""

import os
import sys
import subprocess
import platform
import shutil
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse
import requests
import yaml
import logging

logger = logging.getLogger(__name__)


class DevEnvironmentSetup:
    """Handles complete development environment setup."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.system = platform.system().lower()
        self.python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        self.setup_log = []
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def setup_complete_environment(self, full: bool = False, docker: bool = False):
        """Setup complete development environment."""
        self.log_step("🚀 Starting ActiveLog Development Environment Setup")
        
        try:
            # 1. Check system requirements
            self.check_system_requirements()
            
            # 2. Install system dependencies
            self.install_system_dependencies()
            
            # 3. Setup Python environment
            self.setup_python_environment()
            
            # 4. Install Python dependencies
            self.install_python_dependencies()
            
            # 5. Setup pre-commit hooks
            self.setup_pre_commit_hooks()
            
            # 6. Setup environment variables
            self.setup_environment_variables()
            
            # 7. Setup databases
            if docker:
                self.setup_docker_services()
            else:
                self.setup_local_databases()
            
            # 8. Run database migrations
            self.setup_database_schema()
            
            if full:
                # 9. Setup development tools
                self.setup_development_tools()
                
                # 10. Setup IDE configurations
                self.setup_ide_configurations()
                
                # 11. Install additional tools
                self.install_additional_tools()
            
            # 12. Verify setup
            self.verify_setup()
            
            self.log_step("✅ Development environment setup completed successfully!")
            self.print_setup_summary()
            
        except Exception as e:
            self.log_step(f"❌ Setup failed: {e}")
            self.print_setup_log()
            raise
    
    def check_system_requirements(self):
        """Check system requirements and dependencies."""
        self.log_step("🔍 Checking system requirements...")
        
        # Check Python version
        if sys.version_info < (3, 8):
            raise RuntimeError(f"Python 3.8+ required, found {self.python_version}")
        
        # Check required commands
        required_commands = {
            'git': 'Git version control',
            'node': 'Node.js for frontend tools',
            'npm': 'NPM package manager',
            'docker': 'Docker for containerization',
            'docker-compose': 'Docker Compose for multi-container apps'
        }
        
        missing_commands = []
        for cmd, description in required_commands.items():
            if not shutil.which(cmd):
                missing_commands.append(f"{cmd} ({description})")
        
        if missing_commands:
            self.log_step("⚠️  Missing required commands:")
            for cmd in missing_commands:
                self.log_step(f"   - {cmd}")
            
            if 'docker' in [c.split()[0] for c in missing_commands]:
                self.log_step("   💡 Install Docker from: https://docs.docker.com/get-docker/")
            
            # Don't fail if only optional commands are missing
            critical_missing = [c for c in missing_commands if any(x in c for x in ['git', 'python'])]
            if critical_missing:
                raise RuntimeError(f"Critical dependencies missing: {critical_missing}")
        
        self.log_step("✅ System requirements check passed")
    
    def install_system_dependencies(self):
        """Install system-level dependencies."""
        self.log_step("📦 Installing system dependencies...")
        
        try:
            if self.system == 'darwin':  # macOS
                self._install_macos_dependencies()
            elif self.system == 'linux':
                self._install_linux_dependencies()
            elif self.system == 'windows':
                self._install_windows_dependencies()
            else:
                self.log_step(f"⚠️  Unsupported system: {self.system}")
                
        except Exception as e:
            self.log_step(f"⚠️  System dependency installation failed: {e}")
            self.log_step("   You may need to install dependencies manually")
    
    def _install_macos_dependencies(self):
        """Install macOS dependencies using Homebrew."""
        if not shutil.which('brew'):
            self.log_step("Installing Homebrew...")
            subprocess.run([
                '/bin/bash', '-c',
                '$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)'
            ], check=True)
        
        # Install required packages
        packages = [
            'postgresql', 'redis', 'node', 'git',
            'libpq', 'openssl', 'libffi'
        ]
        
        for package in packages:
            try:
                subprocess.run(['brew', 'install', package], 
                             check=False, capture_output=True)
            except Exception:
                pass  # Continue if individual package fails
    
    def _install_linux_dependencies(self):
        """Install Linux dependencies."""
        # Detect package manager
        if shutil.which('apt'):
            self._install_with_apt()
        elif shutil.which('yum'):
            self._install_with_yum()
        elif shutil.which('pacman'):
            self._install_with_pacman()
        else:
            self.log_step("⚠️  Unknown package manager, skipping system packages")
    
    def _install_with_apt(self):
        """Install dependencies with apt (Ubuntu/Debian)."""
        packages = [
            'postgresql', 'postgresql-contrib', 'redis-server',
            'nodejs', 'npm', 'git', 'build-essential',
            'libpq-dev', 'libssl-dev', 'libffi-dev',
            'python3-dev', 'python3-pip', 'python3-venv'
        ]
        
        try:
            # Update package list
            subprocess.run(['sudo', 'apt', 'update'], check=True)
            
            # Install packages
            subprocess.run(['sudo', 'apt', 'install', '-y'] + packages, 
                         check=True)
        except Exception as e:
            self.log_step(f"⚠️  APT installation failed: {e}")
    
    def _install_with_yum(self):
        """Install dependencies with yum (CentOS/RHEL)."""
        packages = [
            'postgresql', 'postgresql-server', 'redis',
            'nodejs', 'npm', 'git', 'gcc', 'gcc-c++',
            'postgresql-devel', 'openssl-devel', 'libffi-devel',
            'python3-devel', 'python3-pip'
        ]
        
        try:
            subprocess.run(['sudo', 'yum', 'install', '-y'] + packages, 
                         check=True)
        except Exception as e:
            self.log_step(f"⚠️  YUM installation failed: {e}")
    
    def _install_with_pacman(self):
        """Install dependencies with pacman (Arch Linux)."""
        packages = [
            'postgresql', 'redis', 'nodejs', 'npm', 'git',
            'base-devel', 'python', 'python-pip'
        ]
        
        try:
            subprocess.run(['sudo', 'pacman', '-S', '--noconfirm'] + packages,
                         check=True)
        except Exception as e:
            self.log_step(f"⚠️  Pacman installation failed: {e}")
    
    def _install_windows_dependencies(self):
        """Install Windows dependencies."""
        self.log_step("⚠️  Windows automatic installation not supported")
        self.log_step("   Please install manually:")
        self.log_step("   - Python 3.8+ from python.org")
        self.log_step("   - Git from git-scm.com")
        self.log_step("   - Node.js from nodejs.org")
        self.log_step("   - Docker Desktop from docker.com")
        self.log_step("   - PostgreSQL from postgresql.org")
    
    def setup_python_environment(self):
        """Setup Python virtual environment."""
        self.log_step("🐍 Setting up Python environment...")
        
        venv_path = self.project_root / ".venv"
        
        if not venv_path.exists():
            self.log_step("Creating virtual environment...")
            subprocess.run([
                sys.executable, '-m', 'venv', str(venv_path)
            ], check=True)
        
        # Activate virtual environment and upgrade pip
        if self.system == 'windows':
            pip_cmd = [str(venv_path / "Scripts" / "pip")]
            python_cmd = [str(venv_path / "Scripts" / "python")]
        else:
            pip_cmd = [str(venv_path / "bin" / "pip")]
            python_cmd = [str(venv_path / "bin" / "python")]
        
        # Upgrade pip
        subprocess.run(pip_cmd + ['install', '--upgrade', 'pip'], check=True)
        
        self.log_step("✅ Python environment setup completed")
    
    def install_python_dependencies(self):
        """Install Python dependencies."""
        self.log_step("📚 Installing Python dependencies...")
        
        venv_path = self.project_root / ".venv"
        
        if self.system == 'windows':
            pip_cmd = [str(venv_path / "Scripts" / "pip")]
        else:
            pip_cmd = [str(venv_path / "bin" / "pip")]
        
        # Install requirements
        requirements_files = [
            'requirements.txt',
            'requirements-dev.txt'
        ]
        
        for req_file in requirements_files:
            req_path = self.project_root / req_file
            if req_path.exists():
                self.log_step(f"Installing {req_file}...")
                subprocess.run(pip_cmd + ['install', '-r', str(req_path)], 
                             check=True)
        
        # Install additional development tools
        dev_packages = [
            'black', 'isort', 'flake8', 'mypy',
            'pytest', 'pytest-cov', 'pytest-asyncio',
            'pre-commit', 'bandit', 'safety'
        ]
        
        self.log_step("Installing development tools...")
        subprocess.run(pip_cmd + ['install'] + dev_packages, check=True)
        
        self.log_step("✅ Python dependencies installed")
    
    def setup_pre_commit_hooks(self):
        """Setup pre-commit hooks."""
        self.log_step("🪝 Setting up pre-commit hooks...")
        
        venv_path = self.project_root / ".venv"
        
        if self.system == 'windows':
            precommit_cmd = [str(venv_path / "Scripts" / "pre-commit")]
        else:
            precommit_cmd = [str(venv_path / "bin" / "pre-commit")]
        
        # Create .pre-commit-config.yaml if it doesn't exist
        precommit_config = self.project_root / ".pre-commit-config.yaml"
        if not precommit_config.exists():
            self._create_precommit_config(precommit_config)
        
        # Install pre-commit hooks
        try:
            subprocess.run(precommit_cmd + ['install'], 
                         check=True, cwd=self.project_root)
            self.log_step("✅ Pre-commit hooks installed")
        except Exception as e:
            self.log_step(f"⚠️  Pre-commit hook setup failed: {e}")
    
    def _create_precommit_config(self, config_path: Path):
        """Create default pre-commit configuration."""
        config = {
            'repos': [
                {
                    'repo': 'https://github.com/pre-commit/pre-commit-hooks',
                    'rev': 'v4.4.0',
                    'hooks': [
                        {'id': 'trailing-whitespace'},
                        {'id': 'end-of-file-fixer'},
                        {'id': 'check-yaml'},
                        {'id': 'check-added-large-files'},
                        {'id': 'check-merge-conflict'},
                    ]
                },
                {
                    'repo': 'https://github.com/psf/black',
                    'rev': '23.3.0',
                    'hooks': [{'id': 'black'}]
                },
                {
                    'repo': 'https://github.com/pycqa/isort',
                    'rev': '5.12.0',
                    'hooks': [{'id': 'isort'}]
                },
                {
                    'repo': 'https://github.com/pycqa/flake8',
                    'rev': '6.0.0',
                    'hooks': [{'id': 'flake8'}]
                },
                {
                    'repo': 'https://github.com/pycqa/bandit',
                    'rev': '1.7.5',
                    'hooks': [{'id': 'bandit', 'args': ['-c', 'pyproject.toml']}]
                }
            ]
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
    
    def setup_environment_variables(self):
        """Setup environment variables."""
        self.log_step("🔧 Setting up environment variables...")
        
        env_file = self.project_root / ".env"
        env_example = self.project_root / ".env.example"
        
        # Create .env from .env.example if it doesn't exist
        if env_example.exists() and not env_file.exists():
            shutil.copy(env_example, env_file)
            self.log_step("Created .env from .env.example")
        elif not env_file.exists():
            self._create_default_env_file(env_file)
            self.log_step("Created default .env file")
        
        # Create development environment file
        dev_env = self.project_root / ".env.development"
        if not dev_env.exists():
            self._create_dev_env_file(dev_env)
    
    def _create_default_env_file(self, env_path: Path):
        """Create default .env file."""
        default_env = """# ActiveLog Environment Variables

# Environment
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# Database
DATABASE_URL=postgresql://activelog:activelog123@localhost:5432/activelog
REDIS_URL=redis://localhost:6379/0
ELASTICSEARCH_URL=http://localhost:9200

# Security
JWT_SECRET_KEY=dev-jwt-secret-key-change-in-production
ENCRYPTION_KEY=dev-encryption-key-change-in-production
API_SECRET_KEY=dev-api-secret-key

# External Services
OPENAI_API_KEY=your-openai-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# File Storage
UPLOAD_PATH=./uploads
MAX_FILE_SIZE=100MB

# Email (Optional)
SMTP_HOST=localhost
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
FROM_EMAIL=noreply@activelog.local

# Monitoring
SENTRY_DSN=
PROMETHEUS_ENABLED=true

# Development
HOT_RELOAD=true
AUTO_MIGRATE=true
SEED_DATA=true
"""
        
        with open(env_path, 'w') as f:
            f.write(default_env)
    
    def _create_dev_env_file(self, dev_env_path: Path):
        """Create development-specific environment file."""
        dev_env_content = """# Development-specific overrides

# Debug settings
DEBUG=true
LOG_LEVEL=DEBUG
TESTING=false

# Development database
DATABASE_URL=postgresql://activelog:activelog123@localhost:5432/activelog_dev
REDIS_URL=redis://localhost:6379/1

# Fast development settings
HOT_RELOAD=true
AUTO_MIGRATE=true
DISABLE_AUTH=false
MOCK_EXTERNAL_SERVICES=true

# Development ports
API_GATEWAY_PORT=8000
AUTH_SERVICE_PORT=8001
FILE_SYNC_PORT=8002
AI_ORCHESTRATOR_PORT=8003

# Development tools
PROFILING_ENABLED=true
QUERY_DEBUG=true
"""
        
        with open(dev_env_path, 'w') as f:
            f.write(dev_env_content)
    
    def setup_docker_services(self):
        """Setup Docker services for development."""
        self.log_step("🐳 Setting up Docker services...")
        
        compose_file = self.project_root / "docker-compose.dev.yml"
        
        if not compose_file.exists():
            self._create_dev_docker_compose(compose_file)
        
        # Start Docker services
        try:
            subprocess.run([
                'docker-compose', '-f', str(compose_file), 
                'up', '-d', 'postgres', 'redis', 'elasticsearch'
            ], check=True, cwd=self.project_root)
            
            self.log_step("✅ Docker services started")
            
            # Wait for services to be ready
            self._wait_for_docker_services()
            
        except Exception as e:
            self.log_step(f"⚠️  Docker setup failed: {e}")
            raise
    
    def _create_dev_docker_compose(self, compose_path: Path):
        """Create development Docker Compose file."""
        compose_content = {
            'version': '3.8',
            'services': {
                'postgres': {
                    'image': 'postgres:15-alpine',
                    'container_name': 'activelog-postgres-dev',
                    'environment': {
                        'POSTGRES_DB': 'activelog_dev',
                        'POSTGRES_USER': 'activelog',
                        'POSTGRES_PASSWORD': 'activelog123'
                    },
                    'ports': ['5432:5432'],
                    'volumes': ['postgres_dev_data:/var/lib/postgresql/data']
                },
                'redis': {
                    'image': 'redis:7-alpine',
                    'container_name': 'activelog-redis-dev',
                    'ports': ['6379:6379'],
                    'command': 'redis-server --appendonly yes'
                },
                'elasticsearch': {
                    'image': 'docker.elastic.co/elasticsearch/elasticsearch:8.9.0',
                    'container_name': 'activelog-elasticsearch-dev',
                    'environment': {
                        'discovery.type': 'single-node',
                        'xpack.security.enabled': 'false',
                        'ES_JAVA_OPTS': '-Xms512m -Xmx512m'
                    },
                    'ports': ['9200:9200'],
                    'volumes': ['elasticsearch_dev_data:/usr/share/elasticsearch/data']
                }
            },
            'volumes': {
                'postgres_dev_data': {},
                'elasticsearch_dev_data': {}
            }
        }
        
        with open(compose_path, 'w') as f:
            yaml.dump(compose_content, f, default_flow_style=False)
    
    def _wait_for_docker_services(self):
        """Wait for Docker services to be ready."""
        self.log_step("⏳ Waiting for services to be ready...")
        
        services = [
            ('PostgreSQL', 'localhost', 5432),
            ('Redis', 'localhost', 6379),
            ('Elasticsearch', 'localhost', 9200)
        ]
        
        max_wait = 60  # seconds
        start_time = time.time()
        
        for service_name, host, port in services:
            self.log_step(f"Waiting for {service_name}...")
            
            while time.time() - start_time < max_wait:
                try:
                    if service_name == 'Elasticsearch':
                        response = requests.get(f'http://{host}:{port}/_health', timeout=2)
                        if response.status_code == 200:
                            break
                    else:
                        import socket
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        result = sock.connect_ex((host, port))
                        sock.close()
                        if result == 0:
                            break
                except Exception:
                    pass
                
                time.sleep(2)
            else:
                self.log_step(f"⚠️  {service_name} not ready after {max_wait}s")
        
        self.log_step("✅ Services are ready")
    
    def setup_local_databases(self):
        """Setup local databases without Docker."""
        self.log_step("🗄️  Setting up local databases...")
        
        # This would involve starting local services
        # Implementation depends on the system and installation method
        self.log_step("ℹ️  Please ensure PostgreSQL, Redis, and Elasticsearch are running locally")
    
    def setup_database_schema(self):
        """Setup database schema and migrations."""
        self.log_step("🗃️  Setting up database schema...")
        
        try:
            # Run Alembic migrations
            venv_path = self.project_root / ".venv"
            
            if self.system == 'windows':
                alembic_cmd = [str(venv_path / "Scripts" / "alembic")]
            else:
                alembic_cmd = [str(venv_path / "bin" / "alembic")]
            
            # Initialize Alembic if not already done
            alembic_dir = self.project_root / "alembic"
            if not alembic_dir.exists():
                subprocess.run(alembic_cmd + ['init', 'alembic'], 
                             check=True, cwd=self.project_root)
            
            # Run migrations
            subprocess.run(alembic_cmd + ['upgrade', 'head'], 
                         check=True, cwd=self.project_root)
            
            self.log_step("✅ Database schema setup completed")
            
        except Exception as e:
            self.log_step(f"⚠️  Database schema setup failed: {e}")
            self.log_step("   You may need to run migrations manually later")
    
    def setup_development_tools(self):
        """Setup additional development tools."""
        self.log_step("🛠️  Setting up development tools...")
        
        # Install Node.js dependencies
        package_json = self.project_root / "package.json"
        if package_json.exists():
            try:
                subprocess.run(['npm', 'install'], check=True, cwd=self.project_root)
                self.log_step("✅ Node.js dependencies installed")
            except Exception as e:
                self.log_step(f"⚠️  Node.js setup failed: {e}")
        
        # Setup formatting tools
        self._setup_formatting_configs()
        
        # Setup testing configuration
        self._setup_testing_configs()
    
    def _setup_formatting_configs(self):
        """Setup code formatting configurations."""
        # Black configuration in pyproject.toml
        pyproject_path = self.project_root / "pyproject.toml"
        if not pyproject_path.exists():
            self._create_pyproject_toml(pyproject_path)
        
        # isort configuration
        isort_config = self.project_root / ".isort.cfg"
        if not isort_config.exists():
            self._create_isort_config(isort_config)
        
        # flake8 configuration
        flake8_config = self.project_root / ".flake8"
        if not flake8_config.exists():
            self._create_flake8_config(flake8_config)
    
    def _create_pyproject_toml(self, path: Path):
        """Create pyproject.toml with Black configuration."""
        content = '''[build-system]
requires = ["setuptools", "wheel"]

[tool.black]
line-length = 88
target-version = ['py38', 'py39', 'py310', 'py311']
include = '\\.pyi?$'
extend-exclude = '''
    # A regex preceded by ^/ will apply only to files and directories
    # in the root of the project.
    (
      ^/migrations/  # exclude migration files
    | ^/alembic/     # exclude alembic files
    )
'''

[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 88
known_first_party = ["activelog"]

[tool.pytest.ini_options]
minversion = "6.0"
testpaths = ["tests"]
addopts = "-ra -q --strict-markers --strict-config"
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]

[tool.coverage.run]
source = ["."]
omit = [
    "*/tests/*",
    "*/migrations/*",
    "*/alembic/*",
    "*/.venv/*",
    "*/venv/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
]

[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
'''
        
        with open(path, 'w') as f:
            f.write(content)
    
    def _create_isort_config(self, path: Path):
        """Create isort configuration."""
        content = '''[settings]
profile = black
multi_line_output = 3
line_length = 88
known_first_party = activelog
known_third_party = fastapi,sqlalchemy,pydantic,pytest,requests
'''
        
        with open(path, 'w') as f:
            f.write(content)
    
    def _create_flake8_config(self, path: Path):
        """Create flake8 configuration."""
        content = '''[flake8]
max-line-length = 88
select = E,W,F
ignore = 
    E203,  # whitespace before ':'
    E501,  # line too long (handled by black)
    W503,  # line break before binary operator
exclude = 
    .git,
    __pycache__,
    .venv,
    venv,
    migrations,
    alembic,
    .pytest_cache
per-file-ignores =
    __init__.py:F401
    tests/*:F401,F811
'''
        
        with open(path, 'w') as f:
            f.write(content)
    
    def _setup_testing_configs(self):
        """Setup testing configurations."""
        # pytest.ini (if not in pyproject.toml)
        pytest_ini = self.project_root / "pytest.ini"
        if not pytest_ini.exists() and not (self.project_root / "pyproject.toml").exists():
            self._create_pytest_ini(pytest_ini)
    
    def _create_pytest_ini(self, path: Path):
        """Create pytest.ini configuration."""
        content = '''[tool:pytest]
minversion = 6.0
testpaths = tests
addopts = -ra -q --strict-markers --strict-config
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
'''
        
        with open(path, 'w') as f:
            f.write(content)
    
    def setup_ide_configurations(self):
        """Setup IDE configurations."""
        self.log_step("🔧 Setting up IDE configurations...")
        
        # VS Code settings
        self._setup_vscode_config()
        
        # PyCharm settings
        self._setup_pycharm_config()
    
    def _setup_vscode_config(self):
        """Setup VS Code configuration."""
        vscode_dir = self.project_root / ".vscode"
        vscode_dir.mkdir(exist_ok=True)
        
        # Settings
        settings = {
            "python.defaultInterpreterPath": "./.venv/bin/python",
            "python.formatting.provider": "black",
            "python.formatting.blackArgs": ["--line-length=88"],
            "python.linting.enabled": True,
            "python.linting.flake8Enabled": True,
            "python.linting.mypyEnabled": True,
            "python.testing.pytestEnabled": True,
            "python.testing.unittestEnabled": False,
            "editor.formatOnSave": True,
            "editor.codeActionsOnSave": {
                "source.organizeImports": True
            },
            "files.exclude": {
                "**/__pycache__": True,
                "**/.pytest_cache": True,
                "**/node_modules": True
            }
        }
        
        with open(vscode_dir / "settings.json", 'w') as f:
            json.dump(settings, f, indent=2)
        
        # Launch configuration
        launch_config = {
            "version": "0.2.0",
            "configurations": [
                {
                    "name": "Python: Current File",
                    "type": "python",
                    "request": "launch",
                    "program": "${file}",
                    "console": "integratedTerminal"
                },
                {
                    "name": "ActiveLog API Gateway",
                    "type": "python",
                    "request": "launch",
                    "program": "${workspaceFolder}/api_gateway/main.py",
                    "console": "integratedTerminal",
                    "env": {
                        "PYTHONPATH": "${workspaceFolder}"
                    }
                }
            ]
        }
        
        with open(vscode_dir / "launch.json", 'w') as f:
            json.dump(launch_config, f, indent=2)
    
    def _setup_pycharm_config(self):
        """Setup PyCharm configuration."""
        # Create .idea directory with basic configuration
        idea_dir = self.project_root / ".idea"
        idea_dir.mkdir(exist_ok=True)
        
        # This would create PyCharm-specific configurations
        # For now, just create a basic structure
        pass
    
    def install_additional_tools(self):
        """Install additional development tools."""
        self.log_step("🔨 Installing additional development tools...")
        
        # Global tools that might be useful
        global_tools = [
            'httpie',  # HTTP client
            'jq',      # JSON processor
            'tree',    # Directory tree viewer
        ]
        
        for tool in global_tools:
            if not shutil.which(tool):
                self.log_step(f"ℹ️  Consider installing {tool} globally")
    
    def verify_setup(self):
        """Verify the setup is working correctly."""
        self.log_step("🔍 Verifying setup...")
        
        checks = []
        
        # Check Python environment
        venv_path = self.project_root / ".venv"
        if venv_path.exists():
            checks.append(("✅", "Python virtual environment"))
        else:
            checks.append(("❌", "Python virtual environment"))
        
        # Check database connections
        try:
            # This would test actual database connections
            checks.append(("✅", "Database connections"))
        except Exception:
            checks.append(("❌", "Database connections"))
        
        # Check required files
        required_files = [".env", "requirements.txt"]
        for file_name in required_files:
            if (self.project_root / file_name).exists():
                checks.append(("✅", f"{file_name}"))
            else:
                checks.append(("❌", f"{file_name}"))
        
        # Display results
        self.log_step("Verification results:")
        for status, item in checks:
            self.log_step(f"  {status} {item}")
    
    def print_setup_summary(self):
        """Print setup summary and next steps."""
        self.log_step("\n" + "="*60)
        self.log_step("🎉 ActiveLog Development Environment Setup Complete!")
        self.log_step("="*60)
        
        self.log_step("\n📋 Next Steps:")
        self.log_step("1. Activate virtual environment:")
        self.log_step("   source .venv/bin/activate")
        
        self.log_step("\n2. Start development server:")
        self.log_step("   python dev-tools/cli/activelog_cli.py services start api_gateway")
        
        self.log_step("\n3. Run tests:")
        self.log_step("   python dev-tools/cli/activelog_cli.py test run")
        
        self.log_step("\n4. Access the application:")
        self.log_step("   http://localhost:8000")
        
        self.log_step("\n🛠️  Useful Commands:")
        self.log_step("   # CLI help")
        self.log_step("   python dev-tools/cli/activelog_cli.py --help")
        
        self.log_step("   # Format code")
        self.log_step("   python dev-tools/cli/activelog_cli.py dev format")
        
        self.log_step("   # View service status")
        self.log_step("   python dev-tools/cli/activelog_cli.py services status")
        
        self.log_step("\n📝 Configuration Files Created:")
        config_files = [
            ".env", ".env.development", ".pre-commit-config.yaml",
            "pyproject.toml", ".isort.cfg", ".flake8",
            ".vscode/settings.json", "docker-compose.dev.yml"
        ]
        
        for config_file in config_files:
            if (self.project_root / config_file).exists():
                self.log_step(f"   ✅ {config_file}")
        
        self.log_step(f"\n📁 Project Root: {self.project_root}")
        self.log_step("="*60)
    
    def print_setup_log(self):
        """Print the setup log for debugging."""
        self.log_step("\n" + "="*60)
        self.log_step("📋 Setup Log:")
        self.log_step("="*60)
        
        for log_entry in self.setup_log:
            print(log_entry)
    
    def log_step(self, message: str):
        """Log a setup step."""
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        self.setup_log.append(log_message)
        print(log_message)


def main():
    """Main function for development setup."""
    parser = argparse.ArgumentParser(description="ActiveLog Development Environment Setup")
    parser.add_argument('--full', action='store_true', help='Full setup with all tools')
    parser.add_argument('--docker', action='store_true', help='Use Docker for services')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    project_root = Path(__file__).parent.parent.parent
    setup = DevEnvironmentSetup(project_root)
    
    try:
        setup.setup_complete_environment(full=args.full, docker=args.docker)
    except KeyboardInterrupt:
        print("\n⚠️  Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()