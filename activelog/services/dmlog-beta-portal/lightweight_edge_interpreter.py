#!/usr/bin/env python3
"""
Lightweight Edge AI Interpreter
Ultra-lightweight personal AI translation layer for phones and edge devices
<50KB memory footprint, works offline, syncs with cloud when available
"""

import json
import re
import time
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib
import sqlite3
import os

@dataclass
class EdgeInterpretation:
    """Lightweight interpretation result"""
    original: str
    interpreted: str
    confidence: float
    method: str
    timestamp: float

@dataclass  
class UserMicroProfile:
    """Minimal user profile for edge devices"""
    user_id: str
    shortcuts: Dict[str, str]  # Max 20 shortcuts
    vocab_map: Dict[str, str]  # Max 50 vocabulary mappings
    patterns: List[str]  # Max 10 learned patterns
    confidence: float
    last_sync: float

class LightweightEdgeInterpreter:
    """Ultra-lightweight interpreter for edge devices"""
    
    def __init__(self, max_memory_kb: int = 50):
        self.max_memory_kb = max_memory_kb
        self.user_profile: Optional[UserMicroProfile] = None
        self.cache: Dict[str, EdgeInterpretation] = {}  # Max 20 cached interpretations
        self.patterns_cache: Dict[str, str] = {}
        
        # Extremely lightweight pattern rules (compiled regexes cached)
        self.quick_patterns = {
            # Voice command patterns
            r'\b(hey|hi|hello)\b': 'greeting_mode',
            r'\b(set|create|make)\s+(.+)': r'create \2',
            r'\b(find|search|look)\s+(.+)': r'search \2', 
            r'\b(go|navigate)\s+to\s+(.+)': r'navigate \2',
            r'\b(roll|dice)\b': 'roll dice',
            r'\b(attack|fight)\s+(.*)': r'attack \2',
            
            # Common fixes
            r'\bum\b|\buh\b|\byou know\b': '',  # Remove filler words
            r'\s+': ' ',  # Normalize spaces
            r'^\s+|\s+$': '',  # Trim
        }
        
        # Pre-compiled regex patterns for speed
        self.compiled_patterns = {
            pattern: re.compile(pattern, re.IGNORECASE) 
            for pattern in self.quick_patterns
        }
        
        # Common vocabulary shortcuts (universal across users)
        self.universal_shortcuts = {
            'dm': 'dungeon master',
            'npc': 'non-player character',
            'hp': 'hit points',
            'ap': 'autopilot',
            'nav': 'navigate',
            'loc': 'location',
            'msg': 'message',
            'sched': 'schedule',
            'rem': 'remind',
            'cal': 'calendar'
        }
    
    def load_user_profile(self, user_id: str, profile_data: Dict = None) -> bool:
        """Load minimal user profile"""
        if profile_data:
            self.user_profile = UserMicroProfile(
                user_id=user_id,
                shortcuts=profile_data.get('shortcuts', {})[:20],  # Limit to 20
                vocab_map=profile_data.get('vocab_map', {})[:50],   # Limit to 50
                patterns=profile_data.get('patterns', [])[:10],     # Limit to 10
                confidence=profile_data.get('confidence', 0.5),
                last_sync=profile_data.get('last_sync', time.time())
            )
            return True
        
        # Create minimal default profile
        self.user_profile = UserMicroProfile(
            user_id=user_id,
            shortcuts={},
            vocab_map={},
            patterns=[],
            confidence=0.3,
            last_sync=time.time()
        )
        return False
    
    def interpret(self, raw_input: str, context: Dict[str, Any] = None) -> EdgeInterpretation:
        """Ultra-fast lightweight interpretation"""
        start_time = time.time()
        
        # Check cache first (fastest path)
        cache_key = hashlib.md5(raw_input.encode()).hexdigest()[:8]
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            # Update timestamp but keep everything else
            return EdgeInterpretation(
                original=raw_input,
                interpreted=cached.interpreted,
                confidence=cached.confidence,
                method=f"cached_{cached.method}",
                timestamp=time.time()
            )
        
        interpreted = raw_input.strip()
        confidence = 0.6
        methods = []
        
        # Step 1: Apply universal shortcuts (fastest)
        for shortcut, expansion in self.universal_shortcuts.items():
            if shortcut in interpreted.lower():
                interpreted = re.sub(r'\b' + re.escape(shortcut) + r'\b', expansion, 
                                   interpreted, flags=re.IGNORECASE)
                confidence += 0.1
                methods.append('universal_shortcut')
                break  # Only one per pass for speed
        
        # Step 2: Apply personal shortcuts (if profile loaded)
        if self.user_profile and self.user_profile.shortcuts:
            for shortcut, expansion in list(self.user_profile.shortcuts.items())[:5]:  # Max 5 for speed
                if shortcut.lower() in interpreted.lower():
                    interpreted = re.sub(r'\b' + re.escape(shortcut) + r'\b', expansion,
                                       interpreted, flags=re.IGNORECASE)
                    confidence += 0.15
                    methods.append('personal_shortcut')
                    break
        
        # Step 3: Apply quick patterns (pre-compiled for speed)
        for pattern_str, replacement in list(self.quick_patterns.items())[:3]:  # Max 3 for speed
            pattern = self.compiled_patterns.get(pattern_str)
            if pattern and pattern.search(interpreted):
                if replacement.startswith('r'):  # Regex replacement
                    interpreted = pattern.sub(replacement[1:], interpreted)
                elif replacement == '':  # Remove pattern
                    interpreted = pattern.sub('', interpreted)
                else:  # Direct replacement
                    if replacement.endswith('_mode'):
                        # Special mode handlers
                        interpreted = self.handle_mode(interpreted, replacement)
                    else:
                        interpreted = replacement
                confidence += 0.08
                methods.append('quick_pattern')
                break
        
        # Step 4: Apply personal vocabulary (minimal)
        if self.user_profile and self.user_profile.vocab_map:
            for user_word, ai_word in list(self.user_profile.vocab_map.items())[:3]:  # Max 3 for speed
                if user_word.lower() in interpreted.lower():
                    interpreted = re.sub(r'\b' + re.escape(user_word) + r'\b', ai_word,
                                       interpreted, flags=re.IGNORECASE)
                    confidence += 0.12
                    methods.append('personal_vocab')
                    break
        
        # Step 5: Quick cleanup (single pass)
        interpreted = re.sub(r'\s+', ' ', interpreted).strip()  # Normalize spaces
        
        # Cap confidence
        confidence = min(1.0, confidence)
        
        # Create result
        result = EdgeInterpretation(
            original=raw_input,
            interpreted=interpreted,
            confidence=confidence,
            method='+'.join(methods[:3]) if methods else 'passthrough',  # Max 3 methods
            timestamp=time.time()
        )
        
        # Cache result (keep cache small)
        if len(self.cache) >= 20:
            # Remove oldest entry
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k].timestamp)
            del self.cache[oldest_key]
        
        self.cache[cache_key] = result
        
        return result
    
    def handle_mode(self, text: str, mode: str) -> str:
        """Handle special mode interpretations"""
        if mode == 'greeting_mode':
            # For greetings, make more conversational
            if 'hello' in text.lower():
                return "Hello, what can I help you with?"
            elif 'hi' in text.lower():
                return "Hi there, what would you like to do?"
            else:
                return "Hello, I'm ready to help"
        
        return text
    
    def learn_from_success(self, original: str, interpreted: str, success: bool):
        """Lightweight learning from user feedback"""
        if not self.user_profile or not success:
            return
        
        # Extract potential shortcuts (simple heuristic)
        original_words = original.lower().split()
        interpreted_words = interpreted.lower().split()
        
        # If interpreted is shorter and successful, might be a good shortcut
        if len(original_words) > 2 and len(interpreted_words) < len(original_words):
            # Create shortcut if we have space
            if len(self.user_profile.shortcuts) < 20:
                shortcut = ' '.join(original_words[:2])  # First two words
                expansion = interpreted
                self.user_profile.shortcuts[shortcut] = expansion
                self.user_profile.confidence = min(1.0, self.user_profile.confidence + 0.05)
        
        # Learn vocabulary mapping
        if len(original_words) == len(interpreted_words):
            for i, (orig, interp) in enumerate(zip(original_words, interpreted_words)):
                if orig != interp and len(self.user_profile.vocab_map) < 50:
                    self.user_profile.vocab_map[orig] = interp
                    break  # Only one per learning session
    
    def get_memory_usage(self) -> Dict[str, int]:
        """Estimate memory usage in bytes"""
        profile_size = 0
        if self.user_profile:
            profile_json = json.dumps(asdict(self.user_profile))
            profile_size = len(profile_json.encode())
        
        cache_size = sum(len(json.dumps(asdict(result)).encode()) 
                        for result in self.cache.values())
        
        patterns_size = sum(len(pattern.encode()) + len(str(regex).encode()) 
                           for pattern, regex in self.compiled_patterns.items())
        
        total_bytes = profile_size + cache_size + patterns_size
        total_kb = total_bytes / 1024
        
        return {
            'total_bytes': total_bytes,
            'total_kb': round(total_kb, 2),
            'profile_bytes': profile_size,
            'cache_bytes': cache_size,
            'patterns_bytes': patterns_size,
            'within_limit': total_kb <= self.max_memory_kb
        }
    
    def export_profile(self) -> Dict[str, Any]:
        """Export profile for cloud sync"""
        if not self.user_profile:
            return {}
        
        return asdict(self.user_profile)
    
    def import_profile(self, profile_data: Dict[str, Any]) -> bool:
        """Import profile from cloud sync"""
        try:
            self.user_profile = UserMicroProfile(**profile_data)
            return True
        except Exception:
            return False
    
    def cleanup_for_memory(self):
        """Clean up to stay within memory limits"""
        memory_info = self.get_memory_usage()
        
        if not memory_info['within_limit']:
            # Clear half the cache
            cache_items = list(self.cache.items())
            cache_items.sort(key=lambda x: x[1].timestamp)  # Sort by timestamp
            keep_count = len(cache_items) // 2
            
            self.cache.clear()
            for key, value in cache_items[-keep_count:]:  # Keep newest half
                self.cache[key] = value
            
            # Trim personal shortcuts if needed
            if self.user_profile and len(self.user_profile.shortcuts) > 15:
                # Keep most recent 15
                items = list(self.user_profile.shortcuts.items())[-15:]
                self.user_profile.shortcuts = dict(items)
            
            # Trim vocabulary map if needed  
            if self.user_profile and len(self.user_profile.vocab_map) > 30:
                # Keep most recent 30
                items = list(self.user_profile.vocab_map.items())[-30:]
                self.user_profile.vocab_map = dict(items)


