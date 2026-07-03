from typing import Dict, Iterable, List


class AnswerAssembler:
    """Creates one natural caller reply after multiple decomposed questions."""

    ORDER = ["identity", "purpose", "campaign", "fee", "medicine", "location", "time", "doctor", "contact"]

    def assemble(
        self,
        questions: Iterable[str],
        context: Dict[str, str] | None = None,
        include_follow_up: bool = False,
    ) -> str:
        context = context or {}
        ordered = self._ordered(questions)
        answers = self.answer_map(context)
        parts = [answers[question] for question in ordered if question in answers]
        if include_follow_up and parts:
            parts.append("Inkemaina doubts unnaya andi?")
        return " ".join(parts) if parts else "Aa details ippudu confirm ga naa daggara levu andi. Hospital team share chestaru."

    def answer_map(self, context: Dict[str, str]) -> Dict[str, str]:
        hospital = context.get("hospital_name") or "Homeo Pills Hospital"
        campaign_date = context.get("campaign_date") or "July 15"
        offer = context.get("offer") or "Free check-up mariyu free homeo medicines"
        return {
            "identity": f"Nenu {hospital} nundi campaign executive la maatladutunnanu andi.",
            "purpose": f"{campaign_date} free health camp invite kosam call chesanu andi.",
            "campaign": f"{campaign_date} free health camp undi andi. {offer} untayi.",
            "fee": "Avunu andi, free health check-up untundi.",
            "medicine": "Free homeo medicines untayi andi, kani doctor check chesaka matrame decide chestaru.",
            "location": "Venue clear details levu andi. Hospital team exact place share chestaru.",
            "time": "Timing ippudu confirm ga naa daggara ledu andi. Hospital team correct time share chestaru.",
            "doctor": "Doctor details ippudu confirm ga naa daggara levu andi. Hospital team akkada guide chestaru.",
            "contact": "Contact number ippudu confirm ga naa daggara ledu andi. Hospital team share chestaru.",
        }

    def _ordered(self, questions: Iterable[str]) -> List[str]:
        unique = list(dict.fromkeys(questions or []))
        return sorted(unique, key=lambda item: self.ORDER.index(item) if item in self.ORDER else len(self.ORDER))
