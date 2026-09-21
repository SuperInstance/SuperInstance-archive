#!/usr/bin/env python3
"""
Hatchery Management System
Port: 8441

Advanced aquaculture management with:
- NSRAA/SSRAA compliance
- Employee skill tracking & career paths
- Fish disease detection via AI cameras
- Feed optimization algorithms
- Multi-site coordination
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
import uvicorn
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from core.hatchery_controller import HatcheryController
from core.employee_manager import EmployeeManager
from core.nsraa_compliance import NSRAACompliance
from models.hatchery_types import HatcheryStatus, SiteInfo, AlertLevel
from monitoring.disease_detector import DiseaseDetector
from monitoring.water_quality import WaterQualityMonitor
from optimization.feed_optimizer import FeedOptimizer
from utils.notification_system import NotificationSystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HatcheryManager:
    def __init__(self, port: int = 8441):
        self.port = port
        self.app = FastAPI(title="Hatchery Management System")
        self.active_sites: Dict[str, SiteInfo] = {}
        self.websocket_connections: List[WebSocket] = []
        
        # Core components
        self.controller = HatcheryController()
        self.employee_manager = EmployeeManager()
        self.nsraa_compliance = NSRAACompliance()
        self.disease_detector = DiseaseDetector()
        self.water_monitor = WaterQualityMonitor()
        self.feed_optimizer = FeedOptimizer()
        self.notification_system = NotificationSystem()
        
        self._setup_routes()
        self._setup_middleware()
        
    def _setup_middleware(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self):
        
        @self.app.get("/")
        async def root():
            return {
                "system": "Hatchery Management System",
                "version": "1.0.0",
                "active_sites": len(self.active_sites),
                "compliance_status": await self.nsraa_compliance.get_overall_status(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        @self.app.get("/sites")
        async def get_sites():
            return {
                "sites": list(self.active_sites.values()),
                "total": len(self.active_sites)
            }
        
        @self.app.post("/sites/{site_id}/register")
        async def register_site(site_id: str, site_info: dict):
            site = SiteInfo(
                site_id=site_id,
                name=site_info.get("name", f"Site {site_id}"),
                location=site_info.get("location", "Unknown"),
                capacity=site_info.get("capacity", 10000),
                current_stock=site_info.get("current_stock", 0),
                water_systems=site_info.get("water_systems", []),
                employees=site_info.get("employees", [])
            )
            
            self.active_sites[site_id] = site
            await self.controller.initialize_site(site)
            await self._broadcast_update("site_registered", {"site": site.dict()})
            
            logger.info(f"Registered site {site_id}: {site.name}")
            return {"status": "registered", "site": site.dict()}
        
        @self.app.get("/compliance/nsraa")
        async def get_nsraa_compliance():
            return await self.nsraa_compliance.generate_report()
        
        @self.app.get("/compliance/ssraa")
        async def get_ssraa_compliance():
            return await self.nsraa_compliance.generate_ssraa_report()
        
        @self.app.get("/employees")
        async def get_employees():
            return await self.employee_manager.get_all_employees()
        
        @self.app.post("/employees/{employee_id}/skill-assessment")
        async def assess_employee_skills(employee_id: str, assessment_data: dict):
            result = await self.employee_manager.conduct_skill_assessment(
                employee_id, assessment_data
            )
            return result
        
        @self.app.get("/monitoring/disease-alerts")
        async def get_disease_alerts():
            alerts = []
            for site_id in self.active_sites:
                site_alerts = await self.disease_detector.get_site_alerts(site_id)
                alerts.extend(site_alerts)
            return {"alerts": alerts, "total": len(alerts)}
        
        @self.app.post("/monitoring/camera-feed/{site_id}")
        async def process_camera_feed(site_id: str, image_data: dict):
            if site_id not in self.active_sites:
                raise HTTPException(status_code=404, detail="Site not found")
            
            detection_result = await self.disease_detector.analyze_image(
                site_id, image_data
            )
            
            if detection_result.get("disease_detected"):
                await self._broadcast_alert(
                    AlertLevel.HIGH,
                    f"Disease detected at {self.active_sites[site_id].name}",
                    detection_result
                )
            
            return detection_result
        
        @self.app.get("/optimization/feed-schedule/{site_id}")
        async def get_feed_schedule(site_id: str):
            if site_id not in self.active_sites:
                raise HTTPException(status_code=404, detail="Site not found")
            
            schedule = await self.feed_optimizer.generate_schedule(
                self.active_sites[site_id]
            )
            return schedule
        
        @self.app.post("/optimization/update-feed-data/{site_id}")
        async def update_feed_data(site_id: str, feed_data: dict):
            if site_id not in self.active_sites:
                raise HTTPException(status_code=404, detail="Site not found")
            
            optimization = await self.feed_optimizer.optimize_feeding(
                site_id, feed_data
            )
            return optimization
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.websocket_connections.append(websocket)
            
            try:
                while True:
                    data = await websocket.receive_text()
                    logger.info(f"Received websocket message: {data}")
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
            finally:
                self.websocket_connections.remove(websocket)
        
        @self.app.get("/health")
        async def health_check():
            system_health = {
                "hatchery_controller": await self.controller.get_status(),
                "disease_detector": self.disease_detector.is_healthy(),
                "water_monitor": self.water_monitor.is_operational(),
                "feed_optimizer": self.feed_optimizer.is_active(),
                "nsraa_compliance": await self.nsraa_compliance.get_system_status()
            }
            
            overall_healthy = all(system_health.values())
            
            return {
                "status": "healthy" if overall_healthy else "degraded",
                "components": system_health,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def _broadcast_update(self, event_type: str, data: dict):
        if not self.websocket_connections:
            return
        
        message = {
            "event": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        disconnected = []
        for ws in self.websocket_connections:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send WebSocket message: {e}")
                disconnected.append(ws)
        
        for ws in disconnected:
            self.websocket_connections.remove(ws)
    
    async def _broadcast_alert(self, level: AlertLevel, message: str, data: dict = None):
        alert = {
            "level": level.value,
            "message": message,
            "data": data or {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self._broadcast_update("alert", alert)
        await self.notification_system.send_alert(alert)
    
    async def start_monitoring_loops(self):
        """Start background monitoring tasks"""
        asyncio.create_task(self._water_quality_loop())
        asyncio.create_task(self._disease_monitoring_loop())
        asyncio.create_task(self._compliance_check_loop())
        asyncio.create_task(self._feed_optimization_loop())
        
        logger.info("Started all monitoring loops")
    
    async def _water_quality_loop(self):
        """Monitor water quality across all sites"""
        while True:
            try:
                for site_id, site in self.active_sites.items():
                    readings = await self.water_monitor.get_readings(site_id)
                    
                    if readings.get("alerts"):
                        await self._broadcast_alert(
                            AlertLevel.MEDIUM,
                            f"Water quality alert at {site.name}",
                            readings
                        )
                
                await asyncio.sleep(300)  # 5 minutes
            except Exception as e:
                logger.error(f"Water quality monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _disease_monitoring_loop(self):
        """Continuous disease monitoring"""
        while True:
            try:
                for site_id in self.active_sites:
                    status = await self.disease_detector.check_site_status(site_id)
                    
                    if status.get("risk_level", "low") in ["high", "critical"]:
                        await self._broadcast_alert(
                            AlertLevel.HIGH,
                            f"Disease risk elevated at site {site_id}",
                            status
                        )
                
                await asyncio.sleep(600)  # 10 minutes
            except Exception as e:
                logger.error(f"Disease monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _compliance_check_loop(self):
        """Regular compliance status checks"""
        while True:
            try:
                compliance_status = await self.nsraa_compliance.run_compliance_check()
                
                if compliance_status.get("violations"):
                    await self._broadcast_alert(
                        AlertLevel.HIGH,
                        "Compliance violations detected",
                        compliance_status
                    )
                
                await asyncio.sleep(3600)  # 1 hour
            except Exception as e:
                logger.error(f"Compliance check error: {e}")
                await asyncio.sleep(300)
    
    async def _feed_optimization_loop(self):
        """Optimize feeding schedules"""
        while True:
            try:
                for site_id, site in self.active_sites.items():
                    optimization = await self.feed_optimizer.daily_optimization(site)
                    
                    if optimization.get("cost_savings", 0) > 100:
                        await self._broadcast_update(
                            "feed_optimization",
                            {
                                "site_id": site_id,
                                "savings": optimization["cost_savings"],
                                "recommendations": optimization.get("recommendations", [])
                            }
                        )
                
                await asyncio.sleep(86400)  # 24 hours
            except Exception as e:
                logger.error(f"Feed optimization error: {e}")
                await asyncio.sleep(3600)
    
    def run(self):
        """Start the hatchery management system"""
        logger.info(f"Starting Hatchery Management System on port {self.port}")
        uvicorn.run(
            self.app,
            host="0.0.0.0",
            port=self.port,
            log_level="info"
        )

async def main():
    manager = HatcheryManager()
    
    # Start background monitoring
    await manager.start_monitoring_loops()
    
    # This would typically be called by uvicorn
    # manager.run()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        # Development mode with asyncio
        asyncio.run(main())
    else:
        # Production mode with uvicorn
        HatcheryManager().run()