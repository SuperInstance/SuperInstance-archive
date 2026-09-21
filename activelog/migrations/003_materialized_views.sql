-- Migration 003: Add materialized views for analytics
-- This migration creates optimized materialized views for dashboard analytics and reporting

-- Daily file statistics materialized view
CREATE MATERIALIZED VIEW daily_file_stats AS
SELECT 
    DATE(created_at) as date,
    user_id,
    COUNT(*) as files_created,
    SUM(size) as total_size,
    COUNT(DISTINCT file_type) as unique_types,
    AVG(size) as avg_file_size,
    COUNT(CASE WHEN sync_status = 'synced' THEN 1 END) as synced_files,
    COUNT(CASE WHEN sync_status = 'local' THEN 1 END) as local_files,
    COUNT(CASE WHEN sync_status = 'cloud' THEN 1 END) as cloud_files,
    COUNT(CASE WHEN sync_status = 'error' THEN 1 END) as error_files
FROM files_partitioned
WHERE NOT is_deleted
GROUP BY DATE(created_at), user_id;

-- Create indexes on materialized view
CREATE UNIQUE INDEX idx_daily_file_stats_date_user ON daily_file_stats(date, user_id);
CREATE INDEX idx_daily_file_stats_date ON daily_file_stats(date DESC);
CREATE INDEX idx_daily_file_stats_user ON daily_file_stats(user_id);

-- File type distribution materialized view
CREATE MATERIALIZED VIEW file_type_stats AS
SELECT 
    user_id,
    file_type,
    COUNT(*) as file_count,
    SUM(size) as total_size,
    AVG(size) as avg_size,
    MIN(size) as min_size,
    MAX(size) as max_size,
    COUNT(CASE WHEN created_at >= NOW() - INTERVAL '30 days' THEN 1 END) as recent_count,
    COUNT(CASE WHEN sync_status = 'synced' THEN 1 END) as synced_count,
    MAX(created_at) as last_created
FROM files_partitioned
WHERE NOT is_deleted
GROUP BY user_id, file_type;

CREATE UNIQUE INDEX idx_file_type_stats_user_type ON file_type_stats(user_id, file_type);
CREATE INDEX idx_file_type_stats_count ON file_type_stats(file_count DESC);

-- Search analytics materialized view
CREATE MATERIALIZED VIEW search_analytics AS
SELECT 
    user_id,
    DATE(created_at) as date,
    COUNT(*) as search_count,
    COUNT(DISTINCT query) as unique_queries,
    AVG(result_count) as avg_results,
    COUNT(CASE WHEN result_count = 0 THEN 1 END) as zero_result_searches,
    COUNT(CASE WHEN result_count > 0 THEN 1 END) as successful_searches,
    array_agg(DISTINCT query ORDER BY created_at DESC) FILTER (WHERE query IS NOT NULL) as top_queries
FROM search_history
GROUP BY user_id, DATE(created_at);

CREATE UNIQUE INDEX idx_search_analytics_user_date ON search_analytics(user_id, date);
CREATE INDEX idx_search_analytics_date ON search_analytics(date DESC);

-- Popular search terms materialized view
CREATE MATERIALIZED VIEW popular_search_terms AS
WITH search_words AS (
    SELECT 
        user_id,
        unnest(string_to_array(lower(query), ' ')) as word,
        COUNT(*) as frequency
    FROM search_history
    WHERE created_at >= NOW() - INTERVAL '90 days'
    AND length(trim(query)) > 2
    GROUP BY user_id, unnest(string_to_array(lower(query), ' '))
)
SELECT 
    user_id,
    word,
    SUM(frequency) as total_frequency,
    COUNT(*) as usage_count,
    RANK() OVER (PARTITION BY user_id ORDER BY SUM(frequency) DESC) as rank
