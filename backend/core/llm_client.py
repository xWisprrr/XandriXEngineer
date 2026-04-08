"""
XandriX Engineer - LLM Client
Supports OpenAI, Anthropic, Ollama, and Groq with a unified interface.
"""
import json
import re
from typing import Any, AsyncGenerator, Optional

import httpx

from backend.config import (
    LLM_API_KEY, LLM_BASE_URL, LLM_MAX_TOKENS, LLM_MODEL,
    LLM_PROVIDER, LLM_TEMPERATURE,
)


class LLMMessage:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


class LLMResponse:
    def __init__(self, content: str, usage: dict = None, model: str = ""):
        self.content = content
        self.usage = usage or {}
        self.model = model

    def extract_json(self) -> Any:
        """Extract JSON from the response, handling markdown code blocks."""
        content = self.content.strip()
        # Try to find JSON in code blocks
        patterns = [
            r"```json\s*([\s\S]*?)\s*```",
            r"```\s*([\s\S]*?)\s*```",
            r"\{[\s\S]*\}",
            r"\[[\s\S]*\]",
        ]
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                try:
                    text = match.group(1) if match.lastindex else match.group(0)
                    return json.loads(text.strip())
                except json.JSONDecodeError:
                    continue
        # Try parsing the whole thing
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return None

    def extract_code(self, language: str = None) -> Optional[str]:
        """Extract code from markdown code blocks."""
        if language:
            pattern = rf"```{language}\s*([\s\S]*?)\s*```"
        else:
            pattern = r"```(?:\w+)?\s*([\s\S]*?)\s*```"
        match = re.search(pattern, self.content)
        if match:
            return match.group(1).strip()
        return self.content.strip()


class LLMClient:
    """Unified LLM client supporting multiple providers."""

    def __init__(self):
        self.provider = LLM_PROVIDER
        self.model = LLM_MODEL
        self.api_key = LLM_API_KEY
        self.base_url = LLM_BASE_URL
        self.temperature = LLM_TEMPERATURE
        self.max_tokens = LLM_MAX_TOKENS
        self._client = httpx.AsyncClient(timeout=120.0)

    async def chat(
        self,
        messages: list[LLMMessage],
        system: str = None,
        temperature: float = None,
        max_tokens: int = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Send a chat request to the configured LLM provider."""
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens or self.max_tokens

        if self.provider == "openai":
            return await self._openai_chat(messages, system, temp, tokens, json_mode)
        elif self.provider == "anthropic":
            return await self._anthropic_chat(messages, system, temp, tokens)
        elif self.provider == "ollama":
            return await self._ollama_chat(messages, system, temp, tokens)
        elif self.provider == "groq":
            return await self._groq_chat(messages, system, temp, tokens, json_mode)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    async def _openai_chat(
        self, messages: list[LLMMessage], system: str,
        temperature: float, max_tokens: int, json_mode: bool
    ) -> LLMResponse:
        base = self.base_url or "https://api.openai.com/v1"
        msg_list = []
        if system:
            msg_list.append({"role": "system", "content": system})
        msg_list.extend(m.to_dict() for m in messages)

        payload = {
            "model": self.model,
            "messages": msg_list,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        resp = await self._client.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            usage=data.get("usage", {}),
            model=data.get("model", self.model),
        )

    async def _anthropic_chat(
        self, messages: list[LLMMessage], system: str,
        temperature: float, max_tokens: int
    ) -> LLMResponse:
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [m.to_dict() for m in messages],
        }
        if system:
            payload["system"] = system

        resp = await self._client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return LLMResponse(
            content=data["content"][0]["text"],
            usage=data.get("usage", {}),
            model=data.get("model", self.model),
        )

    async def _ollama_chat(
        self, messages: list[LLMMessage], system: str,
        temperature: float, max_tokens: int
    ) -> LLMResponse:
        base = self.base_url or "http://localhost:11434"
        msg_list = []
        if system:
            msg_list.append({"role": "system", "content": system})
        msg_list.extend(m.to_dict() for m in messages)

        resp = await self._client.post(
            f"{base}/api/chat",
            json={
                "model": self.model,
                "messages": msg_list,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return LLMResponse(
            content=data["message"]["content"],
            model=data.get("model", self.model),
        )

    async def _groq_chat(
        self, messages: list[LLMMessage], system: str,
        temperature: float, max_tokens: int, json_mode: bool
    ) -> LLMResponse:
        msg_list = []
        if system:
            msg_list.append({"role": "system", "content": system})
        msg_list.extend(m.to_dict() for m in messages)

        payload = {
            "model": self.model,
            "messages": msg_list,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        resp = await self._client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            usage=data.get("usage", {}),
            model=data.get("model", self.model),
        )

    async def close(self) -> None:
        await self._client.aclose()


# Global LLM client instance
llm = LLMClient()
