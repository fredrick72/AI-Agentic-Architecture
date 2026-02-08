# AI-Agentic Architecture - Local Demo

A complete containerized demonstration of AI-Agentic Architecture showcasing the **key differentiators** that separate AI agents from traditional applications.

## 🎯 Key Differentiators

### 1. **LLM Gateway** - Intelligent Routing & Cost Optimization
- **Model Selection**: Routes complex queries to GPT-4, simple to GPT-3.5
- **Prompt Caching**: 90% cost reduction on repeated queries
- **Cost Tracking**: Real-time metrics for every request
- **Fallback**: Graceful degradation when primary LLM unavailable

### 2. **Clarification Engine** - Collaborative Problem Solving
- **Entity Disambiguation**: Ambiguous queries trigger interactive UI (not errors)
- **Conversational**: Agent asks follow-up questions naturally
- **No Dead Ends**: System always offers paths forward

### 3. **RAG Knowledge Base** - Semantic Search with pgvector
- **Vector Embeddings**: Documents embedded via OpenAI ada-002 (1536 dimensions)
- **Semantic Search**: Agent retrieves relevant knowledge using cosine similarity
- **Tool-Based**: RAG is an explicit tool call (`search_knowledge`), visible in the reasoning chain
- **Auto-Embedding**: Seed documents embedded on startup; new docs embedded on insert

### 4. **Iterative Reasoning** - Multi-Step Tool Execution
- Agent decomposes complex queries into tool chains
- Adaptive execution based on context
- Full reasoning trace visible in observability stack

## 📋 Prerequisites

