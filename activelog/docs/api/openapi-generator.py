#!/usr/bin/env python3
"""
OpenAPI Specification Generator for ActiveLog Services

This script generates OpenAPI 3.0 specifications for all FastAPI services
by making requests to their /openapi.json endpoints.
"""

import asyncio
import aiohttp
import json
import yaml
import os
import sys
from pathlib import Path
from typing import Dict, List


class OpenAPIGenerator:
    def __init__(self, base_output_dir: str = "./openapi"):
        self.base_output_dir = Path(base_output_dir)
        self.base_output_dir.mkdir(exist_ok=True)
        
        # Service configuration: name -> (port, description)
        self.services = {
            "auth": (8001, "Authentication and Authorization Service"),
            "api-gateway": (8000, "API Gateway and Load Balancer"),
            "metadata": (8002, "Metadata and Search Service"),
            "analytics": (8003, "Analytics and Reporting Service"),
            "notifications": (8004, "Notifications and Alerts Service"),
            "document-ai": (8005, "Document AI Processing Service"),
            "video-pipeline": (8006, "Video Processing Pipeline"),
            "ml-pipeline": (8007, "Machine Learning Pipeline"),
            "backup": (8008, "Backup and Recovery Service"),
            "batch-import": (8009, "Batch Import Service"),
            "collaboration": (8010, "Real-time Collaboration Service"),
            "smart-folders": (8011, "Smart Folders and Organization"),
            "workflows": (8012, "Workflow Engine Service"),
            "mobile-api": (8013, "Mobile Optimized API"),
            "data-export": (8014, "Data Export and Archival Service"),
        }
        
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def fetch_openapi_spec(self, service_name: str, port: int) -> Dict:
        """Fetch OpenAPI specification from a service endpoint."""
        url = f"http://localhost:{port}/openapi.json"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    spec = await response.json()
                    print(f"✓ Fetched OpenAPI spec for {service_name}")
                    return spec
                else:
                    print(f"✗ Failed to fetch {service_name}: HTTP {response.status}")
                    return None
        except aiohttp.ClientError as e:
            print(f"✗ Connection error for {service_name}: {e}")
            return None
        except asyncio.TimeoutError:
            print(f"✗ Timeout fetching {service_name}")
            return None
    
    def enhance_openapi_spec(self, spec: Dict, service_name: str, description: str) -> Dict:
        """Enhance OpenAPI spec with additional metadata and documentation."""
        
        # Add service-specific information
        spec.setdefault("info", {}).update({
            "title": spec.get("info", {}).get("title", f"ActiveLog {service_name.title()} Service"),
            "description": description,
            "version": spec.get("info", {}).get("version", "1.0.0"),
            "contact": {
                "name": "ActiveLog Support",
                "url": "https://docs.activelog.com",
                "email": "support@activelog.com"
            },
            "license": {
                "name": "MIT",
                "url": "https://opensource.org/licenses/MIT"
            }
        })
        
        # Add servers information
        spec["servers"] = [
            {
                "url": f"http://localhost:{self.services[service_name][0]}",
                "description": "Development server"
            },
            {
                "url": f"https://api.activelog.com/{service_name}",
                "description": "Production server"
            }
        ]
        
        # Add security schemes
        spec.setdefault("components", {}).setdefault("securitySchemes", {}).update({
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT token obtained from the auth service"
            },
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "API key for service-to-service authentication"
            }
        })
        
        # Add common response schemas
        spec["components"].setdefault("schemas", {}).update({
            "Error": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "example": "error"
                    },
                    "error": {
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "example": "INVALID_REQUEST"
                            },
                            "message": {
                                "type": "string",
                                "example": "The request is invalid"
                            },
                            "details": {
                                "type": "object",
                                "additionalProperties": True
                            }
                        }
                    }
                }
            },
            "Success": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "example": "success"
                    },
                    "message": {
                        "type": "string",
                        "example": "Operation completed successfully"
                    },
                    "data": {
                        "type": "object",
                        "additionalProperties": True
                    }
                }
            },
            "Pagination": {
                "type": "object",
                "properties": {
                    "page": {
                        "type": "integer",
                        "minimum": 1,
                        "example": 1
                    },
                    "per_page": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "example": 20
                    },
                    "total": {
                        "type": "integer",
                        "minimum": 0,
                        "example": 100
                    },
                    "total_pages": {
                        "type": "integer",
                        "minimum": 0,
                        "example": 5
                    },
                    "has_next": {
                        "type": "boolean",
                        "example": True
                    },
                    "has_prev": {
                        "type": "boolean",
                        "example": False
                    }
                }
            }
        })
        
        # Add rate limiting headers to responses
        for path_data in spec.get("paths", {}).values():
            for method_data in path_data.values():
                if isinstance(method_data, dict) and "responses" in method_data:
                    for response_code, response_data in method_data["responses"].items():
                        if isinstance(response_data, dict):
                            response_data.setdefault("headers", {}).update({
                                "X-RateLimit-Limit": {
                                    "description": "Request limit per time window",
                                    "schema": {"type": "integer"}
                                },
                                "X-RateLimit-Remaining": {
                                    "description": "Remaining requests in current window",
                                    "schema": {"type": "integer"}
                                },
                                "X-RateLimit-Reset": {
                                    "description": "Time when the rate limit resets",
                                    "schema": {"type": "integer"}
                                }
                            })
        
        return spec
    
    async def generate_all_specs(self) -> Dict[str, bool]:
        """Generate OpenAPI specifications for all services."""
        results = {}
        
        print("Generating OpenAPI specifications for ActiveLog services...\n")
        
        for service_name, (port, description) in self.services.items():
            print(f"Processing {service_name}...")
            
            spec = await self.fetch_openapi_spec(service_name, port)
            
            if spec:
                # Enhance the specification
                enhanced_spec = self.enhance_openapi_spec(spec, service_name, description)
                
                # Save as JSON
                json_path = self.base_output_dir / f"{service_name}-service.json"
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(enhanced_spec, f, indent=2, ensure_ascii=False)
                
                # Save as YAML
                yaml_path = self.base_output_dir / f"{service_name}-service.yaml"
                with open(yaml_path, "w", encoding="utf-8") as f:
                    yaml.dump(enhanced_spec, f, default_flow_style=False, allow_unicode=True)
                
                results[service_name] = True
                print(f"  → Saved {json_path}")
                print(f"  → Saved {yaml_path}")
            else:
                results[service_name] = False
                print(f"  → Failed to generate spec for {service_name}")
            
            print()
        
        return results
    
    def generate_api_index(self, results: Dict[str, bool]):
        """Generate an index file listing all available API specifications."""
        
        available_specs = [name for name, success in results.items() if success]
        unavailable_specs = [name for name, success in results.items() if not success]
        
        index_content = {
            "title": "ActiveLog API Specifications",
            "version": "1.0.0",
            "description": "Collection of OpenAPI 3.0 specifications for all ActiveLog services",
            "generated_at": "2024-01-01T00:00:00Z",
            "available_services": len(available_specs),
            "total_services": len(self.services),
            "specifications": {}
        }
        
        for service_name in available_specs:
            port, description = self.services[service_name]
            index_content["specifications"][service_name] = {
                "title": f"ActiveLog {service_name.title()} Service",
                "description": description,
                "version": "1.0.0",
                "port": port,
                "specs": {
                    "json": f"{service_name}-service.json",
                    "yaml": f"{service_name}-service.yaml"
                },
                "docs": {
                    "swagger": f"http://localhost:{port}/docs",
                    "redoc": f"http://localhost:{port}/redoc"
                }
            }
        
        if unavailable_specs:
            index_content["unavailable_services"] = unavailable_specs
        
        # Save index
        index_path = self.base_output_dir / "index.json"
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index_content, f, indent=2, ensure_ascii=False)
        
        print(f"Generated API index: {index_path}")
    
    def generate_postman_collection(self, results: Dict[str, bool]):
        """Generate a Postman collection from the OpenAPI specs."""
        
        collection = {
            "info": {
                "name": "ActiveLog API Collection",
                "description": "Complete API collection for ActiveLog services",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "auth": {
                "type": "bearer",
                "bearer": [
                    {
                        "key": "token",
                        "value": "{{jwt_token}}",
                        "type": "string"
                    }
                ]
            },
            "variable": [
                {
                    "key": "base_url",
                    "value": "http://localhost",
                    "type": "string"
                },
                {
                    "key": "jwt_token",
                    "value": "",
                    "type": "string"
                }
            ],
            "item": []
        }
        
        for service_name, success in results.items():
            if success:
                port, description = self.services[service_name]
                
                service_folder = {
                    "name": service_name.title(),
                    "description": description,
                    "item": [
                        {
                            "name": "Health Check",
                            "request": {
                                "method": "GET",
                                "url": {
                                    "raw": f"{{{{base_url}}}}:{port}/health",
                                    "host": ["{{base_url}}"],
                                    "port": str(port),
                                    "path": ["health"]
                                }
                            }
                        }
                    ]
                }
                
                collection["item"].append(service_folder)
        
        # Save Postman collection
        postman_path = self.base_output_dir / "activelog-api-collection.json"
        with open(postman_path, "w", encoding="utf-8") as f:
            json.dump(collection, f, indent=2, ensure_ascii=False)
        
        print(f"Generated Postman collection: {postman_path}")


async def main():
    """Main function to generate all OpenAPI specifications."""
    
    # Check if we're in the correct directory
    if not Path("./services").exists():
        print("Error: This script should be run from the ActiveLog root directory")
        print("Make sure ./services directory exists")
        sys.exit(1)
    
    output_dir = Path(__file__).parent / "openapi"
    
    async with OpenAPIGenerator(str(output_dir)) as generator:
        # Generate all specifications
        results = await generator.generate_all_specs()
        
        # Generate supplementary files
        generator.generate_api_index(results)
        generator.generate_postman_collection(results)
        
        # Print summary
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        
        print(f"\nSummary:")
        print(f"Successfully generated: {successful}/{total} specifications")
        print(f"Output directory: {output_dir}")
        
        if successful < total:
            print(f"\nNote: Some services may not be running. Start all services with:")
            print(f"  ./start_all.sh")
            print(f"Then re-run this generator.")


if __name__ == "__main__":
    asyncio.run(main())