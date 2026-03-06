import type { Connection, QueryResult, TableSchema } from '../types';

const SCHEMA_URL = import.meta.env.VITE_SCHEMA_SERVICE_URL || 'http://localhost:8010';
const AGENT_URL = import.meta.env.VITE_QUERY_AGENT_URL || 'http://localhost:8011';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = body.detail;
    let message: string;
    if (typeof detail === 'string') {
      message = detail;
    } else if (Array.isArray(detail)) {
      message = detail.map((e: { msg?: string }) => e.msg ?? JSON.stringify(e)).join('; ');
    } else {
      message = JSON.stringify(body);
    }
    throw new Error(message);
  }
  return res.json();
}

// ------------------------------------------------------------------ //
//  Connection management (schema service)                             //
// ------------------------------------------------------------------ //

export async function registerConnection(
  name: string,
  connectionString: string
): Promise<{ connection_id: string; status: string }> {
  const res = await fetch(`${SCHEMA_URL}/connections`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, connection_string: connectionString }),
  });
  return handleResponse(res);
}

export async function getConnection(connectionId: string): Promise<Connection> {
  const res = await fetch(`${SCHEMA_URL}/connections/${connectionId}`);
  return handleResponse(res);
}

export async function listTables(connectionId: string): Promise<{ tables: string[]; count: number }> {
  const res = await fetch(`${SCHEMA_URL}/connections/${connectionId}/tables`);
  return handleResponse(res);
}

export async function getTableSchema(
  connectionId: string,
  tableName: string
): Promise<TableSchema> {
  const res = await fetch(`${SCHEMA_URL}/connections/${connectionId}/tables/${tableName}`);
  return handleResponse(res);
}

// ------------------------------------------------------------------ //
//  Query agent                                                        //
// ------------------------------------------------------------------ //

export async function runQuery(
  connectionId: string,
  question: string,
  sessionId: string
): Promise<QueryResult> {
  const res = await fetch(`${AGENT_URL}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      connection_id: connectionId,
      question,
      session_id: sessionId,
    }),
  });
  return handleResponse(res);
}

export async function getAuditLog(
  connectionId: string,
  sessionId?: string
): Promise<{ entries: unknown[]; count: number }> {
  const params = new URLSearchParams({ connection_id: connectionId });
  if (sessionId) params.append('session_id', sessionId);
  const res = await fetch(`${AGENT_URL}/audit?${params}`);
  return handleResponse(res);
}
