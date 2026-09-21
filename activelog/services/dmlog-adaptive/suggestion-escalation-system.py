#!/usr/bin/env python3
"""
DMLog Suggestion Escalation System
Handles escalation of suggestions that might benefit the entire ActiveLog ecosystem

When Max makes suggestions that could improve the whole system, this system:
1. Implements the DMLog-specific version first
2. Evaluates system-wide applicability  
3. Creates escalation notes for admin review
4. Tracks escalation outcomes
"""

import sqlite3
import json
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EscalationStatus(Enum):
    PENDING_EVALUATION = "pending_evaluation"
    READY_FOR_ESCALATION = "ready_for_escalation"
    ESCALATED_TO_ADMIN = "escalated_to_admin"
    ADMIN_REVIEWED = "admin_reviewed"
    IMPLEMENTED_SYSTEM_WIDE = "implemented_system_wide"
    REJECTED = "rejected"
    DMLOG_ONLY = "dmlog_only"

class EscalationPriority(Enum):
    CRITICAL = "critical"  # Could revolutionize entire platform
    HIGH = "high"         # Significant improvement potential
    MEDIUM = "medium"     # Moderate benefit
    LOW = "low"          # Minor enhancement

@dataclass
class SuggestionEscalation:
    """Data structure for suggestion escalations"""
    id: Optional[int]
    original_suggestion: str
    dmlog_implementation: str
    system_wide_potential: str
    impact_assessment: str
    technical_feasibility: str
    resource_requirements: str
    priority: EscalationPriority
    status: EscalationStatus
    created_at: str
    escalated_at: Optional[str]
    admin_response: Optional[str]
    implementation_notes: Optional[str]

@dataclass
class EscalationMetrics:
    """Metrics for escalation system performance"""
    total_escalations: int
    pending_count: int
    approved_count: int
    rejected_count: int
    average_processing_time: float
    system_wide_implementations: int

