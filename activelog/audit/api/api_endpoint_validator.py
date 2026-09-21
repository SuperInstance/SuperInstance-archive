#!/usr/bin/env python3

import asyncio
import aiohttp
import json
import time
import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import logging
import yaml
import os
from urllib.parse import urljoin, urlparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ValidationStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    TIMEOUT = "timeout"
    ERROR = "error"
    SKIP = "skip"

class HTTPMethod(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"

@dataclass
class APIEndpoint:
    name: str
    url: str
    method: HTTPMethod
    expected_status: int = 200
    timeout: float = 10.0
    headers: Dict[str, str] = None
    payload: Dict[str, Any] = None
    auth_required: bool = False
    description: str = ""
    tags: List[str] = None

    def __post_init__(self):
        if self.headers is None:
            self.headers = {}
        if self.tags is None:
            self.tags = []

@dataclass
class ValidationResult:
    endpoint_name: str
    url: str
    method: str
    status: ValidationStatus
    response_status: Optional[int]
    response_time: float
    response_size: Optional[int]
    error_message: Optional[str]
    timestamp: datetime
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}

@dataclass
class ValidationReport:
    total_endpoints: int
    passed: int
    failed: int
    errors: int
    timeouts: int
    skipped: int
    total_time: float
    results: List[ValidationResult]
    timestamp: datetime
    coverage_percentage: float = 0.0
    performance_score: float = 0.0

