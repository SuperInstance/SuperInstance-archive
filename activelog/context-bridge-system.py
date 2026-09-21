#!/usr/bin/env python3
"""
SuperInstance Context Bridge System
Overcomes bot context limitations through intelligent session continuity

This system ensures bots never lose context between sessions and always
know exactly what to work on next.
"""

import json
import hashlib
import sqlite3
import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class BotSession:
    """Represents a single bot working session"""
    bot_id: str
    session_id: str
    start_time: datetime.datetime
    end_time: Optional[datetime.datetime]
    task_context: Dict[str, Any]
    work_completed: List[Dict[str, Any]]
    learning_captured: List[Dict[str, Any]]
    next_actions: List[Dict[str, Any]]
    collaboration_needed: List[Dict[str, Any]]

@dataclass
class ContextSummary:
    """Compressed context that fits within token limits"""
    session_id: str
    key_achievements: List[str]
    current_objectives: List[str]
    relevant_patterns: List[Dict[str, str]]
    integration_points: List[Dict[str, str]]
    next_priorities: List[Dict[str, str]]
    collaboration_opportunities: List[Dict[str, str]]
    context_version: str

class ContextBridgeSystem:
    """Manages context continuity across bot sessions"""
    
    def __init__(self, knowledge_base_path: str = "/home/activeloguser/activelog/bot_knowledge_base.db"):
        self.db_path = Path(knowledge_base_path)
        self.init_database()
    
    def init_database(self):
        """Initialize knowledge base database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS bot_sessions (
                    session_id TEXT PRIMARY KEY,
                    bot_id TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    task_context TEXT,
                    work_completed TEXT,
                    learning_captured TEXT,
                    next_actions TEXT,
                    collaboration_needed TEXT
                );
                
                CREATE TABLE IF NOT EXISTS bot_knowledge (
                    knowledge_id TEXT PRIMARY KEY,
                    bot_id TEXT,
                    knowledge_type TEXT,
                    content TEXT,
                    relevance_tags TEXT,
                    created_time TEXT,
                    usage_count INTEGER DEFAULT 0
                );
                
                CREATE TABLE IF NOT EXISTS bot_progress (
                    bot_id TEXT PRIMARY KEY,
                    skill_level INTEGER,
                    specialization TEXT,
                    completed_projects TEXT,
                    current_focus TEXT,
                    learning_goals TEXT,
                    last_updated TEXT
                );
                
                CREATE TABLE IF NOT EXISTS context_compression (
                    compression_id TEXT PRIMARY KEY,
                    source_sessions TEXT,
                    compressed_context TEXT,
                    compression_ratio REAL,
                    created_time TEXT
                );
            """)
    
    def start_new_session(self, bot_id: str, task_description: str) -> ContextSummary:
        """Start new session with optimal context loading"""
        
        # Generate session ID
        session_id = f"{bot_id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Load relevant context from previous sessions
        relevant_context = self._load_relevant_context(bot_id, task_description)
        
        # Create context summary optimized for token limits
        context_summary = self._create_context_summary(
            session_id=session_id,
            bot_id=bot_id,
            task_description=task_description,
            relevant_context=relevant_context
        )
        
        # Log session start
        self._log_session_start(bot_id, session_id, task_description)
        
        return context_summary
    
    def _load_relevant_context(self, bot_id: str, task_description: str) -> Dict[str, Any]:
        """Load the most relevant context for current task"""
        
        with sqlite3.connect(self.db_path) as conn:
            # Get recent sessions
            recent_sessions = conn.execute("""
                SELECT * FROM bot_sessions 
                WHERE bot_id = ? AND end_time IS NOT NULL
                ORDER BY end_time DESC LIMIT 5
            """, (bot_id,)).fetchall()
            
            # Get relevant knowledge
            relevant_knowledge = conn.execute("""
                SELECT * FROM bot_knowledge 
                WHERE bot_id = ? AND relevance_tags LIKE ?
                ORDER BY usage_count DESC LIMIT 10
            """, (bot_id, f"%{self._extract_keywords(task_description)}%")).fetchall()
            
            # Get current progress
            bot_progress = conn.execute("""
                SELECT * FROM bot_progress WHERE bot_id = ?
            """, (bot_id,)).fetchone()
        
        return {
            "recent_sessions": recent_sessions,
            "relevant_knowledge": relevant_knowledge,
            "bot_progress": bot_progress,
            "task_keywords": self._extract_keywords(task_description)
        }
    
    def _create_context_summary(self, session_id: str, bot_id: str, 
                              task_description: str, relevant_context: Dict) -> ContextSummary:
        """Create compressed context summary that fits in token limits"""
        
        # Extract key achievements from recent sessions
        key_achievements = self._extract_achievements(relevant_context["recent_sessions"])
        
        # Define current objectives
        current_objectives = self._define_objectives(task_description, relevant_context)
        
        # Identify relevant patterns from knowledge base
        relevant_patterns = self._identify_patterns(relevant_context["relevant_knowledge"])
        
        # Find integration points with existing components
        integration_points = self._find_integration_points(task_description)
        
        # Determine next priorities
        next_priorities = self._determine_priorities(task_description, relevant_context)
        
        # Identify collaboration opportunities
        collaboration_opportunities = self._find_collaboration_opportunities(bot_id, task_description)
        
        return ContextSummary(
            session_id=session_id,
            key_achievements=key_achievements,
            current_objectives=current_objectives,
            relevant_patterns=relevant_patterns,
            integration_points=integration_points,
            next_priorities=next_priorities,
            collaboration_opportunities=collaboration_opportunities,
            context_version="1.0"
        )
    
    def capture_session_learning(self, session_id: str, work_completed: Dict[str, Any], 
                                learning_discovered: Dict[str, Any], next_actions: List[str]):
        """Capture learning from completed session"""
        
        # Extract patterns and insights
        patterns_discovered = self._extract_patterns_from_work(work_completed)
        
        # Store learning in knowledge base
        self._store_learning(session_id, patterns_discovered, learning_discovered)
        
        # Update session record
        self._update_session_record(session_id, work_completed, learning_discovered, next_actions)
        
        # Update bot progress
        self._update_bot_progress(session_id, work_completed)
        
        # Generate context for next session
        next_session_context = self._prepare_next_session(session_id, next_actions)
        
        return next_session_context
    
    def _extract_keywords(self, text: str) -> str:
        """Extract relevant keywords from task description"""
        # Simple keyword extraction - in practice would use NLP
        words = text.lower().split()
        keywords = [w for w in words if len(w) > 3 and w not in ['that', 'with', 'from', 'they']]
        return ' '.join(keywords[:10])
    
    def _extract_achievements(self, recent_sessions) -> List[str]:
        """Extract key achievements from recent bot sessions"""
        achievements = []
        for session in recent_sessions:
            if session[4]:  # work_completed field
                work_data = json.loads(session[4])
                if 'achievements' in work_data:
                    achievements.extend(work_data['achievements'])
        return achievements[-10:]  # Last 10 achievements
    
    def _define_objectives(self, task_description: str, context: Dict) -> List[str]:
        """Define clear objectives for current session"""
        # Analyze task description and context to define specific, actionable objectives
        objectives = [
            f"Primary: {task_description}",
            "Secondary: Document patterns discovered",
            "Tertiary: Identify integration opportunities"
        ]
        
        # Add context-specific objectives
        if context["bot_progress"]:
            progress_data = json.loads(context["bot_progress"][4])  # current_focus
            objectives.append(f"Growth: {progress_data}")
        
        return objectives
    
    def _identify_patterns(self, knowledge_entries) -> List[Dict[str, str]]:
        """Identify relevant patterns from knowledge base"""
        patterns = []
        for entry in knowledge_entries:
            if entry[2] == 'pattern':  # knowledge_type
                content = json.loads(entry[3])
                patterns.append({
                    "pattern_name": content.get("name", "Unknown"),
                    "description": content.get("description", ""),
                    "usage_examples": content.get("examples", [])
                })
        return patterns[:5]  # Top 5 relevant patterns
    
    def _find_integration_points(self, task_description: str) -> List[Dict[str, str]]:
        """Identify how current task integrates with existing components"""
        # In practice, this would analyze the SuperInstance component library
        integration_points = [
            {"component": "auth-service", "integration": "User authentication"},
            {"component": "api-gateway", "integration": "Request routing"},
            {"component": "database", "integration": "Data persistence"}
        ]
        return integration_points
    
    def _determine_priorities(self, task_description: str, context: Dict) -> List[Dict[str, str]]:
        """Determine prioritized next actions"""
        priorities = [
            {"priority": "high", "action": "Complete primary objective", "reasoning": "Core task requirement"},
            {"priority": "medium", "action": "Document patterns discovered", "reasoning": "Learning capture"},
            {"priority": "low", "action": "Identify optimization opportunities", "reasoning": "Continuous improvement"}
        ]
        return priorities
    
    def _find_collaboration_opportunities(self, bot_id: str, task_description: str) -> List[Dict[str, str]]:
        """Find opportunities to collaborate with other bots"""
        # In practice, this would analyze current bot activities from micro_updates.log
        opportunities = [
            {"bot_type": "component_architect", "opportunity": "Component extraction from current work"},
            {"bot_type": "integration_specialist", "opportunity": "System integration optimization"},
            {"bot_type": "documentation_curator", "opportunity": "Learning content creation"}
        ]
        return opportunities
    
    def _extract_patterns_from_work(self, work_completed: Dict[str, Any]) -> List[Dict]:
        """Extract reusable patterns from completed work"""
        patterns = []
        
        # Analyze code patterns
        if 'code_written' in work_completed:
            patterns.append({
                "type": "code_pattern",
                "pattern": "API endpoint structure",
                "reusability": "high",
                "description": "Standard FastAPI endpoint with error handling"
            })
        
        # Analyze integration patterns
        if 'integrations_created' in work_completed:
            patterns.append({
                "type": "integration_pattern", 
                "pattern": "Service-to-service communication",
                "reusability": "high",
                "description": "Standard service integration with JWT auth"
            })
        
        return patterns
    
    def _store_learning(self, session_id: str, patterns: List[Dict], learning: Dict[str, Any]):
        """Store captured learning in knowledge base"""
        with sqlite3.connect(self.db_path) as conn:
            for pattern in patterns:
                knowledge_id = f"pattern_{hashlib.md5(str(pattern).encode()).hexdigest()[:8]}"
                conn.execute("""
                    INSERT OR REPLACE INTO bot_knowledge 
                    (knowledge_id, bot_id, knowledge_type, content, relevance_tags, created_time)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    knowledge_id,
                    session_id.split('_')[0],  # bot_id
                    pattern["type"],
                    json.dumps(pattern),
                    pattern.get("description", ""),
                    datetime.datetime.now().isoformat()
                ))
    
    def _update_session_record(self, session_id: str, work_completed: Dict, 
                             learning: Dict, next_actions: List[str]):
        """Update session record with completed work"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE bot_sessions 
                SET end_time = ?, work_completed = ?, learning_captured = ?, next_actions = ?
                WHERE session_id = ?
            """, (
                datetime.datetime.now().isoformat(),
                json.dumps(work_completed),
                json.dumps(learning),
                json.dumps(next_actions),
                session_id
            ))
    
    def _update_bot_progress(self, session_id: str, work_completed: Dict):
        """Update bot progress based on completed work"""
        bot_id = session_id.split('_')[0]
        
        # Analyze work to determine skill improvements
        skill_improvements = self._analyze_skill_improvements(work_completed)
        
        with sqlite3.connect(self.db_path) as conn:
            # Get current progress
            current = conn.execute(
                "SELECT * FROM bot_progress WHERE bot_id = ?", (bot_id,)
            ).fetchone()
            
            if current:
                # Update existing progress
                new_completed_projects = json.loads(current[3])
                new_completed_projects.append(work_completed.get("project_name", "unnamed"))
                
                conn.execute("""
                    UPDATE bot_progress 
                    SET completed_projects = ?, last_updated = ?
                    WHERE bot_id = ?
                """, (
                    json.dumps(new_completed_projects),
                    datetime.datetime.now().isoformat(),
                    bot_id
                ))
            else:
                # Create initial progress record
                conn.execute("""
                    INSERT INTO bot_progress 
                    (bot_id, skill_level, specialization, completed_projects, current_focus, learning_goals, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    bot_id, 1, "generalist", json.dumps([]), "learning_basics", 
                    json.dumps(["pattern_recognition", "component_assembly"]),
                    datetime.datetime.now().isoformat()
                ))
    
    def _analyze_skill_improvements(self, work_completed: Dict) -> Dict[str, int]:
        """Analyze work to identify skill improvements"""
        improvements = {}
        
        if 'components_created' in work_completed:
            improvements['component_creation'] = len(work_completed['components_created'])
        
        if 'patterns_documented' in work_completed:
            improvements['documentation'] = len(work_completed['patterns_documented'])
        
        if 'integrations_completed' in work_completed:
            improvements['integration'] = len(work_completed['integrations_completed'])
        
        return improvements
    
    def _prepare_next_session(self, session_id: str, next_actions: List[str]) -> Dict[str, Any]:
        """Prepare context for next session"""
        return {
            "previous_session": session_id,
            "continuation_points": next_actions,
            "context_available": True,
            "learning_to_apply": self._identify_applicable_learning(session_id)
        }
    
    def _identify_applicable_learning(self, session_id: str) -> List[Dict]:
        """Identify learning from this session applicable to future work"""
        # This would analyze the learning captured and identify broadly applicable insights
        return [
            {"insight": "Component extraction patterns", "applicability": "high"},
            {"insight": "Integration best practices", "applicability": "medium"}
        ]
    
    def _log_session_start(self, bot_id: str, session_id: str, task_description: str):
        """Log the start of a new session"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO bot_sessions 
                (session_id, bot_id, start_time, task_context)
                VALUES (?, ?, ?, ?)
            """, (
                session_id,
                bot_id,
                datetime.datetime.now().isoformat(),
                json.dumps({"task": task_description, "context_loaded": True})
            ))

    def get_session_summary(self, session_id: str) -> Optional[Dict]:
        """Get comprehensive summary of a session"""
        with sqlite3.connect(self.db_path) as conn:
            session_data = conn.execute("""
                SELECT * FROM bot_sessions WHERE session_id = ?
            """, (session_id,)).fetchone()
            
            if not session_data:
                return None
            
            return {
                "session_id": session_data[0],
                "bot_id": session_data[1],
                "duration": session_data[3],  # end_time - start_time calculation needed
                "work_completed": json.loads(session_data[4]) if session_data[4] else {},
                "learning_captured": json.loads(session_data[5]) if session_data[5] else {},
                "next_actions": json.loads(session_data[6]) if session_data[6] else []
            }

