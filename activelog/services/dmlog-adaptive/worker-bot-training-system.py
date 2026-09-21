#!/usr/bin/env python3
"""
DMLog Worker Bot Training System
Contextual training material generator for worker bots working on DMLog-specific improvements

Creates training materials that understand DMLog context and Max's specific requirements
"""

import sqlite3
import json
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class WorkerBotNote:
    """Data structure for worker bot notes from Max"""
    id: int
    note_text: str
    context_type: str  # 'dmlog_specific', 'system_wide', 'interface', 'feature'
    priority: str  # 'high', 'medium', 'low'
    created_at: str
    status: str  # 'pending', 'in_progress', 'completed', 'escalated'
    escalation_reason: Optional[str] = None

@dataclass
class TrainingContext:
    """Training context for worker bots"""
    system_name: str
    current_focus: str
    key_requirements: List[str]
    forbidden_actions: List[str]
    success_metrics: List[str]

class DMLogTrainingSystem:
    """
    Training material generator that creates context-aware training for worker bots
    Ensures all training materials understand DMLog-specific requirements
    """
    
    def __init__(self, db_path: str = "/tmp/dmlog_training.db"):
        self.db_path = db_path
        self.training_dir = "/tmp/dmlog_training_materials"
        self.init_database()
        self.ensure_training_directory()
        
    def init_database(self):
        """Initialize training database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Training contexts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS training_contexts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                context_name TEXT UNIQUE NOT NULL,
                system_focus TEXT NOT NULL,
                requirements JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Training materials table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS training_materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                material_name TEXT NOT NULL,
                context_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                material_type TEXT NOT NULL,
                version INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (context_id) REFERENCES training_contexts (id)
            )
        """)
        
        # Worker bot performance tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS worker_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker_id TEXT NOT NULL,
                task_type TEXT NOT NULL,
                success_rate REAL DEFAULT 0.0,
                context_understanding REAL DEFAULT 0.0,
                last_training_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        
    def ensure_training_directory(self):
        """Ensure training materials directory exists"""
        Path(self.training_dir).mkdir(parents=True, exist_ok=True)
        
    def create_dmlog_training_context(self) -> int:
        """Create the primary DMLog training context"""
        context_data = {
            "system_name": "DMLog Revolutionary",
            "current_focus": "D&D Beyond clone interface with ML observation and voice control",
            "key_requirements": [
                "Start with exact D&D Beyond interface - no revolutionary changes initially",
                "ML observes underneath - never interrupt user flow",
                "Voice controls everything - Max should feel natural using voice commands",
                "Interface adapts based on usage patterns and frustration detection",
                "Worker bots read notes in DMLog context only - not general system improvements",
                "Additional tabs for revolutionary features but main interface stays familiar",
                "Log management under 100MB with rollback capabilities",
                "Real-time interface smoothing based on ML observations"
            ],
            "forbidden_actions": [
                "Never make revolutionary interface changes without ML detecting need first",
                "Don't create new files unless absolutely necessary",
                "Never proactively create documentation unless requested",
                "Don't interrupt user workflow with ML notifications",
                "Avoid making changes that break D&D Beyond familiarity"
            ],
            "success_metrics": [
                "Max thinks he's using D&D Beyond initially",
                "Interface becomes smoother over time without user noticing transitions",
                "Voice commands work faster and more accurately over time",
                "Worker bot notes are understood in proper DMLog context",
                "Log size stays under 100MB",
                "User frustration patterns decrease over time"
            ]
        }
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO training_contexts 
            (context_name, system_focus, requirements, updated_at)
            VALUES (?, ?, ?, ?)
        """, (
            "DMLog_Primary_Context",
            "D&D Beyond clone with adaptive ML layer",
            json.dumps(context_data),
            datetime.now().isoformat()
        ))
        
        context_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return context_id
        
    def generate_worker_bot_briefing(self, worker_id: str) -> str:
        """Generate contextual briefing for a worker bot"""
        
        # Get DMLog context
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM training_contexts 
            WHERE context_name = 'DMLog_Primary_Context'
        """)
        
        context_row = cursor.fetchone()
        if not context_row:
            self.create_dmlog_training_context()
            return self.generate_worker_bot_briefing(worker_id)
            
        context_data = json.loads(context_row[3])
        
        # Get recent worker bot notes from DMLog adaptive system
        notes_db_path = "/tmp/dmlog_adaptive.db"
        if os.path.exists(notes_db_path):
            notes_conn = sqlite3.connect(notes_db_path)
            notes_cursor = notes_conn.cursor()
            
            notes_cursor.execute("""
                SELECT note_text, context_type, priority, created_at, status
                FROM worker_bot_notes
                WHERE status IN ('pending', 'in_progress')
                ORDER BY created_at DESC
                LIMIT 20
            """)
            
            recent_notes = notes_cursor.fetchall()
            notes_conn.close()
        else:
            recent_notes = []
        
        conn.close()
        
        # Generate comprehensive briefing
        briefing = f"""
# DMLog Worker Bot Training Briefing
**Worker ID**: {worker_id}
**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Context**: DMLog Revolutionary System

## PRIMARY MISSION
You are working EXCLUSIVELY on the DMLog system. When Max leaves notes or requests improvements, he is talking about DMLog features only, not the broader ActiveLog ecosystem.

## SYSTEM OVERVIEW
{context_data['system_name']} is designed to be a D&D Beyond clone that becomes superior through:
- **Starting Point**: Exact D&D Beyond interface (familiar to users)
- **Hidden Layer**: ML observation system that learns user patterns
- **Voice Control**: Max can control everything via voice commands
- **Adaptive Interface**: Interface becomes smoother based on usage patterns
- **Worker Communication**: Max can leave notes for worker bots like you

## CURRENT FOCUS
{context_data['current_focus']}

## KEY REQUIREMENTS (MUST FOLLOW)
"""
        
        for i, req in enumerate(context_data['key_requirements'], 1):
            briefing += f"{i}. {req}\n"
            
        briefing += f"""
## FORBIDDEN ACTIONS (NEVER DO)
"""
        for i, forbidden in enumerate(context_data['forbidden_actions'], 1):
            briefing += f"{i}. {forbidden}\n"
            
        briefing += f"""
## SUCCESS METRICS
"""
        for i, metric in enumerate(context_data['success_metrics'], 1):
            briefing += f"{i}. {metric}\n"
            
        if recent_notes:
            briefing += f"""
## RECENT NOTES FROM MAX (DMLog Context)
These notes are about DMLog improvements specifically:

"""
            for note in recent_notes:
                note_text, context_type, priority, created_at, status = note
                briefing += f"""
**[{priority.upper()} - {status.upper()}]** ({created_at})
Context: {context_type}
Note: {note_text}
---
"""
        
        briefing += f"""
## CONTEXT REMINDER
- When Max mentions "interface", he means the DMLog interface
- When Max mentions "system", he means the DMLog system  
- When Max mentions "features", he means DMLog features
- When Max mentions "users", he means DMLog users
- All improvements should be DMLog-specific unless explicitly stated otherwise

## ESCALATION PROTOCOL
If a suggestion from Max might benefit the entire ActiveLog ecosystem:
1. Implement the DMLog-specific version first
2. Leave a note in the escalation system for the admin
3. Continue focusing on DMLog improvements

Remember: You are a DMLog specialist. Your expertise is making DMLog the best D&D Beyond alternative possible.
"""
        
        return briefing
        
    def create_training_material(self, material_name: str, content: str, material_type: str) -> int:
        """Create a new training material"""
        context_id = self.create_dmlog_training_context()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO training_materials 
            (material_name, context_id, content, material_type)
            VALUES (?, ?, ?, ?)
        """, (material_name, context_id, content, material_type))
        
        material_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Save to file system
        file_path = os.path.join(self.training_dir, f"{material_name}.md")
        with open(file_path, 'w') as f:
            f.write(content)
            
        return material_id
        
    def update_worker_performance(self, worker_id: str, task_type: str, success_rate: float, context_understanding: float):
        """Track worker bot performance"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO worker_performance
            (worker_id, task_type, success_rate, context_understanding, last_training_update)
            VALUES (?, ?, ?, ?, ?)
        """, (worker_id, task_type, success_rate, context_understanding, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
    def get_training_recommendations(self, worker_id: str) -> List[str]:
        """Get personalized training recommendations for a worker bot"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT task_type, success_rate, context_understanding
            FROM worker_performance
            WHERE worker_id = ?
            ORDER BY last_training_update DESC
        """, (worker_id,))
        
        performance_data = cursor.fetchall()
        conn.close()
        
        recommendations = []
        
        for task_type, success_rate, context_understanding in performance_data:
            if success_rate < 0.8:
                recommendations.append(f"Improve {task_type} task execution (current: {success_rate:.1%})")
            if context_understanding < 0.9:
                recommendations.append(f"Review DMLog context for {task_type} tasks (current: {context_understanding:.1%})")
                
        if not recommendations:
            recommendations.append("Performance is excellent. Continue current approach.")
            
        return recommendations
        
    def generate_context_validation_test(self) -> Dict[str, Any]:
        """Generate test to validate worker bot understands DMLog context"""
        
        test_scenarios = [
            {
                "scenario": "Max says: 'Make the interface more intuitive'",
                "correct_understanding": "Improve DMLog interface based on ML observations, not revolutionary changes",
                "incorrect_understanding": "Completely redesign the interface to be revolutionary"
            },
            {
                "scenario": "Max says: 'Add better dice rolling'",
                "correct_understanding": "Improve DMLog dice system with physics simulation in additional tab",
                "incorrect_understanding": "Replace D&D Beyond's dice system in main interface"
            },
            {
                "scenario": "Max says: 'The system needs better search'",
                "correct_understanding": "Improve DMLog search functionality with AI-powered semantic search",
                "incorrect_understanding": "Improve search across all ActiveLog services"
            },
            {
                "scenario": "Max says: 'Users are frustrated with navigation'",
                "correct_understanding": "Use ML to detect DMLog navigation patterns and smooth interface",
                "incorrect_understanding": "Change the navigation structure immediately"
            }
        ]
        
        return {
            "test_name": "DMLog Context Understanding Test",
            "scenarios": test_scenarios,
            "passing_score": 0.85,
            "instructions": "For each scenario, identify which understanding demonstrates proper DMLog context awareness"
        }


def main():
    """Initialize training system and create base materials"""
    training_system = DMLogTrainingSystem()
    
    # Create primary training context
    context_id = training_system.create_dmlog_training_context()
    print(f"Created DMLog training context with ID: {context_id}")
    
    # Generate sample worker briefing
    sample_briefing = training_system.generate_worker_bot_briefing("claude-opus-dmlog-worker-001")
    
    # Save briefing as training material
    material_id = training_system.create_training_material(
        "DMLog_Worker_Bot_Briefing",
        sample_briefing,
        "briefing"
    )
    
    print(f"Generated training briefing (Material ID: {material_id})")
    print(f"Training materials saved to: {training_system.training_dir}")
    
    # Create context validation test
    validation_test = training_system.generate_context_validation_test()
    test_content = f"# {validation_test['test_name']}\n\n"
    test_content += f"**Passing Score**: {validation_test['passing_score']:.0%}\n\n"
    test_content += f"**Instructions**: {validation_test['instructions']}\n\n"
    
    for i, scenario in enumerate(validation_test['scenarios'], 1):
        test_content += f"## Scenario {i}\n"
        test_content += f"**Max says**: \"{scenario['scenario']}\"\n\n"
        test_content += f"**Correct Understanding**: {scenario['correct_understanding']}\n\n"
        test_content += f"**Incorrect Understanding**: {scenario['incorrect_understanding']}\n\n"
        test_content += "---\n\n"
    
    test_id = training_system.create_training_material(
        "DMLog_Context_Validation_Test",
        test_content,
        "validation_test"
    )
    
    print(f"Generated context validation test (Material ID: {test_id})")
    print("\nTraining system initialization complete!")
    print("\nWorker bots can now:")
    print("1. Get contextual briefings that understand DMLog scope")
    print("2. Access training materials focused on DMLog requirements")
    print("3. Take validation tests to ensure proper context understanding")
    print("4. Receive performance-based training recommendations")


if __name__ == "__main__":
    main()