#!/usr/bin/env python3
"""
ActiveLog Plugin Version Manager - Handle plugin versioning and updates
"""

import asyncio
import json
import logging
import sqlite3
import time
import zipfile
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from packaging import version as pkg_version
import semver
import hashlib
import shutil


@dataclass
class PluginVersion:
    plugin_id: str
    version: str
    package_path: str
    package_hash: str
    package_size: int
    manifest_data: Dict[str, Any]
    changelog: Optional[str] = None
    is_stable: bool = True
    is_deprecated: bool = False
    created_at: float = 0.0
    updated_at: float = 0.0


@dataclass
class PluginInstallation:
    plugin_id: str
    user_id: str
    installed_version: str
    installation_path: str
    config: Dict[str, Any]
    is_active: bool = True
    installed_at: float = 0.0
    last_used: float = 0.0


@dataclass
class UpdateInfo:
    current_version: str
    latest_version: str
    available_versions: List[str]
    update_required: bool
    breaking_changes: bool
    changelog: Optional[str] = None
    security_update: bool = False


class VersionManager:
    """Manage plugin versions, installations, and updates"""
    
    def __init__(self, db_path: str = "versions.db", storage_path: str = "plugin_storage"):
        self.db_path = db_path
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
        self._init_database()
        
        # In-memory caches
        self.version_cache = {}
        self.installation_cache = {}
    
    def _init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create versions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plugin_versions (
                plugin_id TEXT,
                version TEXT,
                package_path TEXT,
                package_hash TEXT,
                package_size INTEGER,
                manifest_data TEXT,
                changelog TEXT,
                is_stable BOOLEAN DEFAULT 1,
                is_deprecated BOOLEAN DEFAULT 0,
                created_at REAL,
                updated_at REAL,
                PRIMARY KEY (plugin_id, version)
            )
        """)
        
        # Create installations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plugin_installations (
                plugin_id TEXT,
                user_id TEXT,
                installed_version TEXT,
                installation_path TEXT,
                config TEXT,
                is_active BOOLEAN DEFAULT 1,
                installed_at REAL,
                last_used REAL,
                PRIMARY KEY (plugin_id, user_id)
            )
        """)
        
        # Create update history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS update_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plugin_id TEXT,
                user_id TEXT,
                from_version TEXT,
                to_version TEXT,
                status TEXT,
                error_message TEXT,
                started_at REAL,
                completed_at REAL
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_versions_plugin ON plugin_versions (plugin_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_installations_user ON plugin_installations (user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_update_history_plugin ON update_history (plugin_id, user_id)")
        
        conn.commit()
        conn.close()
    
    async def register_version(
        self,
        plugin_id: str,
        version: str,
        package_path: str,
        manifest_data: Dict[str, Any],
        changelog: Optional[str] = None,
        is_stable: bool = True
    ) -> PluginVersion:
        """Register a new plugin version"""
        
        # Validate version format
        if not self._is_valid_version(version):
            raise ValueError(f"Invalid version format: {version}")
        
        # Check if version already exists
        existing = await self.get_version(plugin_id, version)
        if existing:
            raise ValueError(f"Version {version} already exists for plugin {plugin_id}")
        
        # Calculate package hash and size
        package_file = Path(package_path)
        if not package_file.exists():
            raise FileNotFoundError(f"Package file not found: {package_path}")
        
        with open(package_file, 'rb') as f:
            package_content = f.read()
            package_hash = hashlib.sha256(package_content).hexdigest()
            package_size = len(package_content)
        
        # Store package in versioned storage
        stored_path = self._store_package(plugin_id, version, package_path)
        
        now = time.time()
        plugin_version = PluginVersion(
            plugin_id=plugin_id,
            version=version,
            package_path=str(stored_path),
            package_hash=package_hash,
            package_size=package_size,
            manifest_data=manifest_data,
            changelog=changelog,
            is_stable=is_stable,
            created_at=now,
            updated_at=now
        )
        
        # Save to database
        await self._save_version(plugin_version)
        
        # Cache the version
        self.version_cache[(plugin_id, version)] = plugin_version
        
        self.logger.info(f"Registered version {version} for plugin {plugin_id}")
        return plugin_version
    
    async def get_version(self, plugin_id: str, version: str) -> Optional[PluginVersion]:
        """Get specific plugin version"""
        
        # Check cache first
        cache_key = (plugin_id, version)
        if cache_key in self.version_cache:
            return self.version_cache[cache_key]
        
        # Load from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM plugin_versions WHERE plugin_id = ? AND version = ?",
            (plugin_id, version)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            plugin_version = self._row_to_version(result)
            self.version_cache[cache_key] = plugin_version
            return plugin_version
        
        return None
    
    async def get_all_versions(self, plugin_id: str) -> List[PluginVersion]:
        """Get all versions for a plugin, sorted by version number"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM plugin_versions WHERE plugin_id = ? ORDER BY created_at DESC",
            (plugin_id,)
        )
        
        results = cursor.fetchall()
        conn.close()
        
        versions = [self._row_to_version(row) for row in results]
        
        # Sort by semantic version
        try:
            versions.sort(key=lambda v: pkg_version.parse(v.version), reverse=True)
        except Exception:
            # Fallback to string sort if version parsing fails
            versions.sort(key=lambda v: v.version, reverse=True)
        
        return versions
    
    async def get_latest_version(self, plugin_id: str, stable_only: bool = True) -> Optional[PluginVersion]:
        """Get the latest version of a plugin"""
        
        versions = await self.get_all_versions(plugin_id)
        
        if stable_only:
            versions = [v for v in versions if v.is_stable and not v.is_deprecated]
        else:
            versions = [v for v in versions if not v.is_deprecated]
        
        return versions[0] if versions else None
    
    async def install_plugin(
        self,
        plugin_id: str,
        user_id: str,
        version: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> PluginInstallation:
        """Install a plugin for a user"""
        
        # Get version to install
        if version:
            plugin_version = await self.get_version(plugin_id, version)
            if not plugin_version:
                raise ValueError(f"Version {version} not found for plugin {plugin_id}")
        else:
            plugin_version = await self.get_latest_version(plugin_id)
            if not plugin_version:
                raise ValueError(f"No stable version found for plugin {plugin_id}")
        
        # Check if already installed
        existing = await self.get_installation(plugin_id, user_id)
        if existing and existing.is_active:
            raise ValueError(f"Plugin {plugin_id} already installed for user {user_id}")
        
        # Create installation directory
        install_path = self.storage_path / "installations" / user_id / plugin_id
        install_path.mkdir(parents=True, exist_ok=True)
        
        # Extract plugin package
        await self._extract_plugin(plugin_version.package_path, install_path)
        
        now = time.time()
        installation = PluginInstallation(
            plugin_id=plugin_id,
            user_id=user_id,
            installed_version=plugin_version.version,
            installation_path=str(install_path),
            config=config or {},
            installed_at=now,
            last_used=now
        )
        
        # Save installation
        await self._save_installation(installation)
        
        # Cache installation
        self.installation_cache[(plugin_id, user_id)] = installation
        
        self.logger.info(f"Installed plugin {plugin_id} v{plugin_version.version} for user {user_id}")
        return installation
    
    async def update_plugin(
        self,
        plugin_id: str,
        user_id: str,
        target_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update a plugin installation"""
        
        installation = await self.get_installation(plugin_id, user_id)
        if not installation:
            raise ValueError(f"Plugin {plugin_id} not installed for user {user_id}")
        
        # Determine target version
        if target_version:
            new_version = await self.get_version(plugin_id, target_version)
            if not new_version:
                raise ValueError(f"Version {target_version} not found")
        else:
            new_version = await self.get_latest_version(plugin_id)
            if not new_version:
                raise ValueError(f"No stable version available for update")
        
        # Check if update is needed
        current_ver = installation.installed_version
        if current_ver == new_version.version:
            return {
                'success': True,
                'message': 'Plugin is already up to date',
                'version': current_ver
            }
        
        # Record update start
        update_id = await self._start_update_record(plugin_id, user_id, current_ver, new_version.version)
        
        try:
            # Backup current installation
            backup_path = await self._backup_installation(installation)
            
            # Check for breaking changes
            breaking_changes = await self._check_breaking_changes(plugin_id, current_ver, new_version.version)
            
            # Update installation
            install_path = Path(installation.installation_path)
            
            # Clear old files (but keep config)
            config_backup = installation.config
            for item in install_path.iterdir():
                if item.name != 'config.json':  # Preserve config
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
            
            # Extract new version
            await self._extract_plugin(new_version.package_path, install_path)
            
            # Update installation record
            installation.installed_version = new_version.version
            installation.config = config_backup  # Restore config
            installation.last_used = time.time()
            
            await self._save_installation(installation)
            
            # Update cache
            self.installation_cache[(plugin_id, user_id)] = installation
            
            # Record successful update
            await self._complete_update_record(update_id, 'success')
            
            result = {
                'success': True,
                'message': f'Updated from {current_ver} to {new_version.version}',
                'from_version': current_ver,
                'to_version': new_version.version,
                'breaking_changes': breaking_changes,
                'backup_path': str(backup_path)
            }
            
            self.logger.info(f"Updated plugin {plugin_id} for user {user_id} from {current_ver} to {new_version.version}")
            return result
            
        except Exception as e:
            # Record failed update
            await self._complete_update_record(update_id, 'failed', str(e))
            
            self.logger.error(f"Failed to update plugin {plugin_id} for user {user_id}: {e}")
            raise
    
    async def uninstall_plugin(self, plugin_id: str, user_id: str) -> bool:
        """Uninstall a plugin"""
        
        installation = await self.get_installation(plugin_id, user_id)
        if not installation:
            raise ValueError(f"Plugin {plugin_id} not installed for user {user_id}")
        
        # Remove installation directory
        install_path = Path(installation.installation_path)
        if install_path.exists():
            shutil.rmtree(install_path)
        
        # Mark as inactive in database
        installation.is_active = False
        await self._save_installation(installation)
        
        # Remove from cache
        cache_key = (plugin_id, user_id)
        if cache_key in self.installation_cache:
            del self.installation_cache[cache_key]
        
        self.logger.info(f"Uninstalled plugin {plugin_id} for user {user_id}")
        return True
    
    async def get_installation(self, plugin_id: str, user_id: str) -> Optional[PluginInstallation]:
        """Get plugin installation for user"""
        
        # Check cache first
        cache_key = (plugin_id, user_id)
        if cache_key in self.installation_cache:
            return self.installation_cache[cache_key]
        
        # Load from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM plugin_installations WHERE plugin_id = ? AND user_id = ? AND is_active = 1",
            (plugin_id, user_id)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            installation = self._row_to_installation(result)
            self.installation_cache[cache_key] = installation
            return installation
        
        return None
    
    async def check_updates(self, plugin_id: str, user_id: str) -> UpdateInfo:
        """Check for available updates"""
        
        installation = await self.get_installation(plugin_id, user_id)
        if not installation:
            raise ValueError(f"Plugin {plugin_id} not installed for user {user_id}")
        
        current_version = installation.installed_version
        latest_version = await self.get_latest_version(plugin_id)
        all_versions = await self.get_all_versions(plugin_id)
        
        # Filter to stable versions newer than current
        available_versions = []
        for v in all_versions:
            if v.is_stable and not v.is_deprecated:
                try:
                    if pkg_version.parse(v.version) > pkg_version.parse(current_version):
                        available_versions.append(v.version)
                except Exception:
                    # Fallback to string comparison
                    if v.version > current_version:
                        available_versions.append(v.version)
        
        update_required = len(available_versions) > 0
        breaking_changes = False
        security_update = False
        
        if latest_version and update_required:
            breaking_changes = await self._check_breaking_changes(
                plugin_id, current_version, latest_version.version
            )
            
            # Check for security updates (simplified - check changelog for security keywords)
            if latest_version.changelog:
                security_keywords = ['security', 'vulnerability', 'cve', 'exploit', 'patch']
                security_update = any(keyword in latest_version.changelog.lower() 
                                    for keyword in security_keywords)
        
        return UpdateInfo(
            current_version=current_version,
            latest_version=latest_version.version if latest_version else current_version,
            available_versions=available_versions,
            update_required=update_required,
            breaking_changes=breaking_changes,
            changelog=latest_version.changelog if latest_version else None,
            security_update=security_update
        )
    
    async def get_user_installations(self, user_id: str) -> List[PluginInstallation]:
        """Get all installations for a user"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM plugin_installations WHERE user_id = ? AND is_active = 1",
            (user_id,)
        )
        
        results = cursor.fetchall()
        conn.close()
        
        installations = [self._row_to_installation(row) for row in results]
        return installations
    
    async def rollback_update(self, plugin_id: str, user_id: str) -> Dict[str, Any]:
        """Rollback to previous version"""
        
        # Get update history
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT from_version, to_version FROM update_history 
            WHERE plugin_id = ? AND user_id = ? AND status = 'success'
            ORDER BY completed_at DESC LIMIT 1
        """, (plugin_id, user_id))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            raise ValueError("No successful updates found to rollback")
        
        from_version, to_version = result
        
        # Rollback to previous version
        return await self.update_plugin(plugin_id, user_id, from_version)
    
    # Helper methods
    
    def _is_valid_version(self, version: str) -> bool:
        """Check if version string is valid"""
        try:
            pkg_version.parse(version)
            return True
        except Exception:
            try:
                semver.VersionInfo.parse(version)
                return True
            except Exception:
                return False
    
    def _store_package(self, plugin_id: str, version: str, source_path: str) -> Path:
        """Store package in versioned storage"""
        
        storage_dir = self.storage_path / "packages" / plugin_id
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        package_name = f"{plugin_id}-{version}.zip"
        dest_path = storage_dir / package_name
        
        shutil.copy2(source_path, dest_path)
        return dest_path
    
    async def _extract_plugin(self, package_path: str, install_path: Path):
        """Extract plugin package to installation directory"""
        
        with zipfile.ZipFile(package_path, 'r') as zip_ref:
            zip_ref.extractall(install_path)
    
    async def _backup_installation(self, installation: PluginInstallation) -> Path:
        """Create backup of current installation"""
        
        backup_dir = self.storage_path / "backups" / installation.user_id / installation.plugin_id
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = int(time.time())
        backup_path = backup_dir / f"backup-{installation.installed_version}-{timestamp}"
        
        install_path = Path(installation.installation_path)
        shutil.copytree(install_path, backup_path)
        
        return backup_path
    
    async def _check_breaking_changes(self, plugin_id: str, from_version: str, to_version: str) -> bool:
        """Check if update contains breaking changes"""
        
        try:
            from_ver = pkg_version.parse(from_version)
            to_ver = pkg_version.parse(to_version)
            
            # Major version change indicates breaking changes
            return from_ver.major != to_ver.major
            
        except Exception:
            # Fallback: assume breaking changes for different versions
            return from_version != to_version
    
    async def _start_update_record(self, plugin_id: str, user_id: str, from_version: str, to_version: str) -> int:
        """Start update history record"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO update_history 
            (plugin_id, user_id, from_version, to_version, status, started_at)
            VALUES (?, ?, ?, ?, 'in_progress', ?)
        """, (plugin_id, user_id, from_version, to_version, time.time()))
        
        update_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return update_id
    
    async def _complete_update_record(self, update_id: int, status: str, error_message: Optional[str] = None):
        """Complete update history record"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE update_history 
            SET status = ?, error_message = ?, completed_at = ?
            WHERE id = ?
        """, (status, error_message, time.time(), update_id))
        
        conn.commit()
        conn.close()
    
    async def _save_version(self, plugin_version: PluginVersion):
        """Save version to database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO plugin_versions 
            (plugin_id, version, package_path, package_hash, package_size, 
             manifest_data, changelog, is_stable, is_deprecated, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            plugin_version.plugin_id,
            plugin_version.version,
            plugin_version.package_path,
            plugin_version.package_hash,
            plugin_version.package_size,
            json.dumps(plugin_version.manifest_data),
            plugin_version.changelog,
            plugin_version.is_stable,
            plugin_version.is_deprecated,
            plugin_version.created_at,
            plugin_version.updated_at
        ))
        
        conn.commit()
        conn.close()
    
    async def _save_installation(self, installation: PluginInstallation):
        """Save installation to database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO plugin_installations
            (plugin_id, user_id, installed_version, installation_path, 
             config, is_active, installed_at, last_used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            installation.plugin_id,
            installation.user_id,
            installation.installed_version,
            installation.installation_path,
            json.dumps(installation.config),
            installation.is_active,
            installation.installed_at,
            installation.last_used
        ))
        
        conn.commit()
        conn.close()
    
    def _row_to_version(self, row) -> PluginVersion:
        """Convert database row to PluginVersion"""
        
        return PluginVersion(
            plugin_id=row[0],
            version=row[1],
            package_path=row[2],
            package_hash=row[3],
            package_size=row[4],
            manifest_data=json.loads(row[5]) if row[5] else {},
            changelog=row[6],
            is_stable=bool(row[7]),
            is_deprecated=bool(row[8]),
            created_at=row[9],
            updated_at=row[10]
        )
    
    def _row_to_installation(self, row) -> PluginInstallation:
        """Convert database row to PluginInstallation"""
        
        return PluginInstallation(
            plugin_id=row[0],
            user_id=row[1],
            installed_version=row[2],
            installation_path=row[3],
            config=json.loads(row[4]) if row[4] else {},
            is_active=bool(row[5]),
            installed_at=row[6],
            last_used=row[7]
        )


