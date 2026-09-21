#!/usr/bin/env python3
"""
System-Level Input Interpreter
Ultra-lightweight system layer that learns user's typing patterns, 
common mistakes, and input habits to automatically improve all app interactions
"""

import time
import json
import sqlite3
import re
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from datetime import datetime
import threading
import hashlib

@dataclass
class InputEvent:
    """Represents a single input event"""
    text: str
    app_name: str
    input_type: str  # 'typing', 'voice', 'paste', 'autocomplete'
    timestamp: float
    corrected: bool = False
    user_backspaced: bool = False
    final_text: str = ""

@dataclass
class TypingPattern:
    """Represents a learned typing pattern"""
    trigger: str  # What user types
    correction: str  # What they meant
    confidence: float
    frequency: int
    apps_used: List[str]
    last_seen: float

@dataclass
class UserInputProfile:
    """Personal typing and input profile"""
    user_id: str
    typing_patterns: Dict[str, TypingPattern]
    common_typos: Dict[str, str]  # mistake -> correction
    word_shortcuts: Dict[str, str]  # shortcut -> expansion
    context_corrections: Dict[str, Dict[str, str]]  # app -> {mistake -> correction}
    typing_speed: float  # words per minute
    error_rate: float  # mistakes per word
    preferred_autocomplete: bool
    learning_confidence: float

class SystemInputMonitor:
    """Monitors system-wide input events"""
    
    def __init__(self):
        self.recent_events: deque = deque(maxlen=50)  # Last 50 input events
        self.typing_sessions: Dict[str, List[InputEvent]] = defaultdict(list)
        self.active_session: Optional[str] = None
        self.session_timeout = 30  # seconds
        
    def log_input_event(self, text: str, app_name: str, input_type: str = 'typing') -> str:
        """Log an input event and return session ID"""
        timestamp = time.time()
        
        # Create or continue session
        if (not self.active_session or 
            timestamp - self.recent_events[-1].timestamp > self.session_timeout):
            self.active_session = f"session_{int(timestamp)}"
        
        event = InputEvent(
            text=text,
            app_name=app_name,
            input_type=input_type,
            timestamp=timestamp
        )
        
        self.recent_events.append(event)
        self.typing_sessions[self.active_session].append(event)
        
        return self.active_session
    
    def log_backspace_correction(self, session_id: str, original: str, corrected: str):
        """Log when user backspaces to correct something"""
        if session_id in self.typing_sessions and self.typing_sessions[session_id]:
            last_event = self.typing_sessions[session_id][-1]
            if last_event.text == original:
                last_event.user_backspaced = True
                last_event.final_text = corrected
    
    def get_recent_context(self, app_name: str, window: int = 5) -> List[InputEvent]:
        """Get recent input context for an app"""
        app_events = [event for event in self.recent_events 
                     if event.app_name == app_name]
        return list(app_events[-window:])

