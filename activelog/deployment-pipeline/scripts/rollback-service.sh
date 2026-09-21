#!/bin/bash

# Service Rollback Script for DMLog
# Usage: ./rollback-service.sh <environment> <service> <target_version>

set -euo pipefail

ENVIRONMENT=${1:-staging}
SERVICE=${2:-dmlog-integration}
TARGET_VERSION=${3:-latest}
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

# Function to validate inputs
validate_inputs() {
    if [[ ! "$ENVIRONMENT" =~ ^(staging|production)$ ]]; then
        log_error "Environment must be 'staging' or 'production'"
        exit 1
    fi
    
    if [[ -z "$SERVICE" ]]; then
        log_error "Service name is required"
        exit 1
    fi
    
    if [[ -z "$TARGET_VERSION" ]]; then
        log_error "Target version is required"
        exit 1
    fi
    
    log_info "Rollback parameters validated"
    log_info "Environment: $ENVIRONMENT"
    log_info "Service: $SERVICE"
    log_info "Target Version: $TARGET_VERSION"
}

# Function to check prerequisites
check_prerequisites() {
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi
    
    # Check cluster connection
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    # Check namespace
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_error "Namespace $NAMESPACE does not exist"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Function to get current deployment info
get_current_deployment_info() {
    log_info "Getting current deployment information for $SERVICE"
    
    # Check if deployment exists
    if ! kubectl get deployment "$SERVICE" -n "$NAMESPACE" &> /dev/null; then
        log_error "Deployment $SERVICE not found in namespace $NAMESPACE"
        exit 1
    fi
    
    # Get current image and version
    local current_image=$(kubectl get deployment "$SERVICE" -n "$NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].image}')
    local current_version=$(echo "$current_image" | cut -d':' -f2)
    local current_replicas=$(kubectl get deployment "$SERVICE" -n "$NAMESPACE" -o jsonpath='{.spec.replicas}')
    
    log_info "Current image: $current_image"
    log_info "Current version: $current_version"
    log_info "Current replicas: $current_replicas"
    
    # Store in global variables
    CURRENT_IMAGE="$current_image"
    CURRENT_VERSION="$current_version"
    CURRENT_REPLICAS="$current_replicas"
}

# Function to verify target image exists
verify_target_image() {
    local target_image="ghcr.io/dmlog/${SERVICE}:${TARGET_VERSION}"
    
    log_info "Verifying target image: $target_image"
    
    # Try to get image manifest (requires registry access)
    # This is a basic check - in production you might use a more sophisticated method
    if kubectl run image-check-$(date +%s) --rm -i --image="$target_image" --restart=Never --command -- echo "Image exists" &> /dev/null; then
        log_success "Target image verified: $target_image"
    else
        log_error "Cannot verify target image: $target_image"
        log_warning "Proceeding with rollback anyway (image might exist but be inaccessible for verification)"
    fi
}

# Function to create rollback backup
create_rollback_backup() {
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_file="/tmp/${SERVICE}-${ENVIRONMENT}-backup-${timestamp}.yaml"
    
    log_info "Creating backup of current deployment"
    
    kubectl get deployment "$SERVICE" -n "$NAMESPACE" -o yaml > "$backup_file"
    
    if [[ -f "$backup_file" ]]; then
        log_success "Backup created: $backup_file"
        echo "$backup_file"  # Return backup file path
    else
        log_error "Failed to create backup"
        exit 1
    fi
}

# Function to perform blue-green rollback
blue_green_rollback() {
    local target_image="ghcr.io/dmlog/${SERVICE}:${TARGET_VERSION}"
    
    log_info "Starting blue-green rollback for $SERVICE to $TARGET_VERSION"
    
    # Determine current active color
    local active_color="blue"
    if kubectl get deployment "${SERVICE}-green" -n "$NAMESPACE" &> /dev/null; then
        local green_replicas=$(kubectl get deployment "${SERVICE}-green" -n "$NAMESPACE" -o jsonpath='{.spec.replicas}')
        if [[ "$green_replicas" -gt 0 ]]; then
            active_color="green"
        fi
    fi
    
    local rollback_color
    if [[ "$active_color" == "blue" ]]; then
        rollback_color="green"
    else
        rollback_color="blue"
    fi
    
    log_info "Current active color: $active_color, rolling back to: $rollback_color"
    
    # Create or update rollback color deployment
    create_rollback_deployment "$rollback_color" "$target_image"
    
    # Wait for rollback deployment to be ready
    log_info "Waiting for rollback deployment to be ready..."
    kubectl rollout status deployment/"${SERVICE}-${rollback_color}" -n "$NAMESPACE" --timeout=300s
    
    # Run health checks on rollback deployment
    if ! run_health_checks "${SERVICE}-${rollback_color}"; then
        log_error "Health checks failed for rollback deployment"
        return 1
    fi
    
    # Switch traffic to rollback deployment
    log_info "Switching traffic to rollback deployment"
    kubectl patch service "$SERVICE" -n "$NAMESPACE" -p "{\"spec\":{\"selector\":{\"version\":\"$rollback_color\"}}}"
    
    # Wait for traffic switch to take effect
    sleep 10
    
    # Verify traffic switch
    if ! run_health_checks "$SERVICE"; then
        log_error "Health checks failed after traffic switch"
        # Switch back to original
        kubectl patch service "$SERVICE" -n "$NAMESPACE" -p "{\"spec\":{\"selector\":{\"version\":\"$active_color\"}}}"
        return 1
    fi
    
    # Scale down old deployment
    log_info "Scaling down old deployment"
    kubectl scale deployment "${SERVICE}-${active_color}" -n "$NAMESPACE" --replicas=0
    
    log_success "Blue-green rollback completed successfully"
}

# Function to perform rolling update rollback
rolling_update_rollback() {
    local target_image="ghcr.io/dmlog/${SERVICE}:${TARGET_VERSION}"
    
    log_info "Starting rolling update rollback for $SERVICE to $TARGET_VERSION"
    
    # Update deployment with target image
    kubectl set image deployment/"$SERVICE" -n "$NAMESPACE" "${SERVICE}=${target_image}"
    
    # Wait for rollout to complete
    log_info "Waiting for rollback to complete..."
    kubectl rollout status deployment/"$SERVICE" -n "$NAMESPACE" --timeout=300s
    
    # Verify rollback
    local new_image=$(kubectl get deployment "$SERVICE" -n "$NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].image}')
    if [[ "$new_image" == "$target_image" ]]; then
        log_success "Rolling update rollback completed successfully"
    else
        log_error "Rollback verification failed. Expected: $target_image, Got: $new_image"
        return 1
    fi
}

# Function to create rollback deployment for blue-green
create_rollback_deployment() {
    local color=$1
    local target_image=$2
    
    cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${SERVICE}-${color}
  namespace: ${NAMESPACE}
  labels:
    app: ${SERVICE}
    version: ${color}
    environment: ${ENVIRONMENT}
    rollback: "true"
spec:
  replicas: ${CURRENT_REPLICAS}
  selector:
    matchLabels:
      app: ${SERVICE}
      version: ${color}
  template:
    metadata:
      labels:
        app: ${SERVICE}
        version: ${color}
        environment: ${ENVIRONMENT}
        rollback: "true"
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
        rollback.timestamp: "$(date -u +%Y%m%d%H%M%S)"
        rollback.target-version: "${TARGET_VERSION}"
    spec:
      imagePullSecrets:
        - name: registry-secret
      containers:
        - name: ${SERVICE}
          image: ${target_image}
          ports:
            - containerPort: 8080
              protocol: TCP
          env:
            - name: VERSION
              value: "${TARGET_VERSION}"
            - name: COLOR
              value: "${color}"
            - name: ENVIRONMENT
              value: "${ENVIRONMENT}"
            - name: ROLLBACK
              value: "true"
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

# Function to run health checks
run_health_checks() {
    local service_name=$1
    
    log_info "Running health checks for $service_name"
    
    # Get service endpoint
    local service_ip=$(kubectl get service "$service_name" -n "$NAMESPACE" -o jsonpath='{.spec.clusterIP}')
    
    if [[ -z "$service_ip" ]]; then
        log_error "Could not get service IP for $service_name"
        return 1
    fi
    
    # Run health check
    for i in {1..10}; do
        if kubectl run health-check-$(date +%s) --rm -i --image=curlimages/curl --restart=Never -- \
           curl -f -s "http://${service_ip}:8080/health" > /dev/null 2>&1; then
            log_success "Health check passed for $service_name"
            return 0
        fi
        log_warning "Health check attempt $i failed, retrying in 10 seconds..."
        sleep 10
    done
    
    log_error "Health checks failed for $service_name"
    return 1
}

# Function to verify rollback success
verify_rollback() {
    log_info "Verifying rollback success"
    
    # Check deployment image
    local current_image=$(kubectl get deployment "$SERVICE" -n "$NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].image}')
    local expected_image="ghcr.io/dmlog/${SERVICE}:${TARGET_VERSION}"
    
    if [[ "$current_image" == "$expected_image" ]] || [[ "$current_image" =~ $TARGET_VERSION ]]; then
        log_success "Image rollback verified: $current_image"
    else
        log_error "Image rollback verification failed. Expected: $expected_image, Got: $current_image"
        return 1
    fi
    
    # Check deployment status
    local ready_replicas=$(kubectl get deployment "$SERVICE" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}')
    local desired_replicas=$(kubectl get deployment "$SERVICE" -n "$NAMESPACE" -o jsonpath='{.spec.replicas}')
    
    if [[ "$ready_replicas" == "$desired_replicas" && "$ready_replicas" -gt 0 ]]; then
        log_success "Deployment status verified: $ready_replicas/$desired_replicas replicas ready"
    else
        log_error "Deployment status verification failed: $ready_replicas/$desired_replicas replicas ready"
        return 1
    fi
    
    # Final health check
    if run_health_checks "$SERVICE"; then
        log_success "Final health check passed"
    else
        log_error "Final health check failed"
        return 1
    fi
    
    log_success "Rollback verification completed successfully"
}

# Function to cleanup rollback artifacts
cleanup_rollback() {
    log_info "Cleaning up rollback artifacts"
    
    # Remove temporary pods if any
    kubectl delete pods -n "$NAMESPACE" -l "rollback=true" --ignore-not-found=true
    
    log_info "Rollback cleanup completed"
}

# Function to record rollback in annotations
record_rollback() {
    local timestamp=$(date -u +%Y%m%d%H%M%S)
    
    kubectl annotate deployment "$SERVICE" -n "$NAMESPACE" \
        "rollback.dmlog.com/timestamp=${timestamp}" \
        "rollback.dmlog.com/target-version=${TARGET_VERSION}" \
        "rollback.dmlog.com/previous-version=${CURRENT_VERSION}" \
        --overwrite
    
    log_info "Rollback recorded in deployment annotations"
}

# Main rollback function
main() {
    log_info "Starting rollback process for $SERVICE in $ENVIRONMENT environment"
    
    # Validate inputs and check prerequisites
    validate_inputs
    check_prerequisites
    
    # Get current deployment information
    get_current_deployment_info
    
    # Check if already at target version
    if [[ "$CURRENT_VERSION" == "$TARGET_VERSION" ]]; then
        log_warning "Service is already at target version $TARGET_VERSION"
        log_info "No rollback needed"
        exit 0
    fi
    
    # Verify target image
    verify_target_image
    
    # Create backup
    BACKUP_FILE=$(create_rollback_backup)
    
    # Determine rollback strategy
    local rollback_strategy="rolling"
    if kubectl get deployment "${SERVICE}-blue" -n "$NAMESPACE" &> /dev/null || kubectl get deployment "${SERVICE}-green" -n "$NAMESPACE" &> /dev/null; then
        rollback_strategy="blue-green"
    fi
    
    log_info "Using $rollback_strategy rollback strategy"
    
    # Perform rollback
    if [[ "$rollback_strategy" == "blue-green" ]]; then
        if ! blue_green_rollback; then
            log_error "Blue-green rollback failed"
            log_info "Backup available at: $BACKUP_FILE"
            exit 1
        fi
    else
        if ! rolling_update_rollback; then
            log_error "Rolling update rollback failed"
            log_info "Attempting to restore from backup: $BACKUP_FILE"
            kubectl apply -f "$BACKUP_FILE"
            exit 1
        fi
    fi
    
    # Verify rollback
    if ! verify_rollback; then
        log_error "Rollback verification failed"
        exit 1
    fi
    
    # Record rollback
    record_rollback
    
    # Cleanup
    cleanup_rollback
    
    log_success "Rollback completed successfully!"
    log_info "Service: $SERVICE"
    log_info "Environment: $ENVIRONMENT"  
    log_info "Rolled back from: $CURRENT_VERSION"
    log_info "Rolled back to: $TARGET_VERSION"
    log_info "Backup available at: $BACKUP_FILE"
}

# Execute main function if script is run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi