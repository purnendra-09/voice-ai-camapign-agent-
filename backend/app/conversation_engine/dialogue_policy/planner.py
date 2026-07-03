from typing import Any, Dict

from app.conversation_engine.dialogue_policy.response_plan import ResponsePlan
from app.services.planner_models import PolicyPlan


class DialoguePlanner:
    """Converts the policy response plan into the existing PolicyPlan contract."""

    def to_policy_plan(self, plan: ResponsePlan) -> PolicyPlan:
        return PolicyPlan(
            current_state=plan.current_state,
            patient_intent=plan.detected_intent,
            emotion=plan.emotion,
            confidence=plan.confidence,
            goal=plan.goal,
            questions_to_answer=plan.questions_to_answer,
            questions_to_ask=plan.questions_to_ask,
            avoid=plan.avoid,
            next_state=plan.next_state,
            close_conversation=plan.close_conversation,
            requires_tool=bool(plan.tool_needed),
            tool=plan.tool_needed,
            entities={
                **plan.entities,
                "business_action": plan.action,
                "response_plan": plan.to_dict(),
            },
            memory_updates=plan.memory_updates,
            required_facts=plan.required_facts,
            forbidden_claims=plan.forbidden_claims,
            deterministic_response=plan.deterministic_response,
            outcome_hint=plan.outcome_hint,
        )

    def build_prompt_payload(self, plan: ResponsePlan, blackboard: Dict[str, Any], knowledge_context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "blackboard": blackboard,
            "knowledge_context": knowledge_context,
            "response_goal": plan.response_goal,
            "knowledge_needed": plan.knowledge_needed,
            "tool_needed": plan.tool_needed,
            "expected_tone": plan.expected_tone,
            "rules": plan.rules,
        }
