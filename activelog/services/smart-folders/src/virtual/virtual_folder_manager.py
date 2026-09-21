"""
Virtual Folder Manager

Manages virtual folders that provide organized views of files without physically moving them:
- File references instead of file moves
- Dynamic content updates
- Multiple virtual views of same files
- Efficient indexing and caching
- Cross-platform compatibility
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
import json
import hashlib

from ..core.config import settings
from ..core.database import db_manager, FolderType
from ..utils.cache_manager import CacheManager

logger = logging.getLogger(__name__)

class VirtualFileReference:
    """Represents a virtual reference to a physical file"""
    
    def __init__(self, virtual_path: str, physical_path: str, metadata: Dict[str, Any] = None):
        self.virtual_path = virtual_path
        self.physical_path = physical_path
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()
        self.accessed_at = datetime.utcnow()
        self.reference_id = self._generate_reference_id()
    
    def _generate_reference_id(self) -> str:
        """Generate unique reference ID"""
        content = f"{self.virtual_path}:{self.physical_path}:{self.created_at.isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def update_access_time(self):
        """Update last accessed time"""
        self.accessed_at = datetime.utcnow()
    
    def is_valid(self) -> bool:
        """Check if physical file still exists"""
        return os.path.exists(self.physical_path)
    
    def get_file_info(self) -> Dict[str, Any]:
        """Get comprehensive file information"""
        try:
            stat = os.stat(self.physical_path)
            
            return {
                "reference_id": self.reference_id,
                "virtual_path": self.virtual_path,
                "physical_path": self.physical_path,
                "name": os.path.basename(self.physical_path),
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "accessed": self.accessed_at.isoformat(),
                "metadata": self.metadata,
                "exists": True
            }
        except (OSError, IOError):
            return {
                "reference_id": self.reference_id,
                "virtual_path": self.virtual_path,
                "physical_path": self.physical_path,
                "name": os.path.basename(self.physical_path),
                "exists": False,
                "error": "File not found"
            }

class VirtualFolder:
    """Represents a virtual folder containing file references"""
    
    def __init__(self, folder_id: str, name: str, user_id: str):
        self.folder_id = folder_id
        self.name = name
        self.user_id = user_id
        self.file_references: Dict[str, VirtualFileReference] = {}
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.access_count = 0
        self.metadata = {}
    
    def add_file_reference(self, physical_path: str, virtual_name: str = None, 
                          metadata: Dict[str, Any] = None) -> str:
        """Add a file reference to this virtual folder"""
        
        if not os.path.exists(physical_path):
            raise FileNotFoundError(f"Physical file not found: {physical_path}")
        
        virtual_name = virtual_name or os.path.basename(physical_path)
        virtual_path = f"/{self.name}/{virtual_name}"
        
        # Handle duplicate names
        counter = 1
        original_virtual_path = virtual_path
        while virtual_path in [ref.virtual_path for ref in self.file_references.values()]:
            name, ext = os.path.splitext(virtual_name)
            virtual_name = f"{name}_{counter}{ext}"
            virtual_path = f"/{self.name}/{virtual_name}"
            counter += 1
        
        reference = VirtualFileReference(virtual_path, physical_path, metadata)
        self.file_references[reference.reference_id] = reference
        
        self.updated_at = datetime.utcnow()
        
        return reference.reference_id
    
    def remove_file_reference(self, reference_id: str) -> bool:
        """Remove a file reference from this virtual folder"""
        
        if reference_id in self.file_references:
            del self.file_references[reference_id]
            self.updated_at = datetime.utcnow()
            return True
        
        return False
    
    def get_file_reference(self, reference_id: str) -> Optional[VirtualFileReference]:
        """Get a specific file reference"""
        return self.file_references.get(reference_id)
    
    def list_files(self, limit: int = None, offset: int = 0, 
                  filter_func: callable = None) -> List[Dict[str, Any]]:
        """List files in virtual folder"""
        
        references = list(self.file_references.values())
        
        # Apply filter if provided
        if filter_func:
            references = [ref for ref in references if filter_func(ref)]
        
        # Sort by name
        references.sort(key=lambda r: os.path.basename(r.physical_path).lower())
        
        # Apply pagination
        if offset > 0:
            references = references[offset:]
        if limit:
            references = references[:limit]
        
        # Update access times and return file info
        result = []
        for ref in references:
            ref.update_access_time()
            result.append(ref.get_file_info())
        
        self.access_count += 1
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """Get virtual folder statistics"""
        
        valid_references = [ref for ref in self.file_references.values() if ref.is_valid()]
        total_size = sum(
            os.path.getsize(ref.physical_path) 
            for ref in valid_references 
            if os.path.exists(ref.physical_path)
        )
        
        return {
            "folder_id": self.folder_id,
            "name": self.name,
            "total_references": len(self.file_references),
            "valid_references": len(valid_references),
            "invalid_references": len(self.file_references) - len(valid_references),
            "total_size": total_size,
            "access_count": self.access_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    def cleanup_invalid_references(self) -> int:
        """Remove references to files that no longer exist"""
        
        invalid_refs = [
            ref_id for ref_id, ref in self.file_references.items()
            if not ref.is_valid()
        ]
        
        for ref_id in invalid_refs:
            del self.file_references[ref_id]
        
        if invalid_refs:
            self.updated_at = datetime.utcnow()
        
        return len(invalid_refs)

class VirtualFolderManager:
    """Manages all virtual folders and their operations"""
    
    def __init__(self):
        self.virtual_folders: Dict[str, VirtualFolder] = {}
        self.cache_manager = CacheManager()
        
        self.stats = {
            "total_virtual_folders": 0,
            "total_file_references": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cleanup_operations": 0
        }
    
    async def initialize(self):
        """Initialize virtual folder manager"""
        
        # Load existing virtual folders from database
        await self._load_virtual_folders()
        
        logger.info(f"Virtual folder manager initialized with {len(self.virtual_folders)} folders")
    
    async def _load_virtual_folders(self):
        """Load virtual folders from database"""
        
        try:
            query = """
            SELECT sf.*, sfi.* FROM smart_folders sf
            LEFT JOIN smart_folder_items sfi ON sf.id = sfi.folder_id
            WHERE sf.folder_type = :folder_type AND sf.is_active = true
            """
            
            rows = await db_manager.database.fetch_all(
                query, 
                values={"folder_type": FolderType.VIRTUAL}
            )
            
            # Group items by folder
            folders_data = {}
            for row in rows:
                folder_id = row["id"]
                
                if folder_id not in folders_data:
                    folders_data[folder_id] = {
                        "folder_info": {
                            "id": row["id"],
                            "name": row["name"],
                            "user_id": row["user_id"],
                            "created_at": row["created_at"],
                            "updated_at": row["updated_at"]
                        },
                        "items": []
                    }
                
                if row.get("file_id"):  # Has items
                    folders_data[folder_id]["items"].append({
                        "reference_id": row["file_id"],
                        "physical_path": row["file_path"],
                        "virtual_name": row["file_name"],
                        "metadata": json.loads(row["matched_rules"]) if row["matched_rules"] else {}
                    })
            
            # Create virtual folder objects
            for folder_data in folders_data.values():
                folder_info = folder_data["folder_info"]
                virtual_folder = VirtualFolder(
                    folder_info["id"],
                    folder_info["name"],
                    folder_info["user_id"]
                )
                
                # Add file references
                for item in folder_data["items"]:
                    try:
                        reference = VirtualFileReference(
                            f"/{folder_info['name']}/{item['virtual_name']}",
                            item["physical_path"],
                            item["metadata"]
                        )
                        virtual_folder.file_references[item["reference_id"]] = reference
                    except Exception as e:
                        logger.warning(f"Error loading virtual file reference: {e}")
                
                self.virtual_folders[folder_info["id"]] = virtual_folder
            
            self.stats["total_virtual_folders"] = len(self.virtual_folders)
            self.stats["total_file_references"] = sum(
                len(folder.file_references) for folder in self.virtual_folders.values()
            )
            
        except Exception as e:
            logger.error(f"Error loading virtual folders: {e}")
    
    async def create_virtual_folder(self, folder_id: str, config: Dict[str, Any]) -> VirtualFolder:
        """Create a new virtual folder"""
        
        try:
            name = config["name"]
            user_id = config["user_id"]
            
            # Create virtual folder object
            virtual_folder = VirtualFolder(folder_id, name, user_id)
            
            # Add initial files if provided
            initial_files = config.get("initial_files", [])
            for file_config in initial_files:
                try:
                    virtual_folder.add_file_reference(
                        file_config["physical_path"],
                        file_config.get("virtual_name"),
                        file_config.get("metadata", {})
                    )
                except Exception as e:
                    logger.warning(f"Error adding initial file to virtual folder: {e}")
            
            # Store in memory
            self.virtual_folders[folder_id] = virtual_folder
            
            # Save file references to database
            await self._save_virtual_folder_items(virtual_folder)
            
            self.stats["total_virtual_folders"] += 1
            self.stats["total_file_references"] += len(virtual_folder.file_references)
            
            logger.info(f"Created virtual folder {name} with {len(virtual_folder.file_references)} files")
            
            return virtual_folder
            
        except Exception as e:
            logger.error(f"Error creating virtual folder: {e}")
            raise
    
    async def get_virtual_folder(self, folder_id: str) -> Optional[VirtualFolder]:
        """Get virtual folder by ID"""
        
        # Check memory first
        if folder_id in self.virtual_folders:
            self.stats["cache_hits"] += 1
            return self.virtual_folders[folder_id]
        
        # Check database
        try:
            folder = await db_manager.get_smart_folder(folder_id)
            if folder and folder["folder_type"] == FolderType.VIRTUAL:
                # Load folder items and create virtual folder
                await self._load_single_virtual_folder(folder_id)
                self.stats["cache_misses"] += 1
                return self.virtual_folders.get(folder_id)
        except Exception as e:
            logger.error(f"Error getting virtual folder {folder_id}: {e}")
        
        return None
    
    async def _load_single_virtual_folder(self, folder_id: str):
        """Load a single virtual folder from database"""
        
        try:
            folder = await db_manager.get_smart_folder(folder_id)
            if not folder:
                return
            
            virtual_folder = VirtualFolder(folder_id, folder["name"], folder["user_id"])
            
            # Load items
            items = await db_manager.get_folder_items(folder_id)
            for item in items:
                try:
                    reference = VirtualFileReference(
                        f"/{folder['name']}/{item['file_name']}",
                        item["file_path"],
                        item.get("matched_rules", {})
                    )
                    virtual_folder.file_references[item["file_id"]] = reference
                except Exception as e:
                    logger.warning(f"Error loading virtual file reference: {e}")
            
            self.virtual_folders[folder_id] = virtual_folder
            
        except Exception as e:
            logger.error(f"Error loading virtual folder {folder_id}: {e}")
    
    async def add_file_to_virtual_folder(self, folder_id: str, physical_path: str,
                                       virtual_name: str = None, 
                                       metadata: Dict[str, Any] = None) -> Optional[str]:
        """Add a file reference to virtual folder"""
        
        try:
            virtual_folder = await self.get_virtual_folder(folder_id)
            if not virtual_folder:
                raise ValueError(f"Virtual folder {folder_id} not found")
            
            reference_id = virtual_folder.add_file_reference(
                physical_path, virtual_name, metadata
            )
            
            # Update database
            await self._save_single_virtual_item(virtual_folder, reference_id)
            
            self.stats["total_file_references"] += 1
            
            return reference_id
            
        except Exception as e:
            logger.error(f"Error adding file to virtual folder: {e}")
            return None
    
    async def remove_file_from_virtual_folder(self, folder_id: str, reference_id: str) -> bool:
        """Remove a file reference from virtual folder"""
        
        try:
            virtual_folder = await self.get_virtual_folder(folder_id)
            if not virtual_folder:
                return False
            
            success = virtual_folder.remove_file_reference(reference_id)
            
            if success:
                # Update database
                await db_manager.database.execute(
                    "DELETE FROM smart_folder_items WHERE folder_id = :folder_id AND file_id = :file_id",
                    values={"folder_id": folder_id, "file_id": reference_id}
                )
                
                self.stats["total_file_references"] -= 1
            
            return success
            
        except Exception as e:
            logger.error(f"Error removing file from virtual folder: {e}")
            return False
    
    async def get_virtual_folder_content(self, folder_id: str, limit: int = 100, 
                                       offset: int = 0) -> List[Dict[str, Any]]:
        """Get virtual folder content"""
        
        try:
            virtual_folder = await self.get_virtual_folder(folder_id)
            if not virtual_folder:
                return []
            
            return virtual_folder.list_files(limit, offset)
            
        except Exception as e:
            logger.error(f"Error getting virtual folder content: {e}")
            return []
    
    async def refresh_virtual_folder(self, folder_id: str) -> Dict[str, Any]:
        """Refresh virtual folder by cleaning up invalid references"""
        
        try:
            virtual_folder = await self.get_virtual_folder(folder_id)
            if not virtual_folder:
                return {"error": "Folder not found"}
            
            # Clean up invalid references
            removed_count = virtual_folder.cleanup_invalid_references()
            
            # Update database if references were removed
            if removed_count > 0:
                await self._save_virtual_folder_items(virtual_folder)
                self.stats["total_file_references"] -= removed_count
            
            self.stats["cleanup_operations"] += 1
            
            return {
                "folder_id": folder_id,
                "removed_invalid_references": removed_count,
                "remaining_references": len(virtual_folder.file_references)
            }
            
        except Exception as e:
            logger.error(f"Error refreshing virtual folder: {e}")
            return {"error": str(e)}
    
    async def _save_virtual_folder_items(self, virtual_folder: VirtualFolder):
        """Save all virtual folder items to database"""
        
        try:
            # Clear existing items
            await db_manager.database.execute(
                "DELETE FROM smart_folder_items WHERE folder_id = :folder_id",
                values={"folder_id": virtual_folder.folder_id}
            )
            
            # Insert current items
            if virtual_folder.file_references:
                items_data = []
                for ref_id, reference in virtual_folder.file_references.items():
                    if reference.is_valid():  # Only save valid references
                        items_data.append({
                            "file_id": ref_id,
                            "file_path": reference.physical_path,
                            "file_name": os.path.basename(reference.physical_path),
                            "metadata": reference.metadata
                        })
                
                await db_manager.add_folder_items(virtual_folder.folder_id, items_data)
            
        except Exception as e:
            logger.error(f"Error saving virtual folder items: {e}")
    
    async def _save_single_virtual_item(self, virtual_folder: VirtualFolder, reference_id: str):
        """Save a single virtual folder item to database"""
        
        try:
            reference = virtual_folder.get_file_reference(reference_id)
            if not reference or not reference.is_valid():
                return
            
            item_data = {
                "file_id": reference_id,
                "file_path": reference.physical_path,
                "file_name": os.path.basename(reference.physical_path),
                "file_size": os.path.getsize(reference.physical_path) if os.path.exists(reference.physical_path) else 0,
                "metadata": reference.metadata
            }
            
            await db_manager.add_folder_items(virtual_folder.folder_id, [item_data])
            
        except Exception as e:
            logger.error(f"Error saving virtual folder item: {e}")
    
    async def search_virtual_folders(self, user_id: str, query: str) -> List[Dict[str, Any]]:
        """Search across virtual folders"""
        
        results = []
        
        try:
            query_lower = query.lower()
            
            for folder in self.virtual_folders.values():
                if folder.user_id != user_id:
                    continue
                
                # Search folder name
                if query_lower in folder.name.lower():
                    results.append({
                        "type": "folder",
                        "folder_id": folder.folder_id,
                        "name": folder.name,
                        "match_type": "folder_name"
                    })
                
                # Search file names
                for ref in folder.file_references.values():
                    file_name = os.path.basename(ref.physical_path).lower()
                    if query_lower in file_name:
                        results.append({
                            "type": "file",
                            "folder_id": folder.folder_id,
                            "folder_name": folder.name,
                            "reference_id": ref.reference_id,
                            "file_name": os.path.basename(ref.physical_path),
                            "physical_path": ref.physical_path,
                            "match_type": "file_name"
                        })
            
        except Exception as e:
            logger.error(f"Error searching virtual folders: {e}")
        
        return results
    
    async def get_folder_stats(self, folder_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a virtual folder"""
        
        try:
            virtual_folder = await self.get_virtual_folder(folder_id)
            if not virtual_folder:
                return None
            
            return virtual_folder.get_stats()
            
        except Exception as e:
            logger.error(f"Error getting folder stats: {e}")
            return None
    
    async def bulk_add_files(self, folder_id: str, file_paths: List[str]) -> Dict[str, Any]:
        """Add multiple files to virtual folder at once"""
        
        try:
            virtual_folder = await self.get_virtual_folder(folder_id)
            if not virtual_folder:
                return {"error": "Folder not found"}
            
            added_count = 0
            failed_count = 0
            errors = []
            
            for file_path in file_paths:
                try:
                    reference_id = virtual_folder.add_file_reference(file_path)
                    if reference_id:
                        added_count += 1
                except Exception as e:
                    failed_count += 1
                    errors.append(f"{file_path}: {str(e)}")
            
            # Update database
            await self._save_virtual_folder_items(virtual_folder)
            
            self.stats["total_file_references"] += added_count
            
            return {
                "folder_id": folder_id,
                "added_count": added_count,
                "failed_count": failed_count,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Error bulk adding files: {e}")
            return {"error": str(e)}
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """Get virtual folder manager statistics"""
        
        stats = self.stats.copy()
        
        # Add current state
        stats["loaded_folders"] = len(self.virtual_folders)
        stats["current_file_references"] = sum(
            len(folder.file_references) for folder in self.virtual_folders.values()
        )
        
        return stats
    
    async def cleanup(self):
        """Clean up virtual folder manager"""
        
        try:
            # Run cleanup on all virtual folders
            cleanup_tasks = [
                self.refresh_virtual_folder(folder_id) 
                for folder_id in self.virtual_folders.keys()
            ]
            
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
            # Clear memory
            self.virtual_folders.clear()
            
            logger.info("Virtual folder manager cleaned up")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")