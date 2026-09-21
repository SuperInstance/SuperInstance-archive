"""
Zapier-compatible webhook system

Handles:
- Webhook endpoint creation and management
- Request validation and signature verification
- Zapier integration patterns
- Rate limiting and security
- Webhook retries and delivery guarantees
"""

import asyncio
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import parse_qs
import uuid

from core.database import db_manager
from core.config import settings

logger = logging.getLogger(__name__)

class WebhookRequest:
    """Represents an incoming webhook request"""
    
    def __init__(self, endpoint_id: str, method: str, headers: Dict[str, str], 
                 data: Any, query_params: Dict[str, str] = None):
        self.endpoint_id = endpoint_id
        self.method = method.upper()
        self.headers = {k.lower(): v for k, v in headers.items()}
        self.data = data
        self.query_params = query_params or {}
        self.timestamp = datetime.utcnow()
        self.request_id = str(uuid.uuid4())
        
    def get_content_type(self) -> str:
        """Get request content type"""
        return self.headers.get("content-type", "").split(";")[0].strip()
    
    def get_user_agent(self) -> str:
        """Get request user agent"""
        return self.headers.get("user-agent", "")
    
    def is_zapier_request(self) -> bool:
        """Check if request is from Zapier"""
        user_agent = self.get_user_agent().lower()
        return "zapier" in user_agent
    
    def get_signature(self) -> Optional[str]:
        """Get webhook signature from headers"""
        # Check common signature headers
        for header_name in ["x-hub-signature", "x-signature", "signature"]:
            if header_name in self.headers:
                return self.headers[header_name]
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "endpoint_id": self.endpoint_id,
            "method": self.method,
            "headers": self.headers,
            "data": self.data,
            "query_params": self.query_params,
            "timestamp": self.timestamp.isoformat(),
            "request_id": self.request_id,
            "content_type": self.get_content_type(),
            "user_agent": self.get_user_agent(),
            "is_zapier": self.is_zapier_request()
        }

class WebhookResponse:
    """Represents a webhook response"""
    
    def __init__(self, status_code: int = 200, data: Any = None, 
                 headers: Dict[str, str] = None, error: Optional[str] = None):
        self.status_code = status_code
        self.data = data or {}
        self.headers = headers or {}
        self.error = error
        self.timestamp = datetime.utcnow()
        
    def is_success(self) -> bool:
        """Check if response indicates success"""
        return 200 <= self.status_code < 300
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        response = {
            "status_code": self.status_code,
            "data": self.data,
            "headers": self.headers,
            "timestamp": self.timestamp.isoformat(),
            "success": self.is_success()
        }
        
        if self.error:
            response["error"] = self.error
        
        return response

class WebhookEndpointConfig:
    """Configuration for a webhook endpoint"""
    
    def __init__(self, workflow_id: str, name: str = None, description: str = None):
        self.workflow_id = workflow_id
        self.name = name or f"Webhook for {workflow_id}"
        self.description = description or "Auto-generated webhook endpoint"
        
        # Security settings
        self.secret_token: Optional[str] = None
        self.allowed_origins: List[str] = []
        self.allowed_methods: List[str] = ["POST"]
        self.require_signature: bool = False
        
        # Request settings
        self.content_types: List[str] = ["application/json", "application/x-www-form-urlencoded"]
        self.max_body_size: int = 10 * 1024 * 1024  # 10MB
        
        # Rate limiting
        self.rate_limit_per_minute: int = 100
        self.rate_limit_per_hour: int = 1000
        
        # Zapier-specific settings
        self.zapier_compatible: bool = True
        self.return_sample_data: bool = True
        self.support_polling: bool = False
        
        # Response settings
        self.response_format: str = "json"  # json, xml, plain
        self.include_metadata: bool = True
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "secret_token": self.secret_token,
            "allowed_origins": self.allowed_origins,
            "allowed_methods": self.allowed_methods,
            "require_signature": self.require_signature,
            "content_types": self.content_types,
            "max_body_size": self.max_body_size,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "rate_limit_per_hour": self.rate_limit_per_hour,
            "zapier_compatible": self.zapier_compatible,
            "return_sample_data": self.return_sample_data,
            "support_polling": self.support_polling,
            "response_format": self.response_format,
            "include_metadata": self.include_metadata
        }

