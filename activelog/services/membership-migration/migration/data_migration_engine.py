#!/usr/bin/env python3
"""
Data Migration Engine for ActiveLog Migration Service
Handles comprehensive data and history migration between applications
"""

import logging
import json
import uuid
import hashlib
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
import base64

logger = logging.getLogger(__name__)


class MigrationStatus(Enum):
    """Data migration status states"""
    PENDING = "pending"
    ANALYZING = "analyzing"
    EXTRACTING = "extracting"
    TRANSFORMING = "transforming"
    VALIDATING = "validating"
    IMPORTING = "importing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLBACK = "rollback"


class DataType(Enum):
    """Types of data to migrate"""
    USER_PROFILE = "user_profile"
    CONTENT_ENTRIES = "content_entries"
    PREFERENCES = "preferences"
    TAGS = "tags"
    CATEGORIES = "categories"
    ATTACHMENTS = "attachments"
    ANALYTICS_DATA = "analytics_data"
    INTEGRATION_DATA = "integration_data"
    CUSTOM_FIELDS = "custom_fields"
    WORKFLOW_DATA = "workflow_data"


class ConflictResolution(Enum):
    """Conflict resolution strategies"""
    SKIP = "skip"
    OVERWRITE = "overwrite"
    MERGE = "merge"
    CREATE_NEW = "create_new"
    USER_DECISION = "user_decision"


@dataclass
class DataMigrationRequest:
    """Data migration request structure"""
    migration_id: str
    user_id: str
    source_app: str
    target_app: str
    data_types: List[DataType]
    migration_options: Dict[str, Any]
    conflict_resolution: ConflictResolution
    preserve_timestamps: bool
    validate_integrity: bool
    create_backup: bool
    requested_at: datetime


@dataclass
class MigrationProgress:
    """Migration progress tracking"""
    migration_id: str
    status: MigrationStatus
    progress_percentage: float
    current_operation: str
    processed_items: int
    total_items: int
    data_processed_mb: float
    estimated_completion: Optional[datetime]
    errors: List[str]
    warnings: List[str]
    last_updated: datetime


@dataclass
class DataIntegrityReport:
    """Data integrity validation report"""
    migration_id: str
    validation_timestamp: datetime
    total_records_source: int
    total_records_target: int
    successful_migrations: int
    failed_migrations: int
    data_integrity_score: float
    checksum_matches: int
    checksum_mismatches: int
    missing_records: List[str]
    corrupted_records: List[str]
    validation_passed: bool


