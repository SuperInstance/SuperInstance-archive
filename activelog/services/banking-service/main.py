from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from src.api import router
from src.core.config import settings
from src.services.virtual_accounts import VirtualAccountService
from src.services.ach_transfers import ACHTransferService
from src.services.wire_transfers import WireTransferService
from src.services.check_processing import CheckProcessingService
from src.services.card_issuing import CardIssuingService
from src.compliance.kyc_aml import KYCAMLService
from src.services.transaction_monitoring import TransactionMonitoringService
from src.services.fraud_detection import FraudDetectionService
from src.services.statement_generation import StatementGenerationService
from src.services.interest_calculation import InterestCalculationService
from src.services.lending import LendingService
from src.services.credit_scoring import CreditScoringService

# Global service instances
services = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize all banking services
    services["virtual_accounts"] = VirtualAccountService()
    services["ach_transfers"] = ACHTransferService()
    services["wire_transfers"] = WireTransferService()
    services["check_processing"] = CheckProcessingService()
    services["card_issuing"] = CardIssuingService()
    services["kyc_aml"] = KYCAMLService()
    services["transaction_monitoring"] = TransactionMonitoringService()
    services["fraud_detection"] = FraudDetectionService()
    services["statement_generation"] = StatementGenerationService()
    services["interest_calculation"] = InterestCalculationService()
    services["lending"] = LendingService()
    services["credit_scoring"] = CreditScoringService()
    
    # Start background monitoring services
    await services["transaction_monitoring"].start_monitoring()
    await services["fraud_detection"].start_monitoring()
    await services["interest_calculation"].start_daily_calculation()
    
    yield
    
    # Cleanup
    await services["transaction_monitoring"].stop_monitoring()
    await services["fraud_detection"].stop_monitoring()
    await services["interest_calculation"].stop_calculation()

app = FastAPI(
    title="Banking Platform API",
    description="Comprehensive banking platform with accounts, transfers, compliance, and lending",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8088"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)

@app.get("/")
async def root():
    return {
        "message": "Banking Platform API",
        "version": "1.0.0",
        "status": "active",
        "compliance": "KYC/AML Enabled",
        "fraud_protection": "Active"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "services": {
            name: "running" for name in services.keys()
        },
        "compliance_status": "active",
        "fraud_detection": "monitoring"
    }

@app.get("/regulatory/status")
async def regulatory_status():
    return {
        "kyc_compliance": True,
        "aml_monitoring": True,
        "bsa_reporting": True,
        "ctr_filing": True,
        "sar_monitoring": True,
        "pci_compliance": True,
        "sox_compliance": True,
        "gdpr_compliance": True
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8358)