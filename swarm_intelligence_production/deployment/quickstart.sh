#!/bin/bash
#
# Swarm Intelligence Platform - One-Click Quickstart
# Deploys entire platform in 5-10 minutes
#
# Usage:
#   ./quickstart.sh                    # Auto-detect cloud provider
#   ./quickstart.sh --cloud aws       # Force AWS
#   ./quickstart.sh --local           # Deploy locally with minikube
#

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOYMENT_TYPE="staging"
CLOUD_PROVIDER=""
LOCAL_MODE=false

# Logging
log() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $*"
}

log_error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ERROR:${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] WARN:${NC} $*"
}

log_info() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $*"
}

log_step() {
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} $*"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════════╝${NC}"
}

spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='|/-\'
    while ps -p $pid > /dev/null 2>&1; do
        local temp=${spinstr#?}
        printf " [%c]  " "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "    \b\b\b\b"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --cloud)
            CLOUD_PROVIDER="$2"
            shift 2
            ;;
        --local)
            LOCAL_MODE=true
            shift
            ;;
        --production)
            DEPLOYMENT_TYPE="production"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --cloud PROVIDER    Cloud provider (aws|gcp|azure)"
            echo "  --local            Deploy locally with minikube"
            echo "  --production       Deploy to production (requires confirmation)"
            echo "  -h, --help         Show this help"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# ASCII Art Banner
show_banner() {
    echo -e "${MAGENTA}"
    cat << "EOF"
    ____                                  ____      __       ____
   / ___/_      ______ __________  ___   /  _/___  / /____  / / /_
   \__ \ | /| / / __ `/ ___/ __ `__ \  / // __ \/ __/ _ \/ / / /
  ___/ / |/ |/ / /_/ / /  / / / / / /_/ // / / / /_/  __/ / / /
 /____/|__/|__/\__,_/_/  /_/ /_/ /_/_____/_/ /_/\__/\___/_/_/_/

            SWARM INTELLIGENCE PLATFORM - QUICKSTART
EOF
    echo -e "${NC}"
}

# Auto-detect cloud provider
detect_cloud_provider() {
    if $LOCAL_MODE; then
        echo "local"
        return
    fi

    if [ -n "$CLOUD_PROVIDER" ]; then
        echo "$CLOUD_PROVIDER"
        return
    fi

    # Check AWS
    if command -v aws &> /dev/null && aws sts get-caller-identity &> /dev/null; then
        echo "aws"
        return
    fi

    # Check GCP
    if command -v gcloud &> /dev/null && gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
        echo "gcp"
        return
    fi

    # Check Azure
    if command -v az &> /dev/null && az account show &> /dev/null; then
        echo "azure"
        return
    fi

    # Default to local
    echo "local"
}

