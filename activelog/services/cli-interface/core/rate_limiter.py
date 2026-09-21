#!/usr/bin/env python3
"""
Rate Limiter - Implements rate limiting and throttling for CLI operations
Provides token bucket, sliding window, and fixed window rate limiting algorithms
"""

import time
import json
import threading
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum
import sqlite3
import logging
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class LimitType(Enum):
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    CONCURRENT = "concurrent"


@dataclass
class RateLimit:
    """Rate limit configuration"""
    name: str
    limit_type: LimitType
    max_requests: int
    time_window_seconds: int
    burst_allowance: Optional[int] = None  # For token bucket
    cost_per_request: int = 1
    enabled: bool = True
    description: str = ""
    
    def __post_init__(self):
        if isinstance(self.limit_type, str):
            self.limit_type = LimitType(self.limit_type)


@dataclass
class ClientLimitState:
    """State tracking for a specific client and limit"""
    client_id: str
    limit_name: str
    requests_made: int = 0
    tokens_available: float = 0
    last_refill: float = 0
    window_start: float = 0
    request_timestamps: List[float] = None
    concurrent_requests: int = 0
    
    def __post_init__(self):
        if self.request_timestamps is None:
            self.request_timestamps = []


@dataclass
class RateLimitResult:
    """Result of rate limit check"""
    allowed: bool
    limit_name: str
    requests_remaining: int = 0
    retry_after_seconds: Optional[float] = None
    current_usage: int = 0
    limit_info: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.limit_info is None:
            self.limit_info = {}


