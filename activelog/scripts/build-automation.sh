#!/bin/bash
# SuperInstance.AI Build Automation Script
# Optimized for ActiveLog fitness domain focus

set -e

echo "🚀 SuperInstance.AI Build Automation"
echo "======================================"

# Configuration
DOMAIN=${DOMAIN:-"activelog"}
BUILD_TYPE=${BUILD_TYPE:-"development"}
SKIP_TESTS=${SKIP_TESTS:-"false"}

# Health check function
health_check() {
    local service=$1
    local port=$2
    local retries=5
    
    echo "Checking health of $service on port $port..."
    for i in $(seq 1 $retries); do
        if curl -s -f http://localhost:$port/health > /dev/null; then
            echo "✅ $service is healthy"
            return 0
        fi
        echo "⏳ Waiting for $service... (attempt $i/$retries)"
        sleep 3
    done
    echo "❌ $service failed health check"
    return 1
}

# Build services function
build_services() {
    echo "📦 Building services for domain: $DOMAIN"
    
    case $DOMAIN in
        "activelog")
            echo "Building ActiveLog fitness services..."
            # Auth service (already running)
            health_check "auth" 8001 || exit 1
            
            # API Gateway
            health_check "api-gateway" 8088 || {
                echo "Starting API gateway..."
                cd services/api-gateway && python main.py &
                sleep 3
            }
            
            # AI Integration service for fitness insights
            if [ -d "services/ai-insights" ]; then
                echo "Building AI insights service..."
                cd services/ai-insights && python -m pip install -r requirements.txt
                PORT=8090 python main.py &
                sleep 3
                health_check "ai-insights" 8090
            fi
            ;;
        "personallog"|"fishinglog"|"dmlog"|"businesslog")
            echo "Building $DOMAIN services..."
            # Add domain-specific builds here
            ;;
        *)
            echo "Unknown domain: $DOMAIN"
            exit 1
            ;;
    esac
}

# Frontend build function
build_frontend() {
    echo "🎨 Building frontend for domain: $DOMAIN"
    
    local frontend_dir="frontend-${DOMAIN}"
    if [ -d "$frontend_dir" ]; then
        echo "Building $frontend_dir..."
        cd "$frontend_dir"
        npm ci --silent
        npm run build
        cd ..
    else
        echo "⚠️  Frontend not found for $DOMAIN, using unified frontend"
        if [ -d "frontend-unified" ]; then
            cd frontend-unified
            npm ci --silent
            npm run build
            cd ..
        fi
    fi
}

# Test function
run_tests() {
    if [ "$SKIP_TESTS" = "true" ]; then
        echo "⏭️  Skipping tests (SKIP_TESTS=true)"
        return 0
    fi
    
    echo "🧪 Running tests..."
    make test-quick || {
        echo "❌ Tests failed"
        return 1
    }
    echo "✅ Tests passed"
}

# Database migration function
run_migrations() {
    echo "🗄️  Running database migrations..."
    if [ -f "migrations/run_migrations.sh" ]; then
        cd migrations && ./run_migrations.sh && cd ..
    else
        echo "⚠️  No migrations found"
    fi
}

# Docker build function
docker_build() {
    echo "🐳 Building Docker containers..."
    
    # Build main services
    docker-compose build --parallel
    
    # Domain-specific containers
    case $DOMAIN in
        "activelog")
            echo "Building ActiveLog containers..."
            if [ -f "docker-compose.activelog.yml" ]; then
                docker-compose -f docker-compose.activelog.yml build
            fi
            ;;
    esac
}

# Production deployment function
deploy_production() {
    echo "🚀 Production deployment for $DOMAIN..."
    
    # Security checks
    make security || {
        echo "❌ Security checks failed"
        exit 1
    }
    
    # Production build
    BUILD_TYPE="production"
    docker_build
    
    # Start production services
    docker-compose -f docker-compose.prod.yml up -d
    
    # Health checks
    sleep 10
    health_check "api-gateway" 8088
    health_check "auth" 8001
}

# Main execution
main() {
    echo "Starting build for domain: $DOMAIN (type: $BUILD_TYPE)"
    
    # Pre-build cleanup
    make clean
    
    # Install dependencies
    echo "📦 Installing dependencies..."
    make install
    
    # Run migrations
    run_migrations
    
    # Build based on type
    case $BUILD_TYPE in
        "development")
            build_services
            build_frontend
            run_tests
            ;;
        "production")
            build_services
            build_frontend
            run_tests
            deploy_production
            ;;
        "docker")
            docker_build
            ;;
        *)
            echo "Unknown build type: $BUILD_TYPE"
            exit 1
            ;;
    esac
    
    echo "✅ Build completed successfully for $DOMAIN"
}

# Help function
show_help() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -d, --domain DOMAIN     Target domain (activelog, personallog, etc.)"
    echo "  -t, --type TYPE         Build type (development, production, docker)"
    echo "  -s, --skip-tests        Skip running tests"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --domain activelog --type development"
    echo "  $0 --domain personallog --type production"
    echo "  $0 --type docker --skip-tests"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--domain)
            DOMAIN="$2"
            shift 2
            ;;
        -t|--type)
            BUILD_TYPE="$2"
            shift 2
            ;;
        -s|--skip-tests)
            SKIP_TESTS="true"
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Execute main function
main