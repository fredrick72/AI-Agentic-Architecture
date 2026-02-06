"""
Conversation Manager - Handle conversation persistence and retrieval
"""
import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from database import db

logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Manages conversation history in PostgreSQL

    Stores:
    - conversations: High-level conversation state
    - conversation_turns: Individual messages, tool calls, costs
    """

    def create_conversation(
        self,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new conversation

        Args:
            user_id: Optional user identifier
            metadata: Optional metadata dict

        Returns:
            conversation_id (UUID string)
        """
        conversation_id = str(uuid.uuid4())

        query = """
            INSERT INTO conversations (
                conversation_id,
                user_id,
                state,
                metadata,
                created_at,
                updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """

        now = datetime.utcnow()
        metadata = metadata or {}

        db.execute_update(
            query,
            (
                conversation_id,
                user_id,
                "active",
                json.dumps(metadata),
                now,
                now
            )
        )

        logger.info(f"✓ Created conversation: {conversation_id}")
        return conversation_id

    def add_turn(
        self,
        conversation_id: str,
        user_input: str,
        agent_response: Optional[str] = None,
        intent_data: Optional[Dict[str, Any]] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tokens_used: Optional[Dict[str, Any]] = None,
        cost_usd: Optional[float] = None,
        clarification_needed: bool = False,
        clarification_schema: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Add a conversation turn

        Args:
            conversation_id: UUID of conversation
            user_input: User's message
            agent_response: Agent's response (if complete)
            intent_data: Intent analysis data
            tool_calls: List of tool executions
            tokens_used: Token usage breakdown
            cost_usd: Total cost for this turn
            clarification_needed: If clarification was requested
            clarification_schema: UI schema if clarification needed

        Returns:
            turn_id
        """
        query = """
            INSERT INTO conversation_turns (
                conversation_id,
                user_input,
                agent_response,
                intent_data,
                tool_calls,
                tokens_used,
                cost_usd,
                clarification_needed,
                clarification_schema,
                created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING turn_id
        """

        result = db.execute_query(
            query,
            (
                conversation_id,
                user_input,
                agent_response,
                json.dumps(intent_data) if intent_data else None,
                json.dumps(tool_calls) if tool_calls else None,
                json.dumps(tokens_used) if tokens_used else None,
                cost_usd,
                clarification_needed,
                json.dumps(clarification_schema) if clarification_schema else None,
                datetime.utcnow()
            ),
            fetch_one=True
        )

        turn_id = result["turn_id"]

        # Update conversation updated_at
        db.execute_update(
            "UPDATE conversations SET updated_at = %s WHERE conversation_id = %s",
            (datetime.utcnow(), conversation_id)
        )

        logger.info(f"✓ Added turn {turn_id} to conversation {conversation_id}")
        return turn_id

    def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history (recent turns)

        Args:
            conversation_id: UUID of conversation
            limit: Max number of turns to return

        Returns:
            List of turns (newest first)
        """
        query = """
            SELECT
                turn_id,
                user_input,
                agent_response,
                intent_data,
                tool_calls,
                tokens_used,
                cost_usd,
                clarification_needed,
                clarification_schema,
                created_at
            FROM conversation_turns
            WHERE conversation_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """

        results = db.execute_query(query, (conversation_id, limit))

        # Reverse to get oldest first
        turns = []
        for row in reversed(results):
            turn = {
                "turn_id": row["turn_id"],
                "user_input": row["user_input"],
                "agent_response": row["agent_response"],
                "intent_data": row["intent_data"],
                "tool_calls": row["tool_calls"],
                "tokens_used": row["tokens_used"],
                "cost_usd": float(row["cost_usd"]) if row["cost_usd"] else 0.0,
                "clarification_needed": row["clarification_needed"],
                "clarification_schema": row["clarification_schema"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None
            }
            turns.append(turn)

        logger.info(f"Retrieved {len(turns)} turns for conversation {conversation_id}")
        return turns

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get conversation metadata

        Args:
            conversation_id: UUID of conversation

        Returns:
            Conversation dict or None
        """
        query = """
            SELECT
                conversation_id,
                user_id,
                state,
                metadata,
                created_at,
                updated_at
            FROM conversations
            WHERE conversation_id = %s
        """

        result = db.execute_query(query, (conversation_id,), fetch_one=True)

        if result:
            return {
                "conversation_id": result["conversation_id"],
                "user_id": result["user_id"],
                "state": result["state"],
                "metadata": result["metadata"],
                "created_at": result["created_at"].isoformat() if result["created_at"] else None,
                "updated_at": result["updated_at"].isoformat() if result["updated_at"] else None
            }

        return None

    def update_conversation_state(
        self,
        conversation_id: str,
        state: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Update conversation state

        Args:
            conversation_id: UUID of conversation
            state: New state (active, waiting_clarification, completed, error)
            metadata: Optional metadata to merge
        """
        if metadata:
            query = """
                UPDATE conversations
                SET state = %s, metadata = metadata || %s::jsonb, updated_at = %s
                WHERE conversation_id = %s
            """
            db.execute_update(
                query,
                (state, json.dumps(metadata), datetime.utcnow(), conversation_id)
            )
        else:
            query = """
                UPDATE conversations
                SET state = %s, updated_at = %s
                WHERE conversation_id = %s
            """
            db.execute_update(
                query,
                (state, datetime.utcnow(), conversation_id)
            )

        logger.info(f"✓ Updated conversation {conversation_id} state to: {state}")

    def get_conversation_cost(self, conversation_id: str) -> Dict[str, Any]:
        """
        Calculate total cost for a conversation

        Args:
            conversation_id: UUID of conversation

        Returns:
            Dict with total_cost, total_tokens, turn_count
        """
        query = """
            SELECT
                COUNT(*) as turn_count,
                SUM(cost_usd) as total_cost
            FROM conversation_turns
            WHERE conversation_id = %s
        """

        result = db.execute_query(query, (conversation_id,), fetch_one=True)

        return {
            "conversation_id": conversation_id,
            "turn_count": result["turn_count"] or 0,
            "total_cost": float(result["total_cost"]) if result["total_cost"] else 0.0
        }

    def format_history_for_llm(
        self,
        conversation_id: str,
        limit: int = 5
    ) -> List[Dict[str, str]]:
        """
        Format conversation history for LLM context

        Returns list of message dicts in OpenAI format:
        [
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."}
        ]

        Args:
            conversation_id: UUID of conversation
            limit: Max number of turns to include

        Returns:
            List of message dicts
        """
        turns = self.get_conversation_history(conversation_id, limit)

        messages = []
        for turn in turns:
            # Add user message
            messages.append({
                "role": "user",
                "content": turn["user_input"]
            })

            # Add assistant response if available
            if turn["agent_response"]:
                messages.append({
                    "role": "assistant",
                    "content": turn["agent_response"]
                })

        return messages
