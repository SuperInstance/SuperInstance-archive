#!/usr/bin/env python3
"""
Tiered LLM System for DMLog
Smart cost optimization with local small model + cloud fallback
"""

import os
import json
import requests
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class LLMResponse:
    content: str
    model_used: str
    cost_estimate: float
    response_time: float
    confidence_score: float

class LocalLLMManager:
    """Manages lightweight local LLM for basic D&D interactions"""
    
    def __init__(self):
        self.model_path = "/opt/dmlog-models/phi-2-dmlog"  # Microsoft Phi-2 fine-tuned
        self.server_url = "http://localhost:8765"
        self.is_running = False
        self.max_tokens = 200  # Keep responses short
        
        # Quick response templates for ultra-fast fallback
        self.quick_templates = {
            'greeting': [
                "Welcome to the tavern, adventurer!",
                "The keeper nods as you enter.",
                "You're greeted warmly by the staff."
            ],
            'dice_roll': [
                "The dice clatter across the table...",
                "You roll with determination!",
                "Fate will decide your success!"
            ],
            'combat': [
                "Steel rings against steel!",
                "The battle intensifies!",
                "Your enemy staggers from the blow!"
            ],
            'exploration': [
                "You venture deeper into the unknown.",
                "Something catches your attention ahead.",
                "The path forward seems uncertain."
            ]
        }
    
    async def start_local_llm(self) -> bool:
        """Start lightweight local LLM server"""
        try:
            # Check if already running
            try:
                response = requests.get(f"{self.server_url}/health", timeout=2)
                if response.status_code == 200:
                    self.is_running = True
                    return True
            except:
                pass
            
            # Start local LLM server
            logger.info("Starting local DMLog LLM server...")
            
            # Use Phi-2 with Ollama for efficiency
            subprocess.Popen([
                'ollama', 'serve', 
                '--model', 'phi:2.7b',  # 2.7B parameter model
                '--port', '8765',
                '--context-length', '2048',
                '--temperature', '0.7'
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Wait for server to start
            for attempt in range(30):
                try:
                    await asyncio.sleep(2)
                    response = requests.get(f"{self.server_url}/health", timeout=2)
                    if response.status_code == 200:
                        self.is_running = True
                        logger.info("Local LLM server started successfully")
                        return True
                except:
                    continue
            
            logger.warning("Failed to start local LLM server")
            return False
            
        except Exception as e:
            logger.error(f"Error starting local LLM: {e}")
            return False
    
    async def generate_response(self, character: str, message: str, context: str = "") -> Optional[LLMResponse]:
        """Generate response using local LLM"""
        if not self.is_running:
            return None
        
        start_time = datetime.now()
        
        try:
            # Create optimized prompt for small model
            prompt = self._create_local_prompt(character, message, context)
            
            response = requests.post(f"{self.server_url}/generate", json={
                'prompt': prompt,
                'max_tokens': self.max_tokens,
                'temperature': 0.7,
                'stop_sequences': ['\n\nPlayer:', '\nDM:', '\nNarrator:']
            }, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                response_time = (datetime.now() - start_time).total_seconds()
                
                return LLMResponse(
                    content=result['text'].strip(),
                    model_used='phi-2-local',
                    cost_estimate=0.0,  # Local is free!
                    response_time=response_time,
                    confidence_score=self._estimate_confidence(result['text'], message)
                )
        
        except Exception as e:
            logger.debug(f"Local LLM error: {e}")
        
        return None
    
    def _create_local_prompt(self, character: str, message: str, context: str) -> str:
        """Create optimized prompt for small local model"""
        char_prompts = {
            'dm': "You are a D&D Dungeon Master. Be creative but concise.",
            'tavern_keeper': "You are Borin, a gruff but friendly dwarf tavern keeper.",
            'wizard': "You are Eldara, an ancient wise elf wizard.",
            'goblin': "You are Grax, a cowardly goblin. Speak simply.",
            'narrator': "Describe the D&D scene atmospherically."
        }
        
        base_prompt = char_prompts.get(character, "You are a helpful D&D character.")
        
        return f"{base_prompt}\n\nPlayer: {message}\n{character.title()}:"
    
    def _estimate_confidence(self, response: str, original_message: str) -> float:
        """Estimate confidence in local LLM response"""
        # Simple heuristics for confidence
        confidence = 0.8  # Base confidence
        
        # Lower confidence for complex requests
        if len(original_message) > 100:
            confidence -= 0.2
        
        # Lower confidence for very short responses
        if len(response) < 20:
            confidence -= 0.3
        
        # Lower confidence if response seems generic
        generic_phrases = ['interesting', 'i see', 'perhaps', 'maybe']
        if any(phrase in response.lower() for phrase in generic_phrases):
            confidence -= 0.1
        
        return max(0.1, confidence)
    
    def get_quick_response(self, request_type: str) -> str:
        """Get instant template response for basic interactions"""
        import random
        templates = self.quick_templates.get(request_type, self.quick_templates['greeting'])
        return random.choice(templates)

class TieredLLMSystem:
    """Intelligent LLM routing with cost optimization"""
    
    def __init__(self):
        self.local_llm = LocalLLMManager()
        self.openai_client = None
        self.cloud_llm_url = None  # Optional dedicated cloud LLM
        
        # Cost tracking
        self.usage_stats = {
            'local_requests': 0,
            'openai_requests': 0,
            'cloud_llm_requests': 0,
            'total_cost': 0.0
        }
        
        # Initialize OpenAI client
        try:
            from openai import OpenAI
            openai_key = os.getenv('OPENAI_API_KEY', 'test-key-for-demo')
            if openai_key != 'test-key-for-demo':
                self.openai_client = OpenAI(api_key=openai_key)
        except Exception as e:
            logger.warning(f"OpenAI client not available: {e}")
    
    async def initialize(self) -> bool:
        """Initialize the tiered LLM system"""
        logger.info("Initializing Tiered LLM System...")
        
        # Start local LLM
        local_started = await self.local_llm.start_local_llm()
        
        if local_started:
            logger.info("✅ Local LLM ready for basic interactions")
        else:
            logger.warning("⚠️ Local LLM not available - using fallback only")
        
        return True
    
    async def generate_response(self, character: str, message: str, context: Dict[str, Any] = None) -> LLMResponse:
        """Generate response using optimal LLM tier"""
        
        # Determine complexity and route accordingly
        complexity = self._analyze_complexity(message, context or {})
        
        if complexity == 'simple':
            # Try local LLM first
            local_response = await self.local_llm.generate_response(character, message)
            if local_response and local_response.confidence_score > 0.6:
                self.usage_stats['local_requests'] += 1
                logger.debug(f"Local LLM handled request: {message[:50]}...")
                return local_response
        
        elif complexity == 'medium':
            # Try local LLM, but with lower confidence threshold
            local_response = await self.local_llm.generate_response(character, message)
            if local_response and local_response.confidence_score > 0.4:
                self.usage_stats['local_requests'] += 1
                return local_response
        
        # Fallback to cloud LLM or OpenAI
        cloud_response = await self._try_cloud_llm(character, message, context or {})
        if cloud_response:
            return cloud_response
        
        # Final fallback to quick template
        return LLMResponse(
            content=self.local_llm.get_quick_response(self._categorize_request(message)),
            model_used='template-fallback',
            cost_estimate=0.0,
            response_time=0.1,
            confidence_score=0.5
        )
    
    def _analyze_complexity(self, message: str, context: Dict[str, Any]) -> str:
        """Analyze request complexity to route to appropriate LLM"""
        
        # Simple requests - local LLM can handle
        simple_patterns = [
            'hello', 'hi', 'greetings', 'thanks', 'yes', 'no',
            'roll dice', 'attack', 'drink', 'eat', 'buy', 'sell',
            'look around', 'what do you see'
        ]
        
        # Complex requests - need powerful LLM
        complex_patterns = [
            'create a campaign', 'generate a story', 'complex puzzle',
            'detailed backstory', 'intricate plot', 'multiple characters',
            'moral dilemma', 'strategic planning', 'world building'
        ]
        
        message_lower = message.lower()
        
        # Check for complex patterns
        if any(pattern in message_lower for pattern in complex_patterns):
            return 'complex'
        
        # Check for simple patterns
        if any(pattern in message_lower for pattern in simple_patterns):
            return 'simple'
        
        # Check message length and context
        if len(message) > 150 or context.get('session_complexity', 0) > 7:
            return 'complex'
        elif len(message) < 50:
            return 'simple'
        
        return 'medium'
    
    def _categorize_request(self, message: str) -> str:
        """Categorize request for template selection"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['roll', 'dice']):
            return 'dice_roll'
        elif any(word in message_lower for word in ['attack', 'fight', 'combat']):
            return 'combat'
        elif any(word in message_lower for word in ['explore', 'look', 'search']):
            return 'exploration'
        else:
            return 'greeting'
    
    async def _try_cloud_llm(self, character: str, message: str, context: Dict[str, Any]) -> Optional[LLMResponse]:
        """Try cloud LLM or OpenAI as fallback"""
        
        # Try dedicated cloud LLM first (if Game Master enabled it)
        if self.cloud_llm_url:
            cloud_response = await self._query_cloud_llm(character, message, context)
            if cloud_response:
                return cloud_response
        
        # Fallback to OpenAI
        if self.openai_client:
            return await self._query_openai(character, message, context)
        
        return None
    
    async def _query_cloud_llm(self, character: str, message: str, context: Dict[str, Any]) -> Optional[LLMResponse]:
        """Query dedicated cloud LLM instance"""
        try:
            start_time = datetime.now()
            
            response = requests.post(f"{self.cloud_llm_url}/generate", json={
                'character': character,
                'message': message,
                'context': context,
                'max_tokens': 300
            }, timeout=15)
            
            if response.status_code == 200:
                result = response.json()
                response_time = (datetime.now() - start_time).total_seconds()
                
                self.usage_stats['cloud_llm_requests'] += 1
                self.usage_stats['total_cost'] += 0.02  # Estimate $0.02 per request
                
                return LLMResponse(
                    content=result['response'],
                    model_used='cloud-llm',
                    cost_estimate=0.02,
                    response_time=response_time,
                    confidence_score=0.9
                )
                
        except Exception as e:
            logger.debug(f"Cloud LLM error: {e}")
        
        return None
    
    async def _query_openai(self, character: str, message: str, context: Dict[str, Any]) -> Optional[LLMResponse]:
        """Query OpenAI as final fallback"""
        try:
            start_time = datetime.now()
            
            system_prompt = f"You are {character} in a D&D game. Be concise and stay in character."
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",  # Cheaper than GPT-4
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                max_tokens=150,
                temperature=0.8
            )
            
            response_time = (datetime.now() - start_time).total_seconds()
            content = response.choices[0].message.content.strip()
            
            # Estimate cost (roughly $0.002 per 1K tokens)
            token_count = len(message.split()) + len(content.split())
            cost = (token_count / 1000) * 0.002
            
            self.usage_stats['openai_requests'] += 1
            self.usage_stats['total_cost'] += cost
            
            return LLMResponse(
                content=content,
                model_used='openai-gpt3.5',
                cost_estimate=cost,
                response_time=response_time,
                confidence_score=0.95
            )
            
        except Exception as e:
            logger.debug(f"OpenAI error: {e}")
        
        return None
    
    def enable_cloud_llm(self, llm_url: str) -> bool:
        """Enable dedicated cloud LLM for Game Master sessions"""
        try:
            # Test cloud LLM connection
            response = requests.get(f"{llm_url}/health", timeout=5)
            if response.status_code == 200:
                self.cloud_llm_url = llm_url
                logger.info(f"✅ Game Master LLM enabled at {llm_url}")
                return True
        except Exception as e:
            logger.error(f"Failed to connect to cloud LLM: {e}")
        
        return False
    
    def disable_cloud_llm(self):
        """Disable cloud LLM to save costs"""
        if self.cloud_llm_url:
            logger.info("💰 Game Master LLM disabled - saving costs")
            self.cloud_llm_url = None
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get cost and usage statistics"""
        total_requests = sum([
            self.usage_stats['local_requests'],
            self.usage_stats['openai_requests'], 
            self.usage_stats['cloud_llm_requests']
        ])
        
        return {
            'total_requests': total_requests,
            'local_percentage': (self.usage_stats['local_requests'] / max(1, total_requests)) * 100,
            'openai_percentage': (self.usage_stats['openai_requests'] / max(1, total_requests)) * 100,
            'cloud_percentage': (self.usage_stats['cloud_llm_requests'] / max(1, total_requests)) * 100,
            'total_cost': self.usage_stats['total_cost'],
            'cost_per_request': self.usage_stats['total_cost'] / max(1, total_requests),
            'local_llm_running': self.local_llm.is_running,
            'cloud_llm_enabled': self.cloud_llm_url is not None
        }

# Global tiered LLM system
tiered_llm = TieredLLMSystem()

async def initialize_llm_system():
    """Initialize the tiered LLM system"""
    return await tiered_llm.initialize()