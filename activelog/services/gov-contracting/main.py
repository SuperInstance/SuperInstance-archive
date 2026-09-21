#!/usr/bin/env python3
"""
Government Contracting Tools Platform
Comprehensive federal contracting management system
"""

import os
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Government Contracting Tools Platform",
    description="Comprehensive federal contracting management system",
    version="1.0.0"
)

# Import all modules
from rfp_management import rfp_system
from compliance_tracking import compliance_system
from dcaa_timekeeping import dcaa_system
from cost_proposal import proposal_system
from contract_lifecycle import contract_system
from subcontractor_management import subcontractor_system
from security_clearance import clearance_system
from audit_preparation import audit_system
from performance_reporting import performance_system
from small_business_certs import certification_system

# Pydantic models for requests
class RFPSubmissionRequest(BaseModel):
    rfp_data: Dict[str, Any]
    submission_deadline: str
    requirements: List[Dict[str, Any]]

class ComplianceCheckRequest(BaseModel):
    contract_id: str
    compliance_type: str
    check_date: Optional[str] = None

class TimeEntryRequest(BaseModel):
    employee_id: str
    contract_id: str
    date: str
    hours: float
    task_description: str
    direct_indirect: str = "direct"

class CostProposalRequest(BaseModel):
    contract_opportunity: Dict[str, Any]
    cost_elements: List[Dict[str, Any]]
    pricing_strategy: str

class ContractRequest(BaseModel):
    contract_data: Dict[str, Any]
    award_details: Dict[str, Any]

@app.on_event("startup")
async def startup_event():
    """Initialize all systems on startup"""
    try:
        await rfp_system.initialize()
        await compliance_system.initialize()
        await dcaa_system.initialize()
        await proposal_system.initialize()
        await contract_system.initialize()
        await subcontractor_system.initialize()
        await clearance_system.initialize()
        await audit_system.initialize()
        await performance_system.initialize()
        await certification_system.initialize()
        
        logger.info("Government Contracting Platform started successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Government Contracting Platform: {e}")
        raise

# RFP/RFQ Management Endpoints
@app.post("/api/rfp/submit")
async def submit_rfp_response(request: RFPSubmissionRequest):
    """Submit RFP response"""
    try:
        result = await rfp_system.submit_response(request.rfp_data, request.submission_deadline, request.requirements)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"RFP submission error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/rfp/opportunities")
async def get_rfp_opportunities(agency: Optional[str] = None, naics_code: Optional[str] = None):
    """Get RFP opportunities"""
    result = await rfp_system.get_opportunities(agency, naics_code)
    return JSONResponse(content=result)

@app.get("/api/rfp/{rfp_id}/status")
async def get_rfp_status(rfp_id: str):
    """Get RFP response status"""
    result = await rfp_system.get_response_status(rfp_id)
    return JSONResponse(content=result)

# Compliance Tracking Endpoints
@app.post("/api/compliance/check")
async def run_compliance_check(request: ComplianceCheckRequest):
    """Run compliance check"""
    result = await compliance_system.run_compliance_check(request.contract_id, request.compliance_type, request.check_date)
    return JSONResponse(content=result)

@app.get("/api/compliance/dashboard")
async def get_compliance_dashboard():
    """Get compliance dashboard"""
    result = await compliance_system.get_dashboard()
    return JSONResponse(content=result)

@app.get("/api/compliance/{contract_id}/report")
async def get_compliance_report(contract_id: str):
    """Get compliance report for contract"""
    result = await compliance_system.generate_report(contract_id)
    return JSONResponse(content=result)

# DCAA Timekeeping Endpoints
@app.post("/api/dcaa/time-entry")
async def submit_time_entry(request: TimeEntryRequest):
    """Submit DCAA compliant time entry"""
    result = await dcaa_system.submit_time_entry(request.dict())
    return JSONResponse(content=result)

@app.get("/api/dcaa/timesheet/{employee_id}")
async def get_dcaa_timesheet(employee_id: str, start_date: str, end_date: str):
    """Get DCAA compliant timesheet"""
    result = await dcaa_system.generate_timesheet(employee_id, start_date, end_date)
    return JSONResponse(content=result)

@app.post("/api/dcaa/approve-timesheet")
async def approve_timesheet(employee_id: str, period: str, supervisor_id: str):
    """Approve DCAA timesheet"""
    result = await dcaa_system.approve_timesheet(employee_id, period, supervisor_id)
    return JSONResponse(content=result)

# Cost Proposal Generation Endpoints
@app.post("/api/proposals/generate")
async def generate_cost_proposal(request: CostProposalRequest):
    """Generate cost proposal"""
    result = await proposal_system.generate_proposal(request.dict())
    return JSONResponse(content=result)

@app.get("/api/proposals/{proposal_id}/pricing")
async def get_proposal_pricing(proposal_id: str):
    """Get proposal pricing breakdown"""
    result = await proposal_system.get_pricing_breakdown(proposal_id)
    return JSONResponse(content=result)

