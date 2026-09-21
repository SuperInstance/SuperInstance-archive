"""
Opportunity Tracking System
Comprehensive sales opportunity management and tracking
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class OpportunityStage(Enum):
    LEAD = "lead"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class OpportunityPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OpportunityType(Enum):
    NEW_BUSINESS = "new_business"
    EXPANSION = "expansion"
    RENEWAL = "renewal"
    UPSELL = "upsell"


@dataclass
class OpportunityStageInfo:
    stage: str
    probability: float
    order: int
    is_closed: bool
    is_won: bool


class OpportunityTracker:
    """Advanced opportunity tracking and management"""
    
    def __init__(self, config, db):
        self.config = config
        self.db = db
        
        # Opportunity settings
        self.default_probability = config.get('opportunities.default_probability', 50.0)
        self.auto_stage_progression = config.get('opportunities.auto_stage_progression', False)
        self.weighted_pipeline_enabled = config.get('opportunities.weighted_pipeline_enabled', True)
        self.opportunity_aging_days = config.get('opportunities.opportunity_aging_days', 90)
        self.auto_close_stale_opportunities = config.get('opportunities.auto_close_stale_opportunities', True)
        self.require_close_reason = config.get('opportunities.require_close_reason', True)
        
        # Initialize pipeline stages
        self.initialize_pipeline_stages()
        
    def initialize_pipeline_stages(self):
        """Initialize default pipeline stages"""
        try:
            # Check if stages already exist
            existing_stages = self.db.execute_query("SELECT COUNT(*) as count FROM pipeline_stages")
            if existing_stages and existing_stages[0]['count'] > 0:
                return
                
            default_stages = self.config.get('pipeline.default_stages', [
                {'name': 'Lead', 'probability': 10, 'order': 1},
                {'name': 'Qualified', 'probability': 25, 'order': 2},
                {'name': 'Proposal', 'probability': 50, 'order': 3},
                {'name': 'Negotiation', 'probability': 75, 'order': 4},
                {'name': 'Closed Won', 'probability': 100, 'order': 5},
                {'name': 'Closed Lost', 'probability': 0, 'order': 6}
            ])
            
            for stage_data in default_stages:
                stage = {
                    'stage_id': f"stage_{datetime.now().timestamp()}_{stage_data['order']}",
                    'name': stage_data['name'],
                    'probability': stage_data['probability'],
                    'stage_order': stage_data['order'],
                    'is_closed': stage_data['name'].startswith('Closed'),
                    'is_won': stage_data['name'] == 'Closed Won',
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                
                self.db.save_record('pipeline_stages', stage)
                
        except Exception as e:
            print(f"Error initializing pipeline stages: {e}")
            
    def create_opportunity(self, opportunity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new sales opportunity"""
        try:
            # Validate required fields
            required_fields = ['name', 'company_id', 'owner_id', 'close_date']
            for field in required_fields:
                if field not in opportunity_data:
                    raise ValueError(f"Missing required field: {field}")
                    
            # Generate opportunity ID
            opportunity_id = f"opp_{datetime.now().timestamp()}"
            
            # Get stage information
            stage_name = opportunity_data.get('stage', 'Lead')
            stage_info = self.get_stage_info(stage_name)
            
            # Create opportunity record
            opportunity = {
                'opportunity_id': opportunity_id,
                'name': opportunity_data['name'],
                'company_id': opportunity_data['company_id'],
                'contact_id': opportunity_data.get('contact_id'),
                'owner_id': opportunity_data['owner_id'],
                'stage': stage_name,
                'amount': opportunity_data.get('amount', 0),
                'probability': opportunity_data.get('probability', stage_info['probability']),
                'close_date': opportunity_data['close_date'],
                'description': opportunity_data.get('description'),
                'lead_source': opportunity_data.get('lead_source'),
                'campaign_id': opportunity_data.get('campaign_id'),
                'territory_id': opportunity_data.get('territory_id'),
                'opportunity_type': opportunity_data.get('opportunity_type', OpportunityType.NEW_BUSINESS.value),
                'priority': opportunity_data.get('priority', OpportunityPriority.MEDIUM.value),
                'tags': opportunity_data.get('tags', []),
                'custom_fields': opportunity_data.get('custom_fields', {}),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Save opportunity
            success = self.db.save_opportunity(opportunity)
            if not success:
                raise Exception("Failed to save opportunity")
                
            # Create initial activity
            self.create_opportunity_activity(opportunity_id, {
                'activity_type': 'opportunity_created',
                'subject': 'Opportunity Created',
                'description': f'Opportunity "{opportunity["name"]}" was created',
                'owner_id': opportunity['owner_id']
            })
            
            # Update contact conversion status if applicable
            if opportunity.get('contact_id'):
                self.update_contact_conversion_status(opportunity['contact_id'])
                
            return {
                'success': True,
                'opportunity_id': opportunity_id,
                'opportunity': opportunity,
                'message': 'Opportunity created successfully'
            }
            
        except Exception as e:
            raise Exception(f"Error creating opportunity: {e}")
            
    def update_opportunity(self, opportunity_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update opportunity"""
        try:
            # Get existing opportunity
            existing_opportunity = self.db.get_opportunity(opportunity_id)
            if not existing_opportunity:
                raise ValueError("Opportunity not found")
                
            # Handle stage changes
            if 'stage' in update_data:
                stage_change_result = self.handle_stage_change(
                    opportunity_id, 
                    existing_opportunity['stage'], 
                    update_data['stage'],
                    update_data
                )
                
                if not stage_change_result['success']:
                    raise ValueError(stage_change_result['error'])
                    
            # Add update timestamp
            update_data['updated_at'] = datetime.now().isoformat()
            
            # Update opportunity
            success = self.db.update_opportunity(opportunity_id, update_data)
            if not success:
                raise Exception("Failed to update opportunity")
                
            # Create update activity
            self.create_opportunity_activity(opportunity_id, {
                'activity_type': 'opportunity_updated',
                'subject': 'Opportunity Updated',
                'description': f'Opportunity updated: {", ".join(update_data.keys())}',
                'owner_id': update_data.get('owner_id') or existing_opportunity.get('owner_id')
            })
            
            return {
                'success': True,
                'opportunity_id': opportunity_id,
                'updated_fields': list(update_data.keys()),
                'message': 'Opportunity updated successfully'
            }
            
        except Exception as e:
            raise Exception(f"Error updating opportunity: {e}")
            
    def update_opportunity_stage(self, opportunity_id: str, stage_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update opportunity stage with validation"""
        try:
            opportunity = self.db.get_opportunity(opportunity_id)
            if not opportunity:
                raise ValueError("Opportunity not found")
                
            new_stage = stage_data['stage']
            current_stage = opportunity['stage']
            
            # Validate stage transition
            if not self.is_valid_stage_transition(current_stage, new_stage):
                raise ValueError(f"Invalid stage transition from {current_stage} to {new_stage}")
                
            # Get stage info
            stage_info = self.get_stage_info(new_stage)
            
            # Prepare update data
            updates = {
                'stage': new_stage,
                'probability': stage_data.get('probability', stage_info['probability']),
                'updated_at': datetime.now().isoformat()
            }
            
            # Handle closed stages
            if stage_info['is_closed']:
                updates['closed_at'] = datetime.now().isoformat()
                
                if self.require_close_reason:
                    if not stage_data.get('close_reason'):
                        raise ValueError("Close reason is required for closed opportunities")
                    updates['close_reason'] = stage_data['close_reason']
                    
            # Update opportunity
            success = self.db.update_opportunity(opportunity_id, updates)
            if not success:
                raise Exception("Failed to update opportunity stage")
                
            # Create stage change activity
            self.create_opportunity_activity(opportunity_id, {
                'activity_type': 'stage_changed',
                'subject': f'Stage Changed: {current_stage} → {new_stage}',
                'description': f'Opportunity stage changed from {current_stage} to {new_stage}',
                'owner_id': opportunity.get('owner_id'),
                'outcome': stage_data.get('close_reason') if stage_info['is_closed'] else None
            })
            
            # Update contact status if won
            if stage_info['is_won'] and opportunity.get('contact_id'):
                self.db.update_contact(opportunity['contact_id'], {
                    'contact_status': 'converted',
                    'updated_at': datetime.now().isoformat()
                })
                
            return {
                'success': True,
                'opportunity_id': opportunity_id,
                'old_stage': current_stage,
                'new_stage': new_stage,
                'probability': updates['probability'],
                'is_closed': stage_info['is_closed'],
                'is_won': stage_info['is_won'],
                'message': f'Opportunity stage updated to {new_stage}'
            }
            
        except Exception as e:
            raise Exception(f"Error updating opportunity stage: {e}")
            
    def list_opportunities(self, filters: Dict[str, Any] = None, page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """List opportunities with filtering and pagination"""
        try:
            if filters is None:
                filters = {}
                
            # Build WHERE clause
            where_clauses = []
            params = []
            
            for key, value in filters.items():
                if key in ['owner_id', 'stage', 'company_id', 'territory_id', 'opportunity_type']:
                    where_clauses.append(f"{key} = ?")
                    params.append(value)
                elif key == 'amount_min':
                    where_clauses.append("amount >= ?")
                    params.append(value)
                elif key == 'amount_max':
                    where_clauses.append("amount <= ?")
                    params.append(value)
                elif key == 'close_date_start':
                    where_clauses.append("close_date >= ?")
                    params.append(value)
                elif key == 'close_date_end':
                    where_clauses.append("close_date <= ?")
                    params.append(value)
                elif key == 'search':
                    where_clauses.append("(name LIKE ? OR description LIKE ?)")
                    search_term = f"%{value}%"
                    params.extend([search_term, search_term])
                    
            where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            
            # Add pagination
            offset = (page - 1) * limit
            params.extend([limit, offset])
            
            query = f"""
                SELECT * FROM opportunities 
                {where_clause} 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            """
            
            opportunities = self.db.execute_query(query, tuple(params))
            
            # Enrich opportunities
            enriched_opportunities = []
            for opportunity in opportunities:
                enriched_opportunity = self.enrich_opportunity_data(opportunity)
                enriched_opportunities.append(enriched_opportunity)
                
            # Get total count
            count_query = f"SELECT COUNT(*) as count FROM opportunities {where_clause}"
            total_count = self.db.execute_single_query(count_query, tuple(params[:-2]))['count']
            total_pages = (total_count + limit - 1) // limit
            
            return {
                'opportunities': enriched_opportunities,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total_count': total_count,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_prev': page > 1
                },
                'filters_applied': filters
            }
            
        except Exception as e:
            raise Exception(f"Error listing opportunities: {e}")
            
    def get_opportunity_analytics(self, analytics_params: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive opportunity analytics"""
        try:
            start_date = analytics_params.get('start_date', (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d'))
            end_date = analytics_params.get('end_date', datetime.now().strftime('%Y-%m-%d'))
            owner_id = analytics_params.get('owner_id')
            territory_id = analytics_params.get('territory_id')
            
            # Build filter conditions
            date_filter = "created_at BETWEEN ? AND ?"
            params = [start_date, end_date]
            additional_filters = []
            
            if owner_id:
                additional_filters.append("owner_id = ?")
                params.append(owner_id)
                
            if territory_id:
                additional_filters.append("territory_id = ?")
                params.append(territory_id)
                
            filter_clause = date_filter
            if additional_filters:
                filter_clause += " AND " + " AND ".join(additional_filters)
                
            # Total opportunities and value
            totals = self.db.execute_single_query(f"""
                SELECT 
                    COUNT(*) as total_count,
                    SUM(amount) as total_value,
                    AVG(amount) as avg_value
                FROM opportunities 
                WHERE {filter_clause}
            """, tuple(params))
            
            # Opportunities by stage
            stage_distribution = self.db.execute_query(f"""
                SELECT 
                    stage,
                    COUNT(*) as count,
                    SUM(amount) as total_value,
                    AVG(probability) as avg_probability
                FROM opportunities 
                WHERE {filter_clause}
                GROUP BY stage
                ORDER BY stage
            """, tuple(params))
            
            # Win/loss analysis
            closed_analysis = self.db.execute_single_query(f"""
                SELECT 
                    SUM(CASE WHEN stage = 'closed_won' THEN 1 ELSE 0 END) as won_count,
                    SUM(CASE WHEN stage = 'closed_lost' THEN 1 ELSE 0 END) as lost_count,
                    SUM(CASE WHEN stage = 'closed_won' THEN amount ELSE 0 END) as won_value,
                    SUM(CASE WHEN stage = 'closed_lost' THEN amount ELSE 0 END) as lost_value
                FROM opportunities 
                WHERE {filter_clause} AND closed_at IS NOT NULL
            """, tuple(params))
            
            # Calculate win rate
            won_count = closed_analysis['won_count'] if closed_analysis else 0
            lost_count = closed_analysis['lost_count'] if closed_analysis else 0
            total_closed = won_count + lost_count
            win_rate = (won_count / total_closed * 100) if total_closed > 0 else 0
            
            # Sales velocity (average days to close won deals)
            velocity_data = self.db.execute_query(f"""
                SELECT 
                    julianday(closed_at) - julianday(created_at) as days_to_close
                FROM opportunities 
                WHERE {filter_clause} AND stage = 'closed_won' AND closed_at IS NOT NULL
            """, tuple(params))
            
            avg_days_to_close = sum(row['days_to_close'] for row in velocity_data) / len(velocity_data) if velocity_data else 0
            
            # Top performers
            top_performers = self.db.execute_query(f"""
                SELECT 
                    owner_id,
                    COUNT(*) as opportunity_count,
                    SUM(amount) as total_value,
                    SUM(CASE WHEN stage = 'closed_won' THEN 1 ELSE 0 END) as won_count
                FROM opportunities 
                WHERE {filter_clause}
                GROUP BY owner_id
                ORDER BY total_value DESC
                LIMIT 10
            """, tuple(params))
            
            # Enrich performer data with names
            for performer in top_performers:
                user = self.db.get_record('users', 'user_id', performer['owner_id'])
                if user:
                    performer['owner_name'] = f"{user['first_name']} {user['last_name']}"
                    
            return {
                'period': {'start_date': start_date, 'end_date': end_date},
                'overview': {
                    'total_opportunities': totals['total_count'] if totals else 0,
                    'total_pipeline_value': totals['total_value'] if totals else 0,
                    'average_deal_size': totals['avg_value'] if totals else 0,
                    'win_rate_percentage': round(win_rate, 2),
                    'average_days_to_close': round(avg_days_to_close, 1)
                },
                'stage_distribution': stage_distribution,
                'win_loss_analysis': {
                    'won_count': won_count,
                    'lost_count': lost_count,
                    'won_value': closed_analysis['won_value'] if closed_analysis else 0,
                    'lost_value': closed_analysis['lost_value'] if closed_analysis else 0
                },
                'top_performers': top_performers
            }
            
        except Exception as e:
            raise Exception(f"Error getting opportunity analytics: {e}")
            
    def get_opportunity_summary(self) -> Dict[str, Any]:
        """Get opportunity summary for dashboard"""
        try:
            # Current pipeline value
            pipeline_value = self.db.execute_single_query("""
                SELECT SUM(amount) as total_value 
                FROM opportunities 
                WHERE stage NOT IN ('closed_won', 'closed_lost')
            """)
            
            # Weighted pipeline value
            weighted_value = self.db.execute_single_query("""
                SELECT SUM(amount * probability / 100) as weighted_value 
                FROM opportunities 
                WHERE stage NOT IN ('closed_won', 'closed_lost')
            """)
            
            # Opportunities closing this month
            this_month_start = datetime.now().replace(day=1).strftime('%Y-%m-%d')
            next_month_start = (datetime.now().replace(day=1) + timedelta(days=32)).replace(day=1).strftime('%Y-%m-%d')
            
            closing_this_month = self.db.execute_single_query("""
                SELECT COUNT(*) as count, SUM(amount) as value
                FROM opportunities 
                WHERE close_date >= ? AND close_date < ? 
                AND stage NOT IN ('closed_won', 'closed_lost')
            """, (this_month_start, next_month_start))
            
            # Overdue opportunities
            today = datetime.now().strftime('%Y-%m-%d')
            overdue = self.db.execute_single_query("""
                SELECT COUNT(*) as count
                FROM opportunities 
                WHERE close_date < ? AND stage NOT IN ('closed_won', 'closed_lost')
            """, (today,))
            
            return {
                'pipeline_value': pipeline_value['total_value'] if pipeline_value else 0,
                'weighted_pipeline_value': weighted_value['weighted_value'] if weighted_value else 0,
                'closing_this_month': {
                    'count': closing_this_month['count'] if closing_this_month else 0,
                    'value': closing_this_month['value'] if closing_this_month else 0
                },
                'overdue_count': overdue['count'] if overdue else 0
            }
            
        except Exception as e:
            raise Exception(f"Error getting opportunity summary: {e}")
            
    def get_sales_performance_report(self, report_params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate sales performance report"""
        try:
            start_date = report_params.get('start_date', (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d'))
            end_date = report_params.get('end_date', datetime.now().strftime('%Y-%m-%d'))
            
            # Revenue by month
            monthly_revenue = self.db.execute_query("""
                SELECT 
                    strftime('%Y-%m', closed_at) as month,
                    SUM(amount) as revenue,
                    COUNT(*) as deals_won
                FROM opportunities 
                WHERE stage = 'closed_won' 
                AND closed_at BETWEEN ? AND ?
                GROUP BY strftime('%Y-%m', closed_at)
                ORDER BY month
            """, (start_date, end_date))
            
            # Performance by sales rep
            rep_performance = self.db.execute_query("""
                SELECT 
                    o.owner_id,
                    u.first_name || ' ' || u.last_name as rep_name,
                    COUNT(*) as total_opportunities,
                    SUM(CASE WHEN o.stage = 'closed_won' THEN 1 ELSE 0 END) as won_deals,
                    SUM(CASE WHEN o.stage = 'closed_won' THEN o.amount ELSE 0 END) as revenue,
                    AVG(CASE WHEN o.stage = 'closed_won' THEN 
                        julianday(o.closed_at) - julianday(o.created_at) ELSE NULL END) as avg_sales_cycle
                FROM opportunities o
                LEFT JOIN users u ON o.owner_id = u.user_id
                WHERE o.created_at BETWEEN ? AND ?
                GROUP BY o.owner_id, u.first_name, u.last_name
                ORDER BY revenue DESC
            """, (start_date, end_date))
            
            # Add win rate calculation
            for rep in rep_performance:
                rep['win_rate'] = (rep['won_deals'] / rep['total_opportunities'] * 100) if rep['total_opportunities'] > 0 else 0
                
            return {
                'period': {'start_date': start_date, 'end_date': end_date},
                'monthly_revenue': monthly_revenue,
                'rep_performance': rep_performance,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Error generating sales performance report: {e}")
            
    def create_opportunity_activity(self, opportunity_id: str, activity_data: Dict[str, Any]) -> str:
        """Create opportunity-related activity"""
        try:
            activity_id = f"activity_{datetime.now().timestamp()}"
            
            activity = {
                'activity_id': activity_id,
                'activity_type': activity_data['activity_type'],
                'subject': activity_data['subject'],
                'description': activity_data.get('description', ''),
                'opportunity_id': opportunity_id,
                'contact_id': activity_data.get('contact_id'),
                'company_id': activity_data.get('company_id'),
                'owner_id': activity_data.get('owner_id'),
                'status': activity_data.get('status', 'completed'),
                'priority': activity_data.get('priority', 'medium'),
                'due_date': activity_data.get('due_date'),
                'completed_at': activity_data.get('completed_at', datetime.now().isoformat()),
                'duration_minutes': activity_data.get('duration_minutes'),
                'outcome': activity_data.get('outcome'),
                'follow_up_required': activity_data.get('follow_up_required', False),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            success = self.db.save_activity(activity)
            if success:
                return activity_id
            else:
                raise Exception("Failed to save activity")
                
        except Exception as e:
            raise Exception(f"Error creating opportunity activity: {e}")
            
    def enrich_opportunity_data(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich opportunity data for display"""
        try:
            enriched = opportunity.copy()
            
            # Add company information
            if opportunity.get('company_id'):
                company = self.db.get_company(opportunity['company_id'])
                if company:
                    enriched['company_name'] = company['name']
                    enriched['company_industry'] = company.get('industry')
                    
            # Add contact information
            if opportunity.get('contact_id'):
                contact = self.db.get_contact(opportunity['contact_id'])
                if contact:
                    enriched['contact_name'] = f"{contact['first_name']} {contact['last_name']}"
                    enriched['contact_email'] = contact.get('email')
                    
            # Add owner information
            if opportunity.get('owner_id'):
                owner = self.db.get_record('users', 'user_id', opportunity['owner_id'])
                if owner:
                    enriched['owner_name'] = f"{owner['first_name']} {owner['last_name']}"
                    
            # Add stage information
            stage_info = self.get_stage_info(opportunity['stage'])
            enriched['stage_probability'] = stage_info['probability']
            enriched['is_closed'] = stage_info['is_closed']
            enriched['is_won'] = stage_info['is_won']
            
            # Add weighted value
            enriched['weighted_value'] = opportunity.get('amount', 0) * (opportunity.get('probability', 0) / 100)
            
            # Add time-based information
            if opportunity.get('close_date'):
                close_date = datetime.fromisoformat(opportunity['close_date'])
                today = datetime.now()
                days_to_close = (close_date - today).days
                enriched['days_to_close'] = days_to_close
                enriched['is_overdue'] = days_to_close < 0 and not stage_info['is_closed']
                
            if opportunity.get('created_at'):
                created_date = datetime.fromisoformat(opportunity['created_at'])
                age_days = (datetime.now() - created_date).days
                enriched['age_days'] = age_days
                enriched['is_stale'] = age_days > self.opportunity_aging_days
                
            return enriched
            
        except Exception:
            return opportunity
            
    def get_stage_info(self, stage_name: str) -> Dict[str, Any]:
        """Get stage information"""
        try:
            stage = self.db.execute_single_query(
                "SELECT * FROM pipeline_stages WHERE name = ?",
                (stage_name,)
            )
            
            if stage:
                return {
                    'probability': stage['probability'],
                    'order': stage['stage_order'],
                    'is_closed': stage['is_closed'],
                    'is_won': stage['is_won']
                }
            else:
                # Return default for unknown stage
                return {
                    'probability': self.default_probability,
                    'order': 99,
                    'is_closed': False,
                    'is_won': False
                }
                
        except Exception:
            return {
                'probability': self.default_probability,
                'order': 99,
                'is_closed': False,
                'is_won': False
            }
            
    def is_valid_stage_transition(self, current_stage: str, new_stage: str) -> bool:
        """Validate stage transition"""
        try:
            # Get stage order information
            current_info = self.get_stage_info(current_stage)
            new_info = self.get_stage_info(new_stage)
            
            # Allow transitions to any stage if auto progression is disabled
            if not self.auto_stage_progression:
                return True
                
            # Don't allow reopening closed opportunities
            if current_info['is_closed'] and not new_info['is_closed']:
                return False
                
            # Allow any other transition
            return True
            
        except Exception:
            return True  # Allow transition if validation fails
            
    def handle_stage_change(self, opportunity_id: str, current_stage: str, new_stage: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle stage change with business logic"""
        try:
            stage_info = self.get_stage_info(new_stage)
            
            # Update probability if not explicitly provided
            if 'probability' not in update_data:
                update_data['probability'] = stage_info['probability']
                
            # Handle closed stages
            if stage_info['is_closed']:
                update_data['closed_at'] = datetime.now().isoformat()
                
                if self.require_close_reason and not update_data.get('close_reason'):
                    return {
                        'success': False,
                        'error': 'Close reason is required for closed opportunities'
                    }
                    
            return {'success': True}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    def update_contact_conversion_status(self, contact_id: str):
        """Update contact status based on opportunity"""
        try:
            # Check if contact has any won opportunities
            won_opportunities = self.db.execute_query(
                "SELECT COUNT(*) as count FROM opportunities WHERE contact_id = ? AND stage = 'closed_won'",
                (contact_id,)
            )
            
            if won_opportunities and won_opportunities[0]['count'] > 0:
                self.db.update_contact(contact_id, {
                    'contact_status': 'converted',
                    'updated_at': datetime.now().isoformat()
                })
            else:
                # Check if contact has any active opportunities
                active_opportunities = self.db.execute_query(
                    "SELECT COUNT(*) as count FROM opportunities WHERE contact_id = ? AND stage NOT IN ('closed_won', 'closed_lost')",
                    (contact_id,)
                )
                
                if active_opportunities and active_opportunities[0]['count'] > 0:
                    self.db.update_contact(contact_id, {
                        'contact_status': 'qualified',
                        'updated_at': datetime.now().isoformat()
                    })
                    
        except Exception as e:
            print(f"Error updating contact conversion status: {e}")
            
    def cleanup_stale_opportunities(self) -> Dict[str, Any]:
        """Cleanup stale opportunities"""
        try:
            if not self.auto_close_stale_opportunities:
                return {'cleaned_up': 0, 'message': 'Auto cleanup disabled'}
                
            cutoff_date = (datetime.now() - timedelta(days=self.opportunity_aging_days)).strftime('%Y-%m-%d')
            
            # Find stale opportunities
            stale_opportunities = self.db.execute_query("""
                SELECT opportunity_id FROM opportunities 
                WHERE created_at < ? 
                AND stage NOT IN ('closed_won', 'closed_lost')
                AND close_date < ?
            """, (cutoff_date, datetime.now().strftime('%Y-%m-%d')))
            
            cleaned_count = 0
            for opportunity in stale_opportunities:
                # Close as lost with reason
                self.db.update_opportunity(opportunity['opportunity_id'], {
                    'stage': 'closed_lost',
                    'closed_at': datetime.now().isoformat(),
                    'close_reason': 'Auto-closed due to inactivity',
                    'updated_at': datetime.now().isoformat()
                })
                cleaned_count += 1
                
            return {
                'cleaned_up': cleaned_count,
                'message': f'Auto-closed {cleaned_count} stale opportunities'
            }
            
        except Exception as e:
            raise Exception(f"Error cleaning up stale opportunities: {e}")