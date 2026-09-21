#!/usr/bin/env python3

"""
Beta Invite System for ActiveLog
Advanced invite management with batch invites, referrals, and tracking
"""

import os
import json
import csv
import argparse
import logging
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import psycopg2
from psycopg2.extras import RealDictCursor
import qrcode
from io import BytesIO
import base64

@dataclass
class InviteTemplate:
    name: str
    subject: str
    body: str
    access_level: str
    expiry_days: int
    features: List[str]

@dataclass
class InviteCampaign:
    id: str
    name: str
    description: str
    template_name: str
    max_invites: int
    expiry_date: str
    status: str
    created_at: str
    stats: Dict = None

class InviteSystem:
    def __init__(self, environment: str = "beta", config_path: str = None):
        self.environment = environment
        self.data_dir = Path(f"/app/data/invites/{environment}")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.data_dir / "invite-system.log"),
                logging.StreamHandler()
            ]
        )
        
        self.templates = self._load_templates()
        self._init_database()

    def _load_templates(self) -> Dict[str, InviteTemplate]:
        """Load invite templates"""
        templates = {
            "standard": InviteTemplate(
                name="standard",
                subject="Welcome to ActiveLog Beta!",
                body="""
Hi there!

You've been invited to join the ActiveLog Beta program! We're building the future of activity logging and we'd love your feedback.

Your invitation code: {invite_code}

Features you'll get access to:
- New dashboard interface
- Advanced analytics
- Priority support
- Direct feedback channel to our development team

Accept your invitation: {accept_url}

This invitation expires in {expiry_days} days.

Questions? Reply to this email or contact beta-support@activelog.dev

Welcome aboard!
The ActiveLog Team
                """,
                access_level="standard",
                expiry_days=7,
                features=["dashboard", "analytics", "support"]
            ),
            
            "premium": InviteTemplate(
                name="premium",
                subject="ActiveLog Premium Beta - Exclusive Access",
                body="""
Hello!

You've been selected for our exclusive Premium Beta program! 

Your invitation code: {invite_code}

Premium Beta Features:
- All standard beta features
- Advanced AI-powered insights
- Custom integrations
- 1-on-1 onboarding session
- Early access to enterprise features

Accept your invitation: {accept_url}

This invitation expires in {expiry_days} days.

As a premium beta user, you'll also receive:
- Priority feature requests
- Direct line to our product team
- Exclusive beta events and demos

Looking forward to your feedback!
The ActiveLog Team
                """,
                access_level="premium",
                expiry_days=14,
                features=["all_beta", "ai_insights", "integrations", "onboarding"]
            ),
            
            "developer": InviteTemplate(
                name="developer",
                subject="ActiveLog Developer Beta - API Early Access",
                body="""
Hi Developer!

You've been invited to our Developer Beta program with early API access!

Your invitation code: {invite_code}

Developer Beta includes:
- Full API access with extended rate limits
- SDK early access
- Developer documentation preview
- Integration sandbox environment
- Developer community access

Accept your invitation: {accept_url}

This invitation expires in {expiry_days} days.

Developer Resources:
- API Documentation: {api_docs_url}
- SDK Repository: {sdk_repo_url}
- Developer Discord: {discord_url}

Happy coding!
The ActiveLog Developer Team
                """,
                access_level="developer",
                expiry_days=30,
                features=["api_access", "sdk", "docs", "sandbox", "community"]
            )
        }
        
        # Load custom templates from config if available
        templates_file = self.data_dir / "templates.json"
        if templates_file.exists():
            try:
                with open(templates_file) as f:
                    custom_templates = json.load(f)
                
                for name, data in custom_templates.items():
                    templates[name] = InviteTemplate(**data)
                    
            except Exception as e:
                self.logger.error(f"Failed to load custom templates: {e}")
        
        return templates

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
        """Initialize invite system tables"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Invite campaigns table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS invite_campaigns (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    template_name VARCHAR(100) NOT NULL,
                    max_invites INTEGER DEFAULT 100,
                    expiry_date TIMESTAMP,
                    status VARCHAR(50) DEFAULT 'active',
                    created_by UUID REFERENCES users(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSONB
                )
            ''')
            
            # Extended beta_invites with campaign support
            cursor.execute('''
                ALTER TABLE beta_invites 
                ADD COLUMN IF NOT EXISTS campaign_id UUID REFERENCES invite_campaigns(id),
                ADD COLUMN IF NOT EXISTS template_name VARCHAR(100),
                ADD COLUMN IF NOT EXISTS referral_code VARCHAR(100),
                ADD COLUMN IF NOT EXISTS utm_source VARCHAR(100),
                ADD COLUMN IF NOT EXISTS utm_medium VARCHAR(100),
                ADD COLUMN IF NOT EXISTS utm_campaign VARCHAR(100),
                ADD COLUMN IF NOT EXISTS custom_data JSONB
            ''')
            
            # Referral tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS invite_referrals (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    referrer_user_id UUID REFERENCES users(id) NOT NULL,
                    referee_invite_id UUID REFERENCES beta_invites(id) NOT NULL,
                    referee_user_id UUID REFERENCES users(id),
                    reward_earned BOOLEAN DEFAULT FALSE,
                    reward_amount DECIMAL(10,2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            ''')
            
            # Invite analytics
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS invite_analytics (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    invite_id UUID REFERENCES beta_invites(id),
                    event_type VARCHAR(100) NOT NULL,
                    event_data JSONB,
                    ip_address INET,
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Failed to initialize invite tables: {e}")
        finally:
            cursor.close()
            conn.close()

    def create_campaign(self, name: str, description: str, template_name: str,
                       max_invites: int = 100, expiry_days: int = 30,
                       created_by: str = None) -> str:
        """Create invite campaign"""
        if template_name not in self.templates:
            raise ValueError(f"Template '{template_name}' not found")
        
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            expiry_date = datetime.now() + timedelta(days=expiry_days)
            
            cursor.execute('''
                INSERT INTO invite_campaigns 
                (name, description, template_name, max_invites, expiry_date, created_by)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (name, description, template_name, max_invites, expiry_date, created_by))
            
            campaign_id = cursor.fetchone()[0]
            conn.commit()
            
            self.logger.info(f"Created invite campaign: {name} ({campaign_id})")
            return str(campaign_id)
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Failed to create campaign: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def send_invite(self, email: str, invited_by: str, template_name: str = "standard",
                   campaign_id: str = None, referral_code: str = None,
                   custom_data: Dict = None, utm_params: Dict = None) -> str:
        """Send single invite with advanced tracking"""
        template = self.templates.get(template_name, self.templates["standard"])
        
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Generate invite code
            invite_code = self._generate_invite_code()
            expires_at = datetime.now() + timedelta(days=template.expiry_days)
            
            # Insert invite
            cursor.execute('''
                INSERT INTO beta_invites 
                (email, invite_code, invited_by, expires_at, campaign_id, 
                 template_name, referral_code, custom_data, utm_source, 
                 utm_medium, utm_campaign)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                email, invite_code, invited_by, expires_at, campaign_id,
                template_name, referral_code, 
                json.dumps(custom_data) if custom_data else None,
                utm_params.get('utm_source') if utm_params else None,
                utm_params.get('utm_medium') if utm_params else None,
                utm_params.get('utm_campaign') if utm_params else None
            ))
            
            invite_id = cursor.fetchone()[0]
            
            # Handle referral if present
            if referral_code:
                self._handle_referral(cursor, referral_code, invite_id)
            
            conn.commit()
            
            # Generate accept URL with tracking
            accept_url = self._generate_accept_url(invite_code, utm_params)
            
            # Send email
            self._send_invite_email(email, invite_code, template, accept_url)
            
            # Track analytics
            self._track_invite_event(invite_id, "invite_sent", {
                "template": template_name,
                "campaign_id": campaign_id,
                "email": email
            })
            
            self.logger.info(f"Sent invite to {email} with code {invite_code}")
            return str(invite_id)
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Failed to send invite: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def bulk_invite(self, invites_data: List[Dict], campaign_id: str = None,
                   template_name: str = "standard", invited_by: str = None) -> Dict:
        """Send bulk invites from list or CSV"""
        results = {
            "successful": 0,
            "failed": 0,
            "errors": []
        }
        
        template = self.templates.get(template_name, self.templates["standard"])
        
        for invite_data in invites_data:
            try:
                email = invite_data["email"]
                custom_data = invite_data.get("custom_data", {})
                
                # Merge any additional fields into custom_data
                for key, value in invite_data.items():
                    if key not in ["email", "custom_data"]:
                        custom_data[key] = value
                
                invite_id = self.send_invite(
                    email=email,
                    invited_by=invited_by,
                    template_name=template_name,
                    campaign_id=campaign_id,
                    custom_data=custom_data
                )
                
                results["successful"] += 1
                
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "email": invite_data.get("email", "unknown"),
                    "error": str(e)
                })
                self.logger.error(f"Failed to send bulk invite to {invite_data.get('email')}: {e}")
        
        self.logger.info(f"Bulk invite completed: {results['successful']} successful, {results['failed']} failed")
        return results

    def bulk_invite_from_csv(self, csv_file_path: str, campaign_id: str = None,
                            template_name: str = "standard", invited_by: str = None) -> Dict:
        """Send bulk invites from CSV file"""
        invites_data = []
        
        try:
            with open(csv_file_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if row.get('email'):  # Only process rows with email
                        invites_data.append(row)
            
            return self.bulk_invite(invites_data, campaign_id, template_name, invited_by)
            
        except Exception as e:
            self.logger.error(f"Failed to process CSV file: {e}")
            raise

    def generate_referral_code(self, user_id: str) -> str:
        """Generate referral code for user"""
        # Create a short, memorable referral code
        code = f"REF{secrets.token_hex(4).upper()}"
        
        # Could store in database for tracking
        # For now, we'll encode the user_id in the code
        return f"{code}{user_id[:8].upper()}"

    def _handle_referral(self, cursor, referral_code: str, invite_id: str):
        """Handle referral tracking"""
        try:
            # Extract referrer user ID from referral code
            # This is a simple implementation - in production, you'd have a proper lookup
            if referral_code.startswith("REF"):
                referrer_id = referral_code[12:]  # Extract user ID part
                
                cursor.execute('''
                    INSERT INTO invite_referrals (referrer_user_id, referee_invite_id)
                    VALUES (%s, %s)
                ''', (referrer_id, invite_id))
                
        except Exception as e:
            self.logger.error(f"Failed to handle referral: {e}")

    def _generate_invite_code(self) -> str:
        """Generate secure invite code"""
        return secrets.token_urlsafe(16)

    def _generate_accept_url(self, invite_code: str, utm_params: Dict = None) -> str:
        """Generate acceptance URL with tracking"""
        base_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        accept_url = f"{base_url}/beta/accept?code={invite_code}"
        
        if utm_params:
            utm_string = "&".join([f"{k}={v}" for k, v in utm_params.items() if v])
            if utm_string:
                accept_url += f"&{utm_string}"
        
        return accept_url

    def _send_invite_email(self, email: str, invite_code: str, template: InviteTemplate,
                          accept_url: str):
        """Send invite email using template"""
        try:
            # Format template with variables
            subject = template.subject
            body = template.body.format(
                invite_code=invite_code,
                accept_url=accept_url,
                expiry_days=template.expiry_days,
                features="\n".join([f"- {f}" for f in template.features]),
                api_docs_url=os.getenv("API_DOCS_URL", "#"),
                sdk_repo_url=os.getenv("SDK_REPO_URL", "#"),
                discord_url=os.getenv("DISCORD_URL", "#")
            )
            
            # Here you would integrate with your email service
            # For now, we'll log the email content
            self.logger.info(f"Sending email to {email}: {subject}")
            self.logger.debug(f"Email body: {body}")
            
            # In production, integrate with SendGrid, SES, etc.
            
        except Exception as e:
            self.logger.error(f"Failed to send email to {email}: {e}")
            raise

    def _track_invite_event(self, invite_id: str, event_type: str, event_data: Dict):
        """Track invite analytics event"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO invite_analytics (invite_id, event_type, event_data)
                VALUES (%s, %s, %s)
            ''', (invite_id, event_type, json.dumps(event_data)))
            
            conn.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to track invite event: {e}")
        finally:
            cursor.close()
            conn.close()

    def generate_qr_code(self, invite_code: str) -> str:
        """Generate QR code for invite"""
        accept_url = self._generate_accept_url(invite_code)
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(accept_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 for embedding
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{qr_base64}"

    def get_invite_analytics(self, invite_id: str = None, campaign_id: str = None,
                           days: int = 30) -> Dict:
        """Get invite analytics"""
        conn = self._get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            analytics = {}
            
            # Base query conditions
            where_conditions = ["ia.created_at > %s"]
            params = [datetime.now() - timedelta(days=days)]
            
            if invite_id:
                where_conditions.append("ia.invite_id = %s")
                params.append(invite_id)
            
            if campaign_id:
                where_conditions.append("bi.campaign_id = %s")
                params.append(campaign_id)
            
            where_clause = " AND ".join(where_conditions)
            
            # Event counts
            cursor.execute(f'''
                SELECT ia.event_type, COUNT(*) as count
                FROM invite_analytics ia
                JOIN beta_invites bi ON ia.invite_id = bi.id
                WHERE {where_clause}
                GROUP BY ia.event_type
                ORDER BY count DESC
            ''', params)
            
            analytics["event_counts"] = {row["event_type"]: row["count"] for row in cursor.fetchall()}
            
            # Conversion funnel
            cursor.execute(f'''
                SELECT 
                    COUNT(DISTINCT bi.id) as invites_sent,
                    COUNT(DISTINCT CASE WHEN bi.status = 'accepted' THEN bi.id END) as invites_accepted,
                    COUNT(DISTINCT u.id) as users_created
                FROM beta_invites bi
                LEFT JOIN users u ON bi.email = u.email
                WHERE bi.created_at > %s
                {f"AND bi.campaign_id = %s" if campaign_id else ""}
            ''', params)
            
            funnel = cursor.fetchone()
            analytics["conversion_funnel"] = dict(funnel) if funnel else {}
            
            # Top referrers (if campaign-wide)
            if not invite_id:
                cursor.execute(f'''
                    SELECT 
                        u.email,
                        COUNT(*) as referrals_count,
                        COUNT(CASE WHEN bi.status = 'accepted' THEN 1 END) as successful_referrals
                    FROM invite_referrals ir
                    JOIN users u ON ir.referrer_user_id = u.id
                    JOIN beta_invites bi ON ir.referee_invite_id = bi.id
                    WHERE ir.created_at > %s
                    GROUP BY u.id, u.email
                    ORDER BY referrals_count DESC
                    LIMIT 10
                ''', [datetime.now() - timedelta(days=days)])
                
                analytics["top_referrers"] = [dict(row) for row in cursor.fetchall()]
            
            return analytics
            
        except Exception as e:
            self.logger.error(f"Failed to get invite analytics: {e}")
            return {}
        finally:
            cursor.close()
            conn.close()

    def get_campaign_stats(self, campaign_id: str) -> Dict:
        """Get detailed campaign statistics"""
        conn = self._get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Campaign details
            cursor.execute('''
                SELECT * FROM invite_campaigns WHERE id = %s
            ''', (campaign_id,))
            
            campaign = cursor.fetchone()
            if not campaign:
                return {"error": "Campaign not found"}
            
            # Invite stats
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_invites,
                    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_invites,
                    COUNT(CASE WHEN status = 'accepted' THEN 1 END) as accepted_invites,
                    COUNT(CASE WHEN status = 'expired' THEN 1 END) as expired_invites
                FROM beta_invites 
                WHERE campaign_id = %s
            ''', (campaign_id,))
            
            stats = cursor.fetchone()
            
            # Conversion rate
            total = stats["total_invites"]
            accepted = stats["accepted_invites"]
            conversion_rate = (accepted / total * 100) if total > 0 else 0
            
            return {
                "campaign": dict(campaign),
                "stats": dict(stats),
                "conversion_rate": round(conversion_rate, 2),
                "remaining_slots": campaign["max_invites"] - total
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get campaign stats: {e}")
            return {"error": str(e)}
        finally:
            cursor.close()
            conn.close()

def main():
    parser = argparse.ArgumentParser(description='Invite System Manager')
    parser.add_argument('--environment', default='beta', help='Environment')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Setup command
    setup_parser = subparsers.add_parser('setup', help='Setup invite system')
    
    # Create campaign
    campaign_parser = subparsers.add_parser('create-campaign', help='Create invite campaign')
    campaign_parser.add_argument('--name', required=True, help='Campaign name')
    campaign_parser.add_argument('--description', required=True, help='Campaign description')
    campaign_parser.add_argument('--template', default='standard', help='Template name')
    campaign_parser.add_argument('--max-invites', type=int, default=100, help='Max invites')
    
    # Send invite
    invite_parser = subparsers.add_parser('invite', help='Send single invite')
    invite_parser.add_argument('--email', required=True, help='Email address')
    invite_parser.add_argument('--template', default='standard', help='Template name')
    invite_parser.add_argument('--campaign', help='Campaign ID')
    invite_parser.add_argument('--invited-by', required=True, help='Inviter user ID')
    
    # Bulk invite
    bulk_parser = subparsers.add_parser('bulk-invite', help='Send bulk invites from CSV')
    bulk_parser.add_argument('--csv-file', required=True, help='CSV file path')
    bulk_parser.add_argument('--template', default='standard', help='Template name')
    bulk_parser.add_argument('--campaign', help='Campaign ID')
    bulk_parser.add_argument('--invited-by', required=True, help='Inviter user ID')
    
    # Analytics
    analytics_parser = subparsers.add_parser('analytics', help='Get invite analytics')
    analytics_parser.add_argument('--campaign', help='Campaign ID')
    analytics_parser.add_argument('--days', type=int, default=30, help='Days to analyze')
    
    args = parser.parse_args()
    
    system = InviteSystem(args.environment)
    
    if args.command == 'setup':
        print("Invite system setup completed")
    
    elif args.command == 'create-campaign':
        campaign_id = system.create_campaign(
            args.name, args.description, args.template, args.max_invites
        )
        print(f"Created campaign: {campaign_id}")
    
    elif args.command == 'invite':
        invite_id = system.send_invite(
            args.email, args.invited_by, args.template, args.campaign
        )
        print(f"Sent invite: {invite_id}")
    
    elif args.command == 'bulk-invite':
        results = system.bulk_invite_from_csv(
            args.csv_file, args.campaign, args.template, args.invited_by
        )
        print(f"Bulk invite results: {results}")
    
    elif args.command == 'analytics':
        analytics = system.get_invite_analytics(campaign_id=args.campaign, days=args.days)
        print(json.dumps(analytics, indent=2, default=str))
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main()