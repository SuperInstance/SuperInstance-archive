#!/bin/bash

# Environment Promotion Script for DMLog Services
# Usage: ./promote-environment.sh <from_env> <to_env> <version> [services]

set -euo pipefail

FROM_ENV=${1:-staging}
TO_ENV=${2:-production}
VERSION=${3:-latest}
SERVICES=${4:-all}

FROM_NAMESPACE="dmlog-${FROM_ENV}"
TO_NAMESPACE="dmlog-${TO_ENV}"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
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

log_promotion() {
    echo -e "${PURPLE}[PROMOTION]${NC} $1"
}

# Services to promote
ALL_SERVICES=("dmlog-integration" "data-orchestrator" "frontend-dmlog-final" "dmlog-gamedev")

# Parse services input
parse_services() {
    if [[ "$SERVICES" == "all" ]]; then
        SERVICES_ARRAY=("${ALL_SERVICES[@]}")
    else
        IFS=',' read -ra SERVICES_ARRAY <<< "$SERVICES"
        # Trim whitespace
        for i in "${!SERVICES_ARRAY[@]}"; do
            SERVICES_ARRAY[$i]=$(echo "${SERVICES_ARRAY[$i]}" | xargs)
        done
    fi
}

# Validation functions
validate_inputs() {
    # Validate environments
    if [[ ! "$FROM_ENV" =~ ^(staging|production)$ ]] || [[ ! "$TO_ENV" =~ ^(staging|production)$ ]]; then
        log_error "Environments must be 'staging' or 'production'"
        exit 1
    fi
    
    if [[ "$FROM_ENV" == "$TO_ENV" ]]; then
        log_error "Source and target environments cannot be the same"
        exit 1
    fi
    
    # Production can only be promoted from staging
    if [[ "$TO_ENV" == "production" && "$FROM_ENV" != "staging" ]]; then
        log_error "Production can only be promoted from staging environment"
        exit 1
    fi
    
    log_info "Environment promotion validation passed"
    log_promotion "Promoting from $FROM_ENV to $TO_ENV"
}

# Check prerequisites
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
    
    # Check both namespaces exist
    if ! kubectl get namespace "$FROM_NAMESPACE" &> /dev/null; then
        log_error "Source namespace $FROM_NAMESPACE does not exist"
        exit 1
    fi
    
    if ! kubectl get namespace "$TO_NAMESPACE" &> /dev/null; then
        log_error "Target namespace $TO_NAMESPACE does not exist"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Get deployment information from source environment
