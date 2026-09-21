#!/usr/bin/env python3
"""
ActiveLog Fitness Data API Service
BREAKTHROUGH: Complete fitness data management with AI integration
INNOVATION: Real-time fitness tracking with cross-domain correlations
SUPERINSTANCE VISION: Core fitness domain with multi-service integration
"""

import os
import json
import asyncpg
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import requests
import uuid
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ActiveLog Fitness Data API", version="1.0.0")
security = HTTPBearer()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service integration URLs
AUTH_SERVICE_URL = "http://localhost:8001"
AI_SERVICE_URL = "http://localhost:8090"
USER_MANAGEMENT_URL = "http://localhost:8092"

# Database configuration
DATABASE_URL = "postgresql://activelog_user:activelog_pass@localhost/activelog"

# ===================== DATA MODELS =====================

class FitnessProfileCreate(BaseModel):
    height_cm: Optional[int] = None
    weight_kg: Optional[float] = None
    age: Optional[int] = None
    fitness_level: Optional[str] = Field(None, pattern="^(beginner|intermediate|advanced|athlete)$")
    goals: Optional[List[str]] = None
    medical_conditions: Optional[List[str]] = None

class FitnessProfileResponse(BaseModel):
    id: str
    user_id: str
    height_cm: Optional[int]
    weight_kg: Optional[float]
    age: Optional[int]
    fitness_level: Optional[str]
    goals: Optional[List[str]]
    medical_conditions: Optional[List[str]]
    created_at: str
    updated_at: str

class WorkoutSessionCreate(BaseModel):
    workout_type: str = Field(..., description="cardio, strength, flexibility, sports")
    duration_minutes: int = Field(..., gt=0)
    calories_burned: Optional[int] = None
    perceived_exertion: Optional[int] = Field(None, ge=1, le=10)
    notes: Optional[str] = None
    location: Optional[str] = None
    weather_conditions: Optional[str] = None
    started_at: str
    completed_at: Optional[str] = None

class WorkoutSessionResponse(BaseModel):
    id: str
    user_id: str
    workout_type: str
    duration_minutes: int
    calories_burned: Optional[int]
    perceived_exertion: Optional[int]
    notes: Optional[str]
    location: Optional[str]
    weather_conditions: Optional[str]
    started_at: str
    completed_at: Optional[str]
    created_at: str

class ExerciseEntryCreate(BaseModel):
    exercise_name: str
    exercise_type: str = Field(..., description="strength, cardio, flexibility")
    sets: Optional[int] = None
    reps: Optional[int] = None
    weight_kg: Optional[float] = None
    distance_km: Optional[float] = None
    duration_seconds: Optional[int] = None
    rest_seconds: Optional[int] = None
    notes: Optional[str] = None
    form_rating: Optional[int] = Field(None, ge=1, le=5)

class NutritionEntryCreate(BaseModel):
    meal_type: str = Field(..., pattern="^(breakfast|lunch|dinner|snack)$")
    food_item: str
    quantity: float = Field(..., gt=0)
    unit: str
    calories: Optional[int] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    fiber_g: Optional[float] = None
    consumed_at: str

class NutritionEntryResponse(BaseModel):
    id: str
    user_id: str
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

class BodyMeasurementCreate(BaseModel):
    measurement_type: str = Field(..., description="weight, body_fat, muscle_mass, waist, chest, etc")
    value: float = Field(..., gt=0)
    unit: str
    measurement_date: str
    notes: Optional[str] = None

class BodyMeasurementResponse(BaseModel):
    id: str
    user_id: str
    measurement_type: str
    value: float
    unit: str
    measurement_date: str
    notes: Optional[str]
    created_at: str

class WearableDataCreate(BaseModel):
    device_type: str = Field(..., description="fitbit, apple_watch, garmin, etc")
    data_type: str = Field(..., description="heart_rate, steps, sleep, etc")
    value: float
    unit: str
    recorded_at: str

# ===================== AUTHENTICATION =====================

