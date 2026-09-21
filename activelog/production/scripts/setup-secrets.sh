#!/bin/bash

# Production Secrets Setup Script for ActiveLog
# This script generates secure secrets and stores them in encrypted format

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_DIR="${SCRIPT_DIR}/../secrets"
BACKUP_DIR="${SCRIPT_DIR}/../backup/secrets"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Generate secure random string
generate_secret() {
    local length=${1:-32}
    openssl rand -base64 $length | tr -d "=+/" | cut -c1-$length
}

# Generate JWT secret (longer for security)
generate_jwt_secret() {
    openssl rand -base64 64 | tr -d "=+/" | cut -c1-64
}

# Generate database password
generate_db_password() {
    openssl rand -base64 32 | tr -d "=+/" | head -c 24
}

# Create encrypted secret file
create_secret_file() {
    local secret_name="$1"
    local secret_value="$2"
    local file_path="${SECRETS_DIR}/${secret_name}.txt"
    
    echo -n "$secret_value" > "$file_path"
    chmod 600 "$file_path"
    log "Created secret: $secret_name"
}

# Check if required tools are installed
check_dependencies() {
    log "Checking dependencies..."
    
    command -v openssl >/dev/null 2>&1 || error "openssl is required but not installed"
    command -v gpg >/dev/null 2>&1 || error "gpg is required but not installed"
    
    log "All dependencies satisfied"
}

# Create directories
setup_directories() {
    log "Setting up directories..."
    
    mkdir -p "$SECRETS_DIR"
    mkdir -p "$BACKUP_DIR"
    
    # Set secure permissions
    chmod 700 "$SECRETS_DIR"
    chmod 700 "$BACKUP_DIR"
    
    log "Directories created with secure permissions"
}

# Generate all secrets
generate_secrets() {
    log "Generating production secrets..."
    
    # Database secrets
    local db_name="activelog_prod"
    local db_user="activelog_admin"
    local db_password=$(generate_db_password)
    local db_url="postgresql://${db_user}:${db_password}@postgres:5432/${db_name}"
    
    create_secret_file "postgres_db" "$db_name"
    create_secret_file "postgres_user" "$db_user"
    create_secret_file "postgres_password" "$db_password"
    create_secret_file "database_url" "$db_url"
    
    # Redis secrets
    local redis_password=$(generate_secret 32)
    local redis_url="redis://:${redis_password}@redis-master:6379"
    
    create_secret_file "redis_password" "$redis_password"
    create_secret_file "redis_url" "$redis_url"
    
    # JWT secret
    local jwt_secret=$(generate_jwt_secret)
    create_secret_file "jwt_secret" "$jwt_secret"
    
    # Grafana secrets
    local grafana_admin_password=$(generate_secret 24)
    local grafana_db_name="grafana"
    local grafana_db_user="grafana"
    local grafana_db_password=$(generate_db_password)
    
    create_secret_file "grafana_admin_password" "$grafana_admin_password"
    create_secret_file "grafana_db_name" "$grafana_db_name"
    create_secret_file "grafana_db_user" "$grafana_db_user"
    create_secret_file "grafana_db_password" "$grafana_db_password"
    
    # Elasticsearch secret
    local elasticsearch_password=$(generate_secret 24)
    create_secret_file "elasticsearch_password" "$elasticsearch_password"
    
    # Placeholder files for external secrets (to be filled by ops team)
    create_secret_file "openai_api_key" "YOUR_OPENAI_API_KEY_HERE"
    create_secret_file "aws_access_key" "YOUR_AWS_ACCESS_KEY_HERE"
    create_secret_file "aws_secret_key" "YOUR_AWS_SECRET_KEY_HERE"
    create_secret_file "smtp_host" "smtp.your-domain.com"
    create_secret_file "smtp_user" "noreply@your-domain.com"
    create_secret_file "smtp_password" "YOUR_SMTP_PASSWORD_HERE"
    
    log "All secrets generated successfully"
}

# Create backup of secrets
backup_secrets() {
    log "Creating encrypted backup of secrets..."
    
    local backup_file="${BACKUP_DIR}/secrets_backup_$(date +%Y%m%d_%H%M%S).tar.gz.gpg"
    
    # Create encrypted backup
    tar -czf - -C "$SECRETS_DIR" . | gpg --symmetric --cipher-algo AES256 --output "$backup_file"
    
    chmod 600 "$backup_file"
    
    log "Encrypted backup created: $backup_file"
    warn "Store the backup passphrase securely!"
}

