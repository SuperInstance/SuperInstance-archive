-- Database Optimization Script: Index Creation for ActiveLog Production
-- This script creates comprehensive indexes for optimal query performance

-- Enable timing for performance monitoring
\timing on

-- Set work_mem for index creation
SET work_mem = '256MB';
SET maintenance_work_mem = '1GB';

BEGIN;

-- ============================================================================
-- CORE TABLES INDEXES
-- ============================================================================

-- Users table indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email_lower 
    ON users (LOWER(email));

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_username_lower 
    ON users (LOWER(username));

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_created_at 
    ON users (created_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_last_login 
    ON users (last_login_at) WHERE last_login_at IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_status_active 
    ON users (status, created_at) WHERE status = 'active';

-- Files table indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_user_id_created 
    ON files (user_id, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_hash 
    ON files (file_hash) WHERE file_hash IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_size 
    ON files (file_size);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_mimetype 
    ON files (mime_type);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_path_gin 
    ON files USING gin(to_tsvector('english', file_path));

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_name_gin 
    ON files USING gin(to_tsvector('english', original_name));

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_status_processing 
    ON files (processing_status, created_at) 
    WHERE processing_status IN ('pending', 'processing');

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_modified_at 
    ON files (modified_at DESC) WHERE modified_at > created_at;

-- Composite index for file queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_composite_main 
    ON files (user_id, processing_status, created_at DESC) 
    WHERE deleted_at IS NULL;

-- ============================================================================
-- METADATA AND SEARCH INDEXES
-- ============================================================================

-- File metadata indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_metadata_file_id 
    ON file_metadata (file_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_metadata_key_value 
    ON file_metadata (metadata_key, metadata_value);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_metadata_tags_gin 
    ON file_metadata USING gin(tags) WHERE tags IS NOT NULL;

-- Full-text search index
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_metadata_content_fts 
    ON file_metadata USING gin(to_tsvector('english', 
        COALESCE(extracted_text, '') || ' ' || 
        COALESCE(metadata_value::text, '')));

-- File relationships indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_relationships_parent 
    ON file_relationships (parent_file_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_relationships_child 
    ON file_relationships (child_file_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_relationships_type 
    ON file_relationships (relationship_type);

-- ============================================================================
-- AI AND PROCESSING INDEXES
-- ============================================================================

-- AI processing jobs indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ai_jobs_status_created 
    ON ai_processing_jobs (status, created_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ai_jobs_file_id 
    ON ai_processing_jobs (file_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ai_jobs_user_id 
    ON ai_processing_jobs (user_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ai_jobs_job_type 
    ON ai_processing_jobs (job_type, status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ai_jobs_priority_created 
    ON ai_processing_jobs (priority DESC, created_at) 
    WHERE status IN ('pending', 'running');

-- AI results indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ai_results_file_id_type 
    ON ai_results (file_id, result_type);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ai_results_confidence 
    ON ai_results (confidence DESC) WHERE confidence > 0.5;

-- Vector similarity index (if using pgvector)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ai_embeddings_vector_cosine 
    ON ai_embeddings USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 100);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ai_embeddings_file_id 
    ON ai_embeddings (file_id);

-- ============================================================================
-- NOTIFICATIONS AND ACTIVITY INDEXES
-- ============================================================================

-- Notifications indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notifications_user_unread 
    ON notifications (user_id, read_at, created_at DESC) 
    WHERE read_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notifications_type_created 
    ON notifications (notification_type, created_at DESC);

-- Activity logs indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_activity_logs_user_created 
    ON activity_logs (user_id, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_activity_logs_action_created 
    ON activity_logs (action, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_activity_logs_resource 
    ON activity_logs (resource_type, resource_id);

-- Correlation ID index for tracing
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_activity_logs_correlation 
    ON activity_logs (correlation_id) WHERE correlation_id IS NOT NULL;

-- ============================================================================
-- SESSION AND AUTHENTICATION INDEXES
-- ============================================================================

-- User sessions indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_sessions_user_active 
    ON user_sessions (user_id, expires_at) 
    WHERE expires_at > NOW();

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_sessions_token_hash 
    ON user_sessions (session_token_hash);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_sessions_ip_created 
    ON user_sessions (ip_address, created_at DESC);

-- API keys indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_api_keys_user_active 
    ON api_keys (user_id, is_active) WHERE is_active = true;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_api_keys_key_hash 
    ON api_keys (key_hash);

-- ============================================================================
-- ANALYTICS AND METRICS INDEXES
-- ============================================================================

-- Usage metrics indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_usage_metrics_user_date 
    ON usage_metrics (user_id, metric_date DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_usage_metrics_type_date 
    ON usage_metrics (metric_type, metric_date DESC);

-- Performance metrics indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_performance_metrics_created 
    ON performance_metrics (created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_performance_metrics_service 
    ON performance_metrics (service_name, created_at DESC);

-- ============================================================================
-- BACKUP AND COMPLIANCE INDEXES
-- ============================================================================

-- Audit trail indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_trail_table_action 
    ON audit_trail (table_name, action, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_trail_user_created 
    ON audit_trail (user_id, created_at DESC) WHERE user_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_trail_correlation 
    ON audit_trail (correlation_id) WHERE correlation_id IS NOT NULL;

-- Backup records indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_backup_records_status_created 
    ON backup_records (status, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_backup_records_type_created 
    ON backup_records (backup_type, created_at DESC);

-- ============================================================================
-- PARTIAL INDEXES FOR COMMON QUERIES
-- ============================================================================

-- Active files only
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_active_user_created 
    ON files (user_id, created_at DESC) 
    WHERE deleted_at IS NULL AND processing_status = 'completed';

-- Recent activity (last 30 days)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_activity_recent 
    ON activity_logs (user_id, action, created_at DESC) 
    WHERE created_at > (NOW() - INTERVAL '30 days');

-- Failed processing jobs
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ai_jobs_failed 
    ON ai_processing_jobs (created_at DESC, error_message) 
    WHERE status = 'failed';

-- Large files
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_large 
    ON files (file_size DESC, created_at DESC) 
    WHERE file_size > 100 * 1024 * 1024; -- > 100MB

-- ============================================================================
-- EXPRESSION INDEXES
-- ============================================================================

-- Case-insensitive file name search
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_name_lower 
    ON files (LOWER(original_name));

-- Date extraction indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_created_date 
    ON files (DATE(created_at));

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_created_month 
    ON files (DATE_TRUNC('month', created_at));

-- File extension index
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_extension 
    ON files (LOWER(SUBSTRING(original_name FROM '\.([^.]*)$'))) 
    WHERE original_name ~ '\.[^.]+$';

-- ============================================================================
-- COVERING INDEXES FOR COMMON QUERIES
-- ============================================================================

-- File list with metadata (covering index)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_list_covering 
    ON files (user_id, created_at DESC) 
    INCLUDE (original_name, file_size, mime_type, processing_status);

-- User dashboard covering index
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_dashboard_covering 
    ON files (user_id, processing_status) 
    INCLUDE (original_name, file_size, created_at, modified_at);

-- ============================================================================
-- STATISTICS UPDATE
-- ============================================================================

-- Analyze all tables to update statistics
ANALYZE users;
ANALYZE files;
ANALYZE file_metadata;
ANALYZE file_relationships;
ANALYZE ai_processing_jobs;
ANALYZE ai_results;
ANALYZE ai_embeddings;
ANALYZE notifications;
ANALYZE activity_logs;
ANALYZE user_sessions;
ANALYZE api_keys;
ANALYZE usage_metrics;
ANALYZE performance_metrics;
ANALYZE audit_trail;
ANALYZE backup_records;

COMMIT;

-- ============================================================================
-- INDEX USAGE MONITORING QUERIES
-- ============================================================================

-- Query to monitor index usage
/*
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_tup_read,
    idx_tup_fetch,
    idx_scan,
    CASE WHEN idx_scan = 0 THEN 'Unused'
         WHEN idx_scan < 100 THEN 'Low Usage'
         ELSE 'Active'
    END as usage_status
FROM pg_stat_user_indexes 
ORDER BY idx_scan ASC;
*/

-- Query to find missing indexes
/*
SELECT 
    schemaname,
    tablename,
    seq_scan,
    seq_tup_read,
    seq_tup_read / seq_scan as avg_seq_read,
    idx_scan,
    idx_tup_fetch
FROM pg_stat_user_tables 
WHERE seq_scan > 0 
AND seq_tup_read / seq_scan > 100
ORDER BY seq_tup_read DESC;
*/

-- Reset timing
\timing off

-- Set work_mem back to default
RESET work_mem;
RESET maintenance_work_mem;

\echo 'Index creation completed successfully!'
\echo 'Run ANALYZE on your tables to update query planner statistics.'
\echo 'Monitor index usage with pg_stat_user_indexes view.'