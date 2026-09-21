"""
API routes for smart folders service
"""

import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Path, Body
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

def get_smart_folder_manager():
    """Get smart folder manager instance"""
    # Import here to avoid circular imports
    import main
    if not main.smart_folder_manager:
        raise HTTPException(status_code=500, detail="Smart folder manager not initialized")
    return main.smart_folder_manager

# Create router
router = APIRouter()

# Pydantic models for request/response
class FolderCreateRequest(BaseModel):
    name: str = Field(..., description="Folder name")
    user_id: str = Field(..., description="User ID")
    folder_type: str = Field(default="smart", description="Folder type")
    description: Optional[str] = Field(None, description="Folder description")
    rules: List[Dict[str, Any]] = Field(default_factory=list, description="Folder rules")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Folder settings")

class TemplateCreateRequest(BaseModel):
    template_id: str = Field(..., description="Template ID to use")
    user_id: str = Field(..., description="User ID")
    base_path: str = Field(..., description="Base path for folder creation")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional configuration")

class VirtualFolderRequest(BaseModel):
    name: str = Field(..., description="Virtual folder name")
    user_id: str = Field(..., description="User ID")
    initial_files: List[Dict[str, Any]] = Field(default_factory=list, description="Initial files to add")

class FileReferenceRequest(BaseModel):
    physical_path: str = Field(..., description="Physical file path")
    virtual_name: Optional[str] = Field(None, description="Virtual file name")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="File metadata")

class ShareCreateRequest(BaseModel):
    folder_id: str = Field(..., description="Folder ID to share")
    share_type: str = Field(..., description="Type of share (public_link, direct_user, etc.)")
    permissions: List[str] = Field(..., description="List of permissions to grant")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Share configuration")

class PermissionGrantRequest(BaseModel):
    user_id: str = Field(..., description="User ID to grant permission to")
    permission: str = Field(..., description="Permission to grant")

# Smart Folders endpoints
@router.post("/folders", response_model=Dict[str, Any])
async def create_smart_folder(request: FolderCreateRequest, background_tasks: BackgroundTasks):
    """Create a new smart folder"""
    try:
        manager = get_smart_folder_manager()
        
        config = {
            "name": request.name,
            "user_id": request.user_id,
            "folder_type": request.folder_type,
            "description": request.description,
            "rules": request.rules,
            "settings": request.settings
        }
        
        folder = await manager.create_smart_folder(config)
        
        return {
            "folder_id": folder.folder_id,
            "name": folder.name,
            "folder_type": folder.folder_type.value,
            "created_at": folder.created_at.isoformat(),
            "rules": len(folder.rules)
        }
        
    except Exception as e:
        logger.error(f"Error creating smart folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/folders", response_model=List[Dict[str, Any]])
async def list_smart_folders(user_id: str = Query(..., description="User ID")):
    """List all smart folders for a user"""
    try:
        manager = get_smart_folder_manager()
        folders = await manager.list_user_folders(user_id)
        
        return [
            {
                "folder_id": folder["id"],
                "name": folder["name"],
                "folder_type": folder["folder_type"],
                "description": folder.get("description", ""),
                "created_at": folder["created_at"].isoformat() if folder.get("created_at") else None,
                "rule_count": len(folder.get("rules", []))
            }
            for folder in folders
        ]
        
    except Exception as e:
        logger.error(f"Error listing folders: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/folders/{folder_id}", response_model=Dict[str, Any])
async def get_smart_folder(folder_id: str = Path(..., description="Folder ID")):
    """Get smart folder details"""
    try:
        manager = get_smart_folder_manager()
        folder = await manager.get_smart_folder(folder_id)
        
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")
        
        return folder
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/folders/{folder_id}/content", response_model=List[Dict[str, Any]])
async def get_folder_content(
    folder_id: str = Path(..., description="Folder ID"),
    limit: int = Query(100, description="Maximum items to return"),
    offset: int = Query(0, description="Offset for pagination")
):
    """Get folder content"""
    try:
        manager = get_smart_folder_manager()
        content = await manager.get_folder_content(folder_id, limit, offset)
        
        return content
        
    except Exception as e:
        logger.error(f"Error getting folder content: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/folders/{folder_id}/refresh", response_model=Dict[str, Any])