class APIEndpointValidator:
    def __init__(self, db_path: str = "audit_api_validation.db"):
        self.db_path = db_path
        self.session: Optional[aiohttp.ClientSession] = None
        self.endpoints: List[APIEndpoint] = []
        self.results: List[ValidationResult] = []
        self.init_database()
        self.load_endpoint_definitions()

    def init_database(self):
        """Initialize SQLite database for validation results"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS validation_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            endpoint_name TEXT NOT NULL,
            url TEXT NOT NULL,
            method TEXT NOT NULL,
            status TEXT NOT NULL,
            response_status INTEGER,
            response_time REAL NOT NULL,
            response_size INTEGER,
            error_message TEXT,
            timestamp DATETIME NOT NULL,
            details TEXT
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS validation_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_endpoints INTEGER NOT NULL,
            passed INTEGER NOT NULL,
            failed INTEGER NOT NULL,
            errors INTEGER NOT NULL,
            timeouts INTEGER NOT NULL,
            skipped INTEGER NOT NULL,
            total_time REAL NOT NULL,
            coverage_percentage REAL NOT NULL,
            performance_score REAL NOT NULL,
            timestamp DATETIME NOT NULL
        )
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_validation_results_timestamp 
        ON validation_results(timestamp)
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_validation_results_endpoint 
        ON validation_results(endpoint_name)
        ''')
        
        conn.commit()
        conn.close()

    def load_endpoint_definitions(self):
        """Load API endpoint definitions from various sources"""
        # ActiveLog core services endpoints
        activelog_services = [
            # Main API Gateway
            {"name": "api_gateway_health", "url": "http://localhost:8001/health", "method": HTTPMethod.GET, "description": "API Gateway health check"},
            {"name": "api_gateway_metrics", "url": "http://localhost:8001/metrics", "method": HTTPMethod.GET, "description": "API Gateway metrics"},
            
            # Auth Service
            {"name": "auth_health", "url": "http://localhost:8002/health", "method": HTTPMethod.GET, "description": "Auth service health"},
            {"name": "auth_login", "url": "http://localhost:8002/auth/login", "method": HTTPMethod.POST, "expected_status": 422, "description": "Login endpoint"},
            {"name": "auth_register", "url": "http://localhost:8002/auth/register", "method": HTTPMethod.POST, "expected_status": 422, "description": "Register endpoint"},
            
            # File Services
            {"name": "file_sync_health", "url": "http://localhost:8003/health", "method": HTTPMethod.GET, "description": "File sync health"},
            {"name": "file_sync_status", "url": "http://localhost:8003/sync/status", "method": HTTPMethod.GET, "description": "Sync status"},
            {"name": "file_watcher_health", "url": "http://localhost:8004/health", "method": HTTPMethod.GET, "description": "File watcher health"},
            
            # Data Services
            {"name": "metadata_health", "url": "http://localhost:8005/health", "method": HTTPMethod.GET, "description": "Metadata service health"},
            {"name": "metadata_files", "url": "http://localhost:8005/files", "method": HTTPMethod.GET, "description": "File metadata listing"},
            
            # AI Services
            {"name": "ai_orchestrator_health", "url": "http://localhost:8006/health", "method": HTTPMethod.GET, "description": "AI orchestrator health"},
            {"name": "cognitive_ai_health", "url": "http://localhost:8007/health", "method": HTTPMethod.GET, "description": "Cognitive AI health"},
            
            # Voice Excellence
            {"name": "voice_excellence_health", "url": "http://localhost:8380/health", "method": HTTPMethod.GET, "description": "Voice Excellence health"},
            {"name": "voice_excellence_commands", "url": "http://localhost:8380/api/commands/list", "method": HTTPMethod.GET, "description": "Voice commands list"},
            {"name": "voice_excellence_stats", "url": "http://localhost:8380/api/stats", "method": HTTPMethod.GET, "description": "Voice system stats"},
            
            # Dream Mode v2
            {"name": "dream_mode_health", "url": "http://localhost:8388/health", "method": HTTPMethod.GET, "description": "Dream Mode v2 health"},
            {"name": "dream_mode_simulations", "url": "http://localhost:8388/simulations", "method": HTTPMethod.GET, "description": "Industry simulations"},
            {"name": "dream_mode_personas", "url": "http://localhost:8388/personas", "method": HTTPMethod.GET, "description": "User personas"},
            
            # Marketplace v2
            {"name": "marketplace_health", "url": "http://localhost:8390/health", "method": HTTPMethod.GET, "description": "Marketplace v2 health"},
            {"name": "marketplace_products", "url": "http://localhost:8390/products", "method": HTTPMethod.GET, "description": "Product listings"},
            {"name": "marketplace_assemblers", "url": "http://localhost:8390/assemblers", "method": HTTPMethod.GET, "description": "Assembler boards"},
            
            # Frontend Services
            {"name": "frontend_health", "url": "http://localhost:3000", "method": HTTPMethod.GET, "description": "Main frontend", "timeout": 15.0},
            {"name": "unified_frontend", "url": "http://localhost:3001", "method": HTTPMethod.GET, "description": "Unified frontend", "timeout": 15.0},
        ]
        
        # Convert to APIEndpoint objects
        for service in activelog_services:
            endpoint = APIEndpoint(
                name=service["name"],
                url=service["url"],
                method=service["method"],
                expected_status=service.get("expected_status", 200),
                timeout=service.get("timeout", 10.0),
                description=service.get("description", ""),
                tags=["activelog", "core"]
            )
            self.endpoints.append(endpoint)
        
        # Load additional endpoints from config file if exists
        config_path = "api_endpoints_config.yaml"
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    for endpoint_config in config.get('endpoints', []):
                        endpoint = APIEndpoint(**endpoint_config)
                        self.endpoints.append(endpoint)
            except Exception as e:
                logger.warning(f"Failed to load endpoint config: {e}")

    async def validate_endpoint(self, endpoint: APIEndpoint) -> ValidationResult:
        """Validate a single API endpoint"""
        start_time = time.time()
        
        try:
            # Prepare request
            headers = endpoint.headers.copy() if endpoint.headers else {}
            headers.setdefault('User-Agent', 'ActiveLog-API-Validator/1.0')
            
            async with self.session.request(
                method=endpoint.method.value,
                url=endpoint.url,
                headers=headers,
                json=endpoint.payload if endpoint.payload else None,
                timeout=aiohttp.ClientTimeout(total=endpoint.timeout)
            ) as response:
                response_time = time.time() - start_time
                response_text = await response.text()
                response_size = len(response_text.encode('utf-8'))
                
                # Determine validation status
                if response.status == endpoint.expected_status:
                    status = ValidationStatus.PASS
                    error_message = None
                else:
                    status = ValidationStatus.FAIL
                    error_message = f"Expected status {endpoint.expected_status}, got {response.status}"
                
                # Additional checks
                details = {
                    'response_headers': dict(response.headers),
                    'response_preview': response_text[:500] if response_text else None,
                    'content_type': response.headers.get('content-type', ''),
                }
                
                # Check for common issues
                if 'application/json' in details['content_type']:
                    try:
                        json_data = await response.json()
                        details['json_valid'] = True
                        details['json_keys'] = list(json_data.keys()) if isinstance(json_data, dict) else []
                    except:
                        details['json_valid'] = False
                        if status == ValidationStatus.PASS:
                            status = ValidationStatus.FAIL
                            error_message = "Invalid JSON response"
                
                return ValidationResult(
                    endpoint_name=endpoint.name,
                    url=endpoint.url,
                    method=endpoint.method.value,
                    status=status,
                    response_status=response.status,
                    response_time=response_time,
                    response_size=response_size,
                    error_message=error_message,
                    timestamp=datetime.now(),
                    details=details
                )
                
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            return ValidationResult(
                endpoint_name=endpoint.name,
                url=endpoint.url,
                method=endpoint.method.value,
                status=ValidationStatus.TIMEOUT,
                response_status=None,
                response_time=response_time,
                response_size=None,
                error_message="Request timeout",
                timestamp=datetime.now()
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            return ValidationResult(
                endpoint_name=endpoint.name,
                url=endpoint.url,
                method=endpoint.method.value,
                status=ValidationStatus.ERROR,
                response_status=None,
                response_time=response_time,
                response_size=None,
                error_message=str(e),
                timestamp=datetime.now()
            )

    async def validate_all_endpoints(self, parallel_limit: int = 10) -> ValidationReport:
        """Validate all endpoints with controlled parallelism"""
        start_time = time.time()
        self.results = []
        
        # Create session
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
        
        try:
            # Create semaphore for limiting parallel requests
            semaphore = asyncio.Semaphore(parallel_limit)
            
            async def validate_with_semaphore(endpoint):
                async with semaphore:
                    return await self.validate_endpoint(endpoint)
            
            # Run validations
            tasks = [validate_with_semaphore(endpoint) for endpoint in self.endpoints]
            self.results = await asyncio.gather(*tasks)
            
        finally:
            await self.session.close()
        
        # Generate report
        total_time = time.time() - start_time
        
        passed = sum(1 for r in self.results if r.status == ValidationStatus.PASS)
        failed = sum(1 for r in self.results if r.status == ValidationStatus.FAIL)
        errors = sum(1 for r in self.results if r.status == ValidationStatus.ERROR)
        timeouts = sum(1 for r in self.results if r.status == ValidationStatus.TIMEOUT)
        skipped = sum(1 for r in self.results if r.status == ValidationStatus.SKIP)
        
        coverage_percentage = (passed / len(self.endpoints)) * 100 if self.endpoints else 0
        
        # Calculate performance score based on response times
        valid_times = [r.response_time for r in self.results if r.response_time and r.response_time < 30]
        avg_response_time = sum(valid_times) / len(valid_times) if valid_times else 0
        performance_score = max(0, 100 - (avg_response_time * 10))  # Penalize slow responses
        
        report = ValidationReport(
            total_endpoints=len(self.endpoints),
            passed=passed,
            failed=failed,
            errors=errors,
            timeouts=timeouts,
            skipped=skipped,
            total_time=total_time,
            results=self.results,
            timestamp=datetime.now(),
            coverage_percentage=coverage_percentage,
            performance_score=performance_score
        )
        
        # Save to database
        self.save_report(report)
        
        return report

    def save_report(self, report: ValidationReport):
        """Save validation report and results to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Save report summary
            cursor.execute('''
            INSERT INTO validation_reports 
            (total_endpoints, passed, failed, errors, timeouts, skipped, total_time, 
             coverage_percentage, performance_score, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                report.total_endpoints, report.passed, report.failed, report.errors,
                report.timeouts, report.skipped, report.total_time,
                report.coverage_percentage, report.performance_score, report.timestamp
            ))
            
            # Save individual results
            for result in report.results:
                cursor.execute('''
                INSERT INTO validation_results 
                (endpoint_name, url, method, status, response_status, response_time,
                 response_size, error_message, timestamp, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    result.endpoint_name, result.url, result.method, result.status.value,
                    result.response_status, result.response_time, result.response_size,
                    result.error_message, result.timestamp, json.dumps(result.details)
                ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to save validation report: {e}")
            conn.rollback()
        finally:
            conn.close()

    def get_historical_reports(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get historical validation reports"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        cursor.execute('''
        SELECT * FROM validation_reports 
        WHERE timestamp >= ?
        ORDER BY timestamp DESC
        ''', (cutoff_date,))
        
        columns = [description[0] for description in cursor.description]
        reports = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return reports

    def get_endpoint_history(self, endpoint_name: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get validation history for a specific endpoint"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        cursor.execute('''
        SELECT * FROM validation_results 
        WHERE endpoint_name = ? AND timestamp >= ?
        ORDER BY timestamp DESC
        ''', (endpoint_name, cutoff_date))
        
        columns = [description[0] for description in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return results

    def generate_html_report(self, report: ValidationReport) -> str:
        """Generate HTML validation report"""
        # Status colors
        status_colors = {
            ValidationStatus.PASS: "#28a745",
            ValidationStatus.FAIL: "#dc3545", 
            ValidationStatus.ERROR: "#fd7e14",
            ValidationStatus.TIMEOUT: "#6f42c1",
            ValidationStatus.SKIP: "#6c757d"
        }
        
        # Generate results table
        results_html = ""
        for result in sorted(report.results, key=lambda x: (x.status.value, x.endpoint_name)):
            status_color = status_colors.get(result.status, "#6c757d")
            
            results_html += f"""
            <tr style="border-bottom: 1px solid #dee2e6;">
                <td style="padding: 8px;">{result.endpoint_name}</td>
                <td style="padding: 8px; font-family: monospace; font-size: 0.9em;">{result.method}</td>
                <td style="padding: 8px; font-family: monospace; font-size: 0.8em; max-width: 300px; overflow: hidden; text-overflow: ellipsis;">{result.url}</td>
                <td style="padding: 8px; color: {status_color}; font-weight: bold;">{result.status.value.upper()}</td>
                <td style="padding: 8px;">{result.response_status or 'N/A'}</td>
                <td style="padding: 8px;">{result.response_time:.3f}s</td>
                <td style="padding: 8px;">{result.response_size or 'N/A'}</td>
                <td style="padding: 8px; color: #dc3545; font-size: 0.9em;">{result.error_message or ''}</td>
            </tr>
            """
        
        # Generate summary cards
        summary_cards = f"""
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px;">
            <div style="background: #28a745; color: white; padding: 20px; border-radius: 8px; text-align: center;">
                <h3 style="margin: 0; font-size: 2em;">{report.passed}</h3>
                <p style="margin: 5px 0 0 0;">Passed</p>
            </div>
            <div style="background: #dc3545; color: white; padding: 20px; border-radius: 8px; text-align: center;">
                <h3 style="margin: 0; font-size: 2em;">{report.failed}</h3>
                <p style="margin: 5px 0 0 0;">Failed</p>
            </div>
            <div style="background: #fd7e14; color: white; padding: 20px; border-radius: 8px; text-align: center;">
                <h3 style="margin: 0; font-size: 2em;">{report.errors}</h3>
                <p style="margin: 5px 0 0 0;">Errors</p>
            </div>
            <div style="background: #6f42c1; color: white; padding: 20px; border-radius: 8px; text-align: center;">
                <h3 style="margin: 0; font-size: 2em;">{report.timeouts}</h3>
                <p style="margin: 5px 0 0 0;">Timeouts</p>
            </div>
            <div style="background: #17a2b8; color: white; padding: 20px; border-radius: 8px; text-align: center;">
                <h3 style="margin: 0; font-size: 2em;">{report.coverage_percentage:.1f}%</h3>
                <p style="margin: 5px 0 0 0;">Coverage</p>
            </div>
            <div style="background: #20c997; color: white; padding: 20px; border-radius: 8px; text-align: center;">
                <h3 style="margin: 0; font-size: 2em;">{report.performance_score:.1f}</h3>
                <p style="margin: 5px 0 0 0;">Performance Score</p>
            </div>
        </div>
        """
        
        html_report = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>API Endpoint Validation Report</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f8f9fa; }}
                .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                h1 {{ color: #343a40; margin-bottom: 30px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th {{ background: #343a40; color: white; padding: 12px 8px; text-align: left; }}
                .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 20px 0; }}
                .metric {{ background: #e9ecef; padding: 15px; border-radius: 5px; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔍 API Endpoint Validation Report</h1>
                <p><strong>Generated:</strong> {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>Total Validation Time:</strong> {report.total_time:.2f} seconds</p>
                
                {summary_cards}
                
                <h2>📊 Detailed Results</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Endpoint Name</th>
                            <th>Method</th>
                            <th>URL</th>
                            <th>Status</th>
                            <th>Response Code</th>
                            <th>Response Time</th>
                            <th>Response Size</th>
                            <th>Error Message</th>
                        </tr>
                    </thead>
                    <tbody>
                        {results_html}
                    </tbody>
                </table>
                
                <div style="margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 5px;">
                    <h3>📈 Summary Statistics</h3>
                    <div class="metrics">
                        <div class="metric">
                            <strong>{len(report.results)}</strong><br>
                            Total Endpoints
                        </div>
                        <div class="metric">
                            <strong>{report.total_time:.1f}s</strong><br>
                            Total Time
                        </div>
                        <div class="metric">
                            <strong>{sum(r.response_time for r in report.results if r.response_time):.2f}s</strong><br>
                            Total Response Time
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_report

async def main():
    """Main function to run API endpoint validation"""
    validator = APIEndpointValidator()
    
    print("🔍 Starting API Endpoint Validation...")
    print(f"📡 Testing {len(validator.endpoints)} endpoints...")
    
    # Run validation
    report = await validator.validate_all_endpoints(parallel_limit=5)
    
    # Print summary
    print(f"\n📊 Validation Summary:")
    print(f"✅ Passed: {report.passed}")
    print(f"❌ Failed: {report.failed}")  
    print(f"🔥 Errors: {report.errors}")
    print(f"⏰ Timeouts: {report.timeouts}")
    print(f"📈 Coverage: {report.coverage_percentage:.1f}%")
    print(f"⚡ Performance Score: {report.performance_score:.1f}")
    print(f"🕒 Total Time: {report.total_time:.2f} seconds")
    
    # Show failed endpoints
    failed_results = [r for r in report.results if r.status != ValidationStatus.PASS]
    if failed_results:
        print(f"\n⚠️ Issues Found:")
        for result in failed_results:
            print(f"  {result.status.value.upper()}: {result.endpoint_name} - {result.error_message}")
    
    # Generate HTML report
    html_report = validator.generate_html_report(report)
    report_path = f"api_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    
    with open(report_path, 'w') as f:
        f.write(html_report)
    
    print(f"\n📄 HTML report saved: {report_path}")
    return report

if __name__ == "__main__":
    asyncio.run(main())