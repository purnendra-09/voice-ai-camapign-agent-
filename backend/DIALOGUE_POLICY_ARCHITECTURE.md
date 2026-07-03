# Dialogue Policy Engine Architecture

## Purpose

The Dialogue Policy Engine is the backend decision maker for local training conversations. It replaces rigid state-machine-first decisions with a policy-first flow:

Patient message -> intent detection -> entity extraction -> question manager -> response plan -> policy validation -> existing `PolicyPlan` contract -> response blueprint/language layer.

The state machine is now a tracker of the selected policy outcome. The LLM or language generator is only responsible for wording.

## Modules

### `app/conversation_engine/dialogue_policy/policy_engine.py`

Coordinates the full policy decision. It reads the latest patient message, detects intent/entities, tracks questions, applies priority rules, produces one active goal, logs debug details, and returns the existing `PolicyPlan` object for backward compatibility.

### `app/conversation_engine/dialogue_policy/question_manager.py`

Extracts every patient question and maintains asked, answered, pending, and skipped question state on the session. It also provides memory answers for patient-name, attendance confirmation, and conversation-summary questions.

### `app/conversation_engine/dialogue_policy/policy_rules.py`

Centralizes policy mappings: priority classes, question-to-intent mapping, question-to-action mapping, knowledge files needed, and avoid rules. This keeps policy data out of scattered handler code.

### `app/conversation_engine/dialogue_policy/response_plan.py`

Defines `ResponsePlan`, the internal structured plan produced before any reply. It contains the current goal, action, next state, pending questions, knowledge needed, rules, tone, tool need, and deterministic fallback text.

### `app/conversation_engine/dialogue_policy/planner.py`

Converts `ResponsePlan` into the existing `PolicyPlan` schema so the rest of the application does not need API changes.

### `app/conversation_engine/dialogue_policy/response_validator.py`

Validates policy plans before response generation. It prevents asking new questions while pending questions remain and blocks repeat greeting/campaign/interest behavior.

### `app/services/dialogue_policy_engine.py`

Compatibility wrapper. Existing callers still import `DialoguePolicyEngine` from `app.services`, but the implementation is now the new policy engine under `app/conversation_engine/dialogue_policy`.

### `app/services/intent_detector.py`

Expanded closed-set intent coverage for identity, purpose, memory, summary, unexpected/off-topic questions, direct interest, simple refusal, and wrong-call phrasing.

## Policy Priorities

1. Emergency and wrong number.
2. Answer pending patient questions.
3. Clarify confusion or memory questions.
4. Explain campaign.
5. Qualification and interest.
6. Closing or callback.

The policy engine never asks a new qualification question while pending patient questions remain.

## QA Impact

The automated 100-scenario QA simulator improved from:

- Score: `8.20` to `8.88`
- Failed scenarios: `51` to `8`
- Ignored question failures: eliminated in the latest run
- Repeated greeting failures: eliminated in the latest run

Remaining failures are mostly conservative QA heuristics around long-conversation memory/state classification.
