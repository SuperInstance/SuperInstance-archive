-- PostgreSQL initialization script for ActiveLog with pgvector extension
-- This script sets up the database with pgvector and other useful extensions

-- Connect to the main database
\c ${db_name};

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "btree_gist";
CREATE EXTENSION IF NOT EXISTS "hstore";
CREATE EXTENSION IF NOT EXISTS "ltree";
CREATE EXTENSION IF NOT EXISTS "citext";
CREATE EXTENSION IF NOT EXISTS "unaccent";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create database schemas for different service domains
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS users;
CREATE SCHEMA IF NOT EXISTS projects;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS ai;
CREATE SCHEMA IF NOT EXISTS files;
CREATE SCHEMA IF NOT EXISTS communications;
CREATE SCHEMA IF NOT EXISTS security;
CREATE SCHEMA IF NOT EXISTS billing;
CREATE SCHEMA IF NOT EXISTS monitoring;

-- Set up basic tables with vector support
CREATE TABLE IF NOT EXISTS ai.embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    embedding vector(1536), -- OpenAI embeddings are 1536 dimensions
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for vector similarity search
CREATE INDEX IF NOT EXISTS embeddings_embedding_idx ON ai.embeddings 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS embeddings_entity_idx ON ai.embeddings (entity_type, entity_id);
CREATE INDEX IF NOT EXISTS embeddings_created_at_idx ON ai.embeddings (created_at);

-- Create function for updating timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to embeddings table
DROP TRIGGER IF EXISTS update_embeddings_updated_at ON ai.embeddings;
CREATE TRIGGER update_embeddings_updated_at 
    BEFORE UPDATE ON ai.embeddings 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create basic user management tables
CREATE TABLE IF NOT EXISTS users.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(255),
    avatar_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS users_email_idx ON users.users (email);
CREATE INDEX IF NOT EXISTS users_username_idx ON users.users (username);
CREATE INDEX IF NOT EXISTS users_created_at_idx ON users.users (created_at);

-- Apply trigger to users table
DROP TRIGGER IF EXISTS update_users_updated_at ON users.users;
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users.users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create projects tables
CREATE TABLE IF NOT EXISTS projects.projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    owner_id UUID NOT NULL REFERENCES users.users(id) ON DELETE CASCADE,
    is_public BOOLEAN DEFAULT FALSE,
    is_archived BOOLEAN DEFAULT FALSE,
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS projects_owner_id_idx ON projects.projects (owner_id);
CREATE INDEX IF NOT EXISTS projects_created_at_idx ON projects.projects (created_at);
CREATE INDEX IF NOT EXISTS projects_tags_idx ON projects.projects USING GIN (tags);
CREATE INDEX IF NOT EXISTS projects_metadata_idx ON projects.projects USING GIN (metadata);

-- Apply trigger to projects table
DROP TRIGGER IF EXISTS update_projects_updated_at ON projects.projects;
CREATE TRIGGER update_projects_updated_at 
    BEFORE UPDATE ON projects.projects 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create analytics tables for tracking
CREATE TABLE IF NOT EXISTS analytics.events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users.users(id) ON DELETE SET NULL,
    session_id VARCHAR(255),
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB DEFAULT '{}'::jsonb,
    ip_address INET,
    user_agent TEXT,
    referrer TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS events_user_id_idx ON analytics.events (user_id);
CREATE INDEX IF NOT EXISTS events_created_at_idx ON analytics.events (created_at);
CREATE INDEX IF NOT EXISTS events_event_type_idx ON analytics.events (event_type);
CREATE INDEX IF NOT EXISTS events_session_id_idx ON analytics.events (session_id);

-- Create security audit table
CREATE TABLE IF NOT EXISTS security.audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users.users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    details JSONB DEFAULT '{}'::jsonb,
    ip_address INET,
    user_agent TEXT,
    success BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS audit_log_user_id_idx ON security.audit_log (user_id);
CREATE INDEX IF NOT EXISTS audit_log_created_at_idx ON security.audit_log (created_at);
CREATE INDEX IF NOT EXISTS audit_log_action_idx ON security.audit_log (action);
CREATE INDEX IF NOT EXISTS audit_log_resource_idx ON security.audit_log (resource_type, resource_id);

