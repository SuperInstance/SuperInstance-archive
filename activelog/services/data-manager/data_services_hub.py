# Data Services Integration Hub
# Connects all data-related services to the data-manager

import asyncio
import aiohttp
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
import json
import uuid
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import mimetypes
from pathlib import Path

logger = logging.getLogger(__name__)

class DataServiceType(Enum):
    DATA_EXPORT = "data-export"
    BATCH_IMPORT = "batch-import"
    METADATA = "metadata"
    FILE_PROCESSOR = "file-processor"
    SYNC_ENGINE = "sync-engine"
    SYNC_V2 = "sync-v2"
    FILE_SYNC = "file-sync"
    P2P_SYNC = "p2p-sync"
    FILE_WATCHER = "file-watcher"

@dataclass
class DataOperation:
    operation_id: str
    service: str
    operation_type: str  # import, export, sync, process, index, analyze
    source: str
    target: Optional[str] = None
    metadata: Dict[str, Any] = None
    status: str = "pending"  # pending, processing, completed, failed
    started_at: str = None
    completed_at: str = None
    error: Optional[str] = None
    progress: float = 0.0
    
@dataclass
class ServiceEndpoint:
    name: str
    service_type: DataServiceType
    base_url: str
    port: int
    health_endpoint: str = "/health"
    capabilities: List[str] = None
    priority: int = 1
    max_concurrent_operations: int = 5

