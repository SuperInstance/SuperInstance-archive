from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import uuid
from datetime import datetime

class BugReportCreate(BaseModel):
    user_id: uuid.UUID
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=10)
    steps_to_reproduce: Optional[str] = None
    expected_behavior: Optional[str] = None
    actual_behavior: Optional[str] = None
    severity: Optional[str] = Field("medium", regex="^(low|medium|high|critical)$")
    browser_info: Optional[Dict[str, Any]] = None
    device_info: Optional[Dict[str, Any]] = None

class BugReportUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=10)
    steps_to_reproduce: Optional[str] = None
    expected_behavior: Optional[str] = None
    actual_behavior: Optional[str] = None
    severity: Optional[str] = Field(None, regex="^(low|medium|high|critical)$")
    status: Optional[str] = Field(None, regex="^(open|investigating|fixed|closed)$")

class BugReportResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str
    steps_to_reproduce: Optional[str]
    expected_behavior: Optional[str]
    actual_behavior: Optional[str]
    severity: str
    status: str
    screenshot_paths: Optional[List[str]]
    browser_info: Optional[Dict[str, Any]]
    device_info: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True