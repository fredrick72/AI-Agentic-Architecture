"""
Agent Runtime - Main Application
Orchestrates the full AI-agentic workflow
"""
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

from config import settings
from database import db
from conversation_manager import ConversationManager
from orchestrator import AgentOrchestrator
from cost_tracker import CostTracker

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Agent Runtime",
    description="AI Agent orchestrator with iterative reasoning, tool execution, and clarification handling",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
conversation_manager = ConversationManager()
orchestrator = AgentOrchestrator(conversation_manager)
cost_tracker = CostTracker()

# ============================================
# Prometheus Metrics
# ============================================

agent_requests_total = Counter(
    'agent_requests_total',
    'Total agent requests',
    ['response_type']  # result, clarification_needed, error
)

agent_request_duration_seconds = Histogram(
    'agent_request_duration_seconds',
    'Agent request duration'
)

agent_iterations_total = Histogram(
    'agent_iterations_total',
    'Number of reasoning iterations per request'
)

agent_cost_usd_total = Counter(
    'agent_cost_usd_total',
    'Total cost in USD'
)

# ============================================
# Request/Response Models
# ============================================

class QueryRequest(BaseModel):
    """Request to agent"""
    message: str = Field(..., description="User's message or query")
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID")
    clarification_response: Optional[Dict[str, Any]] = Field(None, description="User's clarification response")


class QueryResponse(BaseModel):
    """Response from agent"""
    type: str  # "result" | "clarification_needed" | "error"
    data: Any
    metadata: Dict[str, Any]
    conversation_id: str


class ConversationHistoryResponse(BaseModel):
    """Conversation history response"""
    conversation_id: str
    turns: List[Dict[str, Any]]
    total_cost: float
    turn_count: int


# ============================================
# API Endpoints
# ============================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Agent Runtime",
        "version": "1.0.0",
        "status": "operational",
        "description": "AI Agent with iterative reasoning and clarification"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db_connected = db.test_connection()

    # Check dependent services
    services_status = {
        "database": "connected" if db_connected else "disconnected",
        "llm_gateway": settings.llm_gateway_url,
        "tool_registry": settings.tool_registry_url,
        "clarification_engine": settings.clarification_engine_url
    }

    return {
        "status": "healthy" if db_connected else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "services": services_status
    }


@app.post("/agent/query", response_model=QueryResponse)
async def query_agent(request: QueryRequest):
    """
    Main agent query endpoint

    Flow:
    1. Check for clarification needs
    2. Execute reasoning loop
    3. Return result or clarification request

    Example Simple Query:
        POST /agent/query
        {
            "message": "How many claims does patient PAT-12345 have?"
        }
        → Returns final answer

    Example Ambiguous Query:
        POST /agent/query
        {
            "message": "Find claims for John"
        }
        → Returns clarification UI (which John?)

    Example Clarification Response:
        POST /agent/query
        {
            "message": "Find claims for John",
            "conversation_id": "uuid-here",
            "clarification_response": {
                "clarification_type": "entity_disambiguation",
                "user_selection": {
                    "entity_type": "patient",
                    "selected_id": "PAT-12345"
                },
                "original_intent": {...}
            }
        }
        → Returns final answer
    """
    start_time = datetime.utcnow()

    try:
        logger.info(f"📥 Query: {request.message[:100]}...")

        # Process query via orchestrator
        with agent_request_duration_seconds.time():
            result = await orchestrator.process_query(
                user_input=request.message,
                conversation_id=request.conversation_id,
                clarification_response=request.clarification_response
            )

        # Update metrics
        agent_requests_total.labels(response_type=result["type"]).inc()

        if result["type"] == "result":
            iterations = result["metadata"].get("iterations", 0)
            agent_iterations_total.observe(iterations)

            cost = result["metadata"].get("cost_usd", 0.0)
            agent_cost_usd_total.inc(cost)

        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        logger.info(
            f"✓ Query processed: type={result['type']}, "
            f"duration={duration_ms}ms, "
            f"conversation={result['conversation_id']}"
        )

        return QueryResponse(**result)

    except Exception as e:
        logger.error(f"Query processing error: {e}", exc_info=True)
        agent_requests_total.labels(response_type="error").inc()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query processing failed: {str(e)}"
        )


@app.get("/agent/conversation/{conversation_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(conversation_id: str, limit: int = 10):
    """
    Get conversation history

    Args:
        conversation_id: UUID of conversation
        limit: Max number of turns to return (default 10)

    Returns:
        Conversation history with turns and cost data
    """
    try:
        # Get conversation metadata
        conversation = conversation_manager.get_conversation(conversation_id)

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation not found: {conversation_id}"
            )

        # Get conversation turns
        turns = conversation_manager.get_conversation_history(conversation_id, limit)

        # Get cost data
        cost_data = cost_tracker.get_conversation_cost(conversation_id)

        return ConversationHistoryResponse(
            conversation_id=conversation_id,
            turns=turns,
            total_cost=cost_data["total_cost"],
            turn_count=cost_data["turn_count"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/agent/conversation/{conversation_id}/cost")
async def get_conversation_cost(conversation_id: str):
    """
    Get detailed cost breakdown for a conversation

    Returns:
        Cost breakdown with per-turn details
    """
    try:
        # Get overall cost
        cost_summary = cost_tracker.get_conversation_cost(conversation_id)

        # Get per-turn breakdown
        cost_breakdown = cost_tracker.get_cost_breakdown(conversation_id)

        return {
            "summary": cost_summary,
            "breakdown": cost_breakdown
        }

    except Exception as e:
        logger.error(f"Error getting cost data: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/agent/stats")
async def get_agent_stats():
    """
    Get overall agent statistics

    Returns:
        Stats on usage, costs, trends
    """
    try:
        # Get total cost (last 7 days)
        total_cost = cost_tracker.get_total_cost()

        # Get cost trends
        trends = cost_tracker.get_cost_trends(days=7)

        # Get monthly estimate
        monthly_estimate = cost_tracker.estimate_monthly_cost()

        # Get conversation count
        query = "SELECT COUNT(*) as count FROM conversations"
        result = db.execute_query(query, fetch_one=True)
        conversation_count = result["count"] if result else 0

        return {
            "total_conversations": conversation_count,
            "cost_summary": total_cost,
            "cost_trends": trends,
            "monthly_estimate": monthly_estimate,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# ============================================
# Startup Event
# ============================================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("=" * 50)
    logger.info("Agent Runtime Starting...")
    logger.info("=" * 50)
    logger.info(f"Database: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}")
    logger.info(f"Max iterations: {settings.max_iterations}")
    logger.info(f"Clarification: {'enabled' if settings.enable_clarification else 'disabled'}")
    logger.info("")
    logger.info("Dependent Services:")
    logger.info(f"  - LLM Gateway: {settings.llm_gateway_url}")
    logger.info(f"  - Tool Registry: {settings.tool_registry_url}")
    logger.info(f"  - Clarification Engine: {settings.clarification_engine_url}")
    logger.info("=" * 50)

    # Test database connection
    if db.test_connection():
        logger.info("✓ Database connected")

        # Count conversations
        try:
            query = "SELECT COUNT(*) as count FROM conversations"
            result = db.execute_query(query, fetch_one=True)
            count = result["count"] if result else 0
            logger.info(f"✓ {count} conversations in history")
        except Exception as e:
            logger.warning(f"Could not count conversations: {e}")
    else:
        logger.error("❌ Database connection failed")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level=settings.log_level.lower())
