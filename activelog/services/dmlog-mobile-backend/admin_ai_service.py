#!/usr/bin/env python3
"""
DMLog Admin AI Service
Enhanced Claude AI integration for admin developer mode and ecosystem intelligence
"""

import os
import json
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any, List
import re
from replicate_ai_service import get_replicate_ai_service
from self_improving_claude import get_self_improving_claude

try:
    import anthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False
    print("Claude API not available - install with: pip install anthropic")

class AdminAIService:
    def __init__(self):
        self.db_path = "/tmp/dmlog_admin_ai.db"
        self.init_database()
        
        # Initialize Claude client
        self.claude_client = None
        if CLAUDE_AVAILABLE:
            api_key = os.getenv('CLAUDE_API_KEY')
            if api_key:
                self.claude_client = anthropic.Client(api_key=api_key)
                print("✅ Claude AI Admin System initialized")
            else:
                print("⚠️  Set CLAUDE_API_KEY environment variable")
        
        # Admin user identifier (DMLog Admin)
        self.admin_user = "admin_max"
        self.default_template_user = "default_template"
        
        # Initialize Replicate AI service
        self.replicate_service = get_replicate_ai_service()
        
        # Initialize self-improving Claude
        self.self_improving_claude = get_self_improving_claude()
        
        # Enhanced system prompts for different contexts
        self.admin_system_prompt = """
        You are DMLog Admin AI, the intelligent assistant for the DMLog SuperInstance ecosystem.
        
        You have special administrative capabilities:
        
        1. **Developer Mode**: Help admin Max customize and improve the DMLog interface
        2. **UI Generation**: Create React Native/React components with professional styling
        3. **Visual AI**: Generate themes, backgrounds, logos, and interface mockups using Replicate AI
        4. **System Intelligence**: Provide advanced D&D rules, creative storytelling, and campaign management
        5. **User Experience**: Suggest and implement UI/UX improvements
        6. **Code Generation**: Write clean, production-ready code following existing patterns
        
        ADMIN PRIVILEGES:
        - Can modify default user templates
        - Can generate and test new UI components
        - Can suggest ecosystem-wide improvements
        - Has access to full system customization
        
        Always maintain the professional Lightning Dark theme with glassmorphism effects.
        Use the existing color palette: #FF6B6B (primary), #4ECDC4 (secondary), #0A0E1A (background).
        """
        
        self.user_system_prompt = """
        You are DMLog Assistant, helping users customize their personal D&D experience.
        
        You can help with:
        1. Personal UI customization (colors, layouts, preferences)
        2. D&D rules and gameplay
        3. Character management
        4. Campaign assistance
        
        USER LIMITATIONS:
        - Can only modify their own interface
        - Cannot change default templates
        - Can suggest improvements but cannot implement system-wide changes
        
        If a user's customization is excellent, note it for potential admin review.
        """

    def init_database(self):
        """Initialize admin AI database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # UI customization templates
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ui_templates (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                component_name TEXT,
                template_data TEXT,
                is_default BOOLEAN DEFAULT FALSE,
                is_admin_approved BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Admin sessions and developer mode
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                is_developer_mode BOOLEAN DEFAULT FALSE,
                current_context TEXT,
                session_data TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # User customization requests
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customization_requests (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                request_type TEXT,
                description TEXT,
                component_data TEXT,
                status TEXT DEFAULT 'pending',
                admin_review TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Enhanced conversation history with admin context
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                message TEXT,
                response TEXT,
                context_type TEXT,
                is_admin_mode BOOLEAN DEFAULT FALSE,
                component_generated TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        print("✅ Admin AI database initialized")

    def is_admin_user(self, user_id: str) -> bool:
        """Check if user is admin"""
        return user_id == self.admin_user

    def is_developer_mode(self, user_id: str) -> bool:
        """Check if user is in developer mode"""
        if not self.is_admin_user(user_id):
            return False
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT is_developer_mode FROM admin_sessions 
            WHERE user_id = ? 
            ORDER BY created_at DESC LIMIT 1
        """, (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result and result[0] if result else False

    def toggle_developer_mode(self, user_id: str) -> Dict[str, Any]:
        """Toggle developer mode for admin"""
        if not self.is_admin_user(user_id):
            return {"error": "Only admin can access developer mode"}
        
        current_mode = self.is_developer_mode(user_id)
        new_mode = not current_mode
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        session_id = f"admin_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        cursor.execute("""
            INSERT INTO admin_sessions (id, user_id, is_developer_mode, current_context)
            VALUES (?, ?, ?, ?)
        """, (session_id, user_id, new_mode, "developer_mode_toggle"))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "developer_mode": new_mode,
            "message": f"Developer mode {'enabled' if new_mode else 'disabled'}"
        }

    async def process_admin_query(self, user_input: str, user_id: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Process query with admin capabilities"""
        if not self.claude_client:
            return {"error": "Claude AI not available", "response": "Admin AI system not configured"}
        
        is_admin = self.is_admin_user(user_id)
        is_dev_mode = self.is_developer_mode(user_id)
        
        # Determine context and capabilities
        if is_admin and is_dev_mode:
            system_prompt = self.admin_system_prompt
            capabilities = "full_admin"
        elif is_admin:
            system_prompt = self.admin_system_prompt.replace("ADMIN PRIVILEGES:", "ADMIN MODE (Developer mode disabled):")
            capabilities = "admin_basic"
        else:
            system_prompt = self.user_system_prompt
            capabilities = "user"
        
        # Build context information
        context_info = ""
        if context:
            context_info += f"User context: {json.dumps(context, indent=2)}\n"
        
        if is_admin:
            context_info += f"Admin status: {'Developer Mode' if is_dev_mode else 'Basic Admin'}\n"
        
        # Detect if this is a UI/component generation request
        ui_keywords = ['component', 'interface', 'design', 'ui', 'frontend', 'screen', 'button', 'layout', 'customize']
        is_ui_request = any(keyword in user_input.lower() for keyword in ui_keywords)
        
        # Detect if this is a visual generation request
        visual_keywords = ['theme', 'background', 'logo', 'generate', 'create', 'visual', 'image', 'mockup', 'color', 'style']
        is_visual_request = any(keyword in user_input.lower() for keyword in visual_keywords)
        
        try:
            # Construct the prompt
            prompt = f"""{system_prompt}

{context_info}

User request: {user_input}

Current capabilities: {capabilities}
Is UI/Component request: {is_ui_request}
Is Visual Generation request: {is_visual_request}

Provide a helpful response. If this is a UI request and you're in admin developer mode, 
you can generate actual React Native component code. If this is a visual generation request,
describe what visual assets would be helpful and I'll generate them using Replicate AI.
If it's a user request for customization, help them understand what they can do and suggest 
contacting admin for system-wide changes.
"""

            # Use self-improving Claude instead of direct API call
            improvement_result = await self.self_improving_claude.self_improving_request(
                "admin_ai_assistant", 
                {
                    "prompt": prompt,
                    "user_context": context,
                    "capabilities": capabilities,
                    "is_ui_request": is_ui_request,
                    "is_visual_request": is_visual_request
                },
                user_id,
                "admin"
            )
            
            if improvement_result.get("success"):
                response_text = improvement_result["response"]
                
                # Log self-improvement data
                if improvement_result.get("self_improvement", {}).get("weights_updated"):
                    print(f"🧠 Admin AI improved: {improvement_result['self_improvement']['patterns_learned']}")
            else:
                # Fallback to direct Claude call
                message = await self.claude_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1500,
                    messages=[{
                        "role": "user", 
                        "content": prompt
                    }]
                )
                response_text = message.content[0].text
            
            # Save conversation
            self.save_admin_conversation(
                user_id, user_input, response_text, 
                capabilities, is_admin and is_dev_mode, 
                is_ui_request
            )
            
            # Handle visual generation if this is a visual request and user is admin
            visual_assets = {}
            if is_visual_request and is_admin and is_dev_mode:
                visual_assets = await self.handle_visual_generation(user_id, user_input, response_text)
            
            # If this generated a component and user is admin, potentially save as template
            if is_ui_request and is_admin and is_dev_mode:
                self.handle_component_generation(user_id, user_input, response_text)
            
            return {
                "response": response_text,
                "capabilities": capabilities,
                "is_admin": is_admin,
                "is_developer_mode": is_dev_mode,
                "is_ui_request": is_ui_request,
                "is_visual_request": is_visual_request,
                "visual_assets": visual_assets,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Admin Claude API error: {e}")
            return {
                "error": str(e),
                "response": "Admin AI temporarily unavailable",
                "capabilities": capabilities
            }

    def handle_component_generation(self, user_id: str, request: str, response: str):
        """Handle component generation for admin"""
        # Extract component code if present
        code_blocks = re.findall(r'```(?:tsx?|javascript|react)?\n(.*?)```', response, re.DOTALL)
        
        if code_blocks:
            component_id = f"comp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO ui_templates (id, user_id, component_name, template_data, is_admin_approved)
                VALUES (?, ?, ?, ?, ?)
            """, (component_id, user_id, "generated_component", json.dumps({
                "request": request,
                "code": code_blocks[0],
                "full_response": response
            }), True))
            
            conn.commit()
            conn.close()

    async def handle_visual_generation(self, user_id: str, request: str, response: str) -> Dict[str, Any]:
        """Handle visual generation requests using Replicate AI"""
        try:
            # Analyze the request to determine what to generate
            visual_request = self.replicate_service.process_visual_request(request, user_id)
            
            if visual_request['type'] == 'theme':
                # Extract theme details from request
                colors = "blue and white"  # default
                style = "modern"  # default
                
                # Try to extract colors and style from request
                if 'dark' in request.lower():
                    colors = "dark blue and black"
                elif 'light' in request.lower():
                    colors = "light blue and white"
                elif 'red' in request.lower():
                    colors = "red and black"
                
                if 'futuristic' in request.lower():
                    style = "futuristic"
                elif 'minimalist' in request.lower():
                    style = "minimalist"
                elif 'fantasy' in request.lower():
                    style = "fantasy"
                
                result = await self.replicate_service.generate_ui_theme(
                    request, user_id, colors, style
                )
                
            elif visual_request['type'] == 'logo':
                company = "DMLog"
                style = "modern"
                colors = "blue"
                
                result = await self.replicate_service.generate_logo(company, style, colors)
                
            elif visual_request['type'] == 'dashboard':
                style = "modern"
                colors = "dark blue"
                
                result = await self.replicate_service.generate_dashboard_mockup(
                    request, style, colors
                )
                
            else:
                # General image generation
                result = await self.replicate_service.generate_image(
                    request, model='flux_schnell'
                )
            
            return result
            
        except Exception as e:
            print(f"Visual generation error: {e}")
            return {"error": f"Visual generation failed: {str(e)}"}

    def save_admin_conversation(self, user_id: str, message: str, response: str, 
                               context_type: str, is_admin_mode: bool, is_ui_request: bool):
        """Save admin conversation to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        conversation_id = f"admin_conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id[:8]}"
        
        cursor.execute("""
            INSERT INTO admin_conversations 
            (id, user_id, message, response, context_type, is_admin_mode, component_generated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (conversation_id, user_id, message, response, context_type, is_admin_mode, str(is_ui_request)))
        
        conn.commit()
        conn.close()

    def get_user_customizations(self, user_id: str) -> List[Dict]:
        """Get user's customizations"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM ui_templates 
            WHERE user_id = ? 
            ORDER BY updated_at DESC
        """, (user_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        customizations = []
        for row in results:
            customizations.append({
                "id": row[0],
                "user_id": row[1],
                "component_name": row[2],
                "template_data": json.loads(row[3]) if row[3] else {},
                "is_default": row[4],
                "is_admin_approved": row[5],
                "created_at": row[6],
                "updated_at": row[7]
            })
        
        return customizations

    def apply_default_template(self, component_name: str, user_id: str) -> Dict[str, Any]:
        """Apply admin-approved default template to user"""
        if not self.is_admin_user(user_id):
            return {"error": "Only admin can apply default templates"}
        
        # Implementation for applying templates to default user
        return {"success": True, "message": f"Default template applied for {component_name}"}

# Global admin service instance
admin_ai_service = AdminAIService()

def get_admin_ai_service() -> AdminAIService:
    """Get the global admin AI service instance"""
    return admin_ai_service