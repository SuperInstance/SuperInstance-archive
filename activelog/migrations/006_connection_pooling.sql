-- Migration 006: Add database connection pooling
-- This migration sets up pgBouncer configuration and connection management

-- Create connection pool configuration table
CREATE TABLE IF NOT EXISTS connection_pool_config (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    pool_name VARCHAR(100) NOT NULL UNIQUE,
    database_name VARCHAR(100) NOT NULL,
    pool_mode VARCHAR(20) DEFAULT 'transaction', -- 'session', 'transaction', 'statement'
    pool_size INTEGER DEFAULT 25,
    reserve_pool INTEGER DEFAULT 5,
    max_client_conn INTEGER DEFAULT 100,
    default_pool_size INTEGER DEFAULT 20,
    min_pool_size INTEGER DEFAULT 10,
    server_round_robin BOOLEAN DEFAULT TRUE,
    server_lifetime INTEGER DEFAULT 3600, -- seconds
    server_idle_timeout INTEGER DEFAULT 600, -- seconds
    query_timeout INTEGER DEFAULT 300, -- seconds
    client_idle_timeout INTEGER DEFAULT 0, -- 0 = disabled
    is_active BOOLEAN DEFAULT TRUE,
    config_params JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default connection pool configurations
INSERT INTO connection_pool_config (
    pool_name, database_name, pool_mode, pool_size, reserve_pool, max_client_conn
) VALUES 
    ('activelog_primary', 'activelog', 'transaction', 25, 5, 100),
    ('activelog_readonly', 'activelog', 'transaction', 15, 3, 50),
    ('activelog_analytics', 'activelog', 'session', 10, 2, 30),
    ('activelog_batch', 'activelog', 'session', 5, 1, 20)
ON CONFLICT (pool_name) DO NOTHING;

-- Create connection pool statistics table
CREATE TABLE IF NOT EXISTS connection_pool_stats (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    pool_name VARCHAR(100) NOT NULL,
    total_requests BIGINT DEFAULT 0,
    total_received BIGINT DEFAULT 0,
    total_sent BIGINT DEFAULT 0,
    total_query_time BIGINT DEFAULT 0, -- microseconds
    avg_query_time FLOAT DEFAULT 0,
    active_clients INTEGER DEFAULT 0,
    waiting_clients INTEGER DEFAULT 0,
    active_servers INTEGER DEFAULT 0,
    idle_servers INTEGER DEFAULT 0,
    used_servers INTEGER DEFAULT 0,
    tested_servers INTEGER DEFAULT 0,
    login_servers INTEGER DEFAULT 0,
    maxwait INTEGER DEFAULT 0,
    maxwait_us BIGINT DEFAULT 0,
    pool_mode VARCHAR(20),
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create connection monitoring table
CREATE TABLE IF NOT EXISTS connection_monitoring (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    database_name VARCHAR(100) NOT NULL,
    application_name VARCHAR(100),
    client_addr INET,
    backend_start TIMESTAMP WITH TIME ZONE,
    state VARCHAR(20), -- 'active', 'idle', 'idle in transaction', 'fastpath function call', 'disabled'
    query_start TIMESTAMP WITH TIME ZONE,
    state_change TIMESTAMP WITH TIME ZONE,
    wait_event_type VARCHAR(50),
    wait_event VARCHAR(100),
    current_query TEXT,
    query_duration INTERVAL,
    connection_duration INTERVAL,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Function to collect connection pool statistics
CREATE OR REPLACE FUNCTION collect_pool_stats()
RETURNS VOID AS $$
BEGIN
    -- Insert current connection statistics
    INSERT INTO connection_monitoring (
        database_name,
        application_name,
        client_addr,
        backend_start,
        state,
        query_start,
        state_change,
        wait_event_type,
        wait_event,
        current_query,
        query_duration,
        connection_duration
    )
    SELECT 
        datname as database_name,
        application_name,
        client_addr,
        backend_start,
        state,
        query_start,
        state_change,
        wait_event_type,
        wait_event,
        CASE 
            WHEN state = 'active' THEN query
            ELSE '<idle>'
        END as current_query,
        CASE 
            WHEN query_start IS NOT NULL THEN NOW() - query_start
            ELSE NULL
        END as query_duration,
        NOW() - backend_start as connection_duration
    FROM pg_stat_activity
    WHERE datname = 'activelog'
    AND pid != pg_backend_pid(); -- Exclude current connection
    
    -- Clean old monitoring data (keep last 24 hours)
    DELETE FROM connection_monitoring 
    WHERE recorded_at < NOW() - INTERVAL '24 hours';
    
    -- Log collection
    INSERT INTO system_logs (log_level, message, details)
    VALUES ('DEBUG', 'Connection pool statistics collected', 
            json_build_object('timestamp', NOW()));
            
EXCEPTION WHEN OTHERS THEN
    INSERT INTO system_logs (log_level, message, details)
    VALUES ('ERROR', 'Failed to collect connection pool statistics', 
            json_build_object('error', SQLERRM));
END $$ LANGUAGE plpgsql;

-- Function to analyze connection patterns
CREATE OR REPLACE FUNCTION analyze_connection_patterns()
RETURNS JSON AS $$
BEGIN
    RETURN (
        SELECT json_build_object(
            'total_connections', COUNT(*),
            'active_connections', COUNT(*) FILTER (WHERE state = 'active'),
            'idle_connections', COUNT(*) FILTER (WHERE state = 'idle'),
            'idle_in_transaction', COUNT(*) FILTER (WHERE state = 'idle in transaction'),
            'avg_connection_duration', AVG(EXTRACT(EPOCH FROM connection_duration)),
            'max_connection_duration', MAX(EXTRACT(EPOCH FROM connection_duration)),
            'long_running_queries', COUNT(*) FILTER (WHERE query_duration > INTERVAL '30 seconds'),
            'applications', json_object_agg(application_name, app_count),
            'client_distribution', json_object_agg(client_addr::text, client_count),
            'wait_events', (
                SELECT json_object_agg(wait_event_type || '.' || wait_event, wait_count)
                FROM (
                    SELECT 
                        COALESCE(wait_event_type, 'none') as wait_event_type,
                        COALESCE(wait_event, 'none') as wait_event,
                        COUNT(*) as wait_count
                    FROM connection_monitoring
                    WHERE recorded_at >= NOW() - INTERVAL '1 hour'
                    GROUP BY wait_event_type, wait_event
                ) wait_stats
            ),
            'query_patterns', (
                SELECT json_agg(json_build_object(
                    'pattern', query_pattern,
                    'count', pattern_count,
                    'avg_duration', avg_duration
                ) ORDER BY pattern_count DESC)
                FROM (
                    SELECT 
                        CASE 
                            WHEN current_query LIKE 'SELECT%' THEN 'SELECT'
                            WHEN current_query LIKE 'INSERT%' THEN 'INSERT'
                            WHEN current_query LIKE 'UPDATE%' THEN 'UPDATE'
                            WHEN current_query LIKE 'DELETE%' THEN 'DELETE'
                            ELSE 'OTHER'
                        END as query_pattern,
                        COUNT(*) as pattern_count,
                        AVG(EXTRACT(EPOCH FROM query_duration)) as avg_duration
                    FROM connection_monitoring
                    WHERE recorded_at >= NOW() - INTERVAL '1 hour'
                    AND current_query != '<idle>'
                    GROUP BY query_pattern
                ) pattern_stats
                LIMIT 10
            )
        )
        FROM (
            SELECT 
                state,
                connection_duration,
                query_duration,
                application_name,
                client_addr,
                COUNT(*) OVER (PARTITION BY application_name) as app_count,
                COUNT(*) OVER (PARTITION BY client_addr) as client_count
            FROM connection_monitoring
            WHERE recorded_at >= NOW() - INTERVAL '1 hour'
        ) conn_stats
    );
END $$ LANGUAGE plpgsql;

-- Function to optimize pool configuration
CREATE OR REPLACE FUNCTION optimize_pool_config()
RETURNS JSON AS $$
DECLARE
    current_stats JSON;
    recommendations JSON;
    avg_connections FLOAT;
    peak_connections INTEGER;
    avg_query_time FLOAT;
BEGIN
    -- Get current connection patterns
    current_stats := analyze_connection_patterns();
    
    -- Calculate recommendations based on usage patterns
    SELECT 
        AVG(total_connections)::FLOAT,
        MAX(total_connections),
        AVG(avg_query_time)::FLOAT
    INTO avg_connections, peak_connections, avg_query_time
    FROM (
        SELECT 
            COUNT(*) as total_connections,
            AVG(EXTRACT(EPOCH FROM query_duration)) as avg_query_time
        FROM connection_monitoring
        WHERE recorded_at >= NOW() - INTERVAL '7 days'
        GROUP BY DATE_TRUNC('hour', recorded_at)
    ) hourly_stats;
    
    -- Generate recommendations
    recommendations := json_build_object(
        'recommended_pool_size', 
        CASE 
            WHEN peak_connections > 50 THEN peak_connections * 1.2
            WHEN peak_connections > 20 THEN peak_connections * 1.5
            ELSE GREATEST(10, peak_connections * 2)
        END,
        'recommended_reserve_pool',
        GREATEST(2, CEIL(peak_connections * 0.2)),
        'recommended_max_client_conn',
        peak_connections * 3,
        'recommended_pool_mode',
        CASE 
            WHEN avg_query_time > 5 THEN 'session'
            ELSE 'transaction'
        END,
        'analysis_period', '7 days',
        'avg_connections_per_hour', avg_connections,
        'peak_connections', peak_connections,
        'avg_query_time_seconds', avg_query_time
    );
    
    -- Log recommendations
    INSERT INTO system_logs (log_level, message, details)
    VALUES ('INFO', 'Connection pool optimization recommendations generated', 
            json_build_object(
                'current_stats', current_stats,
                'recommendations', recommendations
            ));
    
    RETURN json_build_object(
        'current_stats', current_stats,
        'recommendations', recommendations
    );
END $$ LANGUAGE plpgsql;

-- Function to apply pool configuration
CREATE OR REPLACE FUNCTION apply_pool_config(
    pool_name VARCHAR(100),
    new_config JSONB
)
RETURNS VOID AS $$
DECLARE
    config_key TEXT;
    config_value TEXT;
BEGIN
    -- Update the pool configuration
    UPDATE connection_pool_config 
    SET 
        pool_size = COALESCE((new_config->>'pool_size')::INTEGER, pool_size),
        reserve_pool = COALESCE((new_config->>'reserve_pool')::INTEGER, reserve_pool),
        max_client_conn = COALESCE((new_config->>'max_client_conn')::INTEGER, max_client_conn),
        pool_mode = COALESCE(new_config->>'pool_mode', pool_mode),
        server_lifetime = COALESCE((new_config->>'server_lifetime')::INTEGER, server_lifetime),
        server_idle_timeout = COALESCE((new_config->>'server_idle_timeout')::INTEGER, server_idle_timeout),
        query_timeout = COALESCE((new_config->>'query_timeout')::INTEGER, query_timeout),
        config_params = config_params || new_config,
        updated_at = NOW()
    WHERE pool_name = apply_pool_config.pool_name;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Pool configuration not found: %', pool_name;
    END IF;
    
    -- Log configuration change
    INSERT INTO system_logs (log_level, message, details)
    VALUES ('INFO', 'Connection pool configuration updated', 
            json_build_object(
                'pool_name', pool_name,
                'new_config', new_config
            ));
END $$ LANGUAGE plpgsql;

-- Function to generate pgBouncer configuration
CREATE OR REPLACE FUNCTION generate_pgbouncer_config()
RETURNS TEXT AS $$
DECLARE
    config_text TEXT := '';
    pool_record RECORD;
BEGIN
    -- Generate pgBouncer configuration file content
    config_text := config_text || E'[databases]\n';
    
    -- Add database configurations
    FOR pool_record IN 
        SELECT * FROM connection_pool_config WHERE is_active = TRUE
    LOOP
        config_text := config_text || pool_record.pool_name || 
                      ' = host=localhost port=5432 dbname=' || pool_record.database_name ||
                      ' pool_size=' || pool_record.pool_size ||
                      ' reserve_pool=' || pool_record.reserve_pool || E'\n';
    END LOOP;
    
    config_text := config_text || E'\n[pgbouncer]\n';
    config_text := config_text || E'listen_addr = *\n';
    config_text := config_text || E'listen_port = 6432\n';
    config_text := config_text || E'auth_type = md5\n';
    config_text := config_text || E'auth_file = /etc/pgbouncer/userlist.txt\n';
    config_text := config_text || E'admin_users = postgres\n';
    config_text := config_text || E'stats_users = stats\n';
    config_text := config_text || E'pool_mode = transaction\n';
    config_text := config_text || E'server_reset_query = DISCARD ALL\n';
    config_text := config_text || E'max_client_conn = 1000\n';
    config_text := config_text || E'default_pool_size = 25\n';
    config_text := config_text || E'min_pool_size = 10\n';
    config_text := config_text || E'reserve_pool_size = 5\n';
    config_text := config_text || E'reserve_pool_timeout = 5\n';
    config_text := config_text || E'max_db_connections = 100\n';
    config_text := config_text || E'max_user_connections = 100\n';
    config_text := config_text || E'server_round_robin = 1\n';
    config_text := config_text || E'ignore_startup_parameters = extra_float_digits\n';
    config_text := config_text || E'log_connections = 1\n';
    config_text := config_text || E'log_disconnections = 1\n';
    config_text := config_text || E'log_pooler_errors = 1\n';
    config_text := config_text || E'stats_period = 60\n';
    
    RETURN config_text;
END $$ LANGUAGE plpgsql;

-- Function to monitor connection health
CREATE OR REPLACE FUNCTION monitor_connection_health()
RETURNS JSON AS $$
BEGIN
    RETURN (
        SELECT json_build_object(
            'timestamp', NOW(),
            'database_stats', json_build_object(
                'total_connections', numbackends,
                'active_connections', active,
                'idle_connections', idle,
                'idle_in_transaction', idle_in_transaction,
                'commits', xact_commit,
                'rollbacks', xact_rollback,
                'blocks_read', blks_read,
                'blocks_hit', blks_hit,
                'cache_hit_ratio', 
                CASE 
                    WHEN blks_read + blks_hit > 0 
                    THEN (blks_hit::FLOAT / (blks_read + blks_hit) * 100)::NUMERIC(5,2)
                    ELSE 0
                END,
                'temp_files', temp_files,
                'temp_bytes', temp_bytes,
                'deadlocks', deadlocks
            ),
            'long_running_queries', (
                SELECT json_agg(json_build_object(
                    'pid', pid,
                    'duration', EXTRACT(EPOCH FROM (NOW() - query_start)),
                    'state', state,
                    'query', LEFT(query, 100)
                ))
                FROM pg_stat_activity 
                WHERE state = 'active' 
                AND NOW() - query_start > INTERVAL '30 seconds'
                AND pid != pg_backend_pid()
            ),
            'blocking_queries', (
                SELECT json_agg(json_build_object(
                    'blocked_pid', blocked_locks.pid,
                    'blocking_pid', blocking_locks.pid,
                    'blocked_statement', blocked_activity.query,
                    'blocking_statement', blocking_activity.query,
                    'blocking_duration', EXTRACT(EPOCH FROM (NOW() - blocking_activity.query_start))
                ))
                FROM pg_catalog.pg_locks blocked_locks
                JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
                JOIN pg_catalog.pg_locks blocking_locks 
                    ON blocking_locks.locktype = blocked_locks.locktype
                    AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
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
                WHERE NOT blocked_locks.granted
            )
        )
        FROM pg_stat_database 
        WHERE datname = 'activelog'
    );
END $$ LANGUAGE plpgsql;

-- Schedule regular connection monitoring
SELECT cron.schedule('collect-pool-stats', '*/5 * * * *', 'SELECT collect_pool_stats();');
SELECT cron.schedule('monitor-connection-health', '*/10 * * * *', 'INSERT INTO system_logs (log_level, message, details) VALUES (''INFO'', ''Connection health check'', monitor_connection_health());');
SELECT cron.schedule('optimize-pool-config', '0 2 * * 1', 'INSERT INTO system_logs (log_level, message, details) VALUES (''INFO'', ''Pool optimization analysis'', optimize_pool_config());');

-- Create indexes for connection monitoring
CREATE INDEX idx_connection_monitoring_recorded_at ON connection_monitoring(recorded_at DESC);
CREATE INDEX idx_connection_monitoring_state ON connection_monitoring(state);
CREATE INDEX idx_connection_monitoring_app_name ON connection_monitoring(application_name);
CREATE INDEX idx_connection_pool_stats_recorded_at ON connection_pool_stats(recorded_at DESC);
CREATE INDEX idx_connection_pool_stats_pool_name ON connection_pool_stats(pool_name);

-- Create view for current pool status
CREATE OR REPLACE VIEW current_pool_status AS
SELECT 
    cpc.pool_name,
    cpc.database_name,
    cpc.pool_mode,
    cpc.pool_size,
    cpc.max_client_conn,
    cpc.is_active,
    COUNT(cm.id) as current_connections,
    COUNT(cm.id) FILTER (WHERE cm.state = 'active') as active_connections,
    COUNT(cm.id) FILTER (WHERE cm.state = 'idle') as idle_connections,
    AVG(EXTRACT(EPOCH FROM cm.connection_duration)) as avg_connection_duration,
    MAX(EXTRACT(EPOCH FROM cm.connection_duration)) as max_connection_duration
FROM connection_pool_config cpc
LEFT JOIN connection_monitoring cm ON cm.database_name = cpc.database_name
    AND cm.recorded_at >= NOW() - INTERVAL '5 minutes'
GROUP BY cpc.pool_name, cpc.database_name, cpc.pool_mode, cpc.pool_size, cpc.max_client_conn, cpc.is_active;

-- Migration metadata
INSERT INTO migration_history (version, name, applied_at, description) 
VALUES (6, 'connection_pooling', NOW(), 'Implemented database connection pooling with pgBouncer configuration and monitoring');