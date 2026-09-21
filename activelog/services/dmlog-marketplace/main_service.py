"""
DMLog Marketplace - Main Service
A comprehensive D&D content marketplace for adventures, art, audio, and digital assets
"""

import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Store imports
from .stores.adventure_store import AdventureStore
from .stores.art_commission_store import ArtCommissionStore
from .stores.miniature_designer import MiniatureDesigner
from .stores.map_asset_store import MapAssetStore
from .stores.audio_library import AudioLibrary
from .stores.rules_supplement_store import RulesSupplementStore
from .stores.voice_pack_store import VoicePackStore
from .stores.dice_skin_store import DiceSkinStore
from .stores.campaign_setting_store import CampaignSettingStore
from .stores.dm_screen_store import DMScreenStore

# Service imports
from .services.royalty_system import RoyaltySystem
from .services.review_system import ReviewSystem

# Model imports
from .models.base import (
    ContentType, ProductStatus, AdventureModule, ArtCommission, 
    CustomMiniature, MapAsset, AudioTrack, RulesSupplement, 
    VoicePack, DiceSkin, CampaignSetting, DMScreen
)

class MarketplaceService:
    """Main marketplace service orchestrator"""
    
    def __init__(self):
        # Initialize all stores
        self.adventure_store = AdventureStore()
        self.art_commission_store = ArtCommissionStore()
        self.miniature_designer = MiniatureDesigner()
        self.map_asset_store = MapAssetStore()
        self.audio_library = AudioLibrary()
        self.rules_supplement_store = RulesSupplementStore()
        self.voice_pack_store = VoicePackStore()
        self.dice_skin_store = DiceSkinStore()
        self.campaign_setting_store = CampaignSettingStore()
        self.dm_screen_store = DMScreenStore()
        
        # Initialize services
        self.royalty_system = RoyaltySystem()
        self.review_system = ReviewSystem()
        
        # Initialize sample data
        self._initialize_sample_data()
    
    def _initialize_sample_data(self):
        """Initialize with sample marketplace data"""
        
        # Sample adventures
        adventure = self.adventure_store.create_adventure(
            creator_id="creator_001",
            title="The Haunted Lighthouse",
            description="A spooky mystery adventure for levels 3-5",
            price=Decimal("12.99"),
            level_range=(3, 5),
            estimated_duration="4-6 hours",
            category="mystery",
            system="D&D 5e"
        )
        self.adventure_store.publish_adventure(adventure.id)
        
        # Sample art commission
        self.art_commission_store.register_artist(
            artist_id="artist_001",
            name="Fantasy Artist Pro",
            bio="Professional fantasy artist specializing in character portraits",
            specialties=["realistic", "fantasy_realism"],
            base_rate=Decimal("50.00"),
            turnaround_days=7
        )
        
        # Sample miniature design
        miniature = self.miniature_designer.start_design("user_001", "Elven Wizard")
        self.miniature_designer.update_design(miniature, "user_001", {
            "race": "elf",
            "class": "wizard",
            "pose": "casting",
            "weapons": ["staff"],
            "accessories": ["spellbook", "robes"]
        })
        
        # Sample map asset
        map_asset = self.map_asset_store.create_asset(
            creator_id="mapper_001",
            title="Tavern Battle Map",
            description="Detailed tavern interior for combat encounters",
            asset_type=self.map_asset_store.AssetType.MAP,
            map_type=self.map_asset_store.MapType.BATTLE_MAP,
            style=self.map_asset_store.MapStyle.TOP_DOWN,
            dimensions=(4096, 3072),
            price=Decimal("8.99")
        )
        
        # Sample audio track
        audio = self.audio_library.create_audio_track(
            creator_id="composer_001",
            title="Tavern Ambience",
            description="Warm tavern atmosphere with crowd chatter",
            audio_type=self.audio_library.AudioType.AMBIENT,
            duration_seconds=180,
            price=Decimal("3.99"),
            is_loopable=True
        )
        
        # Sample rules supplement
        supplement = self.rules_supplement_store.create_supplement(
            creator_id="homebrew_001",
            title="Elemental Sorcerer Subclass",
            description="Master the raw forces of the elements",
            supplement_type=self.rules_supplement_store.SupplementType.SUBCLASS,
            game_system=self.rules_supplement_store.GameSystem.DND_5E,
            complexity_level=self.rules_supplement_store.ComplexityLevel.INTERMEDIATE,
            price=Decimal("4.99")
        )
        
        # Sample voice pack
        voice_pack = self.voice_pack_store.create_voice_pack(
            creator_id="voice_actor_001",
            title="Gruff Dwarf Voice Pack",
            description="Perfect voice for dwarf NPCs and characters",
            character_archetype="warrior",
            voice_type=self.voice_pack_store.VoiceType.MALE,
            voice_age=self.voice_pack_store.VoiceAge.MIDDLE_AGED,
            accent=self.voice_pack_store.VoiceAccent.FANTASY_DWARVEN,
            personality=self.voice_pack_store.VoicePersonality.GRUFF,
            phrase_categories=["greetings", "combat", "social"],
            phrase_count=150,
            audio_quality=self.voice_pack_store.AudioQuality.HIGH,
            price=Decimal("9.99")
        )
        
        # Sample dice skin
        dice_skin = self.dice_skin_store.create_dice_skin(
            creator_id="dice_designer_001",
            name="Dragon Scale Dice",
            description="Mystical dice with dragon scale texture",
            category=self.dice_skin_store.SkinCategory.FANTASY,
            dice_types=[self.dice_skin_store.DiceType.D20, self.dice_skin_store.DiceType.D6],
            base_material="crystal",
            colors=["red", "gold", "black"],
            price=Decimal("6.99"),
            is_animated=True
        )
        
        # Sample campaign setting
        setting = self.campaign_setting_store.create_campaign_setting(
            creator_id="worldbuilder_001",
            name="The Shattered Realms",
            description="A post-apocalyptic fantasy world of floating islands",
            genre=self.campaign_setting_store.SettingGenre.DARK_FANTASY,
            scale=self.campaign_setting_store.SettingScale.GLOBAL,
            tone_style=self.campaign_setting_store.ToneStyle.GRITTY,
            complexity_level=self.campaign_setting_store.ComplexityLevel.ADVANCED,
            magic_system="dying_magic",
            technology_level="medieval",
            key_themes=["survival", "exploration", "lost_civilization"],
            major_conflicts=["resource_wars", "sky_piracy", "ancient_curses"],
            page_count=120,
            price=Decimal("24.99")
        )
        
        # Sample DM screen
        dm_screen = self.dm_screen_store.create_dm_screen(
            creator_id="screen_designer_001",
            name="5e Essential Rules Screen",
            description="Everything you need for D&D 5e sessions",
            screen_type=self.dm_screen_store.ScreenType.DIGITAL,
            layout=self.dm_screen_store.ScreenLayout.LANDSCAPE,
            game_system=self.dm_screen_store.GameSystem.DND_5E,
            content_categories=[
                self.dm_screen_store.ContentCategory.RULES_REFERENCE,
                self.dm_screen_store.ContentCategory.TABLES,
                self.dm_screen_store.ContentCategory.INITIATIVE_TRACKER
            ],
            visual_theme="classic_fantasy",
            price=Decimal("7.99")
        )
        
        print(f"✅ Marketplace initialized with sample content")
        print(f"   - Adventures: {len(self.adventure_store.adventures)}")
        print(f"   - Artists: {len(self.art_commission_store.artists)}")
        print(f"   - Map Assets: {len(self.map_asset_store.assets)}")
        print(f"   - Audio Tracks: {len(self.audio_library.audio_tracks)}")
        print(f"   - Rules Supplements: {len(self.rules_supplement_store.supplements)}")
        print(f"   - Voice Packs: {len(self.voice_pack_store.voice_packs)}")
        print(f"   - Dice Skins: {len(self.dice_skin_store.dice_skins)}")
        print(f"   - Campaign Settings: {len(self.campaign_setting_store.campaign_settings)}")
        print(f"   - DM Screens: {len(self.dm_screen_store.dm_screens)}")

