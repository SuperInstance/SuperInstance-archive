# src/api/api_client.py
"""
Unified API client for all AI providers
Bots use this to make API calls through the resource manager
"""

import os
from typing import Dict, Any, Optional, List
import json


class APIClient:
    """
    Unified client for AI API calls
    Routes to appropriate provider based on model name
    """

    def __init__(self, resource_manager=None):
        self.resource_manager = resource_manager

        # Initialize clients
        self._anthropic_client = None
        self._openai_client = None
        self._groq_client = None

        # Model -> Provider mapping
        self.model_to_provider = {
            # Anthropic
            "claude-opus-4-20250514": "anthropic",
            "claude-sonnet-4-20250514": "anthropic",
            "claude-haiku-4-20250514": "anthropic",

            # OpenAI
            "gpt-4o": "openai",
            "gpt-4o-mini": "openai",
            "gpt-4": "openai",
            "gpt-3.5-turbo": "openai",

            # Groq (free!)
            "llama-3.1-8b-instant": "groq",
            "llama-3.1-70b-versatile": "groq",
            "mixtral-8x7b-32768": "groq",

            # Legacy/compatibility
            "llama3.2:3b": "ollama",
            "llama3.2:1b": "ollama",
        }

    def _get_anthropic_client(self):
        """Lazy load Anthropic client"""
        if self._anthropic_client is None:
            try:
                import anthropic
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if api_key:
                    self._anthropic_client = anthropic.Anthropic(api_key=api_key)
            except ImportError:
                print("⚠️ anthropic package not installed")
        return self._anthropic_client

    def _get_openai_client(self):
        """Lazy load OpenAI client"""
        if self._openai_client is None:
            try:
                import openai
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    self._openai_client = openai.OpenAI(api_key=api_key)
            except ImportError:
                print("⚠️ openai package not installed")
        return self._openai_client

    def _get_groq_client(self):
        """Lazy load Groq client"""
        if self._groq_client is None:
            try:
                import groq
                api_key = os.getenv("GROQ_API_KEY")
                if api_key:
                    self._groq_client = groq.Groq(api_key=api_key)
            except ImportError:
                print("⚠️ groq package not installed")
        return self._groq_client

    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> str:
        """
        Universal chat completion
        Routes to appropriate provider based on model

        Args:
            model: Model identifier
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Max tokens to generate

        Returns:
            Generated text response
        """
        provider = self.model_to_provider.get(model, "unknown")

        if provider == "anthropic":
            return await self._call_anthropic(model, messages, temperature, max_tokens, **kwargs)
        elif provider == "openai":
            return await self._call_openai(model, messages, temperature, max_tokens, **kwargs)
        elif provider == "groq":
            return await self._call_groq(model, messages, temperature, max_tokens, **kwargs)
        elif provider == "ollama":
            return await self._call_ollama(model, messages, temperature, max_tokens, **kwargs)
        else:
            raise ValueError(f"Unknown model or provider: {model}")

    async def _call_anthropic(
        self,
        model: str,
        messages: List[Dict],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> str:
        """Call Anthropic Claude API"""
        client = self._get_anthropic_client()
        if not client:
            raise Exception("Anthropic client not available")

        # Anthropic has different message format
        # Extract system message if present
        system_msg = None
        anthropic_messages = []

        for msg in messages:
            if msg['role'] == 'system':
                system_msg = msg['content']
            else:
                anthropic_messages.append({
                    'role': msg['role'],
                    'content': msg['content']
                })

        # Make API call with resource manager rate limiting if available
        async def api_call():
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_msg if system_msg else None,
                messages=anthropic_messages
            )
            return response.content[0].text

        if self.resource_manager:
            # Estimate tokens for cost tracking
            input_tokens = sum(len(m['content'].split()) * 1.3 for m in messages)
            output_tokens = max_tokens

            return await self.resource_manager.call_api(
                "anthropic",
                api_call,
                input_tokens=int(input_tokens),
                output_tokens=output_tokens
            )
        else:
            return await api_call()

    async def _call_openai(
        self,
        model: str,
        messages: List[Dict],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> str:
        """Call OpenAI API"""
        client = self._get_openai_client()
        if not client:
            raise Exception("OpenAI client not available")

        async def api_call():
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content

        if self.resource_manager:
            input_tokens = sum(len(m['content'].split()) * 1.3 for m in messages)
            output_tokens = max_tokens

            return await self.resource_manager.call_api(
                "openai",
                api_call,
                input_tokens=int(input_tokens),
                output_tokens=output_tokens
            )
        else:
            return await api_call()

    async def _call_groq(
        self,
        model: str,
        messages: List[Dict],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> str:
        """Call Groq API (FREE!)"""
        client = self._get_groq_client()
        if not client:
            raise Exception("Groq client not available")

        async def api_call():
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content

        if self.resource_manager:
            # Groq is free, but still rate limit
            return await self.resource_manager.call_api(
                "groq",
                api_call,
                input_tokens=0,  # Free!
                output_tokens=0
            )
        else:
            return await api_call()

    async def _call_ollama(
        self,
        model: str,
        messages: List[Dict],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> str:
        """Call Ollama (local) - fallback option"""
        try:
            import ollama
        except ImportError:
            raise Exception("Ollama not installed and no API keys available")

        response = ollama.chat(
            model=model,
            messages=messages,
            options={
                "temperature": temperature,
                "num_predict": max_tokens
            }
        )

        return response['message']['content']

    def get_provider_for_model(self, model: str) -> str:
        """Get provider name for a model"""
        return self.model_to_provider.get(model, "unknown")

    def is_model_available(self, model: str) -> bool:
        """Check if a model is available"""
        provider = self.get_provider_for_model(model)

        if provider == "anthropic":
            return self._get_anthropic_client() is not None
        elif provider == "openai":
            return self._get_openai_client() is not None
        elif provider == "groq":
            return self._get_groq_client() is not None
        elif provider == "ollama":
            try:
                import ollama
                return True
            except ImportError:
                return False

        return False
