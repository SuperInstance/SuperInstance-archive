#!/usr/bin/env python3
"""
SuperInstance Ecosystem-Wide Voice Command ML Training
Learns user voice patterns and language across all apps for better AI responses
"""

import os
import json
import sqlite3
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
import pickle
import re
import asyncio
import aiofiles

logger = logging.getLogger(__name__)

@dataclass
class VoiceCommand:
    user_id: str
    app_name: str
    original_command: str
    interpreted_command: str
    ai_response: str
    user_feedback: str  # 'positive', 'negative', 'neutral'
    timestamp: datetime
    context: Dict[str, Any]
    success_metrics: Dict[str, float]

@dataclass
class UserVoiceProfile:
    user_id: str
    preferred_phrases: Dict[str, List[str]]
    command_patterns: Dict[str, str]
    language_style: Dict[str, Any]
    context_preferences: Dict[str, Any]
    learning_confidence: float

class EcosystemVoiceMLTrainer:
    """Trains on voice commands across the entire SuperInstance ecosystem"""
    
    def __init__(self, db_path: str = "/home/activeloguser/activelog/ecosystem_voice_ml.db"):
        self.db_path = db_path
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self.success_predictor = RandomForestRegressor(n_estimators=100)
        self.user_profiles: Dict[str, UserVoiceProfile] = {}
        
        # App-specific command mappings
        self.app_contexts = {
            'dmlog': {
                'domain': 'gaming',
                'common_commands': ['roll dice', 'attack', 'cast spell', 'move to', 'talk to'],
                'entities': ['character', 'monster', 'item', 'location'],
                'success_metrics': ['engagement', 'story_flow', 'character_consistency']
            },
            'fishinglog': {
                'domain': 'fishing',
                'common_commands': ['set autopilot', 'check weather', 'log catch', 'navigate to'],
                'entities': ['location', 'fish_species', 'weather', 'equipment'],
                'success_metrics': ['task_completion', 'accuracy', 'user_satisfaction']
            },
            'personallog': {
                'domain': 'productivity',
                'common_commands': ['schedule meeting', 'create note', 'remind me', 'search'],
                'entities': ['person', 'event', 'date', 'location'],
                'success_metrics': ['task_completion', 'accuracy', 'time_saved']
            }
        }
        
        self.initialize_database()
        self.load_user_profiles()
    
    def initialize_database(self):
        """Initialize SQLite database for ecosystem-wide voice learning"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS voice_commands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    app_name TEXT NOT NULL,
                    original_command TEXT NOT NULL,
                    interpreted_command TEXT NOT NULL,
                    ai_response TEXT NOT NULL,
                    user_feedback TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    context TEXT,
                    success_metrics TEXT,
                    learning_applied BOOLEAN DEFAULT FALSE
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_voice_profiles (
                    user_id TEXT PRIMARY KEY,
                    preferred_phrases TEXT,
                    command_patterns TEXT,
                    language_style TEXT,
                    context_preferences TEXT,
                    learning_confidence REAL DEFAULT 0.5,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS cross_app_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    pattern_type TEXT NOT NULL,
                    source_app TEXT NOT NULL,
                    target_apps TEXT,
                    pattern_data TEXT NOT NULL,
                    confidence REAL DEFAULT 0.5,
                    usage_count INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 0.5,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    async def record_voice_interaction(self, command_data: VoiceCommand):
        """Record a voice interaction for ecosystem-wide learning"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO voice_commands 
                (user_id, app_name, original_command, interpreted_command, 
                 ai_response, user_feedback, context, success_metrics)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                command_data.user_id,
                command_data.app_name,
                command_data.original_command,
                command_data.interpreted_command,
                command_data.ai_response,
                command_data.user_feedback,
                json.dumps(command_data.context),
                json.dumps(command_data.success_metrics)
            ))
            conn.commit()
        
        # Update user profile immediately
        await self.update_user_profile(command_data)
        
        # Train cross-app patterns if we have enough data
        await self.train_cross_app_patterns(command_data.user_id)
    
    async def update_user_profile(self, command_data: VoiceCommand):
        """Update user's voice profile based on new interaction"""
        user_id = command_data.user_id
        
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = UserVoiceProfile(
                user_id=user_id,
                preferred_phrases={},
                command_patterns={},
                language_style={},
                context_preferences={},
                learning_confidence=0.5
            )
        
        profile = self.user_profiles[user_id]
        
        # Update preferred phrases based on positive feedback
        if command_data.user_feedback == 'positive':
            app_phrases = profile.preferred_phrases.get(command_data.app_name, [])
            if command_data.original_command not in app_phrases:
                app_phrases.append(command_data.original_command)
                profile.preferred_phrases[command_data.app_name] = app_phrases[-10:]  # Keep last 10
        
        # Learn command patterns
        command_intent = self.extract_command_intent(command_data.original_command, command_data.app_name)
        if command_intent:
            profile.command_patterns[command_intent] = command_data.original_command
        
        # Update language style
        self.analyze_language_style(profile, command_data)
        
        # Save updated profile
        await self.save_user_profile(profile)
    
    def extract_command_intent(self, command: str, app_name: str) -> Optional[str]:
        """Extract the intent from a voice command"""
        command_lower = command.lower()
        app_context = self.app_contexts.get(app_name, {})
        common_commands = app_context.get('common_commands', [])
        
        for intent in common_commands:
            if any(word in command_lower for word in intent.split()):
                return intent.replace(' ', '_')
        
        # Fallback intent extraction
        action_words = ['set', 'get', 'create', 'delete', 'update', 'find', 'search', 'go', 'move', 'attack', 'cast']
        for action in action_words:
            if action in command_lower:
                return f"{action}_command"
        
        return "general_command"
    
    def analyze_language_style(self, profile: UserVoiceProfile, command_data: VoiceCommand):
        """Analyze and learn user's language style"""
        command = command_data.original_command
        
        # Analyze formality
        formal_indicators = ['please', 'could you', 'would you', 'thank you']
        informal_indicators = ['hey', 'yo', 'gimme', 'gonna', 'wanna']
        
        formal_score = sum(1 for indicator in formal_indicators if indicator in command.lower())
        informal_score = sum(1 for indicator in informal_indicators if indicator in command.lower())
        
        # Update language style metrics
        style = profile.language_style
        style['formality'] = style.get('formality', 0.5)
        if formal_score > informal_score:
            style['formality'] = min(1.0, style['formality'] + 0.1)
        elif informal_score > formal_score:
            style['formality'] = max(0.0, style['formality'] - 0.1)
        
        # Analyze verbosity
        word_count = len(command.split())
        style['verbosity'] = style.get('verbosity', 0.5)
        if word_count > 10:
            style['verbosity'] = min(1.0, style['verbosity'] + 0.1)
        elif word_count < 5:
            style['verbosity'] = max(0.0, style['verbosity'] - 0.1)
        
        # Analyze directness
        question_words = ['what', 'how', 'when', 'where', 'why', 'can you', 'could you']
        if any(word in command.lower() for word in question_words):
            style['directness'] = style.get('directness', 0.5) * 0.9  # Less direct
        else:
            style['directness'] = min(1.0, style.get('directness', 0.5) + 0.1)  # More direct
    
    async def train_cross_app_patterns(self, user_id: str):
        """Train patterns that work across multiple apps for a user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT app_name, original_command, interpreted_command, user_feedback, success_metrics
                FROM voice_commands 
                WHERE user_id = ? AND user_feedback = 'positive'
                ORDER BY timestamp DESC LIMIT 100
            ''', (user_id,))
            
            recent_commands = cursor.fetchall()
        
        if len(recent_commands) < 10:  # Need enough data to find patterns
            return
        
        # Find common phrases used across different apps
        app_commands = {}
        for row in recent_commands:
            app_name, original, interpreted, feedback, metrics = row
            if app_name not in app_commands:
                app_commands[app_name] = []
            app_commands[app_name].append({
                'original': original,
                'interpreted': interpreted,
                'metrics': json.loads(metrics) if metrics else {}
            })
        
        # Find cross-app patterns
        await self.find_cross_app_patterns(user_id, app_commands)
    
    async def find_cross_app_patterns(self, user_id: str, app_commands: Dict[str, List[Dict]]):
        """Find patterns that work across multiple apps"""
        
        # Pattern 1: Command structure preferences
        for app_name, commands in app_commands.items():
            for command_data in commands:
                original = command_data['original']
                
                # Find similar command structures in other apps
                for other_app, other_commands in app_commands.items():
                    if other_app == app_name:
                        continue
                    
                    similar_commands = self.find_similar_commands(original, other_commands)
                    
                    if similar_commands:
                        pattern = {
                            'type': 'command_structure',
                            'pattern': self.extract_command_structure(original),
                            'confidence': len(similar_commands) / len(other_commands),
                            'examples': [original] + [cmd['original'] for cmd in similar_commands[:3]]
                        }
                        
                        await self.save_cross_app_pattern(user_id, 'command_structure', app_name, 
                                                        [other_app], pattern)
        
        # Pattern 2: Language style consistency
        language_patterns = self.analyze_cross_app_language_patterns(app_commands)
        if language_patterns:
            await self.save_cross_app_pattern(user_id, 'language_style', 'all', 
                                            list(app_commands.keys()), language_patterns)
    
    def find_similar_commands(self, target_command: str, commands: List[Dict]) -> List[Dict]:
        """Find commands with similar structure or intent"""
        target_structure = self.extract_command_structure(target_command)
        similar = []
        
        for cmd in commands:
            cmd_structure = self.extract_command_structure(cmd['original'])
            similarity = self.calculate_structure_similarity(target_structure, cmd_structure)
            
            if similarity > 0.7:  # 70% similarity threshold
                similar.append(cmd)
        
        return similar
    
    def extract_command_structure(self, command: str) -> Dict[str, Any]:
        """Extract structural elements of a command"""
        words = command.lower().split()
        
        structure = {
            'length': len(words),
            'starts_with_verb': len(words) > 0 and self.is_action_word(words[0]),
            'has_question_words': any(word in ['what', 'how', 'when', 'where', 'why'] for word in words),
            'has_please': 'please' in words,
            'has_numbers': any(word.isdigit() for word in words),
            'verb_position': next((i for i, word in enumerate(words) if self.is_action_word(word)), -1)
        }
        
        return structure
    
    def is_action_word(self, word: str) -> bool:
        """Check if word is an action/verb"""
        action_words = [
            'set', 'get', 'create', 'delete', 'update', 'find', 'search', 'go', 'move', 
            'attack', 'cast', 'roll', 'check', 'log', 'schedule', 'remind', 'navigate'
        ]
        return word in action_words
    
    def calculate_structure_similarity(self, struct1: Dict, struct2: Dict) -> float:
        """Calculate similarity between command structures"""
        matches = 0
        total = len(struct1)
        
        for key, value in struct1.items():
            if key in struct2 and struct2[key] == value:
                matches += 1
        
        return matches / total if total > 0 else 0
    
    def analyze_cross_app_language_patterns(self, app_commands: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Analyze language patterns across apps"""
        all_commands = []
        for commands in app_commands.values():
            all_commands.extend([cmd['original'] for cmd in commands])
        
        if len(all_commands) < 5:
            return {}
        
        # Analyze common words and phrases
        word_freq = {}
        phrase_freq = {}
        
        for command in all_commands:
            words = command.lower().split()
            
            # Count words
            for word in words:
                word_freq[word] = word_freq.get(word, 0) + 1
            
            # Count 2-word phrases
            for i in range(len(words) - 1):
                phrase = f"{words[i]} {words[i+1]}"
                phrase_freq[phrase] = phrase_freq.get(phrase, 0) + 1
        
        # Find patterns used across multiple apps
        cross_app_words = {}
        cross_app_phrases = {}
        
        for word, freq in word_freq.items():
            if freq >= len(app_commands):  # Used in at least as many times as apps
                cross_app_words[word] = freq
        
        for phrase, freq in phrase_freq.items():
            if freq >= len(app_commands) // 2:  # Used across multiple apps
                cross_app_phrases[phrase] = freq
        
        return {
            'common_words': cross_app_words,
            'common_phrases': cross_app_phrases,
            'total_commands': len(all_commands),
            'apps_count': len(app_commands)
        }
    
    async def save_cross_app_pattern(self, user_id: str, pattern_type: str, source_app: str, 
                                   target_apps: List[str], pattern_data: Dict):
        """Save a cross-app pattern to the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO cross_app_patterns 
                (user_id, pattern_type, source_app, target_apps, pattern_data, confidence)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                pattern_type,
                source_app,
                json.dumps(target_apps),
                json.dumps(pattern_data),
                pattern_data.get('confidence', 0.5)
            ))
            conn.commit()
    
    async def optimize_command_for_user(self, user_id: str, app_name: str, 
                                      original_command: str) -> str:
        """Optimize a command based on user's learned patterns"""
        
        if user_id not in self.user_profiles:
            await self.load_user_profile(user_id)
        
        if user_id not in self.user_profiles:
            return original_command  # No profile data
        
        profile = self.user_profiles[user_id]
        optimized = original_command
        
        # Apply language style preferences
        optimized = self.apply_language_style(optimized, profile.language_style)
        
        # Apply command pattern preferences
        optimized = await self.apply_command_patterns(optimized, profile, app_name)
        
        # Apply cross-app patterns
        optimized = await self.apply_cross_app_patterns(user_id, app_name, optimized)
        
        return optimized
    
    def apply_language_style(self, command: str, language_style: Dict[str, Any]) -> str:
        """Apply user's language style preferences"""
        if not language_style:
            return command
        
        formality = language_style.get('formality', 0.5)
        directness = language_style.get('directness', 0.5)
        
        # Adjust formality
        if formality > 0.7 and 'please' not in command.lower():
            command = f"Please {command.lower()}"
        elif formality < 0.3:
            # Make less formal
            command = command.replace('Please ', '').replace('please ', '')
            command = re.sub(r'\bcould you\b', 'can you', command, flags=re.IGNORECASE)
        
        # Adjust directness
        if directness > 0.7:
            # Make more direct - remove question words when possible
            command = re.sub(r'^(can you |could you |would you )', '', command, flags=re.IGNORECASE)
        
        return command
    
    async def apply_command_patterns(self, command: str, profile: UserVoiceProfile, 
                                   app_name: str) -> str:
        """Apply user's preferred command patterns"""
        command_intent = self.extract_command_intent(command, app_name)
        
        if command_intent in profile.command_patterns:
            preferred_pattern = profile.command_patterns[command_intent]
            
            # Extract key information from current command
            entities = self.extract_entities(command, app_name)
            
            # Apply preferred pattern with current entities
            if entities:
                optimized = self.merge_pattern_with_entities(preferred_pattern, entities)
                return optimized
        
        return command
    
    async def apply_cross_app_patterns(self, user_id: str, app_name: str, command: str) -> str:
        """Apply cross-app patterns for this user"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT pattern_type, pattern_data, confidence
                FROM cross_app_patterns 
                WHERE user_id = ? AND (source_app = ? OR target_apps LIKE ?)
                ORDER BY confidence DESC, usage_count DESC
                LIMIT 5
            ''', (user_id, app_name, f'%{app_name}%'))
            
            patterns = cursor.fetchall()
        
        optimized_command = command
        
        for pattern_type, pattern_json, confidence in patterns:
            if confidence < 0.6:  # Only apply high-confidence patterns
                continue
            
            try:
                pattern_data = json.loads(pattern_json)
                
                if pattern_type == 'command_structure':
                    optimized_command = self.apply_structure_pattern(optimized_command, pattern_data)
                elif pattern_type == 'language_style':
                    optimized_command = self.apply_language_pattern(optimized_command, pattern_data)
            
            except json.JSONDecodeError:
                continue
        
        return optimized_command
    
    def extract_entities(self, command: str, app_name: str) -> Dict[str, List[str]]:
        """Extract entities from command based on app context"""
        entities = {}
        app_context = self.app_contexts.get(app_name, {})
        entity_types = app_context.get('entities', [])
        
        words = command.split()
        
        for entity_type in entity_types:
            entities[entity_type] = []
            
            if entity_type == 'location':
                # Simple location detection
                location_indicators = ['to', 'at', 'in', 'near', 'around']
                for i, word in enumerate(words):
                    if word.lower() in location_indicators and i + 1 < len(words):
                        entities[entity_type].append(words[i + 1])
            
            elif entity_type == 'character':
                # Simple character detection for DMLog
                character_indicators = ['talk to', 'speak with', 'ask']
                command_lower = command.lower()
                for indicator in character_indicators:
                    if indicator in command_lower:
                        idx = command_lower.find(indicator) + len(indicator)
                        remaining = command[idx:].strip()
                        if remaining:
                            entities[entity_type].append(remaining.split()[0])
        
        return entities
    
    def merge_pattern_with_entities(self, pattern: str, entities: Dict[str, List[str]]) -> str:
        """Merge preferred pattern with current entities"""
        # Simple merge - replace entities in pattern with current ones
        merged = pattern
        
        for entity_type, entity_list in entities.items():
            if entity_list:
                # Replace first occurrence of similar entity type
                placeholder = f"{{{entity_type}}}"
                if placeholder in merged:
                    merged = merged.replace(placeholder, entity_list[0])
        
        return merged
    
    def apply_structure_pattern(self, command: str, pattern_data: Dict) -> str:
        """Apply structural pattern to command"""
        # This would implement more sophisticated pattern application
        # For now, return original command
        return command
    
    def apply_language_pattern(self, command: str, pattern_data: Dict) -> str:
        """Apply language pattern to command"""
        common_words = pattern_data.get('common_words', {})
        common_phrases = pattern_data.get('common_phrases', {})
        
        # Replace words with user's preferred alternatives
        words = command.split()
        for i, word in enumerate(words):
            if word.lower() in common_words:
                # Keep user's preferred word
                continue
        
        return command
    
    async def save_user_profile(self, profile: UserVoiceProfile):
        """Save user profile to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO user_voice_profiles
                (user_id, preferred_phrases, command_patterns, language_style, 
                 context_preferences, learning_confidence)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                profile.user_id,
                json.dumps(profile.preferred_phrases),
                json.dumps(profile.command_patterns),
                json.dumps(profile.language_style),
                json.dumps(profile.context_preferences),
                profile.learning_confidence
            ))
            conn.commit()
    
    async def load_user_profile(self, user_id: str) -> Optional[UserVoiceProfile]:
        """Load user profile from database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT preferred_phrases, command_patterns, language_style, 
                       context_preferences, learning_confidence
                FROM user_voice_profiles WHERE user_id = ?
            ''', (user_id,))
            
            row = cursor.fetchone()
        
        if row:
            profile = UserVoiceProfile(
                user_id=user_id,
                preferred_phrases=json.loads(row[0]),
                command_patterns=json.loads(row[1]),
                language_style=json.loads(row[2]),
                context_preferences=json.loads(row[3]),
                learning_confidence=row[4]
            )
            
            self.user_profiles[user_id] = profile
            return profile
        
        return None
    
    def load_user_profiles(self):
        """Load all user profiles into memory"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT user_id, preferred_phrases, command_patterns, language_style,
                       context_preferences, learning_confidence
                FROM user_voice_profiles
            ''')
            
            for row in cursor.fetchall():
                user_id = row[0]
                profile = UserVoiceProfile(
                    user_id=user_id,
                    preferred_phrases=json.loads(row[1]),
                    command_patterns=json.loads(row[2]),
                    language_style=json.loads(row[3]),
                    context_preferences=json.loads(row[4]),
                    learning_confidence=row[5]
                )
                self.user_profiles[user_id] = profile
    
    async def get_ecosystem_insights(self, user_id: str) -> Dict[str, Any]:
        """Get insights about user's voice patterns across ecosystem"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT app_name, COUNT(*) as command_count, 
                       AVG(CASE WHEN user_feedback = 'positive' THEN 1.0 ELSE 0.0 END) as success_rate
                FROM voice_commands 
                WHERE user_id = ?
                GROUP BY app_name
            ''', (user_id,))
            
            app_stats = {row[0]: {'commands': row[1], 'success_rate': row[2]} 
                        for row in cursor.fetchall()}
        
        profile = self.user_profiles.get(user_id)
        
        return {
            'user_id': user_id,
            'app_statistics': app_stats,
            'learning_confidence': profile.learning_confidence if profile else 0.5,
            'total_apps_used': len(app_stats),
            'cross_app_patterns': await self.get_cross_app_pattern_count(user_id),
            'language_style': profile.language_style if profile else {},
            'ecosystem_readiness': self.calculate_ecosystem_readiness(app_stats, profile)
        }
    
    async def get_cross_app_pattern_count(self, user_id: str) -> int:
        """Get count of cross-app patterns for user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT COUNT(*) FROM cross_app_patterns WHERE user_id = ?
            ''', (user_id,))
            
            return cursor.fetchone()[0]
    
    def calculate_ecosystem_readiness(self, app_stats: Dict, profile: Optional[UserVoiceProfile]) -> float:
        """Calculate how ready the ecosystem is to serve this user"""
        if not app_stats or not profile:
            return 0.3
        
        # Base readiness on number of apps used and success rates
        apps_used = len(app_stats)
        avg_success = sum(stats['success_rate'] for stats in app_stats.values()) / apps_used
        total_commands = sum(stats['commands'] for stats in app_stats.values())
        
        readiness = 0.3  # Base readiness
        readiness += min(0.3, apps_used * 0.1)  # Up to 0.3 for using multiple apps
        readiness += min(0.2, avg_success * 0.2)  # Up to 0.2 for high success rate
        readiness += min(0.2, total_commands / 100 * 0.2)  # Up to 0.2 for usage volume
        
        return min(1.0, readiness)


# Global ecosystem voice ML trainer
ecosystem_voice_ml = EcosystemVoiceMLTrainer()

async def initialize_ecosystem_voice_ml():
    """Initialize the ecosystem-wide voice ML trainer"""
    logger.info("🎙️ Initializing SuperInstance Ecosystem Voice ML...")
    return True

async def record_voice_interaction(user_id: str, app_name: str, original_command: str,
                                 interpreted_command: str, ai_response: str,
                                 user_feedback: str, context: Dict[str, Any] = None,
                                 success_metrics: Dict[str, float] = None):
    """Record a voice interaction for ecosystem learning"""
    
    command_data = VoiceCommand(
        user_id=user_id,
        app_name=app_name,
        original_command=original_command,
        interpreted_command=interpreted_command,
        ai_response=ai_response,
        user_feedback=user_feedback,
        timestamp=datetime.now(),
        context=context or {},
        success_metrics=success_metrics or {}
    )
    
    await ecosystem_voice_ml.record_voice_interaction(command_data)

async def optimize_voice_command(user_id: str, app_name: str, command: str) -> str:
    """Optimize a voice command based on user's ecosystem-wide learning"""
    return await ecosystem_voice_ml.optimize_command_for_user(user_id, app_name, command)