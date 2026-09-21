"""
Base model provider interface
All model providers (Claude, Ollama, OpenAI, etc.) inherit from this
"""

from abc import ABC, abstractmethod
from typing import List, Optional, AsyncIterator, Union, Dict, Any
from dataclasses import dataclass


@dataclass
class Message:
    """Chat message"""
    role: str  # 'user', 'assistant', 'system'
    content: str


@dataclass
class Response:
    """Model response"""
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    finish_reason: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None


class ModelProvider(ABC):
    """Abstract base class for all model providers"""

    def __init__(self, model_name: str):
        self.model_name = model_name

    @abstractmethod
    async def chat(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        tools: Optional[List[Dict]] = None
    ) -> Union[Response, AsyncIterator[str]]:
        """
        Send chat request to model

        Args:
            messages: List of conversation messages
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream response
            tools: Optional tool definitions for function calling

        Returns:
            Response object or async iterator of chunks (if streaming)
        """
        pass

    @abstractmethod
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost in USD for given token counts

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        pass

    @abstractmethod
    def get_context_window(self) -> int:
        """Return maximum context window size in tokens"""
        pass

    @abstractmethod
    def supports_tools(self) -> bool:
        """Return True if model supports function calling"""
        pass

    def get_model_name(self) -> str:
        """Return model name"""
        return self.model_name
