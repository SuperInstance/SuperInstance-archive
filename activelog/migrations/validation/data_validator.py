#!/usr/bin/env python3
"""
Data Validation Scripts for ActiveLog Migration
Comprehensive data integrity validation, schema compliance, and quality checks
"""

import asyncio
import json
import logging
import re
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Callable, Tuple
import aiofiles
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ValidationRule:
    """Defines a single validation rule"""
    rule_id: str
    rule_name: str
    rule_type: str  # 'schema', 'data_quality', 'business_logic', 'referential_integrity'
    severity: str  # 'critical', 'warning', 'info'
    description: str
    table_name: Optional[str] = None
    column_name: Optional[str] = None
    validation_query: Optional[str] = None
    expected_result: Any = None
    custom_validator: Optional[Callable] = None

@dataclass
class ValidationResult:
    """Result of a single validation rule execution"""
    rule_id: str
    rule_name: str
    status: str  # 'passed', 'failed', 'error'
    severity: str
    description: str
    error_message: Optional[str] = None
    affected_records: int = 0
    sample_failures: List[Dict[str, Any]] = None
    execution_time: float = 0.0

@dataclass
class ValidationReport:
    """Comprehensive validation report"""
    validation_id: str
    database_name: str
    executed_at: datetime
    total_rules: int
    rules_passed: int
    rules_failed: int
    rules_error: int
    critical_failures: int
    warning_failures: int
    execution_time: float
    results: List[ValidationResult]
    summary: Dict[str, Any]

