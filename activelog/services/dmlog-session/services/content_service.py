"""
Content Sharing Service

Manages handouts, props, documents, and other content sharing during D&D sessions
with support for file uploads, annotations, and access control.
"""

import asyncio
import os
import uuid
import shutil
import mimetypes
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timedelta
from pathlib import Path
import json
import zipfile
from PIL import Image

from ..models.base import BaseSessionModel
from ..models.content import (
    Handout, ContentShare, SharedDocument, ContentAnnotation,
    ContentAccessLog, ContentLibrary
)
from ..models.session import SessionSchema
from ..config import CONTENT_CONFIG


class FileManager:
    """Handles file operations for shared content"""
    
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (self.storage_path / "handouts").mkdir(exist_ok=True)
        (self.storage_path / "props").mkdir(exist_ok=True)
        (self.storage_path / "documents").mkdir(exist_ok=True)
        (self.storage_path / "thumbnails").mkdir(exist_ok=True)
    
    async def save_file(self, file_data: bytes, filename: str, 
                       content_type: str = "handout") -> str:
        """Save uploaded file and return file path"""
        # Generate unique filename
        file_extension = Path(filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # Determine storage directory
        if content_type == "handout":
            file_path = self.storage_path / "handouts" / unique_filename
        elif content_type == "prop":
            file_path = self.storage_path / "props" / unique_filename
        else:
            file_path = self.storage_path / "documents" / unique_filename
        
        # Save file
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        # Generate thumbnail if image
        if self._is_image(filename):
            await self._generate_thumbnail(file_path, unique_filename)
        
        return str(file_path)
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete a file and its thumbnail"""
        try:
            file_path_obj = Path(file_path)
            if file_path_obj.exists():
                file_path_obj.unlink()
            
            # Delete thumbnail if exists
            thumbnail_path = self.storage_path / "thumbnails" / f"{file_path_obj.stem}_thumb.jpg"
            if thumbnail_path.exists():
                thumbnail_path.unlink()
            
            return True
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")
            return False
    
    async def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get file information"""
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            return {}
        
        stat = file_path_obj.stat()
        mime_type, _ = mimetypes.guess_type(str(file_path_obj))
        
        info = {
            "filename": file_path_obj.name,
            "size": stat.st_size,
            "mime_type": mime_type,
            "created": datetime.fromtimestamp(stat.st_ctime),
            "modified": datetime.fromtimestamp(stat.st_mtime),
            "is_image": self._is_image(file_path_obj.name)
        }
        
        # Add thumbnail path if exists
        thumbnail_path = self.storage_path / "thumbnails" / f"{file_path_obj.stem}_thumb.jpg"
        if thumbnail_path.exists():
            info["thumbnail_path"] = str(thumbnail_path)
        
        return info
    
    def _is_image(self, filename: str) -> bool:
        """Check if file is an image"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}
        return Path(filename).suffix.lower() in image_extensions
    
    async def _generate_thumbnail(self, file_path: Path, unique_filename: str):
        """Generate thumbnail for image files"""
        try:
            with Image.open(file_path) as img:
                img.thumbnail((200, 200), Image.Resampling.LANCZOS)
                
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = rgb_img
                
                thumbnail_path = self.storage_path / "thumbnails" / f"{Path(unique_filename).stem}_thumb.jpg"
                img.save(thumbnail_path, 'JPEG', quality=85)
        
        except Exception as e:
            print(f"Error generating thumbnail for {file_path}: {e}")


class AccessController:
    """Manages access control for shared content"""
    
    def __init__(self):
        self.access_logs: List[ContentAccessLog] = []
        self.content_permissions: Dict[str, Dict[str, Set[str]]] = {}
    
    async def grant_access(self, content_id: str, user_id: str, 
                          permissions: Set[str]):
        """Grant access permissions to a user for content"""
        if content_id not in self.content_permissions:
            self.content_permissions[content_id] = {}
        
        self.content_permissions[content_id][user_id] = permissions
    
    async def revoke_access(self, content_id: str, user_id: str):
        """Revoke all access permissions for a user"""
        if (content_id in self.content_permissions and 
            user_id in self.content_permissions[content_id]):
            del self.content_permissions[content_id][user_id]
    
    async def check_permission(self, content_id: str, user_id: str, 
                              permission: str) -> bool:
        """Check if user has specific permission for content"""
        if (content_id in self.content_permissions and 
            user_id in self.content_permissions[content_id]):
            return permission in self.content_permissions[content_id][user_id]
        return False
    
    async def log_access(self, content_id: str, user_id: str, 
                        action: str, session_id: str):
        """Log content access"""
        access_log = ContentAccessLog(
            content_id=content_id,
            user_id=user_id,
            action=action,
            session_id=session_id,
            timestamp=datetime.utcnow()
        )
        self.access_logs.append(access_log)
    
    async def get_access_logs(self, content_id: Optional[str] = None,
                             user_id: Optional[str] = None,
                             session_id: Optional[str] = None) -> List[ContentAccessLog]:
        """Get access logs with optional filtering"""
        logs = self.access_logs
        
        if content_id:
            logs = [log for log in logs if log.content_id == content_id]
        if user_id:
            logs = [log for log in logs if log.user_id == user_id]
        if session_id:
            logs = [log for log in logs if log.session_id == session_id]
        
        return sorted(logs, key=lambda x: x.timestamp, reverse=True)


class AnnotationManager:
    """Manages annotations on shared content"""
    
    def __init__(self):
        self.annotations: Dict[str, List[ContentAnnotation]] = {}
    
    async def add_annotation(self, content_id: str, annotation: ContentAnnotation) -> str:
        """Add annotation to content"""
        if not annotation.id:
            annotation.id = str(uuid.uuid4())
        
        if content_id not in self.annotations:
            self.annotations[content_id] = []
        
        self.annotations[content_id].append(annotation)
        return annotation.id
    
    async def update_annotation(self, content_id: str, annotation_id: str,
                               updates: Dict[str, Any]) -> bool:
        """Update an annotation"""
        if content_id not in self.annotations:
            return False
        
        for annotation in self.annotations[content_id]:
            if annotation.id == annotation_id:
                for key, value in updates.items():
                    if hasattr(annotation, key):
                        setattr(annotation, key, value)
                annotation.updated_at = datetime.utcnow()
                return True
        
        return False
    
    async def delete_annotation(self, content_id: str, annotation_id: str,
                               user_id: str) -> bool:
        """Delete an annotation"""
        if content_id not in self.annotations:
            return False
        
        for i, annotation in enumerate(self.annotations[content_id]):
            if (annotation.id == annotation_id and 
                annotation.created_by == user_id):
                del self.annotations[content_id][i]
                return True
        
        return False
    
    async def get_annotations(self, content_id: str) -> List[ContentAnnotation]:
        """Get all annotations for content"""
        return self.annotations.get(content_id, [])


class ContentLibraryManager:
    """Manages content libraries and organization"""
    
    def __init__(self):
        self.libraries: Dict[str, ContentLibrary] = {}
        self.content_to_library: Dict[str, str] = {}
    
    async def create_library(self, library: ContentLibrary) -> str:
        """Create a new content library"""
        if not library.id:
            library.id = str(uuid.uuid4())
        
        self.libraries[library.id] = library
        return library.id
    
    async def add_to_library(self, library_id: str, content_id: str) -> bool:
        """Add content to a library"""
        if library_id not in self.libraries:
            return False
        
        if content_id not in self.libraries[library_id].content_ids:
            self.libraries[library_id].content_ids.append(content_id)
            self.content_to_library[content_id] = library_id
        
        return True
    
    async def remove_from_library(self, library_id: str, content_id: str) -> bool:
        """Remove content from a library"""
        if library_id not in self.libraries:
            return False
        
        if content_id in self.libraries[library_id].content_ids:
            self.libraries[library_id].content_ids.remove(content_id)
            if content_id in self.content_to_library:
                del self.content_to_library[content_id]
        
        return True
    
    async def get_library_contents(self, library_id: str) -> List[str]:
        """Get all content IDs in a library"""
        if library_id in self.libraries:
            return self.libraries[library_id].content_ids
        return []


class ContentSharingService:
    """Main content sharing service"""
    
    def __init__(self, storage_path: str = None):
        if storage_path is None:
            storage_path = CONTENT_CONFIG["storage_path"]
        
        self.file_manager = FileManager(storage_path)
        self.access_controller = AccessController()
        self.annotation_manager = AnnotationManager()
        self.library_manager = ContentLibraryManager()
        
        self.shared_content: Dict[str, ContentShare] = {}
        self.handouts: Dict[str, Handout] = {}
        self.documents: Dict[str, SharedDocument] = {}
    
    async def upload_handout(self, file_data: bytes, filename: str,
                            session_id: str, uploaded_by: str,
                            title: str = None, description: str = None,
                            allow_download: bool = True,
                            allow_annotation: bool = True) -> str:
        """Upload and share a handout"""
        # Save file
        file_path = await self.file_manager.save_file(
            file_data, filename, "handout"
        )
        
        # Create handout
        handout = Handout(
            id=str(uuid.uuid4()),
            title=title or filename,
            description=description,
            file_path=file_path,
            uploaded_by=uploaded_by,
            allow_download=allow_download,
            allow_annotation=allow_annotation,
            uploaded_at=datetime.utcnow()
        )
        
        self.handouts[handout.id] = handout
        
        # Create content share
        content_share = ContentShare(
            id=handout.id,
            session_id=session_id,
            content_type="handout",
            title=handout.title,
            shared_by=uploaded_by,
            shared_at=datetime.utcnow(),
            is_active=True
        )
        
        self.shared_content[content_share.id] = content_share
        
        # Grant full access to uploader
        await self.access_controller.grant_access(
            handout.id, uploaded_by, {"view", "download", "annotate"}
        )
        
        # Log upload
        await self.access_controller.log_access(
            handout.id, uploaded_by, "upload", session_id
        )
        
        return handout.id
    
    async def share_content(self, content_id: str, user_ids: List[str],
                           permissions: Set[str], session_id: str,
                           shared_by: str) -> bool:
        """Share content with specific users"""
        if content_id not in self.shared_content:
            return False
        
        # Grant permissions to each user
        for user_id in user_ids:
            await self.access_controller.grant_access(
                content_id, user_id, permissions
            )
        
        # Log sharing
        await self.access_controller.log_access(
            content_id, shared_by, "share", session_id
        )
        
        return True
    
    async def access_content(self, content_id: str, user_id: str,
                            session_id: str) -> Optional[Dict[str, Any]]:
        """Access shared content"""
        # Check permission
        if not await self.access_controller.check_permission(
            content_id, user_id, "view"
        ):
            return None
        
        # Get content
        content_data = None
        if content_id in self.handouts:
            handout = self.handouts[content_id]
            content_data = {
                "type": "handout",
                "content": handout.dict(),
                "file_info": await self.file_manager.get_file_info(handout.file_path)
            }
        elif content_id in self.documents:
            document = self.documents[content_id]
            content_data = {
                "type": "document",
                "content": document.dict()
            }
        
        if content_data:
            # Log access
            await self.access_controller.log_access(
                content_id, user_id, "view", session_id
            )
            
            # Add annotations if user has permission
            if await self.access_controller.check_permission(
                content_id, user_id, "annotate"
            ):
                content_data["annotations"] = [
                    ann.dict() for ann in await self.annotation_manager.get_annotations(content_id)
                ]
            
            return content_data
        
        return None
    
    async def download_content(self, content_id: str, user_id: str,
                              session_id: str) -> Optional[str]:
        """Download content file"""
        # Check download permission
        if not await self.access_controller.check_permission(
            content_id, user_id, "download"
        ):
            return None
        
        # Get file path
        file_path = None
        if content_id in self.handouts:
            handout = self.handouts[content_id]
            if handout.allow_download:
                file_path = handout.file_path
        
        if file_path and Path(file_path).exists():
            # Log download
            await self.access_controller.log_access(
                content_id, user_id, "download", session_id
            )
            return file_path
        
        return None
    
    async def add_annotation(self, content_id: str, annotation: ContentAnnotation,
                            user_id: str, session_id: str) -> Optional[str]:
        """Add annotation to content"""
        # Check annotation permission
        if not await self.access_controller.check_permission(
            content_id, user_id, "annotate"
        ):
            return None
        
        # Check if content allows annotations
        if content_id in self.handouts:
            if not self.handouts[content_id].allow_annotation:
                return None
        
        annotation.created_by = user_id
        annotation.created_at = datetime.utcnow()
        
        annotation_id = await self.annotation_manager.add_annotation(
            content_id, annotation
        )
        
        # Log annotation
        await self.access_controller.log_access(
            content_id, user_id, "annotate", session_id
        )
        
        return annotation_id
    
    async def create_content_package(self, session_id: str, user_id: str,
                                   content_ids: List[str]) -> Optional[str]:
        """Create downloadable package of multiple content items"""
        # Check permissions for all content
        accessible_content = []
        
        for content_id in content_ids:
            if await self.access_controller.check_permission(
                content_id, user_id, "download"
            ):
                accessible_content.append(content_id)
        
        if not accessible_content:
            return None
        
        # Create zip package
        package_filename = f"session_content_{session_id}_{uuid.uuid4().hex[:8]}.zip"
        package_path = self.file_manager.storage_path / "packages" / package_filename
        package_path.parent.mkdir(exist_ok=True)
        
        try:
            with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for content_id in accessible_content:
                    if content_id in self.handouts:
                        handout = self.handouts[content_id]
                        if Path(handout.file_path).exists():
                            # Add file with meaningful name
                            arc_name = f"{handout.title}_{Path(handout.file_path).name}"
                            zipf.write(handout.file_path, arc_name)
                
                # Add content manifest
                manifest = {
                    "created_at": datetime.utcnow().isoformat(),
                    "session_id": session_id,
                    "created_by": user_id,
                    "contents": [
                        {
                            "id": cid,
                            "title": self.handouts[cid].title if cid in self.handouts else "Unknown",
                            "type": "handout" if cid in self.handouts else "document"
                        }
                        for cid in accessible_content
                    ]
                }
                
                zipf.writestr("manifest.json", json.dumps(manifest, indent=2))
            
            return str(package_path)
        
        except Exception as e:
            print(f"Error creating content package: {e}")
            return None
    
    async def get_session_content(self, session_id: str,
                                 user_id: str) -> List[Dict[str, Any]]:
        """Get all content shared in a session that user can access"""
        session_content = []
        
        for content_id, content_share in self.shared_content.items():
            if (content_share.session_id == session_id and
                await self.access_controller.check_permission(
                    content_id, user_id, "view"
                )):
                
                content_info = {
                    "share_info": content_share.dict(),
                    "access_permissions": self.access_controller.content_permissions.get(
                        content_id, {}
                    ).get(user_id, set())
                }
                
                # Add specific content details
                if content_id in self.handouts:
                    content_info["handout"] = self.handouts[content_id].dict()
                    content_info["file_info"] = await self.file_manager.get_file_info(
                        self.handouts[content_id].file_path
                    )
                elif content_id in self.documents:
                    content_info["document"] = self.documents[content_id].dict()
                
                session_content.append(content_info)
        
        return session_content
    
    async def cleanup_expired_content(self, days_old: int = 30):
        """Clean up content older than specified days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        expired_content = []
        for content_id, content_share in self.shared_content.items():
            if content_share.shared_at < cutoff_date and not content_share.is_active:
                expired_content.append(content_id)
        
        for content_id in expired_content:
            # Delete file
            if content_id in self.handouts:
                await self.file_manager.delete_file(self.handouts[content_id].file_path)
                del self.handouts[content_id]
            elif content_id in self.documents:
                del self.documents[content_id]
            
            # Clean up related data
            del self.shared_content[content_id]
            if content_id in self.access_controller.content_permissions:
                del self.access_controller.content_permissions[content_id]
            if content_id in self.annotation_manager.annotations:
                del self.annotation_manager.annotations[content_id]
        
        return len(expired_content)