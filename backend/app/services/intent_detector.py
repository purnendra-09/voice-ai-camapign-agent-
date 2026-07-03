from app.services.planner_models import VALID_INTENTS


class IntentDetector:
    """Closed-set intent detector. It never invents new intents."""

    def detect(self, message: str) -> str:
        text = message.lower()
        checks = [
            ("WRONG_NUMBER", ["wrong number", "wrong person", "not this person", "tappu number", "wrong call"]),
            ("EMERGENCY", ["emergency", "urgent", "severe pain", "chala pain", "too much pain", "severe", "108"]),
            ("ALREADY_TREATED", ["already treatment", "already treated", "treatment ayindi", "already ayindi", "already done"]),
            ("CONFIRM_ATTENDANCE", ["i will come", "will come", "i can come", "vastanu", "vasthanu", "ostanu", "vastaru", "vastharu", "pakka"]),
            ("CONTINUE", ["cheppandi", "cheppu"]),
            ("BUSY", ["busy", "not now", "ippudu busy"]),
            ("CALLBACK", ["callback", "call back", "later", "repu", "tomorrow", "morning", "evening"]),
            ("NOT_INTERESTED", ["not interested", "interest ledu", "interest ledhu", "don't call", "vaddu", "no"]),
            ("ASK_UNEXPECTED", ["weather", "politics", "cricket", "movie", "loan"]),
            ("ASK_PREVIOUS_QUESTION", ["what did i ask", "nenu em adiganu", "em adiganu", "what have i asked"]),
            ("ASK_PREVIOUS_RESPONSE", ["what did you tell", "meeru em chepparu", "nuvvu em cheppavu"]),
            ("ASK_PATIENT_COMMITMENT", ["did i say yes", "did i confirm", "vastanu ani", "vasthanu ani", "attend avuthanu", "i will come"]),
            ("ASK_CONVERSATION_SUMMARY", ["what happened", "summary", "conversation enti", "mana conversation", "recap"]),
            ("ASK_CONVERSATION_TOPIC", ["what are we discussing", "topic enti", "em discuss", "deni gurinchi"]),
            ("ASK_MEMORY", ["naa peru", "did i say"]),
            ("ASK_IDENTITY", ["who are you", "who is calling", "evaru", "meeru evaru", "hospital nundi", "hospital aa", "are you from hospital", "homeo pills nundi"]),
            ("ASK_PURPOSE", ["why are you calling", "why call", "enduku call", "enduku andi", "purpose", "what is this call"]),
            ("ASK_LANGUAGE_CHANGE", ["english", "hindi", "telugu lo", "language"]),
            ("ASK_CONTACT", ["phone", "contact", "number"]),
            ("ASK_LOCATION", ["where", "location", "venue", "address", "ekkada", "place"]),
            ("ASK_TIME", ["time", "timing", "when", "eppudu", "enni gantalu", "slot"]),
            ("ASK_DOCTOR", ["doctor", "dr.", "specialist"]),
            ("ASK_MEDICINE", ["medicine", "medicines", "tablet", "pills", "mandulu", "homeo medicine"]),
            ("ASK_FEE", ["free", "cost", "charge", "fee", "dabbu", "payment"]),
            ("ASK_REPEAT", ["repeat", "again", "understand", "artham kale", "malli cheppu"]),
            ("ASK_CAMPAIGN", ["camp", "campaign", "health camp", "details", "free aa"]),
            ("INTERESTED", ["amma", "nanna", "father", "mother", "family", "wife", "husband", "kosam"]),
            ("INTERESTED", ["yes", "avunu", "interested", "interest undi", "sure", "cheppandi"]),
            ("GOODBYE", ["bye", "thank you", "thanks", "dhanyavadalu"]),
            ("GREETING", ["hello", "hi", "namaskaram"]),
        ]
        for intent, tokens in checks:
            if any(token in text for token in tokens):
                return intent
        return "UNKNOWN" if "UNKNOWN" in VALID_INTENTS else "UNKNOWN"
