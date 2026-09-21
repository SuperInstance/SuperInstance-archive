#!/bin/bash

# Feedback Viewer CLI
# Simple interface for viewing and managing beta feedback

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FEEDBACK_AGGREGATOR="$SCRIPT_DIR/feedback-aggregator.py"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

highlight() {
    echo -e "${CYAN}$1${NC}"
}

usage() {
    echo "Feedback Viewer CLI"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  summary [DAYS]              Show feedback summary (default: 30 days)"
    echo "  report [DAYS]               Generate detailed feedback report"
    echo "  export [FORMAT] [DAYS]      Export feedback data (json|csv)"
    echo "  update ID STATUS            Update feedback status"
    echo "  submit                      Submit test feedback (interactive)"
    echo "  dashboard                   Show live feedback dashboard"
    echo "  help                        Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 summary 7                # Last 7 days summary"
    echo "  $0 report 14                # 14-day detailed report"  
    echo "  $0 export csv 30            # Export last 30 days as CSV"
    echo "  $0 update abc-123 resolved  # Mark feedback as resolved"
    echo "  $0 dashboard                # Live dashboard view"
}

# Show feedback summary
show_summary() {
    local days="${1:-30}"
    
    info "Generating feedback summary for last $days days..."
    
    result=$(python3 "$FEEDBACK_AGGREGATOR" summary --days "$days" 2>/dev/null)
    
    if [[ $? -ne 0 ]]; then
        error "Failed to get feedback summary"
    fi
    
    # Parse and display summary
    total=$(echo "$result" | jq -r '.total_feedback')
    avg_rating=$(echo "$result" | jq -r '.average_rating')
    
    highlight "=== FEEDBACK SUMMARY (Last $days Days) ==="
    echo ""
    log "Total Feedback: $total"
    log "Average Rating: $avg_rating/5.0"
    
    # Category breakdown
    echo ""
    highlight "Category Breakdown:"
    echo "$result" | jq -r '.category_breakdown | to_entries[] | "  \(.key): \(.value)"' | sort -k2 -nr
    
    # Priority distribution
    echo ""
    highlight "Priority Distribution:"
    echo "$result" | jq -r '.priority_distribution | to_entries[] | "  \(.key): \(.value)"' | sort -k2 -nr
    
    # Status distribution
    echo ""
    highlight "Status Distribution:"
    echo "$result" | jq -r '.status_distribution | to_entries[] | "  \(.key): \(.value)"' | sort -k2 -nr
    
    # Top issues
    echo ""
    highlight "Top Issues:"
    echo "$result" | jq -r '.top_issues[] | "  - \(.issue) (\(.count) reports)"' | head -5
    
    # Trending topics
    echo ""
    highlight "Trending Topics:"
    echo "$result" | jq -r '.trending_topics[]' | head -5 | sed 's/^/  - /'
    
    # Sentiment analysis
    echo ""
    highlight "Sentiment Analysis:"
    echo "$result" | jq -r '.sentiment_analysis | to_entries[] | "  \(.key): \(.value)"'
}

# Generate detailed report
generate_report() {
    local days="${1:-30}"
    
    info "Generating detailed feedback report for last $days days..."
    
    result=$(python3 "$FEEDBACK_AGGREGATOR" report --days "$days" 2>/dev/null)
    
    if [[ $? -ne 0 ]]; then
        error "Failed to generate feedback report"
    fi
    
    # Parse and display report
    highlight "=== DETAILED FEEDBACK REPORT (Last $days Days) ==="
    echo ""
    
    # Summary section
    total=$(echo "$result" | jq -r '.summary.total_feedback')
    avg_rating=$(echo "$result" | jq -r '.summary.average_rating')
    
    log "Executive Summary:"
    echo "  Total Feedback Items: $total"
    echo "  Average Rating: $avg_rating/5.0"
    
    # Engagement metrics
    echo ""
    highlight "Engagement Metrics:"
    active_users=$(echo "$result" | jq -r '.engagement_metrics.active_feedback_users')
    satisfaction=$(echo "$result" | jq -r '.engagement_metrics.satisfaction_score')
    echo "  Active Feedback Users: $active_users"
    echo "  Satisfaction Score: $satisfaction"
    
    # Resolution metrics
    echo ""
    highlight "Resolution Metrics:"
    resolved=$(echo "$result" | jq -r '.resolution_metrics.resolved_count')
    in_progress=$(echo "$result" | jq -r '.resolution_metrics.in_progress_count')
    open_count=$(echo "$result" | jq -r '.resolution_metrics.open_count')
    avg_hours=$(echo "$result" | jq -r '.resolution_metrics.avg_resolution_hours')
    
    echo "  Resolved: $resolved"
    echo "  In Progress: $in_progress"
    echo "  Open: $open_count"
    echo "  Avg Resolution Time: ${avg_hours} hours"
    
    # Top contributors
    echo ""
    highlight "Top Contributors:"
    echo "$result" | jq -r '.top_contributors[] | "  \(.email): \(.feedback_count) items (avg rating: \(.avg_rating))"' | head -5
    
    # Insights
    echo ""
    highlight "Key Insights:"
    echo "$result" | jq -r '.insights[]' | sed 's/^/  • /'
    
    echo ""
    log "Report generated successfully!"
}