# FastAPI application
app = FastAPI(
    title="DMLog Marketplace",
    description="Comprehensive D&D Content Marketplace",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8088"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize service
marketplace = MarketplaceService()

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with marketplace overview"""
    return {
        "service": "DMLog Marketplace",
        "version": "1.0.0",
        "description": "Comprehensive D&D Content Marketplace",
        "features": [
            "Adventure modules and campaigns",
            "Character art commissions",
            "Custom miniature designer",
            "Map assets and battle maps",
            "Sound effects and music library",
            "Rules supplements and homebrew",
            "Character voice packs",
            "Virtual dice skins",
            "Campaign settings and worlds",
            "DM screen customization",
            "Automated royalty distribution",
            "Content rating and review system"
        ],
        "endpoints": {
            "adventures": "/adventures/",
            "art_commissions": "/art/",
            "miniatures": "/miniatures/",
            "maps": "/maps/",
            "audio": "/audio/",
            "supplements": "/supplements/",
            "voices": "/voices/",
            "dice": "/dice/",
            "settings": "/settings/",
            "screens": "/screens/",
            "reviews": "/reviews/",
            "royalties": "/royalties/"
        }
    }

# Adventure endpoints
@app.get("/adventures/")
async def list_adventures(
    category: Optional[str] = None,
    level_min: Optional[int] = None,
    level_max: Optional[int] = None,
    limit: int = 20
):
    """List available adventures"""
    adventures = marketplace.adventure_store.search_adventures(
        category=category,
        level_min=level_min,
        level_max=level_max
    )
    return {"adventures": adventures[:limit]}

@app.get("/adventures/{adventure_id}")
async def get_adventure(adventure_id: str):
    """Get adventure details"""
    details = marketplace.adventure_store.get_adventure_details(adventure_id)
    if not details:
        raise HTTPException(status_code=404, detail="Adventure not found")
    return details

@app.get("/adventures/featured")
async def get_featured_adventures():
    """Get featured adventures"""
    featured = marketplace.adventure_store.get_featured_adventures()
    return {"featured_adventures": featured}

# Art commission endpoints
@app.get("/art/artists")
async def list_artists(style: Optional[str] = None, max_price: Optional[float] = None):
    """List available artists"""
    from .stores.art_commission_store import ArtStyle
    
    style_enum = None
    if style:
        try:
            style_enum = ArtStyle(style)
        except ValueError:
            pass
    
    max_price_decimal = Decimal(str(max_price)) if max_price else None
    
    artists = marketplace.art_commission_store.search_artists(
        style=style_enum,
        max_price=max_price_decimal
    )
    return {"artists": artists}

@app.post("/art/commissions")
async def create_commission_request(
    client_id: str,
    title: str,
    description: str,
    art_type: str,
    style: str,
    complexity: str,
    budget_max: Optional[float] = None
):
    """Create art commission request"""
    from .stores.art_commission_store import ArtType, ArtStyle
    
    try:
        art_type_enum = ArtType(art_type)
        style_enum = ArtStyle(style)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid enum value: {e}")
    
    budget_decimal = Decimal(str(budget_max)) if budget_max else None
    
    commission = marketplace.art_commission_store.create_commission_request(
        client_id=client_id,
        title=title,
        description=description,
        art_type=art_type_enum,
        preferred_style=style_enum,
        complexity_level=complexity,
        budget_max=budget_decimal
    )
    
    return {"commission": commission.dict()}

# Map asset endpoints
@app.get("/maps/")
async def list_map_assets(
    asset_type: Optional[str] = None,
    style: Optional[str] = None,
    limit: int = 20
):
    """List map assets"""
    from .stores.map_asset_store import AssetType, MapStyle
    
    asset_type_enum = AssetType(asset_type) if asset_type else None
    style_enum = MapStyle(style) if style else None
    
    assets = marketplace.map_asset_store.search_assets(
        asset_type=asset_type_enum,
        style=style_enum
    )
    return {"map_assets": assets[:limit]}

@app.get("/maps/featured")
async def get_featured_maps():
    """Get featured map assets"""
    featured = marketplace.map_asset_store.get_featured_assets()
    return {"featured_maps": featured}

# Audio library endpoints
@app.get("/audio/")
async def list_audio_tracks(
    audio_type: Optional[str] = None,
    genre: Optional[str] = None,
    mood: Optional[str] = None,
    limit: int = 20
):
    """List audio tracks"""
    from .stores.audio_library import AudioType, MusicGenre
    
    audio_type_enum = AudioType(audio_type) if audio_type else None
    genre_enum = MusicGenre(genre) if genre else None
    mood_tags = [mood] if mood else None
    
    tracks = marketplace.audio_library.search_audio(
        audio_type=audio_type_enum,
        genre=genre_enum,
        mood_tags=mood_tags
    )
    return {"audio_tracks": tracks[:limit]}

@app.get("/audio/recommendations/{scenario}")
async def get_audio_for_scenario(scenario: str, session_length: int = 180):
    """Get audio recommendations for scenario"""
    recommendations = marketplace.audio_library.get_recommendations_for_scenario(
        scenario=scenario,
        session_length_minutes=session_length
    )
    return {"recommendations": recommendations}

# Rules supplement endpoints
@app.get("/supplements/")
async def list_supplements(
    supplement_type: Optional[str] = None,
    game_system: Optional[str] = None,
    playtested_only: bool = False,
    limit: int = 20
):
    """List rules supplements"""
    from .stores.rules_supplement_store import SupplementType, GameSystem
    
    type_enum = SupplementType(supplement_type) if supplement_type else None
    system_enum = GameSystem(game_system) if game_system else None
    
    supplements = marketplace.rules_supplement_store.search_supplements(
        supplement_type=type_enum,
        game_system=system_enum,
        playtested_only=playtested_only
    )
    return {"supplements": supplements[:limit]}

@app.get("/supplements/trending")
async def get_trending_supplements():
    """Get trending supplements"""
    trending = marketplace.rules_supplement_store.get_trending_supplements()
    return {"trending_supplements": trending}

# Voice pack endpoints
@app.get("/voices/")
async def list_voice_packs(
    character_archetype: Optional[str] = None,
    voice_type: Optional[str] = None,
    accent: Optional[str] = None,
    limit: int = 20
):
    """List voice packs"""
    from .stores.voice_pack_store import VoiceType, VoiceAccent
    
    voice_type_enum = VoiceType(voice_type) if voice_type else None
    accent_enum = VoiceAccent(accent) if accent else None
    
    voice_packs = marketplace.voice_pack_store.search_voice_packs(
        character_archetype=character_archetype,
        voice_type=voice_type_enum,
        accent=accent_enum
    )
    return {"voice_packs": voice_packs[:limit]}

@app.get("/voices/recommendations")
async def get_voice_recommendations(
    race: str,
    character_class: str,
    background: str
):
    """Get voice recommendations for character"""
    recommendations = marketplace.voice_pack_store.get_voice_recommendations_for_character(
        character_race=race,
        character_class=character_class,
        character_background=background
    )
    return {"recommendations": recommendations}

# Dice skin endpoints
@app.get("/dice/")
async def list_dice_skins(
    category: Optional[str] = None,
    material: Optional[str] = None,
    is_animated: Optional[bool] = None,
    limit: int = 20
):
    """List dice skins"""
    from .stores.dice_skin_store import SkinCategory
    
    category_enum = SkinCategory(category) if category else None
    
    skins = marketplace.dice_skin_store.search_dice_skins(
        category=category_enum,
        base_material=material,
        is_animated=is_animated
    )
    return {"dice_skins": skins[:limit]}

@app.get("/dice/trending")
async def get_trending_dice():
    """Get trending dice skins"""
    trending = marketplace.dice_skin_store.get_trending_dice_skins()
    return {"trending_dice": trending}

# Campaign setting endpoints
@app.get("/settings/")
async def list_campaign_settings(
    genre: Optional[str] = None,
    scale: Optional[str] = None,
    complexity: Optional[str] = None,
    limit: int = 20
):
    """List campaign settings"""
    from .stores.campaign_setting_store import SettingGenre, SettingScale, ComplexityLevel
    
    genre_enum = SettingGenre(genre) if genre else None
    scale_enum = SettingScale(scale) if scale else None
    complexity_enum = ComplexityLevel(complexity) if complexity else None
    
    settings = marketplace.campaign_setting_store.search_campaign_settings(
        genre=genre_enum,
        scale=scale_enum,
        complexity_level=complexity_enum
    )
    return {"campaign_settings": settings[:limit]}

@app.get("/settings/beginner")
async def get_beginner_settings():
    """Get beginner-friendly settings"""
    beginner = marketplace.campaign_setting_store.get_beginner_friendly_settings()
    return {"beginner_settings": beginner}

# DM screen endpoints
@app.get("/screens/")
async def list_dm_screens(
    screen_type: Optional[str] = None,
    game_system: Optional[str] = None,
    is_customizable: Optional[bool] = None,
    limit: int = 20
):
    """List DM screens"""
    from .stores.dm_screen_store import ScreenType, GameSystem
    
    type_enum = ScreenType(screen_type) if screen_type else None
    system_enum = GameSystem(game_system) if game_system else None
    
    screens = marketplace.dm_screen_store.search_dm_screens(
        screen_type=type_enum,
        game_system=system_enum,
        is_customizable=is_customizable
    )
    return {"dm_screens": screens[:limit]}

@app.get("/screens/interactive")
async def get_interactive_screens():
    """Get interactive DM screens"""
    interactive = marketplace.dm_screen_store.get_interactive_screens()
    return {"interactive_screens": interactive}

# Review system endpoints
@app.get("/reviews/{product_id}")
async def get_product_reviews(
    product_id: str,
    sort_by: str = "helpful",
    filter_rating: Optional[int] = None,
    verified_only: bool = False,
    page: int = 1
):
    """Get reviews for a product"""
    reviews = marketplace.review_system.get_product_reviews(
        product_id=product_id,
        sort_by=sort_by,
        filter_rating=filter_rating,
        verified_only=verified_only,
        page=page
    )
    return reviews

@app.get("/reviews/{product_id}/featured")
async def get_featured_reviews(product_id: str):
    """Get featured reviews for product"""
    featured = marketplace.review_system.get_featured_reviews(product_id)
    return {"featured_reviews": featured}

@app.get("/reviews/{product_id}/stats")
async def get_review_stats(product_id: str):
    """Get review statistics for product"""
    stats = marketplace.review_system.get_review_summary_stats(product_id)
    return {"review_stats": stats}

# Royalty system endpoints
@app.get("/royalties/creator/{creator_id}/summary")
async def get_creator_earnings(creator_id: str, period_days: int = 30):
    """Get creator earnings summary"""
    summary = marketplace.royalty_system.get_creator_earnings_summary(
        creator_id=creator_id,
        period_days=period_days
    )
    return {"earnings_summary": summary}

@app.get("/royalties/creator/{creator_id}/report")
async def get_royalty_report(
    creator_id: str,
    start_date: str,
    end_date: str
):
    """Get detailed royalty report"""
    from datetime import datetime
    
    start_dt = datetime.fromisoformat(start_date)
    end_dt = datetime.fromisoformat(end_date)
    
    report = marketplace.royalty_system.generate_royalty_report(
        creator_id=creator_id,
        start_date=start_dt,
        end_date=end_dt
    )
    return {"royalty_report": report}

# Miniature designer endpoints
@app.post("/miniatures/design")
async def start_miniature_design(user_id: str, name: str):
    """Start new miniature design"""
    design_id = marketplace.miniature_designer.start_design(user_id, name)
    return {"design_id": design_id, "status": "Design started"}

@app.put("/miniatures/{design_id}")
async def update_miniature_design(
    design_id: str,
    user_id: str,
    updates: Dict[str, Any]
):
    """Update miniature design"""
    success = marketplace.miniature_designer.update_design(design_id, user_id, updates)
    if not success:
        raise HTTPException(status_code=404, detail="Design not found or unauthorized")
    return {"status": "Design updated"}

@app.get("/miniatures/{design_id}/preview")
async def get_miniature_preview(design_id: str):
    """Get miniature preview"""
    preview = marketplace.miniature_designer.generate_preview(design_id)
    if not preview:
        raise HTTPException(status_code=404, detail="Design not found")
    return {"preview": preview}

# Dashboard endpoint
@app.get("/dashboard")
async def get_marketplace_dashboard():
    """Get marketplace dashboard with overview statistics"""
    
    dashboard = {
        "marketplace_stats": {
            "total_adventures": len(marketplace.adventure_store.adventures),
            "total_artists": len(marketplace.art_commission_store.artists),
            "total_map_assets": len(marketplace.map_asset_store.assets),
            "total_audio_tracks": len(marketplace.audio_library.audio_tracks),
            "total_supplements": len(marketplace.rules_supplement_store.supplements),
            "total_voice_packs": len(marketplace.voice_pack_store.voice_packs),
            "total_dice_skins": len(marketplace.dice_skin_store.dice_skins),
            "total_campaign_settings": len(marketplace.campaign_setting_store.campaign_settings),
            "total_dm_screens": len(marketplace.dm_screen_store.dm_screens)
        },
        "featured_content": {
            "adventures": marketplace.adventure_store.get_featured_adventures(3),
            "map_assets": marketplace.map_asset_store.get_featured_assets()[:3],
            "voice_packs": marketplace.voice_pack_store.get_featured_voice_packs()[:3],
            "campaign_settings": marketplace.campaign_setting_store.get_trending_settings()[:3]
        },
        "system_status": {
            "marketplace_operational": True,
            "royalty_system_active": True,
            "review_system_active": True,
            "last_updated": datetime.utcnow()
        }
    }
    
    return dashboard

if __name__ == "__main__":
    print("🚀 Starting DMLog Marketplace Service...")
    print("📊 Initializing marketplace stores and services...")
    
    import uvicorn
    uvicorn.run(
        "main_service:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )