from typing import Any, Dict, List

from app.conversation_engine.conversation_intelligence import AnswerAssembler


class ResponseCritic:
    """Reviews the candidate reply before it leaves the engine."""

    def __init__(self):
        self.answer_assembler = AnswerAssembler()

    def review(
        self,
        candidate: str,
        session: Dict[str, Any],
        policy_plan: Dict[str, Any],
        confidence: Dict[str, Any],
    ) -> Dict[str, Any]:
        text = (candidate or "").strip()
        lowered = text.lower()
        issues: List[str] = []
        previous = self._previous_assistant(session)
        if not text:
            issues.append("empty")
        if previous and previous.strip().lower() == lowered:
            issues.append("loop")
        if "namaskaram" in lowered and "repeat greeting" in policy_plan.get("avoid", []):
            issues.append("repeated_greeting")
        if policy_plan.get("questions_to_answer") and "?" in text:
            issues.append("asked_question_before_answering")
        if policy_plan.get("questions_to_answer") and not self._answers_expected_question(lowered, policy_plan.get("questions_to_answer")):
            issues.append("ignored_pending_question")
        if len(text.split()) > 38:
            issues.append("too_long")
        if confidence.get("score", 100) < 70 and "confirm" not in lowered and "clear" not in lowered:
            issues.append("low_confidence_not_disclosed")
        return {
            "passed": not issues,
            "issues": issues,
            "would_real_executive_say_this": not {"empty", "loop", "too_long"}.intersection(issues),
        }

    def revise(
        self,
        candidate: str,
        review: Dict[str, Any],
        policy_plan: Dict[str, Any],
        confidence: Dict[str, Any],
    ) -> str:
        text = (candidate or "").strip()
        if "empty" in review["issues"]:
            text = "Artham ayindi andi. Homeo Pills Hospital camp gurinchi cheppandi."
        if "loop" in review["issues"]:
            if policy_plan.get("close_conversation"):
                text = "Dhanyavadalu andi. Manchi roju."
            else:
                text = "Artham ayindi andi. Inka vere campaign doubt unte cheppandi."
        if "low_confidence_not_disclosed" in review["issues"]:
            text = "Aa information confirm ga naa daggara ledu andi. Hospital team exact details share chestaru."
        if "ignored_pending_question" in review["issues"]:
            text = self._fallback_answer(policy_plan)
        if "too_long" in review["issues"]:
            text = ". ".join(text.split(".")[:2]).strip()
            if text and not text.endswith("."):
                text += "."
        return text

    def naturalize(self, text: str) -> str:
        replacements = {
            "Doctor details unavailable.": "Doctor details ippudu naa daggara confirm ga levu andi.",
            "Venue details unavailable.": "Venue details ippudu confirm ga levu andi.",
            "Timing unavailable.": "Timing ippudu confirm ga ledu andi.",
            "I do not have confirmed information.": "Aa information confirm ga naa daggara ledu andi.",
        }
        natural = text or ""
        for before, after in replacements.items():
            natural = natural.replace(before, after)
        return natural.strip()

    def _answers_expected_question(self, lowered_text: str, questions: list[str]) -> bool:
        markers = {
            "identity": ["nenu", "hospital", "maatlad"],
            "purpose": ["call", "invite", "camp", "health"],
            "campaign": ["camp", "check", "medicine", "health"],
            "location": ["venue", "place", "location", "ekkada", "exact place", "details"],
            "time": ["time", "timing", "morning", "evening", "confirm"],
            "doctor": ["doctor", "hospital team", "guide"],
            "medicine": ["medicine", "mandulu", "doctor check"],
            "fee": ["free", "fee", "check-up"],
            "memory": ["peru", "adigaru", "chepparu", "answer"],
        }
        expected = [q for q in questions if q in markers]
        if not expected:
            return True
        return all(any(marker in lowered_text for marker in markers[q]) for q in expected)

    def _fallback_answer(self, policy_plan: Dict[str, Any]) -> str:
        answers = {
            "identity": "Nenu Homeo Pills Hospital nundi maatladutunnanu andi.",
            "purpose": "Free health camp gurinchi invite cheyyadaniki call chesanu andi.",
            "campaign": "Free health camp lo free check-up mariyu homeo medicines untayi andi.",
            "location": "Venue details ippudu confirm ga naa daggara levu andi. Hospital team exact place share chestaru.",
            "time": "Timing ippudu confirm ga naa daggara ledu andi. Hospital team correct time share chestaru.",
            "doctor": "Doctor details ippudu confirm ga naa daggara levu andi. Hospital team akkada guide chestaru.",
            "medicine": "Free homeo medicines untayi andi, kani doctor check chesaka matrame decide chestaru.",
            "fee": "Avunu andi, free health check-up untundi.",
            "memory": "Meeru adigina details ni nenu track chestunnanu andi.",
        }
        questions = policy_plan.get("questions_to_answer") or []
        if len(questions) > 1:
            return self.answer_assembler.assemble(questions, include_follow_up=True)
        for question in questions:
            if question in answers:
                return answers[question]
        return "Aa information confirm ga naa daggara ledu andi. Hospital team exact details share chestaru."

    def _previous_assistant(self, session: Dict[str, Any]) -> str:
        assistant_messages = [m.get("content", "") for m in session.get("messages", []) if m.get("role") == "assistant"]
        return assistant_messages[-1] if assistant_messages else ""
