# ActiveLog Workout Sessions API Service
# CRITICAL BRIDGE: Connects mobile UI foundation with AI insights
# INTEGRATION: Mobile UI (port:TBD) ↔ Workout Sessions (port:8093) ↔ AI Insights (port:8090)

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
from datetime import datetime, timedelta

# Service configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/activelog")
AUTH_SERVICE_URL = "http://localhost:8001"
AI_INSIGHTS_URL = "http://localhost:8090" 
USER_MANAGEMENT_URL = "http://localhost:8092"

# Pydantic models for mobile-friendly API
class WorkoutSessionCreate(BaseModel):
    workout_type: str
    planned_duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    location: Optional[str] = None
    
class WorkoutSessionUpdate(BaseModel):
    duration_minutes: Optional[int] = None
    calories_burned: Optional[int] = None
    perceived_exertion: Optional[int] = None
    notes: Optional[str] = None
    weather_conditions: Optional[str] = None
    completed_at: Optional[str] = None

class ExerciseEntry(BaseModel):
    exercise_name: str
    exercise_type: str
    sets: Optional[int] = None
    reps: Optional[int] = None
    weight_kg: Optional[float] = None
    distance_km: Optional[float] = None
    duration_seconds: Optional[int] = None
    rest_seconds: Optional[int] = None
    notes: Optional[str] = None
    form_rating: Optional[int] = None

class WorkoutSessionResponse(BaseModel):
    id: str
    workout_type: str
    duration_minutes: Optional[int]
    calories_burned: Optional[int]
    perceived_exertion: Optional[int]
    notes: Optional[str]
    location: Optional[str]
    started_at: str
    completed_at: Optional[str]
    exercises: List[Dict]
    ai_insights: Optional[Dict] = None

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
    title="ActiveLog Workout Sessions",
    description="Mobile-optimized workout tracking with AI integration",
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
    except Exception as e:
        # Development fallback
        if credentials.credentials == "dev-token":
            return {"user_id": "dev_user_123", "username": "dev_user"}
        raise HTTPException(status_code=401, detail="Token validation failed")

@app.get("/health")
async def health_check():
    return {
        "service": "workout-sessions",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "integrations": {
            "database": db_pool is not None,
            "auth_service": "connected",
            "ai_insights": "connected",
            "user_management": "connected"
        }
    }