class SystemInputInterpreter:
    """System-level input interpreter that learns across all apps"""
    
    def __init__(self, user_id: str, db_path: str = "system_input.db"):
        self.user_id = user_id
        self.db_path = db_path
        self.profile = UserInputProfile(
            user_id=user_id,
            typing_patterns={},
            common_typos={},
            word_shortcuts={},
            context_corrections={},
            typing_speed=40.0,
            error_rate=0.05,
            preferred_autocomplete=True,
            learning_confidence=0.3
        )
        
        self.monitor = SystemInputMonitor()
        self.init_database()
        self.load_profile()
        
        # Real-time learning buffer
        self.learning_buffer = deque(maxlen=100)
        self.last_save = time.time()
        self.save_interval = 60  # Save every minute
        
        # Lightweight pattern matching for speed
        self.compiled_patterns = {}
        self.update_compiled_patterns()
    
    def init_database(self):
        """Initialize SQLite database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    profile_data TEXT NOT NULL,
                    last_updated REAL DEFAULT 0
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS input_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    app_name TEXT,
                    original_text TEXT,
                    corrected_text TEXT,
                    correction_type TEXT,
                    timestamp REAL,
                    session_id TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS typing_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    trigger_text TEXT,
                    correction_text TEXT,
                    confidence REAL,
                    frequency INTEGER,
                    apps_used TEXT,
                    last_seen REAL
                )
            ''')
    
    def load_profile(self):
        """Load user profile from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT profile_data FROM user_profiles WHERE user_id = ?
                ''', (self.user_id,))
                row = cursor.fetchone()
                
                if row:
                    profile_data = json.loads(row[0])
                    self.profile = UserInputProfile(**profile_data)
        except Exception as e:
            # Use default profile if loading fails
            pass
    
    def save_profile(self):
        """Save user profile to database"""
        try:
            profile_data = asdict(self.profile)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO user_profiles (user_id, profile_data, last_updated)
                    VALUES (?, ?, ?)
                ''', (self.user_id, json.dumps(profile_data), time.time()))
        except Exception:
            pass
    
    def update_compiled_patterns(self):
        """Update compiled regex patterns for fast matching"""
        self.compiled_patterns.clear()
        
        # Compile typing patterns
        for trigger, pattern in list(self.profile.typing_patterns.items())[:20]:  # Limit for speed
            try:
                self.compiled_patterns[trigger] = re.compile(r'\b' + re.escape(trigger) + r'\b', re.IGNORECASE)
            except:
                pass
        
        # Compile common typos
        for typo, correction in list(self.profile.common_typos.items())[:30]:  # Limit for speed
            try:
                self.compiled_patterns[typo] = re.compile(r'\b' + re.escape(typo) + r'\b', re.IGNORECASE)
            except:
                pass
    
    def interpret_input(self, text: str, app_name: str, 
                       input_type: str = 'typing') -> Tuple[str, float, List[str]]:
        """
        Interpret and potentially correct user input
        Returns: (corrected_text, confidence, corrections_applied)
        """
        if not text.strip():
            return text, 1.0, []
        
        # Log the input event
        session_id = self.monitor.log_input_event(text, app_name, input_type)
        
        corrected = text
        confidence = 0.8
        corrections_applied = []
        
        # Apply learned typing patterns (fastest path)
        corrected, pattern_confidence, pattern_corrections = self._apply_typing_patterns(corrected, app_name)
        if pattern_corrections:
            confidence = (confidence + pattern_confidence) / 2
            corrections_applied.extend(pattern_corrections)
        
        # Apply common typo corrections
        corrected, typo_confidence, typo_corrections = self._apply_typo_corrections(corrected)
        if typo_corrections:
            confidence = (confidence + typo_confidence) / 2
            corrections_applied.extend(typo_corrections)
        
        # Apply word shortcuts and expansions
        corrected, shortcut_confidence, shortcut_corrections = self._apply_shortcuts(corrected, app_name)
        if shortcut_corrections:
            confidence = (confidence + shortcut_confidence) / 2
            corrections_applied.extend(shortcut_corrections)
        
        # Apply context-specific corrections
        corrected, context_confidence, context_corrections = self._apply_context_corrections(corrected, app_name)
        if context_corrections:
            confidence = (confidence + context_confidence) / 2
            corrections_applied.extend(context_corrections)
        
        # Save periodically
        if time.time() - self.last_save > self.save_interval:
            self.save_profile()
            self.last_save = time.time()
        
        return corrected, confidence, corrections_applied
    
    def _apply_typing_patterns(self, text: str, app_name: str) -> Tuple[str, float, List[str]]:
        """Apply learned typing patterns"""
        corrected = text
        confidence = 0.8
        applied = []
        
        # Apply most confident patterns first
        patterns_by_confidence = sorted(
            self.profile.typing_patterns.items(), 
            key=lambda x: x[1].confidence, 
            reverse=True
        )
        
        for trigger, pattern in patterns_by_confidence[:5]:  # Max 5 for speed
            if pattern.confidence < 0.6:  # Skip low-confidence patterns
                break
                
            if trigger in self.compiled_patterns:
                regex = self.compiled_patterns[trigger]
                if regex.search(corrected):
                    corrected = regex.sub(pattern.correction, corrected)
                    confidence = min(1.0, confidence + 0.1)
                    applied.append(f"pattern:{trigger}→{pattern.correction}")
                    
                    # Update pattern frequency
                    pattern.frequency += 1
                    pattern.last_seen = time.time()
                    if app_name not in pattern.apps_used:
                        pattern.apps_used.append(app_name)
                    
                    break  # Only one pattern per input for speed
        
        return corrected, confidence, applied
    
    def _apply_typo_corrections(self, text: str) -> Tuple[str, float, List[str]]:
        """Apply common typo corrections"""
        corrected = text
        confidence = 0.8
        applied = []
        
        # Apply most common typos first
        sorted_typos = sorted(
            self.profile.common_typos.items(), 
            key=lambda x: len(x[0]), 
            reverse=True  # Longer typos first to avoid partial matches
        )
        
        for typo, correction in sorted_typos[:10]:  # Max 10 for speed
            if typo in self.compiled_patterns:
                regex = self.compiled_patterns[typo]
                if regex.search(corrected):
                    corrected = regex.sub(correction, corrected)
                    confidence = min(1.0, confidence + 0.15)
                    applied.append(f"typo:{typo}→{correction}")
                    break  # Only one typo correction per input
        
        return corrected, confidence, applied
    
    def _apply_shortcuts(self, text: str, app_name: str) -> Tuple[str, float, List[str]]:
        """Apply word shortcuts and expansions"""
        corrected = text
        confidence = 0.8
        applied = []
        
        words = corrected.split()
        corrected_words = []
        
        for word in words:
            word_lower = word.lower()
            
            # Check personal shortcuts first
            if word_lower in self.profile.word_shortcuts:
                expansion = self.profile.word_shortcuts[word_lower]
                corrected_words.append(expansion)
                applied.append(f"shortcut:{word}→{expansion}")
                confidence = min(1.0, confidence + 0.1)
            
            # Check universal shortcuts for app
            elif app_name in ['dmlog', 'fishinglog', 'personallog']:
                universal_shortcuts = self._get_universal_shortcuts(app_name)
                if word_lower in universal_shortcuts:
                    expansion = universal_shortcuts[word_lower]
                    corrected_words.append(expansion)
                    applied.append(f"universal:{word}→{expansion}")
                    confidence = min(1.0, confidence + 0.05)
                else:
                    corrected_words.append(word)
            else:
                corrected_words.append(word)
        
        corrected = ' '.join(corrected_words)
        return corrected, confidence, applied
    
    def _apply_context_corrections(self, text: str, app_name: str) -> Tuple[str, float, List[str]]:
        """Apply app-specific context corrections"""
        corrected = text
        confidence = 0.8
        applied = []
        
        if app_name in self.profile.context_corrections:
            app_corrections = self.profile.context_corrections[app_name]
            
            for mistake, correction in list(app_corrections.items())[:5]:  # Max 5 for speed
                if mistake.lower() in corrected.lower():
                    corrected = re.sub(r'\b' + re.escape(mistake) + r'\b', correction,
                                     corrected, flags=re.IGNORECASE)
                    applied.append(f"context:{mistake}→{correction}")
                    confidence = min(1.0, confidence + 0.12)
                    break
        
        return corrected, confidence, applied
    
    def _get_universal_shortcuts(self, app_name: str) -> Dict[str, str]:
        """Get universal shortcuts for specific apps"""
        shortcuts = {
            'dmlog': {
                'dm': 'dungeon master',
                'npc': 'non-player character',
                'hp': 'hit points',
                'ac': 'armor class',
                'd20': 'twenty-sided die',
                'char': 'character'
            },
            'fishinglog': {
                'ap': 'autopilot',
                'gps': 'navigation',
                'loc': 'location',
                'wx': 'weather',
                'fish': 'catch'
            },
            'personallog': {
                'sched': 'schedule',
                'rem': 'reminder',
                'cal': 'calendar',
                'meet': 'meeting',
                'appt': 'appointment'
            }
        }
        
        return shortcuts.get(app_name, {})
    
    def learn_from_correction(self, original: str, corrected: str, app_name: str, 
                            correction_type: str = 'user_backspace'):
        """Learn from user corrections (backspace, manual edit, etc.)"""
        if original == corrected or not original.strip() or not corrected.strip():
            return
        
        timestamp = time.time()
        
        # Add to learning buffer
        self.learning_buffer.append({
            'original': original,
            'corrected': corrected,
            'app_name': app_name,
            'correction_type': correction_type,
            'timestamp': timestamp
        })
        
        # Extract learning patterns
        self._extract_learning_patterns(original, corrected, app_name)
        
        # Save to database
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO input_events 
                    (user_id, app_name, original_text, corrected_text, correction_type, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (self.user_id, app_name, original, corrected, correction_type, timestamp))
        except Exception:
            pass
    
    def _extract_learning_patterns(self, original: str, corrected: str, app_name: str):
        """Extract patterns from user corrections"""
        
        # Learn word-level corrections
        orig_words = original.split()
        corr_words = corrected.split()
        
        if len(orig_words) == len(corr_words):
            # Word-by-word corrections (likely typos)
            for orig_word, corr_word in zip(orig_words, corr_words):
                if orig_word.lower() != corr_word.lower() and len(orig_word) > 2:
                    # Learn typo correction
                    self.profile.common_typos[orig_word.lower()] = corr_word.lower()
                    
                    # Update compiled patterns
                    self.compiled_patterns[orig_word.lower()] = re.compile(
                        r'\b' + re.escape(orig_word.lower()) + r'\b', re.IGNORECASE
                    )
        
        elif len(orig_words) > len(corr_words):
            # User shortened something (potential shortcut)
            if len(corr_words) == 1 and len(orig_words) <= 3:
                shortcut_phrase = ' '.join(orig_words).lower()
                expansion = corr_words[0].lower()
                self.profile.word_shortcuts[shortcut_phrase] = expansion
        
        elif len(orig_words) < len(corr_words):
            # User expanded something (learn expansion pattern)
            if len(orig_words) == 1 and len(corr_words) <= 3:
                shortcut = orig_words[0].lower()
                expansion = ' '.join(corr_words).lower()
                self.profile.word_shortcuts[shortcut] = expansion
        
        # Learn app-specific context corrections
        if app_name not in self.profile.context_corrections:
            self.profile.context_corrections[app_name] = {}
        
        # If this is a pattern we see across apps, make it a typing pattern
        pattern_key = f"{original}→{corrected}"
        if pattern_key not in self.profile.typing_patterns:
            self.profile.typing_patterns[pattern_key] = TypingPattern(
                trigger=original.lower(),
                correction=corrected.lower(),
                confidence=0.6,
                frequency=1,
                apps_used=[app_name],
                last_seen=time.time()
            )
        else:
            pattern = self.profile.typing_patterns[pattern_key]
            pattern.frequency += 1
            pattern.confidence = min(1.0, pattern.confidence + 0.1)
            pattern.last_seen = time.time()
            if app_name not in pattern.apps_used:
                pattern.apps_used.append(app_name)
        
        # Update learning confidence
        self.profile.learning_confidence = min(1.0, self.profile.learning_confidence + 0.02)
        
        # Update compiled patterns
        self.update_compiled_patterns()
    
    def get_typing_stats(self) -> Dict[str, Any]:
        """Get typing statistics and learning progress"""
        total_patterns = len(self.profile.typing_patterns)
        total_typos = len(self.profile.common_typos)
        total_shortcuts = len(self.profile.word_shortcuts)
        
        # Calculate confidence distribution
        if self.profile.typing_patterns:
            confidences = [p.confidence for p in self.profile.typing_patterns.values()]
            avg_confidence = sum(confidences) / len(confidences)
        else:
            avg_confidence = 0.0
        
        return {
            'user_id': self.user_id,
            'total_typing_patterns': total_patterns,
            'total_typo_corrections': total_typos,
            'total_shortcuts': total_shortcuts,
            'learning_confidence': self.profile.learning_confidence,
            'average_pattern_confidence': avg_confidence,
            'typing_speed_wpm': self.profile.typing_speed,
            'estimated_error_rate': self.profile.error_rate,
            'apps_with_context': list(self.profile.context_corrections.keys()),
            'recent_corrections': len(self.learning_buffer)
        }
    
    def export_for_sync(self) -> Dict[str, Any]:
        """Export profile for cloud sync"""
        return asdict(self.profile)
    
    def import_from_sync(self, profile_data: Dict[str, Any]) -> bool:
        """Import profile from cloud sync"""
        try:
            # Merge with existing profile (keep best patterns)
            imported = UserInputProfile(**profile_data)
            
            # Merge typing patterns (keep higher confidence)
            for key, pattern in imported.typing_patterns.items():
                if (key not in self.profile.typing_patterns or 
                    pattern.confidence > self.profile.typing_patterns[key].confidence):
                    self.profile.typing_patterns[key] = pattern
            
            # Merge typos and shortcuts
            self.profile.common_typos.update(imported.common_typos)
            self.profile.word_shortcuts.update(imported.word_shortcuts)
            
            # Update context corrections
            for app, corrections in imported.context_corrections.items():
                if app not in self.profile.context_corrections:
                    self.profile.context_corrections[app] = {}
                self.profile.context_corrections[app].update(corrections)
            
            # Update confidence
            self.profile.learning_confidence = max(
                self.profile.learning_confidence, 
                imported.learning_confidence
            )
            
            self.update_compiled_patterns()
            self.save_profile()
            return True
            
        except Exception:
            return False


