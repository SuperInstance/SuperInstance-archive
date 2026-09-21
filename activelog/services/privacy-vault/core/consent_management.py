import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from ..models.privacy_models import (
    ConsentRecord, ConsentType, ProcessingPurpose, DataCategory, 
    LegalBasis
)
import logging
import uuid

logger = logging.getLogger(__name__)

class ConsentManager:
    def __init__(self):
        self.consent_records: Dict[str, ConsentRecord] = {}
        self.user_consents: Dict[str, List[str]] = {}  # user_id -> [consent_ids]
        self.purpose_mappings: Dict[ProcessingPurpose, List[DataCategory]] = {}
        self.consent_templates: Dict[str, Dict] = {}
        self.withdrawal_requests: Dict[str, Dict] = {}
        self.consent_history: Dict[str, List[Dict]] = {}
        self.expiry_notifications: List[Dict] = []
        
        # Initialize consent framework
        asyncio.create_task(self._initialize_consent_templates())
        asyncio.create_task(self._initialize_purpose_mappings())
    
    async def _initialize_consent_templates(self):
        """Initialize consent templates for different purposes"""
        self.consent_templates = {
            "service_provision": {
                "purpose": ProcessingPurpose.SERVICE_PROVISION,
                "legal_basis": LegalBasis.CONTRACT,
                "required_data_categories": [
                    DataCategory.PERSONAL_DATA
                ],
                "optional_data_categories": [
                    DataCategory.COMMUNICATION_DATA
                ],
                "default_expiry_months": 24,
                "consent_text": """
                We process your personal data to provide our services to you. 
                This includes your account information and communication preferences.
                """,
                "withdrawal_impact": "Service functionality may be limited"
            },
            "marketing": {
                "purpose": ProcessingPurpose.MARKETING,
                "legal_basis": LegalBasis.CONSENT,
                "required_data_categories": [],
                "optional_data_categories": [
                    DataCategory.PERSONAL_DATA,
                    DataCategory.BEHAVIORAL_DATA,
                    DataCategory.COMMUNICATION_DATA
                ],
                "default_expiry_months": 12,
                "consent_text": """
                We would like to use your data to send you marketing communications 
                and personalized offers that may be of interest to you.
                """,
                "withdrawal_impact": "You will not receive marketing communications"
            },
            "analytics": {
                "purpose": ProcessingPurpose.ANALYTICS,
                "legal_basis": LegalBasis.LEGITIMATE_INTERESTS,
                "required_data_categories": [],
                "optional_data_categories": [
                    DataCategory.BEHAVIORAL_DATA,
                    DataCategory.LOCATION_DATA
                ],
                "default_expiry_months": 36,
                "consent_text": """
                We analyze usage patterns to improve our services and user experience. 
                This data is processed in aggregate form.
                """,
                "withdrawal_impact": "Service improvements may be less relevant to you"
            },
            "research": {
                "purpose": ProcessingPurpose.RESEARCH,
                "legal_basis": LegalBasis.CONSENT,
                "required_data_categories": [],
                "optional_data_categories": [
                    DataCategory.BEHAVIORAL_DATA,
                    DataCategory.PERSONAL_DATA
                ],
                "default_expiry_months": 60,
                "consent_text": """
                Your data may be used for research purposes to advance scientific 
                understanding and improve services for all users.
                """,
                "withdrawal_impact": "You will not participate in research studies"
            },
            "health_data": {
                "purpose": ProcessingPurpose.SERVICE_PROVISION,
                "legal_basis": LegalBasis.CONSENT,
                "required_data_categories": [
                    DataCategory.HEALTH_DATA
                ],
                "optional_data_categories": [],
                "default_expiry_months": 12,
                "consent_text": """
                We will process your health data to provide healthcare services. 
                This includes medical records and treatment information.
                """,
                "withdrawal_impact": "Healthcare services may not be available",
                "special_category": True,
                "explicit_consent_required": True
            }
        }
    
    async def _initialize_purpose_mappings(self):
        """Initialize mappings between purposes and data categories"""
        self.purpose_mappings = {
            ProcessingPurpose.SERVICE_PROVISION: [
                DataCategory.PERSONAL_DATA,
                DataCategory.COMMUNICATION_DATA
            ],
            ProcessingPurpose.ANALYTICS: [
                DataCategory.BEHAVIORAL_DATA,
                DataCategory.LOCATION_DATA
            ],
            ProcessingPurpose.MARKETING: [
                DataCategory.PERSONAL_DATA,
                DataCategory.BEHAVIORAL_DATA,
                DataCategory.COMMUNICATION_DATA
            ],
            ProcessingPurpose.RESEARCH: [
                DataCategory.BEHAVIORAL_DATA,
                DataCategory.PERSONAL_DATA
            ],
            ProcessingPurpose.SECURITY: [
                DataCategory.PERSONAL_DATA,
                DataCategory.BEHAVIORAL_DATA,
                DataCategory.LOCATION_DATA
            ],
            ProcessingPurpose.LEGAL_COMPLIANCE: [
                DataCategory.PERSONAL_DATA,
                DataCategory.FINANCIAL_DATA
            ],
            ProcessingPurpose.CUSTOMER_SUPPORT: [
                DataCategory.PERSONAL_DATA,
                DataCategory.COMMUNICATION_DATA
            ]
        }
    
    async def record_consent(
        self,
        user_id: str,
        purpose: ProcessingPurpose,
        data_categories: List[DataCategory],
        consent_type: ConsentType,
        expiry_date: Optional[datetime] = None,
        granular_permissions: Optional[Dict[str, bool]] = None
    ) -> ConsentRecord:
        """Record user consent"""
        try:
            consent_id = f"consent_{user_id}_{purpose.value}_{int(datetime.utcnow().timestamp())}"
            
            # Get consent template if available
            template = self.consent_templates.get(purpose.value, {})
            
            # Set default expiry if not provided
            if not expiry_date and template:
                expiry_months = template.get("default_expiry_months", 12)
                expiry_date = datetime.utcnow() + timedelta(days=30 * expiry_months)
            
            # Validate consent requirements
            validation_result = await self._validate_consent_request(
                purpose, data_categories, consent_type, template
            )
            
            if not validation_result["valid"]:
                raise ValueError(f"Invalid consent: {validation_result['errors']}")
            
            # Create granular permissions if not provided
            if not granular_permissions:
                granular_permissions = await self._create_default_permissions(
                    purpose, data_categories
                )
            
            # Get consent text
            consent_text = template.get("consent_text", 
                f"Consent for {purpose.value} processing of {', '.join([cat.value for cat in data_categories])}"
            )
            
            # Create consent record
            consent_record = ConsentRecord(
                consent_id=consent_id,
                user_id=user_id,
                purpose=purpose,
                data_categories=data_categories,
                consent_type=consent_type,
                legal_basis=template.get("legal_basis", LegalBasis.CONSENT),
                granted_at=datetime.utcnow(),
                expires_at=expiry_date,
                withdrawn_at=None,
                granular_permissions=granular_permissions,
                consent_text=consent_text,
                version="1.0",
                is_active=True
            )
            
            # Store consent record
            self.consent_records[consent_id] = consent_record
            
            # Update user consent mapping
            if user_id not in self.user_consents:
                self.user_consents[user_id] = []
            self.user_consents[user_id].append(consent_id)
            
            # Record consent history
            await self._record_consent_history(user_id, consent_id, "granted", {
                "purpose": purpose.value,
                "data_categories": [cat.value for cat in data_categories],
                "consent_type": consent_type.value
            })
            
            # Schedule expiry notification if applicable
            if expiry_date:
                await self._schedule_expiry_notification(consent_id, expiry_date)
            
            logger.info(f"Recorded consent: {consent_id} for user {user_id}")
            return consent_record
            
        except Exception as e:
            logger.error(f"Consent recording failed: {e}")
            raise
    
    async def _validate_consent_request(
        self,
        purpose: ProcessingPurpose,
        data_categories: List[DataCategory],
        consent_type: ConsentType,
        template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate consent request against requirements"""
        errors = []
        valid = True
        
        # Check if purpose requires explicit consent
        if template.get("explicit_consent_required", False) and consent_type != ConsentType.EXPLICIT:
            errors.append(f"Explicit consent required for {purpose.value}")
            valid = False
        
        # Check required data categories
        required_categories = template.get("required_data_categories", [])
        missing_required = set(required_categories) - set(data_categories)
        
        if missing_required:
            errors.append(f"Missing required data categories: {[cat.value for cat in missing_required]}")
            valid = False
        
        # Check for special category data
        special_categories = {
            DataCategory.HEALTH_DATA,
            DataCategory.BIOMETRIC_DATA,
            DataCategory.SENSITIVE_DATA
        }
        
        has_special_category = any(cat in special_categories for cat in data_categories)
        
        if has_special_category and consent_type not in [ConsentType.EXPLICIT, ConsentType.OPT_IN]:
            errors.append("Explicit consent required for special category data")
            valid = False
        
        return {
            "valid": valid,
            "errors": errors
        }
    
    async def _create_default_permissions(
        self,
        purpose: ProcessingPurpose,
        data_categories: List[DataCategory]
    ) -> Dict[str, bool]:
        """Create default granular permissions"""
        permissions = {}
        
        # Set permissions for each data category
        for category in data_categories:
            permissions[f"process_{category.value}"] = True
            permissions[f"store_{category.value}"] = True
            permissions[f"share_{category.value}"] = False  # Default to no sharing
            
            # Special handling for sensitive categories
            if category in [DataCategory.HEALTH_DATA, DataCategory.BIOMETRIC_DATA]:
                permissions[f"automated_decision_{category.value}"] = False
        
        # Purpose-specific permissions
        if purpose == ProcessingPurpose.MARKETING:
            permissions["email_marketing"] = True
            permissions["personalized_ads"] = True
            permissions["third_party_sharing"] = False
        
        elif purpose == ProcessingPurpose.ANALYTICS:
            permissions["usage_analytics"] = True
            permissions["performance_analytics"] = True
            permissions["aggregate_reporting"] = True
        
        elif purpose == ProcessingPurpose.RESEARCH:
            permissions["research_participation"] = True
            permissions["anonymized_research"] = True
            permissions["longitudinal_studies"] = False
        
        return permissions
    
    async def get_user_consents(self, user_id: str) -> List[ConsentRecord]:
        """Get all consents for a user"""
        try:
            user_consent_ids = self.user_consents.get(user_id, [])
            consents = []
            
            for consent_id in user_consent_ids:
                if consent_id in self.consent_records:
                    consent = self.consent_records[consent_id]
                    # Only return active consents
                    if consent.is_active:
                        consents.append(consent)
            
            return consents
            
        except Exception as e:
            logger.error(f"Failed to get consents for user {user_id}: {e}")
            return []
    
    async def check_consent_validity(
        self,
        user_id: str,
        purpose: ProcessingPurpose,
        data_categories: List[DataCategory]
    ) -> Dict[str, Any]:
        """Check if user has valid consent for specific purpose and data categories"""
        try:
            user_consents = await self.get_user_consents(user_id)
            
            # Find matching consents
            matching_consents = []
            
            for consent in user_consents:
                if consent.purpose == purpose:
                    # Check if consent covers required data categories
                    consent_categories = set(consent.data_categories)
                    required_categories = set(data_categories)
                    
                    if required_categories.issubset(consent_categories):
                        # Check expiry
                        if not consent.expires_at or datetime.utcnow() < consent.expires_at:
                            matching_consents.append(consent)
            
            has_valid_consent = len(matching_consents) > 0
            
            result = {
                "user_id": user_id,
                "purpose": purpose.value,
                "data_categories": [cat.value for cat in data_categories],
                "has_valid_consent": has_valid_consent,
                "matching_consents": len(matching_consents),
                "checked_at": datetime.utcnow()
            }
            
            if matching_consents:
                # Return details of the most recent consent
                latest_consent = max(matching_consents, key=lambda c: c.granted_at)
                result.update({
                    "consent_id": latest_consent.consent_id,
                    "granted_at": latest_consent.granted_at,
                    "expires_at": latest_consent.expires_at,
                    "legal_basis": latest_consent.legal_basis.value,
                    "granular_permissions": latest_consent.granular_permissions
                })
            else:
                result["reason"] = await self._analyze_consent_gap(user_id, purpose, data_categories)
            
            return result
            
        except Exception as e:
            logger.error(f"Consent validity check failed: {e}")
            return {
                "has_valid_consent": False,
                "error": str(e)
            }
    
    async def _analyze_consent_gap(
        self,
        user_id: str,
        purpose: ProcessingPurpose,
        data_categories: List[DataCategory]
    ) -> str:
        """Analyze why consent is not valid"""
        user_consents = await self.get_user_consents(user_id)
        
        if not user_consents:
            return "No consents recorded for user"
        
        purpose_consents = [c for c in user_consents if c.purpose == purpose]
        
        if not purpose_consents:
            return f"No consent for purpose: {purpose.value}"
        
        # Check expiry
        expired_consents = [c for c in purpose_consents if c.expires_at and datetime.utcnow() >= c.expires_at]
        if expired_consents:
            return "Consent expired"
        
        # Check data category coverage
        for consent in purpose_consents:
            consent_categories = set(consent.data_categories)
            required_categories = set(data_categories)
            missing_categories = required_categories - consent_categories
            
            if missing_categories:
                return f"Consent does not cover data categories: {[cat.value for cat in missing_categories]}"
        
        return "Consent requirements not met"
    
    async def withdraw_consent(
        self,
        user_id: str,
        consent_id: str,
        reason: Optional[str] = None
    ) -> bool:
        """Withdraw user consent"""
        try:
            if consent_id not in self.consent_records:
                raise ValueError(f"Consent {consent_id} not found")
            
            consent = self.consent_records[consent_id]
            
            # Verify user owns this consent
            if consent.user_id != user_id:
                raise ValueError("User does not own this consent")
            
            # Check if already withdrawn
            if consent.withdrawn_at:
                return True  # Already withdrawn
            
            # Withdraw consent
            consent.withdrawn_at = datetime.utcnow()
            consent.is_active = False
            
            # Record withdrawal in history
            await self._record_consent_history(user_id, consent_id, "withdrawn", {
                "reason": reason or "user_request",
                "withdrawal_timestamp": consent.withdrawn_at.isoformat()
            })
            
            # Create withdrawal request record
            withdrawal_id = f"withdrawal_{consent_id}_{int(datetime.utcnow().timestamp())}"
            self.withdrawal_requests[withdrawal_id] = {
                "withdrawal_id": withdrawal_id,
                "user_id": user_id,
                "consent_id": consent_id,
                "reason": reason,
                "requested_at": datetime.utcnow(),
                "status": "processed",
                "impact_analysis": await self._analyze_withdrawal_impact(consent)
            }
            
            logger.info(f"Consent withdrawn: {consent_id} by user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Consent withdrawal failed: {e}")
            raise
    
    async def _analyze_withdrawal_impact(self, consent: ConsentRecord) -> Dict[str, Any]:
        """Analyze impact of consent withdrawal"""
        template = self.consent_templates.get(consent.purpose.value, {})
        
        impact = {
            "purpose_affected": consent.purpose.value,
            "data_categories_affected": [cat.value for cat in consent.data_categories],
            "service_impact": template.get("withdrawal_impact", "Unknown impact"),
            "data_retention_required": False,
            "processing_restrictions": []
        }
        
        # Determine data retention requirements
        if consent.legal_basis in [LegalBasis.LEGAL_OBLIGATION, LegalBasis.CONTRACT]:
            impact["data_retention_required"] = True
            impact["retention_reason"] = "Legal obligation or contract fulfillment"
        
        # Add processing restrictions
        for category in consent.data_categories:
            impact["processing_restrictions"].append({
                "data_category": category.value,
                "restriction": "Stop processing for withdrawn purpose",
                "exceptions": ["Legal compliance", "Contract fulfillment"]
            })
        
        return impact
    
    async def update_consent(
        self,
        consent_id: str,
        updates: Dict[str, Any]
    ) -> ConsentRecord:
        """Update existing consent"""
        try:
            if consent_id not in self.consent_records:
                raise ValueError(f"Consent {consent_id} not found")
            
            consent = self.consent_records[consent_id]
            
            # Create new version for significant updates
            significant_updates = ["data_categories", "purpose", "granular_permissions"]
            needs_new_version = any(key in updates for key in significant_updates)
            
            if needs_new_version:
                # Create new version
                new_consent_id = f"{consent_id}_v{datetime.utcnow().timestamp()}"
                
                # Copy existing consent
                new_consent = ConsentRecord(
                    consent_id=new_consent_id,
                    user_id=consent.user_id,
                    purpose=updates.get("purpose", consent.purpose),
                    data_categories=updates.get("data_categories", consent.data_categories),
                    consent_type=consent.consent_type,
                    legal_basis=consent.legal_basis,
                    granted_at=datetime.utcnow(),
                    expires_at=updates.get("expires_at", consent.expires_at),
                    withdrawn_at=None,
                    granular_permissions=updates.get("granular_permissions", consent.granular_permissions),
                    consent_text=consent.consent_text,
                    version="2.0",
                    is_active=True
                )
                
                # Deactivate old consent
                consent.is_active = False
                
                # Store new consent
                self.consent_records[new_consent_id] = new_consent
                
                # Update user consent mapping
                if consent.user_id in self.user_consents:
                    self.user_consents[consent.user_id].append(new_consent_id)
                
                # Record history
                await self._record_consent_history(consent.user_id, new_consent_id, "updated", updates)
                
                return new_consent
            
            else:
                # Minor updates to existing consent
                for key, value in updates.items():
                    if hasattr(consent, key):
                        setattr(consent, key, value)
                
                # Record history
                await self._record_consent_history(consent.user_id, consent_id, "modified", updates)
                
                return consent
            
        except Exception as e:
            logger.error(f"Consent update failed: {e}")
            raise
    
    async def _record_consent_history(
        self,
        user_id: str,
        consent_id: str,
        action: str,
        details: Dict[str, Any]
    ):
        """Record consent history event"""
        if user_id not in self.consent_history:
            self.consent_history[user_id] = []
        
        history_entry = {
            "timestamp": datetime.utcnow(),
            "consent_id": consent_id,
            "action": action,
            "details": details,
            "ip_address": details.get("ip_address"),
            "user_agent": details.get("user_agent")
        }
        
        self.consent_history[user_id].append(history_entry)
        
        # Keep only last 1000 entries per user
        if len(self.consent_history[user_id]) > 1000:
            self.consent_history[user_id] = self.consent_history[user_id][-1000:]
    
    async def _schedule_expiry_notification(self, consent_id: str, expiry_date: datetime):
        """Schedule notification for consent expiry"""
        # Schedule notification 30 days before expiry
        notification_date = expiry_date - timedelta(days=30)
        
        if notification_date > datetime.utcnow():
            notification = {
                "consent_id": consent_id,
                "notification_date": notification_date,
                "expiry_date": expiry_date,
                "status": "scheduled",
                "type": "expiry_warning"
            }
            
            self.expiry_notifications.append(notification)
    
    async def check_consent_expiry(self):
        """Check for expiring consents and send notifications"""
        try:
            current_time = datetime.utcnow()
            
            # Check scheduled notifications
            for notification in self.expiry_notifications:
                if (notification["status"] == "scheduled" and 
                    current_time >= notification["notification_date"]):
                    
                    await self._send_expiry_notification(notification)
                    notification["status"] = "sent"
            
            # Check for expired consents
            expired_consents = []
            for consent in self.consent_records.values():
                if (consent.is_active and 
                    consent.expires_at and 
                    current_time >= consent.expires_at):
                    
                    expired_consents.append(consent)
            
            # Handle expired consents
            for consent in expired_consents:
                await self._handle_expired_consent(consent)
            
            logger.info(f"Processed {len(expired_consents)} expired consents")
            
        except Exception as e:
            logger.error(f"Consent expiry check failed: {e}")
    
    async def _send_expiry_notification(self, notification: Dict[str, Any]):
        """Send consent expiry notification"""
        consent_id = notification["consent_id"]
        consent = self.consent_records.get(consent_id)
        
        if consent:
            logger.info(f"Consent expiry notification sent for {consent_id}")
            # In production, integrate with notification service
    
    async def _handle_expired_consent(self, consent: ConsentRecord):
        """Handle expired consent"""
        try:
            # Mark consent as inactive
            consent.is_active = False
            
            # Record expiry in history
            await self._record_consent_history(
                consent.user_id, 
                consent.consent_id, 
                "expired", 
                {"expired_at": datetime.utcnow().isoformat()}
            )
            
            logger.info(f"Consent expired: {consent.consent_id}")
            
        except Exception as e:
            logger.error(f"Failed to handle expired consent {consent.consent_id}: {e}")
    
    async def handle_expiring_consents(self):
        """Handle consents that are expiring soon"""
        try:
            current_time = datetime.utcnow()
            warning_threshold = current_time + timedelta(days=30)  # 30 days warning
            
            expiring_consents = []
            
            for consent in self.consent_records.values():
                if (consent.is_active and 
                    consent.expires_at and 
                    current_time < consent.expires_at <= warning_threshold):
                    
                    expiring_consents.append(consent)
            
            # Process expiring consents
            for consent in expiring_consents:
                await self._handle_expiring_consent(consent)
            
            logger.info(f"Processed {len(expiring_consents)} expiring consents")
            
        except Exception as e:
            logger.error(f"Expiring consents handling failed: {e}")
    
    async def _handle_expiring_consent(self, consent: ConsentRecord):
        """Handle consent that is expiring soon"""
        try:
            # Create notification
            notification = {
                "user_id": consent.user_id,
                "consent_id": consent.consent_id,
                "purpose": consent.purpose.value,
                "expires_at": consent.expires_at,
                "message": f"Your consent for {consent.purpose.value} will expire soon. Please renew to continue service.",
                "action_required": "renewal",
                "created_at": datetime.utcnow()
            }
            
            # In production, send notification to user
            logger.info(f"Expiry warning created for consent {consent.consent_id}")
            
        except Exception as e:
            logger.error(f"Failed to handle expiring consent {consent.consent_id}: {e}")
    
    async def get_consent_statistics(self) -> Dict[str, Any]:
        """Get consent management statistics"""
        try:
            total_consents = len(self.consent_records)
            active_consents = len([c for c in self.consent_records.values() if c.is_active])
            withdrawn_consents = len([c for c in self.consent_records.values() if c.withdrawn_at])
            
            # Purpose distribution
            purpose_distribution = {}
            for consent in self.consent_records.values():
                if consent.is_active:
                    purpose = consent.purpose.value
                    purpose_distribution[purpose] = purpose_distribution.get(purpose, 0) + 1
            
            # Consent type distribution
            type_distribution = {}
            for consent in self.consent_records.values():
                if consent.is_active:
                    consent_type = consent.consent_type.value
                    type_distribution[consent_type] = type_distribution.get(consent_type, 0) + 1
            
            # Expiry analysis
            current_time = datetime.utcnow()
            expiring_soon = len([
                c for c in self.consent_records.values() 
                if (c.is_active and c.expires_at and 
                    current_time < c.expires_at <= current_time + timedelta(days=30))
            ])
            
            return {
                "total_consents": total_consents,
                "active_consents": active_consents,
                "withdrawn_consents": withdrawn_consents,
                "withdrawal_rate": (withdrawn_consents / total_consents * 100) if total_consents > 0 else 0,
                "purpose_distribution": purpose_distribution,
                "consent_type_distribution": type_distribution,
                "expiring_soon": expiring_soon,
                "total_users": len(self.user_consents),
                "avg_consents_per_user": active_consents / len(self.user_consents) if self.user_consents else 0
            }
            
        except Exception as e:
            logger.error(f"Consent statistics generation failed: {e}")
            return {"error": str(e)}