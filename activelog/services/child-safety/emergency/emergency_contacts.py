"""
Emergency Contact System for Child Safety

This module provides comprehensive emergency contact management and automated
response systems for child safety situations, including contact verification,
multi-channel communication, and escalation protocols.
"""

import asyncio
import asyncpg
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import hashlib
import secrets

class EmergencyLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ContactType(Enum):
    PARENT = "parent"
    GUARDIAN = "guardian"
    FAMILY_MEMBER = "family_member"
    TEACHER = "teacher"
    COUNSELOR = "counselor"
    EMERGENCY_SERVICE = "emergency_service"
    TRUSTED_ADULT = "trusted_adult"

class ContactMethod(Enum):
    PHONE = "phone"
    SMS = "sms"
    EMAIL = "email"
    APP_NOTIFICATION = "app_notification"
    EMERGENCY_APP = "emergency_app"

class EmergencyType(Enum):
    BULLYING_INCIDENT = "bullying_incident"
    INAPPROPRIATE_CONTENT = "inappropriate_content"
    STRANGER_CONTACT = "stranger_contact"
    SAFETY_CONCERN = "safety_concern"
    HEALTH_EMERGENCY = "health_emergency"
    TECHNICAL_ISSUE = "technical_issue"
    PARENTAL_CONTROLS = "parental_controls"
    SYSTEM_ALERT = "system_alert"

@dataclass
class EmergencyContact:
    contact_id: str
    user_id: str
    contact_type: ContactType
    name: str
    relationship: str
    phone_primary: Optional[str]
    phone_secondary: Optional[str]
    email: str
    preferred_contact_method: ContactMethod
    emergency_levels: List[EmergencyLevel]
    available_hours: Dict[str, Any]
    verification_code: str
    verified: bool
    active: bool
    priority_order: int
    can_authorize_overrides: bool

@dataclass
class EmergencyAlert:
    alert_id: str
    user_id: str
    emergency_type: EmergencyType
    emergency_level: EmergencyLevel
    timestamp: datetime
    description: str
    context_data: Dict[str, Any]
    auto_generated: bool
    contacts_notified: List[str]
    response_received: bool
    resolved: bool
    escalated: bool
    resolution_notes: Optional[str]

@dataclass
class ContactAttempt:
    attempt_id: str
    alert_id: str
    contact_id: str
    contact_method: ContactMethod
    timestamp: datetime
    status: str
    response_received: bool
    response_time_seconds: Optional[int]
    message_sent: str
    response_message: Optional[str]

@dataclass
class EmergencyProtocol:
    protocol_id: str
    emergency_type: EmergencyType
    emergency_level: EmergencyLevel
    contact_sequence: List[Dict[str, Any]]
    escalation_timeouts: Dict[str, int]
    auto_actions: List[str]
    required_confirmations: int
    can_auto_resolve: bool

