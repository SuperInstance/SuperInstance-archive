#!/usr/bin/env python3
"""
Dividend Shares System
Port: 8444

Advanced dividend distribution and equity management with:
- Automated dividend calculations
- Share class management
- Investor relations portal
- Tax optimization
- Compliance reporting
- Real-time distribution tracking
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal, ROUND_HALF_UP
import uvicorn
from fastapi import FastAPI, WebSocket, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from ..models.market_types import (
    ShareClass, Shareholder, DividendDistribution, 
    InvestorProfile, ComplianceRecord
)
from ..core.dividend_calculator import DividendCalculator
from ..core.equity_manager import EquityManager
from ..core.tax_optimizer import TaxOptimizer
from ..utils.compliance_tracker import ComplianceTracker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DividendSharesSystem:
    def __init__(self, port: int = 8444):
        self.port = port
        self.app = FastAPI(title="Dividend Shares Management System")
        self.shareholders: Dict[str, Shareholder] = {}
        self.share_classes: Dict[str, ShareClass] = {}
        self.distributions: Dict[str, DividendDistribution] = {}
        self.websocket_connections: List[WebSocket] = []
        
        # Core components
        self.dividend_calculator = DividendCalculator()
        self.equity_manager = EquityManager()
        self.tax_optimizer = TaxOptimizer()
        self.compliance_tracker = ComplianceTracker()
        
        self._setup_routes()
        self._setup_middleware()
        self._initialize_system()
        
    def _setup_middleware(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _initialize_system(self):
        """Initialize default share classes and system settings"""
        # Create default share classes
        common_shares = ShareClass(
            class_id="COMMON_A",
            class_name="Class A Common Stock",
            voting_rights=1.0,
            dividend_preference=1.0,
            liquidation_preference=1.0,
            dividend_rate=None,  # Variable based on performance
            cumulative_dividends=False,
            participating=True,
            conversion_rights=None,
            tag_along_rights=True,
            drag_along_rights=True,
            shares_outstanding=1000000,
            par_value=Decimal("0.01")
        )
        
        preferred_shares = ShareClass(
            class_id="PREFERRED_A",
            class_name="Series A Preferred Stock",
            voting_rights=0.0,
            dividend_preference=2.0,  # 2x preference
            liquidation_preference=1.5,
            dividend_rate=0.08,  # 8% annual dividend
            cumulative_dividends=True,
            participating=False,
            conversion_rights={
                "convertible_to": "COMMON_A",
                "conversion_ratio": 1.0,
                "conversion_price": Decimal("10.00")
            },
            tag_along_rights=True,
            drag_along_rights=False,
            shares_outstanding=500000,
            par_value=Decimal("10.00")
        )
        
        self.share_classes["COMMON_A"] = common_shares
        self.share_classes["PREFERRED_A"] = preferred_shares
        
        logger.info("Initialized dividend shares system with default share classes")
    
    def _setup_routes(self):
        
        @self.app.get("/")
        async def root():
            total_shareholders = len(self.shareholders)
            total_distributions = len(self.distributions)
            total_value_distributed = sum(
                float(dist.total_amount) for dist in self.distributions.values()
                if dist.status == "completed"
            )
            
            return {
                "system": "Dividend Shares Management System",
                "version": "1.0.0",
                "total_shareholders": total_shareholders,
                "total_distributions": total_distributions,
                "total_value_distributed": total_value_distributed,
                "share_classes": len(self.share_classes),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Shareholder Management Routes
        @self.app.get("/shareholders")
        async def get_shareholders():
            shareholders_data = []
            for shareholder_id, shareholder in self.shareholders.items():
                shareholder_summary = await self._get_shareholder_summary(shareholder_id)
                shareholders_data.append(shareholder_summary)
            
            return {"shareholders": shareholders_data, "total": len(shareholders_data)}
        
        @self.app.post("/shareholders")
        async def add_shareholder(shareholder_data: dict):
            shareholder_id = await self._create_shareholder(shareholder_data)
            
            if shareholder_id:
                await self._broadcast_update("shareholder_added", {
                    "shareholder_id": shareholder_id,
                    "name": shareholder_data.get("name")
                })
                return {"shareholder_id": shareholder_id, "status": "created"}
            else:
                raise HTTPException(status_code=400, detail="Failed to create shareholder")
        
        @self.app.get("/shareholders/{shareholder_id}")
        async def get_shareholder_details(shareholder_id: str):
            if shareholder_id not in self.shareholders:
                raise HTTPException(status_code=404, detail="Shareholder not found")
            
            details = await self._get_shareholder_details(shareholder_id)
            return details
        
        @self.app.put("/shareholders/{shareholder_id}/shares")
        async def update_shareholding(shareholder_id: str, share_update: dict):
            if shareholder_id not in self.shareholders:
                raise HTTPException(status_code=404, detail="Shareholder not found")
            
            success = await self.equity_manager.update_shareholding(
                shareholder_id, share_update
            )
            
            if success:
                await self._broadcast_update("shareholding_updated", {
                    "shareholder_id": shareholder_id,
                    "update": share_update
                })
                return {"status": "updated"}
            else:
                raise HTTPException(status_code=400, detail="Failed to update shareholding")
        
        # Share Classes Management
        @self.app.get("/share-classes")
        async def get_share_classes():
            classes_data = []
            for class_id, share_class in self.share_classes.items():
                class_summary = {
                    "class_id": class_id,
                    "class_name": share_class.class_name,
                    "shares_outstanding": share_class.shares_outstanding,
                    "voting_rights": share_class.voting_rights,
                    "dividend_preference": share_class.dividend_preference,
                    "dividend_rate": share_class.dividend_rate,
                    "par_value": float(share_class.par_value)
                }
                classes_data.append(class_summary)
            
            return {"share_classes": classes_data}
        
        @self.app.post("/share-classes")
        async def create_share_class(class_data: dict):
            class_id = await self._create_share_class(class_data)
            
            if class_id:
                return {"class_id": class_id, "status": "created"}
            else:
                raise HTTPException(status_code=400, detail="Failed to create share class")
        
        # Dividend Distribution Routes
        @self.app.post("/distributions/calculate")
        async def calculate_dividend_distribution(distribution_data: dict):
            calculation = await self.dividend_calculator.calculate_distribution(
                distribution_data, self.shareholders, self.share_classes
            )
            
            return {
                "calculation_id": calculation["calculation_id"],
                "total_amount": calculation["total_amount"],
                "distributions_by_shareholder": calculation["distributions"],
                "summary": calculation["summary"]
            }
        
        @self.app.post("/distributions")
        async def create_dividend_distribution(distribution_data: dict):
            distribution_id = await self._create_dividend_distribution(distribution_data)
            
            if distribution_id:
                await self._broadcast_update("distribution_created", {
                    "distribution_id": distribution_id,
                    "amount": distribution_data.get("total_amount")
                })
                return {"distribution_id": distribution_id, "status": "created"}
            else:
                raise HTTPException(status_code=400, detail="Failed to create distribution")
        
        @self.app.get("/distributions")
        async def get_distributions():
            distributions_data = []
            for dist_id, distribution in self.distributions.items():
                dist_summary = {
                    "distribution_id": dist_id,
                    "declaration_date": distribution.declaration_date.isoformat(),
                    "payment_date": distribution.payment_date.isoformat() if distribution.payment_date else None,
                    "total_amount": float(distribution.total_amount),
                    "status": distribution.status,
                    "distribution_type": distribution.distribution_type
                }
                distributions_data.append(dist_summary)
            
            return {"distributions": distributions_data, "total": len(distributions_data)}
        
        @self.app.get("/distributions/{distribution_id}")
        async def get_distribution_details(distribution_id: str):
            if distribution_id not in self.distributions:
                raise HTTPException(status_code=404, detail="Distribution not found")
            
            distribution = self.distributions[distribution_id]
            details = {
                "distribution_id": distribution_id,
                "declaration_date": distribution.declaration_date.isoformat(),
                "ex_dividend_date": distribution.ex_dividend_date.isoformat() if distribution.ex_dividend_date else None,
                "record_date": distribution.record_date.isoformat() if distribution.record_date else None,
                "payment_date": distribution.payment_date.isoformat() if distribution.payment_date else None,
                "total_amount": float(distribution.total_amount),
                "status": distribution.status,
                "distribution_type": distribution.distribution_type,
                "individual_distributions": distribution.individual_distributions,
                "tax_withholdings": distribution.tax_withholdings,
                "compliance_notes": distribution.compliance_notes
            }
            
            return details
        
        @self.app.post("/distributions/{distribution_id}/execute")
        async def execute_distribution(distribution_id: str, background_tasks: BackgroundTasks):
            if distribution_id not in self.distributions:
                raise HTTPException(status_code=404, detail="Distribution not found")
            
            background_tasks.add_task(self._execute_distribution, distribution_id)
            return {"status": "execution_initiated", "distribution_id": distribution_id}
        
        # Tax Optimization Routes
        @self.app.get("/tax-optimization/{shareholder_id}")
        async def get_tax_optimization(shareholder_id: str):
            if shareholder_id not in self.shareholders:
                raise HTTPException(status_code=404, detail="Shareholder not found")
            
            optimization = await self.tax_optimizer.analyze_tax_position(
                shareholder_id, self.shareholders[shareholder_id]
            )
            
            return optimization
        
        @self.app.post("/tax-optimization/withholding-calculation")
        async def calculate_tax_withholding(calculation_data: dict):
            withholding = await self.tax_optimizer.calculate_withholding(
                calculation_data
            )
            
            return withholding
        
        # Compliance and Reporting Routes
        @self.app.get("/compliance/status")
        async def get_compliance_status():
            status = await self.compliance_tracker.get_overall_status(
                self.shareholders, self.distributions
            )
            return status
        
        @self.app.get("/compliance/reporting/{report_type}")
        async def generate_compliance_report(report_type: str):
            if report_type not in ["1099", "annual", "quarterly", "ownership"]:
                raise HTTPException(status_code=400, detail="Invalid report type")
            
            report = await self.compliance_tracker.generate_report(
                report_type, self.shareholders, self.distributions, self.share_classes
            )
            
            return report
        
        # Analytics Routes
        @self.app.get("/analytics/dividend-yield")
        async def get_dividend_yield_analysis():
            analysis = await self._calculate_dividend_yield_metrics()
            return analysis
        
        @self.app.get("/analytics/ownership-structure")
        async def get_ownership_analysis():
            analysis = await self._analyze_ownership_structure()
            return analysis
        
        @self.app.get("/analytics/distribution-trends")
        async def get_distribution_trends():
            trends = await self._analyze_distribution_trends()
            return trends
        
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
                "dividend_calculator": self.dividend_calculator.is_operational(),
                "equity_manager": self.equity_manager.is_healthy(),
                "tax_optimizer": self.tax_optimizer.is_active(),
                "compliance_tracker": await self.compliance_tracker.get_system_health()
            }
            
            overall_healthy = all(component_health.values())
            
            return {
                "status": "healthy" if overall_healthy else "degraded",
                "components": component_health,
                "shareholders": len(self.shareholders),
                "distributions": len(self.distributions),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def _create_shareholder(self, shareholder_data: dict) -> Optional[str]:
        """Create new shareholder"""
        try:
            shareholder_id = shareholder_data.get("shareholder_id") or f"SH_{len(self.shareholders)+1:06d}"
            
            shareholder = Shareholder(
                shareholder_id=shareholder_id,
                name=shareholder_data["name"],
                entity_type=shareholder_data.get("entity_type", "individual"),
                contact_info=shareholder_data.get("contact_info", {}),
                tax_info=shareholder_data.get("tax_info", {}),
                shareholdings=shareholder_data.get("shareholdings", {}),
                dividend_preferences=shareholder_data.get("dividend_preferences", {}),
                registration_date=datetime.now(timezone.utc)
            )
            
            self.shareholders[shareholder_id] = shareholder
            
            # Initialize equity tracking
            await self.equity_manager.initialize_shareholder(shareholder_id, shareholder)
            
            logger.info(f"Created shareholder: {shareholder.name} ({shareholder_id})")
            return shareholder_id
            
        except Exception as e:
            logger.error(f"Failed to create shareholder: {e}")
            return None
    
    async def _create_share_class(self, class_data: dict) -> Optional[str]:
        """Create new share class"""
        try:
            class_id = class_data["class_id"]
            
            share_class = ShareClass(
                class_id=class_id,
                class_name=class_data["class_name"],
                voting_rights=class_data.get("voting_rights", 1.0),
                dividend_preference=class_data.get("dividend_preference", 1.0),
                liquidation_preference=class_data.get("liquidation_preference", 1.0),
                dividend_rate=class_data.get("dividend_rate"),
                cumulative_dividends=class_data.get("cumulative_dividends", False),
                participating=class_data.get("participating", True),
                conversion_rights=class_data.get("conversion_rights"),
                tag_along_rights=class_data.get("tag_along_rights", True),
                drag_along_rights=class_data.get("drag_along_rights", True),
                shares_outstanding=class_data.get("shares_outstanding", 0),
                par_value=Decimal(str(class_data.get("par_value", "0.01")))
            )
            
            self.share_classes[class_id] = share_class
            
            logger.info(f"Created share class: {share_class.class_name} ({class_id})")
            return class_id
            
        except Exception as e:
            logger.error(f"Failed to create share class: {e}")
            return None
    
    async def _create_dividend_distribution(self, distribution_data: dict) -> Optional[str]:
        """Create dividend distribution"""
        try:
            distribution_id = f"DIV_{datetime.now().strftime('%Y%m%d')}_{len(self.distributions)+1:03d}"
            
            # Calculate individual distributions
            calculation = await self.dividend_calculator.calculate_distribution(
                distribution_data, self.shareholders, self.share_classes
            )
            
            distribution = DividendDistribution(
                distribution_id=distribution_id,
                declaration_date=datetime.now(timezone.utc),
                ex_dividend_date=datetime.fromisoformat(distribution_data.get("ex_dividend_date")),
                record_date=datetime.fromisoformat(distribution_data.get("record_date")),
                payment_date=datetime.fromisoformat(distribution_data.get("payment_date")),
                total_amount=Decimal(str(distribution_data["total_amount"])),
                distribution_type=distribution_data.get("distribution_type", "regular"),
                individual_distributions=calculation["distributions"],
                tax_withholdings={},  # Will be calculated during execution
                status="declared"
            )
            
            self.distributions[distribution_id] = distribution
            
            logger.info(f"Created dividend distribution: {distribution_id} for ${distribution.total_amount}")
            return distribution_id
            
        except Exception as e:
            logger.error(f"Failed to create dividend distribution: {e}")
            return None
    
    async def _execute_distribution(self, distribution_id: str):
        """Execute dividend distribution (background task)"""
        try:
            distribution = self.distributions[distribution_id]
            
            logger.info(f"Executing dividend distribution: {distribution_id}")
            
            # Calculate tax withholdings for each shareholder
            for shareholder_id, amount in distribution.individual_distributions.items():
                shareholder = self.shareholders[shareholder_id]
                
                withholding = await self.tax_optimizer.calculate_withholding({
                    "shareholder_id": shareholder_id,
                    "dividend_amount": float(amount),
                    "tax_info": shareholder.tax_info
                })
                
                distribution.tax_withholdings[shareholder_id] = withholding["total_withholding"]
            
            # Update status to processing
            distribution.status = "processing"
            
            # Simulate payment processing
            await asyncio.sleep(2)  # Simulate processing time
            
            # Update status to completed
            distribution.status = "completed"
            distribution.payment_date = datetime.now(timezone.utc)
            
            # Generate compliance records
            await self.compliance_tracker.record_distribution(distribution_id, distribution)
            
            await self._broadcast_update("distribution_executed", {
                "distribution_id": distribution_id,
                "total_amount": float(distribution.total_amount),
                "shareholders_paid": len(distribution.individual_distributions)
            })
            
            logger.info(f"Successfully executed dividend distribution: {distribution_id}")
            
        except Exception as e:
            logger.error(f"Failed to execute distribution {distribution_id}: {e}")
            if distribution_id in self.distributions:
                self.distributions[distribution_id].status = "failed"
    
    async def _get_shareholder_summary(self, shareholder_id: str) -> dict:
        """Get shareholder summary information"""
        shareholder = self.shareholders[shareholder_id]
        
        total_shares = sum(shareholder.shareholdings.values())
        total_dividends_received = sum(
            float(dist.individual_distributions.get(shareholder_id, 0))
            for dist in self.distributions.values()
            if dist.status == "completed"
        )
        
        return {
            "shareholder_id": shareholder_id,
            "name": shareholder.name,
            "entity_type": shareholder.entity_type,
            "total_shares": total_shares,
            "total_dividends_received": total_dividends_received,
            "shareholdings_by_class": shareholder.shareholdings,
            "registration_date": shareholder.registration_date.isoformat()
        }
    
    async def _get_shareholder_details(self, shareholder_id: str) -> dict:
        """Get detailed shareholder information"""
        summary = await self._get_shareholder_summary(shareholder_id)
        shareholder = self.shareholders[shareholder_id]
        
        # Get dividend history
        dividend_history = []
        for dist_id, distribution in self.distributions.items():
            if shareholder_id in distribution.individual_distributions:
                dividend_history.append({
                    "distribution_id": dist_id,
                    "payment_date": distribution.payment_date.isoformat() if distribution.payment_date else None,
                    "amount": float(distribution.individual_distributions[shareholder_id]),
                    "tax_withheld": float(distribution.tax_withholdings.get(shareholder_id, 0)),
                    "status": distribution.status
                })
        
        summary.update({
            "contact_info": shareholder.contact_info,
            "tax_info": shareholder.tax_info,
            "dividend_preferences": shareholder.dividend_preferences,
            "dividend_history": dividend_history,
            "kyc_status": shareholder.kyc_status,
            "accredited_investor": shareholder.accredited_investor
        })
        
        return summary
    
    async def _calculate_dividend_yield_metrics(self) -> dict:
        """Calculate dividend yield analytics"""
        # Simplified calculation for demo
        total_dividends_paid = sum(
            float(dist.total_amount) for dist in self.distributions.values()
            if dist.status == "completed"
        )
        
        # Estimate total equity value (would come from valuation system)
        estimated_equity_value = sum(
            share_class.shares_outstanding * float(share_class.par_value) * 10  # 10x par value estimate
            for share_class in self.share_classes.values()
        )
        
        dividend_yield = (total_dividends_paid / estimated_equity_value) * 100 if estimated_equity_value > 0 else 0
        
        return {
            "total_dividends_paid": total_dividends_paid,
            "estimated_equity_value": estimated_equity_value,
            "dividend_yield_percentage": dividend_yield,
            "distributions_count": len([d for d in self.distributions.values() if d.status == "completed"]),
            "average_distribution_size": total_dividends_paid / max(1, len(self.distributions))
        }
    
    async def _analyze_ownership_structure(self) -> dict:
        """Analyze current ownership structure"""
        ownership_by_class = {}
        ownership_by_shareholder = {}
        
        for class_id, share_class in self.share_classes.items():
            total_shares = share_class.shares_outstanding
            ownership_by_class[class_id] = {
                "class_name": share_class.class_name,
                "total_shares": total_shares,
                "shareholders": []
            }
            
            for shareholder_id, shareholder in self.shareholders.items():
                shares_owned = shareholder.shareholdings.get(class_id, 0)
                if shares_owned > 0:
                    ownership_percentage = (shares_owned / total_shares) * 100 if total_shares > 0 else 0
                    
                    ownership_by_class[class_id]["shareholders"].append({
                        "shareholder_id": shareholder_id,
                        "name": shareholder.name,
                        "shares": shares_owned,
                        "percentage": ownership_percentage
                    })
                    
                    if shareholder_id not in ownership_by_shareholder:
                        ownership_by_shareholder[shareholder_id] = {
                            "name": shareholder.name,
                            "total_ownership": 0,
                            "classes": {}
                        }
                    
                    ownership_by_shareholder[shareholder_id]["classes"][class_id] = {
                        "shares": shares_owned,
                        "percentage": ownership_percentage
                    }
        
        return {
            "ownership_by_class": ownership_by_class,
            "ownership_by_shareholder": ownership_by_shareholder,
            "total_shareholders": len(self.shareholders),
            "total_share_classes": len(self.share_classes)
        }
    
    async def _analyze_distribution_trends(self) -> dict:
        """Analyze dividend distribution trends"""
        completed_distributions = [
            dist for dist in self.distributions.values()
            if dist.status == "completed"
        ]
        
        if not completed_distributions:
            return {"message": "No completed distributions to analyze"}
        
        # Sort by payment date
        completed_distributions.sort(key=lambda x: x.payment_date or datetime.min.replace(tzinfo=timezone.utc))
        
        amounts = [float(dist.total_amount) for dist in completed_distributions]
        dates = [dist.payment_date.isoformat() for dist in completed_distributions]
        
        return {
            "distribution_count": len(completed_distributions),
            "total_distributed": sum(amounts),
            "average_distribution": sum(amounts) / len(amounts),
            "largest_distribution": max(amounts),
            "smallest_distribution": min(amounts),
            "distribution_timeline": [
                {
                    "date": dist.payment_date.isoformat(),
                    "amount": float(dist.total_amount),
                    "type": dist.distribution_type
                }
                for dist in completed_distributions
            ]
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
    
    def run(self):
        """Start the dividend shares system"""
        logger.info(f"Starting Dividend Shares Management System on port {self.port}")
        uvicorn.run(
            self.app,
            host="0.0.0.0",
            port=self.port,
            log_level="info"
        )

if __name__ == "__main__":
    DividendSharesSystem().run()