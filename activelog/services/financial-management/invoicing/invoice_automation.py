#!/usr/bin/env python3
"""
Invoice Automation Service for ActiveLog
Handles automated invoice generation, recurring billing, and workflow automation
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
import asyncpg
from dataclasses import dataclass, asdict
import yaml
from enum import Enum
import uuid
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from .invoice_generator import InvoiceGenerator, Invoice

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class InvoiceStatus(Enum):
    DRAFT = "draft"
    SENT = "sent"
    VIEWED = "viewed"
    PARTIAL_PAYMENT = "partial_payment"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"

class RecurrenceType(Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"

@dataclass
class InvoiceRule:
    """Automated invoice generation rule"""
    id: str
    name: str
    customer_id: int
    template_data: Dict[str, Any]
    recurrence_type: RecurrenceType
    start_date: datetime
    end_date: Optional[datetime]
    next_invoice_date: datetime
    is_active: bool = True
    auto_send_email: bool = False
    reminder_days: List[int] = None  # Days before due date to send reminders
    created_at: Optional[datetime] = None

@dataclass
class InvoiceWorkflowTrigger:
    """Invoice workflow trigger configuration"""
    trigger_type: str  # "status_change", "time_based", "amount_threshold"
    conditions: Dict[str, Any]
    actions: List[Dict[str, Any]]
    is_active: bool = True

@dataclass
class InvoiceReminder:
    """Invoice reminder configuration"""
    invoice_id: int
    reminder_type: str  # "before_due", "overdue", "final_notice"
    days_offset: int
    template_name: str
    sent: bool = False
    scheduled_for: Optional[datetime] = None

class InvoiceAutomationService:
    """Main invoice automation service"""
    
    def __init__(self, config_path: str, invoice_generator: InvoiceGenerator):
        self.config = self.load_config(config_path)
        self.invoice_generator = invoice_generator
        self.db_pool = None
        self.scheduler = AsyncIOScheduler()
        
        # Workflow handlers
        self.workflow_handlers: Dict[str, Callable] = {
            'send_email': self._handle_send_email,
            'update_status': self._handle_update_status,
            'create_payment_link': self._handle_create_payment_link,
            'notify_accounting': self._handle_notify_accounting,
            'apply_late_fee': self._handle_apply_late_fee,
            'suspend_service': self._handle_suspend_service
        }
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    async def initialize(self):
        """Initialize the automation service"""
        await self.connect_database()
        await self.create_tables()
        await self.setup_scheduler()
        await self.load_invoice_rules()
        
        self.scheduler.start()
        logger.info("Invoice automation service initialized")
    
    async def shutdown(self):
        """Shutdown the service"""
        if self.scheduler.running:
            self.scheduler.shutdown()
        
        if self.db_pool:
            await self.db_pool.close()
        
        logger.info("Invoice automation service shutdown")
    
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
        """Create database tables for automation"""
        async with self.db_pool.acquire() as conn:
            # Invoice automation rules
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS invoice_automation_rules (
                    id UUID PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    customer_id INTEGER NOT NULL,
                    template_data JSONB NOT NULL,
                    recurrence_type VARCHAR(20) NOT NULL,
                    start_date TIMESTAMP WITH TIME ZONE NOT NULL,
                    end_date TIMESTAMP WITH TIME ZONE,
                    next_invoice_date TIMESTAMP WITH TIME ZONE NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    auto_send_email BOOLEAN DEFAULT FALSE,
                    reminder_days INTEGER[],
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
            
            # Invoice workflow triggers
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS invoice_workflow_triggers (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    trigger_type VARCHAR(50) NOT NULL,
                    conditions JSONB NOT NULL,
                    actions JSONB NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
            
            # Invoice reminders
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS invoice_reminders (
                    id SERIAL PRIMARY KEY,
                    invoice_id INTEGER NOT NULL,
                    reminder_type VARCHAR(50) NOT NULL,
                    days_offset INTEGER NOT NULL,
                    template_name VARCHAR(100),
                    sent BOOLEAN DEFAULT FALSE,
                    scheduled_for TIMESTAMP WITH TIME ZONE,
                    sent_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
            
            # Invoice status history
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS invoice_status_history (
                    id SERIAL PRIMARY KEY,
                    invoice_id INTEGER NOT NULL,
                    old_status VARCHAR(50),
                    new_status VARCHAR(50) NOT NULL,
                    changed_by VARCHAR(100),
                    notes TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
            
            # Automated invoice log
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS automated_invoice_log (
                    id SERIAL PRIMARY KEY,
                    rule_id UUID NOT NULL REFERENCES invoice_automation_rules(id),
                    invoice_id INTEGER,
                    status VARCHAR(50) NOT NULL,
                    error_message TEXT,
                    execution_time_ms INTEGER,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
    
    async def setup_scheduler(self):
        """Setup scheduled jobs"""
        # Daily job to generate recurring invoices
        self.scheduler.add_job(
            self.generate_recurring_invoices,
            CronTrigger(hour=9, minute=0),  # Run daily at 9 AM
            id='generate_recurring_invoices',
            name='Generate Recurring Invoices',
            replace_existing=True
        )
        
        # Daily job to check for overdue invoices
        self.scheduler.add_job(
            self.check_overdue_invoices,
            CronTrigger(hour=10, minute=0),  # Run daily at 10 AM
            id='check_overdue_invoices',
            name='Check Overdue Invoices',
            replace_existing=True
        )
        
        # Hourly job to process invoice reminders
        self.scheduler.add_job(
            self.process_invoice_reminders,
            CronTrigger(minute=0),  # Run every hour
            id='process_invoice_reminders',
            name='Process Invoice Reminders',
            replace_existing=True
        )
        
        # Daily job to execute workflow triggers
        self.scheduler.add_job(
            self.execute_workflow_triggers,
            CronTrigger(hour=11, minute=0),  # Run daily at 11 AM
            id='execute_workflow_triggers',
            name='Execute Workflow Triggers',
            replace_existing=True
        )
    
    async def load_invoice_rules(self):
        """Load and schedule invoice automation rules"""
        async with self.db_pool.acquire() as conn:
            rules = await conn.fetch('''
                SELECT * FROM invoice_automation_rules 
                WHERE is_active = TRUE
            ''')
            
            for rule_row in rules:
                rule = InvoiceRule(
                    id=str(rule_row['id']),
                    name=rule_row['name'],
                    customer_id=rule_row['customer_id'],
                    template_data=rule_row['template_data'],
                    recurrence_type=RecurrenceType(rule_row['recurrence_type']),
                    start_date=rule_row['start_date'],
                    end_date=rule_row['end_date'],
                    next_invoice_date=rule_row['next_invoice_date'],
                    is_active=rule_row['is_active'],
                    auto_send_email=rule_row['auto_send_email'],
                    reminder_days=rule_row['reminder_days'] or [],
                    created_at=rule_row['created_at']
                )
                
                logger.info(f"Loaded invoice rule: {rule.name}")
    
    # Invoice Rule Management
    async def create_invoice_rule(self, rule_data: Dict[str, Any]) -> str:
        """Create a new invoice automation rule"""
        rule_id = str(uuid.uuid4())
        
        rule = InvoiceRule(
            id=rule_id,
            name=rule_data['name'],
            customer_id=rule_data['customer_id'],
            template_data=rule_data['template_data'],
            recurrence_type=RecurrenceType(rule_data['recurrence_type']),
            start_date=datetime.fromisoformat(rule_data['start_date']),
            end_date=datetime.fromisoformat(rule_data['end_date']) if rule_data.get('end_date') else None,
            next_invoice_date=datetime.fromisoformat(rule_data['next_invoice_date']),
            auto_send_email=rule_data.get('auto_send_email', False),
            reminder_days=rule_data.get('reminder_days', [7, 3, 1])
        )
        
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO invoice_automation_rules 
                (id, name, customer_id, template_data, recurrence_type, 
                 start_date, end_date, next_invoice_date, auto_send_email, reminder_days)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ''',
            rule.id, rule.name, rule.customer_id, json.dumps(rule.template_data),
            rule.recurrence_type.value, rule.start_date, rule.end_date,
            rule.next_invoice_date, rule.auto_send_email, rule.reminder_days
            )
        
        logger.info(f"Created invoice automation rule: {rule.name}")
        return rule_id
    
    async def update_invoice_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing invoice rule"""
        try:
            async with self.db_pool.acquire() as conn:
                set_clauses = []
                values = []
                value_index = 1
                
                for field, value in updates.items():
                    if field in ['template_data']:
                        value = json.dumps(value)
                    set_clauses.append(f"{field} = ${value_index}")
                    values.append(value)
                    value_index += 1
                
                set_clauses.append(f"updated_at = ${value_index}")
                values.append(datetime.now())
                values.append(rule_id)
                
                query = f"""
                    UPDATE invoice_automation_rules 
                    SET {', '.join(set_clauses)}
                    WHERE id = ${value_index + 1}
                """
                
                result = await conn.execute(query, *values)
                return result != 'UPDATE 0'
                
        except Exception as e:
            logger.error(f"Failed to update invoice rule {rule_id}: {e}")
            return False
    
    async def delete_invoice_rule(self, rule_id: str) -> bool:
        """Delete an invoice rule"""
        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.execute('''
                    UPDATE invoice_automation_rules 
                    SET is_active = FALSE 
                    WHERE id = $1
                ''', rule_id)
                
                return result != 'UPDATE 0'
                
        except Exception as e:
            logger.error(f"Failed to delete invoice rule {rule_id}: {e}")
            return False
    
    # Recurring Invoice Generation
    async def generate_recurring_invoices(self):
        """Generate invoices based on automation rules"""
        logger.info("Starting recurring invoice generation...")
        
        async with self.db_pool.acquire() as conn:
            # Get rules that should generate invoices today
            rules = await conn.fetch('''
                SELECT * FROM invoice_automation_rules 
                WHERE is_active = TRUE 
                AND next_invoice_date <= NOW()
                AND (end_date IS NULL OR end_date > NOW())
            ''')
            
            for rule_row in rules:
                try:
                    await self._generate_invoice_from_rule(rule_row)
                except Exception as e:
                    logger.error(f"Failed to generate invoice for rule {rule_row['id']}: {e}")
    
    async def _generate_invoice_from_rule(self, rule_row: Dict[str, Any]):
        """Generate a single invoice from a rule"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Parse rule data
            rule_id = str(rule_row['id'])
            template_data = rule_row['template_data']
            customer_id = rule_row['customer_id']
            
            # Get customer information
            async with self.db_pool.acquire() as conn:
                customer = await conn.fetchrow('''
                    SELECT * FROM customers WHERE id = $1
                ''', customer_id)
                
                if not customer:
                    raise ValueError(f"Customer {customer_id} not found")
                
                # Generate unique invoice number
                invoice_number = await self._generate_invoice_number()
                
                # Update template data with customer info and invoice number
                invoice_data = template_data.copy()
                invoice_data.update({
                    'invoice_number': invoice_number,
                    'customer_name': customer['name'],
                    'customer_email': customer['email'],
                    'customer_phone': customer['phone'],
                    'issue_date': datetime.now().isoformat(),
                    'due_date': (datetime.now() + timedelta(days=30)).isoformat()
                })
                
                # Create invoice record in database
                invoice_id = await conn.fetchval('''
                    INSERT INTO invoices 
                    (invoice_number, customer_id, issue_date, due_date, 
                     subtotal, tax_amount, total_amount, status, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    RETURNING id
                ''',
                invoice_number, customer_id, datetime.now(), 
                datetime.now() + timedelta(days=30),
                template_data.get('subtotal', 0),
                template_data.get('tax_amount', 0),
                template_data.get('total_amount', 0),
                InvoiceStatus.DRAFT.value,
                datetime.now()
                )
                
                # Generate the actual invoice
                invoice = await self.invoice_generator.create_invoice_from_data(invoice_data)
                pdf_bytes, filename = await self.invoice_generator.generate_invoice_pdf(invoice)
                
                # Send email if auto_send_email is enabled
                if rule_row['auto_send_email'] and customer['email']:
                    email_sent = await self.invoice_generator.send_invoice_email(
                        invoice, customer['email'], pdf_bytes, filename
                    )
                    
                    if email_sent:
                        await conn.execute('''
                            UPDATE invoices SET status = $1 WHERE id = $2
                        ''', InvoiceStatus.SENT.value, invoice_id)
                
                # Schedule reminders if configured
                if rule_row['reminder_days']:
                    await self._schedule_invoice_reminders(invoice_id, rule_row['reminder_days'])
                
                # Update next invoice date
                next_date = self._calculate_next_invoice_date(
                    rule_row['next_invoice_date'],
                    RecurrenceType(rule_row['recurrence_type'])
                )
                
                await conn.execute('''
                    UPDATE invoice_automation_rules 
                    SET next_invoice_date = $1 
                    WHERE id = $2
                ''', next_date, rule_id)
                
                # Log successful generation
                execution_time = int((asyncio.get_event_loop().time() - start_time) * 1000)
                await conn.execute('''
                    INSERT INTO automated_invoice_log 
                    (rule_id, invoice_id, status, execution_time_ms)
                    VALUES ($1, $2, $3, $4)
                ''', rule_id, invoice_id, 'success', execution_time)
                
                logger.info(f"Generated invoice {invoice_number} from rule {rule_row['name']}")
                
        except Exception as e:
            # Log error
            execution_time = int((asyncio.get_event_loop().time() - start_time) * 1000)
            async with self.db_pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO automated_invoice_log 
                    (rule_id, invoice_id, status, error_message, execution_time_ms)
                    VALUES ($1, $2, $3, $4, $5)
                ''', rule_id, None, 'error', str(e), execution_time)
            
            logger.error(f"Failed to generate invoice from rule {rule_id}: {e}")
            raise
    
    def _calculate_next_invoice_date(self, current_date: datetime, 
                                   recurrence_type: RecurrenceType) -> datetime:
        """Calculate the next invoice date based on recurrence type"""
        if recurrence_type == RecurrenceType.WEEKLY:
            return current_date + timedelta(weeks=1)
        elif recurrence_type == RecurrenceType.MONTHLY:
            # Add one month, handling month-end dates
            if current_date.month == 12:
                return current_date.replace(year=current_date.year + 1, month=1)
            else:
                try:
                    return current_date.replace(month=current_date.month + 1)
                except ValueError:
                    # Handle cases like Jan 31 -> Feb 28
                    return current_date.replace(month=current_date.month + 1, day=28)
        elif recurrence_type == RecurrenceType.QUARTERLY:
            return current_date + timedelta(days=90)
        elif recurrence_type == RecurrenceType.YEARLY:
            try:
                return current_date.replace(year=current_date.year + 1)
            except ValueError:
                # Handle leap year edge case
                return current_date.replace(year=current_date.year + 1, month=2, day=28)
        
        return current_date + timedelta(days=30)  # Default to monthly
    
    async def _generate_invoice_number(self) -> str:
        """Generate unique invoice number"""
        async with self.db_pool.acquire() as conn:
            # Get next invoice number
            result = await conn.fetchval('''
                SELECT COALESCE(MAX(CAST(SUBSTRING(invoice_number FROM '[0-9]+') AS INTEGER)), 0) + 1
                FROM invoices 
                WHERE invoice_number ~ '^INV-[0-9]{4}-[0-9]+$'
            ''')
            
            year = datetime.now().year
            return f"INV-{year}-{result:06d}"
    
    # Invoice Reminders
    async def _schedule_invoice_reminders(self, invoice_id: int, reminder_days: List[int]):
        """Schedule reminders for an invoice"""
        async with self.db_pool.acquire() as conn:
            # Get invoice due date
            due_date = await conn.fetchval('''
                SELECT due_date FROM invoices WHERE id = $1
            ''', invoice_id)
            
            for days in reminder_days:
                reminder_date = due_date - timedelta(days=days)
                
                # Only schedule if reminder date is in the future
                if reminder_date > datetime.now():
                    await conn.execute('''
                        INSERT INTO invoice_reminders 
                        (invoice_id, reminder_type, days_offset, scheduled_for, template_name)
                        VALUES ($1, $2, $3, $4, $5)
                    ''',
                    invoice_id, 'before_due', days, reminder_date, 'payment_reminder'
                    )
    
    async def process_invoice_reminders(self):
        """Process pending invoice reminders"""
        logger.info("Processing invoice reminders...")
        
        async with self.db_pool.acquire() as conn:
            # Get reminders that should be sent now
            reminders = await conn.fetch('''
                SELECT r.*, i.invoice_number, i.customer_id, i.due_date, i.total_amount,
                       c.name as customer_name, c.email as customer_email
                FROM invoice_reminders r
                JOIN invoices i ON r.invoice_id = i.id
                JOIN customers c ON i.customer_id = c.id
                WHERE r.sent = FALSE 
                AND r.scheduled_for <= NOW()
                AND i.status NOT IN ('paid', 'cancelled')
            ''')
            
            for reminder in reminders:
                try:
                    await self._send_invoice_reminder(reminder)
                    
                    # Mark as sent
                    await conn.execute('''
                        UPDATE invoice_reminders 
                        SET sent = TRUE, sent_at = NOW()
                        WHERE id = $1
                    ''', reminder['id'])
                    
                except Exception as e:
                    logger.error(f"Failed to send reminder {reminder['id']}: {e}")
    
    async def _send_invoice_reminder(self, reminder: Dict[str, Any]):
        """Send a single invoice reminder"""
        # This would integrate with your email service
        logger.info(f"Sending reminder for invoice {reminder['invoice_number']} to {reminder['customer_email']}")
        
        # Generate reminder email content
        days_until_due = (reminder['due_date'] - datetime.now()).days
        
        if days_until_due > 0:
            subject = f"Reminder: Invoice {reminder['invoice_number']} due in {days_until_due} days"
        else:
            subject = f"Overdue: Invoice {reminder['invoice_number']} was due {abs(days_until_due)} days ago"
        
        # This is where you'd send the actual email
        logger.info(f"Would send email: {subject}")
    
    # Overdue Invoice Processing
    async def check_overdue_invoices(self):
        """Check for and process overdue invoices"""
        logger.info("Checking for overdue invoices...")
        
        async with self.db_pool.acquire() as conn:
            # Get overdue invoices
            overdue_invoices = await conn.fetch('''
                SELECT * FROM invoices 
                WHERE due_date < NOW() 
                AND status NOT IN ('paid', 'cancelled', 'overdue')
            ''')
            
            for invoice in overdue_invoices:
                try:
                    # Update status to overdue
                    await self._update_invoice_status(
                        invoice['id'], 
                        invoice['status'], 
                        InvoiceStatus.OVERDUE.value,
                        "Automatically marked as overdue"
                    )
                    
                    # Schedule overdue reminders
                    await self._schedule_overdue_reminders(invoice['id'])
                    
                except Exception as e:
                    logger.error(f"Failed to process overdue invoice {invoice['id']}: {e}")
    
    async def _schedule_overdue_reminders(self, invoice_id: int):
        """Schedule overdue reminders"""
        reminder_schedule = [1, 7, 14, 30]  # Days after due date
        
        async with self.db_pool.acquire() as conn:
            for days in reminder_schedule:
                reminder_date = datetime.now() + timedelta(days=days)
                
                await conn.execute('''
                    INSERT INTO invoice_reminders 
                    (invoice_id, reminder_type, days_offset, scheduled_for, template_name)
                    VALUES ($1, $2, $3, $4, $5)
                ''',
                invoice_id, 'overdue', days, reminder_date, 'overdue_notice'
                )
    
    # Workflow Triggers
    async def execute_workflow_triggers(self):
        """Execute invoice workflow triggers"""
        logger.info("Executing workflow triggers...")
        
        async with self.db_pool.acquire() as conn:
            # Get active workflow triggers
            triggers = await conn.fetch('''
                SELECT * FROM invoice_workflow_triggers 
                WHERE is_active = TRUE
            ''')
            
            for trigger in triggers:
                try:
                    await self._execute_workflow_trigger(trigger)
                except Exception as e:
                    logger.error(f"Failed to execute workflow trigger {trigger['id']}: {e}")
    
    async def _execute_workflow_trigger(self, trigger: Dict[str, Any]):
        """Execute a single workflow trigger"""
        trigger_type = trigger['trigger_type']
        conditions = trigger['conditions']
        actions = trigger['actions']
        
        # Find invoices that match the trigger conditions
        matching_invoices = await self._find_invoices_matching_conditions(trigger_type, conditions)
        
        for invoice_id in matching_invoices:
            for action in actions:
                await self._execute_workflow_action(invoice_id, action)
    
    async def _find_invoices_matching_conditions(self, trigger_type: str, 
                                               conditions: Dict[str, Any]) -> List[int]:
        """Find invoices matching workflow conditions"""
        if trigger_type == "status_change":
            # Find invoices with specific status
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT id FROM invoices WHERE status = $1
                ''', conditions.get('status'))
                return [row['id'] for row in rows]
        
        elif trigger_type == "amount_threshold":
            # Find invoices above/below amount threshold
            operator = conditions.get('operator', '>')
            amount = conditions.get('amount', 0)
            
            async with self.db_pool.acquire() as conn:
                if operator == '>':
                    rows = await conn.fetch('''
                        SELECT id FROM invoices WHERE total_amount > $1
                    ''', amount)
                elif operator == '<':
                    rows = await conn.fetch('''
                        SELECT id FROM invoices WHERE total_amount < $1
                    ''', amount)
                else:
                    rows = await conn.fetch('''
                        SELECT id FROM invoices WHERE total_amount = $1
                    ''', amount)
                
                return [row['id'] for row in rows]
        
        return []
    
    async def _execute_workflow_action(self, invoice_id: int, action: Dict[str, Any]):
        """Execute a workflow action"""
        action_type = action.get('type')
        
        if action_type in self.workflow_handlers:
            handler = self.workflow_handlers[action_type]
            await handler(invoice_id, action.get('parameters', {}))
        else:
            logger.warning(f"Unknown workflow action type: {action_type}")
    
    # Workflow Action Handlers
    async def _handle_send_email(self, invoice_id: int, parameters: Dict[str, Any]):
        """Handle send email action"""
        logger.info(f"Sending email for invoice {invoice_id}")
        # Implementation would integrate with email service
    
    async def _handle_update_status(self, invoice_id: int, parameters: Dict[str, Any]):
        """Handle update status action"""
        new_status = parameters.get('status')
        notes = parameters.get('notes', 'Status updated by workflow')
        
        async with self.db_pool.acquire() as conn:
            current_status = await conn.fetchval('''
                SELECT status FROM invoices WHERE id = $1
            ''', invoice_id)
            
            await self._update_invoice_status(invoice_id, current_status, new_status, notes)
    
    async def _handle_create_payment_link(self, invoice_id: int, parameters: Dict[str, Any]):
        """Handle create payment link action"""
        logger.info(f"Creating payment link for invoice {invoice_id}")
        # Implementation would integrate with payment processor
    
    async def _handle_notify_accounting(self, invoice_id: int, parameters: Dict[str, Any]):
        """Handle notify accounting action"""
        logger.info(f"Notifying accounting about invoice {invoice_id}")
        # Implementation would send notification
    
    async def _handle_apply_late_fee(self, invoice_id: int, parameters: Dict[str, Any]):
        """Handle apply late fee action"""
        fee_amount = parameters.get('amount', 25.00)
        logger.info(f"Applying late fee of ${fee_amount} to invoice {invoice_id}")
        
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                UPDATE invoices 
                SET total_amount = total_amount + $1,
                    late_fee_applied = TRUE
                WHERE id = $2
            ''', fee_amount, invoice_id)
    
    async def _handle_suspend_service(self, invoice_id: int, parameters: Dict[str, Any]):
        """Handle suspend service action"""
        logger.info(f"Suspending service for invoice {invoice_id}")
        # Implementation would integrate with service management
    
    # Utility Methods
    async def _update_invoice_status(self, invoice_id: int, old_status: str, 
                                   new_status: str, notes: str = None):
        """Update invoice status with history tracking"""
        async with self.db_pool.acquire() as conn:
            # Update invoice status
            await conn.execute('''
                UPDATE invoices SET status = $1 WHERE id = $2
            ''', new_status, invoice_id)
            
            # Record status change history
            await conn.execute('''
                INSERT INTO invoice_status_history 
                (invoice_id, old_status, new_status, notes)
                VALUES ($1, $2, $3, $4)
            ''', invoice_id, old_status, new_status, notes)
    
    async def get_automation_statistics(self) -> Dict[str, Any]:
        """Get automation statistics"""
        async with self.db_pool.acquire() as conn:
            # Rule statistics
            rule_stats = await conn.fetchrow('''
                SELECT 
                    COUNT(*) as total_rules,
                    COUNT(*) FILTER (WHERE is_active = TRUE) as active_rules
                FROM invoice_automation_rules
            ''')
            
            # Generation statistics (last 30 days)
            generation_stats = await conn.fetchrow('''
                SELECT 
                    COUNT(*) as total_generated,
                    COUNT(*) FILTER (WHERE status = 'success') as successful,
                    COUNT(*) FILTER (WHERE status = 'error') as failed,
                    AVG(execution_time_ms) as avg_execution_time
                FROM automated_invoice_log 
                WHERE created_at >= NOW() - INTERVAL '30 days'
            ''')
            
            # Reminder statistics (last 30 days)
            reminder_stats = await conn.fetchrow('''
                SELECT 
                    COUNT(*) as total_reminders,
                    COUNT(*) FILTER (WHERE sent = TRUE) as sent_reminders
                FROM invoice_reminders 
                WHERE created_at >= NOW() - INTERVAL '30 days'
            ''')
            
            return {
                'rules': dict(rule_stats),
                'generation': dict(generation_stats),
                'reminders': dict(reminder_stats)
            }

def main():
    """Example usage"""
    async def run_automation():
        config_path = "invoice_automation_config.yml"
        invoice_generator = InvoiceGenerator("invoice_config.yml")
        
        automation = InvoiceAutomationService(config_path, invoice_generator)
        
        try:
            await automation.initialize()
            
            # Create a sample recurring invoice rule
            rule_data = {
                "name": "Monthly Subscription - Acme Corp",
                "customer_id": 1,
                "template_data": {
                    "company_name": "ActiveLog Solutions",
                    "items": [
                        {
                            "description": "Monthly Subscription",
                            "quantity": 1,
                            "unit_price": 299.00,
                            "tax_rate": 8.5
                        }
                    ]
                },
                "recurrence_type": "monthly",
                "start_date": "2024-01-15T00:00:00",
                "next_invoice_date": "2024-02-15T00:00:00",
                "auto_send_email": True,
                "reminder_days": [7, 3, 1]
            }
            
            rule_id = await automation.create_invoice_rule(rule_data)
            print(f"Created rule: {rule_id}")
            
            # Get statistics
            stats = await automation.get_automation_statistics()
            print(f"Automation statistics: {stats}")
            
        finally:
            await automation.shutdown()
    
    asyncio.run(run_automation())

if __name__ == '__main__':
    main()