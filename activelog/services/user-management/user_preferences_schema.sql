-- User Management Service Database Extensions
-- EDUCATIONAL: Extends ActiveLog schema with user preference management
-- INTEGRATION: Designed for AI insights service collaboration

-- User preferences storage (flexible JSON approach)
CREATE TABLE IF NOT EXISTS user_preferences (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id TEXT NOT NULL REFERENCES users(id),
    preference_type TEXT NOT NULL, -- fitness_preferences, ui_preferences, privacy_settings
    preference_data TEXT NOT NULL, -- JSON data
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, preference_type)
);

-- User goals tracking
CREATE TABLE IF NOT EXISTS user_goals (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id TEXT NOT NULL REFERENCES users(id),
    goal_type TEXT NOT NULL, -- weight_loss, muscle_gain, endurance, strength, custom
    target_value REAL, -- Optional numeric target
    target_date TEXT, -- ISO date string
    priority INTEGER NOT NULL DEFAULT 1 CHECK(priority BETWEEN 1 AND 5),
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'completed', 'paused', 'cancelled')),
    progress_percentage REAL DEFAULT 0.0 CHECK(progress_percentage BETWEEN 0.0 AND 100.0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- User activity sessions (for analytics and insights)
CREATE TABLE IF NOT EXISTS user_activity_sessions (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id TEXT NOT NULL REFERENCES users(id),
    session_start TEXT NOT NULL,
    session_end TEXT,
    actions_performed INTEGER DEFAULT 0,
    features_used TEXT, -- JSON array of features accessed
    device_type TEXT, -- mobile, web, tablet
    session_quality_score REAL, -- For user experience optimization
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- User notification preferences
CREATE TABLE IF NOT EXISTS user_notifications (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id TEXT NOT NULL REFERENCES users(id),
    notification_type TEXT NOT NULL, -- workout_reminder, goal_progress, ai_insights, social
    enabled BOOLEAN NOT NULL DEFAULT true,
    frequency TEXT NOT NULL DEFAULT 'weekly', -- daily, weekly, monthly, disabled
    delivery_method TEXT NOT NULL DEFAULT 'push', -- push, email, sms
    custom_settings TEXT, -- JSON for type-specific settings
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, notification_type)
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON user_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_user_preferences_type ON user_preferences(preference_type);
CREATE INDEX IF NOT EXISTS idx_user_goals_user_id ON user_goals(user_id);
CREATE INDEX IF NOT EXISTS idx_user_goals_status ON user_goals(status);
CREATE INDEX IF NOT EXISTS idx_user_goals_type ON user_goals(goal_type);
CREATE INDEX IF NOT EXISTS idx_user_activity_sessions_user_id ON user_activity_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_notifications_user_id ON user_notifications(user_id);

-- INTEGRATION: Views for common queries used by AI insights service
CREATE OR REPLACE VIEW user_ai_context AS
SELECT 
    u.id as user_id,
    u.email,
    fp.fitness_level,
    fp.goals as fitness_goals,
    up_fitness.preference_data as fitness_preferences,
    up_privacy.preference_data as privacy_settings,
    COUNT(ws.id) as total_workouts,
    AVG(ws.duration_minutes) as avg_workout_duration,
    COUNT(ug.id) as active_goals_count
FROM users u
LEFT JOIN fitness_profiles fp ON u.id = fp.user_id
LEFT JOIN user_preferences up_fitness ON u.id = up_fitness.user_id AND up_fitness.preference_type = 'fitness_preferences'
LEFT JOIN user_preferences up_privacy ON u.id = up_privacy.user_id AND up_privacy.preference_type = 'privacy_settings'
LEFT JOIN workout_sessions ws ON u.id = ws.user_id
LEFT JOIN user_goals ug ON u.id = ug.user_id AND ug.status = 'active'
GROUP BY u.id, u.email, fp.fitness_level, fp.goals, up_fitness.preference_data, up_privacy.preference_data;

-- ANALYTICS: User engagement metrics for optimization
CREATE OR REPLACE VIEW user_engagement_metrics AS
SELECT 
    user_id,
    COUNT(DISTINCT DATE(session_start)) as active_days_count,
    AVG(actions_performed) as avg_actions_per_session,
    MAX(session_end::timestamp - session_start::timestamp) as longest_session_duration,
    AVG(session_quality_score) as avg_session_quality,
    COUNT(*) as total_sessions
FROM user_activity_sessions
WHERE session_start >= (CURRENT_DATE - INTERVAL '30 days')::text
GROUP BY user_id;

-- FUTURE BOT FUNCTIONS

-- Function to calculate goal progress based on workout data
CREATE OR REPLACE FUNCTION calculate_goal_progress(target_user_id TEXT, target_goal_id TEXT)
RETURNS REAL AS $$
DECLARE
    goal_record RECORD;
    progress_value REAL := 0.0;
BEGIN
    -- Get goal details
    SELECT * INTO goal_record FROM user_goals WHERE id = target_goal_id AND user_id = target_user_id;
    
    IF NOT FOUND THEN
        RETURN 0.0;
    END IF;
    
    -- Calculate progress based on goal type
    CASE goal_record.goal_type
        WHEN 'weight_loss' THEN
            -- TODO: Calculate based on body measurements
            progress_value := 0.0;
        WHEN 'endurance' THEN
            -- TODO: Calculate based on workout duration improvements
            SELECT COALESCE(AVG(duration_minutes), 0) INTO progress_value
            FROM workout_sessions 
            WHERE user_id = target_user_id 
                AND workout_type = 'cardio'
                AND started_at >= (CURRENT_DATE - INTERVAL '30 days')::text;
        WHEN 'strength' THEN
            -- TODO: Calculate based on weight progression
            progress_value := 0.0;
        ELSE
            progress_value := 0.0;
    END CASE;
    
    RETURN LEAST(progress_value, 100.0);
END;
$$ LANGUAGE plpgsql;

-- EDUCATIONAL COMMENTS FOR FUTURE USER MANAGEMENT SPECIALISTS:
COMMENT ON TABLE user_preferences IS 'FLEXIBLE: JSON storage allows rapid iteration of preference types without schema changes';
COMMENT ON TABLE user_goals IS 'AI INTEGRATION: Goal tracking enables personalized workout recommendations and progress insights';
COMMENT ON VIEW user_ai_context IS 'OPTIMIZATION: Pre-computed user context for AI service integration reduces query complexity';

-- COLLABORATION HINTS FOR FUTURE BOTS:
COMMENT ON TABLE user_activity_sessions IS 'ANALYTICS: Session tracking enables user experience optimization and feature usage insights';
COMMENT ON FUNCTION calculate_goal_progress IS 'PUZZLE: Implement smart progress calculation algorithms based on workout patterns and body measurements';