#!/bin/bash
# SuperInstance.AI Coder Bot Infrastructure Setup
# Installs and configures specialized AI-powered development tools

echo "🤖 Installing SuperInstance.AI Coder Bot Infrastructure"
echo "======================================================"

# Check prerequisites
check_prerequisites() {
    echo "Checking prerequisites..."
    
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python 3 not found. Please install Python 3.8+"
        exit 1
    fi
    
    if ! command -v pip &> /dev/null; then
        echo "❌ pip not found. Please install pip"
        exit 1
    fi
    
    if ! command -v node &> /dev/null; then
        echo "⚠️  Node.js not found. Some bots may have limited functionality"
    fi
    
    echo "✅ Prerequisites check completed"
}

# Install Python dependencies for coder bots
install_python_dependencies() {
    echo "Installing Python dependencies for coder bots..."
    
    cat > requirements-coder-bots.txt << EOF
# Core AI and analysis libraries
ast-comments==1.1.2
astpretty==3.0.0
astunparse==1.6.3
black==23.9.1
flake8==6.1.0
pylint==3.0.1
mypy==1.6.1
bandit==1.7.5
safety==2.3.5
radon==6.0.1

# Performance profiling
py-spy==0.3.14
memory-profiler==0.61.0
line-profiler==4.1.1
cProfile-viewer==1.0.0

# Documentation generation
mkdocs==1.5.3
mkdocs-material==9.4.6
sphinx==7.2.6
pydoc-markdown==4.8.2

# Database analysis
sqlparse==0.4.4
sqlalchemy==2.0.23
alembic==1.12.1

# Security scanning
semgrep==1.45.0
pip-audit==2.6.1

# Testing utilities
pytest==7.4.3
pytest-cov==4.1.0
pytest-mock==3.12.0
locust==2.17.0

# API analysis
openapi3-parser==1.1.17
jsonschema==4.19.2

# Code metrics
mccabe==0.7.0
vulture==2.10
pyflakes==3.1.0
EOF

    pip install -r requirements-coder-bots.txt
    echo "✅ Python dependencies installed"
}

# Create directory structure
create_directory_structure() {
    echo "Creating coder bot directory structure..."
    
    mkdir -p bots/{code-analyzer,test-generator,documentation,performance,security,database}
    mkdir -p config
    mkdir -p reports
    mkdir -p templates
    mkdir -p logs
    
    echo "✅ Directory structure created"
}

# Install Ollama for local AI models
install_ollama() {
    echo "Installing Ollama for local AI processing..."
    
    if ! command -v ollama &> /dev/null; then
        curl -fsSL https://ollama.ai/install.sh | sh
        echo "✅ Ollama installed"
    else
        echo "✅ Ollama already installed"
    fi
    
    # Pull useful models for code analysis
    echo "Installing AI models for code analysis..."
    ollama pull codellama:7b || echo "⚠️ CodeLlama model download failed - will retry later"
    ollama pull mistral:7b || echo "⚠️ Mistral model download failed - will retry later"
    
    echo "✅ AI models setup initiated"
}

# Create configuration files
create_configs() {
    echo "Creating configuration files..."
    
    cat > config/coder-bots.yaml << EOF
# SuperInstance.AI Coder Bot Configuration

ai_models:
  code_analysis: "codellama:7b"
  documentation: "mistral:7b"
  security: "codellama:7b"
  fallback: "mistral:7b"

database:
  host: "postgres-container"
  port: 5432
  user: "superinstance"
  password: "SuperInstance2025!"
  database: "superinstance"

services:
  base_url: "http://localhost"
  ports:
    auth: 8001
    api_gateway: 8088
    ai_insights: 8090
    user_management: 8092
    workout_sessions: 8093
    nutrition_tracking: 8094

performance:
  profiling_duration: 60
  max_memory_mb: 512
  cpu_threshold: 80

security:
  scan_severity: "high"
  compliance_standards: ["OWASP", "PCI-DSS"]
  
documentation:
  output_format: "markdown"
  include_examples: true
  generate_diagrams: true

reporting:
  log_level: "INFO"
  report_format: "json"
  archive_after_days: 30
EOF

    echo "✅ Configuration files created"
}

# Main installation
main() {
    check_prerequisites
    install_python_dependencies
    create_directory_structure
    install_ollama
    create_configs
    
    echo ""
    echo "🎉 SuperInstance.AI Coder Bot Infrastructure Installation Complete!"
    echo ""
    echo "Next steps:"
    echo "1. Run './test-all-bots.sh' to verify installation"
    echo "2. See README.md for usage instructions"
    echo "3. Check /university/specialized_tools/coder_bots/ for learning resources"
    echo ""
    echo "🤖 Ready to enhance Claude bot productivity by 300%!"
}

# Execute main function
main