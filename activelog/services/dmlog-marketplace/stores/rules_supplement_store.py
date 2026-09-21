"""
Rules supplements and homebrew content store
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from ..models.base import RulesSupplement, Product, ContentType, ProductStatus

class SupplementType(Enum):
    CLASS = "class"
    SUBCLASS = "subclass"
    RACE = "race"
    BACKGROUND = "background"
    FEAT = "feat"
    SPELL = "spell"
    ITEM = "item"
    MONSTER = "monster"
    SETTING = "setting"
    ADVENTURE_HOOK = "adventure_hook"
    RULE_VARIANT = "rule_variant"
    OPTIONAL_RULE = "optional_rule"

class GameSystem(Enum):
    DND_5E = "dnd_5e"
    PATHFINDER_2E = "pathfinder_2e"
    DND_35 = "dnd_35"
    PATHFINDER_1E = "pathfinder_1e"
    GENERIC = "generic"
    OSR = "osr"
    DCC = "dcc"

class ComplexityLevel(Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class RulesSupplementStore:
    """Manages rules supplements and homebrew content"""
    
    def __init__(self):
        self.supplements: Dict[str, RulesSupplement] = {}
        self.supplement_collections: Dict[str, Dict[str, Any]] = {}
        self.compatibility_db: Dict[str, List[str]] = {}  # Tracks compatibility between supplements
        self.balance_ratings: Dict[str, Dict[str, Any]] = {}  # Community balance feedback
        
        # Initialize content categories
        self._initialize_content_categories()
    
    def _initialize_content_categories(self):
        """Initialize supplement categories and themes"""
        
        self.content_themes = {
            "horror": ["dark", "gothic", "psychological", "supernatural", "undead"],
            "high_fantasy": ["magical", "epic", "heroic", "legendary", "mythical"],
            "low_fantasy": ["gritty", "realistic", "survival", "political", "social"],
            "steampunk": ["mechanical", "industrial", "invention", "steam", "clockwork"],
            "pirate": ["nautical", "swashbuckling", "exploration", "treasure", "sea"],
            "oriental": ["eastern", "martial_arts", "honor", "balance", "wisdom"],
            "nordic": ["viking", "cold", "tribal", "nature", "runic"],
            "desert": ["arid", "nomadic", "survival", "ancient", "mystical"],
            "urban": ["city", "crime", "politics", "investigation", "modern"],
            "wilderness": ["nature", "survival", "primal", "beast", "elemental"]
        }
        
        self.power_levels = {
            "tier_1": {"levels": "1-4", "description": "Local heroes"},
            "tier_2": {"levels": "5-10", "description": "Regional champions"},
            "tier_3": {"levels": "11-16", "description": "National legends"},
            "tier_4": {"levels": "17-20", "description": "World shapers"}
        }
        
        self.supplement_tags = [
            "playtested", "balanced", "official_style", "comprehensive",
            "beginner_friendly", "complex_mechanics", "roleplay_heavy",
            "combat_focused", "utility", "niche", "creative", "innovative"
        ]
    
    def create_supplement(
        self,
        creator_id: str,
        title: str,
        description: str,
        supplement_type: SupplementType,
        game_system: GameSystem,
        complexity_level: ComplexityLevel,
        themes: List[str] = None,
        power_level: Optional[str] = None,
        prerequisites: List[str] = None,
        mechanics_summary: str = "",
        price: Decimal = Decimal("0.00"),
        page_count: int = 1,
        has_artwork: bool = False,
        requires_approval: bool = True
    ) -> RulesSupplement:
        """Create new rules supplement"""
        
        supplement = RulesSupplement(
            creator_id=creator_id,
            title=title,
            description=description,
            content_type=ContentType.RULES_SUPPLEMENT,
            price=price,
            supplement_type=supplement_type.value,
            game_system=game_system.value,
            complexity_level=complexity_level.value,
            themes=themes or [],
            power_level=power_level,
            prerequisites=prerequisites or [],
            mechanics_summary=mechanics_summary,
            page_count=page_count,
            has_artwork=has_artwork,
            playtested=False,
            balance_rating=Decimal("0.0"),
            compatibility_notes=""
        )
        
        # Set initial status based on approval requirement
        if requires_approval:
            supplement.status = ProductStatus.PENDING_REVIEW
        else:
            supplement.status = ProductStatus.DRAFT
        
        self.supplements[supplement.id] = supplement
        return supplement
    
    def submit_for_review(self, supplement_id: str, creator_id: str) -> bool:
        """Submit supplement for community review"""
        
        if supplement_id not in self.supplements:
            return False
        
        supplement = self.supplements[supplement_id]
        
        if supplement.creator_id != creator_id:
            return False
        
        if supplement.status != ProductStatus.DRAFT:
            return False
        
        # Validate required content
        if not self._validate_supplement_content(supplement):
            return False
        
        supplement.status = ProductStatus.PENDING_REVIEW
        supplement.submitted_at = datetime.utcnow()
        
        return True
    
    def _validate_supplement_content(self, supplement: RulesSupplement) -> bool:
        """Validate supplement has required content"""
        
        required_fields = ["title", "description", "mechanics_summary"]
        
        for field in required_fields:
            if not getattr(supplement, field, "").strip():
                return False
        
        # Type-specific validations
        if supplement.supplement_type == SupplementType.CLASS.value:
            # Classes need substantial content
            if supplement.page_count < 2:
                return False
        
        elif supplement.supplement_type == SupplementType.SPELL.value:
            # Spells need level and school information
            if "level" not in supplement.mechanics_summary.lower():
                return False
        
        return True
    
    def approve_supplement(self, supplement_id: str, reviewer_id: str, notes: str = "") -> bool:
        """Approve supplement for publication"""
        
        if supplement_id not in self.supplements:
            return False
        
        supplement = self.supplements[supplement_id]
        
        if supplement.status != ProductStatus.PENDING_REVIEW:
            return False
        
        supplement.status = ProductStatus.ACTIVE
        supplement.approved_at = datetime.utcnow()
        supplement.reviewer_id = reviewer_id
        supplement.reviewer_notes = notes
        
        return True
    
    def search_supplements(
        self,
        query: Optional[str] = None,
        supplement_type: Optional[SupplementType] = None,
        game_system: Optional[GameSystem] = None,
        complexity_level: Optional[ComplexityLevel] = None,
        themes: List[str] = None,
        power_level: Optional[str] = None,
        price_min: Optional[Decimal] = None,
        price_max: Optional[Decimal] = None,
        min_balance_rating: Optional[Decimal] = None,
        playtested_only: bool = False,
        creator_id: Optional[str] = None,
        sort_by: str = "relevance"
    ) -> List[RulesSupplement]:
        """Search rules supplements with filters"""
        
        results = []
        
        for supplement in self.supplements.values():
            if supplement.status != ProductStatus.ACTIVE:
                continue
            
            # Text search
            if query:
                search_text = f"{supplement.title} {supplement.description} {supplement.mechanics_summary} {' '.join(supplement.themes)}".lower()
                if query.lower() not in search_text:
                    continue
            
            # Type filter
            if supplement_type and supplement.supplement_type != supplement_type.value:
                continue
            
            # Game system filter
            if game_system and supplement.game_system != game_system.value:
                continue
            
            # Complexity filter
            if complexity_level and supplement.complexity_level != complexity_level.value:
                continue
            
            # Theme filter
            if themes:
                supplement_themes = set(supplement.themes)
                required_themes = set(themes)
                if not required_themes.issubset(supplement_themes):
                    continue
            
            # Power level filter
            if power_level and supplement.power_level != power_level:
                continue
            
            # Price filter
            if price_min and supplement.price < price_min:
                continue
            if price_max and supplement.price > price_max:
                continue
            
            # Balance rating filter
            if min_balance_rating and supplement.balance_rating < min_balance_rating:
                continue
            
            # Playtested filter
            if playtested_only and not supplement.playtested:
                continue
            
            # Creator filter
            if creator_id and supplement.creator_id != creator_id:
                continue
            
            results.append(supplement)
        
        # Sort results
        if sort_by == "price_low":
            results.sort(key=lambda s: s.price)
        elif sort_by == "price_high":
            results.sort(key=lambda s: s.price, reverse=True)
        elif sort_by == "newest":
            results.sort(key=lambda s: s.created_at, reverse=True)
        elif sort_by == "balance_rating":
            results.sort(key=lambda s: s.balance_rating, reverse=True)
        elif sort_by == "popular":
            results.sort(key=lambda s: (s.download_count, s.average_rating), reverse=True)
        else:  # relevance
            results.sort(key=lambda s: (s.average_rating, s.balance_rating), reverse=True)
        
        return results
    
    def get_supplement_details(self, supplement_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed supplement information"""
        
        if supplement_id not in self.supplements:
            return None
        
        supplement = self.supplements[supplement_id]
        
        return {
            "supplement": supplement.dict(),
            "creator_info": self._get_creator_info(supplement.creator_id),
            "balance_feedback": self._get_balance_feedback(supplement_id),
            "compatibility_info": self._get_compatibility_info(supplement_id),
            "similar_supplements": self._get_similar_supplements(supplement),
            "usage_examples": self._get_usage_examples(supplement),
            "community_reviews": self._get_community_reviews(supplement_id)
        }
    
    def _get_creator_info(self, creator_id: str) -> Dict[str, Any]:
        """Get supplement creator information"""
        
        creator_supplements = [s for s in self.supplements.values() if s.creator_id == creator_id]
        approved_supplements = [s for s in creator_supplements if s.status == ProductStatus.ACTIVE]
        
        total_downloads = sum(s.download_count for s in approved_supplements)
        avg_rating = sum(s.average_rating for s in approved_supplements) / len(approved_supplements) if approved_supplements else 0
        avg_balance = sum(s.balance_rating for s in approved_supplements) / len(approved_supplements) if approved_supplements else 0
        
        return {
            "id": creator_id,
            "name": f"Homebrew Creator {creator_id[:8]}",
            "total_supplements": len(approved_supplements),
            "total_downloads": total_downloads,
            "average_rating": round(avg_rating, 2),
            "average_balance_rating": round(avg_balance, 2),
            "specialties": self._get_creator_specialties(creator_id),
            "verified": len(approved_supplements) >= 5
        }
    
    def _get_creator_specialties(self, creator_id: str) -> List[str]:
        """Determine creator's specialties"""
        
        creator_supplements = [s for s in self.supplements.values() 
                             if s.creator_id == creator_id and s.status == ProductStatus.ACTIVE]
        
        type_counts = {}
        for supplement in creator_supplements:
            type_counts[supplement.supplement_type] = type_counts.get(supplement.supplement_type, 0) + 1
        
        # Return top 3 most common types
        sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
        return [type_name for type_name, _ in sorted_types[:3]]
    
    def _get_balance_feedback(self, supplement_id: str) -> Dict[str, Any]:
        """Get community balance feedback"""
        
        if supplement_id not in self.balance_ratings:
            return {
                "overall_balance": Decimal("0.0"),
                "power_level": "Unknown",
                "feedback_count": 0,
                "common_concerns": [],
                "strengths": []
            }
        
        feedback = self.balance_ratings[supplement_id]
        return feedback
    
    def submit_balance_feedback(
        self,
        supplement_id: str,
        user_id: str,
        balance_rating: int,  # 1-10 scale
        power_assessment: str,  # "underpowered", "balanced", "overpowered"
        feedback_text: str,
        playtested: bool = False
    ) -> bool:
        """Submit balance feedback for supplement"""
        
        if supplement_id not in self.supplements:
            return False
        
        if supplement_id not in self.balance_ratings:
            self.balance_ratings[supplement_id] = {
                "overall_balance": Decimal("0.0"),
                "power_level": "Unknown",
                "feedback_count": 0,
                "ratings": [],
                "common_concerns": [],
                "strengths": []
            }
        
        feedback_entry = {
            "user_id": user_id,
            "balance_rating": balance_rating,
            "power_assessment": power_assessment,
            "feedback_text": feedback_text,
            "playtested": playtested,
            "submitted_at": datetime.utcnow()
        }
        
        balance_data = self.balance_ratings[supplement_id]
        balance_data["ratings"].append(feedback_entry)
        balance_data["feedback_count"] += 1
        
        # Recalculate overall balance
        all_ratings = [r["balance_rating"] for r in balance_data["ratings"]]
        balance_data["overall_balance"] = Decimal(sum(all_ratings) / len(all_ratings))
        
        # Update supplement balance rating
        supplement = self.supplements[supplement_id]
        supplement.balance_rating = balance_data["overall_balance"]
        
        # Mark as playtested if any feedback confirms playtesting
        if playtested:
            supplement.playtested = True
        
        return True
    
    def _get_compatibility_info(self, supplement_id: str) -> Dict[str, Any]:
        """Get compatibility information"""
        
        supplement = self.supplements[supplement_id]
        
        compatible_with = self.compatibility_db.get(supplement_id, [])
        potential_conflicts = self._find_potential_conflicts(supplement)
        
        return {
            "compatible_supplements": compatible_with,
            "potential_conflicts": potential_conflicts,
            "system_requirements": supplement.prerequisites,
            "power_level": supplement.power_level,
            "integration_notes": supplement.compatibility_notes
        }
    
    def _find_potential_conflicts(self, supplement: RulesSupplement) -> List[Dict[str, Any]]:
        """Find supplements that might conflict"""
        
        conflicts = []
        
        for other_id, other in self.supplements.items():
            if (other_id != supplement.id and 
                other.status == ProductStatus.ACTIVE and
                other.game_system == supplement.game_system):
                
                # Check for similar mechanics that might conflict
                if (supplement.supplement_type == other.supplement_type and
                    supplement.supplement_type in [SupplementType.RULE_VARIANT.value, SupplementType.OPTIONAL_RULE.value]):
                    
                    conflicts.append({
                        "supplement_id": other_id,
                        "title": other.title,
                        "conflict_type": "similar_mechanics",
                        "severity": "moderate"
                    })
        
        return conflicts[:5]  # Limit to top 5 conflicts
    
    def _get_similar_supplements(self, supplement: RulesSupplement) -> List[RulesSupplement]:
        """Find similar supplements"""
        
        similar = []
        
        for other in self.supplements.values():
            if other.id == supplement.id or other.status != ProductStatus.ACTIVE:
                continue
            
            similarity_score = 0
            
            # Same type
            if other.supplement_type == supplement.supplement_type:
                similarity_score += 3
            
            # Same game system
            if other.game_system == supplement.game_system:
                similarity_score += 2
            
            # Common themes
            common_themes = set(supplement.themes) & set(other.themes)
            similarity_score += len(common_themes)
            
            # Same complexity
            if other.complexity_level == supplement.complexity_level:
                similarity_score += 1
            
            # Same power level
            if other.power_level == supplement.power_level:
                similarity_score += 1
            
            if similarity_score >= 3:
                similar.append(other)
        
        similar.sort(key=lambda s: (s.average_rating, s.balance_rating), reverse=True)
        return similar[:6]
    
    def _get_usage_examples(self, supplement: RulesSupplement) -> List[str]:
        """Generate usage examples"""
        
        examples = []
        
        if supplement.supplement_type == SupplementType.CLASS.value:
            examples = [
                "Create a unique character with distinctive abilities",
                "Add variety to party composition",
                "Explore new roleplay opportunities"
            ]
        elif supplement.supplement_type == SupplementType.SPELL.value:
            examples = [
                "Expand spellcaster options",
                "Create unique magical effects",
                "Enhance campaign themes"
            ]
        elif supplement.supplement_type == SupplementType.MONSTER.value:
            examples = [
                "Challenge experienced players with new threats",
                "Populate specific environments",
                "Create memorable encounters"
            ]
        elif supplement.supplement_type == SupplementType.RULE_VARIANT.value:
            examples = [
                "Customize game mechanics to table preferences",
                "Add realism or complexity as desired",
                "Create unique campaign experiences"
            ]
        
        return examples
    
    def _get_community_reviews(self, supplement_id: str) -> List[Dict[str, Any]]:
        """Get community reviews"""
        
        # Simulate community reviews
        return [
            {
                "reviewer": "DMaster42",
                "rating": 5,
                "balance_rating": 8,
                "review": "Excellent supplement with clear mechanics and great flavor!",
                "playtested": True,
                "helpful_votes": 15,
                "date": "2024-01-20"
            },
            {
                "reviewer": "HomebrewFan",
                "rating": 4,
                "balance_rating": 7,
                "review": "Good concept but needs minor balance adjustments.",
                "playtested": True,
                "helpful_votes": 8,
                "date": "2024-01-18"
            }
        ]
    
    def create_supplement_collection(
        self,
        creator_id: str,
        name: str,
        description: str,
        theme: str,
        supplement_ids: List[str],
        bundle_price: Optional[Decimal] = None
    ) -> str:
        """Create supplement collection/compendium"""
        
        # Validate supplements
        valid_supplements = []
        total_individual_price = Decimal("0.00")
        
        for supplement_id in supplement_ids:
            if supplement_id in self.supplements:
                supplement = self.supplements[supplement_id]
                if (supplement.creator_id == creator_id and 
                    supplement.status == ProductStatus.ACTIVE):
                    valid_supplements.append(supplement_id)
                    total_individual_price += supplement.price
        
        if not valid_supplements:
            return ""
        
        # Calculate bundle price (25% discount if not specified)
        if bundle_price is None:
            bundle_price = total_individual_price * Decimal("0.75")
        
        collection_id = f"collection_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{creator_id[:8]}"
        
        collection = {
            "id": collection_id,
            "creator_id": creator_id,
            "name": name,
            "description": description,
            "theme": theme,
            "supplement_ids": valid_supplements,
            "bundle_price": bundle_price,
            "individual_price": total_individual_price,
            "savings": total_individual_price - bundle_price,
            "total_pages": sum(self.supplements[sid].page_count for sid in valid_supplements),
            "created_at": datetime.utcnow(),
            "download_count": 0
        }
        
        self.supplement_collections[collection_id] = collection
        return collection_id
    
    def get_trending_supplements(self, supplement_type: Optional[SupplementType] = None, days: int = 7) -> List[RulesSupplement]:
        """Get trending supplements"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        trending = []
        for supplement in self.supplements.values():
            if supplement.status != ProductStatus.ACTIVE:
                continue
            
            if supplement_type and supplement.supplement_type != supplement_type.value:
                continue
            
            # Calculate trend score
            recent_downloads = supplement.download_count  # Simplified
            trend_score = recent_downloads + (float(supplement.average_rating) * 2) + (float(supplement.balance_rating) * 1)
            
            trending.append({
                "supplement": supplement,
                "trend_score": trend_score
            })
        
        trending.sort(key=lambda x: x["trend_score"], reverse=True)
        return [item["supplement"] for item in trending[:20]]
    
    def get_top_rated_supplements(self, supplement_type: Optional[SupplementType] = None) -> List[RulesSupplement]:
        """Get highest rated supplements"""
        
        top_rated = [
            s for s in self.supplements.values()
            if (s.status == ProductStatus.ACTIVE and
                (not supplement_type or s.supplement_type == supplement_type.value))
        ]
        
        top_rated.sort(key=lambda s: (s.average_rating, s.balance_rating, s.download_count), reverse=True)
        return top_rated[:20]
    
    def get_playtested_supplements(self, supplement_type: Optional[SupplementType] = None) -> List[RulesSupplement]:
        """Get community playtested supplements"""
        
        playtested = [
            s for s in self.supplements.values()
            if (s.status == ProductStatus.ACTIVE and
                s.playtested and
                (not supplement_type or s.supplement_type == supplement_type.value))
        ]
        
        playtested.sort(key=lambda s: (s.balance_rating, s.average_rating), reverse=True)
        return playtested[:20]