#!/bin/bash

# Quick Beta User Invite Script
# Simple wrapper for common invite operations

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INVITE_SYSTEM="$SCRIPT_DIR/invite-system.py"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
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

usage() {
    echo "Beta User Invite Script"
    echo ""
    echo "Usage: $0 [EMAIL] [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -t, --template TEMPLATE    Template to use (standard|premium|developer)"
    echo "  -c, --campaign CAMPAIGN    Campaign ID"
    echo "  -b, --bulk CSV_FILE        Send bulk invites from CSV"
    echo "  -r, --referral CODE        Referral code"
    echo "  --invited-by USER_ID       Inviter user ID (required)"
    echo "  --help                     Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 user@example.com --invited-by admin123"
    echo "  $0 --bulk invites.csv --template premium --invited-by admin123"
    echo "  $0 dev@company.com --template developer --invited-by admin123"
}

# Default values
TEMPLATE="standard"
CAMPAIGN=""
BULK_FILE=""
REFERRAL_CODE=""
INVITED_BY=""
EMAIL=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--template)
            TEMPLATE="$2"
            shift 2
            ;;
        -c|--campaign)
            CAMPAIGN="$2"
            shift 2
            ;;
        -b|--bulk)
            BULK_FILE="$2"
            shift 2
            ;;
        -r|--referral)
            REFERRAL_CODE="$2"
            shift 2
            ;;
        --invited-by)
            INVITED_BY="$2"
            shift 2
            ;;
        --help)
            usage
            exit 0
            ;;
        -*)
            error "Unknown option: $1"
            ;;
        *)
            if [[ -z "$EMAIL" ]]; then
                EMAIL="$1"
            fi
            shift
            ;;
    esac
done

# Validate required parameters
if [[ -z "$INVITED_BY" ]]; then
    error "Inviter user ID is required (--invited-by)"
fi

# Validate template
if [[ "$TEMPLATE" != "standard" && "$TEMPLATE" != "premium" && "$TEMPLATE" != "developer" ]]; then
    error "Invalid template: $TEMPLATE. Use: standard, premium, or developer"
fi

# Check if bulk invite
if [[ -n "$BULK_FILE" ]]; then
    if [[ ! -f "$BULK_FILE" ]]; then
        error "CSV file not found: $BULK_FILE"
    fi
    
    log "Processing bulk invite from: $BULK_FILE"
    log "Template: $TEMPLATE"
    
    # Build command
    cmd="python3 $INVITE_SYSTEM bulk-invite --csv-file '$BULK_FILE' --template '$TEMPLATE' --invited-by '$INVITED_BY'"
    
    if [[ -n "$CAMPAIGN" ]]; then
        cmd="$cmd --campaign '$CAMPAIGN'"
    fi
    
    eval $cmd
    
    if [[ $? -eq 0 ]]; then
        log "Bulk invite completed successfully"
    else
        error "Bulk invite failed"
    fi
    
    exit 0
fi

# Single invite
if [[ -z "$EMAIL" ]]; then
    error "Email address is required for single invite"
fi

# Validate email format
if [[ ! "$EMAIL" =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]]; then
    error "Invalid email format: $EMAIL"
fi

log "Sending invite to: $EMAIL"
log "Template: $TEMPLATE"

# Build command
cmd="python3 $INVITE_SYSTEM invite --email '$EMAIL' --template '$TEMPLATE' --invited-by '$INVITED_BY'"

if [[ -n "$CAMPAIGN" ]]; then
    cmd="$cmd --campaign '$CAMPAIGN'"
    log "Campaign: $CAMPAIGN"
fi

if [[ -n "$REFERRAL_CODE" ]]; then
    warn "Referral codes not yet implemented in this script"
fi

# Execute invite
eval $cmd

if [[ $? -eq 0 ]]; then
    log "Invite sent successfully!"
    
    # Show template-specific info
    case "$TEMPLATE" in
        "premium")
            echo ""
            log "Premium Beta Features:"
            log "  - Advanced AI insights"
            log "  - Custom integrations"  
            log "  - 1-on-1 onboarding"
            log "  - Early enterprise features"
            ;;
        "developer")
            echo ""
            log "Developer Beta Features:"
            log "  - Full API access"
            log "  - SDK early access"
            log "  - Integration sandbox"
            log "  - Developer community"
            ;;
        "standard")
            echo ""
            log "Standard Beta Features:"
            log "  - New dashboard interface"
            log "  - Advanced analytics"
            log "  - Priority support"
            ;;
    esac
    
    echo ""
    log "The user will receive an email with their invitation code."
    log "They can accept the invitation at: http://localhost:3000/beta/accept"
    
else
    error "Failed to send invite"
fi