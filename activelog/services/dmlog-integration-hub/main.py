"""
DMLog Integration Hub
Comprehensive integration hub for all DMLog (Dungeon Master Log) services
Connects and orchestrates all D&D and tabletop gaming services
Port: 8018
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from aiohttp import web, ClientSession
import uuid

class DMLogIntegrationHub:
    """Central hub for integrating all DMLog services"""
    
    def __init__(self, port: int = 8018, host: str = '0.0.0.0'):
        self.port = port
        self.host = host
        self.app = web.Application()
        self.client_session: Optional[ClientSession] = None
        
        # DMLog service endpoints
        self.dmlog_services = {
            'core': 'http://localhost:8019',           # dmlog-core
            'ai_dm': 'http://localhost:8020',          # dmlog-ai-dm  
            'battle': 'http://localhost:8021',         # dmlog-battle
            'characters': 'http://localhost:8022',     # dmlog-characters
            'session': 'http://localhost:8023',        # dmlog-session
            'templates': 'http://localhost:8024',      # dmlog-templates
            'world': 'http://localhost:8025',          # dmlog-world
            'player': 'http://localhost:8026',         # dmlog-player
            'marketplace': 'http://localhost:8027',    # dmlog-marketplace
            'converter': 'http://localhost:8028',      # dmlog-converter
            'gamedev': 'http://localhost:8029',        # dmlog-gamedev
            'stream': 'http://localhost:8030'          # dmlog-stream
        }
        
        # Central data stores
        self.campaigns = {}
        self.active_sessions = {}
        self.players = {}
        self.characters = {}
        self.dm_accounts = {}
        self.game_assets = {}
        self.streaming_sessions = {}
        
        # Setup routes and middleware
        self.setup_routes()
        self.setup_middleware()
        
    def setup_middleware(self):
        """Setup middleware"""
        async def cors_middleware(request, handler):
            response = await handler(request)
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            return response
        
        self.app.middlewares.append(cors_middleware)
    
    def setup_routes(self):
        """Setup all API routes"""
        # Health and status
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/api/status', self.get_status)
        self.app.router.add_get('/api/services/status', self.get_services_status)
        
        # Dashboard
        self.app.router.add_get('/', self.serve_dashboard)
        self.app.router.add_get('/dashboard', self.serve_dashboard)
        
        # Campaign Management (Integrated)
        self.app.router.add_post('/api/campaigns/create', self.create_integrated_campaign)
        self.app.router.add_get('/api/campaigns', self.list_campaigns)
        self.app.router.add_get('/api/campaigns/{campaign_id}', self.get_campaign_details)
        self.app.router.add_put('/api/campaigns/{campaign_id}', self.update_campaign)
        self.app.router.add_delete('/api/campaigns/{campaign_id}', self.delete_campaign)
        
        # Session Management (Integrated)
        self.app.router.add_post('/api/sessions/start', self.start_integrated_session)
        self.app.router.add_get('/api/sessions/active', self.get_active_sessions)
        self.app.router.add_get('/api/sessions/{session_id}', self.get_session_details)
        self.app.router.add_post('/api/sessions/{session_id}/end', self.end_session)
        self.app.router.add_post('/api/sessions/{session_id}/stream', self.start_session_stream)
        
        # Character Management (Integrated)
        self.app.router.add_post('/api/characters/create', self.create_integrated_character)
        self.app.router.add_get('/api/characters/{character_id}', self.get_character_details)
        self.app.router.add_put('/api/characters/{character_id}', self.update_character)
        self.app.router.add_get('/api/players/{player_id}/characters', self.get_player_characters)
        
        # AI DM Integration
        self.app.router.add_post('/api/ai-dm/assist', self.get_ai_dm_assistance)
        self.app.router.add_post('/api/ai-dm/generate-content', self.generate_ai_content)
        self.app.router.add_post('/api/ai-dm/analyze-session', self.analyze_session_with_ai)
        
        # Battle System Integration
        self.app.router.add_post('/api/battle/start', self.start_integrated_battle)
        self.app.router.add_get('/api/battle/{battle_id}', self.get_battle_status)
        self.app.router.add_post('/api/battle/{battle_id}/action', self.process_battle_action)
        self.app.router.add_post('/api/battle/{battle_id}/end', self.end_battle)
        
        # World Building Integration
        self.app.router.add_post('/api/world/create-location', self.create_integrated_location)
        self.app.router.add_get('/api/world/{world_id}/locations', self.get_world_locations)
        self.app.router.add_post('/api/world/generate-content', self.generate_world_content)
        
        # Template and Content Generation
        self.app.router.add_get('/api/templates/categories', self.get_template_categories)
        self.app.router.add_get('/api/templates/{category}', self.get_category_templates)
        self.app.router.add_post('/api/templates/generate', self.generate_from_template)
        
        # Marketplace Integration
        self.app.router.add_get('/api/marketplace/browse', self.browse_marketplace)
        self.app.router.add_post('/api/marketplace/purchase', self.purchase_marketplace_item)
        self.app.router.add_get('/api/marketplace/user/{user_id}/library', self.get_user_library)
        
        # Player Tools Integration
        self.app.router.add_get('/api/player/{player_id}/dashboard', self.get_player_dashboard)
        self.app.router.add_post('/api/player/{player_id}/journal/entry', self.add_journal_entry)
        self.app.router.add_get('/api/player/{player_id}/inventory', self.get_player_inventory)
        
        # Cross-Service Operations
        self.app.router.add_post('/api/integrated/quick-campaign', self.create_quick_campaign)
        self.app.router.add_post('/api/integrated/session-prep', self.prepare_session_integrated)
        self.app.router.add_get('/api/integrated/overview', self.get_integrated_overview)
        
        # Service Communication Bridge
        self.app.router.add_post('/api/bridge/service-request', self.bridge_service_request)
        self.app.router.add_get('/api/bridge/service-status/{service_name}', self.get_bridge_service_status)
        
    # Core Integration Methods
    async def make_service_request(self, service: str, endpoint: str, method: str = 'GET', data: Dict = None) -> Dict:
        """Make request to a specific DMLog service"""
        if service not in self.dmlog_services:
            return {"error": f"Service {service} not found"}
        
        if not self.client_session:
            self.client_session = ClientSession()
        
        url = f"{self.dmlog_services[service]}{endpoint}"
        
        try:
            if method.upper() == 'POST':
                async with self.client_session.post(url, json=data, timeout=10) as response:
                    return await response.json()
            elif method.upper() == 'PUT':
                async with self.client_session.put(url, json=data, timeout=10) as response:
                    return await response.json()
            elif method.upper() == 'DELETE':
                async with self.client_session.delete(url, timeout=10) as response:
                    return await response.json()
            else:
                async with self.client_session.get(url, timeout=10) as response:
                    return await response.json()
        except Exception as e:
            logging.error(f"Service request to {service} failed: {e}")
            return {"error": f"Service {service} unavailable", "fallback": True}
    
    async def make_parallel_requests(self, requests: List[Dict]) -> List[Dict]:
        """Make multiple service requests in parallel"""
        tasks = []
        for req in requests:
            task = self.make_service_request(
                req['service'], 
                req['endpoint'], 
                req.get('method', 'GET'), 
                req.get('data')
            )
            tasks.append(task)
        
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    # API Handlers
    async def health_check(self, request):
        """Health check endpoint"""
        # Check all services
        service_health = {}
        for service_name in self.dmlog_services.keys():
            health = await self.make_service_request(service_name, '/health')
            service_health[service_name] = "healthy" if not health.get('error') else "unhealthy"
        
        healthy_services = sum(1 for status in service_health.values() if status == "healthy")
        total_services = len(service_health)
        
        return web.json_response({
            "status": "healthy" if healthy_services > total_services * 0.7 else "degraded",
            "service": "DMLog Integration Hub",
            "port": self.port,
            "timestamp": datetime.now().isoformat(),
            "services": service_health,
            "health_score": f"{healthy_services}/{total_services}",
            "integration_status": "active"
        })
    
    async def get_status(self, request):
        """Get comprehensive system status"""
        # Get status from all services
        status_requests = [
            {'service': service, 'endpoint': '/api/status'} 
            for service in self.dmlog_services.keys()
        ]
        
        service_statuses = await self.make_parallel_requests(status_requests)
        
        # Aggregate metrics
        total_campaigns = len(self.campaigns)
        active_sessions = len(self.active_sessions)
        total_players = len(self.players)
        total_characters = len(self.characters)
        
        return web.json_response({
            "service": "DMLog Integration Hub",
            "version": "1.0.0",
            "port": self.port,
            "status": "running",
            "uptime": datetime.now().isoformat(),
            "integration_metrics": {
                "total_campaigns": total_campaigns,
                "active_sessions": active_sessions,
                "connected_players": total_players,
                "managed_characters": total_characters,
                "streaming_sessions": len(self.streaming_sessions),
                "marketplace_items": len(self.game_assets)
            },
            "service_integration": {
                service: {"status": "connected" if not status.get('error') else "disconnected", "data": status}
                for service, status in zip(self.dmlog_services.keys(), service_statuses)
            },
            "features": {
                "integrated_campaigns": "active",
                "ai_dm_assistance": "active",
                "cross_service_battles": "active",
                "unified_character_management": "active",
                "integrated_streaming": "active",
                "marketplace_integration": "active",
                "world_building_tools": "active",
                "template_system": "active"
            }
        })
    
    async def create_integrated_campaign(self, request):
        """Create a new campaign with full service integration"""
        try:
            data = await request.json()
            campaign_id = str(uuid.uuid4())
            
            # Create campaign in core service
            campaign_data = {
                "name": data.get('name', 'Untitled Campaign'),
                "description": data.get('description', ''),
                "dm_id": data.get('dm_id'),
                "system": data.get('system', 'D&D 5e'),
                "players": data.get('players', []),
                "settings": data.get('settings', {})
            }
            
            # Parallel creation across services
            creation_requests = [
                {'service': 'core', 'endpoint': '/api/campaigns', 'method': 'POST', 'data': campaign_data},
                {'service': 'world', 'endpoint': '/api/worlds', 'method': 'POST', 'data': {
                    'campaign_id': campaign_id,
                    'name': f"{campaign_data['name']} World",
                    'theme': data.get('world_theme', 'fantasy')
                }},
                {'service': 'templates', 'endpoint': '/api/campaign-templates/initialize', 'method': 'POST', 'data': {
                    'campaign_id': campaign_id,
                    'system': campaign_data['system']
                }}
            ]
            
            results = await self.make_parallel_requests(creation_requests)
            
            # Store integrated campaign
            integrated_campaign = {
                "campaign_id": campaign_id,
                "basic_info": campaign_data,
                "core_service_id": results[0].get('campaign_id') if not results[0].get('error') else None,
                "world_id": results[1].get('world_id') if not results[1].get('error') else None,
                "template_set_id": results[2].get('template_set_id') if not results[2].get('error') else None,
                "created_at": datetime.now().isoformat(),
                "services_integrated": {
                    'core': not results[0].get('error'),
                    'world': not results[1].get('error'),
                    'templates': not results[2].get('error')
                },
                "sessions": [],
                "characters": [],
                "status": "active"
            }
            
            self.campaigns[campaign_id] = integrated_campaign
            
            return web.json_response({
                "success": True,
                "campaign_id": campaign_id,
                "integration_status": integrated_campaign["services_integrated"],
                "world_id": integrated_campaign["world_id"],
                "message": "Integrated campaign created successfully"
            })
            
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)
    
    async def start_integrated_session(self, request):
        """Start a fully integrated gaming session"""
        try:
            data = await request.json()
            session_id = str(uuid.uuid4())
            campaign_id = data.get('campaign_id')
            
            if campaign_id not in self.campaigns:
                return web.json_response({"error": "Campaign not found"}, status=404)
            
            campaign = self.campaigns[campaign_id]
            
            # Session data
            session_data = {
                "session_id": session_id,
                "campaign_id": campaign_id,
                "dm_id": data.get('dm_id'),
                "players": data.get('players', []),
                "planned_duration": data.get('duration_minutes', 180),
                "session_type": data.get('type', 'regular'),  # regular, one-shot, tournament
                "streaming_enabled": data.get('enable_streaming', False)
            }
            
            # Start session across services
            session_requests = [
                {'service': 'session', 'endpoint': '/api/sessions/start', 'method': 'POST', 'data': session_data},
                {'service': 'ai_dm', 'endpoint': '/api/sessions/initialize', 'method': 'POST', 'data': {
                    'session_id': session_id,
                    'campaign_context': campaign['basic_info']
                }},
                {'service': 'core', 'endpoint': f'/api/campaigns/{campaign_id}/sessions', 'method': 'POST', 'data': {
                    'session_id': session_id,
                    'start_time': datetime.now().isoformat()
                }}
            ]
            
            # Add streaming if enabled
            if session_data['streaming_enabled']:
                session_requests.append({
                    'service': 'stream', 
                    'endpoint': '/api/streams/setup', 
                    'method': 'POST', 
                    'data': {
                        'session_id': session_id,
                        'campaign_name': campaign['basic_info']['name'],
                        'stream_settings': data.get('stream_settings', {})
                    }
                })
            
            results = await self.make_parallel_requests(session_requests)
            
            # Create integrated session
            integrated_session = {
                "session_id": session_id,
                "campaign_id": campaign_id,
                "session_data": session_data,
                "started_at": datetime.now().isoformat(),
                "status": "active",
                "services": {
                    'session': not results[0].get('error'),
                    'ai_dm': not results[1].get('error'),
                    'core': not results[2].get('error'),
                    'stream': not results[3].get('error') if len(results) > 3 else False
                },
                "service_ids": {
                    'session_service_id': results[0].get('session_id') if not results[0].get('error') else None,
                    'ai_context_id': results[1].get('context_id') if not results[1].get('error') else None,
                    'stream_id': results[3].get('stream_id') if len(results) > 3 and not results[3].get('error') else None
                },
                "battle_encounters": [],
                "characters_in_session": [],
                "notes": [],
                "highlights": []
            }
            
            self.active_sessions[session_id] = integrated_session
            self.campaigns[campaign_id]["sessions"].append(session_id)
            
            return web.json_response({
                "success": True,
                "session_id": session_id,
                "integration_status": integrated_session["services"],
                "stream_url": f"/api/streams/{results[3].get('stream_id')}" if len(results) > 3 and not results[3].get('error') else None,
                "ai_dm_ready": integrated_session["services"]["ai_dm"],
                "message": "Integrated session started successfully"
            })
            
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)
    
    async def create_integrated_character(self, request):
        """Create character with full service integration"""
        try:
            data = await request.json()
            character_id = str(uuid.uuid4())
            
            # Character creation requests
            character_requests = [
                {'service': 'characters', 'endpoint': '/api/characters', 'method': 'POST', 'data': data},
                {'service': 'core', 'endpoint': '/api/characters', 'method': 'POST', 'data': {
                    'character_id': character_id,
                    'name': data.get('name'),
                    'class': data.get('character_class'),
                    'level': data.get('level', 1),
                    'player_id': data.get('player_id')
                }}
            ]
            
            # Add to player service if player_id provided
            if data.get('player_id'):
                character_requests.append({
                    'service': 'player',
                    'endpoint': f'/api/players/{data["player_id"]}/characters',
                    'method': 'POST',
                    'data': {'character_id': character_id, 'character_data': data}
                })
            
            results = await self.make_parallel_requests(character_requests)
            
            # Store integrated character
            integrated_character = {
                "character_id": character_id,
                "character_data": data,
                "created_at": datetime.now().isoformat(),
                "services_integrated": {
                    'characters': not results[0].get('error'),
                    'core': not results[1].get('error'),
                    'player': not results[2].get('error') if len(results) > 2 else False
                },
                "service_ids": {
                    'character_service_id': results[0].get('character_id') if not results[0].get('error') else None,
                    'core_character_id': results[1].get('character_id') if not results[1].get('error') else None
                }
            }
            
            self.characters[character_id] = integrated_character
            
            return web.json_response({
                "success": True,
                "character_id": character_id,
                "integration_status": integrated_character["services_integrated"],
                "message": "Integrated character created successfully"
            })
            
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)
    
    async def get_ai_dm_assistance(self, request):
        """Get AI DM assistance for current situation"""
        try:
            data = await request.json()
            session_id = data.get('session_id')
            assistance_type = data.get('type', 'general')  # general, combat, roleplay, rules
            context = data.get('context', {})
            
            # Get session context if available
            session_context = {}
            if session_id and session_id in self.active_sessions:
                session = self.active_sessions[session_id]
                session_context = {
                    'campaign_id': session['campaign_id'],
                    'current_situation': context,
                    'characters_present': session['characters_in_session'],
                    'session_duration': datetime.now().isoformat()
                }
            
            # Request AI assistance
            ai_request = {
                'session_id': session_id,
                'assistance_type': assistance_type,
                'context': session_context,
                'user_query': data.get('query', '')
            }
            
            ai_response = await self.make_service_request('ai_dm', '/api/assistance', 'POST', ai_request)
            
            return web.json_response({
                "success": True,
                "assistance": ai_response.get('assistance', 'AI assistance unavailable'),
                "suggestions": ai_response.get('suggestions', []),
                "generated_content": ai_response.get('content', {}),
                "session_id": session_id
            })
            
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)
    
    async def start_integrated_battle(self, request):
        """Start integrated battle encounter"""
        try:
            data = await request.json()
            battle_id = str(uuid.uuid4())
            session_id = data.get('session_id')
            
            if session_id and session_id not in self.active_sessions:
                return web.json_response({"error": "Session not found"}, status=404)
            
            # Battle setup
            battle_data = {
                'battle_id': battle_id,
                'session_id': session_id,
                'participants': data.get('participants', []),
                'environment': data.get('environment', {}),
                'initial_conditions': data.get('conditions', {})
            }
            
            # Start battle in battle service
            battle_response = await self.make_service_request('battle', '/api/battles/start', 'POST', battle_data)
            
            # Update session with battle
            if session_id and session_id in self.active_sessions:
                self.active_sessions[session_id]['battle_encounters'].append(battle_id)
            
            return web.json_response({
                "success": True,
                "battle_id": battle_id,
                "session_id": session_id,
                "battle_status": battle_response.get('status', 'unknown'),
                "message": "Integrated battle started"
            })
            
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)
    
    async def create_quick_campaign(self, request):
        """Create a quick campaign with AI assistance"""
        try:
            data = await request.json()
            
            # Generate campaign concept with AI
            concept_request = {
                'theme': data.get('theme', 'fantasy'),
                'system': data.get('system', 'D&D 5e'),
                'player_count': data.get('player_count', 4),
                'experience_level': data.get('experience', 'beginner'),
                'session_length': data.get('session_length', 'medium'),
                'preferences': data.get('preferences', {})
            }
            
            ai_concept = await self.make_service_request('templates', '/api/generate/quick-campaign', 'POST', concept_request)
            
            if not ai_concept.get('error'):
                # Create campaign with generated content
                campaign_data = {
                    'name': ai_concept.get('name', 'Generated Campaign'),
                    'description': ai_concept.get('description', ''),
                    'dm_id': data.get('dm_id'),
                    'system': concept_request['system'],
                    'players': data.get('players', []),
                    'world_theme': ai_concept.get('world_theme', 'fantasy'),
                    'settings': ai_concept.get('settings', {})
                }
                
                # Use the integrated campaign creation
                mock_request = type('MockRequest', (), {
                    'json': lambda: asyncio.create_task(asyncio.coroutine(lambda: campaign_data)())
                })()
                
                return await self.create_integrated_campaign(mock_request)
            else:
                return web.json_response({"error": "AI campaign generation failed"}, status=500)
                
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)
    
    async def get_integrated_overview(self, request):
        """Get comprehensive overview of all DMLog services"""
        # Collect data from all services
        overview_requests = [
            {'service': service, 'endpoint': '/api/overview'} 
            for service in self.dmlog_services.keys()
        ]
        
        service_overviews = await self.make_parallel_requests(overview_requests)
        
        return web.json_response({
            "dmlog_integration_overview": {
                "total_campaigns": len(self.campaigns),
                "active_sessions": len(self.active_sessions),
                "managed_characters": len(self.characters),
                "connected_players": len(self.players),
                "streaming_sessions": len(self.streaming_sessions),
                "marketplace_assets": len(self.game_assets)
            },
            "service_overviews": {
                service: overview for service, overview in zip(self.dmlog_services.keys(), service_overviews)
            },
            "integration_health": {
                "services_online": sum(1 for overview in service_overviews if not overview.get('error')),
                "total_services": len(self.dmlog_services),
                "last_checked": datetime.now().isoformat()
            },
            "features_available": {
                "integrated_campaigns": True,
                "ai_dm_assistance": True,
                "cross_service_battles": True,
                "streaming_integration": True,
                "marketplace_access": True,
                "template_generation": True,
                "world_building": True,
                "character_management": True
            }
        })
    
    async def serve_dashboard(self, request):
        """Serve DMLog integration dashboard"""
        dashboard_html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>DMLog Integration Hub</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #1a1a2e; color: #eee; }
                .header { background: linear-gradient(135deg, #16213e 0%, #0f3460 100%); color: white; padding: 2rem 1rem; text-align: center; }
                .header h1 { font-size: 2.5rem; margin-bottom: 0.5rem; }
                .header p { font-size: 1.1rem; opacity: 0.9; }
                .status { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.9rem; font-weight: 500; margin-top: 1rem; }
                .status.active { background: #22543d; color: #c6f6d5; }
                .container { max-width: 1400px; margin: 0 auto; padding: 2rem 1rem; }
                .services-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }
                .service-card { background: #16213e; border-radius: 12px; padding: 1.5rem; border: 1px solid #0f3460; transition: transform 0.2s; }
                .service-card:hover { transform: translateY(-2px); border-color: #e53e3e; }
                .service-name { font-size: 1.2rem; font-weight: bold; margin-bottom: 0.5rem; color: #90cdf4; }
                .service-status { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 15px; font-size: 0.8rem; margin-bottom: 1rem; }
                .service-status.online { background: #22543d; color: #c6f6d5; }
                .service-status.offline { background: #742a2a; color: #feb2b2; }
                .service-description { color: #cbd5e0; font-size: 0.9rem; line-height: 1.4; }
                .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
                .metric-card { background: #16213e; padding: 1.5rem; border-radius: 8px; border: 1px solid #0f3460; text-align: center; }
                .metric-value { font-size: 2.5rem; font-weight: bold; color: #90cdf4; margin-bottom: 0.5rem; }
                .metric-label { color: #a0aec0; font-size: 0.9rem; }
                .integration-features { background: #16213e; border-radius: 12px; padding: 2rem; border: 1px solid #0f3460; }
                .features-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem; margin-top: 1rem; }
                .feature-item { padding: 1rem; background: #1a202c; border-radius: 8px; border-left: 4px solid #90cdf4; }
                .feature-title { font-weight: bold; color: #90cdf4; margin-bottom: 0.5rem; }
                .feature-description { color: #cbd5e0; font-size: 0.9rem; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🐉 DMLog Integration Hub</h1>
                <p>Comprehensive integration platform for all Dungeon Master and tabletop gaming services</p>
                <div class="status active">Integration Active - Port 8018</div>
            </div>
            
            <div class="container">
                <div class="metrics" id="metrics">
                    <div class="metric-card">
                        <div class="metric-value" id="campaigns">-</div>
                        <div class="metric-label">Active Campaigns</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value" id="sessions">-</div>
                        <div class="metric-label">Live Sessions</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value" id="characters">-</div>
                        <div class="metric-label">Characters</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value" id="services-online">-</div>
                        <div class="metric-label">Services Online</div>
                    </div>
                </div>
                
                <div class="services-grid">
                    <div class="service-card">
                        <div class="service-name">🎲 DMLog Core</div>
                        <div class="service-status online">Online</div>
                        <div class="service-description">Core campaign and rules management system</div>
                    </div>
                    <div class="service-card">
                        <div class="service-name">🧠 AI Dungeon Master</div>
                        <div class="service-status online">Online</div>
                        <div class="service-description">AI-powered DM assistance and content generation</div>
                    </div>
                    <div class="service-card">
                        <div class="service-name">⚔️ Battle System</div>
                        <div class="service-status online">Online</div>
                        <div class="service-description">Advanced combat and encounter management</div>
                    </div>
                    <div class="service-card">
                        <div class="service-name">👥 Character Management</div>
                        <div class="service-status online">Online</div>
                        <div class="service-description">Comprehensive character creation and management</div>
                    </div>
                    <div class="service-card">
                        <div class="service-name">🎮 Session Manager</div>
                        <div class="service-status online">Online</div>
                        <div class="service-description">Session planning, execution, and recording</div>
                    </div>
                    <div class="service-card">
                        <div class="service-name">📋 Template System</div>
                        <div class="service-status online">Online</div>
                        <div class="service-description">Adventure and content templates</div>
                    </div>
                    <div class="service-card">
                        <div class="service-name">🗺️ World Builder</div>
                        <div class="service-status online">Online</div>
                        <div class="service-description">World building and location management</div>
                    </div>
                    <div class="service-card">
                        <div class="service-name">👤 Player Tools</div>
                        <div class="service-status online">Online</div>
                        <div class="service-description">Player-focused tools and interfaces</div>
                    </div>
                    <div class="service-card">
                        <div class="service-name">🛒 Marketplace</div>
                        <div class="service-status online">Online</div>
                        <div class="service-description">Asset marketplace and content library</div>
                    </div>
                    <div class="service-card">
                        <div class="service-name">🎥 Stream Integration</div>
                        <div class="service-status online">Online</div>
                        <div class="service-description">Live streaming and recording capabilities</div>
                    </div>
                </div>
                
                <div class="integration-features">
                    <h3>🔗 Integration Features</h3>
                    <div class="features-grid">
                        <div class="feature-item">
                            <div class="feature-title">Unified Campaign Management</div>
                            <div class="feature-description">Create and manage campaigns across all services with one interface</div>
                        </div>
                        <div class="feature-item">
                            <div class="feature-title">Cross-Service Sessions</div>
                            <div class="feature-description">Sessions that automatically integrate AI, battle, streaming, and more</div>
                        </div>
                        <div class="feature-item">
                            <div class="feature-title">AI-Enhanced Gameplay</div>
                            <div class="feature-description">AI assistance for DMs with context from all active services</div>
                        </div>
                        <div class="feature-item">
                            <div class="feature-title">Integrated Character System</div>
                            <div class="feature-description">Characters that work seamlessly across combat, roleplay, and story</div>
                        </div>
                        <div class="feature-item">
                            <div class="feature-title">Live Stream Integration</div>
                            <div class="feature-description">One-click streaming setup with all session context</div>
                        </div>
                        <div class="feature-item">
                            <div class="feature-title">Content Marketplace</div>
                            <div class="feature-description">Access and integrate purchased content across all services</div>
                        </div>
                    </div>
                </div>
                
                <div style="text-align: center; color: #a0aec0; margin-top: 3rem;">
                    <p>DMLog Integration Hub - Unifying the Tabletop Gaming Experience</p>
                    <p style="margin-top: 0.5rem;">API Status: <a href="/api/status" style="color: #90cdf4;">/api/status</a></p>
                </div>
            </div>
            
            <script>
                async function loadMetrics() {
                    try {
                        const response = await fetch('/api/integrated/overview');
                        const data = await response.json();
                        
                        if (data.dmlog_integration_overview) {
                            const overview = data.dmlog_integration_overview;
                            document.getElementById('campaigns').textContent = overview.total_campaigns || 0;
                            document.getElementById('sessions').textContent = overview.active_sessions || 0;
                            document.getElementById('characters').textContent = overview.managed_characters || 0;
                        }
                        
                        if (data.integration_health) {
                            document.getElementById('services-online').textContent = 
                                `${data.integration_health.services_online}/${data.integration_health.total_services}`;
                        }
                        
                    } catch (error) {
                        console.error('Failed to load metrics:', error);
                    }
                }
                
                loadMetrics();
                setInterval(loadMetrics, 30000);
            </script>
        </body>
        </html>
        """
        return web.Response(text=dashboard_html, content_type='text/html')
    
    # Additional placeholder methods for remaining endpoints
    async def get_services_status(self, request):
        return web.json_response({"services": self.dmlog_services, "status": "checking"})
    
    async def list_campaigns(self, request):
        return web.json_response({"campaigns": list(self.campaigns.values())})
    
    async def get_campaign_details(self, request):
        campaign_id = request.match_info['campaign_id']
        return web.json_response(self.campaigns.get(campaign_id, {"error": "Campaign not found"}))
    
    async def update_campaign(self, request):
        return web.json_response({"success": True})
    
    async def delete_campaign(self, request):
        return web.json_response({"success": True})
    
    async def get_active_sessions(self, request):
        return web.json_response({"sessions": list(self.active_sessions.values())})
    
    async def get_session_details(self, request):
        session_id = request.match_info['session_id']
        return web.json_response(self.active_sessions.get(session_id, {"error": "Session not found"}))
    
    async def end_session(self, request):
        return web.json_response({"success": True})
    
    async def start_session_stream(self, request):
        return web.json_response({"stream_started": True, "stream_url": "rtmp://stream.dmlog.com/live"})
    
    # More placeholder methods...
    async def get_character_details(self, request):
        character_id = request.match_info['character_id']
        return web.json_response(self.characters.get(character_id, {"error": "Character not found"}))
    
    async def update_character(self, request):
        return web.json_response({"success": True})
    
    async def get_player_characters(self, request):
        return web.json_response({"characters": []})
    
    async def generate_ai_content(self, request):
        return web.json_response({"content": "AI-generated content", "type": "adventure"})
    
    async def analyze_session_with_ai(self, request):
        return web.json_response({"analysis": "Session analysis", "suggestions": []})
    
    async def get_battle_status(self, request):
        return web.json_response({"status": "active", "turn": 1})
    
    async def process_battle_action(self, request):
        return web.json_response({"result": "success", "damage": 8})
    
    async def end_battle(self, request):
        return web.json_response({"battle_ended": True, "victor": "party"})
    
    async def create_integrated_location(self, request):
        return web.json_response({"location_created": True})
    
    async def get_world_locations(self, request):
        return web.json_response({"locations": []})
    
    async def generate_world_content(self, request):
        return web.json_response({"generated_content": {}})
    
    async def get_template_categories(self, request):
        return web.json_response({"categories": ["adventure", "character", "location", "encounter"]})
    
    async def get_category_templates(self, request):
        return web.json_response({"templates": []})
    
    async def generate_from_template(self, request):
        return web.json_response({"generated": True})
    
    async def browse_marketplace(self, request):
        return web.json_response({"items": []})
    
    async def purchase_marketplace_item(self, request):
        return web.json_response({"purchased": True})
    
    async def get_user_library(self, request):
        return web.json_response({"library": []})
    
    async def get_player_dashboard(self, request):
        return web.json_response({"dashboard": {}})
    
    async def add_journal_entry(self, request):
        return web.json_response({"entry_added": True})
    
    async def get_player_inventory(self, request):
        return web.json_response({"inventory": []})
    
    async def prepare_session_integrated(self, request):
        return web.json_response({"preparation_complete": True})
    
    async def bridge_service_request(self, request):
        data = await request.json()
        service = data.get('service')
        endpoint = data.get('endpoint')
        method = data.get('method', 'GET')
        payload = data.get('data')
        
        result = await self.make_service_request(service, endpoint, method, payload)
        return web.json_response(result)
    
    async def get_bridge_service_status(self, request):
        service_name = request.match_info['service_name']
        status = await self.make_service_request(service_name, '/health')
        return web.json_response({"service": service_name, "status": status})
    
    async def start_server(self):
        """Start the DMLog integration hub server"""
        try:
            # Initialize HTTP client session
            self.client_session = ClientSession()
            
            # Create and start web server
            runner = web.AppRunner(self.app)
            await runner.setup()
            
            site = web.TCPSite(runner, self.host, self.port)
            await site.start()
            
            print(f"🐉 DMLog Integration Hub started successfully!")
            print(f"📡 Server running on http://{self.host}:{self.port}")
            print(f"🎲 Integrating all DMLog services for unified tabletop gaming")
            print(f"📊 Dashboard available at http://{self.host}:{self.port}/dashboard")
            print(f"🔍 API status at http://{self.host}:{self.port}/api/status")
            print(f"💡 Health check at http://{self.host}:{self.port}/health")
            
            # Keep the server running
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Shutting down DMLog Integration Hub...")
            finally:
                await self.cleanup()
                await runner.cleanup()
                
        except Exception as e:
            logging.error(f"Failed to start server: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup server resources"""
        if self.client_session:
            await self.client_session.close()
        
        print("✅ DMLog Integration Hub shutdown complete")

# Main entry point
async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    hub = DMLogIntegrationHub(port=8018)
    await hub.start_server()

if __name__ == "__main__":
    asyncio.run(main())