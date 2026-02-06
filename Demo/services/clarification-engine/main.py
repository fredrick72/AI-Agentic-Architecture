"""
Clarification Engine - Main Application
Handles ambiguous requests and generates interactive clarification UI
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
from intent_analyzer import IntentAnalyzer
from entity_matcher import EntityMatcher
from ui_generator import UIGenerator

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Clarification Engine",
    description="Converts errors into collaborative conversations: entity disambiguation, parameter elicitation, constraint negotiation",
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
intent_analyzer = IntentAnalyzer()
entity_matcher = EntityMatcher()
ui_generator = UIGenerator()

# ============================================
# Prometheus Metrics
# ============================================

clarification_requests_total = Counter(
    'clarification_requests_total',
    'Total clarification requests',
    ['clarification_type', 'resolved']
)

clarification_analysis_duration_seconds = Histogram(
    'clarification_analysis_duration_seconds',
    'Clarification analysis duration',
    ['analysis_type']
)

# ============================================
# Request/Response Models
# ============================================

class AnalyzeRequest(BaseModel):
    """Request to analyze user input for ambiguity"""
    user_input: str = Field(..., description="User's message or query")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Conversation context")


class AnalyzeResponse(BaseModel):
    """Response from ambiguity analysis"""
    needs_clarification: bool
    clarification_type: Optional[str] = None  # entity_disambiguation, parameter_elicitation, etc.
    ui_schema: Optional[Dict[str, Any]] = None
    intent_data: Dict[str, Any]
    metadata: Dict[str, Any]


class ProcessClarificationRequest(BaseModel):
    """User's response to clarification request"""
    clarification_type: str = Field(..., description="Type of clarification")
    user_selection: Dict[str, Any] = Field(..., description="User's selection/input")
    original_intent: Dict[str, Any] = Field(..., description="Original intent data")


class ProcessClarificationResponse(BaseModel):
    """Processed clarification response"""
    resolved: bool
    resolved_parameters: Dict[str, Any]
    ready_for_execution: bool
    metadata: Dict[str, Any]


class ValidateEntityRequest(BaseModel):
    """Request to validate an entity"""
    entity_type: str = Field(..., description="Type of entity")
    entity_value: str = Field(..., description="Value to validate")


class ValidateEntityResponse(BaseModel):
    """Entity validation response"""
    valid: bool
    unique: bool
    matches: List[Dict[str, Any]]
    ui_schema: Optional[Dict[str, Any]] = None


# ============================================
# API Endpoints
# ============================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Clarification Engine",
        "version": "1.0.0",
        "status": "operational",
        "description": "Converts errors into conversations"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db_connected = db.test_connection()

    return {
        "status": "healthy" if db_connected else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected" if db_connected else "disconnected",
        "llm_gateway": settings.llm_gateway_url
    }


