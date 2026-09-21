#!/usr/bin/env python3

import sqlite3
import os
import hashlib
import json
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple, Set
from enum import Enum
import logging
import glob
from pathlib import Path
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntegrityStatus(Enum):
    PASS = "pass"
    WARNING = "warning"
    CRITICAL = "critical"
    ERROR = "error"

class CheckType(Enum):
    SCHEMA = "schema"
    DATA = "data"
    INDEX = "index"
    FOREIGN_KEY = "foreign_key"
    CONSTRAINT = "constraint"
    PERFORMANCE = "performance"
    CORRUPTION = "corruption"
    SIZE = "size"

@dataclass
class DatabaseInfo:
    path: str
    name: str
    size_bytes: int
    table_count: int
    total_rows: int
    created_time: Optional[datetime] = None
    modified_time: Optional[datetime] = None

@dataclass
class IntegrityIssue:
    database: str
    table: str
    check_type: CheckType
    status: IntegrityStatus
    message: str
    details: Dict[str, Any] = None
    suggestion: str = ""
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}

@dataclass
class TableAnalysis:
    name: str
    row_count: int
    column_count: int
    size_bytes: int
    has_primary_key: bool
    has_indexes: bool
    foreign_keys: List[str]
    constraints: List[str]
    last_analyzed: datetime

@dataclass
class DatabaseIntegrityReport:
    databases_checked: int
    total_issues: int
    critical_issues: int
    warnings: int
    errors: int
    passed_checks: int
    total_size_mb: float
    check_duration: float
    issues: List[IntegrityIssue]
    database_info: List[DatabaseInfo]
    timestamp: datetime

