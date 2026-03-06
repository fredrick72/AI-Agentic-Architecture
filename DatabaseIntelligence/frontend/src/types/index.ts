export interface Connection {
  connection_id: string;
  name: string;
  db_type: string;
  status: 'pending' | 'crawling' | 'ready' | 'error';
  table_count?: number;
  schema_crawled_at?: string;
  error_message?: string;
}

export interface QueryResult {
  answer: string;
  sql: string | null;
  columns: string[];
  rows: (string | number | boolean | null)[][];
  row_count: number;
  truncated: boolean;
  execution_time_ms: number;
  guardrail_blocked: boolean;
  guardrail_reason: string | null;
  tokens_used: number;
  cost_usd: number;
  audit_id: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  queryResult?: QueryResult;
  timestamp: Date;
}

export interface TableSchema {
  name: string;
  comment: string;
  columns: ColumnInfo[];
  primary_key: string[];
  foreign_keys: ForeignKey[];
  row_count: number;
  description?: string;
}

export interface ColumnInfo {
  name: string;
  type: string;
  nullable: boolean;
  default: string | null;
  comment: string;
  sample_values: string[] | null;
}

export interface ForeignKey {
  constrained_columns: string[];
  referred_table: string;
  referred_columns: string[];
}
