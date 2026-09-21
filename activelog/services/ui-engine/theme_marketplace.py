"""
Theme Marketplace
Comprehensive theme marketplace with purchasing, rating, and distribution
"""

from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel
from datetime import datetime, timedelta
import json
import uuid
import hashlib
from enum import Enum

class ThemeCategory(str, Enum):
    BUSINESS = "business"
    CREATIVE = "creative"
    MINIMAL = "minimal"
    DARK = "dark"
    LIGHT = "light"
    COLORFUL = "colorful"
    PROFESSIONAL = "professional"
    GAMING = "gaming"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    ECOMMERCE = "ecommerce"
    PORTFOLIO = "portfolio"

class LicenseType(str, Enum):
    FREE = "free"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"
    OPEN_SOURCE = "open_source"

class ThemeStatus(str, Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"

class ColorPalette(BaseModel):
    """Color palette definition"""
    primary: str
    secondary: str
    accent: str
    background: str
    surface: str
    text_primary: str
    text_secondary: str
    success: str
    warning: str
    error: str
    info: str

class Typography(BaseModel):
    """Typography configuration"""
    font_family_primary: str
    font_family_secondary: str = ""
    font_family_mono: str = "monospace"
    font_size_xs: str = "0.75rem"
    font_size_sm: str = "0.875rem"
    font_size_base: str = "1rem"
    font_size_lg: str = "1.125rem"
    font_size_xl: str = "1.25rem"
    font_size_2xl: str = "1.5rem"
    font_size_3xl: str = "1.875rem"
    line_height_tight: float = 1.25
    line_height_normal: float = 1.5
    line_height_loose: float = 1.75

class Spacing(BaseModel):
    """Spacing system"""
    xs: str = "0.25rem"
    sm: str = "0.5rem"
    md: str = "1rem"
    lg: str = "1.5rem"
    xl: str = "2rem"
    xxl: str = "3rem"

class BorderRadius(BaseModel):
    """Border radius values"""
    none: str = "0"
    sm: str = "0.125rem"
    md: str = "0.375rem"
    lg: str = "0.5rem"
    xl: str = "0.75rem"
    full: str = "9999px"

class Shadows(BaseModel):
    """Box shadow definitions"""
    none: str = "none"
    sm: str = "0 1px 2px 0 rgba(0, 0, 0, 0.05)"
    md: str = "0 4px 6px -1px rgba(0, 0, 0, 0.1)"
    lg: str = "0 10px 15px -3px rgba(0, 0, 0, 0.1)"
    xl: str = "0 20px 25px -5px rgba(0, 0, 0, 0.1)"

class ComponentStyles(BaseModel):
    """Component-specific styling"""
    buttons: Dict[str, Any] = {}
    inputs: Dict[str, Any] = {}
    cards: Dict[str, Any] = {}
    modals: Dict[str, Any] = {}
    navigation: Dict[str, Any] = {}
    tables: Dict[str, Any] = {}

class ThemeAssets(BaseModel):
    """Theme assets (images, icons, etc.)"""
    logo: Optional[str] = None
    favicon: Optional[str] = None
    background_images: List[str] = []
    icons: Dict[str, str] = {}
    illustrations: List[str] = []

class ThemeDefinition(BaseModel):
    """Complete theme definition"""
    id: str
    name: str
    description: str
    category: ThemeCategory
    tags: List[str] = []
    version: str = "1.0.0"
    
    # Design tokens
    colors: ColorPalette
    typography: Typography
    spacing: Spacing = Spacing()
    border_radius: BorderRadius = BorderRadius()
    shadows: Shadows = Shadows()
    
    # Component styles
    component_styles: ComponentStyles = ComponentStyles()
    
    # Assets
    assets: ThemeAssets = ThemeAssets()
    
    # Custom CSS
    custom_css: str = ""
    
    # Responsive breakpoints
    breakpoints: Dict[str, str] = {
        "xs": "0px",
        "sm": "576px", 
        "md": "768px",
        "lg": "992px",
        "xl": "1200px",
        "xxl": "1400px"
    }
    
    # Theme configuration
    supports_dark_mode: bool = False
    supports_rtl: bool = False
    accessibility_features: List[str] = []

class ThemeMarketplaceListing(BaseModel):
    """Marketplace listing for a theme"""
    id: str
    theme_id: str
    title: str
    short_description: str
    long_description: str
    author_id: str
    author_name: str
    
    # Pricing
    license_type: LicenseType
    price: float = 0.0
    currency: str = "USD"
    
    # Media
    preview_images: List[str] = []
    demo_url: Optional[str] = None
    video_url: Optional[str] = None
    
    # Metadata
    status: ThemeStatus = ThemeStatus.DRAFT
    download_count: int = 0
    purchase_count: int = 0
    rating: float = 0.0
    rating_count: int = 0
    
    # Compatibility
    supported_frameworks: List[str] = ["react", "vue", "angular", "vanilla"]
    min_ui_engine_version: str = "1.0.0"
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None
    
    # SEO
    slug: str = ""
    meta_keywords: List[str] = []

class ThemeReview(BaseModel):
    """Theme review/rating"""
    id: str
    theme_id: str
    user_id: str
    username: str
    rating: int  # 1-5
    title: str
    comment: str = ""
    helpful_votes: int = 0
    created_at: datetime
    verified_purchase: bool = False

class ThemePurchase(BaseModel):
    """Theme purchase record"""
    id: str
    theme_id: str
    user_id: str
    price_paid: float
    currency: str
    license_type: LicenseType
    payment_method: str
    transaction_id: str
    purchase_date: datetime
    license_key: Optional[str] = None
    download_count: int = 0
    max_downloads: int = -1  # -1 for unlimited

class ThemeCollection(BaseModel):
    """Curated theme collection"""
    id: str
    name: str
    description: str
    curator_id: str
    curator_name: str
    theme_ids: List[str]
    is_featured: bool = False
    created_at: datetime
    updated_at: datetime

class ThemeMarketplace:
    """Theme marketplace management system"""
    
    def __init__(self):
        self.themes: Dict[str, ThemeDefinition] = {}
        self.listings: Dict[str, ThemeMarketplaceListing] = {}
        self.reviews: Dict[str, List[ThemeReview]] = {}
        self.purchases: Dict[str, ThemePurchase] = {}
        self.collections: Dict[str, ThemeCollection] = {}
        self.featured_themes: List[str] = []
        
        # Initialize with sample themes
        self._initialize_sample_themes()
    
    def _initialize_sample_themes(self):
        """Initialize with sample themes"""
        
        # Modern Dark Theme
        dark_theme = ThemeDefinition(
            id="modern-dark",
            name="Modern Dark",
            description="Sleek dark theme with blue accents",
            category=ThemeCategory.DARK,
            tags=["dark", "modern", "professional"],
            colors=ColorPalette(
                primary="#007acc",
                secondary="#6c757d", 
                accent="#00d4ff",
                background="#1a1a1a",
                surface="#2d2d30",
                text_primary="#ffffff",
                text_secondary="#cccccc",
                success="#28a745",
                warning="#ffc107",
                error="#dc3545",
                info="#17a2b8"
            ),
            typography=Typography(
                font_family_primary="Inter, sans-serif",
                font_family_mono="JetBrains Mono, monospace"
            )
        )
        
        # Clean Light Theme
        light_theme = ThemeDefinition(
            id="clean-light",
            name="Clean Light",
            description="Minimal light theme with subtle shadows",
            category=ThemeCategory.MINIMAL,
            tags=["light", "clean", "minimal"],
            colors=ColorPalette(
                primary="#007acc",
                secondary="#6c757d",
                accent="#ff6b6b",
                background="#ffffff",
                surface="#f8f9fa",
                text_primary="#212529",
                text_secondary="#6c757d",
                success="#28a745",
                warning="#ffc107", 
                error="#dc3545",
                info="#17a2b8"
            ),
            typography=Typography(
                font_family_primary="SF Pro Display, -apple-system, sans-serif"
            )
        )
        
        # Creative Colorful Theme
        colorful_theme = ThemeDefinition(
            id="creative-burst",
            name="Creative Burst",
            description="Vibrant colorful theme for creative projects",
            category=ThemeCategory.COLORFUL,
            tags=["colorful", "creative", "vibrant"],
            colors=ColorPalette(
                primary="#e74c3c",
                secondary="#9b59b6",
                accent="#f39c12", 
                background="#ffffff",
                surface="#fafafa",
                text_primary="#2c3e50",
                text_secondary="#7f8c8d",
                success="#27ae60",
                warning="#f39c12",
                error="#e74c3c",
                info="#3498db"
            ),
            typography=Typography(
                font_family_primary="Poppins, sans-serif"
            )
        )
        
        self.themes[dark_theme.id] = dark_theme
        self.themes[light_theme.id] = light_theme
        self.themes[colorful_theme.id] = colorful_theme
        
        # Create marketplace listings
        self._create_sample_listings()
    
    def _create_sample_listings(self):
        """Create sample marketplace listings"""
        listings_data = [
            {
                "theme_id": "modern-dark",
                "title": "Modern Dark Theme",
                "short_description": "Professional dark theme perfect for development tools",
                "author_name": "UI Engine Team",
                "license_type": LicenseType.FREE,
                "price": 0.0,
                "status": ThemeStatus.APPROVED,
                "rating": 4.8,
                "rating_count": 156,
                "download_count": 2341
            },
            {
                "theme_id": "clean-light", 
                "title": "Clean Light Theme",
                "short_description": "Minimal and clean light theme for business applications",
                "author_name": "UI Engine Team",
                "license_type": LicenseType.PREMIUM,
                "price": 29.99,
                "status": ThemeStatus.APPROVED,
                "rating": 4.6,
                "rating_count": 89,
                "download_count": 1205
            },
            {
                "theme_id": "creative-burst",
                "title": "Creative Burst Theme", 
                "short_description": "Vibrant theme for creative and artistic projects",
                "author_name": "Creative Studios",
                "license_type": LicenseType.PREMIUM,
                "price": 19.99,
                "status": ThemeStatus.APPROVED,
                "rating": 4.3,
                "rating_count": 67,
                "download_count": 892
            }
        ]
        
        for listing_data in listings_data:
            listing = ThemeMarketplaceListing(
                id=str(uuid.uuid4()),
                theme_id=listing_data["theme_id"],
                title=listing_data["title"],
                short_description=listing_data["short_description"],
                long_description=f"Detailed description for {listing_data['title']}",
                author_id=str(uuid.uuid4()),
                author_name=listing_data["author_name"],
                license_type=listing_data["license_type"],
                price=listing_data["price"],
                status=listing_data["status"],
                rating=listing_data["rating"],
                rating_count=listing_data["rating_count"],
                download_count=listing_data["download_count"],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                published_at=datetime.now(),
                slug=listing_data["title"].lower().replace(" ", "-")
            )
            
            self.listings[listing.id] = listing
    
    def create_theme(self, theme_data: Dict[str, Any]) -> str:
        """Create new theme"""
        theme_id = str(uuid.uuid4())
        
        theme = ThemeDefinition(
            id=theme_id,
            **theme_data
        )
        
        self.themes[theme_id] = theme
        return theme_id
    
    def create_listing(self, listing_data: Dict[str, Any]) -> str:
        """Create marketplace listing for theme"""
        listing_id = str(uuid.uuid4())
        
        # Generate slug from title
        slug = listing_data.get("title", "").lower().replace(" ", "-").replace("_", "-")
        slug = "".join(c for c in slug if c.isalnum() or c == "-")
        
        listing = ThemeMarketplaceListing(
            id=listing_id,
            slug=slug,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            **listing_data
        )
        
        self.listings[listing_id] = listing
        return listing_id
    
    def search_themes(self, query: str = "", category: ThemeCategory = None,
                     license_type: LicenseType = None, min_rating: float = 0.0,
                     max_price: float = None, tags: List[str] = None,
                     sort_by: str = "popularity") -> List[ThemeMarketplaceListing]:
        """Search themes in marketplace"""
        results = []
        query_lower = query.lower() if query else ""
        tags = tags or []
        
        for listing in self.listings.values():
            # Status filter - only show approved themes
            if listing.status != ThemeStatus.APPROVED:
                continue
            
            # Category filter
            theme = self.themes.get(listing.theme_id)
            if category and (not theme or theme.category != category):
                continue
            
            # License type filter
            if license_type and listing.license_type != license_type:
                continue
            
            # Rating filter
            if listing.rating < min_rating:
                continue
            
            # Price filter
            if max_price is not None and listing.price > max_price:
                continue
            
            # Tag filter
            if tags and theme:
                if not any(tag in theme.tags for tag in tags):
                    continue
            
            # Text search
            if query_lower:
                searchable_text = f"{listing.title} {listing.short_description} {listing.author_name}".lower()
                if theme:
                    searchable_text += f" {' '.join(theme.tags)}"
                
                if query_lower not in searchable_text:
                    continue
            
            results.append(listing)
        
        # Sort results
        if sort_by == "popularity":
            results.sort(key=lambda l: (l.download_count, l.rating), reverse=True)
        elif sort_by == "rating":
            results.sort(key=lambda l: (l.rating, l.rating_count), reverse=True)
        elif sort_by == "price_low":
            results.sort(key=lambda l: l.price)
        elif sort_by == "price_high":
            results.sort(key=lambda l: l.price, reverse=True)
        elif sort_by == "newest":
            results.sort(key=lambda l: l.published_at or l.created_at, reverse=True)
        
        return results
    
    def get_theme_details(self, theme_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed theme information"""
        theme = self.themes.get(theme_id)
        listing = next((l for l in self.listings.values() if l.theme_id == theme_id), None)
        
        if not theme or not listing:
            return None
        
        reviews = self.reviews.get(theme_id, [])
        
        return {
            "theme": theme.dict(),
            "listing": listing.dict(),
            "reviews": [r.dict() for r in reviews[-5:]],  # Latest 5 reviews
            "review_summary": self._get_review_summary(theme_id)
        }
    
    def add_review(self, theme_id: str, user_id: str, username: str,
                   rating: int, title: str, comment: str = "") -> str:
        """Add theme review"""
        if theme_id not in self.themes:
            raise ValueError("Theme not found")
        
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")
        
        review_id = str(uuid.uuid4())
        review = ThemeReview(
            id=review_id,
            theme_id=theme_id,
            user_id=user_id,
            username=username,
            rating=rating,
            title=title,
            comment=comment,
            created_at=datetime.now()
        )
        
        if theme_id not in self.reviews:
            self.reviews[theme_id] = []
        
        self.reviews[theme_id].append(review)
        
        # Update listing rating
        self._update_listing_rating(theme_id)
        
        return review_id
    
    def _update_listing_rating(self, theme_id: str):
        """Update listing average rating"""
        listing = next((l for l in self.listings.values() if l.theme_id == theme_id), None)
        if not listing:
            return
        
        reviews = self.reviews.get(theme_id, [])
        if not reviews:
            return
        
        total_rating = sum(r.rating for r in reviews)
        listing.rating = round(total_rating / len(reviews), 1)
        listing.rating_count = len(reviews)
        listing.updated_at = datetime.now()
    
    def _get_review_summary(self, theme_id: str) -> Dict[str, Any]:
        """Get review summary statistics"""
        reviews = self.reviews.get(theme_id, [])
        
        if not reviews:
            return {"total": 0, "average": 0.0, "distribution": {}}
        
        total = len(reviews)
        average = sum(r.rating for r in reviews) / total
        
        # Rating distribution
        distribution = {str(i): 0 for i in range(1, 6)}
        for review in reviews:
            distribution[str(review.rating)] += 1
        
        return {
            "total": total,
            "average": round(average, 1),
            "distribution": distribution
        }
    
    def purchase_theme(self, theme_id: str, user_id: str, payment_info: Dict[str, Any]) -> str:
        """Process theme purchase"""
        listing = next((l for l in self.listings.values() if l.theme_id == theme_id), None)
        if not listing:
            raise ValueError("Theme not found")
        
        if listing.license_type == LicenseType.FREE:
            price = 0.0
        else:
            price = listing.price
        
        purchase_id = str(uuid.uuid4())
        license_key = self._generate_license_key(theme_id, user_id) if price > 0 else None
        
        purchase = ThemePurchase(
            id=purchase_id,
            theme_id=theme_id,
            user_id=user_id,
            price_paid=price,
            currency=listing.currency,
            license_type=listing.license_type,
            payment_method=payment_info.get("method", "unknown"),
            transaction_id=payment_info.get("transaction_id", ""),
            purchase_date=datetime.now(),
            license_key=license_key
        )
        
        self.purchases[purchase_id] = purchase
        
        # Update listing stats
        listing.purchase_count += 1
        listing.download_count += 1
        
        return purchase_id
    
    def _generate_license_key(self, theme_id: str, user_id: str) -> str:
        """Generate license key for purchase"""
        data = f"{theme_id}:{user_id}:{datetime.now().isoformat()}"
        hash_obj = hashlib.sha256(data.encode())
        return hash_obj.hexdigest()[:32].upper()
    
    def get_user_purchases(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's theme purchases"""
        user_purchases = []
        
        for purchase in self.purchases.values():
            if purchase.user_id == user_id:
                listing = next((l for l in self.listings.values() 
                              if l.theme_id == purchase.theme_id), None)
                theme = self.themes.get(purchase.theme_id)
                
                purchase_info = {
                    "purchase": purchase.dict(),
                    "theme": theme.dict() if theme else None,
                    "listing": listing.dict() if listing else None
                }
                user_purchases.append(purchase_info)
        
        user_purchases.sort(key=lambda p: p["purchase"]["purchase_date"], reverse=True)
        return user_purchases
    
    def download_theme(self, theme_id: str, user_id: str) -> Dict[str, Any]:
        """Download theme (requires purchase for premium themes)"""
        theme = self.themes.get(theme_id)
        listing = next((l for l in self.listings.values() if l.theme_id == theme_id), None)
        
        if not theme or not listing:
            raise ValueError("Theme not found")
        
        # Check if user has purchased theme (for premium themes)
        if listing.license_type != LicenseType.FREE:
            user_purchase = next((p for p in self.purchases.values() 
                                if p.theme_id == theme_id and p.user_id == user_id), None)
            
            if not user_purchase:
                raise ValueError("Theme not purchased")
            
            # Check download limits
            if user_purchase.max_downloads > 0 and user_purchase.download_count >= user_purchase.max_downloads:
                raise ValueError("Download limit exceeded")
            
            # Increment download count
            user_purchase.download_count += 1
        
        # Generate download package
        download_data = {
            "theme": theme.dict(),
            "license": {
                "type": listing.license_type.value,
                "user_id": user_id,
                "downloaded_at": datetime.now().isoformat()
            },
            "installation_guide": self._generate_installation_guide(theme),
            "changelog": []
        }
        
        return {
            "download_url": f"/downloads/themes/{theme_id}.json",
            "data": download_data,
            "expires_at": (datetime.now() + timedelta(hours=24)).isoformat()
        }
    
    def _generate_installation_guide(self, theme: ThemeDefinition) -> str:
        """Generate installation guide for theme"""
        return f"""
# Installation Guide for {theme.name}

## Installation Steps:

1. Import the theme into your UI Engine project
2. Apply the theme to your components
3. Customize colors and typography as needed
4. Test across different screen sizes

## Customization:

The theme includes:
- Color palette with {len(theme.colors.dict())} colors
- Typography settings
- Component styling
- Responsive breakpoints

## Support:

For support, please contact the theme author or visit the marketplace.
"""
    
    def create_collection(self, name: str, description: str, curator_id: str,
                         curator_name: str, theme_ids: List[str]) -> str:
        """Create theme collection"""
        collection_id = str(uuid.uuid4())
        
        collection = ThemeCollection(
            id=collection_id,
            name=name,
            description=description,
            curator_id=curator_id,
            curator_name=curator_name,
            theme_ids=theme_ids,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.collections[collection_id] = collection
        return collection_id
    
    def get_featured_themes(self, limit: int = 10) -> List[ThemeMarketplaceListing]:
        """Get featured themes"""
        featured = [self.listings[listing_id] for listing_id in self.featured_themes 
                   if listing_id in self.listings]
        
        # If not enough featured themes, add popular ones
        if len(featured) < limit:
            popular = self.search_themes(sort_by="popularity")
            for listing in popular:
                if listing.id not in self.featured_themes and len(featured) < limit:
                    featured.append(listing)
        
        return featured[:limit]
    
    def get_categories_with_stats(self) -> Dict[ThemeCategory, Dict[str, Any]]:
        """Get theme categories with statistics"""
        category_stats = {}
        
        for category in ThemeCategory:
            themes_in_category = [t for t in self.themes.values() if t.category == category]
            listings_in_category = [l for l in self.listings.values() 
                                  if l.status == ThemeStatus.APPROVED and 
                                  l.theme_id in [t.id for t in themes_in_category]]
            
            if themes_in_category:
                avg_rating = sum(l.rating for l in listings_in_category) / len(listings_in_category) if listings_in_category else 0
                total_downloads = sum(l.download_count for l in listings_in_category)
                
                category_stats[category] = {
                    "name": category.value.title(),
                    "theme_count": len(themes_in_category),
                    "avg_rating": round(avg_rating, 1),
                    "total_downloads": total_downloads,
                    "popular_themes": sorted(listings_in_category, 
                                           key=lambda l: l.download_count, reverse=True)[:3]
                }
        
        return category_stats
    
    def export_theme(self, theme_id: str) -> Dict[str, Any]:
        """Export theme for distribution"""
        theme = self.themes.get(theme_id)
        if not theme:
            raise ValueError("Theme not found")
        
        return {
            "theme": theme.dict(),
            "metadata": {
                "exported_at": datetime.now().isoformat(),
                "version": theme.version,
                "export_format_version": "1.0.0"
            }
        }
    
    def import_theme(self, theme_data: Dict[str, Any]) -> str:
        """Import theme from exported data"""
        theme_dict = theme_data.get("theme", {})
        theme = ThemeDefinition(**theme_dict)
        theme.id = str(uuid.uuid4())  # Generate new ID
        
        self.themes[theme.id] = theme
        return theme.id