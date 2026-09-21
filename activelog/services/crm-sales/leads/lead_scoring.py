"""
Lead Scoring System
Advanced lead scoring with ML capabilities and behavioral tracking
"""

import json
import math
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ScoreType(Enum):
    DEMOGRAPHIC = "demographic"
    BEHAVIORAL = "behavioral"
    ENGAGEMENT = "engagement"
    FIRMOGRAPHIC = "firmographic"


class ScoreOperation(Enum):
    ADD = "add"
    SUBTRACT = "subtract"
    MULTIPLY = "multiply"
    SET = "set"


@dataclass
class ScoringRule:
    rule_id: str
    name: str
    score_type: ScoreType
    condition_field: str
    condition_operator: str
    condition_value: str
    score_change: int
    operation: ScoreOperation
    weight: float
    is_active: bool


class LeadScoringSystem:
    """Advanced lead scoring with behavioral tracking"""
    
    def __init__(self, config, db):
        self.config = config
        self.db = db
        
        # Scoring configuration
        self.enabled = config.get('lead_scoring.enabled', True)
        self.auto_scoring_enabled = config.get('lead_scoring.auto_scoring_enabled', True)
        self.score_range = config.get('lead_scoring.score_range', {'min': 0, 'max': 100})
        self.hot_lead_threshold = config.get('lead_scoring.hot_lead_threshold', 80)
        self.warm_lead_threshold = config.get('lead_scoring.warm_lead_threshold', 60)
        self.cold_lead_threshold = config.get('lead_scoring.cold_lead_threshold', 40)
        
        # Scoring behavior
        self.scoring_frequency_hours = config.get('lead_scoring.scoring_frequency_hours', 24)
        self.decay_enabled = config.get('lead_scoring.decay_enabled', True)
        self.decay_rate_days = config.get('lead_scoring.decay_rate_days', 30)
        
        # Initialize default scoring rules
        self.initialize_default_rules()
        
    def initialize_default_rules(self):
        """Initialize default lead scoring rules"""
        try:
            # Check if rules already exist
            existing_rules = self.db.execute_query("SELECT COUNT(*) as count FROM lead_scoring_rules")
            if existing_rules and existing_rules[0]['count'] > 0:
                return
                
            default_rules = [
                # Demographic scoring
                {
                    'name': 'Email Provided',
                    'score_type': ScoreType.DEMOGRAPHIC.value,
                    'condition_field': 'email',
                    'condition_operator': 'is_not_empty',
                    'condition_value': '',
                    'score_change': 10,
                    'operation': ScoreOperation.ADD.value,
                    'weight': 1.0
                },
                {
                    'name': 'Phone Provided',
                    'score_type': ScoreType.DEMOGRAPHIC.value,
                    'condition_field': 'phone',
                    'condition_operator': 'is_not_empty',
                    'condition_value': '',
                    'score_change': 5,
                    'operation': ScoreOperation.ADD.value,
                    'weight': 1.0
                },
                {
                    'name': 'Title - C-Level',
                    'score_type': ScoreType.DEMOGRAPHIC.value,
                    'condition_field': 'title',
                    'condition_operator': 'contains',
                    'condition_value': 'CEO,CTO,CFO,CMO,President',
                    'score_change': 25,
                    'operation': ScoreOperation.ADD.value,
                    'weight': 1.5
                },
                {
                    'name': 'Title - Manager/Director',
                    'score_type': ScoreType.DEMOGRAPHIC.value,
                    'condition_field': 'title',
                    'condition_operator': 'contains',
                    'condition_value': 'Manager,Director,VP',
                    'score_change': 15,
                    'operation': ScoreOperation.ADD.value,
                    'weight': 1.2
                },
                
                # Firmographic scoring
                {
                    'name': 'Company Size - Large',
                    'score_type': ScoreType.FIRMOGRAPHIC.value,
                    'condition_field': 'company_size',
                    'condition_operator': 'equals',
                    'condition_value': 'Enterprise,Large',
                    'score_change': 20,
                    'operation': ScoreOperation.ADD.value,
                    'weight': 1.3
                },
                {
                    'name': 'Industry - Technology',
                    'score_type': ScoreType.FIRMOGRAPHIC.value,
                    'condition_field': 'industry',
                    'condition_operator': 'equals',
                    'condition_value': 'Technology,Software,SaaS',
                    'score_change': 15,
                    'operation': ScoreOperation.ADD.value,
                    'weight': 1.1
                },
                
                # Lead source scoring
                {
                    'name': 'Lead Source - Referral',
                    'score_type': ScoreType.BEHAVIORAL.value,
                    'condition_field': 'lead_source',
                    'condition_operator': 'equals',
                    'condition_value': 'referral',
                    'score_change': 25,
                    'operation': ScoreOperation.ADD.value,
                    'weight': 1.5
                },
                {
                    'name': 'Lead Source - Website',
                    'score_type': ScoreType.BEHAVIORAL.value,
                    'condition_field': 'lead_source',
                    'condition_operator': 'equals',
                    'condition_value': 'website',
                    'score_change': 15,
                    'operation': ScoreOperation.ADD.value,
                    'weight': 1.2
                },
                
                # Engagement scoring
                {
                    'name': 'Email Opened',
                    'score_type': ScoreType.ENGAGEMENT.value,
                    'condition_field': 'email_opened',
                    'condition_operator': 'equals',
                    'condition_value': 'true',
                    'score_change': 5,
                    'operation': ScoreOperation.ADD.value,
                    'weight': 1.0
                },
                {
                    'name': 'Email Clicked',
                    'score_type': ScoreType.ENGAGEMENT.value,
                    'condition_field': 'email_clicked',
                    'condition_operator': 'equals',
                    'condition_value': 'true',
                    'score_change': 10,
                    'operation': ScoreOperation.ADD.value,
                    'weight': 1.2
                },
                {
                    'name': 'Website Visit',
                    'score_type': ScoreType.ENGAGEMENT.value,
                    'condition_field': 'website_visits',
                    'condition_operator': 'greater_than',
                    'condition_value': '0',
                    'score_change': 8,
                    'operation': ScoreOperation.ADD.value,
                    'weight': 1.1
                }
            ]
            
            # Save default rules
            for rule_data in default_rules:
                self.create_scoring_rule(rule_data)
                
        except Exception as e:
            print(f"Error initializing default scoring rules: {e}")
            
    def calculate_lead_score(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive lead score"""
        try:
            contact_id = lead_data.get('contact_id')
            
            if not contact_id:
                # Calculate score for new lead data
                return self.calculate_score_for_data(lead_data)
            else:
                # Calculate score for existing contact
                contact = self.db.get_contact(contact_id)
                if not contact:
                    raise ValueError("Contact not found")
                    
                return self.calculate_score_for_contact(contact)
                
        except Exception as e:
            raise Exception(f"Error calculating lead score: {e}")
            
    def calculate_score_for_data(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate score for lead data"""
        try:
            # Get active scoring rules
            rules = self.get_active_scoring_rules()
            
            base_score = 0
            score_breakdown = []
            applied_rules = []
            
            # Apply demographic and firmographic rules
            for rule in rules:
                if rule['score_type'] in [ScoreType.DEMOGRAPHIC.value, ScoreType.FIRMOGRAPHIC.value]:
                    if self.evaluate_rule_condition(rule, lead_data):
                        score_change = self.apply_score_operation(
                            base_score, 
                            rule['score_change'], 
                            rule['operation'], 
                            rule['weight']
                        )
                        base_score = max(0, min(100, base_score + score_change))
                        
                        applied_rules.append({
                            'rule_name': rule['name'],
                            'score_change': score_change,
                            'score_type': rule['score_type']
                        })
                        
                        score_breakdown.append({
                            'category': rule['score_type'],
                            'rule': rule['name'],
                            'points': score_change
                        })
                        
            # Get behavioral and engagement data if contact exists
            if lead_data.get('contact_id'):
                behavioral_score = self.calculate_behavioral_score(lead_data['contact_id'])
                engagement_score = self.calculate_engagement_score(lead_data['contact_id'])
                
                base_score = min(100, base_score + behavioral_score + engagement_score)
                
                if behavioral_score > 0:
                    score_breakdown.append({
                        'category': 'behavioral',
                        'rule': 'Behavioral Activities',
                        'points': behavioral_score
                    })
                    
                if engagement_score > 0:
                    score_breakdown.append({
                        'category': 'engagement',
                        'rule': 'Engagement Activities',
                        'points': engagement_score
                    })
                    
            # Apply score decay if enabled
            if self.decay_enabled and lead_data.get('last_activity_date'):
                decay_factor = self.calculate_score_decay(lead_data['last_activity_date'])
                decayed_score = int(base_score * decay_factor)
                
                if decayed_score != base_score:
                    score_breakdown.append({
                        'category': 'decay',
                        'rule': 'Time Decay',
                        'points': decayed_score - base_score
                    })
                    base_score = decayed_score
                    
            # Determine score level
            score_level = self.get_score_level(base_score)
            
            return {
                'total_score': base_score,
                'score_level': score_level,
                'score_breakdown': score_breakdown,
                'applied_rules': applied_rules,
                'calculation_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Error calculating score for data: {e}")
            
    def calculate_score_for_contact(self, contact: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate score for existing contact"""
        try:
            contact_data = contact.copy()
            
            # Add company data if available
            if contact.get('company_id'):
                company = self.db.get_company(contact['company_id'])
                if company:
                    contact_data['company_size'] = company.get('size')
                    contact_data['industry'] = company.get('industry')
                    contact_data['company_revenue'] = company.get('revenue')
                    
            # Add engagement data
            contact_data['email_opened'] = self.has_opened_emails(contact['contact_id'])
            contact_data['email_clicked'] = self.has_clicked_emails(contact['contact_id'])
            contact_data['website_visits'] = self.get_website_visit_count(contact['contact_id'])
            contact_data['last_activity_date'] = self.get_last_activity_date(contact['contact_id'])
            
            # Calculate score
            score_result = self.calculate_score_for_data(contact_data)
            
            # Update contact score if auto-scoring is enabled
            if self.auto_scoring_enabled:
                self.db.update_contact(contact['contact_id'], {
                    'lead_score': score_result['total_score'],
                    'updated_at': datetime.now().isoformat()
                })
                
                # Log scoring activity
                self.log_scoring_activity(contact['contact_id'], score_result)
                
            return score_result
            
        except Exception as e:
            raise Exception(f"Error calculating score for contact: {e}")
            
    def calculate_behavioral_score(self, contact_id: str) -> int:
        """Calculate behavioral score based on activities"""
        try:
            score = 0
            
            # Get recent activities (last 30 days)
            thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
            activities = self.db.execute_query(
                "SELECT * FROM activities WHERE contact_id = ? AND created_at >= ?",
                (contact_id, thirty_days_ago)
            )
            
            activity_scores = {
                'email': 2,
                'call': 5,
                'meeting': 10,
                'demo': 15,
                'proposal': 20,
                'contract': 25
            }
            
            for activity in activities:
                activity_type = activity['activity_type'].lower()
                for key, points in activity_scores.items():
                    if key in activity_type:
                        score += points
                        break
                        
            return min(score, 30)  # Cap behavioral score at 30
            
        except Exception:
            return 0
            
    def calculate_engagement_score(self, contact_id: str) -> int:
        """Calculate engagement score"""
        try:
            score = 0
            
            # Email engagement
            if self.has_opened_emails(contact_id):
                score += 5
            if self.has_clicked_emails(contact_id):
                score += 10
                
            # Website engagement
            visit_count = self.get_website_visit_count(contact_id)
            if visit_count > 0:
                score += min(visit_count * 2, 20)  # 2 points per visit, max 20
                
            # Form submissions
            form_submissions = self.get_form_submission_count(contact_id)
            if form_submissions > 0:
                score += min(form_submissions * 5, 15)  # 5 points per submission, max 15
                
            return min(score, 25)  # Cap engagement score at 25
            
        except Exception:
            return 0
            
    def calculate_score_decay(self, last_activity_date: str) -> float:
        """Calculate score decay factor based on last activity"""
        try:
            last_activity = datetime.fromisoformat(last_activity_date)
            days_since = (datetime.now() - last_activity).days
            
            if days_since <= self.decay_rate_days:
                return 1.0  # No decay
            else:
                # Exponential decay after decay period
                decay_factor = math.exp(-(days_since - self.decay_rate_days) / self.decay_rate_days)
                return max(decay_factor, 0.1)  # Minimum 10% of original score
                
        except Exception:
            return 1.0
            
    def evaluate_rule_condition(self, rule: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Evaluate if rule condition is met"""
        try:
            field_value = data.get(rule['condition_field'], '')
            condition_value = rule['condition_value']
            operator = rule['condition_operator']
            
            if operator == 'equals':
                if ',' in condition_value:
                    # Multiple values (OR condition)
                    return str(field_value).lower() in [v.strip().lower() for v in condition_value.split(',')]
                else:
                    return str(field_value).lower() == condition_value.lower()
                    
            elif operator == 'contains':
                if ',' in condition_value:
                    # Check if field contains any of the values
                    values = [v.strip().lower() for v in condition_value.split(',')]
                    field_lower = str(field_value).lower()
                    return any(value in field_lower for value in values)
                else:
                    return condition_value.lower() in str(field_value).lower()
                    
            elif operator == 'is_not_empty':
                return field_value is not None and str(field_value).strip() != ''
                
            elif operator == 'is_empty':
                return field_value is None or str(field_value).strip() == ''
                
            elif operator == 'greater_than':
                try:
                    return float(field_value) > float(condition_value)
                except (ValueError, TypeError):
                    return False
                    
            elif operator == 'less_than':
                try:
                    return float(field_value) < float(condition_value)
                except (ValueError, TypeError):
                    return False
                    
            elif operator == 'starts_with':
                return str(field_value).lower().startswith(condition_value.lower())
                
            elif operator == 'ends_with':
                return str(field_value).lower().endswith(condition_value.lower())
                
            return False
            
        except Exception:
            return False
            
    def apply_score_operation(self, current_score: int, score_change: int, operation: str, weight: float = 1.0) -> int:
        """Apply score operation with weight"""
        try:
            weighted_change = int(score_change * weight)
            
            if operation == ScoreOperation.ADD.value:
                return weighted_change
            elif operation == ScoreOperation.SUBTRACT.value:
                return -weighted_change
            elif operation == ScoreOperation.MULTIPLY.value:
                return int(current_score * (weighted_change / 100))
            elif operation == ScoreOperation.SET.value:
                return weighted_change - current_score
            else:
                return weighted_change
                
        except Exception:
            return 0
            
    def get_score_level(self, score: int) -> str:
        """Get descriptive score level"""
        if score >= self.hot_lead_threshold:
            return "Hot"
        elif score >= self.warm_lead_threshold:
            return "Warm"
        elif score >= self.cold_lead_threshold:
            return "Cool"
        else:
            return "Cold"
            
    def create_scoring_rule(self, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new scoring rule"""
        try:
            rule_id = f"rule_{datetime.now().timestamp()}"
            
            rule = {
                'rule_id': rule_id,
                'name': rule_data['name'],
                'condition_field': rule_data['condition_field'],
                'condition_operator': rule_data['condition_operator'],
                'condition_value': rule_data['condition_value'],
                'score_change': rule_data['score_change'],
                'is_active': rule_data.get('is_active', True),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            success = self.db.save_record('lead_scoring_rules', rule)
            if not success:
                raise Exception("Failed to save scoring rule")
                
            return {
                'success': True,
                'rule_id': rule_id,
                'message': 'Scoring rule created successfully'
            }
            
        except Exception as e:
            raise Exception(f"Error creating scoring rule: {e}")
            
    def get_scoring_rules(self) -> List[Dict[str, Any]]:
        """Get all scoring rules"""
        try:
            rules = self.db.execute_query("SELECT * FROM lead_scoring_rules ORDER BY created_at DESC")
            return rules
            
        except Exception as e:
            raise Exception(f"Error getting scoring rules: {e}")
            
    def get_active_scoring_rules(self) -> List[Dict[str, Any]]:
        """Get active scoring rules"""
        try:
            rules = self.db.execute_query(
                "SELECT * FROM lead_scoring_rules WHERE is_active = 1 ORDER BY name"
            )
            return rules
            
        except Exception:
            return []
            
    def update_scoring_rule(self, rule_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update scoring rule"""
        try:
            updates['updated_at'] = datetime.now().isoformat()
            
            success = self.db.update_record('lead_scoring_rules', 'rule_id', rule_id, updates)
            if not success:
                raise Exception("Failed to update scoring rule")
                
            return {
                'success': True,
                'rule_id': rule_id,
                'message': 'Scoring rule updated successfully'
            }
            
        except Exception as e:
            raise Exception(f"Error updating scoring rule: {e}")
            
    def delete_scoring_rule(self, rule_id: str) -> Dict[str, Any]:
        """Delete scoring rule (deactivate)"""
        try:
            success = self.db.update_record('lead_scoring_rules', 'rule_id', rule_id, {
                'is_active': False,
                'updated_at': datetime.now().isoformat()
            })
            
            if not success:
                raise Exception("Failed to deactivate scoring rule")
                
            return {
                'success': True,
                'rule_id': rule_id,
                'message': 'Scoring rule deactivated successfully'
            }
            
        except Exception as e:
            raise Exception(f"Error deleting scoring rule: {e}")
            
    def get_hot_leads(self, threshold: float = None) -> List[Dict[str, Any]]:
        """Get high-scoring leads"""
        try:
            if threshold is None:
                threshold = self.hot_lead_threshold
                
            hot_leads = self.db.execute_query(
                "SELECT * FROM contacts WHERE lead_score >= ? AND contact_status = 'active' ORDER BY lead_score DESC",
                (threshold,)
            )
            
            # Enrich lead data
            enriched_leads = []
            for lead in hot_leads:
                enriched_lead = self.enrich_lead_data(lead)
                enriched_leads.append(enriched_lead)
                
            return enriched_leads
            
        except Exception as e:
            raise Exception(f"Error getting hot leads: {e}")
            
    def bulk_rescore_contacts(self, contact_ids: List[str] = None) -> Dict[str, Any]:
        """Bulk rescore contacts"""
        try:
            if contact_ids is None:
                # Rescore all active contacts
                contacts = self.db.execute_query(
                    "SELECT contact_id FROM contacts WHERE contact_status = 'active'"
                )
                contact_ids = [contact['contact_id'] for contact in contacts]
                
            rescored_count = 0
            errors = []
            
            for contact_id in contact_ids:
                try:
                    contact = self.db.get_contact(contact_id)
                    if contact:
                        score_result = self.calculate_score_for_contact(contact)
                        rescored_count += 1
                except Exception as e:
                    errors.append({'contact_id': contact_id, 'error': str(e)})
                    
            return {
                'success': True,
                'rescored_count': rescored_count,
                'total_requested': len(contact_ids),
                'errors': errors,
                'message': f'Rescored {rescored_count} contacts'
            }
            
        except Exception as e:
            raise Exception(f"Error bulk rescoring contacts: {e}")
            
    def get_scoring_analytics(self, period_days: int = 30) -> Dict[str, Any]:
        """Get lead scoring analytics"""
        try:
            start_date = (datetime.now() - timedelta(days=period_days)).isoformat()
            
            # Score distribution
            score_distribution = self.db.execute_query("""
                SELECT 
                    CASE 
                        WHEN lead_score >= ? THEN 'Hot'
                        WHEN lead_score >= ? THEN 'Warm' 
                        WHEN lead_score >= ? THEN 'Cool'
                        ELSE 'Cold'
                    END as score_level,
                    COUNT(*) as count
                FROM contacts 
                WHERE contact_status = 'active'
                GROUP BY score_level
            """, (self.hot_lead_threshold, self.warm_lead_threshold, self.cold_lead_threshold))
            
            # Average scores by lead source
            source_scores = self.db.execute_query("""
                SELECT 
                    lead_source,
                    AVG(lead_score) as avg_score,
                    COUNT(*) as count
                FROM contacts 
                WHERE contact_status = 'active' AND created_at >= ?
                GROUP BY lead_source
                ORDER BY avg_score DESC
            """, (start_date,))
            
            # Score trends (would need historical data)
            total_contacts = self.db.execute_single_query(
                "SELECT COUNT(*) as count FROM contacts WHERE contact_status = 'active'"
            )
            
            return {
                'period_days': period_days,
                'score_distribution': score_distribution,
                'source_performance': source_scores,
                'total_active_contacts': total_contacts['count'] if total_contacts else 0,
                'hot_leads_count': len(self.get_hot_leads()),
                'average_score': self.get_average_lead_score()
            }
            
        except Exception as e:
            raise Exception(f"Error getting scoring analytics: {e}")
            
    def enrich_lead_data(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich lead data for display"""
        try:
            enriched = lead.copy()
            
            # Add full name
            enriched['full_name'] = f"{lead['first_name']} {lead['last_name']}"
            
            # Add score level
            enriched['score_level'] = self.get_score_level(lead.get('lead_score', 0))
            
            # Add company information
            if lead.get('company_id'):
                company = self.db.get_company(lead['company_id'])
                if company:
                    enriched['company_name'] = company['name']
                    enriched['company_industry'] = company.get('industry')
                    
            # Add last activity
            last_activity = self.get_last_activity_date(lead['contact_id'])
            if last_activity:
                enriched['last_activity_date'] = last_activity
                enriched['days_since_activity'] = (datetime.now() - datetime.fromisoformat(last_activity)).days
                
            return enriched
            
        except Exception:
            return lead
            
    def get_average_lead_score(self) -> float:
        """Get average lead score for active contacts"""
        try:
            result = self.db.execute_single_query(
                "SELECT AVG(lead_score) as avg_score FROM contacts WHERE contact_status = 'active'"
            )
            return round(result['avg_score'], 2) if result and result['avg_score'] else 0.0
        except Exception:
            return 0.0
            
    def log_scoring_activity(self, contact_id: str, score_result: Dict[str, Any]):
        """Log scoring activity for audit trail"""
        try:
            activity_id = f"scoring_{datetime.now().timestamp()}"
            
            activity = {
                'activity_id': activity_id,
                'activity_type': 'lead_scored',
                'subject': f'Lead Score Updated: {score_result["total_score"]}',
                'description': f'Lead score updated to {score_result["total_score"]} ({score_result["score_level"]})',
                'contact_id': contact_id,
                'status': 'completed',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            self.db.save_activity(activity)
            
        except Exception as e:
            print(f"Error logging scoring activity: {e}")
            
    # Helper methods for engagement data
    def has_opened_emails(self, contact_id: str) -> bool:
        """Check if contact has opened emails"""
        try:
            result = self.db.execute_single_query(
                "SELECT COUNT(*) as count FROM campaign_recipients WHERE contact_id = ? AND opened_at IS NOT NULL",
                (contact_id,)
            )
            return result['count'] > 0 if result else False
        except Exception:
            return False
            
    def has_clicked_emails(self, contact_id: str) -> bool:
        """Check if contact has clicked email links"""
        try:
            result = self.db.execute_single_query(
                "SELECT COUNT(*) as count FROM campaign_recipients WHERE contact_id = ? AND clicked_at IS NOT NULL",
                (contact_id,)
            )
            return result['count'] > 0 if result else False
        except Exception:
            return False
            
    def get_website_visit_count(self, contact_id: str) -> int:
        """Get website visit count (would integrate with analytics)"""
        try:
            # This would integrate with website analytics
            # For now, return mock data based on activities
            result = self.db.execute_single_query(
                "SELECT COUNT(*) as count FROM activities WHERE contact_id = ? AND activity_type = 'website_visit'",
                (contact_id,)
            )
            return result['count'] if result else 0
        except Exception:
            return 0
            
    def get_form_submission_count(self, contact_id: str) -> int:
        """Get form submission count"""
        try:
            result = self.db.execute_single_query(
                "SELECT COUNT(*) as count FROM activities WHERE contact_id = ? AND activity_type = 'form_submission'",
                (contact_id,)
            )
            return result['count'] if result else 0
        except Exception:
            return 0
            
    def get_last_activity_date(self, contact_id: str) -> Optional[str]:
        """Get last activity date for contact"""
        try:
            result = self.db.execute_single_query(
                "SELECT MAX(created_at) as last_activity FROM activities WHERE contact_id = ?",
                (contact_id,)
            )
            return result['last_activity'] if result else None
        except Exception:
            return None