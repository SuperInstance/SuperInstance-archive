-- Migration 005: Optimize vector similarity searches
-- This migration optimizes vector embeddings for fast similarity searches and clustering

-- Install and configure pgvector extension with optimizations
CREATE EXTENSION IF NOT EXISTS vector;

-- Create optimized vector configuration
-- Set vector-specific PostgreSQL parameters for better performance
ALTER SYSTEM SET shared_preload_libraries = 'vector';
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '256MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;

-- Optimize work_mem for vector operations
ALTER SYSTEM SET work_mem = '32MB';

-- Create vector configuration table
CREATE TABLE IF NOT EXISTS vector_config (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL UNIQUE,
    vector_dimension INTEGER NOT NULL,
    distance_metric VARCHAR(20) DEFAULT 'cosine', -- 'cosine', 'euclidean', 'inner_product'
    index_type VARCHAR(20) DEFAULT 'ivfflat', -- 'ivfflat', 'hnsw'
    index_params JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default vector configurations
INSERT INTO vector_config (model_name, vector_dimension, distance_metric, index_type, index_params)
VALUES 
    ('text-embedding-ada-002', 1536, 'cosine', 'ivfflat', '{"lists": 100}'),
    ('text-embedding-3-small', 1536, 'cosine', 'hnsw', '{"m": 16, "ef_construction": 64}'),
    ('text-embedding-3-large', 3072, 'cosine', 'hnsw', '{"m": 16, "ef_construction": 64}'),
    ('sentence-transformers', 768, 'cosine', 'ivfflat', '{"lists": 50}'),
    ('clip-vit-base', 512, 'cosine', 'ivfflat', '{"lists": 50}'),
    ('clip-vit-large', 768, 'cosine', 'hnsw', '{"m": 16, "ef_construction": 64}')
ON CONFLICT (model_name) DO NOTHING;

-- Create optimized file embeddings table with multiple vector types
CREATE TABLE IF NOT EXISTS file_embeddings_optimized (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    file_id UUID NOT NULL,
    embedding_model VARCHAR(100) NOT NULL,
    embedding_type VARCHAR(50) NOT NULL, -- 'content', 'title', 'summary', 'visual'
    embedding_vector VECTOR(1536), -- Will be dynamically sized based on model
    chunk_index INTEGER DEFAULT 0,
    chunk_text TEXT,
    chunk_start_pos INTEGER,
    chunk_end_pos INTEGER,
    confidence_score FLOAT DEFAULT 1.0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure we have the right foreign key relationships
    FOREIGN KEY (file_id) REFERENCES files_partitioned(id) ON DELETE CASCADE,
    FOREIGN KEY (embedding_model) REFERENCES vector_config(model_name)
) PARTITION BY RANGE (created_at);

-- Create optimized indexes for vector similarity search
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_embeddings_opt_vector_cosine 
ON file_embeddings_optimized USING ivfflat (embedding_vector vector_cosine_ops) WITH (lists = 100);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_embeddings_opt_vector_l2 
ON file_embeddings_optimized USING ivfflat (embedding_vector vector_l2_ops) WITH (lists = 100);

-- For HNSW indexes (better for high-dimensional vectors)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_embeddings_opt_vector_hnsw 
ON file_embeddings_optimized USING hnsw (embedding_vector vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- Composite indexes for filtered similarity search
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_embeddings_opt_model_type 
ON file_embeddings_optimized(embedding_model, embedding_type);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_embeddings_opt_file_model 
ON file_embeddings_optimized(file_id, embedding_model);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_embeddings_opt_confidence 
ON file_embeddings_optimized(confidence_score DESC) WHERE confidence_score > 0.5;

-- Create quarterly partitions for optimized embeddings
DO $$
DECLARE
    start_date DATE;
    end_date DATE;
    partition_name TEXT;
    i INTEGER;
BEGIN
    FOR i IN -2..6 LOOP
        start_date := DATE_TRUNC('quarter', NOW() + INTERVAL '3 months' * i);
        end_date := start_date + INTERVAL '3 months';
        partition_name := 'file_embeddings_opt_' || TO_CHAR(start_date, 'YYYY_Q"Q"');
        
        EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF file_embeddings_optimized 
                       FOR VALUES FROM (%L) TO (%L)', 
                       partition_name, start_date, end_date);
        
        -- Add optimized vector indexes to each partition
        EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_vector_cosine 
                       ON %I USING ivfflat (embedding_vector vector_cosine_ops) WITH (lists = 100)', 
                       partition_name, partition_name);
                       
        EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_file_id ON %I(file_id)', 
                       partition_name, partition_name);
    END LOOP;
