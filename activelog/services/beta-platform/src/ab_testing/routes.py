from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid
import random
from datetime import datetime

from ..database import get_db, ABTest, ABTestAssignment, ABTestResult

router = APIRouter()

@router.post("/tests")
async def create_ab_test(
    name: str,
    description: str,
    hypothesis: str,
    variants: List[dict],
    traffic_allocation: dict,
    success_metrics: List[str],
    target_users: dict = None,
    db: AsyncSession = Depends(get_db)
):
    """Create a new A/B test"""
    test = ABTest(
        name=name,
        description=description,
        hypothesis=hypothesis,
        variants=variants,
        traffic_allocation=traffic_allocation,
        target_users=target_users or {},
        success_metrics=success_metrics
    )
    
    db.add(test)
    await db.commit()
    await db.refresh(test)
    
    return test

@router.get("/tests")
async def get_ab_tests(
    status: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Get A/B tests"""
    query = select(ABTest)
    
    if status:
        query = query.where(ABTest.status == status)
    
    query = query.order_by(ABTest.created_at.desc())
    
    result = await db.execute(query)
    tests = result.scalars().all()
    
    return tests

@router.post("/tests/{test_id}/start")
async def start_ab_test(
    test_id: uuid.UUID,
    start_date: datetime = None,
    end_date: datetime = None,
    db: AsyncSession = Depends(get_db)
):
    """Start an A/B test"""
    result = await db.execute(select(ABTest).where(ABTest.id == test_id))
    test = result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    
    test.status = "running"
    test.start_date = start_date or datetime.utcnow()
    if end_date:
        test.end_date = end_date
    test.updated_at = datetime.utcnow()
    
    await db.commit()
    return {"message": "A/B test started"}

@router.get("/tests/{test_id}/assign/{user_id}")
async def assign_user_to_variant(
    test_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Assign a user to a test variant"""
    # Check if user already assigned
    existing_result = await db.execute(
        select(ABTestAssignment).where(
            ABTestAssignment.test_id == test_id,
            ABTestAssignment.user_id == user_id
        )
    )
    existing_assignment = existing_result.scalar_one_or_none()
    
    if existing_assignment:
        return {"variant": existing_assignment.variant}
    
    # Get test
    test_result = await db.execute(select(ABTest).where(ABTest.id == test_id))
    test = test_result.scalar_one_or_none()
    
    if not test or test.status != "running":
        raise HTTPException(status_code=400, detail="Test not available")
    
    # Assign variant based on traffic allocation
    variant = _select_variant(test.traffic_allocation)
    
    assignment = ABTestAssignment(
        test_id=test_id,
        user_id=user_id,
        variant=variant
    )
    
    db.add(assignment)
    await db.commit()
    
    return {"variant": variant}

@router.post("/tests/{test_id}/results")
async def record_test_result(
    test_id: uuid.UUID,
    user_id: uuid.UUID,
    metric_name: str,
    metric_value: float,
    metadata: dict = None,
    db: AsyncSession = Depends(get_db)
):
    """Record a test result/metric"""
    # Get user's variant assignment
    assignment_result = await db.execute(
        select(ABTestAssignment).where(
            ABTestAssignment.test_id == test_id,
            ABTestAssignment.user_id == user_id
        )
    )
    assignment = assignment_result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(status_code=400, detail="User not assigned to test")
    
    result = ABTestResult(
        test_id=test_id,
        user_id=user_id,
        variant=assignment.variant,
        metric_name=metric_name,
        metric_value=metric_value,
        metadata=metadata or {}
    )
    
    db.add(result)
    await db.commit()
    
    return {"message": "Result recorded"}

@router.get("/tests/{test_id}/analysis")
async def get_test_analysis(
    test_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get A/B test analysis results"""
    # Get test results
    results_query = await db.execute(
        select(ABTestResult).where(ABTestResult.test_id == test_id)
    )
    results = results_query.scalars().all()
    
    # Group by variant and metric
    analysis = {}
    for result in results:
        variant = result.variant
        metric = result.metric_name
        
        if variant not in analysis:
            analysis[variant] = {}
        if metric not in analysis[variant]:
            analysis[variant][metric] = []
        
        analysis[variant][metric].append(result.metric_value)
    
    # Calculate statistics
    stats = {}
    for variant, metrics in analysis.items():
        stats[variant] = {}
        for metric, values in metrics.items():
            stats[variant][metric] = {
                "count": len(values),
                "mean": sum(values) / len(values),
                "min": min(values),
                "max": max(values)
            }
    
    return stats

def _select_variant(traffic_allocation: dict) -> str:
    """Select a variant based on traffic allocation"""
    rand = random.random()
    cumulative = 0.0
    
    for variant, allocation in traffic_allocation.items():
        cumulative += allocation
        if rand <= cumulative:
            return variant
    
    # Fallback to first variant
    return list(traffic_allocation.keys())[0]