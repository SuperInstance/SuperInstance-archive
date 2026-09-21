"""
Affiliate Link Manager - Advanced affiliate marketing system.
Features: Multi-network integration, smart link generation, commission tracking, and performance optimization.
"""

import asyncio
import json
import hashlib
import hmac
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import urllib.parse
import uuid
import re

class AffiliateNetwork(Enum):
    AMAZON_ASSOCIATES = "amazon_associates"
    COMMISSION_JUNCTION = "commission_junction"
    SHAREASALE = "shareasale"
    CLICKBANK = "clickbank"
    IMPACT = "impact"
    RAKUTEN = "rakuten"
    INTERNAL = "internal"

class ProductCategory(Enum):
    ELECTRONICS = "electronics"
    SOFTWARE = "software"
    BOOKS = "books"
    FISHING_GEAR = "fishing_gear"
    BUSINESS_TOOLS = "business_tools"
    EDUCATION = "education"
    GAMING = "gaming"
    VIDEO_EQUIPMENT = "video_equipment"
    MAKER_TOOLS = "maker_tools"
    MARINE_EQUIPMENT = "marine_equipment"

@dataclass
class AffiliateAccount:
    """Affiliate account configuration."""
    network: AffiliateNetwork
    account_id: str
    api_key: Optional[str] = None
    tracking_id: str = ""
    commission_rate: float = 0.0
    cookie_duration: int = 24  # hours
    min_payout: float = 50.0
    currency: str = "USD"

@dataclass
class Product:
    """Product information for affiliate linking."""
    id: str
    name: str
    description: str
    price: float
    currency: str
    category: ProductCategory
    merchant: str
    image_url: Optional[str] = None
    rating: Optional[float] = None
    availability: bool = True

@dataclass
class AffiliateLink:
    """Generated affiliate link with tracking."""
    id: str
    original_url: str
    affiliate_url: str
    network: AffiliateNetwork
    product_id: Optional[str] = None
    tracking_code: str = ""
    commission_rate: float = 0.0
    created_at: datetime = None
    expires_at: Optional[datetime] = None

@dataclass
class Commission:
    """Commission tracking data."""
    id: str
    affiliate_link_id: str
    user_id: str
    order_id: str
    order_value: float
    commission_amount: float
    commission_rate: float
    network: AffiliateNetwork
    status: str = "pending"  # pending, confirmed, paid
    created_at: datetime = None

