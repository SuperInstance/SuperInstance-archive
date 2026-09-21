#!/usr/bin/env python3
"""
SuperInstance Replicate AI Service
Visual AI generation for interface customization, assets, and look & feel
"""

import os
import json
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
import base64
import io
import requests
from visual_behavior_learner import get_visual_behavior_learner

try:
    import replicate
    REPLICATE_AVAILABLE = True
except ImportError:
    REPLICATE_AVAILABLE = False
    print("Replicate not available - install with: pip install replicate")

class ReplicateAIService:
    def __init__(self):
        self.db_path = "/tmp/dmlog_replicate_ai.db"
        self.init_database()
        
        # Initialize visual behavior learning
        self.behavior_learner = get_visual_behavior_learner()
        
        # Initialize Replicate client
        self.replicate_client = None
        if REPLICATE_AVAILABLE:
            api_key = os.getenv('REPLICATE_API_TOKEN')
            if api_key:
                os.environ['REPLICATE_API_TOKEN'] = api_key
                self.replicate_client = replicate
                print("✅ Replicate AI initialized")
            else:
                print("⚠️  Set REPLICATE_API_TOKEN environment variable")
        
        # Popular models for different use cases
        self.models = {
            # Image Generation
            'flux_dev': 'black-forest-labs/flux-dev',
            'flux_schnell': 'black-forest-labs/flux-schnell', 
            'sdxl': 'stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b',
            'stable_diffusion': 'stability-ai/stable-diffusion:27b93a2413e7f36cd83da926f3656280b2931564ff050bf9575f1fdf9bcd7478',
            
            # Style Transfer & Enhancement
            'real_esrgan': 'nightmareai/real-esrgan:42fed1c4974146d4d2414e2be2c5277c7fcf05fcc972b753c2a11efe8a7a8b8a',
            'colorization': 'cjwbw/bigcolor:9451bfb0a5581c68ba4c8e7e8b5e1235f0c0e7e8b5e1235f0c0e7e8b5e1235',
            
            # UI/UX Generation
            'ui_mockup': 'replicate/stable-diffusion-inpainting',
            'logo_generation': 'ai-forever/kandinsky-2.2:ad601ca67a444f999ac15e3cb07c4d57d4e59ddc5c5e0f5e80e84aa30bfea31a',
            
            # Background/Texture Generation  
            'texture_gen': 'stability-ai/stable-diffusion:27b93a2413e7f36cd83da926f3656280b2931564ff050bf9575f1fdf9bcd7478',
            'background_gen': 'black-forest-labs/flux-dev'
        }
        
        # Optimized prompts for interface generation
        self.prompt_templates = {
            'ui_theme': "Modern {style} user interface theme, clean design, {colors} color palette, professional web design, high contrast, accessibility friendly, {mood} aesthetic",
            'background': "Abstract {style} background pattern, {colors} gradient, subtle texture, web interface background, professional design, seamless pattern",
            'icon_set': "Modern {style} icon set, {theme} theme, vector style, consistent design language, professional UI icons, clean lines",
            'logo': "Professional {company} logo, {style} design, {colors} colors, modern typography, clean vector graphics, brand identity",
            'dashboard': "Modern {style} dashboard interface mockup, {colors} theme, data visualization, clean layout, professional web app design",
            'component': "Modern UI {component} component, {style} design system, {colors} color scheme, interactive element, web interface"
        }

    def init_database(self):
        """Initialize Replicate AI database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Generated visual assets
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS visual_assets (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                asset_type TEXT,
                prompt TEXT,
                model_used TEXT,
                generation_params TEXT,
                asset_url TEXT,
                local_path TEXT,
                is_admin_approved BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Visual customization requests
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS visual_requests (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                request_type TEXT,
                description TEXT,
                target_component TEXT,
                generated_assets TEXT,
                status TEXT DEFAULT 'pending',
                admin_review TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Theme and style presets
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS style_presets (
                id TEXT PRIMARY KEY,
                name TEXT,
                category TEXT,
                colors TEXT,
                typography TEXT,
                spacing TEXT,
                visual_assets TEXT,
                is_default BOOLEAN DEFAULT FALSE,
                created_by TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        print("✅ Replicate AI database initialized")

    async def generate_image(self, prompt: str, model: str = 'flux_schnell', user_id: str = "default", **kwargs) -> Dict[str, Any]:
        """Generate image using Replicate with self-improving prompts"""
        if not self.replicate_client:
            return {"error": "Replicate not available"}
        
        # Get improved prompt based on learned patterns
        improved_prompt, confidence = self.behavior_learner.get_improved_prompt(prompt, user_id)
        
        # Use improved prompt if confidence is high enough
        final_prompt = improved_prompt if confidence > 0.7 else prompt
        
        print(f"🎨 Generating image:")
        print(f"   Original: {prompt}")
        if final_prompt != prompt:
            print(f"   Improved: {final_prompt} (confidence: {confidence:.2f})")
        
        try:
            model_path = self.models.get(model, model)
            
            # Default parameters for different models
            if 'flux' in model:
                input_params = {
                    "prompt": prompt,
                    "width": kwargs.get('width', 1024),
                    "height": kwargs.get('height', 1024),
                    "num_inference_steps": kwargs.get('steps', 4),
                    "guidance_scale": kwargs.get('guidance', 3.5),
                    "num_outputs": kwargs.get('num_outputs', 1)
                }
            elif 'sdxl' in model:
                input_params = {
                    "prompt": prompt,
                    "width": kwargs.get('width', 1024),
                    "height": kwargs.get('height', 1024),
                    "num_inference_steps": kwargs.get('steps', 20),
                    "guidance_scale": kwargs.get('guidance', 7.5),
                    "num_outputs": kwargs.get('num_outputs', 1),
                    "scheduler": "K_EULER"
                }
            else:
                input_params = {
                    "prompt": prompt,
                    **kwargs
                }
            
            print(f"🎨 Generating image with {model}: {prompt[:50]}...")
            
            output = self.replicate_client.run(
                model_path,
                input=input_params
            )
            
            # Handle different output formats
            if isinstance(output, list) and len(output) > 0:
                image_url = output[0]
            elif isinstance(output, str):
                image_url = output
            else:
                return {"error": f"Unexpected output format: {type(output)}"}
            
            return {
                "success": True,
                "image_url": image_url,
                "model": model,
                "prompt": prompt,
                "params": input_params
            }
            
        except Exception as e:
            print(f"Replicate generation error: {e}")
            return {"error": str(e)}

    async def generate_ui_theme(self, theme_request: str, user_id: str, colors: str = "blue and white", style: str = "modern") -> Dict[str, Any]:
        """Generate complete UI theme assets"""
        try:
            theme_id = f"theme_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id[:8]}"
            
            # Generate multiple assets for the theme
            assets = {}
            
            # 1. Background/Pattern
            bg_prompt = self.prompt_templates['background'].format(
                style=style,
                colors=colors,
                mood=theme_request
            )
            
            bg_result = await self.generate_image(
                bg_prompt, 
                model='flux_schnell',
                width=1920, 
                height=1080
            )
            
            if bg_result.get('success'):
                assets['background'] = bg_result['image_url']
            
            # 2. UI Components
            comp_prompt = self.prompt_templates['component'].format(
                component="button and card",
                style=style,
                colors=colors
            )
            
            comp_result = await self.generate_image(
                comp_prompt,
                model='flux_schnell', 
                width=800,
                height=600
            )
            
            if comp_result.get('success'):
                assets['components'] = comp_result['image_url']
            
            # 3. Icon Set
            icon_prompt = self.prompt_templates['icon_set'].format(
                style=style,
                theme=colors
            )
            
            icon_result = await self.generate_image(
                icon_prompt,
                model='flux_schnell',
                width=512,
                height=512
            )
            
            if icon_result.get('success'):
                assets['icons'] = icon_result['image_url']
            
            # Save theme to database
            self.save_theme_preset(
                theme_id, 
                f"{style.title()} {colors.title()} Theme",
                "generated",
                colors,
                style,
                assets,
                user_id
            )
            
            return {
                "success": True,
                "theme_id": theme_id,
                "assets": assets,
                "description": f"Generated {style} theme with {colors} colors"
            }
            
        except Exception as e:
            return {"error": f"Theme generation failed: {str(e)}"}

    async def generate_dashboard_mockup(self, description: str, style: str = "modern", colors: str = "dark blue") -> Dict[str, Any]:
        """Generate dashboard/interface mockup"""
        prompt = self.prompt_templates['dashboard'].format(
            style=style,
            colors=colors
        ) + f", {description}"
        
        return await self.generate_image(
            prompt,
            model='flux_dev',
            width=1200,
            height=800,
            steps=20
        )

    async def generate_logo(self, company: str, style: str = "modern", colors: str = "blue") -> Dict[str, Any]:
        """Generate logo design"""
        prompt = self.prompt_templates['logo'].format(
            company=company,
            style=style,
            colors=colors
        )
        
        return await self.generate_image(
            prompt,
            model='flux_dev',
            width=512,
            height=512,
            steps=20
        )

    def save_visual_asset(self, user_id: str, asset_type: str, prompt: str, 
                         model: str, asset_url: str, params: Dict = None) -> str:
        """Save generated visual asset to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        asset_id = f"asset_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id[:8]}"
        
        cursor.execute("""
            INSERT INTO visual_assets 
            (id, user_id, asset_type, prompt, model_used, generation_params, asset_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (asset_id, user_id, asset_type, prompt, model, json.dumps(params or {}), asset_url))
        
        conn.commit()
        conn.close()
        
        return asset_id

    def save_theme_preset(self, theme_id: str, name: str, category: str, 
                         colors: str, typography: str, visual_assets: Dict, created_by: str):
        """Save theme preset to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO style_presets 
            (id, name, category, colors, typography, visual_assets, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (theme_id, name, category, colors, typography, json.dumps(visual_assets), created_by))
        
        conn.commit()
        conn.close()

    def get_user_assets(self, user_id: str) -> List[Dict]:
        """Get user's generated visual assets"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM visual_assets 
            WHERE user_id = ? 
            ORDER BY created_at DESC
        """, (user_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        assets = []
        for row in results:
            assets.append({
                "id": row[0],
                "user_id": row[1],
                "asset_type": row[2],
                "prompt": row[3],
                "model_used": row[4],
                "generation_params": json.loads(row[5]) if row[5] else {},
                "asset_url": row[6],
                "local_path": row[7],
                "is_admin_approved": row[8],
                "created_at": row[9]
            })
        
        return assets

    def get_style_presets(self, category: str = None) -> List[Dict]:
        """Get available style presets"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if category:
            cursor.execute("""
                SELECT * FROM style_presets 
                WHERE category = ? 
                ORDER BY created_at DESC
            """, (category,))
        else:
            cursor.execute("""
                SELECT * FROM style_presets 
                ORDER BY created_at DESC
            """)
        
        results = cursor.fetchall()
        conn.close()
        
        presets = []
        for row in results:
            presets.append({
                "id": row[0],
                "name": row[1],
                "category": row[2],
                "colors": row[3],
                "typography": row[4],
                "spacing": row[5],
                "visual_assets": json.loads(row[6]) if row[6] else {},
                "is_default": row[7],
                "created_by": row[8],
                "created_at": row[9]
            })
        
        return presets

    async def enhance_image(self, image_url: str, enhancement_type: str = 'upscale') -> Dict[str, Any]:
        """Enhance existing image using Replicate"""
        if not self.replicate_client:
            return {"error": "Replicate not available"}
        
        try:
            if enhancement_type == 'upscale':
                output = self.replicate_client.run(
                    self.models['real_esrgan'],
                    input={"image": image_url, "scale": 4}
                )
            elif enhancement_type == 'colorize':
                output = self.replicate_client.run(
                    self.models['colorization'],
                    input={"image": image_url}
                )
            else:
                return {"error": f"Unknown enhancement type: {enhancement_type}"}
            
            return {
                "success": True,
                "enhanced_url": output,
                "original_url": image_url,
                "enhancement_type": enhancement_type
            }
            
        except Exception as e:
            return {"error": f"Enhancement failed: {str(e)}"}

    def process_visual_request(self, user_input: str, user_id: str) -> Dict[str, Any]:
        """Process natural language visual generation request"""
        user_lower = user_input.lower()
        
        # Detect request type
        if any(word in user_lower for word in ['theme', 'color scheme', 'style']):
            return {'type': 'theme', 'action': 'generate_ui_theme'}
        elif any(word in user_lower for word in ['background', 'wallpaper']):
            return {'type': 'background', 'action': 'generate_background'}
        elif any(word in user_lower for word in ['logo', 'brand']):
            return {'type': 'logo', 'action': 'generate_logo'}
        elif any(word in user_lower for word in ['dashboard', 'interface', 'mockup']):
            return {'type': 'dashboard', 'action': 'generate_dashboard_mockup'}
        elif any(word in user_lower for word in ['icon', 'symbol']):
            return {'type': 'icon', 'action': 'generate_icon_set'}
        else:
            return {'type': 'general', 'action': 'generate_image'}

# Global replicate service instance
replicate_ai_service = ReplicateAIService()

def get_replicate_ai_service() -> ReplicateAIService:
    """Get the global Replicate AI service instance"""
    return replicate_ai_service