# Check prerequisites
check_prerequisites() {
    log_step "Checking Prerequisites"

    local missing_tools=()

    # Required tools
    local required_tools=("kubectl" "docker")

    if $LOCAL_MODE; then
        required_tools+=("minikube")
    else
        required_tools+=("terraform" "helm")
    fi

    for tool in "${required_tools[@]}"; do
        if command -v "$tool" &> /dev/null; then
            log_info "✓ $tool found"
        else
            missing_tools+=("$tool")
            log_error "✗ $tool not found"
        fi
    done

    if [ ${#missing_tools[@]} -gt 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_info "Please install missing tools and try again"
        exit 1
    fi

    log "All prerequisites met"
}

# Deploy locally with Minikube
deploy_local() {
    log_step "Local Deployment with Minikube"

    # Start minikube if not running
    if ! minikube status &> /dev/null; then
        log "Starting Minikube..."
        minikube start \
            --cpus=4 \
            --memory=8192 \
            --disk-size=20g \
            --driver=docker &
        spinner $!
        wait $!
        log "✓ Minikube started"
    else
        log_info "Minikube already running"
    fi

    # Enable addons
    log "Enabling Minikube addons..."
    minikube addons enable ingress &> /dev/null
    minikube addons enable metrics-server &> /dev/null
    log "✓ Addons enabled"

    # Use minikube docker env
    eval $(minikube docker-env)

    # Deploy using docker-compose (simpler for local)
    log "Deploying services..."
    cd "$PROJECT_ROOT/infrastructure/docker"
    docker-compose up -d &
    spinner $!
    wait $!

    log "✓ Services deployed"

    # Wait for services
    log "Waiting for services to be ready..."
    sleep 30

    # Get minikube IP
    MINIKUBE_IP=$(minikube ip)

    return 0
}

# Deploy to cloud
deploy_cloud() {
    local cloud=$1
    log_step "Cloud Deployment - $cloud"

    # Provision infrastructure
    log "Provisioning infrastructure on $cloud..."
    cd "$PROJECT_ROOT/infrastructure/terraform/$cloud"

    terraform init -input=false &> /dev/null &
    spinner $!
    wait $!

    case $cloud in
        aws)
            terraform apply \
                -var="cluster_name=swarm-quickstart-eks" \
                -var="environment=$DEPLOYMENT_TYPE" \
                -var="min_nodes=3" \
                -var="max_nodes=10" \
                -auto-approve &
            spinner $!
            wait $!

            # Update kubeconfig
            aws eks update-kubeconfig \
                --name swarm-quickstart-eks \
                --region us-east-1
            ;;
        gcp)
            terraform apply \
                -var="environment=$DEPLOYMENT_TYPE" \
                -auto-approve &
            spinner $!
            wait $!

            # Get credentials
            gcloud container clusters get-credentials \
                swarm-quickstart-gke \
                --region us-central1
            ;;
        azure)
            terraform apply \
                -var="environment=$DEPLOYMENT_TYPE" \
                -auto-approve &
            spinner $!
            wait $!

            # Get credentials
            az aks get-credentials \
                --resource-group swarm-quickstart-rg \
                --name swarm-quickstart-aks
            ;;
    esac

    log "✓ Infrastructure provisioned"
}

# Deploy application
deploy_application() {
    log_step "Deploying Application"

    cd "$PROJECT_ROOT"

    # Run deployment script
    log "Deploying application components..."
    "$SCRIPT_DIR/deploy.sh" \
        -e "$DEPLOYMENT_TYPE" \
        -c "${CLOUD_PROVIDER:-aws}" \
        -n swarm-intelligence &
    spinner $!
    wait $!

    log "✓ Application deployed"
}

# Run tests
run_tests() {
    log_step "Running Verification Tests"

    # Wait for services to stabilize
    log "Waiting for services to stabilize..."
    sleep 30

    # Run basic health check
    log "Running health checks..."

    local api_url
    if $LOCAL_MODE; then
        api_url="http://localhost:3000"
    else
        api_url=$(kubectl get ingress -n swarm-intelligence -o jsonpath='{.items[0].spec.rules[0].host}' 2>/dev/null || echo "http://localhost:3000")
    fi

    # Port forward if needed
    if [[ "$api_url" == "http://localhost:3000" ]]; then
        kubectl port-forward -n swarm-intelligence svc/swarm-api 3000:8080 &> /dev/null &
        local pf_pid=$!
        sleep 5
    fi

    # Test API
    if curl -sf "$api_url/health" > /dev/null 2>&1; then
        log "✓ API health check passed"
    else
        log_warn "API health check failed (may still be starting)"
    fi

    # Kill port forward
    [ -n "${pf_pid:-}" ] && kill $pf_pid 2>/dev/null || true
}

