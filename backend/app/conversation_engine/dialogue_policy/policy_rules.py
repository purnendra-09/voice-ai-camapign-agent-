from typing import Any, Dict, List


PRIORITY = {
    "EMERGENCY": 1,
    "WRONG_NUMBER": 1,
    "NOT_INTERESTED": 6,
    "BUSY": 6,
    "CALLBACK": 6,
    "CONFIRM_ATTENDANCE": 6,
}


QUESTION_TO_INTENT = {
    "identity": "ASK_IDENTITY",
    "purpose": "ASK_PURPOSE",
    "campaign": "ASK_CAMPAIGN",
    "location": "ASK_LOCATION",
    "time": "ASK_TIME",
    "doctor": "ASK_DOCTOR",
    "medicine": "ASK_MEDICINE",
    "fee": "ASK_FEE",
    "memory": "ASK_MEMORY",
    "unexpected": "ASK_UNEXPECTED",
}


KNOWLEDGE_BY_QUESTION = {
    "identity": ["identity.md"],
    "purpose": ["identity.md", "campaign.md"],
    "campaign": ["campaign.md", "faq.md"],
    "location": ["campaign.md", "faq.md"],
    "time": ["campaign.md", "faq.md"],
    "doctor": ["hospital.md", "faq.md"],
    "medicine": ["faq.md", "business_rules.md"],
    "fee": ["campaign.md", "faq.md"],
    "memory": [],
    "unexpected": [],
}


GOAL_BY_QUESTION = {
    "identity": "Answer identity",
    "purpose": "Answer purpose",
    "campaign": "Explain campaign",
    "location": "Answer venue",
    "time": "Answer timing",
    "doctor": "Answer doctor availability",
    "medicine": "Answer medicine or test question",
    "fee": "Answer fee question",
    "memory": "Answer from conversation memory",
    "unexpected": "Redirect off-topic question",
}


ACTION_BY_QUESTION = {
    "identity": "ANSWER_IDENTITY",
    "purpose": "ANSWER_PURPOSE",
    "campaign": "ANSWER_CAMPAIGN",
    "location": "ANSWER_LOCATION",
    "time": "ANSWER_TIME",
    "doctor": "ANSWER_DOCTOR",
    "medicine": "ANSWER_FAQ",
    "fee": "ANSWER_FAQ",
    "memory": "ANSWER_MEMORY",
    "unexpected": "REDIRECT_OFF_TOPIC",
}


class DialoguePolicyRules:
    """Priority rules that choose exactly one active goal."""

    def select_questions_to_answer(self, detected_intent: str, pending: List[str], latest_questions: List[str]) -> List[str]:
        if detected_intent in PRIORITY and PRIORITY[detected_intent] == 1:
            return []
        if pending:
            return list(dict.fromkeys(pending))
        return [q for q in latest_questions if q != "unexpected"]

    def intent_from_questions(self, questions: List[str], fallback: str) -> str:
        if not questions:
            return fallback
        if "unexpected" in questions:
            return "ASK_UNEXPECTED"
        return QUESTION_TO_INTENT.get(questions[0], fallback)

    def avoid_list(self, memory: Dict[str, Any]) -> List[str]:
        avoid = ["hallucinate", "guess hospital information", "ask multiple questions"]
        if memory.get("greeted", True):
            avoid.append("repeat greeting")
        if memory.get("campaign_explained"):
            avoid.append("repeat campaign")
        if memory.get("interest_confirmed"):
            avoid.append("ask if interested again")
        return avoid

    def knowledge_needed(self, questions: List[str]) -> List[str]:
        files: List[str] = []
        for question in questions:
            files.extend(KNOWLEDGE_BY_QUESTION.get(question, []))
        return list(dict.fromkeys(files))
