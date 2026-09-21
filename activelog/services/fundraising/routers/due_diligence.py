"""
Due Diligence Tools and Verification Systems
Comprehensive verification and analysis tools for app listings
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import sqlite3
import json
import requests
from datetime import datetime, timedelta
import hashlib
import re

router = APIRouter(prefix="/due-diligence", tags=["Due Diligence"])

DATABASE_PATH = "fundraising_platform.db"

def get_db_connection():
    return sqlite3.connect(DATABASE_PATH)

# Pydantic models
class DueDiligenceData(BaseModel):
    listing_id: str
    revenue_verified: bool = False
    user_growth_data: str = ""
    code_quality_score: float = 0.0
    security_score: float = 0.0
    legal_structure: str = ""
    competitive_analysis: str = ""
    market_size: float = 0.0
    risk_disclosures: str = ""

class RevenueVerification(BaseModel):
    monthly_revenue: List[float]
    revenue_sources: List[str]
    payment_processor_data: Optional[str] = None
    bank_statements: Optional[str] = None

class UserGrowthMetrics(BaseModel):
    daily_active_users: List[int]
    monthly_active_users: List[int]
    retention_rates: List[float]
    churn_rate: float
    growth_channels: List[str]

class CodeQualityAnalysis(BaseModel):
    lines_of_code: int
    test_coverage: float
    code_complexity: float
    security_vulnerabilities: int
    dependency_analysis: Dict[str, Any]
    performance_metrics: Dict[str, float]

class SecurityAuditResults(BaseModel):
    vulnerability_count: int
    critical_issues: List[str]
    security_score: float
    compliance_status: Dict[str, bool]
    recommendations: List[str]

class CompetitiveAnalysis(BaseModel):
    direct_competitors: List[str]
    market_position: str
    competitive_advantages: List[str]
    market_threats: List[str]
    differentiation_factors: List[str]

@router.post("/create")
async def create_due_diligence(dd_data: DueDiligenceData):
    """Create or update due diligence data for a listing"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if listing exists
    cursor.execute("SELECT id FROM app_listings WHERE id = ?", (dd_data.listing_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Listing not found")
    
    dd_id = str(hash(dd_data.listing_id))
    
    # Insert or update due diligence data
    cursor.execute('''
        INSERT OR REPLACE INTO due_diligence (
            id, listing_id, revenue_verified, user_growth_data, code_quality_score,
            security_score, legal_structure, competitive_analysis, market_size,
            risk_disclosures, last_updated
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        dd_id, dd_data.listing_id, dd_data.revenue_verified, dd_data.user_growth_data,
        dd_data.code_quality_score, dd_data.security_score, dd_data.legal_structure,
        dd_data.competitive_analysis, dd_data.market_size, dd_data.risk_disclosures,
        datetime.now().isoformat()
    ))
    
    conn.commit()
    conn.close()
    
    return {
        "message": "Due diligence data updated successfully",
        "dd_id": dd_id,
        "verification_score": calculate_verification_score(dd_data)
    }

@router.get("/{listing_id}")
async def get_due_diligence(listing_id: str):
    """Get due diligence data for a listing"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM due_diligence WHERE listing_id = ?", (listing_id,))
    dd_data = cursor.fetchone()
    
    if not dd_data:
        raise HTTPException(status_code=404, detail="Due diligence data not found")
    
    columns = [desc[0] for desc in cursor.description]
    dd_dict = dict(zip(columns, dd_data))
    
    # Parse JSON fields
    if dd_dict.get('user_growth_data'):
        try:
            dd_dict['user_growth_data'] = json.loads(dd_dict['user_growth_data'])
        except:
            pass
    
    if dd_dict.get('competitive_analysis'):
        try:
            dd_dict['competitive_analysis'] = json.loads(dd_dict['competitive_analysis'])
        except:
            pass
    
    conn.close()
    return dd_dict

@router.post("/{listing_id}/revenue-verification")
async def verify_revenue(listing_id: str, revenue_data: RevenueVerification):
    """Verify revenue claims for a listing"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if listing exists
    cursor.execute("SELECT id FROM app_listings WHERE id = ?", (listing_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Listing not found")
    
    # Analyze revenue data
    verification_result = analyze_revenue_data(revenue_data)
    
    # Update due diligence with verification status
    cursor.execute('''
        UPDATE due_diligence 
        SET revenue_verified = ?, last_updated = ?
        WHERE listing_id = ?
    ''', (verification_result['verified'], datetime.now().isoformat(), listing_id))
    
    conn.commit()
    conn.close()
    
    return {
        "verified": verification_result['verified'],
        "confidence_score": verification_result['confidence'],
        "analysis": verification_result['analysis'],
        "recommendations": verification_result['recommendations']
    }

@router.post("/{listing_id}/user-growth-analysis")
async def analyze_user_growth(listing_id: str, growth_data: UserGrowthMetrics):
    """Analyze user growth metrics and patterns"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if listing exists
    cursor.execute("SELECT id FROM app_listings WHERE id = ?", (listing_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Listing not found")
    
    # Analyze growth patterns
    analysis_result = analyze_growth_patterns(growth_data)
    
    # Update due diligence data
    growth_data_json = json.dumps({
        "daily_active_users": growth_data.daily_active_users,
        "monthly_active_users": growth_data.monthly_active_users,
        "retention_rates": growth_data.retention_rates,
        "churn_rate": growth_data.churn_rate,
        "growth_channels": growth_data.growth_channels,
        "analysis": analysis_result
    })
    
    cursor.execute('''
        UPDATE due_diligence 
        SET user_growth_data = ?, last_updated = ?
        WHERE listing_id = ?
    ''', (growth_data_json, datetime.now().isoformat(), listing_id))
    
    conn.commit()
    conn.close()
    
    return analysis_result

@router.post("/{listing_id}/code-quality-analysis")
async def analyze_code_quality(listing_id: str, code_data: CodeQualityAnalysis):
    """Perform code quality analysis"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if listing exists
    cursor.execute("SELECT id FROM app_listings WHERE id = ?", (listing_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Listing not found")
    
    # Calculate code quality score
    quality_score = calculate_code_quality_score(code_data)
    
    # Update due diligence data
    cursor.execute('''
        UPDATE due_diligence 
        SET code_quality_score = ?, last_updated = ?
        WHERE listing_id = ?
    ''', (quality_score, datetime.now().isoformat(), listing_id))
    
    conn.commit()
    conn.close()
    
    return {
        "quality_score": quality_score,
        "grade": get_quality_grade(quality_score),
        "analysis": generate_code_analysis_report(code_data),
        "recommendations": get_code_improvement_recommendations(code_data)
    }

@router.post("/{listing_id}/security-audit")
async def perform_security_audit(listing_id: str, security_data: SecurityAuditResults):
    """Perform security audit and risk assessment"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if listing exists
    cursor.execute("SELECT id FROM app_listings WHERE id = ?", (listing_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Listing not found")
    
    # Calculate security score
    security_score = calculate_security_score(security_data)
    
    # Update due diligence data
    cursor.execute('''
        UPDATE due_diligence 
        SET security_score = ?, last_updated = ?
        WHERE listing_id = ?
    ''', (security_score, datetime.now().isoformat(), listing_id))
    
    conn.commit()
    conn.close()
    
    return {
        "security_score": security_score,
        "risk_level": get_risk_level(security_score),
        "critical_issues": security_data.critical_issues,
        "compliance_status": security_data.compliance_status,
        "recommendations": security_data.recommendations
    }

@router.post("/{listing_id}/competitive-analysis")
async def create_competitive_analysis(listing_id: str, comp_data: CompetitiveAnalysis):
    """Create competitive analysis for a listing"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if listing exists
    cursor.execute("SELECT id FROM app_listings WHERE id = ?", (listing_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Listing not found")
    
    # Analyze competitive position
    analysis_result = analyze_competitive_position(comp_data)
    
    # Update due diligence data
    comp_analysis_json = json.dumps({
        "direct_competitors": comp_data.direct_competitors,
        "market_position": comp_data.market_position,
        "competitive_advantages": comp_data.competitive_advantages,
        "market_threats": comp_data.market_threats,
        "differentiation_factors": comp_data.differentiation_factors,
        "analysis": analysis_result
    })
    
    cursor.execute('''
        UPDATE due_diligence 
        SET competitive_analysis = ?, last_updated = ?
        WHERE listing_id = ?
    ''', (comp_analysis_json, datetime.now().isoformat(), listing_id))
    
    conn.commit()
    conn.close()
    
    return analysis_result

@router.get("/{listing_id}/risk-assessment")
async def generate_risk_assessment(listing_id: str):
    """Generate comprehensive risk assessment for a listing"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get listing and due diligence data
    cursor.execute('''
        SELECT al.*, dd.* FROM app_listings al
        LEFT JOIN due_diligence dd ON al.id = dd.listing_id
        WHERE al.id = ?
    ''', (listing_id,))
    
    data = cursor.fetchone()
    if not data:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    conn.close()
    
    # Generate risk assessment
    risk_assessment = generate_comprehensive_risk_assessment(data)
    
    return risk_assessment

# Helper functions

def calculate_verification_score(dd_data: DueDiligenceData) -> float:
    """Calculate overall verification score based on due diligence data"""
    score = 0.0
    
    if dd_data.revenue_verified:
        score += 25
    
    if dd_data.code_quality_score > 0:
        score += (dd_data.code_quality_score / 100) * 25
    
    if dd_data.security_score > 0:
        score += (dd_data.security_score / 100) * 25
    
    if dd_data.user_growth_data:
        score += 15
    
    if dd_data.competitive_analysis:
        score += 10
    
    return min(score, 100.0)

def analyze_revenue_data(revenue_data: RevenueVerification) -> Dict[str, Any]:
    """Analyze revenue data for verification"""
    total_revenue = sum(revenue_data.monthly_revenue)
    avg_monthly = total_revenue / len(revenue_data.monthly_revenue) if revenue_data.monthly_revenue else 0
    
    # Calculate growth trend
    if len(revenue_data.monthly_revenue) > 1:
        recent_avg = sum(revenue_data.monthly_revenue[-3:]) / 3
        earlier_avg = sum(revenue_data.monthly_revenue[:3]) / 3
        growth_trend = ((recent_avg - earlier_avg) / earlier_avg) * 100 if earlier_avg > 0 else 0
    else:
        growth_trend = 0
    
    # Verification confidence based on data sources
    confidence = 60  # Base confidence
    if revenue_data.payment_processor_data:
        confidence += 20
    if revenue_data.bank_statements:
        confidence += 20
    
    verified = confidence >= 80 and total_revenue > 0
    
    return {
        "verified": verified,
        "confidence": min(confidence, 100),
        "analysis": {
            "total_revenue": total_revenue,
            "average_monthly": avg_monthly,
            "growth_trend": growth_trend,
            "revenue_sources_count": len(revenue_data.revenue_sources)
        },
        "recommendations": generate_revenue_recommendations(revenue_data, growth_trend)
    }

def analyze_growth_patterns(growth_data: UserGrowthMetrics) -> Dict[str, Any]:
    """Analyze user growth patterns and metrics"""
    # Calculate growth rates
    dau_growth = calculate_growth_rate(growth_data.daily_active_users)
    mau_growth = calculate_growth_rate(growth_data.monthly_active_users)
    
    # Analyze retention
    avg_retention = sum(growth_data.retention_rates) / len(growth_data.retention_rates) if growth_data.retention_rates else 0
    
    # Growth health score
    health_score = calculate_growth_health_score(growth_data)
    
    return {
        "dau_growth_rate": dau_growth,
        "mau_growth_rate": mau_growth,
        "average_retention": avg_retention,
        "churn_rate": growth_data.churn_rate,
        "growth_health_score": health_score,
        "growth_stage": determine_growth_stage(growth_data),
        "recommendations": generate_growth_recommendations(growth_data)
    }

def calculate_code_quality_score(code_data: CodeQualityAnalysis) -> float:
    """Calculate code quality score based on various metrics"""
    score = 0.0
    
    # Test coverage (30% weight)
    score += (code_data.test_coverage / 100) * 30
    
    # Code complexity (20% weight) - lower is better
    complexity_score = max(0, 100 - (code_data.code_complexity * 10))
    score += (complexity_score / 100) * 20
    
    # Security vulnerabilities (25% weight) - fewer is better
    vuln_score = max(0, 100 - (code_data.security_vulnerabilities * 5))
    score += (vuln_score / 100) * 25
    
    # Performance metrics (15% weight)
    perf_score = calculate_performance_score(code_data.performance_metrics)
    score += (perf_score / 100) * 15
    
    # Dependency health (10% weight)
    dep_score = calculate_dependency_score(code_data.dependency_analysis)
    score += (dep_score / 100) * 10
    
    return min(score, 100.0)

def calculate_security_score(security_data: SecurityAuditResults) -> float:
    """Calculate security score based on audit results"""
    base_score = 100.0
    
    # Deduct points for vulnerabilities
    base_score -= security_data.vulnerability_count * 2
    
    # Critical issues have higher impact
    base_score -= len(security_data.critical_issues) * 15
    
    # Compliance bonus
    compliance_count = sum(1 for status in security_data.compliance_status.values() if status)
    total_compliance = len(security_data.compliance_status)
    if total_compliance > 0:
        compliance_ratio = compliance_count / total_compliance
        base_score += compliance_ratio * 10
    
    return max(0, min(base_score, 100))

def calculate_growth_rate(values: List[int]) -> float:
    """Calculate growth rate from a list of values"""
    if len(values) < 2:
        return 0.0
    
    first_half = sum(values[:len(values)//2])
    second_half = sum(values[len(values)//2:])
    
    if first_half == 0:
        return 0.0
    
    return ((second_half - first_half) / first_half) * 100

def calculate_growth_health_score(growth_data: UserGrowthMetrics) -> float:
    """Calculate overall growth health score"""
    score = 0.0
    
    # DAU growth
    dau_growth = calculate_growth_rate(growth_data.daily_active_users)
    if dau_growth > 0:
        score += 30
    
    # Retention rate
    avg_retention = sum(growth_data.retention_rates) / len(growth_data.retention_rates) if growth_data.retention_rates else 0
    score += (avg_retention / 100) * 40
    
    # Low churn rate
    churn_score = max(0, 100 - (growth_data.churn_rate * 100))
    score += (churn_score / 100) * 30
    
    return min(score, 100.0)

def determine_growth_stage(growth_data: UserGrowthMetrics) -> str:
    """Determine the growth stage of the app"""
    latest_mau = growth_data.monthly_active_users[-1] if growth_data.monthly_active_users else 0
    growth_rate = calculate_growth_rate(growth_data.monthly_active_users)
    
    if latest_mau < 1000:
        return "early_stage"
    elif latest_mau < 10000:
        return "growth_stage" if growth_rate > 10 else "steady_stage"
    elif latest_mau < 100000:
        return "scale_stage" if growth_rate > 5 else "mature_stage"
    else:
        return "enterprise_stage"

def calculate_performance_score(performance_metrics: Dict[str, float]) -> float:
    """Calculate performance score from metrics"""
    if not performance_metrics:
        return 50.0  # Default score
    
    # Normalize common performance metrics
    score = 50.0
    
    if 'response_time' in performance_metrics:
        # Lower response time is better
        response_score = max(0, 100 - (performance_metrics['response_time'] * 10))
        score += (response_score / 100) * 25
    
    if 'throughput' in performance_metrics:
        # Higher throughput is better
        throughput_score = min(100, performance_metrics['throughput'])
        score += (throughput_score / 100) * 25
    
    return min(score, 100.0)

def calculate_dependency_score(dependency_analysis: Dict[str, Any]) -> float:
    """Calculate dependency health score"""
    if not dependency_analysis:
        return 50.0  # Default score
    
    score = 100.0
    
    # Deduct for outdated dependencies
    if 'outdated_count' in dependency_analysis:
        score -= dependency_analysis['outdated_count'] * 5
    
    # Deduct for vulnerabilities
    if 'vulnerable_count' in dependency_analysis:
        score -= dependency_analysis['vulnerable_count'] * 10
    
    return max(0, min(score, 100))

def get_quality_grade(score: float) -> str:
    """Convert quality score to letter grade"""
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"

def get_risk_level(security_score: float) -> str:
    """Convert security score to risk level"""
    if security_score >= 80:
        return "Low"
    elif security_score >= 60:
        return "Medium"
    elif security_score >= 40:
        return "High"
    else:
        return "Critical"

def generate_revenue_recommendations(revenue_data: RevenueVerification, growth_trend: float) -> List[str]:
    """Generate revenue-related recommendations"""
    recommendations = []
    
    if growth_trend < 0:
        recommendations.append("Revenue trend is declining. Consider diversifying revenue streams.")
    elif growth_trend < 10:
        recommendations.append("Revenue growth is modest. Explore upselling and new customer acquisition.")
    
    if len(revenue_data.revenue_sources) == 1:
        recommendations.append("Single revenue source detected. Consider diversifying revenue streams for stability.")
    
    if not revenue_data.payment_processor_data:
        recommendations.append("Provide payment processor data to increase verification confidence.")
    
    return recommendations

def generate_growth_recommendations(growth_data: UserGrowthMetrics) -> List[str]:
    """Generate user growth recommendations"""
    recommendations = []
    
    avg_retention = sum(growth_data.retention_rates) / len(growth_data.retention_rates) if growth_data.retention_rates else 0
    
    if avg_retention < 0.3:
        recommendations.append("User retention is low. Focus on improving user onboarding and engagement.")
    
    if growth_data.churn_rate > 0.1:
        recommendations.append("High churn rate detected. Analyze user feedback and improve product-market fit.")
    
    dau_growth = calculate_growth_rate(growth_data.daily_active_users)
    if dau_growth < 5:
        recommendations.append("DAU growth is slow. Consider implementing referral programs or viral features.")
    
    return recommendations

def generate_code_analysis_report(code_data: CodeQualityAnalysis) -> Dict[str, Any]:
    """Generate comprehensive code analysis report"""
    return {
        "code_size": {
            "lines_of_code": code_data.lines_of_code,
            "size_category": "Small" if code_data.lines_of_code < 10000 else "Medium" if code_data.lines_of_code < 100000 else "Large"
        },
        "testing": {
            "coverage": code_data.test_coverage,
            "coverage_grade": "Good" if code_data.test_coverage > 80 else "Fair" if code_data.test_coverage > 60 else "Poor"
        },
        "complexity": {
            "score": code_data.code_complexity,
            "maintainability": "High" if code_data.code_complexity < 2 else "Medium" if code_data.code_complexity < 4 else "Low"
        },
        "security": {
            "vulnerability_count": code_data.security_vulnerabilities,
            "security_status": "Secure" if code_data.security_vulnerabilities == 0 else "Needs Attention"
        }
    }

def get_code_improvement_recommendations(code_data: CodeQualityAnalysis) -> List[str]:
    """Generate code improvement recommendations"""
    recommendations = []
    
    if code_data.test_coverage < 80:
        recommendations.append("Increase test coverage to at least 80% for better reliability.")
    
    if code_data.code_complexity > 3:
        recommendations.append("Reduce code complexity by refactoring complex functions.")
    
    if code_data.security_vulnerabilities > 0:
        recommendations.append("Address security vulnerabilities before launch.")
    
    return recommendations

def analyze_competitive_position(comp_data: CompetitiveAnalysis) -> Dict[str, Any]:
    """Analyze competitive position"""
    return {
        "market_position": comp_data.market_position,
        "competitive_strength": len(comp_data.competitive_advantages),
        "threat_level": len(comp_data.market_threats),
        "differentiation_score": len(comp_data.differentiation_factors) * 10,
        "market_opportunity": "High" if len(comp_data.direct_competitors) < 5 else "Medium" if len(comp_data.direct_competitors) < 10 else "Low",
        "strategic_recommendations": generate_competitive_recommendations(comp_data)
    }

def generate_competitive_recommendations(comp_data: CompetitiveAnalysis) -> List[str]:
    """Generate competitive strategy recommendations"""
    recommendations = []
    
    if len(comp_data.direct_competitors) > 10:
        recommendations.append("Highly competitive market. Focus on unique value proposition.")
    
    if len(comp_data.competitive_advantages) < 3:
        recommendations.append("Strengthen competitive advantages to stand out in the market.")
    
    if len(comp_data.differentiation_factors) < 2:
        recommendations.append("Develop more differentiation factors to create unique market position.")
    
    return recommendations

def generate_comprehensive_risk_assessment(data) -> Dict[str, Any]:
    """Generate comprehensive risk assessment"""
    # This would analyze all available data and generate a risk profile
    return {
        "overall_risk": "Medium",
        "financial_risk": "Low",
        "technical_risk": "Medium",
        "market_risk": "Medium",
        "operational_risk": "Low",
        "risk_factors": [
            "Limited market validation",
            "Moderate technical complexity",
            "Competitive market landscape"
        ],
        "mitigation_strategies": [
            "Strengthen user acquisition channels",
            "Improve technical documentation",
            "Develop unique competitive advantages"
        ],
        "investment_readiness": "Ready with conditions"
    }