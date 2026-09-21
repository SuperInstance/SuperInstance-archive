#!/bin/bash

# Database Maintenance Script for ActiveLog Production
# Performs routine maintenance, optimization, and health checks

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="/opt/activelog/logs/database"
BACKUP_DIR="/opt/activelog/backup/database"
PGHOST="${PGHOST:-postgres}"
PGPORT="${PGPORT:-5432}"
PGDATABASE="${PGDATABASE:-activelog_prod}"
PGUSER="${PGUSER:-activelog_admin}"

# Logging setup
LOGFILE="${LOG_DIR}/maintenance_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$LOG_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${GREEN}[$timestamp] $message${NC}" | tee -a "$LOGFILE"
}

warn() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${YELLOW}[$timestamp] WARNING: $message${NC}" | tee -a "$LOGFILE"
}

error() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${RED}[$timestamp] ERROR: $message${NC}" | tee -a "$LOGFILE"
    exit 1
}

info() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${BLUE}[$timestamp] $message${NC}" | tee -a "$LOGFILE"
}

# Check dependencies
check_dependencies() {
    log "Checking dependencies..."
    
    command -v psql >/dev/null 2>&1 || error "psql is required but not installed"
    command -v pg_dump >/dev/null 2>&1 || error "pg_dump is required but not installed"
    command -v vacuumdb >/dev/null 2>&1 || error "vacuumdb is required but not installed"
    
    # Test database connection
    if ! psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -c '\q' >/dev/null 2>&1; then
        error "Cannot connect to PostgreSQL database"
    fi
    
    log "All dependencies satisfied and database connection successful"
}

# Database health check
health_check() {
    log "Performing database health check..."
    
    local temp_file=$(mktemp)
    
    # Check database size and growth
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -t -A -F',' > "$temp_file" << 'EOF'
SELECT 
    'database_size_mb',
    ROUND(pg_database_size(current_database()) / 1024.0 / 1024.0, 2);
    
SELECT 
    'total_connections',
    count(*)
FROM pg_stat_activity;

SELECT 
    'active_connections',
    count(*)
FROM pg_stat_activity 
WHERE state = 'active';

SELECT 
    'cache_hit_ratio',
    ROUND(
        100.0 * sum(heap_blks_hit) / NULLIF(sum(heap_blks_hit + heap_blks_read), 0), 
        2
    )
FROM pg_statio_user_tables;

SELECT 
    'index_hit_ratio',
    ROUND(
        100.0 * sum(idx_blks_hit) / NULLIF(sum(idx_blks_hit + idx_blks_read), 0), 
        2
    )
FROM pg_statio_user_indexes;

SELECT 
    'longest_running_query_minutes',
    COALESCE(
        ROUND(
            EXTRACT(EPOCH FROM (NOW() - query_start)) / 60.0, 
            2
        ), 
        0
    )
FROM pg_stat_activity 
WHERE state = 'active' 
AND query_start IS NOT NULL
ORDER BY query_start 
LIMIT 1;
EOF

    # Parse and display results
    while IFS=',' read -r metric value; do
        case "$metric" in
            "database_size_mb")
                info "Database size: ${value} MB"
                if (( $(echo "$value > 10240" | bc -l) )); then
                    warn "Database size is larger than 10GB, consider archiving old data"
                fi
                ;;
            "total_connections")
                info "Total connections: $value"
                if (( value > 150 )); then
                    warn "High number of connections: $value"
                fi
                ;;
            "active_connections")
                info "Active connections: $value"
                ;;
            "cache_hit_ratio")
                info "Cache hit ratio: ${value}%"
                if (( $(echo "$value < 95" | bc -l) )); then
                    warn "Low cache hit ratio: ${value}%. Consider increasing shared_buffers."
                fi
                ;;
            "index_hit_ratio")
                info "Index hit ratio: ${value}%"
                if (( $(echo "$value < 95" | bc -l) )); then
                    warn "Low index hit ratio: ${value}%. Consider increasing shared_buffers."
                fi
                ;;
            "longest_running_query_minutes")
                info "Longest running query: ${value} minutes"
                if (( $(echo "$value > 30" | bc -l) )); then
                    warn "Long running query detected: ${value} minutes"
                fi
                ;;
        esac
    done < "$temp_file"
    
    rm -f "$temp_file"
    log "Health check completed"
}

