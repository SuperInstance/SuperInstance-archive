"""
Annotation management for collaborative documents
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4

from core.database import db_manager, annotations, comments, activity_feed
from core.database import AnnotationType, ActivityType

logger = logging.getLogger(__name__)

class AnnotationManager:
    def __init__(self):
        self.active_annotations = {}  # In-memory cache for active annotations
        self.annotation_locks = {}    # Prevent concurrent edits
        
    async def initialize(self):
        """Initialize annotation manager"""
        logger.info("Initializing annotation manager")
        await self._load_active_annotations()
        
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up annotation manager")
        self.active_annotations.clear()
        self.annotation_locks.clear()
        
    async def _load_active_annotations(self):
        """Load active annotations from database"""
        try:
            # Load recent annotations (last 24 hours) into cache
            query = f"""
                SELECT id, document_id, created_by, annotation_type, content, 
                       position_data, style_data, is_private, is_resolved, 
                       created_at, updated_at
                FROM {annotations.name}
                WHERE created_at > NOW() - INTERVAL '24 hours'
                AND is_resolved = false
                ORDER BY created_at DESC
                LIMIT 1000
            """
            
            results = await db_manager.database.fetch_all(query)
            
            for annotation in results:
                ann_dict = dict(annotation)
                document_id = str(ann_dict["document_id"])
                
                if document_id not in self.active_annotations:
                    self.active_annotations[document_id] = {}
                    
                self.active_annotations[document_id][str(ann_dict["id"])] = ann_dict
                
            logger.info(f"Loaded {len(results)} active annotations")
            
        except Exception as e:
            logger.error(f"Failed to load active annotations: {e}")
            
    async def create_annotation(self, annotation_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Create a new annotation"""
        try:
            # Validate annotation data
            required_fields = ["document_id", "annotation_type", "position_data"]
            for field in required_fields:
                if field not in annotation_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate annotation type
            if annotation_data["annotation_type"] not in [t.value for t in AnnotationType]:
                raise ValueError(f"Invalid annotation type: {annotation_data['annotation_type']}")
            
            # Generate annotation ID
            annotation_id = str(uuid4())
            
            # Prepare annotation data
            ann_data = {
                "id": annotation_id,
                "document_id": annotation_data["document_id"],
                "created_by": user_id,
                "annotation_type": annotation_data["annotation_type"],
                "content": annotation_data.get("content", ""),
                "position_data": annotation_data["position_data"],
                "style_data": annotation_data.get("style_data", {}),
                "is_private": annotation_data.get("is_private", False),
                "metadata": annotation_data.get("metadata", {}),
                "thread_id": annotation_data.get("thread_id"),
                "version_id": annotation_data.get("version_id"),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            
            # Insert into database
            query = annotations.insert().values(**ann_data)
            await db_manager.database.execute(query)
            
            # Add to cache
            document_id = str(annotation_data["document_id"])
            if document_id not in self.active_annotations:
                self.active_annotations[document_id] = {}
            self.active_annotations[document_id][annotation_id] = ann_data
            
            # Log activity
            await self._log_annotation_activity(
                document_id=document_id,
                annotation_id=annotation_id,
                user_id=user_id,
                activity_type=ActivityType.ANNOTATION_ADDED,
                details={"annotation_type": annotation_data["annotation_type"]}
            )
            
            logger.info(f"Created annotation {annotation_id} by {user_id}")
            return ann_data
            
        except Exception as e:
            logger.error(f"Failed to create annotation: {e}")
            raise
            
    async def update_annotation(self, annotation_id: str, updates: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Update an existing annotation"""
        try:
            # Check if annotation exists and user has permission
            annotation = await self.get_annotation(annotation_id)
            if not annotation:
                raise ValueError(f"Annotation {annotation_id} not found")
                
            # Check edit permissions (owner or admin)
            if annotation["created_by"] != user_id:
                # TODO: Check if user has admin permissions
                raise PermissionError("Only annotation owner can edit")
            
            # Acquire lock for concurrent edit protection
            if annotation_id in self.annotation_locks:
                raise ValueError("Annotation is currently being edited")
                
            self.annotation_locks[annotation_id] = user_id
            
            try:
                # Prepare update data
                update_data = {
                    "updated_at": datetime.now(timezone.utc)
                }
                
                # Allow updates to specific fields
                allowed_fields = ["content", "style_data", "is_private", "is_resolved", "metadata"]
                for field in allowed_fields:
                    if field in updates:
                        update_data[field] = updates[field]
                
                # Handle resolution
                if "is_resolved" in updates and updates["is_resolved"]:
                    update_data["resolved_by"] = user_id
                    update_data["resolved_at"] = datetime.now(timezone.utc)
                
                # Update in database
                query = (annotations.update()
                        .where(annotations.c.id == annotation_id)
                        .values(**update_data))
                await db_manager.database.execute(query)
                
                # Update cache
                document_id = str(annotation["document_id"])
                if document_id in self.active_annotations and annotation_id in self.active_annotations[document_id]:
                    self.active_annotations[document_id][annotation_id].update(update_data)
                
                # Get updated annotation
                updated_annotation = await self.get_annotation(annotation_id)
                
                # Log activity
                await self._log_annotation_activity(
                    document_id=document_id,
                    annotation_id=annotation_id,
                    user_id=user_id,
                    activity_type=ActivityType.ANNOTATION_UPDATED,
                    details={"updated_fields": list(updates.keys())}
                )
                
                logger.info(f"Updated annotation {annotation_id} by {user_id}")
                return updated_annotation
                
            finally:
                # Release lock
                if annotation_id in self.annotation_locks:
                    del self.annotation_locks[annotation_id]
                    
        except Exception as e:
            logger.error(f"Failed to update annotation {annotation_id}: {e}")
            raise
            
    async def delete_annotation(self, annotation_id: str, user_id: str) -> bool:
        """Delete an annotation"""
        try:
            # Check if annotation exists and user has permission
            annotation = await self.get_annotation(annotation_id)
            if not annotation:
                raise ValueError(f"Annotation {annotation_id} not found")
                
            # Check delete permissions (owner or admin)
            if annotation["created_by"] != user_id:
                # TODO: Check if user has admin permissions
                raise PermissionError("Only annotation owner can delete")
            
            document_id = str(annotation["document_id"])
            
            # Delete from database (cascade will handle related comments)
            query = annotations.delete().where(annotations.c.id == annotation_id)
            await db_manager.database.execute(query)
            
            # Remove from cache
            if document_id in self.active_annotations and annotation_id in self.active_annotations[document_id]:
                del self.active_annotations[document_id][annotation_id]
            
            # Log activity
            await self._log_annotation_activity(
                document_id=document_id,
                annotation_id=annotation_id,
                user_id=user_id,
                activity_type=ActivityType.ANNOTATION_DELETED,
                details={"annotation_type": annotation["annotation_type"]}
            )
            
            logger.info(f"Deleted annotation {annotation_id} by {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete annotation {annotation_id}: {e}")
            raise
            
    async def get_annotation(self, annotation_id: str) -> Optional[Dict[str, Any]]:
        """Get annotation by ID"""
        try:
            # Check cache first
            for document_id, doc_annotations in self.active_annotations.items():
                if annotation_id in doc_annotations:
                    return doc_annotations[annotation_id]
            
            # Query database
            query = annotations.select().where(annotations.c.id == annotation_id)
            result = await db_manager.database.fetch_one(query)
            
            if result:
                return dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get annotation {annotation_id}: {e}")
            return None
            
    async def get_document_annotations(self, document_id: str, user_id: str, 
                                     include_private: bool = False) -> List[Dict[str, Any]]:
        """Get all annotations for a document"""
        try:
            # Build query conditions
            conditions = [
                annotations.c.document_id == document_id
            ]
            
            # Filter private annotations
            if not include_private:
                conditions.append(
                    (annotations.c.is_private == False) |
                    (annotations.c.created_by == user_id)
                )
            
            # Query database
            query = (annotations.select()
                    .where(*conditions)
                    .order_by(annotations.c.created_at.asc()))
            
            results = await db_manager.database.fetch_all(query)
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get annotations for document {document_id}: {e}")
            return []
            
    async def get_annotations_by_position(self, document_id: str, position_data: Dict[str, Any], 
                                        user_id: str) -> List[Dict[str, Any]]:
        """Get annotations at a specific position (e.g., page, coordinates)"""
        try:
            # Get all document annotations
            all_annotations = await self.get_document_annotations(document_id, user_id)
            
            # Filter by position overlap
            matching_annotations = []
            for annotation in all_annotations:
                if self._positions_overlap(annotation["position_data"], position_data):
                    matching_annotations.append(annotation)
            
            return matching_annotations
            
        except Exception as e:
            logger.error(f"Failed to get annotations by position: {e}")
            return []
            
    def _positions_overlap(self, pos1: Dict[str, Any], pos2: Dict[str, Any]) -> bool:
        """Check if two position data objects overlap"""
        try:
            # Basic position overlap logic
            # This can be enhanced based on specific annotation types
            
            # Check page match (for document-based annotations)
            if "page" in pos1 and "page" in pos2:
                if pos1["page"] != pos2["page"]:
                    return False
            
            # Check coordinate overlap (for spatial annotations)
            if all(k in pos1 and k in pos2 for k in ["x", "y", "width", "height"]):
                x1, y1, w1, h1 = pos1["x"], pos1["y"], pos1["width"], pos1["height"]
                x2, y2, w2, h2 = pos2["x"], pos2["y"], pos2["width"], pos2["height"]
                
                # Check rectangular overlap
                return not (x1 + w1 < x2 or x2 + w2 < x1 or y1 + h1 < y2 or y2 + h2 < y1)
            
            # Check text selection overlap (for text-based annotations)
            if all(k in pos1 and k in pos2 for k in ["start_offset", "end_offset"]):
                start1, end1 = pos1["start_offset"], pos1["end_offset"]
                start2, end2 = pos2["start_offset"], pos2["end_offset"]
                
                # Check text range overlap
                return not (end1 <= start2 or end2 <= start1)
            
            return True  # Default to overlapping if unclear
            
        except Exception:
            return False
            
    async def _log_annotation_activity(self, document_id: str, annotation_id: str, 
                                     user_id: str, activity_type: ActivityType, 
                                     details: Dict[str, Any] = None):
        """Log annotation activity"""
        try:
            # Get workspace from document
            from core.database import documents
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
                "target_id": annotation_id,
                "target_type": "annotation",
                "details": details or {},
                "created_at": datetime.now(timezone.utc)
            }
            
            query = activity_feed.insert().values(**activity_data)
            await db_manager.database.execute(query)
            
        except Exception as e:
            logger.warning(f"Failed to log annotation activity: {e}")
            
    async def get_annotation_statistics(self, document_id: str) -> Dict[str, Any]:
        """Get annotation statistics for a document"""
        try:
            query = f"""
                SELECT 
                    COUNT(*) as total_annotations,
                    COUNT(CASE WHEN annotation_type = 'highlight' THEN 1 END) as highlights,
                    COUNT(CASE WHEN annotation_type = 'note' THEN 1 END) as notes,
                    COUNT(CASE WHEN annotation_type = 'drawing' THEN 1 END) as drawings,
                    COUNT(CASE WHEN annotation_type = 'stamp' THEN 1 END) as stamps,
                    COUNT(CASE WHEN is_resolved = true THEN 1 END) as resolved,
                    COUNT(CASE WHEN is_private = true THEN 1 END) as private_annotations,
                    COUNT(DISTINCT created_by) as unique_annotators
                FROM {annotations.name}
                WHERE document_id = :document_id
            """
            
            result = await db_manager.database.fetch_one(query, {"document_id": document_id})
            return dict(result) if result else {}
            
        except Exception as e:
            logger.error(f"Failed to get annotation statistics: {e}")
            return {}