class SchemaValidator:
    """Validates database schema integrity and compliance"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
    
    async def initialize(self):
        """Initialize database connection"""
        self.engine = create_async_engine(self.database_url)
    
    async def validate_schema_structure(self) -> List[ValidationResult]:
        """Validate basic schema structure requirements"""
        results = []
        
        # Check required tables exist
        required_tables = ['users', 'activity_logs', 'activelog_migrations']
        for table in required_tables:
            result = await self._validate_table_exists(table)
            results.append(result)
        
        # Check required columns exist
        required_columns = {
            'users': ['id', 'email', 'created_at', 'updated_at'],
            'activity_logs': ['id', 'user_id', 'activity_type', 'occurred_at', 'created_at']
        }
        
        for table, columns in required_columns.items():
            for column in columns:
                result = await self._validate_column_exists(table, column)
                results.append(result)
        
        # Check primary keys
        primary_key_tables = ['users', 'activity_logs', 'activelog_migrations']
        for table in primary_key_tables:
            result = await self._validate_primary_key_exists(table)
            results.append(result)
        
        # Check foreign key constraints
        foreign_keys = [
            ('activity_logs', 'user_id', 'users', 'id')
        ]
        
        for child_table, child_column, parent_table, parent_column in foreign_keys:
            result = await self._validate_foreign_key_constraint(
                child_table, child_column, parent_table, parent_column
            )
            results.append(result)
        
        return results
    
    async def _validate_table_exists(self, table_name: str) -> ValidationResult:
        """Check if required table exists"""
        start_time = datetime.now()
        
        try:
            async with self.engine.begin() as conn:
                if 'postgresql' in self.database_url:
                    query = """
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_name = :table_name AND table_schema = 'public'
                    """
                elif 'mysql' in self.database_url:
                    query = """
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_name = :table_name AND table_schema = DATABASE()
                    """
                else:  # SQLite
                    query = """
                    SELECT COUNT(*) FROM sqlite_master 
                    WHERE type='table' AND name = :table_name
                    """
                
                result = await conn.execute(text(query), {"table_name": table_name})
                count = result.scalar()
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                if count > 0:
                    return ValidationResult(
                        rule_id=f"table_exists_{table_name}",
                        rule_name=f"Table {table_name} exists",
                        status="passed",
                        severity="critical",
                        description=f"Required table '{table_name}' exists in database",
                        execution_time=execution_time
                    )
                else:
                    return ValidationResult(
                        rule_id=f"table_exists_{table_name}",
                        rule_name=f"Table {table_name} exists",
                        status="failed",
                        severity="critical",
                        description=f"Required table '{table_name}' is missing from database",
                        execution_time=execution_time
                    )
        
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ValidationResult(
                rule_id=f"table_exists_{table_name}",
                rule_name=f"Table {table_name} exists",
                status="error",
                severity="critical",
                description=f"Error checking table existence: {str(e)}",
                error_message=str(e),
                execution_time=execution_time
            )
    
    async def _validate_column_exists(self, table_name: str, column_name: str) -> ValidationResult:
        """Check if required column exists in table"""
        start_time = datetime.now()
        
        try:
            async with self.engine.begin() as conn:
                if 'postgresql' in self.database_url:
                    query = """
                    SELECT COUNT(*) FROM information_schema.columns 
                    WHERE table_name = :table_name AND column_name = :column_name 
                    AND table_schema = 'public'
                    """
                elif 'mysql' in self.database_url:
                    query = """
                    SELECT COUNT(*) FROM information_schema.columns 
                    WHERE table_name = :table_name AND column_name = :column_name 
                    AND table_schema = DATABASE()
                    """
                else:  # SQLite
                    # For SQLite, we need to use PRAGMA
                    query = f"PRAGMA table_info({table_name})"
                    result = await conn.execute(text(query))
                    columns = [row[1] for row in result.fetchall()]
                    count = 1 if column_name in columns else 0
                
                if 'sqlite' not in self.database_url:
                    result = await conn.execute(text(query), {
                        "table_name": table_name,
                        "column_name": column_name
                    })
                    count = result.scalar()
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                if count > 0:
                    return ValidationResult(
                        rule_id=f"column_exists_{table_name}_{column_name}",
                        rule_name=f"Column {table_name}.{column_name} exists",
                        status="passed",
                        severity="critical",
                        description=f"Required column '{column_name}' exists in table '{table_name}'",
                        execution_time=execution_time
                    )
                else:
                    return ValidationResult(
                        rule_id=f"column_exists_{table_name}_{column_name}",
                        rule_name=f"Column {table_name}.{column_name} exists",
                        status="failed",
                        severity="critical",
                        description=f"Required column '{column_name}' is missing from table '{table_name}'",
                        execution_time=execution_time
                    )
        
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ValidationResult(
                rule_id=f"column_exists_{table_name}_{column_name}",
                rule_name=f"Column {table_name}.{column_name} exists",
                status="error",
                severity="critical",
                description=f"Error checking column existence: {str(e)}",
                error_message=str(e),
                execution_time=execution_time
            )
    
    async def _validate_primary_key_exists(self, table_name: str) -> ValidationResult:
        """Check if table has a primary key"""
        start_time = datetime.now()
        
        try:
            async with self.engine.begin() as conn:
                if 'postgresql' in self.database_url:
                    query = """
                    SELECT COUNT(*) FROM information_schema.table_constraints 
                    WHERE table_name = :table_name AND constraint_type = 'PRIMARY KEY' 
                    AND table_schema = 'public'
                    """
                elif 'mysql' in self.database_url:
                    query = """
                    SELECT COUNT(*) FROM information_schema.table_constraints 
                    WHERE table_name = :table_name AND constraint_type = 'PRIMARY KEY' 
                    AND table_schema = DATABASE()
                    """
                else:  # SQLite
                    query = f"PRAGMA table_info({table_name})"
                    result = await conn.execute(text(query))
                    primary_keys = [row for row in result.fetchall() if row[5] == 1]  # pk column is index 5
                    count = len(primary_keys)
                
                if 'sqlite' not in self.database_url:
                    result = await conn.execute(text(query), {"table_name": table_name})
                    count = result.scalar()
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                if count > 0:
                    return ValidationResult(
                        rule_id=f"primary_key_{table_name}",
                        rule_name=f"Table {table_name} has primary key",
                        status="passed",
                        severity="critical",
                        description=f"Table '{table_name}' has a primary key defined",
                        execution_time=execution_time
                    )
                else:
                    return ValidationResult(
                        rule_id=f"primary_key_{table_name}",
                        rule_name=f"Table {table_name} has primary key",
                        status="failed",
                        severity="critical",
                        description=f"Table '{table_name}' is missing a primary key",
                        execution_time=execution_time
                    )
        
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ValidationResult(
                rule_id=f"primary_key_{table_name}",
                rule_name=f"Table {table_name} has primary key",
                status="error",
                severity="critical",
                description=f"Error checking primary key: {str(e)}",
                error_message=str(e),
                execution_time=execution_time
            )
    
    async def _validate_foreign_key_constraint(self, child_table: str, child_column: str,
                                             parent_table: str, parent_column: str) -> ValidationResult:
        """Check foreign key constraint exists and is valid"""
        start_time = datetime.now()
        
        try:
            async with self.engine.begin() as conn:
                # Check orphaned records (foreign key violations)
                query = f"""
                SELECT COUNT(*) FROM {child_table} c
                LEFT JOIN {parent_table} p ON c.{child_column} = p.{parent_column}
                WHERE c.{child_column} IS NOT NULL AND p.{parent_column} IS NULL
                """
                
                result = await conn.execute(text(query))
                orphaned_count = result.scalar()
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                if orphaned_count == 0:
                    return ValidationResult(
                        rule_id=f"fk_{child_table}_{child_column}",
                        rule_name=f"Foreign key {child_table}.{child_column} valid",
                        status="passed",
                        severity="critical",
                        description=f"No orphaned records in {child_table}.{child_column}",
                        execution_time=execution_time
                    )
                else:
                    return ValidationResult(
                        rule_id=f"fk_{child_table}_{child_column}",
                        rule_name=f"Foreign key {child_table}.{child_column} valid",
                        status="failed",
                        severity="critical",
                        description=f"Found {orphaned_count} orphaned records in {child_table}.{child_column}",
                        affected_records=orphaned_count,
                        execution_time=execution_time
                    )
        
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ValidationResult(
                rule_id=f"fk_{child_table}_{child_column}",
                rule_name=f"Foreign key {child_table}.{child_column} valid",
                status="error",
                severity="critical",
                description=f"Error checking foreign key constraint: {str(e)}",
                error_message=str(e),
                execution_time=execution_time
            )
    
    async def close(self):
        """Close database connection"""
        if self.engine:
            await self.engine.dispose()

class DataQualityValidator:
    """Validates data quality and business rules"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
    
    async def initialize(self):
        """Initialize database connection"""
        self.engine = create_async_engine(self.database_url)
    
    async def validate_data_quality(self) -> List[ValidationResult]:
        """Run comprehensive data quality validation"""
        results = []
        
        # Null value checks
        null_checks = [
            ('users', 'email', 'critical'),
            ('users', 'created_at', 'critical'),
            ('activity_logs', 'user_id', 'critical'),
            ('activity_logs', 'activity_type', 'critical'),
            ('activity_logs', 'occurred_at', 'critical')
        ]
        
        for table, column, severity in null_checks:
            result = await self._validate_not_null(table, column, severity)
            results.append(result)
        
        # Email format validation
        result = await self._validate_email_format()
        results.append(result)
        
        # Date range validation
        result = await self._validate_date_ranges()
        results.append(result)
        
        # Duplicate detection
        result = await self._validate_unique_emails()
        results.append(result)
        
        # Data consistency checks
        result = await self._validate_activity_log_consistency()
        results.append(result)
        
        # Character encoding validation
        result = await self._validate_character_encoding()
        results.append(result)
        
        # Value range validation
        result = await self._validate_value_ranges()
        results.append(result)
        
        return results
    
    async def _validate_not_null(self, table_name: str, column_name: str, severity: str) -> ValidationResult:
        """Check for null values in required columns"""
        start_time = datetime.now()
        
        try:
            async with self.engine.begin() as conn:
                query = f"SELECT COUNT(*) FROM {table_name} WHERE {column_name} IS NULL"
                result = await conn.execute(text(query))
                null_count = result.scalar()
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                if null_count == 0:
                    return ValidationResult(
                        rule_id=f"not_null_{table_name}_{column_name}",
                        rule_name=f"{table_name}.{column_name} not null",
                        status="passed",
                        severity=severity,
                        description=f"No null values found in {table_name}.{column_name}",
                        execution_time=execution_time
                    )
                else:
                    return ValidationResult(
                        rule_id=f"not_null_{table_name}_{column_name}",
                        rule_name=f"{table_name}.{column_name} not null",
                        status="failed",
                        severity=severity,
                        description=f"Found {null_count} null values in {table_name}.{column_name}",
                        affected_records=null_count,
                        execution_time=execution_time
                    )
        
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ValidationResult(
                rule_id=f"not_null_{table_name}_{column_name}",
                rule_name=f"{table_name}.{column_name} not null",
                status="error",
                severity=severity,
                description=f"Error checking null values: {str(e)}",
                error_message=str(e),
                execution_time=execution_time
            )
    
    async def _validate_email_format(self) -> ValidationResult:
        """Validate email format using regex"""
        start_time = datetime.now()
        
        try:
            async with self.engine.begin() as conn:
                # Basic email regex pattern
                if 'postgresql' in self.database_url:
                    query = """
                    SELECT COUNT(*) FROM users 
                    WHERE email IS NOT NULL 
                    AND email !~ '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                    """
                else:
                    # Fallback for databases without regex support
                    query = """
                    SELECT COUNT(*) FROM users 
                    WHERE email IS NOT NULL 
                    AND (email NOT LIKE '%@%' OR email NOT LIKE '%.%')
                    """
                
                result = await conn.execute(text(query))
                invalid_count = result.scalar()
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                if invalid_count == 0:
                    return ValidationResult(
                        rule_id="email_format_validation",
                        rule_name="Email format validation",
                        status="passed",
                        severity="warning",
                        description="All email addresses have valid format",
                        execution_time=execution_time
                    )
                else:
                    return ValidationResult(
                        rule_id="email_format_validation",
                        rule_name="Email format validation",
                        status="failed",
                        severity="warning",
                        description=f"Found {invalid_count} invalid email formats",
                        affected_records=invalid_count,
                        execution_time=execution_time
                    )
        
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ValidationResult(
                rule_id="email_format_validation",
                rule_name="Email format validation",
                status="error",
                severity="warning",
                description=f"Error validating email format: {str(e)}",
                error_message=str(e),
                execution_time=execution_time
            )
    
    async def _validate_date_ranges(self) -> ValidationResult:
        """Validate date ranges are reasonable"""
        start_time = datetime.now()
        
        try:
            async with self.engine.begin() as conn:
                # Check for future dates in created_at
                query = """
                SELECT COUNT(*) FROM users 
                WHERE created_at > NOW() + INTERVAL '1 hour'
                """
                
                try:
                    result = await conn.execute(text(query))
                    future_count = result.scalar()
                except:
                    # Fallback for databases without INTERVAL support
                    query = "SELECT COUNT(*) FROM users WHERE created_at > datetime('now', '+1 hour')"
                    result = await conn.execute(text(query))
                    future_count = result.scalar()
                
                # Check for very old dates (before 1990)
                query2 = "SELECT COUNT(*) FROM users WHERE created_at < '1990-01-01'"
                result2 = await conn.execute(text(query2))
                old_count = result2.scalar()
                
                total_invalid = future_count + old_count
                execution_time = (datetime.now() - start_time).total_seconds()
                
                if total_invalid == 0:
                    return ValidationResult(
                        rule_id="date_range_validation",
                        rule_name="Date range validation",
                        status="passed",
                        severity="warning",
                        description="All dates are within reasonable ranges",
                        execution_time=execution_time
                    )
                else:
                    return ValidationResult(
                        rule_id="date_range_validation",
                        rule_name="Date range validation",
                        status="failed",
                        severity="warning",
                        description=f"Found {total_invalid} records with invalid dates ({future_count} future, {old_count} very old)",
                        affected_records=total_invalid,
                        execution_time=execution_time
                    )
        
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ValidationResult(
                rule_id="date_range_validation",
                rule_name="Date range validation",
                status="error",
                severity="warning",
                description=f"Error validating date ranges: {str(e)}",
                error_message=str(e),
                execution_time=execution_time
            )
    
    async def _validate_unique_emails(self) -> ValidationResult:
        """Check for duplicate email addresses"""
        start_time = datetime.now()
        
        try:
            async with self.engine.begin() as conn:
                query = """
                SELECT COUNT(*) FROM (
                    SELECT email FROM users 
                    WHERE email IS NOT NULL 
                    GROUP BY email 
                    HAVING COUNT(*) > 1
                ) duplicates
                """
                
                result = await conn.execute(text(query))
                duplicate_count = result.scalar()
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                if duplicate_count == 0:
                    return ValidationResult(
                        rule_id="unique_email_validation",
                        rule_name="Unique email validation",
                        status="passed",
                        severity="critical",
                        description="All email addresses are unique",
                        execution_time=execution_time
                    )
                else:
                    return ValidationResult(
                        rule_id="unique_email_validation",
                        rule_name="Unique email validation",
                        status="failed",
                        severity="critical",
                        description=f"Found {duplicate_count} duplicate email addresses",
                        affected_records=duplicate_count,
                        execution_time=execution_time
                    )
        
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ValidationResult(
                rule_id="unique_email_validation",
                rule_name="Unique email validation",
                status="error",
                severity="critical",
                description=f"Error checking email uniqueness: {str(e)}",
                error_message=str(e),
                execution_time=execution_time
            )
    
    async def _validate_activity_log_consistency(self) -> ValidationResult:
        """Validate activity log data consistency"""
        start_time = datetime.now()
        
        try:
            async with self.engine.begin() as conn:
                # Check if occurred_at is before created_at
                query = """
                SELECT COUNT(*) FROM activity_logs 
                WHERE occurred_at > created_at + INTERVAL '1 hour'
                """
                
                try:
                    result = await conn.execute(text(query))
                    inconsistent_count = result.scalar()
                except:
                    # Fallback for databases without INTERVAL support
                    query = """
                    SELECT COUNT(*) FROM activity_logs 
                    WHERE occurred_at > datetime(created_at, '+1 hour')
                    """
                    result = await conn.execute(text(query))
                    inconsistent_count = result.scalar()
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                if inconsistent_count == 0:
                    return ValidationResult(
                        rule_id="activity_log_consistency",
                        rule_name="Activity log consistency",
                        status="passed",
                        severity="warning",
                        description="Activity log timestamps are consistent",
                        execution_time=execution_time
                    )
                else:
                    return ValidationResult(
                        rule_id="activity_log_consistency",
                        rule_name="Activity log consistency",
                        status="failed",
                        severity="warning",
                        description=f"Found {inconsistent_count} activity logs with inconsistent timestamps",
                        affected_records=inconsistent_count,
                        execution_time=execution_time
                    )
        
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ValidationResult(
                rule_id="activity_log_consistency",
                rule_name="Activity log consistency",
                status="error",
                severity="warning",
                description=f"Error checking activity log consistency: {str(e)}",
                error_message=str(e),
                execution_time=execution_time
            )
    
    async def _validate_character_encoding(self) -> ValidationResult:
        """Check for character encoding issues"""
        start_time = datetime.now()
        
        try:
            async with self.engine.begin() as conn:
                # Check for suspicious characters that might indicate encoding issues
                query = """
                SELECT COUNT(*) FROM users 
                WHERE full_name ~ '[^\x00-\x7F]'
                OR email ~ '[^\x00-\x7F]'
                """
                
                try:
                    result = await conn.execute(text(query))
                    encoding_issues = result.scalar()
                except:
                    # Fallback for databases without regex support
                    encoding_issues = 0
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                return ValidationResult(
                    rule_id="character_encoding_validation",
                    rule_name="Character encoding validation",
                    status="passed" if encoding_issues == 0 else "failed",
                    severity="info",
                    description=f"Found {encoding_issues} records with non-ASCII characters" if encoding_issues > 0 else "No character encoding issues detected",
                    affected_records=encoding_issues,
                    execution_time=execution_time
                )
        
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ValidationResult(
                rule_id="character_encoding_validation",
                rule_name="Character encoding validation",
                status="error",
                severity="info",
                description=f"Error checking character encoding: {str(e)}",
                error_message=str(e),
                execution_time=execution_time
            )
    
    async def _validate_value_ranges(self) -> ValidationResult:
        """Validate numeric value ranges"""
        start_time = datetime.now()
        
        try:
            async with self.engine.begin() as conn:
                # Check for negative sentiment scores outside valid range
                query = """
                SELECT COUNT(*) FROM activity_logs 
                WHERE sentiment_score IS NOT NULL 
                AND (sentiment_score < -1.0 OR sentiment_score > 1.0)
                """
                
                result = await conn.execute(text(query))
                invalid_range_count = result.scalar()
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                if invalid_range_count == 0:
                    return ValidationResult(
                        rule_id="value_range_validation",
                        rule_name="Value range validation",
                        status="passed",
                        severity="warning",
                        description="All numeric values are within valid ranges",
                        execution_time=execution_time
                    )
                else:
                    return ValidationResult(
                        rule_id="value_range_validation",
                        rule_name="Value range validation",
                        status="failed",
                        severity="warning",
                        description=f"Found {invalid_range_count} records with values outside valid ranges",
                        affected_records=invalid_range_count,
                        execution_time=execution_time
                    )
        
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ValidationResult(
                rule_id="value_range_validation",
                rule_name="Value range validation",
                status="error",
                severity="warning",
                description=f"Error validating value ranges: {str(e)}",
                error_message=str(e),
                execution_time=execution_time
            )
    
    async def close(self):
        """Close database connection"""
        if self.engine:
            await self.engine.dispose()

