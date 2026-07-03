import json
from typing import Any, Dict

from app.models import CallOutcome
from app.services.base_llm_service import BaseLLMService
from app.services.outcome_service import OutcomeService
from app.utils import get_logger

logger = get_logger(__name__)


class ConversationAnalyzer:
    """Analyzes Retell transcripts into structured campaign outcomes."""

    def __init__(self, llm_service: BaseLLMService | None, outcome_service: OutcomeService):
        self.llm = llm_service
        self.outcomes = outcome_service

    async def analyze_transcript(
        self,
        transcript: str,
        campaign_context: Dict[str, Any] | None = None,
    ) -> CallOutcome:
        """Classify intent, summarize the call, and return a structured outcome."""
        if not self.llm:
            return self.outcomes.normalize(self._rule_based_outcome(transcript))

        prompt = (
            "Analyze this outbound hospital campaign call transcript. "
            "Return only valid JSON with keys: status, summary, next_action, "
            "follow_up_required, confidence, sentiment, intent, notes. "
            "Allowed status values: Interested, Not Interested, Busy, No Answer, "
            "Wrong Number, Callback Requested, Already Treated, Appointment Requested, "
            "Emergency, Other. Apply precedence rules: Emergency overrides all, "
            "Wrong Number overrides non-emergency outcomes, Appointment Requested beats general interest, "
            "Callback Requested beats general interest when a callback time is requested, and no conversation means No Answer.\n\n"
            f"Campaign context: {json.dumps(campaign_context or {}, ensure_ascii=True)}\n\n"
            f"Transcript:\n{transcript}"
        )
        response = await self.llm.generate_content(
            prompt=prompt,
            system_prompt="You are a precise call outcome analyst for hospital outreach campaigns.",
            temperature=0.1,
            max_tokens=450,
            tools=None,
        )
        if response.get("success"):
            text = await self.llm.extract_response_text(response)
            parsed = self._parse_json(text or "")
            if parsed:
                return self.outcomes.normalize(parsed)

        logger.warning("LLM analysis failed or returned invalid JSON; using rule fallback")
        return self.outcomes.normalize(self._rule_based_outcome(transcript))

    def _parse_json(self, text: str) -> Dict[str, Any] | None:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end + 1])
                except json.JSONDecodeError:
                    return None
        return None

    def _rule_based_outcome(self, transcript: str) -> Dict[str, Any]:
        lowered = transcript.lower()
        if any(word in lowered for word in ["emergency", "urgent", "severe", "severe pain", "chala pain", "108"]):
            status = "Emergency"
        elif any(word in lowered for word in ["wrong number", "not this person", "wrong person", "tappu number"]):
            status = "Wrong Number"
        elif any(word in lowered for word in ["appointment", "book", "schedule"]):
            status = "Appointment Requested"
        elif any(word in lowered for word in ["call back", "callback", "later", "repu", "tomorrow", "morning", "evening"]):
            status = "Callback Requested"
        elif any(word in lowered for word in ["already treated", "already done", "treatment completed", "already treatment", "treatment ayindi"]):
            status = "Already Treated"
        elif any(word in lowered for word in ["busy", "not now", "ippudu busy"]):
            status = "Busy"
        elif any(word in lowered for word in ["no answer", "unanswered", "ringing"]):
            status = "No Answer"
        elif any(word in lowered for word in ["not interested", "don't call", "interest ledu", "vaddu"]):
            status = "Not Interested"
        elif any(word in lowered for word in ["yes", "interested", "tell me more", "avunu", "vastanu", "vasthanu", "ostanu", "ravachu"]):
            status = "Interested"
        else:
            status = "Other"
        return {
            "status": status,
            "summary": "Transcript analyzed with local fallback rules.",
            "next_action": "",
            "follow_up_required": status in {"Interested", "Callback Requested", "Appointment Requested", "Emergency"},
            "confidence": 0.45,
        }
