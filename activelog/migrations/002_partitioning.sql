-- Migration 002: Implement database partitioning for files table
-- This migration creates partitioned tables for better performance with large datasets

-- Create partitioned files table
CREATE TABLE files_partitioned (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    file_type VARCHAR(50),
    mime_type VARCHAR(100),
    size BIGINT DEFAULT 0,
    checksum VARCHAR(64),
    sync_status VARCHAR(20) DEFAULT 'local',
    cloud_id VARCHAR(255),
    local_path TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    version_number INTEGER DEFAULT 1,
    parent_id UUID REFERENCES files_partitioned(id),
    tags TEXT[],
    
    -- Partition key
    CONSTRAINT files_partitioned_pkey PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Create monthly partitions for the last 12 months and next 12 months
DO $$
DECLARE
    start_date DATE;
    end_date DATE;
    partition_name TEXT;
    i INTEGER;
BEGIN
    -- Create partitions for last 12 months
    FOR i IN -12..12 LOOP
        start_date := DATE_TRUNC('month', NOW() + INTERVAL '1 month' * i);
        end_date := start_date + INTERVAL '1 month';
        partition_name := 'files_' || TO_CHAR(start_date, 'YYYY_MM');
        
        EXECUTE format('CREATE TABLE %I PARTITION OF files_partitioned 
                       FOR VALUES FROM (%L) TO (%L)', 
                       partition_name, start_date, end_date);
                       
        -- Add indexes to each partition
        EXECUTE format('CREATE INDEX idx_%I_user_id ON %I(user_id)', 
                       partition_name, partition_name);
        EXECUTE format('CREATE INDEX idx_%I_sync_status ON %I(sync_status)', 
                       partition_name, partition_name);
        EXECUTE format('CREATE INDEX idx_%I_file_type ON %I(file_type)', 
                       partition_name, partition_name);
        EXECUTE format('CREATE INDEX idx_%I_path_trgm ON %I USING gin(path gin_trgm_ops)', 
                       partition_name, partition_name);
    END LOOP;
END $$;

-- Create default partition for future dates
CREATE TABLE files_default PARTITION OF files_partitioned DEFAULT;

-- Create partitioned file_embeddings table
CREATE TABLE file_embeddings_partitioned (
    id UUID DEFAULT gen_random_uuid(),
    file_id UUID NOT NULL,
    embedding_model VARCHAR(100) NOT NULL,
    embedding_vector VECTOR(1536),
    chunk_index INTEGER DEFAULT 0,
    chunk_text TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT file_embeddings_partitioned_pkey PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Create quarterly partitions for embeddings (they're larger)
DO $$
DECLARE
    start_date DATE;
    end_date DATE;
    partition_name TEXT;
    i INTEGER;
BEGIN
    FOR i IN -4..4 LOOP
        start_date := DATE_TRUNC('quarter', NOW() + INTERVAL '3 months' * i);
        end_date := start_date + INTERVAL '3 months';
        partition_name := 'file_embeddings_' || TO_CHAR(start_date, 'YYYY_Q"Q"');
        
        EXECUTE format('CREATE TABLE %I PARTITION OF file_embeddings_partitioned 
                       FOR VALUES FROM (%L) TO (%L)', 
                       partition_name, start_date, end_date);
                       
        -- Add vector similarity index to each partition
        EXECUTE format('CREATE INDEX idx_%I_embedding_vector ON %I USING ivfflat (embedding_vector vector_cosine_ops)', 
                       partition_name, partition_name);
        EXECUTE format('CREATE INDEX idx_%I_file_id ON %I(file_id)', 
                       partition_name, partition_name);
        EXECUTE format('CREATE INDEX idx_%I_model ON %I(embedding_model)', 
                       partition_name, partition_name);
    END LOOP;
END $$;

-- Create default partition for embeddings
CREATE TABLE file_embeddings_default PARTITION OF file_embeddings_partitioned DEFAULT;

-- Create partitioned user_activities table for audit logs
CREATE TABLE user_activities_partitioned (
    id UUID DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    activity_type VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    details JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT user_activities_partitioned_pkey PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Create weekly partitions for activity logs (high volume)
DO $$
DECLARE
    start_date DATE;
    end_date DATE;
    partition_name TEXT;
    i INTEGER;
BEGIN
    FOR i IN -8..8 LOOP
        start_date := DATE_TRUNC('week', NOW() + INTERVAL '1 week' * i);
        end_date := start_date + INTERVAL '1 week';
        partition_name := 'user_activities_' || TO_CHAR(start_date, 'YYYY_"W"WW');
        
        EXECUTE format('CREATE TABLE %I PARTITION OF user_activities_partitioned 
                       FOR VALUES FROM (%L) TO (%L)', 
                       partition_name, start_date, end_date);
                       
        EXECUTE format('CREATE INDEX idx_%I_user_id ON %I(user_id)', 
                       partition_name, partition_name);
        EXECUTE format('CREATE INDEX idx_%I_activity_type ON %I(activity_type)', 
                       partition_name, partition_name);
    END LOOP;
END $$;

-- Create default partition for activities
CREATE TABLE user_activities_default PARTITION OF user_activities_partitioned DEFAULT;

-- Function to automatically create new partitions
CREATE OR REPLACE FUNCTION create_monthly_partition(table_name TEXT, start_date DATE)
RETURNS VOID AS $$
DECLARE
    partition_name TEXT;
    end_date DATE;
BEGIN
    end_date := start_date + INTERVAL '1 month';
    partition_name := table_name || '_' || TO_CHAR(start_date, 'YYYY_MM');
    
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF %I 
                   FOR VALUES FROM (%L) TO (%L)', 
                   partition_name, table_name || '_partitioned', start_date, end_date);
                   
    -- Add common indexes
    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_user_id ON %I(user_id)', 
                   partition_name, partition_name);
END $$ LANGUAGE plpgsql;

-- Function to automatically create quarterly partitions for embeddings
CREATE OR REPLACE FUNCTION create_quarterly_partition(table_name TEXT, start_date DATE)
RETURNS VOID AS $$
DECLARE
    partition_name TEXT;
    end_date DATE;
BEGIN
    end_date := start_date + INTERVAL '3 months';
    partition_name := table_name || '_' || TO_CHAR(start_date, 'YYYY_Q"Q"');
    
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF %I 
                   FOR VALUES FROM (%L) TO (%L)', 
                   partition_name, table_name || '_partitioned', start_date, end_date);
                   
    -- Add vector indexes for embeddings
    IF table_name = 'file_embeddings' THEN
        EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_embedding_vector ON %I USING ivfflat (embedding_vector vector_cosine_ops)', 
                       partition_name, partition_name);
    END IF;
