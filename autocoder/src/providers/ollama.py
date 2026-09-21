"""
Ollama provider for local models (Qwen, etc.)
"""

import aiohttp
import json
from typing import List, Optional, AsyncIterator, Union
from .base import ModelProvider, Message, Response


class OllamaProvider(ModelProvider):
    """Ollama local model provider"""

    def __init__(
        self,
        model_name: str = "qwen2.5-coder:7b-instruct-q4_K_M",
        base_url: str = "http://localhost:11434"
    ):
        super().__init__(model_name)
        self.base_url = base_url

    async def chat(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        tools: Optional[List] = None
    ) -> Union[Response, AsyncIterator[str]]:
        """Send chat request to Ollama"""

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": m.role, "content": m.content}
                for m in messages
            ],
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/chat",
                json=payload
            ) as resp:

                if stream:
                    return self._stream_response(resp)
                else:
                    result = await resp.json()
                    return Response(
                        content=result["message"]["content"],
                        model=self.model_name,
                        input_tokens=0,  # Ollama doesn't provide token counts
                        output_tokens=0,
                        finish_reason=result.get("done_reason")
                    )

    async def _stream_response(self, response) -> AsyncIterator[str]:
        """Stream chunks from Ollama"""
        async for line in response.content:
            if line:
                data = json.loads(line)
                if "message" in data:
                    chunk = data["message"].get("content", "")
                    if chunk:
                        yield chunk

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Local models are free"""
        return 0.0

    def get_context_window(self) -> int:
        """Return context window (32K for Qwen 2.5)"""
        return 32768

    def supports_tools(self) -> bool:
        """Qwen 2.5 supports function calling"""
        return "qwen" in self.model_name.lower()
