/**
 * API client for Agent Runtime
 */
import axios from 'axios';
import type { QueryRequest, QueryResponse, AgentStats } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000, // 60s timeout for LLM calls
});

/**
 * Send a query to the agent
 */
export async function sendQuery(request: QueryRequest): Promise<QueryResponse> {
  const response = await api.post<QueryResponse>('/agent/query', request);
  return response.data;
}

/**
 * Get agent statistics
 */
export async function getAgentStats(): Promise<AgentStats> {
  const response = await api.get<AgentStats>('/agent/stats');
  return response.data;
}

/**
 * Get conversation history
 */
export async function getConversationHistory(conversationId: string, limit: number = 10) {
  const response = await api.get(`/agent/conversation/${conversationId}`, {
    params: { limit },
  });
  return response.data;
}

/**
 * Get conversation cost breakdown
 */
export async function getConversationCost(conversationId: string) {
  const response = await api.get(`/agent/conversation/${conversationId}/cost`);
  return response.data;
}

/**
 * Health check
 */
export async function healthCheck() {
  const response = await api.get('/health');
  return response.data;
}

export default api;
