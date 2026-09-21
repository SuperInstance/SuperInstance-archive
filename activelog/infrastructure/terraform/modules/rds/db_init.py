"""
Database initialization Lambda function for ActiveLog
Installs pgvector extension and creates initial schema
"""

import json
import os
import boto3
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def get_secret_value(secret_arn):
    """Retrieve secret value from AWS Secrets Manager"""
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_arn)
    return response['SecretString']

def handler(event, context):
    """Lambda handler for database initialization"""
    
    try:
        # Get database connection parameters
        db_host = os.environ['DB_HOST']
        db_name = os.environ['DB_NAME']
        db_username = os.environ['DB_USERNAME']
        secret_arn = os.environ['SECRET_ARN']
        
        # Get password from Secrets Manager
        db_password = get_secret_value(secret_arn)
        
        # Connect to PostgreSQL
        connection = psycopg2.connect(
            host=db_host,
            database=db_name,
            user=db_username,
            password=db_password,
            port=5432
        )
        
        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = connection.cursor()
        
        print("Connected to database successfully")
        
        # Install pgvector extension
        try:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            print("pgvector extension installed successfully")
        except Exception as e:
            print(f"Error installing pgvector extension: {e}")
            # Don't fail if extension already exists
        
        # Install pg_trgm extension for trigram search
        try:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
            print("pg_trgm extension installed successfully")
        except Exception as e:
            print(f"Error installing pg_trgm extension: {e}")
        
        # Install uuid-ossp extension
        try:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")
            print("uuid-ossp extension installed successfully")
        except Exception as e:
            print(f"Error installing uuid-ossp extension: {e}")
        
        # Create initial schema
        schema_sql = """
        -- Users table
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(255),
            is_active BOOLEAN DEFAULT true,
            is_verified BOOLEAN DEFAULT false,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Files table
        CREATE TABLE IF NOT EXISTS files (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            filename VARCHAR(255) NOT NULL,
            original_filename VARCHAR(255) NOT NULL,
            file_path VARCHAR(500) NOT NULL,
            file_size BIGINT NOT NULL,
            mime_type VARCHAR(100) NOT NULL,
            checksum VARCHAR(64) NOT NULL,
            upload_status VARCHAR(50) DEFAULT 'pending',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        -- File metadata table
        CREATE TABLE IF NOT EXISTS file_metadata (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            file_id UUID NOT NULL REFERENCES files(id) ON DELETE CASCADE,
            extracted_text TEXT,
            summary TEXT,
            tags TEXT[],
            metadata_json JSONB,
            processing_status VARCHAR(50) DEFAULT 'pending',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        -- File embeddings table with vector support
        CREATE TABLE IF NOT EXISTS file_embeddings (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            file_id UUID NOT NULL REFERENCES files(id) ON DELETE CASCADE,
            embedding vector(1536),
            embedding_model VARCHAR(100) DEFAULT 'text-embedding-ada-002',
            chunk_index INTEGER DEFAULT 0,
            chunk_text TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Search history table
        CREATE TABLE IF NOT EXISTS search_history (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            query TEXT NOT NULL,
            results_count INTEGER DEFAULT 0,
            execution_time_ms INTEGER,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        -- User sessions table
        CREATE TABLE IF NOT EXISTS user_sessions (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            session_token VARCHAR(255) NOT NULL UNIQUE,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Notifications table
        CREATE TABLE IF NOT EXISTS notifications (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title VARCHAR(255) NOT NULL,
            message TEXT NOT NULL,
            notification_type VARCHAR(50) NOT NULL,
            is_read BOOLEAN DEFAULT false,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        cursor.execute(schema_sql)
        print("Initial schema created successfully")
        
        # Create indexes for performance
        indexes_sql = """
        -- Indexes for users table
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);
        
        -- Indexes for files table
        CREATE INDEX IF NOT EXISTS idx_files_user_id ON files(user_id);
        CREATE INDEX IF NOT EXISTS idx_files_created_at ON files(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_files_filename ON files(filename);
        CREATE INDEX IF NOT EXISTS idx_files_path_trgm ON files USING gin(file_path gin_trgm_ops);
        
        -- Indexes for file metadata
        CREATE INDEX IF NOT EXISTS idx_file_metadata_file_id ON file_metadata(file_id);
        CREATE INDEX IF NOT EXISTS idx_file_metadata_tags ON file_metadata USING gin(tags);
        CREATE INDEX IF NOT EXISTS idx_file_metadata_text_trgm ON file_metadata USING gin(extracted_text gin_trgm_ops);
        
        -- Indexes for embeddings (vector similarity search)
        CREATE INDEX IF NOT EXISTS idx_file_embeddings_file_id ON file_embeddings(file_id);
        CREATE INDEX IF NOT EXISTS idx_file_embeddings_vector_hnsw ON file_embeddings USING hnsw (embedding vector_cosine_ops);
        
        -- Indexes for search history
        CREATE INDEX IF NOT EXISTS idx_search_history_user_id ON search_history(user_id);
        CREATE INDEX IF NOT EXISTS idx_search_history_created_at ON search_history(created_at DESC);
        
        -- Indexes for sessions
        CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(session_token);
        CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions(expires_at);
        
        -- Indexes for notifications
        CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
        CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read);
        """
        
        cursor.execute(indexes_sql)
        print("Database indexes created successfully")
        
        # Create functions for updated_at triggers
        trigger_function_sql = """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        
        -- Create triggers for updated_at
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_users_updated_at') THEN
                CREATE TRIGGER update_users_updated_at 
                    BEFORE UPDATE ON users 
                    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
            END IF;
            
            IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_files_updated_at') THEN
                CREATE TRIGGER update_files_updated_at 
                    BEFORE UPDATE ON files 
                    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
            END IF;
            
            IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_file_metadata_updated_at') THEN
                CREATE TRIGGER update_file_metadata_updated_at 
                    BEFORE UPDATE ON file_metadata 
                    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
            END IF;
        END
        $$;
        """
        
        cursor.execute(trigger_function_sql)
        print("Database triggers created successfully")
        
        # Close connections
        cursor.close()
        connection.close()
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Database initialized successfully',
                'extensions': ['pgvector', 'pg_trgm', 'uuid-ossp'],
                'schema': 'created',
                'indexes': 'created',
                'triggers': 'created'
            })
        }
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to initialize database'
            })
        }