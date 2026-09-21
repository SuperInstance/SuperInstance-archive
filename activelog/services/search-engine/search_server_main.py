#!/usr/bin/env python3
"""
ActiveLog Unified Search Engine - Main Server
Comprehensive search system orchestrating all search capabilities
"""

import asyncio
import json
import logging
import time
from pathlib import Path
import sys
from aiohttp import web, web_request
import aiohttp_cors
import uuid
from typing import Dict, List, Any, Optional

# Add current directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import all search components
from core.search_engine import UnifiedSearchEngine, SearchQuery, SearchType, SearchDocument, ContentType
from semantic.semantic_search import SemanticSearch
from multimodal.multimodal_search import MultimodalSearch, ModalityType
from suggestions.saved_searches import SuggestionEngine, SavedSearchManager
from federated.federated_search import FederatedSearchEngine, ExternalSource, GitHubSearchAdapter, NewsAPIAdapter
from nlp.query_parser import NaturalLanguageQueryParser
from ranking.ml_ranking import MLRankingModel
from fuzzy.fuzzy_search import FuzzySearchEngine
from multilingual.multilingual_search import MultilingualSearchEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SearchIndexManager:
    """Manages indexing across all search systems"""
    
    def __init__(self, unified_engine, semantic_engine, multimodal_engine, 
                 fuzzy_engine, multilingual_engine):
        self.unified_engine = unified_engine
        self.semantic_engine = semantic_engine
        self.multimodal_engine = multimodal_engine
        self.fuzzy_engine = fuzzy_engine
        self.multilingual_engine = multilingual_engine
        
        # Auto-discovery of services (mock)
        self.discovered_services = self._discover_services()
        
        # Indexing statistics
        self.indexing_stats = {
            "documents_indexed": 0,
            "services_indexed": 0,
            "last_index_time": 0,
            "indexing_errors": 0
        }
    
    def _discover_services(self) -> List[Dict[str, Any]]:
        """Auto-discover ActiveLog services for indexing"""
        # Mock service discovery - in production, this would scan actual services
        mock_services = [
            {"id": "PersonalLog", "name": "Personal Log", "port": 8001, "documents": 1500},
            {"id": "BusinessLog", "name": "Business Log", "port": 8002, "documents": 2300},
            {"id": "TaskManager", "name": "Task Manager", "port": 8003, "documents": 800},
            {"id": "NoteTaker", "name": "Note Taker", "port": 8004, "documents": 1200},
            {"id": "Calendar", "name": "Calendar", "port": 8005, "documents": 600},
            {"id": "Contacts", "name": "Contacts", "port": 8006, "documents": 400},
            {"id": "FinanceLog", "name": "Finance Log", "port": 8007, "documents": 900},
            {"id": "HealthLog", "name": "Health Log", "port": 8008, "documents": 700},
            {"id": "MediaLibrary", "name": "Media Library", "port": 8009, "documents": 3200},
            {"id": "EmailManager", "name": "Email Manager", "port": 8010, "documents": 5500}
        ]
        
        logger.info(f"Discovered {len(mock_services)} ActiveLog services")
        return mock_services
    
    async def index_all_services(self):
        """Index content from all discovered services"""
        logger.info("🔄 Starting comprehensive indexing of all services...")
        start_time = time.time()
        
        total_documents = 0
        errors = 0
        
        for service in self.discovered_services:
            try:
                await self._index_service(service)
                total_documents += service.get("documents", 0)
                logger.info(f"✅ Indexed {service['name']}: {service.get('documents', 0)} documents")
            except Exception as e:
                errors += 1
                logger.error(f"❌ Failed to index {service['name']}: {e}")
        
        # Fit semantic models after indexing
        if total_documents > 0:
            await self._fit_semantic_models()
        
        # Update statistics
        indexing_time = time.time() - start_time
        self.indexing_stats.update({
            "documents_indexed": total_documents,
            "services_indexed": len(self.discovered_services) - errors,
            "last_index_time": indexing_time,
            "indexing_errors": errors
        })
        
        logger.info(f"🎉 Indexing completed: {total_documents} documents from {len(self.discovered_services)} services in {indexing_time:.1f}s")
    
    async def _index_service(self, service: Dict[str, Any]):
        """Index content from a specific service"""
        service_id = service["id"]
        document_count = service.get("documents", 100)
        
        # Generate mock documents for each service
        for i in range(document_count):
            doc_id = f"{service_id}_{i}"
            
            # Generate content based on service type
            title, content, content_type = self._generate_mock_content(service_id, i)
            
            # Create search document
            document = SearchDocument(
                id=doc_id,
                service_id=service_id,
                content_type=content_type,
                title=title,
                content=content,
                metadata={
                    "service_name": service["name"],
                    "created_at": time.time() - (i * 3600),  # Stagger creation times
                    "last_modified": time.time() - (i * 1800),
                    "file_size": len(content),
                    "mock_document": True
                }
            )
            
            # Index in all engines
            await self._index_document_all_engines(document)
    
    def _generate_mock_content(self, service_id: str, index: int) -> tuple:
        """Generate mock content based on service type"""
        content_templates = {
            "PersonalLog": {
                "titles": [
                    f"Daily Reflection {index}",
                    f"Personal Goals Update {index}",
                    f"Life Event - {index}",
                    f"Thoughts and Ideas {index}"
                ],
                "content": [
                    f"Today I reflected on my personal growth and achievements. Entry number {index} in my journey.",
                    f"Setting new personal goals for self-improvement. This is my {index}th goal-setting session.",
                    f"Recording an important life event that happened today. Event {index} has been significant.",
                    f"Capturing thoughts and ideas that came to mind. Idea collection {index} for future reference."
                ],
                "type": ContentType.LOG_ENTRY
            },
            "BusinessLog": {
                "titles": [
                    f"Business Meeting Notes {index}",
                    f"Project Status Update {index}",
                    f"Client Communication {index}",
                    f"Strategy Planning {index}"
                ],
                "content": [
                    f"Meeting with stakeholders about project progress. Meeting {index} covered key business decisions.",
                    f"Project milestone review and planning. Update {index} shows good progress toward goals.",
                    f"Client feedback and requirements discussion. Communication {index} clarified expectations.",
                    f"Strategic planning session for future growth. Planning session {index} identified opportunities."
                ],
                "type": ContentType.LOG_ENTRY
            },
            "TaskManager": {
                "titles": [
                    f"Project Task {index}",
                    f"Weekly Review {index}",
                    f"Action Item {index}",
                    f"Deadline Reminder {index}"
                ],
                "content": [
                    f"Important project task requiring attention. Task {index} is high priority.",
                    f"Weekly productivity review and planning. Review {index} shows task completion trends.",
                    f"Action item from recent meeting. Item {index} needs immediate follow-up.",
                    f"Reminder about upcoming deadline. Deadline {index} approaches soon."
                ],
                "type": ContentType.CUSTOM
            },
            "EmailManager": {
                "titles": [
                    f"Important Email {index}",
                    f"Team Communication {index}",
                    f"Client Update {index}",
                    f"Project Discussion {index}"
                ],
                "content": [
                    f"Important email regarding business matters. Email {index} contains critical information.",
                    f"Team coordination and communication. Message {index} discusses project collaboration.",
                    f"Client status update and feedback. Update {index} includes important client requirements.",
                    f"Project discussion with stakeholders. Discussion {index} covers technical details."
                ],
                "type": ContentType.EMAIL
            }
        }
        
        # Get template for service or use default
        template = content_templates.get(service_id, content_templates["PersonalLog"])
        
        title_idx = index % len(template["titles"])
        content_idx = index % len(template["content"])
        
        return (
            template["titles"][title_idx],
            template["content"][content_idx],
            template["type"]
        )
    
    async def _index_document_all_engines(self, document: SearchDocument):
        """Index document in all search engines"""
        # Core unified engine
        self.unified_engine.add_document(document)
        
        # Semantic search
        await self.semantic_engine.index_document(
            document.id, 
            document.content, 
            document.title
        )
        
        # Multimodal search (text modality)
        await self.multimodal_engine.index_content(
            document.id,
            document.content,
            ModalityType.TEXT,
            {"title": document.title}
        )
        
        # Fuzzy search
        self.fuzzy_engine.add_document(
            document.id,
            document.content,
            document.title
        )
        
        # Multilingual search
        detected_language = self.multilingual_engine.add_document(
            document.id,
            document.content,
            document.title
        )
    
    async def _fit_semantic_models(self):
        """Fit semantic models after indexing"""
        logger.info("🧠 Fitting semantic search models...")
        
        # Collect corpus from indexed documents
        corpus = []
        for doc in self.unified_engine.index.documents.values():
            corpus.append(f"{doc.title} {doc.content}")
        
        # Fit semantic search models
        await self.semantic_engine.fit_models(corpus)
        
        logger.info("✅ Semantic models fitted successfully")

