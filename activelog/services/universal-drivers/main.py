import asyncio
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks, File, UploadFile
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import sqlite3

from driver_dev_kit.template_generator import DriverTemplateGenerator
from driver_dev_kit.protocol_analyzer import ProtocolAnalyzer
from driver_dev_kit.packet_sniffer import PacketSniffer
from protocol_translation.protocol_converters import UniversalProtocolConverter
from smart_contracts.hardware_contracts import HardwareContractManager
from hardware_simulation import (
    VirtualDeviceManager, DeviceConfig, DeviceType, Protocol,
    HardwareEmulator, create_microcontroller_emulator,
    ProtocolSimulator, ProtocolType, ProtocolConfig
)

# Database setup
DATABASE_PATH = "universal_drivers.db"

def init_database():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Driver projects table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS driver_projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            protocol TEXT NOT NULL,
            language TEXT NOT NULL,
            hardware_platform TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            project_data JSON
        )
    """)
    
    # Protocol analysis sessions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analysis_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            protocol TEXT NOT NULL,
            data_source TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            results JSON
        )
    """)
    
    # Virtual devices registry
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS virtual_devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            device_type TEXT NOT NULL,
            protocol TEXT NOT NULL,
            configuration JSON,
            status TEXT DEFAULT 'stopped',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Smart contracts registry
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hardware_contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id TEXT UNIQUE NOT NULL,
            contract_type TEXT NOT NULL,
            device_id TEXT,
            parameters JSON,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            executed_at TIMESTAMP
        )
    """)
    
    # Protocol conversion jobs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversion_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT UNIQUE NOT NULL,
            source_protocol TEXT NOT NULL,
            target_protocol TEXT NOT NULL,
            input_data BLOB,
            output_data BLOB,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

# Global managers
template_generator = DriverTemplateGenerator()
protocol_analyzer = ProtocolAnalyzer()
packet_sniffer = PacketSniffer()
protocol_converter = UniversalProtocolConverter()
contract_manager = HardwareContractManager()
device_manager = VirtualDeviceManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting Universal Driver System...")
    init_database()
    
    # Start virtual device manager
    device_manager.start_all()
    
    print("Universal Driver System started successfully")
    print(f"Database: {DATABASE_PATH}")
    print("Available services:")
    print("  - Driver Development Kit")
    print("  - Protocol Analysis & Translation")
    print("  - Hardware Simulation")
    print("  - Smart Contract Management")
    
    yield
    
    # Shutdown
    print("Shutting down Universal Driver System...")
    device_manager.stop_all()

app = FastAPI(
    title="Universal Driver System",
    description="Comprehensive platform for hardware driver development, protocol analysis, and device simulation",
    version="1.0.0",
    lifespan=lifespan
)

# Create static directories
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Pydantic models
class DriverProjectCreate(BaseModel):
    name: str
    protocol: str
    language: str
    hardware_platform: Optional[str] = None
    custom_config: Optional[Dict[str, Any]] = None

class AnalysisSessionCreate(BaseModel):
    name: str
    protocol: str
    data_source: Optional[str] = None

class VirtualDeviceCreate(BaseModel):
    name: str
    device_type: str
    protocol: str
    properties: Optional[Dict[str, Any]] = None

class ProtocolConvertRequest(BaseModel):
    source_protocol: str
    target_protocol: str
    data_hex: str

class SmartContractCreate(BaseModel):
    contract_type: str
    device_id: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None

# Root endpoint with dashboard
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Universal Driver System Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: #2c3e50; color: white; padding: 20px; border-radius: 10px; margin-bottom: 30px; }
            .services { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
            .service-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .service-title { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-bottom: 15px; }
            .endpoint { background: #ecf0f1; padding: 8px 12px; margin: 5px 0; border-radius: 5px; font-family: monospace; }
            .get { border-left: 4px solid #27ae60; }
            .post { border-left: 4px solid #3498db; }
            .delete { border-left: 4px solid #e74c3c; }
            .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }
            .stat-card { background: white; padding: 15px; border-radius: 10px; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            .stat-number { font-size: 2em; font-weight: bold; color: #3498db; }
            .stat-label { color: #7f8c8d; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔧 Universal Driver System</h1>
                <p>Comprehensive platform for hardware driver development, protocol analysis, and device simulation</p>
            </div>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number" id="projects-count">0</div>
                    <div class="stat-label">Driver Projects</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="devices-count">0</div>
                    <div class="stat-label">Virtual Devices</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="contracts-count">0</div>
                    <div class="stat-label">Smart Contracts</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="analyses-count">0</div>
                    <div class="stat-label">Protocol Analyses</div>
                </div>
            </div>
            
            <div class="services">
                <div class="service-card">
                    <h3 class="service-title">🛠️ Driver Development Kit</h3>
                    <p>Generate driver templates, analyze protocols, and capture packets</p>
                    <div class="endpoint post">POST /api/drivers/generate - Generate driver template</div>
                    <div class="endpoint get">GET /api/drivers/projects - List driver projects</div>
                    <div class="endpoint post">POST /api/analysis/start - Start protocol analysis</div>
                    <div class="endpoint get">GET /api/analysis/sessions - List analysis sessions</div>
                </div>
                
                <div class="service-card">
                    <h3 class="service-title">🔄 Protocol Translation</h3>
                    <p>Convert between different hardware communication protocols</p>
                    <div class="endpoint post">POST /api/protocol/convert - Convert protocol data</div>
                    <div class="endpoint get">GET /api/protocol/supported - List supported protocols</div>
                    <div class="endpoint get">GET /api/protocol/conversions - List conversion jobs</div>
                </div>
                
                <div class="service-card">
                    <h3 class="service-title">🖥️ Hardware Simulation</h3>
                    <p>Create and manage virtual hardware devices</p>
                    <div class="endpoint post">POST /api/devices/create - Create virtual device</div>
                    <div class="endpoint get">GET /api/devices - List virtual devices</div>
                    <div class="endpoint post">POST /api/devices/{id}/command - Send device command</div>
                    <div class="endpoint delete">DELETE /api/devices/{id} - Remove device</div>
                </div>
                
                <div class="service-card">
                    <h3 class="service-title">📜 Smart Contracts</h3>
                    <p>Manage hardware contracts and automated operations</p>
                    <div class="endpoint post">POST /api/contracts/create - Create smart contract</div>
                    <div class="endpoint get">GET /api/contracts - List contracts</div>
                    <div class="endpoint post">POST /api/contracts/{id}/execute - Execute contract</div>
                </div>
                
                <div class="service-card">
                    <h3 class="service-title">📊 System Status</h3>
                    <p>Monitor system performance and statistics</p>
                    <div class="endpoint get">GET /api/system/status - System status</div>
                    <div class="endpoint get">GET /api/system/metrics - Performance metrics</div>
                    <div class="endpoint get">GET /api/system/logs - Recent logs</div>
                </div>
                
                <div class="service-card">
                    <h3 class="service-title">📚 Documentation</h3>
                    <p>API documentation and interactive testing</p>
                    <div class="endpoint get">GET /docs - Swagger UI</div>
                    <div class="endpoint get">GET /redoc - ReDoc documentation</div>
                    <div class="endpoint get">GET /openapi.json - OpenAPI specification</div>
                </div>
            </div>
        </div>
        
        <script>
            // Load dashboard statistics
            async function loadStats() {
                try {
                    const [projects, devices, contracts, analyses] = await Promise.all([
                        fetch('/api/drivers/projects').then(r => r.json()),
                        fetch('/api/devices').then(r => r.json()),
                        fetch('/api/contracts').then(r => r.json()),
                        fetch('/api/analysis/sessions').then(r => r.json())
                    ]);
                    
                    document.getElementById('projects-count').textContent = projects.length || 0;
                    document.getElementById('devices-count').textContent = devices.length || 0;
                    document.getElementById('contracts-count').textContent = contracts.length || 0;
                    document.getElementById('analyses-count').textContent = analyses.length || 0;
                } catch (error) {
                    console.error('Failed to load statistics:', error);
                }
            }
            
            loadStats();
            setInterval(loadStats, 30000); // Refresh every 30 seconds
        </script>
    </body>
    </html>
    """
    return html_content

