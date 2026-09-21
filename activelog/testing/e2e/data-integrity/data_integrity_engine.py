"""
Data Integrity Verification Engine for ActiveLog Platform

This module provides comprehensive data integrity testing including database
consistency checks, data validation, corruption detection, and audit trails.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from enum import Enum
import json
import asyncio
import hashlib
import sqlite3
import psycopg2
import pymongo
import redis
import logging
from pathlib import Path
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text, inspect
import subprocess
import re


class DataIntegrityTestType(Enum):
    """Types of data integrity tests"""
    REFERENTIAL_INTEGRITY = "referential_integrity"
    DATA_VALIDATION = "data_validation"
    CONSISTENCY_CHECK = "consistency_check"
    CORRUPTION_DETECTION = "corruption_detection"
    AUDIT_TRAIL = "audit_trail"
    BACKUP_VERIFICATION = "backup_verification"
    SYNCHRONIZATION = "synchronization"
    CONSTRAINT_VALIDATION = "constraint_validation"
    FOREIGN_KEY_CHECK = "foreign_key_check"
    DUPLICATE_DETECTION = "duplicate_detection"


class DataSourceType(Enum):
    """Types of data sources"""
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"
    MONGODB = "mongodb"
    REDIS = "redis"
    JSON_FILE = "json_file"
    CSV_FILE = "csv_file"
    API_ENDPOINT = "api_endpoint"
    ELASTICSEARCH = "elasticsearch"


class IntegrityIssueLevel(Enum):
    """Severity levels for integrity issues"""
    CRITICAL = "critical"  # Data corruption, complete loss
    HIGH = "high"  # Referential integrity violations
    MEDIUM = "medium"  # Constraint violations, inconsistencies
    LOW = "low"  # Minor data quality issues
    INFORMATIONAL = "informational"  # Statistics and warnings


@dataclass
class DataIntegrityRule:
    """Definition of a data integrity rule"""
    rule_id: str
    name: str
    description: str
    test_type: DataIntegrityTestType
    data_source: str
    table_name: Optional[str] = None
    column_name: Optional[str] = None
    rule_expression: Optional[str] = None  # SQL or validation expression
    expected_result: Optional[Any] = None
    tolerance: float = 0.0  # Allowed variance
    severity: IntegrityIssueLevel = IntegrityIssueLevel.MEDIUM
    tags: List[str] = field(default_factory=list)


@dataclass
class IntegrityTestResult:
    """Result of a data integrity test"""
    test_id: str
    rule_id: str
    test_type: DataIntegrityTestType
    status: str  # "passed", "failed", "warning"
    severity: IntegrityIssueLevel
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    affected_records: int = 0
    data_samples: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    execution_time: float = 0.0


@dataclass
class DataIntegrityReport:
    """Comprehensive data integrity report"""
    report_id: str
    test_session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    warnings: int = 0
    results: List[IntegrityTestResult] = field(default_factory=list)
    data_sources_tested: List[str] = field(default_factory=list)
    summary_statistics: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


class DatabaseConnector:
    """Manages connections to various database types"""
    
    def __init__(self):
        self.connections: Dict[str, Any] = {}
    
    def add_connection(self, source_id: str, source_type: DataSourceType, 
                      connection_string: str, **kwargs):
        """Add a database connection"""
        try:
            if source_type == DataSourceType.POSTGRESQL:
                import psycopg2.extras
                conn = psycopg2.connect(connection_string)
                conn.autocommit = True
                self.connections[source_id] = {
                    'type': source_type,
                    'connection': conn,
                    'cursor': conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                }
            
            elif source_type == DataSourceType.SQLITE:
                conn = sqlite3.connect(connection_string)
                conn.row_factory = sqlite3.Row
                self.connections[source_id] = {
                    'type': source_type,
                    'connection': conn,
                    'cursor': conn.cursor()
                }
            
            elif source_type == DataSourceType.MONGODB:
                from pymongo import MongoClient
                client = MongoClient(connection_string)
                db_name = kwargs.get('database', 'test')
                self.connections[source_id] = {
                    'type': source_type,
                    'client': client,
                    'database': client[db_name]
                }
            
            elif source_type == DataSourceType.REDIS:
                import redis
                r = redis.from_url(connection_string)
                self.connections[source_id] = {
                    'type': source_type,
                    'connection': r
                }
            
            logging.info(f"Connected to {source_type.value} data source: {source_id}")
            
        except Exception as e:
            logging.error(f"Failed to connect to {source_id}: {e}")
            raise
    
    def execute_query(self, source_id: str, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """Execute query on specified data source"""
        if source_id not in self.connections:
            raise ValueError(f"Data source {source_id} not found")
        
        conn_info = self.connections[source_id]
        
        try:
            if conn_info['type'] in [DataSourceType.POSTGRESQL, DataSourceType.SQLITE]:
                cursor = conn_info['cursor']
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                results = cursor.fetchall()
                return [dict(row) for row in results]
            
            elif conn_info['type'] == DataSourceType.MONGODB:
                # Parse MongoDB query (simplified)
                # In real implementation, would parse proper MongoDB query syntax
                db = conn_info['database']
                collection_name = query.split('.')[0] if '.' in query else 'default'
                collection = db[collection_name]
                results = list(collection.find())
                return results
            
            elif conn_info['type'] == DataSourceType.REDIS:
                # Handle Redis commands (simplified)
                r = conn_info['connection']
                if query.startswith('KEYS'):
                    pattern = query.split(' ', 1)[1] if ' ' in query else '*'
                    keys = r.keys(pattern)
                    return [{'key': key.decode() if isinstance(key, bytes) else key} for key in keys]
                elif query.startswith('GET'):
                    key = query.split(' ', 1)[1]
                    value = r.get(key)
                    return [{'key': key, 'value': value.decode() if isinstance(value, bytes) else value}]
            
        except Exception as e:
            logging.error(f"Query execution failed on {source_id}: {e}")
            raise
        
        return []
    
    def get_table_info(self, source_id: str, table_name: str) -> Dict[str, Any]:
        """Get metadata about a table"""
        if source_id not in self.connections:
            raise ValueError(f"Data source {source_id} not found")
        
        conn_info = self.connections[source_id]
        
        try:
            if conn_info['type'] == DataSourceType.POSTGRESQL:
                query = """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = %s
                ORDER BY ordinal_position
                """
                columns = self.execute_query(source_id, query, (table_name,))
                
                # Get row count
                count_query = f"SELECT COUNT(*) as row_count FROM {table_name}"
                count_result = self.execute_query(source_id, count_query)
                row_count = count_result[0]['row_count'] if count_result else 0
                
                return {
                    'table_name': table_name,
                    'columns': columns,
                    'row_count': row_count,
                    'data_source': source_id
                }
            
            elif conn_info['type'] == DataSourceType.SQLITE:
                # Get table info
                pragma_query = f"PRAGMA table_info({table_name})"
                columns = self.execute_query(source_id, pragma_query)
                
                # Get row count
                count_query = f"SELECT COUNT(*) as row_count FROM {table_name}"
                count_result = self.execute_query(source_id, count_query)
                row_count = count_result[0]['row_count'] if count_result else 0
                
                return {
                    'table_name': table_name,
                    'columns': columns,
                    'row_count': row_count,
                    'data_source': source_id
                }
        
        except Exception as e:
            logging.error(f"Failed to get table info for {table_name}: {e}")
            return {}
    
    def close_all(self):
        """Close all database connections"""
        for source_id, conn_info in self.connections.items():
            try:
                if conn_info['type'] in [DataSourceType.POSTGRESQL, DataSourceType.SQLITE]:
                    conn_info['connection'].close()
                elif conn_info['type'] == DataSourceType.MONGODB:
                    conn_info['client'].close()
                elif conn_info['type'] == DataSourceType.REDIS:
                    conn_info['connection'].close()
            except Exception as e:
                logging.error(f"Error closing connection {source_id}: {e}")
        
        self.connections.clear()


class ReferentialIntegrityTester:
    """Tests referential integrity constraints"""
    
    def __init__(self, db_connector: DatabaseConnector):
        self.db_connector = db_connector
    
    def test_foreign_key_constraints(self, source_id: str, table_name: str, 
                                   foreign_key_column: str, referenced_table: str,
                                   referenced_column: str) -> IntegrityTestResult:
        """Test foreign key constraint integrity"""
        start_time = datetime.now()
        
        try:
            # Find orphaned records (foreign key values that don't exist in referenced table)
            query = f"""
                SELECT DISTINCT {foreign_key_column}
                FROM {table_name} t1
                WHERE {foreign_key_column} IS NOT NULL
                AND NOT EXISTS (
                    SELECT 1 FROM {referenced_table} t2 
                    WHERE t2.{referenced_column} = t1.{foreign_key_column}
                )
            """
            
            orphaned_records = self.db_connector.execute_query(source_id, query)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            if orphaned_records:
                return IntegrityTestResult(
                    test_id=f"fk_constraint_{table_name}_{foreign_key_column}",
                    rule_id="foreign_key_integrity",
                    test_type=DataIntegrityTestType.FOREIGN_KEY_CHECK,
                    status="failed",
                    severity=IntegrityIssueLevel.HIGH,
                    message=f"Foreign key constraint violation in {table_name}.{foreign_key_column}",
                    details={
                        "table": table_name,
                        "foreign_key_column": foreign_key_column,
                        "referenced_table": referenced_table,
                        "referenced_column": referenced_column,
                        "orphaned_values": [str(record[foreign_key_column]) for record in orphaned_records[:10]]
                    },
                    affected_records=len(orphaned_records),
                    data_samples=orphaned_records[:5],
                    execution_time=execution_time
                )
            else:
                return IntegrityTestResult(
                    test_id=f"fk_constraint_{table_name}_{foreign_key_column}",
                    rule_id="foreign_key_integrity",
                    test_type=DataIntegrityTestType.FOREIGN_KEY_CHECK,
                    status="passed",
                    severity=IntegrityIssueLevel.INFORMATIONAL,
                    message=f"Foreign key constraint valid for {table_name}.{foreign_key_column}",
                    execution_time=execution_time
                )
        
        except Exception as e:
            return IntegrityTestResult(
                test_id=f"fk_constraint_{table_name}_{foreign_key_column}",
                rule_id="foreign_key_integrity",
                test_type=DataIntegrityTestType.FOREIGN_KEY_CHECK,
                status="failed",
                severity=IntegrityIssueLevel.CRITICAL,
                message=f"Error testing foreign key constraint: {str(e)}",
                execution_time=(datetime.now() - start_time).total_seconds()
            )
    
    def test_referential_consistency(self, source_id: str, parent_table: str,
                                   child_table: str, relationship_column: str) -> IntegrityTestResult:
        """Test bidirectional referential consistency"""
        start_time = datetime.now()
        
        try:
            # Check for records in child table without corresponding parent
            orphan_query = f"""
                SELECT COUNT(*) as orphan_count
                FROM {child_table} c
                WHERE NOT EXISTS (
                    SELECT 1 FROM {parent_table} p 
                    WHERE p.id = c.{relationship_column}
                )
            """
            
            # Check for parents with no children (might be informational)
            childless_query = f"""
                SELECT COUNT(*) as childless_count
                FROM {parent_table} p
                WHERE NOT EXISTS (
                    SELECT 1 FROM {child_table} c 
                    WHERE c.{relationship_column} = p.id
                )
            """
            
            orphan_result = self.db_connector.execute_query(source_id, orphan_query)
            childless_result = self.db_connector.execute_query(source_id, childless_query)
            
            orphan_count = orphan_result[0]['orphan_count'] if orphan_result else 0
            childless_count = childless_result[0]['childless_count'] if childless_result else 0
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            if orphan_count > 0:
                return IntegrityTestResult(
                    test_id=f"ref_consistency_{parent_table}_{child_table}",
                    rule_id="referential_consistency",
                    test_type=DataIntegrityTestType.REFERENTIAL_INTEGRITY,
                    status="failed",
                    severity=IntegrityIssueLevel.HIGH,
                    message=f"Referential inconsistency: {orphan_count} orphaned records in {child_table}",
                    details={
                        "orphan_count": orphan_count,
                        "childless_count": childless_count,
                        "parent_table": parent_table,
                        "child_table": child_table
                    },
                    affected_records=orphan_count,
                    execution_time=execution_time
                )
            else:
                status = "passed"
                message = f"Referential consistency maintained between {parent_table} and {child_table}"
                if childless_count > 0:
                    status = "warning"
                    message += f" ({childless_count} parents without children)"
                
                return IntegrityTestResult(
                    test_id=f"ref_consistency_{parent_table}_{child_table}",
                    rule_id="referential_consistency",
                    test_type=DataIntegrityTestType.REFERENTIAL_INTEGRITY,
                    status=status,
                    severity=IntegrityIssueLevel.INFORMATIONAL,
                    message=message,
                    details={"childless_count": childless_count},
                    execution_time=execution_time
                )
        
        except Exception as e:
            return IntegrityTestResult(
                test_id=f"ref_consistency_{parent_table}_{child_table}",
                rule_id="referential_consistency",
                test_type=DataIntegrityTestType.REFERENTIAL_INTEGRITY,
                status="failed",
                severity=IntegrityIssueLevel.CRITICAL,
                message=f"Error testing referential consistency: {str(e)}",
                execution_time=(datetime.now() - start_time).total_seconds()
            )


class DataValidationTester:
    """Tests data validation rules and constraints"""
    
    def __init__(self, db_connector: DatabaseConnector):
        self.db_connector = db_connector
    
    def test_null_constraints(self, source_id: str, table_name: str, 
                             non_null_columns: List[str]) -> List[IntegrityTestResult]:
        """Test NOT NULL constraints"""
        results = []
        
        for column in non_null_columns:
            start_time = datetime.now()
            
            try:
                query = f"""
                    SELECT COUNT(*) as null_count
                    FROM {table_name}
                    WHERE {column} IS NULL
                """
                
                result = self.db_connector.execute_query(source_id, query)
                null_count = result[0]['null_count'] if result else 0
                execution_time = (datetime.now() - start_time).total_seconds()
                
                if null_count > 0:
                    # Get sample of null records
                    sample_query = f"SELECT * FROM {table_name} WHERE {column} IS NULL LIMIT 5"
                    samples = self.db_connector.execute_query(source_id, sample_query)
                    
                    results.append(IntegrityTestResult(
                        test_id=f"null_constraint_{table_name}_{column}",
                        rule_id="null_constraint",
                        test_type=DataIntegrityTestType.CONSTRAINT_VALIDATION,
                        status="failed",
                        severity=IntegrityIssueLevel.HIGH,
                        message=f"NULL constraint violation in {table_name}.{column}",
                        details={"table": table_name, "column": column},
                        affected_records=null_count,
                        data_samples=samples,
                        execution_time=execution_time
                    ))
                else:
                    results.append(IntegrityTestResult(
                        test_id=f"null_constraint_{table_name}_{column}",
                        rule_id="null_constraint",
                        test_type=DataIntegrityTestType.CONSTRAINT_VALIDATION,
                        status="passed",
                        severity=IntegrityIssueLevel.INFORMATIONAL,
                        message=f"NULL constraint valid for {table_name}.{column}",
                        execution_time=execution_time
                    ))
            
            except Exception as e:
                results.append(IntegrityTestResult(
                    test_id=f"null_constraint_{table_name}_{column}",
                    rule_id="null_constraint",
                    test_type=DataIntegrityTestType.CONSTRAINT_VALIDATION,
                    status="failed",
                    severity=IntegrityIssueLevel.CRITICAL,
                    message=f"Error testing NULL constraint: {str(e)}",
                    execution_time=(datetime.now() - start_time).total_seconds()
                ))
        
        return results
    
    def test_data_type_integrity(self, source_id: str, table_name: str,
                                column_name: str, expected_type: str) -> IntegrityTestResult:
        """Test data type integrity"""
        start_time = datetime.now()
        
        try:
            # This is a simplified check - in practice would be more sophisticated
            if expected_type.lower() in ['int', 'integer', 'bigint']:
                query = f"""
                    SELECT COUNT(*) as invalid_count
                    FROM {table_name}
                    WHERE {column_name} IS NOT NULL
                    AND {column_name} NOT SIMILAR TO '^[+-]?[0-9]+$'
                """
            elif expected_type.lower() in ['float', 'decimal', 'numeric']:
                query = f"""
                    SELECT COUNT(*) as invalid_count
                    FROM {table_name}
                    WHERE {column_name} IS NOT NULL
                    AND {column_name} NOT SIMILAR TO '^[+-]?[0-9]*\\.?[0-9]+([eE][+-]?[0-9]+)?$'
                """
            elif expected_type.lower() in ['email']:
                query = f"""
                    SELECT COUNT(*) as invalid_count
                    FROM {table_name}
                    WHERE {column_name} IS NOT NULL
                    AND {column_name} NOT SIMILAR TO '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{{2,}}$'
                """
            else:
                # Generic string validation
                query = f"""
                    SELECT COUNT(*) as invalid_count
                    FROM {table_name}
                    WHERE {column_name} IS NOT NULL
                    AND LENGTH(TRIM({column_name})) = 0
                """
            
            result = self.db_connector.execute_query(source_id, query)
            invalid_count = result[0]['invalid_count'] if result else 0
            execution_time = (datetime.now() - start_time).total_seconds()
            
            if invalid_count > 0:
                # Get samples of invalid data
                sample_query = f"""
                    SELECT {column_name}, id 
                    FROM {table_name} 
                    WHERE {column_name} IS NOT NULL 
                    LIMIT 5
                """
                samples = self.db_connector.execute_query(source_id, sample_query)
                
                return IntegrityTestResult(
                    test_id=f"data_type_{table_name}_{column_name}",
                    rule_id="data_type_integrity",
                    test_type=DataIntegrityTestType.DATA_VALIDATION,
                    status="failed",
                    severity=IntegrityIssueLevel.MEDIUM,
                    message=f"Data type integrity issue in {table_name}.{column_name}",
                    details={
                        "table": table_name,
                        "column": column_name,
                        "expected_type": expected_type
                    },
                    affected_records=invalid_count,
                    data_samples=samples,
                    execution_time=execution_time
                )
            else:
                return IntegrityTestResult(
                    test_id=f"data_type_{table_name}_{column_name}",
                    rule_id="data_type_integrity",
                    test_type=DataIntegrityTestType.DATA_VALIDATION,
                    status="passed",
                    severity=IntegrityIssueLevel.INFORMATIONAL,
                    message=f"Data type integrity valid for {table_name}.{column_name}",
                    execution_time=execution_time
                )
        
        except Exception as e:
            return IntegrityTestResult(
                test_id=f"data_type_{table_name}_{column_name}",
                rule_id="data_type_integrity",
                test_type=DataIntegrityTestType.DATA_VALIDATION,
                status="failed",
                severity=IntegrityIssueLevel.CRITICAL,
                message=f"Error testing data type integrity: {str(e)}",
                execution_time=(datetime.now() - start_time).total_seconds()
            )
    
    def test_unique_constraints(self, source_id: str, table_name: str,
                              unique_columns: List[str]) -> List[IntegrityTestResult]:
        """Test unique constraints"""
        results = []
        
        for column in unique_columns:
            start_time = datetime.now()
            
            try:
                query = f"""
                    SELECT {column}, COUNT(*) as duplicate_count
                    FROM {table_name}
                    WHERE {column} IS NOT NULL
                    GROUP BY {column}
                    HAVING COUNT(*) > 1
                """
                
                duplicates = self.db_connector.execute_query(source_id, query)
                execution_time = (datetime.now() - start_time).total_seconds()
                
                if duplicates:
                    total_duplicates = sum(dup['duplicate_count'] for dup in duplicates)
                    
                    results.append(IntegrityTestResult(
                        test_id=f"unique_constraint_{table_name}_{column}",
                        rule_id="unique_constraint",
                        test_type=DataIntegrityTestType.CONSTRAINT_VALIDATION,
                        status="failed",
                        severity=IntegrityIssueLevel.HIGH,
                        message=f"Unique constraint violation in {table_name}.{column}",
                        details={
                            "table": table_name,
                            "column": column,
                            "unique_violations": len(duplicates)
                        },
                        affected_records=total_duplicates,
                        data_samples=duplicates[:5],
                        execution_time=execution_time
                    ))
                else:
                    results.append(IntegrityTestResult(
                        test_id=f"unique_constraint_{table_name}_{column}",
                        rule_id="unique_constraint",
                        test_type=DataIntegrityTestType.CONSTRAINT_VALIDATION,
                        status="passed",
                        severity=IntegrityIssueLevel.INFORMATIONAL,
                        message=f"Unique constraint valid for {table_name}.{column}",
                        execution_time=execution_time
                    ))
            
            except Exception as e:
                results.append(IntegrityTestResult(
                    test_id=f"unique_constraint_{table_name}_{column}",
                    rule_id="unique_constraint",
                    test_type=DataIntegrityTestType.CONSTRAINT_VALIDATION,
                    status="failed",
                    severity=IntegrityIssueLevel.CRITICAL,
                    message=f"Error testing unique constraint: {str(e)}",
                    execution_time=(datetime.now() - start_time).total_seconds()
                ))
        
        return results


class DataConsistencyTester:
    """Tests data consistency across sources and time"""
    
    def __init__(self, db_connector: DatabaseConnector):
        self.db_connector = db_connector
    
    def test_cross_source_consistency(self, source1_id: str, source2_id: str,
                                    table1: str, table2: str, key_column: str) -> IntegrityTestResult:
        """Test consistency between two data sources"""
        start_time = datetime.now()
        
        try:
            # Get record counts from both sources
            count_query1 = f"SELECT COUNT(*) as count FROM {table1}"
            count_query2 = f"SELECT COUNT(*) as count FROM {table2}"
            
            count1 = self.db_connector.execute_query(source1_id, count_query1)[0]['count']
            count2 = self.db_connector.execute_query(source2_id, count_query2)[0]['count']
            
            # Get checksums for comparison (simplified)
            checksum_query1 = f"SELECT {key_column} FROM {table1} ORDER BY {key_column}"
            checksum_query2 = f"SELECT {key_column} FROM {table2} ORDER BY {key_column}"
            
            records1 = self.db_connector.execute_query(source1_id, checksum_query1)
            records2 = self.db_connector.execute_query(source2_id, checksum_query2)
            
            keys1 = set(str(r[key_column]) for r in records1)
            keys2 = set(str(r[key_column]) for r in records2)
            
            missing_in_source2 = keys1 - keys2
            missing_in_source1 = keys2 - keys1
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            if missing_in_source1 or missing_in_source2:
                return IntegrityTestResult(
                    test_id=f"cross_source_consistency_{table1}_{table2}",
                    rule_id="cross_source_consistency",
                    test_type=DataIntegrityTestType.CONSISTENCY_CHECK,
                    status="failed",
                    severity=IntegrityIssueLevel.HIGH,
                    message=f"Data inconsistency between {source1_id}.{table1} and {source2_id}.{table2}",
                    details={
                        "source1_count": count1,
                        "source2_count": count2,
                        "missing_in_source1": len(missing_in_source1),
                        "missing_in_source2": len(missing_in_source2),
                        "sample_missing_source1": list(missing_in_source1)[:5],
                        "sample_missing_source2": list(missing_in_source2)[:5]
                    },
                    affected_records=len(missing_in_source1) + len(missing_in_source2),
                    execution_time=execution_time
                )
            else:
                return IntegrityTestResult(
                    test_id=f"cross_source_consistency_{table1}_{table2}",
                    rule_id="cross_source_consistency",
                    test_type=DataIntegrityTestType.CONSISTENCY_CHECK,
                    status="passed",
                    severity=IntegrityIssueLevel.INFORMATIONAL,
                    message=f"Data consistent between {source1_id}.{table1} and {source2_id}.{table2}",
                    details={"record_count": count1},
                    execution_time=execution_time
                )
        
        except Exception as e:
            return IntegrityTestResult(
                test_id=f"cross_source_consistency_{table1}_{table2}",
                rule_id="cross_source_consistency",
                test_type=DataIntegrityTestType.CONSISTENCY_CHECK,
                status="failed",
                severity=IntegrityIssueLevel.CRITICAL,
                message=f"Error testing cross-source consistency: {str(e)}",
                execution_time=(datetime.now() - start_time).total_seconds()
            )
    
    def test_temporal_consistency(self, source_id: str, table_name: str,
                                timestamp_column: str, tolerance_minutes: int = 5) -> IntegrityTestResult:
        """Test temporal data consistency"""
        start_time = datetime.now()
        
        try:
            # Check for future timestamps
            future_query = f"""
                SELECT COUNT(*) as future_count
                FROM {table_name}
                WHERE {timestamp_column} > NOW()
            """
            
            # Check for timestamps that are too old (potential data corruption)
            old_threshold = datetime.now() - timedelta(days=365*10)  # 10 years
            old_query = f"""
                SELECT COUNT(*) as old_count
                FROM {table_name}
                WHERE {timestamp_column} < '{old_threshold.isoformat()}'
            """
            
            # Check for inconsistent timestamp ordering
            ordering_query = f"""
                SELECT COUNT(*) as ordering_issues
                FROM {table_name} t1
                JOIN {table_name} t2 ON t1.id = t2.id - 1
                WHERE t1.{timestamp_column} > t2.{timestamp_column}
            """
            
            future_result = self.db_connector.execute_query(source_id, future_query)
            old_result = self.db_connector.execute_query(source_id, old_query)
            
            future_count = future_result[0]['future_count'] if future_result else 0
            old_count = old_result[0]['old_count'] if old_result else 0
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            issues = []
            if future_count > 0:
                issues.append(f"{future_count} future timestamps")
            if old_count > 0:
                issues.append(f"{old_count} very old timestamps")
            
            if issues:
                return IntegrityTestResult(
                    test_id=f"temporal_consistency_{table_name}",
                    rule_id="temporal_consistency",
                    test_type=DataIntegrityTestType.CONSISTENCY_CHECK,
                    status="failed",
                    severity=IntegrityIssueLevel.MEDIUM,
                    message=f"Temporal inconsistencies in {table_name}.{timestamp_column}: {', '.join(issues)}",
                    details={
                        "future_timestamps": future_count,
                        "old_timestamps": old_count
                    },
                    affected_records=future_count + old_count,
                    execution_time=execution_time
                )
            else:
                return IntegrityTestResult(
                    test_id=f"temporal_consistency_{table_name}",
                    rule_id="temporal_consistency",
                    test_type=DataIntegrityTestType.CONSISTENCY_CHECK,
                    status="passed",
                    severity=IntegrityIssueLevel.INFORMATIONAL,
                    message=f"Temporal consistency valid for {table_name}.{timestamp_column}",
                    execution_time=execution_time
                )
        
        except Exception as e:
            return IntegrityTestResult(
                test_id=f"temporal_consistency_{table_name}",
                rule_id="temporal_consistency",
                test_type=DataIntegrityTestType.CONSISTENCY_CHECK,
                status="failed",
                severity=IntegrityIssueLevel.CRITICAL,
                message=f"Error testing temporal consistency: {str(e)}",
                execution_time=(datetime.now() - start_time).total_seconds()
            )


class DataCorruptionDetector:
    """Detects data corruption and anomalies"""
    
    def __init__(self, db_connector: DatabaseConnector):
        self.db_connector = db_connector
    
    def test_data_corruption(self, source_id: str, table_name: str,
                           columns: List[str]) -> List[IntegrityTestResult]:
        """Test for data corruption indicators"""
        results = []
        
        for column in columns:
            start_time = datetime.now()
            
            try:
                # Check for unusual characters that might indicate corruption
                corruption_query = f"""
                    SELECT COUNT(*) as corrupt_count
                    FROM {table_name}
                    WHERE {column} IS NOT NULL
                    AND (
                        {column} LIKE '%\\x00%' OR  -- null bytes
                        {column} LIKE '%\\x01%' OR  -- control characters
                        {column} LIKE '%\\x02%' OR
                        {column} LIKE '%\\x03%' OR
                        {column} LIKE '%\\x04%' OR
                        {column} LIKE '%\\x05%' OR
                        {column} LIKE '%\\x06%' OR
                        {column} LIKE '%\\x07%' OR
                        {column} LIKE '%\\x08%' OR
                        {column} LIKE '%\\x0B%' OR
                        {column} LIKE '%\\x0C%' OR
                        {column} LIKE '%\\x0E%' OR
                        {column} LIKE '%\\x0F%'
                    )
                """
                
                result = self.db_connector.execute_query(source_id, corruption_query)
                corrupt_count = result[0]['corrupt_count'] if result else 0
                
                # Check for encoding issues
                encoding_query = f"""
                    SELECT COUNT(*) as encoding_issues
                    FROM {table_name}
                    WHERE {column} IS NOT NULL
                    AND {column} ~ '[\\x80-\\xFF]'  -- Non-ASCII characters that might indicate encoding issues
                """
                
                try:
                    encoding_result = self.db_connector.execute_query(source_id, encoding_query)
                    encoding_issues = encoding_result[0]['encoding_issues'] if encoding_result else 0
                except:
                    encoding_issues = 0  # Query might not work on all databases
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                total_issues = corrupt_count + encoding_issues
                
                if total_issues > 0:
                    # Get samples of corrupted data
                    sample_query = f"""
                        SELECT {column}, id
                        FROM {table_name}
                        WHERE {column} IS NOT NULL
                        AND LENGTH({column}) > 0
                        LIMIT 5
                    """
                    samples = self.db_connector.execute_query(source_id, sample_query)
                    
                    results.append(IntegrityTestResult(
                        test_id=f"corruption_{table_name}_{column}",
                        rule_id="data_corruption",
                        test_type=DataIntegrityTestType.CORRUPTION_DETECTION,
                        status="failed",
                        severity=IntegrityIssueLevel.CRITICAL,
                        message=f"Data corruption detected in {table_name}.{column}",
                        details={
                            "corrupt_records": corrupt_count,
                            "encoding_issues": encoding_issues,
                            "table": table_name,
                            "column": column
                        },
                        affected_records=total_issues,
                        data_samples=samples,
                        execution_time=execution_time
                    ))
                else:
                    results.append(IntegrityTestResult(
                        test_id=f"corruption_{table_name}_{column}",
                        rule_id="data_corruption",
                        test_type=DataIntegrityTestType.CORRUPTION_DETECTION,
                        status="passed",
                        severity=IntegrityIssueLevel.INFORMATIONAL,
                        message=f"No corruption detected in {table_name}.{column}",
                        execution_time=execution_time
                    ))
            
            except Exception as e:
                results.append(IntegrityTestResult(
                    test_id=f"corruption_{table_name}_{column}",
                    rule_id="data_corruption",
                    test_type=DataIntegrityTestType.CORRUPTION_DETECTION,
                    status="failed",
                    severity=IntegrityIssueLevel.CRITICAL,
                    message=f"Error testing data corruption: {str(e)}",
                    execution_time=(datetime.now() - start_time).total_seconds()
                ))
        
        return results
    
    def test_statistical_anomalies(self, source_id: str, table_name: str,
                                  numeric_column: str) -> IntegrityTestResult:
        """Test for statistical anomalies in numeric data"""
        start_time = datetime.now()
        
        try:
            # Get basic statistics
            stats_query = f"""
                SELECT 
                    COUNT(*) as record_count,
                    MIN({numeric_column}) as min_value,
                    MAX({numeric_column}) as max_value,
                    AVG({numeric_column}) as avg_value,
                    STDDEV({numeric_column}) as std_dev
                FROM {table_name}
                WHERE {numeric_column} IS NOT NULL
            """
            
            stats = self.db_connector.execute_query(source_id, stats_query)
            if not stats:
                return IntegrityTestResult(
                    test_id=f"stats_anomaly_{table_name}_{numeric_column}",
                    rule_id="statistical_anomalies",
                    test_type=DataIntegrityTestType.CORRUPTION_DETECTION,
                    status="failed",
                    severity=IntegrityIssueLevel.CRITICAL,
                    message="No statistical data available",
                    execution_time=(datetime.now() - start_time).total_seconds()
                )
            
            stat = stats[0]
            record_count = stat['record_count']
            min_val = float(stat['min_value']) if stat['min_value'] is not None else 0
            max_val = float(stat['max_value']) if stat['max_value'] is not None else 0
            avg_val = float(stat['avg_value']) if stat['avg_value'] is not None else 0
            std_dev = float(stat['std_dev']) if stat['std_dev'] is not None else 0
            
            anomalies = []
            
            # Check for extreme outliers (more than 3 standard deviations)
            if std_dev > 0:
                outlier_query = f"""
                    SELECT COUNT(*) as outlier_count
                    FROM {table_name}
                    WHERE {numeric_column} IS NOT NULL
                    AND (
                        {numeric_column} > {avg_val + (3 * std_dev)} OR
                        {numeric_column} < {avg_val - (3 * std_dev)}
                    )
                """
                
                outlier_result = self.db_connector.execute_query(source_id, outlier_query)
                outlier_count = outlier_result[0]['outlier_count'] if outlier_result else 0
                
                if outlier_count > record_count * 0.05:  # More than 5% outliers
                    anomalies.append(f"{outlier_count} extreme outliers")
            
            # Check for suspicious patterns
            if min_val == max_val and record_count > 1:
                anomalies.append("All values are identical")
            
            if max_val > avg_val * 1000:  # Suspiciously large maximum
                anomalies.append("Suspiciously large maximum value")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            if anomalies:
                return IntegrityTestResult(
                    test_id=f"stats_anomaly_{table_name}_{numeric_column}",
                    rule_id="statistical_anomalies",
                    test_type=DataIntegrityTestType.CORRUPTION_DETECTION,
                    status="failed",
                    severity=IntegrityIssueLevel.MEDIUM,
                    message=f"Statistical anomalies in {table_name}.{numeric_column}: {', '.join(anomalies)}",
                    details={
                        "min_value": min_val,
                        "max_value": max_val,
                        "avg_value": avg_val,
                        "std_dev": std_dev,
                        "record_count": record_count,
                        "anomalies": anomalies
                    },
                    execution_time=execution_time
                )
            else:
                return IntegrityTestResult(
                    test_id=f"stats_anomaly_{table_name}_{numeric_column}",
                    rule_id="statistical_anomalies",
                    test_type=DataIntegrityTestType.CORRUPTION_DETECTION,
                    status="passed",
                    severity=IntegrityIssueLevel.INFORMATIONAL,
                    message=f"No statistical anomalies in {table_name}.{numeric_column}",
                    details={
                        "min_value": min_val,
                        "max_value": max_val,
                        "avg_value": avg_val,
                        "record_count": record_count
                    },
                    execution_time=execution_time
                )
        
        except Exception as e:
            return IntegrityTestResult(
                test_id=f"stats_anomaly_{table_name}_{numeric_column}",
                rule_id="statistical_anomalies",
                test_type=DataIntegrityTestType.CORRUPTION_DETECTION,
                status="failed",
                severity=IntegrityIssueLevel.CRITICAL,
                message=f"Error testing statistical anomalies: {str(e)}",
                execution_time=(datetime.now() - start_time).total_seconds()
            )


class DataIntegrityEngine:
    """Main data integrity testing engine"""
    
    def __init__(self):
        self.db_connector = DatabaseConnector()
        self.ref_integrity_tester = ReferentialIntegrityTester(self.db_connector)
        self.validation_tester = DataValidationTester(self.db_connector)
        self.consistency_tester = DataConsistencyTester(self.db_connector)
        self.corruption_detector = DataCorruptionDetector(self.db_connector)
        self.rules: List[DataIntegrityRule] = []
        self.test_results: List[IntegrityTestResult] = []
    
    def add_data_source(self, source_id: str, source_type: DataSourceType, 
                       connection_string: str, **kwargs):
        """Add a data source for testing"""
        self.db_connector.add_connection(source_id, source_type, connection_string, **kwargs)
    
    def add_integrity_rule(self, rule: DataIntegrityRule):
        """Add a data integrity rule"""
        self.rules.append(rule)
    
    def create_default_rules(self, source_id: str):
        """Create default integrity rules for a data source"""
        # These would be created based on database schema inspection
        # For demo purposes, creating some common rules
        
        default_rules = [
            DataIntegrityRule(
                rule_id="users_email_unique",
                name="Users Email Unique",
                description="Email addresses should be unique in users table",
                test_type=DataIntegrityTestType.CONSTRAINT_VALIDATION,
                data_source=source_id,
                table_name="users",
                column_name="email",
                severity=IntegrityIssueLevel.HIGH
            ),
            DataIntegrityRule(
                rule_id="users_created_at_not_null",
                name="Users Created At Not Null",
                description="Created timestamp should not be null",
                test_type=DataIntegrityTestType.CONSTRAINT_VALIDATION,
                data_source=source_id,
                table_name="users",
                column_name="created_at",
                severity=IntegrityIssueLevel.HIGH
            ),
            DataIntegrityRule(
                rule_id="posts_user_id_foreign_key",
                name="Posts User ID Foreign Key",
                description="Post user_id should reference existing user",
                test_type=DataIntegrityTestType.FOREIGN_KEY_CHECK,
                data_source=source_id,
                table_name="posts",
                column_name="user_id",
                severity=IntegrityIssueLevel.HIGH
            )
        ]
        
        for rule in default_rules:
            self.add_integrity_rule(rule)
    
    async def run_comprehensive_test(self, source_ids: List[str]) -> DataIntegrityReport:
        """Run comprehensive data integrity test"""
        session_id = f"integrity_test_{int(datetime.now().timestamp())}"
        
        report = DataIntegrityReport(
            report_id=f"report_{session_id}",
            test_session_id=session_id,
            start_time=datetime.now(),
            data_sources_tested=source_ids
        )
        
        print(f"Starting comprehensive data integrity test...")
        print(f"Testing {len(source_ids)} data sources with {len(self.rules)} rules")
        
        try:
            # Run all integrity rules
            for rule in self.rules:
                if rule.data_source in source_ids:
                    result = await self._execute_rule(rule)
                    if result:
                        self.test_results.append(result)
                        report.results.append(result)
            
            # Run additional automated tests
            for source_id in source_ids:
                additional_results = await self._run_automated_tests(source_id)
                self.test_results.extend(additional_results)
                report.results.extend(additional_results)
            
            # Compile report statistics
            report.total_tests = len(report.results)
            report.passed_tests = len([r for r in report.results if r.status == "passed"])
            report.failed_tests = len([r for r in report.results if r.status == "failed"])
            report.warnings = len([r for r in report.results if r.status == "warning"])
            
            # Generate summary statistics
            report.summary_statistics = self._generate_summary_statistics(report.results)
            
            # Generate recommendations
            report.recommendations = self._generate_recommendations(report.results)
            
            report.end_time = datetime.now()
            
            print(f"Data integrity test completed:")
            print(f"  Total tests: {report.total_tests}")
            print(f"  Passed: {report.passed_tests}")
            print(f"  Failed: {report.failed_tests}")
            print(f"  Warnings: {report.warnings}")
            
        except Exception as e:
            logging.error(f"Error during comprehensive test: {e}")
        
        return report
    
    async def _execute_rule(self, rule: DataIntegrityRule) -> Optional[IntegrityTestResult]:
        """Execute a specific integrity rule"""
        try:
            if rule.test_type == DataIntegrityTestType.FOREIGN_KEY_CHECK:
                # Extract referenced table from rule (simplified)
                if rule.table_name and rule.column_name:
                    referenced_table = "users"  # Simplified - would parse from rule
                    referenced_column = "id"
                    
                    return self.ref_integrity_tester.test_foreign_key_constraints(
                        rule.data_source, rule.table_name, rule.column_name,
                        referenced_table, referenced_column
                    )
            
            elif rule.test_type == DataIntegrityTestType.CONSTRAINT_VALIDATION:
                if rule.column_name:
                    if "unique" in rule.name.lower():
                        results = self.validation_tester.test_unique_constraints(
                            rule.data_source, rule.table_name, [rule.column_name]
                        )
                        return results[0] if results else None
                    elif "not_null" in rule.rule_id.lower():
                        results = self.validation_tester.test_null_constraints(
                            rule.data_source, rule.table_name, [rule.column_name]
                        )
                        return results[0] if results else None
            
            elif rule.test_type == DataIntegrityTestType.CORRUPTION_DETECTION:
                if rule.table_name and rule.column_name:
                    results = self.corruption_detector.test_data_corruption(
                        rule.data_source, rule.table_name, [rule.column_name]
                    )
                    return results[0] if results else None
            
        except Exception as e:
            logging.error(f"Error executing rule {rule.rule_id}: {e}")
            return IntegrityTestResult(
                test_id=rule.rule_id,
                rule_id=rule.rule_id,
                test_type=rule.test_type,
                status="failed",
                severity=IntegrityIssueLevel.CRITICAL,
                message=f"Rule execution failed: {str(e)}"
            )
        
        return None
    
    async def _run_automated_tests(self, source_id: str) -> List[IntegrityTestResult]:
        """Run automated tests based on database schema"""
        results = []
        
        try:
            # Get table list (simplified - would inspect actual schema)
            common_tables = ["users", "posts", "comments", "sessions", "logs"]
            
            for table_name in common_tables:
                try:
                    table_info = self.db_connector.get_table_info(source_id, table_name)
                    if table_info and table_info.get('row_count', 0) > 0:
                        
                        # Test for common integrity issues
                        if table_name == "users":
                            # Test email format
                            email_result = self.validation_tester.test_data_type_integrity(
                                source_id, table_name, "email", "email"
                            )
                            results.append(email_result)
                            
                            # Test for temporal consistency on created_at
                            temporal_result = self.consistency_tester.test_temporal_consistency(
                                source_id, table_name, "created_at"
                            )
                            results.append(temporal_result)
                        
                        # Test for data corruption on text columns
                        text_columns = ["name", "email", "title", "content", "description"]
                        for col in text_columns:
                            corruption_results = self.corruption_detector.test_data_corruption(
                                source_id, table_name, [col]
                            )
                            results.extend(corruption_results)
                
                except Exception as e:
                    logging.debug(f"Error testing table {table_name}: {e}")
                    continue
        
        except Exception as e:
            logging.error(f"Error in automated tests: {e}")
        
        return results
    
    def _generate_summary_statistics(self, results: List[IntegrityTestResult]) -> Dict[str, Any]:
        """Generate summary statistics from test results"""
        if not results:
            return {}
        
        severity_counts = {}
        test_type_counts = {}
        
        for result in results:
            # Count by severity
            severity = result.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            # Count by test type
            test_type = result.test_type.value
            test_type_counts[test_type] = test_type_counts.get(test_type, 0) + 1
        
        total_affected_records = sum(result.affected_records for result in results)
        avg_execution_time = sum(result.execution_time for result in results) / len(results)
        
        return {
            "total_results": len(results),
            "severity_breakdown": severity_counts,
            "test_type_breakdown": test_type_counts,
            "total_affected_records": total_affected_records,
            "average_execution_time": avg_execution_time,
            "critical_issues": len([r for r in results if r.severity == IntegrityIssueLevel.CRITICAL]),
            "high_issues": len([r for r in results if r.severity == IntegrityIssueLevel.HIGH]),
            "success_rate": (len([r for r in results if r.status == "passed"]) / len(results)) * 100
        }
    
    def _generate_recommendations(self, results: List[IntegrityTestResult]) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        critical_issues = [r for r in results if r.severity == IntegrityIssueLevel.CRITICAL]
        high_issues = [r for r in results if r.severity == IntegrityIssueLevel.HIGH]
        
        if critical_issues:
            recommendations.append(f"URGENT: Address {len(critical_issues)} critical data integrity issues immediately")
        
        if high_issues:
            recommendations.append(f"High priority: Fix {len(high_issues)} high-severity integrity violations")
        
        # Specific recommendations based on common issues
        corruption_issues = [r for r in results if r.test_type == DataIntegrityTestType.CORRUPTION_DETECTION and r.status == "failed"]
        if corruption_issues:
            recommendations.append("Data corruption detected - investigate backup and recovery procedures")
        
        fk_issues = [r for r in results if r.test_type == DataIntegrityTestType.FOREIGN_KEY_CHECK and r.status == "failed"]
        if fk_issues:
            recommendations.append("Foreign key constraint violations found - review data insertion processes")
        
        consistency_issues = [r for r in results if r.test_type == DataIntegrityTestType.CONSISTENCY_CHECK and r.status == "failed"]
        if consistency_issues:
            recommendations.append("Cross-source data inconsistencies found - review data synchronization processes")
        
        # General recommendations
        recommendations.extend([
            "Implement regular automated data integrity monitoring",
            "Set up alerting for critical data integrity violations",
            "Review and strengthen data validation at application level",
            "Consider implementing database constraints to prevent future violations",
            "Establish data quality metrics and monitoring dashboards"
        ])
        
        return recommendations[:10]  # Limit to top 10 recommendations
    
    def generate_html_report(self, report: DataIntegrityReport) -> str:
        """Generate HTML report"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Data Integrity Report - {report.report_id}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background: #f4f4f4; padding: 20px; border-radius: 5px; }}
                .summary {{ display: flex; justify-content: space-around; margin: 20px 0; }}
                .metric {{ text-align: center; }}
                .metric h3 {{ margin: 0; color: #333; }}
                .metric .value {{ font-size: 2em; font-weight: bold; }}
                .critical {{ color: #d32f2f; }}
                .high {{ color: #f57c00; }}
                .medium {{ color: #fbc02d; }}
                .low {{ color: #388e3c; }}
                .passed {{ color: #4caf50; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .failed {{ background-color: #ffebee; }}
                .warning {{ background-color: #fff3e0; }}
                .passed {{ background-color: #e8f5e8; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Data Integrity Report</h1>
                <p><strong>Report ID:</strong> {report.report_id}</p>
                <p><strong>Test Period:</strong> {report.start_time} - {report.end_time}</p>
                <p><strong>Data Sources:</strong> {', '.join(report.data_sources_tested)}</p>
            </div>
            
            <div class="summary">
                <div class="metric">
                    <h3>Total Tests</h3>
                    <div class="value">{report.total_tests}</div>
                </div>
                <div class="metric">
                    <h3>Passed</h3>
                    <div class="value passed">{report.passed_tests}</div>
                </div>
                <div class="metric">
                    <h3>Failed</h3>
                    <div class="value critical">{report.failed_tests}</div>
                </div>
                <div class="metric">
                    <h3>Warnings</h3>
                    <div class="value medium">{report.warnings}</div>
                </div>
            </div>
            
            <h2>Test Results</h2>
            <table>
                <thead>
                    <tr>
                        <th>Test ID</th>
                        <th>Type</th>
                        <th>Status</th>
                        <th>Severity</th>
                        <th>Message</th>
                        <th>Affected Records</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for result in report.results:
            status_class = result.status
            severity_class = result.severity.value
            
            html += f"""
                    <tr class="{status_class}">
                        <td>{result.test_id}</td>
                        <td>{result.test_type.value}</td>
                        <td>{result.status.upper()}</td>
                        <td class="{severity_class}">{result.severity.value.upper()}</td>
                        <td>{result.message}</td>
                        <td>{result.affected_records}</td>
                    </tr>
            """
        
        html += """
                </tbody>
            </table>
            
            <h2>Recommendations</h2>
            <ul>
        """
        
        for rec in report.recommendations:
            html += f"<li>{rec}</li>"
        
        html += """
            </ul>
        </body>
        </html>
        """
        
        return html
    
    def cleanup(self):
        """Clean up database connections"""
        self.db_connector.close_all()


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def run_data_integrity_tests():
        # Initialize data integrity engine
        engine = DataIntegrityEngine()
        
        try:
            # Add data sources
            engine.add_data_source("main_db", DataSourceType.SQLITE, "test_data.db")
            engine.add_data_source("backup_db", DataSourceType.SQLITE, "backup_data.db")
            
            # Create default rules
            engine.create_default_rules("main_db")
            
            # Add custom rules
            custom_rule = DataIntegrityRule(
                rule_id="custom_email_validation",
                name="Email Validation",
                description="Validate email format in users table",
                test_type=DataIntegrityTestType.DATA_VALIDATION,
                data_source="main_db",
                table_name="users",
                column_name="email",
                severity=IntegrityIssueLevel.HIGH
            )
            engine.add_integrity_rule(custom_rule)
            
            print("Starting data integrity tests...")
            
            # Run comprehensive test
            report = await engine.run_comprehensive_test(["main_db", "backup_db"])
            
            # Generate and save HTML report
            html_report = engine.generate_html_report(report)
            report_file = Path(f"data_integrity_report_{int(datetime.now().timestamp())}.html")
            report_file.write_text(html_report)
            
            print(f"\nData Integrity Test Summary:")
            print(f"Total Tests: {report.total_tests}")
            print(f"Success Rate: {report.summary_statistics.get('success_rate', 0):.1f}%")
            print(f"Critical Issues: {report.summary_statistics.get('critical_issues', 0)}")
            print(f"High Issues: {report.summary_statistics.get('high_issues', 0)}")
            print(f"HTML Report saved to: {report_file}")
            
        finally:
            engine.cleanup()
    
    # Run the tests
    asyncio.run(run_data_integrity_tests())