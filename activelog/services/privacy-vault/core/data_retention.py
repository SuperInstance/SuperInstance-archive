import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from ..models.privacy_models import RetentionPolicy, RetentionSchedule, DataCategory, LegalBasis
import logging
import json

logger = logging.getLogger(__name__)

class DataRetentionManager:
    def __init__(self):
        self.retention_policies: Dict[str, RetentionPolicy] = {}
        self.retention_schedules: Dict[str, RetentionSchedule] = {}
        self.data_registry: Dict[str, Dict] = {}  # data_id -> metadata
        self.deletion_queue: List[Dict] = []
        self.retention_exceptions: Dict[str, Dict] = {}
        self.compliance_rules: Dict[str, Dict] = {}
        self.audit_log: List[Dict] = []
        
        # Initialize retention framework
        asyncio.create_task(self._initialize_compliance_rules())
        asyncio.create_task(self._initialize_default_policies())
    
    async def _initialize_compliance_rules(self):
        """Initialize compliance-based retention rules"""
        self.compliance_rules = {
            "gdpr": {
                "name": "General Data Protection Regulation",
                "default_retention": timedelta(days=1095),  # 3 years
                "special_categories": {
                    DataCategory.HEALTH_DATA: timedelta(days=3650),  # 10 years
                    DataCategory.BIOMETRIC_DATA: timedelta(days=365),  # 1 year
                    DataCategory.SENSITIVE_DATA: timedelta(days=1095)  # 3 years
                },
                "deletion_requirements": {
                    "method": "secure_deletion",
                    "verification_required": True,
                    "audit_trail": True
                }
            },
            "hipaa": {
                "name": "Health Insurance Portability and Accountability Act",
                "default_retention": timedelta(days=2190),  # 6 years
                "special_categories": {
                    DataCategory.HEALTH_DATA: timedelta(days=2190),
                    DataCategory.PERSONAL_DATA: timedelta(days=2190)
                },
                "deletion_requirements": {
                    "method": "cryptographic_erasure",
                    "verification_required": True,
                    "medical_review": True
                }
            },
            "sox": {
                "name": "Sarbanes-Oxley Act",
                "default_retention": timedelta(days=2555),  # 7 years
                "special_categories": {
                    DataCategory.FINANCIAL_DATA: timedelta(days=2555),
                    DataCategory.PERSONAL_DATA: timedelta(days=1825)  # 5 years
                },
                "deletion_requirements": {
                    "method": "secure_overwrite",
                    "verification_required": True,
                    "compliance_review": True
                }
            },
            "pci_dss": {
                "name": "Payment Card Industry Data Security Standard",
                "default_retention": timedelta(days=365),  # 1 year
                "special_categories": {
                    DataCategory.FINANCIAL_DATA: timedelta(days=365)
                },
                "deletion_requirements": {
                    "method": "cryptographic_erasure",
                    "verification_required": True,
                    "immediate_deletion": True
                }
            }
        }
    
    async def _initialize_default_policies(self):
        """Initialize default retention policies"""
        default_policies = [
            {
                "name": "General Personal Data",
                "data_categories": [DataCategory.PERSONAL_DATA],
                "retention_period": timedelta(days=1095),
                "legal_basis": LegalBasis.LEGITIMATE_INTERESTS,
                "deletion_method": "secure_deletion"
            },
            {
                "name": "Marketing Data",
                "data_categories": [DataCategory.BEHAVIORAL_DATA, DataCategory.COMMUNICATION_DATA],
                "retention_period": timedelta(days=730),  # 2 years
                "legal_basis": LegalBasis.CONSENT,
                "deletion_method": "anonymization"
            },
            {
                "name": "Financial Records",
                "data_categories": [DataCategory.FINANCIAL_DATA],
                "retention_period": timedelta(days=2555),  # 7 years
                "legal_basis": LegalBasis.LEGAL_OBLIGATION,
                "deletion_method": "secure_overwrite",
                "exceptions": ["audit_requirement", "tax_obligation"]
            },
            {
                "name": "Health Data",
                "data_categories": [DataCategory.HEALTH_DATA],
                "retention_period": timedelta(days=3650),  # 10 years
                "legal_basis": LegalBasis.CONSENT,
                "deletion_method": "cryptographic_erasure",
                "exceptions": ["medical_research", "treatment_continuity"]
            },
            {
                "name": "Biometric Data",
                "data_categories": [DataCategory.BIOMETRIC_DATA],
                "retention_period": timedelta(days=365),  # 1 year
                "legal_basis": LegalBasis.CONSENT,
                "deletion_method": "cryptographic_erasure"
            },
            {
                "name": "Location Data",
                "data_categories": [DataCategory.LOCATION_DATA],
                "retention_period": timedelta(days=90),  # 3 months
                "legal_basis": LegalBasis.LEGITIMATE_INTERESTS,
                "deletion_method": "anonymization"
            }
        ]
        
        for policy_data in default_policies:
            await self.create_retention_policy(
                name=policy_data["name"],
                data_categories=policy_data["data_categories"],
                retention_period=policy_data["retention_period"],
                legal_basis=policy_data["legal_basis"],
                deletion_method=policy_data["deletion_method"],
                exceptions=policy_data.get("exceptions", [])
            )
    
    async def create_retention_policy(
        self,
        name: str,
        data_categories: List[DataCategory],
        retention_period: timedelta,
        legal_basis: LegalBasis,
        deletion_method: str = "secure_deletion",
        exceptions: Optional[List[str]] = None,
        geographic_scope: Optional[List[str]] = None
    ) -> RetentionPolicy:
        """Create a data retention policy"""
        try:
            policy_id = f"policy_{name.lower().replace(' ', '_')}_{int(datetime.utcnow().timestamp())}"
            
            # Validate retention period against compliance rules
            validation_result = await self._validate_retention_period(data_categories, retention_period)
            if not validation_result["valid"]:
                logger.warning(f"Retention period validation issues: {validation_result['warnings']}")
            
            # Create retention policy
            policy = RetentionPolicy(
                policy_id=policy_id,
                name=name,
                data_categories=data_categories,
                retention_period=retention_period,
                legal_basis=legal_basis,
                deletion_method=deletion_method,
                exceptions=exceptions or [],
                created_at=datetime.utcnow(),
                last_updated=datetime.utcnow(),
                is_active=True
            )
            
            # Store policy
            self.retention_policies[policy_id] = policy
            
            # Log policy creation
            await self._log_retention_event("policy_created", {
                "policy_id": policy_id,
                "name": name,
                "data_categories": [cat.value for cat in data_categories],
                "retention_days": retention_period.days
            })
            
            logger.info(f"Created retention policy: {policy_id}")
            return policy
            
        except Exception as e:
            logger.error(f"Retention policy creation failed: {e}")
            raise
    
    async def _validate_retention_period(
        self, data_categories: List[DataCategory], retention_period: timedelta
    ) -> Dict[str, Any]:
        """Validate retention period against compliance requirements"""
        warnings = []
        valid = True
        
        for category in data_categories:
            # Check against GDPR requirements
            if category in self.compliance_rules["gdpr"]["special_categories"]:
                min_period = self.compliance_rules["gdpr"]["special_categories"][category]
                if retention_period > min_period:
                    warnings.append(f"GDPR: {category.value} retention exceeds recommended {min_period.days} days")
            
            # Check against HIPAA requirements
            if category == DataCategory.HEALTH_DATA:
                hipaa_period = self.compliance_rules["hipaa"]["special_categories"][category]
                if retention_period < hipaa_period:
                    warnings.append(f"HIPAA: {category.value} retention below required {hipaa_period.days} days")
                    valid = False
            
            # Check against financial regulations
            if category == DataCategory.FINANCIAL_DATA:
                sox_period = self.compliance_rules["sox"]["special_categories"][category]
                if retention_period < sox_period:
                    warnings.append(f"SOX: {category.value} retention below required {sox_period.days} days")
                    valid = False
        
        return {"valid": valid, "warnings": warnings}
    
    async def register_data(
        self,
        data_id: str,
        data_categories: List[DataCategory],
        creation_date: datetime,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Register data for retention management"""
        try:
            # Find applicable retention policy
            applicable_policy = await self._find_applicable_policy(data_categories)
            
            if not applicable_policy:
                # Create default policy if none exists
                applicable_policy = await self._create_default_policy_for_categories(data_categories)
            
            # Calculate deletion date
            deletion_date = creation_date + applicable_policy.retention_period
            
            # Create retention schedule
            schedule_id = f"schedule_{data_id}_{int(datetime.utcnow().timestamp())}"
            schedule = RetentionSchedule(
                schedule_id=schedule_id,
                data_id=data_id,
                policy_id=applicable_policy.policy_id,
                creation_date=creation_date,
                deletion_date=deletion_date,
                status="scheduled"
            )
            
            # Store schedule
            self.retention_schedules[schedule_id] = schedule
            
            # Register data in registry
            self.data_registry[data_id] = {
                "data_id": data_id,
                "data_categories": [cat.value for cat in data_categories],
                "creation_date": creation_date,
                "deletion_date": deletion_date,
                "policy_id": applicable_policy.policy_id,
                "schedule_id": schedule_id,
                "metadata": metadata or {},
                "registered_at": datetime.utcnow()
            }
            
            # Log registration
            await self._log_retention_event("data_registered", {
                "data_id": data_id,
                "schedule_id": schedule_id,
                "deletion_date": deletion_date.isoformat(),
                "policy_id": applicable_policy.policy_id
            })
            
            logger.info(f"Registered data for retention: {data_id}")
            return schedule_id
            
        except Exception as e:
            logger.error(f"Data registration failed: {e}")
            raise
    
    async def _find_applicable_policy(self, data_categories: List[DataCategory]) -> Optional[RetentionPolicy]:
        """Find the most applicable retention policy for data categories"""
        best_match = None
        best_match_score = 0
        
        for policy in self.retention_policies.values():
            if not policy.is_active:
                continue
            
            # Calculate match score based on category overlap
            policy_categories = set(policy.data_categories)
            data_categories_set = set(data_categories)
            
            overlap = len(policy_categories.intersection(data_categories_set))
            coverage = overlap / len(data_categories_set) if data_categories_set else 0
            
            if overlap > 0 and coverage > best_match_score:
                best_match_score = coverage
                best_match = policy
        
        return best_match
    
    async def _create_default_policy_for_categories(self, data_categories: List[DataCategory]) -> RetentionPolicy:
        """Create a default retention policy for data categories"""
        # Determine appropriate retention period based on data sensitivity
        max_retention = timedelta(days=365)  # Default 1 year
        
        sensitive_categories = {
            DataCategory.HEALTH_DATA: timedelta(days=3650),
            DataCategory.FINANCIAL_DATA: timedelta(days=2555),
            DataCategory.BIOMETRIC_DATA: timedelta(days=365),
            DataCategory.SENSITIVE_DATA: timedelta(days=1095)
        }
        
        for category in data_categories:
            if category in sensitive_categories:
                category_retention = sensitive_categories[category]
                if category_retention > max_retention:
                    max_retention = category_retention
        
        # Create policy
        return await self.create_retention_policy(
            name=f"Auto-generated for {', '.join([cat.value for cat in data_categories])}",
            data_categories=data_categories,
            retention_period=max_retention,
            legal_basis=LegalBasis.LEGITIMATE_INTERESTS,
            deletion_method="secure_deletion"
        )
    
    async def enforce_retention_policies(self):
        """Enforce retention policies by processing expired data"""
        try:
            current_time = datetime.utcnow()
            expired_schedules = []
            
            # Find expired retention schedules
            for schedule in self.retention_schedules.values():
                if (schedule.status == "scheduled" and 
                    current_time >= schedule.deletion_date):
                    
                    expired_schedules.append(schedule)
            
            # Process expired schedules
            for schedule in expired_schedules:
                await self._process_expired_schedule(schedule)
            
            logger.info(f"Processed {len(expired_schedules)} expired retention schedules")
            
        except Exception as e:
            logger.error(f"Retention policy enforcement failed: {e}")
    
    async def _process_expired_schedule(self, schedule: RetentionSchedule):
        """Process an expired retention schedule"""
        try:
            # Update schedule status
            schedule.status = "processing"
            
            # Check for retention exceptions
            has_exception = await self._check_retention_exceptions(schedule.data_id)
            
            if has_exception:
                # Extend retention or mark as exception
                await self._handle_retention_exception(schedule)
                return
            
            # Get retention policy
            policy = self.retention_policies.get(schedule.policy_id)
            if not policy:
                logger.error(f"Retention policy not found: {schedule.policy_id}")
                return
            
            # Execute deletion based on policy
            deletion_result = await self._execute_data_deletion(
                schedule.data_id, 
                policy.deletion_method
            )
            
            if deletion_result["success"]:
                schedule.status = "completed"
                
                # Log successful deletion
                await self._log_retention_event("data_deleted", {
                    "data_id": schedule.data_id,
                    "schedule_id": schedule.schedule_id,
                    "deletion_method": policy.deletion_method,
                    "deleted_at": datetime.utcnow().isoformat()
                })
                
                # Remove from data registry
                if schedule.data_id in self.data_registry:
                    del self.data_registry[schedule.data_id]
            else:
                schedule.status = "failed"
                
                # Log failure
                await self._log_retention_event("deletion_failed", {
                    "data_id": schedule.data_id,
                    "schedule_id": schedule.schedule_id,
                    "error": deletion_result["error"]
                })
            
        except Exception as e:
            logger.error(f"Failed to process expired schedule {schedule.schedule_id}: {e}")
            schedule.status = "failed"
    
    async def _check_retention_exceptions(self, data_id: str) -> bool:
        """Check if data has retention exceptions"""
        return data_id in self.retention_exceptions
    
    async def _handle_retention_exception(self, schedule: RetentionSchedule):
        """Handle retention exception"""
        try:
            exception_info = self.retention_exceptions.get(schedule.data_id, {})
            
            if exception_info.get("extend_retention"):
                # Extend retention period
                extension_period = exception_info.get("extension_period", timedelta(days=365))
                schedule.deletion_date += extension_period
                schedule.status = "scheduled"
                
                # Log extension
                await self._log_retention_event("retention_extended", {
                    "data_id": schedule.data_id,
                    "schedule_id": schedule.schedule_id,
                    "new_deletion_date": schedule.deletion_date.isoformat(),
                    "reason": exception_info.get("reason", "Unknown")
                })
            else:
                # Mark as exception
                schedule.status = "exception"
                
                await self._log_retention_event("retention_exception", {
                    "data_id": schedule.data_id,
                    "schedule_id": schedule.schedule_id,
                    "reason": exception_info.get("reason", "Unknown")
                })
            
        except Exception as e:
            logger.error(f"Failed to handle retention exception: {e}")
    
    async def _execute_data_deletion(self, data_id: str, deletion_method: str) -> Dict[str, Any]:
        """Execute data deletion using specified method"""
        try:
            if deletion_method == "secure_deletion":
                return await self._secure_delete(data_id)
            elif deletion_method == "cryptographic_erasure":
                return await self._cryptographic_erasure(data_id)
            elif deletion_method == "secure_overwrite":
                return await self._secure_overwrite(data_id)
            elif deletion_method == "anonymization":
                return await self._anonymize_data(data_id)
            else:
                return {"success": False, "error": f"Unknown deletion method: {deletion_method}"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _secure_delete(self, data_id: str) -> Dict[str, Any]:
        """Perform secure deletion"""
        # Simulate secure deletion process
        logger.info(f"Performing secure deletion for data: {data_id}")
        
        # In production, implement actual secure deletion:
        # 1. Identify all storage locations
        # 2. Overwrite data multiple times
        # 3. Verify deletion completion
        # 4. Update metadata
        
        return {
            "success": True,
            "method": "secure_deletion",
            "verification": "completed",
            "deleted_at": datetime.utcnow()
        }
    
    async def _cryptographic_erasure(self, data_id: str) -> Dict[str, Any]:
        """Perform cryptographic erasure"""
        logger.info(f"Performing cryptographic erasure for data: {data_id}")
        
        # In production:
        # 1. Destroy encryption keys
        # 2. Verify key destruction
        # 3. Data becomes unrecoverable without keys
        
        return {
            "success": True,
            "method": "cryptographic_erasure",
            "key_destroyed": True,
            "deleted_at": datetime.utcnow()
        }
    
    async def _secure_overwrite(self, data_id: str) -> Dict[str, Any]:
        """Perform secure overwrite"""
        logger.info(f"Performing secure overwrite for data: {data_id}")
        
        # In production:
        # 1. Overwrite data with random patterns multiple times
        # 2. Follow DoD 5220.22-M standard
        # 3. Verify overwrite completion
        
        return {
            "success": True,
            "method": "secure_overwrite",
            "overwrite_passes": 3,
            "deleted_at": datetime.utcnow()
        }
    
    async def _anonymize_data(self, data_id: str) -> Dict[str, Any]:
        """Perform data anonymization"""
        logger.info(f"Performing data anonymization for data: {data_id}")
        
        # In production:
        # 1. Remove or hash personal identifiers
        # 2. Apply k-anonymity or differential privacy
        # 3. Verify anonymization effectiveness
        
        return {
            "success": True,
            "method": "anonymization",
            "anonymization_level": "k=5",
            "processed_at": datetime.utcnow()
        }
    
    async def add_retention_exception(
        self,
        data_id: str,
        reason: str,
        extend_retention: bool = False,
        extension_period: Optional[timedelta] = None
    ) -> str:
        """Add retention exception for specific data"""
        try:
            exception_id = f"exception_{data_id}_{int(datetime.utcnow().timestamp())}"
            
            exception_info = {
                "exception_id": exception_id,
                "data_id": data_id,
                "reason": reason,
                "extend_retention": extend_retention,
                "extension_period": extension_period,
                "created_at": datetime.utcnow(),
                "created_by": "system"  # In production, track actual user
            }
            
            self.retention_exceptions[data_id] = exception_info
            
            # Log exception
            await self._log_retention_event("exception_added", {
                "exception_id": exception_id,
                "data_id": data_id,
                "reason": reason,
                "extend_retention": extend_retention
            })
            
            logger.info(f"Added retention exception: {exception_id}")
            return exception_id
            
        except Exception as e:
            logger.error(f"Failed to add retention exception: {e}")
            raise
    
    async def cleanup_expired_data(self):
        """Cleanup expired data based on retention policies"""
        try:
            cleanup_count = 0
            
            # Run retention policy enforcement
            await self.enforce_retention_policies()
            
            # Cleanup completed schedules older than 1 year
            one_year_ago = datetime.utcnow() - timedelta(days=365)
            old_schedules = []
            
            for schedule_id, schedule in self.retention_schedules.items():
                if (schedule.status == "completed" and 
                    schedule.deletion_date < one_year_ago):
                    
                    old_schedules.append(schedule_id)
            
            # Remove old schedules
            for schedule_id in old_schedules:
                del self.retention_schedules[schedule_id]
                cleanup_count += 1
            
            # Cleanup old audit logs
            six_months_ago = datetime.utcnow() - timedelta(days=180)
            old_logs = []
            
            for i, log_entry in enumerate(self.audit_log):
                log_time = datetime.fromisoformat(log_entry["timestamp"])
                if log_time < six_months_ago:
                    old_logs.append(i)
            
            # Remove old logs (in reverse order to maintain indices)
            for i in reversed(old_logs):
                del self.audit_log[i]
                cleanup_count += 1
            
            logger.info(f"Cleaned up {cleanup_count} expired retention records")
            return cleanup_count
            
        except Exception as e:
            logger.error(f"Expired data cleanup failed: {e}")
            return 0
    
    async def _log_retention_event(self, event_type: str, details: Dict[str, Any]):
        """Log retention management event"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "details": details
        }
        
        self.audit_log.append(log_entry)
        
        # Keep only last 10000 log entries
        if len(self.audit_log) > 10000:
            self.audit_log = self.audit_log[-10000:]
    
    async def list_policies(self) -> List[RetentionPolicy]:
        """List all retention policies"""
        return list(self.retention_policies.values())
    
    async def get_data_retention_status(self, data_id: str) -> Dict[str, Any]:
        """Get retention status for specific data"""
        try:
            if data_id not in self.data_registry:
                return {"error": "Data not registered for retention management"}
            
            data_info = self.data_registry[data_id]
            schedule = self.retention_schedules.get(data_info["schedule_id"])
            policy = self.retention_policies.get(data_info["policy_id"])
            
            if not schedule or not policy:
                return {"error": "Retention schedule or policy not found"}
            
            # Calculate time remaining
            time_remaining = schedule.deletion_date - datetime.utcnow()
            
            return {
                "data_id": data_id,
                "status": schedule.status,
                "creation_date": data_info["creation_date"],
                "deletion_date": schedule.deletion_date,
                "time_remaining_days": max(0, time_remaining.days),
                "policy_name": policy.name,
                "deletion_method": policy.deletion_method,
                "data_categories": data_info["data_categories"],
                "has_exception": data_id in self.retention_exceptions
            }
            
        except Exception as e:
            logger.error(f"Retention status check failed for {data_id}: {e}")
            return {"error": str(e)}
    
    async def get_retention_statistics(self) -> Dict[str, Any]:
        """Get retention management statistics"""
        try:
            total_policies = len(self.retention_policies)
            active_policies = len([p for p in self.retention_policies.values() if p.is_active])
            total_schedules = len(self.retention_schedules)
            
            # Status distribution
            status_counts = {}
            for schedule in self.retention_schedules.values():
                status = schedule.status
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # Upcoming deletions (next 30 days)
            thirty_days = datetime.utcnow() + timedelta(days=30)
            upcoming_deletions = len([
                s for s in self.retention_schedules.values()
                if s.status == "scheduled" and s.deletion_date <= thirty_days
            ])
            
            # Category distribution
            category_counts = {}
            for data_info in self.data_registry.values():
                for category in data_info["data_categories"]:
                    category_counts[category] = category_counts.get(category, 0) + 1
            
            return {
                "total_policies": total_policies,
                "active_policies": active_policies,
                "total_schedules": total_schedules,
                "schedule_status_distribution": status_counts,
                "upcoming_deletions_30_days": upcoming_deletions,
                "data_category_distribution": category_counts,
                "total_exceptions": len(self.retention_exceptions),
                "total_registered_data": len(self.data_registry)
            }
            
        except Exception as e:
            logger.error(f"Retention statistics generation failed: {e}")
            return {"error": str(e)}