# Driver Development Kit endpoints
@app.post("/api/drivers/generate")
async def generate_driver(request: DriverProjectCreate):
    try:
        # Generate driver template
        output_dir = f"generated_drivers/{request.name}"
        config = {
            'hardware_platform': request.hardware_platform or 'generic',
            'protocol_config': request.custom_config or {}
        }
        
        template_generator.generate_driver_template(
            protocol=request.protocol,
            language=request.language,
            output_dir=output_dir,
            config=config
        )
        
        # Save project to database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO driver_projects (name, protocol, language, hardware_platform, project_data)
            VALUES (?, ?, ?, ?, ?)
        """, (request.name, request.protocol, request.language, 
              request.hardware_platform, json.dumps(config)))
        conn.commit()
        project_id = cursor.lastrowid
        conn.close()
        
        return {
            "status": "success",
            "project_id": project_id,
            "output_directory": output_dir,
            "message": f"Driver template generated for {request.protocol} in {request.language}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/drivers/projects")
async def list_driver_projects():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM driver_projects ORDER BY created_at DESC")
    projects = cursor.fetchall()
    conn.close()
    
    return [
        {
            "id": p[0], "name": p[1], "protocol": p[2], "language": p[3],
            "hardware_platform": p[4], "status": p[5], "created_at": p[6]
        }
        for p in projects
    ]

# Protocol Analysis endpoints
@app.post("/api/analysis/start")
async def start_protocol_analysis(request: AnalysisSessionCreate):
    try:
        # Create analysis session
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO analysis_sessions (name, protocol, data_source)
            VALUES (?, ?, ?)
        """, (request.name, request.protocol, request.data_source))
        conn.commit()
        session_id = cursor.lastrowid
        conn.close()
        
        return {
            "status": "success",
            "session_id": session_id,
            "message": f"Analysis session started for {request.protocol}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis/sessions")
