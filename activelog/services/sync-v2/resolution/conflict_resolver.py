#!/usr/bin/env python3
"""
ActiveLog.ai Conflict Resolution System

Advanced conflict detection and resolution for multi-device synchronization.
"""

import json
import logging
import hashlib
import difflib
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import re
import uuid

class ConflictType(Enum):
    CONCURRENT_EDIT = "concurrent_edit"          # Same item edited simultaneously
    DELETE_EDIT = "delete_edit"                  # Item deleted on one device, edited on another
    MOVE_MOVE = "move_move"                      # Item moved to different locations
    RENAME_RENAME = "rename_rename"              # Item renamed differently
    TYPE_CHANGE = "type_change"                  # Content type changed
    SCHEMA_MISMATCH = "schema_mismatch"          # Data structure incompatible
    PERMISSION_CONFLICT = "permission_conflict"  # Permission changes conflict

class ResolutionStrategy(Enum):
    AUTO_MERGE = "auto_merge"                    # Automatic merge when possible
    LAST_WRITER_WINS = "last_writer_wins"       # Most recent change wins
    FIRST_WRITER_WINS = "first_writer_wins"     # First change wins
    USER_CHOICE = "user_choice"                  # Let user decide
    MANUAL_MERGE = "manual_merge"               # Manual conflict resolution
    BRANCH_BOTH = "branch_both"                 # Keep both versions as branches
    SMART_MERGE = "smart_merge"                 # AI-assisted intelligent merge

class ConflictSeverity(Enum):
    LOW = 1          # Minor differences, auto-resolvable
    MEDIUM = 2       # Significant differences, may need user input
    HIGH = 3         # Major conflicts, definitely need user input
    CRITICAL = 4     # Data loss risk, immediate attention required

@dataclass
class ConflictItem:
    """Individual conflicting version of an item"""
    version_id: str
    device_id: str
    device_name: str
    user_id: str
    timestamp: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    checksum: str
    change_description: str = ""
    author_info: Dict[str, str] = None

    def __post_init__(self):
        if self.author_info is None:
            self.author_info = {}

@dataclass
class Conflict:
    """Conflict between multiple versions"""
    conflict_id: str
    item_id: str
    conflict_type: ConflictType
    severity: ConflictSeverity
    conflicting_items: List[ConflictItem]
    base_version: Optional[ConflictItem] = None  # Common ancestor
    detected_at: str = None
    resolution_deadline: Optional[str] = None
    context: Dict[str, Any] = None
    auto_resolvable: bool = False
    suggested_resolution: Optional[str] = None

    def __post_init__(self):
        if self.detected_at is None:
            self.detected_at = datetime.now().isoformat()
        if self.context is None:
            self.context = {}

@dataclass
class ResolutionResult:
    """Result of conflict resolution"""
    conflict_id: str
    strategy_used: ResolutionStrategy
    resolved_at: str
    resolved_by: str  # user_id or "system"
    merged_data: Optional[Dict[str, Any]] = None
    branches_created: List[str] = None
    user_notes: str = ""
    confidence_score: float = 0.0  # 0-1, how confident we are in the resolution
    
    def __post_init__(self):
        if self.branches_created is None:
            self.branches_created = []

