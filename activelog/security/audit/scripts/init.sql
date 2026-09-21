-- ActiveLog Audit Logging Database Initialization

-- Create database if not exists
SELECT 'CREATE DATABASE activelog_audit'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'activelog_audit');

-- Connect to the audit database
\c activelog_audit;

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create tables
CREATE TABLE IF NOT EXISTS audit_events (
    id SERIAL PRIMARY KEY,
    event_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    event_type VARCHAR(100) NOT NULL,
    user_id VARCHAR(255),
    session_id VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    resource_type VARCHAR(255),
    resource_id VARCHAR(255),
    action VARCHAR(255) NOT NULL,
    outcome VARCHAR(50) NOT NULL CHECK (outcome IN ('success', 'failure', 'error')),
    risk_level VARCHAR(20) NOT NULL CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    compliance_frameworks JSONB DEFAULT '[]',
    details JSONB DEFAULT '{}',
    context JSONB DEFAULT '{}',
    geolocation JSONB,
    fingerprint VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS compliance_reports (
    id SERIAL PRIMARY KEY,
    framework VARCHAR(50) NOT NULL,
    report_period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    report_period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    total_events INTEGER NOT NULL,
    high_risk_events INTEGER NOT NULL,
    failed_events INTEGER NOT NULL,
    report_data JSONB NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    generated_by VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS retention_policies (
    id SERIAL PRIMARY KEY,
    framework VARCHAR(50) UNIQUE NOT NULL,
    retention_days INTEGER NOT NULL CHECK (retention_days > 0),
    archive_after_days INTEGER CHECK (archive_after_days > 0),
    encryption_required BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(255) UNIQUE NOT NULL,
    setting_value JSONB NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS compliance_rules (
    id SERIAL PRIMARY KEY,
    framework VARCHAR(50) NOT NULL,
    rule_name VARCHAR(255) NOT NULL,
    rule_type VARCHAR(100) NOT NULL, -- threshold, pattern, frequency, etc.
    rule_config JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    alert_severity VARCHAR(20) DEFAULT 'medium',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alert_history (
    id SERIAL PRIMARY KEY,
    alert_type VARCHAR(100) NOT NULL,
    framework VARCHAR(50),
    rule_id INTEGER REFERENCES compliance_rules(id),
    event_id UUID REFERENCES audit_events(event_id),
    alert_data JSONB NOT NULL,
    severity VARCHAR(20) NOT NULL,
    status VARCHAR(50) DEFAULT 'open',
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS data_retention_log (
    id SERIAL PRIMARY KEY,
    action VARCHAR(50) NOT NULL, -- archive, delete, export
    table_name VARCHAR(255) NOT NULL,
    records_affected INTEGER NOT NULL,
    criteria JSONB NOT NULL,
    execution_time INTEGER, -- milliseconds
    status VARCHAR(50) NOT NULL,
    error_message TEXT,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    executed_by VARCHAR(255) DEFAULT 'system'
);

-- Create indexes for optimal performance
CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp ON audit_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_events_user_id ON audit_events(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_event_type ON audit_events(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_events_risk_level ON audit_events(risk_level);
CREATE INDEX IF NOT EXISTS idx_audit_events_outcome ON audit_events(outcome);
CREATE INDEX IF NOT EXISTS idx_audit_events_ip_address ON audit_events(ip_address);
CREATE INDEX IF NOT EXISTS idx_audit_events_session_id ON audit_events(session_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_resource ON audit_events(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_fingerprint ON audit_events(fingerprint);

-- GIN indexes for JSONB fields
CREATE INDEX IF NOT EXISTS idx_audit_events_compliance_gin ON audit_events USING GIN(compliance_frameworks);
CREATE INDEX IF NOT EXISTS idx_audit_events_details_gin ON audit_events USING GIN(details);
CREATE INDEX IF NOT EXISTS idx_audit_events_context_gin ON audit_events USING GIN(context);
CREATE INDEX IF NOT EXISTS idx_audit_events_geolocation_gin ON audit_events USING GIN(geolocation);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_audit_events_user_time ON audit_events(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_type_time ON audit_events(event_type, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_risk_time ON audit_events(risk_level, timestamp DESC);

-- Indexes for other tables
CREATE INDEX IF NOT EXISTS idx_compliance_reports_framework ON compliance_reports(framework);
CREATE INDEX IF NOT EXISTS idx_compliance_reports_period ON compliance_reports(report_period_start, report_period_end);
CREATE INDEX IF NOT EXISTS idx_alert_history_status ON alert_history(status);
CREATE INDEX IF NOT EXISTS idx_alert_history_severity ON alert_history(severity);
CREATE INDEX IF NOT EXISTS idx_alert_history_framework ON alert_history(framework);

-- Create functions for automatic timestamp updates
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for automatic timestamp updates
CREATE TRIGGER update_retention_policies_updated_at 
    BEFORE UPDATE ON retention_policies 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_audit_settings_updated_at 
    BEFORE UPDATE ON audit_settings 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_compliance_rules_updated_at 
    BEFORE UPDATE ON compliance_rules 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default retention policies
INSERT INTO retention_policies (framework, retention_days, archive_after_days, encryption_required) VALUES
    ('sox', 2555, 365, true),      -- 7 years for SOX compliance
    ('pci', 365, 90, true),        -- 1 year for PCI DSS
    ('gdpr', 2190, 730, true),     -- 6 years for GDPR
    ('hipaa', 2190, 365, true),    -- 6 years for HIPAA
    ('soc2', 1095, 365, true),     -- 3 years for SOC2
    ('iso27001', 1095, 365, true), -- 3 years for ISO27001
    ('default', 1095, 365, true)   -- 3 years default retention
ON CONFLICT (framework) DO NOTHING;

-- Insert default audit settings
INSERT INTO audit_settings (setting_key, setting_value, description) VALUES
    ('global_audit_enabled', 'true', 'Global audit logging enabled/disabled'),
    ('high_risk_alert_threshold', '10', 'Number of high-risk events in 1 hour to trigger alert'),
    ('failed_login_threshold', '5', 'Number of failed login attempts to trigger alert'),
    ('suspicious_ip_threshold', '50', 'Number of requests from single IP per minute to flag as suspicious'),
    ('data_export_notification', 'true', 'Send notifications for data export events'),
    ('gdpr_monitoring_enabled', 'true', 'Monitor GDPR-related events'),
    ('real_time_alerting', 'true', 'Enable real-time compliance alerting')
ON CONFLICT (setting_key) DO NOTHING;

-- Insert default compliance rules
INSERT INTO compliance_rules (framework, rule_name, rule_type, rule_config, alert_severity) VALUES
    ('sox', 'Failed Financial Transactions', 'threshold', '{"event_type": "financial_transaction", "outcome": "failure", "threshold": 5, "time_window": "1h"}', 'high'),
    ('sox', 'Unauthorized Admin Access', 'pattern', '{"event_type": "admin_action", "risk_level": "high", "unauthorized": true}', 'critical'),
    ('pci', 'Cardholder Data Access', 'pattern', '{"resource_type": "cardholder_data", "event_type": "data_access"}', 'high'),
    ('pci', 'Failed Payment Processing', 'threshold', '{"event_type": "payment_processing", "outcome": "failure", "threshold": 10, "time_window": "5m"}', 'medium'),
    ('gdpr', 'PII Access Without Consent', 'pattern', '{"event_type": "pii_access", "consent_verified": false}', 'high'),
    ('gdpr', 'Mass Data Export', 'threshold', '{"action": "data_export", "records_threshold": 1000}', 'medium'),
    ('hipaa', 'PHI Access Outside Hours', 'pattern', '{"resource_type": "phi", "event_type": "data_access", "outside_business_hours": true}', 'medium'),
    ('general', 'Multiple Failed Logins', 'threshold', '{"event_type": "user_login", "outcome": "failure", "threshold": 5, "time_window": "15m"}', 'medium'),
    ('general', 'Privilege Escalation', 'pattern', '{"event_type": "permission_change", "action": "privilege_escalation"}', 'high'),
    ('general', 'Suspicious IP Activity', 'threshold', '{"suspicious_ip": true, "threshold": 100, "time_window": "1h"}', 'medium')
ON CONFLICT DO NOTHING;

-- Create views for common compliance queries
CREATE OR REPLACE VIEW compliance_dashboard AS
SELECT 
    framework,
    COUNT(*) as total_events,
    COUNT(CASE WHEN risk_level IN ('high', 'critical') THEN 1 END) as high_risk_events,
    COUNT(CASE WHEN outcome = 'failure' THEN 1 END) as failed_events,
    COUNT(CASE WHEN timestamp >= CURRENT_DATE THEN 1 END) as today_events,
    COUNT(CASE WHEN timestamp >= CURRENT_DATE - INTERVAL '7 days' THEN 1 END) as week_events
FROM audit_events ae, 
     unnest(ARRAY(SELECT jsonb_array_elements_text(compliance_frameworks))) as framework
WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY framework;

CREATE OR REPLACE VIEW recent_high_risk_events AS
SELECT 
    event_id,
    timestamp,
    event_type,
    user_id,
    action,
    risk_level,
    compliance_frameworks,
    details->>'description' as description
FROM audit_events
WHERE risk_level IN ('high', 'critical')
  AND timestamp >= CURRENT_DATE - INTERVAL '24 hours'
ORDER BY timestamp DESC;

CREATE OR REPLACE VIEW user_activity_summary AS
SELECT 
    user_id,
    COUNT(*) as total_events,
    COUNT(CASE WHEN outcome = 'failure' THEN 1 END) as failed_events,
    COUNT(CASE WHEN risk_level IN ('high', 'critical') THEN 1 END) as high_risk_events,
    MAX(timestamp) as last_activity,
    COUNT(DISTINCT ip_address) as unique_ips,
    COUNT(DISTINCT session_id) as unique_sessions
FROM audit_events
WHERE user_id IS NOT NULL
  AND timestamp >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY user_id
ORDER BY high_risk_events DESC, failed_events DESC;

-- Create function for automatic event archiving
CREATE OR REPLACE FUNCTION archive_old_events()
RETURNS INTEGER AS $$
DECLARE
    archive_count INTEGER := 0;
    policy RECORD;
BEGIN
    -- Archive events based on retention policies
    FOR policy IN 
        SELECT framework, archive_after_days 
        FROM retention_policies 
        WHERE archive_after_days IS NOT NULL
    LOOP
        -- Move events to archive table (create if not exists)
        CREATE TABLE IF NOT EXISTS audit_events_archive (LIKE audit_events INCLUDING ALL);
        
        WITH archived_events AS (
            DELETE FROM audit_events
            WHERE framework = ANY(compliance_frameworks::text[])
              AND timestamp < CURRENT_DATE - INTERVAL '1 day' * policy.archive_after_days
            RETURNING *
        )
        INSERT INTO audit_events_archive SELECT * FROM archived_events;
        
        GET DIAGNOSTICS archive_count = ROW_COUNT;
        
        INSERT INTO data_retention_log (action, table_name, records_affected, criteria, status)
        VALUES ('archive', 'audit_events', archive_count, 
                json_build_object('framework', policy.framework, 'days', policy.archive_after_days),
                'completed');
    END LOOP;
    
    RETURN archive_count;
END;
$$ LANGUAGE plpgsql;

-- Create function for data cleanup based on retention policies
CREATE OR REPLACE FUNCTION cleanup_expired_data()
RETURNS INTEGER AS $$
DECLARE
    cleanup_count INTEGER := 0;
    policy RECORD;
BEGIN
    -- Clean up expired data based on retention policies
    FOR policy IN 
        SELECT framework, retention_days 
        FROM retention_policies
    LOOP
        -- Delete from archive table
        DELETE FROM audit_events_archive
        WHERE framework = ANY(compliance_frameworks::text[])
          AND timestamp < CURRENT_DATE - INTERVAL '1 day' * policy.retention_days;
        
        GET DIAGNOSTICS cleanup_count = ROW_COUNT;
        
        INSERT INTO data_retention_log (action, table_name, records_affected, criteria, status)
        VALUES ('delete', 'audit_events_archive', cleanup_count,
                json_build_object('framework', policy.framework, 'retention_days', policy.retention_days),
                'completed');
    END LOOP;
    
    -- Clean up old alert history (keep for 1 year)
    DELETE FROM alert_history WHERE created_at < CURRENT_DATE - INTERVAL '365 days';
    GET DIAGNOSTICS cleanup_count = ROW_COUNT;
    
    INSERT INTO data_retention_log (action, table_name, records_affected, criteria, status)
    VALUES ('delete', 'alert_history', cleanup_count,
            '{"retention_days": 365}', 'completed');
    
    RETURN cleanup_count;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT USAGE ON SCHEMA public TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO postgres;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- Create a sample audit event for testing
INSERT INTO audit_events (
    event_type, user_id, action, outcome, risk_level, 
    compliance_frameworks, details, context
) VALUES (
    'system_initialization', 'system', 'database_setup', 'success', 'low',
    '["sox", "gdpr"]',
    '{"message": "Audit logging database initialized successfully"}',
    '{"component": "audit-logger", "version": "1.0.0"}'
);

-- Print initialization summary
DO $$
DECLARE
    event_count INTEGER;
    rule_count INTEGER;
    policy_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO event_count FROM audit_events;
    SELECT COUNT(*) INTO rule_count FROM compliance_rules;
    SELECT COUNT(*) INTO policy_count FROM retention_policies;
    
    RAISE NOTICE 'ActiveLog Audit Logging Database Initialized Successfully';
    RAISE NOTICE 'Audit events: %', event_count;
    RAISE NOTICE 'Compliance rules: %', rule_count;
    RAISE NOTICE 'Retention policies: %', policy_count;
    RAISE NOTICE 'Database ready for audit logging service';
END $$;