# Generate secrets rotation script
create_rotation_script() {
    log "Creating secrets rotation script..."
    
    cat > "${SCRIPT_DIR}/rotate-secrets.sh" << 'EOF'
#!/bin/bash

# Secrets Rotation Script for ActiveLog Production
# This script rotates selected secrets safely

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_DIR="${SCRIPT_DIR}/../secrets"

# Rotate specific secret
rotate_secret() {
    local secret_name="$1"
    local secret_file="${SECRETS_DIR}/${secret_name}.txt"
    
    if [[ -f "$secret_file" ]]; then
        # Backup old secret
        cp "$secret_file" "${secret_file}.old"
        
        # Generate new secret
        case "$secret_name" in
            "jwt_secret")
                openssl rand -base64 64 | tr -d "=+/" | cut -c1-64 > "$secret_file"
                ;;
            "redis_password")
                openssl rand -base64 32 | tr -d "=+/" | cut -c1-32 > "$secret_file"
                ;;
            *)
                openssl rand -base64 32 | tr -d "=+/" | cut -c1-24 > "$secret_file"
                ;;
        esac
        
        chmod 600 "$secret_file"
        echo "Rotated secret: $secret_name"
    else
        echo "Secret file not found: $secret_file"
        exit 1
    fi
}

# Main rotation logic
if [[ $# -eq 0 ]]; then
    echo "Usage: $0 <secret_name>"
    echo "Available secrets: jwt_secret, redis_password, grafana_admin_password"
    exit 1
fi

rotate_secret "$1"
echo "Secret rotation completed. Remember to restart affected services."
EOF

    chmod +x "${SCRIPT_DIR}/rotate-secrets.sh"
    log "Secrets rotation script created"
}

# Create secrets health check script
create_health_check() {
    log "Creating secrets health check script..."
    
    cat > "${SCRIPT_DIR}/check-secrets.sh" << 'EOF'
#!/bin/bash

# Secrets Health Check Script
# Validates all required secrets are present and properly formatted

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_DIR="${SCRIPT_DIR}/../secrets"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

check_secret() {
    local secret_name="$1"
    local min_length="${2:-8}"
    local secret_file="${SECRETS_DIR}/${secret_name}.txt"
    
    if [[ -f "$secret_file" ]]; then
        local secret_value=$(cat "$secret_file")
        local secret_length=${#secret_value}
        
        if [[ $secret_length -ge $min_length ]]; then
            echo -e "${GREEN}✓${NC} $secret_name (length: $secret_length)"
        else
            echo -e "${RED}✗${NC} $secret_name (too short: $secret_length < $min_length)"
            return 1
        fi
    else
        echo -e "${RED}✗${NC} $secret_name (missing file)"
        return 1
    fi
}

echo "Checking production secrets..."

errors=0

# Check all required secrets
check_secret "database_url" 20 || ((errors++))
check_secret "redis_url" 15 || ((errors++))
check_secret "redis_password" 16 || ((errors++))
check_secret "jwt_secret" 32 || ((errors++))
check_secret "postgres_db" 3 || ((errors++))
check_secret "postgres_user" 3 || ((errors++))
check_secret "postgres_password" 12 || ((errors++))
check_secret "grafana_admin_password" 12 || ((errors++))
check_secret "elasticsearch_password" 12 || ((errors++))

# Check placeholder secrets (warn if not updated)
check_placeholder() {
    local secret_name="$1"
    local secret_file="${SECRETS_DIR}/${secret_name}.txt"
    
    if [[ -f "$secret_file" ]]; then
        local secret_value=$(cat "$secret_file")
        if [[ "$secret_value" == *"YOUR_"* ]] || [[ "$secret_value" == *"HERE"* ]]; then
            echo -e "\033[1;33m⚠${NC} $secret_name (placeholder - needs manual update)"
        fi
    fi
}

echo ""
echo "Checking placeholder secrets..."
check_placeholder "openai_api_key"
check_placeholder "aws_access_key"
check_placeholder "aws_secret_key"
check_placeholder "smtp_password"

if [[ $errors -eq 0 ]]; then
    echo -e "\n${GREEN}All secrets validation passed!${NC}"
    exit 0
else
    echo -e "\n${RED}Found $errors secret validation errors!${NC}"
    exit 1
fi
EOF

    chmod +x "${SCRIPT_DIR}/check-secrets.sh"
    log "Secrets health check script created"
}

# Main execution
main() {
    log "Starting production secrets setup for ActiveLog..."
    
    check_dependencies
    setup_directories
    generate_secrets
    create_rotation_script
    create_health_check
    
    log "Production secrets setup completed successfully!"
    
    echo ""
    warn "IMPORTANT NEXT STEPS:"
    echo "1. Update the placeholder secrets with real values:"
    echo "   - openai_api_key.txt"
    echo "   - aws_access_key.txt" 
    echo "   - aws_secret_key.txt"
    echo "   - smtp_password.txt"
    echo "   - smtp_host.txt"
    echo "   - smtp_user.txt"
    echo ""
    echo "2. Run the health check: ./check-secrets.sh"
    echo "3. Create an encrypted backup and store it securely"
    echo "4. Set up secret rotation schedule"
    echo ""
    warn "Keep these secrets secure and never commit them to version control!"
}

# Run main function
main "$@"