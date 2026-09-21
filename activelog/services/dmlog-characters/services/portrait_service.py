"""
Character portrait generation service.
"""

import os
import random
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
import logging

from ..models.portrait import (
    PortraitStyle, FacialExpression, EyeColor, HairColor, HairStyle, SkinTone, ClothingStyle,
    PhysicalAppearanceSchema, ClothingAppearanceSchema, PortraitGenerationRequest,
    PortraitGenerationResponse, PortraitVariationRequest, PortraitTemplateSchema,
    PortraitAnalysis, RacialFeatureSet, PortraitGenerationSettings,
    CharacterPortrait, PortraitTemplate, PortraitVariation
)
from ..models.base import CharacterType, CharacterRace, ArtStyle
from ..models.personality import PersonalityProfileSchema
from ..config import Config

logger = logging.getLogger(__name__)

class PortraitService:
    def __init__(self):
        self.config = Config()
        self.racial_features = self._initialize_racial_features()
        self.style_prompts = self._initialize_style_prompts()
        self.expression_modifiers = self._initialize_expression_modifiers()
        self.generation_settings = PortraitGenerationSettings()
        
        # In a real implementation, these would be actual AI model clients
        self.stable_diffusion_client = None  # Mock
        self.midjourney_client = None        # Mock
        self.dalle_client = None             # Mock
        
    def _initialize_racial_features(self) -> Dict[CharacterRace, RacialFeatureSet]:
        """Initialize racial feature sets for different character races."""
        return {
            CharacterRace.HUMAN: RacialFeatureSet(
                race=CharacterRace.HUMAN,
                typical_features={
                    "eye_shape": ["almond", "round", "hooded"],
                    "nose_shape": ["straight", "button", "roman"],
                    "face_shape": ["oval", "round", "square", "heart"]
                },
                rare_features={
                    "eye_color": ["violet", "amber"],
                    "hair_color": ["silver", "white"]
                },
                cultural_elements=["various_cultural_clothing", "diverse_accessories"],
                traditional_colors=["earth_tones", "royal_colors", "natural_dyes"]
            ),
            
            CharacterRace.ELF: RacialFeatureSet(
                race=CharacterRace.ELF,
                typical_features={
                    "ears": ["pointed", "long_pointed"],
                    "build": ["slender", "graceful"],
                    "eye_shape": ["almond", "large"],
                    "face_shape": ["oval", "angular"]
                },
                rare_features={
                    "eye_color": ["silver", "gold"],
                    "hair_color": ["silver", "platinum", "golden"]
                },
                cultural_elements=["nature_motifs", "elegant_clothing", "leaf_patterns"],
                traditional_colors=["forest_greens", "earth_browns", "sky_blues", "silver"]
            ),
            
            CharacterRace.DWARF: RacialFeatureSet(
                race=CharacterRace.DWARF,
                typical_features={
                    "build": ["stocky", "muscular", "broad"],
                    "facial_hair": ["full_beard", "braided_beard"],
                    "face_shape": ["square", "broad"]
                },
                rare_features={
                    "hair_color": ["bright_red", "steel_gray"],
                    "eye_color": ["amber", "steel_gray"]
                },
                cultural_elements=["clan_symbols", "metal_work", "gemstones"],
                traditional_colors=["earth_tones", "metal_colors", "gem_colors"]
            ),
            
            CharacterRace.HALFLING: RacialFeatureSet(
                race=CharacterRace.HALFLING,
                typical_features={
                    "build": ["small", "round", "cheerful"],
                    "feet": ["large", "furry"],
                    "face_shape": ["round", "friendly"]
                },
                rare_features={
                    "hair_color": ["unusual_curls"],
                    "height": ["unusually_tall_for_halfling"]
                },
                cultural_elements=["comfortable_clothing", "food_items", "rural_elements"],
                traditional_colors=["warm_browns", "greens", "comfortable_colors"]
            ),
            
            CharacterRace.ORC: RacialFeatureSet(
                race=CharacterRace.ORC,
                typical_features={
                    "tusks": ["prominent", "small"],
                    "build": ["muscular", "intimidating"],
                    "skin_tone": ["green", "gray"],
                    "face_shape": ["angular", "broad"]
                },
                rare_features={
                    "eye_color": ["red", "yellow"],
                    "skin_markings": ["war_paint", "scars"]
                },
                cultural_elements=["tribal_markings", "warrior_gear", "bone_accessories"],
                traditional_colors=["dark_colors", "blood_reds", "earth_tones"]
            ),
            
            CharacterRace.TIEFLING: RacialFeatureSet(
                race=CharacterRace.TIEFLING,
                typical_features={
                    "horns": ["curved", "straight", "spiral"],
                    "tail": ["long", "spaded"],
                    "skin_tone": ["red", "blue", "purple", "gray"],
                    "eyes": ["solid_color", "glowing"]
                },
                rare_features={
                    "eye_color": ["gold", "silver", "white"],
                    "horn_variations": ["multiple", "crystalline"]
                },
                cultural_elements=["infernal_symbols", "dark_elegance", "magical_items"],
                traditional_colors=["deep_reds", "purples", "blacks", "golds"]
            )
        }
    
    def _initialize_style_prompts(self) -> Dict[PortraitStyle, Dict[str, str]]:
        """Initialize art style specific prompt modifiers."""
        return {
            PortraitStyle.REALISTIC: {
                "base": "photorealistic, high detail, professional portrait photography",
                "quality": "8k resolution, sharp focus, professional lighting",
                "avoid": "cartoon, anime, stylized, painted"
            },
            
            PortraitStyle.ANIME: {
                "base": "anime style, manga art, cel shading",
                "quality": "high quality anime art, detailed shading, vibrant colors",
                "avoid": "realistic, photographic, western art style"
            },
            
            PortraitStyle.FANTASY_ART: {
                "base": "fantasy art, digital painting, epic fantasy style",
                "quality": "detailed fantasy illustration, dramatic lighting, rich colors",
                "avoid": "modern, contemporary, minimalist"
            },
            
            PortraitStyle.WATERCOLOR: {
                "base": "watercolor painting, soft brushstrokes, flowing colors",
                "quality": "artistic watercolor technique, paper texture, color bleeding",
                "avoid": "digital, sharp edges, solid colors"
            },
            
            PortraitStyle.PIXEL_ART: {
                "base": "pixel art, 16-bit style, retro gaming aesthetic",
                "quality": "clean pixels, limited color palette, sharp edges",
                "avoid": "smooth gradients, photorealistic, high resolution"
            }
        }
    
    def _initialize_expression_modifiers(self) -> Dict[FacialExpression, Dict[str, str]]:
        """Initialize facial expression modifiers for prompts."""
        return {
            FacialExpression.NEUTRAL: {
                "expression": "calm expression, relaxed face",
                "eyes": "neutral eyes",
                "mouth": "slight neutral expression"
            },
            
            FacialExpression.SMILING: {
                "expression": "warm smile, friendly expression",
                "eyes": "kind eyes, slight crinkles",
                "mouth": "gentle smile, upturned lips"
            },
            
            FacialExpression.ANGRY: {
                "expression": "angry expression, furrowed brow",
                "eyes": "intense glare, narrowed eyes",
                "mouth": "scowling, clenched jaw"
            },
            
            FacialExpression.MYSTERIOUS: {
                "expression": "mysterious smile, enigmatic look",
                "eyes": "knowing eyes, slight squint",
                "mouth": "subtle smirk, half-smile"
            },
            
            FacialExpression.CONFIDENT: {
                "expression": "confident expression, determined look",
                "eyes": "steady gaze, focused eyes",
                "mouth": "firm expression, slight smile"
            }
        }

    async def generate_portrait(
        self,
        request: PortraitGenerationRequest,
        personality: Optional[PersonalityProfileSchema] = None,
        character_background: Optional[Dict[str, Any]] = None,
        db_session: Optional[Session] = None
    ) -> PortraitGenerationResponse:
        """Generate a character portrait based on the request."""
        
        try:
            # Generate unique portrait ID
            portrait_id = self._generate_portrait_id(request)
            
            # Build generation prompt
            prompt = await self._build_generation_prompt(
                request, personality, character_background
            )
            
            # Determine optimal generation parameters
            gen_params = await self._determine_generation_parameters(request)
            
            # Generate the portrait (mock implementation)
            start_time = datetime.utcnow()
            image_path, quality_score = await self._generate_image(prompt, gen_params)
            generation_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Save portrait record
            await self._save_portrait_record(
                portrait_id, request, prompt, gen_params, 
                image_path, quality_score, generation_time, db_session
            )
            
            return PortraitGenerationResponse(
                portrait_id=portrait_id,
                character_id=request.character_id,
                generation_status="completed",
                image_url=image_path,
                generation_time=generation_time,
                quality_score=quality_score,
                generation_prompt=prompt
            )
            
        except Exception as e:
            logger.error(f"Portrait generation failed for character {request.character_id}: {str(e)}")
            
            return PortraitGenerationResponse(
                portrait_id=portrait_id if 'portrait_id' in locals() else "error",
                character_id=request.character_id,
                generation_status="failed",
                error_message=str(e)
            )

    async def generate_portrait_variation(
        self,
        variation_request: PortraitVariationRequest,
        db_session: Optional[Session] = None
    ) -> PortraitGenerationResponse:
        """Generate a variation of an existing portrait."""
        
        # Get base portrait
        base_portrait = await self._get_portrait(variation_request.base_portrait_id, db_session)
        if not base_portrait:
            return PortraitGenerationResponse(
                portrait_id="error",
                character_id="unknown",
                generation_status="failed",
                error_message="Base portrait not found"
            )
        
        # Create variation prompt based on base portrait and changes
        variation_prompt = await self._build_variation_prompt(
            base_portrait, variation_request
        )
        
        # Generate variation parameters
        gen_params = await self._determine_generation_parameters_for_variation(
            base_portrait, variation_request
        )
        
        # Generate the variation
        start_time = datetime.utcnow()
        image_path, quality_score = await self._generate_image(variation_prompt, gen_params)
        generation_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Save variation record
        variation_id = f"var_{variation_request.base_portrait_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        await self._save_variation_record(
            variation_id, variation_request, variation_prompt,
            image_path, quality_score, db_session
        )
        
        return PortraitGenerationResponse(
            portrait_id=variation_id,
            character_id=base_portrait.character_id,
            generation_status="completed",
            image_url=image_path,
            generation_time=generation_time,
            quality_score=quality_score,
            generation_prompt=variation_prompt
        )

    async def analyze_portrait_quality(
        self,
        portrait_id: str,
        db_session: Optional[Session] = None
    ) -> PortraitAnalysis:
        """Analyze the quality of a generated portrait."""
        
        portrait = await self._get_portrait(portrait_id, db_session)
        if not portrait:
            raise ValueError(f"Portrait {portrait_id} not found")
        
        # In a real implementation, this would use computer vision to analyze the image
        # For now, we'll return mock analysis
        return PortraitAnalysis(
            portrait_id=portrait_id,
            facial_feature_quality={
                "eyes": 0.85,
                "nose": 0.78,
                "mouth": 0.82,
                "ears": 0.75,
                "hair": 0.88
            },
            art_style_adherence=0.80,
            prompt_accuracy=0.83,
            technical_quality=0.85,
            overall_score=0.82,
            improvement_suggestions=[
                "Enhance ear detail",
                "Improve nose proportions",
                "Add more hair texture variation"
            ]
        )

    async def get_portrait_templates(
        self,
        race: Optional[CharacterRace] = None,
        character_type: Optional[CharacterType] = None,
        art_style: Optional[ArtStyle] = None
    ) -> List[PortraitTemplateSchema]:
        """Get available portrait templates based on filters."""
        
        # In a real implementation, this would query the database
        # For now, return mock templates
        mock_templates = [
            PortraitTemplateSchema(
                id="template_human_warrior_fantasy",
                template_name="Human Warrior Fantasy",
                race=CharacterRace.HUMAN,
                character_type=CharacterType.WARRIOR,
                art_style=ArtStyle.FANTASY,
                face_shape_options=["square", "oval", "angular"],
                eye_shape_options=["determined", "fierce", "focused"],
                clothing_options=["plate_armor", "chain_mail", "leather_armor"],
                pose_options=["heroic", "battle_ready", "noble"]
            ),
            PortraitTemplateSchema(
                id="template_elf_mage_mystical",
                template_name="Elf Mage Mystical",
                race=CharacterRace.ELF,
                character_type=CharacterType.MAGE,
                art_style=ArtStyle.MYSTICAL,
                face_shape_options=["angular", "delicate", "ethereal"],
                eye_shape_options=["wise", "magical", "ancient"],
                clothing_options=["robes", "mystical_garments", "nature_clothing"],
                pose_options=["casting", "contemplative", "wise"]
            )
        ]
        
        # Apply filters
        filtered_templates = []
        for template in mock_templates:
            if race and template.race != race:
                continue
            if character_type and template.character_type != character_type:
                continue
            if art_style and template.art_style != art_style:
                continue
            filtered_templates.append(template)
            
        return filtered_templates

    async def _build_generation_prompt(
        self,
        request: PortraitGenerationRequest,
        personality: Optional[PersonalityProfileSchema] = None,
        character_background: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build the complete generation prompt for the AI model."""
        
        prompt_parts = []
        
        # Base art style
        style_prompts = self.style_prompts.get(request.art_style, {})
        if "base" in style_prompts:
            prompt_parts.append(style_prompts["base"])
        
        # Character description
        char_description = await self._build_character_description(request)
        prompt_parts.append(char_description)
        
        # Physical features
        physical_description = await self._build_physical_description(
            request.physical_appearance, character_background
        )
        prompt_parts.append(physical_description)
        
        # Clothing and accessories
        clothing_description = await self._build_clothing_description(
            request.clothing_appearance
        )
        prompt_parts.append(clothing_description)
        
        # Facial expression
        expression_modifiers = self.expression_modifiers.get(request.expression, {})
        if "expression" in expression_modifiers:
            prompt_parts.append(expression_modifiers["expression"])
        
        # Personality influence
        if personality:
            personality_modifiers = await self._build_personality_modifiers(personality)
            if personality_modifiers:
                prompt_parts.append(personality_modifiers)
        
        # Pose and composition
        prompt_parts.append(f"{request.pose} pose")
        prompt_parts.append(f"{request.background} background")
        
        # Quality modifiers
        if "quality" in style_prompts:
            prompt_parts.append(style_prompts["quality"])
        
        # Custom additions
        if request.custom_prompt_additions:
            prompt_parts.append(request.custom_prompt_additions)
        
        # Negative prompt (what to avoid)
        if "avoid" in style_prompts:
            prompt_parts.append(f"NOT: {style_prompts['avoid']}")
        
        return ", ".join(prompt_parts)

    async def _build_character_description(
        self,
        request: PortraitGenerationRequest
    ) -> str:
        """Build basic character description."""
        
        # Determine race and type from physical appearance or character background
        # For now, using generic descriptions
        return "fantasy character portrait"

    async def _build_physical_description(
        self,
        appearance: PhysicalAppearanceSchema,
        background: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build physical appearance description for prompt."""
        
        description_parts = []
        
        # Basic features
        description_parts.append(f"{appearance.skin_tone.value} skin")
        description_parts.append(f"{appearance.eye_color.value} eyes")
        description_parts.append(f"{appearance.hair_color.value} {appearance.hair_style.value} hair")
        
        # Age appearance
        age_descriptor = self._get_age_descriptor(appearance.age_appearance)
        description_parts.append(f"{age_descriptor} appearance")
        
        # Build
        description_parts.append(f"{appearance.build} build")
        
        # Facial hair
        if appearance.facial_hair and appearance.facial_hair != "clean-shaven":
            description_parts.append(f"{appearance.facial_hair}")
        
        # Distinctive features
        if appearance.distinctive_features:
            description_parts.extend(appearance.distinctive_features)
        
        # Scars and marks
        if appearance.scars_marks:
            description_parts.extend(appearance.scars_marks)
        
        return ", ".join(description_parts)

    async def _build_clothing_description(
        self,
        clothing: ClothingAppearanceSchema
    ) -> str:
        """Build clothing and accessory description."""
        
        description_parts = []
        
        # Clothing style
        description_parts.append(f"{clothing.style.value} clothing")
        
        # Colors
        if clothing.colors:
            colors_text = " and ".join(clothing.colors)
            description_parts.append(f"{colors_text} colors")
        
        # Armor type
        if clothing.armor_type:
            description_parts.append(f"{clothing.armor_type} armor")
        
        # Accessories
        if clothing.accessories:
            accessories_text = ", ".join(clothing.accessories)
            description_parts.append(f"wearing {accessories_text}")
        
        # Visible weapon
        if clothing.weapon_visible:
            description_parts.append(f"{clothing.weapon_visible} weapon")
        
        # Magical effects
        if clothing.magical_effects:
            effects_text = ", ".join(clothing.magical_effects)
            description_parts.append(f"magical {effects_text}")
        
        return ", ".join(description_parts)

    async def _build_personality_modifiers(
        self,
        personality: PersonalityProfileSchema
    ) -> str:
        """Build personality-based visual modifiers."""
        
        modifiers = []
        
        # High extraversion = more expressive, open posture
        if personality.extraversion > 0.7:
            modifiers.append("expressive face, open posture")
        elif personality.extraversion < 0.3:
            modifiers.append("reserved expression, closed posture")
        
        # High conscientiousness = neat, orderly appearance
        if personality.conscientiousness > 0.7:
            modifiers.append("well-groomed, orderly appearance")
        elif personality.conscientiousness < 0.3:
            modifiers.append("casual, slightly disheveled")
        
        # High neuroticism = tense, worried expression
        if personality.neuroticism > 0.7:
            modifiers.append("tense expression, worried look")
        elif personality.neuroticism < 0.3:
            modifiers.append("calm, relaxed expression")
        
        # High openness = creative, artistic elements
        if personality.openness > 0.7:
            modifiers.append("artistic flair, creative elements")
        
        # High agreeableness = kind, warm expression
        if personality.agreeableness > 0.7:
            modifiers.append("kind eyes, warm expression")
        elif personality.agreeableness < 0.3:
            modifiers.append("stern look, cold expression")
        
        return ", ".join(modifiers) if modifiers else ""

    def _get_age_descriptor(self, age: int) -> str:
        """Get age descriptor from numerical age."""
        if age < 18:
            return "youthful"
        elif age < 30:
            return "young adult"
        elif age < 50:
            return "mature"
        elif age < 65:
            return "middle-aged"
        else:
            return "elderly"

    async def _determine_generation_parameters(
        self,
        request: PortraitGenerationRequest
    ) -> Dict[str, Any]:
        """Determine optimal generation parameters for the request."""
        
        quality_settings = {
            "low": {"resolution": (512, 512), "steps": 20, "guidance": 7.0},
            "medium": {"resolution": (768, 768), "steps": 30, "guidance": 7.5},
            "high": {"resolution": (1024, 1024), "steps": 50, "guidance": 8.0},
            "ultra": {"resolution": (1536, 1536), "steps": 80, "guidance": 8.5}
        }
        
        base_params = quality_settings.get(request.quality_level, quality_settings["high"])
        
        # Style-specific adjustments
        if request.art_style == PortraitStyle.PIXEL_ART:
            base_params["resolution"] = (256, 256)  # Lower res for pixel art
        elif request.art_style == PortraitStyle.REALISTIC:
            base_params["guidance"] = 9.0  # Higher guidance for realism
        
        return base_params

    async def _generate_image(
        self,
        prompt: str,
        parameters: Dict[str, Any]
    ) -> Tuple[str, float]:
        """Generate the actual image (mock implementation)."""
        
        # In a real implementation, this would call an AI image generation service
        # For now, we'll simulate the process
        
        # Simulate generation time
        import asyncio
        import random
        await asyncio.sleep(random.uniform(1, 3))  # Simulate generation time
        
        # Mock file path
        filename = f"portrait_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        image_path = f"/portraits/{filename}"
        
        # Mock quality score
        quality_score = random.uniform(0.7, 0.95)
        
        logger.info(f"Generated portrait at {image_path} with quality {quality_score}")
        
        return image_path, quality_score

    def _generate_portrait_id(self, request: PortraitGenerationRequest) -> str:
        """Generate a unique portrait ID."""
        content = f"{request.character_id}_{request.art_style.value}_{datetime.now().isoformat()}"
        hash_digest = hashlib.md5(content.encode()).hexdigest()[:12]
        return f"port_{hash_digest}"

    async def _save_portrait_record(
        self,
        portrait_id: str,
        request: PortraitGenerationRequest,
        prompt: str,
        parameters: Dict[str, Any],
        image_path: str,
        quality_score: float,
        generation_time: float,
        db_session: Optional[Session]
    ) -> None:
        """Save portrait record to database."""
        
        # In a real implementation, this would save to database
        logger.info(f"Saved portrait record {portrait_id} for character {request.character_id}")

    async def _build_variation_prompt(
        self,
        base_portrait: CharacterPortrait,
        variation_request: PortraitVariationRequest
    ) -> str:
        """Build prompt for portrait variation."""
        
        # Start with base portrait prompt
        base_prompt = base_portrait.generation_prompt or ""
        
        # Apply changes based on variation request
        variation_parts = [base_prompt]
        
        for feature, new_value in variation_request.changed_features.items():
            variation_parts.append(f"modified {feature}: {new_value}")
        
        # Add custom additions
        if variation_request.custom_prompt_additions:
            variation_parts.append(variation_request.custom_prompt_additions)
        
        return ", ".join(variation_parts)

    async def _determine_generation_parameters_for_variation(
        self,
        base_portrait: CharacterPortrait,
        variation_request: PortraitVariationRequest
    ) -> Dict[str, Any]:
        """Determine generation parameters for variation."""
        
        # Use base portrait's parameters as starting point
        if base_portrait.generation_parameters:
            return base_portrait.generation_parameters.copy()
        
        # Fallback to default high quality
        return {
            "resolution": (1024, 1024),
            "steps": 50,
            "guidance": 8.0
        }

    async def _save_variation_record(
        self,
        variation_id: str,
        variation_request: PortraitVariationRequest,
        prompt: str,
        image_path: str,
        quality_score: float,
        db_session: Optional[Session]
    ) -> None:
        """Save variation record to database."""
        
        # In a real implementation, this would save to database
        logger.info(f"Saved variation record {variation_id}")

    async def _get_portrait(
        self,
        portrait_id: str,
        db_session: Optional[Session]
    ) -> Optional[CharacterPortrait]:
        """Get portrait from database."""
        
        # In a real implementation, this would query the database
        # For now, return a mock portrait
        if portrait_id.startswith("port_"):
            return CharacterPortrait(
                id=portrait_id,
                character_id="char_123",
                portrait_name="Mock Portrait",
                art_style="fantasy_art",
                generation_prompt="fantasy character portrait",
                generation_parameters={"resolution": (1024, 1024)}
            )
        return None