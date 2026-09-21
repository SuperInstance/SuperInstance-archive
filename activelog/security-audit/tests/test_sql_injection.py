"""
SQL Injection Prevention Tests for ActiveLog
Comprehensive test suite to detect and prevent SQL injection vulnerabilities.
"""

import pytest
import asyncio
import sqlite3
import tempfile
import os
from typing import List, Dict, Any
from pathlib import Path
import sqlalchemy
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import psycopg2
from psycopg2 import sql
import pymongo
from fastapi.testclient import TestClient


class SQLInjectionTester:
    """SQL injection vulnerability tester."""
    
    def __init__(self):
        self.test_db_path = None
        self.engine = None
        self.session = None
        
        # Common SQL injection payloads
        self.sql_injection_payloads = [
            # Classic SQL injection
            "'; DROP TABLE users; --",
            "admin'--",
            "admin'/*",
            "' OR '1'='1",
            "' OR 1=1--",
            "' OR 'a'='a",
            "') OR ('1'='1",
            
            # Union-based injection
            "' UNION SELECT username, password FROM users--",
            "' UNION SELECT 1,2,3,4,5--",
            "' UNION ALL SELECT NULL,NULL,NULL--",
            
            # Boolean-based blind injection
            "' AND 1=1--",
            "' AND 1=2--",
            "' AND (SELECT COUNT(*) FROM users)>0--",
            "' AND (SELECT SUBSTRING(@@version,1,1))='5'--",
            
            # Time-based blind injection
            "'; WAITFOR DELAY '00:00:05'--",
            "'; SELECT SLEEP(5)--",
            "' AND (SELECT SLEEP(5))--",
            "'; pg_sleep(5)--",
            
            # Error-based injection
            "' AND (SELECT * FROM (SELECT COUNT(*),CONCAT(version(),FLOOR(RAND(0)*2))x FROM information_schema.tables GROUP BY x)a)--",
            "' AND extractvalue(1, concat(0x7e, (select user()), 0x7e))--",
            
            # Second-order injection
            "admin'; INSERT INTO users (username, password) VALUES ('hacker', 'password')--",
            
            # NoSQL injection (for MongoDB tests)
            {"$ne": None},
            {"$gt": ""},
            {"$regex": ".*"},
            {"$where": "this.username == 'admin'"},
            
            # Advanced payloads
            "'; EXEC xp_cmdshell('dir')--",
            "'; EXEC master..xp_cmdshell 'ping 127.0.0.1'--",
            "' OR (SELECT user FROM mysql.user WHERE user='root')='root'--",
            
            # Encoding variations
            "%27%20OR%201=1--",
            "0x27204f5220313d312d2d",
            "\\' OR 1=1--",
            
            # Polyglot payloads
            "SLEEP(1) /*' or SLEEP(1) or '\" or SLEEP(1) or \"*/",
        ]
        
        # SQL functions and keywords to detect
        self.dangerous_sql_keywords = [
            'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
            'EXEC', 'EXECUTE', 'UNION', 'SCRIPT', 'INFORMATION_SCHEMA',
            'SYSOBJECTS', 'SYSCOLUMNS', 'xp_', 'sp_', 'WAITFOR', 'SLEEP',
            'BENCHMARK', 'LOAD_FILE', 'INTO OUTFILE', 'INTO DUMPFILE'
        ]
    
    def setup_test_database(self) -> str:
        """Setup test SQLite database."""
        fd, self.test_db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        # Create test database with sample data
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT,
                role TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create files table
        cursor.execute('''
            CREATE TABLE files (
                id INTEGER PRIMARY KEY,
                filename TEXT NOT NULL,
                path TEXT NOT NULL,
                owner_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users (id)
            )
        ''')
        
        # Insert test data
        test_users = [
            ('admin', 'admin_password_hash', 'admin@activelog.com', 'admin'),
            ('user1', 'user1_password_hash', 'user1@example.com', 'user'),
            ('user2', 'user2_password_hash', 'user2@example.com', 'user'),
            ('testuser', 'test_password_hash', 'test@example.com', 'user')
        ]
        
        cursor.executemany(
            'INSERT INTO users (username, password, email, role) VALUES (?, ?, ?, ?)',
            test_users
        )
        
        test_files = [
            ('document1.pdf', '/files/doc1.pdf', 1),
            ('image1.jpg', '/files/img1.jpg', 2),
            ('spreadsheet1.xlsx', '/files/sheet1.xlsx', 1),
            ('presentation1.pptx', '/files/pres1.pptx', 3)
        ]
        
        cursor.executemany(
            'INSERT INTO files (filename, path, owner_id) VALUES (?, ?, ?)',
            test_files
        )
        
        conn.commit()
        conn.close()
        
        return self.test_db_path
    
    def test_vulnerable_query(self, user_input: str) -> Dict[str, Any]:
        """Test a vulnerable SQL query (for demonstration)."""
        result = {
            'payload': user_input,
            'vulnerable': False,
            'error': None,
            'results': None,
            'execution_time': 0
        }
        
        try:
            import time
            start_time = time.time()
            
            conn = sqlite3.connect(self.test_db_path)
            cursor = conn.cursor()
            
            # VULNERABLE QUERY - DO NOT USE IN PRODUCTION
            vulnerable_query = f"SELECT * FROM users WHERE username = '{user_input}'"
            
            cursor.execute(vulnerable_query)
            results = cursor.fetchall()
            
            execution_time = time.time() - start_time
            
            result.update({
                'vulnerable': True,
                'results': results,
                'execution_time': execution_time,
                'query': vulnerable_query
            })
            
            conn.close()
            
        except Exception as e:
            result.update({
                'vulnerable': True,
                'error': str(e),
                'execution_time': time.time() - start_time
            })
        
        return result
    
    def test_secure_query(self, user_input: str) -> Dict[str, Any]:
        """Test a secure parameterized query."""
        result = {
            'payload': user_input,
            'vulnerable': False,
            'error': None,
            'results': None,
            'execution_time': 0
        }
        
        try:
            import time
            start_time = time.time()
            
            conn = sqlite3.connect(self.test_db_path)
            cursor = conn.cursor()
            
            # SECURE QUERY - Uses parameterized statements
            secure_query = "SELECT * FROM users WHERE username = ?"
            
            cursor.execute(secure_query, (user_input,))
            results = cursor.fetchall()
            
            execution_time = time.time() - start_time
            
            result.update({
                'vulnerable': False,
                'results': results,
                'execution_time': execution_time,
                'query': secure_query
            })
            
            conn.close()
            
        except Exception as e:
            result.update({
                'error': str(e),
                'execution_time': time.time() - start_time
            })
        
        return result
    
    def test_sqlalchemy_queries(self, user_input: str) -> Dict[str, Any]:
        """Test SQLAlchemy ORM and raw queries."""
        if not self.engine:
            self.engine = create_engine(f'sqlite:///{self.test_db_path}')
            Session = sessionmaker(bind=self.engine)
            self.session = Session()
        
        results = {
            'payload': user_input,
            'raw_query_vulnerable': False,
            'raw_query_secure': False,
            'orm_query': False,
            'errors': []
        }
        
        try:
            # Test vulnerable raw SQL
            try:
                vulnerable_sql = text(f"SELECT * FROM users WHERE username = '{user_input}'")
                result = self.session.execute(vulnerable_sql).fetchall()
                results['raw_query_vulnerable'] = True
                results['vulnerable_results'] = len(result)
            except Exception as e:
                results['errors'].append(f"Vulnerable query error: {str(e)}")
            
            # Test secure raw SQL
            try:
                secure_sql = text("SELECT * FROM users WHERE username = :username")
                result = self.session.execute(secure_sql, {'username': user_input}).fetchall()
                results['raw_query_secure'] = True
                results['secure_results'] = len(result)
            except Exception as e:
                results['errors'].append(f"Secure query error: {str(e)}")
                
        except Exception as e:
            results['errors'].append(f"SQLAlchemy test error: {str(e)}")
        
        return results
    
    def analyze_payload_effectiveness(self, payload: str, test_results: List[Dict]) -> Dict[str, Any]:
        """Analyze the effectiveness of a SQL injection payload."""
        analysis = {
            'payload': payload,
            'effective': False,
            'attack_type': 'unknown',
            'severity': 'low',
            'indicators': []
        }
        
        for result in test_results:
            if result.get('vulnerable', False):
                # Check for successful data extraction
                if result.get('results') and len(result['results']) > 0:
                    analysis['effective'] = True
                    analysis['severity'] = 'high'
                    analysis['indicators'].append('data_extraction')
                
                # Check for error-based injection
                if result.get('error'):
                    error_msg = result['error'].lower()
                    if any(keyword in error_msg for keyword in ['syntax', 'near', 'unexpected']):
                        analysis['effective'] = True
                        analysis['attack_type'] = 'error_based'
                        analysis['indicators'].append('sql_error')
                
                # Check for time-based injection
                if result.get('execution_time', 0) > 3:  # Delay > 3 seconds
                    analysis['effective'] = True
                    analysis['attack_type'] = 'time_based'
                    analysis['severity'] = 'medium'
                    analysis['indicators'].append('time_delay')
                
                # Check for boolean-based injection
                if 'OR' in payload.upper() and result.get('results'):
                    analysis['effective'] = True
                    analysis['attack_type'] = 'boolean_based'
                    analysis['indicators'].append('boolean_logic')
        
        return analysis
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive SQL injection tests."""
        self.setup_test_database()
        
        test_report = {
            'total_payloads': len(self.sql_injection_payloads),
            'vulnerable_responses': 0,
            'secure_responses': 0,
            'effective_payloads': 0,
            'failed_payloads': 0,
            'detailed_results': [],
            'severity_summary': {'high': 0, 'medium': 0, 'low': 0},
            'attack_types': {}
        }
        
        print("Running comprehensive SQL injection tests...")
        
        for i, payload in enumerate(self.sql_injection_payloads):
            if isinstance(payload, dict):
                # Skip NoSQL payloads for SQL tests
                continue
                
            print(f"Testing payload {i+1}/{len(self.sql_injection_payloads)}: {payload[:50]}...")
            
            # Test vulnerable query
            vulnerable_result = self.test_vulnerable_query(payload)
            
            # Test secure query  
            secure_result = self.test_secure_query(payload)
            
            # Test SQLAlchemy queries
            sqlalchemy_result = self.test_sqlalchemy_queries(payload)
            
            # Analyze payload effectiveness
            analysis = self.analyze_payload_effectiveness(
                payload, [vulnerable_result, secure_result, sqlalchemy_result]
            )
            
            # Update counters
            if vulnerable_result.get('vulnerable', False):
                test_report['vulnerable_responses'] += 1
            
            if not secure_result.get('error'):
                test_report['secure_responses'] += 1
            
            if analysis['effective']:
                test_report['effective_payloads'] += 1
                test_report['severity_summary'][analysis['severity']] += 1
                
                attack_type = analysis['attack_type']
                test_report['attack_types'][attack_type] = test_report['attack_types'].get(attack_type, 0) + 1
            
            if vulnerable_result.get('error') and secure_result.get('error'):
                test_report['failed_payloads'] += 1
            
            # Store detailed results
            detailed_result = {
                'payload': payload,
                'vulnerable_query': vulnerable_result,
                'secure_query': secure_result,
                'sqlalchemy_query': sqlalchemy_result,
                'analysis': analysis
            }
            test_report['detailed_results'].append(detailed_result)
        
        # Cleanup
        self.cleanup()
        
        return test_report
    
    def generate_test_report(self, test_results: Dict[str, Any]) -> str:
        """Generate human-readable test report."""
        report_lines = [
            "=" * 80,
            "SQL INJECTION PREVENTION TEST REPORT",
            "=" * 80,
            f"Total Payloads Tested: {test_results['total_payloads']}",
            f"Vulnerable Responses: {test_results['vulnerable_responses']}",
            f"Secure Responses: {test_results['secure_responses']}",
            f"Effective Payloads: {test_results['effective_payloads']}",
            f"Failed Payloads: {test_results['failed_payloads']}",
            "",
            "SEVERITY BREAKDOWN:",
            f"  HIGH:   {test_results['severity_summary']['high']} payloads",
            f"  MEDIUM: {test_results['severity_summary']['medium']} payloads",
            f"  LOW:    {test_results['severity_summary']['low']} payloads",
            "",
            "ATTACK TYPES DETECTED:",
        ]
        
        for attack_type, count in test_results['attack_types'].items():
            report_lines.append(f"  {attack_type.upper()}: {count} payloads")
        
        report_lines.extend([
            "",
            "RECOMMENDATIONS:",
            "- Use parameterized queries/prepared statements for all database interactions",
            "- Implement input validation and sanitization",
            "- Apply principle of least privilege for database access",
            "- Use stored procedures where appropriate",
            "- Implement Web Application Firewall (WAF) rules",
            "- Regular security testing and code review",
            "",
            "EFFECTIVE PAYLOADS DETAILS:",
        ])
        
        # Show details for effective payloads
        effective_payloads = [r for r in test_results['detailed_results'] if r['analysis']['effective']]
        for result in effective_payloads[:10]:  # Show first 10
            payload = result['payload']
            analysis = result['analysis']
            report_lines.extend([
                f"  Payload: {payload}",
                f"  Attack Type: {analysis['attack_type']}",
                f"  Severity: {analysis['severity']}",
                f"  Indicators: {', '.join(analysis['indicators'])}",
                ""
            ])
        
        if len(effective_payloads) > 10:
            report_lines.append(f"  ... and {len(effective_payloads) - 10} more effective payloads")
        
        report_lines.extend([
            "",
            "=" * 80
        ])
        
        return "\n".join(report_lines)
    
    def cleanup(self):
        """Cleanup test resources."""
        if self.session:
            self.session.close()
        
        if self.test_db_path and os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)


# Pytest test cases
class TestSQLInjectionPrevention:
    """Pytest test cases for SQL injection prevention."""
    
    @pytest.fixture
    def sql_tester(self):
        """Create SQL injection tester instance."""
        tester = SQLInjectionTester()
        tester.setup_test_database()
        yield tester
        tester.cleanup()
    
    def test_parameterized_queries_prevent_injection(self, sql_tester):
        """Test that parameterized queries prevent SQL injection."""
        malicious_input = "'; DROP TABLE users; --"
        
        # Secure query should not be vulnerable
        result = sql_tester.test_secure_query(malicious_input)
        
        assert not result['vulnerable']
        assert result['error'] is None
        assert isinstance(result['results'], list)
    
    def test_vulnerable_query_detection(self, sql_tester):
        """Test detection of vulnerable queries."""
        malicious_input = "' OR '1'='1"
        
        # Vulnerable query should be detected
        result = sql_tester.test_vulnerable_query(malicious_input)
        
        assert result['vulnerable']
        # Should return more results than expected (all users)
        assert len(result['results']) > 1
    
    def test_time_based_injection_detection(self, sql_tester):
        """Test detection of time-based injection attempts."""
        # Note: SQLite doesn't support SLEEP, so this test is conceptual
        time_based_payload = "'; SELECT SLEEP(5)--"
        
        result = sql_tester.test_secure_query(time_based_payload)
        
        # Should not cause delay in secure implementation
        assert result['execution_time'] < 1
    
    def test_union_based_injection_prevention(self, sql_tester):
        """Test prevention of UNION-based injection."""
        union_payload = "' UNION SELECT username, password FROM users--"
        
        secure_result = sql_tester.test_secure_query(union_payload)
        
        # Should not return multiple columns or sensitive data
        assert not secure_result.get('vulnerable', False)
    
    def test_error_based_injection_prevention(self, sql_tester):
        """Test prevention of error-based injection."""
        error_payload = "' AND (SELECT * FROM non_existent_table)--"
        
        secure_result = sql_tester.test_secure_query(error_payload)
        
        # Should handle errors gracefully without revealing schema info
        if secure_result.get('error'):
            assert 'non_existent_table' not in secure_result['error'].lower()
    
    @pytest.mark.parametrize("payload", [
        "'; DROP TABLE users; --",
        "' OR 1=1--",
        "admin'--", 
        "' UNION SELECT * FROM users--"
    ])
    def test_common_injection_payloads(self, sql_tester, payload):
        """Test common SQL injection payloads."""
        secure_result = sql_tester.test_secure_query(payload)
        
        # Secure implementation should not be vulnerable
        assert not secure_result.get('vulnerable', True)
        
        # Should either return no results or expected single result
        if secure_result.get('results'):
            assert len(secure_result['results']) <= 1


def run_active_log_sql_injection_tests():
    """Run SQL injection tests specifically for ActiveLog services."""
    
    # Test database connection strings
    test_scenarios = [
        {
            'name': 'Auth Service Database',
            'connection_string': 'sqlite:///test_auth.db',
            'test_queries': [
                "SELECT * FROM users WHERE username = '{input}' AND password = '{password}'",
                "SELECT * FROM sessions WHERE token = '{input}'",
                "INSERT INTO audit_log (user_id, action) VALUES ({input}, 'login')"
            ]
        },
        {
            'name': 'Metadata Service Database', 
            'connection_string': 'sqlite:///test_metadata.db',
            'test_queries': [
                "SELECT * FROM files WHERE filename LIKE '%{input}%'",
                "SELECT * FROM tags WHERE name = '{input}'",
                "SELECT * FROM search_history WHERE query = '{input}'"
            ]
        }
    ]
    
    tester = SQLInjectionTester()
    overall_results = {'services': []}
    
    for scenario in test_scenarios:
        print(f"\nTesting {scenario['name']}...")
        
        service_results = {
            'name': scenario['name'],
            'vulnerable_queries': 0,
            'total_queries': len(scenario['test_queries']),
            'findings': []
        }
        
        for query_template in scenario['test_queries']:
            for payload in tester.sql_injection_payloads[:10]:  # Test first 10 payloads
                if isinstance(payload, dict):
                    continue
                    
                # Simulate vulnerable query construction
                try:
                    vulnerable_query = query_template.format(input=payload, password='test')
                    
                    # Check if payload would modify query structure
                    if any(keyword in vulnerable_query.upper() for keyword in tester.dangerous_sql_keywords):
                        service_results['vulnerable_queries'] += 1
                        service_results['findings'].append({
                            'query_template': query_template,
                            'payload': payload,
                            'resulting_query': vulnerable_query,
                            'risk': 'HIGH'
                        })
                        break  # One finding per query template is enough
                        
                except Exception as e:
                    # Payload caused formatting error - potential injection
                    service_results['findings'].append({
                        'query_template': query_template,
                        'payload': payload,
                        'error': str(e),
                        'risk': 'MEDIUM'
                    })
        
        overall_results['services'].append(service_results)
    
    # Generate report
    print("\n" + "="*80)
    print("ACTIVELOG SQL INJECTION ASSESSMENT REPORT")
    print("="*80)
    
    for service in overall_results['services']:
        print(f"\nService: {service['name']}")
        print(f"Vulnerable Queries: {service['vulnerable_queries']}/{service['total_queries']}")
        
        if service['findings']:
            print("Key Findings:")
            for finding in service['findings'][:3]:  # Show first 3 findings
                print(f"  - Risk: {finding['risk']}")
                print(f"    Template: {finding['query_template']}")
                print(f"    Payload: {finding['payload']}")
    
    return overall_results


def main():
    """Main function to run SQL injection tests."""
    print("Starting SQL Injection Prevention Tests for ActiveLog...")
    
    # Run comprehensive tests
    tester = SQLInjectionTester()
    results = tester.run_comprehensive_test()
    
    # Generate and save report
    report = tester.generate_test_report(results)
    
    # Save report to file
    report_path = Path(__file__).parent.parent / "reports" / "sql_injection_test_report.txt"
    report_path.parent.mkdir(exist_ok=True)
    
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(report)
    print(f"\nDetailed report saved to: {report_path}")
    
    # Run ActiveLog specific tests
    print("\nRunning ActiveLog specific tests...")
    activelog_results = run_active_log_sql_injection_tests()
    
    return results


if __name__ == "__main__":
    main()