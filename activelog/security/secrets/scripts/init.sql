-- ActiveLog Secrets Rotation Database Initialization

-- Create database if not exists
SELECT 'CREATE DATABASE activelog_secrets'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'activelog_secrets');

-- Connect to the secrets database
\c activelog_secrets;

-- Create tables
CREATE TABLE IF NOT EXISTS secret_configs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    type VARCHAR(100) NOT NULL,
    rotation_interval_days INTEGER DEFAULT 30,
    auto_rotate BOOLEAN DEFAULT TRUE,
    backup_versions INTEGER DEFAULT 3,
    notification_before_expiry_hours INTEGER DEFAULT 24,
    environments JSONB DEFAULT '["production"]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_rotation_interval CHECK (rotation_interval_days > 0),
    CONSTRAINT valid_backup_versions CHECK (backup_versions >= 0)
);

CREATE TABLE IF NOT EXISTS secret_versions (
    id SERIAL PRIMARY KEY,
    secret_name VARCHAR(255) REFERENCES secret_configs(name) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    encrypted_value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    UNIQUE(secret_name, version),
    CONSTRAINT valid_version CHECK (version > 0)
);

CREATE TABLE IF NOT EXISTS rotation_history (
    id SERIAL PRIMARY KEY,
    secret_name VARCHAR(255) NOT NULL,
    old_version INTEGER,
    new_version INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL,
    message TEXT,
    rotated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    rotated_by VARCHAR(255) DEFAULT 'system',
    duration_ms INTEGER,
    CONSTRAINT valid_status CHECK (status IN ('success', 'failed', 'in_progress'))
);

CREATE TABLE IF NOT EXISTS notification_logs (
    id SERIAL PRIMARY KEY,
    secret_name VARCHAR(255) NOT NULL,
    notification_type VARCHAR(100) NOT NULL,
    recipient VARCHAR(255) NOT NULL,
    message TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'sent',
    retry_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_secret_versions_active ON secret_versions(secret_name, is_active);
CREATE INDEX IF NOT EXISTS idx_secret_versions_expires ON secret_versions(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_rotation_history_secret ON rotation_history(secret_name, rotated_at);
CREATE INDEX IF NOT EXISTS idx_rotation_history_status ON rotation_history(status, rotated_at);
CREATE INDEX IF NOT EXISTS idx_notification_logs_secret ON notification_logs(secret_name, sent_at);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id, created_at);

-- Create functions for automatic timestamp updates
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers
CREATE TRIGGER update_secret_configs_updated_at 
    BEFORE UPDATE ON secret_configs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create views for common queries
CREATE OR REPLACE VIEW active_secrets AS
SELECT 
    sc.name,
    sc.type,
    sc.rotation_interval_days,
    sc.auto_rotate,
    sv.version,
    sv.created_at as last_rotated,
    sv.expires_at,
    CASE 
        WHEN sv.expires_at <= NOW() + INTERVAL '24 hours' THEN 'expiring_soon'
        WHEN sv.expires_at <= NOW() THEN 'expired'
        ELSE 'active'
    END as status
FROM secret_configs sc
LEFT JOIN secret_versions sv ON sc.name = sv.secret_name AND sv.is_active = TRUE;

CREATE OR REPLACE VIEW rotation_statistics AS
SELECT 
    DATE_TRUNC('day', rotated_at) as date,
    COUNT(*) as total_rotations,
    COUNT(CASE WHEN status = 'success' THEN 1 END) as successful_rotations,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_rotations,
    AVG(duration_ms) as avg_duration_ms
FROM rotation_history
WHERE rotated_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', rotated_at)
ORDER BY date DESC;

-- Insert default secret configurations
INSERT INTO secret_configs (name, type, rotation_interval_days, auto_rotate, environments) VALUES
('database-master-password', 'database_password', 30, true, '["production", "staging"]'),
('api-gateway-jwt-secret', 'jwt_secret', 60, true, '["production", "staging"]'),
('auth-service-encryption-key', 'encryption_key', 90, true, '["production", "staging"]'),
('external-api-key-stripe', 'api_key', 30, true, '["production"]'),
('external-api-key-sendgrid', 'api_key', 30, true, '["production"]'),
('redis-auth-password', 'password', 45, true, '["production", "staging"]'),
('session-encryption-key', 'encryption_key', 30, true, '["production", "staging"]'),
('webhook-signing-secret', 'api_key', 60, true, '["production"]')
ON CONFLICT (name) DO NOTHING;

-- Create initial audit log entry
INSERT INTO audit_logs (action, resource_type, resource_id, user_id, details)
VALUES ('database_initialized', 'system', 'secrets_rotation_db', 'system', 
        '{"message": "Secrets rotation database initialized successfully"}');

-- Grant permissions (in production, use more restrictive permissions)
GRANT USAGE ON SCHEMA public TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO postgres;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- Print initialization status
DO $$
DECLARE
    config_count INTEGER;
    history_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO config_count FROM secret_configs;
    SELECT COUNT(*) INTO history_count FROM rotation_history;
    
    RAISE NOTICE 'ActiveLog Secrets Rotation Database Initialized Successfully';
    RAISE NOTICE 'Secret configurations: %', config_count;
    RAISE NOTICE 'Rotation history entries: %', history_count;
    RAISE NOTICE 'Database ready for secrets rotation service';
END $$;