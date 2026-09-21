#!/usr/bin/env python3

"""
Beta User Management System for ActiveLog
Manages beta user lifecycle, permissions, and analytics
"""

import os
import json
import secrets
import string
import argparse
import logging
import smtplib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
import bcrypt

@dataclass
class BetaUser:
    id: str
    email: str
    username: str
    first_name: str
    last_name: str
    status: str
    invited_by: str
    invited_at: str
    activated_at: str = None
    last_login: str = None
    login_count: int = 0
    feedback_count: int = 0
    nda_signed: bool = False
    access_level: str = "standard"  # standard, premium, admin

@dataclass
class BetaInvite:
    id: str
    email: str
    invite_code: str
    invited_by: str
    status: str
    invited_at: str
    expires_at: str
    accepted_at: str = None
    metadata: Dict = None

class BetaUserManager:
    def __init__(self, environment: str = "beta", config_path: str = None):
        self.environment = environment
        self.data_dir = Path(f"/app/data/beta-management/{environment}")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.data_dir / "beta-management.log"),
                logging.StreamHandler()
            ]
        )
        
        self.config = self._load_config(config_path)
        self._init_database()

    def _load_config(self, config_path: str = None) -> Dict:
        """Load beta management configuration"""
        default_config = {
            "max_beta_users": 100,
            "invite_expiry_days": 7,
            "welcome_email_enabled": True,
            "analytics_enabled": True,
            "feedback_required": True,
            "nda_required": True,
            "auto_approve": False,
            "email": {
                "smtp_host": "localhost",
                "smtp_port": 587,
                "username": "",
                "password": "",
                "from_email": f"beta@activelog.dev"
            }
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
        """Initialize beta management tables if needed"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Check if tables exist, create if needed
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS beta_user_analytics (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    user_id UUID REFERENCES users(id) NOT NULL,
                    event_type VARCHAR(100) NOT NULL,
                    event_data JSONB,
                    session_id VARCHAR(255),
                    ip_address INET,
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Beta user tiers
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS beta_user_tiers (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    user_id UUID REFERENCES users(id) UNIQUE NOT NULL,
                    tier VARCHAR(50) DEFAULT 'standard',
                    features_enabled TEXT[],
                    data_limits JSONB,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Failed to initialize beta tables: {e}")
        finally:
            cursor.close()
            conn.close()

    def generate_invite_code(self, length: int = 12) -> str:
        """Generate secure invite code"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def create_invite(self, email: str, invited_by: str, 
                     access_level: str = "standard", metadata: Dict = None) -> str:
        """Create a new beta invite"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Check if user already exists
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                raise ValueError(f"User with email {email} already exists")
            
            # Check invite limit
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_beta_user = true")
            current_count = cursor.fetchone()[0]
            
            if current_count >= self.config["max_beta_users"]:
                raise ValueError(f"Beta user limit reached ({self.config['max_beta_users']})")
            
            # Check if invite already exists
            cursor.execute("SELECT id FROM beta_invites WHERE email = %s AND status = 'pending'", (email,))
            if cursor.fetchone():
                raise ValueError(f"Pending invite already exists for {email}")
            
            # Create invite
            invite_code = self.generate_invite_code()
            expires_at = datetime.now() + timedelta(days=self.config["invite_expiry_days"])
            
            cursor.execute('''
                INSERT INTO beta_invites 
                (email, invite_code, invited_by, expires_at, status)
                VALUES (%s, %s, %s, %s, 'pending')
                RETURNING id
            ''', (email, invite_code, invited_by, expires_at))
            
            invite_id = cursor.fetchone()[0]
            
            # Store metadata
            if metadata:
                cursor.execute('''
                    UPDATE beta_invites 
                    SET metadata = %s 
                    WHERE id = %s
                ''', (json.dumps({**metadata, "access_level": access_level}), invite_id))
            
            conn.commit()
            
            self.logger.info(f"Created beta invite {invite_id} for {email}")
            
            # Send invitation email
            if self.config["welcome_email_enabled"]:
                self._send_invite_email(email, invite_code, invited_by)
            
            return str(invite_id)
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Failed to create invite: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def accept_invite(self, invite_code: str, user_data: Dict) -> str:
        """Accept beta invite and create user account"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Validate invite
            cursor.execute('''
                SELECT id, email, invited_by, expires_at, status, metadata
                FROM beta_invites 
                WHERE invite_code = %s
            ''', (invite_code,))
            
            invite = cursor.fetchone()
            if not invite:
                raise ValueError("Invalid invite code")
            
            invite_id, email, invited_by, expires_at, status, metadata = invite
            
            if status != 'pending':
                raise ValueError(f"Invite is {status}")
            
            if datetime.now() > expires_at:
                raise ValueError("Invite has expired")
            
            # Create user account
            password_hash = bcrypt.hashpw(
                user_data["password"].encode('utf-8'), 
                bcrypt.gensalt()
            ).decode('utf-8')
            
            cursor.execute('''
                INSERT INTO users 
                (email, username, password_hash, first_name, last_name, 
                 is_beta_user, is_active, email_verified_at)
                VALUES (%s, %s, %s, %s, %s, true, true, %s)
                RETURNING id
            ''', (
                email,
                user_data.get("username", email.split('@')[0]),
                password_hash,
                user_data.get("first_name", ""),
                user_data.get("last_name", ""),
                datetime.now()
            ))
            
            user_id = cursor.fetchone()[0]
            
            # Update invite status
            cursor.execute('''
                UPDATE beta_invites 
                SET status = 'accepted', accepted_at = %s
                WHERE id = %s
            ''', (datetime.now(), invite_id))
            
            # Set user tier
            access_level = "standard"
            if metadata:
                meta_dict = json.loads(metadata) if isinstance(metadata, str) else metadata
                access_level = meta_dict.get("access_level", "standard")
            
            self._set_user_tier(user_id, access_level)
            
            # Log analytics event
            self._log_analytics_event(user_id, "account_created", {
                "invite_id": str(invite_id),
                "invited_by": invited_by,
                "access_level": access_level
            })
            
            conn.commit()
            
            self.logger.info(f"Beta invite accepted: {email} -> {user_id}")
            
            # Send welcome email
            if self.config["welcome_email_enabled"]:
                self._send_welcome_email(email, user_data.get("first_name", ""))
            
            return str(user_id)
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Failed to accept invite: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def _set_user_tier(self, user_id: str, tier: str):
        """Set user tier and associated features"""
        tier_configs = {
            "standard": {
                "features_enabled": ["basic_features", "feedback_system"],
                "data_limits": {
                    "max_files": 1000,
                    "max_storage_mb": 500,
                    "api_calls_per_day": 1000
                }
            },
            "premium": {
                "features_enabled": ["basic_features", "advanced_features", "beta_features"],
                "data_limits": {
                    "max_files": 10000,
                    "max_storage_mb": 5000,
                    "api_calls_per_day": 10000
                }
            },
            "admin": {
                "features_enabled": ["all_features", "admin_panel"],
                "data_limits": {
                    "max_files": -1,  # Unlimited
                    "max_storage_mb": -1,
                    "api_calls_per_day": -1
                }
            }
        }
        
        config = tier_configs.get(tier, tier_configs["standard"])
        expires_at = datetime.now() + timedelta(days=90)  # 90-day beta period
        
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO beta_user_tiers 
                (user_id, tier, features_enabled, data_limits, expires_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    tier = EXCLUDED.tier,
                    features_enabled = EXCLUDED.features_enabled,
                    data_limits = EXCLUDED.data_limits,
                    expires_at = EXCLUDED.expires_at,
                    updated_at = CURRENT_TIMESTAMP
            ''', (
                user_id,
                tier,
                config["features_enabled"],
                json.dumps(config["data_limits"]),
                expires_at
            ))
            
            conn.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to set user tier: {e}")
        finally:
            cursor.close()
            conn.close()

    def get_beta_users(self, limit: int = 100, offset: int = 0) -> List[BetaUser]:
        """Get list of beta users"""
        conn = self._get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute('''
                SELECT 
                    u.id, u.email, u.username, u.first_name, u.last_name,
                    u.created_at as invited_at, u.last_login,
                    CASE WHEN u.is_active THEN 'active' ELSE 'inactive' END as status,
                    t.tier as access_level,
                    (SELECT COUNT(*) FROM feedback WHERE user_id = u.id) as feedback_count,
                    (SELECT COUNT(*) FROM user_sessions WHERE user_id = u.id) as login_count,
                    (SELECT agreed_at IS NOT NULL FROM nda_agreements WHERE user_id = u.id) as nda_signed
                FROM users u
                LEFT JOIN beta_user_tiers t ON u.id = t.user_id
                WHERE u.is_beta_user = true
                ORDER BY u.created_at DESC
                LIMIT %s OFFSET %s
            ''', (limit, offset))
            
            users = []
            for row in cursor.fetchall():
                user = BetaUser(
                    id=str(row["id"]),
                    email=row["email"],
                    username=row["username"] or "",
                    first_name=row["first_name"] or "",
                    last_name=row["last_name"] or "",
                    status=row["status"],
                    invited_by="",  # Would need join to get this
                    invited_at=row["invited_at"].isoformat() if row["invited_at"] else "",
                    last_login=row["last_login"].isoformat() if row["last_login"] else None,
                    login_count=row["login_count"] or 0,
                    feedback_count=row["feedback_count"] or 0,
                    nda_signed=row["nda_signed"] or False,
                    access_level=row["access_level"] or "standard"
                )
                users.append(user)
            
            return users
            
        except Exception as e:
            self.logger.error(f"Failed to get beta users: {e}")
            return []
        finally:
            cursor.close()
            conn.close()

    def get_beta_stats(self) -> Dict:
        """Get beta program statistics"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            stats = {}
            
            # User counts
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_beta_user = true")
            stats["total_beta_users"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_beta_user = true AND is_active = true")
            stats["active_beta_users"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM beta_invites WHERE status = 'pending'")
            stats["pending_invites"] = cursor.fetchone()[0]
            
            # Activity stats
            cursor.execute('''
                SELECT COUNT(DISTINCT user_id) 
                FROM user_sessions 
                WHERE created_at > %s
            ''', (datetime.now() - timedelta(days=7),))
            stats["weekly_active_users"] = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT COUNT(DISTINCT user_id) 
                FROM user_sessions 
                WHERE created_at > %s
            ''', (datetime.now() - timedelta(days=30),))
            stats["monthly_active_users"] = cursor.fetchone()[0]
            
            # Feedback stats
            cursor.execute("SELECT COUNT(*) FROM feedback WHERE created_at > %s", 
                         (datetime.now() - timedelta(days=7),))
            stats["weekly_feedback_count"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT AVG(rating) FROM feedback WHERE rating IS NOT NULL")
            avg_rating = cursor.fetchone()[0]
            stats["average_rating"] = float(avg_rating) if avg_rating else 0
            
            # NDA stats
            cursor.execute("SELECT COUNT(*) FROM nda_agreements")
            stats["nda_signed_count"] = cursor.fetchone()[0]
            
            # Feature usage
            cursor.execute('''
                SELECT event_type, COUNT(*) 
                FROM beta_user_analytics 
                WHERE created_at > %s
                GROUP BY event_type
                ORDER BY count DESC
                LIMIT 10
            ''', (datetime.now() - timedelta(days=7),))
            
            stats["top_features"] = [
                {"feature": row[0], "usage_count": row[1]} 
                for row in cursor.fetchall()
            ]
            
            # Tier distribution
            cursor.execute('''
                SELECT tier, COUNT(*) 
                FROM beta_user_tiers 
                GROUP BY tier
            ''')
            stats["tier_distribution"] = {row[0]: row[1] for row in cursor.fetchall()}
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get beta stats: {e}")
            return {}
        finally:
            cursor.close()
            conn.close()

    def deactivate_user(self, user_id: str, reason: str = "Manual deactivation") -> bool:
        """Deactivate beta user"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE users 
                SET is_active = false 
                WHERE id = %s AND is_beta_user = true
            ''', (user_id,))
            
            if cursor.rowcount == 0:
                raise ValueError("User not found or not a beta user")
            
            # Log the deactivation
            self._log_analytics_event(user_id, "account_deactivated", {
                "reason": reason,
                "deactivated_at": datetime.now().isoformat()
            })
            
            conn.commit()
            
            self.logger.info(f"Deactivated beta user {user_id}: {reason}")
            return True
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Failed to deactivate user: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def upgrade_user_tier(self, user_id: str, new_tier: str) -> bool:
        """Upgrade user to higher tier"""
        valid_tiers = ["standard", "premium", "admin"]
        if new_tier not in valid_tiers:
            raise ValueError(f"Invalid tier: {new_tier}")
        
        self._set_user_tier(user_id, new_tier)
        
        # Log the upgrade
        self._log_analytics_event(user_id, "tier_upgraded", {
            "new_tier": new_tier,
            "upgraded_at": datetime.now().isoformat()
        })
        
        self.logger.info(f"Upgraded user {user_id} to {new_tier} tier")
        return True

    def _log_analytics_event(self, user_id: str, event_type: str, event_data: Dict):
        """Log analytics event for beta user"""
        if not self.config.get("analytics_enabled", True):
            return
        
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO beta_user_analytics 
                (user_id, event_type, event_data)
                VALUES (%s, %s, %s)
            ''', (user_id, event_type, json.dumps(event_data)))
            
            conn.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to log analytics event: {e}")
        finally:
            cursor.close()
            conn.close()

    def _send_invite_email(self, email: str, invite_code: str, invited_by: str):
        """Send invitation email"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config["email"]["from_email"]
            msg['To'] = email
            msg['Subject'] = "You're invited to ActiveLog Beta!"
            
            body = f"""
Hi there!

You've been invited to join the ActiveLog Beta program! 

Your invitation code is: {invite_code}

To accept your invitation, visit:
{self.config.get('frontend_url', 'http://localhost:3000')}/beta/accept?code={invite_code}

This invitation expires in {self.config['invite_expiry_days']} days.

Welcome to the future of activity logging!

The ActiveLog Team
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(
                self.config["email"]["smtp_host"], 
                self.config["email"]["smtp_port"]
            )
            
            if self.config["email"]["username"]:
                server.starttls()
                server.login(
                    self.config["email"]["username"], 
                    self.config["email"]["password"]
                )
            
            server.send_message(msg)
            server.quit()
            
            self.logger.info(f"Sent invitation email to {email}")
            
        except Exception as e:
            self.logger.error(f"Failed to send invitation email: {e}")

    def _send_welcome_email(self, email: str, first_name: str):
        """Send welcome email to new beta user"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config["email"]["from_email"]
            msg['To'] = email
            msg['Subject'] = "Welcome to ActiveLog Beta!"
            
            name = first_name or "there"
            
            body = f"""
Hi {name}!

Welcome to ActiveLog Beta! We're excited to have you on board.

Here are some things to get you started:
- Complete your profile setup
- Try out the new dashboard features
- Share your feedback - we really value your input!

If you have any questions, don't hesitate to reach out to our beta support team.

Happy logging!

The ActiveLog Team

P.S. Don't forget to sign the NDA to access all beta features!
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(
                self.config["email"]["smtp_host"], 
                self.config["email"]["smtp_port"]
            )
            
            if self.config["email"]["username"]:
                server.starttls()
                server.login(
                    self.config["email"]["username"], 
                    self.config["email"]["password"]
                )
            
            server.send_message(msg)
            server.quit()
            
            self.logger.info(f"Sent welcome email to {email}")
            
        except Exception as e:
            self.logger.error(f"Failed to send welcome email: {e}")

    def cleanup_expired_invites(self) -> int:
        """Clean up expired invites"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE beta_invites 
                SET status = 'expired' 
                WHERE status = 'pending' AND expires_at < %s
            ''', (datetime.now(),))
            
            expired_count = cursor.rowcount
            conn.commit()
            
            self.logger.info(f"Marked {expired_count} invites as expired")
            return expired_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup expired invites: {e}")
            return 0
        finally:
            cursor.close()
            conn.close()

def main():
    parser = argparse.ArgumentParser(description='Beta User Manager')
    parser.add_argument('--environment', default='beta', help='Environment')
    parser.add_argument('--config', help='Configuration file path')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize beta management system')
    
    # Invite command
    invite_parser = subparsers.add_parser('invite', help='Create beta invite')
    invite_parser.add_argument('--email', required=True, help='Email address')
    invite_parser.add_argument('--invited-by', required=True, help='Inviter user ID')
    invite_parser.add_argument('--tier', default='standard', help='Access tier')
    
    # List users command
    list_parser = subparsers.add_parser('list', help='List beta users')
    list_parser.add_argument('--limit', type=int, default=50, help='Limit results')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show beta statistics')
    
    # Deactivate command
    deactivate_parser = subparsers.add_parser('deactivate', help='Deactivate user')
    deactivate_parser.add_argument('--user-id', required=True, help='User ID')
    deactivate_parser.add_argument('--reason', default='Manual', help='Reason')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Cleanup expired invites')
    
    args = parser.parse_args()
    
    manager = BetaUserManager(args.environment, args.config)
    
    if args.command == 'init':
        print("Beta user management system initialized")
    
    elif args.command == 'invite':
        invite_id = manager.create_invite(args.email, args.invited_by, args.tier)
        print(f"Created invite: {invite_id}")
    
    elif args.command == 'list':
        users = manager.get_beta_users(args.limit)
        for user in users:
            print(f"{user.email}: {user.status} ({user.access_level})")
    
    elif args.command == 'stats':
        stats = manager.get_beta_stats()
        print(json.dumps(stats, indent=2, default=str))
    
    elif args.command == 'deactivate':
        success = manager.deactivate_user(args.user_id, args.reason)
        print("User deactivated" if success else "Failed to deactivate user")
    
    elif args.command == 'cleanup':
        count = manager.cleanup_expired_invites()
        print(f"Cleaned up {count} expired invites")
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main()