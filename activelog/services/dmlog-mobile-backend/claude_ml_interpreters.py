#!/usr/bin/env python3
"""
Claude ML Interpreters
Using Claude's context windows cleverly for machine learning tasks
"""

import json
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from superinstance_api_manager import get_api_manager

class ClaudeMLInterpreters:
    def __init__(self):
        self.api_manager = get_api_manager()
        self.db_path = "/tmp/claude_ml_interpreters.db"
        self.init_database()
        
        # Flag to enable self-improving mode
        self.self_improving_enabled = True
        
        # Pre-built interpreter templates
        self.interpreter_templates = {
            "data_analyzer": {
                "name": "Data Pattern Analyzer",
                "prompt": """You are a data pattern analyzer. Analyze the provided data and identify:
1. Patterns and trends
2. Anomalies or outliers
3. Statistical insights
4. Actionable recommendations

Format your response as JSON with these keys:
- patterns: list of identified patterns
- anomalies: list of outliers or unusual data points
- insights: statistical insights
- recommendations: actionable suggestions

Data to analyze:""",
                "input_format": "CSV, JSON, or structured text data",
                "output_format": "JSON with analysis results"
            },
            
            "code_generator": {
                "name": "Code Generation Specialist",
                "prompt": """You are a code generation specialist. Based on the requirements, generate clean, efficient code.

Requirements format: {
    "language": "programming language",
    "task": "description of what to build",
    "framework": "specific framework if any",
    "features": ["list", "of", "required", "features"]
}

Generate complete, production-ready code with:
1. Clear comments and documentation
2. Error handling
3. Best practices for the specified language
4. Modular, maintainable structure

Requirements:""",
                "input_format": "JSON requirements specification",
                "output_format": "Complete code with documentation"
            },
            
            "game_mechanics_designer": {
                "name": "Game Mechanics Designer",
                "prompt": """You are a game mechanics designer. Create balanced, engaging game mechanics based on the specifications.

Input format: {
    "game_type": "genre of game",
    "target_audience": "age group and experience level",
    "theme": "game theme or setting",
    "mechanics_needed": ["list", "of", "specific", "mechanics"],
    "constraints": {"budget": "low/medium/high", "complexity": "simple/moderate/complex"}
}

Design comprehensive game mechanics including:
1. Core gameplay loop
2. Progression systems
3. Balance considerations
4. Player engagement hooks
5. Implementation guidelines

Format response as detailed game design document.

Game specifications:""",
                "input_format": "JSON game requirements",
                "output_format": "Comprehensive game design document"
            },
            
            "content_optimizer": {
                "name": "Content Optimization Engine",
                "prompt": """You are a content optimization engine. Optimize content for maximum engagement and effectiveness.

Analyze and optimize for:
1. Readability and clarity
2. SEO and keyword optimization
3. Emotional engagement
4. Call-to-action effectiveness
5. Target audience alignment

Provide:
- Original analysis
- Optimized version
- Specific improvements made
- Performance predictions

Content to optimize:""",
                "input_format": "Text content (articles, marketing copy, etc.)",
                "output_format": "Analysis and optimized content"
            },
            
            "api_endpoint_designer": {
                "name": "API Endpoint Designer",
                "prompt": """You are an API design specialist. Design RESTful API endpoints based on requirements.

Input format: {
    "service_name": "name of the service",
    "resources": ["list", "of", "data", "resources"],
    "operations": ["CRUD", "operations", "needed"],
    "authentication": "auth method",
    "constraints": {"rate_limits": true/false, "versioning": true/false}
}

Design complete API specification including:
1. Endpoint URLs and HTTP methods
2. Request/response schemas
3. Authentication and authorization
4. Error handling
5. Rate limiting
6. Documentation
7. OpenAPI/Swagger specification

API requirements:""",
                "input_format": "JSON API requirements",
                "output_format": "Complete API specification with OpenAPI schema"
            },
            
            "ui_component_architect": {
                "name": "UI Component Architect",
                "prompt": """You are a UI component architect. Design reusable UI components based on specifications.

Input format: {
    "component_type": "type of component needed",
    "framework": "React/Vue/Angular/etc",
    "design_system": "material/ant/custom/etc",
    "features": ["list", "of", "required", "features"],
    "responsive": true/false,
    "accessibility": "WCAG level required"
}

Design comprehensive component including:
1. Component architecture and structure
2. Props interface and validation
3. State management approach
4. Styling and theming
5. Accessibility implementation
6. Unit test structure
7. Usage examples and documentation

Component specifications:""",
                "input_format": "JSON component requirements",
                "output_format": "Complete component implementation with docs"
            },
            
            "database_optimizer": {
                "name": "Database Query Optimizer",
                "prompt": """You are a database optimization specialist. Analyze and optimize database schemas and queries.

Analyze for:
1. Query performance bottlenecks
2. Index optimization opportunities
3. Schema normalization issues
4. Scaling considerations
5. Security vulnerabilities

Provide:
- Performance analysis
- Optimized queries/schema
- Index recommendations
- Scaling strategies
- Security improvements

Database information to analyze:""",
                "input_format": "SQL schemas, queries, or performance data",
                "output_format": "Optimization report with specific recommendations"
            },
            
            "ml_model_advisor": {
                "name": "ML Model Selection Advisor",
                "prompt": """You are a machine learning model selection advisor. Recommend optimal ML approaches for given problems.

Input format: {
    "problem_type": "classification/regression/clustering/etc",
    "data_description": "description of available data",
    "data_size": "small/medium/large",
    "performance_requirements": "accuracy/speed/interpretability priorities",
    "constraints": {"compute_budget": "low/medium/high", "time_to_deploy": "days/weeks/months"}
}

Provide comprehensive ML strategy including:
1. Recommended algorithms with justification
2. Data preprocessing pipeline
3. Feature engineering suggestions
4. Model evaluation metrics
5. Deployment architecture
6. Monitoring and maintenance plan

ML problem specification:""",
                "input_format": "JSON ML problem description",
                "output_format": "Complete ML strategy and implementation plan"
            }
        }

    def init_database(self):
        """Initialize Claude ML interpreters database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Interpreter execution logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interpreter_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                interpreter_name TEXT,
                user_id TEXT,
                tenant_id TEXT,
                input_data TEXT,
                output_data TEXT,
                execution_time REAL,
                tokens_used INTEGER,
                cost REAL,
                success BOOLEAN,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Context optimization tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS context_optimizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                interpreter_name TEXT,
                original_context_length INTEGER,
                optimized_context_length INTEGER,
                compression_ratio REAL,
                performance_impact TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Custom interpreter definitions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS custom_interpreters (
                id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                prompt_template TEXT,
                input_examples TEXT,
                output_examples TEXT,
                optimization_rules TEXT,
                created_by TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        print("✅ Claude ML Interpreters database initialized")

    def optimize_context_window(self, context: str, target_length: int = 6000) -> str:
        """Optimize context to fit within Claude's window while preserving key information"""
        
        if len(context) <= target_length:
            return context
        
        # Context compression strategies
        lines = context.split('\n')
        
        # Keep critical sections (marked with ##, ***, or specific keywords)
        critical_lines = []
        regular_lines = []
        
        for line in lines:
            if any(marker in line for marker in ['##', '***', 'IMPORTANT:', 'ERROR:', 'WARNING:']):
                critical_lines.append(line)
            else:
                regular_lines.append(line)
        
        # Reconstruct with priority to critical content
        optimized_lines = critical_lines.copy()
        
        # Add regular lines until we reach target length
        current_length = len('\n'.join(optimized_lines))
        
        for line in regular_lines:
            if current_length + len(line) + 1 <= target_length:
                optimized_lines.append(line)
                current_length += len(line) + 1
            else:
                break
        
        # Add truncation notice if needed
        if len(regular_lines) > len(optimized_lines) - len(critical_lines):
            optimized_lines.append(f"\n[... truncated {len(regular_lines) - (len(optimized_lines) - len(critical_lines))} lines for context optimization ...]")
        
        return '\n'.join(optimized_lines)

    async def run_interpreter(self, interpreter_name: str, input_data: Any, 
                             user_id: str, tenant_id: str = "default",
                             context_examples: List[Dict] = None) -> Dict[str, Any]:
        """Run a Claude ML interpreter with context optimization"""
        
        start_time = datetime.now()
        
        # Get interpreter template
        if interpreter_name in self.interpreter_templates:
            template = self.interpreter_templates[interpreter_name]
        else:
            # Check for custom interpreter
            template = self.get_custom_interpreter(interpreter_name)
            if not template:
                return {"error": f"Interpreter '{interpreter_name}' not found"}
        
        # Build optimized context
        context = self.build_context(template, input_data, context_examples)
        optimized_context = self.optimize_context_window(context)
        
        # Execute with self-improving Claude if enabled
        if self.self_improving_enabled:
            # Import here to avoid circular imports
            try:
                from self_improving_claude import get_self_improving_claude
                self_improving_claude = get_self_improving_claude()
                
                result = await self_improving_claude.self_improving_request(
                    interpreter_name,
                    {
                        "input_data": input_data,
                        "context": optimized_context,
                        "examples": context_examples
                    },
                    user_id,
                    tenant_id
                )
                
                # Extract response from self-improving result
                if result.get("success"):
                    claude_result = {
                        "success": True,
                        "response": result["response"],
                        "tokens": len(result["response"].split()),
                        "self_improvement": result.get("self_improvement", {}),
                        "quality_metrics": result.get("quality_metrics", {})
                    }
                else:
                    # Fallback to regular Claude
                    claude_result = await self.api_manager.make_api_request(
                        "claude",
                        {
                            "prompt": optimized_context,
                            "max_tokens": 3000,
                            "model": "claude-3-5-sonnet-20241022"
                        },
                        user_id,
                        tenant_id
                    )
            except ImportError:
                # Fallback if self-improving Claude not available
                claude_result = await self.api_manager.make_api_request(
                    "claude",
                    {
                        "prompt": optimized_context,
                        "max_tokens": 3000,
                        "model": "claude-3-5-sonnet-20241022"
                    },
                    user_id,
                    tenant_id
                )
        else:
            # Use regular Claude API
            claude_result = await self.api_manager.make_api_request(
                "claude",
                {
                    "prompt": optimized_context,
                    "max_tokens": 3000,
                    "model": "claude-3-5-sonnet-20241022"
                },
                user_id,
                tenant_id
            )
        
        result = claude_result
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        if result.get("success"):
            # Log execution
            self.log_execution(
                interpreter_name, user_id, tenant_id, str(input_data),
                result.get("response", ""), execution_time,
                result.get("tokens", 0), 0.015, True
            )
            
            return {
                "success": True,
                "interpreter": interpreter_name,
                "input": input_data,
                "output": result["response"],
                "execution_time": execution_time,
                "tokens_used": result.get("tokens", 0),
                "cost": 0.015
            }
        else:
            self.log_execution(
                interpreter_name, user_id, tenant_id, str(input_data),
                "", execution_time, 0, 0.015, False
            )
            return result

    def build_context(self, template: Dict[str, Any], input_data: Any, 
                     examples: List[Dict] = None) -> str:
        """Build optimized context for Claude with examples and instructions"""
        
        context = f"{template['prompt']}\n\n"
        
        # Add examples if provided
        if examples:
            context += "Examples:\n"
            for i, example in enumerate(examples[:3]):  # Limit to 3 examples
                context += f"\nExample {i+1}:\nInput: {example.get('input', '')}\nOutput: {example.get('output', '')}\n"
            context += "\n"
        
        # Add the actual input
        if isinstance(input_data, dict):
            context += f"Input: {json.dumps(input_data, indent=2)}\n\n"
        else:
            context += f"Input: {str(input_data)}\n\n"
        
        context += "Analyze the input and provide your response:"
        
        return context

    def get_custom_interpreter(self, interpreter_id: str) -> Optional[Dict[str, Any]]:
        """Get custom interpreter definition"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT name, description, prompt_template, input_examples, output_examples
            FROM custom_interpreters WHERE id = ?
        """, (interpreter_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "name": result[0],
                "description": result[1],
                "prompt": result[2],
                "input_format": "Custom",
                "output_format": "Custom"
            }
        
        return None

    def create_custom_interpreter(self, name: str, description: str, 
                                prompt_template: str, input_examples: List[str],
                                output_examples: List[str], user_id: str) -> str:
        """Create a custom Claude ML interpreter"""
        
        interpreter_id = f"custom_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id[:8]}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO custom_interpreters 
            (id, name, description, prompt_template, input_examples, output_examples, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (interpreter_id, name, description, prompt_template,
              json.dumps(input_examples), json.dumps(output_examples), user_id))
        
        conn.commit()
        conn.close()
        
        return interpreter_id

    def log_execution(self, interpreter_name: str, user_id: str, tenant_id: str,
                     input_data: str, output_data: str, execution_time: float,
                     tokens_used: int, cost: float, success: bool):
        """Log interpreter execution for analytics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO interpreter_executions
            (interpreter_name, user_id, tenant_id, input_data, output_data, 
             execution_time, tokens_used, cost, success)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (interpreter_name, user_id, tenant_id, input_data, output_data,
              execution_time, tokens_used, cost, success))
        
        conn.commit()
        conn.close()

    def get_interpreter_analytics(self, interpreter_name: str = None,
                                 days: int = 7) -> Dict[str, Any]:
        """Get analytics for interpreter usage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        since = since.replace(day=since.day - days)
        
        if interpreter_name:
            cursor.execute("""
                SELECT COUNT(*) as executions, AVG(execution_time) as avg_time,
                       SUM(cost) as total_cost, AVG(tokens_used) as avg_tokens,
                       SUM(CASE WHEN success THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate
                FROM interpreter_executions 
                WHERE interpreter_name = ? AND timestamp > ?
            """, (interpreter_name, since))
        else:
            cursor.execute("""
                SELECT interpreter_name, COUNT(*) as executions, AVG(execution_time) as avg_time,
                       SUM(cost) as total_cost, AVG(tokens_used) as avg_tokens,
                       SUM(CASE WHEN success THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate
                FROM interpreter_executions 
                WHERE timestamp > ?
                GROUP BY interpreter_name
                ORDER BY executions DESC
            """, (since,))
        
        results = cursor.fetchall()
        conn.close()
        
        if interpreter_name:
            if results:
                row = results[0]
                return {
                    "interpreter": interpreter_name,
                    "executions": row[0],
                    "avg_execution_time": row[1],
                    "total_cost": row[2],
                    "avg_tokens": row[3],
                    "success_rate": row[4]
                }
            else:
                return {"interpreter": interpreter_name, "executions": 0}
        else:
            analytics = []
            for row in results:
                analytics.append({
                    "interpreter": row[0],
                    "executions": row[1],
                    "avg_execution_time": row[2],
                    "total_cost": row[3],
                    "avg_tokens": row[4],
                    "success_rate": row[5]
                })
            return {"interpreters": analytics}

    def get_available_interpreters(self) -> Dict[str, Dict[str, str]]:
        """Get all available interpreters"""
        available = {}
        
        # Built-in interpreters
        for name, template in self.interpreter_templates.items():
            available[name] = {
                "name": template["name"],
                "input_format": template["input_format"],
                "output_format": template["output_format"],
                "type": "built-in"
            }
        
        # Custom interpreters
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, description FROM custom_interpreters
        """)
        
        for row in cursor.fetchall():
            available[row[0]] = {
                "name": row[1],
                "description": row[2],
                "type": "custom"
            }
        
        conn.close()
        
        return available

# Global Claude ML interpreters instance
claude_ml_interpreters = ClaudeMLInterpreters()

def get_claude_ml_interpreters() -> ClaudeMLInterpreters:
    """Get the global Claude ML interpreters instance"""
    return claude_ml_interpreters