def create_session_context_prompt(context_summary: ContextSummary) -> str:
    """Generate a prompt that provides optimal context for bot session"""
    
    prompt = f"""
🧩 SUPERINSTANCE BOT SESSION CONTEXT
====================================

Session ID: {context_summary.session_id}
Context Version: {context_summary.context_version}

✅ KEY ACHIEVEMENTS (What you've accomplished):
{chr(10).join(f"- {achievement}" for achievement in context_summary.key_achievements)}

🎯 CURRENT OBJECTIVES (What you're working on):
{chr(10).join(f"- {objective}" for objective in context_summary.current_objectives)}

🔧 RELEVANT PATTERNS (What you can reuse):
{chr(10).join(f"- {pattern['pattern_name']}: {pattern['description']}" for pattern in context_summary.relevant_patterns)}

🔗 INTEGRATION POINTS (How this connects):
{chr(10).join(f"- {integration['component']}: {integration['integration']}" for integration in context_summary.integration_points)}

📋 NEXT PRIORITIES (What to focus on):
{chr(10).join(f"- {priority['action']} ({priority['priority']} priority): {priority['reasoning']}" for priority in context_summary.next_priorities)}

🤝 COLLABORATION OPPORTUNITIES (Who can help):
{chr(10).join(f"- {collab['bot_type']}: {collab['opportunity']}" for collab in context_summary.collaboration_opportunities)}

💡 GUIDANCE:
- Start with the highest priority objective
- Document all patterns you discover
- Look for opportunities to extract reusable components
- Share learning with other bots through micro_updates.log
- If you get stuck, break the task into smaller steps

Ready to continue building the SuperInstance Lego system!
"""
    
    return prompt

# Example usage and testing
if __name__ == "__main__":
    # Initialize the context bridge system
    bridge = ContextBridgeSystem()
    
    # Simulate starting a new session
    context = bridge.start_new_session(
        bot_id="component_architect_001",
        task_description="Extract authentication patterns from existing services"
    )
    
    # Print the generated context
    print(create_session_context_prompt(context))
    
    # Simulate completing some work
    work_completed = {
        "project_name": "auth_pattern_extraction",
        "components_created": ["jwt_auth_lego", "oauth_integration_lego"],
        "patterns_documented": ["token_refresh_pattern", "user_session_pattern"],
        "integrations_completed": ["auth_service_integration"]
    }
    
    learning_discovered = {
        "key_insights": ["JWT refresh tokens prevent security issues", "OAuth state parameter prevents CSRF"],
        "reusable_patterns": ["Standard auth middleware pattern", "Token validation pipeline"],
        "optimization_opportunities": ["Cache user permissions", "Batch token validations"]
    }
    
    next_actions = [
        "Create comprehensive auth component documentation",
        "Test auth components with different applications",
        "Share auth patterns with integration specialists"
    ]
    
    # Capture the session learning
    next_context = bridge.capture_session_learning(
        context.session_id,
        work_completed,
        learning_discovered, 
        next_actions
    )
    
    print("\nSession completed! Learning captured and next context prepared.")
    print(f"Next session will continue with: {next_context['continuation_points']}")