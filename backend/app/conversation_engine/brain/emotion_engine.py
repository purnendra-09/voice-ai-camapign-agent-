from typing import Dict


class EmotionEngine:
    """Detects patient emotion and suggests tone controls."""

    def detect(self, patient_message: str, intent: str) -> Dict[str, str]:
        text = (patient_message or "").lower()
        if intent == "EMERGENCY" or any(token in text for token in ["bayam", "fear", "scared", "tension", "pain"]):
            emotion = "fear"
        elif intent in {"BUSY", "CALLBACK"}:
            emotion = "busy"
        elif intent in {"NOT_INTERESTED", "WRONG_NUMBER"}:
            emotion = "irritated"
        elif intent.startswith("ASK_"):
            emotion = "curious"
        elif intent in {"INTERESTED", "CONFIRM_ATTENDANCE"}:
            emotion = "happy"
        else:
            emotion = "neutral"

        controls = {
            "fear": {"tone": "calm and reassuring", "speed": "slow", "sentence_length": "short", "empathy": "high"},
            "busy": {"tone": "respectful", "speed": "quick", "sentence_length": "very short", "empathy": "medium"},
            "irritated": {"tone": "apologetic", "speed": "quick", "sentence_length": "short", "empathy": "high"},
            "curious": {"tone": "clear", "speed": "normal", "sentence_length": "short", "empathy": "medium"},
            "happy": {"tone": "warm", "speed": "normal", "sentence_length": "short", "empathy": "medium"},
            "neutral": {"tone": "warm", "speed": "normal", "sentence_length": "short", "empathy": "medium"},
        }
        return {"emotion": emotion, **controls[emotion]}
