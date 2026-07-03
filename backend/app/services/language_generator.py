from typing import Optional

from app.services.phrase_library import TeluguPhraseLibrary
from app.services.response_blueprint import ResponseBlueprint


class LanguageGenerator:
    """Provider-neutral prompt builder for the LLM language step."""

    def __init__(self):
        self.phrases = TeluguPhraseLibrary()

    def build_prompt(self, blueprint: ResponseBlueprint, hospital_context: dict, campaign_context: dict, transcript: str) -> str:
        return (
            "Convert this response blueprint into natural spoken Telugu. "
            "Do not decide flow, state, next action, or facts. Follow the blueprint exactly.\n\n"
            f"BLUEPRINT_JSON: {blueprint.to_dict()}\n"
            f"HOSPITAL_CONTEXT: {hospital_context}\n"
            f"CAMPAIGN_CONTEXT: {campaign_context}\n"
            f"PERSONALITY: {self.phrases.personality()}\n"
            f"PHRASE_LIBRARY: {self.phrases.for_prompt()}\n\n"
            "Style rules: everyday Andhra Telugu, max 3 short sentences, no brochure tone, "
            "no greeting repetition, no campaign repetition unless blueprint says so, one question max.\n\n"
            f"Conversation so far:\n{transcript}\n\n"
            "Return only the final assistant reply."
        )

    def deterministic_fallback(self, blueprint: ResponseBlueprint) -> str:
        if blueprint.deterministic_text:
            return blueprint.deterministic_text
        if blueprint.ask_question:
            return f"Ardam ayyindi andi. {blueprint.ask_question}"
        return "Ardam ayyindi andi. Inka emaina doubt unda?"


class ResponseQualityValidator:
    """Scores and validates generated voice replies."""

    def score(self, response: str, blueprint: ResponseBlueprint) -> dict:
        text = (response or "").strip()
        lowered = text.lower()
        score = 100
        issues: list[str] = []

        sentence_count = sum(text.count(mark) for mark in [".", "?", "!"])
        if sentence_count > blueprint.max_sentences:
            score -= 20
            issues.append("too_many_sentences")
        if text.count("?") > 1:
            score -= 25
            issues.append("multiple_questions")
        if not blueprint.repeat_greeting and "namaskaram" in lowered:
            score -= 25
            issues.append("repeated_greeting")
        if not blueprint.repeat_campaign and lowered.count("free health camp") > 1:
            score -= 15
            issues.append("repeated_campaign")
        if not blueprint.repeat_interest and lowered.count("interest") > 1:
            score -= 15
            issues.append("repeated_interest")
        hallucination_terms = ["amalapuram", "9 am", "10 am", "doctor available", "confirmed appointment"]
        if any(term in lowered for term in hallucination_terms):
            score -= 40
            issues.append("hallucination")
        if len(text.split()) > 55:
            score -= 20
            issues.append("too_long")
        if any(word in lowered for word in ["as an ai", "unfortunately", "i apologize"]):
            score -= 20
            issues.append("robotic")

        return {
            "overall": max(score, 0),
            "natural_telugu": max(score - (10 if "details" in lowered else 0), 0),
            "human_likeness": max(score - (10 if len(text.split()) > 35 else 0), 0),
            "warmth": max(score - (10 if "dhanyavadalu" not in lowered and blueprint.thank_patient else 0), 0),
            "flow": score,
            "repetition": 100 if not any(issue.startswith("repeated") for issue in issues) else 60,
            "empathy": max(score - (15 if blueprint.emotion == "distressed" and "108" not in lowered else 0), 0),
            "conversation_progress": score,
            "issues": issues,
        }

    def validate(self, response: str, blueprint: ResponseBlueprint) -> Optional[str]:
        quality = self.score(response, blueprint)
        if quality["overall"] < 90:
            return None
        return response.strip()