class ConflictDetector:
    """Detect conflicts between versions"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def detect_conflicts(self, item_id: str, versions: List[ConflictItem],
                        base_version: Optional[ConflictItem] = None) -> List[Conflict]:
        """Detect conflicts between multiple versions of an item"""
        conflicts = []
        
        if len(versions) < 2:
            return conflicts
        
        # Sort versions by timestamp
        sorted_versions = sorted(versions, key=lambda v: v.timestamp)
        
        # Check for different types of conflicts
        conflicts.extend(self._detect_concurrent_edits(item_id, sorted_versions, base_version))
        conflicts.extend(self._detect_delete_edit_conflicts(item_id, sorted_versions))
        conflicts.extend(self._detect_move_conflicts(item_id, sorted_versions))
        conflicts.extend(self._detect_type_conflicts(item_id, sorted_versions))
        conflicts.extend(self._detect_schema_conflicts(item_id, sorted_versions))
        
        return conflicts
    
    def _detect_concurrent_edits(self, item_id: str, versions: List[ConflictItem],
                                base_version: Optional[ConflictItem]) -> List[Conflict]:
        """Detect concurrent editing conflicts"""
        conflicts = []
        
        # Group versions by time window (e.g., within 5 minutes)
        time_window = timedelta(minutes=5)
        concurrent_groups = []
        
        for version in versions:
            version_time = datetime.fromisoformat(version.timestamp)
            added_to_group = False
            
            for group in concurrent_groups:
                group_time = datetime.fromisoformat(group[0].timestamp)
                if abs(version_time - group_time) <= time_window:
                    group.append(version)
                    added_to_group = True
                    break
            
            if not added_to_group:
                concurrent_groups.append([version])
        
        # Check groups with multiple versions
        for group in concurrent_groups:
            if len(group) > 1:
                # Check if versions actually differ
                if self._versions_differ_significantly(group):
                    severity = self._assess_conflict_severity(group, base_version)
                    
                    conflict = Conflict(
                        conflict_id=str(uuid.uuid4()),
                        item_id=item_id,
                        conflict_type=ConflictType.CONCURRENT_EDIT,
                        severity=severity,
                        conflicting_items=group,
                        base_version=base_version,
                        context={
                            "time_window_minutes": time_window.total_seconds() / 60,
                            "devices_involved": [v.device_id for v in group]
                        }
                    )
                    
                    # Check if auto-resolvable
                    conflict.auto_resolvable = self._is_auto_resolvable(conflict)
                    if conflict.auto_resolvable:
                        conflict.suggested_resolution = self._suggest_auto_resolution(conflict)
                    
                    conflicts.append(conflict)
        
        return conflicts
    
    def _detect_delete_edit_conflicts(self, item_id: str, versions: List[ConflictItem]) -> List[Conflict]:
        """Detect delete-edit conflicts"""
        conflicts = []
        
        # Look for deleted versions (would need to be tracked separately)
        # This is a simplified implementation
        
        return conflicts
    
    def _detect_move_conflicts(self, item_id: str, versions: List[ConflictItem]) -> List[Conflict]:
        """Detect move/rename conflicts"""
        conflicts = []
        
        # Check for different paths/names in metadata
        paths = set()
        names = set()
        
        for version in versions:
            metadata = version.metadata
            if 'path' in metadata:
                paths.add(metadata['path'])
            if 'name' in metadata:
                names.add(metadata['name'])
        
        if len(paths) > 1:
            conflict = Conflict(
                conflict_id=str(uuid.uuid4()),
                item_id=item_id,
                conflict_type=ConflictType.MOVE_MOVE,
                severity=ConflictSeverity.MEDIUM,
                conflicting_items=versions,
                context={"conflicting_paths": list(paths)}
            )
            conflicts.append(conflict)
        
        if len(names) > 1:
            conflict = Conflict(
                conflict_id=str(uuid.uuid4()),
                item_id=item_id,
                conflict_type=ConflictType.RENAME_RENAME,
                severity=ConflictSeverity.MEDIUM,
                conflicting_items=versions,
                context={"conflicting_names": list(names)}
            )
            conflicts.append(conflict)
        
        return conflicts
    
    def _detect_type_conflicts(self, item_id: str, versions: List[ConflictItem]) -> List[Conflict]:
        """Detect content type conflicts"""
        conflicts = []
        
        content_types = set()
        for version in versions:
            content_type = version.metadata.get('content_type')
            if content_type:
                content_types.add(content_type)
        
        if len(content_types) > 1:
            conflict = Conflict(
                conflict_id=str(uuid.uuid4()),
                item_id=item_id,
                conflict_type=ConflictType.TYPE_CHANGE,
                severity=ConflictSeverity.HIGH,
                conflicting_items=versions,
                context={"conflicting_types": list(content_types)}
            )
            conflicts.append(conflict)
        
        return conflicts
    
    def _detect_schema_conflicts(self, item_id: str, versions: List[ConflictItem]) -> List[Conflict]:
        """Detect data schema conflicts"""
        conflicts = []
        
        # Check for incompatible data structures
        schemas = []
        for version in versions:
            schema = self._extract_schema(version.data)
            schemas.append(schema)
        
        if not self._schemas_compatible(schemas):
            conflict = Conflict(
                conflict_id=str(uuid.uuid4()),
                item_id=item_id,
                conflict_type=ConflictType.SCHEMA_MISMATCH,
                severity=ConflictSeverity.HIGH,
                conflicting_items=versions,
                context={"schema_differences": self._describe_schema_differences(schemas)}
            )
            conflicts.append(conflict)
        
        return conflicts
    
    def _versions_differ_significantly(self, versions: List[ConflictItem]) -> bool:
        """Check if versions differ significantly"""
        if len(versions) < 2:
            return False
        
        # Compare checksums first
        checksums = set(v.checksum for v in versions)
        if len(checksums) == 1:
            return False  # All versions identical
        
        # Compare data content
        base_data = versions[0].data
        for version in versions[1:]:
            if not self._data_similar(base_data, version.data):
                return True
        
        return False
    
    def _data_similar(self, data1: Dict[str, Any], data2: Dict[str, Any], threshold: float = 0.8) -> bool:
        """Check if two data objects are similar"""
        str1 = json.dumps(data1, sort_keys=True)
        str2 = json.dumps(data2, sort_keys=True)
        
        # Use difflib to calculate similarity
        similarity = difflib.SequenceMatcher(None, str1, str2).ratio()
        return similarity >= threshold
    
    def _assess_conflict_severity(self, versions: List[ConflictItem],
                                 base_version: Optional[ConflictItem]) -> ConflictSeverity:
        """Assess the severity of a conflict"""
        if len(versions) <= 1:
            return ConflictSeverity.LOW
        
        # Check data size differences
        max_size = max(len(json.dumps(v.data)) for v in versions)
        min_size = min(len(json.dumps(v.data)) for v in versions)
        size_ratio = min_size / max_size if max_size > 0 else 1.0
        
        # Check structural differences
        has_structural_changes = False
        base_keys = set(versions[0].data.keys())
        for version in versions[1:]:
            if set(version.data.keys()) != base_keys:
                has_structural_changes = True
                break
        
        # Assess severity
        if has_structural_changes or size_ratio < 0.5:
            return ConflictSeverity.HIGH
        elif size_ratio < 0.8:
            return ConflictSeverity.MEDIUM
        else:
            return ConflictSeverity.LOW
    
    def _is_auto_resolvable(self, conflict: Conflict) -> bool:
        """Check if conflict can be automatically resolved"""
        if conflict.severity == ConflictSeverity.CRITICAL:
            return False
        
        if conflict.conflict_type == ConflictType.CONCURRENT_EDIT:
            # Can auto-resolve if changes are in different fields
            return self._changes_in_different_fields(conflict.conflicting_items)
        
        if conflict.conflict_type == ConflictType.MOVE_MOVE:
            # Can auto-resolve by using most recent move
            return True
        
        return conflict.severity == ConflictSeverity.LOW
    
    def _changes_in_different_fields(self, versions: List[ConflictItem]) -> bool:
        """Check if changes are in different data fields"""
        if len(versions) < 2:
            return True
        
        changed_fields = []
        base_data = versions[0].data
        
        for version in versions[1:]:
            fields = set()
            for key in set(base_data.keys()) | set(version.data.keys()):
                if base_data.get(key) != version.data.get(key):
                    fields.add(key)
            changed_fields.append(fields)
        
        # Check if any fields overlap
        if len(changed_fields) < 2:
            return True
        
        overlap = changed_fields[0]
        for field_set in changed_fields[1:]:
            overlap = overlap.intersection(field_set)
        
        return len(overlap) == 0
    
    def _suggest_auto_resolution(self, conflict: Conflict) -> str:
        """Suggest automatic resolution strategy"""
        if conflict.conflict_type == ConflictType.CONCURRENT_EDIT:
            if self._changes_in_different_fields(conflict.conflicting_items):
                return "merge_non_conflicting_fields"
            else:
                return "last_writer_wins"
        
        if conflict.conflict_type == ConflictType.MOVE_MOVE:
            return "use_most_recent_move"
        
        if conflict.conflict_type == ConflictType.RENAME_RENAME:
            return "use_most_recent_name"
        
        return "manual_review_required"
    
    def _extract_schema(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Extract schema from data object"""
        schema = {}
        for key, value in data.items():
            schema[key] = type(value).__name__
        return schema
    
    def _schemas_compatible(self, schemas: List[Dict[str, str]]) -> bool:
        """Check if schemas are compatible"""
        if len(schemas) <= 1:
            return True
        
        base_schema = schemas[0]
        for schema in schemas[1:]:
            # Check for type mismatches in common fields
            for key in set(base_schema.keys()) & set(schema.keys()):
                if base_schema[key] != schema[key]:
                    return False
        
        return True
    
    def _describe_schema_differences(self, schemas: List[Dict[str, str]]) -> Dict[str, Any]:
        """Describe differences between schemas"""
        if len(schemas) <= 1:
            return {}
        
        all_keys = set()
        for schema in schemas:
            all_keys.update(schema.keys())
        
        differences = {}
        for key in all_keys:
            types = [schema.get(key, 'missing') for schema in schemas]
            if len(set(types)) > 1:
                differences[key] = types
        
        return differences