class SystemInputService:
    """Background service for system-wide input interpretation"""
    
    def __init__(self):
        self.interpreters: Dict[str, SystemInputInterpreter] = {}
        self.active = False
        self.lock = threading.Lock()
    
    def get_interpreter(self, user_id: str) -> SystemInputInterpreter:
        """Get or create interpreter for user"""
        with self.lock:
            if user_id not in self.interpreters:
                self.interpreters[user_id] = SystemInputInterpreter(user_id)
            return self.interpreters[user_id]
    
    def interpret_input(self, user_id: str, text: str, app_name: str, 
                       input_type: str = 'typing') -> Tuple[str, float, List[str]]:
        """System-wide input interpretation entry point"""
        interpreter = self.get_interpreter(user_id)
        return interpreter.interpret_input(text, app_name, input_type)
    
    def report_correction(self, user_id: str, original: str, corrected: str, 
                         app_name: str, correction_type: str = 'user_backspace'):
        """Report user correction for learning"""
        interpreter = self.get_interpreter(user_id)
        interpreter.learn_from_correction(original, corrected, app_name, correction_type)
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user typing statistics"""
        interpreter = self.get_interpreter(user_id)
        return interpreter.get_typing_stats()


# Global system input service
system_input_service = SystemInputService()

# Easy integration functions
def interpret_system_input(user_id: str, text: str, app_name: str) -> Tuple[str, float, List[str]]:
    """Main entry point for system-wide input interpretation"""
    return system_input_service.interpret_input(user_id, text, app_name)

def report_user_correction(user_id: str, original: str, corrected: str, app_name: str):
    """Report when user corrects something (backspace, edit, etc.)"""
    system_input_service.report_correction(user_id, original, corrected, app_name)

def get_typing_insights(user_id: str) -> Dict[str, Any]:
    """Get insights about user's typing patterns"""
    return system_input_service.get_user_stats(user_id)


