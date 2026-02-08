"""
Agent Orchestrator - Main reasoning loop
"""
import logging
import requests
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json
import re

from config import settings
from conversation_manager import ConversationManager

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Main agent orchestration loop

    Flow:
    1. Receive user input
    2. Check for clarification needs
    3. Call LLM Gateway for reasoning
    4. Parse tool calls from LLM response
    5. Execute tools via Tool Registry
    6. Feed results back to LLM
    7. Repeat until final answer (max 5 iterations)
    8. Save conversation + costs
    """

    def __init__(self, conversation_manager: ConversationManager):
        self.conversation_manager = conversation_manager
        self.llm_gateway_url = settings.llm_gateway_url
        self.tool_registry_url = settings.tool_registry_url
        self.clarification_engine_url = settings.clarification_engine_url
        self.max_iterations = settings.max_iterations

    async def process_query(
        self,
        user_input: str,
        conversation_id: Optional[str] = None,
        clarification_response: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for processing user queries

        Args:
            user_input: User's message
            conversation_id: Optional existing conversation ID
            clarification_response: Optional user's clarification response

        Returns:
            Dict with:
                - type: "result" | "clarification_needed" | "error"
                - data: Result data or clarification UI schema
                - metadata: Execution metadata (tokens, cost, tool_calls)
                - conversation_id: Conversation ID
        """
        start_time = datetime.utcnow()

        try:
            # Create or load conversation
            if not conversation_id:
                conversation_id = self.conversation_manager.create_conversation()
                logger.info(f"✓ Created new conversation: {conversation_id}")
            else:
                logger.info(f"✓ Continuing conversation: {conversation_id}")

            # Load conversation history
            history = self.conversation_manager.get_conversation_history(
                conversation_id,
                limit=settings.max_conversation_history
            )

            # Step 1: Check for clarification needs (if enabled)
            if settings.enable_clarification and not clarification_response:
                clarification_result = self._check_clarification(user_input, history)

                if clarification_result["needs_clarification"]:
                    # Save turn with clarification request
                    self.conversation_manager.add_turn(
                        conversation_id=conversation_id,
                        user_input=user_input,
                        intent_data=clarification_result["intent_data"],
                        clarification_needed=True,
                        clarification_schema=clarification_result["ui_schema"]
                    )

                    # Update conversation state
                    self.conversation_manager.update_conversation_state(
                        conversation_id,
                        "waiting_clarification"
                    )

                    logger.info("⚠ Clarification needed, pausing execution")

                    return {
                        "type": "clarification_needed",
                        "data": clarification_result["ui_schema"],
                        "metadata": {
                            "clarification_type": clarification_result["clarification_type"],
                            "intent_data": clarification_result["intent_data"]
                        },
                        "conversation_id": conversation_id
                    }

            # Step 2: Process clarification response if provided
            resolved_parameters = {}
            if clarification_response:
                resolved_parameters = self._process_clarification_response(
                    clarification_response
                )
                logger.info(f"✓ Clarification resolved: {resolved_parameters}")

            # Step 3: Execute main reasoning loop
            result = await self._reasoning_loop(
                user_input,
                conversation_id,
                history,
                resolved_parameters
            )

            # Calculate total execution time
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            result["metadata"]["total_execution_time_ms"] = duration_ms

            # Update conversation state
            self.conversation_manager.update_conversation_state(
                conversation_id,
                "completed"
            )

            logger.info(f"✓ Query processed successfully in {duration_ms}ms")

            return {
                **result,
                "conversation_id": conversation_id
            }

        except Exception as e:
            logger.error(f"Orchestration error: {e}", exc_info=True)

            # Update conversation state to error
            if conversation_id:
                self.conversation_manager.update_conversation_state(
                    conversation_id,
                    "error",
                    {"error": str(e)}
                )

            return {
                "type": "error",
                "data": {
                    "error": str(e),
                    "message": "I encountered an error processing your request."
                },
                "metadata": {},
                "conversation_id": conversation_id
            }

    async def _reasoning_loop(
        self,
        user_input: str,
        conversation_id: str,
        history: List[Dict[str, Any]],
        resolved_parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main iterative reasoning loop

        Iterates up to max_iterations times:
        1. Call LLM with context
        2. Parse tool calls
        3. Execute tools
        4. Feed results back
        5. Repeat until final answer

        Returns:
            Dict with type="result", data, metadata
        """
        iteration = 0
        tool_calls_made = []
        total_tokens = {"input": 0, "output": 0}
        total_cost = 0.0

        # Build initial context
        context = self._build_context(user_input, history, resolved_parameters)

        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"🔄 Iteration {iteration}/{self.max_iterations}")

            # Call LLM Gateway
            llm_response = self._call_llm(context)

            # Track tokens and cost
            total_tokens["input"] += llm_response.get("tokens_used", {}).get("input_tokens", 0)
            total_tokens["output"] += llm_response.get("tokens_used", {}).get("output_tokens", 0)
            total_cost += llm_response.get("cost", {}).get("total_cost", 0.0)

            response_text = llm_response["response"]

            # Parse for tool calls
            tool_calls = self._parse_tool_calls(response_text)

            if not tool_calls:
                # No more tool calls, this is the final answer
                logger.info("✓ Final answer received")

                # Save turn
                self.conversation_manager.add_turn(
                    conversation_id=conversation_id,
                    user_input=user_input,
                    agent_response=response_text,
                    tool_calls=tool_calls_made,
                    tokens_used=total_tokens,
                    cost_usd=total_cost
                )

                return {
                    "type": "result",
                    "data": {
                        "answer": response_text,
                        "iterations": iteration
                    },
                    "metadata": {
                        "tool_calls": tool_calls_made,
                        "tokens_used": total_tokens,
                        "cost_usd": round(total_cost, 6),
                        "model_used": llm_response.get("model_used"),
                        "cache_hit": llm_response.get("cache_hit", False),
                        "iterations": iteration
                    }
                }

            # Execute tool calls
            logger.info(f"🔧 Executing {len(tool_calls)} tool call(s)")

            tool_results = []
            for tool_call in tool_calls:
                result = self._execute_tool(tool_call)
                tool_results.append(result)
                tool_calls_made.append({
                    "tool": tool_call["tool_name"],
                    "parameters": tool_call["parameters"],
                    "result": result,
                    "iteration": iteration
                })

            # Feed results back to LLM
            context = self._update_context_with_results(context, tool_calls, tool_results)

        # Max iterations reached
        logger.warning(f"⚠ Max iterations ({self.max_iterations}) reached")

        # Save turn
        self.conversation_manager.add_turn(
            conversation_id=conversation_id,
            user_input=user_input,
            agent_response="Max iterations reached. Unable to complete query.",
            tool_calls=tool_calls_made,
            tokens_used=total_tokens,
            cost_usd=total_cost
        )

        return {
            "type": "result",
            "data": {
                "answer": "I reached the maximum number of reasoning steps. Here's what I found:\n\n" +
                         self._summarize_tool_results(tool_calls_made),
                "partial": True,
                "iterations": iteration
            },
            "metadata": {
                "tool_calls": tool_calls_made,
                "tokens_used": total_tokens,
                "cost_usd": round(total_cost, 6),
                "max_iterations_reached": True,
                "iterations": iteration
            }
        }

    def _check_clarification(
        self,
        user_input: str,
        history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Check if clarification is needed via Clarification Engine

        Returns:
            Dict with needs_clarification, clarification_type, ui_schema, intent_data
        """
        try:
            endpoint = f"{self.clarification_engine_url}/clarify/analyze"

            # Build context from history
            context = {}
            if history:
                last_turn = history[-1]
                context = {
                    "last_patient_id": None,  # Could extract from history
                    "previous_intents": []
                }

            payload = {
                "user_input": user_input,
                "context": context
            }

            response = requests.post(
                endpoint,
                json=payload,
                timeout=settings.clarification_timeout
            )
            response.raise_for_status()

            data = response.json()
            logger.info(f"Clarification check: needs={data['needs_clarification']}")

            return data

        except Exception as e:
            logger.error(f"Clarification check failed: {e}")
            # Fallback: assume no clarification needed
            return {
                "needs_clarification": False,
                "intent_data": {"intent": "unknown", "confidence": 0.5}
            }

    def _process_clarification_response(
        self,
        clarification_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process user's clarification response via Clarification Engine

        Returns:
            Resolved parameters dict
        """
        try:
            endpoint = f"{self.clarification_engine_url}/clarify/process"

            response = requests.post(
                endpoint,
                json=clarification_response,
                timeout=settings.clarification_timeout
            )
            response.raise_for_status()

            data = response.json()

            if data["resolved"]:
                return data["resolved_parameters"]
            else:
                logger.error("Clarification processing failed")
                return {}

        except Exception as e:
            logger.error(f"Clarification processing error: {e}")
            return {}

    def _call_llm(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call LLM Gateway for reasoning

        Args:
            context: Dict with prompt, messages, etc.

        Returns:
            LLM response dict
        """
        try:
            endpoint = f"{self.llm_gateway_url}/llm/complete"

            payload = {
                "prompt": context["prompt"],
                "model_preference": "auto",  # Let gateway choose
                "temperature": 0.1,  # Low temp for deterministic reasoning
                "max_tokens": 1000,
                "use_cache": True
            }

            response = requests.post(
                endpoint,
                json=payload,
                timeout=settings.llm_timeout
            )
            response.raise_for_status()

            data = response.json()
            logger.info(f"LLM response: {len(data['response'])} chars, cost=${data['cost']['total_cost']:.4f}")

            return data

        except Exception as e:
            logger.error(f"LLM call failed: {e}", exc_info=True)
            raise

    def _execute_tool(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool via Tool Registry

        Args:
            tool_call: Dict with tool_name and parameters

        Returns:
            Tool result dict
        """
        try:
            endpoint = f"{self.tool_registry_url}/tools/execute"

            payload = {
                "tool_name": tool_call["tool_name"],
                "parameters": tool_call["parameters"]
            }

            response = requests.post(
                endpoint,
                json=payload,
                timeout=settings.tool_timeout
            )
            response.raise_for_status()

            data = response.json()
            logger.info(f"✓ Tool {tool_call['tool_name']} executed successfully")

            return data["result"]

        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return {
                "error": str(e),
                "tool": tool_call["tool_name"]
            }

    def _build_context(
        self,
        user_input: str,
        history: List[Dict[str, Any]],
        resolved_parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build context for LLM call

        Includes:
        - System prompt with tool definitions
        - Conversation history
        - Current user input
        - Resolved parameters (if from clarification)
        """
        # System prompt
        system_prompt = """You are a healthcare claims assistant with access to tools.

Available Tools:
1. query_patients(name: str) - Search for patients by name
   Returns: List of patients with patient_id, full_name, last_visit_date

2. get_claims(patient_id: str, status: Optional[List[str]], claim_type: Optional[str]) - Get claims for a patient
   Returns: List of claims with amounts, statuses, and total_amount

3. calculate_total(claim_ids: List[str]) - Calculate total amount from claim IDs
   Returns: Total amount and breakdown

4. search_knowledge(query: str, limit: int, category: str) - Search knowledge base for relevant information
   Returns: List of relevant documents with title, content, category, and similarity scores
   Categories: policy, procedure, diagnosis_code, claims_process

Instructions:
- Break down complex queries into tool calls
- Use patient_id (not name) for get_claims
- Use search_knowledge when the user asks about policies, procedures, diagnosis codes, medical terminology, or coverage rules
- When citing knowledge base results, mention the source document title
- If you need to call a tool, respond with: TOOL_CALL: tool_name(param1="value1", param2="value2")
- You can make multiple TOOL_CALL in one response
- After receiving tool results, provide a clear answer to the user
- Be conversational and helpful

Example:
User: "What is the total for all claims by John Smith?"
You: I need to find John Smith first.
TOOL_CALL: query_patients(name="John Smith")
[After receiving patient_id=PAT-12345]
You: TOOL_CALL: get_claims(patient_id="PAT-12345")
[After receiving claim_ids]
You: TOOL_CALL: calculate_total(claim_ids=["CLM-12345-001", "CLM-12345-002"])
[After receiving total]
You: John Smith has 2 claims totaling $1,250.50.

Example:
User: "What does diagnosis code S83.5 mean?"
You: Let me look that up in the knowledge base.
TOOL_CALL: search_knowledge(query="diagnosis code S83.5")
[After receiving knowledge results]
You: Diagnosis code S83.5 refers to a sprain of the cruciate ligament of the knee...
"""

        # Build conversation context
        conversation_context = ""
        if history:
            for turn in history[-3:]:  # Last 3 turns
                conversation_context += f"User: {turn['user_input']}\n"
                if turn['agent_response']:
                    conversation_context += f"Assistant: {turn['agent_response']}\n"

        # Add resolved parameters if any
        parameters_context = ""
        if resolved_parameters:
            parameters_context = f"\n[User clarified: {json.dumps(resolved_parameters)}]"

        # Combine into prompt
        prompt = f"""{system_prompt}

{conversation_context}
User: {user_input}{parameters_context}
Assistant:"""

        return {
            "prompt": prompt,
            "system_prompt": system_prompt,
            "user_input": user_input
        }

    def _update_context_with_results(
        self,
        context: Dict[str, Any],
        tool_calls: List[Dict[str, Any]],
        tool_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Update context with tool results for next iteration
        """
        results_text = "\n[Tool Results]\n"

        for tool_call, result in zip(tool_calls, tool_results):
            results_text += f"- {tool_call['tool_name']}: {json.dumps(result, indent=2)}\n"

        results_text += "\nBased on these results, provide your final answer to the user.\nAssistant:"

        # Append to existing prompt
        context["prompt"] = context["prompt"] + "\n" + results_text

        return context

    def _parse_tool_calls(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Parse tool calls from LLM response

        Looks for pattern: TOOL_CALL: tool_name(param1="value1", param2="value2")

        Returns:
            List of tool call dicts with tool_name and parameters
        """
        tool_calls = []

        # Regex pattern for TOOL_CALL
        pattern = r'TOOL_CALL:\s*(\w+)\((.*?)\)'

        matches = re.finditer(pattern, response_text, re.MULTILINE)

        for match in matches:
            tool_name = match.group(1)
            params_str = match.group(2)

            # Parse parameters (simple key="value" parsing)
            parameters = {}
            param_pattern = r'(\w+)=(["\'])(.*?)\2'
            for param_match in re.finditer(param_pattern, params_str):
                param_name = param_match.group(1)
                param_value = param_match.group(3)
                parameters[param_name] = param_value

            tool_calls.append({
                "tool_name": tool_name,
                "parameters": parameters
            })

            logger.info(f"Parsed tool call: {tool_name}({parameters})")

        return tool_calls

    def _summarize_tool_results(self, tool_calls: List[Dict[str, Any]]) -> str:
        """
        Summarize tool results for partial response
        """
        summary = []
        for tc in tool_calls:
            result = tc.get("result", {})
            summary.append(f"- {tc['tool']}: {json.dumps(result, indent=2)[:200]}...")

        return "\n".join(summary)
