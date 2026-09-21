from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid
from datetime import datetime

from ..database import get_db, RolloutStage, UserRolloutAssignment, RolloutMetrics, User

router = APIRouter()

@router.post("/stages")
async def create_rollout_stage(
    name: str,
    description: str,
    feature_flags: dict,
    user_percentage: float = 0.0,
    db: AsyncSession = Depends(get_db)
):
    """Create a new rollout stage"""
    stage = RolloutStage(
        name=name,
        description=description,
        feature_flags=feature_flags,
        user_percentage=user_percentage
    )
    
    db.add(stage)
    await db.commit()
    await db.refresh(stage)
    
    return stage

@router.get("/stages")
async def get_rollout_stages(db: AsyncSession = Depends(get_db)):
    """Get all rollout stages"""
    result = await db.execute(select(RolloutStage).order_by(RolloutStage.created_at))
    stages = result.scalars().all()
    return stages

@router.put("/stages/{stage_id}/activate")
async def activate_stage(
    stage_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Activate a rollout stage"""
    result = await db.execute(select(RolloutStage).where(RolloutStage.id == stage_id))
    stage = result.scalar_one_or_none()
    
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    
    stage.is_active = True
    stage.updated_at = datetime.utcnow()
    
    await db.commit()
    return {"message": "Stage activated successfully"}

@router.get("/user/{user_id}/features")
async def get_user_features(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get feature flags for a specific user"""
    # Get user's rollout assignment
    assignment_result = await db.execute(
        select(UserRolloutAssignment).where(UserRolloutAssignment.user_id == user_id)
    )
    assignment = assignment_result.scalar_one_or_none()
    
    if not assignment:
        return {"features": {}}
    
    # Get stage features
    stage_result = await db.execute(
        select(RolloutStage).where(RolloutStage.id == assignment.stage_id)
    )
    stage = stage_result.scalar_one_or_none()
    
    if not stage or not stage.is_active:
        return {"features": {}}
    
    return {"features": stage.feature_flags}