from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import uuid

class CreditConsumptionRequest(BaseModel):
    user_id: uuid.UUID
    resource_type: str = Field(..., description="Type of resource: cpu, gpu, storage, bandwidth")
    units: float = Field(..., gt=0, description="Number of units consumed")
    tier: str = Field(default="standard", description="Service tier: standard, premium, enterprise")
    region: str = Field(default="global", description="Region for resource consumption")
    job_id: Optional[str] = Field(None, description="Associated job ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class CreditReservationRequest(BaseModel):
    user_id: uuid.UUID
    credits_amount: float = Field(..., gt=0)
    job_id: str
    duration_minutes: int = Field(default=60, description="Reservation duration in minutes")

class CreditPurchaseRequest(BaseModel):
    user_id: uuid.UUID
    usd_amount: float = Field(..., gt=0)
    payment_method_id: str
    bonus_percentage: float = Field(default=0.0, ge=0, le=1.0, description="Bonus credits percentage")

class UsageAnalyticsRequest(BaseModel):
    user_id: Optional[uuid.UUID] = None
    organization_id: Optional[uuid.UUID] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class CreditBalanceResponse(BaseModel):
    user_id: str
    total_balance: float
    reserved_balance: float
    available_balance: float
    auto_recharge_enabled: bool
    auto_recharge_threshold: Optional[float]
    auto_recharge_amount: Optional[float]
    last_updated: str

class ConsumptionResponse(BaseModel):
    success: bool
    credits_consumed: Optional[float] = None
    remaining_balance: Optional[float] = None
    transaction_id: Optional[str] = None
    error: Optional[str] = None
    required: Optional[float] = None
    available: Optional[float] = None
    shortfall: Optional[float] = None