# Check for bloat
check_bloat() {
    log "Checking for table and index bloat..."
    
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" << 'EOF'
-- Table bloat check
WITH table_bloat AS (
    SELECT
        schemaname,
        tablename,
        ROUND(
            CASE 
                WHEN cc.reltuples = 0 THEN 0
                ELSE 100 * (cc.relpages - 
                    CASE 
                        WHEN cc.relpages < 10 THEN 0
                        ELSE CEIL(cc.reltuples / (8192 / 32))
                    END) / cc.relpages::numeric
            END, 
            2
        ) AS bloat_percent,
        pg_size_pretty(pg_relation_size(cc.oid)) as table_size
    FROM pg_stat_user_tables s
    JOIN pg_class cc ON cc.relname = s.tablename
    WHERE s.schemaname = 'public'
)
SELECT 
    'BLOAT CHECK' as check_type,
    schemaname,
    tablename,
    bloat_percent,
    table_size
FROM table_bloat 
WHERE bloat_percent > 20
ORDER BY bloat_percent DESC;
EOF

    log "Bloat check completed"
}

# Analyze slow queries
analyze_slow_queries() {
    log "Analyzing slow queries..."
    
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" << 'EOF'
-- Top 10 slowest queries
SELECT 
    'TOP SLOW QUERIES' as analysis_type,
    ROUND(mean_exec_time::numeric, 2) as avg_time_ms,
    calls,
    ROUND(total_exec_time::numeric, 2) as total_time_ms,
    ROUND(100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0), 2) AS hit_percent,
    LEFT(query, 100) as query_preview
FROM pg_stat_statements 
WHERE calls > 10
ORDER BY mean_exec_time DESC 
LIMIT 10;
EOF

    log "Slow query analysis completed"
}

# Refresh materialized views
refresh_materialized_views() {
    log "Refreshing materialized views..."
    
    local views=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -t -c \
        "SELECT matviewname FROM pg_matviews WHERE schemaname = 'public' ORDER BY matviewname;")
    
    if [ -z "$views" ]; then
        info "No materialized views found to refresh"
        return 0
    fi
    
    for view in $views; do
        log "Refreshing materialized view: $view"
        if psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -c \
            "REFRESH MATERIALIZED VIEW CONCURRENTLY $view;" >/dev/null 2>&1; then
            info "Successfully refreshed $view"
        else
            warn "Failed to refresh $view, trying without CONCURRENTLY"
            psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -c \
                "REFRESH MATERIALIZED VIEW $view;"
        fi
    done
    
    log "Materialized view refresh completed"
}

# Run vacuum and analyze
vacuum_analyze() {
    log "Running vacuum and analyze operations..."
    
    # Smart vacuum based on table statistics
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" << 'EOF'
SELECT smart_vacuum_analyze();
EOF

    # Update table statistics
    log "Updating table statistics..."
    vacuumdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" --analyze-only
    
    log "Vacuum and analyze completed"
}

# Reindex if needed
reindex_if_needed() {
    log "Checking if reindexing is needed..."
    
    local needs_reindex=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -t -c \
        "SELECT COUNT(*) FROM pg_stat_user_indexes WHERE idx_scan = 0 AND idx_tup_read > 1000;")
    
    if [ "$needs_reindex" -gt 0 ]; then
        warn "Found $needs_reindex unused indexes with significant reads"
        
        # List problematic indexes
        psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" << 'EOF'
