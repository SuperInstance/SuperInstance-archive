"""
Retention Analytics System
Customer retention analysis, churn prediction, and retention strategies
"""

import sqlite3
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
import uuid
import statistics
import math
from collections import defaultdict


class ChurnRiskLevel(Enum):
    """Customer churn risk levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RetentionStage(Enum):
    """Customer retention lifecycle stages"""
    NEW = "new"
    ENGAGED = "engaged"
    STABLE = "stable"
    AT_RISK = "at_risk"
    CHURNED = "churned"


class InterventionType(Enum):
    """Retention intervention types"""
    EMAIL_CAMPAIGN = "email_campaign"
    PERSONAL_OUTREACH = "personal_outreach"
    DISCOUNT_OFFER = "discount_offer"
    PRODUCT_TRAINING = "product_training"
    ACCOUNT_REVIEW = "account_review"
    LOYALTY_PROGRAM = "loyalty_program"


@dataclass
class ChurnPrediction:
    """Churn prediction result"""
    contact_id: str
    churn_probability: float
    risk_level: ChurnRiskLevel
    risk_factors: List[str]
    predicted_churn_date: Optional[datetime]
    confidence_score: float


@dataclass
class RetentionMetrics:
    """Customer retention metrics"""
    customer_count: int
    retention_rate: float
    churn_rate: float
    avg_lifetime_days: float
    revenue_at_risk: float


class RetentionAnalyticsSystem:
    """Customer retention analytics and churn prediction system"""
    
    def __init__(self, db_path: str = "data/crm_sales.db"):
        self.db_path = db_path
        
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
        
    def analyze_customer_retention(self, period_months: int = 12) -> Dict[str, Any]:
        """Comprehensive customer retention analysis"""
        
        analysis_id = str(uuid.uuid4())
        start_date = (datetime.utcnow() - timedelta(days=period_months * 30)).isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get customer cohorts by join month
            cursor.execute("""
                SELECT 
                    strftime('%Y-%m', c.created_at) as cohort_month,
                    COUNT(DISTINCT c.contact_id) as customers,
                    COUNT(DISTINCT CASE WHEN o.status = 'won' THEN c.contact_id END) as paying_customers
                FROM contacts c
                LEFT JOIN opportunities o ON c.contact_id = o.contact_id
                WHERE c.created_at >= ?
                GROUP BY strftime('%Y-%m', c.created_at)
                ORDER BY cohort_month
            """, [start_date])
            
            cohorts = cursor.fetchall()
            
            # Calculate retention rates for each cohort
            cohort_analysis = []
            
            for cohort in cohorts:
                cohort_month = cohort['cohort_month']
                
                # Get retention data for different time periods
                retention_data = self._calculate_cohort_retention(cursor, cohort_month)
                
                cohort_analysis.append({
                    'cohort_month': cohort_month,
                    'initial_customers': cohort['customers'],
                    'paying_customers': cohort['paying_customers'],
                    'conversion_rate': (cohort['paying_customers'] / cohort['customers'] * 100) 
                                     if cohort['customers'] > 0 else 0,
                    'retention_rates': retention_data
                })
            
            # Overall retention metrics
            overall_metrics = self._calculate_overall_retention_metrics(cursor, start_date)
            
            # Customer lifetime analysis
            lifetime_analysis = self._analyze_customer_lifetime(cursor)
            
            return {
                'analysis_id': analysis_id,
                'period_months': period_months,
                'cohort_analysis': cohort_analysis,
                'overall_metrics': overall_metrics,
                'lifetime_analysis': lifetime_analysis,
                'generated_at': datetime.utcnow().isoformat()
            }
    
    def predict_customer_churn(self, model_type: str = "rule_based") -> Dict[str, Any]:
        """Predict customer churn using various models"""
        
        prediction_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get customer data for churn prediction
            cursor.execute("""
                SELECT 
                    c.contact_id,
                    c.first_name,
                    c.last_name,
                    c.company,
                    c.email,
                    c.created_at,
                    c.last_contact_date,
                    COUNT(o.opportunity_id) as total_opportunities,
                    COUNT(CASE WHEN o.status = 'won' THEN 1 END) as won_opportunities,
                    COALESCE(SUM(CASE WHEN o.status = 'won' THEN o.value ELSE 0 END), 0) as lifetime_value,
                    MAX(CASE WHEN o.status = 'won' THEN o.updated_at END) as last_purchase,
                    COUNT(CASE WHEN o.created_at >= DATE('now', '-90 days') THEN 1 END) as recent_activity,
                    JULIANDAY('now') - JULIANDAY(COALESCE(c.last_contact_date, c.created_at)) as days_since_contact,
                    JULIANDAY('now') - JULIANDAY(c.created_at) as customer_age_days
                FROM contacts c
                LEFT JOIN opportunities o ON c.contact_id = o.contact_id
                GROUP BY c.contact_id
                HAVING COUNT(CASE WHEN o.status = 'won' THEN 1 END) > 0
            """)
            
            customers = cursor.fetchall()
            
            if not customers:
                return {
                    'prediction_id': prediction_id,
                    'error': 'No customer data available for churn prediction'
                }
            
            # Perform churn prediction based on model type
            if model_type == "rule_based":
                predictions = self._rule_based_churn_prediction(customers)
            elif model_type == "statistical":
                predictions = self._statistical_churn_prediction(customers)
            else:
                predictions = self._rule_based_churn_prediction(customers)
            
            # Save predictions
            self._save_churn_predictions(cursor, prediction_id, predictions)
            
            conn.commit()
            
            # Analyze results
            risk_distribution = defaultdict(int)
            high_risk_customers = []
            
            for pred in predictions:
                risk_distribution[pred.risk_level.value] += 1
                if pred.risk_level in [ChurnRiskLevel.HIGH, ChurnRiskLevel.CRITICAL]:
                    high_risk_customers.append({
                        'contact_id': pred.contact_id,
                        'churn_probability': pred.churn_probability,
                        'risk_level': pred.risk_level.value,
                        'risk_factors': pred.risk_factors,
                        'confidence_score': pred.confidence_score
                    })
            
            return {
                'prediction_id': prediction_id,
                'model_type': model_type,
                'total_customers_analyzed': len(customers),
                'risk_distribution': dict(risk_distribution),
                'high_risk_customers': high_risk_customers,
                'predictions_summary': {
                    'avg_churn_probability': statistics.mean([p.churn_probability for p in predictions]),
                    'customers_at_risk': len(high_risk_customers),
                    'revenue_at_risk': sum([
                        next((c['lifetime_value'] for c in customers if c['contact_id'] == p['contact_id']), 0)
                        for p in high_risk_customers
                    ])
                },
                'generated_at': datetime.utcnow().isoformat()
            }
    
    def analyze_churn_factors(self) -> Dict[str, Any]:
        """Analyze factors that contribute to customer churn"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get churned vs retained customers
            cursor.execute("""
                SELECT 
                    c.contact_id,
                    c.created_at,
                    c.industry,
                    c.company_size,
                    c.country,
                    c.lead_source,
                    COUNT(o.opportunity_id) as total_opportunities,
                    COUNT(CASE WHEN o.status = 'won' THEN 1 END) as won_opportunities,
                    COALESCE(SUM(CASE WHEN o.status = 'won' THEN o.value ELSE 0 END), 0) as lifetime_value,
                    MAX(CASE WHEN o.status = 'won' THEN o.updated_at END) as last_purchase,
                    JULIANDAY('now') - JULIANDAY(MAX(CASE WHEN o.status = 'won' THEN o.updated_at END)) as days_since_purchase,
                    CASE 
                        WHEN MAX(CASE WHEN o.status = 'won' THEN o.updated_at END) < DATE('now', '-365 days') THEN 'churned'
                        WHEN MAX(CASE WHEN o.status = 'won' THEN o.updated_at END) >= DATE('now', '-90 days') THEN 'active'
                        ELSE 'at_risk'
                    END as customer_status
                FROM contacts c
                LEFT JOIN opportunities o ON c.contact_id = o.contact_id
                WHERE c.created_at <= DATE('now', '-180 days')
                GROUP BY c.contact_id
                HAVING COUNT(CASE WHEN o.status = 'won' THEN 1 END) > 0
            """)
            
            customers = cursor.fetchall()
            
            if not customers:
                return {'error': 'Insufficient data for churn factor analysis'}
            
            # Analyze different factors
            factor_analysis = {}
            
            # Industry analysis
            factor_analysis['industry'] = self._analyze_churn_by_factor(
                customers, 'industry', 'customer_status'
            )
            
            # Company size analysis
            factor_analysis['company_size'] = self._analyze_churn_by_factor(
                customers, 'company_size', 'customer_status'
            )
            
            # Geographic analysis
            factor_analysis['country'] = self._analyze_churn_by_factor(
                customers, 'country', 'customer_status'
            )
            
            # Lead source analysis
            factor_analysis['lead_source'] = self._analyze_churn_by_factor(
                customers, 'lead_source', 'customer_status'
            )
            
            # Purchase behavior analysis
            churned_customers = [c for c in customers if c['customer_status'] == 'churned']
            active_customers = [c for c in customers if c['customer_status'] == 'active']
            
            behavioral_analysis = {
                'churned_customers': {
                    'avg_lifetime_value': statistics.mean([c['lifetime_value'] for c in churned_customers]) if churned_customers else 0,
                    'avg_opportunities': statistics.mean([c['total_opportunities'] for c in churned_customers]) if churned_customers else 0,
                    'avg_conversion_rate': statistics.mean([
                        c['won_opportunities'] / c['total_opportunities'] if c['total_opportunities'] > 0 else 0 
                        for c in churned_customers
                    ]) if churned_customers else 0
                },
                'active_customers': {
                    'avg_lifetime_value': statistics.mean([c['lifetime_value'] for c in active_customers]) if active_customers else 0,
                    'avg_opportunities': statistics.mean([c['total_opportunities'] for c in active_customers]) if active_customers else 0,
                    'avg_conversion_rate': statistics.mean([
                        c['won_opportunities'] / c['total_opportunities'] if c['total_opportunities'] > 0 else 0 
                        for c in active_customers
                    ]) if active_customers else 0
                }
            }
            
            # Identify top churn indicators
            churn_indicators = self._identify_churn_indicators(customers)
            
            return {
                'total_customers_analyzed': len(customers),
                'customer_distribution': {
                    'churned': len(churned_customers),
                    'active': len(active_customers),
                    'at_risk': len([c for c in customers if c['customer_status'] == 'at_risk'])
                },
                'factor_analysis': factor_analysis,
                'behavioral_analysis': behavioral_analysis,
                'churn_indicators': churn_indicators,
                'generated_at': datetime.utcnow().isoformat()
            }
    
    def create_retention_campaign(self, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create targeted retention campaign"""
        
        campaign_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert campaign
            cursor.execute("""
                INSERT INTO retention_campaigns (
                    campaign_id, name, description, target_segment,
                    intervention_type, campaign_data, status,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                campaign_id,
                campaign_data['name'],
                campaign_data.get('description', ''),
                campaign_data.get('target_segment', 'at_risk'),
                campaign_data.get('intervention_type', InterventionType.EMAIL_CAMPAIGN.value),
                json.dumps(campaign_data),
                'active',
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ])
            
            # Find target customers
            target_customers = self._find_retention_targets(cursor, campaign_data)
            
            # Create campaign enrollments
            enrollments = []
            for customer in target_customers:
                enrollment_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO retention_campaign_enrollments (
                        enrollment_id, campaign_id, contact_id,
                        enrolled_at, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, [
                    enrollment_id,
                    campaign_id,
                    customer['contact_id'],
                    datetime.utcnow().isoformat(),
                    'enrolled',
                    datetime.utcnow().isoformat()
                ])
                
                enrollments.append({
                    'enrollment_id': enrollment_id,
                    'contact_id': customer['contact_id'],
                    'customer_name': f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip(),
                    'risk_level': customer.get('risk_level')
                })
            
            conn.commit()
            
            return {
                'campaign_id': campaign_id,
                'name': campaign_data['name'],
                'target_segment': campaign_data.get('target_segment'),
                'intervention_type': campaign_data.get('intervention_type'),
                'enrolled_customers': len(enrollments),
                'enrollments': enrollments[:50],  # First 50 for response size
                'created_at': datetime.utcnow().isoformat()
            }
    
    def track_retention_interventions(self, contact_id: str) -> Dict[str, Any]:
        """Track retention interventions for a specific customer"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get customer's intervention history
            cursor.execute("""
                SELECT 
                    rc.campaign_id,
                    rc.name as campaign_name,
                    rc.intervention_type,
                    rce.enrolled_at,
                    rce.status,
                    rce.completed_at,
                    rce.outcome
                FROM retention_campaign_enrollments rce
                JOIN retention_campaigns rc ON rce.campaign_id = rc.campaign_id
                WHERE rce.contact_id = ?
                ORDER BY rce.enrolled_at DESC
            """, [contact_id])
            
            interventions = []
            for result in cursor.fetchall():
                interventions.append({
                    'campaign_id': result['campaign_id'],
                    'campaign_name': result['campaign_name'],
                    'intervention_type': result['intervention_type'],
                    'enrolled_at': result['enrolled_at'],
                    'status': result['status'],
                    'completed_at': result['completed_at'],
                    'outcome': result['outcome']
                })
            
            # Get customer's current status and metrics
            cursor.execute("""
                SELECT 
                    c.*,
                    COUNT(o.opportunity_id) as total_opportunities,
                    COUNT(CASE WHEN o.status = 'won' THEN 1 END) as won_opportunities,
                    MAX(CASE WHEN o.status = 'won' THEN o.updated_at END) as last_purchase,
                    COALESCE(SUM(CASE WHEN o.status = 'won' THEN o.value ELSE 0 END), 0) as lifetime_value
                FROM contacts c
                LEFT JOIN opportunities o ON c.contact_id = o.contact_id
                WHERE c.contact_id = ?
                GROUP BY c.contact_id
            """, [contact_id])
            
            customer = cursor.fetchone()
            
            if not customer:
                return {'error': 'Customer not found'}
            
            # Calculate retention metrics
            days_since_last_purchase = None
            if customer['last_purchase']:
                days_since_last_purchase = (
                    datetime.utcnow() - datetime.fromisoformat(customer['last_purchase'])
                ).days
            
            return {
                'contact_id': contact_id,
                'customer_name': f"{customer['first_name']} {customer['last_name']}".strip(),
                'company': customer['company'],
                'customer_metrics': {
                    'lifetime_value': customer['lifetime_value'],
                    'total_opportunities': customer['total_opportunities'],
                    'won_opportunities': customer['won_opportunities'],
                    'last_purchase': customer['last_purchase'],
                    'days_since_last_purchase': days_since_last_purchase,
                    'customer_age_days': (
                        datetime.utcnow() - datetime.fromisoformat(customer['created_at'])
                    ).days
                },
                'interventions_history': interventions,
                'total_interventions': len(interventions),
                'active_campaigns': len([i for i in interventions if i['status'] == 'enrolled']),
                'successful_interventions': len([i for i in interventions if i['outcome'] == 'retained'])
            }
    
    def calculate_customer_health_score(self, contact_id: str) -> Dict[str, Any]:
        """Calculate comprehensive customer health score"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get customer data
            cursor.execute("""
                SELECT 
                    c.*,
                    COUNT(o.opportunity_id) as total_opportunities,
                    COUNT(CASE WHEN o.status = 'won' THEN 1 END) as won_opportunities,
                    COUNT(CASE WHEN o.status = 'open' THEN 1 END) as open_opportunities,
                    COALESCE(SUM(CASE WHEN o.status = 'won' THEN o.value ELSE 0 END), 0) as lifetime_value,
                    MAX(CASE WHEN o.status = 'won' THEN o.updated_at END) as last_purchase,
                    MIN(o.created_at) as first_opportunity,
                    COUNT(CASE WHEN o.created_at >= DATE('now', '-90 days') THEN 1 END) as recent_activity,
                    COUNT(CASE WHEN o.updated_at >= DATE('now', '-30 days') THEN 1 END) as very_recent_activity
                FROM contacts c
                LEFT JOIN opportunities o ON c.contact_id = o.contact_id
                WHERE c.contact_id = ?
                GROUP BY c.contact_id
            """, [contact_id])
            
            customer = cursor.fetchone()
            
            if not customer:
                return {'error': 'Customer not found'}
            
            # Calculate health score components
            health_components = {}
            
            # 1. Purchase recency (0-25 points)
            if customer['last_purchase']:
                days_since_purchase = (
                    datetime.utcnow() - datetime.fromisoformat(customer['last_purchase'])
                ).days
                
                if days_since_purchase <= 30:
                    health_components['recency'] = 25
                elif days_since_purchase <= 90:
                    health_components['recency'] = 20
                elif days_since_purchase <= 180:
                    health_components['recency'] = 15
                elif days_since_purchase <= 365:
                    health_components['recency'] = 10
                else:
                    health_components['recency'] = 0
            else:
                health_components['recency'] = 0
            
            # 2. Purchase frequency (0-25 points)
            customer_age_days = (
                datetime.utcnow() - datetime.fromisoformat(customer['created_at'])
            ).days
            
            if customer_age_days > 0:
                purchase_frequency = customer['won_opportunities'] / (customer_age_days / 30)  # purchases per month
                
                if purchase_frequency >= 2:
                    health_components['frequency'] = 25
                elif purchase_frequency >= 1:
                    health_components['frequency'] = 20
                elif purchase_frequency >= 0.5:
                    health_components['frequency'] = 15
                elif purchase_frequency >= 0.25:
                    health_components['frequency'] = 10
                else:
                    health_components['frequency'] = 5
            else:
                health_components['frequency'] = 0
            
            # 3. Lifetime value (0-25 points)
            ltv = customer['lifetime_value']
            if ltv >= 50000:
                health_components['value'] = 25
            elif ltv >= 20000:
                health_components['value'] = 20
            elif ltv >= 10000:
                health_components['value'] = 15
            elif ltv >= 5000:
                health_components['value'] = 10
            elif ltv > 0:
                health_components['value'] = 5
            else:
                health_components['value'] = 0
            
            # 4. Engagement level (0-25 points)
            engagement_score = 0
            if customer['very_recent_activity'] > 0:
                engagement_score += 10
            if customer['recent_activity'] > 0:
                engagement_score += 10
            if customer['open_opportunities'] > 0:
                engagement_score += 5
            
            health_components['engagement'] = min(25, engagement_score)
            
            # Calculate total health score
            total_health_score = sum(health_components.values())
            
            # Determine health status
            if total_health_score >= 80:
                health_status = "Excellent"
            elif total_health_score >= 60:
                health_status = "Good"
            elif total_health_score >= 40:
                health_status = "Fair"
            elif total_health_score >= 20:
                health_status = "Poor"
            else:
                health_status = "Critical"
            
            # Generate recommendations
            recommendations = self._generate_health_recommendations(
                health_components, customer
            )
            
            return {
                'contact_id': contact_id,
                'customer_name': f"{customer['first_name']} {customer['last_name']}".strip(),
                'health_score': total_health_score,
                'health_status': health_status,
                'health_components': health_components,
                'customer_metrics': {
                    'lifetime_value': customer['lifetime_value'],
                    'total_opportunities': customer['total_opportunities'],
                    'won_opportunities': customer['won_opportunities'],
                    'open_opportunities': customer['open_opportunities'],
                    'last_purchase': customer['last_purchase'],
                    'customer_age_days': customer_age_days,
                    'recent_activity': customer['recent_activity']
                },
                'recommendations': recommendations,
                'calculated_at': datetime.utcnow().isoformat()
            }
    
    def get_retention_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive retention analytics dashboard"""
        
        # Perform various retention analyses
        retention_analysis = self.analyze_customer_retention(12)
        churn_prediction = self.predict_customer_churn()
        churn_factors = self.analyze_churn_factors()
        
        # Get active retention campaigns
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    rc.campaign_id,
                    rc.name,
                    rc.intervention_type,
                    rc.created_at,
                    COUNT(rce.enrollment_id) as enrolled_customers,
                    COUNT(CASE WHEN rce.status = 'completed' THEN 1 END) as completed
                FROM retention_campaigns rc
                LEFT JOIN retention_campaign_enrollments rce ON rc.campaign_id = rce.campaign_id
                WHERE rc.status = 'active'
                GROUP BY rc.campaign_id
                ORDER BY rc.created_at DESC
                LIMIT 5
            """)
            
            active_campaigns = []
            for result in cursor.fetchall():
                active_campaigns.append({
                    'campaign_id': result['campaign_id'],
                    'name': result['name'],
                    'intervention_type': result['intervention_type'],
                    'enrolled_customers': result['enrolled_customers'],
                    'completed': result['completed'],
                    'completion_rate': (result['completed'] / result['enrolled_customers'] * 100) 
                                     if result['enrolled_customers'] > 0 else 0,
                    'created_at': result['created_at']
                })
            
            # Overall retention metrics
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT c.contact_id) as total_customers,
                    COUNT(DISTINCT CASE WHEN o.status = 'won' AND o.updated_at >= DATE('now', '-365 days') 
                        THEN c.contact_id END) as active_customers,
                    COUNT(DISTINCT CASE WHEN o.status = 'won' AND o.updated_at < DATE('now', '-365 days') 
                        THEN c.contact_id END) as churned_customers,
                    COALESCE(SUM(CASE WHEN o.status = 'won' THEN o.value ELSE 0 END), 0) as total_revenue
                FROM contacts c
                LEFT JOIN opportunities o ON c.contact_id = o.contact_id
                WHERE c.created_at <= DATE('now', '-180 days')
            """)
            
            overall_stats = cursor.fetchone()
        
        total_customers = overall_stats['total_customers']
        active_customers = overall_stats['active_customers']
        churned_customers = overall_stats['churned_customers']
        
        dashboard_metrics = {
            'total_customers': total_customers,
            'active_customers': active_customers,
            'churned_customers': churned_customers,
            'retention_rate': (active_customers / total_customers * 100) if total_customers > 0 else 0,
            'churn_rate': (churned_customers / total_customers * 100) if total_customers > 0 else 0,
            'total_revenue': overall_stats['total_revenue']
        }
        
        return {
            'dashboard_metrics': dashboard_metrics,
            'retention_analysis_summary': {
                'cohorts_analyzed': len(retention_analysis.get('cohort_analysis', [])),
                'avg_lifetime_days': retention_analysis.get('lifetime_analysis', {}).get('avg_lifetime_days', 0)
            },
            'churn_prediction_summary': {
                'customers_analyzed': churn_prediction.get('total_customers_analyzed', 0),
                'customers_at_risk': churn_prediction.get('predictions_summary', {}).get('customers_at_risk', 0),
                'revenue_at_risk': churn_prediction.get('predictions_summary', {}).get('revenue_at_risk', 0),
                'avg_churn_probability': churn_prediction.get('predictions_summary', {}).get('avg_churn_probability', 0)
            },
            'churn_factors_summary': {
                'top_churn_indicators': churn_factors.get('churn_indicators', [])[:3] if not churn_factors.get('error') else []
            },
            'active_retention_campaigns': active_campaigns,
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def _calculate_cohort_retention(self, cursor, cohort_month: str) -> Dict[str, float]:
        """Calculate retention rates for a specific cohort"""
        
        retention_periods = [1, 3, 6, 12]  # months
        retention_rates = {}
        
        # Get cohort customer IDs
        cursor.execute("""
            SELECT contact_id FROM contacts 
            WHERE strftime('%Y-%m', created_at) = ?
        """, [cohort_month])
        
        cohort_customers = [row['contact_id'] for row in cursor.fetchall()]
        initial_count = len(cohort_customers)
        
        if initial_count == 0:
            return {f'{p}_month': 0 for p in retention_periods}
        
        for period in retention_periods:
            # Count customers still active after period
            cursor.execute("""
                SELECT COUNT(DISTINCT c.contact_id) as retained_customers
                FROM contacts c
                JOIN opportunities o ON c.contact_id = o.contact_id
                WHERE c.contact_id IN ({})
                AND o.status = 'won'
                AND o.updated_at >= DATE(?, '+{} months')
                AND o.updated_at <= DATE('now')
            """.format(','.join('?' * len(cohort_customers)), period), 
            [cohort_month + '-01'] + cohort_customers)
            
            result = cursor.fetchone()
            retained_count = result['retained_customers'] or 0
            retention_rates[f'{period}_month'] = (retained_count / initial_count * 100)
        
        return retention_rates
    
    def _calculate_overall_retention_metrics(self, cursor, start_date: str) -> Dict[str, Any]:
        """Calculate overall retention metrics"""
        
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT c.contact_id) as total_customers,
                COUNT(DISTINCT CASE WHEN EXISTS (
                    SELECT 1 FROM opportunities o2 
                    WHERE o2.contact_id = c.contact_id 
                    AND o2.status = 'won' 
                    AND o2.updated_at >= DATE('now', '-12 months')
                ) THEN c.contact_id END) as retained_customers,
                COALESCE(AVG(JULIANDAY('now') - JULIANDAY(c.created_at)), 0) as avg_customer_age,
                COALESCE(SUM(CASE WHEN o.status = 'won' THEN o.value ELSE 0 END), 0) as total_revenue
            FROM contacts c
            LEFT JOIN opportunities o ON c.contact_id = o.contact_id
            WHERE c.created_at >= ?
            AND EXISTS (
                SELECT 1 FROM opportunities o3 
                WHERE o3.contact_id = c.contact_id 
                AND o3.status = 'won'
            )
        """, [start_date])
        
        result = cursor.fetchone()
        
        total_customers = result['total_customers'] or 0
        retained_customers = result['retained_customers'] or 0
        
        return {
            'total_customers': total_customers,
            'retained_customers': retained_customers,
            'retention_rate': (retained_customers / total_customers * 100) if total_customers > 0 else 0,
            'churn_rate': ((total_customers - retained_customers) / total_customers * 100) if total_customers > 0 else 0,
            'avg_customer_age_days': result['avg_customer_age'],
            'total_revenue': result['total_revenue']
        }
    
    def _analyze_customer_lifetime(self, cursor) -> Dict[str, Any]:
        """Analyze customer lifetime patterns"""
        
        cursor.execute("""
            SELECT 
                c.contact_id,
                JULIANDAY('now') - JULIANDAY(c.created_at) as lifetime_days,
                COUNT(CASE WHEN o.status = 'won' THEN 1 END) as purchases,
                COALESCE(SUM(CASE WHEN o.status = 'won' THEN o.value ELSE 0 END), 0) as lifetime_value,
                MIN(CASE WHEN o.status = 'won' THEN o.updated_at END) as first_purchase,
                MAX(CASE WHEN o.status = 'won' THEN o.updated_at END) as last_purchase
            FROM contacts c
            LEFT JOIN opportunities o ON c.contact_id = o.contact_id
            GROUP BY c.contact_id
            HAVING COUNT(CASE WHEN o.status = 'won' THEN 1 END) > 0
        """)
        
        customers = cursor.fetchall()
        
        if not customers:
            return {'error': 'No customer lifetime data available'}
        
        lifetime_days = [c['lifetime_days'] for c in customers]
        lifetime_values = [c['lifetime_value'] for c in customers]
        
        return {
            'total_customers': len(customers),
            'avg_lifetime_days': statistics.mean(lifetime_days),
            'median_lifetime_days': statistics.median(lifetime_days),
            'avg_lifetime_value': statistics.mean(lifetime_values),
            'median_lifetime_value': statistics.median(lifetime_values),
            'lifetime_distribution': {
                '0-30_days': len([d for d in lifetime_days if d <= 30]),
                '31-90_days': len([d for d in lifetime_days if 31 <= d <= 90]),
                '91-180_days': len([d for d in lifetime_days if 91 <= d <= 180]),
                '181-365_days': len([d for d in lifetime_days if 181 <= d <= 365]),
                '365+_days': len([d for d in lifetime_days if d > 365])
            }
        }
    
    def _rule_based_churn_prediction(self, customers: List[Dict[str, Any]]) -> List[ChurnPrediction]:
        """Rule-based churn prediction model"""
        
        predictions = []
        
        for customer in customers:
            risk_factors = []
            churn_score = 0
            
            # Factor 1: Days since last contact
            days_since_contact = customer['days_since_contact']
            if days_since_contact > 365:
                churn_score += 40
                risk_factors.append("No contact for over 1 year")
            elif days_since_contact > 180:
                churn_score += 25
                risk_factors.append("No contact for over 6 months")
            elif days_since_contact > 90:
                churn_score += 15
                risk_factors.append("No recent contact")
            
            # Factor 2: Purchase recency
            if customer['last_purchase']:
                last_purchase_days = (
                    datetime.utcnow() - datetime.fromisoformat(customer['last_purchase'])
                ).days
                
                if last_purchase_days > 365:
                    churn_score += 35
                    risk_factors.append("No purchases for over 1 year")
                elif last_purchase_days > 180:
                    churn_score += 20
                    risk_factors.append("No recent purchases")
            else:
                churn_score += 30
                risk_factors.append("No purchase history")
            
            # Factor 3: Recent activity
            if customer['recent_activity'] == 0:
                churn_score += 15
                risk_factors.append("No recent activity")
            
            # Factor 4: Customer value
            if customer['lifetime_value'] < 1000:
                churn_score += 10
                risk_factors.append("Low lifetime value")
            
            # Factor 5: Conversion rate
            conversion_rate = (customer['won_opportunities'] / customer['total_opportunities'] 
                             if customer['total_opportunities'] > 0 else 0)
            if conversion_rate < 0.2:
                churn_score += 10
                risk_factors.append("Low conversion rate")
            
            # Convert score to probability
            churn_probability = min(1.0, churn_score / 100)
            
            # Determine risk level
            if churn_probability >= 0.8:
                risk_level = ChurnRiskLevel.CRITICAL
            elif churn_probability >= 0.6:
                risk_level = ChurnRiskLevel.HIGH
            elif churn_probability >= 0.4:
                risk_level = ChurnRiskLevel.MEDIUM
            else:
                risk_level = ChurnRiskLevel.LOW
            
            # Predict churn date
            predicted_churn_date = None
            if churn_probability > 0.5:
                days_to_churn = max(30, 365 * (1 - churn_probability))
                predicted_churn_date = datetime.utcnow() + timedelta(days=days_to_churn)
            
            predictions.append(ChurnPrediction(
                contact_id=customer['contact_id'],
                churn_probability=churn_probability,
                risk_level=risk_level,
                risk_factors=risk_factors,
                predicted_churn_date=predicted_churn_date,
                confidence_score=min(1.0, len(risk_factors) / 5)
            ))
        
        return predictions
    
    def _statistical_churn_prediction(self, customers: List[Dict[str, Any]]) -> List[ChurnPrediction]:
        """Statistical churn prediction model"""
        
        # This is a simplified statistical model
        # In practice, you would use more sophisticated ML algorithms
        
        predictions = []
        
        # Calculate statistical thresholds
        days_since_contact_values = [c['days_since_contact'] for c in customers]
        lifetime_values = [c['lifetime_value'] for c in customers]
        
        contact_threshold = np.percentile(days_since_contact_values, 75)
        value_threshold = np.percentile(lifetime_values, 25)
        
        for customer in customers:
            # Calculate statistical features
            features = {
                'days_since_contact_normalized': min(1.0, customer['days_since_contact'] / 365),
                'value_score': 1.0 - (customer['lifetime_value'] / max(lifetime_values)) if max(lifetime_values) > 0 else 1.0,
                'activity_score': 1.0 - (customer['recent_activity'] / 10),
                'age_score': min(1.0, customer['customer_age_days'] / 730)  # 2 years
            }
            
            # Simple weighted scoring
            weights = {
                'days_since_contact_normalized': 0.4,
                'value_score': 0.3,
                'activity_score': 0.2,
                'age_score': 0.1
            }
            
            churn_probability = sum(features[f] * weights[f] for f in features)
            
            # Determine risk level
            if churn_probability >= 0.75:
                risk_level = ChurnRiskLevel.CRITICAL
            elif churn_probability >= 0.55:
                risk_level = ChurnRiskLevel.HIGH
            elif churn_probability >= 0.35:
                risk_level = ChurnRiskLevel.MEDIUM
            else:
                risk_level = ChurnRiskLevel.LOW
            
            # Generate risk factors based on features
            risk_factors = []
            if features['days_since_contact_normalized'] > 0.5:
                risk_factors.append("Prolonged inactivity")
            if features['value_score'] > 0.7:
                risk_factors.append("Low customer value")
            if features['activity_score'] > 0.6:
                risk_factors.append("Declining engagement")
            
            predictions.append(ChurnPrediction(
                contact_id=customer['contact_id'],
                churn_probability=churn_probability,
                risk_level=risk_level,
                risk_factors=risk_factors,
                predicted_churn_date=None,
                confidence_score=0.8  # Statistical model confidence
            ))
        
        return predictions
    
    def _analyze_churn_by_factor(self, customers: List[Dict[str, Any]], 
                                factor: str, status_field: str) -> Dict[str, Any]:
        """Analyze churn rates by a specific factor"""
        
        factor_analysis = defaultdict(lambda: {'total': 0, 'churned': 0, 'active': 0})
        
        for customer in customers:
            factor_value = customer.get(factor, 'Unknown')
            if factor_value is None:
                factor_value = 'Unknown'
                
            factor_analysis[factor_value]['total'] += 1
            
            if customer[status_field] == 'churned':
                factor_analysis[factor_value]['churned'] += 1
            elif customer[status_field] == 'active':
                factor_analysis[factor_value]['active'] += 1
        
        # Calculate churn rates
        result = {}
        for factor_value, data in factor_analysis.items():
            churn_rate = (data['churned'] / data['total'] * 100) if data['total'] > 0 else 0
            result[factor_value] = {
                'total_customers': data['total'],
                'churned_customers': data['churned'],
                'active_customers': data['active'],
                'churn_rate': churn_rate
            }
        
        return result
    
    def _identify_churn_indicators(self, customers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify the strongest churn indicators"""
        
        churned_customers = [c for c in customers if c['customer_status'] == 'churned']
        active_customers = [c for c in customers if c['customer_status'] == 'active']
        
        indicators = []
        
        # Analyze different metrics
        if churned_customers and active_customers:
            # Average days since contact
            churned_avg_contact_days = statistics.mean([c['days_since_contact'] for c in churned_customers])
            active_avg_contact_days = statistics.mean([c['days_since_contact'] for c in active_customers])
            
            if churned_avg_contact_days > active_avg_contact_days:
                indicators.append({
                    'indicator': 'Days since last contact',
                    'churned_avg': churned_avg_contact_days,
                    'active_avg': active_avg_contact_days,
                    'impact_score': min(100, (churned_avg_contact_days - active_avg_contact_days) / 10)
                })
            
            # Average lifetime value
            churned_avg_ltv = statistics.mean([c['lifetime_value'] for c in churned_customers])
            active_avg_ltv = statistics.mean([c['lifetime_value'] for c in active_customers])
            
            indicators.append({
                'indicator': 'Lifetime value',
                'churned_avg': churned_avg_ltv,
                'active_avg': active_avg_ltv,
                'impact_score': min(100, abs(active_avg_ltv - churned_avg_ltv) / 1000)
            })
        
        # Sort by impact score
        indicators.sort(key=lambda x: x['impact_score'], reverse=True)
        
        return indicators[:5]  # Top 5 indicators
    
    def _find_retention_targets(self, cursor, campaign_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find target customers for retention campaign"""
        
        target_segment = campaign_data.get('target_segment', 'at_risk')
        
        if target_segment == 'at_risk':
            # Customers with no activity in 90-365 days
            cursor.execute("""
                SELECT c.contact_id, c.first_name, c.last_name, c.company,
                       'medium' as risk_level
                FROM contacts c
                LEFT JOIN opportunities o ON c.contact_id = o.contact_id
                WHERE c.last_contact_date BETWEEN DATE('now', '-365 days') AND DATE('now', '-90 days')
                AND EXISTS (
                    SELECT 1 FROM opportunities o2 
                    WHERE o2.contact_id = c.contact_id AND o2.status = 'won'
                )
                LIMIT 100
            """)
        elif target_segment == 'high_risk':
            # Customers with high churn probability
            cursor.execute("""
                SELECT c.contact_id, c.first_name, c.last_name, c.company,
                       'high' as risk_level
                FROM contacts c
                LEFT JOIN opportunities o ON c.contact_id = o.contact_id
                WHERE c.last_contact_date < DATE('now', '-365 days')
                AND EXISTS (
                    SELECT 1 FROM opportunities o2 
                    WHERE o2.contact_id = c.contact_id AND o2.status = 'won'
                )
                LIMIT 100
            """)
        else:
            # Default to recent customers
            cursor.execute("""
                SELECT c.contact_id, c.first_name, c.last_name, c.company,
                       'low' as risk_level
                FROM contacts c
                WHERE c.created_at >= DATE('now', '-90 days')
                LIMIT 100
            """)
        
        return [dict(row) for row in cursor.fetchall()]
    
    def _generate_health_recommendations(self, health_components: Dict[str, int], 
                                       customer: Dict[str, Any]) -> List[str]:
        """Generate health score recommendations"""
        
        recommendations = []
        
        if health_components['recency'] < 15:
            recommendations.append("Immediate outreach required - customer showing signs of disengagement")
        elif health_components['recency'] < 20:
            recommendations.append("Schedule follow-up call to check customer satisfaction")
        
        if health_components['frequency'] < 10:
            recommendations.append("Develop nurturing campaign to increase purchase frequency")
        elif health_components['frequency'] < 15:
            recommendations.append("Identify cross-sell and upsell opportunities")
        
        if health_components['value'] < 10:
            recommendations.append("Focus on value demonstration and ROI improvement")
        elif health_components['value'] < 15:
            recommendations.append("Consider volume discounts or loyalty programs")
        
        if health_components['engagement'] < 10:
            recommendations.append("Re-engagement campaign with educational content")
        elif health_components['engagement'] < 15:
            recommendations.append("Increase touchpoints with relevant product updates")
        
        return recommendations
    
    def _save_churn_predictions(self, cursor, prediction_id: str, 
                              predictions: List[ChurnPrediction]):
        """Save churn predictions to database"""
        
        for pred in predictions:
            cursor.execute("""
                INSERT INTO churn_predictions (
                    prediction_id, contact_id, churn_probability, risk_level,
                    risk_factors, predicted_churn_date, confidence_score,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                prediction_id,
                pred.contact_id,
                pred.churn_probability,
                pred.risk_level.value,
                json.dumps(pred.risk_factors),
                pred.predicted_churn_date.isoformat() if pred.predicted_churn_date else None,
                pred.confidence_score,
                datetime.utcnow().isoformat()
            ])