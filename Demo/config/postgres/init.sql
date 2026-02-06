-- ============================================
-- AI-Agentic Architecture - Database Schema
-- ============================================
-- PostgreSQL 16 with pgvector extension
-- This script creates all tables for the demo

-- Enable pgvector extension for vector embeddings (RAG)
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- Conversation Management Tables
-- ============================================

-- Main conversations table
CREATE TABLE conversations (
    conversation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    state VARCHAR(50) NOT NULL DEFAULT 'active',
    -- States: 'active', 'awaiting_clarification', 'completed', 'error'
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT valid_state CHECK (state IN ('active', 'awaiting_clarification', 'completed', 'error'))
);

-- Individual conversation turns (messages + responses)
CREATE TABLE conversation_turns (
    turn_id SERIAL PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    turn_number INT NOT NULL,
    user_input TEXT NOT NULL,
    agent_response TEXT,
    intent_analysis JSONB,
    -- Stores: {"intent": "...", "entities": {...}, "confidence": 0.95}
    tool_calls JSONB,
    -- Stores: [{"tool": "query_patients", "params": {...}, "result": {...}}]
    tokens_used JSONB,
    -- Stores: {"input": 1500, "output": 800, "cached": 200}
    cost_usd NUMERIC(10, 6),
    model_used VARCHAR(100),
    cache_hit BOOLEAN DEFAULT false,
    clarification_needed BOOLEAN DEFAULT false,
    clarification_response JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    execution_time_ms INT,
    CONSTRAINT unique_turn UNIQUE (conversation_id, turn_number)
);

-- Index for faster conversation lookups
CREATE INDEX idx_conversations_user ON conversations(user_id);
CREATE INDEX idx_conversations_state ON conversations(state);
CREATE INDEX idx_turns_conversation ON conversation_turns(conversation_id);

-- ============================================
-- Knowledge Base (for RAG)
-- ============================================

