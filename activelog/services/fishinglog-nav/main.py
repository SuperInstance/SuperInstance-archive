#!/usr/bin/env python3
"""
Professional Marine Navigation System
ECDIS-compliant navigation software with comprehensive maritime features
"""

import os
import json
import logging
from datetime import datetime, timezone
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import threading
import time
from typing import Dict, List, Optional, Tuple
import numpy as np
from geopy.distance import geodesic
import redis
from dotenv import load_dotenv

from src.chart_engine import ECDISChartEngine
from src.ais_tracker import AISTracker
from src.radar_system import ARPARadar
from src.weather_router import WeatherRouter
from src.tide_system import TideCurrentSystem
from src.route_planner import RoutePlanner
from src.mob_system import MOBSystem
from src.track_recorder import TrackRecorder
from src.display_manager import MultiDisplayManager
from src.night_mode import NightModeManager
from src.bathymetric import BathymetricVisualizer
from src.split_screen import SplitScreenManager

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'marine-nav-2024-secure-key')
CORS(app, origins=["*"])
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/activeloguser/activelog/services/fishinglog-nav/navigation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MarineNavigationSystem:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.active_sessions = {}
        self.vessel_position = {"lat": 0.0, "lon": 0.0, "heading": 0.0, "speed": 0.0}
        
        self.chart_engine = ECDISChartEngine()
        self.ais_tracker = AISTracker()
        self.radar_system = ARPARadar()
        self.weather_router = WeatherRouter()
        self.tide_system = TideCurrentSystem()
        self.route_planner = RoutePlanner()
        self.mob_system = MOBSystem()
        self.track_recorder = TrackRecorder()
        self.display_manager = MultiDisplayManager()
        self.night_mode = NightModeManager()
        self.bathymetric = BathymetricVisualizer()
        self.split_screen = SplitScreenManager()
        
        self._setup_background_tasks()
        logger.info("Marine Navigation System initialized")
    
    def _setup_background_tasks(self):
        self.update_thread = threading.Thread(target=self._background_updates, daemon=True)
        self.update_thread.start()
        
        self.ais_thread = threading.Thread(target=self._ais_updates, daemon=True)
        self.ais_thread.start()
        
        self.radar_thread = threading.Thread(target=self._radar_updates, daemon=True)
        self.radar_thread.start()
    
    def _background_updates(self):
        while True:
            try:
                current_pos = self.get_current_position()
                if current_pos:
                    self.track_recorder.add_position(current_pos)
                    self.tide_system.update_position(current_pos)
                    self.weather_router.update_position(current_pos)
                    
                    socketio.emit('position_update', current_pos, namespace='/')
                
                time.sleep(1)
            except Exception as e:
                logger.error(f"Background update error: {e}")
                time.sleep(5)
    
    def _ais_updates(self):
        while True:
            try:
                ais_targets = self.ais_tracker.get_active_targets()
                if ais_targets:
                    collision_risks = self.ais_tracker.calculate_collision_risks(
                        self.vessel_position
                    )
                    
                    socketio.emit('ais_update', {
                        'targets': ais_targets,
                        'collision_risks': collision_risks
                    }, namespace='/')
                
                time.sleep(2)
            except Exception as e:
                logger.error(f"AIS update error: {e}")
                time.sleep(5)
    
    def _radar_updates(self):
        while True:
            try:
                radar_data = self.radar_system.get_processed_data()
                if radar_data:
                    socketio.emit('radar_update', radar_data, namespace='/')
                
                time.sleep(1)
            except Exception as e:
                logger.error(f"Radar update error: {e}")
                time.sleep(5)
    
    def get_current_position(self) -> Optional[Dict]:
        try:
            pos_data = self.redis_client.get('vessel_position')
            if pos_data:
                return json.loads(pos_data)
            return self.vessel_position
        except Exception as e:
            logger.error(f"Position retrieval error: {e}")
            return None
    
    def update_position(self, lat: float, lon: float, heading: float = 0.0, speed: float = 0.0):
        self.vessel_position = {
            "lat": lat,
            "lon": lon,
            "heading": heading,
            "speed": speed,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            self.redis_client.setex(
                'vessel_position', 
                60, 
                json.dumps(self.vessel_position)
            )
        except Exception as e:
            logger.error(f"Position update error: {e}")

nav_system = MarineNavigationSystem()

@app.route('/')
def index():
    return render_template('navigation.html')

@app.route('/helm')
def helm_station():
    return render_template('helm_station.html')

@app.route('/nav-station')
def nav_station():
    return render_template('nav_station.html')

@app.route('/flybridge')
def flybridge():
    return render_template('flybridge.html')

@app.route('/api/position', methods=['GET', 'POST'])
def handle_position():
    if request.method == 'POST':
        data = request.json
        nav_system.update_position(
            data.get('lat', 0.0),
            data.get('lon', 0.0),
            data.get('heading', 0.0),
            data.get('speed', 0.0)
        )
        return jsonify({"status": "updated"})
    else:
        return jsonify(nav_system.get_current_position())

@app.route('/api/charts/load', methods=['POST'])
def load_chart():
    data = request.json
    chart_path = data.get('chart_path')
    
    try:
        chart_data = nav_system.chart_engine.load_chart(chart_path)
        return jsonify({
            "status": "success",
            "chart_data": chart_data
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400

@app.route('/api/route/plan', methods=['POST'])
def plan_route():
    data = request.json
    waypoints = data.get('waypoints', [])
    
    try:
        optimized_route = nav_system.route_planner.optimize_route(waypoints)
        return jsonify({
            "status": "success",
            "route": optimized_route
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400

@app.route('/api/mob/mark', methods=['POST'])
def mark_mob():
    try:
        current_pos = nav_system.get_current_position()
        mob_data = nav_system.mob_system.mark_mob(current_pos)
        
        socketio.emit('mob_alert', mob_data, namespace='/')
        
        return jsonify({
            "status": "success",
            "mob_data": mob_data
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400

@app.route('/api/weather/grib', methods=['POST'])
def load_grib():
    data = request.json
    grib_file = data.get('grib_file')
    
    try:
        weather_data = nav_system.weather_router.load_grib(grib_file)
        return jsonify({
            "status": "success",
            "weather_data": weather_data
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400

@app.route('/api/display/config', methods=['POST'])
def configure_display():
    data = request.json
    display_config = data.get('config')
    
    try:
        nav_system.display_manager.configure_displays(display_config)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400

@app.route('/api/night-mode/<mode>')
def set_night_mode(mode):
    try:
        nav_system.night_mode.set_mode(mode == 'on')
        socketio.emit('night_mode_changed', {'enabled': mode == 'on'}, namespace='/')
        return jsonify({"status": "success", "mode": mode})
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400

@socketio.on('connect')
def handle_connect():
    session_id = request.sid
    nav_system.active_sessions[session_id] = {
        'connected_at': datetime.now(timezone.utc).isoformat(),
        'station_type': 'general'
    }
    
    emit('connected', {'session_id': session_id})
    logger.info(f"Client connected: {session_id}")

@socketio.on('disconnect')
def handle_disconnect():
    session_id = request.sid
    if session_id in nav_system.active_sessions:
        del nav_system.active_sessions[session_id]
    logger.info(f"Client disconnected: {session_id}")

@socketio.on('join_station')
def handle_join_station(data):
    station_type = data.get('station_type', 'general')
    session_id = request.sid
    
    if session_id in nav_system.active_sessions:
        nav_system.active_sessions[session_id]['station_type'] = station_type
    
    join_room(station_type)
    emit('station_joined', {'station_type': station_type})

@socketio.on('radar_control')
def handle_radar_control(data):
    command = data.get('command')
    params = data.get('params', {})
    
    try:
        result = nav_system.radar_system.process_command(command, params)
        emit('radar_response', result)
    except Exception as e:
        emit('radar_error', {'message': str(e)})

@socketio.on('chart_interaction')
def handle_chart_interaction(data):
    interaction_type = data.get('type')
    coordinates = data.get('coordinates')
    
    try:
        if interaction_type == 'waypoint_add':
            nav_system.route_planner.add_waypoint(coordinates)
        elif interaction_type == 'depth_query':
            depth = nav_system.bathymetric.get_depth_at_point(coordinates)
            emit('depth_response', {'coordinates': coordinates, 'depth': depth})
        
        emit('chart_updated', data)
    except Exception as e:
        emit('chart_error', {'message': str(e)})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8365))
    logger.info(f"Starting Marine Navigation System on port {port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=False)