class AmazonAssociatesAPI:
    """Amazon Associates API integration."""
    
    def __init__(self, account: AffiliateAccount):
        self.account = account
        self.base_url = "https://webservices.amazon.com/paapi5"
        self.region = "US"
    
    def generate_affiliate_link(self, product_url: str, tracking_id: str = None) -> str:
        """Generate Amazon affiliate link."""
        tracking_id = tracking_id or self.account.tracking_id
        
        # Parse the original URL
        if "amazon.com" not in product_url:
            return product_url
        
        # Extract ASIN from URL
        asin = self._extract_asin(product_url)
        if not asin:
            return product_url
        
        # Generate clean affiliate link
        affiliate_url = f"https://www.amazon.com/dp/{asin}?tag={tracking_id}"
        
        return affiliate_url
    
    def _extract_asin(self, url: str) -> Optional[str]:
        """Extract ASIN from Amazon URL."""
        patterns = [
            r'/dp/([A-Z0-9]{10})',
            r'/gp/product/([A-Z0-9]{10})',
            r'/product/([A-Z0-9]{10})',
            r'asin=([A-Z0-9]{10})',
            r'/([A-Z0-9]{10})(?:/|\?|$)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    async def search_products(self, keywords: str, category: str = "All") -> List[Product]:
        """Search for products (mock implementation)."""
        # Mock product data
        mock_products = [
            Product(
                id="B08N5WRWNW",
                name=f"Professional {keywords} Equipment",
                description=f"High-quality {keywords} gear for professionals",
                price=89.99,
                currency="USD",
                category=ProductCategory.ELECTRONICS,
                merchant="Amazon",
                rating=4.5,
                availability=True
            ),
            Product(
                id="B07XJ8C8F5",
                name=f"{keywords} Starter Kit",
                description=f"Everything you need to get started with {keywords}",
                price=34.99,
                currency="USD",
                category=ProductCategory.ELECTRONICS,
                merchant="Amazon",
                rating=4.2,
                availability=True
            )
        ]
        
        return mock_products
    
    async def get_commission_rate(self, category: str) -> float:
        """Get commission rate for product category."""
        # Amazon Associates commission rates (simplified)
        rates = {
            "Electronics": 0.02,    # 2%
            "Software": 0.10,       # 10%
            "Books": 0.045,         # 4.5%
            "Sports": 0.03,         # 3%
            "Tools": 0.03,          # 3%
            "Default": 0.02         # 2%
        }
        
        return rates.get(category, rates["Default"])

class LinkTracker:
    """Advanced link tracking and analytics system."""
    
    def __init__(self):
        self.clicks = []
        self.conversions = []
        self.link_performance = {}
    
    def generate_tracking_code(self, user_id: str, campaign: str = "default") -> str:
        """Generate unique tracking code."""
        timestamp = int(datetime.now().timestamp())
        data = f"{user_id}:{campaign}:{timestamp}"
        return hashlib.md5(data.encode()).hexdigest()[:12]
    
    def create_tracked_link(self, original_url: str, user_id: str, 
                          campaign: str = "default") -> str:
        """Create tracked link with analytics."""
        tracking_code = self.generate_tracking_code(user_id, campaign)
        
        # Add tracking parameters
        separator = "&" if "?" in original_url else "?"
        tracked_url = f"{original_url}{separator}utm_source=activelog&utm_medium=affiliate&utm_campaign={campaign}&al_track={tracking_code}"
        
        return tracked_url
    
    async def record_click(self, tracking_code: str, user_id: str, 
                          ip_address: str = None, user_agent: str = None) -> Dict[str, Any]:
        """Record affiliate link click."""
        click_data = {
            "id": str(uuid.uuid4()),
            "tracking_code": tracking_code,
            "user_id": user_id,
            "timestamp": datetime.now(),
            "ip_address": ip_address,
            "user_agent": user_agent
        }
        
        self.clicks.append(click_data)
        
        # Update performance metrics
        if tracking_code not in self.link_performance:
            self.link_performance[tracking_code] = {
                "clicks": 0,
                "conversions": 0,
                "revenue": 0.0
            }
        
        self.link_performance[tracking_code]["clicks"] += 1
        
        return {
            "success": True,
            "click_id": click_data["id"],
            "tracking_code": tracking_code
        }
    
    async def record_conversion(self, tracking_code: str, order_value: float, 
                              commission_amount: float) -> Dict[str, Any]:
        """Record affiliate conversion."""
        conversion_data = {
            "id": str(uuid.uuid4()),
            "tracking_code": tracking_code,
            "order_value": order_value,
            "commission_amount": commission_amount,
            "timestamp": datetime.now()
        }
        
        self.conversions.append(conversion_data)
        
        # Update performance metrics
        if tracking_code in self.link_performance:
            self.link_performance[tracking_code]["conversions"] += 1
            self.link_performance[tracking_code]["revenue"] += commission_amount
        
        return {
            "success": True,
            "conversion_id": conversion_data["id"],
            "commission_amount": commission_amount
        }
    
    async def get_performance_stats(self, tracking_code: str = None, 
                                  user_id: str = None) -> Dict[str, Any]:
        """Get performance statistics."""
        if tracking_code:
            # Stats for specific tracking code
            perf = self.link_performance.get(tracking_code, {
                "clicks": 0,
                "conversions": 0,
                "revenue": 0.0
            })
            
            conversion_rate = (perf["conversions"] / perf["clicks"] * 100) if perf["clicks"] > 0 else 0
            
            return {
                "tracking_code": tracking_code,
                "clicks": perf["clicks"],
                "conversions": perf["conversions"],
                "revenue": round(perf["revenue"], 2),
                "conversion_rate": round(conversion_rate, 2),
                "average_order_value": round(perf["revenue"] / perf["conversions"], 2) if perf["conversions"] > 0 else 0
            }
        
        elif user_id:
            # Stats for specific user
            user_clicks = [c for c in self.clicks if c["user_id"] == user_id]
            user_tracking_codes = list(set(c["tracking_code"] for c in user_clicks))
            
            total_clicks = len(user_clicks)
            total_conversions = len([c for c in self.conversions if c["tracking_code"] in user_tracking_codes])
            total_revenue = sum(c["commission_amount"] for c in self.conversions if c["tracking_code"] in user_tracking_codes)
            
            return {
                "user_id": user_id,
                "total_clicks": total_clicks,
                "total_conversions": total_conversions,
                "total_revenue": round(total_revenue, 2),
                "active_links": len(user_tracking_codes),
                "conversion_rate": round((total_conversions / total_clicks * 100) if total_clicks > 0 else 0, 2)
            }
        
        else:
            # Overall stats
            total_clicks = len(self.clicks)
            total_conversions = len(self.conversions)
            total_revenue = sum(c["commission_amount"] for c in self.conversions)
            
            return {
                "total_clicks": total_clicks,
                "total_conversions": total_conversions,
                "total_revenue": round(total_revenue, 2),
                "overall_conversion_rate": round((total_conversions / total_clicks * 100) if total_clicks > 0 else 0, 2),
                "active_tracking_codes": len(self.link_performance)
            }

class SmartRecommendationEngine:
    """AI-powered product recommendation system."""
    
    def __init__(self):
        self.user_preferences = {}
        self.product_database = self._initialize_product_database()
        self.recommendation_rules = self._load_recommendation_rules()
    
    def _initialize_product_database(self) -> Dict[str, List[Product]]:
        """Initialize product database by category."""
        return {
            ProductCategory.FISHING_GEAR.value: [
                Product("FG001", "Professional Fishing Rod", "Carbon fiber fishing rod", 129.99, "USD", ProductCategory.FISHING_GEAR, "Bass Pro"),
                Product("FG002", "Tackle Box Set", "Complete tackle organization", 45.99, "USD", ProductCategory.FISHING_GEAR, "Cabela's"),
                Product("FG003", "Fish Finder GPS", "Advanced sonar technology", 299.99, "USD", ProductCategory.ELECTRONICS, "Garmin")
            ],
            ProductCategory.BUSINESS_TOOLS.value: [
                Product("BT001", "Receipt Scanner", "Mobile receipt scanning", 89.99, "USD", ProductCategory.ELECTRONICS, "Fujitsu"),
                Product("BT002", "Accounting Software", "Small business accounting", 29.99, "USD", ProductCategory.SOFTWARE, "QuickBooks"),
                Product("BT003", "Business Card Scanner", "Digital business cards", 199.99, "USD", ProductCategory.ELECTRONICS, "ScanSnap")
            ],
            ProductCategory.EDUCATION.value: [
                Product("ED001", "Study Planner", "Academic planning tools", 24.99, "USD", ProductCategory.SOFTWARE, "StudyBlue"),
                Product("ED002", "Online Course Bundle", "Skill development courses", 199.99, "USD", ProductCategory.EDUCATION, "Coursera"),
                Product("ED003", "Note-Taking App", "Digital note organization", 9.99, "USD", ProductCategory.SOFTWARE, "Notion")
            ],
            ProductCategory.GAMING.value: [
                Product("GM001", "Gaming Headset", "Professional gaming audio", 149.99, "USD", ProductCategory.ELECTRONICS, "SteelSeries"),
                Product("GM002", "Game Overlay Software", "Streaming tools", 59.99, "USD", ProductCategory.SOFTWARE, "OBS Studio"),
                Product("GM003", "Gaming Mouse", "High-precision gaming", 79.99, "USD", ProductCategory.ELECTRONICS, "Logitech")
            ],
            ProductCategory.VIDEO_EQUIPMENT.value: [
                Product("VE001", "4K Camera", "Professional video recording", 899.99, "USD", ProductCategory.ELECTRONICS, "Sony"),
                Product("VE002", "Video Editing Software", "Professional editing suite", 299.99, "USD", ProductCategory.SOFTWARE, "Adobe"),
                Product("VE003", "Microphone Kit", "Studio-quality audio", 199.99, "USD", ProductCategory.ELECTRONICS, "Rode")
            ]
        }
    
    def _load_recommendation_rules(self) -> Dict[str, Any]:
        """Load recommendation rules and algorithms."""
        return {
            "module_product_mapping": {
                "fishing": ProductCategory.FISHING_GEAR.value,
                "business": ProductCategory.BUSINESS_TOOLS.value,
                "study": ProductCategory.EDUCATION.value,
                "player": ProductCategory.GAMING.value,
                "real": ProductCategory.VIDEO_EQUIPMENT.value,
                "maker": ProductCategory.MAKER_TOOLS.value,
                "marine": ProductCategory.MARINE_EQUIPMENT.value
            },
            "contextual_triggers": {
                "receipt_scan": ["receipt_scanner", "accounting_software"],
                "expense_tracking": ["business_tools", "tax_software"],
                "fishing_trip": ["fishing_gear", "marine_equipment"],
                "study_session": ["education", "productivity_tools"],
                "gaming_stream": ["gaming_gear", "streaming_tools"],
                "video_editing": ["video_equipment", "editing_software"]
            },
            "price_sensitivity": {
                "budget": {"max": 50, "categories": ["accessories", "software"]},
                "mid_range": {"max": 200, "categories": ["tools", "equipment"]},
                "premium": {"max": 1000, "categories": ["professional", "high_end"]}
            }
        }
    
    async def get_contextual_recommendations(self, user_id: str, context: str, 
                                           module: str = None, price_range: str = "mid_range") -> List[Dict[str, Any]]:
        """Get contextual product recommendations."""
        recommendations = []
        
        # Determine relevant categories
        relevant_categories = []
        
        if module and module in self.recommendation_rules["module_product_mapping"]:
            relevant_categories.append(self.recommendation_rules["module_product_mapping"][module])
        
        if context in self.recommendation_rules["contextual_triggers"]:
            relevant_categories.extend(self.recommendation_rules["contextual_triggers"][context])
        
        # Get price constraints
        price_constraints = self.recommendation_rules["price_sensitivity"].get(price_range, {})
        max_price = price_constraints.get("max", 1000)
        
        # Find matching products
        for category in set(relevant_categories):
            products = self.product_database.get(category, [])
            for product in products:
                if product.price <= max_price and product.availability:
                    recommendations.append({
                        "product": asdict(product),
                        "relevance_score": self._calculate_relevance_score(product, context, module),
                        "commission_potential": product.price * 0.05,  # 5% average commission
                        "recommendation_reason": self._get_recommendation_reason(product, context, module)
                    })
        
        # Sort by relevance score
        recommendations.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return recommendations[:5]  # Top 5 recommendations
    
    def _calculate_relevance_score(self, product: Product, context: str, module: str) -> float:
        """Calculate relevance score for a product."""
        score = 0.5  # Base score
        
        # Module match bonus
        if module and module in product.name.lower():
            score += 0.3
        
        # Context match bonus
        if context and any(word in product.name.lower() for word in context.split("_")):
            score += 0.2
        
        # Rating bonus
        if product.rating:
            score += (product.rating - 3.0) * 0.1  # Bonus for ratings above 3.0
        
        # Price factor (higher price = potentially higher commission)
        if product.price > 100:
            score += 0.1
        
        return min(score, 1.0)
    
    def _get_recommendation_reason(self, product: Product, context: str, module: str) -> str:
        """Generate human-readable recommendation reason."""
        reasons = []
        
        if module:
            reasons.append(f"Recommended for {module} users")
        
        if context:
            reasons.append(f"Perfect for {context.replace('_', ' ')}")
        
        if product.rating and product.rating >= 4.0:
            reasons.append(f"Highly rated ({product.rating}/5)")
        
        if not reasons:
            reasons.append("Popular choice")
        
        return " • ".join(reasons)
    
    async def update_user_preferences(self, user_id: str, interactions: List[Dict[str, Any]]):
        """Update user preferences based on interactions."""
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {
                "preferred_categories": {},
                "price_range": "mid_range",
                "interaction_count": 0
            }
        
        prefs = self.user_preferences[user_id]
        
        for interaction in interactions:
            category = interaction.get("category")
            if category:
                prefs["preferred_categories"][category] = prefs["preferred_categories"].get(category, 0) + 1
            
            prefs["interaction_count"] += 1
        
        # Adjust price range based on interactions
        if prefs["interaction_count"] > 10:
            high_price_interactions = sum(1 for i in interactions if i.get("price", 0) > 200)
            if high_price_interactions / len(interactions) > 0.5:
                prefs["price_range"] = "premium"
            elif high_price_interactions / len(interactions) < 0.2:
                prefs["price_range"] = "budget"

class AffiliateManager:
    """Main affiliate marketing system orchestrator."""
    
    def __init__(self):
        self.networks = {}
        self.link_tracker = LinkTracker()
        self.recommendation_engine = SmartRecommendationEngine()
        self.affiliate_links = []
        self.commissions = []
        
        # Initialize affiliate networks
        self._initialize_networks()
        
        print("🔗 Affiliate Manager initialized")
    
    def _initialize_networks(self):
        """Initialize affiliate network configurations."""
        self.networks = {
            AffiliateNetwork.AMAZON_ASSOCIATES: AffiliateAccount(
                network=AffiliateNetwork.AMAZON_ASSOCIATES,
                account_id="activelog-20",
                tracking_id="activelog-20",
                commission_rate=0.04,  # 4% average
                cookie_duration=24
            ),
            AffiliateNetwork.COMMISSION_JUNCTION: AffiliateAccount(
                network=AffiliateNetwork.COMMISSION_JUNCTION,
                account_id="13579246",
                tracking_id="AL_CJ",
                commission_rate=0.08,  # 8% average
                cookie_duration=30
            ),
            AffiliateNetwork.SHAREASALE: AffiliateAccount(
                network=AffiliateNetwork.SHAREASALE,
                account_id="12345",
                tracking_id="AL_SAS",
                commission_rate=0.10,  # 10% average
                cookie_duration=45
            )
        }
    
    async def generate_affiliate_link(self, original_url: str, user_id: str, 
                                    campaign: str = "default", 
                                    network: AffiliateNetwork = None) -> Dict[str, Any]:
        """Generate tracked affiliate link."""
        try:
            # Auto-detect network if not specified
            if not network:
                network = self._detect_network(original_url)
            
            # Get network configuration
            account = self.networks.get(network)
            if not account:
                return {"error": f"Network {network} not configured"}
            
            # Generate affiliate link based on network
            if network == AffiliateNetwork.AMAZON_ASSOCIATES:
                amazon_api = AmazonAssociatesAPI(account)
                affiliate_url = amazon_api.generate_affiliate_link(original_url, account.tracking_id)
            else:
                # Generic affiliate link generation
                affiliate_url = self._generate_generic_affiliate_link(original_url, account)
            
            # Add tracking
            tracked_url = self.link_tracker.create_tracked_link(affiliate_url, user_id, campaign)
            tracking_code = self.link_tracker.generate_tracking_code(user_id, campaign)
            
            # Create affiliate link record
            link_id = str(uuid.uuid4())
            affiliate_link = AffiliateLink(
                id=link_id,
                original_url=original_url,
                affiliate_url=tracked_url,
                network=network,
                tracking_code=tracking_code,
                commission_rate=account.commission_rate,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=account.cookie_duration)
            )
            
            self.affiliate_links.append(affiliate_link)
            
            return {
                "success": True,
                "affiliate_link": asdict(affiliate_link),
                "estimated_commission_rate": account.commission_rate * 100,
                "cookie_duration_hours": account.cookie_duration
            }
            
        except Exception as e:
            return {"error": f"Failed to generate affiliate link: {str(e)}"}
    
    def _detect_network(self, url: str) -> AffiliateNetwork:
        """Auto-detect affiliate network from URL."""
        url_lower = url.lower()
        
        if "amazon.com" in url_lower:
            return AffiliateNetwork.AMAZON_ASSOCIATES
        elif "target.com" in url_lower or "bestbuy.com" in url_lower:
            return AffiliateNetwork.COMMISSION_JUNCTION
        elif "walmart.com" in url_lower or "homedepot.com" in url_lower:
            return AffiliateNetwork.SHAREASALE
        else:
            return AffiliateNetwork.AMAZON_ASSOCIATES  # Default
    
    def _generate_generic_affiliate_link(self, url: str, account: AffiliateAccount) -> str:
        """Generate generic affiliate link for non-Amazon networks."""
        # Add affiliate parameters
        separator = "&" if "?" in url else "?"
        affiliate_url = f"{url}{separator}aff_id={account.account_id}&tracking={account.tracking_id}"
        
        return affiliate_url
    
    async def get_smart_recommendations(self, user_id: str, module: str, 
                                      context: str = "general") -> List[Dict[str, Any]]:
        """Get smart product recommendations with affiliate links."""
        # Get contextual recommendations
        recommendations = await self.recommendation_engine.get_contextual_recommendations(
            user_id, context, module
        )
        
        # Generate affiliate links for each recommendation
        enhanced_recommendations = []
        for rec in recommendations:
            product = rec["product"]
            
            # Create mock product URL (in real implementation, use actual product URLs)
            product_url = f"https://www.amazon.com/dp/{product['id']}"
            
            # Generate affiliate link
            link_result = await self.generate_affiliate_link(
                product_url, user_id, f"{module}_{context}"
            )
            
            if link_result.get("success"):
                rec["affiliate_link"] = link_result["affiliate_link"]["affiliate_url"]
                rec["tracking_code"] = link_result["affiliate_link"]["tracking_code"]
                rec["commission_rate"] = link_result["estimated_commission_rate"]
            
            enhanced_recommendations.append(rec)
        
        return enhanced_recommendations
    
    async def record_link_click(self, tracking_code: str, user_id: str) -> Dict[str, Any]:
        """Record affiliate link click."""
        click_result = await self.link_tracker.record_click(tracking_code, user_id)
        
        if click_result["success"]:
            print(f"🖱️ Affiliate click recorded: {tracking_code}")
        
        return click_result
    
    async def record_commission(self, tracking_code: str, order_value: float, 
                              commission_rate: float = None) -> Dict[str, Any]:
        """Record affiliate commission."""
        # Find the affiliate link
        affiliate_link = next(
            (link for link in self.affiliate_links if link.tracking_code == tracking_code),
            None
        )
        
        if not affiliate_link:
            return {"error": "Affiliate link not found"}
        
        # Calculate commission
        rate = commission_rate or affiliate_link.commission_rate
        commission_amount = order_value * rate
        
        # Create commission record
        commission = Commission(
            id=str(uuid.uuid4()),
            affiliate_link_id=affiliate_link.id,
            user_id="",  # Would be extracted from tracking
            order_id=f"ORDER_{datetime.now().timestamp()}",
            order_value=order_value,
            commission_amount=commission_amount,
            commission_rate=rate,
            network=affiliate_link.network,
            created_at=datetime.now()
        )
        
        self.commissions.append(commission)
        
        # Record conversion in tracker
        await self.link_tracker.record_conversion(tracking_code, order_value, commission_amount)
        
        print(f"💰 Commission recorded: ${commission_amount:.2f} from ${order_value} order")
        
        return {
            "success": True,
            "commission": asdict(commission),
            "commission_amount": commission_amount
        }
    
    async def get_performance_analytics(self, user_id: str = None, 
                                      network: AffiliateNetwork = None,
                                      days: int = 30) -> Dict[str, Any]:
        """Get comprehensive affiliate performance analytics."""
        # Filter data based on parameters
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        filtered_commissions = [
            c for c in self.commissions
            if c.created_at >= start_date
        ]
        
        if network:
            filtered_commissions = [c for c in filtered_commissions if c.network == network]
        
        # Calculate metrics
        total_commissions = len(filtered_commissions)
        total_revenue = sum(c.commission_amount for c in filtered_commissions)
        total_order_value = sum(c.order_value for c in filtered_commissions)
        
        # Get click data
        if user_id:
            click_stats = await self.link_tracker.get_performance_stats(user_id=user_id)
        else:
            click_stats = await self.link_tracker.get_performance_stats()
        
        # Network breakdown
        network_stats = {}
        for commission in filtered_commissions:
            net = commission.network.value
            if net not in network_stats:
                network_stats[net] = {
                    "commissions": 0,
                    "revenue": 0.0,
                    "order_value": 0.0
                }
            
            network_stats[net]["commissions"] += 1
            network_stats[net]["revenue"] += commission.commission_amount
            network_stats[net]["order_value"] += commission.order_value
        
        return {
            "analytics_period": f"{start_date.date()} to {end_date.date()}",
            "summary": {
                "total_commissions": total_commissions,
                "total_revenue": round(total_revenue, 2),
                "total_order_value": round(total_order_value, 2),
                "average_commission": round(total_revenue / total_commissions, 2) if total_commissions > 0 else 0,
                "average_commission_rate": round((total_revenue / total_order_value * 100) if total_order_value > 0 else 0, 2)
            },
            "click_stats": click_stats,
            "network_breakdown": {
                net: {
                    **stats,
                    "average_commission_rate": round((stats["revenue"] / stats["order_value"] * 100) if stats["order_value"] > 0 else 0, 2)
                }
                for net, stats in network_stats.items()
            },
            "top_performing_links": await self._get_top_performing_links(days),
            "generated_at": datetime.now().isoformat()
        }
    
    async def _get_top_performing_links(self, days: int) -> List[Dict[str, Any]]:
        """Get top performing affiliate links."""
        # Get performance for all tracking codes
        top_links = []
        
        for tracking_code in self.link_tracker.link_performance:
            stats = await self.link_tracker.get_performance_stats(tracking_code)
            if stats["revenue"] > 0:  # Only include links with revenue
                top_links.append(stats)
        
        # Sort by revenue
        top_links.sort(key=lambda x: x["revenue"], reverse=True)
        
        return top_links[:10]  # Top 10 links
    
    async def optimize_affiliate_strategy(self) -> Dict[str, Any]:
        """Analyze performance and suggest optimizations."""
        analytics = await self.get_performance_analytics(days=30)
        
        optimizations = []
        
        # Network performance analysis
        network_stats = analytics["network_breakdown"]
        if network_stats:
            best_network = max(network_stats.items(), key=lambda x: x[1]["revenue"])
            worst_network = min(network_stats.items(), key=lambda x: x[1]["revenue"])
            
            optimizations.append({
                "type": "network_optimization",
                "recommendation": f"Focus more on {best_network[0]} network (${best_network[1]['revenue']:.2f} revenue)",
                "priority": "high"
            })
            
            if worst_network[1]["revenue"] < best_network[1]["revenue"] * 0.1:
                optimizations.append({
                    "type": "network_review",
                    "recommendation": f"Consider reducing focus on {worst_network[0]} network",
                    "priority": "medium"
                })
        
        # Click-to-conversion analysis
        overall_conversion_rate = analytics["click_stats"].get("overall_conversion_rate", 0)
        if overall_conversion_rate < 2.0:
            optimizations.append({
                "type": "conversion_optimization",
                "recommendation": "Low conversion rate detected. Review product recommendations and targeting",
                "priority": "high",
                "current_rate": overall_conversion_rate
            })
        
        # Revenue per click analysis
        total_clicks = analytics["click_stats"].get("total_clicks", 1)
        total_revenue = analytics["summary"]["total_revenue"]
        revenue_per_click = total_revenue / total_clicks if total_clicks > 0 else 0
        
        if revenue_per_click < 0.10:
            optimizations.append({
                "type": "monetization_improvement",
                "recommendation": "Low revenue per click. Consider promoting higher-value products",
                "priority": "medium",
                "current_rpc": round(revenue_per_click, 3)
            })
        
        return {
            "optimization_analysis": {
                "period": "Last 30 days",
                "overall_performance": "good" if overall_conversion_rate > 2.0 and revenue_per_click > 0.10 else "needs_improvement",
                "key_metrics": {
                    "conversion_rate": overall_conversion_rate,
                    "revenue_per_click": round(revenue_per_click, 3),
                    "total_revenue": total_revenue
                }
            },
            "optimizations": optimizations,
            "generated_at": datetime.now().isoformat()
        }

