from datetime import datetime
from typing import Any, Dict, List, Optional
import time
import uuid

from app.conversation_engine.brain import CognitiveConversationEngine
from app.models import CallOutcome
from app.services.base_llm_service import BaseLLMService
from app.services.campaign_orchestrator import CampaignOrchestrator
from app.services.campaign_service import CampaignService
from app.services.client_manager import ClientManager
from app.services.conversation_planner import ConversationPlanner, PlannerPromptBuilder, ResponseValidator
from app.services.language_generator import LanguageGenerator, ResponseQualityValidator
from app.services.prompt_manager import PromptManager
from app.services.response_planner import ResponsePlanner
from app.utils import get_logger

logger = get_logger(__name__)


class LocalTrainingService:
    """Provider-agnostic local conversation training interface."""

    def __init__(
        self,
        campaign_service: CampaignService,
        orchestrator: CampaignOrchestrator,
        prompt_manager: PromptManager,
        client_manager: ClientManager,
        llm_service: Optional[BaseLLMService] = None,
    ):
        self.campaigns = campaign_service
        self.orchestrator = orchestrator
        self.prompts = prompt_manager
        self.clients = client_manager
        self.llm = llm_service
        self.planner = ConversationPlanner()
        self.prompt_builder = PlannerPromptBuilder()
        self.response_validator = ResponseValidator()
        self.response_planner = ResponsePlanner()
        self.language_generator = LanguageGenerator()
        self.quality_validator = ResponseQualityValidator()
        self.cognitive_engine = CognitiveConversationEngine()
        self.sessions: Dict[str, Dict[str, Any]] = {}

    async def start_session(
        self,
        campaign_id: str,
        row_number: Optional[int] = None,
        client_id: Optional[str] = None,
        prompt_key: str = "campaign_calling",
    ) -> Dict[str, Any]:
        """Select a patient and start a local training conversation."""
        client_context = self.clients.get_client_metadata(client_id) if client_id else {}
        effective_prompt_key = prompt_key or client_context.get("prompt_key") or "campaign_calling"
        if prompt_key == "campaign_calling" and client_context.get("prompt_key"):
            effective_prompt_key = client_context["prompt_key"]

        start_result = self.campaigns.start_call(campaign_id, row_number)
        if not start_result.get("success"):
            logger.warning(
                "Using local-only fallback lead because campaign sheet has no pending lead",
                extra={"extra_data": {"campaign_id": campaign_id, "row_number": row_number}},
            )
            start_result = {
                "success": True,
                "lead": self._fallback_lead(campaign_id, row_number, effective_prompt_key),
                "local_only": True,
            }

        lead = start_result.get("lead") or {}
        session_id = str(uuid.uuid4())
        base_prompt = self.prompts.get_prompt(effective_prompt_key)
        client_name = client_context.get("name", "Hospital Campaign Team")
        system_prompt = self.prompts.generate_system_prompt(
            base_prompt=base_prompt,
            client_name=client_name,
            client_context=client_context,
        )
        system_prompt += self._build_training_context(lead, campaign_id)

        assistant_message = self._opening_message(lead)
        now = datetime.utcnow().isoformat()
        self.sessions[session_id] = {
            "session_id": session_id,
            "campaign_id": campaign_id,
            "row_number": lead.get("row_number"),
            "client_id": client_id,
            "lead": lead,
            "prompt_key": effective_prompt_key,
            "prompt_used": system_prompt,
            "messages": [
                {"role": "assistant", "content": assistant_message, "timestamp": now}
            ],
            "started_at": time.perf_counter(),
            "started_at_iso": now,
            "outcome": None,
            "updated": False,
        }
        return {
            "success": True,
            "session_id": session_id,
            "campaign_id": campaign_id,
            "lead": lead,
            "assistant_message": assistant_message,
            "prompt_key": effective_prompt_key,
        }

    async def send_message(self, session_id: str, message: str) -> Dict[str, Any]:
        """Send a patient message and return the AI caller reply."""
        session = self.sessions.get(session_id)
        if not session:
            return {"success": False, "session_id": session_id, "error": "Training session not found"}

        session["messages"].append(self._message("user", message))
        assistant_message = await self._generate_reply(session)
        session["messages"].append(self._message("assistant", assistant_message))
        return {
            "success": True,
            "session_id": session_id,
            "assistant_message": assistant_message,
        }

    async def finish_session(
        self,
        session_id: str,
        notes: Optional[str] = None,
        update_excel: bool = True,
    ) -> Dict[str, Any]:
        """Classify the completed training conversation and optionally update Excel."""
        session = self.sessions.get(session_id)
        if not session:
            return {"success": False, "session_id": session_id, "error": "Training session not found"}

        transcript = self._transcript(session["messages"])
        result = await self.orchestrator.complete_call(
            campaign_id=session["campaign_id"],
            row_number=session["row_number"],
            transcript=transcript,
            metadata={
                "source": "local_training",
                "notes": notes,
                "update_excel": update_excel,
            },
            update_excel=update_excel,
        )
        outcome = result.get("outcome")
        session["outcome"] = outcome.model_dump() if isinstance(outcome, CallOutcome) else outcome
        session["updated"] = result.get("updated", False)
        return self.report(session_id)

    def report(self, session_id: str) -> Dict[str, Any]:
        """Return the local training dashboard state."""
        session = self.sessions.get(session_id)
        if not session:
            return {"success": False, "session_id": session_id, "error": "Training session not found"}

        outcome = session.get("outcome")
        duration = round(time.perf_counter() - session["started_at"], 2)
        return {
            "success": True,
            "session_id": session_id,
            "campaign_id": session.get("campaign_id"),
            "current_patient": session.get("lead"),
            "conversation_history": session.get("messages", []),
            "current_outcome": outcome,
            "summary": outcome.get("summary") if isinstance(outcome, dict) else None,
            "confidence": outcome.get("confidence") if isinstance(outcome, dict) else None,
            "prompt_key": session.get("prompt_key"),
            "prompt_used": session.get("prompt_used"),
            "last_plan": session.get("last_plan"),
            "last_blueprint": session.get("last_blueprint"),
            "last_cognitive_trace": session.get("last_cognitive_trace"),
            "patient_context": session.get("lead") or {},
            "campaign_context": {
                "campaign_id": session.get("campaign_id"),
                "campaign": (session.get("lead") or {}).get("campaign"),
                "language": (session.get("lead") or {}).get("language"),
                "priority": (session.get("lead") or {}).get("priority"),
            },
            "duration_seconds": duration,
            "updated": session.get("updated", False),
        }

    def _message(self, role: str, content: str) -> Dict[str, str]:
        return {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def _generate_reply(self, session: Dict[str, Any]) -> str:
        plan = self.planner.plan(session)
        blueprint = self.response_planner.build_blueprint(plan)
        plan_dict = plan.to_dict()
        thought = self.cognitive_engine.think(session, plan_dict)
        session["last_plan"] = plan_dict
        session["last_blueprint"] = blueprint.to_dict()
        candidate = None
        if blueprint.deterministic_text:
            candidate = blueprint.deterministic_text

        if not candidate and not self.llm:
            candidate = self.language_generator.deterministic_fallback(blueprint)

        if not candidate:
            lead = session.get("lead") or {}
            raw = lead.get("raw") or {}
            prompt = self.language_generator.build_prompt(
                blueprint=blueprint,
                hospital_context={"hospital_name": raw.get("hospital_name") or "Homeo Pills Hospital"},
                campaign_context={
                    "campaign": lead.get("campaign") or session.get("campaign_id"),
                    "campaign_date": raw.get("campaign_date") or "July 15",
                    "offer": raw.get("offer") or "Free check-up and free homeo medicines",
                },
                transcript=self._transcript(session["messages"]),
            )
            response = await self.llm.generate_content(
                prompt=prompt,
                system_prompt=session["prompt_used"],
                temperature=0.35,
                max_tokens=180,
                tools=None,
            )
            if response.get("success"):
                text = await self.llm.extract_response_text(response)
                if text:
                    validated = self.quality_validator.validate(text, blueprint)
                    if validated:
                        candidate = self.response_validator.validate(validated, plan)
            if not candidate:
                candidate = self.language_generator.deterministic_fallback(blueprint)

        final_response, trace = self.cognitive_engine.finalize_response(
            candidate=candidate,
            session=session,
            policy_plan=plan_dict,
            thought=thought,
        )
        session["last_cognitive_trace"] = trace
        return final_response

    def _high_priority_rule_reply(self, session: Dict[str, Any]) -> Optional[str]:
        user_messages = [msg for msg in session["messages"] if msg["role"] == "user"]
        if not user_messages:
            return None

        latest = user_messages[-1]["content"].lower()
        lead = session.get("lead") or {}
        raw = lead.get("raw") or {}
        campaign_date = raw.get("campaign_date") or "July 15"
        if not self._is_homeo_campaign(lead, session.get("prompt_key")):
            return None

        if self._is_wrong_number(latest):
            return "Kshaminchandi andi. Inconvenience ki sorry. Manchi roju."
        if self._is_emergency(latest):
            return "Idi urgent la undi andi. Dayachesi immediate medical attention teesukondi. Emergency aithe 108 ki call cheyyandi."
        if self._is_already_treated(latest):
            return "Bagundi andi. Mee arogyam bagundali ani korukuntunnam. Dhanyavadalu."
        if self._patient_confirmed_attendance(latest):
            return f"Chala santosham andi. {campaign_date} camp ki tappakunda randi. Homeo Pills Hospital team meeku akkada guide chestaru. Dhanyavadalu."
        if self._asks_trust(latest):
            return "Avunu andi, Homeo Pills Hospital campaign kosam call chestunnanu. July 15 free health camp gurinchi invite cheyyadaniki call chesanu."
        if self._mentions_family(latest):
            return "Sare andi. Mee family member ki ee camp gurinchi cheppagalara? Free check-up mariyu free homeo medicines untayi."
        if self._asks_location(latest):
            return f"Camp ekkada jarugutundo naaku ippudu clear details levu andi. Hospital team exact place share chestaru. {campaign_date} camp ki ravadaniki meeku interest unda?"
        if self._asks_timing(latest):
            return f"Camp time naaku ippudu clear ga available ledu andi. Hospital team correct time confirm chestaru. Meeru {campaign_date} ravagalara?"
        if self._asks_cost(latest):
            return "Avunu andi, free health check-up mariyu free homeo medicines untayi. Meeru attend avvagalara?"
        if self._asks_medicine(latest):
            return "Free homeo medicines untayi andi, kani medicine details doctor check chesaka cheptaru. Meeru camp ki ravadaniki interested aa?"
        if self._asks_medical_advice(latest):
            return "Aa medical doubt ki doctor ni consult cheyyadam best andi. Camp lo hospital team guide chestaru. Meeru attend avvagalara?"
        if "busy" in latest or "later" in latest:
            return "Parledandi. Meeku eppudu callback cheyyali?"
        if "no" in latest or "not interested" in latest or "vaddu" in latest:
            return "Parledandi. Mee time ki thanks andi. Future lo avasaram unte Homeo Pills Hospital team ni contact cheyyandi."
        return None

    def _fallback_reply(self, session: Dict[str, Any]) -> str:
        user_messages = [msg for msg in session["messages"] if msg["role"] == "user"]
        if not user_messages:
            return self._opening_message(session.get("lead") or {})
        latest = user_messages[-1]["content"].lower()
        lead = session.get("lead") or {}
        is_homeo = self._is_homeo_campaign(lead, session.get("prompt_key"))
        raw = lead.get("raw") or {}
        campaign_date = raw.get("campaign_date") or "July 15"
        if self._is_wrong_number(latest):
            return "Kshaminchandi andi. Inconvenience ki sorry. Manchi roju."
        if self._is_emergency(latest):
            return "Idi urgent la undi andi. Dayachesi immediate medical attention teesukondi. Emergency aithe 108 ki call cheyyandi."
        if self._is_already_treated(latest):
            return "Bagundi andi. Mee arogyam bagundali ani korukuntunnam. Dhanyavadalu."
        if self._patient_confirmed_attendance(latest):
            return f"Chala santosham andi. {campaign_date} camp ki tappakunda randi. Homeo Pills Hospital team meeku akkada guide chestaru. Dhanyavadalu."
        if self._asks_trust(latest):
            return "Avunu andi, Homeo Pills Hospital campaign kosam call chestunnanu. July 15 free health camp gurinchi invite cheyyadaniki call chesanu."
        if self._mentions_family(latest):
            return "Sare andi. Mee family member ki ee camp gurinchi cheppagalara? Free check-up mariyu free homeo medicines untayi."
        if self._asks_location(latest):
            return f"Camp ekkada jarugutundo naaku ippudu clear details levu andi. Hospital team exact place share chestaru. {campaign_date} camp ki ravadaniki meeku interest unda?"
        if self._asks_timing(latest):
            return f"Camp time naaku ippudu clear ga available ledu andi. Hospital team correct time confirm chestaru. Meeru {campaign_date} ravagalara?"
        if self._asks_cost(latest):
            return "Avunu andi, free health check-up mariyu free homeo medicines untayi. Meeru attend avvagalara?"
        if self._asks_medicine(latest):
            return "Free homeo medicines untayi andi, kani medicine details doctor check chesaka cheptaru. Meeru camp ki ravadaniki interested aa?"
        if self._asks_medical_advice(latest):
            return "Aa medical doubt ki doctor ni consult cheyyadam best andi. Camp lo hospital team guide chestaru. Meeru attend avvagalara?"
        if "busy" in latest or "later" in latest:
            return "Parledandi. Meeku eppudu callback cheyyali?"
        if "appointment" in latest or "interested" in latest or "yes" in latest:
            if is_homeo:
                return f"Chala bagundi andi. {campaign_date} free health camp lo free check-up mariyu free homeo medicines untayi. Meeru attend avvagalara?"
            return "Chala bagundi andi. Maa hospital team follow-up chestaru. Meeku callback kavala?"
        if "no" in latest or "not interested" in latest or "vaddu" in latest:
            return "Parledandi. Mee time ki thanks andi. Future lo avasaram unte Homeo Pills Hospital team ni contact cheyyandi."
        if "wrong" in latest:
            return "Sorry andi. Inconvenience ki kshaminchandi. Dhanyavadalu."
        if "pain" in latest or "urgent" in latest or "emergency" in latest:
            return "Immediate attention avasaram undachu andi. Dayachesi nearest hospital leda 108 ni contact cheyyandi."
        if is_homeo:
            return f"Artham ayindi andi. {campaign_date} free health camp ki ravadaniki interest unda?"
        return "Artham ayindi andi. Ee hospital campaign gurinchi interest unda?"

    def _opening_message(self, lead: Dict[str, Any]) -> str:
        if self._is_homeo_campaign(lead):
            return "Namaskaram andi! Nenu Homeo Pills Hospital nundi maatladutunnanu. Mee tho oka nimisham maatladacha?"

        name = lead.get("patient_name") or "andi"
        campaign = lead.get("campaign") or "hospital campaign"
        hospital_name = (lead.get("raw") or {}).get("hospital_name") or "Hospital Campaign Team"
        return (
            f"Namaskaram {name} garu. Nenu {hospital_name} nundi maatladutunnanu. "
            f"{campaign} gurinchi rendu nimishalu maatladataniki samayam unda?"
        )

    def _build_training_context(self, lead: Dict[str, Any], campaign_id: str) -> str:
        raw_context = lead.get("raw") or {}
        return (
            "\n\nLocal training mode rules:"
            "\n- Input is coming from a developer acting as the patient, not a phone system."
            "\n- Behave exactly like a real outbound hospital campaign caller."
            "\n- Do not mention local testing, APIs, Excel, Retell, Twilio, or tools."
            "\n- Use Telugu-English naturally for Telugu patients."
            "\n- Ask one question at a time."
            "\n- Answer the patient's current question before asking a new question."
            "\n- Never invent venue, address, exact timings, doctors, phone numbers, or details not present in context."
            "\n- If a requested fact is unavailable, say it is not available and that the hospital team will share it."
            "\n- If the patient confirms attendance, close politely and do not repeat qualification questions."
            f"\n- Campaign ID: {campaign_id}"
            f"\n- Patient context: {lead}"
            f"\n- Campaign detail context: {raw_context}"
        )

    def _fallback_lead(
        self,
        campaign_id: str,
        row_number: Optional[int],
        prompt_key: str,
    ) -> Dict[str, Any]:
        is_homeo = "homeo" in (campaign_id or "").lower() or prompt_key == "homeo_pills_campaign"
        campaign = "Homeo Pills Free Health Camp" if is_homeo else campaign_id
        hospital_name = "Homeo Pills Hospital" if is_homeo else "Hospital Campaign Team"
        raw = {"source": "local_training_fallback", "hospital_name": hospital_name}
        if is_homeo:
            raw.update(
                {
                    "campaign_date": "July 15",
                    "campaign_message": (
                        "July 15 na maa Homeo Pills Hospital free health camp conduct chesthundi. "
                        "Free check-up mariyu free homeo medicines untayi."
                    ),
                    "offer": "Free check-up and free homeo medicines",
                    "region": "Andhra Pradesh",
                }
            )

        return {
            "row_number": row_number or 2,
            "patient_id": "LOCAL001",
            "patient_name": "Ravi Kumar",
            "phone_number": "9876543210",
            "language": "Telugu",
            "campaign": campaign,
            "priority": "High",
            "status": "Local Training",
            "call_attempts": 0,
            "assigned_agent": "Homeo Pills Campaign Executive" if is_homeo else "AI Campaign Bot",
            "raw": raw,
        }

    def _is_homeo_campaign(
        self,
        lead: Dict[str, Any],
        prompt_key: Optional[str] = None,
    ) -> bool:
        raw = lead.get("raw") or {}
        text = " ".join(
            str(value)
            for value in [
                prompt_key,
                lead.get("campaign"),
                lead.get("assigned_agent"),
                raw.get("hospital_name"),
                raw.get("campaign_message"),
            ]
            if value
        ).lower()
        return "homeo pills" in text or "homeo_pills" in text

    def _patient_confirmed_attendance(self, text: str) -> bool:
        confirmations = [
            "i will come",
            "will come",
            "i can come",
            "sure i will attend",
            "confirm",
            "confirmed",
            "attend chestha",
            "vastanu",
            "vasthanu",
            "ostanu",
            "vastaru",
            "vastharu",
            "ravachu",
            "pakka",
        ]
        return any(token in text for token in confirmations)

    def _is_wrong_number(self, text: str) -> bool:
        tokens = ["wrong number", "wrong person", "not this person", "tappu number", "wrong num"]
        return any(token in text for token in tokens)

    def _is_emergency(self, text: str) -> bool:
        tokens = ["emergency", "urgent", "severe pain", "chala pain", "too much pain", "severe", "108"]
        return any(token in text for token in tokens)

    def _is_already_treated(self, text: str) -> bool:
        tokens = ["already treatment", "already treated", "treatment ayindi", "already ayindi", "already done"]
        return any(token in text for token in tokens)

    def _asks_trust(self, text: str) -> bool:
        tokens = ["hospital nundi", "hospital aa", "meeru hospital", "are you from hospital", "homeo pills nundi"]
        return any(token in text for token in tokens)

    def _mentions_family(self, text: str) -> bool:
        tokens = ["amma", "nanna", "father", "mother", "family", "wife", "husband", "kosam"]
        return any(token in text for token in tokens)

    def _asks_location(self, text: str) -> bool:
        tokens = ["where", "location", "venue", "address", "ekkada", "place"]
        return any(token in text for token in tokens)

    def _asks_timing(self, text: str) -> bool:
        tokens = ["time", "timing", "when", "eppudu", "enni gantalu", "slot"]
        return any(token in text for token in tokens)

    def _asks_cost(self, text: str) -> bool:
        tokens = ["free", "cost", "charge", "fee", "dabbu", "payment"]
        return any(token in text for token in tokens)

    def _asks_medicine(self, text: str) -> bool:
        tokens = ["medicine", "medicines", "tablet", "pills", "mandulu", "homeo medicine"]
        return any(token in text for token in tokens)

    def _asks_medical_advice(self, text: str) -> bool:
        tokens = ["cure", "treatment", "problem", "disease", "sugar", "bp", "pain", "medicine for"]
        return any(token in text for token in tokens)

    def _transcript(self, messages: List[Dict[str, str]]) -> str:
        lines = []
        for message in messages:
            speaker = "AI Caller" if message["role"] == "assistant" else "Patient"
            lines.append(f"{speaker}: {message['content']}")
        return "\n".join(lines)
