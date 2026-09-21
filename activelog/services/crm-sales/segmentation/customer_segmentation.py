"""
Customer Segmentation System
Advanced customer segmentation using RFM, behavioral, and predictive analytics
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


class SegmentationType(Enum):
    """Customer segmentation types"""
    RFM = "rfm"  # Recency, Frequency, Monetary
    BEHAVIORAL = "behavioral"
    DEMOGRAPHIC = "demographic"
    PSYCHOGRAPHIC = "psychographic"
    GEOGRAPHIC = "geographic"
    LIFECYCLE = "lifecycle"
    VALUE_BASED = "value_based"
    PREDICTIVE = "predictive"


class RFMTier(Enum):
    """RFM analysis tiers"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class CustomerSegment:
    """Customer segment data structure"""
    segment_id: str
    name: str
    description: str
    segmentation_type: SegmentationType
    criteria: Dict[str, Any]
    customer_count: int
    avg_value: float
    created_at: datetime


@dataclass
class RFMScores:
    """RFM analysis scores"""
    recency_score: int
    frequency_score: int
    monetary_score: int
    rfm_score: str
    segment: str


class CustomerSegmentationSystem:
    """Customer segmentation and analytics system"""
    
    def __init__(self, db_path: str = "data/crm_sales.db"):
        self.db_path = db_path
        
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
        
    def perform_rfm_analysis(self, analysis_date: Optional[str] = None) -> Dict[str, Any]:
        """Perform RFM (Recency, Frequency, Monetary) analysis"""
        
        if analysis_date is None:
            analysis_date = datetime.utcnow().isoformat()
        
        analysis_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get customer transaction data
            cursor.execute("""
                SELECT 
                    c.contact_id,
                    c.first_name,
                    c.last_name,
                    c.company,
                    c.email,
                    COALESCE(MAX(JULIANDAY(?) - JULIANDAY(o.updated_at)), 9999) as recency_days,
                    COUNT(o.opportunity_id) as frequency,
                    COALESCE(SUM(CASE WHEN o.status = 'won' THEN o.value ELSE 0 END), 0) as monetary_value,
                    COALESCE(AVG(CASE WHEN o.status = 'won' THEN o.value END), 0) as avg_order_value,
                    MIN(o.created_at) as first_purchase,
                    MAX(CASE WHEN o.status = 'won' THEN o.updated_at END) as last_purchase
                FROM contacts c
                LEFT JOIN opportunities o ON c.contact_id = o.contact_id
                GROUP BY c.contact_id, c.first_name, c.last_name, c.company, c.email
                HAVING COUNT(o.opportunity_id) > 0 OR c.created_at >= DATE('now', '-2 years')
            """, [analysis_date])
            
            customers = cursor.fetchall()
            
            if not customers:
                return {
                    'analysis_id': analysis_id,
                    'error': 'No customer data available for RFM analysis'
                }
            
            # Calculate RFM scores
            rfm_data = []
            recency_values = [c['recency_days'] for c in customers if c['recency_days'] < 9999]
            frequency_values = [c['frequency'] for c in customers]
            monetary_values = [c['monetary_value'] for c in customers if c['monetary_value'] > 0]
            
            # Calculate quintiles for scoring
            recency_quintiles = self._calculate_quintiles(recency_values) if recency_values else [0, 0, 0, 0]
            frequency_quintiles = self._calculate_quintiles(frequency_values)
            monetary_quintiles = self._calculate_quintiles(monetary_values) if monetary_values else [0, 0, 0, 0]
            
            for customer in customers:
                # Calculate individual RFM scores (1-5 scale)
                r_score = self._calculate_recency_score(customer['recency_days'], recency_quintiles)
                f_score = self._calculate_frequency_score(customer['frequency'], frequency_quintiles)
                m_score = self._calculate_monetary_score(customer['monetary_value'], monetary_quintiles)
                
                # Create RFM score string
                rfm_score = f"{r_score}{f_score}{m_score}"
                
                # Determine segment
                segment = self._determine_rfm_segment(r_score, f_score, m_score)
                
                rfm_data.append({
                    'contact_id': customer['contact_id'],
                    'name': f"{customer['first_name']} {customer['last_name']}".strip(),
                    'company': customer['company'],
                    'email': customer['email'],
                    'recency_days': customer['recency_days'] if customer['recency_days'] < 9999 else None,
                    'frequency': customer['frequency'],
                    'monetary_value': customer['monetary_value'],
                    'avg_order_value': customer['avg_order_value'],
                    'recency_score': r_score,
                    'frequency_score': f_score,
                    'monetary_score': m_score,
                    'rfm_score': rfm_score,
                    'segment': segment,
                    'first_purchase': customer['first_purchase'],
                    'last_purchase': customer['last_purchase']
                })
            
            # Save RFM analysis results
            self._save_rfm_analysis(cursor, analysis_id, rfm_data, {
                'analysis_date': analysis_date,
                'total_customers': len(customers),
                'recency_quintiles': recency_quintiles,
                'frequency_quintiles': frequency_quintiles,
                'monetary_quintiles': monetary_quintiles
            })
            
            # Generate segment summary
            segment_summary = self._generate_rfm_segment_summary(rfm_data)
            
            conn.commit()
            
            return {
                'analysis_id': analysis_id,
                'analysis_date': analysis_date,
                'total_customers': len(customers),
                'rfm_data': rfm_data[:100],  # First 100 for response size
                'segment_summary': segment_summary,
                'quintiles': {
                    'recency': recency_quintiles,
                    'frequency': frequency_quintiles,
                    'monetary': monetary_quintiles
                }
            }
    
    def create_behavioral_segments(self, segment_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Create behavioral customer segments"""
        
        segment_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Build behavioral segmentation query based on criteria
            segments = []
            
            for segment_name, criteria in segment_criteria.items():
                customers = self._find_customers_by_behavior(cursor, criteria)
                
                if customers:
                    segments.append({
                        'segment_name': segment_name,
                        'criteria': criteria,
                        'customer_count': len(customers),
                        'customers': customers[:50],  # Limit for response size
                        'avg_value': statistics.mean([c.get('total_value', 0) for c in customers]) if customers else 0
                    })
            
            # Save segmentation
            cursor.execute("""
                INSERT INTO customer_segments (
                    segment_id, name, description, segmentation_type,
                    criteria, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [
                segment_id,
                "Behavioral Segmentation",
                "Customer segments based on behavioral patterns",
                SegmentationType.BEHAVIORAL.value,
                json.dumps(segment_criteria),
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ])
            
            conn.commit()
            
            return {
                'segmentation_id': segment_id,
                'segmentation_type': SegmentationType.BEHAVIORAL.value,
                'segments': segments,
                'total_segments': len(segments),
                'created_at': datetime.utcnow().isoformat()
            }
    
    def create_lifecycle_segments(self) -> Dict[str, Any]:
        """Create customer lifecycle segments"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Define lifecycle stages
            lifecycle_segments = {
                'new_leads': {
                    'description': 'Recent leads with no purchases',
                    'criteria': 'created within 30 days, no won opportunities',
                    'customers': []
                },
                'prospects': {
                    'description': 'Engaged leads with active opportunities',
                    'criteria': 'has open opportunities',
                    'customers': []
                },
                'first_time_buyers': {
                    'description': 'Made their first purchase recently',
                    'criteria': 'exactly 1 won opportunity within 90 days',
                    'customers': []
                },
                'repeat_customers': {
                    'description': 'Multiple purchases, active',
                    'criteria': 'multiple won opportunities, recent activity',
                    'customers': []
                },
                'loyal_customers': {
                    'description': 'High-value, long-term customers',
                    'criteria': 'high monetary value, long relationship',
                    'customers': []
                },
                'at_risk': {
                    'description': 'Previously active, now inactive',
                    'criteria': 'no activity for 180+ days, had previous purchases',
                    'customers': []
                },
                'dormant': {
                    'description': 'Inactive for extended period',
                    'criteria': 'no activity for 365+ days',
                    'customers': []
                }
            }
            
            # New leads
            cursor.execute("""
                SELECT c.contact_id, c.first_name, c.last_name, c.company, c.email,
                       c.created_at, COUNT(o.opportunity_id) as opportunity_count
                FROM contacts c
                LEFT JOIN opportunities o ON c.contact_id = o.contact_id
                WHERE c.created_at >= DATE('now', '-30 days')
                GROUP BY c.contact_id
                HAVING COUNT(CASE WHEN o.status = 'won' THEN 1 END) = 0
                ORDER BY c.created_at DESC
            """)
            
            lifecycle_segments['new_leads']['customers'] = [
                {
                    'contact_id': r['contact_id'],
                    'name': f"{r['first_name']} {r['last_name']}".strip(),
                    'company': r['company'],
                    'email': r['email'],
                    'created_at': r['created_at'],
                    'days_since_created': (datetime.utcnow() - datetime.fromisoformat(r['created_at'])).days
                }
                for r in cursor.fetchall()
            ]
            
            # Prospects with active opportunities
            cursor.execute("""
                SELECT c.contact_id, c.first_name, c.last_name, c.company, c.email,
                       COUNT(o.opportunity_id) as active_opportunities,
                       SUM(o.value) as pipeline_value
                FROM contacts c
                JOIN opportunities o ON c.contact_id = o.contact_id
                WHERE o.status = 'open'
                GROUP BY c.contact_id
                ORDER BY pipeline_value DESC
            """)
            
            lifecycle_segments['prospects']['customers'] = [
                {
                    'contact_id': r['contact_id'],
                    'name': f"{r['first_name']} {r['last_name']}".strip(),
                    'company': r['company'],
                    'email': r['email'],
                    'active_opportunities': r['active_opportunities'],
                    'pipeline_value': r['pipeline_value']
                }
                for r in cursor.fetchall()
            ]
            
            # First-time buyers
            cursor.execute("""
                SELECT c.contact_id, c.first_name, c.last_name, c.company, c.email,
                       o.value as first_purchase_value, o.updated_at as purchase_date
                FROM contacts c
                JOIN opportunities o ON c.contact_id = o.contact_id
                WHERE o.status = 'won' AND o.updated_at >= DATE('now', '-90 days')
                AND c.contact_id IN (
                    SELECT contact_id 
                    FROM opportunities 
                    WHERE status = 'won' 
                    GROUP BY contact_id 
                    HAVING COUNT(*) = 1
                )
                ORDER BY o.updated_at DESC
            """)
            
            lifecycle_segments['first_time_buyers']['customers'] = [
                {
                    'contact_id': r['contact_id'],
                    'name': f"{r['first_name']} {r['last_name']}".strip(),
                    'company': r['company'],
                    'email': r['email'],
                    'first_purchase_value': r['first_purchase_value'],
                    'purchase_date': r['purchase_date'],
                    'days_since_purchase': (datetime.utcnow() - datetime.fromisoformat(r['purchase_date'])).days
                }
                for r in cursor.fetchall()
            ]
            
            # Repeat customers
            cursor.execute("""
                SELECT c.contact_id, c.first_name, c.last_name, c.company, c.email,
                       COUNT(o.opportunity_id) as purchase_count,
                       SUM(o.value) as total_value,
                       MAX(o.updated_at) as last_purchase
                FROM contacts c
                JOIN opportunities o ON c.contact_id = o.contact_id
                WHERE o.status = 'won' AND o.updated_at >= DATE('now', '-180 days')
                GROUP BY c.contact_id
                HAVING COUNT(o.opportunity_id) > 1
                ORDER BY total_value DESC
            """)
            
            lifecycle_segments['repeat_customers']['customers'] = [
                {
                    'contact_id': r['contact_id'],
                    'name': f"{r['first_name']} {r['last_name']}".strip(),
                    'company': r['company'],
                    'email': r['email'],
                    'purchase_count': r['purchase_count'],
                    'total_value': r['total_value'],
                    'last_purchase': r['last_purchase'],
                    'avg_purchase_value': r['total_value'] / r['purchase_count']
                }
                for r in cursor.fetchall()
            ]
            
            # At-risk customers
            cursor.execute("""
                SELECT c.contact_id, c.first_name, c.last_name, c.company, c.email,
                       COUNT(o.opportunity_id) as total_purchases,
                       SUM(o.value) as total_value,
                       MAX(o.updated_at) as last_activity,
                       JULIANDAY('now') - JULIANDAY(MAX(o.updated_at)) as days_since_activity
                FROM contacts c
                JOIN opportunities o ON c.contact_id = o.contact_id
                WHERE o.status = 'won'
                GROUP BY c.contact_id
                HAVING MAX(o.updated_at) BETWEEN DATE('now', '-365 days') AND DATE('now', '-180 days')
                AND COUNT(o.opportunity_id) > 0
                ORDER BY total_value DESC
            """)
            
            lifecycle_segments['at_risk']['customers'] = [
                {
                    'contact_id': r['contact_id'],
                    'name': f"{r['first_name']} {r['last_name']}".strip(),
                    'company': r['company'],
                    'email': r['email'],
                    'total_purchases': r['total_purchases'],
                    'total_value': r['total_value'],
                    'last_activity': r['last_activity'],
                    'days_since_activity': int(r['days_since_activity']),
                    'risk_score': min(100, int(r['days_since_activity'] / 365 * 100))
                }
                for r in cursor.fetchall()
            ]
            
            # Calculate summary statistics
            summary = {}
            for segment_name, segment_data in lifecycle_segments.items():
                customers = segment_data['customers']
                summary[segment_name] = {
                    'count': len(customers),
                    'avg_value': statistics.mean([c.get('total_value', 0) for c in customers]) if customers else 0,
                    'description': segment_data['description']
                }
            
            return {
                'segmentation_type': SegmentationType.LIFECYCLE.value,
                'segments': lifecycle_segments,
                'summary': summary,
                'total_customers_segmented': sum(s['count'] for s in summary.values()),
                'generated_at': datetime.utcnow().isoformat()
            }
    
    def create_value_based_segments(self) -> Dict[str, Any]:
        """Create value-based customer segments"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get customer lifetime values
            cursor.execute("""
                SELECT 
                    c.contact_id,
                    c.first_name,
                    c.last_name,
                    c.company,
                    c.email,
                    COALESCE(SUM(CASE WHEN o.status = 'won' THEN o.value ELSE 0 END), 0) as lifetime_value,
                    COUNT(CASE WHEN o.status = 'won' THEN 1 END) as purchase_count,
                    COALESCE(AVG(CASE WHEN o.status = 'won' THEN o.value END), 0) as avg_purchase_value,
                    MIN(o.created_at) as first_purchase,
                    MAX(CASE WHEN o.status = 'won' THEN o.updated_at END) as last_purchase
                FROM contacts c
                LEFT JOIN opportunities o ON c.contact_id = o.contact_id
                GROUP BY c.contact_id
                HAVING lifetime_value > 0
                ORDER BY lifetime_value DESC
            """)
            
            customers = cursor.fetchall()
            
            if not customers:
                return {
                    'error': 'No customer purchase data available for value-based segmentation'
                }
            
            # Calculate value tiers
            lifetime_values = [c['lifetime_value'] for c in customers]
            value_percentiles = [
                np.percentile(lifetime_values, 80),  # Top 20%
                np.percentile(lifetime_values, 60),  # Top 40%
                np.percentile(lifetime_values, 40),  # Top 60%
                np.percentile(lifetime_values, 20)   # Top 80%
            ]
            
            value_segments = {
                'vip_customers': {
                    'description': 'Top 20% highest value customers',
                    'min_value': value_percentiles[0],
                    'customers': []
                },
                'high_value': {
                    'description': 'Top 20-40% value customers',
                    'min_value': value_percentiles[1],
                    'max_value': value_percentiles[0],
                    'customers': []
                },
                'medium_value': {
                    'description': 'Middle 40-60% value customers',
                    'min_value': value_percentiles[2],
                    'max_value': value_percentiles[1],
                    'customers': []
                },
                'low_value': {
                    'description': 'Lower 20-40% value customers',
                    'min_value': value_percentiles[3],
                    'max_value': value_percentiles[2],
                    'customers': []
                },
                'minimal_value': {
                    'description': 'Bottom 20% value customers',
                    'max_value': value_percentiles[3],
                    'customers': []
                }
            }
            
            # Assign customers to value segments
            for customer in customers:
                ltv = customer['lifetime_value']
                
                if ltv >= value_percentiles[0]:
                    segment = 'vip_customers'
                elif ltv >= value_percentiles[1]:
                    segment = 'high_value'
                elif ltv >= value_percentiles[2]:
                    segment = 'medium_value'
                elif ltv >= value_percentiles[3]:
                    segment = 'low_value'
                else:
                    segment = 'minimal_value'
                
                value_segments[segment]['customers'].append({
                    'contact_id': customer['contact_id'],
                    'name': f"{customer['first_name']} {customer['last_name']}".strip(),
                    'company': customer['company'],
                    'email': customer['email'],
                    'lifetime_value': customer['lifetime_value'],
                    'purchase_count': customer['purchase_count'],
                    'avg_purchase_value': customer['avg_purchase_value'],
                    'first_purchase': customer['first_purchase'],
                    'last_purchase': customer['last_purchase']
                })
            
            # Calculate segment statistics
            segment_stats = {}
            for segment_name, segment_data in value_segments.items():
                customers = segment_data['customers']
                segment_stats[segment_name] = {
                    'count': len(customers),
                    'total_value': sum(c['lifetime_value'] for c in customers),
                    'avg_value': statistics.mean([c['lifetime_value'] for c in customers]) if customers else 0,
                    'min_value': min([c['lifetime_value'] for c in customers]) if customers else 0,
                    'max_value': max([c['lifetime_value'] for c in customers]) if customers else 0,
                    'description': segment_data['description']
                }
            
            return {
                'segmentation_type': SegmentationType.VALUE_BASED.value,
                'segments': value_segments,
                'segment_statistics': segment_stats,
                'value_percentiles': value_percentiles,
                'total_customers': len(customers),
                'total_lifetime_value': sum(c['lifetime_value'] for c in customers),
                'generated_at': datetime.utcnow().isoformat()
            }
    
    def create_geographic_segments(self) -> Dict[str, Any]:
        """Create geographic customer segments"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Segment by country
            cursor.execute("""
                SELECT 
                    COALESCE(c.country, 'Unknown') as country,
                    COUNT(c.contact_id) as customer_count,
                    COALESCE(SUM(CASE WHEN o.status = 'won' THEN o.value ELSE 0 END), 0) as total_revenue,
                    COALESCE(AVG(CASE WHEN o.status = 'won' THEN o.value END), 0) as avg_deal_size,
                    COUNT(CASE WHEN o.status = 'won' THEN 1 END) as won_deals
                FROM contacts c
                LEFT JOIN opportunities o ON c.contact_id = o.contact_id
                GROUP BY c.country
                ORDER BY total_revenue DESC
            """)
            
            country_segments = []
            for result in cursor.fetchall():
                country_segments.append({
                    'country': result['country'],
                    'customer_count': result['customer_count'],
                    'total_revenue': result['total_revenue'],
                    'avg_deal_size': result['avg_deal_size'],
                    'won_deals': result['won_deals'],
                    'conversion_rate': (result['won_deals'] / result['customer_count'] * 100) 
                                     if result['customer_count'] > 0 else 0
                })
            
            # Segment by state/region
            cursor.execute("""
                SELECT 
                    COALESCE(c.state, 'Unknown') as state,
                    COALESCE(c.country, 'Unknown') as country,
                    COUNT(c.contact_id) as customer_count,
                    COALESCE(SUM(CASE WHEN o.status = 'won' THEN o.value ELSE 0 END), 0) as total_revenue
                FROM contacts c
                LEFT JOIN opportunities o ON c.contact_id = o.contact_id
                WHERE c.state IS NOT NULL AND c.state != ''
                GROUP BY c.state, c.country
                ORDER BY total_revenue DESC
                LIMIT 20
            """)
            
            state_segments = []
            for result in cursor.fetchall():
                state_segments.append({
                    'state': result['state'],
                    'country': result['country'],
                    'customer_count': result['customer_count'],
                    'total_revenue': result['total_revenue']
                })
            
            # Urban vs Rural (based on city population - simplified)
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN c.city IN ('New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 
                                      'Philadelphia', 'San Antonio', 'San Diego', 'Dallas', 'San Jose',
                                      'London', 'Paris', 'Berlin', 'Madrid', 'Rome', 'Toronto', 'Vancouver') 
                        THEN 'Major Urban'
                        WHEN c.city IS NOT NULL AND c.city != '' THEN 'Urban/Suburban'
                        ELSE 'Unknown/Rural'
                    END as location_type,
                    COUNT(c.contact_id) as customer_count,
                    COALESCE(SUM(CASE WHEN o.status = 'won' THEN o.value ELSE 0 END), 0) as total_revenue,
                    COALESCE(AVG(CASE WHEN o.status = 'won' THEN o.value END), 0) as avg_deal_size
                FROM contacts c
                LEFT JOIN opportunities o ON c.contact_id = o.contact_id
                GROUP BY location_type
                ORDER BY total_revenue DESC
            """)
            
            location_segments = []
            for result in cursor.fetchall():
                location_segments.append({
                    'location_type': result['location_type'],
                    'customer_count': result['customer_count'],
                    'total_revenue': result['total_revenue'],
                    'avg_deal_size': result['avg_deal_size']
                })
            
            return {
                'segmentation_type': SegmentationType.GEOGRAPHIC.value,
                'country_segments': country_segments,
                'state_segments': state_segments,
                'location_type_segments': location_segments,
                'total_countries': len([s for s in country_segments if s['country'] != 'Unknown']),
                'generated_at': datetime.utcnow().isoformat()
            }
    
    def get_segment_recommendations(self, contact_id: str) -> Dict[str, Any]:
        """Get personalized recommendations for a customer segment"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get customer details
            cursor.execute("""
                SELECT c.*, 
                       COUNT(o.opportunity_id) as total_opportunities,
                       COUNT(CASE WHEN o.status = 'won' THEN 1 END) as won_opportunities,
                       COALESCE(SUM(CASE WHEN o.status = 'won' THEN o.value ELSE 0 END), 0) as lifetime_value,
                       MAX(o.updated_at) as last_activity
                FROM contacts c
                LEFT JOIN opportunities o ON c.contact_id = o.contact_id
                WHERE c.contact_id = ?
                GROUP BY c.contact_id
            """, [contact_id])
            
            customer = cursor.fetchone()
            if not customer:
                return {'error': 'Customer not found'}
            
            # Determine customer's primary segment
            rfm_analysis = self.perform_rfm_analysis()
            customer_rfm = None
            
            for rfm_data in rfm_analysis.get('rfm_data', []):
                if rfm_data['contact_id'] == contact_id:
                    customer_rfm = rfm_data
                    break
            
            # Generate recommendations based on segment
            recommendations = []
            
            if customer_rfm:
                segment = customer_rfm['segment']
                
                if segment == 'Champions':
                    recommendations = [
                        "Invite to VIP program or loyalty rewards",
                        "Request referrals and testimonials",
                        "Offer exclusive early access to new products",
                        "Provide premium customer support"
                    ]
                elif segment == 'Loyal Customers':
                    recommendations = [
                        "Upsell complementary products or services",
                        "Offer volume discounts for bulk purchases",
                        "Create personalized product recommendations",
                        "Invite to customer advisory board"
                    ]
                elif segment == 'Potential Loyalists':
                    recommendations = [
                        "Offer loyalty program enrollment",
                        "Send targeted product recommendations",
                        "Provide educational content about product usage",
                        "Follow up with satisfaction surveys"
                    ]
                elif segment == 'At Risk':
                    recommendations = [
                        "Reach out with special retention offer",
                        "Conduct 'win-back' email campaign",
                        "Offer customer success consultation",
                        "Provide limited-time discount or incentive"
                    ]
                elif segment in ['Hibernating', 'Lost']:
                    recommendations = [
                        "Launch re-engagement campaign",
                        "Offer significant discount to return",
                        "Survey to understand reason for inactivity",
                        "Consider if customer is worth retention cost"
                    ]
                else:  # New customers, etc.
                    recommendations = [
                        "Send welcome series and onboarding materials",
                        "Provide educational content and best practices",
                        "Schedule follow-up call to ensure satisfaction",
                        "Offer training or implementation support"
                    ]
            
            # Add value-based recommendations
            if customer['lifetime_value'] > 10000:
                recommendations.append("Assign dedicated account manager")
                recommendations.append("Invite to exclusive customer events")
            elif customer['lifetime_value'] > 5000:
                recommendations.append("Quarterly business review meetings")
                recommendations.append("Priority customer support")
            
            # Add behavioral recommendations
            if customer['total_opportunities'] > customer['won_opportunities'] * 2:
                recommendations.append("Improve sales process and follow-up")
                recommendations.append("Provide better qualification criteria")
            
            return {
                'contact_id': contact_id,
                'customer_name': f"{customer['first_name']} {customer['last_name']}".strip(),
                'company': customer['company'],
                'primary_segment': customer_rfm['segment'] if customer_rfm else 'Unknown',
                'rfm_scores': {
                    'recency': customer_rfm['recency_score'] if customer_rfm else None,
                    'frequency': customer_rfm['frequency_score'] if customer_rfm else None,
                    'monetary': customer_rfm['monetary_score'] if customer_rfm else None
                } if customer_rfm else None,
                'customer_metrics': {
                    'lifetime_value': customer['lifetime_value'],
                    'total_opportunities': customer['total_opportunities'],
                    'won_opportunities': customer['won_opportunities'],
                    'conversion_rate': (customer['won_opportunities'] / customer['total_opportunities'] * 100) 
                                     if customer['total_opportunities'] > 0 else 0,
                    'last_activity': customer['last_activity']
                },
                'recommendations': recommendations,
                'priority_score': self._calculate_priority_score(customer, customer_rfm),
                'generated_at': datetime.utcnow().isoformat()
            }
    
    def get_segmentation_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive segmentation dashboard"""
        
        # Perform various segmentation analyses
        rfm_analysis = self.perform_rfm_analysis()
        lifecycle_segments = self.create_lifecycle_segments()
        value_segments = self.create_value_based_segments()
        geographic_segments = self.create_geographic_segments()
        
        # Calculate overall metrics
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT c.contact_id) as total_customers,
                    COUNT(DISTINCT CASE WHEN o.status = 'won' THEN c.contact_id END) as paying_customers,
                    COALESCE(SUM(CASE WHEN o.status = 'won' THEN o.value ELSE 0 END), 0) as total_revenue,
                    COUNT(CASE WHEN o.status = 'won' THEN 1 END) as total_transactions
                FROM contacts c
                LEFT JOIN opportunities o ON c.contact_id = o.contact_id
            """)
            
            overall_metrics = cursor.fetchone()
        
        return {
            'overall_metrics': {
                'total_customers': overall_metrics['total_customers'],
                'paying_customers': overall_metrics['paying_customers'],
                'total_revenue': overall_metrics['total_revenue'],
                'total_transactions': overall_metrics['total_transactions'],
                'customer_conversion_rate': (overall_metrics['paying_customers'] / 
                                           overall_metrics['total_customers'] * 100) 
                                          if overall_metrics['total_customers'] > 0 else 0
            },
            'rfm_analysis': {
                'total_analyzed': len(rfm_analysis.get('rfm_data', [])),
                'segment_summary': rfm_analysis.get('segment_summary', {})
            },
            'lifecycle_segments': {
                'total_segmented': lifecycle_segments.get('total_customers_segmented', 0),
                'summary': lifecycle_segments.get('summary', {})
            },
            'value_segments': {
                'total_customers': value_segments.get('total_customers', 0) if not value_segments.get('error') else 0,
                'total_lifetime_value': value_segments.get('total_lifetime_value', 0) if not value_segments.get('error') else 0,
                'segment_stats': value_segments.get('segment_statistics', {}) if not value_segments.get('error') else {}
            },
            'geographic_distribution': {
                'total_countries': geographic_segments.get('total_countries', 0),
                'top_countries': geographic_segments.get('country_segments', [])[:5]
            },
            'dashboard_generated_at': datetime.utcnow().isoformat()
        }
    
    def _calculate_quintiles(self, values: List[float]) -> List[float]:
        """Calculate quintiles for scoring"""
        if not values:
            return [0, 0, 0, 0]
        
        return [
            np.percentile(values, 20),
            np.percentile(values, 40),
            np.percentile(values, 60),
            np.percentile(values, 80)
        ]
    
    def _calculate_recency_score(self, recency_days: float, quintiles: List[float]) -> int:
        """Calculate recency score (1-5, with 5 being most recent)"""
        if recency_days is None or recency_days >= 9999:
            return 1  # No recent activity
        
        # For recency, lower values (more recent) get higher scores
        if recency_days <= quintiles[0]:
            return 5
        elif recency_days <= quintiles[1]:
            return 4
        elif recency_days <= quintiles[2]:
            return 3
        elif recency_days <= quintiles[3]:
            return 2
        else:
            return 1
    
    def _calculate_frequency_score(self, frequency: int, quintiles: List[float]) -> int:
        """Calculate frequency score (1-5, with 5 being highest frequency)"""
        if frequency >= quintiles[3]:
            return 5
        elif frequency >= quintiles[2]:
            return 4
        elif frequency >= quintiles[1]:
            return 3
        elif frequency >= quintiles[0]:
            return 2
        else:
            return 1
    
    def _calculate_monetary_score(self, monetary_value: float, quintiles: List[float]) -> int:
        """Calculate monetary score (1-5, with 5 being highest value)"""
        if monetary_value <= 0:
            return 1
        
        if monetary_value >= quintiles[3]:
            return 5
        elif monetary_value >= quintiles[2]:
            return 4
        elif monetary_value >= quintiles[1]:
            return 3
        elif monetary_value >= quintiles[0]:
            return 2
        else:
            return 1
    
    def _determine_rfm_segment(self, r_score: int, f_score: int, m_score: int) -> str:
        """Determine customer segment based on RFM scores"""
        
        # Define segment rules based on RFM scores
        if r_score >= 4 and f_score >= 4 and m_score >= 4:
            return "Champions"
        elif r_score >= 3 and f_score >= 4 and m_score >= 4:
            return "Loyal Customers"
        elif r_score >= 4 and f_score >= 3 and m_score >= 3:
            return "Potential Loyalists"
        elif r_score >= 4 and f_score <= 2:
            return "New Customers"
        elif r_score >= 3 and f_score >= 3 and m_score >= 3:
            return "Promising"
        elif r_score >= 3 and f_score <= 2:
            return "Need Attention"
        elif r_score <= 2 and f_score >= 3:
            return "At Risk"
        elif r_score <= 2 and f_score <= 2 and m_score >= 3:
            return "Cannot Lose Them"
        elif r_score <= 2 and f_score <= 2 and m_score <= 2:
            return "Hibernating"
        else:
            return "Lost"
    
    def _find_customers_by_behavior(self, cursor, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find customers matching behavioral criteria"""
        
        # Build query based on criteria
        query = """
            SELECT c.contact_id, c.first_name, c.last_name, c.company, c.email,
                   COUNT(o.opportunity_id) as total_opportunities,
                   COUNT(CASE WHEN o.status = 'won' THEN 1 END) as won_opportunities,
                   COALESCE(SUM(CASE WHEN o.status = 'won' THEN o.value ELSE 0 END), 0) as total_value,
                   MAX(o.updated_at) as last_activity
            FROM contacts c
            LEFT JOIN opportunities o ON c.contact_id = o.contact_id
        """
        
        where_conditions = []
        params = []
        
        if 'min_opportunities' in criteria:
            where_conditions.append("COUNT(o.opportunity_id) >= ?")
            params.append(criteria['min_opportunities'])
        
        if 'min_value' in criteria:
            where_conditions.append("SUM(CASE WHEN o.status = 'won' THEN o.value ELSE 0 END) >= ?")
            params.append(criteria['min_value'])
        
        if 'activity_period_days' in criteria:
            where_conditions.append("MAX(o.updated_at) >= DATE('now', '-{} days')".format(criteria['activity_period_days']))
        
        if where_conditions:
            query += " GROUP BY c.contact_id HAVING " + " AND ".join(where_conditions)
        else:
            query += " GROUP BY c.contact_id"
        
        cursor.execute(query, params)
        
        customers = []
        for result in cursor.fetchall():
            customers.append({
                'contact_id': result['contact_id'],
                'name': f"{result['first_name']} {result['last_name']}".strip(),
                'company': result['company'],
                'email': result['email'],
                'total_opportunities': result['total_opportunities'],
                'won_opportunities': result['won_opportunities'],
                'total_value': result['total_value'],
                'last_activity': result['last_activity']
            })
        
        return customers
    
    def _generate_rfm_segment_summary(self, rfm_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics for RFM segments"""
        
        segment_stats = defaultdict(lambda: {
            'count': 0,
            'total_value': 0,
            'avg_recency': 0,
            'avg_frequency': 0,
            'avg_monetary': 0
        })
        
        for customer in rfm_data:
            segment = customer['segment']
            segment_stats[segment]['count'] += 1
            segment_stats[segment]['total_value'] += customer['monetary_value']
            
            if customer['recency_days'] is not None:
                segment_stats[segment]['avg_recency'] += customer['recency_days']
            
            segment_stats[segment]['avg_frequency'] += customer['frequency']
            segment_stats[segment]['avg_monetary'] += customer['monetary_value']
        
        # Calculate averages
        for segment in segment_stats:
            count = segment_stats[segment]['count']
            if count > 0:
                segment_stats[segment]['avg_recency'] /= count
                segment_stats[segment]['avg_frequency'] /= count
                segment_stats[segment]['avg_monetary'] /= count
                segment_stats[segment]['percentage'] = (count / len(rfm_data)) * 100
        
        return dict(segment_stats)
    
    def _save_rfm_analysis(self, cursor, analysis_id: str, rfm_data: List[Dict[str, Any]], 
                          metadata: Dict[str, Any]):
        """Save RFM analysis results"""
        
        cursor.execute("""
            INSERT INTO rfm_analyses (
                analysis_id, analysis_data, metadata, created_at
            ) VALUES (?, ?, ?, ?)
        """, [
            analysis_id,
            json.dumps(rfm_data),
            json.dumps(metadata),
            datetime.utcnow().isoformat()
        ])
        
        # Update individual customer RFM scores
        for customer in rfm_data:
            cursor.execute("""
                UPDATE contacts 
                SET rfm_score = ?, rfm_segment = ?, updated_at = ?
                WHERE contact_id = ?
            """, [
                customer['rfm_score'],
                customer['segment'],
                datetime.utcnow().isoformat(),
                customer['contact_id']
            ])
    
    def _calculate_priority_score(self, customer: Dict[str, Any], 
                                customer_rfm: Optional[Dict[str, Any]]) -> int:
        """Calculate customer priority score (0-100)"""
        
        score = 0
        
        # Lifetime value component (0-40 points)
        ltv = customer.get('lifetime_value', 0)
        if ltv > 50000:
            score += 40
        elif ltv > 20000:
            score += 30
        elif ltv > 10000:
            score += 20
        elif ltv > 5000:
            score += 10
        
        # RFM component (0-30 points)
        if customer_rfm:
            rfm_total = customer_rfm['recency_score'] + customer_rfm['frequency_score'] + customer_rfm['monetary_score']
            score += min(30, (rfm_total / 15) * 30)
        
        # Conversion rate component (0-20 points)
        total_opps = customer.get('total_opportunities', 0)
        won_opps = customer.get('won_opportunities', 0)
        if total_opps > 0:
            conversion_rate = won_opps / total_opps
            score += conversion_rate * 20
        
        # Activity recency component (0-10 points)
        if customer.get('last_activity'):
            days_since = (datetime.utcnow() - datetime.fromisoformat(customer['last_activity'])).days
            if days_since <= 30:
                score += 10
            elif days_since <= 90:
                score += 5
        
        return min(100, int(score))