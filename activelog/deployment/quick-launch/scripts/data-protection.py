#!/usr/bin/env python3

"""
Data Protection Manager for ActiveLog Beta
Implements GDPR compliance, data encryption, and user privacy controls
"""

import os
import json
import hashlib
import secrets
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import psycopg2
from psycopg2.extras import RealDictCursor
import base64

@dataclass
class DataProtectionConfig:
    environment: str
    encryption_enabled: bool = True
    data_retention_days: int = 90
    anonymization_enabled: bool = True
    audit_enabled: bool = True
    backup_encryption: bool = True
    gdpr_compliance: bool = True

@dataclass
class UserDataRequest:
    user_id: str
    request_type: str  # export, delete, anonymize
    status: str = "pending"
    created_at: str = None
    completed_at: str = None
    file_path: str = None

class DataProtectionManager:
    def __init__(self, environment: str = "beta", config_path: str = None):
        self.environment = environment
        self.config = self._load_config(config_path)
        self.data_dir = Path(f"/app/data/privacy/{environment}")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.data_dir / "privacy.log"),
                logging.StreamHandler()
            ]
        )
        
        self.encryption_key = self._get_encryption_key()
        self.cipher = Fernet(self.encryption_key) if self.encryption_key else None
        
        self._init_database()

    def _load_config(self, config_path: str = None) -> DataProtectionConfig:
        """Load data protection configuration"""
        if config_path and Path(config_path).exists():
            with open(config_path) as f:
                data = json.load(f)
            return DataProtectionConfig(**data)
        
        # Default config for beta environment
        return DataProtectionConfig(
            environment=self.environment,
            encryption_enabled=True,
            data_retention_days=90,  # Shorter retention for beta
            anonymization_enabled=True,
            audit_enabled=True,
            backup_encryption=True,
            gdpr_compliance=True
        )

    def _get_encryption_key(self) -> bytes:
        """Get or generate encryption key"""
        key_file = Path(f"/run/secrets/data_protection_key_{self.environment}")
        
        if key_file.exists():
            return key_file.read_bytes()
        
        # Generate new key for development/testing
        if self.environment in ['beta', 'development', 'test']:
            key = Fernet.generate_key()
            # Store in data directory for persistence
            key_path = self.data_dir / "encryption.key"
            key_path.write_bytes(key)
            key_path.chmod(0o600)  # Restrict permissions
            self.logger.warning(f"Generated new encryption key at {key_path}")
            return key
        
        raise ValueError("Encryption key not found in production environment")

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
        """Initialize privacy tracking tables"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Data requests table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS data_requests (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    user_id UUID NOT NULL,
                    request_type VARCHAR(50) NOT NULL,
                    status VARCHAR(50) DEFAULT 'pending',
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    file_path VARCHAR(500),
                    expiry_date TIMESTAMP
                )
            ''')
            
            # Data retention policy
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS data_retention_policy (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    table_name VARCHAR(100) NOT NULL,
                    retention_days INTEGER NOT NULL,
                    anonymization_fields TEXT[],
                    deletion_cascade BOOLEAN DEFAULT false,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Data anonymization log
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS anonymization_log (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    table_name VARCHAR(100) NOT NULL,
                    record_id VARCHAR(255) NOT NULL,
                    fields_anonymized TEXT[],
                    anonymized_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    anonymization_method VARCHAR(100)
                )
            ''')
            
            # Consent tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_consent (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    user_id UUID NOT NULL,
                    consent_type VARCHAR(100) NOT NULL,
                    granted BOOLEAN NOT NULL,
                    version VARCHAR(10) NOT NULL,
                    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    withdrawn_at TIMESTAMP,
                    ip_address INET,
                    user_agent TEXT
                )
            ''')
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Failed to initialize privacy tables: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        if not self.cipher or not self.config.encryption_enabled:
            return data
        
        return base64.b64encode(self.cipher.encrypt(data.encode())).decode()

    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        if not self.cipher or not self.config.encryption_enabled:
            return encrypted_data
        
        try:
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            return self.cipher.decrypt(encrypted_bytes).decode()
        except Exception as e:
            self.logger.error(f"Decryption failed: {e}")
            return encrypted_data

    def anonymize_email(self, email: str) -> str:
        """Anonymize email address"""
        if not email or '@' not in email:
            return email
        
        local, domain = email.split('@', 1)
        # Keep first character, hash the rest
        if len(local) > 1:
            hashed = hashlib.sha256(local[1:].encode()).hexdigest()[:8]
            return f"{local[0]}***{hashed}@{domain}"
        return f"*@{domain}"

    def anonymize_name(self, name: str) -> str:
        """Anonymize personal name"""
        if not name:
            return name
        
        words = name.strip().split()
        if len(words) == 1:
            return f"{words[0][0]}***"
        else:
            return f"{words[0][0]}*** {words[-1][0]}***"

    def anonymize_ip_address(self, ip_address: str) -> str:
        """Anonymize IP address"""
        if not ip_address:
            return ip_address
        
        if ':' in ip_address:  # IPv6
            parts = ip_address.split(':')
            return ':'.join(parts[:4] + ['0000'] * (len(parts) - 4))
        else:  # IPv4
            parts = ip_address.split('.')
            return '.'.join(parts[:2] + ['0', '0'])

    def create_data_request(self, user_id: str, request_type: str, 
                           metadata: Dict = None) -> str:
        """Create a new data request"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Set expiry date (30 days from now)
            expiry_date = datetime.now() + timedelta(days=30)
            
            cursor.execute('''
                INSERT INTO data_requests 
                (user_id, request_type, metadata, expiry_date)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            ''', (user_id, request_type, json.dumps(metadata or {}), expiry_date))
            
            request_id = cursor.fetchone()[0]
            conn.commit()
            
            self.logger.info(f"Created data request {request_id} for user {user_id}: {request_type}")
            
            # Log audit event
            self._log_audit_event(user_id, "data_request_created", {
                "request_id": str(request_id),
                "request_type": request_type
            })
            
            return str(request_id)
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Failed to create data request: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def export_user_data(self, user_id: str, request_id: str = None) -> str:
        """Export all user data in GDPR-compliant format"""
        self.logger.info(f"Starting data export for user {user_id}")
        
        conn = self._get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            export_data = {
                "user_id": user_id,
                "export_date": datetime.now().isoformat(),
                "environment": self.environment,
                "data": {}
            }
            
            # Export user profile
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user_data = cursor.fetchone()
            if user_data:
                # Remove sensitive fields
                user_dict = dict(user_data)
                user_dict.pop('password_hash', None)
                export_data["data"]["profile"] = user_dict
            
            # Export user sessions
            cursor.execute("SELECT * FROM user_sessions WHERE user_id = %s", (user_id,))
            export_data["data"]["sessions"] = [dict(row) for row in cursor.fetchall()]
            
            # Export feedback
            cursor.execute("SELECT * FROM feedback WHERE user_id = %s", (user_id,))
            export_data["data"]["feedback"] = [dict(row) for row in cursor.fetchall()]
            
            # Export consent records
            cursor.execute("SELECT * FROM user_consent WHERE user_id = %s", (user_id,))
            export_data["data"]["consent"] = [dict(row) for row in cursor.fetchall()]
            
            # Export feature flags
            cursor.execute("SELECT * FROM user_feature_flags WHERE user_id = %s", (user_id,))
            export_data["data"]["feature_flags"] = [dict(row) for row in cursor.fetchall()]
            
            # Export files metadata (not the actual files for security)
            cursor.execute("SELECT id, filename, mime_type, size_bytes, created_at FROM files WHERE user_id = %s", (user_id,))
            export_data["data"]["files"] = [dict(row) for row in cursor.fetchall()]
            
            # Export audit log entries
            cursor.execute("SELECT * FROM audit_log WHERE user_id = %s ORDER BY created_at DESC LIMIT 1000", (user_id,))
            export_data["data"]["audit_log"] = [dict(row) for row in cursor.fetchall()]
            
            # Save export to file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            export_filename = f"user_data_export_{user_id}_{timestamp}.json"
            export_path = self.data_dir / "exports" / export_filename
            export_path.parent.mkdir(exist_ok=True)
            
            with open(export_path, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            # Encrypt the export file if enabled
            if self.config.encryption_enabled and self.cipher:
                with open(export_path, 'rb') as f:
                    encrypted_data = self.cipher.encrypt(f.read())
                
                encrypted_path = export_path.with_suffix('.json.encrypted')
                with open(encrypted_path, 'wb') as f:
                    f.write(encrypted_data)
                
                # Remove unencrypted file
                export_path.unlink()
                export_path = encrypted_path
            
            # Update request status if provided
            if request_id:
                cursor.execute('''
                    UPDATE data_requests 
                    SET status = 'completed', completed_at = %s, file_path = %s
                    WHERE id = %s
                ''', (datetime.now(), str(export_path), request_id))
                conn.commit()
            
            self.logger.info(f"Data export completed: {export_path}")
            
            # Log audit event
            self._log_audit_event(user_id, "data_exported", {
                "export_file": str(export_path),
                "request_id": request_id
            })
            
            return str(export_path)
            
        except Exception as e:
            self.logger.error(f"Data export failed: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def anonymize_user_data(self, user_id: str, request_id: str = None) -> bool:
        """Anonymize user data while preserving analytics value"""
        self.logger.info(f"Starting data anonymization for user {user_id}")
        
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Get user data before anonymization
            cursor.execute("SELECT email, first_name, last_name FROM users WHERE id = %s", (user_id,))
            user_data = cursor.fetchone()
            
            if not user_data:
                self.logger.error(f"User {user_id} not found")
                return False
            
            # Anonymize user profile
            anonymized_email = self.anonymize_email(user_data[0])
            anonymized_first_name = self.anonymize_name(user_data[1] or "")
            anonymized_last_name = self.anonymize_name(user_data[2] or "")
            
            cursor.execute('''
                UPDATE users 
                SET email = %s, first_name = %s, last_name = %s, 
                    username = %s
                WHERE id = %s
            ''', (
                anonymized_email,
                anonymized_first_name,
                anonymized_last_name,
                f"anonymous_{user_id[:8]}",
                user_id
            ))
            
            # Anonymize IP addresses in sessions
            cursor.execute('''
                UPDATE user_sessions 
                SET ip_address = inet %s
                WHERE user_id = %s AND ip_address IS NOT NULL
            ''', (self.anonymize_ip_address("192.168.1.1"), user_id))
            
            # Anonymize IP addresses in audit log
            cursor.execute('''
                UPDATE audit_log 
                SET ip_address = inet %s
                WHERE user_id = %s AND ip_address IS NOT NULL
            ''', (self.anonymize_ip_address("192.168.1.1"), user_id))
            
            # Log anonymization
            cursor.execute('''
                INSERT INTO anonymization_log 
                (table_name, record_id, fields_anonymized, anonymization_method)
                VALUES 
                ('users', %s, %s, 'hash_truncate'),
                ('user_sessions', %s, %s, 'ip_masking'),
                ('audit_log', %s, %s, 'ip_masking')
            ''', (
                user_id, ['email', 'first_name', 'last_name', 'username'],
                user_id, ['ip_address'],
                user_id, ['ip_address']
            ))
            
            # Update request status if provided
            if request_id:
                cursor.execute('''
                    UPDATE data_requests 
                    SET status = 'completed', completed_at = %s
                    WHERE id = %s
                ''', (datetime.now(), request_id))
            
            conn.commit()
            
            self.logger.info(f"Data anonymization completed for user {user_id}")
            
            # Log audit event
            self._log_audit_event(user_id, "data_anonymized", {
                "request_id": request_id,
                "tables_affected": ["users", "user_sessions", "audit_log"]
            })
            
            return True
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Data anonymization failed: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def delete_user_data(self, user_id: str, request_id: str = None) -> bool:
        """Delete all user data (GDPR Right to be Forgotten)"""
        self.logger.info(f"Starting data deletion for user {user_id}")
        
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Delete in dependency order
            tables_to_delete = [
                'user_feature_flags',
                'user_sessions',
                'feedback_responses',
                'feedback',
                'beta_metrics',
                'files',
                'nda_agreements',
                'user_consent',
                'data_requests',
                'audit_log'
            ]
            
            deleted_counts = {}
            
            for table in tables_to_delete:
                cursor.execute(f"DELETE FROM {table} WHERE user_id = %s", (user_id,))
                deleted_counts[table] = cursor.rowcount
                self.logger.debug(f"Deleted {cursor.rowcount} records from {table}")
            
            # Finally delete user record
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            deleted_counts['users'] = cursor.rowcount
            
            # Update request status if provided
            if request_id:
                cursor.execute('''
                    UPDATE data_requests 
                    SET status = 'completed', completed_at = %s, 
                        metadata = metadata || %s
                    WHERE id = %s
                ''', (
                    datetime.now(),
                    json.dumps({"deleted_counts": deleted_counts}),
                    request_id
                ))
            
            conn.commit()
            
            total_deleted = sum(deleted_counts.values())
            self.logger.info(f"Data deletion completed: {total_deleted} records deleted")
            
            return True
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Data deletion failed: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def cleanup_expired_data(self) -> int:
        """Clean up expired data based on retention policy"""
        self.logger.info("Starting expired data cleanup")
        
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            total_deleted = 0
            
            # Clean up expired sessions
            cutoff_date = datetime.now() - timedelta(days=30)
            cursor.execute("DELETE FROM user_sessions WHERE expires_at < %s", (cutoff_date,))
            session_deleted = cursor.rowcount
            total_deleted += session_deleted
            
            # Clean up old audit logs (keep for retention period)
            audit_cutoff = datetime.now() - timedelta(days=self.config.data_retention_days)
            cursor.execute("DELETE FROM audit_log WHERE created_at < %s", (audit_cutoff,))
            audit_deleted = cursor.rowcount
            total_deleted += audit_deleted
            
            # Clean up old beta metrics
            cursor.execute("DELETE FROM beta_metrics WHERE created_at < %s", (audit_cutoff,))
            metrics_deleted = cursor.rowcount
            total_deleted += metrics_deleted
            
            # Clean up expired data requests
            cursor.execute("DELETE FROM data_requests WHERE expiry_date < %s", (datetime.now(),))
            requests_deleted = cursor.rowcount
            total_deleted += requests_deleted
            
            conn.commit()
            
            self.logger.info(f"Cleanup completed: {total_deleted} records deleted")
            self.logger.debug(f"Sessions: {session_deleted}, Audit: {audit_deleted}, "
                            f"Metrics: {metrics_deleted}, Requests: {requests_deleted}")
            
            return total_deleted
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Data cleanup failed: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def _log_audit_event(self, user_id: str, action: str, metadata: Dict):
        """Log privacy-related audit event"""
        if not self.config.audit_enabled:
            return
        
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO audit_log (user_id, action, metadata)
                VALUES (%s, %s, %s)
            ''', (user_id, action, json.dumps(metadata)))
            
            conn.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to log audit event: {e}")
        finally:
            cursor.close()
            conn.close()

    def get_privacy_dashboard(self, user_id: str) -> Dict:
        """Get privacy dashboard data for user"""
        conn = self._get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            dashboard = {
                "user_id": user_id,
                "data_requests": [],
                "consent_status": {},
                "data_summary": {}
            }
            
            # Get data requests
            cursor.execute('''
                SELECT * FROM data_requests 
                WHERE user_id = %s 
                ORDER BY created_at DESC LIMIT 10
            ''', (user_id,))
            dashboard["data_requests"] = [dict(row) for row in cursor.fetchall()]
            
            # Get consent status
            cursor.execute('''
                SELECT consent_type, granted, version, granted_at, withdrawn_at
                FROM user_consent 
                WHERE user_id = %s
                ORDER BY granted_at DESC
            ''', (user_id,))
            
            for row in cursor.fetchall():
                dashboard["consent_status"][row["consent_type"]] = {
                    "granted": row["granted"],
                    "version": row["version"],
                    "date": row["granted_at"] if row["granted"] else row["withdrawn_at"]
                }
            
            # Get data summary
            cursor.execute("SELECT COUNT(*) FROM feedback WHERE user_id = %s", (user_id,))
            dashboard["data_summary"]["feedback_count"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM files WHERE user_id = %s", (user_id,))
            dashboard["data_summary"]["files_count"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM user_sessions WHERE user_id = %s", (user_id,))
            dashboard["data_summary"]["sessions_count"] = cursor.fetchone()[0]
            
            return dashboard
            
        except Exception as e:
            self.logger.error(f"Failed to get privacy dashboard: {e}")
            return {"error": str(e)}
        finally:
            cursor.close()
            conn.close()

def main():
    parser = argparse.ArgumentParser(description='Data Protection Manager')
    parser.add_argument('--environment', default='beta', help='Environment')
    parser.add_argument('--action', choices=['export', 'anonymize', 'delete', 'cleanup', 'dashboard'],
                       required=True, help='Action to perform')
    parser.add_argument('--user-id', help='User ID for user-specific actions')
    parser.add_argument('--request-id', help='Data request ID')
    parser.add_argument('--config', help='Configuration file path')
    
    args = parser.parse_args()
    
    manager = DataProtectionManager(args.environment, args.config)
    
    if args.action == 'export':
        if not args.user_id:
            print("User ID required for export")
            return
        
        export_path = manager.export_user_data(args.user_id, args.request_id)
        print(f"Export completed: {export_path}")
    
    elif args.action == 'anonymize':
        if not args.user_id:
            print("User ID required for anonymization")
            return
        
        success = manager.anonymize_user_data(args.user_id, args.request_id)
        print("Anonymization completed" if success else "Anonymization failed")
    
    elif args.action == 'delete':
        if not args.user_id:
            print("User ID required for deletion")
            return
        
        success = manager.delete_user_data(args.user_id, args.request_id)
        print("Deletion completed" if success else "Deletion failed")
    
    elif args.action == 'cleanup':
        deleted_count = manager.cleanup_expired_data()
        print(f"Cleanup completed: {deleted_count} records deleted")
    
    elif args.action == 'dashboard':
        if not args.user_id:
            print("User ID required for dashboard")
            return
        
        dashboard = manager.get_privacy_dashboard(args.user_id)
        print(json.dumps(dashboard, indent=2, default=str))

if __name__ == '__main__':
    main()