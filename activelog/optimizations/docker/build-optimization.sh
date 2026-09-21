#!/bin/bash
# Docker build optimization script for ActiveLog

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="${IMAGE_NAME:-activelog}"
IMAGE_TAG="${IMAGE_TAG:-optimized}"
BUILD_CONTEXT="${BUILD_CONTEXT:-../..}"
DOCKERFILE="${DOCKERFILE:-optimizations/docker/Dockerfile.optimized}"
REGISTRY="${REGISTRY:-}"
PUSH_TO_REGISTRY="${PUSH_TO_REGISTRY:-false}"
USE_BUILDKIT="${USE_BUILDKIT:-true}"
CACHE_FROM="${CACHE_FROM:-}"
CACHE_TO="${CACHE_TO:-}"
PLATFORM="${PLATFORM:-linux/amd64}"
NO_CACHE="${NO_CACHE:-false}"

# Functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

# Check dependencies
check_dependencies() {
    log "Checking dependencies..."
    
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed or not in PATH"
    fi
    
    if ! docker buildx version &> /dev/null; then
        warning "Docker Buildx not available. Falling back to regular docker build."
        USE_BUILDKIT=false
    fi
    
    success "Dependencies check passed"
}

# Clean up old images and build cache
cleanup() {
    log "Cleaning up old images and build cache..."
    
    # Remove dangling images
    if docker images -f "dangling=true" -q | grep -q .; then
        docker rmi $(docker images -f "dangling=true" -q) 2>/dev/null || true
    fi
    
    # Remove old versions of the image (keep last 3)
    if docker images "${IMAGE_NAME}" --format "table {{.ID}}\t{{.Tag}}\t{{.CreatedAt}}" | tail -n +2 | sort -k3 -r | tail -n +4 | awk '{print $1}' | grep -q .; then
        docker rmi $(docker images "${IMAGE_NAME}" --format "table {{.ID}}\t{{.Tag}}\t{{.CreatedAt}}" | tail -n +2 | sort -k3 -r | tail -n +4 | awk '{print $1}') 2>/dev/null || true
    fi
    
    # Prune build cache (keep last 24 hours)
    docker buildx prune -f --filter until=24h 2>/dev/null || docker builder prune -f --filter until=24h 2>/dev/null || true
    
    success "Cleanup completed"
}

# Optimize build context
optimize_build_context() {
    log "Optimizing build context..."
    
    # Check for .dockerignore
    if [[ ! -f "${BUILD_CONTEXT}/.dockerignore" ]]; then
        warning ".dockerignore not found. Creating one..."
        cat > "${BUILD_CONTEXT}/.dockerignore" << EOF
# Git
.git
.gitignore
.gitattributes

# Documentation
README.md
docs/
*.md

# Development files
.env
.env.local
.env.development
.vscode/
.idea/
*.pyc
__pycache__/
.pytest_cache/
.coverage
htmlcov/

# Logs
*.log
logs/
.npm/

# OS generated files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Node modules (if any)
node_modules/
npm-debug.log*

# Python virtual environments
venv/
env/
.venv/

# Test files
tests/
test_*/
*_test.py
test.py

# Temporary files
tmp/
temp/
*.tmp
*.temp

# Docker files
Dockerfile*
docker-compose*.yml
.dockerignore
EOF
    fi
    
    # Calculate build context size
    BUILD_CONTEXT_SIZE=$(du -sh "${BUILD_CONTEXT}" 2>/dev/null | cut -f1 || echo "unknown")
    log "Build context size: ${BUILD_CONTEXT_SIZE}"
    
    success "Build context optimization completed"
}

