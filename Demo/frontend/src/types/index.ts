/**
 * TypeScript types for AI Agent Frontend
 */

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  metadata?: MessageMetadata;
}

export interface MessageMetadata {
  tool_calls?: ToolCall[];
  tokens_used?: TokenUsage;
  cost_usd?: number;
  model_used?: string;
  cache_hit?: boolean;
  iterations?: number;
}

export interface ToolCall {
  tool: string;
  parameters: Record<string, any>;
  result?: any;
  iteration?: number;
}

export interface TokenUsage {
  input: number;
  output: number;
  total?: number;
}

export interface ClarificationUI {
  type: 'entity_disambiguation' | 'parameter_elicitation' | 'constraint_negotiation' | 'scope_guidance';
  entity_type?: string;
  question: string;
  ui_type: 'radio' | 'checkbox' | 'text' | 'date' | 'number';
  options?: ClarificationOption[];
  allow_multiple?: boolean;
  parameter_name?: string;
  parameter_type?: string;
  suggestions?: any[];
  required?: boolean;
  metadata?: Record<string, any>;
}

export interface ClarificationOption {
  id: string;
  label: string;
  sublabel?: string;
  metadata?: Record<string, any>;
  recommended?: boolean;
  relevance?: number;
}

export interface QueryRequest {
  message: string;
  conversation_id?: string;
  clarification_response?: ClarificationResponse;
}

export interface ClarificationResponse {
  clarification_type: string;
  user_selection: {
    entity_type?: string;
    selected_id?: string;
    selected_label?: string;
    value?: any;
    parameter_name?: string;
    parameter_type?: string;
    metadata?: Record<string, any>;
  };
  original_intent: Record<string, any>;
}

export interface QueryResponse {
  type: 'result' | 'clarification_needed' | 'error';
  data: any;
  metadata: Record<string, any>;
  conversation_id: string;
}

export interface AgentStats {
  total_conversations: number;
  cost_summary: {
    total_cost: number;
    conversation_count: number;
    avg_cost_per_conversation: number;
    total_tokens: number;
  };
  cost_trends: {
    period_days: number;
    total_cost: number;
    avg_daily_cost: number;
    daily_breakdown: Array<{
      date: string;
      cost: number;
      turn_count: number;
      conversation_count: number;
    }>;
  };
  monthly_estimate: {
    avg_daily_cost: number;
    estimated_monthly_cost: number;
    based_on_days: number;
  };
}