@app.post("/clarify/analyze", response_model=AnalyzeResponse)
async def analyze_for_clarification(request: AnalyzeRequest):
    """
    Analyze user input to detect if clarification is needed

    Flow:
    1. Use IntentAnalyzer to understand intent and extract entities
    2. If low confidence or ambiguous entities, use EntityMatcher to find options
    3. Generate UI schema with UIGenerator
    4. Return clarification request or proceed signal

    Example:
        User: "Find claims for John"
        → Detects ambiguity (3 patients named John)
        → Returns UI schema with radio buttons
    """
    start_time = datetime.utcnow()

    try:
        logger.info(f"Analyzing: {request.user_input[:100]}...")

        # Step 1: Analyze intent
        with clarification_analysis_duration_seconds.labels(analysis_type="intent").time():
            intent_data = intent_analyzer.analyze_intent(
                request.user_input,
                request.context
            )

        # Step 2: Check if clarification needed
        if not intent_data["needs_clarification"]:
            logger.info("✓ No clarification needed, confidence high")

            return AnalyzeResponse(
                needs_clarification=False,
                intent_data=intent_data,
                metadata={
                    "confidence": intent_data["confidence"],
                    "analysis_time_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000)
                }
            )

        # Step 3: Handle ambiguous entities
        clarification_type = None
        ui_schema = None

        ambiguous_entities = intent_data.get("ambiguous_entities", [])

        if ambiguous_entities:
            # Focus on first ambiguous entity
            ambiguous_entity = ambiguous_entities[0]

            # Find matching entities
            entity_value = next(
                (e["value"] for e in intent_data["entities"] if e["type"] == ambiguous_entity),
                None
            )

            if entity_value:
                with clarification_analysis_duration_seconds.labels(analysis_type="entity_matching").time():
                    # Entity disambiguation
                    if ambiguous_entity in ["patient_name", "patient"]:
                        matches = entity_matcher.find_patient_matches(
                            entity_value,
                            request.context
                        )

                        if len(matches) > 1:
                            clarification_type = "entity_disambiguation"
                            ui_schema = ui_generator.generate_disambiguation_ui(
                                entity_type="patient",
                                question=f"I found {len(matches)} patients matching '{entity_value}'. Which one do you mean?",
                                options=matches,
                                allow_multiple=False
                            )

                        elif len(matches) == 1:
                            # Only one match, auto-resolve
                            logger.info(f"Auto-resolving to single match: {matches[0]['id']}")
                            intent_data["resolved_entity"] = matches[0]
                            intent_data["needs_clarification"] = False

                        else:
                            # No matches
                            raise HTTPException(
                                status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"No patients found matching '{entity_value}'"
                            )

                    elif ambiguous_entity in ["claim_name", "claim"]:
                        # Similar logic for claims
                        clarification_type = "entity_disambiguation"
                        ui_schema = ui_generator.generate_disambiguation_ui(
                            entity_type="claim",
                            question=f"Multiple claims found. Please select one:",
                            options=[],  # Would need claim matching logic
                            allow_multiple=False
                        )

        # If still needs clarification after entity matching
        if intent_data["needs_clarification"] and not ui_schema:
            # Parameter elicitation (missing required parameters)
            clarification_type = "parameter_elicitation"

            # Determine missing parameter based on intent
            if intent_data["intent"] == "get_claims":
                ui_schema = ui_generator.generate_parameter_elicitation_ui(
                    parameter_name="status",
                    question="Which claim statuses would you like to see?",
                    parameter_type="array",
                    suggestions=["pending", "approved", "denied"],
                    required=False
                )

        # Update metrics
        clarification_requests_total.labels(
            clarification_type=clarification_type or "none",
            resolved=str(not intent_data["needs_clarification"])
        ).inc()

        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        logger.info(
            f"✓ Analysis complete: needs_clarification={intent_data['needs_clarification']}, "
            f"type={clarification_type}, duration={duration_ms}ms"
        )

        return AnalyzeResponse(
            needs_clarification=intent_data["needs_clarification"],
            clarification_type=clarification_type,
            ui_schema=ui_schema,
            intent_data=intent_data,
            metadata={
                "confidence": intent_data["confidence"],
                "analysis_time_ms": duration_ms,
                "ambiguous_entities": ambiguous_entities
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


@app.post("/clarify/process", response_model=ProcessClarificationResponse)
async def process_clarification_response(request: ProcessClarificationRequest):
    """
    Process user's response to clarification request

    Takes user's selection and merges it with original intent

    Example:
        User selected: John Smith (PAT-12345)
        Original intent: "Find claims for John"
        → Resolved: "Find claims for patient PAT-12345"
    """
    try:
        logger.info(f"Processing clarification: {request.clarification_type}")

        # Format user selection
        formatted_response = ui_generator.format_clarification_response(
            request.clarification_type,
            request.user_selection
        )

        if not formatted_response.get("resolved"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Clarification not properly resolved"
            )

        # Merge with original intent
        resolved_parameters = {}

        if request.clarification_type == "entity_disambiguation":
            entity_type = formatted_response["entity_type"]
            resolved_value = formatted_response["resolved_value"]

            # Map entity type to parameter name
            if entity_type == "patient":
                resolved_parameters["patient_id"] = resolved_value
            elif entity_type == "claim":
                resolved_parameters["claim_id"] = resolved_value

        elif request.clarification_type == "parameter_elicitation":
            param_name = formatted_response["parameter_name"]
            param_value = formatted_response["resolved_value"]
            resolved_parameters[param_name] = param_value

        # Check if ready for execution
        intent = request.original_intent.get("intent")
        ready_for_execution = self._check_ready_for_execution(intent, resolved_parameters)

        # Update metrics
        clarification_requests_total.labels(
            clarification_type=request.clarification_type,
            resolved="true"
        ).inc()

        logger.info(f"✓ Clarification processed: {resolved_parameters}")

        return ProcessClarificationResponse(
            resolved=True,
            resolved_parameters=resolved_parameters,
            ready_for_execution=ready_for_execution,
            metadata={
                "clarification_type": request.clarification_type,
                "additional_context": formatted_response.get("additional_context", {})
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Processing error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed: {str(e)}"
        )


@app.post("/clarify/validate", response_model=ValidateEntityResponse)
async def validate_entity(request: ValidateEntityRequest):
    """
    Validate an entity value (check if exists and is unambiguous)

    Used by Agent Runtime before executing tools

    Example:
        Validate patient_id "PAT-12345"
        → Returns: valid=True, unique=True
    """
    try:
        logger.info(f"Validating {request.entity_type}: {request.entity_value}")

        validation_result = entity_matcher.validate_entity(
            request.entity_type,
            request.entity_value
        )

        # If multiple matches, generate disambiguation UI
        ui_schema = None
        if validation_result["valid"] and not validation_result["unique"]:
            matches = validation_result["matches"]

            if request.entity_type in ["patient_id", "patient_name"]:
                ui_schema = ui_generator.generate_disambiguation_ui(
                    entity_type="patient",
                    question=f"Multiple patients found matching '{request.entity_value}'. Please select one:",
                    options=matches,
                    allow_multiple=False
                )

        logger.info(
            f"✓ Validation: valid={validation_result['valid']}, "
            f"unique={validation_result['unique']}, "
            f"matches={len(validation_result['matches'])}"
        )

        return ValidateEntityResponse(
            valid=validation_result["valid"],
            unique=validation_result["unique"],
            matches=validation_result["matches"],
            ui_schema=ui_schema
        )

    except Exception as e:
        logger.error(f"Validation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}"
        )


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# ============================================
# Helper Methods
# ============================================

def _check_ready_for_execution(intent: str, resolved_parameters: Dict[str, Any]) -> bool:
    """
    Check if we have all required parameters for tool execution

    Args:
        intent: Tool name
        resolved_parameters: Parameters we've resolved so far

    Returns:
        True if ready to execute tool
    """
    # Define required parameters for each intent
    required_params = {
        "query_patients": ["name"],
        "get_claims": ["patient_id"],
        "calculate_total": ["claim_ids"]
    }

    required = required_params.get(intent, [])

    # Check if all required params are present
    for param in required:
        if param not in resolved_parameters:
            # Check aliases
            if param == "name" and "patient_id" in resolved_parameters:
                continue  # patient_id can substitute for name
            return False

    return True


# ============================================
# Startup Event
# ============================================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("=" * 50)
    logger.info("Clarification Engine Starting...")
    logger.info("=" * 50)
    logger.info(f"Database: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}")
    logger.info(f"LLM Gateway: {settings.llm_gateway_url}")
    logger.info(f"Confidence thresholds: {settings.confidence_threshold_low:.2f} - {settings.confidence_threshold_high:.2f}")
    logger.info("=" * 50)

    # Test database connection
    if db.test_connection():
        logger.info("✓ Database connected")
    else:
        logger.error("❌ Database connection failed")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004, log_level=settings.log_level.lower())