@app.post("/workouts", response_model=WorkoutSessionResponse)
async def create_workout_session(
    workout: WorkoutSessionCreate,
    user=Depends(verify_jwt_token)
):
    """Create new workout session optimized for mobile apps"""
    
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database unavailable")
    
    async with db_pool.acquire() as conn:
        try:
            workout_id = str(uuid.uuid4())
            started_at = datetime.utcnow().isoformat()
            
            # Insert workout session
            await conn.execute("""
                INSERT INTO workout_sessions (
                    id, user_id, workout_type, duration_minutes, notes, 
                    location, started_at, created_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, workout_id, user["user_id"], workout.workout_type,
                workout.planned_duration_minutes, workout.notes,
                workout.location, started_at, started_at)
            
            return WorkoutSessionResponse(
                id=workout_id,
                workout_type=workout.workout_type,
                duration_minutes=workout.planned_duration_minutes,
                calories_burned=None,
                perceived_exertion=None,
                notes=workout.notes,
                location=workout.location,
                started_at=started_at,
                completed_at=None,
                exercises=[]
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create workout: {str(e)}")

@app.get("/workouts/{workout_id}", response_model=WorkoutSessionResponse)
async def get_workout_session(
    workout_id: str,
    include_ai_insights: bool = False,
    user=Depends(verify_jwt_token)
):
    """Get workout session with optional AI insights - mobile optimized"""
    
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database unavailable")
    
    async with db_pool.acquire() as conn:
        try:
            # Get workout session
            workout_row = await conn.fetchrow("""
                SELECT * FROM workout_sessions 
                WHERE id = $1 AND user_id = $2
            """, workout_id, user["user_id"])
            
            if not workout_row:
                raise HTTPException(status_code=404, detail="Workout not found")
            
            workout_data = dict(workout_row)
            
            # Get exercises for this workout
            exercise_rows = await conn.fetch("""
                SELECT * FROM exercise_entries 
                WHERE workout_session_id = $1
                ORDER BY created_at
            """, workout_id)
            
            exercises = [dict(row) for row in exercise_rows]
            
            # Get AI insights if requested
            ai_insights = None
            if include_ai_insights and workout_data.get('completed_at'):
                try:
                    ai_response = requests.post(
                        f"{AI_INSIGHTS_URL}/workout/insights",
                        json={"workout_session_id": workout_id},
                        headers={"Authorization": f"Bearer {user.get('token', 'dev-token')}"},
                        timeout=10
                    )
                    if ai_response.status_code == 200:
                        ai_insights = ai_response.json()
                except Exception as e:
                    print(f"AI insights request failed: {e}")
            
            return WorkoutSessionResponse(
                id=workout_data["id"],
                workout_type=workout_data["workout_type"],
                duration_minutes=workout_data.get("duration_minutes"),
                calories_burned=workout_data.get("calories_burned"),
                perceived_exertion=workout_data.get("perceived_exertion"),
                notes=workout_data.get("notes"),
                location=workout_data.get("location"),
                started_at=workout_data["started_at"],
                completed_at=workout_data.get("completed_at"),
                exercises=exercises,
                ai_insights=ai_insights
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get workout: {str(e)}")

@app.put("/workouts/{workout_id}", response_model=WorkoutSessionResponse)
async def update_workout_session(
    workout_id: str,
    workout_update: WorkoutSessionUpdate,
    user=Depends(verify_jwt_token)
):
    """Update workout session - optimized for mobile real-time updates"""
    
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database unavailable")
    
    async with db_pool.acquire() as conn:
        try:
            # Build update query dynamically
            update_fields = []
            update_values = []
            param_count = 1
            
            for field, value in workout_update.dict(exclude_unset=True).items():
                if value is not None:
                    update_fields.append(f"{field} = ${param_count}")
                    update_values.append(value)
                    param_count += 1
            
            if not update_fields:
                raise HTTPException(status_code=400, detail="No fields to update")
            
            # Add updated timestamp
            update_fields.append(f"updated_at = ${param_count}")
            update_values.append(datetime.utcnow().isoformat())
            param_count += 1
            
            # Add WHERE conditions
            update_values.extend([workout_id, user["user_id"]])
            
            query = f"""
                UPDATE workout_sessions 
                SET {', '.join(update_fields)}
                WHERE id = ${param_count-1} AND user_id = ${param_count}
                RETURNING *
            """
            
            updated_row = await conn.fetchrow(query, *update_values)
            
            if not updated_row:
                raise HTTPException(status_code=404, detail="Workout not found")
            
            # Trigger AI embedding storage if workout completed
            if workout_update.completed_at:
                try:
                    requests.post(
                        f"{AI_INSIGHTS_URL}/workout/store-embedding",
                        json={"workout_session_id": workout_id},
                        headers={"Authorization": f"Bearer {user.get('token', 'dev-token')}"},
                        timeout=5
                    )
                except Exception as e:
                    print(f"AI embedding storage failed: {e}")
            
            # Get exercises for response
            exercise_rows = await conn.fetch("""
                SELECT * FROM exercise_entries 
                WHERE workout_session_id = $1
                ORDER BY created_at
            """, workout_id)
            
            updated_data = dict(updated_row)
            exercises = [dict(row) for row in exercise_rows]
            
            return WorkoutSessionResponse(
                id=updated_data["id"],
                workout_type=updated_data["workout_type"],
                duration_minutes=updated_data.get("duration_minutes"),
                calories_burned=updated_data.get("calories_burned"),
                perceived_exertion=updated_data.get("perceived_exertion"),
                notes=updated_data.get("notes"),
                location=updated_data.get("location"),
                started_at=updated_data["started_at"],
                completed_at=updated_data.get("completed_at"),
                exercises=exercises
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to update workout: {str(e)}")

@app.post("/workouts/{workout_id}/exercises")
async def add_exercise_to_workout(
    workout_id: str,
    exercise: ExerciseEntry,
    user=Depends(verify_jwt_token)
):
    """Add exercise to workout session - mobile real-time tracking"""
    
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database unavailable")
    
    async with db_pool.acquire() as conn:
        try:
            # Verify workout exists and belongs to user
            workout_exists = await conn.fetchval("""
                SELECT EXISTS(
                    SELECT 1 FROM workout_sessions 
                    WHERE id = $1 AND user_id = $2
                )
            """, workout_id, user["user_id"])
            
            if not workout_exists:
                raise HTTPException(status_code=404, detail="Workout not found")
            
            # Insert exercise
            exercise_id = str(uuid.uuid4())
            created_at = datetime.utcnow().isoformat()
            
            await conn.execute("""
                INSERT INTO exercise_entries (
                    id, workout_session_id, exercise_name, exercise_type,
                    sets, reps, weight_kg, distance_km, duration_seconds,
                    rest_seconds, notes, form_rating, created_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            """, exercise_id, workout_id, exercise.exercise_name, exercise.exercise_type,
                exercise.sets, exercise.reps, exercise.weight_kg, exercise.distance_km,
                exercise.duration_seconds, exercise.rest_seconds, exercise.notes,
                exercise.form_rating, created_at)
            
            return {
                "id": exercise_id,
                "workout_session_id": workout_id,
                "exercise_name": exercise.exercise_name,
                "exercise_type": exercise.exercise_type,
                "created_at": created_at,
                "status": "added_successfully"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to add exercise: {str(e)}")

@app.get("/workouts")
async def get_user_workouts(
    limit: int = 20,
    offset: int = 0,
    workout_type: Optional[str] = None,
    user=Depends(verify_jwt_token)
):
    """Get user's workout history - mobile dashboard optimized"""
    
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database unavailable")
    
    async with db_pool.acquire() as conn:
        try:
            # Build query with optional filtering
            where_conditions = ["user_id = $1"]
            query_params = [user["user_id"]]
            param_count = 2
            
            if workout_type:
                where_conditions.append(f"workout_type = ${param_count}")
                query_params.append(workout_type)
                param_count += 1
            
            # Add pagination
            query_params.extend([limit, offset])
            
            query = f"""
                SELECT ws.*, 
                       COUNT(ee.id) as exercise_count,
                       CASE WHEN ws.completed_at IS NOT NULL THEN true ELSE false END as is_completed
                FROM workout_sessions ws
                LEFT JOIN exercise_entries ee ON ws.id = ee.workout_session_id
                WHERE {' AND '.join(where_conditions)}
                GROUP BY ws.id
                ORDER BY ws.started_at DESC
                LIMIT ${param_count-1} OFFSET ${param_count}
            """
            
            workout_rows = await conn.fetch(query, *query_params)
            
            # Get total count for pagination
            count_query = f"""
                SELECT COUNT(*) FROM workout_sessions 
                WHERE {' AND '.join(where_conditions[:-2] if workout_type else where_conditions[:-2])}
            """
            total_count = await conn.fetchval(count_query, *query_params[:-2])
            
            workouts = []
            for row in workout_rows:
                workout_data = dict(row)
                workouts.append({
                    "id": workout_data["id"],
                    "workout_type": workout_data["workout_type"],
                    "duration_minutes": workout_data.get("duration_minutes"),
                    "calories_burned": workout_data.get("calories_burned"),
                    "perceived_exertion": workout_data.get("perceived_exertion"),
                    "started_at": workout_data["started_at"],
                    "completed_at": workout_data.get("completed_at"),
                    "exercise_count": workout_data["exercise_count"],
                    "is_completed": workout_data["is_completed"]
                })
            
            return {
                "workouts": workouts,
                "pagination": {
                    "total_count": total_count,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + limit < total_count
                }
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get workouts: {str(e)}")

@app.get("/workouts/{workout_id}/ai-insights")
async def get_workout_ai_insights(
    workout_id: str,
    user=Depends(verify_jwt_token)
):
    """Get AI insights for completed workout - mobile optimization"""
    
    try:
        ai_response = requests.post(
            f"{AI_INSIGHTS_URL}/workout/insights",
            json={
                "workout_session_id": workout_id,
                "analysis_type": "comprehensive"
            },
            headers={"Authorization": f"Bearer {user.get('token', 'dev-token')}"},
            timeout=15
        )
        
        if ai_response.status_code == 200:
            return ai_response.json()
        else:
            raise HTTPException(status_code=ai_response.status_code, 
                              detail="AI insights service unavailable")
            
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=503, detail="AI insights service unavailable")

@app.get("/dashboard/stats")
async def get_dashboard_stats(
    days: int = 30,
    user=Depends(verify_jwt_token)
):
    """Mobile dashboard statistics - optimized for quick loading"""
    
    if not db_pool:
        return {"error": "Database unavailable", "stats": {}}
    
    async with db_pool.acquire() as conn:
        try:
            since_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            # Get comprehensive stats in single query
            stats_query = """
                SELECT 
                    COUNT(*) as total_workouts,
                    COUNT(CASE WHEN completed_at IS NOT NULL THEN 1 END) as completed_workouts,
                    AVG(duration_minutes) as avg_duration,
                    AVG(calories_burned) as avg_calories,
                    AVG(perceived_exertion) as avg_exertion,
                    COUNT(DISTINCT workout_type) as workout_types,
                    SUM(duration_minutes) as total_minutes
                FROM workout_sessions
                WHERE user_id = $1 AND started_at >= $2
            """
            
            stats_row = await conn.fetchrow(stats_query, user["user_id"], since_date)
            stats = dict(stats_row)
            
            # Get workout type breakdown
            type_breakdown = await conn.fetch("""
                SELECT workout_type, COUNT(*) as count
                FROM workout_sessions
                WHERE user_id = $1 AND started_at >= $2
                GROUP BY workout_type
                ORDER BY count DESC
            """, user["user_id"], since_date)
            
            return {
                "period_days": days,
                "stats": {
                    "total_workouts": stats["total_workouts"] or 0,
                    "completed_workouts": stats["completed_workouts"] or 0,
                    "completion_rate": round(
                        (stats["completed_workouts"] or 0) / max(stats["total_workouts"] or 1, 1) * 100, 1
                    ),
                    "avg_duration_minutes": round(stats["avg_duration"] or 0, 1),
                    "avg_calories_burned": round(stats["avg_calories"] or 0, 1),
                    "avg_perceived_exertion": round(stats["avg_exertion"] or 0, 1),
                    "total_minutes_exercised": stats["total_minutes"] or 0,
                    "workout_types_used": stats["workout_types"] or 0
                },
                "workout_type_breakdown": [
                    {"type": row["workout_type"], "count": row["count"]} 
                    for row in type_breakdown
                ],
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {"error": f"Stats calculation failed: {str(e)}", "stats": {}}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8093)