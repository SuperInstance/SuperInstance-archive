"""
A/B Testing System for Beta Pricing
Test different price points and strategies to optimize conversion rates
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import sqlite3
import json
import uuid
import random
import statistics
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ExperimentStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class SignificanceLevel(str, Enum):
    LOW = "low"          # 90% confidence
    MEDIUM = "medium"    # 95% confidence
    HIGH = "high"        # 99% confidence

@dataclass
class TestGroup:
    group_id: str
    name: str
    description: str
    price_point: Decimal
    features: List[str]
    weight: float  # Percentage of users assigned to this group

@dataclass
class ExperimentResult:
    group_id: str
    total_users: int
    converted_users: int
    conversion_rate: float
    average_revenue: Decimal
    statistical_significance: str
    confidence_interval: tuple

class ABTestingSystem:
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/beta-pricing/data/beta_pricing.db"
        self._initialize_tables()
    
    def _initialize_tables(self):
        """Initialize database tables for A/B testing"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Experiments table (already exists in main.py, but ensuring it's here)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ab_experiments (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'draft',
                control_group TEXT NOT NULL,
                test_groups TEXT NOT NULL,
                start_date TIMESTAMP,
                end_date TIMESTAMP,
                conversion_metric TEXT DEFAULT 'signup_to_paid',
                target_significance REAL DEFAULT 0.95,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT NOT NULL
            )
        ''')
        
        # User experiment assignments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_experiment_assignments (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                experiment_id TEXT NOT NULL,
                group_id TEXT NOT NULL,
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                converted BOOLEAN DEFAULT FALSE,
                conversion_date TIMESTAMP,
                revenue DECIMAL DEFAULT 0,
                data TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES beta_users (id),
                FOREIGN KEY (experiment_id) REFERENCES ab_experiments (id),
                UNIQUE(user_id, experiment_id)
            )
        ''')
        
        # Experiment events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS experiment_events (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                experiment_id TEXT NOT NULL,
                group_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_data TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES beta_users (id),
                FOREIGN KEY (experiment_id) REFERENCES ab_experiments (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def create_experiment(
        self,
        name: str,
        description: str,
        test_groups: List[Dict[str, Any]],
        conversion_metric: str = "signup_to_paid",
        target_significance: float = 0.95
    ) -> Dict[str, Any]:
        """Create a new A/B testing experiment"""
        try:
            experiment_id = f"EXP_{uuid.uuid4().hex[:8].upper()}"
            
            # Validate test groups
            total_weight = sum(group.get("weight", 0) for group in test_groups)
            if abs(total_weight - 1.0) > 0.01:
                raise ValueError("Test group weights must sum to 1.0")
            
            # Create test group objects
            groups = []
            control_group = None
            
            for group_data in test_groups:
                group = TestGroup(
                    group_id=f"GRP_{uuid.uuid4().hex[:6].upper()}",
                    name=group_data["name"],
                    description=group_data.get("description", ""),
                    price_point=Decimal(str(group_data["price_point"])),
                    features=group_data.get("features", []),
                    weight=group_data["weight"]
                )
                groups.append(group)
                
                if group_data.get("is_control", False):
                    control_group = group.group_id
            
            if not control_group:
                # Default to first group as control
                control_group = groups[0].group_id
            
            experiment_data = {
                "id": experiment_id,
                "name": name,
                "description": description,
                "status": ExperimentStatus.DRAFT.value,
                "control_group": control_group,
                "test_groups": [
                    {
                        "group_id": g.group_id,
                        "name": g.name,
                        "description": g.description,
                        "price_point": float(g.price_point),
                        "features": g.features,
                        "weight": g.weight
                    }
                    for g in groups
                ],
                "conversion_metric": conversion_metric,
                "target_significance": target_significance,
                "created_at": datetime.now().isoformat()
            }
            
            # Store experiment
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO ab_experiments 
                (id, name, description, status, control_group, test_groups,
                 conversion_metric, target_significance, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                experiment_id, name, description, ExperimentStatus.DRAFT.value,
                control_group, json.dumps([g.__dict__ for g in groups]),
                conversion_metric, target_significance,
                json.dumps(experiment_data)
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Created experiment {experiment_id}: {name}")
            
            return experiment_data
            
        except Exception as e:
            logger.error(f"Error creating experiment: {str(e)}")
            return {"error": str(e)}
    
    async def start_experiment(self, experiment_id: str) -> Dict[str, Any]:
        """Start an experiment"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Update experiment status
            cursor.execute('''
                UPDATE ab_experiments 
                SET status = ?, start_date = ?
                WHERE id = ? AND status = 'draft'
            ''', (ExperimentStatus.ACTIVE.value, datetime.now().isoformat(), experiment_id))
            
            if cursor.rowcount == 0:
                conn.close()
                return {"error": "Experiment not found or not in draft status"}
            
            conn.commit()
            conn.close()
            
            logger.info(f"Started experiment {experiment_id}")
            
            return {
                "experiment_id": experiment_id,
                "status": "active",
                "started_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error starting experiment: {str(e)}")
            return {"error": str(e)}
    
    async def assign_user_to_experiment(self, user_id: str, experiment_id: str) -> str:
        """Assign user to experiment group"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if user already assigned
            cursor.execute('''
                SELECT group_id FROM user_experiment_assignments 
                WHERE user_id = ? AND experiment_id = ?
            ''', (user_id, experiment_id))
            
            existing = cursor.fetchone()
            if existing:
                conn.close()
                return existing[0]
            
            # Get experiment details
            cursor.execute('''
                SELECT test_groups, status FROM ab_experiments 
                WHERE id = ?
            ''', (experiment_id,))
            
            exp_result = cursor.fetchone()
            if not exp_result or exp_result[1] != ExperimentStatus.ACTIVE.value:
                conn.close()
                return "control"  # Default group if experiment not active
            
            test_groups = json.loads(exp_result[0])
            
            # Assign user to group based on weights
            rand = random.random()
            cumulative_weight = 0
            selected_group = test_groups[0]["group_id"]  # Fallback
            
            for group in test_groups:
                cumulative_weight += group["weight"]
                if rand <= cumulative_weight:
                    selected_group = group["group_id"]
                    break
            
            # Record assignment
            assignment_id = f"ASSIGN_{uuid.uuid4().hex[:8].upper()}"
            assignment_data = {
                "id": assignment_id,
                "user_id": user_id,
                "experiment_id": experiment_id,
                "group_id": selected_group,
                "assigned_at": datetime.now().isoformat()
            }
            
            cursor.execute('''
                INSERT INTO user_experiment_assignments 
                (id, user_id, experiment_id, group_id, data)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                assignment_id, user_id, experiment_id, selected_group,
                json.dumps(assignment_data)
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Assigned user {user_id} to group {selected_group} in experiment {experiment_id}")
            
            return selected_group
            
        except Exception as e:
            logger.error(f"Error assigning user to experiment: {str(e)}")
            return "control"  # Safe fallback
    
    async def track_conversion(self, user_id: str, experiment_id: str, revenue: Decimal = Decimal('0')) -> Dict[str, Any]:
        """Track user conversion in experiment"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Update conversion status
            cursor.execute('''
                UPDATE user_experiment_assignments 
                SET converted = TRUE, conversion_date = ?, revenue = ?
                WHERE user_id = ? AND experiment_id = ?
            ''', (datetime.now().isoformat(), float(revenue), user_id, experiment_id))
            
            if cursor.rowcount == 0:
                conn.close()
                return {"error": "Assignment not found"}
            
            # Record conversion event
            event_id = f"CONV_{uuid.uuid4().hex[:8].upper()}"
            cursor.execute('''
                INSERT INTO experiment_events 
                (id, user_id, experiment_id, group_id, event_type, event_data)
                SELECT ?, ?, ?, group_id, 'conversion', ?
                FROM user_experiment_assignments 
                WHERE user_id = ? AND experiment_id = ?
            ''', (
                event_id, user_id, experiment_id,
                json.dumps({"revenue": float(revenue)}),
                user_id, experiment_id
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Tracked conversion for user {user_id} in experiment {experiment_id}")
            
            return {
                "user_id": user_id,
                "experiment_id": experiment_id,
                "converted": True,
                "revenue": float(revenue),
                "conversion_date": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error tracking conversion: {str(e)}")
            return {"error": str(e)}
    
    async def get_experiment_results(self, experiment_id: str) -> Dict[str, Any]:
        """Get detailed experiment results with statistical analysis"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get experiment details
            cursor.execute('''
                SELECT name, description, status, control_group, test_groups, 
                       target_significance, start_date, data
                FROM ab_experiments WHERE id = ?
            ''', (experiment_id,))
            
            exp_result = cursor.fetchone()
            if not exp_result:
                conn.close()
                return {"error": "Experiment not found"}
            
            name, description, status, control_group, test_groups_json, target_sig, start_date, exp_data = exp_result
            test_groups = json.loads(test_groups_json)
            
            # Get results by group
            cursor.execute('''
                SELECT 
                    group_id,
                    COUNT(*) as total_users,
                    SUM(CASE WHEN converted = 1 THEN 1 ELSE 0 END) as converted_users,
                    AVG(CASE WHEN converted = 1 THEN revenue ELSE 0 END) as avg_revenue,
                    SUM(revenue) as total_revenue
                FROM user_experiment_assignments 
                WHERE experiment_id = ?
                GROUP BY group_id
            ''', (experiment_id,))
            
            group_results = cursor.fetchall()
            conn.close()
            
            # Calculate statistical significance
            results = []
            control_stats = None
            
            for group_id, total_users, converted_users, avg_revenue, total_revenue in group_results:
                conversion_rate = converted_users / total_users if total_users > 0 else 0
                
                group_data = next((g for g in test_groups if g["group_id"] == group_id), {})
                
                result = ExperimentResult(
                    group_id=group_id,
                    total_users=total_users,
                    converted_users=converted_users,
                    conversion_rate=conversion_rate,
                    average_revenue=Decimal(str(avg_revenue or 0)),
                    statistical_significance="pending",
                    confidence_interval=(0, 0)
                )
                
                if group_id == control_group:
                    control_stats = result
                
                results.append({
                    "group_id": group_id,
                    "group_name": group_data.get("name", group_id),
                    "price_point": group_data.get("price_point", 0),
                    "total_users": total_users,
                    "converted_users": converted_users,
                    "conversion_rate": round(conversion_rate * 100, 2),
                    "average_revenue": float(result.average_revenue),
                    "total_revenue": float(total_revenue or 0),
                    "statistical_significance": result.statistical_significance
                })
            
            # Calculate statistical significance compared to control
            if control_stats and len(results) > 1:
                for result_dict in results:
                    if result_dict["group_id"] != control_group:
                        significance = self._calculate_statistical_significance(
                            control_stats.converted_users, control_stats.total_users,
                            result_dict["converted_users"], result_dict["total_users"],
                            target_sig
                        )
                        result_dict["statistical_significance"] = significance
            
            # Calculate experiment summary
            total_users = sum(r["total_users"] for r in results)
            total_converted = sum(r["converted_users"] for r in results)
            overall_conversion = (total_converted / total_users * 100) if total_users > 0 else 0
            
            # Determine winning group
            winning_group = max(results, key=lambda x: x["conversion_rate"]) if results else None
            
            return {
                "experiment_id": experiment_id,
                "name": name,
                "description": description,
                "status": status,
                "start_date": start_date,
                "duration_days": self._calculate_duration_days(start_date),
                "control_group": control_group,
                "summary": {
                    "total_users": total_users,
                    "total_converted": total_converted,
                    "overall_conversion_rate": round(overall_conversion, 2),
                    "winning_group": winning_group["group_name"] if winning_group else None,
                    "improvement": self._calculate_improvement(results, control_group)
                },
                "group_results": results,
                "recommendations": self._generate_recommendations(results, control_group),
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting experiment results: {str(e)}")
            return {"error": str(e)}
    
    def _calculate_statistical_significance(
        self, 
        control_conversions: int, 
        control_total: int,
        test_conversions: int, 
        test_total: int,
        target_significance: float
    ) -> str:
        """Calculate statistical significance using z-test"""
        if control_total == 0 or test_total == 0:
            return "insufficient_data"
        
        # Calculate conversion rates
        p1 = control_conversions / control_total
        p2 = test_conversions / test_total
        
        # Calculate pooled probability
        pooled_prob = (control_conversions + test_conversions) / (control_total + test_total)
        pooled_se = (pooled_prob * (1 - pooled_prob) * (1/control_total + 1/test_total)) ** 0.5
        
        if pooled_se == 0:
            return "no_difference"
        
        # Calculate z-score
        z_score = (p2 - p1) / pooled_se
        
        # Determine significance level
        if abs(z_score) >= 2.576:  # 99% confidence
            return "high"
        elif abs(z_score) >= 1.96:  # 95% confidence
            return "medium"
        elif abs(z_score) >= 1.645:  # 90% confidence
            return "low"
        else:
            return "not_significant"
    
    def _calculate_duration_days(self, start_date: str) -> int:
        """Calculate experiment duration in days"""
        if not start_date:
            return 0
        
        start = datetime.fromisoformat(start_date)
        return (datetime.now() - start).days
    
    def _calculate_improvement(self, results: List[Dict], control_group: str) -> Optional[float]:
        """Calculate improvement over control group"""
        control_result = next((r for r in results if r["group_id"] == control_group), None)
        if not control_result:
            return None
        
        best_result = max(results, key=lambda x: x["conversion_rate"] if x["group_id"] != control_group else 0)
        
        if best_result["group_id"] == control_group or control_result["conversion_rate"] == 0:
            return 0.0
        
        improvement = ((best_result["conversion_rate"] - control_result["conversion_rate"]) 
                      / control_result["conversion_rate"] * 100)
        
        return round(improvement, 2)
    
    def _generate_recommendations(self, results: List[Dict], control_group: str) -> List[str]:
        """Generate recommendations based on experiment results"""
        recommendations = []
        
        if not results:
            return ["Insufficient data for recommendations"]
        
        # Find control and best performing group
        control_result = next((r for r in results if r["group_id"] == control_group), None)
        best_result = max(results, key=lambda x: x["conversion_rate"])
        
        if not control_result:
            recommendations.append("Control group not found in results")
            return recommendations
        
        # Statistical significance check
        if best_result["statistical_significance"] in ["high", "medium"]:
            if best_result["group_id"] != control_group:
                recommendations.append(
                    f"Implement {best_result['group_name']} - shows {best_result['conversion_rate']:.1f}% "
                    f"conversion rate vs {control_result['conversion_rate']:.1f}% control"
                )
            else:
                recommendations.append("Current control group is performing best - maintain current pricing")
        else:
            recommendations.append("No statistically significant winner - continue testing or gather more data")
        
        # Sample size recommendations
        min_sample_size = 100  # Minimum for reliable results
        if any(r["total_users"] < min_sample_size for r in results):
            recommendations.append(f"Increase sample size - aim for at least {min_sample_size} users per group")
        
        # Revenue considerations
        if best_result["average_revenue"] > 0:
            total_revenue_impact = (best_result["conversion_rate"] / 100 * best_result["average_revenue"] * 1000)
            recommendations.append(
                f"Potential monthly revenue impact: ${total_revenue_impact:.2f} "
                f"(based on 1000 monthly users)"
            )
        
        return recommendations
    
    async def get_active_experiments_summary(self) -> Dict[str, Any]:
        """Get summary of all active experiments"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, name, status, start_date,
                       (SELECT COUNT(*) FROM user_experiment_assignments 
                        WHERE experiment_id = ab_experiments.id) as total_users,
                       (SELECT COUNT(*) FROM user_experiment_assignments 
                        WHERE experiment_id = ab_experiments.id AND converted = 1) as converted_users
                FROM ab_experiments 
                WHERE status = 'active'
                ORDER BY start_date DESC
            ''')
            
            experiments = cursor.fetchall()
            conn.close()
            
            experiment_summaries = []
            for exp_id, name, status, start_date, total_users, converted_users in experiments:
                conversion_rate = (converted_users / total_users * 100) if total_users > 0 else 0
                
                experiment_summaries.append({
                    "experiment_id": exp_id,
                    "name": name,
                    "status": status,
                    "start_date": start_date,
                    "duration_days": self._calculate_duration_days(start_date),
                    "total_users": total_users,
                    "converted_users": converted_users,
                    "conversion_rate": round(conversion_rate, 2)
                })
            
            return {
                "active_experiments": len(experiment_summaries),
                "experiments": experiment_summaries,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting experiments summary: {str(e)}")
            return {"error": str(e)}
    
    async def stop_experiment(self, experiment_id: str, reason: str = "completed") -> Dict[str, Any]:
        """Stop an active experiment"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            status = ExperimentStatus.COMPLETED.value if reason == "completed" else ExperimentStatus.CANCELLED.value
            
            cursor.execute('''
                UPDATE ab_experiments 
                SET status = ?, end_date = ?
                WHERE id = ? AND status = 'active'
            ''', (status, datetime.now().isoformat(), experiment_id))
            
            if cursor.rowcount == 0:
                conn.close()
                return {"error": "Experiment not found or not active"}
            
            conn.commit()
            conn.close()
            
            logger.info(f"Stopped experiment {experiment_id} with reason: {reason}")
            
            # Get final results
            final_results = await self.get_experiment_results(experiment_id)
            
            return {
                "experiment_id": experiment_id,
                "status": status,
                "stopped_at": datetime.now().isoformat(),
                "reason": reason,
                "final_results": final_results
            }
            
        except Exception as e:
            logger.error(f"Error stopping experiment: {str(e)}")
            return {"error": str(e)}

# Global instance
ab_testing_system = ABTestingSystem()