# Export feedback data
export_feedback() {
    local format="${1:-json}"
    local days="${2:-30}"
    
    if [[ "$format" != "json" && "$format" != "csv" ]]; then
        error "Invalid format: $format. Use 'json' or 'csv'"
    fi
    
    info "Exporting feedback data as $format for last $days days..."
    
    result=$(python3 "$FEEDBACK_AGGREGATOR" export --format "$format" --days "$days" 2>&1)
    
    if [[ $? -eq 0 ]]; then
        export_file=$(echo "$result" | grep "Exported to:" | cut -d' ' -f3)
        log "Export completed successfully!"
        echo "File: $export_file"
        
        # Show file info
        if [[ -f "$export_file" ]]; then
            file_size=$(du -h "$export_file" | cut -f1)
            echo "Size: $file_size"
        fi
    else
        error "Export failed: $result"
    fi
}

# Update feedback status
update_feedback() {
    local feedback_id="$1"
    local status="$2"
    
    if [[ -z "$feedback_id" || -z "$status" ]]; then
        error "Feedback ID and status are required"
    fi
    
    valid_statuses=("open" "in_progress" "resolved" "closed")
    if [[ ! " ${valid_statuses[@]} " =~ " ${status} " ]]; then
        error "Invalid status: $status. Valid options: ${valid_statuses[*]}"
    fi
    
    info "Updating feedback $feedback_id to $status..."
    
    result=$(python3 "$FEEDBACK_AGGREGATOR" update --feedback-id "$feedback_id" --status "$status" 2>&1)
    
    if [[ $? -eq 0 ]]; then
        log "Feedback status updated successfully!"
    else
        error "Update failed: $result"
    fi
}

# Interactive feedback submission
submit_feedback() {
    info "Interactive feedback submission"
    echo ""
    
    # Get user input
    read -p "User ID: " user_id
    if [[ -z "$user_id" ]]; then
        error "User ID is required"
    fi
    
    echo ""
    echo "Available categories:"
    echo "  1. bug_report"
    echo "  2. feature_request"
    echo "  3. usability"
    echo "  4. performance"
    echo "  5. documentation"
    echo "  6. general"
    echo ""
    read -p "Select category (1-6): " category_choice
    
    case "$category_choice" in
        1) category="bug_report" ;;
        2) category="feature_request" ;;
        3) category="usability" ;;
        4) category="performance" ;;
        5) category="documentation" ;;
        6) category="general" ;;
        *) error "Invalid category selection" ;;
    esac
    
    echo ""
    read -p "Subject: " subject
    if [[ -z "$subject" ]]; then
        error "Subject is required"
    fi
    
    echo ""
    echo "Message (press Ctrl+D when done):"
    message=$(cat)
    if [[ -z "$message" ]]; then
        error "Message is required"
    fi
    
    echo ""
    read -p "Rating (1-5, optional): " rating
    
    # Submit feedback
    info "Submitting feedback..."
    
    cmd="python3 $FEEDBACK_AGGREGATOR submit --user-id '$user_id' --category '$category' --subject '$subject' --message '$message'"
    
    if [[ -n "$rating" ]]; then
        cmd="$cmd --rating $rating"
    fi
    
    result=$(eval "$cmd" 2>&1)
    
    if [[ $? -eq 0 ]]; then
        feedback_id=$(echo "$result" | grep "Feedback submitted:" | cut -d' ' -f3)
        log "Feedback submitted successfully!"
        echo "Feedback ID: $feedback_id"
    else
        error "Submission failed: $result"
    fi
}

# Show live dashboard (simplified)
show_dashboard() {
    info "Live Feedback Dashboard"
    echo ""
    
    while true; do
        clear
        
        highlight "=== ACTIVELOG FEEDBACK DASHBOARD ==="
        echo "Updated: $(date)"
        echo ""
        
        # Get recent summary
        result=$(python3 "$FEEDBACK_AGGREGATOR" summary --days 7 2>/dev/null)
        
        if [[ $? -eq 0 ]]; then
            total=$(echo "$result" | jq -r '.total_feedback')
            avg_rating=$(echo "$result" | jq -r '.average_rating')
            
            # Status overview
            echo "📊 7-Day Overview:"
            echo "  Total Feedback: $total"
            echo "  Average Rating: $avg_rating/5.0"
            
            # Quick stats
            echo ""
            echo "📈 Quick Stats:"
            echo "$result" | jq -r '.status_distribution | to_entries[] | "  \(.key | ascii_upcase): \(.value)"'
            
            # Priority alerts
            echo ""
            critical=$(echo "$result" | jq -r '.priority_distribution.critical // 0')
            high=$(echo "$result" | jq -r '.priority_distribution.high // 0')
            
            if [[ "$critical" -gt 0 ]]; then
                warn "🚨 $critical CRITICAL issues need attention!"
            fi
            
            if [[ "$high" -gt 0 ]]; then
                warn "⚡ $high HIGH priority issues open"
            fi
            
            # Top trending
            echo ""
            echo "🔥 Trending Topics:"
            echo "$result" | jq -r '.trending_topics[]' | head -3 | sed 's/^/  • /'
            
        else
            error "Failed to load dashboard data"
        fi
        
        echo ""
        echo "Press Ctrl+C to exit, or wait 30s for refresh..."
        sleep 30
    done
}

# Main command processing
case "$1" in
    "summary")
        show_summary "$2"
        ;;
    "report")
        generate_report "$2"
        ;;
    "export")
        export_feedback "$2" "$3"
        ;;
    "update")
        if [[ -z "$2" || -z "$3" ]]; then
            error "Usage: $0 update FEEDBACK_ID STATUS"
        fi
        update_feedback "$2" "$3"
        ;;
    "submit")
        submit_feedback
        ;;
    "dashboard")
        show_dashboard
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