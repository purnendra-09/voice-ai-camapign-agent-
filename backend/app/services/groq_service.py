import httpx
import json
import time
from typing import Any, Dict, List, Optional
from app.utils import get_logger
from app.services.base_llm_service import BaseLLMService

logger = get_logger(__name__)


class GroqService(BaseLLMService):
    """Service for Groq API interactions (OpenAI-compatible)"""

    def __init__(self, api_key: str, model: str = "mixtral-8x7b-32768"):
        """
        Initialize Groq Service

        Args:
            api_key: Groq API key
            model: Model name (default: mixtral-8x7b-32768)
        """
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.groq.com/openai/v1"
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(18.0, connect=5.0))

    async def generate_content(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.4,
        max_tokens: int = 220,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate content using Groq API

        Args:
            prompt: User prompt/question
            system_prompt: System context
            temperature: Temperature for generation (0-1)
            max_tokens: Maximum tokens in response
            tools: Optional list of tools for function calling

        Returns:
            Response from Groq API
        """
        try:
            started_at = time.perf_counter()
            # Build messages
            messages = []

            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })

            messages.append({
                "role": "user",
                "content": prompt
            })

            # Build request body
            request_body = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            # Add tools if provided (Groq supports function calling)
            if tools:
                request_body["tools"] = [{"type": "function", "function": tool} for tool in tools]
                request_body["tool_choice"] = "auto"

            # Make API call
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            response = await self.client.post(
                url,
                json=request_body,
                headers=headers,
            )
            latency_ms = round((time.perf_counter() - started_at) * 1000, 2)

            if response.status_code != 200:
                error_msg = f"Groq API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": "Failed to generate response",
                    "status_code": response.status_code,
                }

            result = response.json()
            logger.info(
                "Groq API call successful",
                extra={
                    "extra_data": {
                        "event": "llm_call_success",
                        "provider": "groq",
                        "model": self.model,
                        "latency_ms": latency_ms,
                        "has_tools": bool(tools),
                    }
                },
            )

            return {
                "success": True,
                "data": result,
            }

        except httpx.TimeoutException:
            error_msg = "Groq API request timeout"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"Error calling Groq API: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    async def extract_response_text(self, api_response: Dict[str, Any]) -> Optional[str]:
        """
        Extract text response from Groq API response

        Args:
            api_response: Response from generate_content

        Returns:
            Text content or None
        """
        try:
            if not api_response.get("success"):
                logger.debug(f"API response not successful: {api_response}")
                return None

            data = api_response.get("data", {})
            choices = data.get("choices", [])

            logger.debug(f"[DEBUG] Groq choices count: {len(choices)}")
            if not choices:
                logger.debug("[DEBUG] No choices in response")
                return None

            message = choices[0].get("message", {})
            logger.debug(f"[DEBUG] Message object: {message}")
            content = message.get("content")

            if isinstance(content, list):
                content = "".join(
                    part.get("text", "")
                    for part in content
                    if isinstance(part, dict)
                )

            if isinstance(content, str):
                content = " ".join(content.split())

            logger.info(
                "Extracted LLM response text",
                extra={
                    "extra_data": {
                        "event": "llm_text_extracted",
                        "has_text": bool(content),
                        "text_length": len(content or ""),
                    }
                },
            )
            return content or None

        except Exception as e:
            logger.error(f"Error extracting response text: {str(e)}")
            return None

    async def extract_tool_calls(self, api_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract tool/function calls from Groq API response

        Args:
            api_response: Response from generate_content

        Returns:
            List of tool calls
        """
        try:
            if not api_response.get("success"):
                return []

            data = api_response.get("data", {})
            choices = data.get("choices", [])

            if not choices:
                return []

            message = choices[0].get("message", {})
            tool_calls = message.get("tool_calls", [])

            extracted_calls = []
            for tool_call in tool_calls:
                raw_arguments = tool_call.get("function", {}).get("arguments", "{}")
                try:
                    arguments = json.loads(raw_arguments)
                except json.JSONDecodeError:
                    logger.warning(
                        "Malformed tool arguments from LLM",
                        extra={
                            "extra_data": {
                                "event": "tool_arguments_malformed",
                                "tool_call_id": tool_call.get("id"),
                            }
                        },
                    )
                    arguments = {}
                extracted_calls.append({
                    "id": tool_call.get("id"),
                    "name": tool_call.get("function", {}).get("name"),
                    "arguments": arguments,
                })

            return extracted_calls

        except Exception as e:
            logger.error(f"Error extracting tool calls: {str(e)}")
            return []

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
