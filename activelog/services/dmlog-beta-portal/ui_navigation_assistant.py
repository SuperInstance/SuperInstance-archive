#!/usr/bin/env python3
"""
UI Navigation Assistant
Intelligent UI assistant that learns user navigation patterns and suggests improvements
Detects when users struggle to find options or frequently access deep settings
"""

import json
import sqlite3
import time
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class NavigationEvent:
    """Represents a navigation event"""
    user_id: str
    page_path: str
    action: str  # 'click', 'hover', 'search', 'back', 'scroll'
    element_id: str
    element_text: str
    timestamp: float
    session_id: str
    time_spent: float  # seconds spent on page/element
    success: bool  # whether user found what they were looking for

@dataclass
class NavigationPattern:
    """Detected navigation pattern"""
    pattern_id: str
    pattern_type: str  # 'struggle_finding', 'frequent_deep_access', 'inefficient_path'
    user_id: str
    description: str
    frequency: int
    confidence: float
    suggested_solution: str
    pages_involved: List[str]
    last_detected: float

@dataclass
class UIOptimization:
    """UI optimization suggestion"""
    optimization_id: str
    user_id: str
    optimization_type: str  # 'add_shortcut', 'move_option', 'add_search', 'create_favorites'
    title: str
    description: str
    implementation: Dict[str, Any]  # How to implement the optimization
    confidence: float
    expected_benefit: str
    created_at: float

class UINavigationMonitor:
    """Monitors user navigation patterns"""
    
    def __init__(self):
        self.user_sessions: Dict[str, List[NavigationEvent]] = defaultdict(list)
        self.navigation_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.page_visit_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.search_attempts: Dict[str, List[Dict]] = defaultdict(list)
        self.session_timeout = 30 * 60  # 30 minutes
    
    def track_navigation(self, user_id: str, page_path: str, action: str, 
                        element_id: str = '', element_text: str = '', 
                        session_id: str = '', time_spent: float = 0.0) -> str:
        """Track a navigation event"""
        
        timestamp = time.time()
        
        event = NavigationEvent(
            user_id=user_id,
            page_path=page_path,
            action=action,
            element_id=element_id,
            element_text=element_text,
            timestamp=timestamp,
            session_id=session_id or f"session_{int(timestamp)}",
            time_spent=time_spent,
            success=False  # Will be updated based on subsequent actions
        )
        
        self.user_sessions[user_id].append(event)
        self.navigation_history[user_id].append(event)
        self.page_visit_counts[user_id][page_path] += 1
        
        return event.session_id
    
    def track_search_attempt(self, user_id: str, search_query: str, 
                           results_found: bool, page_path: str):
        """Track when user searches for something"""
        self.search_attempts[user_id].append({
            'query': search_query,
            'found': results_found,
            'page': page_path,
            'timestamp': time.time()
        })
    
    def mark_navigation_success(self, user_id: str, session_id: str):
        """Mark recent navigation as successful"""
        user_events = self.user_sessions[user_id]
        for event in reversed(user_events[-10:]):  # Check last 10 events
            if event.session_id == session_id:
                event.success = True
                break
    
    def get_recent_navigation_pattern(self, user_id: str, minutes: int = 10) -> List[NavigationEvent]:
        """Get recent navigation pattern for analysis"""
        cutoff_time = time.time() - (minutes * 60)
        user_events = self.navigation_history[user_id]
        
        return [event for event in user_events if event.timestamp > cutoff_time]