async def refresh_folder(folder_id: str = Path(..., description="Folder ID")):
    """Refresh folder content by re-evaluating rules"""
    try:
        manager = get_smart_folder_manager()
        result = await manager.refresh_folder(folder_id)
        
        return result
        
    except Exception as e:
        logger.error(f"Error refreshing folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Template endpoints
@router.get("/templates", response_model=List[Dict[str, Any]])
async def list_templates(category: Optional[str] = Query(None, description="Filter by category")):
    """List available folder templates"""
    try:
        manager = get_smart_folder_manager()
        
        if category:
            templates = manager.template_manager.get_templates_by_category(category)
        else:
            templates = manager.template_manager.get_all_templates()
        
        return [template.get_template_info() for template in templates]
        
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/templates/{template_id}", response_model=Dict[str, Any])
async def get_template(template_id: str = Path(..., description="Template ID")):
    """Get template details"""
    try:
        manager = get_smart_folder_manager()
        template = manager.template_manager.get_template(template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return template.get_template_info()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/templates/{template_id}/preview", response_model=Dict[str, Any])
async def preview_template(template_id: str = Path(..., description="Template ID")):
    """Preview what folders would be created from template"""
    try:
        manager = get_smart_folder_manager()
        preview = manager.template_manager.get_template_preview(template_id)
        
        if not preview:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return preview
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/templates/{template_id}/create", response_model=Dict[str, Any])
async def create_folders_from_template(template_id: str = Path(..., description="Template ID"), request: TemplateCreateRequest = Body(...)):
    """Create smart folders from template"""
    try:
        manager = get_smart_folder_manager()
        result = await manager.template_manager.create_folders_from_template(
            template_id, request.user_id, request.base_path, request.config
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error creating folders from template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/templates/categories", response_model=List[str])
async def list_template_categories():
    """List all template categories"""
    try:
        manager = get_smart_folder_manager()
        categories = manager.template_manager.get_categories()
        
        return categories
        
    except Exception as e:
        logger.error(f"Error listing template categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Virtual folder endpoints
@router.post("/virtual-folders", response_model=Dict[str, Any])
async def create_virtual_folder(request: VirtualFolderRequest):
    """Create a new virtual folder"""
    try:
        manager = get_smart_folder_manager()
        
        config = {
            "name": request.name,
            "user_id": request.user_id,
            "initial_files": request.initial_files
        }
        
        # Generate folder ID
        import uuid
        folder_id = str(uuid.uuid4())
        
        virtual_folder = await manager.virtual_manager.create_virtual_folder(folder_id, config)
        
        return {
            "folder_id": virtual_folder.folder_id,
            "name": virtual_folder.name,
            "user_id": virtual_folder.user_id,
            "file_count": len(virtual_folder.file_references),
            "created_at": virtual_folder.created_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error creating virtual folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/virtual-folders/{folder_id}", response_model=Dict[str, Any])
async def get_virtual_folder(folder_id: str = Path(..., description="Virtual folder ID")):
    """Get virtual folder details"""
    try:
        manager = get_smart_folder_manager()
        virtual_folder = await manager.virtual_manager.get_virtual_folder(folder_id)
        
        if not virtual_folder:
            raise HTTPException(status_code=404, detail="Virtual folder not found")
        
        return virtual_folder.get_stats()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting virtual folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/virtual-folders/{folder_id}/content", response_model=List[Dict[str, Any]])
async def get_virtual_folder_content(
    folder_id: str = Path(..., description="Virtual folder ID"),
    limit: int = Query(100, description="Maximum items to return"),
    offset: int = Query(0, description="Offset for pagination")
):
    """Get virtual folder content"""
    try:
        manager = get_smart_folder_manager()
        content = await manager.virtual_manager.get_virtual_folder_content(folder_id, limit, offset)
        
        return content
        
    except Exception as e:
        logger.error(f"Error getting virtual folder content: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/virtual-folders/{folder_id}/files", response_model=Dict[str, Any])
async def add_file_to_virtual_folder(
    folder_id: str = Path(..., description="Virtual folder ID"),
    request: FileReferenceRequest = Body(...)
):
    """Add file reference to virtual folder"""
    try:
        manager = get_smart_folder_manager()
        reference_id = await manager.virtual_manager.add_file_to_virtual_folder(
            folder_id, request.physical_path, request.virtual_name, request.metadata
        )
        
        if not reference_id:
            raise HTTPException(status_code=400, detail="Failed to add file reference")
        
        return {
            "reference_id": reference_id,
            "folder_id": folder_id,
            "physical_path": request.physical_path,
            "virtual_name": request.virtual_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding file to virtual folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/virtual-folders/{folder_id}/files/{reference_id}", response_model=Dict[str, Any])
async def remove_file_from_virtual_folder(
    folder_id: str = Path(..., description="Virtual folder ID"),
    reference_id: str = Path(..., description="File reference ID")
):
    """Remove file reference from virtual folder"""
    try:
        manager = get_smart_folder_manager()
        success = await manager.virtual_manager.remove_file_from_virtual_folder(folder_id, reference_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="File reference not found")
        
        return {
            "success": True,
            "folder_id": folder_id,
            "reference_id": reference_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing file from virtual folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# AI suggestions endpoint
@router.get("/suggestions", response_model=List[Dict[str, Any]])
async def get_folder_suggestions(
    user_id: str = Query(..., description="User ID"),
    path: str = Query(..., description="Path to analyze"),
    suggestion_type: str = Query("structure", description="Type of suggestion")
):
    """Get AI-powered folder suggestions"""
    try:
        manager = get_smart_folder_manager()
        suggestions = await manager.folder_suggester.suggest_folder_structure(
            path, user_id, suggestion_type
        )
        
        return suggestions
        
    except Exception as e:
        logger.error(f"Error getting folder suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Search endpoints
@router.get("/search/folders", response_model=List[Dict[str, Any]])
async def search_folders(
    user_id: str = Query(..., description="User ID"),
    query: str = Query(..., description="Search query")
):
    """Search smart folders"""
    try:
        manager = get_smart_folder_manager()
        results = await manager.search_folders(user_id, query)
        
        return results
        
    except Exception as e:
        logger.error(f"Error searching folders: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search/templates", response_model=List[Dict[str, Any]])
async def search_templates(query: str = Query(..., description="Search query")):
    """Search folder templates"""
    try:
        manager = get_smart_folder_manager()
        results = manager.template_manager.search_templates(query)
        
        return results
        
    except Exception as e:
        logger.error(f"Error searching templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search/virtual-folders", response_model=List[Dict[str, Any]])
async def search_virtual_folders(
    user_id: str = Query(..., description="User ID"),
    query: str = Query(..., description="Search query")
):
    """Search virtual folders"""
    try:
        manager = get_smart_folder_manager()
        results = await manager.virtual_manager.search_virtual_folders(user_id, query)
        
        return results
        
    except Exception as e:
        logger.error(f"Error searching virtual folders: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Inheritance endpoints
@router.post("/folders/{parent_id}/children/{child_id}", response_model=Dict[str, Any])
async def create_folder_relationship(
    parent_id: str = Path(..., description="Parent folder ID"),
    child_id: str = Path(..., description="Child folder ID"),
    inheritance_config: Optional[Dict[str, Any]] = Body(None, description="Inheritance configuration")
):
    """Create parent-child relationship with inheritance rules"""
    try:
        manager = get_smart_folder_manager()
        success = await manager.inheritance_manager.create_folder_relationship(
            parent_id, child_id, inheritance_config
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to create folder relationship")
        
        return {
            "parent_id": parent_id,
            "child_id": child_id,
            "inheritance_config": inheritance_config,
            "success": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating folder relationship: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/folders/{folder_id}/hierarchy", response_model=Dict[str, Any])
async def get_folder_hierarchy(folder_id: str = Path(..., description="Folder ID")):
    """Get folder hierarchy information"""
    try:
        manager = get_smart_folder_manager()
        hierarchy_info = await manager.inheritance_manager.get_folder_hierarchy_info(folder_id)
        
        return hierarchy_info
        
    except Exception as e:
        logger.error(f"Error getting folder hierarchy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/folders/{folder_id}/effective-rules", response_model=List[Dict[str, Any]])
async def get_effective_rules(folder_id: str = Path(..., description="Folder ID")):
    """Get effective rules for folder including inherited ones"""
    try:
        manager = get_smart_folder_manager()
        rules = await manager.inheritance_manager.evaluate_inherited_rules(folder_id)
        
        return rules
        
    except Exception as e:
        logger.error(f"Error getting effective rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/folders/{folder_id}/effective-settings", response_model=Dict[str, Any])
async def get_effective_settings(folder_id: str = Path(..., description="Folder ID")):
    """Get effective settings for folder including inherited ones"""
    try:
        manager = get_smart_folder_manager()
        settings = await manager.inheritance_manager.evaluate_inherited_settings(folder_id)
        
        return settings
        
    except Exception as e:
        logger.error(f"Error getting effective settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/folders/{folder_id}/propagate", response_model=Dict[str, Any])
async def propagate_changes(
    folder_id: str = Path(..., description="Folder ID"),
    change_type: str = Query(..., description="Type of change to propagate")
):
    """Propagate changes from parent to all descendants"""
    try:
        manager = get_smart_folder_manager()
        
        # Import here to avoid circular imports
        from ..core.inheritance_manager import InheritanceType
        
        try:
            inheritance_type = InheritanceType(change_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid change type: {change_type}")
        
        result = await manager.inheritance_manager.propagate_changes_to_children(
            folder_id, inheritance_type
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error propagating changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/hierarchy/validate", response_model=Dict[str, Any])
async def validate_hierarchy():
    """Validate folder hierarchy for cycles and consistency"""
    try:
        manager = get_smart_folder_manager()
        validation_result = await manager.inheritance_manager.validate_hierarchy()
        
        return validation_result
        
    except Exception as e:
        logger.error(f"Error validating hierarchy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Sharing and Permissions endpoints
@router.post("/folders/{folder_id}/share", response_model=Dict[str, Any])
async def create_folder_share(
    folder_id: str = Path(..., description="Folder ID"),
    request: ShareCreateRequest = Body(...),
    owner_id: str = Query(..., description="Owner user ID")
):
    """Create a folder share"""
    try:
        manager = get_smart_folder_manager()
        
        # Import here to avoid circular imports
        from ..permissions.permission_manager import ShareType
        
        try:
            share_type = ShareType(request.share_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid share type: {request.share_type}")
        
        share = await manager.permission_manager.create_folder_share(
            folder_id, owner_id, share_type, request.permissions, request.config
        )
        
        result = share.to_dict()
        
        # Add share URL for public links
        if share_type == ShareType.PUBLIC_LINK:
            result["share_url"] = manager.permission_manager.generate_public_share_url(share.share_id)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating folder share: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/folders/{folder_id}/shares", response_model=List[Dict[str, Any]])
async def get_folder_shares(folder_id: str = Path(..., description="Folder ID")):
    """Get all shares for a folder"""
    try:
        manager = get_smart_folder_manager()
        shares = manager.permission_manager.get_folder_shares(folder_id)
        
        return [share.to_dict() for share in shares]
        
    except Exception as e:
        logger.error(f"Error getting folder shares: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/shares/{share_id}", response_model=Dict[str, Any])
async def get_share(share_id: str = Path(..., description="Share ID")):
    """Get share details"""
    try:
        manager = get_smart_folder_manager()
        share = await manager.permission_manager.get_folder_share(share_id)
        
        if not share:
            raise HTTPException(status_code=404, detail="Share not found or expired")
        
        return share.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting share: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/shares/{share_id}/access", response_model=Dict[str, Any])
async def access_share(
    share_id: str = Path(..., description="Share ID"),
    user_id: Optional[str] = Query(None, description="User ID accessing the share")
):
    """Access a shared folder"""
    try:
        manager = get_smart_folder_manager()
        share = await manager.permission_manager.access_folder_share(share_id, user_id)
        
        if not share:
            raise HTTPException(status_code=404, detail="Share not found or expired")
        
        # Return share details and folder info
        result = share.to_dict()
        
        # Get folder details
        folder = await manager.get_smart_folder(share.folder_id)
        if folder:
            result["folder"] = {
                "id": folder["id"],
                "name": folder["name"],
                "description": folder.get("description", ""),
                "folder_type": folder["folder_type"]
            }
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accessing share: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/shares/{share_id}", response_model=Dict[str, Any])
async def revoke_share(
    share_id: str = Path(..., description="Share ID"),
    user_id: str = Query(..., description="User ID requesting revocation")
):
    """Revoke a folder share"""
    try:
        manager = get_smart_folder_manager()
        success = await manager.permission_manager.revoke_folder_share(share_id, user_id)
        
        if not success:
            raise HTTPException(status_code=403, detail="Not authorized to revoke this share")
        
        return {"share_id": share_id, "revoked": True}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking share: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/folders/{folder_id}/permissions", response_model=Dict[str, Any])
async def grant_folder_permission(
    folder_id: str = Path(..., description="Folder ID"),
    request: PermissionGrantRequest = Body(...)
):
    """Grant direct permission to user for folder"""
    try:
        manager = get_smart_folder_manager()
        
        # Import here to avoid circular imports
        from ..permissions.permission_manager import PermissionType
        
        try:
            permission = PermissionType(request.permission)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid permission type: {request.permission}")
        
        manager.permission_manager.grant_permission(folder_id, request.user_id, permission)
        
        return {
            "folder_id": folder_id,
            "user_id": request.user_id,
            "permission": request.permission,
            "granted": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error granting permission: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/folders/{folder_id}/permissions/{user_id}/{permission}", response_model=Dict[str, Any])
async def revoke_folder_permission(
    folder_id: str = Path(..., description="Folder ID"),
    user_id: str = Path(..., description="User ID"),
    permission: str = Path(..., description="Permission to revoke")
):
    """Revoke direct permission from user for folder"""
    try:
        manager = get_smart_folder_manager()
        
        # Import here to avoid circular imports
        from ..permissions.permission_manager import PermissionType
        
        try:
            permission_type = PermissionType(permission)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid permission type: {permission}")
        
        success = manager.permission_manager.revoke_permission(folder_id, user_id, permission_type)
        
        return {
            "folder_id": folder_id,
            "user_id": user_id,
            "permission": permission,
            "revoked": success
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking permission: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/folders/{folder_id}/permissions", response_model=Dict[str, Any])
async def get_folder_permissions(folder_id: str = Path(..., description="Folder ID")):
    """Get all permissions for a folder"""
    try:
        manager = get_smart_folder_manager()
        permissions = manager.permission_manager.get_folder_permissions(folder_id)
        
        # Convert permission sets to lists for JSON serialization
        result = {}
        for user_id, perms in permissions.items():
            result[user_id] = [p.value for p in perms]
        
        return {
            "folder_id": folder_id,
            "permissions": result
        }
        
    except Exception as e:
        logger.error(f"Error getting folder permissions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{user_id}/shared-folders", response_model=List[Dict[str, Any]])
async def get_user_shared_folders(user_id: str = Path(..., description="User ID")):
    """Get all folders shared with a user"""
    try:
        manager = get_smart_folder_manager()
        shared_folders = manager.permission_manager.get_user_shared_folders(user_id)
        
        return shared_folders
        
    except Exception as e:
        logger.error(f"Error getting user shared folders: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/shares/cleanup", response_model=Dict[str, Any])
async def cleanup_expired_shares():
    """Clean up expired shares"""
    try:
        manager = get_smart_folder_manager()
        cleaned_count = await manager.permission_manager.cleanup_expired_shares()
        
        return {
            "cleaned_shares": cleaned_count,
            "cleanup_completed": True
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up shares: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Statistics endpoints
@router.get("/stats", response_model=Dict[str, Any])
async def get_service_stats():
    """Get smart folders service statistics"""
    try:
        manager = get_smart_folder_manager()
        
        stats = {
            "folders": await manager.get_folder_stats(),
            "templates": manager.template_manager.get_manager_stats(),
            "virtual_folders": manager.virtual_manager.get_manager_stats(),
            "inheritance": manager.inheritance_manager.get_manager_stats(),
            "permissions": manager.permission_manager.get_stats(),
            "ai_suggestions": manager.folder_suggester.get_stats()
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting service stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))