#!/usr/bin/env python3
"""
Visual Behavior Learning System
Tracks user responses to generated images and uses Claude to improve prompt engineering
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import hashlib
from dataclasses import dataclass
import asyncio

@dataclass
class VisualInteraction:
    user_id: str
    original_prompt: str
    generated_image_url: str
    model_used: str
    generation_params: Dict
    user_response: str  # "liked", "disliked", "modified", "regenerated", etc.
    time_spent_viewing: float  # seconds
    user_feedback: str  # text feedback if provided
    interaction_timestamp: datetime
    follow_up_action: str  # what user did next

class VisualBehaviorLearner:
    def __init__(self):
        self.db_path = "/tmp/visual_behavior_learner.db"
        self.init_database()
        
        # Learning thresholds
        self.batch_size = 20  # Process 20 interactions at once
        self.learning_threshold = 50  # Start learning after 50 interactions
        self.improvement_confidence = 0.8  # Confidence threshold for applying improvements
        
        # Behavior tracking
        self.active_sessions = {}  # Track users currently viewing images
        
    def init_database(self):
        """Initialize visual behavior learning database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # User visual interactions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS visual_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                session_id TEXT,
                original_prompt TEXT,
                improved_prompt TEXT,
                generated_image_url TEXT,
                model_used TEXT,
                generation_params TEXT,
                user_response TEXT,
                time_spent_viewing REAL,
                user_feedback TEXT,
                follow_up_action TEXT,
                emotional_response TEXT,
                quality_rating INTEGER,
                interaction_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Learned prompt improvements
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prompt_improvements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_prompt_pattern TEXT,
                improved_prompt_pattern TEXT,
                improvement_type TEXT,
                success_rate REAL,
                usage_count INTEGER DEFAULT 0,
                claude_reasoning TEXT,
                confidence_score REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_used DATETIME
            )
        """)
        
        # Batch learning sessions with Claude
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS claude_learning_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT,
                interactions_analyzed INTEGER,
                patterns_discovered TEXT,
                improvements_generated TEXT,
                claude_insights TEXT,
                performance_prediction TEXT,
                session_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # User behavior profiles
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_visual_profiles (
                user_id TEXT PRIMARY KEY,
                preferred_styles TEXT,
                disliked_elements TEXT,
                typical_viewing_time REAL,
                engagement_patterns TEXT,
                improvement_suggestions TEXT,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        print("✅ Visual Behavior Learner database initialized")

    def start_image_viewing_session(self, user_id: str, prompt: str, image_url: str, 
                                   model: str, params: Dict) -> str:
        """Start tracking when user begins viewing an image"""
        session_id = f"visual_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id[:8]}"
        
        self.active_sessions[session_id] = {
            "user_id": user_id,
            "prompt": prompt,
            "image_url": image_url,
            "model": model,
            "params": params,
            "start_time": datetime.now(),
            "interactions": []
        }
        
        return session_id

    def record_user_reaction(self, session_id: str, reaction_type: str, 
                           feedback: str = "", quality_rating: int = None):
        """Record user's immediate reaction to generated image"""
        if session_id not in self.active_sessions:
            return
        
        session = self.active_sessions[session_id]
        viewing_time = (datetime.now() - session["start_time"]).total_seconds()
        
        # Determine emotional response based on reaction type and timing
        emotional_response = self.infer_emotional_response(reaction_type, viewing_time, feedback)
        
        # Record interaction
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO visual_interactions
            (user_id, session_id, original_prompt, generated_image_url, model_used,
             generation_params, user_response, time_spent_viewing, user_feedback,
             emotional_response, quality_rating, follow_up_action)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"], session_id, session["prompt"], session["image_url"],
            session["model"], json.dumps(session["params"]), reaction_type,
            viewing_time, feedback, emotional_response, quality_rating, ""
        ))
        
        conn.commit()
        conn.close()
        
        # Check if we should trigger batch learning
        self.check_batch_learning_trigger()

    def infer_emotional_response(self, reaction_type: str, viewing_time: float, 
                                feedback: str) -> str:
        """Infer emotional response from behavior"""
        if viewing_time < 2:
            return "immediate_dislike"
        elif viewing_time > 10 and reaction_type == "liked":
            return "strong_positive"
        elif "amazing" in feedback.lower() or "love" in feedback.lower():
            return "enthusiasm"
        elif "terrible" in feedback.lower() or "hate" in feedback.lower():
            return "strong_negative"
        elif reaction_type == "regenerated":
            return "dissatisfaction"
        elif reaction_type == "modified":
            return "partial_satisfaction"
        else:
            return "neutral"

    def record_follow_up_action(self, session_id: str, action: str):
        """Record what user did after viewing image"""
        if session_id in self.active_sessions:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE visual_interactions 
                SET follow_up_action = ?
                WHERE session_id = ?
            """, (action, session_id))
            
            conn.commit()
            conn.close()
            
            # Clean up session
            del self.active_sessions[session_id]

    def check_batch_learning_trigger(self):
        """Check if we should trigger Claude batch learning"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Count unprocessed interactions
        cursor.execute("""
            SELECT COUNT(*) FROM visual_interactions 
            WHERE id NOT IN (
                SELECT COALESCE(MAX(id), 0) FROM claude_learning_sessions
            )
        """)
        
        unprocessed_count = cursor.fetchone()[0]
        conn.close()
        
        if unprocessed_count >= self.batch_size:
            # Trigger batch learning asynchronously
            asyncio.create_task(self.run_claude_batch_learning())

    async def run_claude_batch_learning(self):
        """Use Claude to analyze batch of interactions and learn patterns"""
        try:
            # Get recent interactions for analysis
            interactions = self.get_unprocessed_interactions()
            
            if len(interactions) < self.batch_size:
                return
            
            # Build Claude prompt for batch learning
            prompt = self.build_batch_learning_prompt(interactions)
            
            # Import here to avoid circular imports
            from superinstance_api_manager import get_api_manager
            api_manager = get_api_manager()
            
            result = await api_manager.make_api_request(
                "claude",
                {
                    "prompt": prompt,
                    "max_tokens": 4000,
                    "model": "claude-3-5-sonnet-latest"
                },
                "visual_learner",
                "system"
            )
            
            if result.get("success"):
                # Parse Claude's learning insights
                insights = self.parse_claude_learning_response(result["response"])
                
                # Apply learned improvements
                self.apply_learned_improvements(insights, interactions)
                
                # Record learning session
                self.record_learning_session(len(interactions), insights)
                
                print(f"🎨 Visual AI learned from {len(interactions)} interactions")
                print(f"   Patterns discovered: {len(insights.get('patterns', []))}")
                print(f"   Improvements generated: {len(insights.get('improvements', []))}")
            
        except Exception as e:
            print(f"Batch learning error: {e}")

    def build_batch_learning_prompt(self, interactions: List[Dict]) -> str:
        """Build Claude prompt for analyzing user behavior patterns"""
        prompt = f"""You are a Visual AI Learning System. Analyze these {len(interactions)} user interactions with generated images to discover patterns and improve prompt engineering.

## Your Task:
1. Identify patterns in successful vs unsuccessful image generations
2. Discover what prompt elements lead to positive user responses
3. Generate improved prompt templates based on user behavior
4. Predict what changes will improve user satisfaction

## Interaction Data:
"""
        
        for i, interaction in enumerate(interactions, 1):
            prompt += f"""
Interaction {i}:
- Original Prompt: "{interaction['original_prompt']}"
- User Response: {interaction['user_response']}
- Viewing Time: {interaction['time_spent_viewing']:.1f} seconds
- Emotional Response: {interaction['emotional_response']}
- Feedback: "{interaction['user_feedback']}"
- Follow-up Action: {interaction['follow_up_action']}
- Quality Rating: {interaction['quality_rating']}/10
"""
        
        prompt += """
## Analysis Instructions:
Analyze these patterns and provide insights in this EXACT format:

PATTERNS_DISCOVERED:
{
  "successful_prompts": ["pattern 1", "pattern 2"],
  "unsuccessful_prompts": ["pattern 1", "pattern 2"], 
  "user_preferences": ["preference 1", "preference 2"],
  "timing_insights": ["insight 1", "insight 2"],
  "emotional_triggers": ["trigger 1", "trigger 2"]
}

PROMPT_IMPROVEMENTS:
{
  "improvement_1": {
    "original_pattern": "common failing pattern",
    "improved_pattern": "optimized version",
    "reasoning": "why this will work better",
    "confidence": 0.85
  },
  "improvement_2": {
    "original_pattern": "another pattern",
    "improved_pattern": "improved version", 
    "reasoning": "explanation",
    "confidence": 0.92
  }
}

BEHAVIORAL_INSIGHTS:
{
  "viewing_time_correlation": "what viewing time indicates",
  "satisfaction_predictors": ["predictor 1", "predictor 2"],
  "improvement_recommendations": ["rec 1", "rec 2"],
  "success_rate_prediction": "expected improvement percentage"
}

Begin your analysis:
"""
        
        return prompt

    def get_unprocessed_interactions(self) -> List[Dict]:
        """Get interactions that haven't been processed by Claude yet"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM visual_interactions 
            WHERE id > COALESCE((
                SELECT MAX(interactions_analyzed) FROM claude_learning_sessions
            ), 0)
            ORDER BY interaction_timestamp DESC
            LIMIT ?
        """, (self.batch_size,))
        
        results = cursor.fetchall()
        conn.close()
        
        interactions = []
        for row in results:
            interactions.append({
                "id": row[0],
                "user_id": row[1],
                "session_id": row[2],
                "original_prompt": row[3],
                "improved_prompt": row[4],
                "generated_image_url": row[5],
                "model_used": row[6],
                "generation_params": json.loads(row[7]) if row[7] else {},
                "user_response": row[8],
                "time_spent_viewing": row[9],
                "user_feedback": row[10] or "",
                "follow_up_action": row[11] or "",
                "emotional_response": row[12] or "",
                "quality_rating": row[13] or 5
            })
        
        return interactions

    def parse_claude_learning_response(self, response: str) -> Dict[str, Any]:
        """Parse Claude's structured learning response"""
        try:
            insights = {
                "patterns": {},
                "improvements": {},
                "behavioral_insights": {}
            }
            
            # Extract JSON sections from response
            sections = ["PATTERNS_DISCOVERED:", "PROMPT_IMPROVEMENTS:", "BEHAVIORAL_INSIGHTS:"]
            current_section = None
            current_content = []
            
            for line in response.split('\n'):
                if any(section in line for section in sections):
                    # Process previous section
                    if current_section and current_content:
                        section_key = current_section.replace(":", "").replace("_", "").lower()
                        try:
                            insights[section_key] = json.loads('\n'.join(current_content))
                        except:
                            insights[section_key] = {"raw": '\n'.join(current_content)}
                    
                    # Start new section
                    current_section = next((s for s in sections if s in line), None)
                    current_content = []
                elif current_section:
                    current_content.append(line)
            
            # Process final section
            if current_section and current_content:
                section_key = current_section.replace(":", "").replace("_", "").lower()
                try:
                    insights[section_key] = json.loads('\n'.join(current_content))
                except:
                    insights[section_key] = {"raw": '\n'.join(current_content)}
            
            return insights
            
        except Exception as e:
            print(f"Failed to parse Claude learning response: {e}")
            return {"patterns": {}, "improvements": {}, "behavioral_insights": {}}

    def apply_learned_improvements(self, insights: Dict[str, Any], interactions: List[Dict]):
        """Apply Claude's learned improvements to the system"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Store prompt improvements
        improvements = insights.get("improvements", {})
        for improvement_id, improvement in improvements.items():
            if isinstance(improvement, dict) and "confidence" in improvement:
                cursor.execute("""
                    INSERT INTO prompt_improvements
                    (original_prompt_pattern, improved_prompt_pattern, improvement_type,
                     claude_reasoning, confidence_score)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    improvement.get("original_pattern", ""),
                    improvement.get("improved_pattern", ""),
                    "claude_learning",
                    improvement.get("reasoning", ""),
                    improvement.get("confidence", 0.5)
                ))
        
        conn.commit()
        conn.close()

    def record_learning_session(self, interactions_count: int, insights: Dict[str, Any]):
        """Record Claude learning session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        batch_id = f"learn_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        cursor.execute("""
            INSERT INTO claude_learning_sessions
            (batch_id, interactions_analyzed, patterns_discovered, 
             improvements_generated, claude_insights, performance_prediction)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            batch_id, interactions_count,
            json.dumps(insights.get("patterns", {})),
            json.dumps(insights.get("improvements", {})),
            json.dumps(insights.get("behavioral_insights", {})),
            insights.get("behavioral_insights", {}).get("success_rate_prediction", "Unknown")
        ))
        
        conn.commit()
        conn.close()

    def get_improved_prompt(self, original_prompt: str, user_id: str) -> Tuple[str, float]:
        """Get improved prompt based on learned patterns"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Find matching improvements
        cursor.execute("""
            SELECT improved_prompt_pattern, confidence_score, claude_reasoning
            FROM prompt_improvements
            WHERE confidence_score >= ? AND (
                original_prompt_pattern = ? OR
                ? LIKE '%' || original_prompt_pattern || '%'
            )
            ORDER BY confidence_score DESC, usage_count DESC
            LIMIT 1
        """, (self.improvement_confidence, original_prompt, original_prompt))
        
        result = cursor.fetchone()
        
        if result:
            # Update usage count
            cursor.execute("""
                UPDATE prompt_improvements 
                SET usage_count = usage_count + 1, last_used = ?
                WHERE improved_prompt_pattern = ?
            """, (datetime.now(), result[0]))
            
            conn.commit()
            conn.close()
            
            return result[0], result[1]
        
        conn.close()
        return original_prompt, 0.0

    def get_learning_analytics(self) -> Dict[str, Any]:
        """Get analytics on visual behavior learning"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Learning progress
        cursor.execute("""
            SELECT COUNT(*) as total_interactions,
                   AVG(quality_rating) as avg_quality,
                   COUNT(DISTINCT user_id) as unique_users
            FROM visual_interactions
        """)
        
        stats = cursor.fetchone()
        
        # Learning sessions
        cursor.execute("""
            SELECT COUNT(*), AVG(interactions_analyzed)
            FROM claude_learning_sessions
        """)
        
        learning_stats = cursor.fetchone()
        
        # Improvement success rate
        cursor.execute("""
            SELECT COUNT(*), AVG(confidence_score)
            FROM prompt_improvements
            WHERE confidence_score >= ?
        """, (self.improvement_confidence,))
        
        improvement_stats = cursor.fetchone()
        
        conn.close()
        
        return {
            "total_interactions": stats[0] if stats else 0,
            "average_quality_rating": stats[1] if stats and stats[1] else 0,
            "unique_users": stats[2] if stats else 0,
            "learning_sessions": learning_stats[0] if learning_stats else 0,
            "avg_batch_size": learning_stats[1] if learning_stats and learning_stats[1] else 0,
            "active_improvements": improvement_stats[0] if improvement_stats else 0,
            "avg_improvement_confidence": improvement_stats[1] if improvement_stats and improvement_stats[1] else 0,
            "learning_features": [
                "Real-time behavior tracking",
                "Claude-powered pattern recognition",
                "Automatic prompt optimization",
                "Emotional response analysis",
                "Batch learning from user interactions"
            ]
        }

# Global visual behavior learner instance
visual_behavior_learner = VisualBehaviorLearner()

def get_visual_behavior_learner() -> VisualBehaviorLearner:
    """Get the global visual behavior learner instance"""
    return visual_behavior_learner