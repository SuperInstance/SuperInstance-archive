#!/usr/bin/env python3
"""
Invoice Engine Platform
Professional invoicing system with templates, automation, and payment tracking
"""

import asyncio
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import all modules
from invoice_templates import template_system
from recurring_invoices import recurring_system
from quote_conversion import quote_system
from payment_reminders import reminder_system
from late_fee_automation import late_fee_system
from partial_payments import payment_tracking_system
from credit_notes import credit_system
from multilang_invoices import multilang_system
from approval_workflows import approval_system
from bulk_invoicing import bulk_system
from payment_plans import payment_plan_system
from collections_automation import collections_system

# FastAPI app
app = FastAPI(
    title="Invoice Engine Platform",
    description="Professional invoicing system with templates, automation, and payment tracking",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8088"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class InvoiceRequest(BaseModel):
    customer_id: str
    items: List[Dict[str, Any]]
    template_id: Optional[str] = None
    language: Optional[str] = 'en'
    due_date: Optional[str] = None

class RecurringInvoiceRequest(BaseModel):
    customer_id: str
    items: List[Dict[str, Any]]
    frequency: str  # daily, weekly, monthly, quarterly, yearly
    start_date: str
    end_date: Optional[str] = None

class QuoteRequest(BaseModel):
    customer_id: str
    items: List[Dict[str, Any]]
    valid_until: str
    template_id: Optional[str] = None

class PaymentRequest(BaseModel):
    invoice_id: str
    amount: float
    payment_method: str
    payment_date: Optional[str] = None

# Invoice Template endpoints
@app.post("/api/v1/templates")
async def create_template(template_data: Dict[str, Any]):
    """Create professional invoice template"""
    result = await template_system.create_template(template_data)
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error'))
    return result

@app.get("/api/v1/templates")
async def list_templates():
    """List all invoice templates"""
    return await template_system.list_templates()

@app.get("/api/v1/templates/{template_id}")
async def get_template(template_id: str):
    """Get specific template"""
    result = await template_system.get_template(template_id)
    if not result.get('success'):
        raise HTTPException(status_code=404, detail="Template not found")
    return result

# Invoice Management endpoints
@app.post("/api/v1/invoices")
async def create_invoice(request: InvoiceRequest):
    """Create professional invoice"""
    result = await template_system.generate_invoice({
        'customer_id': request.customer_id,
        'items': request.items,
        'template_id': request.template_id,
        'language': request.language,
        'due_date': request.due_date
    })
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error'))
    return result

@app.get("/api/v1/invoices")
async def list_invoices(status: Optional[str] = None, customer_id: Optional[str] = None):
    """List invoices with filtering"""
    return await template_system.list_invoices({'status': status, 'customer_id': customer_id})

@app.get("/api/v1/invoices/{invoice_id}")
async def get_invoice(invoice_id: str):
    """Get specific invoice"""
    result = await template_system.get_invoice(invoice_id)
    if not result.get('success'):
        raise HTTPException(status_code=404, detail="Invoice not found")
    return result

# Recurring Invoice endpoints
@app.post("/api/v1/recurring-invoices")
async def create_recurring_invoice(request: RecurringInvoiceRequest):
    """Set up recurring invoice"""
    result = await recurring_system.create_recurring_invoice({
        'customer_id': request.customer_id,
        'items': request.items,
        'frequency': request.frequency,
        'start_date': request.start_date,
        'end_date': request.end_date
    })
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error'))
    return result

@app.get("/api/v1/recurring-invoices")
async def list_recurring_invoices():
    """List all recurring invoice schedules"""
    return await recurring_system.list_recurring_invoices()

@app.post("/api/v1/recurring-invoices/process")
async def process_recurring_invoices(background_tasks: BackgroundTasks):
    """Process due recurring invoices"""
    background_tasks.add_task(recurring_system.process_recurring_invoices)
    return {"success": True, "message": "Processing recurring invoices in background"}

# Quote Management endpoints
@app.post("/api/v1/quotes")
async def create_quote(request: QuoteRequest):
    """Create quote"""
    result = await quote_system.create_quote({
        'customer_id': request.customer_id,
        'items': request.items,
        'valid_until': request.valid_until,
        'template_id': request.template_id
    })
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error'))
    return result

@app.post("/api/v1/quotes/{quote_id}/convert")
async def convert_quote_to_invoice(quote_id: str):
    """Convert quote to invoice"""
    result = await quote_system.convert_to_invoice(quote_id)
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error'))
    return result

@app.get("/api/v1/quotes")
async def list_quotes():
    """List all quotes"""
    return await quote_system.list_quotes()

# Payment Management endpoints
@app.post("/api/v1/payments")
async def record_payment(request: PaymentRequest):
    """Record payment against invoice"""
    result = await payment_tracking_system.record_payment({
        'invoice_id': request.invoice_id,
        'amount': request.amount,
        'payment_method': request.payment_method,
        'payment_date': request.payment_date
    })
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error'))
    return result

@app.get("/api/v1/invoices/{invoice_id}/payments")
async def get_invoice_payments(invoice_id: str):
    """Get all payments for an invoice"""
    return await payment_tracking_system.get_invoice_payments(invoice_id)

# Payment Reminders endpoints
@app.post("/api/v1/reminders/send")
async def send_payment_reminders(background_tasks: BackgroundTasks):
    """Send payment reminders for overdue invoices"""
    background_tasks.add_task(reminder_system.send_overdue_reminders)
    return {"success": True, "message": "Sending payment reminders in background"}

@app.get("/api/v1/reminders")
async def list_reminders():
    """List payment reminder history"""
    return await reminder_system.list_reminders()

# Late Fee Management endpoints
@app.post("/api/v1/late-fees/apply")
async def apply_late_fees(background_tasks: BackgroundTasks):
    """Apply late fees to overdue invoices"""
    background_tasks.add_task(late_fee_system.apply_late_fees)
    return {"success": True, "message": "Applying late fees in background"}

@app.get("/api/v1/late-fees")
async def list_late_fees():
    """List applied late fees"""
    return await late_fee_system.list_late_fees()

# Credit Notes endpoints
@app.post("/api/v1/credit-notes")
async def create_credit_note(credit_data: Dict[str, Any]):
    """Create credit note"""
    result = await credit_system.create_credit_note(credit_data)
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error'))
    return result

@app.post("/api/v1/credit-notes/{credit_id}/apply")
async def apply_credit_note(credit_id: str, application_data: Dict[str, Any]):
    """Apply credit note to invoice"""
    result = await credit_system.apply_credit_note(credit_id, application_data)
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error'))
    return result

@app.get("/api/v1/credit-notes")
async def list_credit_notes():
    """List all credit notes"""
    return await credit_system.list_credit_notes()

# Multi-language endpoints
@app.post("/api/v1/languages")
async def add_language_template(language_data: Dict[str, Any]):
    """Add language template"""
    result = await multilang_system.add_language_template(language_data)
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error'))
    return result

@app.get("/api/v1/languages")
async def list_languages():
    """List supported languages"""
    return await multilang_system.list_languages()

# Approval Workflow endpoints
@app.post("/api/v1/approval-workflows")
async def create_workflow(workflow_data: Dict[str, Any]):
    """Create approval workflow"""
    result = await approval_system.create_workflow(workflow_data)
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error'))
    return result

@app.post("/api/v1/invoices/{invoice_id}/submit-approval")
async def submit_for_approval(invoice_id: str):
    """Submit invoice for approval"""
    result = await approval_system.submit_for_approval(invoice_id)
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error'))
    return result

@app.post("/api/v1/approvals/{approval_id}/approve")
async def approve_invoice(approval_id: str, approval_data: Dict[str, Any]):
    """Approve invoice"""
    result = await approval_system.approve_invoice(approval_id, approval_data)
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error'))
    return result

# Bulk Invoicing endpoints
@app.post("/api/v1/bulk-invoices")
async def create_bulk_invoices(bulk_data: Dict[str, Any], background_tasks: BackgroundTasks):
    """Create invoices in bulk"""
    background_tasks.add_task(bulk_system.process_bulk_invoices, bulk_data)
    return {"success": True, "message": "Processing bulk invoices in background"}

@app.get("/api/v1/bulk-invoices/{batch_id}")
async def get_bulk_status(batch_id: str):
    """Get bulk processing status"""
    return await bulk_system.get_batch_status(batch_id)

# Payment Plans endpoints
@app.post("/api/v1/payment-plans")
async def create_payment_plan(plan_data: Dict[str, Any]):
    """Create payment plan"""
    result = await payment_plan_system.create_payment_plan(plan_data)
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error'))
    return result

@app.get("/api/v1/payment-plans")
async def list_payment_plans():
    """List payment plans"""
    return await payment_plan_system.list_payment_plans()

@app.post("/api/v1/payment-plans/process")
async def process_payment_plans(background_tasks: BackgroundTasks):
    """Process due payment plan installments"""
    background_tasks.add_task(payment_plan_system.process_installments)
    return {"success": True, "message": "Processing payment plans in background"}

# Collections Automation endpoints
@app.post("/api/v1/collections/process")
async def process_collections(background_tasks: BackgroundTasks):
    """Process collections automation"""
    background_tasks.add_task(collections_system.process_collections)
    return {"success": True, "message": "Processing collections in background"}

@app.get("/api/v1/collections")
async def list_collections():
    """List collections activities"""
    return await collections_system.list_collections()

# Reports endpoints
@app.get("/api/v1/reports/dashboard")
async def get_dashboard():
    """Get invoice dashboard data"""
    return await template_system.get_dashboard_stats()

@app.get("/api/v1/reports/aging")
async def get_aging_report():
    """Get accounts receivable aging report"""
    return await payment_tracking_system.get_aging_report()

# Health check
@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Invoice Engine Platform",
        "timestamp": datetime.now().isoformat()
    }

@app.on_event("startup")
async def startup_event():
    """Initialize all systems on startup"""
    try:
        # Initialize all modules
        await template_system.initialize()
        await recurring_system.initialize()
        await quote_system.initialize()
        await reminder_system.initialize()
        await late_fee_system.initialize()
        await payment_tracking_system.initialize()
        await credit_system.initialize()
        await multilang_system.initialize()
        await approval_system.initialize()
        await bulk_system.initialize()
        await payment_plan_system.initialize()
        await collections_system.initialize()
        
        logger.info("Invoice Engine Platform started on port 8350")
        
    except Exception as e:
        logger.error(f"Failed to start Invoice Engine Platform: {e}")
        raise

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8350)