CREATE TABLE knowledge_base (
    doc_id SERIAL PRIMARY KEY,
    title VARCHAR(500),
    content TEXT NOT NULL,
    embedding vector(1536),
    -- OpenAI ada-002 embedding dimension
    metadata JSONB DEFAULT '{}'::jsonb,
    -- Stores: {"source": "...", "category": "...", "tags": [...]}
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Vector similarity search index (IVFFlat for fast approximate nearest neighbor)
CREATE INDEX ON knowledge_base USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- ============================================
-- Demo Data Tables (Healthcare Claims Example)
-- ============================================

-- Patients table
CREATE TABLE patients (
    patient_id VARCHAR(50) PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    dob DATE,
    email VARCHAR(255),
    phone VARCHAR(20),
    address TEXT,
    last_visit_date DATE,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Index for fuzzy name search
CREATE INDEX idx_patients_name ON patients(full_name);
CREATE INDEX idx_patients_last_name ON patients(last_name);
CREATE INDEX idx_patients_first_name ON patients(first_name);

-- Claims table
CREATE TABLE claims (
    claim_id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    claim_date DATE NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    status VARCHAR(50) NOT NULL,
    -- Status: 'pending', 'approved', 'denied', 'in_review'
    claim_type VARCHAR(100),
    -- Type: 'medical', 'dental', 'vision', 'prescription'
    description TEXT,
    diagnosis_code VARCHAR(20),
    provider_name VARCHAR(255),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_status CHECK (status IN ('pending', 'approved', 'denied', 'in_review')),
    CONSTRAINT positive_amount CHECK (amount >= 0)
);

-- Indexes for claims queries
CREATE INDEX idx_claims_patient ON claims(patient_id);
CREATE INDEX idx_claims_status ON claims(status);
CREATE INDEX idx_claims_date ON claims(claim_date);
CREATE INDEX idx_claims_type ON claims(claim_type);

-- ============================================
-- Metrics and Analytics Tables
-- ============================================

-- Request metrics (for cost tracking)
CREATE TABLE request_metrics (
    metric_id SERIAL PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    turn_id INT,
    metric_type VARCHAR(100) NOT NULL,
    -- Types: 'llm_call', 'tool_execution', 'cache_hit', 'clarification'
    metric_value NUMERIC(15, 6),
    metadata JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_metrics_type ON request_metrics(metric_type);
CREATE INDEX idx_metrics_timestamp ON request_metrics(timestamp);

-- ============================================
-- User Preferences (for learning)
-- ============================================

CREATE TABLE user_preferences (
    preference_id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    preference_type VARCHAR(100) NOT NULL,
    -- Types: 'entity_selection', 'parameter_default', 'clarification_history'
    preference_value JSONB NOT NULL,
    frequency INT DEFAULT 1,
    last_used TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_user_preference UNIQUE (user_id, preference_type, preference_value)
);

CREATE INDEX idx_preferences_user ON user_preferences(user_id);
CREATE INDEX idx_preferences_type ON user_preferences(preference_type);

-- ============================================
-- Helper Functions
-- ============================================

-- Function to update conversation timestamp automatically
CREATE OR REPLACE FUNCTION update_conversation_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE conversations
    SET updated_at = CURRENT_TIMESTAMP
    WHERE conversation_id = NEW.conversation_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update conversation when new turn is added
CREATE TRIGGER update_conversation_on_turn
AFTER INSERT ON conversation_turns
FOR EACH ROW
EXECUTE FUNCTION update_conversation_timestamp();

-- Function for fuzzy patient name search
CREATE OR REPLACE FUNCTION search_patients_fuzzy(search_name VARCHAR)
RETURNS TABLE (
    patient_id VARCHAR,
    full_name VARCHAR,
    last_visit_date DATE,
    similarity_score REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.patient_id,
        p.full_name,
        p.last_visit_date,
        similarity(p.full_name, search_name) AS similarity_score
    FROM patients p
    WHERE p.full_name ILIKE '%' || search_name || '%'
    ORDER BY similarity_score DESC, p.last_visit_date DESC NULLS LAST
    LIMIT 10;
END;
$$ LANGUAGE plpgsql;

-- Enable similarity search extension for fuzzy matching
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================
-- Views for Analytics
-- ============================================

-- View: Recent conversations with stats
CREATE OR REPLACE VIEW recent_conversations AS
SELECT
    c.conversation_id,
    c.user_id,
    c.state,
    c.created_at,
    COUNT(ct.turn_id) AS turn_count,
    SUM(ct.cost_usd) AS total_cost,
    SUM((ct.tokens_used->>'input')::int + (ct.tokens_used->>'output')::int) AS total_tokens,
    AVG(ct.execution_time_ms) AS avg_execution_time_ms
FROM conversations c
LEFT JOIN conversation_turns ct ON c.conversation_id = ct.conversation_id
GROUP BY c.conversation_id, c.user_id, c.state, c.created_at
ORDER BY c.created_at DESC;

-- View: Cost by user
CREATE OR REPLACE VIEW cost_by_user AS
SELECT
    c.user_id,
    COUNT(DISTINCT c.conversation_id) AS conversation_count,
    COUNT(ct.turn_id) AS total_turns,
    SUM(ct.cost_usd) AS total_cost,
    AVG(ct.cost_usd) AS avg_cost_per_turn
FROM conversations c
LEFT JOIN conversation_turns ct ON c.conversation_id = ct.conversation_id
GROUP BY c.user_id
ORDER BY total_cost DESC;

-- ============================================
-- Sample Test Data (minimal)
-- ============================================
-- More comprehensive seed data is in seed-data.sql

-- Insert a default admin user for testing
INSERT INTO conversations (conversation_id, user_id, state)
VALUES ('00000000-0000-0000-0000-000000000001', 'demo_user', 'active');

-- ============================================
-- Database Initialization Complete
-- ============================================

-- Display database info
\echo '==================================='
\echo 'Database Schema Created Successfully'
\echo '==================================='
\echo ''
\echo 'Tables Created:'
\echo '  - conversations'
\echo '  - conversation_turns'
\echo '  - knowledge_base (with pgvector)'
\echo '  - patients'
\echo '  - claims'
\echo '  - request_metrics'
\echo '  - user_preferences'
\echo ''
\echo 'Extensions Enabled:'
\echo '  - vector (pgvector)'
\echo '  - pg_trgm (fuzzy search)'
\echo ''
\echo 'Next step: Load seed data from seed-data.sql'
\echo '==================================='