async def list_analysis_sessions():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM analysis_sessions ORDER BY created_at DESC")
    sessions = cursor.fetchall()
    conn.close()
    
    return [
        {
            "id": s[0], "name": s[1], "protocol": s[2], "data_source": s[3],
            "status": s[4], "created_at": s[5]
        }
        for s in sessions
    ]

# Protocol Translation endpoints
@app.post("/api/protocol/convert")
async def convert_protocol(request: ProtocolConvertRequest):
    try:
        # Convert hex string to bytes
        input_data = bytes.fromhex(request.data_hex)
        
        # Perform conversion
        output_data = protocol_converter.convert_protocol(
            input_data, 
            request.source_protocol, 
            request.target_protocol
        )
        
        # Save conversion job
        job_id = f"conv_{int(datetime.now().timestamp() * 1000)}"
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO conversion_jobs (job_id, source_protocol, target_protocol, input_data, output_data, status, completed_at)
            VALUES (?, ?, ?, ?, ?, 'completed', CURRENT_TIMESTAMP)
        """, (job_id, request.source_protocol, request.target_protocol, input_data, output_data))
        conn.commit()
        conn.close()
        
        return {
            "status": "success",
            "job_id": job_id,
            "output_data_hex": output_data.hex(),
            "input_length": len(input_data),
            "output_length": len(output_data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/protocol/supported")
async def list_supported_protocols():
    return {
        "supported_protocols": [
            "i2c", "spi", "uart", "usb", "can", "modbus", "ethernet", "tcp", "udp", "http", "mqtt"
        ],
        "conversion_matrix": protocol_converter.get_supported_conversions()
    }

@app.get("/api/protocol/conversions")
async def list_conversions():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT job_id, source_protocol, target_protocol, status, created_at, completed_at FROM conversion_jobs ORDER BY created_at DESC LIMIT 100")
    conversions = cursor.fetchall()
    conn.close()
    
    return [
        {
            "job_id": c[0], "source_protocol": c[1], "target_protocol": c[2],
            "status": c[3], "created_at": c[4], "completed_at": c[5]
        }
        for c in conversions
    ]

# Virtual Device endpoints
@app.post("/api/devices/create")
async def create_virtual_device(request: VirtualDeviceCreate):
    try:
        device_config = DeviceConfig(
            device_id=f"dev_{int(datetime.now().timestamp() * 1000)}",
            name=request.name,
            device_type=DeviceType(request.device_type),
            protocol=Protocol(request.protocol),
            address=request.properties.get('address', '0x00') if request.properties else '0x00',
            properties=request.properties or {}
        )
        
        device = device_manager.create_device(device_config)
        device.start()
        
        # Save to database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO virtual_devices (device_id, name, device_type, protocol, configuration, status)
            VALUES (?, ?, ?, ?, ?, 'running')
        """, (device_config.device_id, device_config.name, device_config.device_type.value, 
              device_config.protocol.value, json.dumps(device_config.properties)))
        conn.commit()
        conn.close()
        
        return {
            "status": "success",
            "device_id": device_config.device_id,
            "message": f"Virtual device '{request.name}' created and started"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/devices")
async def list_virtual_devices():
    devices = []
    for device_id in device_manager.list_devices():
        device = device_manager.get_device(device_id)
        if device:
            devices.append({
                "device_id": device_id,
                "name": device.config.name,
                "device_type": device.config.device_type.value,
                "protocol": device.config.protocol.value,
                "status": device.state.status,
                "last_update": device.state.timestamp.isoformat()
            })
    return devices

@app.post("/api/devices/{device_id}/command")
async def send_device_command(device_id: str, command: str, params: Optional[Dict[str, Any]] = None):
    device = device_manager.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    try:
        response = device.send_command(command, params)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/devices/{device_id}")
async def remove_virtual_device(device_id: str):
    device = device_manager.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    device_manager.remove_device(device_id)
    
    # Update database
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE virtual_devices SET status = 'removed' WHERE device_id = ?", (device_id,))
    conn.commit()
    conn.close()
    
    return {"status": "success", "message": f"Device {device_id} removed"}

# Smart Contract endpoints
@app.post("/api/contracts/create")
async def create_smart_contract(request: SmartContractCreate):
    try:
        contract_id = f"contract_{int(datetime.now().timestamp() * 1000)}"
        
        # Create contract using contract manager
        contract = contract_manager.create_device_registration_contract(
            contract_id=contract_id,
            device_id=request.device_id or f"device_{contract_id}",
            device_type=request.parameters.get('device_type', 'generic') if request.parameters else 'generic',
            manufacturer=request.parameters.get('manufacturer', 'unknown') if request.parameters else 'unknown'
        )
        
        # Save to database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO hardware_contracts (contract_id, contract_type, device_id, parameters)
            VALUES (?, ?, ?, ?)
        """, (contract_id, request.contract_type, request.device_id, 
              json.dumps(request.parameters or {})))
        conn.commit()
        conn.close()
        
        return {
            "status": "success",
            "contract_id": contract_id,
            "message": f"Smart contract created for {request.contract_type}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/contracts")
async def list_smart_contracts():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hardware_contracts ORDER BY created_at DESC")
    contracts = cursor.fetchall()
    conn.close()
    
    return [
        {
            "id": c[0], "contract_id": c[1], "contract_type": c[2], 
            "device_id": c[3], "status": c[5], "created_at": c[6]
        }
        for c in contracts
    ]

@app.post("/api/contracts/{contract_id}/execute")
async def execute_smart_contract(contract_id: str):
    try:
        # Execute contract
        result = contract_manager.execute_contract(contract_id)
        
        # Update database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE hardware_contracts 
            SET status = 'executed', executed_at = CURRENT_TIMESTAMP 
            WHERE contract_id = ?
        """, (contract_id,))
        conn.commit()
        conn.close()
        
        return {
            "status": "success",
            "contract_id": contract_id,
            "result": result,
            "message": "Contract executed successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# System Status endpoints
@app.get("/api/system/status")
async def get_system_status():
    return {
        "service": "Universal Driver System",
        "status": "running",
        "version": "1.0.0",
        "uptime": "operational",
        "components": {
            "driver_dev_kit": "active",
            "protocol_converter": "active",
            "device_manager": "active",
            "contract_manager": "active",
            "database": "connected"
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/system/metrics")
async def get_system_metrics():
    # Get database counts
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM driver_projects")
    projects_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM virtual_devices WHERE status = 'running'")
    running_devices = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM hardware_contracts WHERE status = 'active'")
    active_contracts = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM conversion_jobs WHERE status = 'completed'")
    completed_conversions = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "driver_projects": projects_count,
        "running_devices": running_devices,
        "active_contracts": active_contracts,
        "completed_conversions": completed_conversions,
        "supported_protocols": 11,
        "supported_languages": 4,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    print("Starting Universal Driver System on port 8423...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8423,
        log_level="info"
    )