class UnifiedSearchServer:
    """Main unified search server"""
    
    def __init__(self, host: str = "localhost", port: int = 8102):
        self.host = host
        self.port = port
        
        # Initialize all search components
        logger.info("🔧 Initializing search components...")
        
        # Core search engine
        self.unified_engine = UnifiedSearchEngine()
        
        # Specialized search engines
        self.semantic_engine = SemanticSearch()
        self.multimodal_engine = MultimodalSearch()
        self.suggestion_engine = SuggestionEngine()
        self.saved_search_manager = SavedSearchManager()
        self.federated_engine = FederatedSearchEngine()
        self.nlp_processor = NaturalLanguageQueryParser()
        self.ranking_model = MLRankingModel()
        self.fuzzy_engine = FuzzySearchEngine()
        self.multilingual_engine = MultilingualSearchEngine()
        
        # Connect components
        self.unified_engine.set_components(
            semantic_search=self.semantic_engine,
            multimodal_search=self.multimodal_engine,
            nlp_processor=self.nlp_processor,
            ranking_model=self.ranking_model,
            fuzzy_matcher=self.fuzzy_engine,
            multilingual_processor=self.multilingual_engine
        )
        
        # Index manager
        self.index_manager = SearchIndexManager(
            self.unified_engine,
            self.semantic_engine,
            self.multimodal_engine,
            self.fuzzy_engine,
            self.multilingual_engine
        )
        
        # Configure external sources for federated search
        self._configure_federated_sources()
        
        # Web application
        self.app = web.Application()
        self.setup_routes()
        self.setup_cors()
        
        # Server statistics
        self.start_time = time.time()
        
        logger.info("✅ All search components initialized")
    
    def _configure_federated_sources(self):
        """Configure external search sources"""
        # GitHub source (requires API key for higher rate limits)
        github_source = ExternalSource(
            id="github",
            name="GitHub",
            base_url="https://api.github.com",
            search_endpoint="search/repositories",
            # api_key="your_github_token_here",  # Uncomment and add real token
            rate_limit=60,  # Lower rate limit without API key
            weight=0.8
        )
        self.federated_engine.register_source(github_source, GitHubSearchAdapter)
        
        # News API source (requires API key)
        # news_source = ExternalSource(
        #     id="news",
        #     name="NewsAPI",
        #     base_url="https://newsapi.org/v2",
        #     api_key="your_newsapi_key_here",  # Add real API key
        #     rate_limit=500,
        #     weight=0.6
        # )
        # self.federated_engine.register_source(news_source, NewsAPIAdapter)
    
    def setup_routes(self):
        """Setup HTTP routes"""
        # Main search endpoint
        self.app.router.add_post('/search', self.handle_search)
        
        # Specialized search endpoints
        self.app.router.add_post('/search/semantic', self.handle_semantic_search)
        self.app.router.add_post('/search/multimodal', self.handle_multimodal_search)
        self.app.router.add_post('/search/fuzzy', self.handle_fuzzy_search)
        self.app.router.add_post('/search/multilingual', self.handle_multilingual_search)
        self.app.router.add_post('/search/federated', self.handle_federated_search)
        
        # Suggestions and autocomplete
        self.app.router.add_get('/suggest', self.handle_suggestions)
        self.app.router.add_get('/autocomplete', self.handle_autocomplete)
        
        # Saved searches
        self.app.router.add_post('/saved-searches', self.handle_save_search)
        self.app.router.add_get('/saved-searches/{user_id}', self.handle_get_saved_searches)
        self.app.router.add_delete('/saved-searches/{search_id}', self.handle_delete_saved_search)
        
        # Analytics
        self.app.router.add_get('/analytics', self.handle_analytics)
        self.app.router.add_get('/popular-queries', self.handle_popular_queries)
        
        # System endpoints
        self.app.router.add_get('/health', self.handle_health_check)
        self.app.router.add_get('/stats', self.handle_stats)
        self.app.router.add_post('/reindex', self.handle_reindex)
        
        # Index management
        self.app.router.add_post('/documents', self.handle_add_document)
        self.app.router.add_delete('/documents/{doc_id}', self.handle_delete_document)
        
        # Static dashboard
        self.app.router.add_get('/', self.handle_dashboard)
    
    def setup_cors(self):
        """Setup CORS for web API"""
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # Add CORS to all routes
        for route in list(self.app.router.routes()):
            cors.add(route)
    
    async def handle_search(self, request: web_request.Request) -> web.Response:
        """Handle unified search requests"""
        try:
            data = await request.json()
            
            # Create search query
            query = SearchQuery(
                id=str(uuid.uuid4()),
                query=data.get('query', ''),
                search_type=SearchType(data.get('search_type', 'text')),
                filters=data.get('filters', {}),
                facets=data.get('facets', []),
                limit=min(data.get('limit', 50), 200),
                offset=data.get('offset', 0),
                user_id=data.get('user_id'),
                language=data.get('language', 'en')
            )
            
            # Record query for suggestions
            self.suggestion_engine.record_query(
                query.query, 
                query.user_id,
                execution_time_ms=0  # Will be updated after search
            )
            
            # Perform search
            start_time = time.time()
            response = await self.unified_engine.search(query)
            search_time = (time.time() - start_time) * 1000
            
            # Update suggestion engine with timing
            self.suggestion_engine.record_query(
                query.query,
                query.user_id,
                len(response.results),
                search_time
            )
            
            return web.json_response({
                "status": "success",
                "query_id": response.query_id,
                "results": [
                    {
                        "document_id": result.document_id,
                        "service_id": result.service_id,
                        "title": result.title,
                        "content_snippet": result.content_snippet,
                        "content_type": result.content_type.value,
                        "score": result.score,
                        "metadata": result.metadata,
                        "highlights": result.highlights
                    }
                    for result in response.results
                ],
                "total_hits": response.total_hits,
                "facets": response.facets,
                "suggestions": response.suggestions,
                "query_time_ms": response.query_time_ms
            })
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return web.json_response({
                "status": "error",
                "message": str(e)
            }, status=500)
    
    async def handle_semantic_search(self, request: web_request.Request) -> web.Response:
        """Handle semantic search requests"""
        try:
            data = await request.json()
            query = data.get('query', '')
            limit = min(data.get('limit', 50), 200)
            
            results = await self.semantic_engine.search(query, limit)
            
            return web.json_response({
                "status": "success",
                "results": [{"document_id": doc_id, "score": score} for doc_id, score in results],
                "search_type": "semantic"
            })
            
        except Exception as e:
            logger.error(f"Semantic search error: {e}")
            return web.json_response({
                "status": "error",
                "message": str(e)
            }, status=500)
    
    async def handle_multimodal_search(self, request: web_request.Request) -> web.Response:
        """Handle multimodal search requests"""
        try:
            data = await request.json()
            query = data.get('query', '')
            modality = data.get('modality')  # Optional: specific modality
            limit = min(data.get('limit', 50), 200)
            
            results = await self.multimodal_engine.search(query, modality, limit)
            
            return web.json_response({
                "status": "success",
                "results": [{"document_id": doc_id, "score": score} for doc_id, score in results],
                "search_type": "multimodal",
                "modality": modality
            })
            
        except Exception as e:
            logger.error(f"Multimodal search error: {e}")
            return web.json_response({
                "status": "error",
                "message": str(e)
            }, status=500)
    
    async def handle_fuzzy_search(self, request: web_request.Request) -> web.Response:
        """Handle fuzzy search requests"""
        try:
            data = await request.json()
            query = data.get('query', '')
            limit = min(data.get('limit', 50), 200)
            
            results = await self.fuzzy_engine.search(query, limit)
            
            return web.json_response({
                "status": "success",
                "results": [{"document_id": doc_id, "score": score} for doc_id, score in results],
                "search_type": "fuzzy"
            })
            
        except Exception as e:
            logger.error(f"Fuzzy search error: {e}")
            return web.json_response({
                "status": "error",
                "message": str(e)
            }, status=500)
    
    async def handle_multilingual_search(self, request: web_request.Request) -> web.Response:
        """Handle multilingual search requests"""
        try:
            data = await request.json()
            query = data.get('query', '')
            target_language = data.get('target_language', 'en')
            limit = min(data.get('limit', 50), 200)
            
            results = await self.multilingual_engine.search(query, target_language, limit)
            
            return web.json_response({
                "status": "success",
                "results": [{"document_id": doc_id, "score": score} for doc_id, score in results],
                "search_type": "multilingual",
                "target_language": target_language
            })
            
        except Exception as e:
            logger.error(f"Multilingual search error: {e}")
            return web.json_response({
                "status": "error",
                "message": str(e)
            }, status=500)
    
    async def handle_federated_search(self, request: web_request.Request) -> web.Response:
        """Handle federated search requests"""
        try:
            data = await request.json()
            query = data.get('query', '')
            sources = data.get('sources')  # Optional: specific sources
            limit = min(data.get('limit', 50), 200)
            
            results = await self.federated_engine.search(query, sources, limit_per_source=10, total_limit=limit)
            
            return web.json_response({
                "status": "success",
                "results": [
                    {
                        "source_id": result.source_id,
                        "source_name": result.source_name,
                        "title": result.title,
                        "content": result.content,
                        "url": result.url,
                        "score": result.score,
                        "metadata": result.metadata
                    }
                    for result in results
                ],
                "search_type": "federated"
            })
            
        except Exception as e:
            logger.error(f"Federated search error: {e}")
            return web.json_response({
                "status": "error",
                "message": str(e)
            }, status=500)
    
    async def handle_suggestions(self, request: web_request.Request) -> web.Response:
        """Handle search suggestions"""
        try:
            query = request.query.get('q', '')
            user_id = request.query.get('user_id')
            limit = min(int(request.query.get('limit', 10)), 50)
            
            suggestions = self.suggestion_engine.get_suggestions(query, user_id, limit)
            
            return web.json_response({
                "status": "success",
                "query": query,
                "suggestions": [
                    {
                        "text": suggestion.text,
                        "type": suggestion.type,
                        "score": suggestion.score,
                        "metadata": suggestion.metadata
                    }
                    for suggestion in suggestions
                ]
            })
            
        except Exception as e:
            logger.error(f"Suggestions error: {e}")
            return web.json_response({
                "status": "error",
                "message": str(e)
            }, status=500)
    
    async def handle_autocomplete(self, request: web_request.Request) -> web.Response:
        """Handle autocomplete requests"""
        try:
            prefix = request.query.get('q', '')
            limit = min(int(request.query.get('limit', 10)), 50)
            
            suggestions = self.suggestion_engine.get_autocomplete(prefix, limit)
            
            return web.json_response({
                "status": "success",
                "prefix": prefix,
                "completions": [
                    {
                        "suggestion": completion.suggestion,
                        "type": completion.type,
                        "score": completion.score,
                        "highlights": completion.highlight_positions
                    }
                    for completion in suggestions
                ]
            })
            
        except Exception as e:
            logger.error(f"Autocomplete error: {e}")
            return web.json_response({
                "status": "error",
                "message": str(e)
            }, status=500)
    
    async def handle_save_search(self, request: web_request.Request) -> web.Response:
        """Handle save search requests"""
        try:
            data = await request.json()
            
            saved_search = self.saved_search_manager.save_search(
                user_id=data.get('user_id'),
                name=data.get('name'),
                query=data.get('query'),
                filters=data.get('filters'),
                facets=data.get('facets'),
                alert_enabled=data.get('alert_enabled', False),
                alert_frequency=data.get('alert_frequency', 'daily'),
                is_public=data.get('is_public', False),
                tags=data.get('tags', [])
            )
            
            return web.json_response({
                "status": "success",
                "saved_search": {
                    "id": saved_search.id,
                    "name": saved_search.name,
                    "query": saved_search.query,
                    "created_at": saved_search.created_at
                }
            })
            
        except Exception as e:
            logger.error(f"Save search error: {e}")
            return web.json_response({
                "status": "error",
                "message": str(e)
            }, status=500)
    
    async def handle_get_saved_searches(self, request: web_request.Request) -> web.Response:
        """Handle get saved searches requests"""
        try:
            user_id = request.match_info['user_id']
            
            saved_searches = self.saved_search_manager.get_user_searches(user_id)
            
            return web.json_response({
                "status": "success",
                "saved_searches": [
                    {
                        "id": search.id,
                        "name": search.name,
                        "query": search.query,
                        "filters": search.filters,
                        "created_at": search.created_at,
                        "execution_count": search.execution_count,
                        "alert_enabled": search.alert_enabled
                    }
                    for search in saved_searches
                ]
            })
            
        except Exception as e:
            logger.error(f"Get saved searches error: {e}")
            return web.json_response({
                "status": "error",
                "message": str(e)
            }, status=500)
    
    async def handle_delete_saved_search(self, request: web_request.Request) -> web.Response:
        """Handle delete saved search requests"""
        try:
            search_id = request.match_info['search_id']
            user_id = request.query.get('user_id')
            
            success = self.saved_search_manager.delete_saved_search(search_id, user_id)
            
            return web.json_response({
                "status": "success" if success else "error",
                "message": "Search deleted" if success else "Search not found or unauthorized"
            })
            
        except Exception as e:
            logger.error(f"Delete saved search error: {e}")
            return web.json_response({
                "status": "error",
                "message": str(e)
            }, status=500)
    
    async def handle_analytics(self, request: web_request.Request) -> web.Response:
        """Handle analytics requests"""
        try:
            analytics = self.unified_engine.get_search_analytics()
            
            return web.json_response({
                "status": "success",
                "analytics": analytics
            })
            
        except Exception as e:
            logger.error(f"Analytics error: {e}")
            return web.json_response({
                "status": "error",
                "message": str(e)
            }, status=500)
    
    async def handle_popular_queries(self, request: web_request.Request) -> web.Response:
        """Handle popular queries requests"""
        try:
            limit = min(int(request.query.get('limit', 20)), 100)
            
            popular_queries = self.unified_engine.get_popular_queries(limit)
            
            return web.json_response({
                "status": "success",
                "popular_queries": [
                    {"query": query, "count": count}
                    for query, count in popular_queries
                ]
            })
            
        except Exception as e:
            logger.error(f"Popular queries error: {e}")
            return web.json_response({
                "status": "error",
                "message": str(e)
            }, status=500)
    
    async def handle_health_check(self, request: web_request.Request) -> web.Response:
        """Handle health check requests"""
        uptime = time.time() - self.start_time
        
        return web.json_response({
            "status": "healthy",
            "uptime_seconds": uptime,
            "services": {
                "unified_search": "operational",
                "semantic_search": "operational",
                "multimodal_search": "operational",
                "federated_search": "operational",
                "suggestion_engine": "operational",
                "ranking_model": "operational" if self.ranking_model.is_trained else "training",
                "multilingual_search": "operational",
                "fuzzy_search": "operational"
            }
        })
    
    async def handle_stats(self, request: web_request.Request) -> web.Response:
        """Handle comprehensive statistics"""
        try:
            uptime = time.time() - self.start_time
            
            stats = {
                "system": {
                    "uptime_seconds": uptime,
                    "start_time": self.start_time
                },
                "unified_search": self.unified_engine.stats,
                "semantic_search": self.semantic_engine.get_stats(),
                "multimodal_search": self.multimodal_engine.get_stats(),
                "federated_search": self.federated_engine.get_stats(),
                "suggestion_engine": self.suggestion_engine.get_stats(),
                "saved_searches": self.saved_search_manager.get_stats(),
                "ranking_model": self.ranking_model.get_model_info(),
                "fuzzy_search": self.fuzzy_engine.get_stats(),
                "multilingual_search": self.multilingual_engine.get_stats(),
                "indexing": self.index_manager.indexing_stats
            }
            
            return web.json_response({
                "status": "success",
                "stats": stats
            })
            
        except Exception as e:
            logger.error(f"Stats error: {e}")
            return web.json_response({
                "status": "error",
                "message": str(e)
            }, status=500)
    
    async def handle_reindex(self, request: web_request.Request) -> web.Response:
        """Handle reindexing requests"""
        try:
            # Start reindexing in background
            asyncio.create_task(self.index_manager.index_all_services())
            
            return web.json_response({
                "status": "success",
                "message": "Reindexing started in background"
            })
            
        except Exception as e:
            logger.error(f"Reindex error: {e}")
            return web.json_response({
                "status": "error",
                "message": str(e)
            }, status=500)
    
    async def handle_add_document(self, request: web_request.Request) -> web.Response:
        """Handle add document requests"""
        try:
            data = await request.json()
            
            document = SearchDocument(
                id=data.get('id', str(uuid.uuid4())),
                service_id=data.get('service_id', 'custom'),
                content_type=ContentType(data.get('content_type', 'document')),
                title=data.get('title', ''),
                content=data.get('content', ''),
                metadata=data.get('metadata', {}),
                language=data.get('language', 'en'),
                tags=data.get('tags', [])
            )
            
            # Index in all engines
            await self.index_manager._index_document_all_engines(document)
            
            return web.json_response({
                "status": "success",
                "document_id": document.id,
                "message": "Document indexed successfully"
            })
            
        except Exception as e:
            logger.error(f"Add document error: {e}")
            return web.json_response({
                "status": "error",
                "message": str(e)
            }, status=500)
    
    async def handle_delete_document(self, request: web_request.Request) -> web.Response:
        """Handle delete document requests"""
        try:
            doc_id = request.match_info['doc_id']
            
            # Remove from all engines
            self.unified_engine.remove_document(doc_id)
            self.semantic_engine.remove_document(doc_id)
            self.multimodal_engine.remove_document(doc_id)
            self.fuzzy_engine.remove_document(doc_id)
            
            return web.json_response({
                "status": "success",
                "message": "Document removed from all indexes"
            })
            
        except Exception as e:
            logger.error(f"Delete document error: {e}")
            return web.json_response({
                "status": "error",
                "message": str(e)
            }, status=500)
    
    async def handle_dashboard(self, request: web_request.Request) -> web.Response:
        """Handle dashboard requests"""
        dashboard_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>ActiveLog Unified Search Engine</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
                .container { max-width: 1200px; margin: 0 auto; }
                .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
                .search-box { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .features { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 20px; }
                .feature { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .stats { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                input[type="text"] { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 16px; }
                button { background: #3498db; color: white; padding: 12px 24px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; margin-left: 10px; }
                button:hover { background: #2980b9; }
                .emoji { font-size: 24px; margin-right: 10px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔍 ActiveLog Unified Search Engine</h1>
                    <p>Comprehensive search across all 70+ services with ML-powered ranking</p>
                </div>
                
                <div class="search-box">
                    <h2>🚀 Try the Search API</h2>
                    <input type="text" id="searchQuery" placeholder="Enter your search query..." value="business meeting notes">
                    <button onclick="performSearch()">Search</button>
                    <div id="searchResults" style="margin-top: 20px;"></div>
                </div>
                
                <div class="features">
                    <div class="feature">
                        <h3><span class="emoji">🧠</span>Semantic Search</h3>
                        <p>Advanced semantic understanding using embeddings and vector similarity for meaning-based search.</p>
                    </div>
                    <div class="feature">
                        <h3><span class="emoji">🎭</span>Multi-modal Search</h3>
                        <p>Search across text, images, audio, and video content with unified ranking.</p>
                    </div>
                    <div class="feature">
                        <h3><span class="emoji">🔧</span>Faceted Search</h3>
                        <p>Dynamic filtering by service, content type, date, tags, and custom metadata.</p>
                    </div>
                    <div class="feature">
                        <h3><span class="emoji">💡</span>Smart Suggestions</h3>
                        <p>Intelligent autocomplete and query suggestions based on usage patterns.</p>
                    </div>
                    <div class="feature">
                        <h3><span class="emoji">💾</span>Saved Searches</h3>
                        <p>Save searches with alerts and notifications for new matching content.</p>
                    </div>
                    <div class="feature">
                        <h3><span class="emoji">🌐</span>Federated Search</h3>
                        <p>Search external sources like Wikipedia, GitHub, arXiv, and news APIs.</p>
                    </div>
                    <div class="feature">
                        <h3><span class="emoji">🗣️</span>Natural Language</h3>
                        <p>Parse natural language queries with intent recognition and entity extraction.</p>
                    </div>
                    <div class="feature">
                        <h3><span class="emoji">🎯</span>ML Ranking</h3>
                        <p>Machine learning-based result ranking with user behavior analysis.</p>
                    </div>
                    <div class="feature">
                        <h3><span class="emoji">🔀</span>Fuzzy Matching</h3>
                        <p>Phonetic and fuzzy search with edit distance and wildcard support.</p>
                    </div>
                    <div class="feature">
                        <h3><span class="emoji">🌍</span>Cross-lingual</h3>
                        <p>Search across multiple languages with automatic translation and detection.</p>
                    </div>
                </div>
                
                <div class="stats">
                    <h2>📊 API Endpoints</h2>
                    <ul>
                        <li><strong>POST /search</strong> - Unified search across all capabilities</li>
                        <li><strong>POST /search/semantic</strong> - Semantic search only</li>
                        <li><strong>POST /search/multimodal</strong> - Multi-modal search</li>
                        <li><strong>POST /search/federated</strong> - External source search</li>
                        <li><strong>GET /suggest?q=query</strong> - Search suggestions</li>
                        <li><strong>GET /autocomplete?q=prefix</strong> - Query completion</li>
                        <li><strong>GET /stats</strong> - Comprehensive system statistics</li>
                        <li><strong>GET /health</strong> - Health check</li>
                    </ul>
                </div>
            </div>
            
            <script>
            async function performSearch() {
                const query = document.getElementById('searchQuery').value;
                const resultsDiv = document.getElementById('searchResults');
                
                resultsDiv.innerHTML = '<p>Searching...</p>';
                
                try {
                    const response = await fetch('/search', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            query: query,
                            search_type: 'semantic',
                            limit: 10
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (data.status === 'success') {
                        let html = '<h3>Search Results (' + data.total_hits + ' found in ' + data.query_time_ms.toFixed(1) + 'ms)</h3>';
                        
                        data.results.forEach(result => {
                            html += '<div style="border: 1px solid #ddd; padding: 10px; margin: 10px 0; border-radius: 4px;">';
                            html += '<h4>' + result.title + '</h4>';
                            html += '<p>' + result.content_snippet + '</p>';
                            html += '<small>Service: ' + result.service_id + ' | Score: ' + result.score.toFixed(3) + '</small>';
                            html += '</div>';
                        });
                        
                        resultsDiv.innerHTML = html;
                    } else {
                        resultsDiv.innerHTML = '<p style="color: red;">Search failed: ' + data.message + '</p>';
                    }
                } catch (error) {
                    resultsDiv.innerHTML = '<p style="color: red;">Error: ' + error.message + '</p>';
                }
            }
            </script>
        </body>
        </html>
        """
        
        return web.Response(text=dashboard_html, content_type='text/html')
    
    async def start_server(self):
        """Start the search server"""
        logger.info("🚀 Starting ActiveLog Unified Search Engine")
        logger.info("🔍 System Features:")
        logger.info("  • Semantic search across all 70+ services")
        logger.info("  • Multi-modal search (text, image, audio, video)")
        logger.info("  • Faceted search with dynamic filters") 
        logger.info("  • Search suggestions and autocomplete")
        logger.info("  • Saved search functionality with alerts")
        logger.info("  • Search analytics and popular queries")
        logger.info("  • Federated search across external sources")
        logger.info("  • Natural language query parsing")
        logger.info("  • ML-based result ranking")
        logger.info("  • Phonetic/fuzzy matching")
        logger.info("  • Cross-lingual search")
        logger.info("="*80)
        
        # Start indexing in background
        logger.info("📚 Starting background indexing...")
        asyncio.create_task(self.index_manager.index_all_services())
        
        # Start web server
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        logger.info(f"✅ Unified Search Engine running on http://{self.host}:{self.port}")
        logger.info("🌐 Dashboard available at http://localhost:8102/")
        
        # Keep server running
        try:
            while True:
                await asyncio.sleep(3600)  # Sleep for 1 hour
        except KeyboardInterrupt:
            logger.info("👋 Shutting down search engine...")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ActiveLog Unified Search Engine")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=8102, help="Server port")
    args = parser.parse_args()
    
    # Create and start server
    server = UnifiedSearchServer(host=args.host, port=args.port)
    
    try:
        asyncio.run(server.start_server())
    except KeyboardInterrupt:
        logger.info("👋 Unified Search Engine stopped by user")
    except Exception as e:
        logger.error(f"❌ Failed to start Unified Search Engine: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()