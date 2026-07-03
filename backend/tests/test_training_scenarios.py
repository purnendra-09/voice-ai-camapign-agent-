import unittest

from app.services.conversation_analyzer import ConversationAnalyzer
from app.services.local_training_service import LocalTrainingService
from app.services.outcome_service import OutcomeService
from app.services.prompt_manager import PromptManager
from app.conversation_engine.action_repository import get_action_repository


class FakeCampaignService:
    def start_call(self, campaign_id, row_number=None):
        return {"success": False}


class FakeClientManager:
    def get_client_metadata(self, client_id):
        return {
            "name": "Homeo Pills Hospital",
            "prompt_key": "homeo_pills_campaign",
            "language": "Telugu",
        }


class FakeOrchestrator:
    pass


class TrainingScenarioTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.service = LocalTrainingService(
            FakeCampaignService(),
            FakeOrchestrator(),
            PromptManager(),
            FakeClientManager(),
            llm_service=None,
        )
        self.start = await self.service.start_session(
            "Homeo Pills Free Health Camp",
            client_id="homeo_pills_hospital",
        )
        self.session_id = self.start["session_id"]

    async def reply(self, patient_message):
        result = await self.service.send_message(self.session_id, patient_message)
        self.assertIn("last_plan", self.service.sessions[self.session_id])
        return result["assistant_message"]

    async def test_interested_confirmation_closes(self):
        reply = await self.reply("Avunu, vastanu.")
        self.assertIn("July 15", reply)
        self.assertIn("Dhanyavadalu", reply)

    async def test_busy_requests_callback_time(self):
        reply = await self.reply("Ippudu busy unna.")
        self.assertIn("callback", reply.lower())

    async def test_wrong_number_apologizes_and_ends(self):
        reply = await self.reply("Wrong number.")
        self.assertIn("Kshaminchandi", reply)
        self.assertIn("Manchi roju", reply)

    async def test_unknown_location_is_not_hallucinated(self):
        reply = await self.reply("Camp ekkada? Time enti?")
        self.assertIn("clear details levu", reply)
        self.assertNotIn("Amalapuram", reply)

    async def test_planner_outputs_structured_json(self):
        await self.reply("Camp ekkada?")
        plan = self.service.sessions[self.session_id]["last_plan"]
        self.assertEqual(plan["patient_intent"], "ASK_LOCATION")
        self.assertEqual(plan["next_state"], "QUESTION_ANSWERING")
        self.assertEqual(plan["entities"]["business_action"], "ANSWER_LOCATION")
        self.assertIn("venue", plan["forbidden_claims"])
        self.assertIsInstance(plan["required_facts"], dict)

    async def test_response_blueprint_blocks_repetition(self):
        await self.reply("Camp ekkada?")
        blueprint = self.service.sessions[self.session_id]["last_blueprint"]
        self.assertFalse(blueprint["repeat_greeting"])
        self.assertFalse(blueprint["repeat_campaign"])
        self.assertFalse(blueprint["repeat_interest"])
        self.assertEqual(blueprint["answer_questions"], ["location"])
        self.assertLessEqual(blueprint["max_sentences"], 3)

    async def test_family_flow_continues(self):
        reply = await self.reply("Maa amma kosam.")
        self.assertIn("family", reply.lower())
        self.assertIn("Free check-up", reply)

    async def test_trust_question_answered(self):
        reply = await self.reply("Meeru hospital nundi aa?")
        self.assertIn("Homeo Pills Hospital", reply)

    async def test_already_treated_closes_politely(self):
        reply = await self.reply("Already treatment ayindi.")
        self.assertIn("Mee arogyam bagundali", reply)

    async def test_emergency_ends_campaign_flow(self):
        reply = await self.reply("Severe pain undi.")
        self.assertIn("108", reply)


class OutcomeScenarioTests(unittest.TestCase):
    def setUp(self):
        self.analyzer = ConversationAnalyzer(None, OutcomeService())

    def classify(self, patient_line):
        transcript = f"AI Caller: Namaskaram\nPatient: {patient_line}"
        return self.analyzer._rule_based_outcome(transcript)["status"]

    def test_pdf_expected_outcomes(self):
        cases = {
            "Avunu, vastanu.": "Interested",
            "Ippudu busy unna. Repu morning.": "Callback Requested",
            "Wrong number.": "Wrong Number",
            "Interest ledu.": "Not Interested",
            "Already treatment ayindi.": "Already Treated",
            "Severe pain undi.": "Emergency",
        }
        for patient_line, expected in cases.items():
            with self.subTest(patient_line=patient_line):
                self.assertEqual(self.classify(patient_line), expected)


class DatasetActionRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.repository = get_action_repository()

    def test_dataset_loads_expected_rows(self):
        self.assertGreaterEqual(len(self.repository.rows), 13)

    def test_exact_transition_from_dataset(self):
        row = self.repository.find_transition("INTEREST_CHECK", "INTERESTED")
        self.assertIsNotNone(row)
        self.assertEqual(row.action, "ACKNOWLEDGE_INTEREST")
        self.assertEqual(row.next_state, "QUESTION_ANSWERING")

    def test_any_transition_from_dataset(self):
        row = self.repository.find_transition("QUESTION_ANSWERING", "WRONG_NUMBER")
        self.assertIsNotNone(row)
        self.assertEqual(row.action, "END_WRONG_NUMBER")
        self.assertEqual(row.next_state, "FINISHED")


if __name__ == "__main__":
    unittest.main()