class DataServicesHub:
    """Central hub managing all data services integration with data-manager"""
    
    def __init__(self, data_manager_url: str = "http://data-manager.activelog:8010"):
        self.data_manager_url = data_manager_url
        self.services = {}
        self.operations_queue = []
        self.active_operations = {}
        self.completed_operations = {}
        self.service_health = {}
        self.setup_services()
        
    def setup_services(self):
        """Initialize all data service endpoints"""
        
        # Data Export Service
        self.services[DataServiceType.DATA_EXPORT] = ServiceEndpoint(
            name="data-export",
            service_type=DataServiceType.DATA_EXPORT,
            base_url="http://data-export.activelog",
            port=8011,
            capabilities=["export_json", "export_csv", "export_xml", "export_pdf", "bulk_export"],
            priority=2,
            max_concurrent_operations=3
        )
        
        # Batch Import Service
        self.services[DataServiceType.BATCH_IMPORT] = ServiceEndpoint(
            name="batch-import",
            service_type=DataServiceType.BATCH_IMPORT,
            base_url="http://batch-import.activelog",
            port=8012,
            capabilities=["batch_upload", "csv_import", "json_import", "file_validation", "progress_tracking"],
            priority=1,
            max_concurrent_operations=2
        )
        
        # Metadata Service
        self.services[DataServiceType.METADATA] = ServiceEndpoint(
            name="metadata",
            service_type=DataServiceType.METADATA,
            base_url="http://metadata.activelog",
            port=8013,
            capabilities=["extract_metadata", "index_content", "search", "tag_management", "relationship_mapping"],
            priority=1,
            max_concurrent_operations=10
        )
        
        # File Processor Service
        self.services[DataServiceType.FILE_PROCESSOR] = ServiceEndpoint(
            name="file-processor",
            service_type=DataServiceType.FILE_PROCESSOR,
            base_url="http://file-processor.activelog",
            port=8014,
            capabilities=["image_processing", "document_parsing", "video_analysis", "audio_transcription", "format_conversion"],
            priority=1,
            max_concurrent_operations=5
        )
        
        # Sync Engine
        self.services[DataServiceType.SYNC_ENGINE] = ServiceEndpoint(
            name="sync-engine",
            service_type=DataServiceType.SYNC_ENGINE,
            base_url="http://sync-engine.activelog",
            port=8020,
            capabilities=["real_time_sync", "conflict_resolution", "delta_sync", "offline_queue"],
            priority=1,
            max_concurrent_operations=20
        )
        
        # Sync V2
        self.services[DataServiceType.SYNC_V2] = ServiceEndpoint(
            name="sync-v2",
            service_type=DataServiceType.SYNC_V2,
            base_url="http://sync-v2.activelog",
            port=8021,
            capabilities=["collaborative_sync", "selective_sync", "bandwidth_aware", "conflict_resolution"],
            priority=1,
            max_concurrent_operations=15
        )
        
        # File Sync
        self.services[DataServiceType.FILE_SYNC] = ServiceEndpoint(
            name="file-sync",
            service_type=DataServiceType.FILE_SYNC,
            base_url="http://file-sync.activelog",
            port=8022,
            capabilities=["file_synchronization", "version_control", "backup_sync"],
            priority=2,
            max_concurrent_operations=10
        )
        
        # P2P Sync
        self.services[DataServiceType.P2P_SYNC] = ServiceEndpoint(
            name="p2p-sync",
            service_type=DataServiceType.P2P_SYNC,
            base_url="http://p2p-sync.activelog",
            port=8023,
            capabilities=["peer_discovery", "distributed_sync", "mesh_networking", "encryption"],
            priority=3,
            max_concurrent_operations=8
        )
        
        # File Watcher
        self.services[DataServiceType.FILE_WATCHER] = ServiceEndpoint(
            name="file-watcher",
            service_type=DataServiceType.FILE_WATCHER,
            base_url="http://file-watcher.activelog",
            port=8024,
            capabilities=["file_monitoring", "change_detection", "auto_import", "pattern_matching"],
            priority=2,
            max_concurrent_operations=5
        )

    async def register_operation(self, service: str, operation_type: str, 
                                source: str, target: Optional[str] = None,
                                metadata: Dict[str, Any] = None) -> str:
        """Register a new data operation"""
        
        operation_id = str(uuid.uuid4())
        operation = DataOperation(
            operation_id=operation_id,
            service=service,
            operation_type=operation_type,
            source=source,
            target=target,
            metadata=metadata or {},
            status="pending",
            started_at=datetime.utcnow().isoformat()
        )
        
        # Add to operations queue
        self.operations_queue.append(operation)
        
        # Process immediately if service is available
        service_endpoint = self._get_service_by_name(service)
        if service_endpoint and self._can_accept_operation(service_endpoint):
            await self._process_operation(operation)
        
        return operation_id

    def _get_service_by_name(self, service_name: str) -> Optional[ServiceEndpoint]:
        """Get service endpoint by name"""
        for service_type, endpoint in self.services.items():
            if endpoint.name == service_name:
                return endpoint
        return None

    def _can_accept_operation(self, service: ServiceEndpoint) -> bool:
        """Check if service can accept new operations"""
        active_count = len([op for op in self.active_operations.values() 
                           if op.service == service.name])
        return active_count < service.max_concurrent_operations

    async def _process_operation(self, operation: DataOperation):
        """Process a data operation"""
        try:
            # Move to active operations
            self.active_operations[operation.operation_id] = operation
            operation.status = "processing"
            operation.started_at = datetime.utcnow().isoformat()
            
            # Route to appropriate service
            result = await self._route_operation(operation)
            
            # Update operation status
            if result.get("success", False):
                operation.status = "completed"
                operation.progress = 100.0
                operation.completed_at = datetime.utcnow().isoformat()
                
                # Notify data-manager of completion
                await self._notify_data_manager(operation, result)
                
            else:
                operation.status = "failed"
                operation.error = result.get("error", "Unknown error")
            
            # Move to completed operations
            self.completed_operations[operation.operation_id] = operation
            del self.active_operations[operation.operation_id]
            
        except Exception as e:
            logger.error(f"Operation {operation.operation_id} failed: {e}")
            operation.status = "failed"
            operation.error = str(e)
            operation.completed_at = datetime.utcnow().isoformat()
            
            # Move to completed operations
            if operation.operation_id in self.active_operations:
                self.completed_operations[operation.operation_id] = operation
                del self.active_operations[operation.operation_id]

    async def _route_operation(self, operation: DataOperation) -> Dict[str, Any]:
        """Route operation to appropriate service"""
        
        service = self._get_service_by_name(operation.service)
        if not service:
            return {"success": False, "error": f"Service {operation.service} not found"}
        
        # Build endpoint URL based on operation type
        endpoint_map = {
            # Data Export endpoints
            "export_json": "/export/json",
            "export_csv": "/export/csv",
            "export_xml": "/export/xml",
            "export_pdf": "/export/pdf",
            "bulk_export": "/export/bulk",
            
            # Batch Import endpoints
            "batch_upload": "/import/batch",
            "csv_import": "/import/csv",
            "json_import": "/import/json",
            "file_validation": "/validate",
            
            # Metadata endpoints
            "extract_metadata": "/metadata/extract",
            "index_content": "/index",
            "search": "/search",
            "tag_management": "/tags",
            
            # File Processor endpoints
            "image_processing": "/process/image",
            "document_parsing": "/process/document",
            "video_analysis": "/process/video",
            "audio_transcription": "/process/audio",
            "format_conversion": "/convert",
            
            # Sync endpoints
            "real_time_sync": "/sync/realtime",
            "delta_sync": "/sync/delta",
            "collaborative_sync": "/sync/collaborative",
            "file_synchronization": "/sync/files",
            "peer_discovery": "/p2p/discover",
            "distributed_sync": "/p2p/sync",
            
            # File Watcher endpoints
            "file_monitoring": "/watch",
            "change_detection": "/detect",
            "auto_import": "/auto-import"
        }
        
        endpoint = endpoint_map.get(operation.operation_type, f"/api/{operation.operation_type}")
        url = f"{service.base_url}:{service.port}{endpoint}"
        
        # Prepare request payload
        payload = {
            "operation_id": operation.operation_id,
            "source": operation.source,
            "target": operation.target,
            "metadata": operation.metadata
        }
        
        # Send request to service
        async with aiohttp.ClientSession() as session:
            try:
                timeout = aiohttp.ClientTimeout(total=300)  # 5 minutes for data operations
                
                async with session.post(url, json=payload, timeout=timeout) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "success": True,
                            "service": service.name,
                            "operation_type": operation.operation_type,
                            "result": result,
                            "processed_at": datetime.utcnow().isoformat()
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "service": service.name,
                            "error": f"HTTP {response.status}: {error_text}"
                        }
                        
            except Exception as e:
                logger.error(f"Request to {service.name} failed: {e}")
                return {
                    "success": False,
                    "service": service.name,
                    "error": str(e)
                }

    async def _notify_data_manager(self, operation: DataOperation, result: Dict[str, Any]):
        """Notify data-manager of completed operation"""
        
        notification_payload = {
            "operation_id": operation.operation_id,
            "service": operation.service,
            "operation_type": operation.operation_type,
            "source": operation.source,
            "target": operation.target,
            "status": operation.status,
            "result": result,
            "completed_at": operation.completed_at
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                url = f"{self.data_manager_url}/notifications/operation-completed"
                timeout = aiohttp.ClientTimeout(total=10)
                
                async with session.post(url, json=notification_payload, timeout=timeout) as response:
                    if response.status == 200:
                        logger.info(f"Data-manager notified of operation {operation.operation_id}")
                    else:
                        logger.warning(f"Failed to notify data-manager: {response.status}")
                        
            except Exception as e:
                logger.error(f"Failed to notify data-manager: {e}")

    async def batch_import_files(self, user_id: str, file_paths: List[str], 
                                import_config: Dict[str, Any] = None) -> List[str]:
        """Batch import multiple files"""
        
        import_operations = []
        
        for file_path in file_paths:
            # Determine file type and appropriate processor
            file_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
            
            metadata = {
                "user_id": user_id,
                "file_path": file_path,
                "file_type": file_type,
                "import_config": import_config or {},
                "batch_import": True
            }
            
            operation_id = await self.register_operation(
                service="batch-import",
                operation_type="batch_upload",
                source=file_path,
                metadata=metadata
            )
            
            import_operations.append(operation_id)
        
        return import_operations

    async def sync_data_across_services(self, sync_config: Dict[str, Any]) -> List[str]:
        """Synchronize data across multiple sync services"""
        
        sync_operations = []
        sync_type = sync_config.get("type", "real_time_sync")
        source_service = sync_config.get("source")
        target_services = sync_config.get("targets", [])
        
        for target in target_services:
            metadata = {
                "sync_config": sync_config,
                "source_service": source_service,
                "target_service": target,
                "sync_type": sync_type
            }
            
            # Determine best sync service based on requirements
            if sync_config.get("collaborative", False):
                service = "sync-v2"
                operation_type = "collaborative_sync"
            elif sync_config.get("p2p", False):
                service = "p2p-sync"
                operation_type = "distributed_sync"
            else:
                service = "sync-engine"
                operation_type = sync_type
            
            operation_id = await self.register_operation(
                service=service,
                operation_type=operation_type,
                source=source_service,
                target=target,
                metadata=metadata
            )
            
            sync_operations.append(operation_id)
        
        return sync_operations

    async def process_media_files(self, user_id: str, media_files: List[Dict[str, Any]]) -> List[str]:
        """Process multiple media files (images, videos, audio)"""
        
        processing_operations = []
        
        for media_file in media_files:
            file_path = media_file.get("path")
            file_type = media_file.get("type", "")
            processing_options = media_file.get("options", {})
            
            # Determine processing type based on file type
            if file_type.startswith("image/"):
                operation_type = "image_processing"
            elif file_type.startswith("video/"):
                operation_type = "video_analysis"
            elif file_type.startswith("audio/"):
                operation_type = "audio_transcription"
            else:
                operation_type = "format_conversion"
            
            metadata = {
                "user_id": user_id,
                "file_type": file_type,
                "processing_options": processing_options,
                "batch_processing": len(media_files) > 1
            }
            
            operation_id = await self.register_operation(
                service="file-processor",
                operation_type=operation_type,
                source=file_path,
                metadata=metadata
            )
            
            processing_operations.append(operation_id)
        
        return processing_operations

    async def export_user_data(self, user_id: str, export_format: str, 
                              data_types: List[str] = None) -> str:
        """Export user data in specified format"""
        
        export_metadata = {
            "user_id": user_id,
            "export_format": export_format,
            "data_types": data_types or ["all"],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        operation_type = f"export_{export_format.lower()}"
        if operation_type not in ["export_json", "export_csv", "export_xml", "export_pdf"]:
            operation_type = "bulk_export"
        
        operation_id = await self.register_operation(
            service="data-export",
            operation_type=operation_type,
            source=f"user:{user_id}",
            metadata=export_metadata
        )
        
        return operation_id

    async def get_operation_status(self, operation_id: str) -> Dict[str, Any]:
        """Get status of a specific operation"""
        
        # Check active operations
        if operation_id in self.active_operations:
            operation = self.active_operations[operation_id]
            return {
                "operation_id": operation.operation_id,
                "service": operation.service,
                "operation_type": operation.operation_type,
                "status": operation.status,
                "progress": operation.progress,
                "started_at": operation.started_at,
                "error": operation.error
            }
        
        # Check completed operations
        if operation_id in self.completed_operations:
            operation = self.completed_operations[operation_id]
            return {
                "operation_id": operation.operation_id,
                "service": operation.service,
                "operation_type": operation.operation_type,
                "status": operation.status,
                "progress": operation.progress,
                "started_at": operation.started_at,
                "completed_at": operation.completed_at,
                "error": operation.error
            }
        
        # Check queue
        for operation in self.operations_queue:
            if operation.operation_id == operation_id:
                return {
                    "operation_id": operation.operation_id,
                    "service": operation.service,
                    "operation_type": operation.operation_type,
                    "status": "queued",
                    "progress": 0.0,
                    "queue_position": self.operations_queue.index(operation)
                }
        
        return {"error": "Operation not found"}

    async def get_services_health(self) -> Dict[str, Any]:
        """Check health of all data services"""
        
        health_results = {}
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for service_type, service in self.services.items():
                tasks.append(self._check_service_health(session, service))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                service = list(self.services.values())[i]
                if isinstance(result, Exception):
                    health_results[service.name] = {
                        "status": "unhealthy",
                        "error": str(result),
                        "checked_at": datetime.utcnow().isoformat()
                    }
                else:
                    health_results[service.name] = result

        # Update service health cache
        self.service_health = health_results
        
        return health_results

    async def _check_service_health(self, session: aiohttp.ClientSession, 
                                   service: ServiceEndpoint) -> Dict[str, Any]:
        """Check health of individual service"""
        try:
            health_url = f"{service.base_url}:{service.port}{service.health_endpoint}"
            timeout = aiohttp.ClientTimeout(total=5)
            
            async with session.get(health_url, timeout=timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "status": "healthy",
                        "response_time": response.headers.get("X-Response-Time"),
                        "capabilities": service.capabilities,
                        "active_operations": len([op for op in self.active_operations.values() 
                                                if op.service == service.name]),
                        "max_operations": service.max_concurrent_operations,
                        "data": data,
                        "checked_at": datetime.utcnow().isoformat()
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "http_status": response.status,
                        "checked_at": datetime.utcnow().isoformat()
                    }
                    
        except Exception as e:
            return {
                "status": "unreachable",
                "error": str(e),
                "checked_at": datetime.utcnow().isoformat()
            }

    async def get_hub_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the data services hub"""
        
        return {
            "services": {
                "total": len(self.services),
                "healthy": len([s for s in self.service_health.values() 
                              if s.get("status") == "healthy"]),
                "capabilities": sum(len(s.capabilities or []) for s in self.services.values())
            },
            "operations": {
                "queued": len(self.operations_queue),
                "active": len(self.active_operations),
                "completed": len(self.completed_operations),
                "total_processed": len(self.active_operations) + len(self.completed_operations)
            },
            "service_load": {
                service.name: {
                    "active": len([op for op in self.active_operations.values() 
                                 if op.service == service.name]),
                    "capacity": service.max_concurrent_operations,
                    "utilization": len([op for op in self.active_operations.values() 
                                      if op.service == service.name]) / service.max_concurrent_operations * 100
                }
                for service in self.services.values()
            },
            "generated_at": datetime.utcnow().isoformat()
        }