# Build the Docker image with optimizations
build_image() {
    log "Building Docker image: ${IMAGE_NAME}:${IMAGE_TAG}"
    
    # Prepare build arguments
    BUILD_ARGS=()
    BUILD_ARGS+=("--file" "${BUILD_CONTEXT}/${DOCKERFILE}")
    BUILD_ARGS+=("--tag" "${IMAGE_NAME}:${IMAGE_TAG}")
    BUILD_ARGS+=("--platform" "${PLATFORM}")
    
    if [[ "${NO_CACHE}" == "true" ]]; then
        BUILD_ARGS+=("--no-cache")
    fi
    
    # Add cache configuration
    if [[ -n "${CACHE_FROM}" ]]; then
        BUILD_ARGS+=("--cache-from" "${CACHE_FROM}")
    fi
    
    if [[ -n "${CACHE_TO}" ]]; then
        BUILD_ARGS+=("--cache-to" "${CACHE_TO}")
    fi
    
    # Build arguments for optimization
    BUILD_ARGS+=("--build-arg" "BUILDKIT_INLINE_CACHE=1")
    BUILD_ARGS+=("--build-arg" "DOCKER_BUILDKIT=1")
    
    # Use BuildKit if available
    if [[ "${USE_BUILDKIT}" == "true" ]]; then
        export DOCKER_BUILDKIT=1
        
        # Use buildx for advanced features
        if command -v docker buildx &> /dev/null; then
            BUILD_ARGS+=("--load")  # Load image to local Docker daemon
            docker buildx build "${BUILD_ARGS[@]}" "${BUILD_CONTEXT}"
        else
            docker build "${BUILD_ARGS[@]}" "${BUILD_CONTEXT}"
        fi
    else
        docker build "${BUILD_ARGS[@]}" "${BUILD_CONTEXT}"
    fi
    
    success "Docker image built successfully"
}

# Analyze image size and layers
analyze_image() {
    log "Analyzing image size and layers..."
    
    # Get image size
    IMAGE_SIZE=$(docker images "${IMAGE_NAME}:${IMAGE_TAG}" --format "table {{.Size}}" | tail -n 1)
    log "Final image size: ${IMAGE_SIZE}"
    
    # Show layer information
    log "Image layers:"
    docker history "${IMAGE_NAME}:${IMAGE_TAG}" --format "table {{.CreatedBy}}\t{{.Size}}" | head -10
    
    # Security scan if available
    if command -v docker scan &> /dev/null; then
        log "Running security scan..."
        docker scan "${IMAGE_NAME}:${IMAGE_TAG}" || warning "Security scan failed or found vulnerabilities"
    fi
    
    success "Image analysis completed"
}

# Test the built image
test_image() {
    log "Testing the built image..."
    
    # Basic smoke test
    CONTAINER_ID=$(docker run -d --rm -p 8001:8000 "${IMAGE_NAME}:${IMAGE_TAG}")
    
    # Wait for container to start
    sleep 10
    
    # Test health endpoint
    if curl -f http://localhost:8001/health &>/dev/null; then
        success "Health check passed"
    else
        warning "Health check failed"
    fi
    
    # Stop test container
    docker stop "${CONTAINER_ID}" &>/dev/null || true
    
    success "Image testing completed"
}

# Push to registry
push_image() {
    if [[ "${PUSH_TO_REGISTRY}" != "true" ]]; then
        log "Skipping registry push (PUSH_TO_REGISTRY=false)"
        return
    fi
    
    if [[ -z "${REGISTRY}" ]]; then
        warning "REGISTRY not set, skipping push"
        return
    fi
    
    log "Pushing image to registry: ${REGISTRY}"
    
    # Tag for registry
    REGISTRY_TAG="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
    docker tag "${IMAGE_NAME}:${IMAGE_TAG}" "${REGISTRY_TAG}"
    
    # Push to registry
    docker push "${REGISTRY_TAG}"
    
    # Also push as latest if this is a production build
    if [[ "${IMAGE_TAG}" == "production" ]] || [[ "${IMAGE_TAG}" == "main" ]]; then
        LATEST_TAG="${REGISTRY}/${IMAGE_NAME}:latest"
        docker tag "${IMAGE_NAME}:${IMAGE_TAG}" "${LATEST_TAG}"
        docker push "${LATEST_TAG}"
        success "Pushed ${LATEST_TAG}"
    fi
    
    success "Image pushed to registry: ${REGISTRY_TAG}"
}

