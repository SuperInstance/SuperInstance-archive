"""
Pagination implementations for all ActiveLog API endpoints.
Provides consistent pagination patterns across all list endpoints.
"""
from typing import Dict, List, Any, Optional, Union
from fastapi import Query, HTTPException, Depends
from pydantic import BaseModel, Field
import asyncio
import logging
from .cursor_pagination import (
    PaginatedResult, CursorInfo, get_pagination_service,
    PaginationService, CursorEncoder
)

logger = logging.getLogger(__name__)


class PaginationParams(BaseModel):
    """Standard pagination parameters for API endpoints."""
    
    cursor: Optional[str] = Field(None, description="Cursor for pagination")
    limit: int = Field(50, ge=1, le=1000, description="Number of items per page")
    
    class Config:
        schema_extra = {
            "example": {
                "cursor": "eyJ0aW1lc3RhbXAiOiAiMjAyMy0xMC0xNVQxMDozMDowMFoiLCAiaWQiOiAiMTIzNDU2NzgifQ==",
                "limit": 50
            }
        }


class OffsetPaginationParams(BaseModel):
    """Offset-based pagination parameters for compatibility."""
    
    page: int = Field(1, ge=1, description="Page number")
    per_page: int = Field(50, ge=1, le=1000, description="Items per page")
    include_total: bool = Field(False, description="Include total count (slower)")


class SearchPaginationParams(PaginationParams):
    """Pagination parameters with search capabilities."""
    
    query: str = Field(..., min_length=1, description="Search query")
    
    class Config:
        schema_extra = {
            "example": {
                "query": "presentation slides",
                "cursor": None,
                "limit": 20
            }
        }


class FilesFilterParams(BaseModel):
    """Filter parameters for files endpoints."""
    
    content_type: Optional[str] = Field(None, description="Filter by content type prefix")
    min_size: Optional[int] = Field(None, ge=0, description="Minimum file size in bytes")
    max_size: Optional[int] = Field(None, ge=0, description="Maximum file size in bytes")
    created_after: Optional[str] = Field(None, description="ISO datetime filter")
    created_before: Optional[str] = Field(None, description="ISO datetime filter")


class PaginatedResponse(BaseModel):
    """Standard paginated response model."""
    
    items: List[Dict[str, Any]]
    pagination: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "items": [
                    {"id": "123", "name": "document.pdf", "size": 1048576},
                    {"id": "456", "name": "image.jpg", "size": 2097152}
                ],
                "pagination": {
                    "next_cursor": "eyJ0aW1lc3RhbXAiOi...",
                    "has_more": True,
                    "limit": 50
                },
                "metadata": {
                    "total_size": 15728640,
                    "file_types": 12
                }
            }
        }