class EmergencyContactSystem:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.active_alerts: Dict[str, EmergencyAlert] = {}
        self.contact_protocols = self._initialize_protocols()
        self.pending_verifications: Dict[str, datetime] = {}
        self.logger = logging.getLogger(__name__)
        
        # Rate limiting for contact attempts
        self.contact_rate_limits = {
            ContactMethod.SMS: timedelta(minutes=2),
            ContactMethod.PHONE: timedelta(minutes=5),
            ContactMethod.EMAIL: timedelta(minutes=1),
            ContactMethod.APP_NOTIFICATION: timedelta(seconds=30)
        }
        
        # Emergency service contacts (would be configured per region)
        self.emergency_services = {
            "police": {"phone": "911", "sms": None},
            "child_protection": {"phone": "1-800-4-A-CHILD", "sms": None},
            "crisis_text": {"phone": None, "sms": "HOME to 741741"}
        }

    def _initialize_protocols(self) -> Dict[str, EmergencyProtocol]:
        """Initialize emergency response protocols"""
        
        protocols = {}
        
        # Bullying incident protocol
        protocols["bullying_incident"] = EmergencyProtocol(
            protocol_id="bullying_incident",
            emergency_type=EmergencyType.BULLYING_INCIDENT,
            emergency_level=EmergencyLevel.HIGH,
            contact_sequence=[
                {"contact_types": [ContactType.PARENT, ContactType.GUARDIAN], "delay_seconds": 0},
                {"contact_types": [ContactType.TEACHER, ContactType.COUNSELOR], "delay_seconds": 300},
                {"contact_types": [ContactType.TRUSTED_ADULT], "delay_seconds": 600}
            ],
            escalation_timeouts={"parent_response": 900, "authority_escalation": 1800},
            auto_actions=["document_incident", "preserve_evidence", "block_perpetrator"],
            required_confirmations=1,
            can_auto_resolve=False
        )
        
        # Inappropriate content protocol
        protocols["inappropriate_content"] = EmergencyProtocol(
            protocol_id="inappropriate_content",
            emergency_type=EmergencyType.INAPPROPRIATE_CONTENT,
            emergency_level=EmergencyLevel.MEDIUM,
            contact_sequence=[
                {"contact_types": [ContactType.PARENT, ContactType.GUARDIAN], "delay_seconds": 0}
            ],
            escalation_timeouts={"parent_response": 3600},
            auto_actions=["block_content", "document_incident", "update_filters"],
            required_confirmations=1,
            can_auto_resolve=True
        )
        
        # Stranger contact protocol
        protocols["stranger_contact"] = EmergencyProtocol(
            protocol_id="stranger_contact",
            emergency_type=EmergencyType.STRANGER_CONTACT,
            emergency_level=EmergencyLevel.CRITICAL,
            contact_sequence=[
                {"contact_types": [ContactType.PARENT, ContactType.GUARDIAN], "delay_seconds": 0},
                {"contact_types": [ContactType.EMERGENCY_SERVICE], "delay_seconds": 300}
            ],
            escalation_timeouts={"immediate_response": 180, "authority_escalation": 600},
            auto_actions=["block_contact", "preserve_evidence", "location_tracking"],
            required_confirmations=2,
            can_auto_resolve=False
        )
        
        # Health emergency protocol
        protocols["health_emergency"] = EmergencyProtocol(
            protocol_id="health_emergency",
            emergency_type=EmergencyType.HEALTH_EMERGENCY,
            emergency_level=EmergencyLevel.CRITICAL,
            contact_sequence=[
                {"contact_types": [ContactType.PARENT, ContactType.GUARDIAN], "delay_seconds": 0},
                {"contact_types": [ContactType.EMERGENCY_SERVICE], "delay_seconds": 120}
            ],
            escalation_timeouts={"immediate_response": 60, "emergency_services": 300},
            auto_actions=["preserve_health_data", "location_sharing", "emergency_override"],
            required_confirmations=1,
            can_auto_resolve=False
        )
        
        return protocols

    async def initialize_database(self):
        """Initialize database tables for emergency contact system"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS emergency_contacts (
                    contact_id VARCHAR PRIMARY KEY,
                    user_id VARCHAR NOT NULL,
                    contact_type VARCHAR NOT NULL,
                    name VARCHAR NOT NULL,
                    relationship VARCHAR NOT NULL,
                    phone_primary VARCHAR,
                    phone_secondary VARCHAR,
                    email VARCHAR NOT NULL,
                    preferred_contact_method VARCHAR NOT NULL,
                    emergency_levels JSONB NOT NULL,
                    available_hours JSONB NOT NULL DEFAULT '{}',
                    verification_code VARCHAR NOT NULL,
                    verified BOOLEAN DEFAULT FALSE,
                    active BOOLEAN DEFAULT TRUE,
                    priority_order INTEGER NOT NULL DEFAULT 1,
                    can_authorize_overrides BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS emergency_alerts (
                    alert_id VARCHAR PRIMARY KEY,
                    user_id VARCHAR NOT NULL,
                    emergency_type VARCHAR NOT NULL,
                    emergency_level VARCHAR NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    description TEXT NOT NULL,
                    context_data JSONB NOT NULL DEFAULT '{}',
                    auto_generated BOOLEAN DEFAULT TRUE,
                    contacts_notified JSONB NOT NULL DEFAULT '[]',
                    response_received BOOLEAN DEFAULT FALSE,
                    resolved BOOLEAN DEFAULT FALSE,
                    escalated BOOLEAN DEFAULT FALSE,
                    resolution_notes TEXT,
                    resolved_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES emergency_contacts(user_id)
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS contact_attempts (
                    attempt_id VARCHAR PRIMARY KEY,
                    alert_id VARCHAR NOT NULL,
                    contact_id VARCHAR NOT NULL,
                    contact_method VARCHAR NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    status VARCHAR NOT NULL,
                    response_received BOOLEAN DEFAULT FALSE,
                    response_time_seconds INTEGER,
                    message_sent TEXT NOT NULL,
                    response_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (alert_id) REFERENCES emergency_alerts(alert_id),
                    FOREIGN KEY (contact_id) REFERENCES emergency_contacts(contact_id)
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS emergency_protocols (
                    protocol_id VARCHAR PRIMARY KEY,
                    emergency_type VARCHAR NOT NULL,
                    emergency_level VARCHAR NOT NULL,
                    contact_sequence JSONB NOT NULL,
                    escalation_timeouts JSONB NOT NULL,
                    auto_actions JSONB NOT NULL DEFAULT '[]',
                    required_confirmations INTEGER DEFAULT 1,
                    can_auto_resolve BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    async def add_emergency_contact(self, user_id: str, contact_type: ContactType,
                                  name: str, relationship: str, email: str,
                                  phone_primary: Optional[str] = None,
                                  phone_secondary: Optional[str] = None,
                                  preferred_method: ContactMethod = ContactMethod.EMAIL,
                                  emergency_levels: List[EmergencyLevel] = None,
                                  can_authorize: bool = False) -> str:
        """Add a new emergency contact for a user"""
        
        if emergency_levels is None:
            emergency_levels = [EmergencyLevel.MEDIUM, EmergencyLevel.HIGH, EmergencyLevel.CRITICAL]
        
        contact_id = f"contact_{user_id}_{int(datetime.now().timestamp())}"
        verification_code = secrets.token_hex(8)
        
        contact = EmergencyContact(
            contact_id=contact_id,
            user_id=user_id,
            contact_type=contact_type,
            name=name,
            relationship=relationship,
            phone_primary=phone_primary,
            phone_secondary=phone_secondary,
            email=email,
            preferred_contact_method=preferred_method,
            emergency_levels=emergency_levels,
            available_hours={"always": True},  # Default to always available
            verification_code=verification_code,
            verified=False,
            active=True,
            priority_order=1,
            can_authorize_overrides=can_authorize
        )
        
        # Store contact
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO emergency_contacts 
                (contact_id, user_id, contact_type, name, relationship,
                 phone_primary, phone_secondary, email, preferred_contact_method,
                 emergency_levels, available_hours, verification_code, 
                 can_authorize_overrides)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            """, contact_id, user_id, contact_type.value, name, relationship,
                phone_primary, phone_secondary, email, preferred_method.value,
                json.dumps([level.value for level in emergency_levels]),
                json.dumps(contact.available_hours), verification_code, can_authorize
            )
        
        # Send verification request
        await self._send_verification_request(contact)
        
        self.logger.info(f"Added emergency contact {contact_id} for user {user_id}")
        return contact_id

    async def verify_contact(self, contact_id: str, verification_code: str) -> bool:
        """Verify an emergency contact using verification code"""
        
        async with self.db_pool.acquire() as conn:
            contact_data = await conn.fetchrow("""
                SELECT verification_code, verified FROM emergency_contacts
                WHERE contact_id = $1
            """, contact_id)
        
        if not contact_data:
            return False
        
        if contact_data["verified"]:
            return True  # Already verified
        
        if contact_data["verification_code"] == verification_code:
            # Mark as verified
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    UPDATE emergency_contacts 
                    SET verified = TRUE, updated_at = CURRENT_TIMESTAMP
                    WHERE contact_id = $1
                """, contact_id)
            
            self.logger.info(f"Emergency contact {contact_id} verified successfully")
            return True
        
        return False

    async def trigger_emergency_alert(self, user_id: str, emergency_type: EmergencyType,
                                    emergency_level: EmergencyLevel, description: str,
                                    context_data: Dict[str, Any] = None,
                                    auto_generated: bool = True) -> str:
        """Trigger an emergency alert and initiate contact protocol"""
        
        if context_data is None:
            context_data = {}
        
        alert_id = f"alert_{user_id}_{emergency_type.value}_{int(datetime.now().timestamp())}"
        
        alert = EmergencyAlert(
            alert_id=alert_id,
            user_id=user_id,
            emergency_type=emergency_type,
            emergency_level=emergency_level,
            timestamp=datetime.now(),
            description=description,
            context_data=context_data,
            auto_generated=auto_generated,
            contacts_notified=[],
            response_received=False,
            resolved=False,
            escalated=False,
            resolution_notes=None
        )
        
        # Store alert
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO emergency_alerts 
                (alert_id, user_id, emergency_type, emergency_level, timestamp,
                 description, context_data, auto_generated)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, alert_id, user_id, emergency_type.value, emergency_level.value,
                alert.timestamp, description, json.dumps(context_data), auto_generated
            )
        
        self.active_alerts[alert_id] = alert
        
        # Execute emergency protocol
        await self._execute_emergency_protocol(alert)
        
        self.logger.critical(f"Emergency alert triggered: {alert_id} - {emergency_type.value}")
        return alert_id

    async def _execute_emergency_protocol(self, alert: EmergencyAlert):
        """Execute the emergency response protocol for an alert"""
        
        protocol_key = alert.emergency_type.value
        if protocol_key not in self.contact_protocols:
            # Use default protocol
            await self._execute_default_protocol(alert)
            return
        
        protocol = self.contact_protocols[protocol_key]
        
        # Execute auto actions first
        await self._execute_auto_actions(alert, protocol.auto_actions)
        
        # Start contact sequence
        await self._execute_contact_sequence(alert, protocol)
        
        # Schedule escalation if needed
        if alert.emergency_level in [EmergencyLevel.HIGH, EmergencyLevel.CRITICAL]:
            asyncio.create_task(self._schedule_escalation(alert, protocol))

    async def _execute_auto_actions(self, alert: EmergencyAlert, auto_actions: List[str]):
        """Execute automated actions for an emergency alert"""
        
        for action in auto_actions:
            try:
                if action == "block_content":
                    await self._block_harmful_content(alert)
                elif action == "block_contact":
                    await self._block_suspicious_contact(alert)
                elif action == "document_incident":
                    await self._document_incident(alert)
                elif action == "preserve_evidence":
                    await self._preserve_evidence(alert)
                elif action == "location_tracking":
                    await self._enable_location_tracking(alert)
                elif action == "emergency_override":
                    await self._enable_emergency_override(alert)
                elif action == "update_filters":
                    await self._update_content_filters(alert)
                
                self.logger.info(f"Executed auto action: {action} for alert {alert.alert_id}")
                
            except Exception as e:
                self.logger.error(f"Failed to execute auto action {action}: {e}")

    async def _execute_contact_sequence(self, alert: EmergencyAlert, protocol: EmergencyProtocol):
        """Execute the contact sequence for an emergency protocol"""
        
        # Get user's emergency contacts
        contacts = await self._get_emergency_contacts(alert.user_id, alert.emergency_level)
        
        for sequence_step in protocol.contact_sequence:
            # Wait for specified delay
            delay_seconds = sequence_step.get("delay_seconds", 0)
            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)
            
            # Contact appropriate contact types
            target_types = sequence_step["contact_types"]
            relevant_contacts = [
                c for c in contacts 
                if ContactType(c["contact_type"]) in target_types
            ]
            
            if relevant_contacts:
                # Contact in parallel
                contact_tasks = []
                for contact in relevant_contacts:
                    task = asyncio.create_task(self._attempt_contact(alert, contact))
                    contact_tasks.append(task)
                
                # Wait for all contact attempts
                if contact_tasks:
                    await asyncio.gather(*contact_tasks, return_exceptions=True)
                
                # Check if we got a response
                if alert.response_received:
                    break

    async def _attempt_contact(self, alert: EmergencyAlert, contact: Dict[str, Any]) -> ContactAttempt:
        """Attempt to contact an emergency contact"""
        
        attempt_id = f"attempt_{alert.alert_id}_{contact['contact_id']}_{int(datetime.now().timestamp())}"
        
        # Determine contact method
        preferred_method = ContactMethod(contact["preferred_contact_method"])
        
        # Check rate limiting
        if not await self._check_rate_limit(contact["contact_id"], preferred_method):
            self.logger.warning(f"Rate limit exceeded for contact {contact['contact_id']}")
            return None
        
        # Prepare message
        message = await self._prepare_emergency_message(alert, contact)
        
        attempt = ContactAttempt(
            attempt_id=attempt_id,
            alert_id=alert.alert_id,
            contact_id=contact["contact_id"],
            contact_method=preferred_method,
            timestamp=datetime.now(),
            status="sending",
            response_received=False,
            response_time_seconds=None,
            message_sent=message,
            response_message=None
        )
        
        # Store attempt
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO contact_attempts 
                (attempt_id, alert_id, contact_id, contact_method, timestamp,
                 status, message_sent)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, attempt_id, alert.alert_id, contact["contact_id"],
                preferred_method.value, attempt.timestamp, "sending", message
            )
        
        # Send message
        success = await self._send_emergency_message(contact, preferred_method, message)
        
        # Update attempt status
        status = "sent" if success else "failed"
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE contact_attempts 
                SET status = $1
                WHERE attempt_id = $2
            """, status, attempt_id)
        
        attempt.status = status
        
        if success:
            # Add to notified contacts
            alert.contacts_notified.append(contact["contact_id"])
            
            # Update alert
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    UPDATE emergency_alerts 
                    SET contacts_notified = $1
                    WHERE alert_id = $2
                """, json.dumps(alert.contacts_notified), alert.alert_id)
        
        self.logger.info(f"Contact attempt {attempt_id}: {status}")
        return attempt

    async def _prepare_emergency_message(self, alert: EmergencyAlert, contact: Dict[str, Any]) -> str:
        """Prepare emergency message for a contact"""
        
        contact_name = contact["name"]
        child_relationship = contact["relationship"]
        
        # Base message templates by emergency type
        message_templates = {
            EmergencyType.BULLYING_INCIDENT: f"""
