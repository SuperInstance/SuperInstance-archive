"""
Engine Monitor Service
Comprehensive marine engine monitoring system with advanced features

Port: 8378
Features:
- NMEA 2000 gateway integration
- Analog gauge digitization with computer vision
- CAN bus integration for engine data
- Custom sensor support with multiple interfaces
- Real-time gauge display with professional UI
- Alarm threshold management and alerts
- Historical data logging and analysis
- Predictive maintenance algorithms
- Fuel efficiency tracking and optimization
- Parts ordering integration
- Installation guidance and documentation
- Wiring diagram generator
"""

import asyncio
import logging
import os
import json
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from pydantic import BaseModel, Field

# Import all engine monitoring modules
from nmea.nmea2000_gateway import NMEA2000Gateway, EngineData, NMEA2000Message
from analog.gauge_digitization import AnalogGaugeDigitizer, GaugeCalibration, GaugeType
from canbus.can_integration import CANBusManager, CANMessage, EngineCANData
from sensors.custom_sensors import CustomSensorManager, SensorConfiguration, SensorType
from wiring.diagram_generator import WiringDiagramGenerator, InstallationGuide

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Engine Monitor Service",
    description="Comprehensive marine engine monitoring system with advanced diagnostics",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8088"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global managers
nmea_gateway: Optional[NMEA2000Gateway] = None
gauge_digitizer: Optional[AnalogGaugeDigitizer] = None
can_manager: Optional[CANBusManager] = None
sensor_manager: Optional[CustomSensorManager] = None

# WebSocket connections
websocket_connections: Dict[str, WebSocket] = {}

# Data storage for real-time display
engine_data_cache: Dict[str, Any] = {}
alarm_history: List[Dict[str, Any]] = []
maintenance_schedule: List[Dict[str, Any]] = []


# Pydantic models
class EngineAlarmThreshold(BaseModel):
    parameter: str
    low_warning: Optional[float] = None
    high_warning: Optional[float] = None
    low_alarm: Optional[float] = None
    high_alarm: Optional[float] = None
    enabled: bool = True


class MaintenanceTask(BaseModel):
    task_id: str
    engine_id: int
    task_type: str
    description: str
    due_date: str
    priority: str = "medium"
    estimated_hours: float = 1.0
    parts_required: List[str] = []


class FuelEfficiencyRequest(BaseModel):
    engine_id: int
    start_time: str
    end_time: str
    fuel_consumed: float
    distance_traveled: Optional[float] = None
    operating_hours: Optional[float] = None


@app.on_event("startup")
async def startup_event():
    """Initialize all monitoring systems"""
    global nmea_gateway, gauge_digitizer, can_manager, sensor_manager
    
    logger.info("Starting Engine Monitor Service")
    
    try:
        # Initialize NMEA 2000 gateway
        nmea_gateway = NMEA2000Gateway("can0")
        await nmea_gateway.start_gateway()
        nmea_gateway.subscribe_to_updates(handle_nmea_engine_data)
        
        # Initialize analog gauge digitizer
        gauge_digitizer = AnalogGaugeDigitizer()
        gauge_digitizer.subscribe_to_readings(handle_gauge_reading)
        await gauge_digitizer.start_monitoring()
        
        # Initialize CAN bus manager
        can_manager = CANBusManager()
        can_manager.add_interface("can0", 250000)
        can_manager.subscribe_to_messages(handle_can_message)
        await can_manager.start_monitoring()
        
        # Initialize custom sensor manager
        sensor_manager = CustomSensorManager()
        sensor_manager.subscribe_to_readings(handle_sensor_reading)
        await sensor_manager.start_monitoring()
        
        # Create demo sensors and gauges
        await create_demo_configuration()
        
        # Start background tasks
        asyncio.create_task(predictive_maintenance_task())
        asyncio.create_task(fuel_efficiency_analyzer())
        asyncio.create_task(alarm_processor())
        
        logger.info("All engine monitoring systems initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize engine monitoring systems: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Engine Monitor Service")
    
    try:
        if nmea_gateway:
            await nmea_gateway.stop_gateway()
        
        if gauge_digitizer:
            await gauge_digitizer.stop_monitoring()
        
        if can_manager:
            await can_manager.stop_monitoring()
        
        if sensor_manager:
            await sensor_manager.stop_monitoring()
            
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


