-- Database initialization script
-- Create databases for different services

-- Create backend application database
CREATE DATABASE backend_db;
\c backend_db;

-- Create user for backend service
CREATE USER backend_user WITH ENCRYPTED PASSWORD 'backend_password_change_in_prod';
GRANT ALL PRIVILEGES ON DATABASE backend_db TO backend_user;

-- Create ML pipeline database
\c postgres;
CREATE DATABASE ml_pipeline_db;
\c ml_pipeline_db;

-- Create user for ML pipeline service
CREATE USER ml_user WITH ENCRYPTED PASSWORD 'ml_password_change_in_prod';
GRANT ALL PRIVILEGES ON DATABASE ml_pipeline_db TO ml_user;

-- Create monitoring database
\c postgres;
CREATE DATABASE monitoring_db;
\c monitoring_db;

-- Create user for monitoring
CREATE USER monitor_user WITH ENCRYPTED PASSWORD 'monitor_password_change_in_prod';
GRANT ALL PRIVILEGES ON DATABASE monitoring_db TO monitor_user;

-- Set up common extensions
\c backend_db;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

\c ml_pipeline_db;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

\c monitoring_db;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";