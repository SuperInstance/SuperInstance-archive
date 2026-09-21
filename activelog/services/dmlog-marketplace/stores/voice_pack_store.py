"""
Character voice pack marketplace for NPCs and player characters
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from ..models.base import VoicePack, Product, ContentType, ProductStatus

class VoiceType(Enum):
    MALE = "male"
    FEMALE = "female"
    NON_BINARY = "non_binary"
    CREATURE = "creature"
    ROBOTIC = "robotic"
    ELEMENTAL = "elemental"

class VoiceAge(Enum):
    CHILD = "child"
    YOUNG_ADULT = "young_adult"
    ADULT = "adult"
    MIDDLE_AGED = "middle_aged"
    ELDERLY = "elderly"
    ANCIENT = "ancient"

class VoiceAccent(Enum):
    NEUTRAL = "neutral"
    BRITISH = "british"
    SCOTTISH = "scottish"
    IRISH = "irish"
    SOUTHERN_US = "southern_us"
    NEW_YORK = "new_york"
    COCKNEY = "cockney"
    FRENCH = "french"
    GERMAN = "german"
    RUSSIAN = "russian"
    SPANISH = "spanish"
    FANTASY_ELVISH = "fantasy_elvish"
    FANTASY_DWARVEN = "fantasy_dwarven"
    PIRATE = "pirate"
    NOBLE = "noble"

class VoicePersonality(Enum):
    FRIENDLY = "friendly"
    GRUFF = "gruff"
    MYSTERIOUS = "mysterious"
    CHEERFUL = "cheerful"
    MENACING = "menacing"
    WISE = "wise"
    SARCASTIC = "sarcastic"
    NERVOUS = "nervous"
    CONFIDENT = "confident"
    DRAMATIC = "dramatic"
    SCHOLARLY = "scholarly"
    COMEDIC = "comedic"

class AudioQuality(Enum):
    STANDARD = "standard"  # Good for online play
    HIGH = "high"         # Studio quality
    BROADCAST = "broadcast"  # Professional broadcast quality

class VoicePackStore:
    """Manages character voice pack marketplace"""
    
    def __init__(self):
        self.voice_packs: Dict[str, VoicePack] = {}
        self.voice_actors: Dict[str, Dict[str, Any]] = {}
        self.sample_libraries: Dict[str, List[Dict[str, Any]]] = {}
        self.featured_voices: List[str] = []
        
        # Initialize voice categories and phrases
        self._initialize_voice_categories()
    
    def _initialize_voice_categories(self):
        """Initialize voice pack categories and phrase types"""
        
        self.character_archetypes = {
            "warrior": {
                "personality": [VoicePersonality.GRUFF, VoicePersonality.CONFIDENT],
                "phrases": ["battle_cries", "challenges", "commands", "threats"]
            },
            "wizard": {
                "personality": [VoicePersonality.SCHOLARLY, VoicePersonality.MYSTERIOUS],
                "phrases": ["incantations", "explanations", "warnings", "discoveries"]
            },
            "rogue": {
                "personality": [VoicePersonality.SARCASTIC, VoicePersonality.CONFIDENT],
                "phrases": ["quips", "boasts", "whispers", "plans"]
            },
            "cleric": {
                "personality": [VoicePersonality.WISE, VoicePersonality.FRIENDLY],
                "phrases": ["prayers", "blessings", "guidance", "comfort"]
            },
            "merchant": {
                "personality": [VoicePersonality.CHEERFUL, VoicePersonality.FRIENDLY],
                "phrases": ["greetings", "sales_pitches", "negotiations", "farewells"]
            },
            "noble": {
                "personality": [VoicePersonality.DRAMATIC, VoicePersonality.CONFIDENT],
                "phrases": ["commands", "declarations", "complaints", "praise"]
            },
            "innkeeper": {
                "personality": [VoicePersonality.FRIENDLY, VoicePersonality.CHEERFUL],
                "phrases": ["welcomes", "offers", "gossip", "stories"]
            },
            "guard": {
                "personality": [VoicePersonality.GRUFF, VoicePersonality.CONFIDENT],
                "phrases": ["challenges", "warnings", "orders", "investigations"]
            },
            "villain": {
                "personality": [VoicePersonality.MENACING, VoicePersonality.DRAMATIC],
                "phrases": ["threats", "monologues", "taunts", "commands"]
            }
        }
        
        self.phrase_categories = {
            "social": [
                "greetings", "farewells", "introductions", "small_talk",
                "compliments", "insults", "apologies", "thanks"
            ],
            "combat": [
                "battle_cries", "threats", "challenges", "victory_shouts",
                "defeat_cries", "pain_sounds", "effort_grunts", "death_rattle"
            ],
            "emotion": [
                "laughter", "crying", "gasps", "sighs", "screams",
                "whispers", "shouts", "muttering", "humming"
            ],
            "magic": [
                "incantations", "spell_casting", "magical_reactions",
                "enchantment_effects", "dispelling", "ritual_chanting"
            ],
            "roleplay": [
                "personality_quirks", "catchphrases", "nervous_habits",
                "confident_declarations", "storytelling", "jokes"
            ]
        }
        
        self.voice_tags = [
            "professional", "amateur", "ai_generated", "celebrity_impression",
            "multilingual", "singing_capable", "character_flexible",
            "accent_specialist", "creature_specialist", "comedy_focused"
        ]
    
    def register_voice_actor(
        self,
        actor_id: str,
        stage_name: str,
        bio: str,
        specialties: List[str],
        voice_range: List[VoiceType],
        accent_expertise: List[VoiceAccent],
        demo_reel_url: str,
        professional_rate: Decimal,
        is_verified: bool = False
    ) -> Dict[str, Any]:
        """Register voice actor"""
        
        actor_profile = {
            "id": actor_id,
            "stage_name": stage_name,
            "bio": bio,
            "specialties": specialties,
            "voice_range": [vt.value for vt in voice_range],
            "accent_expertise": [acc.value for acc in accent_expertise],
            "demo_reel_url": demo_reel_url,
            "professional_rate": professional_rate,
            "is_verified": is_verified,
            "is_available": True,
            "total_packs": 0,
            "average_rating": Decimal("0.0"),
            "created_at": datetime.utcnow(),
            "languages": ["english"],  # Default
            "equipment": "professional"  # professional, amateur, studio
        }
        
        self.voice_actors[actor_id] = actor_profile
        self.sample_libraries[actor_id] = []
        
        return actor_profile
    
    def create_voice_pack(
        self,
        creator_id: str,
        title: str,
        description: str,
        character_archetype: str,
        voice_type: VoiceType,
        voice_age: VoiceAge,
        accent: VoiceAccent,
        personality: VoicePersonality,
        phrase_categories: List[str],
        phrase_count: int,
        audio_quality: AudioQuality,
        price: Decimal = Decimal("0.00"),
        languages: List[str] = None,
        is_character_flexible: bool = False,
        includes_singing: bool = False
    ) -> VoicePack:
        """Create new voice pack"""
        
        voice_pack = VoicePack(
            creator_id=creator_id,
            title=title,
            description=description,
            content_type=ContentType.VOICE_PACK,
            price=price,
            voice_type=voice_type.value,
            voice_age=voice_age.value,
            accent=accent.value,
            personality=personality.value,
            character_archetype=character_archetype,
            phrase_categories=phrase_categories,
            phrase_count=phrase_count,
            audio_quality=audio_quality.value,
            languages=languages or ["english"],
            is_character_flexible=is_character_flexible,
            includes_singing=includes_singing,
            sample_phrases=[]
        )
        
        self.voice_packs[voice_pack.id] = voice_pack
        
        # Update actor stats
        if creator_id in self.voice_actors:
            self.voice_actors[creator_id]["total_packs"] += 1
        
        return voice_pack
    
    def add_sample_phrases(
        self,
        voice_pack_id: str,
        creator_id: str,
        sample_urls: List[Dict[str, str]]
    ) -> bool:
        """Add sample phrases to voice pack"""
        
        if voice_pack_id not in self.voice_packs:
            return False
        
        voice_pack = self.voice_packs[voice_pack_id]
        
        if voice_pack.creator_id != creator_id:
            return False
        
        # Validate sample format: [{"phrase": "Hello there!", "url": "http://...", "category": "greetings"}]
        for sample in sample_urls:
            if all(key in sample for key in ["phrase", "url", "category"]):
                voice_pack.sample_phrases.append(sample)
        
        return True
    
    def search_voice_packs(
        self,
        query: Optional[str] = None,
        character_archetype: Optional[str] = None,
        voice_type: Optional[VoiceType] = None,
        voice_age: Optional[VoiceAge] = None,
        accent: Optional[VoiceAccent] = None,
        personality: Optional[VoicePersonality] = None,
        phrase_categories: List[str] = None,
        audio_quality: Optional[AudioQuality] = None,
        languages: List[str] = None,
        price_min: Optional[Decimal] = None,
        price_max: Optional[Decimal] = None,
        min_phrase_count: Optional[int] = None,
        is_character_flexible: Optional[bool] = None,
        includes_singing: Optional[bool] = None,
        creator_id: Optional[str] = None,
        sort_by: str = "relevance"
    ) -> List[VoicePack]:
        """Search voice packs with filters"""
        
        results = []
        
        for voice_pack in self.voice_packs.values():
            if voice_pack.status != ProductStatus.ACTIVE:
                continue
            
            # Text search
            if query:
                search_text = f"{voice_pack.title} {voice_pack.description} {voice_pack.character_archetype} {' '.join(voice_pack.phrase_categories)}".lower()
                if query.lower() not in search_text:
                    continue
            
            # Character archetype filter
            if character_archetype and voice_pack.character_archetype != character_archetype:
                continue
            
            # Voice type filter
            if voice_type and voice_pack.voice_type != voice_type.value:
                continue
            
            # Age filter
            if voice_age and voice_pack.voice_age != voice_age.value:
                continue
            
            # Accent filter
            if accent and voice_pack.accent != accent.value:
                continue
            
            # Personality filter
            if personality and voice_pack.personality != personality.value:
                continue
            
            # Phrase categories filter
            if phrase_categories:
                pack_categories = set(voice_pack.phrase_categories)
                required_categories = set(phrase_categories)
                if not required_categories.issubset(pack_categories):
                    continue
            
            # Audio quality filter
            if audio_quality and voice_pack.audio_quality != audio_quality.value:
                continue
            
            # Language filter
            if languages:
                pack_languages = set(voice_pack.languages)
                required_languages = set(languages)
                if not required_languages.intersection(pack_languages):
                    continue
            
            # Price filter
            if price_min and voice_pack.price < price_min:
                continue
            if price_max and voice_pack.price > price_max:
                continue
            
            # Phrase count filter
            if min_phrase_count and voice_pack.phrase_count < min_phrase_count:
                continue
            
            # Character flexibility filter
            if is_character_flexible is not None and voice_pack.is_character_flexible != is_character_flexible:
                continue
            
            # Singing capability filter
            if includes_singing is not None and voice_pack.includes_singing != includes_singing:
                continue
            
            # Creator filter
            if creator_id and voice_pack.creator_id != creator_id:
                continue
            
            results.append(voice_pack)
        
        # Sort results
        if sort_by == "price_low":
            results.sort(key=lambda vp: vp.price)
        elif sort_by == "price_high":
            results.sort(key=lambda vp: vp.price, reverse=True)
        elif sort_by == "phrase_count":
            results.sort(key=lambda vp: vp.phrase_count, reverse=True)
        elif sort_by == "newest":
            results.sort(key=lambda vp: vp.created_at, reverse=True)
        elif sort_by == "popular":
            results.sort(key=lambda vp: (vp.download_count, vp.average_rating), reverse=True)
        else:  # relevance
            results.sort(key=lambda vp: (vp.average_rating, vp.download_count), reverse=True)
        
        return results
    
    def get_voice_pack_details(self, voice_pack_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed voice pack information"""
        
        if voice_pack_id not in self.voice_packs:
            return None
        
        voice_pack = self.voice_packs[voice_pack_id]
        
        return {
            "voice_pack": voice_pack.dict(),
            "voice_actor_info": self._get_voice_actor_info(voice_pack.creator_id),
            "sample_phrases": voice_pack.sample_phrases,
            "technical_specs": self._get_technical_specs(voice_pack),
            "usage_suggestions": self._get_usage_suggestions(voice_pack),
            "similar_voice_packs": self._get_similar_voice_packs(voice_pack),
            "phrase_breakdown": self._get_phrase_breakdown(voice_pack)
        }
    
    def _get_voice_actor_info(self, actor_id: str) -> Dict[str, Any]:
        """Get voice actor information"""
        
        if actor_id in self.voice_actors:
            return self.voice_actors[actor_id]
        
        # Default info for non-registered creators
        return {
            "id": actor_id,
            "stage_name": f"Voice Artist {actor_id[:8]}",
            "bio": "Independent voice artist",
            "is_verified": False,
            "total_packs": len([vp for vp in self.voice_packs.values() if vp.creator_id == actor_id]),
            "average_rating": Decimal("4.0")
        }
    
    def _get_technical_specs(self, voice_pack: VoicePack) -> Dict[str, Any]:
        """Get technical specifications"""
        
        quality_specs = {
            AudioQuality.STANDARD.value: {
                "sample_rate": "44.1 kHz",
                "bit_depth": "16-bit",
                "format": "MP3 320kbps",
                "suitable_for": "Online play, streaming"
            },
            AudioQuality.HIGH.value: {
                "sample_rate": "48 kHz",
                "bit_depth": "24-bit", 
                "format": "WAV/FLAC",
                "suitable_for": "Professional recording, broadcast"
            },
            AudioQuality.BROADCAST.value: {
                "sample_rate": "96 kHz",
                "bit_depth": "32-bit",
                "format": "WAV uncompressed",
                "suitable_for": "Professional production, mastering"
            }
        }
        
        specs = quality_specs.get(voice_pack.audio_quality, quality_specs[AudioQuality.STANDARD.value])
        
        # Estimate file sizes
        avg_phrase_duration = 3  # seconds
        total_duration = voice_pack.phrase_count * avg_phrase_duration
        
        if voice_pack.audio_quality == AudioQuality.STANDARD.value:
            estimated_size = total_duration * 0.32  # MB for 320kbps MP3
        elif voice_pack.audio_quality == AudioQuality.HIGH.value:
            estimated_size = total_duration * 1.4   # MB for 24-bit WAV
        else:
            estimated_size = total_duration * 2.8   # MB for 32-bit WAV
        
        specs.update({
            "total_phrases": voice_pack.phrase_count,
            "estimated_duration": f"{total_duration // 60}:{total_duration % 60:02d}",
            "estimated_file_size": f"~{estimated_size:.1f} MB",
            "languages": voice_pack.languages
        })
        
        return specs
    
    def _get_usage_suggestions(self, voice_pack: VoicePack) -> List[str]:
        """Generate usage suggestions"""
        
        suggestions = []
        
        # Character-specific suggestions
        if voice_pack.character_archetype in self.character_archetypes:
            archetype_info = self.character_archetypes[voice_pack.character_archetype]
            suggestions.append(f"Perfect for {voice_pack.character_archetype} NPCs and characters")
        
        # Personality-based suggestions
        personality_suggestions = {
            VoicePersonality.FRIENDLY.value: "Great for shopkeepers, innkeepers, and helpful NPCs",
            VoicePersonality.MENACING.value: "Ideal for villains, monsters, and intimidating characters",
            VoicePersonality.WISE.value: "Perfect for sages, mentors, and ancient beings",
            VoicePersonality.COMEDIC.value: "Excellent for comic relief characters and light-hearted moments"
        }
        
        if voice_pack.personality in personality_suggestions:
            suggestions.append(personality_suggestions[voice_pack.personality])
        
        # Accent-based suggestions
        if voice_pack.accent != VoiceAccent.NEUTRAL.value:
            suggestions.append(f"Adds authentic {voice_pack.accent.replace('_', ' ')} flavor to characters")
        
        # Feature-based suggestions
        if voice_pack.is_character_flexible:
            suggestions.append("Flexible enough for multiple character types")
        
        if voice_pack.includes_singing:
            suggestions.append("Includes singing for bards and musical moments")
        
        if "multilingual" in voice_pack.languages:
            suggestions.append("Multi-language support for diverse campaigns")
        
        return suggestions
    
    def _get_similar_voice_packs(self, voice_pack: VoicePack) -> List[VoicePack]:
        """Find similar voice packs"""
        
        similar = []
        
        for other in self.voice_packs.values():
            if other.id == voice_pack.id or other.status != ProductStatus.ACTIVE:
                continue
            
            similarity_score = 0
            
            # Same character archetype
            if other.character_archetype == voice_pack.character_archetype:
                similarity_score += 3
            
            # Same voice type and age
            if other.voice_type == voice_pack.voice_type:
                similarity_score += 2
            if other.voice_age == voice_pack.voice_age:
                similarity_score += 1
            
            # Same personality
            if other.personality == voice_pack.personality:
                similarity_score += 2
            
            # Common phrase categories
            common_categories = set(voice_pack.phrase_categories) & set(other.phrase_categories)
            similarity_score += len(common_categories)
            
            # Same accent
            if other.accent == voice_pack.accent:
                similarity_score += 1
            
            # Same creator
            if other.creator_id == voice_pack.creator_id:
                similarity_score += 1
            
            if similarity_score >= 3:
                similar.append(other)
        
        similar.sort(key=lambda vp: (vp.average_rating, vp.download_count), reverse=True)
        return similar[:6]
    
    def _get_phrase_breakdown(self, voice_pack: VoicePack) -> Dict[str, int]:
        """Get breakdown of phrases by category"""
        
        # Estimate phrase distribution based on categories
        total_phrases = voice_pack.phrase_count
        num_categories = len(voice_pack.phrase_categories)
        
        if num_categories == 0:
            return {}
        
        base_per_category = total_phrases // num_categories
        remainder = total_phrases % num_categories
        
        breakdown = {}
        for i, category in enumerate(voice_pack.phrase_categories):
            phrase_count = base_per_category
            if i < remainder:  # Distribute remainder
                phrase_count += 1
            breakdown[category] = phrase_count
        
        return breakdown
    
    def get_voice_recommendations_for_character(
        self,
        character_race: str,
        character_class: str,
        character_background: str,
        personality_traits: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Get voice pack recommendations for specific character"""
        
        recommendations = []
        
        # Map character info to voice characteristics
        race_voice_mapping = {
            "elf": {"voice_type": VoiceType.FEMALE, "accent": VoiceAccent.FANTASY_ELVISH, "age": VoiceAge.ADULT},
            "dwarf": {"voice_type": VoiceType.MALE, "accent": VoiceAccent.FANTASY_DWARVEN, "age": VoiceAge.MIDDLE_AGED},
            "human": {"voice_type": VoiceType.MALE, "accent": VoiceAccent.NEUTRAL, "age": VoiceAge.ADULT},
            "halfling": {"voice_type": VoiceType.FEMALE, "accent": VoiceAccent.CHEERFUL, "age": VoiceAge.YOUNG_ADULT},
            "dragonborn": {"voice_type": VoiceType.CREATURE, "accent": VoiceAccent.NEUTRAL, "age": VoiceAge.ADULT}
        }
        
        class_archetype_mapping = {
            "fighter": "warrior",
            "wizard": "wizard", 
            "rogue": "rogue",
            "cleric": "cleric",
            "ranger": "warrior",
            "bard": "merchant",  # Often social
            "paladin": "warrior",
            "warlock": "wizard"
        }
        
        # Get suggested characteristics
        suggested_archetype = class_archetype_mapping.get(character_class.lower(), "warrior")
        
        # Find matching voice packs
        for voice_pack in self.voice_packs.values():
            if voice_pack.status != ProductStatus.ACTIVE:
                continue
            
            match_score = 0
            
            # Character archetype match
            if voice_pack.character_archetype == suggested_archetype:
                match_score += 3
            
            # Race-based preferences
            if character_race.lower() in race_voice_mapping:
                race_prefs = race_voice_mapping[character_race.lower()]
                if voice_pack.voice_type == race_prefs.get("voice_type", VoiceType.MALE).value:
                    match_score += 2
                if voice_pack.accent == race_prefs.get("accent", VoiceAccent.NEUTRAL).value:
                    match_score += 2
            
            # Personality trait matching
            if personality_traits:
                trait_personality_mapping = {
                    "friendly": VoicePersonality.FRIENDLY,
                    "gruff": VoicePersonality.GRUFF,
                    "mysterious": VoicePersonality.MYSTERIOUS,
                    "cheerful": VoicePersonality.CHEERFUL
                }
                
                for trait in personality_traits:
                    if trait.lower() in trait_personality_mapping:
                        if voice_pack.personality == trait_personality_mapping[trait.lower()].value:
                            match_score += 2
            
            if match_score > 0:
                recommendations.append({
                    "voice_pack": voice_pack,
                    "match_score": match_score,
                    "match_reasons": self._generate_match_reasons(voice_pack, character_race, character_class, match_score)
                })
        
        # Sort by match score and quality
        recommendations.sort(key=lambda x: (x["match_score"], x["voice_pack"].average_rating), reverse=True)
        return recommendations[:10]
    
    def _generate_match_reasons(self, voice_pack: VoicePack, race: str, char_class: str, score: int) -> List[str]:
        """Generate reasons why voice pack matches character"""
        
        reasons = []
        
        if score >= 3:
            reasons.append(f"Perfect match for {char_class} archetype")
        
        if voice_pack.accent != VoiceAccent.NEUTRAL.value:
            reasons.append(f"Authentic {voice_pack.accent.replace('_', ' ')} accent fits {race} character")
        
        if voice_pack.is_character_flexible:
            reasons.append("Versatile voice suitable for character development")
        
        if voice_pack.phrase_count > 100:
            reasons.append("Extensive phrase library for rich roleplay")
        
        return reasons
    
    def get_featured_voice_packs(self, category: Optional[str] = None) -> List[VoicePack]:
        """Get featured voice packs"""
        
        featured = []
        
        # Get manually featured packs first
        for pack_id in self.featured_voices:
            if pack_id in self.voice_packs:
                pack = self.voice_packs[pack_id]
                if (pack.status == ProductStatus.ACTIVE and
                    (not category or pack.character_archetype == category)):
                    featured.append(pack)
        
        # Fill with high-rated packs if needed
        if len(featured) < 8:
            all_packs = [vp for vp in self.voice_packs.values()
                        if (vp.status == ProductStatus.ACTIVE and
                            vp.id not in self.featured_voices and
                            (not category or vp.character_archetype == category))]
            
            all_packs.sort(key=lambda vp: (vp.average_rating, vp.download_count), reverse=True)
            remaining = 8 - len(featured)
            featured.extend(all_packs[:remaining])
        
        return featured
    
    def get_trending_voice_packs(self, days: int = 7) -> List[VoicePack]:
        """Get trending voice packs"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        trending = []
        for voice_pack in self.voice_packs.values():
            if voice_pack.status != ProductStatus.ACTIVE:
                continue
            
            # Calculate trend score
            trend_score = voice_pack.download_count + (float(voice_pack.average_rating) * 5)
            
            trending.append({
                "voice_pack": voice_pack,
                "trend_score": trend_score
            })
        
        trending.sort(key=lambda x: x["trend_score"], reverse=True)
        return [item["voice_pack"] for item in trending[:15]]
    
    def get_voice_actor_showcase(self, actor_id: str) -> Optional[Dict[str, Any]]:
        """Get voice actor's complete showcase"""
        
        if actor_id not in self.voice_actors:
            return None
        
        actor = self.voice_actors[actor_id]
        actor_packs = [vp for vp in self.voice_packs.values() 
                      if vp.creator_id == actor_id and vp.status == ProductStatus.ACTIVE]
        
        # Group packs by archetype
        packs_by_archetype = {}
        for pack in actor_packs:
            archetype = pack.character_archetype
            if archetype not in packs_by_archetype:
                packs_by_archetype[archetype] = []
            packs_by_archetype[archetype].append(pack)
        
        # Calculate statistics
        total_phrases = sum(pack.phrase_count for pack in actor_packs)
        total_downloads = sum(pack.download_count for pack in actor_packs)
        avg_rating = sum(pack.average_rating for pack in actor_packs) / len(actor_packs) if actor_packs else 0
        
        return {
            "actor": actor,
            "voice_packs": actor_packs,
            "packs_by_archetype": packs_by_archetype,
            "statistics": {
                "total_packs": len(actor_packs),
                "total_phrases": total_phrases,
                "total_downloads": total_downloads,
                "average_rating": round(avg_rating, 2),
                "voice_range_count": len(set(pack.voice_type for pack in actor_packs)),
                "accent_count": len(set(pack.accent for pack in actor_packs))
            }
        }