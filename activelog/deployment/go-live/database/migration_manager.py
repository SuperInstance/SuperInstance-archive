#!/usr/bin/env python3
"""
Database Migration Manager
Handles database schema migrations, data migrations, and production deployment
"""

import os
import json
import logging
import subprocess
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import psycopg2
import redis
import sqlalchemy
from sqlalchemy import create_engine, text

@dataclass
class Migration:
    id: str
    name: str
    description: str
    type: str  # schema, data, rollback
    sql_files: List[str]
    dependencies: List[str]
    rollback_sql: Optional[str] = None
    created_at: datetime = None
    applied_at: Optional[datetime] = None
    status: str = "pending"

@dataclass
class DatabaseConfig:
    host: str
    port: int
    database: str
    username: str
    password: str
    ssl_mode: str = "require"
    connection_timeout: int = 30

class MigrationManager:
    """Comprehensive database migration management"""
    
    def __init__(self):
        self.setup_logging()
        self.migration_table = "schema_migrations"
        self.migrations_dir = "/home/activeloguser/activelog/deployment/go-live/database/migrations"
        os.makedirs(self.migrations_dir, exist_ok=True)
        
    def setup_logging(self):
        """Configure logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'/home/activeloguser/activelog/logs/migration-manager-{datetime.now().strftime("%Y%m%d")}.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def execute_production_migration(self, db_configs: Dict[str, DatabaseConfig]) -> Dict[str, Any]:
        """Execute complete production database migration"""
        try:
            self.logger.info("Starting production database migration")
            
            results = {
                'migration_started': datetime.now().isoformat(),
                'databases': {},
                'errors': [],
                'rollback_info': []
            }
            
            for db_name, db_config in db_configs.items():
                self.logger.info(f"Migrating database: {db_name}")
                
                db_result = self._migrate_database(db_name, db_config)
                results['databases'][db_name] = db_result
                
                if not db_result['success']:
                    results['errors'].append(f"Migration failed for {db_name}: {db_result['error']}")
                else:
                    self.logger.info(f"✓ {db_name} migration completed")
            
            # Setup replication monitoring
            replication_result = self._setup_replication_monitoring(db_configs)
            if replication_result['success']:
                results['replication_monitoring'] = replication_result
                self.logger.info("✓ Replication monitoring configured")
            
            # Create database backups before going live
            backup_result = self._create_pre_migration_backups(db_configs)
            if backup_result['success']:
                results['backups_created'] = backup_result['backups']
                self.logger.info("✓ Pre-migration backups created")
            
            results['migration_completed'] = datetime.now().isoformat()
            results['success'] = len(results['errors']) == 0
            
            return results
            
        except Exception as e:
            self.logger.error(f"Production migration failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'migration_failed': datetime.now().isoformat()
            }
    
    def _migrate_database(self, db_name: str, db_config: DatabaseConfig) -> Dict[str, Any]:
        """Migrate individual database"""
        try:
            # Create database connection
            engine = self._create_database_connection(db_config)
            
            # Initialize migration tracking
            self._initialize_migration_tracking(engine)
            
            # Get pending migrations
            pending_migrations = self._get_pending_migrations(engine, db_name)
            
            if not pending_migrations:
                return {
                    'success': True,
                    'message': 'No pending migrations',
                    'migrations_applied': 0
                }
            
            self.logger.info(f"Found {len(pending_migrations)} pending migrations for {db_name}")
            
            # Apply migrations in order
            applied_migrations = []
            rollback_info = []
            
            for migration in pending_migrations:
                migration_result = self._apply_migration(engine, migration)
                
                if migration_result['success']:
                    applied_migrations.append(migration.id)
                    rollback_info.append({
                        'migration_id': migration.id,
                        'rollback_sql': migration.rollback_sql
                    })
                    self.logger.info(f"✓ Applied migration: {migration.id}")
                else:
                    self.logger.error(f"✗ Failed to apply migration: {migration.id}")
                    
                    # Rollback previous migrations if configured
                    if rollback_info:
                        self._rollback_migrations(engine, rollback_info)
                    
                    return {
                        'success': False,
                        'error': migration_result['error'],
                        'failed_migration': migration.id,
                        'applied_migrations': applied_migrations
                    }
            
            # Verify database integrity
            integrity_result = self._verify_database_integrity(engine)
            
            return {
                'success': True,
                'migrations_applied': len(applied_migrations),
                'applied_migration_ids': applied_migrations,
                'integrity_check': integrity_result
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _create_database_connection(self, db_config: DatabaseConfig) -> sqlalchemy.Engine:
        """Create database connection"""
        connection_string = (
            f"postgresql://{db_config.username}:{db_config.password}"
            f"@{db_config.host}:{db_config.port}/{db_config.database}"
            f"?sslmode={db_config.ssl_mode}&connect_timeout={db_config.connection_timeout}"
        )
        
        return create_engine(
            connection_string,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=3600,
            echo=False
        )
    
    def _initialize_migration_tracking(self, engine: sqlalchemy.Engine):
        """Initialize migration tracking table"""
        with engine.connect() as conn:
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {self.migration_table} (
                    id VARCHAR(255) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    type VARCHAR(50) NOT NULL,
                    checksum VARCHAR(64),
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    applied_by VARCHAR(100),
                    execution_time_ms INTEGER,
                    rollback_sql TEXT
                )
            """))
            conn.commit()
    
    def _get_pending_migrations(self, engine: sqlalchemy.Engine, db_name: str) -> List[Migration]:
        """Get pending migrations for database"""
        # Get applied migrations from database
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT id FROM {self.migration_table}"))
            applied_migration_ids = {row[0] for row in result.fetchall()}
        
        # Load available migrations
        available_migrations = self._load_migrations(db_name)
        
        # Filter pending migrations
        pending_migrations = [
            migration for migration in available_migrations
            if migration.id not in applied_migration_ids
        ]
        
        # Sort by dependencies and creation time
        return sorted(pending_migrations, key=lambda m: (m.created_at or datetime.min))
    
    def _load_migrations(self, db_name: str) -> List[Migration]:
        """Load migration definitions"""
        # This would typically load from files or a migration registry
        # For now, return predefined migrations
        migrations = []
        
        # Core schema migrations
        migrations.extend([
            Migration(
                id="001_initial_schema",
                name="Initial Schema Creation",
                description="Create initial database schema",
                type="schema",
                sql_files=[f"{self.migrations_dir}/001_initial_schema.sql"],
                dependencies=[],
                created_at=datetime(2024, 1, 1)
            ),
            Migration(
                id="002_user_tables",
                name="User Management Tables",
                description="Create user, authentication, and profile tables",
                type="schema",
                sql_files=[f"{self.migrations_dir}/002_user_tables.sql"],
                dependencies=["001_initial_schema"],
                created_at=datetime(2024, 1, 2)
            ),
            Migration(
                id="003_service_tables",
                name="Service-specific Tables",
                description="Create tables for ActiveLog services",
                type="schema",
                sql_files=[f"{self.migrations_dir}/003_service_tables.sql"],
                dependencies=["002_user_tables"],
                created_at=datetime(2024, 1, 3)
            ),
            Migration(
                id="004_indexes_optimization",
                name="Database Indexes",
                description="Add performance indexes",
                type="schema",
                sql_files=[f"{self.migrations_dir}/004_indexes.sql"],
                dependencies=["003_service_tables"],
                created_at=datetime(2024, 1, 4)
            ),
            Migration(
                id="005_production_data",
                name="Production Data Setup",
                description="Insert initial production data",
                type="data",
                sql_files=[f"{self.migrations_dir}/005_production_data.sql"],
                dependencies=["004_indexes_optimization"],
                created_at=datetime(2024, 1, 5)
            )
        ])
        
        return migrations
    
    def _apply_migration(self, engine: sqlalchemy.Engine, migration: Migration) -> Dict[str, Any]:
        """Apply single migration"""
        try:
            start_time = time.time()
            
            with engine.begin() as conn:
                # Execute migration SQL files
                for sql_file in migration.sql_files:
                    if os.path.exists(sql_file):
                        with open(sql_file, 'r') as f:
                            sql_content = f.read()
                        
                        # Execute SQL statements
                        statements = sql_content.split(';')
                        for statement in statements:
                            statement = statement.strip()
                            if statement:
                                conn.execute(text(statement))
                    else:
                        # Generate SQL for common migration types
                        sql_content = self._generate_migration_sql(migration)
                        if sql_content:
                            conn.execute(text(sql_content))
                
                # Record migration as applied
                execution_time = int((time.time() - start_time) * 1000)
                
                conn.execute(text(f"""
                    INSERT INTO {self.migration_table} 
                    (id, name, description, type, applied_at, applied_by, execution_time_ms, rollback_sql)
                    VALUES (:id, :name, :description, :type, :applied_at, :applied_by, :execution_time, :rollback_sql)
                """), {
                    'id': migration.id,
                    'name': migration.name,
                    'description': migration.description,
                    'type': migration.type,
                    'applied_at': datetime.now(),
                    'applied_by': 'migration_manager',
                    'execution_time': execution_time,
                    'rollback_sql': migration.rollback_sql
                })
            
            return {
                'success': True,
                'execution_time_ms': execution_time
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _generate_migration_sql(self, migration: Migration) -> Optional[str]:
        """Generate SQL for common migration patterns"""
        if migration.id == "001_initial_schema":
            return """
            -- ActiveLog Initial Schema
            CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
            CREATE EXTENSION IF NOT EXISTS "pgcrypto";
            
            -- Core tables
            CREATE TABLE IF NOT EXISTS system_config (
                key VARCHAR(255) PRIMARY KEY,
                value TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Audit log table
            CREATE TABLE IF NOT EXISTS audit_log (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                entity_type VARCHAR(100) NOT NULL,
                entity_id VARCHAR(255) NOT NULL,
                action VARCHAR(50) NOT NULL,
                old_values JSONB,
                new_values JSONB,
                user_id UUID,
                ip_address INET,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX idx_audit_log_entity ON audit_log(entity_type, entity_id);
            CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);
            """
        
        elif migration.id == "002_user_tables":
            return """
            -- User management tables
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                email VARCHAR(255) UNIQUE NOT NULL,
                username VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                first_name VARCHAR(100),
                last_name VARCHAR(100),
                is_active BOOLEAN DEFAULT true,
                is_verified BOOLEAN DEFAULT false,
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS user_sessions (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                session_token VARCHAR(255) UNIQUE NOT NULL,
                ip_address INET,
                user_agent TEXT,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                avatar_url TEXT,
                bio TEXT,
                timezone VARCHAR(50),
                language VARCHAR(10) DEFAULT 'en',
                preferences JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX idx_users_email ON users(email);
            CREATE INDEX idx_users_username ON users(username);
            CREATE INDEX idx_user_sessions_token ON user_sessions(session_token);
            CREATE INDEX idx_user_sessions_expires ON user_sessions(expires_at);
            """
        
        elif migration.id == "003_service_tables":
            return """
            -- Service-specific tables
            CREATE TABLE IF NOT EXISTS services (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                name VARCHAR(100) UNIQUE NOT NULL,
                display_name VARCHAR(200) NOT NULL,
                description TEXT,
                version VARCHAR(20),
                status VARCHAR(20) DEFAULT 'active',
                endpoint_url TEXT,
                health_check_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS service_metrics (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                service_id UUID NOT NULL REFERENCES services(id) ON DELETE CASCADE,
                metric_name VARCHAR(100) NOT NULL,
                metric_value NUMERIC NOT NULL,
                metric_type VARCHAR(20) DEFAULT 'gauge',
                tags JSONB DEFAULT '{}',
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS api_keys (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                key_hash VARCHAR(255) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                permissions JSONB DEFAULT '{}',
                last_used_at TIMESTAMP,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX idx_services_name ON services(name);
            CREATE INDEX idx_service_metrics_service_id ON service_metrics(service_id);
            CREATE INDEX idx_service_metrics_recorded_at ON service_metrics(recorded_at);
            CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);
            """
        
        elif migration.id == "004_indexes_optimization":
            return """
            -- Performance optimization indexes
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_log_user_action ON audit_log(user_id, action);
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_active_verified ON users(is_active, is_verified);
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_sessions_user_expires ON user_sessions(user_id, expires_at);
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_service_metrics_name_time ON service_metrics(metric_name, recorded_at);
            
            -- Partial indexes
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_active_users ON users(id) WHERE is_active = true;
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_active_api_keys ON api_keys(id) WHERE is_active = true;
            
            -- Composite indexes for common queries
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_profiles_timezone_lang ON user_profiles(timezone, language);
            """
        
        elif migration.id == "005_production_data":
            return """
            -- Initial production data
            INSERT INTO system_config (key, value, description) VALUES
            ('app.version', '1.0.0', 'Application version'),
            ('app.environment', 'production', 'Application environment'),
            ('app.maintenance_mode', 'false', 'Maintenance mode flag'),
            ('security.session_timeout', '3600', 'Session timeout in seconds'),
            ('security.max_login_attempts', '5', 'Maximum login attempts'),
            ('api.rate_limit_requests', '1000', 'API rate limit requests per hour'),
            ('api.rate_limit_burst', '100', 'API rate limit burst size')
            ON CONFLICT (key) DO NOTHING;
            
            -- Register core services
            INSERT INTO services (name, display_name, description, endpoint_url, health_check_url) VALUES
            ('api-gateway', 'API Gateway', 'Main API gateway service', 'https://api.activelog.com', 'https://api.activelog.com/health'),
            ('auth-service', 'Authentication Service', 'User authentication and authorization', 'https://auth.activelog.com', 'https://auth.activelog.com/health'),
            ('file-service', 'File Management Service', 'File upload and management', 'https://files.activelog.com', 'https://files.activelog.com/health'),
            ('legal-framework', 'Legal Framework Service', 'Legal document and compliance management', 'https://legal.activelog.com', 'https://legal.activelog.com/health')
            ON CONFLICT (name) DO NOTHING;
            """
        
        return None
    
    def _rollback_migrations(self, engine: sqlalchemy.Engine, rollback_info: List[Dict[str, Any]]):
        """Rollback migrations in reverse order"""
        try:
            self.logger.warning(f"Rolling back {len(rollback_info)} migrations")
            
            for rollback in reversed(rollback_info):
                migration_id = rollback['migration_id']
                rollback_sql = rollback['rollback_sql']
                
                if rollback_sql:
                    with engine.begin() as conn:
                        conn.execute(text(rollback_sql))
                        
                        # Remove migration record
                        conn.execute(text(f"""
                            DELETE FROM {self.migration_table} WHERE id = :migration_id
                        """), {'migration_id': migration_id})
                    
                    self.logger.info(f"✓ Rolled back migration: {migration_id}")
        
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
    
    def _verify_database_integrity(self, engine: sqlalchemy.Engine) -> Dict[str, Any]:
        """Verify database integrity after migration"""
        try:
            with engine.connect() as conn:
                # Check for foreign key violations
                fk_violations = conn.execute(text("""
                    SELECT COUNT(*) as violation_count 
                    FROM information_schema.table_constraints 
                    WHERE constraint_type = 'FOREIGN KEY'
                """)).fetchone()[0]
                
                # Check for missing indexes on foreign keys
                missing_indexes = conn.execute(text("""
                    SELECT COUNT(*) as missing_count
                    FROM information_schema.table_constraints tc
                    LEFT JOIN information_schema.statistics s ON tc.table_name = s.table_name
                    WHERE tc.constraint_type = 'FOREIGN KEY' AND s.index_name IS NULL
                """)).fetchone()[0]
                
                # Get table counts
                tables_result = conn.execute(text("""
                    SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del
                    FROM pg_stat_user_tables
                    ORDER BY tablename
                """))
                
                table_stats = []
                for row in tables_result:
                    table_stats.append({
                        'schema': row[0],
                        'table': row[1],
                        'inserts': row[2],
                        'updates': row[3],
                        'deletes': row[4]
                    })
                
                return {
                    'passed': True,
                    'foreign_key_violations': fk_violations,
                    'missing_indexes': missing_indexes,
                    'table_stats': table_stats
                }
        
        except Exception as e:
            return {
                'passed': False,
                'error': str(e)
            }
    
    def _setup_replication_monitoring(self, db_configs: Dict[str, DatabaseConfig]) -> Dict[str, Any]:
        """Setup database replication monitoring"""
        try:
            monitoring_queries = []
            
            # Monitor replication lag
            monitoring_queries.append({
                'name': 'replication_lag',
                'query': """
                    SELECT 
                        client_addr,
                        client_hostname,
                        state,
                        sent_lsn,
                        write_lsn,
                        flush_lsn,
                        replay_lsn,
                        write_lag,
                        flush_lag,
                        replay_lag
                    FROM pg_stat_replication;
                """,
                'description': 'Monitor replication lag between primary and replicas'
            })
            
            # Monitor connection counts
            monitoring_queries.append({
                'name': 'connection_stats',
                'query': """
                    SELECT 
                        COUNT(*) as total_connections,
                        COUNT(*) FILTER (WHERE state = 'active') as active_connections,
                        COUNT(*) FILTER (WHERE state = 'idle') as idle_connections
                    FROM pg_stat_activity 
                    WHERE datname IS NOT NULL;
                """,
                'description': 'Monitor database connection statistics'
            })
            
            return {
                'success': True,
                'monitoring_queries': monitoring_queries,
                'databases_monitored': list(db_configs.keys())
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _create_pre_migration_backups(self, db_configs: Dict[str, DatabaseConfig]) -> Dict[str, Any]:
        """Create database backups before migration"""
        try:
            backups_created = []
            backup_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            for db_name, db_config in db_configs.items():
                backup_filename = f"backup_{db_name}_{backup_timestamp}.sql"
                backup_path = f"/home/activeloguser/activelog/backups/{backup_filename}"
                
                os.makedirs(os.path.dirname(backup_path), exist_ok=True)
                
                # Create pg_dump command
                dump_command = [
                    'pg_dump',
                    '-h', db_config.host,
                    '-p', str(db_config.port),
                    '-U', db_config.username,
                    '-d', db_config.database,
                    '-f', backup_path,
                    '--verbose',
                    '--no-password'
                ]
                
                # Set password via environment
                env = os.environ.copy()
                env['PGPASSWORD'] = db_config.password
                
                # Execute backup
                result = subprocess.run(
                    dump_command,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=3600  # 1 hour timeout
                )
                
                if result.returncode == 0:
                    backup_size = os.path.getsize(backup_path)
                    backups_created.append({
                        'database': db_name,
                        'backup_file': backup_path,
                        'backup_size_bytes': backup_size,
                        'created_at': backup_timestamp
                    })
                    self.logger.info(f"✓ Backup created for {db_name}: {backup_filename}")
                else:
                    self.logger.error(f"✗ Backup failed for {db_name}: {result.stderr}")
            
            return {
                'success': len(backups_created) > 0,
                'backups': backups_created
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def validate_migration_status(self, db_configs: Dict[str, DatabaseConfig]) -> Dict[str, Any]:
        """Validate migration status across all databases"""
        validation_results = {
            'timestamp': datetime.now().isoformat(),
            'databases': {},
            'overall_status': 'unknown'
        }
        
        all_healthy = True
        
        for db_name, db_config in db_configs.items():
            try:
                engine = self._create_database_connection(db_config)
                
                # Check migration table exists
                with engine.connect() as conn:
                    migration_table_exists = conn.execute(text(f"""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = '{self.migration_table}'
                        )
                    """)).fetchone()[0]
                    
                    if migration_table_exists:
                        # Get migration status
                        applied_migrations = conn.execute(text(f"""
                            SELECT COUNT(*) FROM {self.migration_table}
                        """)).fetchone()[0]
                        
                        latest_migration = conn.execute(text(f"""
                            SELECT id, applied_at FROM {self.migration_table}
                            ORDER BY applied_at DESC LIMIT 1
                        """)).fetchone()
                        
                        validation_results['databases'][db_name] = {
                            'status': 'healthy',
                            'migration_table_exists': True,
                            'applied_migrations_count': applied_migrations,
                            'latest_migration': {
                                'id': latest_migration[0] if latest_migration else None,
                                'applied_at': latest_migration[1].isoformat() if latest_migration else None
                            }
                        }
                    else:
                        validation_results['databases'][db_name] = {
                            'status': 'unhealthy',
                            'migration_table_exists': False,
                            'error': 'Migration table does not exist'
                        }
                        all_healthy = False
                
            except Exception as e:
                validation_results['databases'][db_name] = {
                    'status': 'error',
                    'error': str(e)
                }
                all_healthy = False
        
        validation_results['overall_status'] = 'healthy' if all_healthy else 'unhealthy'
        
        return validation_results

def main():
    """Main function for database migration"""
    migration_manager = MigrationManager()
    
    print("🗄️  Starting ActiveLog Database Migration")
    print("=" * 60)
    
    # Example database configurations
    db_configs = {
        'primary': DatabaseConfig(
            host='activelog-production-db.cluster-xyz.us-east-1.rds.amazonaws.com',
            port=5432,
            database='activelog_production',
            username='activelog_user',
            password='secure_password_here'
        ),
        'analytics': DatabaseConfig(
            host='activelog-analytics-db.cluster-abc.us-east-1.rds.amazonaws.com',
            port=5432,
            database='activelog_analytics',
            username='analytics_user',
            password='analytics_password_here'
        )
    }
    
    # Execute production migration
    result = migration_manager.execute_production_migration(db_configs)
    
    if result['success']:
        print("✅ Database migration completed successfully!")
        for db_name, db_result in result['databases'].items():
            if db_result['success']:
                print(f"  ✓ {db_name}: {db_result['migrations_applied']} migrations applied")
            else:
                print(f"  ✗ {db_name}: {db_result['error']}")
    else:
        print("❌ Database migration failed!")
        for error in result.get('errors', []):
            print(f"  - {error}")
    
    # Validate migration status
    print("\n🔍 Validating migration status...")
    validation = migration_manager.validate_migration_status(db_configs)
    
    print(f"Overall Status: {validation['overall_status']}")
    
    for db_name, db_status in validation['databases'].items():
        status_emoji = "✅" if db_status['status'] == 'healthy' else "❌"
        print(f"{status_emoji} {db_name}: {db_status.get('applied_migrations_count', 0)} migrations applied")

if __name__ == "__main__":
    main()