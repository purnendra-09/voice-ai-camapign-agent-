from typing import Any, Dict, List, Optional

from app.services.action_models import BusinessAction
from app.services.planner_models import DialogueMemory, PolicyPlan
from app.services.response_goal import ResponseGoalGenerator


class PolicyRuleEngine:
    """Applies deterministic policy rules before any LLM wording."""

    def __init__(self):
        self.goals = ResponseGoalGenerator()

    def build_plan(
        self,
        intent: str,
        emotion: str,
        confidence: float,
        entities: Dict[str, Any],
        memory: DialogueMemory,
        hospital_context: Dict[str, Any],
        campaign_details: Dict[str, Any],
        next_state: str,
    ) -> PolicyPlan:
        campaign_date = str(campaign_details.get("campaign_date") or "July 15")
        hospital_name = str(hospital_context.get("hospital_name") or "Homeo Pills Hospital")
        known_facts = {
            "hospital_name": hospital_name,
            "campaign_date": campaign_date,
            "offer": campaign_details.get("offer") or "Free check-up and free homeo medicines",
        }
        forbidden = ["venue", "exact timings", "doctors", "address", "phone number"]
        questions = self._questions_for_intent(intent)
        close = intent in {"WRONG_NUMBER", "EMERGENCY", "CONFIRM_ATTENDANCE", "NOT_INTERESTED", "ALREADY_TREATED", "CALLBACK"}
        response = self._deterministic_response(intent, campaign_date, hospital_name, entities)
        return PolicyPlan(
            current_state=memory.current_state,
            patient_intent=intent,
            emotion=emotion,
            confidence=confidence,
            goal=self.goals.goal_for(intent, questions, entities),
            questions_to_answer=questions,
            questions_to_ask=self._questions_to_ask(intent, memory),
            avoid=self._avoid_list(memory),
            next_state="FINISHED" if close else next_state,
            close_conversation=close,
            requires_tool=False,
            tool=None,
            entities=entities,
            memory_updates={
                **self._memory_updates(intent, entities),
                "last_action": action.action,
                "last_expected_outcome": action.outcome_hint,
            },
            required_facts=known_facts,
            forbidden_claims=forbidden,
            deterministic_response=response,
            outcome_hint=self._outcome_for_intent(intent),
        )

    def build_plan_from_action(
        self,
        action: BusinessAction,
        intent: str,
        emotion: str,
        confidence: float,
        entities: Dict[str, Any],
        memory: DialogueMemory,
        hospital_context: Dict[str, Any],
        campaign_details: Dict[str, Any],
    ) -> PolicyPlan:
        campaign_date = str(campaign_details.get("campaign_date") or "July 15")
        hospital_name = str(hospital_context.get("hospital_name") or "Homeo Pills Hospital")
        known_facts = {
            "hospital_name": hospital_name,
            "campaign_date": campaign_date,
            "offer": campaign_details.get("offer") or "Free check-up and free homeo medicines",
        }
        return PolicyPlan(
            current_state=memory.current_state,
            patient_intent=intent,
            emotion=emotion,
            confidence=confidence,
            goal=action.goal,
            questions_to_answer=action.questions_to_answer,
            questions_to_ask=action.questions_to_ask,
            avoid=action.avoid,
            next_state=action.next_state,
            close_conversation=action.close_conversation,
            requires_tool=False,
            tool=None,
            entities=entities,
            memory_updates=self._memory_updates(intent, entities),
            required_facts=known_facts,
            forbidden_claims=["venue", "exact timings", "doctors", "address", "phone number"],
            deterministic_response=action.deterministic_response,
            outcome_hint=action.outcome_hint,
        )

    def _questions_for_intent(self, intent: str) -> List[str]:
        mapping = {
            "ASK_LOCATION": ["location"],
            "ASK_TIME": ["time"],
            "ASK_DOCTOR": ["doctor"],
            "ASK_MEDICINE": ["medicine"],
            "ASK_FEE": ["fee"],
            "ASK_CONTACT": ["contact"],
            "ASK_CAMPAIGN": ["campaign"],
        }
        return mapping.get(intent, [])

    def _questions_to_ask(self, intent: str, memory: DialogueMemory) -> List[str]:
        if intent == "BUSY":
            return ["callback_time"]
        if intent in {"ASK_LOCATION", "ASK_TIME", "ASK_MEDICINE", "ASK_FEE", "INTERESTED"} and not memory.interest_confirmed:
            return ["attendance"]
        if intent == "UNKNOWN" and not memory.interest_confirmed:
            return ["interest"]
        return []

    def _avoid_list(self, memory: DialogueMemory) -> List[str]:
        avoid = ["hallucinate", "guess hospital information", "ask multiple questions"]
        if memory.greeted:
            avoid.append("repeat greeting")
        if memory.campaign_explained:
            avoid.append("repeat campaign")
        if memory.interest_confirmed:
            avoid.append("ask if interested again")
        return avoid

    def _memory_updates(self, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        updates: Dict[str, Any] = {}
        if intent in {"INTERESTED", "CONFIRM_ATTENDANCE"}:
            updates["interest_confirmed"] = True
        if intent == "CALLBACK":
            updates["callback_requested"] = True
            updates["callback_time"] = " ".join(str(v) for v in entities.values()) or None
        if intent in {"ASK_LOCATION", "ASK_TIME", "ASK_MEDICINE", "ASK_FEE", "ASK_CAMPAIGN"}:
            updates["campaign_explained"] = True
        return updates

    def _outcome_for_intent(self, intent: str) -> Optional[str]:
        mapping = {
            "WRONG_NUMBER": "Wrong Number",
            "EMERGENCY": "Emergency",
            "CONFIRM_ATTENDANCE": "Interested",
            "NOT_INTERESTED": "Not Interested",
            "ALREADY_TREATED": "Already Treated",
            "CALLBACK": "Callback Requested",
        }
        return mapping.get(intent)

    def _deterministic_response(
        self,
        intent: str,
        campaign_date: str,
        hospital_name: str,
        entities: Dict[str, Any],
    ) -> Optional[str]:
        if intent == "INTERESTED" and entities.get("family_member"):
            return "Sare andi. Mee family member ki ee camp gurinchi cheppagalara? Free check-up mariyu free homeo medicines untayi."
        if intent == "ASK_CAMPAIGN" and entities.get("trust_check"):
            return f"Avunu andi, {hospital_name} campaign kosam call chestunnanu. {campaign_date} free health camp gurinchi invite cheyyadaniki call chesanu."
        responses = {
            "WRONG_NUMBER": "Kshaminchandi andi. Inconvenience ki sorry. Manchi roju.",
            "EMERGENCY": "Idi urgent la undi andi. Dayachesi immediate medical attention teesukondi. Emergency aithe 108 ki call cheyyandi.",
            "ALREADY_TREATED": "Bagundi andi. Mee arogyam bagundali ani korukuntunnam. Dhanyavadalu.",
            "CONFIRM_ATTENDANCE": f"Chala santosham andi. {campaign_date} camp ki tappakunda randi. {hospital_name} team meeku akkada guide chestaru. Dhanyavadalu.",
            "NOT_INTERESTED": "Parledandi. Mee samayam ichinanduku dhanyavadalu andi.",
            "BUSY": "Parledandi. Meeku eppudu callback cheyyali?",
            "CALLBACK": "Sare andi. Aa time lo callback cheyyadaniki note chestanu. Dhanyavadalu.",
            "ASK_LOCATION": f"Camp ekkada jarugutundo naaku ippudu clear details levu andi. Hospital team exact place share chestaru. {campaign_date} camp ki ravadaniki meeku interest unda?",
            "ASK_TIME": f"Camp time naaku ippudu clear ga available ledu andi. Hospital team correct time confirm chestaru. Meeru {campaign_date} ravagalara?",
            "ASK_FEE": "Avunu andi, free health check-up mariyu free homeo medicines untayi. Meeru attend avvagalara?",
            "ASK_MEDICINE": "Free homeo medicines untayi andi, kani medicine details doctor check chesaka cheptaru. Meeru camp ki ravadaniki interested aa?",
            "ASK_DOCTOR": "Doctor details naaku ippudu clear ga available levu andi. Hospital team akkada guide chestaru.",
            "ASK_CONTACT": "Contact number naaku ippudu clear ga available ledu andi. Hospital team details share chestaru.",
        }
        return responses.get(intent)
