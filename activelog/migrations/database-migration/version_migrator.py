#!/usr/bin/env python3
"""
Database Version Migration System for ActiveLog
Manages database schema versions, migrations, and rollbacks
"""

import asyncio
import json
import logging
import os
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import aiofiles
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MigrationScript:
    """Represents a single migration script"""
    version: str
    name: str
    description: str
    up_script: str
    down_script: str
    checksum: str
    dependencies: List[str] = None
    estimated_duration: int = 0  # seconds
    requires_downtime: bool = False

@dataclass
class MigrationExecution:
    """Represents an executed migration"""
    version: str
    name: str
    executed_at: datetime
    execution_time: float
    checksum: str
    success: bool
    error_message: Optional[str] = None

class DatabaseVersionManager:
    """Manages database version tracking and migration execution"""
    
    def __init__(self, database_url: str, migrations_dir: str = "migrations/sql"):
        self.database_url = database_url
        self.migrations_dir = Path(migrations_dir)
        self.engine = None
        self.migration_table = "activelog_migrations"
        
    async def initialize(self):
        """Initialize the version manager and create migration tracking table"""
        self.engine = create_async_engine(self.database_url)
        await self._create_migration_table()
    
    async def _create_migration_table(self):
        """Create the migration tracking table if it doesn't exist"""
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.migration_table} (
            version VARCHAR(50) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            executed_at TIMESTAMP WITH TIME ZONE NOT NULL,
            execution_time REAL NOT NULL,
            checksum VARCHAR(64) NOT NULL,
            success BOOLEAN NOT NULL,
            error_message TEXT
        )
        """
        
        async with self.engine.begin() as conn:
            await conn.execute(text(create_table_sql))
    
    async def get_current_version(self) -> Optional[str]:
        """Get the current database version"""
        query = f"""
        SELECT version FROM {self.migration_table} 
        WHERE success = true 
        ORDER BY executed_at DESC 
        LIMIT 1
        """
        
        async with self.engine.begin() as conn:
            result = await conn.execute(text(query))
            row = result.fetchone()
            return row[0] if row else None
    
    async def get_migration_history(self) -> List[MigrationExecution]:
        """Get complete migration history"""
        query = f"""
        SELECT version, name, executed_at, execution_time, checksum, success, error_message
        FROM {self.migration_table}
        ORDER BY executed_at ASC
        """
        
        migrations = []
        async with self.engine.begin() as conn:
            result = await conn.execute(text(query))
            for row in result:
                migration = MigrationExecution(
                    version=row[0],
                    name=row[1],
                    executed_at=row[2],
                    execution_time=row[3],
                    checksum=row[4],
                    success=row[5],
                    error_message=row[6]
                )
                migrations.append(migration)
        
        return migrations
    
    async def is_migration_applied(self, version: str) -> bool:
        """Check if a migration has been successfully applied"""
        query = f"""
        SELECT COUNT(*) FROM {self.migration_table} 
        WHERE version = :version AND success = true
        """
        
        async with self.engine.begin() as conn:
            result = await conn.execute(text(query), {"version": version})
            count = result.scalar()
            return count > 0
    
    async def record_migration(self, migration: MigrationScript, execution_time: float, 
                             success: bool, error_message: Optional[str] = None):
        """Record migration execution in the tracking table"""
        insert_sql = f"""
        INSERT INTO {self.migration_table} 
        (version, name, description, executed_at, execution_time, checksum, success, error_message)
        VALUES (:version, :name, :description, :executed_at, :execution_time, :checksum, :success, :error_message)
        """
        
        async with self.engine.begin() as conn:
            await conn.execute(text(insert_sql), {
                "version": migration.version,
                "name": migration.name,
                "description": migration.description,
                "executed_at": datetime.now(timezone.utc),
                "execution_time": execution_time,
                "checksum": migration.checksum,
                "success": success,
                "error_message": error_message
            })
    
    async def close(self):
        """Close database connection"""
        if self.engine:
            await self.engine.dispose()

class MigrationLoader:
    """Loads migration scripts from filesystem"""
    
    def __init__(self, migrations_dir: str):
        self.migrations_dir = Path(migrations_dir)
    
    def load_migrations(self) -> List[MigrationScript]:
        """Load all migration scripts from directory"""
        migrations = []
        
        if not self.migrations_dir.exists():
            logger.warning(f"Migrations directory not found: {self.migrations_dir}")
            return migrations
        
        # Look for migration files (format: V{version}__{name}.sql)
        for migration_file in sorted(self.migrations_dir.glob("V*__*.sql")):
            try:
                migration = self._parse_migration_file(migration_file)
                migrations.append(migration)
            except Exception as e:
                logger.error(f"Failed to parse migration file {migration_file}: {e}")
        
        return migrations
    
    def _parse_migration_file(self, file_path: Path) -> MigrationScript:
        """Parse a single migration file"""
        # Extract version and name from filename
        # Expected format: V1.0.0__create_users_table.sql
        filename = file_path.stem
        if not filename.startswith('V'):
            raise ValueError(f"Migration file must start with 'V': {filename}")
        
        parts = filename[1:].split('__', 1)
        if len(parts) != 2:
            raise ValueError(f"Migration file must follow format V{version}__{name}: {filename}")
        
        version, name = parts
        
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse migration content
        up_script, down_script, description, metadata = self._parse_migration_content(content)
        
        # Calculate checksum
        checksum = hashlib.sha256(content.encode('utf-8')).hexdigest()
        
        return MigrationScript(
            version=version,
            name=name,
            description=description,
            up_script=up_script,
            down_script=down_script,
            checksum=checksum,
            dependencies=metadata.get('dependencies', []),
            estimated_duration=metadata.get('estimated_duration', 0),
            requires_downtime=metadata.get('requires_downtime', False)
        )
    
    def _parse_migration_content(self, content: str) -> tuple:
        """Parse migration file content into up/down scripts and metadata"""
        lines = content.split('\n')
        
        description = ""
        up_script = ""
        down_script = ""
        metadata = {}
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            # Parse metadata comments
            if line.startswith('-- @description:'):
                description = line[16:].strip()
            elif line.startswith('-- @dependencies:'):
                metadata['dependencies'] = [dep.strip() for dep in line[17:].split(',') if dep.strip()]
            elif line.startswith('-- @estimated_duration:'):
                metadata['estimated_duration'] = int(line[23:].strip())
            elif line.startswith('-- @requires_downtime:'):
                metadata['requires_downtime'] = line[22:].strip().lower() == 'true'
            
            # Section markers
            elif line == '-- +migrate Up':
                current_section = 'up'
                continue
            elif line == '-- +migrate Down':
                current_section = 'down'
                continue
            
            # Add content to appropriate section
            elif current_section == 'up' and line and not line.startswith('--'):
                up_script += line + '\n'
            elif current_section == 'down' and line and not line.startswith('--'):
                down_script += line + '\n'
        
        return up_script.strip(), down_script.strip(), description, metadata

class MigrationExecutor:
    """Executes database migrations with transaction support"""
    
    def __init__(self, version_manager: DatabaseVersionManager):
        self.version_manager = version_manager
    
    async def migrate_to_version(self, target_version: str, migrations: List[MigrationScript]) -> Dict[str, Any]:
        """Migrate database to specific version"""
        current_version = await self.version_manager.get_current_version()
        
        # Find migrations to execute
        pending_migrations = self._get_pending_migrations(current_version, target_version, migrations)
        
        if not pending_migrations:
            return {
                'status': 'up_to_date',
                'current_version': current_version,
                'target_version': target_version,
                'migrations_executed': 0
            }
        
        # Execute migrations
        results = []
        total_time = 0
        
        for migration in pending_migrations:
            logger.info(f"Executing migration {migration.version}: {migration.name}")
            
            start_time = datetime.now()
            success = False
            error_message = None
            
            try:
                await self._execute_migration_up(migration)
                success = True
                logger.info(f"Migration {migration.version} completed successfully")
            except Exception as e:
                error_message = str(e)
                logger.error(f"Migration {migration.version} failed: {error_message}")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            total_time += execution_time
            
            # Record migration result
            await self.version_manager.record_migration(
                migration, execution_time, success, error_message
            )
            
            results.append({
                'version': migration.version,
                'name': migration.name,
                'success': success,
                'execution_time': execution_time,
                'error': error_message
            })
            
            if not success:
                break
        
        final_version = await self.version_manager.get_current_version()
        
        return {
            'status': 'completed' if all(r['success'] for r in results) else 'failed',
            'initial_version': current_version,
            'final_version': final_version,
            'target_version': target_version,
            'migrations_executed': len([r for r in results if r['success']]),
            'total_execution_time': total_time,
            'migration_results': results
        }
    
    async def rollback_to_version(self, target_version: str, migrations: List[MigrationScript]) -> Dict[str, Any]:
        """Rollback database to specific version"""
        current_version = await self.version_manager.get_current_version()
        
        if not current_version:
            return {
                'status': 'error',
                'message': 'No migrations found to rollback'
            }
        
        # Find migrations to rollback
        rollback_migrations = self._get_rollback_migrations(current_version, target_version, migrations)
        
        if not rollback_migrations:
            return {
                'status': 'up_to_date',
                'current_version': current_version,
                'target_version': target_version,
                'migrations_rolled_back': 0
            }
        
        # Execute rollbacks in reverse order
        results = []
        total_time = 0
        
        for migration in reversed(rollback_migrations):
            logger.info(f"Rolling back migration {migration.version}: {migration.name}")
            
            start_time = datetime.now()
            success = False
            error_message = None
            
            try:
                await self._execute_migration_down(migration)
                success = True
                logger.info(f"Rollback of {migration.version} completed successfully")
            except Exception as e:
                error_message = str(e)
                logger.error(f"Rollback of {migration.version} failed: {error_message}")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            total_time += execution_time
            
            # Remove migration record if rollback successful
            if success:
                await self._remove_migration_record(migration.version)
            
            results.append({
                'version': migration.version,
                'name': migration.name,
                'success': success,
                'execution_time': execution_time,
                'error': error_message
            })
            
            if not success:
                break
        
        final_version = await self.version_manager.get_current_version()
        
        return {
            'status': 'completed' if all(r['success'] for r in results) else 'failed',
            'initial_version': current_version,
            'final_version': final_version,
            'target_version': target_version,
            'migrations_rolled_back': len([r for r in results if r['success']]),
            'total_execution_time': total_time,
            'rollback_results': results
        }
    
    async def _execute_migration_up(self, migration: MigrationScript):
        """Execute migration up script"""
        if not migration.up_script:
            raise ValueError(f"No up script found for migration {migration.version}")
        
        async with self.version_manager.engine.begin() as conn:
            # Split and execute statements
            statements = self._split_sql_statements(migration.up_script)
            for statement in statements:
                if statement.strip():
                    await conn.execute(text(statement))
    
    async def _execute_migration_down(self, migration: MigrationScript):
        """Execute migration down script"""
        if not migration.down_script:
            raise ValueError(f"No down script found for migration {migration.version}")
        
        async with self.version_manager.engine.begin() as conn:
            # Split and execute statements
            statements = self._split_sql_statements(migration.down_script)
            for statement in statements:
                if statement.strip():
                    await conn.execute(text(statement))
    
    def _split_sql_statements(self, sql: str) -> List[str]:
        """Split SQL script into individual statements"""
        # Simple statement splitting - could be enhanced for complex cases
        statements = []
        current_statement = ""
        
        for line in sql.split('\n'):
            line = line.strip()
            if line and not line.startswith('--'):
                current_statement += line + '\n'
                if line.endswith(';'):
                    statements.append(current_statement.strip())
                    current_statement = ""
        
        if current_statement.strip():
            statements.append(current_statement.strip())
        
        return statements
    
    def _get_pending_migrations(self, current_version: Optional[str], target_version: str,
                               migrations: List[MigrationScript]) -> List[MigrationScript]:
        """Get migrations that need to be executed to reach target version"""
        # Sort migrations by version
        sorted_migrations = sorted(migrations, key=lambda m: self._version_key(m.version))
        
        pending = []
        for migration in sorted_migrations:
            # Check if migration should be executed
            if (current_version is None or self._version_key(migration.version) > self._version_key(current_version)):
                if self._version_key(migration.version) <= self._version_key(target_version):
                    pending.append(migration)
        
        return pending
    
    def _get_rollback_migrations(self, current_version: str, target_version: Optional[str],
                                migrations: List[MigrationScript]) -> List[MigrationScript]:
        """Get migrations that need to be rolled back to reach target version"""
        # Sort migrations by version
        sorted_migrations = sorted(migrations, key=lambda m: self._version_key(m.version))
        
        rollback = []
        for migration in sorted_migrations:
            # Check if migration should be rolled back
            if self._version_key(migration.version) <= self._version_key(current_version):
                if target_version is None or self._version_key(migration.version) > self._version_key(target_version):
                    rollback.append(migration)
        
        return rollback
    
    def _version_key(self, version: str) -> tuple:
        """Convert version string to sortable tuple"""
        try:
            # Handle semantic versioning (e.g., "1.2.3")
            parts = version.split('.')
            return tuple(int(part) for part in parts)
        except ValueError:
            # Fallback to string comparison for non-numeric versions
            return (version,)
    
    async def _remove_migration_record(self, version: str):
        """Remove migration record from tracking table"""
        delete_sql = f"DELETE FROM {self.version_manager.migration_table} WHERE version = :version"
        
        async with self.version_manager.engine.begin() as conn:
            await conn.execute(text(delete_sql), {"version": version})

class MigrationValidator:
    """Validates migration scripts and dependency chains"""
    
    def validate_migrations(self, migrations: List[MigrationScript]) -> Dict[str, Any]:
        """Validate all migrations for consistency and dependencies"""
        issues = []
        warnings = []
        
        # Check for duplicate versions
        versions = [m.version for m in migrations]
        duplicates = set([v for v in versions if versions.count(v) > 1])
        if duplicates:
            issues.append(f"Duplicate migration versions found: {duplicates}")
        
        # Validate dependencies
        version_map = {m.version: m for m in migrations}
        for migration in migrations:
            if migration.dependencies:
                for dep in migration.dependencies:
                    if dep not in version_map:
                        issues.append(f"Migration {migration.version} depends on missing migration {dep}")
        
        # Check for missing down scripts
        missing_down = [m.version for m in migrations if not m.down_script]
        if missing_down:
            warnings.append(f"Migrations without down scripts: {missing_down}")
        
        # Validate SQL syntax (basic check)
        for migration in migrations:
            if migration.up_script:
                syntax_issues = self._validate_sql_syntax(migration.up_script, f"{migration.version} (up)")
                issues.extend(syntax_issues)
            
            if migration.down_script:
                syntax_issues = self._validate_sql_syntax(migration.down_script, f"{migration.version} (down)")
                issues.extend(syntax_issues)
        
        return {
            'valid': len(issues) == 0,
            'total_migrations': len(migrations),
            'issues': issues,
            'warnings': warnings
        }
    
    def _validate_sql_syntax(self, sql: str, context: str) -> List[str]:
        """Basic SQL syntax validation"""
        issues = []
        
        # Check for common SQL issues
        if 'DROP TABLE' in sql.upper() and 'IF EXISTS' not in sql.upper():
            issues.append(f"Potentially unsafe DROP TABLE without IF EXISTS in {context}")
        
        if 'ALTER TABLE' in sql.upper() and 'ADD COLUMN' in sql.upper():
            if 'IF NOT EXISTS' not in sql.upper():
                issues.append(f"ADD COLUMN without IF NOT EXISTS may fail on re-run in {context}")
        
        # Check for transaction control in migration scripts
        if any(keyword in sql.upper() for keyword in ['BEGIN', 'COMMIT', 'ROLLBACK']):
            issues.append(f"Manual transaction control found in {context} - migrations run in transactions automatically")
        
        return issues

# CLI Interface
async def main():
    """Command-line interface for database migrations"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ActiveLog Database Migration Tool')
    parser.add_argument('action', choices=['status', 'migrate', 'rollback', 'validate', 'create'])
    parser.add_argument('--database-url', required=True, help='Database connection URL')
    parser.add_argument('--migrations-dir', default='migrations/sql', help='Migrations directory')
    parser.add_argument('--target-version', help='Target version for migrate/rollback')
    parser.add_argument('--migration-name', help='Name for new migration (create action)')
    parser.add_argument('--description', help='Description for new migration')
    
    args = parser.parse_args()
    
    version_manager = DatabaseVersionManager(args.database_url, args.migrations_dir)
    await version_manager.initialize()
    
    try:
        if args.action == 'status':
            current_version = await version_manager.get_current_version()
            history = await version_manager.get_migration_history()
            
            print(f"Current Version: {current_version or 'None'}")
            print(f"Total Migrations Applied: {len([h for h in history if h.success])}")
            
            if history:
                print("\nMigration History:")
                for migration in history[-10:]:  # Last 10 migrations
                    status = "✓" if migration.success else "✗"
                    print(f"  {status} {migration.version} - {migration.name} ({migration.executed_at})")
        
        elif args.action == 'validate':
            loader = MigrationLoader(args.migrations_dir)
            migrations = loader.load_migrations()
            
            validator = MigrationValidator()
            result = validator.validate_migrations(migrations)
            
            print(f"Validation Result: {'PASS' if result['valid'] else 'FAIL'}")
            print(f"Total Migrations: {result['total_migrations']}")
            
            if result['issues']:
                print("\nIssues:")
                for issue in result['issues']:
                    print(f"  ✗ {issue}")
            
            if result['warnings']:
                print("\nWarnings:")
                for warning in result['warnings']:
                    print(f"  ⚠ {warning}")
        
        elif args.action == 'migrate':
            if not args.target_version:
                print("Error: --target-version required for migrate action")
                return
            
            loader = MigrationLoader(args.migrations_dir)
            migrations = loader.load_migrations()
            
            executor = MigrationExecutor(version_manager)
            result = await executor.migrate_to_version(args.target_version, migrations)
            
            print(f"Migration Status: {result['status']}")
            print(f"Version: {result['initial_version']} -> {result['final_version']}")
            print(f"Migrations Executed: {result['migrations_executed']}")
            print(f"Total Time: {result['total_execution_time']:.2f}s")
            
            if result.get('migration_results'):
                print("\nMigration Details:")
                for migration_result in result['migration_results']:
                    status = "✓" if migration_result['success'] else "✗"
                    print(f"  {status} {migration_result['version']} - {migration_result['name']}")
                    if migration_result.get('error'):
                        print(f"    Error: {migration_result['error']}")
        
        elif args.action == 'rollback':
            loader = MigrationLoader(args.migrations_dir)
            migrations = loader.load_migrations()
            
            executor = MigrationExecutor(version_manager)
            result = await executor.rollback_to_version(args.target_version, migrations)
            
            print(f"Rollback Status: {result['status']}")
            print(f"Version: {result['initial_version']} -> {result['final_version']}")
            print(f"Migrations Rolled Back: {result['migrations_rolled_back']}")
            print(f"Total Time: {result['total_execution_time']:.2f}s")
        
        elif args.action == 'create':
            if not args.migration_name:
                print("Error: --migration-name required for create action")
                return
            
            # Generate new migration file
            version = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"V{version}__{args.migration_name}.sql"
            filepath = Path(args.migrations_dir) / filename
            
            # Create migrations directory if it doesn't exist
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # Template migration content
            template = f"""-- @description: {args.description or 'TODO: Add migration description'}
-- @dependencies: 
-- @estimated_duration: 0
-- @requires_downtime: false

-- +migrate Up
-- TODO: Add your migration SQL here
-- Example:
-- CREATE TABLE example_table (
--     id SERIAL PRIMARY KEY,
--     name VARCHAR(255) NOT NULL,
--     created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
-- );

-- +migrate Down
-- TODO: Add your rollback SQL here
-- Example:
-- DROP TABLE IF EXISTS example_table;
"""
            
            with open(filepath, 'w') as f:
                f.write(template)
            
            print(f"Created migration file: {filepath}")
            print("Please edit the file to add your migration SQL.")
    
    finally:
        await version_manager.close()

if __name__ == "__main__":
    asyncio.run(main())