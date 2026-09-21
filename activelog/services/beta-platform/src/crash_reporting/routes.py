from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid
from datetime import datetime

from ..database import get_db, CrashReport

router = APIRouter()

@router.post("/submit")
async def submit_crash_report(
    user_id: uuid.UUID,
    error_type: str,
    error_message: str,
    stack_trace: str = None,
    url: str = None,
    user_agent: str = None,
    session_id: str = None,
    browser_info: dict = None,
    device_info: dict = None,
    severity: str = "medium",
    metadata: dict = None,
    db: AsyncSession = Depends(get_db)
):
    """Submit a crash report"""
    crash_report = CrashReport(
        user_id=user_id,
        error_type=error_type,
        error_message=error_message,
        stack_trace=stack_trace,
        url=url,
        user_agent=user_agent,
        session_id=session_id,
        browser_info=browser_info,
        device_info=device_info,
        severity=severity,
        metadata=metadata or {}
    )
    
    db.add(crash_report)
    await db.commit()
    await db.refresh(crash_report)
    
    return {"message": "Crash report submitted", "id": crash_report.id}

@router.get("/")
async def get_crash_reports(
    skip: int = 0,
    limit: int = 100,
    severity: str = None,
    status: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Get crash reports with filtering"""
    query = select(CrashReport)
    
    if severity:
        query = query.where(CrashReport.severity == severity)
    if status:
        query = query.where(CrashReport.status == status)
    
    query = query.offset(skip).limit(limit).order_by(CrashReport.created_at.desc())
    
    result = await db.execute(query)
    crashes = result.scalars().all()
    
    return crashes

@router.get("/stats")
async def get_crash_stats(db: AsyncSession = Depends(get_db)):
    """Get crash statistics"""
    result = await db.execute(select(CrashReport))
    crashes = result.scalars().all()
    
    # Group by severity
    severity_stats = {}
    error_type_stats = {}
    
    for crash in crashes:
        # By severity
        if crash.severity in severity_stats:
            severity_stats[crash.severity] += 1
        else:
            severity_stats[crash.severity] = 1
        
        # By error type
        if crash.error_type in error_type_stats:
            error_type_stats[crash.error_type] += 1
        else:
            error_type_stats[crash.error_type] = 1
    
    return {
        "total_crashes": len(crashes),
        "by_severity": severity_stats,
        "by_error_type": error_type_stats
    }