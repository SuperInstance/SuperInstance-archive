#!/usr/bin/env python3
"""
Unified Generative Gateway - Central Nervous System of Building Bots Network

This gateway orchestrates all specialized construction bots to deliver integrated,
high-quality solutions that embody the network's mission of construction excellence.

The gateway serves as:
- Central orchestration of all generative services
- Intelligent routing and load balancing
- Cross-service optimization and learning
- Multi-modal generation workflows
- Quality assurance across all outputs
- Resource allocation and optimization
- Building Bots Network mission coordination
"""

import asyncio
import logging
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import statistics
from collections import defaultdict, deque
import aiohttp
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
import sqlite3
import threading
from pathlib import Path
import psutil
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Building Bots Network Service Configuration
BBN_SERVICES = {
    "generative_tools_hub": {
        "url": "http://localhost:8500",
        "port": 8500,
        "description": "Comprehensive AI generation suite",
        "capabilities": ["text", "image", "audio", "video", "code", "document"],
        "priority": 10,
        "health_endpoint": "/health",
        "startup_command": "cd /home/activeloguser/activelog/services/generative-tools-hub && python main.py",
        "building_specialty": "multi_modal_generation"
    },
    "image_generation_service": {
        "url": "http://localhost:8480",
        "port": 8480,
        "description": "Specialized image generation and processing",
        "capabilities": ["image_generation", "image_editing", "visual_enhancement"],
        "priority": 9,
        "health_endpoint": "/health",
        "startup_command": "cd /home/activeloguser/activelog/services/image-generation-service && python main.py",
        "building_specialty": "visual_construction"
    },
    "audio_generation_service": {
        "url": "http://localhost:8481",
        "port": 8481,
        "description": "Audio generation and processing",
        "capabilities": ["audio_generation", "speech_synthesis", "audio_processing"],
        "priority": 8,
        "health_endpoint": "/health",
        "startup_command": "cd /home/activeloguser/activelog/services/audio-generation-service && python main.py 8481",
        "building_specialty": "audio_construction"
    },
    "video_generation_service": {
        "url": "http://localhost:8483",
        "port": 8483,
        "description": "Video generation and editing",
        "capabilities": ["video_generation", "video_editing", "animation"],
        "priority": 8,
        "health_endpoint": "/health",
        "startup_command": "cd /home/activeloguser/activelog/services/video-generation-service && python main.py",
        "building_specialty": "video_construction"
    },
    "code_generation_service": {
        "url": "http://localhost:8482",
        "port": 8482,
        "description": "Code generation and development",
        "capabilities": ["code_generation", "code_review", "architecture_design"],
        "priority": 9,
        "health_endpoint": "/health",
        "startup_command": "cd /home/activeloguser/activelog/services/code-generation-service && python main.py",
        "building_specialty": "code_construction"
    },
    "ai_picker_system": {
        "url": "http://localhost:8470",
        "port": 8470,
        "description": "Intelligent AI model selection and optimization",
        "capabilities": ["model_selection", "prompt_optimization", "performance_prediction"],
        "priority": 10,
        "health_endpoint": "/health",
        "startup_command": "cd /home/activeloguser/activelog/services/ai-picker-system && python main.py",
        "building_specialty": "intelligence_optimization"
    },
    "data_lifecycle_manager": {
        "url": "http://localhost:8490",
        "port": 8490,
        "description": "Data management and ML optimization",
        "capabilities": ["data_management", "ml_optimization", "analytics"],
        "priority": 8,
        "health_endpoint": "/health",
        "startup_command": "cd /home/activeloguser/activelog/services/data-lifecycle-manager && python main.py",
        "building_specialty": "data_construction"
    },
    "openai_integration": {
        "url": "http://localhost:8475",
        "port": 8475,
        "description": "OpenAI API integration and optimization",
        "capabilities": ["openai_models", "gpt_completion", "dalle_generation"],
        "priority": 9,
        "health_endpoint": "/health",
        "startup_command": "cd /home/activeloguser/activelog/services/openai-integration && python main.py",
        "building_specialty": "ai_integration"
    },
    "claude_task_hierarchy": {
        "url": "http://localhost:8474",
        "port": 8474,
        "description": "Claude-based task management and delegation",
        "capabilities": ["task_delegation", "claude_integration", "intelligent_routing"],
        "priority": 9,
        "health_endpoint": "/health",
        "startup_command": "cd /home/activeloguser/activelog/services/claude-task-hierarchy && python main.py",
        "building_specialty": "task_construction"
    },
    "hierarchical_task_system": {
        "url": "http://localhost:8471",
        "port": 8471,
        "description": "Advanced hierarchical task processing",
        "capabilities": ["task_hierarchy", "delegation_control", "prompt_optimization"],
        "priority": 8,
        "health_endpoint": "/health",
        "startup_command": "cd /home/activeloguser/activelog/services/hierarchical-task-system && python main.py",
        "building_specialty": "system_construction"
    }
}

class ProjectType(Enum):
    CONSTRUCTION_BLUEPRINT = "construction_blueprint"
    ARCHITECTURAL_DESIGN = "architectural_design"
    INFRASTRUCTURE_PLANNING = "infrastructure_planning"
    SMART_BUILDING = "smart_building"
    SUSTAINABLE_CONSTRUCTION = "sustainable_construction"
    INDUSTRIAL_FACILITY = "industrial_facility"
    RESIDENTIAL_COMPLEX = "residential_complex"
    COMMERCIAL_BUILDING = "commercial_building"
    RENOVATION_PROJECT = "renovation_project"
    LANDSCAPE_DESIGN = "landscape_design"

class QualityTier(Enum):
    DRAFT = "draft"
    STANDARD = "standard"
    HIGH = "high"
    PROFESSIONAL = "professional"
    EXCELLENCE = "excellence"

