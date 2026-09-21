from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from typing import Optional, List
import uuid
from datetime import datetime

from ..database import RewardTransaction, User
from .schemas import LeaderboardResponse

class RewardService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def award_points(
        self, 
        user_id: uuid.UUID, 
        action_type: str, 
        points: int, 
        description: str, 
        metadata: dict = {}
    ) -> RewardTransaction:
        """Award points to a user and update their total"""
        
        # Create transaction
        transaction = RewardTransaction(
            user_id=user_id,
            action_type=action_type,
            points_earned=points,
            description=description,
            metadata=metadata
        )
        
        self.db.add(transaction)
        
        # Update user's total points
        user_result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if user:
            user.reward_points = max(0, user.reward_points + points)
            
            # Update tier based on points
            if user.reward_points >= 1500:
                user.beta_tier = "enterprise"
            elif user.reward_points >= 500:
                user.beta_tier = "premium"
            else:
                user.beta_tier = "basic"
        
        await self.db.commit()
        await self.db.refresh(transaction)
        
        return transaction
    
    async def get_user_total_points(self, user_id: uuid.UUID) -> int:
        """Get total points for a user"""
        result = await self.db.execute(
            select(User.reward_points).where(User.id == user_id)
        )
        points = result.scalar_one_or_none()
        return points or 0
    
    async def get_leaderboard(
        self, 
        limit: int = 50, 
        since: Optional[datetime] = None
    ) -> List[LeaderboardResponse]:
        """Get leaderboard of top users by points"""
        
        if since:
            # Get points earned since a specific date
            recent_points_query = (
                select(
                    RewardTransaction.user_id,
                    func.sum(RewardTransaction.points_earned).label('recent_points')
                )
                .where(RewardTransaction.created_at >= since)
                .group_by(RewardTransaction.user_id)
            ).subquery()
            
            query = (
                select(
                    User.id,
                    User.username,
                    User.reward_points,
                    User.beta_tier,
                    func.coalesce(recent_points_query.c.recent_points, 0).label('recent_activity')
                )
                .outerjoin(recent_points_query, User.id == recent_points_query.c.user_id)
                .order_by(desc(func.coalesce(recent_points_query.c.recent_points, 0)))
                .limit(limit)
            )
        else:
            # Get all-time leaderboard
            query = (
                select(User.id, User.username, User.reward_points, User.beta_tier)
                .order_by(desc(User.reward_points))
                .limit(limit)
            )
        
        result = await self.db.execute(query)
        rows = result.all()
        
        leaderboard = []
        for rank, row in enumerate(rows, 1):
            leaderboard.append(LeaderboardResponse(
                user_id=row.id,
                username=row.username,
                total_points=row.reward_points,
                beta_tier=row.beta_tier,
                rank=rank,
                recent_activity=getattr(row, 'recent_activity', 0) if since else 0
            ))
        
        return leaderboard
    
    async def get_user_rank(self, user_id: uuid.UUID) -> int:
        """Get user's current rank in the leaderboard"""
        user_points_result = await self.db.execute(
            select(User.reward_points).where(User.id == user_id)
        )
        user_points = user_points_result.scalar_one_or_none() or 0
        
        # Count users with more points
        higher_ranked_result = await self.db.execute(
            select(func.count(User.id)).where(User.reward_points > user_points)
        )
        higher_ranked_count = higher_ranked_result.scalar() or 0
        
        return higher_ranked_count + 1
    
    async def calculate_activity_rewards(self, user_id: uuid.UUID):
        """Calculate and award points for recent activity"""
        # This would be called by a background task
        # Check for recent feedback, bug reports, feature requests
        # Award points automatically based on activity
        
        # Implementation would depend on specific business rules
        # For now, this is a placeholder
        pass