#!/bin/bash

# Blue-Green Deployment Script for DMLog Services
# Usage: ./blue-green-deploy.sh <environment> <version> [service]

set -euo pipefail

ENVIRONMENT=${1:-staging}
VERSION=${2:-latest}
SERVICE=${3:-all}
NAMESPACE="dmlog-${ENVIRONMENT}"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(staging|production)$ ]]; then
    log_error "Environment must be 'staging' or 'production'"
    exit 1
fi

# Services to deploy
SERVICES=("dmlog-integration" "data-orchestrator" "frontend-dmlog-final" "dmlog-gamedev")

if [[ "$SERVICE" != "all" ]]; then
    SERVICES=("$SERVICE")
fi

# Function to check if kubectl is available and configured
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi

    if ! kubectl cluster-info &> /dev/null; then
        log_error "kubectl is not configured or cluster is not accessible"
        exit 1
    fi

    log_info "kubectl is configured and cluster is accessible"
}

# Function to check if namespace exists
check_namespace() {
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_error "Namespace $NAMESPACE does not exist"
        exit 1
    fi
    log_info "Namespace $NAMESPACE exists"
}

# Function to determine current active color
get_active_color() {
    local service_name=$1
    local current_color="blue"
    
    # Check if green version exists and is currently active
    if kubectl get deployment "${service_name}-green" -n "$NAMESPACE" &> /dev/null; then
        local green_replicas=$(kubectl get deployment "${service_name}-green" -n "$NAMESPACE" -o jsonpath='{.spec.replicas}')
        if [[ "$green_replicas" -gt 0 ]]; then
            current_color="green"
        fi
    fi
    
    echo "$current_color"
}

# Function to get inactive color
get_inactive_color() {
    local active_color=$1
    if [[ "$active_color" == "blue" ]]; then
        echo "green"
    else
        echo "blue"
    fi
}

# Function to create deployment manifest
create_deployment_manifest() {
    local service_name=$1
    local color=$2
    local image_version=$3
    
    cat <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${service_name}-${color}
  namespace: ${NAMESPACE}
  labels:
    app: ${service_name}
    version: ${color}
    environment: ${ENVIRONMENT}
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ${service_name}
      version: ${color}
  template:
    metadata:
      labels:
        app: ${service_name}
        version: ${color}
        environment: ${ENVIRONMENT}
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
        deployment.timestamp: "$(date -u +%Y%m%d%H%M%S)"
    spec:
      imagePullSecrets:
        - name: registry-secret
      containers:
        - name: ${service_name}
          image: ghcr.io/dmlog/${service_name}:${image_version}
          ports:
            - containerPort: 8080
              protocol: TCP
          env:
            - name: VERSION
              value: "${image_version}"
            - name: COLOR
              value: "${color}"
            - name: ENVIRONMENT
              value: "${ENVIRONMENT}"
          envFrom:
            - configMapRef:
                name: dmlog-config
            - secretRef:
                name: dmlog-database
            - secretRef:
                name: dmlog-redis
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /ready
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 2
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
EOF
}

# Function to create service manifest
create_service_manifest() {
    local service_name=$1
    local color=$2
    
    cat <<EOF
apiVersion: v1
kind: Service
metadata:
  name: ${service_name}-${color}
  namespace: ${NAMESPACE}
  labels:
    app: ${service_name}
    version: ${color}
spec:
  type: ClusterIP
  ports:
    - port: 8080
      targetPort: 8080
      protocol: TCP
      name: http
  selector:
    app: ${service_name}
    version: ${color}
EOF
}

