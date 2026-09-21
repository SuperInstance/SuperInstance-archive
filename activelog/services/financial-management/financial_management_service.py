#!/usr/bin/env python3
"""
Comprehensive Financial Management Service for ActiveLog
Orchestrates QuickBooks integration, invoice generation, payroll automation, and tax filing
"""

import asyncio
import json
import logging
import os
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from aiohttp import web, ClientSession
import aiohttp_cors
import asyncpg
import yaml

# Import our financial management modules
from quickbooks.quickbooks_service import QuickBooksIntegrationService
from invoicing.invoice_generator import InvoiceGenerator
from invoicing.invoice_automation import InvoiceAutomationService
from payroll.payroll_engine import PayrollEngine
from tax_filing.tax_preparation_service import TaxPreparationService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FinancialManagementService:
    """Main financial management service orchestrator"""
    
    def __init__(self, config_path: str):
        self.config = self.load_config(config_path)
        self.db_pool = None
        
        # Initialize service components
        self.quickbooks_service = QuickBooksIntegrationService(
            self.config['quickbooks']['config_path']
        )
        
        self.invoice_generator = InvoiceGenerator(
            self.config['invoicing']['config_path']
        )
        
        self.invoice_automation = InvoiceAutomationService(
            self.config['invoicing']['automation_config_path'],
            self.invoice_generator
        )
        
        self.payroll_engine = PayrollEngine(
            self.config['payroll']['config_path']
        )
        
        self.tax_service = TaxPreparationService(
            self.config['tax_filing']['config_path']
        )
        
        # Web application
        self.app = None
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    async def initialize(self):
        """Initialize the financial management service"""
        # Connect to database
        await self.connect_database()
        
        # Initialize all service components
        await self.quickbooks_service.initialize()
        await self.invoice_generator.initialize()
        await self.invoice_automation.initialize()
        await self.payroll_engine.initialize()
        await self.tax_service.initialize()
        
        # Create web application
        await self.create_web_app()
        
        logger.info("Financial Management Service initialized")
    
    async def shutdown(self):
        """Shutdown the service"""
        # Shutdown all components
        await self.quickbooks_service.shutdown()
        await self.invoice_automation.shutdown()
        await self.payroll_engine.shutdown()
        await self.tax_service.shutdown()
        
        if self.db_pool:
            await self.db_pool.close()
        
        logger.info("Financial Management Service shutdown")
    
    async def connect_database(self):
        """Connect to PostgreSQL database"""
        db_config = self.config['database']
        self.db_pool = await asyncpg.create_pool(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database'],
            min_size=2,
            max_size=10
        )
    
    async def create_web_app(self):
        """Create web application with API endpoints"""
        self.app = web.Application()
        
        # Configure CORS
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # API Routes
        
        # Dashboard and overview
        self.app.router.add_get('/', self.dashboard_handler)
        self.app.router.add_get('/api/financial-overview', self.financial_overview_handler)
        
        # QuickBooks Integration
        self.app.router.add_post('/api/quickbooks/sync/customers', self.sync_customers_handler)
        self.app.router.add_post('/api/quickbooks/sync/invoices', self.sync_invoices_handler)
        self.app.router.add_post('/api/quickbooks/sync/employees', self.sync_employees_handler)
        self.app.router.add_get('/api/quickbooks/sync/status', self.qb_sync_status_handler)
        self.app.router.add_post('/api/quickbooks/webhook', self.qb_webhook_handler)
        
        # Invoice Management
        self.app.router.add_post('/api/invoices/generate', self.generate_invoice_handler)
        self.app.router.add_post('/api/invoices/send', self.send_invoice_handler)
        self.app.router.add_get('/api/invoices/{invoice_id}', self.get_invoice_handler)
        self.app.router.add_get('/api/invoices', self.list_invoices_handler)
        
        # Invoice Automation
        self.app.router.add_post('/api/invoice-automation/rules', self.create_invoice_rule_handler)
        self.app.router.add_get('/api/invoice-automation/rules', self.list_invoice_rules_handler)
        self.app.router.add_put('/api/invoice-automation/rules/{rule_id}', self.update_invoice_rule_handler)
        self.app.router.add_delete('/api/invoice-automation/rules/{rule_id}', self.delete_invoice_rule_handler)
        self.app.router.add_get('/api/invoice-automation/statistics', self.invoice_automation_stats_handler)
        
        # Payroll Management
        self.app.router.add_post('/api/payroll/employees', self.create_payroll_employee_handler)
        self.app.router.add_post('/api/payroll/timesheets', self.submit_timesheet_handler)
        self.app.router.add_post('/api/payroll/timesheets/{timesheet_id}/approve', self.approve_timesheet_handler)
        self.app.router.add_post('/api/payroll/runs', self.create_payroll_run_handler)
        self.app.router.add_post('/api/payroll/runs/{run_id}/calculate', self.calculate_payroll_handler)
        self.app.router.add_post('/api/payroll/runs/{run_id}/pay', self.process_payroll_handler)
        self.app.router.add_get('/api/payroll/runs/{run_id}/report', self.payroll_report_handler)
        
        # Tax Filing
        self.app.router.add_post('/api/tax/form-941', self.prepare_form_941_handler)
        self.app.router.add_post('/api/tax/w2-forms', self.prepare_w2_forms_handler)
        self.app.router.add_post('/api/tax/file/{form_id}', self.file_tax_form_handler)
        self.app.router.add_get('/api/tax/status/{form_id}', self.tax_filing_status_handler)
        self.app.router.add_get('/api/tax/compliance', self.tax_compliance_handler)
        self.app.router.add_get('/api/tax/calendar/{year}', self.tax_calendar_handler)
        
        # Reports
        self.app.router.add_get('/api/reports/financial-summary', self.financial_summary_handler)
        self.app.router.add_get('/api/reports/payroll-summary', self.payroll_summary_handler)
        self.app.router.add_get('/api/reports/tax-summary/{year}', self.tax_summary_handler)
        
        # Add CORS to all routes
        for route in list(self.app.router.routes()):
            cors.add(route)
        
        # Static files
        self.app.router.add_static('/static/', path='static', name='static')
    
    # Web Handlers
    
    async def dashboard_handler(self, request):
        """Main dashboard page"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>ActiveLog Financial Management</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        </head>
        <body>
            <div class="container-fluid">
                <div class="row">
                    <div class="col-12">
                        <h1 class="mt-4">ActiveLog Financial Management Dashboard</h1>
                    </div>
                </div>
                
                <div class="row mt-4">
                    <div class="col-md-3">
                        <div class="card">
                            <div class="card-header">QuickBooks Integration</div>
                            <div class="card-body">
                                <button class="btn btn-primary" onclick="syncCustomers()">Sync Customers</button>
                                <button class="btn btn-primary" onclick="syncInvoices()">Sync Invoices</button>
                                <button class="btn btn-primary" onclick="syncEmployees()">Sync Employees</button>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-3">
                        <div class="card">
                            <div class="card-header">Invoice Management</div>
                            <div class="card-body">
                                <button class="btn btn-success" onclick="generateInvoice()">Generate Invoice</button>
                                <button class="btn btn-info" onclick="viewInvoices()">View Invoices</button>
                                <button class="btn btn-warning" onclick="automationRules()">Automation Rules</button>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-3">
                        <div class="card">
                            <div class="card-header">Payroll Processing</div>
                            <div class="card-body">
                                <button class="btn btn-primary" onclick="createPayrollRun()">Create Payroll Run</button>
                                <button class="btn btn-success" onclick="processPayroll()">Process Payroll</button>
                                <button class="btn btn-info" onclick="payrollReports()">Payroll Reports</button>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-3">
                        <div class="card">
                            <div class="card-header">Tax Filing</div>
                            <div class="card-body">
                                <button class="btn btn-danger" onclick="prepareForm941()">Form 941</button>
                                <button class="btn btn-danger" onclick="prepareW2Forms()">W-2 Forms</button>
                                <button class="btn btn-warning" onclick="taxCompliance()">Compliance</button>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="row mt-4">
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header">Financial Overview</div>
                            <div class="card-body">
                                <canvas id="financialChart"></canvas>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header">Recent Activity</div>
                            <div class="card-body">
                                <div id="recentActivity">Loading...</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <script>
                // Dashboard JavaScript functions
                function syncCustomers() {
                    fetch('/api/quickbooks/sync/customers', {method: 'POST'})
                        .then(response => response.json())
                        .then(data => alert('Customers synced: ' + JSON.stringify(data)));
                }
                
                function syncInvoices() {
                    fetch('/api/quickbooks/sync/invoices', {method: 'POST'})
                        .then(response => response.json())
                        .then(data => alert('Invoices synced: ' + JSON.stringify(data)));
                }
                
                function syncEmployees() {
                    fetch('/api/quickbooks/sync/employees', {method: 'POST'})
                        .then(response => response.json())
                        .then(data => alert('Employees synced: ' + JSON.stringify(data)));
                }
                
                function generateInvoice() {
                    alert('Invoice generation functionality - integrate with form modal');
                }
                
                function viewInvoices() {
                    window.open('/api/invoices', '_blank');
                }
                
                function automationRules() {
                    window.open('/api/invoice-automation/rules', '_blank');
                }
                
                function createPayrollRun() {
                    alert('Payroll run creation - integrate with form modal');
                }
                
                function processPayroll() {
                    alert('Payroll processing - integrate with wizard');
                }
                
                function payrollReports() {
                    window.open('/api/reports/payroll-summary', '_blank');
                }
                
                function prepareForm941() {
                    alert('Form 941 preparation - integrate with form');
                }
                
                function prepareW2Forms() {
                    alert('W-2 forms preparation - integrate with year selection');
                }
                
                function taxCompliance() {
                    window.open('/api/tax/compliance', '_blank');
                }
                
                // Load financial overview chart
                fetch('/api/financial-overview')
                    .then(response => response.json())
                    .then(data => {
                        const ctx = document.getElementById('financialChart').getContext('2d');
                        new Chart(ctx, {
                            type: 'bar',
                            data: {
                                labels: ['Revenue', 'Expenses', 'Payroll', 'Taxes'],
                                datasets: [{
                                    label: 'Amount ($)',
                                    data: [data.revenue, data.expenses, data.payroll, data.taxes],
                                    backgroundColor: ['#28a745', '#dc3545', '#ffc107', '#17a2b8']
                                }]
                            },
                            options: {
                                responsive: true,
                                scales: {
                                    y: {
                                        beginAtZero: true
                                    }
                                }
                            }
                        });
                    });
            </script>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')
    
    async def financial_overview_handler(self, request):
        """Get financial overview data"""
        try:
            # This would fetch real financial data
            overview = {
                'revenue': 125000,
                'expenses': 85000,
                'payroll': 45000,
                'taxes': 15000,
                'net_income': 40000,
                'cash_flow': 35000
            }
            
            return web.json_response(overview)
            
        except Exception as e:
            logger.error(f"Failed to get financial overview: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    # QuickBooks API Handlers
    
    async def sync_customers_handler(self, request):
        """Sync customers with QuickBooks"""
        try:
            result = await self.quickbooks_service.sync_customers_to_qb()
            return web.json_response({
                'status': 'success',
                'synced': result.total_synced,
                'errors': result.errors
            })
        except Exception as e:
            logger.error(f"Customer sync failed: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def sync_invoices_handler(self, request):
        """Sync invoices with QuickBooks"""
        try:
            # Implementation would call appropriate sync methods
            return web.json_response({
                'status': 'success',
                'message': 'Invoice sync initiated'
            })
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def sync_employees_handler(self, request):
        """Sync employees with QuickBooks"""
        try:
            result = await self.quickbooks_service.sync_employees_to_qb()
            return web.json_response({
                'status': 'success',
                'synced': result.total_synced,
                'errors': result.errors
            })
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def qb_sync_status_handler(self, request):
        """Get QuickBooks sync status"""
        try:
            status = await self.quickbooks_service.get_sync_status()
            return web.json_response(status)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def qb_webhook_handler(self, request):
        """Handle QuickBooks webhooks"""
        try:
            payload = await request.text()
            signature = request.headers.get('intuit-signature')
            
            result = await self.quickbooks_service.handle_webhook(payload, signature)
            return web.json_response(result)
            
        except Exception as e:
            logger.error(f"Webhook handling failed: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    # Invoice API Handlers
    
    async def generate_invoice_handler(self, request):
        """Generate invoice"""
        try:
            invoice_data = await request.json()
            
            # Create invoice object
            invoice = await self.invoice_generator.create_invoice_from_data(invoice_data)
            
            # Generate PDF
            pdf_bytes, filename = await self.invoice_generator.generate_invoice_pdf(invoice)
            
            return web.Response(
                body=pdf_bytes,
                content_type='application/pdf',
                headers={'Content-Disposition': f'attachment; filename="{filename}"'}
            )
            
        except Exception as e:
            logger.error(f"Invoice generation failed: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def send_invoice_handler(self, request):
        """Send invoice via email"""
        try:
            data = await request.json()
            invoice_id = data['invoice_id']
            recipient_email = data['recipient_email']
            
            # This would implement email sending logic
            return web.json_response({
                'status': 'success',
                'message': f'Invoice {invoice_id} sent to {recipient_email}'
            })
            
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def get_invoice_handler(self, request):
        """Get invoice details"""
        try:
            invoice_id = request.match_info['invoice_id']
            
            # This would fetch invoice from database
            return web.json_response({
                'invoice_id': invoice_id,
                'status': 'draft',
                'amount': 1500.00
            })
            
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def list_invoices_handler(self, request):
        """List invoices"""
        try:
            # This would fetch invoices from database
            invoices = [
                {'id': 1, 'number': 'INV-2024-001', 'amount': 1500.00, 'status': 'sent'},
                {'id': 2, 'number': 'INV-2024-002', 'amount': 2200.00, 'status': 'paid'}
            ]
            
            return web.json_response(invoices)
            
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    # Invoice Automation Handlers
    
    async def create_invoice_rule_handler(self, request):
        """Create invoice automation rule"""
        try:
            rule_data = await request.json()
            rule_id = await self.invoice_automation.create_invoice_rule(rule_data)
            
            return web.json_response({
                'status': 'success',
                'rule_id': rule_id
            })
            
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def list_invoice_rules_handler(self, request):
        """List invoice automation rules"""
        try:
            # This would fetch rules from database
            rules = [
                {'id': '123', 'name': 'Monthly Subscription', 'active': True},
                {'id': '456', 'name': 'Quarterly Maintenance', 'active': True}
            ]
            
            return web.json_response(rules)
            
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def update_invoice_rule_handler(self, request):
        """Update invoice automation rule"""
        try:
            rule_id = request.match_info['rule_id']
            updates = await request.json()
            
            success = await self.invoice_automation.update_invoice_rule(rule_id, updates)
            
            return web.json_response({
                'status': 'success' if success else 'failed',
                'rule_id': rule_id
            })
            
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def delete_invoice_rule_handler(self, request):
        """Delete invoice automation rule"""
        try:
            rule_id = request.match_info['rule_id']
            
            success = await self.invoice_automation.delete_invoice_rule(rule_id)
            
            return web.json_response({
                'status': 'success' if success else 'failed',
                'rule_id': rule_id
            })
            
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def invoice_automation_stats_handler(self, request):
        """Get invoice automation statistics"""
        try:
            stats = await self.invoice_automation.get_automation_statistics()
            return web.json_response(stats)
            
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    # Payroll Handlers
    
    async def create_payroll_employee_handler(self, request):
        """Create payroll employee"""
        try:
            employee_data = await request.json()
            employee_id = await self.payroll_engine.create_payroll_employee(employee_data)
            
            return web.json_response({
                'status': 'success',
                'employee_id': employee_id
            })
            
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def submit_timesheet_handler(self, request):
        """Submit employee timesheet"""
        try:
            timesheet_data = await request.json()
            timesheet_id = await self.payroll_engine.submit_timesheet(timesheet_data)
            
            return web.json_response({
                'status': 'success',
                'timesheet_id': timesheet_id
            })
            
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def approve_timesheet_handler(self, request):
        """Approve employee timesheet"""
        try:
            timesheet_id = request.match_info['timesheet_id']
            data = await request.json()
            approved_by = data['approved_by']
            
            success = await self.payroll_engine.approve_timesheet(int(timesheet_id), approved_by)
            
            return web.json_response({
                'status': 'success' if success else 'failed',
                'timesheet_id': timesheet_id
            })
            
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def create_payroll_run_handler(self, request):
        """Create payroll run"""
        try:
            run_data = await request.json()
            payroll_run_id = await self.payroll_engine.create_payroll_run(run_data)
            
            return web.json_response({
                'status': 'success',
                'payroll_run_id': payroll_run_id
            })
            
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def calculate_payroll_handler(self, request):
        """Calculate payroll"""
        try:
            run_id = request.match_info['run_id']
            results = await self.payroll_engine.calculate_payroll(int(run_id))
            
            return web.json_response(results)
            
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def process_payroll_handler(self, request):
        """Process payroll payments"""
        try:
            run_id = request.match_info['run_id']
            results = await self.payroll_engine.process_direct_deposits(int(run_id))
            
            return web.json_response(results)
            
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def payroll_report_handler(self, request):
        """Get payroll report"""
        try:
            run_id = request.match_info['run_id']
            report = await self.payroll_engine.generate_payroll_report(int(run_id))
            
            return web.json_response(report)
            
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    # Tax Filing Handlers
    
    async def prepare_form_941_handler(self, request):
        """Prepare Form 941"""
        try:
            data = await request.json()
            quarter = data['quarter']
            year = data['year']
            
            form_id = await self.tax_service.prepare_form_941(quarter, year)
            
            return web.json_response({
                'status': 'success',
                'form_id': form_id
            })
            
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def prepare_w2_forms_handler(self, request):
        """Prepare W-2 forms"""
        try:
            data = await request.json()
            tax_year = data['tax_year']
            
            form_ids = await self.tax_service.prepare_w2_forms(tax_year)
            
            return web.json_response({
                'status': 'success',
                'form_count': len(form_ids),
                'form_ids': form_ids
            })
            
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def file_tax_form_handler(self, request):
        """File tax form electronically"""
        try:
            form_id = request.match_info['form_id']
            
            result = await self.tax_service.submit_form_electronically(form_id)
            
            return web.json_response(result)
            
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def tax_filing_status_handler(self, request):
        """Check tax filing status"""
        try:
            form_id = request.match_info['form_id']
            
            status = await self.tax_service.check_filing_status(form_id)
            
            return web.json_response(status)
            
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def tax_compliance_handler(self, request):
        """Get tax compliance status"""
        try:
            alerts_created = await self.tax_service.monitor_compliance()
            
            return web.json_response({
                'compliance_check_completed': True,
                'alerts_created': alerts_created
            })
            
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def tax_calendar_handler(self, request):
        """Get tax filing calendar"""
        try:
            year = int(request.match_info['year'])
            
            calendar = await self.tax_service.get_tax_calendar(year)
            
            return web.json_response(calendar)
            
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    # Report Handlers
    
    async def financial_summary_handler(self, request):
        """Get financial summary report"""
        try:
            # This would generate comprehensive financial summary
            summary = {
                'revenue': {
                    'current_month': 45000,
                    'previous_month': 42000,
                    'ytd': 480000
                },
                'expenses': {
                    'current_month': 32000,
                    'previous_month': 31000,
                    'ytd': 350000
                },
                'profit': {
                    'current_month': 13000,
                    'previous_month': 11000,
                    'ytd': 130000
                }
            }
            
            return web.json_response(summary)
            
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def payroll_summary_handler(self, request):
        """Get payroll summary report"""
        try:
            # This would generate payroll summary
            summary = {
                'total_employees': 25,
                'total_payroll_ytd': 875000,
                'average_salary': 35000,
                'tax_withholdings_ytd': 142000
            }
            
            return web.json_response(summary)
            
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def tax_summary_handler(self, request):
        """Get tax summary report"""
        try:
            year = int(request.match_info['year'])
            
            summary = await self.tax_service.generate_tax_summary_report(year)
            
            return web.json_response(summary)
            
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    # Service Management
    
    async def run_server(self, host='0.0.0.0', port=8080):
        """Run the financial management web server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, host, port)
        await site.start()
        
        logger.info(f"Financial Management Service started at http://{host}:{port}")
        
        try:
            # Keep the server running
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            logger.info("Shutting down Financial Management Service...")
        finally:
            await runner.cleanup()

def main():
    """Main entry point"""
    async def run_service():
        config_path = os.getenv('FINANCIAL_CONFIG_PATH', 'financial_config.yml')
        service = FinancialManagementService(config_path)
        
        try:
            await service.initialize()
            await service.run_server()
        finally:
            await service.shutdown()
    
    asyncio.run(run_service())

if __name__ == '__main__':
    main()