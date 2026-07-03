from typing import Any, Dict

from app.conversation_engine.brain.confidence_engine import ConfidenceEngine
from app.conversation_engine.brain.conversation_strategy import ConversationStrategy
from app.conversation_engine.brain.emotion_engine import EmotionEngine
from app.conversation_engine.brain.planner import CognitivePlanner
from app.conversation_engine.brain.reasoning_engine import ReasoningEngine
from app.conversation_engine.brain.response_critic import ResponseCritic
from app.utils import get_logger


logger = get_logger(__name__)


class CognitiveConversationEngine:
    """Internal think/reason/plan/evaluate/generate/self-review layer."""

    def __init__(self):
        self.reasoning = ReasoningEngine()
        self.emotion = EmotionEngine()
        self.confidence = ConfidenceEngine()
        self.planner = CognitivePlanner()
        self.strategy = ConversationStrategy()
        self.critic = ResponseCritic()

    def think(self, session: Dict[str, Any], policy_plan: Dict[str, Any]) -> Dict[str, Any]:
        understanding = self.reasoning.understand(session, policy_plan)
        reasoning = self.reasoning.reason(understanding, policy_plan)
        emotion = self.emotion.detect(
            understanding.get("patient_said", ""),
            policy_plan.get("patient_intent", "UNKNOWN"),
        )
        confidence = self.confidence.score(policy_plan, understanding)
        cognitive_plan = self.planner.plan(policy_plan, understanding, emotion, confidence)
        strategy = self.strategy.build(session, policy_plan)
        return {
            "understanding": understanding,
            "reasoning": reasoning,
            "emotion": emotion,
            "confidence": confidence,
            "plan": cognitive_plan,
            "strategy": strategy,
        }

    def finalize_response(
        self,
        candidate: str,
        session: Dict[str, Any],
        policy_plan: Dict[str, Any],
        thought: Dict[str, Any],
    ) -> tuple[str, Dict[str, Any]]:
        natural = self.critic.naturalize(candidate)
        review = self.critic.review(natural, session, policy_plan, thought["confidence"])
        final = self.critic.revise(natural, review, policy_plan, thought["confidence"])
        second_review = self.critic.review(final, session, policy_plan, thought["confidence"])
        trace = {
            **thought,
            "critic_result": second_review,
            "initial_response": candidate,
            "final_response": final,
        }
        logger.info(
            "Cognitive conversation turn",
            extra={
                "extra_data": {
                    "intent": policy_plan.get("patient_intent"),
                    "emotion": thought["emotion"],
                    "reasoning": thought["reasoning"],
                    "plan": thought["plan"],
                    "knowledge_used": thought["plan"].get("knowledge_files"),
                    "confidence": thought["confidence"],
                    "critic_result": second_review,
                    "final_response": final,
                }
            },
        )
        return final, trace
