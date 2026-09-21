#!/usr/bin/env python3

"""
Database Migration Runner with Safety Features
Safe database migrations with automatic backups and rollback capabilities
"""

import os
import sys
import json
import psycopg2
import argparse
import logging
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict

@dataclass
class Migration:
    id: str
    name: str
    version: str
    description: str
    up_sql: str
    down_sql: str
    checksum: str
    dependencies: List[str] = None
    created_at: str = None
    applied_at: str = None

@dataclass
class MigrationResult:
    success: bool
    migration_id: str
    error_message: str = None
    execution_time: float = 0.0
    affected_rows: int = 0

class MigrationRunner:
    def __init__(self, environment: str = "beta", db_config: Dict = None):
        self.environment = environment
        self.db_config = db_config or self._load_db_config()
        self.migrations_dir = Path(__file__).parent / "sql"
        self.logger = logging.getLogger(__name__)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(Path(__file__).parent / "migration.log"),
                logging.StreamHandler()
            ]
        )
        
        self._init_migration_table()

    def _load_db_config(self) -> Dict:
        """Load database configuration"""
        config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", 5432)),
            "database": os.getenv("DB_NAME", f"activelog_{self.environment}"),
            "user": os.getenv("DB_USER", "activelog_user"),
            "password": os.getenv("DB_PASSWORD", ""),
        }
        
        # Try to read password from file if not in env
        password_file = os.getenv("DB_PASSWORD_FILE")
        if password_file and Path(password_file).exists():
            config["password"] = Path(password_file).read_text().strip()
        
        return config

    def _get_connection(self):
        """Get database connection"""
        try:
            return psycopg2.connect(**self.db_config)
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")
            raise

    def _init_migration_table(self):
        """Initialize migration tracking table"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id VARCHAR(255) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    version VARCHAR(50) NOT NULL,
                    description TEXT,
                    checksum VARCHAR(64) NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    execution_time_ms INTEGER,
                    environment VARCHAR(50) NOT NULL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS migration_backups (
                    id SERIAL PRIMARY KEY,
                    migration_id VARCHAR(255) NOT NULL,
                    backup_file VARCHAR(500) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    environment VARCHAR(50) NOT NULL
                )
            ''')
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Failed to initialize migration table: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def _calculate_checksum(self, content: str) -> str:
        """Calculate checksum for migration content"""
        return hashlib.sha256(content.encode()).hexdigest()

    def _parse_migration_file(self, file_path: Path) -> Migration:
        """Parse migration file and extract metadata"""
        content = file_path.read_text()
        
        # Extract metadata from comments
        metadata = {}
        lines = content.split('\n')
        
        for line in lines:
            if line.strip().startswith('-- @'):
                key, value = line.strip()[4:].split(':', 1)
                metadata[key.strip()] = value.strip()
        
        # Split UP and DOWN migrations
        up_sql = ""
        down_sql = ""
        current_section = "up"
        
        for line in lines:
            if line.strip().startswith('-- DOWN'):
                current_section = "down"
                continue
            elif line.strip().startswith('-- UP'):
                current_section = "up"
                continue
            elif line.strip().startswith('--'):
                continue
            
            if current_section == "up":
                up_sql += line + '\n'
            else:
                down_sql += line + '\n'
        
        # Generate migration ID from filename
        migration_id = file_path.stem
        
        migration = Migration(
            id=migration_id,
            name=metadata.get('name', migration_id),
            version=metadata.get('version', '1.0.0'),
            description=metadata.get('description', ''),
            up_sql=up_sql.strip(),
            down_sql=down_sql.strip(),
            checksum=self._calculate_checksum(up_sql),
            dependencies=metadata.get('dependencies', '').split(',') if metadata.get('dependencies') else [],
            created_at=datetime.now().isoformat()
        )
        
        return migration

    def _load_migrations(self) -> List[Migration]:
        """Load all migration files"""
        migrations = []
        
        if not self.migrations_dir.exists():
            self.logger.warning(f"Migrations directory not found: {self.migrations_dir}")
            return migrations
        
        for file_path in sorted(self.migrations_dir.glob("*.sql")):
            try:
                migration = self._parse_migration_file(file_path)
                migrations.append(migration)
                self.logger.debug(f"Loaded migration: {migration.id}")
            except Exception as e:
                self.logger.error(f"Failed to parse migration {file_path}: {e}")
        
        return migrations

    def _get_applied_migrations(self) -> List[str]:
        """Get list of already applied migrations"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT id FROM schema_migrations WHERE environment = %s ORDER BY applied_at",
                (self.environment,)
            )
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Failed to get applied migrations: {e}")
            return []
        finally:
            cursor.close()
            conn.close()

    def _check_migration_integrity(self, migration: Migration) -> bool:
        """Check if migration has been modified since last application"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT checksum FROM schema_migrations WHERE id = %s AND environment = %s",
                (migration.id, self.environment)
            )
            row = cursor.fetchone()
            
            if row and row[0] != migration.checksum:
                self.logger.error(f"Migration {migration.id} checksum mismatch - migration may have been modified")
                return False
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to check migration integrity: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    def _create_backup(self, migration_id: str, backup_file: str = None) -> str:
        """Create database backup before migration"""
        if not backup_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f"/app/backups/pre-migration-{migration_id}-{timestamp}.sql"
        
        # Ensure backup directory exists
        Path(backup_file).parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Create backup using pg_dump
            cmd = [
                "pg_dump",
                f"--host={self.db_config['host']}",
                f"--port={self.db_config['port']}",
                f"--username={self.db_config['user']}",
                f"--dbname={self.db_config['database']}",
                "--no-password",
                "--verbose",
                "--clean",
                "--if-exists",
                "--create"
            ]
            
            env = os.environ.copy()
            env["PGPASSWORD"] = self.db_config["password"]
            
            with open(backup_file, 'w') as f:
                result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, 
                                      env=env, check=True)
            
            # Record backup in database
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO migration_backups (migration_id, backup_file, environment)
                VALUES (%s, %s, %s)
            ''', (migration_id, backup_file, self.environment))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            self.logger.info(f"Backup created: {backup_file}")
            return backup_file
            
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            raise

    def _apply_migration(self, migration: Migration, backup_file: str = None) -> MigrationResult:
        """Apply a single migration"""
        self.logger.info(f"Applying migration: {migration.id} - {migration.name}")
        
        start_time = datetime.now()
        
        # Create backup if specified
        if backup_file:
            self._create_backup(migration.id, backup_file)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Execute migration
            cursor.execute(migration.up_sql)
            affected_rows = cursor.rowcount
            
            # Record migration as applied
            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            cursor.execute('''
                INSERT INTO schema_migrations 
                (id, name, version, description, checksum, execution_time_ms, environment)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                migration.id,
                migration.name,
                migration.version,
                migration.description,
                migration.checksum,
                execution_time_ms,
                self.environment
            ))
            
            conn.commit()
            
            self.logger.info(f"Migration {migration.id} applied successfully in {execution_time_ms}ms")
            
            return MigrationResult(
                success=True,
                migration_id=migration.id,
                execution_time=execution_time_ms / 1000.0,
                affected_rows=affected_rows
            )
            
        except Exception as e:
            conn.rollback()
            error_msg = f"Migration {migration.id} failed: {e}"
            self.logger.error(error_msg)
            
            return MigrationResult(
                success=False,
                migration_id=migration.id,
                error_message=error_msg
            )
        finally:
            cursor.close()
            conn.close()

    def _rollback_migration(self, migration: Migration) -> MigrationResult:
        """Rollback a single migration"""
        self.logger.info(f"Rolling back migration: {migration.id}")
        
        if not migration.down_sql:
            error_msg = f"No rollback SQL provided for migration {migration.id}"
            self.logger.error(error_msg)
            return MigrationResult(False, migration.id, error_msg)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Execute rollback
            cursor.execute(migration.down_sql)
            affected_rows = cursor.rowcount
            
            # Remove migration record
            cursor.execute(
                "DELETE FROM schema_migrations WHERE id = %s AND environment = %s",
                (migration.id, self.environment)
            )
            
            conn.commit()
            
            self.logger.info(f"Migration {migration.id} rolled back successfully")
            
            return MigrationResult(
                success=True,
                migration_id=migration.id,
                affected_rows=affected_rows
            )
            
        except Exception as e:
            conn.rollback()
            error_msg = f"Rollback {migration.id} failed: {e}"
            self.logger.error(error_msg)
            
            return MigrationResult(
                success=False,
                migration_id=migration.id,
                error_message=error_msg
            )
        finally:
            cursor.close()
            conn.close()

    def migrate(self, target_version: str = None, backup_enabled: bool = True) -> List[MigrationResult]:
        """Run pending migrations"""
        self.logger.info(f"Starting migration for environment: {self.environment}")
        
        migrations = self._load_migrations()
        applied_migrations = self._get_applied_migrations()
        
        # Filter pending migrations
        pending_migrations = [m for m in migrations if m.id not in applied_migrations]
        
        if target_version:
            # Filter to specific version
            pending_migrations = [m for m in pending_migrations if m.version <= target_version]
        
        if not pending_migrations:
            self.logger.info("No pending migrations found")
            return []
        
        self.logger.info(f"Found {len(pending_migrations)} pending migrations")
        
        results = []
        
        for migration in pending_migrations:
            # Check integrity
            if not self._check_migration_integrity(migration):
                results.append(MigrationResult(
                    success=False,
                    migration_id=migration.id,
                    error_message="Migration integrity check failed"
                ))
                break
            
            # Apply migration
            backup_file = None
            if backup_enabled:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_file = f"/app/backups/pre-migration-{migration.id}-{timestamp}.sql"
            
            result = self._apply_migration(migration, backup_file)
            results.append(result)
            
            if not result.success:
                self.logger.error("Migration failed, stopping execution")
                break
        
        # Summary
        successful = len([r for r in results if r.success])
        failed = len([r for r in results if not r.success])
        
        self.logger.info(f"Migration completed: {successful} successful, {failed} failed")
        
        return results

    def rollback(self, target_migration: str = None) -> List[MigrationResult]:
        """Rollback migrations"""
        self.logger.info(f"Starting rollback for environment: {self.environment}")
        
        migrations = self._load_migrations()
        applied_migrations = self._get_applied_migrations()
        
        # Get migrations to rollback (in reverse order)
        migrations_to_rollback = []
        
        if target_migration:
            # Rollback to specific migration
            try:
                target_index = applied_migrations.index(target_migration)
                migrations_to_rollback = applied_migrations[target_index + 1:]
            except ValueError:
                self.logger.error(f"Target migration not found: {target_migration}")
                return []
        else:
            # Rollback last migration only
            if applied_migrations:
                migrations_to_rollback = [applied_migrations[-1]]
        
        if not migrations_to_rollback:
            self.logger.info("No migrations to rollback")
            return []
        
        # Reverse order for rollback
        migrations_to_rollback.reverse()
        
        self.logger.info(f"Rolling back {len(migrations_to_rollback)} migrations")
        
        results = []
        
        for migration_id in migrations_to_rollback:
            # Find migration object
            migration = next((m for m in migrations if m.id == migration_id), None)
            if not migration:
                self.logger.error(f"Migration not found: {migration_id}")
                continue
            
            result = self._rollback_migration(migration)
            results.append(result)
            
            if not result.success:
                self.logger.error("Rollback failed, stopping execution")
                break
        
        return results

    def status(self) -> Dict:
        """Get migration status"""
        migrations = self._load_migrations()
        applied_migrations = self._get_applied_migrations()
        
        pending_migrations = [m for m in migrations if m.id not in applied_migrations]
        
        return {
            "environment": self.environment,
            "total_migrations": len(migrations),
            "applied_migrations": len(applied_migrations),
            "pending_migrations": len(pending_migrations),
            "last_applied": applied_migrations[-1] if applied_migrations else None,
            "pending_list": [m.id for m in pending_migrations]
        }

def main():
    parser = argparse.ArgumentParser(description='Database Migration Runner')
    parser.add_argument('--environment', default='beta', help='Environment (beta/prod)')
    parser.add_argument('--action', choices=['migrate', 'rollback', 'status'], 
                       default='migrate', help='Action to perform')
    parser.add_argument('--target-version', help='Target version for migration')
    parser.add_argument('--target-migration', help='Target migration for rollback')
    parser.add_argument('--backup-file', help='Specific backup file to use')
    parser.add_argument('--no-backup', action='store_true', help='Disable automatic backup')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    
    args = parser.parse_args()
    
    runner = MigrationRunner(args.environment)
    
    if args.action == 'migrate':
        if args.dry_run:
            status = runner.status()
            print(f"Would apply {status['pending_migrations']} migrations:")
            for migration_id in status['pending_list']:
                print(f"  - {migration_id}")
        else:
            results = runner.migrate(args.target_version, not args.no_backup)
            for result in results:
                status = "SUCCESS" if result.success else "FAILED"
                print(f"{result.migration_id}: {status}")
                if result.error_message:
                    print(f"  Error: {result.error_message}")
    
    elif args.action == 'rollback':
        if args.dry_run:
            print(f"Would rollback to: {args.target_migration or 'previous migration'}")
        else:
            results = runner.rollback(args.target_migration)
            for result in results:
                status = "SUCCESS" if result.success else "FAILED"
                print(f"Rollback {result.migration_id}: {status}")
    
    elif args.action == 'status':
        status = runner.status()
        print(json.dumps(status, indent=2))

if __name__ == '__main__':
    main()