class FileDataValidator:
    """Validates data files (CSV, JSON, etc.) before import"""
    
    def __init__(self):
        self.supported_formats = ['.csv', '.json', '.xlsx', '.parquet']
    
    async def validate_file_structure(self, file_path: str) -> List[ValidationResult]:
        """Validate file structure and format"""
        results = []
        file_path = Path(file_path)
        
        # File existence check
        result = await self._validate_file_exists(file_path)
        results.append(result)
        
        if result.status != "passed":
            return results
        
        # File format check
        result = await self._validate_file_format(file_path)
        results.append(result)
        
        # File size check
        result = await self._validate_file_size(file_path)
        results.append(result)
        
        # Content validation based on file type
        if file_path.suffix.lower() == '.csv':
            csv_results = await self._validate_csv_file(file_path)
            results.extend(csv_results)
        elif file_path.suffix.lower() == '.json':
            json_results = await self._validate_json_file(file_path)
            results.extend(json_results)
        
        return results
    
    async def _validate_file_exists(self, file_path: Path) -> ValidationResult:
        """Check if file exists and is readable"""
        start_time = datetime.now()
        
        try:
            if file_path.exists() and file_path.is_file():
                execution_time = (datetime.now() - start_time).total_seconds()
                return ValidationResult(
                    rule_id=f"file_exists_{file_path.name}",
                    rule_name="File exists",
                    status="passed",
                    severity="critical",
                    description=f"File {file_path.name} exists and is readable",
                    execution_time=execution_time
                )
            else:
                execution_time = (datetime.now() - start_time).total_seconds()
                return ValidationResult(
                    rule_id=f"file_exists_{file_path.name}",
                    rule_name="File exists",
                    status="failed",
                    severity="critical",
                    description=f"File {file_path.name} does not exist or is not readable",
                    execution_time=execution_time
                )
        
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ValidationResult(
                rule_id=f"file_exists_{file_path.name}",
                rule_name="File exists",
                status="error",
                severity="critical",
                description=f"Error checking file existence: {str(e)}",
                error_message=str(e),
                execution_time=execution_time
            )
    
    async def _validate_file_format(self, file_path: Path) -> ValidationResult:
        """Validate file format is supported"""
        start_time = datetime.now()
        
        file_extension = file_path.suffix.lower()
        execution_time = (datetime.now() - start_time).total_seconds()
        
        if file_extension in self.supported_formats:
            return ValidationResult(
                rule_id=f"file_format_{file_path.name}",
                rule_name="File format supported",
                status="passed",
                severity="critical",
                description=f"File format {file_extension} is supported",
                execution_time=execution_time
            )
        else:
            return ValidationResult(
                rule_id=f"file_format_{file_path.name}",
                rule_name="File format supported",
                status="failed",
                severity="critical",
                description=f"File format {file_extension} is not supported. Supported formats: {self.supported_formats}",
                execution_time=execution_time
            )
    
    async def _validate_file_size(self, file_path: Path) -> ValidationResult:
        """Validate file size is reasonable"""
        start_time = datetime.now()
        
        try:
            file_size = file_path.stat().st_size
            max_size = 1024 * 1024 * 1024  # 1GB limit
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            if file_size <= max_size:
                return ValidationResult(
                    rule_id=f"file_size_{file_path.name}",
                    rule_name="File size validation",
                    status="passed",
                    severity="warning",
                    description=f"File size {file_size / (1024*1024):.2f} MB is within limits",
                    execution_time=execution_time
                )
            else:
                return ValidationResult(
                    rule_id=f"file_size_{file_path.name}",
                    rule_name="File size validation",
                    status="failed",
                    severity="warning",
                    description=f"File size {file_size / (1024*1024):.2f} MB exceeds maximum limit of {max_size / (1024*1024)} MB",
                    execution_time=execution_time
                )
        
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ValidationResult(
                rule_id=f"file_size_{file_path.name}",
                rule_name="File size validation",
                status="error",
                severity="warning",
                description=f"Error checking file size: {str(e)}",
                error_message=str(e),
                execution_time=execution_time
            )
    
    async def _validate_csv_file(self, file_path: Path) -> List[ValidationResult]:
        """Validate CSV file structure and content"""
        results = []
        start_time = datetime.now()
        
        try:
            # Read CSV file
            df = pd.read_csv(file_path)
            
            # Check if file is empty
            if len(df) == 0:
                results.append(ValidationResult(
                    rule_id=f"csv_empty_{file_path.name}",
                    rule_name="CSV not empty",
                    status="failed",
                    severity="warning",
                    description="CSV file is empty",
                    execution_time=(datetime.now() - start_time).total_seconds()
                ))
            else:
                results.append(ValidationResult(
                    rule_id=f"csv_empty_{file_path.name}",
                    rule_name="CSV not empty",
                    status="passed",
                    severity="warning",
                    description=f"CSV file contains {len(df)} rows",
                    execution_time=(datetime.now() - start_time).total_seconds()
                ))
            
            # Check for required columns (example)
            required_columns = ['email', 'created_at']  # Customize based on your needs
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                results.append(ValidationResult(
                    rule_id=f"csv_columns_{file_path.name}",
                    rule_name="Required CSV columns",
                    status="failed",
                    severity="critical",
                    description=f"Missing required columns: {missing_columns}",
                    execution_time=(datetime.now() - start_time).total_seconds()
                ))
            else:
                results.append(ValidationResult(
                    rule_id=f"csv_columns_{file_path.name}",
                    rule_name="Required CSV columns",
                    status="passed",
                    severity="critical",
                    description="All required columns present",
                    execution_time=(datetime.now() - start_time).total_seconds()
                ))
            
            # Check for duplicate rows
            duplicate_count = len(df) - len(df.drop_duplicates())
            if duplicate_count > 0:
                results.append(ValidationResult(
                    rule_id=f"csv_duplicates_{file_path.name}",
                    rule_name="CSV duplicate rows",
                    status="failed",
                    severity="warning",
                    description=f"Found {duplicate_count} duplicate rows",
                    affected_records=duplicate_count,
                    execution_time=(datetime.now() - start_time).total_seconds()
                ))
            else:
                results.append(ValidationResult(
                    rule_id=f"csv_duplicates_{file_path.name}",
                    rule_name="CSV duplicate rows",
                    status="passed",
                    severity="warning",
                    description="No duplicate rows found",
                    execution_time=(datetime.now() - start_time).total_seconds()
                ))
        
        except Exception as e:
            results.append(ValidationResult(
                rule_id=f"csv_validation_{file_path.name}",
                rule_name="CSV file validation",
                status="error",
                severity="critical",
                description=f"Error validating CSV file: {str(e)}",
                error_message=str(e),
                execution_time=(datetime.now() - start_time).total_seconds()
            ))
        
        return results
    
    async def _validate_json_file(self, file_path: Path) -> List[ValidationResult]:
        """Validate JSON file structure and content"""
        results = []
        start_time = datetime.now()
        
        try:
            # Read and parse JSON file
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
                data = json.loads(content)
            
            # Check if JSON is valid structure
            if isinstance(data, (list, dict)):
                results.append(ValidationResult(
                    rule_id=f"json_structure_{file_path.name}",
                    rule_name="JSON structure valid",
                    status="passed",
                    severity="critical",
                    description="JSON file has valid structure",
                    execution_time=(datetime.now() - start_time).total_seconds()
                ))
            else:
                results.append(ValidationResult(
                    rule_id=f"json_structure_{file_path.name}",
                    rule_name="JSON structure valid",
                    status="failed",
                    severity="critical",
                    description="JSON file does not contain valid list or object structure",
                    execution_time=(datetime.now() - start_time).total_seconds()
                ))
            
            # Check if data is not empty
            if (isinstance(data, list) and len(data) > 0) or (isinstance(data, dict) and len(data) > 0):
                count = len(data) if isinstance(data, list) else 1
                results.append(ValidationResult(
                    rule_id=f"json_empty_{file_path.name}",
                    rule_name="JSON not empty",
                    status="passed",
                    severity="warning",
                    description=f"JSON file contains {count} records",
                    execution_time=(datetime.now() - start_time).total_seconds()
                ))
            else:
                results.append(ValidationResult(
                    rule_id=f"json_empty_{file_path.name}",
                    rule_name="JSON not empty",
                    status="failed",
                    severity="warning",
                    description="JSON file is empty",
                    execution_time=(datetime.now() - start_time).total_seconds()
                ))
        
        except json.JSONDecodeError as e:
            results.append(ValidationResult(
                rule_id=f"json_parse_{file_path.name}",
                rule_name="JSON parsing",
                status="failed",
                severity="critical",
                description=f"Invalid JSON format: {str(e)}",
                error_message=str(e),
                execution_time=(datetime.now() - start_time).total_seconds()
            ))
        
        except Exception as e:
            results.append(ValidationResult(
                rule_id=f"json_validation_{file_path.name}",
                rule_name="JSON file validation",
                status="error",
                severity="critical",
                description=f"Error validating JSON file: {str(e)}",
                error_message=str(e),
                execution_time=(datetime.now() - start_time).total_seconds()
            ))
        
        return results

