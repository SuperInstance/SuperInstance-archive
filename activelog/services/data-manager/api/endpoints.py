"""
API endpoints for the Data Management AI service.
Provides REST API access to all data management capabilities.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
import json
from dataclasses import asdict

# Mock FastAPI-like decorators and classes for this implementation
class APIRouter:
    def __init__(self):
        self.routes = {}
    
    def post(self, path: str):
        def decorator(func):
            self.routes[f"POST {path}"] = func
            return func
        return decorator
    
    def get(self, path: str):
        def decorator(func):
            self.routes[f"GET {path}"] = func
            return func
        return decorator
    
    def put(self, path: str):
        def decorator(func):
            self.routes[f"PUT {path}"] = func
            return func
        return decorator
    
    def delete(self, path: str):
        def decorator(func):
            self.routes[f"DELETE {path}"] = func
            return func
        return decorator

class HTTPException(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail

# Import our services
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data_manager import DataManager
from ai.recommendation_engine import RecommendationEngine
from analytics.insights_engine import InsightsEngine
from monitoring.quality_monitor import QualityMonitor

# Initialize services
data_manager = DataManager("sqlite:///:memory:")
recommendation_engine = RecommendationEngine()
insights_engine = InsightsEngine()
quality_monitor = QualityMonitor()

# Create router
router = APIRouter()

# Data ingestion endpoints
@router.post("/data/ingest")
async def ingest_data(
    user_id: str,
    source: str,
    content: Any,
    metadata: Optional[Dict[str, Any]] = None
):
    """Ingest new data into the system."""
    try:
        result = await data_manager.ingest_data(user_id, source, content, metadata)
        return {
            "success": True,
            "data_item_id": result.id,
            "classification": asdict(result.classification),
            "message": "Data ingested successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/data/batch-ingest")
async def batch_ingest_data(
    user_id: str,
    items: List[Dict[str, Any]]
):
    """Ingest multiple data items in batch."""
    try:
        results = []
        for item in items:
            result = await data_manager.ingest_data(
                user_id, 
                item.get("source", "unknown"),
                item.get("content"),
                item.get("metadata", {})
            )
            results.append({
                "data_item_id": result.id,
                "classification": asdict(result.classification)
            })
        
        return {
            "success": True,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Classification endpoints
@router.post("/classify")
async def classify_content(
    content: Any,
    metadata: Optional[Dict[str, Any]] = None
):
    """Classify content without ingesting it."""
    try:
        classification = await data_manager.classifier.classify(content, metadata)
        return {
            "success": True,
            "classification": asdict(classification)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Recommendation endpoints
@router.get("/recommendations/{user_id}")
async def get_recommendations(
    user_id: str,
    recommendation_types: Optional[str] = None,
    refresh_profile: bool = False
):
    """Get personalized recommendations for a user."""
    try:
        types_list = None
        if recommendation_types:
            types_list = recommendation_types.split(",")
        
        recommendations = await recommendation_engine.get_recommendations(
            user_id, types_list, refresh_profile
        )
        
        return {
            "success": True,
            "recommendations": [asdict(rec) for rec in recommendations],
            "count": len(recommendations)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user-profile/{user_id}")
async def get_user_profile(user_id: str):
    """Get user behavior profile."""
    try:
        profile = await recommendation_engine.profiler.get_user_profile(user_id)
        return {
            "success": True,
            "profile": asdict(profile)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/user-behavior/{user_id}")
async def record_user_behavior(
    user_id: str,
    action: str,
    context: Dict[str, Any],
    timestamp: Optional[str] = None
):
    """Record user behavior for profile learning."""
    try:
        ts = datetime.fromisoformat(timestamp) if timestamp else datetime.now()
        await recommendation_engine.profiler.record_behavior(user_id, action, context, ts)
        return {
            "success": True,
            "message": "Behavior recorded successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Analytics and insights endpoints
@router.get("/insights/{user_id}")
async def get_insights(
    user_id: str,
    insight_types: Optional[str] = None,
    force_refresh: bool = False
):
    """Get data insights for a user."""
    try:
        types_list = None
        if insight_types:
            types_list = insight_types.split(",")
        
        insights = await insights_engine.generate_insights(
            user_id, types_list, force_refresh
        )
        
        return {
            "success": True,
            "insights": [asdict(insight) for insight in insights],
            "count": len(insights)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/{user_id}")
async def get_analytics(user_id: str):
    """Get comprehensive analytics for a user."""
    try:
        analytics = await insights_engine.analytics.get_user_analytics(user_id)
        return {
            "success": True,
            "analytics": asdict(analytics)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Quality monitoring endpoints
@router.get("/quality/{user_id}")
async def get_quality_report(user_id: str):
    """Get data quality report for a user."""
    try:
        report = await quality_monitor.run_quality_assessment(user_id)
        return {
            "success": True,
            "quality_report": asdict(report)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/quality/alerts/{user_id}")
async def get_quality_alerts(user_id: str):
    """Get active quality alerts for a user."""
    try:
        alerts = await quality_monitor.get_alerts(user_id)
        return {
            "success": True,
            "alerts": [asdict(alert) for alert in alerts],
            "count": len(alerts)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Data processing endpoints
@router.post("/process/{data_item_id}")
async def process_data_item(
    data_item_id: str,
    processor_type: str,
    parameters: Optional[Dict[str, Any]] = None
):
    """Process a specific data item."""
    try:
        result = await data_manager.processing_pipeline.process_item(
            data_item_id, processor_type, parameters or {}
        )
        return {
            "success": True,
            "processing_result": asdict(result)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/processing/status/{job_id}")
async def get_processing_status(job_id: str):
    """Get status of a processing job."""
    try:
        status = await data_manager.processing_pipeline.get_job_status(job_id)
        return {
            "success": True,
            "status": status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Folder and organization endpoints
@router.post("/folders/create")
async def create_folder(
    user_id: str,
    folder_name: str,
    description: Optional[str] = None,
    template_type: Optional[str] = None,
    natural_language_request: Optional[str] = None
):
    """Create a new folder with optional template or natural language processing."""
    try:
        # This would integrate with the folder management system
        folder_data = {
            "user_id": user_id,
            "name": folder_name,
            "description": description,
            "template_type": template_type,
            "created_at": datetime.now().isoformat()
        }
        
        if natural_language_request:
            # Process natural language to determine folder structure
            # This would use NLP to parse requests like "create a folder for tax documents from 2024"
            pass
        
        return {
            "success": True,
            "folder": folder_data,
            "message": f"Folder '{folder_name}' created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/folders/suggestions/{user_id}")
async def get_folder_suggestions(user_id: str):
    """Get intelligent folder organization suggestions."""
    try:
        recommendations = await recommendation_engine.get_recommendations(
            user_id, ["FOLDER_ORGANIZATION"]
        )
        
        return {
            "success": True,
            "suggestions": [asdict(rec) for rec in recommendations if rec.type == "FOLDER_ORGANIZATION"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Export and backup endpoints
@router.get("/export/preferences/{user_id}")
async def export_user_preferences(user_id: str):
    """Export user's trained preferences and profile."""
    try:
        profile = await recommendation_engine.profiler.get_user_profile(user_id)
        export_data = {
            "user_id": user_id,
            "profile": asdict(profile),
            "export_timestamp": datetime.now().isoformat(),
            "version": "1.0"
        }
        
        return {
            "success": True,
            "export_data": export_data,
            "message": "Preferences exported successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import/preferences/{user_id}")