class EndpointPaginationHandler:
    """Handles pagination for all API endpoints."""
    
    def __init__(self, pagination_service: PaginationService):
        self.pagination_service = pagination_service
    
    def _format_paginated_response(
        self,
        result: PaginatedResult,
        request_params: Dict[str, Any] = None
    ) -> PaginatedResponse:
        """Format pagination result for API response."""
        pagination_info = {
            "next_cursor": result.cursor_info.cursor,
            "has_more": result.cursor_info.has_next,
            "has_previous": result.cursor_info.has_previous,
            "limit": request_params.get("limit") if request_params else None
        }
        
        # Add additional pagination info if available
        if result.cursor_info.total_count is not None:
            pagination_info["total_count"] = result.cursor_info.total_count
        
        if result.cursor_info.page_info:
            pagination_info.update(result.cursor_info.page_info)
        
        return PaginatedResponse(
            items=result.items,
            pagination=pagination_info,
            metadata=result.metadata
        )
    
    async def paginate_user_files(
        self,
        user_id: str,
        pagination: PaginationParams,
        filters: FilesFilterParams = None
    ) -> PaginatedResponse:
        """Paginate user files endpoint."""
        try:
            # Build filter parameters
            filter_params = {}
            if filters:
                if filters.content_type:
                    filter_params['content_type_filter'] = filters.content_type
                if filters.min_size is not None and filters.max_size is not None:
                    filter_params['size_filter'] = (filters.min_size, filters.max_size)
            
            result = await self.pagination_service.paginate_user_files(
                user_id=user_id,
                cursor=pagination.cursor,
                limit=pagination.limit,
                **filter_params
            )
            
            return self._format_paginated_response(
                result, {"limit": pagination.limit}
            )
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error paginating user files: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def search_user_files(
        self,
        user_id: str,
        search_params: SearchPaginationParams
    ) -> PaginatedResponse:
        """Search user files with pagination."""
        try:
            result = await self.pagination_service.search_user_files(
                user_id=user_id,
                search_query=search_params.query,
                cursor=search_params.cursor,
                limit=search_params.limit
            )
            
            # Add search metadata
            search_metadata = {
                "query": search_params.query,
                "result_count": len(result.items)
            }
            
            if result.metadata:
                result.metadata.update(search_metadata)
            else:
                result.metadata = search_metadata
            
            return self._format_paginated_response(
                result, {"limit": search_params.limit}
            )
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error searching user files: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def paginate_file_versions(
        self,
        file_id: str,
        user_id: str,
        pagination: PaginationParams
    ) -> PaginatedResponse:
        """Paginate file versions."""
        try:
            # Custom query for file versions
            async with self.pagination_service.db_manager.get_postgres_connection() as conn:
                # Verify file ownership
                file_check = await conn.fetchrow(
                    "SELECT 1 FROM files WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL",
                    file_id, user_id
                )
                if not file_check:
                    raise HTTPException(status_code=404, detail="File not found")
                
                # Build pagination query
                where_conditions = ["file_id = $1"]
                where_params = [file_id]
                cursor_condition = ""
                
                if pagination.cursor:
                    try:
                        cursor_data = CursorEncoder.decode_cursor(pagination.cursor)
                        where_conditions.append("created_at < $2")
                        where_params.append(cursor_data['timestamp'])
                    except Exception:
                        raise HTTPException(status_code=400, detail="Invalid cursor")
                
                where_clause = "WHERE " + " AND ".join(where_conditions)
                
                query = f"""
                    SELECT 
                        id, version_number, size, checksum, 
                        created_at, created_by,
                        u.name as created_by_name
                    FROM file_versions fv
                    LEFT JOIN users u ON fv.created_by = u.id
                    {where_clause}
                    ORDER BY created_at DESC
                    LIMIT ${len(where_params) + 1}
                """
                
                rows = await conn.fetch(query, *where_params, pagination.limit + 1)
                
                # Process results
                has_next = len(rows) > pagination.limit
                items = [dict(row) for row in rows[:pagination.limit]]
                
                # Create next cursor
                next_cursor = None
                if has_next and items:
                    last_item = items[-1]
                    next_cursor = CursorEncoder.encode_cursor({
                        'timestamp': last_item['created_at']
                    })
                
                cursor_info = CursorInfo(
                    cursor=next_cursor,
                    has_previous=pagination.cursor is not None,
                    has_next=has_next
                )
                
                result = PaginatedResult(items=items, cursor_info=cursor_info)
                return self._format_paginated_response(
                    result, {"limit": pagination.limit}
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error paginating file versions: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def paginate_user_activity(
        self,
        user_id: str,
        pagination: PaginationParams,
        action_filter: Optional[str] = None
    ) -> PaginatedResponse:
        """Paginate user activity logs."""
        try:
            async with self.pagination_service.db_manager.get_postgres_connection() as conn:
                # Build query conditions
                where_conditions = ["user_id = $1"]
                where_params = [user_id]
                param_index = 2
                
                if action_filter:
                    where_conditions.append(f"action = ${param_index}")
                    where_params.append(action_filter)
                    param_index += 1
                
                cursor_condition = ""
                if pagination.cursor:
                    try:
                        cursor_data = CursorEncoder.decode_cursor(pagination.cursor)
                        where_conditions.append(f"created_at < ${param_index}")
                        where_params.append(cursor_data['timestamp'])
                        param_index += 1
                    except Exception:
                        raise HTTPException(status_code=400, detail="Invalid cursor")
                
                where_clause = "WHERE " + " AND ".join(where_conditions)
                
                query = f"""
                    SELECT 
                        id, action, resource_type, resource_id,
                        details, created_at, ip_address, user_agent
                    FROM activity_logs
                    {where_clause}
                    ORDER BY created_at DESC
                    LIMIT ${param_index}
                """
                
                rows = await conn.fetch(query, *where_params, pagination.limit + 1)
                
                # Process results
                has_next = len(rows) > pagination.limit
                items = [dict(row) for row in rows[:pagination.limit]]
                
                # Create next cursor
                next_cursor = None
                if has_next and items:
                    last_item = items[-1]
                    next_cursor = CursorEncoder.encode_cursor({
                        'timestamp': last_item['created_at']
                    })
                
                cursor_info = CursorInfo(
                    cursor=next_cursor,
                    has_previous=pagination.cursor is not None,
                    has_next=has_next
                )
                
                result = PaginatedResult(items=items, cursor_info=cursor_info)
                return self._format_paginated_response(
                    result, {"limit": pagination.limit}
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error paginating user activity: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def paginate_shared_files(
        self,
        user_id: str,
        pagination: PaginationParams,
        shared_by_me: bool = False
    ) -> PaginatedResponse:
        """Paginate shared files (with user or by user)."""
        try:
            async with self.pagination_service.db_manager.get_postgres_connection() as conn:
                # Build different queries based on direction
                if shared_by_me:
                    # Files shared by the user
                    user_field = "shared_by"
                    join_condition = "LEFT JOIN users u ON fs.shared_with = u.id"
                    select_extra = "u.name as shared_with_name"
                else:
                    # Files shared with the user
                    user_field = "shared_with"
                    join_condition = "LEFT JOIN users u ON fs.shared_by = u.id"
                    select_extra = "u.name as shared_by_name"
                
                where_conditions = [f"fs.{user_field} = $1", "fs.deleted_at IS NULL", "f.deleted_at IS NULL"]
                where_params = [user_id]
                param_index = 2
                
                # Add expiration filter
                where_conditions.append("(fs.expires_at IS NULL OR fs.expires_at > NOW())")
                
                cursor_condition = ""
                if pagination.cursor:
                    try:
                        cursor_data = CursorEncoder.decode_cursor(pagination.cursor)
                        where_conditions.append(f"fs.created_at < ${param_index}")
                        where_params.append(cursor_data['timestamp'])
                        param_index += 1
                    except Exception:
                        raise HTTPException(status_code=400, detail="Invalid cursor")
                
                where_clause = "WHERE " + " AND ".join(where_conditions)
                
                query = f"""
                    SELECT 
                        f.id, f.name, f.size, f.content_type, f.updated_at,
                        fs.permissions, fs.expires_at, fs.created_at as shared_at,
                        {select_extra}
                    FROM file_shares fs
                    JOIN files f ON fs.file_id = f.id
                    {join_condition}
                    {where_clause}
                    ORDER BY fs.created_at DESC
                    LIMIT ${param_index}
                """
                
                rows = await conn.fetch(query, *where_params, pagination.limit + 1)
                
                # Process results
                has_next = len(rows) > pagination.limit
                items = [dict(row) for row in rows[:pagination.limit]]
                
                # Create next cursor
                next_cursor = None
                if has_next and items:
                    last_item = items[-1]
                    next_cursor = CursorEncoder.encode_cursor({
                        'timestamp': last_item['shared_at']
                    })
                
                cursor_info = CursorInfo(
                    cursor=next_cursor,
                    has_previous=pagination.cursor is not None,
                    has_next=has_next
                )
                
                result = PaginatedResult(items=items, cursor_info=cursor_info)
                return self._format_paginated_response(
                    result, {"limit": pagination.limit}
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error paginating shared files: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")


# Dependency injection helpers
async def get_pagination_handler() -> EndpointPaginationHandler:
    """Get pagination handler for dependency injection."""
    pagination_service = get_pagination_service()
    return EndpointPaginationHandler(pagination_service)


def get_pagination_params(
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    limit: int = Query(50, ge=1, le=1000, description="Items per page")
) -> PaginationParams:
    """Extract pagination parameters from query string."""
    return PaginationParams(cursor=cursor, limit=limit)


def get_search_pagination_params(
    query: str = Query(..., min_length=1, description="Search query"),
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    limit: int = Query(50, ge=1, le=1000, description="Items per page")
) -> SearchPaginationParams:
    """Extract search pagination parameters from query string."""
    return SearchPaginationParams(query=query, cursor=cursor, limit=limit)


def get_files_filter_params(
    content_type: Optional[str] = Query(None, description="Content type filter"),
    min_size: Optional[int] = Query(None, ge=0, description="Minimum file size"),
    max_size: Optional[int] = Query(None, ge=0, description="Maximum file size"),
    created_after: Optional[str] = Query(None, description="Created after ISO datetime"),
    created_before: Optional[str] = Query(None, description="Created before ISO datetime")
) -> FilesFilterParams:
    """Extract file filter parameters from query string."""
    return FilesFilterParams(
        content_type=content_type,
        min_size=min_size,
        max_size=max_size,
        created_after=created_after,
        created_before=created_before
    )


# Global handler instance
pagination_handler = None


async def initialize_pagination_handler():
    """Initialize the global pagination handler."""
    global pagination_handler
    pagination_service = get_pagination_service()
    pagination_handler = EndpointPaginationHandler(pagination_service)
    return pagination_handler


def get_pagination_handler_instance() -> EndpointPaginationHandler:
    """Get the global pagination handler instance."""
    if pagination_handler is None:
        raise RuntimeError("Pagination handler not initialized")
    return pagination_handler