import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from decimal import Decimal
from models.monetization_models import *

class APIMarketplaceManager:
    def __init__(self):
        self.api_listings = {}
        self.categories = {
            "data": "Data & Analytics",
            "ai": "Artificial Intelligence",
            "financial": "Financial Services",
            "social": "Social Media",
            "communication": "Communication",
            "weather": "Weather & Climate",
            "location": "Maps & Location",
            "ecommerce": "E-commerce",
            "healthcare": "Healthcare",
            "security": "Security & Identity"
        }
        self.reviews = {}
        self.marketplace_stats = {}
        self.featured_apis = []
        
    async def submit_api_listing(self, request: APIListingRequest) -> APIListingResponse:
        listing_id = str(uuid.uuid4())
        
        listing_data = {
            "listing_id": listing_id,
            "api_id": request.api_id,
            "name": request.name,
            "description": request.description,
            "provider_id": request.provider_id,
            "pricing_tiers": request.pricing_tiers,
            "categories": request.categories,
            "documentation_url": request.documentation_url,
            "terms_of_service_url": request.terms_of_service_url,
            "status": MarketplaceStatus.PENDING,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "rating": 0.0,
            "total_subscribers": 0,
            "total_revenue": Decimal("0.00"),
            "monthly_calls": 0,
            "uptime_percentage": 99.9,
            "average_response_time": 150,
            "supported_formats": ["JSON", "XML"],
            "geographic_availability": ["global"],
            "compliance_certifications": [],
            "last_updated": datetime.now()
        }
        
        self.api_listings[listing_id] = listing_data
        
        await self._create_review_workflow(listing_id, request.provider_id)
        
        return APIListingResponse(
            listing_id=listing_id,
            api_id=request.api_id,
            name=request.name,
            description=request.description,
            provider_id=request.provider_id,
            pricing_tiers=request.pricing_tiers,
            categories=request.categories,
            rating=0.0,
            total_subscribers=0,
            status=MarketplaceStatus.PENDING,
            created_at=listing_data["created_at"],
            updated_at=listing_data["updated_at"]
        )
    
    async def approve_api_listing(self, listing_id: str, reviewer_id: str, notes: str = "") -> Dict:
        if listing_id not in self.api_listings:
            raise ValueError("API listing not found")
        
        listing = self.api_listings[listing_id]
        listing["status"] = MarketplaceStatus.APPROVED
        listing["approved_at"] = datetime.now()
        listing["approved_by"] = reviewer_id
        listing["approval_notes"] = notes
        listing["updated_at"] = datetime.now()
        
        await self._notify_provider(listing["provider_id"], "listing_approved", {
            "listing_id": listing_id,
            "api_name": listing["name"]
        })
        
        return {
            "success": True,
            "message": "API listing approved",
            "listing_id": listing_id,
            "approved_at": datetime.now()
        }
    
    async def reject_api_listing(self, listing_id: str, reviewer_id: str, reason: str) -> Dict:
        if listing_id not in self.api_listings:
            raise ValueError("API listing not found")
        
        listing = self.api_listings[listing_id]
        listing["status"] = MarketplaceStatus.REJECTED
        listing["rejected_at"] = datetime.now()
        listing["rejected_by"] = reviewer_id
        listing["rejection_reason"] = reason
        listing["updated_at"] = datetime.now()
        
        await self._notify_provider(listing["provider_id"], "listing_rejected", {
            "listing_id": listing_id,
            "api_name": listing["name"],
            "reason": reason
        })
        
        return {
            "success": True,
            "message": "API listing rejected",
            "listing_id": listing_id,
            "reason": reason,
            "rejected_at": datetime.now()
        }
    
    async def search_apis(self, query: str = "", category: str = "", 
                         min_rating: float = 0.0, max_price: float = None,
                         sort_by: str = "relevance") -> List[Dict]:
        
        filtered_listings = []
        
        for listing in self.api_listings.values():
            if listing["status"] != MarketplaceStatus.APPROVED:
                continue
            
            if query and query.lower() not in listing["name"].lower() and query.lower() not in listing["description"].lower():
                continue
            
            if category and category not in listing["categories"]:
                continue
            
            if listing["rating"] < min_rating:
                continue
            
            if max_price is not None:
                min_tier_price = min([float(tier.overage_pricing or 0) for tier in listing["pricing_tiers"]])
                if min_tier_price > max_price:
                    continue
            
            listing_summary = {
                "listing_id": listing["listing_id"],
                "api_id": listing["api_id"],
                "name": listing["name"],
                "description": listing["description"][:200] + "..." if len(listing["description"]) > 200 else listing["description"],
                "provider_id": listing["provider_id"],
                "categories": listing["categories"],
                "rating": listing["rating"],
                "total_subscribers": listing["total_subscribers"],
                "pricing_tiers": listing["pricing_tiers"],
                "uptime_percentage": listing["uptime_percentage"],
                "average_response_time": listing["average_response_time"]
            }
            
            filtered_listings.append(listing_summary)
        
        if sort_by == "rating":
            filtered_listings.sort(key=lambda x: x["rating"], reverse=True)
        elif sort_by == "subscribers":
            filtered_listings.sort(key=lambda x: x["total_subscribers"], reverse=True)
        elif sort_by == "price_low":
            filtered_listings.sort(key=lambda x: min([float(tier.overage_pricing or 0) for tier in x["pricing_tiers"]]))
        elif sort_by == "price_high":
            filtered_listings.sort(key=lambda x: min([float(tier.overage_pricing or 0) for tier in x["pricing_tiers"]]), reverse=True)
        
        return filtered_listings
    
    async def get_api_details(self, listing_id: str) -> Dict:
        if listing_id not in self.api_listings:
            raise ValueError("API listing not found")
        
        listing = self.api_listings[listing_id]
        
        reviews = await self._get_api_reviews(listing_id)
        similar_apis = await self._get_similar_apis(listing["categories"], listing_id)
        usage_statistics = await self._get_api_usage_stats(listing["api_id"])
        
        return {
            "listing": listing,
            "reviews": reviews,
            "similar_apis": similar_apis,
            "usage_statistics": usage_statistics,
            "provider_info": await self._get_provider_info(listing["provider_id"])
        }
    
    async def submit_api_review(self, listing_id: str, reviewer_id: str, 
                              rating: int, comment: str) -> Dict:
        if listing_id not in self.api_listings:
            raise ValueError("API listing not found")
        
        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5")
        
        review_id = str(uuid.uuid4())
        
        review = {
            "review_id": review_id,
            "listing_id": listing_id,
            "reviewer_id": reviewer_id,
            "rating": rating,
            "comment": comment,
            "created_at": datetime.now(),
            "helpful_votes": 0,
            "verified_purchase": True
        }
        
        if listing_id not in self.reviews:
            self.reviews[listing_id] = []
        
        self.reviews[listing_id].append(review)
        
        await self._update_api_rating(listing_id)
        
        return {
            "review_id": review_id,
            "message": "Review submitted successfully",
            "submitted_at": datetime.now()
        }
    
    async def get_marketplace_categories(self) -> Dict:
        category_stats = {}
        
        for category_key, category_name in self.categories.items():
            count = sum(1 for listing in self.api_listings.values() 
                       if listing["status"] == MarketplaceStatus.APPROVED 
                       and category_key in listing["categories"])
            
            category_stats[category_key] = {
                "name": category_name,
                "api_count": count,
                "trending": count > 5
            }
        
        return category_stats
    
    async def get_featured_apis(self, limit: int = 10) -> List[Dict]:
        featured = []
        
        approved_listings = [
            listing for listing in self.api_listings.values()
            if listing["status"] == MarketplaceStatus.APPROVED
        ]
        
        sorted_by_popularity = sorted(
            approved_listings,
            key=lambda x: (x["rating"], x["total_subscribers"]),
            reverse=True
        )
        
        for listing in sorted_by_popularity[:limit]:
            featured.append({
                "listing_id": listing["listing_id"],
                "name": listing["name"],
                "description": listing["description"][:150] + "..." if len(listing["description"]) > 150 else listing["description"],
                "provider_id": listing["provider_id"],
                "rating": listing["rating"],
                "total_subscribers": listing["total_subscribers"],
                "categories": listing["categories"]
            })
        
        return featured
    
    async def get_marketplace_analytics(self) -> Dict:
        total_apis = len([l for l in self.api_listings.values() if l["status"] == MarketplaceStatus.APPROVED])
        total_providers = len(set(l["provider_id"] for l in self.api_listings.values()))
        total_subscribers = sum(l["total_subscribers"] for l in self.api_listings.values())
        total_revenue = sum(l["total_revenue"] for l in self.api_listings.values())
        
        return {
            "total_apis": total_apis,
            "total_providers": total_providers,
            "total_subscribers": total_subscribers,
            "total_revenue": float(total_revenue),
            "growth_metrics": {
                "new_apis_this_month": 15,
                "new_subscribers_this_month": 1250,
                "revenue_growth_percentage": 25.3
            },
            "top_categories": await self._get_top_categories(),
            "platform_health": {
                "average_uptime": 99.7,
                "average_response_time": 145,
                "average_rating": 4.2
            }
        }
    
    async def update_api_stats(self, api_id: str, monthly_calls: int, 
                             uptime: float, response_time: float) -> Dict:
        
        for listing in self.api_listings.values():
            if listing["api_id"] == api_id:
                listing["monthly_calls"] = monthly_calls
                listing["uptime_percentage"] = uptime
                listing["average_response_time"] = response_time
                listing["last_updated"] = datetime.now()
                
                return {
                    "success": True,
                    "message": "API statistics updated",
                    "updated_at": datetime.now()
                }
        
        raise ValueError("API not found in marketplace")
    
    async def _create_review_workflow(self, listing_id: str, provider_id: str):
        pass
    
    async def _notify_provider(self, provider_id: str, event_type: str, data: Dict):
        pass
    
    async def _get_api_reviews(self, listing_id: str) -> List[Dict]:
        if listing_id not in self.reviews:
            return []
        
        return sorted(
            self.reviews[listing_id],
            key=lambda x: x["created_at"],
            reverse=True
        )
    
    async def _get_similar_apis(self, categories: List[str], exclude_listing_id: str) -> List[Dict]:
        similar = []
        
        for listing in self.api_listings.values():
            if (listing["listing_id"] != exclude_listing_id and 
                listing["status"] == MarketplaceStatus.APPROVED and
                any(cat in listing["categories"] for cat in categories)):
                
                similar.append({
                    "listing_id": listing["listing_id"],
                    "name": listing["name"],
                    "rating": listing["rating"],
                    "total_subscribers": listing["total_subscribers"]
                })
        
        return sorted(similar, key=lambda x: x["rating"], reverse=True)[:5]
    
    async def _get_api_usage_stats(self, api_id: str) -> Dict:
        return {
            "monthly_calls": 150000,
            "average_response_time": 145,
            "uptime_percentage": 99.7,
            "error_rate": 0.1
        }
    
    async def _get_provider_info(self, provider_id: str) -> Dict:
        return {
            "provider_id": provider_id,
            "company_name": f"Provider {provider_id[:8]}",
            "total_apis": len([l for l in self.api_listings.values() if l["provider_id"] == provider_id]),
            "average_rating": 4.3,
            "support_response_time": "< 2 hours"
        }
    
    async def _update_api_rating(self, listing_id: str):
        if listing_id in self.reviews and self.reviews[listing_id]:
            reviews = self.reviews[listing_id]
            average_rating = sum(r["rating"] for r in reviews) / len(reviews)
            self.api_listings[listing_id]["rating"] = round(average_rating, 1)
    
    async def _get_top_categories(self) -> List[Dict]:
        category_counts = {}
        
        for listing in self.api_listings.values():
            if listing["status"] == MarketplaceStatus.APPROVED:
                for category in listing["categories"]:
                    category_counts[category] = category_counts.get(category, 0) + 1
        
        return sorted(
            [{"category": cat, "count": count} for cat, count in category_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:5]

api_marketplace_manager = APIMarketplaceManager()