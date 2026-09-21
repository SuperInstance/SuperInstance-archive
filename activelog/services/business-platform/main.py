#!/usr/bin/env python3
"""
Business Platform System
Port: 8442

Comprehensive business management platform with:
- Multi-business portfolio management
- Financial analytics & reporting
- Market intelligence integration
- Automated decision support
- Cross-platform synchronization
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import uvicorn
from fastapi import FastAPI, WebSocket, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from core.business_controller import BusinessController
from core.portfolio_manager import PortfolioManager
from core.decision_engine import DecisionEngine
from models.business_types import BusinessStatus, BusinessType, PortfolioMetrics
from analytics.financial_analyzer import FinancialAnalyzer
from analytics.market_intelligence import MarketIntelligence
from integrations.external_apis import ExternalAPIManager
from utils.reporting_system import ReportingSystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BusinessPlatform:
    def __init__(self, port: int = 8442):
        self.port = port
        self.app = FastAPI(title="Business Management Platform")
        self.active_businesses: Dict[str, Any] = {}
        self.websocket_connections: List[WebSocket] = []
        
        # Core components
        self.business_controller = BusinessController()
        self.portfolio_manager = PortfolioManager()
        self.decision_engine = DecisionEngine()
        self.financial_analyzer = FinancialAnalyzer()
        self.market_intelligence = MarketIntelligence()
        self.external_apis = ExternalAPIManager()
        self.reporting_system = ReportingSystem()
        
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
            portfolio_metrics = await self.portfolio_manager.get_metrics()
            return {
                "platform": "Business Management System",
                "version": "1.0.0",
                "active_businesses": len(self.active_businesses),
                "portfolio_value": portfolio_metrics.get("total_value", 0),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Business Management Routes
        @self.app.get("/businesses")
        async def get_businesses():
            businesses = []
            for business_id, business in self.active_businesses.items():
                business_summary = await self.business_controller.get_business_summary(business_id)
                businesses.append(business_summary)
            
            return {
                "businesses": businesses,
                "total": len(businesses),
                "portfolio_metrics": await self.portfolio_manager.get_metrics()
            }
        
        @self.app.post("/businesses")
        async def create_business(business_data: dict):
            business_id = await self.business_controller.create_business(business_data)
            
            if business_id:
                business = await self.business_controller.get_business(business_id)
                self.active_businesses[business_id] = business
                
                await self._broadcast_update("business_created", {
                    "business_id": business_id,
                    "business": business
                })
                
                return {"business_id": business_id, "status": "created"}
            else:
                raise HTTPException(status_code=400, detail="Failed to create business")
        
        @self.app.get("/businesses/{business_id}")
        async def get_business(business_id: str):
            if business_id not in self.active_businesses:
                raise HTTPException(status_code=404, detail="Business not found")
            
            business_details = await self.business_controller.get_business_details(business_id)
            return business_details
        
        @self.app.put("/businesses/{business_id}")
        async def update_business(business_id: str, updates: dict):
            if business_id not in self.active_businesses:
                raise HTTPException(status_code=404, detail="Business not found")
            
            success = await self.business_controller.update_business(business_id, updates)
            
            if success:
                await self._broadcast_update("business_updated", {
                    "business_id": business_id,
                    "updates": updates
                })
                return {"status": "updated"}
            else:
                raise HTTPException(status_code=400, detail="Failed to update business")
        
        # Financial Analytics Routes
        @self.app.get("/analytics/financial/{business_id}")
        async def get_financial_analytics(business_id: str):
            if business_id not in self.active_businesses:
                raise HTTPException(status_code=404, detail="Business not found")
            
            analytics = await self.financial_analyzer.generate_report(business_id)
            return analytics
        
        @self.app.get("/analytics/portfolio")
        async def get_portfolio_analytics():
            analytics = await self.financial_analyzer.generate_portfolio_report(
                list(self.active_businesses.keys())
            )
            return analytics
        
        @self.app.get("/analytics/market-intelligence/{business_id}")
        async def get_market_intelligence(business_id: str):
            if business_id not in self.active_businesses:
                raise HTTPException(status_code=404, detail="Business not found")
            
            business = self.active_businesses[business_id]
            market_data = await self.market_intelligence.analyze_market(
                business.get("industry", "general"),
                business.get("location", "global")
            )
            return market_data
        
        # Decision Support Routes
        @self.app.post("/decisions/analyze")
        async def analyze_decision(decision_data: dict):
            analysis = await self.decision_engine.analyze_decision(decision_data)
            return analysis
        
        @self.app.get("/decisions/recommendations/{business_id}")
        async def get_recommendations(business_id: str):
            if business_id not in self.active_businesses:
                raise HTTPException(status_code=404, detail="Business not found")
            
            recommendations = await self.decision_engine.generate_recommendations(business_id)
            return recommendations
        
        # Reporting Routes
        @self.app.get("/reports/business/{business_id}")
        async def generate_business_report(business_id: str, report_type: str = "comprehensive"):
            if business_id not in self.active_businesses:
                raise HTTPException(status_code=404, detail="Business not found")
            
            report = await self.reporting_system.generate_business_report(
                business_id, report_type
            )
            return report
        
        @self.app.get("/reports/portfolio")
        async def generate_portfolio_report(report_type: str = "summary"):
            report = await self.reporting_system.generate_portfolio_report(
                list(self.active_businesses.keys()), report_type
            )
            return report
        
        # Integration Routes
        @self.app.get("/integrations/external-data/{business_id}")
        async def get_external_data(business_id: str, data_type: str):
            if business_id not in self.active_businesses:
                raise HTTPException(status_code=404, detail="Business not found")
            
            external_data = await self.external_apis.fetch_business_data(
                business_id, data_type
            )
            return external_data
        
        @self.app.post("/integrations/sync/{business_id}")
        async def sync_business_data(business_id: str, background_tasks: BackgroundTasks):
            if business_id not in self.active_businesses:
                raise HTTPException(status_code=404, detail="Business not found")
            
            background_tasks.add_task(self._sync_business_data, business_id)
            return {"status": "sync_initiated", "business_id": business_id}
        
        # WebSocket for real-time updates
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
            component_health = {
                "business_controller": await self.business_controller.get_status(),
                "portfolio_manager": self.portfolio_manager.is_healthy(),
                "decision_engine": self.decision_engine.is_operational(),
                "financial_analyzer": self.financial_analyzer.is_active(),
                "market_intelligence": await self.market_intelligence.get_status()
            }
            
            overall_healthy = all(component_health.values())
            
            return {
                "status": "healthy" if overall_healthy else "degraded",
                "components": component_health,
                "active_businesses": len(self.active_businesses),
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
    
    async def _sync_business_data(self, business_id: str):
        """Background task to sync business data with external sources"""
        try:
            logger.info(f"Starting data sync for business {business_id}")
            
            # Fetch latest financial data
            financial_data = await self.external_apis.fetch_financial_data(business_id)
            if financial_data:
                await self.business_controller.update_financial_data(business_id, financial_data)
            
            # Update market intelligence
            market_data = await self.external_apis.fetch_market_data(business_id)
            if market_data:
                await self.market_intelligence.update_market_data(business_id, market_data)
            
            # Refresh analytics
            await self.financial_analyzer.refresh_analytics(business_id)
            
            await self._broadcast_update("data_sync_completed", {
                "business_id": business_id,
                "sync_timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            logger.info(f"Completed data sync for business {business_id}")
            
        except Exception as e:
            logger.error(f"Data sync failed for business {business_id}: {e}")
            await self._broadcast_update("data_sync_failed", {
                "business_id": business_id,
                "error": str(e)
            })
    
    async def start_monitoring_loops(self):
        """Start background monitoring and analysis tasks"""
        asyncio.create_task(self._portfolio_monitoring_loop())
        asyncio.create_task(self._market_analysis_loop())
        asyncio.create_task(self._decision_analysis_loop())
        asyncio.create_task(self._reporting_loop())
        
        logger.info("Started all business platform monitoring loops")
    
    async def _portfolio_monitoring_loop(self):
        """Monitor portfolio performance and generate alerts"""
        while True:
            try:
                portfolio_metrics = await self.portfolio_manager.get_metrics()
                
                # Check for significant changes
                if portfolio_metrics.get("variance_percentage", 0) > 10:
                    await self._broadcast_update("portfolio_alert", {
                        "type": "high_variance",
                        "metrics": portfolio_metrics
                    })
                
                # Update all businesses with latest performance data
                for business_id in self.active_businesses:
                    await self.business_controller.update_performance_metrics(business_id)
                
                await asyncio.sleep(300)  # 5 minutes
                
            except Exception as e:
                logger.error(f"Portfolio monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _market_analysis_loop(self):
        """Continuous market analysis and opportunity detection"""
        while True:
            try:
                for business_id in self.active_businesses:
                    business = self.active_businesses[business_id]
                    
                    # Analyze market conditions
                    market_conditions = await self.market_intelligence.get_market_conditions(
                        business.get("industry", "general")
                    )
                    
                    # Generate market-based recommendations
                    if market_conditions.get("opportunity_score", 0) > 0.7:
                        recommendations = await self.decision_engine.generate_market_recommendations(
                            business_id, market_conditions
                        )
                        
                        await self._broadcast_update("market_opportunity", {
                            "business_id": business_id,
                            "opportunity_score": market_conditions["opportunity_score"],
                            "recommendations": recommendations
                        })
                
                await asyncio.sleep(1800)  # 30 minutes
                
            except Exception as e:
                logger.error(f"Market analysis error: {e}")
                await asyncio.sleep(300)
    
    async def _decision_analysis_loop(self):
        """Analyze pending decisions and provide AI recommendations"""
        while True:
            try:
                for business_id in self.active_businesses:
                    pending_decisions = await self.decision_engine.get_pending_decisions(business_id)
                    
                    for decision in pending_decisions:
                        analysis = await self.decision_engine.analyze_decision(decision)
                        
                        if analysis.get("confidence_score", 0) > 0.8:
                            await self._broadcast_update("decision_recommendation", {
                                "business_id": business_id,
                                "decision_id": decision.get("decision_id"),
                                "recommendation": analysis["recommendation"],
                                "confidence": analysis["confidence_score"]
                            })
                
                await asyncio.sleep(3600)  # 1 hour
                
            except Exception as e:
                logger.error(f"Decision analysis error: {e}")
                await asyncio.sleep(600)
    
    async def _reporting_loop(self):
        """Generate periodic reports and insights"""
        while True:
            try:
                # Generate daily portfolio summary
                daily_summary = await self.reporting_system.generate_daily_summary(
                    list(self.active_businesses.keys())
                )
                
                await self._broadcast_update("daily_summary", daily_summary)
                
                # Weekly comprehensive reports (only on Mondays)
                if datetime.now().weekday() == 0:  # Monday
                    for business_id in self.active_businesses:
                        weekly_report = await self.reporting_system.generate_business_report(
                            business_id, "weekly"
                        )
                        
                        await self._broadcast_update("weekly_report", {
                            "business_id": business_id,
                            "report": weekly_report
                        })
                
                await asyncio.sleep(86400)  # 24 hours
                
            except Exception as e:
                logger.error(f"Reporting loop error: {e}")
                await asyncio.sleep(3600)
    
    def run(self):
        """Start the business platform system"""
        logger.info(f"Starting Business Management Platform on port {self.port}")
        uvicorn.run(
            self.app,
            host="0.0.0.0",
            port=self.port,
            log_level="info"
        )

async def main():
    platform = BusinessPlatform()
    
    # Start background monitoring
    await platform.start_monitoring_loops()
    
    # This would typically be called by uvicorn
    # platform.run()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        # Development mode with asyncio
        asyncio.run(main())
    else:
        # Production mode with uvicorn
        BusinessPlatform().run()