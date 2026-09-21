#!/usr/bin/env python3

"""
NDA (Non-Disclosure Agreement) Management System for ActiveLog Beta
Handles NDA signing, tracking, and compliance
"""

import os
import json
import argparse
import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import psycopg2
from psycopg2.extras import RealDictCursor
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

@dataclass
class NDADocument:
    id: str
    version: str
    title: str
    content: str
    effective_date: str
    expiry_date: str = None
    is_active: bool = True
    created_at: str = None

@dataclass
class NDAAgreement:
    id: str
    user_id: str
    nda_version: str
    agreed_at: str
    ip_address: str
    user_agent: str
    digital_signature: str
    witness_signature: str = None
    document_hash: str = None
    is_valid: bool = True

class NDAManager:
    def __init__(self, environment: str = "beta", config_path: str = None):
        self.environment = environment
        self.data_dir = Path(f"/app/data/nda/{environment}")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.data_dir / "nda-manager.log"),
                logging.StreamHandler()
            ]
        )
        
        self.config = self._load_config(config_path)
        self._init_database()
        self._ensure_current_nda()

    def _load_config(self, config_path: str = None) -> Dict:
        """Load NDA management configuration"""
        default_config = {
            "company_name": "ActiveLog Inc.",
            "company_address": "123 Tech Street, Silicon Valley, CA 94000",
            "legal_contact": "legal@activelog.com",
            "nda_validity_days": 365,
            "reminder_days_before_expiry": 30,
            "require_witness": False,
            "allow_digital_signature": True,
            "email_notifications": True,
            "compliance_tracking": True
        }
        
        if config_path and Path(config_path).exists():
            with open(config_path) as f:
                user_config = json.load(f)
            default_config.update(user_config)
        
        return default_config

    def _get_db_connection(self):
        """Get database connection"""
        db_config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", 5432)),
            "database": os.getenv("DB_NAME", f"activelog_{self.environment}"),
            "user": os.getenv("DB_USER", "activelog_user"),
            "password": os.getenv("DB_PASSWORD", ""),
        }
        
        return psycopg2.connect(**db_config)

    def _init_database(self):
        """Initialize NDA management tables"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            # NDA documents table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS nda_documents (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    version VARCHAR(20) NOT NULL UNIQUE,
                    title VARCHAR(500) NOT NULL,
                    content TEXT NOT NULL,
                    content_hash VARCHAR(64) NOT NULL,
                    effective_date TIMESTAMP NOT NULL,
                    expiry_date TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by UUID REFERENCES users(id),
                    metadata JSONB
                )
            ''')
            
            # Extend existing nda_agreements table
            cursor.execute('''
                ALTER TABLE nda_agreements 
                ADD COLUMN IF NOT EXISTS digital_signature TEXT,
                ADD COLUMN IF NOT EXISTS witness_signature TEXT,
                ADD COLUMN IF NOT EXISTS document_hash VARCHAR(64),
                ADD COLUMN IF NOT EXISTS is_valid BOOLEAN DEFAULT TRUE,
                ADD COLUMN IF NOT EXISTS expiry_date TIMESTAMP,
                ADD COLUMN IF NOT EXISTS reminder_sent BOOLEAN DEFAULT FALSE
            ''')
            
            # NDA reminders table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS nda_reminders (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    agreement_id UUID REFERENCES nda_agreements(id) NOT NULL,
                    reminder_type VARCHAR(50) NOT NULL,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    next_reminder TIMESTAMP
                )
            ''')
            
            # NDA access log
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS nda_access_log (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    user_id UUID REFERENCES users(id) NOT NULL,
                    action VARCHAR(100) NOT NULL,
                    nda_version VARCHAR(20),
                    ip_address INET,
                    user_agent TEXT,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Failed to initialize NDA tables: {e}")
        finally:
            cursor.close()
            conn.close()

    def _ensure_current_nda(self):
        """Ensure there's a current NDA document"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT COUNT(*) FROM nda_documents WHERE is_active = TRUE")
            active_count = cursor.fetchone()[0]
            
            if active_count == 0:
                # Create default NDA
                self._create_default_nda(cursor)
                conn.commit()
                self.logger.info("Created default NDA document")
                
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Failed to ensure current NDA: {e}")
        finally:
            cursor.close()
            conn.close()

    def _create_default_nda(self, cursor):
        """Create default NDA document"""
        default_nda_content = f"""
NON-DISCLOSURE AGREEMENT

This Non-Disclosure Agreement ("Agreement") is entered into on [DATE] between {self.config['company_name']} ("Company") and the undersigned user ("Recipient").

1. CONFIDENTIAL INFORMATION
The Company will disclose certain confidential and proprietary information relating to ActiveLog Beta software, features, designs, algorithms, business plans, and related materials ("Confidential Information").

2. OBLIGATIONS OF RECIPIENT
Recipient agrees to:
a) Hold all Confidential Information in strict confidence
b) Not disclose Confidential Information to any third parties
c) Use Confidential Information solely for evaluating the ActiveLog Beta software
d) Not reverse engineer, decompile, or attempt to derive the source code
e) Provide feedback and report bugs through designated channels only

3. EXCEPTIONS
This Agreement does not apply to information that:
a) Was known to Recipient before disclosure
b) Becomes publicly available through no breach of this Agreement
c) Is independently developed without use of Confidential Information

4. TERM
This Agreement shall remain in effect for 12 months from the date of signing or until the beta program ends, whichever is earlier.

5. RETURN OF INFORMATION
Upon termination, Recipient shall return or destroy all Confidential Information and certify such return or destruction in writing.

6. REMEDIES
Recipient acknowledges that breach of this Agreement would cause irreparable harm, and Company shall be entitled to injunctive relief and other remedies.

7. GOVERNING LAW
This Agreement shall be governed by the laws of California.

8. BETA PROGRAM SPECIFIC TERMS
a) Beta software is provided "as is" without warranty
b) Recipient understands the software may contain bugs
c) Company reserves the right to terminate beta access at any time
d) Feedback provided becomes property of the Company

By signing below, the parties agree to be bound by this Agreement.

Company: {self.config['company_name']}
Address: {self.config['company_address']}
Contact: {self.config['legal_contact']}

Recipient Signature: ________________________
Name: ________________________
Email: ________________________
Date: ________________________
        """
        
        version = "1.0"
        content_hash = hashlib.sha256(default_nda_content.encode()).hexdigest()
        
        cursor.execute('''
            INSERT INTO nda_documents 
            (version, title, content, content_hash, effective_date)
            VALUES (%s, %s, %s, %s, %s)
        ''', (
            version,
            f"ActiveLog Beta NDA v{version}",
            default_nda_content,
            content_hash,
            datetime.now()
        ))

    def create_nda_document(self, version: str, title: str, content: str, 
                           effective_date: datetime = None, expiry_date: datetime = None,
                           created_by: str = None) -> str:
        """Create new NDA document version"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Deactivate previous versions
            cursor.execute("UPDATE nda_documents SET is_active = FALSE")
            
            # Create new document
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            effective_date = effective_date or datetime.now()
            
            cursor.execute('''
                INSERT INTO nda_documents 
                (version, title, content, content_hash, effective_date, expiry_date, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (version, title, content, content_hash, effective_date, expiry_date, created_by))
            
            document_id = cursor.fetchone()[0]
            conn.commit()
            
            self.logger.info(f"Created NDA document v{version}: {document_id}")
            return str(document_id)
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Failed to create NDA document: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def get_current_nda(self) -> Optional[NDADocument]:
        """Get current active NDA document"""
        conn = self._get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute('''
                SELECT * FROM nda_documents 
                WHERE is_active = TRUE AND effective_date <= %s
                ORDER BY effective_date DESC LIMIT 1
            ''', (datetime.now(),))
            
            row = cursor.fetchone()
            if row:
                return NDADocument(
                    id=str(row["id"]),
                    version=row["version"],
                    title=row["title"],
                    content=row["content"],
                    effective_date=row["effective_date"].isoformat(),
                    expiry_date=row["expiry_date"].isoformat() if row["expiry_date"] else None,
                    is_active=row["is_active"],
                    created_at=row["created_at"].isoformat()
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get current NDA: {e}")
            return None
        finally:
            cursor.close()
            conn.close()

    def sign_nda(self, user_id: str, ip_address: str, user_agent: str,
                digital_signature: str = None, witness_signature: str = None) -> str:
        """Process NDA signing"""
        current_nda = self.get_current_nda()
        if not current_nda:
            raise ValueError("No active NDA document found")
        
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Check if user already signed current version
            cursor.execute('''
                SELECT id FROM nda_agreements 
                WHERE user_id = %s AND version = %s AND is_valid = TRUE
            ''', (user_id, current_nda.version))
            
            if cursor.fetchone():
                raise ValueError("User has already signed the current NDA version")
            
            # Generate digital signature if not provided
            if not digital_signature:
                digital_signature = self._generate_digital_signature(user_id, current_nda.version)
            
            # Calculate expiry date
            expiry_date = datetime.now() + timedelta(days=self.config["nda_validity_days"])
            
            # Create agreement record
            cursor.execute('''
                INSERT INTO nda_agreements 
                (user_id, version, agreed_at, ip_address, user_agent, 
                 digital_signature, witness_signature, document_hash, expiry_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                user_id, current_nda.version, datetime.now(), ip_address, user_agent,
                digital_signature, witness_signature, 
                hashlib.sha256(current_nda.content.encode()).hexdigest(),
                expiry_date
            ))
            
            agreement_id = cursor.fetchone()[0]
            
            # Log the signing
            self._log_nda_access(cursor, user_id, "nda_signed", current_nda.version, 
                                ip_address, user_agent, {
                                    "agreement_id": str(agreement_id),
                                    "expiry_date": expiry_date.isoformat()
                                })
            
            conn.commit()
            
            self.logger.info(f"NDA signed by user {user_id}: v{current_nda.version}")
            
            # Send confirmation email
            if self.config["email_notifications"]:
                self._send_nda_confirmation_email(user_id, current_nda.version, expiry_date)
            
            return str(agreement_id)
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Failed to sign NDA: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def _generate_digital_signature(self, user_id: str, nda_version: str) -> str:
        """Generate digital signature for NDA agreement"""
        timestamp = datetime.now().isoformat()
        signature_data = f"{user_id}:{nda_version}:{timestamp}:{secrets.token_hex(8)}"
        return hashlib.sha256(signature_data.encode()).hexdigest()

    def check_nda_status(self, user_id: str) -> Dict:
        """Check user's NDA signing status"""
        conn = self._get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            current_nda = self.get_current_nda()
            if not current_nda:
                return {"status": "no_active_nda"}
            
            # Check if user has signed current version
            cursor.execute('''
                SELECT * FROM nda_agreements 
                WHERE user_id = %s AND version = %s AND is_valid = TRUE
                ORDER BY agreed_at DESC LIMIT 1
            ''', (user_id, current_nda.version))
            
            agreement = cursor.fetchone()
            
            if not agreement:
                return {
                    "status": "not_signed",
                    "current_nda_version": current_nda.version,
                    "required": True
                }
            
            # Check if expired
            if agreement["expiry_date"] and datetime.now() > agreement["expiry_date"]:
                return {
                    "status": "expired",
                    "signed_version": agreement["version"],
                    "expiry_date": agreement["expiry_date"].isoformat(),
                    "required": True
                }
            
            # Calculate days until expiry
            days_until_expiry = None
            if agreement["expiry_date"]:
                days_until_expiry = (agreement["expiry_date"] - datetime.now()).days
            
            return {
                "status": "signed",
                "signed_version": agreement["version"],
                "agreed_at": agreement["agreed_at"].isoformat(),
                "expiry_date": agreement["expiry_date"].isoformat() if agreement["expiry_date"] else None,
                "days_until_expiry": days_until_expiry,
                "required": False
            }
            
        except Exception as e:
            self.logger.error(f"Failed to check NDA status: {e}")
            return {"status": "error", "error": str(e)}
        finally:
            cursor.close()
            conn.close()

    def get_nda_compliance_report(self, start_date: datetime = None, 
                                 end_date: datetime = None) -> Dict:
        """Generate NDA compliance report"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            if not start_date:
                start_date = datetime.now() - timedelta(days=30)
            if not end_date:
                end_date = datetime.now()
            
            report = {
                "report_period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "statistics": {},
                "compliance_issues": []
            }
            
            # Total beta users
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_beta_user = TRUE")
            total_beta_users = cursor.fetchone()[0]
            
            # Users with valid NDA
            cursor.execute('''
                SELECT COUNT(DISTINCT user_id) FROM nda_agreements 
                WHERE is_valid = TRUE AND (expiry_date IS NULL OR expiry_date > %s)
            ''', (datetime.now(),))
            users_with_valid_nda = cursor.fetchone()[0]
            
            # Users with expired NDA
            cursor.execute('''
                SELECT COUNT(DISTINCT user_id) FROM nda_agreements 
                WHERE is_valid = TRUE AND expiry_date <= %s
            ''', (datetime.now(),))
            users_with_expired_nda = cursor.fetchone()[0]
            
            # Users without NDA
            users_without_nda = total_beta_users - users_with_valid_nda - users_with_expired_nda
            
            report["statistics"] = {
                "total_beta_users": total_beta_users,
                "users_with_valid_nda": users_with_valid_nda,
                "users_with_expired_nda": users_with_expired_nda,
                "users_without_nda": users_without_nda,
                "compliance_rate": round((users_with_valid_nda / total_beta_users * 100), 2) if total_beta_users > 0 else 0
            }
            
            # Find compliance issues
            cursor.execute('''
                SELECT u.id, u.email, u.created_at
                FROM users u
                LEFT JOIN nda_agreements na ON u.id = na.user_id AND na.is_valid = TRUE
                WHERE u.is_beta_user = TRUE 
                AND (na.id IS NULL OR na.expiry_date <= %s)
                ORDER BY u.created_at
            ''', (datetime.now(),))
            
            for row in cursor.fetchall():
                report["compliance_issues"].append({
                    "user_id": str(row[0]),
                    "email": row[1],
                    "issue": "Missing or expired NDA",
                    "user_created": row[2].isoformat()
                })
            
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to generate compliance report: {e}")
            return {"error": str(e)}
        finally:
            cursor.close()
            conn.close()

    def send_nda_reminders(self) -> int:
        """Send NDA expiry reminders"""
        conn = self._get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Find agreements expiring soon
            reminder_date = datetime.now() + timedelta(days=self.config["reminder_days_before_expiry"])
            
            cursor.execute('''
                SELECT na.*, u.email, u.first_name
                FROM nda_agreements na
                JOIN users u ON na.user_id = u.id
                WHERE na.is_valid = TRUE 
                AND na.expiry_date <= %s 
                AND na.expiry_date > %s
                AND na.reminder_sent = FALSE
            ''', (reminder_date, datetime.now()))
            
            reminders_sent = 0
            
            for agreement in cursor.fetchall():
                try:
                    self._send_nda_reminder_email(
                        agreement["user_id"],
                        agreement["email"],
                        agreement["first_name"] or "User",
                        agreement["expiry_date"]
                    )
                    
                    # Mark reminder as sent
                    cursor.execute('''
                        UPDATE nda_agreements 
                        SET reminder_sent = TRUE 
                        WHERE id = %s
                    ''', (agreement["id"],))
                    
                    # Log reminder
                    cursor.execute('''
                        INSERT INTO nda_reminders (agreement_id, reminder_type)
                        VALUES (%s, 'expiry_warning')
                    ''', (agreement["id"],))
                    
                    reminders_sent += 1
                    
                except Exception as e:
                    self.logger.error(f"Failed to send reminder to {agreement['email']}: {e}")
            
            conn.commit()
            self.logger.info(f"Sent {reminders_sent} NDA expiry reminders")
            return reminders_sent
            
        except Exception as e:
            self.logger.error(f"Failed to send NDA reminders: {e}")
            return 0
        finally:
            cursor.close()
            conn.close()

    def _log_nda_access(self, cursor, user_id: str, action: str, nda_version: str,
                       ip_address: str, user_agent: str, metadata: Dict = None):
        """Log NDA access event"""
        if self.config.get("compliance_tracking", True):
            cursor.execute('''
                INSERT INTO nda_access_log 
                (user_id, action, nda_version, ip_address, user_agent, metadata)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (user_id, action, nda_version, ip_address, user_agent, 
                  json.dumps(metadata) if metadata else None))

    def _send_nda_confirmation_email(self, user_id: str, nda_version: str, expiry_date: datetime):
        """Send NDA signing confirmation email"""
        # Implementation depends on your email system
        self.logger.info(f"NDA confirmation email would be sent for user {user_id}, version {nda_version}")

    def _send_nda_reminder_email(self, user_id: str, email: str, name: str, expiry_date: datetime):
        """Send NDA expiry reminder email"""
        # Implementation depends on your email system
        days_until_expiry = (expiry_date - datetime.now()).days
        self.logger.info(f"NDA reminder email would be sent to {email}: expires in {days_until_expiry} days")

    def invalidate_nda(self, user_id: str, reason: str = "Manual invalidation") -> bool:
        """Invalidate user's NDA agreement"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE nda_agreements 
                SET is_valid = FALSE 
                WHERE user_id = %s AND is_valid = TRUE
            ''', (user_id,))
            
            if cursor.rowcount > 0:
                # Log invalidation
                self._log_nda_access(cursor, user_id, "nda_invalidated", "", "", "", {
                    "reason": reason,
                    "invalidated_at": datetime.now().isoformat()
                })
                
                conn.commit()
                self.logger.info(f"Invalidated NDA for user {user_id}: {reason}")
                return True
            
            return False
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Failed to invalidate NDA: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

def main():
    parser = argparse.ArgumentParser(description='NDA Manager')
    parser.add_argument('--environment', default='beta', help='Environment')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Check user NDA status')
    status_parser.add_argument('--user-id', required=True, help='User ID')
    
    # Sign command
    sign_parser = subparsers.add_parser('sign', help='Sign NDA for user')
    sign_parser.add_argument('--user-id', required=True, help='User ID')
    sign_parser.add_argument('--ip-address', default='127.0.0.1', help='IP address')
    sign_parser.add_argument('--user-agent', default='CLI', help='User agent')
    
    # Report command
    report_parser = subparsers.add_parser('report', help='Generate compliance report')
    report_parser.add_argument('--days', type=int, default=30, help='Report period in days')
    
    # Reminders command
    reminders_parser = subparsers.add_parser('reminders', help='Send expiry reminders')
    
    # Current NDA command
    current_parser = subparsers.add_parser('current', help='Show current NDA document')
    
    args = parser.parse_args()
    
    manager = NDAManager(args.environment)
    
    if args.command == 'status':
        status = manager.check_nda_status(args.user_id)
        print(json.dumps(status, indent=2))
    
    elif args.command == 'sign':
        try:
            agreement_id = manager.sign_nda(args.user_id, args.ip_address, args.user_agent)
            print(f"NDA signed successfully: {agreement_id}")
        except Exception as e:
            print(f"Failed to sign NDA: {e}")
    
    elif args.command == 'report':
        start_date = datetime.now() - timedelta(days=args.days)
        report = manager.get_nda_compliance_report(start_date)
        print(json.dumps(report, indent=2, default=str))
    
    elif args.command == 'reminders':
        count = manager.send_nda_reminders()
        print(f"Sent {count} reminder emails")
    
    elif args.command == 'current':
        nda = manager.get_current_nda()
        if nda:
            print(f"Current NDA: v{nda.version} - {nda.title}")
            print(f"Effective: {nda.effective_date}")
            print(f"Content preview: {nda.content[:200]}...")
        else:
            print("No current NDA document found")
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main()