#!/usr/bin/env python3

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import uvicorn
import subprocess
import threading
import time

# Add audit modules to path
sys.path.append(str(Path(__file__).parent))

from health.service_health_checker import ServiceHealthChecker
from api.api_endpoint_validator import APIEndpointValidator  
from database.database_integrity_checker import DatabaseIntegrityChecker
from payments.payment_flow_tester import PaymentFlowTester

app = FastAPI(title="ActiveLog Audit Dashboard", version="1.0.0")

class AuditOrchestrator:
    def __init__(self):
        self.health_checker = ServiceHealthChecker()
        self.api_validator = APIEndpointValidator()
        self.db_checker = DatabaseIntegrityChecker()
        self.payment_tester = PaymentFlowTester()
        
        # Status tracking
        self.last_health_check = None
        self.last_api_validation = None
        self.last_db_integrity = None
        self.last_payment_test = None
        
        # Background task flags
        self.health_monitoring_active = False

    async def run_comprehensive_audit(self):
        """Run all audit tools and generate comprehensive report"""
        print("🔍 Starting Comprehensive ActiveLog Audit...")
        start_time = time.time()
        
        results = {}
        
        try:
            # 1. Service Health Check
            print("📡 Running service health checks...")
            health_report = self.health_checker.check_all_services()
            self.last_health_check = datetime.now()
            results['health'] = {
                'status': 'completed',
                'services_checked': health_report.services_checked,
                'healthy_services': health_report.healthy_services,
                'failed_services': health_report.failed_services,
                'total_issues': health_report.total_issues,
                'timestamp': health_report.timestamp
            }
            
            # 2. API Endpoint Validation
            print("🔗 Running API endpoint validation...")
            api_report = await self.api_validator.validate_all_endpoints()
            self.last_api_validation = datetime.now()
            results['api'] = {
                'status': 'completed',
                'total_endpoints': api_report.total_endpoints,
                'passed': api_report.passed,
                'failed': api_report.failed,
                'errors': api_report.errors,
                'coverage_percentage': api_report.coverage_percentage,
                'timestamp': api_report.timestamp
            }
            
            # 3. Database Integrity Check
            print("🗃️ Running database integrity checks...")
            db_report = self.db_checker.run_comprehensive_check()
            self.last_db_integrity = datetime.now()
            results['database'] = {
                'status': 'completed',
                'databases_checked': db_report.databases_checked,
                'total_issues': db_report.total_issues,
                'critical_issues': db_report.critical_issues,
                'warnings': db_report.warnings,
                'total_size_mb': db_report.total_size_mb,
                'timestamp': db_report.timestamp
            }
            
            # 4. Payment Flow Testing
            print("💳 Running payment flow tests...")
            payment_report = await self.payment_tester.run_all_payment_tests()
            self.last_payment_test = datetime.now()
            results['payments'] = {
                'status': 'completed',
                'total_tests': payment_report.total_tests,
                'passed': payment_report.passed,
                'failed': payment_report.failed,
                'errors': payment_report.errors,
                'total_amount_tested': float(payment_report.total_amount_tested),
                'average_processing_time': payment_report.average_processing_time,
                'timestamp': payment_report.timestamp
            }
            
        except Exception as e:
            print(f"❌ Audit error: {e}")
            results['error'] = str(e)
        
        audit_duration = time.time() - start_time
        results['audit_summary'] = {
            'duration': audit_duration,
            'completed_checks': len([k for k, v in results.items() if isinstance(v, dict) and v.get('status') == 'completed']),
            'timestamp': datetime.now()
        }
        
        print(f"✅ Comprehensive audit completed in {audit_duration:.2f} seconds")
        return results

    def start_health_monitoring(self):
        """Start continuous health monitoring"""
        def monitor_loop():
            while self.health_monitoring_active:
                try:
                    self.health_checker.check_all_services()
                    self.last_health_check = datetime.now()
                    time.sleep(60)  # Check every minute
                except Exception as e:
                    print(f"Health monitoring error: {e}")
                    time.sleep(10)
        
        if not self.health_monitoring_active:
            self.health_monitoring_active = True
            monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
            monitor_thread.start()
            print("🔄 Started continuous health monitoring")

    def stop_health_monitoring(self):
        """Stop continuous health monitoring"""
        self.health_monitoring_active = False
        print("⏹️ Stopped health monitoring")

