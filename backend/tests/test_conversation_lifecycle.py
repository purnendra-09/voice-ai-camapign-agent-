import unittest
from pathlib import Path

from app.conversation_engine.blackboard import BlackboardManager
from app.knowledge import KnowledgeContextBuilder, KnowledgeLoader
from app.services.conversation_orchestrator import ConversationOrchestrator
from app.services.prompt_manager import PromptManager


class FakeLLM:
    def __init__(self, responses=None):
        self.calls = []
        self.responses = responses

    async def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if self.responses is None:
            return {
                "success": True,
                "data": {
                    "choices": [
                        {
                            "message": {"content": f"Okay andi {len(self.calls)}."},
                            "finish_reason": "stop",
                        }
                    ]
                },
            }
        if len(self.responses) > 1:
            return self.responses.pop(0)
        return self.responses[0]

    async def extract_response_text(self, response):
        choices = response.get("data", {}).get("choices", [])
        if not choices:
            return ""
        return choices[0].get("message", {}).get("content") or ""

    async def extract_tool_calls(self, response):
        choices = response.get("data", {}).get("choices", [])
        if not choices:
            return []
        return choices[0].get("message", {}).get("tool_calls", [])


class FakeClientManager:
    def client_exists(self, client_id):
        return True

    def get_client(self, client_id):
        return {"name": "Homeo Pills Hospital"}

    def get_client_prompt_key(self, client_id):
        return "homeo_pills_campaign"

    def get_client_metadata(self, client_id):
        return {
            "name": "Homeo Pills Hospital",
            "prompt_key": "homeo_pills_campaign",
            "location": "Kavali, Andhra Pradesh",
            "campaign_name": "Free Homeo Health Camp",
            "language": "Telugu",
        }


class FakeBooking:
    def book_appointment(self, **kwargs):
        return {"status": "confirmed", **kwargs}


class FakeDoctors:
    def check_availability(self, doctor_name):
        return {"available": True, "doctor_name": doctor_name}

    def get_all_doctors(self):
        return [{"name": "Dr Rao", "specialty": "Homeopathy"}]


