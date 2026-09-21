#!/usr/bin/env python3
"""
SuperInstance API Management System
Intelligent routing, cost optimization, and comprehensive AI toolkit
"""

import os
import json
import sqlite3
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union
import requests
from dataclasses import dataclass
from enum import Enum
import hashlib

try:
    import anthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False

try:
    import replicate
    REPLICATE_AVAILABLE = True
except ImportError:
    REPLICATE_AVAILABLE = False

class APIServiceType(Enum):
    CHAT = "chat"
    IMAGE = "image" 
    VIDEO = "video"
    AUDIO = "audio"
    CODE = "code"
    ML = "machine_learning"
    GAME = "game_engine"
    DATA = "data_processing"

@dataclass
class APIService:
    name: str
    service_type: APIServiceType
    cost_per_request: float
    api_endpoint: str
    requires_key: bool
    rate_limit_per_hour: int = 1000
    quality_score: float = 1.0  # 0-1 scale

class SuperInstanceAPIManager:
    def __init__(self):
        self.db_path = "/tmp/superinstance_api_manager.db"
        self.init_database()
        
        # Core API services registry
        self.api_services = {
            # Chat & Language Models
            "claude": APIService("Claude", APIServiceType.CHAT, 0.015, "anthropic", True, 1000, 0.95),
            "gpt4": APIService("GPT-4", APIServiceType.CHAT, 0.03, "openai", True, 10000, 0.90),
            "gemini": APIService("Gemini Pro", APIServiceType.CHAT, 0.001, "google", True, 60, 0.85),
            
            # Image Generation & Processing
            "flux_dev": APIService("Flux Dev", APIServiceType.IMAGE, 0.055, "replicate", True, 100, 0.95),
            "flux_schnell": APIService("Flux Schnell", APIServiceType.IMAGE, 0.003, "replicate", True, 500, 0.85),
            "sdxl": APIService("SDXL", APIServiceType.IMAGE, 0.0095, "replicate", True, 200, 0.80),
            "midjourney": APIService("Midjourney", APIServiceType.IMAGE, 0.08, "replicate", True, 50, 0.98),
            "dall_e_3": APIService("DALL-E 3", APIServiceType.IMAGE, 0.04, "openai", True, 50, 0.90),
            
            # Video Generation
            "runway_ml": APIService("RunwayML", APIServiceType.VIDEO, 0.25, "replicate", True, 20, 0.95),
            "stable_video": APIService("Stable Video", APIServiceType.VIDEO, 0.15, "replicate", True, 30, 0.85),
            "luma_ai": APIService("Luma Dream Machine", APIServiceType.VIDEO, 0.12, "replicate", True, 25, 0.88),
            
            # Audio & Music
            "elevenlabs": APIService("ElevenLabs TTS", APIServiceType.AUDIO, 0.0015, "elevenlabs", True, 1000, 0.95),
            "whisper": APIService("Whisper STT", APIServiceType.AUDIO, 0.006, "openai", True, 500, 0.90),
            "musicgen": APIService("MusicGen", APIServiceType.AUDIO, 0.05, "replicate", True, 100, 0.85),
            "suno_ai": APIService("Suno AI Music", APIServiceType.AUDIO, 0.08, "replicate", True, 50, 0.92),
            
            # Code & Development
            "codestral": APIService("Codestral", APIServiceType.CODE, 0.001, "mistral", True, 1000, 0.90),
            "github_copilot": APIService("GitHub Copilot API", APIServiceType.CODE, 0.002, "github", True, 2000, 0.85),
            "tabnine": APIService("Tabnine Pro", APIServiceType.CODE, 0.0005, "tabnine", True, 5000, 0.80),
            
            # Machine Learning & Data
            "huggingface": APIService("HuggingFace Inference", APIServiceType.ML, 0.001, "huggingface", True, 1000, 0.85),
            "cohere": APIService("Cohere Embed/Classify", APIServiceType.ML, 0.0001, "cohere", True, 10000, 0.80),
            "pinecone": APIService("Pinecone Vector DB", APIServiceType.DATA, 0.0001, "pinecone", True, 100000, 0.90),
            
            # Game Engine APIs
            "unity_cloud": APIService("Unity Cloud Build", APIServiceType.GAME, 0.10, "unity", True, 100, 0.85),
            "photon": APIService("Photon Multiplayer", APIServiceType.GAME, 0.005, "photon", True, 1000, 0.90),
            "playfab": APIService("PlayFab Backend", APIServiceType.GAME, 0.001, "microsoft", True, 10000, 0.85),
        }
        
        # Load API keys from environment
        self.load_api_keys()
        
        # Usage tracking
        self.usage_limits = {
            "claude_hourly": 100,  # Based on your 5-hour limit
            "default_hourly": 1000
        }

    def init_database(self):
        """Initialize API management database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # API usage tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                tenant_id TEXT,
                service_name TEXT,
                request_type TEXT,
                cost REAL,
                tokens_used INTEGER DEFAULT 0,
                success BOOLEAN,
                response_time REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tenant API key management
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tenant_api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT,
                service_name TEXT,
                api_key TEXT,
                usage_limit_hourly INTEGER,
                cost_limit_daily REAL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Cost optimization rules
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS optimization_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_name TEXT,
                conditions TEXT,
                preferred_service TEXT,
                fallback_services TEXT,
                cost_threshold REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # ML Model registry for Claude interpreters
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ml_interpreters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                interpreter_name TEXT,
                input_format TEXT,
                output_format TEXT,
                claude_prompt TEXT,
                context_examples TEXT,
                success_rate REAL DEFAULT 0.0,
                average_cost REAL DEFAULT 0.0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Service health monitoring
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS service_health (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name TEXT,
                is_available BOOLEAN,
                response_time REAL,
                error_rate REAL,
                last_check DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        print("✅ SuperInstance API Manager database initialized")

    def load_api_keys(self):
        """Load API keys from environment variables"""
        self.api_keys = {
            "claude": os.getenv('CLAUDE_API_KEY'),
            "replicate": os.getenv('REPLICATE_API_TOKEN'),
            "openai": os.getenv('OPENAI_API_KEY'),
            "google": os.getenv('GOOGLE_API_KEY'),
            "elevenlabs": os.getenv('ELEVENLABS_API_KEY'),
            "mistral": os.getenv('MISTRAL_API_KEY'),
            "huggingface": os.getenv('HUGGINGFACE_API_TOKEN'),
            "cohere": os.getenv('COHERE_API_KEY'),
            "pinecone": os.getenv('PINECONE_API_KEY'),
        }

    def get_optimal_service(self, request_type: APIServiceType, user_id: str, 
                          tenant_id: str = "default", quality_requirement: float = 0.8,
                          cost_limit: float = None) -> Optional[str]:
        """Intelligent service selection based on cost, quality, and availability"""
        
        # Get available services for request type
        available_services = [
            (name, service) for name, service in self.api_services.items()
            if service.service_type == request_type and self.is_service_available(name, tenant_id)
        ]
        
        if not available_services:
            return None
        
        # Check usage limits
        available_services = [
            (name, service) for name, service in available_services
            if not self.is_rate_limited(name, user_id, tenant_id)
        ]
        
        # Filter by quality requirement
        available_services = [
            (name, service) for name, service in available_services
            if service.quality_score >= quality_requirement
        ]
        
        # Filter by cost limit if specified
        if cost_limit:
            available_services = [
                (name, service) for name, service in available_services
                if service.cost_per_request <= cost_limit
            ]
        
        if not available_services:
            return None
        
        # Sort by cost-effectiveness (quality/cost ratio)
        available_services.sort(
            key=lambda x: x[1].quality_score / x[1].cost_per_request, 
            reverse=True
        )
        
        return available_services[0][0]

    def is_service_available(self, service_name: str, tenant_id: str) -> bool:
        """Check if service is available for tenant"""
        if tenant_id != "default":
            # Check tenant-specific API keys
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT api_key FROM tenant_api_keys 
                WHERE tenant_id = ? AND service_name = ? AND is_active = TRUE
            """, (tenant_id, service_name))
            result = cursor.fetchone()
            conn.close()
            return bool(result)
        else:
            # Check global API keys
            if service_name in ["flux_dev", "flux_schnell", "sdxl", "runway_ml", "stable_video", "luma_ai", "musicgen", "suno_ai"]:
                return bool(self.api_keys.get("replicate"))
            else:
                return bool(self.api_keys.get(service_name))

    def is_rate_limited(self, service_name: str, user_id: str, tenant_id: str) -> bool:
        """Check if user/tenant has hit rate limits"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check hourly usage
        one_hour_ago = datetime.now() - timedelta(hours=1)
        cursor.execute("""
            SELECT COUNT(*) FROM api_usage 
            WHERE user_id = ? AND tenant_id = ? AND service_name = ? 
            AND timestamp > ? AND success = TRUE
        """, (user_id, tenant_id, service_name, one_hour_ago))
        
        hourly_usage = cursor.fetchone()[0]
        conn.close()
        
        # Special handling for Claude limits
        if service_name == "claude":
            return hourly_usage >= self.usage_limits["claude_hourly"]
        
        service = self.api_services.get(service_name)
        if service:
            return hourly_usage >= service.rate_limit_per_hour
        
        return False

    async def make_api_request(self, service_name: str, request_data: Dict[str, Any], 
                              user_id: str, tenant_id: str = "default") -> Dict[str, Any]:
        """Make API request with usage tracking and error handling"""
        
        start_time = datetime.now()
        service = self.api_services.get(service_name)
        
        if not service:
            return {"error": f"Unknown service: {service_name}"}
        
        if not self.is_service_available(service_name, tenant_id):
            return {"error": f"Service {service_name} not available for tenant {tenant_id}"}
        
        if self.is_rate_limited(service_name, user_id, tenant_id):
            return {"error": f"Rate limit exceeded for {service_name}"}
        
        try:
            # Route to appropriate API handler
            if service_name == "claude":
                result = await self._call_claude(request_data)
            elif service_name.startswith("flux") or service_name in ["sdxl", "runway_ml", "stable_video"]:
                result = await self._call_replicate(service_name, request_data)
            elif service_name == "elevenlabs":
                result = await self._call_elevenlabs(request_data)
            elif service_name == "whisper":
                result = await self._call_openai_whisper(request_data)
            else:
                result = {"error": f"Handler not implemented for {service_name}"}
            
            # Calculate response time and cost
            response_time = (datetime.now() - start_time).total_seconds()
            cost = service.cost_per_request
            success = "error" not in result
            
            # Track usage
            self.track_usage(user_id, tenant_id, service_name, "api_call", 
                           cost, response_time, success)
            
            return result
            
        except Exception as e:
            self.track_usage(user_id, tenant_id, service_name, "api_call", 
                           0, 0, False)
            return {"error": f"API call failed: {str(e)}"}

    async def _call_claude(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Call Claude API"""
        if not CLAUDE_AVAILABLE or not self.api_keys.get("claude"):
            return {"error": "Claude API not available"}
        
        client = anthropic.Client(api_key=self.api_keys["claude"])
        
        try:
            message = await client.messages.create(
                model=request_data.get("model", "claude-3-5-sonnet-20241022"),
                max_tokens=request_data.get("max_tokens", 1500),
                messages=[{
                    "role": "user",
                    "content": request_data.get("prompt", request_data.get("message", ""))
                }]
            )
            
            return {
                "success": True,
                "response": message.content[0].text,
                "model": request_data.get("model", "claude-3-5-sonnet-20241022"),
                "tokens": len(message.content[0].text.split())
            }
        except Exception as e:
            return {"error": f"Claude API error: {str(e)}"}

    async def _call_replicate(self, service_name: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Call Replicate API for various models"""
        if not REPLICATE_AVAILABLE or not self.api_keys.get("replicate"):
            return {"error": "Replicate API not available"}
        
        # Model mapping
        model_map = {
            "flux_dev": "black-forest-labs/flux-dev",
            "flux_schnell": "black-forest-labs/flux-schnell",
            "sdxl": "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
            "runway_ml": "runwayml/stable-video-diffusion:4a1a7c0aac5b0b88fedf85e21dd0be5a669eb5ea1558f0c38dd10b2b0f54a0f0",
            "stable_video": "stability-ai/stable-video-diffusion:12b5ca5c3e6bdccdea0c5b53e9f1e11dd57a7985bf1b6e01e8fe4abf7b6b6c7c"
        }
        
        model_path = model_map.get(service_name, service_name)
        
        try:
            output = replicate.run(model_path, input=request_data)
            
            return {
                "success": True,
                "output": output,
                "model": service_name,
                "input": request_data
            }
        except Exception as e:
            return {"error": f"Replicate API error: {str(e)}"}

    async def _call_elevenlabs(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Call ElevenLabs TTS API"""
        api_key = self.api_keys.get("elevenlabs")
        if not api_key:
            return {"error": "ElevenLabs API key not found"}
        
        # Implementation would go here
        return {"error": "ElevenLabs integration pending"}

    async def _call_openai_whisper(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Call OpenAI Whisper API"""
        api_key = self.api_keys.get("openai")
        if not api_key:
            return {"error": "OpenAI API key not found"}
        
        # Implementation would go here
        return {"error": "Whisper integration pending"}

    def track_usage(self, user_id: str, tenant_id: str, service_name: str, 
                   request_type: str, cost: float, response_time: float, success: bool):
        """Track API usage for billing and optimization"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO api_usage 
            (user_id, tenant_id, service_name, request_type, cost, success, response_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, tenant_id, service_name, request_type, cost, success, response_time))
        
        conn.commit()
        conn.close()

    def get_usage_report(self, tenant_id: str = "default", 
                        timeframe_hours: int = 24) -> Dict[str, Any]:
        """Generate usage and cost report"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since = datetime.now() - timedelta(hours=timeframe_hours)
        
        cursor.execute("""
            SELECT service_name, COUNT(*) as requests, SUM(cost) as total_cost,
                   AVG(response_time) as avg_response_time,
                   SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_requests
            FROM api_usage 
            WHERE tenant_id = ? AND timestamp > ?
            GROUP BY service_name
        """, (tenant_id, since))
        
        results = cursor.fetchall()
        conn.close()
        
        report = {
            "tenant_id": tenant_id,
            "timeframe_hours": timeframe_hours,
            "services": [],
            "total_cost": 0,
            "total_requests": 0
        }
        
        for row in results:
            service_data = {
                "service": row[0],
                "requests": row[1],
                "cost": row[2],
                "avg_response_time": row[3],
                "success_rate": row[4] / row[1] if row[1] > 0 else 0
            }
            report["services"].append(service_data)
            report["total_cost"] += row[2]
            report["total_requests"] += row[1]
        
        return report

    def create_ml_interpreter(self, name: str, input_format: str, output_format: str,
                            claude_prompt: str, examples: List[Dict] = None) -> str:
        """Create a Claude-based ML interpreter for custom tasks"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        interpreter_id = f"ml_interp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        cursor.execute("""
            INSERT INTO ml_interpreters 
            (id, interpreter_name, input_format, output_format, claude_prompt, context_examples)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (interpreter_id, name, input_format, output_format, claude_prompt, 
              json.dumps(examples or [])))
        
        conn.commit()
        conn.close()
        
        return interpreter_id

    async def run_ml_interpreter(self, interpreter_id: str, input_data: Any, 
                                user_id: str, tenant_id: str = "default") -> Dict[str, Any]:
        """Run a custom ML interpreter using Claude"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT interpreter_name, input_format, output_format, claude_prompt, context_examples
            FROM ml_interpreters WHERE id = ?
        """, (interpreter_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return {"error": f"ML interpreter {interpreter_id} not found"}
        
        name, input_format, output_format, prompt_template, examples_json = result
        examples = json.loads(examples_json) if examples_json else []
        
        # Build context with examples
        context = f"You are a specialized ML interpreter: {name}\n\n"
        context += f"Input format: {input_format}\n"
        context += f"Output format: {output_format}\n\n"
        
        if examples:
            context += "Examples:\n"
            for example in examples[:3]:  # Limit to 3 examples for context window
                context += f"Input: {example.get('input', '')}\n"
                context += f"Output: {example.get('output', '')}\n\n"
        
        context += f"{prompt_template}\n\nInput: {input_data}\nOutput:"
        
        # Use Claude to process
        result = await self.make_api_request(
            "claude", 
            {"prompt": context, "max_tokens": 2000},
            user_id, 
            tenant_id
        )
        
        if result.get("success"):
            return {
                "success": True,
                "interpreter": name,
                "input": input_data,
                "output": result["response"],
                "cost": 0.015  # Claude cost
            }
        else:
            return result

# Global API manager instance
superinstance_api_manager = SuperInstanceAPIManager()

def get_api_manager() -> SuperInstanceAPIManager:
    """Get the global SuperInstance API manager"""
    return superinstance_api_manager