# Global orchestrator
orchestrator = AuditOrchestrator()

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Main audit dashboard"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ActiveLog Audit Dashboard</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                margin: 0; padding: 20px; background: #f8f9fa; 
            }
            .container { 
                max-width: 1400px; margin: 0 auto; background: white; 
                padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
            }
            h1 { color: #343a40; margin-bottom: 30px; text-align: center; }
            .tools-grid { 
                display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
                gap: 20px; margin-bottom: 30px; 
            }
            .tool-card { 
                background: #fff; border: 1px solid #dee2e6; border-radius: 8px; 
                padding: 20px; transition: transform 0.2s; 
            }
            .tool-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
            .tool-title { font-size: 1.2em; font-weight: bold; margin-bottom: 10px; color: #495057; }
            .tool-description { color: #6c757d; margin-bottom: 15px; line-height: 1.5; }
            .btn { 
                display: inline-block; padding: 10px 20px; background: #007bff; 
                color: white; text-decoration: none; border-radius: 5px; border: none;
                cursor: pointer; font-size: 0.9em; transition: background 0.2s;
            }
            .btn:hover { background: #0056b3; }
            .btn-success { background: #28a745; }
            .btn-success:hover { background: #1e7e34; }
            .btn-danger { background: #dc3545; }
            .btn-danger:hover { background: #c82333; }
            .status-indicator { 
                display: inline-block; width: 12px; height: 12px; border-radius: 50%; 
                margin-right: 8px; 
            }
            .status-healthy { background: #28a745; }
            .status-warning { background: #ffc107; }
            .status-critical { background: #dc3545; }
            .actions { margin-top: 30px; text-align: center; }
            .actions button { margin: 0 10px; }
            #status { margin-top: 20px; padding: 15px; border-radius: 5px; display: none; }
            .status-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .status-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔍 ActiveLog Audit Dashboard</h1>
            <p style="text-align: center; color: #6c757d; margin-bottom: 30px;">
                Comprehensive audit and monitoring suite for the ActiveLog ecosystem
            </p>
            
            <div class="tools-grid">
                <div class="tool-card">
                    <div class="tool-title">
                        <span class="status-indicator status-healthy"></span>
                        Service Health Checker
                    </div>
                    <div class="tool-description">
                        Monitor all ActiveLog services, check endpoints, and track system metrics
                    </div>
                    <button class="btn" onclick="runTool('health')">Run Health Check</button>
                    <a href="/health/report" class="btn">View Report</a>
                </div>
                
                <div class="tool-card">
                    <div class="tool-title">
                        <span class="status-indicator status-warning"></span>
                        API Endpoint Validator
                    </div>
                    <div class="tool-description">
                        Validate API endpoints across all services and check response integrity
                    </div>
                    <button class="btn" onclick="runTool('api')">Run API Tests</button>
                    <a href="/api/report" class="btn">View Report</a>
                </div>
                
                <div class="tool-card">
                    <div class="tool-title">
                        <span class="status-indicator status-healthy"></span>
                        Database Integrity
                    </div>
                    <div class="tool-description">
                        Scan all databases for corruption, performance issues, and data consistency
                    </div>
                    <button class="btn" onclick="runTool('database')">Check Databases</button>
                    <a href="/database/report" class="btn">View Report</a>
                </div>
                
                <div class="tool-card">
                    <div class="tool-title">
                        <span class="status-indicator status-healthy"></span>
                        Payment Flow Tester
                    </div>
                    <div class="tool-description">
                        Test payment processing flows and transaction handling across all methods
                    </div>
                    <button class="btn" onclick="runTool('payments')">Test Payments</button>
                    <a href="/payments/report" class="btn">View Report</a>
                </div>
            </div>
            
            <div class="actions">
                <button class="btn btn-success" onclick="runComprehensiveAudit()" id="auditBtn">
                    🚀 Run Comprehensive Audit
                </button>
                <button class="btn" onclick="startMonitoring()" id="monitorBtn">
                    🔄 Start Monitoring
                </button>
                <button class="btn btn-danger" onclick="stopMonitoring()" id="stopBtn" style="display: none;">
                    ⏹️ Stop Monitoring
                </button>
            </div>
            
            <div id="status"></div>
        </div>
        
        <script>
            async function runTool(tool) {
                const statusDiv = document.getElementById('status');
                statusDiv.style.display = 'block';
                statusDiv.className = 'status-success';
                statusDiv.textContent = `Running ${tool} audit...`;
                
                try {
                    const response = await fetch(`/audit/${tool}`, { method: 'POST' });
                    const result = await response.json();
                    
                    if (response.ok) {
                        statusDiv.textContent = `${tool} audit completed successfully!`;
                        setTimeout(() => {
                            statusDiv.style.display = 'none';
                        }, 3000);
                    } else {
                        throw new Error(result.detail || 'Audit failed');
                    }
                } catch (error) {
                    statusDiv.className = 'status-error';
                    statusDiv.textContent = `Error running ${tool} audit: ${error.message}`;
                }
            }
            
            async function runComprehensiveAudit() {
                const btn = document.getElementById('auditBtn');
                const statusDiv = document.getElementById('status');
                
                btn.disabled = true;
                btn.textContent = '🔄 Running Comprehensive Audit...';
                statusDiv.style.display = 'block';
                statusDiv.className = 'status-success';
                statusDiv.textContent = 'Starting comprehensive audit of all systems...';
                
                try {
                    const response = await fetch('/audit/comprehensive', { method: 'POST' });
                    const result = await response.json();
                    
                    if (response.ok) {
                        statusDiv.textContent = `Comprehensive audit completed! Duration: ${result.audit_summary.duration.toFixed(2)}s`;
                        setTimeout(() => {
                            statusDiv.style.display = 'none';
                        }, 5000);
                    } else {
                        throw new Error(result.detail || 'Comprehensive audit failed');
                    }
                } catch (error) {
                    statusDiv.className = 'status-error';
                    statusDiv.textContent = `Error running comprehensive audit: ${error.message}`;
                } finally {
                    btn.disabled = false;
                    btn.textContent = '🚀 Run Comprehensive Audit';
                }
            }
            
            async function startMonitoring() {
                const response = await fetch('/monitoring/start', { method: 'POST' });
                if (response.ok) {
                    document.getElementById('monitorBtn').style.display = 'none';
                    document.getElementById('stopBtn').style.display = 'inline-block';
                    
                    const statusDiv = document.getElementById('status');
                    statusDiv.style.display = 'block';
                    statusDiv.className = 'status-success';
                    statusDiv.textContent = 'Continuous health monitoring started!';
                    setTimeout(() => statusDiv.style.display = 'none', 3000);
                }
            }
            
            async function stopMonitoring() {
                const response = await fetch('/monitoring/stop', { method: 'POST' });
                if (response.ok) {
                    document.getElementById('monitorBtn').style.display = 'inline-block';
                    document.getElementById('stopBtn').style.display = 'none';
                    
                    const statusDiv = document.getElementById('status');
                    statusDiv.style.display = 'block';
                    statusDiv.className = 'status-success';
                    statusDiv.textContent = 'Health monitoring stopped.';
                    setTimeout(() => statusDiv.style.display = 'none', 3000);
                }
            }
            
            // Auto-refresh status indicators every 30 seconds
            setInterval(async () => {
                try {
                    const response = await fetch('/status');
                    const status = await response.json();
                    // Update status indicators based on response
                } catch (error) {
                    console.log('Status update error:', error);
                }
            }, 30000);
        </script>
    </body>
    </html>
    """

@app.post("/audit/comprehensive")
async def run_comprehensive_audit():
    """Run comprehensive audit of all systems"""
    try:
        results = await orchestrator.run_comprehensive_audit()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/audit/{tool}")
async def run_individual_audit(tool: str):
    """Run individual audit tool"""
    try:
        if tool == "health":
            report = orchestrator.health_checker.check_all_services()
            orchestrator.last_health_check = datetime.now()
            return {"status": "completed", "report": "Health check completed"}
        
        elif tool == "api":
            report = await orchestrator.api_validator.validate_all_endpoints()
            orchestrator.last_api_validation = datetime.now()
            return {"status": "completed", "report": "API validation completed"}
        
        elif tool == "database":
            report = orchestrator.db_checker.run_comprehensive_check()
            orchestrator.last_db_integrity = datetime.now()
            return {"status": "completed", "report": "Database integrity check completed"}
        
        elif tool == "payments":
            report = await orchestrator.payment_tester.run_all_payment_tests()
            orchestrator.last_payment_test = datetime.now()
            return {"status": "completed", "report": "Payment flow tests completed"}
        
        else:
            raise HTTPException(status_code=400, detail="Unknown audit tool")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/monitoring/start")
async def start_monitoring():
    """Start continuous health monitoring"""
    orchestrator.start_health_monitoring()
    return {"status": "monitoring_started"}

@app.post("/monitoring/stop")
async def stop_monitoring():
    """Stop continuous health monitoring"""
    orchestrator.stop_health_monitoring()
    return {"status": "monitoring_stopped"}

@app.get("/status")
async def get_status():
    """Get current audit status"""
    return {
        "last_health_check": orchestrator.last_health_check.isoformat() if orchestrator.last_health_check else None,
        "last_api_validation": orchestrator.last_api_validation.isoformat() if orchestrator.last_api_validation else None,
        "last_db_integrity": orchestrator.last_db_integrity.isoformat() if orchestrator.last_db_integrity else None,
        "last_payment_test": orchestrator.last_payment_test.isoformat() if orchestrator.last_payment_test else None,
        "health_monitoring_active": orchestrator.health_monitoring_active
    }

@app.get("/health/report")
async def get_health_report():
    """Get latest health check report"""
    report = orchestrator.health_checker.check_all_services()
    html_report = orchestrator.health_checker.generate_html_report(report)
    return HTMLResponse(content=html_report)

@app.get("/api/report")
async def get_api_report():
    """Get latest API validation report"""
    report = await orchestrator.api_validator.validate_all_endpoints()
    html_report = orchestrator.api_validator.generate_html_report(report)
    return HTMLResponse(content=html_report)

@app.get("/database/report")
async def get_database_report():
    """Get latest database integrity report"""
    report = orchestrator.db_checker.run_comprehensive_check()
    html_report = orchestrator.db_checker.generate_html_report(report)
    return HTMLResponse(content=html_report)

@app.get("/payments/report")
async def get_payments_report():
    """Get latest payment flow report"""
    report = await orchestrator.payment_tester.run_all_payment_tests()
    html_report = orchestrator.payment_tester.generate_html_report(report)
    return HTMLResponse(content=html_report)

def main():
    """Run the audit dashboard"""
    print("🔍 Starting ActiveLog Audit Dashboard...")
    print("📊 Dashboard URL: http://localhost:8399")
    print("🚀 Access comprehensive audit tools at the dashboard")
    
    # Start the audit dashboard server
    uvicorn.run(app, host="0.0.0.0", port=8399, log_level="info")

if __name__ == "__main__":
    main()