class ValidationOrchestrator:
    """Orchestrates comprehensive validation across all components"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.schema_validator = SchemaValidator(database_url)
        self.data_quality_validator = DataQualityValidator(database_url)
        self.file_validator = FileDataValidator()
    
    async def run_comprehensive_validation(self, include_files: List[str] = None) -> ValidationReport:
        """Run complete validation suite"""
        validation_id = f"validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()
        
        all_results = []
        
        try:
            # Initialize database validators
            await self.schema_validator.initialize()
            await self.data_quality_validator.initialize()
            
            # Run schema validation
            logger.info("Running schema validation...")
            schema_results = await self.schema_validator.validate_schema_structure()
            all_results.extend(schema_results)
            
            # Run data quality validation
            logger.info("Running data quality validation...")
            quality_results = await self.data_quality_validator.validate_data_quality()
            all_results.extend(quality_results)
            
            # Run file validation if files specified
            if include_files:
                logger.info("Running file validation...")
                for file_path in include_files:
                    file_results = await self.file_validator.validate_file_structure(file_path)
                    all_results.extend(file_results)
            
        finally:
            # Clean up connections
            await self.schema_validator.close()
            await self.data_quality_validator.close()
        
        # Generate summary statistics
        total_rules = len(all_results)
        rules_passed = len([r for r in all_results if r.status == "passed"])
        rules_failed = len([r for r in all_results if r.status == "failed"])
        rules_error = len([r for r in all_results if r.status == "error"])
        critical_failures = len([r for r in all_results if r.status == "failed" and r.severity == "critical"])
        warning_failures = len([r for r in all_results if r.status == "failed" and r.severity == "warning"])
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Create summary
        summary = {
            'validation_score': (rules_passed / total_rules * 100) if total_rules > 0 else 0,
            'critical_issues': critical_failures,
            'warning_issues': warning_failures,
            'data_quality_score': len([r for r in quality_results if r.status == "passed"]) / len(quality_results) * 100 if quality_results else 100,
            'schema_compliance': len([r for r in schema_results if r.status == "passed"]) / len(schema_results) * 100 if schema_results else 100
        }
        
        # Create validation report
        report = ValidationReport(
            validation_id=validation_id,
            database_name=self.database_url.split('/')[-1] if '/' in self.database_url else 'unknown',
            executed_at=start_time,
            total_rules=total_rules,
            rules_passed=rules_passed,
            rules_failed=rules_failed,
            rules_error=rules_error,
            critical_failures=critical_failures,
            warning_failures=warning_failures,
            execution_time=execution_time,
            results=all_results,
            summary=summary
        )
        
        return report
    
    def generate_validation_report(self, report: ValidationReport, output_file: str = None) -> str:
        """Generate human-readable validation report"""
        report_content = f"""
