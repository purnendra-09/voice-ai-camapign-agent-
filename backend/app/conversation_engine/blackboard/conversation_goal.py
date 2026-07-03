from typing import List

from app.conversation_engine.blackboard.blackboard_models import BlackboardPlan, ConversationBlackboard


class ConversationGoalEngine:
    """Chooses the single next objective from blackboard state."""

    def plan(self, blackboard: ConversationBlackboard) -> BlackboardPlan:
        avoid: List[str] = []
        if blackboard.greeting_done:
            avoid.append("repeat_greeting")
        if blackboard.campaign_explained:
            avoid.append("repeat_campaign")
        if blackboard.interest_confirmed:
            avoid.append("repeat_interest")

        if blackboard.questions_pending:
            goal = "Answer pending questions"
            decision = "Answer pending patient questions before any new pitch or follow-up."
            return BlackboardPlan(
                current_goal=goal,
                planner_decision=decision,
                response_goals=[goal],
                must_answer_questions=list(blackboard.questions_pending),
                avoid=avoid,
            )

        if blackboard.callback_requested:
            goal = "Collect callback time"
        elif blackboard.appointment_requested:
            goal = "Collect appointment details"
        elif not blackboard.campaign_explained:
            goal = "Introduce campaign"
        elif not blackboard.interest_confirmed:
            goal = "Confirm interest"
        else:
            goal = "Confirm attendance or close conversation"

        return BlackboardPlan(
            current_goal=goal,
            planner_decision=f"Proceed with the next single objective: {goal}.",
            response_goals=[goal],
            must_answer_questions=[],
            avoid=avoid,
        )
