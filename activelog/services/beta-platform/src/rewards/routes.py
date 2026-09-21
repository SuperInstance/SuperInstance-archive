from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from typing import List, Optional
import uuid
from datetime import datetime, timedelta

from ..database import get_db, RewardTransaction, User, Feedback, BugReport, FeatureRequest
from .schemas import RewardTransactionResponse, LeaderboardResponse, RewardSummaryResponse
from .service import RewardService

router = APIRouter()

@router.post("/award")
async def award_points(
    user_id: uuid.UUID,
    action_type: str,
    points: int,
    description: str,
    metadata: dict = {},
    db: AsyncSession = Depends(get_db)
):
    """Award points to a user for beta testing activities"""
    reward_service = RewardService(db)
    
    transaction = await reward_service.award_points(
        user_id=user_id,
        action_type=action_type,
        points=points,
        description=description,
        metadata=metadata
    )
    
    return {
        "message": "Points awarded successfully",
        "transaction_id": transaction.id,
        "points_awarded": points,
        "total_points": await reward_service.get_user_total_points(user_id)
    }

@router.get("/user/{user_id}/balance")
async def get_user_balance(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get user's current reward points balance"""
    reward_service = RewardService(db)
    
    # Get user
    user_result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    total_points = await reward_service.get_user_total_points(user_id)
    
    return {
        "user_id": user_id,
        "username": user.username,
        "total_points": total_points,
        "beta_tier": user.beta_tier
    }

@router.get("/user/{user_id}/transactions", response_model=List[RewardTransactionResponse])
async def get_user_transactions(
    user_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get user's reward transaction history"""
    result = await db.execute(
        select(RewardTransaction)
        .where(RewardTransaction.user_id == user_id)
        .order_by(desc(RewardTransaction.created_at))
        .offset(skip)
        .limit(limit)
    )
    
    transactions = result.scalars().all()
    return transactions

@router.get("/leaderboard", response_model=List[LeaderboardResponse])
async def get_leaderboard(
    limit: int = 50,
    timeframe: Optional[str] = None,  # weekly, monthly, all_time
    db: AsyncSession = Depends(get_db)
):
    """Get rewards leaderboard"""
    reward_service = RewardService(db)
    
    # Calculate timeframe filter
    time_filter = None
    if timeframe == "weekly":
        time_filter = datetime.utcnow() - timedelta(weeks=1)
    elif timeframe == "monthly":
        time_filter = datetime.utcnow() - timedelta(days=30)
    
    # Get leaderboard data
    leaderboard = await reward_service.get_leaderboard(limit=limit, since=time_filter)
    
    return leaderboard

@router.get("/user/{user_id}/summary", response_model=RewardSummaryResponse)
async def get_user_reward_summary(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive reward summary for a user"""
    reward_service = RewardService(db)
    
    # Check if user exists
    user_result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get total points
    total_points = await reward_service.get_user_total_points(user_id)
    
    # Get points by activity type
    transactions_result = await db.execute(
        select(RewardTransaction).where(RewardTransaction.user_id == user_id)
    )
    transactions = transactions_result.scalars().all()
    
    points_by_activity = {}
    for transaction in transactions:
        activity = transaction.action_type
        if activity in points_by_activity:
            points_by_activity[activity] += transaction.points_earned
        else:
            points_by_activity[activity] = transaction.points_earned
    
    # Get activity counts
    feedback_count_result = await db.execute(
        select(Feedback).where(Feedback.user_id == user_id)
    )
    feedback_count = len(feedback_count_result.scalars().all())
    
    bug_count_result = await db.execute(
        select(BugReport).where(BugReport.user_id == user_id)
    )
    bug_count = len(bug_count_result.scalars().all())
    
    feature_count_result = await db.execute(
        select(FeatureRequest).where(FeatureRequest.user_id == user_id)
    )
    feature_count = len(feature_count_result.scalars().all())
    
    # Calculate achievements
    achievements = []
    if feedback_count >= 10:
        achievements.append("Feedback Champion")
    if bug_count >= 5:
        achievements.append("Bug Hunter")
    if feature_count >= 3:
        achievements.append("Idea Generator")
    if total_points >= 1000:
        achievements.append("Super Tester")
    
    return RewardSummaryResponse(
        user_id=user_id,
        username=user.username,
        total_points=total_points,
        beta_tier=user.beta_tier,
        points_by_activity=points_by_activity,
        activity_counts={
            "feedback_submitted": feedback_count,
            "bugs_reported": bug_count,
            "features_requested": feature_count
        },
        achievements=achievements,
        rank=await reward_service.get_user_rank(user_id)
    )

@router.get("/tiers")
async def get_reward_tiers():
    """Get available reward tiers and their requirements"""
    return {
        "tiers": [
            {
                "name": "basic",
                "min_points": 0,
                "max_points": 499,
                "benefits": ["Basic beta access", "Community forum access"],
                "color": "#6B7280"
            },
            {
                "name": "premium", 
                "min_points": 500,
                "max_points": 1499,
                "benefits": ["Early feature previews", "Priority bug fixes", "Direct feedback channel"],
                "color": "#3B82F6"
            },
            {
                "name": "enterprise",
                "min_points": 1500,
                "max_points": None,
                "benefits": ["Beta feature influence", "One-on-one sessions", "Custom integrations"],
                "color": "#F59E0B"
            }
        ],
        "point_values": {
            "feedback_submission": 10,
            "bug_report": 25,
            "feature_request": 15,
            "testing_session": 50,
            "community_help": 5
        }
    }

@router.post("/redeem")
async def redeem_points(
    user_id: uuid.UUID,
    reward_type: str,
    points_cost: int,
    description: str,
    db: AsyncSession = Depends(get_db)
):
    """Redeem points for rewards"""
    reward_service = RewardService(db)
    
    # Check user balance
    current_points = await reward_service.get_user_total_points(user_id)
    
    if current_points < points_cost:
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient points. Current: {current_points}, Required: {points_cost}"
        )
    
    # Deduct points
    transaction = await reward_service.award_points(
        user_id=user_id,
        action_type=f"redeem_{reward_type}",
        points=-points_cost,
        description=f"Redeemed: {description}",
        metadata={"redemption_type": reward_type}
    )
    
    new_balance = await reward_service.get_user_total_points(user_id)
    
    return {
        "message": "Points redeemed successfully",
        "transaction_id": transaction.id,
        "points_redeemed": points_cost,
        "remaining_balance": new_balance
    }