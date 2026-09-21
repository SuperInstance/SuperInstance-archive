-- Database Query Optimization Script for ActiveLog Production
-- Optimizes PostgreSQL configuration and creates materialized views

-- ============================================================================
-- POSTGRESQL CONFIGURATION OPTIMIZATION
-- ============================================================================

-- Memory settings for production
ALTER SYSTEM SET shared_buffers = '2GB';                    -- 25% of RAM
ALTER SYSTEM SET effective_cache_size = '6GB';              -- 75% of RAM
ALTER SYSTEM SET work_mem = '32MB';                          -- Per connection sort memory
ALTER SYSTEM SET maintenance_work_mem = '512MB';            -- Maintenance operations
ALTER SYSTEM SET wal_buffers = '64MB';                      -- WAL write buffer

-- Connection settings
ALTER SYSTEM SET max_connections = '200';                   -- Maximum connections
ALTER SYSTEM SET max_prepared_transactions = '50';         -- For 2PC
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements,auto_explain';

-- Query optimization
ALTER SYSTEM SET random_page_cost = '1.1';                 -- SSD optimized
ALTER SYSTEM SET effective_io_concurrency = '200';         -- SSD concurrent I/O
ALTER SYSTEM SET default_statistics_target = '100';        -- Query planner statistics
ALTER SYSTEM SET constraint_exclusion = 'partition';       -- Partition pruning

-- Checkpoint and WAL settings
ALTER SYSTEM SET checkpoint_completion_target = '0.9';     -- Spread checkpoints
ALTER SYSTEM SET checkpoint_timeout = '15min';             -- Checkpoint frequency
ALTER SYSTEM SET max_wal_size = '4GB';                     -- WAL size limit
ALTER SYSTEM SET min_wal_size = '1GB';                     -- WAL size minimum
ALTER SYSTEM SET wal_level = 'replica';                    -- Replication support
ALTER SYSTEM SET archive_mode = 'on';                      -- Enable archiving
ALTER SYSTEM SET archive_command = '/opt/activelog/scripts/wal_archive.sh %p %f';

-- Autovacuum optimization
ALTER SYSTEM SET autovacuum_max_workers = '4';             -- Concurrent vacuum workers
ALTER SYSTEM SET autovacuum_vacuum_scale_factor = '0.1';   -- Vacuum trigger threshold
ALTER SYSTEM SET autovacuum_analyze_scale_factor = '0.05'; -- Analyze trigger threshold
ALTER SYSTEM SET autovacuum_work_mem = '256MB';            -- Memory for vacuum operations

-- Logging configuration
ALTER SYSTEM SET log_destination = 'jsonlog';              -- JSON logging
ALTER SYSTEM SET log_min_duration_statement = '1000ms';    -- Log slow queries
ALTER SYSTEM SET log_checkpoints = 'on';                   -- Log checkpoints
ALTER SYSTEM SET log_connections = 'on';                   -- Log connections
ALTER SYSTEM SET log_disconnections = 'on';                -- Log disconnections
ALTER SYSTEM SET log_lock_waits = 'on';                    -- Log lock waits
ALTER SYSTEM SET log_statement = 'ddl';                    -- Log DDL statements
ALTER SYSTEM SET log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h,correlation_id=%x ';

-- Performance monitoring
ALTER SYSTEM SET track_activities = 'on';                  -- Track running queries
ALTER SYSTEM SET track_counts = 'on';                      -- Track table statistics
ALTER SYSTEM SET track_io_timing = 'on';                   -- Track I/O timing
ALTER SYSTEM SET track_functions = 'all';                  -- Track function calls
ALTER SYSTEM SET pg_stat_statements.track = 'all';         -- Track all statements
ALTER SYSTEM SET pg_stat_statements.max = '10000';         -- Statement history size
ALTER SYSTEM SET auto_explain.log_min_duration = '5000ms'; -- Auto explain slow queries
ALTER SYSTEM SET auto_explain.log_analyze = 'on';          -- Include actual times

-- Apply configuration changes (requires restart)
SELECT pg_reload_conf();

-- ============================================================================
-- MATERIALIZED VIEWS FOR PERFORMANCE
-- ============================================================================

