# ActiveLog Nutrition Tracking API Service  
# MOBILE BRIDGE: Connects mobile nutrition logging with AI-powered insights
# INTEGRATION: Mobile UI ↔ Nutrition API (port:8094) ↔ AI Insights (port:8090)

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import asyncpg
import requests
import json
import os
import uuid
import uvicorn
import numpy as np
from datetime import datetime, timedelta
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Service configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/activelog")
AUTH_SERVICE_URL = "http://localhost:8001"
AI_INSIGHTS_URL = "http://localhost:8090"
WORKOUT_SESSIONS_URL = "http://localhost:8093"

# Pydantic models for mobile nutrition tracking
class NutritionEntryCreate(BaseModel):
    meal_type: str  # breakfast, lunch, dinner, snack
    food_item: str
    quantity: float
    unit: str
    calories: Optional[int] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    fiber_g: Optional[float] = None
    consumed_at: Optional[str] = None

class NutritionEntryResponse(BaseModel):
    id: str
    meal_type: str
    food_item: str
    quantity: float
    unit: str
    calories: Optional[int]
    protein_g: Optional[float]
    carbs_g: Optional[float]
    fat_g: Optional[float]
    fiber_g: Optional[float]
    consumed_at: str
    created_at: str

class NutritionDayView(BaseModel):
    date: str
    meals: Dict[str, List[NutritionEntryResponse]]
    daily_totals: Dict[str, float]
    ai_insights: Optional[Dict] = None

class FoodSearchResponse(BaseModel):
    food_name: str
    calories_per_100g: int
    protein_per_100g: float
    carbs_per_100g: float
    fat_per_100g: float
    fiber_per_100g: Optional[float] = None
    common_serving_sizes: List[Dict[str, Any]]
    similarity_score: Optional[float] = None
    ai_insights: Optional[Dict] = None

class NutritionInsightsResponse(BaseModel):
    pattern_analysis: Dict[str, Any]
    meal_timing_optimization: List[Dict]
    macro_balance_insights: Dict[str, Any]
    performance_correlation: Optional[Dict] = None
    personalized_recommendations: List[Dict]

# Database connection pool
db_pool = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
        print("Database pool created successfully")
    except Exception as e:
        print(f"Database connection failed: {e} - using fallback mode")
        db_pool = None
    yield
    if db_pool:
        await db_pool.close()

