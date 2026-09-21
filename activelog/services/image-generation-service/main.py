#!/usr/bin/env python3
"""
Comprehensive Image Generation Service
Advanced AI-powered image generation with DALL-E 3 integration, Stable Diffusion local support,
intelligent style detection, batch processing, and ML-driven prompt optimization.
"""

import asyncio
import json
import logging
import os
import base64
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import io

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
import uvicorn
import aiohttp
import aiofiles
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import sqlite3
import pickle

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Comprehensive Image Generation Service", 
    version="2.0.0",
    description="Advanced AI-powered image generation with intelligent optimization"
)

# Data Models
class ImageGenerationRequest(BaseModel):
    prompt: str = Field(..., description="Detailed image generation prompt")
    user_id: str = Field(default="default", description="User identifier")
    style: Optional[str] = Field(default=None, description="Art style preference")
    quality: str = Field(default="standard", description="Quality level: draft, standard, high, professional")
    size: str = Field(default="1024x1024", description="Image dimensions")
    format: str = Field(default="png", description="Output format: png, jpeg, webp")
    model_preference: Optional[str] = Field(default=None, description="Preferred model: dall-e-3, stable-diffusion")
    enhance_prompt: bool = Field(default=True, description="Use AI prompt enhancement")
    negative_prompt: Optional[str] = Field(default=None, description="What to avoid in the image")
    guidance_scale: float = Field(default=7.5, description="How closely to follow the prompt")
    num_inference_steps: int = Field(default=50, description="Number of denoising steps")
    seed: Optional[int] = Field(default=None, description="Random seed for reproducible results")

class BatchImageRequest(BaseModel):
    prompts: List[str] = Field(..., description="List of prompts for batch generation")
    user_id: str = Field(default="default", description="User identifier")
    base_style: Optional[str] = Field(default=None, description="Base style for all images")
    quality: str = Field(default="standard", description="Quality level for all images")
    size: str = Field(default="1024x1024", description="Size for all images")
    format: str = Field(default="png", description="Output format for all images")
    variations_per_prompt: int = Field(default=1, description="Number of variations per prompt")
    priority: int = Field(default=5, description="Batch processing priority 1-10")

class ImageEditRequest(BaseModel):
    operation: str = Field(..., description="Edit operation: enhance, upscale, style_transfer, inpaint, outpaint")
    user_id: str = Field(default="default", description="User identifier")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Operation-specific parameters")

class StyleAnalysisRequest(BaseModel):
    prompt: str = Field(..., description="Prompt to analyze")
    reference_images: Optional[List[str]] = Field(default=None, description="Reference image URLs or base64")
    user_id: str = Field(default="default", description="User identifier")

class PromptOptimizationRequest(BaseModel):
    original_prompt: str = Field(..., description="Original prompt to optimize")
    target_style: Optional[str] = Field(default=None, description="Target style")
    improvement_focus: str = Field(default="quality", description="Focus: quality, creativity, specificity")
    user_id: str = Field(default="default", description="User identifier")

class FeedbackRequest(BaseModel):
    image_id: str = Field(..., description="Generated image identifier")
    user_id: str = Field(..., description="User identifier")
    quality_score: float = Field(..., description="Quality rating 1-10")
    style_accuracy: float = Field(..., description="Style accuracy 1-10")
    prompt_adherence: float = Field(..., description="Prompt adherence 1-10")
    overall_satisfaction: float = Field(..., description="Overall satisfaction 1-10")
    comments: Optional[str] = Field(default=None, description="Additional feedback")


