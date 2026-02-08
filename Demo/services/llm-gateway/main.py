"""
LLM Gateway - Main Application
KEY DIFFERENTIATOR: Intelligent routing, caching, and cost tracking
"""
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime
import openai
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

from config import settings
from model_selector import model_selector
from cache_manager import cache_manager
from token_counter import token_counter

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="LLM Gateway",
    description="Intelligent LLM routing, caching, and cost optimization",
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

# Configure OpenAI client
openai.api_key = settings.openai_api_key
if settings.openai_organization:
    openai.organization = settings.openai_organization

# ============================================
# Prometheus Metrics
# ============================================

llm_requests_total = Counter(
    'llm_requests_total',
    'Total LLM requests',
    ['model', 'cache_hit', 'status']
)

llm_tokens_total = Counter(
    'llm_tokens_total',
    'Total tokens processed',
    ['model', 'type']  # type: input, output, cached
)

llm_cost_usd_total = Counter(
    'llm_cost_usd_total',
    'Total cost in USD',
    ['model']
)

llm_request_duration_seconds = Histogram(
    'llm_request_duration_seconds',
    'LLM request duration',
    ['model']
)

llm_cache_hit_rate = Gauge(
    'llm_cache_hit_rate',
    'Cache hit rate percentage'
)

# ============================================
# Request/Response Models
# ============================================

class CompletionRequest(BaseModel):
    """Request model for LLM completion"""
    prompt: str = Field(..., description="User prompt")
    model: Optional[str] = Field(None, description="Specific model preference")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(4000, ge=1, le=4000)
    system_prompt: Optional[str] = Field(None, description="System message")
    use_cache: bool = Field(True, description="Whether to use caching")


class CompletionResponse(BaseModel):
    """Response model for LLM completion"""
    response: str
    model_used: str
    complexity_score: float
    selection_reason: str
    tokens: Dict[str, int]
    cost: Dict[str, float]
    cache_hit: bool
    timestamp: str


class EmbeddingRequest(BaseModel):
    """Request model for embedding generation"""
    text: Optional[str] = Field(None, description="Single text to embed")
    texts: Optional[List[str]] = Field(None, description="Batch of texts to embed")


class EmbeddingResponse(BaseModel):
    """Response model for embedding generation"""
    embeddings: List[List[float]]
    model_used: str
    tokens_used: int
    cost: Dict[str, float]
    timestamp: str


# ============================================
# API Endpoints
# ============================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "LLM Gateway",
        "version": "1.0.0",
        "status": "operational",
        "features": [
            "Intelligent model selection (GPT-4 vs GPT-3.5)",
            "Redis caching (90% cost reduction)",
            "Real-time cost tracking",
            "Embedding generation (text-embedding-ada-002)",
            "Prometheus metrics"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    cache_stats = cache_manager.get_stats()

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "cache": cache_stats.get("status", "unknown"),
        "openai_configured": bool(settings.openai_api_key)
    }