SELECT 
    'UNUSED INDEXES' as issue_type,
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read
FROM pg_stat_user_indexes 
WHERE idx_scan = 0 
AND idx_tup_read > 1000
ORDER BY idx_tup_read DESC;
EOF
    fi
    
    # Reindex tables with high bloat
    local high_bloat_tables=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -t -A -c \
        "SELECT tablename FROM pg_stat_user_tables s 
         JOIN pg_class c ON c.relname = s.tablename 
         WHERE s.n_dead_tup > 10000 AND s.n_dead_tup::float / NULLIF(s.n_tup, 0) > 0.1;")
    
    if [ -n "$high_bloat_tables" ]; then
        warn "Found tables with high bloat, considering reindex..."
        for table in $high_bloat_tables; do
            warn "Table $table has high bloat"
            # Note: REINDEX can lock tables, so we just log for now
            # Uncomment the following line for automatic reindexing during maintenance window
            # psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -c "REINDEX TABLE $table;"
        done
    fi
    
    log "Reindex check completed"
}

# Clean up old data
cleanup_old_data() {
    log "Cleaning up old data..."
    
    # Archive old activity logs (older than 90 days)
    local old_activities=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -t -c \
        "SELECT COUNT(*) FROM activity_logs WHERE created_at < NOW() - INTERVAL '90 days';")
    
    if [ "$old_activities" -gt 0 ]; then
        log "Archiving $old_activities old activity log entries..."
        
        # Create archive table if it doesn't exist
        psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" << 'EOF'
CREATE TABLE IF NOT EXISTS activity_logs_archive (
    LIKE activity_logs INCLUDING ALL
);
EOF
        
        # Move old data to archive
        psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" << 'EOF'
WITH archived AS (
    DELETE FROM activity_logs 
    WHERE created_at < NOW() - INTERVAL '90 days'
    RETURNING *
)
INSERT INTO activity_logs_archive 
SELECT * FROM archived;
EOF
        
        log "Archived $old_activities activity log entries"
    fi
    
    # Clean up temporary files and failed processing jobs older than 7 days
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" << 'EOF'
DELETE FROM ai_processing_jobs 
WHERE status = 'failed' 
AND created_at < NOW() - INTERVAL '7 days';

-- Clean up old session data
DELETE FROM user_sessions 
WHERE expires_at < NOW() - INTERVAL '1 day';

-- Clean up old notification data (older than 30 days and read)
DELETE FROM notifications 
WHERE read_at IS NOT NULL 
AND created_at < NOW() - INTERVAL '30 days';
EOF

    log "Old data cleanup completed"
}

# Generate performance report
generate_performance_report() {
    log "Generating performance report..."
    
    local report_file="${LOG_DIR}/performance_report_$(date +%Y%m%d_%H%M%S).txt"
    
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" > "$report_file" << 'EOF'
\echo '=== ActiveLog Database Performance Report ==='
\echo ''

\echo '=== Database Overview ==='
SELECT 
    'Database Size' as metric,
    pg_size_pretty(pg_database_size(current_database())) as value;

SELECT 
    'Total Tables' as metric,
    count(*)::text as value
FROM pg_tables 
WHERE schemaname = 'public';

\echo ''
\echo '=== Connection Statistics ==='
SELECT 
    state,
    count(*) as connections
FROM pg_stat_activity 
GROUP BY state
ORDER BY connections DESC;

\echo ''
\echo '=== Cache Hit Ratios ==='
SELECT 
    'Table Hit Ratio' AS metric,
    ROUND(100.0 * sum(heap_blks_hit) / NULLIF(sum(heap_blks_hit + heap_blks_read), 0), 2)::text || '%' AS value
FROM pg_statio_user_tables
UNION ALL
SELECT 
    'Index Hit Ratio' AS metric,
    ROUND(100.0 * sum(idx_blks_hit) / NULLIF(sum(idx_blks_hit + idx_blks_read), 0), 2)::text || '%' AS value
FROM pg_statio_user_indexes;

\echo ''
\echo '=== Top 5 Largest Tables ==='
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 5;

\echo ''
\echo '=== Most Active Tables (by reads) ==='
SELECT 
    tablename,
    seq_scan + idx_scan as total_scans,
    seq_tup_read + idx_tup_fetch as total_rows_read,
    n_tup_ins + n_tup_upd + n_tup_del as total_modifications
FROM pg_stat_user_tables
ORDER BY (seq_scan + idx_scan) DESC
LIMIT 5;

\echo ''
\echo '=== Recent Maintenance Operations ==='
SELECT 
    operation,
    status,
    completed_at,
    details
FROM maintenance_log
ORDER BY completed_at DESC
LIMIT 10;
EOF

    log "Performance report generated: $report_file"
    
    # Send report summary to log
    info "=== Performance Report Summary ==="
    head -n 50 "$report_file" | tail -n +2 | while read line; do
        info "$line"
    done
}

