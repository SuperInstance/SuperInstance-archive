from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import uuid
from datetime import datetime

class FeedbackCreate(BaseModel):
    user_id: uuid.UUID
    category: str = Field(..., description="Feedback category: ui, performance, feature, general")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating from 1 to 5 stars")
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    priority: Optional[str] = Field("medium", regex="^(low|medium|high|critical)$")

class FeedbackUpdate(BaseModel):
    category: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[str] = Field(None, regex="^(open|reviewed|implemented|closed)$")
    priority: Optional[str] = Field(None, regex="^(low|medium|high|critical)$")

class FeedbackResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    category: str
    rating: Optional[int]
    title: str
    description: Optional[str]
    metadata: Optional[Dict[str, Any]]
    status: str
    priority: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True