@app.post("/llm/complete", response_model=CompletionResponse)
async def complete(request: CompletionRequest):
    """
    Main LLM completion endpoint

    Features:
    - Intelligent model selection
    - Redis caching
    - Cost tracking
    - Prometheus metrics
    """
    start_time = datetime.utcnow()

    try:
        # Step 1: Select optimal model
        selected_model, complexity, reason = model_selector.select_model(
            prompt=request.prompt,
            user_preference=request.model
        )

        # Step 2: Check cache
        cache_hit = False
        cached_response = None

        if request.use_cache:
            cached_response = cache_manager.get(
                prompt=request.prompt,
                model=selected_model,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )

        if cached_response:
            # Return cached response
            cache_hit = True
            logger.info("✓ Returning cached response")

            # Update metrics
            llm_requests_total.labels(
                model=selected_model,
                cache_hit="true",
                status="success"
            ).inc()

            # Update cache hit rate
            stats = cache_manager.get_stats()
            if stats.get("hit_rate"):
                llm_cache_hit_rate.set(stats["hit_rate"])

            return CompletionResponse(**cached_response)

        # Step 3: Call OpenAI API
        logger.info(f"Calling OpenAI with model: {selected_model}")

        # Prepare messages
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        # Count input tokens
        input_tokens = token_counter.count_messages_tokens(messages)

        # Make API call
        try:
            response = openai.chat.completions.create(
                model=selected_model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )

            # Extract response
            completion_text = response.choices[0].message.content
            output_tokens = response.usage.completion_tokens

        except openai.AuthenticationError as e:
            logger.error(f"OpenAI authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="OpenAI API authentication failed. Check API key."
            )
        except openai.RateLimitError as e:
            logger.error(f"OpenAI rate limit: {e}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="OpenAI rate limit exceeded. Please try again later."
            )
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"LLM API error: {str(e)}"
            )

        # Step 4: Calculate cost
        cost_info = token_counter.calculate_cost(
            model=selected_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )

        # Step 5: Build response
        response_data = {
            "response": completion_text,
            "model_used": selected_model,
            "complexity_score": complexity,
            "selection_reason": reason,
            "tokens": {
                "input": input_tokens,
                "output": output_tokens,
                "total": input_tokens + output_tokens
            },
            "cost": cost_info,
            "cache_hit": False,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Step 6: Cache response
        if request.use_cache:
            cache_manager.set(
                prompt=request.prompt,
                model=selected_model,
                response_data=response_data,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )

        # Step 7: Update metrics
        duration = (datetime.utcnow() - start_time).total_seconds()

        llm_requests_total.labels(
            model=selected_model,
            cache_hit="false",
            status="success"
        ).inc()

        llm_tokens_total.labels(model=selected_model, type="input").inc(input_tokens)
        llm_tokens_total.labels(model=selected_model, type="output").inc(output_tokens)

        llm_cost_usd_total.labels(model=selected_model).inc(cost_info["total_cost"])

        llm_request_duration_seconds.labels(model=selected_model).observe(duration)

        logger.info(
            f"✓ Completed: {selected_model} | "
            f"Tokens: {input_tokens}+{output_tokens} | "
            f"Cost: ${cost_info['total_cost']:.4f} | "
            f"Duration: {duration:.2f}s"
        )

        return CompletionResponse(**response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)

        llm_requests_total.labels(
            model="unknown",
            cache_hit="false",
            status="error"
        ).inc()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/llm/embed", response_model=EmbeddingResponse)
async def embed(request: EmbeddingRequest):
    """
    Generate embeddings for text using OpenAI ada-002

    Supports single text or batch embedding.
    Used by RAG pipeline for knowledge base indexing and query embedding.
    """
    start_time = datetime.utcnow()

    # Validate input
    if not request.text and not request.texts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'text' or 'texts' must be provided"
        )

    # Normalize to list
    input_texts = request.texts if request.texts else [request.text]

    try:
        response = openai.embeddings.create(
            model=settings.embedding_model,
            input=input_texts
        )

        embeddings = [item.embedding for item in response.data]
        tokens_used = response.usage.total_tokens

        # Calculate cost
        cost_per_token = settings.embedding_cost_per_1k_tokens / 1000
        total_cost = tokens_used * cost_per_token

        # Update metrics
        duration = (datetime.utcnow() - start_time).total_seconds()

        llm_requests_total.labels(
            model=settings.embedding_model,
            cache_hit="false",
            status="success"
        ).inc()

        llm_tokens_total.labels(
            model=settings.embedding_model,
            type="input"
        ).inc(tokens_used)

        llm_cost_usd_total.labels(
            model=settings.embedding_model
        ).inc(total_cost)

        llm_request_duration_seconds.labels(
            model=settings.embedding_model
        ).observe(duration)

        logger.info(
            f"✓ Embedding: {len(input_texts)} text(s) | "
            f"Tokens: {tokens_used} | "
            f"Cost: ${total_cost:.6f} | "
            f"Duration: {duration:.2f}s"
        )

        return EmbeddingResponse(
            embeddings=embeddings,
            model_used=settings.embedding_model,
            tokens_used=tokens_used,
            cost={
                "input_cost": total_cost,
                "total_cost": total_cost
            },
            timestamp=datetime.utcnow().isoformat()
        )

    except openai.AuthenticationError as e:
        logger.error(f"OpenAI authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OpenAI API authentication failed. Check API key."
        )
    except Exception as e:
        logger.error(f"Embedding error: {e}", exc_info=True)

        llm_requests_total.labels(
            model=settings.embedding_model,
            cache_hit="false",
            status="error"
        ).inc()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Embedding generation failed: {str(e)}"
        )


@app.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics"""
    stats = cache_manager.get_stats()
    return stats


@app.post("/cache/invalidate")
async def invalidate_cache(pattern: str = "llm:cache:*"):
    """Invalidate cache entries"""
    deleted = cache_manager.invalidate(pattern)
    return {
        "status": "success",
        "deleted_keys": deleted,
        "pattern": pattern
    }


@app.get("/models")
async def list_models():
    """List available models with metadata"""
    return {
        "models": [
            model_selector.get_model_info(settings.gpt4_turbo_model),
            model_selector.get_model_info(settings.gpt35_turbo_model)
        ],
        "default_selection": "Automatic based on complexity",
        "complexity_thresholds": {
            "high": settings.complexity_threshold_high,
            "medium": settings.complexity_threshold_medium
        }
    }


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
    logger.info("LLM Gateway Starting...")
    logger.info("=" * 50)
    logger.info(f"GPT-4 Model: {settings.gpt4_turbo_model}")
    logger.info(f"GPT-3.5 Model: {settings.gpt35_turbo_model}")
    logger.info(f"Embedding Model: {settings.embedding_model}")
    logger.info(f"Cache TTL: {settings.cache_ttl_seconds}s")
    logger.info(f"Redis: {settings.redis_url}")
    logger.info(f"Prometheus: {'Enabled' if settings.prometheus_enabled else 'Disabled'}")
    logger.info("=" * 50)

    # Test Redis connection
    cache_stats = cache_manager.get_stats()
    if cache_stats.get("status") == "connected":
        logger.info("✓ Cache operational")
    else:
        logger.warning("⚠ Cache disabled - responses will not be cached")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002, log_level=settings.log_level.lower())