async def create_demo_configuration():
    """Create demonstration configuration"""
    try:
        # Add demo analog gauges
        from analog.gauge_digitization import GaugeCalibration, GaugeType
        
        gauges = [
            GaugeCalibration(
                gauge_id="oil_pressure_gauge",
                gauge_type=GaugeType.CIRCULAR,
                center_x=200, center_y=200, radius=150,
                start_angle=-135, end_angle=135,
                min_value=0, max_value=500, units="kPa",
                roi_x=50, roi_y=50, roi_width=300, roi_height=300
            ),
            GaugeCalibration(
                gauge_id="coolant_temp_gauge", 
                gauge_type=GaugeType.CIRCULAR,
                center_x=200, center_y=200, radius=150,
                start_angle=-135, end_angle=135,
                min_value=60, max_value=120, units="°C",
                roi_x=50, roi_y=50, roi_width=300, roi_height=300
            )
        ]
        
        for gauge in gauges:
            gauge_digitizer.add_gauge(gauge)
        
        # Add demo custom sensors
        from sensors.custom_sensors import SensorConfiguration, SensorType, SensorInterface
        
        sensors = [
            SensorConfiguration(
                sensor_id="fuel_flow_sensor",
                name="Fuel Flow Rate",
                sensor_type=SensorType.FLOW_RATE,
                interface=SensorInterface.ANALOG_4_20MA,
                unit="L/hr",
                min_value=0, max_value=50,
                sampling_rate_hz=2.0,
                high_warning=40, high_alarm=45,
                description="Main engine fuel flow sensor"
            ),
            SensorConfiguration(
                sensor_id="exhaust_temp_sensor",
                name="Exhaust Gas Temperature",
                sensor_type=SensorType.TEMPERATURE,
                interface=SensorInterface.MODBUS_RTU,
                unit="°C",
                min_value=200, max_value=800,
                interface_params={
                    'slave_id': 1,
                    'register_address': 100,
                    'data_type': 'float32'
                },
                high_warning=650, high_alarm=700,
                description="Turbocharger exhaust temperature"
            )
        ]
        
        for sensor in sensors:
            sensor_manager.add_sensor(sensor)
        
        logger.info("Created demo configuration")
        
    except Exception as e:
        logger.error(f"Failed to create demo configuration: {e}")


