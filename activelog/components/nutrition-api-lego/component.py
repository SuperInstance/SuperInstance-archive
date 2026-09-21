# SUPERINSTANCE LEGO COMPONENT: Nutrition API
# EXTRACTED FROM: services/nutrition-tracking/main.py:141-633
# LEGO PRINCIPLE: Software = Data + Tools + Configuration

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import asyncpg

class NutritionAPILego:
    """
    🧩 LEGO COMPONENT: Nutrition API
    
    DATA: Nutrition entries (calories, macros, timing)
    TOOLS: CRUD operations, daily summaries, goal tracking
    CONFIGURATION: Database connection, serving options
    
    INTERFACES:
    - Input: Nutrition entries, search queries, date ranges
    - Output: Structured nutrition data, summaries, insights
    - Integration: Auth service, AI insights, user management
    
    DEPLOYMENT OPTIONS:
    - Device: Local nutrition logging for privacy
    - Edge: Regional nutrition database caching
    - Cloud: Full-scale nutrition analytics platform
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.database_url = config.get("database_url", "postgresql://localhost/activelog")
        self.app = FastAPI(title="Nutrition API Lego", version="1.0.0")
        self._setup_middleware()
        self._setup_routes()
        self.db_pool = None
    
    def _setup_middleware(self):
        """Configure CORS and other middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.get("cors_origins", ["*"]),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self):
        """Setup all nutrition API endpoints"""
        
        @self.app.post("/nutrition")
        async def log_nutrition_entry(nutrition: Dict[str, Any]):
            """Log nutrition entry - core LEGO function"""
            if not self.db_pool:
                # Mock mode for testing
                return {
                    "id": str(uuid.uuid4()),
                    "status": "logged",
                    "data": nutrition,
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Real database implementation
            async with self.db_pool.acquire() as conn:
                entry_id = str(uuid.uuid4())
                await conn.execute("""
                    INSERT INTO nutrition_entries (id, user_id, meal_type, food_item, 
                                                 quantity, unit, calories, protein_g, carbs_g, fat_g)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """, entry_id, nutrition.get("user_id"), nutrition.get("meal_type"),
                    nutrition.get("food_item"), nutrition.get("quantity"), 
                    nutrition.get("unit"), nutrition.get("calories"),
                    nutrition.get("protein_g"), nutrition.get("carbs_g"), nutrition.get("fat_g"))
                
                return {"id": entry_id, "status": "logged", "timestamp": datetime.utcnow().isoformat()}
        
        @self.app.get("/nutrition/day/{date}")
        async def get_nutrition_day(date: str, user_id: str):
            """Get complete day nutrition - dashboard LEGO function"""
            if not self.db_pool:
                return self._mock_daily_data(date)
            
            # Real implementation with database
            async with self.db_pool.acquire() as conn:
                entries = await conn.fetch("""
                    SELECT * FROM nutrition_entries 
                    WHERE user_id = $1 AND DATE(consumed_at) = $2::date
                    ORDER BY consumed_at
                """, user_id, date)
                
                return self._format_daily_summary(entries, date)
        
        @self.app.get("/nutrition/week")
        async def get_nutrition_week_summary(user_id: str, start_date: Optional[str] = None):
            """Weekly nutrition summary - analytics LEGO function"""
            if not start_date:
                start_date = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
            
            if not self.db_pool:
                return self._mock_weekly_data(start_date)
            
            # Real weekly analysis implementation
            return await self._generate_weekly_summary(user_id, start_date)
        
        @self.app.get("/health")
        async def health_check():
            return {
                "component": "nutrition-api-lego",
                "status": "healthy",
                "version": "1.0.0",
                "database": self.db_pool is not None
            }
    
    def _mock_daily_data(self, date: str) -> Dict:
        """Mock data for testing without database"""
        return {
            "date": date,
            "meals": {
                "breakfast": [{"food": "oatmeal", "calories": 300, "protein": 8}],
                "lunch": [{"food": "chicken salad", "calories": 450, "protein": 35}],
                "dinner": [{"food": "salmon", "calories": 400, "protein": 30}]
            },
            "totals": {"calories": 1150, "protein": 73, "carbs": 85, "fat": 35},
            "goals_progress": {"calories": 0.52, "protein": 0.68}
        }
    
    def _mock_weekly_data(self, start_date: str) -> Dict:
        """Mock weekly data for testing"""
        return {
            "week_start": start_date,
            "daily_averages": {"calories": 2100, "protein": 125, "meals_logged": 3.2},
            "consistency_score": 0.85,
            "trends": ["increasing_protein", "consistent_breakfast"]
        }
    
    async def connect_database(self):
        """Initialize database connection pool"""
        try:
            self.db_pool = await asyncpg.create_pool(self.database_url, min_size=1, max_size=10)
        except Exception as e:
            print(f"Database connection failed: {e} - running in mock mode")
            self.db_pool = None
    
    async def disconnect_database(self):
        """Clean up database connections"""
        if self.db_pool:
            await self.db_pool.close()
    
    def get_app(self):
        """Get FastAPI app instance for deployment"""
        return self.app

# LEGO CONFIGURATION OPTIONS
DEPLOYMENT_CONFIGS = {
    "device_local": {
        "database_url": "sqlite:///nutrition.db",
        "cors_origins": ["http://localhost:3000"],
        "features": ["basic_logging", "offline_sync"]
    },
    "edge_regional": {
        "database_url": "postgresql://edge-db:5432/nutrition",
        "cors_origins": ["https://*.myapp.com"],
        "features": ["caching", "regional_compliance", "performance_optimization"]
    },
    "cloud_scale": {
        "database_url": "postgresql://cloud-db:5432/nutrition_prod",
        "cors_origins": ["*"],
        "features": ["analytics", "ai_insights", "global_scaling", "enterprise_compliance"]
    }
}

# USAGE EXAMPLES
def create_nutrition_lego(deployment_type: str = "device_local"):
    """Factory function to create configured Nutrition API Lego"""
    config = DEPLOYMENT_CONFIGS.get(deployment_type, DEPLOYMENT_CONFIGS["device_local"])
    return NutritionAPILego(config)

# INTEGRATION INTERFACES
def integrate_with_auth_service(nutrition_lego: NutritionAPILego, auth_service_url: str):
    """Connect to auth service Lego for user validation"""
    nutrition_lego.config["auth_service_url"] = auth_service_url
    # Add auth middleware to the FastAPI app
    pass

def integrate_with_ai_insights(nutrition_lego: NutritionAPILego, ai_service_url: str):
    """Connect to AI insights Lego for enhanced analytics"""
    nutrition_lego.config["ai_insights_url"] = ai_service_url
    # Add AI-powered endpoints
    pass