-- User file statistics
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_user_file_stats AS
SELECT 
    u.id as user_id,
    u.username,
    COUNT(f.id) as total_files,
    SUM(f.file_size) as total_size,
    COUNT(CASE WHEN f.processing_status = 'completed' THEN 1 END) as completed_files,
    COUNT(CASE WHEN f.processing_status = 'processing' THEN 1 END) as processing_files,
    COUNT(CASE WHEN f.processing_status = 'failed' THEN 1 END) as failed_files,
    COUNT(CASE WHEN f.created_at >= NOW() - INTERVAL '30 days' THEN 1 END) as recent_files,
    MAX(f.created_at) as last_upload,
    AVG(f.file_size) as avg_file_size
FROM users u
LEFT JOIN files f ON u.id = f.user_id AND f.deleted_at IS NULL
GROUP BY u.id, u.username;

-- Create unique index for fast refreshes
CREATE UNIQUE INDEX idx_mv_user_file_stats_user_id ON mv_user_file_stats (user_id);

-- File type statistics
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_file_type_stats AS
SELECT 
    COALESCE(mime_type, 'unknown') as file_type,
    COUNT(*) as file_count,
    SUM(file_size) as total_size,
    AVG(file_size) as avg_size,
    MAX(file_size) as max_size,
    MIN(file_size) as min_size,
    COUNT(CASE WHEN processing_status = 'completed' THEN 1 END) as completed_count,
    COUNT(CASE WHEN processing_status = 'failed' THEN 1 END) as failed_count,
    ROUND(AVG(CASE WHEN processing_status = 'completed' THEN 
        EXTRACT(EPOCH FROM (updated_at - created_at)) END), 2) as avg_processing_time
FROM files 
WHERE deleted_at IS NULL
GROUP BY mime_type;

-- Create unique index
CREATE UNIQUE INDEX idx_mv_file_type_stats_type ON mv_file_type_stats (file_type);

-- Daily usage statistics
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_daily_usage_stats AS
SELECT 
    DATE(created_at) as usage_date,
    COUNT(DISTINCT user_id) as active_users,
    COUNT(*) as total_uploads,
    SUM(file_size) as total_bytes,
    COUNT(CASE WHEN processing_status = 'completed' THEN 1 END) as successful_uploads,
    COUNT(CASE WHEN processing_status = 'failed' THEN 1 END) as failed_uploads,
    AVG(file_size) as avg_file_size,
    COUNT(DISTINCT 
        CASE WHEN mime_type LIKE 'image/%' THEN user_id END) as users_uploading_images,
    COUNT(DISTINCT 
        CASE WHEN mime_type LIKE 'video/%' THEN user_id END) as users_uploading_videos,
    COUNT(DISTINCT 
        CASE WHEN mime_type LIKE 'audio/%' THEN user_id END) as users_uploading_audio
FROM files 
WHERE created_at >= CURRENT_DATE - INTERVAL '90 days'
AND deleted_at IS NULL
GROUP BY DATE(created_at);

-- Create unique index
CREATE UNIQUE INDEX idx_mv_daily_usage_stats_date ON mv_daily_usage_stats (usage_date);

-- AI processing performance stats
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_ai_processing_stats AS
SELECT 
    job_type,
    status,
    COUNT(*) as job_count,
    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_duration_seconds,
    MIN(EXTRACT(EPOCH FROM (completed_at - started_at))) as min_duration_seconds,
    MAX(EXTRACT(EPOCH FROM (completed_at - started_at))) as max_duration_seconds,
    COUNT(CASE WHEN created_at >= NOW() - INTERVAL '24 hours' THEN 1 END) as jobs_last_24h,
    COUNT(CASE WHEN created_at >= NOW() - INTERVAL '7 days' THEN 1 END) as jobs_last_week,
    AVG(CASE WHEN created_at >= NOW() - INTERVAL '24 hours' 
        THEN EXTRACT(EPOCH FROM (completed_at - started_at)) END) as avg_duration_24h
FROM ai_processing_jobs 
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY job_type, status;

-- Create unique index
CREATE UNIQUE INDEX idx_mv_ai_processing_stats_type_status 
ON mv_ai_processing_stats (job_type, status);

