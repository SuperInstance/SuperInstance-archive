"""
ActiveLog Manufacturing Suite - Supplier Reputation Tracker

Performance-based supplier scoring system with delivery tracking,
quality assessment, communication monitoring, and risk evaluation.
"""

import asyncio
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
from pathlib import Path
import aiohttp
import hashlib
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
warnings.filterwarnings('ignore')


class PerformanceCategory(Enum):
    DELIVERY = "delivery"
    QUALITY = "quality"
    COMMUNICATION = "communication"
    PRICING = "pricing"
    COMPLIANCE = "compliance"
    INNOVATION = "innovation"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SupplierTier(Enum):
    STRATEGIC = "strategic"
    PREFERRED = "preferred"
    APPROVED = "approved"
    CONDITIONAL = "conditional"
    BLACKLISTED = "blacklisted"


class AlertType(Enum):
    PERFORMANCE_DECLINE = "performance_decline"
    DELIVERY_DELAY = "delivery_delay"
    QUALITY_ISSUE = "quality_issue"
    PRICE_INCREASE = "price_increase"
    COMPLIANCE_VIOLATION = "compliance_violation"
    COMMUNICATION_BREAKDOWN = "communication_breakdown"


@dataclass
class SupplierProfile:
    supplier_id: str
    name: str
    legal_name: str
    registration_number: str
    address: Dict[str, str]
    contact_info: Dict[str, str]
    website: str
    industry_sector: str
    size_category: str  # small, medium, large, enterprise
    certifications: List[str]
    capabilities: List[str]
    geographic_coverage: List[str]
    established_date: datetime
    relationship_start: datetime
    tier: SupplierTier
    is_active: bool


@dataclass
class PerformanceMetric:
    metric_id: str
    supplier_id: str
    category: PerformanceCategory
    metric_name: str
    value: float
    target_value: float
    weight: float
    measurement_date: datetime
    period_start: datetime
    period_end: datetime
    data_source: str
    notes: Optional[str] = None


@dataclass
class DeliveryRecord:
    delivery_id: str
    supplier_id: str
    order_id: str
    promised_date: datetime
    actual_date: Optional[datetime]
    quantity_ordered: int
    quantity_delivered: int
    delivery_status: str  # on_time, early, late, partial, cancelled
    delay_days: int
    delivery_score: float


@dataclass
class QualityRecord:
    quality_id: str
    supplier_id: str
    order_id: str
    inspection_date: datetime
    defect_rate: float
    rejection_rate: float
    rework_rate: float
    customer_complaints: int
    quality_score: float
    inspector_notes: str


@dataclass
class SupplierAlert:
    alert_id: str
    supplier_id: str
    alert_type: AlertType
    severity: RiskLevel
    title: str
    description: str
    created_at: datetime
    acknowledged: bool
    resolved: bool
    resolution_notes: Optional[str] = None


@dataclass
class SupplierScorecard:
    supplier_id: str
    overall_score: float
    category_scores: Dict[PerformanceCategory, float]
    tier: SupplierTier
    risk_level: RiskLevel
    trend: str  # improving, stable, declining
    last_updated: datetime
    recommendations: List[str]