# Display access information
show_access_info() {
    log_step "Deployment Complete!"

    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                  ACCESS INFORMATION                    ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""

    if $LOCAL_MODE; then
        local MINIKUBE_IP=$(minikube ip 2>/dev/null || echo "localhost")
        echo -e "${CYAN}Frontend:${NC}    http://$MINIKUBE_IP"
        echo -e "${CYAN}API:${NC}         http://localhost:3000"
        echo -e "${CYAN}Grafana:${NC}     http://localhost:3001"
        echo -e "${CYAN}Prometheus:${NC}  http://localhost:9090"
        echo ""
        echo -e "${YELLOW}Note: Use these commands to access services:${NC}"
        echo ""
        echo "  # Port forward API"
        echo "  kubectl port-forward -n swarm-intelligence svc/swarm-api 3000:8080"
        echo ""
        echo "  # Port forward Grafana"
        echo "  kubectl port-forward -n swarm-intelligence svc/grafana 3001:3000"
        echo ""
        echo "  # Port forward Prometheus"
        echo "  kubectl port-forward -n swarm-intelligence svc/prometheus 9090:9090"
    else
        local LB_ADDRESS=$(kubectl get svc istio-ingressgateway -n istio-system \
            -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || \
            kubectl get svc istio-ingressgateway -n istio-system \
            -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || \
            echo "pending")

        if [[ "$LB_ADDRESS" == "pending" ]]; then
            echo -e "${YELLOW}Load Balancer is still provisioning...${NC}"
            echo "Run this command to get the address:"
            echo "  kubectl get svc istio-ingressgateway -n istio-system"
        else
            echo -e "${CYAN}Load Balancer:${NC} $LB_ADDRESS"
            echo ""
            echo "Configure DNS:"
            echo "  swarm-quickstart.example.com -> $LB_ADDRESS"
        fi

        echo ""
        echo -e "${CYAN}Monitoring (via port-forward):${NC}"
        echo "  kubectl port-forward -n swarm-intelligence svc/grafana 3000:3000"
        echo "  kubectl port-forward -n swarm-intelligence svc/prometheus 9090:9090"
    fi

    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                     NEXT STEPS                         ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "1. View pods:      kubectl get pods -n swarm-intelligence"
    echo "2. Check logs:     kubectl logs -f deployment/swarm-core -n swarm-intelligence"
    echo "3. Run tests:      python tests/e2e/test_full_workflow.py --target local"
    echo "4. Load test:      k6 run tests/e2e/load_test.js"
    echo "5. Documentation:  cat deployment/STAGING_DEPLOYMENT.md"
    echo ""

    # Save info to file
    local info_file="$PROJECT_ROOT/DEPLOYMENT_INFO.txt"
    cat > "$info_file" <<EOF
Swarm Intelligence Platform - Deployment Info
==============================================

Deployed: $(date)
Type: $DEPLOYMENT_TYPE
Cloud: ${CLOUD_PROVIDER:-local}

Access Information:
$([ "$LOCAL_MODE" = true ] && echo "Frontend: http://$(minikube ip 2>/dev/null || echo localhost)" || echo "Load Balancer: $LB_ADDRESS")

Cleanup Command:
$([ "$LOCAL_MODE" = true ] && echo "minikube delete" || echo "cd infrastructure/terraform/${CLOUD_PROVIDER} && terraform destroy")
EOF

    log_info "Deployment info saved to: $info_file"
}

# Cleanup on error
cleanup_on_error() {
    log_error "Deployment failed!"
    log_warn "You may need to manually clean up resources"

    if ! $LOCAL_MODE && [ -n "$CLOUD_PROVIDER" ]; then
        echo ""
        read -p "Do you want to destroy provisioned infrastructure? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cd "$PROJECT_ROOT/infrastructure/terraform/$CLOUD_PROVIDER"
            terraform destroy -auto-approve
        fi
    fi
}

# Main function
main() {
    show_banner

    # Production safety check
    if [[ "$DEPLOYMENT_TYPE" == "production" ]]; then
        echo -e "${RED}WARNING: You are about to deploy to PRODUCTION${NC}"
        read -p "Are you sure? Type 'yes' to continue: " -r
        if [[ ! $REPLY == "yes" ]]; then
            log "Deployment cancelled"
            exit 0
        fi
    fi

    # Detect cloud provider
    CLOUD_PROVIDER=$(detect_cloud_provider)
    log_info "Detected environment: $CLOUD_PROVIDER"

    # Check prerequisites
    check_prerequisites

    # Set error handler
    trap cleanup_on_error ERR

    # Deploy
    local start_time=$(date +%s)

    if $LOCAL_MODE || [[ "$CLOUD_PROVIDER" == "local" ]]; then
        LOCAL_MODE=true
        deploy_local
    else
        deploy_cloud "$CLOUD_PROVIDER"
    fi

    deploy_application
    run_tests

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    # Show results
    show_access_info

    echo ""
    log "✓ Deployment completed in $((duration / 60)) minutes $((duration % 60)) seconds"
    echo ""
}

# Run main
main "$@"