- **Docker Desktop** (or Docker Engine + Docker Compose)
- **OpenAI API Key** ([Get one here](https://platform.openai.com/api-keys))
- **Minimum**: 8GB RAM, 4 CPU cores
- **Recommended**: 16GB RAM, 8 CPU cores

## 🚀 Quick Start

### 1. Clone and Navigate

```bash
cd Demo/
```

### 2. Configure Environment

```bash
# Copy the environment template
cp .env.example .env

# Edit .env and add your OpenAI API key
# Windows: notepad .env
# Mac/Linux: nano .env
```

Update this line in `.env`:
```env
OPENAI_API_KEY=sk-your-actual-api-key-here
```

### 3. Start All Services

```bash
# Build and start all containers
docker compose up -d --build

# Wait for services to be healthy (2-3 minutes)
docker compose ps
```

### 4. Verify Services

```bash
# Check Traefik dashboard
curl http://localhost:8080/dashboard/

# Check LLM Gateway health
curl http://localhost:8002/health

# Check database
docker compose exec postgres psql -U postgres -d agent_db -c "\dt"
```

### 5. Access UIs

- **Frontend**: http://localhost:5173
- **Grafana**: http://localhost:3000 (admin/admin)
- **Traefik Dashboard**: http://localhost:8080
- **Prometheus**: http://localhost:9090

## 🧪 Demo Scenarios

### Scenario 1: Simple Query (Traditional Flow)

```bash
curl -X POST http://localhost/api/agent/query \
  -H "Content-Type: application/json" \
  -d '{"message": "How many claims does patient PAT-12345 have?"}'
```

**Expected**: Direct answer with cost tracking

---

### Scenario 2: Ambiguous Query (Clarification Engine ⭐)

**Via Frontend**:
1. Open http://localhost:5173
2. Type: "Find claims for John"
3. **See clarification widget with 3 options** (not an error!)
4. Select "John Smith"
5. See results

**Via API**:
```bash
curl -X POST http://localhost/api/agent/query \
  -H "Content-Type: application/json" \
  -d '{"message": "Find claims for John"}'
```

**Expected Response**:
```json
{
  "type": "clarification_needed",
  "data": {
    "question": "I found 3 patients named John. Which one?",
    "options": [
      {
        "id": "PAT-12345",
        "label": "John Smith (ID: PAT-12345)",
        "metadata": {"last_visit": "2024-01-15"}
      },
      {
        "id": "PAT-67890",
        "label": "John Doe (ID: PAT-67890)",
        "metadata": {"last_visit": "2023-11-20"}
      },
      {
        "id": "PAT-24680",
        "label": "John Williams (ID: PAT-24680)",
        "metadata": {"last_visit": "2024-02-05"}
      }
    ]
  }
}
```

**Traditional System**: Would return `400 Bad Request - Ambiguous query` ❌
**AI-Agentic System**: Continues conversation with clarification ✅

---

### Scenario 3: Multi-Step Reasoning

```bash
curl -X POST http://localhost/api/agent/query \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the total claim amount for John Smith?"}'
```

**Reasoning Chain**:
1. Calls `query_patients("John Smith")` → Returns patient_id PAT-12345
2. Calls `get_claims(patient_id=PAT-12345)` → Returns 5 claims
3. Calls `calculate_total(claim_ids)` → Returns $12,450.50
4. Synthesizes natural language response

**Check Reasoning in Logs**:
```bash
docker compose logs -f agent-runtime | grep "Tool call"
```

---

### Scenario 4: Knowledge Base Search (⭐ RAG)

```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"message": "What does diagnosis code S83.5 mean?"}'
```

**Reasoning Chain**:
1. LLM recognizes this is a knowledge question
2. Calls `search_knowledge(query="diagnosis code S83.5")` → Finds matching ICD-10 document
3. Synthesizes answer citing the source document

**Expected**: Agent explains S83.5 is a sprain of the cruciate ligament (ACL/PCL) of the knee, with treatment options and related claim types.

**More RAG queries to try**:
```bash
# Policy question
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"message": "Does my insurance cover cosmetic teeth whitening?"}'

# Multi-step with RAG: combines patient lookup + knowledge search
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"message": "What is John Williams being treated for and what does his diagnosis mean?"}'
```

**Knowledge Base Stats**:
```bash
curl http://localhost:8003/knowledge/stats
```

---

### Scenario 5: LLM Gateway - Caching (⭐ Cost Optimization)

```bash
# First request - Cache miss
curl -X POST http://localhost/api/llm/complete \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is 2+2?"}'

# Expected: cache_hit=false, cost=~$0.001

# Second identical request - Cache hit
curl -X POST http://localhost/api/llm/complete \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is 2+2?"}'

# Expected: cache_hit=true, cost=~$0.0001 (90% savings!)
```

**Check Cache Hit Rate**:
```bash
curl http://localhost:8002/metrics | grep cache_hit
```

---

### Scenario 6: Model Selection (⭐ Intelligent Routing)

```bash
# Simple query - Uses GPT-3.5 Turbo (cheaper)
curl -X POST http://localhost/api/llm/complete \
  -d '{"prompt": "What is 2+2?"}'
# Cost: ~$0.001

# Complex query - Uses GPT-4 Turbo (smarter)
curl -X POST http://localhost/api/llm/complete \
  -d '{"prompt": "Explain the philosophical implications of quantum entanglement on free will"}'
# Cost: ~$0.05
```

**View Model Distribution** in Grafana:
- Open http://localhost:3000
- Navigate to "LLM Gateway" dashboard
- See pie chart of model usage

## 📊 Observability

### Grafana Dashboards

**LLM Gateway Dashboard** (http://localhost:3000):
- Model usage distribution (GPT-4 vs GPT-3.5)
- Cache hit rate over time
- Cost per request trends
- Token usage metrics

**Agent Overview Dashboard**:
- Request rate
- Success/failure rates
- Average cost per request
- Reasoning iterations

### Prometheus Metrics

```bash
# View raw metrics
curl http://localhost:9090

# Key metrics:
# - llm_requests_total{model, cache_hit}       (includes embedding requests)
# - llm_tokens_total{model, type}              (includes embedding tokens)
# - llm_cost_usd_total{model}                  (includes embedding costs)
# - tool_executions_total{tool_name, status}   (includes search_knowledge)
# - agent_reasoning_iterations
# - clarification_rate
```

### Logs

```bash
# View all logs
docker compose logs -f

# Specific service logs
docker compose logs -f agent-runtime
docker compose logs -f llm-gateway
docker compose logs -f clarification-engine
```

## 🏗️ Architecture

```
┌─────────────┐
│  Frontend   │ ← React UI (port 5173)
└──────┬──────┘
       │
┌──────▼──────┐
│Agent Runtime│ ← Orchestrator (port 8001)
└──┬──┬──┬────┘
   │  │  │
   │  │  └──────────────────────────────────┐
   │  │                                     │
   │  ▼                                     ▼
   │  ┌──────────────────┐  ┌───────────────────────┐
   │  │   LLM Gateway    │  │  Clarification Engine  │
   │  │    (port 8002)   │  │     (port 8004)        │
   │  │ ● Model routing  │  └───────────┬────────────┘
   │  │ ● Caching        │              │
   │  │ ● Embeddings     │         ┌────▼────┐
   │  └────────┬─────────┘         │PostgreSQL│
   │           │                   │+pgvector │
   │    ┌──────▼──────┐            └────┬─────┘
   │    │    Redis     │                │
   │    │ Prompt cache │           ┌────▼──────────┐
   │    └─────────────┘            │ knowledge_base │
   │                               │ (RAG vectors)  │
   ▼                               └───────────────┘
┌────────────────┐
│ Tool Registry  │ ← port 8003
│ (port 8003)    │
│ ● query_patients    │
│ ● get_claims        │
│ ● calculate_total   │
│ ● search_knowledge  │ ← RAG tool (calls LLM Gateway for embeddings)
└────────────────┘

Observability: Prometheus (9090) + Grafana (3000)
```

## 🛠️ Development

### Running Individual Services

```bash
# Start only infrastructure
docker compose up -d postgres redis traefik prometheus grafana

# Start LLM Gateway
docker compose up -d llm-gateway

# View logs in real-time
docker compose logs -f llm-gateway
```

### Rebuilding After Code Changes

```bash
# Rebuild specific service
docker compose up -d --build llm-gateway

# Rebuild all services
docker compose up -d --build
```

### Database Access

```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U postgres -d agent_db

# Run SQL queries
docker compose exec postgres psql -U postgres -d agent_db -c "SELECT * FROM patients WHERE first_name='John';"

# Reset database (WARNING: deletes all data)
docker compose down -v
docker compose up -d
```

### Knowledge Base Management

```bash
# Check knowledge base stats
curl http://localhost:8003/knowledge/stats

# Add a new document (auto-generates embedding)
curl -X POST http://localhost:8003/knowledge/add \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Physical Therapy Coverage",
    "content": "Physical therapy is covered for up to 20 sessions per year...",
    "category": "policy",
    "tags": ["physical therapy", "coverage"]
  }'

# Re-generate embeddings for any documents missing them
curl -X POST http://localhost:8003/knowledge/embed-all

# Test embedding endpoint directly
curl -X POST http://localhost:8002/llm/embed \
  -H "Content-Type: application/json" \
  -d '{"text": "knee surgery recovery"}'
```

### Redis Cache Management

```bash
# Connect to Redis CLI
docker compose exec redis redis-cli

# View all keys
docker compose exec redis redis-cli KEYS "*"

# Clear cache
docker compose exec redis redis-cli FLUSHALL

# Check cache stats
docker compose exec redis redis-cli INFO stats
```

## 📁 Project Structure

```
Demo/
├── docker-compose.yml          # Main orchestration
├── .env.example                # Environment template
├── README.md                   # This file
│
├── services/
│   ├── agent-runtime/          # Main orchestrator
│   │   └── orchestrator.py     #   Reasoning loop + system prompt
│   ├── llm-gateway/            # LLM routing, caching & embeddings
│   │   └── main.py             #   /llm/complete + /llm/embed endpoints
│   ├── clarification-engine/   # Ambiguity handler
│   └── tool-registry/          # Tool execution + knowledge management
│       ├── main.py             #   Tool routing + /knowledge/* admin endpoints
│       └── tools/
│           ├── query_patients.py
│           ├── get_claims.py
│           ├── calculate_total.py
│           ├── search_knowledge.py   # RAG: vector similarity search
│           └── manage_knowledge.py   # Document add + embedding generation
│
├── frontend/                   # React UI
│
├── config/
│   ├── traefik/                # API gateway config
│   ├── prometheus/             # Metrics collection
│   ├── grafana/                # Dashboards
│   └── postgres/
│       ├── init.sql            # Schema (incl. knowledge_base + pgvector)
│       ├── seed-data.sql       # Patients + claims
│       └── seed-knowledge.sql  # RAG knowledge documents (15 docs)
│
└── scripts/                    # Helper scripts
```

## 🎥 Stakeholder Demo Script (15 minutes)

### Part 1: The Problem (2 min)
"Traditional apps break on ambiguity..."

1. Show simulated traditional API:
   ```bash
   # Traditional API behavior
   curl http://localhost/api/agent/query -d '{"message": "Find claims for John"}'
   # Without clarification engine: Would return 400 error
   ```

2. "User is stuck. Dead end."

### Part 2: Our Solution (5 min)
"AI-agentic architecture turns errors into conversations."

1. Open frontend: http://localhost:5173
2. Type: "Find claims for John"
3. **Show clarification widget**
4. Select patient
5. Results appear

"No error. Collaboration."

### Part 3: Knowledge Retrieval - RAG (3 min)
"The agent doesn't just query data — it understands domain knowledge."

1. Ask: "What does diagnosis code S83.5 mean?"
2. Show the reasoning chain: agent calls `search_knowledge` tool
3. Show knowledge base stats: `curl http://localhost:8003/knowledge/stats`
4. Ask: "Does my insurance cover cosmetic teeth whitening?"
5. "Agent found the dental policy and cited it."

### Part 4: The Intelligence (3 min)
"Look under the hood."

1. Open Grafana: http://localhost:3000
2. Show:
   - Model distribution (GPT-4 vs GPT-3.5)
   - Cache hit rate climbing
   - Cost tracking (including embedding costs)

### Part 5: Multi-Step Reasoning (2 min)
1. Query: "Total amount for John Smith?"
2. Show logs: 3 tool calls
3. "Agent decomposed the query."

### Part 6: The Differentiators (2 min)
1. **LLM Gateway**: Routing, caching, embeddings, cost tracking
2. **Clarification Engine**: Errors → Conversations
3. **RAG**: Domain knowledge retrieval via semantic search

### Part 7: Architecture (1 min)
1. Show docker-compose.yml
2. "9 microservices, fully containerized"
3. "Scales to cloud with minimal changes"

## 🧹 Cleanup

```bash
# Stop all containers
docker compose down

# Stop and remove volumes (WARNING: deletes data)
docker compose down -v

# Remove images
docker compose down --rmi all
```

## 🐛 Troubleshooting

### Issue: "Port already in use"

```bash
# Find process using port 80
# Windows:
netstat -ano | findstr :80

# Mac/Linux:
lsof -i :80

# Change ports in docker-compose.yml if needed
```

### Issue: "OpenAI API rate limit"

- Check `.env` has valid `OPENAI_API_KEY`
- Wait 1 minute between requests (free tier has limits)
- Upgrade to paid tier if needed

### Issue: "Services unhealthy"

```bash
# Check service status
docker compose ps

# View specific service logs
docker compose logs llm-gateway

# Restart services
docker compose restart
```

### Issue: "Database not initialized"

```bash
# Manually run init scripts
docker compose exec postgres psql -U postgres -d agent_db -f /docker-entrypoint-initdb.d/01-init.sql
docker compose exec postgres psql -U postgres -d agent_db -f /docker-entrypoint-initdb.d/02-seed.sql
docker compose exec postgres psql -U postgres -d agent_db -f /docker-entrypoint-initdb.d/03-seed-knowledge.sql
```

### Issue: "Knowledge base has no embeddings"

```bash
# Embeddings are generated on tool-registry startup. Trigger manually:
curl -X POST http://localhost:8003/knowledge/embed-all

# Verify embeddings exist:
docker compose exec postgres psql -U postgres -d agent_db \
  -c "SELECT doc_id, title, (embedding IS NOT NULL) as has_embedding FROM knowledge_base;"
```

## 📚 Next Steps

After mastering the current demo, consider:

1. ~~**Add RAG**~~: ✅ Implemented — pgvector embeddings with `search_knowledge` tool
2. **Advanced Clarification**: Parameter elicitation, constraint negotiation
3. **Jaeger Tracing**: Visual reasoning chains
4. **Ollama Fallback**: Local LLM as backup
5. **Deploy to Cloud**: Azure Container Apps or AWS ECS

## 📄 License

This is a demonstration project for educational purposes.

## 🤝 Contributing

Feedback and improvements welcome! Open an issue or PR.

---

**Built with**: FastAPI, PostgreSQL + pgvector, Redis, React, Traefik, Prometheus, Grafana, OpenAI
