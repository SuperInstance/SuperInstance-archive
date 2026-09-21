#!/usr/bin/env python3
"""
Schema Migration Tool for ActiveLog
Handles database schema transformations, field mappings, and data type conversions
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Callable, Union
import aiofiles
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateTable, DropTable
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class FieldMapping:
    """Mapping configuration for field transformations"""
    source_field: str
    target_field: str
    data_type: str
    transform_function: Optional[str] = None
    default_value: Any = None
    nullable: bool = True
    validation_pattern: Optional[str] = None

@dataclass
class TableMapping:
    """Mapping configuration for table transformations"""
    source_table: str
    target_table: str
    field_mappings: List[FieldMapping]
    filter_condition: Optional[str] = None
    custom_query: Optional[str] = None

@dataclass
class MigrationPlan:
    """Complete migration plan with all transformations"""
    migration_id: str
    source_database: str
    target_database: str
    table_mappings: List[TableMapping]
    pre_migration_scripts: List[str] = None
    post_migration_scripts: List[str] = None
    batch_size: int = 1000
    parallel_tables: bool = False

class DataTypeConverter:
    """Handles data type conversions between different database systems"""
    
    # Mapping from common types to database-specific types
    TYPE_MAPPINGS = {
        'postgresql': {
            'string': 'VARCHAR',
            'text': 'TEXT',
            'integer': 'INTEGER',
            'bigint': 'BIGINT',
            'float': 'REAL',
            'double': 'DOUBLE PRECISION',
            'decimal': 'NUMERIC',
            'boolean': 'BOOLEAN',
            'date': 'DATE',
            'datetime': 'TIMESTAMP',
            'json': 'JSONB',
            'uuid': 'UUID'
        },
        'mysql': {
            'string': 'VARCHAR(255)',
            'text': 'TEXT',
            'integer': 'INT',
            'bigint': 'BIGINT',
            'float': 'FLOAT',
            'double': 'DOUBLE',
            'decimal': 'DECIMAL',
            'boolean': 'BOOLEAN',
            'date': 'DATE',
            'datetime': 'DATETIME',
            'json': 'JSON',
            'uuid': 'CHAR(36)'
        },
        'sqlite': {
            'string': 'TEXT',
            'text': 'TEXT',
            'integer': 'INTEGER',
            'bigint': 'INTEGER',
            'float': 'REAL',
            'double': 'REAL',
            'decimal': 'REAL',
            'boolean': 'INTEGER',
            'date': 'TEXT',
            'datetime': 'TEXT',
            'json': 'TEXT',
            'uuid': 'TEXT'
        }
    }
    
    @classmethod
    def convert_type(cls, data_type: str, target_db: str) -> str:
        """Convert generic data type to database-specific type"""
        if target_db not in cls.TYPE_MAPPINGS:
            return data_type
        
        return cls.TYPE_MAPPINGS[target_db].get(data_type.lower(), data_type)
    
    @classmethod
    def convert_value(cls, value: Any, target_type: str, source_db: str = None) -> Any:
        """Convert value to target data type"""
        if value is None:
            return None
        
        try:
            if target_type.lower() in ['integer', 'int', 'bigint']:
                return int(value)
            elif target_type.lower() in ['float', 'real', 'double']:
                return float(value)
            elif target_type.lower() in ['boolean', 'bool']:
                if isinstance(value, str):
                    return value.lower() in ('true', '1', 'yes', 'on')
                return bool(value)
            elif target_type.lower() in ['date', 'datetime', 'timestamp']:
                if isinstance(value, str):
                    return datetime.fromisoformat(value.replace('Z', '+00:00'))
                return value
            elif target_type.lower() == 'json':
                if isinstance(value, str):
                    return json.loads(value)
                return value
            else:
                return str(value)
        except (ValueError, TypeError) as e:
            logger.warning(f"Type conversion failed for value '{value}' to type '{target_type}': {e}")
            return value

class SchemaMigrator:
    """Main schema migration engine"""
    
    def __init__(self, migration_plan: MigrationPlan):
        self.plan = migration_plan
        self.source_engine = None
        self.target_engine = None
        self.migration_log = []
        self.errors = []
    
    async def execute_migration(self) -> Dict[str, Any]:
        """Execute the complete migration plan"""
        start_time = datetime.now()
        
        try:
            # Initialize database connections
            self.source_engine = create_async_engine(self.plan.source_database)
            self.target_engine = create_async_engine(self.plan.target_database)
            
            # Execute pre-migration scripts
            await self._execute_scripts(self.plan.pre_migration_scripts, "pre-migration")
            
            # Create target tables
            await self._create_target_tables()
            
            # Migrate data
            migration_results = await self._migrate_data()
            
            # Execute post-migration scripts
            await self._execute_scripts(self.plan.post_migration_scripts, "post-migration")
            
            # Generate migration report
            return {
                'migration_id': self.plan.migration_id,
                'status': 'completed',
                'start_time': start_time.isoformat(),
                'end_time': datetime.now().isoformat(),
                'duration': (datetime.now() - start_time).total_seconds(),
                'results': migration_results,
                'errors': self.errors,
                'migration_log': self.migration_log
            }
            
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            self.errors.append(f"Migration failed: {str(e)}")
            return {
                'migration_id': self.plan.migration_id,
                'status': 'failed',
                'start_time': start_time.isoformat(),
                'end_time': datetime.now().isoformat(),
                'error': str(e),
                'errors': self.errors,
                'migration_log': self.migration_log
            }
        finally:
            if self.source_engine:
                await self.source_engine.dispose()
            if self.target_engine:
                await self.target_engine.dispose()
    
    async def _execute_scripts(self, scripts: List[str], phase: str):
        """Execute SQL scripts"""
        if not scripts:
            return
        
        self.migration_log.append(f"Executing {phase} scripts")
        
        async with self.target_engine.begin() as conn:
            for script in scripts:
                try:
                    await conn.execute(sa.text(script))
                    self.migration_log.append(f"Executed {phase} script: {script[:100]}...")
                except Exception as e:
                    error_msg = f"Script execution failed in {phase}: {str(e)}"
                    self.errors.append(error_msg)
                    logger.error(error_msg)
    
    async def _create_target_tables(self):
        """Create target tables based on mappings"""
        self.migration_log.append("Creating target tables")
        
        async with self.target_engine.begin() as conn:
            for table_mapping in self.plan.table_mappings:
                try:
                    # Generate CREATE TABLE statement
                    create_sql = self._generate_create_table_sql(table_mapping)
                    await conn.execute(sa.text(create_sql))
                    self.migration_log.append(f"Created table: {table_mapping.target_table}")
                except Exception as e:
                    error_msg = f"Failed to create table {table_mapping.target_table}: {str(e)}"
                    self.errors.append(error_msg)
                    logger.error(error_msg)
    
    def _generate_create_table_sql(self, table_mapping: TableMapping) -> str:
        """Generate CREATE TABLE SQL from field mappings"""
        target_db = self._get_database_type(self.plan.target_database)
        
        columns = []
        for field in table_mapping.field_mappings:
            column_def = f"{field.target_field} {DataTypeConverter.convert_type(field.data_type, target_db)}"
            
            if not field.nullable:
                column_def += " NOT NULL"
            
            if field.default_value is not None:
                if isinstance(field.default_value, str):
                    column_def += f" DEFAULT '{field.default_value}'"
                else:
                    column_def += f" DEFAULT {field.default_value}"
            
            columns.append(column_def)
        
        # Add primary key if none specified
        if not any('PRIMARY KEY' in col for col in columns):
            if target_db == 'postgresql':
                columns.insert(0, "id SERIAL PRIMARY KEY")
            elif target_db == 'mysql':
                columns.insert(0, "id INT AUTO_INCREMENT PRIMARY KEY")
            else:
                columns.insert(0, "id INTEGER PRIMARY KEY AUTOINCREMENT")
        
        return f"CREATE TABLE IF NOT EXISTS {table_mapping.target_table} (\n  {',\n  '.join(columns)}\n)"
    
    async def _migrate_data(self) -> Dict[str, Any]:
        """Migrate data according to table mappings"""
        results = {}
        
        if self.plan.parallel_tables:
            # Migrate tables in parallel
            tasks = []
            for table_mapping in self.plan.table_mappings:
                task = asyncio.create_task(self._migrate_table(table_mapping))
                tasks.append((table_mapping.source_table, task))
            
            for source_table, task in tasks:
                try:
                    result = await task
                    results[source_table] = result
                except Exception as e:
                    results[source_table] = {'status': 'failed', 'error': str(e)}
        else:
            # Migrate tables sequentially
            for table_mapping in self.plan.table_mappings:
                try:
                    result = await self._migrate_table(table_mapping)
                    results[table_mapping.source_table] = result
                except Exception as e:
                    results[table_mapping.source_table] = {'status': 'failed', 'error': str(e)}
        
        return results
    
    async def _migrate_table(self, table_mapping: TableMapping) -> Dict[str, Any]:
        """Migrate data for a single table"""
        self.migration_log.append(f"Starting migration: {table_mapping.source_table} -> {table_mapping.target_table}")
        
        total_rows = 0
        migrated_rows = 0
        failed_rows = 0
        
        try:
            async with self.source_engine.begin() as source_conn:
                async with self.target_engine.begin() as target_conn:
                    # Build source query
                    if table_mapping.custom_query:
                        source_query = table_mapping.custom_query
                    else:
                        source_fields = [fm.source_field for fm in table_mapping.field_mappings]
                        source_query = f"SELECT {', '.join(source_fields)} FROM {table_mapping.source_table}"
                        
                        if table_mapping.filter_condition:
                            source_query += f" WHERE {table_mapping.filter_condition}"
                    
                    # Execute source query in batches
                    offset = 0
                    while True:
                        batch_query = f"{source_query} LIMIT {self.plan.batch_size} OFFSET {offset}"
                        result = await source_conn.execute(sa.text(batch_query))
                        rows = result.fetchall()
                        
                        if not rows:
                            break
                        
                        columns = result.keys()
                        
                        # Transform and insert batch
                        batch_data = []
                        for row in rows:
                            total_rows += 1
                            try:
                                row_dict = dict(zip(columns, row))
                                transformed_row = self._transform_row(row_dict, table_mapping)
                                batch_data.append(transformed_row)
                            except Exception as e:
                                failed_rows += 1
                                self.errors.append(f"Row transformation failed in {table_mapping.source_table}: {str(e)}")
                        
                        # Insert batch
                        if batch_data:
                            try:
                                inserted = await self._insert_batch(target_conn, table_mapping.target_table, batch_data)
                                migrated_rows += inserted
                            except Exception as e:
                                failed_rows += len(batch_data)
                                self.errors.append(f"Batch insert failed for {table_mapping.target_table}: {str(e)}")
                        
                        offset += self.plan.batch_size
                        
                        if len(rows) < self.plan.batch_size:
                            break
            
            self.migration_log.append(f"Completed migration: {table_mapping.source_table} ({migrated_rows}/{total_rows} rows)")
            
            return {
                'status': 'completed',
                'total_rows': total_rows,
                'migrated_rows': migrated_rows,
                'failed_rows': failed_rows,
                'success_rate': (migrated_rows / total_rows * 100) if total_rows > 0 else 0
            }
            
        except Exception as e:
            error_msg = f"Table migration failed for {table_mapping.source_table}: {str(e)}"
            self.errors.append(error_msg)
            logger.error(error_msg)
            
            return {
                'status': 'failed',
                'error': str(e),
                'total_rows': total_rows,
                'migrated_rows': migrated_rows,
                'failed_rows': failed_rows
            }
    
    def _transform_row(self, row: Dict[str, Any], table_mapping: TableMapping) -> Dict[str, Any]:
        """Transform a single row according to field mappings"""
        transformed = {}
        
        for field_mapping in table_mapping.field_mappings:
            source_value = row.get(field_mapping.source_field)
            
            # Apply default value if source is None
            if source_value is None and field_mapping.default_value is not None:
                source_value = field_mapping.default_value
            
            # Apply custom transformation function
            if field_mapping.transform_function:
                source_value = self._apply_transform_function(source_value, field_mapping.transform_function, row)
            
            # Convert data type
            if source_value is not None:
                source_value = DataTypeConverter.convert_value(
                    source_value, 
                    field_mapping.data_type,
                    self._get_database_type(self.plan.source_database)
                )
            
            # Validate pattern if specified
            if (source_value is not None and 
                field_mapping.validation_pattern and 
                isinstance(source_value, str)):
                import re
                if not re.match(field_mapping.validation_pattern, source_value):
                    raise ValueError(f"Value '{source_value}' does not match pattern '{field_mapping.validation_pattern}'")
            
            transformed[field_mapping.target_field] = source_value
        
        return transformed
    
    def _apply_transform_function(self, value: Any, function_name: str, row: Dict[str, Any]) -> Any:
        """Apply named transformation function"""
        transform_functions = {
            'uppercase': lambda x: x.upper() if isinstance(x, str) else x,
            'lowercase': lambda x: x.lower() if isinstance(x, str) else x,
            'trim': lambda x: x.strip() if isinstance(x, str) else x,
            'concat_names': lambda x: f"{row.get('first_name', '')} {row.get('last_name', '')}".strip(),
            'extract_domain': lambda x: x.split('@')[1] if isinstance(x, str) and '@' in x else x,
            'current_timestamp': lambda x: datetime.now(timezone.utc),
            'boolean_from_string': lambda x: str(x).lower() in ('true', '1', 'yes', 'on') if x is not None else False,
            'json_stringify': lambda x: json.dumps(x) if x is not None else None,
            'slugify': lambda x: re.sub(r'[^\w\s-]', '', str(x)).strip().lower().replace(' ', '-') if x else x
        }
        
        if function_name in transform_functions:
            try:
                return transform_functions[function_name](value)
            except Exception as e:
                logger.warning(f"Transform function '{function_name}' failed: {e}")
                return value
        else:
            logger.warning(f"Unknown transform function: {function_name}")
            return value
    
    async def _insert_batch(self, conn, table_name: str, batch_data: List[Dict[str, Any]]) -> int:
        """Insert batch of transformed data"""
        if not batch_data:
            return 0
        
        try:
            # Build parameterized insert query
            columns = list(batch_data[0].keys())
            placeholders = ', '.join([f':{col}' for col in columns])
            query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
            
            await conn.execute(sa.text(query), batch_data)
            return len(batch_data)
        except Exception as e:
            logger.error(f"Batch insert failed for {table_name}: {str(e)}")
            # Try individual inserts to identify problematic rows
            successful = 0
            for row_data in batch_data:
                try:
                    await conn.execute(sa.text(query), [row_data])
                    successful += 1
                except Exception as row_error:
                    logger.error(f"Individual row insert failed: {row_error}")
            return successful
    
    def _get_database_type(self, database_url: str) -> str:
        """Extract database type from connection URL"""
        if database_url.startswith('postgresql'):
            return 'postgresql'
        elif database_url.startswith('mysql'):
            return 'mysql'
        elif database_url.startswith('sqlite'):
            return 'sqlite'
        else:
            return 'unknown'

class MigrationPlanBuilder:
    """Helper class to build migration plans from configuration"""
    
    @staticmethod
    def from_json_file(file_path: str) -> MigrationPlan:
        """Load migration plan from JSON file"""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        return MigrationPlanBuilder.from_dict(data)
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> MigrationPlan:
        """Build migration plan from dictionary"""
        table_mappings = []
        
        for table_data in data.get('table_mappings', []):
            field_mappings = []
            for field_data in table_data.get('field_mappings', []):
                field_mapping = FieldMapping(
                    source_field=field_data['source_field'],
                    target_field=field_data['target_field'],
                    data_type=field_data['data_type'],
                    transform_function=field_data.get('transform_function'),
                    default_value=field_data.get('default_value'),
                    nullable=field_data.get('nullable', True),
                    validation_pattern=field_data.get('validation_pattern')
                )
                field_mappings.append(field_mapping)
            
            table_mapping = TableMapping(
                source_table=table_data['source_table'],
                target_table=table_data['target_table'],
                field_mappings=field_mappings,
                filter_condition=table_data.get('filter_condition'),
                custom_query=table_data.get('custom_query')
            )
            table_mappings.append(table_mapping)
        
        return MigrationPlan(
            migration_id=data['migration_id'],
            source_database=data['source_database'],
            target_database=data['target_database'],
            table_mappings=table_mappings,
            pre_migration_scripts=data.get('pre_migration_scripts'),
            post_migration_scripts=data.get('post_migration_scripts'),
            batch_size=data.get('batch_size', 1000),
            parallel_tables=data.get('parallel_tables', False)
        )
    
    @staticmethod
    def create_sample_plan() -> str:
        """Create a sample migration plan JSON"""
        sample_plan = {
            "migration_id": "user_profile_migration_20250822",
            "source_database": "postgresql://user:pass@localhost/old_db",
            "target_database": "postgresql://user:pass@localhost/new_db",
            "batch_size": 1000,
            "parallel_tables": False,
            "pre_migration_scripts": [
                "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"",
                "CREATE SCHEMA IF NOT EXISTS activelog"
            ],
            "post_migration_scripts": [
                "CREATE INDEX idx_users_email ON activelog.users(email)",
                "CREATE INDEX idx_users_created_at ON activelog.users(created_at)"
            ],
            "table_mappings": [
                {
                    "source_table": "user_profiles",
                    "target_table": "activelog.users",
                    "field_mappings": [
                        {
                            "source_field": "id",
                            "target_field": "user_id",
                            "data_type": "uuid",
                            "nullable": False
                        },
                        {
                            "source_field": "email_address",
                            "target_field": "email",
                            "data_type": "string",
                            "transform_function": "lowercase",
                            "nullable": False,
                            "validation_pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
                        },
                        {
                            "source_field": "first_name",
                            "target_field": "full_name",
                            "data_type": "string",
                            "transform_function": "concat_names"
                        },
                        {
                            "source_field": "registration_date",
                            "target_field": "created_at",
                            "data_type": "datetime"
                        },
                        {
                            "source_field": "is_verified",
                            "target_field": "email_verified",
                            "data_type": "boolean",
                            "default_value": False
                        }
                    ],
                    "filter_condition": "is_active = true AND deleted_at IS NULL"
                }
            ]
        }
        
        return json.dumps(sample_plan, indent=2)

# CLI Interface
async def main():
    """Command-line interface for schema migration"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ActiveLog Schema Migration Tool')
    parser.add_argument('action', choices=['migrate', 'plan', 'validate'])
    parser.add_argument('--plan-file', help='Migration plan JSON file')
    parser.add_argument('--output', help='Output file for generated plans')
    
    args = parser.parse_args()
    
    if args.action == 'plan':
        # Generate sample migration plan
        sample_plan = MigrationPlanBuilder.create_sample_plan()
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(sample_plan)
            print(f"Sample migration plan written to: {args.output}")
        else:
            print("Sample Migration Plan:")
            print(sample_plan)
    
    elif args.action == 'validate':
        if not args.plan_file:
            print("Error: --plan-file required for validate action")
            return
        
        try:
            plan = MigrationPlanBuilder.from_json_file(args.plan_file)
            print(f"Migration plan '{plan.migration_id}' is valid")
            print(f"Tables to migrate: {len(plan.table_mappings)}")
            for mapping in plan.table_mappings:
                print(f"  {mapping.source_table} -> {mapping.target_table} ({len(mapping.field_mappings)} fields)")
        except Exception as e:
            print(f"Migration plan validation failed: {str(e)}")
    
    elif args.action == 'migrate':
        if not args.plan_file:
            print("Error: --plan-file required for migrate action")
            return
        
        try:
            plan = MigrationPlanBuilder.from_json_file(args.plan_file)
            migrator = SchemaMigrator(plan)
            
            print(f"Starting migration: {plan.migration_id}")
            result = await migrator.execute_migration()
            
            print("\nMigration Results:")
            print(json.dumps(result, indent=2))
            
            # Save detailed results
            result_file = f"migration_result_{plan.migration_id}.json"
            with open(result_file, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\nDetailed results saved to: {result_file}")
            
        except Exception as e:
            print(f"Migration execution failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())