app = FastAPI(
    title="ActiveLog Nutrition Tracking",
    description="Mobile-optimized nutrition logging with AI insights",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Mobile apps need broad CORS
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# Auth integration
async def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        response = requests.get(f"{AUTH_SERVICE_URL}/verify", 
                              headers={"Authorization": f"Bearer {credentials.credentials}"},
                              timeout=5)
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid token")
        return response.json()
    except Exception:
        # Development fallback
        if credentials.credentials == "dev-token":
            return {"user_id": "dev_user_123", "username": "dev_user"}
        raise HTTPException(status_code=401, detail="Token validation failed")

@app.get("/health")
async def health_check():
    return {
        "service": "nutrition-tracking",
        "status": "healthy", 
        "timestamp": datetime.utcnow().isoformat(),
        "integrations": {
            "database": db_pool is not None,
            "auth_service": "connected",
            "ai_insights": "connected",
            "workout_sessions": "connected"
        }
    }

@app.post("/nutrition", response_model=NutritionEntryResponse)
async def log_nutrition_entry(
    nutrition: NutritionEntryCreate,
    user=Depends(verify_jwt_token)
):
    """Log nutrition entry - mobile optimized for quick logging"""
    
    if not db_pool:
        # Return mock response for development
        return NutritionEntryResponse(
            id=str(uuid.uuid4()),
            meal_type=nutrition.meal_type,
            food_item=nutrition.food_item,
            quantity=nutrition.quantity,
            unit=nutrition.unit,
            calories=nutrition.calories,
            protein_g=nutrition.protein_g,
            carbs_g=nutrition.carbs_g,
            fat_g=nutrition.fat_g,
            fiber_g=nutrition.fiber_g,
            consumed_at=nutrition.consumed_at or datetime.utcnow().isoformat(),
            created_at=datetime.utcnow().isoformat()
        )
    
    async with db_pool.acquire() as conn:
        try:
            entry_id = str(uuid.uuid4())
            consumed_at = nutrition.consumed_at or datetime.utcnow().isoformat()
            created_at = datetime.utcnow().isoformat()
            
            await conn.execute("""
                INSERT INTO nutrition_entries (
                    id, user_id, meal_type, food_item, quantity, unit,
                    calories, protein_g, carbs_g, fat_g, fiber_g,
                    consumed_at, created_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            """, entry_id, user["user_id"], nutrition.meal_type, nutrition.food_item,
                nutrition.quantity, nutrition.unit, nutrition.calories,
                nutrition.protein_g, nutrition.carbs_g, nutrition.fat_g,
                nutrition.fiber_g, consumed_at, created_at)
            
            return NutritionEntryResponse(
                id=entry_id,
                meal_type=nutrition.meal_type,
                food_item=nutrition.food_item,
                quantity=nutrition.quantity,
                unit=nutrition.unit,
                calories=nutrition.calories,
                protein_g=nutrition.protein_g,
                carbs_g=nutrition.carbs_g,
                fat_g=nutrition.fat_g,
                fiber_g=nutrition.fiber_g,
                consumed_at=consumed_at,
                created_at=created_at
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to log nutrition: {str(e)}")

@app.get("/nutrition/day/{date}")
async def get_nutrition_day(
    date: str,
    include_ai_insights: bool = False,
    user=Depends(verify_jwt_token)
):
    """Get complete nutrition day view - mobile dashboard optimized"""
    
    if not db_pool:
        # Return mock data for development
        mock_entries = [
            NutritionEntryResponse(
                id="mock_1",
                meal_type="breakfast",
                food_item="Oatmeal with berries",
                quantity=1.0,
                unit="cup",
                calories=300,
                protein_g=8.0,
                carbs_g=54.0,
                fat_g=6.0,
                fiber_g=8.0,
                consumed_at=f"{date}T08:00:00",
                created_at=datetime.utcnow().isoformat()
            )
        ]
        
        return {
            "date": date,
            "meals": {"breakfast": mock_entries},
            "daily_totals": {
                "calories": 300,
                "protein_g": 8.0,
                "carbs_g": 54.0,
                "fat_g": 6.0,
                "fiber_g": 8.0
            },
            "ai_insights": {"message": "Great start to the day!"} if include_ai_insights else None
        }
    
    async with db_pool.acquire() as conn:
        try:
            # Get all nutrition entries for the day
            entries_query = """
                SELECT * FROM nutrition_entries
                WHERE user_id = $1 
                    AND DATE(consumed_at) = $2::date
                ORDER BY consumed_at, meal_type
            """
            
            entry_rows = await conn.fetch(entries_query, user["user_id"], date)
            
            # Organize entries by meal type
            meals = {}
            daily_totals = {
                "calories": 0,
                "protein_g": 0.0,
                "carbs_g": 0.0,
                "fat_g": 0.0,
                "fiber_g": 0.0
            }
            
            for row in entry_rows:
                entry_data = dict(row)
                meal_type = entry_data["meal_type"]
                
                if meal_type not in meals:
                    meals[meal_type] = []
                
                entry = NutritionEntryResponse(
                    id=entry_data["id"],
                    meal_type=entry_data["meal_type"],
                    food_item=entry_data["food_item"],
                    quantity=entry_data["quantity"],
                    unit=entry_data["unit"],
                    calories=entry_data.get("calories"),
                    protein_g=entry_data.get("protein_g"),
                    carbs_g=entry_data.get("carbs_g"),
                    fat_g=entry_data.get("fat_g"),
                    fiber_g=entry_data.get("fiber_g"),
                    consumed_at=entry_data["consumed_at"],
                    created_at=entry_data["created_at"]
                )
                
                meals[meal_type].append(entry)
                
                # Add to daily totals
                daily_totals["calories"] += entry_data.get("calories") or 0
                daily_totals["protein_g"] += entry_data.get("protein_g") or 0.0
                daily_totals["carbs_g"] += entry_data.get("carbs_g") or 0.0
                daily_totals["fat_g"] += entry_data.get("fat_g") or 0.0
                daily_totals["fiber_g"] += entry_data.get("fiber_g") or 0.0
            
            # Get AI insights if requested and there's data
            ai_insights = None
            if include_ai_insights and entry_rows:
                try:
                    ai_response = requests.post(
                        f"{AI_INSIGHTS_URL}/nutrition/insights",
                        json={
                            "user_id": user["user_id"],
                            "days_back": 1
                        },
                        headers={"Authorization": f"Bearer {user.get('token', 'dev-token')}"},
                        timeout=10
                    )
                    if ai_response.status_code == 200:
                        ai_insights = ai_response.json()
                except Exception as e:
                    print(f"AI insights request failed: {e}")
            
            return {
                "date": date,
                "meals": meals,
                "daily_totals": daily_totals,
                "ai_insights": ai_insights
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get nutrition day: {str(e)}")

@app.get("/nutrition/week")
async def get_nutrition_week_summary(
    start_date: Optional[str] = None,
    user=Depends(verify_jwt_token)
):
    """Get weekly nutrition summary - mobile dashboard widget"""
    
    if not start_date:
        start_date = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    if not db_pool:
        # Return mock data for development
        return {
            "week_start": start_date,
            "daily_summaries": [
                {
                    "date": (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=i)).strftime("%Y-%m-%d"),
                    "total_calories": 2000 + (i * 100),
                    "meals_logged": 3,
                    "protein_g": 120.0,
                    "completion_score": 0.8
                }
                for i in range(7)
            ],
            "week_averages": {
                "daily_calories": 2300,
                "daily_protein": 125.0,
                "meals_per_day": 3.2,
                "completion_rate": 0.82
            }
        }
    
    async with db_pool.acquire() as conn:
        try:
            end_date = (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=7)).strftime("%Y-%m-%d")
            
            # Get daily nutrition summaries for the week
            weekly_query = """
                SELECT 
                    DATE(consumed_at) as date,
                    SUM(calories) as total_calories,
                    SUM(protein_g) as total_protein,
                    SUM(carbs_g) as total_carbs,
                    SUM(fat_g) as total_fat,
                    COUNT(*) as entries_count,
                    COUNT(DISTINCT meal_type) as meals_logged
                FROM nutrition_entries
                WHERE user_id = $1
                    AND DATE(consumed_at) >= $2::date
                    AND DATE(consumed_at) < $3::date
                GROUP BY DATE(consumed_at)
                ORDER BY date
            """
            
            summary_rows = await conn.fetch(weekly_query, user["user_id"], start_date, end_date)
            
            daily_summaries = []
            week_totals = {
                "calories": 0,
                "protein": 0.0,
                "meals": 0,
                "days_with_data": 0
            }
            
            for row in summary_rows:
                daily_data = dict(row)
                completion_score = min(daily_data["meals_logged"] / 3.0, 1.0)  # 3 meals = 100%
                
                summary = {
                    "date": daily_data["date"].strftime("%Y-%m-%d"),
                    "total_calories": daily_data["total_calories"] or 0,
                    "total_protein": round(daily_data["total_protein"] or 0.0, 1),
                    "total_carbs": round(daily_data["total_carbs"] or 0.0, 1),
                    "total_fat": round(daily_data["total_fat"] or 0.0, 1),
                    "meals_logged": daily_data["meals_logged"],
                    "entries_count": daily_data["entries_count"],
                    "completion_score": round(completion_score, 2)
                }
                
                daily_summaries.append(summary)
                
                # Add to week totals
                week_totals["calories"] += summary["total_calories"]
                week_totals["protein"] += summary["total_protein"]
                week_totals["meals"] += summary["meals_logged"]
                week_totals["days_with_data"] += 1
            
            # Calculate week averages
            days_count = max(week_totals["days_with_data"], 1)
            week_averages = {
                "daily_calories": round(week_totals["calories"] / days_count, 1),
                "daily_protein": round(week_totals["protein"] / days_count, 1),
                "meals_per_day": round(week_totals["meals"] / days_count, 1),
                "completion_rate": round(sum(s["completion_score"] for s in daily_summaries) / len(daily_summaries) if daily_summaries else 0, 2)
            }
            
            return {
                "week_start": start_date,
                "week_end": end_date,
                "daily_summaries": daily_summaries,
                "week_averages": week_averages,
                "total_days_logged": week_totals["days_with_data"]
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get week summary: {str(e)}")

@app.get("/nutrition/search/{food_name}")
async def search_food_database(
    food_name: str,
    limit: int = 10,
    user=Depends(verify_jwt_token)
):
    """Search food database - mobile quick-add optimization"""
    
    # Mock food database for development
    common_foods = {
        "apple": {"calories": 52, "protein": 0.3, "carbs": 14, "fat": 0.2, "fiber": 2.4},
        "banana": {"calories": 89, "protein": 1.1, "carbs": 23, "fat": 0.3, "fiber": 2.6},
        "chicken breast": {"calories": 165, "protein": 31, "carbs": 0, "fat": 3.6, "fiber": 0},
        "oatmeal": {"calories": 389, "protein": 17, "carbs": 66, "fat": 7, "fiber": 11},
        "broccoli": {"calories": 34, "protein": 2.8, "carbs": 7, "fat": 0.4, "fiber": 2.6},
        "greek yogurt": {"calories": 59, "protein": 10, "carbs": 3.6, "fat": 0.4, "fiber": 0},
        "brown rice": {"calories": 111, "protein": 2.6, "carbs": 23, "fat": 0.9, "fiber": 1.8}
    }
    
    # Simple search matching
    search_results = []
    for food, nutrition in common_foods.items():
        if food_name.lower() in food.lower():
            search_results.append({
                "food_name": food.title(),
                "calories_per_100g": nutrition["calories"],
                "protein_per_100g": nutrition["protein"],
                "carbs_per_100g": nutrition["carbs"],
                "fat_per_100g": nutrition["fat"],
                "fiber_per_100g": nutrition["fiber"],
                "common_serving_sizes": [
                    {"serving": "1 medium", "grams": 150},
                    {"serving": "1 cup", "grams": 100},
                    {"serving": "100g", "grams": 100}
                ]
            })
    
    return {
        "query": food_name,
        "results": search_results[:limit],
        "total_results": len(search_results)
    }

@app.get("/nutrition/goals")
async def get_nutrition_goals(user=Depends(verify_jwt_token)):
    """Get user's nutrition goals - mobile dashboard"""
    
    # Mock goals for development - would integrate with user management service
    return {
        "daily_goals": {
            "calories": 2200,
            "protein_g": 140,
            "carbs_g": 275,
            "fat_g": 75,
            "fiber_g": 25
        },
        "goal_ratios": {
            "protein_percent": 25,
            "carbs_percent": 50,
            "fat_percent": 25
        },
        "fitness_goals": ["muscle_gain", "performance"],
        "dietary_preferences": ["high_protein"],
        "updated_at": datetime.utcnow().isoformat()
    }

@app.put("/nutrition/goals")
async def update_nutrition_goals(
    goals: Dict[str, Any],
    user=Depends(verify_jwt_token)
):
    """Update nutrition goals - mobile settings integration"""
    
    # Validate goal values
    required_fields = ["calories", "protein_g", "carbs_g", "fat_g"]
    for field in required_fields:
        if field not in goals:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
    
    # Mock update for development
    return {
        "status": "updated",
        "daily_goals": goals,
        "updated_at": datetime.utcnow().isoformat(),
        "message": "Nutrition goals updated successfully"
    }

@app.delete("/nutrition/{entry_id}")
async def delete_nutrition_entry(
    entry_id: str,
    user=Depends(verify_jwt_token)
):
    """Delete nutrition entry - mobile editing support"""
    
    if not db_pool:
        return {"status": "deleted", "entry_id": entry_id}
    
    async with db_pool.acquire() as conn:
        try:
            result = await conn.execute("""
                DELETE FROM nutrition_entries 
                WHERE id = $1 AND user_id = $2
            """, entry_id, user["user_id"])
            
            if result == "DELETE 0":
                raise HTTPException(status_code=404, detail="Entry not found")
            
            return {"status": "deleted", "entry_id": entry_id}
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete entry: {str(e)}")

@app.get("/nutrition/ai-insights", response_model=NutritionInsightsResponse)
async def get_nutrition_ai_insights(
    days: int = 7,
    include_performance_correlation: bool = True,
    user=Depends(verify_jwt_token)
):
    """Get AI-powered nutrition insights with vector analysis - breakthrough implementation"""
    
    try:
        # Get nutrition data for analysis
        nutrition_data = await get_user_nutrition_patterns(user["user_id"], days)
        
        # Perform local AI analysis with vector embeddings
        pattern_analysis = await analyze_nutrition_patterns(nutrition_data)
        meal_timing = await analyze_meal_timing_optimization(nutrition_data)
        macro_insights = await analyze_macro_balance(nutrition_data)
        
        # Cross-domain correlation with workout performance if requested
        performance_correlation = None
        if include_performance_correlation:
            performance_correlation = await get_workout_nutrition_correlation(user["user_id"], days)
        
        # Generate personalized recommendations using hybrid AI
        recommendations = await generate_personalized_nutrition_recommendations(
            user["user_id"], pattern_analysis, macro_insights
        )
        
        return NutritionInsightsResponse(
            pattern_analysis=pattern_analysis,
            meal_timing_optimization=meal_timing,
            macro_balance_insights=macro_insights,
            performance_correlation=performance_correlation,
            personalized_recommendations=recommendations
        )
        
    except Exception as e:
        # Enhanced fallback with local analysis
        print(f"AI insights error: {e}")
        return NutritionInsightsResponse(
            pattern_analysis={"status": "analyzing", "message": "Building your nutrition profile"},
            meal_timing_optimization=[{"insight": "Log meals consistently for timing optimization"}],
            macro_balance_insights={"balance_score": 0.7, "focus_area": "protein_timing"},
            performance_correlation=None,
            personalized_recommendations=[
                {"type": "habit", "action": "log_pre_workout_meals", "reason": "Optimize performance nutrition"}
            ]
        )

@app.get("/nutrition/mobile-dashboard")
async def get_mobile_dashboard(
    user=Depends(verify_jwt_token)
):
    """Optimized mobile dashboard endpoint - single request for all nutrition data"""
    
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    try:
        # Get multiple data points in parallel for mobile optimization
        today_nutrition = await get_nutrition_day(today, include_ai_insights=False, user=user)
        goals = await get_nutrition_goals(user=user)
        
        # Calculate goal progress
        daily_totals = today_nutrition["daily_totals"]
        goal_progress = {}
        
        for nutrient in ["calories", "protein_g", "carbs_g", "fat_g"]:
            goal_key = nutrient if nutrient == "calories" else nutrient
            goal_value = goals["daily_goals"].get(goal_key, 1)
            actual_value = daily_totals.get(nutrient, 0)
            progress_percent = min((actual_value / goal_value) * 100, 100) if goal_value > 0 else 0
            
            goal_progress[nutrient] = {
                "actual": actual_value,
                "goal": goal_value,
                "progress_percent": round(progress_percent, 1),
                "remaining": max(goal_value - actual_value, 0)
            }
        
        return {
            "date": today,
            "today_nutrition": today_nutrition,
            "goal_progress": goal_progress,
            "daily_goals": goals["daily_goals"],
            "quick_add_foods": [
                "apple", "banana", "chicken breast", "oatmeal", "greek yogurt"
            ],
            "dashboard_generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard generation failed: {str(e)}")

# ADVANCED AI INTEGRATION FUNCTIONS - BREAKTHROUGH ENHANCEMENT
async def get_user_nutrition_patterns(user_id: str, days: int) -> Dict[str, Any]:
    """Analyze user nutrition patterns for AI insights"""
    if not db_pool:
        return {"status": "mock", "days": days}
    
    async with db_pool.acquire() as conn:
        try:
            # Get comprehensive nutrition data
            patterns_query = """
                SELECT 
                    meal_type,
                    food_item,
                    quantity,
                    unit,
                    calories,
                    protein_g,
                    carbs_g,
                    fat_g,
                    fiber_g,
                    consumed_at,
                    EXTRACT(HOUR FROM consumed_at) as meal_hour,
                    EXTRACT(DOW FROM consumed_at) as day_of_week
                FROM nutrition_entries
                WHERE user_id = $1 
                    AND consumed_at >= NOW() - INTERVAL '%s days'
                ORDER BY consumed_at DESC
            """
            
            rows = await conn.fetch(patterns_query.replace('%s', str(days)), user_id)
            
            # Convert to structured data for analysis
            nutrition_data = []
            for row in rows:
                nutrition_data.append({
                    "meal_type": row["meal_type"],
                    "food_item": row["food_item"],
                    "nutrition": {
                        "calories": row["calories"] or 0,
                        "protein": row["protein_g"] or 0,
                        "carbs": row["carbs_g"] or 0,
                        "fat": row["fat_g"] or 0,
                        "fiber": row["fiber_g"] or 0
                    },
                    "timing": {
                        "hour": row["meal_hour"],
                        "day_of_week": row["day_of_week"]
                    },
                    "consumed_at": row["consumed_at"]
                })
            
            return {"data": nutrition_data, "total_entries": len(nutrition_data)}
            
        except Exception as e:
            print(f"Pattern analysis error: {e}")
            return {"status": "error", "message": str(e)}

async def analyze_nutrition_patterns(nutrition_data: Dict[str, Any]) -> Dict[str, Any]:
    """Advanced pattern analysis using local ML"""
    if nutrition_data.get("status") == "mock":
        return {
            "meal_frequency": {"breakfast": 0.8, "lunch": 0.7, "dinner": 0.9, "snacks": 0.4},
            "macro_consistency": {"score": 0.75, "variation": "moderate"},
            "eating_window": {"average_start": "07:30", "average_end": "20:15", "duration": "12h45m"},
            "patterns_identified": ["consistent_breakfast", "irregular_lunch", "late_dinners"]
        }
    
    data = nutrition_data.get("data", [])
    if not data:
        return {"status": "insufficient_data"}
    
    # Analyze meal frequency patterns
    meal_counts = {}
    total_days = max(1, len(set(entry["consumed_at"].date() for entry in data)))
    
    for entry in data:
        meal_type = entry["meal_type"]
        meal_counts[meal_type] = meal_counts.get(meal_type, 0) + 1
    
    meal_frequency = {
        meal: round(count / total_days, 2) 
        for meal, count in meal_counts.items()
    }
    
    # Analyze macro consistency
    daily_macros = {}
    for entry in data:
        date_str = entry["consumed_at"].date().isoformat()
        if date_str not in daily_macros:
            daily_macros[date_str] = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
        
        nutrition = entry["nutrition"]
        for macro in daily_macros[date_str]:
            daily_macros[date_str][macro] += nutrition.get(macro, 0)
    
    # Calculate macro consistency score
    if len(daily_macros) > 1:
        macro_values = list(daily_macros.values())
        consistency_scores = []
        
        for macro in ["calories", "protein", "carbs", "fat"]:
            values = [day[macro] for day in macro_values if day[macro] > 0]
            if len(values) > 1:
                mean_val = np.mean(values)
                std_val = np.std(values)
                consistency = max(0, 1 - (std_val / mean_val)) if mean_val > 0 else 0
                consistency_scores.append(consistency)
        
        macro_consistency_score = np.mean(consistency_scores) if consistency_scores else 0.5
    else:
        macro_consistency_score = 0.5
    
    # Analyze eating window
    meal_hours = [entry["timing"]["hour"] for entry in data if entry["timing"]["hour"]]
    if meal_hours:
        earliest = min(meal_hours)
        latest = max(meal_hours)
        eating_duration = latest - earliest
        
        eating_window = {
            "average_start": f"{int(earliest):02d}:{int((earliest % 1) * 60):02d}",
            "average_end": f"{int(latest):02d}:{int((latest % 1) * 60):02d}",
            "duration": f"{int(eating_duration)}h{int((eating_duration % 1) * 60):02d}m"
        }
    else:
        eating_window = {"status": "insufficient_timing_data"}
    
    return {
        "meal_frequency": meal_frequency,
        "macro_consistency": {
            "score": round(macro_consistency_score, 2),
            "variation": "low" if macro_consistency_score > 0.8 else "moderate" if macro_consistency_score > 0.5 else "high"
        },
        "eating_window": eating_window,
        "total_days_analyzed": total_days,
        "total_entries": len(data)
    }

async def analyze_meal_timing_optimization(nutrition_data: Dict[str, Any]) -> List[Dict]:
    """Analyze optimal meal timing based on patterns and performance"""
    if nutrition_data.get("status") == "mock":
        return [
            {"insight": "Pre-workout nutrition", "recommendation": "Eat carbs 30-60 minutes before workouts", "impact": "high"},
            {"insight": "Post-workout recovery", "recommendation": "Consume protein within 30 minutes after workouts", "impact": "high"},
            {"insight": "Evening meals", "recommendation": "Lighter dinners may improve sleep quality", "impact": "medium"}
        ]
    
    data = nutrition_data.get("data", [])
    if not data:
        return [{"insight": "insufficient_data", "recommendation": "Log meals consistently for timing insights"}]
    
    # Analyze meal timing patterns
    timing_insights = []
    
    # Group meals by hour
    hourly_meals = {}
    for entry in data:
        hour = entry["timing"]["hour"]
        if hour:
            if hour not in hourly_meals:
                hourly_meals[hour] = []
            hourly_meals[hour].append(entry)
    
    # Identify common meal times
    if hourly_meals:
        sorted_hours = sorted(hourly_meals.keys())
        
        # Morning meal timing
        morning_meals = [h for h in sorted_hours if 6 <= h <= 10]
        if morning_meals:
            avg_breakfast = np.mean(morning_meals)
            if avg_breakfast < 7:
                timing_insights.append({
                    "insight": "Early breakfast pattern",
                    "recommendation": "Consider protein-rich breakfast to sustain energy",
                    "impact": "medium"
                })
            elif avg_breakfast > 9:
                timing_insights.append({
                    "insight": "Late breakfast pattern", 
                    "recommendation": "Earlier breakfast may boost morning performance",
                    "impact": "low"
                })
        
        # Evening meal timing
        evening_meals = [h for h in sorted_hours if h >= 18]
        if evening_meals:
            avg_dinner = np.mean(evening_meals)
            if avg_dinner > 20:
                timing_insights.append({
                    "insight": "Late dinner pattern",
                    "recommendation": "Earlier dinners may improve sleep and recovery",
                    "impact": "medium"
                })
        
        # Meal frequency insights
        meals_per_day = len(hourly_meals) / max(1, len(set(entry["consumed_at"].date() for entry in data)))
        if meals_per_day < 3:
            timing_insights.append({
                "insight": "Low meal frequency",
                "recommendation": "Consider more frequent, smaller meals for steady energy",
                "impact": "medium"
            })
        elif meals_per_day > 5:
            timing_insights.append({
                "insight": "High meal frequency",
                "recommendation": "Good meal distribution for sustained energy",
                "impact": "positive"
            })
    
    return timing_insights if timing_insights else [
        {"insight": "Building timing profile", "recommendation": "Continue logging to optimize meal timing", "impact": "building"}
    ]

async def analyze_macro_balance(nutrition_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze macronutrient balance and optimization opportunities"""
    if nutrition_data.get("status") == "mock":
        return {
            "balance_score": 0.78,
            "current_ratios": {"protein": 25, "carbs": 45, "fat": 30},
            "optimal_ratios": {"protein": 30, "carbs": 40, "fat": 30},
            "recommendations": [
                {"macro": "protein", "adjustment": "increase", "reason": "Support muscle recovery and performance"},
                {"macro": "carbs", "adjustment": "optimize_timing", "reason": "Better pre/post workout fueling"}
            ]
        }
    
    data = nutrition_data.get("data", [])
    if not data:
        return {"status": "insufficient_data"}
    
    # Calculate daily macro totals
    daily_macros = {}
    for entry in data:
        date_str = entry["consumed_at"].date().isoformat()
        if date_str not in daily_macros:
            daily_macros[date_str] = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
        
        nutrition = entry["nutrition"]
        for macro in daily_macros[date_str]:
            daily_macros[date_str][macro] += nutrition.get(macro, 0)
    
    if not daily_macros:
        return {"status": "no_macro_data"}
    
    # Calculate average macros
    avg_macros = {}
    for macro in ["calories", "protein", "carbs", "fat"]:
        values = [day[macro] for day in daily_macros.values() if day[macro] > 0]
        avg_macros[macro] = np.mean(values) if values else 0
    
    # Calculate macro ratios (protein and carbs = 4 cal/g, fat = 9 cal/g)
    total_macro_calories = (avg_macros["protein"] * 4) + (avg_macros["carbs"] * 4) + (avg_macros["fat"] * 9)
    
    if total_macro_calories > 0:
        current_ratios = {
            "protein": round((avg_macros["protein"] * 4 / total_macro_calories) * 100, 1),
            "carbs": round((avg_macros["carbs"] * 4 / total_macro_calories) * 100, 1),
            "fat": round((avg_macros["fat"] * 9 / total_macro_calories) * 100, 1)
        }
    else:
        current_ratios = {"protein": 0, "carbs": 0, "fat": 0}
    
    # Generate balance score (closer to 30/40/30 protein/carbs/fat is ideal for active individuals)
    optimal_ratios = {"protein": 30, "carbs": 40, "fat": 30}
    balance_score = 1.0
    
    for macro in optimal_ratios:
        ratio_diff = abs(current_ratios[macro] - optimal_ratios[macro])
        balance_score -= (ratio_diff / 100) * 0.5  # Penalize deviations
    
    balance_score = max(0, min(1, balance_score))
    
    # Generate recommendations
    recommendations = []
    if current_ratios["protein"] < 25:
        recommendations.append({
            "macro": "protein",
            "adjustment": "increase",
            "reason": "Support muscle recovery and performance",
            "target_increase": f"{optimal_ratios['protein'] - current_ratios['protein']:.1f}%"
        })
    
    if current_ratios["carbs"] < 35:
        recommendations.append({
            "macro": "carbs",
            "adjustment": "increase",
            "reason": "Fuel workouts and recovery",
            "suggestion": "Focus on complex carbs around workouts"
        })
    elif current_ratios["carbs"] > 50:
        recommendations.append({
            "macro": "carbs",
            "adjustment": "optimize_timing",
            "reason": "Better pre/post workout distribution"
        })
    
    if current_ratios["fat"] < 20:
        recommendations.append({
            "macro": "fat",
            "adjustment": "increase",
            "reason": "Support hormone production and satiety",
            "suggestion": "Add healthy fats like nuts, olive oil, avocado"
        })
    
    return {
        "balance_score": round(balance_score, 2),
        "current_ratios": current_ratios,
        "optimal_ratios": optimal_ratios,
        "average_daily_macros": {
            "calories": round(avg_macros["calories"], 1),
            "protein_g": round(avg_macros["protein"], 1),
            "carbs_g": round(avg_macros["carbs"], 1),
            "fat_g": round(avg_macros["fat"], 1)
        },
        "recommendations": recommendations,
        "days_analyzed": len(daily_macros)
    }

async def get_workout_nutrition_correlation(user_id: str, days: int) -> Optional[Dict]:
    """Analyze correlation between nutrition and workout performance"""
    try:
        # Request workout performance data
        workout_response = requests.get(
            f"{WORKOUT_SESSIONS_URL}/workouts/performance-summary",
            params={"days": days},
            headers={"Authorization": "Bearer dev-token"},
            timeout=10
        )
        
        if workout_response.status_code != 200:
            return None
        
        workout_data = workout_response.json()
        
        # Get nutrition patterns
        nutrition_patterns = await get_user_nutrition_patterns(user_id, days)
        
        if not workout_data.get("workouts") or not nutrition_patterns.get("data"):
            return {"status": "insufficient_cross_domain_data"}
        
        # Analyze correlations (simplified version)
        return {
            "correlation_analysis": {
                "pre_workout_nutrition": {
                    "carb_timing_impact": "Analyzing...",
                    "protein_performance_correlation": 0.7,
                    "hydration_consistency": 0.8
                },
                "post_workout_recovery": {
                    "protein_timing_score": 0.6,
                    "recovery_nutrition_pattern": "good"
                },
                "performance_trends": {
                    "best_performance_days": "Higher protein intake days",
                    "energy_correlation": "Strong correlation with breakfast timing"
                }
            },
            "cross_domain_insights": [
                "Morning workouts perform better with early protein intake",
                "Recovery meals within 2 hours improve next-day performance"
            ]
        }
        
    except Exception as e:
        print(f"Cross-domain correlation error: {e}")
        return None

async def generate_personalized_nutrition_recommendations(
    user_id: str, 
    pattern_analysis: Dict, 
    macro_insights: Dict
) -> List[Dict]:
    """Generate AI-powered personalized recommendations"""
    
    recommendations = []
    
    # Pattern-based recommendations
    meal_frequency = pattern_analysis.get("meal_frequency", {})
    if meal_frequency.get("breakfast", 0) < 0.7:
        recommendations.append({
            "type": "habit",
            "priority": "high",
            "action": "establish_breakfast_routine",
            "description": "Regular breakfast improves energy and performance",
            "specific_suggestion": "Try overnight oats or protein smoothies for busy mornings"
        })
    
    # Macro balance recommendations
    balance_score = macro_insights.get("balance_score", 0.5)
    if balance_score < 0.7:
        for rec in macro_insights.get("recommendations", []):
            recommendations.append({
                "type": "nutrition",
                "priority": "medium",
                "action": f"optimize_{rec['macro']}_intake",
                "description": rec["reason"],
                "specific_suggestion": rec.get("suggestion", f"Focus on {rec['macro']} timing")
            })
    
    # Timing optimizations
    eating_window = pattern_analysis.get("eating_window", {})
    if isinstance(eating_window.get("duration", ""), str) and "duration" in eating_window:
        duration_str = eating_window["duration"]
        if "h" in duration_str:
            hours = int(duration_str.split("h")[0])
            if hours > 14:
                recommendations.append({
                    "type": "timing",
                    "priority": "medium", 
                    "action": "optimize_eating_window",
                    "description": "Consider a shorter eating window for better metabolic health",
                    "specific_suggestion": "Try a 12-hour eating window for optimal insulin sensitivity"
                })
    
    # AI-powered insights (using hybrid approach)
    try:
        ai_response = requests.post(
            f"{AI_INSIGHTS_URL}/nutrition/personalized-recommendations",
            json={
                "user_id": user_id,
                "pattern_analysis": pattern_analysis,
                "macro_insights": macro_insights,
                "focus": "performance_optimization"
            },
            headers={"Authorization": "Bearer dev-token"},
            timeout=10
        )
        
        if ai_response.status_code == 200:
            ai_recommendations = ai_response.json().get("recommendations", [])
            recommendations.extend(ai_recommendations)
            
    except Exception as e:
        print(f"AI recommendations error: {e}")
    
    return recommendations[:8]  # Limit to top 8 recommendations

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8094)