class PerformanceAnalyzer:
    """Analyzer for supplier performance metrics"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.weights = {
            PerformanceCategory.DELIVERY: 0.25,
            PerformanceCategory.QUALITY: 0.25,
            PerformanceCategory.COMMUNICATION: 0.15,
            PerformanceCategory.PRICING: 0.15,
            PerformanceCategory.COMPLIANCE: 0.15,
            PerformanceCategory.INNOVATION: 0.05
        }
    
    async def calculate_delivery_performance(self, supplier_id: str, 
                                           period_days: int = 90) -> float:
        """Calculate delivery performance score"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get delivery records for the period
        cursor.execute("""
            SELECT delivery_status, delay_days, quantity_ordered, quantity_delivered
            FROM delivery_records 
            WHERE supplier_id = ? 
            AND actual_date > date('now', '-{} days')
        """.format(period_days), (supplier_id,))
        
        records = cursor.fetchall()
        conn.close()
        
        if not records:
            return 0.0
        
        on_time_count = 0
        total_orders = len(records)
        quantity_accuracy = []
        
        for status, delay, ordered, delivered in records:
            # On-time delivery (within 1 day tolerance)
            if status == 'on_time' or delay <= 1:
                on_time_count += 1
            
            # Quantity accuracy
            if ordered > 0:
                accuracy = min(1.0, delivered / ordered)
                quantity_accuracy.append(accuracy)
        
        # Calculate metrics
        on_time_rate = on_time_count / total_orders
        avg_quantity_accuracy = np.mean(quantity_accuracy) if quantity_accuracy else 0.0
        
        # Weighted score
        delivery_score = (on_time_rate * 0.6) + (avg_quantity_accuracy * 0.4)
        
        return min(1.0, delivery_score)
    
    async def calculate_quality_performance(self, supplier_id: str, 
                                          period_days: int = 90) -> float:
        """Calculate quality performance score"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT defect_rate, rejection_rate, rework_rate, customer_complaints
            FROM quality_records 
            WHERE supplier_id = ? 
            AND inspection_date > date('now', '-{} days')
        """.format(period_days), (supplier_id,))
        
        records = cursor.fetchall()
        conn.close()
        
        if not records:
            return 0.0
        
        # Calculate average quality metrics
        avg_defect_rate = np.mean([r[0] for r in records])
        avg_rejection_rate = np.mean([r[1] for r in records])
        avg_rework_rate = np.mean([r[2] for r in records])
        total_complaints = sum([r[3] for r in records])
        
        # Convert to scores (lower rates = higher scores)
        defect_score = max(0, 1.0 - avg_defect_rate)
        rejection_score = max(0, 1.0 - avg_rejection_rate)
        rework_score = max(0, 1.0 - avg_rework_rate)
        
        # Complaint penalty
        complaint_penalty = min(0.5, total_complaints * 0.1)
        
        # Weighted quality score
        quality_score = (
            defect_score * 0.4 + 
            rejection_score * 0.3 + 
            rework_score * 0.2 + 
            (1.0 - complaint_penalty) * 0.1
        )
        
        return max(0.0, min(1.0, quality_score))
    
    async def calculate_communication_performance(self, supplier_id: str, 
                                                period_days: int = 90) -> float:
        """Calculate communication performance score"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get communication metrics
        cursor.execute("""
            SELECT response_time_hours, proactive_updates, issue_escalations
            FROM communication_records 
            WHERE supplier_id = ? 
            AND interaction_date > date('now', '-{} days')
        """.format(period_days), (supplier_id,))
        
        records = cursor.fetchall()
        conn.close()
        
        if not records:
            return 0.7  # Neutral score if no data
        
        # Calculate metrics
        response_times = [r[0] for r in records if r[0] is not None]
        proactive_updates = sum([r[1] for r in records if r[1] is not None])
        escalations = sum([r[2] for r in records if r[2] is not None])
        
        # Response time score (target: < 4 hours)
        if response_times:
            avg_response_time = np.mean(response_times)
            response_score = max(0, 1.0 - (avg_response_time / 24))  # 24 hours = 0 score
        else:
            response_score = 0.7
        
        # Proactive communication bonus
        proactive_score = min(1.0, proactive_updates / len(records))
        
        # Escalation penalty
        escalation_penalty = min(0.5, escalations * 0.2)
        
        communication_score = (
            response_score * 0.5 + 
            proactive_score * 0.3 + 
            (1.0 - escalation_penalty) * 0.2
        )
        
        return max(0.0, min(1.0, communication_score))
    
    async def calculate_pricing_performance(self, supplier_id: str, 
                                          period_days: int = 90) -> float:
        """Calculate pricing competitiveness score"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get pricing data
        cursor.execute("""
            SELECT pr.unit_price, pr.market_price, pr.negotiated_discount
            FROM pricing_records pr
            WHERE pr.supplier_id = ? 
            AND pr.quote_date > date('now', '-{} days')
        """.format(period_days), (supplier_id,))
        
        records = cursor.fetchall()
        conn.close()
        
        if not records:
            return 0.5  # Neutral score if no data
        
        pricing_scores = []
        
        for unit_price, market_price, discount in records:
            if market_price and market_price > 0:
                # Price competitiveness vs market
                price_ratio = unit_price / market_price
                competitive_score = max(0, 2.0 - price_ratio)  # Best score when price <= 50% of market
                
                # Discount factor
                discount_bonus = min(0.2, discount * 0.1) if discount else 0
                
                score = min(1.0, competitive_score + discount_bonus)
                pricing_scores.append(score)
        
        return np.mean(pricing_scores) if pricing_scores else 0.5
    
    async def calculate_compliance_performance(self, supplier_id: str, 
                                             period_days: int = 365) -> float:
        """Calculate compliance performance score"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get compliance data
        cursor.execute("""
            SELECT certification_status, audit_score, violations_count
            FROM compliance_records 
            WHERE supplier_id = ? 
            AND assessment_date > date('now', '-{} days')
        """.format(period_days), (supplier_id,))
        
        records = cursor.fetchall()
        conn.close()
        
        if not records:
            return 0.0  # No compliance data = risk
        
        # Latest compliance record
        latest_record = records[-1]
        cert_status, audit_score, violations = latest_record
        
        # Certification score
        cert_score = 1.0 if cert_status == 'valid' else 0.0
        
        # Audit score (normalized)
        audit_score_norm = (audit_score or 0) / 100.0
        
        # Violations penalty
        violation_penalty = min(0.8, violations * 0.2) if violations else 0
        
        compliance_score = (
            cert_score * 0.4 + 
            audit_score_norm * 0.4 + 
            (1.0 - violation_penalty) * 0.2
        )
        
        return max(0.0, min(1.0, compliance_score))
    
    async def calculate_overall_score(self, supplier_id: str) -> Tuple[float, Dict[PerformanceCategory, float]]:
        """Calculate overall supplier score and category breakdown"""
        category_scores = {}
        
        # Calculate scores for each category
        category_scores[PerformanceCategory.DELIVERY] = await self.calculate_delivery_performance(supplier_id)
        category_scores[PerformanceCategory.QUALITY] = await self.calculate_quality_performance(supplier_id)
        category_scores[PerformanceCategory.COMMUNICATION] = await self.calculate_communication_performance(supplier_id)
        category_scores[PerformanceCategory.PRICING] = await self.calculate_pricing_performance(supplier_id)
        category_scores[PerformanceCategory.COMPLIANCE] = await self.calculate_compliance_performance(supplier_id)
        category_scores[PerformanceCategory.INNOVATION] = await self.calculate_innovation_performance(supplier_id)
        
        # Calculate weighted overall score
        overall_score = sum(
            score * self.weights[category] 
            for category, score in category_scores.items()
        )
        
        return overall_score, category_scores
    
    async def calculate_innovation_performance(self, supplier_id: str) -> float:
        """Calculate innovation performance score"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get innovation metrics
        cursor.execute("""
            SELECT COUNT(*) as suggestions, 
                   AVG(cost_savings) as avg_savings,
                   COUNT(CASE WHEN implemented = 1 THEN 1 END) as implemented
            FROM innovation_records 
            WHERE supplier_id = ? 
            AND submission_date > date('now', '-365 days')
        """, (supplier_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        suggestions, avg_savings, implemented = result or (0, 0, 0)
        
        if suggestions == 0:
            return 0.3  # Baseline score for no innovation activity
        
        # Innovation metrics
        suggestion_rate = min(1.0, suggestions / 10)  # Target: 10 suggestions per year
        implementation_rate = implemented / suggestions if suggestions > 0 else 0
        savings_score = min(1.0, (avg_savings or 0) / 10000)  # $10k target savings
        
        innovation_score = (
            suggestion_rate * 0.4 + 
            implementation_rate * 0.4 + 
            savings_score * 0.2
        )
        
        return min(1.0, innovation_score)


class RiskAssessment:
    """Risk assessment engine for suppliers"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.risk_factors = {
            'financial_stability': 0.25,
            'geographic_risk': 0.15,
            'dependency_risk': 0.15,
            'performance_volatility': 0.15,
            'compliance_risk': 0.15,
            'operational_risk': 0.15
        }
    
    async def assess_supplier_risk(self, supplier_id: str) -> Tuple[RiskLevel, Dict[str, float], List[str]]:
        """Comprehensive supplier risk assessment"""
        risk_scores = {}
        risk_factors = []
        
        # Financial stability risk
        risk_scores['financial_stability'] = await self._assess_financial_risk(supplier_id)
        
        # Geographic risk
        risk_scores['geographic_risk'] = await self._assess_geographic_risk(supplier_id)
        
        # Dependency risk
        risk_scores['dependency_risk'] = await self._assess_dependency_risk(supplier_id)
        
        # Performance volatility
        risk_scores['performance_volatility'] = await self._assess_performance_volatility(supplier_id)
        
        # Compliance risk
        risk_scores['compliance_risk'] = await self._assess_compliance_risk(supplier_id)
        
        # Operational risk
        risk_scores['operational_risk'] = await self._assess_operational_risk(supplier_id)
        
        # Calculate overall risk score
        overall_risk = sum(
            score * self.risk_factors[factor] 
            for factor, score in risk_scores.items()
        )
        
        # Determine risk level
        if overall_risk >= 0.8:
            risk_level = RiskLevel.CRITICAL
        elif overall_risk >= 0.6:
            risk_level = RiskLevel.HIGH
        elif overall_risk >= 0.4:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW
        
        # Generate risk factors list
        for factor, score in risk_scores.items():
            if score >= 0.6:
                risk_factors.append(f"High {factor.replace('_', ' ')} risk (score: {score:.2f})")
        
        return risk_level, risk_scores, risk_factors
    
    async def _assess_financial_risk(self, supplier_id: str) -> float:
        """Assess financial stability risk"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get financial data
        cursor.execute("""
            SELECT credit_rating, debt_to_equity, liquidity_ratio, payment_delays
            FROM financial_records 
            WHERE supplier_id = ? 
            ORDER BY assessment_date DESC LIMIT 1
        """, (supplier_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return 0.7  # High risk if no financial data
        
        credit_rating, debt_to_equity, liquidity_ratio, payment_delays = result
        
        # Credit rating risk (AAA=0.1, D=1.0)
        credit_risk_map = {
            'AAA': 0.1, 'AA': 0.2, 'A': 0.3, 'BBB': 0.4,
            'BB': 0.6, 'B': 0.7, 'CCC': 0.8, 'CC': 0.9, 'D': 1.0
        }
        credit_risk = credit_risk_map.get(credit_rating, 0.7)
        
        # Debt-to-equity risk
        debt_risk = min(1.0, (debt_to_equity or 0) / 3.0)  # 3.0 = high risk threshold
        
        # Liquidity risk
        liquidity_risk = max(0, 1.0 - (liquidity_ratio or 0))
        
        # Payment delay risk
        payment_risk = min(1.0, (payment_delays or 0) / 10)  # 10 delays = max risk
        
        financial_risk = (credit_risk * 0.4 + debt_risk * 0.3 + 
                         liquidity_risk * 0.2 + payment_risk * 0.1)
        
        return min(1.0, financial_risk)
    
    async def _assess_geographic_risk(self, supplier_id: str) -> float:
        """Assess geographic/political risk"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT country, region FROM supplier_profiles 
            WHERE supplier_id = ?
        """, (supplier_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return 0.5
        
        country, region = result
        
        # Simplified geographic risk mapping
        high_risk_countries = ['country_a', 'country_b', 'country_c']
        medium_risk_countries = ['country_d', 'country_e']
        
        if country.lower() in high_risk_countries:
            return 0.8
        elif country.lower() in medium_risk_countries:
            return 0.5
        else:
            return 0.2
    
    async def _assess_dependency_risk(self, supplier_id: str) -> float:
        """Assess dependency risk (single source, high volume)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Calculate supplier's share of total spend
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN supplier_id = ? THEN order_value ELSE 0 END) as supplier_spend,
                SUM(order_value) as total_spend
            FROM purchase_orders 
            WHERE order_date > date('now', '-365 days')
        """, (supplier_id,))
        
        result = cursor.fetchone()
        
        if not result or result[1] == 0:
            return 0.3
        
        supplier_spend, total_spend = result
        spend_share = supplier_spend / total_spend
        
        # High dependency if >30% of spend
        if spend_share > 0.3:
            dependency_risk = 0.8
        elif spend_share > 0.15:
            dependency_risk = 0.5
        else:
            dependency_risk = 0.2
        
        # Check for single-source items
        cursor.execute("""
            SELECT COUNT(DISTINCT component_id) as single_source_items
            FROM sourcing_records 
            WHERE supplier_id = ? AND alternative_suppliers = 0
        """, (supplier_id,))
        
        single_source_count = cursor.fetchone()[0] or 0
        
        if single_source_count > 10:
            dependency_risk = min(1.0, dependency_risk + 0.3)
        elif single_source_count > 5:
            dependency_risk = min(1.0, dependency_risk + 0.1)
        
        conn.close()
        return dependency_risk
    
    async def _assess_performance_volatility(self, supplier_id: str) -> float:
        """Assess performance consistency/volatility"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get historical performance scores
        cursor.execute("""
            SELECT overall_score, measurement_date
            FROM supplier_scorecards 
            WHERE supplier_id = ? 
            ORDER BY measurement_date DESC LIMIT 12
        """, (supplier_id,))
        
        scores = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if len(scores) < 3:
            return 0.5  # Insufficient data
        
        # Calculate coefficient of variation
        cv = np.std(scores) / np.mean(scores) if np.mean(scores) > 0 else 1.0
        
        # High volatility = high risk
        volatility_risk = min(1.0, cv * 2.0)  # CV of 0.5 = max risk
        
        return volatility_risk
    
    async def _assess_compliance_risk(self, supplier_id: str) -> float:
        """Assess compliance and regulatory risk"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT violations_count, audit_score, certification_status
            FROM compliance_records 
            WHERE supplier_id = ? 
            ORDER BY assessment_date DESC LIMIT 1
        """, (supplier_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return 0.8  # High risk if no compliance data
        
        violations, audit_score, cert_status = result
        
        # Violations risk
        violation_risk = min(1.0, (violations or 0) * 0.3)
        
        # Audit score risk
        audit_risk = 1.0 - ((audit_score or 0) / 100.0)
        
        # Certification risk
        cert_risk = 0.0 if cert_status == 'valid' else 0.8
        
        compliance_risk = (violation_risk * 0.4 + audit_risk * 0.4 + cert_risk * 0.2)
        
        return min(1.0, compliance_risk)
    
    async def _assess_operational_risk(self, supplier_id: str) -> float:
        """Assess operational risk factors"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get operational metrics
        cursor.execute("""
            SELECT capacity_utilization, lead_time_variance, quality_incidents
            FROM operational_records 
            WHERE supplier_id = ? 
            ORDER BY assessment_date DESC LIMIT 1
        """, (supplier_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return 0.5
        
        capacity_util, lead_variance, quality_incidents = result
        
        # High capacity utilization risk
        capacity_risk = max(0, (capacity_util or 0) - 0.8) * 5  # Risk above 80%
        
        # Lead time variance risk
        variance_risk = min(1.0, (lead_variance or 0) / 10)  # 10 days variance = max risk
        
        # Quality incidents risk
        incident_risk = min(1.0, (quality_incidents or 0) * 0.2)
        
        operational_risk = (capacity_risk * 0.4 + variance_risk * 0.3 + incident_risk * 0.3)
        
        return min(1.0, operational_risk)


class AlertSystem:
    """Automated alert system for supplier performance"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.alert_thresholds = {
            'performance_decline': 0.2,  # 20% decline
            'delivery_delay': 3,  # 3+ days late
            'quality_degradation': 0.1,  # 10% increase in defects
            'price_increase': 0.15,  # 15% price increase
        }
    
    async def monitor_suppliers(self) -> List[SupplierAlert]:
        """Monitor all suppliers and generate alerts"""
        alerts = []
        
        # Get all active suppliers
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT supplier_id FROM supplier_profiles WHERE is_active = 1")
        supplier_ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        for supplier_id in supplier_ids:
            supplier_alerts = await self._check_supplier_alerts(supplier_id)
            alerts.extend(supplier_alerts)
        
        # Store alerts in database
        for alert in alerts:
            await self._store_alert(alert)
        
        return alerts
    
    async def _check_supplier_alerts(self, supplier_id: str) -> List[SupplierAlert]:
        """Check for alerts for a specific supplier"""
        alerts = []
        
        # Performance decline check
        performance_alert = await self._check_performance_decline(supplier_id)
        if performance_alert:
            alerts.append(performance_alert)
        
        # Delivery delay check
        delivery_alert = await self._check_delivery_delays(supplier_id)
        if delivery_alert:
            alerts.append(delivery_alert)
        
        # Quality issue check
        quality_alert = await self._check_quality_issues(supplier_id)
        if quality_alert:
            alerts.append(quality_alert)
        
        # Price increase check
        price_alert = await self._check_price_increases(supplier_id)
        if price_alert:
            alerts.append(price_alert)
        
        return alerts
    
    async def _check_performance_decline(self, supplier_id: str) -> Optional[SupplierAlert]:
        """Check for performance decline"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get recent performance scores
        cursor.execute("""
            SELECT overall_score, measurement_date
            FROM supplier_scorecards 
            WHERE supplier_id = ? 
            ORDER BY measurement_date DESC LIMIT 2
        """, (supplier_id,))
        
        scores = cursor.fetchall()
        conn.close()
        
        if len(scores) < 2:
            return None
        
        current_score, latest_score = scores[0][0], scores[1][0]
        decline = (latest_score - current_score) / latest_score if latest_score > 0 else 0
        
        if decline >= self.alert_thresholds['performance_decline']:
            return SupplierAlert(
                alert_id=f"perf_{supplier_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                supplier_id=supplier_id,
                alert_type=AlertType.PERFORMANCE_DECLINE,
                severity=RiskLevel.HIGH if decline >= 0.3 else RiskLevel.MEDIUM,
                title="Performance Decline Detected",
                description=f"Supplier performance declined by {decline:.1%} from {latest_score:.2f} to {current_score:.2f}",
                created_at=datetime.now(),
                acknowledged=False,
                resolved=False
            )
        
        return None
    
    async def _check_delivery_delays(self, supplier_id: str) -> Optional[SupplierAlert]:
        """Check for delivery delays"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check recent deliveries
        cursor.execute("""
            SELECT AVG(delay_days), COUNT(*) as late_count
            FROM delivery_records 
            WHERE supplier_id = ? 
            AND actual_date > date('now', '-30 days')
            AND delay_days > ?
        """, (supplier_id, self.alert_thresholds['delivery_delay']))
        
        result = cursor.fetchone()
        conn.close()
        
        if result and result[1] > 0:
            avg_delay, late_count = result
            
            return SupplierAlert(
                alert_id=f"delay_{supplier_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                supplier_id=supplier_id,
                alert_type=AlertType.DELIVERY_DELAY,
                severity=RiskLevel.HIGH if avg_delay > 7 else RiskLevel.MEDIUM,
                title="Delivery Delays Detected",
                description=f"{late_count} late deliveries in past 30 days, average delay: {avg_delay:.1f} days",
                created_at=datetime.now(),
                acknowledged=False,
                resolved=False
            )
        
        return None
    
    async def _check_quality_issues(self, supplier_id: str) -> Optional[SupplierAlert]:
        """Check for quality issues"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Compare recent quality to baseline
        cursor.execute("""
            SELECT 
                AVG(CASE WHEN inspection_date > date('now', '-30 days') THEN defect_rate END) as recent_defects,
                AVG(CASE WHEN inspection_date BETWEEN date('now', '-90 days') AND date('now', '-30 days') THEN defect_rate END) as baseline_defects
            FROM quality_records 
            WHERE supplier_id = ?
        """, (supplier_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0] is not None and result[1] is not None:
            recent_defects, baseline_defects = result
            
            if baseline_defects > 0:
                increase = (recent_defects - baseline_defects) / baseline_defects
                
                if increase >= self.alert_thresholds['quality_degradation']:
                    return SupplierAlert(
                        alert_id=f"quality_{supplier_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        supplier_id=supplier_id,
                        alert_type=AlertType.QUALITY_ISSUE,
                        severity=RiskLevel.HIGH if increase >= 0.25 else RiskLevel.MEDIUM,
                        title="Quality Degradation Detected",
                        description=f"Defect rate increased by {increase:.1%} from {baseline_defects:.2%} to {recent_defects:.2%}",
                        created_at=datetime.now(),
                        acknowledged=False,
                        resolved=False
                    )
        
        return None
    
    async def _check_price_increases(self, supplier_id: str) -> Optional[SupplierAlert]:
        """Check for price increases"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check recent price changes
        cursor.execute("""
            SELECT 
                AVG(CASE WHEN quote_date > date('now', '-30 days') THEN unit_price END) as recent_price,
                AVG(CASE WHEN quote_date BETWEEN date('now', '-90 days') AND date('now', '-30 days') THEN unit_price END) as baseline_price
            FROM pricing_records 
            WHERE supplier_id = ?
        """, (supplier_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0] is not None and result[1] is not None:
            recent_price, baseline_price = result
            
            if baseline_price > 0:
                increase = (recent_price - baseline_price) / baseline_price
                
                if increase >= self.alert_thresholds['price_increase']:
                    return SupplierAlert(
                        alert_id=f"price_{supplier_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        supplier_id=supplier_id,
                        alert_type=AlertType.PRICE_INCREASE,
                        severity=RiskLevel.MEDIUM,
                        title="Price Increase Detected",
                        description=f"Average price increased by {increase:.1%} from ${baseline_price:.2f} to ${recent_price:.2f}",
                        created_at=datetime.now(),
                        acknowledged=False,
                        resolved=False
                    )
        
        return None
    
    async def _store_alert(self, alert: SupplierAlert):
        """Store alert in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO supplier_alerts 
            (alert_id, supplier_id, alert_type, severity, title, description, 
             created_at, acknowledged, resolved, resolution_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            alert.alert_id, alert.supplier_id, alert.alert_type.value,
            alert.severity.value, alert.title, alert.description,
            alert.created_at, alert.acknowledged, alert.resolved, alert.resolution_notes
        ))
        
        conn.commit()
        conn.close()


class SupplierReputationTracker:
    """Main system for tracking and managing supplier reputation"""
    
    def __init__(self, db_path: str = "supplier_reputation.db"):
        self.db_path = db_path
        self.performance_analyzer = PerformanceAnalyzer(db_path)
        self.risk_assessment = RiskAssessment(db_path)
        self.alert_system = AlertSystem(db_path)
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize supplier reputation database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Supplier profiles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS supplier_profiles (
                supplier_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                legal_name TEXT,
                registration_number TEXT,
                address TEXT,
                contact_info TEXT,
                website TEXT,
                industry_sector TEXT,
                size_category TEXT,
                certifications TEXT,
                capabilities TEXT,
                geographic_coverage TEXT,
                established_date TIMESTAMP,
                relationship_start TIMESTAMP,
                tier TEXT,
                is_active BOOLEAN,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        
        # Performance metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                metric_id TEXT PRIMARY KEY,
                supplier_id TEXT,
                category TEXT,
                metric_name TEXT,
                value REAL,
                target_value REAL,
                weight REAL,
                measurement_date TIMESTAMP,
                period_start TIMESTAMP,
                period_end TIMESTAMP,
                data_source TEXT,
                notes TEXT,
                FOREIGN KEY (supplier_id) REFERENCES supplier_profiles (supplier_id)
            )
        """)
        
        # Delivery records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS delivery_records (
                delivery_id TEXT PRIMARY KEY,
                supplier_id TEXT,
                order_id TEXT,
                promised_date TIMESTAMP,
                actual_date TIMESTAMP,
                quantity_ordered INTEGER,
                quantity_delivered INTEGER,
                delivery_status TEXT,
                delay_days INTEGER,
                delivery_score REAL,
                FOREIGN KEY (supplier_id) REFERENCES supplier_profiles (supplier_id)
            )
        """)
        
        # Quality records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quality_records (
                quality_id TEXT PRIMARY KEY,
                supplier_id TEXT,
                order_id TEXT,
                inspection_date TIMESTAMP,
                defect_rate REAL,
                rejection_rate REAL,
                rework_rate REAL,
                customer_complaints INTEGER,
                quality_score REAL,
                inspector_notes TEXT,
                FOREIGN KEY (supplier_id) REFERENCES supplier_profiles (supplier_id)
            )
        """)
        
        # Communication records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS communication_records (
                communication_id TEXT PRIMARY KEY,
                supplier_id TEXT,
                interaction_date TIMESTAMP,
                interaction_type TEXT,
                response_time_hours REAL,
                proactive_updates INTEGER,
                issue_escalations INTEGER,
                satisfaction_rating INTEGER,
                FOREIGN KEY (supplier_id) REFERENCES supplier_profiles (supplier_id)
            )
        """)
        
        # Pricing records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pricing_records (
                pricing_id TEXT PRIMARY KEY,
                supplier_id TEXT,
                component_id TEXT,
                quote_date TIMESTAMP,
                unit_price REAL,
                market_price REAL,
                negotiated_discount REAL,
                validity_period INTEGER,
                FOREIGN KEY (supplier_id) REFERENCES supplier_profiles (supplier_id)
            )
        """)
        
        # Compliance records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compliance_records (
                compliance_id TEXT PRIMARY KEY,
                supplier_id TEXT,
                assessment_date TIMESTAMP,
                certification_status TEXT,
                audit_score REAL,
                violations_count INTEGER,
                corrective_actions TEXT,
                FOREIGN KEY (supplier_id) REFERENCES supplier_profiles (supplier_id)
            )
        """)
        
        # Innovation records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS innovation_records (
                innovation_id TEXT PRIMARY KEY,
                supplier_id TEXT,
                submission_date TIMESTAMP,
                suggestion_title TEXT,
                description TEXT,
                cost_savings REAL,
                implemented BOOLEAN,
                implementation_date TIMESTAMP,
                FOREIGN KEY (supplier_id) REFERENCES supplier_profiles (supplier_id)
            )
        """)
        
        # Financial records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS financial_records (
                financial_id TEXT PRIMARY KEY,
                supplier_id TEXT,
                assessment_date TIMESTAMP,
                credit_rating TEXT,
                debt_to_equity REAL,
                liquidity_ratio REAL,
                payment_delays INTEGER,
                revenue_size TEXT,
                FOREIGN KEY (supplier_id) REFERENCES supplier_profiles (supplier_id)
            )
        """)
        
        # Supplier scorecards table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS supplier_scorecards (
                scorecard_id TEXT PRIMARY KEY,
                supplier_id TEXT,
                overall_score REAL,
                category_scores TEXT,
                tier TEXT,
                risk_level TEXT,
                trend TEXT,
                measurement_date TIMESTAMP,
                recommendations TEXT,
                FOREIGN KEY (supplier_id) REFERENCES supplier_profiles (supplier_id)
            )
        """)
        
        # Alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS supplier_alerts (
                alert_id TEXT PRIMARY KEY,
                supplier_id TEXT,
                alert_type TEXT,
                severity TEXT,
                title TEXT,
                description TEXT,
                created_at TIMESTAMP,
                acknowledged BOOLEAN,
                resolved BOOLEAN,
                resolution_notes TEXT,
                FOREIGN KEY (supplier_id) REFERENCES supplier_profiles (supplier_id)
            )
        """)
        
        # Additional tables for operational and other records
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS operational_records (
                operational_id TEXT PRIMARY KEY,
                supplier_id TEXT,
                assessment_date TIMESTAMP,
                capacity_utilization REAL,
                lead_time_variance REAL,
                quality_incidents INTEGER,
                FOREIGN KEY (supplier_id) REFERENCES supplier_profiles (supplier_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS purchase_orders (
                order_id TEXT PRIMARY KEY,
                supplier_id TEXT,
                order_date TIMESTAMP,
                order_value REAL,
                component_id TEXT,
                FOREIGN KEY (supplier_id) REFERENCES supplier_profiles (supplier_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sourcing_records (
                sourcing_id TEXT PRIMARY KEY,
                supplier_id TEXT,
                component_id TEXT,
                alternative_suppliers INTEGER,
                FOREIGN KEY (supplier_id) REFERENCES supplier_profiles (supplier_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def add_supplier(self, profile: SupplierProfile) -> str:
        """Add new supplier to tracking system"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO supplier_profiles 
            (supplier_id, name, legal_name, registration_number, address, contact_info,
             website, industry_sector, size_category, certifications, capabilities,
             geographic_coverage, established_date, relationship_start, tier, is_active,
             created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            profile.supplier_id, profile.name, profile.legal_name, profile.registration_number,
            json.dumps(profile.address), json.dumps(profile.contact_info), profile.website,
            profile.industry_sector, profile.size_category, json.dumps(profile.certifications),
            json.dumps(profile.capabilities), json.dumps(profile.geographic_coverage),
            profile.established_date, profile.relationship_start, profile.tier.value,
            profile.is_active, datetime.now(), datetime.now()
        ))
        
        conn.commit()
        conn.close()
        
        return profile.supplier_id
    
    async def update_supplier_scorecard(self, supplier_id: str) -> SupplierScorecard:
        """Update supplier scorecard with latest performance data"""
        # Calculate performance scores
        overall_score, category_scores = await self.performance_analyzer.calculate_overall_score(supplier_id)
        
        # Assess risk
        risk_level, risk_scores, risk_factors = await self.risk_assessment.assess_supplier_risk(supplier_id)
        
        # Determine tier based on score
        if overall_score >= 0.9:
            tier = SupplierTier.STRATEGIC
        elif overall_score >= 0.8:
            tier = SupplierTier.PREFERRED
        elif overall_score >= 0.6:
            tier = SupplierTier.APPROVED
        else:
            tier = SupplierTier.CONDITIONAL
        
        # Determine trend
        trend = await self._calculate_performance_trend(supplier_id)
        
        # Generate recommendations
        recommendations = await self._generate_recommendations(supplier_id, category_scores, risk_factors)
        
        # Create scorecard
        scorecard = SupplierScorecard(
            supplier_id=supplier_id,
            overall_score=overall_score,
            category_scores=category_scores,
            tier=tier,
            risk_level=risk_level,
            trend=trend,
            last_updated=datetime.now(),
            recommendations=recommendations
        )
        
        # Store scorecard
        await self._store_scorecard(scorecard)
        
        return scorecard
    
    async def _calculate_performance_trend(self, supplier_id: str) -> str:
        """Calculate performance trend over time"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT overall_score, measurement_date
            FROM supplier_scorecards 
            WHERE supplier_id = ? 
            ORDER BY measurement_date DESC LIMIT 3
        """, (supplier_id,))
        
        scores = cursor.fetchall()
        conn.close()
        
        if len(scores) < 2:
            return "stable"
        
        recent_scores = [score[0] for score in scores]
        
        # Calculate trend using linear regression
        if len(recent_scores) >= 3:
            x = np.arange(len(recent_scores))
            slope = np.polyfit(x, recent_scores, 1)[0]
            
            if slope > 0.05:
                return "improving"
            elif slope < -0.05:
                return "declining"
            else:
                return "stable"
        else:
            # Simple comparison for 2 points
            if recent_scores[0] > recent_scores[1] * 1.05:
                return "improving"
            elif recent_scores[0] < recent_scores[1] * 0.95:
                return "declining"
            else:
                return "stable"
    
    async def _generate_recommendations(self, supplier_id: str, 
                                      category_scores: Dict[PerformanceCategory, float],
                                      risk_factors: List[str]) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        
        # Performance-based recommendations
        for category, score in category_scores.items():
            if score < 0.6:
                if category == PerformanceCategory.DELIVERY:
                    recommendations.append("Implement delivery performance improvement plan")
                elif category == PerformanceCategory.QUALITY:
                    recommendations.append("Conduct quality system audit and improvement")
                elif category == PerformanceCategory.COMMUNICATION:
                    recommendations.append("Establish regular communication protocols")
                elif category == PerformanceCategory.PRICING:
                    recommendations.append("Negotiate better pricing terms or seek alternatives")
                elif category == PerformanceCategory.COMPLIANCE:
                    recommendations.append("Address compliance gaps immediately")
        
        # Risk-based recommendations
        if risk_factors:
            recommendations.append("Develop risk mitigation strategies")
            if any("financial" in factor.lower() for factor in risk_factors):
                recommendations.append("Consider requiring financial guarantees")
            if any("geographic" in factor.lower() for factor in risk_factors):
                recommendations.append("Identify alternative suppliers in stable regions")
        
        # General recommendations
        if not recommendations:
            recommendations.append("Maintain current performance levels")
            recommendations.append("Explore opportunities for strategic partnership")
        
        return recommendations
    
    async def _store_scorecard(self, scorecard: SupplierScorecard):
        """Store supplier scorecard in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        scorecard_id = f"sc_{scorecard.supplier_id}_{scorecard.last_updated.strftime('%Y%m%d_%H%M%S')}"
        
        cursor.execute("""
            INSERT INTO supplier_scorecards 
            (scorecard_id, supplier_id, overall_score, category_scores, tier, risk_level,
             trend, measurement_date, recommendations)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            scorecard_id, scorecard.supplier_id, scorecard.overall_score,
            json.dumps({k.value: v for k, v in scorecard.category_scores.items()}),
            scorecard.tier.value, scorecard.risk_level.value, scorecard.trend,
            scorecard.last_updated, json.dumps(scorecard.recommendations)
        ))
        
        conn.commit()
        conn.close()
    
    async def get_supplier_dashboard(self, supplier_id: str) -> Dict[str, Any]:
        """Get comprehensive supplier dashboard"""
        # Get latest scorecard
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM supplier_scorecards 
            WHERE supplier_id = ? 
            ORDER BY measurement_date DESC LIMIT 1
        """, (supplier_id,))
        
        scorecard_row = cursor.fetchone()
        
        # Get recent alerts
        cursor.execute("""
            SELECT * FROM supplier_alerts 
            WHERE supplier_id = ? AND resolved = 0
            ORDER BY created_at DESC LIMIT 5
        """, (supplier_id,))
        
        alert_rows = cursor.fetchall()
        
        # Get profile
        cursor.execute("SELECT * FROM supplier_profiles WHERE supplier_id = ?", (supplier_id,))
        profile_row = cursor.fetchone()
        
        conn.close()
        
        dashboard = {
            'supplier_id': supplier_id,
            'profile': dict(zip([desc[0] for desc in cursor.description], profile_row)) if profile_row else None,
            'scorecard': dict(zip([desc[0] for desc in cursor.description], scorecard_row)) if scorecard_row else None,
            'active_alerts': [dict(zip([desc[0] for desc in cursor.description], row)) for row in alert_rows],
            'performance_trends': await self._get_performance_trends(supplier_id),
            'recent_deliveries': await self._get_recent_deliveries(supplier_id),
            'quality_metrics': await self._get_quality_metrics(supplier_id)
        }
        
        return dashboard
    
    async def _get_performance_trends(self, supplier_id: str) -> Dict[str, Any]:
        """Get performance trend data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT overall_score, measurement_date
            FROM supplier_scorecards 
            WHERE supplier_id = ? 
            ORDER BY measurement_date DESC LIMIT 12
        """, (supplier_id,))
        
        trend_data = cursor.fetchall()
        conn.close()
        
        return {
            'scores': [row[0] for row in trend_data],
            'dates': [row[1] for row in trend_data]
        }
    
    async def _get_recent_deliveries(self, supplier_id: str) -> List[Dict[str, Any]]:
        """Get recent delivery performance"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT delivery_status, delay_days, quantity_delivered, quantity_ordered, actual_date
            FROM delivery_records 
            WHERE supplier_id = ? 
            ORDER BY actual_date DESC LIMIT 10
        """, (supplier_id,))
        
        deliveries = cursor.fetchall()
        conn.close()
        
        return [
            {
                'status': row[0],
                'delay_days': row[1],
                'quantity_delivered': row[2],
                'quantity_ordered': row[3],
                'delivery_date': row[4]
            }
            for row in deliveries
        ]
    
    async def _get_quality_metrics(self, supplier_id: str) -> Dict[str, float]:
        """Get quality performance metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                AVG(defect_rate) as avg_defect_rate,
                AVG(rejection_rate) as avg_rejection_rate,
                AVG(quality_score) as avg_quality_score,
                COUNT(*) as total_inspections
            FROM quality_records 
            WHERE supplier_id = ? 
            AND inspection_date > date('now', '-90 days')
        """, (supplier_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return {
            'average_defect_rate': result[0] if result[0] else 0.0,
            'average_rejection_rate': result[1] if result[1] else 0.0,
            'average_quality_score': result[2] if result[2] else 0.0,
            'total_inspections': result[3] if result[3] else 0
        }
    
    async def run_monitoring_cycle(self) -> Dict[str, Any]:
        """Run complete supplier monitoring cycle"""
        # Monitor for alerts
        alerts = await self.alert_system.monitor_suppliers()
        
        # Update scorecards for all active suppliers
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT supplier_id FROM supplier_profiles WHERE is_active = 1")
        supplier_ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        updated_scorecards = []
        for supplier_id in supplier_ids:
            try:
                scorecard = await self.update_supplier_scorecard(supplier_id)
                updated_scorecards.append(scorecard)
            except Exception as e:
                print(f"Error updating scorecard for {supplier_id}: {e}")
        
        return {
            'monitoring_date': datetime.now(),
            'suppliers_monitored': len(supplier_ids),
            'alerts_generated': len(alerts),
            'scorecards_updated': len(updated_scorecards),
            'critical_alerts': len([a for a in alerts if a.severity == RiskLevel.CRITICAL]),
            'high_risk_suppliers': len([s for s in updated_scorecards if s.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]])
        }


async def main():
    """Example usage of Supplier Reputation Tracker"""
    tracker = SupplierReputationTracker()
    
    # Example supplier profile
    supplier = SupplierProfile(
        supplier_id="SUPP001",
        name="TechComponents Ltd",
        legal_name="TechComponents Limited",
        registration_number="TC123456",
        address={"street": "123 Tech Street", "city": "TechCity", "country": "TechLand"},
        contact_info={"email": "contact@techcomponents.com", "phone": "+1-555-0123"},
        website="https://techcomponents.com",
        industry_sector="Electronics",
        size_category="medium",
        certifications=["ISO9001", "ISO14001"],
        capabilities=["PCB_Assembly", "Component_Testing"],
        geographic_coverage=["North_America", "Europe"],
        established_date=datetime(2010, 1, 1),
        relationship_start=datetime(2020, 6, 1),
        tier=SupplierTier.PREFERRED,
        is_active=True
    )
    
    # Add supplier
    await tracker.add_supplier(supplier)
    print(f"Added supplier: {supplier.name}")
    
    # Update scorecard
    scorecard = await tracker.update_supplier_scorecard(supplier.supplier_id)
    print(f"\nSupplier Scorecard:")
    print(f"Overall Score: {scorecard.overall_score:.2f}")
    print(f"Tier: {scorecard.tier.value}")
    print(f"Risk Level: {scorecard.risk_level.value}")
    print(f"Trend: {scorecard.trend}")
    
    print(f"\nCategory Scores:")
    for category, score in scorecard.category_scores.items():
        print(f"  {category.value}: {score:.2f}")
    
    print(f"\nRecommendations:")
    for rec in scorecard.recommendations:
        print(f"  - {rec}")
    
    # Run monitoring cycle
    monitoring_results = await tracker.run_monitoring_cycle()
    print(f"\nMonitoring Results:")
    print(f"Suppliers Monitored: {monitoring_results['suppliers_monitored']}")
    print(f"Alerts Generated: {monitoring_results['alerts_generated']}")
    print(f"Critical Alerts: {monitoring_results['critical_alerts']}")
    
    # Get dashboard
    dashboard = await tracker.get_supplier_dashboard(supplier.supplier_id)
    print(f"\nDashboard Summary:")
    print(f"Active Alerts: {len(dashboard['active_alerts'])}")
    print(f"Recent Quality Score: {dashboard['quality_metrics']['average_quality_score']:.2f}")


if __name__ == "__main__":
    asyncio.run(main())