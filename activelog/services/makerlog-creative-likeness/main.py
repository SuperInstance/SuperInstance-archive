#!/usr/bin/env python3
"""
MakerLog Creative Likeness Engine
AI-Powered system for generating audio, visuals, and themes in stories using reference-based descriptions.
Supports all types of creators: writers, game developers, filmmakers, musicians, artists, and more.
"""

import asyncio
import json
import time
import uuid
import re
import logging
import base64
import io
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import sqlite3
import threading
from contextlib import asynccontextmanager
from collections import defaultdict
import difflib
from fuzzywuzzy import fuzz, process
import numpy as np

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Creative Types and Models
class CreativeType(str):
    CHARACTER = "character"
    SCENE = "scene" 
    PLOT = "plot"
    AUDIO = "audio"
    MUSIC = "music"
    VISUAL = "visual"
    THEME = "theme"
    MOOD = "mood"
    STYLE = "style"
    VOICE = "voice"
    ATMOSPHERE = "atmosphere"

class MediaType(str):
    ACTOR = "actor"
    CHARACTER = "character"
    MOVIE = "movie"
    TV_SHOW = "tv_show"
    BOOK = "book"
    GAME = "game"
    SONG = "song"
    ALBUM = "album"
    ARTIST = "artist"
    COMPOSER = "composer"
    PAINTING = "painting"
    PHOTOGRAPHER = "photographer"
    BRAND = "brand"
    GENRE = "genre"

@dataclass
class CreativeReference:
    name: str
    type: MediaType
    category: str  # visual, audio, narrative, style, etc.
    description: str
    attributes: Dict[str, Any]
    popularity_score: float
    tags: List[str]
    generation_prompts: Dict[str, str]  # Prompts for different AI models
    
@dataclass 
class GenerationRequest:
    description: str
    creative_type: CreativeType
    output_formats: List[str]  # ["text", "audio", "image", "video", "3d"]
    style_preferences: Optional[List[str]] = None
    reference_strength: float = 0.7  # How strongly to follow references
    creativity_level: float = 0.5  # How creative vs faithful to references
    target_audience: Optional[str] = None
    project_context: Optional[Dict[str, Any]] = None

@dataclass
class GeneratedAsset:
    asset_type: str
    format: str
    content: Union[str, bytes]
    metadata: Dict[str, Any]
    generation_params: Dict[str, Any]
    quality_score: float

class CreativeAnalysisResponse(BaseModel):
    original_description: str
    parsed_references: List[Dict[str, Any]]
    enhanced_description: str
    generated_assets: List[Dict[str, Any]]
    style_analysis: Dict[str, Any]
    mood_analysis: Dict[str, Any]
    technical_specs: Dict[str, Any]
    inspiration_notes: List[str]
    remix_suggestions: List[str]
    confidence_score: float

class CreativeDatabase:
    """Comprehensive database of creative references across all media types"""
    
    def __init__(self):
        self.db_path = "data/creative_database.db"
        self.references = {}
        self._init_database()
        self._populate_creative_data()
    
    def _init_database(self):
        """Initialize the creative database schema"""
        Path("data").mkdir(exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS creative_references (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                attributes TEXT,
                popularity_score REAL,
                tags TEXT,
                generation_prompts TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS generated_assets (
                id TEXT PRIMARY KEY,
                request_id TEXT,
                asset_type TEXT,
                format TEXT,
                file_path TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS style_combinations (
                id TEXT PRIMARY KEY,
                references TEXT,
                combination_type TEXT,
                success_rating REAL,
                user_feedback TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _populate_creative_data(self):
        """Populate database with comprehensive creative references"""
        references_data = [
            # Visual Artists & Styles
            {
                "name": "Studio Ghibli",
                "type": MediaType.BRAND,
                "category": "visual",
                "description": "Japanese animation studio known for whimsical, detailed, nature-focused artwork",
                "attributes": {
                    "visual_style": ["hand-drawn", "organic shapes", "nature integration", "soft colors"],
                    "mood": ["whimsical", "nostalgic", "peaceful", "magical"],
                    "themes": ["nature", "childhood", "magic", "adventure"],
                    "color_palette": ["earthy greens", "soft blues", "warm yellows", "muted tones"]
                },
                "popularity_score": 0.95,
                "tags": ["anime", "nature", "whimsical", "hand-drawn", "peaceful"],
                "generation_prompts": {
                    "image": "Studio Ghibli style, hand-drawn animation, soft watercolor textures, nature elements, whimsical atmosphere",
                    "video": "Ghibli-inspired scene with gentle camera movements, nature sounds, peaceful atmosphere",
                    "audio": "Gentle, orchestral music with nature sounds, peaceful and nostalgic mood"
                }
            },
            {
                "name": "Tim Burton",
                "type": MediaType.ARTIST,
                "category": "visual",
                "description": "Director/artist known for gothic, dark whimsical aesthetic with twisted fairy tale elements",
                "attributes": {
                    "visual_style": ["gothic", "striped patterns", "exaggerated proportions", "dark colors"],
                    "mood": ["dark whimsical", "gothic", "mysterious", "melancholic"],
                    "themes": ["outsiders", "gothic romance", "dark fairy tales", "Victorian"],
                    "color_palette": ["black", "white", "deep purples", "blood red", "pale skin tones"]
                },
                "popularity_score": 0.88,
                "tags": ["gothic", "dark", "whimsical", "striped", "Victorian"],
                "generation_prompts": {
                    "image": "Tim Burton style, gothic architecture, striped patterns, pale characters with large eyes, dark whimsical atmosphere",
                    "video": "Burton-esque scene with dramatic lighting, gothic elements, exaggerated character designs",
                    "audio": "Danny Elfman style orchestral music, dark whimsical tones, gothic atmosphere"
                }
            },
            
            # Music & Audio
            {
                "name": "Hans Zimmer",
                "type": MediaType.COMPOSER,
                "category": "audio",
                "description": "Epic film composer known for powerful orchestral scores with electronic elements",
                "attributes": {
                    "audio_style": ["orchestral", "electronic fusion", "powerful", "dramatic"],
                    "instruments": ["full orchestra", "synthesizers", "percussion", "brass"],
                    "mood": ["epic", "dramatic", "emotional", "intense"],
                    "techniques": ["building crescendos", "time stretching", "braams", "ostinatos"]
                },
                "popularity_score": 0.94,
                "tags": ["epic", "orchestral", "cinematic", "dramatic", "electronic"],
                "generation_prompts": {
                    "audio": "Hans Zimmer style epic orchestral score, building crescendos, dramatic brass, electronic elements",
                    "music": "Cinematic orchestral piece with Zimmer-style braams, emotional strings, powerful percussion"
                }
            },
            {
                "name": "Lofi Hip Hop",
                "type": MediaType.GENRE,
                "category": "audio",
                "description": "Chill, relaxed music genre with vintage aesthetic and study/work atmosphere",
                "attributes": {
                    "audio_style": ["chill", "nostalgic", "relaxed", "vintage"],
                    "instruments": ["electric piano", "vinyl samples", "jazz samples", "soft drums"],
                    "mood": ["relaxed", "nostalgic", "cozy", "contemplative"],
                    "production": ["vinyl crackle", "low-fi production", "jazz chord progressions", "simple beats"]
                },
                "popularity_score": 0.82,
                "tags": ["lofi", "chill", "vintage", "nostalgic", "study"],
                "generation_prompts": {
                    "audio": "Lofi hip hop beat, vinyl crackle, jazz piano samples, chill atmosphere, nostalgic mood",
                    "music": "Relaxed lofi track with vintage aesthetic, study music vibes, cozy atmosphere"
                }
            },
            
            # Literary/Narrative Styles
            {
                "name": "Neil Gaiman",
                "type": MediaType.ARTIST,
                "category": "narrative",
                "description": "Fantasy author known for dark fairy tales, mythology, and poetic prose",
                "attributes": {
                    "writing_style": ["poetic", "mythological", "dark fairy tale", "philosophical"],
                    "themes": ["mythology", "dreams", "identity", "coming of age"],
                    "mood": ["mysterious", "poetic", "dark wonder", "contemplative"],
                    "narrative_techniques": ["unreliable narrators", "mythological elements", "dream logic", "folklore"]
                },
                "popularity_score": 0.89,
                "tags": ["fantasy", "mythology", "poetic", "dark fairy tale", "philosophical"],
                "generation_prompts": {
                    "text": "Neil Gaiman style prose, mythological elements, poetic language, dark fairy tale atmosphere",
                    "narrative": "Gaiman-inspired story with dream logic, mythological themes, poetic descriptions"
                }
            },
            
            # Game/Interactive Styles
            {
                "name": "Dark Souls",
                "type": MediaType.GAME,
                "category": "interactive",
                "description": "Gothic action RPG series known for dark atmosphere, challenging gameplay, and environmental storytelling",
                "attributes": {
                    "visual_style": ["gothic", "dark fantasy", "medieval", "atmospheric"],
                    "mood": ["dark", "oppressive", "mysterious", "melancholic"],
                    "themes": ["death", "persistence", "decay", "ancient mysteries"],
                    "design_principles": ["environmental storytelling", "challenging", "atmospheric", "interconnected"]
                },
                "popularity_score": 0.91,
                "tags": ["dark souls", "gothic", "challenging", "atmospheric", "medieval"],
                "generation_prompts": {
                    "image": "Dark Souls aesthetic, gothic architecture, medieval fantasy, dark atmospheric lighting",
                    "environment": "Souls-like environment design, interconnected levels, atmospheric storytelling through architecture"
                }
            },
            
            # Contemporary Internet Culture
            {
                "name": "Vaporwave",
                "type": MediaType.GENRE,
                "category": "style",
                "description": "Aesthetic and music genre featuring 80s/90s nostalgia, neon colors, and retro-futuristic elements",
                "attributes": {
                    "visual_style": ["neon colors", "retro computer graphics", "palm trees", "geometric shapes"],
                    "color_palette": ["hot pink", "electric blue", "purple", "teal", "sunset gradients"],
                    "mood": ["nostalgic", "dreamy", "surreal", "melancholic"],
                    "elements": ["VHS aesthetics", "classical sculptures", "80s tech", "Japanese text"]
                },
                "popularity_score": 0.75,
                "tags": ["vaporwave", "80s", "neon", "nostalgic", "retro-futuristic"],
                "generation_prompts": {
                    "image": "Vaporwave aesthetic, neon pink and blue colors, retro computer graphics, palm trees, 80s nostalgia",
                    "audio": "Vaporwave music, slowed down samples, dreamy synths, nostalgic 80s atmosphere"
                }
            },
            
            # Photography & Visual Styles
            {
                "name": "Annie Leibovitz",
                "type": MediaType.PHOTOGRAPHER,
                "category": "visual",
                "description": "Renowned portrait photographer known for dramatic, cinematic celebrity photography",
                "attributes": {
                    "visual_style": ["dramatic lighting", "cinematic", "bold compositions", "storytelling"],
                    "techniques": ["environmental portraits", "dramatic poses", "rich colors", "narrative elements"],
                    "mood": ["dramatic", "powerful", "intimate", "storytelling"],
                    "lighting": ["dramatic shadows", "rich contrasts", "cinematic lighting", "environmental use"]
                },
                "popularity_score": 0.86,
                "tags": ["portrait", "dramatic", "cinematic", "storytelling", "professional"],
                "generation_prompts": {
                    "image": "Annie Leibovitz style portrait, dramatic lighting, cinematic composition, storytelling elements",
                    "photography": "Leibovitz-inspired dramatic portrait with rich colors and narrative elements"
                }
            }
        ]
        
        for ref_data in references_data:
            self.add_reference(CreativeReference(
                name=ref_data["name"],
                type=ref_data["type"],
                category=ref_data["category"],
                description=ref_data["description"],
                attributes=ref_data["attributes"],
                popularity_score=ref_data["popularity_score"],
                tags=ref_data["tags"],
                generation_prompts=ref_data["generation_prompts"]
            ))
    
    def add_reference(self, reference: CreativeReference):
        """Add a creative reference to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        ref_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT OR REPLACE INTO creative_references 
            (id, name, type, category, description, attributes, popularity_score, tags, generation_prompts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ref_id,
            reference.name,
            reference.type,
            reference.category,
            reference.description,
            json.dumps(reference.attributes),
            reference.popularity_score,
            json.dumps(reference.tags),
            json.dumps(reference.generation_prompts)
        ))
        
        conn.commit()
        conn.close()
        
        self.references[reference.name.lower()] = reference

class CreativeGenerator:
    """AI-powered generator for creative assets based on reference descriptions"""
    
    def __init__(self, creative_db: CreativeDatabase):
        self.creative_db = creative_db
        self._init_ai_clients()
        self.generation_history = defaultdict(list)
    
    def _init_ai_clients(self):
        """Initialize various AI service clients"""
        self.openai_available = False
        self.stabilityai_available = False
        self.elevenlabs_available = False
        
        try:
            import os
            if os.getenv('OPENAI_API_KEY'):
                self.openai_available = True
                logger.info("OpenAI client available")
            
            if os.getenv('STABILITY_API_KEY'):
                self.stabilityai_available = True
                logger.info("Stability AI client available")
                
            if os.getenv('ELEVENLABS_API_KEY'):
                self.elevenlabs_available = True
                logger.info("ElevenLabs client available")
                
        except Exception as e:
            logger.warning(f"AI client initialization: {e}")
    
    async def generate_creative_assets(self, request: GenerationRequest) -> CreativeAnalysisResponse:
        """Main generation function that creates assets based on reference descriptions"""
        
        # Step 1: Parse and match references
        references = await self._parse_creative_references(request.description)
        matched_refs = await self._match_creative_references(references)
        
        # Step 2: Analyze style and mood
        style_analysis = await self._analyze_style(matched_refs, request)
        mood_analysis = await self._analyze_mood(matched_refs, request)
        
        # Step 3: Generate enhanced description
        enhanced_desc = await self._generate_enhanced_description(request, matched_refs, style_analysis)
        
        # Step 4: Generate requested assets
        generated_assets = []
        for output_format in request.output_formats:
            assets = await self._generate_assets_by_format(
                output_format, request, matched_refs, style_analysis, mood_analysis
            )
            generated_assets.extend(assets)
        
        # Step 5: Generate technical specs and suggestions
        tech_specs = await self._generate_technical_specs(matched_refs, request)
        suggestions = await self._generate_remix_suggestions(matched_refs, request)
        
        return CreativeAnalysisResponse(
            original_description=request.description,
            parsed_references=[asdict(ref) for ref in matched_refs],
            enhanced_description=enhanced_desc,
            generated_assets=[asdict(asset) for asset in generated_assets],
            style_analysis=style_analysis,
            mood_analysis=mood_analysis,
            technical_specs=tech_specs,
            inspiration_notes=await self._generate_inspiration_notes(matched_refs),
            remix_suggestions=suggestions,
            confidence_score=self._calculate_generation_confidence(matched_refs)
        )
    
    async def _parse_creative_references(self, description: str) -> List[Dict[str, Any]]:
        """Parse creative references from description"""
        
        # Enhanced patterns for creative references
        patterns = [
            # "like [artist/style] meets [artist/style]"
            r"like\s+([^,\s]+(?:\s+[^,\s]+)*?)\s+meets\s+([^,\.\!]+)",
            # "in the style of [artist/creator]"
            r"(?:in\s+the\s+style\s+of|styled\s+like)\s+([^,\.\!]+)",
            # "sounds like [artist] but with [element]"
            r"sounds?\s+like\s+([^,\s]+(?:\s+[^,\s]+)*?)\s+but\s+with\s+([^,\.\!]+)",
            # "has the [quality] of [reference] and the [quality] of [reference]"
            r"has\s+the\s+([^,\s]+(?:\s+[^,\s]+)*?)\s+of\s+([^,\s]+(?:\s+[^,\s]+)*?)\s+and\s+the\s+([^,\s]+(?:\s+[^,\s]+)*?)\s+of\s+([^,\.\!]+)",
            # "reminiscent of [reference]"
            r"reminiscent\s+of\s+([^,\.\!]+)",
            # "[reference]-inspired" or "[reference]-esque"
            r"([^,\s]+(?:\s+[^,\s]+)*?)[-\s](?:inspired|esque|style|like|vibes)",
            # "mix of [ref] and [ref]"
            r"(?:mix|blend|combination)\s+of\s+([^,\s]+(?:\s+[^,\s]+)*?)\s+and\s+([^,\.\!]+)",
        ]
        
        parsed_references = []
        
        for pattern in patterns:
            matches = re.finditer(pattern, description, re.IGNORECASE)
            for match in matches:
                groups = match.groups()
                if len(groups) == 2:
                    if "meets" in match.group(0) or "and" in pattern:
                        # Two references
                        parsed_references.append({
                            "reference": groups[0].strip(),
                            "context": match.group(0),
                            "type": "primary"
                        })
                        parsed_references.append({
                            "reference": groups[1].strip(),
                            "context": match.group(0),
                            "type": "secondary"
                        })
                    else:
                        parsed_references.append({
                            "reference": groups[0].strip(),
                            "attribute": groups[1].strip() if len(groups) > 1 else None,
                            "context": match.group(0),
                            "type": "attributed"
                        })
                elif len(groups) == 4:
                    # Four groups - complex pattern
                    parsed_references.extend([
                        {
                            "reference": groups[1].strip(),
                            "attribute": groups[0].strip(),
                            "context": match.group(0),
                            "type": "attributed"
                        },
                        {
                            "reference": groups[3].strip(),
                            "attribute": groups[2].strip(),
                            "context": match.group(0),
                            "type": "attributed"
                        }
                    ])
                else:
                    parsed_references.append({
                        "reference": groups[0].strip(),
                        "attribute": None,
                        "context": match.group(0),
                        "type": "direct"
                    })
        
        return parsed_references
    
    async def _match_creative_references(self, parsed_refs: List[Dict[str, Any]]) -> List[CreativeReference]:
        """Match parsed references to database entries"""
        matches = []
        
        for ref in parsed_refs:
            reference_name = ref["reference"]
            
            # Try exact match
            exact_matches = self.creative_db.search_references(reference_name)
            if exact_matches:
                matches.extend(exact_matches[:2])  # Top 2 exact matches
                continue
            
            # Try fuzzy matching
            fuzzy_matches = self.creative_db.fuzzy_match(reference_name, limit=2)
            matches.extend([match[0] for match in fuzzy_matches])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_matches = []
        for match in matches:
            if match.name not in seen:
                seen.add(match.name)
                unique_matches.append(match)
        
        return unique_matches[:6]  # Limit to top 6 matches
    
    async def _analyze_style(self, references: List[CreativeReference], 
                           request: GenerationRequest) -> Dict[str, Any]:
        """Analyze the combined style from references"""
        
        if not references:
            return {"primary_style": "original", "elements": [], "confidence": 0.3}
        
        # Combine style elements from all references
        visual_styles = []
        color_palettes = []
        moods = []
        themes = []
        
        for ref in references:
            attrs = ref.attributes
            visual_styles.extend(attrs.get("visual_style", []))
            color_palettes.extend(attrs.get("color_palette", []))
            moods.extend(attrs.get("mood", []))
            themes.extend(attrs.get("themes", []))
        
        # Find most common elements
        from collections import Counter
        
        style_analysis = {
            "primary_references": [ref.name for ref in references[:3]],
            "dominant_visual_styles": [item for item, count in Counter(visual_styles).most_common(5)],
            "color_palette": [item for item, count in Counter(color_palettes).most_common(5)],
            "mood_elements": [item for item, count in Counter(moods).most_common(5)],
            "thematic_elements": [item for item, count in Counter(themes).most_common(5)],
            "style_combination_type": self._classify_style_combination(references),
            "complexity_score": min(len(references) * 0.2, 1.0),
            "confidence": min(sum(ref.popularity_score for ref in references) / len(references), 1.0)
        }
        
        return style_analysis
    
    async def _analyze_mood(self, references: List[CreativeReference], 
                          request: GenerationRequest) -> Dict[str, Any]:
        """Analyze the emotional mood from references"""
        
        if not references:
            return {"primary_mood": "neutral", "intensity": 0.5, "elements": []}
        
        # Extract mood elements
        all_moods = []
        for ref in references:
            all_moods.extend(ref.attributes.get("mood", []))
        
        from collections import Counter
        mood_counts = Counter(all_moods)
        
        # Classify mood intensity and type
        primary_mood = mood_counts.most_common(1)[0][0] if mood_counts else "neutral"
        
        # Map moods to intensity levels
        intensity_map = {
            "peaceful": 0.3, "calm": 0.3, "gentle": 0.3,
            "nostalgic": 0.4, "contemplative": 0.4, "melancholic": 0.4,
            "mysterious": 0.6, "dramatic": 0.7, "intense": 0.8,
            "epic": 0.9, "powerful": 0.9, "overwhelming": 1.0
        }
        
        intensity = intensity_map.get(primary_mood, 0.5)
        
        mood_analysis = {
            "primary_mood": primary_mood,
            "secondary_moods": [mood for mood, count in mood_counts.most_common(3)[1:]],
            "intensity": intensity,
            "emotional_arc": self._determine_emotional_arc(all_moods),
            "mood_consistency": self._calculate_mood_consistency(all_moods),
            "recommended_pacing": self._suggest_pacing_from_mood(primary_mood, intensity)
        }
        
        return mood_analysis
    
    async def _generate_assets_by_format(self, output_format: str, request: GenerationRequest,
                                       references: List[CreativeReference], 
                                       style_analysis: Dict[str, Any],
                                       mood_analysis: Dict[str, Any]) -> List[GeneratedAsset]:
        """Generate assets for a specific format"""
        
        assets = []
        
        if output_format == "text":
            assets.extend(await self._generate_text_assets(request, references, style_analysis))
        elif output_format == "image":
            assets.extend(await self._generate_image_assets(request, references, style_analysis))
        elif output_format == "audio":
            assets.extend(await self._generate_audio_assets(request, references, mood_analysis))
        elif output_format == "video":
            assets.extend(await self._generate_video_concepts(request, references, style_analysis))
        elif output_format == "3d":
            assets.extend(await self._generate_3d_concepts(request, references, style_analysis))
        
        return assets
    
    async def _generate_text_assets(self, request: GenerationRequest,
                                   references: List[CreativeReference],
                                   style_analysis: Dict[str, Any]) -> List[GeneratedAsset]:
        """Generate text-based creative assets"""
        
        assets = []
        
        # Generate enhanced descriptions
        if self.openai_available:
            enhanced_text = await self._ai_generate_text(request, references, style_analysis)
        else:
            enhanced_text = await self._template_generate_text(request, references, style_analysis)
        
        # Create different text variants
        assets.append(GeneratedAsset(
            asset_type="description",
            format="text",
            content=enhanced_text["detailed"],
            metadata={"style": "detailed", "word_count": len(enhanced_text["detailed"].split())},
            generation_params={"references": len(references), "style_strength": request.reference_strength},
            quality_score=0.8
        ))
        
        assets.append(GeneratedAsset(
            asset_type="description",
            format="text",
            content=enhanced_text["concise"],
            metadata={"style": "concise", "word_count": len(enhanced_text["concise"].split())},
            generation_params={"references": len(references), "style_strength": request.reference_strength},
            quality_score=0.8
        ))
        
        # Generate dialogue/voice samples if character
        if request.creative_type == CreativeType.CHARACTER:
            dialogue = await self._generate_character_dialogue(request, references)
            assets.append(GeneratedAsset(
                asset_type="dialogue",
                format="text",
                content=dialogue,
                metadata={"type": "sample_dialogue", "character_voice": True},
                generation_params={"voice_references": [ref.name for ref in references if "voice" in ref.attributes]},
                quality_score=0.7
            ))
        
        return assets
    
    async def _generate_image_assets(self, request: GenerationRequest,
                                   references: List[CreativeReference],
                                   style_analysis: Dict[str, Any]) -> List[GeneratedAsset]:
        """Generate image concepts and prompts"""
        
        assets = []
        
        # Build comprehensive image generation prompt
        prompt_parts = []
        
        # Add primary style references
        for ref in references[:3]:
            if ref.generation_prompts.get("image"):
                prompt_parts.append(ref.generation_prompts["image"])
        
        # Add style elements
        if style_analysis["dominant_visual_styles"]:
            prompt_parts.append(", ".join(style_analysis["dominant_visual_styles"][:3]))
        
        # Add color palette
        if style_analysis["color_palette"]:
            prompt_parts.append(f"color palette: {', '.join(style_analysis['color_palette'][:3])}")
        
        # Add mood
        if style_analysis["mood_elements"]:
            prompt_parts.append(f"{style_analysis['mood_elements'][0]} atmosphere")
        
        # Combine and clean
        full_prompt = f"{request.description}, " + ", ".join(prompt_parts)
        
        # Generate different prompt variants
        prompts = {
            "detailed": full_prompt,
            "artistic": f"artistic interpretation, {full_prompt}, highly detailed, professional artwork",
            "concept_art": f"concept art style, {full_prompt}, game art, illustration",
            "photographic": f"photographic style, {full_prompt}, professional photography, realistic"
        }
        
        for prompt_type, prompt_text in prompts.items():
            assets.append(GeneratedAsset(
                asset_type="image_prompt",
                format="text",
                content=prompt_text,
                metadata={
                    "prompt_type": prompt_type,
                    "style_references": [ref.name for ref in references[:3]],
                    "recommended_model": "stable-diffusion-xl" if prompt_type == "artistic" else "midjourney"
                },
                generation_params={
                    "style_strength": request.reference_strength,
                    "creativity": request.creativity_level
                },
                quality_score=0.85
            ))
        
        return assets
    
    async def _generate_audio_assets(self, request: GenerationRequest,
                                   references: List[CreativeReference],
                                   mood_analysis: Dict[str, Any]) -> List[GeneratedAsset]:
        """Generate audio concepts and specifications"""
        
        assets = []
        
        # Build audio generation specifications
        audio_refs = [ref for ref in references if ref.category == "audio" or "audio" in ref.attributes]
        
        if audio_refs:
            # Music generation prompt
            music_elements = []
            for ref in audio_refs:
                if ref.generation_prompts.get("audio"):
                    music_elements.append(ref.generation_prompts["audio"])
                if ref.attributes.get("instruments"):
                    music_elements.append(f"instruments: {', '.join(ref.attributes['instruments'][:3])}")
            
            music_prompt = f"{request.description}, " + ", ".join(music_elements)
            
            assets.append(GeneratedAsset(
                asset_type="music_prompt",
                format="text",
                content=music_prompt,
                metadata={
                    "primary_mood": mood_analysis["primary_mood"],
                    "intensity": mood_analysis["intensity"],
                    "recommended_bpm": self._suggest_bpm_from_mood(mood_analysis["primary_mood"]),
                    "key_signature": self._suggest_key_from_mood(mood_analysis["primary_mood"])
                },
                generation_params={
                    "mood_strength": request.reference_strength,
                    "audio_references": len(audio_refs)
                },
                quality_score=0.8
            ))
        
        # Sound design specifications
        sound_design = await self._generate_sound_design_spec(request, references, mood_analysis)
        assets.append(GeneratedAsset(
            asset_type="sound_design",
            format="json",
            content=json.dumps(sound_design),
            metadata={"type": "sound_design_specification"},
            generation_params={"mood_based": True},
            quality_score=0.7
        ))
        
        return assets

# Continue with the rest of the methods...

# FastAPI Application Setup
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting MakerLog Creative Likeness Engine...")
    yield
    logger.info("Shutting down MakerLog Creative Likeness Engine...")

app = FastAPI(
    title="MakerLog Creative Likeness Engine",
    description="AI-Powered Creative Asset Generation using Reference-Based Descriptions",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
creative_database = CreativeDatabase()
creative_generator = CreativeGenerator(creative_database)

@app.post("/generate-creative-assets", response_model=CreativeAnalysisResponse)
async def generate_creative_assets(request: GenerationRequest):
    """
    Generate creative assets based on reference descriptions.
    
    Example: "I want a character design like Studio Ghibli meets Tim Burton, 
    with the musical style of Hans Zimmer but more chill like lofi hip hop"
    """
    try:
        result = await creative_generator.generate_creative_assets(request)
        return result
    except Exception as e:
        logger.error(f"Asset generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/creative-inspiration")
async def get_creative_inspiration(
    creative_type: str = "character",
    category: Optional[str] = None,
    mood: Optional[str] = None
):
    """Get random creative inspiration combining different references"""
    try:
        import random
        
        # Get random references from different categories
        all_refs = list(creative_database.references.values())
        
        # Filter by category if specified
        if category:
            all_refs = [ref for ref in all_refs if ref.category == category]
        
        # Filter by mood if specified
        if mood:
            all_refs = [ref for ref in all_refs if mood in ref.attributes.get("mood", [])]
        
        # Select random combination
        selected_refs = random.sample(all_refs, min(3, len(all_refs)))
        
        inspiration = {
            "creative_type": creative_type,
            "inspiration_prompt": f"Create a {creative_type} that combines:",
            "primary_reference": {
                "name": selected_refs[0].name,
                "description": selected_refs[0].description,
                "key_elements": selected_refs[0].attributes.get("visual_style" if selected_refs[0].category == "visual" else "mood", [])[:3]
            },
            "secondary_reference": {
                "name": selected_refs[1].name if len(selected_refs) > 1 else None,
                "description": selected_refs[1].description if len(selected_refs) > 1 else None,
                "key_elements": selected_refs[1].attributes.get("visual_style" if len(selected_refs) > 1 and selected_refs[1].category == "visual" else "mood", [])[:3] if len(selected_refs) > 1 else []
            },
            "suggested_combination": f"A {creative_type} with the {selected_refs[0].category} style of {selected_refs[0].name}" + (f" combined with elements from {selected_refs[1].name}" if len(selected_refs) > 1 else ""),
            "remix_ideas": [
                f"What if {selected_refs[0].name} created something in the world of {selected_refs[1].name if len(selected_refs) > 1 else 'fantasy'}?",
                f"Blend the mood of {selected_refs[0].name} with modern technology",
                f"Take the visual style but completely reverse the emotional tone"
            ]
        }
        
        return inspiration
        
    except Exception as e:
        logger.error(f"Failed to generate inspiration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/style-analyzer")
async def analyze_existing_style(description: str):
    """Analyze an existing creative work and suggest similar references"""
    try:
        # Parse the description for style elements
        refs = await creative_generator._parse_creative_references(description)
        matched = await creative_generator._match_creative_references(refs)
        
        style_analysis = await creative_generator._analyze_style(matched, None)
        
        return {
            "analysis": style_analysis,
            "similar_references": [asdict(ref) for ref in matched],
            "style_tags": style_analysis.get("dominant_visual_styles", []),
            "mood_profile": style_analysis.get("mood_elements", []),
            "recommendations": f"This style is most similar to {matched[0].name if matched else 'original work'}"
        }
        
    except Exception as e:
        logger.error(f"Style analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "database_refs": len(creative_database.references),
        "ai_services": {
            "openai": creative_generator.openai_available,
            "stability_ai": creative_generator.stabilityai_available,
            "elevenlabs": creative_generator.elevenlabs_available
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8081,
        log_level="info"
    )