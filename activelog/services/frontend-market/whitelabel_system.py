"""
White-label Frontend System
Customizable frontend solutions for resellers and partners
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from enum import Enum
import uuid
import asyncio
import logging
import json
import sqlite3

logger = logging.getLogger(__name__)

class WhitelabelTier(str, Enum):
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"

class CustomizationLevel(str, Enum):
    MINIMAL = "minimal"      # Colors and logo only
    STANDARD = "standard"    # Full branding customization
    ADVANCED = "advanced"    # Layout and component changes
    COMPLETE = "complete"    # Full custom implementation

class WhitelabelProduct(BaseModel):
    id: str
    base_frontend_id: str
    partner_id: str
    
    # Product details
    name: str
    description: str
    tier: WhitelabelTier
    customization_level: CustomizationLevel
    
    # Branding customization
    branding: Dict[str, Any] = {}
    theme_config: Dict[str, Any] = {}
    
    # Features and limitations
    enabled_features: List[str] = []
    disabled_features: List[str] = []
    feature_limits: Dict[str, int] = {}
    
    # Deployment
    custom_domain: Optional[str] = None
    deployment_config: Dict[str, Any] = {}
    
    # Business terms
    revenue_split_percentage: float = 70.0  # Partner gets 70%
    minimum_monthly_fee: float = 0.0
    
    # Status
    active: bool = True
    created_at: datetime
    updated_at: datetime

class WhitelabelManager:
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/frontend-market/data/whitelabel_system.db"
        self.init_database()
    
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS whitelabel_products (
                id TEXT PRIMARY KEY,
                base_frontend_id TEXT NOT NULL,
                partner_id TEXT NOT NULL,
                name TEXT NOT NULL,
                tier TEXT NOT NULL,
                customization_level TEXT NOT NULL,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def create_whitelabel_product(self, product_data: Dict[str, Any]) -> WhitelabelProduct:
        """Create a new white-label product"""
        
        product_id = f"WL_{uuid.uuid4().hex[:8].upper()}"
        
        # Default branding configuration
        default_branding = {
            "logo_url": "",
            "company_name": product_data.get("partner_name", ""),
            "primary_color": "#007bff",
            "secondary_color": "#6c757d",
            "accent_color": "#28a745",
            "font_family": "Inter, sans-serif",
            "favicon_url": ""
        }
        
        # Default theme configuration
        default_theme = {
            "layout": "default",
            "sidebar_position": "left",
            "header_style": "modern",
            "color_scheme": "light",
            "border_radius": "medium",
            "shadow_style": "soft"
        }
        
        product = WhitelabelProduct(
            id=product_id,
            base_frontend_id=product_data["base_frontend_id"],
            partner_id=product_data["partner_id"],
            name=product_data["name"],
            description=product_data.get("description", ""),
            tier=WhitelabelTier(product_data.get("tier", "basic")),
            customization_level=CustomizationLevel(product_data.get("customization_level", "standard")),
            branding={**default_branding, **product_data.get("branding", {})},
            theme_config={**default_theme, **product_data.get("theme_config", {})},
            enabled_features=product_data.get("enabled_features", []),
            disabled_features=product_data.get("disabled_features", []),
            feature_limits=product_data.get("feature_limits", {}),
            custom_domain=product_data.get("custom_domain"),
            deployment_config=product_data.get("deployment_config", {}),
            revenue_split_percentage=product_data.get("revenue_split_percentage", 70.0),
            minimum_monthly_fee=product_data.get("minimum_monthly_fee", 0.0),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        await self._store_whitelabel_product(product)
        return product
    
    async def _store_whitelabel_product(self, product: WhitelabelProduct):
        """Store white-label product in database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO whitelabel_products 
            (id, base_frontend_id, partner_id, name, tier, customization_level, data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            product.id, product.base_frontend_id, product.partner_id,
            product.name, product.tier.value, product.customization_level.value,
            product.model_dump_json()
        ))
        
        conn.commit()
        conn.close()

# Global instance
whitelabel_manager = WhitelabelManager()