# Multi-platform build
build_multiplatform() {
    if [[ "${PLATFORM}" == *","* ]]; then
        log "Building multi-platform image for: ${PLATFORM}"
        
        # Create and use a new builder instance
        docker buildx create --name multiplatform-builder --use 2>/dev/null || docker buildx use multiplatform-builder
        
        BUILD_ARGS=()
        BUILD_ARGS+=("--file" "${BUILD_CONTEXT}/${DOCKERFILE}")
        BUILD_ARGS+=("--tag" "${IMAGE_NAME}:${IMAGE_TAG}")
        BUILD_ARGS+=("--platform" "${PLATFORM}")
        BUILD_ARGS+=("--push")  # Push directly for multi-platform
        
        if [[ -n "${REGISTRY}" ]]; then
            BUILD_ARGS+=("--tag" "${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}")
        fi
        
        docker buildx build "${BUILD_ARGS[@]}" "${BUILD_CONTEXT}"
        
        success "Multi-platform build completed"
        return 0
    fi
    
    return 1
}

# Generate build report
generate_report() {
    log "Generating build report..."
    
    REPORT_FILE="${BUILD_CONTEXT}/build-report-$(date +%Y%m%d-%H%M%S).txt"
    
    cat > "${REPORT_FILE}" << EOF
ActiveLog Docker Build Report
============================
Date: $(date)
Image: ${IMAGE_NAME}:${IMAGE_TAG}
Platform: ${PLATFORM}
Registry: ${REGISTRY:-"Not set"}
Build Context: ${BUILD_CONTEXT}
Dockerfile: ${DOCKERFILE}

Image Information:
$(docker images "${IMAGE_NAME}:${IMAGE_TAG}" --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}\t{{.CreatedAt}}")

Layer Information:
$(docker history "${IMAGE_NAME}:${IMAGE_TAG}" --format "table {{.CreatedBy}}\t{{.Size}}")

Build Configuration:
- BuildKit: ${USE_BUILDKIT}
- No Cache: ${NO_CACHE}
- Cache From: ${CACHE_FROM:-"Not set"}
- Cache To: ${CACHE_TO:-"Not set"}
- Push to Registry: ${PUSH_TO_REGISTRY}

Build Context Size: ${BUILD_CONTEXT_SIZE:-"Unknown"}
EOF
    
    log "Build report saved to: ${REPORT_FILE}"
}

# Main execution
main() {
    log "Starting optimized Docker build for ActiveLog"
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --image-name)
                IMAGE_NAME="$2"
                shift 2
                ;;
            --tag)
                IMAGE_TAG="$2"
                shift 2
                ;;
            --registry)
                REGISTRY="$2"
                shift 2
                ;;
            --push)
                PUSH_TO_REGISTRY="true"
                shift
                ;;
            --no-cache)
                NO_CACHE="true"
                shift
                ;;
            --platform)
                PLATFORM="$2"
                shift 2
                ;;
            --cache-from)
                CACHE_FROM="$2"
                shift 2
                ;;
            --cache-to)
                CACHE_TO="$2"
                shift 2
                ;;
            --help)
                echo "Usage: $0 [options]"
                echo "Options:"
                echo "  --image-name NAME    Image name (default: activelog)"
                echo "  --tag TAG           Image tag (default: optimized)"
                echo "  --registry URL      Registry URL for pushing"
                echo "  --push              Push to registry after build"
                echo "  --no-cache          Build without cache"
                echo "  --platform PLATFORM Target platform (default: linux/amd64)"
                echo "  --cache-from IMAGE  Cache source image"
                echo "  --cache-to DEST     Cache destination"
                echo "  --help              Show this help"
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                ;;
        esac
    done
    
    # Execute build pipeline
    check_dependencies
    cleanup
    optimize_build_context
    
    # Try multi-platform build first
    if ! build_multiplatform; then
        build_image
        analyze_image
        test_image
        push_image
    fi
    
    generate_report
    
    success "Docker build optimization completed successfully!"
    log "Image: ${IMAGE_NAME}:${IMAGE_TAG}"
    if [[ -n "${REGISTRY}" ]] && [[ "${PUSH_TO_REGISTRY}" == "true" ]]; then
        log "Registry: ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
    fi
}

# Run main function
main "$@"