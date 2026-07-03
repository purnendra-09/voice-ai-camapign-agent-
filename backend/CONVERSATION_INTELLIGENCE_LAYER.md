# Conversation Intelligence Layer

The Conversation Intelligence Layer (CIL) adds conversation awareness without replacing the existing Dialogue Policy Engine, Blackboard, Cognitive Engine, or provider adapters.

## Modules

- `memory_query_engine.py`: detects conversation-aware questions such as "Nenu em adiganu?", "What did you tell me?", and "Did I say I will attend?", then answers from blackboard state.
- `conversation_summarizer.py`: builds a live structured summary from greeting/campaign flags, answered questions, pending questions, and commitments.
- `question_decomposer.py`: extracts every normal campaign question from a single patient turn so multi-question inputs do not lose items.
- `answer_assembler.py`: orders decomposed answers and merges them into one natural Telugu-English response.
- `conversation_reflection.py`: creates natural summaries of what the patient asked, what was answered, what is pending, and what the patient committed to.

## Runtime Flow

1. Blackboard receives the patient message before the LLM.
2. CIL checks for a memory/reflection query.
3. If found, the planner returns a direct `MEMORY_QUERY_ENGINE` response and the LLM is skipped.
4. If multiple campaign questions are found, CIL decomposes and assembles a direct `QUESTION_DECOMPOSER` response.
5. Otherwise the existing dialogue flow continues normally.

The LLM remains responsible only for natural wording on ordinary turns. Conversation-memory answers come from tracked state.

## Guarantees

- Conversation reflection questions are not sent to normal dialogue flow.
- Multi-question turns preserve all detected questions.
- Attendance commitments are stored in blackboard and memory.
- Validators reject ignored conversation questions and incorrect commitment summaries.
- Existing APIs remain unchanged.