URGENT - Child Safety Alert

Hello {contact_name},

This is an automated message from the child safety monitoring system. 
We've detected a potential bullying incident involving your {child_relationship}.

Incident Details:
- Time: {alert.timestamp.strftime('%Y-%m-%d at %I:%M %p')}
- Type: Bullying Detection
- Description: {alert.description}

Immediate actions taken:
- Incident documented
- Harmful contact blocked
- Evidence preserved

Please respond immediately to acknowledge receipt and take appropriate action.
Reply with "RECEIVED" to confirm.

For urgent matters, call our safety hotline: 1-800-CHILD-SAFE
            """.strip(),
            
            EmergencyType.INAPPROPRIATE_CONTENT: f"""
Child Safety Alert

Hello {contact_name},

Your {child_relationship} has encountered inappropriate content that was blocked by our safety filters.

Details:
- Time: {alert.timestamp.strftime('%Y-%m-%d at %I:%M %p')}
- Description: {alert.description}

Actions taken:
- Content blocked immediately
- Incident logged for review
- Filters updated

Please review this incident with your child and reply "ACKNOWLEDGED" to confirm.
            """.strip(),
            
            EmergencyType.STRANGER_CONTACT: f"""
CRITICAL - Child Safety Emergency

IMMEDIATE ACTION REQUIRED