-- Popular search terms
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_search_analytics AS
SELECT 
    search_term,
    COUNT(*) as search_count,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(CASE WHEN result_count > 0 THEN 1 END) as searches_with_results,
    AVG(result_count) as avg_results,
    AVG(search_duration_ms) as avg_duration_ms,
    DATE_TRUNC('week', created_at) as search_week
FROM search_logs 
WHERE created_at >= CURRENT_DATE - INTERVAL '90 days'
AND search_term IS NOT NULL 
AND search_term != ''
GROUP BY search_term, DATE_TRUNC('week', created_at)
HAVING COUNT(*) >= 5; -- Only include terms searched at least 5 times

-- Create indexes for search analytics
CREATE INDEX idx_mv_search_analytics_term ON mv_search_analytics (search_term);
CREATE INDEX idx_mv_search_analytics_week ON mv_search_analytics (search_week);
CREATE INDEX idx_mv_search_analytics_count ON mv_search_analytics (search_count DESC);

-- ============================================================================
-- REFRESH FUNCTIONS FOR MATERIALIZED VIEWS
-- ============================================================================

-- Function to refresh all materialized views
CREATE OR REPLACE FUNCTION refresh_all_materialized_views()
RETURNS void AS $$
BEGIN
    -- Refresh concurrently to avoid blocking reads
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_user_file_stats;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_file_type_stats;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_usage_stats;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_ai_processing_stats;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_search_analytics;
    
    -- Log the refresh
    INSERT INTO maintenance_log (operation, status, completed_at, details)
    VALUES ('refresh_materialized_views', 'completed', NOW(), 
            'All materialized views refreshed successfully');
END;
$$ LANGUAGE plpgsql;

-- Function to refresh views based on data age
CREATE OR REPLACE FUNCTION refresh_materialized_views_if_stale()
RETURNS void AS $$
DECLARE
    view_name text;
    last_refresh timestamp;
    refresh_needed boolean := false;
BEGIN
    -- Check each materialized view's last refresh time
    FOR view_name IN 
        SELECT matviewname FROM pg_matviews 
        WHERE schemaname = 'public' 
        AND matviewname LIKE 'mv_%'
    LOOP
        -- Get last refresh time from pg_stat_user_tables
        SELECT stats_reset INTO last_refresh 
        FROM pg_stat_user_tables 
        WHERE relname = view_name;
        
        -- Refresh if older than 1 hour
        IF last_refresh IS NULL OR last_refresh < NOW() - INTERVAL '1 hour' THEN
            EXECUTE 'REFRESH MATERIALIZED VIEW CONCURRENTLY ' || view_name;
            refresh_needed := true;
        END IF;
    END LOOP;
    
    -- Log if any refreshes were performed
    IF refresh_needed THEN
        INSERT INTO maintenance_log (operation, status, completed_at, details)
        VALUES ('conditional_refresh_materialized_views', 'completed', NOW(), 
                'Stale materialized views refreshed');
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- PARTITIONING FOR LARGE TABLES
-- ============================================================================

-- Partition activity_logs by date (if table exists and is large)
DO $$
DECLARE
    table_size bigint;
    partition_name text;
    start_date date;
    end_date date;
BEGIN
    -- Check if activity_logs table exists and is large enough to partition
    SELECT pg_total_relation_size('activity_logs') INTO table_size;
    
    IF table_size > 1073741824 THEN -- 1GB
        -- Create partitioned table for activity_logs
        EXECUTE '
        CREATE TABLE activity_logs_partitioned (
            LIKE activity_logs INCLUDING ALL
        ) PARTITION BY RANGE (created_at)';
        
        -- Create monthly partitions for the last year and next 6 months
        FOR i IN -12..6 LOOP
            start_date := DATE_TRUNC('month', CURRENT_DATE + (i || ' month')::interval);
            end_date := start_date + INTERVAL '1 month';
            partition_name := 'activity_logs_' || TO_CHAR(start_date, 'YYYY_MM');
            
            EXECUTE format('
                CREATE TABLE %I PARTITION OF activity_logs_partitioned
                FOR VALUES FROM (%L) TO (%L)',
                partition_name, start_date, end_date);
        END LOOP;
        
        -- Create default partition for other dates
        EXECUTE 'CREATE TABLE activity_logs_default PARTITION OF activity_logs_partitioned DEFAULT';
        
        -- Note: Manual migration of data would be needed
        INSERT INTO maintenance_log (operation, status, completed_at, details)
        VALUES ('create_activity_logs_partitions', 'completed', NOW(), 
                'Partitioned table structure created');
    END IF;