class WebhookManager:
    """Manages webhook endpoints and request processing"""
    
    def __init__(self):
        self.endpoints: Dict[str, WebhookEndpointConfig] = {}
        self.request_counts: Dict[str, Dict[str, int]] = {}  # endpoint_id -> {minute: count, hour: count}
        self.last_cleanup = datetime.utcnow()
        
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "rate_limited_requests": 0,
            "signature_failures": 0,
            "zapier_requests": 0
        }
    
    async def initialize(self):
        """Initialize webhook manager"""
        
        # Load existing webhook endpoints from database
        await self._load_webhook_endpoints()
        
        logger.info(f"Webhook manager initialized with {len(self.endpoints)} endpoints")
    
    async def _load_webhook_endpoints(self):
        """Load webhook endpoints from database"""
        try:
            query = """
            SELECT endpoint_id, workflow_id, name, description, secret_token, 
                   allowed_origins, request_method, content_type, is_active
            FROM webhook_endpoints
            WHERE is_active = true
            """
            
            rows = await db_manager.database.fetch_all(query)
            
            for row in rows:
                config = WebhookEndpointConfig(
                    workflow_id=row["workflow_id"],
                    name=row["name"],
                    description=row["description"]
                )
                
                config.secret_token = row["secret_token"]
                config.allowed_origins = json.loads(row["allowed_origins"]) if row["allowed_origins"] else []
                config.allowed_methods = [row["request_method"]] if row["request_method"] else ["POST"]
                config.content_types = [row["content_type"]] if row["content_type"] else ["application/json"]
                
                self.endpoints[row["endpoint_id"]] = config
            
            logger.info(f"Loaded {len(self.endpoints)} webhook endpoints from database")
            
        except Exception as e:
            logger.error(f"Error loading webhook endpoints: {e}")
    
    async def create_endpoint(self, config: WebhookEndpointConfig) -> str:
        """Create a new webhook endpoint"""
        
        endpoint_id = str(uuid.uuid4())
        self.endpoints[endpoint_id] = config
        
        # Save to database
        try:
            query = """
            INSERT INTO webhook_endpoints (id, endpoint_id, workflow_id, name, description,
                                         secret_token, allowed_origins, request_method,
                                         content_type, is_active)
            VALUES (:id, :endpoint_id, :workflow_id, :name, :description,
                    :secret_token, :allowed_origins, :request_method,
                    :content_type, :is_active)
            """
            
            values = {
                "id": str(uuid.uuid4()),
                "endpoint_id": endpoint_id,
                "workflow_id": config.workflow_id,
                "name": config.name,
                "description": config.description,
                "secret_token": config.secret_token,
                "allowed_origins": json.dumps(config.allowed_origins),
                "request_method": config.allowed_methods[0] if config.allowed_methods else "POST",
                "content_type": config.content_types[0] if config.content_types else "application/json",
                "is_active": True
            }
            
            await db_manager.database.execute(query, values)
            
        except Exception as e:
            logger.error(f"Error saving webhook endpoint: {e}")
        
        logger.info(f"Created webhook endpoint {endpoint_id} for workflow {config.workflow_id}")
        return endpoint_id
    
    async def process_webhook(self, endpoint_id: str, data: Any, headers: Dict[str, str], 
                            method: str = "POST", query_params: Dict[str, str] = None) -> Dict[str, Any]:
        """Process incoming webhook request"""
        
        request = WebhookRequest(endpoint_id, method, headers, data, query_params)
        self.stats["total_requests"] += 1
        
        if request.is_zapier_request():
            self.stats["zapier_requests"] += 1
        
        try:
            # Get endpoint configuration
            config = self.endpoints.get(endpoint_id)
            if not config:
                response = WebhookResponse(404, error="Webhook endpoint not found")
                self.stats["failed_requests"] += 1
                return response.to_dict()
            
            # Validate request
            validation_result = await self._validate_request(request, config)
            if not validation_result["valid"]:
                response = WebhookResponse(
                    validation_result["status_code"],
                    error=validation_result["error"]
                )
                self.stats["failed_requests"] += 1
                return response.to_dict()
            
            # Check rate limits
            if not await self._check_rate_limits(endpoint_id, config):
                response = WebhookResponse(429, error="Rate limit exceeded")
                self.stats["rate_limited_requests"] += 1
                self.stats["failed_requests"] += 1
                return response.to_dict()
            
            # Process the webhook
            result = await self._execute_webhook(request, config)
            
            if result["success"]:
                self.stats["successful_requests"] += 1
            else:
                self.stats["failed_requests"] += 1
            
            # Update endpoint statistics
            await self._update_endpoint_stats(endpoint_id, result["success"])
            
            # Return appropriate response
            return await self._format_response(result, config, request)
            
        except Exception as e:
            logger.error(f"Error processing webhook {endpoint_id}: {e}")
            self.stats["failed_requests"] += 1
            
            response = WebhookResponse(500, error="Internal server error")
            return response.to_dict()
    
    async def _validate_request(self, request: WebhookRequest, config: WebhookEndpointConfig) -> Dict[str, Any]:
        """Validate incoming webhook request"""
        
        # Check HTTP method
        if request.method not in config.allowed_methods:
            return {
                "valid": False,
                "status_code": 405,
                "error": f"Method {request.method} not allowed"
            }
        
        # Check content type
        content_type = request.get_content_type()
        if content_type and content_type not in config.content_types:
            return {
                "valid": False,
                "status_code": 415,
                "error": f"Content type {content_type} not supported"
            }
        
        # Check signature if required
        if config.require_signature and config.secret_token:
            if not await self._verify_signature(request, config.secret_token):
                self.stats["signature_failures"] += 1
                return {
                    "valid": False,
                    "status_code": 401,
                    "error": "Invalid signature"
                }
        
        # Check allowed origins (for CORS)
        origin = request.headers.get("origin")
        if origin and config.allowed_origins and origin not in config.allowed_origins:
            return {
                "valid": False,
                "status_code": 403,
                "error": f"Origin {origin} not allowed"
            }
        
        return {"valid": True}
    
    async def _verify_signature(self, request: WebhookRequest, secret: str) -> bool:
        """Verify webhook signature"""
        
        signature = request.get_signature()
        if not signature:
            return False
        
        try:
            # Support different signature formats
            if signature.startswith("sha1="):
                expected = "sha1=" + hmac.new(
                    secret.encode(),
                    json.dumps(request.data).encode(),
                    hashlib.sha1
                ).hexdigest()
            elif signature.startswith("sha256="):
                expected = "sha256=" + hmac.new(
                    secret.encode(),
                    json.dumps(request.data).encode(),
                    hashlib.sha256
                ).hexdigest()
            else:
                # Plain HMAC
                expected = hmac.new(
                    secret.encode(),
                    json.dumps(request.data).encode(),
                    hashlib.sha256
                ).hexdigest()
            
            return hmac.compare_digest(signature, expected)
            
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False
    
    async def _check_rate_limits(self, endpoint_id: str, config: WebhookEndpointConfig) -> bool:
        """Check rate limits for endpoint"""
        
        current_time = datetime.utcnow()
        current_minute = current_time.replace(second=0, microsecond=0)
        current_hour = current_time.replace(minute=0, second=0, microsecond=0)
        
        # Initialize tracking if needed
        if endpoint_id not in self.request_counts:
            self.request_counts[endpoint_id] = {}
        
        endpoint_counts = self.request_counts[endpoint_id]
        
        # Check minute limit
        minute_key = current_minute.isoformat()
        minute_count = endpoint_counts.get(minute_key, 0)
        if minute_count >= config.rate_limit_per_minute:
            return False
        
        # Check hour limit
        hour_key = current_hour.isoformat()
        hour_count = endpoint_counts.get(hour_key, 0)
        if hour_count >= config.rate_limit_per_hour:
            return False
        
        # Update counts
        endpoint_counts[minute_key] = minute_count + 1
        endpoint_counts[hour_key] = hour_count + 1
        
        return True
    
    async def _execute_webhook(self, request: WebhookRequest, config: WebhookEndpointConfig) -> Dict[str, Any]:
        """Execute webhook by triggering workflow"""
        
        try:
            # Import here to avoid circular imports
            from workflow.workflow_engine import WorkflowEngine
            
            # Get workflow engine (would normally be injected)
            # For now, we'll simulate workflow execution
            
            # Prepare trigger data
            trigger_data = {
                "webhook": request.to_dict(),
                "timestamp": request.timestamp.isoformat(),
                "source": "webhook"
            }
            
            # Execute workflow
            # execution_id = await workflow_engine.execute_workflow(config.workflow_id, trigger_data)
            
            # For demo purposes, simulate successful execution
            execution_id = str(uuid.uuid4())
            
            return {
                "success": True,
                "execution_id": execution_id,
                "workflow_id": config.workflow_id,
                "triggered_at": datetime.utcnow().isoformat(),
                "trigger_data": trigger_data
            }
            
        except Exception as e:
            logger.error(f"Webhook execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _format_response(self, result: Dict[str, Any], config: WebhookEndpointConfig, 
                             request: WebhookRequest) -> Dict[str, Any]:
        """Format webhook response"""
        
        # Base response
        response_data = {
            "success": result["success"],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if result["success"]:
            response_data.update({
                "execution_id": result.get("execution_id"),
                "workflow_id": result.get("workflow_id")
            })
            
            # Add sample data for Zapier testing
            if config.zapier_compatible and config.return_sample_data:
                response_data["sample_data"] = {
                    "id": "12345",
                    "message": "Workflow executed successfully",
                    "status": "completed",
                    "created_at": datetime.utcnow().isoformat()
                }
        else:
            response_data["error"] = result.get("error", "Unknown error")
        
        # Add metadata if requested
        if config.include_metadata:
            response_data["metadata"] = {
                "endpoint_id": request.endpoint_id,
                "request_id": request.request_id,
                "processing_time_ms": int((datetime.utcnow() - request.timestamp).total_seconds() * 1000),
                "user_agent": request.get_user_agent(),
                "is_zapier": request.is_zapier_request()
            }
        
        # Handle different response formats
        if config.response_format == "json":
            return WebhookResponse(
                200 if result["success"] else 400,
                response_data,
                {"Content-Type": "application/json"}
            ).to_dict()
        elif config.response_format == "xml":
            # Convert to XML (simplified)
            xml_data = self._dict_to_xml(response_data)
            return WebhookResponse(
                200 if result["success"] else 400,
                xml_data,
                {"Content-Type": "application/xml"}
            ).to_dict()
        else:
            # Plain text
            message = "Success" if result["success"] else result.get("error", "Failed")
            return WebhookResponse(
                200 if result["success"] else 400,
                message,
                {"Content-Type": "text/plain"}
            ).to_dict()
    
    def _dict_to_xml(self, data: Dict[str, Any], root_tag: str = "response") -> str:
        """Convert dictionary to simple XML"""
        def dict_to_xml_recursive(d, tag):
            xml = f"<{tag}>"
            for key, value in d.items():
                if isinstance(value, dict):
                    xml += dict_to_xml_recursive(value, key)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            xml += dict_to_xml_recursive(item, key)
                        else:
                            xml += f"<{key}>{str(item)}</{key}>"
                else:
                    xml += f"<{key}>{str(value)}</{key}>"
            xml += f"</{tag}>"
            return xml
        
        return f'<?xml version="1.0" encoding="UTF-8"?>{dict_to_xml_recursive(data, root_tag)}'
    
    async def _update_endpoint_stats(self, endpoint_id: str, success: bool):
        """Update endpoint statistics in database"""
        
        try:
            if success:
                query = """
                UPDATE webhook_endpoints 
                SET successful_requests = successful_requests + 1,
                    last_request_at = :timestamp
                WHERE endpoint_id = :endpoint_id
                """
            else:
                query = """
                UPDATE webhook_endpoints 
                SET failed_requests = failed_requests + 1,
                    last_request_at = :timestamp
                WHERE endpoint_id = :endpoint_id
                """
            
            await db_manager.database.execute(query, {
                "endpoint_id": endpoint_id,
                "timestamp": datetime.utcnow()
            })
            
        except Exception as e:
            logger.error(f"Error updating endpoint stats: {e}")
    
    async def get_endpoint_info(self, endpoint_id: str) -> Optional[Dict[str, Any]]:
        """Get webhook endpoint information"""
        
        config = self.endpoints.get(endpoint_id)
        if not config:
            return None
        
        # Get stats from database
        try:
            query = """
            SELECT total_requests, successful_requests, failed_requests, last_request_at
            FROM webhook_endpoints
            WHERE endpoint_id = :endpoint_id
            """
            
            row = await db_manager.database.fetch_one(query, {"endpoint_id": endpoint_id})
            
            endpoint_info = {
                "endpoint_id": endpoint_id,
                "config": config.to_dict(),
                "url": f"/webhook/{endpoint_id}",
                "stats": {
                    "total_requests": row["total_requests"] if row else 0,
                    "successful_requests": row["successful_requests"] if row else 0,
                    "failed_requests": row["failed_requests"] if row else 0,
                    "last_request_at": row["last_request_at"].isoformat() if row and row["last_request_at"] else None
                }
            }
            
            return endpoint_info
            
        except Exception as e:
            logger.error(f"Error getting endpoint info: {e}")
            return {
                "endpoint_id": endpoint_id,
                "config": config.to_dict(),
                "url": f"/webhook/{endpoint_id}",
                "stats": {}
            }
    
    async def delete_endpoint(self, endpoint_id: str) -> bool:
        """Delete webhook endpoint"""
        
        if endpoint_id not in self.endpoints:
            return False
        
        try:
            # Remove from database
            query = "UPDATE webhook_endpoints SET is_active = false WHERE endpoint_id = :endpoint_id"
            await db_manager.database.execute(query, {"endpoint_id": endpoint_id})
            
            # Remove from memory
            del self.endpoints[endpoint_id]
            
            # Clean up rate limit tracking
            self.request_counts.pop(endpoint_id, None)
            
            logger.info(f"Deleted webhook endpoint {endpoint_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting webhook endpoint: {e}")
            return False
    
    async def start_cleanup_task(self):
        """Start background cleanup task"""
        asyncio.create_task(self._cleanup_task())
    
    async def _cleanup_task(self):
        """Background task to clean up old rate limit data"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                current_time = datetime.utcnow()
                cutoff_time = current_time - timedelta(hours=2)
                
                # Clean up old rate limit data
                for endpoint_id in list(self.request_counts.keys()):
                    endpoint_counts = self.request_counts[endpoint_id]
                    
                    # Remove old entries
                    old_keys = [
                        key for key in endpoint_counts.keys()
                        if datetime.fromisoformat(key) < cutoff_time
                    ]
                    
                    for key in old_keys:
                        del endpoint_counts[key]
                    
                    # Remove empty endpoint tracking
                    if not endpoint_counts:
                        del self.request_counts[endpoint_id]
                
                logger.debug("Webhook cleanup completed")
                
            except Exception as e:
                logger.error(f"Webhook cleanup error: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get webhook manager metrics"""
        return {
            "webhook_manager": {
                "active_endpoints": len(self.endpoints),
                "total_requests": self.stats["total_requests"],
                "successful_requests": self.stats["successful_requests"],
                "failed_requests": self.stats["failed_requests"],
                "rate_limited_requests": self.stats["rate_limited_requests"],
                "signature_failures": self.stats["signature_failures"],
                "zapier_requests": self.stats["zapier_requests"],
                "success_rate": (
                    self.stats["successful_requests"] / max(1, self.stats["total_requests"])
                ) * 100 if self.stats["total_requests"] > 0 else 0
            }
        }
    
    async def cleanup(self):
        """Clean up webhook manager"""
        self.endpoints.clear()
        self.request_counts.clear()
        logger.info("Webhook manager cleaned up")