@dataclass
class BuildingRequest:
    """Request for Building Bots Network construction project"""
    project_id: str
    user_id: str
    project_type: ProjectType
    description: str
    requirements: Dict[str, Any]
    quality_tier: QualityTier
    budget_limit: Optional[float] = None
    timeline: Optional[str] = None
    deliverables: List[str] = None
    preferences: Dict[str, Any] = None
    timestamp: datetime = None

@dataclass
class ServiceResponse:
    """Response from a specialized construction service"""
    service_name: str
    success: bool
    content: Any
    metadata: Dict[str, Any]
    quality_score: float
    cost: float
    time_taken: float
    building_specialty: str

@dataclass
class OrchestrationPlan:
    """Plan for orchestrating multiple services for a project"""
    project_id: str
    services_sequence: List[str]
    parallel_services: List[List[str]]
    estimated_cost: float
    estimated_time: float
    quality_prediction: float
    resource_requirements: Dict[str, Any]
    building_phases: List[str]

class UnifiedGenerativeGateway:
    """Central orchestration engine for Building Bots Network"""
    
    def __init__(self):
        self.services = BBN_SERVICES.copy()
        self.service_health = {}
        self.service_performance = defaultdict(list)
        self.active_projects = {}
        self.project_history = []
        self.resource_monitor = ResourceMonitor()
        self.quality_assurance = QualityAssurance()
        self.load_balancer = IntelligentLoadBalancer()
        self.network_coordinator = BuildingBotsNetworkCoordinator()
        
        # Initialize database
        self.db_path = "/home/activeloguser/activelog/services/unified-generative-gateway/gateway.db"
        self._init_database()
        
        # Performance tracking
        self.metrics = {
            "total_projects": 0,
            "successful_projects": 0,
            "average_satisfaction": 0.0,
            "service_utilization": defaultdict(int),
            "resource_efficiency": 0.0
        }
        
    def _init_database(self):
        """Initialize SQLite database for gateway operations"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Projects table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                project_type TEXT NOT NULL,
                description TEXT NOT NULL,
                requirements TEXT,
                quality_tier TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME,
                final_quality_score REAL,
                total_cost REAL,
                user_satisfaction REAL
            )
        ''')
        
        # Service executions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS service_executions (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                service_name TEXT NOT NULL,
                input_data TEXT,
                output_data TEXT,
                success BOOLEAN NOT NULL,
                quality_score REAL,
                cost REAL,
                time_taken REAL,
                executed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects (id)
            )
        ''')
        
        # Service health logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS service_health_logs (
                id TEXT PRIMARY KEY,
                service_name TEXT NOT NULL,
                status TEXT NOT NULL,
                response_time REAL,
                error_message TEXT,
                checked_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Network performance metrics
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS network_metrics (
                id TEXT PRIMARY KEY,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                service_name TEXT,
                recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def orchestrate_project(self, building_request: BuildingRequest) -> Dict[str, Any]:
        """Orchestrate a complete construction project using specialized bots"""
        
        logger.info(f"🏗️ Starting Building Bots Network project: {building_request.project_id}")
        
        # Store project in database
        await self._store_project(building_request)
        
        # Create orchestration plan
        orchestration_plan = await self._create_orchestration_plan(building_request)
        
        # Execute orchestration plan
        results = await self._execute_orchestration_plan(orchestration_plan, building_request)
        
        # Quality assurance
        quality_report = await self.quality_assurance.assess_project(results, building_request)
        
        # Finalize project
        final_result = await self._finalize_project(
            building_request, 
            results, 
            quality_report,
            orchestration_plan
        )
        
        logger.info(f"✅ Completed Building Bots Network project: {building_request.project_id}")
        
        return final_result
    
    async def _create_orchestration_plan(self, request: BuildingRequest) -> OrchestrationPlan:
        """Create intelligent orchestration plan based on project requirements"""
        
        # Analyze project requirements
        required_capabilities = self._analyze_project_requirements(request)
        
        # Select optimal services
        selected_services = await self._select_optimal_services(required_capabilities, request)
        
        # Create execution sequence
        services_sequence, parallel_groups = self._plan_execution_sequence(selected_services, request)
        
        # Estimate resources and time
        estimated_cost, estimated_time = await self._estimate_project_resources(
            services_sequence, parallel_groups, request
        )
        
        # Predict quality
        quality_prediction = await self._predict_project_quality(
            selected_services, request
        )
        
        # Define building phases
        building_phases = self._define_building_phases(request.project_type, services_sequence)
        
        return OrchestrationPlan(
            project_id=request.project_id,
            services_sequence=services_sequence,
            parallel_services=parallel_groups,
            estimated_cost=estimated_cost,
            estimated_time=estimated_time,
            quality_prediction=quality_prediction,
            resource_requirements={"cpu": 0.8, "memory": 4096, "storage": 1024},
            building_phases=building_phases
        )
    
    def _analyze_project_requirements(self, request: BuildingRequest) -> List[str]:
        """Analyze project requirements to determine needed capabilities"""
        
        project_capability_mapping = {
            ProjectType.CONSTRUCTION_BLUEPRINT: [
                "image_generation", "code_generation", "document_generation", "technical_writing"
            ],
            ProjectType.ARCHITECTURAL_DESIGN: [
                "image_generation", "video_generation", "3d_modeling", "technical_analysis"
            ],
            ProjectType.SMART_BUILDING: [
                "code_generation", "system_architecture", "iot_integration", "data_analysis"
            ],
            ProjectType.SUSTAINABLE_CONSTRUCTION: [
                "environmental_analysis", "material_optimization", "energy_modeling", "reporting"
            ],
            ProjectType.RESIDENTIAL_COMPLEX: [
                "architectural_design", "landscape_design", "utility_planning", "visualization"
            ]
        }
        
        base_capabilities = project_capability_mapping.get(
            request.project_type, 
            ["text_generation", "image_generation", "analysis"]
        )
        
        # Add capabilities based on deliverables
        if request.deliverables:
            for deliverable in request.deliverables:
                if "video" in deliverable.lower():
                    base_capabilities.append("video_generation")
                if "audio" in deliverable.lower() or "presentation" in deliverable.lower():
                    base_capabilities.append("audio_generation")
                if "code" in deliverable.lower() or "software" in deliverable.lower():
                    base_capabilities.append("code_generation")
                if "3d" in deliverable.lower() or "model" in deliverable.lower():
                    base_capabilities.append("3d_modeling")
        
        # Quality tier adjustments
        if request.quality_tier in [QualityTier.PROFESSIONAL, QualityTier.EXCELLENCE]:
            base_capabilities.extend(["quality_assurance", "advanced_optimization"])
        
        return list(set(base_capabilities))
    
    async def _select_optimal_services(self, required_capabilities: List[str], 
                                      request: BuildingRequest) -> Dict[str, Any]:
        """Select optimal services based on capabilities and current performance"""
        
        selected_services = {}
        
        for capability in required_capabilities:
            # Find services that provide this capability
            candidate_services = []
            
            for service_name, service_config in self.services.items():
                if any(cap in service_config["capabilities"] for cap in [capability]):
                    # Check service health and performance
                    health_score = await self._get_service_health_score(service_name)
                    performance_score = self._get_service_performance_score(service_name)
                    
                    total_score = (health_score * 0.6) + (performance_score * 0.4)
                    
                    candidate_services.append({
                        "name": service_name,
                        "config": service_config,
                        "score": total_score,
                        "capability_match": capability
                    })
            
            # Select best service for this capability
            if candidate_services:
                best_service = max(candidate_services, key=lambda x: x["score"])
                selected_services[capability] = best_service
        
        return selected_services
    
    def _plan_execution_sequence(self, selected_services: Dict[str, Any], 
                                request: BuildingRequest) -> Tuple[List[str], List[List[str]]]:
        """Plan the sequence of service execution including parallelizable operations"""
        
        # Define dependency relationships for construction projects
        dependencies = {
            "requirements_analysis": [],
            "architectural_design": ["requirements_analysis"],
            "structural_engineering": ["architectural_design"],
            "system_design": ["architectural_design"],
            "visualization": ["architectural_design", "structural_engineering"],
            "documentation": ["structural_engineering", "system_design"],
            "quality_review": ["visualization", "documentation"]
        }
        
        # Map capabilities to construction phases
        capability_to_phase = {
            "text_generation": "requirements_analysis",
            "image_generation": "visualization",
            "video_generation": "visualization",
            "code_generation": "system_design",
            "technical_writing": "documentation",
            "analysis": "quality_review"
        }
        
        # Create execution plan
        phases = []
        parallel_groups = []
        
        # Determine phases needed for this project
        needed_phases = set()
        for capability in selected_services.keys():
            phase = capability_to_phase.get(capability, "implementation")
            needed_phases.add(phase)
        
        # Sort phases by dependencies
        sorted_phases = self._topological_sort(needed_phases, dependencies)
        
        # Group phases that can run in parallel
        current_parallel_group = []
        for phase in sorted_phases:
            # Check if this phase depends on any phase in current group
            can_parallelize = True
            for existing_phase in current_parallel_group:
                if phase in dependencies and existing_phase in dependencies[phase]:
                    can_parallelize = False
                    break
            
            if can_parallelize and len(current_parallel_group) < 3:  # Max 3 parallel services
                current_parallel_group.append(phase)
            else:
                if current_parallel_group:
                    parallel_groups.append(current_parallel_group.copy())
                current_parallel_group = [phase]
        
        if current_parallel_group:
            parallel_groups.append(current_parallel_group)
        
        # Convert phases back to service names
        services_sequence = []
        parallel_services = []
        
        for group in parallel_groups:
            service_group = []
            for phase in group:
                # Find service that matches this phase
                for capability, service_info in selected_services.items():
                    if capability_to_phase.get(capability) == phase:
                        service_name = service_info["name"]
                        if service_name not in services_sequence:
                            services_sequence.append(service_name)
                            service_group.append(service_name)
            if service_group:
                parallel_services.append(service_group)
        
        return services_sequence, parallel_services
    
    def _topological_sort(self, phases: set, dependencies: Dict[str, List[str]]) -> List[str]:
        """Perform topological sort on phases based on dependencies"""
        
        result = []
        visited = set()
        temp_visited = set()
        
        def visit(phase):
            if phase in temp_visited:
                return  # Circular dependency, skip
            if phase in visited:
                return
            
            temp_visited.add(phase)
            
            # Visit dependencies first
            for dep in dependencies.get(phase, []):
                if dep in phases:
                    visit(dep)
            
            temp_visited.remove(phase)
            visited.add(phase)
            result.append(phase)
        
        for phase in phases:
            if phase not in visited:
                visit(phase)
        
        return result
    
    async def _execute_orchestration_plan(self, plan: OrchestrationPlan, 
                                        request: BuildingRequest) -> Dict[str, ServiceResponse]:
        """Execute the orchestration plan with intelligent coordination"""
        
        logger.info(f"🚀 Executing orchestration plan for project {plan.project_id}")
        
        results = {}
        project_context = {
            "project_id": plan.project_id,
            "project_type": request.project_type.value,
            "quality_tier": request.quality_tier.value,
            "user_id": request.user_id
        }
        
        # Execute parallel service groups
        for i, service_group in enumerate(plan.parallel_services):
            logger.info(f"🔧 Executing Building Phase {i+1}: {', '.join(service_group)}")
            
            # Execute services in parallel
            if len(service_group) == 1:
                # Single service execution
                service_name = service_group[0]
                result = await self._execute_service(
                    service_name, 
                    request, 
                    project_context,
                    results  # Previous results as context
                )
                results[service_name] = result
            else:
                # Parallel execution
                tasks = []
                for service_name in service_group:
                    task = self._execute_service(
                        service_name, 
                        request, 
                        project_context,
                        results
                    )
                    tasks.append(task)
                
                # Wait for all parallel services to complete
                parallel_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for j, result in enumerate(parallel_results):
                    service_name = service_group[j]
                    if isinstance(result, Exception):
                        logger.error(f"❌ Service {service_name} failed: {result}")
                        results[service_name] = ServiceResponse(
                            service_name=service_name,
                            success=False,
                            content=f"Error: {result}",
                            metadata={"error": str(result)},
                            quality_score=0.0,
                            cost=0.0,
                            time_taken=0.0,
                            building_specialty="error"
                        )
                    else:
                        results[service_name] = result
        
        return results
    
    async def _execute_service(self, service_name: str, request: BuildingRequest, 
                              project_context: Dict[str, Any], 
                              previous_results: Dict[str, ServiceResponse]) -> ServiceResponse:
        """Execute a specific building bot service"""
        
        start_time = time.time()
        
        try:
            service_config = self.services[service_name]
            
            # Prepare service-specific payload
            payload = await self._prepare_service_payload(
                service_name, 
                service_config,
                request, 
                project_context, 
                previous_results
            )
            
            # Execute service call
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=300)) as session:
                endpoint = self._get_service_endpoint(service_name, service_config)
                
                async with session.post(
                    f"{service_config['url']}{endpoint}",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        result_data = await response.json()
                        
                        # Extract standardized information
                        content = result_data.get("content", result_data)
                        quality_score = result_data.get("quality_score", 8.0)
                        cost = result_data.get("cost", 0.0)
                        
                        # Store execution in database
                        await self._store_service_execution(
                            request.project_id, service_name, payload, result_data, 
                            True, quality_score, cost, response_time
                        )
                        
                        service_response = ServiceResponse(
                            service_name=service_name,
                            success=True,
                            content=content,
                            metadata=result_data.get("metadata", {}),
                            quality_score=quality_score,
                            cost=cost,
                            time_taken=response_time,
                            building_specialty=service_config["building_specialty"]
                        )
                        
                        logger.info(f"✅ Service {service_name} completed successfully (Quality: {quality_score}/10)")
                        
                        return service_response
                    
                    else:
                        error_text = await response.text()
                        raise Exception(f"HTTP {response.status}: {error_text}")
        
        except Exception as e:
            response_time = time.time() - start_time
            
            logger.error(f"❌ Service {service_name} failed: {e}")
            
            # Store failed execution
            await self._store_service_execution(
                request.project_id, service_name, payload if 'payload' in locals() else {}, 
                {"error": str(e)}, False, 0.0, 0.0, response_time
            )
            
            return ServiceResponse(
                service_name=service_name,
                success=False,
                content=f"Service execution failed: {e}",
                metadata={"error": str(e), "response_time": response_time},
                quality_score=0.0,
                cost=0.0,
                time_taken=response_time,
                building_specialty=service_config.get("building_specialty", "unknown")
            )
    
    async def _prepare_service_payload(self, service_name: str, service_config: Dict[str, Any],
                                      request: BuildingRequest, project_context: Dict[str, Any],
                                      previous_results: Dict[str, ServiceResponse]) -> Dict[str, Any]:
        """Prepare service-specific payload with context from previous results"""
        
        # Base payload
        base_payload = {
            "user_id": request.user_id,
            "project_id": request.project_id,
            "project_type": request.project_type.value,
            "description": request.description,
            "quality_tier": request.quality_tier.value,
            "requirements": request.requirements,
            "building_context": project_context
        }
        
        # Add context from previous results
        if previous_results:
            base_payload["previous_results"] = {
                name: {
                    "content": result.content,
                    "quality_score": result.quality_score,
                    "building_specialty": result.building_specialty,
                    "metadata": result.metadata
                }
                for name, result in previous_results.items()
                if result.success
            }
        
        # Service-specific payload customization
        if service_name == "generative_tools_hub":
            return {
                **base_payload,
                "prompt": f"Building Bots Network Construction Project: {request.description}",
                "generation_type": self._determine_generation_type(request),
                "quality": request.quality_tier.value,
                "context": f"Construction project of type {request.project_type.value}",
                "parameters": request.requirements
            }
        
        elif service_name == "ai_picker_system":
            return {
                **base_payload,
                "prompt": request.description,
                "context": {
                    "project_type": request.project_type.value,
                    "quality_tier": request.quality_tier.value,
                    "building_context": "construction_project",
                    **request.requirements
                }
            }
        
        elif service_name == "image_generation_service":
            return {
                **base_payload,
                "prompt": f"Professional architectural visualization for {request.project_type.value}: {request.description}",
                "style": "architectural",
                "quality": "high",
                "format": "detailed_blueprint"
            }
        
        elif service_name == "code_generation_service":
            return {
                **base_payload,
                "description": f"Generate construction management code for {request.description}",
                "language": "python",
                "framework": "fastapi",
                "complexity": "medium",
                "include_tests": True,
                "include_docs": True
            }
        
        elif service_name == "video_generation_service":
            return {
                **base_payload,
                "description": f"Create construction project visualization video for {request.description}",
                "duration": "medium",
                "style": "professional",
                "format": "mp4"
            }
        
        else:
            # Generic payload for other services
            return base_payload
    
    def _determine_generation_type(self, request: BuildingRequest) -> str:
        """Determine the primary generation type based on project requirements"""
        
        if "visual" in request.description.lower() or "blueprint" in request.description.lower():
            return "image"
        elif "documentation" in request.description.lower() or "report" in request.description.lower():
            return "document"
        elif "software" in request.description.lower() or "system" in request.description.lower():
            return "code"
        elif "presentation" in request.description.lower() or "demo" in request.description.lower():
            return "video"
        else:
            return "text"
    
    def _get_service_endpoint(self, service_name: str, service_config: Dict[str, Any]) -> str:
        """Get the appropriate endpoint for the service"""
        
        endpoint_mapping = {
            "generative_tools_hub": "/generate",
            "ai_picker_system": "/recommend",
            "image_generation_service": "/generate",
            "code_generation_service": "/generate",
            "video_generation_service": "/generate",
            "audio_generation_service": "/generate",
            "data_lifecycle_manager": "/process",
            "openai_integration": "/execute",
            "claude_task_hierarchy": "/execute",
            "hierarchical_task_system": "/execute"
        }
        
        return endpoint_mapping.get(service_name, "/execute")
    
    async def _finalize_project(self, request: BuildingRequest, 
                               results: Dict[str, ServiceResponse],
                               quality_report: Dict[str, Any],
                               orchestration_plan: OrchestrationPlan) -> Dict[str, Any]:
        """Finalize project with comprehensive results and quality assessment"""
        
        # Calculate overall metrics
        successful_services = [r for r in results.values() if r.success]
        total_cost = sum(r.cost for r in results.values())
        total_time = max(r.time_taken for r in results.values()) if results.values() else 0
        average_quality = statistics.mean([r.quality_score for r in successful_services]) if successful_services else 0
        
        # Building Bots Network specialties involved
        specialties_involved = list(set(r.building_specialty for r in results.values()))
        
        # Create comprehensive deliverables
        deliverables = {}
        for service_name, response in results.items():
            if response.success:
                deliverables[service_name] = {
                    "content": response.content,
                    "building_specialty": response.building_specialty,
                    "quality_score": response.quality_score,
                    "metadata": response.metadata
                }
        
        # Update project in database
        await self._update_project_completion(
            request.project_id, 
            average_quality, 
            total_cost, 
            len(successful_services) / len(results) if results else 0
        )
        
        # Update metrics
        self.metrics["total_projects"] += 1
        if len(successful_services) == len(results):
            self.metrics["successful_projects"] += 1
        
        success_rate = self.metrics["successful_projects"] / self.metrics["total_projects"]
        
        final_result = {
            "project_id": request.project_id,
            "status": "completed",
            "success": len(successful_services) == len(results),
            "building_bots_network": {
                "specialties_involved": specialties_involved,
                "construction_excellence": average_quality >= 8.0,
                "network_coordination_quality": quality_report.get("coordination_score", 8.5)
            },
            "deliverables": deliverables,
            "quality_metrics": {
                "overall_quality_score": average_quality,
                "quality_report": quality_report,
                "construction_standards_met": average_quality >= request.quality_tier.value * 2
            },
            "resource_metrics": {
                "total_cost": total_cost,
                "total_time": total_time,
                "cost_efficiency": orchestration_plan.estimated_cost / total_cost if total_cost > 0 else 1.0,
                "time_efficiency": orchestration_plan.estimated_time / total_time if total_time > 0 else 1.0
            },
            "network_performance": {
                "services_used": len(results),
                "services_successful": len(successful_services),
                "success_rate": len(successful_services) / len(results) if results else 0,
                "network_success_rate": success_rate
            },
            "orchestration_plan": asdict(orchestration_plan),
            "timestamp": datetime.now().isoformat()
        }
        
        # Store final result
        self.project_history.append(final_result)
        if len(self.project_history) > 1000:
            self.project_history = self.project_history[-1000:]
        
        return final_result
    
    async def check_service_health(self, service_name: str) -> Dict[str, Any]:
        """Check health of a specific building bot service"""
        
        if service_name not in self.services:
            return {"status": "unknown", "message": "Service not registered"}
        
        service_config = self.services[service_name]
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                health_url = f"{service_config['url']}{service_config.get('health_endpoint', '/health')}"
                
                start_time = time.time()
                async with session.get(health_url) as response:
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        health_data = await response.json()
                        
                        health_result = {
                            "status": "healthy",
                            "response_time": response_time,
                            "service_data": health_data,
                            "building_specialty": service_config["building_specialty"],
                            "checked_at": datetime.now().isoformat()
                        }
                        
                        # Store health check in database
                        await self._store_health_check(service_name, "healthy", response_time, None)
                        
                        return health_result
                    else:
                        error_message = f"HTTP {response.status}"
                        await self._store_health_check(service_name, "unhealthy", response_time, error_message)
                        
                        return {
                            "status": "unhealthy",
                            "response_time": response_time,
                            "error": error_message,
                            "checked_at": datetime.now().isoformat()
                        }
        
        except Exception as e:
            error_message = str(e)
            await self._store_health_check(service_name, "error", 0.0, error_message)
            
            return {
                "status": "error",
                "error": error_message,
                "checked_at": datetime.now().isoformat()
            }
    
    async def get_network_status(self) -> Dict[str, Any]:
        """Get comprehensive Building Bots Network status"""
        
        # Check all services
        service_statuses = {}
        healthy_services = 0
        
        for service_name in self.services.keys():
            status = await self.check_service_health(service_name)
            service_statuses[service_name] = status
            if status["status"] == "healthy":
                healthy_services += 1
        
        # Resource utilization
        system_resources = self.resource_monitor.get_system_resources()
        
        # Network metrics
        network_health_score = healthy_services / len(self.services) * 100
        
        return {
            "building_bots_network": {
                "total_bots": len(self.services),
                "healthy_bots": healthy_services,
                "network_health_score": network_health_score,
                "specialties_available": list(set(
                    config["building_specialty"] for config in self.services.values()
                ))
            },
            "service_statuses": service_statuses,
            "system_resources": system_resources,
            "performance_metrics": self.metrics,
            "active_projects": len(self.active_projects),
            "total_projects_completed": len(self.project_history),
            "network_coordination_active": True,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _get_service_health_score(self, service_name: str) -> float:
        """Get health score for a service"""
        health_status = await self.check_service_health(service_name)
        
        if health_status["status"] == "healthy":
            response_time = health_status.get("response_time", 1.0)
            # Score based on response time (lower is better)
            return max(0.1, 1.0 - (response_time / 10.0))
        else:
            return 0.1  # Minimal score for unhealthy services
    
    def _get_service_performance_score(self, service_name: str) -> float:
        """Get performance score based on historical data"""
        
        if service_name in self.service_performance:
            recent_scores = self.service_performance[service_name][-10:]  # Last 10 executions
            if recent_scores:
                return statistics.mean(recent_scores) / 10.0  # Normalize to 0-1
        
        return 0.5  # Default moderate score
    
    async def _estimate_project_resources(self, services_sequence: List[str], 
                                         parallel_groups: List[List[str]], 
                                         request: BuildingRequest) -> Tuple[float, float]:
        """Estimate cost and time for project execution"""
        
        # Base estimates per service type
        service_estimates = {
            "generative_tools_hub": {"cost": 0.50, "time": 30},
            "image_generation_service": {"cost": 0.75, "time": 45},
            "code_generation_service": {"cost": 0.40, "time": 60},
            "video_generation_service": {"cost": 1.20, "time": 120},
            "audio_generation_service": {"cost": 0.30, "time": 30},
            "ai_picker_system": {"cost": 0.10, "time": 5},
            "data_lifecycle_manager": {"cost": 0.20, "time": 15},
            "openai_integration": {"cost": 0.60, "time": 20},
            "claude_task_hierarchy": {"cost": 0.45, "time": 25},
            "hierarchical_task_system": {"cost": 0.35, "time": 20}
        }
        
        total_cost = 0.0
        total_time = 0.0
        
        # Calculate based on parallel execution
        for group in parallel_groups:
            group_cost = 0.0
            max_group_time = 0.0
            
            for service_name in group:
                estimates = service_estimates.get(service_name, {"cost": 0.50, "time": 30})
                group_cost += estimates["cost"]
                max_group_time = max(max_group_time, estimates["time"])
            
            total_cost += group_cost
            total_time += max_group_time  # Parallel execution
        
        # Quality tier multipliers
        quality_multipliers = {
            QualityTier.DRAFT: 0.7,
            QualityTier.STANDARD: 1.0,
            QualityTier.HIGH: 1.3,
            QualityTier.PROFESSIONAL: 1.6,
            QualityTier.EXCELLENCE: 2.0
        }
        
        multiplier = quality_multipliers.get(request.quality_tier, 1.0)
        
        return total_cost * multiplier, total_time * multiplier
    
    async def _predict_project_quality(self, selected_services: Dict[str, Any], 
                                      request: BuildingRequest) -> float:
        """Predict quality score for the project"""
        
        # Base quality scores for services
        service_quality_scores = {
            "generative_tools_hub": 8.5,
            "image_generation_service": 8.0,
            "code_generation_service": 7.8,
            "video_generation_service": 7.5,
            "audio_generation_service": 8.2,
            "ai_picker_system": 9.0,
            "data_lifecycle_manager": 8.3,
            "openai_integration": 8.1,
            "claude_task_hierarchy": 8.7,
            "hierarchical_task_system": 8.4
        }
        
        # Calculate weighted average based on service selection
        total_score = 0.0
        total_weight = 0.0
        
        for capability, service_info in selected_services.items():
            service_name = service_info["name"]
            base_score = service_quality_scores.get(service_name, 7.5)
            weight = service_info["config"]["priority"] / 10.0
            
            total_score += base_score * weight
            total_weight += weight
        
        average_quality = total_score / total_weight if total_weight > 0 else 7.5
        
        # Adjust for quality tier
        quality_adjustments = {
            QualityTier.DRAFT: -1.0,
            QualityTier.STANDARD: 0.0,
            QualityTier.HIGH: +0.5,
            QualityTier.PROFESSIONAL: +1.0,
            QualityTier.EXCELLENCE: +1.5
        }
        
        adjustment = quality_adjustments.get(request.quality_tier, 0.0)
        
        return min(10.0, max(1.0, average_quality + adjustment))
    
    def _define_building_phases(self, project_type: ProjectType, 
                               services_sequence: List[str]) -> List[str]:
        """Define construction phases based on project type"""
        
        phase_templates = {
            ProjectType.CONSTRUCTION_BLUEPRINT: [
                "Requirements Analysis",
                "Architectural Design",
                "Structural Planning", 
                "Systems Design",
                "Documentation",
                "Quality Review"
            ],
            ProjectType.SMART_BUILDING: [
                "Requirements Analysis",
                "System Architecture",
                "IoT Integration Design",
                "Software Development",
                "Testing & Validation",
                "Deployment Planning"
            ],
            ProjectType.RESIDENTIAL_COMPLEX: [
                "Site Analysis",
                "Architectural Design",
                "Landscape Planning",
                "Infrastructure Design",
                "Visualization",
                "Documentation"
            ]
        }
        
        return phase_templates.get(project_type, [
            "Planning",
            "Design", 
            "Implementation",
            "Review",
            "Finalization"
        ])
    
    # Database operations
    async def _store_project(self, request: BuildingRequest):
        """Store project in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO projects 
            (id, user_id, project_type, description, requirements, quality_tier)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            request.project_id,
            request.user_id,
            request.project_type.value,
            request.description,
            json.dumps(request.requirements),
            request.quality_tier.value
        ))
        
        conn.commit()
        conn.close()
    
    async def _store_service_execution(self, project_id: str, service_name: str,
                                      input_data: Dict, output_data: Dict,
                                      success: bool, quality_score: float,
                                      cost: float, time_taken: float):
        """Store service execution in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO service_executions
            (id, project_id, service_name, input_data, output_data, success,
             quality_score, cost, time_taken)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(uuid.uuid4()),
            project_id,
            service_name,
            json.dumps(input_data),
            json.dumps(output_data),
            success,
            quality_score,
            cost,
            time_taken
        ))
        
        conn.commit()
        conn.close()
    
    async def _store_health_check(self, service_name: str, status: str,
                                 response_time: float, error_message: Optional[str]):
        """Store health check in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO service_health_logs
            (id, service_name, status, response_time, error_message)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            str(uuid.uuid4()),
            service_name,
            status,
            response_time,
            error_message
        ))
        
        conn.commit()
        conn.close()
    
    async def _update_project_completion(self, project_id: str, quality_score: float,
                                        total_cost: float, satisfaction: float):
        """Update project completion in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE projects 
            SET status = 'completed', completed_at = CURRENT_TIMESTAMP,
                final_quality_score = ?, total_cost = ?, user_satisfaction = ?
            WHERE id = ?
        ''', (quality_score, total_cost, satisfaction, project_id))
        
        conn.commit()
        conn.close()


class ResourceMonitor:
    """Monitor system resources for optimal performance"""
    
    def get_system_resources(self) -> Dict[str, Any]:
        """Get current system resource utilization"""
        
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "network_io": {
                "bytes_sent": psutil.net_io_counters().bytes_sent,
                "bytes_recv": psutil.net_io_counters().bytes_recv
            },
            "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0],
            "timestamp": datetime.now().isoformat()
        }


class QualityAssurance:
    """Quality assurance system for Building Bots Network"""
    
    async def assess_project(self, results: Dict[str, ServiceResponse], 
                            request: BuildingRequest) -> Dict[str, Any]:
        """Assess overall project quality"""
        
        quality_metrics = {
            "service_quality_scores": {},
            "consistency_score": 0.0,
            "completeness_score": 0.0,
            "coordination_score": 0.0,
            "building_standards_compliance": 0.0
        }
        
        successful_results = [r for r in results.values() if r.success]
        
        if not successful_results:
            return quality_metrics
        
        # Individual service quality scores
        for service_name, result in results.items():
            quality_metrics["service_quality_scores"][service_name] = {
                "quality_score": result.quality_score,
                "success": result.success,
                "building_specialty": result.building_specialty
            }
        
        # Consistency across services
        quality_scores = [r.quality_score for r in successful_results]
        if quality_scores:
            std_dev = statistics.stdev(quality_scores) if len(quality_scores) > 1 else 0
            consistency_score = max(0, 10 - std_dev)  # Lower deviation = higher consistency
            quality_metrics["consistency_score"] = consistency_score
        
        # Completeness based on planned vs executed services
        total_planned = len(results)
        successful_count = len(successful_results)
        quality_metrics["completeness_score"] = (successful_count / total_planned) * 10 if total_planned > 0 else 0
        
        # Coordination score based on Building Bots Network integration
        specialties_involved = set(r.building_specialty for r in successful_results)
        specialty_diversity = len(specialties_involved)
        coordination_score = min(10, specialty_diversity * 2)  # More specialties = better coordination
        quality_metrics["coordination_score"] = coordination_score
        
        # Building standards compliance based on quality tier
        min_expected_quality = {
            QualityTier.DRAFT: 5.0,
            QualityTier.STANDARD: 6.5,
            QualityTier.HIGH: 8.0,
            QualityTier.PROFESSIONAL: 8.5,
            QualityTier.EXCELLENCE: 9.0
        }.get(request.quality_tier, 7.0)
        
        avg_quality = statistics.mean(quality_scores) if quality_scores else 0
        compliance_score = min(10, (avg_quality / min_expected_quality) * 10)
        quality_metrics["building_standards_compliance"] = compliance_score
        
        return quality_metrics


class IntelligentLoadBalancer:
    """Load balancer for optimal service distribution"""
    
    def __init__(self):
        self.service_loads = defaultdict(int)
        self.service_response_times = defaultdict(list)
    
    async def select_optimal_service_instance(self, service_name: str, 
                                            available_instances: List[str]) -> str:
        """Select optimal service instance based on current load"""
        
        if not available_instances:
            return service_name
        
        if len(available_instances) == 1:
            return available_instances[0]
        
        # Simple round-robin for now
        # In production, this would consider actual load metrics
        instance_loads = [self.service_loads[instance] for instance in available_instances]
        min_load_index = instance_loads.index(min(instance_loads))
        
        selected_instance = available_instances[min_load_index]
        self.service_loads[selected_instance] += 1
        
        return selected_instance


class BuildingBotsNetworkCoordinator:
    """Coordinates the Building Bots Network mission and objectives"""
    
    def __init__(self):
        self.network_mission = """
        Building Bots Network Mission:
        To deliver construction excellence through intelligent coordination of 
        specialized AI construction bots, ensuring high-quality, efficient, 
        and innovative building solutions.
        """
        
        self.construction_principles = [
            "Quality First: Every output meets professional construction standards",
            "Collaborative Excellence: Bots work together seamlessly",
            "Innovation-Driven: Leveraging cutting-edge AI for construction",
            "Efficiency Optimized: Maximum value with optimal resource usage",
            "User-Centric: Solutions tailored to user needs and preferences"
        ]
    
    async def coordinate_network_mission(self, project_request: BuildingRequest) -> Dict[str, Any]:
        """Coordinate network-wide mission alignment for project"""
        
        mission_alignment = {
            "mission_compatibility": self._assess_mission_compatibility(project_request),
            "construction_principles_applied": self.construction_principles,
            "network_coordination_strategy": self._develop_coordination_strategy(project_request),
            "excellence_targets": self._define_excellence_targets(project_request)
        }
        
        return mission_alignment
    
    def _assess_mission_compatibility(self, request: BuildingRequest) -> float:
        """Assess how well the request aligns with network mission"""
        
        # Construction-related keywords boost compatibility
        construction_keywords = [
            "building", "construction", "architecture", "infrastructure", 
            "design", "blueprint", "structure", "facility", "development"
        ]
        
        description_lower = request.description.lower()
        keyword_matches = sum(1 for keyword in construction_keywords if keyword in description_lower)
        
        # Base compatibility score
        compatibility = min(10.0, (keyword_matches / len(construction_keywords)) * 10 + 5.0)
        
        # Quality tier boost
        quality_boost = {
            QualityTier.DRAFT: 0.0,
            QualityTier.STANDARD: 0.5,
            QualityTier.HIGH: 1.0,
            QualityTier.PROFESSIONAL: 1.5,
            QualityTier.EXCELLENCE: 2.0
        }.get(request.quality_tier, 0.5)
        
        return min(10.0, compatibility + quality_boost)
    
    def _develop_coordination_strategy(self, request: BuildingRequest) -> List[str]:
        """Develop coordination strategy for the project"""
        
        strategies = [
            "Multi-bot collaborative workflow",
            "Quality assurance at each construction phase",
            "Resource optimization across all bots",
            "Real-time performance monitoring",
            "Adaptive execution based on intermediate results"
        ]
        
        # Add project-specific strategies
        if request.quality_tier in [QualityTier.PROFESSIONAL, QualityTier.EXCELLENCE]:
            strategies.extend([
                "Enhanced quality validation",
                "Advanced optimization algorithms",
                "Premium service tier activation"
            ])
        
        return strategies
    
    def _define_excellence_targets(self, request: BuildingRequest) -> Dict[str, float]:
        """Define excellence targets for the project"""
        
        base_targets = {
            "overall_quality_score": 8.0,
            "service_success_rate": 0.95,
            "user_satisfaction": 8.5,
            "cost_efficiency": 0.85,
            "time_efficiency": 0.90,
            "construction_standards_compliance": 9.0
        }
        
        # Adjust targets based on quality tier
        quality_multipliers = {
            QualityTier.DRAFT: 0.7,
            QualityTier.STANDARD: 1.0,
            QualityTier.HIGH: 1.15,
            QualityTier.PROFESSIONAL: 1.25,
            QualityTier.EXCELLENCE: 1.4
        }
        
        multiplier = quality_multipliers.get(request.quality_tier, 1.0)
        
        return {
            key: min(10.0, value * multiplier) 
            for key, value in base_targets.items()
        }


# FastAPI Models
class BuildingProjectRequest(BaseModel):
    user_id: str = Field(default="anonymous")
    project_type: str
    description: str
    requirements: Dict[str, Any] = Field(default_factory=dict)
    quality_tier: str = "standard"
    budget_limit: Optional[float] = None
    timeline: Optional[str] = None
    deliverables: List[str] = Field(default_factory=list)
    preferences: Dict[str, Any] = Field(default_factory=dict)

class ServiceHealthRequest(BaseModel):
    service_name: str

class NetworkStatusResponse(BaseModel):
    building_bots_network: Dict[str, Any]
    service_statuses: Dict[str, Any]
    system_resources: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    timestamp: str

# Global gateway instance
gateway = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global gateway
    
    logger.info("🏗️ Initializing Building Bots Network Unified Generative Gateway...")
    
    gateway = UnifiedGenerativeGateway()
    
    logger.info("✅ Building Bots Network Gateway initialized successfully")
    
    yield
    
    # Shutdown
    logger.info("🔧 Shutting down Building Bots Network Gateway...")

# Initialize FastAPI app
app = FastAPI(
    title="Building Bots Network - Unified Generative Gateway",
    description="Central nervous system for orchestrating all construction bots in the Building Bots Network",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Building Bots Network Gateway status"""
    return {
        "service": "Building Bots Network - Unified Generative Gateway",
        "status": "operational",
        "mission": "Construction excellence through intelligent AI coordination",
        "network_bots": len(BBN_SERVICES),
        "specialties": list(set(config["building_specialty"] for config in BBN_SERVICES.values())),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/orchestrate")
async def orchestrate_construction_project(request: BuildingProjectRequest):
    """Orchestrate a complete construction project using Building Bots Network"""
    
    try:
        # Convert request to internal format
        building_request = BuildingRequest(
            project_id=str(uuid.uuid4()),
            user_id=request.user_id,
            project_type=ProjectType(request.project_type),
            description=request.description,
            requirements=request.requirements,
            quality_tier=QualityTier(request.quality_tier),
            budget_limit=request.budget_limit,
            timeline=request.timeline,
            deliverables=request.deliverables,
            preferences=request.preferences,
            timestamp=datetime.now()
        )
        
        # Orchestrate the project
        result = await gateway.orchestrate_project(building_request)
        
        return result
    
    except Exception as e:
        logger.error(f"Error in orchestrate_construction_project: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/network-status", response_model=NetworkStatusResponse)
async def get_network_status():
    """Get comprehensive Building Bots Network status"""
    
    try:
        status = await gateway.get_network_status()
        return NetworkStatusResponse(**status)
    
    except Exception as e:
        logger.error(f"Error in get_network_status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/service-health")
async def check_service_health(request: ServiceHealthRequest):
    """Check health of specific building bot service"""
    
    try:
        health_status = await gateway.check_service_health(request.service_name)
        return health_status
    
    except Exception as e:
        logger.error(f"Error in check_service_health: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/services")
async def list_building_bots():
    """List all available building bots and their specialties"""
    
    return {
        "building_bots_network": {
            "total_bots": len(BBN_SERVICES),
            "bots": {
                name: {
                    "description": config["description"],
                    "building_specialty": config["building_specialty"],
                    "capabilities": config["capabilities"],
                    "priority": config["priority"],
                    "port": config["port"]
                }
                for name, config in BBN_SERVICES.items()
            }
        },
        "network_mission": gateway.network_coordinator.network_mission if gateway else "",
        "construction_principles": gateway.network_coordinator.construction_principles if gateway else []
    }

@app.get("/analytics")
async def get_network_analytics():
    """Get Building Bots Network analytics and performance metrics"""
    
    try:
        return {
            "network_performance": gateway.metrics,
            "project_history_summary": {
                "total_projects": len(gateway.project_history),
                "recent_projects": gateway.project_history[-5:] if gateway.project_history else []
            },
            "service_utilization": dict(gateway.metrics["service_utilization"]),
            "system_resources": gateway.resource_monitor.get_system_resources(),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error in get_network_analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Building Bots Network Gateway",
        "network_operational": True,
        "bots_registered": len(BBN_SERVICES),
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import sys
    
    # Configuration
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8600
    
    logger.info(f"🚀 Starting Building Bots Network Unified Generative Gateway on port {port}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        workers=1,
        log_level="info"
    )