@app.post("/api/proposals/{proposal_id}/update-pricing")
async def update_proposal_pricing(proposal_id: str, pricing_updates: Dict[str, Any]):
    """Update proposal pricing"""
    result = await proposal_system.update_pricing(proposal_id, pricing_updates)
    return JSONResponse(content=result)

# Contract Lifecycle Management Endpoints
@app.post("/api/contracts/create")
async def create_contract(request: ContractRequest):
    """Create new contract"""
    result = await contract_system.create_contract(request.contract_data, request.award_details)
    return JSONResponse(content=result)

@app.get("/api/contracts/{contract_id}/status")
async def get_contract_status(contract_id: str):
    """Get contract status"""
    result = await contract_system.get_status(contract_id)
    return JSONResponse(content=result)

@app.post("/api/contracts/{contract_id}/modify")
async def modify_contract(contract_id: str, modification_data: Dict[str, Any]):
    """Submit contract modification"""
    result = await contract_system.submit_modification(contract_id, modification_data)
    return JSONResponse(content=result)

# Subcontractor Management Endpoints
@app.post("/api/subcontractors/register")
async def register_subcontractor(subcontractor_data: Dict[str, Any]):
    """Register subcontractor"""
    result = await subcontractor_system.register_subcontractor(subcontractor_data)
    return JSONResponse(content=result)

@app.get("/api/subcontractors/{subcontractor_id}/performance")
async def get_subcontractor_performance(subcontractor_id: str):
    """Get subcontractor performance metrics"""
    result = await subcontractor_system.get_performance_metrics(subcontractor_id)
    return JSONResponse(content=result)

@app.post("/api/subcontractors/{subcontractor_id}/evaluate")
async def evaluate_subcontractor(subcontractor_id: str, evaluation_data: Dict[str, Any]):
    """Evaluate subcontractor performance"""
    result = await subcontractor_system.evaluate_performance(subcontractor_id, evaluation_data)
    return JSONResponse(content=result)

# Security Clearance Tracking Endpoints
@app.post("/api/clearances/track")
async def track_clearance(employee_id: str, clearance_data: Dict[str, Any]):
    """Track security clearance"""
    result = await clearance_system.track_clearance(employee_id, clearance_data)
    return JSONResponse(content=result)

@app.get("/api/clearances/expiring")
async def get_expiring_clearances(days_ahead: int = 90):
    """Get expiring clearances"""
    result = await clearance_system.get_expiring_clearances(days_ahead)
    return JSONResponse(content=result)

@app.post("/api/clearances/{clearance_id}/renew")
async def renew_clearance(clearance_id: str, renewal_data: Dict[str, Any]):
    """Initiate clearance renewal"""
    result = await clearance_system.initiate_renewal(clearance_id, renewal_data)
    return JSONResponse(content=result)

# Audit Preparation Endpoints
@app.post("/api/audit/prepare")
async def prepare_audit(contract_id: str, audit_type: str):
    """Prepare for audit"""
    result = await audit_system.prepare_audit(contract_id, audit_type)
    return JSONResponse(content=result)

@app.get("/api/audit/{audit_id}/checklist")
async def get_audit_checklist(audit_id: str):
    """Get audit preparation checklist"""
    result = await audit_system.get_checklist(audit_id)
    return JSONResponse(content=result)

@app.post("/api/audit/{audit_id}/submit-evidence")
async def submit_audit_evidence(audit_id: str, evidence_data: Dict[str, Any]):
    """Submit audit evidence"""
    result = await audit_system.submit_evidence(audit_id, evidence_data)
    return JSONResponse(content=result)

# Performance Reporting Endpoints
@app.post("/api/performance/report")
async def generate_performance_report(contract_id: str, reporting_period: str):
    """Generate performance report"""
    result = await performance_system.generate_report(contract_id, reporting_period)
    return JSONResponse(content=result)

@app.get("/api/performance/{contract_id}/metrics")
async def get_performance_metrics(contract_id: str):
    """Get contract performance metrics"""
    result = await performance_system.get_metrics(contract_id)
    return JSONResponse(content=result)

@app.post("/api/performance/{contract_id}/update-milestones")
async def update_milestones(contract_id: str, milestone_updates: List[Dict[str, Any]]):
    """Update contract milestones"""
    result = await performance_system.update_milestones(contract_id, milestone_updates)
    return JSONResponse(content=result)

# Small Business Certifications Endpoints
@app.post("/api/certifications/apply")
async def apply_certification(certification_type: str, application_data: Dict[str, Any]):
    """Apply for small business certification"""
    result = await certification_system.apply_certification(certification_type, application_data)
    return JSONResponse(content=result)

@app.get("/api/certifications/status")
async def get_certification_status():
    """Get certification status"""
    result = await certification_system.get_status()
    return JSONResponse(content=result)

@app.post("/api/certifications/{cert_id}/renew")
async def renew_certification(cert_id: str, renewal_data: Dict[str, Any]):
    """Renew certification"""
    result = await certification_system.renew_certification(cert_id, renewal_data)
    return JSONResponse(content=result)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Main execution
if __name__ == "__main__":
    port = int(os.getenv('PORT', 8363))
    logger.info(f"Starting Government Contracting Platform on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)