"""
Enhanced Token Management for Claude Max 20x Account

Provides intelligent token tracking, 5-hour limit management, and cost optimization
specifically designed for ActiveLog's development workflow.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import aiosqlite
import threading
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class ModelTier(Enum):
    CLAUDE_OPUS_4 = "claude-opus-4-1"
    CLAUDE_SONNET_3_5 = "claude-3-5-sonnet-20241022"
    CLAUDE_HAIKU_3_5 = "claude-3-5-haiku-20241022"
    LOCAL_OLLAMA = "ollama"
    FREE_GPT = "gpt-free"

@dataclass
class TokenUsage:
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_cc: float
    timestamp: datetime
    task_id: str
    bot_id: str
    session_id: str

@dataclass
class SessionLimits:
    max_duration_hours: int = 5
    max_total_tokens: int = 2_000_000  # Conservative for 5-hour session
    max_cost_cc: float = 1000.0  # Max CC spend per session
    warning_threshold: float = 0.8  # Warn at 80% usage
    emergency_threshold: float = 0.95  # Emergency throttle at 95%

class ClaudeMaxTokenManager:
    """
    Advanced token management for Claude Max 20x account with 5-hour limit tracking
    """
    
    def __init__(self, session_limits: SessionLimits = None):
        self.session_limits = session_limits or SessionLimits()
        self.session_start = datetime.now(timezone.utc)
        self.session_id = f"session_{int(time.time())}"
        
        # Token tracking
        self.session_usage = defaultdict(int)
        self.session_cost = 0.0
        self.usage_history = deque(maxlen=10000)
        self.model_costs = {
            ModelTier.CLAUDE_OPUS_4.value: {"input": 15.0, "output": 75.0},  # per 1M tokens in CC
            ModelTier.CLAUDE_SONNET_3_5.value: {"input": 3.0, "output": 15.0},
            ModelTier.CLAUDE_HAIKU_3_5.value: {"input": 1.0, "output": 5.0},
            ModelTier.LOCAL_OLLAMA.value: {"input": 0.0, "output": 0.0},
            ModelTier.FREE_GPT.value: {"input": 0.0, "output": 0.0}
        }
        
        # Rate limiting
        self.current_requests_per_minute = defaultdict(int)
        self.rate_limits = {
            ModelTier.CLAUDE_OPUS_4.value: 50,  # requests per minute
            ModelTier.CLAUDE_SONNET_3_5.value: 100,
            ModelTier.CLAUDE_HAIKU_3_5.value: 200,
            ModelTier.LOCAL_OLLAMA.value: 999999,
            ModelTier.FREE_GPT.value: 60
        }
        
        # Throttling state
        self.throttling_active = False
        self.emergency_mode = False
        self.throttle_factor = 1.0
        
        # Database path
        self.db_path = "/home/activeloguser/activelog/services/bot-orchestrator/token_usage.db"
        self.lock = threading.RLock()
        
        # Start background monitoring
        asyncio.create_task(self._start_monitoring())
    
    async def _start_monitoring(self):
        """Start background monitoring and database initialization"""
        await self._init_database()
        asyncio.create_task(self._monitor_limits())
        asyncio.create_task(self._rate_limit_reset())
    
    async def _init_database(self):
        """Initialize token usage database"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS token_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    bot_id TEXT NOT NULL,
                    model TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    cost_cc REAL NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS session_stats (
                    session_id TEXT PRIMARY KEY,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    total_tokens INTEGER DEFAULT 0,
                    total_cost_cc REAL DEFAULT 0.0,
                    tasks_completed INTEGER DEFAULT 0,
                    throttling_events INTEGER DEFAULT 0,
                    emergency_stops INTEGER DEFAULT 0
                )
            """)
            
            await db.commit()
    
    async def track_usage(self, model: str, input_tokens: int, output_tokens: int,
                         task_id: str, bot_id: str) -> TokenUsage:
        """Track token usage for a specific request"""
        with self.lock:
            total_tokens = input_tokens + output_tokens
            cost_cc = self._calculate_cost(model, input_tokens, output_tokens)
            
            usage = TokenUsage(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cost_cc=cost_cc,
                timestamp=datetime.now(timezone.utc),
                task_id=task_id,
                bot_id=bot_id,
                session_id=self.session_id
            )
            
            # Update session tracking
            self.session_usage['total_tokens'] += total_tokens
            self.session_usage['input_tokens'] += input_tokens
            self.session_usage['output_tokens'] += output_tokens
            self.session_cost += cost_cc
            self.usage_history.append(usage)
            
            # Update rate limiting
            current_minute = int(time.time() // 60)
            self.current_requests_per_minute[f"{model}:{current_minute}"] += 1
            
            # Store in database
            await self._store_usage(usage)
            
            # Check limits
            await self._check_limits()
            
            logger.info(f"Token usage tracked: {total_tokens} tokens, {cost_cc:.3f} CC for {task_id}")
            return usage
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in CC tokens"""
        if model not in self.model_costs:
            model = ModelTier.CLAUDE_SONNET_3_5.value  # Default fallback
        
        costs = self.model_costs[model]
        input_cost = (input_tokens / 1_000_000) * costs["input"]
        output_cost = (output_tokens / 1_000_000) * costs["output"]
        return input_cost + output_cost
    
    async def _store_usage(self, usage: TokenUsage):
        """Store usage data in database"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO token_usage 
                (session_id, task_id, bot_id, model, input_tokens, output_tokens, 
                 total_tokens, cost_cc, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                usage.session_id, usage.task_id, usage.bot_id, usage.model,
                usage.input_tokens, usage.output_tokens, usage.total_tokens,
                usage.cost_cc, usage.timestamp.isoformat()
            ))
            await db.commit()
    
    async def _check_limits(self):
        """Check if we're approaching session limits"""
        session_duration = (datetime.now(timezone.utc) - self.session_start).total_seconds() / 3600
        
        # Check time limit
        time_usage = session_duration / self.session_limits.max_duration_hours
        
        # Check token limit
        token_usage = self.session_usage['total_tokens'] / self.session_limits.max_total_tokens
        
        # Check cost limit
        cost_usage = self.session_cost / self.session_limits.max_cost_cc
        
        max_usage = max(time_usage, token_usage, cost_usage)
        
        if max_usage >= self.session_limits.emergency_threshold:
            await self._activate_emergency_mode()
        elif max_usage >= self.session_limits.warning_threshold:
            await self._activate_throttling(max_usage)
        
        # Log status every 10% usage
        usage_percent = int(max_usage * 100)
        if usage_percent % 10 == 0 and usage_percent > 0:
            logger.warning(f"Session usage: {usage_percent}% (Time: {time_usage:.1%}, "
                         f"Tokens: {token_usage:.1%}, Cost: {cost_usage:.1%})")
    
    async def _activate_throttling(self, usage_ratio: float):
        """Activate intelligent throttling"""
        if not self.throttling_active:
            self.throttling_active = True
            # Increase delay between requests based on usage
            self.throttle_factor = 1.0 + (usage_ratio - self.session_limits.warning_threshold) * 10
            logger.warning(f"Throttling activated: {self.throttle_factor:.1f}x delay")
    
    async def _activate_emergency_mode(self):
        """Activate emergency mode to prevent limit breach"""
        if not self.emergency_mode:
            self.emergency_mode = True
            self.throttle_factor = 5.0  # Severe throttling
            logger.critical("EMERGENCY MODE ACTIVATED - Severe throttling in effect")
            
            # Switch to cheapest models only
            await self._emergency_model_switch()
    
    async def _emergency_model_switch(self):
        """Switch to emergency model preferences"""
        logger.critical("Switching to emergency model preferences (Local/Free only)")
        # This would notify the bot allocation system to prefer free models
    
    def can_make_request(self, model: str, estimated_tokens: int = 1000) -> Tuple[bool, str]:
        """Check if we can make a request given current limits"""
        with self.lock:
            # Check rate limits
            current_minute = int(time.time() // 60)
            current_requests = self.current_requests_per_minute.get(f"{model}:{current_minute}", 0)
            rate_limit = self.rate_limits.get(model, 50)
            
            if current_requests >= rate_limit:
                return False, f"Rate limit exceeded for {model} ({current_requests}/{rate_limit})"
            
            # Check session limits
            estimated_cost = self._calculate_cost(model, estimated_tokens // 2, estimated_tokens // 2)
            
            if (self.session_usage['total_tokens'] + estimated_tokens) > self.session_limits.max_total_tokens:
                return False, "Session token limit would be exceeded"
            
            if (self.session_cost + estimated_cost) > self.session_limits.max_cost_cc:
                return False, "Session cost limit would be exceeded"
            
            session_duration = (datetime.now(timezone.utc) - self.session_start).total_seconds() / 3600
            if session_duration > self.session_limits.max_duration_hours:
                return False, "Session time limit exceeded"
            
            if self.emergency_mode and model == ModelTier.CLAUDE_OPUS_4.value:
                return False, "Emergency mode: Claude Opus disabled"
            
            return True, "Request approved"
    
    async def get_throttle_delay(self, model: str) -> float:
        """Get the current throttling delay for a model"""
        base_delay = 0.1  # Base delay in seconds
        if self.throttling_active:
            return base_delay * self.throttle_factor
        return base_delay
    
    async def _monitor_limits(self):
        """Background task to monitor limits"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self._check_limits()
                await self._log_session_stats()
            except Exception as e:
                logger.error(f"Error in limit monitoring: {e}")
    
    async def _rate_limit_reset(self):
        """Reset rate limit counters every minute"""
        while True:
            await asyncio.sleep(60)
            current_minute = int(time.time() // 60)
            # Clean up old rate limit entries
            keys_to_remove = []
            for key in self.current_requests_per_minute:
                if int(key.split(':')[1]) < current_minute - 1:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.current_requests_per_minute[key]
    
    async def _log_session_stats(self):
        """Log current session statistics"""
        session_duration = (datetime.now(timezone.utc) - self.session_start).total_seconds() / 3600
        
        stats = {
            "session_duration_hours": round(session_duration, 2),
            "total_tokens": self.session_usage['total_tokens'],
            "total_cost_cc": round(self.session_cost, 3),
            "throttling_active": self.throttling_active,
            "emergency_mode": self.emergency_mode,
            "requests_this_session": len(self.usage_history)
        }
        
        logger.info(f"Session stats: {stats}")
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get comprehensive session summary"""
        with self.lock:
            session_duration = (datetime.now(timezone.utc) - self.session_start).total_seconds() / 3600
            
            # Calculate model usage breakdown
            model_usage = defaultdict(lambda: {"tokens": 0, "cost": 0.0, "requests": 0})
            for usage in self.usage_history:
                model_usage[usage.model]["tokens"] += usage.total_tokens
                model_usage[usage.model]["cost"] += usage.cost_cc
                model_usage[usage.model]["requests"] += 1
            
            return {
                "session_id": self.session_id,
                "start_time": self.session_start.isoformat(),
                "duration_hours": round(session_duration, 2),
                "total_tokens": self.session_usage['total_tokens'],
                "total_cost_cc": round(self.session_cost, 3),
                "total_requests": len(self.usage_history),
                "model_breakdown": dict(model_usage),
                "throttling_active": self.throttling_active,
                "emergency_mode": self.emergency_mode,
                "limits": {
                    "time_usage_percent": round((session_duration / self.session_limits.max_duration_hours) * 100, 1),
                    "token_usage_percent": round((self.session_usage['total_tokens'] / self.session_limits.max_total_tokens) * 100, 1),
                    "cost_usage_percent": round((self.session_cost / self.session_limits.max_cost_cc) * 100, 1)
                }
            }
    
    async def force_session_end(self):
        """Force end current session and save statistics"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO session_stats 
                (session_id, start_time, end_time, total_tokens, total_cost_cc, 
                 tasks_completed, throttling_events, emergency_stops)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.session_id,
                self.session_start.isoformat(),
                datetime.now(timezone.utc).isoformat(),
                self.session_usage['total_tokens'],
                self.session_cost,
                len(set(usage.task_id for usage in self.usage_history)),
                1 if self.throttling_active else 0,
                1 if self.emergency_mode else 0
            ))
            await db.commit()
        
        logger.info(f"Session {self.session_id} ended. Final stats: {self.get_session_summary()}")

# Global instance for the Director Bot
director_token_manager = ClaudeMaxTokenManager()