class DataMigrationEngine:
    """Comprehensive data migration engine"""
    
    def __init__(self, config):
        self.config = config
        self.active_migrations = {}
        self.migration_history = {}
        self.data_transformers = {}
        self.integrity_validators = {}
        
        # Schema mappings between apps
        self.schema_mappings = {
            ('activelog-core', 'studylog'): {
                'entries': 'study_sessions',
                'tags': 'subjects',
                'categories': 'study_types',
                'user_settings': 'study_preferences'
            },
            ('activelog-core', 'businesslog'): {
                'entries': 'business_activities',
                'tags': 'business_tags',
                'categories': 'activity_types',
                'user_settings': 'business_preferences'
            },
            ('studylog', 'businesslog'): {
                'study_sessions': 'training_activities',
                'subjects': 'skill_areas',
                'study_types': 'training_types',
                'progress_data': 'performance_metrics'
            },
            ('makerlog', 'businesslog'): {
                'projects': 'business_projects',
                'milestones': 'project_milestones',
                'maker_profile': 'business_profile',
                'community_data': 'team_collaboration'
            },
            ('dmlog', 'activelog-core'): {
                'campaigns': 'projects',
                'characters': 'contacts',
                'session_notes': 'entries',
                'world_data': 'reference_data'
            }
        }
        
        # Data validation rules
        self.validation_rules = {
            DataType.USER_PROFILE: {
                'required_fields': ['user_id', 'email', 'created_at'],
                'max_field_length': {'email': 255, 'display_name': 100},
                'format_validators': {'email': self._validate_email_format}
            },
            DataType.CONTENT_ENTRIES: {
                'required_fields': ['entry_id', 'user_id', 'created_at'],
                'max_field_length': {'title': 500, 'content': 50000},
                'format_validators': {'created_at': self._validate_datetime_format}
            },
            DataType.ATTACHMENTS: {
                'required_fields': ['attachment_id', 'filename', 'file_size'],
                'max_file_size_mb': 100,
                'allowed_extensions': ['.jpg', '.png', '.pdf', '.doc', '.docx', '.txt']
            }
        }
        
        logger.info("DataMigrationEngine initialized")
    
    def migrate_data(self, user_id: str, source_app: str, target_app: str, 
                    migration_options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Initiate comprehensive data migration"""
        try:
            if migration_options is None:
                migration_options = {}
            
            # Generate migration ID
            migration_id = f"dm_{uuid.uuid4().hex[:8]}"
            
            # Determine data types to migrate
            data_types = self._determine_data_types(source_app, target_app, migration_options)
            
            # Create migration request
            migration_request = DataMigrationRequest(
                migration_id=migration_id,
                user_id=user_id,
                source_app=source_app,
                target_app=target_app,
                data_types=data_types,
                migration_options=migration_options,
                conflict_resolution=ConflictResolution(migration_options.get('conflict_resolution', 'merge')),
                preserve_timestamps=migration_options.get('preserve_timestamps', True),
                validate_integrity=migration_options.get('validate_integrity', True),
                create_backup=migration_options.get('create_backup', True),
                requested_at=datetime.utcnow()
            )
            
            # Initialize progress tracking
            migration_progress = MigrationProgress(
                migration_id=migration_id,
                status=MigrationStatus.PENDING,
                progress_percentage=0.0,
                current_operation="Initializing migration",
                processed_items=0,
                total_items=0,
                data_processed_mb=0.0,
                estimated_completion=None,
                errors=[],
                warnings=[],
                last_updated=datetime.utcnow()
            )
            
            # Store migration
            self.active_migrations[migration_id] = {
                'request': migration_request,
                'progress': migration_progress
            }
            
            # Start async migration process
            asyncio.create_task(self._execute_migration(migration_id))
            
            logger.info(f"Data migration initiated: {migration_id}")
            
            return {
                'migration_id': migration_id,
                'status': 'pending',
                'data_types_to_migrate': [dt.value for dt in data_types],
                'estimated_duration_minutes': self._estimate_migration_duration(data_types, migration_options),
                'migration_steps': self._get_migration_steps(data_types),
                'backup_created': migration_request.create_backup
            }
            
        except Exception as e:
            logger.error(f"Failed to initiate data migration: {e}")
            return {
                'error': str(e),
                'migration_id': None,
                'status': 'failed'
            }
    
    def get_migration_status(self, migration_id: str) -> Dict[str, Any]:
        """Get detailed migration status"""
        try:
            if migration_id not in self.active_migrations:
                if migration_id in self.migration_history:
                    return self._format_migration_status(self.migration_history[migration_id])
                else:
                    return {'error': 'Migration not found'}
            
            migration_data = self.active_migrations[migration_id]
            return self._format_migration_status(migration_data)
            
        except Exception as e:
            logger.error(f"Failed to get migration status: {e}")
            return {'error': str(e)}
    
    async def _execute_migration(self, migration_id: str):
        """Execute the complete migration process"""
        try:
            migration_data = self.active_migrations[migration_id]
            request = migration_data['request']
            
            # Step 1: Analyze source data
            await self._analyze_source_data(migration_id)
            
            # Step 2: Create backup if requested
            if request.create_backup:
                await self._create_data_backup(migration_id)
            
            # Step 3: Extract data from source
            source_data = await self._extract_source_data(migration_id)
            
            # Step 4: Transform data for target
            transformed_data = await self._transform_data(migration_id, source_data)
            
            # Step 5: Validate data integrity
            if request.validate_integrity:
                validation_result = await self._validate_data_integrity(migration_id, transformed_data)
                if not validation_result['passed']:
                    self._handle_validation_failure(migration_id, validation_result)
                    return
            
            # Step 6: Import data to target
            import_result = await self._import_data_to_target(migration_id, transformed_data)
            
            # Step 7: Verify migration
            await self._verify_migration(migration_id)
            
            # Step 8: Complete migration
            self._complete_migration(migration_id)
            
            logger.info(f"Data migration completed: {migration_id}")
            
        except Exception as e:
            logger.error(f"Migration failed: {migration_id}, Error: {e}")
            self._fail_migration(migration_id, str(e))
    
    async def _analyze_source_data(self, migration_id: str):
        """Analyze source data to determine migration scope"""
        self._update_migration_progress(migration_id, MigrationStatus.ANALYZING, 5.0, 
                                      "Analyzing source data structure")
        
        await asyncio.sleep(2)  # Simulate analysis time
        
        migration_data = self.active_migrations[migration_id]
        request = migration_data['request']
        progress = migration_data['progress']
        
        # Simulate data analysis results
        total_items = 0
        data_size_mb = 0.0
        
        for data_type in request.data_types:
            if data_type == DataType.CONTENT_ENTRIES:
                total_items += 1250  # Simulated entry count
                data_size_mb += 45.7
            elif data_type == DataType.ATTACHMENTS:
                total_items += 234  # Simulated attachment count
                data_size_mb += 1200.5
            elif data_type == DataType.USER_PROFILE:
                total_items += 1
                data_size_mb += 0.1
            else:
                total_items += 50  # Default count for other data types
                data_size_mb += 5.0
        
        progress.total_items = total_items
        progress.data_processed_mb = data_size_mb
        progress.estimated_completion = datetime.utcnow() + timedelta(
            minutes=self._estimate_migration_duration(request.data_types, request.migration_options)
        )
    
    async def _create_data_backup(self, migration_id: str):
        """Create backup of source data"""
        self._update_migration_progress(migration_id, MigrationStatus.EXTRACTING, 15.0,
                                      "Creating data backup")
        
        await asyncio.sleep(3)  # Simulate backup time
        
        # In production, this would create actual backups
        backup_id = f"backup_{migration_id}_{int(datetime.utcnow().timestamp())}"
        logger.info(f"Backup created: {backup_id}")
    
    async def _extract_source_data(self, migration_id: str) -> Dict[str, Any]:
        """Extract data from source application"""
        self._update_migration_progress(migration_id, MigrationStatus.EXTRACTING, 30.0,
                                      "Extracting data from source application")
        
        await asyncio.sleep(5)  # Simulate extraction time
        
        migration_data = self.active_migrations[migration_id]
        request = migration_data['request']
        
        # Simulate extracted data
        extracted_data = {}
        
        if DataType.USER_PROFILE in request.data_types:
            extracted_data['user_profile'] = {
                'user_id': request.user_id,
                'email': 'user@example.com',
                'display_name': 'John Doe',
                'preferences': {'theme': 'dark', 'notifications': True},
                'created_at': '2023-01-15T10:30:00Z',
                'last_login': '2024-08-20T15:45:00Z'
            }
        
        if DataType.CONTENT_ENTRIES in request.data_types:
            extracted_data['content_entries'] = [
                {
                    'entry_id': f'entry_{i}',
                    'title': f'Entry {i}',
                    'content': f'Content for entry {i}',
                    'tags': ['work', 'personal'],
                    'category': 'daily',
                    'created_at': (datetime.utcnow() - timedelta(days=i)).isoformat(),
                    'updated_at': (datetime.utcnow() - timedelta(days=i-1)).isoformat()
                }
                for i in range(1, 11)  # Sample 10 entries
            ]
        
        if DataType.ATTACHMENTS in request.data_types:
            extracted_data['attachments'] = [
                {
                    'attachment_id': f'att_{i}',
                    'entry_id': f'entry_{i}',
                    'filename': f'document_{i}.pdf',
                    'file_size': 1024 * i,
                    'mime_type': 'application/pdf',
                    'created_at': (datetime.utcnow() - timedelta(days=i)).isoformat()
                }
                for i in range(1, 6)  # Sample 5 attachments
            ]
        
        if DataType.TAGS in request.data_types:
            extracted_data['tags'] = [
                {'tag_id': 'tag_1', 'name': 'work', 'color': '#ff6b6b', 'usage_count': 45},
                {'tag_id': 'tag_2', 'name': 'personal', 'color': '#4ecdc4', 'usage_count': 32},
                {'tag_id': 'tag_3', 'name': 'projects', 'color': '#45b7d1', 'usage_count': 28}
            ]
        
        progress = migration_data['progress']
        progress.processed_items = len(extracted_data.get('content_entries', [])) + \
                                 len(extracted_data.get('attachments', [])) + \
                                 len(extracted_data.get('tags', []))
        
        return extracted_data
    
    async def _transform_data(self, migration_id: str, source_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data for target application"""
        self._update_migration_progress(migration_id, MigrationStatus.TRANSFORMING, 55.0,
                                      "Transforming data for target application")
        
        await asyncio.sleep(4)  # Simulate transformation time
        
        migration_data = self.active_migrations[migration_id]
        request = migration_data['request']
        
        mapping_key = (request.source_app, request.target_app)
        schema_mapping = self.schema_mappings.get(mapping_key, {})
        
        transformed_data = {}
        
        # Transform each data type
        for data_type, data_items in source_data.items():
            if data_type == 'user_profile':
                transformed_data['user_profile'] = self._transform_user_profile(
                    data_items, request.target_app
                )
            elif data_type == 'content_entries':
                transformed_data[schema_mapping.get('entries', 'entries')] = [
                    self._transform_entry(entry, request.target_app, schema_mapping)
                    for entry in data_items
                ]
            elif data_type == 'tags':
                transformed_data[schema_mapping.get('tags', 'tags')] = [
                    self._transform_tag(tag, request.target_app, schema_mapping)
                    for tag in data_items
                ]
            elif data_type == 'attachments':
                transformed_data['attachments'] = [
                    self._transform_attachment(attachment, request.target_app)
                    for attachment in data_items
                ]
            else:
                # Default transformation
                transformed_data[data_type] = data_items
        
        return transformed_data
    
    async def _validate_data_integrity(self, migration_id: str, 
                                     transformed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data integrity before import"""
        self._update_migration_progress(migration_id, MigrationStatus.VALIDATING, 70.0,
                                      "Validating data integrity")
        
        await asyncio.sleep(2)  # Simulate validation time
        
        validation_errors = []
        validation_warnings = []
        total_records = 0
        valid_records = 0
        
        for data_type, data_items in transformed_data.items():
            if isinstance(data_items, list):
                total_records += len(data_items)
                for item in data_items:
                    validation_result = self._validate_record(data_type, item)
                    if validation_result['valid']:
                        valid_records += 1
                    else:
                        validation_errors.extend(validation_result['errors'])
                        validation_warnings.extend(validation_result['warnings'])
            else:
                total_records += 1
                validation_result = self._validate_record(data_type, data_items)
                if validation_result['valid']:
                    valid_records += 1
                else:
                    validation_errors.extend(validation_result['errors'])
                    validation_warnings.extend(validation_result['warnings'])
        
        integrity_score = (valid_records / total_records * 100) if total_records > 0 else 0
        validation_passed = integrity_score >= 95.0 and len(validation_errors) == 0
        
        return {
            'passed': validation_passed,
            'integrity_score': integrity_score,
            'total_records': total_records,
            'valid_records': valid_records,
            'errors': validation_errors,
            'warnings': validation_warnings
        }
    
    async def _import_data_to_target(self, migration_id: str, 
                                   transformed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Import transformed data to target application"""
        self._update_migration_progress(migration_id, MigrationStatus.IMPORTING, 85.0,
                                      "Importing data to target application")
        
        await asyncio.sleep(6)  # Simulate import time
        
        # Simulate import results
        import_results = {
            'imported_records': {},
            'failed_imports': {},
            'import_warnings': []
        }
        
        for data_type, data_items in transformed_data.items():
            if isinstance(data_items, list):
                import_results['imported_records'][data_type] = len(data_items)
                import_results['failed_imports'][data_type] = 0  # Simulate success
            else:
                import_results['imported_records'][data_type] = 1
                import_results['failed_imports'][data_type] = 0
        
        return import_results
    
    async def _verify_migration(self, migration_id: str):
        """Verify migration completion and data consistency"""
        self._update_migration_progress(migration_id, MigrationStatus.VERIFYING, 95.0,
                                      "Verifying migration completion")
        
        await asyncio.sleep(3)  # Simulate verification time
        
        # Create integrity report
        integrity_report = DataIntegrityReport(
            migration_id=migration_id,
            validation_timestamp=datetime.utcnow(),
            total_records_source=1500,  # Simulated
            total_records_target=1500,  # Simulated
            successful_migrations=1500,
            failed_migrations=0,
            data_integrity_score=100.0,
            checksum_matches=1500,
            checksum_mismatches=0,
            missing_records=[],
            corrupted_records=[],
            validation_passed=True
        )
        
        migration_data = self.active_migrations[migration_id]
        migration_data['integrity_report'] = integrity_report
    
    def _complete_migration(self, migration_id: str):
        """Complete migration and move to history"""
        self._update_migration_progress(migration_id, MigrationStatus.COMPLETED, 100.0,
                                      "Migration completed successfully")
        
        if migration_id in self.active_migrations:
            migration_data = self.active_migrations[migration_id]
            self.migration_history[migration_id] = migration_data
            del self.active_migrations[migration_id]
    
    def _fail_migration(self, migration_id: str, error_message: str):
        """Handle migration failure"""
        self._update_migration_progress(migration_id, MigrationStatus.FAILED, None,
                                      "Migration failed", [error_message])
        
        if migration_id in self.active_migrations:
            migration_data = self.active_migrations[migration_id]
            self.migration_history[migration_id] = migration_data
            del self.active_migrations[migration_id]
    
    def _update_migration_progress(self, migration_id: str, status: MigrationStatus,
                                 progress_percentage: Optional[float], current_operation: str,
                                 errors: List[str] = None, warnings: List[str] = None):
        """Update migration progress"""
        if migration_id not in self.active_migrations:
            return
        
        progress = self.active_migrations[migration_id]['progress']
        progress.status = status
        if progress_percentage is not None:
            progress.progress_percentage = progress_percentage
        progress.current_operation = current_operation
        if errors:
            progress.errors.extend(errors)
        if warnings:
            progress.warnings.extend(warnings)
        progress.last_updated = datetime.utcnow()
    
    def _determine_data_types(self, source_app: str, target_app: str, 
                            options: Dict[str, Any]) -> List[DataType]:
        """Determine which data types to migrate"""
        if options.get('data_types'):
            return [DataType(dt) for dt in options['data_types']]
        
        # Default data types based on app combination
        default_types = [
            DataType.USER_PROFILE,
            DataType.CONTENT_ENTRIES,
            DataType.PREFERENCES,
            DataType.TAGS,
            DataType.CATEGORIES
        ]
        
        # Add app-specific data types
        if source_app == 'studylog':
            default_types.extend([DataType.ANALYTICS_DATA])
        elif source_app == 'businesslog':
            default_types.extend([DataType.INTEGRATION_DATA, DataType.WORKFLOW_DATA])
        elif source_app == 'makerlog':
            default_types.extend([DataType.CUSTOM_FIELDS])
        
        # Include attachments if requested
        if options.get('include_attachments', True):
            default_types.append(DataType.ATTACHMENTS)
        
        return default_types
    
    def _estimate_migration_duration(self, data_types: List[DataType], 
                                   options: Dict[str, Any]) -> int:
        """Estimate migration duration in minutes"""
        base_duration = len(data_types) * 2  # 2 minutes per data type
        
        # Add time for attachments
        if DataType.ATTACHMENTS in data_types:
            base_duration += 10
        
        # Add time for validation
        if options.get('validate_integrity', True):
            base_duration += 5
        
        # Add time for backup
        if options.get('create_backup', True):
            base_duration += 3
        
        return max(base_duration, 8)  # Minimum 8 minutes
    
    def _get_migration_steps(self, data_types: List[DataType]) -> List[str]:
        """Get migration steps based on data types"""
        steps = [
            "Analyze source data structure",
            "Extract data from source application",
            "Transform data for target application",
            "Import data to target application",
            "Verify migration completion"
        ]
        
        if DataType.ATTACHMENTS in data_types:
            steps.insert(2, "Process and migrate file attachments")
        
        return steps
    
    def _format_migration_status(self, migration_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format migration status for API response"""
        request = migration_data['request']
        progress = migration_data['progress']
        
        status_data = {
            'migration_id': request.migration_id,
            'user_id': request.user_id,
            'source_app': request.source_app,
            'target_app': request.target_app,
            'status': progress.status.value,
            'progress_percentage': progress.progress_percentage,
            'current_operation': progress.current_operation,
            'processed_items': progress.processed_items,
            'total_items': progress.total_items,
            'data_processed_mb': progress.data_processed_mb,
            'estimated_completion': progress.estimated_completion.isoformat() if progress.estimated_completion else None,
            'errors': progress.errors,
            'warnings': progress.warnings,
            'requested_at': request.requested_at.isoformat(),
            'last_updated': progress.last_updated.isoformat(),
            'data_types_migrated': [dt.value for dt in request.data_types]
        }
        
        # Add integrity report if available
        if 'integrity_report' in migration_data:
            report = migration_data['integrity_report']
            status_data['integrity_report'] = {
                'data_integrity_score': report.data_integrity_score,
                'successful_migrations': report.successful_migrations,
                'failed_migrations': report.failed_migrations,
                'validation_passed': report.validation_passed
            }
        
        return status_data
    
    def _transform_user_profile(self, profile: Dict[str, Any], target_app: str) -> Dict[str, Any]:
        """Transform user profile for target app"""
        transformed = profile.copy()
        
        # App-specific transformations
        if target_app == 'studylog':
            transformed['study_preferences'] = profile.get('preferences', {})
            transformed['learning_goals'] = []
        elif target_app == 'businesslog':
            transformed['business_preferences'] = profile.get('preferences', {})
            transformed['company_role'] = 'Individual'
        elif target_app == 'dmlog':
            transformed['dm_preferences'] = profile.get('preferences', {})
            transformed['campaign_style'] = 'balanced'
        
        return transformed
    
    def _transform_entry(self, entry: Dict[str, Any], target_app: str, 
                        schema_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Transform content entry for target app"""
        transformed = entry.copy()
        
        # App-specific transformations
        if target_app == 'studylog':
            transformed['study_duration'] = 60  # Default 60 minutes
            transformed['subject'] = entry.get('category', 'general')
            transformed['difficulty_level'] = 'medium'
        elif target_app == 'businesslog':
            transformed['activity_type'] = entry.get('category', 'meeting')
            transformed['business_impact'] = 'medium'
            transformed['team_members'] = []
        elif target_app == 'dmlog':
            transformed['session_type'] = 'narrative'
            transformed['players_present'] = []
            transformed['campaign_id'] = None
        
        return transformed
    
    def _transform_tag(self, tag: Dict[str, Any], target_app: str, 
                      schema_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Transform tag for target app"""
        transformed = tag.copy()
        
        # App-specific transformations
        if target_app == 'studylog':
            transformed['subject_area'] = tag['name']
            transformed['study_level'] = 'intermediate'
        elif target_app == 'businesslog':
            transformed['business_category'] = tag['name']
            transformed['priority_level'] = 'normal'
        
        return transformed
    
    def _transform_attachment(self, attachment: Dict[str, Any], target_app: str) -> Dict[str, Any]:
        """Transform attachment for target app"""
        return attachment  # Minimal transformation for attachments
    
    def _validate_record(self, data_type: str, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate individual record"""
        errors = []
        warnings = []
        
        # Get validation rules for data type
        validation_rules = self.validation_rules.get(DataType(data_type), {})
        
        # Check required fields
        required_fields = validation_rules.get('required_fields', [])
        for field in required_fields:
            if field not in record or record[field] is None:
                errors.append(f"Missing required field: {field}")
        
        # Check field lengths
        max_lengths = validation_rules.get('max_field_length', {})
        for field, max_length in max_lengths.items():
            if field in record and isinstance(record[field], str) and len(record[field]) > max_length:
                errors.append(f"Field {field} exceeds maximum length of {max_length}")
        
        # Check format validators
        format_validators = validation_rules.get('format_validators', {})
        for field, validator in format_validators.items():
            if field in record:
                if not validator(record[field]):
                    errors.append(f"Invalid format for field: {field}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def _validate_email_format(self, email: str) -> bool:
        """Validate email format"""
        return '@' in email and '.' in email.split('@')[1]
    
    def _validate_datetime_format(self, datetime_str: str) -> bool:
        """Validate datetime format"""
        try:
            datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            return True
        except ValueError:
            return False
    
    def _handle_validation_failure(self, migration_id: str, validation_result: Dict[str, Any]):
        """Handle data validation failure"""
        errors = validation_result.get('errors', [])
        self._fail_migration(migration_id, f"Data validation failed: {'; '.join(errors[:5])}")
    
    def rollback_migration(self, migration_id: str) -> Dict[str, Any]:
        """Rollback a completed migration"""
        try:
            if migration_id not in self.migration_history:
                return {'error': 'Migration not found in history'}
            
            migration_data = self.migration_history[migration_id]
            request = migration_data['request']
            
            if not request.create_backup:
                return {'error': 'Cannot rollback migration without backup'}
            
            # Start rollback process
            rollback_id = f"rollback_{migration_id}"
            
            # Update status
            progress = migration_data['progress']
            progress.status = MigrationStatus.ROLLBACK
            progress.current_operation = "Rolling back migration"
            progress.last_updated = datetime.utcnow()
            
            # Move back to active migrations for tracking
            self.active_migrations[rollback_id] = migration_data
            
            # Start async rollback
            asyncio.create_task(self._execute_rollback(rollback_id, migration_id))
            
            return {
                'rollback_id': rollback_id,
                'original_migration_id': migration_id,
                'status': 'rollback_initiated',
                'message': 'Migration rollback started'
            }
            
        except Exception as e:
            logger.error(f"Failed to initiate rollback: {e}")
            return {'error': str(e)}
    
    async def _execute_rollback(self, rollback_id: str, original_migration_id: str):
        """Execute migration rollback"""
        try:
            # Simulate rollback process
            await asyncio.sleep(5)  # Simulate rollback time
            
            # Update progress
            self._update_migration_progress(rollback_id, MigrationStatus.COMPLETED, 100.0,
                                          "Rollback completed successfully")
            
            logger.info(f"Migration rollback completed: {rollback_id}")
            
        except Exception as e:
            logger.error(f"Rollback failed: {rollback_id}, Error: {e}")
            self._fail_migration(rollback_id, str(e))