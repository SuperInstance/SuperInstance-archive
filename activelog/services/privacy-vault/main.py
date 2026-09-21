from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
import uvicorn

from models.privacy_models import *
from core.pii_detection import PIIDetectionEngine
from core.data_residency import DataResidencyManager
from core.consent_management import ConsentManager
from core.right_to_be_forgotten import RightToBeForgottenManager
from core.data_retention import DataRetentionManager
from core.privacy_impact_assessment import PrivacyImpactAssessmentManager
from core.cross_border_transfer import CrossBorderTransferManager
from core.pseudonymization import PseudonymizationManager
from core.audit_trail import PrivacyAuditManager
from core.privacy_analytics import PrivacyPreservingAnalyticsEngine
from core.differential_privacy import DifferentialPrivacyEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="ActiveLog Privacy Vault",
    description="Comprehensive privacy protection and data governance service",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8088"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global privacy managers
pii_detection_engine: PIIDetectionEngine = None
data_residency_manager: DataResidencyManager = None
consent_manager: ConsentManager = None
rtbf_manager: RightToBeForgottenManager = None
retention_manager: DataRetentionManager = None
pia_manager: PrivacyImpactAssessmentManager = None
transfer_manager: CrossBorderTransferManager = None
pseudonymization_manager: PseudonymizationManager = None
audit_manager: PrivacyAuditManager = None
analytics_engine: PrivacyPreservingAnalyticsEngine = None
differential_privacy_engine: DifferentialPrivacyEngine = None

@app.on_event("startup")
async def startup_event():
    """Initialize privacy vault components on startup"""
    global (pii_detection_engine, data_residency_manager, consent_manager, 
            rtbf_manager, retention_manager, pia_manager, transfer_manager,
            pseudonymization_manager, audit_manager, analytics_engine, 
            differential_privacy_engine)
    
    try:
        logger.info("Initializing Privacy Vault services...")
        
        # Initialize core privacy engines
        pii_detection_engine = PIIDetectionEngine()
        data_residency_manager = DataResidencyManager()
        consent_manager = ConsentManager()
        rtbf_manager = RightToBeForgottenManager()
        retention_manager = DataRetentionManager()
        pia_manager = PrivacyImpactAssessmentManager()
        transfer_manager = CrossBorderTransferManager()
        pseudonymization_manager = PseudonymizationManager()
        audit_manager = PrivacyAuditManager()
        analytics_engine = PrivacyPreservingAnalyticsEngine()
        differential_privacy_engine = DifferentialPrivacyEngine()
        
        # Start background privacy monitoring
        asyncio.create_task(privacy_monitoring_loop())
        asyncio.create_task(retention_cleanup_loop())
        asyncio.create_task(consent_expiry_monitoring())
        
        logger.info("Privacy Vault services initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Privacy Vault: {e}")
        raise

async def privacy_monitoring_loop():
    """Background loop for privacy monitoring"""
    while True:
        try:
            # Monitor data residency compliance
            await data_residency_manager.monitor_compliance()
            
            # Check retention policy enforcement
            await retention_manager.enforce_retention_policies()
            
            # Monitor consent validity
            await consent_manager.check_consent_expiry()
            
            # Sleep for 1 hour
            await asyncio.sleep(3600)
            
        except Exception as e:
            logger.error(f"Privacy monitoring error: {e}")
            await asyncio.sleep(300)  # Retry in 5 minutes

async def retention_cleanup_loop():
    """Background loop for retention cleanup"""
    while True:
        try:
            # Run retention cleanup daily
            await retention_manager.cleanup_expired_data()
            await asyncio.sleep(86400)  # 24 hours
            
        except Exception as e:
            logger.error(f"Retention cleanup error: {e}")
            await asyncio.sleep(3600)  # Retry in 1 hour

