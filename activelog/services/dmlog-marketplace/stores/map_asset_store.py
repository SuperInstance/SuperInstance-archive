"""
Map asset marketplace for battle maps, world maps, and tokens
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from decimal import Decimal
from enum import Enum
from ..models.base import MapAsset, Product, ContentType, ProductStatus

class MapType(Enum):
    BATTLE_MAP = "battle_map"
    WORLD_MAP = "world_map"
    CITY_MAP = "city_map"
    DUNGEON_MAP = "dungeon_map"
    REGIONAL_MAP = "regional_map"
    FLOOR_PLAN = "floor_plan"
    OVERWORLD_MAP = "overworld_map"

class MapStyle(Enum):
    REALISTIC = "realistic"
    STYLIZED = "stylized"
    HAND_DRAWN = "hand_drawn"
    ISOMETRIC = "isometric"
    TOP_DOWN = "top_down"
    SIDE_VIEW = "side_view"
    PIXEL_ART = "pixel_art"

class GridType(Enum):
    SQUARE = "square"
    HEX = "hex"
    NO_GRID = "no_grid"

class AssetType(Enum):
    MAP = "map"
    TOKEN = "token"
    TILE_SET = "tile_set"
    PROP = "prop"
    BACKGROUND = "background"

class MapAssetStore:
    """Manages map assets and tokens marketplace"""
    
    def __init__(self):
        self.assets: Dict[str, MapAsset] = {}
        self.collections: Dict[str, Dict[str, Any]] = {}
        self.creators: Dict[str, Dict[str, Any]] = {}
        self.featured_assets: List[str] = []
        
        # Initialize categories and tags
        self._initialize_categories()
    
    def _initialize_categories(self):
        """Initialize asset categories and common tags"""
        
        self.categories = {
            "environments": {
                "dungeon": ["cave", "underground", "stone", "dark", "torchlight"],
                "forest": ["trees", "nature", "outdoor", "wilderness", "green"],
                "city": ["urban", "buildings", "streets", "civilization", "NPCs"],
                "desert": ["sand", "dunes", "hot", "oasis", "ruins"],
                "mountains": ["peaks", "cliffs", "snow", "rocky", "caves"],
                "ocean": ["water", "ships", "islands", "underwater", "coastal"],
                "arctic": ["snow", "ice", "cold", "frozen", "tundra"],
                "swamp": ["marsh", "murky", "vegetation", "dangerous", "fog"],
                "volcanic": ["lava", "fire", "molten", "dangerous", "hot"],
                "planar": ["otherworldly", "magical", "ethereal", "elemental", "cosmic"]
            },
            "structures": {
                "tavern": ["inn", "social", "rest", "food", "gathering"],
                "castle": ["fortress", "noble", "defense", "grand", "royal"],
                "temple": ["religious", "holy", "worship", "divine", "sacred"],
                "shop": ["merchant", "trade", "goods", "commerce", "urban"],
                "house": ["residential", "home", "domestic", "private", "cozy"],
                "tower": ["wizard", "magical", "tall", "observation", "isolated"],
                "bridge": ["crossing", "travel", "connection", "spanning", "architectural"],
                "ruins": ["ancient", "destroyed", "historical", "mysterious", "abandoned"]
            },
            "tokens": {
                "player_characters": ["PC", "hero", "adventurer", "customizable", "various_classes"],
                "NPCs": ["civilian", "merchant", "noble", "guard", "commoner"],
                "monsters": ["beast", "humanoid", "undead", "dragon", "aberration"],
                "objects": ["furniture", "decoration", "interactive", "prop", "environment"],
                "vehicles": ["cart", "ship", "mount", "magical_transport", "siege_engine"]
            }
        }
        
        self.common_tags = [
            "high_resolution", "print_ready", "VTT_ready", "animated", "layered",
            "day_night", "seasonal", "modular", "customizable", "atmospheric"
        ]
    
    def create_asset(
        self,
        creator_id: str,
        title: str,
        description: str,
        asset_type: AssetType,
        map_type: Optional[MapType] = None,
        style: Optional[MapStyle] = None,
        grid_type: Optional[GridType] = None,
        dimensions: Optional[tuple] = None,
        price: Decimal = Decimal("0.00"),
        tags: List[str] = None,
        file_formats: List[str] = None
    ) -> MapAsset:
        """Create new map asset"""
        
        asset = MapAsset(
            creator_id=creator_id,
            title=title,
            description=description,
            content_type=ContentType.MAP_ASSET,
            price=price,
            asset_type=asset_type.value,
            map_type=map_type.value if map_type else None,
            style=style.value if style else None,
            grid_type=grid_type.value if grid_type else None,
            dimensions=dimensions,
            tags=tags or [],
            file_formats=file_formats or ["jpg", "png"]
        )
        
        self.assets[asset.id] = asset
        return asset
    
    def create_collection(
        self,
        creator_id: str,
        name: str,
        description: str,
        theme: str,
        asset_ids: List[str],
        bundle_price: Optional[Decimal] = None
    ) -> str:
        """Create asset collection/bundle"""
        
        # Validate all assets exist and belong to creator
        valid_assets = []
        total_individual_price = Decimal("0.00")
        
        for asset_id in asset_ids:
            if asset_id in self.assets:
                asset = self.assets[asset_id]
                if asset.creator_id == creator_id:
                    valid_assets.append(asset_id)
                    total_individual_price += asset.price
        
        if not valid_assets:
            return ""
        
        # Calculate bundle price (20% discount if not specified)
        if bundle_price is None:
            bundle_price = total_individual_price * Decimal("0.8")
        
        collection_id = f"collection_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{creator_id[:8]}"
        
        collection = {
            "id": collection_id,
            "creator_id": creator_id,
            "name": name,
            "description": description,
            "theme": theme,
            "asset_ids": valid_assets,
            "bundle_price": bundle_price,
            "individual_price": total_individual_price,
            "savings": total_individual_price - bundle_price,
            "created_at": datetime.utcnow(),
            "purchase_count": 0
        }
        
        self.collections[collection_id] = collection
        return collection_id
    
    def search_assets(
        self,
        query: Optional[str] = None,
        asset_type: Optional[AssetType] = None,
        map_type: Optional[MapType] = None,
        style: Optional[MapStyle] = None,
        grid_type: Optional[GridType] = None,
        tags: List[str] = None,
        price_min: Optional[Decimal] = None,
        price_max: Optional[Decimal] = None,
        dimensions_min: Optional[tuple] = None,
        dimensions_max: Optional[tuple] = None,
        creator_id: Optional[str] = None,
        sort_by: str = "relevance"
    ) -> List[MapAsset]:
        """Search map assets with filters"""
        
        results = []
        
        for asset in self.assets.values():
            if asset.status != ProductStatus.ACTIVE:
                continue
            
            # Text search
            if query:
                search_text = f"{asset.title} {asset.description} {' '.join(asset.tags)}".lower()
                if query.lower() not in search_text:
                    continue
            
            # Asset type filter
            if asset_type and asset.asset_type != asset_type.value:
                continue
            
            # Map type filter
            if map_type and asset.map_type != map_type.value:
                continue
            
            # Style filter
            if style and asset.style != style.value:
                continue
            
            # Grid type filter
            if grid_type and asset.grid_type != grid_type.value:
                continue
            
            # Tag filter
            if tags:
                asset_tags = set(asset.tags)
                required_tags = set(tags)
                if not required_tags.issubset(asset_tags):
                    continue
            
            # Price filter
            if price_min and asset.price < price_min:
                continue
            if price_max and asset.price > price_max:
                continue
            
            # Dimensions filter
            if dimensions_min and asset.dimensions:
                if asset.dimensions[0] < dimensions_min[0] or asset.dimensions[1] < dimensions_min[1]:
                    continue
            if dimensions_max and asset.dimensions:
                if asset.dimensions[0] > dimensions_max[0] or asset.dimensions[1] > dimensions_max[1]:
                    continue
            
            # Creator filter
            if creator_id and asset.creator_id != creator_id:
                continue
            
            results.append(asset)
        
        # Sort results
        if sort_by == "price_low":
            results.sort(key=lambda a: a.price)
        elif sort_by == "price_high":
            results.sort(key=lambda a: a.price, reverse=True)
        elif sort_by == "newest":
            results.sort(key=lambda a: a.created_at, reverse=True)
        elif sort_by == "popular":
            results.sort(key=lambda a: (a.download_count, a.average_rating), reverse=True)
        else:  # relevance
            results.sort(key=lambda a: (a.average_rating, a.download_count), reverse=True)
        
        return results
    
    def get_asset_details(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed asset information"""
        
        if asset_id not in self.assets:
            return None
        
        asset = self.assets[asset_id]
        
        return {
            "asset": asset.dict(),
            "creator_info": self._get_creator_info(asset.creator_id),
            "preview_images": self._get_preview_images(asset),
            "technical_specs": self._get_technical_specs(asset),
            "similar_assets": self._get_similar_assets(asset),
            "usage_license": self._get_usage_license(asset),
            "download_options": self._get_download_options(asset)
        }
    
    def _get_creator_info(self, creator_id: str) -> Dict[str, Any]:
        """Get creator information"""
        
        if creator_id in self.creators:
            return self.creators[creator_id]
        
        # Default creator info
        return {
            "id": creator_id,
            "name": f"Map Creator {creator_id[:8]}",
            "rating": Decimal("4.5"),
            "total_assets": len([a for a in self.assets.values() if a.creator_id == creator_id]),
            "verified": True,
            "specialties": ["battle_maps", "tokens"]
        }
    
    def _get_preview_images(self, asset: MapAsset) -> List[str]:
        """Generate preview image URLs"""
        
        base_url = f"https://maps.marketplace.com/previews/{asset.id}"
        
        previews = [
            f"{base_url}/thumb.jpg",
            f"{base_url}/preview.jpg"
        ]
        
        # Add grid/no-grid variants for maps
        if asset.asset_type == AssetType.MAP.value:
            previews.extend([
                f"{base_url}/with_grid.jpg",
                f"{base_url}/without_grid.jpg"
            ])
        
        # Add animation preview if animated
        if "animated" in asset.tags:
            previews.append(f"{base_url}/animation.gif")
        
        return previews
    
    def _get_technical_specs(self, asset: MapAsset) -> Dict[str, Any]:
        """Get technical specifications"""
        
        specs = {
            "file_formats": asset.file_formats,
            "file_count": len(asset.file_formats) * (2 if asset.grid_type != GridType.NO_GRID.value else 1)
        }
        
        if asset.dimensions:
            specs.update({
                "dimensions": f"{asset.dimensions[0]}x{asset.dimensions[1]}",
                "aspect_ratio": round(asset.dimensions[0] / asset.dimensions[1], 2),
                "print_size_inches": f"{asset.dimensions[0]/300:.1f}\"x{asset.dimensions[1]/300:.1f}\" at 300 DPI"
            })
        
        if asset.asset_type == AssetType.MAP.value:
            specs.update({
                "grid_size": "1 inch squares" if asset.grid_type == GridType.SQUARE.value else "1 inch hexes",
                "vtt_ready": "VTT_ready" in asset.tags,
                "print_ready": "print_ready" in asset.tags
            })
        
        return specs
    
    def _get_similar_assets(self, asset: MapAsset) -> List[Dict[str, Any]]:
        """Find similar assets"""
        
        similar = []
        
        for other in self.assets.values():
            if other.id == asset.id or other.status != ProductStatus.ACTIVE:
                continue
            
            similarity_score = 0
            
            # Same type
            if other.asset_type == asset.asset_type:
                similarity_score += 3
            
            # Same map type
            if other.map_type == asset.map_type:
                similarity_score += 2
            
            # Same style
            if other.style == asset.style:
                similarity_score += 2
            
            # Common tags
            common_tags = set(asset.tags) & set(other.tags)
            similarity_score += len(common_tags)
            
            # Same creator
            if other.creator_id == asset.creator_id:
                similarity_score += 1
            
            if similarity_score >= 3:
                similar.append({
                    "asset": other.dict(),
                    "similarity_score": similarity_score,
                    "preview_image": f"https://maps.marketplace.com/previews/{other.id}/thumb.jpg"
                })
        
        similar.sort(key=lambda x: x["similarity_score"], reverse=True)
        return similar[:6]
    
    def _get_usage_license(self, asset: MapAsset) -> Dict[str, Any]:
        """Get usage license information"""
        
        return {
            "type": "Commercial Use",
            "personal_use": True,
            "commercial_use": True,
            "print_allowed": True,
            "vtt_streaming": True,
            "modification_allowed": True,
            "redistribution_allowed": False,
            "credit_required": False
        }
    
    def _get_download_options(self, asset: MapAsset) -> List[Dict[str, Any]]:
        """Get available download options"""
        
        options = []
        
        for file_format in asset.file_formats:
            # Base version
            options.append({
                "name": f"Standard ({file_format.upper()})",
                "format": file_format,
                "grid": asset.grid_type != GridType.NO_GRID.value,
                "size": "Standard Resolution",
                "file_size": "~2-5 MB"
            })
            
            # No grid version for maps
            if asset.asset_type == AssetType.MAP.value and asset.grid_type != GridType.NO_GRID.value:
                options.append({
                    "name": f"No Grid ({file_format.upper()})",
                    "format": file_format,
                    "grid": False,
                    "size": "Standard Resolution",
                    "file_size": "~2-5 MB"
                })
            
            # High resolution version
            if "high_resolution" in asset.tags:
                options.append({
                    "name": f"High Resolution ({file_format.upper()})",
                    "format": file_format,
                    "grid": asset.grid_type != GridType.NO_GRID.value,
                    "size": "High Resolution (4K+)",
                    "file_size": "~10-20 MB"
                })
        
        return options
    
    def get_featured_assets(self, asset_type: Optional[AssetType] = None) -> List[MapAsset]:
        """Get featured assets"""
        
        featured = []
        
        # Get manually featured assets first
        for asset_id in self.featured_assets:
            if asset_id in self.assets:
                asset = self.assets[asset_id]
                if asset.status == ProductStatus.ACTIVE:
                    if not asset_type or asset.asset_type == asset_type.value:
                        featured.append(asset)
        
        # Fill with top-rated if needed
        if len(featured) < 8:
            all_assets = [a for a in self.assets.values() 
                         if (a.status == ProductStatus.ACTIVE and 
                             a.id not in self.featured_assets and
                             (not asset_type or a.asset_type == asset_type.value))]
            
            all_assets.sort(key=lambda a: (a.average_rating, a.download_count), reverse=True)
            featured.extend(all_assets[:8 - len(featured)])
        
        return featured
    
    def get_new_releases(self, days: int = 30, asset_type: Optional[AssetType] = None) -> List[MapAsset]:
        """Get recently released assets"""
        
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        new_assets = [
            a for a in self.assets.values()
            if (a.status == ProductStatus.ACTIVE and 
                a.created_at >= cutoff_date and
                (not asset_type or a.asset_type == asset_type.value))
        ]
        
        new_assets.sort(key=lambda a: a.created_at, reverse=True)
        return new_assets[:20]
    
    def get_bestselling_assets(self, asset_type: Optional[AssetType] = None, period: str = "all_time") -> List[MapAsset]:
        """Get bestselling assets"""
        
        assets = [a for a in self.assets.values() 
                 if (a.status == ProductStatus.ACTIVE and
                     (not asset_type or a.asset_type == asset_type.value))]
        
        # Sort by download count (proxy for sales)
        assets.sort(key=lambda a: a.download_count, reverse=True)
        return assets[:20]
    
    def get_free_assets(self, asset_type: Optional[AssetType] = None) -> List[MapAsset]:
        """Get free assets"""
        
        free_assets = [
            a for a in self.assets.values()
            if (a.status == ProductStatus.ACTIVE and
                a.price == Decimal("0.00") and
                (not asset_type or a.asset_type == asset_type.value))
        ]
        
        free_assets.sort(key=lambda a: (a.average_rating, a.download_count), reverse=True)
        return free_assets[:20]
    
    def get_creator_assets(self, creator_id: str) -> Dict[str, Any]:
        """Get all assets by creator"""
        
        creator_assets = [a for a in self.assets.values() if a.creator_id == creator_id]
        creator_collections = [c for c in self.collections.values() if c["creator_id"] == creator_id]
        
        # Group by asset type
        assets_by_type = {}
        for asset in creator_assets:
            if asset.asset_type not in assets_by_type:
                assets_by_type[asset.asset_type] = []
            assets_by_type[asset.asset_type].append(asset)
        
        # Calculate statistics
        total_downloads = sum(a.download_count for a in creator_assets)
        avg_rating = sum(a.average_rating for a in creator_assets) / len(creator_assets) if creator_assets else 0
        
        return {
            "assets": creator_assets,
            "collections": creator_collections,
            "assets_by_type": assets_by_type,
            "statistics": {
                "total_assets": len(creator_assets),
                "total_downloads": total_downloads,
                "average_rating": round(avg_rating, 2),
                "total_collections": len(creator_collections)
            }
        }
    
    def create_wishlist(self, user_id: str, asset_id: str) -> bool:
        """Add asset to user wishlist"""
        
        if not hasattr(self, 'wishlists'):
            self.wishlists = {}
        
        if user_id not in self.wishlists:
            self.wishlists[user_id] = []
        
        if asset_id not in self.wishlists[user_id] and asset_id in self.assets:
            self.wishlists[user_id].append(asset_id)
            return True
        
        return False
    
    def get_user_wishlist(self, user_id: str) -> List[MapAsset]:
        """Get user's wishlist"""
        
        if not hasattr(self, 'wishlists') or user_id not in self.wishlists:
            return []
        
        wishlist_assets = []
        for asset_id in self.wishlists[user_id]:
            if asset_id in self.assets:
                wishlist_assets.append(self.assets[asset_id])
        
        return wishlist_assets
    
    def get_trending_tags(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get trending tags"""
        
        tag_counts = {}
        
        # Count tag usage in recent assets
        from datetime import timedelta
        recent_cutoff = datetime.utcnow() - timedelta(days=30)
        
        for asset in self.assets.values():
            if asset.created_at >= recent_cutoff and asset.status == ProductStatus.ACTIVE:
                for tag in asset.tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # Sort by count
        trending = [{"tag": tag, "count": count} for tag, count in tag_counts.items()]
        trending.sort(key=lambda x: x["count"], reverse=True)
        
        return trending[:limit]