# Global version manager instance
version_manager = VersionManager()


async def main():
    """Test the version manager"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: version-manager.py <command> [args...]")
        print("Commands:")
        print("  register <plugin_id> <version> <package_path>")
        print("  install <plugin_id> <user_id> [version]")
        print("  update <plugin_id> <user_id> [target_version]")
        print("  check <plugin_id> <user_id>")
        print("  list <plugin_id>")
        sys.exit(1)
    
    command = sys.argv[1]
    manager = VersionManager("test_versions.db", "test_storage")
    
    if command == 'register' and len(sys.argv) >= 5:
        plugin_id, version, package_path = sys.argv[2], sys.argv[3], sys.argv[4]
        manifest = {"name": plugin_id, "version": version, "main": "index.js"}
        
        plugin_version = await manager.register_version(plugin_id, version, package_path, manifest)
        print(f"Registered: {plugin_version.plugin_id} v{plugin_version.version}")
    
    elif command == 'install' and len(sys.argv) >= 4:
        plugin_id, user_id = sys.argv[2], sys.argv[3]
        target_version = sys.argv[4] if len(sys.argv) > 4 else None
        
        installation = await manager.install_plugin(plugin_id, user_id, target_version)
        print(f"Installed: {installation.plugin_id} v{installation.installed_version}")
    
    elif command == 'update' and len(sys.argv) >= 4:
        plugin_id, user_id = sys.argv[2], sys.argv[3]
        target_version = sys.argv[4] if len(sys.argv) > 4 else None
        
        result = await manager.update_plugin(plugin_id, user_id, target_version)
        print(f"Update result: {result}")
    
    elif command == 'check' and len(sys.argv) >= 4:
        plugin_id, user_id = sys.argv[2], sys.argv[3]
        
        update_info = await manager.check_updates(plugin_id, user_id)
        print(f"Current: {update_info.current_version}")
        print(f"Latest: {update_info.latest_version}")
        print(f"Updates available: {update_info.available_versions}")
        print(f"Update required: {update_info.update_required}")
    
    elif command == 'list' and len(sys.argv) >= 3:
        plugin_id = sys.argv[2]
        
        versions = await manager.get_all_versions(plugin_id)
        for v in versions:
            status = "stable" if v.is_stable else "unstable"
            if v.is_deprecated:
                status += " (deprecated)"
            print(f"  {v.version} - {status}")


if __name__ == '__main__':
    asyncio.run(main())