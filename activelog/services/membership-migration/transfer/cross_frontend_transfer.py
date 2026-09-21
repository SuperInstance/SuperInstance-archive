#!/usr/bin/env python3
"""
Cross-frontend membership transfer system for ActiveLog
Handles seamless membership transfers between different ActiveLog applications
"""

import logging
import json
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)


class TransferStatus(Enum):
    """Transfer status states"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VALIDATING = "validating"
    TRANSFERRING = "transferring"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TransferType(Enum):
    """Types of transfers"""
    FULL_MIGRATION = "full_migration"
    MEMBERSHIP_ONLY = "membership_only"
    DATA_SYNC = "data_sync"
    TRIAL_CONVERSION = "trial_conversion"
    UPGRADE_TRANSFER = "upgrade_transfer"


@dataclass
class TransferRequest:
    """Transfer request data structure"""
    transfer_id: str
    user_id: str
    source_app: str
    target_app: str
    transfer_type: TransferType
    transfer_options: Dict[str, Any]
    requested_at: datetime
    estimated_duration_minutes: int
    priority: int = 5  # 1-10, 10 being highest


@dataclass
class TransferProgress:
    """Transfer progress tracking"""
    transfer_id: str
    status: TransferStatus
    progress_percentage: float
    current_stage: str
    stages_completed: List[str]
    stages_remaining: List[str]
    estimated_completion: Optional[datetime]
    error_message: Optional[str]
    last_updated: datetime


class CrossFrontendTransfer:
    """Cross-frontend membership transfer orchestrator"""
    
    def __init__(self, config):
        self.config = config
        self.active_transfers = {}
        self.transfer_history = {}
        self.transfer_queue = []
        self.supported_apps = {
            'activelog-core': {
                'name': 'ActiveLog Core',
                'version': '2.0',
                'endpoints': {
                    'export': '/api/v1/export/user-data',
                    'import': '/api/v1/import/user-data',
                    'validate': '/api/v1/validate/user-data'
                },
                'features': ['basic_logging', 'search', 'tags', 'export']
            },
            'studylog': {
                'name': 'StudyLog',
                'version': '1.5',
                'endpoints': {
                    'export': '/api/v1/student/export',
                    'import': '/api/v1/student/import',
                    'validate': '/api/v1/student/validate'
                },
                'features': ['study_tracking', 'progress_analytics', 'scheduling', 'collaboration']
            },
            'businesslog': {
                'name': 'BusinessLog',
                'version': '1.8',
                'endpoints': {
                    'export': '/api/v1/business/export',
                    'import': '/api/v1/business/import',
                    'validate': '/api/v1/business/validate'
                },
                'features': ['team_management', 'reporting', 'integration_hub', 'analytics']
            },
            'makerlog': {
                'name': 'MakerLog',
                'version': '1.3',
                'endpoints': {
                    'export': '/api/v1/maker/export',
                    'import': '/api/v1/maker/import',
                    'validate': '/api/v1/maker/validate'
                },
                'features': ['project_tracking', 'milestone_management', 'community', 'showcase']
            },
            'dmlog': {
                'name': 'DMLog',
                'version': '2.1',
                'endpoints': {
                    'export': '/api/v1/dm/export',
                    'import': '/api/v1/dm/import',
                    'validate': '/api/v1/dm/validate'
                },
                'features': ['campaign_management', 'character_tracking', 'dice_rolling', 'world_building']
            }
        }
        logger.info("CrossFrontendTransfer initialized")
    
    def initiate_transfer(self, user_id: str, source_app: str, target_app: str, 
                         transfer_options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Initiate a cross-frontend membership transfer"""
        try:
            if transfer_options is None:
                transfer_options = {}
            
            # Generate unique transfer ID
            transfer_id = f"xft_{uuid.uuid4().hex[:8]}"
            
            # Validate apps
            if not self._validate_apps(source_app, target_app):
                raise ValueError(f"Invalid app combination: {source_app} -> {target_app}")
            
            # Determine transfer type
            transfer_type = self._determine_transfer_type(source_app, target_app, transfer_options)
            
            # Estimate duration
            estimated_duration = self._estimate_transfer_duration(user_id, transfer_type, transfer_options)
            
            # Create transfer request
            transfer_request = TransferRequest(
                transfer_id=transfer_id,
                user_id=user_id,
                source_app=source_app,
                target_app=target_app,
                transfer_type=transfer_type,
                transfer_options=transfer_options,
                requested_at=datetime.utcnow(),
                estimated_duration_minutes=estimated_duration,
                priority=transfer_options.get('priority', 5)
            )
            
            # Initialize transfer progress
            transfer_progress = TransferProgress(
                transfer_id=transfer_id,
                status=TransferStatus.PENDING,
                progress_percentage=0.0,
                current_stage="Queued for processing",
                stages_completed=[],
                stages_remaining=self._get_transfer_stages(transfer_type),
                estimated_completion=datetime.utcnow() + timedelta(minutes=estimated_duration),
                error_message=None,
                last_updated=datetime.utcnow()
            )
            
            # Store in active transfers
            self.active_transfers[transfer_id] = {
                'request': transfer_request,
                'progress': transfer_progress
            }
            
            # Add to processing queue
            self.transfer_queue.append(transfer_id)
            
            # Start async processing
            asyncio.create_task(self._process_transfer(transfer_id))
            
            logger.info(f"Transfer initiated: {transfer_id} from {source_app} to {target_app}")
            
            return {
                'transfer_id': transfer_id,
                'status': 'pending',
                'estimated_duration_minutes': estimated_duration,
                'estimated_completion': transfer_progress.estimated_completion.isoformat(),
                'next_steps': [
                    'Validating source and target applications',
                    'Exporting user data from source application',
                    'Transforming data for target application',
                    'Importing data to target application',
                    'Finalizing transfer and cleanup'
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to initiate transfer: {e}")
            return {
                'error': str(e),
                'transfer_id': None,
                'status': 'failed'
            }
    
    def get_transfer_status(self, transfer_id: str) -> Dict[str, Any]:
        """Get detailed transfer status"""
        try:
            if transfer_id not in self.active_transfers:
                # Check history
                if transfer_id in self.transfer_history:
                    return asdict(self.transfer_history[transfer_id])
                else:
                    return {'error': 'Transfer not found', 'transfer_id': transfer_id}
            
            transfer_data = self.active_transfers[transfer_id]
            request = transfer_data['request']
            progress = transfer_data['progress']
            
            return {
                'transfer_id': transfer_id,
                'user_id': request.user_id,
                'source_app': request.source_app,
                'target_app': request.target_app,
                'transfer_type': request.transfer_type.value,
                'status': progress.status.value,
                'progress_percentage': progress.progress_percentage,
                'current_stage': progress.current_stage,
                'stages_completed': progress.stages_completed,
                'stages_remaining': progress.stages_remaining,
                'estimated_completion': progress.estimated_completion.isoformat() if progress.estimated_completion else None,
                'error_message': progress.error_message,
                'requested_at': request.requested_at.isoformat(),
                'last_updated': progress.last_updated.isoformat(),
                'transfer_options': request.transfer_options
            }
            
        except Exception as e:
            logger.error(f"Failed to get transfer status: {e}")
            return {'error': str(e)}
    
    async def _process_transfer(self, transfer_id: str):
        """Process a transfer asynchronously"""
        try:
            if transfer_id not in self.active_transfers:
                return
            
            transfer_data = self.active_transfers[transfer_id]
            request = transfer_data['request']
            progress = transfer_data['progress']
            
            # Update status to in progress
            self._update_transfer_progress(transfer_id, TransferStatus.IN_PROGRESS, 10.0, 
                                         "Starting transfer process")
            
            # Stage 1: Validate source and target
            await self._validate_transfer_compatibility(transfer_id)
            self._update_transfer_progress(transfer_id, TransferStatus.VALIDATING, 25.0, 
                                         "Validating data compatibility")
            
            # Stage 2: Export data from source
            source_data = await self._export_source_data(transfer_id)
            self._update_transfer_progress(transfer_id, TransferStatus.TRANSFERRING, 50.0, 
                                         "Exporting data from source application")
            
            # Stage 3: Transform data for target
            transformed_data = await self._transform_data_for_target(transfer_id, source_data)
            self._update_transfer_progress(transfer_id, TransferStatus.TRANSFERRING, 70.0, 
                                         "Transforming data for target application")
            
            # Stage 4: Import data to target
            await self._import_data_to_target(transfer_id, transformed_data)
            self._update_transfer_progress(transfer_id, TransferStatus.TRANSFERRING, 85.0, 
                                         "Importing data to target application")
            
            # Stage 5: Verify and finalize
            await self._verify_and_finalize_transfer(transfer_id)
            self._update_transfer_progress(transfer_id, TransferStatus.FINALIZING, 95.0, 
                                         "Verifying transfer and finalizing")
            
            # Stage 6: Complete
            self._complete_transfer(transfer_id)
            self._update_transfer_progress(transfer_id, TransferStatus.COMPLETED, 100.0, 
                                         "Transfer completed successfully")
            
            logger.info(f"Transfer completed successfully: {transfer_id}")
            
        except Exception as e:
            logger.error(f"Transfer failed: {transfer_id}, Error: {e}")
            self._fail_transfer(transfer_id, str(e))
    
    async def _validate_transfer_compatibility(self, transfer_id: str):
        """Validate transfer compatibility between apps"""
        await asyncio.sleep(2)  # Simulate validation time
        
        transfer_data = self.active_transfers[transfer_id]
        request = transfer_data['request']
        
        source_app = self.supported_apps.get(request.source_app)
        target_app = self.supported_apps.get(request.target_app)
        
        if not source_app or not target_app:
            raise Exception("Unsupported application in transfer")
        
        # Check feature compatibility
        source_features = set(source_app['features'])
        target_features = set(target_app['features'])
        
        incompatible_features = source_features - target_features
        if incompatible_features and request.transfer_type == TransferType.FULL_MIGRATION:
            logger.warning(f"Incompatible features detected: {incompatible_features}")
            # Continue with warning but log compatibility issues
    
    async def _export_source_data(self, transfer_id: str) -> Dict[str, Any]:
        """Export data from source application"""
        await asyncio.sleep(5)  # Simulate export time
        
        # Simulate exported data structure
        return {
            'user_profile': {
                'user_id': 'user_12345',
                'email': 'user@example.com',
                'preferences': {'theme': 'dark', 'notifications': True},
                'created_at': '2023-01-15T10:30:00Z'
            },
            'membership_data': {
                'tier': 'pro',
                'subscription_id': 'sub_12345',
                'billing_cycle': 'annual',
                'features': ['advanced_analytics', 'priority_support']
            },
            'usage_data': {
                'total_entries': 1250,
                'storage_used_mb': 450.7,
                'last_activity': '2024-08-20T15:45:00Z'
            },
            'content_data': {
                'entries': [],  # Would contain actual entries
                'tags': ['work', 'personal', 'projects'],
                'categories': ['daily', 'weekly', 'monthly']
            }
        }
    
    async def _transform_data_for_target(self, transfer_id: str, source_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data format for target application"""
        await asyncio.sleep(3)  # Simulate transformation time
        
        transfer_data = self.active_transfers[transfer_id]
        request = transfer_data['request']
        
        # Apply transformation rules based on target app
        transformed_data = source_data.copy()
        
        if request.target_app == 'studylog':
            # Add study-specific fields
            transformed_data['study_profile'] = {
                'learning_goals': [],
                'study_schedule': {},
                'progress_tracking': {}
            }
        elif request.target_app == 'businesslog':
            # Add business-specific fields
            transformed_data['business_profile'] = {
                'company_info': {},
                'team_members': [],
                'project_data': {}
            }
        elif request.target_app == 'dmlog':
            # Add D&D specific fields
            transformed_data['dm_profile'] = {
                'campaigns': [],
                'characters': [],
                'world_data': {}
            }
        
        return transformed_data
    
    async def _import_data_to_target(self, transfer_id: str, transformed_data: Dict[str, Any]):
        """Import transformed data to target application"""
        await asyncio.sleep(4)  # Simulate import time
        
        # Simulate successful import
        # In real implementation, this would make API calls to target app
        pass
    
    async def _verify_and_finalize_transfer(self, transfer_id: str):
        """Verify transfer completion and finalize"""
        await asyncio.sleep(2)  # Simulate verification time
        
        # Verify data integrity
        # Update user's active app preference
        # Send confirmation notifications
        pass
    
    def _complete_transfer(self, transfer_id: str):
        """Complete the transfer and move to history"""
        if transfer_id in self.active_transfers:
            transfer_data = self.active_transfers[transfer_id]
            self.transfer_history[transfer_id] = transfer_data['progress']
            del self.active_transfers[transfer_id]
    
    def _fail_transfer(self, transfer_id: str, error_message: str):
        """Mark transfer as failed"""
        self._update_transfer_progress(transfer_id, TransferStatus.FAILED, None, 
                                     "Transfer failed", error_message)
        if transfer_id in self.active_transfers:
            transfer_data = self.active_transfers[transfer_id]
            self.transfer_history[transfer_id] = transfer_data['progress']
            del self.active_transfers[transfer_id]
    
    def _update_transfer_progress(self, transfer_id: str, status: TransferStatus, 
                                progress_percentage: Optional[float], current_stage: str, 
                                error_message: Optional[str] = None):
        """Update transfer progress"""
        if transfer_id not in self.active_transfers:
            return
        
        progress = self.active_transfers[transfer_id]['progress']
        progress.status = status
        if progress_percentage is not None:
            progress.progress_percentage = progress_percentage
        progress.current_stage = current_stage
        if error_message:
            progress.error_message = error_message
        progress.last_updated = datetime.utcnow()
        
        # Update completed stages
        if progress_percentage and progress_percentage >= 25 and "Validation" not in progress.stages_completed:
            progress.stages_completed.append("Validation")
        if progress_percentage and progress_percentage >= 50 and "Data Export" not in progress.stages_completed:
            progress.stages_completed.append("Data Export")
        if progress_percentage and progress_percentage >= 70 and "Data Transformation" not in progress.stages_completed:
            progress.stages_completed.append("Data Transformation")
        if progress_percentage and progress_percentage >= 85 and "Data Import" not in progress.stages_completed:
            progress.stages_completed.append("Data Import")
        if progress_percentage and progress_percentage >= 100 and "Verification" not in progress.stages_completed:
            progress.stages_completed.append("Verification")
    
    def _validate_apps(self, source_app: str, target_app: str) -> bool:
        """Validate that both apps are supported"""
        return source_app in self.supported_apps and target_app in self.supported_apps
    
    def _determine_transfer_type(self, source_app: str, target_app: str, 
                               transfer_options: Dict[str, Any]) -> TransferType:
        """Determine the appropriate transfer type"""
        if transfer_options.get('full_migration', False):
            return TransferType.FULL_MIGRATION
        elif transfer_options.get('membership_only', False):
            return TransferType.MEMBERSHIP_ONLY
        elif transfer_options.get('data_sync', False):
            return TransferType.DATA_SYNC
        elif transfer_options.get('trial_conversion', False):
            return TransferType.TRIAL_CONVERSION
        else:
            return TransferType.UPGRADE_TRANSFER
    
    def _estimate_transfer_duration(self, user_id: str, transfer_type: TransferType, 
                                  transfer_options: Dict[str, Any]) -> int:
        """Estimate transfer duration in minutes"""
        base_duration = {
            TransferType.FULL_MIGRATION: 15,
            TransferType.MEMBERSHIP_ONLY: 5,
            TransferType.DATA_SYNC: 10,
            TransferType.TRIAL_CONVERSION: 8,
            TransferType.UPGRADE_TRANSFER: 12
        }
        
        duration = base_duration.get(transfer_type, 10)
        
        # Adjust based on data size (simulated)
        data_size_factor = transfer_options.get('estimated_data_size_mb', 100) / 100
        duration = int(duration * (1 + data_size_factor * 0.5))
        
        return max(duration, 5)  # Minimum 5 minutes
    
    def _get_transfer_stages(self, transfer_type: TransferType) -> List[str]:
        """Get the stages for a transfer type"""
        stages = [
            "Validation",
            "Data Export", 
            "Data Transformation",
            "Data Import",
            "Verification"
        ]
        
        if transfer_type == TransferType.MEMBERSHIP_ONLY:
            return ["Validation", "Membership Transfer", "Verification"]
        
        return stages
    
    def cancel_transfer(self, transfer_id: str) -> Dict[str, Any]:
        """Cancel an active transfer"""
        try:
            if transfer_id not in self.active_transfers:
                return {'error': 'Transfer not found or already completed'}
            
            transfer_data = self.active_transfers[transfer_id]
            progress = transfer_data['progress']
            
            if progress.status in [TransferStatus.COMPLETED, TransferStatus.FAILED]:
                return {'error': 'Cannot cancel completed or failed transfer'}
            
            # Update status to cancelled
            self._update_transfer_progress(transfer_id, TransferStatus.CANCELLED, None, 
                                         "Transfer cancelled by user")
            
            # Move to history
            self.transfer_history[transfer_id] = progress
            del self.active_transfers[transfer_id]
            
            logger.info(f"Transfer cancelled: {transfer_id}")
            
            return {
                'transfer_id': transfer_id,
                'status': 'cancelled',
                'message': 'Transfer cancelled successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to cancel transfer: {e}")
            return {'error': str(e)}
    
    def get_supported_apps(self) -> Dict[str, Any]:
        """Get list of supported applications"""
        return {
            'supported_apps': list(self.supported_apps.keys()),
            'app_details': {
                app_id: {
                    'name': details['name'],
                    'version': details['version'],
                    'features': details['features']
                }
                for app_id, details in self.supported_apps.items()
            }
        }
    
    def get_transfer_recommendations(self, user_id: str, current_app: str) -> List[Dict[str, Any]]:
        """Get transfer recommendations for a user"""
        recommendations = []
        
        for app_id, app_details in self.supported_apps.items():
            if app_id == current_app:
                continue
            
            recommendation = {
                'target_app': app_id,
                'app_name': app_details['name'],
                'compatibility_score': self._calculate_compatibility_score(current_app, app_id),
                'transfer_benefits': self._get_transfer_benefits(current_app, app_id),
                'estimated_duration_minutes': self._estimate_transfer_duration(user_id, TransferType.FULL_MIGRATION, {}),
                'recommended_transfer_type': 'full_migration'
            }
            recommendations.append(recommendation)
        
        # Sort by compatibility score
        recommendations.sort(key=lambda x: x['compatibility_score'], reverse=True)
        
        return recommendations
    
    def _calculate_compatibility_score(self, source_app: str, target_app: str) -> float:
        """Calculate compatibility score between apps"""
        if source_app not in self.supported_apps or target_app not in self.supported_apps:
            return 0.0
        
        source_features = set(self.supported_apps[source_app]['features'])
        target_features = set(self.supported_apps[target_app]['features'])
        
        common_features = source_features.intersection(target_features)
        total_features = source_features.union(target_features)
        
        if not total_features:
            return 0.0
        
        return len(common_features) / len(total_features)
    
    def _get_transfer_benefits(self, source_app: str, target_app: str) -> List[str]:
        """Get benefits of transferring to target app"""
        if target_app not in self.supported_apps:
            return []
        
        target_features = set(self.supported_apps[target_app]['features'])
        source_features = set(self.supported_apps[source_app]['features']) if source_app in self.supported_apps else set()
        
        new_features = target_features - source_features
        
        benefit_mapping = {
            'study_tracking': 'Advanced study progress tracking',
            'team_management': 'Comprehensive team collaboration tools',
            'project_tracking': 'Project milestone and progress management',
            'campaign_management': 'D&D campaign and world management',
            'integration_hub': 'Third-party service integrations',
            'analytics': 'Advanced analytics and reporting',
            'collaboration': 'Real-time collaboration features'
        }
        
        return [benefit_mapping.get(feature, f"Access to {feature}") for feature in new_features]