class SuggestionEscalationSystem:
    """
    System for evaluating and escalating DMLog suggestions that could benefit the entire platform
    """
    
    def __init__(self, db_path: str = "/tmp/dmlog_escalations.db"):
        self.db_path = db_path
        self.escalation_dir = "/tmp/dmlog_escalations"
        self.admin_notification_file = "/tmp/admin_escalation_notifications.json"
        self.init_database()
        self.ensure_directories()
        
    def init_database(self):
        """Initialize escalation database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Suggestion escalations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS suggestion_escalations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_suggestion TEXT NOT NULL,
                dmlog_implementation TEXT NOT NULL,
                system_wide_potential TEXT NOT NULL,
                impact_assessment TEXT NOT NULL,
                technical_feasibility TEXT NOT NULL,
                resource_requirements TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                escalated_at TIMESTAMP,
                admin_response TEXT,
                implementation_notes TEXT
            )
        """)
        
        # Escalation evaluation criteria
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evaluation_criteria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                criterion_name TEXT UNIQUE NOT NULL,
                description TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                threshold REAL DEFAULT 0.7,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Admin notifications queue
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                escalation_id INTEGER NOT NULL,
                notification_type TEXT NOT NULL,
                message TEXT NOT NULL,
                priority TEXT NOT NULL,
                delivered BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                delivered_at TIMESTAMP,
                FOREIGN KEY (escalation_id) REFERENCES suggestion_escalations (id)
            )
        """)
        
        # System-wide implementation tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_implementations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                escalation_id INTEGER NOT NULL,
                service_name TEXT NOT NULL,
                implementation_status TEXT NOT NULL,
                implementation_date TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (escalation_id) REFERENCES suggestion_escalations (id)
            )
        """)
        
        conn.commit()
        conn.close()
        
        # Initialize default evaluation criteria
        self.init_default_criteria()
        
    def init_default_criteria(self):
        """Initialize default evaluation criteria for escalations"""
        criteria = [
            {
                "criterion_name": "user_impact",
                "description": "How significantly this would improve user experience across services",
                "weight": 2.0,
                "threshold": 0.8
            },
            {
                "criterion_name": "technical_reusability",
                "description": "How easily this can be applied to other services",
                "weight": 1.5,
                "threshold": 0.7
            },
            {
                "criterion_name": "innovation_value",
                "description": "How innovative or unique this improvement is",
                "weight": 1.2,
                "threshold": 0.6
            },
            {
                "criterion_name": "resource_efficiency",
                "description": "Return on investment for system-wide implementation",
                "weight": 1.8,
                "threshold": 0.7
            },
            {
                "criterion_name": "strategic_alignment",
                "description": "Alignment with overall ActiveLog platform goals",
                "weight": 2.5,
                "threshold": 0.8
            }
        ]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for criterion in criteria:
            cursor.execute("""
                INSERT OR IGNORE INTO evaluation_criteria
                (criterion_name, description, weight, threshold)
                VALUES (?, ?, ?, ?)
            """, (
                criterion["criterion_name"],
                criterion["description"],
                criterion["weight"],
                criterion["threshold"]
            ))
            
        conn.commit()
        conn.close()
        
    def ensure_directories(self):
        """Ensure required directories exist"""
        Path(self.escalation_dir).mkdir(parents=True, exist_ok=True)
        
    def evaluate_suggestion_for_escalation(self, suggestion: str, dmlog_context: str) -> Dict[str, Any]:
        """
        Evaluate whether a DMLog suggestion should be escalated system-wide
        Uses AI-powered analysis to assess escalation potential
        """
        
        # AI-powered evaluation criteria
        evaluation_prompts = {
            "user_impact": f"""
            Analyze this suggestion for system-wide user impact:
            
            Original: {suggestion}
            DMLog Context: {dmlog_context}
            
            Rate 0.0-1.0: How much would implementing this across all ActiveLog services improve user experience?
            Consider: usability, efficiency, satisfaction, feature completeness
            """,
            
            "technical_reusability": f"""
            Assess technical reusability:
            
            Suggestion: {suggestion}
            Implementation: {dmlog_context}
            
            Rate 0.0-1.0: How easily could this be implemented in other ActiveLog services?
            Consider: code reusability, architectural compatibility, maintenance overhead
            """,
            
            "innovation_value": f"""
            Evaluate innovation value:
            
            Suggestion: {suggestion}
            
            Rate 0.0-1.0: How innovative or competitive advantage does this provide?
            Consider: market differentiation, technological advancement, user wow factor
            """,
            
            "resource_efficiency": f"""
            Assess resource efficiency:
            
            Suggestion: {suggestion}
            Context: {dmlog_context}
            
            Rate 0.0-1.0: What's the ROI of system-wide implementation?
            Consider: development time, maintenance cost, user value delivered
            """,
            
            "strategic_alignment": f"""
            Evaluate strategic alignment:
            
            Suggestion: {suggestion}
            
            Rate 0.0-1.0: How well does this align with ActiveLog platform goals?
            Consider: unified user experience, platform coherence, long-term vision
            """
        }
        
        # Simulate AI evaluation (in production, use actual AI model)
        evaluation_scores = {}
        evaluation_explanations = {}
        
        # Basic heuristic evaluation (replace with actual AI in production)
        keywords_high_impact = ["ai", "voice", "automation", "intelligence", "adaptive", "learning"]
        keywords_reusable = ["interface", "api", "system", "framework", "component", "service"]
        keywords_innovative = ["revolutionary", "unique", "advanced", "breakthrough", "cutting-edge"]
        
        suggestion_lower = suggestion.lower()
        dmlog_lower = dmlog_context.lower()
        
        # User Impact Score
        impact_indicators = sum(1 for kw in keywords_high_impact if kw in suggestion_lower)
        evaluation_scores["user_impact"] = min(0.3 + (impact_indicators * 0.2), 1.0)
        evaluation_explanations["user_impact"] = f"Found {impact_indicators} high-impact indicators in suggestion"
        
        # Technical Reusability Score  
        reusability_indicators = sum(1 for kw in keywords_reusable if kw in dmlog_lower)
        evaluation_scores["technical_reusability"] = min(0.4 + (reusability_indicators * 0.15), 1.0)
        evaluation_explanations["technical_reusability"] = f"Found {reusability_indicators} reusability indicators"
        
        # Innovation Value Score
        innovation_indicators = sum(1 for kw in keywords_innovative if kw in suggestion_lower)
        evaluation_scores["innovation_value"] = min(0.2 + (innovation_indicators * 0.25), 1.0)
        evaluation_explanations["innovation_value"] = f"Found {innovation_indicators} innovation indicators"
        
        # Resource Efficiency (inverse of complexity)
        complexity_indicators = len([w for w in suggestion_lower.split() if len(w) > 8])
        evaluation_scores["resource_efficiency"] = max(0.8 - (complexity_indicators * 0.05), 0.2)
        evaluation_explanations["resource_efficiency"] = f"Complexity assessment based on {complexity_indicators} complex terms"
        
        # Strategic Alignment (based on key platform concepts)
        platform_concepts = ["platform", "ecosystem", "unified", "consistent", "integrated"]
        alignment_indicators = sum(1 for kw in platform_concepts if kw in suggestion_lower)
        evaluation_scores["strategic_alignment"] = min(0.5 + (alignment_indicators * 0.2), 1.0)
        evaluation_explanations["strategic_alignment"] = f"Found {alignment_indicators} platform alignment indicators"
        
        return {
            "scores": evaluation_scores,
            "explanations": evaluation_explanations,
            "overall_score": sum(evaluation_scores.values()) / len(evaluation_scores)
        }
        
    def calculate_escalation_priority(self, evaluation_scores: Dict[str, float]) -> EscalationPriority:
        """Calculate escalation priority based on evaluation scores"""
        
        # Get criteria weights
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT criterion_name, weight, threshold FROM evaluation_criteria")
        criteria_data = cursor.fetchall()
        conn.close()
        
        # Calculate weighted score
        weighted_total = 0.0
        weight_sum = 0.0
        
        for criterion_name, weight, threshold in criteria_data:
            if criterion_name in evaluation_scores:
                weighted_total += evaluation_scores[criterion_name] * weight
                weight_sum += weight
                
        if weight_sum == 0:
            return EscalationPriority.LOW
            
        weighted_average = weighted_total / weight_sum
        
        # Determine priority based on weighted score
        if weighted_average >= 0.9:
            return EscalationPriority.CRITICAL
        elif weighted_average >= 0.75:
            return EscalationPriority.HIGH
        elif weighted_average >= 0.6:
            return EscalationPriority.MEDIUM
        else:
            return EscalationPriority.LOW
            
    def should_escalate(self, evaluation_scores: Dict[str, float]) -> Tuple[bool, str]:
        """Determine if suggestion should be escalated and provide reasoning"""
        
        # Get thresholds
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT criterion_name, threshold FROM evaluation_criteria")
        thresholds = dict(cursor.fetchall())
        conn.close()
        
        # Check if meets escalation criteria
        meets_criteria = []
        fails_criteria = []
        
        for criterion, score in evaluation_scores.items():
            if criterion in thresholds:
                if score >= thresholds[criterion]:
                    meets_criteria.append(f"{criterion}: {score:.2f} >= {thresholds[criterion]:.2f}")
                else:
                    fails_criteria.append(f"{criterion}: {score:.2f} < {thresholds[criterion]:.2f}")
                    
        # Must meet at least 3 criteria and overall score > 0.65
        overall_score = sum(evaluation_scores.values()) / len(evaluation_scores)
        
        should_escalate = len(meets_criteria) >= 3 and overall_score >= 0.65
        
        reasoning = f"""
Escalation Decision: {"ESCALATE" if should_escalate else "DO NOT ESCALATE"}

Overall Score: {overall_score:.3f}
Criteria Met: {len(meets_criteria)}/5 (need 3+)

Criteria Analysis:
✅ Meets Threshold:
{chr(10).join(meets_criteria) if meets_criteria else "None"}

❌ Below Threshold:
{chr(10).join(fails_criteria) if fails_criteria else "None"}

Decision Logic: Needs 3+ criteria met AND overall score ≥ 0.65
"""
        
        return should_escalate, reasoning
        
    def create_escalation(self, original_suggestion: str, dmlog_implementation: str) -> int:
        """Create a new escalation record"""
        
        # Evaluate suggestion
        evaluation = self.evaluate_suggestion_for_escalation(original_suggestion, dmlog_implementation)
        priority = self.calculate_escalation_priority(evaluation["scores"])
        should_escalate, reasoning = self.should_escalate(evaluation["scores"])
        
        # Generate system-wide potential assessment
        system_wide_potential = f"""
System-Wide Implementation Potential:

Overall Score: {evaluation['overall_score']:.3f}/1.0
Priority: {priority.value}

Evaluation Breakdown:
"""
        for criterion, score in evaluation["scores"].items():
            explanation = evaluation["explanations"].get(criterion, "No explanation")
            system_wide_potential += f"- {criterion.replace('_', ' ').title()}: {score:.2f} - {explanation}\n"
            
        system_wide_potential += f"\n{reasoning}"
        
        # Create escalation record
        escalation = SuggestionEscalation(
            id=None,
            original_suggestion=original_suggestion,
            dmlog_implementation=dmlog_implementation,
            system_wide_potential=system_wide_potential,
            impact_assessment=json.dumps(evaluation["scores"]),
            technical_feasibility="Requires detailed analysis by admin",
            resource_requirements="To be assessed during admin review",
            priority=priority,
            status=EscalationStatus.READY_FOR_ESCALATION if should_escalate else EscalationStatus.DMLOG_ONLY,
            created_at=datetime.now().isoformat(),
            escalated_at=None,
            admin_response=None,
            implementation_notes=None
        )
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO suggestion_escalations
            (original_suggestion, dmlog_implementation, system_wide_potential, 
             impact_assessment, technical_feasibility, resource_requirements,
             priority, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            escalation.original_suggestion,
            escalation.dmlog_implementation,
            escalation.system_wide_potential,
            escalation.impact_assessment,
            escalation.technical_feasibility,
            escalation.resource_requirements,
            escalation.priority.value,
            escalation.status.value,
            escalation.created_at
        ))
        
        escalation_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # If should escalate, create admin notification
        if should_escalate:
            self.create_admin_notification(escalation_id, priority)
            
        return escalation_id
        
    def create_admin_notification(self, escalation_id: int, priority: EscalationPriority):
        """Create notification for admin about new escalation"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get escalation details
        cursor.execute("""
            SELECT original_suggestion, system_wide_potential
            FROM suggestion_escalations
            WHERE id = ?
        """, (escalation_id,))
        
        result = cursor.fetchone()
        if not result:
            return
            
        original_suggestion, system_wide_potential = result
        
        # Create notification message
        message = f"""
