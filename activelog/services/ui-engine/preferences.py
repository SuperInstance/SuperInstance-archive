"""
Preference Persistence System
User preferences and settings management with synchronization
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import json
import uuid
import asyncio
import sqlite3
import os
from enum import Enum

class PreferenceScope(str, Enum):
    USER = "user"
    PROJECT = "project"
    WORKSPACE = "workspace"
    GLOBAL = "global"

class PreferenceType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    COLOR = "color"
    FONT = "font"

class SyncStatus(str, Enum):
    SYNCED = "synced"
    PENDING = "pending"
    CONFLICT = "conflict"
    ERROR = "error"

class PreferenceDefinition(BaseModel):
    """Definition of a preference setting"""
    key: str
    name: str
    description: str
    type: PreferenceType
    default_value: Any
    scope: PreferenceScope
    category: str = "general"
    
    # Validation
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    allowed_values: Optional[List[Any]] = None
    pattern: Optional[str] = None  # Regex pattern for string validation
    
    # UI hints
    ui_component: str = "input"  # input, select, checkbox, color-picker, etc.
    ui_options: Dict[str, Any] = {}
    
    # Metadata
    is_sensitive: bool = False  # Don't sync sensitive data
    requires_restart: bool = False
    deprecated: bool = False
    added_in_version: str = "1.0.0"

class PreferenceValue(BaseModel):
    """A preference value with metadata"""
    key: str
    value: Any
    scope: PreferenceScope
    scope_id: str  # user_id, project_id, workspace_id, or "global"
    
    # Metadata
    set_by: str
    set_at: datetime
    sync_status: SyncStatus = SyncStatus.SYNCED
    last_synced: Optional[datetime] = None
    conflict_data: Optional[Dict[str, Any]] = None
    
    # Change tracking
    previous_value: Optional[Any] = None
    change_reason: str = ""

class PreferenceSchema(BaseModel):
    """Schema defining available preferences"""
    version: str
    categories: Dict[str, Dict[str, str]]  # category_id -> {name, description}
    preferences: List[PreferenceDefinition]

class UserProfile(BaseModel):
    """User preference profile"""
    id: str
    user_id: str
    name: str
    description: str = ""
    
    # Profile settings
    theme: str = "default"
    language: str = "en"
    timezone: str = "UTC"
    
    # UI preferences
    sidebar_width: int = 280
    sidebar_collapsed: bool = False
    panel_layout: str = "default"
    zoom_level: float = 1.0
    
    # Editor preferences
    editor_theme: str = "default"
    editor_font_size: int = 14
    editor_font_family: str = "monospace"
    editor_line_numbers: bool = True
    editor_word_wrap: bool = False
    
    # Behavior preferences
    auto_save: bool = True
    auto_save_interval: int = 30  # seconds
    show_tooltips: bool = True
    confirm_deletions: bool = True
    
    # Advanced preferences
    debug_mode: bool = False
    performance_mode: bool = False
    telemetry_enabled: bool = True
    
    created_at: datetime
    updated_at: datetime

class PreferenceManager:
    """Preference persistence and management system"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or "/home/activeloguser/activelog/services/ui-engine/data/preferences.db"
        self.preferences: Dict[str, PreferenceValue] = {}
        self.schemas: Dict[str, PreferenceSchema] = {}
        self.user_profiles: Dict[str, UserProfile] = {}
        self.change_listeners: List[callable] = []
        
        # Ensure database directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        # Load default schema
        self._load_default_schema()
        
        # Load preferences from database
        self._load_preferences()
    
    def _init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Preferences table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT NOT NULL,
                scope TEXT NOT NULL,
                scope_id TEXT NOT NULL,
                value TEXT NOT NULL,
                set_by TEXT,
                set_at TIMESTAMP,
                sync_status TEXT DEFAULT 'synced',
                last_synced TIMESTAMP,
                conflict_data TEXT,
                previous_value TEXT,
                change_reason TEXT,
                PRIMARY KEY (key, scope, scope_id)
            )
        ''')
        
        # User profiles table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profiles (
                id TEXT PRIMARY KEY,
                user_id TEXT UNIQUE,
                name TEXT,
                description TEXT,
                profile_data TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        ''')
        
        # Preference schemas table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS preference_schemas (
                version TEXT PRIMARY KEY,
                schema_data TEXT,
                created_at TIMESTAMP
            )
        ''')
        
        # Sync log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_log (
                id TEXT PRIMARY KEY,
                operation TEXT,
                key TEXT,
                scope TEXT,
                scope_id TEXT,
                status TEXT,
                details TEXT,
                timestamp TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_default_schema(self):
        """Load default preference schema"""
        default_schema = PreferenceSchema(
            version="1.0.0",
            categories={
                "general": {"name": "General", "description": "General application settings"},
                "appearance": {"name": "Appearance", "description": "Visual and theme settings"},
                "editor": {"name": "Editor", "description": "Code editor preferences"},
                "behavior": {"name": "Behavior", "description": "Application behavior settings"},
                "advanced": {"name": "Advanced", "description": "Advanced and debug settings"},
                "sync": {"name": "Sync", "description": "Synchronization settings"}
            },
            preferences=[
                # General preferences
                PreferenceDefinition(
                    key="language",
                    name="Language",
                    description="Interface language",
                    type=PreferenceType.STRING,
                    default_value="en",
                    scope=PreferenceScope.USER,
                    category="general",
                    ui_component="select",
                    ui_options={"options": ["en", "es", "fr", "de", "ja", "zh"]}
                ),
                PreferenceDefinition(
                    key="timezone",
                    name="Timezone", 
                    description="User timezone",
                    type=PreferenceType.STRING,
                    default_value="UTC",
                    scope=PreferenceScope.USER,
                    category="general"
                ),
                
                # Appearance preferences
                PreferenceDefinition(
                    key="theme",
                    name="Theme",
                    description="Application theme",
                    type=PreferenceType.STRING,
                    default_value="default",
                    scope=PreferenceScope.USER,
                    category="appearance",
                    ui_component="select",
                    ui_options={"options": ["default", "dark", "light", "auto"]}
                ),
                PreferenceDefinition(
                    key="zoom_level",
                    name="Zoom Level",
                    description="Interface zoom level",
                    type=PreferenceType.NUMBER,
                    default_value=1.0,
                    scope=PreferenceScope.USER,
                    category="appearance",
                    min_value=0.5,
                    max_value=3.0,
                    ui_component="slider",
                    ui_options={"step": 0.1}
                ),
                PreferenceDefinition(
                    key="sidebar_width",
                    name="Sidebar Width",
                    description="Width of the sidebar in pixels",
                    type=PreferenceType.NUMBER,
                    default_value=280,
                    scope=PreferenceScope.USER,
                    category="appearance",
                    min_value=200,
                    max_value=500
                ),
                
                # Editor preferences
                PreferenceDefinition(
                    key="editor.font_size",
                    name="Editor Font Size",
                    description="Font size in the code editor",
                    type=PreferenceType.NUMBER,
                    default_value=14,
                    scope=PreferenceScope.USER,
                    category="editor",
                    min_value=8,
                    max_value=32
                ),
                PreferenceDefinition(
                    key="editor.font_family",
                    name="Editor Font Family",
                    description="Font family for the code editor",
                    type=PreferenceType.FONT,
                    default_value="JetBrains Mono, Consolas, Monaco, monospace",
                    scope=PreferenceScope.USER,
                    category="editor"
                ),
                PreferenceDefinition(
                    key="editor.line_numbers",
                    name="Show Line Numbers",
                    description="Display line numbers in editor",
                    type=PreferenceType.BOOLEAN,
                    default_value=True,
                    scope=PreferenceScope.USER,
                    category="editor",
                    ui_component="checkbox"
                ),
                
                # Behavior preferences
                PreferenceDefinition(
                    key="auto_save",
                    name="Auto Save",
                    description="Automatically save changes",
                    type=PreferenceType.BOOLEAN,
                    default_value=True,
                    scope=PreferenceScope.USER,
                    category="behavior",
                    ui_component="checkbox"
                ),
                PreferenceDefinition(
                    key="auto_save_interval",
                    name="Auto Save Interval",
                    description="Auto save interval in seconds",
                    type=PreferenceType.NUMBER,
                    default_value=30,
                    scope=PreferenceScope.USER,
                    category="behavior",
                    min_value=5,
                    max_value=300
                ),
                
                # Advanced preferences
                PreferenceDefinition(
                    key="debug_mode",
                    name="Debug Mode",
                    description="Enable debug mode",
                    type=PreferenceType.BOOLEAN,
                    default_value=False,
                    scope=PreferenceScope.USER,
                    category="advanced",
                    ui_component="checkbox",
                    requires_restart=True
                ),
                PreferenceDefinition(
                    key="telemetry_enabled",
                    name="Enable Telemetry",
                    description="Allow sending anonymous usage data",
                    type=PreferenceType.BOOLEAN,
                    default_value=True,
                    scope=PreferenceScope.USER,
                    category="advanced",
                    ui_component="checkbox"
                )
            ]
        )
        
        self.schemas["1.0.0"] = default_schema
    
    def _load_preferences(self):
        """Load preferences from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT key, scope, scope_id, value, set_by, set_at, 
                   sync_status, last_synced, conflict_data, 
                   previous_value, change_reason
            FROM preferences
        ''')
        
        for row in cursor.fetchall():
            key, scope, scope_id, value_json, set_by, set_at, sync_status, last_synced, conflict_data, previous_value, change_reason = row
            
            pref_key = f"{key}:{scope}:{scope_id}"
            
            preference = PreferenceValue(
                key=key,
                value=json.loads(value_json),
                scope=PreferenceScope(scope),
                scope_id=scope_id,
                set_by=set_by,
                set_at=datetime.fromisoformat(set_at),
                sync_status=SyncStatus(sync_status),
                last_synced=datetime.fromisoformat(last_synced) if last_synced else None,
                conflict_data=json.loads(conflict_data) if conflict_data else None,
                previous_value=json.loads(previous_value) if previous_value else None,
                change_reason=change_reason or ""
            )
            
            self.preferences[pref_key] = preference
        
        conn.close()
    
    def get_preference(self, key: str, scope: PreferenceScope, scope_id: str,
                      default: Any = None) -> Any:
        """Get preference value"""
        pref_key = f"{key}:{scope.value}:{scope_id}"
        
        if pref_key in self.preferences:
            return self.preferences[pref_key].value
        
        # Check for default value in schema
        schema = self.schemas.get("1.0.0")  # Use latest schema
        if schema:
            pref_def = next((p for p in schema.preferences if p.key == key), None)
            if pref_def:
                return pref_def.default_value
        
        return default
    
    def set_preference(self, key: str, value: Any, scope: PreferenceScope,
                      scope_id: str, set_by: str, change_reason: str = "") -> bool:
        """Set preference value"""
        
        # Validate preference
        validation_result = self._validate_preference(key, value)
        if not validation_result["valid"]:
            raise ValueError(f"Invalid preference value: {validation_result['error']}")
        
        pref_key = f"{key}:{scope.value}:{scope_id}"
        
        # Get previous value
        previous_value = None
        if pref_key in self.preferences:
            previous_value = self.preferences[pref_key].value
        
        # Create preference value
        preference = PreferenceValue(
            key=key,
            value=value,
            scope=scope,
            scope_id=scope_id,
            set_by=set_by,
            set_at=datetime.now(),
            sync_status=SyncStatus.PENDING,
            previous_value=previous_value,
            change_reason=change_reason
        )
        
        self.preferences[pref_key] = preference
        
        # Save to database
        self._save_preference(preference)
        
        # Notify listeners
        self._notify_change_listeners(key, value, previous_value, scope, scope_id)
        
        return True
    
    def _validate_preference(self, key: str, value: Any) -> Dict[str, Any]:
        """Validate preference value against schema"""
        schema = self.schemas.get("1.0.0")
        if not schema:
            return {"valid": True}  # No schema to validate against
        
        pref_def = next((p for p in schema.preferences if p.key == key), None)
        if not pref_def:
            return {"valid": False, "error": "Unknown preference key"}
        
        # Type validation
        if pref_def.type == PreferenceType.STRING and not isinstance(value, str):
            return {"valid": False, "error": "Value must be a string"}
        elif pref_def.type == PreferenceType.NUMBER and not isinstance(value, (int, float)):
            return {"valid": False, "error": "Value must be a number"}
        elif pref_def.type == PreferenceType.BOOLEAN and not isinstance(value, bool):
            return {"valid": False, "error": "Value must be a boolean"}
        elif pref_def.type == PreferenceType.ARRAY and not isinstance(value, list):
            return {"valid": False, "error": "Value must be an array"}
        elif pref_def.type == PreferenceType.OBJECT and not isinstance(value, dict):
            return {"valid": False, "error": "Value must be an object"}
        
        # Range validation
        if pref_def.type == PreferenceType.NUMBER:
            if pref_def.min_value is not None and value < pref_def.min_value:
                return {"valid": False, "error": f"Value must be >= {pref_def.min_value}"}
            if pref_def.max_value is not None and value > pref_def.max_value:
                return {"valid": False, "error": f"Value must be <= {pref_def.max_value}"}
        
        # Allowed values validation
        if pref_def.allowed_values and value not in pref_def.allowed_values:
            return {"valid": False, "error": f"Value must be one of: {pref_def.allowed_values}"}
        
        return {"valid": True}
    
    def _save_preference(self, preference: PreferenceValue):
        """Save preference to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO preferences 
            (key, scope, scope_id, value, set_by, set_at, sync_status, 
             last_synced, conflict_data, previous_value, change_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            preference.key,
            preference.scope.value,
            preference.scope_id,
            json.dumps(preference.value),
            preference.set_by,
            preference.set_at.isoformat(),
            preference.sync_status.value,
            preference.last_synced.isoformat() if preference.last_synced else None,
            json.dumps(preference.conflict_data) if preference.conflict_data else None,
            json.dumps(preference.previous_value) if preference.previous_value is not None else None,
            preference.change_reason
        ))
        
        conn.commit()
        conn.close()
    
    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get all preferences for a user"""
        user_prefs = {}
        
        for pref_key, preference in self.preferences.items():
            if preference.scope == PreferenceScope.USER and preference.scope_id == user_id:
                user_prefs[preference.key] = preference.value
        
        return user_prefs
    
    def create_user_profile(self, user_id: str, name: str, description: str = "") -> str:
        """Create user preference profile"""
        profile_id = str(uuid.uuid4())
        
        profile = UserProfile(
            id=profile_id,
            user_id=user_id,
            name=name,
            description=description,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.user_profiles[profile_id] = profile
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO user_profiles 
            (id, user_id, name, description, profile_data, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            profile_id,
            user_id,
            name,
            description,
            json.dumps(profile.dict()),
            profile.created_at.isoformat(),
            profile.updated_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return profile_id
    
    def export_preferences(self, scope: PreferenceScope, scope_id: str) -> Dict[str, Any]:
        """Export preferences for backup or migration"""
        exported_prefs = {}
        
        for pref_key, preference in self.preferences.items():
            if preference.scope == scope and preference.scope_id == scope_id:
                # Don't export sensitive preferences
                schema = self.schemas.get("1.0.0")
                if schema:
                    pref_def = next((p for p in schema.preferences if p.key == preference.key), None)
                    if pref_def and pref_def.is_sensitive:
                        continue
                
                exported_prefs[preference.key] = {
                    "value": preference.value,
                    "set_at": preference.set_at.isoformat(),
                    "change_reason": preference.change_reason
                }
        
        return {
            "preferences": exported_prefs,
            "scope": scope.value,
            "scope_id": scope_id,
            "exported_at": datetime.now().isoformat(),
            "schema_version": "1.0.0"
        }
    
    def import_preferences(self, import_data: Dict[str, Any], imported_by: str,
                          merge_strategy: str = "overwrite") -> bool:
        """Import preferences from exported data"""
        preferences_data = import_data.get("preferences", {})
        scope = PreferenceScope(import_data.get("scope", "user"))
        scope_id = import_data.get("scope_id", "")
        
        for key, pref_data in preferences_data.items():
            value = pref_data.get("value")
            change_reason = f"Imported ({pref_data.get('change_reason', 'no reason')})"
            
            # Handle merge strategies
            if merge_strategy == "skip_existing":
                pref_key = f"{key}:{scope.value}:{scope_id}"
                if pref_key in self.preferences:
                    continue
            elif merge_strategy == "keep_newer":
                pref_key = f"{key}:{scope.value}:{scope_id}"
                if pref_key in self.preferences:
                    existing_date = self.preferences[pref_key].set_at
                    import_date = datetime.fromisoformat(pref_data.get("set_at"))
                    if existing_date > import_date:
                        continue
            
            self.set_preference(key, value, scope, scope_id, imported_by, change_reason)
        
        return True
    
    def reset_preferences(self, scope: PreferenceScope, scope_id: str,
                         category: str = None) -> int:
        """Reset preferences to default values"""
        reset_count = 0
        schema = self.schemas.get("1.0.0")
        
        if not schema:
            return reset_count
        
        for pref_def in schema.preferences:
            # Filter by category if specified
            if category and pref_def.category != category:
                continue
            
            # Filter by scope
            if pref_def.scope != scope:
                continue
            
            # Reset to default value
            self.set_preference(
                pref_def.key,
                pref_def.default_value,
                scope,
                scope_id,
                "system",
                "Reset to default"
            )
            reset_count += 1
        
        return reset_count
    
    def add_change_listener(self, listener: callable):
        """Add preference change listener"""
        self.change_listeners.append(listener)
    
    def remove_change_listener(self, listener: callable):
        """Remove preference change listener"""
        if listener in self.change_listeners:
            self.change_listeners.remove(listener)
    
    def _notify_change_listeners(self, key: str, new_value: Any, old_value: Any,
                                scope: PreferenceScope, scope_id: str):
        """Notify all change listeners"""
        for listener in self.change_listeners:
            try:
                listener(key, new_value, old_value, scope, scope_id)
            except Exception as e:
                print(f"Error in preference change listener: {e}")
    
    async def sync_preferences(self, user_id: str) -> Dict[str, Any]:
        """Sync user preferences with remote server"""
        # This is a placeholder for actual sync implementation
        sync_result = {
            "synced_count": 0,
            "conflict_count": 0,
            "error_count": 0,
            "conflicts": []
        }
        
        # Mark synced preferences
        for pref_key, preference in self.preferences.items():
            if (preference.scope == PreferenceScope.USER and 
                preference.scope_id == user_id and
                preference.sync_status == SyncStatus.PENDING):
                
                preference.sync_status = SyncStatus.SYNCED
                preference.last_synced = datetime.now()
                self._save_preference(preference)
                sync_result["synced_count"] += 1
        
        return sync_result
    
    def get_preference_schema(self, version: str = "1.0.0") -> Optional[PreferenceSchema]:
        """Get preference schema"""
        return self.schemas.get(version)
    
    def get_categories(self) -> Dict[str, Dict[str, str]]:
        """Get preference categories"""
        schema = self.schemas.get("1.0.0")
        return schema.categories if schema else {}
    
    def get_preferences_by_category(self, category: str, scope: PreferenceScope,
                                   scope_id: str) -> Dict[str, Any]:
        """Get preferences in a specific category"""
        schema = self.schemas.get("1.0.0")
        if not schema:
            return {}
        
        category_prefs = {}
        
        for pref_def in schema.preferences:
            if pref_def.category == category and pref_def.scope == scope:
                value = self.get_preference(pref_def.key, scope, scope_id, pref_def.default_value)
                category_prefs[pref_def.key] = {
                    "definition": pref_def.dict(),
                    "value": value
                }
        
        return category_prefs