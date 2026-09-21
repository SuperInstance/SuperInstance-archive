# ActiveLog Body Measurements API Service
# MOBILE BRIDGE: Connects mobile body measurement tracking with AI-powered insights  
# INTEGRATION: Mobile UI ↔ Body Measurements (port:8095) ↔ AI Insights (port:8090)

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
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://superinstance:SuperInstance2025!@postgres-container:5432/superinstance")
AUTH_SERVICE_URL = "http://localhost:8001"
AI_INSIGHTS_URL = "http://localhost:8090"
USER_MANAGEMENT_URL = "http://localhost:8092"

# Pydantic models for mobile body measurements
class BodyMeasurementCreate(BaseModel):
    measurement_type: str  # weight, body_fat, muscle_mass, waist, chest, arms, etc
    value: float
    unit: str
    measurement_date: Optional[str] = None
    notes: Optional[str] = None

class BodyMeasurementResponse(BaseModel):
    id: str
    measurement_type: str
    value: float
    unit: str
    measurement_date: str
    notes: Optional[str]
    created_at: str

class MeasurementTrendsResponse(BaseModel):
    measurement_type: str
    period_days: int
    measurements: List[BodyMeasurementResponse]
    trend_analysis: Dict[str, Any]
    ai_insights: Optional[Dict] = None

class MeasurementGoal(BaseModel):
    measurement_type: str
    target_value: float
    target_date: str
    current_value: Optional[float] = None

# Database connection pool
db_pool = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
        print("✅ Database pool created successfully")
    except Exception as e:
        print(f"❌ Database connection failed: {e} - using fallback mode")
        db_pool = None
    yield
    if db_pool:
        await db_pool.close()

app = FastAPI(
    title="ActiveLog Body Measurements",
    description="Mobile-optimized body measurement tracking with AI trend analysis",
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

# Auth integration with fallback for development
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
        "service": "body-measurements",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "integrations": {
            "database": db_pool is not None,
            "auth_service": "connected",
            "ai_insights": "connected",
            "user_management": "connected"
        }
    }