END $$;

-- Create vector similarity search functions
CREATE OR REPLACE FUNCTION find_similar_files(
    query_vector VECTOR(1536),
    model_name VARCHAR(100) DEFAULT 'text-embedding-ada-002',
    similarity_threshold FLOAT DEFAULT 0.7,
    max_results INTEGER DEFAULT 20,
    file_types TEXT[] DEFAULT NULL,
    user_id UUID DEFAULT NULL
)
RETURNS TABLE(
    file_id UUID,
    similarity_score FLOAT,
    file_name TEXT,
    file_path TEXT,
    file_type VARCHAR(50),
    chunk_text TEXT,
    metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    WITH similarity_search AS (
        SELECT 
            fe.file_id,
            1 - (fe.embedding_vector <=> query_vector) as similarity,
            fe.chunk_text,
            fe.metadata as embedding_metadata,
            ROW_NUMBER() OVER (PARTITION BY fe.file_id ORDER BY 1 - (fe.embedding_vector <=> query_vector) DESC) as rn
        FROM file_embeddings_optimized fe
        WHERE fe.embedding_model = find_similar_files.model_name
        AND 1 - (fe.embedding_vector <=> query_vector) >= similarity_threshold
    ),
    ranked_files AS (
        SELECT 
            ss.file_id,
            ss.similarity as similarity_score,
            ss.chunk_text,
            ss.embedding_metadata
        FROM similarity_search ss
        WHERE ss.rn = 1  -- Get best match per file
    )
    SELECT 
        rf.file_id,
        rf.similarity_score,
        f.name as file_name,
        f.path as file_path,
        f.file_type,
        rf.chunk_text,
        rf.embedding_metadata as metadata
    FROM ranked_files rf
    JOIN files_partitioned f ON rf.file_id = f.id
    WHERE NOT f.is_deleted
    AND (find_similar_files.file_types IS NULL OR f.file_type = ANY(find_similar_files.file_types))
    AND (find_similar_files.user_id IS NULL OR f.user_id = find_similar_files.user_id)
    ORDER BY rf.similarity_score DESC
    LIMIT max_results;
END $$ LANGUAGE plpgsql;

-- Create semantic clustering function
CREATE OR REPLACE FUNCTION create_semantic_clusters(
    model_name VARCHAR(100) DEFAULT 'text-embedding-ada-002',
    cluster_count INTEGER DEFAULT 10,
    min_cluster_size INTEGER DEFAULT 3,
    user_id UUID DEFAULT NULL
)
RETURNS TABLE(
    cluster_id INTEGER,
    centroid_vector VECTOR(1536),
    file_ids UUID[],
    representative_text TEXT,
    cluster_size INTEGER,
    avg_similarity FLOAT
) AS $$
DECLARE
    embedding_record RECORD;
    current_cluster INTEGER := 0;
BEGIN
    -- Create temporary table for clustering
    CREATE TEMP TABLE IF NOT EXISTS temp_clusters (
        cluster_id INTEGER,
        file_id UUID,
        embedding_vector VECTOR(1536),
        similarity_to_centroid FLOAT
    );
    
    -- Simple k-means clustering implementation
    -- In production, you'd use a more sophisticated clustering algorithm
    
    FOR embedding_record IN
        SELECT DISTINCT ON (fe.file_id) 
            fe.file_id,
            fe.embedding_vector,
            fe.chunk_text
        FROM file_embeddings_optimized fe
        JOIN files_partitioned f ON fe.file_id = f.id
        WHERE fe.embedding_model = create_semantic_clusters.model_name
        AND NOT f.is_deleted
        AND (create_semantic_clusters.user_id IS NULL OR f.user_id = create_semantic_clusters.user_id)
        ORDER BY fe.file_id, fe.confidence_score DESC
    LOOP
        -- Assign to nearest cluster or create new one
        current_cluster := current_cluster + 1;
        
        INSERT INTO temp_clusters (cluster_id, file_id, embedding_vector)
        VALUES (current_cluster, embedding_record.file_id, embedding_record.embedding_vector);
    END LOOP;
    
    -- Return cluster results
    RETURN QUERY
    SELECT 
        tc.cluster_id,
        AVG(tc.embedding_vector)::VECTOR(1536) as centroid_vector,
        array_agg(tc.file_id) as file_ids,
        STRING_AGG(fe.chunk_text, ' | ') as representative_text,
        COUNT(*)::INTEGER as cluster_size,
        AVG(tc.similarity_to_centroid)::FLOAT as avg_similarity
    FROM temp_clusters tc
    JOIN file_embeddings_optimized fe ON tc.file_id = fe.file_id
    WHERE fe.embedding_model = create_semantic_clusters.model_name
    GROUP BY tc.cluster_id
    HAVING COUNT(*) >= min_cluster_size
    ORDER BY cluster_size DESC;
    
    DROP TABLE temp_clusters;
END $$ LANGUAGE plpgsql;

-- Create batch embedding insertion function
CREATE OR REPLACE FUNCTION insert_embeddings_batch(
    embeddings_data JSONB
)
RETURNS INTEGER AS $$
DECLARE
    embedding_record JSONB;
    inserted_count INTEGER := 0;
BEGIN
    -- Validate input format
    IF NOT jsonb_typeof(embeddings_data) = 'array' THEN
        RAISE EXCEPTION 'embeddings_data must be a JSON array';
    END IF;
    
    -- Insert embeddings in batch
    FOR embedding_record IN SELECT * FROM jsonb_array_elements(embeddings_data)
    LOOP
        INSERT INTO file_embeddings_optimized (
            file_id,
            embedding_model,
            embedding_type,
            embedding_vector,
            chunk_index,
            chunk_text,
            chunk_start_pos,
            chunk_end_pos,
            confidence_score,
            metadata
        ) VALUES (
            (embedding_record->>'file_id')::UUID,
            embedding_record->>'embedding_model',
            COALESCE(embedding_record->>'embedding_type', 'content'),
            (embedding_record->>'embedding_vector')::VECTOR(1536),
            COALESCE((embedding_record->>'chunk_index')::INTEGER, 0),
            embedding_record->>'chunk_text',
            (embedding_record->>'chunk_start_pos')::INTEGER,
            (embedding_record->>'chunk_end_pos')::INTEGER,
            COALESCE((embedding_record->>'confidence_score')::FLOAT, 1.0),
            COALESCE(embedding_record->'metadata', '{}'::JSONB)
        );
        
        inserted_count := inserted_count + 1;
    END LOOP;
    
    RETURN inserted_count;
END $$ LANGUAGE plpgsql;

-- Create vector index optimization function
CREATE OR REPLACE FUNCTION optimize_vector_indexes()
RETURNS VOID AS $$
DECLARE
    table_record RECORD;
    index_record RECORD;
BEGIN
    -- Update vector index statistics
    FOR table_record IN 
        SELECT schemaname, tablename 
        FROM pg_tables 
        WHERE tablename LIKE 'file_embeddings%'
    LOOP
        EXECUTE format('ANALYZE %I.%I', table_record.schemaname, table_record.tablename);
    END LOOP;
    
    -- Rebuild vector indexes if they're getting fragmented
    FOR index_record IN
        SELECT schemaname, indexname, tablename
        FROM pg_indexes
        WHERE indexdef LIKE '%vector%'
        AND schemaname = 'public'
    LOOP
        -- Check index bloat and rebuild if necessary
        EXECUTE format('REINDEX INDEX CONCURRENTLY %I.%I', index_record.schemaname, index_record.indexname);
    END LOOP;
    
    -- Log optimization completion
    INSERT INTO system_logs (log_level, message)
    VALUES ('INFO', 'Vector index optimization completed');
END $$ LANGUAGE plpgsql;

-- Create embedding quality monitoring
CREATE OR REPLACE FUNCTION monitor_embedding_quality()
RETURNS JSON AS $$
BEGIN
    RETURN (
        SELECT json_build_object(
            'total_embeddings', COUNT(*),
            'models_in_use', COUNT(DISTINCT embedding_model),
            'avg_confidence', AVG(confidence_score),
            'low_confidence_count', COUNT(*) FILTER (WHERE confidence_score < 0.5),
            'embedding_types', json_object_agg(embedding_type, type_count),
            'model_distribution', (
                SELECT json_object_agg(embedding_model, model_count)
                FROM (
                    SELECT embedding_model, COUNT(*) as model_count
                    FROM file_embeddings_optimized
                    GROUP BY embedding_model
                ) model_stats
            ),
            'recent_embeddings', COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '24 hours'),
            'index_usage_stats', (
                SELECT json_object_agg(indexname, idx_tup_read)
                FROM pg_stat_user_indexes
                WHERE relname LIKE 'file_embeddings%'
                AND indexname LIKE '%vector%'
            )
        )
        FROM (
            SELECT 
                embedding_model,
                embedding_type,
                confidence_score,
                created_at,
                COUNT(*) OVER (PARTITION BY embedding_type) as type_count
            FROM file_embeddings_optimized
        ) embedding_stats
    );
