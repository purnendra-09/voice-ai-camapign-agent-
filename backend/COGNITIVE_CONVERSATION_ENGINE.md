# Cognitive Conversation Engine

## Purpose

The Cognitive Conversation Engine adds an internal think/reason/plan/evaluate/self-review layer before any response is returned to the patient.

The Dialogue Policy Engine still decides the business action. The Cognitive Conversation Engine decides whether the planned response sounds human, safe, confident, and complete enough to send.

## Flow

Patient message -> intent/entity/policy/blackboard -> cognitive understanding -> reasoning -> cognitive plan -> emotion controls -> confidence estimate -> response critic -> naturalized final reply.

For live LLM calls, the LLM output is treated as a candidate response. It is passed through the cognitive critic before the existing business validator and before it reaches the caller.

## Modules

### `app/conversation_engine/brain/cognitive_engine.py`

Coordinates the full brain pass. It produces the cognitive trace and logs intent, emotion, reasoning, plan, knowledge used, confidence, critic result, and final response.

### `reasoning_engine.py`

Builds a compact understanding of the turn:

- what the patient said
- what they are asking
- known information
- missing information
- pending and answered questions

### `emotion_engine.py`

Detects patient emotion such as happy, confused, busy, angry/irritated, fear, curious, or neutral. It returns tone, speed, sentence length, and empathy controls.

### `planner.py`

Turns the policy plan, understanding, emotion, and confidence into a cognitive response plan with response goal, information needed, knowledge files, tone, length, and follow-up.

### `conversation_strategy.py`

Tracks current goal, next goal, conversation progress, and completion percentage.

### `response_critic.py`

Reviews the candidate response for:

- ignored pending questions
- repetition or loop
- repeated greeting
- too-long wording
- low confidence without disclosure
- robotic phrasing

It also naturalizes common robotic sentences into warmer Telugu-English.

### `confidence_engine.py`

Scores answer confidence as High, Medium, or Low. If a requested fact is not confirmed, confidence is reduced and the critic forces non-hallucinating wording.

## Integration Points

### Local Training

`LocalTrainingService._generate_reply()` now:

1. Builds the policy plan.
2. Builds a response blueprint.
3. Runs cognitive `think()`.
4. Generates or selects candidate text.
5. Runs cognitive self-review.
6. Stores `last_cognitive_trace`.
7. Returns the final response.

### Live Conversation Orchestrator

`ConversationRuntime.cognitive_review_response()` reviews live LLM output before business validation and response persistence.

## Backward Compatibility

Existing API payloads remain unchanged. Reports now include `last_cognitive_trace` for local training sessions, but no existing fields were removed.
