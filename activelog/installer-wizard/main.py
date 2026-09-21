#!/usr/bin/env python3
"""
Installation Wizard - 6-Phase Intelligent Installer
Advanced AI-driven installation experience with adaptive interfaces
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates

# Import intelligent installer components
sys.path.append('/home/activeloguser/activelog/services/intelligent-installer')
from hardware.profiler import HardwareProfiler
from adaptive.interfaces import AdaptiveInterfaceManager
from optimization.optimizer import IntelligentOptimizer

class WizardPhase(Enum):
    WELCOME = "welcome"
    USE_CASE = "use_case"
    TRADE_OFFS = "trade_offs"
    INSTALLATION = "installation"
    FIRST_RUN = "first_run"
    OPTIMIZATION = "optimization"

@dataclass
class UserProfile:
    technical_level: str = "intermediate"
    primary_use_case: str = "general"
    performance_priority: str = "balanced"
    resource_constraints: Dict[str, Any] = None
    preferences: Dict[str, Any] = None
    hardware_profile: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.resource_constraints is None:
            self.resource_constraints = {}
        if self.preferences is None:
            self.preferences = {}
        if self.hardware_profile is None:
            self.hardware_profile = {}

class InstallationWizard:
    def __init__(self):
        self.app = FastAPI(title="ActiveLog Installation Wizard")
        self.templates = Jinja2Templates(directory="templates")
        self.hardware_profiler = HardwareProfiler()
        self.adaptive_interface = AdaptiveInterfaceManager()
        self.optimizer = IntelligentOptimizer()
        
        self.active_sessions = {}
        self.installation_progress = {}
        
        self.setup_routes()
    
    def setup_routes(self):
        @self.app.get("/")
        async def home():
            return FileResponse("templates/index.html")
        
        @self.app.websocket("/ws/{session_id}")
        async def websocket_endpoint(websocket: WebSocket, session_id: str):
            await self.handle_websocket(websocket, session_id)
        
        @self.app.get("/api/hardware-detection")
        async def detect_hardware():
            return await self.detect_hardware()
        
        @self.app.post("/api/install/{session_id}")
        async def start_installation(session_id: str, config: dict):
            return await self.start_installation(session_id, config)
    
    async def handle_websocket(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_sessions[session_id] = {
            'websocket': websocket,
            'profile': UserProfile(),
            'current_phase': WizardPhase.WELCOME,
            'start_time': datetime.now()
        }
        
        try:
            await self.run_wizard_session(session_id)
        except WebSocketDisconnect:
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
    
    async def run_wizard_session(self, session_id: str):
        session = self.active_sessions[session_id]
        websocket = session['websocket']
        
        # Phase 1: Welcome & Detection
        await self.welcome_phase(session_id)
        
        # Phase 2: Use Case Interview
        await self.use_case_phase(session_id)
        
        # Phase 3: Trade-off Discussion
        await self.trade_offs_phase(session_id)
        
        # Phase 4: Installation
        await self.installation_phase(session_id)
        
        # Phase 5: First Run
        await self.first_run_phase(session_id)
        
        # Phase 6: Continuous Optimization
        await self.optimization_phase(session_id)
    
    async def welcome_phase(self, session_id: str):
        session = self.active_sessions[session_id]
        websocket = session['websocket']
        session['current_phase'] = WizardPhase.WELCOME
        
        await websocket.send_json({
            'phase': 'welcome',
            'message': 'Welcome to ActiveLog! Let me analyze your system...',
            'progress': 5
        })
        
        # Hardware detection
        hardware_info = await self.detect_hardware()
        session['profile'].hardware_profile = hardware_info
        
        # Adaptive interface selection
        interface_config = await self.adaptive_interface.select_optimal_interface(
            hardware_info, 
            user_context={'session_start': True}
        )
        
        await websocket.send_json({
            'phase': 'welcome',
            'message': f'System detected: {hardware_info.get("cpu_model", "Unknown")}',
            'hardware': hardware_info,
            'interface': interface_config,
            'progress': 15
        })
    
    async def use_case_phase(self, session_id: str):
        session = self.active_sessions[session_id]
        websocket = session['websocket']
        session['current_phase'] = WizardPhase.USE_CASE
        
        await websocket.send_json({
            'phase': 'use_case',
            'message': 'Let\'s understand your primary use case',
            'questions': [
                {
                    'id': 'primary_use',
                    'type': 'choice',
                    'question': 'What will you primarily use ActiveLog for?',
                    'options': [
                        {'value': 'gaming', 'label': 'Gaming & Entertainment'},
                        {'value': 'development', 'label': 'Software Development'},
                        {'value': 'business', 'label': 'Business & Productivity'},
                        {'value': 'education', 'label': 'Education & Learning'},
                        {'value': 'creative', 'label': 'Creative Work'},
                        {'value': 'general', 'label': 'General Use'}
                    ]
                },
                {
                    'id': 'technical_level',
                    'type': 'choice',
                    'question': 'How would you describe your technical expertise?',
                    'options': [
                        {'value': 'beginner', 'label': 'Beginner - I prefer simple interfaces'},
                        {'value': 'intermediate', 'label': 'Intermediate - Some technical knowledge'},
                        {'value': 'advanced', 'label': 'Advanced - I want full control'},
                        {'value': 'expert', 'label': 'Expert - Give me everything'}
                    ]
                }
            ],
            'progress': 25
        })
        
        # Wait for user responses
        while True:
            try:
                response = await websocket.receive_json()
                if response['type'] == 'use_case_answers':
                    session['profile'].primary_use_case = response['data']['primary_use']
                    session['profile'].technical_level = response['data']['technical_level']
                    break
            except Exception as e:
                print(f"Error in use case phase: {e}")
                break
    
    async def trade_offs_phase(self, session_id: str):
        session = self.active_sessions[session_id]
        websocket = session['websocket']
        session['current_phase'] = WizardPhase.TRADE_OFFS
        
        profile = session['profile']
        hardware = profile.hardware_profile
        
        # Generate personalized trade-off recommendations
        recommendations = await self.generate_trade_off_recommendations(profile)
        
        await websocket.send_json({
            'phase': 'trade_offs',
            'message': 'Let\'s optimize for your specific needs',
            'recommendations': recommendations,
            'trade_offs': [
                {
                    'category': 'Performance vs Battery',
                    'options': [
                        {'value': 'performance', 'label': 'Maximum Performance', 'impact': 'Higher power usage'},
                        {'value': 'balanced', 'label': 'Balanced', 'impact': 'Moderate power usage'},
                        {'value': 'battery', 'label': 'Battery Saver', 'impact': 'Reduced performance'}
                    ]
                },
                {
                    'category': 'Features vs Simplicity',
                    'options': [
                        {'value': 'full', 'label': 'All Features', 'impact': 'More complex interface'},
                        {'value': 'curated', 'label': 'Curated Selection', 'impact': 'Simplified experience'},
                        {'value': 'minimal', 'label': 'Minimal', 'impact': 'Basic functionality only'}
                    ]
                }
            ],
            'progress': 40
        })
        
        # Wait for preferences
        while True:
            try:
                response = await websocket.receive_json()
                if response['type'] == 'trade_off_answers':
                    session['profile'].preferences.update(response['data'])
                    break
            except Exception as e:
                print(f"Error in trade-offs phase: {e}")
                break
    
    async def installation_phase(self, session_id: str):
        session = self.active_sessions[session_id]
        websocket = session['websocket']
        session['current_phase'] = WizardPhase.INSTALLATION
        
        await websocket.send_json({
            'phase': 'installation',
            'message': 'Installing ActiveLog with your optimized configuration...',
            'progress': 50
        })
        
        # Generate optimized configuration
        config = await self.generate_installation_config(session['profile'])
        
        # Simulate installation steps
        install_steps = [
            {'step': 'Preparing installation', 'progress': 55},
            {'step': 'Installing core components', 'progress': 65},
            {'step': 'Configuring services', 'progress': 75},
            {'step': 'Applying optimizations', 'progress': 85},
            {'step': 'Finalizing setup', 'progress': 95}
        ]
        
        for step in install_steps:
            await websocket.send_json({
                'phase': 'installation',
                'message': step['step'],
                'progress': step['progress']
            })
            await asyncio.sleep(2)  # Simulate work
        
        # Save configuration
        config_path = f"/tmp/activelog_config_{session_id}.json"
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
    
    async def first_run_phase(self, session_id: str):
        session = self.active_sessions[session_id]
        websocket = session['websocket']
        session['current_phase'] = WizardPhase.FIRST_RUN
        
        await websocket.send_json({
            'phase': 'first_run',
            'message': 'ActiveLog is ready! Let\'s take it for a spin...',
            'quick_tour': {
                'features': [
                    'Adaptive interface that learns from your usage',
                    'Predictive optimization for better performance',
                    'Community-shared configurations',
                    'Real-time hardware monitoring'
                ],
                'next_steps': [
                    'Explore the dashboard',
                    'Check community recommendations',
                    'Review performance metrics',
                    'Customize your workspace'
                ]
            },
            'progress': 98
        })
        
        # Start background optimization
        await self.start_background_optimization(session_id)
    
    async def optimization_phase(self, session_id: str):
        session = self.active_sessions[session_id]
        websocket = session['websocket']
        session['current_phase'] = WizardPhase.OPTIMIZATION
        
        await websocket.send_json({
            'phase': 'optimization',
            'message': 'Setting up continuous optimization...',
            'optimization': {
                'learning_enabled': True,
                'auto_updates': True,
                'performance_monitoring': True,
                'community_integration': True
            },
            'completion': {
                'message': 'Welcome to ActiveLog! Your system is fully optimized.',
                'launch_url': 'http://localhost:8080'
            },
            'progress': 100
        })
    
    async def detect_hardware(self) -> Dict[str, Any]:
        try:
            profile = await self.hardware_profiler.create_comprehensive_profile()
            return {
                'cpu_model': profile.get('cpu', {}).get('model', 'Unknown'),
                'cpu_cores': profile.get('cpu', {}).get('cores', 0),
                'memory_gb': profile.get('memory', {}).get('total_gb', 0),
                'storage_type': profile.get('storage', {}).get('primary_type', 'Unknown'),
                'gpu_info': profile.get('gpu', {}),
                'network_speed': profile.get('network', {}).get('speed_mbps', 0),
                'performance_tier': profile.get('tier', 'medium')
            }
        except Exception as e:
            print(f"Hardware detection error: {e}")
            return {'error': str(e), 'fallback': True}
    
    async def generate_trade_off_recommendations(self, profile: UserProfile) -> List[Dict]:
        hardware = profile.hardware_profile
        use_case = profile.primary_use_case
        
        recommendations = []
        
        if hardware.get('performance_tier') == 'high':
            recommendations.append({
                'category': 'Performance',
                'recommendation': 'Enable high-performance mode for maximum responsiveness',
                'impact': 'Higher power usage but optimal experience'
            })
        
        if use_case == 'gaming':
            recommendations.append({
                'category': 'Gaming',
                'recommendation': 'Prioritize GPU optimization and low-latency networking',
                'impact': 'Better gaming performance, moderate battery impact'
            })
        
        return recommendations
    
    async def generate_installation_config(self, profile: UserProfile) -> Dict[str, Any]:
        return {
            'user_profile': asdict(profile),
            'optimization_settings': await self.optimizer.generate_optimized_config(
                profile.hardware_profile,
                profile.primary_use_case,
                profile.preferences
            ),
            'installation_timestamp': datetime.now().isoformat(),
            'wizard_version': '1.0.0'
        }
    
    async def start_background_optimization(self, session_id: str):
        # Start continuous learning and optimization
        pass

if __name__ == "__main__":
    wizard = InstallationWizard()
    
    # Create templates directory if it doesn't exist
    os.makedirs("templates", exist_ok=True)
    
    print("Starting ActiveLog Installation Wizard...")
    print("Visit: http://localhost:3000")
    
    uvicorn.run(
        wizard.app,
        host="0.0.0.0",
        port=3000,
        reload=False
    )