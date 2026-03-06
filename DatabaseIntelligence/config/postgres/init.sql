-- Database Intelligence Agent - App Metadata Schema
-- This database stores schema maps and audit logs, NOT your target database data

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- Registered database connections
-- ============================================
CREATE TABLE connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    db_type VARCHAR(50) NOT NULL,           -- postgresql, mysql, sqlite, mssql
    host VARCHAR(500),
    port INTEGER,
    database_name VARCHAR(255),
    -- Connection string stored encrypted in production; plaintext here for demo
    connection_string TEXT NOT NULL,
    schema_crawled_at TIMESTAMP,
    table_count INTEGER,
    status VARCHAR(50) DEFAULT 'pending',   -- pending, crawling, ready, error
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- Schema chunks (one per table) with embeddings
-- Used for RAG: find relevant tables for a question
-- ============================================
CREATE TABLE schema_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    connection_id UUID NOT NULL REFERENCES connections(id) ON DELETE CASCADE,
    table_name VARCHAR(255) NOT NULL,
    chunk_type VARCHAR(50) NOT NULL,        -- 'table_overview', 'column_details', 'relationships'
    content TEXT NOT NULL,                  -- human-readable description of this table/chunk
    raw_schema JSONB,                       -- raw schema data (columns, PKs, FKs, etc.)
    embedding vector(1536),                 -- ada-002 embedding of content
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- IVFFlat index for cosine similarity search
CREATE INDEX idx_schema_chunks_embedding
    ON schema_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);

CREATE INDEX idx_schema_chunks_connection
    ON schema_chunks(connection_id);

CREATE INDEX idx_schema_chunks_table
    ON schema_chunks(connection_id, table_name);

-- ============================================
-- Query audit log - every query, safe or blocked
-- ============================================
CREATE TABLE query_audit (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    connection_id UUID REFERENCES connections(id) ON DELETE SET NULL,
    session_id VARCHAR(255),
    user_question TEXT NOT NULL,
    generated_sql TEXT,
    guardrail_blocked BOOLEAN DEFAULT FALSE,
    guardrail_reason TEXT,
    execution_status VARCHAR(50),           -- success, error, timeout
    row_count INTEGER,
    execution_time_ms INTEGER,
    llm_tokens_used INTEGER,
    llm_cost_usd NUMERIC(10, 6),
    result_sample JSONB,                    -- first 5 rows for display
    agent_explanation TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_query_audit_connection ON query_audit(connection_id);
CREATE INDEX idx_query_audit_session ON query_audit(session_id);
CREATE INDEX idx_query_audit_created ON query_audit(created_at DESC);