# Data handlers
async def handle_nmea_engine_data(engine_data: EngineData):
    """Handle NMEA 2000 engine data updates"""
    try:
        engine_data_cache[f"nmea_engine_{engine_data.engine_id}"] = engine_data.to_dict()
        await broadcast_to_websockets({
            "type": "nmea_engine_data",
            "data": engine_data.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error handling NMEA engine data: {e}")


async def handle_gauge_reading(reading):
    """Handle analog gauge reading updates"""
    try:
        engine_data_cache[f"gauge_{reading.gauge_id}"] = reading.to_dict()
        await broadcast_to_websockets({
            "type": "gauge_reading",
            "data": reading.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error handling gauge reading: {e}")


async def handle_can_message(message):
    """Handle CAN bus message updates"""
    try:
        # Store CAN data in cache
        if hasattr(message, 'to_dict'):
            await broadcast_to_websockets({
                "type": "can_message",
                "data": message.to_dict()
            })
        
    except Exception as e:
        logger.error(f"Error handling CAN message: {e}")


async def handle_sensor_reading(reading):
    """Handle custom sensor reading updates"""
    try:
        engine_data_cache[f"sensor_{reading.sensor_id}"] = reading.to_dict()
        await broadcast_to_websockets({
            "type": "sensor_reading",
            "data": reading.to_dict()
        })
        
        # Check for alarms
        if 'alarms' in reading.metadata:
            alarm = {
                "id": str(uuid.uuid4()),
                "type": "sensor_alarm",
                "sensor_id": reading.sensor_id,
                "value": reading.value,
                "alarms": reading.metadata['alarms'],
                "timestamp": reading.timestamp.isoformat(),
                "acknowledged": False
            }
            alarm_history.append(alarm)
            
            await broadcast_to_websockets({
                "type": "alarm",
                "data": alarm
            })
        
    except Exception as e:
        logger.error(f"Error handling sensor reading: {e}")


# Background tasks
async def predictive_maintenance_task():
    """Background task for predictive maintenance analysis"""
    while True:
        try:
            await asyncio.sleep(300)  # Run every 5 minutes
            
            # Analyze engine data for maintenance predictions
            for engine_key, data in engine_data_cache.items():
                if "engine" in engine_key and isinstance(data, dict):
                    await analyze_maintenance_needs(data)
            
        except Exception as e:
            logger.error(f"Error in predictive maintenance task: {e}")
            await asyncio.sleep(60)


async def analyze_maintenance_needs(engine_data: Dict[str, Any]):
    """Analyze engine data for maintenance needs"""
    try:
        engine_id = engine_data.get('engine_id', 0)
        
        # Oil analysis
        oil_pressure = engine_data.get('oil_pressure')
        if oil_pressure and oil_pressure < 250:
            task = MaintenanceTask(
                task_id=f"oil_service_{engine_id}_{int(time.time())}",
                engine_id=engine_id,
                task_type="oil_service",
                description="Low oil pressure detected - check oil level and filter",
                due_date=(datetime.now() + timedelta(days=7)).isoformat(),
                priority="high",
                estimated_hours=2.0,
                parts_required=["oil_filter", "engine_oil"]
            )
            
            # Check if task already exists
            existing = next((t for t in maintenance_schedule 
                           if t.get('engine_id') == engine_id and t.get('task_type') == 'oil_service'), None)
            
            if not existing:
                maintenance_schedule.append(task.dict())
                logger.info(f"Added maintenance task: {task.description}")
        
        # Temperature analysis
        coolant_temp = engine_data.get('coolant_temp')
        if coolant_temp and coolant_temp > 95:
            task = MaintenanceTask(
                task_id=f"cooling_service_{engine_id}_{int(time.time())}",
                engine_id=engine_id,
                task_type="cooling_service", 
                description="High coolant temperature - inspect cooling system",
                due_date=(datetime.now() + timedelta(days=3)).isoformat(),
                priority="high",
                estimated_hours=3.0,
                parts_required=["coolant", "thermostat", "water_pump_impeller"]
            )
            
            existing = next((t for t in maintenance_schedule 
                           if t.get('engine_id') == engine_id and t.get('task_type') == 'cooling_service'), None)
            
            if not existing:
                maintenance_schedule.append(task.dict())
                logger.info(f"Added maintenance task: {task.description}")
        
        # Operating hours analysis
        operating_hours = engine_data.get('operating_hours')
        if operating_hours:
            # Schedule routine maintenance based on hours
            if operating_hours % 100 < 1:  # Every 100 hours
                task = MaintenanceTask(
                    task_id=f"routine_100h_{engine_id}_{int(operating_hours)}",
                    engine_id=engine_id,
                    task_type="routine_maintenance",
                    description=f"100-hour routine maintenance at {operating_hours:.1f} hours",
                    due_date=(datetime.now() + timedelta(days=14)).isoformat(),
                    priority="medium",
                    estimated_hours=4.0,
                    parts_required=["engine_oil", "oil_filter", "air_filter", "fuel_filter"]
                )
                
                existing = next((t for t in maintenance_schedule 
                               if t.get('task_id') == task.task_id), None)
                
                if not existing:
                    maintenance_schedule.append(task.dict())
                    logger.info(f"Scheduled routine maintenance: {task.description}")
        
    except Exception as e:
        logger.error(f"Error analyzing maintenance needs: {e}")


async def fuel_efficiency_analyzer():
    """Background task for fuel efficiency analysis"""
    while True:
        try:
            await asyncio.sleep(600)  # Run every 10 minutes
            
            # Analyze fuel efficiency trends - create copy to avoid iteration errors
            engine_data_snapshot = dict(engine_data_cache)
            for engine_key, data in engine_data_snapshot.items():
                if "engine" in engine_key and isinstance(data, dict):
                    await calculate_fuel_efficiency(data)
            
        except Exception as e:
            logger.error(f"Error in fuel efficiency analyzer: {e}")
            await asyncio.sleep(60)


async def calculate_fuel_efficiency(engine_data: Dict[str, Any]):
    """Calculate real-time fuel efficiency metrics"""
    try:
        fuel_rate = engine_data.get('fuel_rate')  # L/hr
        rpm = engine_data.get('rpm')
        engine_load = engine_data.get('engine_load')
        
        if fuel_rate and rpm:
            # Calculate fuel efficiency metrics
            fuel_per_rev = fuel_rate / (rpm * 60) if rpm > 0 else 0
            
            # Calculate efficiency rating based on load and consumption
            if engine_load and engine_load > 0:
                efficiency_ratio = engine_load / fuel_rate if fuel_rate > 0 else 0
                
                # Store efficiency data
                efficiency_data = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "engine_id": engine_data.get('engine_id', 0),
                    "fuel_rate": fuel_rate,
                    "rpm": rpm,
                    "engine_load": engine_load,
                    "fuel_per_rev": fuel_per_rev,
                    "efficiency_ratio": efficiency_ratio,
                    "efficiency_rating": "good" if efficiency_ratio > 5 else "fair" if efficiency_ratio > 3 else "poor"
                }
                
                engine_data_cache[f"efficiency_{engine_data.get('engine_id', 0)}"] = efficiency_data
                
                await broadcast_to_websockets({
                    "type": "fuel_efficiency",
                    "data": efficiency_data
                })
        
    except Exception as e:
        logger.error(f"Error calculating fuel efficiency: {e}")


async def alarm_processor():
    """Background task for processing alarms"""
    while True:
        try:
            await asyncio.sleep(10)  # Process every 10 seconds
            
            # Process unacknowledged alarms
            unack_alarms = [a for a in alarm_history if not a.get('acknowledged', False)]
            
            # Auto-escalate critical alarms
            for alarm in unack_alarms:
                alarm_age = (datetime.now(timezone.utc) - 
                           datetime.fromisoformat(alarm['timestamp'].replace('Z', '+00:00'))).total_seconds()
                
                if alarm_age > 300 and 'ALARM' in str(alarm.get('alarms', [])):  # 5 minutes
                    alarm['escalated'] = True
                    logger.warning(f"Escalated unacknowledged alarm: {alarm['id']}")
                    
                    await broadcast_to_websockets({
                        "type": "alarm_escalation",
                        "data": alarm
                    })
            
        except Exception as e:
            logger.error(f"Error in alarm processor: {e}")
            await asyncio.sleep(60)


# WebSocket management
async def broadcast_to_websockets(message: Dict[str, Any]):
    """Broadcast message to all connected WebSocket clients"""
    if not websocket_connections:
        return
    
    message_str = json.dumps(message, default=str)
    disconnected = []
    
    for connection_id, websocket in websocket_connections.items():
        try:
            await websocket.send_text(message_str)
        except Exception as e:
            logger.warning(f"Failed to send to WebSocket {connection_id}: {e}")
            disconnected.append(connection_id)
    
    # Clean up disconnected clients
    for connection_id in disconnected:
        del websocket_connections[connection_id]


# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "engine-monitor",
        "port": 8378,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "nmea_gateway": nmea_gateway is not None,
            "gauge_digitizer": gauge_digitizer is not None,
            "can_manager": can_manager is not None,
            "sensor_manager": sensor_manager is not None
        }
    }


# Main UI endpoint
@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Engine Monitor System</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Arial', sans-serif; 
            background: linear-gradient(135deg, #1e3c72, #2a5298);
            color: white; 
            min-height: 100vh;
        }
        .header {
            background: rgba(0,0,0,0.3);
            padding: 1rem;
            border-bottom: 2px solid #FF6B35;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .container { 
            display: grid; 
            grid-template-columns: 1fr 2fr 1fr;
            grid-template-rows: auto 1fr auto;
            height: calc(100vh - 80px);
            gap: 1rem;
            padding: 1rem;
        }
        .panel {
            background: rgba(0,0,0,0.4);
            border-radius: 8px;
            padding: 1rem;
            border: 1px solid rgba(255,255,255,0.2);
            overflow-y: auto;
        }
        .gauge-display {
            background: rgba(0,0,0,0.6);
            border-radius: 8px;
            position: relative;
            min-height: 400px;
            border: 2px solid #FF6B35;
            display: flex;
            flex-wrap: wrap;
            gap: 1rem;
            padding: 1rem;
        }
        .gauge {
            width: 200px;
            height: 200px;
            position: relative;
            background: radial-gradient(circle, rgba(255,107,53,0.1) 0%, transparent 70%);
            border-radius: 50%;
            border: 3px solid #FF6B35;
        }
        .gauge-needle {
            position: absolute;
            top: 50%;
            left: 50%;
            width: 3px;
            height: 80px;
            background: linear-gradient(to top, #FF6B35, #FF8C42);
            transform-origin: bottom center;
            transform: translate(-50%, -100%) rotate(45deg);
            animation: needle-sweep 3s ease-in-out infinite alternate;
        }
        @keyframes needle-sweep {
            from { transform: translate(-50%, -100%) rotate(-45deg); }
            to { transform: translate(-50%, -100%) rotate(135deg); }
        }
        .gauge-label {
            position: absolute;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            font-weight: bold;
            font-size: 0.9em;
        }
        .gauge-value {
            position: absolute;
            top: 70%;
            left: 50%;
            transform: translateX(-50%);
            font-size: 1.2em;
            font-weight: bold;
            color: #FF6B35;
        }
        .data-item {
            background: rgba(255,107,53,0.2);
            border-left: 4px solid #FF6B35;
            padding: 0.5rem;
            margin: 0.5rem 0;
            border-radius: 4px;
            font-size: 0.9em;
        }
        .alarm-item {
            background: rgba(255,0,0,0.2);
            border-left: 4px solid #ff4444;
            padding: 0.5rem;
            margin: 0.5rem 0;
            border-radius: 4px;
        }
        .status-ok { border-left-color: #4CAF50; background: rgba(76,175,80,0.2); }
        .status-warning { border-left-color: #FF9800; background: rgba(255,152,0,0.2); }
        .btn {
            background: #FF6B35;
            border: none;
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            cursor: pointer;
            margin: 0.25rem;
        }
        .btn:hover { background: #FF8C42; }
        .btn-danger { background: #f44336; }
        .btn-danger:hover { background: #da190b; }
        .btn-small {
            background: #4CAF50;
            border: none;
            color: white;
            padding: 0.25rem 0.5rem;
            border-radius: 3px;
            cursor: pointer;
            font-size: 0.8em;
            margin-left: 0.5rem;
        }
        .btn-small:hover { background: #45a049; }
        .select-input {
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.3);
            color: white;
            padding: 0.3rem;
            border-radius: 3px;
            width: 100%;
            margin-bottom: 0.5rem;
        }
        .select-input option {
            background: #1e3c72;
            color: white;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.5rem;
            font-size: 0.85em;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔧 Engine Monitor System - Port 8378</h1>
        <div>
            Status: <span id="status">Connecting...</span> | 
            Engines: <span id="engine-count">0</span> | 
            Alarms: <span id="alarm-count">0</span>
        </div>
    </div>
    
    <div class="container">
        <div class="panel">
            <h3>🚨 Active Alarms</h3>
            <div id="alarms">
                <div class="alarm-item status-ok">✅ All Systems Normal</div>
            </div>
            
            <h3 style="margin-top: 1rem;">⚙️ Controls</h3>
            <button class="btn" onclick="testAlarm()">🔊 Test Alarm</button>
            <button class="btn" onclick="silenceAlarms()">🔇 Silence All</button>
            <button class="btn" onclick="emergencyShutdown()">🛑 Emergency Shutdown</button>
            
            <h3 style="margin-top: 1rem;">🔌 Wiring Diagrams</h3>
            <button class="btn" onclick="showWiringDiagrams()">📋 View Templates</button>
            <button class="btn" onclick="generateDiagram()">⚡ Generate Diagram</button>
            <div id="wiring-section" style="display: none; margin-top: 0.5rem;">
                <select id="diagram-template" class="select-input">
                    <option value="">Select Configuration...</option>
                    <option value="single_engine_basic">Single Engine - Basic</option>
                    <option value="single_engine_advanced">Single Engine - Advanced</option>
                    <option value="twin_engine_basic">Twin Engine - Basic</option>
                    <option value="twin_engine_advanced">Twin Engine - Advanced</option>
                </select>
                <button class="btn-small" onclick="createWiringDiagram()">Create</button>
            </div>
            
            <h3 style="margin-top: 1rem;">🔧 Maintenance</h3>
            <div id="maintenance">
                <div class="data-item">✅ All maintenance current</div>
            </div>
        </div>
        
        <div class="gauge-display">
            <h3 style="position: absolute; top: 1rem; left: 1rem; z-index: 10;">📊 Engine Gauges</h3>
            
            <div class="gauge">
                <div class="gauge-needle" id="rpm-needle"></div>
                <div class="gauge-label">RPM</div>
                <div class="gauge-value" id="rpm-value">1800</div>
            </div>
            
            <div class="gauge">
                <div class="gauge-needle" id="temp-needle"></div>
                <div class="gauge-label">Coolant Temp (°C)</div>
                <div class="gauge-value" id="temp-value">85</div>
            </div>
            
            <div class="gauge">
                <div class="gauge-needle" id="oil-needle"></div>
                <div class="gauge-label">Oil Pressure (kPa)</div>
                <div class="gauge-value" id="oil-value">350</div>
            </div>
            
            <div class="gauge">
                <div class="gauge-needle" id="fuel-needle"></div>
                <div class="gauge-label">Fuel Rate (L/hr)</div>
                <div class="gauge-value" id="fuel-value">15.5</div>
            </div>
        </div>
        
        <div class="panel">
            <h3>📊 Engine Data</h3>
            <div id="engine-data">
                <div class="data-item">🔋 Battery: 13.8V</div>
                <div class="data-item">🌡️ Exhaust: 420°C</div>
                <div class="data-item">💨 Boost: 150kPa</div>
                <div class="data-item">⚡ Alternator: 85A</div>
            </div>
            
            <h3 style="margin-top: 1rem;">⛽ Fuel Efficiency</h3>
            <div id="efficiency">
                <div class="data-item status-ok">📈 Rating: Good</div>
                <div class="data-item">📊 L/hr per load: 0.23</div>
            </div>
            
            <h3 style="margin-top: 1rem;">🔌 System Status</h3>
            <div class="stats-grid">
                <div>NMEA 2000: <span id="nmea-status">●</span></div>
                <div>CAN Bus: <span id="can-status">●</span></div>
                <div>Gauges: <span id="gauge-status">●</span></div>
                <div>Sensors: <span id="sensor-status">●</span></div>
            </div>
        </div>
    </div>

    <script>
        let ws = null;
        let engineData = {};

        // WebSocket connection
        function connectWebSocket() {
            ws = new WebSocket(`ws://localhost:8378/ws/${Math.random().toString(36).substr(2, 9)}`);
            
            ws.onopen = function() {
                document.getElementById('status').textContent = 'Connected';
                document.getElementById('status').style.color = '#4CAF50';
                updateSystemStatus();
            };
            
            ws.onmessage = function(event) {
                const message = JSON.parse(event.data);
                handleWebSocketMessage(message);
            };
            
            ws.onclose = function() {
                document.getElementById('status').textContent = 'Disconnected';
                document.getElementById('status').style.color = '#f44336';
                setTimeout(connectWebSocket, 3000);
            };
        }

        function handleWebSocketMessage(message) {
            console.log('Received:', message);
            
            switch(message.type) {
                case 'nmea_engine_data':
                    updateEngineData('nmea', message.data);
                    break;
                case 'sensor_reading':
                    updateSensorData(message.data);
                    break;
                case 'gauge_reading':
                    updateGaugeData(message.data);
                    break;
                case 'alarm':
                    addAlarm(message.data);
                    break;
                case 'fuel_efficiency':
                    updateFuelEfficiency(message.data);
                    break;
            }
        }

        function updateEngineData(source, data) {
            engineData[source] = data;
            
            // Update gauge displays
            if (data.rpm) {
                document.getElementById('rpm-value').textContent = Math.round(data.rpm);
                updateGaugeNeedle('rpm-needle', data.rpm, 0, 3000);
            }
            
            if (data.coolant_temp) {
                document.getElementById('temp-value').textContent = Math.round(data.coolant_temp);
                updateGaugeNeedle('temp-needle', data.coolant_temp, 60, 120);
            }
            
            if (data.oil_pressure) {
                document.getElementById('oil-value').textContent = Math.round(data.oil_pressure);
                updateGaugeNeedle('oil-needle', data.oil_pressure, 0, 500);
            }
            
            if (data.fuel_rate) {
                document.getElementById('fuel-value').textContent = data.fuel_rate.toFixed(1);
                updateGaugeNeedle('fuel-needle', data.fuel_rate, 0, 50);
            }
            
            // Update data panel
            updateDataPanel(data);
        }

        function updateGaugeNeedle(needleId, value, min, max) {
            const needle = document.getElementById(needleId);
            if (needle) {
                // Convert value to angle (-135° to 135°)
                const percentage = Math.max(0, Math.min(1, (value - min) / (max - min)));
                const angle = -135 + (percentage * 270);
                needle.style.transform = `translate(-50%, -100%) rotate(${angle}deg)`;
            }
        }

        function updateSensorData(data) {
            console.log('Sensor data:', data);
        }

        function updateGaugeData(data) {
            console.log('Gauge data:', data);
        }

        function updateDataPanel(data) {
            const dataDiv = document.getElementById('engine-data');
            dataDiv.innerHTML = '';
            
            if (data.battery_voltage) {
                dataDiv.innerHTML += `<div class="data-item">🔋 Battery: ${data.battery_voltage.toFixed(1)}V</div>`;
            }
            if (data.exhaust_gas_temp) {
                dataDiv.innerHTML += `<div class="data-item">🌡️ Exhaust: ${Math.round(data.exhaust_gas_temp)}°C</div>`;
            }
            if (data.turbo_boost) {
                dataDiv.innerHTML += `<div class="data-item">💨 Boost: ${Math.round(data.turbo_boost)}kPa</div>`;
            }
            if (data.alternator_load) {
                dataDiv.innerHTML += `<div class="data-item">⚡ Alternator: ${Math.round(data.alternator_load)}A</div>`;
            }
        }

        function updateFuelEfficiency(data) {
            const effDiv = document.getElementById('efficiency');
            effDiv.innerHTML = `
                <div class="data-item status-${data.efficiency_rating === 'good' ? 'ok' : 'warning'}">📈 Rating: ${data.efficiency_rating}</div>
                <div class="data-item">📊 Efficiency: ${data.efficiency_ratio.toFixed(2)}</div>
            `;
        }

        function addAlarm(alarm) {
            const alarmsDiv = document.getElementById('alarms');
            const alarmDiv = document.createElement('div');
            alarmDiv.className = 'alarm-item';
            alarmDiv.innerHTML = `🚨 ${alarm.sensor_id}: ${alarm.alarms.join(', ')} (${alarm.value})`;
            alarmsDiv.insertBefore(alarmDiv, alarmsDiv.firstChild);
            
            updateAlarmCount();
        }

        function updateAlarmCount() {
            const alarms = document.querySelectorAll('.alarm-item').length - 1;
            document.getElementById('alarm-count').textContent = Math.max(0, alarms);
        }

        function updateSystemStatus() {
            document.getElementById('nmea-status').style.color = '#4CAF50';
            document.getElementById('can-status').style.color = '#4CAF50';
            document.getElementById('gauge-status').style.color = '#4CAF50';
            document.getElementById('sensor-status').style.color = '#4CAF50';
        }

        function testAlarm() {
            fetch('/api/test-alarm', { method: 'POST' })
                .then(() => addAlarm({
                    sensor_id: 'test_sensor',
                    alarms: ['test_alarm'],
                    value: 999
                }))
                .catch(err => console.error(err));
        }

        function silenceAlarms() {
            document.querySelectorAll('.alarm-item').forEach(item => {
                if (!item.classList.contains('status-ok')) {
                    item.style.opacity = '0.5';
                }
            });
        }

        function emergencyShutdown() {
            if (confirm('Initiate emergency engine shutdown?')) {
                fetch('/api/emergency-shutdown', { method: 'POST' })
                    .then(() => alert('Emergency shutdown initiated'))
                    .catch(err => console.error(err));
            }
        }

        // Wiring diagram functions
        function showWiringDiagrams() {
            const section = document.getElementById('wiring-section');
            section.style.display = section.style.display === 'none' ? 'block' : 'none';
        }

        function generateDiagram() {
            showWiringDiagrams();
        }

        function createWiringDiagram() {
            const templateSelect = document.getElementById('diagram-template');
            const templateId = templateSelect.value;
            
            if (!templateId) {
                alert('Please select a configuration template');
                return;
            }

            // Create configuration based on template
            const config = {
                template_id: templateId,
                vessel_name: "Marine Vessel",
                installer_name: "Certified Marine Electrician"
            };

            // Generate the wiring diagram
            fetch('/api/wiring/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(config)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    displayWiringResults(data);
                } else {
                    alert('Error generating diagram: ' + data.detail);
                }
            })
            .catch(err => {
                console.error('Error:', err);
                alert('Failed to generate wiring diagram');
            });
        }

        function displayWiringResults(data) {
            const resultDiv = document.createElement('div');
            resultDiv.innerHTML = `
                <div style="background: rgba(0,0,0,0.8); position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 1000; display: flex; align-items: center; justify-content: center;" onclick="this.remove()">
                    <div style="background: #1e3c72; padding: 2rem; border-radius: 8px; max-width: 80%; max-height: 80%; overflow-y: auto; color: white;" onclick="event.stopPropagation()">
                        <h2>🔌 Wiring Diagram Generated</h2>
                        <p><strong>Diagram ID:</strong> ${data.diagram_id}</p>
                        <p><strong>Estimated Cost:</strong> $${data.estimated_cost.toFixed(2)}</p>
                        
                        <h3>📋 Parts List (${data.parts_list.parts.length} items)</h3>
                        <div style="max-height: 200px; overflow-y: auto; margin: 1rem 0;">
                            ${data.parts_list.parts.map(part => 
                                `<div style="margin: 0.5rem 0; padding: 0.5rem; background: rgba(255,255,255,0.1); border-radius: 4px;">
                                    <strong>${part.name}</strong> - ${part.part_number}<br>
                                    Qty: ${part.quantity} | $${part.estimated_cost.toFixed(2)}
                                </div>`
                            ).join('')}
                        </div>
                        
                        <h3>📖 Installation Steps</h3>
                        <div style="max-height: 200px; overflow-y: auto;">
                            ${data.installation_guide.steps.map((step, i) => 
                                `<div style="margin: 0.5rem 0;"><strong>${i+1}.</strong> ${step}</div>`
                            ).join('')}
                        </div>
                        
                        <button class="btn" onclick="this.parentElement.parentElement.remove()">Close</button>
                        <button class="btn" onclick="downloadWiringData('${data.diagram_id}')">Download Full Report</button>
                    </div>
                </div>
            `;
            document.body.appendChild(resultDiv);
        }

        function downloadWiringData(diagramId) {
            // In a real implementation, this would download a PDF or detailed report
            alert('Wiring diagram report would be downloaded for diagram: ' + diagramId);
        }

        // Initialize
        connectWebSocket();
        
        // Simulate some data updates
        setInterval(() => {
            document.getElementById('engine-count').textContent = Object.keys(engineData).length;
        }, 1000);
    </script>
</body>
</html>
    """


# WebSocket endpoint
@app.websocket("/ws/{connection_id}")
async def websocket_endpoint(websocket: WebSocket, connection_id: str):
    await websocket.accept()
    websocket_connections[connection_id] = websocket
    
    logger.info(f"WebSocket connection {connection_id} established")
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket connection {connection_id} disconnected")
    finally:
        websocket_connections.pop(connection_id, None)


# API Endpoints
@app.get("/api/engines")
async def get_engines():
    """Get all engine data"""
    try:
        return {
            "engines": engine_data_cache,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting engine data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/alarms")
async def get_alarms():
    """Get all alarms"""
    try:
        return {
            "alarms": alarm_history[-100:],  # Last 100 alarms
            "active_alarms": [a for a in alarm_history if not a.get('acknowledged', False)],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting alarms: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/maintenance")
async def get_maintenance_schedule():
    """Get maintenance schedule"""
    try:
        return {
            "tasks": maintenance_schedule,
            "overdue_tasks": [t for t in maintenance_schedule 
                             if datetime.fromisoformat(t['due_date']) < datetime.now(timezone.utc)],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting maintenance schedule: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/system-status")
async def get_system_status():
    """Get comprehensive system status"""
    try:
        nmea_stats = nmea_gateway.get_gateway_statistics() if nmea_gateway else {}
        can_stats = can_manager.get_can_statistics() if can_manager else {}
        
        return {
            "service": "engine-monitor",
            "port": 8378,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "nmea_gateway": nmea_stats,
            "can_bus": can_stats,
            "analog_gauges": len(gauge_digitizer.gauges) if gauge_digitizer else 0,
            "custom_sensors": len(sensor_manager.sensors) if sensor_manager else 0,
            "websocket_connections": len(websocket_connections),
            "cached_data_points": len(engine_data_cache),
            "total_alarms": len(alarm_history),
            "maintenance_tasks": len(maintenance_schedule)
        }
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/test-alarm")
async def test_alarm():
    """Trigger test alarm"""
    alarm = {
        "id": str(uuid.uuid4()),
        "type": "test_alarm",
        "sensor_id": "test_sensor",
        "value": 999,
        "alarms": ["test_high_alarm"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "acknowledged": False
    }
    
    alarm_history.append(alarm)
    
    await broadcast_to_websockets({
        "type": "alarm",
        "data": alarm
    })
    
    return {"success": True, "alarm_id": alarm["id"]}


@app.post("/api/emergency-shutdown")
async def emergency_shutdown():
    """Emergency engine shutdown"""
    logger.critical("EMERGENCY SHUTDOWN INITIATED")
    
    # In a real system, this would trigger actual shutdown procedures
    shutdown_alarm = {
        "id": str(uuid.uuid4()),
        "type": "emergency_shutdown",
        "sensor_id": "system",
        "value": 0,
        "alarms": ["emergency_shutdown_activated"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "acknowledged": False
    }
    
    alarm_history.append(shutdown_alarm)
    
    await broadcast_to_websockets({
        "type": "alarm",
        "data": shutdown_alarm
    })
    
    return {"success": True, "message": "Emergency shutdown initiated"}


# Wiring Diagram API Endpoints
@app.get("/api/wiring/diagrams")
async def get_available_diagrams():
    """Get list of available wiring diagram templates"""
    try:
        diagram_generator = WiringDiagramGenerator()
        
        # Get available engine configurations
        configurations = [
            {
                "id": "single_engine_basic",
                "name": "Single Engine - Basic Monitoring",
                "description": "Basic engine monitoring setup with essential sensors",
                "engine_count": 1,
                "sensors": ["rpm", "oil_pressure", "coolant_temp", "fuel_level"]
            },
            {
                "id": "single_engine_advanced",
                "name": "Single Engine - Advanced Monitoring", 
                "description": "Complete engine monitoring with all sensor types",
                "engine_count": 1,
                "sensors": ["rpm", "oil_pressure", "coolant_temp", "fuel_level", "fuel_flow", "exhaust_temp", "transmission_pressure", "alternator_output"]
            },
            {
                "id": "twin_engine_basic",
                "name": "Twin Engine - Basic Monitoring",
                "description": "Twin engine setup with essential monitoring",
                "engine_count": 2,
                "sensors": ["rpm", "oil_pressure", "coolant_temp", "fuel_level"]
            },
            {
                "id": "twin_engine_advanced",
                "name": "Twin Engine - Advanced Monitoring",
                "description": "Complete twin engine monitoring system",
                "engine_count": 2,
                "sensors": ["rpm", "oil_pressure", "coolant_temp", "fuel_level", "fuel_flow", "exhaust_temp", "transmission_pressure", "alternator_output"]
            }
        ]
        
        return {"success": True, "configurations": configurations}
        
    except Exception as e:
        logger.error(f"Error getting diagram configurations: {e}")
        raise HTTPException(status_code=500, detail="Failed to get diagram configurations")


@app.post("/api/wiring/generate")
async def generate_wiring_diagram(config: Dict[str, Any]):
    """Generate a wiring diagram based on configuration"""
    try:
        diagram_generator = WiringDiagramGenerator()
        
        # Generate the diagram
        diagram_result = diagram_generator.create_engine_monitoring_diagram(config)
        
        if diagram_result["success"]:
            diagram_id = diagram_result["diagram_id"]
            
            # Generate parts list
            parts_list = diagram_generator.generate_parts_list(diagram_id)
            
            # Generate installation guide
            installation_guide = InstallationGuide(diagram_generator)
            guide = installation_guide.generate_installation_guide(diagram_id)
            
            return {
                "success": True,
                "diagram_id": diagram_id,
                "diagram": diagram_result["diagram"],
                "parts_list": parts_list,
                "installation_guide": guide,
                "estimated_cost": sum(part.get("estimated_cost", 0) for part in parts_list.get("parts", []))
            }
        else:
            raise HTTPException(status_code=400, detail=diagram_result["error"])
            
    except Exception as e:
        logger.error(f"Error generating wiring diagram: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate wiring diagram")


@app.get("/api/wiring/parts/{diagram_id}")
async def get_parts_list(diagram_id: str):
    """Get parts list for a specific diagram"""
    try:
        diagram_generator = WiringDiagramGenerator()
        parts_list = diagram_generator.generate_parts_list(diagram_id)
        
        return {"success": True, "parts_list": parts_list}
        
    except Exception as e:
        logger.error(f"Error getting parts list: {e}")
        raise HTTPException(status_code=500, detail="Failed to get parts list")


@app.get("/api/wiring/installation/{diagram_id}")
async def get_installation_guide(diagram_id: str):
    """Get installation guide for a specific diagram"""
    try:
        diagram_generator = WiringDiagramGenerator()
        installation_guide = InstallationGuide(diagram_generator)
        guide = installation_guide.generate_installation_guide(diagram_id)
        
        return {"success": True, "installation_guide": guide}
        
    except Exception as e:
        logger.error(f"Error getting installation guide: {e}")
        raise HTTPException(status_code=500, detail="Failed to get installation guide")


@app.post("/api/wiring/validate")
async def validate_wiring_config(config: Dict[str, Any]):
    """Validate a wiring configuration"""
    try:
        diagram_generator = WiringDiagramGenerator()
        validation_result = diagram_generator.validate_configuration(config)
        
        return {"success": True, "validation": validation_result}
        
    except Exception as e:
        logger.error(f"Error validating wiring config: {e}")
        raise HTTPException(status_code=500, detail="Failed to validate configuration")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8378))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )