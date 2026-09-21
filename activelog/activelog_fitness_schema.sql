-- ActiveLog Fitness Domain Schema Design
-- Created by Foreman to accelerate Bot-Domains work
-- SuperInstance Rebranding Priority

-- Core fitness tracking tables
CREATE TABLE fitness_profiles (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    height_cm INTEGER,
    weight_kg REAL,
    age INTEGER,
    fitness_level TEXT CHECK(fitness_level IN ('beginner', 'intermediate', 'advanced', 'athlete')),
    goals TEXT, -- JSON array of fitness goals
    medical_conditions TEXT, -- JSON array of relevant conditions
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Workout sessions
CREATE TABLE workout_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    workout_type TEXT NOT NULL, -- cardio, strength, flexibility, sports
    duration_minutes INTEGER NOT NULL,
    calories_burned INTEGER,
    perceived_exertion INTEGER CHECK(perceived_exertion BETWEEN 1 AND 10),
    notes TEXT,
    location TEXT,
    weather_conditions TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Individual exercises within workouts
CREATE TABLE exercise_entries (
    id TEXT PRIMARY KEY,
    workout_session_id TEXT NOT NULL REFERENCES workout_sessions(id),
    exercise_name TEXT NOT NULL,
    exercise_type TEXT NOT NULL, -- strength, cardio, flexibility
    sets INTEGER,
    reps INTEGER,
    weight_kg REAL,
    distance_km REAL,
    duration_seconds INTEGER,
    rest_seconds INTEGER,
    notes TEXT,
    form_rating INTEGER CHECK(form_rating BETWEEN 1 AND 5),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Nutrition logging
CREATE TABLE nutrition_entries (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    meal_type TEXT CHECK(meal_type IN ('breakfast', 'lunch', 'dinner', 'snack')),
    food_item TEXT NOT NULL,
    quantity REAL NOT NULL,
    unit TEXT NOT NULL, -- grams, cups, pieces, etc
    calories INTEGER,
    protein_g REAL,
    carbs_g REAL,
    fat_g REAL,
    fiber_g REAL,
    consumed_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Body measurements and progress tracking  
CREATE TABLE body_measurements (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    measurement_type TEXT NOT NULL, -- weight, body_fat, muscle_mass, waist, chest, etc
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    measurement_date TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Wearable device integration
CREATE TABLE wearable_data (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    device_type TEXT NOT NULL, -- fitbit, apple_watch, garmin, etc
    data_type TEXT NOT NULL, -- heart_rate, steps, sleep, etc
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    synced_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Performance analytics and trends
CREATE TABLE fitness_analytics (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    metric_type TEXT NOT NULL, -- strength_trend, endurance_improvement, weight_loss_rate
    metric_value REAL NOT NULL,
    calculation_period TEXT NOT NULL, -- weekly, monthly, quarterly
    calculated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT -- JSON with calculation details
);

-- Cross-domain correlation for SuperInstance
CREATE TABLE cross_domain_correlations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    fitness_metric TEXT NOT NULL,
    fitness_value REAL NOT NULL,
    correlation_domain TEXT NOT NULL, -- personal, business, gaming
    correlation_metric TEXT NOT NULL,
    correlation_value REAL NOT NULL,
    correlation_strength REAL, -- -1 to 1
    time_period TEXT NOT NULL,
    calculated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_fitness_profiles_user_id ON fitness_profiles(user_id);
CREATE INDEX idx_workout_sessions_user_id ON workout_sessions(user_id);
CREATE INDEX idx_workout_sessions_started_at ON workout_sessions(started_at);
CREATE INDEX idx_exercise_entries_workout_id ON exercise_entries(workout_session_id);
CREATE INDEX idx_nutrition_entries_user_id ON nutrition_entries(user_id);
CREATE INDEX idx_nutrition_entries_consumed_at ON nutrition_entries(consumed_at);
CREATE INDEX idx_body_measurements_user_id ON body_measurements(user_id);
CREATE INDEX idx_body_measurements_type_date ON body_measurements(measurement_type, measurement_date);
CREATE INDEX idx_wearable_data_user_id ON wearable_data(user_id);
CREATE INDEX idx_wearable_data_recorded_at ON wearable_data(recorded_at);
CREATE INDEX idx_fitness_analytics_user_id ON fitness_analytics(user_id);
CREATE INDEX idx_cross_domain_correlations_user_id ON cross_domain_correlations(user_id);