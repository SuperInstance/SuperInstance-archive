"""
Mobile Sync API - Offline-first synchronization
Optimized for mobile bandwidth and battery efficiency
"""

import asyncio
import hashlib
import gzip
import lz4.frame
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, validator
import orjson

from ..core.config import settings, mobile_settings
from ..services.sync_manager import SyncManager, SyncConflictResolver
from ..services.battery_manager import BatteryManager
from ..middleware.compression import compress_response
from ..middleware.mobile_optimization import get_device_info, get_connection_info
from ..middleware.rate_limiting import rate_limit
from ..api.auth import get_current_user
from ..protobuf.generated.mobile_pb import (
    SyncRequest, SyncResponse, SyncItem, SyncConflict, SyncStats,
    BatteryImpact, DeviceInfo, SyncMode, SyncOptions
)

router = APIRouter()

# Pydantic models for JSON API
class SyncRequestModel(BaseModel):
    sync_token: Optional[str] = None
    mode: str = "incremental"  # full, incremental, selective, metadata
    options: Dict[str, Any] = {}
    file_ids: Optional[List[str]] = None
    since_timestamp: Optional[datetime] = None
    max_items: int = 100
    include_thumbnails: bool = True
    include_content: bool = False
    compression: str = "auto"  # none, gzip, brotli, lz4, auto
    
    @validator('mode')
    def validate_mode(cls, v):
        allowed_modes = ['full', 'incremental', 'selective', 'metadata']
        if v not in allowed_modes:
            raise ValueError(f'Mode must be one of {allowed_modes}')
        return v
    
    @validator('max_items')
    def validate_max_items(cls, v):
        return min(v, 500)  # Limit for mobile optimization

class ConflictResolutionModel(BaseModel):
    file_id: str
    resolution: str  # server_wins, client_wins, merge, rename_both, manual
    resolved_metadata: Optional[Dict[str, Any]] = None

class BatchSyncRequest(BaseModel):
    requests: List[SyncRequestModel]
    atomic: bool = False
    max_concurrent: int = 3

# Dependency injection
async def get_sync_manager(request: Request) -> SyncManager:
    return request.app.state.sync_manager

async def get_battery_manager(request: Request) -> BatteryManager:
    return request.app.state.battery_manager

async def get_conflict_resolver(request: Request) -> SyncConflictResolver:
    return SyncConflictResolver(request.app.state.database)

@router.post("/sync", response_model=Dict[str, Any])
@rate_limit("sync_request", per_minute=30, per_hour=200)
async def sync_files(
    request_data: SyncRequestModel,
    http_request: Request,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    sync_manager: SyncManager = Depends(get_sync_manager),
    battery_manager: BatteryManager = Depends(get_battery_manager)
):
    """
    Main synchronization endpoint
    Features:
    - Bandwidth-optimized delta sync
    - Battery-aware sync strategies
    - Compression and deduplication
    - Conflict resolution
    """
    
    device_info = get_device_info(http_request)
    connection_info = get_connection_info(http_request)
    
    # Start battery monitoring for this sync session
    sync_session_id = await battery_manager.start_sync_session(
        user_id=current_user["id"],
        device_info=device_info,
        connection_info=connection_info
    )
    
    try:
        # Optimize sync parameters based on device and connection
        optimized_params = await _optimize_sync_params(
            request_data, device_info, connection_info
        )
        
        # Execute sync with optimizations
        sync_result = await sync_manager.sync_files(
            user_id=current_user["id"],
            device_id=device_info.get("device_id"),
            sync_token=request_data.sync_token,
            mode=optimized_params["mode"],
            options=optimized_params["options"],
            file_ids=request_data.file_ids,
            since_timestamp=request_data.since_timestamp,
            max_items=optimized_params["max_items"]
        )
        
        # Apply compression if requested
        response_data = sync_result
        if optimized_params["compression"] != "none":
            response_data = await _compress_sync_response(
                sync_result, optimized_params["compression"]
            )
        
        # Update battery usage statistics
        battery_impact = await battery_manager.end_sync_session(
            sync_session_id, 
            len(sync_result.get("items", [])),
            response_data.get("stats", {}).get("bytes_transferred", 0)
        )
        
        # Add mobile-specific metadata to response
        response_data.update({
            "battery_impact": {
                "level": battery_impact.level,
                "estimated_drain_percent": battery_impact.drain_percent,
                "optimization_hint": battery_impact.optimization_hint
            },
            "sync_session_id": sync_session_id,
            "next_sync_recommendation": await _calculate_next_sync_time(
                connection_info, battery_impact, device_info
            ),
            "compression_applied": optimized_params["compression"],
            "optimization_applied": True
        })
        
        # Background task to update sync statistics
        background_tasks.add_task(
            sync_manager.update_sync_statistics,
            current_user["id"],
            device_info.get("device_id"),
            sync_result.get("stats", {})
        )
        
        return response_data
        
    except Exception as e:
        # End battery session with error
        await battery_manager.end_sync_session(sync_session_id, error=str(e))
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "sync_failed",
                "message": "Synchronization failed",
                "battery_impact": "medium",
                "retry_after": 60,
                "sync_session_id": sync_session_id
            }
        )

