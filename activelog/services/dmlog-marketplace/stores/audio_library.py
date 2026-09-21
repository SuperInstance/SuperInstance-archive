"""
Sound effects and music library for tabletop gaming
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from ..models.base import AudioTrack, Product, ContentType, ProductStatus

class AudioType(Enum):
    MUSIC = "music"
    SOUND_EFFECT = "sound_effect"
    AMBIENT = "ambient"
    VOICE_ACTING = "voice_acting"

class MusicGenre(Enum):
    EPIC_ORCHESTRAL = "epic_orchestral"
    MEDIEVAL_FANTASY = "medieval_fantasy"
    DARK_AMBIENT = "dark_ambient"
    TAVERN_FOLK = "tavern_folk"
    BATTLE_COMBAT = "battle_combat"
    MYSTERIOUS = "mysterious"
    PEACEFUL = "peaceful"
    HORROR = "horror"
    TRIBAL = "tribal"
    STEAMPUNK = "steampunk"
    CYBERPUNK = "cyberpunk"
    PIRATE = "pirate"
    WESTERN = "western"
    ASIAN_INSPIRED = "asian_inspired"

class SoundCategory(Enum):
    WEAPONS = "weapons"
    MAGIC = "magic"
    NATURE = "nature"
    CREATURES = "creatures"
    ENVIRONMENT = "environment"
    MECHANICAL = "mechanical"
    FOOTSTEPS = "footsteps"
    DOORS = "doors"
    WEATHER = "weather"
    CROWD = "crowd"
    VEHICLE = "vehicle"
    ELEMENTAL = "elemental"

class AudioQuality(Enum):
    STANDARD = "standard"  # 128kbps
    HIGH = "high"         # 256kbps
    LOSSLESS = "lossless" # FLAC

class AudioLibrary:
    """Manages audio content marketplace"""
    
    def __init__(self):
        self.audio_tracks: Dict[str, AudioTrack] = {}
        self.playlists: Dict[str, Dict[str, Any]] = {}
        self.audio_packs: Dict[str, Dict[str, Any]] = {}
        self.featured_audio: List[str] = []
        
        # Initialize categories and moods
        self._initialize_audio_categories()
    
    def _initialize_audio_categories(self):
        """Initialize audio categories and mood tags"""
        
        self.mood_tags = {
            "music": [
                "epic", "heroic", "dramatic", "mysterious", "peaceful", "tense",
                "melancholy", "triumphant", "ominous", "playful", "romantic",
                "nostalgic", "energetic", "calming", "suspenseful", "magical"
            ],
            "ambient": [
                "atmospheric", "immersive", "background", "looping", "subtle",
                "environmental", "spatial", "cinematic", "textural", "evolving"
            ],
            "sound_effects": [
                "realistic", "fantasy", "magical", "mechanical", "organic",
                "impact", "continuous", "one_shot", "layered", "crisp"
            ]
        }
        
        self.scenario_tags = [
            "tavern", "dungeon", "forest", "city", "combat", "exploration",
            "social", "stealth", "travel", "rest", "shopping", "ceremony",
            "celebration", "funeral", "chase", "puzzle", "trap", "boss_fight",
            "revelation", "betrayal", "victory", "defeat", "romance", "comedy"
        ]
        
        self.intensity_levels = [
            "very_low", "low", "medium", "high", "very_high"
        ]
    
    def create_audio_track(
        self,
        creator_id: str,
        title: str,
        description: str,
        audio_type: AudioType,
        duration_seconds: int,
        genre: Optional[MusicGenre] = None,
        category: Optional[SoundCategory] = None,
        mood_tags: List[str] = None,
        scenario_tags: List[str] = None,
        intensity: str = "medium",
        tempo_bpm: Optional[int] = None,
        key_signature: Optional[str] = None,
        price: Decimal = Decimal("0.00"),
        is_loopable: bool = False,
        file_formats: List[str] = None
    ) -> AudioTrack:
        """Create new audio track"""
        
        audio_track = AudioTrack(
            creator_id=creator_id,
            title=title,
            description=description,
            content_type=ContentType.AUDIO,
            price=price,
            audio_type=audio_type.value,
            duration_seconds=duration_seconds,
            genre=genre.value if genre else None,
            category=category.value if category else None,
            mood_tags=mood_tags or [],
            scenario_tags=scenario_tags or [],
            intensity=intensity,
            tempo_bpm=tempo_bpm,
            key_signature=key_signature,
            is_loopable=is_loopable,
            file_formats=file_formats or ["mp3", "wav"]
        )
        
        self.audio_tracks[audio_track.id] = audio_track
        return audio_track
    
    def create_audio_pack(
        self,
        creator_id: str,
        name: str,
        description: str,
        theme: str,
        track_ids: List[str],
        pack_price: Optional[Decimal] = None
    ) -> str:
        """Create audio pack/bundle"""
        
        # Validate tracks exist and belong to creator
        valid_tracks = []
        total_individual_price = Decimal("0.00")
        total_duration = 0
        
        for track_id in track_ids:
            if track_id in self.audio_tracks:
                track = self.audio_tracks[track_id]
                if track.creator_id == creator_id:
                    valid_tracks.append(track_id)
                    total_individual_price += track.price
                    total_duration += track.duration_seconds
        
        if not valid_tracks:
            return ""
        
        # Calculate pack price (15% discount if not specified)
        if pack_price is None:
            pack_price = total_individual_price * Decimal("0.85")
        
        pack_id = f"pack_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{creator_id[:8]}"
        
        audio_pack = {
            "id": pack_id,
            "creator_id": creator_id,
            "name": name,
            "description": description,
            "theme": theme,
            "track_ids": valid_tracks,
            "pack_price": pack_price,
            "individual_price": total_individual_price,
            "savings": total_individual_price - pack_price,
            "total_duration": total_duration,
            "track_count": len(valid_tracks),
            "created_at": datetime.utcnow(),
            "download_count": 0,
            "average_rating": Decimal("0.0")
        }
        
        self.audio_packs[pack_id] = audio_pack
        return pack_id
    
    def create_playlist(
        self,
        user_id: str,
        name: str,
        description: str,
        track_ids: List[str],
        is_public: bool = False,
        scenario: Optional[str] = None
    ) -> str:
        """Create custom playlist"""
        
        # Validate tracks exist
        valid_tracks = [tid for tid in track_ids if tid in self.audio_tracks]
        
        if not valid_tracks:
            return ""
        
        playlist_id = f"playlist_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{user_id[:8]}"
        
        playlist = {
            "id": playlist_id,
            "creator_id": user_id,
            "name": name,
            "description": description,
            "track_ids": valid_tracks,
            "is_public": is_public,
            "scenario": scenario,
            "total_duration": sum(self.audio_tracks[tid].duration_seconds for tid in valid_tracks),
            "created_at": datetime.utcnow(),
            "last_updated": datetime.utcnow(),
            "play_count": 0,
            "likes": 0
        }
        
        self.playlists[playlist_id] = playlist
        return playlist_id
    
    def search_audio(
        self,
        query: Optional[str] = None,
        audio_type: Optional[AudioType] = None,
        genre: Optional[MusicGenre] = None,
        category: Optional[SoundCategory] = None,
        mood_tags: List[str] = None,
        scenario_tags: List[str] = None,
        intensity: Optional[str] = None,
        duration_min: Optional[int] = None,
        duration_max: Optional[int] = None,
        tempo_min: Optional[int] = None,
        tempo_max: Optional[int] = None,
        is_loopable: Optional[bool] = None,
        price_min: Optional[Decimal] = None,
        price_max: Optional[Decimal] = None,
        creator_id: Optional[str] = None,
        sort_by: str = "relevance"
    ) -> List[AudioTrack]:
        """Search audio tracks with filters"""
        
        results = []
        
        for track in self.audio_tracks.values():
            if track.status != ProductStatus.ACTIVE:
                continue
            
            # Text search
            if query:
                search_text = f"{track.title} {track.description} {' '.join(track.mood_tags)} {' '.join(track.scenario_tags)}".lower()
                if query.lower() not in search_text:
                    continue
            
            # Audio type filter
            if audio_type and track.audio_type != audio_type.value:
                continue
            
            # Genre filter
            if genre and track.genre != genre.value:
                continue
            
            # Category filter
            if category and track.category != category.value:
                continue
            
            # Mood tags filter
            if mood_tags:
                track_moods = set(track.mood_tags)
                required_moods = set(mood_tags)
                if not required_moods.issubset(track_moods):
                    continue
            
            # Scenario tags filter
            if scenario_tags:
                track_scenarios = set(track.scenario_tags)
                required_scenarios = set(scenario_tags)
                if not required_scenarios.issubset(track_scenarios):
                    continue
            
            # Intensity filter
            if intensity and track.intensity != intensity:
                continue
            
            # Duration filter
            if duration_min and track.duration_seconds < duration_min:
                continue
            if duration_max and track.duration_seconds > duration_max:
                continue
            
            # Tempo filter
            if tempo_min and (not track.tempo_bpm or track.tempo_bpm < tempo_min):
                continue
            if tempo_max and (not track.tempo_bpm or track.tempo_bpm > tempo_max):
                continue
            
            # Loopable filter
            if is_loopable is not None and track.is_loopable != is_loopable:
                continue
            
            # Price filter
            if price_min and track.price < price_min:
                continue
            if price_max and track.price > price_max:
                continue
            
            # Creator filter
            if creator_id and track.creator_id != creator_id:
                continue
            
            results.append(track)
        
        # Sort results
        if sort_by == "duration_short":
            results.sort(key=lambda t: t.duration_seconds)
        elif sort_by == "duration_long":
            results.sort(key=lambda t: t.duration_seconds, reverse=True)
        elif sort_by == "price_low":
            results.sort(key=lambda t: t.price)
        elif sort_by == "price_high":
            results.sort(key=lambda t: t.price, reverse=True)
        elif sort_by == "newest":
            results.sort(key=lambda t: t.created_at, reverse=True)
        elif sort_by == "popular":
            results.sort(key=lambda t: (t.play_count, t.average_rating), reverse=True)
        else:  # relevance
            results.sort(key=lambda t: (t.average_rating, t.play_count), reverse=True)
        
        return results
    
    def get_recommendations_for_scenario(self, scenario: str, session_length_minutes: int = 180) -> Dict[str, List[AudioTrack]]:
        """Get audio recommendations for specific scenario"""
        
        scenario_mapping = {
            "tavern": {
                "music": ["tavern_folk", "peaceful", "medieval_fantasy"],
                "ambient": ["crowd", "environment"],
                "effects": ["crowd", "doors", "footsteps"]
            },
            "dungeon": {
                "music": ["dark_ambient", "mysterious", "tense"],
                "ambient": ["environment", "atmospheric"],
                "effects": ["footsteps", "doors", "mechanical", "creatures"]
            },
            "forest": {
                "music": ["peaceful", "medieval_fantasy", "nature"],
                "ambient": ["nature", "environment"],
                "effects": ["nature", "creatures", "footsteps", "weather"]
            },
            "combat": {
                "music": ["battle_combat", "epic_orchestral", "tense"],
                "ambient": [],
                "effects": ["weapons", "magic", "creatures"]
            },
            "city": {
                "music": ["medieval_fantasy", "peaceful"],
                "ambient": ["crowd", "environment"],
                "effects": ["crowd", "footsteps", "doors", "vehicle"]
            }
        }
        
        recommendations = {
            "background_music": [],
            "ambient_sounds": [],
            "sound_effects": [],
            "suggested_playlists": []
        }
        
        if scenario in scenario_mapping:
            mapping = scenario_mapping[scenario]
            
            # Get background music
            music_tracks = [t for t in self.audio_tracks.values() 
                          if (t.audio_type == AudioType.MUSIC.value and
                              any(tag in mapping["music"] for tag in [t.genre] + t.mood_tags))]
            music_tracks.sort(key=lambda t: (t.average_rating, t.is_loopable), reverse=True)
            recommendations["background_music"] = music_tracks[:10]
            
            # Get ambient sounds
            ambient_tracks = [t for t in self.audio_tracks.values()
                            if (t.audio_type == AudioType.AMBIENT.value and
                                any(tag in mapping["ambient"] for tag in [t.category] + t.mood_tags))]
            ambient_tracks.sort(key=lambda t: (t.average_rating, t.is_loopable), reverse=True)
            recommendations["ambient_sounds"] = ambient_tracks[:8]
            
            # Get sound effects
            effect_tracks = [t for t in self.audio_tracks.values()
                           if (t.audio_type == AudioType.SOUND_EFFECT.value and
                               any(tag in mapping["effects"] for tag in [t.category] + t.mood_tags))]
            effect_tracks.sort(key=lambda t: t.average_rating, reverse=True)
            recommendations["sound_effects"] = effect_tracks[:15]
        
        # Get pre-made playlists for scenario
        scenario_playlists = [p for p in self.playlists.values()
                            if (p["is_public"] and 
                                p["scenario"] == scenario)]
        scenario_playlists.sort(key=lambda p: p["play_count"], reverse=True)
        recommendations["suggested_playlists"] = scenario_playlists[:5]
        
        return recommendations
    
    def generate_dynamic_playlist(
        self,
        scenario: str,
        duration_minutes: int,
        intensity_progression: List[str] = None,
        exclude_tracks: List[str] = None
    ) -> Dict[str, Any]:
        """Generate dynamic playlist based on scenario and intensity"""
        
        if not intensity_progression:
            intensity_progression = ["low", "medium", "high", "medium", "low"]
        
        exclude_tracks = exclude_tracks or []
        segment_duration = duration_minutes / len(intensity_progression)
        
        playlist_tracks = []
        total_duration = 0
        
        for intensity in intensity_progression:
            # Find suitable tracks for this intensity level
            suitable_tracks = [
                t for t in self.audio_tracks.values()
                if (t.status == ProductStatus.ACTIVE and
                    t.intensity == intensity and
                    scenario in t.scenario_tags and
                    t.id not in exclude_tracks and
                    t.is_loopable)  # Prefer loopable tracks
            ]
            
            if not suitable_tracks:
                # Fallback to any tracks with matching intensity
                suitable_tracks = [
                    t for t in self.audio_tracks.values()
                    if (t.status == ProductStatus.ACTIVE and
                        t.intensity == intensity and
                        t.id not in exclude_tracks)
                ]
            
            # Select best track for this segment
            if suitable_tracks:
                suitable_tracks.sort(key=lambda t: (t.average_rating, t.play_count), reverse=True)
                selected_track = suitable_tracks[0]
                
                playlist_tracks.append({
                    "track": selected_track,
                    "segment_start": total_duration,
                    "segment_intensity": intensity,
                    "expected_duration": segment_duration * 60  # Convert to seconds
                })
                
                total_duration += segment_duration
                exclude_tracks.append(selected_track.id)  # Avoid repeats
        
        return {
            "tracks": playlist_tracks,
            "total_duration_minutes": duration_minutes,
            "scenario": scenario,
            "intensity_progression": intensity_progression,
            "generated_at": datetime.utcnow()
        }
    
    def get_audio_details(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed audio track information"""
        
        if track_id not in self.audio_tracks:
            return None
        
        track = self.audio_tracks[track_id]
        
        return {
            "track": track.dict(),
            "creator_info": self._get_creator_info(track.creator_id),
            "technical_info": self._get_technical_info(track),
            "usage_suggestions": self._get_usage_suggestions(track),
            "similar_tracks": self._get_similar_tracks(track),
            "download_options": self._get_download_options(track),
            "preview_url": f"https://audio.marketplace.com/previews/{track_id}.mp3"
        }
    
    def _get_creator_info(self, creator_id: str) -> Dict[str, Any]:
        """Get audio creator information"""
        
        creator_tracks = [t for t in self.audio_tracks.values() if t.creator_id == creator_id]
        total_plays = sum(t.play_count for t in creator_tracks)
        avg_rating = sum(t.average_rating for t in creator_tracks) / len(creator_tracks) if creator_tracks else 0
        
        return {
            "id": creator_id,
            "name": f"Audio Creator {creator_id[:8]}",
            "specialties": ["epic_orchestral", "medieval_fantasy"],
            "total_tracks": len(creator_tracks),
            "total_plays": total_plays,
            "average_rating": round(avg_rating, 2),
            "verified": True
        }
    
    def _get_technical_info(self, track: AudioTrack) -> Dict[str, Any]:
        """Get technical audio information"""
        
        return {
            "duration": f"{track.duration_seconds // 60}:{track.duration_seconds % 60:02d}",
            "file_formats": track.file_formats,
            "quality_levels": [AudioQuality.STANDARD.value, AudioQuality.HIGH.value],
            "sample_rate": "44.1 kHz",
            "bit_depth": "16-bit",
            "is_loopable": track.is_loopable,
            "tempo_bpm": track.tempo_bpm,
            "key_signature": track.key_signature,
            "file_sizes": {
                "mp3_standard": f"~{track.duration_seconds * 0.125:.1f} MB",
                "mp3_high": f"~{track.duration_seconds * 0.25:.1f} MB",
                "wav": f"~{track.duration_seconds * 1.4:.1f} MB"
            }
        }
    
    def _get_usage_suggestions(self, track: AudioTrack) -> List[str]:
        """Get usage suggestions for track"""
        
        suggestions = []
        
        if track.is_loopable:
            suggestions.append("Perfect for background ambience - loops seamlessly")
        
        if track.audio_type == AudioType.MUSIC.value:
            if track.intensity in ["high", "very_high"]:
                suggestions.append("Great for combat encounters and climactic moments")
            elif track.intensity in ["low", "very_low"]:
                suggestions.append("Ideal for peaceful exploration and social interactions")
        
        if "tavern" in track.scenario_tags:
            suggestions.append("Perfect for inn and tavern scenes")
        
        if "dungeon" in track.scenario_tags:
            suggestions.append("Excellent for underground exploration")
        
        if track.duration_seconds < 60:
            suggestions.append("Short and impactful - great for specific moments")
        elif track.duration_seconds > 300:
            suggestions.append("Extended track - perfect for longer scenes")
        
        return suggestions
    
    def _get_similar_tracks(self, track: AudioTrack) -> List[AudioTrack]:
        """Find similar audio tracks"""
        
        similar = []
        
        for other in self.audio_tracks.values():
            if other.id == track.id or other.status != ProductStatus.ACTIVE:
                continue
            
            similarity_score = 0
            
            # Same audio type
            if other.audio_type == track.audio_type:
                similarity_score += 3
            
            # Same genre/category
            if other.genre == track.genre or other.category == track.category:
                similarity_score += 2
            
            # Common mood tags
            common_moods = set(track.mood_tags) & set(other.mood_tags)
            similarity_score += len(common_moods)
            
            # Common scenario tags
            common_scenarios = set(track.scenario_tags) & set(other.scenario_tags)
            similarity_score += len(common_scenarios) * 2
            
            # Similar intensity
            if other.intensity == track.intensity:
                similarity_score += 1
            
            # Similar duration
            duration_diff = abs(other.duration_seconds - track.duration_seconds)
            if duration_diff < 30:
                similarity_score += 1
            
            if similarity_score >= 3:
                similar.append(other)
        
        similar.sort(key=lambda t: (t.average_rating, t.play_count), reverse=True)
        return similar[:8]
    
    def _get_download_options(self, track: AudioTrack) -> List[Dict[str, Any]]:
        """Get available download options"""
        
        options = []
        
        for file_format in track.file_formats:
            # Standard quality
            options.append({
                "format": file_format.upper(),
                "quality": "Standard (128kbps)" if file_format == "mp3" else "Standard",
                "file_size": f"~{track.duration_seconds * (0.125 if file_format == 'mp3' else 1.4):.1f} MB",
                "compatible_with": "All devices and software"
            })
            
            # High quality option for MP3
            if file_format == "mp3":
                options.append({
                    "format": "MP3",
                    "quality": "High Quality (256kbps)",
                    "file_size": f"~{track.duration_seconds * 0.25:.1f} MB",
                    "compatible_with": "All devices and software"
                })
        
        return options
    
    def get_trending_audio(self, audio_type: Optional[AudioType] = None, days: int = 7) -> List[AudioTrack]:
        """Get trending audio tracks"""
        
        # Calculate trending based on recent play count increase
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        trending_tracks = []
        for track in self.audio_tracks.values():
            if track.status != ProductStatus.ACTIVE:
                continue
            
            if audio_type and track.audio_type != audio_type.value:
                continue
            
            # Simple trending calculation (would be more sophisticated in real implementation)
            trend_score = track.play_count + (track.average_rating * 10)
            
            trending_tracks.append({
                "track": track,
                "trend_score": trend_score
            })
        
        trending_tracks.sort(key=lambda x: x["trend_score"], reverse=True)
        return [item["track"] for item in trending_tracks[:20]]
    
    def get_free_audio(self, audio_type: Optional[AudioType] = None) -> List[AudioTrack]:
        """Get free audio tracks"""
        
        free_tracks = [
            t for t in self.audio_tracks.values()
            if (t.status == ProductStatus.ACTIVE and
                t.price == Decimal("0.00") and
                (not audio_type or t.audio_type == audio_type.value))
        ]
        
        free_tracks.sort(key=lambda t: (t.average_rating, t.play_count), reverse=True)
        return free_tracks[:30]
    
    def track_playback(self, track_id: str, user_id: Optional[str] = None) -> bool:
        """Track audio playback for analytics"""
        
        if track_id not in self.audio_tracks:
            return False
        
        track = self.audio_tracks[track_id]
        track.play_count += 1
        track.last_played = datetime.utcnow()
        
        # Could also track user-specific play history here
        
        return True