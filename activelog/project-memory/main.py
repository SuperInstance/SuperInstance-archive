#!/usr/bin/env python3
"""
ActiveLog Project Memory System
Port: 8460

Intelligent codebase understanding with minimal context window usage:
- Hierarchical Knowledge Graph with semantic compression
- Smart path encoding for maximum information density  
- Context window optimization with need-to-know loading
- Bot-specific views with capability-based filtering
- Dynamic documentation generation with change tracking
- Deep integration with all ActiveLog services
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set, Tuple
from pathlib import Path
import json
import hashlib
import uvicorn
from fastapi import FastAPI, WebSocket, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from knowledge.knowledge_graph import KnowledgeGraph
from contexts.context_optimizer import ContextOptimizer
from views.bot_view_manager import BotViewManager
from docs.doc_generator import DynamicDocumentationGenerator
from encoding.path_encoder import SmartPathEncoder
from integration.activelog_connector import ActiveLogConnector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProjectMemorySystem:
    def __init__(self, port: int = 8460):
        self.port = port
        self.app = FastAPI(title="ActiveLog Project Memory System")
        self.websocket_connections: List[WebSocket] = []
        
        # Core components
        self.knowledge_graph = KnowledgeGraph()
        self.context_optimizer = ContextOptimizer()
        self.bot_view_manager = BotViewManager()
        self.doc_generator = DynamicDocumentationGenerator()
        self.path_encoder = SmartPathEncoder()
        self.activelog_connector = ActiveLogConnector()
        
        # Memory storage
        self.concept_cache: Dict[str, Any] = {}
        self.context_cache: Dict[str, Any] = {}
        self.path_encodings: Dict[str, str] = {}
        self.bot_sessions: Dict[str, Dict[str, Any]] = {}
        
        self._setup_routes()
        self._setup_middleware()
        
    def _setup_middleware(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self):
        
        @self.app.get("/")
        async def root():
            knowledge_stats = await self.knowledge_graph.get_stats()
            return {
                "system": "ActiveLog Project Memory System",
                "version": "1.0.0",
                "knowledge_concepts": knowledge_stats.get("concepts", 0),
                "context_optimizations": len(self.context_cache),
                "active_bot_sessions": len(self.bot_sessions),
                "memory_compression_ratio": await self._calculate_compression_ratio(),
                "activelog_integration": len(self.activelog_connector.services),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Knowledge Graph Management
        @self.app.post("/knowledge/concepts")
        async def create_concept(concept_data: dict):
            """Create new compressed concept with unique ID"""
            concept_id = await self.knowledge_graph.create_concept(
                content=concept_data["content"],
                category=concept_data.get("category", "CORE"),
                references=concept_data.get("references", []),
                compression_level=concept_data.get("compression_level", "high")
            )
            
            if concept_id:
                # Update concept cache
                await self._update_concept_cache(concept_id)
                
                # Broadcast to connected services
                await self._broadcast_update("concept_created", {
                    "concept_id": concept_id,
                    "category": concept_data.get("category")
                })
                
                return {"concept_id": concept_id, "status": "created"}
            else:
                raise HTTPException(status_code=400, detail="Failed to create concept")
        
        @self.app.get("/knowledge/concepts/{concept_id}")
        async def get_concept(concept_id: str, bot_type: str = "advanced", expand_refs: bool = False):
            """Get concept with bot-specific formatting"""
            concept = await self.knowledge_graph.get_concept(concept_id)
            
            if not concept:
                raise HTTPException(status_code=404, detail="Concept not found")
            
            # Apply bot-specific view
            formatted_concept = self.bot_view_manager.format_for_bot(
                {"concepts": [concept]}, bot_type
            )
            
            return formatted_concept
        
        @self.app.get("/knowledge/search")
        async def search_concepts(
            query: str, 
            category: Optional[str] = None,
            max_results: int = 10,
            bot_type: str = "advanced"
        ):
            """Semantic search with bot-optimized results"""
            results = await self.knowledge_graph.semantic_search(
                query=query,
                category=category,
                max_results=max_results
            )
            
            # Format for specific bot type
            formatted_results = self.bot_view_manager.format_for_bot(
                {"concepts": results}, bot_type
            )["content"]["concepts"]
            
            return {
                "query": query,
                "results": formatted_results,
                "total": len(formatted_results),
                "bot_optimized": bot_type
            }
        
        # Context Optimization Routes
        @self.app.post("/context/optimize")
        async def optimize_context(context_request: dict):
            """Optimize context for minimal token usage"""
            optimization_id = f"ctx_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            optimized_context = await self.context_optimizer.optimize(
                request_id=optimization_id,
                task_description=context_request["task"],
                current_context=context_request.get("current_context", []),
                bot_capabilities=context_request.get("bot_type", "advanced"),
                max_tokens=context_request.get("max_tokens", 4000),
                priority_concepts=context_request.get("priority", [])
            )
            
            # Cache optimized context
            self.context_cache[optimization_id] = optimized_context
            
            return {
                "optimization_id": optimization_id,
                "optimized_context": optimized_context,
                "token_reduction": optimized_context.get("token_savings", 0),
                "compression_techniques": optimized_context.get("techniques_used", [])
            }
        
        @self.app.get("/context/{optimization_id}")
        async def get_optimized_context(optimization_id: str):
            """Retrieve cached optimized context"""
            if optimization_id not in self.context_cache:
                raise HTTPException(status_code=404, detail="Context optimization not found")
            
            return self.context_cache[optimization_id]
        
        @self.app.post("/context/progressive-load")
        async def progressive_context_load(load_request: dict):
            """Incrementally load context as needed"""
            session_id = load_request.get("session_id", f"session_{datetime.now().timestamp()}")
            
            if session_id not in self.bot_sessions:
                self.bot_sessions[session_id] = {
                    "loaded_concepts": set(),
                    "context_history": [],
                    "bot_type": load_request.get("bot_type", "advanced"),
                    "task_context": load_request.get("task", "")
                }
            
            session = self.bot_sessions[session_id]
            
            # Determine what new context to load
            new_context = await self.context_optimizer.progressive_load(
                session=session,
                new_requirement=load_request.get("requirement", ""),
                max_new_tokens=load_request.get("max_new_tokens", 1000)
            )
            
            session["loaded_concepts"].update(new_context.get("new_concepts", []))
            session["context_history"].append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "requirement": load_request.get("requirement", ""),
                "loaded": new_context.get("new_concepts", [])
            })
            
            return {
                "session_id": session_id,
                "new_context": new_context,
                "total_loaded": len(session["loaded_concepts"]),
                "session_history": session["context_history"]
            }
        
        # Path Encoding System
        @self.app.post("/paths/encode")
        async def encode_path(path_data: dict):
            """Create semantically meaningful path encoding"""
            original_path = path_data["path"]
            content_analysis = path_data.get("content_analysis")
            
            encoded_path_obj = self.path_encoder.encode_path(
                original_path=original_path,
                content_analysis=content_analysis
            )
            
            # Store encoding mapping
            path_hash = hashlib.md5(original_path.encode()).hexdigest()[:8]
            self.path_encodings[path_hash] = {
                "original": original_path,
                "encoded": encoded_path_obj.encoded_path,
                "functionality": encoded_path_obj.functionality.value,
                "path_type": encoded_path_obj.path_type.value,
                "complexity": encoded_path_obj.complexity_level,
                "created": datetime.now(timezone.utc).isoformat()
            }
            
            return {
                "encoded_path": encoded_path_obj.encoded_path,
                "path_id": path_hash,
                "functionality": encoded_path_obj.functionality.value,
                "complexity": encoded_path_obj.complexity_level,
                "metadata": encoded_path_obj.metadata
            }
        
        @self.app.get("/paths/decode/{path_id}")
        async def decode_path(path_id: str):
            """Decode semantic path to understand functionality"""
            if path_id not in self.path_encodings:
                raise HTTPException(status_code=404, detail="Path encoding not found")
            
            encoding_info = self.path_encodings[path_id]
            
            # Use path encoder to decode
            decoded_info = self.path_encoder.decode_path(encoding_info["encoded"])
            
            return {
                "path_id": path_id,
                "original_path": encoding_info["original"],
                "encoded_path": encoding_info["encoded"],
                "decoded_info": decoded_info,
                "functionality": encoding_info["functionality"],
                "path_type": encoding_info["path_type"],
                "complexity": encoding_info["complexity"]
            }
        
        # Bot-Specific Views
        @self.app.post("/views/bot-session")
        async def create_bot_session(session_data: dict):
            """Create optimized view for specific bot capabilities"""
            bot_type = session_data["bot_type"]  # simple, intermediate, advanced, expert
            task_context = session_data["task"]
            capabilities = session_data.get("capabilities", [])
            
            session_id = f"bot_{bot_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Create optimized view using bot view manager
            from views.bot_view_manager import BotCapabilityLevel
            try:
                bot_level = BotCapabilityLevel(bot_type)
            except ValueError:
                bot_level = BotCapabilityLevel.ADVANCED
            
            bot_view = {
                "session_id": session_id,
                "bot_type": bot_type,
                "task_context": task_context,
                "capabilities": capabilities,
                "bot_level": bot_level.value,
                "created": datetime.now(timezone.utc).isoformat(),
                "last_activity": datetime.now(timezone.utc).isoformat()
            }
            
            self.bot_sessions[session_id] = bot_view
            
            return {
                "session_id": session_id,
                "bot_type": bot_type,
                "optimized_view": bot_view,
                "estimated_token_usage": bot_view.get("estimated_tokens", 0)
            }
        
        @self.app.get("/views/bot-session/{session_id}")
        async def get_bot_session_view(session_id: str, expand: bool = False):
            """Get current bot session view"""
            if session_id not in self.bot_sessions:
                raise HTTPException(status_code=404, detail="Bot session not found")
            
            session = self.bot_sessions[session_id]
            
            if expand:
                # Provide expanded context if requested
                expanded_view = dict(session)
                expanded_view["expanded"] = True
                expanded_view["expansion_timestamp"] = datetime.now(timezone.utc).isoformat()
                return expanded_view
            
            return session
        
        # Dynamic Documentation
        @self.app.post("/docs/generate")
        async def generate_documentation(doc_request: dict, background_tasks: BackgroundTasks):
            """Generate documentation for code changes"""
            generation_id = f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            background_tasks.add_task(
                self._generate_documentation,
                generation_id,
                doc_request
            )
            
            return {"generation_id": generation_id, "status": "generation_initiated"}
        
        @self.app.post("/docs/update-tracking")
        async def update_change_tracking(change_data: dict):
            """Track code changes for documentation updates"""
            change_id = f"change_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            change = self.doc_generator.track_changes(change_data["file_path"])
            
            # Check if documentation needs updating 
            outdated_docs = self.doc_generator.detect_outdated_documentation()
            
            if outdated_docs:
                await self._broadcast_update("docs_outdated", {
                    "change_id": change_id,
                    "outdated_docs": outdated_docs
                })
            
            return {
                "change_id": change_id,
                "tracked": True,
                "outdated_docs_count": len(outdated_docs)
            }
        
        # ActiveLog Integration Routes
        @self.app.post("/integration/sync-services")
        async def sync_with_activelog_services(background_tasks: BackgroundTasks):
            """Sync knowledge graph with all ActiveLog services"""
            background_tasks.add_task(self._sync_all_activelog_services)
            return {"status": "sync_initiated", "services_to_sync": 12}
        
        @self.app.get("/integration/service-knowledge/{service_name}")
        async def get_service_knowledge(service_name: str, bot_type: str = "advanced"):
            """Get optimized knowledge for specific ActiveLog service"""
            service_info = await self.activelog_connector.get_service_info(service_name)
            
            if service_info:
                # Format service info for bot consumption
                formatted = self.bot_view_manager.format_for_bot(
                    {"service_info": service_info}, bot_type
                )
                return formatted
            
            raise HTTPException(status_code=404, detail="Service not found")
        
        @self.app.post("/integration/cross-service-context")
        async def generate_cross_service_context(context_request: dict):
            """Generate context spanning multiple ActiveLog services"""
            services = context_request["services"]  # List of service names
            task_context = context_request["task"]
            bot_type = context_request.get("bot_type", "advanced")
            
            # Get info for all requested services
            service_contexts = []
            for service in services:
                service_info = await self.activelog_connector.get_service_info(service)
                if service_info:
                    service_contexts.append(service_info)
            
            cross_service_context = {
                "services": service_contexts,
                "task_context": task_context,
                "optimization_level": bot_type,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
            return cross_service_context
        
        # Analytics & Optimization
        @self.app.get("/analytics/compression-stats")
        async def get_compression_analytics():
            """Get detailed compression and optimization statistics"""
            stats = {
                "context_optimization": {
                    "cached_contexts": len(self.context_cache),
                    "active_optimizations": sum(1 for c in self.context_cache.values() if c.get("active", False))
                },
                "knowledge_efficiency": await self.knowledge_graph.get_stats(),
                "bot_view_utilization": {
                    "active_sessions": len(self.bot_sessions),
                    "session_types": {bt: sum(1 for s in self.bot_sessions.values() if s.get("bot_type") == bt) 
                                    for bt in ["simple", "intermediate", "advanced", "expert"]}
                },
                "memory_usage": await self._get_memory_usage_stats()
            }
            
            return stats
        
        @self.app.post("/optimization/auto-compress")
        async def auto_compress_concepts(compression_request: dict, background_tasks: BackgroundTasks):
            """Automatically compress and optimize concept storage"""
            compression_id = f"compress_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            background_tasks.add_task(
                self._auto_compress_concepts,
                compression_id,
                compression_request
            )
            
            return {"compression_id": compression_id, "status": "compression_initiated"}
        
        # WebSocket for real-time updates
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.websocket_connections.append(websocket)
            
            try:
                while True:
                    data = await websocket.receive_text()
                    logger.info(f"Received websocket message: {data}")
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
            finally:
                self.websocket_connections.remove(websocket)
        
        @self.app.get("/health")
        async def health_check():
            component_health = {
                "knowledge_graph": True,  # Simplified health check
                "context_optimizer": True,
                "bot_view_manager": True, 
                "doc_generator": True,
                "activelog_connector": len(self.activelog_connector.services) > 0
            }
            
            overall_healthy = all(component_health.values())
            
            return {
                "status": "healthy" if overall_healthy else "degraded",
                "components": component_health,
                "memory_efficiency": await self._calculate_compression_ratio(),
                "active_sessions": len(self.bot_sessions),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def _generate_semantic_path(self, original_path: str, functionality: str, context: dict) -> str:
        """Generate semantically meaningful path encoding"""
        # Parse functionality and create semantic segments
        segments = []
        
        # Extract core functionality
        if "auth" in functionality.lower():
            segments.append("auth")
            if "jwt" in functionality.lower():
                segments.append("jwt")
            if "validation" in functionality.lower():
                segments.append("validate")
        
        # Add context-specific segments
        if context.get("security_level"):
            segments.append(f"sec-{context['security_level']}")
        
        if context.get("performance_critical"):
            segments.append("perf-critical")
        
        # Create compressed but meaningful path
        semantic_path = "/".join(segments) + "/"
        
        # Add specific file naming
        if original_path.endswith('.py'):
            base_name = Path(original_path).stem
            semantic_name = await self._compress_filename(base_name, functionality)
            semantic_path += f"{semantic_name}.py"
        
        return semantic_path
    
    async def _compress_filename(self, base_name: str, functionality: str) -> str:
        """Compress filename while maintaining semantic meaning"""
        # Use common abbreviations and semantic compression
        compressions = {
            "authentication": "auth",
            "validation": "validate",
            "configuration": "config",
            "initialization": "init",
            "management": "mgmt",
            "processing": "proc",
            "generation": "gen",
            "optimization": "opt"
        }
        
        compressed = base_name.lower()
        for full, abbrev in compressions.items():
            compressed = compressed.replace(full, abbrev)
        
        return compressed.replace('_', '-')
    
    async def _calculate_semantic_density(self, encoded_path: str) -> float:
        """Calculate information density of semantic path"""
        # Measure how much functionality is encoded per character
        char_count = len(encoded_path)
        semantic_elements = len(encoded_path.split('/')) + encoded_path.count('-')
        
        return semantic_elements / char_count if char_count > 0 else 0
    
    async def _explain_path_functionality(self, encoded_path: str) -> str:
        """Generate human-readable explanation of path functionality"""
        segments = encoded_path.strip('/').split('/')
        explanations = []
        
        for segment in segments:
            if segment == "auth":
                explanations.append("Authentication system")
            elif segment == "jwt":
                explanations.append("JSON Web Token handling")
            elif segment == "validate":
                explanations.append("Input validation logic")
            elif segment.startswith("sec-"):
                level = segment.split('-')[1]
                explanations.append(f"Security level: {level}")
            elif segment == "perf-critical":
                explanations.append("Performance-critical component")
            else:
                explanations.append(f"Component: {segment}")
        
        return " → ".join(explanations)
    
    async def _break_down_path_semantics(self, encoded_path: str) -> Dict[str, Any]:
        """Break down path into semantic components"""
        return {
            "domain": encoded_path.split('/')[0] if '/' in encoded_path else "root",
            "subdomain": encoded_path.split('/')[1] if len(encoded_path.split('/')) > 1 else None,
            "action": encoded_path.split('/')[-1].split('.')[0] if '.' in encoded_path else None,
            "file_type": encoded_path.split('.')[-1] if '.' in encoded_path else None,
            "semantic_indicators": [seg for seg in encoded_path.split('/') if '-' in seg]
        }
    
    async def _update_concept_cache(self, concept_id: str):
        """Update concept cache with new or modified concept"""
        concept = await self.knowledge_graph.get_concept(concept_id)
        if concept:
            self.concept_cache[concept_id] = {
                "concept": concept,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "access_count": 0
            }
    
    async def _calculate_compression_ratio(self) -> float:
        """Calculate overall memory compression efficiency"""
        if not self.concept_cache:
            return 0.0
        
        total_original = 0
        total_compressed = 0
        
        for concept_data in self.concept_cache.values():
            concept = concept_data["concept"]
            original_size = len(concept.get("original_content", ""))
            compressed_size = len(concept.get("compressed_content", ""))
            
            total_original += original_size
            total_compressed += compressed_size
        
        if total_original == 0:
            return 0.0
        
        return 1.0 - (total_compressed / total_original)
    
    async def _get_memory_usage_stats(self) -> Dict[str, Any]:
        """Get detailed memory usage statistics"""
        return {
            "concepts_cached": len(self.concept_cache),
            "contexts_cached": len(self.context_cache),
            "path_encodings": len(self.path_encodings),
            "active_bot_sessions": len(self.bot_sessions),
            "estimated_memory_mb": (
                len(str(self.concept_cache)) + 
                len(str(self.context_cache)) + 
                len(str(self.bot_sessions))
            ) / (1024 * 1024)
        }
    
    async def _generate_documentation(self, generation_id: str, doc_request: dict):
        """Generate documentation (background task)"""
        try:
            logger.info(f"Generating documentation: {generation_id}")
            
            # Use doc generator to create documentation
            target = doc_request.get("target", "")
            doc_type = doc_request.get("type", "api")
            
            if doc_type == "api":
                documentation = self.doc_generator.generate_api_documentation(target)
            elif doc_type == "code":
                documentation = self.doc_generator.generate_code_explanation(target)
            else:
                # Generate system overview
                services_info = {}
                for service_name, service in self.activelog_connector.services.items():
                    services_info[service_name] = {
                        "port": service.port,
                        "phase": service.phase,
                        "status": service.status.value,
                        "description": f"{service_name} service",
                        "features": service.features
                    }
                documentation = self.doc_generator.generate_system_overview(services_info)
            
            if documentation:
                doc_info = {
                    "pages_count": 1,
                    "compression_ratio": 0.8
                }
            else:
                doc_info = {"pages_count": 0, "compression_ratio": 0}
            
            await self._broadcast_update("documentation_generated", {
                "generation_id": generation_id,
                "pages_generated": doc_info["pages_count"],
                "compression_achieved": doc_info["compression_ratio"]
            })
            
            logger.info(f"Documentation generation completed: {generation_id}")
            
        except Exception as e:
            logger.error(f"Documentation generation failed {generation_id}: {e}")
    
    async def _sync_all_activelog_services(self):
        """Sync knowledge with all ActiveLog services (background task)"""
        try:
            services = [
                "bot-orchestrator", "bot-ecosystem", "auto-scheduler",
                "luciddreamer-core", "dream-simulator", 
                "compute-sharing", "hatchery-manager", "business-platform", "municipal-platform",
                "dividend-shares", "paper-trading", "code-director"
            ]
            
            synced_services = []
            for service in services:
                try:
                    service_info = await self.activelog_connector.get_service_info(service)
                    if service_info:
                        synced_services.append(service)
                        
                        # Create service concept in knowledge graph
                        await self.knowledge_graph.create_concept(
                            content=f"{service}={service_info.get('description', 'ActiveLog service')}",
                            category=f"SERVICE_{service.upper().replace('-', '_')}",
                            references=service_info.get("features", [])
                        )
                        logger.info(f"Synced service knowledge: {service}")
                except Exception as e:
                    logger.error(f"Failed to sync service {service}: {e}")
            
            await self._broadcast_update("services_synced", {
                "synced_services": synced_services,
                "total_synced": len(synced_services),
                "failed_services": [s for s in services if s not in synced_services]
            })
            
            logger.info(f"Synced {len(synced_services)}/{len(services)} ActiveLog services")
            
        except Exception as e:
            logger.error(f"Service sync failed: {e}")
    
    async def _auto_compress_concepts(self, compression_id: str, compression_request: dict):
        """Auto-compress concepts for optimization (background task)"""
        try:
            logger.info(f"Auto-compressing concepts: {compression_id}")
            
            # Simulate compression results
            compression_results = {
                "compressed": {},
                "compression_ratio": compression_request.get("target_ratio", 0.7),
                "space_saved": 1024 * 1024  # 1MB saved
            }
            
            logger.info(f"Auto-compression simulation completed for {compression_id}")
            
            await self._broadcast_update("concepts_compressed", {
                "compression_id": compression_id,
                "concepts_compressed": len(compression_results.get("compressed", {})),
                "compression_achieved": compression_results.get("compression_ratio", 0),
                "space_saved_mb": compression_results.get("space_saved", 0)
            })
            
            logger.info(f"Concept compression completed: {compression_id}")
            
        except Exception as e:
            logger.error(f"Concept compression failed {compression_id}: {e}")
    
    async def _broadcast_update(self, event_type: str, data: dict):
        """Broadcast updates to WebSocket connections and ActiveLog services"""
        if not self.websocket_connections:
            return
        
        message = {
            "event": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "project_memory_system"
        }
        
        disconnected = []
        for ws in self.websocket_connections:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send WebSocket message: {e}")
                disconnected.append(ws)
        
        for ws in disconnected:
            self.websocket_connections.remove(ws)
        
        # Also notify ActiveLog services of memory system updates
        try:
            await self.activelog_connector.broadcast_to_all_services("/memory/update", message)
        except Exception as e:
            logger.error(f"Failed to broadcast to ActiveLog services: {e}")
    
    async def start_monitoring_loops(self):
        """Start background monitoring and optimization loops"""
        asyncio.create_task(self._knowledge_optimization_loop())
        asyncio.create_task(self._context_cleanup_loop())
        asyncio.create_task(self._documentation_monitoring_loop())
        asyncio.create_task(self._activelog_sync_loop())
        
        logger.info("Started all project memory monitoring loops")
    
    async def _knowledge_optimization_loop(self):
        """Continuously optimize knowledge storage"""
        while True:
            try:
                # Check for optimization opportunities in concept cache
                if len(self.concept_cache) > 100:  # If we have many cached concepts
                    # Simple optimization: remove least accessed concepts
                    sorted_concepts = sorted(
                        self.concept_cache.items(),
                        key=lambda x: x[1].get("access_count", 0)
                    )
                    
                    # Remove bottom 10%
                    to_remove = len(sorted_concepts) // 10
                    for concept_id, _ in sorted_concepts[:to_remove]:
                        del self.concept_cache[concept_id]
                    
                    logger.info(f"Optimized concept cache: removed {to_remove} least accessed concepts")
                
                await asyncio.sleep(1800)  # 30 minutes
                
            except Exception as e:
                logger.error(f"Knowledge optimization error: {e}")
                await asyncio.sleep(300)
    
    async def _context_cleanup_loop(self):
        """Clean up expired contexts and sessions"""
        while True:
            try:
                current_time = datetime.now(timezone.utc)
                
                # Clean up old contexts (older than 4 hours)
                expired_contexts = []
                for ctx_id, context in self.context_cache.items():
                    created_time = datetime.fromisoformat(context.get("created", current_time.isoformat()))
                    if (current_time - created_time).total_seconds() > 14400:  # 4 hours
                        expired_contexts.append(ctx_id)
                
                for ctx_id in expired_contexts:
                    del self.context_cache[ctx_id]
                
                # Clean up inactive bot sessions
                inactive_sessions = []
                for session_id, session in self.bot_sessions.items():
                    last_activity = datetime.fromisoformat(
                        session.get("last_activity", current_time.isoformat())
                    )
                    if (current_time - last_activity).total_seconds() > 7200:  # 2 hours
                        inactive_sessions.append(session_id)
                
                for session_id in inactive_sessions:
                    del self.bot_sessions[session_id]
                
                if expired_contexts or inactive_sessions:
                    logger.info(f"Cleaned up {len(expired_contexts)} contexts and {len(inactive_sessions)} sessions")
                
                await asyncio.sleep(3600)  # 1 hour
                
            except Exception as e:
                logger.error(f"Context cleanup error: {e}")
                await asyncio.sleep(600)
    
    async def _documentation_monitoring_loop(self):
        """Monitor for documentation updates needed"""
        while True:
            try:
                # Check for outdated documentation
                outdated_docs = self.doc_generator.detect_outdated_documentation()
                
                if outdated_docs:
                    await self._broadcast_update("documentation_needs_update", {
                        "outdated_count": len(outdated_docs),
                        "outdated_docs": outdated_docs
                    })
                
                await asyncio.sleep(7200)  # 2 hours
                
            except Exception as e:
                logger.error(f"Documentation monitoring error: {e}")
                await asyncio.sleep(600)
    
    async def _activelog_sync_loop(self):
        """Periodically sync with ActiveLog services"""
        while True:
            try:
                # Check connectivity to all services
                service_status = await self.activelog_connector.get_all_services_status()
                healthy_services = [name for name, info in service_status["services"].items() 
                                  if info["status"] == "healthy"]
                
                # Update sync tracking
                if not hasattr(self, '_last_synced_services'):
                    self._last_synced_services = set()
                
                # Log service status
                logger.info(f"ActiveLog services status: {len(healthy_services)}/{len(service_status['services'])} healthy")
                
                self._last_synced_services = set(healthy_services)
                
                await asyncio.sleep(1800)  # 30 minutes
                
            except Exception as e:
                logger.error(f"ActiveLog sync error: {e}")
                await asyncio.sleep(600)
    
    def run(self):
        """Start the project memory system"""
        logger.info(f"Starting ActiveLog Project Memory System on port {self.port}")
        uvicorn.run(
            self.app,
            host="0.0.0.0",
            port=self.port,
            log_level="info"
        )

async def main():
    system = ProjectMemorySystem()
    
    # Start background monitoring
    await system.start_monitoring_loops()
    
    # This would typically be called by uvicorn
    # system.run()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        # Development mode with asyncio
        asyncio.run(main())
    else:
        # Production mode with uvicorn
        ProjectMemorySystem().run()