Hello {contact_name},

We've detected suspicious stranger contact with your {child_relationship}.

URGENT Details:
- Time: {alert.timestamp.strftime('%Y-%m-%d at %I:%M %p')}
- Description: {alert.description}

Emergency actions taken:
- Contact blocked immediately
- Evidence preserved
- Location tracking enabled

PLEASE RESPOND IMMEDIATELY or call emergency services if needed.
Reply "URGENT RECEIVED" to confirm.

Emergency Hotline: 1-800-CHILD-SAFE
            """.strip()
        }
        
        # Get template or create default
        message = message_templates.get(alert.emergency_type, f"""
Child Safety Alert

Hello {contact_name},

This is an automated safety alert regarding your {child_relationship}.

Details:
- Time: {alert.timestamp.strftime('%Y-%m-%d at %I:%M %p')}
- Type: {alert.emergency_type.value.replace('_', ' ').title()}
- Description: {alert.description}

Please respond to acknowledge receipt.
        """.strip())
        
        return message

    async def _send_emergency_message(self, contact: Dict[str, Any], 
                                    method: ContactMethod, message: str) -> bool:
        """Send emergency message via specified method"""
        
        try:
            if method == ContactMethod.EMAIL:
                return await self._send_email(contact["email"], "Child Safety Emergency Alert", message)
            elif method == ContactMethod.SMS:
                phone = contact["phone_primary"] or contact["phone_secondary"]
                if phone:
                    return await self._send_sms(phone, message)
            elif method == ContactMethod.PHONE:
                phone = contact["phone_primary"] or contact["phone_secondary"]
                if phone:
                    return await self._make_phone_call(phone, message)
            elif method == ContactMethod.APP_NOTIFICATION:
                return await self._send_app_notification(contact["contact_id"], message)
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to send emergency message via {method.value}: {e}")
            return False

    async def _send_email(self, email: str, subject: str, message: str) -> bool:
        """Send emergency email (mock implementation)"""
        # In production, integrate with email service
        self.logger.info(f"Sending emergency email to {email}: {subject}")
        await asyncio.sleep(0.1)  # Simulate sending
        return True

    async def _send_sms(self, phone: str, message: str) -> bool:
        """Send emergency SMS (mock implementation)"""
        # In production, integrate with SMS service
        self.logger.info(f"Sending emergency SMS to {phone}")
        await asyncio.sleep(0.1)  # Simulate sending
        return True

    async def _make_phone_call(self, phone: str, message: str) -> bool:
        """Make emergency phone call (mock implementation)"""
        # In production, integrate with voice call service
        self.logger.info(f"Making emergency call to {phone}")
        await asyncio.sleep(0.1)  # Simulate calling
        return True

    async def _send_app_notification(self, contact_id: str, message: str) -> bool:
        """Send app notification (mock implementation)"""
        # In production, integrate with push notification service
        self.logger.info(f"Sending app notification to {contact_id}")
        await asyncio.sleep(0.1)  # Simulate sending
        return True

    async def _send_verification_request(self, contact: EmergencyContact):
        """Send verification request to new contact"""
        
        message = f"""
