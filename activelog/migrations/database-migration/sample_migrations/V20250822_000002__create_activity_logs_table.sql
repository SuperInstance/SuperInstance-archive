-- @description: Create activity logs table for user activity tracking
-- @dependencies: V20250822_000001__create_users_table
-- @estimated_duration: 10
-- @requires_downtime: false

-- +migrate Up
CREATE TABLE IF NOT EXISTS activity_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    activity_type VARCHAR(100) NOT NULL,
    activity_category VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    metadata JSONB DEFAULT '{}',
    source_platform VARCHAR(100),
    source_app VARCHAR(100),
    source_device VARCHAR(100),
    location_data JSONB,
    media_attachments JSONB DEFAULT '[]',
    tags TEXT[],
    privacy_level VARCHAR(20) DEFAULT 'private',
    sentiment_score REAL,
    importance_score REAL,
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_activity_logs_user_id ON activity_logs(user_id);
CREATE INDEX idx_activity_logs_activity_type ON activity_logs(activity_type);
CREATE INDEX idx_activity_logs_activity_category ON activity_logs(activity_category);
CREATE INDEX idx_activity_logs_occurred_at ON activity_logs(occurred_at);
CREATE INDEX idx_activity_logs_created_at ON activity_logs(created_at);
CREATE INDEX idx_activity_logs_privacy_level ON activity_logs(privacy_level);
CREATE INDEX idx_activity_logs_tags ON activity_logs USING GIN(tags);
CREATE INDEX idx_activity_logs_metadata ON activity_logs USING GIN(metadata);

-- Composite indexes for common queries
CREATE INDEX idx_activity_logs_user_occurred ON activity_logs(user_id, occurred_at DESC);
CREATE INDEX idx_activity_logs_user_category ON activity_logs(user_id, activity_category);

-- +migrate Down
DROP INDEX IF EXISTS idx_activity_logs_user_category;
DROP INDEX IF EXISTS idx_activity_logs_user_occurred;
DROP INDEX IF EXISTS idx_activity_logs_metadata;
DROP INDEX IF EXISTS idx_activity_logs_tags;
DROP INDEX IF EXISTS idx_activity_logs_privacy_level;
DROP INDEX IF EXISTS idx_activity_logs_created_at;
DROP INDEX IF EXISTS idx_activity_logs_occurred_at;
DROP INDEX IF EXISTS idx_activity_logs_activity_category;
DROP INDEX IF EXISTS idx_activity_logs_activity_type;
DROP INDEX IF EXISTS idx_activity_logs_user_id;
DROP TABLE IF EXISTS activity_logs;