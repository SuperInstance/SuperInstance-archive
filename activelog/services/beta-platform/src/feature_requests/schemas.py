from pydantic import BaseModel, Field
from typing import Optional
import uuid
from datetime import datetime

class FeatureRequestCreate(BaseModel):
    user_id: uuid.UUID
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=10)
    category: Optional[str] = None
    priority: Optional[str] = Field("medium", regex="^(low|medium|high|critical)$")
    implementation_effort: Optional[str] = Field(None, regex="^(small|medium|large)$")
    business_value: Optional[str] = Field(None, regex="^(low|medium|high)$")

class FeatureRequestUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=10)
    category: Optional[str] = None
    priority: Optional[str] = Field(None, regex="^(low|medium|high|critical)$")
    status: Optional[str] = Field(None, regex="^(proposed|approved|in_progress|completed|rejected)$")
    implementation_effort: Optional[str] = Field(None, regex="^(small|medium|large)$")
    business_value: Optional[str] = Field(None, regex="^(low|medium|high)$")

class VoteRequest(BaseModel):
    user_id: uuid.UUID
    vote_type: str = Field(..., regex="^(upvote|downvote)$")

class FeatureRequestResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str
    category: Optional[str]
    priority: str
    status: str
    votes: int
    implementation_effort: Optional[str]
    business_value: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class VoteResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    feature_request_id: uuid.UUID
    vote_type: str
    created_at: datetime

    class Config:
        from_attributes = True