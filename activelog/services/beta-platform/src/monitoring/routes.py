from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid
from datetime import datetime

from ..database import get_db, PerformanceMetric

router = APIRouter()

@router.post("/performance")
async def record_performance_metric(
    user_id: uuid.UUID,
    metric_type: str,
    metric_value: float,
    url: str = None,
    browser_info: dict = None,
    device_info: dict = None,
    session_id: str = None,
    metadata: dict = None,
    db: AsyncSession = Depends(get_db)
):
    """Record a performance metric"""
    metric = PerformanceMetric(
        user_id=user_id,
        metric_type=metric_type,
        metric_value=metric_value,
        url=url,
        browser_info=browser_info,
        device_info=device_info,
        session_id=session_id,
        metadata=metadata or {}
    )
    
    db.add(metric)
    await db.commit()
    await db.refresh(metric)
    
    return {"message": "Performance metric recorded", "id": metric.id}

@router.get("/performance/stats")
async def get_performance_stats(db: AsyncSession = Depends(get_db)):
    """Get performance statistics summary"""
    result = await db.execute(select(PerformanceMetric))
    metrics = result.scalars().all()
    
    # Group by metric type and calculate averages
    stats = {}
    for metric in metrics:
        if metric.metric_type not in stats:
            stats[metric.metric_type] = []
        stats[metric.metric_type].append(metric.metric_value)
    
    summary = {}
    for metric_type, values in stats.items():
        summary[metric_type] = {
            "average": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "count": len(values)
        }
    
    return summary