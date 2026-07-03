from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseLLMService(ABC):
    """Provider-agnostic interface used by conversation orchestration."""

    @abstractmethod
    async def generate_content(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.4,
        max_tokens: int = 220,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Generate a model response."""

    @abstractmethod
    async def extract_response_text(self, api_response: Dict[str, Any]) -> Optional[str]:
        """Return assistant text from a provider response."""

    @abstractmethod
    async def extract_tool_calls(self, api_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return normalized tool calls from a provider response."""

    @abstractmethod
    async def close(self):
        """Close provider resources."""
