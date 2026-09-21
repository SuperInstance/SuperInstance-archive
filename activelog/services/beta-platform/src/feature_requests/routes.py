from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
import uuid
from datetime import datetime

from ..database import get_db, FeatureRequest, FeatureVote, User
from .schemas import FeatureRequestCreate, FeatureRequestResponse, VoteRequest

router = APIRouter()

@router.post("/submit", response_model=FeatureRequestResponse)
async def submit_feature_request(
    feature: FeatureRequestCreate,
    db: AsyncSession = Depends(get_db)
):
    """Submit new feature request"""
    db_feature = FeatureRequest(
        user_id=feature.user_id,
        title=feature.title,
        description=feature.description,
        category=feature.category,
        priority=feature.priority or "medium",
        implementation_effort=feature.implementation_effort,
        business_value=feature.business_value
    )
    
    db.add(db_feature)
    await db.commit()
    await db.refresh(db_feature)
    
    return db_feature

@router.get("/", response_model=List[FeatureRequestResponse])
async def get_feature_requests(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    status: Optional[str] = None,
    sort_by: Optional[str] = "created_at",  # created_at, votes, priority
    db: AsyncSession = Depends(get_db)
):
    """Get feature requests with optional filtering and sorting"""
    query = select(FeatureRequest)
    
    if category:
        query = query.where(FeatureRequest.category == category)
    if status:
        query = query.where(FeatureRequest.status == status)
    
    # Sorting
    if sort_by == "votes":
        query = query.order_by(FeatureRequest.votes.desc())
    elif sort_by == "priority":
        # Custom priority ordering: critical > high > medium > low
        query = query.order_by(
            FeatureRequest.priority.case(
                {"critical": 1, "high": 2, "medium": 3, "low": 4}
            )
        )
    else:
        query = query.order_by(FeatureRequest.created_at.desc())
    
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    features = result.scalars().all()
    
    return features

@router.get("/{feature_id}", response_model=FeatureRequestResponse)
async def get_feature_request(
    feature_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get specific feature request by ID"""
    result = await db.execute(
        select(FeatureRequest).where(FeatureRequest.id == feature_id)
    )
    feature = result.scalar_one_or_none()
    
    if not feature:
        raise HTTPException(status_code=404, detail="Feature request not found")
    
    return feature

@router.post("/{feature_id}/vote")
async def vote_on_feature(
    feature_id: uuid.UUID,
    vote_request: VoteRequest,
    db: AsyncSession = Depends(get_db)
):
    """Vote on a feature request (upvote/downvote)"""
    # Check if feature exists
    feature_result = await db.execute(
        select(FeatureRequest).where(FeatureRequest.id == feature_id)
    )
    feature = feature_result.scalar_one_or_none()
    
    if not feature:
        raise HTTPException(status_code=404, detail="Feature request not found")
    
    # Check if user already voted
    existing_vote_result = await db.execute(
        select(FeatureVote).where(
            and_(
                FeatureVote.user_id == vote_request.user_id,
                FeatureVote.feature_request_id == feature_id
            )
        )
    )
    existing_vote = existing_vote_result.scalar_one_or_none()
    
    if existing_vote:
        if existing_vote.vote_type == vote_request.vote_type:
            # Remove vote if same type
            await db.delete(existing_vote)
            if vote_request.vote_type == "upvote":
                feature.votes = max(0, feature.votes - 1)
            else:
                feature.votes = feature.votes + 1
        else:
            # Change vote type
            existing_vote.vote_type = vote_request.vote_type
            if vote_request.vote_type == "upvote":
                feature.votes = feature.votes + 2  # Remove downvote, add upvote
            else:
                feature.votes = max(0, feature.votes - 2)  # Remove upvote, add downvote
    else:
        # New vote
        new_vote = FeatureVote(
            user_id=vote_request.user_id,
            feature_request_id=feature_id,
            vote_type=vote_request.vote_type
        )
        db.add(new_vote)
        
        if vote_request.vote_type == "upvote":
            feature.votes = feature.votes + 1
        else:
            feature.votes = max(0, feature.votes - 1)
    
    feature.updated_at = datetime.utcnow()
    await db.commit()
    
    return {"message": "Vote recorded successfully", "current_votes": feature.votes}

@router.get("/{feature_id}/votes")
async def get_feature_votes(
    feature_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get vote details for a feature request"""
    # Check if feature exists
    feature_result = await db.execute(
        select(FeatureRequest).where(FeatureRequest.id == feature_id)
    )
    feature = feature_result.scalar_one_or_none()
    
    if not feature:
        raise HTTPException(status_code=404, detail="Feature request not found")
    
    # Get vote breakdown
    votes_result = await db.execute(
        select(FeatureVote).where(FeatureVote.feature_request_id == feature_id)
    )
    votes = votes_result.scalars().all()
    
    upvotes = len([v for v in votes if v.vote_type == "upvote"])
    downvotes = len([v for v in votes if v.vote_type == "downvote"])
    
    return {
        "feature_id": feature_id,
        "total_votes": feature.votes,
        "upvotes": upvotes,
        "downvotes": downvotes,
        "vote_breakdown": {
            "upvote": upvotes,
            "downvote": downvotes
        }
    }

@router.put("/{feature_id}/status")
async def update_feature_status(
    feature_id: uuid.UUID,
    status: str = Form(...),
    priority: Optional[str] = Form(None),
    implementation_effort: Optional[str] = Form(None),
    business_value: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Update feature request status and other attributes"""
    result = await db.execute(
        select(FeatureRequest).where(FeatureRequest.id == feature_id)
    )
    feature = result.scalar_one_or_none()
    
    if not feature:
        raise HTTPException(status_code=404, detail="Feature request not found")
    
    feature.status = status
    if priority:
        feature.priority = priority
    if implementation_effort:
        feature.implementation_effort = implementation_effort
    if business_value:
        feature.business_value = business_value
    feature.updated_at = datetime.utcnow()
    
    await db.commit()
    return {"message": "Feature request updated successfully"}

@router.get("/stats/summary")
async def get_feature_stats(db: AsyncSession = Depends(get_db)):
    """Get feature request statistics"""
    # Total features
    total_result = await db.execute(select(FeatureRequest))
    total_count = len(total_result.scalars().all())
    
    # By status
    status_result = await db.execute(
        select(FeatureRequest.status, FeatureRequest.id).group_by(FeatureRequest.status, FeatureRequest.id)
    )
    statuses = {}
    for status, _ in status_result.all():
        if status in statuses:
            statuses[status] += 1
        else:
            statuses[status] = 1
    
    # By category
    category_result = await db.execute(
        select(FeatureRequest.category, FeatureRequest.id).group_by(FeatureRequest.category, FeatureRequest.id)
    )
    categories = {}
    for category, _ in category_result.all():
        if category and category in categories:
            categories[category] += 1
        elif category:
            categories[category] = 1
    
    # Top voted features
    top_voted_result = await db.execute(
        select(FeatureRequest).order_by(FeatureRequest.votes.desc()).limit(5)
    )
    top_voted = top_voted_result.scalars().all()
    
    return {
        "total_features": total_count,
        "by_status": statuses,
        "by_category": categories,
        "top_voted": [
            {"id": f.id, "title": f.title, "votes": f.votes} 
            for f in top_voted
        ]
    }