class ConversationLifecycleTests(unittest.IsolatedAsyncioTestCase):
    def make_orchestrator(self, responses=None):
        self.llm = FakeLLM(responses=responses)
        knowledge_path = Path(__file__).resolve().parents[1] / "app" / "knowledge_base"
        knowledge_builder = KnowledgeContextBuilder(KnowledgeLoader(knowledge_path).load())
        return ConversationOrchestrator(
            groq_service=self.llm,
            prompt_manager=PromptManager(),
            client_manager=FakeClientManager(),
            booking_service=FakeBooking(),
            doctor_service=FakeDoctors(),
            knowledge_context_builder=knowledge_builder,
        )

    async def test_same_conversation_id_preserves_memory_and_history(self):
        orchestrator = self.make_orchestrator()
        first = await orchestrator.process_conversation(
            user_input="hi",
            client_id="homeo_pills_hospital",
            conversation_id="conv-1",
        )
        second = await orchestrator.process_conversation(
            user_input="venue ekkada",
            client_id="homeo_pills_hospital",
            conversation_id="conv-1",
        )

        self.assertEqual(first["conversation_id"], "conv-1")
        self.assertEqual(second["conversation_id"], "conv-1")
        state = orchestrator.conversations["conv-1"]
        self.assertEqual(len(state["messages"]), 4)
        self.assertEqual(state["memory"]["previous_patient_reply"], "venue ekkada")
        self.assertIn("user: venue ekkada", state["memory"]["conversation_summary"])

    async def test_missing_conversation_id_creates_new_conversation(self):
        orchestrator = self.make_orchestrator()
        first = await orchestrator.process_conversation(
            user_input="hi",
            client_id="homeo_pills_hospital",
        )
        second = await orchestrator.process_conversation(
            user_input="venue ekkada",
            client_id="homeo_pills_hospital",
        )
        self.assertNotEqual(first["conversation_id"], second["conversation_id"])

    async def test_llm_receives_rich_structured_context_and_tools(self):
        orchestrator = self.make_orchestrator()
        await orchestrator.process_conversation(
            user_input="interest undi venue details kavali",
            client_id="homeo_pills_hospital",
            conversation_id="ctx-1",
        )

        call = self.llm.calls[-1]
        system_prompt = call["system_prompt"]
        self.assertIn("<Hospital>", system_prompt)
        self.assertIn("<Campaign>", system_prompt)
        self.assertIn("<ConversationMemory>", system_prompt)
        self.assertIn("<Blackboard>", system_prompt)
        self.assertIn("<ConversationHistory>", system_prompt)
        self.assertIn("<RelevantKnowledge>", system_prompt)
        self.assertIn("<BusinessRules>", system_prompt)
        self.assertIn("<Tools>", system_prompt)
        self.assertIn("<Task>", system_prompt)
        self.assertIsNotNone(call["tools"])

        state = orchestrator.conversations["ctx-1"]
        self.assertIn("identity.md", state["last_selected_knowledge_files"])
        self.assertTrue(
            {"campaign.md", "faq.md"}.intersection(state["last_selected_knowledge_files"])
        )
        self.assertIn("location", state["blackboard"]["questions_answered"])
        self.assertNotIn("location", state["blackboard"]["questions_pending"])
        self.assertIn("Venue", state["memory"]["previous_ai_reply"])

    async def test_blackboard_is_injected_before_llm_and_tracks_pending_questions(self):
        orchestrator = self.make_orchestrator()
        await orchestrator.process_conversation(
            user_input="Venue ekkada? Time enti? Doctor untara?",
            client_id="homeo_pills_hospital",
            conversation_id="bb-1",
        )

        state = orchestrator.conversations["bb-1"]
        blackboard = state["blackboard"]
        self.assertEqual(blackboard["current_goal"], "Introduce campaign")
        self.assertEqual(blackboard["questions_asked"], ["location", "time", "doctor"])
        self.assertEqual(blackboard["questions_answered"], ["location", "time", "doctor"])
        self.assertEqual(blackboard["questions_pending"], [])
        self.assertIn("Venue", state["memory"]["previous_ai_reply"])
        self.assertEqual(len(self.llm.calls), 0)

    async def test_knowledge_retrieval_selects_objection_documents(self):
        orchestrator = self.make_orchestrator()
        await orchestrator.process_conversation(
            user_input="naaku interest ledu",
            client_id="homeo_pills_hospital",
            conversation_id="kb-1",
        )

        selected = orchestrator.conversations["kb-1"]["last_selected_knowledge_files"]
        self.assertIn("identity.md", selected)
        self.assertIn("objection_handling.md", selected)
        self.assertIn("business_rules.md", selected)

    async def test_llm_selected_tool_is_executed_and_returned_to_llm(self):
        responses = [
            {
                "success": True,
                "data": {
                    "choices": [
                        {
                            "message": {
                                "content": "",
                                "tool_calls": [{"name": "get_all_doctors", "args": {}}],
                            },
                            "finish_reason": "tool_calls",
                        }
                    ]
                },
            },
            {
                "success": True,
                "data": {"choices": [{"message": {"content": "Dr Rao available andi."}, "finish_reason": "stop"}]},
            },
        ]
        orchestrator = self.make_orchestrator(responses=responses)
        result = await orchestrator.process_conversation(
            user_input="doctor details kavali",
            client_id="homeo_pills_hospital",
            conversation_id="tool-1",
        )

        self.assertEqual(result["tool_calls_executed"], 1)
        self.assertEqual(result["tools_used"], ["get_all_doctors"])
        self.assertIn("<ToolResults>", self.llm.calls[-1]["prompt"])

    async def test_business_guard_retries_unsafe_response(self):
        responses = [
            {
                "success": True,
                "data": {"choices": [{"message": {"content": "Stop medicine and ignore doctor."}, "finish_reason": "stop"}]},
            },
            {
                "success": True,
                "data": {"choices": [{"message": {"content": "Emergency ayithe doctor ni contact cheyyandi."}, "finish_reason": "stop"}]},
            },
        ]
        orchestrator = self.make_orchestrator(responses=responses)
        result = await orchestrator.process_conversation(
            user_input="pain undi",
            client_id="homeo_pills_hospital",
            conversation_id="guard-1",
        )

        self.assertTrue(result["success"])
        self.assertEqual(len(self.llm.calls), 2)
        self.assertIn("<ValidationErrors>", self.llm.calls[-1]["prompt"])
        self.assertEqual(orchestrator.conversations["guard-1"]["last_validation"], {"valid": True, "violations": []})

    async def test_conversation_intelligence_answers_previous_question(self):
        orchestrator = self.make_orchestrator()
        await orchestrator.process_conversation(
            user_input="Venue ekkada?",
            client_id="homeo_pills_hospital",
            conversation_id="cil-memory-1",
        )
        result = await orchestrator.process_conversation(
            user_input="Nenu em adiganu?",
            client_id="homeo_pills_hospital",
            conversation_id="cil-memory-1",
        )

        self.assertEqual(result["success"], True)
        self.assertIn("location", result["response"])
        self.assertEqual(len(self.llm.calls), 1)

    async def test_conversation_intelligence_answers_multiple_questions(self):
        orchestrator = self.make_orchestrator()
        result = await orchestrator.process_conversation(
            user_input="Camp enti? Venue ekkada? Doctor untara? Time enti?",
            client_id="homeo_pills_hospital",
            conversation_id="cil-multi-1",
        )

        self.assertEqual(result["success"], True)
        lowered = result["response"].lower()
        self.assertIn("camp", lowered)
        self.assertIn("venue", lowered)
        self.assertIn("doctor", lowered)
        self.assertIn("timing", lowered)
        state = orchestrator.conversations["cil-multi-1"]
        self.assertEqual(state["blackboard"]["questions_pending"], [])

    async def test_conversation_intelligence_remembers_attendance_commitment(self):
        orchestrator = self.make_orchestrator()
        await orchestrator.process_conversation(
            user_input="Vastanu",
            client_id="homeo_pills_hospital",
            conversation_id="cil-commit-1",
        )
        result = await orchestrator.process_conversation(
            user_input="Nenu vastanu ani cheppana?",
            client_id="homeo_pills_hospital",
            conversation_id="cil-commit-1",
        )

        self.assertEqual(result["success"], True)
        self.assertIn("Avunu", result["response"])
        self.assertIn("attend", orchestrator.conversations["cil-commit-1"]["blackboard"]["patient_commitments"])

    async def test_conversation_intelligence_summarizes_conversation(self):
        orchestrator = self.make_orchestrator()
        await orchestrator.process_conversation(
            user_input="Camp enti?",
            client_id="homeo_pills_hospital",
            conversation_id="cil-summary-1",
        )
        await orchestrator.process_conversation(
            user_input="Doctor untara?",
            client_id="homeo_pills_hospital",
            conversation_id="cil-summary-1",
        )
        result = await orchestrator.process_conversation(
            user_input="Mana conversation enti?",
            client_id="homeo_pills_hospital",
            conversation_id="cil-summary-1",
        )

        self.assertEqual(result["success"], True)
        lowered = result["response"].lower()
        self.assertIn("camp", lowered)
        self.assertIn("doctor", lowered)

