from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid
from datetime import datetime

from ..database import get_db, UsageEvent

router = APIRouter()

@router.post("/track")
async def track_usage_event(
    user_id: uuid.UUID,
    event_type: str,
    event_data: dict,
    url: str = None,
    session_id: str = None,
    browser_info: dict = None,
    device_info: dict = None,
    db: AsyncSession = Depends(get_db)
):
    """Track a usage event"""
    event = UsageEvent(
        user_id=user_id,
        event_type=event_type,
        event_data=event_data,
        url=url,
        session_id=session_id,
        browser_info=browser_info,
        device_info=device_info
    )
    
    db.add(event)
    await db.commit()
    await db.refresh(event)
    
    return {"message": "Event tracked", "id": event.id}

@router.get("/events")
async def get_usage_events(
    event_type: str = None,
    user_id: uuid.UUID = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get usage events with filtering"""
    query = select(UsageEvent)
    
    if event_type:
        query = query.where(UsageEvent.event_type == event_type)
    if user_id:
        query = query.where(UsageEvent.user_id == user_id)
    
    query = query.offset(skip).limit(limit).order_by(UsageEvent.timestamp.desc())
    
    result = await db.execute(query)
    events = result.scalars().all()
    
    return events

@router.get("/stats")
async def get_usage_stats(db: AsyncSession = Depends(get_db)):
    """Get usage analytics summary"""
    result = await db.execute(select(UsageEvent))
    events = result.scalars().all()
    
    # Group by event type
    event_type_stats = {}
    for event in events:
        if event.event_type in event_type_stats:
            event_type_stats[event.event_type] += 1
        else:
            event_type_stats[event.event_type] = 1
    
    # Unique users
    unique_users = len(set(event.user_id for event in events))
    
    return {
        "total_events": len(events),
        "unique_users": unique_users,
        "by_event_type": event_type_stats
    }