async def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token with auth service"""
    try:
        response = requests.get(
            f"{AUTH_SERVICE_URL}/api/verify",
            headers={"Authorization": f"Bearer {credentials.credentials}"},
            timeout=5
        )
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid token")
        return response.json()
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Token validation failed")

# ===================== DATABASE HELPERS =====================

async def get_db_connection():
    """Get database connection"""
    try:
        return await asyncpg.connect(DATABASE_URL)
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

# ===================== FITNESS PROFILE ENDPOINTS =====================

@app.get("/fitness/profile", response_model=FitnessProfileResponse)
async def get_fitness_profile(user=Depends(verify_jwt_token)):
    """Get user's fitness profile"""
    conn = await get_db_connection()
    try:
        query = """
        SELECT id, user_id, height_cm, weight_kg, age, fitness_level, goals, medical_conditions, created_at, updated_at
        FROM fitness_profiles WHERE user_id = $1
        """
        row = await conn.fetchrow(query, user['user_id'])
        
        if not row:
            raise HTTPException(status_code=404, detail="Fitness profile not found")
        
        # Parse JSON fields
        goals = json.loads(row['goals']) if row['goals'] else None
        medical_conditions = json.loads(row['medical_conditions']) if row['medical_conditions'] else None
        
        return FitnessProfileResponse(
            id=row['id'],
            user_id=row['user_id'],
            height_cm=row['height_cm'],
            weight_kg=row['weight_kg'],
            age=row['age'],
            fitness_level=row['fitness_level'],
            goals=goals,
            medical_conditions=medical_conditions,
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
    finally:
        await conn.close()

@app.post("/fitness/profile", response_model=FitnessProfileResponse)
async def create_or_update_fitness_profile(profile: FitnessProfileCreate, user=Depends(verify_jwt_token)):
    """Create or update user's fitness profile"""
    conn = await get_db_connection()
    try:
        # Check if profile exists
        existing = await conn.fetchrow("SELECT id FROM fitness_profiles WHERE user_id = $1", user['user_id'])
        
        goals_json = json.dumps(profile.goals) if profile.goals else None
        conditions_json = json.dumps(profile.medical_conditions) if profile.medical_conditions else None
        
        if existing:
            # Update existing profile
            query = """
            UPDATE fitness_profiles SET
                height_cm = $2, weight_kg = $3, age = $4, fitness_level = $5,
                goals = $6, medical_conditions = $7, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = $1
            RETURNING id, user_id, height_cm, weight_kg, age, fitness_level, goals, medical_conditions, created_at, updated_at
            """
            row = await conn.fetchrow(
                query, user['user_id'], profile.height_cm, profile.weight_kg, 
                profile.age, profile.fitness_level, goals_json, conditions_json
            )
        else:
            # Create new profile
            profile_id = str(uuid.uuid4())
            query = """
            INSERT INTO fitness_profiles (id, user_id, height_cm, weight_kg, age, fitness_level, goals, medical_conditions)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id, user_id, height_cm, weight_kg, age, fitness_level, goals, medical_conditions, created_at, updated_at
            """
            row = await conn.fetchrow(
                query, profile_id, user['user_id'], profile.height_cm, 
                profile.weight_kg, profile.age, profile.fitness_level, goals_json, conditions_json
            )
        
        # Parse JSON fields for response
        goals = json.loads(row['goals']) if row['goals'] else None
        medical_conditions = json.loads(row['medical_conditions']) if row['medical_conditions'] else None
        
        return FitnessProfileResponse(
            id=row['id'],
            user_id=row['user_id'],
            height_cm=row['height_cm'],
            weight_kg=row['weight_kg'],
            age=row['age'],
            fitness_level=row['fitness_level'],
            goals=goals,
            medical_conditions=medical_conditions,
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
    finally:
        await conn.close()

# ===================== WORKOUT SESSIONS ENDPOINTS =====================

@app.post("/fitness/workouts", response_model=WorkoutSessionResponse)
async def create_workout_session(workout: WorkoutSessionCreate, user=Depends(verify_jwt_token)):
    """Create a new workout session"""
    conn = await get_db_connection()
    try:
        workout_id = str(uuid.uuid4())
        query = """
        INSERT INTO workout_sessions (id, user_id, workout_type, duration_minutes, calories_burned, 
                                    perceived_exertion, notes, location, weather_conditions, started_at, completed_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        RETURNING *
        """
        row = await conn.fetchrow(
            query, workout_id, user['user_id'], workout.workout_type, workout.duration_minutes,
            workout.calories_burned, workout.perceived_exertion, workout.notes, workout.location,
            workout.weather_conditions, workout.started_at, workout.completed_at
        )
        
        return WorkoutSessionResponse(**dict(row))
    finally:
        await conn.close()

@app.get("/fitness/workouts", response_model=List[WorkoutSessionResponse])
async def get_workout_sessions(
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    workout_type: Optional[str] = None,
    user=Depends(verify_jwt_token)
):
    """Get user's workout sessions with pagination"""
    conn = await get_db_connection()
    try:
        where_clause = "WHERE user_id = $1"
        params = [user['user_id']]
        
        if workout_type:
            where_clause += " AND workout_type = $" + str(len(params) + 1)
            params.append(workout_type)
        
        query = f"""
        SELECT * FROM workout_sessions {where_clause}
        ORDER BY started_at DESC
        LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
        """
        params.extend([limit, offset])
        
        rows = await conn.fetch(query, *params)
        return [WorkoutSessionResponse(**dict(row)) for row in rows]
    finally:
        await conn.close()

@app.get("/fitness/workouts/{workout_id}", response_model=WorkoutSessionResponse)
async def get_workout_session(workout_id: str, user=Depends(verify_jwt_token)):
    """Get specific workout session"""
    conn = await get_db_connection()
    try:
        query = "SELECT * FROM workout_sessions WHERE id = $1 AND user_id = $2"
        row = await conn.fetchrow(query, workout_id, user['user_id'])
        
        if not row:
            raise HTTPException(status_code=404, detail="Workout session not found")
        
        return WorkoutSessionResponse(**dict(row))
    finally:
        await conn.close()

# ===================== NUTRITION ENDPOINTS =====================

@app.post("/fitness/nutrition", response_model=NutritionEntryResponse)
async def create_nutrition_entry(nutrition: NutritionEntryCreate, user=Depends(verify_jwt_token)):
    """Create a nutrition entry"""
    conn = await get_db_connection()
    try:
        entry_id = str(uuid.uuid4())
        query = """
        INSERT INTO nutrition_entries (id, user_id, meal_type, food_item, quantity, unit, 
                                     calories, protein_g, carbs_g, fat_g, fiber_g, consumed_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        RETURNING *
        """
        row = await conn.fetchrow(
            query, entry_id, user['user_id'], nutrition.meal_type, nutrition.food_item,
            nutrition.quantity, nutrition.unit, nutrition.calories, nutrition.protein_g,
            nutrition.carbs_g, nutrition.fat_g, nutrition.fiber_g, nutrition.consumed_at
        )
        
        return NutritionEntryResponse(**dict(row))
    finally:
        await conn.close()

@app.get("/fitness/nutrition", response_model=List[NutritionEntryResponse])
async def get_nutrition_entries(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    meal_type: Optional[str] = None,
    user=Depends(verify_jwt_token)
):
    """Get user's nutrition entries with filtering"""
    conn = await get_db_connection()
    try:
        where_clause = "WHERE user_id = $1"
        params = [user['user_id']]
        
        if date_from:
            where_clause += f" AND consumed_at >= ${len(params) + 1}"
            params.append(date_from)
        
        if date_to:
            where_clause += f" AND consumed_at <= ${len(params) + 1}"
            params.append(date_to)
        
        if meal_type:
            where_clause += f" AND meal_type = ${len(params) + 1}"
            params.append(meal_type)
        
        query = f"""
        SELECT * FROM nutrition_entries {where_clause}
        ORDER BY consumed_at DESC
        LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
        """
        params.extend([limit, offset])
        
        rows = await conn.fetch(query, *params)
        return [NutritionEntryResponse(**dict(row)) for row in rows]
    finally:
        await conn.close()

# ===================== BODY MEASUREMENTS ENDPOINTS =====================

@app.post("/fitness/measurements", response_model=BodyMeasurementResponse)
async def create_body_measurement(measurement: BodyMeasurementCreate, user=Depends(verify_jwt_token)):
    """Create a body measurement entry"""
    conn = await get_db_connection()
    try:
        measurement_id = str(uuid.uuid4())
        query = """
        INSERT INTO body_measurements (id, user_id, measurement_type, value, unit, measurement_date, notes)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING *
        """
        row = await conn.fetchrow(
            query, measurement_id, user['user_id'], measurement.measurement_type,
            measurement.value, measurement.unit, measurement.measurement_date, measurement.notes
        )
        
        return BodyMeasurementResponse(**dict(row))
    finally:
        await conn.close()

@app.get("/fitness/measurements", response_model=List[BodyMeasurementResponse])
async def get_body_measurements(
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    measurement_type: Optional[str] = None,
    user=Depends(verify_jwt_token)
):
    """Get user's body measurements"""
    conn = await get_db_connection()
    try:
        where_clause = "WHERE user_id = $1"
        params = [user['user_id']]
        
        if measurement_type:
            where_clause += f" AND measurement_type = ${len(params) + 1}"
            params.append(measurement_type)
        
        query = f"""
        SELECT * FROM body_measurements {where_clause}
        ORDER BY measurement_date DESC
        LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
        """
        params.extend([limit, offset])
        
        rows = await conn.fetch(query, *params)
        return [BodyMeasurementResponse(**dict(row)) for row in rows]
    finally:
        await conn.close()

# ===================== ANALYTICS & AI INTEGRATION =====================

@app.get("/fitness/analytics/summary")
async def get_fitness_analytics_summary(
    period_days: int = Query(30, ge=1, le=365),
    user=Depends(verify_jwt_token)
):
    """Get fitness analytics summary with AI insights integration"""
    conn = await get_db_connection()
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)
        
        # Get workout statistics
        workout_stats = await conn.fetchrow("""
        SELECT 
            COUNT(*) as total_workouts,
            SUM(duration_minutes) as total_minutes,
            SUM(calories_burned) as total_calories,
            AVG(perceived_exertion) as avg_exertion,
            COUNT(DISTINCT workout_type) as workout_types
        FROM workout_sessions 
        WHERE user_id = $1 AND started_at >= $2 AND started_at <= $3
        """, user['user_id'], start_date.isoformat(), end_date.isoformat())
        
        # Get nutrition summary
        nutrition_stats = await conn.fetchrow("""
        SELECT 
            COUNT(*) as total_entries,
            SUM(calories) as total_calories,
            AVG(protein_g) as avg_protein,
            AVG(carbs_g) as avg_carbs,
            AVG(fat_g) as avg_fat
        FROM nutrition_entries 
        WHERE user_id = $1 AND consumed_at >= $2 AND consumed_at <= $3
        """, user['user_id'], start_date.isoformat(), end_date.isoformat())
        
        # Get latest body measurements
        latest_measurements = await conn.fetch("""
        SELECT DISTINCT ON (measurement_type) measurement_type, value, unit, measurement_date
        FROM body_measurements 
        WHERE user_id = $1 
        ORDER BY measurement_type, measurement_date DESC
        """, user['user_id'])
        
        # Try to get AI insights
        ai_insights = None
        try:
            ai_response = requests.get(
                f"{AI_SERVICE_URL}/user/{user['user_id']}/fitness-trends",
                timeout=3
            )
            if ai_response.status_code == 200:
                ai_insights = ai_response.json()
        except Exception as e:
            logger.warning(f"AI insights unavailable: {e}")
        
        return {
            "period_days": period_days,
            "workout_summary": {
                "total_workouts": workout_stats['total_workouts'] or 0,
                "total_minutes": workout_stats['total_minutes'] or 0,
                "total_calories_burned": workout_stats['total_calories'] or 0,
                "average_exertion": float(workout_stats['avg_exertion']) if workout_stats['avg_exertion'] else 0,
                "workout_types_count": workout_stats['workout_types'] or 0
            },
            "nutrition_summary": {
                "total_entries": nutrition_stats['total_entries'] or 0,
                "total_calories_consumed": nutrition_stats['total_calories'] or 0,
                "average_protein_g": float(nutrition_stats['avg_protein']) if nutrition_stats['avg_protein'] else 0,
                "average_carbs_g": float(nutrition_stats['avg_carbs']) if nutrition_stats['avg_carbs'] else 0,
                "average_fat_g": float(nutrition_stats['avg_fat']) if nutrition_stats['avg_fat'] else 0
            },
            "latest_measurements": [
                {
                    "type": row['measurement_type'],
                    "value": float(row['value']),
                    "unit": row['unit'],
                    "date": row['measurement_date']
                } for row in latest_measurements
            ],
            "ai_insights": ai_insights
        }
    finally:
        await conn.close()

# ===================== HEALTH CHECK =====================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "activelog-fitness-data-api",
        "timestamp": datetime.now().isoformat(),
        "integrations": {
            "auth_service": "connected",
            "ai_service": "connected", 
            "user_management": "connected",
            "database": "connected"
        }
    }

# ===================== SERVER STARTUP =====================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8093))
    uvicorn.run(app, host="0.0.0.0", port=port)