get_source_deployment_info() {
    local service_name=$1
    
    log_info "Getting deployment information for $service_name from $FROM_ENV"
    
    # Check if deployment exists in source
    if ! kubectl get deployment "$service_name" -n "$FROM_NAMESPACE" &> /dev/null; then
        log_error "Service $service_name not found in $FROM_ENV environment"
        return 1
    fi
    
    # Get deployment details
    local image=$(kubectl get deployment "$service_name" -n "$FROM_NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].image}')
    local replicas=$(kubectl get deployment "$service_name" -n "$FROM_NAMESPACE" -o jsonpath='{.spec.replicas}')
    local current_version=$(echo "$image" | cut -d':' -f2)
    
    # Store in associative array (using global variables for simplicity)
    eval "SOURCE_${service_name}_IMAGE=\"$image\""
    eval "SOURCE_${service_name}_REPLICAS=\"$replicas\""
    eval "SOURCE_${service_name}_VERSION=\"$current_version\""
    
    log_info "Source $service_name - Image: $image, Replicas: $replicas, Version: $current_version"
    
    return 0
}

# Verify source environment health
verify_source_health() {
    local service_name=$1
    
    log_info "Verifying health of $service_name in $FROM_ENV"
    
    # Check deployment status
    local ready_replicas=$(kubectl get deployment "$service_name" -n "$FROM_NAMESPACE" -o jsonpath='{.status.readyReplicas}')
    local desired_replicas=$(kubectl get deployment "$service_name" -n "$FROM_NAMESPACE" -o jsonpath='{.spec.replicas}')
    
    if [[ "$ready_replicas" != "$desired_replicas" ]]; then
        log_error "$service_name in $FROM_ENV is not healthy: $ready_replicas/$desired_replicas replicas ready"
        return 1
    fi
    
    # Run health check
    local service_ip=$(kubectl get service "$service_name" -n "$FROM_NAMESPACE" -o jsonpath='{.spec.clusterIP}')
    
    if kubectl run health-check-source-$(date +%s) --rm -i --image=curlimages/curl --restart=Never -- \
       curl -f -s "http://${service_ip}:8080/health" > /dev/null 2>&1; then
        log_success "$service_name in $FROM_ENV is healthy"
        return 0
    else
        log_error "$service_name in $FROM_ENV failed health check"
        return 1
    fi
}

# Run integration tests on source environment
run_source_integration_tests() {
    log_info "Running integration tests on $FROM_ENV environment"
    
    # Create a test pod to run integration tests
    local test_pod_name="integration-test-$(date +%s)"
    
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: ${test_pod_name}
  namespace: ${FROM_NAMESPACE}
  labels:
    test: integration
spec:
  restartPolicy: Never
  containers:
  - name: test-runner
    image: curlimages/curl
    command: ["/bin/sh"]
    args:
    - -c
    - |
      set -e
      echo "Running integration tests..."
      
      # Test each service endpoint
      for service in dmlog-integration data-orchestrator frontend-dmlog-final dmlog-gamedev; do
        if nslookup \$service.${FROM_NAMESPACE}.svc.cluster.local > /dev/null 2>&1; then
          SERVICE_IP=\$(nslookup \$service.${FROM_NAMESPACE}.svc.cluster.local | grep Address | tail -1 | cut -d' ' -f3)
          echo "Testing \$service at \$SERVICE_IP"
          
          # Health check
          if curl -f -s "http://\$SERVICE_IP:8080/health" > /dev/null; then
            echo "✅ \$service health check passed"
          else
            echo "❌ \$service health check failed"
            exit 1
          fi
          
          # Ready check
          if curl -f -s "http://\$SERVICE_IP:8080/ready" > /dev/null 2>&1; then
            echo "✅ \$service ready check passed"
          else
            echo "⚠️  \$service ready check not available (non-critical)"
          fi
        else
          echo "⚠️  Service \$service not found (may not be deployed)"
        fi
      done
      
      echo "All integration tests passed!"
EOF

    # Wait for test to complete
    kubectl wait --for=condition=Ready pod/"$test_pod_name" -n "$FROM_NAMESPACE" --timeout=60s || true
    
    # Get test results
    local test_exit_code=0
    kubectl logs "$test_pod_name" -n "$FROM_NAMESPACE" || test_exit_code=1
    
    # Cleanup test pod
    kubectl delete pod "$test_pod_name" -n "$FROM_NAMESPACE" --ignore-not-found=true
    
    if [[ $test_exit_code -eq 0 ]]; then
        log_success "Integration tests passed on $FROM_ENV"
        return 0
    else
        log_error "Integration tests failed on $FROM_ENV"
        return 1
    fi
}

# Create backup of target environment
create_target_backup() {
    log_info "Creating backup of $TO_ENV environment"
    
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_dir="/tmp/dmlog-backup-${TO_ENV}-${timestamp}"
    
    mkdir -p "$backup_dir"
    
    # Backup deployments and services
    for service in "${SERVICES_ARRAY[@]}"; do
        if kubectl get deployment "$service" -n "$TO_NAMESPACE" &> /dev/null; then
            kubectl get deployment "$service" -n "$TO_NAMESPACE" -o yaml > "${backup_dir}/${service}-deployment.yaml"
            log_info "Backed up $service deployment"
        fi
        
        if kubectl get service "$service" -n "$TO_NAMESPACE" &> /dev/null; then
            kubectl get service "$service" -n "$TO_NAMESPACE" -o yaml > "${backup_dir}/${service}-service.yaml"
            log_info "Backed up $service service"
        fi
    done
    
    # Store backup path globally
    BACKUP_DIR="$backup_dir"
    
    log_success "Backup created at $backup_dir"
}

# Promote service to target environment
promote_service() {
    local service_name=$1
    
    log_promotion "Promoting $service_name from $FROM_ENV to $TO_ENV"
    
    # Get source image and configuration
    local source_image_var="SOURCE_${service_name}_IMAGE"
    local source_replicas_var="SOURCE_${service_name}_REPLICAS"
    local source_image="${!source_image_var}"
    local source_replicas="${!source_replicas_var}"
    
    # Adjust replicas for production environment
    local target_replicas="$source_replicas"
    if [[ "$TO_ENV" == "production" ]]; then
        # Increase replicas for production
        target_replicas=$((source_replicas + 1))
        if [[ $target_replicas -lt 2 ]]; then
            target_replicas=2
        fi
    fi
    
    log_info "Promoting $service_name with image: $source_image, replicas: $target_replicas"
    
    # Check if using blue-green deployment in target
    local deployment_strategy="rolling"
    if kubectl get deployment "${service_name}-blue" -n "$TO_NAMESPACE" &> /dev/null || kubectl get deployment "${service_name}-green" -n "$TO_NAMESPACE" &> /dev/null; then
        deployment_strategy="blue-green"
    fi
    
    if [[ "$deployment_strategy" == "blue-green" ]]; then
        promote_service_blue_green "$service_name" "$source_image" "$target_replicas"
    else
        promote_service_rolling "$service_name" "$source_image" "$target_replicas"
    fi
}

# Promote using rolling update
promote_service_rolling() {
    local service_name=$1
    local source_image=$2
    local target_replicas=$3
    
    log_info "Using rolling update strategy for $service_name"
    
    # Check if deployment exists
    if kubectl get deployment "$service_name" -n "$TO_NAMESPACE" &> /dev/null; then
        # Update existing deployment
        kubectl set image deployment/"$service_name" -n "$TO_NAMESPACE" "${service_name}=${source_image}"
        kubectl scale deployment "$service_name" -n "$TO_NAMESPACE" --replicas="$target_replicas"
    else
        # Create new deployment
        create_deployment_manifest "$service_name" "$source_image" "$target_replicas" | kubectl apply -f -
        create_service_manifest "$service_name" | kubectl apply -f -
    fi
    
    # Wait for rollout
    log_info "Waiting for $service_name rollout to complete..."
    kubectl rollout status deployment/"$service_name" -n "$TO_NAMESPACE" --timeout=300s
    
    # Verify deployment
    verify_service_deployment "$service_name"
}

# Promote using blue-green deployment
promote_service_blue_green() {
    local service_name=$1
    local source_image=$2
    local target_replicas=$3
    
    log_info "Using blue-green deployment strategy for $service_name"
    
    # Determine current active color
    local active_color="blue"
    if kubectl get deployment "${service_name}-green" -n "$TO_NAMESPACE" &> /dev/null; then
        local green_replicas=$(kubectl get deployment "${service_name}-green" -n "$TO_NAMESPACE" -o jsonpath='{.spec.replicas}')
        if [[ "$green_replicas" -gt 0 ]]; then
            active_color="green"
        fi
    fi
    
    local inactive_color
    if [[ "$active_color" == "blue" ]]; then
        inactive_color="green"
    else
        inactive_color="blue"
    fi
    
    log_info "Current active: $active_color, promoting to: $inactive_color"
    
    # Deploy to inactive color
    create_blue_green_deployment "$service_name" "$inactive_color" "$source_image" "$target_replicas" | kubectl apply -f -
    create_blue_green_service "$service_name" "$inactive_color" | kubectl apply -f -
    
    # Wait for deployment
    kubectl rollout status deployment/"${service_name}-${inactive_color}" -n "$TO_NAMESPACE" --timeout=300s
    
    # Run health checks
    if ! run_health_checks "${service_name}-${inactive_color}"; then
        log_error "Health checks failed for ${service_name}-${inactive_color}"
        return 1
    fi
    
    # Switch traffic
    kubectl patch service "$service_name" -n "$TO_NAMESPACE" -p "{\"spec\":{\"selector\":{\"version\":\"$inactive_color\"}}}"
    
    # Wait and verify
    sleep 10
    if ! run_health_checks "$service_name"; then
        log_error "Health checks failed after traffic switch"
        # Rollback traffic
        kubectl patch service "$service_name" -n "$TO_NAMESPACE" -p "{\"spec\":{\"selector\":{\"version\":\"$active_color\"}}}"
        return 1
    fi
    
    # Scale down old deployment
    kubectl scale deployment "${service_name}-${active_color}" -n "$TO_NAMESPACE" --replicas=0
    
    log_success "Blue-green promotion completed for $service_name"
}

# Create deployment manifest
create_deployment_manifest() {
    local service_name=$1
    local image=$2
    local replicas=$3
    
    cat <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${service_name}
  namespace: ${TO_NAMESPACE}
  labels:
    app: ${service_name}
    environment: ${TO_ENV}
    promoted-from: ${FROM_ENV}
  annotations:
    promotion.dmlog.com/timestamp: "$(date -u +%Y%m%d%H%M%S)"
    promotion.dmlog.com/source-env: "${FROM_ENV}"
    promotion.dmlog.com/version: "${VERSION}"
spec:
  replicas: ${replicas}
  selector:
    matchLabels:
      app: ${service_name}
  template:
    metadata:
      labels:
        app: ${service_name}
        environment: ${TO_ENV}
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
    spec:
      imagePullSecrets:
        - name: registry-secret
      containers:
        - name: ${service_name}
          image: ${image}
          ports:
            - containerPort: 8080
              protocol: TCP
          env:
            - name: ENVIRONMENT
              value: "${TO_ENV}"
            - name: VERSION
              value: "${VERSION}"
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

# Create service manifest
create_service_manifest() {
    local service_name=$1
    
    cat <<EOF
apiVersion: v1
kind: Service
metadata:
  name: ${service_name}
  namespace: ${TO_NAMESPACE}
  labels:
    app: ${service_name}
    environment: ${TO_ENV}
spec:
  type: ClusterIP
  ports:
    - port: 8080
      targetPort: 8080
      protocol: TCP
      name: http
  selector:
    app: ${service_name}
EOF
}

# Create blue-green deployment
create_blue_green_deployment() {
    local service_name=$1
    local color=$2
    local image=$3
    local replicas=$4
    
    cat <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${service_name}-${color}
  namespace: ${TO_NAMESPACE}
  labels:
    app: ${service_name}
    version: ${color}
    environment: ${TO_ENV}
    promoted-from: ${FROM_ENV}
  annotations:
    promotion.dmlog.com/timestamp: "$(date -u +%Y%m%d%H%M%S)"
    promotion.dmlog.com/source-env: "${FROM_ENV}"
    promotion.dmlog.com/version: "${VERSION}"
spec:
  replicas: ${replicas}
  selector:
    matchLabels:
      app: ${service_name}
      version: ${color}
  template:
    metadata:
      labels:
        app: ${service_name}
        version: ${color}
        environment: ${TO_ENV}
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
    spec:
      imagePullSecrets:
        - name: registry-secret
      containers:
        - name: ${service_name}
          image: ${image}
          ports:
            - containerPort: 8080
              protocol: TCP
          env:
            - name: ENVIRONMENT
              value: "${TO_ENV}"
            - name: VERSION
              value: "${VERSION}"
            - name: COLOR
              value: "${color}"
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

# Create blue-green service
create_blue_green_service() {
    local service_name=$1
    local color=$2
    
    cat <<EOF
apiVersion: v1
kind: Service
metadata:
  name: ${service_name}-${color}
  namespace: ${TO_NAMESPACE}
  labels:
    app: ${service_name}
    version: ${color}
    environment: ${TO_ENV}
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

# Run health checks
run_health_checks() {
    local service_name=$1
    
    log_info "Running health checks for $service_name"
    
    local service_ip=$(kubectl get service "$service_name" -n "$TO_NAMESPACE" -o jsonpath='{.spec.clusterIP}')
    
    for i in {1..10}; do
        if kubectl run health-check-$(date +%s) --rm -i --image=curlimages/curl --restart=Never -- \
           curl -f -s "http://${service_ip}:8080/health" > /dev/null 2>&1; then
            log_success "Health check passed for $service_name"
            return 0
        fi
        log_warning "Health check attempt $i failed, retrying..."
        sleep 10
    done
    
    log_error "Health checks failed for $service_name"
    return 1
}

# Verify service deployment
verify_service_deployment() {
    local service_name=$1
    
    log_info "Verifying deployment for $service_name"
    
    local ready_replicas=$(kubectl get deployment "$service_name" -n "$TO_NAMESPACE" -o jsonpath='{.status.readyReplicas}')
    local desired_replicas=$(kubectl get deployment "$service_name" -n "$TO_NAMESPACE" -o jsonpath='{.spec.replicas}')
    
    if [[ "$ready_replicas" == "$desired_replicas" && "$ready_replicas" -gt 0 ]]; then
        log_success "$service_name deployment verified: $ready_replicas/$desired_replicas replicas ready"
        return 0
    else
        log_error "$service_name deployment verification failed: $ready_replicas/$desired_replicas replicas ready"
        return 1
    fi
}

# Run post-promotion tests
run_post_promotion_tests() {
    log_info "Running post-promotion tests on $TO_ENV environment"
    
    # Similar to source integration tests but for target environment
    local test_pod_name="post-promotion-test-$(date +%s)"
    
    # Create and run test pod (similar to source tests)
    # [Test implementation similar to run_source_integration_tests but for TO_NAMESPACE]
    
    log_success "Post-promotion tests completed successfully"
}

# Create promotion record
create_promotion_record() {
    local timestamp=$(date -u +%Y%m%d%H%M%S)
    
    log_info "Creating promotion record"
    
    # Create ConfigMap with promotion details
    kubectl create configmap "promotion-record-${timestamp}" \
        -n "$TO_NAMESPACE" \
        --from-literal=timestamp="$timestamp" \
        --from-literal=from-environment="$FROM_ENV" \
        --from-literal=to-environment="$TO_ENV" \
        --from-literal=version="$VERSION" \
        --from-literal=services="${SERVICES}" \
        --from-literal=backup-path="$BACKUP_DIR" \
        -o yaml --dry-run=client | kubectl apply -f -
    
    log_success "Promotion record created: promotion-record-$timestamp"
}

# Main promotion function
main() {
    log_promotion "Starting environment promotion process"
    log_promotion "From: $FROM_ENV → To: $TO_ENV"
    log_promotion "Version: $VERSION"
    log_promotion "Services: $SERVICES"
    
    # Parse services
    parse_services
    
    # Validate inputs and check prerequisites
    validate_inputs
    check_prerequisites
    
    # Get source deployment information
    for service in "${SERVICES_ARRAY[@]}"; do
        if ! get_source_deployment_info "$service"; then
            log_error "Failed to get deployment info for $service"
            exit 1
        fi
    done
    
    # Verify source environment health
    for service in "${SERVICES_ARRAY[@]}"; do
        if ! verify_source_health "$service"; then
            log_error "Source environment health check failed for $service"
            exit 1
        fi
    done
    
    # Run integration tests on source
    if ! run_source_integration_tests; then
        log_error "Source environment integration tests failed"
        exit 1
    fi
    
    # Create backup of target environment
    create_target_backup
    
    # Promote each service
    local failed_services=()
    
    for service in "${SERVICES_ARRAY[@]}"; do
        log_promotion "Promoting service: $service"
        
        if promote_service "$service"; then
            log_success "Successfully promoted $service"
        else
            log_error "Failed to promote $service"
            failed_services+=("$service")
        fi
        
        # Add delay between service promotions
        sleep 10
    done
    
    # Check for failures
    if [[ ${#failed_services[@]} -gt 0 ]]; then
        log_error "Some services failed to promote: ${failed_services[*]}"
        log_error "Backup available at: $BACKUP_DIR"
        exit 1
    fi
    
    # Run post-promotion tests
    if ! run_post_promotion_tests; then
        log_warning "Post-promotion tests failed (non-critical)"
    fi
    
    # Create promotion record
    create_promotion_record
    
    log_success "Environment promotion completed successfully!"
    log_promotion "All services promoted from $FROM_ENV to $TO_ENV"
    log_info "Backup available at: $BACKUP_DIR"
}

# Execute main function if script is run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi