#!/bin/bash

# ActiveLog Production Rollback Script
# Supports both Kubernetes and Docker Compose rollbacks

set -euo pipefail

# Configuration
NAMESPACE="${NAMESPACE:-activelog}"
CONTEXT="${CONTEXT:-production}"
ROLLBACK_TYPE="${ROLLBACK_TYPE:-deployment}"  # deployment, service-mesh, full
DRY_RUN="${DRY_RUN:-false}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check if running in dry-run mode
check_dry_run() {
    if [[ "$DRY_RUN" == "true" ]]; then
        log_warn "Running in DRY-RUN mode - no actual changes will be made"
        return 0
    fi
    return 1
}

# Validate prerequisites
validate_prerequisites() {
    log_info "Validating prerequisites..."
    
    # Check required tools
    local required_tools=("kubectl" "docker" "jq" "curl")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "Required tool not found: $tool"
            exit 1
        fi
    done
    
    # Check Kubernetes connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Unable to connect to Kubernetes cluster"
        exit 1
    fi
    
    # Check namespace exists
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_error "Namespace '$NAMESPACE' does not exist"
        exit 1
    fi
    
    log_success "Prerequisites validated"
}

# Get current deployment information
get_current_deployment_info() {
    log_info "Gathering current deployment information..."
    
    # Get current active environment (blue/green)
    CURRENT_ENV=$(kubectl get service api-gateway -n "$NAMESPACE" -o jsonpath='{.metadata.labels.environment}' 2>/dev/null || echo "blue")
    
    # Get deployment revisions
    DEPLOYMENTS=$(kubectl get deployments -n "$NAMESPACE" -o name | cut -d'/' -f2)
    
    # Store current state
    mkdir -p "/tmp/activelog-rollback-$(date +%Y%m%d-%H%M%S)"
    ROLLBACK_DIR="/tmp/activelog-rollback-$(date +%Y%m%d-%H%M%S)"
    
    log_info "Current environment: $CURRENT_ENV"
    log_info "Rollback directory: $ROLLBACK_DIR"
    
    # Backup current state
    kubectl get all,ingress,configmap,secret -n "$NAMESPACE" -o yaml > "$ROLLBACK_DIR/current-state.yaml"
    
    export CURRENT_ENV ROLLBACK_DIR DEPLOYMENTS
}

# List available rollback targets
list_rollback_targets() {
    log_info "Available rollback targets:"
    
    echo "Deployment Revisions:"
    for deployment in $DEPLOYMENTS; do
        echo "  $deployment:"
        kubectl rollout history deployment/"$deployment" -n "$NAMESPACE" | tail -n +2 | sed 's/^/    /'
    done
    
    echo
    echo "Docker Images (last 10 tags):"
    # This would typically query your container registry
    echo "  Note: Query your container registry for available image tags"
    
    echo
    echo "Database Backups:"
    kubectl get pvc -n "$NAMESPACE" | grep backup || echo "  No backup PVCs found"
}

# Rollback deployments to previous revision
rollback_deployments() {
    local target_revision="${1:-}"
    
    log_info "Rolling back deployments..."
    
    if [[ -z "$target_revision" ]]; then
        # Rollback to previous revision
        for deployment in $DEPLOYMENTS; do
            log_info "Rolling back deployment: $deployment"
            
            if check_dry_run; then
                echo "DRY-RUN: kubectl rollout undo deployment/$deployment -n $NAMESPACE"
            else
                kubectl rollout undo deployment/"$deployment" -n "$NAMESPACE"
                
                # Wait for rollback to complete
                kubectl rollout status deployment/"$deployment" -n "$NAMESPACE" --timeout=300s
            fi
        done
    else
        # Rollback to specific revision
        for deployment in $DEPLOYMENTS; do
            log_info "Rolling back deployment $deployment to revision $target_revision"
            
            if check_dry_run; then
                echo "DRY-RUN: kubectl rollout undo deployment/$deployment --to-revision=$target_revision -n $NAMESPACE"
            else
                kubectl rollout undo deployment/"$deployment" --to-revision="$target_revision" -n "$NAMESPACE"
                kubectl rollout status deployment/"$deployment" -n "$NAMESPACE" --timeout=300s
            fi
        done
    fi
    
    log_success "Deployment rollback completed"
}

# Rollback service mesh configuration
rollback_service_mesh() {
    log_info "Rolling back service mesh configuration..."
    
    # Get previous Istio configuration
    local istio_backup_file="$ROLLBACK_DIR/istio-config-backup.yaml"
    
    if [[ -f "$istio_backup_file" ]]; then
        if check_dry_run; then
            echo "DRY-RUN: kubectl apply -f $istio_backup_file"
        else
            kubectl apply -f "$istio_backup_file"
        fi
        log_success "Service mesh rollback completed"
    else
        log_warn "No service mesh backup found, skipping"
    fi
}

# Rollback database to previous backup
rollback_database() {
    local backup_name="${1:-latest}"
    
    log_info "Rolling back database to backup: $backup_name"
    
    # Find database backup
    local backup_job_name="postgres-restore-$(date +%s)"
    
    if check_dry_run; then
        echo "DRY-RUN: Would restore database from backup $backup_name"
        return
    fi
    
    # Create restore job
    cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: $backup_job_name
  namespace: $NAMESPACE
spec:
  template:
    spec:
      containers:
      - name: postgres-restore
        image: postgres:15-alpine
        command:
        - sh
        - -c
        - |
          echo "Finding backup file..."
          BACKUP_FILE=\$(find /backup -name "*$backup_name*.sql" | head -1)
          if [[ -z "\$BACKUP_FILE" ]]; then
            echo "No backup file found for: $backup_name"
            exit 1
          fi
          
          echo "Restoring from: \$BACKUP_FILE"
          
          # Drop and recreate database
          PGPASSWORD=\$POSTGRES_PASSWORD dropdb -h postgres -U postgres activelog --if-exists
          PGPASSWORD=\$POSTGRES_PASSWORD createdb -h postgres -U postgres activelog
          
          # Restore backup
          PGPASSWORD=\$POSTGRES_PASSWORD psql -h postgres -U postgres -d activelog < \$BACKUP_FILE
          
          echo "Database restore completed"
        env:
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: password
        volumeMounts:
        - name: backup-storage
          mountPath: /backup
      volumes:
      - name: backup-storage
        persistentVolumeClaim:
          claimName: postgres-backup
      restartPolicy: OnFailure
  backoffLimit: 3
EOF
    
    # Wait for restore to complete
    kubectl wait --for=condition=complete job/"$backup_job_name" -n "$NAMESPACE" --timeout=600s
    
    # Check if restore was successful
    if kubectl get job "$backup_job_name" -n "$NAMESPACE" -o jsonpath='{.status.conditions[?(@.type=="Complete")].status}' | grep -q "True"; then
        log_success "Database rollback completed"
        kubectl delete job "$backup_job_name" -n "$NAMESPACE"
    else
        log_error "Database rollback failed"
        kubectl logs job/"$backup_job_name" -n "$NAMESPACE"
        exit 1
    fi
}

# Switch traffic between blue/green environments
switch_traffic() {
    local target_env="${1:-}"
    
    if [[ -z "$target_env" ]]; then
        # Determine opposite environment
        target_env=$([ "$CURRENT_ENV" = "blue" ] && echo "green" || echo "blue")
    fi
    
    log_info "Switching traffic from $CURRENT_ENV to $target_env environment"
    
    if check_dry_run; then
        echo "DRY-RUN: Would switch traffic to $target_env environment"
        return
    fi
    
    # Update service selectors
    kubectl patch service api-gateway -n "$NAMESPACE" -p "{\"spec\":{\"selector\":{\"environment\":\"$target_env\"}}}"
    
    # Update Istio VirtualService if exists
    if kubectl get virtualservice activelog-vs -n "$NAMESPACE" &>/dev/null; then
        kubectl patch virtualservice activelog-vs -n "$NAMESPACE" --type='merge' -p="
        {
          \"spec\": {
            \"http\": [
              {
                \"match\": [{\"uri\": {\"prefix\": \"/\"}}],
                \"route\": [{
                  \"destination\": {
                    \"host\": \"api-gateway\"
                  },
                  \"weight\": 100
                }]
              }
            ]
          }
        }"
    fi
    
    log_success "Traffic switched to $target_env environment"
}

# Verify rollback success
verify_rollback() {
    log_info "Verifying rollback success..."
    
    # Check all deployments are ready
    local ready_deployments=0
    local total_deployments=$(echo "$DEPLOYMENTS" | wc -w)
    
    for deployment in $DEPLOYMENTS; do
        if kubectl get deployment "$deployment" -n "$NAMESPACE" -o jsonpath='{.status.conditions[?(@.type=="Available")].status}' | grep -q "True"; then
            ((ready_deployments++))
        fi
    done
    
    if [[ $ready_deployments -eq $total_deployments ]]; then
        log_success "All deployments are ready ($ready_deployments/$total_deployments)"
    else
        log_error "Some deployments are not ready ($ready_deployments/$total_deployments)"
        return 1
    fi
    
    # Test API endpoints
    local api_endpoint
    if kubectl get service api-gateway -n "$NAMESPACE" &>/dev/null; then
        # Try to get external IP
        api_endpoint=$(kubectl get service api-gateway -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
        
        if [[ -z "$api_endpoint" ]]; then
            # Use port-forward for testing
            log_info "Using port-forward for testing..."
            kubectl port-forward service/api-gateway 18000:8000 -n "$NAMESPACE" &
            local port_forward_pid=$!
            sleep 5
            api_endpoint="localhost:18000"
        fi
        
        # Test health endpoint
        if curl -f -s "http://$api_endpoint/health" >/dev/null; then
            log_success "Health endpoint is responding"
        else
            log_error "Health endpoint is not responding"
            return 1
        fi
        
        # Clean up port-forward if used
        if [[ -n "${port_forward_pid:-}" ]]; then
            kill $port_forward_pid 2>/dev/null || true
        fi
    fi
    
    log_success "Rollback verification completed successfully"
}

# Send notifications
send_notifications() {
    local status="$1"
    local message="$2"
    
    # Slack notification
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        local color="good"
        local emoji="✅"
        
        if [[ "$status" == "error" ]]; then
            color="danger"
            emoji="🚨"
        elif [[ "$status" == "warning" ]]; then
            color="warning"
            emoji="⚠️"
        fi
        
        curl -X POST -H 'Content-type: application/json' \
            --data "{
                \"attachments\": [{
                    \"color\": \"$color\",
                    \"text\": \"$emoji ActiveLog Rollback: $message\",
                    \"fields\": [
                        {\"title\": \"Environment\", \"value\": \"$CURRENT_ENV\", \"short\": true},
                        {\"title\": \"Namespace\", \"value\": \"$NAMESPACE\", \"short\": true},
                        {\"title\": \"Timestamp\", \"value\": \"$(date -u)\", \"short\": false}
                    ]
                }]
            }" \
            "$SLACK_WEBHOOK_URL" || true
    fi
    
    # Email notification (if configured)
    if [[ -n "${EMAIL_RECIPIENTS:-}" ]] && command -v mail &>/dev/null; then
        echo "$message" | mail -s "ActiveLog Rollback - $status" "$EMAIL_RECIPIENTS" || true
    fi
}

# Cleanup old rollback data
cleanup_old_rollbacks() {
    log_info "Cleaning up old rollback data..."
    
    # Clean up old rollback directories
    find /tmp -maxdepth 1 -name "activelog-rollback-*" -type d -mtime +7 -exec rm -rf {} \; 2>/dev/null || true
    
    # Clean up completed jobs older than retention period
    kubectl get jobs -n "$NAMESPACE" -o go-template='{{range .items}}{{if and (eq .status.conditions[0].type "Complete") (lt .status.completionTime "'"$(date -d "${BACKUP_RETENTION_DAYS} days ago" -u +%Y-%m-%dT%H:%M:%SZ)"'")}}{{.metadata.name}}{{"\n"}}{{end}}{{end}}' | \
        xargs -r kubectl delete job -n "$NAMESPACE" || true
    
    log_success "Cleanup completed"
}

# Main rollback function
perform_rollback() {
    local rollback_target="${1:-previous}"
    
    log_info "Starting ActiveLog rollback process..."
    log_info "Rollback type: $ROLLBACK_TYPE"
    log_info "Target: $rollback_target"
    
    case "$ROLLBACK_TYPE" in
        "deployment")
            rollback_deployments "$rollback_target"
            ;;
        "service-mesh")
            rollback_service_mesh
            ;;
        "database")
            rollback_database "$rollback_target"
            ;;
        "traffic")
            switch_traffic "$rollback_target"
            ;;
        "full")
            rollback_deployments "$rollback_target"
            rollback_service_mesh
            switch_traffic
            ;;
        *)
            log_error "Unknown rollback type: $ROLLBACK_TYPE"
            exit 1
            ;;
    esac
    
    # Verify rollback
    if verify_rollback; then
        send_notifications "success" "Rollback completed successfully"
        log_success "Rollback completed successfully!"
    else
        send_notifications "error" "Rollback verification failed"
        log_error "Rollback verification failed!"
        exit 1
    fi
}

# Usage information
usage() {
    cat << EOF
ActiveLog Production Rollback Script

Usage: $0 [OPTIONS] [TARGET]

OPTIONS:
    -t, --type TYPE          Rollback type (deployment|service-mesh|database|traffic|full) [default: deployment]
    -n, --namespace NAME     Kubernetes namespace [default: activelog]
    -c, --context CONTEXT    Kubernetes context [default: production]
    -d, --dry-run            Show what would be done without making changes
    -l, --list               List available rollback targets
    -h, --help               Show this help message

TARGETS:
    previous                 Rollback to previous version (default)
    REVISION_NUMBER         Rollback to specific revision
    IMAGE_TAG               Rollback to specific image tag
    BACKUP_NAME             Rollback to specific backup (for database)

EXAMPLES:
    $0                              # Rollback deployments to previous version
    $0 --type full                  # Full rollback (deployments + service-mesh + traffic)
    $0 --type database backup-001   # Rollback database to specific backup
    $0 --dry-run                    # Show what would be done
    $0 --list                       # List available rollback targets

ENVIRONMENT VARIABLES:
    SLACK_WEBHOOK_URL       Slack webhook for notifications
    EMAIL_RECIPIENTS        Email addresses for notifications
    BACKUP_RETENTION_DAYS   Days to keep rollback data [default: 30]

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            ROLLBACK_TYPE="$2"
            shift 2
            ;;
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -c|--context)
            CONTEXT="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN="true"
            shift
            ;;
        -l|--list)
            validate_prerequisites
            get_current_deployment_info
            list_rollback_targets
            exit 0
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        -*)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
        *)
            ROLLBACK_TARGET="$1"
            shift
            ;;
    esac
done

# Set kubectl context
kubectl config use-context "$CONTEXT"

# Main execution
main() {
    validate_prerequisites
    get_current_deployment_info
    perform_rollback "${ROLLBACK_TARGET:-previous}"
    cleanup_old_rollbacks
}

# Execute main function
main "$@"