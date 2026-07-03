import re
from typing import Iterable, List


QUESTION_PATTERNS = {
    "location": [
        r"\bwhere\b",
        r"\blocation\b",
        r"\bvenue\b",
        r"\baddress\b",
        r"ekkada",
        r"place",
    ],
    "time": [
        r"\btime\b",
        r"\btiming\b",
        r"\bwhen\b",
        r"eppudu",
        r"enni gant",
        r"slot",
    ],
    "doctor": [
        r"\bdoctor\b",
        r"\bdr\b",
        r"specialist",
        r"doctor unt",
    ],
    "fee": [
        r"\bfee\b",
        r"\bcost\b",
        r"\bcharge\b",
        r"\bfree\b",
        r"dabbu",
        r"payment",
    ],
    "campaign": [
        r"\bcamp\b",
        r"\bcampaign\b",
        r"details",
        r"hospital nundi",
        r"meeru hospital",
    ],
    "medicine": [
        r"\bmedicine\b",
        r"\btablet\b",
        r"\bpills\b",
        r"mandulu",
    ],
    "contact": [
        r"\bphone\b",
        r"\bcontact\b",
        r"\bnumber\b",
    ],
}


ANSWER_PATTERNS = {
    "location": [r"location", r"venue", r"address", r"ekkada", r"kavali", r"amalapuram", r"hospital"],
    "time": [r"time", r"timing", r"morning", r"evening", r"am\b", r"pm\b", r"july", r"eppudu"],
    "doctor": [r"doctor", r"dr", r"specialist", r"available"],
    "fee": [r"free", r"cost", r"fee", r"charge", r"payment"],
    "campaign": [r"camp", r"campaign", r"check[- ]?up", r"health"],
    "medicine": [r"medicine", r"tablet", r"pills", r"mandulu"],
    "contact": [r"phone", r"contact", r"number"],
}


class QuestionTracker:
    """Tracks patient questions without relying on the LLM."""

    def extract_questions(self, message: str) -> List[str]:
        text = (message or "").lower()
        found: List[str] = []
        for question, patterns in QUESTION_PATTERNS.items():
            if any(re.search(pattern, text) for pattern in patterns):
                found.append(question)
        return found

    def add_asked(self, asked: Iterable[str], answered: Iterable[str], pending: Iterable[str], new_questions: Iterable[str]) -> tuple[List[str], List[str], List[str]]:
        asked_list = list(dict.fromkeys(list(asked or [])))
        answered_set = set(answered or [])
        pending_list = list(dict.fromkeys(list(pending or [])))
        for question in new_questions:
            if question not in asked_list:
                asked_list.append(question)
            if question not in answered_set and question not in pending_list:
                pending_list.append(question)
        return asked_list, list(dict.fromkeys(answered or [])), pending_list

    def answered_by_response(self, response_text: str, pending_questions: Iterable[str]) -> List[str]:
        text = (response_text or "").lower()
        answered: List[str] = []
        for question in pending_questions or []:
            patterns = ANSWER_PATTERNS.get(question, [])
            if any(re.search(pattern, text) for pattern in patterns):
                answered.append(question)
        return answered

    def resolve(self, answered: Iterable[str], pending: Iterable[str], resolved: Iterable[str]) -> tuple[List[str], List[str]]:
        answered_list = list(dict.fromkeys(list(answered or [])))
        resolved_set = set(resolved or [])
        for question in resolved or []:
            if question not in answered_list:
                answered_list.append(question)
        pending_list = [question for question in list(dict.fromkeys(pending or [])) if question not in resolved_set]
        return answered_list, pending_list