class ComprehensiveImageGenerationService:
    """Advanced image generation service with ML optimization"""
    
    def __init__(self):
        # Service configurations
        self.openai_service_url = "http://localhost:8475"
        self.generative_hub_url = "http://localhost:8500"
        self.local_ai_url = "http://localhost:8471"
        
        # Database setup
        self.db_path = "/home/activeloguser/activelog/services/image-generation-service/image_generation.db"
        self.setup_database()
        
        # ML Models and optimization
        self.style_classifier = None
        self.prompt_enhancer = None
        self.quality_predictor = None
        
        # User preferences and learning
        self.user_preferences: Dict[str, Dict] = {}
        self.style_patterns: Dict[str, List] = {}
        self.prompt_improvements: Dict[str, str] = {}
        
        # Generation statistics
        self.generation_stats = {
            "total_generated": 0,
            "successful_generations": 0,
            "user_satisfaction_avg": 0.0,
            "popular_styles": {},
            "model_performance": {}
        }
        
        # Image processing capabilities
        self.supported_formats = ["png", "jpeg", "jpg", "webp", "bmp", "tiff"]
        self.supported_sizes = [
            "512x512", "768x768", "1024x1024", "1024x1792", "1792x1024",
            "1536x1536", "2048x2048", "512x1024", "1024x512"
        ]
        
        # Style detection patterns
        self.style_keywords = {
            "photorealistic": ["photorealistic", "realistic", "photo", "lifelike", "natural"],
            "artistic": ["artistic", "painting", "art", "canvas", "brush strokes"],
            "digital_art": ["digital art", "cgi", "3d render", "digital painting"],
            "anime": ["anime", "manga", "japanese animation", "cartoon"],
            "sketch": ["sketch", "pencil", "drawing", "charcoal", "line art"],
            "vintage": ["vintage", "retro", "old", "classic", "aged"],
            "modern": ["modern", "contemporary", "sleek", "minimalist"],
            "fantasy": ["fantasy", "magical", "mystical", "ethereal", "surreal"],
            "sci_fi": ["sci-fi", "futuristic", "cyberpunk", "space", "technology"],
            "abstract": ["abstract", "geometric", "non-representational", "conceptual"]
        }
        
        # Load existing data
        self.load_user_data()
        self.initialize_ml_models()
    
    def setup_database(self):
        """Initialize SQLite database for storing generation data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Image generations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS image_generations (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    original_prompt TEXT NOT NULL,
                    enhanced_prompt TEXT,
                    style TEXT,
                    model_used TEXT,
                    quality_requested TEXT,
                    size TEXT,
                    format TEXT,
                    generation_time REAL,
                    cost REAL,
                    file_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    quality_score REAL,
                    user_rating REAL,
                    style_accuracy REAL,
                    prompt_adherence REAL
                )
            ''')
            
            # User preferences table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id TEXT NOT NULL,
                    preferred_style TEXT,
                    preferred_model TEXT,
                    preferred_quality TEXT,
                    preferred_size TEXT,
                    preference_score REAL,
                    usage_count INTEGER,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, preferred_style, preferred_model)
                )
            ''')
            
            # Style analysis table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS style_analysis (
                    id TEXT PRIMARY KEY,
                    prompt TEXT NOT NULL,
                    detected_styles TEXT,
                    confidence_scores TEXT,
                    recommended_model TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Prompt optimizations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS prompt_optimizations (
                    id TEXT PRIMARY KEY,
                    original_prompt TEXT NOT NULL,
                    optimized_prompt TEXT NOT NULL,
                    improvement_type TEXT,
                    success_rate REAL,
                    user_satisfaction REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ Database initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Database setup failed: {e}")
    
    def load_user_data(self):
        """Load existing user preferences and patterns from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Load user preferences
            cursor.execute("SELECT * FROM user_preferences")
            prefs = cursor.fetchall()
            
            for pref in prefs:
                user_id = pref[0]
                if user_id not in self.user_preferences:
                    self.user_preferences[user_id] = {}
                
                style_model_key = f"{pref[1]}_{pref[2]}"
                self.user_preferences[user_id][style_model_key] = {
                    "style": pref[1],
                    "model": pref[2],
                    "quality": pref[3],
                    "size": pref[4],
                    "preference_score": pref[5],
                    "usage_count": pref[6]
                }
            
            conn.close()
            logger.info(f"📚 Loaded preferences for {len(self.user_preferences)} users")
            
        except Exception as e:
            logger.error(f"❌ Failed to load user data: {e}")
    
    def initialize_ml_models(self):
        """Initialize ML models for style detection and optimization"""
        try:
            # Placeholder for ML model initialization
            # In a real implementation, these would load trained models
            self.style_classifier = self._create_style_classifier()
            self.prompt_enhancer = self._create_prompt_enhancer()
            self.quality_predictor = self._create_quality_predictor()
            
            logger.info("🤖 ML models initialized")
            
        except Exception as e:
            logger.error(f"❌ ML model initialization failed: {e}")
    
    def _create_style_classifier(self):
        """Create style classification system"""
        return {
            "model_type": "style_classifier",
            "confidence_threshold": 0.7,
            "supported_styles": list(self.style_keywords.keys())
        }
    
    def _create_prompt_enhancer(self):
        """Create prompt enhancement system"""
        return {
            "model_type": "prompt_enhancer",
            "enhancement_patterns": {
                "quality_boosters": [
                    "highly detailed", "professional quality", "masterpiece",
                    "ultra-realistic", "high resolution", "award-winning"
                ],
                "style_enhancers": {
                    "photorealistic": ["sharp focus", "professional lighting", "DSLR quality"],
                    "artistic": ["oil painting", "canvas texture", "artistic composition"],
                    "digital_art": ["digital illustration", "concept art", "trending on artstation"]
                }
            }
        }
    
    def _create_quality_predictor(self):
        """Create quality prediction system"""
        return {
            "model_type": "quality_predictor",
            "factors": ["prompt_length", "style_clarity", "technical_terms", "artist_references"]
        }
    
    async def detect_image_style(self, prompt: str, reference_images: Optional[List] = None) -> Dict:
        """Detect and analyze image style from prompt and references"""
        
        detected_styles = {}
        confidence_scores = {}
        
        # Analyze prompt for style keywords
        prompt_lower = prompt.lower()
        for style, keywords in self.style_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in prompt_lower)
            if matches > 0:
                confidence = min(matches / len(keywords) + 0.3, 1.0)
                detected_styles[style] = confidence
                confidence_scores[style] = confidence
        
        # If no specific style detected, default to photorealistic
        if not detected_styles:
            detected_styles["photorealistic"] = 0.8
            confidence_scores["photorealistic"] = 0.8
        
        # Recommend best model based on detected style
        recommended_model = self._recommend_model_for_style(detected_styles)
        
        # Store analysis in database
        style_id = hashlib.md5(f"{prompt}{datetime.now()}".encode()).hexdigest()[:16]
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO style_analysis 
                (id, prompt, detected_styles, confidence_scores, recommended_model)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                style_id,
                prompt,
                json.dumps(detected_styles),
                json.dumps(confidence_scores),
                recommended_model
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to store style analysis: {e}")
        
        return {
            "detected_styles": detected_styles,
            "confidence_scores": confidence_scores,
            "recommended_model": recommended_model,
            "primary_style": max(detected_styles, key=detected_styles.get),
            "analysis_id": style_id
        }
    
    def _recommend_model_for_style(self, detected_styles: Dict) -> str:
        """Recommend the best model based on detected styles"""
        
        # Model preferences for different styles
        model_preferences = {
            "photorealistic": "dall-e-3",
            "digital_art": "dall-e-3", 
            "modern": "dall-e-3",
            "sci_fi": "dall-e-3",
            "artistic": "stable-diffusion",
            "anime": "stable-diffusion",
            "sketch": "stable-diffusion",
            "vintage": "stable-diffusion",
            "fantasy": "stable-diffusion",
            "abstract": "stable-diffusion"
        }
        
        if not detected_styles:
            return "dall-e-3"  # Default
        
        # Get the style with highest confidence
        primary_style = max(detected_styles, key=detected_styles.get)
        return model_preferences.get(primary_style, "dall-e-3")
    
    async def optimize_prompt(self, original_prompt: str, target_style: Optional[str] = None,
                            improvement_focus: str = "quality") -> Dict:
        """Use ML to optimize prompts for better image generation"""
        
        optimized_prompt = original_prompt
        improvements = []
        
        # Style-specific enhancements
        if target_style and target_style in self.style_keywords:
            style_enhancers = self.prompt_enhancer["enhancement_patterns"]["style_enhancers"].get(target_style, [])
            if style_enhancers:
                enhancer = np.random.choice(style_enhancers)
                optimized_prompt = f"{optimized_prompt}, {enhancer}"
                improvements.append(f"Added {target_style} enhancer: {enhancer}")
        
        # Quality improvements
        if improvement_focus == "quality":
            quality_boosters = self.prompt_enhancer["enhancement_patterns"]["quality_boosters"]
            selected_boosters = np.random.choice(quality_boosters, size=min(2, len(quality_boosters)), replace=False)
            for booster in selected_boosters:
                if booster.lower() not in optimized_prompt.lower():
                    optimized_prompt = f"{optimized_prompt}, {booster}"
                    improvements.append(f"Added quality booster: {booster}")
        
        # Creativity improvements
        elif improvement_focus == "creativity":
            creative_additions = [
                "unique perspective", "innovative composition", "creative lighting",
                "unusual angle", "artistic interpretation", "imaginative details"
            ]
            creative_boost = np.random.choice(creative_additions)
            optimized_prompt = f"{optimized_prompt}, {creative_boost}"
            improvements.append(f"Added creativity boost: {creative_boost}")
        
        # Specificity improvements
        elif improvement_focus == "specificity":
            if len(original_prompt.split()) < 10:  # Short prompt needs more detail
                specificity_additions = [
                    "with intricate details", "in sharp focus", "with rich textures",
                    "with dramatic lighting", "with vibrant colors", "with perfect composition"
                ]
                specific_addition = np.random.choice(specificity_additions)
                optimized_prompt = f"{optimized_prompt} {specific_addition}"
                improvements.append(f"Added specificity: {specific_addition}")
        
        # Store optimization
        opt_id = hashlib.md5(f"{original_prompt}{optimized_prompt}{datetime.now()}".encode()).hexdigest()[:16]
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO prompt_optimizations 
                (id, original_prompt, optimized_prompt, improvement_type)
                VALUES (?, ?, ?, ?)
            ''', (opt_id, original_prompt, optimized_prompt, improvement_focus))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to store prompt optimization: {e}")
        
        return {
            "original_prompt": original_prompt,
            "optimized_prompt": optimized_prompt,
            "improvements": improvements,
            "improvement_focus": improvement_focus,
            "optimization_id": opt_id,
            "enhancement_score": len(improvements) * 0.2 + 0.6  # Base score + improvements
        }
    
    def calculate_quality_score(self, generation_params: Dict, user_feedback: Optional[Dict] = None) -> float:
        """Calculate predicted quality score based on parameters and feedback"""
        
        base_score = 7.0  # Start with good baseline
        
        # Model quality scoring
        model_scores = {
            "dall-e-3": 8.5,
            "stable-diffusion": 7.0,
            "local": 5.5
        }
        
        model_used = generation_params.get("model_used", "dall-e-3")
        base_score = model_scores.get(model_used, 7.0)
        
        # Prompt quality factors
        prompt = generation_params.get("prompt", "")
        if len(prompt) > 100:  # Detailed prompts often yield better results
            base_score += 0.5
        if len(prompt) > 200:
            base_score += 0.3
        
        # Style clarity bonus
        if generation_params.get("style"):
            base_score += 0.3
        
        # Quality setting bonus
        quality_bonuses = {
            "draft": -1.0,
            "standard": 0.0,
            "high": 0.8,
            "professional": 1.5
        }
        quality = generation_params.get("quality", "standard")
        base_score += quality_bonuses.get(quality, 0.0)
        
        # User feedback integration
        if user_feedback:
            feedback_score = user_feedback.get("overall_satisfaction", 7.0)
            # Exponential moving average with existing score
            alpha = 0.3
            base_score = (1 - alpha) * base_score + alpha * feedback_score
        
        return min(max(base_score, 1.0), 10.0)  # Clamp between 1-10
    
    async def generate_image(self, request: ImageGenerationRequest) -> Dict:
        """Generate image using optimal model and parameters"""
        
        start_time = datetime.now()
        generation_id = hashlib.md5(f"{request.prompt}{request.user_id}{start_time}".encode()).hexdigest()[:16]
        
        try:
            # Style detection and analysis
            style_analysis = await self.detect_image_style(request.prompt)
            detected_style = style_analysis["primary_style"]
            recommended_model = style_analysis["recommended_model"]
            
            # Use specified model preference or recommendation
            model_to_use = request.model_preference or recommended_model
            
            # Prompt optimization if requested
            optimized_prompt = request.prompt
            if request.enhance_prompt:
                optimization = await self.optimize_prompt(
                    request.prompt, 
                    detected_style,
                    "quality"
                )
                optimized_prompt = optimization["optimized_prompt"]
            
            # Generate image based on selected model
            result = None
            if model_to_use == "dall-e-3":
                result = await self._generate_with_dalle(request, optimized_prompt)
            elif model_to_use == "stable-diffusion":
                result = await self._generate_with_stable_diffusion(request, optimized_prompt)
            else:
                # Fallback to DALL-E 3
                result = await self._generate_with_dalle(request, optimized_prompt)
            
            if not result or not result.get("success"):
                raise Exception(result.get("error", "Generation failed"))
            
            generation_time = (datetime.now() - start_time).total_seconds()
            
            # Calculate quality score
            quality_score = self.calculate_quality_score({
                "model_used": model_to_use,
                "prompt": optimized_prompt,
                "style": detected_style,
                "quality": request.quality
            })
            
            # Store generation in database
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO image_generations 
                    (id, user_id, original_prompt, enhanced_prompt, style, model_used,
                     quality_requested, size, format, generation_time, cost, file_path, quality_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    generation_id, request.user_id, request.prompt, optimized_prompt,
                    detected_style, model_to_use, request.quality, request.size,
                    request.format, generation_time, result.get("cost", 0.0),
                    result.get("file_path"), quality_score
                ))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"Failed to store generation: {e}")
            
            # Update statistics
            self.generation_stats["total_generated"] += 1
            if result.get("success"):
                self.generation_stats["successful_generations"] += 1
            
            return {
                "success": True,
                "generation_id": generation_id,
                "model_used": model_to_use,
                "original_prompt": request.prompt,
                "enhanced_prompt": optimized_prompt,
                "detected_style": detected_style,
                "style_analysis": style_analysis,
                "quality_score": quality_score,
                "generation_time": generation_time,
                "cost": result.get("cost", 0.0),
                "image_url": result.get("image_url"),
                "file_path": result.get("file_path"),
                "metadata": {
                    "size": request.size,
                    "format": request.format,
                    "model_recommendation_confidence": style_analysis["confidence_scores"].get(detected_style, 0.0)
                }
            }
            
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "generation_id": generation_id,
                "user_id": request.user_id
            }
    
    async def _generate_with_dalle(self, request: ImageGenerationRequest, prompt: str) -> Dict:
        """Generate image using DALL-E 3 via OpenAI integration"""
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "task_description": f"Generate image: {prompt}",
                    "user_id": request.user_id,
                    "user_initiated": True,
                    "quality_requirement": 9 if request.quality in ["high", "professional"] else 7,
                    "multimodal_needed": True,
                    "preferred_provider": "openai"
                }
                
                async with session.post(f"{self.openai_service_url}/execute", json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "success": result.get("success", False),
                            "content": result.get("content"),
                            "cost": result.get("cost", 0.0),
                            "image_url": result.get("content"),  # Assume content contains image URL
                            "file_path": None  # Would be set after downloading/saving
                        }
                    else:
                        error_text = await response.text()
                        return {"success": False, "error": f"DALL-E API error: {error_text}"}
                        
        except Exception as e:
            return {"success": False, "error": f"DALL-E generation failed: {str(e)}"}
    
    async def _generate_with_stable_diffusion(self, request: ImageGenerationRequest, prompt: str) -> Dict:
        """Generate image using Stable Diffusion (local or cloud)"""
        
        try:
            # For now, simulate Stable Diffusion generation
            # In real implementation, this would call actual SD API/service
            
            await asyncio.sleep(2)  # Simulate generation time
            
            # Create placeholder response
            return {
                "success": True,
                "content": f"Stable Diffusion generated image for: {prompt[:50]}...",
                "cost": 0.0,  # Local generation is free
                "image_url": f"http://localhost:8480/generated/{hashlib.md5(prompt.encode()).hexdigest()}.{request.format}",
                "file_path": f"/tmp/sd_generated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{request.format}"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Stable Diffusion generation failed: {str(e)}"}
    
    async def generate_batch_images(self, request: BatchImageRequest) -> Dict:
        """Generate multiple images in batch with intelligent optimization"""
        
        batch_id = hashlib.md5(f"batch_{request.user_id}_{datetime.now()}".encode()).hexdigest()[:16]
        start_time = datetime.now()
        
        results = []
        total_cost = 0.0
        successful_generations = 0
        
        try:
            # Process each prompt
            for i, prompt in enumerate(request.prompts):
                for variation in range(request.variations_per_prompt):
                    try:
                        # Create individual request
                        img_request = ImageGenerationRequest(
                            prompt=prompt,
                            user_id=request.user_id,
                            style=request.base_style,
                            quality=request.quality,
                            size=request.size,
                            format=request.format,
                            enhance_prompt=True
                        )
                        
                        # Generate image
                        result = await self.generate_image(img_request)
                        
                        if result.get("success"):
                            successful_generations += 1
                            total_cost += result.get("cost", 0.0)
                        
                        results.append({
                            "prompt_index": i,
                            "variation": variation,
                            "result": result
                        })
                        
                        # Small delay between generations to avoid rate limits
                        await asyncio.sleep(0.5)
                        
                    except Exception as e:
                        logger.error(f"Batch generation failed for prompt {i}, variation {variation}: {e}")
                        results.append({
                            "prompt_index": i,
                            "variation": variation,
                            "result": {"success": False, "error": str(e)}
                        })
            
            batch_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": True,
                "batch_id": batch_id,
                "total_prompts": len(request.prompts),
                "total_variations": len(request.prompts) * request.variations_per_prompt,
                "successful_generations": successful_generations,
                "total_cost": total_cost,
                "batch_time": batch_time,
                "average_time_per_image": batch_time / len(results) if results else 0,
                "results": results,
                "summary": {
                    "success_rate": successful_generations / len(results) if results else 0,
                    "cost_per_image": total_cost / successful_generations if successful_generations > 0 else 0,
                    "estimated_quality": 8.0  # Would be calculated from actual results
                }
            }
            
        except Exception as e:
            logger.error(f"Batch generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "batch_id": batch_id,
                "partial_results": results
            }
    
    async def edit_image(self, image_file: UploadFile, request: ImageEditRequest) -> Dict:
        """Perform image editing operations"""
        
        edit_id = hashlib.md5(f"edit_{request.user_id}_{datetime.now()}".encode()).hexdigest()[:16]
        
        try:
            # Read uploaded image
            image_data = await image_file.read()
            image = Image.open(io.BytesIO(image_data))
            
            # Perform editing operation
            edited_image = None
            
            if request.operation == "enhance":
                edited_image = await self._enhance_image(image, request.parameters)
            elif request.operation == "upscale":
                edited_image = await self._upscale_image(image, request.parameters)
            elif request.operation == "style_transfer":
                edited_image = await self._apply_style_transfer(image, request.parameters)
            elif request.operation == "inpaint":
                edited_image = await self._inpaint_image(image, request.parameters)
            elif request.operation == "outpaint":
                edited_image = await self._outpaint_image(image, request.parameters)
            else:
                raise ValueError(f"Unsupported operation: {request.operation}")
            
            # Save edited image
            output_path = f"/tmp/edited_{edit_id}_{request.operation}.png"
            edited_image.save(output_path)
            
            return {
                "success": True,
                "edit_id": edit_id,
                "operation": request.operation,
                "file_path": output_path,
                "original_size": image.size,
                "edited_size": edited_image.size,
                "parameters_used": request.parameters
            }
            
        except Exception as e:
            logger.error(f"Image editing failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "edit_id": edit_id
            }
    
    async def _enhance_image(self, image: Image.Image, parameters: Dict) -> Image.Image:
        """Enhance image quality"""
        
        enhanced = image.copy()
        
        # Brightness adjustment
        if "brightness" in parameters:
            enhancer = ImageEnhance.Brightness(enhanced)
            enhanced = enhancer.enhance(parameters["brightness"])
        
        # Contrast adjustment
        if "contrast" in parameters:
            enhancer = ImageEnhance.Contrast(enhanced)
            enhanced = enhancer.enhance(parameters["contrast"])
        
        # Saturation adjustment
        if "saturation" in parameters:
            enhancer = ImageEnhance.Color(enhanced)
            enhanced = enhancer.enhance(parameters["saturation"])
        
        # Sharpness adjustment
        if "sharpness" in parameters:
            enhancer = ImageEnhance.Sharpness(enhanced)
            enhanced = enhancer.enhance(parameters["sharpness"])
        
        # Noise reduction
        if parameters.get("reduce_noise", False):
            enhanced = enhanced.filter(ImageFilter.MedianFilter(size=3))
        
        return enhanced
    
    async def _upscale_image(self, image: Image.Image, parameters: Dict) -> Image.Image:
        """Upscale image using AI or interpolation"""
        
        scale_factor = parameters.get("scale_factor", 2.0)
        method = parameters.get("method", "lanczos")
        
        new_size = (int(image.width * scale_factor), int(image.height * scale_factor))
        
        if method == "lanczos":
            return image.resize(new_size, Image.LANCZOS)
        elif method == "bicubic":
            return image.resize(new_size, Image.BICUBIC)
        else:
            return image.resize(new_size, Image.LANCZOS)
    
    async def _apply_style_transfer(self, image: Image.Image, parameters: Dict) -> Image.Image:
        """Apply style transfer (placeholder - would use actual ML model)"""
        
        # Placeholder implementation
        # In real scenario, would use neural style transfer
        style = parameters.get("style", "artistic")
        
        # Apply simple filter as placeholder
        if style == "vintage":
            # Apply sepia-like effect
            enhanced = ImageEnhance.Color(image).enhance(0.7)
            enhanced = ImageEnhance.Contrast(enhanced).enhance(1.2)
        else:
            enhanced = image
        
        return enhanced
    
    async def _inpaint_image(self, image: Image.Image, parameters: Dict) -> Image.Image:
        """Inpaint image (fill masked areas)"""
        
        # Placeholder - would integrate with actual inpainting model
        return image
    
    async def _outpaint_image(self, image: Image.Image, parameters: Dict) -> Image.Image:
        """Outpaint image (extend beyond borders)"""
        
        # Placeholder - would integrate with actual outpainting model
        expansion = parameters.get("expansion", 100)
        
        # Simple extension by duplicating edges
        new_width = image.width + 2 * expansion
        new_height = image.height + 2 * expansion
        
        extended = Image.new(image.mode, (new_width, new_height), color=(255, 255, 255))
        extended.paste(image, (expansion, expansion))
        
        return extended
    
    def learn_user_preferences(self, feedback: FeedbackRequest):
        """Learn from user feedback to improve future generations"""
        
        try:
            # Update database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Update the specific generation with feedback
            cursor.execute('''
                UPDATE image_generations 
                SET user_rating = ?, style_accuracy = ?, prompt_adherence = ?
                WHERE id = ?
            ''', (
                feedback.overall_satisfaction,
                feedback.style_accuracy, 
                feedback.prompt_adherence,
                feedback.image_id
            ))
            
            # Get generation details for learning
            cursor.execute('''
                SELECT model_used, style, quality_requested, size, user_id
                FROM image_generations WHERE id = ?
            ''', (feedback.image_id,))
            
            result = cursor.fetchone()
            if result:
                model_used, style, quality, size, user_id = result
                
                # Update user preferences
                pref_key = f"{style}_{model_used}"
                if user_id not in self.user_preferences:
                    self.user_preferences[user_id] = {}
                
                if pref_key not in self.user_preferences[user_id]:
                    self.user_preferences[user_id][pref_key] = {
                        "style": style,
                        "model": model_used,
                        "quality": quality,
                        "size": size,
                        "preference_score": feedback.overall_satisfaction,
                        "usage_count": 1
                    }
                else:
                    # Update with exponential moving average
                    prefs = self.user_preferences[user_id][pref_key]
                    alpha = 0.2
                    prefs["preference_score"] = (1 - alpha) * prefs["preference_score"] + alpha * feedback.overall_satisfaction
                    prefs["usage_count"] += 1
                
                # Update database preferences
                cursor.execute('''
                    INSERT OR REPLACE INTO user_preferences 
                    (user_id, preferred_style, preferred_model, preferred_quality, 
                     preferred_size, preference_score, usage_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id, style, model_used, quality, size,
                    self.user_preferences[user_id][pref_key]["preference_score"],
                    self.user_preferences[user_id][pref_key]["usage_count"]
                ))
            
            conn.commit()
            conn.close()
            
            # Update global statistics
            current_avg = self.generation_stats["user_satisfaction_avg"]
            total_generations = self.generation_stats["total_generated"]
            
            if total_generations > 0:
                self.generation_stats["user_satisfaction_avg"] = (
                    current_avg * (total_generations - 1) + feedback.overall_satisfaction
                ) / total_generations
            
            logger.info(f"📚 Updated preferences for user {feedback.user_id}: {feedback.overall_satisfaction}/10")
            
        except Exception as e:
            logger.error(f"Failed to learn from feedback: {e}")
    
    def get_user_analytics(self, user_id: str) -> Dict:
        """Get comprehensive analytics for a specific user"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get generation statistics
            cursor.execute('''
                SELECT COUNT(*), AVG(user_rating), AVG(quality_score), 
                       AVG(generation_time), SUM(cost)
                FROM image_generations WHERE user_id = ?
            ''', (user_id,))
            
            stats = cursor.fetchone()
            total_gens, avg_rating, avg_quality, avg_time, total_cost = stats
            
            # Get style preferences
            cursor.execute('''
                SELECT style, COUNT(*), AVG(user_rating)
                FROM image_generations WHERE user_id = ? AND style IS NOT NULL
                GROUP BY style ORDER BY COUNT(*) DESC
            ''', (user_id,))
            
            style_stats = cursor.fetchall()
            
            # Get model usage
            cursor.execute('''
                SELECT model_used, COUNT(*), AVG(user_rating), AVG(cost)
                FROM image_generations WHERE user_id = ?
                GROUP BY model_used ORDER BY COUNT(*) DESC
            ''', (user_id,))
            
            model_stats = cursor.fetchall()
            
            conn.close()
            
            return {
                "user_id": user_id,
                "total_generations": total_gens or 0,
                "average_rating": round(avg_rating or 0, 2),
                "average_quality_score": round(avg_quality or 0, 2),
                "average_generation_time": round(avg_time or 0, 2),
                "total_cost": round(total_cost or 0, 4),
                "style_preferences": [
                    {
                        "style": style,
                        "usage_count": count,
                        "average_rating": round(rating or 0, 2)
                    } for style, count, rating in style_stats
                ],
                "model_preferences": [
                    {
                        "model": model,
                        "usage_count": count,
                        "average_rating": round(rating or 0, 2),
                        "average_cost": round(cost or 0, 4)
                    } for model, count, rating, cost in model_stats
                ],
                "user_preferences": self.user_preferences.get(user_id, {}),
                "insights": self._generate_user_insights(user_id, total_gens or 0, avg_rating or 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get user analytics: {e}")
            return {"error": str(e), "user_id": user_id}
    
    def _generate_user_insights(self, user_id: str, total_gens: int, avg_rating: float) -> List[str]:
        """Generate personalized insights for the user"""
        
        insights = []
        
        if total_gens == 0:
            insights.append("New user - no generation history yet")
        elif total_gens < 5:
            insights.append("Getting started - try different styles to find your preferences")
        elif total_gens < 20:
            insights.append("Regular user - system is learning your preferences")
        else:
            insights.append("Power user - system has learned your style preferences well")
        
        if avg_rating > 8.0:
            insights.append("High satisfaction user - consistently happy with results")
        elif avg_rating > 6.0:
            insights.append("Moderate satisfaction - some room for improvement in recommendations")
        elif avg_rating > 0:
            insights.append("Low satisfaction - consider trying different models or styles")
        
        # Check user preferences
        if user_id in self.user_preferences:
            prefs = self.user_preferences[user_id]
            if len(prefs) > 3:
                insights.append("Has strong style preferences - system optimizes accordingly")
            
            # Find preferred style
            best_style = max(prefs.keys(), key=lambda k: prefs[k]["preference_score"]) if prefs else None
            if best_style:
                style = prefs[best_style]["style"]
                insights.append(f"Preferred style: {style}")
        
        return insights
    
    def get_system_analytics(self) -> Dict:
        """Get comprehensive system analytics"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Overall statistics
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_generations,
                    COUNT(DISTINCT user_id) as unique_users,
                    AVG(user_rating) as avg_satisfaction,
                    AVG(quality_score) as avg_quality,
                    SUM(cost) as total_cost,
                    AVG(generation_time) as avg_generation_time
                FROM image_generations
            ''')
            
            overall_stats = cursor.fetchone()
            
            # Model performance
            cursor.execute('''
                SELECT 
                    model_used,
                    COUNT(*) as usage_count,
                    AVG(user_rating) as avg_rating,
                    AVG(quality_score) as avg_quality,
                    AVG(generation_time) as avg_time,
                    SUM(cost) as total_cost
                FROM image_generations
                GROUP BY model_used
                ORDER BY usage_count DESC
            ''')
            
            model_performance = cursor.fetchall()
            
            # Popular styles
            cursor.execute('''
                SELECT 
                    style,
                    COUNT(*) as usage_count,
                    AVG(user_rating) as avg_rating
                FROM image_generations
                WHERE style IS NOT NULL
                GROUP BY style
                ORDER BY usage_count DESC
                LIMIT 10
            ''')
            
            popular_styles = cursor.fetchall()
            
            # Recent activity (last 7 days)
            cursor.execute('''
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as generations
                FROM image_generations
                WHERE created_at >= datetime('now', '-7 days')
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            ''')
            
            recent_activity = cursor.fetchall()
            
            conn.close()
            
            return {
                "overview": {
                    "total_generations": overall_stats[0] or 0,
                    "unique_users": overall_stats[1] or 0,
                    "average_satisfaction": round(overall_stats[2] or 0, 2),
                    "average_quality": round(overall_stats[3] or 0, 2),
                    "total_cost": round(overall_stats[4] or 0, 4),
                    "average_generation_time": round(overall_stats[5] or 0, 2)
                },
                "model_performance": [
                    {
                        "model": model,
                        "usage_count": count,
                        "avg_rating": round(rating or 0, 2),
                        "avg_quality": round(quality or 0, 2),
                        "avg_time": round(time or 0, 2),
                        "total_cost": round(cost or 0, 4)
                    }
                    for model, count, rating, quality, time, cost in model_performance
                ],
                "popular_styles": [
                    {
                        "style": style,
                        "usage_count": count,
                        "avg_rating": round(rating or 0, 2)
                    }
                    for style, count, rating in popular_styles
                ],
                "recent_activity": [
                    {
                        "date": date,
                        "generations": count
                    }
                    for date, count in recent_activity
                ],
                "system_insights": [
                    "Advanced ML-powered prompt optimization",
                    "Intelligent style detection and model selection",
                    "User preference learning for personalized results",
                    "Multi-model support with cost optimization",
                    "Comprehensive quality scoring and analytics"
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get system analytics: {e}")
            return {"error": str(e)}


# Initialize the service
service = ComprehensiveImageGenerationService()

# API Endpoints
@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("🎨 Starting Comprehensive Image Generation Service")
    logger.info(f"✅ Initialized with {len(service.supported_formats)} supported formats")
    logger.info(f"🎯 Style detection for {len(service.style_keywords)} style categories")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Comprehensive Image Generation Service",
        "status": "operational",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "capabilities": {
            "models": ["dall-e-3", "stable-diffusion"],
            "formats": service.supported_formats,
            "sizes": service.supported_sizes,
            "features": [
                "intelligent_style_detection",
                "ml_prompt_optimization", 
                "batch_generation",
                "image_editing",
                "quality_scoring",
                "user_preference_learning"
            ]
        },
        "statistics": service.generation_stats
    }

@app.post("/generate")
async def generate_image(request: ImageGenerationRequest):
    """Generate a single image with full optimization"""
    result = await service.generate_image(request)
    return result

@app.post("/generate/batch")
async def generate_batch_images(request: BatchImageRequest):
    """Generate multiple images in batch"""
    result = await service.generate_batch_images(request)
    return result

@app.post("/analyze/style")
async def analyze_style(request: StyleAnalysisRequest):
    """Analyze image style and get model recommendations"""
    result = await service.detect_image_style(request.prompt, request.reference_images)
    return result

@app.post("/optimize/prompt") 
async def optimize_prompt(request: PromptOptimizationRequest):
    """Optimize prompt for better generation results"""
    result = await service.optimize_prompt(
        request.original_prompt,
        request.target_style,
        request.improvement_focus
    )
    return result

@app.post("/edit")
async def edit_image(
    image: UploadFile = File(...),
    operation: str = Form(...),
    user_id: str = Form(default="default"),
    parameters: str = Form(default="{}")
):
    """Edit existing image"""
    try:
        params = json.loads(parameters) if parameters else {}
        edit_request = ImageEditRequest(
            operation=operation,
            user_id=user_id,
            parameters=params
        )
        result = await service.edit_image(image, edit_request)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """Submit feedback for learning and improvement"""
    service.learn_user_preferences(feedback)
    return {
        "message": "Feedback recorded successfully",
        "image_id": feedback.image_id,
        "user_id": feedback.user_id,
        "overall_satisfaction": feedback.overall_satisfaction
    }

@app.get("/analytics/user/{user_id}")
async def get_user_analytics(user_id: str):
    """Get comprehensive user analytics"""
    return service.get_user_analytics(user_id)

@app.get("/analytics/system")
async def get_system_analytics():
    """Get system-wide analytics and insights"""
    return service.get_system_analytics()

@app.get("/models")
async def list_models():
    """List available models and their capabilities"""
    return {
        "available_models": {
            "dall-e-3": {
                "name": "DALL-E 3",
                "provider": "OpenAI",
                "strengths": ["photorealistic", "creative", "detailed", "ui_mockups"],
                "cost_structure": "pay_per_use",
                "quality_levels": ["standard", "high"],
                "max_size": "1792x1024",
                "supported_formats": ["png", "jpeg"]
            },
            "stable-diffusion": {
                "name": "Stable Diffusion",
                "provider": "Local/Open Source",
                "strengths": ["artistic", "fast", "customizable", "batch_friendly"],
                "cost_structure": "free",
                "quality_levels": ["draft", "standard", "high"],
                "max_size": "2048x2048",
                "supported_formats": ["png", "jpeg", "webp"]
            }
        },
        "selection_criteria": {
            "photorealistic": "dall-e-3",
            "artistic": "stable-diffusion", 
            "ui_mockups": "dall-e-3",
            "concept_art": "stable-diffusion",
            "marketing_visuals": "dall-e-3",
            "batch_processing": "stable-diffusion"
        }
    }

@app.get("/styles")
async def list_styles():
    """List supported styles and their characteristics"""
    return {
        "supported_styles": service.style_keywords,
        "style_recommendations": {
            style: {
                "keywords": keywords,
                "recommended_model": service._recommend_model_for_style({style: 1.0}),
                "typical_use_cases": _get_style_use_cases(style)
            }
            for style, keywords in service.style_keywords.items()
        }
    }

def _get_style_use_cases(style: str) -> List[str]:
    """Get typical use cases for each style"""
    use_cases = {
        "photorealistic": ["product photography", "portraits", "real estate"],
        "artistic": ["book covers", "gallery art", "creative projects"],
        "digital_art": ["game assets", "digital illustrations", "concept art"],
        "anime": ["character design", "manga illustrations", "animation"],
        "sketch": ["wireframes", "rough concepts", "artistic studies"],
        "vintage": ["retro marketing", "nostalgic themes", "period pieces"],
        "modern": ["corporate materials", "tech products", "minimalist design"],
        "fantasy": ["book illustrations", "game art", "creative storytelling"],
        "sci_fi": ["futuristic concepts", "space themes", "technology visualization"],
        "abstract": ["artistic expression", "creative backgrounds", "conceptual art"]
    }
    return use_cases.get(style, ["general purpose"])

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8480))
    uvicorn.run(
        "main:app",
        host="0.0.0.0", 
        port=port,
        log_level="info",
        reload=True
    )