NEW ESCALATION READY FOR REVIEW

Priority: {priority.value.upper()}
Escalation ID: {escalation_id}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Original Suggestion from Max:
{original_suggestion}

System-Wide Analysis:
{system_wide_potential[:500]}...

Action Required:
Please review this escalation when you have time. The DMLog-specific implementation has been completed, and this suggestion shows potential for system-wide benefits.

Review Command: View escalation details in /tmp/dmlog_escalations/
"""
        
        # Save notification
        cursor.execute("""
            INSERT INTO admin_notifications
            (escalation_id, notification_type, message, priority)
            VALUES (?, ?, ?, ?)
        """, (escalation_id, "new_escalation", message, priority.value))
        
        conn.commit()
        conn.close()
        
        # Update notification file for admin
        self.update_admin_notification_file()
        
    def update_admin_notification_file(self):
        """Update admin notification file with pending escalations"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all undelivered notifications
        cursor.execute("""
            SELECT id, escalation_id, message, priority, created_at
            FROM admin_notifications
            WHERE delivered = FALSE
            ORDER BY 
                CASE priority 
                    WHEN 'critical' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'medium' THEN 3
                    WHEN 'low' THEN 4
                END,
                created_at DESC
        """)
        
        notifications = cursor.fetchall()
        conn.close()
        
        if notifications:
            notification_data = {
                "unread_count": len(notifications),
                "last_updated": datetime.now().isoformat(),
                "notifications": []
            }
            
            for notif_id, escalation_id, message, priority, created_at in notifications:
                notification_data["notifications"].append({
                    "id": notif_id,
                    "escalation_id": escalation_id,
                    "priority": priority,
                    "created_at": created_at,
                    "preview": message[:200] + "..." if len(message) > 200 else message
                })
            
            # Save to file
            with open(self.admin_notification_file, 'w') as f:
                json.dump(notification_data, f, indent=2)
                
    def get_escalation_metrics(self) -> EscalationMetrics:
        """Get metrics about the escalation system"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total escalations
        cursor.execute("SELECT COUNT(*) FROM suggestion_escalations")
        total_escalations = cursor.fetchone()[0]
        
        # Count by status
        cursor.execute("""
            SELECT status, COUNT(*) 
            FROM suggestion_escalations 
            GROUP BY status
        """)
        status_counts = dict(cursor.fetchall())
        
        # Average processing time for completed escalations
        cursor.execute("""
            SELECT AVG(
                CASE 
                    WHEN escalated_at IS NOT NULL AND admin_response IS NOT NULL
                    THEN julianday(admin_response) - julianday(escalated_at)
                    ELSE NULL
                END
            ) * 24 * 60 as avg_minutes
            FROM suggestion_escalations
        """)
        avg_processing_result = cursor.fetchone()[0]
        avg_processing_time = avg_processing_result if avg_processing_result else 0.0
        
        conn.close()
        
        return EscalationMetrics(
            total_escalations=total_escalations,
            pending_count=status_counts.get("pending_evaluation", 0) + status_counts.get("ready_for_escalation", 0),
            approved_count=status_counts.get("admin_reviewed", 0) + status_counts.get("implemented_system_wide", 0),
            rejected_count=status_counts.get("rejected", 0),
            average_processing_time=avg_processing_time,
            system_wide_implementations=status_counts.get("implemented_system_wide", 0)
        )


def main():
    """Test the escalation system"""
    escalation_system = SuggestionEscalationSystem()
    
    # Test escalation creation
    test_suggestion = "Add AI-powered voice commands that learn user preferences over time"
    test_implementation = "Implemented voice control system in DMLog with machine learning adaptation"
    
    escalation_id = escalation_system.create_escalation(test_suggestion, test_implementation)
    
    print(f"Created test escalation with ID: {escalation_id}")
    print(f"Admin notifications saved to: {escalation_system.admin_notification_file}")
    
    # Get metrics
    metrics = escalation_system.get_escalation_metrics()
    print(f"\nEscalation System Metrics:")
    print(f"Total Escalations: {metrics.total_escalations}")
    print(f"Pending Review: {metrics.pending_count}")
    print(f"Average Processing Time: {metrics.average_processing_time:.1f} minutes")
    
    print("\nSuggestion escalation system is ready!")
    print("When Max makes suggestions that might benefit the whole system,")
    print("they will be automatically evaluated and escalated if appropriate.")


if __name__ == "__main__":
    main()