import asyncio
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks, File, UploadFile, Form
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import sqlite3

from automatic_detection import AutomaticDetection, InterfaceType, DetectedDevice
from manual_configuration import ManualConfigurationWizard, WizardStep, ValidationError
from bulk_provisioning import BulkProvisioning, ProvisioningMethod, DeviceTemplate, DeviceGroup

# Database setup
DATABASE_PATH = "hardware_wizard.db"

def init_database():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Discovery sessions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS discovery_sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            interfaces TEXT,
            devices_found INTEGER DEFAULT 0,
            devices_onboarded INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            results JSON
        )
    """)
    
    # Manual configuration sessions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS config_sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            device_name TEXT NOT NULL,
            current_step TEXT,
            completed_steps TEXT,
            step_data JSON,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    """)
    
    # Bulk provisioning jobs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS provisioning_jobs (
            job_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            method TEXT NOT NULL,
            device_count INTEGER,
            created_by TEXT,
            status TEXT DEFAULT 'pending',
            progress REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            results JSON
        )
    """)
    
    # Registered devices
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS registered_devices (
            device_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT,
            interface TEXT,
            manufacturer TEXT,
            model TEXT,
            driver_name TEXT,
            configuration JSON,
            groups TEXT,
            status TEXT DEFAULT 'active',
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP
        )
    """)
    
    # Device templates
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS device_templates (
            template_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT,
            interface TEXT,
            default_config JSON,
            driver_info JSON,
            tags TEXT,
            description TEXT,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            usage_count INTEGER DEFAULT 0
        )
    """)
    
    # Usage analytics
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usage_analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            user_id TEXT,
            session_id TEXT,
            device_id TEXT,
            metadata JSON,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

# Global instances
auto_detection = AutomaticDetection()
manual_wizard = ManualConfigurationWizard()
bulk_provisioning = BulkProvisioning()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting Hardware Wizard Service...")
    init_database()
    
    # Register callbacks for analytics
    def log_discovery_event(device):
        log_analytics("device_discovered", metadata={
            "device_id": device.device_id,
            "interface": device.interface.value,
            "manufacturer": device.manufacturer
        })
    
    def log_onboarding_complete(session):
        log_analytics("device_onboarded", metadata={
            "session_id": session.session_id,
            "device_id": session.device.device_id
        })
    
    def log_manual_step_complete(session_id, step, data):
        log_analytics("manual_step_completed", metadata={
            "session_id": session_id,
            "step": step.value
        })
    
    def log_bulk_job_complete(job_id, job):
        log_analytics("bulk_job_completed", metadata={
            "job_id": job_id,
            "method": job.method.value,
            "device_count": len(job.devices)
        })
    
    auto_detection.register_callback("device_found", log_discovery_event)
    auto_detection.register_callback("session_updated", log_onboarding_complete)
    manual_wizard.register_callback("step_completed", log_manual_step_complete)
    bulk_provisioning.register_callback("job_completed", log_bulk_job_complete)
    
    print("Hardware Wizard Service started successfully")
    print(f"Database: {DATABASE_PATH}")
    print("Available features:")
    print("  - Automatic Device Detection")
    print("  - Manual Configuration Wizard")
    print("  - Bulk Device Provisioning")
    print("  - QR Code Generation")
    print("  - Template Management")
    
    yield
    
    # Shutdown
    print("Shutting down Hardware Wizard Service...")

app = FastAPI(
    title="Hardware Wizard Service",
    description="Comprehensive device onboarding and configuration platform",
    version="1.0.0",
    lifespan=lifespan
)

# Create static directories
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

def log_analytics(event_type: str, user_id: str = None, session_id: str = None, device_id: str = None, metadata: Dict[str, Any] = None):
    """Log analytics event"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO usage_analytics (event_type, user_id, session_id, device_id, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (event_type, user_id, session_id, device_id, json.dumps(metadata or {})))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Analytics logging error: {e}")

# Pydantic models
class DiscoveryRequest(BaseModel):
    user_id: str
    interfaces: List[str] = ["usb", "serial", "ethernet", "i2c"]

class OnboardingRequest(BaseModel):
    device_id: str
    user_id: str

