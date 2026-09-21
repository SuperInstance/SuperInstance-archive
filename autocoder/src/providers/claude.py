"""
Anthropic Claude provider
"""

import os
from typing import List, Optional, AsyncIterator, Union
try:
    import anthropic
except ImportError:
    anthropic = None

from .base import ModelProvider, Message, Response


class ClaudeProvider(ModelProvider):
    """Anthropic Claude model provider"""

    # Pricing per 1M tokens (USD)
    PRICING = {
        "claude-sonnet-4-5-20250929": {"input": 3.00, "output": 15.00},
        "claude-3-7-sonnet-20250219": {"input": 3.00, "output": 15.00},
        "claude-3-5-haiku-20250219": {"input": 0.80, "output": 4.00},
    }

    def __init__(
        self,
        model_name: str = "claude-sonnet-4-5-20250929",
        api_key: Optional[str] = None
    ):
        super().__init__(model_name)

        if anthropic is None:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        self.client = anthropic.AsyncAnthropic(api_key=self.api_key)

    async def chat(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        tools: Optional[List] = None
    ) -> Union[Response, AsyncIterator[str]]:
        """Send chat request to Claude"""

        kwargs = {
            "model": self.model_name,
            "messages": [
                {"role": m.role, "content": m.content}
                for m in messages
                if m.role != "system"  # Claude handles system differently
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Add system message if present
        system_messages = [m for m in messages if m.role == "system"]
        if system_messages:
            kwargs["system"] = system_messages[0].content

        # Add tools if provided
        if tools:
            kwargs["tools"] = tools

        if stream:
            return self._stream_response(kwargs)
        else:
            response = await self.client.messages.create(**kwargs)

            return Response(
                content=response.content[0].text,
                model=self.model_name,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                finish_reason=response.stop_reason
            )

    async def _stream_response(self, kwargs) -> AsyncIterator[str]:
        """Stream chunks from Claude"""
        async with self.client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on token usage"""
        pricing = self.PRICING.get(self.model_name, {"input": 3.0, "output": 15.0})

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    def get_context_window(self) -> int:
        """Claude models have 200K context"""
        return 200_000

    def supports_tools(self) -> bool:
        """All Claude models support function calling"""
        return True
