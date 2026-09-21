"""
Interface Versioning System
Version control and management for UI interfaces and components
"""

from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel
from datetime import datetime
import json
import uuid
import hashlib
from enum import Enum
import difflib

class VersionType(str, Enum):
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"

class ChangeType(str, Enum):
    ADDED = "added"
    MODIFIED = "modified"
    REMOVED = "removed"
    MOVED = "moved"
    RENAMED = "renamed"

class InterfaceSnapshot(BaseModel):
    """Snapshot of interface state at a point in time"""
    id: str
    interface_id: str
    version: str
    title: str
    description: str = ""
    
    # Interface data
    components: List[Dict[str, Any]]
    layout: Dict[str, Any]
    theme_id: str = ""
    settings: Dict[str, Any] = {}
    
    # Version metadata
    created_by: str
    created_at: datetime
    parent_version: Optional[str] = None
    tags: List[str] = []
    
    # Checksums for integrity
    component_hash: str
    layout_hash: str
    
    # Change information
    changes: List[Dict[str, Any]] = []
    change_summary: str = ""

class VersionBranch(BaseModel):
    """Version branch for parallel development"""
    id: str
    name: str
    interface_id: str
    base_version: str
    head_version: str
    created_by: str
    created_at: datetime
    is_active: bool = True
    description: str = ""

class VersionMerge(BaseModel):
    """Record of version merge operation"""
    id: str
    interface_id: str
    source_version: str
    target_version: str
    result_version: str
    merged_by: str
    merged_at: datetime
    conflicts: List[Dict[str, Any]] = []
    resolution: Dict[str, Any] = {}

class VersionComparison(BaseModel):
    """Comparison between two versions"""
    id: str
    interface_id: str
    version_a: str
    version_b: str
    
    # Component changes
    components_added: List[Dict[str, Any]] = []
    components_removed: List[Dict[str, Any]] = []
    components_modified: List[Dict[str, Any]] = []
    
    # Layout changes
    layout_changes: List[Dict[str, Any]] = []
    
    # Theme changes
    theme_changes: Dict[str, Any] = {}
    
    # Settings changes
    settings_changes: Dict[str, Any] = {}
    
    created_at: datetime

