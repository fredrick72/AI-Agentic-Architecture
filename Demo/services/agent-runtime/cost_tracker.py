"""
Cost Tracker - Track and analyze LLM costs
"""
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from database import db

logger = logging.getLogger(__name__)


class CostTracker:
    """
    Track and analyze LLM costs across conversations

    Provides:
    - Real-time cost tracking
    - Cost breakdown by conversation
    - Cost trends over time
    - Budget alerts
    """

    def __init__(self):
        self.cost_threshold_warning = 1.0  # Warn if conversation exceeds $1
        self.cost_threshold_critical = 5.0  # Critical if conversation exceeds $5

    def get_conversation_cost(self, conversation_id: str) -> Dict[str, Any]:
        """
        Get total cost for a conversation

        Args:
            conversation_id: UUID of conversation

        Returns:
            Dict with total_cost, turn_count, avg_cost_per_turn
        """
        query = """
            SELECT
                COUNT(*) as turn_count,
                SUM(cost_usd) as total_cost,
                AVG(cost_usd) as avg_cost_per_turn,
                SUM(tokens_used->>'input_tokens')::int as total_input_tokens,
                SUM(tokens_used->>'output_tokens')::int as total_output_tokens
            FROM conversation_turns
            WHERE conversation_id = %s
        """

        result = db.execute_query(query, (conversation_id,), fetch_one=True)

        if result:
            total_cost = float(result["total_cost"]) if result["total_cost"] else 0.0
            turn_count = result["turn_count"] or 0
            avg_cost = float(result["avg_cost_per_turn"]) if result["avg_cost_per_turn"] else 0.0

            cost_data = {
                "conversation_id": conversation_id,
                "total_cost": round(total_cost, 6),
                "turn_count": turn_count,
                "avg_cost_per_turn": round(avg_cost, 6),
                "total_input_tokens": result["total_input_tokens"] or 0,
                "total_output_tokens": result["total_output_tokens"] or 0,
                "total_tokens": (result["total_input_tokens"] or 0) + (result["total_output_tokens"] or 0)
            }

            # Check thresholds
            if total_cost >= self.cost_threshold_critical:
                cost_data["alert"] = "critical"
                cost_data["alert_message"] = f"Cost ${total_cost:.2f} exceeds critical threshold"
            elif total_cost >= self.cost_threshold_warning:
                cost_data["alert"] = "warning"
                cost_data["alert_message"] = f"Cost ${total_cost:.2f} exceeds warning threshold"
            else:
                cost_data["alert"] = None

            return cost_data

        return {
            "conversation_id": conversation_id,
            "total_cost": 0.0,
            "turn_count": 0,
            "avg_cost_per_turn": 0.0,
            "total_tokens": 0,
            "alert": None
        }

    def get_total_cost(
        self,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Dict[str, Any]:
        """
        Get total cost across all conversations

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dict with total_cost, conversation_count, avg_cost_per_conversation
        """
        query = """
            SELECT
                COUNT(DISTINCT conversation_id) as conversation_count,
                SUM(cost_usd) as total_cost,
                AVG(cost_usd) as avg_cost_per_turn,
                SUM(tokens_used->>'input_tokens')::int as total_input_tokens,
                SUM(tokens_used->>'output_tokens')::int as total_output_tokens
            FROM conversation_turns
            WHERE 1=1
        """

        params = []

        if start_date:
            query += " AND created_at >= %s"
            params.append(start_date)

        if end_date:
            query += " AND created_at <= %s"
            params.append(end_date)

        result = db.execute_query(query, tuple(params) if params else None, fetch_one=True)

        if result:
            total_cost = float(result["total_cost"]) if result["total_cost"] else 0.0
            conversation_count = result["conversation_count"] or 0

            return {
                "total_cost": round(total_cost, 6),
                "conversation_count": conversation_count,
                "avg_cost_per_conversation": round(total_cost / conversation_count, 6) if conversation_count > 0 else 0.0,
                "total_input_tokens": result["total_input_tokens"] or 0,
                "total_output_tokens": result["total_output_tokens"] or 0,
                "total_tokens": (result["total_input_tokens"] or 0) + (result["total_output_tokens"] or 0),
                "period": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None
                }
            }

        return {
            "total_cost": 0.0,
            "conversation_count": 0,
            "avg_cost_per_conversation": 0.0,
            "total_tokens": 0
        }

    def get_cost_breakdown(
        self,
        conversation_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get cost breakdown by turn for a conversation

        Args:
            conversation_id: UUID of conversation

        Returns:
            List of turns with cost details
        """
        query = """
            SELECT
                turn_id,
                user_input,
                cost_usd,
                tokens_used,
                created_at
            FROM conversation_turns
            WHERE conversation_id = %s
            ORDER BY created_at ASC
        """

        results = db.execute_query(query, (conversation_id,))

        breakdown = []
        cumulative_cost = 0.0

        for row in results:
            cost = float(row["cost_usd"]) if row["cost_usd"] else 0.0
            cumulative_cost += cost

            tokens_used = row["tokens_used"] or {}

            breakdown.append({
                "turn_id": row["turn_id"],
                "user_input": row["user_input"][:100] + "..." if len(row["user_input"]) > 100 else row["user_input"],
                "cost": round(cost, 6),
                "cumulative_cost": round(cumulative_cost, 6),
                "tokens": {
                    "input": tokens_used.get("input", 0),
                    "output": tokens_used.get("output", 0),
                    "total": tokens_used.get("input", 0) + tokens_used.get("output", 0)
                },
                "created_at": row["created_at"].isoformat() if row["created_at"] else None
            })

        return breakdown

    def get_cost_trends(
        self,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get cost trends over time

        Args:
            days: Number of days to analyze

        Returns:
            Dict with daily cost breakdown
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        query = """
            SELECT
                DATE(created_at) as date,
                COUNT(*) as turn_count,
                SUM(cost_usd) as daily_cost,
                COUNT(DISTINCT conversation_id) as conversation_count
            FROM conversation_turns
            WHERE created_at >= %s
            GROUP BY DATE(created_at)
            ORDER BY date ASC
        """

        results = db.execute_query(query, (start_date,))

        daily_data = []
        total_cost = 0.0

        for row in results:
            daily_cost = float(row["daily_cost"]) if row["daily_cost"] else 0.0
            total_cost += daily_cost

            daily_data.append({
                "date": row["date"].isoformat() if row["date"] else None,
                "cost": round(daily_cost, 6),
                "turn_count": row["turn_count"],
                "conversation_count": row["conversation_count"]
            })

        return {
            "period_days": days,
            "total_cost": round(total_cost, 6),
            "avg_daily_cost": round(total_cost / days, 6) if days > 0 else 0.0,
            "daily_breakdown": daily_data
        }

    def estimate_monthly_cost(self) -> Dict[str, Any]:
        """
        Estimate monthly cost based on recent usage

        Returns:
            Dict with estimated monthly cost
        """
        # Get last 7 days cost
        trends = self.get_cost_trends(days=7)
        avg_daily_cost = trends["avg_daily_cost"]

        # Estimate monthly (30 days)
        estimated_monthly = avg_daily_cost * 30

        return {
            "avg_daily_cost": round(avg_daily_cost, 6),
            "estimated_monthly_cost": round(estimated_monthly, 2),
            "based_on_days": 7,
            "note": "Estimate based on last 7 days of usage"
        }