FROM search_words
WHERE length(word) > 2
AND word NOT IN ('the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'who', 'boy', 'did', 'has', 'let', 'put', 'say', 'she', 'too', 'use')
GROUP BY user_id, word;

CREATE UNIQUE INDEX idx_popular_search_terms_user_word ON popular_search_terms(user_id, word);
CREATE INDEX idx_popular_search_terms_frequency ON popular_search_terms(total_frequency DESC);

-- User activity summary materialized view
CREATE MATERIALIZED VIEW user_activity_summary AS
SELECT 
    user_id,
    DATE(created_at) as date,
    COUNT(*) as total_activities,
    COUNT(CASE WHEN activity_type = 'file_upload' THEN 1 END) as uploads,
    COUNT(CASE WHEN activity_type = 'file_download' THEN 1 END) as downloads,
    COUNT(CASE WHEN activity_type = 'search' THEN 1 END) as searches,
    COUNT(CASE WHEN activity_type = 'tag_create' THEN 1 END) as tags_created,
    COUNT(CASE WHEN activity_type = 'sync_action' THEN 1 END) as sync_actions,
    COUNT(DISTINCT ip_address) as unique_ips,
    MIN(created_at) as first_activity,
    MAX(created_at) as last_activity,
    EXTRACT(EPOCH FROM (MAX(created_at) - MIN(created_at))) / 60 as session_duration_minutes
FROM user_activities_partitioned
GROUP BY user_id, DATE(created_at);

CREATE UNIQUE INDEX idx_user_activity_summary_user_date ON user_activity_summary(user_id, date);
CREATE INDEX idx_user_activity_summary_date ON user_activity_summary(date DESC);

-- File relationship network view
CREATE MATERIALIZED VIEW file_relationship_network AS
SELECT 
    parent_file_id,
    child_file_id,
    relationship_type,
    strength,
    COUNT(*) OVER (PARTITION BY parent_file_id) as parent_connections,
    COUNT(*) OVER (PARTITION BY child_file_id) as child_connections,
    AVG(strength) OVER (PARTITION BY relationship_type) as avg_type_strength,
    p.user_id as parent_user_id,
    c.user_id as child_user_id,
    p.file_type as parent_type,
    c.file_type as child_type
FROM file_relationships fr
JOIN files_partitioned p ON fr.parent_file_id = p.id
JOIN files_partitioned c ON fr.child_file_id = c.id
WHERE NOT p.is_deleted AND NOT c.is_deleted;

CREATE INDEX idx_file_relationship_network_parent ON file_relationship_network(parent_file_id);
CREATE INDEX idx_file_relationship_network_child ON file_relationship_network(child_file_id);
CREATE INDEX idx_file_relationship_network_strength ON file_relationship_network(strength DESC);

-- Storage analytics materialized view
CREATE MATERIALIZED VIEW storage_analytics AS
SELECT 
    user_id,
    COUNT(*) as total_files,
    SUM(size) as total_size,
    AVG(size) as avg_file_size,
    MAX(size) as largest_file,
    COUNT(CASE WHEN sync_status = 'local' THEN 1 END) as local_only_files,
    SUM(CASE WHEN sync_status = 'local' THEN size ELSE 0 END) as local_only_size,
    COUNT(CASE WHEN sync_status = 'cloud' THEN 1 END) as cloud_only_files,
    SUM(CASE WHEN sync_status = 'cloud' THEN size ELSE 0 END) as cloud_only_size,
    COUNT(CASE WHEN sync_status = 'synced' THEN 1 END) as synced_files,
    SUM(CASE WHEN sync_status = 'synced' THEN size ELSE 0 END) as synced_size,
    COUNT(CASE WHEN created_at >= NOW() - INTERVAL '7 days' THEN 1 END) as files_last_week,
    SUM(CASE WHEN created_at >= NOW() - INTERVAL '7 days' THEN size ELSE 0 END) as size_last_week,
    COUNT(CASE WHEN accessed_at >= NOW() - INTERVAL '7 days' THEN 1 END) as accessed_last_week,
    COUNT(CASE WHEN modified_at >= NOW() - INTERVAL '7 days' THEN 1 END) as modified_last_week
FROM files_partitioned
WHERE NOT is_deleted
GROUP BY user_id;

CREATE UNIQUE INDEX idx_storage_analytics_user ON storage_analytics(user_id);
CREATE INDEX idx_storage_analytics_total_size ON storage_analytics(total_size DESC);

-- Tag usage analytics materialized view
CREATE MATERIALIZED VIEW tag_analytics AS
SELECT 
    t.user_id,
    t.id as tag_id,
    t.name as tag_name,
    t.color as tag_color,
    COUNT(ft.file_id) as file_count,
    SUM(f.size) as total_file_size,
    MAX(ft.created_at) as last_used,
    MIN(ft.created_at) as first_used,
    COUNT(CASE WHEN ft.created_at >= NOW() - INTERVAL '30 days' THEN 1 END) as recent_usage,
    array_agg(DISTINCT f.file_type) as associated_file_types
FROM tags t
LEFT JOIN file_tags ft ON t.id = ft.tag_id
LEFT JOIN files_partitioned f ON ft.file_id = f.id AND NOT f.is_deleted
GROUP BY t.user_id, t.id, t.name, t.color;

CREATE UNIQUE INDEX idx_tag_analytics_tag_id ON tag_analytics(tag_id);
CREATE INDEX idx_tag_analytics_user_id ON tag_analytics(user_id);
CREATE INDEX idx_tag_analytics_file_count ON tag_analytics(file_count DESC);

-- Performance monitoring view
CREATE MATERIALIZED VIEW performance_metrics AS
SELECT 
    DATE(NOW()) as metric_date,
    'files' as table_name,
    COUNT(*) as row_count,
    pg_size_pretty(pg_total_relation_size('files_partitioned')) as table_size,
    pg_size_pretty(pg_indexes_size('files_partitioned')) as index_size
FROM files_partitioned
UNION ALL
SELECT 
    DATE(NOW()),
    'file_embeddings',
    COUNT(*),
    pg_size_pretty(pg_total_relation_size('file_embeddings_partitioned')),
    pg_size_pretty(pg_indexes_size('file_embeddings_partitioned'))
FROM file_embeddings_partitioned
UNION ALL
SELECT 
    DATE(NOW()),
    'user_activities',
    COUNT(*),
    pg_size_pretty(pg_total_relation_size('user_activities_partitioned')),
    pg_size_pretty(pg_indexes_size('user_activities_partitioned'))
FROM user_activities_partitioned;

-- Function to refresh all materialized views
CREATE OR REPLACE FUNCTION refresh_analytics_views()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY daily_file_stats;
    REFRESH MATERIALIZED VIEW CONCURRENTLY file_type_stats;
    REFRESH MATERIALIZED VIEW CONCURRENTLY search_analytics;
    REFRESH MATERIALIZED VIEW CONCURRENTLY popular_search_terms;
    REFRESH MATERIALIZED VIEW CONCURRENTLY user_activity_summary;
    REFRESH MATERIALIZED VIEW CONCURRENTLY file_relationship_network;
    REFRESH MATERIALIZED VIEW CONCURRENTLY storage_analytics;
    REFRESH MATERIALIZED VIEW CONCURRENTLY tag_analytics;
    REFRESH MATERIALIZED VIEW performance_metrics;
    
    -- Log the refresh
    INSERT INTO system_logs (log_level, message, created_at)
    VALUES ('INFO', 'Analytics materialized views refreshed', NOW());
END $$ LANGUAGE plpgsql;

-- Schedule automatic refresh of materialized views
SELECT cron.schedule('refresh-analytics', '0 1 * * *', 'SELECT refresh_analytics_views();');
SELECT cron.schedule('refresh-performance-metrics', '0 */6 * * *', 'REFRESH MATERIALIZED VIEW performance_metrics;');

-- Create system logs table if it doesn't exist
CREATE TABLE IF NOT EXISTS system_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    log_level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    details JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create migration history table if it doesn't exist
CREATE TABLE IF NOT EXISTS migration_history (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    version INTEGER NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    description TEXT,
    checksum VARCHAR(64)
);

-- Analytics helper functions
CREATE OR REPLACE FUNCTION get_user_dashboard_stats(p_user_id UUID)
RETURNS JSON AS $$
DECLARE
    result JSON;
BEGIN
    SELECT json_build_object(
        'total_files', COALESCE(total_files, 0),
        'total_size', COALESCE(total_size, 0),
        'files_last_week', COALESCE(files_last_week, 0),
        'sync_status', json_build_object(
            'synced', COALESCE(synced_files, 0),
            'local', COALESCE(local_only_files, 0),
            'cloud', COALESCE(cloud_only_files, 0)
        ),
        'recent_activity', (
            SELECT json_agg(json_build_object(
                'date', date,
                'files_created', files_created,
                'total_size', total_size
            ) ORDER BY date DESC)
            FROM daily_file_stats 
            WHERE user_id = p_user_id 
            AND date >= NOW() - INTERVAL '7 days'
        ),
        'top_file_types', (
            SELECT json_agg(json_build_object(
                'type', file_type,
                'count', file_count,
                'size', total_size
            ) ORDER BY file_count DESC)
            FROM file_type_stats 
            WHERE user_id = p_user_id 
            LIMIT 5
        )
    ) INTO result
    FROM storage_analytics
    WHERE user_id = p_user_id;
    
    RETURN COALESCE(result, '{}'::json);
END $$ LANGUAGE plpgsql;

-- Function to get search insights
CREATE OR REPLACE FUNCTION get_search_insights(p_user_id UUID)
RETURNS JSON AS $$
BEGIN
    RETURN (
        SELECT json_build_object(
            'popular_terms', (
                SELECT json_agg(json_build_object(
                    'term', word,
                    'frequency', total_frequency
                ) ORDER BY total_frequency DESC)
                FROM popular_search_terms 
                WHERE user_id = p_user_id 
                AND rank <= 10
            ),
            'search_trends', (
                SELECT json_agg(json_build_object(
                    'date', date,
                    'search_count', search_count,
                    'success_rate', CASE WHEN search_count > 0 
                        THEN successful_searches::float / search_count 
                        ELSE 0 END
                ) ORDER BY date DESC)
                FROM search_analytics 
                WHERE user_id = p_user_id 
                AND date >= NOW() - INTERVAL '30 days'
            )
        )
    );
END $$ LANGUAGE plpgsql;

-- Migration metadata
INSERT INTO migration_history (version, name, applied_at, description) 
VALUES (3, 'materialized_views', NOW(), 'Added materialized views for analytics and dashboard reporting');