class RateLimiter:
    """Advanced rate limiting system with multiple algorithms"""
    
    def __init__(self, config):
        self.config = config
        self.limits = {}  # limit_name -> RateLimit
        self.client_states = {}  # (client_id, limit_name) -> ClientLimitState
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Database for persistent state
        self.db_path = Path("/home/activeloguser/activelog/data/cli-interface/rate_limits.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        # Load existing limits and states
        self._load_limits()
        self._load_client_states()
        
        # Background cleanup thread
        self.running = True
        self.cleanup_thread = threading.Thread(target=self._cleanup_old_states, daemon=True)
        self.cleanup_thread.start()
        
        # Initialize default limits
        self._initialize_default_limits()
        
        logger.info("Rate Limiter initialized")

    def check_limit(self, client_id: str, operation: str, cost: int = 1) -> bool:
        """Check if client can perform operation within rate limits"""
        try:
            with self.lock:
                # Get applicable limits for operation
                applicable_limits = self._get_applicable_limits(operation)
                
                if not applicable_limits:
                    return True  # No limits apply
                
                # Check each applicable limit
                for limit_name in applicable_limits:
                    result = self._check_single_limit(client_id, limit_name, cost)
                    if not result.allowed:
                        return False
                
                # All limits passed - consume from each
                for limit_name in applicable_limits:
                    self._consume_from_limit(client_id, limit_name, cost)
                
                return True
                
        except Exception as e:
            logger.error(f"Rate limit check failed for {client_id}/{operation}: {e}")
            return True  # Fail open

    def check_limit_detailed(self, client_id: str, operation: str, cost: int = 1) -> List[RateLimitResult]:
        """Check rate limits with detailed results for each applicable limit"""
        try:
            with self.lock:
                results = []
                applicable_limits = self._get_applicable_limits(operation)
                
                if not applicable_limits:
                    return [RateLimitResult(allowed=True, limit_name="none", requests_remaining=-1)]
                
                all_allowed = True
                
                # Check each limit
                for limit_name in applicable_limits:
                    result = self._check_single_limit(client_id, limit_name, cost)
                    results.append(result)
                    
                    if not result.allowed:
                        all_allowed = False
                
                # If all limits allow, consume from each
                if all_allowed:
                    for limit_name in applicable_limits:
                        self._consume_from_limit(client_id, limit_name, cost)
                
                return results
                
        except Exception as e:
            logger.error(f"Detailed rate limit check failed for {client_id}/{operation}: {e}")
            return [RateLimitResult(allowed=True, limit_name="error", limit_info={"error": str(e)})]

    def get_client_status(self, client_id: str) -> Dict[str, Any]:
        """Get current rate limit status for client"""
        try:
            with self.lock:
                status = {
                    'client_id': client_id,
                    'limits': {},
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                for limit_name, limit_config in self.limits.items():
                    if not limit_config.enabled:
                        continue
                    
                    state_key = (client_id, limit_name)
                    state = self.client_states.get(state_key)
                    
                    limit_status = self._get_limit_status(limit_config, state)
                    status['limits'][limit_name] = limit_status
                
                return status
                
        except Exception as e:
            logger.error(f"Failed to get client status for {client_id}: {e}")
            return {'error': str(e)}

    def register_limit(self, limit: RateLimit):
        """Register new rate limit"""
        try:
            with self.lock:
                self.limits[limit.name] = limit
                self._save_limit(limit)
                logger.info(f"Registered rate limit: {limit.name}")
                
        except Exception as e:
            logger.error(f"Failed to register limit {limit.name}: {e}")

    def update_limit(self, limit_name: str, updates: Dict[str, Any]) -> bool:
        """Update existing rate limit"""
        try:
            with self.lock:
                limit = self.limits.get(limit_name)
                if not limit:
                    return False
                
                # Update fields
                for key, value in updates.items():
                    if hasattr(limit, key):
                        setattr(limit, key, value)
                
                self._save_limit(limit)
                logger.info(f"Updated rate limit: {limit_name}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update limit {limit_name}: {e}")
            return False

    def remove_limit(self, limit_name: str) -> bool:
        """Remove rate limit"""
        try:
            with self.lock:
                if limit_name not in self.limits:
                    return False
                
                # Remove from memory
                del self.limits[limit_name]
                
                # Remove client states for this limit
                states_to_remove = [
                    key for key in self.client_states.keys()
                    if key[1] == limit_name
                ]
                
                for key in states_to_remove:
                    del self.client_states[key]
                
                # Remove from database
                self._delete_limit(limit_name)
                
                logger.info(f"Removed rate limit: {limit_name}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to remove limit {limit_name}: {e}")
            return False

    def reset_client_limits(self, client_id: str, limit_name: Optional[str] = None):
        """Reset rate limits for client"""
        try:
            with self.lock:
                if limit_name:
                    # Reset specific limit
                    state_key = (client_id, limit_name)
                    if state_key in self.client_states:
                        del self.client_states[state_key]
                else:
                    # Reset all limits for client
                    states_to_remove = [
                        key for key in self.client_states.keys()
                        if key[0] == client_id
                    ]
                    
                    for key in states_to_remove:
                        del self.client_states[key]
                
                logger.info(f"Reset limits for client {client_id}, limit: {limit_name or 'all'}")
                
        except Exception as e:
            logger.error(f"Failed to reset limits for {client_id}: {e}")

    def get_rate_limit_stats(self) -> Dict[str, Any]:
        """Get rate limiting statistics"""
        try:
            with self.lock:
                total_limits = len(self.limits)
                active_limits = sum(1 for limit in self.limits.values() if limit.enabled)
                total_clients = len(set(key[0] for key in self.client_states.keys()))
                
                # Limit type distribution
                limit_types = {}
                for limit in self.limits.values():
                    lt = limit.limit_type.value
                    limit_types[lt] = limit_types.get(lt, 0) + 1
                
                # Client activity (clients with recent requests)
                recent_threshold = time.time() - 3600  # Last hour
                active_clients = set()
                
                for state in self.client_states.values():
                    if state.request_timestamps:
                        recent_requests = [ts for ts in state.request_timestamps if ts > recent_threshold]
                        if recent_requests:
                            active_clients.add(state.client_id)
                
                return {
                    'total_limits': total_limits,
                    'active_limits': active_limits,
                    'total_clients_tracked': total_clients,
                    'active_clients_last_hour': len(active_clients),
                    'limit_type_distribution': limit_types,
                    'total_client_states': len(self.client_states)
                }
                
        except Exception as e:
            logger.error(f"Failed to get rate limit stats: {e}")
            return {'error': str(e)}

    def _get_applicable_limits(self, operation: str) -> List[str]:
        """Get list of rate limits that apply to the operation"""
        applicable = []
        
        # Operation-specific mapping
        operation_mappings = {
            'command_execution': ['command_rate', 'global_rate'],
            'api_request': ['api_rate', 'global_rate'],
            'file_upload': ['upload_rate', 'global_rate'],
            'search': ['search_rate', 'global_rate'],
            'export': ['export_rate', 'global_rate'],
            'webhook': ['webhook_rate', 'global_rate']
        }
        
        # Get mapped limits
        mapped_limits = operation_mappings.get(operation, ['global_rate'])
        
        # Filter to only enabled limits that exist
        for limit_name in mapped_limits:
            if limit_name in self.limits and self.limits[limit_name].enabled:
                applicable.append(limit_name)
        
        return applicable

    def _check_single_limit(self, client_id: str, limit_name: str, cost: int) -> RateLimitResult:
        """Check a single rate limit for client"""
        try:
            limit_config = self.limits.get(limit_name)
            if not limit_config or not limit_config.enabled:
                return RateLimitResult(allowed=True, limit_name=limit_name)
            
            state_key = (client_id, limit_name)
            state = self.client_states.get(state_key)
            
            if not state:
                state = ClientLimitState(client_id=client_id, limit_name=limit_name)
                self.client_states[state_key] = state
            
            current_time = time.time()
            
            if limit_config.limit_type == LimitType.TOKEN_BUCKET:
                return self._check_token_bucket(limit_config, state, cost, current_time)
            elif limit_config.limit_type == LimitType.SLIDING_WINDOW:
                return self._check_sliding_window(limit_config, state, cost, current_time)
            elif limit_config.limit_type == LimitType.FIXED_WINDOW:
                return self._check_fixed_window(limit_config, state, cost, current_time)
            elif limit_config.limit_type == LimitType.CONCURRENT:
                return self._check_concurrent(limit_config, state, cost, current_time)
            else:
                return RateLimitResult(allowed=False, limit_name=limit_name, 
                                     limit_info={'error': f'Unknown limit type: {limit_config.limit_type}'})
                
        except Exception as e:
            logger.error(f"Failed to check limit {limit_name} for {client_id}: {e}")
            return RateLimitResult(allowed=True, limit_name=limit_name, 
                                 limit_info={'error': str(e)})

    def _check_token_bucket(self, limit_config: RateLimit, state: ClientLimitState, 
                           cost: int, current_time: float) -> RateLimitResult:
        """Check token bucket rate limit"""
        # Initialize or refill bucket
        if state.last_refill == 0:
            state.tokens_available = limit_config.max_requests
            state.last_refill = current_time
        else:
            # Calculate tokens to add based on time passed
            time_passed = current_time - state.last_refill
            tokens_to_add = time_passed * (limit_config.max_requests / limit_config.time_window_seconds)
            
            max_tokens = limit_config.burst_allowance or limit_config.max_requests
            state.tokens_available = min(max_tokens, state.tokens_available + tokens_to_add)
            state.last_refill = current_time
        
        # Check if enough tokens available
        if state.tokens_available >= cost:
            return RateLimitResult(
                allowed=True,
                limit_name=limit_config.name,
                requests_remaining=int(state.tokens_available) - cost,
                current_usage=limit_config.max_requests - int(state.tokens_available),
                limit_info={
                    'tokens_available': state.tokens_available,
                    'bucket_size': limit_config.max_requests,
                    'refill_rate': limit_config.max_requests / limit_config.time_window_seconds
                }
            )
        else:
            # Calculate retry after
            tokens_needed = cost - state.tokens_available
            refill_rate = limit_config.max_requests / limit_config.time_window_seconds
            retry_after = tokens_needed / refill_rate
            
            return RateLimitResult(
                allowed=False,
                limit_name=limit_config.name,
                requests_remaining=0,
                retry_after_seconds=retry_after,
                current_usage=limit_config.max_requests,
                limit_info={
                    'tokens_available': state.tokens_available,
                    'tokens_needed': tokens_needed,
                    'refill_rate': refill_rate
                }
            )

    def _check_sliding_window(self, limit_config: RateLimit, state: ClientLimitState,
                            cost: int, current_time: float) -> RateLimitResult:
        """Check sliding window rate limit"""
        window_start = current_time - limit_config.time_window_seconds
        
        # Remove old timestamps
        state.request_timestamps = [ts for ts in state.request_timestamps if ts > window_start]
        
        # Calculate current usage
        current_requests = sum(1 for _ in state.request_timestamps)  # Could be weighted by cost
        
        if current_requests + cost <= limit_config.max_requests:
            return RateLimitResult(
                allowed=True,
                limit_name=limit_config.name,
                requests_remaining=limit_config.max_requests - current_requests - cost,
                current_usage=current_requests,
                limit_info={
                    'window_requests': current_requests,
                    'window_start': datetime.fromtimestamp(window_start).isoformat(),
                    'window_end': datetime.fromtimestamp(current_time).isoformat()
                }
            )
        else:
            # Calculate retry after (when oldest request exits window)
            if state.request_timestamps:
                oldest_request = min(state.request_timestamps)
                retry_after = (oldest_request + limit_config.time_window_seconds) - current_time
            else:
                retry_after = limit_config.time_window_seconds
            
            return RateLimitResult(
                allowed=False,
                limit_name=limit_config.name,
                requests_remaining=0,
                retry_after_seconds=max(0, retry_after),
                current_usage=current_requests,
                limit_info={
                    'window_requests': current_requests,
                    'limit': limit_config.max_requests
                }
            )

    def _check_fixed_window(self, limit_config: RateLimit, state: ClientLimitState,
                          cost: int, current_time: float) -> RateLimitResult:
        """Check fixed window rate limit"""
        window_start = (current_time // limit_config.time_window_seconds) * limit_config.time_window_seconds
        
        # Reset if new window
        if state.window_start != window_start:
            state.window_start = window_start
            state.requests_made = 0
        
        if state.requests_made + cost <= limit_config.max_requests:
            return RateLimitResult(
                allowed=True,
                limit_name=limit_config.name,
                requests_remaining=limit_config.max_requests - state.requests_made - cost,
                current_usage=state.requests_made,
                limit_info={
                    'window_requests': state.requests_made,
                    'window_start': datetime.fromtimestamp(window_start).isoformat(),
                    'window_end': datetime.fromtimestamp(window_start + limit_config.time_window_seconds).isoformat()
                }
            )
        else:
            # Retry after current window ends
            retry_after = (window_start + limit_config.time_window_seconds) - current_time
            
            return RateLimitResult(
                allowed=False,
                limit_name=limit_config.name,
                requests_remaining=0,
                retry_after_seconds=retry_after,
                current_usage=state.requests_made,
                limit_info={
                    'window_requests': state.requests_made,
                    'limit': limit_config.max_requests
                }
            )

    def _check_concurrent(self, limit_config: RateLimit, state: ClientLimitState,
                        cost: int, current_time: float) -> RateLimitResult:
        """Check concurrent requests limit"""
        if state.concurrent_requests + cost <= limit_config.max_requests:
            return RateLimitResult(
                allowed=True,
                limit_name=limit_config.name,
                requests_remaining=limit_config.max_requests - state.concurrent_requests - cost,
                current_usage=state.concurrent_requests,
                limit_info={
                    'concurrent_requests': state.concurrent_requests,
                    'max_concurrent': limit_config.max_requests
                }
            )
        else:
            return RateLimitResult(
                allowed=False,
                limit_name=limit_config.name,
                requests_remaining=0,
                current_usage=state.concurrent_requests,
                limit_info={
                    'concurrent_requests': state.concurrent_requests,
                    'max_concurrent': limit_config.max_requests
                }
            )

    def _consume_from_limit(self, client_id: str, limit_name: str, cost: int):
        """Consume tokens/requests from rate limit"""
        try:
            limit_config = self.limits.get(limit_name)
            if not limit_config:
                return
            
            state_key = (client_id, limit_name)
            state = self.client_states.get(state_key)
            if not state:
                return
            
            current_time = time.time()
            
            if limit_config.limit_type == LimitType.TOKEN_BUCKET:
                state.tokens_available -= cost
            elif limit_config.limit_type == LimitType.SLIDING_WINDOW:
                # Add timestamp(s) for the request
                for _ in range(cost):
                    state.request_timestamps.append(current_time)
            elif limit_config.limit_type == LimitType.FIXED_WINDOW:
                state.requests_made += cost
            elif limit_config.limit_type == LimitType.CONCURRENT:
                state.concurrent_requests += cost
            
            # Save state
            self._save_client_state(state)
            
        except Exception as e:
            logger.error(f"Failed to consume from limit {limit_name} for {client_id}: {e}")

    def release_concurrent_request(self, client_id: str, limit_name: str, cost: int = 1):
        """Release concurrent request slots"""
        try:
            with self.lock:
                state_key = (client_id, limit_name)
                state = self.client_states.get(state_key)
                
                if state:
                    state.concurrent_requests = max(0, state.concurrent_requests - cost)
                    self._save_client_state(state)
                    
        except Exception as e:
            logger.error(f"Failed to release concurrent request for {client_id}/{limit_name}: {e}")

    def _get_limit_status(self, limit_config: RateLimit, state: Optional[ClientLimitState]) -> Dict[str, Any]:
        """Get status information for a specific limit"""
        if not state:
            return {
                'limit_type': limit_config.limit_type.value,
                'max_requests': limit_config.max_requests,
                'time_window_seconds': limit_config.time_window_seconds,
                'requests_remaining': limit_config.max_requests,
                'current_usage': 0,
                'enabled': limit_config.enabled
            }
        
        current_time = time.time()
        
        if limit_config.limit_type == LimitType.TOKEN_BUCKET:
            # Calculate current tokens
            if state.last_refill > 0:
                time_passed = current_time - state.last_refill
                tokens_to_add = time_passed * (limit_config.max_requests / limit_config.time_window_seconds)
                max_tokens = limit_config.burst_allowance or limit_config.max_requests
                current_tokens = min(max_tokens, state.tokens_available + tokens_to_add)
            else:
                current_tokens = limit_config.max_requests
            
            return {
                'limit_type': limit_config.limit_type.value,
                'max_requests': limit_config.max_requests,
                'time_window_seconds': limit_config.time_window_seconds,
                'tokens_available': current_tokens,
                'requests_remaining': int(current_tokens),
                'burst_allowance': limit_config.burst_allowance,
                'enabled': limit_config.enabled
            }
        
        elif limit_config.limit_type == LimitType.SLIDING_WINDOW:
            window_start = current_time - limit_config.time_window_seconds
            recent_requests = [ts for ts in state.request_timestamps if ts > window_start]
            current_usage = len(recent_requests)
            
            return {
                'limit_type': limit_config.limit_type.value,
                'max_requests': limit_config.max_requests,
                'time_window_seconds': limit_config.time_window_seconds,
                'current_usage': current_usage,
                'requests_remaining': max(0, limit_config.max_requests - current_usage),
                'enabled': limit_config.enabled
            }
        
        elif limit_config.limit_type == LimitType.FIXED_WINDOW:
            window_start = (current_time // limit_config.time_window_seconds) * limit_config.time_window_seconds
            
            # Check if we're in a new window
            if state.window_start != window_start:
                current_usage = 0
            else:
                current_usage = state.requests_made
            
            return {
                'limit_type': limit_config.limit_type.value,
                'max_requests': limit_config.max_requests,
                'time_window_seconds': limit_config.time_window_seconds,
                'current_usage': current_usage,
                'requests_remaining': max(0, limit_config.max_requests - current_usage),
                'window_start': datetime.fromtimestamp(window_start).isoformat(),
                'enabled': limit_config.enabled
            }
        
        elif limit_config.limit_type == LimitType.CONCURRENT:
            return {
                'limit_type': limit_config.limit_type.value,
                'max_concurrent': limit_config.max_requests,
                'current_concurrent': state.concurrent_requests,
                'concurrent_remaining': max(0, limit_config.max_requests - state.concurrent_requests),
                'enabled': limit_config.enabled
            }
        
        return {'enabled': limit_config.enabled}

    def _initialize_default_limits(self):
        """Initialize default rate limits"""
        default_limits = [
            RateLimit(
                name="global_rate",
                limit_type=LimitType.SLIDING_WINDOW,
                max_requests=1000,
                time_window_seconds=3600,  # 1 hour
                description="Global rate limit for all operations"
            ),
            RateLimit(
                name="command_rate",
                limit_type=LimitType.TOKEN_BUCKET,
                max_requests=60,
                time_window_seconds=60,  # 1 minute
                burst_allowance=100,
                description="Rate limit for CLI command execution"
            ),
            RateLimit(
                name="api_rate",
                limit_type=LimitType.SLIDING_WINDOW,
                max_requests=300,
                time_window_seconds=300,  # 5 minutes
                description="Rate limit for API requests"
            ),
            RateLimit(
                name="upload_rate",
                limit_type=LimitType.FIXED_WINDOW,
                max_requests=20,
                time_window_seconds=3600,  # 1 hour
                cost_per_request=5,
                description="Rate limit for file uploads"
            ),
            RateLimit(
                name="search_rate",
                limit_type=LimitType.TOKEN_BUCKET,
                max_requests=30,
                time_window_seconds=60,  # 1 minute
                description="Rate limit for search operations"
            ),
            RateLimit(
                name="webhook_rate",
                limit_type=LimitType.SLIDING_WINDOW,
                max_requests=100,
                time_window_seconds=3600,  # 1 hour
                description="Rate limit for webhook operations"
            ),
            RateLimit(
                name="concurrent_operations",
                limit_type=LimitType.CONCURRENT,
                max_requests=10,
                time_window_seconds=0,  # Not applicable for concurrent
                description="Limit on concurrent operations per client"
            )
        ]
        
        for limit in default_limits:
            if limit.name not in self.limits:
                self.register_limit(limit)

    def _cleanup_old_states(self):
        """Background thread to cleanup old client states"""
        while self.running:
            try:
                current_time = time.time()
                cleanup_threshold = current_time - 86400  # 24 hours
                
                with self.lock:
                    states_to_remove = []
                    
                    for key, state in self.client_states.items():
                        # Remove states that haven't been used recently
                        last_activity = 0
                        
                        if state.request_timestamps:
                            last_activity = max(state.request_timestamps)
                        elif state.last_refill > 0:
                            last_activity = state.last_refill
                        
                        if last_activity > 0 and last_activity < cleanup_threshold:
                            states_to_remove.append(key)
                    
                    # Remove old states
                    for key in states_to_remove:
                        del self.client_states[key]
                    
                    if states_to_remove:
                        logger.info(f"Cleaned up {len(states_to_remove)} old client states")
                
                # Sleep for 1 hour before next cleanup
                time.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error in cleanup thread: {e}")
                time.sleep(3600)

    def _init_database(self):
        """Initialize SQLite database for persistent storage"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Create limits table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rate_limits (
                    name TEXT PRIMARY KEY,
                    limit_data TEXT NOT NULL,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            
            # Create client states table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS client_states (
                    client_id TEXT,
                    limit_name TEXT,
                    state_data TEXT NOT NULL,
                    updated_at TEXT,
                    PRIMARY KEY (client_id, limit_name)
                )
            """)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to initialize rate limit database: {e}")
            raise

    def _load_limits(self):
        """Load rate limits from database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("SELECT limit_data FROM rate_limits")
            rows = cursor.fetchall()
            
            for row in rows:
                try:
                    limit_data = json.loads(row[0])
                    limit = RateLimit(**limit_data)
                    self.limits[limit.name] = limit
                except Exception as e:
                    logger.warning(f"Failed to load rate limit: {e}")
            
            conn.close()
            logger.info(f"Loaded {len(self.limits)} rate limits from database")
            
        except Exception as e:
            logger.error(f"Failed to load rate limits: {e}")

    def _load_client_states(self):
        """Load client states from database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Only load recent states (last 24 hours)
            cutoff_time = (datetime.utcnow() - timedelta(hours=24)).isoformat()
            
            cursor.execute("""
                SELECT client_id, limit_name, state_data 
                FROM client_states 
                WHERE updated_at >= ?
            """, (cutoff_time,))
            
            rows = cursor.fetchall()
            
            for row in rows:
                try:
                    client_id, limit_name, state_data = row
                    state_dict = json.loads(state_data)
                    state = ClientLimitState(**state_dict)
                    
                    state_key = (client_id, limit_name)
                    self.client_states[state_key] = state
                except Exception as e:
                    logger.warning(f"Failed to load client state: {e}")
            
            conn.close()
            logger.info(f"Loaded {len(self.client_states)} client states from database")
            
        except Exception as e:
            logger.error(f"Failed to load client states: {e}")

    def _save_limit(self, limit: RateLimit):
        """Save rate limit to database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            limit_data = asdict(limit)
            
            cursor.execute("""
                INSERT OR REPLACE INTO rate_limits 
                (name, limit_data, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (
                limit.name,
                json.dumps(limit_data),
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save rate limit {limit.name}: {e}")

    def _save_client_state(self, state: ClientLimitState):
        """Save client state to database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            state_data = asdict(state)
            
            cursor.execute("""
                INSERT OR REPLACE INTO client_states 
                (client_id, limit_name, state_data, updated_at)
                VALUES (?, ?, ?, ?)
            """, (
                state.client_id,
                state.limit_name,
                json.dumps(state_data),
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save client state {state.client_id}/{state.limit_name}: {e}")

    def _delete_limit(self, limit_name: str):
        """Delete rate limit from database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM rate_limits WHERE name = ?", (limit_name,))
            cursor.execute("DELETE FROM client_states WHERE limit_name = ?", (limit_name,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to delete rate limit {limit_name}: {e}")

    def shutdown(self):
        """Shutdown rate limiter"""
        self.running = False
        
        # Save all current states
        with self.lock:
            for state in self.client_states.values():
                self._save_client_state(state)
        
        # Wait for cleanup thread
        if self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5)
        
        logger.info("Rate Limiter shut down")