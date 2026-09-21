#!/usr/bin/env python3
"""
QuickBooks Integration Service for ActiveLog
High-level service that manages QuickBooks integration and data synchronization
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import asyncpg
from dataclasses import dataclass, asdict
import yaml
from .quickbooks_client import (
    QuickBooksClient, QBOAuth, QBOCustomer, QBOItem, 
    QBOInvoice, QBOPayment, QBOEmployee, QuickBooksWebhookHandler
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SyncStatus:
    """Synchronization status for entities"""
    entity_type: str
    last_sync: datetime
    total_synced: int
    errors: int
    status: str  # 'success', 'error', 'in_progress'

class QuickBooksIntegrationService:
    """Main QuickBooks integration service for ActiveLog"""
    
    def __init__(self, config_path: str):
        self.config = self.load_config(config_path)
        self.auth = self.create_auth_from_config()
        self.qb_client = None
        self.db_pool = None
        self.webhook_handler = QuickBooksWebhookHandler(
            self.config['quickbooks']['webhook_token']
        )
        
        # Sync status tracking
        self.sync_status: Dict[str, SyncStatus] = {}
        
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def create_auth_from_config(self) -> QBOAuth:
        """Create QuickBooks auth from configuration"""
        qb_config = self.config['quickbooks']
        return QBOAuth(
            client_id=qb_config['client_id'],
            client_secret=qb_config['client_secret'],
            access_token=qb_config.get('access_token'),
            refresh_token=qb_config.get('refresh_token'),
            realm_id=qb_config.get('realm_id'),
            scope=qb_config.get('scope', 'com.intuit.quickbooks.accounting')
        )
    
    async def initialize(self):
        """Initialize the service"""
        # Connect to database
        await self.connect_database()
        
        # Initialize QuickBooks client
        self.qb_client = QuickBooksClient(self.auth, 
                                         sandbox=self.config['quickbooks']['sandbox'])
        await self.qb_client.__aenter__()
        
        # Create database tables
        await self.create_tables()
        
        logger.info("QuickBooks integration service initialized")
    
    async def shutdown(self):
        """Shutdown the service"""
        if self.qb_client:
            await self.qb_client.__aexit__(None, None, None)
        
        if self.db_pool:
            await self.db_pool.close()
        
        logger.info("QuickBooks integration service shutdown")
    
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
    
    async def create_tables(self):
        """Create database tables for QuickBooks integration"""
        async with self.db_pool.acquire() as conn:
            # QuickBooks sync status table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS qb_sync_status (
                    id SERIAL PRIMARY KEY,
                    entity_type VARCHAR(50) NOT NULL UNIQUE,
                    last_sync TIMESTAMP WITH TIME ZONE,
                    total_synced INTEGER DEFAULT 0,
                    errors INTEGER DEFAULT 0,
                    status VARCHAR(20) DEFAULT 'pending',
                    last_error TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
            
            # Customer mapping table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS qb_customer_mapping (
                    id SERIAL PRIMARY KEY,
                    activelog_customer_id INTEGER NOT NULL,
                    qb_customer_id VARCHAR(50) NOT NULL,
                    qb_sync_token VARCHAR(20),
                    last_synced TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(activelog_customer_id),
                    UNIQUE(qb_customer_id)
                )
            ''')
            
            # Invoice mapping table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS qb_invoice_mapping (
                    id SERIAL PRIMARY KEY,
                    activelog_invoice_id INTEGER NOT NULL,
                    qb_invoice_id VARCHAR(50) NOT NULL,
                    qb_doc_number VARCHAR(50),
                    qb_sync_token VARCHAR(20),
                    last_synced TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(activelog_invoice_id),
                    UNIQUE(qb_invoice_id)
                )
            ''')
            
            # Employee mapping table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS qb_employee_mapping (
                    id SERIAL PRIMARY KEY,
                    activelog_employee_id INTEGER NOT NULL,
                    qb_employee_id VARCHAR(50) NOT NULL,
                    qb_sync_token VARCHAR(20),
                    last_synced TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(activelog_employee_id),
                    UNIQUE(qb_employee_id)
                )
            ''')
            
            # Webhook events table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS qb_webhook_events (
                    id SERIAL PRIMARY KEY,
                    realm_id VARCHAR(50) NOT NULL,
                    entity_name VARCHAR(50) NOT NULL,
                    entity_id VARCHAR(50) NOT NULL,
                    operation VARCHAR(20) NOT NULL,
                    processed BOOLEAN DEFAULT FALSE,
                    payload JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    processed_at TIMESTAMP WITH TIME ZONE
                )
            ''')
    
    # Customer Synchronization
    async def sync_customers_to_qb(self) -> SyncStatus:
        """Sync ActiveLog customers to QuickBooks"""
        logger.info("Starting customer sync to QuickBooks...")
        
        sync_status = SyncStatus(
            entity_type='customers',
            last_sync=datetime.now(),
            total_synced=0,
            errors=0,
            status='in_progress'
        )
        
        try:
            async with self.db_pool.acquire() as conn:
                # Get ActiveLog customers that need syncing
                customers = await conn.fetch('''
                    SELECT c.id, c.name, c.email, c.phone, c.company,
                           c.billing_address, c.created_at
                    FROM customers c
                    LEFT JOIN qb_customer_mapping qm ON c.id = qm.activelog_customer_id
                    WHERE qm.id IS NULL AND c.active = true
                    ORDER BY c.created_at DESC
                    LIMIT 100
                ''')
                
                for customer_row in customers:
                    try:
                        # Create QuickBooks customer
                        qb_customer = QBOCustomer(
                            name=customer_row['company'] or customer_row['name'],
                            email=customer_row['email'],
                            phone=customer_row['phone'],
                            billing_address=json.loads(customer_row['billing_address']) if customer_row['billing_address'] else None
                        )
                        
                        created_customer = await self.qb_client.create_customer(qb_customer)
                        
                        # Store mapping
                        await conn.execute('''
                            INSERT INTO qb_customer_mapping 
                            (activelog_customer_id, qb_customer_id, qb_sync_token, last_synced)
                            VALUES ($1, $2, $3, $4)
                        ''', 
                        customer_row['id'], 
                        created_customer['Id'],
                        created_customer['SyncToken'],
                        datetime.now()
                        )
                        
                        sync_status.total_synced += 1
                        logger.info(f"Synced customer {customer_row['name']} to QuickBooks")
                        
                    except Exception as e:
                        logger.error(f"Failed to sync customer {customer_row['id']}: {e}")
                        sync_status.errors += 1
                
                sync_status.status = 'success' if sync_status.errors == 0 else 'error'
                await self.update_sync_status(sync_status)
                
        except Exception as e:
            logger.error(f"Customer sync failed: {e}")
            sync_status.status = 'error'
            sync_status.errors += 1
            await self.update_sync_status(sync_status)
        
        return sync_status
    
    async def sync_customers_from_qb(self) -> SyncStatus:
        """Sync QuickBooks customers to ActiveLog"""
        logger.info("Starting customer sync from QuickBooks...")
        
        sync_status = SyncStatus(
            entity_type='qb_customers',
            last_sync=datetime.now(),
            total_synced=0,
            errors=0,
            status='in_progress'
        )
        
        try:
            # Get QuickBooks customers
            qb_customers = await self.qb_client.list_customers()
            
            async with self.db_pool.acquire() as conn:
                for qb_customer in qb_customers:
                    try:
                        # Check if customer already exists
                        existing_mapping = await conn.fetchrow('''
                            SELECT activelog_customer_id FROM qb_customer_mapping 
                            WHERE qb_customer_id = $1
                        ''', qb_customer['Id'])
                        
                        if existing_mapping:
                            continue  # Skip existing customers
                        
                        # Create ActiveLog customer
                        customer_id = await conn.fetchval('''
                            INSERT INTO customers 
                            (name, email, phone, company, created_at, active)
                            VALUES ($1, $2, $3, $4, $5, $6)
                            RETURNING id
                        ''',
                        qb_customer['Name'],
                        qb_customer.get('PrimaryEmailAddr', {}).get('Address'),
                        qb_customer.get('PrimaryPhone', {}).get('FreeFormNumber'),
                        qb_customer.get('CompanyName', qb_customer['Name']),
                        datetime.now(),
                        qb_customer.get('Active', True)
                        )
                        
                        # Create mapping
                        await conn.execute('''
                            INSERT INTO qb_customer_mapping 
                            (activelog_customer_id, qb_customer_id, qb_sync_token, last_synced)
                            VALUES ($1, $2, $3, $4)
                        ''',
                        customer_id,
                        qb_customer['Id'],
                        qb_customer['SyncToken'],
                        datetime.now()
                        )
                        
                        sync_status.total_synced += 1
                        logger.info(f"Synced QB customer {qb_customer['Name']} to ActiveLog")
                        
                    except Exception as e:
                        logger.error(f"Failed to sync QB customer {qb_customer['Id']}: {e}")
                        sync_status.errors += 1
                
                sync_status.status = 'success' if sync_status.errors == 0 else 'error'
                await self.update_sync_status(sync_status)
                
        except Exception as e:
            logger.error(f"QB customer sync failed: {e}")
            sync_status.status = 'error'
            sync_status.errors += 1
            await self.update_sync_status(sync_status)
        
        return sync_status
    
    # Invoice Synchronization
    async def create_qb_invoice(self, activelog_invoice_id: int) -> Optional[str]:
        """Create QuickBooks invoice from ActiveLog invoice"""
        try:
            async with self.db_pool.acquire() as conn:
                # Get ActiveLog invoice with details
                invoice_data = await conn.fetchrow('''
                    SELECT i.id, i.invoice_number, i.issue_date, i.due_date,
                           i.customer_id, i.subtotal, i.tax_amount, i.total_amount,
                           i.status, i.notes, c.name as customer_name
                    FROM invoices i
                    JOIN customers c ON i.customer_id = c.id
                    WHERE i.id = $1
                ''', activelog_invoice_id)
                
                if not invoice_data:
                    raise ValueError(f"Invoice {activelog_invoice_id} not found")
                
                # Get customer mapping
                customer_mapping = await conn.fetchrow('''
                    SELECT qb_customer_id FROM qb_customer_mapping 
                    WHERE activelog_customer_id = $1
                ''', invoice_data['customer_id'])
                
                if not customer_mapping:
                    raise ValueError(f"Customer {invoice_data['customer_id']} not synced to QB")
                
                # Get invoice line items
                line_items_data = await conn.fetch('''
                    SELECT description, quantity, unit_price, total_amount
                    FROM invoice_line_items
                    WHERE invoice_id = $1
                    ORDER BY line_number
                ''', activelog_invoice_id)
                
                # Build QuickBooks line items
                qb_line_items = []
                for i, item in enumerate(line_items_data, 1):
                    qb_line_items.append({
                        'Id': str(i),
                        'LineNum': i,
                        'Amount': float(item['total_amount']),
                        'DetailType': 'SalesItemLineDetail',
                        'SalesItemLineDetail': {
                            'Qty': float(item['quantity']),
                            'UnitPrice': float(item['unit_price']),
                            'ItemRef': {'value': '1', 'name': 'Services'}  # Default service item
                        },
                        'Description': item['description']
                    })
                
                # Create QuickBooks invoice
                qb_invoice = QBOInvoice(
                    doc_number=invoice_data['invoice_number'],
                    txn_date=invoice_data['issue_date'].isoformat(),
                    due_date=invoice_data['due_date'].isoformat(),
                    customer_ref={'value': customer_mapping['qb_customer_id']},
                    line_items=qb_line_items,
                    total_amt=float(invoice_data['total_amount'])
                )
                
                created_invoice = await self.qb_client.create_invoice(qb_invoice)
                
                # Store mapping
                await conn.execute('''
                    INSERT INTO qb_invoice_mapping 
                    (activelog_invoice_id, qb_invoice_id, qb_doc_number, qb_sync_token, last_synced)
                    VALUES ($1, $2, $3, $4, $5)
                ''',
                activelog_invoice_id,
                created_invoice['Id'],
                created_invoice.get('DocNumber'),
                created_invoice['SyncToken'],
                datetime.now()
                )
                
                logger.info(f"Created QB invoice {created_invoice['Id']} for ActiveLog invoice {activelog_invoice_id}")
                return created_invoice['Id']
                
        except Exception as e:
            logger.error(f"Failed to create QB invoice for {activelog_invoice_id}: {e}")
            return None
    
    async def send_invoice_email(self, activelog_invoice_id: int, email_address: str) -> bool:
        """Send QuickBooks invoice via email"""
        try:
            async with self.db_pool.acquire() as conn:
                # Get QuickBooks invoice ID
                mapping = await conn.fetchrow('''
                    SELECT qb_invoice_id FROM qb_invoice_mapping 
                    WHERE activelog_invoice_id = $1
                ''', activelog_invoice_id)
                
                if not mapping:
                    raise ValueError(f"No QB invoice found for ActiveLog invoice {activelog_invoice_id}")
                
                success = await self.qb_client.send_invoice_email(
                    mapping['qb_invoice_id'], 
                    email_address
                )
                
                if success:
                    logger.info(f"Sent QB invoice {mapping['qb_invoice_id']} to {email_address}")
                
                return success
                
        except Exception as e:
            logger.error(f"Failed to send QB invoice email: {e}")
            return False
    
    # Employee Synchronization
    async def sync_employees_to_qb(self) -> SyncStatus:
        """Sync ActiveLog employees to QuickBooks"""
        logger.info("Starting employee sync to QuickBooks...")
        
        sync_status = SyncStatus(
            entity_type='employees',
            last_sync=datetime.now(),
            total_synced=0,
            errors=0,
            status='in_progress'
        )
        
        try:
            async with self.db_pool.acquire() as conn:
                # Get ActiveLog employees that need syncing
                employees = await conn.fetch('''
                    SELECT e.id, e.first_name, e.last_name, e.email, e.phone,
                           e.employee_number, e.hire_date, e.status, e.ssn
                    FROM employees e
                    LEFT JOIN qb_employee_mapping qm ON e.id = qm.activelog_employee_id
                    WHERE qm.id IS NULL AND e.active = true
                    ORDER BY e.hire_date DESC
                    LIMIT 50
                ''')
                
                for employee_row in employees:
                    try:
                        # Create QuickBooks employee
                        qb_employee = QBOEmployee(
                            name=f"{employee_row['first_name']} {employee_row['last_name']}",
                            employee_number=employee_row['employee_number'],
                            ssn=employee_row['ssn'],
                            hire_date=employee_row['hire_date'].isoformat(),
                            status='Active' if employee_row['status'] == 'active' else 'Released',
                            primary_email_addr={'Address': employee_row['email']} if employee_row['email'] else None,
                            primary_phone={'FreeFormNumber': employee_row['phone']} if employee_row['phone'] else None
                        )
                        
                        created_employee = await self.qb_client.create_employee(qb_employee)
                        
                        # Store mapping
                        await conn.execute('''
                            INSERT INTO qb_employee_mapping 
                            (activelog_employee_id, qb_employee_id, qb_sync_token, last_synced)
                            VALUES ($1, $2, $3, $4)
                        ''',
                        employee_row['id'],
                        created_employee['Id'],
                        created_employee['SyncToken'],
                        datetime.now()
                        )
                        
                        sync_status.total_synced += 1
                        logger.info(f"Synced employee {employee_row['first_name']} {employee_row['last_name']} to QuickBooks")
                        
                    except Exception as e:
                        logger.error(f"Failed to sync employee {employee_row['id']}: {e}")
                        sync_status.errors += 1
                
                sync_status.status = 'success' if sync_status.errors == 0 else 'error'
                await self.update_sync_status(sync_status)
                
        except Exception as e:
            logger.error(f"Employee sync failed: {e}")
            sync_status.status = 'error'
            sync_status.errors += 1
            await self.update_sync_status(sync_status)
        
        return sync_status
    
    # Webhook Handling
    async def handle_webhook(self, payload: str, signature: str) -> Dict[str, Any]:
        """Handle QuickBooks webhook"""
        try:
            result = await self.webhook_handler.handle_webhook(payload, signature)
            
            # Store webhook events for processing
            webhook_data = json.loads(payload)
            
            async with self.db_pool.acquire() as conn:
                for entity_data in webhook_data.get('eventNotifications', []):
                    realm_id = entity_data.get('realmId')
                    
                    for entity in entity_data.get('dataChangeEvent', {}).get('entities', []):
                        await conn.execute('''
                            INSERT INTO qb_webhook_events 
                            (realm_id, entity_name, entity_id, operation, payload)
                            VALUES ($1, $2, $3, $4, $5)
                        ''',
                        realm_id,
                        entity.get('name'),
                        entity.get('id'),
                        entity.get('operation'),
                        json.dumps(entity)
                        )
            
            # Process webhook events asynchronously
            asyncio.create_task(self.process_webhook_events())
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to handle webhook: {e}")
            raise
    
    async def process_webhook_events(self):
        """Process pending webhook events"""
        try:
            async with self.db_pool.acquire() as conn:
                # Get unprocessed events
                events = await conn.fetch('''
                    SELECT id, entity_name, entity_id, operation, payload
                    FROM qb_webhook_events
                    WHERE processed = false
                    ORDER BY created_at ASC
                    LIMIT 100
                ''')
                
                for event in events:
                    try:
                        # Process based on entity type and operation
                        if event['entity_name'] == 'Customer':
                            await self.process_customer_webhook(event)
                        elif event['entity_name'] == 'Invoice':
                            await self.process_invoice_webhook(event)
                        elif event['entity_name'] == 'Payment':
                            await self.process_payment_webhook(event)
                        elif event['entity_name'] == 'Employee':
                            await self.process_employee_webhook(event)
                        
                        # Mark as processed
                        await conn.execute('''
                            UPDATE qb_webhook_events 
                            SET processed = true, processed_at = $1
                            WHERE id = $2
                        ''', datetime.now(), event['id'])
                        
                    except Exception as e:
                        logger.error(f"Failed to process webhook event {event['id']}: {e}")
                        
        except Exception as e:
            logger.error(f"Failed to process webhook events: {e}")
    
    async def process_customer_webhook(self, event: Dict[str, Any]):
        """Process customer webhook event"""
        # Implement customer-specific webhook logic
        logger.info(f"Processing customer webhook: {event['operation']} for {event['entity_id']}")
    
    async def process_invoice_webhook(self, event: Dict[str, Any]):
        """Process invoice webhook event"""
        # Implement invoice-specific webhook logic
        logger.info(f"Processing invoice webhook: {event['operation']} for {event['entity_id']}")
    
    async def process_payment_webhook(self, event: Dict[str, Any]):
        """Process payment webhook event"""
        # Implement payment-specific webhook logic
        logger.info(f"Processing payment webhook: {event['operation']} for {event['entity_id']}")
    
    async def process_employee_webhook(self, event: Dict[str, Any]):
        """Process employee webhook event"""
        # Implement employee-specific webhook logic
        logger.info(f"Processing employee webhook: {event['operation']} for {event['entity_id']}")
    
    # Reporting
    async def get_financial_reports(self, report_type: str, 
                                  start_date: str, end_date: str) -> Dict[str, Any]:
        """Get financial reports from QuickBooks"""
        try:
            if report_type == 'profit_loss':
                return await self.qb_client.get_profit_loss_report(start_date, end_date)
            elif report_type == 'balance_sheet':
                return await self.qb_client.get_balance_sheet_report(end_date)
            elif report_type == 'cash_flow':
                return await self.qb_client.get_cash_flow_report(start_date, end_date)
            else:
                raise ValueError(f"Unknown report type: {report_type}")
                
        except Exception as e:
            logger.error(f"Failed to get {report_type} report: {e}")
            raise
    
    # Utility Methods
    async def update_sync_status(self, sync_status: SyncStatus):
        """Update sync status in database"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO qb_sync_status 
                (entity_type, last_sync, total_synced, errors, status, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (entity_type) DO UPDATE SET
                    last_sync = EXCLUDED.last_sync,
                    total_synced = EXCLUDED.total_synced,
                    errors = EXCLUDED.errors,
                    status = EXCLUDED.status,
                    updated_at = EXCLUDED.updated_at
            ''',
            sync_status.entity_type,
            sync_status.last_sync,
            sync_status.total_synced,
            sync_status.errors,
            sync_status.status,
            datetime.now()
            )
    
    async def get_sync_status(self, entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get synchronization status"""
        async with self.db_pool.acquire() as conn:
            if entity_type:
                rows = await conn.fetch('''
                    SELECT * FROM qb_sync_status WHERE entity_type = $1
                ''', entity_type)
            else:
                rows = await conn.fetch('SELECT * FROM qb_sync_status ORDER BY updated_at DESC')
            
            return [dict(row) for row in rows]
    
    async def full_sync(self):
        """Perform full synchronization"""
        logger.info("Starting full QuickBooks synchronization...")
        
        # Sync customers both ways
        await self.sync_customers_to_qb()
        await self.sync_customers_from_qb()
        
        # Sync employees to QB
        await self.sync_employees_to_qb()
        
        logger.info("Full QuickBooks synchronization completed")

def main():
    """Example usage"""
    async def run_service():
        service = QuickBooksIntegrationService('qb_config.yml')
        
        try:
            await service.initialize()
            
            # Perform full sync
            await service.full_sync()
            
            # Get sync status
            status = await service.get_sync_status()
            for s in status:
                print(f"{s['entity_type']}: {s['status']} - {s['total_synced']} synced, {s['errors']} errors")
            
        finally:
            await service.shutdown()
    
    asyncio.run(run_service())

if __name__ == '__main__':
    main()