# Update statistics
update_statistics() {
    log "Updating database statistics..."
    
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" << 'EOF'
-- Reset query statistics if they're getting too large
DO $$
BEGIN
    IF (SELECT count(*) FROM pg_stat_statements) > 5000 THEN
        SELECT pg_stat_statements_reset();
    END IF;
END;
$$;

-- Update table and index statistics
ANALYZE;
EOF

    log "Statistics update completed"
}

# Log maintenance completion
log_maintenance() {
    local operation="$1"
    local status="$2"
    local details="$3"
    
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" << EOF
INSERT INTO maintenance_log (operation, status, completed_at, details)
VALUES ('$operation', '$status', NOW(), '$details');
EOF
}

# Main maintenance routine
main_maintenance() {
    log "Starting database maintenance routine..."
    
    local start_time=$(date +%s)
    
    # Perform maintenance tasks
    health_check
    check_bloat
    analyze_slow_queries
    refresh_materialized_views
    vacuum_analyze
    reindex_if_needed
    cleanup_old_data
    update_statistics
    generate_performance_report
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log "Database maintenance completed in ${duration} seconds"
    
    # Log maintenance completion
    log_maintenance "full_maintenance" "completed" \
        "Full maintenance routine completed successfully in ${duration} seconds"
}

# Quick maintenance (for frequent runs)
quick_maintenance() {
    log "Starting quick maintenance routine..."
    
    local start_time=$(date +%s)
    
    # Perform lightweight maintenance tasks
    health_check
    refresh_materialized_views
    update_statistics
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log "Quick maintenance completed in ${duration} seconds"
    
    # Log maintenance completion
    log_maintenance "quick_maintenance" "completed" \
        "Quick maintenance routine completed in ${duration} seconds"
}

# Emergency maintenance (for critical issues)
emergency_maintenance() {
    log "Starting emergency maintenance routine..."
    
    local start_time=$(date +%s)
    
    # Address critical issues
    health_check
    
    # Check for blocking queries
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" << 'EOF'
-- Find and report blocking queries
SELECT 
    blocked_locks.pid AS blocked_pid,
    blocked_activity.usename AS blocked_user,
    blocking_locks.pid AS blocking_pid,
    blocking_activity.usename AS blocking_user,
    blocked_activity.query AS blocked_statement,
    blocking_activity.query AS blocking_statement,
    blocked_activity.application_name AS blocked_application,
    blocking_activity.application_name AS blocking_application
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
    AND blocking_locks.DATABASE IS NOT DISTINCT FROM blocked_locks.DATABASE
    AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
    AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
    AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
    AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
    AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
    AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
    AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
    AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
    AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.GRANTED;
EOF
    
    # Force vacuum on heavily modified tables
    vacuum_analyze
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    warn "Emergency maintenance completed in ${duration} seconds"
    
    # Log maintenance completion
    log_maintenance "emergency_maintenance" "completed" \
        "Emergency maintenance routine completed in ${duration} seconds"
}

# Main execution
case "${1:-full}" in
    "full")
        check_dependencies
        main_maintenance
        ;;
    "quick")
        check_dependencies
        quick_maintenance
        ;;
    "emergency")
        check_dependencies
        emergency_maintenance
        ;;
    "health")
        check_dependencies
        health_check
        ;;
    *)
        echo "Usage: $0 {full|quick|emergency|health}"
        echo "  full      - Complete maintenance routine (default)"
        echo "  quick     - Quick maintenance for frequent runs"
        echo "  emergency - Emergency maintenance for critical issues"
        echo "  health    - Health check only"
        exit 1
        ;;
esac