@router.get("/sync/status")
async def get_sync_status(
    current_user: dict = Depends(get_current_user),
    sync_manager: SyncManager = Depends(get_sync_manager)
):
    """Get current synchronization status"""
    
    try:
        status = await sync_manager.get_sync_status(current_user["id"])
        
        return {
            "success": True,
            "status": status,
            "battery_impact": "minimal"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "status_error",
                "message": "Failed to get sync status",
                "battery_impact": "minimal"
            }
        )

@router.post("/sync/resolve-conflicts")
@rate_limit("conflict_resolution", per_minute=20, per_hour=100)
async def resolve_conflicts(
    resolutions: List[ConflictResolutionModel],
    current_user: dict = Depends(get_current_user),
    conflict_resolver: SyncConflictResolver = Depends(get_conflict_resolver)
):
    """Resolve synchronization conflicts"""
    
    try:
        results = []
        for resolution in resolutions:
            result = await conflict_resolver.resolve_conflict(
                user_id=current_user["id"],
                file_id=resolution.file_id,
                resolution_type=resolution.resolution,
                resolved_metadata=resolution.resolved_metadata
            )
            results.append(result)
        
        return {
            "success": True,
            "resolved_conflicts": results,
            "battery_impact": "low"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "conflict_resolution_error",
                "message": "Failed to resolve conflicts",
                "battery_impact": "low"
            }
        )

@router.get("/sync/conflicts")
async def get_pending_conflicts(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    sync_manager: SyncManager = Depends(get_sync_manager)
):
    """Get pending sync conflicts for user"""
    
    try:
        conflicts = await sync_manager.get_pending_conflicts(
            user_id=current_user["id"],
            limit=limit,
            offset=offset
        )
        
        return {
            "success": True,
            "conflicts": conflicts,
            "has_more": len(conflicts) == limit,
            "battery_impact": "minimal"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "conflicts_error",
                "message": "Failed to get conflicts",
                "battery_impact": "minimal"
            }
        )

@router.post("/sync/batch")
@rate_limit("batch_sync", per_minute=10, per_hour=50)
async def batch_sync(
    request_data: BatchSyncRequest,
    http_request: Request,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    sync_manager: SyncManager = Depends(get_sync_manager),
    battery_manager: BatteryManager = Depends(get_battery_manager)
):
    """
    Batch synchronization for multiple requests
    Optimized for efficiency and battery usage
    """
    
    device_info = get_device_info(http_request)
    connection_info = get_connection_info(http_request)
    
    # Start batch sync session
    batch_session_id = await battery_manager.start_batch_session(
        user_id=current_user["id"],
        batch_size=len(request_data.requests),
        device_info=device_info,
        connection_info=connection_info
    )
    
    try:
        results = []
        if request_data.atomic:
            # All or nothing - use transaction
            results = await sync_manager.batch_sync_atomic(
                user_id=current_user["id"],
                requests=[req.dict() for req in request_data.requests],
                device_info=device_info,
                connection_info=connection_info
            )
        else:
            # Process requests with limited concurrency
            semaphore = asyncio.Semaphore(request_data.max_concurrent)
            tasks = []
            
            for i, req in enumerate(request_data.requests):
                task = _process_sync_request_with_semaphore(
                    semaphore, req, current_user["id"], 
                    device_info, connection_info, sync_manager, i
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Calculate batch statistics
        successful_requests = sum(1 for r in results if not isinstance(r, Exception))
        total_bytes = sum(
            r.get("stats", {}).get("bytes_transferred", 0) 
            for r in results if isinstance(r, dict)
        )
        
        # End batch session
        battery_impact = await battery_manager.end_batch_session(
            batch_session_id, successful_requests, total_bytes
        )
        
        return {
            "success": True,
            "results": [
                r if isinstance(r, dict) else {"error": str(r)}
                for r in results
            ],
            "batch_stats": {
                "total_requests": len(request_data.requests),
                "successful": successful_requests,
                "failed": len(request_data.requests) - successful_requests,
                "total_bytes_transferred": total_bytes
            },
            "battery_impact": {
                "level": battery_impact.level,
                "estimated_drain_percent": battery_impact.drain_percent,
                "optimization_hint": battery_impact.optimization_hint
            },
            "batch_session_id": batch_session_id
        }
        
    except Exception as e:
        await battery_manager.end_batch_session(batch_session_id, error=str(e))
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "batch_sync_failed",
                "message": "Batch synchronization failed",
                "battery_impact": "high",
                "retry_after": 120
            }
        )