# Function to deploy to inactive color
deploy_inactive() {
    local service_name=$1
    local active_color=$2
    local inactive_color=$3
    local image_version=$4
    
    log_info "Deploying $service_name version $image_version to $inactive_color environment"
    
    # Create deployment manifest
    create_deployment_manifest "$service_name" "$inactive_color" "$image_version" | kubectl apply -f -
    
    # Create service manifest
    create_service_manifest "$service_name" "$inactive_color" | kubectl apply -f -
    
    # Wait for rollout to complete
    log_info "Waiting for $service_name-$inactive_color rollout to complete..."
    kubectl rollout status deployment/"${service_name}-${inactive_color}" -n "$NAMESPACE" --timeout=300s
    
    # Verify deployment
    local ready_replicas=$(kubectl get deployment "${service_name}-${inactive_color}" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}')
    local desired_replicas=$(kubectl get deployment "${service_name}-${inactive_color}" -n "$NAMESPACE" -o jsonpath='{.spec.replicas}')
    
    if [[ "$ready_replicas" == "$desired_replicas" && "$ready_replicas" -gt 0 ]]; then
        log_success "$service_name-$inactive_color deployment completed successfully"
    else
        log_error "$service_name-$inactive_color deployment failed. Ready: $ready_replicas, Desired: $desired_replicas"
        return 1
    fi
}

# Function to run health checks
run_health_checks() {
    local service_name=$1
    local color=$2
    
    log_info "Running health checks for $service_name-$color"
    
    # Get service endpoint
    local service_ip=$(kubectl get service "${service_name}-${color}" -n "$NAMESPACE" -o jsonpath='{.spec.clusterIP}')
    
    # Run health check
    for i in {1..10}; do
        if kubectl run health-check-$(date +%s) --rm -i --image=curlimages/curl --restart=Never -- \
           curl -f -s "http://${service_ip}:8080/health" > /dev/null 2>&1; then
            log_success "Health check passed for $service_name-$color"
            return 0
        fi
        log_warning "Health check attempt $i failed, retrying..."
        sleep 10
    done
    
    log_error "Health checks failed for $service_name-$color"
    return 1
}

# Function to run smoke tests
run_smoke_tests() {
    local service_name=$1
    local color=$2
    
    log_info "Running smoke tests for $service_name-$color"
    
    # Run basic smoke tests
    kubectl run smoke-test-$(date +%s) --rm -i --image=curlimages/curl --restart=Never -- \
        sh -c "
        SERVICE_IP=\$(nslookup ${service_name}-${color}.${NAMESPACE}.svc.cluster.local | grep Address | tail -1 | cut -d' ' -f3)
        
        # Test health endpoint
        curl -f -s http://\$SERVICE_IP:8080/health || exit 1
        
        # Test ready endpoint
        curl -f -s http://\$SERVICE_IP:8080/ready || exit 1
        
        # Test main functionality (if available)
        if curl -f -s http://\$SERVICE_IP:8080/api/status > /dev/null 2>&1; then
            echo 'API endpoint accessible'
        fi
        
        echo 'Smoke tests passed'
        "
    
    if [[ $? -eq 0 ]]; then
        log_success "Smoke tests passed for $service_name-$color"
        return 0
    else
        log_error "Smoke tests failed for $service_name-$color"
        return 1
    fi
}

# Function to update main service to point to new color
switch_traffic() {
    local service_name=$1
    local new_color=$2
    
    log_info "Switching traffic from main service to $service_name-$new_color"
    
    # Update main service selector to point to new color
    kubectl patch service "$service_name" -n "$NAMESPACE" -p "{\"spec\":{\"selector\":{\"version\":\"$new_color\"}}}"
    
    # Verify the switch
    local current_selector=$(kubectl get service "$service_name" -n "$NAMESPACE" -o jsonpath='{.spec.selector.version}')
    if [[ "$current_selector" == "$new_color" ]]; then
        log_success "Traffic successfully switched to $service_name-$new_color"
        return 0
    else
        log_error "Failed to switch traffic to $service_name-$new_color"
        return 1
    fi
}

# Function to scale down old color
scale_down_old() {
    local service_name=$1
    local old_color=$2
    
    log_info "Scaling down $service_name-$old_color"
    
    kubectl scale deployment "${service_name}-${old_color}" -n "$NAMESPACE" --replicas=0
    
    # Wait for scale down
    kubectl rollout status deployment/"${service_name}-${old_color}" -n "$NAMESPACE" --timeout=120s
    
    log_success "$service_name-$old_color scaled down successfully"
}

