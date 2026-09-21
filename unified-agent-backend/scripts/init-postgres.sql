-- PostgreSQL initialization script for unified-agent-backend
-- This script is executed when the PostgreSQL container is first created

-- Create additional user for application (optional)
-- CREATE USER app_user WITH PASSWORD 'app_password';
-- GRANT ALL PRIVILEGES ON DATABASE unified_agent_db TO app_user;

-- Create extensions that might be needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create custom types if needed
-- CREATE TYPE user_role AS ENUM ('admin', 'user', 'guest');

-- Set default configurations
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET track_activity_query_size = 2048;
ALTER SYSTEM SET pg_stat_statements.track = 'all';

-- Reload configuration
SELECT pg_reload_conf();

-- Create basic indexes for performance (tables will be created by Alembic)
-- These are examples and should be adjusted based on actual schema

-- Example: Index for vector similarity search (when using pgvector)
-- CREATE EXTENSION IF NOT EXISTS vector;
-- CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops);

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'Unified Agent Backend PostgreSQL initialization completed';
END $$;