-- Create view for user activity summary
CREATE OR REPLACE VIEW analytics.user_activity_summary AS
SELECT 
    u.id,
    u.username,
    u.email,
    COUNT(e.id) as total_events,
    COUNT(DISTINCT DATE(e.created_at)) as active_days,
    MAX(e.created_at) as last_activity,
    COUNT(p.id) as total_projects,
    ARRAY_AGG(DISTINCT e.event_type) as event_types
FROM users.users u
LEFT JOIN analytics.events e ON u.id = e.user_id
LEFT JOIN projects.projects p ON u.id = p.owner_id
GROUP BY u.id, u.username, u.email;

-- Create function for vector similarity search
CREATE OR REPLACE FUNCTION ai.find_similar_embeddings(
    query_embedding vector(1536),
    entity_type_filter text DEFAULT NULL,
    similarity_threshold float DEFAULT 0.8,
    max_results int DEFAULT 10
)
RETURNS TABLE(
    id uuid,
    entity_type varchar(50),
    entity_id uuid,
    similarity float,
    metadata jsonb
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.id,
        e.entity_type,
        e.entity_id,
        1 - (e.embedding <=> query_embedding) as similarity,
        e.metadata
    FROM ai.embeddings e
    WHERE 
        (entity_type_filter IS NULL OR e.entity_type = entity_type_filter)
        AND (1 - (e.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY e.embedding <=> query_embedding
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- Create function for full-text search with vector boost
CREATE OR REPLACE FUNCTION projects.search_projects(
    search_query text,
    query_embedding vector(1536) DEFAULT NULL,
    user_id_filter uuid DEFAULT NULL,
    limit_results int DEFAULT 20
)
RETURNS TABLE(
    id uuid,
    name varchar(255),
    description text,
    owner_id uuid,
    similarity_score float,
    text_rank float
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id,
        p.name,
        p.description,
        p.owner_id,
        CASE 
            WHEN query_embedding IS NOT NULL AND e.embedding IS NOT NULL 
            THEN (1 - (e.embedding <=> query_embedding))::float
            ELSE 0.0
        END as similarity_score,
        ts_rank(
            to_tsvector('english', p.name || ' ' || COALESCE(p.description, '')),
            plainto_tsquery('english', search_query)
        ) as text_rank
    FROM projects.projects p
    LEFT JOIN ai.embeddings e ON p.id = e.entity_id AND e.entity_type = 'project'
    WHERE 
        (user_id_filter IS NULL OR p.owner_id = user_id_filter)
        AND (
            to_tsvector('english', p.name || ' ' || COALESCE(p.description, '')) @@ plainto_tsquery('english', search_query)
            OR (query_embedding IS NOT NULL AND e.embedding IS NOT NULL AND (1 - (e.embedding <=> query_embedding)) > 0.7)
        )
    ORDER BY 
        CASE 
            WHEN query_embedding IS NOT NULL AND e.embedding IS NOT NULL 
            THEN (1 - (e.embedding <=> query_embedding))::float
            ELSE ts_rank(
                to_tsvector('english', p.name || ' ' || COALESCE(p.description, '')),
                plainto_tsquery('english', search_query)
            )
        END DESC
    LIMIT limit_results;
END;
$$ LANGUAGE plpgsql;

-- Grant appropriate permissions
GRANT USAGE ON SCHEMA auth TO PUBLIC;
GRANT USAGE ON SCHEMA users TO PUBLIC;
GRANT USAGE ON SCHEMA projects TO PUBLIC;
GRANT USAGE ON SCHEMA analytics TO PUBLIC;
GRANT USAGE ON SCHEMA ai TO PUBLIC;
GRANT USAGE ON SCHEMA files TO PUBLIC;
GRANT USAGE ON SCHEMA communications TO PUBLIC;
GRANT USAGE ON SCHEMA security TO PUBLIC;
GRANT USAGE ON SCHEMA billing TO PUBLIC;
GRANT USAGE ON SCHEMA monitoring TO PUBLIC;

-- Grant select permissions on views
GRANT SELECT ON analytics.user_activity_summary TO PUBLIC;

-- Create indexes for performance
SET maintenance_work_mem = '2GB';

-- Analyze tables for better query planning
ANALYZE users.users;
ANALYZE projects.projects;
ANALYZE analytics.events;
ANALYZE ai.embeddings;
ANALYZE security.audit_log;

-- Print completion message
SELECT 'ActiveLog database initialization completed successfully!' as message;