# Data Validation Report
**Validation ID:** {report.validation_id}
**Database:** {report.database_name}
**Executed:** {report.executed_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
**Duration:** {report.execution_time:.2f} seconds

## Summary
- **Validation Score:** {report.summary['validation_score']:.1f}%
- **Rules Executed:** {report.total_rules}
- **Passed:** {report.rules_passed} ✅
- **Failed:** {report.rules_failed} ❌
- **Errors:** {report.rules_error} ⚠️

### Critical Issues: {report.critical_failures}
### Warning Issues: {report.warning_failures}

## Detailed Results

### Critical Failures
"""
        
        critical_results = [r for r in report.results if r.status == "failed" and r.severity == "critical"]
        if critical_results:
            for result in critical_results:
                report_content += f"- **{result.rule_name}**: {result.description}\n"
                if result.affected_records:
                    report_content += f"  - Affected records: {result.affected_records}\n"
        else:
            report_content += "No critical failures found ✅\n"
        
        report_content += "\n### Warning Failures\n"
        warning_results = [r for r in report.results if r.status == "failed" and r.severity == "warning"]
        if warning_results:
            for result in warning_results:
                report_content += f"- **{result.rule_name}**: {result.description}\n"
                if result.affected_records:
                    report_content += f"  - Affected records: {result.affected_records}\n"
        else:
            report_content += "No warning failures found ✅\n"
        
        report_content += "\n### Errors\n"
        error_results = [r for r in report.results if r.status == "error"]
        if error_results:
            for result in error_results:
                report_content += f"- **{result.rule_name}**: {result.description}\n"
                if result.error_message:
                    report_content += f"  - Error: {result.error_message}\n"
        else:
            report_content += "No validation errors encountered ✅\n"
        
        # Save report if output file specified
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_content)
            logger.info(f"Validation report saved to: {output_file}")
        
        return report_content

# CLI Interface
async def main():
    """Command-line interface for data validation"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ActiveLog Data Validation Tool')
    parser.add_argument('action', choices=['validate', 'schema', 'quality', 'files'])
    parser.add_argument('--database-url', required=True, help='Database connection URL')
    parser.add_argument('--files', nargs='+', help='Files to validate')
    parser.add_argument('--output', help='Output file for validation report')
    parser.add_argument('--format', choices=['text', 'json'], default='text', help='Report format')
    
    args = parser.parse_args()
    
    orchestrator = ValidationOrchestrator(args.database_url)
    
    if args.action == 'validate':
        # Run comprehensive validation
        report = await orchestrator.run_comprehensive_validation(args.files)
        
        if args.format == 'json':
            output = json.dumps(asdict(report), indent=2, default=str)
        else:
            output = orchestrator.generate_validation_report(report)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"Validation report saved to: {args.output}")
        else:
            print(output)
        
        # Exit with error code if critical failures found
        if report.critical_failures > 0:
            exit(1)
    
    elif args.action == 'schema':
        # Run schema validation only
        await orchestrator.schema_validator.initialize()
        results = await orchestrator.schema_validator.validate_schema_structure()
        await orchestrator.schema_validator.close()
        
        print("Schema Validation Results:")
        for result in results:
            status_icon = "✅" if result.status == "passed" else "❌" if result.status == "failed" else "⚠️"
            print(f"{status_icon} {result.rule_name}: {result.description}")
    
    elif args.action == 'quality':
        # Run data quality validation only
        await orchestrator.data_quality_validator.initialize()
        results = await orchestrator.data_quality_validator.validate_data_quality()
        await orchestrator.data_quality_validator.close()
        
        print("Data Quality Validation Results:")
        for result in results:
            status_icon = "✅" if result.status == "passed" else "❌" if result.status == "failed" else "⚠️"
            print(f"{status_icon} {result.rule_name}: {result.description}")
    
    elif args.action == 'files':
        # Run file validation only
        if not args.files:
            print("Error: --files required for file validation")
            return
        
        for file_path in args.files:
            print(f"\nValidating file: {file_path}")
            results = await orchestrator.file_validator.validate_file_structure(file_path)
            
            for result in results:
                status_icon = "✅" if result.status == "passed" else "❌" if result.status == "failed" else "⚠️"
                print(f"{status_icon} {result.rule_name}: {result.description}")

if __name__ == "__main__":
    asyncio.run(main())