"""
Adventure module store management
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from decimal import Decimal
from ..models.base import AdventureModule, Product, ContentType, ProductStatus, Order

class AdventureStore:
    """Manages adventure module marketplace"""
    
    def __init__(self):
        self.adventures: Dict[str, AdventureModule] = {}
        self.featured_adventures: List[str] = []
        self.categories = {
            "dungeon_crawl": "Dungeon Crawl",
            "social_intrigue": "Social Intrigue", 
            "exploration": "Exploration",
            "mystery": "Mystery",
            "horror": "Horror",
            "political": "Political",
            "heist": "Heist",
            "survival": "Survival",
            "urban": "Urban Adventure",
            "wilderness": "Wilderness",
            "planar": "Planar Adventure",
            "one_shot": "One-Shot"
        }
    
    def create_adventure(
        self,
        creator_id: str,
        title: str,
        description: str,
        price: Decimal,
        level_range: tuple,
        estimated_duration: str,
        category: str,
        system: str = "D&D 5e",
        content_files: Optional[List[Dict[str, Any]]] = None
    ) -> AdventureModule:
        """Create new adventure module"""
        
        if category not in self.categories:
            raise ValueError(f"Invalid category: {category}")
        
        adventure = AdventureModule(
            creator_id=creator_id,
            title=title,
            description=description,
            content_type=ContentType.ADVENTURE,
            price=price,
            level_range=level_range,
            estimated_duration=estimated_duration,
            category=category,
            game_system=system,
            content_files=content_files or []
        )
        
        self.adventures[adventure.id] = adventure
        return adventure
    
    def publish_adventure(self, adventure_id: str) -> bool:
        """Publish adventure to marketplace"""
        
        if adventure_id not in self.adventures:
            return False
        
        adventure = self.adventures[adventure_id]
        
        # Validate required content
        if not self._validate_adventure_content(adventure):
            return False
        
        adventure.status = ProductStatus.ACTIVE
        adventure.published_at = datetime.utcnow()
        return True
    
    def _validate_adventure_content(self, adventure: AdventureModule) -> bool:
        """Validate adventure has required content"""
        
        required_files = ["adventure_text", "maps"]
        
        if not adventure.content_files:
            return False
        
        file_types = [f.get("type") for f in adventure.content_files]
        
        for required in required_files:
            if required not in file_types:
                return False
        
        return True
    
    def search_adventures(
        self,
        query: Optional[str] = None,
        level_min: Optional[int] = None,
        level_max: Optional[int] = None,
        category: Optional[str] = None,
        system: Optional[str] = None,
        price_min: Optional[Decimal] = None,
        price_max: Optional[Decimal] = None,
        duration: Optional[str] = None
    ) -> List[AdventureModule]:
        """Search adventures with filters"""
        
        results = []
        
        for adventure in self.adventures.values():
            if adventure.status != ProductStatus.ACTIVE:
                continue
            
            # Text search
            if query:
                search_text = f"{adventure.title} {adventure.description}".lower()
                if query.lower() not in search_text:
                    continue
            
            # Level range filter
            if level_min is not None or level_max is not None:
                adv_min, adv_max = adventure.level_range
                if level_min is not None and adv_max < level_min:
                    continue
                if level_max is not None and adv_min > level_max:
                    continue
            
            # Category filter
            if category and adventure.category != category:
                continue
            
            # System filter
            if system and adventure.game_system != system:
                continue
            
            # Price filter
            if price_min is not None and adventure.price < price_min:
                continue
            if price_max is not None and adventure.price > price_max:
                continue
            
            # Duration filter
            if duration and adventure.estimated_duration != duration:
                continue
            
            results.append(adventure)
        
        # Sort by rating, then by sales
        results.sort(key=lambda a: (a.average_rating, a.total_sales), reverse=True)
        return results
    
    def get_adventure_details(self, adventure_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed adventure information"""
        
        if adventure_id not in self.adventures:
            return None
        
        adventure = self.adventures[adventure_id]
        
        return {
            "adventure": adventure.dict(),
            "creator_info": self._get_creator_info(adventure.creator_id),
            "content_preview": self._get_content_preview(adventure),
            "similar_adventures": self._get_similar_adventures(adventure),
            "reviews": self._get_adventure_reviews(adventure_id)
        }
    
    def _get_creator_info(self, creator_id: str) -> Dict[str, Any]:
        """Get creator information"""
        # Would integrate with user system
        return {
            "id": creator_id,
            "name": "Adventure Creator",
            "rating": 4.5,
            "total_adventures": 12,
            "verified": True
        }
    
    def _get_content_preview(self, adventure: AdventureModule) -> Dict[str, Any]:
        """Generate content preview"""
        
        preview = {
            "synopsis": adventure.description[:200] + "...",
            "key_locations": [],
            "major_npcs": [],
            "treasure_highlights": [],
            "unique_features": []
        }
        
        # Extract preview from content files
        for file_info in adventure.content_files:
            if file_info.get("type") == "adventure_text":
                # Would parse actual content for preview
                preview["key_locations"] = ["Ancient Temple", "Goblin Warren", "Crystal Caverns"]
                preview["major_npcs"] = ["Sage Aldric", "Bandit Captain Vex", "Dragon Wyrmling Zyx"]
                preview["treasure_highlights"] = ["Magic Sword +1", "Bag of Holding", "1,200 GP"]
        
        return preview
    
    def _get_similar_adventures(self, adventure: AdventureModule) -> List[Dict[str, Any]]:
        """Find similar adventures"""
        
        similar = []
        
        for other in self.adventures.values():
            if other.id == adventure.id or other.status != ProductStatus.ACTIVE:
                continue
            
            # Calculate similarity score
            score = 0
            
            # Same category
            if other.category == adventure.category:
                score += 3
            
            # Overlapping level range
            other_min, other_max = other.level_range
            adv_min, adv_max = adventure.level_range
            
            if not (other_max < adv_min or other_min > adv_max):
                score += 2
            
            # Same system
            if other.game_system == adventure.game_system:
                score += 1
            
            # Similar duration
            if other.estimated_duration == adventure.estimated_duration:
                score += 1
            
            if score >= 3:
                similar.append({
                    "id": other.id,
                    "title": other.title,
                    "price": other.price,
                    "rating": other.average_rating,
                    "level_range": other.level_range,
                    "similarity_score": score
                })
        
        # Sort by similarity score
        similar.sort(key=lambda x: x["similarity_score"], reverse=True)
        return similar[:5]
    
    def _get_adventure_reviews(self, adventure_id: str) -> List[Dict[str, Any]]:
        """Get adventure reviews"""
        # Would integrate with review system
        return [
            {
                "reviewer": "DMaster42",
                "rating": 5,
                "comment": "Excellent adventure with great maps and memorable NPCs!",
                "helpful_votes": 12,
                "date": "2024-01-15"
            },
            {
                "reviewer": "TabletopFan",
                "rating": 4,
                "comment": "Good story but could use more combat encounters.",
                "helpful_votes": 8,
                "date": "2024-01-10"
            }
        ]
    
    def get_featured_adventures(self, limit: int = 6) -> List[AdventureModule]:
        """Get featured adventures"""
        
        featured = []
        
        for adventure_id in self.featured_adventures[:limit]:
            if adventure_id in self.adventures:
                adventure = self.adventures[adventure_id]
                if adventure.status == ProductStatus.ACTIVE:
                    featured.append(adventure)
        
        # Fill with top-rated if needed
        if len(featured) < limit:
            all_active = [a for a in self.adventures.values() 
                         if a.status == ProductStatus.ACTIVE and a.id not in self.featured_adventures]
            all_active.sort(key=lambda a: (a.average_rating, a.total_sales), reverse=True)
            
            remaining = limit - len(featured)
            featured.extend(all_active[:remaining])
        
        return featured
    
    def set_featured_adventures(self, adventure_ids: List[str]):
        """Set featured adventures"""
        
        # Validate all IDs exist and are active
        valid_ids = []
        for adventure_id in adventure_ids:
            if (adventure_id in self.adventures and 
                self.adventures[adventure_id].status == ProductStatus.ACTIVE):
                valid_ids.append(adventure_id)
        
        self.featured_adventures = valid_ids
    
    def get_adventure_analytics(self, adventure_id: str, creator_id: str) -> Optional[Dict[str, Any]]:
        """Get adventure performance analytics"""
        
        if adventure_id not in self.adventures:
            return None
        
        adventure = self.adventures[adventure_id]
        
        # Verify creator access
        if adventure.creator_id != creator_id:
            return None
        
        # Calculate analytics
        analytics = {
            "total_views": adventure.view_count,
            "total_sales": adventure.total_sales,
            "revenue": adventure.total_sales * adventure.price,
            "average_rating": adventure.average_rating,
            "rating_breakdown": {
                "5_star": 45,
                "4_star": 30,
                "3_star": 15,
                "2_star": 7,
                "1_star": 3
            },
            "conversion_rate": (adventure.total_sales / max(adventure.view_count, 1)) * 100,
            "recent_activity": {
                "last_7_days": {"views": 120, "sales": 8},
                "last_30_days": {"views": 450, "sales": 25}
            },
            "top_search_terms": ["dungeon", "level 3", "goblins", "magic items"],
            "competitor_comparison": {
                "your_price": adventure.price,
                "avg_category_price": Decimal("15.99"),
                "your_rating": adventure.average_rating,
                "avg_category_rating": 4.2
            }
        }
        
        return analytics
    
    def update_adventure_metrics(self, adventure_id: str, metric: str, value: Any):
        """Update adventure metrics"""
        
        if adventure_id not in self.adventures:
            return False
        
        adventure = self.adventures[adventure_id]
        
        if metric == "view":
            adventure.view_count += 1
        elif metric == "sale":
            adventure.total_sales += 1
        elif metric == "rating":
            # Would integrate with review system to update rating
            pass
        
        return True
    
    def get_creator_adventures(self, creator_id: str) -> List[AdventureModule]:
        """Get all adventures by creator"""
        
        creator_adventures = [
            adventure for adventure in self.adventures.values()
            if adventure.creator_id == creator_id
        ]
        
        # Sort by creation date, newest first
        creator_adventures.sort(key=lambda a: a.created_at, reverse=True)
        return creator_adventures
    
    def get_bestselling_adventures(self, category: Optional[str] = None, limit: int = 10) -> List[AdventureModule]:
        """Get bestselling adventures"""
        
        adventures = [a for a in self.adventures.values() if a.status == ProductStatus.ACTIVE]
        
        if category:
            adventures = [a for a in adventures if a.category == category]
        
        adventures.sort(key=lambda a: a.total_sales, reverse=True)
        return adventures[:limit]
    
    def get_new_releases(self, days: int = 30, limit: int = 10) -> List[AdventureModule]:
        """Get recently published adventures"""
        
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        new_adventures = [
            a for a in self.adventures.values()
            if (a.status == ProductStatus.ACTIVE and 
                a.published_at and a.published_at >= cutoff_date)
        ]
        
        new_adventures.sort(key=lambda a: a.published_at, reverse=True)
        return new_adventures[:limit]