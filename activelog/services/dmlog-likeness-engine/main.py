#!/usr/bin/env python3
"""
DMLog Likeness Engine - AI-Powered Character, Scene, and Plot Description Tool
Allows creators to describe NPCs, scenes, and plots using references to real actors, 
fictional characters, movies, books, and other media for vivid, relatable descriptions.
"""

import asyncio
import json
import time
import uuid
import re
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import openai
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import sqlite3
import threading
from contextlib import asynccontextmanager
from collections import defaultdict
import difflib
from fuzzywuzzy import fuzz, process

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Data Models
class LikenessType(str):
    CHARACTER = "character"
    SCENE = "scene"
    PLOT = "plot"
    MOOD = "mood"
    VOICE = "voice"
    MANNERISM = "mannerism"

@dataclass
class MediaReference:
    name: str
    type: str  # actor, character, movie, book, tv_show, game, etc.
    description: str
    attributes: Dict[str, Any]
    popularity_score: float
    tags: List[str]

@dataclass
class LikenessMatch:
    reference: MediaReference
    confidence: float
    matching_attributes: List[str]
    description: str
    usage_context: str

class LikenessRequest(BaseModel):
    description: str = Field(..., description="User's description using likeness references")
    creation_type: str = Field(..., description="character, scene, plot, etc.")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Campaign context")
    style_preferences: Optional[List[str]] = Field(default=None, description="Preferred genres/styles")
    exclude_references: Optional[List[str]] = Field(default=None, description="References to avoid")

class LikenessResponse(BaseModel):
    original_description: str
    parsed_references: List[Dict[str, Any]]
    enhanced_description: str
    visual_description: str
    personality_traits: List[str]
    suggested_voice: Dict[str, str]
    mannerisms: List[str]
    similar_characters: List[Dict[str, Any]]
    dm_notes: List[str]
    player_description: str
    confidence_score: float

class MediaDatabase:
    """Comprehensive database of media references for likeness matching"""
    
    def __init__(self):
        self.db_path = "data/likeness_database.db"
        self.references = {}
        self._init_database()
        self._populate_initial_data()
    
    def _init_database(self):
        """Initialize the database schema"""
        Path("data").mkdir(exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS media_references (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                description TEXT,
                attributes TEXT,
                popularity_score REAL,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS likeness_cache (
                id TEXT PRIMARY KEY,
                input_hash TEXT NOT NULL,
                result TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _populate_initial_data(self):
        """Populate database with comprehensive media references"""
        initial_data = [
            # Actors
            {
                "name": "Johnny Depp",
                "type": "actor",
                "description": "Eccentric character actor known for unique mannerisms and mysterious charm",
                "attributes": {
                    "facial_features": ["angular cheekbones", "expressive eyes", "distinctive smile"],
                    "mannerisms": ["head tilts", "hand gestures", "slight swagger"],
                    "voice": ["smooth", "slightly raspy", "articulate"],
                    "personality_archetypes": ["eccentric", "mysterious", "charismatic", "unpredictable"]
                },
                "popularity_score": 0.95,
                "tags": ["pirate", "gothic", "eccentric", "mysterious", "charismatic"]
            },
            {
                "name": "Sean Connery",
                "type": "actor",
                "description": "Classic Bond actor with commanding presence and sophisticated charm",
                "attributes": {
                    "facial_features": ["strong jaw", "piercing eyes", "confident smile"],
                    "mannerisms": ["raised eyebrow", "confident posture", "slight smirk"],
                    "voice": ["deep", "Scottish accent", "authoritative", "smooth"],
                    "personality_archetypes": ["sophisticated", "confident", "commanding", "suave"]
                },
                "popularity_score": 0.92,
                "tags": ["bond", "sophisticated", "spy", "suave", "classic"]
            },
            
            # Disney Villains
            {
                "name": "Jafar",
                "type": "character",
                "description": "Scheming sorcerer from Disney's Aladdin with theatrical villainy",
                "attributes": {
                    "facial_features": ["thin mustache", "angular features", "menacing eyes"],
                    "mannerisms": ["dramatic gestures", "finger pointing", "cape flourishing"],
                    "voice": ["theatrical", "sinister", "articulate", "commanding"],
                    "personality_archetypes": ["scheming", "power-hungry", "theatrical", "intelligent"]
                },
                "popularity_score": 0.88,
                "tags": ["disney", "villain", "sorcerer", "scheming", "theatrical"]
            },
            {
                "name": "Scar",
                "type": "character", 
                "description": "Manipulative lion from Disney's Lion King with sardonic wit",
                "attributes": {
                    "facial_features": ["scarred eye", "lean build", "dark mane"],
                    "mannerisms": ["languid movements", "claw inspection", "sarcastic expressions"],
                    "voice": ["British accent", "sardonic", "smooth", "condescending"],
                    "personality_archetypes": ["manipulative", "sarcastic", "intelligent", "bitter"]
                },
                "popularity_score": 0.90,
                "tags": ["disney", "villain", "sarcastic", "manipulative", "british"]
            },
            
            # Bond Villains
            {
                "name": "Goldfinger",
                "type": "character",
                "description": "Classic Bond villain with obsessive attention to detail and gold fixation",
                "attributes": {
                    "facial_features": ["round face", "calculating eyes", "slight smile"],
                    "mannerisms": ["finger steepling", "gold object handling", "measured speech"],
                    "voice": ["accented", "calm", "calculated", "precise"],
                    "personality_archetypes": ["obsessive", "calculating", "methodical", "greedy"]
                },
                "popularity_score": 0.85,
                "tags": ["bond", "villain", "obsessive", "gold", "calculating"]
            },
            {
                "name": "Ernst Stavro Blofeld",
                "type": "character",
                "description": "Mastermind Bond villain with cat-stroking menace and calm evil",
                "attributes": {
                    "facial_features": ["bald head", "scar", "cold eyes"],
                    "mannerisms": ["cat stroking", "calm demeanor", "finger tapping"],
                    "voice": ["calm", "measured", "threatening", "sophisticated"],
                    "personality_archetypes": ["mastermind", "calm", "methodical", "ruthless"]
                },
                "popularity_score": 0.87,
                "tags": ["bond", "villain", "mastermind", "bald", "cat", "calm"]
            },
            
            # Fantasy Archetypes
            {
                "name": "Gollum/Sméagol",
                "type": "character",
                "description": "Dual personality creature from Lord of the Rings with internal conflict",
                "attributes": {
                    "facial_features": ["large eyes", "thin build", "gaunt features"],
                    "mannerisms": ["hissing speech", "internal dialogue", "precious gestures"],
                    "voice": ["dual tones", "hissing", "whispering", "internal conflict"],
                    "personality_archetypes": ["corrupted", "conflicted", "obsessive", "tragic"]
                },
                "popularity_score": 0.93,
                "tags": ["fantasy", "corrupted", "dual personality", "tragic", "obsessive"]
            },
            
            # More Actors for Reference
            {
                "name": "Christopher Walken",
                "type": "actor",
                "description": "Distinctive actor known for unusual cadence and intense stare",
                "attributes": {
                    "facial_features": ["intense eyes", "sharp features", "distinctive smile"],
                    "mannerisms": ["unique speech rhythm", "intense stare", "hand movements"],
                    "voice": ["distinctive cadence", "pause-heavy", "intense", "unique rhythm"],
                    "personality_archetypes": ["intense", "unpredictable", "menacing", "unique"]
                },
                "popularity_score": 0.89,
                "tags": ["intense", "unique", "menacing", "distinctive", "unpredictable"]
            },
            {
                "name": "Ian McKellen",
                "type": "actor",
                "description": "Classically trained actor known for wise mentor roles and theatrical presence",
                "attributes": {
                    "facial_features": ["wise eyes", "expressive face", "dignified bearing"],
                    "mannerisms": ["theatrical gestures", "knowing looks", "staff wielding"],
                    "voice": ["authoritative", "warm", "theatrical", "British"],
                    "personality_archetypes": ["wise", "mentoring", "powerful", "dignified"]
                },
                "popularity_score": 0.91,
                "tags": ["wizard", "mentor", "wise", "theatrical", "british", "gandalf"]
            }
        ]
        
        for ref_data in initial_data:
            self.add_reference(MediaReference(
                name=ref_data["name"],
                type=ref_data["type"],
                description=ref_data["description"],
                attributes=ref_data["attributes"],
                popularity_score=ref_data["popularity_score"],
                tags=ref_data["tags"]
            ))
    
    def add_reference(self, reference: MediaReference):
        """Add a media reference to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        ref_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT OR REPLACE INTO media_references 
            (id, name, type, description, attributes, popularity_score, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            ref_id,
            reference.name,
            reference.type,
            reference.description,
            json.dumps(reference.attributes),
            reference.popularity_score,
            json.dumps(reference.tags)
        ))
        
        conn.commit()
        conn.close()
        
        self.references[reference.name.lower()] = reference
    
    def search_references(self, query: str, ref_type: str = None) -> List[MediaReference]:
        """Search for references by name, description, or tags"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        base_query = """
            SELECT name, type, description, attributes, popularity_score, tags
            FROM media_references
            WHERE (LOWER(name) LIKE ? OR LOWER(description) LIKE ? OR LOWER(tags) LIKE ?)
        """
        params = [f"%{query.lower()}%"] * 3
        
        if ref_type:
            base_query += " AND type = ?"
            params.append(ref_type)
        
        base_query += " ORDER BY popularity_score DESC"
        
        cursor.execute(base_query, params)
        results = cursor.fetchall()
        conn.close()
        
        references = []
        for row in results:
            references.append(MediaReference(
                name=row[0],
                type=row[1],
                description=row[2],
                attributes=json.loads(row[3]) if row[3] else {},
                popularity_score=row[4],
                tags=json.loads(row[5]) if row[5] else []
            ))
        
        return references
    
    def fuzzy_match(self, query: str, limit: int = 5) -> List[Tuple[MediaReference, float]]:
        """Perform fuzzy matching on reference names"""
        all_names = list(self.references.keys())
        matches = process.extract(query.lower(), all_names, limit=limit)
        
        results = []
        for name, score in matches:
            if score > 60:  # Minimum similarity threshold
                results.append((self.references[name], score / 100.0))
        
        return results

class LikenessAnalyzer:
    """AI-powered analyzer for parsing and enhancing likeness descriptions"""
    
    def __init__(self, media_db: MediaDatabase):
        self.media_db = media_db
        self.openai_client = None
        self._init_openai()
    
    def _init_openai(self):
        """Initialize OpenAI client if API key is available"""
        try:
            import os
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                openai.api_key = api_key
                self.openai_client = openai
                logger.info("OpenAI client initialized")
            else:
                logger.warning("No OpenAI API key found - using fallback analysis")
        except Exception as e:
            logger.warning(f"OpenAI initialization failed: {e}")
    
    async def analyze_likeness(self, request: LikenessRequest) -> LikenessResponse:
        """Main analysis function that processes likeness descriptions"""
        
        # Step 1: Parse references from the description
        parsed_refs = await self._parse_references(request.description)
        
        # Step 2: Match references to database entries
        matched_refs = await self._match_references(parsed_refs)
        
        # Step 3: Generate enhanced description
        enhanced_desc = await self._generate_enhanced_description(
            request, matched_refs
        )
        
        # Step 4: Extract specific attributes
        attributes = await self._extract_attributes(matched_refs, request)
        
        # Step 5: Generate suggestions
        suggestions = await self._generate_suggestions(matched_refs, request)
        
        return LikenessResponse(
            original_description=request.description,
            parsed_references=[asdict(ref) for ref in parsed_refs],
            enhanced_description=enhanced_desc["full"],
            visual_description=enhanced_desc["visual"],
            personality_traits=attributes["personality"],
            suggested_voice=attributes["voice"],
            mannerisms=attributes["mannerisms"],
            similar_characters=suggestions["similar"],
            dm_notes=suggestions["dm_notes"],
            player_description=enhanced_desc["player"],
            confidence_score=self._calculate_confidence(matched_refs)
        )
    
    async def _parse_references(self, description: str) -> List[Dict[str, Any]]:
        """Parse and extract media references from the description"""
        
        # Common patterns for reference extraction
        patterns = [
            # "like [character/person] from [media]"
            r"like\s+([^,\s]+(?:\s+[^,\s]+)*?)\s+(?:from|in)\s+([^,\.\!]+)",
            # "acts like [character/person]"
            r"acts\s+like\s+([^,\.\!]+)",
            # "looks like [person]"
            r"looks?\s+(?:like|similar to)\s+([^,\.\!]+)",
            # "sounds like [person]"
            r"sounds?\s+like\s+([^,\.\!]+)",
            # "has the [attribute] of [person]"
            r"has\s+the\s+([^,\s]+(?:\s+[^,\s]+)*?)\s+of\s+([^,\.\!]+)",
            # "reminds me of [person/character]"
            r"reminds?\s+me\s+of\s+([^,\.\!]+)",
            # "[person]-like" or "[person]-esque"
            r"([^,\s]+(?:\s+[^,\s]+)*?)[-\s](?:like|esque|style|ish)",
        ]
        
        parsed_references = []
        
        for pattern in patterns:
            matches = re.finditer(pattern, description, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) == 2:
                    attribute, reference = match.groups()
                    parsed_references.append({
                        "reference": reference.strip(),
                        "attribute": attribute.strip(),
                        "context": match.group(0),
                        "type": "attributed"
                    })
                else:
                    reference = match.group(1).strip()
                    parsed_references.append({
                        "reference": reference,
                        "attribute": None,
                        "context": match.group(0),
                        "type": "direct"
                    })
        
        # Additional AI-powered parsing if OpenAI is available
        if self.openai_client:
            ai_refs = await self._ai_parse_references(description)
            parsed_references.extend(ai_refs)
        
        return parsed_references
    
    async def _ai_parse_references(self, description: str) -> List[Dict[str, Any]]:
        """Use AI to parse more complex reference patterns"""
        try:
            prompt = f"""
            Analyze this character/scene description and extract all references to real people, fictional characters, movies, books, TV shows, or other media:

            "{description}"

            Return a JSON array of references found, each with:
            - "reference": the name of person/character/media
            - "attribute": what specific trait is being referenced (appearance, personality, voice, etc.)
            - "context": the specific part of the description
            - "confidence": confidence level (0-1)

            Focus on implicit references and cultural knowledge.
            """
            
            response = await self.openai_client.ChatCompletion.acreate(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            # Parse JSON response
            import json
            references = json.loads(content)
            return references
            
        except Exception as e:
            logger.warning(f"AI reference parsing failed: {e}")
            return []
    
    async def _match_references(self, parsed_refs: List[Dict[str, Any]]) -> List[LikenessMatch]:
        """Match parsed references to database entries"""
        matches = []
        
        for ref in parsed_refs:
            reference_name = ref["reference"]
            
            # Try exact match first
            exact_matches = self.media_db.search_references(reference_name)
            if exact_matches:
                for match in exact_matches[:3]:  # Top 3 exact matches
                    matches.append(LikenessMatch(
                        reference=match,
                        confidence=0.95,
                        matching_attributes=[ref.get("attribute", "general")],
                        description=f"Exact match for {reference_name}",
                        usage_context=ref.get("context", "")
                    ))
                continue
            
            # Try fuzzy matching
            fuzzy_matches = self.media_db.fuzzy_match(reference_name, limit=3)
            for match_ref, similarity in fuzzy_matches:
                matches.append(LikenessMatch(
                    reference=match_ref,
                    confidence=similarity * 0.8,  # Reduce confidence for fuzzy matches
                    matching_attributes=[ref.get("attribute", "general")],
                    description=f"Similar to {reference_name} (fuzzy match)",
                    usage_context=ref.get("context", "")
                ))
        
        # Sort by confidence and remove duplicates
        unique_matches = {}
        for match in matches:
            key = match.reference.name
            if key not in unique_matches or match.confidence > unique_matches[key].confidence:
                unique_matches[key] = match
        
        return sorted(unique_matches.values(), key=lambda x: x.confidence, reverse=True)
    
    async def _generate_enhanced_description(self, request: LikenessRequest, 
                                           matches: List[LikenessMatch]) -> Dict[str, str]:
        """Generate enhanced descriptions based on matched references"""
        
        if not matches:
            return {
                "full": request.description,
                "visual": "No specific visual references found.",
                "player": request.description
            }
        
        # Build context from matches
        context_parts = []
        for match in matches[:5]:  # Top 5 matches
            ref = match.reference
            context_parts.append(f"- {ref.name} ({ref.type}): {ref.description}")
        
        context = "\n".join(context_parts)
        
        if self.openai_client:
            return await self._ai_generate_description(request, context, matches)
        else:
            return await self._template_generate_description(request, matches)
    
    async def _ai_generate_description(self, request: LikenessRequest, 
                                     context: str, matches: List[LikenessMatch]) -> Dict[str, str]:
        """Use AI to generate enhanced descriptions"""
        try:
            prompt = f"""
            Create an enhanced D&D character description based on these references:

            Original description: "{request.description}"
            Type: {request.creation_type}

            Reference context:
            {context}

            Generate three versions:
            1. FULL: A detailed description for the DM (2-3 paragraphs)
            2. VISUAL: Focus only on physical appearance (1 paragraph)  
            3. PLAYER: A version suitable for players to read (1-2 paragraphs, no spoilers)

            Make the description vivid and immersive while maintaining the essence of the references.
            Use D&D appropriate language and fantasy context.
            
            Format as JSON with "full", "visual", and "player" keys.
            """
            
            response = await self.openai_client.ChatCompletion.acreate(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
            
        except Exception as e:
            logger.warning(f"AI description generation failed: {e}")
            return await self._template_generate_description(request, matches)
    
    async def _template_generate_description(self, request: LikenessRequest, 
                                           matches: List[LikenessMatch]) -> Dict[str, str]:
        """Generate descriptions using templates when AI is not available"""
        
        primary_match = matches[0] if matches else None
        
        if not primary_match:
            return {
                "full": request.description,
                "visual": "A distinctive character with memorable features.",
                "player": request.description
            }
        
        ref = primary_match.reference
        
        # Template-based generation
        full_desc = f"""
        This character draws inspiration from {ref.name}, known for {ref.description}. 
        {request.description}
        
        Like {ref.name}, they possess {"notable characteristics" if not ref.attributes else ', '.join(ref.attributes.get('personality_archetypes', ['distinctive qualities']))}. 
        Their presence commands attention through {"their unique mannerisms" if not ref.attributes else ', '.join(ref.attributes.get('mannerisms', ['distinctive behaviors']))}.
        """
        
        visual_desc = f"""
        Physically, they share traits reminiscent of {ref.name}, featuring {', '.join(ref.attributes.get('facial_features', ['distinctive features'])) if ref.attributes else 'memorable features'}.
        Their overall appearance suggests {"a unique presence" if not ref.attributes else ref.description}.
        """
        
        player_desc = f"""
        You encounter a character whose presence is immediately striking. 
        {request.description.replace('like', 'reminiscent of').replace('acts like', 'has mannerisms similar to')}
        Their demeanor suggests {"interesting depth" if not ref.attributes else ', '.join(ref.attributes.get('personality_archetypes', ['complex personality'])[:2])}.
        """
        
        return {
            "full": full_desc.strip(),
            "visual": visual_desc.strip(),
            "player": player_desc.strip()
        }
    
    async def _extract_attributes(self, matches: List[LikenessMatch], 
                                request: LikenessRequest) -> Dict[str, Any]:
        """Extract specific attributes from matches"""
        
        personality_traits = set()
        voice_attributes = {}
        mannerisms = set()
        
        for match in matches[:3]:  # Top 3 matches
            ref = match.reference
            if ref.attributes:
                # Personality traits
                personality_traits.update(ref.attributes.get('personality_archetypes', []))
                
                # Voice attributes
                voice_attrs = ref.attributes.get('voice', [])
                if voice_attrs:
                    voice_attributes[ref.name] = voice_attrs
                
                # Mannerisms
                mannerisms.update(ref.attributes.get('mannerisms', []))
        
        # Combine voice attributes
        combined_voice = {}
        if voice_attributes:
            all_voice_attrs = []
            for attrs in voice_attributes.values():
                all_voice_attrs.extend(attrs)
            
            # Count frequency of voice attributes
            from collections import Counter
            voice_counts = Counter(all_voice_attrs)
            most_common = voice_counts.most_common(3)
            
            combined_voice = {
                "primary_qualities": [attr for attr, count in most_common],
                "suggested_description": f"A voice that is {', '.join([attr for attr, count in most_common[:2]])}"
            }
        
        return {
            "personality": list(personality_traits)[:8],  # Limit to most relevant
            "voice": combined_voice,
            "mannerisms": list(mannerisms)[:6]  # Limit to most relevant
        }
    
    async def _generate_suggestions(self, matches: List[LikenessMatch], 
                                  request: LikenessRequest) -> Dict[str, Any]:
        """Generate similar characters and DM notes"""
        
        similar_characters = []
        dm_notes = []
        
        if matches:
            # Find similar characters based on tags and attributes
            primary_match = matches[0]
            primary_tags = set(primary_match.reference.tags)
            
            # Search for characters with similar tags
            for tag in list(primary_tags)[:3]:  # Top 3 tags
                similar_refs = self.media_db.search_references(tag, ref_type="character")
                for ref in similar_refs[:2]:  # Limit results
                    if ref.name != primary_match.reference.name:
                        similar_characters.append({
                            "name": ref.name,
                            "description": ref.description,
                            "similarity_reason": f"Shares the '{tag}' archetype",
                            "reference_type": ref.type
                        })
            
            # Generate DM notes
            dm_notes = [
                f"Primary inspiration: {primary_match.reference.name} - {primary_match.reference.description}",
                f"Key traits to emphasize: {', '.join(primary_match.reference.attributes.get('personality_archetypes', ['distinctive personality'])[:3]) if primary_match.reference.attributes else 'unique characteristics'}",
            ]
            
            if len(matches) > 1:
                secondary = matches[1]
                dm_notes.append(f"Secondary influence: {secondary.reference.name} - incorporate their {', '.join(secondary.reference.attributes.get('mannerisms', ['distinctive style'])[:2]) if secondary.reference.attributes else 'style'}")
            
            if request.context:
                dm_notes.append(f"Campaign context: Adapt to fit {request.context.get('setting', 'your campaign setting')}")
        
        return {
            "similar": similar_characters[:5],  # Limit to 5
            "dm_notes": dm_notes[:5]  # Limit to 5
        }
    
    def _calculate_confidence(self, matches: List[LikenessMatch]) -> float:
        """Calculate overall confidence in the likeness analysis"""
        if not matches:
            return 0.0
        
        # Weight confidence by match quality and quantity
        total_confidence = 0.0
        weight_sum = 0.0
        
        for i, match in enumerate(matches[:5]):  # Top 5 matches
            weight = 1.0 / (i + 1)  # Decreasing weight
            total_confidence += match.confidence * weight
            weight_sum += weight
        
        return min(total_confidence / weight_sum if weight_sum > 0 else 0.0, 1.0)

# FastAPI Application
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting DMLog Likeness Engine...")
    yield
    logger.info("Shutting down DMLog Likeness Engine...")

app = FastAPI(
    title="DMLog Likeness Engine",
    description="AI-Powered Character, Scene, and Plot Description Tool using Media References",
    version="1.0.0",
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
media_database = MediaDatabase()
likeness_analyzer = LikenessAnalyzer(media_database)

@app.post("/analyze-likeness", response_model=LikenessResponse)
async def analyze_likeness(request: LikenessRequest):
    """
    Analyze a character, scene, or plot description using media references.
    
    Example: "I need a goblin that acts like Jafar from Disney's Aladdin, 
    looks a little like Johnny Depp but has the facial expressions of an old school Bond villain."
    """
    try:
        result = await likeness_analyzer.analyze_likeness(request)
        return result
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search-references")
async def search_references(
    query: str,
    ref_type: Optional[str] = None,
    limit: int = 10
):
    """Search for media references in the database"""
    try:
        references = media_database.search_references(query, ref_type)
        return {
            "query": query,
            "results": [asdict(ref) for ref in references[:limit]],
            "total_found": len(references)
        }
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/add-reference")
async def add_reference(reference_data: Dict[str, Any]):
    """Add a new media reference to the database"""
    try:
        reference = MediaReference(
            name=reference_data["name"],
            type=reference_data["type"],
            description=reference_data["description"],
            attributes=reference_data.get("attributes", {}),
            popularity_score=reference_data.get("popularity_score", 0.5),
            tags=reference_data.get("tags", [])
        )
        
        media_database.add_reference(reference)
        
        return {
            "message": "Reference added successfully",
            "reference": asdict(reference)
        }
    except Exception as e:
        logger.error(f"Failed to add reference: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/random-inspiration")
async def get_random_inspiration(creation_type: str = "character"):
    """Get random inspiration for character/scene creation"""
    try:
        import random
        
        # Get random references
        all_refs = media_database.search_references("", ref_type=None)
        random_refs = random.sample(all_refs, min(3, len(all_refs)))
        
        inspiration = {
            "creation_type": creation_type,
            "inspiration_prompt": f"Create a {creation_type} that combines elements from these references:",
            "references": [
                {
                    "name": ref.name,
                    "type": ref.type,
                    "description": ref.description,
                    "key_traits": ref.attributes.get("personality_archetypes", [])[:3] if ref.attributes else []
                }
                for ref in random_refs
            ],
            "suggested_combination": f"A {creation_type} with the {random_refs[0].attributes.get('personality_archetypes', ['personality'])[0] if random_refs[0].attributes else 'traits'} of {random_refs[0].name}, the {random_refs[1].attributes.get('mannerisms', ['style'])[0] if len(random_refs) > 1 and random_refs[1].attributes else 'appearance'} of {random_refs[1].name if len(random_refs) > 1 else 'someone distinctive'}, and the {random_refs[2].attributes.get('voice', ['voice'])[0] if len(random_refs) > 2 and random_refs[2].attributes else 'presence'} of {random_refs[2].name if len(random_refs) > 2 else 'a memorable character'}."
        }
        
        return inspiration
        
    except Exception as e:
        logger.error(f"Failed to generate inspiration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "database_refs": len(media_database.references),
        "ai_enabled": likeness_analyzer.openai_client is not None
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8080,
        log_level="info"
    )