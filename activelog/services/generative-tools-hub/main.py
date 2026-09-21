#!/usr/bin/env python3
"""
Generative Tools Hub - Comprehensive AI Generation Suite
Unified interface for all types of AI generation across the SuperInstance ecosystem
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from pydantic import BaseModel
import uvicorn
import os
import aiohttp
import base64
from pathlib import Path
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="Generative Tools Hub", version="1.0.0")

class GenerationRequest(BaseModel):
    prompt: str
    generation_type: str  # 'image', 'text', 'code', 'audio', 'video', 'document'
    user_id: str = "default"
    style: Optional[str] = None
    quality: str = "standard"  # 'draft', 'standard', 'high', 'professional'
    format: Optional[str] = None
    context: Optional[str] = None
    user_initiated: bool = True
    parameters: Dict[str, Any] = {}

class CodeGenerationRequest(BaseModel):
    description: str
    language: str
    framework: Optional[str] = None
    complexity: str = "medium"  # 'simple', 'medium', 'complex'
    include_tests: bool = False
    include_docs: bool = False
    user_id: str = "default"

class DocumentGenerationRequest(BaseModel):
    content_type: str  # 'blog', 'report', 'email', 'summary', 'proposal'
    topic: str
    tone: str = "professional"  # 'casual', 'professional', 'friendly', 'formal'
    length: str = "medium"  # 'short', 'medium', 'long'
    audience: str = "general"
    key_points: List[str] = []
    user_id: str = "default"

class MultimodalRequest(BaseModel):
    inputs: List[Dict[str, Any]]  # Multiple inputs of different types
    output_type: str
    fusion_style: str = "complement"  # 'complement', 'enhance', 'transform'
    user_id: str = "default"

class GenerativeToolsHub:
    """Centralized hub for all generative AI capabilities"""
    
    def __init__(self):
        self.openai_service_url = "http://localhost:8475"
        self.claude_service_url = "http://localhost:8474" 
        self.local_ai_url = "http://localhost:8471"
        
        # Generation history and analytics
        self.generation_history: List[Dict] = []
        self.user_preferences: Dict[str, Dict] = {}
        
        # Initialize generation capabilities
        self.generators = {
            'image': self._get_image_generators(),
            'text': self._get_text_generators(),
            'code': self._get_code_generators(),
            'audio': self._get_audio_generators(),
            'video': self._get_video_generators(),
            'document': self._get_document_generators()
        }
    
    def _get_image_generators(self) -> Dict[str, Dict]:
        """Available image generation methods"""
        return {
            'dall-e-3': {
                'service': 'openai',
                'endpoint': '/execute',
                'strengths': ['photorealistic', 'creative', 'detailed'],
                'use_cases': ['ui_mockups', 'concept_art', 'marketing_visuals'],
                'quality_tiers': ['standard', 'high']
            },
            'stable-diffusion': {
                'service': 'local',
                'endpoint': '/generate_image',
                'strengths': ['artistic', 'fast', 'customizable'],
                'use_cases': ['artistic_content', 'rapid_prototyping', 'batch_generation'],
                'quality_tiers': ['draft', 'standard', 'high']
            }
        }
    
    def _get_text_generators(self) -> Dict[str, Dict]:
        """Available text generation methods"""
        return {
            'gpt-4-turbo': {
                'service': 'openai',
                'endpoint': '/execute',
                'strengths': ['reasoning', 'analysis', 'detailed_writing'],
                'use_cases': ['technical_writing', 'analysis', 'complex_content'],
                'quality_tiers': ['standard', 'high', 'professional']
            },
            'claude-3-opus': {
                'service': 'claude',
                'endpoint': '/execute',
                'strengths': ['creative_writing', 'nuanced_understanding', 'consistency'],
                'use_cases': ['creative_content', 'storytelling', 'detailed_explanations'],
                'quality_tiers': ['standard', 'high', 'professional']
            },
            'local-llm': {
                'service': 'local',
                'endpoint': '/generate',
                'strengths': ['speed', 'privacy', 'cost_free'],
                'use_cases': ['simple_content', 'summaries', 'basic_writing'],
                'quality_tiers': ['draft', 'standard']
            }
        }
    
    def _get_code_generators(self) -> Dict[str, Dict]:
        """Available code generation methods"""
        return {
            'claude-coding': {
                'service': 'claude', 
                'endpoint': '/execute',
                'strengths': ['architecture', 'best_practices', 'complex_logic'],
                'languages': ['python', 'javascript', 'typescript', 'rust', 'go', 'java'],
                'frameworks': ['react', 'fastapi', 'django', 'express', 'spring']
            },
            'gpt-4-coding': {
                'service': 'openai',
                'endpoint': '/execute', 
                'strengths': ['quick_solutions', 'debugging', 'optimization'],
                'languages': ['python', 'javascript', 'typescript', 'c++', 'java', 'php'],
                'frameworks': ['vue', 'flask', 'nodejs', 'angular']
            },
            'local-coding': {
                'service': 'local',
                'endpoint': '/code_complete',
                'strengths': ['completion', 'snippets', 'refactoring'],
                'languages': ['python', 'javascript', 'java', 'c++'],
                'frameworks': ['basic_templates']
            }
        }
    
    def _get_audio_generators(self) -> Dict[str, Dict]:
        """Available audio generation methods"""
        return {
            'openai-tts': {
                'service': 'openai',
                'endpoint': '/execute',
                'strengths': ['natural_voices', 'quality', 'multiple_voices'],
                'voices': ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'],
                'formats': ['mp3', 'opus', 'aac', 'flac']
            },
            'whisper-transcription': {
                'service': 'openai',
                'endpoint': '/execute',
                'strengths': ['transcription', 'multilingual', 'accuracy'],
                'input_formats': ['mp3', 'wav', 'flac', 'm4a'],
                'languages': ['en', 'es', 'fr', 'de', 'zh', 'ja', 'multi']
            },
            'elevenlabs-voice': {
                'service': 'external',
                'endpoint': '/voice_generation',
                'strengths': ['voice_cloning', 'emotional_speech', 'premium_quality'],
                'use_cases': ['character_voices', 'audiobooks', 'professional_narration']
            }
        }
    
    def _get_video_generators(self) -> Dict[str, Dict]:
        """Available video generation methods"""
        return {
            'runway-ml': {
                'service': 'external',
                'endpoint': '/video_generation',
                'strengths': ['text_to_video', 'image_to_video', 'style_transfer'],
                'formats': ['mp4', 'gif', 'webm'],
                'durations': ['short', 'medium', 'long']
            },
            'stable-video': {
                'service': 'local',
                'endpoint': '/generate_video',
                'strengths': ['motion_from_image', 'artistic_video', 'batch_processing'],
                'formats': ['mp4', 'gif'],
                'durations': ['short', 'medium']
            },
            'luma-ai': {
                'service': 'external',
                'endpoint': '/3d_video',
                'strengths': ['3d_scenes', 'product_demos', 'architectural_visualization'],
                'formats': ['mp4', '3d_model'],
                'specialties': ['product_showcase', 'architectural_walkthrough']
            }
        }
    
    def _get_document_generators(self) -> Dict[str, Dict]:
        """Available document generation methods"""
        return {
            'claude-writer': {
                'service': 'claude',
                'endpoint': '/execute',
                'strengths': ['long_form', 'structured_content', 'research_quality'],
                'document_types': ['reports', 'proposals', 'articles', 'documentation'],
                'formats': ['markdown', 'html', 'structured_json']
            },
            'gpt-business': {
                'service': 'openai',
                'endpoint': '/execute',
                'strengths': ['business_content', 'marketing_copy', 'emails'],
                'document_types': ['emails', 'marketing', 'summaries', 'presentations'],
                'formats': ['text', 'markdown', 'html']
            }
        }
    
    async def intelligent_generator_selection(self, generation_type: str, prompt: str, 
                                            quality: str, user_id: str, context: Optional[str] = None) -> str:
        """Intelligently select the best generator for the task"""
        
        generators = self.generators.get(generation_type, {})
        if not generators:
            raise ValueError(f"No generators available for type: {generation_type}")
        
        # Score generators based on requirements
        scores = {}
        
        for name, config in generators.items():
            score = 0
            
            # Quality matching
            if quality in config.get('quality_tiers', ['standard']):
                score += 10
            
            # Use case matching
            use_cases = config.get('use_cases', [])
            if any(case in prompt.lower() for case in use_cases):
                score += 15
            
            # User preference boost
            user_prefs = self.user_preferences.get(user_id, {})
            if name in user_prefs:
                score += user_prefs[name].get('preference_score', 0) * 5
            
            # Context-specific scoring
            if context:
                if 'creative' in context.lower() and 'creative' in config.get('strengths', []):
                    score += 8
                if 'professional' in context.lower() and 'professional' in config.get('quality_tiers', []):
                    score += 10
                if 'fast' in context.lower() and 'speed' in config.get('strengths', []):
                    score += 12
            
            scores[name] = score
        
        # Select best generator
        best_generator = max(scores, key=scores.get)
        logger.info(f"🎯 Selected {best_generator} for {generation_type} (score: {scores[best_generator]})")
        
        return best_generator
    
    async def generate_content(self, request: GenerationRequest) -> Dict[str, Any]:
        """Generate content using the best available method"""
        
        try:
            # Select optimal generator
            generator_name = await self.intelligent_generator_selection(
                request.generation_type,
                request.prompt,
                request.quality,
                request.user_id,
                request.context
            )
            
            generator_config = self.generators[request.generation_type][generator_name]
            service = generator_config['service']
            
            # Prepare generation request
            generation_result = None
            
            if service == 'openai':
                generation_result = await self._generate_via_openai(
                    generator_name, request
                )
            elif service == 'claude':
                generation_result = await self._generate_via_claude(
                    generator_name, request
                )
            elif service == 'local':
                generation_result = await self._generate_via_local_ai(
                    generator_name, request
                )
            elif service == 'external':
                generation_result = await self._generate_via_external_service(
                    generator_name, request
                )
            else:
                raise ValueError(f"Unknown service: {service}")
            
            # Track generation
            self._track_generation(request, generation_result, generator_name)
            
            return {
                "success": True,
                "generator_used": generator_name,
                "generation_type": request.generation_type,
                "content": generation_result.get("content"),
                "metadata": generation_result.get("metadata", {}),
                "quality_score": generation_result.get("quality_score", 8),
                "generation_time": generation_result.get("generation_time", 0),
                "cost": generation_result.get("cost", 0.0),
                "user_id": request.user_id,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "generation_type": request.generation_type,
                "user_id": request.user_id
            }
    
    async def _generate_via_openai(self, generator_name: str, request: GenerationRequest) -> Dict:
        """Generate content via OpenAI service"""
        
        # Map to appropriate OpenAI model/endpoint
        model_mapping = {
            'dall-e-3': 'dall-e-3',
            'gpt-4-turbo': 'gpt-4-turbo',
            'openai-tts': 'tts-1',
            'whisper-transcription': 'whisper-1'
        }
        
        model = model_mapping.get(generator_name, 'gpt-4-turbo')
        
        # Prepare enhanced prompt based on generation type
        enhanced_prompt = await self._enhance_prompt(request.prompt, request.generation_type, request.parameters)
        
        async with aiohttp.ClientSession() as session:
            payload = {
                "task_description": enhanced_prompt,
                "user_id": request.user_id,
                "user_initiated": request.user_initiated,
                "quality_requirement": self._quality_to_score(request.quality),
                "creativity_needed": request.generation_type in ['image', 'text', 'document'],
                "multimodal_needed": request.generation_type in ['image', 'video', 'audio'],
                "preferred_provider": "openai"
            }
            
            async with session.post(f"{self.openai_service_url}/execute", json=payload) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"OpenAI service error: {error_text}")
    
    async def _generate_via_claude(self, generator_name: str, request: GenerationRequest) -> Dict:
        """Generate content via Claude service"""
        
        enhanced_prompt = await self._enhance_prompt(request.prompt, request.generation_type, request.parameters)
        
        async with aiohttp.ClientSession() as session:
            payload = {
                "task_description": enhanced_prompt,
                "user_id": request.user_id,
                "complexity": self._quality_to_complexity(request.quality),
                "priority": 8 if request.user_initiated else 5
            }
            
            async with session.post(f"{self.claude_service_url}/execute", json=payload) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"Claude service error: {error_text}")
    
    async def _generate_via_local_ai(self, generator_name: str, request: GenerationRequest) -> Dict:
        """Generate content via local AI service"""
        
        enhanced_prompt = await self._enhance_prompt(request.prompt, request.generation_type, request.parameters)
        
        async with aiohttp.ClientSession() as session:
            payload = {
                "task_description": enhanced_prompt,
                "user_id": request.user_id,
                "task_type": request.generation_type,
                "speed_requirement": 9  # Local AI is preferred for speed
            }
            
            async with session.post(f"{self.local_ai_url}/execute", json=payload) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"Local AI service error: {error_text}")
    
    async def _generate_via_external_service(self, generator_name: str, request: GenerationRequest) -> Dict:
        """Generate content via external services (placeholder for future integrations)"""
        
        # Placeholder for external services like ElevenLabs, Runway, etc.
        logger.info(f"📡 External service {generator_name} would be called here")
        
        return {
            "content": f"[{generator_name} would generate: {request.prompt}]",
            "metadata": {"service": "external", "generator": generator_name},
            "quality_score": 7,
            "generation_time": 5.0,
            "cost": 0.10
        }
    
    async def _enhance_prompt(self, prompt: str, generation_type: str, parameters: Dict) -> str:
        """Enhance prompt based on generation type and parameters"""
        
        enhancements = {
            'image': {
                'prefix': 'Create a high-quality visual image of: ',
                'suffix': '. Style: professional, detailed, visually appealing.'
            },
            'text': {
                'prefix': 'Generate well-written, engaging text about: ',
                'suffix': '. Make it informative and well-structured.'
            },
            'code': {
                'prefix': 'Generate clean, well-documented code for: ',
                'suffix': '. Include proper error handling and best practices.'
            },
            'audio': {
                'prefix': 'Generate or process audio for: ',
                'suffix': '. Ensure high quality and clarity.'
            },
            'video': {
                'prefix': 'Create a compelling video showing: ',
                'suffix': '. Focus on visual storytelling and engagement.'
            },
            'document': {
                'prefix': 'Create a professional document about: ',
                'suffix': '. Structure it clearly with proper headings and flow.'
            }
        }
        
        enhancement = enhancements.get(generation_type, {'prefix': '', 'suffix': ''})
        
        enhanced = f"{enhancement['prefix']}{prompt}{enhancement['suffix']}"
        
        # Add parameter-specific enhancements
        if parameters.get('style'):
            enhanced += f" Style: {parameters['style']}."
        
        if parameters.get('audience'):
            enhanced += f" Target audience: {parameters['audience']}."
        
        return enhanced
    
    def _quality_to_score(self, quality: str) -> int:
        """Convert quality string to numeric score"""
        mapping = {
            'draft': 5,
            'standard': 7,
            'high': 8,
            'professional': 10
        }
        return mapping.get(quality, 7)
    
    def _quality_to_complexity(self, quality: str) -> int:
        """Convert quality to complexity score"""
        mapping = {
            'draft': 3,
            'standard': 6,
            'high': 8,
            'professional': 10
        }
        return mapping.get(quality, 6)
    
    def _track_generation(self, request: GenerationRequest, result: Dict, generator_name: str):
        """Track generation for analytics and learning"""
        
        generation_record = {
            "timestamp": datetime.now().isoformat(),
            "user_id": request.user_id,
            "generation_type": request.generation_type,
            "generator_used": generator_name,
            "prompt_length": len(request.prompt),
            "quality_requested": request.quality,
            "success": result.get("success", True),
            "generation_time": result.get("generation_time", 0),
            "cost": result.get("cost", 0.0),
            "quality_score": result.get("quality_score", 0)
        }
        
        self.generation_history.append(generation_record)
        
        # Keep last 1000 generations
        if len(self.generation_history) > 1000:
            self.generation_history = self.generation_history[-1000:]
    
    def learn_user_preference(self, user_id: str, generator_name: str, generation_type: str, 
                            satisfaction_score: float):
        """Learn user preferences for better future selections"""
        
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {}
        
        if generator_name not in self.user_preferences[user_id]:
            self.user_preferences[user_id][generator_name] = {
                'preference_score': 0,
                'usage_count': 0,
                'avg_satisfaction': 5.0
            }
        
        prefs = self.user_preferences[user_id][generator_name]
        
        # Update with exponential moving average
        alpha = 0.2
        prefs['avg_satisfaction'] = (1 - alpha) * prefs['avg_satisfaction'] + alpha * satisfaction_score
        prefs['preference_score'] = (satisfaction_score - 5) / 5  # Normalize to -1 to 1
        prefs['usage_count'] += 1
        
        logger.info(f"📚 Updated preference: {user_id} rates {generator_name} {satisfaction_score}/10")
    
    def get_generation_analytics(self) -> Dict:
        """Get comprehensive generation analytics"""
        
        if not self.generation_history:
            return {"message": "No generation history available"}
        
        total_generations = len(self.generation_history)
        successful_generations = sum(1 for g in self.generation_history if g.get("success", True))
        
        # Type breakdown
        type_stats = {}
        for gen in self.generation_history:
            gen_type = gen["generation_type"]
            if gen_type not in type_stats:
                type_stats[gen_type] = {"count": 0, "total_cost": 0, "avg_quality": 0}
            type_stats[gen_type]["count"] += 1
            type_stats[gen_type]["total_cost"] += gen.get("cost", 0)
        
        # Generator performance
        generator_stats = {}
        for gen in self.generation_history:
            gen_name = gen["generator_used"]
            if gen_name not in generator_stats:
                generator_stats[gen_name] = {"count": 0, "success_rate": 0, "avg_quality": 0}
            generator_stats[gen_name]["count"] += 1
            if gen.get("success", True):
                generator_stats[gen_name]["success_rate"] += 1
        
        # Calculate averages
        for stats in generator_stats.values():
            if stats["count"] > 0:
                stats["success_rate"] = stats["success_rate"] / stats["count"]
        
        return {
            "total_generations": total_generations,
            "success_rate": successful_generations / total_generations,
            "generation_types": type_stats,
            "generator_performance": generator_stats,
            "total_users": len(set(g["user_id"] for g in self.generation_history)),
            "total_cost": sum(g.get("cost", 0) for g in self.generation_history)
        }

# Initialize the hub
hub = GenerativeToolsHub()

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("🎨 Starting Generative Tools Hub")
    logger.info(f"✅ Initialized {len(hub.generators)} generation categories")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Generative Tools Hub",
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
        "capabilities": list(hub.generators.keys()),
        "total_generators": sum(len(gens) for gens in hub.generators.values())
    }

@app.post("/generate")
async def generate_content(request: GenerationRequest):
    """Generate content using the optimal method"""
    
    result = await hub.generate_content(request)
    return result

@app.post("/generate/code")
async def generate_code(request: CodeGenerationRequest):
    """Specialized code generation endpoint"""
    
    # Convert to general generation request
    enhanced_prompt = f"Create {request.language}"
    if request.framework:
        enhanced_prompt += f" using {request.framework}"
    
    enhanced_prompt += f" code that {request.description}. "
    enhanced_prompt += f"Complexity level: {request.complexity}."
    
    if request.include_tests:
        enhanced_prompt += " Include comprehensive tests."
    if request.include_docs:
        enhanced_prompt += " Include detailed documentation."
    
    gen_request = GenerationRequest(
        prompt=enhanced_prompt,
        generation_type="code",
        user_id=request.user_id,
        quality="high",
        parameters={
            "language": request.language,
            "framework": request.framework,
            "complexity": request.complexity
        }
    )
    
    return await hub.generate_content(gen_request)

@app.post("/generate/document")
async def generate_document(request: DocumentGenerationRequest):
    """Specialized document generation endpoint"""
    
    enhanced_prompt = f"Create a {request.length} {request.content_type} about {request.topic}. "
    enhanced_prompt += f"Tone: {request.tone}. Target audience: {request.audience}."
    
    if request.key_points:
        enhanced_prompt += f" Key points to cover: {', '.join(request.key_points)}"
    
    gen_request = GenerationRequest(
        prompt=enhanced_prompt,
        generation_type="document",
        user_id=request.user_id,
        quality="professional",
        parameters={
            "content_type": request.content_type,
            "tone": request.tone,
            "length": request.length,
            "audience": request.audience
        }
    )
    
    return await hub.generate_content(gen_request)

@app.post("/generate/multimodal")
async def generate_multimodal(request: MultimodalRequest):
    """Generate content combining multiple input types"""
    
    # This would handle complex multimodal generation
    # For now, return a placeholder
    return {
        "message": "Multimodal generation system ready",
        "inputs_received": len(request.inputs),
        "output_type": request.output_type,
        "fusion_style": request.fusion_style
    }

@app.get("/generators")
async def list_generators():
    """List all available generators and their capabilities"""
    
    generator_info = {}
    for category, generators in hub.generators.items():
        generator_info[category] = {}
        for name, config in generators.items():
            generator_info[category][name] = {
                "service": config["service"],
                "strengths": config.get("strengths", []),
                "use_cases": config.get("use_cases", []),
                "quality_tiers": config.get("quality_tiers", ["standard"])
            }
    
    return {
        "categories": list(hub.generators.keys()),
        "generators": generator_info,
        "total_generators": sum(len(gens) for gens in hub.generators.values())
    }

@app.post("/feedback")
async def submit_feedback(user_id: str, generator_name: str, generation_type: str, satisfaction_score: float):
    """Submit user feedback for learning"""
    
    hub.learn_user_preference(user_id, generator_name, generation_type, satisfaction_score)
    
    return {
        "message": "Feedback recorded successfully",
        "user_id": user_id,
        "generator": generator_name,
        "satisfaction_score": satisfaction_score
    }

@app.get("/analytics")
async def get_analytics():
    """Get generation analytics and insights"""
    
    return hub.get_generation_analytics()

@app.get("/analytics/user/{user_id}")
async def get_user_analytics(user_id: str):
    """Get user-specific generation analytics"""
    
    user_generations = [g for g in hub.generation_history if g["user_id"] == user_id]
    
    if not user_generations:
        return {"message": f"No generation history for user {user_id}"}
    
    # User-specific stats
    user_types = {}
    for gen in user_generations:
        gen_type = gen["generation_type"]
        user_types[gen_type] = user_types.get(gen_type, 0) + 1
    
    return {
        "user_id": user_id,
        "total_generations": len(user_generations),
        "generation_types": user_types,
        "preferences": hub.user_preferences.get(user_id, {}),
        "total_cost": sum(g.get("cost", 0) for g in user_generations)
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8500))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=True
    )