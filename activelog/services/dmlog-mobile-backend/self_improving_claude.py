#!/usr/bin/env python3
"""
Self-Improving Claude System
Claude generates both responses AND updates its own "weights" to improve performance
"""

import json
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import hashlib
from claude_ml_interpreters import get_claude_ml_interpreters

class SelfImprovingClaude:
    def __init__(self):
        self.db_path = "/tmp/self_improving_claude.db"
        self.ml_interpreters = get_claude_ml_interpreters()
        self.init_database()
        
        # Self-improvement configuration
        self.improvement_threshold = 10  # Update weights after 10 interactions
        self.max_weight_history = 100   # Keep last 100 weight updates
        self.learning_rate = 0.1        # How much to adjust weights

    def init_database(self):
        """Initialize self-improving Claude database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Model weights/patterns that Claude updates about itself
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS claude_weights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                interpreter_name TEXT,
                weight_type TEXT,
                weight_data TEXT,
                performance_score REAL,
                usage_count INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 1.0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Self-improvement interactions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS improvement_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                interpreter_name TEXT,
                input_hash TEXT,
                user_feedback_score REAL,
                response_quality REAL,
                weights_before TEXT,
                weights_after TEXT,
                improvement_delta REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Performance tracking per interpreter
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interpreter_performance (
                interpreter_name TEXT PRIMARY KEY,
                total_requests INTEGER DEFAULT 0,
                successful_requests INTEGER DEFAULT 0,
                average_quality REAL DEFAULT 0.0,
                improvement_velocity REAL DEFAULT 0.0,
                last_improvement DATETIME,
                current_weights TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        print("✅ Self-Improving Claude database initialized")

    def build_self_improving_prompt(self, interpreter_name: str, input_data: Any, 
                                   current_weights: Dict = None) -> str:
        """Build prompt that makes Claude both respond AND improve itself"""
        
        # Get base template
        template = self.ml_interpreters.interpreter_templates.get(interpreter_name)
        if not template:
            return "Invalid interpreter"
        
        # Get current performance data
        performance = self.get_interpreter_performance(interpreter_name)
        recent_patterns = self.get_recent_successful_patterns(interpreter_name, limit=5)
        
        # Build the self-improving prompt
        prompt = f"""You are a self-improving AI system. Your task is to:
1. Provide an excellent response to the user's request
2. Update your own "weights" (patterns/rules) to improve future performance

## Current Role: {template['name']}
{template['prompt']}

## Your Current Performance Metrics:
- Total requests handled: {performance.get('total_requests', 0)}
- Success rate: {performance.get('success_rate', 100):.1f}%
- Average quality score: {performance.get('average_quality', 0):.2f}/10
- Last improvement: {performance.get('last_improvement', 'Never')}

## Current Weights (Your learned patterns):
{json.dumps(current_weights or {}, indent=2)}

## Recent Successful Patterns:
{self.format_recent_patterns(recent_patterns)}

## User Input:
{json.dumps(input_data) if isinstance(input_data, dict) else str(input_data)}

## Instructions:
1. First, analyze the input using your current weights and patterns
2. Provide the best possible response to the user
3. Then, based on this interaction, update your weights to improve future performance

## Response Format:
Please respond in this EXACT format:

USER_RESPONSE:
[Your response to the user's request - make this excellent]

WEIGHT_UPDATE:
{{
  "pattern_learned": "[What pattern did you identify in this request?]",
  "weight_changes": {{
    "[weight_name]": {{
      "old_value": "[current value]",
      "new_value": "[improved value]", 
      "reason": "[why this improvement helps]"
    }}
  }},
  "new_patterns": {{
    "[pattern_name]": "[pattern rule or template]"
  }},
  "performance_prediction": "[How will this improve future responses?]",
  "confidence": [0.1-1.0 confidence in this improvement]
}}

QUALITY_ASSESSMENT:
{{
  "response_quality": [1-10 your assessment of response quality],
  "improvement_applied": [true/false - did you use previous learnings?],
  "learning_opportunity": "[What could be learned from this interaction?]"
}}

Begin your response now:
"""
        return prompt

    def get_interpreter_performance(self, interpreter_name: str) -> Dict[str, Any]:
        """Get current performance metrics for interpreter"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT total_requests, successful_requests, average_quality, 
                   improvement_velocity, last_improvement, current_weights
            FROM interpreter_performance WHERE interpreter_name = ?
        """, (interpreter_name,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "total_requests": result[0],
                "successful_requests": result[1],
                "success_rate": (result[1] / result[0] * 100) if result[0] > 0 else 100,
                "average_quality": result[2],
                "improvement_velocity": result[3],
                "last_improvement": result[4],
                "current_weights": json.loads(result[5]) if result[5] else {}
            }
        else:
            return {"total_requests": 0, "successful_requests": 0, "success_rate": 100, 
                   "average_quality": 0, "current_weights": {}}

    def get_recent_successful_patterns(self, interpreter_name: str, limit: int = 5) -> List[Dict]:
        """Get recent successful interaction patterns"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT weights_before, weights_after, improvement_delta, user_feedback_score
            FROM improvement_interactions 
            WHERE interpreter_name = ? AND user_feedback_score >= 8.0
            ORDER BY timestamp DESC LIMIT ?
        """, (interpreter_name, limit))
        
        results = cursor.fetchall()
        conn.close()
        
        patterns = []
        for result in results:
            patterns.append({
                "weights_before": json.loads(result[0]) if result[0] else {},
                "weights_after": json.loads(result[1]) if result[1] else {},
                "improvement_delta": result[2],
                "feedback_score": result[3]
            })
        
        return patterns

    def format_recent_patterns(self, patterns: List[Dict]) -> str:
        """Format recent patterns for prompt inclusion"""
        if not patterns:
            return "No recent successful patterns available."
        
        formatted = "Recent high-performing interactions:\n"
        for i, pattern in enumerate(patterns, 1):
            formatted += f"{i}. Feedback Score: {pattern['feedback_score']:.1f}/10\n"
            if pattern['weights_after']:
                formatted += f"   Successful pattern: {pattern['weights_after']}\n"
        
        return formatted

    async def self_improving_request(self, interpreter_name: str, input_data: Any, 
                                   user_id: str, tenant_id: str = "default") -> Dict[str, Any]:
        """Process request with self-improvement"""
        
        # Get current weights
        performance = self.get_interpreter_performance(interpreter_name)
        current_weights = performance.get("current_weights", {})
        
        # Build self-improving prompt
        prompt = self.build_self_improving_prompt(interpreter_name, input_data, current_weights)
        
        try:
            # Call Claude with self-improving prompt
            result = await self.ml_interpreters.api_manager.make_api_request(
                "claude",
                {
                    "prompt": prompt,
                    "max_tokens": 3000,
                    "model": "claude-3-5-sonnet-latest"  # Use latest model
                },
                user_id,
                tenant_id
            )
            
            if result.get("success"):
                # Parse the structured response
                parsed = self.parse_self_improving_response(result["response"])
                
                if parsed["success"]:
                    # Update weights in database
                    self.update_interpreter_weights(
                        interpreter_name, 
                        current_weights,
                        parsed["weight_update"],
                        parsed["quality_assessment"]
                    )
                    
                    # Track the improvement interaction
                    self.track_improvement_interaction(
                        interpreter_name, input_data, current_weights,
                        parsed["weight_update"], parsed["quality_assessment"]
                    )
                    
                    return {
                        "success": True,
                        "response": parsed["user_response"],
                        "self_improvement": {
                            "weights_updated": True,
                            "patterns_learned": parsed["weight_update"].get("pattern_learned"),
                            "confidence": parsed["weight_update"].get("confidence", 0),
                            "predicted_improvement": parsed["weight_update"].get("performance_prediction")
                        },
                        "quality_metrics": parsed["quality_assessment"],
                        "cost": result.get("cost", 0.015),
                        "interpreter": interpreter_name
                    }
                else:
                    # Fallback to regular response
                    return {
                        "success": True,
                        "response": result["response"],
                        "self_improvement": {"weights_updated": False, "error": "Failed to parse improvement data"},
                        "cost": result.get("cost", 0.015)
                    }
            else:
                return result
                
        except Exception as e:
            return {"success": False, "error": f"Self-improving request failed: {str(e)}"}

    def parse_self_improving_response(self, response: str) -> Dict[str, Any]:
        """Parse Claude's structured self-improving response"""
        try:
            # Look for the structured sections
            sections = {
                "user_response": "",
                "weight_update": {},
                "quality_assessment": {}
            }
            
            lines = response.split('\n')
            current_section = None
            current_content = []
            
            for line in lines:
                if line.strip().startswith("USER_RESPONSE:"):
                    if current_section and current_content:
                        sections[current_section] = self.process_section_content(current_section, current_content)
                    current_section = "user_response"
                    current_content = []
                elif line.strip().startswith("WEIGHT_UPDATE:"):
                    if current_section and current_content:
                        sections[current_section] = self.process_section_content(current_section, current_content)
                    current_section = "weight_update"
                    current_content = []
                elif line.strip().startswith("QUALITY_ASSESSMENT:"):
                    if current_section and current_content:
                        sections[current_section] = self.process_section_content(current_section, current_content)
                    current_section = "quality_assessment"
                    current_content = []
                elif current_section:
                    current_content.append(line)
            
            # Process final section
            if current_section and current_content:
                sections[current_section] = self.process_section_content(current_section, current_content)
            
            return {
                "success": True,
                "user_response": sections["user_response"],
                "weight_update": sections["weight_update"],
                "quality_assessment": sections["quality_assessment"]
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to parse response: {str(e)}"}

    def process_section_content(self, section_type: str, content_lines: List[str]) -> Any:
        """Process content for each section type"""
        content = '\n'.join(content_lines).strip()
        
        if section_type == "user_response":
            return content
        elif section_type in ["weight_update", "quality_assessment"]:
            try:
                # Try to parse as JSON
                return json.loads(content)
            except:
                # If JSON parsing fails, return as string
                return {"raw_content": content}
        else:
            return content

    def update_interpreter_weights(self, interpreter_name: str, old_weights: Dict, 
                                 weight_update: Dict, quality_assessment: Dict):
        """Update interpreter weights in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Merge old weights with updates
        new_weights = old_weights.copy()
        
        # Apply weight changes
        if "weight_changes" in weight_update:
            for weight_name, change in weight_update["weight_changes"].items():
                new_weights[weight_name] = change.get("new_value", change.get("old_value"))
        
        # Add new patterns
        if "new_patterns" in weight_update:
            if "patterns" not in new_weights:
                new_weights["patterns"] = {}
            new_weights["patterns"].update(weight_update["new_patterns"])
        
        # Update performance metrics
        cursor.execute("""
            INSERT OR REPLACE INTO interpreter_performance
            (interpreter_name, total_requests, successful_requests, average_quality,
             improvement_velocity, last_improvement, current_weights)
            VALUES (?, 
                COALESCE((SELECT total_requests FROM interpreter_performance WHERE interpreter_name = ?), 0) + 1,
                COALESCE((SELECT successful_requests FROM interpreter_performance WHERE interpreter_name = ?), 0) + 1,
                ?,
                ?,
                ?,
                ?)
        """, (
            interpreter_name, interpreter_name, interpreter_name,
            quality_assessment.get("response_quality", 5),
            weight_update.get("confidence", 0.5),
            datetime.now(),
            json.dumps(new_weights)
        ))
        
        conn.commit()
        conn.close()

    def track_improvement_interaction(self, interpreter_name: str, input_data: Any,
                                    weights_before: Dict, weight_update: Dict, 
                                    quality_assessment: Dict):
        """Track this improvement interaction"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        input_hash = hashlib.sha256(str(input_data).encode()).hexdigest()[:16]
        
        cursor.execute("""
            INSERT INTO improvement_interactions
            (interpreter_name, input_hash, user_feedback_score, response_quality,
             weights_before, weights_after, improvement_delta)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            interpreter_name,
            input_hash, 
            quality_assessment.get("response_quality", 5),
            quality_assessment.get("response_quality", 5),
            json.dumps(weights_before),
            json.dumps(weight_update),
            weight_update.get("confidence", 0.5)
        ))
        
        conn.commit()
        conn.close()

    def get_improvement_analytics(self, interpreter_name: str = None) -> Dict[str, Any]:
        """Get self-improvement analytics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if interpreter_name:
            cursor.execute("""
                SELECT COUNT(*), AVG(improvement_delta), AVG(user_feedback_score)
                FROM improvement_interactions WHERE interpreter_name = ?
            """, (interpreter_name,))
        else:
            cursor.execute("""
                SELECT COUNT(*), AVG(improvement_delta), AVG(user_feedback_score)
                FROM improvement_interactions
            """)
        
        result = cursor.fetchone()
        
        # Get performance trends
        cursor.execute("""
            SELECT interpreter_name, total_requests, average_quality, improvement_velocity
            FROM interpreter_performance
            ORDER BY improvement_velocity DESC
        """)
        
        performance_data = cursor.fetchall()
        conn.close()
        
        return {
            "total_improvements": result[0] if result else 0,
            "average_improvement_delta": result[1] if result and result[1] else 0,
            "average_feedback_score": result[2] if result and result[2] else 0,
            "interpreter_performance": [
                {
                    "name": row[0],
                    "requests": row[1], 
                    "quality": row[2],
                    "improvement_rate": row[3]
                }
                for row in performance_data
            ],
            "improvement_features": [
                "Claude updates its own weights after each interaction",
                "Learns patterns and rules from successful responses", 
                "Self-assesses response quality and confidence",
                "Builds knowledge base that improves over time",
                "Reduces costs as patterns become more efficient"
            ]
        }

# Global self-improving Claude instance
self_improving_claude = SelfImprovingClaude()

def get_self_improving_claude() -> SelfImprovingClaude:
    """Get the global self-improving Claude instance"""
    return self_improving_claude