from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import uuid
import os
import aiofiles
from datetime import datetime
from pathlib import Path

from ..database import get_db, BugReport, User
from .schemas import BugReportCreate, BugReportResponse, BugReportUpdate

router = APIRouter()

UPLOAD_DIR = Path("static/screenshots")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/submit", response_model=BugReportResponse)
async def submit_bug_report(
    title: str = Form(...),
    description: str = Form(...),
    user_id: str = Form(...),
    steps_to_reproduce: Optional[str] = Form(None),
    expected_behavior: Optional[str] = Form(None),
    actual_behavior: Optional[str] = Form(None),
    severity: Optional[str] = Form("medium"),
    browser_info: Optional[str] = Form(None),
    device_info: Optional[str] = Form(None),
    screenshots: List[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_db)
):
    """Submit new bug report with optional screenshots"""
    
    # Save uploaded screenshots
    screenshot_paths = []
    for screenshot in screenshots:
        if screenshot.filename:
            file_extension = screenshot.filename.split('.')[-1]
            filename = f"{uuid.uuid4()}.{file_extension}"
            file_path = UPLOAD_DIR / filename
            
            async with aiofiles.open(file_path, 'wb') as f:
                content = await screenshot.read()
                await f.write(content)
            
            screenshot_paths.append(str(file_path))
    
    # Parse JSON strings for browser and device info
    import json
    browser_data = None
    device_data = None
    
    try:
        if browser_info:
            browser_data = json.loads(browser_info)
    except:
        browser_data = {"raw": browser_info}
    
    try:
        if device_info:
            device_data = json.loads(device_info)
    except:
        device_data = {"raw": device_info}
    
    db_bug_report = BugReport(
        user_id=uuid.UUID(user_id),
        title=title,
        description=description,
        steps_to_reproduce=steps_to_reproduce,
        expected_behavior=expected_behavior,
        actual_behavior=actual_behavior,
        severity=severity,
        screenshot_paths=screenshot_paths,
        browser_info=browser_data,
        device_info=device_data
    )
    
    db.add(db_bug_report)
    await db.commit()
    await db.refresh(db_bug_report)
    
    return db_bug_report

@router.get("/", response_model=List[BugReportResponse])
async def get_bug_reports(
    skip: int = 0,
    limit: int = 100,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get bug reports with optional filtering"""
    query = select(BugReport)
    
    if severity:
        query = query.where(BugReport.severity == severity)
    if status:
        query = query.where(BugReport.status == status)
    
    query = query.offset(skip).limit(limit).order_by(BugReport.created_at.desc())
    
    result = await db.execute(query)
    bug_reports = result.scalars().all()
    
    return bug_reports

@router.get("/{bug_id}", response_model=BugReportResponse)
async def get_bug_report(
    bug_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get specific bug report by ID"""
    result = await db.execute(
        select(BugReport).where(BugReport.id == bug_id)
    )
    bug_report = result.scalar_one_or_none()
    
    if not bug_report:
        raise HTTPException(status_code=404, detail="Bug report not found")
    
    return bug_report

@router.put("/{bug_id}/status")
async def update_bug_status(
    bug_id: uuid.UUID,
    status: str = Form(...),
    severity: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Update bug report status and severity"""
    result = await db.execute(
        select(BugReport).where(BugReport.id == bug_id)
    )
    bug_report = result.scalar_one_or_none()
    
    if not bug_report:
        raise HTTPException(status_code=404, detail="Bug report not found")
    
    bug_report.status = status
    if severity:
        bug_report.severity = severity
    bug_report.updated_at = datetime.utcnow()
    
    await db.commit()
    return {"message": "Bug report updated successfully"}

@router.get("/stats/summary")
async def get_bug_stats(db: AsyncSession = Depends(get_db)):
    """Get bug report statistics"""
    # Total bugs
    total_result = await db.execute(select(BugReport))
    total_count = len(total_result.scalars().all())
    
    # By severity
    severity_result = await db.execute(
        select(BugReport.severity, BugReport.id).group_by(BugReport.severity, BugReport.id)
    )
    severities = {}
    for severity, _ in severity_result.all():
        if severity in severities:
            severities[severity] += 1
        else:
            severities[severity] = 1
    
    # By status
    status_result = await db.execute(
        select(BugReport.status, BugReport.id).group_by(BugReport.status, BugReport.id)
    )
    statuses = {}
    for status, _ in status_result.all():
        if status in statuses:
            statuses[status] += 1
        else:
            statuses[status] = 1
    
    return {
        "total_bugs": total_count,
        "by_severity": severities,
        "by_status": statuses
    }