class InterfaceVersioning:
    """Interface versioning and version control system"""
    
    def __init__(self):
        self.snapshots: Dict[str, InterfaceSnapshot] = {}
        self.branches: Dict[str, VersionBranch] = {}
        self.merges: Dict[str, VersionMerge] = {}
        self.comparisons: Dict[str, VersionComparison] = {}
        
        # Version tracking by interface
        self.interface_versions: Dict[str, List[str]] = {}
        self.interface_current: Dict[str, str] = {}
    
    def create_snapshot(self, interface_id: str, version: str, title: str,
                       components: List[Dict[str, Any]], layout: Dict[str, Any],
                       created_by: str, description: str = "",
                       theme_id: str = "", settings: Dict[str, Any] = None) -> str:
        """Create new version snapshot"""
        
        snapshot_id = str(uuid.uuid4())
        settings = settings or {}
        
        # Calculate hashes
        component_hash = self._calculate_hash(components)
        layout_hash = self._calculate_hash(layout)
        
        # Get parent version
        parent_version = self.interface_current.get(interface_id)
        
        # Calculate changes from parent
        changes = []
        change_summary = ""
        
        if parent_version:
            parent_snapshot = self.snapshots.get(parent_version)
            if parent_snapshot:
                changes = self._calculate_changes(parent_snapshot, {
                    "components": components,
                    "layout": layout,
                    "theme_id": theme_id,
                    "settings": settings
                })
                change_summary = self._generate_change_summary(changes)
        
        snapshot = InterfaceSnapshot(
            id=snapshot_id,
            interface_id=interface_id,
            version=version,
            title=title,
            description=description,
            components=components,
            layout=layout,
            theme_id=theme_id,
            settings=settings,
            created_by=created_by,
            created_at=datetime.now(),
            parent_version=parent_version,
            component_hash=component_hash,
            layout_hash=layout_hash,
            changes=changes,
            change_summary=change_summary
        )
        
        self.snapshots[snapshot_id] = snapshot
        
        # Update version tracking
        if interface_id not in self.interface_versions:
            self.interface_versions[interface_id] = []
        
        self.interface_versions[interface_id].append(snapshot_id)
        self.interface_current[interface_id] = snapshot_id
        
        return snapshot_id
    
    def get_snapshot(self, snapshot_id: str) -> Optional[InterfaceSnapshot]:
        """Get snapshot by ID"""
        return self.snapshots.get(snapshot_id)
    
    def get_interface_versions(self, interface_id: str) -> List[InterfaceSnapshot]:
        """Get all versions for an interface"""
        version_ids = self.interface_versions.get(interface_id, [])
        return [self.snapshots[vid] for vid in version_ids if vid in self.snapshots]
    
    def get_current_version(self, interface_id: str) -> Optional[InterfaceSnapshot]:
        """Get current version of interface"""
        current_id = self.interface_current.get(interface_id)
        return self.snapshots.get(current_id) if current_id else None
    
    def revert_to_version(self, interface_id: str, version_id: str) -> str:
        """Revert interface to specific version"""
        target_snapshot = self.snapshots.get(version_id)
        if not target_snapshot or target_snapshot.interface_id != interface_id:
            raise ValueError("Version not found or doesn't belong to interface")
        
        # Create new snapshot based on target version
        new_version = self._increment_version(
            self._get_latest_version(interface_id), VersionType.MINOR
        )
        
        revert_snapshot_id = self.create_snapshot(
            interface_id=interface_id,
            version=new_version,
            title=f"Revert to {target_snapshot.version}",
            components=target_snapshot.components,
            layout=target_snapshot.layout,
            created_by="system",
            description=f"Reverted to version {target_snapshot.version}",
            theme_id=target_snapshot.theme_id,
            settings=target_snapshot.settings
        )
        
        return revert_snapshot_id
    
    def create_branch(self, interface_id: str, name: str, base_version: str,
                     created_by: str, description: str = "") -> str:
        """Create new branch from version"""
        if base_version not in self.snapshots:
            raise ValueError("Base version not found")
        
        base_snapshot = self.snapshots[base_version]
        if base_snapshot.interface_id != interface_id:
            raise ValueError("Base version doesn't belong to interface")
        
        branch_id = str(uuid.uuid4())
        
        branch = VersionBranch(
            id=branch_id,
            name=name,
            interface_id=interface_id,
            base_version=base_version,
            head_version=base_version,
            created_by=created_by,
            created_at=datetime.now(),
            description=description
        )
        
        self.branches[branch_id] = branch
        return branch_id
    
    def merge_branch(self, interface_id: str, source_branch_id: str,
                    target_version: str, merged_by: str,
                    resolve_conflicts: Dict[str, Any] = None) -> str:
        """Merge branch into target version"""
        
        source_branch = self.branches.get(source_branch_id)
        if not source_branch or source_branch.interface_id != interface_id:
            raise ValueError("Source branch not found or invalid")
        
        target_snapshot = self.snapshots.get(target_version)
        if not target_snapshot or target_snapshot.interface_id != interface_id:
            raise ValueError("Target version not found or invalid")
        
        source_snapshot = self.snapshots[source_branch.head_version]
        
        # Detect conflicts
        conflicts = self._detect_merge_conflicts(source_snapshot, target_snapshot)
        
        # Merge data
        merged_data = self._merge_snapshots(
            source_snapshot, target_snapshot, resolve_conflicts or {}
        )
        
        # Create merged version
        new_version = self._increment_version(
            self._get_latest_version(interface_id), VersionType.MINOR
        )
        
        merged_snapshot_id = self.create_snapshot(
            interface_id=interface_id,
            version=new_version,
            title=f"Merge {source_branch.name} into {target_snapshot.version}",
            components=merged_data["components"],
            layout=merged_data["layout"],
            created_by=merged_by,
            description=f"Merged branch '{source_branch.name}'",
            theme_id=merged_data["theme_id"],
            settings=merged_data["settings"]
        )
        
        # Record merge
        merge_id = str(uuid.uuid4())
        merge_record = VersionMerge(
            id=merge_id,
            interface_id=interface_id,
            source_version=source_branch.head_version,
            target_version=target_version,
            result_version=merged_snapshot_id,
            merged_by=merged_by,
            merged_at=datetime.now(),
            conflicts=[c.dict() for c in conflicts],
            resolution=resolve_conflicts or {}
        )
        
        self.merges[merge_id] = merge_record
        
        # Deactivate branch
        source_branch.is_active = False
        
        return merged_snapshot_id
    
    def compare_versions(self, interface_id: str, version_a: str, version_b: str) -> str:
        """Compare two versions and return differences"""
        
        snapshot_a = self.snapshots.get(version_a)
        snapshot_b = self.snapshots.get(version_b)
        
        if not snapshot_a or not snapshot_b:
            raise ValueError("One or both versions not found")
        
        if snapshot_a.interface_id != interface_id or snapshot_b.interface_id != interface_id:
            raise ValueError("Versions don't belong to interface")
        
        comparison_id = str(uuid.uuid4())
        
        # Compare components
        components_added, components_removed, components_modified = self._compare_components(
            snapshot_a.components, snapshot_b.components
        )
        
        # Compare layout
        layout_changes = self._compare_layout(snapshot_a.layout, snapshot_b.layout)
        
        # Compare theme
        theme_changes = {}
        if snapshot_a.theme_id != snapshot_b.theme_id:
            theme_changes = {
                "from": snapshot_a.theme_id,
                "to": snapshot_b.theme_id
            }
        
        # Compare settings
        settings_changes = self._compare_settings(snapshot_a.settings, snapshot_b.settings)
        
        comparison = VersionComparison(
            id=comparison_id,
            interface_id=interface_id,
            version_a=version_a,
            version_b=version_b,
            components_added=components_added,
            components_removed=components_removed,
            components_modified=components_modified,
            layout_changes=layout_changes,
            theme_changes=theme_changes,
            settings_changes=settings_changes,
            created_at=datetime.now()
        )
        
        self.comparisons[comparison_id] = comparison
        return comparison_id
    
    def get_version_history(self, interface_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get version history for interface"""
        versions = self.get_interface_versions(interface_id)
        versions.sort(key=lambda v: v.created_at, reverse=True)
        
        history = []
        for version in versions[:limit]:
            history.append({
                "id": version.id,
                "version": version.version,
                "title": version.title,
                "description": version.description,
                "created_by": version.created_by,
                "created_at": version.created_at.isoformat(),
                "change_summary": version.change_summary,
                "component_count": len(version.components),
                "tags": version.tags
            })
        
        return history
    
    def tag_version(self, version_id: str, tags: List[str]):
        """Add tags to version"""
        snapshot = self.snapshots.get(version_id)
        if snapshot:
            snapshot.tags.extend(tags)
            # Remove duplicates
            snapshot.tags = list(set(snapshot.tags))
    
    def search_versions(self, interface_id: str, query: str = "",
                       tags: List[str] = None, created_by: str = "",
                       date_from: datetime = None, date_to: datetime = None) -> List[InterfaceSnapshot]:
        """Search versions by criteria"""
        
        versions = self.get_interface_versions(interface_id)
        results = []
        
        query_lower = query.lower() if query else ""
        tags = tags or []
        
        for version in versions:
            # Text search
            if query_lower:
                searchable_text = f"{version.title} {version.description} {version.change_summary}".lower()
                if query_lower not in searchable_text:
                    continue
            
            # Tag filter
            if tags and not any(tag in version.tags for tag in tags):
                continue
            
            # Creator filter
            if created_by and version.created_by != created_by:
                continue
            
            # Date filters
            if date_from and version.created_at < date_from:
                continue
            if date_to and version.created_at > date_to:
                continue
            
            results.append(version)
        
        return sorted(results, key=lambda v: v.created_at, reverse=True)
    
    def _calculate_hash(self, data: Any) -> str:
        """Calculate hash for data integrity"""
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    def _calculate_changes(self, old_snapshot: InterfaceSnapshot, new_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Calculate changes between snapshots"""
        changes = []
        
        # Compare components
        old_components = {c.get("id"): c for c in old_snapshot.components}
        new_components = {c.get("id"): c for c in new_data["components"]}
        
        # Added components
        for comp_id, comp_data in new_components.items():
            if comp_id not in old_components:
                changes.append({
                    "type": ChangeType.ADDED.value,
                    "target": "component",
                    "id": comp_id,
                    "data": comp_data
                })
        
        # Removed components
        for comp_id, comp_data in old_components.items():
            if comp_id not in new_components:
                changes.append({
                    "type": ChangeType.REMOVED.value,
                    "target": "component",
                    "id": comp_id,
                    "data": comp_data
                })
        
        # Modified components
        for comp_id in old_components:
            if comp_id in new_components:
                if old_components[comp_id] != new_components[comp_id]:
                    changes.append({
                        "type": ChangeType.MODIFIED.value,
                        "target": "component",
                        "id": comp_id,
                        "old_data": old_components[comp_id],
                        "new_data": new_components[comp_id]
                    })
        
        # Compare layout
        if old_snapshot.layout != new_data["layout"]:
            changes.append({
                "type": ChangeType.MODIFIED.value,
                "target": "layout",
                "old_data": old_snapshot.layout,
                "new_data": new_data["layout"]
            })
        
        # Compare theme
        if old_snapshot.theme_id != new_data["theme_id"]:
            changes.append({
                "type": ChangeType.MODIFIED.value,
                "target": "theme",
                "old_data": old_snapshot.theme_id,
                "new_data": new_data["theme_id"]
            })
        
        return changes
    
    def _generate_change_summary(self, changes: List[Dict[str, Any]]) -> str:
        """Generate human-readable change summary"""
        if not changes:
            return "No changes"
        
        summary_parts = []
        
        # Count changes by type
        added_components = len([c for c in changes if c["type"] == "added" and c["target"] == "component"])
        removed_components = len([c for c in changes if c["type"] == "removed" and c["target"] == "component"])
        modified_components = len([c for c in changes if c["type"] == "modified" and c["target"] == "component"])
        
        if added_components:
            summary_parts.append(f"Added {added_components} component(s)")
        if removed_components:
            summary_parts.append(f"Removed {removed_components} component(s)")
        if modified_components:
            summary_parts.append(f"Modified {modified_components} component(s)")
        
        # Layout changes
        layout_changes = [c for c in changes if c["target"] == "layout"]
        if layout_changes:
            summary_parts.append("Updated layout")
        
        # Theme changes
        theme_changes = [c for c in changes if c["target"] == "theme"]
        if theme_changes:
            summary_parts.append("Changed theme")
        
        return ", ".join(summary_parts) if summary_parts else "Minor changes"
    
    def _increment_version(self, current_version: str, version_type: VersionType) -> str:
        """Increment version number"""
        if not current_version:
            return "1.0.0"
        
        try:
            parts = current_version.split(".")
            major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
            
            if version_type == VersionType.MAJOR:
                return f"{major + 1}.0.0"
            elif version_type == VersionType.MINOR:
                return f"{major}.{minor + 1}.0"
            else:  # PATCH
                return f"{major}.{minor}.{patch + 1}"
        except (ValueError, IndexError):
            return "1.0.0"
    
    def _get_latest_version(self, interface_id: str) -> str:
        """Get latest version number for interface"""
        versions = self.get_interface_versions(interface_id)
        if not versions:
            return "0.0.0"
        
        latest = max(versions, key=lambda v: v.created_at)
        return latest.version
    
    def _detect_merge_conflicts(self, source: InterfaceSnapshot, target: InterfaceSnapshot) -> List[Dict[str, Any]]:
        """Detect conflicts between two snapshots"""
        conflicts = []
        
        # Component conflicts
        source_components = {c.get("id"): c for c in source.components}
        target_components = {c.get("id"): c for c in target.components}
        
        for comp_id in source_components:
            if comp_id in target_components:
                if source_components[comp_id] != target_components[comp_id]:
                    conflicts.append({
                        "type": "component_conflict",
                        "component_id": comp_id,
                        "source_data": source_components[comp_id],
                        "target_data": target_components[comp_id]
                    })
        
        # Layout conflicts
        if source.layout != target.layout:
            conflicts.append({
                "type": "layout_conflict",
                "source_data": source.layout,
                "target_data": target.layout
            })
        
        return conflicts
    
    def _merge_snapshots(self, source: InterfaceSnapshot, target: InterfaceSnapshot,
                        conflict_resolutions: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two snapshots with conflict resolution"""
        
        # Start with target as base
        merged_components = target.components.copy()
        merged_layout = target.layout.copy()
        merged_theme_id = target.theme_id
        merged_settings = target.settings.copy()
        
        # Apply source changes
        source_components = {c.get("id"): c for c in source.components}
        target_components = {c.get("id"): c for c in merged_components}
        
        # Add new components from source
        for comp_id, comp_data in source_components.items():
            if comp_id not in target_components:
                merged_components.append(comp_data)
        
        # Apply conflict resolutions
        for conflict_id, resolution in conflict_resolutions.items():
            if resolution == "source":
                # Use source version
                pass  # Implementation depends on conflict type
            elif resolution == "target":
                # Use target version (already applied)
                pass
            elif resolution == "custom":
                # Apply custom resolution
                pass
        
        return {
            "components": merged_components,
            "layout": merged_layout,
            "theme_id": merged_theme_id,
            "settings": merged_settings
        }
    
    def _compare_components(self, components_a: List[Dict], components_b: List[Dict]) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """Compare component lists"""
        
        components_a_dict = {c.get("id"): c for c in components_a}
        components_b_dict = {c.get("id"): c for c in components_b}
        
        added = []
        removed = []
        modified = []
        
        # Find added components
        for comp_id, comp_data in components_b_dict.items():
            if comp_id not in components_a_dict:
                added.append(comp_data)
        
        # Find removed components
        for comp_id, comp_data in components_a_dict.items():
            if comp_id not in components_b_dict:
                removed.append(comp_data)
        
        # Find modified components
        for comp_id in components_a_dict:
            if comp_id in components_b_dict:
                if components_a_dict[comp_id] != components_b_dict[comp_id]:
                    modified.append({
                        "id": comp_id,
                        "old": components_a_dict[comp_id],
                        "new": components_b_dict[comp_id]
                    })
        
        return added, removed, modified
    
    def _compare_layout(self, layout_a: Dict, layout_b: Dict) -> List[Dict[str, Any]]:
        """Compare layout configurations"""
        changes = []
        
        # Simple deep comparison (in production, use more sophisticated diff)
        if layout_a != layout_b:
            changes.append({
                "type": "layout_changed",
                "old": layout_a,
                "new": layout_b
            })
        
        return changes
    
    def _compare_settings(self, settings_a: Dict, settings_b: Dict) -> Dict[str, Any]:
        """Compare settings"""
        changes = {}
        
        all_keys = set(settings_a.keys()) | set(settings_b.keys())
        
        for key in all_keys:
            value_a = settings_a.get(key)
            value_b = settings_b.get(key)
            
            if value_a != value_b:
                changes[key] = {
                    "old": value_a,
                    "new": value_b
                }
        
        return changes
    
    def export_version(self, version_id: str) -> Dict[str, Any]:
        """Export version data"""
        snapshot = self.snapshots.get(version_id)
        if not snapshot:
            raise ValueError("Version not found")
        
        return {
            "snapshot": snapshot.dict(),
            "metadata": {
                "exported_at": datetime.now().isoformat(),
                "export_format_version": "1.0.0"
            }
        }
    
    def import_version(self, interface_id: str, version_data: Dict[str, Any], imported_by: str) -> str:
        """Import version from exported data"""
        snapshot_dict = version_data.get("snapshot", {})
        
        # Create new snapshot with imported data
        new_version = self._increment_version(
            self._get_latest_version(interface_id), VersionType.MINOR
        )
        
        return self.create_snapshot(
            interface_id=interface_id,
            version=new_version,
            title=f"Imported: {snapshot_dict.get('title', 'Untitled')}",
            components=snapshot_dict.get("components", []),
            layout=snapshot_dict.get("layout", {}),
            created_by=imported_by,
            description=f"Imported version from external source",
            theme_id=snapshot_dict.get("theme_id", ""),
            settings=snapshot_dict.get("settings", {})
        )