class ConflictResolver:
    """Resolve conflicts using various strategies"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.resolution_strategies = {
            ResolutionStrategy.AUTO_MERGE: self._auto_merge,
            ResolutionStrategy.LAST_WRITER_WINS: self._last_writer_wins,
            ResolutionStrategy.FIRST_WRITER_WINS: self._first_writer_wins,
            ResolutionStrategy.SMART_MERGE: self._smart_merge,
            ResolutionStrategy.BRANCH_BOTH: self._branch_both
        }
    
    def resolve_conflict(self, conflict: Conflict, strategy: ResolutionStrategy,
                        user_id: str = "system", user_input: Dict[str, Any] = None) -> ResolutionResult:
        """Resolve conflict using specified strategy"""
        self.logger.info(f"Resolving conflict {conflict.conflict_id} using {strategy.value}")
        
        if strategy in self.resolution_strategies:
            resolver_func = self.resolution_strategies[strategy]
            
            try:
                result = resolver_func(conflict, user_input or {})
                result.resolved_by = user_id
                result.resolved_at = datetime.now().isoformat()
                result.strategy_used = strategy
                
                return result
            
            except Exception as e:
                self.logger.error(f"Resolution failed: {e}")
                return ResolutionResult(
                    conflict_id=conflict.conflict_id,
                    strategy_used=strategy,
                    resolved_at=datetime.now().isoformat(),
                    resolved_by=user_id,
                    confidence_score=0.0,
                    user_notes=f"Resolution failed: {str(e)}"
                )
        
        else:
            raise ValueError(f"Unknown resolution strategy: {strategy}")
    
    def _auto_merge(self, conflict: Conflict, user_input: Dict[str, Any]) -> ResolutionResult:
        """Automatically merge non-conflicting changes"""
        if len(conflict.conflicting_items) < 2:
            raise ValueError("Need at least 2 versions to merge")
        
        # Start with base version or first version
        base_data = conflict.base_version.data if conflict.base_version else {}
        merged_data = base_data.copy()
        
        # Apply changes from each version
        for item in conflict.conflicting_items:
            for key, value in item.data.items():
                if key not in merged_data or merged_data[key] != value:
                    # Check if this field conflicts with other versions
                    conflict_found = False
                    for other_item in conflict.conflicting_items:
                        if (other_item != item and 
                            key in other_item.data and 
                            other_item.data[key] != value and
                            other_item.data[key] != base_data.get(key)):
                            conflict_found = True
                            break
                    
                    if not conflict_found:
                        merged_data[key] = value
                    else:
                        # Use last writer wins for conflicting fields
                        latest_item = max(conflict.conflicting_items, 
                                        key=lambda x: x.timestamp)
                        if item == latest_item:
                            merged_data[key] = value
        
        confidence = self._calculate_merge_confidence(conflict, merged_data)
        
        return ResolutionResult(
            conflict_id=conflict.conflict_id,
            strategy_used=ResolutionStrategy.AUTO_MERGE,
            merged_data=merged_data,
            confidence_score=confidence,
            user_notes="Automatically merged non-conflicting changes"
        )
    
    def _last_writer_wins(self, conflict: Conflict, user_input: Dict[str, Any]) -> ResolutionResult:
        """Use the most recent version"""
        latest_item = max(conflict.conflicting_items, key=lambda x: x.timestamp)
        
        return ResolutionResult(
            conflict_id=conflict.conflict_id,
            strategy_used=ResolutionStrategy.LAST_WRITER_WINS,
            merged_data=latest_item.data,
            confidence_score=0.7,
            user_notes=f"Used version from {latest_item.device_name} ({latest_item.timestamp})"
        )
    
    def _first_writer_wins(self, conflict: Conflict, user_input: Dict[str, Any]) -> ResolutionResult:
        """Use the earliest version"""
        earliest_item = min(conflict.conflicting_items, key=lambda x: x.timestamp)
        
        return ResolutionResult(
            conflict_id=conflict.conflict_id,
            strategy_used=ResolutionStrategy.FIRST_WRITER_WINS,
            merged_data=earliest_item.data,
            confidence_score=0.7,
            user_notes=f"Used version from {earliest_item.device_name} ({earliest_item.timestamp})"
        )
    
    def _smart_merge(self, conflict: Conflict, user_input: Dict[str, Any]) -> ResolutionResult:
        """Intelligent merge using content analysis"""
        if conflict.conflict_type == ConflictType.CONCURRENT_EDIT:
            return self._smart_merge_text_content(conflict)
        else:
            # Fall back to auto merge for other types
            return self._auto_merge(conflict, user_input)
    
    def _smart_merge_text_content(self, conflict: Conflict) -> ResolutionResult:
        """Smart merge for text content using diff algorithms"""
        items = conflict.conflicting_items
        
        if len(items) != 2:
            # For now, only handle 2-way merges
            return self._auto_merge(conflict, {})
        
        # Extract text content
        text1 = self._extract_text_content(items[0].data)
        text2 = self._extract_text_content(items[1].data)
        
        if conflict.base_version:
            base_text = self._extract_text_content(conflict.base_version.data)
            merged_text = self._three_way_merge(base_text, text1, text2)
        else:
            merged_text = self._two_way_merge(text1, text2)
        
        # Create merged data
        merged_data = items[0].data.copy()
        self._update_text_content(merged_data, merged_text)
        
        # Calculate confidence based on merge complexity
        confidence = 0.8 if conflict.base_version else 0.6
        
        return ResolutionResult(
            conflict_id=conflict.conflict_id,
            strategy_used=ResolutionStrategy.SMART_MERGE,
            merged_data=merged_data,
            confidence_score=confidence,
            user_notes="Smart merged text content using diff algorithms"
        )
    
    def _branch_both(self, conflict: Conflict, user_input: Dict[str, Any]) -> ResolutionResult:
        """Keep both versions as separate branches"""
        branches = []
        
        for i, item in enumerate(conflict.conflicting_items):
            branch_id = f"{conflict.item_id}_branch_{i}_{item.device_id}"
            branches.append(branch_id)
        
        return ResolutionResult(
            conflict_id=conflict.conflict_id,
            strategy_used=ResolutionStrategy.BRANCH_BOTH,
            branches_created=branches,
            confidence_score=1.0,
            user_notes=f"Created {len(branches)} branches to preserve all versions"
        )
    
    def _extract_text_content(self, data: Dict[str, Any]) -> str:
        """Extract text content from data for merging"""
        # Look for common text fields
        text_fields = ['content', 'text', 'body', 'description', 'message']
        
        for field in text_fields:
            if field in data and isinstance(data[field], str):
                return data[field]
        
        # If no text field found, use JSON representation
        return json.dumps(data, indent=2)
    
    def _update_text_content(self, data: Dict[str, Any], text: str):
        """Update text content in data"""
        text_fields = ['content', 'text', 'body', 'description', 'message']
        
        for field in text_fields:
            if field in data:
                data[field] = text
                return
        
        # If no text field found, add as 'content'
        data['content'] = text
    
    def _two_way_merge(self, text1: str, text2: str) -> str:
        """Simple two-way text merge"""
        lines1 = text1.splitlines()
        lines2 = text2.splitlines()
        
        # Use difflib to create unified diff
        diff = list(difflib.unified_diff(lines1, lines2, lineterm=''))
        
        # For simplicity, just concatenate unique lines
        merged_lines = []
        
        # Add all lines from text1
        for line in lines1:
            if line not in merged_lines:
                merged_lines.append(line)
        
        # Add unique lines from text2
        for line in lines2:
            if line not in merged_lines:
                merged_lines.append(line)
        
        return '\n'.join(merged_lines)
    
    def _three_way_merge(self, base: str, text1: str, text2: str) -> str:
        """Three-way merge with common ancestor"""
        base_lines = base.splitlines()
        lines1 = text1.splitlines()
        lines2 = text2.splitlines()
        
        # Simple three-way merge algorithm
        merged_lines = []
        
        # Use difflib to find differences
        diff1 = list(difflib.unified_diff(base_lines, lines1, lineterm=''))
        diff2 = list(difflib.unified_diff(base_lines, lines2, lineterm=''))
        
        # For simplicity, start with base and apply non-conflicting changes
        merged_lines = base_lines.copy()
        
        # This is a simplified merge - a real implementation would be more sophisticated
        unique_lines1 = [line for line in lines1 if line not in base_lines]
        unique_lines2 = [line for line in lines2 if line not in base_lines]
        
        # Add unique lines from both versions
        merged_lines.extend(unique_lines1)
        merged_lines.extend(unique_lines2)
        
        return '\n'.join(merged_lines)
    
    def _calculate_merge_confidence(self, conflict: Conflict, merged_data: Dict[str, Any]) -> float:
        """Calculate confidence score for merge result"""
        base_confidence = 0.5
        
        # Increase confidence for low severity conflicts
        if conflict.severity == ConflictSeverity.LOW:
            base_confidence += 0.3
        elif conflict.severity == ConflictSeverity.MEDIUM:
            base_confidence += 0.1
        
        # Increase confidence if we have a base version
        if conflict.base_version:
            base_confidence += 0.2
        
        # Decrease confidence for many conflicting versions
        if len(conflict.conflicting_items) > 2:
            base_confidence -= 0.1 * (len(conflict.conflicting_items) - 2)
        
        return max(0.0, min(1.0, base_confidence))

class ConflictManager:
    """Manage the entire conflict resolution process"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.detector = ConflictDetector()
        self.resolver = ConflictResolver()
        self.logger = logging.getLogger(__name__)
        
        # Default resolution preferences
        self.default_strategies = {
            ConflictType.CONCURRENT_EDIT: ResolutionStrategy.SMART_MERGE,
            ConflictType.DELETE_EDIT: ResolutionStrategy.USER_CHOICE,
            ConflictType.MOVE_MOVE: ResolutionStrategy.LAST_WRITER_WINS,
            ConflictType.RENAME_RENAME: ResolutionStrategy.LAST_WRITER_WINS,
            ConflictType.TYPE_CHANGE: ResolutionStrategy.USER_CHOICE,
            ConflictType.SCHEMA_MISMATCH: ResolutionStrategy.USER_CHOICE
        }
        
        # Auto-resolution settings
        self.auto_resolve_low_severity = self.config.get('auto_resolve_low_severity', True)
        self.auto_resolve_threshold = self.config.get('auto_resolve_threshold', 0.8)
    
    def process_conflict(self, item_id: str, versions: List[ConflictItem],
                        base_version: Optional[ConflictItem] = None,
                        user_preferences: Dict[str, Any] = None) -> List[ResolutionResult]:
        """Process conflicts for an item"""
        # Detect conflicts
        conflicts = self.detector.detect_conflicts(item_id, versions, base_version)
        
        if not conflicts:
            self.logger.info(f"No conflicts detected for item {item_id}")
            return []
        
        self.logger.info(f"Detected {len(conflicts)} conflicts for item {item_id}")
        
        # Resolve conflicts
        results = []
        for conflict in conflicts:
            try:
                result = self._resolve_single_conflict(conflict, user_preferences)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Failed to resolve conflict {conflict.conflict_id}: {e}")
                # Create failed resolution result
                results.append(ResolutionResult(
                    conflict_id=conflict.conflict_id,
                    strategy_used=ResolutionStrategy.USER_CHOICE,
                    resolved_at=datetime.now().isoformat(),
                    resolved_by="system",
                    confidence_score=0.0,
                    user_notes=f"Auto-resolution failed: {str(e)}"
                ))
        
        return results
    
    def _resolve_single_conflict(self, conflict: Conflict,
                                user_preferences: Dict[str, Any] = None) -> ResolutionResult:
        """Resolve a single conflict"""
        preferences = user_preferences or {}
        
        # Check if conflict can be auto-resolved
        if (conflict.auto_resolvable and 
            self.auto_resolve_low_severity and 
            conflict.severity == ConflictSeverity.LOW):
            
            strategy = ResolutionStrategy.AUTO_MERGE
            self.logger.info(f"Auto-resolving conflict {conflict.conflict_id}")
        
        else:
            # Get preferred strategy
            strategy = preferences.get(
                f'strategy_{conflict.conflict_type.value}',
                self.default_strategies.get(conflict.conflict_type, ResolutionStrategy.USER_CHOICE)
            )
        
        # Resolve using chosen strategy
        if strategy == ResolutionStrategy.USER_CHOICE:
            # For user choice, we'll use smart merge as fallback
            # In a real system, this would prompt the user
            strategy = ResolutionStrategy.SMART_MERGE
        
        return self.resolver.resolve_conflict(conflict, strategy, "system", preferences)
    
    def get_conflict_summary(self, conflicts: List[Conflict]) -> Dict[str, Any]:
        """Get summary of conflicts"""
        if not conflicts:
            return {"total": 0}
        
        summary = {
            "total": len(conflicts),
            "by_type": {},
            "by_severity": {},
            "auto_resolvable": 0,
            "needs_user_input": 0
        }
        
        for conflict in conflicts:
            # Count by type
            type_key = conflict.conflict_type.value
            summary["by_type"][type_key] = summary["by_type"].get(type_key, 0) + 1
            
            # Count by severity
            severity_key = conflict.severity.name.lower()
            summary["by_severity"][severity_key] = summary["by_severity"].get(severity_key, 0) + 1
            
            # Count resolvability
            if conflict.auto_resolvable:
                summary["auto_resolvable"] += 1
            else:
                summary["needs_user_input"] += 1
        
        return summary