END $$ LANGUAGE plpgsql;

-- Create function to update vector search parameters
CREATE OR REPLACE FUNCTION update_vector_search_params(
    model_name VARCHAR(100),
    new_params JSONB
)
RETURNS VOID AS $$
BEGIN
    UPDATE vector_config 
    SET 
        index_params = new_params,
        updated_at = NOW()
    WHERE model_name = update_vector_search_params.model_name;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Vector configuration not found for model: %', model_name;
    END IF;
    
    -- Log parameter update
    INSERT INTO system_logs (log_level, message, details)
    VALUES ('INFO', 'Vector search parameters updated', 
            json_build_object('model', model_name, 'params', new_params));
END $$ LANGUAGE plpgsql;

-- Schedule vector index optimization
SELECT cron.schedule('optimize-vector-indexes', '0 3 * * 1', 'SELECT optimize_vector_indexes();');

-- Schedule embedding quality monitoring
SELECT cron.schedule('monitor-embeddings', '0 */6 * * *', 'INSERT INTO system_logs (log_level, message, details) VALUES (''INFO'', ''Embedding quality report'', monitor_embedding_quality());');

-- Create performance monitoring view for vectors
CREATE MATERIALIZED VIEW vector_performance_stats AS
SELECT 
    embedding_model,
    embedding_type,
    COUNT(*) as embedding_count,
    AVG(confidence_score) as avg_confidence,
    MIN(confidence_score) as min_confidence,
    MAX(confidence_score) as max_confidence,
    COUNT(DISTINCT file_id) as unique_files,
    AVG(char_length(chunk_text)) as avg_chunk_length,
    COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days') as recent_count,
    pg_size_pretty(pg_total_relation_size('file_embeddings_optimized')) as total_size
FROM file_embeddings_optimized
GROUP BY embedding_model, embedding_type;

CREATE UNIQUE INDEX idx_vector_perf_stats_model_type ON vector_performance_stats(embedding_model, embedding_type);

-- Add vector performance stats to refresh schedule
CREATE OR REPLACE FUNCTION refresh_vector_stats()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY vector_performance_stats;
    INSERT INTO system_logs (log_level, message)
    VALUES ('INFO', 'Vector performance stats refreshed');
END $$ LANGUAGE plpgsql;

SELECT cron.schedule('refresh-vector-stats', '0 2 * * *', 'SELECT refresh_vector_stats();');

-- Migration metadata
INSERT INTO migration_history (version, name, applied_at, description) 
VALUES (5, 'vector_optimization', NOW(), 'Optimized vector similarity searches with improved indexing and clustering capabilities');