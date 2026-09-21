"""
Crew Management and Invitation System
Comprehensive crew member management with invitation workflow
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
import logging
import hashlib
import secrets
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

logger = logging.getLogger(__name__)

class CrewRole(Enum):
    CAPTAIN = "captain"
    FIRST_MATE = "first_mate"
    MATE = "mate"
    DECKHAND = "deckhand"
    ENGINEER = "engineer"
    COOK = "cook"
    OBSERVER = "observer"
    GUEST = "guest"

class InvitationStatus(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class CrewStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ON_LEAVE = "on_leave"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"

class EmergencyContact(Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    MEDICAL = "medical"
    WORK = "work"

@dataclass
class CrewMember:
    member_id: str
    vessel_id: str
    user_id: Optional[str] = None
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    role: CrewRole = CrewRole.DECKHAND
    status: CrewStatus = CrewStatus.ACTIVE
    hire_date: Optional[datetime] = None
    last_active: Optional[datetime] = None
    emergency_contacts: Optional[List[Dict[str, str]]] = None
    certifications: Optional[List[str]] = None
    medical_restrictions: Optional[str] = None
    share_percentage: float = 0.0
    hourly_rate: Optional[float] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if not self.member_id:
            self.member_id = str(uuid.uuid4())
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = self.created_at
        if self.emergency_contacts is None:
            self.emergency_contacts = []
        if self.certifications is None:
            self.certifications = []
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def is_officer(self) -> bool:
        return self.role in [CrewRole.CAPTAIN, CrewRole.FIRST_MATE, CrewRole.MATE]
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['role'] = self.role.value
        result['status'] = self.status.value
        if result.get('hire_date'):
            result['hire_date'] = result['hire_date'].isoformat()
        if result.get('last_active'):
            result['last_active'] = result['last_active'].isoformat()
        if result.get('created_at'):
            result['created_at'] = result['created_at'].isoformat()
        if result.get('updated_at'):
            result['updated_at'] = result['updated_at'].isoformat()
        return result

@dataclass
class CrewInvitation:
    invitation_id: str
    vessel_id: str
    invited_by: str  # member_id
    email: str
    phone: Optional[str] = None
    proposed_role: CrewRole = CrewRole.DECKHAND
    message: Optional[str] = None
    status: InvitationStatus = InvitationStatus.PENDING
    invitation_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if not self.invitation_id:
            self.invitation_id = str(uuid.uuid4())
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(days=7)  # 7 days to respond
        if self.invitation_token is None:
            self.invitation_token = secrets.token_urlsafe(32)
    
    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['proposed_role'] = self.proposed_role.value
        result['status'] = self.status.value
        if result.get('expires_at'):
            result['expires_at'] = result['expires_at'].isoformat()
        if result.get('sent_at'):
            result['sent_at'] = result['sent_at'].isoformat()
        if result.get('responded_at'):
            result['responded_at'] = result['responded_at'].isoformat()
        if result.get('created_at'):
            result['created_at'] = result['created_at'].isoformat()
        return result

@dataclass
class VesselCrew:
    vessel_id: str
    vessel_name: str
    captain_id: str
    max_crew_size: int = 8
    current_crew_count: int = 0
    active_trip_id: Optional[str] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        if result.get('created_at'):
            result['created_at'] = result['created_at'].isoformat()
        return result

class CrewDatabase:
    """Database for crew management"""
    
    def __init__(self, db_path: str = "crew_management.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            # Vessels table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vessels (
                    vessel_id TEXT PRIMARY KEY,
                    vessel_name TEXT NOT NULL,
                    captain_id TEXT NOT NULL,
                    max_crew_size INTEGER DEFAULT 8,
                    current_crew_count INTEGER DEFAULT 0,
                    active_trip_id TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            
            # Crew members table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS crew_members (
                    member_id TEXT PRIMARY KEY,
                    vessel_id TEXT NOT NULL,
                    user_id TEXT,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    phone TEXT,
                    role TEXT NOT NULL,
                    status TEXT NOT NULL,
                    hire_date TEXT,
                    last_active TEXT,
                    emergency_contacts TEXT,
                    certifications TEXT,
                    medical_restrictions TEXT,
                    share_percentage REAL DEFAULT 0.0,
                    hourly_rate REAL,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (vessel_id) REFERENCES vessels (vessel_id)
                )
            """)
            
            # Invitations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS crew_invitations (
                    invitation_id TEXT PRIMARY KEY,
                    vessel_id TEXT NOT NULL,
                    invited_by TEXT NOT NULL,
                    email TEXT NOT NULL,
                    phone TEXT,
                    proposed_role TEXT NOT NULL,
                    message TEXT,
                    status TEXT NOT NULL,
                    invitation_token TEXT UNIQUE NOT NULL,
                    expires_at TEXT NOT NULL,
                    sent_at TEXT,
                    responded_at TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (vessel_id) REFERENCES vessels (vessel_id),
                    FOREIGN KEY (invited_by) REFERENCES crew_members (member_id)
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_crew_vessel ON crew_members(vessel_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_crew_role ON crew_members(role)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_crew_status ON crew_members(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_invitations_vessel ON crew_invitations(vessel_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_invitations_token ON crew_invitations(invitation_token)")
    
    def save_vessel(self, vessel: VesselCrew) -> bool:
        """Save vessel crew configuration"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO vessels (
                        vessel_id, vessel_name, captain_id, max_crew_size,
                        current_crew_count, active_trip_id, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    vessel.vessel_id, vessel.vessel_name, vessel.captain_id,
                    vessel.max_crew_size, vessel.current_crew_count,
                    vessel.active_trip_id, vessel.created_at.isoformat()
                ))
            return True
        except Exception as e:
            logger.error(f"Failed to save vessel: {e}")
            return False
    
    def save_crew_member(self, member: CrewMember) -> bool:
        """Save crew member"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO crew_members (
                        member_id, vessel_id, user_id, first_name, last_name,
                        email, phone, role, status, hire_date, last_active,
                        emergency_contacts, certifications, medical_restrictions,
                        share_percentage, hourly_rate, notes, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    member.member_id, member.vessel_id, member.user_id,
                    member.first_name, member.last_name, member.email, member.phone,
                    member.role.value, member.status.value,
                    member.hire_date.isoformat() if member.hire_date else None,
                    member.last_active.isoformat() if member.last_active else None,
                    json.dumps(member.emergency_contacts) if member.emergency_contacts else None,
                    json.dumps(member.certifications) if member.certifications else None,
                    member.medical_restrictions, member.share_percentage, member.hourly_rate,
                    member.notes, member.created_at.isoformat(), member.updated_at.isoformat()
                ))
            return True
        except Exception as e:
            logger.error(f"Failed to save crew member: {e}")
            return False
    
    def save_invitation(self, invitation: CrewInvitation) -> bool:
        """Save crew invitation"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO crew_invitations (
                        invitation_id, vessel_id, invited_by, email, phone,
                        proposed_role, message, status, invitation_token,
                        expires_at, sent_at, responded_at, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    invitation.invitation_id, invitation.vessel_id, invitation.invited_by,
                    invitation.email, invitation.phone, invitation.proposed_role.value,
                    invitation.message, invitation.status.value, invitation.invitation_token,
                    invitation.expires_at.isoformat(), 
                    invitation.sent_at.isoformat() if invitation.sent_at else None,
                    invitation.responded_at.isoformat() if invitation.responded_at else None,
                    invitation.created_at.isoformat()
                ))
            return True
        except Exception as e:
            logger.error(f"Failed to save invitation: {e}")
            return False
    
    def get_vessel_crew(self, vessel_id: str) -> List[Dict[str, Any]]:
        """Get all crew members for vessel"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM crew_members 
                WHERE vessel_id = ? AND status != 'terminated'
                ORDER BY role, last_name
            """, (vessel_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_crew_member(self, member_id: str) -> Optional[Dict[str, Any]]:
        """Get crew member by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM crew_members WHERE member_id = ?
            """, (member_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_invitation_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Get invitation by token"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM crew_invitations WHERE invitation_token = ?
            """, (token,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_pending_invitations(self, vessel_id: str) -> List[Dict[str, Any]]:
        """Get pending invitations for vessel"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM crew_invitations 
                WHERE vessel_id = ? AND status = 'pending' AND expires_at > ?
                ORDER BY created_at DESC
            """, (vessel_id, datetime.now(timezone.utc).isoformat()))
            return [dict(row) for row in cursor.fetchall()]

class CrewManager:
    """Main crew management service"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.database = CrewDatabase(self.config.get('database_path', 'crew_management.db'))
        
        # Email configuration
        self.email_config = self.config.get('email', {})
        self.smtp_server = self.email_config.get('smtp_server')
        self.smtp_port = self.email_config.get('smtp_port', 587)
        self.smtp_username = self.email_config.get('username')
        self.smtp_password = self.email_config.get('password')
        
        # Base URL for invitation links
        self.base_url = self.config.get('base_url', 'http://localhost:8375')
    
    def create_vessel_crew(self, vessel_id: str, vessel_name: str, captain_id: str,
                          max_crew_size: int = 8) -> VesselCrew:
        """Create vessel crew configuration"""
        vessel = VesselCrew(
            vessel_id=vessel_id,
            vessel_name=vessel_name,
            captain_id=captain_id,
            max_crew_size=max_crew_size
        )
        
        success = self.database.save_vessel(vessel)
        if success:
            logger.info(f"Created vessel crew: {vessel_name} ({vessel_id})")
        else:
            logger.error(f"Failed to create vessel crew: {vessel_name}")
        
        return vessel
    
    def add_crew_member(self, vessel_id: str, first_name: str, last_name: str, 
                       email: str, role: CrewRole, **kwargs) -> CrewMember:
        """Add crew member directly (without invitation)"""
        member = CrewMember(
            member_id=str(uuid.uuid4()),
            vessel_id=vessel_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            role=role,
            hire_date=datetime.now(timezone.utc),
            **kwargs
        )
        
        success = self.database.save_crew_member(member)
        if success:
            logger.info(f"Added crew member: {member.full_name} as {role.value}")
        else:
            logger.error(f"Failed to add crew member: {member.full_name}")
        
        return member
    
    def invite_crew_member(self, vessel_id: str, inviter_id: str, email: str,
                          proposed_role: CrewRole, message: Optional[str] = None,
                          phone: Optional[str] = None) -> CrewInvitation:
        """Send crew invitation"""
        invitation = CrewInvitation(
            invitation_id=str(uuid.uuid4()),
            vessel_id=vessel_id,
            invited_by=inviter_id,
            email=email,
            phone=phone,
            proposed_role=proposed_role,
            message=message
        )
        
        success = self.database.save_invitation(invitation)
        if success:
            # Send invitation email
            self._send_invitation_email(invitation)
            
            # Update sent timestamp
            invitation.sent_at = datetime.now(timezone.utc)
            self.database.save_invitation(invitation)
            
            logger.info(f"Sent crew invitation to {email} for {proposed_role.value}")
        else:
            logger.error(f"Failed to create invitation for {email}")
        
        return invitation
    
    def accept_invitation(self, invitation_token: str, user_details: Dict[str, Any]) -> Optional[CrewMember]:
        """Accept crew invitation and create crew member"""
        invitation_data = self.database.get_invitation_by_token(invitation_token)
        if not invitation_data:
            logger.warning(f"Invalid invitation token: {invitation_token}")
            return None
        
        # Check if invitation is still valid
        expires_at = datetime.fromisoformat(invitation_data['expires_at'])
        if datetime.now(timezone.utc) > expires_at:
            logger.warning(f"Invitation expired: {invitation_token}")
            return None
        
        if invitation_data['status'] != InvitationStatus.PENDING.value:
            logger.warning(f"Invitation already processed: {invitation_token}")
            return None
        
        # Create crew member from accepted invitation
        member = CrewMember(
            member_id=str(uuid.uuid4()),
            vessel_id=invitation_data['vessel_id'],
            first_name=user_details.get('first_name', ''),
            last_name=user_details.get('last_name', ''),
            email=invitation_data['email'],
            phone=user_details.get('phone', invitation_data.get('phone', '')),
            role=CrewRole(invitation_data['proposed_role']),
            hire_date=datetime.now(timezone.utc),
            emergency_contacts=user_details.get('emergency_contacts', []),
            certifications=user_details.get('certifications', []),
            medical_restrictions=user_details.get('medical_restrictions'),
            user_id=user_details.get('user_id')
        )
        
        # Save crew member
        member_success = self.database.save_crew_member(member)
        
        if member_success:
            # Update invitation status
            invitation = CrewInvitation(
                invitation_id=invitation_data['invitation_id'],
                vessel_id=invitation_data['vessel_id'],
                invited_by=invitation_data['invited_by'],
                email=invitation_data['email'],
                phone=invitation_data['phone'],
                proposed_role=CrewRole(invitation_data['proposed_role']),
                message=invitation_data['message'],
                status=InvitationStatus.ACCEPTED,
                invitation_token=invitation_data['invitation_token'],
                expires_at=datetime.fromisoformat(invitation_data['expires_at']),
                sent_at=datetime.fromisoformat(invitation_data['sent_at']) if invitation_data['sent_at'] else None,
                responded_at=datetime.now(timezone.utc),
                created_at=datetime.fromisoformat(invitation_data['created_at'])
            )
            
            self.database.save_invitation(invitation)
            logger.info(f"Accepted invitation for {member.full_name}")
            return member
        
        return None
    
    def decline_invitation(self, invitation_token: str) -> bool:
        """Decline crew invitation"""
        invitation_data = self.database.get_invitation_by_token(invitation_token)
        if not invitation_data:
            return False
        
        invitation = CrewInvitation(
            invitation_id=invitation_data['invitation_id'],
            vessel_id=invitation_data['vessel_id'],
            invited_by=invitation_data['invited_by'],
            email=invitation_data['email'],
            phone=invitation_data['phone'],
            proposed_role=CrewRole(invitation_data['proposed_role']),
            message=invitation_data['message'],
            status=InvitationStatus.DECLINED,
            invitation_token=invitation_data['invitation_token'],
            expires_at=datetime.fromisoformat(invitation_data['expires_at']),
            sent_at=datetime.fromisoformat(invitation_data['sent_at']) if invitation_data['sent_at'] else None,
            responded_at=datetime.now(timezone.utc),
            created_at=datetime.fromisoformat(invitation_data['created_at'])
        )
        
        success = self.database.save_invitation(invitation)
        if success:
            logger.info(f"Declined invitation for {invitation_data['email']}")
        
        return success
    
    def update_crew_member(self, member_id: str, **updates) -> bool:
        """Update crew member information"""
        member_data = self.database.get_crew_member(member_id)
        if not member_data:
            return False
        
        # Update fields
        for key, value in updates.items():
            if key in member_data:
                member_data[key] = value
        
        member_data['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        # Convert back to CrewMember object
        member = self._dict_to_crew_member(member_data)
        return self.database.save_crew_member(member)
    
    def remove_crew_member(self, member_id: str, reason: str = "terminated") -> bool:
        """Remove crew member (set status to terminated)"""
        return self.update_crew_member(member_id, 
                                     status=CrewStatus.TERMINATED.value,
                                     notes=f"Removed: {reason}")
    
    def get_vessel_crew(self, vessel_id: str) -> List[Dict[str, Any]]:
        """Get all crew members for vessel"""
        return self.database.get_vessel_crew(vessel_id)
    
    def get_crew_by_role(self, vessel_id: str, role: CrewRole) -> List[Dict[str, Any]]:
        """Get crew members by role"""
        crew = self.get_vessel_crew(vessel_id)
        return [member for member in crew if member['role'] == role.value]
    
    def get_active_crew(self, vessel_id: str) -> List[Dict[str, Any]]:
        """Get active crew members for vessel"""
        crew = self.get_vessel_crew(vessel_id)
        return [member for member in crew if member['status'] == CrewStatus.ACTIVE.value]
    
    def get_crew_hierarchy(self, vessel_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get crew organized by hierarchy"""
        crew = self.get_vessel_crew(vessel_id)
        
        hierarchy = {
            'officers': [],
            'crew': [],
            'guests': []
        }
        
        for member in crew:
            role = CrewRole(member['role'])
            if role in [CrewRole.CAPTAIN, CrewRole.FIRST_MATE, CrewRole.MATE]:
                hierarchy['officers'].append(member)
            elif role == CrewRole.GUEST:
                hierarchy['guests'].append(member)
            else:
                hierarchy['crew'].append(member)
        
        return hierarchy
    
    def get_pending_invitations(self, vessel_id: str) -> List[Dict[str, Any]]:
        """Get pending invitations for vessel"""
        return self.database.get_pending_invitations(vessel_id)
    
    def _send_invitation_email(self, invitation: CrewInvitation):
        """Send invitation email"""
        if not self.smtp_server:
            logger.warning("SMTP not configured, skipping email send")
            return
        
        try:
            # Get vessel info
            vessel_crew = self.database.get_vessel_crew(invitation.vessel_id)
            captain = next((m for m in vessel_crew if m['role'] == 'captain'), None)
            
            # Create invitation link
            invitation_link = f"{self.base_url}/invite/{invitation.invitation_token}"
            
            # Create email
            msg = MimeMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = invitation.email
            msg['Subject'] = f"Crew Invitation - {invitation.proposed_role.value.title()} Position"
            
            # Email body
            body = f"""
You've been invited to join the crew!

Position: {invitation.proposed_role.value.title()}
Invited by: {captain['first_name'] if captain else 'Captain'} {captain['last_name'] if captain else ''}

{invitation.message if invitation.message else ''}

To accept or decline this invitation, click the link below:
{invitation_link}

This invitation expires on {invitation.expires_at.strftime('%B %d, %Y at %I:%M %p UTC')}.

Thank you,
FishingLog Crew Management
"""
            
            msg.attach(MimeText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                text = msg.as_string()
                server.sendmail(self.smtp_username, invitation.email, text)
            
            logger.info(f"Invitation email sent to {invitation.email}")
            
        except Exception as e:
            logger.error(f"Failed to send invitation email: {e}")
    
    def _dict_to_crew_member(self, data: Dict[str, Any]) -> CrewMember:
        """Convert dictionary to CrewMember object"""
        # Parse JSON fields
        if isinstance(data.get('emergency_contacts'), str):
            data['emergency_contacts'] = json.loads(data['emergency_contacts'])
        if isinstance(data.get('certifications'), str):
            data['certifications'] = json.loads(data['certifications'])
        
        # Parse datetime fields
        datetime_fields = ['hire_date', 'last_active', 'created_at', 'updated_at']
        for field in datetime_fields:
            if data.get(field):
                data[field] = datetime.fromisoformat(data[field])
        
        # Parse enum fields
        data['role'] = CrewRole(data['role'])
        data['status'] = CrewStatus(data['status'])
        
        return CrewMember(**data)

async def main():
    """Example usage of crew management system"""
    
    # Initialize crew manager
    crew_manager = CrewManager({
        'database_path': 'crew_management.db',
        'base_url': 'http://localhost:8375',
        'email': {
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'username': 'your-email@gmail.com',
            'password': 'your-app-password'
        }
    })
    
    print("=== Crew Management System Demo ===")
    
    # Create vessel crew
    vessel = crew_manager.create_vessel_crew(
        vessel_id="vessel_001",
        vessel_name="Sea Hunter",
        captain_id="capt_001",
        max_crew_size=6
    )
    
    print(f"Created vessel: {vessel.vessel_name}")
    
    # Add captain directly
    captain = crew_manager.add_crew_member(
        vessel_id=vessel.vessel_id,
        first_name="John",
        last_name="Smith",
        email="captain@example.com",
        role=CrewRole.CAPTAIN,
        phone="+1-555-0101",
        share_percentage=40.0,
        certifications=["Master License", "STCW"]
    )
    
    print(f"Added captain: {captain.full_name}")
    
    # Send crew invitations
    mate_invitation = crew_manager.invite_crew_member(
        vessel_id=vessel.vessel_id,
        inviter_id=captain.member_id,
        email="mate@example.com",
        proposed_role=CrewRole.FIRST_MATE,
        message="Looking forward to having you aboard for the upcoming season!",
        phone="+1-555-0102"
    )
    
    deckhand_invitation = crew_manager.invite_crew_member(
        vessel_id=vessel.vessel_id,
        inviter_id=captain.member_id,
        email="deckhand@example.com",
        proposed_role=CrewRole.DECKHAND,
        message="We need an experienced deckhand for our crew."
    )
    
    print(f"Sent invitations:")
    print(f"- Mate invitation: {mate_invitation.invitation_id}")
    print(f"- Deckhand invitation: {deckhand_invitation.invitation_id}")
    
    # Simulate accepting an invitation
    mate_member = crew_manager.accept_invitation(
        mate_invitation.invitation_token,
        {
            'first_name': 'Sarah',
            'last_name': 'Johnson',
            'phone': '+1-555-0102',
            'certifications': ['Deck Officer', 'First Aid'],
            'emergency_contacts': [
                {
                    'name': 'Mike Johnson',
                    'relationship': 'spouse',
                    'phone': '+1-555-0103',
                    'type': 'primary'
                }
            ]
        }
    )
    
    if mate_member:
        print(f"Accepted invitation: {mate_member.full_name} joined as {mate_member.role.value}")
    
    # Get vessel crew
    crew_list = crew_manager.get_vessel_crew(vessel.vessel_id)
    print(f"\nCurrent crew ({len(crew_list)} members):")
    for member in crew_list:
        print(f"- {member['first_name']} {member['last_name']}: {member['role']} ({member['status']})")
    
    # Get crew hierarchy
    hierarchy = crew_manager.get_crew_hierarchy(vessel.vessel_id)
    print(f"\nCrew hierarchy:")
    print(f"- Officers: {len(hierarchy['officers'])}")
    print(f"- Crew: {len(hierarchy['crew'])}")
    print(f"- Guests: {len(hierarchy['guests'])}")
    
    # Get pending invitations
    pending = crew_manager.get_pending_invitations(vessel.vessel_id)
    print(f"\nPending invitations: {len(pending)}")
    for inv in pending:
        print(f"- {inv['email']}: {inv['proposed_role']} (expires {inv['expires_at']})")
    
    # Update crew member
    success = crew_manager.update_crew_member(
        mate_member.member_id if mate_member else captain.member_id,
        share_percentage=25.0,
        notes="Updated share percentage"
    )
    
    if success:
        print("Updated crew member information")

if __name__ == "__main__":
    asyncio.run(main())