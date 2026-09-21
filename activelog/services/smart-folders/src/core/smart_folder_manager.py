"""
Central smart folder management and orchestration
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from concurrent.futures import ThreadPoolExecutor
import time

from .database import db_manager, FolderType
from .rule_engine import RuleEngine
from .inheritance_manager import InheritanceManager
from ..ai.folder_suggester import FolderSuggester
from ..virtual.virtual_folder_manager import VirtualFolderManager
from ..templates.template_manager import TemplateManager
from ..permissions.permission_manager import PermissionManager
from ..utils.cache_manager import CacheManager
from .config import settings

logger = logging.getLogger(__name__)

class SmartFolderManager:
    """Central manager for all smart folder operations"""
    
    def __init__(self):
        self.active_folders: Dict[str, Dict[str, Any]] = {}
        self.rule_engine = RuleEngine()
        self.inheritance_manager = InheritanceManager()
        self.folder_suggester = FolderSuggester()
        self.virtual_manager = VirtualFolderManager()
        self.template_manager = TemplateManager()
        self.permission_manager = PermissionManager()
        self.cache_manager = CacheManager()
        
        self.thread_pool = ThreadPoolExecutor(max_workers=settings.workers)
        self.background_tasks_running = False
        
    async def initialize(self):
        """Initialize smart folder manager and components"""
        
        # Initialize all components
        await self.rule_engine.initialize()
        await self.inheritance_manager.initialize()
        await self.folder_suggester.initialize()
        await self.virtual_manager.initialize()
        await self.template_manager.initialize()
        await self.permission_manager.initialize()
        await self.cache_manager.initialize()
        
        # Load active folders from database
        await self._load_active_folders()
        
        logger.info("Smart folder manager initialized successfully")
    
    async def _load_active_folders(self):
        """Load active smart folders from database"""
        
        try:
            # Get all active folders
            query = "SELECT id, user_id, folder_type, last_evaluated FROM smart_folders WHERE is_active = true"
            rows = await db_manager.database.fetch_all(query)
            
            for row in rows:
                folder_info = dict(row)
                self.active_folders[folder_info["id"]] = {
                    "user_id": folder_info["user_id"],
                    "folder_type": folder_info["folder_type"],
                    "last_evaluated": folder_info["last_evaluated"],
                    "needs_refresh": True
                }
            
            logger.info(f"Loaded {len(self.active_folders)} active smart folders")
            
        except Exception as e:
            logger.error(f"Failed to load active folders: {e}")
    
    async def create_smart_folder(self, user_id: str, folder_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new smart folder"""
        
        try:
            # Extract configuration
            name = folder_config["name"]
            folder_type = FolderType(folder_config.get("type", "smart"))
            
            # Validate folder creation permissions
            if not await self.permission_manager.can_create_folder(user_id):
                raise PermissionError("User does not have permission to create folders")
            
            # Create folder in database
            folder_id = await db_manager.create_smart_folder(
                user_id=user_id,
                name=name,
                folder_type=folder_type,
                parent_id=folder_config.get("parent_id"),
                description=folder_config.get("description", ""),
                rules=folder_config.get("rules", []),
                ai_generated=folder_config.get("ai_generated", False),
                template_id=folder_config.get("template_id")
            )
            
            # Add to active folders
            self.active_folders[folder_id] = {
                "user_id": user_id,
                "folder_type": folder_type,
                "last_evaluated": None,
                "needs_refresh": True
            }
            
            # Initialize folder content
            if folder_type in [FolderType.SMART, FolderType.AI]:
                asyncio.create_task(self._evaluate_folder_rules(folder_id))
            elif folder_type == FolderType.VIRTUAL:
                await self.virtual_manager.create_virtual_folder(folder_id, folder_config)
            
            # Log activity
            await self._log_folder_activity(
                folder_id, user_id, "created", f"Created {folder_type} folder: {name}"
            )
            
            return {
                "folder_id": folder_id,
                "name": name,
                "type": folder_type,
                "status": "created"
            }
            
        except Exception as e:
            logger.error(f"Failed to create smart folder: {e}")
            raise
    
    async def update_smart_folder(self, folder_id: str, updates: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Update smart folder configuration"""
        
        try:
            # Check permissions
            if not await self.permission_manager.can_modify_folder(user_id, folder_id):
                raise PermissionError("User does not have permission to modify this folder")
            
            # Update database
            success = await db_manager.update_smart_folder(folder_id, updates)
            
            if success:
                # Update active folders cache
                if folder_id in self.active_folders:
                    self.active_folders[folder_id]["needs_refresh"] = True
                
                # If rules were updated, re-evaluate folder
                if "rules" in updates:
                    asyncio.create_task(self._evaluate_folder_rules(folder_id))
                
                # Log activity
                await self._log_folder_activity(
                    folder_id, user_id, "updated", f"Updated folder configuration"
                )
                
                return {"status": "updated", "folder_id": folder_id}
            else:
                return {"status": "not_found", "folder_id": folder_id}
                
        except Exception as e:
            logger.error(f"Failed to update smart folder {folder_id}: {e}")
            raise
    
    async def delete_smart_folder(self, folder_id: str, user_id: str) -> Dict[str, Any]:
        """Delete smart folder"""
        
        try:
            # Check permissions
            if not await self.permission_manager.can_delete_folder(user_id, folder_id):
                raise PermissionError("User does not have permission to delete this folder")
            
            # Get folder info before deletion
            folder = await db_manager.get_smart_folder(folder_id)
            if not folder:
                return {"status": "not_found", "folder_id": folder_id}
            
            # Remove from cache and active folders
            await self.cache_manager.delete_folder_cache(folder_id)
            if folder_id in self.active_folders:
                del self.active_folders[folder_id]
            
            # Delete from database
            success = await db_manager.delete_smart_folder(folder_id)
            
            if success:
                # Log activity
                await self._log_folder_activity(
                    folder_id, user_id, "deleted", f"Deleted folder: {folder['name']}"
                )
                
                return {"status": "deleted", "folder_id": folder_id}
            else:
                return {"status": "error", "folder_id": folder_id}
                
        except Exception as e:
            logger.error(f"Failed to delete smart folder {folder_id}: {e}")
            raise
    
    async def get_folder_content(self, folder_id: str, user_id: str, 
                               limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Get smart folder content"""
        
        try:
            # Check permissions
            if not await self.permission_manager.can_read_folder(user_id, folder_id):
                raise PermissionError("User does not have permission to read this folder")
            
            # Try to get from cache first
            cache_key = f"folder_content:{folder_id}:{limit}:{offset}"
            cached_content = await self.cache_manager.get(cache_key)
            
            if cached_content:
                return cached_content
            
            # Get folder info
            folder = await db_manager.get_smart_folder(folder_id)
            if not folder:
                raise ValueError("Folder not found")
            
            # Get items based on folder type
            if folder["folder_type"] == FolderType.VIRTUAL:
                items = await self.virtual_manager.get_virtual_folder_content(folder_id, limit, offset)
            else:
                items = await db_manager.get_folder_items(folder_id, limit, offset)
            
            # Prepare response
            content = {
                "folder_id": folder_id,
                "folder_name": folder["name"],
                "folder_type": folder["folder_type"],
                "total_items": folder["item_count"],
                "items": items,
                "last_updated": folder["last_updated"].isoformat() if folder["last_updated"] else None
            }
            
            # Cache the content
            await self.cache_manager.set(
                cache_key, content, ttl=settings.cache.folder_content_ttl
            )
            
            return content
            
        except Exception as e:
            logger.error(f"Failed to get folder content for {folder_id}: {e}")
            raise
    
    async def refresh_folder(self, folder_id: str) -> Dict[str, Any]:
        """Manually refresh a smart folder's content"""
        
        try:
            folder = await db_manager.get_smart_folder(folder_id)
            if not folder:
                return {"status": "not_found", "folder_id": folder_id}
            
            # Clear cache
            await self.cache_manager.delete_folder_cache(folder_id)
            
            # Mark for refresh
            if folder_id in self.active_folders:
                self.active_folders[folder_id]["needs_refresh"] = True
            
            # Evaluate rules
            if folder["folder_type"] in [FolderType.SMART, FolderType.AI]:
                result = await self._evaluate_folder_rules(folder_id)
                return {
                    "status": "refreshed",
                    "folder_id": folder_id,
                    "items_processed": result.get("items_processed", 0)
                }
            elif folder["folder_type"] == FolderType.VIRTUAL:
                await self.virtual_manager.refresh_virtual_folder(folder_id)
                return {"status": "refreshed", "folder_id": folder_id}
            
            return {"status": "no_action_needed", "folder_id": folder_id}
            
        except Exception as e:
            logger.error(f"Failed to refresh folder {folder_id}: {e}")
            raise
    
    async def _evaluate_folder_rules(self, folder_id: str) -> Dict[str, Any]:
        """Evaluate folder rules and update content"""
        
        start_time = time.time()
        
        try:
            # Get folder configuration
            folder = await db_manager.get_smart_folder(folder_id)
            if not folder or not folder["rules"]:
                return {"status": "no_rules", "items_processed": 0}
            
            # Clear existing items
            await db_manager.database.execute(
                "DELETE FROM smart_folder_items WHERE folder_id = :folder_id",
                values={"folder_id": folder_id}
            )
            
            # Evaluate rules against file system
            matching_items = await self.rule_engine.evaluate_rules(
                folder["rules"], 
                folder.get("rule_logic", "AND"),
                user_id=folder["user_id"]
            )
            
            # Add matching items to folder
            if matching_items:
                await db_manager.add_folder_items(folder_id, matching_items)
            
            # Update folder metadata
            await db_manager.update_smart_folder(folder_id, {
                "last_evaluated": datetime.utcnow(),
                "item_count": len(matching_items)
            })
            
            # Update active folders
            if folder_id in self.active_folders:
                self.active_folders[folder_id]["last_evaluated"] = datetime.utcnow()
                self.active_folders[folder_id]["needs_refresh"] = False
            
            evaluation_time = time.time() - start_time
            
            logger.info(f"Evaluated folder {folder_id}: {len(matching_items)} items in {evaluation_time:.2f}s")
            
            return {
                "status": "completed",
                "items_processed": len(matching_items),
                "evaluation_time": evaluation_time
            }
            
        except Exception as e:
            logger.error(f"Failed to evaluate folder rules for {folder_id}: {e}")
            return {"status": "error", "error": str(e)}
    
    async def get_folder_suggestions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get AI-generated folder structure suggestions for user"""
        
        try:
            # Check cache first
            cache_key = f"folder_suggestions:{user_id}"
            cached_suggestions = await self.cache_manager.get(cache_key)
            
            if cached_suggestions:
                return cached_suggestions
            
            # Generate new suggestions
            suggestions = await self.folder_suggester.generate_suggestions(user_id)
            
            # Cache suggestions
            await self.cache_manager.set(
                cache_key, suggestions, ttl=settings.cache.ai_suggestions_ttl
            )
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Failed to get folder suggestions for user {user_id}: {e}")
            return []
    
    async def apply_template(self, user_id: str, template_id: str, 
                           parent_folder_id: Optional[str] = None) -> Dict[str, Any]:
        """Apply a folder template to create folder structure"""
        
        try:
            # Check permissions
            if not await self.permission_manager.can_create_folder(user_id):
                raise PermissionError("User does not have permission to create folders")
            
            # Apply template
            result = await self.template_manager.apply_template(
                user_id, template_id, parent_folder_id
            )
            
            # Add created folders to active folders
            for folder_id in result.get("created_folders", []):
                self.active_folders[folder_id] = {
                    "user_id": user_id,
                    "folder_type": FolderType.TEMPLATE,
                    "last_evaluated": None,
                    "needs_refresh": True
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to apply template {template_id} for user {user_id}: {e}")
            raise
    
    async def share_folder(self, folder_id: str, user_id: str, 
                          share_config: Dict[str, Any]) -> Dict[str, Any]:
        """Share folder with specified permissions"""
        
        try:
            # Check permissions
            if not await self.permission_manager.can_share_folder(user_id, folder_id):
                raise PermissionError("User does not have permission to share this folder")
            
            # Apply sharing configuration
            result = await self.permission_manager.share_folder(
                folder_id, user_id, share_config
            )
            
            # Log activity
            await self._log_folder_activity(
                folder_id, user_id, "shared", 
                f"Shared folder with {len(share_config.get('users', []))} users"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to share folder {folder_id}: {e}")
            raise
    
    async def start_background_tasks(self):
        """Start background processing tasks"""
        
        if self.background_tasks_running:
            return
        
        self.background_tasks_running = True
        
        # Start periodic folder evaluation
        asyncio.create_task(self._periodic_folder_evaluation())
        
        # Start cache cleanup
        asyncio.create_task(self._periodic_cache_cleanup())
        
        # Start metrics collection
        asyncio.create_task(self._periodic_metrics_collection())
        
        logger.info("Started background tasks")
    
    async def _periodic_folder_evaluation(self):
        """Periodically evaluate folder rules for active folders"""
        
        while self.background_tasks_running:
            try:
                current_time = datetime.utcnow()
                
                for folder_id, folder_info in list(self.active_folders.items()):
                    try:
                        # Check if folder needs evaluation
                        last_evaluated = folder_info.get("last_evaluated")
                        needs_refresh = folder_info.get("needs_refresh", False)
                        
                        should_evaluate = (
                            needs_refresh or
                            not last_evaluated or
                            (current_time - last_evaluated).total_seconds() > settings.smart_folders.rule_evaluation_interval
                        )
                        
                        if should_evaluate:
                            # Evaluate folder rules
                            await self._evaluate_folder_rules(folder_id)
                    
                    except Exception as e:
                        logger.error(f"Error evaluating folder {folder_id}: {e}")
                
                # Wait before next evaluation cycle
                await asyncio.sleep(settings.smart_folders.rule_evaluation_interval)
                
            except Exception as e:
                logger.error(f"Error in periodic folder evaluation: {e}")
                await asyncio.sleep(60)  # Wait a minute before retrying
    
    async def _periodic_cache_cleanup(self):
        """Periodically clean up expired cache entries"""
        
        while self.background_tasks_running:
            try:
                await self.cache_manager.cleanup_expired()
                await asyncio.sleep(1800)  # Run every 30 minutes
                
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _periodic_metrics_collection(self):
        """Periodically collect and store metrics"""
        
        while self.background_tasks_running:
            try:
                # Collect metrics
                metrics = await self.get_metrics()
                
                # Store metrics (implement metric storage as needed)
                logger.debug(f"Collected metrics: {json.dumps(metrics, default=str)}")
                
                await asyncio.sleep(300)  # Collect every 5 minutes
                
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                await asyncio.sleep(300)
    
    async def _log_folder_activity(self, folder_id: str, user_id: str, 
                                 activity_type: str, description: str):
        """Log folder activity"""
        
        try:
            query = """
            INSERT INTO folder_activity (id, folder_id, user_id, activity_type, description)
            VALUES (:id, :folder_id, :user_id, :activity_type, :description)
            """
            
            await db_manager.database.execute(
                query,
                values={
                    "id": str(uuid.uuid4()),
                    "folder_id": folder_id,
                    "user_id": user_id,
                    "activity_type": activity_type,
                    "description": description
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to log folder activity: {e}")
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive service metrics"""
        
        try:
            # Database metrics
            db_metrics = await self._get_database_metrics()
            
            # Active folder metrics
            folder_metrics = {
                "total_active_folders": len(self.active_folders),
                "folders_by_type": {},
                "folders_needing_refresh": 0
            }
            
            for folder_info in self.active_folders.values():
                folder_type = folder_info["folder_type"]
                folder_metrics["folders_by_type"][folder_type] = folder_metrics["folders_by_type"].get(folder_type, 0) + 1
                
                if folder_info.get("needs_refresh", False):
                    folder_metrics["folders_needing_refresh"] += 1
            
            # Component metrics
            cache_metrics = await self.cache_manager.get_metrics()
            ai_metrics = await self.folder_suggester.get_metrics()
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "service": "smart_folders",
                "database": db_metrics,
                "folders": folder_metrics,
                "cache": cache_metrics,
                "ai": ai_metrics,
                "background_tasks_running": self.background_tasks_running
            }
            
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
    
    async def _get_database_metrics(self) -> Dict[str, Any]:
        """Get database-related metrics"""
        
        try:
            queries = {
                "total_folders": "SELECT COUNT(*) FROM smart_folders",
                "active_folders": "SELECT COUNT(*) FROM smart_folders WHERE is_active = true",
                "total_folder_items": "SELECT COUNT(*) FROM smart_folder_items",
                "total_templates": "SELECT COUNT(*) FROM folder_templates",
                "total_permissions": "SELECT COUNT(*) FROM folder_permissions"
            }
            
            metrics = {}
            for metric_name, query in queries.items():
                result = await db_manager.database.fetch_val(query)
                metrics[metric_name] = result or 0
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get database metrics: {e}")
            return {"error": str(e)}
    
    async def cleanup(self):
        """Clean up smart folder manager resources"""
        
        # Stop background tasks
        self.background_tasks_running = False
        
        # Clean up components
        await self.rule_engine.cleanup()
        await self.folder_suggester.cleanup()
        await self.virtual_manager.cleanup()
        await self.template_manager.cleanup()
        await self.permission_manager.cleanup()
        await self.cache_manager.cleanup()
        
        # Shutdown thread pool
        self.thread_pool.shutdown(wait=True)
        
        logger.info("Smart folder manager cleaned up")