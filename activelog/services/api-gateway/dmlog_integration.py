"""
DMlog SuperInstance API Gateway Integration
Registers DMlog services with the main API Gateway
"""

DMLOG_SERVICES = {
    "dmlog-core": {
        "url": "http://localhost:8012",
        "health_check": "/health",
        "routes": [
            "/api/v1/characters/enhance",
            "/api/v1/dm/rewards", 
            "/api/v1/campaigns/ai-generate",
            "/api/v1/cross-domain"
        ],
        "capabilities": [
            "rpg_rules_engine",
            "character_management",
            "cross_domain_gaming",
            "dm_reward_tracking",
            "ai_campaign_generation"
        ],
        "integration_points": {
            "user_management": "gaming_profiles",
            "ai_insights": "cross_domain_enhancement",
            "compute_capital": "dm_rewards",
            "dmlog_ai": "character_ai_enhancement"
        }
    },
    "dmlog-ai": {
        "url": "http://localhost:8097", 
        "health_check": "/health",
        "routes": [
            "/api/v1/character-enhancement",
            "/api/v1/campaign-ai"
        ],
        "capabilities": [
            "ai_powered_gaming",
            "cross_domain_character_analysis",
            "campaign_intelligence"
        ],
        "integration_points": {
            "dmlog_core": "character_enhancement",
            "ai_insights": "cross_domain_analysis",
            "user_management": "personality_insights"
        }
    },
    "dmlog-final": {
        "url": "http://localhost:8508",
        "health_check": "/health", 
        "routes": [
            "/api/v1/campaigns",
            "/api/v1/sessions",
            "/api/v1/marketplace"
        ],
        "capabilities": [
            "campaign_management",
            "real_time_multiplayer", 
            "community_marketplace",
            "3d_printing_integration"
        ],
        "integration_points": {
            "dmlog_core": "campaign_data",
            "user_management": "player_profiles",
            "compute_capital": "marketplace_economy"
        }
    }
}

def get_dmlog_route_mappings():
    """Get route mappings for DMlog services"""
    routes = {}
    for service, config in DMLOG_SERVICES.items():
        for route in config["routes"]:
            routes[route] = {
                "service": service,
                "url": config["url"],
                "capabilities": config["capabilities"]
            }
    return routes

def get_dmlog_health_checks():
    """Get health check URLs for all DMlog services"""
    return {
        service: f"{config['url']}{config['health_check']}"
        for service, config in DMLOG_SERVICES.items()
    }