"""
Commission Tracking System
Sales commission calculation, tracking, and reporting
"""

import sqlite3
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
import uuid
from decimal import Decimal, ROUND_HALF_UP


class CommissionType(Enum):
    """Commission calculation types"""
    FLAT_RATE = "flat_rate"
    PERCENTAGE = "percentage"
    TIERED = "tiered"
    SLIDING_SCALE = "sliding_scale"
    BONUS = "bonus"
    DRAW_AGAINST = "draw_against"


class CommissionStatus(Enum):
    """Commission record status"""
    PENDING = "pending"
    APPROVED = "approved"
    PAID = "paid"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"
    CLAWBACK = "clawback"


class PaymentSchedule(Enum):
    """Commission payment schedules"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUAL = "semi_annual"
    ANNUAL = "annual"
    PER_DEAL = "per_deal"


@dataclass
class CommissionRule:
    """Commission rule configuration"""
    rule_id: str
    name: str
    commission_type: CommissionType
    rate: float
    conditions: Dict[str, Any]
    effective_date: datetime
    expiry_date: Optional[datetime]


@dataclass
class CommissionRecord:
    """Commission calculation record"""
    commission_id: str
    user_id: str
    opportunity_id: str
    rule_id: str
    commission_amount: Decimal
    base_amount: Decimal
    commission_rate: float
    status: CommissionStatus
    earned_date: datetime
    payment_date: Optional[datetime]


class CommissionTrackingSystem:
    """Commission tracking and calculation system"""
    
    def __init__(self, db_path: str = "data/crm_sales.db"):
        self.db_path = db_path
        
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
        
    def create_commission_rule(self, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new commission rule"""
        
        rule_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert commission rule
            cursor.execute("""
                INSERT INTO commission_rules (
                    rule_id, name, commission_type, rate, conditions,
                    effective_date, expiry_date, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                rule_id,
                rule_data['name'],
                rule_data['commission_type'],
                rule_data['rate'],
                json.dumps(rule_data.get('conditions', {})),
                rule_data.get('effective_date', datetime.utcnow().isoformat()),
                rule_data.get('expiry_date'),
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ])
            
            conn.commit()
            
            # Log activity
            self._log_activity('commission_rule_created', f"Commission rule '{rule_data['name']}' created", {
                'rule_id': rule_id,
                'commission_type': rule_data['commission_type'],
                'rate': rule_data['rate']
            })
            
            return {
                'rule_id': rule_id,
                'name': rule_data['name'],
                'commission_type': rule_data['commission_type'],
                'rate': rule_data['rate'],
                'created_at': datetime.utcnow().isoformat()
            }
    
    def get_commission_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Get commission rule by ID"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM commission_rules 
                WHERE rule_id = ?
            """, [rule_id])
            
            result = cursor.fetchone()
            if result:
                return {
                    'rule_id': result['rule_id'],
                    'name': result['name'],
                    'commission_type': result['commission_type'],
                    'rate': result['rate'],
                    'conditions': json.loads(result['conditions']) if result['conditions'] else {},
                    'effective_date': result['effective_date'],
                    'expiry_date': result['expiry_date'],
                    'created_at': result['created_at'],
                    'updated_at': result['updated_at']
                }
            return None
    
    def list_commission_rules(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """List commission rules"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM commission_rules"
            params = []
            
            if active_only:
                now = datetime.utcnow().isoformat()
                query += " WHERE effective_date <= ? AND (expiry_date IS NULL OR expiry_date > ?)"
                params.extend([now, now])
                
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            rules = []
            for result in results:
                rules.append({
                    'rule_id': result['rule_id'],
                    'name': result['name'],
                    'commission_type': result['commission_type'],
                    'rate': result['rate'],
                    'conditions': json.loads(result['conditions']) if result['conditions'] else {},
                    'effective_date': result['effective_date'],
                    'expiry_date': result['expiry_date'],
                    'created_at': result['created_at']
                })
                
            return rules
    
    def calculate_commission(self, opportunity_id: str) -> Dict[str, Any]:
        """Calculate commission for an opportunity"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get opportunity details
            cursor.execute("""
                SELECT o.*, c.assigned_to, c.territory_id
                FROM opportunities o
                JOIN contacts c ON o.contact_id = c.contact_id
                WHERE o.opportunity_id = ? AND o.status = 'won'
            """, [opportunity_id])
            
            opportunity = cursor.fetchone()
            if not opportunity:
                raise ValueError("Opportunity not found or not won")
            
            # Find applicable commission rules
            applicable_rules = self._find_applicable_rules(cursor, opportunity)
            
            if not applicable_rules:
                return {
                    'opportunity_id': opportunity_id,
                    'commission_amount': 0,
                    'message': 'No applicable commission rules found'
                }
            
            # Calculate commission based on rules
            total_commission = Decimal('0')
            commission_details = []
            
            for rule in applicable_rules:
                commission_amount = self._calculate_rule_commission(
                    rule, Decimal(str(opportunity['value']))
                )
                
                total_commission += commission_amount
                commission_details.append({
                    'rule_id': rule['rule_id'],
                    'rule_name': rule['name'],
                    'commission_type': rule['commission_type'],
                    'rate': rule['rate'],
                    'commission_amount': float(commission_amount),
                    'base_amount': float(opportunity['value'])
                })
            
            return {
                'opportunity_id': opportunity_id,
                'user_id': opportunity['assigned_to'],
                'total_commission': float(total_commission),
                'commission_details': commission_details,
                'opportunity_value': float(opportunity['value']),
                'calculated_at': datetime.utcnow().isoformat()
            }
    
    def record_commission(self, commission_data: Dict[str, Any]) -> Dict[str, Any]:
        """Record a commission calculation"""
        
        commission_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if commission already exists for this opportunity
            cursor.execute("""
                SELECT commission_id FROM commissions 
                WHERE opportunity_id = ? AND user_id = ?
            """, [commission_data['opportunity_id'], commission_data['user_id']])
            
            if cursor.fetchone():
                raise ValueError("Commission already recorded for this opportunity and user")
            
            # Insert commission record
            cursor.execute("""
                INSERT INTO commissions (
                    commission_id, user_id, opportunity_id, rule_id,
                    commission_amount, base_amount, commission_rate,
                    status, earned_date, metadata, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                commission_id,
                commission_data['user_id'],
                commission_data['opportunity_id'],
                commission_data.get('rule_id'),
                commission_data['commission_amount'],
                commission_data['base_amount'],
                commission_data.get('commission_rate', 0),
                CommissionStatus.PENDING.value,
                commission_data.get('earned_date', datetime.utcnow().isoformat()),
                json.dumps(commission_data.get('metadata', {})),
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ])
            
            conn.commit()
            
            # Log activity
            self._log_activity('commission_recorded', f"Commission recorded for user {commission_data['user_id']}", {
                'commission_id': commission_id,
                'opportunity_id': commission_data['opportunity_id'],
                'commission_amount': commission_data['commission_amount']
            })
            
            return {
                'commission_id': commission_id,
                'status': CommissionStatus.PENDING.value,
                'commission_amount': commission_data['commission_amount'],
                'created_at': datetime.utcnow().isoformat()
            }
    
    def approve_commission(self, commission_id: str, approved_by: str) -> Dict[str, Any]:
        """Approve a commission for payment"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE commissions 
                SET status = ?, approved_by = ?, approved_at = ?, updated_at = ?
                WHERE commission_id = ? AND status = ?
            """, [
                CommissionStatus.APPROVED.value,
                approved_by,
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat(),
                commission_id,
                CommissionStatus.PENDING.value
            ])
            
            if cursor.rowcount == 0:
                raise ValueError("Commission not found or already processed")
            
            conn.commit()
            
            return {
                'commission_id': commission_id,
                'status': CommissionStatus.APPROVED.value,
                'approved_by': approved_by,
                'approved_at': datetime.utcnow().isoformat()
            }
    
    def mark_commission_paid(self, commission_id: str, payment_reference: str = None) -> Dict[str, Any]:
        """Mark commission as paid"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE commissions 
                SET status = ?, payment_date = ?, payment_reference = ?, updated_at = ?
                WHERE commission_id = ? AND status = ?
            """, [
                CommissionStatus.PAID.value,
                datetime.utcnow().isoformat(),
                payment_reference,
                datetime.utcnow().isoformat(),
                commission_id,
                CommissionStatus.APPROVED.value
            ])
            
            if cursor.rowcount == 0:
                raise ValueError("Commission not found or not approved")
            
            conn.commit()
            
            return {
                'commission_id': commission_id,
                'status': CommissionStatus.PAID.value,
                'payment_date': datetime.utcnow().isoformat(),
                'payment_reference': payment_reference
            }
    
    def get_user_commissions(self, user_id: str, period_start: Optional[str] = None,
                           period_end: Optional[str] = None, status: Optional[str] = None) -> Dict[str, Any]:
        """Get commissions for a specific user"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Build query
            query = """
                SELECT c.*, o.value as opportunity_value, o.name as opportunity_name,
                       cont.company, cont.first_name, cont.last_name
                FROM commissions c
                JOIN opportunities o ON c.opportunity_id = o.opportunity_id
                JOIN contacts cont ON o.contact_id = cont.contact_id
                WHERE c.user_id = ?
            """
            params = [user_id]
            
            if period_start:
                query += " AND c.earned_date >= ?"
                params.append(period_start)
            if period_end:
                query += " AND c.earned_date <= ?"
                params.append(period_end)
            if status:
                query += " AND c.status = ?"
                params.append(status)
                
            query += " ORDER BY c.earned_date DESC"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            # Calculate summary statistics
            total_earned = sum(float(r['commission_amount']) for r in results)
            paid_commissions = [r for r in results if r['status'] == CommissionStatus.PAID.value]
            pending_commissions = [r for r in results if r['status'] == CommissionStatus.PENDING.value]
            
            commissions = []
            for result in results:
                commissions.append({
                    'commission_id': result['commission_id'],
                    'opportunity_id': result['opportunity_id'],
                    'opportunity_name': result['opportunity_name'],
                    'company': result['company'],
                    'contact_name': f"{result['first_name']} {result['last_name']}".strip(),
                    'commission_amount': float(result['commission_amount']),
                    'base_amount': float(result['base_amount']),
                    'commission_rate': result['commission_rate'],
                    'status': result['status'],
                    'earned_date': result['earned_date'],
                    'payment_date': result['payment_date'],
                    'approved_at': result['approved_at']
                })
            
            return {
                'user_id': user_id,
                'period_start': period_start,
                'period_end': period_end,
                'summary': {
                    'total_commissions': len(results),
                    'total_earned': total_earned,
                    'total_paid': sum(float(r['commission_amount']) for r in paid_commissions),
                    'total_pending': sum(float(r['commission_amount']) for r in pending_commissions),
                    'paid_count': len(paid_commissions),
                    'pending_count': len(pending_commissions)
                },
                'commissions': commissions
            }
    
    def get_commission_report(self, period_start: str, period_end: str,
                            user_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate commission report"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Build base query
            where_clause = "WHERE c.earned_date BETWEEN ? AND ?"
            params = [period_start, period_end]
            
            if user_id:
                where_clause += " AND c.user_id = ?"
                params.append(user_id)
            
            # Get commission summary
            cursor.execute(f"""
                SELECT 
                    c.user_id,
                    COUNT(*) as total_commissions,
                    SUM(c.commission_amount) as total_amount,
                    SUM(CASE WHEN c.status = 'paid' THEN c.commission_amount ELSE 0 END) as paid_amount,
                    SUM(CASE WHEN c.status = 'pending' THEN c.commission_amount ELSE 0 END) as pending_amount,
                    AVG(c.commission_amount) as avg_commission
                FROM commissions c
                {where_clause}
                GROUP BY c.user_id
                ORDER BY total_amount DESC
            """, params)
            
            user_summaries = []
            for result in cursor.fetchall():
                user_summaries.append({
                    'user_id': result['user_id'],
                    'total_commissions': result['total_commissions'],
                    'total_amount': float(result['total_amount']),
                    'paid_amount': float(result['paid_amount']),
                    'pending_amount': float(result['pending_amount']),
                    'avg_commission': float(result['avg_commission'])
                })
            
            # Get commission by rule type
            cursor.execute(f"""
                SELECT 
                    cr.commission_type,
                    COUNT(c.commission_id) as commission_count,
                    SUM(c.commission_amount) as total_amount
                FROM commissions c
                JOIN commission_rules cr ON c.rule_id = cr.rule_id
                {where_clause}
                GROUP BY cr.commission_type
                ORDER BY total_amount DESC
            """, params)
            
            by_rule_type = []
            for result in cursor.fetchall():
                by_rule_type.append({
                    'commission_type': result['commission_type'],
                    'commission_count': result['commission_count'],
                    'total_amount': float(result['total_amount'])
                })
            
            # Get monthly breakdown
            cursor.execute(f"""
                SELECT 
                    strftime('%Y-%m', c.earned_date) as month,
                    COUNT(*) as commission_count,
                    SUM(c.commission_amount) as total_amount
                FROM commissions c
                {where_clause}
                GROUP BY strftime('%Y-%m', c.earned_date)
                ORDER BY month
            """, params)
            
            monthly_breakdown = []
            for result in cursor.fetchall():
                monthly_breakdown.append({
                    'month': result['month'],
                    'commission_count': result['commission_count'],
                    'total_amount': float(result['total_amount'])
                })
            
            # Calculate overall statistics
            total_amount = sum(user['total_amount'] for user in user_summaries)
            total_paid = sum(user['paid_amount'] for user in user_summaries)
            total_pending = sum(user['pending_amount'] for user in user_summaries)
            
            return {
                'period_start': period_start,
                'period_end': period_end,
                'overall_summary': {
                    'total_amount': total_amount,
                    'paid_amount': total_paid,
                    'pending_amount': total_pending,
                    'total_users': len(user_summaries),
                    'total_commissions': sum(user['total_commissions'] for user in user_summaries)
                },
                'user_summaries': user_summaries,
                'by_rule_type': by_rule_type,
                'monthly_breakdown': monthly_breakdown,
                'generated_at': datetime.utcnow().isoformat()
            }
    
    def process_clawback(self, opportunity_id: str, reason: str) -> Dict[str, Any]:
        """Process commission clawback for cancelled/refunded deal"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Find existing commission
            cursor.execute("""
                SELECT * FROM commissions 
                WHERE opportunity_id = ? AND status IN ('paid', 'approved')
            """, [opportunity_id])
            
            commissions = cursor.fetchall()
            if not commissions:
                raise ValueError("No paid/approved commissions found for this opportunity")
            
            clawback_records = []
            
            for commission in commissions:
                # Create clawback record
                clawback_id = str(uuid.uuid4())
                
                cursor.execute("""
                    INSERT INTO commission_clawbacks (
                        clawback_id, original_commission_id, user_id,
                        clawback_amount, reason, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, [
                    clawback_id,
                    commission['commission_id'],
                    commission['user_id'],
                    commission['commission_amount'],
                    reason,
                    datetime.utcnow().isoformat()
                ])
                
                # Update original commission status
                cursor.execute("""
                    UPDATE commissions 
                    SET status = ?, clawback_reason = ?, updated_at = ?
                    WHERE commission_id = ?
                """, [
                    CommissionStatus.CLAWBACK.value,
                    reason,
                    datetime.utcnow().isoformat(),
                    commission['commission_id']
                ])
                
                clawback_records.append({
                    'clawback_id': clawback_id,
                    'commission_id': commission['commission_id'],
                    'user_id': commission['user_id'],
                    'clawback_amount': float(commission['commission_amount'])
                })
            
            conn.commit()
            
            # Log activity
            self._log_activity('commission_clawback', f"Commission clawback processed for opportunity {opportunity_id}", {
                'opportunity_id': opportunity_id,
                'reason': reason,
                'clawback_count': len(clawback_records)
            })
            
            return {
                'opportunity_id': opportunity_id,
                'clawback_records': clawback_records,
                'reason': reason,
                'processed_at': datetime.utcnow().isoformat()
            }
    
    def calculate_team_commissions(self, opportunity_id: str, 
                                 team_split: Dict[str, float]) -> Dict[str, Any]:
        """Calculate and distribute team commissions"""
        
        # Validate split percentages
        total_percentage = sum(team_split.values())
        if abs(total_percentage - 100) > 0.01:  # Allow for small floating point errors
            raise ValueError("Team split percentages must total 100%")
        
        # Get base commission calculation
        base_calculation = self.calculate_commission(opportunity_id)
        if base_calculation.get('total_commission', 0) == 0:
            return {'message': 'No commission to split', 'team_commissions': []}
        
        total_commission = Decimal(str(base_calculation['total_commission']))
        team_commissions = []
        
        for user_id, percentage in team_split.items():
            user_commission = total_commission * Decimal(str(percentage)) / Decimal('100')
            
            # Round to 2 decimal places
            user_commission = user_commission.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            team_commissions.append({
                'user_id': user_id,
                'percentage': percentage,
                'commission_amount': float(user_commission),
                'base_amount': float(base_calculation['opportunity_value'])
            })
        
        return {
            'opportunity_id': opportunity_id,
            'total_commission': float(total_commission),
            'team_commissions': team_commissions,
            'calculated_at': datetime.utcnow().isoformat()
        }
    
    def get_commission_analytics(self, period_days: int = 90) -> Dict[str, Any]:
        """Get commission analytics and trends"""
        
        start_date = (datetime.utcnow() - timedelta(days=period_days)).isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Basic statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_commissions,
                    SUM(commission_amount) as total_amount,
                    AVG(commission_amount) as avg_commission,
                    COUNT(DISTINCT user_id) as active_users,
                    COUNT(CASE WHEN status = 'paid' THEN 1 END) as paid_commissions,
                    SUM(CASE WHEN status = 'paid' THEN commission_amount ELSE 0 END) as paid_amount
                FROM commissions
                WHERE earned_date >= ?
            """, [start_date])
            
            basic_stats = cursor.fetchone()
            
            # Top performers
            cursor.execute("""
                SELECT 
                    user_id,
                    COUNT(*) as commission_count,
                    SUM(commission_amount) as total_earned
                FROM commissions
                WHERE earned_date >= ?
                GROUP BY user_id
                ORDER BY total_earned DESC
                LIMIT 10
            """, [start_date])
            
            top_performers = []
            for result in cursor.fetchall():
                top_performers.append({
                    'user_id': result['user_id'],
                    'commission_count': result['commission_count'],
                    'total_earned': float(result['total_earned'])
                })
            
            # Commission trends (weekly)
            cursor.execute("""
                SELECT 
                    strftime('%Y-%W', earned_date) as week,
                    COUNT(*) as commission_count,
                    SUM(commission_amount) as total_amount
                FROM commissions
                WHERE earned_date >= ?
                GROUP BY strftime('%Y-%W', earned_date)
                ORDER BY week
            """, [start_date])
            
            weekly_trends = []
            for result in cursor.fetchall():
                weekly_trends.append({
                    'week': result['week'],
                    'commission_count': result['commission_count'],
                    'total_amount': float(result['total_amount'])
                })
            
            return {
                'period_days': period_days,
                'basic_stats': {
                    'total_commissions': basic_stats['total_commissions'] or 0,
                    'total_amount': float(basic_stats['total_amount'] or 0),
                    'avg_commission': float(basic_stats['avg_commission'] or 0),
                    'active_users': basic_stats['active_users'] or 0,
                    'paid_commissions': basic_stats['paid_commissions'] or 0,
                    'paid_amount': float(basic_stats['paid_amount'] or 0),
                    'payment_rate': (basic_stats['paid_commissions'] / basic_stats['total_commissions'] * 100) 
                                  if basic_stats['total_commissions'] > 0 else 0
                },
                'top_performers': top_performers,
                'weekly_trends': weekly_trends,
                'generated_at': datetime.utcnow().isoformat()
            }
    
    def _find_applicable_rules(self, cursor, opportunity: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find commission rules applicable to an opportunity"""
        
        # Get active rules
        now = datetime.utcnow().isoformat()
        cursor.execute("""
            SELECT * FROM commission_rules
            WHERE effective_date <= ? 
            AND (expiry_date IS NULL OR expiry_date > ?)
            ORDER BY created_at DESC
        """, [now, now])
        
        rules = cursor.fetchall()
        applicable_rules = []
        
        for rule in rules:
            conditions = json.loads(rule['conditions']) if rule['conditions'] else {}
            
            if self._opportunity_matches_conditions(opportunity, conditions):
                applicable_rules.append({
                    'rule_id': rule['rule_id'],
                    'name': rule['name'],
                    'commission_type': rule['commission_type'],
                    'rate': rule['rate'],
                    'conditions': conditions
                })
        
        return applicable_rules
    
    def _opportunity_matches_conditions(self, opportunity: Dict[str, Any], 
                                      conditions: Dict[str, Any]) -> bool:
        """Check if opportunity matches rule conditions"""
        
        if not conditions:
            return True  # No conditions means rule applies to all
        
        for condition, value in conditions.items():
            if condition == 'min_value':
                if opportunity['value'] < value:
                    return False
            elif condition == 'max_value':
                if opportunity['value'] > value:
                    return False
            elif condition == 'territory_id':
                if isinstance(value, list):
                    if opportunity.get('territory_id') not in value:
                        return False
                else:
                    if opportunity.get('territory_id') != value:
                        return False
            elif condition == 'user_id':
                if isinstance(value, list):
                    if opportunity.get('assigned_to') not in value:
                        return False
                else:
                    if opportunity.get('assigned_to') != value:
                        return False
            # Add more condition types as needed
        
        return True
    
    def _calculate_rule_commission(self, rule: Dict[str, Any], 
                                 opportunity_value: Decimal) -> Decimal:
        """Calculate commission based on rule type"""
        
        commission_type = rule['commission_type']
        rate = Decimal(str(rule['rate']))
        
        if commission_type == CommissionType.FLAT_RATE.value:
            return rate
        elif commission_type == CommissionType.PERCENTAGE.value:
            return opportunity_value * (rate / Decimal('100'))
        elif commission_type == CommissionType.TIERED.value:
            return self._calculate_tiered_commission(rule, opportunity_value)
        elif commission_type == CommissionType.SLIDING_SCALE.value:
            return self._calculate_sliding_scale_commission(rule, opportunity_value)
        else:
            # Default to percentage
            return opportunity_value * (rate / Decimal('100'))
    
    def _calculate_tiered_commission(self, rule: Dict[str, Any], 
                                   opportunity_value: Decimal) -> Decimal:
        """Calculate tiered commission"""
        
        conditions = rule.get('conditions', {})
        tiers = conditions.get('tiers', [])
        
        if not tiers:
            # Fallback to regular percentage
            return opportunity_value * (Decimal(str(rule['rate'])) / Decimal('100'))
        
        # Sort tiers by threshold
        tiers = sorted(tiers, key=lambda x: x.get('threshold', 0))
        
        applicable_tier = tiers[0]  # Default to first tier
        
        for tier in tiers:
            if opportunity_value >= Decimal(str(tier.get('threshold', 0))):
                applicable_tier = tier
            else:
                break
        
        tier_rate = Decimal(str(applicable_tier.get('rate', rule['rate'])))
        return opportunity_value * (tier_rate / Decimal('100'))
    
    def _calculate_sliding_scale_commission(self, rule: Dict[str, Any], 
                                          opportunity_value: Decimal) -> Decimal:
        """Calculate sliding scale commission"""
        
        conditions = rule.get('conditions', {})
        min_rate = Decimal(str(conditions.get('min_rate', rule['rate'])))
        max_rate = Decimal(str(conditions.get('max_rate', rule['rate'])))
        min_value = Decimal(str(conditions.get('min_value', 0)))
        max_value = Decimal(str(conditions.get('max_value', 100000)))
        
        # Calculate rate based on opportunity value position in range
        if opportunity_value <= min_value:
            rate = min_rate
        elif opportunity_value >= max_value:
            rate = max_rate
        else:
            # Linear interpolation
            value_ratio = (opportunity_value - min_value) / (max_value - min_value)
            rate = min_rate + (max_rate - min_rate) * value_ratio
        
        return opportunity_value * (rate / Decimal('100'))
    
    def _log_activity(self, activity_type: str, description: str, metadata: Dict[str, Any]):
        """Log commission activity"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO activities (
                    activity_type, description, metadata, created_at
                ) VALUES (?, ?, ?, ?)
            """, [
                activity_type,
                description,
                json.dumps(metadata),
                datetime.utcnow().isoformat()
            ])
            
            conn.commit()