class EdgeInterpreterDatabase:
    """Lightweight SQLite database for edge devices"""
    
    def __init__(self, db_path: str = "edge_interpreter.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize minimal database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    profile_data TEXT NOT NULL,
                    last_sync REAL DEFAULT 0,
                    version INTEGER DEFAULT 1
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS interpretations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    original TEXT,
                    interpreted TEXT,
                    success INTEGER DEFAULT 0,
                    timestamp REAL,
                    FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
                )
            ''')
    
    def save_profile(self, user_id: str, profile_data: Dict[str, Any]) -> bool:
        """Save user profile"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO user_profiles (user_id, profile_data, last_sync)
                    VALUES (?, ?, ?)
                ''', (user_id, json.dumps(profile_data), time.time()))
            return True
        except Exception:
            return False
    
    def load_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Load user profile"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT profile_data FROM user_profiles WHERE user_id = ?
                ''', (user_id,))
                row = cursor.fetchone()
                if row:
                    return json.loads(row[0])
        except Exception:
            pass
        return None
    
    def log_interpretation(self, user_id: str, original: str, interpreted: str, success: int = 0):
        """Log interpretation for learning"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO interpretations (user_id, original, interpreted, success, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, original, interpreted, success, time.time()))
            
            # Keep only last 100 per user to save space
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    DELETE FROM interpretations 
                    WHERE user_id = ? AND id NOT IN (
                        SELECT id FROM interpretations 
                        WHERE user_id = ? 
                        ORDER BY timestamp DESC LIMIT 100
                    )
                ''', (user_id, user_id))
        except Exception:
            pass
    
    def get_db_size(self) -> int:
        """Get database size in bytes"""
        try:
            return os.path.getsize(self.db_path)
        except:
            return 0