class BlackboardQuestionTrackerTests(unittest.TestCase):
    def test_pending_questions_are_resolved_one_answer_at_a_time(self):
        manager = BlackboardManager()
        blackboard = manager.new("unit-bb")
        memory = {"conversation_summary": ""}

        manager.before_llm(
            blackboard=blackboard,
            patient_message="Venue ekkada? Time enti? Doctor untara?",
            memory=memory,
            current_state="ACTIVE",
        )
        self.assertEqual(blackboard.questions_pending, ["location", "time", "doctor"])

        manager.after_ai(blackboard, "Venue Kavali hospital daggara andi.", memory)
        self.assertEqual(blackboard.questions_answered, ["location"])
        self.assertEqual(blackboard.questions_pending, ["time", "doctor"])

        manager.after_ai(blackboard, "Time morning 10 AM to 2 PM andi.", memory)
        self.assertEqual(blackboard.questions_answered, ["location", "time"])
        self.assertEqual(blackboard.questions_pending, ["doctor"])

        manager.after_ai(blackboard, "Doctor available untaru andi.", memory)
        self.assertEqual(blackboard.questions_answered, ["location", "time", "doctor"])
        self.assertEqual(blackboard.questions_pending, [])
        self.assertNotEqual(blackboard.current_goal, "Answer pending questions")


if __name__ == "__main__":
    unittest.main()
