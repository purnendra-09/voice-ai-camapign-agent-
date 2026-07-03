import httpx
import json
from typing import Any, Dict, List, Optional
from app.utils import get_logger

logger = get_logger(__name__)


class GeminiService:
    """OpenAI-compatible chat service for Groq/xAI, kept under the old name.

    The rest of the app historically imports GeminiService. Keeping this class
    name avoids a broad rename while allowing Groq or xAI Grok to be selected
    through configuration.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "llama-3.1-8b-instant",
        base_url: str = "https://api.groq.com/openai/v1",
        provider: str = "groq",
    ):
        """
        Initialize chat service

        Args:
            api_key: Provider API key
            model: Model name (default: gemini-pro)
            base_url: OpenAI-compatible API base URL
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.provider = provider
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        )

    async def generate_content(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate content using an OpenAI-compatible chat completions API

        Args:
            prompt: User prompt/question
            system_prompt: System context
            temperature: Temperature for generation (0-1)
            max_tokens: Maximum tokens in response
            tools: Optional list of tools for function calling

        Returns:
            Provider response
        """
        try:
            messages = []

            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt,
                })

            messages.append({
                "role": "user",
                "content": prompt,
            })

            request_body = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            if tools:
                request_body["tools"] = [
                    {
                        "type": "function",
                        "function": tool,
                    }
                    for tool in tools
                ]
                request_body["tool_choice"] = "auto"

            url = f"{self.base_url}/chat/completions"

            response = await self.client.post(
                url,
                json=request_body,
                timeout=30.0,
            )

            if response.status_code >= 400:
                error_msg = f"{self.provider} API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": "Failed to generate response",
                    "status_code": response.status_code,
                }

            result = response.json()
            logger.info(f"{self.provider} API call successful")

            return {
                "success": True,
                "data": result,
            }

        except httpx.TimeoutException:
            error_msg = f"{self.provider} API request timeout"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"Error calling {self.provider} API: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    async def extract_response_text(self, api_response: Dict[str, Any]) -> Optional[str]:
        """
        Extract text response from API response

        Args:
            api_response: Response from generate_content

        Returns:
            Text content or None
        """
        try:
            if not api_response.get("success"):
                return None

            message = self._extract_message(api_response)
            if message is not None:
                content = message.get("content")
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    return "".join(
                        part.get("text", "")
                        for part in content
                        if isinstance(part, dict)
                    ) or None

            data = api_response.get("data", {})
            candidates = data.get("candidates", [])
            if not candidates:
                return None

            content = candidates[0].get("content", {})
            parts = content.get("parts", [])

            if not parts:
                return None

            return parts[0].get("text")

        except Exception as e:
            logger.error(f"Error extracting response text: {str(e)}")
            return None

    async def extract_tool_calls(self, api_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract tool/function calls from API response

        Args:
            api_response: Response from generate_content

        Returns:
            List of tool calls
        """
        try:
            if not api_response.get("success"):
                return []

            message = self._extract_message(api_response)
            if message is not None:
                calls = []
                for tool_call in message.get("tool_calls") or []:
                    function = tool_call.get("function", {})
                    raw_args = function.get("arguments") or "{}"
                    try:
                        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                    except json.JSONDecodeError:
                        args = {}
                    calls.append({
                        "name": function.get("name"),
                        "args": args,
                    })
                return [call for call in calls if call.get("name")]

            data = api_response.get("data", {})
            candidates = data.get("candidates", [])
            if not candidates:
                return []

            content = candidates[0].get("content", {})
            parts = content.get("parts", [])

            tool_calls = []
            for part in parts:
                if "functionCall" in part:
                    tool_calls.append(part["functionCall"])

            return tool_calls

        except Exception as e:
            logger.error(f"Error extracting tool calls: {str(e)}")
            return []

    def _extract_message(self, api_response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        data = api_response.get("data", {})
        choices = data.get("choices", [])
        if not choices:
            return None
        message = choices[0].get("message")
        return message if isinstance(message, dict) else None

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
