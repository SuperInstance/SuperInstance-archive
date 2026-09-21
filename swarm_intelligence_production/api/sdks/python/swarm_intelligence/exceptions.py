"""
SDK Exceptions
"""


class SwarmError(Exception):
    """Base exception for swarm operations"""
    pass


class SwarmCreationError(SwarmError):
    """Error creating swarm"""
    pass


class TaskSubmissionError(SwarmError):
    """Error submitting task"""
    pass


class AuthenticationError(SwarmError):
    """Authentication failed"""
    pass


class RateLimitError(SwarmError):
    """Rate limit exceeded"""
    pass


class SwarmNotFoundError(SwarmError):
    """Swarm not found"""
    pass


class TaskNotFoundError(SwarmError):
    """Task not found"""
    pass