END;
$$;

-- ============================================================================
-- VACUUM AND ANALYZE OPTIMIZATION
-- ============================================================================

-- Create function for intelligent vacuum
CREATE OR REPLACE FUNCTION smart_vacuum_analyze()
RETURNS void AS $$
DECLARE
    table_record record;
    vacuum_threshold numeric;
    analyze_threshold numeric;
BEGIN
    -- Get tables that need vacuum or analyze
    FOR table_record IN
        SELECT 
            schemaname,
            tablename,
            n_dead_tup,
            n_tup_ins + n_tup_upd + n_tup_del as total_changes,
            pg_stat_get_last_vacuum_time(c.oid) as last_vacuum,
            pg_stat_get_last_analyze_time(c.oid) as last_analyze
        FROM pg_stat_user_tables s
        JOIN pg_class c ON c.relname = s.tablename
        WHERE schemaname = 'public'
    LOOP
        -- Calculate thresholds based on table size
        vacuum_threshold := GREATEST(50, table_record.total_changes * 0.2);
        analyze_threshold := GREATEST(50, table_record.total_changes * 0.1);
        
        -- Vacuum if needed
        IF table_record.n_dead_tup > vacuum_threshold 
           OR table_record.last_vacuum < NOW() - INTERVAL '24 hours' THEN
            EXECUTE format('VACUUM (ANALYZE) %I.%I', 
                          table_record.schemaname, table_record.tablename);
        -- Analyze if needed
        ELSIF table_record.total_changes > analyze_threshold 
              OR table_record.last_analyze < NOW() - INTERVAL '6 hours' THEN
            EXECUTE format('ANALYZE %I.%I', 
                          table_record.schemaname, table_record.tablename);
        END IF;
    END LOOP;
    
    INSERT INTO maintenance_log (operation, status, completed_at, details)
    VALUES ('smart_vacuum_analyze', 'completed', NOW(), 
            'Smart vacuum and analyze completed');
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- QUERY PERFORMANCE MONITORING
-- ============================================================================

-- View for slow queries
CREATE OR REPLACE VIEW slow_queries AS
SELECT 
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    max_exec_time,
    min_exec_time,
    stddev_exec_time,
    rows,
    100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
FROM pg_stat_statements 
WHERE mean_exec_time > 1000  -- Queries taking more than 1 second on average
ORDER BY mean_exec_time DESC;

-- View for cache hit ratio monitoring
CREATE OR REPLACE VIEW cache_hit_ratios AS
SELECT 
    'index hit rate' AS name,
    (sum(idx_blks_hit)) / nullif(sum(idx_blks_hit + idx_blks_read), 0) AS ratio
FROM pg_statio_user_indexes
UNION ALL
SELECT 
    'table hit rate' AS name,
    sum(heap_blks_hit) / nullif(sum(heap_blks_hit + heap_blks_read), 0) AS ratio
FROM pg_statio_user_tables;

-- View for table and index sizes
CREATE OR REPLACE VIEW table_sizes AS
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - 
                   pg_relation_size(schemaname||'.'||tablename)) AS index_size,
    pg_total_relation_size(schemaname||'.'||tablename) AS bytes_total
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY bytes_total DESC;

-- ============================================================================
-- MAINTENANCE SCHEDULING
-- ============================================================================

-- Create maintenance log table if it doesn't exist
CREATE TABLE IF NOT EXISTS maintenance_log (
    id SERIAL PRIMARY KEY,
    operation TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    details TEXT,
    error_message TEXT
);

-- Create index on maintenance log
CREATE INDEX IF NOT EXISTS idx_maintenance_log_operation_date 
ON maintenance_log (operation, started_at DESC);

\echo 'Query optimization setup completed!'
\echo 'Remember to:'
\echo '1. Restart PostgreSQL to apply system configuration changes'
\echo '2. Schedule regular materialized view refreshes'
\echo '3. Schedule smart_vacuum_analyze() to run during low-traffic periods'
\echo '4. Monitor slow_queries view regularly'
\echo '5. Check cache_hit_ratios - should be > 95%'