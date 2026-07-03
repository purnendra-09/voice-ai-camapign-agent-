import re
from typing import Dict, List


QUESTION_PATTERNS: Dict[str, List[str]] = {
    "identity": [r"who are you", r"who is calling", r"evaru", r"meeru evaru", r"hospital nundi", r"hospital aa"],
    "purpose": [r"why.*call", r"why call", r"enduku.*call", r"purpose", r"what is this call"],
    "campaign": [r"camp enti", r"camp details", r"\bcampaign\b", r"health camp", r"em chestaru"],
    "location": [r"\bwhere\b", r"\blocation\b", r"\bvenue\b", r"\baddress\b", r"ekkada", r"\bplace\b"],
    "time": [r"\btime\b", r"\btiming\b", r"\bwhen\b", r"eppudu", r"enni gant", r"\bslot\b"],
    "doctor": [r"\bdoctor\b", r"\bdr\b", r"specialist", r"doctor unt", r"eye doctor"],
    "medicine": [r"\bmedicine\b", r"medicines", r"\btablet\b", r"\bpills\b", r"mandulu", r"tests"],
    "fee": [r"\bfee\b", r"\bcost\b", r"\bcharge\b", r"\bfree\b", r"dabbu", r"payment"],
    "contact": [r"\bphone\b", r"\bcontact\b", r"\bnumber\b"],
}


ACTION_BY_QUESTION = {
    "identity": "Answer Identity",
    "purpose": "Answer Purpose",
    "campaign": "Explain Campaign",
    "location": "Answer Venue",
    "time": "Answer Time",
    "doctor": "Answer Doctor",
    "medicine": "Answer Medicine",
    "fee": "Answer Fee",
    "contact": "Answer Contact",
}


class QuestionDecomposer:
    """Breaks one patient turn into every normal campaign question it contains."""

    def decompose(self, message: str) -> List[Dict[str, str]]:
        text = (message or "").lower()
        parts: List[Dict[str, str]] = []
        for question, patterns in QUESTION_PATTERNS.items():
            if any(re.search(pattern, text) for pattern in patterns):
                parts.append({"question": question, "action": ACTION_BY_QUESTION[question]})
        return parts

    def decompose_keys(self, message: str) -> List[str]:
        return [part["question"] for part in self.decompose(message)]
