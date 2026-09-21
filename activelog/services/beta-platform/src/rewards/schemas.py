from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uuid
from datetime import datetime

class RewardTransactionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    action_type: str
    points_earned: int
    description: str
    metadata: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True

class LeaderboardResponse(BaseModel):
    user_id: uuid.UUID
    username: str
    total_points: int
    beta_tier: str
    rank: int
    recent_activity: Optional[int] = 0  # Points earned in the specified timeframe

class RewardSummaryResponse(BaseModel):
    user_id: uuid.UUID
    username: str
    total_points: int
    beta_tier: str
    points_by_activity: Dict[str, int]
    activity_counts: Dict[str, int]
    achievements: List[str]
    rank: int

class AwardPointsRequest(BaseModel):
    user_id: uuid.UUID
    action_type: str
    points: int
    description: str
    metadata: Optional[Dict[str, Any]] = {}

class RedeemPointsRequest(BaseModel):
    user_id: uuid.UUID
    reward_type: str
    points_cost: int
    description: str