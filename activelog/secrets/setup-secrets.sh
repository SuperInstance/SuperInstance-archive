#!/bin/bash

# ActiveLog Secrets Setup Script
# This script generates secure secrets for production deployment

set -e

SECRETS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Setting up ActiveLog production secrets..."

# Function to generate random password
generate_password() {
    openssl rand -base64 32
}

# Function to generate JWT secret
generate_jwt_secret() {
    openssl rand -hex 64
}

# Function to create secret file
create_secret() {
    local name=$1
    local value=$2
    local file="$SECRETS_DIR/${name}.txt"
    
    echo "$value" > "$file"
    chmod 600 "$file"
    echo "Created secret: $name"
}

# Database secrets
echo "Generating database secrets..."
DB_NAME="activelog_prod"
DB_USER="activelog"
DB_PASSWORD=$(generate_password)
DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}"

create_secret "postgres_db" "$DB_NAME"
create_secret "postgres_user" "$DB_USER"
create_secret "postgres_password" "$DB_PASSWORD"
create_secret "database_url" "$DATABASE_URL"

# Redis secrets
echo "Generating Redis secrets..."
REDIS_PASSWORD=$(generate_password)
REDIS_URL="redis://:${REDIS_PASSWORD}@redis:6379/0"

create_secret "redis_password" "$REDIS_PASSWORD"
create_secret "redis_url" "$REDIS_URL"

# JWT secret
echo "Generating JWT secret..."
JWT_SECRET=$(generate_jwt_secret)
create_secret "jwt_secret" "$JWT_SECRET"

# OpenAI API key (placeholder - replace with actual key)
echo "Creating OpenAI API key placeholder..."
create_secret "openai_api_key" "sk-your-openai-api-key-here"

# AWS credentials (placeholders - replace with actual credentials)
echo "Creating AWS credentials placeholders..."
create_secret "aws_access_key" "your-aws-access-key-id"
create_secret "aws_secret_key" "your-aws-secret-access-key"

# SMTP configuration (placeholders - replace with actual values)
echo "Creating SMTP configuration placeholders..."
create_secret "smtp_host" "smtp.gmail.com"
create_secret "smtp_user" "your-email@gmail.com"
create_secret "smtp_password" "your-app-password"

# Grafana secrets
echo "Generating Grafana secrets..."
GRAFANA_ADMIN_PASSWORD=$(generate_password)
GRAFANA_DB_NAME="grafana"
GRAFANA_DB_USER="grafana"
GRAFANA_DB_PASSWORD=$(generate_password)

create_secret "grafana_admin_password" "$GRAFANA_ADMIN_PASSWORD"
create_secret "grafana_db_name" "$GRAFANA_DB_NAME"
create_secret "grafana_db_user" "$GRAFANA_DB_USER"
create_secret "grafana_db_password" "$GRAFANA_DB_PASSWORD"

# Set proper ownership and permissions
chown -R $(whoami):$(whoami) "$SECRETS_DIR"
chmod 700 "$SECRETS_DIR"
chmod 600 "$SECRETS_DIR"/*.txt

echo ""
echo "✅ Secrets setup complete!"
echo ""
echo "📋 Important Notes:"
echo "1. Update OpenAI API key: $SECRETS_DIR/openai_api_key.txt"
echo "2. Update AWS credentials: $SECRETS_DIR/aws_access_key.txt and $SECRETS_DIR/aws_secret_key.txt"
echo "3. Update SMTP settings: $SECRETS_DIR/smtp_*.txt"
echo "4. Database password: $DB_PASSWORD"
echo "5. Redis password: $REDIS_PASSWORD"
echo "6. Grafana admin password: $GRAFANA_ADMIN_PASSWORD"
echo ""
echo "🔒 All secret files are secured with 600 permissions"
echo "📁 Secrets directory: $SECRETS_DIR"
echo ""
echo "⚠️  IMPORTANT: Never commit these files to version control!"
echo "   Add secrets/ to your .gitignore file"