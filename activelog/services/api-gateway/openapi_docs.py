"""
Enhanced OpenAPI Documentation Generator for ActiveLog API Gateway
"""

from typing import Dict, Any, List, Optional
import httpx
import asyncio
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class OpenAPIDocumentationGenerator:
    def __init__(self, gateway_url: str = "http://localhost:8088", service_configs: Dict[str, Any] = None):
        self.gateway_url = gateway_url
        self.service_configs = service_configs or {}
        self.service_to_service_key = "service-internal-key-change-in-production"
    
    async def fetch_service_openapi(self, service_name: str, service_url: str) -> Optional[Dict[str, Any]]:
        """Fetch OpenAPI schema from a service"""
        try:
            headers = {}
            service_config = self.service_configs.get(service_name, {})
            if service_config.get("service_auth", False):
                headers["X-Service-Auth"] = self.service_to_service_key
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{service_url}/openapi.json",
                    headers=headers
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"Service {service_name} returned {response.status_code} for OpenAPI schema")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to fetch OpenAPI schema from {service_name}: {e}")
            return None
    
    async def generate_unified_openapi(self) -> Dict[str, Any]:
        """Generate unified OpenAPI documentation for all services"""
        
        # Base OpenAPI schema
        unified_schema = {
            "openapi": "3.0.2",
            "info": {
                "title": "ActiveLog API Gateway - Unified Documentation",
                "version": "2.0.0",
                "description": """
# ActiveLog API Gateway - Complete API Documentation

This is the unified API documentation for all ActiveLog services accessible through the API Gateway.

## 🔐 Authentication
Most endpoints require JWT authentication. Include your token in the Authorization header:
```
Authorization: Bearer <your-jwt-token>
```

### Getting an Access Token
```bash
curl -X POST "http://localhost:8088/api/auth/login" \\
  -H "Content-Type: application/json" \\
  -d '{"username": "your-username", "password": "your-password"}'
```

## 🚦 Rate Limits
- **Viewer**: 100 requests/hour
- **User**: 500 requests/hour  
- **Admin**: 2000 requests/hour
- **Service**: 10000 requests/hour

## 🏗️ Architecture
All services are accessible via the API Gateway using the pattern:
```
/api/{service}/{endpoint}
```

## 🚀 Performance Features
- **Redis Caching**: Intelligent response caching with configurable TTL
- **Circuit Breaker**: Automatic service failure detection and recovery
- **Request Deduplication**: Efficient handling of concurrent identical requests
- **Rate Limiting**: Role-based request throttling

## 📊 Monitoring
- **Health Checks**: `/health` for gateway and service status
- **Metrics**: `/metrics` for performance and usage statistics (admin only)
- **Cache Stats**: `/cache/stats` for caching performance (admin only)

## 🛡️ Security
- JWT-based authentication with role-based access control
- Service-to-service authentication for internal communication
- Request validation and sanitization
- CORS protection
                """,
                "contact": {
                    "name": "ActiveLog Support",
                    "email": "support@activelog.ai"
                },
                "license": {
                    "name": "MIT",
                    "url": "https://opensource.org/licenses/MIT"
                }
            },
            "servers": [
                {
                    "url": "http://localhost:8088",
                    "description": "Development Gateway"
                }
            ],
            "paths": {},
            "components": {
                "securitySchemes": {
                    "bearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT",
                        "description": "JWT token obtained from /api/auth/login"
                    },
                    "serviceAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-Service-Auth",
                        "description": "Service-to-service authentication key"
                    }
                },
                "schemas": {
                    "ErrorResponse": {
                        "type": "object",
                        "properties": {
                            "error": {
                                "type": "string",
                                "description": "Error message"
                            },
                            "detail": {
                                "type": "string",
                                "description": "Detailed error information"
                            },
                            "status_code": {
                                "type": "integer",
                                "description": "HTTP status code"
                            }
                        },
                        "required": ["error"]
                    },
                    "HealthResponse": {
                        "type": "object",
                        "properties": {
                            "gateway": {
                                "type": "string",
                                "example": "healthy"
                            },
                            "timestamp": {
                                "type": "string",
                                "format": "date-time"
                            },
                            "services": {
                                "type": "object",
                                "additionalProperties": {
                                    "type": "object"
                                }
                            },
                            "redis": {
                                "type": "string",
                                "example": "healthy"
                            }
                        }
                    },
                    "MetricsResponse": {
                        "type": "object",
                        "properties": {
                            "timestamp": {
                                "type": "string",
                                "format": "date-time"
                            },
                            "request_metrics": {
                                "type": "object",
                                "additionalProperties": {
                                    "type": "object"
                                }
                            },
                            "error_metrics": {
                                "type": "object",
                                "additionalProperties": {
                                    "type": "object"
                                }
                            },
                            "cache_stats": {
                                "type": "object",
                                "properties": {
                                    "hits": {"type": "integer"},
                                    "misses": {"type": "integer"},
                                    "hit_rate": {"type": "number"},
                                    "in_memory_entries": {"type": "integer"}
                                }
                            },
                            "circuit_breaker_states": {
                                "type": "object",
                                "additionalProperties": {
                                    "type": "object",
                                    "properties": {
                                        "state": {"type": "string"},
                                        "failure_count": {"type": "integer"},
                                        "last_failure": {"type": "number", "nullable": True}
                                    }
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "BadRequest": {
                        "description": "Bad request",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        }
                    },
                    "Unauthorized": {
                        "description": "Authentication required",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        }
                    },
                    "Forbidden": {
                        "description": "Insufficient permissions",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        }
                    },
                    "NotFound": {
                        "description": "Resource not found",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        }
                    },
                    "TooManyRequests": {
                        "description": "Rate limit exceeded",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        }
                    },
                    "ServiceUnavailable": {
                        "description": "Service temporarily unavailable",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        }
                    }
                }
            },
            "security": [
                {"bearerAuth": []}
            ]
        }
        
        # Add gateway-specific endpoints
        self._add_gateway_endpoints(unified_schema)
        
        # Fetch and merge service schemas
        for service_name, service_config in self.service_configs.items():
            service_schema = await self.fetch_service_openapi(service_name, service_config["url"])
            if service_schema:
                self._merge_service_schema(unified_schema, service_name, service_schema, service_config)
        
        return unified_schema
    
    def _add_gateway_endpoints(self, schema: Dict[str, Any]):
        """Add gateway-specific endpoints to the schema"""
        gateway_paths = {
            "/": {
                "get": {
                    "tags": ["Gateway"],
                    "summary": "Gateway Information",
                    "description": "Get API Gateway information and available services",
                    "security": [],
                    "responses": {
                        "200": {
                            "description": "Gateway information",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "gateway": {"type": "string"},
                                            "version": {"type": "string"},
                                            "services": {
                                                "type": "array",
                                                "items": {"type": "string"}
                                            },
                                            "features": {
                                                "type": "array",
                                                "items": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/health": {
                "get": {
                    "tags": ["Gateway"],
                    "summary": "Health Check",
                    "description": "Get gateway and service health status",
                    "security": [],
                    "responses": {
                        "200": {
                            "description": "Health status",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/HealthResponse"}
                                }
                            }
                        }
                    }
                }
            },
            "/metrics": {
                "get": {
                    "tags": ["Gateway"],
                    "summary": "Gateway Metrics",
                    "description": "Get detailed gateway metrics (admin only)",
                    "security": [{"bearerAuth": []}],
                    "responses": {
                        "200": {
                            "description": "Gateway metrics",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/MetricsResponse"}
                                }
                            }
                        },
                        "401": {"$ref": "#/components/responses/Unauthorized"},
                        "403": {"$ref": "#/components/responses/Forbidden"}
                    }
                }
            },
            "/services": {
                "get": {
                    "tags": ["Gateway"],
                    "summary": "List Services",
                    "description": "List all available services with their status",
                    "security": [],
                    "responses": {
                        "200": {
                            "description": "Services information",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "gateway": {"type": "string"},
                                            "version": {"type": "string"},
                                            "timestamp": {"type": "string"},
                                            "services": {
                                                "type": "object",
                                                "additionalProperties": {
                                                    "type": "object",
                                                    "properties": {
                                                        "name": {"type": "string"},
                                                        "url": {"type": "string"},
                                                        "status": {"type": "string"},
                                                        "protected_paths": {
                                                            "type": "array",
                                                            "items": {"type": "string"}
                                                        },
                                                        "admin_only_paths": {
                                                            "type": "array",
                                                            "items": {"type": "string"}
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/cache/stats": {
                "get": {
                    "tags": ["Gateway", "Cache"],
                    "summary": "Cache Statistics",
                    "description": "Get cache performance statistics (admin only)",
                    "security": [{"bearerAuth": []}],
                    "responses": {
                        "200": {
                            "description": "Cache statistics",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "cache_stats": {
                                                "type": "object",
                                                "properties": {
                                                    "hits": {"type": "integer"},
                                                    "misses": {"type": "integer"},
                                                    "hit_rate": {"type": "number"},
                                                    "in_memory_entries": {"type": "integer"}
                                                }
                                            },
                                            "timestamp": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        },
                        "401": {"$ref": "#/components/responses/Unauthorized"},
                        "403": {"$ref": "#/components/responses/Forbidden"}
                    }
                }
            },
            "/cache/invalidate": {
                "post": {
                    "tags": ["Gateway", "Cache"],
                    "summary": "Invalidate Cache",
                    "description": "Invalidate cache entries matching patterns (admin only)",
                    "security": [{"bearerAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "example": ["auth", "user", "profile"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Cache invalidated",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "message": {"type": "string"},
                                            "patterns": {
                                                "type": "array",
                                                "items": {"type": "string"}
                                            },
                                            "timestamp": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        },
                        "401": {"$ref": "#/components/responses/Unauthorized"},
                        "403": {"$ref": "#/components/responses/Forbidden"}
                    }
                }
            }
        }
        
        schema["paths"].update(gateway_paths)
    
    def _merge_service_schema(self, unified_schema: Dict[str, Any], service_name: str, service_schema: Dict[str, Any], service_config: Dict[str, Any]):
        """Merge a service's OpenAPI schema into the unified schema"""
        
        # Add service paths with /api/{service} prefix
        if "paths" in service_schema:
            for path, path_info in service_schema["paths"].items():
                # Skip health endpoints (already handled by gateway)
                if path == "/health":
                    continue
                
                gateway_path = f"/api/{service_name}{path}"
                
                # Process each method in the path
                for method, method_info in path_info.items():
                    if method.lower() not in ["get", "post", "put", "delete", "patch", "options", "head"]:
                        continue
                    
                    # Add service tag
                    if "tags" not in method_info:
                        method_info["tags"] = []
                    
                    # Add service name to tags
                    service_tag = f"{service_name.title()} Service"
                    if service_tag not in method_info["tags"]:
                        method_info["tags"].insert(0, service_tag)
                    
                    # Add authentication requirements based on service config
                    original_path = path.lstrip("/")
                    if self._is_protected_path(service_config, original_path):
                        if "security" not in method_info:
                            method_info["security"] = [{"bearerAuth": []}]
                        
                        # Add common error responses for protected endpoints
                        if "responses" not in method_info:
                            method_info["responses"] = {}
                        
                        method_info["responses"].update({
                            "401": {"$ref": "#/components/responses/Unauthorized"},
                            "429": {"$ref": "#/components/responses/TooManyRequests"}
                        })
                        
                        if self._is_admin_only_path(service_config, original_path):
                            method_info["responses"]["403"] = {"$ref": "#/components/responses/Forbidden"}
                    
                    # Add service unavailable response for all endpoints
                    if "responses" not in method_info:
                        method_info["responses"] = {}
                    method_info["responses"]["503"] = {"$ref": "#/components/responses/ServiceUnavailable"}
                    
                    # Add description about gateway routing
                    if "description" in method_info:
                        method_info["description"] += f"\n\n**Gateway Route**: `{gateway_path}`\n**Direct Service**: `{service_config['url']}{path}`"
                    else:
                        method_info["description"] = f"**Gateway Route**: `{gateway_path}`\n**Direct Service**: `{service_config['url']}{path}`"
                
                unified_schema["paths"][gateway_path] = path_info
        
        # Merge components (schemas, responses, etc.)
        if "components" in service_schema:
            for component_type in ["schemas", "responses", "parameters", "examples"]:
                if component_type in service_schema["components"]:
                    if component_type not in unified_schema["components"]:
                        unified_schema["components"][component_type] = {}
                    
                    # Prefix component names with service name to avoid conflicts
                    for name, component in service_schema["components"][component_type].items():
                        prefixed_name = f"{service_name.title()}{name}"
                        unified_schema["components"][component_type][prefixed_name] = component
        
        # Update info with service details
        if "x-services" not in unified_schema["info"]:
            unified_schema["info"]["x-services"] = {}
        
        unified_schema["info"]["x-services"][service_name] = {
            "url": service_config["url"],
            "protected_paths": service_config.get("protected_paths", []),
            "admin_only_paths": service_config.get("admin_only_paths", []),
            "requires_service_auth": service_config.get("service_auth", False),
            "schema_available": True
        }
    
    def _is_protected_path(self, service_config: Dict[str, Any], path: str) -> bool:
        """Check if path requires authentication"""
        protected_paths = service_config.get("protected_paths", [])
        normalized_path = "/" + path.strip("/")
        
        for protected_path in protected_paths:
            normalized_protected = "/" + protected_path.strip("/")
            if normalized_path.startswith(normalized_protected):
                return True
        return False
    
    def _is_admin_only_path(self, service_config: Dict[str, Any], path: str) -> bool:
        """Check if path requires admin role"""
        admin_paths = service_config.get("admin_only_paths", [])
        normalized_path = "/" + path.strip("/")
        
        for admin_path in admin_paths:
            normalized_admin = "/" + admin_path.strip("/")
            if normalized_path.startswith(normalized_admin):
                return True
        return False

async def generate_documentation():
    """Generate unified documentation for all services"""
    
    # Service configurations (should match main.py)
    SERVICES = {
        "file-sync": {
            "url": "http://localhost:8000",
            "protected_paths": ["/upload", "/delete", "/sync"],
            "admin_only_paths": ["/admin"],
            "service_auth": True
        },
        "ai-orchestrator": {
            "url": "http://localhost:8001",
            "protected_paths": ["/analyze", "/plugins"],
            "admin_only_paths": ["/admin", "/plugins/manage"],
            "service_auth": True
        },
        "auth": {
            "url": "http://localhost:8002",
            "protected_paths": ["/me", "/change-password", "/logout"],
            "admin_only_paths": ["/users"],
            "service_auth": False
        },
        "metadata": {
            "url": "http://localhost:8003",
            "protected_paths": ["/metadata", "/tags", "/embeddings", "/relationships", "/batch"],
            "admin_only_paths": ["/batch"],
            "service_auth": True
        }
    }
    
    generator = OpenAPIDocumentationGenerator(
        gateway_url="http://localhost:8088",
        service_configs=SERVICES
    )
    
    unified_schema = await generator.generate_unified_openapi()
    return unified_schema

if __name__ == "__main__":
    async def main():
        schema = await generate_documentation()
        print(json.dumps(schema, indent=2))
    
    asyncio.run(main())