class DatabaseIntegrityChecker:
    def __init__(self, audit_db_path: str = "audit_database_integrity.db"):
        self.audit_db_path = audit_db_path
        self.issues: List[IntegrityIssue] = []
        self.database_info: List[DatabaseInfo] = []
        self.init_audit_database()
        
    def init_audit_database(self):
        """Initialize audit database for storing integrity check results"""
        conn = sqlite3.connect(self.audit_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS integrity_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            databases_checked INTEGER NOT NULL,
            total_issues INTEGER NOT NULL,
            critical_issues INTEGER NOT NULL,
            warnings INTEGER NOT NULL,
            errors INTEGER NOT NULL,
            passed_checks INTEGER NOT NULL,
            total_size_mb REAL NOT NULL,
            check_duration REAL NOT NULL,
            timestamp DATETIME NOT NULL
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS integrity_issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER,
            database_name TEXT NOT NULL,
            table_name TEXT NOT NULL,
            check_type TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT NOT NULL,
            details TEXT,
            suggestion TEXT,
            timestamp DATETIME NOT NULL,
            FOREIGN KEY (report_id) REFERENCES integrity_reports (id)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS database_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            database_path TEXT NOT NULL,
            database_name TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            table_count INTEGER NOT NULL,
            total_rows INTEGER NOT NULL,
            checksum TEXT,
            timestamp DATETIME NOT NULL
        )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_integrity_issues_timestamp ON integrity_issues(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_database_snapshots_name ON database_snapshots(database_name)')
        
        conn.commit()
        conn.close()

    def find_database_files(self, root_path: str = "/home/activeloguser/activelog") -> List[str]:
        """Find all SQLite database files in the ActiveLog directory"""
        db_files = []
        
        # Common SQLite file extensions
        patterns = [
            "*.db",
            "*.sqlite",
            "*.sqlite3",
            "*.db3"
        ]
        
        for pattern in patterns:
            for file_path in glob.glob(f"{root_path}/**/{pattern}", recursive=True):
                # Verify it's actually a SQLite database
                if self.is_sqlite_database(file_path):
                    db_files.append(file_path)
        
        return sorted(set(db_files))

    def is_sqlite_database(self, file_path: str) -> bool:
        """Check if a file is a valid SQLite database"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(16)
                return header.startswith(b'SQLite format 3\x00')
        except:
            return False

    def get_database_info(self, db_path: str) -> DatabaseInfo:
        """Get basic information about a database"""
        try:
            stat_info = os.stat(db_path)
            size_bytes = stat_info.st_size
            modified_time = datetime.fromtimestamp(stat_info.st_mtime)
            created_time = datetime.fromtimestamp(stat_info.st_ctime)
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get table count
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            
            # Get total row count
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            total_rows = 0
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                    total_rows += cursor.fetchone()[0]
                except:
                    continue
            
            conn.close()
            
            return DatabaseInfo(
                path=db_path,
                name=os.path.basename(db_path),
                size_bytes=size_bytes,
                table_count=table_count,
                total_rows=total_rows,
                created_time=created_time,
                modified_time=modified_time
            )
            
        except Exception as e:
            logger.error(f"Failed to get database info for {db_path}: {e}")
            return DatabaseInfo(
                path=db_path,
                name=os.path.basename(db_path),
                size_bytes=0,
                table_count=0,
                total_rows=0
            )

    def check_database_corruption(self, db_path: str) -> List[IntegrityIssue]:
        """Check for database corruption using PRAGMA integrity_check"""
        issues = []
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Run integrity check
            cursor.execute("PRAGMA integrity_check")
            results = cursor.fetchall()
            
            if len(results) == 1 and results[0][0] == "ok":
                # Database is clean
                pass
            else:
                # Found corruption
                for result in results:
                    issues.append(IntegrityIssue(
                        database=os.path.basename(db_path),
                        table="*",
                        check_type=CheckType.CORRUPTION,
                        status=IntegrityStatus.CRITICAL,
                        message=f"Database corruption detected: {result[0]}",
                        suggestion="Run VACUUM command or restore from backup"
                    ))
            
            # Check foreign key constraints
            cursor.execute("PRAGMA foreign_key_check")
            fk_violations = cursor.fetchall()
            
            for violation in fk_violations:
                issues.append(IntegrityIssue(
                    database=os.path.basename(db_path),
                    table=violation[0],
                    check_type=CheckType.FOREIGN_KEY,
                    status=IntegrityStatus.CRITICAL,
                    message=f"Foreign key violation in row {violation[1]}: {violation[2]} -> {violation[3]}",
                    details={"rowid": violation[1], "parent": violation[2], "fkid": violation[3]},
                    suggestion="Fix data inconsistencies or update foreign key constraints"
                ))
            
            conn.close()
            
        except Exception as e:
            issues.append(IntegrityIssue(
                database=os.path.basename(db_path),
                table="*",
                check_type=CheckType.CORRUPTION,
                status=IntegrityStatus.ERROR,
                message=f"Failed to check corruption: {str(e)}",
                suggestion="Check database file permissions and integrity"
            ))
            
        return issues

    def analyze_table_structure(self, db_path: str) -> List[IntegrityIssue]:
        """Analyze table structures for potential issues"""
        issues = []
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            for table_name in tables:
                if table_name == 'sqlite_sequence':
                    continue
                    
                # Check table structure
                cursor.execute(f"PRAGMA table_info(`{table_name}`)")
                columns = cursor.fetchall()
                
                has_primary_key = any(col[5] for col in columns)  # col[5] is pk flag
                
                if not has_primary_key:
                    issues.append(IntegrityIssue(
                        database=os.path.basename(db_path),
                        table=table_name,
                        check_type=CheckType.SCHEMA,
                        status=IntegrityStatus.WARNING,
                        message="Table has no primary key",
                        details={"column_count": len(columns)},
                        suggestion="Consider adding a primary key for better performance"
                    ))
                
                # Check for indexes
                cursor.execute(f"PRAGMA index_list(`{table_name}`)")
                indexes = cursor.fetchall()
                
                # Get row count for performance checks
                cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                row_count = cursor.fetchone()[0]
                
                if row_count > 1000 and len(indexes) == 0:
                    issues.append(IntegrityIssue(
                        database=os.path.basename(db_path),
                        table=table_name,
                        check_type=CheckType.PERFORMANCE,
                        status=IntegrityStatus.WARNING,
                        message=f"Large table ({row_count} rows) has no indexes",
                        details={"row_count": row_count, "index_count": len(indexes)},
                        suggestion="Consider adding indexes on frequently queried columns"
                    ))
                
                # Check for unused columns (columns with all NULL values)
                if row_count > 0:
                    for col in columns:
                        col_name = col[1]
                        try:
                            cursor.execute(f"SELECT COUNT(*) FROM `{table_name}` WHERE `{col_name}` IS NOT NULL")
                            non_null_count = cursor.fetchone()[0]
                            
                            if non_null_count == 0:
                                issues.append(IntegrityIssue(
                                    database=os.path.basename(db_path),
                                    table=table_name,
                                    check_type=CheckType.DATA,
                                    status=IntegrityStatus.WARNING,
                                    message=f"Column '{col_name}' contains only NULL values",
                                    details={"total_rows": row_count, "non_null_rows": non_null_count},
                                    suggestion="Consider removing unused columns to optimize storage"
                                ))
                        except:
                            continue
            
            conn.close()
            
        except Exception as e:
            issues.append(IntegrityIssue(
                database=os.path.basename(db_path),
                table="*",
                check_type=CheckType.CORRUPTION,
                status=IntegrityStatus.ERROR,
                message=f"Failed to analyze table structure: {str(e)}",
                suggestion="Check database accessibility and permissions"
            ))
            
        return issues

    def check_database_performance(self, db_path: str) -> List[IntegrityIssue]:
        """Check database performance characteristics"""
        issues = []
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check database page size
            cursor.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            
            if page_size < 4096:
                issues.append(IntegrityIssue(
                    database=os.path.basename(db_path),
                    table="*",
                    check_type=CheckType.PERFORMANCE,
                    status=IntegrityStatus.WARNING,
                    message=f"Small page size ({page_size} bytes) may impact performance",
                    details={"current_page_size": page_size, "recommended_page_size": 4096},
                    suggestion="Consider using PRAGMA page_size=4096 for better performance"
                ))
            
            # Check for fragmentation
            cursor.execute("PRAGMA freelist_count")
            freelist_count = cursor.fetchone()[0]
            
            cursor.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            
            if page_count > 0:
                fragmentation_ratio = freelist_count / page_count
                if fragmentation_ratio > 0.1:  # More than 10% fragmentation
                    issues.append(IntegrityIssue(
                        database=os.path.basename(db_path),
                        table="*",
                        check_type=CheckType.PERFORMANCE,
                        status=IntegrityStatus.WARNING,
                        message=f"High fragmentation detected ({fragmentation_ratio:.1%})",
                        details={"freelist_pages": freelist_count, "total_pages": page_count},
                        suggestion="Run VACUUM command to defragment database"
                    ))
            
            # Check WAL mode
            cursor.execute("PRAGMA journal_mode")
            journal_mode = cursor.fetchone()[0]
            
            if journal_mode.upper() != 'WAL':
                issues.append(IntegrityIssue(
                    database=os.path.basename(db_path),
                    table="*",
                    check_type=CheckType.PERFORMANCE,
                    status=IntegrityStatus.WARNING,
                    message=f"Journal mode is {journal_mode}, WAL mode recommended",
                    details={"current_mode": journal_mode, "recommended_mode": "WAL"},
                    suggestion="Consider enabling WAL mode for better concurrent access"
                ))
            
            conn.close()
            
        except Exception as e:
            issues.append(IntegrityIssue(
                database=os.path.basename(db_path),
                table="*",
                check_type=CheckType.CORRUPTION,
                status=IntegrityStatus.ERROR,
                message=f"Failed to check performance: {str(e)}",
                suggestion="Check database accessibility"
            ))
            
        return issues

    def check_data_consistency(self, db_path: str) -> List[IntegrityIssue]:
        """Check data consistency and patterns"""
        issues = []
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            for table_name in tables:
                if table_name == 'sqlite_sequence':
                    continue
                
                # Check for duplicate rows
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                    total_rows = cursor.fetchone()[0]
                    
                    if total_rows > 0:
                        # Get column names
                        cursor.execute(f"PRAGMA table_info(`{table_name}`)")
                        columns = [col[1] for col in cursor.fetchall()]
                        column_list = ', '.join(f'`{col}`' for col in columns)
                        
                        cursor.execute(f"SELECT COUNT(DISTINCT {column_list}) FROM `{table_name}`")
                        distinct_rows = cursor.fetchone()[0]
                        
                        if distinct_rows < total_rows:
                            duplicate_count = total_rows - distinct_rows
                            issues.append(IntegrityIssue(
                                database=os.path.basename(db_path),
                                table=table_name,
                                check_type=CheckType.DATA,
                                status=IntegrityStatus.WARNING,
                                message=f"Found {duplicate_count} duplicate rows",
                                details={"total_rows": total_rows, "unique_rows": distinct_rows},
                                suggestion="Consider adding unique constraints or removing duplicates"
                            ))
                
                except Exception as e:
                    # Skip tables that can't be analyzed
                    continue
            
            conn.close()
            
        except Exception as e:
            issues.append(IntegrityIssue(
                database=os.path.basename(db_path),
                table="*",
                check_type=CheckType.CORRUPTION,
                status=IntegrityStatus.ERROR,
                message=f"Failed to check data consistency: {str(e)}",
                suggestion="Check database structure and permissions"
            ))
            
        return issues

    def run_comprehensive_check(self) -> DatabaseIntegrityReport:
        """Run comprehensive database integrity check"""
        start_time = time.time()
        
        print("🔍 Scanning for database files...")
        db_files = self.find_database_files()
        
        print(f"📊 Found {len(db_files)} database files")
        
        self.issues = []
        self.database_info = []
        
        total_size_bytes = 0
        
        for db_path in db_files:
            print(f"🔬 Checking: {os.path.basename(db_path)}")
            
            # Get database info
            db_info = self.get_database_info(db_path)
            self.database_info.append(db_info)
            total_size_bytes += db_info.size_bytes
            
            # Run all checks
            self.issues.extend(self.check_database_corruption(db_path))
            self.issues.extend(self.analyze_table_structure(db_path))
            self.issues.extend(self.check_database_performance(db_path))
            self.issues.extend(self.check_data_consistency(db_path))
        
        # Generate report
        check_duration = time.time() - start_time
        
        critical_issues = sum(1 for issue in self.issues if issue.status == IntegrityStatus.CRITICAL)
        warnings = sum(1 for issue in self.issues if issue.status == IntegrityStatus.WARNING)
        errors = sum(1 for issue in self.issues if issue.status == IntegrityStatus.ERROR)
        passed_checks = len(db_files) * 4 - len(self.issues)  # 4 check types per DB
        
        report = DatabaseIntegrityReport(
            databases_checked=len(db_files),
            total_issues=len(self.issues),
            critical_issues=critical_issues,
            warnings=warnings,
            errors=errors,
            passed_checks=passed_checks,
            total_size_mb=total_size_bytes / (1024 * 1024),
            check_duration=check_duration,
            issues=self.issues,
            database_info=self.database_info,
            timestamp=datetime.now()
        )
        
        # Save report
        self.save_report(report)
        
        return report

    def save_report(self, report: DatabaseIntegrityReport):
        """Save integrity report to audit database"""
        conn = sqlite3.connect(self.audit_db_path)
        cursor = conn.cursor()
        
        try:
            # Save report summary
            cursor.execute('''
            INSERT INTO integrity_reports 
            (databases_checked, total_issues, critical_issues, warnings, errors, 
             passed_checks, total_size_mb, check_duration, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                report.databases_checked, report.total_issues, report.critical_issues,
                report.warnings, report.errors, report.passed_checks,
                report.total_size_mb, report.check_duration, report.timestamp
            ))
            
            report_id = cursor.lastrowid
            
            # Save individual issues
            for issue in report.issues:
                cursor.execute('''
                INSERT INTO integrity_issues 
                (report_id, database_name, table_name, check_type, status, 
                 message, details, suggestion, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    report_id, issue.database, issue.table, issue.check_type.value,
                    issue.status.value, issue.message, json.dumps(issue.details),
                    issue.suggestion, report.timestamp
                ))
            
            # Save database snapshots
            for db_info in report.database_info:
                cursor.execute('''
                INSERT INTO database_snapshots 
                (database_path, database_name, size_bytes, table_count, 
                 total_rows, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    db_info.path, db_info.name, db_info.size_bytes,
                    db_info.table_count, db_info.total_rows, report.timestamp
                ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to save integrity report: {e}")
            conn.rollback()
        finally:
            conn.close()

    def generate_html_report(self, report: DatabaseIntegrityReport) -> str:
        """Generate HTML integrity report"""
        # Status colors
        status_colors = {
            IntegrityStatus.PASS: "#28a745",
            IntegrityStatus.WARNING: "#ffc107",
            IntegrityStatus.CRITICAL: "#dc3545",
            IntegrityStatus.ERROR: "#fd7e14"
        }
        
        # Generate issues table
        issues_html = ""
        for issue in sorted(report.issues, key=lambda x: (x.status.value, x.database, x.table)):
            status_color = status_colors.get(issue.status, "#6c757d")
            
            issues_html += f"""
            <tr style="border-bottom: 1px solid #dee2e6;">
                <td style="padding: 8px;">{issue.database}</td>
                <td style="padding: 8px; font-family: monospace;">{issue.table}</td>
                <td style="padding: 8px;">{issue.check_type.value.replace('_', ' ').title()}</td>
                <td style="padding: 8px; color: {status_color}; font-weight: bold;">{issue.status.value.upper()}</td>
                <td style="padding: 8px; max-width: 300px;">{issue.message}</td>
                <td style="padding: 8px; font-size: 0.9em; color: #6c757d;">{issue.suggestion}</td>
            </tr>
            """
        
        # Generate database info table  
        db_info_html = ""
        for db_info in sorted(report.database_info, key=lambda x: x.size_bytes, reverse=True):
            size_mb = db_info.size_bytes / (1024 * 1024)
            
            db_info_html += f"""
            <tr style="border-bottom: 1px solid #dee2e6;">
                <td style="padding: 8px; font-family: monospace;">{db_info.name}</td>
                <td style="padding: 8px; text-align: right;">{size_mb:.2f} MB</td>
                <td style="padding: 8px; text-align: right;">{db_info.table_count}</td>
                <td style="padding: 8px; text-align: right;">{db_info.total_rows:,}</td>
                <td style="padding: 8px; font-size: 0.9em;">{db_info.modified_time.strftime('%Y-%m-%d %H:%M') if db_info.modified_time else 'Unknown'}</td>
            </tr>
            """
        
        html_report = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Database Integrity Report</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f8f9fa; }}
                .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                h1 {{ color: #343a40; margin-bottom: 30px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th {{ background: #343a40; color: white; padding: 12px 8px; text-align: left; }}
                .summary-cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
                .card {{ padding: 20px; border-radius: 8px; text-align: center; color: white; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🗃️ Database Integrity Report</h1>
                <p><strong>Generated:</strong> {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>Check Duration:</strong> {report.check_duration:.2f} seconds</p>
                <p><strong>Total Database Size:</strong> {report.total_size_mb:.2f} MB</p>
                
                <div class="summary-cards">
                    <div class="card" style="background: #17a2b8;">
                        <h3 style="margin: 0; font-size: 2em;">{report.databases_checked}</h3>
                        <p style="margin: 5px 0 0 0;">Databases Checked</p>
                    </div>
                    <div class="card" style="background: #dc3545;">
                        <h3 style="margin: 0; font-size: 2em;">{report.critical_issues}</h3>
                        <p style="margin: 5px 0 0 0;">Critical Issues</p>
                    </div>
                    <div class="card" style="background: #ffc107; color: #212529;">
                        <h3 style="margin: 0; font-size: 2em;">{report.warnings}</h3>
                        <p style="margin: 5px 0 0 0;">Warnings</p>
                    </div>
                    <div class="card" style="background: #fd7e14;">
                        <h3 style="margin: 0; font-size: 2em;">{report.errors}</h3>
                        <p style="margin: 5px 0 0 0;">Errors</p>
                    </div>
                    <div class="card" style="background: #28a745;">
                        <h3 style="margin: 0; font-size: 2em;">{report.passed_checks}</h3>
                        <p style="margin: 5px 0 0 0;">Passed Checks</p>
                    </div>
                </div>
                
                <h2>🚨 Issues Found</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Database</th>
                            <th>Table</th>
                            <th>Check Type</th>
                            <th>Status</th>
                            <th>Message</th>
                            <th>Suggestion</th>
                        </tr>
                    </thead>
                    <tbody>
                        {issues_html}
                    </tbody>
                </table>
                
                <h2>📊 Database Overview</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Database Name</th>
                            <th>Size</th>
                            <th>Tables</th>
                            <th>Total Rows</th>
                            <th>Last Modified</th>
                        </tr>
                    </thead>
                    <tbody>
                        {db_info_html}
                    </tbody>
                </table>
            </div>
        </body>
        </html>
        """
        
        return html_report

def main():
    """Main function to run database integrity check"""
    checker = DatabaseIntegrityChecker()
    
    print("🗃️ Starting Database Integrity Check...")
    
    # Run comprehensive check
    report = checker.run_comprehensive_check()
    
    # Print summary
    print(f"\n📊 Integrity Check Summary:")
    print(f"🗃️ Databases Checked: {report.databases_checked}")
    print(f"📋 Total Size: {report.total_size_mb:.2f} MB")
    print(f"🚨 Critical Issues: {report.critical_issues}")
    print(f"⚠️ Warnings: {report.warnings}")
    print(f"🔥 Errors: {report.errors}")
    print(f"✅ Passed Checks: {report.passed_checks}")
    print(f"🕒 Check Duration: {report.check_duration:.2f} seconds")
    
    # Show critical issues
    critical_issues = [issue for issue in report.issues if issue.status == IntegrityStatus.CRITICAL]
    if critical_issues:
        print(f"\n🚨 Critical Issues:")
        for issue in critical_issues:
            print(f"  {issue.database}/{issue.table}: {issue.message}")
    
    # Generate HTML report
    html_report = checker.generate_html_report(report)
    report_path = f"database_integrity_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    
    with open(report_path, 'w') as f:
        f.write(html_report)
    
    print(f"\n📄 HTML report saved: {report_path}")
    return report

if __name__ == "__main__":
    main()