class ConfigSessionCreate(BaseModel):
    user_id: str
    device_name: str

class StepSubmission(BaseModel):
    step_data: Dict[str, Any]

class CSVJobCreate(BaseModel):
    name: str
    created_by: str

class QRJobCreate(BaseModel):
    name: str
    devices: List[Dict[str, Any]]
    created_by: str

class TemplateJobCreate(BaseModel):
    name: str
    template_id: str
    device_list: List[Dict[str, Any]]
    created_by: str

class TemplateCreate(BaseModel):
    name: str
    category: str
    interface: str
    default_config: Dict[str, Any]
    driver_info: Dict[str, Any]
    tags: List[str]
    description: str
    created_by: str

class GroupCreate(BaseModel):
    name: str
    description: str
    policies: Dict[str, Any]
    tags: List[str] = []

# Root endpoint with dashboard
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Hardware Wizard - Device Onboarding Platform</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f8f9fa; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 15px; margin-bottom: 30px; text-align: center; }
            .features { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 25px; margin-bottom: 30px; }
            .feature-card { background: white; padding: 25px; border-radius: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.08); transition: transform 0.3s; }
            .feature-card:hover { transform: translateY(-5px); }
            .feature-title { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; margin-bottom: 20px; font-size: 1.3em; }
            .endpoint { background: #ecf0f1; padding: 10px 15px; margin: 8px 0; border-radius: 8px; font-family: monospace; font-size: 0.9em; }
            .get { border-left: 5px solid #27ae60; }
            .post { border-left: 5px solid #3498db; }
            .put { border-left: 5px solid #f39c12; }
            .delete { border-left: 5px solid #e74c3c; }
            .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 20px; margin-bottom: 30px; }
            .stat-card { background: white; padding: 20px; border-radius: 15px; text-align: center; box-shadow: 0 3px 10px rgba(0,0,0,0.1); }
            .stat-number { font-size: 2.5em; font-weight: bold; color: #3498db; margin-bottom: 5px; }
            .stat-label { color: #7f8c8d; font-size: 0.9em; }
            .demo-section { background: white; padding: 25px; border-radius: 15px; margin-bottom: 20px; box-shadow: 0 5px 15px rgba(0,0,0,0.08); }
            .demo-button { background: #3498db; color: white; border: none; padding: 12px 25px; border-radius: 8px; cursor: pointer; margin: 5px; font-size: 0.9em; }
            .demo-button:hover { background: #2980b9; }
            .icon { font-size: 2em; margin-bottom: 15px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🧙‍♂️ Hardware Wizard</h1>
                <p>Comprehensive Device Onboarding & Configuration Platform</p>
                <p><strong>Automatic Detection • Manual Configuration • Bulk Provisioning</strong></p>
            </div>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number" id="discovery-sessions">0</div>
                    <div class="stat-label">Discovery Sessions</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="config-sessions">0</div>
                    <div class="stat-label">Config Sessions</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="provisioning-jobs">0</div>
                    <div class="stat-label">Provisioning Jobs</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="registered-devices">0</div>
                    <div class="stat-label">Registered Devices</div>
                </div>
            </div>
            
            <div class="features">
                <div class="feature-card">
                    <div class="icon">🔍</div>
                    <h3 class="feature-title">Automatic Detection</h3>
                    <p>Scan interfaces, identify devices, download drivers, and configure automatically</p>
                    <div class="endpoint post">POST /api/discovery/start - Start device discovery</div>
                    <div class="endpoint get">GET /api/discovery/{session_id} - Get discovery results</div>
                    <div class="endpoint post">POST /api/onboard/auto - Auto-onboard device</div>
                    <div class="endpoint get">GET /api/devices/registered - List registered devices</div>
                </div>
                
                <div class="feature-card">
                    <div class="icon">⚙️</div>
                    <h3 class="feature-title">Manual Configuration</h3>
                    <p>Step-by-step wizard with visual guides and troubleshooting</p>
                    <div class="endpoint post">POST /api/config/session - Create config session</div>
                    <div class="endpoint get">GET /api/config/{session_id}/step - Get current step</div>
                    <div class="endpoint post">POST /api/config/{session_id}/submit - Submit step data</div>
                    <div class="endpoint get">GET /api/config/{session_id}/test - Test device connection</div>
                </div>
                
                <div class="feature-card">
                    <div class="icon">📦</div>
                    <h3 class="feature-title">Bulk Provisioning</h3>
                    <p>CSV import, QR codes, templates, and batch operations</p>
                    <div class="endpoint post">POST /api/bulk/csv - Create CSV import job</div>
                    <div class="endpoint post">POST /api/bulk/qr - Create QR batch job</div>
                    <div class="endpoint post">POST /api/bulk/template - Create template job</div>
                    <div class="endpoint post">POST /api/bulk/execute/{job_id} - Execute job</div>
                </div>
                
                <div class="feature-card">
                    <div class="icon">🏷️</div>
                    <h3 class="feature-title">Templates & Groups</h3>
                    <p>Device templates, group management, and policy inheritance</p>
                    <div class="endpoint get">GET /api/templates - List templates</div>
                    <div class="endpoint post">POST /api/templates - Create template</div>
                    <div class="endpoint get">GET /api/groups - List device groups</div>
                    <div class="endpoint post">POST /api/groups - Create group</div>
                </div>
                
                <div class="feature-card">
                    <div class="icon">🔧</div>
                    <h3 class="feature-title">Community & Custom</h3>
                    <p>Community drivers, custom protocols, and troubleshooting</p>
                    <div class="endpoint get">GET /api/community/drivers - Search community drivers</div>
                    <div class="endpoint post">POST /api/protocol/builder - Build custom protocol</div>
                    <div class="endpoint post">POST /api/troubleshooting - Get troubleshooting help</div>
                </div>
                
                <div class="feature-card">
                    <div class="icon">📊</div>
                    <h3 class="feature-title">Analytics & Monitoring</h3>
                    <p>Usage analytics, performance metrics, and system status</p>
                    <div class="endpoint get">GET /api/analytics/summary - Usage analytics</div>
                    <div class="endpoint get">GET /api/system/status - System status</div>
                    <div class="endpoint get">GET /api/system/metrics - Performance metrics</div>
                </div>
            </div>
            
            <div class="demo-section">
                <h3>🚀 Quick Start Demo</h3>
                <p>Try out the Hardware Wizard features with these interactive demos:</p>
                <button class="demo-button" onclick="startDiscovery()">Start Device Discovery</button>
                <button class="demo-button" onclick="createConfigSession()">Manual Configuration</button>
                <button class="demo-button" onclick="showTemplates()">View Templates</button>
                <button class="demo-button" onclick="showAnalytics()">View Analytics</button>
            </div>
        </div>
        
        <script>
            // Load dashboard statistics
            async function loadStats() {
                try {
                    const [sessions, configs, jobs, devices] = await Promise.all([
                        fetch('/api/discovery/sessions').then(r => r.json()),
                        fetch('/api/config/sessions').then(r => r.json()),
                        fetch('/api/bulk/jobs').then(r => r.json()),
                        fetch('/api/devices/registered').then(r => r.json())
                    ]);
                    
                    document.getElementById('discovery-sessions').textContent = sessions.length || 0;
                    document.getElementById('config-sessions').textContent = configs.length || 0;
                    document.getElementById('provisioning-jobs').textContent = jobs.length || 0;
                    document.getElementById('registered-devices').textContent = devices.length || 0;
                } catch (error) {
                    console.error('Failed to load statistics:', error);
                }
            }
            
            // Demo functions
            async function startDiscovery() {
                try {
                    const response = await fetch('/api/discovery/start', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ user_id: 'demo_user', interfaces: ['usb', 'serial'] })
                    });
                    const result = await response.json();
                    alert(`Discovery started! Session ID: ${result.session_id}`);
                } catch (error) {
                    alert('Demo discovery failed: ' + error);
                }
            }
            
            async function createConfigSession() {
                try {
                    const response = await fetch('/api/config/session', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ user_id: 'demo_user', device_name: 'Demo Device' })
                    });
                    const result = await response.json();
                    alert(`Configuration session created! Session ID: ${result.session_id}`);
                } catch (error) {
                    alert('Demo config session failed: ' + error);
                }
            }
            
            async function showTemplates() {
                try {
                    const response = await fetch('/api/templates');
                    const templates = await response.json();
                    alert(`Available templates: ${templates.map(t => t.name).join(', ')}`);
                } catch (error) {
                    alert('Failed to load templates: ' + error);
                }
            }
            
            async function showAnalytics() {
                try {
                    const response = await fetch('/api/analytics/summary');
                    const analytics = await response.json();
                    alert(`Total events: ${analytics.total_events}, Most common: ${analytics.top_events[0]?.event_type || 'none'}`);
                } catch (error) {
                    alert('Failed to load analytics: ' + error);
                }
            }
            
            // Load initial stats
            loadStats();
            setInterval(loadStats, 30000); // Refresh every 30 seconds
        </script>
    </body>
    </html>
    """
    return html_content

# Automatic Detection Endpoints
@app.post("/api/discovery/start")
async def start_discovery(request: DiscoveryRequest, background_tasks: BackgroundTasks):
    """Start automatic device discovery"""
    try:
        # Convert interface strings to enum
        interfaces = []
        for interface_str in request.interfaces:
            try:
                interfaces.append(InterfaceType(interface_str.lower()))
            except ValueError:
                continue
        
        if not interfaces:
            interfaces = [InterfaceType.USB, InterfaceType.SERIAL, InterfaceType.ETHERNET]
        
        # Start discovery
        devices = await auto_detection.start_discovery(interfaces)
        
        # Save session to database
        session_id = f"discovery_{int(datetime.now().timestamp() * 1000)}"
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO discovery_sessions (session_id, user_id, interfaces, devices_found, results)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, request.user_id, json.dumps(request.interfaces), 
              len(devices), json.dumps([asdict(device) for device in devices], default=str)))
        conn.commit()
        conn.close()
        
        log_analytics("discovery_started", request.user_id, session_id, metadata={
            "interfaces": request.interfaces,
            "devices_found": len(devices)
        })
        
        return {
            "session_id": session_id,
            "devices_found": len(devices),
            "devices": [asdict(device) for device in devices],
            "message": f"Found {len(devices)} devices"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/discovery/{session_id}")
async def get_discovery_results(session_id: str):
    """Get discovery session results"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM discovery_sessions WHERE session_id = ?", (session_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            raise HTTPException(status_code=404, detail="Discovery session not found")
        
        return {
            "session_id": result[0],
            "user_id": result[1],
            "interfaces": json.loads(result[2]),
            "devices_found": result[3],
            "devices_onboarded": result[4],
            "status": result[5],
            "created_at": result[6],
            "completed_at": result[7],
            "results": json.loads(result[8]) if result[8] else []
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/discovery/sessions")
async def list_discovery_sessions():
    """List discovery sessions"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT session_id, user_id, devices_found, status, created_at FROM discovery_sessions ORDER BY created_at DESC LIMIT 50")
        sessions = cursor.fetchall()
        conn.close()
        
        return [
            {
                "session_id": s[0],
                "user_id": s[1],
                "devices_found": s[2],
                "status": s[3],
                "created_at": s[4]
            }
            for s in sessions
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/onboard/auto")
async def auto_onboard_device(request: OnboardingRequest, background_tasks: BackgroundTasks):
    """Start automatic device onboarding"""
    try:
        # Create a dummy detected device for demo
        device = DetectedDevice(
            device_id=request.device_id,
            interface=InterfaceType.USB,
            address="auto",
            manufacturer="Unknown",
            model="Auto Device"
        )
        
        # Start onboarding
        session = await auto_detection.onboard_device(device)
        
        log_analytics("auto_onboarding_started", request.user_id, session.session_id, request.device_id)
        
        return {
            "session_id": session.session_id,
            "device_id": request.device_id,
            "status": session.status.value,
            "current_step": session.current_step,
            "message": "Automatic onboarding started"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Manual Configuration Endpoints
@app.post("/api/config/session")
async def create_config_session(request: ConfigSessionCreate):
    """Create manual configuration session"""
    try:
        session_id = manual_wizard.create_session(request.user_id, request.device_name)
        
        # Save to database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO config_sessions (session_id, user_id, device_name, current_step)
            VALUES (?, ?, ?, ?)
        """, (session_id, request.user_id, request.device_name, "device_type"))
        conn.commit()
        conn.close()
        
        log_analytics("config_session_created", request.user_id, session_id)
        
        return {
            "session_id": session_id,
            "device_name": request.device_name,
            "message": "Configuration session created"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/config/{session_id}/step")
async def get_current_step(session_id: str):
    """Get current configuration step"""
    try:
        session = manual_wizard.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        step_def = manual_wizard.get_current_step(session_id)
        if not step_def:
            raise HTTPException(status_code=404, detail="Step definition not found")
        
        return {
            "session_id": session_id,
            "current_step": session.current_step.value,
            "completed_steps": [s.value for s in session.completed_steps],
            "step_definition": {
                "title": step_def.title,
                "description": step_def.description,
                "fields": step_def.fields,
                "help_content": step_def.help_content,
                "estimated_time": step_def.estimated_time,
                "skippable": step_def.skippable
            },
            "validation_errors": [asdict(error) for error in session.validation_errors]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/config/{session_id}/submit")
async def submit_step(session_id: str, submission: StepSubmission):
    """Submit step data"""
    try:
        result = manual_wizard.submit_step(session_id, submission.step_data)
        
        # Update database
        session = manual_wizard.get_session(session_id)
        if session:
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE config_sessions 
                SET current_step = ?, completed_steps = ?, step_data = ?, 
                    completed_at = CASE WHEN ? = 'complete' THEN CURRENT_TIMESTAMP ELSE completed_at END
                WHERE session_id = ?
            """, (session.current_step.value, 
                  json.dumps([s.value for s in session.completed_steps]),
                  json.dumps({k.value: v for k, v in session.step_data.items()}, default=str),
                  session.current_step.value, session_id))
            conn.commit()
            conn.close()
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/config/{session_id}/test")
async def test_device_connection(session_id: str):
    """Test device connection"""
    try:
        result = manual_wizard.test_device_connection(session_id)
        
        log_analytics("device_test", session_id=session_id, metadata={
            "success": result["success"]
        })
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/config/sessions")
async def list_config_sessions():
    """List configuration sessions"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT session_id, user_id, device_name, current_step, status, created_at FROM config_sessions ORDER BY created_at DESC LIMIT 50")
        sessions = cursor.fetchall()
        conn.close()
        
        return [
            {
                "session_id": s[0],
                "user_id": s[1],
                "device_name": s[2],
                "current_step": s[3],
                "status": s[4],
                "created_at": s[5]
            }
            for s in sessions
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Bulk Provisioning Endpoints
@app.post("/api/bulk/csv")
async def create_csv_job(request: CSVJobCreate, csv_file: UploadFile = File(...)):
    """Create CSV import provisioning job"""
    try:
        # Read CSV content
        csv_content = await csv_file.read()
        csv_text = csv_content.decode('utf-8')
        
        # Create job
        result = bulk_provisioning.create_csv_job(request.name, csv_text, request.created_by)
        
        if result["success"]:
            job_id = result["job_id"]
            
            # Save to database
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO provisioning_jobs (job_id, name, method, device_count, created_by)
                VALUES (?, ?, ?, ?, ?)
            """, (job_id, request.name, "csv_import", result["device_count"], request.created_by))
            conn.commit()
            conn.close()
            
            log_analytics("csv_job_created", request.created_by, metadata={
                "job_id": job_id,
                "device_count": result["device_count"]
            })
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/bulk/qr")
async def create_qr_job(request: QRJobCreate):
    """Create QR code batch provisioning job"""
    try:
        result = bulk_provisioning.create_qr_batch_job(request.name, request.devices, request.created_by)
        
        if result["success"]:
            job_id = result["job_id"]
            
            # Save to database
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO provisioning_jobs (job_id, name, method, device_count, created_by, results)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (job_id, request.name, "qr_code_scan", result["device_count"], 
                  request.created_by, json.dumps({"qr_codes": result["qr_codes"]}, default=str)))
            conn.commit()
            conn.close()
            
            log_analytics("qr_job_created", request.created_by, metadata={
                "job_id": job_id,
                "device_count": result["device_count"]
            })
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/bulk/template")
async def create_template_job(request: TemplateJobCreate):
    """Create template-based provisioning job"""
    try:
        result = bulk_provisioning.create_template_job(
            request.name, request.template_id, request.device_list, request.created_by
        )
        
        if result["success"]:
            job_id = result["job_id"]
            
            # Save to database
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO provisioning_jobs (job_id, name, method, device_count, created_by)
                VALUES (?, ?, ?, ?, ?)
            """, (job_id, request.name, "template_clone", result["device_count"], request.created_by))
            conn.commit()
            conn.close()
            
            log_analytics("template_job_created", request.created_by, metadata={
                "job_id": job_id,
                "template_id": request.template_id,
                "device_count": result["device_count"]
            })
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/bulk/execute/{job_id}")
async def execute_provisioning_job(job_id: str, background_tasks: BackgroundTasks):
    """Execute provisioning job"""
    try:
        # Execute in background
        background_tasks.add_task(execute_job_async, job_id)
        
        return {
            "success": True,
            "job_id": job_id,
            "message": "Job execution started"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def execute_job_async(job_id: str):
    """Execute job asynchronously"""
    try:
        result = await bulk_provisioning.execute_job(job_id)
        
        # Update database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE provisioning_jobs 
            SET status = ?, progress = 100.0, completed_at = CURRENT_TIMESTAMP, results = ?
            WHERE job_id = ?
        """, ("completed" if result["success"] else "failed", 
              json.dumps(result, default=str), job_id))
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Job execution error: {e}")

@app.get("/api/bulk/jobs")
async def list_provisioning_jobs():
    """List provisioning jobs"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM provisioning_jobs ORDER BY created_at DESC LIMIT 50")
        jobs = cursor.fetchall()
        conn.close()
        
        return [
            {
                "job_id": job[0],
                "name": job[1],
                "method": job[2],
                "device_count": job[3],
                "created_by": job[4],
                "status": job[5],
                "progress": job[6],
                "created_at": job[7],
                "started_at": job[8],
                "completed_at": job[9]
            }
            for job in jobs
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/bulk/job/{job_id}/status")
async def get_job_status(job_id: str):
    """Get job status"""
    try:
        status = bulk_provisioning.get_job_status(job_id)
        if not status:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return status
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Template Management Endpoints
@app.get("/api/templates")
async def list_templates(category: str = None, interface: str = None):
    """List device templates"""
    try:
        templates = bulk_provisioning.get_template_manager().list_templates(category, interface)
        return [asdict(template) for template in templates]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/templates")
async def create_template(request: TemplateCreate):
    """Create device template"""
    try:
        template = DeviceTemplate(
            template_id=f"custom_{int(datetime.now().timestamp())}",
            name=request.name,
            category=request.category,
            interface=request.interface,
            default_config=request.default_config,
            driver_info=request.driver_info,
            tags=request.tags,
            description=request.description,
            created_by=request.created_by,
            created_at=datetime.now()
        )
        
        success = bulk_provisioning.get_template_manager().create_template(template)
        
        if success:
            # Save to database
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO device_templates (template_id, name, category, interface, default_config, driver_info, tags, description, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (template.template_id, template.name, template.category, template.interface,
                  json.dumps(template.default_config), json.dumps(template.driver_info),
                  json.dumps(template.tags), template.description, template.created_by))
            conn.commit()
            conn.close()
            
            log_analytics("template_created", request.created_by, metadata={
                "template_id": template.template_id,
                "category": request.category
            })
            
            return {"success": True, "template_id": template.template_id}
        else:
            return {"success": False, "error": "Template ID already exists"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Group Management Endpoints
@app.get("/api/groups")
async def list_groups():
    """List device groups"""
    try:
        groups = bulk_provisioning.get_group_manager().list_groups()
        return [asdict(group) for group in groups]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/groups")
async def create_group(request: GroupCreate):
    """Create device group"""
    try:
        group = DeviceGroup(
            group_id=f"group_{int(datetime.now().timestamp())}",
            name=request.name,
            description=request.description,
            policies=request.policies,
            member_count=0,
            created_at=datetime.now(),
            tags=request.tags
        )
        
        success = bulk_provisioning.get_group_manager().create_group(group)
        
        if success:
            return {"success": True, "group_id": group.group_id}
        else:
            return {"success": False, "error": "Group ID already exists"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Community and Troubleshooting Endpoints
@app.get("/api/community/drivers")
async def search_community_drivers(device_type: str = None, interface: str = None):
    """Search community drivers"""
    try:
        query = {}
        if device_type:
            query["device_type"] = device_type
        if interface:
            query["interface"] = interface
        
        drivers = manual_wizard.get_community_drivers(query)
        return drivers
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/protocol/builder")
async def build_custom_protocol(protocol_type: str, config: Dict[str, Any], language: str = "python"):
    """Build custom protocol"""
    try:
        protocol_builder = manual_wizard.get_protocol_builder()
        
        # Validate configuration
        errors = protocol_builder.validate_protocol_config(protocol_type, config)
        if errors:
            return {
                "success": False,
                "errors": [asdict(error) for error in errors]
            }
        
        # Generate driver code
        driver_code = protocol_builder.generate_driver_code(protocol_type, config, language)
        
        return {
            "success": True,
            "protocol_type": protocol_type,
            "language": language,
            "driver_code": driver_code,
            "config": config
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/troubleshooting")
async def get_troubleshooting_help(symptoms: Dict[str, Any]):
    """Get troubleshooting suggestions"""
    try:
        suggestions = manual_wizard.get_troubleshooting_help(symptoms)
        return [asdict(suggestion) for suggestion in suggestions]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Device Registry Endpoints
@app.get("/api/devices/registered")
async def list_registered_devices():
    """List registered devices"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM registered_devices ORDER BY registered_at DESC")
        devices = cursor.fetchall()
        conn.close()
        
        return [
            {
                "device_id": device[0],
                "name": device[1],
                "category": device[2],
                "interface": device[3],
                "manufacturer": device[4],
                "model": device[5],
                "driver_name": device[6],
                "groups": json.loads(device[8]) if device[8] else [],
                "status": device[9],
                "registered_at": device[10],
                "last_seen": device[11]
            }
            for device in devices
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Analytics Endpoints
@app.get("/api/analytics/summary")
async def get_analytics_summary():
    """Get usage analytics summary"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Total events
        cursor.execute("SELECT COUNT(*) FROM usage_analytics")
        total_events = cursor.fetchone()[0]
        
        # Top event types
        cursor.execute("SELECT event_type, COUNT(*) as count FROM usage_analytics GROUP BY event_type ORDER BY count DESC LIMIT 10")
        top_events = [{"event_type": row[0], "count": row[1]} for row in cursor.fetchall()]
        
        # Recent activity
        cursor.execute("SELECT event_type, timestamp FROM usage_analytics ORDER BY timestamp DESC LIMIT 20")
        recent_activity = [{"event_type": row[0], "timestamp": row[1]} for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            "total_events": total_events,
            "top_events": top_events,
            "recent_activity": recent_activity,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# System Status Endpoints
@app.get("/api/system/status")
async def get_system_status():
    """Get system status"""
    return {
        "service": "Hardware Wizard",
        "status": "running",
        "version": "1.0.0",
        "components": {
            "automatic_detection": "active",
            "manual_wizard": "active", 
            "bulk_provisioning": "active",
            "database": "connected"
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/system/metrics")
async def get_system_metrics():
    """Get system performance metrics"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Get counts from all tables
        cursor.execute("SELECT COUNT(*) FROM discovery_sessions")
        discovery_sessions = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM config_sessions")
        config_sessions = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM provisioning_jobs")
        provisioning_jobs = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM registered_devices")
        registered_devices = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM device_templates")
        device_templates = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "discovery_sessions": discovery_sessions,
            "config_sessions": config_sessions,
            "provisioning_jobs": provisioning_jobs,
            "registered_devices": registered_devices,
            "device_templates": device_templates,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("Starting Hardware Wizard Service on port 8425...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8425,
        log_level="info"
    )