END $$ LANGUAGE plpgsql;

-- Automated partition maintenance procedure
CREATE OR REPLACE FUNCTION maintain_partitions()
RETURNS VOID AS $$
DECLARE
    next_month DATE;
    next_quarter DATE;
BEGIN
    -- Create next month's partitions
    next_month := DATE_TRUNC('month', NOW() + INTERVAL '1 month');
    PERFORM create_monthly_partition('files', next_month);
    
    -- Create next quarter's partition for embeddings
    next_quarter := DATE_TRUNC('quarter', NOW() + INTERVAL '3 months');
    PERFORM create_quarterly_partition('file_embeddings', next_quarter);
    
    -- Drop old partitions (older than 2 years for files, 1 year for activities)
    PERFORM drop_old_partitions('files', INTERVAL '2 years');
    PERFORM drop_old_partitions('user_activities', INTERVAL '1 year');
    PERFORM drop_old_partitions('file_embeddings', INTERVAL '1 year');
END $$ LANGUAGE plpgsql;

-- Function to drop old partitions
CREATE OR REPLACE FUNCTION drop_old_partitions(table_prefix TEXT, retention_period INTERVAL)
RETURNS VOID AS $$
DECLARE
    partition_record RECORD;
    cutoff_date DATE;
BEGIN
    cutoff_date := (NOW() - retention_period)::DATE;
    
    FOR partition_record IN 
        SELECT schemaname, tablename 
        FROM pg_tables 
        WHERE tablename LIKE table_prefix || '_%'
        AND tablename ~ '\d{4}_\d{2}$|Q\d$|\d{2}$'
    LOOP
        -- Extract date from partition name and check if it's old enough
        -- This is a simplified check - in production you'd want more robust date parsing
        IF position('_' in partition_record.tablename) > 0 THEN
            EXECUTE format('DROP TABLE IF EXISTS %I CASCADE', partition_record.tablename);
        END IF;
    END LOOP;
END $$ LANGUAGE plpgsql;

-- Schedule automatic partition maintenance
CREATE EXTENSION IF NOT EXISTS pg_cron;
SELECT cron.schedule('maintain-partitions', '0 2 1 * *', 'SELECT maintain_partitions();');

-- Data migration from original tables (if they exist)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'files') THEN
        INSERT INTO files_partitioned SELECT * FROM files;
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'file_embeddings') THEN
        INSERT INTO file_embeddings_partitioned SELECT * FROM file_embeddings;
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_activities') THEN
        INSERT INTO user_activities_partitioned SELECT * FROM user_activities;
    END IF;
END $$;

-- Create views to maintain compatibility
CREATE OR REPLACE VIEW files AS SELECT * FROM files_partitioned;
CREATE OR REPLACE VIEW file_embeddings AS SELECT * FROM file_embeddings_partitioned;
CREATE OR REPLACE VIEW user_activities AS SELECT * FROM user_activities_partitioned;

-- Update table statistics
ANALYZE files_partitioned;
ANALYZE file_embeddings_partitioned;
ANALYZE user_activities_partitioned;

-- Migration metadata
INSERT INTO migration_history (version, name, applied_at, description) 
VALUES (2, 'partitioning', NOW(), 'Implemented table partitioning for improved performance with large datasets');