async def main():
    """Example usage of conflict resolution"""
    # Create test conflict items
    item1 = ConflictItem(
        version_id="v1",
        device_id="phone-001",
        device_name="iPhone 15",
        user_id="user123",
        timestamp="2024-01-01T10:00:00",
        data={"title": "My Note", "content": "Original content here"},
        metadata={"content_type": "text"},
        checksum="abc123",
        change_description="Initial creation"
    )
    
    item2 = ConflictItem(
        version_id="v2",
        device_id="desktop-001", 
        device_name="MacBook Pro",
        user_id="user123",
        timestamp="2024-01-01T10:02:00",
        data={"title": "My Note", "content": "Original content here\nAdded from desktop"},
        metadata={"content_type": "text"},
        checksum="def456",
        change_description="Added content from desktop"
    )
    
    item3 = ConflictItem(
        version_id="v3",
        device_id="tablet-001",
        device_name="iPad Pro", 
        user_id="user123",
        timestamp="2024-01-01T10:01:30",
        data={"title": "My Note", "content": "Original content here\nAdded from tablet"},
        metadata={"content_type": "text"},
        checksum="ghi789",
        change_description="Added content from tablet"
    )
    
    # Initialize conflict manager
    manager = ConflictManager()
    
    # Process conflicts
    results = manager.process_conflict("note-001", [item1, item2, item3])
    
    print(f"Resolved {len(results)} conflicts:")
    for result in results:
        print(f"  Conflict {result.conflict_id[:8]}...")
        print(f"    Strategy: {result.strategy_used.value}")
        print(f"    Confidence: {result.confidence_score:.2f}")
        print(f"    Notes: {result.user_notes}")
        if result.merged_data:
            print(f"    Merged content preview: {str(result.merged_data)[:100]}...")
        print()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())