"""
Inheritance Manager for Nested Folder Hierarchies

Manages rule and property inheritance between parent and child folders:
- Rule inheritance with override capabilities
- Setting inheritance with merge strategies
- Permission inheritance with delegation
- Template inheritance for consistent structures
- Recursive evaluation for deep hierarchies
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Tuple
from enum import Enum

from .database import db_manager

logger = logging.getLogger(__name__)

class InheritanceType(Enum):
    RULES = "rules"
    SETTINGS = "settings" 
    PERMISSIONS = "permissions"
    TEMPLATES = "templates"

class MergeStrategy(Enum):
    OVERRIDE = "override"  # Child completely overrides parent
    MERGE = "merge"       # Child merges with parent
    APPEND = "append"     # Child appends to parent
    INHERIT_ONLY = "inherit_only"  # Child only inherits, no local config

class InheritanceRule:
    """Represents an inheritance rule between parent and child folders"""
    
    def __init__(self, parent_id: str, child_id: str, inheritance_type: InheritanceType,
                 merge_strategy: MergeStrategy, config: Dict[str, Any] = None):
        self.parent_id = parent_id
        self.child_id = child_id
        self.inheritance_type = inheritance_type
        self.merge_strategy = merge_strategy
        self.config = config or {}
        self.created_at = datetime.utcnow()
        self.is_active = True
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "parent_id": self.parent_id,
            "child_id": self.child_id,
            "inheritance_type": self.inheritance_type.value,
            "merge_strategy": self.merge_strategy.value,
            "config": self.config,
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active
        }

class FolderHierarchy:
    """Represents folder hierarchy relationships"""
    
    def __init__(self):
        self.parent_to_children: Dict[str, Set[str]] = {}
        self.child_to_parent: Dict[str, str] = {}
        self.folder_depths: Dict[str, int] = {}
        
    def add_relationship(self, parent_id: str, child_id: str):
        """Add parent-child relationship"""
        if parent_id not in self.parent_to_children:
            self.parent_to_children[parent_id] = set()
        
        self.parent_to_children[parent_id].add(child_id)
        self.child_to_parent[child_id] = parent_id
        
        # Update depths
        parent_depth = self.folder_depths.get(parent_id, 0)
        self.folder_depths[child_id] = parent_depth + 1
        
    def remove_relationship(self, parent_id: str, child_id: str):
        """Remove parent-child relationship"""
        if parent_id in self.parent_to_children:
            self.parent_to_children[parent_id].discard(child_id)
            
            if not self.parent_to_children[parent_id]:
                del self.parent_to_children[parent_id]
        
        if child_id in self.child_to_parent:
            del self.child_to_parent[child_id]
            
        # Recalculate depths for affected subtree
        self._recalculate_depths(child_id)
    
    def _recalculate_depths(self, folder_id: str):
        """Recalculate depths for folder and its descendants"""
        parent_id = self.child_to_parent.get(folder_id)
        
        if parent_id:
            parent_depth = self.folder_depths.get(parent_id, 0)
            self.folder_depths[folder_id] = parent_depth + 1
        else:
            self.folder_depths[folder_id] = 0
            
        # Recursively update children
        children = self.parent_to_children.get(folder_id, set())
        for child_id in children:
            self._recalculate_depths(child_id)
    
    def get_children(self, folder_id: str) -> Set[str]:
        """Get direct children of folder"""
        return self.parent_to_children.get(folder_id, set()).copy()
    
    def get_parent(self, folder_id: str) -> Optional[str]:
        """Get parent of folder"""
        return self.child_to_parent.get(folder_id)
    
    def get_ancestors(self, folder_id: str) -> List[str]:
        """Get all ancestors of folder (bottom-up)"""
        ancestors = []
        current = folder_id
        
        while current in self.child_to_parent:
            parent = self.child_to_parent[current]
            ancestors.append(parent)
            current = parent
            
        return ancestors
    
    def get_descendants(self, folder_id: str) -> Set[str]:
        """Get all descendants of folder"""
        descendants = set()
        
        def collect_descendants(current_id: str):
            children = self.parent_to_children.get(current_id, set())
            for child_id in children:
                descendants.add(child_id)
                collect_descendants(child_id)
        
        collect_descendants(folder_id)
        return descendants
    
    def get_depth(self, folder_id: str) -> int:
        """Get depth of folder in hierarchy"""
        return self.folder_depths.get(folder_id, 0)
    
    def is_ancestor(self, potential_ancestor: str, folder_id: str) -> bool:
        """Check if one folder is ancestor of another"""
        return potential_ancestor in self.get_ancestors(folder_id)

class InheritanceManager:
    """Manages inheritance rules and evaluation for folder hierarchies"""
    
    def __init__(self):
        self.hierarchy = FolderHierarchy()
        self.inheritance_rules: Dict[str, List[InheritanceRule]] = {}  # child_id -> rules
        
        self.stats = {
            "inheritance_evaluations": 0,
            "rules_inherited": 0,
            "settings_merged": 0,
            "permission_delegations": 0
        }
    
    async def initialize(self):
        """Initialize inheritance manager"""
        
        # Load folder relationships and inheritance rules from database
        await self._load_folder_hierarchy()
        await self._load_inheritance_rules()
        
        logger.info(f"Inheritance manager initialized with {len(self.hierarchy.child_to_parent)} relationships")
    
    async def _load_folder_hierarchy(self):
        """Load folder parent-child relationships from database"""
        
        try:
            query = """
            SELECT id, parent_folder_id, folder_path
            FROM smart_folders 
            WHERE is_active = true
            ORDER BY created_at
            """
            
            rows = await db_manager.database.fetch_all(query)
            
            for row in rows:
                folder_id = row["id"]
                parent_id = row.get("parent_folder_id")
                
                if parent_id:
                    self.hierarchy.add_relationship(parent_id, folder_id)
                    
        except Exception as e:
            logger.error(f"Error loading folder hierarchy: {e}")
    
    async def _load_inheritance_rules(self):
        """Load inheritance rules from database"""
        
        try:
            # This would load from a dedicated inheritance_rules table
            # For now, we'll check folder settings for inheritance config
            query = """
            SELECT id, settings, folder_path
            FROM smart_folders 
            WHERE is_active = true AND settings IS NOT NULL
            """
            
            rows = await db_manager.database.fetch_all(query)
            
            for row in rows:
                folder_id = row["id"]
                settings = row.get("settings", {})
                
                # Check for inheritance configuration in settings
                inheritance_config = settings.get("inheritance", {})
                if inheritance_config:
                    self._process_inheritance_config(folder_id, inheritance_config)
                    
        except Exception as e:
            logger.error(f"Error loading inheritance rules: {e}")
    
    def _process_inheritance_config(self, folder_id: str, config: Dict[str, Any]):
        """Process inheritance configuration for a folder"""
        
        parent_id = self.hierarchy.get_parent(folder_id)
        if not parent_id:
            return
        
        for inheritance_type_str, rule_config in config.items():
            try:
                inheritance_type = InheritanceType(inheritance_type_str)
                merge_strategy = MergeStrategy(rule_config.get("strategy", "merge"))
                
                rule = InheritanceRule(
                    parent_id, folder_id, inheritance_type, merge_strategy, rule_config
                )
                
                if folder_id not in self.inheritance_rules:
                    self.inheritance_rules[folder_id] = []
                
                self.inheritance_rules[folder_id].append(rule)
                
            except ValueError as e:
                logger.warning(f"Invalid inheritance configuration for folder {folder_id}: {e}")
    
    async def create_folder_relationship(self, parent_id: str, child_id: str, 
                                       inheritance_config: Dict[str, Any] = None) -> bool:
        """Create parent-child relationship with optional inheritance rules"""
        
        try:
            # Add to hierarchy
            self.hierarchy.add_relationship(parent_id, child_id)
            
            # Create default inheritance rules if not specified
            if not inheritance_config:
                inheritance_config = {
                    "rules": {"strategy": "merge"},
                    "settings": {"strategy": "merge"}
                }
            
            # Process inheritance configuration
            self._process_inheritance_config(child_id, inheritance_config)
            
            # Update database
            await db_manager.database.execute(
                "UPDATE smart_folders SET parent_folder_id = :parent_id WHERE id = :child_id",
                values={"parent_id": parent_id, "child_id": child_id}
            )
            
            logger.info(f"Created folder relationship: {parent_id} -> {child_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating folder relationship: {e}")
            return False
    
    async def evaluate_inherited_rules(self, folder_id: str) -> List[Dict[str, Any]]:
        """Evaluate and return effective rules for folder including inherited ones"""
        
        self.stats["inheritance_evaluations"] += 1
        
        try:
            # Get folder's direct rules
            folder = await db_manager.get_smart_folder(folder_id)
            if not folder:
                return []
            
            direct_rules = folder.get("rules", [])
            
            # Get inheritance rules for this folder
            inheritance_rules = self.inheritance_rules.get(folder_id, [])
            rules_inheritance = next(
                (rule for rule in inheritance_rules if rule.inheritance_type == InheritanceType.RULES),
                None
            )
            
            if not rules_inheritance:
                return direct_rules
            
            # Get parent's effective rules (recursive)
            parent_id = self.hierarchy.get_parent(folder_id)
            if not parent_id:
                return direct_rules
            
            parent_rules = await self.evaluate_inherited_rules(parent_id)
            
            # Apply merge strategy
            effective_rules = self._merge_rules(
                parent_rules, direct_rules, rules_inheritance.merge_strategy
            )
            
            self.stats["rules_inherited"] += len(parent_rules)
            
            return effective_rules
            
        except Exception as e:
            logger.error(f"Error evaluating inherited rules for folder {folder_id}: {e}")
            return []
    
    def _merge_rules(self, parent_rules: List[Dict[str, Any]], 
                    child_rules: List[Dict[str, Any]], 
                    strategy: MergeStrategy) -> List[Dict[str, Any]]:
        """Merge parent and child rules according to strategy"""
        
        if strategy == MergeStrategy.OVERRIDE:
            return child_rules if child_rules else parent_rules
        
        elif strategy == MergeStrategy.INHERIT_ONLY:
            return parent_rules
        
        elif strategy == MergeStrategy.APPEND:
            return parent_rules + child_rules
        
        elif strategy == MergeStrategy.MERGE:
            # Merge rules, with child rules taking precedence for conflicts
            merged_rules = parent_rules.copy()
            
            # Create index for quick lookup of parent rules by field
            parent_rule_index = {}
            for i, rule in enumerate(parent_rules):
                field = rule.get("field")
                if field:
                    parent_rule_index[field] = i
            
            # Process child rules
            for child_rule in child_rules:
                field = child_rule.get("field")
                
                if field in parent_rule_index:
                    # Replace parent rule with child rule
                    merged_rules[parent_rule_index[field]] = child_rule
                else:
                    # Add new child rule
                    merged_rules.append(child_rule)
            
            return merged_rules
        
        else:
            logger.warning(f"Unknown merge strategy: {strategy}")
            return child_rules
    
    async def evaluate_inherited_settings(self, folder_id: str) -> Dict[str, Any]:
        """Evaluate and return effective settings for folder including inherited ones"""
        
        try:
            # Get folder's direct settings
            folder = await db_manager.get_smart_folder(folder_id)
            if not folder:
                return {}
            
            direct_settings = folder.get("settings", {})
            
            # Get inheritance rules for this folder
            inheritance_rules = self.inheritance_rules.get(folder_id, [])
            settings_inheritance = next(
                (rule for rule in inheritance_rules if rule.inheritance_type == InheritanceType.SETTINGS),
                None
            )
            
            if not settings_inheritance:
                return direct_settings
            
            # Get parent's effective settings (recursive)
            parent_id = self.hierarchy.get_parent(folder_id)
            if not parent_id:
                return direct_settings
            
            parent_settings = await self.evaluate_inherited_settings(parent_id)
            
            # Apply merge strategy
            effective_settings = self._merge_settings(
                parent_settings, direct_settings, settings_inheritance.merge_strategy
            )
            
            self.stats["settings_merged"] += 1
            
            return effective_settings
            
        except Exception as e:
            logger.error(f"Error evaluating inherited settings for folder {folder_id}: {e}")
            return {}
    
    def _merge_settings(self, parent_settings: Dict[str, Any], 
                       child_settings: Dict[str, Any],
                       strategy: MergeStrategy) -> Dict[str, Any]:
        """Merge parent and child settings according to strategy"""
        
        if strategy == MergeStrategy.OVERRIDE:
            return child_settings if child_settings else parent_settings
        
        elif strategy == MergeStrategy.INHERIT_ONLY:
            return parent_settings
        
        elif strategy == MergeStrategy.MERGE:
            # Deep merge settings
            merged = parent_settings.copy()
            
            for key, value in child_settings.items():
                if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                    # Recursively merge dict values
                    merged[key] = {**merged[key], **value}
                else:
                    # Override with child value
                    merged[key] = value
            
            return merged
        
        else:
            return child_settings
    
    async def get_folder_hierarchy_info(self, folder_id: str) -> Dict[str, Any]:
        """Get hierarchy information for a folder"""
        
        try:
            return {
                "folder_id": folder_id,
                "parent_id": self.hierarchy.get_parent(folder_id),
                "children": list(self.hierarchy.get_children(folder_id)),
                "ancestors": self.hierarchy.get_ancestors(folder_id),
                "descendants": list(self.hierarchy.get_descendants(folder_id)),
                "depth": self.hierarchy.get_depth(folder_id),
                "inheritance_rules": [
                    rule.to_dict() for rule in self.inheritance_rules.get(folder_id, [])
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting hierarchy info for folder {folder_id}: {e}")
            return {}
    
    async def propagate_changes_to_children(self, folder_id: str, 
                                          change_type: InheritanceType) -> Dict[str, Any]:
        """Propagate changes from parent to all descendants"""
        
        try:
            descendants = self.hierarchy.get_descendants(folder_id)
            affected_folders = []
            
            for descendant_id in descendants:
                # Check if descendant has inheritance rule for this change type
                inheritance_rules = self.inheritance_rules.get(descendant_id, [])
                relevant_rule = next(
                    (rule for rule in inheritance_rules if rule.inheritance_type == change_type),
                    None
                )
                
                if relevant_rule:
                    # Re-evaluate this folder
                    if change_type == InheritanceType.RULES:
                        await self.evaluate_inherited_rules(descendant_id)
                    elif change_type == InheritanceType.SETTINGS:
                        await self.evaluate_inherited_settings(descendant_id)
                    
                    affected_folders.append(descendant_id)
            
            return {
                "parent_folder_id": folder_id,
                "change_type": change_type.value,
                "affected_folders": affected_folders,
                "propagation_count": len(affected_folders)
            }
            
        except Exception as e:
            logger.error(f"Error propagating changes: {e}")
            return {"error": str(e)}
    
    async def validate_hierarchy(self) -> Dict[str, Any]:
        """Validate folder hierarchy for cycles and consistency"""
        
        issues = []
        
        try:
            # Check for cycles
            visited = set()
            rec_stack = set()
            
            def has_cycle(folder_id: str) -> bool:
                if folder_id in rec_stack:
                    return True
                
                if folder_id in visited:
                    return False
                
                visited.add(folder_id)
                rec_stack.add(folder_id)
                
                children = self.hierarchy.get_children(folder_id)
                for child_id in children:
                    if has_cycle(child_id):
                        return True
                
                rec_stack.remove(folder_id)
                return False
            
            # Check all root folders (folders without parents)
            root_folders = set()
            for folder_id in self.hierarchy.folder_depths.keys():
                if self.hierarchy.get_parent(folder_id) is None:
                    root_folders.add(folder_id)
            
            for root_id in root_folders:
                if has_cycle(root_id):
                    issues.append(f"Cycle detected starting from folder {root_id}")
            
            # Check for orphaned inheritance rules
            for child_id, rules in self.inheritance_rules.items():
                parent_id = self.hierarchy.get_parent(child_id)
                if not parent_id:
                    issues.append(f"Inheritance rules exist for folder {child_id} but no parent found")
            
            return {
                "valid": len(issues) == 0,
                "issues": issues,
                "total_folders": len(self.hierarchy.folder_depths),
                "root_folders": list(root_folders),
                "max_depth": max(self.hierarchy.folder_depths.values()) if self.hierarchy.folder_depths else 0
            }
            
        except Exception as e:
            logger.error(f"Error validating hierarchy: {e}")
            return {"valid": False, "error": str(e)}
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """Get inheritance manager statistics"""
        
        stats = self.stats.copy()
        
        # Add current state
        stats.update({
            "total_relationships": len(self.hierarchy.child_to_parent),
            "total_inheritance_rules": sum(len(rules) for rules in self.inheritance_rules.values()),
            "max_hierarchy_depth": max(self.hierarchy.folder_depths.values()) if self.hierarchy.folder_depths else 0,
            "root_folder_count": sum(1 for depth in self.hierarchy.folder_depths.values() if depth == 0)
        })
        
        return stats