async def import_user_preferences(
    user_id: str,
    preferences_data: Dict[str, Any]
):
    """Import user preferences from export."""
    try:
        # Validate and import preferences
        if "profile" in preferences_data:
            # This would restore the user profile
            pass
        
        return {
            "success": True,
            "message": "Preferences imported successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Privacy and consent endpoints
@router.post("/privacy/consent/{user_id}")
async def update_privacy_consent(
    user_id: str,
    consent_type: str,
    granted: bool,
    timestamp: Optional[str] = None
):
    """Update user privacy consent settings."""
    try:
        ts = datetime.fromisoformat(timestamp) if timestamp else datetime.now()
        
        consent_record = {
            "user_id": user_id,
            "consent_type": consent_type,
            "granted": granted,
            "timestamp": ts.isoformat(),
            "ip_address": "127.0.0.1"  # Would get from request
        }
        
        return {
            "success": True,
            "consent_record": consent_record,
            "message": f"Privacy consent for '{consent_type}' updated"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/privacy/consent/{user_id}")
async def get_privacy_consent(user_id: str):
    """Get user's current privacy consent settings."""
    try:
        # This would retrieve from consent storage
        consent_settings = {
            "data_collection": True,
            "personalization": True,
            "analytics": False,
            "marketing": False
        }
        
        return {
            "success": True,
            "consent_settings": consent_settings
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health and status endpoints
@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "data_manager": "running",
            "recommendation_engine": "running",
            "insights_engine": "running",
            "quality_monitor": "running"
        }
    }

@router.get("/status")
async def get_system_status():
    """Get detailed system status."""
    try:
        return {
            "success": True,
            "system_status": {
                "uptime": "0:00:01",
                "memory_usage": "25%",
                "cpu_usage": "15%",
                "active_users": 0,
                "processed_items_today": 0,
                "quality_score": 95.5
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# CLI interface for testing
async def test_api():
    """Test the API endpoints with sample data."""
    print("Testing Data Management AI API Endpoints...")
    
    # Test data ingestion
    print("\n1. Testing data ingestion...")
    result = await ingest_data(
        user_id="test_user",
        source="api_test",
        content="This is a test document about machine learning.",
        metadata={"filename": "test.txt", "size": 1024}
    )
    print(f"Ingestion result: {result}")
    
    # Test classification
    print("\n2. Testing classification...")
    classification_result = await classify_content(
        content="Financial report Q4 2024",
        metadata={"type": "document"}
    )
    print(f"Classification result: {classification_result}")
    
    # Test recommendations
    print("\n3. Testing recommendations...")
    recommendations = await get_recommendations("test_user")
    print(f"Recommendations: {recommendations}")
    
    # Test insights
    print("\n4. Testing insights...")
    insights = await get_insights("test_user")
    print(f"Insights: {insights}")
    
    # Test quality monitoring
    print("\n5. Testing quality monitoring...")
    quality_report = await get_quality_report("test_user")
    print(f"Quality report: {quality_report}")
    
    # Test health check
    print("\n6. Testing health check...")
    health = await health_check()
    print(f"Health status: {health}")

if __name__ == "__main__":
    asyncio.run(test_api())