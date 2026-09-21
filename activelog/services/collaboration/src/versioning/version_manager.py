"""
Document version control and management system
"""

import asyncio
import hashlib
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from uuid import uuid4

from core.database import db_manager, documents, document_versions, activity_feed
from core.database import ActivityType
from core.config import settings
from .diff_engine import DiffEngine

logger = logging.getLogger(__name__)

class VersionManager:
    def __init__(self):
        self.storage_path = Path(settings.STORAGE_PATH)
        self.versions_path = self.storage_path / "versions"
        self.diff_engine = DiffEngine()
        self.version_cache = {}  # Cache for recent versions
        
    async def initialize(self):
        """Initialize version manager"""
        logger.info("Initializing version manager")
        
        # Create storage directories
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.versions_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize diff engine
        await self.diff_engine.initialize()
        
        # Load recent versions
        await self._load_recent_versions()
        
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up version manager")
        self.version_cache.clear()
        await self.diff_engine.cleanup()
        
    async def _load_recent_versions(self):
        """Load recent document versions into cache"""
        try:
            # Load versions from last 24 hours
            query = f"""
                SELECT dv.*, d.name as document_name
                FROM {document_versions.name} dv
                JOIN {documents.name} d ON dv.document_id = d.id
                WHERE dv.created_at > NOW() - INTERVAL '24 hours'
                ORDER BY dv.created_at DESC
                LIMIT 1000
            """
            
            results = await db_manager.database.fetch_all(query)
            
            for version in results:
                version_dict = dict(version)
                document_id = str(version_dict["document_id"])
                
                if document_id not in self.version_cache:
                    self.version_cache[document_id] = []
                    
                self.version_cache[document_id].append(version_dict)
                
            logger.info(f"Loaded {len(results)} recent versions")
            
        except Exception as e:
            logger.error(f"Failed to load recent versions: {e}")
            
    async def create_version(self, document_id: str, file_path: str, 
                           created_by: str, change_summary: str = "", 
                           is_auto_version: bool = False, 
                           metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a new document version"""
        try:
            # Validate document exists
            doc_query = documents.select().where(documents.c.id == document_id)
            doc_result = await db_manager.database.fetch_one(doc_query)
            
            if not doc_result:
                raise ValueError(f"Document {document_id} not found")
            
            document = dict(doc_result)
            
            # Get next version number
            current_versions = await self.get_document_versions(document_id)
            next_version = len(current_versions) + 1
            
            # Calculate file checksum
            file_checksum = self._calculate_checksum(file_path)
            file_size = os.path.getsize(file_path)
            
            # Check if content changed from last version
            if current_versions:
                latest_version = current_versions[0]  # Assumes sorted by version desc
                if latest_version["checksum"] == file_checksum:
                    logger.info(f"No changes detected for document {document_id}, skipping version creation")
                    return latest_version
            
            # Generate version ID and storage path
            version_id = str(uuid4())
            version_storage_path = self.versions_path / document_id / str(next_version)
            version_storage_path.mkdir(parents=True, exist_ok=True)
            
            # Copy file to version storage
            original_filename = Path(file_path).name
            version_file_path = version_storage_path / original_filename
            shutil.copy2(file_path, version_file_path)
            
            # Create version record
            version_data = {
                "id": version_id,
                "document_id": document_id,
                "version_number": next_version,
                "file_path": str(version_file_path),
                "file_size": file_size,
                "checksum": file_checksum,
                "created_by": created_by,
                "change_summary": change_summary,
                "metadata": metadata or {},
                "is_auto_version": is_auto_version,
                "created_at": datetime.now(timezone.utc)
            }
            
            # Insert into database
            query = document_versions.insert().values(**version_data)
            await db_manager.database.execute(query)
            
            # Update document's current version
            doc_update_query = (documents.update()
                               .where(documents.c.id == document_id)
                               .values(current_version_id=version_id,
                                      updated_at=datetime.now(timezone.utc)))
            await db_manager.database.execute(doc_update_query)
            
            # Update cache
            if document_id not in self.version_cache:
                self.version_cache[document_id] = []
            self.version_cache[document_id].insert(0, version_data)
            
            # Generate diff if not the first version
            if current_versions:
                previous_version = current_versions[0]
                try:
                    diff_result = await self.diff_engine.generate_diff(
                        previous_version["file_path"], 
                        str(version_file_path),
                        document["file_type"]
                    )
                    version_data["diff_summary"] = diff_result.get("summary")
                    version_data["changes_count"] = diff_result.get("changes_count", 0)
                except Exception as e:
                    logger.warning(f"Failed to generate diff for version {version_id}: {e}")
            
            # Cleanup old versions if over limit
            await self._cleanup_old_versions(document_id)
            
            # Log activity
            await self._log_version_activity(
                document_id=document_id,
                version_id=version_id,
                user_id=created_by,
                activity_type=ActivityType.VERSION_CREATED,
                details={
                    "version_number": next_version,
                    "file_size": file_size,
                    "is_auto_version": is_auto_version
                }
            )
            
            logger.info(f"Created version {next_version} for document {document_id}")
            return version_data
            
        except Exception as e:
            logger.error(f"Failed to create version: {e}")
            raise
            
    async def get_document_versions(self, document_id: str, 
                                  limit: int = None, 
                                  offset: int = 0) -> List[Dict[str, Any]]:
        """Get all versions for a document"""
        try:
            # Build query
            query = (document_versions.select()
                    .where(document_versions.c.document_id == document_id)
                    .order_by(document_versions.c.version_number.desc())
                    .offset(offset))
            
            if limit:
                query = query.limit(limit)
                
            results = await db_manager.database.fetch_all(query)
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get versions for document {document_id}: {e}")
            return []
            
    async def get_version(self, version_id: str) -> Optional[Dict[str, Any]]:
        """Get specific version by ID"""
        try:
            # Check cache first
            for document_id, doc_versions in self.version_cache.items():
                for version in doc_versions:
                    if version["id"] == version_id:
                        return version
            
            # Query database
            query = document_versions.select().where(document_versions.c.id == version_id)
            result = await db_manager.database.fetch_one(query)
            
            if result:
                return dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get version {version_id}: {e}")
            return None
            
    async def restore_version(self, document_id: str, version_id: str, 
                            restored_by: str) -> Dict[str, Any]:
        """Restore document to a previous version"""
        try:
            # Get the version to restore
            version_to_restore = await self.get_version(version_id)
            if not version_to_restore:
                raise ValueError(f"Version {version_id} not found")
            
            # Verify it belongs to the document
            if str(version_to_restore["document_id"]) != document_id:
                raise ValueError("Version does not belong to the specified document")
            
            # Get current document info
            doc_query = documents.select().where(documents.c.id == document_id)
            doc_result = await db_manager.database.fetch_one(doc_query)
            
            if not doc_result:
                raise ValueError(f"Document {document_id} not found")
            
            document = dict(doc_result)
            
            # Copy version file back to document location
            version_file_path = Path(version_to_restore["file_path"])
            if not version_file_path.exists():
                raise FileNotFoundError(f"Version file not found: {version_file_path}")
            
            # Create new version from current state before restoring
            current_file_path = document["file_path"]
            await self.create_version(
                document_id=document_id,
                file_path=current_file_path,
                created_by=restored_by,
                change_summary=f"Auto-save before restoring to version {version_to_restore['version_number']}",
                is_auto_version=True
            )
            
            # Copy restored version to document location
            shutil.copy2(version_file_path, current_file_path)
            
            # Create new version for the restoration
            restored_version = await self.create_version(
                document_id=document_id,
                file_path=current_file_path,
                created_by=restored_by,
                change_summary=f"Restored from version {version_to_restore['version_number']}",
                metadata={
                    "restored_from_version_id": version_id,
                    "restored_from_version_number": version_to_restore["version_number"]
                }
            )
            
            logger.info(f"Restored document {document_id} to version {version_to_restore['version_number']}")
            return restored_version
            
        except Exception as e:
            logger.error(f"Failed to restore version {version_id}: {e}")
            raise
            
    async def compare_versions(self, version_id_1: str, version_id_2: str) -> Dict[str, Any]:
        """Compare two document versions"""
        try:
            # Get both versions
            version_1 = await self.get_version(version_id_1)
            version_2 = await self.get_version(version_id_2)
            
            if not version_1 or not version_2:
                raise ValueError("One or both versions not found")
            
            # Ensure they belong to the same document
            if version_1["document_id"] != version_2["document_id"]:
                raise ValueError("Versions belong to different documents")
            
            # Get document info for file type
            document_id = str(version_1["document_id"])
            doc_query = documents.select().where(documents.c.id == document_id)
            doc_result = await db_manager.database.fetch_one(doc_query)
            
            if not doc_result:
                raise ValueError("Document not found")
            
            document = dict(doc_result)
            
            # Generate comparison
            comparison = await self.diff_engine.compare_files(
                version_1["file_path"],
                version_2["file_path"],
                document["file_type"]
            )
            
            comparison.update({
                "version_1": version_1,
                "version_2": version_2,
                "document_id": document_id
            })
            
            return comparison
            
        except Exception as e:
            logger.error(f"Failed to compare versions {version_id_1} and {version_id_2}: {e}")
            raise
            
    async def delete_version(self, version_id: str, deleted_by: str) -> bool:
        """Delete a specific version (except current version)"""
        try:
            # Get version info
            version = await self.get_version(version_id)
            if not version:
                raise ValueError(f"Version {version_id} not found")
            
            document_id = str(version["document_id"])
            
            # Check if it's the current version
            doc_query = documents.select().where(documents.c.id == document_id)
            doc_result = await db_manager.database.fetch_one(doc_query)
            
            if not doc_result:
                raise ValueError("Document not found")
            
            document = dict(doc_result)
            if str(document["current_version_id"]) == version_id:
                raise ValueError("Cannot delete current version")
            
            # Delete version file
            version_file_path = Path(version["file_path"])
            if version_file_path.exists():
                version_file_path.unlink()
                
                # Try to remove parent directories if empty
                try:
                    version_file_path.parent.rmdir()
                    version_file_path.parent.parent.rmdir()
                except OSError:
                    pass  # Directory not empty
            
            # Delete from database
            query = document_versions.delete().where(document_versions.c.id == version_id)
            await db_manager.database.execute(query)
            
            # Remove from cache
            if document_id in self.version_cache:
                self.version_cache[document_id] = [
                    v for v in self.version_cache[document_id] 
                    if v["id"] != version_id
                ]
            
            # Log activity
            await self._log_version_activity(
                document_id=document_id,
                version_id=version_id,
                user_id=deleted_by,
                activity_type=ActivityType.VERSION_CREATED,  # Using closest available
                details={
                    "action": "version_deleted",
                    "version_number": version["version_number"]
                }
            )
            
            logger.info(f"Deleted version {version_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete version {version_id}: {e}")
            raise
            
    async def get_version_timeline(self, document_id: str) -> List[Dict[str, Any]]:
        """Get chronological timeline of document versions"""
        try:
            # Get all versions with additional info
            query = f"""
                SELECT dv.*, 
                       LAG(dv.checksum) OVER (ORDER BY dv.version_number) as prev_checksum,
                       LAG(dv.file_size) OVER (ORDER BY dv.version_number) as prev_file_size
                FROM {document_versions.name} dv
                WHERE dv.document_id = :document_id
                ORDER BY dv.version_number ASC
            """
            
            results = await db_manager.database.fetch_all(query, {"document_id": document_id})
            
            timeline = []
            for row in results:
                version_dict = dict(row)
                
                # Calculate changes from previous version
                if version_dict["prev_checksum"]:
                    version_dict["content_changed"] = version_dict["checksum"] != version_dict["prev_checksum"]
                    version_dict["size_delta"] = version_dict["file_size"] - (version_dict["prev_file_size"] or 0)
                else:
                    version_dict["content_changed"] = True  # First version
                    version_dict["size_delta"] = version_dict["file_size"]
                
                # Remove prev_ fields
                version_dict.pop("prev_checksum", None)
                version_dict.pop("prev_file_size", None)
                
                timeline.append(version_dict)
            
            return timeline
            
        except Exception as e:
            logger.error(f"Failed to get version timeline for document {document_id}: {e}")
            return []
            
    async def _cleanup_old_versions(self, document_id: str):
        """Remove old versions beyond the configured limit"""
        try:
            # Get all versions for document
            all_versions = await self.get_document_versions(document_id)
            
            if len(all_versions) > settings.MAX_VERSIONS_PER_DOCUMENT:
                # Keep the most recent versions and current version
                doc_query = documents.select().where(documents.c.id == document_id)
                doc_result = await db_manager.database.fetch_one(doc_query)
                
                if doc_result:
                    current_version_id = str(doc_result["current_version_id"])
                    
                    # Find versions to delete (oldest ones, but preserve current)
                    versions_to_delete = []
                    versions_to_keep = []
                    
                    for version in all_versions:
                        if str(version["id"]) == current_version_id:
                            versions_to_keep.append(version)  # Always keep current
                        elif len(versions_to_keep) < settings.MAX_VERSIONS_PER_DOCUMENT - 1:
                            versions_to_keep.append(version)  # Keep recent versions
                        else:
                            versions_to_delete.append(version)  # Mark for deletion
                    
                    # Delete old versions
                    for version in versions_to_delete:
                        try:
                            # Delete file
                            version_file_path = Path(version["file_path"])
                            if version_file_path.exists():
                                version_file_path.unlink()
                            
                            # Delete from database
                            delete_query = document_versions.delete().where(
                                document_versions.c.id == version["id"]
                            )
                            await db_manager.database.execute(delete_query)
                            
                            logger.info(f"Cleaned up old version {version['version_number']} for document {document_id}")
                            
                        except Exception as e:
                            logger.warning(f"Failed to cleanup version {version['id']}: {e}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old versions for document {document_id}: {e}")
            
    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA-256 checksum of file"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate checksum for {file_path}: {e}")
            raise
            
    async def _log_version_activity(self, document_id: str, version_id: str, 
                                  user_id: str, activity_type: ActivityType, 
                                  details: Dict[str, Any] = None):
        """Log version activity"""
        try:
            # Get workspace from document
            doc_query = documents.select().where(documents.c.id == document_id)
            doc_result = await db_manager.database.fetch_one(doc_query)
            
            if not doc_result:
                return
                
            workspace_id = str(doc_result["workspace_id"])
            
            activity_data = {
                "workspace_id": workspace_id,
                "document_id": document_id,
                "actor_id": user_id,
                "activity_type": activity_type.value,
                "target_id": version_id,
                "target_type": "version",
                "details": details or {},
                "created_at": datetime.now(timezone.utc)
            }
            
            query = activity_feed.insert().values(**activity_data)
            await db_manager.database.execute(query)
            
        except Exception as e:
            logger.warning(f"Failed to log version activity: {e}")
            
    async def get_version_statistics(self, document_id: str) -> Dict[str, Any]:
        """Get version control statistics for a document"""
        try:
            query = f"""
                SELECT 
                    COUNT(*) as total_versions,
                    COUNT(DISTINCT created_by) as unique_contributors,
                    COUNT(CASE WHEN is_auto_version = true THEN 1 END) as auto_versions,
                    COUNT(CASE WHEN is_auto_version = false THEN 1 END) as manual_versions,
                    MIN(created_at) as first_version_date,
                    MAX(created_at) as latest_version_date,
                    AVG(file_size) as avg_file_size,
                    SUM(file_size) as total_storage_used
                FROM {document_versions.name}
                WHERE document_id = :document_id
            """
            
            result = await db_manager.database.fetch_one(query, {"document_id": document_id})
            stats = dict(result) if result else {}
            
            # Add storage path info
            doc_versions_path = self.versions_path / document_id
            if doc_versions_path.exists():
                stats["storage_path"] = str(doc_versions_path)
                stats["storage_exists"] = True
            else:
                stats["storage_exists"] = False
                
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get version statistics: {e}")
            return {}