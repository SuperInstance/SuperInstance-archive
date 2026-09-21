-- Migration 001: Add indexes for common queries
-- This migration creates optimized indexes for frequently accessed data patterns

-- Files table indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_user_id ON files(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_created_at ON files(created_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_modified_at ON files(modified_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_file_type ON files(file_type);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_sync_status ON files(sync_status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_size ON files(size);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_path_trgm ON files USING gin(path gin_trgm_ops);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_name_trgm ON files USING gin(name gin_trgm_ops);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_user_created ON files(user_id, created_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_user_type ON files(user_id, file_type);

-- File content embeddings indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_embeddings_file_id ON file_embeddings(file_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_embeddings_model ON file_embeddings(embedding_model);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_embeddings_created ON file_embeddings(created_at DESC);

-- Tags table indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tags_user_id ON tags(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tags_name ON tags(name);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tags_color ON tags(color);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tags_user_name ON tags(user_id, name);

-- File tags junction table indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_tags_file_id ON file_tags(file_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_tags_tag_id ON file_tags(tag_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_tags_created ON file_tags(created_at DESC);

-- File relationships indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_relationships_parent ON file_relationships(parent_file_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_relationships_child ON file_relationships(child_file_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_relationships_type ON file_relationships(relationship_type);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_file_relationships_strength ON file_relationships(strength DESC);

-- Search history indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_search_history_user_id ON search_history(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_search_history_query_trgm ON search_history USING gin(query gin_trgm_ops);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_search_history_created ON search_history(created_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_search_history_user_created ON search_history(user_id, created_at DESC);

-- User activity logs indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_activities_user_id ON user_activities(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_activities_activity_type ON user_activities(activity_type);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_activities_created ON user_activities(created_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_activities_user_type ON user_activities(user_id, activity_type);

-- Sync events indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sync_events_file_id ON sync_events(file_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sync_events_event_type ON sync_events(event_type);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sync_events_created ON sync_events(created_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sync_events_status ON sync_events(sync_status);

-- User sessions indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_sessions_token ON user_sessions(session_token);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_sessions_expires ON user_sessions(expires_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_sessions_active ON user_sessions(is_active);

-- Composite indexes for complex queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_user_sync_modified ON files(user_id, sync_status, modified_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_files_type_size_created ON files(file_type, size, created_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_search_freq_user ON search_history(user_id, query, created_at DESC);

-- Enable extensions needed for trigram search
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- Update table statistics
ANALYZE files;
ANALYZE file_embeddings;
ANALYZE tags;
ANALYZE file_tags;
ANALYZE file_relationships;
ANALYZE search_history;
ANALYZE user_activities;
ANALYZE sync_events;
ANALYZE user_sessions;

-- Migration metadata
INSERT INTO migration_history (version, name, applied_at, description) 
VALUES (1, 'create_indexes', NOW(), 'Added optimized indexes for common query patterns');