from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import uuid
from datetime import datetime

from ..database import get_db, Feedback, User
from .schemas import FeedbackCreate, FeedbackResponse, FeedbackUpdate

router = APIRouter()

@router.post("/submit", response_model=FeedbackResponse)
async def submit_feedback(
    feedback: FeedbackCreate,
    db: AsyncSession = Depends(get_db)
):
    """Submit new user feedback"""
    db_feedback = Feedback(
        user_id=feedback.user_id,
        category=feedback.category,
        rating=feedback.rating,
        title=feedback.title,
        description=feedback.description,
        metadata=feedback.metadata or {},
        priority=feedback.priority or "medium"
    )
    
    db.add(db_feedback)
    await db.commit()
    await db.refresh(db_feedback)
    
    return db_feedback

@router.get("/", response_model=List[FeedbackResponse])
async def get_feedback(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get feedback with optional filtering"""
    query = select(Feedback)
    
    if category:
        query = query.where(Feedback.category == category)
    if status:
        query = query.where(Feedback.status == status)
    
    query = query.offset(skip).limit(limit).order_by(Feedback.created_at.desc())
    
    result = await db.execute(query)
    feedback_list = result.scalars().all()
    
    return feedback_list

@router.get("/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback_by_id(
    feedback_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get specific feedback by ID"""
    result = await db.execute(
        select(Feedback).where(Feedback.id == feedback_id)
    )
    feedback = result.scalar_one_or_none()
    
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    return feedback

@router.put("/{feedback_id}/status")
async def update_feedback_status(
    feedback_id: uuid.UUID,
    status: str = Form(...),
    priority: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Update feedback status and priority"""
    result = await db.execute(
        select(Feedback).where(Feedback.id == feedback_id)
    )
    feedback = result.scalar_one_or_none()
    
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    feedback.status = status
    if priority:
        feedback.priority = priority
    feedback.updated_at = datetime.utcnow()
    
    await db.commit()
    return {"message": "Feedback updated successfully"}

@router.get("/stats/summary")
async def get_feedback_stats(db: AsyncSession = Depends(get_db)):
    """Get feedback statistics summary"""
    # Total feedback count
    total_result = await db.execute(select(Feedback))
    total_count = len(total_result.scalars().all())
    
    # By category
    categories_result = await db.execute(
        select(Feedback.category, Feedback.id).group_by(Feedback.category, Feedback.id)
    )
    categories = {}
    for category, _ in categories_result.all():
        if category in categories:
            categories[category] += 1
        else:
            categories[category] = 1
    
    # By status
    status_result = await db.execute(
        select(Feedback.status, Feedback.id).group_by(Feedback.status, Feedback.id)
    )
    statuses = {}
    for status, _ in status_result.all():
        if status in statuses:
            statuses[status] += 1
        else:
            statuses[status] = 1
    
    # Average rating
    ratings_result = await db.execute(select(Feedback.rating))
    ratings = [r for r, in ratings_result.all() if r is not None]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    
    return {
        "total_feedback": total_count,
        "by_category": categories,
        "by_status": statuses,
        "average_rating": round(avg_rating, 2),
        "total_ratings": len(ratings)
    }