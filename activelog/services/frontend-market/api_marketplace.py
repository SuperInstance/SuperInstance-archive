"""
Frontend API Marketplace System
Marketplace for frontend APIs and integrations
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

class APICategory(str, Enum):
    AUTHENTICATION = "authentication"
    PAYMENT = "payment"
    ANALYTICS = "analytics"
    COMMUNICATION = "communication"
    STORAGE = "storage"
    AI_ML = "ai_ml"
    SOCIAL = "social"
    MEDIA = "media"
    UTILITIES = "utilities"

class PricingModel(str, Enum):
    FREE = "free"
    FREEMIUM = "freemium"
    SUBSCRIPTION = "subscription"
    PAY_PER_USE = "pay_per_use"
    ONE_TIME = "one_time"

class APIListing(BaseModel):
    id: str
    provider_id: str
    
    # Basic information
    name: str
    description: str
    category: APICategory
    tags: List[str] = []
    
    # API details
    base_url: str
    documentation_url: str
    openapi_spec_url: Optional[str] = None
    sdk_urls: Dict[str, str] = {}  # language -> SDK URL
    
    # Pricing and usage
    pricing_model: PricingModel
    price_per_request: float = 0.0
    monthly_subscription: float = 0.0
    free_tier_limits: Dict[str, int] = {}
    
    # Quality metrics
    uptime_percentage: float = 99.9
    avg_response_time_ms: int = 150
    rate_limits: Dict[str, int] = {}
    
    # Marketplace metadata
    featured: bool = False
    verified: bool = False
    rating: float = 0.0
    review_count: int = 0
    usage_count: int = 0
    
    # Status
    active: bool = True
    created_at: datetime
    updated_at: datetime

class APIMarketplaceManager:
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/frontend-market/data/api_marketplace.db"
        self.init_database()
    
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_listings (
                id TEXT PRIMARY KEY,
                provider_id TEXT NOT NULL,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                pricing_model TEXT NOT NULL,
                rating REAL DEFAULT 0.0,
                usage_count INTEGER DEFAULT 0,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()

# Global instance
api_marketplace_manager = APIMarketplaceManager()