#!/usr/bin/env python3
"""
Payment Reminders System
Automated payment reminder notifications for overdue invoices
"""

import json
import sqlite3
import asyncio
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class ReminderType(str, Enum):
    GENTLE = "gentle"
    FIRM = "firm"
    URGENT = "urgent"
    FINAL = "final"

class PaymentReminderSystem:
    """Automated payment reminder system"""
    
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/invoice-engine/data/invoice_engine.db"
        
        # Reminder schedule configuration
        self.reminder_schedule = {
            ReminderType.GENTLE: 7,   # 7 days after due date
            ReminderType.FIRM: 14,    # 14 days after due date
            ReminderType.URGENT: 21,  # 21 days after due date
            ReminderType.FINAL: 30    # 30 days after due date
        }
        
        # Email templates
        self.email_templates = {
            ReminderType.GENTLE: {
                'subject': 'Friendly Payment Reminder - Invoice {invoice_number}',
                'template': 'gentle_reminder.html'
            },
            ReminderType.FIRM: {
                'subject': 'Payment Reminder - Invoice {invoice_number} - {days_overdue} days overdue',
                'template': 'firm_reminder.html'
            },
            ReminderType.URGENT: {
                'subject': 'URGENT: Payment Required - Invoice {invoice_number}',
                'template': 'urgent_reminder.html'
            },
            ReminderType.FINAL: {
                'subject': 'FINAL NOTICE: Invoice {invoice_number} - Account may be suspended',
                'template': 'final_reminder.html'
            }
        }
    
    async def initialize(self):
        """Initialize payment reminder system"""
        try:
            await self._setup_reminder_tables()
            logger.info("Payment reminder system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize payment reminder system: {e}")
            raise
    
    async def _setup_reminder_tables(self):
        """Setup reminder-related tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Payment reminders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payment_reminders (
                id TEXT PRIMARY KEY,
                invoice_id TEXT NOT NULL,
                reminder_type TEXT NOT NULL,
                sent_date DATE NOT NULL,
                days_overdue INTEGER NOT NULL,
                amount_due DECIMAL NOT NULL,
                email_sent BOOLEAN DEFAULT FALSE,
                sms_sent BOOLEAN DEFAULT FALSE,
                email_opened BOOLEAN DEFAULT FALSE,
                email_clicked BOOLEAN DEFAULT FALSE,
                response_received BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT
            )
        ''')
        
        # Reminder settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reminder_settings (
                id TEXT PRIMARY KEY,
                customer_id TEXT,
                reminder_enabled BOOLEAN DEFAULT TRUE,
                email_enabled BOOLEAN DEFAULT TRUE,
                sms_enabled BOOLEAN DEFAULT FALSE,
                custom_schedule TEXT,
                escalation_enabled BOOLEAN DEFAULT TRUE,
                custom_templates TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Reminder templates table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reminder_templates (
                id TEXT PRIMARY KEY,
                template_name TEXT NOT NULL,
                reminder_type TEXT NOT NULL,
                language TEXT DEFAULT 'en',
                subject TEXT NOT NULL,
                html_content TEXT NOT NULL,
                sms_content TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def send_overdue_reminders(self) -> Dict[str, Any]:
        """Process and send all overdue payment reminders"""
        try:
            today = date.today()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get overdue invoices that need reminders
            cursor.execute('''
                SELECT i.id, i.invoice_number, i.customer_id, i.due_date,
                       i.total_amount, i.paid_amount, i.status
                FROM invoices i
                WHERE i.status IN ('sent', 'overdue')
                  AND i.due_date < ?
                  AND (i.total_amount - COALESCE(i.paid_amount, 0)) > 0.01
            ''', (today.isoformat(),))
            
            overdue_invoices = cursor.fetchall()
            sent_reminders = []
            
            for invoice_row in overdue_invoices:
                invoice_id = invoice_row[0]
                invoice_number = invoice_row[1]
                customer_id = invoice_row[2]
                due_date = datetime.strptime(invoice_row[3], '%Y-%m-%d').date()
                total_amount = Decimal(str(invoice_row[4]))
                paid_amount = Decimal(str(invoice_row[5] or 0))
                
                days_overdue = (today - due_date).days
                amount_due = total_amount - paid_amount
                
                # Determine reminder type based on days overdue
                reminder_type = self._get_reminder_type(days_overdue)
                if not reminder_type:
                    continue  # Too early or too late
                
                # Check if this type of reminder was already sent
                cursor.execute('''
                    SELECT id FROM payment_reminders
                    WHERE invoice_id = ? AND reminder_type = ?
                ''', (invoice_id, reminder_type))
                
                if cursor.fetchone():
                    continue  # Already sent
                
                # Check customer settings
                reminder_settings = await self._get_customer_reminder_settings(cursor, customer_id)
                if not reminder_settings.get('reminder_enabled', True):
                    continue
                
                # Send reminder
                reminder_result = await self._send_reminder(
                    cursor, invoice_id, invoice_number, customer_id,
                    reminder_type, days_overdue, amount_due, reminder_settings
                )
                
                if reminder_result['success']:
                    sent_reminders.append({
                        'invoice_id': invoice_id,
                        'invoice_number': invoice_number,
                        'reminder_type': reminder_type,
                        'days_overdue': days_overdue,
                        'amount_due': amount_due
                    })
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'reminders_sent': len(sent_reminders),
                'reminders': sent_reminders,
                'process_date': today.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error sending overdue reminders: {e}")
            return {
                'success': False,
                'error': f"Reminder processing error: {str(e)}"
            }
    
    def _get_reminder_type(self, days_overdue: int) -> Optional[str]:
        """Determine reminder type based on days overdue"""
        if days_overdue >= self.reminder_schedule[ReminderType.FINAL]:
            return ReminderType.FINAL.value
        elif days_overdue >= self.reminder_schedule[ReminderType.URGENT]:
            return ReminderType.URGENT.value
        elif days_overdue >= self.reminder_schedule[ReminderType.FIRM]:
            return ReminderType.FIRM.value
        elif days_overdue >= self.reminder_schedule[ReminderType.GENTLE]:
            return ReminderType.GENTLE.value
        else:
            return None
    
    async def _get_customer_reminder_settings(self, cursor, customer_id: str) -> Dict[str, Any]:
        """Get customer-specific reminder settings"""
        cursor.execute('''
            SELECT reminder_enabled, email_enabled, sms_enabled, custom_schedule,
                   escalation_enabled, custom_templates
            FROM reminder_settings WHERE customer_id = ?
        ''', (customer_id,))
        
        row = cursor.fetchone()
        if row:
            return {
                'reminder_enabled': bool(row[0]),
                'email_enabled': bool(row[1]),
                'sms_enabled': bool(row[2]),
                'custom_schedule': json.loads(row[3]) if row[3] else None,
                'escalation_enabled': bool(row[4]),
                'custom_templates': json.loads(row[5]) if row[5] else None
            }
        else:
            # Default settings
            return {
                'reminder_enabled': True,
                'email_enabled': True,
                'sms_enabled': False,
                'custom_schedule': None,
                'escalation_enabled': True,
                'custom_templates': None
            }
    
    async def _send_reminder(
        self, cursor, invoice_id: str, invoice_number: str, customer_id: str,
        reminder_type: str, days_overdue: int, amount_due: Decimal,
        settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send individual payment reminder"""
        try:
            reminder_id = f"REM_{uuid.uuid4().hex[:8].upper()}"
            
            # Record reminder
            cursor.execute('''
                INSERT INTO payment_reminders (
                    id, invoice_id, reminder_type, sent_date, days_overdue,
                    amount_due, data
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                reminder_id, invoice_id, reminder_type, date.today().isoformat(),
                days_overdue, float(amount_due), json.dumps({
                    'invoice_number': invoice_number,
                    'customer_id': customer_id,
                    'settings_used': settings
                })
            ))
            
            # Send email reminder
            email_sent = False
            if settings.get('email_enabled', True):
                email_result = await self._send_email_reminder(
                    invoice_id, invoice_number, customer_id, reminder_type,
                    days_overdue, amount_due, settings
                )
                email_sent = email_result.get('success', False)
                
                cursor.execute('''
                    UPDATE payment_reminders SET email_sent = ? WHERE id = ?
                ''', (email_sent, reminder_id))
            
            # Send SMS reminder
            sms_sent = False
            if settings.get('sms_enabled', False):
                sms_result = await self._send_sms_reminder(
                    invoice_id, invoice_number, customer_id, reminder_type,
                    days_overdue, amount_due
                )
                sms_sent = sms_result.get('success', False)
                
                cursor.execute('''
                    UPDATE payment_reminders SET sms_sent = ? WHERE id = ?
                ''', (sms_sent, reminder_id))
            
            return {
                'success': True,
                'reminder_id': reminder_id,
                'email_sent': email_sent,
                'sms_sent': sms_sent
            }
            
        except Exception as e:
            logger.error(f"Error sending reminder: {e}")
            return {
                'success': False,
                'error': f"Reminder send error: {str(e)}"
            }
    
    async def _send_email_reminder(
        self, invoice_id: str, invoice_number: str, customer_id: str,
        reminder_type: str, days_overdue: int, amount_due: Decimal,
        settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send email reminder"""
        try:
            # Get email template
            template_info = self.email_templates[ReminderType(reminder_type)]
            
            # Format subject
            subject = template_info['subject'].format(
                invoice_number=invoice_number,
                days_overdue=days_overdue,
                amount_due=amount_due
            )
            
            # Generate email content
            email_content = await self._generate_email_content(
                invoice_id, invoice_number, customer_id, reminder_type,
                days_overdue, amount_due, template_info['template']
            )
            
            # In a real implementation, this would integrate with an email service
            # For now, we'll simulate successful sending
            logger.info(f"Email reminder sent: {subject} to customer {customer_id}")
            
            return {
                'success': True,
                'subject': subject,
                'template': template_info['template']
            }
            
        except Exception as e:
            logger.error(f"Error sending email reminder: {e}")
            return {
                'success': False,
                'error': f"Email send error: {str(e)}"
            }
    
    async def _send_sms_reminder(
        self, invoice_id: str, invoice_number: str, customer_id: str,
        reminder_type: str, days_overdue: int, amount_due: Decimal
    ) -> Dict[str, Any]:
        """Send SMS reminder"""
        try:
            # Generate SMS content
            sms_content = self._generate_sms_content(
                invoice_number, reminder_type, days_overdue, amount_due
            )
            
            # In a real implementation, this would integrate with an SMS service
            logger.info(f"SMS reminder sent to customer {customer_id}: {sms_content}")
            
            return {
                'success': True,
                'content': sms_content
            }
            
        except Exception as e:
            logger.error(f"Error sending SMS reminder: {e}")
            return {
                'success': False,
                'error': f"SMS send error: {str(e)}"
            }
    
    def _generate_sms_content(self, invoice_number: str, reminder_type: str, days_overdue: int, amount_due: Decimal) -> str:
        """Generate SMS reminder content"""
        if reminder_type == ReminderType.GENTLE.value:
            return f"Friendly reminder: Invoice {invoice_number} is {days_overdue} days overdue. Amount due: ${amount_due}. Please pay at your earliest convenience."
        elif reminder_type == ReminderType.FIRM.value:
            return f"Payment reminder: Invoice {invoice_number} is {days_overdue} days overdue. Please pay ${amount_due} immediately to avoid service interruption."
        elif reminder_type == ReminderType.URGENT.value:
            return f"URGENT: Invoice {invoice_number} is {days_overdue} days overdue. Pay ${amount_due} now to prevent collection action."
        else:  # FINAL
            return f"FINAL NOTICE: Invoice {invoice_number} - {days_overdue} days overdue. Pay ${amount_due} within 48 hours or account will be suspended."
    
    async def _generate_email_content(
        self, invoice_id: str, invoice_number: str, customer_id: str,
        reminder_type: str, days_overdue: int, amount_due: Decimal, template_name: str
    ) -> str:
        """Generate HTML email content"""
        # In a real implementation, this would use a template engine
        base_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 20px;">
            <h2>Payment Reminder</h2>
            <p>Dear Valued Customer,</p>
            <p>This is a {reminder_type} reminder that Invoice #{invoice_number} is now {days_overdue} days overdue.</p>
            <p><strong>Amount Due: ${amount_due}</strong></p>
            <p>Please process payment at your earliest convenience to avoid any service interruption.</p>
            <p>If you have already made this payment, please disregard this notice.</p>
            <p>Thank you for your prompt attention to this matter.</p>
            <p>Best regards,<br>Accounts Receivable Team</p>
        </body>
        </html>
        """
        return base_content
    
    async def create_reminder_template(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create custom reminder template"""
        try:
            template_id = f"TMPL_{uuid.uuid4().hex[:8].upper()}"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO reminder_templates (
                    id, template_name, reminder_type, language, subject,
                    html_content, sms_content
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                template_id, template_data['template_name'], template_data['reminder_type'],
                template_data.get('language', 'en'), template_data['subject'],
                template_data['html_content'], template_data.get('sms_content')
            ))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'template_id': template_id,
                'template_name': template_data['template_name']
            }
            
        except Exception as e:
            logger.error(f"Error creating reminder template: {e}")
            return {
                'success': False,
                'error': f"Template creation error: {str(e)}"
            }
    
    async def update_customer_settings(self, customer_id: str, settings_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update customer reminder settings"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if settings exist
            cursor.execute('SELECT id FROM reminder_settings WHERE customer_id = ?', (customer_id,))
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute('''
                    UPDATE reminder_settings 
                    SET reminder_enabled = ?, email_enabled = ?, sms_enabled = ?,
                        escalation_enabled = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE customer_id = ?
                ''', (
                    settings_data.get('reminder_enabled', True),
                    settings_data.get('email_enabled', True),
                    settings_data.get('sms_enabled', False),
                    settings_data.get('escalation_enabled', True),
                    customer_id
                ))
            else:
                settings_id = f"SET_{uuid.uuid4().hex[:8].upper()}"
                cursor.execute('''
                    INSERT INTO reminder_settings (
                        id, customer_id, reminder_enabled, email_enabled,
                        sms_enabled, escalation_enabled
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    settings_id, customer_id,
                    settings_data.get('reminder_enabled', True),
                    settings_data.get('email_enabled', True),
                    settings_data.get('sms_enabled', False),
                    settings_data.get('escalation_enabled', True)
                ))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'customer_id': customer_id,
                'settings_updated': True
            }
            
        except Exception as e:
            logger.error(f"Error updating customer settings: {e}")
            return {
                'success': False,
                'error': f"Settings update error: {str(e)}"
            }
    
    async def list_reminders(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """List payment reminders with filtering"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            base_query = '''
                SELECT pr.id, pr.invoice_id, pr.reminder_type, pr.sent_date,
                       pr.days_overdue, pr.amount_due, pr.email_sent, pr.sms_sent,
                       pr.email_opened, pr.response_received
                FROM payment_reminders pr
                WHERE 1=1
            '''
            
            params = []
            
            if filters:
                if filters.get('invoice_id'):
                    base_query += " AND pr.invoice_id = ?"
                    params.append(filters['invoice_id'])
                
                if filters.get('reminder_type'):
                    base_query += " AND pr.reminder_type = ?"
                    params.append(filters['reminder_type'])
                
                if filters.get('date_from'):
                    base_query += " AND pr.sent_date >= ?"
                    params.append(filters['date_from'])
                
                if filters.get('date_to'):
                    base_query += " AND pr.sent_date <= ?"
                    params.append(filters['date_to'])
            
            base_query += " ORDER BY pr.sent_date DESC"
            
            cursor.execute(base_query, params)
            
            reminders = []
            for row in cursor.fetchall():
                reminders.append({
                    'id': row[0],
                    'invoice_id': row[1],
                    'reminder_type': row[2],
                    'sent_date': row[3],
                    'days_overdue': row[4],
                    'amount_due': Decimal(str(row[5])),
                    'email_sent': bool(row[6]),
                    'sms_sent': bool(row[7]),
                    'email_opened': bool(row[8]),
                    'response_received': bool(row[9])
                })
            
            conn.close()
            
            return {
                'success': True,
                'reminders': reminders,
                'count': len(reminders)
            }
            
        except Exception as e:
            logger.error(f"Error listing reminders: {e}")
            return {
                'success': False,
                'error': f"List error: {str(e)}"
            }

# Global instance
reminder_system = PaymentReminderSystem()