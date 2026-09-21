"""
Hardware Ecosystem Platform
Comprehensive hardware marketplace, device management, edge orchestration and IoT fleet management
Port: 8422
"""

import asyncio
import logging
import sqlite3
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, Field
import uvicorn

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Hardware Ecosystem Platform",
    description="Comprehensive hardware marketplace, device management, edge orchestration and IoT fleet management",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database initialization
def init_database():
    """Initialize SQLite database with all required tables"""
    conn = sqlite3.connect('hardware_ecosystem.db')
    cursor = conn.cursor()
    
    # Hardware Marketplace Tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hardware_listings (
            id TEXT PRIMARY KEY,
            owner_id TEXT NOT NULL,
            device_type TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            specifications TEXT,
            hourly_rate REAL NOT NULL,
            daily_rate REAL,
            weekly_rate REAL,
            availability_schedule TEXT,
            location TEXT,
            status TEXT DEFAULT 'available',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rental_bookings (
            id TEXT PRIMARY KEY,
            listing_id TEXT NOT NULL,
            renter_id TEXT NOT NULL,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP NOT NULL,
            total_cost REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            payment_status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (listing_id) REFERENCES hardware_listings (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS compute_auctions (
            id TEXT PRIMARY KEY,
            requester_id TEXT NOT NULL,
            compute_type TEXT NOT NULL,
            requirements TEXT,
            max_budget REAL NOT NULL,
            duration_hours INTEGER NOT NULL,
            status TEXT DEFAULT 'open',
            winning_bid_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deadline TIMESTAMP NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS storage_trades (
            id TEXT PRIMARY KEY,
            provider_id TEXT NOT NULL,
            storage_type TEXT NOT NULL,
            capacity_gb INTEGER NOT NULL,
            price_per_gb REAL NOT NULL,
            location TEXT,
            performance_tier TEXT,
            status TEXT DEFAULT 'available',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Device Management Tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS managed_devices (
            id TEXT PRIMARY KEY,
            owner_id TEXT NOT NULL,
            device_name TEXT NOT NULL,
            device_type TEXT NOT NULL,
            ip_address TEXT,
            location TEXT,
            status TEXT DEFAULT 'offline',
            last_seen TIMESTAMP,
            firmware_version TEXT,
            hardware_info TEXT,
            performance_metrics TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS device_metrics (
            id TEXT PRIMARY KEY,
            device_id TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cpu_usage REAL,
            memory_usage REAL,
            disk_usage REAL,
            temperature REAL,
            network_rx INTEGER,
            network_tx INTEGER,
            power_consumption REAL,
            FOREIGN KEY (device_id) REFERENCES managed_devices (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS maintenance_schedules (
            id TEXT PRIMARY KEY,
            device_id TEXT NOT NULL,
            maintenance_type TEXT NOT NULL,
            scheduled_date TIMESTAMP NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'scheduled',
            technician_id TEXT,
            estimated_duration INTEGER,
            actual_duration INTEGER,
            cost REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (device_id) REFERENCES managed_devices (id)
        )
    ''')
    
    # Edge Orchestration Tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS edge_nodes (
            id TEXT PRIMARY KEY,
            node_name TEXT NOT NULL,
            location TEXT,
            ip_address TEXT NOT NULL,
            port INTEGER DEFAULT 22,
            status TEXT DEFAULT 'offline',
            capabilities TEXT,
            resources TEXT,
            last_heartbeat TIMESTAMP,
            cluster_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS edge_deployments (
            id TEXT PRIMARY KEY,
            deployment_name TEXT NOT NULL,
            container_image TEXT NOT NULL,
            target_nodes TEXT,
            config TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deployed_at TIMESTAMP,
            health_check_url TEXT
        )
    ''')
    
    # IoT Fleet Management Tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS iot_devices (
            id TEXT PRIMARY KEY,
            device_name TEXT NOT NULL,
            device_type TEXT NOT NULL,
            mac_address TEXT UNIQUE,
            firmware_version TEXT,
            location TEXT,
            group_id TEXT,
            status TEXT DEFAULT 'offline',
            last_seen TIMESTAMP,
            configuration TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fleet_groups (
            id TEXT PRIMARY KEY,
            group_name TEXT NOT NULL,
            description TEXT,
            policies TEXT,
            automation_rules TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ota_updates (
            id TEXT PRIMARY KEY,
            firmware_version TEXT NOT NULL,
            device_type TEXT NOT NULL,
            update_package_url TEXT NOT NULL,
            changelog TEXT,
            rollout_percentage INTEGER DEFAULT 0,
            status TEXT DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# Pydantic models
class HardwareListing(BaseModel):
    device_type: str
    name: str
    description: Optional[str] = None
    specifications: Optional[Dict[str, Any]] = None
    hourly_rate: float
    daily_rate: Optional[float] = None
    weekly_rate: Optional[float] = None
    availability_schedule: Optional[Dict[str, Any]] = None
    location: Optional[str] = None

class RentalBooking(BaseModel):
    listing_id: str
    start_time: datetime
    end_time: datetime
    
class ComputeAuction(BaseModel):
    compute_type: str
    requirements: Dict[str, Any]
    max_budget: float
    duration_hours: int
    deadline: datetime

class DeviceRegistration(BaseModel):
    device_name: str
    device_type: str
    ip_address: Optional[str] = None
    location: Optional[str] = None
    firmware_version: Optional[str] = None
    hardware_info: Optional[Dict[str, Any]] = None

class EdgeDeployment(BaseModel):
    deployment_name: str
    container_image: str
    target_nodes: List[str]
    config: Optional[Dict[str, Any]] = None
    health_check_url: Optional[str] = None

class IoTDevice(BaseModel):
    device_name: str
    device_type: str
    mac_address: str
    firmware_version: Optional[str] = None
    location: Optional[str] = None
    group_id: Optional[str] = None

# WebSocket connections
active_connections: List[WebSocket] = []

@app.on_event("startup")
async def startup_event():
    """Initialize database and background tasks"""
    init_database()
    logger.info("Hardware Ecosystem Platform started successfully on port 8422")
    
    # Start background monitoring tasks
    asyncio.create_task(device_health_monitor())
    asyncio.create_task(edge_node_monitor())
    asyncio.create_task(iot_fleet_monitor())

async def device_health_monitor():
    """Background task to monitor device health"""
    while True:
        try:
            conn = sqlite3.connect('hardware_ecosystem.db')
            cursor = conn.cursor()
            
            # Check for devices that haven't reported in 5 minutes
            threshold = datetime.now() - timedelta(minutes=5)
            cursor.execute('''
                UPDATE managed_devices 
                SET status = 'offline' 
                WHERE last_seen < ? AND status != 'offline'
            ''', (threshold,))
            
            # Broadcast status updates
            if cursor.rowcount > 0:
                await broadcast_system_update({
                    "type": "device_status_change",
                    "message": f"{cursor.rowcount} devices marked as offline"
                })
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Device health monitor error: {e}")
        
        await asyncio.sleep(60)  # Check every minute

async def edge_node_monitor():
    """Background task to monitor edge nodes"""
    while True:
        try:
            conn = sqlite3.connect('hardware_ecosystem.db')
            cursor = conn.cursor()
            
            # Check edge node heartbeats
            threshold = datetime.now() - timedelta(minutes=2)
            cursor.execute('''
                UPDATE edge_nodes 
                SET status = 'offline' 
                WHERE last_heartbeat < ? AND status != 'offline'
            ''', (threshold,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Edge node monitor error: {e}")
        
        await asyncio.sleep(30)  # Check every 30 seconds

async def iot_fleet_monitor():
    """Background task to monitor IoT fleet"""
    while True:
        try:
            conn = sqlite3.connect('hardware_ecosystem.db')
            cursor = conn.cursor()
            
            # Check IoT device connectivity
            threshold = datetime.now() - timedelta(minutes=10)
            cursor.execute('''
                UPDATE iot_devices 
                SET status = 'offline' 
                WHERE last_seen < ? AND status != 'offline'
            ''', (threshold,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"IoT fleet monitor error: {e}")
        
        await asyncio.sleep(120)  # Check every 2 minutes

async def broadcast_system_update(message: Dict[str, Any]):
    """Broadcast updates to all connected WebSocket clients"""
    if active_connections:
        disconnected = []
        for connection in active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                disconnected.append(connection)
        
        for connection in disconnected:
            active_connections.remove(connection)

# === Root and System Endpoints ===

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Hardware Ecosystem Dashboard"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Hardware Ecosystem Platform</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                     color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }
            .section { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; 
                      box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
            .feature { border: 1px solid #e0e0e0; padding: 15px; border-radius: 5px; }
            .endpoint { background: #f8f9fa; padding: 10px; border-radius: 5px; margin: 5px 0; }
            .badge { background: #007bff; color: white; padding: 3px 8px; border-radius: 12px; font-size: 12px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏭 Hardware Ecosystem Platform</h1>
                <p>Comprehensive hardware marketplace, device management, edge orchestration and IoT fleet management</p>
                <p><strong>Port:</strong> 8422 | <strong>Status:</strong> Active | <strong>Version:</strong> 1.0.0</p>
            </div>
            
            <div class="grid">
                <div class="section">
                    <h2>🏪 Hardware Marketplace</h2>
                    <div class="feature">
                        <h3>Device Rental System</h3>
                        <div class="endpoint">POST /api/marketplace/listings - Create rental listing</div>
                        <div class="endpoint">GET /api/marketplace/listings - Browse available hardware</div>
                        <div class="endpoint">POST /api/marketplace/bookings - Book hardware rental</div>
                    </div>
                    <div class="feature">
                        <h3>Compute Auction System</h3>
                        <div class="endpoint">POST /api/marketplace/auctions - Create compute auction</div>
                        <div class="endpoint">GET /api/marketplace/auctions - View active auctions</div>
                    </div>
                    <div class="feature">
                        <h3>Storage Trading</h3>
                        <div class="endpoint">POST /api/marketplace/storage - List storage for trade</div>
                        <div class="endpoint">GET /api/marketplace/storage - Browse storage offers</div>
                    </div>
                </div>
                
                <div class="section">
                    <h2>📊 Device Management</h2>
                    <div class="feature">
                        <h3>Device Registration & Monitoring</h3>
                        <div class="endpoint">POST /api/devices/register - Register new device</div>
                        <div class="endpoint">GET /api/devices - List managed devices</div>
                        <div class="endpoint">GET /api/devices/{id}/metrics - Device performance</div>
                    </div>
                    <div class="feature">
                        <h3>Maintenance Management</h3>
                        <div class="endpoint">POST /api/devices/{id}/maintenance - Schedule maintenance</div>
                        <div class="endpoint">GET /api/maintenance - View schedules</div>
                    </div>
                </div>
                
                <div class="section">
                    <h2>🌐 Edge Orchestration</h2>
                    <div class="feature">
                        <h3>Edge Deployment</h3>
                        <div class="endpoint">POST /api/edge/nodes - Register edge node</div>
                        <div class="endpoint">POST /api/edge/deploy - Deploy to edge</div>
                        <div class="endpoint">GET /api/edge/deployments - Monitor deployments</div>
                    </div>
                </div>
                
                <div class="section">
                    <h2>📱 IoT Fleet Management</h2>
                    <div class="feature">
                        <h3>Device Provisioning</h3>
                        <div class="endpoint">POST /api/iot/devices - Add IoT device</div>
                        <div class="endpoint">POST /api/iot/groups - Create device group</div>
                        <div class="endpoint">POST /api/iot/ota - Over-the-air updates</div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>📡 Real-time Monitoring</h2>
                <p>Connect to WebSocket at <code>/ws/ecosystem</code> for real-time updates on device status, 
                edge deployments, and IoT fleet health.</p>
            </div>
        </div>
        
        <script>
            // Auto-refresh every 30 seconds
            setTimeout(() => location.reload(), 30000);
        </script>
    </body>
    </html>
    """

@app.get("/api/system/status")
async def get_system_status():
    """Get comprehensive system status"""
    try:
        conn = sqlite3.connect('hardware_ecosystem.db')
        cursor = conn.cursor()
        
        # Get counts for all major components
        cursor.execute("SELECT COUNT(*) FROM hardware_listings WHERE status = 'available'")
        available_listings = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM managed_devices WHERE status = 'online'")
        online_devices = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM edge_nodes WHERE status = 'online'")
        online_edge_nodes = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM iot_devices WHERE status = 'online'")
        online_iot_devices = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM rental_bookings WHERE status = 'active'")
        active_rentals = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM compute_auctions WHERE status = 'open'")
        open_auctions = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "service": "Hardware Ecosystem Platform",
            "status": "healthy",
            "port": 8422,
            "components": {
                "marketplace": {
                    "available_listings": available_listings,
                    "active_rentals": active_rentals,
                    "open_auctions": open_auctions
                },
                "device_management": {
                    "online_devices": online_devices,
                    "total_managed": online_devices
                },
                "edge_orchestration": {
                    "online_nodes": online_edge_nodes
                },
                "iot_fleet": {
                    "online_devices": online_iot_devices
                }
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# === Hardware Marketplace Endpoints ===

@app.post("/api/marketplace/listings")
async def create_hardware_listing(listing: HardwareListing, owner_id: str = "default_user"):
    """Create a new hardware rental listing"""
    try:
        listing_id = str(uuid.uuid4())
        conn = sqlite3.connect('hardware_ecosystem.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO hardware_listings 
            (id, owner_id, device_type, name, description, specifications, 
             hourly_rate, daily_rate, weekly_rate, availability_schedule, location)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            listing_id, owner_id, listing.device_type, listing.name, 
            listing.description, json.dumps(listing.specifications or {}),
            listing.hourly_rate, listing.daily_rate, listing.weekly_rate,
            json.dumps(listing.availability_schedule or {}), listing.location
        ))
        
        conn.commit()
        conn.close()
        
        await broadcast_system_update({
            "type": "new_listing",
            "listing_id": listing_id,
            "device_type": listing.device_type,
            "name": listing.name
        })
        
        return {
            "listing_id": listing_id,
            "status": "created",
            "message": "Hardware listing created successfully"
        }
    except Exception as e:
        logger.error(f"Error creating listing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/marketplace/listings")
async def get_hardware_listings(device_type: Optional[str] = None, location: Optional[str] = None):
    """Browse available hardware listings"""
    try:
        conn = sqlite3.connect('hardware_ecosystem.db')
        cursor = conn.cursor()
        
        query = "SELECT * FROM hardware_listings WHERE status = 'available'"
        params = []
        
        if device_type:
            query += " AND device_type = ?"
            params.append(device_type)
        if location:
            query += " AND location = ?"
            params.append(location)
            
        cursor.execute(query, params)
        listings = cursor.fetchall()
        conn.close()
        
        result = []
        for listing in listings:
            result.append({
                "id": listing[0],
                "owner_id": listing[1],
                "device_type": listing[2],
                "name": listing[3],
                "description": listing[4],
                "specifications": json.loads(listing[5]) if listing[5] else {},
                "hourly_rate": listing[6],
                "daily_rate": listing[7],
                "weekly_rate": listing[8],
                "availability_schedule": json.loads(listing[9]) if listing[9] else {},
                "location": listing[10],
                "status": listing[11],
                "created_at": listing[12]
            })
        
        return {"listings": result, "count": len(result)}
    except Exception as e:
        logger.error(f"Error getting listings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/marketplace/bookings")
async def create_rental_booking(booking: RentalBooking, renter_id: str = "default_user"):
    """Create a hardware rental booking"""
    try:
        booking_id = str(uuid.uuid4())
        
        # Calculate rental cost
        duration_hours = (booking.end_time - booking.start_time).total_seconds() / 3600
        
        conn = sqlite3.connect('hardware_ecosystem.db')
        cursor = conn.cursor()
        
        # Get listing details
        cursor.execute("SELECT hourly_rate FROM hardware_listings WHERE id = ?", (booking.listing_id,))
        listing = cursor.fetchone()
        if not listing:
            raise HTTPException(status_code=404, detail="Hardware listing not found")
        
        total_cost = listing[0] * duration_hours
        
        cursor.execute('''
            INSERT INTO rental_bookings 
            (id, listing_id, renter_id, start_time, end_time, total_cost)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (booking_id, booking.listing_id, renter_id, booking.start_time, booking.end_time, total_cost))
        
        conn.commit()
        conn.close()
        
        return {
            "booking_id": booking_id,
            "total_cost": total_cost,
            "duration_hours": duration_hours,
            "status": "confirmed"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating booking: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/marketplace/auctions")
async def create_compute_auction(auction: ComputeAuction, requester_id: str = "default_user"):
    """Create a compute auction for GPU/quantum/specialized hardware time"""
    try:
        auction_id = str(uuid.uuid4())
        conn = sqlite3.connect('hardware_ecosystem.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO compute_auctions 
            (id, requester_id, compute_type, requirements, max_budget, duration_hours, deadline)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            auction_id, requester_id, auction.compute_type, 
            json.dumps(auction.requirements), auction.max_budget, 
            auction.duration_hours, auction.deadline
        ))
        
        conn.commit()
        conn.close()
        
        await broadcast_system_update({
            "type": "new_auction",
            "auction_id": auction_id,
            "compute_type": auction.compute_type,
            "max_budget": auction.max_budget
        })
        
        return {
            "auction_id": auction_id,
            "status": "created",
            "deadline": auction.deadline.isoformat()
        }
    except Exception as e:
        logger.error(f"Error creating auction: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/marketplace/auctions")
async def get_compute_auctions(status: str = "open"):
    """Get active compute auctions"""
    try:
        conn = sqlite3.connect('hardware_ecosystem.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM compute_auctions WHERE status = ?", (status,))
        auctions = cursor.fetchall()
        conn.close()
        
        result = []
        for auction in auctions:
            result.append({
                "id": auction[0],
                "requester_id": auction[1],
                "compute_type": auction[2],
                "requirements": json.loads(auction[3]),
                "max_budget": auction[4],
                "duration_hours": auction[5],
                "status": auction[6],
                "deadline": auction[8],
                "created_at": auction[9]
            })
        
        return {"auctions": result, "count": len(result)}
    except Exception as e:
        logger.error(f"Error getting auctions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# === Device Management Endpoints ===

@app.post("/api/devices/register")
async def register_device(device: DeviceRegistration, owner_id: str = "default_user"):
    """Register a new device for management"""
    try:
        device_id = str(uuid.uuid4())
        conn = sqlite3.connect('hardware_ecosystem.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO managed_devices 
            (id, owner_id, device_name, device_type, ip_address, location, 
             firmware_version, hardware_info, last_seen, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'online')
        ''', (
            device_id, owner_id, device.device_name, device.device_type,
            device.ip_address, device.location, device.firmware_version,
            json.dumps(device.hardware_info or {}), datetime.now()
        ))
        
        conn.commit()
        conn.close()
        
        return {
            "device_id": device_id,
            "status": "registered",
            "message": "Device registered successfully"
        }
    except Exception as e:
        logger.error(f"Error registering device: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/devices")
async def get_managed_devices(status: Optional[str] = None):
    """Get all managed devices"""
    try:
        conn = sqlite3.connect('hardware_ecosystem.db')
        cursor = conn.cursor()
        
        query = "SELECT * FROM managed_devices"
        params = []
        
        if status:
            query += " WHERE status = ?"
            params.append(status)
            
        cursor.execute(query, params)
        devices = cursor.fetchall()
        conn.close()
        
        result = []
        for device in devices:
            result.append({
                "id": device[0],
                "owner_id": device[1],
                "device_name": device[2],
                "device_type": device[3],
                "ip_address": device[4],
                "location": device[5],
                "status": device[6],
                "last_seen": device[7],
                "firmware_version": device[8],
                "hardware_info": json.loads(device[9]) if device[9] else {},
                "created_at": device[11]
            })
        
        return {"devices": result, "count": len(result)}
    except Exception as e:
        logger.error(f"Error getting devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/devices/{device_id}/metrics")
async def get_device_metrics(device_id: str, hours: int = 24):
    """Get device performance metrics"""
    try:
        conn = sqlite3.connect('hardware_ecosystem.db')
        cursor = conn.cursor()
        
        since = datetime.now() - timedelta(hours=hours)
        cursor.execute('''
            SELECT timestamp, cpu_usage, memory_usage, disk_usage, 
                   temperature, network_rx, network_tx, power_consumption
            FROM device_metrics 
            WHERE device_id = ? AND timestamp > ?
            ORDER BY timestamp DESC
        ''', (device_id, since))
        
        metrics = cursor.fetchall()
        conn.close()
        
        result = []
        for metric in metrics:
            result.append({
                "timestamp": metric[0],
                "cpu_usage": metric[1],
                "memory_usage": metric[2],
                "disk_usage": metric[3],
                "temperature": metric[4],
                "network_rx": metric[5],
                "network_tx": metric[6],
                "power_consumption": metric[7]
            })
        
        return {"device_id": device_id, "metrics": result, "hours": hours}
    except Exception as e:
        logger.error(f"Error getting device metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# === Edge Orchestration Endpoints ===

@app.post("/api/edge/nodes")
async def register_edge_node(node_data: dict):
    """Register a new edge node"""
    try:
        conn = sqlite3.connect('hardware_ecosystem.db')
        cursor = conn.cursor()
        
        node_id = str(uuid.uuid4())
        cursor.execute("""
        INSERT INTO edge_nodes (id, node_name, location, ip_address, port, capabilities, resources, status, last_heartbeat)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?)
        """, (
            node_id,
            node_data['name'],
            node_data.get('location', 'unknown'),
            node_data.get('ip_address', '192.168.1.100'),
            node_data.get('port', 22),
            json.dumps(node_data.get('capabilities', {})),
            json.dumps(node_data.get('resources', {})),
            datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return {"node_id": node_id, "status": "registered", "message": "Edge node registered successfully"}
    except Exception as e:
        logger.error(f"Error registering edge node: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/edge/deploy")
async def deploy_to_edge(deployment_data: dict):
    """Deploy container/service to edge node"""
    try:
        conn = sqlite3.connect('hardware_ecosystem.db')
        cursor = conn.cursor()
        
        deployment_id = str(uuid.uuid4())
        cursor.execute("""
        INSERT INTO edge_deployments (id, deployment_name, container_image, target_nodes, config, status, deployed_at)
        VALUES (?, ?, ?, ?, ?, 'deploying', ?)
        """, (
            deployment_id,
            deployment_data.get('name', f"deployment-{deployment_id[:8]}"),
            deployment_data['container_image'],
            json.dumps([deployment_data['node_id']]),
            json.dumps(deployment_data.get('config', {})),
            datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        # Simulate deployment process
        asyncio.create_task(simulate_deployment(deployment_id))
        
        return {"deployment_id": deployment_id, "status": "initiated", "message": "Deployment started"}
    except Exception as e:
        logger.error(f"Error deploying to edge: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/edge/ai-models")
async def deploy_ai_model_to_edge(model_data: dict):
    """Deploy AI model to edge nodes for inference"""
    try:
        conn = sqlite3.connect('hardware_ecosystem.db')
        cursor = conn.cursor()
        
        deployment_id = str(uuid.uuid4())
        # Create AI model deployment entry
        cursor.execute("""
        INSERT INTO edge_deployments (id, deployment_name, container_image, target_nodes, config, status, deployed_at)
        VALUES (?, ?, ?, ?, ?, 'deploying_ai_model', ?)
        """, (
            deployment_id,
            f"ai-model-{model_data['model_name']}-{deployment_id[:8]}",
            f"ai-inference:{model_data['model_name']}",
            json.dumps([model_data['node_id']]),
            json.dumps({
                "model_name": model_data['model_name'],
                "model_version": model_data.get('model_version', 'latest'),
                "inference_config": model_data.get('config', {}),
                "resource_requirements": model_data.get('resources', {}),
                "optimization": model_data.get('optimization', 'speed')
            }),
            datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        # Simulate AI model deployment
        asyncio.create_task(simulate_ai_model_deployment(deployment_id))
        
        return {"deployment_id": deployment_id, "status": "deploying_ai_model", "message": "AI model deployment initiated"}
    except Exception as e:
        logger.error(f"Error deploying AI model to edge: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/edge/containers/distribute")
async def distribute_containers_to_edge(distribution_data: dict):
    """Distribute containers to multiple edge nodes"""
    try:
        conn = sqlite3.connect('hardware_ecosystem.db')
        cursor = conn.cursor()
        
        deployment_ids = []
        
        for node_id in distribution_data['node_ids']:
            cursor.execute("""
            INSERT INTO edge_deployments (node_id, container_image, config, status, deployed_at)
            VALUES (?, ?, ?, 'distributing', ?)
            """, (
                node_id,
                distribution_data['container_image'],
                json.dumps({
                    "batch_id": distribution_data.get('batch_id', f"batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"),
                    "priority": distribution_data.get('priority', 'normal'),
                    "rollout_strategy": distribution_data.get('rollout_strategy', 'immediate'),
                    "config": distribution_data.get('config', {})
                }),
                datetime.utcnow().isoformat()
            ))
            deployment_ids.append(cursor.lastrowid)
        
        conn.commit()
        conn.close()
        
        # Simulate distributed deployment
        for deployment_id in deployment_ids:
            asyncio.create_task(simulate_deployment(deployment_id))
        
        return {
            "batch_id": distribution_data.get('batch_id', f"batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"),
            "deployment_ids": deployment_ids,
            "status": "distributing",
            "message": f"Container distribution initiated to {len(deployment_ids)} edge nodes"
        }
    except Exception as e:
        logger.error(f"Error distributing containers to edge: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/edge/nodes")
async def get_edge_nodes():
    """Get all edge nodes with status"""
    try:
        conn = sqlite3.connect('hardware_ecosystem.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM edge_nodes ORDER BY created_at DESC")
        
        nodes = []
        for row in cursor.fetchall():
            nodes.append({
                "id": row[0],
                "name": row[1],
                "location": row[2],
                "ip_address": row[3],
                "port": row[4],
                "status": row[5],
                "capabilities": json.loads(row[6]) if row[6] else {},
                "resources": json.loads(row[7]) if row[7] else {},
                "last_heartbeat": row[8],
                "cluster_id": row[9],
                "created_at": row[10]
            })
        
        conn.close()
        return {"nodes": nodes, "count": len(nodes)}
    except Exception as e:
        logger.error(f"Error getting edge nodes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/edge/deployments")
async def get_edge_deployments():
    """Get all edge deployments"""
    try:
        conn = sqlite3.connect('hardware_ecosystem.db')
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT ed.*, en.name as node_name, en.location 
        FROM edge_deployments ed
        LEFT JOIN edge_nodes en ON ed.node_id = en.id
        ORDER BY ed.deployed_at DESC
        """)
        
        deployments = []
        for row in cursor.fetchall():
            deployments.append({
                "id": row[0],
                "node_id": row[1],
                "node_name": row[7],
                "location": row[8],
                "container_image": row[2],
                "config": json.loads(row[3]),
                "status": row[4],
                "deployed_at": row[5],
                "updated_at": row[6]
            })
        
        conn.close()
        return {"deployments": deployments, "count": len(deployments)}
    except Exception as e:
        logger.error(f"Error getting edge deployments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def simulate_deployment(deployment_id: str):
    """Simulate deployment process"""
    await asyncio.sleep(5)  # Simulate deployment time
    
    conn = sqlite3.connect('hardware_ecosystem.db')
    cursor = conn.cursor()
    
    cursor.execute("""
    UPDATE edge_deployments 
    SET status = 'deployed', deployed_at = ?
    WHERE id = ?
    """, (datetime.utcnow().isoformat(), deployment_id))
    
    conn.commit()
    conn.close()

async def simulate_ai_model_deployment(deployment_id: str):
    """Simulate AI model deployment process"""
    await asyncio.sleep(8)  # AI models take longer to deploy
    
    conn = sqlite3.connect('hardware_ecosystem.db')
    cursor = conn.cursor()
    
    cursor.execute("""
    UPDATE edge_deployments 
    SET status = 'ai_model_deployed', deployed_at = ?
    WHERE id = ?
    """, (datetime.utcnow().isoformat(), deployment_id))
    
    conn.commit()
    conn.close()

# === IoT Fleet Management Endpoints ===

@app.post("/api/iot/devices")
async def add_iot_device(device_data: dict):
    """Add IoT device to fleet"""
    try:
        conn = sqlite3.connect('hardware_ecosystem.db')
        cursor = conn.cursor()
        
        device_id = str(uuid.uuid4())
        cursor.execute("""
        INSERT INTO iot_devices (id, device_name, device_type, mac_address, firmware_version, location, 
                                group_id, status, last_seen, configuration)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'online', ?, ?)
        """, (
            device_id,
            device_data['name'],
            device_data['device_type'],
            device_data.get('mac_address', f"00:00:00:{device_id[:6]}"),
            device_data.get('firmware_version', '1.0.0'),
            device_data.get('location', 'unknown'),
            device_data.get('group_id'),
            datetime.utcnow().isoformat(),
            json.dumps(device_data.get('metadata', {}))
        ))
        
        conn.commit()
        conn.close()
        
        return {"device_id": device_id, "status": "added", "message": "IoT device added to fleet"}
    except Exception as e:
        logger.error(f"Error adding IoT device: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/iot/groups")
async def create_device_group(group_data: dict):
    """Create device group for fleet management"""
    try:
        conn = sqlite3.connect('hardware_ecosystem.db')
        cursor = conn.cursor()
        
        cursor.execute("""
        INSERT INTO fleet_groups (name, description, policies, created_at)
        VALUES (?, ?, ?, ?)
        """, (
            group_data['name'],
            group_data.get('description', ''),
            json.dumps(group_data.get('policies', {})),
            datetime.utcnow().isoformat()
        ))
        
        group_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {"group_id": group_id, "status": "created", "message": "Device group created"}
    except Exception as e:
        logger.error(f"Error creating device group: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/iot/ota")
async def initiate_ota_update(update_data: dict):
    """Initiate over-the-air firmware update"""
    try:
        conn = sqlite3.connect('hardware_ecosystem.db')
        cursor = conn.cursor()
        
        cursor.execute("""
        INSERT INTO ota_updates (target_devices, firmware_version, update_package_url,
                               rollout_strategy, status, initiated_at)
        VALUES (?, ?, ?, ?, 'initiated', ?)
        """, (
            json.dumps(update_data['target_devices']),
            update_data['firmware_version'],
            update_data['update_package_url'],
            update_data.get('rollout_strategy', 'immediate'),
            datetime.utcnow().isoformat()
        ))
        
        update_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Simulate OTA update process
        asyncio.create_task(simulate_ota_update(update_id))
        
        return {"update_id": update_id, "status": "initiated", "message": "OTA update initiated"}
    except Exception as e:
        logger.error(f"Error initiating OTA update: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/iot/devices")
async def get_iot_devices(group_id: Optional[str] = None, status: Optional[str] = None):
    """Get IoT devices in fleet"""
    try:
        conn = sqlite3.connect('hardware_ecosystem.db')
        cursor = conn.cursor()
        
        query = "SELECT * FROM iot_devices WHERE 1=1"
        params = []
        
        if group_id:
            query += " AND group_id = ?"
            params.append(group_id)
        if status:
            query += " AND status = ?"
            params.append(status)
            
        cursor.execute(query, params)
        
        devices = []
        for row in cursor.fetchall():
            devices.append({
                "id": row[0],
                "name": row[1],
                "device_type": row[2],
                "mac_address": row[3],
                "firmware_version": row[4],
                "location": row[5],
                "group_id": row[6],
                "status": row[7],
                "last_seen": row[8],
                "configuration": json.loads(row[9]) if row[9] else {},
                "created_at": row[10]
            })
        
        conn.close()
        return {"devices": devices, "count": len(devices)}
    except Exception as e:
        logger.error(f"Error getting IoT devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/iot/fleet/command")
async def send_fleet_command(command_data: dict):
    """Send command to fleet or device group"""
    try:
        conn = sqlite3.connect('hardware_ecosystem.db')
        cursor = conn.cursor()
        
        # Get target devices
        if command_data.get('group_id'):
            cursor.execute("SELECT id FROM iot_devices WHERE group_id = ?", (command_data['group_id'],))
            target_devices = [row[0] for row in cursor.fetchall()]
        else:
            target_devices = command_data.get('device_ids', [])
        
        # Record command execution
        command_id = str(uuid.uuid4())
        execution_results = []
        
        for device_id in target_devices:
            # Simulate command execution
            success = random.choice([True, True, True, False])  # 75% success rate
            result = {
                "device_id": device_id,
                "status": "success" if success else "failed",
                "response": f"Command executed successfully on {device_id}" if success else "Command failed",
                "timestamp": datetime.utcnow().isoformat()
            }
            execution_results.append(result)
        
        conn.close()
        
        return {
            "command_id": command_id,
            "command": command_data['command'],
            "target_count": len(target_devices),
            "results": execution_results,
            "success_rate": sum(1 for r in execution_results if r['status'] == 'success') / len(execution_results)
        }
    except Exception as e:
        logger.error(f"Error sending fleet command: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def simulate_ota_update(update_id: int):
    """Simulate OTA update process"""
    await asyncio.sleep(10)  # Simulate update time
    
    conn = sqlite3.connect('hardware_ecosystem.db')
    cursor = conn.cursor()
    
    cursor.execute("""
    UPDATE ota_updates 
    SET status = 'completed', completed_at = ?
    WHERE id = ?
    """, (datetime.utcnow().isoformat(), update_id))
    
    conn.commit()
    conn.close()

# === WebSocket Endpoint ===

@app.websocket("/ws/ecosystem")
async def ecosystem_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time ecosystem updates"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        # Send initial status
        status = await get_system_status()
        await websocket.send_text(json.dumps({
            "type": "initial_status",
            "data": status
        }))
        
        while True:
            # Keep connection alive and handle client messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            elif message.get("type") == "subscribe":
                # Handle subscriptions for specific updates
                subscription_type = message.get("subscription")
                await websocket.send_text(json.dumps({
                    "type": "subscription_confirmed",
                    "subscription": subscription_type
                }))
                
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)

if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8422,
        reload=True,
        log_level="info"
    )