async def consent_expiry_monitoring():
    """Monitor and handle consent expiry"""
    while True:
        try:
            # Check for expiring consents
            await consent_manager.handle_expiring_consents()
            await asyncio.sleep(3600)  # Check hourly
            
        except Exception as e:
            logger.error(f"Consent monitoring error: {e}")
            await asyncio.sleep(300)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "privacy-vault",
        "version": "1.0.0"
    }

# PII Detection and Masking Endpoints
@app.post("/api/pii/detect", response_model=PIIDetectionResult)
async def detect_pii(request: PIIDetectionRequest):
    """Detect PII in data"""
    try:
        result = await pii_detection_engine.detect_pii(
            data=request.data,
            detection_level=request.detection_level,
            custom_patterns=request.custom_patterns
        )
        
        # Audit the detection request
        await audit_manager.log_privacy_event(
            event_type="pii_detection",
            user_id=request.user_id,
            details={"detection_count": len(result.pii_findings)}
        )
        
        return result
        
    except Exception as e:
        logger.error(f"PII detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/pii/mask", response_model=PIIMaskingResult)
async def mask_pii(request: PIIMaskingRequest):
    """Mask PII in data"""
    try:
        result = await pii_detection_engine.mask_pii(
            data=request.data,
            masking_strategy=request.masking_strategy,
            preserve_format=request.preserve_format,
            custom_masks=request.custom_masks
        )
        
        await audit_manager.log_privacy_event(
            event_type="pii_masking",
            user_id=request.user_id,
            details={"masking_strategy": request.masking_strategy}
        )
        
        return result
        
    except Exception as e:
        logger.error(f"PII masking failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Data Residency Endpoints
@app.post("/api/residency/register")
async def register_data_location(request: DataLocationRequest):
    """Register data location for residency tracking"""
    try:
        result = await data_residency_manager.register_data_location(
            data_id=request.data_id,
            location=request.location,
            data_type=request.data_type,
            jurisdiction=request.jurisdiction,
            storage_requirements=request.storage_requirements
        )
        
        return {"success": True, "location_id": result}
        
    except Exception as e:
        logger.error(f"Data location registration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/residency/compliance/{data_id}")
async def check_residency_compliance(data_id: str):
    """Check data residency compliance"""
    try:
        result = await data_residency_manager.check_compliance(data_id)
        return result
        
    except Exception as e:
        logger.error(f"Residency compliance check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Consent Management Endpoints
@app.post("/api/consent/record", response_model=ConsentRecord)
async def record_consent(request: ConsentRequest):
    """Record user consent"""
    try:
        consent_record = await consent_manager.record_consent(
            user_id=request.user_id,
            purpose=request.purpose,
            data_categories=request.data_categories,
            consent_type=request.consent_type,
            expiry_date=request.expiry_date,
            granular_permissions=request.granular_permissions
        )
        
        return consent_record
        
    except Exception as e:
        logger.error(f"Consent recording failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/consent/{user_id}", response_model=List[ConsentRecord])
async def get_user_consents(user_id: str):
    """Get all consents for a user"""
    try:
        consents = await consent_manager.get_user_consents(user_id)
        return consents
        
    except Exception as e:
        logger.error(f"Consent retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/consent/withdraw")
async def withdraw_consent(request: ConsentWithdrawalRequest):
    """Withdraw user consent"""
    try:
        result = await consent_manager.withdraw_consent(
            user_id=request.user_id,
            consent_id=request.consent_id,
            reason=request.reason
        )
        
        return {"success": result}
        
    except Exception as e:
        logger.error(f"Consent withdrawal failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Right to be Forgotten Endpoints
@app.post("/api/rtbf/request", response_model=RTBFRequest)
async def create_rtbf_request(request: RTBFRequestCreate):
    """Create a right to be forgotten request"""
    try:
        rtbf_request = await rtbf_manager.create_rtbf_request(
            user_id=request.user_id,
            scope=request.scope,
            reason=request.reason,
            urgency=request.urgency,
            specific_data=request.specific_data
        )
        
        return rtbf_request
        
    except Exception as e:
        logger.error(f"RTBF request creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/rtbf/status/{request_id}")
async def get_rtbf_status(request_id: str):
    """Get status of RTBF request"""
    try:
        status = await rtbf_manager.get_request_status(request_id)
        return status
        
    except Exception as e:
        logger.error(f"RTBF status retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rtbf/execute/{request_id}")
async def execute_rtbf_request(request_id: str, background_tasks: BackgroundTasks):
    """Execute RTBF request"""
    try:
        # Execute in background
        background_tasks.add_task(rtbf_manager.execute_rtbf_request, request_id)
        
        return {"success": True, "message": "RTBF execution started"}
        
    except Exception as e:
        logger.error(f"RTBF execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Data Retention Endpoints
@app.post("/api/retention/policy", response_model=RetentionPolicy)
async def create_retention_policy(request: RetentionPolicyRequest):
    """Create data retention policy"""
    try:
        policy = await retention_manager.create_retention_policy(
            name=request.name,
            data_categories=request.data_categories,
            retention_period=request.retention_period,
            legal_basis=request.legal_basis,
            deletion_method=request.deletion_method,
            exceptions=request.exceptions
        )
        
        return policy
        
    except Exception as e:
        logger.error(f"Retention policy creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/retention/policies", response_model=List[RetentionPolicy])
async def list_retention_policies():
    """List all retention policies"""
    try:
        policies = await retention_manager.list_policies()
        return policies
        
    except Exception as e:
        logger.error(f"Retention policies listing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Privacy Impact Assessment Endpoints
@app.post("/api/pia/create", response_model=PrivacyImpactAssessment)
async def create_pia(request: PIARequest):
    """Create Privacy Impact Assessment"""
    try:
        pia = await pia_manager.create_pia(
            project_name=request.project_name,
            description=request.description,
            data_categories=request.data_categories,
            processing_purposes=request.processing_purposes,
            stakeholders=request.stakeholders,
            risk_level=request.risk_level
        )
        
        return pia
        
    except Exception as e:
        logger.error(f"PIA creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/pia/{pia_id}/assess")
async def conduct_pia_assessment(pia_id: str, request: PIAAssessmentRequest):
    """Conduct PIA assessment"""
    try:
        result = await pia_manager.conduct_assessment(
            pia_id=pia_id,
            privacy_risks=request.privacy_risks,
            mitigation_measures=request.mitigation_measures,
            residual_risks=request.residual_risks
        )
        
        return result
        
    except Exception as e:
        logger.error(f"PIA assessment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Cross-Border Transfer Endpoints
@app.post("/api/transfer/register")
async def register_cross_border_transfer(request: CrossBorderTransferRequest):
    """Register cross-border data transfer"""
    try:
        transfer_id = await transfer_manager.register_transfer(
            data_id=request.data_id,
            source_country=request.source_country,
            destination_country=request.destination_country,
            legal_mechanism=request.legal_mechanism,
            safeguards=request.safeguards,
            purpose=request.purpose
        )
        
        return {"success": True, "transfer_id": transfer_id}
        
    except Exception as e:
        logger.error(f"Cross-border transfer registration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/transfer/adequacy/{country}")
async def check_adequacy_decision(country: str):
    """Check adequacy decision for country"""
    try:
        adequacy = await transfer_manager.check_adequacy_decision(country)
        return adequacy
        
    except Exception as e:
        logger.error(f"Adequacy decision check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Pseudonymization Endpoints
@app.post("/api/pseudonymization/pseudonymize", response_model=PseudonymizationResult)
async def pseudonymize_data(request: PseudonymizationRequest):
    """Pseudonymize data"""
    try:
        result = await pseudonymization_manager.pseudonymize(
            data=request.data,
            method=request.method,
            key_id=request.key_id,
            preserve_relationships=request.preserve_relationships
        )
        
        await audit_manager.log_privacy_event(
            event_type="data_pseudonymization",
            user_id=request.user_id,
            details={"method": request.method, "data_size": len(str(request.data))}
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Pseudonymization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/pseudonymization/reverse")
async def reverse_pseudonymization(request: ReversePseudonymizationRequest):
    """Reverse pseudonymization (if authorized)"""
    try:
        result = await pseudonymization_manager.reverse_pseudonymization(
            pseudonymized_data=request.pseudonymized_data,
            key_id=request.key_id,
            authorization_token=request.authorization_token
        )
        
        await audit_manager.log_privacy_event(
            event_type="pseudonymization_reversal",
            user_id=request.user_id,
            details={"authorized": result is not None}
        )
        
        return {"success": result is not None, "data": result}
        
    except Exception as e:
        logger.error(f"Reverse pseudonymization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Privacy Audit Endpoints
@app.get("/api/audit/trail")
async def get_privacy_audit_trail(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    event_type: Optional[str] = None,
    user_id: Optional[str] = None
):
    """Get privacy audit trail"""
    try:
        trail = await audit_manager.get_audit_trail(
            start_date=start_date,
            end_date=end_date,
            event_type=event_type,
            user_id=user_id
        )
        
        return {"audit_events": trail}
        
    except Exception as e:
        logger.error(f"Audit trail retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/audit/data-access/{data_id}")
async def get_data_access_log(data_id: str):
    """Get data access audit log"""
    try:
        access_log = await audit_manager.get_data_access_log(data_id)
        return {"access_log": access_log}
        
    except Exception as e:
        logger.error(f"Data access log retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Privacy-Preserving Analytics Endpoints
@app.post("/api/analytics/query", response_model=AnalyticsResult)
async def execute_privacy_preserving_query(request: AnalyticsQueryRequest):
    """Execute privacy-preserving analytics query"""
    try:
        result = await analytics_engine.execute_query(
            query=request.query,
            dataset_id=request.dataset_id,
            privacy_budget=request.privacy_budget,
            aggregation_level=request.aggregation_level
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Privacy-preserving analytics query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analytics/k-anonymity")
async def apply_k_anonymity(request: KAnonymityRequest):
    """Apply k-anonymity to dataset"""
    try:
        result = await analytics_engine.apply_k_anonymity(
            data=request.data,
            k_value=request.k_value,
            quasi_identifiers=request.quasi_identifiers,
            sensitive_attributes=request.sensitive_attributes
        )
        
        return result
        
    except Exception as e:
        logger.error(f"K-anonymity application failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Differential Privacy Endpoints
@app.post("/api/differential-privacy/query", response_model=DifferentialPrivacyResult)
async def differential_privacy_query(request: DifferentialPrivacyRequest):
    """Execute differential privacy query"""
    try:
        result = await differential_privacy_engine.execute_dp_query(
            query_type=request.query_type,
            data=request.data,
            epsilon=request.epsilon,
            delta=request.delta,
            sensitivity=request.sensitivity
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Differential privacy query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/differential-privacy/budget/{user_id}")
async def get_privacy_budget(user_id: str):
    """Get privacy budget for user"""
    try:
        budget = await differential_privacy_engine.get_privacy_budget(user_id)
        return budget
        
    except Exception as e:
        logger.error(f"Privacy budget retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# System Status and Monitoring
@app.get("/api/status/privacy-compliance")
async def get_privacy_compliance_status():
    """Get overall privacy compliance status"""
    try:
        status = {
            "pii_detection_active": pii_detection_engine is not None,
            "consent_management_active": consent_manager is not None,
            "retention_policies_count": len(await retention_manager.list_policies()) if retention_manager else 0,
            "active_rtbf_requests": len(await rtbf_manager.get_active_requests()) if rtbf_manager else 0,
            "cross_border_transfers_monitored": await transfer_manager.get_transfer_count() if transfer_manager else 0,
            "audit_events_last_24h": await audit_manager.get_event_count(hours=24) if audit_manager else 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return status
        
    except Exception as e:
        logger.error(f"Privacy compliance status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Error handler
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8107)