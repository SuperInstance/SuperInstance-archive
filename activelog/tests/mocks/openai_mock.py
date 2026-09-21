"""
Mock OpenAI service for testing
Provides realistic responses for embedding and chat completion requests
"""

import json
import asyncio
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock
import numpy as np


class MockOpenAIClient:
    """Mock OpenAI client that simulates API responses"""
    
    def __init__(self):
        self.embeddings = MockEmbeddings()
        self.chat = MockChat()
        self.call_log = []
    
    def log_call(self, method: str, **kwargs):
        """Log API calls for testing verification"""
        self.call_log.append({
            "method": method,
            "timestamp": asyncio.get_event_loop().time(),
            **kwargs
        })


class MockEmbeddings:
    """Mock embeddings API"""
    
    def __init__(self):
        self.client = None
    
    async def create(self, input: List[str], model: str = "text-embedding-ada-002", **kwargs):
        """Mock embedding creation"""
        if self.client:
            self.client.log_call("embeddings.create", input=input, model=model)
        
        # Simulate API delay
        await asyncio.sleep(0.1)
        
        # Generate deterministic embeddings based on input
        embeddings = []
        for text in input:
            # Create a simple hash-based embedding
            embedding = self._generate_embedding(text)
            embeddings.append({
                "object": "embedding",
                "embedding": embedding,
                "index": len(embeddings)
            })
        
        return {
            "object": "list",
            "data": embeddings,
            "model": model,
            "usage": {
                "prompt_tokens": sum(len(text.split()) for text in input),
                "total_tokens": sum(len(text.split()) for text in input)
            }
        }
    
    def _generate_embedding(self, text: str, dimensions: int = 1536) -> List[float]:
        """Generate deterministic embedding vector based on text"""
        # Use hash of text to create reproducible embeddings
        text_hash = hash(text)
        np.random.seed(abs(text_hash) % (2**32))
        
        # Generate normalized vector
        vector = np.random.normal(0, 1, dimensions)
        vector = vector / np.linalg.norm(vector)
        
        return vector.tolist()


class MockChat:
    """Mock chat completions API"""
    
    def __init__(self):
        self.client = None
        self.responses = {
            "summarize": "This document discusses key concepts and implementation details.",
            "analyze": "The content shows strong technical implementation with good structure.",
            "extract_tags": "technology, implementation, documentation, analysis",
            "default": "I understand your request and here's my response based on the content."
        }
    
    async def create(self, messages: List[Dict[str, str]], model: str = "gpt-3.5-turbo", **kwargs):
        """Mock chat completion"""
        if self.client:
            self.client.log_call("chat.create", messages=messages, model=model)
        
        # Simulate API delay
        await asyncio.sleep(0.2)
        
        # Analyze the request to provide appropriate response
        last_message = messages[-1] if messages else {}
        content = last_message.get("content", "").lower()
        
        response_text = self._generate_response(content)
        
        return {
            "id": f"chatcmpl-mock-{hash(str(messages)) % 10000}",
            "object": "chat.completion",
            "created": int(asyncio.get_event_loop().time()),
            "model": model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": sum(len(msg.get("content", "").split()) for msg in messages),
                "completion_tokens": len(response_text.split()),
                "total_tokens": sum(len(msg.get("content", "").split()) for msg in messages) + len(response_text.split())
            }
        }
    
    def _generate_response(self, content: str) -> str:
        """Generate appropriate response based on request content"""
        if "summarize" in content or "summary" in content:
            return self.responses["summarize"]
        elif "analyze" in content or "analysis" in content:
            return self.responses["analyze"]
        elif "tag" in content or "extract" in content:
            return self.responses["extract_tags"]
        else:
            return self.responses["default"]


class MockOpenAIError(Exception):
    """Mock OpenAI API errors"""
    
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class MockRateLimitError(MockOpenAIError):
    """Mock rate limit error"""
    
    def __init__(self):
        super().__init__("Rate limit exceeded", 429)


class MockAPIError(MockOpenAIError):
    """Mock general API error"""
    
    def __init__(self, message: str = "API error occurred"):
        super().__init__(message, 500)


def create_mock_openai_client() -> MockOpenAIClient:
    """Factory function to create mock OpenAI client"""
    client = MockOpenAIClient()
    client.embeddings.client = client
    client.chat.client = client
    return client


# Pytest fixtures
def mock_openai_successful():
    """Mock successful OpenAI responses"""
    return create_mock_openai_client()


def mock_openai_rate_limited():
    """Mock rate-limited OpenAI client"""
    async def rate_limited_create(*args, **kwargs):
        raise MockRateLimitError()
    
    client = create_mock_openai_client()
    client.embeddings.create = rate_limited_create
    client.chat.create = rate_limited_create
    return client


def mock_openai_error():
    """Mock error-prone OpenAI client"""
    async def error_create(*args, **kwargs):
        raise MockAPIError("Service temporarily unavailable")
    
    client = create_mock_openai_client()
    client.embeddings.create = error_create
    client.chat.create = error_create
    return client


# Response templates for different scenarios
MOCK_RESPONSES = {
    "file_analysis": {
        "summary": "This file contains implementation details for a web application with user authentication and file management capabilities.",
        "tags": ["web-app", "authentication", "file-management", "python", "fastapi"],
        "insights": "The code follows modern Python patterns with async/await and includes comprehensive error handling."
    },
    "document_processing": {
        "summary": "Technical documentation outlining system architecture and implementation guidelines.",
        "tags": ["documentation", "architecture", "guidelines", "technical"],
        "insights": "Well-structured documentation with clear explanations and examples."
    },
    "code_review": {
        "summary": "Source code implementing core business logic with database interactions and API endpoints.",
        "tags": ["source-code", "api", "database", "business-logic"],
        "insights": "Code demonstrates good separation of concerns and follows established patterns."
    }
}


def get_mock_response(content_type: str = "file_analysis") -> Dict[str, str]:
    """Get predefined mock response for testing"""
    return MOCK_RESPONSES.get(content_type, MOCK_RESPONSES["file_analysis"])