# Function to cleanup old resources (optional)
cleanup_old() {
    local service_name=$1
    local old_color=$2
    
    log_warning "Cleaning up old $service_name-$old_color resources"
    
    # Delete old deployment and service
    kubectl delete deployment "${service_name}-${old_color}" -n "$NAMESPACE" --ignore-not-found=true
    kubectl delete service "${service_name}-${old_color}" -n "$NAMESPACE" --ignore-not-found=true
    
    log_info "Cleanup completed for $service_name-$old_color"
}

# Function to rollback on failure
rollback_deployment() {
    local service_name=$1
    local failed_color=$2
    local rollback_color=$3
    
    log_error "Rolling back $service_name deployment"
    
    # Switch traffic back to old color
    switch_traffic "$service_name" "$rollback_color"
    
    # Scale down failed deployment
    scale_down_old "$service_name" "$failed_color"
    
    log_warning "Rollback completed for $service_name"
}

# Main deployment function
deploy_service() {
    local service_name=$1
    local image_version=$2
    
    log_info "Starting blue-green deployment for $service_name version $image_version"
    
    # Determine current active color
    local active_color=$(get_active_color "$service_name")
    local inactive_color=$(get_inactive_color "$active_color")
    
    log_info "Current active color: $active_color, deploying to: $inactive_color"
    
    # Deploy to inactive color
    if ! deploy_inactive "$service_name" "$active_color" "$inactive_color" "$image_version"; then
        log_error "Failed to deploy $service_name to $inactive_color"
        return 1
    fi
    
    # Run health checks
    if ! run_health_checks "$service_name" "$inactive_color"; then
        log_error "Health checks failed for $service_name-$inactive_color"
        scale_down_old "$service_name" "$inactive_color"
        return 1
    fi
    
    # Run smoke tests
    if ! run_smoke_tests "$service_name" "$inactive_color"; then
        log_error "Smoke tests failed for $service_name-$inactive_color"
        scale_down_old "$service_name" "$inactive_color"
        return 1
    fi
    
    # Switch traffic to new color
    if ! switch_traffic "$service_name" "$inactive_color"; then
        log_error "Failed to switch traffic for $service_name"
        rollback_deployment "$service_name" "$inactive_color" "$active_color"
        return 1
    fi
    
    # Wait a bit to monitor for issues
    log_info "Monitoring new deployment for 30 seconds..."
    sleep 30
    
    # Final health check
    if ! run_health_checks "$service_name" "$inactive_color"; then
        log_error "Post-switch health checks failed for $service_name"
        rollback_deployment "$service_name" "$inactive_color" "$active_color"
        return 1
    fi
    
    # Scale down old color
    scale_down_old "$service_name" "$active_color"
    
    log_success "Blue-green deployment completed successfully for $service_name"
    
    # Optional: cleanup old resources after some time
    # cleanup_old "$service_name" "$active_color"
    
    return 0
}

# Main script execution
main() {
    log_info "Starting blue-green deployment for environment: $ENVIRONMENT, version: $VERSION"
    
    # Pre-flight checks
    check_kubectl
    check_namespace
    
    # Deploy each service
    local failed_services=()
    
    for service in "${SERVICES[@]}"; do
        log_info "Processing service: $service"
        
        if deploy_service "$service" "$VERSION"; then
            log_success "Successfully deployed $service"
        else
            log_error "Failed to deploy $service"
            failed_services+=("$service")
        fi
        
        # Add delay between service deployments
        sleep 10
    done
    
    # Report results
    if [[ ${#failed_services[@]} -eq 0 ]]; then
        log_success "All services deployed successfully!"
        log_info "Blue-green deployment completed for $ENVIRONMENT environment"
    else
        log_error "Some services failed to deploy: ${failed_services[*]}"
        exit 1
    fi
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi