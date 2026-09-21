#!/bin/bash

# Secrets Management Setup Script for DMLog
# Usage: ./setup-secrets.sh <environment> [action]

set -euo pipefail

ENVIRONMENT=${1:-staging}
ACTION=${2:-setup}
NAMESPACE="dmlog-${ENVIRONMENT}"

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

log_secrets() {
    echo -e "${PURPLE}[SECRETS]${NC} $1"
}

# Validate inputs
validate_inputs() {
    if [[ ! "$ENVIRONMENT" =~ ^(staging|production)$ ]]; then
        log_error "Environment must be 'staging' or 'production'"
        exit 1
    fi
    
    if [[ ! "$ACTION" =~ ^(setup|update|rotate|verify|cleanup)$ ]]; then
        log_error "Action must be 'setup', 'update', 'rotate', 'verify', or 'cleanup'"
        exit 1
    fi
    
    log_info "Secrets management parameters validated"
    log_secrets "Environment: $ENVIRONMENT"
    log_secrets "Action: $ACTION"
}

# Check prerequisites
check_prerequisites() {
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed"
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
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Generate secure password
generate_password() {
    local length=${1:-32}
    openssl rand -base64 $length | tr -d "=+/" | cut -c1-$length
}

# Generate JWT secret
generate_jwt_secret() {
    openssl rand -base64 64 | tr -d "=+/" | cut -c1-64
}

# Create AWS Secrets Manager secrets
create_aws_secrets() {
    log_secrets "Creating AWS Secrets Manager secrets for $ENVIRONMENT"
    
    local aws_region="us-west-2"
    
    # Database credentials
    local db_password=$(generate_password 16)
    local db_secret_name="dmlog/${ENVIRONMENT}/database"
    
    # Check if secret exists
    if aws secretsmanager describe-secret --secret-id "$db_secret_name" --region "$aws_region" &> /dev/null; then
        log_warning "Database secret already exists, skipping creation"
    else
        local db_secret_value=$(cat <<EOF
{
  "username": "dmlog_admin",
  "password": "$db_password",
  "engine": "postgres",
  "host": "dmlog-${ENVIRONMENT}-db.cluster-xxx.${aws_region}.rds.amazonaws.com",
  "port": 5432,
  "dbname": "dmlog",
  "url": "postgresql://dmlog_admin:$db_password@dmlog-${ENVIRONMENT}-db.cluster-xxx.${aws_region}.rds.amazonaws.com:5432/dmlog"
}
EOF
)
        
        aws secretsmanager create-secret \
            --name "$db_secret_name" \
            --description "Database credentials for DMLog $ENVIRONMENT" \
            --secret-string "$db_secret_value" \
            --region "$aws_region"
        
        log_success "Created database secret: $db_secret_name"
    fi
    
    # Redis credentials
    local redis_auth_token=$(generate_password 32)
    local redis_secret_name="dmlog/${ENVIRONMENT}/redis"
    
    if aws secretsmanager describe-secret --secret-id "$redis_secret_name" --region "$aws_region" &> /dev/null; then
        log_warning "Redis secret already exists, skipping creation"
    else
        local redis_secret_value=$(cat <<EOF
{
  "host": "dmlog-${ENVIRONMENT}-cache.xxx.${aws_region}.cache.amazonaws.com",
  "port": 6379,
  "auth_token": "$redis_auth_token",
  "url": "redis://default:$redis_auth_token@dmlog-${ENVIRONMENT}-cache.xxx.${aws_region}.cache.amazonaws.com:6379"
}
EOF
)
        
        aws secretsmanager create-secret \
            --name "$redis_secret_name" \
            --description "Redis credentials for DMLog $ENVIRONMENT" \
            --secret-string "$redis_secret_value" \
            --region "$aws_region"
        
        log_success "Created Redis secret: $redis_secret_name"
    fi
    
    # JWT secrets
    local jwt_secret=$(generate_jwt_secret)
    local jwt_secret_name="dmlog/${ENVIRONMENT}/jwt"
    
    if aws secretsmanager describe-secret --secret-id "$jwt_secret_name" --region "$aws_region" &> /dev/null; then
        log_warning "JWT secret already exists, skipping creation"
    else
        local jwt_secret_value=$(cat <<EOF
{
  "secret": "$jwt_secret",
  "algorithm": "HS256",
  "expires_in": "24h"
}
EOF
)
        
        aws secretsmanager create-secret \
            --name "$jwt_secret_name" \
            --description "JWT secrets for DMLog $ENVIRONMENT" \
            --secret-string "$jwt_secret_value" \
            --region "$aws_region"
        
        log_success "Created JWT secret: $jwt_secret_name"
    fi
    
    # API Keys
    local api_key=$(generate_password 32)
    local api_secret_name="dmlog/${ENVIRONMENT}/api-keys"
    
    if aws secretsmanager describe-secret --secret-id "$api_secret_name" --region "$aws_region" &> /dev/null; then
        log_warning "API keys secret already exists, skipping creation"
    else
        local api_secret_value=$(cat <<EOF
{
  "internal_api_key": "$api_key",
  "webhook_secret": "$(generate_password 32)",
  "encryption_key": "$(generate_password 32)"
}
EOF
)
        
        aws secretsmanager create-secret \
            --name "$api_secret_name" \
            --description "API keys for DMLog $ENVIRONMENT" \
            --secret-string "$api_secret_value" \
            --region "$aws_region"
        
        log_success "Created API keys secret: $api_secret_name"
    fi
}

# Install External Secrets Operator
install_external_secrets_operator() {
    log_secrets "Installing External Secrets Operator"
    
    # Check if already installed
    if kubectl get namespace external-secrets &> /dev/null; then
        log_warning "External Secrets Operator already installed"
        return 0
    fi
    
    # Add helm repo
    if command -v helm &> /dev/null; then
        helm repo add external-secrets https://charts.external-secrets.io
        helm repo update
        
        # Install External Secrets Operator
        helm install external-secrets external-secrets/external-secrets \
            --namespace external-secrets \
            --create-namespace \
            --set installCRDs=true
        
        # Wait for deployment
        kubectl wait --for=condition=available --timeout=300s \
            deployment/external-secrets -n external-secrets
        
        log_success "External Secrets Operator installed successfully"
    else
        log_error "Helm is required to install External Secrets Operator"
        exit 1
    fi
}

# Create SecretStore for AWS Secrets Manager
create_secret_store() {
    log_secrets "Creating SecretStore for AWS Secrets Manager"
    
    local aws_region="us-west-2"
    local service_account_name="external-secrets"
    
    # Create service account with IAM role annotation
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ${service_account_name}
  namespace: external-secrets
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/dmlog-${ENVIRONMENT}-external-secrets-role
---
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secrets-manager
  namespace: ${NAMESPACE}
spec:
  provider:
    aws:
      service: SecretsManager
      region: ${aws_region}
      auth:
        serviceAccount:
          serviceAccountRef:
            name: ${service_account_name}
            namespace: external-secrets
EOF
    
    log_success "SecretStore created successfully"
}

# Create ExternalSecret resources
create_external_secrets() {
    log_secrets "Creating ExternalSecret resources"
    
    # Database external secret
    cat <<EOF | kubectl apply -f -
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: dmlog-database
  namespace: ${NAMESPACE}
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: dmlog-database
    creationPolicy: Owner
    template:
      type: Opaque
      data:
        DATABASE_URL: "{{ .url }}"
        DB_HOST: "{{ .host }}"
        DB_PORT: "{{ .port }}"
        DB_NAME: "{{ .dbname }}"
        DB_USER: "{{ .username }}"
        DB_PASSWORD: "{{ .password }}"
  data:
  - secretKey: url
    remoteRef:
      key: dmlog/${ENVIRONMENT}/database
      property: url
  - secretKey: host
    remoteRef:
      key: dmlog/${ENVIRONMENT}/database
      property: host
  - secretKey: port
    remoteRef:
      key: dmlog/${ENVIRONMENT}/database
      property: port
  - secretKey: dbname
    remoteRef:
      key: dmlog/${ENVIRONMENT}/database
      property: dbname
  - secretKey: username
    remoteRef:
      key: dmlog/${ENVIRONMENT}/database
      property: username
  - secretKey: password
    remoteRef:
      key: dmlog/${ENVIRONMENT}/database
      property: password
EOF
    
    # Redis external secret
    cat <<EOF | kubectl apply -f -
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: dmlog-redis
  namespace: ${NAMESPACE}
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: dmlog-redis
    creationPolicy: Owner
    template:
      type: Opaque
      data:
        REDIS_URL: "{{ .url }}"
        REDIS_HOST: "{{ .host }}"
        REDIS_PORT: "{{ .port }}"
        REDIS_AUTH_TOKEN: "{{ .auth_token }}"
  data:
  - secretKey: url
    remoteRef:
      key: dmlog/${ENVIRONMENT}/redis
      property: url
  - secretKey: host
    remoteRef:
      key: dmlog/${ENVIRONMENT}/redis
      property: host
  - secretKey: port
    remoteRef:
      key: dmlog/${ENVIRONMENT}/redis
      property: port
  - secretKey: auth_token
    remoteRef:
      key: dmlog/${ENVIRONMENT}/redis
      property: auth_token
EOF
    
    # JWT external secret
    cat <<EOF | kubectl apply -f -
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: dmlog-jwt
  namespace: ${NAMESPACE}
spec:
  refreshInterval: 24h
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: dmlog-jwt
    creationPolicy: Owner
    template:
      type: Opaque
      data:
        JWT_SECRET: "{{ .secret }}"
        JWT_ALGORITHM: "{{ .algorithm }}"
        JWT_EXPIRES_IN: "{{ .expires_in }}"
  data:
  - secretKey: secret
    remoteRef:
      key: dmlog/${ENVIRONMENT}/jwt
      property: secret
  - secretKey: algorithm
    remoteRef:
      key: dmlog/${ENVIRONMENT}/jwt
      property: algorithm
  - secretKey: expires_in
    remoteRef:
      key: dmlog/${ENVIRONMENT}/jwt
      property: expires_in
EOF
    
    # API Keys external secret
    cat <<EOF | kubectl apply -f -
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: dmlog-api-keys
  namespace: ${NAMESPACE}
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: dmlog-api-keys
    creationPolicy: Owner
    template:
      type: Opaque
      data:
        INTERNAL_API_KEY: "{{ .internal_api_key }}"
        WEBHOOK_SECRET: "{{ .webhook_secret }}"
        ENCRYPTION_KEY: "{{ .encryption_key }}"
  data:
  - secretKey: internal_api_key
    remoteRef:
      key: dmlog/${ENVIRONMENT}/api-keys
      property: internal_api_key
  - secretKey: webhook_secret
    remoteRef:
      key: dmlog/${ENVIRONMENT}/api-keys
      property: webhook_secret
  - secretKey: encryption_key
    remoteRef:
      key: dmlog/${ENVIRONMENT}/api-keys
      property: encryption_key
EOF
    
    log_success "ExternalSecret resources created successfully"
}

# Create container registry secret
create_registry_secret() {
    log_secrets "Creating container registry secret"
    
    # GitHub Container Registry secret
    if [[ -n "${GITHUB_TOKEN:-}" ]]; then
        kubectl create secret docker-registry registry-secret \
            --namespace="$NAMESPACE" \
            --docker-server=ghcr.io \
            --docker-username="$GITHUB_USERNAME" \
            --docker-password="$GITHUB_TOKEN" \
            --dry-run=client -o yaml | kubectl apply -f -
        
        log_success "GitHub Container Registry secret created"
    else
        log_warning "GITHUB_TOKEN not set, skipping registry secret creation"
    fi
}

# Rotate secrets
rotate_secrets() {
    log_secrets "Rotating secrets for $ENVIRONMENT"
    
    local aws_region="us-west-2"
    
    # Rotate JWT secret
    local new_jwt_secret=$(generate_jwt_secret)
    local jwt_secret_name="dmlog/${ENVIRONMENT}/jwt"
    
    local jwt_secret_value=$(cat <<EOF
{
  "secret": "$new_jwt_secret",
  "algorithm": "HS256",
  "expires_in": "24h"
}
EOF
)
    
    aws secretsmanager update-secret \
        --secret-id "$jwt_secret_name" \
        --secret-string "$jwt_secret_value" \
        --region "$aws_region"
    
    log_success "JWT secret rotated"
    
    # Rotate API keys
    local new_api_key=$(generate_password 32)
    local api_secret_name="dmlog/${ENVIRONMENT}/api-keys"
    
    local api_secret_value=$(cat <<EOF
{
  "internal_api_key": "$new_api_key",
  "webhook_secret": "$(generate_password 32)",
  "encryption_key": "$(generate_password 32)"
}
EOF
)
    
    aws secretsmanager update-secret \
        --secret-id "$api_secret_name" \
        --secret-string "$api_secret_value" \
        --region "$aws_region"
    
    log_success "API keys rotated"
    
    # Force refresh of ExternalSecrets
    kubectl annotate externalsecret dmlog-jwt -n "$NAMESPACE" \
        force-sync="$(date +%s)" --overwrite
    kubectl annotate externalsecret dmlog-api-keys -n "$NAMESPACE" \
        force-sync="$(date +%s)" --overwrite
    
    log_success "Secrets rotation completed"
}

# Verify secrets
verify_secrets() {
    log_secrets "Verifying secrets for $ENVIRONMENT"
    
    local secrets=("dmlog-database" "dmlog-redis" "dmlog-jwt" "dmlog-api-keys" "registry-secret")
    
    for secret in "${secrets[@]}"; do
        if kubectl get secret "$secret" -n "$NAMESPACE" &> /dev/null; then
            # Check if secret has data
            local data_count=$(kubectl get secret "$secret" -n "$NAMESPACE" -o jsonpath='{.data}' | jq 'length')
            if [[ "$data_count" -gt 0 ]]; then
                log_success "Secret $secret exists and has data ($data_count keys)"
            else
                log_error "Secret $secret exists but has no data"
            fi
        else
            log_error "Secret $secret not found"
        fi
    done
    
    # Verify ExternalSecrets status
    local external_secrets=("dmlog-database" "dmlog-redis" "dmlog-jwt" "dmlog-api-keys")
    
    for es in "${external_secrets[@]}"; do
        if kubectl get externalsecret "$es" -n "$NAMESPACE" &> /dev/null; then
            local status=$(kubectl get externalsecret "$es" -n "$NAMESPACE" -o jsonpath='{.status.conditions[0].status}')
            local reason=$(kubectl get externalsecret "$es" -n "$NAMESPACE" -o jsonpath='{.status.conditions[0].reason}')
            
            if [[ "$status" == "True" && "$reason" == "SecretSynced" ]]; then
                log_success "ExternalSecret $es is synced"
            else
                log_error "ExternalSecret $es status: $status, reason: $reason"
            fi
        else
            log_error "ExternalSecret $es not found"
        fi
    done
    
    log_success "Secrets verification completed"
}

# Cleanup secrets
cleanup_secrets() {
    log_secrets "Cleaning up secrets for $ENVIRONMENT"
    
    # Remove ExternalSecrets
    kubectl delete externalsecret --all -n "$NAMESPACE" || true
    
    # Remove SecretStore
    kubectl delete secretstore aws-secrets-manager -n "$NAMESPACE" || true
    
    # Remove Kubernetes secrets
    local secrets=("dmlog-database" "dmlog-redis" "dmlog-jwt" "dmlog-api-keys" "registry-secret")
    for secret in "${secrets[@]}"; do
        kubectl delete secret "$secret" -n "$NAMESPACE" --ignore-not-found=true
    done
    
    # Optionally remove AWS Secrets Manager secrets (commented out for safety)
    # local aws_region="us-west-2"
    # aws secretsmanager delete-secret --secret-id "dmlog/${ENVIRONMENT}/database" --region "$aws_region" || true
    # aws secretsmanager delete-secret --secret-id "dmlog/${ENVIRONMENT}/redis" --region "$aws_region" || true
    # aws secretsmanager delete-secret --secret-id "dmlog/${ENVIRONMENT}/jwt" --region "$aws_region" || true
    # aws secretsmanager delete-secret --secret-id "dmlog/${ENVIRONMENT}/api-keys" --region "$aws_region" || true
    
    log_warning "Cleanup completed (AWS Secrets Manager secrets preserved)"
}

# Main function
main() {
    log_secrets "Starting secrets management for $ENVIRONMENT"
    
    # Validate inputs and check prerequisites
    validate_inputs
    check_prerequisites
    
    case "$ACTION" in
        "setup")
            log_secrets "Setting up secrets management"
            create_aws_secrets
            install_external_secrets_operator
            create_secret_store
            create_external_secrets
            create_registry_secret
            
            # Wait for secrets to sync
            log_info "Waiting for secrets to sync..."
            sleep 30
            
            verify_secrets
            log_success "Secrets management setup completed!"
            ;;
        "update")
            log_secrets "Updating secrets"
            create_external_secrets
            create_registry_secret
            verify_secrets
            log_success "Secrets updated successfully!"
            ;;
        "rotate")
            log_secrets "Rotating secrets"
            rotate_secrets
            log_success "Secrets rotated successfully!"
            ;;
        "verify")
            log_secrets "Verifying secrets"
            verify_secrets
            ;;
        "cleanup")
            log_warning "This will remove all secrets management resources"
            read -p "Are you sure? (yes/no): " confirm
            if [[ "$confirm" == "yes" ]]; then
                cleanup_secrets
                log_success "Cleanup completed!"
            else
                log_info "Cleanup cancelled"
            fi
            ;;
    esac
    
    log_success "Secrets management operation completed successfully!"
}

# Execute main function if script is run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi