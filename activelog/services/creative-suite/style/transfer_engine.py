"""
ActiveLog Creative Suite - Style Transfer Between Mediums

This module provides intelligent style transfer capabilities across different creative mediums including:
- Visual style extraction and application (painting to digital, photo to illustration)
- Musical style analysis and cross-genre transfer
- Writing style adaptation between formats and genres
- Design pattern migration across mediums
- Color palette and mood translation
- Texture and material style conversion
- Temporal style mapping (vintage to modern, etc.)
- Cultural style interpretation and adaptation
"""

import asyncio
import json
import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
import io
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CreativeMedium(Enum):
    """Different creative mediums for style transfer"""
    VISUAL_ART = "visual_art"
    DIGITAL_ART = "digital_art"
    PHOTOGRAPHY = "photography"
    ILLUSTRATION = "illustration"
    MUSIC = "music"
    WRITING = "writing"
    DESIGN = "design"
    SCULPTURE = "sculpture"
    FILM = "film"
    ANIMATION = "animation"
    FASHION = "fashion"
    ARCHITECTURE = "architecture"


class StyleAttribute(Enum):
    """Attributes that define a creative style"""
    COLOR_PALETTE = "color_palette"
    TEXTURE = "texture"
    COMPOSITION = "composition"
    RHYTHM = "rhythm"
    TONE = "tone"
    MOOD = "mood"
    ENERGY_LEVEL = "energy_level"
    COMPLEXITY = "complexity"
    CONTRAST = "contrast"
    SYMMETRY = "symmetry"
    MOVEMENT = "movement"
    SCALE = "scale"
    DETAIL_LEVEL = "detail_level"
    CULTURAL_CONTEXT = "cultural_context"
    HISTORICAL_PERIOD = "historical_period"


class TransferMethod(Enum):
    """Methods for transferring style between mediums"""
    DIRECT_MAPPING = "direct_mapping"
    CONCEPTUAL_TRANSLATION = "conceptual_translation"
    PARAMETRIC_ADAPTATION = "parametric_adaptation"
    SEMANTIC_INTERPRETATION = "semantic_interpretation"
    GENERATIVE_SYNTHESIS = "generative_synthesis"
    HYBRID_APPROACH = "hybrid_approach"
    CONTEXTUAL_ADAPTATION = "contextual_adaptation"


class StyleCategory(Enum):
    """Categories of creative styles"""
    CLASSICAL = "classical"
    MODERN = "modern"
    CONTEMPORARY = "contemporary"
    ABSTRACT = "abstract"
    REALISTIC = "realistic"
    MINIMALIST = "minimalist"
    MAXIMALIST = "maximalist"
    VINTAGE = "vintage"
    FUTURISTIC = "futuristic"
    ORGANIC = "organic"
    GEOMETRIC = "geometric"
    EXPRESSIONIST = "expressionist"
    SURREAL = "surreal"


@dataclass
class StyleSignature:
    """Signature characteristics of a creative style"""
    signature_id: str
    name: str
    medium: CreativeMedium
    category: StyleCategory
    attributes: Dict[StyleAttribute, Any]
    dominant_colors: List[str] = field(default_factory=list)
    characteristic_patterns: List[str] = field(default_factory=list)
    mood_descriptors: List[str] = field(default_factory=list)
    technical_aspects: Dict[str, Any] = field(default_factory=dict)
    cultural_markers: List[str] = field(default_factory=list)
    complexity_score: float = 0.5  # 0-1
    uniqueness_score: float = 0.5  # 0-1
    adaptability_score: float = 0.5  # 0-1
    extracted_from: Optional[str] = None  # Source work/artist
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class StyleTransfer:
    """Result of a style transfer operation"""
    transfer_id: str
    source_signature: str  # ID of source style
    target_medium: CreativeMedium
    target_attributes: Dict[StyleAttribute, Any]
    transfer_method: TransferMethod
    adapted_signature: StyleSignature
    confidence_score: float  # 0-1
    fidelity_score: float  # How well style was preserved
    adaptation_notes: List[str] = field(default_factory=list)
    suggested_refinements: List[str] = field(default_factory=list)
    transformation_mapping: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class StyleEvolution:
    """Evolution of a style through multiple transfers"""
    evolution_id: str
    original_signature: str
    evolution_path: List[Tuple[str, CreativeMedium]]  # (signature_id, medium)
    final_signature: str
    evolution_steps: int
    style_drift: float  # How much the style has changed
    innovation_points: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class CrossMediumMapping:
    """Mapping between style elements across different mediums"""
    mapping_id: str
    source_medium: CreativeMedium
    target_medium: CreativeMedium
    attribute_mappings: Dict[StyleAttribute, StyleAttribute]
    equivalence_rules: Dict[str, str]
    adaptation_factors: Dict[str, float]
    quality_preservation: float  # 0-1
    common_use_cases: List[str] = field(default_factory=list)


@dataclass
class StyleAnalysis:
    """Analysis of a creative work's style"""
    analysis_id: str
    work_identifier: str
    medium: CreativeMedium
    detected_styles: List[StyleSignature]
    primary_style: Optional[StyleSignature] = None
    style_confidence: float = 0.0
    mixed_style_indicators: List[str] = field(default_factory=list)
    historical_influences: List[str] = field(default_factory=list)
    innovation_elements: List[str] = field(default_factory=list)
    analysis_metadata: Dict[str, Any] = field(default_factory=dict)
    analyzed_at: datetime = field(default_factory=datetime.now)


class StyleExtractor(ABC):
    """Abstract base class for style extraction from different mediums"""
    
    @abstractmethod
    async def extract_style(self, work_data: Any, medium: CreativeMedium) -> StyleSignature:
        """Extract style signature from a creative work"""
        pass
    
    @abstractmethod
    async def analyze_style_elements(self, work_data: Any) -> Dict[StyleAttribute, Any]:
        """Analyze individual style elements"""
        pass


class StyleTransferEngine(ABC):
    """Abstract base class for style transfer implementations"""
    
    @abstractmethod
    async def transfer_style(self, source_signature: StyleSignature, 
                           target_medium: CreativeMedium,
                           method: TransferMethod) -> StyleTransfer:
        """Transfer a style to a different medium"""
        pass
    
    @abstractmethod
    async def suggest_adaptations(self, signature: StyleSignature, 
                                target_medium: CreativeMedium) -> List[Dict[str, Any]]:
        """Suggest how to adapt style for target medium"""
        pass


class StyleAnalyzer(ABC):
    """Abstract base class for style analysis"""
    
    @abstractmethod
    async def compare_styles(self, signature1: StyleSignature, 
                           signature2: StyleSignature) -> Dict[str, float]:
        """Compare two style signatures"""
        pass
    
    @abstractmethod
    async def find_similar_styles(self, signature: StyleSignature, 
                                style_database: List[StyleSignature]) -> List[Tuple[StyleSignature, float]]:
        """Find similar styles in database"""
        pass


