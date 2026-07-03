import json
import re
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from app.utils import get_logger
from app.services.base_llm_service import BaseLLMService
from app.services.prompt_manager import PromptManager
from app.services.client_manager import ClientManager
from app.services.booking_service import BookingService
from app.services.doctor_service import DoctorService
from app.services.conversation_runtime import ConversationRuntime
from app.knowledge import KnowledgeContextBuilder

logger = get_logger(__name__)


class ConversationOrchestrator:
    """Orchestrates multi-turn conversations with AI and tool calling"""

    def __init__(
        self,
        groq_service: BaseLLMService,
        prompt_manager: PromptManager,
        client_manager: ClientManager,
        booking_service: BookingService,
        doctor_service: DoctorService,
        knowledge_context_builder: Optional[KnowledgeContextBuilder] = None,
    ):
        """
        Initialize Conversation Orchestrator

        Args:
            groq_service: Groq API service
            prompt_manager: Prompt manager
            client_manager: Client manager
            booking_service: Booking service
            doctor_service: Doctor service
        """
        self.ai = groq_service
        self.prompts = prompt_manager
        self.clients = client_manager
        self.booking = booking_service
        self.doctors = doctor_service
        self.conversations = {}  # Store conversation history
        self.max_history_messages = 8
        self.max_tool_repeats = 1
        self.knowledge_context_builder = knowledge_context_builder
        self.runtime = ConversationRuntime(knowledge_context_builder=knowledge_context_builder)

    def define_tools(self) -> List[Dict[str, Any]]:
        """
        Define available tools for function calling

        Returns:
            List of tool definitions
        """
        tools = [
            {
                "name": "check_doctor_availability",
                "description": "Check if a doctor is available and get their schedule",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "doctor_name": {
                            "type": "string",
                            "description": "Name of the doctor to check",
                        },
                    },
                    "required": ["doctor_name"],
                },
            },
            {
                "name": "book_appointment",
                "description": "Book an appointment for a patient with a doctor",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "patient_name": {
                            "type": "string",
                            "description": "Full name of the patient",
                        },
                        "phone": {
                            "type": "string",
                            "description": "Patient's 10-digit phone number",
                        },
                        "doctor_name": {
                            "type": "string",
                            "description": "Name of the doctor",
                        },
                        "date": {
                            "type": "string",
                            "description": "Appointment date (YYYY-MM-DD format)",
                        },
                        "time": {
                            "type": "string",
                            "description": "Appointment time",
                        },
                    },
                    "required": ["patient_name", "phone", "doctor_name", "date", "time"],
                },
            },
            {
                "name": "get_all_doctors",
                "description": "Get a list of all available doctors",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "knowledge_lookup",
                "description": "Look up source-of-truth hospital, campaign, location, timing, service, and contact details before answering factual questions",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The factual question to answer from hospital/campaign context",
                        },
                    },
                    "required": ["query"],
                },
            },
        ]
        return tools

    async def execute_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        client_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a tool/function call

        Args:
            tool_name: Name of the tool
            tool_args: Arguments for the tool

        Returns:
            Tool result
        """
        try:
            if tool_name == "check_doctor_availability":
                result = self.doctors.check_availability(tool_args.get("doctor_name"))
                return result

            elif tool_name == "book_appointment":
                required_fields = ["patient_name", "phone", "doctor_name", "date", "time"]
                missing_fields = [
                    field for field in required_fields if not tool_args.get(field)
                ]
                if missing_fields:
                    logger.info(
                        "Booking tool skipped because required fields are missing",
                        extra={
                            "extra_data": {
                                "event": "booking_tool_missing_fields",
                                "missing_fields": missing_fields,
                            }
                        },
                    )
                    return {
                        "status": "needs_more_info",
                        "missing_fields": missing_fields,
                        "message": "Need complete appointment details before booking",
                    }
                result = self.booking.book_appointment(
                    patient_name=tool_args.get("patient_name"),
                    phone=tool_args.get("phone"),
                    doctor_name=tool_args.get("doctor_name"),
                    date=tool_args.get("date"),
                    time=tool_args.get("time"),
                )
                return result

            elif tool_name == "get_all_doctors":
                doctors = self.doctors.get_all_doctors()
                return {"doctors": doctors, "count": len(doctors)}

            elif tool_name == "knowledge_lookup":
                metadata = self.clients.get_client_metadata(client_id) if client_id else {}
                query = tool_args.get("query") or ""
                knowledge = None
                if self.knowledge_context_builder:
                    memory = {"conversation_summary": "", "questions_answered": [], "questions_pending": []}
                    selection = self.knowledge_context_builder.build(
                        patient_message=query,
                        memory=memory,
                        conversation_state="TOOL_LOOKUP",
                        detected_intent="knowledge_lookup",
                        current_goal="Answer factual hospital or campaign question",
                    )
                    knowledge = {
                        "selected_files": selection.selected_files,
                        "content": selection.prompt_section,
                    }
                return {
                    "query": query,
                    "hospital_context": metadata or {},
                    "knowledge": knowledge,
                    "source": "client_metadata",
                }

            else:
                logger.warning(f"Unknown tool: {tool_name}")
                return {"error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            error_msg = f"Error executing tool {tool_name}: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    async def process_conversation(
        self,
        user_input: str,
        client_id: str,
        conversation_id: Optional[str] = None,
        max_iterations: int = 3,
    ) -> Dict[str, Any]:
        """
        Process a user input and manage multi-turn conversation

        Args:
            user_input: User's input message
            client_id: Client/hospital identifier
            conversation_id: Optional conversation ID for continuity
            max_iterations: Maximum tool calling iterations

        Returns:
            Structured response
        """
        try:
            started_at = time.perf_counter()
            if not self.clients.client_exists(client_id):
                logger.warning(f"Client not found: {client_id}")
                return {
                    "success": False,
                    "error": "Client not found",
                }

            logger.info(f"Received conversation_id: {conversation_id}")
            if not conversation_id:
                conversation_id = self._generate_conversation_id()

            conv_state = self.conversations.get(conversation_id)
            if not conv_state:
                logger.info(f"Initialized new conversation state for ID: {conversation_id}")
                conv_state = self.runtime.create_session(conversation_id, client_id)
                self.conversations[conversation_id] = conv_state
            else:
                logger.info(f"Resuming existing conversation session ID: {conversation_id}")

            conv_state = self.runtime.hydrate_session(conv_state, conversation_id, client_id)
            self.conversations[conversation_id] = conv_state
            logger.info(f"Active sessions count: {len(self.conversations)}")

            client_data = self.clients.get_client(client_id)
            client_context = self.clients.get_client_metadata(client_id) or {}
            client_context["name"] = client_context.get("name") or client_data.get("name")
            tools = self.define_tools()
            ai_context = self.runtime.build_ai_context(
                conversation_id=conversation_id,
                session=conv_state,
                hospital_context=client_context,
                campaign_context=self.runtime.campaign_context(client_context),
                business_rules=self.runtime.business_rules(),
                allowed_tools=tools,
                current_patient_message=user_input,
            )
            self.runtime.persist_user_turn(conv_state, user_input)

            if ai_context.blackboard_plan.direct_response:
                final_response_text = ai_context.blackboard_plan.direct_response
                validation = self.runtime.validate_response(final_response_text, ai_context, [])
                if not validation["valid"]:
                    return {
                        "success": False,
                        "error": f"Response failed business guard: {validation['violations']}",
                        "conversation_id": conversation_id,
                    }
                logger.info(
                    "Conversation Intelligence Layer direct response",
                    extra={
                        "extra_data": {
                            "conversation_id": conversation_id,
                            "planner_route": ai_context.blackboard_plan.route,
                            "reflection_output": ai_context.blackboard.reflection_output,
                            "questions_asked": ai_context.blackboard.questions_asked,
                            "questions_answered": ai_context.blackboard.questions_answered,
                            "questions_pending": ai_context.blackboard.questions_pending,
                            "commitments": ai_context.blackboard.patient_commitments,
                            "conversation_summary": ai_context.blackboard.conversation_summary,
                        }
                    },
                )
                self.runtime.persist_assistant_turn(
                    session=conv_state,
                    response_text=final_response_text,
                    validation=validation,
                    tool_results=[],
                )
                self._log_after_response(conversation_id, conv_state, saved=True)
                latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
                logger.info(
                    "Conversation processed",
                    extra={
                        "extra_data": {
                            "event": "conversation_processed",
                            "conversation_id": conversation_id,
                            "client_id": client_id,
                            "latency_ms": latency_ms,
                            "tool_calls_executed": 0,
                            "tools_used": [],
                            "response_length": len(final_response_text),
                            "planner_route": ai_context.blackboard_plan.route,
                        }
                    },
                )
                return {
                    "success": True,
                    "response": final_response_text,
                    "conversation_id": conversation_id,
                    "client_id": client_id,
                    "tool_calls_executed": 0,
                    "tools_used": [],
                }

            logger.info(
                "AI conversation before LLM",
                extra={
                    "extra_data": {
                        "conversation_id": conversation_id,
                        "current_state": ai_context.current_state,
                        "memory_before": ai_context.memory_before,
                        "history_count": len(ai_context.conversation_history),
                        "tool_names": [tool.get("name") for tool in tools],
                    }
                },
            )
            groq_response = await self.ai.generate_content(
                prompt=ai_context.user_prompt,
                system_prompt=ai_context.system_prompt,
                temperature=0.45,
                max_tokens=260,
                tools=tools,
            )
            logger.info(f"[DEBUG] AI raw LLM response: {groq_response}")

            if not groq_response.get("success"):
                logger.error(f"Groq API failed: {groq_response.get('error')}")
                return {
                    "success": False,
                    "error": "Failed to generate response",
                    "conversation_id": conversation_id,
                }

            final_response_text = self.runtime.clean_response_text(
                await self.ai.extract_response_text(groq_response)
            )
            tool_calls = await self.ai.extract_tool_calls(groq_response)
            tool_calls = self._dedupe_tool_calls(tool_calls, conv_state)
            executed_tool_results = []

            for iteration in range(max_iterations):
                if not tool_calls:
                    break
                logger.info(
                    "Executing LLM-selected tools",
                    extra={
                        "extra_data": {
                            "conversation_id": conversation_id,
                            "iteration": iteration + 1,
                            "tool_count": len(tool_calls),
                        }
                    },
                )
                tool_results = []
                for tool_call in tool_calls:
                    tool_name = tool_call.get("name")
                    tool_args = tool_call.get("args") or tool_call.get("arguments") or {}
                    result = await self.execute_tool(tool_name, tool_args, client_id=client_id)
                    tool_result = {"tool": tool_name, "args": tool_args, "result": result}
                    tool_results.append(tool_result)
                    executed_tool_results.append(tool_result)

                self.runtime.persist_tool_results(conv_state, executed_tool_results)
                follow_up_prompt = (
                    f"{ai_context.user_prompt}\n"
                    f"{self.runtime.xml_section('ToolResults', self.runtime.to_json(tool_results))}\n"
                    "<Task>Use the tool result and continue the conversation naturally. Do not call tools again unless essential.</Task>"
                )
                follow_up_response = await self.ai.generate_content(
                    prompt=follow_up_prompt,
                    system_prompt=ai_context.system_prompt,
                    temperature=0.4,
                    max_tokens=260,
                    tools=None,
                )
                if not follow_up_response.get("success"):
                    break
                final_response_text = self.runtime.clean_response_text(
                    await self.ai.extract_response_text(follow_up_response)
                )
                tool_calls = []

            final_response_text = self.runtime.cognitive_review_response(
                response_text=final_response_text,
                session=conv_state,
                context=ai_context,
            )
            validation = self.runtime.validate_response(final_response_text, ai_context, executed_tool_results)
            if not validation["valid"]:
                logger.warning(
                    "Business guard rejected LLM response",
                    extra={
                        "extra_data": {
                            "conversation_id": conversation_id,
                            "violations": validation["violations"],
                        }
                    },
                )
                retry_response = await self.ai.generate_content(
                    prompt=self.runtime.build_regeneration_prompt(
                        user_input,
                        validation,
                        tool_results=executed_tool_results,
                    ),
                    system_prompt=ai_context.system_prompt,
                    temperature=0.35,
                    max_tokens=220,
                    tools=None,
                )
                if retry_response.get("success"):
                    retry_text = self.runtime.clean_response_text(
                        await self.ai.extract_response_text(retry_response)
                    )
                    retry_validation = self.runtime.validate_response(retry_text, ai_context, executed_tool_results)
                    if retry_validation["valid"]:
                        final_response_text = retry_text
                        validation = retry_validation

            if not validation["valid"]:
                return {
                    "success": False,
                    "error": f"Response failed business guard: {validation['violations']}",
                    "conversation_id": conversation_id,
                }

            logger.info(f"[DEBUG] Final response_text value: {final_response_text}")
            self.runtime.persist_assistant_turn(
                session=conv_state,
                response_text=final_response_text,
                validation=validation,
                tool_results=executed_tool_results,
            )
            self._log_after_response(conversation_id, conv_state, saved=True)

            final_response = {
                "success": True,
                "response": final_response_text,
                "conversation_id": conversation_id,
                "client_id": client_id,
                "tool_calls_executed": len(executed_tool_results),
                "tools_used": [result["tool"] for result in executed_tool_results],
            }
            latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.info(
                "Conversation processed",
                extra={
                    "extra_data": {
                        "event": "conversation_processed",
                        "conversation_id": conversation_id,
                        "client_id": client_id,
                        "latency_ms": latency_ms,
                        "tool_calls_executed": len(executed_tool_results),
                        "tools_used": [result["tool"] for result in executed_tool_results],
                        "response_length": len(final_response_text),
                    }
                },
            )
            logger.info(f"[DEBUG] Final return payload: {final_response}")
            return final_response

        except Exception as e:
            error_msg = f"Error processing conversation: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
            }

    def get_conversation_history(self, conversation_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get conversation history

        Args:
            conversation_id: Conversation identifier

        Returns:
            Conversation messages or None
        """
        conversation = self.conversations.get(conversation_id)
        if not conversation:
            return None
        return conversation.get("messages", [])

    def _new_memory_state(self) -> Dict[str, Any]:
        return {
            "patient_name": None,
            "phone": None,
            "doctor_name": None,
            "appointment_date": None,
            "appointment_time": None,
            "specialty": None,
            "availability_checked": False,
            "booking_confirmed": False,
            "current_state": "GREETING",
            "previous_state": None,
            "conversation_stage": "GREETING",
            "greeting_done": False,
            "campaign_explained": False,
            "interest_confirmed": False,
            "attendance_confirmed": False,
            "callback_requested": False,
            "questions_answered": [],
            "questions_pending": [],
            "last_action": None,
            "conversation_goal": None,
        }

    def _merge_memory_defaults(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        defaults = self._new_memory_state()
        defaults.update(memory or {})
        defaults["questions_answered"] = list(defaults.get("questions_answered") or [])
        defaults["questions_pending"] = list(defaults.get("questions_pending") or [])
        return defaults

    def _new_conversation_cursor(self, conversation_id: str) -> Dict[str, Any]:
        return {
            "conversation_id": conversation_id,
            "current_node": "GREETING",
            "completed_nodes": [],
            "last_action": None,
            "current_state": "GREETING",
        }

    def _detect_lifecycle_intent(self, user_input: str) -> str:
        text = user_input.lower()
        if any(token in text for token in ["wrong number", "tappu number"]):
            return "WRONG_NUMBER"
        if any(token in text for token in ["emergency", "urgent", "severe pain", "chala pain"]):
            return "EMERGENCY"
        if any(token in text for token in ["busy", "later", "repu", "callback"]):
            return "CALLBACK"
        if any(token in text for token in ["not interested", "interest ledu", "interest ledhu", "vaddu"]):
            return "NOT_INTERESTED"
        if any(token in text for token in ["vastanu", "vasthanu", "ostanu", "i will come"]):
            return "CONFIRM_ATTENDANCE"
        if any(token in text for token in ["where", "venue", "location", "ekkada"]):
            return "ASK_LOCATION"
        if any(token in text for token in ["time", "timing", "eppudu"]):
            return "ASK_TIME"
        if any(token in text for token in ["yes", "avunu", "interested", "interest undi"]):
            return "INTERESTED"
        if any(token in text for token in ["hi", "hello", "namaskaram"]):
            return "GREETING"
        return "UNKNOWN"

    def _next_lifecycle_state(self, current_state: str, intent: str, memory: Dict[str, Any]) -> str:
        if intent in {"WRONG_NUMBER", "EMERGENCY", "NOT_INTERESTED"}:
            return "FINISHED"
        if intent == "CALLBACK":
            return "CALLBACK"
        if intent == "CONFIRM_ATTENDANCE":
            return "CLOSING"
        if intent in {"ASK_LOCATION", "ASK_TIME"}:
            return "QUESTION_ANSWERING"
        if intent == "INTERESTED":
            return "QUESTION_ANSWERING"
        if current_state == "GREETING":
            return "CAMPAIGN_INTRODUCTION"
        if current_state == "CAMPAIGN_INTRODUCTION":
            return "INTEREST_CHECK"
        return current_state or "GREETING"

    def _apply_lifecycle_state(
        self,
        conversation_id: str,
        conv_state: Dict[str, Any],
        previous_state: str,
        next_state: str,
        intent: str,
    ) -> None:
        memory = conv_state["memory"]
        cursor = conv_state["conversation_cursor"]
        self._warn_if_regression(conversation_id, previous_state, next_state, memory)

        memory["previous_state"] = previous_state
        memory["current_state"] = next_state
        memory["conversation_stage"] = next_state
        memory["last_action"] = intent
        memory["conversation_goal"] = self._goal_for_intent(intent)
        if previous_state and previous_state not in cursor["completed_nodes"]:
            cursor["completed_nodes"].append(previous_state)
        cursor["current_node"] = next_state
        cursor["current_state"] = next_state
        cursor["last_action"] = intent

        if intent == "GREETING" and memory.get("greeting_done"):
            logger.warning("Greeting repeated", extra={"extra_data": {"conversation_id": conversation_id}})
        if intent in {"INTERESTED", "CONFIRM_ATTENDANCE"} and memory.get("interest_confirmed"):
            logger.warning("Interest repeated", extra={"extra_data": {"conversation_id": conversation_id}})
        if next_state == "CAMPAIGN_INTRODUCTION" and memory.get("campaign_explained"):
            logger.warning("Campaign introduction repeated", extra={"extra_data": {"conversation_id": conversation_id}})

        if next_state != "GREETING":
            memory["greeting_done"] = True
        if intent == "CALLBACK":
            memory["callback_requested"] = True
        if intent == "INTERESTED":
            memory["interest_confirmed"] = True
        if intent == "CONFIRM_ATTENDANCE":
            memory["attendance_confirmed"] = True
            memory["interest_confirmed"] = True
        if next_state in {"INTEREST_CHECK", "QUESTION_ANSWERING", "CLOSING", "FINISHED"}:
            memory["campaign_explained"] = True
        if intent in {"ASK_LOCATION", "ASK_TIME"}:
            question = "location" if intent == "ASK_LOCATION" else "time"
            if question not in memory["questions_answered"]:
                memory["questions_answered"].append(question)

    def _goal_for_intent(self, intent: str) -> str:
        return {
            "ASK_LOCATION": "Answer location question without repeating campaign.",
            "ASK_TIME": "Answer timing question without guessing.",
            "INTERESTED": "Acknowledge interest and continue.",
            "CONFIRM_ATTENDANCE": "Confirm attendance and close.",
            "CALLBACK": "Offer callback.",
            "WRONG_NUMBER": "Apologize and end.",
            "EMERGENCY": "Advise emergency care and end.",
        }.get(intent, "Continue conversation without repeating completed steps.")

    def _warn_if_regression(
        self,
        conversation_id: str,
        previous_state: str,
        next_state: str,
        memory: Dict[str, Any],
    ) -> None:
        order = {
            "GREETING": 0,
            "CAMPAIGN_INTRODUCTION": 1,
            "INTEREST_CHECK": 2,
            "QUESTION_ANSWERING": 3,
            "CONFIRMATION": 4,
            "CLOSING": 5,
            "FINISHED": 6,
            "CALLBACK": 6,
        }
        if order.get(next_state, 0) < order.get(previous_state, 0):
            logger.error(
                "Conversation state regression detected",
                extra={
                    "extra_data": {
                        "conversation_id": conversation_id,
                        "previous_state": previous_state,
                        "next_state": next_state,
                        "memory": memory,
                    }
                },
            )

    def _log_before_llm(
        self,
        conversation_id: str,
        conv_state: Dict[str, Any],
        patient_intent: str,
        planner_action: str,
        goal: str,
    ) -> None:
        memory = conv_state["memory"]
        logger.info(
            "Conversation lifecycle before LLM",
            extra={
                "extra_data": {
                    "conversation_id": conversation_id,
                    "current_state": memory.get("current_state"),
                    "previous_state": memory.get("previous_state"),
                    "patient_intent": patient_intent,
                    "planner_action": planner_action,
                    "conversation_goal": goal,
                    "memory": memory,
                    "questions_answered": memory.get("questions_answered"),
                    "questions_pending": memory.get("questions_pending"),
                    "interest": memory.get("interest_confirmed"),
                    "attendance": memory.get("attendance_confirmed"),
                    "current_cursor": conv_state.get("conversation_cursor"),
                    "next_state": memory.get("current_state"),
                }
            },
        )

    def _log_after_response(self, conversation_id: str, conv_state: Dict[str, Any], saved: bool) -> None:
        logger.info(
            "Conversation lifecycle after response",
            extra={
                "extra_data": {
                    "conversation_id": conversation_id,
                    "updated_state": conv_state["memory"].get("current_state"),
                    "updated_memory": conv_state["memory"],
                    "conversation_saved": saved,
                    "cursor": conv_state.get("conversation_cursor"),
                }
            },
        )

    async def _synthesize_final_response(
        self,
        user_input: str,
        system_prompt: str,
        memory: Dict[str, Any],
        tool_results: List[Dict[str, Any]],
        conversation_id: str,
    ) -> Optional[str]:
        tool_context = self._format_tool_results(tool_results)
        prompt = (
            f"{self._build_memory_context(memory)}"
            f"Caller said: {user_input}\n\n"
            f"{tool_context}\n\n"
            "Now give the caller the next spoken reply. "
            "Use only the tool results. Do not call tools. "
            "Do not output JSON. Do not leave content blank. "
            "Keep it to 1 or 2 short Telugu-English sentences. "
            "If booking details are missing, ask for exactly one missing detail."
        )
        response = await self.ai.generate_content(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.25,
            max_tokens=140,
            tools=None,
        )
        logger.info(f"[DEBUG] Final LLM raw response after tools: {response}")
        self._log_response_content(response, "post_tool_synthesis")

        if response.get("success"):
            text = await self.ai.extract_response_text(response)
            logger.info(f"[DEBUG] Final assistant message variable: {text}")
            if text:
                return text
        else:
            logger.error(
                "Final response synthesis failed",
                extra={
                    "extra_data": {
                        "event": "final_synthesis_failed",
                        "conversation_id": conversation_id,
                        "error": response.get("error"),
                    }
                },
            )

        retry_prompt = (
            f"{tool_context}\n\n"
            "The previous assistant message was empty. "
            "Write one short natural phone reply now. "
            "Example style: Okay andi, appointment booking continue chesthunnanu. "
            "Konchem details confirm cheyyandi."
        )
        retry_response = await self.ai.generate_content(
            prompt=retry_prompt,
            system_prompt=system_prompt,
            temperature=0.2,
            max_tokens=100,
            tools=None,
        )
        logger.info(f"[DEBUG] Retry final LLM raw response: {retry_response}")
        self._log_response_content(retry_response, "post_tool_synthesis_retry")
        if retry_response.get("success"):
            retry_text = await self.ai.extract_response_text(retry_response)
            logger.info(f"[DEBUG] Retry assistant message variable: {retry_text}")
            if retry_text:
                return retry_text
        return None

    def _format_tool_results(self, tool_results: List[Dict[str, Any]]) -> str:
        compact_results = []
        for tool_result in tool_results:
            compact_results.append({
                "tool": tool_result.get("tool"),
                "args": tool_result.get("args", {}),
                "result": tool_result.get("result", {}),
            })
        return "Tool results:\n" + json.dumps(compact_results, ensure_ascii=True)

    def _log_response_content(self, response: Dict[str, Any], stage: str):
        data = response.get("data", {}) if response.get("success") else {}
        choices = data.get("choices", [])
        message = choices[0].get("message", {}) if choices else {}
        content = message.get("content")
        logger.info(
            "[DEBUG] LLM response.content inspection",
            extra={
                "extra_data": {
                    "stage": stage,
                    "has_choices": bool(choices),
                    "response_content": content,
                    "has_tool_calls": bool(message.get("tool_calls")),
                    "finish_reason": choices[0].get("finish_reason") if choices else None,
                }
            },
        )

    def _fallback_response(
        self,
        memory: Dict[str, Any],
        executed_tool_results: List[Dict[str, Any]],
    ) -> str:
        missing_fields = []
        for tool_result in executed_tool_results:
            result = tool_result.get("result", {})
            if result.get("status") == "needs_more_info":
                missing_fields.extend(result.get("missing_fields", []))

        if missing_fields:
            next_field = missing_fields[0]
            field_prompts = {
                "patient_name": "Patient peru cheppandi andi.",
                "phone": "Phone number 10 digits cheppandi andi.",
                "doctor_name": "Doctor peru leda specialty cheppandi andi.",
                "date": "Appointment date cheppandi andi.",
                "time": "Preferred time cheppandi andi.",
            }
            return field_prompts.get(
                next_field,
                "Okay andi, appointment booking continue chesthunnanu. Konchem details confirm cheyyandi.",
            )

        if any(tool_result.get("tool") == "get_all_doctors" for tool_result in executed_tool_results):
            return "Okay andi, doctors details check chesanu. Appointment book cheyyadaniki patient name cheppandi."

        if memory.get("appointment_date") or memory.get("appointment_time"):
            return "Okay andi, appointment booking continue chesthunnanu. Patient name cheppandi."

        return "Okay andi, appointment booking continue chesthunnanu. Konchem details confirm cheyyandi."

    def _build_memory_context(self, memory: Dict[str, Any]) -> str:
        remembered = {
            key: value
            for key, value in memory.items()
            if value not in (None, "", False)
        }
        if not remembered:
            return ""
        return (
            "Known call context, do not ask again unless caller changes it:\n"
            f"{json.dumps(remembered, ensure_ascii=True)}\n\n"
        )

    def _update_memory_from_user_input(self, memory: Dict[str, Any], user_input: str):
        phone_match = re.search(r"\b(?:\+91[- ]?)?([6-9]\d{9})\b", user_input)
        if phone_match:
            memory["phone"] = phone_match.group(1)

        lowered = user_input.lower()
        if "morning" in lowered or "udayam" in lowered:
            memory["appointment_time"] = memory.get("appointment_time") or "morning"
        elif "evening" in lowered or "sayantram" in lowered:
            memory["appointment_time"] = memory.get("appointment_time") or "evening"

        if "repu" in lowered or "tomorrow" in lowered:
            memory["appointment_date"] = memory.get("appointment_date") or "tomorrow"
        elif "eroju" in lowered or "today" in lowered:
            memory["appointment_date"] = memory.get("appointment_date") or "today"

    def _update_memory_from_tool(
        self,
        memory: Dict[str, Any],
        tool_name: str,
        tool_args: Dict[str, Any],
        result: Dict[str, Any],
    ):
        if tool_args.get("doctor_name"):
            memory["doctor_name"] = tool_args["doctor_name"]
        if tool_args.get("patient_name"):
            memory["patient_name"] = tool_args["patient_name"]
        if tool_args.get("phone"):
            memory["phone"] = tool_args["phone"]
        if tool_args.get("date"):
            memory["appointment_date"] = tool_args["date"]
        if tool_args.get("time"):
            memory["appointment_time"] = tool_args["time"]

        if tool_name == "check_doctor_availability":
            memory["availability_checked"] = bool(result.get("available"))
        elif tool_name == "book_appointment" and result.get("status") == "confirmed":
            memory["booking_confirmed"] = True
            logger.info(
                "Booking completed",
                extra={
                    "extra_data": {
                        "event": "booking_completed",
                        "doctor_name": result.get("doctor_name"),
                        "date": result.get("date"),
                        "time": result.get("time"),
                    }
                },
            )

    def _tools_for_context(
        self,
        tools: List[Dict[str, Any]],
        memory: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        complete_booking_details = all(
            memory.get(field)
            for field in [
                "patient_name",
                "phone",
                "doctor_name",
                "appointment_date",
                "appointment_time",
            ]
        )
        if complete_booking_details:
            return tools
        return [tool for tool in tools if tool.get("name") != "book_appointment"]

    def _dedupe_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]],
        conv_state: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        filtered_calls = []
        recent_signatures = conv_state.setdefault("recent_tool_signatures", [])

        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            tool_args = tool_call.get("args") or tool_call.get("arguments") or {}
            signature = json.dumps(
                {"name": tool_name, "args": tool_args},
                sort_keys=True,
                ensure_ascii=True,
            )
            if recent_signatures.count(signature) >= self.max_tool_repeats:
                logger.info(
                    "Duplicate tool call skipped",
                    extra={
                        "extra_data": {
                            "event": "tool_call_deduped",
                            "tool": tool_name,
                        }
                    },
                )
                continue
            recent_signatures.append(signature)
            filtered_calls.append(tool_call)

        conv_state["recent_tool_signatures"] = recent_signatures[-12:]
        return filtered_calls

    def cleanup_old_conversations(self, max_age_minutes: int = 120) -> int:
        cutoff = datetime.utcnow().timestamp() - (max_age_minutes * 60)
        removed = 0
        for conversation_id, state in list(self.conversations.items()):
            last_activity = state.get("last_activity_at") or state.get("created_at")
            try:
                last_activity_ts = datetime.fromisoformat(last_activity).timestamp()
            except (TypeError, ValueError):
                last_activity_ts = 0
            if last_activity_ts < cutoff:
                del self.conversations[conversation_id]
                removed += 1
        if removed:
            logger.info(
                "Old conversations cleaned up",
                extra={"extra_data": {"event": "conversation_cleanup", "removed": removed}},
            )
        return removed

    def _generate_conversation_id(self) -> str:
        """Generate unique conversation ID"""
        import uuid
        return str(uuid.uuid4())