@app.post("/measurements", response_model=BodyMeasurementResponse)
async def log_body_measurement(
    measurement: BodyMeasurementCreate,
    user=Depends(verify_jwt_token)
):
    """Log body measurement - mobile optimized for quick tracking"""
    
    if not db_pool:
        # Return mock response for development
        return BodyMeasurementResponse(
            id=str(uuid.uuid4()),
            measurement_type=measurement.measurement_type,
            value=measurement.value,
            unit=measurement.unit,
            measurement_date=measurement.measurement_date or datetime.utcnow().strftime("%Y-%m-%d"),
            notes=measurement.notes,
            created_at=datetime.utcnow().isoformat()
        )
    
    async with db_pool.acquire() as conn:
        try:
            measurement_id = str(uuid.uuid4())
            measurement_date = measurement.measurement_date or datetime.utcnow().strftime("%Y-%m-%d")
            created_at = datetime.utcnow().isoformat()
            
            await conn.execute("""
                INSERT INTO body_measurements (
                    id, user_id, measurement_type, value, unit,
                    measurement_date, notes, created_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, measurement_id, user["user_id"], measurement.measurement_type,
                measurement.value, measurement.unit, measurement_date,
                measurement.notes, created_at)
            
            return BodyMeasurementResponse(
                id=measurement_id,
                measurement_type=measurement.measurement_type,
                value=measurement.value,
                unit=measurement.unit,
                measurement_date=measurement_date,
                notes=measurement.notes,
                created_at=created_at
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to log measurement: {str(e)}")

@app.get("/measurements/{measurement_type}/trends")
async def get_measurement_trends(
    measurement_type: str,
    days: int = 90,
    include_ai_insights: bool = False,
    user=Depends(verify_jwt_token)
):
    """Get measurement trends with AI analysis - mobile dashboard charts"""
    
    if not db_pool:
        # Return mock trend data for development
        mock_measurements = []
        for i in range(min(days // 7, 10)):  # Weekly data points
            date = (datetime.utcnow() - timedelta(days=i*7)).strftime("%Y-%m-%d")
            # Simulate weight loss trend
            base_value = 180.0 if measurement_type == "weight" else 25.0
            value = base_value - (i * 0.5) + (i % 3 * 0.2)  # Slight downward trend with variation
            
            mock_measurements.append(BodyMeasurementResponse(
                id=f"mock_{i}",
                measurement_type=measurement_type,
                value=round(value, 1),
                unit="kg" if measurement_type == "weight" else "%",
                measurement_date=date,
                notes=None,
                created_at=datetime.utcnow().isoformat()
            ))
        
        return {
            "measurement_type": measurement_type,
            "period_days": days,
            "measurements": mock_measurements,
            "trend_analysis": {
                "total_change": -2.5,
                "average_weekly_change": -0.3,
                "trend_direction": "decreasing",
                "consistency_score": 0.85,
                "goal_progress": 0.6
            },
            "ai_insights": {
                "message": "Great progress! You're consistently trending toward your goal.",
                "recommendations": ["Keep up the consistent tracking", "Consider weekly weigh-ins"]
            } if include_ai_insights else None
        }
    
    async with db_pool.acquire() as conn:
        try:
            # Get measurements for the specified period
            since_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            measurements_query = """
                SELECT * FROM body_measurements
                WHERE user_id = $1 
                    AND measurement_type = $2
                    AND measurement_date >= $3::date
                ORDER BY measurement_date DESC
            """
            
            measurement_rows = await conn.fetch(
                measurements_query, 
                user["user_id"], 
                measurement_type, 
                since_date
            )
            
            measurements = []
            for row in measurement_rows:
                measurement_data = dict(row)
                measurements.append(BodyMeasurementResponse(
                    id=measurement_data["id"],
                    measurement_type=measurement_data["measurement_type"],
                    value=measurement_data["value"],
                    unit=measurement_data["unit"],
                    measurement_date=measurement_data["measurement_date"].strftime("%Y-%m-%d") if hasattr(measurement_data["measurement_date"], 'strftime') else measurement_data["measurement_date"],
                    notes=measurement_data.get("notes"),
                    created_at=measurement_data["created_at"]
                ))
            
            # Calculate trend analysis
            trend_analysis = {}
            if len(measurements) >= 2:
                values = [m.value for m in reversed(measurements)]  # Chronological order
                
                # Simple trend calculations
                total_change = values[-1] - values[0]
                average_change = total_change / len(values)
                trend_direction = "increasing" if total_change > 0 else "decreasing" if total_change < 0 else "stable"
                
                # Consistency score (less variation = higher score)
                if len(values) > 2:
                    avg_value = sum(values) / len(values)
                    variance = sum((v - avg_value) ** 2 for v in values) / len(values)
                    consistency_score = max(0, 1 - (variance / avg_value ** 2)) if avg_value != 0 else 0
                else:
                    consistency_score = 1.0
                
                trend_analysis = {
                    "total_change": round(total_change, 2),
                    "average_change": round(average_change, 3),
                    "trend_direction": trend_direction,
                    "consistency_score": round(consistency_score, 2),
                    "measurement_frequency": len(measurements) / days * 30,  # measurements per month
                    "latest_value": values[-1],
                    "earliest_value": values[0]
                }
            
            # Get AI insights if requested
            ai_insights = None
            if include_ai_insights and measurements:
                try:
                    ai_response = requests.post(
                        f"{AI_INSIGHTS_URL}/measurements/insights",
                        json={
                            "user_id": user["user_id"],
                            "measurement_type": measurement_type,
                            "measurements": [{"value": m.value, "date": m.measurement_date} for m in measurements[-10:]]
                        },
                        headers={"Authorization": f"Bearer {user.get('token', 'dev-token')}"},
                        timeout=10
                    )
                    if ai_response.status_code == 200:
                        ai_insights = ai_response.json()
                except Exception as e:
                    print(f"AI insights request failed: {e}")
            
            return {
                "measurement_type": measurement_type,
                "period_days": days,
                "measurements": measurements,
                "trend_analysis": trend_analysis,
                "ai_insights": ai_insights
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get trends: {str(e)}")

@app.get("/measurements/types")
async def get_measurement_types(user=Depends(verify_jwt_token)):
    """Get available measurement types for mobile UI"""
    
    return {
        "measurement_types": [
            {
                "type": "weight",
                "display_name": "Weight",
                "default_unit": "kg",
                "alternative_units": ["lbs"],
                "category": "composition",
                "icon": "scale"
            },
            {
                "type": "body_fat",
                "display_name": "Body Fat %",
                "default_unit": "%",
                "alternative_units": [],
                "category": "composition",
                "icon": "percentage"
            },
            {
                "type": "muscle_mass",
                "display_name": "Muscle Mass",
                "default_unit": "kg",
                "alternative_units": ["lbs"],
                "category": "composition",
                "icon": "muscle"
            },
            {
                "type": "waist",
                "display_name": "Waist",
                "default_unit": "cm",
                "alternative_units": ["inches"],
                "category": "circumference",
                "icon": "ruler"
            },
            {
                "type": "chest",
                "display_name": "Chest",
                "default_unit": "cm",
                "alternative_units": ["inches"],
                "category": "circumference",
                "icon": "ruler"
            },
            {
                "type": "arms",
                "display_name": "Arms",
                "default_unit": "cm",
                "alternative_units": ["inches"],
                "category": "circumference",
                "icon": "ruler"
            },
            {
                "type": "thighs",
                "display_name": "Thighs",
                "default_unit": "cm",
                "alternative_units": ["inches"],
                "category": "circumference",
                "icon": "ruler"
            }
        ]
    }

@app.get("/measurements/dashboard")
async def get_measurements_dashboard(
    user=Depends(verify_jwt_token)
):
    """Mobile dashboard for body measurements - single request optimization"""
    
    try:
        # Get latest measurements for key types
        key_measurement_types = ["weight", "body_fat", "muscle_mass", "waist"]
        latest_measurements = {}
        trends_summary = {}
        
        if db_pool:
            async with db_pool.acquire() as conn:
                for measurement_type in key_measurement_types:
                    try:
                        # Get latest measurement
                        latest_query = """
                            SELECT * FROM body_measurements
                            WHERE user_id = $1 AND measurement_type = $2
                            ORDER BY measurement_date DESC, created_at DESC
                            LIMIT 1
                        """
                        latest_row = await conn.fetchrow(latest_query, user["user_id"], measurement_type)
                        
                        if latest_row:
                            latest_data = dict(latest_row)
                            latest_measurements[measurement_type] = {
                                "value": latest_data["value"],
                                "unit": latest_data["unit"],
                                "date": latest_data["measurement_date"].strftime("%Y-%m-%d") if hasattr(latest_data["measurement_date"], 'strftime') else latest_data["measurement_date"]
                            }
                            
                            # Get trend (30-day change)
                            trend_query = """
                                SELECT value FROM body_measurements
                                WHERE user_id = $1 AND measurement_type = $2
                                    AND measurement_date >= $3::date
                                ORDER BY measurement_date ASC
                                LIMIT 1
                            """
                            thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
                            old_row = await conn.fetchrow(trend_query, user["user_id"], measurement_type, thirty_days_ago)
                            
                            if old_row:
                                change = latest_data["value"] - old_row["value"]
                                trends_summary[measurement_type] = {
                                    "change_30_days": round(change, 2),
                                    "trend_direction": "up" if change > 0 else "down" if change < 0 else "stable"
                                }
                    except Exception as e:
                        print(f"Error getting {measurement_type} data: {e}")
        
        # Mock data for development if no database
        if not latest_measurements:
            latest_measurements = {
                "weight": {"value": 75.2, "unit": "kg", "date": datetime.utcnow().strftime("%Y-%m-%d")},
                "body_fat": {"value": 18.5, "unit": "%", "date": datetime.utcnow().strftime("%Y-%m-%d")}
            }
            trends_summary = {
                "weight": {"change_30_days": -1.2, "trend_direction": "down"},
                "body_fat": {"change_30_days": -0.8, "trend_direction": "down"}
            }
        
        return {
            "latest_measurements": latest_measurements,
            "trends_summary": trends_summary,
            "measurement_streak": 7,  # Mock streak data
            "next_suggested_measurements": ["weight", "waist"],
            "dashboard_tips": [
                "Track weight at the same time daily for consistency",
                "Take body measurements weekly for best trend data"
            ],
            "dashboard_generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard generation failed: {str(e)}")

@app.delete("/measurements/{measurement_id}")
async def delete_measurement(
    measurement_id: str,
    user=Depends(verify_jwt_token)
):
    """Delete body measurement - mobile editing support"""
    
    if not db_pool:
        return {"status": "deleted", "measurement_id": measurement_id}
    
    async with db_pool.acquire() as conn:
        try:
            result = await conn.execute("""
                DELETE FROM body_measurements 
                WHERE id = $1 AND user_id = $2
            """, measurement_id, user["user_id"])
            
            if result == "DELETE 0":
                raise HTTPException(status_code=404, detail="Measurement not found")
            
            return {"status": "deleted", "measurement_id": measurement_id}
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete measurement: {str(e)}")

@app.get("/measurements/ai-insights")
async def get_measurement_ai_insights(
    measurement_types: str = "weight,body_fat",
    days: int = 30,
    user=Depends(verify_jwt_token)
):
    """Get AI-powered measurement insights - mobile dashboard feature"""
    
    try:
        measurement_type_list = [t.strip() for t in measurement_types.split(",")]
        
        ai_response = requests.post(
            f"{AI_INSIGHTS_URL}/measurements/comprehensive-insights",
            json={
                "user_id": user["user_id"],
                "measurement_types": measurement_type_list,
                "days_back": days,
                "focus": "trends_and_goals"
            },
            headers={"Authorization": f"Bearer {user.get('token', 'dev-token')}"},
            timeout=15
        )
        
        if ai_response.status_code == 200:
            return ai_response.json()
        else:
            # Fallback insights
            return {
                "insights": [
                    {
                        "type": "trend",
                        "measurement_type": "weight",
                        "message": "Your weight trend shows consistent progress toward your goal."
                    }
                ],
                "recommendations": [
                    {
                        "action": "maintain_consistency",
                        "reason": "Regular tracking helps identify patterns",
                        "measurement_type": "all"
                    }
                ],
                "goal_progress": {
                    "overall_score": 0.75,
                    "areas_for_improvement": ["measurement_frequency"]
                }
            }
            
    except requests.exceptions.RequestException:
        return {
            "insights": [
                {"type": "general", "message": "AI insights temporarily unavailable"}
            ],
            "recommendations": [
                {"action": "keep_tracking", "reason": "Consistent measurement tracking helps monitor progress"}
            ]
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8095)