@router.get("/sync/delta/{file_id}")
async def get_file_delta(
    file_id: str,
    since_version: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    sync_manager: SyncManager = Depends(get_sync_manager)
):
    """Get delta changes for a specific file"""
    
    try:
        delta = await sync_manager.get_file_delta(
            user_id=current_user["id"],
            file_id=file_id,
            since_version=since_version
        )
        
        if not delta:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "file_not_found",
                    "message": "File not found or no changes",
                    "battery_impact": "minimal"
                }
            )
        
        return {
            "success": True,
            "delta": delta,
            "battery_impact": "low"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "delta_error",
                "message": "Failed to get file delta",
                "battery_impact": "minimal"
            }
        )

@router.post("/sync/upload-delta/{file_id}")
@rate_limit("delta_upload", per_minute=50, per_hour=300)
async def upload_file_delta(
    file_id: str,
    delta_data: dict,
    current_user: dict = Depends(get_current_user),
    sync_manager: SyncManager = Depends(get_sync_manager)
):
    """Upload delta changes for a file"""
    
    try:
        result = await sync_manager.apply_file_delta(
            user_id=current_user["id"],
            file_id=file_id,
            delta_data=delta_data
        )
        
        return {
            "success": True,
            "result": result,
            "battery_impact": "low"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "delta_upload_error",
                "message": "Failed to apply file delta",
                "battery_impact": "medium"
            }
        )

@router.get("/sync/offline-queue")
async def get_offline_queue(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(100, le=500),
    sync_manager: SyncManager = Depends(get_sync_manager)
):
    """Get queued offline operations"""
    
    try:
        queue = await sync_manager.get_offline_queue(
            user_id=current_user["id"],
            limit=limit
        )
        
        return {
            "success": True,
            "queue": queue,
            "battery_impact": "minimal"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "queue_error",
                "message": "Failed to get offline queue",
                "battery_impact": "minimal"
            }
        )

@router.post("/sync/offline-queue")
async def add_to_offline_queue(
    operations: List[Dict[str, Any]],
    current_user: dict = Depends(get_current_user),
    sync_manager: SyncManager = Depends(get_sync_manager)
):
    """Add operations to offline queue"""
    
    try:
        queue_ids = await sync_manager.add_to_offline_queue(
            user_id=current_user["id"],
            operations=operations
        )
        
        return {
            "success": True,
            "queue_ids": queue_ids,
            "battery_impact": "minimal"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "queue_add_error",
                "message": "Failed to add to offline queue",
                "battery_impact": "minimal"
            }
        )

@router.delete("/sync/offline-queue/{operation_id}")
async def remove_from_offline_queue(
    operation_id: str,
    current_user: dict = Depends(get_current_user),
    sync_manager: SyncManager = Depends(get_sync_manager)
):
    """Remove operation from offline queue"""
    
    try:
        success = await sync_manager.remove_from_offline_queue(
            user_id=current_user["id"],
            operation_id=operation_id
        )
        
        return {
            "success": success,
            "battery_impact": "minimal"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "queue_remove_error",
                "message": "Failed to remove from offline queue",
                "battery_impact": "minimal"
            }
        )

@router.get("/sync/history")
async def get_sync_history(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    sync_manager: SyncManager = Depends(get_sync_manager)
):
    """Get synchronization history"""
    
    try:
        history = await sync_manager.get_sync_history(
            user_id=current_user["id"],
            limit=limit,
            offset=offset
        )
        
        return {
            "success": True,
            "history": history,
            "has_more": len(history) == limit,
            "battery_impact": "minimal"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "history_error",
                "message": "Failed to get sync history",
                "battery_impact": "minimal"
            }
        )

