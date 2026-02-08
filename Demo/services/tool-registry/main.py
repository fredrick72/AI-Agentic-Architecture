"""
Tool Registry - Main Application
Provides executable tools for the AI agent
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
from tools import (
    query_patients,
    get_patient_by_id,
    get_claims,
    get_claim_by_id,
    calculate_total,
    calculate_total_by_patient,
    search_knowledge,
    add_document,
    generate_missing_embeddings,
)

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Tool Registry",
    description="Executable tools for AI agent: database queries, calculations, API calls",
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

# ============================================
# Prometheus Metrics
# ============================================

tool_executions_total = Counter(
    'tool_executions_total',
    'Total tool executions',
    ['tool_name', 'status']
)

tool_execution_duration_seconds = Histogram(
    'tool_execution_duration_seconds',
    'Tool execution duration',
    ['tool_name']
)

# ============================================
# Request/Response Models
# ============================================

class ToolExecutionRequest(BaseModel):
    """Generic tool execution request"""
    tool_name: str = Field(..., description="Name of tool to execute")
    parameters: Dict[str, Any] = Field(..., description="Tool parameters")


class ToolExecutionResponse(BaseModel):
    """Generic tool execution response"""
    tool: str
    result: Any
    metadata: Dict[str, Any]
    timestamp: str


class QueryPatientsRequest(BaseModel):
    """Request for query_patients tool"""
    name: str = Field(..., description="Patient name to search for")
    limit: int = Field(10, ge=1, le=100)


class GetClaimsRequest(BaseModel):
    """Request for get_claims tool"""
    patient_id: str = Field(..., description="Patient ID")
    status: Optional[List[str]] = Field(None, description="Filter by status")
    claim_type: Optional[str] = Field(None, description="Filter by claim type")
    limit: int = Field(100, ge=1, le=1000)


class CalculateTotalRequest(BaseModel):
    """Request for calculate_total tool"""
    claim_ids: List[str] = Field(..., description="List of claim IDs")


# ============================================
# Tool Definitions (for LLM)
# ============================================

TOOL_DEFINITIONS = {
    "query_patients": {
        "name": "query_patients",
        "description": "Search for patients by name with fuzzy matching",
        "parameters": {
            "name": {"type": "string", "required": True, "description": "Patient name to search for"},
            "limit": {"type": "integer", "required": False, "default": 10, "description": "Max results"}
        },
        "returns": "List of matching patients with patient_id, full_name, and last_visit_date"
    },
    "get_claims": {
        "name": "get_claims",
        "description": "Retrieve claims for a specific patient",
        "parameters": {
            "patient_id": {"type": "string", "required": True, "description": "Patient ID (e.g., PAT-12345)"},
            "status": {"type": "array", "required": False, "description": "Filter by status (pending, approved, denied)"},
            "claim_type": {"type": "string", "required": False, "description": "Filter by type (medical, dental, vision)"},
            "limit": {"type": "integer", "required": False, "default": 100, "description": "Max results"}
        },
        "returns": "List of claims with amounts, statuses, and total amount"
    },
    "calculate_total": {
        "name": "calculate_total",
        "description": "Calculate total amount from a list of claim IDs",
        "parameters": {
            "claim_ids": {"type": "array", "required": True, "description": "List of claim IDs"}
        },
        "returns": "Total amount and breakdown by claim"
    },
    "search_knowledge": {
        "name": "search_knowledge",
        "description": "Search knowledge base for relevant information using semantic similarity (RAG). Use for policies, procedures, diagnosis codes, medical terminology, or coverage rules.",
        "parameters": {
            "query": {"type": "string", "required": True, "description": "Natural language search query"},
            "limit": {"type": "integer", "required": False, "default": 5, "description": "Max results to return"},
            "category": {"type": "string", "required": False, "description": "Filter by category (policy, procedure, diagnosis_code, claims_process)"}
        },
        "returns": "List of relevant documents with title, content, category, and similarity scores"
    }
}

# ============================================
# API Endpoints
# ============================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Tool Registry",
        "version": "1.0.0",
        "status": "operational",
        "available_tools": list(TOOL_DEFINITIONS.keys())
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db_connected = db.test_connection()

    return {
        "status": "healthy" if db_connected else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected" if db_connected else "disconnected"
    }


@app.get("/tools")
async def list_tools():
    """List all available tools with definitions"""
    return {
        "tools": TOOL_DEFINITIONS,
        "count": len(TOOL_DEFINITIONS)
    }


@app.post("/tools/execute", response_model=ToolExecutionResponse)
async def execute_tool(request: ToolExecutionRequest):
    """
    Generic tool execution endpoint

    Routes to specific tool based on tool_name parameter
    """
    start_time = datetime.utcnow()
    tool_name = request.tool_name

    try:
        logger.info(f"Executing tool: {tool_name} with params: {request.parameters}")

        # Route to specific tool
        if tool_name == "query_patients":
            result = query_patients(**request.parameters)
        elif tool_name == "get_claims":
            result = get_claims(**request.parameters)
        elif tool_name == "calculate_total":
            result = calculate_total(**request.parameters)
        elif tool_name == "search_knowledge":
            result = search_knowledge(**request.parameters)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool not found: {tool_name}. Available: {list(TOOL_DEFINITIONS.keys())}"
            )

        # Calculate execution time
        duration = (datetime.utcnow() - start_time).total_seconds()

        # Update metrics
        tool_executions_total.labels(tool_name=tool_name, status="success").inc()
        tool_execution_duration_seconds.labels(tool_name=tool_name).observe(duration)

        logger.info(f"✓ Tool {tool_name} completed in {duration:.3f}s")

        return ToolExecutionResponse(
            tool=tool_name,
            result=result,
            metadata={
                "execution_time_ms": int(duration * 1000),
                "timestamp": datetime.utcnow().isoformat()
            },
            timestamp=datetime.utcnow().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Tool execution error: {e}", exc_info=True)
        tool_executions_total.labels(tool_name=tool_name, status="error").inc()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tool execution failed: {str(e)}"
        )


# ============================================
# Specific Tool Endpoints (for direct access)
# ============================================

@app.post("/tools/query_patients")
async def api_query_patients(request: QueryPatientsRequest):
    """Query patients by name"""
    return await execute_tool(ToolExecutionRequest(
        tool_name="query_patients",
        parameters=request.dict()
    ))


@app.get("/tools/patient/{patient_id}")
async def api_get_patient(patient_id: str):
    """Get patient by ID"""
    try:
        result = get_patient_by_id(patient_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient not found: {patient_id}"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/tools/get_claims")
async def api_get_claims(request: GetClaimsRequest):
    """Get claims for a patient"""
    return await execute_tool(ToolExecutionRequest(
        tool_name="get_claims",
        parameters=request.dict()
    ))


@app.get("/tools/claim/{claim_id}")
async def api_get_claim(claim_id: str):
    """Get claim by ID"""
    try:
        result = get_claim_by_id(claim_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Claim not found: {claim_id}"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/tools/calculate_total")
async def api_calculate_total(request: CalculateTotalRequest):
    """Calculate total amount from claim IDs"""
    return await execute_tool(ToolExecutionRequest(
        tool_name="calculate_total",
        parameters=request.dict()
    ))


@app.get("/tools/patient/{patient_id}/total")
async def api_patient_total(
    patient_id: str,
    status: Optional[str] = None
):
    """Calculate total for a patient"""
    try:
        status_list = status.split(',') if status else None
        result = calculate_total_by_patient(patient_id, status_list)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================
# Knowledge Management Endpoints (Admin)
# ============================================

class AddDocumentRequest(BaseModel):
    """Request for adding a knowledge base document"""
    title: str = Field(..., description="Document title")
    content: str = Field(..., description="Document content")
    category: str = Field("general", description="Category (policy, procedure, diagnosis_code, claims_process)")
    tags: Optional[List[str]] = Field(None, description="Tags for filtering")


@app.post("/knowledge/add")
async def api_add_document(request: AddDocumentRequest):
    """Add a document to the knowledge base with auto-generated embedding"""
    try:
        result = add_document(
            title=request.title,
            content=request.content,
            category=request.category,
            tags=request.tags
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/knowledge/embed-all")
async def api_embed_all():
    """Generate embeddings for all documents missing them"""
    try:
        result = generate_missing_embeddings()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/knowledge/stats")
async def api_knowledge_stats():
    """Get knowledge base statistics"""
    try:
        total = db.execute_query(
            "SELECT COUNT(*) as count FROM knowledge_base",
            fetch_one=True
        )
        embedded = db.execute_query(
            "SELECT COUNT(*) as count FROM knowledge_base WHERE embedding IS NOT NULL",
            fetch_one=True
        )
        categories = db.execute_query(
            "SELECT metadata->>'category' as category, COUNT(*) as count "
            "FROM knowledge_base GROUP BY metadata->>'category' ORDER BY count DESC"
        )

        return {
            "total_documents": total["count"],
            "embedded_documents": embedded["count"],
            "pending_embedding": total["count"] - embedded["count"],
            "categories": {row["category"]: row["count"] for row in categories}
        }
    except Exception as e:
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
    logger.info("Tool Registry Starting...")
    logger.info("=" * 50)
    logger.info(f"Database: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}")
    logger.info(f"LLM Gateway: {settings.llm_gateway_url}")
    logger.info(f"Available tools: {list(TOOL_DEFINITIONS.keys())}")
    logger.info("=" * 50)

    # Test database connection
    if db.test_connection():
        logger.info("✓ Database connected")

        # Count available data
        try:
            patient_count = db.execute_query("SELECT COUNT(*) as count FROM patients", fetch_one=True)
            claim_count = db.execute_query("SELECT COUNT(*) as count FROM claims", fetch_one=True)
            kb_count = db.execute_query("SELECT COUNT(*) as count FROM knowledge_base", fetch_one=True)

            logger.info(f"✓ {patient_count['count']} patients available")
            logger.info(f"✓ {claim_count['count']} claims available")
            logger.info(f"✓ {kb_count['count']} knowledge base documents")
        except Exception as e:
            logger.warning(f"Could not count data: {e}")

        # Generate embeddings for any seed data missing them
        try:
            result = generate_missing_embeddings()
            if result["processed"] > 0:
                logger.info(f"✓ Generated embeddings for {result['processed']} documents")
        except Exception as e:
            logger.warning(f"Could not generate embeddings on startup: {e}")
    else:
        logger.error("❌ Database connection failed")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003, log_level=settings.log_level.lower())