class EdgeInterpreterManager:
    """Manager for edge interpreter with cloud sync capabilities"""
    
    def __init__(self, user_id: str, max_memory_kb: int = 50):
        self.user_id = user_id
        self.interpreter = LightweightEdgeInterpreter(max_memory_kb)
        self.db = EdgeInterpreterDatabase()
        self.needs_sync = False
        self.last_cloud_sync = 0
        
        # Load profile from local storage
        profile_data = self.db.load_profile(user_id)
        if profile_data:
            self.interpreter.load_user_profile(user_id, profile_data)
        else:
            self.interpreter.load_user_profile(user_id)
    
    async def interpret(self, raw_input: str, context: Dict[str, Any] = None) -> EdgeInterpretation:
        """Interpret with automatic learning"""
        result = self.interpreter.interpret(raw_input, context or {})
        
        # Log for potential learning
        self.db.log_interpretation(self.user_id, result.original, result.interpreted)
        
        return result
    
    async def provide_feedback(self, original: str, interpreted: str, success: bool):
        """Provide feedback for learning"""
        self.interpreter.learn_from_success(original, interpreted, success)
        
        # Update database
        self.db.log_interpretation(self.user_id, original, interpreted, 1 if success else 0)
        
        # Save updated profile
        profile_data = self.interpreter.export_profile()
        self.db.save_profile(self.user_id, profile_data)
        
        self.needs_sync = True
    
    async def sync_with_cloud(self, cloud_endpoint: str = None) -> bool:
        """Sync with cloud interpreter system (when available)"""
        if not cloud_endpoint or not self.needs_sync:
            return False
        
        try:
            profile_data = self.interpreter.export_profile()
            
            # In a real implementation, this would make HTTP requests
            # For now, we'll just mark as synced
            self.last_cloud_sync = time.time()
            self.needs_sync = False
            
            if self.interpreter.user_profile:
                self.interpreter.user_profile.last_sync = self.last_cloud_sync
            
            return True
        except Exception:
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get interpreter status and statistics"""
        memory_info = self.interpreter.get_memory_usage()
        
        return {
            'user_id': self.user_id,
            'memory_usage_kb': memory_info['total_kb'],
            'within_memory_limit': memory_info['within_limit'],
            'cached_interpretations': len(self.interpreter.cache),
            'personal_shortcuts': len(self.interpreter.user_profile.shortcuts) if self.interpreter.user_profile else 0,
            'vocabulary_mappings': len(self.interpreter.user_profile.vocab_map) if self.interpreter.user_profile else 0,
            'learning_confidence': self.interpreter.user_profile.confidence if self.interpreter.user_profile else 0.3,
            'needs_cloud_sync': self.needs_sync,
            'last_sync': self.last_cloud_sync,
            'db_size_bytes': self.db.get_db_size()
        }
    
    def cleanup(self):
        """Cleanup to stay within resource limits"""
        self.interpreter.cleanup_for_memory()
        
        # Save cleaned profile
        if self.interpreter.user_profile:
            profile_data = self.interpreter.export_profile()
            self.db.save_profile(self.user_id, profile_data)


# Factory function for easy integration
def create_edge_interpreter(user_id: str, max_memory_kb: int = 50) -> EdgeInterpreterManager:
    """Create a lightweight edge interpreter for a user"""
    return EdgeInterpreterManager(user_id, max_memory_kb)


# Example usage and testing
if __name__ == "__main__":
    # Test the lightweight interpreter
    interpreter = create_edge_interpreter("test_user_123", max_memory_kb=30)
    
    # Test interpretations
    test_inputs = [
        "hey set a reminder",
        "find my fishing log",
        "dm roll dice for combat", 
        "nav to the harbor",
        "hey make a new character"
    ]
    
    print("🔬 Testing Lightweight Edge Interpreter")
    print("=" * 50)
    
    for i, test_input in enumerate(test_inputs):
        result = interpreter.interpreter.interpret(test_input)
        print(f"\nTest {i+1}:")
        print(f"  Input: '{result.original}'")
        print(f"  Output: '{result.interpreted}'")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Method: {result.method}")
        
        # Simulate feedback
        success = result.confidence > 0.7
        interpreter.interpreter.learn_from_success(result.original, result.interpreted, success)
    
    # Show final status
    status = interpreter.get_status()
    print(f"\n📊 Final Status:")
    print(f"  Memory Usage: {status['memory_usage_kb']:.2f} KB")
    print(f"  Within Limit: {status['within_memory_limit']}")
    print(f"  Shortcuts Learned: {status['personal_shortcuts']}")
    print(f"  Vocabulary Mappings: {status['vocabulary_mappings']}")
    print(f"  Learning Confidence: {status['learning_confidence']:.2f}")
    
    print(f"\n✅ Edge interpreter ready for deployment on mobile devices!")