# Helper functions
async def _optimize_sync_params(
    request_data: SyncRequestModel,
    device_info: Dict[str, Any],
    connection_info: Dict[str, Any]
) -> Dict[str, Any]:
    """Optimize sync parameters based on device and connection"""
    
    # Get connection-specific settings
    connection_type = connection_info.get("type", "wifi")
    connection_settings = mobile_settings.get_sync_settings(connection_type)
    
    # Get battery-specific settings
    battery_level = device_info.get("battery", {}).get("level", 100)
    battery_settings = mobile_settings.get_battery_settings(battery_level)
    
    return {
        "mode": request_data.mode,
        "max_items": min(
            request_data.max_items,
            connection_settings["batch_size"]
        ),
        "options": {
            **request_data.options,
            "include_thumbnails": request_data.include_thumbnails and connection_settings["enable_high_quality"],
            "include_content": request_data.include_content and connection_settings["enable_video"],
            "max_file_size": connection_settings["max_file_size"],
            "timeout": connection_settings["timeout"],
            "battery_optimization": True
        },
        "compression": _select_optimal_compression(
            request_data.compression,
            connection_info,
            device_info
        )
    }

def _select_optimal_compression(
    requested: str,
    connection_info: Dict[str, Any],
    device_info: Dict[str, Any]
) -> str:
    """Select optimal compression based on device capabilities and connection"""
    
    if requested != "auto":
        return requested
    
    # Check device performance tier
    device_tier = device_info.get("performance_tier", "mid_range")
    connection_type = connection_info.get("type", "wifi")
    
    if device_tier == "high_end" and connection_type in ["wifi", "cellular_5g"]:
        return "brotli"  # Best compression ratio
    elif device_tier == "mid_range":
        return "lz4"     # Good compression, fast
    else:
        return "gzip"    # Basic compression, low CPU usage

async def _compress_sync_response(
    response_data: Dict[str, Any],
    compression_type: str
) -> Dict[str, Any]:
    """Apply compression to sync response data"""
    
    if compression_type == "none":
        return response_data
    
    # Compress large data fields
    if "items" in response_data:
        for item in response_data["items"]:
            if "content" in item and item["content"]:
                if compression_type == "gzip":
                    item["content"] = gzip.compress(item["content"].encode()).decode("latin-1")
                elif compression_type == "lz4":
                    item["content"] = lz4.frame.compress(item["content"].encode()).decode("latin-1")
                elif compression_type == "brotli":
                    import brotli
                    item["content"] = brotli.compress(item["content"].encode()).decode("latin-1")
                
                item["content_compressed"] = compression_type
    
    return response_data

async def _calculate_next_sync_time(
    connection_info: Dict[str, Any],
    battery_impact: Any,
    device_info: Dict[str, Any]
) -> int:
    """Calculate recommended time for next sync"""
    
    base_interval = 300  # 5 minutes
    
    # Adjust based on connection type
    connection_type = connection_info.get("type", "wifi")
    if connection_type == "wifi":
        interval = base_interval
    elif connection_type in ["cellular_5g", "cellular_4g"]:
        interval = base_interval * 2
    else:
        interval = base_interval * 4
    
    # Adjust based on battery impact
    if hasattr(battery_impact, 'level'):
        if battery_impact.level in ["high", "medium"]:
            interval *= 2
    
    # Adjust based on battery level
    battery_level = device_info.get("battery", {}).get("level", 100)
    if battery_level < 20:
        interval *= 3
    elif battery_level < 50:
        interval *= 1.5
    
    return int(interval)

async def _process_sync_request_with_semaphore(
    semaphore: asyncio.Semaphore,
    request_data: SyncRequestModel,
    user_id: str,
    device_info: Dict[str, Any],
    connection_info: Dict[str, Any],
    sync_manager: SyncManager,
    index: int
) -> Dict[str, Any]:
    """Process individual sync request with concurrency control"""
    
    async with semaphore:
        try:
            optimized_params = await _optimize_sync_params(
                request_data, device_info, connection_info
            )
            
            result = await sync_manager.sync_files(
                user_id=user_id,
                device_id=device_info.get("device_id"),
                sync_token=request_data.sync_token,
                mode=optimized_params["mode"],
                options=optimized_params["options"],
                file_ids=request_data.file_ids,
                since_timestamp=request_data.since_timestamp,
                max_items=optimized_params["max_items"]
            )
            
            result["batch_index"] = index
            return result
            
        except Exception as e:
            return {
                "batch_index": index,
                "error": str(e),
                "success": False
            }