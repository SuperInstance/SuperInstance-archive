"""
Territory Management System
Sales territory assignment, balancing, and performance tracking
"""

import sqlite3
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
import uuid
import statistics
import math


class TerritoryType(Enum):
    """Territory types"""
    GEOGRAPHIC = "geographic"
    ACCOUNT_BASED = "account_based"
    INDUSTRY = "industry"
    PRODUCT = "product"
    CHANNEL = "channel"
    HYBRID = "hybrid"


class AssignmentMethod(Enum):
    """Territory assignment methods"""
    MANUAL = "manual"
    ROUND_ROBIN = "round_robin"
    WORKLOAD_BASED = "workload_based"
    PERFORMANCE_BASED = "performance_based"
    GEOGRAPHIC_PROXIMITY = "geographic_proximity"


class TerritoryStatus(Enum):
    """Territory status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"


@dataclass
class Territory:
    """Territory data structure"""
    territory_id: str
    name: str
    territory_type: TerritoryType
    description: str
    criteria: Dict[str, Any]
    assigned_users: List[str]
    status: TerritoryStatus
    created_at: datetime
    

@dataclass
class TerritoryAssignment:
    """Territory assignment data structure"""
    assignment_id: str
    territory_id: str
    user_id: str
    assigned_at: datetime
    assignment_method: AssignmentMethod


class TerritoryManagementSystem:
    """Territory management and assignment system"""
    
    def __init__(self, db_path: str = "data/crm_sales.db"):
        self.db_path = db_path
        
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
        
    def create_territory(self, territory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new sales territory"""
        
        territory_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert territory
            cursor.execute("""
                INSERT INTO territories (
                    territory_id, name, territory_type, description,
                    criteria, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                territory_id,
                territory_data['name'],
                territory_data['territory_type'],
                territory_data.get('description', ''),
                json.dumps(territory_data.get('criteria', {})),
                TerritoryStatus.DRAFT.value,
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ])
            
            conn.commit()
            
            # Log activity
            self._log_activity('territory_created', f"Territory '{territory_data['name']}' created", {
                'territory_id': territory_id,
                'territory_type': territory_data['territory_type']
            })
            
            return {
                'territory_id': territory_id,
                'name': territory_data['name'],
                'territory_type': territory_data['territory_type'],
                'status': TerritoryStatus.DRAFT.value,
                'created_at': datetime.utcnow().isoformat()
            }
    
    def get_territory(self, territory_id: str) -> Optional[Dict[str, Any]]:
        """Get territory by ID"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM territories 
                WHERE territory_id = ?
            """, [territory_id])
            
            result = cursor.fetchone()
            if result:
                # Get assigned users
                cursor.execute("""
                    SELECT ta.user_id, ta.assigned_at, ta.assignment_method
                    FROM territory_assignments ta
                    WHERE ta.territory_id = ?
                """, [territory_id])
                
                assignments = []
                for assignment in cursor.fetchall():
                    assignments.append({
                        'user_id': assignment['user_id'],
                        'assigned_at': assignment['assigned_at'],
                        'assignment_method': assignment['assignment_method']
                    })
                
                # Get territory metrics
                metrics = self._get_territory_metrics(cursor, territory_id)
                
                return {
                    'territory_id': result['territory_id'],
                    'name': result['name'],
                    'territory_type': result['territory_type'],
                    'description': result['description'],
                    'criteria': json.loads(result['criteria']) if result['criteria'] else {},
                    'status': result['status'],
                    'assignments': assignments,
                    'metrics': metrics,
                    'created_at': result['created_at'],
                    'updated_at': result['updated_at']
                }
            return None
    
    def list_territories(self, territory_type: Optional[str] = None, 
                        status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List territories with filters"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM territories WHERE 1=1"
            params = []
            
            if territory_type:
                query += " AND territory_type = ?"
                params.append(territory_type)
            if status:
                query += " AND status = ?"
                params.append(status)
                
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            territories = []
            for result in results:
                # Get assignment count
                cursor.execute("""
                    SELECT COUNT(*) as assignment_count
                    FROM territory_assignments
                    WHERE territory_id = ?
                """, [result['territory_id']])
                
                assignment_count = cursor.fetchone()['assignment_count']
                
                # Get basic metrics
                metrics = self._get_territory_metrics(cursor, result['territory_id'])
                
                territories.append({
                    'territory_id': result['territory_id'],
                    'name': result['name'],
                    'territory_type': result['territory_type'],
                    'description': result['description'],
                    'status': result['status'],
                    'assignment_count': assignment_count,
                    'contact_count': metrics.get('contact_count', 0),
                    'opportunity_count': metrics.get('opportunity_count', 0),
                    'total_pipeline_value': metrics.get('total_pipeline_value', 0),
                    'created_at': result['created_at']
                })
                
            return territories
    
    def assign_user_to_territory(self, territory_id: str, user_id: str,
                               assignment_method: str = "manual") -> Dict[str, Any]:
        """Assign user to territory"""
        
        assignment_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if assignment already exists
            cursor.execute("""
                SELECT assignment_id FROM territory_assignments 
                WHERE territory_id = ? AND user_id = ?
            """, [territory_id, user_id])
            
            if cursor.fetchone():
                raise ValueError("User already assigned to this territory")
            
            # Create assignment
            cursor.execute("""
                INSERT INTO territory_assignments (
                    assignment_id, territory_id, user_id, assignment_method,
                    assigned_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, [
                assignment_id,
                territory_id,
                user_id,
                assignment_method,
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ])
            
            # Update contacts and opportunities in this territory
            self._reassign_territory_records(cursor, territory_id, user_id)
            
            conn.commit()
            
            # Log activity
            self._log_activity('territory_assignment', f"User {user_id} assigned to territory", {
                'territory_id': territory_id,
                'user_id': user_id,
                'assignment_method': assignment_method
            })
            
            return {
                'assignment_id': assignment_id,
                'territory_id': territory_id,
                'user_id': user_id,
                'assignment_method': assignment_method,
                'assigned_at': datetime.utcnow().isoformat()
            }
    
    def remove_user_from_territory(self, territory_id: str, user_id: str) -> Dict[str, Any]:
        """Remove user from territory"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM territory_assignments 
                WHERE territory_id = ? AND user_id = ?
            """, [territory_id, user_id])
            
            if cursor.rowcount == 0:
                raise ValueError("Assignment not found")
            
            conn.commit()
            
            return {
                'territory_id': territory_id,
                'user_id': user_id,
                'status': 'removed',
                'removed_at': datetime.utcnow().isoformat()
            }
    
    def auto_assign_territories(self, method: AssignmentMethod = AssignmentMethod.WORKLOAD_BASED) -> Dict[str, Any]:
        """Automatically assign territories based on method"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get unassigned contacts/leads
            cursor.execute("""
                SELECT contact_id, country, state, city, company, lead_score,
                       industry, assigned_to
                FROM contacts
                WHERE territory_id IS NULL AND assigned_to IS NULL
                ORDER BY lead_score DESC
            """)
            
            unassigned_contacts = cursor.fetchall()
            
            # Get active territories
            cursor.execute("""
                SELECT * FROM territories 
                WHERE status = 'active'
            """)
            
            territories = cursor.fetchall()
            
            # Get users and their current workload
            user_workloads = self._get_user_workloads(cursor)
            
            assigned_count = 0
            assignments = []
            
            for contact in unassigned_contacts:
                territory_id = None
                user_id = None
                
                if method == AssignmentMethod.WORKLOAD_BASED:
                    # Assign to user with lowest workload
                    if user_workloads:
                        min_workload_user = min(user_workloads.items(), key=lambda x: x[1])
                        user_id = min_workload_user[0]
                        user_workloads[user_id] += 1
                        
                        # Find appropriate territory for this user
                        territory_id = self._find_best_territory_for_contact(
                            cursor, contact, territories, user_id
                        )
                
                elif method == AssignmentMethod.GEOGRAPHIC_PROXIMITY:
                    # Assign based on geographic location
                    territory_id = self._find_geographic_territory(
                        cursor, contact, territories
                    )
                
                if territory_id:
                    # Update contact
                    cursor.execute("""
                        UPDATE contacts 
                        SET territory_id = ?, assigned_to = ?, updated_at = ?
                        WHERE contact_id = ?
                    """, [
                        territory_id,
                        user_id,
                        datetime.utcnow().isoformat(),
                        contact['contact_id']
                    ])
                    
                    assigned_count += 1
                    assignments.append({
                        'contact_id': contact['contact_id'],
                        'territory_id': territory_id,
                        'user_id': user_id
                    })
            
            conn.commit()
            
            return {
                'method': method.value,
                'assigned_count': assigned_count,
                'total_unassigned': len(unassigned_contacts),
                'assignments': assignments[:10]  # First 10 for brevity
            }
    
    def balance_territories(self, rebalance_threshold: float = 0.3) -> Dict[str, Any]:
        """Balance workload across territories"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get territory workloads
            cursor.execute("""
                SELECT 
                    t.territory_id,
                    t.name,
                    COUNT(c.contact_id) as contact_count,
                    COUNT(o.opportunity_id) as opportunity_count,
                    COALESCE(SUM(o.value), 0) as pipeline_value
                FROM territories t
                LEFT JOIN contacts c ON t.territory_id = c.territory_id
                LEFT JOIN opportunities o ON c.contact_id = o.contact_id
                WHERE t.status = 'active'
                GROUP BY t.territory_id, t.name
            """)
            
            territory_workloads = cursor.fetchall()
            
            if len(territory_workloads) < 2:
                return {'message': 'Need at least 2 territories for balancing'}
            
            # Calculate statistics
            contact_counts = [t['contact_count'] for t in territory_workloads]
            avg_contacts = statistics.mean(contact_counts)
            std_contacts = statistics.stdev(contact_counts) if len(contact_counts) > 1 else 0
            
            # Identify imbalanced territories
            imbalanced = []
            balanced_count = 0
            
            for territory in territory_workloads:
                deviation = abs(territory['contact_count'] - avg_contacts)
                if deviation > (avg_contacts * rebalance_threshold):
                    imbalanced.append({
                        'territory_id': territory['territory_id'],
                        'name': territory['name'],
                        'contact_count': territory['contact_count'],
                        'deviation': deviation,
                        'status': 'overloaded' if territory['contact_count'] > avg_contacts else 'underloaded'
                    })
                else:
                    balanced_count += 1
            
            # Perform rebalancing (simplified logic)
            rebalanced = self._perform_territory_rebalancing(cursor, imbalanced, avg_contacts)
            
            conn.commit()
            
            return {
                'total_territories': len(territory_workloads),
                'balanced_territories': balanced_count,
                'imbalanced_territories': len(imbalanced),
                'avg_contacts_per_territory': avg_contacts,
                'standard_deviation': std_contacts,
                'rebalance_threshold': rebalance_threshold,
                'rebalanced_contacts': rebalanced,
                'imbalanced_details': imbalanced
            }
    
    def get_territory_performance(self, territory_id: Optional[str] = None,
                                period_days: int = 90) -> Dict[str, Any]:
        """Get territory performance analytics"""
        
        start_date = (datetime.utcnow() - timedelta(days=period_days)).isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if territory_id:
                # Single territory performance
                return self._get_single_territory_performance(cursor, territory_id, start_date)
            else:
                # All territories performance comparison
                return self._get_all_territories_performance(cursor, start_date, period_days)
    
    def get_user_territory_assignments(self, user_id: str) -> List[Dict[str, Any]]:
        """Get territories assigned to a user"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT t.*, ta.assigned_at, ta.assignment_method
                FROM territories t
                JOIN territory_assignments ta ON t.territory_id = ta.territory_id
                WHERE ta.user_id = ? AND t.status = 'active'
                ORDER BY ta.assigned_at DESC
            """, [user_id])
            
            results = cursor.fetchall()
            
            territories = []
            for result in results:
                metrics = self._get_territory_metrics(cursor, result['territory_id'])
                
                territories.append({
                    'territory_id': result['territory_id'],
                    'name': result['name'],
                    'territory_type': result['territory_type'],
                    'description': result['description'],
                    'assigned_at': result['assigned_at'],
                    'assignment_method': result['assignment_method'],
                    'metrics': metrics
                })
                
            return territories
    
    def suggest_territory_optimization(self) -> Dict[str, Any]:
        """Suggest territory optimization improvements"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            suggestions = []
            
            # Check for unassigned contacts
            cursor.execute("""
                SELECT COUNT(*) as unassigned_count
                FROM contacts
                WHERE territory_id IS NULL
            """)
            
            unassigned_count = cursor.fetchone()['unassigned_count']
            if unassigned_count > 0:
                suggestions.append({
                    'type': 'unassigned_contacts',
                    'description': f"{unassigned_count} contacts are not assigned to any territory",
                    'priority': 'high',
                    'action': 'Run auto-assignment or create new territories'
                })
            
            # Check for territory overlap
            overlap_count = self._check_territory_overlap(cursor)
            if overlap_count > 0:
                suggestions.append({
                    'type': 'territory_overlap',
                    'description': f"{overlap_count} contacts are assigned to multiple territories",
                    'priority': 'medium',
                    'action': 'Review territory criteria and resolve overlaps'
                })
            
            # Check workload balance
            balance_score = self._calculate_balance_score(cursor)
            if balance_score < 0.7:  # Below 70% balance
                suggestions.append({
                    'type': 'workload_imbalance',
                    'description': f"Territory workload balance score: {balance_score:.2f}",
                    'priority': 'medium',
                    'action': 'Consider rebalancing territories'
                })
            
            # Check for inactive territories
            cursor.execute("""
                SELECT COUNT(*) as inactive_count
                FROM territories
                WHERE status != 'active'
            """)
            
            inactive_count = cursor.fetchone()['inactive_count']
            if inactive_count > 0:
                suggestions.append({
                    'type': 'inactive_territories',
                    'description': f"{inactive_count} territories are not active",
                    'priority': 'low',
                    'action': 'Review and activate or remove inactive territories'
                })
            
            return {
                'suggestions_count': len(suggestions),
                'suggestions': suggestions,
                'overall_health_score': self._calculate_territory_health_score(cursor),
                'generated_at': datetime.utcnow().isoformat()
            }
    
    def _get_territory_metrics(self, cursor, territory_id: str) -> Dict[str, Any]:
        """Get territory performance metrics"""
        
        # Contact metrics
        cursor.execute("""
            SELECT 
                COUNT(*) as contact_count,
                COUNT(CASE WHEN lead_score > 70 THEN 1 END) as hot_leads,
                AVG(COALESCE(lead_score, 0)) as avg_lead_score
            FROM contacts
            WHERE territory_id = ?
        """, [territory_id])
        
        contact_metrics = cursor.fetchone()
        
        # Opportunity metrics
        cursor.execute("""
            SELECT 
                COUNT(o.opportunity_id) as opportunity_count,
                COALESCE(SUM(o.value), 0) as total_pipeline_value,
                COALESCE(AVG(o.value), 0) as avg_deal_size,
                COUNT(CASE WHEN o.status = 'won' THEN 1 END) as won_opportunities
            FROM opportunities o
            JOIN contacts c ON o.contact_id = c.contact_id
            WHERE c.territory_id = ?
        """, [territory_id])
        
        opportunity_metrics = cursor.fetchone()
        
        return {
            'contact_count': contact_metrics['contact_count'] or 0,
            'hot_leads': contact_metrics['hot_leads'] or 0,
            'avg_lead_score': contact_metrics['avg_lead_score'] or 0,
            'opportunity_count': opportunity_metrics['opportunity_count'] or 0,
            'total_pipeline_value': opportunity_metrics['total_pipeline_value'] or 0,
            'avg_deal_size': opportunity_metrics['avg_deal_size'] or 0,
            'won_opportunities': opportunity_metrics['won_opportunities'] or 0
        }
    
    def _get_user_workloads(self, cursor) -> Dict[str, int]:
        """Get current workload for each user"""
        
        cursor.execute("""
            SELECT 
                assigned_to,
                COUNT(*) as contact_count
            FROM contacts
            WHERE assigned_to IS NOT NULL
            GROUP BY assigned_to
        """)
        
        workloads = {}
        for result in cursor.fetchall():
            workloads[result['assigned_to']] = result['contact_count']
            
        return workloads
    
    def _find_best_territory_for_contact(self, cursor, contact: Dict[str, Any], 
                                       territories: List[Dict[str, Any]], 
                                       user_id: str) -> Optional[str]:
        """Find the best territory for a contact"""
        
        for territory in territories:
            criteria = json.loads(territory['criteria']) if territory['criteria'] else {}
            
            # Check if contact matches territory criteria
            if self._contact_matches_criteria(contact, criteria):
                # Check if user is assigned to this territory
                cursor.execute("""
                    SELECT assignment_id FROM territory_assignments
                    WHERE territory_id = ? AND user_id = ?
                """, [territory['territory_id'], user_id])
                
                if cursor.fetchone():
                    return territory['territory_id']
        
        # If no specific match, return first territory the user is assigned to
        cursor.execute("""
            SELECT territory_id FROM territory_assignments
            WHERE user_id = ?
            LIMIT 1
        """, [user_id])
        
        result = cursor.fetchone()
        return result['territory_id'] if result else None
    
    def _find_geographic_territory(self, cursor, contact: Dict[str, Any], 
                                 territories: List[Dict[str, Any]]) -> Optional[str]:
        """Find territory based on geographic location"""
        
        for territory in territories:
            if territory['territory_type'] != TerritoryType.GEOGRAPHIC.value:
                continue
                
            criteria = json.loads(territory['criteria']) if territory['criteria'] else {}
            
            if self._contact_matches_criteria(contact, criteria):
                return territory['territory_id']
        
        return None
    
    def _contact_matches_criteria(self, contact: Dict[str, Any], criteria: Dict[str, Any]) -> bool:
        """Check if contact matches territory criteria"""
        
        if not criteria:
            return False
        
        for field, value in criteria.items():
            contact_value = contact.get(field)
            
            if isinstance(value, list):
                if contact_value not in value:
                    return False
            elif isinstance(value, dict):
                # Handle range criteria (e.g., lead_score: {"min": 50, "max": 100})
                if 'min' in value and contact_value < value['min']:
                    return False
                if 'max' in value and contact_value > value['max']:
                    return False
            else:
                if contact_value != value:
                    return False
        
        return True
    
    def _reassign_territory_records(self, cursor, territory_id: str, user_id: str):
        """Reassign contacts and opportunities when user is assigned to territory"""
        
        # Update contacts in this territory
        cursor.execute("""
            UPDATE contacts 
            SET assigned_to = ?, updated_at = ?
            WHERE territory_id = ? AND assigned_to IS NULL
        """, [
            user_id,
            datetime.utcnow().isoformat(),
            territory_id
        ])
        
        # Update opportunities for contacts in this territory
        cursor.execute("""
            UPDATE opportunities 
            SET assigned_to = ?, updated_at = ?
            WHERE contact_id IN (
                SELECT contact_id FROM contacts WHERE territory_id = ?
            ) AND assigned_to IS NULL
        """, [
            user_id,
            datetime.utcnow().isoformat(),
            territory_id
        ])
    
    def _perform_territory_rebalancing(self, cursor, imbalanced: List[Dict[str, Any]], 
                                     avg_contacts: float) -> int:
        """Perform territory rebalancing"""
        
        rebalanced_count = 0
        
        # Simple rebalancing: move contacts from overloaded to underloaded territories
        overloaded = [t for t in imbalanced if t['status'] == 'overloaded']
        underloaded = [t for t in imbalanced if t['status'] == 'underloaded']
        
        for overloaded_territory in overloaded:
            for underloaded_territory in underloaded:
                # Calculate how many contacts to move
                move_count = min(
                    int((overloaded_territory['contact_count'] - avg_contacts) / 2),
                    int((avg_contacts - underloaded_territory['contact_count']) / 2)
                )
                
                if move_count > 0:
                    # Move contacts (simplified logic - in practice, you'd consider criteria)
                    cursor.execute("""
                        UPDATE contacts 
                        SET territory_id = ?, updated_at = ?
                        WHERE territory_id = ?
                        AND contact_id IN (
                            SELECT contact_id FROM contacts 
                            WHERE territory_id = ?
                            ORDER BY lead_score ASC
                            LIMIT ?
                        )
                    """, [
                        underloaded_territory['territory_id'],
                        datetime.utcnow().isoformat(),
                        overloaded_territory['territory_id'],
                        overloaded_territory['territory_id'],
                        move_count
                    ])
                    
                    rebalanced_count += move_count
                    
                    # Update counts for next iteration
                    overloaded_territory['contact_count'] -= move_count
                    underloaded_territory['contact_count'] += move_count
        
        return rebalanced_count
    
    def _get_single_territory_performance(self, cursor, territory_id: str, start_date: str) -> Dict[str, Any]:
        """Get performance metrics for a single territory"""
        
        # Basic metrics
        metrics = self._get_territory_metrics(cursor, territory_id)
        
        # Time-based metrics
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN o.created_at >= ? THEN 1 END) as new_opportunities,
                COUNT(CASE WHEN o.status = 'won' AND o.updated_at >= ? THEN 1 END) as won_opportunities,
                COALESCE(SUM(CASE WHEN o.status = 'won' AND o.updated_at >= ? THEN o.value END), 0) as won_value
            FROM opportunities o
            JOIN contacts c ON o.contact_id = c.contact_id
            WHERE c.territory_id = ?
        """, [start_date, start_date, start_date, territory_id])
        
        time_metrics = cursor.fetchone()
        
        return {
            'territory_id': territory_id,
            'current_metrics': metrics,
            'period_metrics': {
                'new_opportunities': time_metrics['new_opportunities'] or 0,
                'won_opportunities': time_metrics['won_opportunities'] or 0,
                'won_value': time_metrics['won_value'] or 0
            }
        }
    
    def _get_all_territories_performance(self, cursor, start_date: str, period_days: int) -> Dict[str, Any]:
        """Get performance comparison for all territories"""
        
        cursor.execute("""
            SELECT 
                t.territory_id,
                t.name,
                COUNT(c.contact_id) as contact_count,
                COUNT(o.opportunity_id) as opportunity_count,
                COALESCE(SUM(o.value), 0) as pipeline_value,
                COUNT(CASE WHEN o.status = 'won' AND o.updated_at >= ? THEN 1 END) as won_deals,
                COALESCE(SUM(CASE WHEN o.status = 'won' AND o.updated_at >= ? THEN o.value END), 0) as won_value
            FROM territories t
            LEFT JOIN contacts c ON t.territory_id = c.territory_id
            LEFT JOIN opportunities o ON c.contact_id = o.contact_id
            WHERE t.status = 'active'
            GROUP BY t.territory_id, t.name
            ORDER BY pipeline_value DESC
        """, [start_date, start_date])
        
        results = cursor.fetchall()
        
        performance_data = []
        for result in results:
            performance_data.append({
                'territory_id': result['territory_id'],
                'name': result['name'],
                'contact_count': result['contact_count'],
                'opportunity_count': result['opportunity_count'],
                'pipeline_value': result['pipeline_value'],
                'won_deals': result['won_deals'],
                'won_value': result['won_value']
            })
        
        return {
            'period_days': period_days,
            'territories': performance_data,
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def _check_territory_overlap(self, cursor) -> int:
        """Check for contacts assigned to multiple territories"""
        
        # This is a simplified check - in practice, you'd have more complex logic
        cursor.execute("""
            SELECT COUNT(*) as overlap_count
            FROM contacts
            WHERE territory_id IS NOT NULL
            AND contact_id IN (
                SELECT contact_id 
                FROM territory_assignments ta1
                JOIN territory_assignments ta2 ON ta1.user_id != ta2.user_id
            )
        """)
        
        result = cursor.fetchone()
        return result['overlap_count'] if result else 0
    
    def _calculate_balance_score(self, cursor) -> float:
        """Calculate territory workload balance score (0-1)"""
        
        cursor.execute("""
            SELECT COUNT(c.contact_id) as contact_count
            FROM territories t
            LEFT JOIN contacts c ON t.territory_id = c.territory_id
            WHERE t.status = 'active'
            GROUP BY t.territory_id
        """)
        
        contact_counts = [result['contact_count'] for result in cursor.fetchall()]
        
        if len(contact_counts) < 2:
            return 1.0  # Perfect balance with 0-1 territories
        
        # Calculate coefficient of variation (lower is better)
        mean_count = statistics.mean(contact_counts)
        if mean_count == 0:
            return 1.0
            
        std_count = statistics.stdev(contact_counts)
        cv = std_count / mean_count
        
        # Convert to score (1 - normalized CV)
        return max(0, 1 - min(cv, 1))
    
    def _calculate_territory_health_score(self, cursor) -> float:
        """Calculate overall territory health score"""
        
        # Factors: assignment coverage, balance, performance
        
        # Assignment coverage
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN territory_id IS NOT NULL THEN 1 END) as assigned,
                COUNT(*) as total
            FROM contacts
        """)
        
        result = cursor.fetchone()
        coverage_score = result['assigned'] / result['total'] if result['total'] > 0 else 0
        
        # Balance score
        balance_score = self._calculate_balance_score(cursor)
        
        # Simple weighted average
        health_score = (coverage_score * 0.4 + balance_score * 0.6)
        
        return round(health_score, 2)
    
    def _log_activity(self, activity_type: str, description: str, metadata: Dict[str, Any]):
        """Log territory management activity"""
        
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