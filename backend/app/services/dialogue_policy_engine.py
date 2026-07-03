from app.conversation_engine.dialogue_policy import DialoguePolicyEngine


class EmotionDetector:
    """Compatibility shim retained for older imports."""

    def detect(self, message: str, intent: str) -> str:
        if intent in {"INTERESTED", "CONFIRM_ATTENDANCE"}:
            return "POSITIVE"
        if intent == "EMERGENCY":
            return "DISTRESSED"
        if intent in {"NOT_INTERESTED", "WRONG_NUMBER"}:
            return "NEGATIVE"
        if "?" in (message or "") or intent.startswith("ASK_"):
            return "CURIOUS"
        return "NEUTRAL"


__all__ = ["DialoguePolicyEngine", "EmotionDetector"]
