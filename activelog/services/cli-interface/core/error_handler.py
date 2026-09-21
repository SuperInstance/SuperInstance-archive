#!/usr/bin/env python3
"""
Error Handler - Provides centralized error handling and recovery for CLI operations
Handles error reporting, logging, retry logic, and user-friendly error messages
"""

import json
import uuid
import time
import traceback
import logging
from typing import Dict, List, Any, Optional, Callable, Type, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum
import sqlite3
import functools

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NETWORK = "network"
    FILE_SYSTEM = "file_system"
    DATABASE = "database"
    EXTERNAL_SERVICE = "external_service"
    SYSTEM = "system"
    USER_INPUT = "user_input"
    CONFIGURATION = "configuration"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"


@dataclass
class ErrorContext:
    """Error context information"""
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    command: Optional[str] = None
    service: Optional[str] = None
    additional_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.additional_data is None:
            self.additional_data = {}


@dataclass
class ErrorRecord:
    """Error record for tracking and analysis"""
    id: str
    error_code: str
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    timestamp: str
    context: ErrorContext
    stack_trace: Optional[str] = None
    resolution_steps: List[str] = None
    related_errors: List[str] = None
    resolved: bool = False
    resolution_notes: Optional[str] = None
    
    def __post_init__(self):
        if self.resolution_steps is None:
            self.resolution_steps = []
        if self.related_errors is None:
            self.related_errors = []


@dataclass
class RetryConfig:
    """Retry configuration for failed operations"""
    max_attempts: int = 3
    delay_seconds: float = 1.0
    backoff_factor: float = 2.0
    max_delay_seconds: float = 60.0
    retry_on: List[Type[Exception]] = None
    
    def __post_init__(self):
        if self.retry_on is None:
            self.retry_on = [Exception]


class CLIError(Exception):
    """Base CLI error with enhanced context"""
    
    def __init__(self, message: str, error_code: str = None, 
                 category: ErrorCategory = ErrorCategory.SYSTEM,
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 context: ErrorContext = None,
                 resolution_steps: List[str] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.category = category
        self.severity = severity
        self.context = context or ErrorContext()
        self.resolution_steps = resolution_steps or []


class ValidationError(CLIError):
    """Validation error"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.VALIDATION, **kwargs)


class AuthenticationError(CLIError):
    """Authentication error"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.AUTHENTICATION, 
                        severity=ErrorSeverity.HIGH, **kwargs)


class NetworkError(CLIError):
    """Network-related error"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.NETWORK, **kwargs)


class FileSystemError(CLIError):
    """File system error"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.FILE_SYSTEM, **kwargs)