Child Safety System - Contact Verification

Hello {contact.name},

You've been added as an emergency contact for child safety monitoring.

Your verification code is: {contact.verification_code}

Please verify your contact information by responding with this code.
This ensures we can reach you in case of emergencies.

If you did not expect this message, please contact support immediately.
        """.strip()
        
        # Send via preferred method
        await self._send_emergency_message(
            {
                "email": contact.email,
                "phone_primary": contact.phone_primary,
                "phone_secondary": contact.phone_secondary,
                "contact_id": contact.contact_id
            },
            contact.preferred_contact_method,
            message
        )

    async def _get_emergency_contacts(self, user_id: str, emergency_level: EmergencyLevel) -> List[Dict]:
        """Get emergency contacts for a user filtered by emergency level"""
        
        async with self.db_pool.acquire() as conn:
            contacts = await conn.fetch("""
                SELECT * FROM emergency_contacts
                WHERE user_id = $1 AND verified = TRUE AND active = TRUE
                AND emergency_levels::jsonb ? $2
                ORDER BY priority_order ASC
            """, user_id, emergency_level.value)
        
        return [dict(contact) for contact in contacts]

    async def _check_rate_limit(self, contact_id: str, method: ContactMethod) -> bool:
        """Check if contact method is within rate limits"""
        
        # Simple in-memory rate limiting (in production, use Redis)
        rate_key = f"{contact_id}_{method.value}"
        now = datetime.now()
        limit = self.contact_rate_limits.get(method, timedelta(minutes=1))
        
        if rate_key in self.pending_verifications:
            last_contact = self.pending_verifications[rate_key]
            if now - last_contact < limit:
                return False
        
        self.pending_verifications[rate_key] = now
        return True

    async def _schedule_escalation(self, alert: EmergencyAlert, protocol: EmergencyProtocol):
        """Schedule escalation if no response received"""
        
        escalation_timeout = protocol.escalation_timeouts.get("parent_response", 1800)  # 30 minutes default
        
        await asyncio.sleep(escalation_timeout)
        
        # Check if alert is still active and no response received
        if alert.alert_id in self.active_alerts and not alert.response_received:
            await self._escalate_alert(alert)

    async def _escalate_alert(self, alert: EmergencyAlert):
        """Escalate an emergency alert to higher authorities"""
        
        alert.escalated = True
        
        # Update database
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE emergency_alerts 
                SET escalated = TRUE
                WHERE alert_id = $1
            """, alert.alert_id)
        
        # Contact emergency services if critical
        if alert.emergency_level == EmergencyLevel.CRITICAL:
            await self._contact_emergency_services(alert)
        
        self.logger.critical(f"Alert escalated: {alert.alert_id}")

    async def _contact_emergency_services(self, alert: EmergencyAlert):
        """Contact appropriate emergency services"""
        
        # Determine which service to contact
        service_type = None
        if alert.emergency_type == EmergencyType.HEALTH_EMERGENCY:
            service_type = "police"  # Or medical services
        elif alert.emergency_type in [EmergencyType.STRANGER_CONTACT, EmergencyType.SAFETY_CONCERN]:
            service_type = "police"
        elif alert.emergency_type == EmergencyType.BULLYING_INCIDENT:
            service_type = "child_protection"
        
        if service_type and service_type in self.emergency_services:
            service_info = self.emergency_services[service_type]
            
            # Log the emergency service contact (in production, actually contact them)
            self.logger.critical(f"EMERGENCY SERVICE CONTACT: {service_type} - Alert: {alert.alert_id}")
            
            # In production, this would make actual emergency calls/notifications

    async def respond_to_alert(self, alert_id: str, contact_id: str, response_message: str) -> bool:
        """Process response from an emergency contact"""
        
        if alert_id not in self.active_alerts:
            return False
        
        alert = self.active_alerts[alert_id]
        response_time = datetime.now()
        
        # Update alert
        alert.response_received = True
        
        # Find the contact attempt to update
        async with self.db_pool.acquire() as conn:
            # Update contact attempt
            await conn.execute("""
                UPDATE contact_attempts 
                SET response_received = TRUE, 
                    response_time_seconds = EXTRACT(EPOCH FROM ($1 - timestamp))::INTEGER,
                    response_message = $2
                WHERE alert_id = $3 AND contact_id = $4
                ORDER BY timestamp DESC LIMIT 1
            """, response_time, response_message, alert_id, contact_id)
            
            # Update alert
            await conn.execute("""
                UPDATE emergency_alerts 
                SET response_received = TRUE
                WHERE alert_id = $1
            """, alert_id)
        
        # Check if response indicates resolution
        if any(keyword in response_message.upper() for keyword in ["RESOLVED", "HANDLED", "SAFE", "OK"]):
            await self.resolve_alert(alert_id, f"Resolved by contact response: {response_message}")
        
        self.logger.info(f"Received response for alert {alert_id} from contact {contact_id}")
        return True

    async def resolve_alert(self, alert_id: str, resolution_notes: str) -> bool:
        """Resolve an emergency alert"""
        
        if alert_id not in self.active_alerts:
            return False
        
        alert = self.active_alerts[alert_id]
        alert.resolved = True
        alert.resolution_notes = resolution_notes
        
        # Update database
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE emergency_alerts 
                SET resolved = TRUE, resolution_notes = $1, resolved_at = CURRENT_TIMESTAMP
                WHERE alert_id = $2
            """, resolution_notes, alert_id)
        
        # Remove from active alerts
        del self.active_alerts[alert_id]
        
        self.logger.info(f"Resolved emergency alert: {alert_id}")
        return True

    async def get_emergency_dashboard(self, user_id: str) -> Dict[str, Any]:
        """Generate emergency system dashboard for a user"""
        
        async with self.db_pool.acquire() as conn:
            # Get contact summary
            contacts = await conn.fetch("""
                SELECT contact_type, verified, active, COUNT(*) as count
                FROM emergency_contacts
                WHERE user_id = $1
                GROUP BY contact_type, verified, active
            """, user_id)
            
            # Get recent alerts
            recent_alerts = await conn.fetch("""
                SELECT * FROM emergency_alerts
                WHERE user_id = $1
                ORDER BY timestamp DESC LIMIT 5
            """, user_id)
            
            # Get response statistics
            response_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_attempts,
                    COUNT(CASE WHEN response_received THEN 1 END) as responses_received,
                    AVG(response_time_seconds) as avg_response_time
                FROM contact_attempts ca
                JOIN emergency_alerts ea ON ca.alert_id = ea.alert_id
                WHERE ea.user_id = $1
                AND ca.timestamp > CURRENT_DATE - INTERVAL '30 days'
            """, user_id)
        
        # Process contact data
        contact_summary = {}
        total_contacts = 0
        verified_contacts = 0
        
        for row in contacts:
            contact_type = row["contact_type"]
            if contact_type not in contact_summary:
                contact_summary[contact_type] = {"total": 0, "verified": 0, "active": 0}
            
            count = row["count"]
            contact_summary[contact_type]["total"] += count
            total_contacts += count
            
            if row["verified"]:
                contact_summary[contact_type]["verified"] += count
                verified_contacts += count
            
            if row["active"]:
                contact_summary[contact_type]["active"] += count
        
        dashboard = {
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "emergency_contacts": {
                "total": total_contacts,
                "verified": verified_contacts,
                "verification_rate": (verified_contacts / max(1, total_contacts)) * 100,
                "by_type": contact_summary
            },
            "recent_alerts": [dict(alert) for alert in recent_alerts],
            "response_performance": {
                "total_attempts": response_stats["total_attempts"] if response_stats else 0,
                "response_rate": ((response_stats["responses_received"] or 0) / max(1, response_stats["total_attempts"] or 1)) * 100,
                "average_response_time_minutes": (response_stats["avg_response_time"] or 0) / 60
            },
            "system_status": {
                "status": "Active" if verified_contacts > 0 else "Setup Required",
                "coverage": "Full" if verified_contacts >= 2 else "Partial" if verified_contacts >= 1 else "None",
                "recommendations": self._generate_emergency_recommendations(verified_contacts, contact_summary)
            }
        }
        
        return dashboard

    def _generate_emergency_recommendations(self, verified_contacts: int, contact_summary: Dict) -> List[str]:
        """Generate recommendations for emergency contact setup"""
        
        recommendations = []
        
        if verified_contacts == 0:
            recommendations.append("Add and verify at least one emergency contact")
        elif verified_contacts == 1:
            recommendations.append("Add a backup emergency contact for redundancy")
        
        if ContactType.PARENT.value not in contact_summary and ContactType.GUARDIAN.value not in contact_summary:
            recommendations.append("Add a parent or guardian as primary emergency contact")
        
        if not any(ContactType.TEACHER.value in contact_summary or ContactType.COUNSELOR.value in contact_summary):
            recommendations.append("Consider adding a teacher or counselor for school-related incidents")
        
        if not recommendations:
            recommendations.append("Emergency contact system is properly configured")
        
        return recommendations

    # Mock implementations for auto actions
    async def _block_harmful_content(self, alert: EmergencyAlert):
        """Block harmful content identified in alert"""
        self.logger.info(f"Blocking harmful content for alert {alert.alert_id}")

    async def _block_suspicious_contact(self, alert: EmergencyAlert):
        """Block suspicious contact identified in alert"""
        self.logger.info(f"Blocking suspicious contact for alert {alert.alert_id}")

    async def _document_incident(self, alert: EmergencyAlert):
        """Document incident for future reference"""
        self.logger.info(f"Documenting incident for alert {alert.alert_id}")

    async def _preserve_evidence(self, alert: EmergencyAlert):
        """Preserve digital evidence related to alert"""
        self.logger.info(f"Preserving evidence for alert {alert.alert_id}")

    async def _enable_location_tracking(self, alert: EmergencyAlert):
        """Enable location tracking for safety"""
        self.logger.info(f"Enabling location tracking for alert {alert.alert_id}")

    async def _enable_emergency_override(self, alert: EmergencyAlert):
        """Enable emergency override mode"""
        self.logger.info(f"Enabling emergency override for alert {alert.alert_id}")

    async def _update_content_filters(self, alert: EmergencyAlert):
        """Update content filters based on incident"""
        self.logger.info(f"Updating content filters for alert {alert.alert_id}")

    async def _execute_default_protocol(self, alert: EmergencyAlert):
        """Execute default emergency protocol"""
        # Simple default: contact all verified emergency contacts
        contacts = await self._get_emergency_contacts(alert.user_id, alert.emergency_level)
        
        for contact in contacts:
            await self._attempt_contact(alert, contact)