class UniversalStyleExtractor(StyleExtractor):
    """Universal style extractor that works across different mediums"""
    
    def __init__(self):
        self.color_analyzers = {
            CreativeMedium.VISUAL_ART: self._analyze_visual_colors,
            CreativeMedium.PHOTOGRAPHY: self._analyze_photo_colors,
            CreativeMedium.DIGITAL_ART: self._analyze_digital_colors
        }
        
        self.pattern_extractors = {
            CreativeMedium.MUSIC: self._extract_musical_patterns,
            CreativeMedium.WRITING: self._extract_linguistic_patterns,
            CreativeMedium.DESIGN: self._extract_design_patterns
        }
    
    async def extract_style(self, work_data: Any, medium: CreativeMedium) -> StyleSignature:
        """Extract comprehensive style signature from work"""
        try:
            # Extract style elements
            elements = await self.analyze_style_elements(work_data)
            
            # Determine style category
            category = await self._categorize_style(elements, medium)
            
            # Extract patterns and characteristics
            patterns = await self._extract_characteristic_patterns(work_data, medium)
            mood_descriptors = await self._analyze_mood(elements)
            
            # Calculate scores
            complexity_score = await self._calculate_complexity(elements)
            uniqueness_score = await self._calculate_uniqueness(elements)
            adaptability_score = await self._calculate_adaptability(elements, medium)
            
            signature = StyleSignature(
                signature_id=str(uuid4()),
                name=f"{category.value.title()} {medium.value.title()} Style",
                medium=medium,
                category=category,
                attributes=elements,
                dominant_colors=elements.get(StyleAttribute.COLOR_PALETTE, []),
                characteristic_patterns=patterns,
                mood_descriptors=mood_descriptors,
                complexity_score=complexity_score,
                uniqueness_score=uniqueness_score,
                adaptability_score=adaptability_score
            )
            
            return signature
            
        except Exception as e:
            logger.error(f"Error extracting style: {e}")
            # Return default signature
            return StyleSignature(
                signature_id=str(uuid4()),
                name="Default Style",
                medium=medium,
                category=StyleCategory.CONTEMPORARY,
                attributes={}
            )
    
    async def analyze_style_elements(self, work_data: Any) -> Dict[StyleAttribute, Any]:
        """Analyze individual style elements"""
        try:
            elements = {}
            
            # If work_data is image data
            if isinstance(work_data, dict) and 'image' in work_data:
                image_elements = await self._analyze_visual_elements(work_data['image'])
                elements.update(image_elements)
            
            # If work_data is text
            if isinstance(work_data, dict) and 'text' in work_data:
                text_elements = await self._analyze_text_elements(work_data['text'])
                elements.update(text_elements)
            
            # If work_data is audio/music data
            if isinstance(work_data, dict) and 'audio' in work_data:
                audio_elements = await self._analyze_audio_elements(work_data['audio'])
                elements.update(audio_elements)
            
            # If work_data is design specification
            if isinstance(work_data, dict) and 'design' in work_data:
                design_elements = await self._analyze_design_elements(work_data['design'])
                elements.update(design_elements)
            
            return elements
            
        except Exception as e:
            logger.error(f"Error analyzing style elements: {e}")
            return {}
    
    async def _analyze_visual_elements(self, image_data: Any) -> Dict[StyleAttribute, Any]:
        """Analyze visual style elements"""
        elements = {}
        
        try:
            # Simulate image analysis
            elements[StyleAttribute.COLOR_PALETTE] = [
                "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7"
            ]
            elements[StyleAttribute.CONTRAST] = random.uniform(0.3, 0.9)
            elements[StyleAttribute.COMPLEXITY] = random.uniform(0.2, 0.8)
            elements[StyleAttribute.TEXTURE] = random.choice(["smooth", "rough", "organic", "geometric"])
            elements[StyleAttribute.COMPOSITION] = random.choice(["balanced", "asymmetric", "centered", "dynamic"])
            elements[StyleAttribute.MOVEMENT] = random.uniform(0.0, 1.0)
            
        except Exception as e:
            logger.error(f"Error analyzing visual elements: {e}")
        
        return elements
    
    async def _analyze_text_elements(self, text_data: str) -> Dict[StyleAttribute, Any]:
        """Analyze text style elements"""
        elements = {}
        
        try:
            # Simple text analysis
            word_count = len(text_data.split())
            sentence_count = text_data.count('.') + text_data.count('!') + text_data.count('?')
            avg_word_length = sum(len(word) for word in text_data.split()) / word_count if word_count > 0 else 0
            
            elements[StyleAttribute.COMPLEXITY] = min(avg_word_length / 10, 1.0)  # Normalize to 0-1
            elements[StyleAttribute.RHYTHM] = random.uniform(0.3, 0.9)  # Based on sentence structure
            elements[StyleAttribute.TONE] = random.choice(["formal", "casual", "poetic", "technical", "conversational"])
            elements[StyleAttribute.ENERGY_LEVEL] = random.uniform(0.2, 0.9)
            elements[StyleAttribute.MOOD] = random.choice(["optimistic", "melancholic", "neutral", "dramatic", "peaceful"])
            
        except Exception as e:
            logger.error(f"Error analyzing text elements: {e}")
        
        return elements
    
    async def _analyze_audio_elements(self, audio_data: Any) -> Dict[StyleAttribute, Any]:
        """Analyze audio/music style elements"""
        elements = {}
        
        try:
            # Simulate audio analysis
            elements[StyleAttribute.RHYTHM] = random.uniform(0.4, 0.9)
            elements[StyleAttribute.ENERGY_LEVEL] = random.uniform(0.2, 1.0)
            elements[StyleAttribute.COMPLEXITY] = random.uniform(0.3, 0.8)
            elements[StyleAttribute.MOOD] = random.choice(["upbeat", "melancholic", "energetic", "calm", "dramatic"])
            elements[StyleAttribute.TONE] = random.choice(["major", "minor", "modal", "chromatic", "atonal"])
            elements[StyleAttribute.SCALE] = random.choice(["intimate", "grandiose", "moderate"])
            
        except Exception as e:
            logger.error(f"Error analyzing audio elements: {e}")
        
        return elements
    
    async def _analyze_design_elements(self, design_data: Dict[str, Any]) -> Dict[StyleAttribute, Any]:
        """Analyze design style elements"""
        elements = {}
        
        try:
            # Analyze design specifications
            elements[StyleAttribute.COLOR_PALETTE] = design_data.get('colors', ["#000000", "#FFFFFF"])
            elements[StyleAttribute.SYMMETRY] = random.uniform(0.0, 1.0)
            elements[StyleAttribute.COMPLEXITY] = random.uniform(0.2, 0.8)
            elements[StyleAttribute.SCALE] = design_data.get('scale', "medium")
            elements[StyleAttribute.COMPOSITION] = design_data.get('layout', "balanced")
            elements[StyleAttribute.DETAIL_LEVEL] = random.uniform(0.3, 0.9)
            
        except Exception as e:
            logger.error(f"Error analyzing design elements: {e}")
        
        return elements
    
    async def _categorize_style(self, elements: Dict[StyleAttribute, Any], medium: CreativeMedium) -> StyleCategory:
        """Categorize style based on elements"""
        try:
            # Simple categorization based on complexity and other factors
            complexity = elements.get(StyleAttribute.COMPLEXITY, 0.5)
            
            if complexity < 0.3:
                return StyleCategory.MINIMALIST
            elif complexity > 0.7:
                return StyleCategory.MAXIMALIST
            else:
                # Random selection from common categories
                categories = [StyleCategory.MODERN, StyleCategory.CONTEMPORARY, 
                            StyleCategory.CLASSICAL, StyleCategory.ABSTRACT]
                return random.choice(categories)
                
        except Exception as e:
            logger.error(f"Error categorizing style: {e}")
            return StyleCategory.CONTEMPORARY
    
    async def _extract_characteristic_patterns(self, work_data: Any, medium: CreativeMedium) -> List[str]:
        """Extract characteristic patterns from the work"""
        patterns = []
        
        try:
            if medium in [CreativeMedium.VISUAL_ART, CreativeMedium.DIGITAL_ART]:
                patterns.extend(["curved_lines", "geometric_shapes", "organic_forms", "repetitive_elements"])
            elif medium == CreativeMedium.MUSIC:
                patterns.extend(["melodic_progression", "rhythmic_pattern", "harmonic_structure"])
            elif medium == CreativeMedium.WRITING:
                patterns.extend(["narrative_structure", "literary_devices", "stylistic_choices"])
            elif medium == CreativeMedium.DESIGN:
                patterns.extend(["grid_system", "typography_hierarchy", "spacing_patterns"])
            
            # Return random subset
            return random.sample(patterns, min(len(patterns), 3))
            
        except Exception as e:
            logger.error(f"Error extracting patterns: {e}")
            return []
    
    async def _analyze_mood(self, elements: Dict[StyleAttribute, Any]) -> List[str]:
        """Analyze mood descriptors from style elements"""
        mood_descriptors = []
        
        try:
            # Extract mood from various elements
            if StyleAttribute.MOOD in elements:
                mood_descriptors.append(elements[StyleAttribute.MOOD])
            
            if StyleAttribute.ENERGY_LEVEL in elements:
                energy = elements[StyleAttribute.ENERGY_LEVEL]
                if energy > 0.7:
                    mood_descriptors.append("energetic")
                elif energy < 0.3:
                    mood_descriptors.append("calm")
                else:
                    mood_descriptors.append("balanced")
            
            if StyleAttribute.TONE in elements:
                mood_descriptors.append(elements[StyleAttribute.TONE])
            
            # Add some general mood descriptors
            general_moods = ["serene", "dynamic", "contemplative", "vibrant", "subdued"]
            mood_descriptors.extend(random.sample(general_moods, 2))
            
            return list(set(mood_descriptors))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Error analyzing mood: {e}")
            return ["neutral"]
    
    async def _calculate_complexity(self, elements: Dict[StyleAttribute, Any]) -> float:
        """Calculate overall complexity score"""
        try:
            complexity_indicators = []
            
            if StyleAttribute.COMPLEXITY in elements:
                complexity_indicators.append(elements[StyleAttribute.COMPLEXITY])
            
            if StyleAttribute.DETAIL_LEVEL in elements:
                complexity_indicators.append(elements[StyleAttribute.DETAIL_LEVEL])
            
            if StyleAttribute.COLOR_PALETTE in elements:
                color_count = len(elements[StyleAttribute.COLOR_PALETTE])
                complexity_indicators.append(min(color_count / 10, 1.0))  # Normalize
            
            return sum(complexity_indicators) / len(complexity_indicators) if complexity_indicators else 0.5
            
        except Exception as e:
            logger.error(f"Error calculating complexity: {e}")
            return 0.5
    
    async def _calculate_uniqueness(self, elements: Dict[StyleAttribute, Any]) -> float:
        """Calculate uniqueness score"""
        try:
            # Simplified uniqueness calculation
            uniqueness_score = 0.5  # Base score
            
            # Unusual combinations increase uniqueness
            if len(elements) > 5:
                uniqueness_score += 0.2
            
            # Extreme values in certain attributes
            for attr, value in elements.items():
                if isinstance(value, (int, float)):
                    if value < 0.2 or value > 0.8:  # Extreme values
                        uniqueness_score += 0.1
            
            return min(uniqueness_score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating uniqueness: {e}")
            return 0.5
    
    async def _calculate_adaptability(self, elements: Dict[StyleAttribute, Any], medium: CreativeMedium) -> float:
        """Calculate how adaptable the style is to other mediums"""
        try:
            adaptability_score = 0.5  # Base score
            
            # Certain mediums are more adaptable
            adaptable_mediums = [CreativeMedium.DESIGN, CreativeMedium.DIGITAL_ART, CreativeMedium.VISUAL_ART]
            if medium in adaptable_mediums:
                adaptability_score += 0.2
            
            # Simple elements are more adaptable
            complexity = elements.get(StyleAttribute.COMPLEXITY, 0.5)
            adaptability_score += (1 - complexity) * 0.3
            
            return min(adaptability_score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating adaptability: {e}")
            return 0.5
    
    # Color analysis methods for different mediums
    async def _analyze_visual_colors(self, image_data: Any) -> List[str]:
        """Extract dominant colors from visual art"""
        # Simplified color extraction
        return ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7"]
    
    async def _analyze_photo_colors(self, photo_data: Any) -> List[str]:
        """Extract colors from photography"""
        return ["#2C3E50", "#E74C3C", "#3498DB", "#2ECC71", "#F39C12"]
    
    async def _analyze_digital_colors(self, digital_data: Any) -> List[str]:
        """Extract colors from digital art"""
        return ["#9B59B6", "#1ABC9C", "#E67E22", "#34495E", "#F1C40F"]
    
    # Pattern extraction methods
    async def _extract_musical_patterns(self, audio_data: Any) -> List[str]:
        """Extract musical patterns"""
        return ["verse-chorus-bridge", "ascending-melody", "syncopated-rhythm"]
    
    async def _extract_linguistic_patterns(self, text_data: str) -> List[str]:
        """Extract writing patterns"""
        return ["metaphorical-language", "parallel-structure", "dialogue-heavy"]
    
    async def _extract_design_patterns(self, design_data: Dict[str, Any]) -> List[str]:
        """Extract design patterns"""
        return ["grid-based-layout", "asymmetrical-balance", "minimal-typography"]


class IntelligentStyleTransferEngine(StyleTransferEngine):
    """Intelligent style transfer engine with multiple transfer strategies"""
    
    def __init__(self):
        self.transfer_strategies = {
            TransferMethod.DIRECT_MAPPING: self._direct_mapping_transfer,
            TransferMethod.CONCEPTUAL_TRANSLATION: self._conceptual_translation,
            TransferMethod.PARAMETRIC_ADAPTATION: self._parametric_adaptation,
            TransferMethod.SEMANTIC_INTERPRETATION: self._semantic_interpretation,
            TransferMethod.GENERATIVE_SYNTHESIS: self._generative_synthesis,
            TransferMethod.HYBRID_APPROACH: self._hybrid_approach
        }
        
        # Medium compatibility matrix
        self.medium_compatibility = {
            (CreativeMedium.VISUAL_ART, CreativeMedium.DIGITAL_ART): 0.9,
            (CreativeMedium.PHOTOGRAPHY, CreativeMedium.VISUAL_ART): 0.8,
            (CreativeMedium.MUSIC, CreativeMedium.VISUAL_ART): 0.6,  # Synesthesia-like transfers
            (CreativeMedium.WRITING, CreativeMedium.DESIGN): 0.7,
            (CreativeMedium.DESIGN, CreativeMedium.ARCHITECTURE): 0.8,
            (CreativeMedium.FASHION, CreativeMedium.DESIGN): 0.8
        }
        
        # Attribute translation rules
        self.attribute_translations = {
            (StyleAttribute.COLOR_PALETTE, CreativeMedium.MUSIC): "harmonic_palette",
            (StyleAttribute.RHYTHM, CreativeMedium.VISUAL_ART): "visual_flow",
            (StyleAttribute.TEXTURE, CreativeMedium.WRITING): "prose_texture",
            (StyleAttribute.COMPOSITION, CreativeMedium.MUSIC): "arrangement_structure"
        }
    
    async def transfer_style(self, source_signature: StyleSignature, 
                           target_medium: CreativeMedium,
                           method: TransferMethod) -> StyleTransfer:
        """Transfer style to target medium using specified method"""
        try:
            # Check if we have a strategy for this method
            strategy = self.transfer_strategies.get(method)
            if not strategy:
                raise ValueError(f"Unknown transfer method: {method}")
            
            # Execute transfer strategy
            adapted_signature, confidence, fidelity, notes = await strategy(source_signature, target_medium)
            
            # Calculate transformation mapping
            transformation_mapping = await self._create_transformation_mapping(
                source_signature, adapted_signature, target_medium
            )
            
            # Generate refinement suggestions
            refinements = await self._suggest_refinements(adapted_signature, target_medium)
            
            transfer = StyleTransfer(
                transfer_id=str(uuid4()),
                source_signature=source_signature.signature_id,
                target_medium=target_medium,
                target_attributes=adapted_signature.attributes,
                transfer_method=method,
                adapted_signature=adapted_signature,
                confidence_score=confidence,
                fidelity_score=fidelity,
                adaptation_notes=notes,
                suggested_refinements=refinements,
                transformation_mapping=transformation_mapping
            )
            
            return transfer
            
        except Exception as e:
            logger.error(f"Error transferring style: {e}")
            # Return fallback transfer
            return StyleTransfer(
                transfer_id=str(uuid4()),
                source_signature=source_signature.signature_id,
                target_medium=target_medium,
                target_attributes={},
                transfer_method=method,
                adapted_signature=source_signature,  # Fallback to source
                confidence_score=0.1,
                fidelity_score=0.1
            )
    
    async def suggest_adaptations(self, signature: StyleSignature, 
                                target_medium: CreativeMedium) -> List[Dict[str, Any]]:
        """Suggest how to adapt style for target medium"""
        try:
            adaptations = []
            
            # Get medium compatibility
            compatibility_key = (signature.medium, target_medium)
            reverse_compatibility_key = (target_medium, signature.medium)
            
            compatibility = (
                self.medium_compatibility.get(compatibility_key) or
                self.medium_compatibility.get(reverse_compatibility_key) or
                0.5  # Default compatibility
            )
            
            # Suggest attribute adaptations
            for attr, value in signature.attributes.items():
                adaptation = await self._suggest_attribute_adaptation(attr, value, target_medium)
                if adaptation:
                    adaptations.append({
                        "attribute": attr.value,
                        "adaptation": adaptation,
                        "confidence": compatibility * 0.8 + random.uniform(0.1, 0.2)
                    })
            
            # Suggest new attributes for target medium
            new_attributes = await self._suggest_new_attributes(signature, target_medium)
            adaptations.extend(new_attributes)
            
            return adaptations
            
        except Exception as e:
            logger.error(f"Error suggesting adaptations: {e}")
            return []
    
    async def _direct_mapping_transfer(self, source: StyleSignature, 
                                     target_medium: CreativeMedium) -> Tuple[StyleSignature, float, float, List[str]]:
        """Direct mapping transfer strategy"""
        try:
            adapted_attributes = {}
            notes = ["Applied direct mapping strategy"]
            
            # Map attributes directly where possible
            for attr, value in source.attributes.items():
                if attr in [StyleAttribute.COLOR_PALETTE, StyleAttribute.MOOD, StyleAttribute.COMPLEXITY]:
                    adapted_attributes[attr] = value
                    notes.append(f"Directly mapped {attr.value}")
            
            # Create adapted signature
            adapted_signature = StyleSignature(
                signature_id=str(uuid4()),
                name=f"{source.name} -> {target_medium.value}",
                medium=target_medium,
                category=source.category,
                attributes=adapted_attributes,
                dominant_colors=source.dominant_colors,
                mood_descriptors=source.mood_descriptors
            )
            
            confidence = 0.8
            fidelity = 0.7
            
            return adapted_signature, confidence, fidelity, notes
            
        except Exception as e:
            logger.error(f"Error in direct mapping: {e}")
            return source, 0.1, 0.1, ["Direct mapping failed"]
    
    async def _conceptual_translation(self, source: StyleSignature, 
                                    target_medium: CreativeMedium) -> Tuple[StyleSignature, float, float, List[str]]:
        """Conceptual translation strategy"""
        try:
            adapted_attributes = {}
            notes = ["Applied conceptual translation strategy"]
            
            # Translate concepts rather than direct attributes
            for attr, value in source.attributes.items():
                translated = await self._translate_concept(attr, value, target_medium)
                if translated:
                    adapted_attributes.update(translated)
                    notes.append(f"Conceptually translated {attr.value}")
            
            # Add medium-specific interpretations
            if target_medium == CreativeMedium.MUSIC and StyleAttribute.COLOR_PALETTE in source.attributes:
                # Translate colors to musical elements
                adapted_attributes[StyleAttribute.TONE] = "harmonic_richness"
                notes.append("Translated color palette to harmonic richness")
            
            adapted_signature = StyleSignature(
                signature_id=str(uuid4()),
                name=f"Conceptual: {source.name} -> {target_medium.value}",
                medium=target_medium,
                category=source.category,
                attributes=adapted_attributes,
                mood_descriptors=source.mood_descriptors
            )
            
            confidence = 0.7
            fidelity = 0.6  # Lower fidelity due to conceptual nature
            
            return adapted_signature, confidence, fidelity, notes
            
        except Exception as e:
            logger.error(f"Error in conceptual translation: {e}")
            return source, 0.1, 0.1, ["Conceptual translation failed"]
    
    async def _parametric_adaptation(self, source: StyleSignature, 
                                   target_medium: CreativeMedium) -> Tuple[StyleSignature, float, float, List[str]]:
        """Parametric adaptation strategy"""
        try:
            adapted_attributes = {}
            notes = ["Applied parametric adaptation strategy"]
            
            # Adapt parameters based on medium constraints
            for attr, value in source.attributes.items():
                if isinstance(value, (int, float)):
                    # Apply medium-specific scaling
                    adapted_value = await self._scale_parameter(value, attr, target_medium)
                    adapted_attributes[attr] = adapted_value
                    notes.append(f"Scaled {attr.value} from {value} to {adapted_value}")
                else:
                    adapted_attributes[attr] = value
            
            adapted_signature = StyleSignature(
                signature_id=str(uuid4()),
                name=f"Parametric: {source.name} -> {target_medium.value}",
                medium=target_medium,
                category=source.category,
                attributes=adapted_attributes,
                dominant_colors=source.dominant_colors
            )
            
            confidence = 0.75
            fidelity = 0.8  # High fidelity for parameter preservation
            
            return adapted_signature, confidence, fidelity, notes
            
        except Exception as e:
            logger.error(f"Error in parametric adaptation: {e}")
            return source, 0.1, 0.1, ["Parametric adaptation failed"]
    
    async def _semantic_interpretation(self, source: StyleSignature, 
                                     target_medium: CreativeMedium) -> Tuple[StyleSignature, float, float, List[str]]:
        """Semantic interpretation strategy"""
        try:
            adapted_attributes = {}
            notes = ["Applied semantic interpretation strategy"]
            
            # Interpret semantic meaning and adapt to target medium
            semantic_themes = await self._extract_semantic_themes(source)
            
            for theme in semantic_themes:
                medium_expression = await self._express_theme_in_medium(theme, target_medium)
                if medium_expression:
                    adapted_attributes.update(medium_expression)
                    notes.append(f"Expressed theme '{theme}' in {target_medium.value}")
            
            adapted_signature = StyleSignature(
                signature_id=str(uuid4()),
                name=f"Semantic: {source.name} -> {target_medium.value}",
                medium=target_medium,
                category=source.category,
                attributes=adapted_attributes,
                mood_descriptors=source.mood_descriptors
            )
            
            confidence = 0.65
            fidelity = 0.5  # Lower fidelity due to interpretation
            
            return adapted_signature, confidence, fidelity, notes
            
        except Exception as e:
            logger.error(f"Error in semantic interpretation: {e}")
            return source, 0.1, 0.1, ["Semantic interpretation failed"]
    
    async def _generative_synthesis(self, source: StyleSignature, 
                                  target_medium: CreativeMedium) -> Tuple[StyleSignature, float, float, List[str]]:
        """Generative synthesis strategy"""
        try:
            adapted_attributes = {}
            notes = ["Applied generative synthesis strategy"]
            
            # Generate new attributes inspired by source
            inspiration_elements = list(source.attributes.keys())
            
            for element in inspiration_elements:
                generated = await self._generate_inspired_attribute(element, source, target_medium)
                if generated:
                    adapted_attributes.update(generated)
                    notes.append(f"Generated new attribute inspired by {element.value}")
            
            # Add some novel elements
            novel_attributes = await self._generate_novel_attributes(target_medium)
            adapted_attributes.update(novel_attributes)
            notes.append("Added novel generative elements")
            
            adapted_signature = StyleSignature(
                signature_id=str(uuid4()),
                name=f"Generative: {source.name} -> {target_medium.value}",
                medium=target_medium,
                category=source.category,
                attributes=adapted_attributes,
                uniqueness_score=min(source.uniqueness_score + 0.2, 1.0)  # Increase uniqueness
            )
            
            confidence = 0.6
            fidelity = 0.4  # Lower fidelity due to generative nature
            
            return adapted_signature, confidence, fidelity, notes
            
        except Exception as e:
            logger.error(f"Error in generative synthesis: {e}")
            return source, 0.1, 0.1, ["Generative synthesis failed"]
    
    async def _hybrid_approach(self, source: StyleSignature, 
                             target_medium: CreativeMedium) -> Tuple[StyleSignature, float, float, List[str]]:
        """Hybrid approach combining multiple strategies"""
        try:
            adapted_attributes = {}
            notes = ["Applied hybrid approach"]
            
            # Use direct mapping for compatible attributes
            direct_mapped = 0
            for attr, value in source.attributes.items():
                if attr in [StyleAttribute.COLOR_PALETTE, StyleAttribute.MOOD]:
                    adapted_attributes[attr] = value
                    direct_mapped += 1
            
            notes.append(f"Direct mapped {direct_mapped} attributes")
            
            # Use conceptual translation for complex attributes
            conceptual_count = 0
            for attr, value in source.attributes.items():
                if attr not in adapted_attributes:
                    translated = await self._translate_concept(attr, value, target_medium)
                    if translated:
                        adapted_attributes.update(translated)
                        conceptual_count += 1
            
            notes.append(f"Conceptually translated {conceptual_count} attributes")
            
            # Add some generative elements
            novel_attributes = await self._generate_novel_attributes(target_medium)
            adapted_attributes.update(novel_attributes)
            notes.append("Added generative elements")
            
            adapted_signature = StyleSignature(
                signature_id=str(uuid4()),
                name=f"Hybrid: {source.name} -> {target_medium.value}",
                medium=target_medium,
                category=source.category,
                attributes=adapted_attributes,
                dominant_colors=source.dominant_colors,
                mood_descriptors=source.mood_descriptors
            )
            
            confidence = 0.8
            fidelity = 0.7
            
            return adapted_signature, confidence, fidelity, notes
            
        except Exception as e:
            logger.error(f"Error in hybrid approach: {e}")
            return source, 0.1, 0.1, ["Hybrid approach failed"]
    
    # Helper methods for style transfer strategies
    
    async def _translate_concept(self, attr: StyleAttribute, value: Any, 
                               target_medium: CreativeMedium) -> Optional[Dict[StyleAttribute, Any]]:
        """Translate a concept to target medium"""
        try:
            translation_key = (attr, target_medium)
            
            if translation_key in self.attribute_translations:
                translated_name = self.attribute_translations[translation_key]
                return {attr: translated_name}
            
            # Default conceptual translations
            if attr == StyleAttribute.RHYTHM and target_medium == CreativeMedium.VISUAL_ART:
                return {StyleAttribute.MOVEMENT: value}
            elif attr == StyleAttribute.COLOR_PALETTE and target_medium == CreativeMedium.MUSIC:
                return {StyleAttribute.TONE: "harmonic"}
            elif attr == StyleAttribute.TEXTURE and target_medium == CreativeMedium.WRITING:
                return {StyleAttribute.TONE: "textural"}
            
            return None
            
        except Exception as e:
            logger.error(f"Error translating concept: {e}")
            return None
    
    async def _scale_parameter(self, value: Union[int, float], 
                             attr: StyleAttribute, target_medium: CreativeMedium) -> Union[int, float]:
        """Scale parameter for target medium"""
        try:
            # Medium-specific scaling factors
            scaling_factors = {
                (StyleAttribute.COMPLEXITY, CreativeMedium.MUSIC): 0.8,
                (StyleAttribute.ENERGY_LEVEL, CreativeMedium.VISUAL_ART): 1.2,
                (StyleAttribute.CONTRAST, CreativeMedium.WRITING): 0.9
            }
            
            scaling_key = (attr, target_medium)
            if scaling_key in scaling_factors:
                return value * scaling_factors[scaling_key]
            
            # Default: slight random variation
            return value * random.uniform(0.9, 1.1)
            
        except Exception as e:
            logger.error(f"Error scaling parameter: {e}")
            return value
    
    async def _extract_semantic_themes(self, signature: StyleSignature) -> List[str]:
        """Extract semantic themes from style signature"""
        themes = []
        
        try:
            # Extract themes from mood descriptors
            themes.extend(signature.mood_descriptors)
            
            # Extract themes from category
            themes.append(signature.category.value)
            
            # Extract themes from patterns
            themes.extend(signature.characteristic_patterns)
            
            return list(set(themes))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Error extracting semantic themes: {e}")
            return ["neutral"]
    
    async def _express_theme_in_medium(self, theme: str, medium: CreativeMedium) -> Optional[Dict[StyleAttribute, Any]]:
        """Express a semantic theme in target medium"""
        try:
            expressions = {
                ("energetic", CreativeMedium.VISUAL_ART): {StyleAttribute.MOVEMENT: 0.9, StyleAttribute.CONTRAST: 0.8},
                ("calm", CreativeMedium.MUSIC): {StyleAttribute.RHYTHM: 0.3, StyleAttribute.ENERGY_LEVEL: 0.2},
                ("dramatic", CreativeMedium.WRITING): {StyleAttribute.TONE: "intense", StyleAttribute.COMPLEXITY: 0.8}
            }
            
            expression_key = (theme, medium)
            return expressions.get(expression_key)
            
        except Exception as e:
            logger.error(f"Error expressing theme: {e}")
            return None
    
    async def _generate_inspired_attribute(self, inspiration: StyleAttribute, 
                                         source: StyleSignature, target_medium: CreativeMedium) -> Optional[Dict[StyleAttribute, Any]]:
        """Generate new attribute inspired by source element"""
        try:
            # Generate variations or related attributes
            if inspiration == StyleAttribute.COLOR_PALETTE:
                return {StyleAttribute.MOOD: random.choice(["vibrant", "muted", "harmonious"])}
            elif inspiration == StyleAttribute.COMPLEXITY:
                complexity_val = source.attributes.get(inspiration, 0.5)
                return {StyleAttribute.DETAIL_LEVEL: complexity_val * 0.8}
            elif inspiration == StyleAttribute.RHYTHM:
                return {StyleAttribute.MOVEMENT: random.uniform(0.3, 0.8)}
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating inspired attribute: {e}")
            return None
    
    async def _generate_novel_attributes(self, medium: CreativeMedium) -> Dict[StyleAttribute, Any]:
        """Generate novel attributes for target medium"""
        try:
            novel = {}
            
            if medium == CreativeMedium.VISUAL_ART:
                novel[StyleAttribute.TEXTURE] = random.choice(["painterly", "smooth", "textured"])
            elif medium == CreativeMedium.MUSIC:
                novel[StyleAttribute.SCALE] = random.choice(["intimate", "epic", "moderate"])
            elif medium == CreativeMedium.WRITING:
                novel[StyleAttribute.TONE] = random.choice(["lyrical", "prose", "technical"])
            
            return novel
            
        except Exception as e:
            logger.error(f"Error generating novel attributes: {e}")
            return {}
    
    async def _create_transformation_mapping(self, source: StyleSignature, 
                                           adapted: StyleSignature, target_medium: CreativeMedium) -> Dict[str, str]:
        """Create mapping of transformations applied"""
        mapping = {}
        
        try:
            for attr in source.attributes:
                if attr in adapted.attributes:
                    source_val = str(source.attributes[attr])
                    adapted_val = str(adapted.attributes[attr])
                    mapping[f"{attr.value}_transformation"] = f"{source_val} -> {adapted_val}"
                else:
                    mapping[f"{attr.value}_transformation"] = "removed"
            
            # Note new attributes
            for attr in adapted.attributes:
                if attr not in source.attributes:
                    mapping[f"{attr.value}_transformation"] = f"new -> {adapted.attributes[attr]}"
            
            return mapping
            
        except Exception as e:
            logger.error(f"Error creating transformation mapping: {e}")
            return {}
    
    async def _suggest_refinements(self, signature: StyleSignature, 
                                 target_medium: CreativeMedium) -> List[str]:
        """Suggest refinements for the adapted style"""
        refinements = []
        
        try:
            # Medium-specific refinement suggestions
            if target_medium == CreativeMedium.VISUAL_ART:
                refinements.extend([
                    "Consider adjusting brush stroke technique",
                    "Experiment with color temperature balance",
                    "Refine composition focal points"
                ])
            elif target_medium == CreativeMedium.MUSIC:
                refinements.extend([
                    "Fine-tune harmonic progressions",
                    "Adjust tempo to match energy level",
                    "Consider instrumental arrangement"
                ])
            elif target_medium == CreativeMedium.WRITING:
                refinements.extend([
                    "Refine narrative voice consistency",
                    "Adjust sentence rhythm and flow",
                    "Consider vocabulary level appropriateness"
                ])
            
            # General refinements
            refinements.extend([
                "Test with target audience",
                "Iterate based on medium constraints",
                "Consider cultural context adaptation"
            ])
            
            return refinements
            
        except Exception as e:
            logger.error(f"Error suggesting refinements: {e}")
            return ["Review and iterate as needed"]
    
    async def _suggest_attribute_adaptation(self, attr: StyleAttribute, value: Any, 
                                          target_medium: CreativeMedium) -> Optional[str]:
        """Suggest how to adapt a specific attribute"""
        try:
            suggestions = {
                (StyleAttribute.COLOR_PALETTE, CreativeMedium.MUSIC): "Map colors to harmonic relationships",
                (StyleAttribute.RHYTHM, CreativeMedium.VISUAL_ART): "Translate to visual flow and movement",
                (StyleAttribute.TEXTURE, CreativeMedium.WRITING): "Express through prose texture and word choice",
                (StyleAttribute.COMPOSITION, CreativeMedium.DESIGN): "Apply as layout and hierarchy principles"
            }
            
            suggestion_key = (attr, target_medium)
            return suggestions.get(suggestion_key)
            
        except Exception as e:
            logger.error(f"Error suggesting attribute adaptation: {e}")
            return None
    
    async def _suggest_new_attributes(self, signature: StyleSignature, 
                                    target_medium: CreativeMedium) -> List[Dict[str, Any]]:
        """Suggest new attributes specific to target medium"""
        suggestions = []
        
        try:
            medium_specific_attrs = {
                CreativeMedium.VISUAL_ART: [StyleAttribute.TEXTURE, StyleAttribute.COMPOSITION],
                CreativeMedium.MUSIC: [StyleAttribute.RHYTHM, StyleAttribute.SCALE],
                CreativeMedium.WRITING: [StyleAttribute.TONE, StyleAttribute.COMPLEXITY],
                CreativeMedium.DESIGN: [StyleAttribute.SYMMETRY, StyleAttribute.DETAIL_LEVEL]
            }
            
            if target_medium in medium_specific_attrs:
                for attr in medium_specific_attrs[target_medium]:
                    if attr not in signature.attributes:
                        suggestions.append({
                            "attribute": attr.value,
                            "adaptation": f"Add medium-specific {attr.value}",
                            "confidence": 0.7
                        })
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error suggesting new attributes: {e}")
            return []


class ComprehensiveStyleAnalyzer(StyleAnalyzer):
    """Comprehensive style analysis and comparison"""
    
    def __init__(self):
        self.similarity_weights = {
            StyleAttribute.COLOR_PALETTE: 0.2,
            StyleAttribute.MOOD: 0.15,
            StyleAttribute.COMPLEXITY: 0.15,
            StyleAttribute.TONE: 0.15,
            StyleAttribute.ENERGY_LEVEL: 0.1,
            StyleAttribute.COMPOSITION: 0.1,
            StyleAttribute.TEXTURE: 0.05,
            StyleAttribute.RHYTHM: 0.1
        }
    
    async def compare_styles(self, signature1: StyleSignature, 
                           signature2: StyleSignature) -> Dict[str, float]:
        """Compare two style signatures"""
        try:
            comparison = {}
            
            # Overall similarity
            comparison["overall_similarity"] = await self._calculate_overall_similarity(signature1, signature2)
            
            # Attribute-by-attribute comparison
            for attr in StyleAttribute:
                similarity = await self._compare_attribute(signature1, signature2, attr)
                comparison[f"{attr.value}_similarity"] = similarity
            
            # Medium compatibility
            comparison["medium_compatibility"] = await self._calculate_medium_compatibility(signature1, signature2)
            
            # Category compatibility
            comparison["category_compatibility"] = 1.0 if signature1.category == signature2.category else 0.0
            
            # Mood compatibility
            comparison["mood_compatibility"] = await self._calculate_mood_compatibility(signature1, signature2)
            
            # Complexity difference
            comparison["complexity_difference"] = abs(signature1.complexity_score - signature2.complexity_score)
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error comparing styles: {e}")
            return {"overall_similarity": 0.0}
    
    async def find_similar_styles(self, signature: StyleSignature, 
                                style_database: List[StyleSignature]) -> List[Tuple[StyleSignature, float]]:
        """Find similar styles in database"""
        try:
            similarities = []
            
            for other_signature in style_database:
                if other_signature.signature_id != signature.signature_id:
                    comparison = await self.compare_styles(signature, other_signature)
                    similarity_score = comparison.get("overall_similarity", 0.0)
                    
                    similarities.append((other_signature, similarity_score))
            
            # Sort by similarity (descending)
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            return similarities[:10]  # Return top 10 most similar
            
        except Exception as e:
            logger.error(f"Error finding similar styles: {e}")
            return []
    
    async def _calculate_overall_similarity(self, sig1: StyleSignature, sig2: StyleSignature) -> float:
        """Calculate overall similarity between two signatures"""
        try:
            total_similarity = 0.0
            total_weight = 0.0
            
            # Compare each attribute with weights
            for attr, weight in self.similarity_weights.items():
                attr_similarity = await self._compare_attribute(sig1, sig2, attr)
                total_similarity += attr_similarity * weight
                total_weight += weight
            
            # Normalize by total weight
            if total_weight > 0:
                return total_similarity / total_weight
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"Error calculating overall similarity: {e}")
            return 0.0
    
    async def _compare_attribute(self, sig1: StyleSignature, sig2: StyleSignature, 
                               attr: StyleAttribute) -> float:
        """Compare specific attribute between signatures"""
        try:
            val1 = sig1.attributes.get(attr)
            val2 = sig2.attributes.get(attr)
            
            # If both are None
            if val1 is None and val2 is None:
                return 1.0
            
            # If one is None
            if val1 is None or val2 is None:
                return 0.0
            
            # Compare based on type
            if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                # Numerical comparison
                max_diff = 1.0  # Assume normalized 0-1 range
                diff = abs(val1 - val2)
                return 1.0 - (diff / max_diff)
            
            elif isinstance(val1, str) and isinstance(val2, str):
                # String comparison
                return 1.0 if val1 == val2 else 0.0
            
            elif isinstance(val1, list) and isinstance(val2, list):
                # List comparison (e.g., color palettes)
                return await self._compare_lists(val1, val2)
            
            else:
                # Default comparison
                return 1.0 if val1 == val2 else 0.0
                
        except Exception as e:
            logger.error(f"Error comparing attribute {attr}: {e}")
            return 0.0
    
    async def _compare_lists(self, list1: List[Any], list2: List[Any]) -> float:
        """Compare two lists (e.g., color palettes, patterns)"""
        try:
            if not list1 and not list2:
                return 1.0
            
            if not list1 or not list2:
                return 0.0
            
            # Calculate intersection over union (Jaccard similarity)
            set1 = set(list1)
            set2 = set(list2)
            
            intersection = len(set1.intersection(set2))
            union = len(set1.union(set2))
            
            return intersection / union if union > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error comparing lists: {e}")
            return 0.0
    
    async def _calculate_medium_compatibility(self, sig1: StyleSignature, sig2: StyleSignature) -> float:
        """Calculate compatibility between mediums"""
        try:
            if sig1.medium == sig2.medium:
                return 1.0
            
            # Use predefined compatibility matrix
            compatible_pairs = {
                (CreativeMedium.VISUAL_ART, CreativeMedium.DIGITAL_ART): 0.9,
                (CreativeMedium.DESIGN, CreativeMedium.VISUAL_ART): 0.8,
                (CreativeMedium.PHOTOGRAPHY, CreativeMedium.VISUAL_ART): 0.7,
                (CreativeMedium.WRITING, CreativeMedium.DESIGN): 0.6,
                (CreativeMedium.MUSIC, CreativeMedium.VISUAL_ART): 0.5  # Synesthetic connections
            }
            
            # Check both directions
            pair1 = (sig1.medium, sig2.medium)
            pair2 = (sig2.medium, sig1.medium)
            
            return compatible_pairs.get(pair1) or compatible_pairs.get(pair2) or 0.3
            
        except Exception as e:
            logger.error(f"Error calculating medium compatibility: {e}")
            return 0.3
    
    async def _calculate_mood_compatibility(self, sig1: StyleSignature, sig2: StyleSignature) -> float:
        """Calculate compatibility between mood descriptors"""
        try:
            moods1 = set(sig1.mood_descriptors)
            moods2 = set(sig2.mood_descriptors)
            
            if not moods1 and not moods2:
                return 1.0
            
            if not moods1 or not moods2:
                return 0.0
            
            # Calculate overlap
            intersection = len(moods1.intersection(moods2))
            union = len(moods1.union(moods2))
            
            return intersection / union if union > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating mood compatibility: {e}")
            return 0.0


class StyleTransferService:
    """Main style transfer service"""
    
    def __init__(self,
                 style_extractor: StyleExtractor,
                 transfer_engine: StyleTransferEngine,
                 style_analyzer: StyleAnalyzer):
        self.style_extractor = style_extractor
        self.transfer_engine = transfer_engine
        self.style_analyzer = style_analyzer
        
        # In-memory storage (replace with database in production)
        self.style_signatures: Dict[str, StyleSignature] = {}
        self.style_transfers: Dict[str, StyleTransfer] = {}
        self.style_evolutions: Dict[str, StyleEvolution] = {}
        self.cross_medium_mappings: Dict[str, CrossMediumMapping] = {}
        
        # User context
        self.user_styles: Dict[str, List[str]] = {}  # user_id -> [signature_ids]
        self.user_transfers: Dict[str, List[str]] = {}  # user_id -> [transfer_ids]
        
        # Background tasks
        self._background_tasks: List[asyncio.Task] = []
        self._running = False
    
    async def start(self):
        """Start the style transfer service"""
        if self._running:
            return
        
        self._running = True
        logger.info("Starting Style Transfer Service")
        
        # Start background tasks
        self._background_tasks = [
            asyncio.create_task(self._analyze_style_trends()),
            asyncio.create_task(self._optimize_transfer_mappings()),
            asyncio.create_task(self._generate_style_evolutions())
        ]
    
    async def stop(self):
        """Stop the style transfer service"""
        if not self._running:
            return
        
        self._running = False
        logger.info("Stopping Style Transfer Service")
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        
        await asyncio.gather(*self._background_tasks, return_exceptions=True)
        self._background_tasks.clear()
    
    async def extract_style(self, user_id: str, work_data: Any, medium: CreativeMedium,
                          work_name: Optional[str] = None) -> StyleSignature:
        """Extract style from a creative work"""
        try:
            signature = await self.style_extractor.extract_style(work_data, medium)
            
            if work_name:
                signature.name = f"Style from {work_name}"
            
            signature.extracted_from = work_name
            
            # Store signature
            self.style_signatures[signature.signature_id] = signature
            
            # Associate with user
            if user_id not in self.user_styles:
                self.user_styles[user_id] = []
            self.user_styles[user_id].append(signature.signature_id)
            
            logger.info(f"Extracted style {signature.signature_id} for user {user_id}")
            return signature
            
        except Exception as e:
            logger.error(f"Error extracting style: {e}")
            # Return default signature
            return StyleSignature(
                signature_id=str(uuid4()),
                name="Default Style",
                medium=medium,
                category=StyleCategory.CONTEMPORARY,
                attributes={}
            )
    
    async def transfer_style(self, user_id: str, signature_id: str, target_medium: CreativeMedium,
                           method: TransferMethod = TransferMethod.HYBRID_APPROACH) -> Optional[StyleTransfer]:
        """Transfer a style to a different medium"""
        try:
            if signature_id not in self.style_signatures:
                logger.warning(f"Style signature {signature_id} not found")
                return None
            
            source_signature = self.style_signatures[signature_id]
            
            # Perform transfer
            transfer = await self.transfer_engine.transfer_style(source_signature, target_medium, method)
            
            # Store adapted signature
            self.style_signatures[transfer.adapted_signature.signature_id] = transfer.adapted_signature
            
            # Store transfer
            self.style_transfers[transfer.transfer_id] = transfer
            
            # Associate with user
            if user_id not in self.user_transfers:
                self.user_transfers[user_id] = []
            self.user_transfers[user_id].append(transfer.transfer_id)
            
            if user_id not in self.user_styles:
                self.user_styles[user_id] = []
            self.user_styles[user_id].append(transfer.adapted_signature.signature_id)
            
            logger.info(f"Transferred style {signature_id} to {target_medium.value} for user {user_id}")
            return transfer
            
        except Exception as e:
            logger.error(f"Error transferring style: {e}")
            return None
    
    async def get_adaptation_suggestions(self, signature_id: str, target_medium: CreativeMedium) -> List[Dict[str, Any]]:
        """Get suggestions for adapting a style to target medium"""
        try:
            if signature_id not in self.style_signatures:
                return []
            
            signature = self.style_signatures[signature_id]
            suggestions = await self.transfer_engine.suggest_adaptations(signature, target_medium)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error getting adaptation suggestions: {e}")
            return []
    
    async def compare_styles(self, signature_id1: str, signature_id2: str) -> Dict[str, float]:
        """Compare two style signatures"""
        try:
            if signature_id1 not in self.style_signatures or signature_id2 not in self.style_signatures:
                return {}
            
            sig1 = self.style_signatures[signature_id1]
            sig2 = self.style_signatures[signature_id2]
            
            comparison = await self.style_analyzer.compare_styles(sig1, sig2)
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error comparing styles: {e}")
            return {}
    
    async def find_similar_styles(self, signature_id: str, user_id: Optional[str] = None) -> List[Tuple[StyleSignature, float]]:
        """Find styles similar to the given signature"""
        try:
            if signature_id not in self.style_signatures:
                return []
            
            signature = self.style_signatures[signature_id]
            
            # Determine search scope
            if user_id and user_id in self.user_styles:
                search_signatures = [self.style_signatures[sid] for sid in self.user_styles[user_id] 
                                   if sid in self.style_signatures]
            else:
                search_signatures = list(self.style_signatures.values())
            
            # Find similar styles
            similar_styles = await self.style_analyzer.find_similar_styles(signature, search_signatures)
            
            return similar_styles
            
        except Exception as e:
            logger.error(f"Error finding similar styles: {e}")
            return []
    
    async def get_user_styles(self, user_id: str) -> List[StyleSignature]:
        """Get all styles for a user"""
        try:
            user_style_ids = self.user_styles.get(user_id, [])
            user_styles = [self.style_signatures[sid] for sid in user_style_ids 
                          if sid in self.style_signatures]
            
            return user_styles
            
        except Exception as e:
            logger.error(f"Error getting user styles: {e}")
            return []
    
    async def get_user_transfers(self, user_id: str) -> List[StyleTransfer]:
        """Get all style transfers for a user"""
        try:
            user_transfer_ids = self.user_transfers.get(user_id, [])
            user_transfers = [self.style_transfers[tid] for tid in user_transfer_ids 
                            if tid in self.style_transfers]
            
            return user_transfers
            
        except Exception as e:
            logger.error(f"Error getting user transfers: {e}")
            return []
    
    async def create_style_evolution(self, user_id: str, original_signature_id: str,
                                   evolution_path: List[CreativeMedium]) -> Optional[StyleEvolution]:
        """Create a style evolution through multiple mediums"""
        try:
            if original_signature_id not in self.style_signatures:
                return None
            
            evolution_signatures = []
            current_signature_id = original_signature_id
            
            # Apply transfers in sequence
            for target_medium in evolution_path:
                transfer = await self.transfer_style(user_id, current_signature_id, target_medium)
                if transfer:
                    evolution_signatures.append((transfer.adapted_signature.signature_id, target_medium))
                    current_signature_id = transfer.adapted_signature.signature_id
                else:
                    logger.warning(f"Failed to transfer to {target_medium.value}")
                    break
            
            if evolution_signatures:
                # Calculate style drift
                original_sig = self.style_signatures[original_signature_id]
                final_sig = self.style_signatures[current_signature_id]
                comparison = await self.style_analyzer.compare_styles(original_sig, final_sig)
                style_drift = 1.0 - comparison.get("overall_similarity", 0.0)
                
                evolution = StyleEvolution(
                    evolution_id=str(uuid4()),
                    original_signature=original_signature_id,
                    evolution_path=evolution_signatures,
                    final_signature=current_signature_id,
                    evolution_steps=len(evolution_signatures),
                    style_drift=style_drift
                )
                
                self.style_evolutions[evolution.evolution_id] = evolution
                
                logger.info(f"Created style evolution {evolution.evolution_id} for user {user_id}")
                return evolution
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating style evolution: {e}")
            return None
    
    async def get_transfer_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get transfer statistics for a user"""
        try:
            user_transfers = await self.get_user_transfers(user_id)
            
            if not user_transfers:
                return {}
            
            # Calculate statistics
            total_transfers = len(user_transfers)
            avg_confidence = sum(t.confidence_score for t in user_transfers) / total_transfers
            avg_fidelity = sum(t.fidelity_score for t in user_transfers) / total_transfers
            
            # Method distribution
            method_counts = {}
            for transfer in user_transfers:
                method = transfer.transfer_method.value
                method_counts[method] = method_counts.get(method, 0) + 1
            
            # Target medium distribution
            medium_counts = {}
            for transfer in user_transfers:
                medium = transfer.target_medium.value
                medium_counts[medium] = medium_counts.get(medium, 0) + 1
            
            return {
                "total_transfers": total_transfers,
                "average_confidence": avg_confidence,
                "average_fidelity": avg_fidelity,
                "method_distribution": method_counts,
                "target_medium_distribution": medium_counts,
                "most_used_method": max(method_counts.items(), key=lambda x: x[1])[0] if method_counts else None,
                "preferred_target_medium": max(medium_counts.items(), key=lambda x: x[1])[0] if medium_counts else None
            }
            
        except Exception as e:
            logger.error(f"Error getting transfer statistics: {e}")
            return {}
    
    # Background tasks
    
    async def _analyze_style_trends(self):
        """Background task to analyze style trends"""
        while self._running:
            try:
                # Analyze trends in styles and transfers
                all_signatures = list(self.style_signatures.values())
                
                if len(all_signatures) > 10:
                    # Analyze category trends
                    category_counts = {}
                    for signature in all_signatures:
                        category = signature.category.value
                        category_counts[category] = category_counts.get(category, 0) + 1
                    
                    logger.info(f"Style trends: {category_counts}")
                
                # Wait 6 hours before next analysis
                await asyncio.sleep(21600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error analyzing style trends: {e}")
                await asyncio.sleep(21600)
    
    async def _optimize_transfer_mappings(self):
        """Background task to optimize transfer mappings"""
        while self._running:
            try:
                # Analyze transfer success rates and optimize mappings
                all_transfers = list(self.style_transfers.values())
                
                if len(all_transfers) > 20:
                    # Find best performing transfer methods
                    method_performance = {}
                    
                    for transfer in all_transfers:
                        method = transfer.transfer_method
                        performance = (transfer.confidence_score + transfer.fidelity_score) / 2
                        
                        if method not in method_performance:
                            method_performance[method] = []
                        method_performance[method].append(performance)
                    
                    # Calculate averages
                    for method in method_performance:
                        avg_performance = sum(method_performance[method]) / len(method_performance[method])
                        logger.info(f"Method {method.value} average performance: {avg_performance:.2f}")
                
                # Wait 12 hours before next optimization
                await asyncio.sleep(43200)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error optimizing transfer mappings: {e}")
                await asyncio.sleep(43200)
    
    async def _generate_style_evolutions(self):
        """Background task to generate style evolutions"""
        while self._running:
            try:
                # Generate style evolutions for interesting signatures
                high_quality_signatures = []
                
                for signature in self.style_signatures.values():
                    if signature.uniqueness_score > 0.7 and signature.adaptability_score > 0.6:
                        high_quality_signatures.append(signature)
                
                # Create evolutions for some high-quality signatures
                for signature in high_quality_signatures[:3]:  # Limit to 3 per cycle
                    evolution_path = [CreativeMedium.DIGITAL_ART, CreativeMedium.DESIGN, CreativeMedium.VISUAL_ART]
                    
                    # Find a user who has this signature (simplified)
                    user_id = "system"  # System-generated evolution
                    
                    evolution = await self.create_style_evolution(user_id, signature.signature_id, evolution_path)
                    
                    if evolution:
                        logger.info(f"Generated system evolution {evolution.evolution_id}")
                
                # Wait 24 hours before next evolution generation
                await asyncio.sleep(86400)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error generating style evolutions: {e}")
                await asyncio.sleep(86400)


# Singleton instance
_style_transfer_service_instance: Optional[StyleTransferService] = None


def get_style_transfer_service() -> StyleTransferService:
    """Get the singleton style transfer service instance"""
    global _style_transfer_service_instance
    
    if _style_transfer_service_instance is None:
        # Initialize with default implementations
        style_extractor = UniversalStyleExtractor()
        transfer_engine = IntelligentStyleTransferEngine()
        style_analyzer = ComprehensiveStyleAnalyzer()
        
        _style_transfer_service_instance = StyleTransferService(
            style_extractor=style_extractor,
            transfer_engine=transfer_engine,
            style_analyzer=style_analyzer
        )
    
    return _style_transfer_service_instance


async def main():
    """Example usage of the style transfer service"""
    service = get_style_transfer_service()
    
    try:
        await service.start()
        
        user_id = "creative_user_123"
        
        # Example 1: Extract style from visual work
        print("=== Extracting Style ===")
        visual_work_data = {
            'image': 'sample_image_data',
            'metadata': {
                'title': 'Abstract Painting',
                'medium': 'oil_on_canvas'
            }
        }
        
        visual_signature = await service.extract_style(
            user_id=user_id,
            work_data=visual_work_data,
            medium=CreativeMedium.VISUAL_ART,
            work_name="Abstract Painting"
        )
        
        print(f"Extracted style: {visual_signature.name}")
        print(f"Category: {visual_signature.category.value}")
        print(f"Complexity: {visual_signature.complexity_score:.2f}")
        print(f"Uniqueness: {visual_signature.uniqueness_score:.2f}")
        print("---")
        
        # Example 2: Transfer style to different medium
        print("=== Transferring Style ===")
        transfer = await service.transfer_style(
            user_id=user_id,
            signature_id=visual_signature.signature_id,
            target_medium=CreativeMedium.MUSIC,
            method=TransferMethod.CONCEPTUAL_TRANSLATION
        )
        
        if transfer:
            print(f"Transfer: {transfer.transfer_method.value}")
            print(f"Confidence: {transfer.confidence_score:.2f}")
            print(f"Fidelity: {transfer.fidelity_score:.2f}")
            print(f"Adapted style: {transfer.adapted_signature.name}")
            print("---")
        
        # Example 3: Get adaptation suggestions
        print("=== Adaptation Suggestions ===")
        suggestions = await service.get_adaptation_suggestions(
            visual_signature.signature_id,
            CreativeMedium.WRITING
        )
        
        for suggestion in suggestions:
            print(f"Attribute: {suggestion['attribute']}")
            print(f"Adaptation: {suggestion['adaptation']}")
            print(f"Confidence: {suggestion['confidence']:.2f}")
            print("---")
        
        # Example 4: Extract another style and compare
        print("=== Style Comparison ===")
        music_work_data = {
            'audio': 'sample_audio_data',
            'metadata': {
                'title': 'Jazz Composition',
                'genre': 'jazz'
            }
        }
        
        music_signature = await service.extract_style(
            user_id=user_id,
            work_data=music_work_data,
            medium=CreativeMedium.MUSIC,
            work_name="Jazz Composition"
        )
        
        comparison = await service.compare_styles(
            visual_signature.signature_id,
            music_signature.signature_id
        )
        
        print(f"Overall similarity: {comparison.get('overall_similarity', 0):.2f}")
        print(f"Medium compatibility: {comparison.get('medium_compatibility', 0):.2f}")
        print(f"Mood compatibility: {comparison.get('mood_compatibility', 0):.2f}")
        print("---")
        
        # Example 5: Find similar styles
        print("=== Finding Similar Styles ===")
        similar_styles = await service.find_similar_styles(visual_signature.signature_id, user_id)
        
        for signature, similarity in similar_styles:
            print(f"Similar style: {signature.name} (similarity: {similarity:.2f})")
        
        if not similar_styles:
            print("No similar styles found (need more styles in database)")
        print("---")
        
        # Example 6: Create style evolution
        print("=== Style Evolution ===")
        evolution_path = [CreativeMedium.DIGITAL_ART, CreativeMedium.DESIGN]
        
        evolution = await service.create_style_evolution(
            user_id=user_id,
            original_signature_id=visual_signature.signature_id,
            evolution_path=evolution_path
        )
        
        if evolution:
            print(f"Evolution ID: {evolution.evolution_id}")
            print(f"Evolution steps: {evolution.evolution_steps}")
            print(f"Style drift: {evolution.style_drift:.2f}")
            print("Evolution path:")
            for signature_id, medium in evolution.evolution_path:
                print(f"  -> {medium.value}")
        print("---")
        
        # Example 7: Get user statistics
        print("=== Transfer Statistics ===")
        stats = await service.get_transfer_statistics(user_id)
        
        for key, value in stats.items():
            print(f"{key}: {value}")
        
        # Let background tasks run briefly
        await asyncio.sleep(5)
        
    finally:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())