# CLI interface for testing
async def main():
    """CLI interface for Affiliate Manager testing."""
    affiliate_manager = AffiliateManager()
    
    print("🔗 Affiliate Manager Test Suite")
    print("=" * 40)
    
    # Test 1: Generate affiliate links
    print("\n1. Generating affiliate links...")
    
    amazon_link = await affiliate_manager.generate_affiliate_link(
        "https://www.amazon.com/dp/B08N5WRWNW",
        "test_user",
        "fishing_module"
    )
    
    generic_link = await affiliate_manager.generate_affiliate_link(
        "https://www.bestbuy.com/site/product/12345",
        "test_user",
        "electronics"
    )
    
    print(f"✅ Generated Amazon link: {amazon_link['success']}")
    print(f"✅ Generated generic link: {generic_link['success']}")
    
    # Test 2: Get smart recommendations
    print("\n2. Getting smart recommendations...")
    
    fishing_recs = await affiliate_manager.get_smart_recommendations(
        "test_user", "fishing", "fishing_trip"
    )
    
    business_recs = await affiliate_manager.get_smart_recommendations(
        "test_user", "business", "expense_tracking"
    )
    
    print(f"✅ Fishing recommendations: {len(fishing_recs)} products")
    print(f"✅ Business recommendations: {len(business_recs)} products")
    
    # Test 3: Simulate clicks and conversions
    print("\n3. Simulating clicks and conversions...")
    
    if amazon_link.get("success"):
        tracking_code = amazon_link["affiliate_link"]["tracking_code"]
        
        # Record click
        click_result = await affiliate_manager.record_link_click(tracking_code, "test_user")
        print(f"✅ Click recorded: {click_result['success']}")
        
        # Record commission
        commission_result = await affiliate_manager.record_commission(tracking_code, 129.99, 0.04)
        print(f"✅ Commission recorded: ${commission_result.get('commission_amount', 0):.2f}")
    
    # Test 4: Performance analytics
    print("\n4. Getting performance analytics...")
    
    analytics = await affiliate_manager.get_performance_analytics(days=30)
    print(f"✅ Analytics generated:")
    print(f"   Total revenue: ${analytics['summary']['total_revenue']}")
    print(f"   Total clicks: {analytics['click_stats']['total_clicks']}")
    print(f"   Conversion rate: {analytics['click_stats']['overall_conversion_rate']}%")
    
    # Test 5: Optimization recommendations
    print("\n5. Getting optimization recommendations...")
    
    optimization = await affiliate_manager.optimize_affiliate_strategy()
    print(f"✅ Optimization analysis: {optimization['optimization_analysis']['overall_performance']}")
    print(f"   Recommendations: {len(optimization['optimizations'])}")
    
    for opt in optimization['optimizations'][:3]:  # Show first 3
        print(f"   - {opt['recommendation']} (Priority: {opt['priority']})")
    
    # Test 6: Network comparison
    print("\n6. Network performance comparison...")
    
    network_stats = analytics["network_breakdown"]
    if network_stats:
        for network, stats in network_stats.items():
            print(f"   {network}: ${stats['revenue']:.2f} revenue, {stats['average_commission_rate']:.1f}% rate")
    else:
        print("   No network data available yet")
    
    print("\n🎉 Affiliate Manager tests completed!")

if __name__ == "__main__":
    asyncio.run(main())