class UINavigationAssistant:
    """Intelligent assistant that analyzes navigation and suggests improvements"""
    
    def __init__(self, db_path: str = "ui_navigation.db"):
        self.db_path = db_path
        self.monitor = UINavigationMonitor()
        self.detected_patterns: Dict[str, List[NavigationPattern]] = defaultdict(list)
        self.generated_optimizations: Dict[str, List[UIOptimization]] = defaultdict(list)
        
        self.init_database()
        
        # Common UI paths and their complexity scores
        self.ui_complexity = {
            '/dashboard': 1,
            '/gaming/interface': 2,
            '/settings': 3,
            '/settings/advanced': 5,
            '/settings/audio': 4,
            '/settings/display': 4,
            '/settings/ai': 6,
            '/settings/account': 4,
            '/help': 2,
            '/stats': 3
        }
        
        # Define what constitutes "struggling" behavior
        self.struggle_indicators = {
            'multiple_back_clicks': 3,  # Going back 3+ times
            'long_hover_time': 5.0,    # Hovering for 5+ seconds
            'repeated_page_visits': 4,  # Visiting same page 4+ times
            'search_after_browse': True, # Searching after browsing
            'deep_path_frequency': 3    # Accessing deep paths 3+ times per session
        }
    
    def init_database(self):
        """Initialize SQLite database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS navigation_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    page_path TEXT NOT NULL,
                    action TEXT NOT NULL,
                    element_id TEXT,
                    element_text TEXT,
                    timestamp REAL NOT NULL,
                    session_id TEXT NOT NULL,
                    time_spent REAL DEFAULT 0.0,
                    success BOOLEAN DEFAULT FALSE
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS navigation_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_id TEXT UNIQUE NOT NULL,
                    user_id TEXT NOT NULL,
                    pattern_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    frequency INTEGER DEFAULT 1,
                    confidence REAL DEFAULT 0.5,
                    suggested_solution TEXT,
                    pages_involved TEXT,
                    last_detected REAL NOT NULL
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS ui_optimizations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    optimization_id TEXT UNIQUE NOT NULL,
                    user_id TEXT NOT NULL,
                    optimization_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    implementation TEXT NOT NULL,
                    confidence REAL DEFAULT 0.5,
                    expected_benefit TEXT,
                    created_at REAL NOT NULL,
                    dismissed BOOLEAN DEFAULT FALSE,
                    implemented BOOLEAN DEFAULT FALSE
                )
            ''')
    
    def track_user_navigation(self, user_id: str, page_path: str, action: str, 
                            element_id: str = '', element_text: str = '', 
                            session_id: str = '', time_spent: float = 0.0):
        """Track navigation and analyze for patterns"""
        
        session_id = self.monitor.track_navigation(
            user_id, page_path, action, element_id, element_text, session_id, time_spent
        )
        
        # Store in database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO navigation_events 
                (user_id, page_path, action, element_id, element_text, timestamp, session_id, time_spent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, page_path, action, element_id, element_text, time.time(), session_id, time_spent))
        
        # Analyze for patterns in real-time
        self._analyze_user_patterns(user_id)
        
        return session_id
    
    def _analyze_user_patterns(self, user_id: str):
        """Analyze user navigation patterns and detect issues"""
        
        recent_events = self.monitor.get_recent_navigation_pattern(user_id, minutes=15)
        if len(recent_events) < 5:  # Need enough data
            return
        
        # Detect struggle patterns
        self._detect_struggle_finding_options(user_id, recent_events)
        self._detect_frequent_deep_access(user_id, recent_events)
        self._detect_inefficient_navigation(user_id, recent_events)
    
    def _detect_struggle_finding_options(self, user_id: str, events: List[NavigationEvent]):
        """Detect when user struggles to find options"""
        
        # Pattern 1: Multiple back clicks in short time
        back_clicks = [e for e in events if e.action == 'back']
        if len(back_clicks) >= self.struggle_indicators['multiple_back_clicks']:
            self._create_struggle_pattern(
                user_id, 
                'struggle_finding', 
                f"User clicked back {len(back_clicks)} times - likely struggling to find something",
                [e.page_path for e in back_clicks],
                "Add prominent navigation or search functionality"
            )
        
        # Pattern 2: Repeated visits to same page without action
        page_visits = defaultdict(int)
        for event in events:
            if event.action == 'click':
                page_visits[event.page_path] += 1
        
        for page, visits in page_visits.items():
            if visits >= self.struggle_indicators['repeated_page_visits']:
                self._create_struggle_pattern(
                    user_id,
                    'struggle_finding',
                    f"User visited {page} {visits} times without success",
                    [page],
                    f"Add contextual help or better navigation on {page}"
                )
        
        # Pattern 3: Long hover times (user reading/searching)
        long_hovers = [e for e in events if e.action == 'hover' and e.time_spent > self.struggle_indicators['long_hover_time']]
        if len(long_hovers) >= 3:
            affected_pages = list(set(e.page_path for e in long_hovers))
            self._create_struggle_pattern(
                user_id,
                'struggle_finding',
                f"User spent long time hovering on {len(affected_pages)} pages - seeking specific option",
                affected_pages,
                "Add tooltips or improve option visibility"
            )
    
    def _detect_frequent_deep_access(self, user_id: str, events: List[NavigationEvent]):
        """Detect when user frequently accesses deep/complex options"""
        
        # Count visits to complex pages
        complex_visits = defaultdict(int)
        for event in events:
            complexity = self.ui_complexity.get(event.page_path, 1)
            if complexity >= 4:  # Deep/complex pages
                complex_visits[event.page_path] += 1
        
        for page, visits in complex_visits.items():
            if visits >= self.struggle_indicators['deep_path_frequency']:
                complexity = self.ui_complexity.get(page, 1)
                
                self._create_struggle_pattern(
                    user_id,
                    'frequent_deep_access',
                    f"User frequently accesses {page} (complexity: {complexity}) - {visits} times",
                    [page],
                    f"Create shortcut or move common options from {page} to main interface"
                )
    
    def _detect_inefficient_navigation(self, user_id: str, events: List[NavigationEvent]):
        """Detect inefficient navigation patterns"""
        
        # Look for patterns where user goes through many steps to reach a destination
        navigation_sequences = self._extract_navigation_sequences(events)
        
        for sequence in navigation_sequences:
            if len(sequence) >= 5:  # Long navigation path
                start_page = sequence[0].page_path
                end_page = sequence[-1].page_path
                
                self._create_struggle_pattern(
                    user_id,
                    'inefficient_path',
                    f"User took {len(sequence)} steps to go from {start_page} to {end_page}",
                    [e.page_path for e in sequence],
                    f"Add direct link from {start_page} to {end_page}"
                )
    
    def _extract_navigation_sequences(self, events: List[NavigationEvent]) -> List[List[NavigationEvent]]:
        """Extract navigation sequences (sequences of page visits)"""\n        sequences = []\n        current_sequence = []\n        \n        for event in events:\n            if event.action == 'click' and event.page_path:\n                current_sequence.append(event)\n            else:\n                if len(current_sequence) >= 2:\n                    sequences.append(current_sequence.copy())\n                current_sequence = []\n        \n        if len(current_sequence) >= 2:\n            sequences.append(current_sequence)\n        \n        return sequences\n    \n    def _create_struggle_pattern(self, user_id: str, pattern_type: str, description: str, \n                               pages: List[str], suggested_solution: str):\n        \"\"\"Create a detected struggle pattern\"\"\"\n        \n        pattern_id = f\"{user_id}_{pattern_type}_{hash(''.join(pages))}_{int(time.time())}\"\n        \n        pattern = NavigationPattern(\n            pattern_id=pattern_id,\n            pattern_type=pattern_type,\n            user_id=user_id,\n            description=description,\n            frequency=1,\n            confidence=0.7,\n            suggested_solution=suggested_solution,\n            pages_involved=pages,\n            last_detected=time.time()\n        )\n        \n        # Check if similar pattern already exists\n        existing_patterns = self.detected_patterns[user_id]\n        similar_pattern = None\n        \n        for existing in existing_patterns:\n            if (existing.pattern_type == pattern_type and \n                set(existing.pages_involved) == set(pages)):\n                similar_pattern = existing\n                break\n        \n        if similar_pattern:\n            # Update existing pattern\n            similar_pattern.frequency += 1\n            similar_pattern.confidence = min(1.0, similar_pattern.confidence + 0.1)\n            similar_pattern.last_detected = time.time()\n        else:\n            # Add new pattern\n            self.detected_patterns[user_id].append(pattern)\n            \n            # Generate optimization suggestion if confidence is high\n            if pattern.confidence >= 0.8:\n                self._generate_optimization_suggestion(user_id, pattern)\n        \n        # Save to database\n        self._save_pattern_to_db(pattern)\n    \n    def _generate_optimization_suggestion(self, user_id: str, pattern: NavigationPattern):\n        \"\"\"Generate UI optimization suggestion based on detected pattern\"\"\"\n        \n        optimization_id = f\"opt_{pattern.pattern_id}\"\n        \n        if pattern.pattern_type == 'struggle_finding':\n            optimization = UIOptimization(\n                optimization_id=optimization_id,\n                user_id=user_id,\n                optimization_type='add_search_help',\n                title=\"Add Search & Help Features\",\n                description=f\"You seem to have trouble finding options. Would you like us to add a search feature or contextual help?\",\n                implementation={\n                    'type': 'add_search_box',\n                    'pages': pattern.pages_involved,\n                    'search_scope': 'page_options',\n                    'help_tooltips': True\n                },\n                confidence=pattern.confidence,\n                expected_benefit=\"Reduce time spent searching by 60%\",\n                created_at=time.time()\n            )\n        \n        elif pattern.pattern_type == 'frequent_deep_access':\n            frequently_accessed_page = pattern.pages_involved[0] if pattern.pages_involved else '/settings'\n            \n            optimization = UIOptimization(\n                optimization_id=optimization_id,\n                user_id=user_id,\n                optimization_type='add_shortcut',\n                title=\"Create Quick Access Shortcut\",\n                description=f\"You frequently access {frequently_accessed_page}. Would you like a shortcut on your main interface?\",\n                implementation={\n                    'type': 'add_shortcut_button',\n                    'target_page': frequently_accessed_page,\n                    'placement': 'dashboard',\n                    'style': 'floating_button'\n                },\n                confidence=pattern.confidence,\n                expected_benefit=\"Save 3-4 clicks each time you access this feature\",\n                created_at=time.time()\n            )\n        \n        elif pattern.pattern_type == 'inefficient_path':\n            start_page = pattern.pages_involved[0] if pattern.pages_involved else '/dashboard'\n            end_page = pattern.pages_involved[-1] if len(pattern.pages_involved) > 1 else '/settings'\n            \n            optimization = UIOptimization(\n                optimization_id=optimization_id,\n                user_id=user_id,\n                optimization_type='add_direct_link',\n                title=\"Add Direct Navigation Link\",\n                description=f\"You often navigate from {start_page} to {end_page}. Would you like a direct link?\",\n                implementation={\n                    'type': 'add_navigation_link',\n                    'source_page': start_page,\n                    'target_page': end_page,\n                    'link_text': f\"Go to {end_page.split('/')[-1].title()}\",\n                    'placement': 'sidebar'\n                },\n                confidence=pattern.confidence,\n                expected_benefit=\"Reduce navigation steps by 50%\",\n                created_at=time.time()\n            )\n        else:\n            return  # Unknown pattern type\n        \n        self.generated_optimizations[user_id].append(optimization)\n        self._save_optimization_to_db(optimization)\n    \n    def _save_pattern_to_db(self, pattern: NavigationPattern):\n        \"\"\"Save pattern to database\"\"\"\n        try:\n            with sqlite3.connect(self.db_path) as conn:\n                conn.execute('''\n                    INSERT OR REPLACE INTO navigation_patterns \n                    (pattern_id, user_id, pattern_type, description, frequency, confidence, \n                     suggested_solution, pages_involved, last_detected)\n                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)\n                ''', (\n                    pattern.pattern_id, pattern.user_id, pattern.pattern_type, \n                    pattern.description, pattern.frequency, pattern.confidence,\n                    pattern.suggested_solution, json.dumps(pattern.pages_involved), \n                    pattern.last_detected\n                ))\n        except Exception as e:\n            logger.warning(f\"Failed to save pattern to DB: {e}\")\n    \n    def _save_optimization_to_db(self, optimization: UIOptimization):\n        \"\"\"Save optimization to database\"\"\"\n        try:\n            with sqlite3.connect(self.db_path) as conn:\n                conn.execute('''\n                    INSERT OR REPLACE INTO ui_optimizations \n                    (optimization_id, user_id, optimization_type, title, description, \n                     implementation, confidence, expected_benefit, created_at)\n                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)\n                ''', (\n                    optimization.optimization_id, optimization.user_id, optimization.optimization_type,\n                    optimization.title, optimization.description, json.dumps(optimization.implementation),\n                    optimization.confidence, optimization.expected_benefit, optimization.created_at\n                ))\n        except Exception as e:\n            logger.warning(f\"Failed to save optimization to DB: {e}\")\n    \n    def get_user_optimizations(self, user_id: str) -> List[UIOptimization]:\n        \"\"\"Get pending UI optimizations for user\"\"\"\n        try:\n            with sqlite3.connect(self.db_path) as conn:\n                cursor = conn.execute('''\n                    SELECT optimization_id, optimization_type, title, description, \n                           implementation, confidence, expected_benefit, created_at\n                    FROM ui_optimizations \n                    WHERE user_id = ? AND dismissed = FALSE AND implemented = FALSE\n                    ORDER BY confidence DESC, created_at DESC\n                    LIMIT 5\n                ''', (user_id,))\n                \n                optimizations = []\n                for row in cursor.fetchall():\n                    optimization = UIOptimization(\n                        optimization_id=row[0],\n                        user_id=user_id,\n                        optimization_type=row[1],\n                        title=row[2],\n                        description=row[3],\n                        implementation=json.loads(row[4]),\n                        confidence=row[5],\n                        expected_benefit=row[6],\n                        created_at=row[7]\n                    )\n                    optimizations.append(optimization)\n                \n                return optimizations\n                \n        except Exception as e:\n            logger.warning(f\"Failed to load optimizations: {e}\")\n            return []\n    \n    def dismiss_optimization(self, user_id: str, optimization_id: str):\n        \"\"\"Mark optimization as dismissed\"\"\"\n        try:\n            with sqlite3.connect(self.db_path) as conn:\n                conn.execute('''\n                    UPDATE ui_optimizations \n                    SET dismissed = TRUE \n                    WHERE user_id = ? AND optimization_id = ?\n                ''', (user_id, optimization_id))\n        except Exception as e:\n            logger.warning(f\"Failed to dismiss optimization: {e}\")\n    \n    def implement_optimization(self, user_id: str, optimization_id: str):\n        \"\"\"Mark optimization as implemented\"\"\"\n        try:\n            with sqlite3.connect(self.db_path) as conn:\n                conn.execute('''\n                    UPDATE ui_optimizations \n                    SET implemented = TRUE \n                    WHERE user_id = ? AND optimization_id = ?\n                ''', (user_id, optimization_id))\n        except Exception as e:\n            logger.warning(f\"Failed to mark optimization as implemented: {e}\")\n    \n    def get_navigation_insights(self, user_id: str) -> Dict[str, Any]:\n        \"\"\"Get navigation insights for user\"\"\"\n        patterns = self.detected_patterns.get(user_id, [])\n        optimizations = self.get_user_optimizations(user_id)\n        page_visits = self.monitor.page_visit_counts.get(user_id, {})\n        \n        return {\n            'total_patterns_detected': len(patterns),\n            'active_optimizations': len(optimizations),\n            'most_visited_pages': sorted(page_visits.items(), key=lambda x: x[1], reverse=True)[:5],\n            'navigation_efficiency_score': self._calculate_efficiency_score(user_id),\n            'recent_struggles': [p for p in patterns if p.last_detected > time.time() - 24*60*60],  # Last 24h\n            'ui_readiness': min(1.0, len(optimizations) / 10)  # More optimizations = more personalized UI\n        }\n    \n    def _calculate_efficiency_score(self, user_id: str) -> float:\n        \"\"\"Calculate navigation efficiency score (0-1, higher is better)\"\"\"\n        patterns = self.detected_patterns.get(user_id, [])\n        \n        if not patterns:\n            return 0.8  # Default good score\n        \n        struggle_patterns = len([p for p in patterns if p.pattern_type == 'struggle_finding'])\n        inefficient_patterns = len([p for p in patterns if p.pattern_type == 'inefficient_path'])\n        \n        efficiency = 1.0\n        efficiency -= (struggle_patterns * 0.2)  # Each struggle reduces score\n        efficiency -= (inefficient_patterns * 0.1)  # Each inefficient path reduces score\n        \n        return max(0.1, efficiency)\n\n# Global UI navigation assistant\nui_nav_assistant = UINavigationAssistant()\n\ndef track_navigation(user_id: str, page_path: str, action: str, \n                    element_id: str = '', element_text: str = '', \n                    session_id: str = '', time_spent: float = 0.0):\n    \"\"\"Track navigation event\"\"\"\n    return ui_nav_assistant.track_user_navigation(\n        user_id, page_path, action, element_id, element_text, session_id, time_spent\n    )\n\ndef get_ui_suggestions(user_id: str) -> List[UIOptimization]:\n    \"\"\"Get UI optimization suggestions for user\"\"\"\n    return ui_nav_assistant.get_user_optimizations(user_id)\n\ndef respond_to_ui_suggestion(user_id: str, optimization_id: str, response: str):\n    \"\"\"Respond to UI suggestion (accept/dismiss)\"\"\"\n    if response == 'accept':\n        ui_nav_assistant.implement_optimization(user_id, optimization_id)\n    elif response == 'dismiss':\n        ui_nav_assistant.dismiss_optimization(user_id, optimization_id)\n\ndef get_navigation_insights(user_id: str) -> Dict[str, Any]:\n    \"\"\"Get navigation insights for user\"\"\"\n    return ui_nav_assistant.get_navigation_insights(user_id)