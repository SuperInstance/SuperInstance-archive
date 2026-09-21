#!/bin/bash

# NDA Manager CLI Wrapper
# Simplified interface for common NDA operations

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NDA_MANAGER="$SCRIPT_DIR/nda-manager.py"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

info() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')] $1${NC}"
}

usage() {
    echo "NDA Manager CLI"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  check USER_ID              Check user's NDA status"
    echo "  sign USER_ID               Sign NDA for user (admin only)"
    echo "  report [DAYS]              Generate compliance report"
    echo "  reminders                  Send expiry reminder emails"
    echo "  current                    Show current NDA document info"
    echo "  bulk-check                 Check all beta users' NDA status"
    echo "  help                       Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 check user-123-456"
    echo "  $0 sign user-123-456"
    echo "  $0 report 7"
    echo "  $0 reminders"
}

# Check if user ID is valid UUID format
validate_user_id() {
    local user_id="$1"
    if [[ ! "$user_id" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]; then
        error "Invalid user ID format: $user_id"
    fi
}

# Check user NDA status
check_nda_status() {
    local user_id="$1"
    validate_user_id "$user_id"
    
    info "Checking NDA status for user: $user_id"
    
    result=$(python3 "$NDA_MANAGER" status --user-id "$user_id" 2>/dev/null)
    
    if [[ $? -ne 0 ]]; then
        error "Failed to check NDA status"
    fi
    
    status=$(echo "$result" | jq -r '.status' 2>/dev/null)
    
    case "$status" in
        "signed")
            signed_version=$(echo "$result" | jq -r '.signed_version')
            agreed_at=$(echo "$result" | jq -r '.agreed_at')
            expiry_date=$(echo "$result" | jq -r '.expiry_date')
            days_until_expiry=$(echo "$result" | jq -r '.days_until_expiry')
            
            log "✓ NDA Status: SIGNED"
            echo "  Version: $signed_version"
            echo "  Signed: $agreed_at"
            if [[ "$expiry_date" != "null" ]]; then
                echo "  Expires: $expiry_date"
                if [[ "$days_until_expiry" != "null" && "$days_until_expiry" -lt 30 ]]; then
                    warn "  ⚠ Expires in $days_until_expiry days"
                fi
            fi
            ;;
        "not_signed")
            current_version=$(echo "$result" | jq -r '.current_nda_version')
            warn "✗ NDA Status: NOT SIGNED"
            echo "  Required version: $current_version"
            echo "  User must sign NDA to access beta features"
            ;;
        "expired")
            signed_version=$(echo "$result" | jq -r '.signed_version')
            expiry_date=$(echo "$result" | jq -r '.expiry_date')
            error "✗ NDA Status: EXPIRED"
            echo "  Signed version: $signed_version"
            echo "  Expired on: $expiry_date"
            echo "  User must sign new NDA"
            ;;
        *)
            error "Unknown NDA status: $status"
            ;;
    esac
}

# Sign NDA for user (admin operation)
sign_nda() {
    local user_id="$1"
    validate_user_id "$user_id"
    
    warn "This will sign the NDA on behalf of the user. Continue? (y/N)"
    read -r confirm
    
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        info "NDA signing cancelled"
        return 0
    fi
    
    info "Signing NDA for user: $user_id"
    
    result=$(python3 "$NDA_MANAGER" sign --user-id "$user_id" 2>&1)
    
    if [[ $? -eq 0 ]]; then
        log "✓ NDA signed successfully"
        echo "$result"
    else
        error "Failed to sign NDA: $result"
    fi
}

# Generate compliance report
generate_report() {
    local days="${1:-30}"
    
    info "Generating NDA compliance report for last $days days..."
    
    result=$(python3 "$NDA_MANAGER" report --days "$days" 2>/dev/null)
    
    if [[ $? -ne 0 ]]; then
        error "Failed to generate report"
    fi
    
    # Parse and display report
    total_users=$(echo "$result" | jq -r '.statistics.total_beta_users')
    valid_nda=$(echo "$result" | jq -r '.statistics.users_with_valid_nda')
    expired_nda=$(echo "$result" | jq -r '.statistics.users_with_expired_nda')
    no_nda=$(echo "$result" | jq -r '.statistics.users_without_nda')
    compliance_rate=$(echo "$result" | jq -r '.statistics.compliance_rate')
    
    log "NDA Compliance Report"
    echo "=================="
    echo "Total Beta Users: $total_users"
    echo "Users with Valid NDA: $valid_nda"
    echo "Users with Expired NDA: $expired_nda"  
    echo "Users without NDA: $no_nda"
    echo "Compliance Rate: ${compliance_rate}%"
    
    # Show compliance issues if any
    issues_count=$(echo "$result" | jq -r '.compliance_issues | length')
    
    if [[ "$issues_count" -gt 0 ]]; then
        echo ""
        warn "Compliance Issues ($issues_count):"
        echo "$result" | jq -r '.compliance_issues[] | "  - \(.email): \(.issue)"'
    else
        echo ""
        log "✓ No compliance issues found"
    fi
}

# Send reminder emails
send_reminders() {
    info "Sending NDA expiry reminder emails..."
    
    result=$(python3 "$NDA_MANAGER" reminders 2>&1)
    
    if [[ $? -eq 0 ]]; then
        count=$(echo "$result" | grep -o '[0-9]\+' | head -1)
        log "✓ Sent $count reminder emails"
    else
        error "Failed to send reminders: $result"
    fi
}

# Show current NDA document
show_current_nda() {
    info "Current NDA Document:"
    
    python3 "$NDA_MANAGER" current
}

# Bulk check all beta users
bulk_check_nda() {
    info "Checking NDA status for all beta users..."
    
    # Get all beta user IDs (requires database access)
    # This is a simplified version - in production you'd query the database
    warn "Bulk check requires database query implementation"
    warn "Use individual check command for now"
}

# Main command processing
case "$1" in
    "check")
        if [[ -z "$2" ]]; then
            error "User ID required for check command"
        fi
        check_nda_status "$2"
        ;;
    "sign")
        if [[ -z "$2" ]]; then
            error "User ID required for sign command"
        fi
        sign_nda "$2"
        ;;
    "report")
        generate_report "$2"
        ;;
    "reminders")
        send_reminders
        ;;
    "current")
        show_current_nda
        ;;
    "bulk-check")
        bulk_check_nda
        ;;
    "help"|"--help"|"-h")
        usage
        ;;
    "")
        usage
        exit 1
        ;;
    *)
        error "Unknown command: $1"
        ;;
esac