class RateLimitError(CLIError):
    """Rate limit exceeded error"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.RATE_LIMIT, 
                        severity=ErrorSeverity.HIGH, **kwargs)


class ErrorHandler:
    """Centralized error handling and recovery system"""
    
    def __init__(self, config):
        self.config = config
        self.error_records = {}  # error_id -> ErrorRecord
        
        # Database for persistent error storage
        self.db_path = Path("/home/activeloguser/activelog/data/cli-interface/errors.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        # Error pattern tracking
        self.error_patterns = {}  # pattern -> count
        self.pattern_threshold = 10  # Alert after this many similar errors
        
        # Recovery strategies
        self.recovery_strategies = {}
        self._initialize_recovery_strategies()
        
        # Load existing errors
        self._load_recent_errors()
        
        logger.info("Error Handler initialized")

    def handle_error(self, error: Exception, context: ErrorContext = None) -> ErrorRecord:
        """Handle and record error with context"""
        try:
            # Create error record
            error_record = self._create_error_record(error, context)
            
            # Store error
            self.error_records[error_record.id] = error_record
            self._save_error_record(error_record)
            
            # Log error
            self._log_error(error_record)
            
            # Check for error patterns
            self._analyze_error_pattern(error_record)
            
            # Attempt automatic recovery if available
            self._attempt_recovery(error_record)
            
            return error_record
            
        except Exception as e:
            # Fallback error handling
            logger.critical(f"Error handler itself failed: {e}")
            return self._create_fallback_error_record(error)

    def retry_with_backoff(self, func: Callable, retry_config: RetryConfig = None, 
                          context: ErrorContext = None) -> Any:
        """Execute function with retry logic and exponential backoff"""
        retry_config = retry_config or RetryConfig()
        attempt = 1
        delay = retry_config.delay_seconds
        last_error = None
        
        while attempt <= retry_config.max_attempts:
            try:
                return func()
                
            except Exception as e:
                last_error = e
                
                # Check if error type should trigger retry
                if not any(isinstance(e, exc_type) for exc_type in retry_config.retry_on):
                    break
                
                if attempt == retry_config.max_attempts:
                    break
                
                # Log retry attempt
                logger.warning(f"Attempt {attempt} failed, retrying in {delay}s: {str(e)}")
                
                # Wait before retry
                time.sleep(delay)
                
                # Calculate next delay with backoff
                delay = min(
                    delay * retry_config.backoff_factor,
                    retry_config.max_delay_seconds
                )
                attempt += 1
        
        # All attempts failed - handle the final error
        final_context = context or ErrorContext()
        final_context.additional_data.update({
            'retry_attempts': attempt - 1,
            'max_attempts': retry_config.max_attempts
        })
        
        error_record = self.handle_error(last_error, final_context)
        raise CLIError(
            f"Operation failed after {attempt - 1} attempts: {str(last_error)}",
            error_code="RETRY_EXHAUSTED",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.HIGH,
            context=final_context
        )

    def with_error_handling(self, context: ErrorContext = None):
        """Decorator for automatic error handling"""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_record = self.handle_error(e, context)
                    
                    # Convert to user-friendly CLI error if needed
                    if not isinstance(e, CLIError):
                        raise CLIError(
                            self._get_user_friendly_message(error_record),
                            error_code=error_record.error_code,
                            category=error_record.category,
                            severity=error_record.severity,
                            context=error_record.context,
                            resolution_steps=error_record.resolution_steps
                        )
                    raise
            
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    error_record = self.handle_error(e, context)
                    
                    if not isinstance(e, CLIError):
                        raise CLIError(
                            self._get_user_friendly_message(error_record),
                            error_code=error_record.error_code,
                            category=error_record.category,
                            severity=error_record.severity,
                            context=error_record.context,
                            resolution_steps=error_record.resolution_steps
                        )
                    raise
            
            # Return appropriate wrapper based on function type
            if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
                return async_wrapper
            else:
                return wrapper
            
        return decorator

    def get_error_record(self, error_id: str) -> Optional[ErrorRecord]:
        """Get error record by ID"""
        return self.error_records.get(error_id)

    def list_errors(self, category: Optional[ErrorCategory] = None,
                   severity: Optional[ErrorSeverity] = None,
                   since: Optional[str] = None,
                   limit: int = 100) -> List[ErrorRecord]:
        """List error records with optional filtering"""
        try:
            errors = []
            
            for error_record in self.error_records.values():
                # Apply filters
                if category and error_record.category != category:
                    continue
                if severity and error_record.severity != severity:
                    continue
                if since:
                    error_time = datetime.fromisoformat(error_record.timestamp)
                    since_time = datetime.fromisoformat(since)
                    if error_time < since_time:
                        continue
                
                errors.append(error_record)
            
            # Sort by timestamp (newest first)
            errors.sort(key=lambda x: x.timestamp, reverse=True)
            
            return errors[:limit]
            
        except Exception as e:
            logger.error(f"Failed to list errors: {e}")
            return []

    def get_error_stats(self, time_window: str = '24h') -> Dict[str, Any]:
        """Get error statistics for specified time window"""
        try:
            # Parse time window
            hours = {'1h': 1, '24h': 24, '7d': 168, '30d': 720}.get(time_window, 24)
            since = datetime.utcnow() - timedelta(hours=hours)
            
            # Count errors by category and severity
            category_counts = {}
            severity_counts = {}
            total_errors = 0
            resolved_errors = 0
            
            for error_record in self.error_records.values():
                error_time = datetime.fromisoformat(error_record.timestamp)
                if error_time < since:
                    continue
                
                total_errors += 1
                
                # Count by category
                category = error_record.category.value
                category_counts[category] = category_counts.get(category, 0) + 1
                
                # Count by severity
                severity = error_record.severity.value
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
                
                # Count resolved
                if error_record.resolved:
                    resolved_errors += 1
            
            # Get most common error patterns
            common_patterns = sorted(
                [(pattern, count) for pattern, count in self.error_patterns.items() if count > 1],
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            return {
                'time_window': time_window,
                'total_errors': total_errors,
                'resolved_errors': resolved_errors,
                'resolution_rate': resolved_errors / max(total_errors, 1),
                'category_distribution': category_counts,
                'severity_distribution': severity_counts,
                'common_patterns': common_patterns,
                'error_rate_per_hour': total_errors / hours
            }
            
        except Exception as e:
            logger.error(f"Failed to get error stats: {e}")
            return {}

    def resolve_error(self, error_id: str, resolution_notes: str = None) -> bool:
        """Mark error as resolved"""
        try:
            error_record = self.error_records.get(error_id)
            if not error_record:
                return False
            
            error_record.resolved = True
            error_record.resolution_notes = resolution_notes
            
            self._save_error_record(error_record)
            
            logger.info(f"Resolved error {error_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resolve error {error_id}: {e}")
            return False

    def _create_error_record(self, error: Exception, context: ErrorContext = None) -> ErrorRecord:
        """Create error record from exception"""
        error_id = str(uuid.uuid4())
        
        # Determine error details
        if isinstance(error, CLIError):
            error_code = error.error_code
            category = error.category
            severity = error.severity
            resolution_steps = error.resolution_steps
            context = error.context if context is None else context
        else:
            error_code = error.__class__.__name__
            category = self._categorize_error(error)
            severity = self._assess_severity(error)
            resolution_steps = self._get_resolution_steps(error)
            context = context or ErrorContext()
        
        return ErrorRecord(
            id=error_id,
            error_code=error_code,
            message=str(error),
            category=category,
            severity=severity,
            timestamp=datetime.utcnow().isoformat(),
            context=context,
            stack_trace=traceback.format_exc(),
            resolution_steps=resolution_steps
        )

    def _create_fallback_error_record(self, error: Exception) -> ErrorRecord:
        """Create minimal error record for fallback scenarios"""
        return ErrorRecord(
            id=str(uuid.uuid4()),
            error_code="UNKNOWN_ERROR",
            message=str(error),
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.CRITICAL,
            timestamp=datetime.utcnow().isoformat(),
            context=ErrorContext(),
            stack_trace=traceback.format_exc()
        )

    def _categorize_error(self, error: Exception) -> ErrorCategory:
        """Categorize error based on type and message"""
        error_type = type(error).__name__
        error_message = str(error).lower()
        
        # Authentication/Authorization errors
        if any(keyword in error_message for keyword in ['unauthorized', 'forbidden', 'authentication', 'login']):
            return ErrorCategory.AUTHENTICATION
        
        # Network errors
        if any(keyword in error_message for keyword in ['connection', 'network', 'timeout', 'dns']):
            return ErrorCategory.NETWORK
        
        # File system errors
        if any(keyword in error_message for keyword in ['file not found', 'permission denied', 'disk space']):
            return ErrorCategory.FILE_SYSTEM
        
        # Database errors
        if any(keyword in error_message for keyword in ['database', 'sql', 'connection pool']):
            return ErrorCategory.DATABASE
        
        # Validation errors
        if any(keyword in error_message for keyword in ['invalid', 'validation', 'required field']):
            return ErrorCategory.VALIDATION
        
        # Rate limit errors
        if any(keyword in error_message for keyword in ['rate limit', 'too many requests', 'quota exceeded']):
            return ErrorCategory.RATE_LIMIT
        
        return ErrorCategory.SYSTEM

    def _assess_severity(self, error: Exception) -> ErrorSeverity:
        """Assess error severity"""
        error_message = str(error).lower()
        
        # Critical errors
        if any(keyword in error_message for keyword in ['critical', 'fatal', 'system failure']):
            return ErrorSeverity.CRITICAL
        
        # High severity
        if any(keyword in error_message for keyword in ['security', 'unauthorized', 'data loss']):
            return ErrorSeverity.HIGH
        
        # Low severity
        if any(keyword in error_message for keyword in ['warning', 'deprecated', 'minor']):
            return ErrorSeverity.LOW
        
        return ErrorSeverity.MEDIUM

    def _get_resolution_steps(self, error: Exception) -> List[str]:
        """Get resolution steps based on error type"""
        error_message = str(error).lower()
        steps = []
        
        if 'authentication' in error_message:
            steps.extend([
                "Check your authentication credentials",
                "Try logging in again with 'activelog auth login'",
                "Verify your API key is valid and not expired"
            ])
        elif 'network' in error_message or 'connection' in error_message:
            steps.extend([
                "Check your internet connection",
                "Verify the service URL is correct",
                "Try again after a few moments"
            ])
        elif 'file not found' in error_message:
            steps.extend([
                "Check if the file path is correct",
                "Verify the file exists and is accessible",
                "Check file permissions"
            ])
        elif 'rate limit' in error_message:
            steps.extend([
                "Wait before making additional requests",
                "Consider reducing request frequency",
                "Check your API usage limits"
            ])
        else:
            steps.extend([
                "Check the command syntax and arguments",
                "Review the logs for more details",
                "Try the operation again"
            ])
        
        return steps

    def _log_error(self, error_record: ErrorRecord):
        """Log error record appropriately"""
        log_message = f"Error {error_record.id}: {error_record.message}"
        
        if error_record.context.command:
            log_message += f" (Command: {error_record.context.command})"
        
        if error_record.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message)
        elif error_record.severity == ErrorSeverity.HIGH:
            logger.error(log_message)
        elif error_record.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)

    def _analyze_error_pattern(self, error_record: ErrorRecord):
        """Analyze error patterns for alerts"""
        try:
            # Create pattern key from error code and category
            pattern_key = f"{error_record.error_code}:{error_record.category.value}"
            
            self.error_patterns[pattern_key] = self.error_patterns.get(pattern_key, 0) + 1
            
            # Check if pattern exceeds threshold
            if self.error_patterns[pattern_key] >= self.pattern_threshold:
                logger.warning(
                    f"Error pattern alert: {pattern_key} occurred {self.error_patterns[pattern_key]} times"
                )
                
                # Reset counter to avoid spam
                self.error_patterns[pattern_key] = 0
                
        except Exception as e:
            logger.error(f"Failed to analyze error pattern: {e}")

    def _attempt_recovery(self, error_record: ErrorRecord):
        """Attempt automatic recovery for known error types"""
        try:
            recovery_strategy = self.recovery_strategies.get(error_record.error_code)
            
            if recovery_strategy:
                logger.info(f"Attempting recovery for error {error_record.id}")
                success = recovery_strategy(error_record)
                
                if success:
                    error_record.resolved = True
                    error_record.resolution_notes = "Automatic recovery successful"
                    logger.info(f"Successfully recovered from error {error_record.id}")
                else:
                    logger.warning(f"Recovery attempt failed for error {error_record.id}")
                    
        except Exception as e:
            logger.error(f"Recovery attempt failed for error {error_record.id}: {e}")

    def _initialize_recovery_strategies(self):
        """Initialize automatic recovery strategies"""
        self.recovery_strategies = {
            'ConnectionError': self._recover_connection_error,
            'AuthenticationError': self._recover_authentication_error,
            'RateLimitError': self._recover_rate_limit_error,
        }

    def _recover_connection_error(self, error_record: ErrorRecord) -> bool:
        """Attempt to recover from connection errors"""
        try:
            # Simple retry with delay
            time.sleep(5)
            # In a real implementation, this would retry the original operation
            return True
        except:
            return False

    def _recover_authentication_error(self, error_record: ErrorRecord) -> bool:
        """Attempt to recover from authentication errors"""
        try:
            # In a real implementation, this would attempt token refresh
            return False
        except:
            return False

    def _recover_rate_limit_error(self, error_record: ErrorRecord) -> bool:
        """Attempt to recover from rate limit errors"""
        try:
            # Wait and retry
            time.sleep(60)  # Wait 1 minute
            return True
        except:
            return False

    def _get_user_friendly_message(self, error_record: ErrorRecord) -> str:
        """Convert technical error to user-friendly message"""
        friendly_messages = {
            ErrorCategory.AUTHENTICATION: "Authentication failed. Please check your credentials and try logging in again.",
            ErrorCategory.NETWORK: "Network connection failed. Please check your internet connection and try again.",
            ErrorCategory.FILE_SYSTEM: "File operation failed. Please check the file path and permissions.",
            ErrorCategory.VALIDATION: "Invalid input provided. Please check your command arguments.",
            ErrorCategory.RATE_LIMIT: "Too many requests. Please wait a moment before trying again.",
        }
        
        friendly_msg = friendly_messages.get(error_record.category, error_record.message)
        
        if error_record.resolution_steps:
            friendly_msg += f"\n\nSuggested actions:\n" + "\n".join(f"- {step}" for step in error_record.resolution_steps)
        
        return friendly_msg

    def _init_database(self):
        """Initialize SQLite database for error storage"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS error_records (
                    id TEXT PRIMARY KEY,
                    error_data TEXT NOT NULL,
                    timestamp TEXT,
                    category TEXT,
                    severity TEXT,
                    resolved INTEGER DEFAULT 0
                )
            """)
            
            # Create indexes for efficient queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON error_records(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON error_records(category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_severity ON error_records(severity)")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to initialize error database: {e}")
            raise

    def _load_recent_errors(self):
        """Load recent errors from database"""
        try:
            # Load errors from last 7 days
            since = (datetime.utcnow() - timedelta(days=7)).isoformat()
            
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT error_data FROM error_records 
                WHERE timestamp >= ? 
                ORDER BY timestamp DESC 
                LIMIT 1000
            """, (since,))
            
            rows = cursor.fetchall()
            
            for row in rows:
                try:
                    error_data = json.loads(row[0])
                    
                    # Reconstruct ErrorRecord
                    context_data = error_data.get('context', {})
                    context = ErrorContext(**context_data)
                    
                    error_record = ErrorRecord(
                        id=error_data['id'],
                        error_code=error_data['error_code'],
                        message=error_data['message'],
                        category=ErrorCategory(error_data['category']),
                        severity=ErrorSeverity(error_data['severity']),
                        timestamp=error_data['timestamp'],
                        context=context,
                        stack_trace=error_data.get('stack_trace'),
                        resolution_steps=error_data.get('resolution_steps', []),
                        related_errors=error_data.get('related_errors', []),
                        resolved=error_data.get('resolved', False),
                        resolution_notes=error_data.get('resolution_notes')
                    )
                    
                    self.error_records[error_record.id] = error_record
                    
                except Exception as e:
                    logger.warning(f"Failed to load error record: {e}")
            
            conn.close()
            logger.info(f"Loaded {len(self.error_records)} recent error records")
            
        except Exception as e:
            logger.error(f"Failed to load recent errors: {e}")

    def _save_error_record(self, error_record: ErrorRecord):
        """Save error record to database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Convert to serializable format
            error_data = asdict(error_record)
            
            cursor.execute("""
                INSERT OR REPLACE INTO error_records 
                (id, error_data, timestamp, category, severity, resolved)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                error_record.id,
                json.dumps(error_data),
                error_record.timestamp,
                error_record.category.value,
                error_record.severity.value,
                int(error_record.resolved)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save error record {error_record.id}: {e}")

    def cleanup_old_errors(self, days: int = 30):
        """Cleanup old error records"""
        try:
            cutoff_time = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            # Remove from memory
            errors_to_remove = [
                error_id for error_id, error_record in self.error_records.items()
                if error_record.timestamp < cutoff_time
            ]
            
            for error_id in errors_to_remove:
                del self.error_records[error_id]
            
            # Remove from database
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM error_records WHERE timestamp < ?", (cutoff_time,))
            deleted_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            logger.info(f"Cleaned up {deleted_count} old error records")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old errors: {e}")