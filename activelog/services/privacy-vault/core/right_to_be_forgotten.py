import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from ..models.privacy_models import RTBFRequest, RTBFStatus, DataCategory
import logging
import json
import uuid

logger = logging.getLogger(__name__)

class RightToBeForgottenManager:
    def __init__(self):
        self.rtbf_requests: Dict[str, RTBFRequest] = {}
        self.deletion_workflows: Dict[str, Dict] = {}
        self.data_mapping: Dict[str, List[Dict]] = {}  # user_id -> [data_locations]
        self.deletion_policies: Dict[str, Dict] = {}
        self.verification_queue: List[str] = []
        self.compliance_tracking: Dict[str, Dict] = {}
        self.third_party_processors: Dict[str, Dict] = {}
        
        # Initialize RTBF framework
        asyncio.create_task(self._initialize_deletion_policies())
        asyncio.create_task(self._initialize_data_processors())
    
    async def _initialize_deletion_policies(self):
        """Initialize deletion policies for different data types"""
        self.deletion_policies = {
            DataCategory.PERSONAL_DATA.value: {
                "deletion_method": "secure_overwrite",
                "verification_required": True,
                "retention_exceptions": [
                    "legal_obligation",
                    "contract_fulfillment", 
                    "vital_interests"
                ],
                "cascade_deletion": True,
                "backup_deletion_days": 30
            },
            DataCategory.SENSITIVE_DATA.value: {
                "deletion_method": "cryptographic_erasure",
                "verification_required": True,
                "retention_exceptions": [
                    "explicit_consent",
                    "legal_obligation"
                ],
                "cascade_deletion": True,
                "backup_deletion_days": 7,
                "audit_trail_required": True
            },
            DataCategory.FINANCIAL_DATA.value: {
                "deletion_method": "secure_overwrite",
                "verification_required": True,
                "retention_exceptions": [
                    "legal_obligation",
                    "regulatory_requirement"
                ],
                "cascade_deletion": False,  # May need to retain for compliance
                "backup_deletion_days": 90,
                "compliance_review_required": True
            },
            DataCategory.HEALTH_DATA.value: {
                "deletion_method": "cryptographic_erasure",
                "verification_required": True,
                "retention_exceptions": [
                    "medical_records_retention",
                    "research_consent",
                    "legal_obligation"
                ],
                "cascade_deletion": False,
                "backup_deletion_days": 14,
                "medical_review_required": True
            },
            DataCategory.BIOMETRIC_DATA.value: {
                "deletion_method": "cryptographic_erasure",
                "verification_required": True,
                "retention_exceptions": [
                    "security_purposes",
                    "legal_obligation"
                ],
                "cascade_deletion": True,
                "backup_deletion_days": 1,
                "immediate_deletion": True
            },
            DataCategory.BEHAVIORAL_DATA.value: {
                "deletion_method": "anonymization",
                "verification_required": False,
                "retention_exceptions": [
                    "legitimate_interests",
                    "research_purposes"
                ],
                "cascade_deletion": False,
                "backup_deletion_days": 60,
                "anonymization_allowed": True
            }
        }
    
    async def _initialize_data_processors(self):
        """Initialize third-party data processors"""
        self.third_party_processors = {
            "analytics_provider": {
                "name": "Analytics Service",
                "api_endpoint": "https://analytics.example.com/api/delete",
                "auth_method": "bearer_token",
                "deletion_confirmation_required": True,
                "sla_hours": 72
            },
            "marketing_platform": {
                "name": "Marketing Platform",
                "api_endpoint": "https://marketing.example.com/api/gdpr/delete",
                "auth_method": "api_key",
                "deletion_confirmation_required": True,
                "sla_hours": 24
            },
            "cloud_storage": {
                "name": "Cloud Storage Provider",
                "api_endpoint": "https://storage.example.com/api/delete",
                "auth_method": "oauth2",
                "deletion_confirmation_required": True,
                "sla_hours": 48
            },
            "backup_service": {
                "name": "Backup Service",
                "api_endpoint": "https://backup.example.com/api/purge",
                "auth_method": "mutual_tls",
                "deletion_confirmation_required": True,
                "sla_hours": 168  # 7 days
            }
        }
    
    async def create_rtbf_request(
        self,
        user_id: str,
        scope: List[str],
        reason: str,
        urgency: str = "normal",
        specific_data: Optional[List[str]] = None
    ) -> RTBFRequest:
        """Create a Right to be Forgotten request"""
        try:
            request_id = f"rtbf_{user_id}_{int(datetime.utcnow().timestamp())}"
            
            # Determine deadline based on urgency and jurisdiction
            deadline = await self._calculate_deadline(urgency)
            
            # Create RTBF request
            rtbf_request = RTBFRequest(
                request_id=request_id,
                user_id=user_id,
                scope=scope,
                reason=reason,
                status=RTBFStatus.PENDING,
                created_at=datetime.utcnow(),
                deadline=deadline,
                deletion_log=[],
                verification_required=await self._requires_verification(scope)
            )
            
            # Store request
            self.rtbf_requests[request_id] = rtbf_request
            
            # Initialize deletion workflow
            await self._initialize_deletion_workflow(request_id)
            
            # Start processing if auto-processing is enabled
            asyncio.create_task(self._process_rtbf_request(request_id))
            
            logger.info(f"Created RTBF request: {request_id} for user {user_id}")
            return rtbf_request
            
        except Exception as e:
            logger.error(f"RTBF request creation failed: {e}")
            raise
    
    async def _calculate_deadline(self, urgency: str) -> datetime:
        """Calculate deadline based on urgency and jurisdiction"""
        base_days = {
            "normal": 30,    # Standard GDPR deadline
            "high": 7,       # High priority
            "legal_deadline": 3  # Legal requirement
        }
        
        days = base_days.get(urgency, 30)
        return datetime.utcnow() + timedelta(days=days)
    
    async def _requires_verification(self, scope: List[str]) -> bool:
        """Determine if verification is required based on scope"""
        sensitive_scopes = [
            DataCategory.HEALTH_DATA.value,
            DataCategory.FINANCIAL_DATA.value,
            DataCategory.BIOMETRIC_DATA.value,
            DataCategory.SENSITIVE_DATA.value
        ]
        
        return any(scope_item in sensitive_scopes for scope_item in scope)
    
    async def _initialize_deletion_workflow(self, request_id: str):
        """Initialize deletion workflow for RTBF request"""
        try:
            rtbf_request = self.rtbf_requests[request_id]
            
            # Discover data locations
            data_locations = await self._discover_data_locations(rtbf_request.user_id, rtbf_request.scope)
            
            # Create workflow steps
            workflow_steps = []
            
            # Step 1: Verify identity (if required)
            if rtbf_request.verification_required:
                workflow_steps.append({
                    "step": "identity_verification",
                    "description": "Verify user identity",
                    "status": "pending",
                    "estimated_duration": timedelta(hours=24)
                })
            
            # Step 2: Legal basis analysis
            workflow_steps.append({
                "step": "legal_analysis",
                "description": "Analyze legal basis for retention",
                "status": "pending",
                "estimated_duration": timedelta(hours=48)
            })
            
            # Step 3: Data location mapping
            workflow_steps.append({
                "step": "data_mapping",
                "description": "Map all data locations",
                "status": "pending",
                "data_locations": data_locations,
                "estimated_duration": timedelta(hours=12)
            })
            
            # Step 4: Third-party notification
            if data_locations.get("third_party", []):
                workflow_steps.append({
                    "step": "third_party_notification",
                    "description": "Notify third-party processors",
                    "status": "pending",
                    "processors": data_locations["third_party"],
                    "estimated_duration": timedelta(hours=72)
                })
            
            # Step 5: Data deletion
            workflow_steps.append({
                "step": "data_deletion",
                "description": "Execute data deletion",
                "status": "pending",
                "estimated_duration": timedelta(hours=24)
            })
            
            # Step 6: Backup purging
            workflow_steps.append({
                "step": "backup_purging",
                "description": "Purge data from backups",
                "status": "pending",
                "estimated_duration": timedelta(days=7)
            })
            
            # Step 7: Verification
            workflow_steps.append({
                "step": "deletion_verification",
                "description": "Verify complete deletion",
                "status": "pending",
                "estimated_duration": timedelta(hours=12)
            })
            
            # Store workflow
            self.deletion_workflows[request_id] = {
                "request_id": request_id,
                "steps": workflow_steps,
                "current_step": 0,
                "created_at": datetime.utcnow(),
                "estimated_completion": datetime.utcnow() + sum(
                    step["estimated_duration"] for step in workflow_steps
                )
            }
            
        except Exception as e:
            logger.error(f"Workflow initialization failed for {request_id}: {e}")
            raise
    
    async def _discover_data_locations(self, user_id: str, scope: List[str]) -> Dict[str, List[Dict]]:
        """Discover all data locations for user and scope"""
        try:
            locations = {
                "internal": [],
                "third_party": [],
                "backups": [],
                "archives": []
            }
            
            # Simulate data discovery (in production, integrate with data catalog)
            internal_systems = [
                {"system": "primary_database", "type": "postgresql", "location": "main_cluster"},
                {"system": "user_profiles", "type": "redis", "location": "cache_cluster"},
                {"system": "analytics_db", "type": "clickhouse", "location": "analytics_cluster"},
                {"system": "document_storage", "type": "s3", "location": "document_bucket"}
            ]
            
            for system in internal_systems:
                # Check if system contains data for user
                has_data = await self._check_system_for_user_data(system, user_id, scope)
                if has_data:
                    locations["internal"].append(system)
            
            # Check third-party processors
            for processor_id, processor_info in self.third_party_processors.items():
                # Simulate checking if processor has user data
                has_data = await self._check_processor_for_user_data(processor_id, user_id, scope)
                if has_data:
                    locations["third_party"].append({
                        "processor_id": processor_id,
                        "processor_info": processor_info
                    })
            
            # Check backup locations
            backup_locations = await self._discover_backup_locations(user_id, scope)
            locations["backups"] = backup_locations
            
            return locations
            
        except Exception as e:
            logger.error(f"Data location discovery failed: {e}")
            return {"internal": [], "third_party": [], "backups": [], "archives": []}
    
    async def _check_system_for_user_data(self, system: Dict, user_id: str, scope: List[str]) -> bool:
        """Check if system contains data for user (simplified)"""
        # In production, this would query actual systems
        return True  # Assume all systems have user data for demo
    
    async def _check_processor_for_user_data(self, processor_id: str, user_id: str, scope: List[str]) -> bool:
        """Check if third-party processor has user data"""
        # In production, this would call processor APIs
        return processor_id in ["analytics_provider", "marketing_platform"]
    
    async def _discover_backup_locations(self, user_id: str, scope: List[str]) -> List[Dict]:
        """Discover backup locations containing user data"""
        # Simulate backup discovery
        return [
            {"backup_id": "daily_backup_20241201", "location": "backup_vault_1", "age_days": 7},
            {"backup_id": "weekly_backup_20241124", "location": "backup_vault_2", "age_days": 14},
            {"backup_id": "monthly_backup_20241101", "location": "archive_storage", "age_days": 45}
        ]
    
    async def _process_rtbf_request(self, request_id: str):
        """Process RTBF request through workflow"""
        try:
            workflow = self.deletion_workflows[request_id]
            rtbf_request = self.rtbf_requests[request_id]
            
            rtbf_request.status = RTBFStatus.IN_PROGRESS
            
            for i, step in enumerate(workflow["steps"]):
                workflow["current_step"] = i
                step["started_at"] = datetime.utcnow()
                step["status"] = "in_progress"
                
                logger.info(f"Processing RTBF step: {step['step']} for request {request_id}")
                
                # Execute step
                step_result = await self._execute_workflow_step(request_id, step)
                
                if step_result["success"]:
                    step["status"] = "completed"
                    step["completed_at"] = datetime.utcnow()
                    step["result"] = step_result["result"]
                    
                    # Log in RTBF request
                    rtbf_request.deletion_log.append({
                        "timestamp": datetime.utcnow(),
                        "step": step["step"],
                        "status": "completed",
                        "details": step_result["result"]
                    })
                else:
                    step["status"] = "failed"
                    step["error"] = step_result["error"]
                    step["failed_at"] = datetime.utcnow()
                    
                    # Log failure
                    rtbf_request.deletion_log.append({
                        "timestamp": datetime.utcnow(),
                        "step": step["step"],
                        "status": "failed",
                        "error": step_result["error"]
                    })
                    
                    # Mark request as partial completion
                    rtbf_request.status = RTBFStatus.PARTIAL
                    logger.error(f"RTBF step failed: {step['step']} for request {request_id}")
                    return
                
                # Add delay between steps
                await asyncio.sleep(1)
            
            # All steps completed
            rtbf_request.status = RTBFStatus.COMPLETED
            rtbf_request.completed_at = datetime.utcnow()
            
            logger.info(f"RTBF request completed: {request_id}")
            
        except Exception as e:
            logger.error(f"RTBF processing failed for {request_id}: {e}")
            rtbf_request.status = RTBFStatus.PARTIAL
    
    async def _execute_workflow_step(self, request_id: str, step: Dict) -> Dict[str, Any]:
        """Execute a specific workflow step"""
        try:
            step_type = step["step"]
            
            if step_type == "identity_verification":
                return await self._verify_identity(request_id)
            
            elif step_type == "legal_analysis":
                return await self._analyze_legal_basis(request_id)
            
            elif step_type == "data_mapping":
                return await self._map_data_locations(request_id, step["data_locations"])
            
            elif step_type == "third_party_notification":
                return await self._notify_third_parties(request_id, step["processors"])
            
            elif step_type == "data_deletion":
                return await self._execute_data_deletion(request_id)
            
            elif step_type == "backup_purging":
                return await self._purge_backups(request_id)
            
            elif step_type == "deletion_verification":
                return await self._verify_deletion(request_id)
            
            else:
                return {"success": False, "error": f"Unknown step type: {step_type}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _verify_identity(self, request_id: str) -> Dict[str, Any]:
        """Verify user identity for RTBF request"""
        # In production, implement proper identity verification
        # For demo, auto-approve
        return {
            "success": True,
            "result": {
                "verification_method": "automated",
                "verified_at": datetime.utcnow(),
                "verification_id": f"verify_{request_id}"
            }
        }
    
    async def _analyze_legal_basis(self, request_id: str) -> Dict[str, Any]:
        """Analyze legal basis for data retention"""
        try:
            rtbf_request = self.rtbf_requests[request_id]
            
            # Analyze each data category in scope
            retention_analysis = {}
            can_delete_all = True
            
            for scope_item in rtbf_request.scope:
                policy = self.deletion_policies.get(scope_item, {})
                retention_exceptions = policy.get("retention_exceptions", [])
                
                # Simulate legal analysis
                applicable_exceptions = []
                
                # Check for common retention reasons
                if scope_item == DataCategory.FINANCIAL_DATA.value:
                    applicable_exceptions.append("regulatory_requirement")
                    can_delete_all = False
                
                if scope_item == DataCategory.HEALTH_DATA.value:
                    # Check if medical record retention applies
                    applicable_exceptions.append("medical_records_retention")
                    can_delete_all = False
                
                retention_analysis[scope_item] = {
                    "can_delete": len(applicable_exceptions) == 0,
                    "retention_exceptions": applicable_exceptions,
                    "deletion_method": policy.get("deletion_method", "secure_overwrite")
                }
            
            return {
                "success": True,
                "result": {
                    "can_delete_all": can_delete_all,
                    "retention_analysis": retention_analysis,
                    "analyzed_at": datetime.utcnow()
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _map_data_locations(self, request_id: str, data_locations: Dict) -> Dict[str, Any]:
        """Map all data locations for deletion"""
        try:
            location_map = {
                "internal_systems": len(data_locations.get("internal", [])),
                "third_party_processors": len(data_locations.get("third_party", [])),
                "backup_locations": len(data_locations.get("backups", [])),
                "total_locations": sum([
                    len(data_locations.get("internal", [])),
                    len(data_locations.get("third_party", [])),
                    len(data_locations.get("backups", []))
                ])
            }
            
            return {
                "success": True,
                "result": {
                    "location_map": location_map,
                    "data_locations": data_locations,
                    "mapped_at": datetime.utcnow()
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _notify_third_parties(self, request_id: str, processors: List[Dict]) -> Dict[str, Any]:
        """Notify third-party processors of deletion request"""
        try:
            notification_results = []
            
            for processor in processors:
                processor_info = processor["processor_info"]
                
                # Simulate API call to third-party processor
                notification_result = {
                    "processor_id": processor["processor_id"],
                    "name": processor_info["name"],
                    "notified_at": datetime.utcnow(),
                    "status": "notified",
                    "sla_deadline": datetime.utcnow() + timedelta(hours=processor_info["sla_hours"])
                }
                
                notification_results.append(notification_result)
                
                logger.info(f"Notified third-party processor: {processor_info['name']}")
            
            return {
                "success": True,
                "result": {
                    "notifications_sent": len(notification_results),
                    "notification_results": notification_results
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_data_deletion(self, request_id: str) -> Dict[str, Any]:
        """Execute data deletion from internal systems"""
        try:
            rtbf_request = self.rtbf_requests[request_id]
            deletion_results = []
            
            # Get data locations from workflow
            workflow = self.deletion_workflows[request_id]
            data_locations = None
            
            for step in workflow["steps"]:
                if step["step"] == "data_mapping" and "result" in step:
                    data_locations = step["result"]["data_locations"]
                    break
            
            if not data_locations:
                return {"success": False, "error": "Data locations not found"}
            
            # Delete from internal systems
            for system in data_locations.get("internal", []):
                deletion_result = await self._delete_from_system(
                    system, rtbf_request.user_id, rtbf_request.scope
                )
                deletion_results.append({
                    "system": system["system"],
                    "status": "deleted" if deletion_result else "failed",
                    "deleted_at": datetime.utcnow()
                })
            
            return {
                "success": True,
                "result": {
                    "systems_processed": len(deletion_results),
                    "deletion_results": deletion_results
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _delete_from_system(self, system: Dict, user_id: str, scope: List[str]) -> bool:
        """Delete user data from specific system"""
        try:
            # Simulate system-specific deletion
            system_type = system["type"]
            
            if system_type == "postgresql":
                # SQL deletion
                logger.info(f"Executing SQL deletion for user {user_id} in {system['system']}")
                
            elif system_type == "redis":
                # Redis key deletion
                logger.info(f"Deleting Redis keys for user {user_id} in {system['system']}")
                
            elif system_type == "s3":
                # S3 object deletion
                logger.info(f"Deleting S3 objects for user {user_id} in {system['system']}")
            
            # Simulate successful deletion
            return True
            
        except Exception as e:
            logger.error(f"Deletion failed for system {system}: {e}")
            return False
    
    async def _purge_backups(self, request_id: str) -> Dict[str, Any]:
        """Purge user data from backups"""
        try:
            workflow = self.deletion_workflows[request_id]
            data_locations = None
            
            for step in workflow["steps"]:
                if step["step"] == "data_mapping" and "result" in step:
                    data_locations = step["result"]["data_locations"]
                    break
            
            if not data_locations:
                return {"success": False, "error": "Backup locations not found"}
            
            purge_results = []
            
            for backup in data_locations.get("backups", []):
                # Simulate backup purging
                purge_result = {
                    "backup_id": backup["backup_id"],
                    "location": backup["location"],
                    "status": "purged",
                    "purged_at": datetime.utcnow()
                }
                purge_results.append(purge_result)
                
                logger.info(f"Purged backup: {backup['backup_id']}")
            
            return {
                "success": True,
                "result": {
                    "backups_purged": len(purge_results),
                    "purge_results": purge_results
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _verify_deletion(self, request_id: str) -> Dict[str, Any]:
        """Verify that deletion was completed successfully"""
        try:
            rtbf_request = self.rtbf_requests[request_id]
            
            # Simulate verification by checking various systems
            verification_results = {
                "primary_database": True,
                "cache_systems": True,
                "backup_systems": True,
                "third_party_processors": True  # Would need confirmation from processors
            }
            
            all_verified = all(verification_results.values())
            
            if all_verified:
                # Add to verification queue for audit
                self.verification_queue.append(request_id)
            
            return {
                "success": True,
                "result": {
                    "verification_complete": all_verified,
                    "verification_results": verification_results,
                    "verified_at": datetime.utcnow()
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def execute_rtbf_request(self, request_id: str):
        """Manually execute RTBF request"""
        try:
            if request_id not in self.rtbf_requests:
                raise ValueError(f"RTBF request {request_id} not found")
            
            # Start processing
            asyncio.create_task(self._process_rtbf_request(request_id))
            
        except Exception as e:
            logger.error(f"Manual RTBF execution failed: {e}")
            raise
    
    async def get_request_status(self, request_id: str) -> Dict[str, Any]:
        """Get status of RTBF request"""
        try:
            if request_id not in self.rtbf_requests:
                return {"error": "Request not found"}
            
            rtbf_request = self.rtbf_requests[request_id]
            workflow = self.deletion_workflows.get(request_id, {})
            
            # Calculate progress
            if workflow and "steps" in workflow:
                completed_steps = len([s for s in workflow["steps"] if s["status"] == "completed"])
                total_steps = len(workflow["steps"])
                progress_percentage = (completed_steps / total_steps * 100) if total_steps > 0 else 0
            else:
                progress_percentage = 0
            
            return {
                "request_id": request_id,
                "user_id": rtbf_request.user_id,
                "status": rtbf_request.status.value,
                "created_at": rtbf_request.created_at,
                "deadline": rtbf_request.deadline,
                "completed_at": rtbf_request.completed_at,
                "progress_percentage": progress_percentage,
                "deletion_log": rtbf_request.deletion_log,
                "workflow": workflow
            }
            
        except Exception as e:
            logger.error(f"Status retrieval failed for {request_id}: {e}")
            return {"error": str(e)}
    
    async def get_active_requests(self) -> List[RTBFRequest]:
        """Get all active RTBF requests"""
        active_statuses = [RTBFStatus.PENDING, RTBFStatus.IN_PROGRESS]
        return [
            request for request in self.rtbf_requests.values()
            if request.status in active_statuses
        ]
    
    async def get_rtbf_statistics(self) -> Dict[str, Any]:
        """Get RTBF processing statistics"""
        try:
            total_requests = len(self.rtbf_requests)
            
            if total_requests == 0:
                return {
                    "total_requests": 0,
                    "message": "No RTBF requests processed yet"
                }
            
            # Status distribution
            status_counts = {}
            for request in self.rtbf_requests.values():
                status = request.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # Calculate completion rate
            completed = status_counts.get("completed", 0)
            completion_rate = (completed / total_requests * 100) if total_requests > 0 else 0
            
            # Average processing time for completed requests
            completed_requests = [r for r in self.rtbf_requests.values() if r.status == RTBFStatus.COMPLETED]
            
            avg_processing_time = None
            if completed_requests:
                processing_times = [
                    (r.completed_at - r.created_at).total_seconds() / 3600  # hours
                    for r in completed_requests if r.completed_at
                ]
                avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
            
            return {
                "total_requests": total_requests,
                "status_distribution": status_counts,
                "completion_rate": completion_rate,
                "avg_processing_time_hours": avg_processing_time,
                "requests_in_verification": len(self.verification_queue),
                "active_workflows": len([w for w in self.deletion_workflows.values() 
                                       if any(s["status"] in ["pending", "in_progress"] for s in w["steps"])])
            }
            
        except Exception as e:
            logger.error(f"RTBF statistics generation failed: {e}")
            return {"error": str(e)}