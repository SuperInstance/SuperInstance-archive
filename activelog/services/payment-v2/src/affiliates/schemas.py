from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from decimal import Decimal
import uuid

class CreateAffiliateProgramRequest(BaseModel):
    user_id: uuid.UUID
    commission_rate: float = Field(default=0.1, ge=0.01, le=0.5, description="Commission rate (0.01 to 0.5)")
    tier_level: int = Field(default=1, ge=1, le=5, description="Starting tier level")

class ProcessReferralRequest(BaseModel):
    affiliate_code: str = Field(..., min_length=8, max_length=12)
    new_user_id: uuid.UUID

class ProcessCommissionRequest(BaseModel):
    affiliate_id: uuid.UUID
    referred_user_id: uuid.UUID
    transaction_id: str
    original_amount: float = Field(..., gt=0)

class TransactionData(BaseModel):
    user_id: uuid.UUID
    transaction_id: str
    amount: float = Field(..., gt=0)

class BatchCommissionRequest(BaseModel):
    transactions: List[TransactionData] = Field(..., min_items=1)

class AffiliateStatsResponse(BaseModel):
    affiliate_id: str
    program_status: str
    tier_level: int
    commission_rate: float
    lifetime_earnings: float
    total_referrals: int
    recent_referrals: int
    total_commissions: float
    recent_commissions: float
    commission_count: int
    top_referrals: List[Dict[str, Any]]
    period_days: int
    next_tier_requirement: Optional[Dict[str, Any]]
    payout_threshold: float

class LeaderboardEntry(BaseModel):
    rank: int
    affiliate_id: str
    lifetime_earnings: float
    tier_level: int
    total_referrals: int

class CommissionCalculation(BaseModel):
    base_commission: float
    tier_multiplier: float
    final_commission: float
    commission_rate: float
    tier_level: int
    success: Optional[bool] = True
    error: Optional[str] = None