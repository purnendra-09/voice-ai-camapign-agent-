from typing import Dict, List


class TeluguPhraseLibrary:
    """Reusable everyday Andhra Telugu phrases for voice responses."""

    PHRASES: Dict[str, List[str]] = {
        "acknowledgement": [
            "Avunandi.",
            "Sare andi.",
            "Ardam ayyindi.",
            "Bagundi.",
            "Parledandi.",
        ],
        "agreement": [
            "Chaala santosham.",
            "Bagundi andi.",
            "Sare andi, noted.",
        ],
        "thinking": [
            "Oka nimisham andi.",
            "Chepthanu andi.",
        ],
        "empathy": [
            "Ayyo, ardam ayyindi andi.",
            "Parledandi.",
            "Mee situation ardam ayyindi.",
        ],
        "explanation": [
            "July 15 na free health camp undi.",
            "Free check-up mariyu free homeo medicines untayi.",
            "Hospital team akkada guide chestaru.",
        ],
        "confirmation": [
            "Tappakunda randi andi.",
            "Mee attendance note chesukuntanu.",
        ],
        "closing": [
            "Dhanyavadalu andi.",
            "Manchi roju.",
            "Kaluddam andi.",
        ],
        "unknown_fact": [
            "Naaku ippudu clear details levu andi.",
            "Hospital team exact details share chestaru.",
        ],
    }

    PERSONALITY = {
        "role": "friendly hospital employee",
        "language": "simple everyday Andhra Telugu",
        "traits": ["patient", "warm", "helpful", "respectful", "not scripted"],
        "avoid": ["corporate tone", "ChatGPT tone", "brochure style", "long paragraphs"],
    }

    def for_prompt(self) -> Dict[str, List[str]]:
        return self.PHRASES

    def personality(self) -> Dict[str, object]:
        return self.PERSONALITY
