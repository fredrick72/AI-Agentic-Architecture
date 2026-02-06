# AI-Agentic-Architecture-Azure

# Main
```mermaid
graph TB
    %% Styling
    classDef azure fill:#0078D4,stroke:#005A9E,stroke-width:3px,color:#fff
    classDef aiml fill:#7B68EE,stroke:#5a4db8,stroke-width:3px,color:#fff
    classDef data fill:#2E8B57,stroke:#1e5a3a,stroke-width:3px,color:#fff
    classDef security fill:#DC143C,stroke:#a00f2b,stroke-width:3px,color:#fff
    classDef integration fill:#FF8C00,stroke:#cc7000,stroke-width:3px,color:#fff
    classDef observability fill:#4682B4,stroke:#335f85,stroke-width:3px,color:#fff
    
    %% Entry Layer
    APIM["API Gateway (APIM)<br/>Auth • Rate Limiting • Logging"]
    
    %% Orchestration Layer
    AgentRuntime["Agent Runtime<br/>Azure Container Apps<br/>━━━━━━━━━<br/>• Auto-scale 0→N<br/>• GPU node pools<br/>• Managed Identity"]
    LLMGateway{"LLM Gateway<br/>━━━━━━━━━<br/>⭐ KEY DIFFERENTIATOR<br/>Routing • Caching • Fallback"}
    ToolRegistry["Tool Registry<br/>Azure Functions<br/>━━━━━━━━━<br/>• Database queries<br/>• API integrations<br/>• File operations"]
    
    %% AI/ML Services
    OpenAI["Azure OpenAI<br/>GPT-4 • GPT-3.5"]
    AISearch["Azure AI Search<br/>Vector Search • RAG"]
    ContentSafety["Content Safety API<br/>Filter • PII Detection"]
    
    %% Data Layer
    CosmosDB[("Cosmos DB<br/>━━━━━━━━━<br/>• Vector search<br/>• Conversation history<br/>• Agent memory")]
    Redis[("Redis Enterprise<br/>━━━━━━━━━<br/>• Working memory<br/>• Tool result cache<br/>• Session state")]
    
    %% Security
    KeyVault["Key Vault<br/>Secrets • Keys"]
    
    %% Integration Services
    DurableFuncs["Durable Functions<br/>Multi-step orchestration"]
    EventGrid["Event Grid<br/>Event-driven triggers"]
    
    %% Observability
    AppInsights["Application Insights<br/>━━━━━━━━━<br/>• Semantic tracing<br/>• Token usage metrics<br/>• Cost attribution"]
    Monitor["Azure Monitor<br/>━━━━━━━━━<br/>• Budget alerts<br/>• Performance metrics"]
    
    %% Primary Flows
    APIM -->|"Agent requests"| AgentRuntime
    APIM -->|"Tool invocations"| ToolRegistry
    AgentRuntime ==>|"Prompt routing"| LLMGateway
    LLMGateway -->|"1. Primary LLM"| OpenAI
    LLMGateway -.->|"2. Fallback"| ExternalModels["External Models<br/>Claude • Local"]
    AgentRuntime <-->|"State • Memory"| CosmosDB
    AgentRuntime <-->|"RAG retrieval"| AISearch
    AgentRuntime -->|"Cache read/write"| Redis
    ToolRegistry -.->|"Data operations"| CosmosDB
    ToolRegistry -.->|"Tool results"| AgentRuntime
    
    %% Security Flows
    AgentRuntime -.->|"Secrets retrieval"| KeyVault
    LLMGateway -.->|"Input/output filtering"| ContentSafety
    ToolRegistry -.->|"Secrets"| KeyVault
    
    %% Integration Flows
    EventGrid -.->|"Triggers"| AgentRuntime
    AgentRuntime -.->|"Long-running workflows"| DurableFuncs
    
    %% Observability Flows
    AgentRuntime -.->|"Traces • Logs"| AppInsights
    LLMGateway -.->|"Token metrics"| AppInsights
    OpenAI -.->|"API logs"| AppInsights
    AgentRuntime -.->|"Metrics"| Monitor
    LLMGateway -.->|"Metrics"| Monitor
    OpenAI -.->|"Metrics"| Monitor
    CosmosDB -.->|"Metrics"| Monitor
    
    %% Apply Styles
    class APIM integration
    class AgentRuntime,ToolRegistry azure
    class LLMGateway,OpenAI,AISearch aiml
    class CosmosDB,Redis data
    class KeyVault,ContentSafety security
    class DurableFuncs,EventGrid integration
    class AppInsights,Monitor observability
```
# RequestRoute
```mermaid
sequenceDiagram
    autonumber
    participant User
    participant APIM as API Gateway
    participant Agent as Agent Runtime
    participant Gateway as LLM Gateway
    participant OpenAI as Azure OpenAI
    participant Tools as Tool Registry
    participant Cosmos as Cosmos DB
    participant Search as AI Search
    participant Safety as Content Safety
    participant Insights as App Insights
    
    User->>APIM: Request: "Find recent claims for patient X"
    APIM->>APIM: Authenticate & Rate Limit
    APIM->>Agent: Forward request
    
    Agent->>Safety: Check input for PII/harmful content
    Safety-->>Agent: ✓ Safe
    
    Agent->>Cosmos: Load conversation history
    Cosmos-->>Agent: Previous context
    
    Agent->>Search: Vector search for relevant knowledge
    Search-->>Agent: Top-K documents (RAG)
    
    Agent->>Gateway: Construct prompt + context
    Gateway->>Gateway: Select model (GPT-4 for complex task)
    Gateway->>OpenAI: Send prompt
    
    rect rgb(123, 104, 238, 0.2)
        Note over OpenAI: LLM reasoning:<br/>"Need to query database<br/>for claims data"
        OpenAI-->>Gateway: Tool call: query_claims_db(patient_id)
    end
    
    Gateway-->>Agent: Response with tool call
    Agent->>Insights: Log reasoning trace
    Agent->>Tools: Execute: query_claims_db(patient_id)
    Tools->>Cosmos: SELECT * FROM claims WHERE...
    Cosmos-->>Tools: Claims data
    Tools-->>Agent: Tool result
    
    Agent->>Gateway: Prompt + tool results
    Gateway->>OpenAI: Continue with results
    
    rect rgb(123, 104, 238, 0.2)
        Note over OpenAI: LLM synthesis:<br/>"Analyze claims and<br/>format response"
        OpenAI-->>Gateway: Final answer
    end
    
    Gateway-->>Agent: Complete response
    Agent->>Safety: Check output for safety
    Safety-->>Agent: ✓ Safe
    
    Agent->>Cosmos: Save conversation + reasoning chain
    Agent->>Insights: Log token usage & cost
    Agent->>APIM: Return response
    APIM->>User: "Patient X has 3 recent claims..."
    
    Note over User,Insights: Total tokens: 2,847 | Cost: $0.08 | Duration: 3.2s
```
# State
```mermaid
stateDiagram-v2
    [*] --> Idle
    
    Idle --> Authenticating: Incoming Request
    Authenticating --> InputValidation: Auth Success
    Authenticating --> [*]: Auth Failure
    
    InputValidation --> ContentSafety: Valid Input
    InputValidation --> [*]: Invalid/Unsafe
    
    ContentSafety --> LoadContext: Safe
    ContentSafety --> [*]: Harmful Content
    
    LoadContext --> Reasoning: Context Retrieved
    
    state Reasoning {
        [*] --> PromptConstruction
        PromptConstruction --> ModelSelection
        ModelSelection --> LLMInference
        LLMInference --> ResponseParsing
        ResponseParsing --> ToolExecutionNeeded: Tool Call?
        ResponseParsing --> FinalAnswer: Complete
        
        ToolExecutionNeeded --> ToolExecution
        ToolExecution --> ToolResultValidation
        ToolResultValidation --> PromptConstruction: Add Results
        ToolResultValidation --> ErrorHandling: Tool Failed
        
        ErrorHandling --> PromptConstruction: Retry
        ErrorHandling --> FinalAnswer: Max Retries
    }
    
    Reasoning --> OutputValidation: Answer Generated
    
    OutputValidation --> PersistState: Valid & Safe
    OutputValidation --> [*]: Unsafe Output
    
    PersistState --> LogMetrics: State Saved
    LogMetrics --> Idle: Complete
    
    note right of Reasoning
        Iterative loop:
        - May call tools 0-N times
        - Each iteration logged
        - Token costs accumulate
        - Circuit breaker on iterations
    end note
    
    note right of LogMetrics
        Captured metrics:
        • Token count (in/out)
        • Model used
        • Tools invoked
        • Cost calculation
        • Reasoning trace
    end note
```
# Comparison
```mermaid
graph LR
    subgraph Traditional["🏢 Traditional Application"]
        direction TB
        T1["Fixed Request"] --> T2["Predictable Logic"]
        T2 --> T3["Database Query"]
        T3 --> T4["Format Response"]
        T4 --> T5["Return"]
        
        style T1 fill:#e8e8e8
        style T2 fill:#e8e8e8
        style T3 fill:#e8e8e8
        style T4 fill:#e8e8e8
        style T5 fill:#e8e8e8
    end
    
    subgraph AIAgent["🤖 AI Agent Application"]
        direction TB
        A1["Natural Language"] --> A2{"Interpret Intent"}
        A2 --> A3["Build Context<br/>(RAG + Memory)"]
        A3 --> A4{"LLM Reasoning"}
        A4 -->|"Need data"| A5["Execute Tool"]
        A5 --> A4
        A4 -->|"Need clarification"| A6["Ask User"]
        A6 --> A4
        A4 -->|"Complete"| A7["Synthesize Answer"]
        A7 --> A8["Safety Check"]
        A8 --> A9["Return + Log Trace"]
        
        style A1 fill:#7B68EE,color:#fff
        style A2 fill:#7B68EE,color:#fff
        style A3 fill:#7B68EE,color:#fff
        style A4 fill:#7B68EE,color:#fff
        style A5 fill:#0078D4,color:#fff
        style A6 fill:#0078D4,color:#fff
        style A7 fill:#7B68EE,color:#fff
        style A8 fill:#DC143C,color:#fff
        style A9 fill:#4682B4,color:#fff
    end
    
    Diff["KEY DIFFERENCES:<br/>━━━━━━━━━━━━━━<br/>• Non-deterministic path<br/>• Iterative reasoning<br/>• Variable cost/latency<br/>• Tool composition<br/>• Semantic understanding<br/>• Context-aware"]
    
    Traditional -.->|vs| Diff
    AIAgent -.->|vs| Diff
    
    style Diff fill:#fff,stroke:#FF8C00,stroke-width:4px
```
# Cost Breakdown
```mermaid
graph TD
    subgraph CostTracking["💰 Cost Tracking & Attribution"]
        direction TB
        
        Request[/"Agent Request"/]
        
        Request --> Meter["Cost Meter<br/>━━━━━━━━━<br/>Track per:<br/>• User<br/>• Agent Type<br/>• Task Category"]
        
        Meter --> InputTokens["Input Tokens<br/>Base: $0.01/1K"]
        Meter --> OutputTokens["Output Tokens<br/>Base: $0.03/1K"]
        Meter --> CachedTokens["Cached Tokens<br/>Discount: 90% off"]
        
        InputTokens --> Accumulate
        OutputTokens --> Accumulate
        CachedTokens --> Accumulate
        
        Accumulate["Accumulate Cost"] --> ToolCosts["+ Tool Execution<br/>• DB queries<br/>• API calls<br/>• Compute time"]
        
        ToolCosts --> TotalCost["Total Request Cost"]
        
        TotalCost --> Budget{"Within Budget?"}
        
        Budget -->|Yes| Log["Log to Cosmos<br/>+ App Insights"]
        Budget -->|No| Alert["🚨 Alert + Throttle"]
        
        Alert --> NotifyOps["Notify Operations"]
        Alert --> CircuitBreaker["Circuit Breaker<br/>Limit iterations"]
        
        Log --> Dashboard["Power BI Dashboard<br/>━━━━━━━━━<br/>• Cost per user<br/>• Cost per agent<br/>• Token efficiency<br/>• Model usage mix"]
        
        Dashboard --> Optimize["Optimization Actions<br/>━━━━━━━━━<br/>• Switch to cheaper models<br/>• Improve prompt caching<br/>• Reduce iterations<br/>• Compress prompts"]
        
        style Request fill:#FF8C00,color:#fff
        style Meter fill:#4682B4,color:#fff
        style InputTokens fill:#2E8B57,color:#fff
        style OutputTokens fill:#2E8B57,color:#fff
        style CachedTokens fill:#2E8B57,color:#fff
        style Budget fill:#DC143C,color:#fff
        style Alert fill:#DC143C,color:#fff
        style Dashboard fill:#4682B4,color:#fff
        style Optimize fill:#7B68EE,color:#fff
    end
    
    Example["Example Calculation:<br/>━━━━━━━━━━━━━━<br/>Input: 1,500 tokens × $0.01 = $0.015<br/>Output: 800 tokens × $0.03 = $0.024<br/>Cached: 2,000 tokens × $0.001 = $0.002<br/>Tool: DB query = $0.001<br/>━━━━━━━━━━━━━━<br/>Total: $0.042 per request"]
    
    TotalCost -.->|"Real example"| Example
    
    style Example fill:#fff,stroke:#666,stroke-width:2px,stroke-dasharray: 5 5
```
# AI-Agentic-Architecture-AWS
# Main
```mermaid
graph TB
    %% Styling
    classDef aws fill:#FF9900,stroke:#cc7a00,stroke-width:3px,color:#000
    classDef aiml fill:#8B4789,stroke:#6b3569,stroke-width:3px,color:#fff
    classDef data fill:#3B48CC,stroke:#2d3899,stroke-width:3px,color:#fff
    classDef security fill:#DD344C,stroke:#b02a3d,stroke-width:3px,color:#fff
    classDef integration fill:#759C3E,stroke:#5a7830,stroke-width:3px,color:#fff
    classDef observability fill:#146EB4,stroke:#0f5489,stroke-width:3px,color:#fff
    
    %% Entry Layer
    APIGateway["API Gateway<br/>Auth • Rate Limiting • Throttling<br/>WAF Integration"]
    
    %% Orchestration Layer
    AgentRuntime["Agent Runtime<br/>ECS Fargate / EKS<br/>━━━━━━━━━<br/>• Auto-scale with Target Tracking<br/>• GPU instances (p3/g4dn)<br/>• Task IAM roles"]
    LLMGateway{"LLM Gateway<br/>━━━━━━━━━<br/>⭐ KEY DIFFERENTIATOR<br/>Lambda / Step Functions<br/>Routing • Caching • Fallback"}
    ToolRegistry["Tool Orchestration<br/>Lambda Functions<br/>━━━━━━━━━<br/>• Database queries<br/>• API integrations<br/>• S3 operations"]
    
    %% AI/ML Services
    Bedrock["Amazon Bedrock<br/>Claude • Titan • Llama"]
    SageMaker["SageMaker<br/>Custom models • Endpoints"]
    Kendra["Amazon Kendra<br/>Enterprise Search • RAG"]
    
    %% Data Layer
    DynamoDB[("DynamoDB<br/>━━━━━━━━━<br/>• Conversation history<br/>• Agent state<br/>• Vector embeddings<br/>(with pgvector extension)")]
    OpenSearch[("OpenSearch<br/>━━━━━━━━━<br/>• Vector search<br/>• Semantic retrieval<br/>• RAG knowledge base")]
    ElastiCache[("ElastiCache Redis<br/>━━━━━━━━━<br/>• Working memory<br/>• Tool result cache<br/>• Session state")]
    S3[("S3<br/>━━━━━━━━━<br/>• Document storage<br/>• Conversation archives<br/>• Model artifacts")]
    
    %% Security
    SecretsManager["Secrets Manager<br/>API Keys • Credentials"]
    IAM["IAM Roles<br/>Least Privilege Access"]
    GuardDuty["Amazon GuardDuty<br/>Threat Detection"]
    
    %% Integration Services
    StepFunctions["Step Functions<br/>Multi-step workflows<br/>Error handling"]
    EventBridge["EventBridge<br/>Event-driven triggers<br/>Scheduling"]
    SQS["SQS Queues<br/>Async processing<br/>Dead letter queues"]
    
    %% Observability
    CloudWatch["CloudWatch<br/>━━━━━━━━━<br/>• Logs & Metrics<br/>• Token usage tracking<br/>• Cost attribution<br/>• Custom dashboards"]
    XRay["X-Ray<br/>━━━━━━━━━<br/>• Distributed tracing<br/>• Reasoning chain analysis<br/>• Performance insights"]
    
    %% Primary Flows
    APIGateway -->|"Agent requests"| AgentRuntime
    APIGateway -->|"Direct tool calls"| ToolRegistry
    AgentRuntime ==>|"Prompt routing"| LLMGateway
    LLMGateway -->|"1. Primary"| Bedrock
    LLMGateway -->|"2. Custom models"| SageMaker
    LLMGateway -.->|"3. Fallback"| ExternalAPI["External APIs<br/>OpenAI • Anthropic"]
    
    AgentRuntime <-->|"State • Memory"| DynamoDB
    AgentRuntime <-->|"Vector search"| OpenSearch
    AgentRuntime <-->|"Enterprise search"| Kendra
    AgentRuntime -->|"Cache operations"| ElastiCache
    AgentRuntime <-->|"Documents"| S3
    
    ToolRegistry -->|"Data queries"| DynamoDB
    ToolRegistry -->|"Document retrieval"| S3
    ToolRegistry -.->|"Results"| AgentRuntime
    
    %% Security Flows
    AgentRuntime -.->|"Assume role"| IAM
    AgentRuntime -.->|"Get secrets"| SecretsManager
    ToolRegistry -.->|"Get credentials"| SecretsManager
    LLMGateway -.->|"Content filtering"| BedrockGuardrails["Bedrock Guardrails<br/>PII • Toxicity • Prompt injection"]
    
    %% Integration Flows
    EventBridge -.->|"Scheduled/event triggers"| AgentRuntime
    AgentRuntime -->|"Complex workflows"| StepFunctions
    AgentRuntime -->|"Async tasks"| SQS
    SQS -->|"Process queue"| ToolRegistry
    
    %% Observability Flows
    AgentRuntime -.->|"Logs • Metrics"| CloudWatch
    LLMGateway -.->|"Token metrics"| CloudWatch
    Bedrock -.->|"Model metrics"| CloudWatch
    AgentRuntime -.->|"Trace data"| XRay
    LLMGateway -.->|"Trace segments"| XRay
    ToolRegistry -.->|"Trace spans"| XRay
    
    %% Monitoring
    GuardDuty -.->|"Security alerts"| CloudWatch
    
    %% Apply Styles
    class APIGateway integration
    class AgentRuntime,ToolRegistry aws
    class LLMGateway,Bedrock,SageMaker,Kendra aiml
    class DynamoDB,OpenSearch,ElastiCache,S3 data
    class SecretsManager,IAM,GuardDuty,BedrockGuardrails security
    class StepFunctions,EventBridge,SQS integration
    class CloudWatch,XRay observability
```
# Request Route
```mermaid
sequenceDiagram
    autonumber
    participant User
    participant APIGW as API Gateway
    participant Lambda as Agent Lambda
    participant Gateway as LLM Gateway
    participant Bedrock as Amazon Bedrock
    participant Guardrails as Bedrock Guardrails
    participant Tools as Lambda Tools
    participant Dynamo as DynamoDB
    participant Search as OpenSearch
    participant XRay as X-Ray
    participant CW as CloudWatch
    
    User->>APIGW: POST /agent/query
    APIGW->>APIGW: Validate JWT + WAF check
    APIGW->>Lambda: Invoke agent
    
    activate Lambda
    Lambda->>XRay: Start trace segment
    Lambda->>Guardrails: Validate input
    Guardrails-->>Lambda: ✓ Safe (no PII/injection)
    
    Lambda->>Dynamo: GetItem(conversation_id)
    Dynamo-->>Lambda: Conversation history
    
    Lambda->>Search: Vector search (k-NN)
    Search-->>Lambda: Top-5 relevant docs
    
    Lambda->>Gateway: Build prompt + context
    activate Gateway
    Gateway->>Gateway: Select model (Claude on Bedrock)
    Gateway->>Bedrock: InvokeModel
    
    rect rgb(139, 71, 137, 0.2)
        Note over Bedrock: LLM reasoning:<br/>"Need to query claims database"
        Bedrock-->>Gateway: Tool use: query_claims(patient_id)
    end
    
    Gateway-->>Lambda: Response with tool call
    deactivate Gateway
    
    Lambda->>CW: Log reasoning trace
    Lambda->>Tools: Invoke tool Lambda
    activate Tools
    Tools->>Dynamo: Query(ClaimsTable)
    Dynamo-->>Tools: Claims records
    Tools-->>Lambda: Structured results
    deactivate Tools
    
    Lambda->>Gateway: Continue with tool results
    activate Gateway
    Gateway->>Bedrock: InvokeModel (with results)
    
    rect rgb(139, 71, 137, 0.2)
        Note over Bedrock: LLM synthesis:<br/>"Format response"
        Bedrock-->>Gateway: Final answer
    end
    
    Gateway-->>Lambda: Complete response
    deactivate Gateway
    
    Lambda->>Guardrails: Validate output
    Guardrails-->>Lambda: ✓ Safe
    
    Lambda->>Dynamo: PutItem(conversation + trace)
    Lambda->>CW: PutMetricData(tokens, cost, latency)
    Lambda->>XRay: End trace segment
    Lambda->>APIGW: 200 OK + response
    deactivate Lambda
    
    APIGW->>User: JSON response
    
    Note over User,CW: Trace ID: 1-67abc-def | Tokens: 2,431 | Cost: $0.073 | Duration: 2.8s
```
# State
```mermaid
stateDiagram-v2
    [*] --> ReceiveRequest
    
    ReceiveRequest --> ValidateInput: EventBridge trigger
    ValidateInput --> ContentFilter: Schema valid
    ValidateInput --> [*]: Invalid input
    
    ContentFilter --> LoadContext: Guardrails pass
    ContentFilter --> [*]: Harmful content
    
    LoadContext --> CheckCache: DynamoDB + OpenSearch
    
    CheckCache --> CacheHit: Response cached
    CheckCache --> InvokeAgent: Cache miss
    
    CacheHit --> ReturnResponse
    
    state InvokeAgent {
        [*] --> SelectModel
        SelectModel --> InvokeBedrock: Standard query
        SelectModel --> InvokeSageMaker: Custom model
        
        InvokeBedrock --> ParseResponse
        InvokeSageMaker --> ParseResponse
        
        ParseResponse --> ToolCallRequired: Contains tool_use
        ParseResponse --> FinalAnswer: Complete
        
        ToolCallRequired --> ExecuteTool
        ExecuteTool --> ValidateToolResult
        ValidateToolResult --> SelectModel: Add to context
        ValidateToolResult --> HandleError: Tool failed
        
        HandleError --> Retry: Attempt < 3
        HandleError --> FinalAnswer: Max retries
        
        Retry --> ExecuteTool
    }
    
    InvokeAgent --> ValidateOutput
    
    ValidateOutput --> PersistState: Safe output
    ValidateOutput --> [*]: Unsafe output
    
    PersistState --> CacheResponse: DynamoDB write
    CacheResponse --> LogMetrics: ElastiCache set
    LogMetrics --> ReturnResponse: CloudWatch + X-Ray
    
    ReturnResponse --> [*]
    
    note right of InvokeAgent
        Orchestrated by Step Functions:
        - Express workflow (< 5 min)
        - Error retry with backoff
        - Dead letter queue for failures
        - Cost per execution tracked
    end note
    
    note right of LogMetrics
        Metrics logged:
        • Input/output tokens
        • Model invocations
        • Tool executions
        • Total cost (Bedrock + Lambda)
        • Cache hit rate
    end note
```
# Comparison
```mermaid
graph LR
    subgraph Traditional["🏢 Traditional AWS Application"]
        direction TB
        T1["ALB/API Gateway"] --> T2["Lambda/ECS"]
        T2 --> T3["RDS Query"]
        T3 --> T4["Format JSON"]
        T4 --> T5["Return 200 OK"]
        
        T_Compute["Compute:<br/>Fixed Lambda timeout<br/>Predictable memory"]
        T_Data["Data:<br/>Relational schema<br/>SQL queries"]
        T_Cost["Cost:<br/>$0.0001 per request<br/>±10% variance"]
        
        style T1 fill:#e8e8e8
        style T2 fill:#e8e8e8
        style T3 fill:#e8e8e8
        style T4 fill:#e8e8e8
        style T5 fill:#e8e8e8
        style T_Compute fill:#f5f5f5,stroke:#999
        style T_Data fill:#f5f5f5,stroke:#999
        style T_Cost fill:#f5f5f5,stroke:#999
    end
    
    subgraph AIAgent["🤖 AI Agent AWS Application"]
        direction TB
        A1["API Gateway + WAF"] --> A2{"Bedrock Guardrails"}
        A2 --> A3["Load Context<br/>(DynamoDB + OpenSearch)"]
        A3 --> A4{"Bedrock Reasoning"}
        A4 -->|"tool_use"| A5["Lambda Tool Executor"]
        A5 --> A4
        A4 -->|"needs_docs"| A6["Kendra Search"]
        A6 --> A4
        A4 -->|"long_workflow"| A7["Step Functions"]
        A7 --> A4
        A4 -->|"complete"| A8["Synthesize Answer"]
        A8 --> A9["Content Filter + Cache"]
        A9 --> A10["Return + X-Ray trace"]
        
        A_Compute["Compute:<br/>Variable duration (1s - 15m)<br/>GPU instances for inference<br/>Auto-scaling 0→100"]
        A_Data["Data:<br/>Vector embeddings<br/>Semantic search<br/>Graph relationships"]
        A_Cost["Cost:<br/>$0.001 - $0.50 per request<br/>500x variance possible"]
        
        style A1 fill:#FF9900,color:#000
        style A2 fill:#DD344C,color:#fff
        style A3 fill:#3B48CC,color:#fff
        style A4 fill:#8B4789,color:#fff
        style A5 fill:#FF9900,color:#000
        style A6 fill:#8B4789,color:#fff
        style A7 fill:#759C3E,color:#fff
        style A8 fill:#8B4789,color:#fff
        style A9 fill:#3B48CC,color:#fff
        style A10 fill:#146EB4,color:#fff
        style A_Compute fill:#fff7e6,stroke:#FF9900,stroke-width:2px
        style A_Data fill:#fff7e6,stroke:#FF9900,stroke-width:2px
        style A_Cost fill:#fff7e6,stroke:#FF9900,stroke-width:2px
    end
    
    Diff["KEY AWS-SPECIFIC DIFFERENCES:<br/>━━━━━━━━━━━━━━━━━━━<br/>• Bedrock managed models vs self-hosted<br/>• Guardrails for safety vs custom filters<br/>• Step Functions for orchestration<br/>• X-Ray for reasoning trace analysis<br/>• EventBridge for async triggers<br/>• DynamoDB streams for state changes<br/>• Lambda reserved concurrency limits"]
    
    Traditional -.->|vs| Diff
    AIAgent -.->|vs| Diff
    
    style Diff fill:#fff,stroke:#FF9900,stroke-width:4px
```
# Cost Breakdown
```mermaid
graph TD
    subgraph CostTracking["💰 AWS AI Agent Cost Tracking"]
        direction TB
        
        Request[/"Agent Request"/]
        
        Request --> Meter["Cost Meter<br/>━━━━━━━━━<br/>CloudWatch Custom Metrics<br/>Track by:<br/>• User ID (tag)<br/>• Agent type (dimension)<br/>• Model used"]
        
        Meter --> BedrockCost["Bedrock Costs<br/>━━━━━━━━━<br/>Input tokens: $0.008/1K<br/>Output tokens: $0.024/1K<br/>(Claude 3 Sonnet)"]
        
        Meter --> LambdaCost["Lambda Costs<br/>━━━━━━━━━<br/>Duration-based<br/>Memory allocation<br/>Invocation count"]
        
        Meter --> DataCost["Data Transfer<br/>━━━━━━━━━<br/>• DynamoDB RCU/WCU<br/>• OpenSearch queries<br/>• S3 GET/PUT<br/>• ElastiCache ops"]
        
        BedrockCost --> Accumulate
        LambdaCost --> Accumulate
        DataCost --> Accumulate
        
        Accumulate["Aggregate Cost"] --> ToolCosts["+ Tool Execution<br/>━━━━━━━━━<br/>• Lambda invocations<br/>• External API calls<br/>• Kendra queries<br/>• SageMaker endpoints"]
        
        ToolCosts --> TotalCost["Total Request Cost<br/>Tagged with:<br/>cost-center, project, user"]
        
        TotalCost --> Budget{"Within Budget?<br/>AWS Budgets check"}
        
        Budget -->|Yes| Log["Log to:<br/>• CloudWatch Logs<br/>• DynamoDB cost table<br/>• S3 (daily aggregates)"]
        Budget -->|No| Alert["🚨 Budget Alert"]
        
        Alert --> SNS["SNS Topic<br/>━━━━━━━━━<br/>• Email ops team<br/>• Slack webhook<br/>• PagerDuty"]
        Alert --> Throttle["API Gateway<br/>Usage Plan throttle<br/>━━━━━━━━━<br/>Reduce rate limits<br/>Return 429"]
        Alert --> CircuitBreaker["Lambda env var:<br/>MAX_ITERATIONS=3<br/>Block expensive ops"]
        
        Log --> CostExplorer["AWS Cost Explorer<br/>━━━━━━━━━<br/>• Daily breakdown<br/>• Service allocation<br/>• Forecast trends"]
        
        Log --> QuickSight["QuickSight Dashboard<br/>━━━━━━━━━<br/>• Cost per user<br/>• Model efficiency<br/>• Token/$ trends<br/>• Agent ROI"]
        
        QuickSight --> Optimize["Optimization Actions<br/>━━━━━━━━━━━━━━<br/>1. Switch to Haiku for simple tasks<br/>2. Enable prompt caching (90% discount)<br/>3. Use reserved concurrency<br/>4. Batch DynamoDB writes<br/>5. Compress prompts<br/>6. ElastiCache aggressive TTL"]
        
        CostExplorer --> Optimize
        
        style Request fill:#FF9900,color:#000
        style Meter fill:#146EB4,color:#fff
        style BedrockCost fill:#8B4789,color:#fff
        style LambdaCost fill:#FF9900,color:#000
        style DataCost fill:#3B48CC,color:#fff
        style Budget fill:#DD344C,color:#fff
        style Alert fill:#DD344C,color:#fff
        style SNS fill:#DD344C,color:#fff
        style QuickSight fill:#146EB4,color:#fff
        style Optimize fill:#759C3E,color:#fff
    end
    
    Example["Real Example Calculation:<br/>━━━━━━━━━━━━━━━━━━<br/>Bedrock (Claude Sonnet):<br/>  Input: 2,000 tokens × $0.008 = $0.016<br/>  Output: 800 tokens × $0.024 = $0.019<br/>Lambda (agent orchestrator):<br/>  2GB × 3s × $0.0000166667 = $0.0001<br/>Lambda (3 tool calls):<br/>  512MB × 0.5s × 3 × $0.0000083334 = $0.00001<br/>DynamoDB:<br/>  2 reads + 1 write = $0.0003<br/>OpenSearch:<br/>  1 query = $0.001<br/>━━━━━━━━━━━━━━━━━━<br/>Total: $0.037 per complex request<br/><br/>Simple cached request: $0.003"]
    
    TotalCost -.->|"Actual AWS bill"| Example
    
    style Example fill:#fff,stroke:#666,stroke-width:2px,stroke-dasharray: 5 5
    
    CachingStrategy["Prompt Caching Strategy:<br/>━━━━━━━━━━━━━━━━━━<br/>System prompts: Cache 5 min<br/>User context: Cache 1 min<br/>RAG results: Cache 30 min<br/>━━━━━━━━━━━━━━━━━━<br/>Savings: 50-70% on repeated queries"]
    
    Optimize -.->|"Implement"| CachingStrategy
    
    style CachingStrategy fill:#e6ffe6,stroke:#759C3E,stroke-width:2px
```
