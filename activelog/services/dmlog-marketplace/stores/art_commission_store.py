"""
Character art commission system
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from ..models.base import ArtCommission, Product, ContentType, CommissionStatus

class ArtStyle(Enum):
    REALISTIC = "realistic"
    CARTOON = "cartoon"
    ANIME = "anime"
    FANTASY_REALISM = "fantasy_realism"
    SKETCH = "sketch"
    DIGITAL_PAINTING = "digital_painting"
    WATERCOLOR = "watercolor"
    INK = "ink"
    PIXEL_ART = "pixel_art"

class ArtType(Enum):
    CHARACTER_PORTRAIT = "character_portrait"
    FULL_BODY = "full_body"
    CHARACTER_SHEET = "character_sheet"
    PARTY_GROUP = "party_group"
    SCENE_ILLUSTRATION = "scene_illustration"
    ITEM_DESIGN = "item_design"
    CREATURE_DESIGN = "creature_design"

class ArtCommissionStore:
    """Manages character art commission marketplace"""
    
    def __init__(self):
        self.commissions: Dict[str, ArtCommission] = {}
        self.artists: Dict[str, Dict[str, Any]] = {}
        self.portfolio_items: Dict[str, List[Dict[str, Any]]] = {}
        
        # Base pricing by type and complexity
        self.base_prices = {
            ArtType.CHARACTER_PORTRAIT: {
                "sketch": Decimal("25.00"),
                "full_color": Decimal("50.00"),
                "detailed": Decimal("75.00")
            },
            ArtType.FULL_BODY: {
                "sketch": Decimal("40.00"),
                "full_color": Decimal("80.00"),
                "detailed": Decimal("120.00")
            },
            ArtType.CHARACTER_SHEET: {
                "sketch": Decimal("60.00"),
                "full_color": Decimal("120.00"),
                "detailed": Decimal("180.00")
            },
            ArtType.PARTY_GROUP: {
                "sketch": Decimal("80.00"),
                "full_color": Decimal("160.00"),
                "detailed": Decimal("240.00")
            },
            ArtType.SCENE_ILLUSTRATION: {
                "sketch": Decimal("100.00"),
                "full_color": Decimal("200.00"),
                "detailed": Decimal("300.00")
            }
        }
    
    def register_artist(
        self,
        artist_id: str,
        name: str,
        bio: str,
        specialties: List[ArtStyle],
        base_rate: Decimal,
        turnaround_days: int,
        portfolio_links: List[str] = None
    ) -> Dict[str, Any]:
        """Register new artist"""
        
        artist_profile = {
            "id": artist_id,
            "name": name,
            "bio": bio,
            "specialties": [style.value for style in specialties],
            "base_rate": base_rate,
            "turnaround_days": turnaround_days,
            "portfolio_links": portfolio_links or [],
            "rating": Decimal("0.0"),
            "total_commissions": 0,
            "completed_commissions": 0,
            "is_verified": False,
            "is_accepting": True,
            "created_at": datetime.utcnow(),
            "last_active": datetime.utcnow()
        }
        
        self.artists[artist_id] = artist_profile
        self.portfolio_items[artist_id] = []
        
        return artist_profile
    
    def add_portfolio_item(
        self,
        artist_id: str,
        title: str,
        description: str,
        image_url: str,
        art_type: ArtType,
        art_style: ArtStyle,
        tags: List[str] = None
    ) -> bool:
        """Add item to artist portfolio"""
        
        if artist_id not in self.artists:
            return False
        
        portfolio_item = {
            "id": f"portfolio_{len(self.portfolio_items[artist_id])}",
            "title": title,
            "description": description,
            "image_url": image_url,
            "art_type": art_type.value,
            "art_style": art_style.value,
            "tags": tags or [],
            "likes": 0,
            "created_at": datetime.utcnow()
        }
        
        self.portfolio_items[artist_id].append(portfolio_item)
        return True
    
    def create_commission_request(
        self,
        client_id: str,
        title: str,
        description: str,
        art_type: ArtType,
        preferred_style: ArtStyle,
        complexity_level: str,
        reference_images: List[str] = None,
        deadline: Optional[datetime] = None,
        budget_max: Optional[Decimal] = None,
        character_details: Optional[Dict[str, Any]] = None
    ) -> ArtCommission:
        """Create new commission request"""
        
        # Calculate estimated price
        base_price = self.base_prices.get(art_type, {}).get(complexity_level, Decimal("50.00"))
        
        commission = ArtCommission(
            client_id=client_id,
            title=title,
            description=description,
            content_type=ContentType.CHARACTER_ART,
            price=base_price,
            art_type=art_type.value,
            style=preferred_style.value,
            complexity_level=complexity_level,
            reference_images=reference_images or [],
            deadline=deadline,
            budget_max=budget_max or base_price * Decimal("1.5"),
            character_details=character_details or {}
        )
        
        self.commissions[commission.id] = commission
        return commission
    
    def find_matching_artists(
        self,
        commission_id: str,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Find artists suitable for commission"""
        
        if commission_id not in self.commissions:
            return []
        
        commission = self.commissions[commission_id]
        matching_artists = []
        
        for artist_id, artist in self.artists.items():
            if not artist["is_accepting"]:
                continue
            
            score = 0
            
            # Style match
            if commission.style in artist["specialties"]:
                score += 5
            
            # Budget compatibility
            if artist["base_rate"] <= commission.budget_max:
                score += 3
            
            # Turnaround time
            if commission.deadline:
                days_available = (commission.deadline - datetime.utcnow()).days
                if artist["turnaround_days"] <= days_available:
                    score += 2
            
            # Portfolio relevance
            portfolio_score = self._calculate_portfolio_relevance(
                artist_id, commission.art_type, commission.style
            )
            score += portfolio_score
            
            # Artist rating
            score += float(artist["rating"])
            
            if score > 0:
                matching_artists.append({
                    "artist": artist,
                    "match_score": score,
                    "estimated_price": self._estimate_commission_price(artist_id, commission),
                    "estimated_completion": self._estimate_completion_date(artist_id, commission)
                })
        
        # Sort by match score
        matching_artists.sort(key=lambda x: x["match_score"], reverse=True)
        return matching_artists[:max_results]
    
    def _calculate_portfolio_relevance(
        self,
        artist_id: str,
        art_type: str,
        style: str
    ) -> int:
        """Calculate how relevant artist's portfolio is"""
        
        if artist_id not in self.portfolio_items:
            return 0
        
        portfolio = self.portfolio_items[artist_id]
        relevance_score = 0
        
        for item in portfolio:
            if item["art_type"] == art_type:
                relevance_score += 2
            if item["art_style"] == style:
                relevance_score += 2
            
            # Bonus for popular items
            if item["likes"] > 10:
                relevance_score += 1
        
        return min(relevance_score, 5)  # Cap at 5 points
    
    def _estimate_commission_price(
        self,
        artist_id: str,
        commission: ArtCommission
    ) -> Decimal:
        """Estimate price for specific artist"""
        
        if artist_id not in self.artists:
            return commission.price
        
        artist = self.artists[artist_id]
        base_price = commission.price
        
        # Artist rate multiplier
        rate_multiplier = artist["base_rate"] / Decimal("50.00")  # Normalize to $50 base
        
        # Experience bonus
        experience_multiplier = Decimal("1.0")
        if artist["completed_commissions"] > 50:
            experience_multiplier = Decimal("1.2")
        elif artist["completed_commissions"] > 20:
            experience_multiplier = Decimal("1.1")
        
        # Rating bonus
        rating_multiplier = Decimal("1.0")
        if artist["rating"] > Decimal("4.5"):
            rating_multiplier = Decimal("1.15")
        elif artist["rating"] > Decimal("4.0"):
            rating_multiplier = Decimal("1.05")
        
        estimated_price = base_price * rate_multiplier * experience_multiplier * rating_multiplier
        return estimated_price.quantize(Decimal('0.01'))
    
    def _estimate_completion_date(
        self,
        artist_id: str,
        commission: ArtCommission
    ) -> datetime:
        """Estimate completion date"""
        
        if artist_id not in self.artists:
            return datetime.utcnow() + timedelta(days=14)
        
        artist = self.artists[artist_id]
        base_days = artist["turnaround_days"]
        
        # Check artist's current workload
        active_commissions = [
            c for c in self.commissions.values()
            if c.artist_id == artist_id and c.status in [CommissionStatus.ACCEPTED, CommissionStatus.IN_PROGRESS]
        ]
        
        # Add buffer for existing work
        workload_buffer = len(active_commissions) * 2
        total_days = base_days + workload_buffer
        
        return datetime.utcnow() + timedelta(days=total_days)
    
    def submit_artist_proposal(
        self,
        commission_id: str,
        artist_id: str,
        proposed_price: Decimal,
        estimated_completion: datetime,
        proposal_message: str,
        concept_sketch: Optional[str] = None
    ) -> bool:
        """Artist submits proposal for commission"""
        
        if commission_id not in self.commissions:
            return False
        
        if artist_id not in self.artists:
            return False
        
        commission = self.commissions[commission_id]
        
        if commission.status != CommissionStatus.OPEN:
            return False
        
        # Check if artist already submitted proposal
        existing_proposals = [p for p in commission.proposals if p["artist_id"] == artist_id]
        if existing_proposals:
            return False
        
        proposal = {
            "artist_id": artist_id,
            "artist_name": self.artists[artist_id]["name"],
            "proposed_price": proposed_price,
            "estimated_completion": estimated_completion,
            "message": proposal_message,
            "concept_sketch": concept_sketch,
            "submitted_at": datetime.utcnow()
        }
        
        commission.proposals.append(proposal)
        return True
    
    def accept_proposal(
        self,
        commission_id: str,
        client_id: str,
        proposal_index: int
    ) -> bool:
        """Client accepts artist proposal"""
        
        if commission_id not in self.commissions:
            return False
        
        commission = self.commissions[commission_id]
        
        # Verify client ownership
        if commission.client_id != client_id:
            return False
        
        if commission.status != CommissionStatus.OPEN:
            return False
        
        if proposal_index >= len(commission.proposals):
            return False
        
        accepted_proposal = commission.proposals[proposal_index]
        
        # Update commission
        commission.status = CommissionStatus.ACCEPTED
        commission.artist_id = accepted_proposal["artist_id"]
        commission.price = accepted_proposal["proposed_price"]
        commission.estimated_completion = accepted_proposal["estimated_completion"]
        commission.accepted_at = datetime.utcnow()
        
        # Update artist stats
        artist_id = accepted_proposal["artist_id"]
        self.artists[artist_id]["total_commissions"] += 1
        
        return True
    
    def start_commission(self, commission_id: str, artist_id: str) -> bool:
        """Artist starts working on commission"""
        
        if commission_id not in self.commissions:
            return False
        
        commission = self.commissions[commission_id]
        
        if commission.artist_id != artist_id:
            return False
        
        if commission.status != CommissionStatus.ACCEPTED:
            return False
        
        commission.status = CommissionStatus.IN_PROGRESS
        commission.started_at = datetime.utcnow()
        return True
    
    def submit_work_in_progress(
        self,
        commission_id: str,
        artist_id: str,
        wip_image_url: str,
        progress_notes: str,
        completion_percentage: int
    ) -> bool:
        """Artist submits work in progress"""
        
        if commission_id not in self.commissions:
            return False
        
        commission = self.commissions[commission_id]
        
        if commission.artist_id != artist_id:
            return False
        
        if commission.status != CommissionStatus.IN_PROGRESS:
            return False
        
        wip_update = {
            "image_url": wip_image_url,
            "notes": progress_notes,
            "completion_percentage": completion_percentage,
            "submitted_at": datetime.utcnow()
        }
        
        commission.wip_updates.append(wip_update)
        return True
    
    def submit_final_artwork(
        self,
        commission_id: str,
        artist_id: str,
        final_image_url: str,
        high_res_url: str,
        completion_notes: str
    ) -> bool:
        """Artist submits final artwork"""
        
        if commission_id not in self.commissions:
            return False
        
        commission = self.commissions[commission_id]
        
        if commission.artist_id != artist_id:
            return False
        
        if commission.status != CommissionStatus.IN_PROGRESS:
            return False
        
        commission.final_artwork_url = final_image_url
        commission.high_res_url = high_res_url
        commission.completion_notes = completion_notes
        commission.status = CommissionStatus.PENDING_REVIEW
        commission.completed_at = datetime.utcnow()
        
        return True
    
    def approve_final_artwork(
        self,
        commission_id: str,
        client_id: str,
        rating: int,
        review: str
    ) -> bool:
        """Client approves final artwork"""
        
        if commission_id not in self.commissions:
            return False
        
        commission = self.commissions[commission_id]
        
        if commission.client_id != client_id:
            return False
        
        if commission.status != CommissionStatus.PENDING_REVIEW:
            return False
        
        commission.status = CommissionStatus.COMPLETED
        commission.client_rating = rating
        commission.client_review = review
        commission.approved_at = datetime.utcnow()
        
        # Update artist stats
        if commission.artist_id:
            artist = self.artists[commission.artist_id]
            artist["completed_commissions"] += 1
            
            # Update rating (simple average)
            current_rating = artist["rating"]
            total_completed = artist["completed_commissions"]
            new_rating = ((current_rating * (total_completed - 1)) + Decimal(rating)) / total_completed
            artist["rating"] = new_rating.quantize(Decimal('0.1'))
        
        return True
    
    def search_artists(
        self,
        style: Optional[ArtStyle] = None,
        art_type: Optional[ArtType] = None,
        max_price: Optional[Decimal] = None,
        min_rating: Optional[Decimal] = None,
        available_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Search available artists"""
        
        results = []
        
        for artist_id, artist in self.artists.items():
            if available_only and not artist["is_accepting"]:
                continue
            
            # Style filter
            if style and style.value not in artist["specialties"]:
                continue
            
            # Price filter
            if max_price and artist["base_rate"] > max_price:
                continue
            
            # Rating filter
            if min_rating and artist["rating"] < min_rating:
                continue
            
            # Add portfolio samples
            portfolio = self.portfolio_items.get(artist_id, [])
            
            # Filter portfolio by art type if specified
            if art_type:
                portfolio = [item for item in portfolio if item["art_type"] == art_type.value]
            
            results.append({
                "artist": artist,
                "portfolio_samples": portfolio[:6],  # Show top 6 samples
                "current_workload": len([
                    c for c in self.commissions.values()
                    if c.artist_id == artist_id and c.status in [CommissionStatus.ACCEPTED, CommissionStatus.IN_PROGRESS]
                ])
            })
        
        # Sort by rating, then by completed commissions
        results.sort(key=lambda x: (x["artist"]["rating"], x["artist"]["completed_commissions"]), reverse=True)
        return results
    
    def get_commission_status(self, commission_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed commission status"""
        
        if commission_id not in self.commissions:
            return None
        
        commission = self.commissions[commission_id]
        
        status_info = {
            "commission": commission.dict(),
            "timeline": self._generate_commission_timeline(commission),
            "messages": self._get_commission_messages(commission_id),
            "next_actions": self._get_next_actions(commission)
        }
        
        if commission.artist_id:
            status_info["artist"] = self.artists.get(commission.artist_id)
        
        return status_info
    
    def _generate_commission_timeline(self, commission: ArtCommission) -> List[Dict[str, Any]]:
        """Generate commission timeline"""
        
        timeline = [
            {
                "event": "Commission Created",
                "date": commission.created_at,
                "status": "completed"
            }
        ]
        
        if commission.accepted_at:
            timeline.append({
                "event": "Proposal Accepted",
                "date": commission.accepted_at,
                "status": "completed"
            })
        
        if commission.started_at:
            timeline.append({
                "event": "Work Started",
                "date": commission.started_at,
                "status": "completed"
            })
        
        if commission.completed_at:
            timeline.append({
                "event": "Artwork Submitted",
                "date": commission.completed_at,
                "status": "completed"
            })
        
        if commission.approved_at:
            timeline.append({
                "event": "Commission Completed",
                "date": commission.approved_at,
                "status": "completed"
            })
        
        return timeline
    
    def _get_commission_messages(self, commission_id: str) -> List[Dict[str, Any]]:
        """Get commission conversation messages"""
        # Would integrate with messaging system
        return []
    
    def _get_next_actions(self, commission: ArtCommission) -> List[str]:
        """Get next required actions"""
        
        actions = []
        
        if commission.status == CommissionStatus.OPEN:
            actions.append("Waiting for artist proposals")
        elif commission.status == CommissionStatus.ACCEPTED:
            actions.append("Artist to start work")
        elif commission.status == CommissionStatus.IN_PROGRESS:
            actions.append("Artist working on commission")
        elif commission.status == CommissionStatus.PENDING_REVIEW:
            actions.append("Client review required")
        
        return actions