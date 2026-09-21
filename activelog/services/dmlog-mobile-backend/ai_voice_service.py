#!/usr/bin/env python3
"""
DMLog AI Voice Service
Lightweight voice processing + Claude AI integration for D&D Beyond functionality
"""

import os
import json
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any
import re

# Import AI and speech libraries
try:
    import anthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False
    print("Claude API not available - install with: pip install anthropic")

class DMLogAIService:
    def __init__(self):
        self.db_path = "/tmp/dmlog_ai_service.db"
        self.init_database()
        
        # Enable self-improving Claude for voice interactions  
        self.self_improving_enabled = True
        
        # Initialize Claude client if available
        self.claude_client = None
        if CLAUDE_AVAILABLE:
            # You'll need to set your Claude API key
            api_key = os.getenv('CLAUDE_API_KEY')
            if api_key:
                self.claude_client = anthropic.Client(api_key=api_key)
                print("✅ Claude AI initialized")
            else:
                print("⚠️  Set CLAUDE_API_KEY environment variable to use Claude")
        
        # D&D specific knowledge base
        self.dnd_context = """
        You are DMLog, an intelligent D&D Beyond assistant. You help with:
        - Character creation and management
        - Spell lookups and explanations
        - Rule clarifications
        - Campaign management
        - Dice rolling interpretation
        - NPC generation and roleplay
        
        Keep responses concise but helpful. When users ask about complex rules,
        break them down simply. Always stay in character as a helpful D&D assistant.
        """

    def init_database(self):
        """Initialize AI service database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Conversation history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                message TEXT,
                response TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                intent TEXT,
                needs_heavy_ai BOOLEAN DEFAULT FALSE
            )
        """)
        
        # User preferences and context
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_contexts (
                user_id TEXT PRIMARY KEY,
                current_character TEXT,
                current_campaign TEXT,
                preferences TEXT,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        print("✅ AI service database initialized")

    def classify_intent(self, user_input: str) -> Dict[str, Any]:
        """
        Lightweight intent classification to determine if we need heavy AI
        """
        user_lower = user_input.lower()
        
        # Simple patterns for common D&D tasks
        simple_intents = {
            'dice_roll': ['roll', 'd20', 'd6', 'd8', 'd10', 'd12', 'dice'],
            'spell_lookup': ['spell', 'cast', 'magic', 'fireball', 'heal'],
            'character_info': ['character', 'stats', 'hp', 'health', 'ac', 'armor class'],
            'rules_simple': ['how do i', 'what is', 'explain', 'rule'],
            'campaign_simple': ['campaign', 'session', 'notes']
        }
        
        # Complex intents that need Claude
        complex_patterns = [
            'create a character',
            'build a campaign',
            'generate a story',
            'roleplay',
            'what would happen if',
            'help me decide',
            'creative',
            'narrative'
        ]
        
        # Check for simple intents first
        for intent, keywords in simple_intents.items():
            if any(keyword in user_lower for keyword in keywords):
                return {
                    'intent': intent,
                    'complexity': 'simple',
                    'needs_heavy_ai': False,
                    'confidence': 0.8
                }
        
        # Check for complex intents
        if any(pattern in user_lower for pattern in complex_patterns):
            return {
                'intent': 'complex_query',
                'complexity': 'complex',
                'needs_heavy_ai': True,
                'confidence': 0.9
            }
        
        # Default: assume simple unless proven otherwise
        return {
            'intent': 'general',
            'complexity': 'simple',
            'needs_heavy_ai': len(user_input.split()) > 15,  # Long queries get Claude
            'confidence': 0.5
        }

    def handle_simple_query(self, user_input: str, intent_info: Dict) -> str:
        """
        Handle simple queries with lightweight logic
        """
        intent = intent_info['intent']
        user_lower = user_input.lower()
        
        if intent == 'dice_roll':
            # Extract dice notation (d20, 2d6, etc.)
            dice_match = re.search(r'(\d*)d(\d+)', user_lower)
            if dice_match:
                count = int(dice_match.group(1)) if dice_match.group(1) else 1
                sides = int(dice_match.group(2))
                import random
                rolls = [random.randint(1, sides) for _ in range(min(count, 10))]
                total = sum(rolls)
                return f"🎲 Rolled {count}d{sides}: {rolls} = **{total}**"
            return "🎲 I can help you roll dice! Try 'd20' or '2d6'"
        
        elif intent == 'character_info':
            return "📋 Character info coming soon! For now, check the Characters tab in the app."
        
        elif intent == 'spell_lookup':
            return "✨ Spell lookup coming soon! For now, check the Spells tab for basic spell info."
        
        elif intent == 'rules_simple':
            return "📖 For rule clarifications, I can help with basic questions. Try asking something specific like 'how does advantage work?'"
        
        else:
            return "🤔 I can help with dice rolls, spells, characters, and D&D rules. What would you like to know?"

    async def process_with_claude(self, user_input: str, user_context: Optional[Dict] = None) -> str:
        """
        Process complex queries with Claude AI
        """
        if not self.claude_client:
            return "🔧 Claude AI not configured. Using basic response: " + self.handle_simple_query(user_input, {'intent': 'general'})
        
        try:
            # Build context for Claude
            context_info = ""
            if user_context:
                if user_context.get('current_character'):
                    context_info += f"Current character: {user_context['current_character']}\n"
                if user_context.get('current_campaign'):
                    context_info += f"Current campaign: {user_context['current_campaign']}\n"
            
            # Construct the prompt
            prompt = f"""{self.dnd_context}
            
{context_info}

User question: {user_input}

Provide a helpful, concise response as DMLog assistant."""

            # Call Claude API
            response = await self.claude_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=300,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            return response.content[0].text
            
        except Exception as e:
            print(f"Claude API error: {e}")
            return f"🔧 AI temporarily unavailable. Basic response: {self.handle_simple_query(user_input, {'intent': 'general'})}"

    def process_user_query(self, user_input: str, user_id: str = "default") -> Dict[str, Any]:
        """
        Main processing function - decides between simple and complex handling
        """
        # Classify the intent
        intent_info = self.classify_intent(user_input)
        
        # Get user context
        user_context = self.get_user_context(user_id)
        
        # Process based on complexity
        if intent_info['needs_heavy_ai'] and self.claude_client:
            # Use Claude for complex queries
            import asyncio
            try:
                response = asyncio.run(self.process_with_claude(user_input, user_context))
                processing_method = "claude_ai"
            except:
                response = self.handle_simple_query(user_input, intent_info)
                processing_method = "simple_fallback"
        else:
            # Use lightweight processing
            response = self.handle_simple_query(user_input, intent_info)
            processing_method = "simple"
        
        # Save conversation
        self.save_conversation(user_id, user_input, response, intent_info['intent'], intent_info['needs_heavy_ai'])
        
        return {
            'response': response,
            'intent': intent_info['intent'],
            'processing_method': processing_method,
            'needs_heavy_ai': intent_info['needs_heavy_ai'],
            'timestamp': datetime.now().isoformat()
        }

    def get_user_context(self, user_id: str) -> Dict:
        """Get user context from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT current_character, current_campaign, preferences
            FROM user_contexts WHERE user_id = ?
        """, (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'current_character': result[0],
                'current_campaign': result[1],
                'preferences': json.loads(result[2]) if result[2] else {}
            }
        return {}

    def save_conversation(self, user_id: str, message: str, response: str, intent: str, needs_heavy_ai: bool):
        """Save conversation to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        conversation_id = f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id[:8]}"
        
        cursor.execute("""
            INSERT INTO conversations (id, user_id, message, response, intent, needs_heavy_ai)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (conversation_id, user_id, message, response, intent, needs_heavy_ai))
        
        conn.commit()
        conn.close()

# Global service instance
ai_service = DMLogAIService()

def get_ai_service() -> DMLogAIService:
    """Get the global AI service instance"""
    return ai_service