# Example integration for web apps (JavaScript callable)
def create_web_integration_script() -> str:
    """Generate JavaScript for web integration"""
    return '''
// SuperInstance System Input Interpreter - Web Integration
class SystemInputInterpreter {
    constructor(userId, appName) {
        this.userId = userId;
        this.appName = appName;
        this.correctionBuffer = [];
    }
    
    // Call this on every input event
    async interpretInput(text, inputType = 'typing') {
        try {
            const response = await fetch('/api/interpret-input', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    user_id: this.userId,
                    text: text,
                    app_name: this.appName,
                    input_type: inputType
                })
            });
            
            const result = await response.json();
            return {
                corrected: result.corrected_text,
                confidence: result.confidence,
                corrections: result.corrections_applied
            };
        } catch (error) {
            return {corrected: text, confidence: 1.0, corrections: []};
        }
    }
    
    // Call this when user backspaces/corrects
    async reportCorrection(original, corrected) {
        try {
            await fetch('/api/report-correction', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    user_id: this.userId,
                    original: original,
                    corrected: corrected,
                    app_name: this.appName,
                    correction_type: 'user_edit'
                })
            });
        } catch (error) {
            // Silently fail - learning is optional
        }
    }
    
    // Auto-attach to input elements
    attachToElement(element) {
        let lastValue = '';
        
        element.addEventListener('input', async (e) => {
            const currentValue = e.target.value;
            
            // Detect backspace corrections
            if (currentValue.length < lastValue.length) {
                const removed = lastValue.substring(currentValue.length);
                if (removed.length > 0) {
                    // User backspaced - potential correction learning
                    setTimeout(() => {
                        const finalValue = e.target.value;
                        if (finalValue !== lastValue && finalValue.length >= currentValue.length) {
                            this.reportCorrection(lastValue, finalValue);
                        }
                    }, 1000); // Wait for user to finish typing
                }
            }
            
            // Apply real-time interpretation for longer inputs
            if (currentValue.length > 3) {
                const result = await this.interpretInput(currentValue);
                if (result.corrected !== currentValue && result.confidence > 0.8) {
                    // Suggest correction (don't auto-apply to avoid disrupting user)
                    this.showSuggestion(element, result.corrected, result.corrections);
                }
            }
            
            lastValue = currentValue;
        });
    }
    
    showSuggestion(element, suggestion, corrections) {
        // Create subtle suggestion UI
        // Implementation depends on your UI framework
        console.log(`Suggestion for "${element.value}": "${suggestion}" (${corrections.join(', ')})`);
    }
}

// Auto-initialize for SuperInstance apps
if (window.SuperInstance) {
    const userId = window.SuperInstance.currentUser?.id || 'anonymous';
    const appName = window.SuperInstance.currentApp || 'web';
    
    window.inputInterpreter = new SystemInputInterpreter(userId, appName);
    
    // Auto-attach to all text inputs
    document.addEventListener('DOMContentLoaded', () => {
        const inputs = document.querySelectorAll('input[type="text"], textarea');
        inputs.forEach(input => window.inputInterpreter.attachToElement(input));
    });
}
'''

if __name__ == "__main__":
    # Test the system input interpreter
    interpreter = SystemInputInterpreter("test_user")
    
    print("🔧 Testing System Input Interpreter")
    print("=" * 50)
    
    # Simulate user typing with mistakes
    test_cases = [
        ("helo world", "dmlog", "hello world"),  # typo
        ("dm roll dice", "dmlog", None),  # shortcut
        ("sched a meeting", "personallog", None),  # shortcut
        ("set autopilto", "fishinglog", "set autopilot"),  # typo
    ]
    
    for original, app, expected_correction in test_cases:
        # Initial interpretation
        corrected, confidence, applied = interpreter.interpret_input(original, app)
        print(f"\nInput: '{original}' in {app}")
        print(f"Output: '{corrected}' (confidence: {confidence:.2f})")
        print(f"Applied: {applied}")
        
        # Simulate user correction if provided
        if expected_correction:
            interpreter.learn_from_correction(original, expected_correction, app)
            print(f"User corrected to: '{expected_correction}' - Learning applied!")
    
    # Show final stats
    stats = interpreter.get_typing_stats()
    print(f"\n📊 Final Stats:")
    print(f"  Typing patterns: {stats['total_typing_patterns']}")
    print(f"  Typo corrections: {stats['total_typo_corrections']}")  
    print(f"  Shortcuts: {stats['total_shortcuts']}")
    print(f"  Learning confidence: {stats['learning_confidence']:.2f}")
    
    print(f"\n✅ System input interpreter ready for deployment!")