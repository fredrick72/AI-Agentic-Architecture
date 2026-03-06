import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Bot, User, AlertCircle } from 'lucide-react';
import { runQuery } from '../api/agent';
import { SQLViewer } from './SQLViewer';
import { ResultsTable } from './ResultsTable';
import type { ChatMessage, Connection, QueryResult } from '../types';

interface Props {
  connection: Connection;
  sessionId: string;
  onTableMention?: (tableName: string) => void;
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';
  const result = message.queryResult;

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
        isUser ? 'bg-blue-600' : 'bg-gray-700'
      }`}>
        {isUser ? <User className="w-4 h-4 text-white" /> : <Bot className="w-4 h-4 text-gray-300" />}
      </div>

      {/* Content */}
      <div className={`max-w-[85%] space-y-3 ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
        {/* Text bubble */}
        <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? 'bg-blue-600 text-white rounded-tr-sm'
            : 'bg-gray-800 text-gray-200 rounded-tl-sm'
        }`}>
          {message.content}
        </div>

        {/* Query result panels (only on assistant messages) */}
        {result && (
          <div className="w-full space-y-3">
            <SQLViewer
              sql={result.sql}
              blocked={result.guardrail_blocked}
              blockedReason={result.guardrail_reason}
              executionTimeMs={result.execution_time_ms}
              rowCount={result.row_count}
              truncated={result.truncated}
              costUsd={result.cost_usd}
              tokensUsed={result.tokens_used}
            />
            {result.columns.length > 0 && (
              <ResultsTable
                columns={result.columns}
                rows={result.rows}
                rowCount={result.row_count}
                truncated={result.truncated}
              />
            )}
          </div>
        )}

        <span className="text-[10px] text-gray-600 px-1">
          {message.timestamp.toLocaleTimeString()}
        </span>
      </div>
    </div>
  );
}

const SUGGESTED_QUESTIONS = [
  'Show me the 10 most recently updated records',
  'How many rows are in each table?',
  'What are the distinct status values?',
  'Show me records created in the last 30 days',
];

export function ChatInterface({ connection, sessionId, onTableMention }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '0',
      role: 'assistant',
      content: `Connected to **${connection.name}** (${connection.db_type}). Schema analyzed — ${connection.table_count} tables mapped.\n\nAsk me anything about your data in plain English. I'll translate it to SQL, run it safely, and explain the results.`,
      timestamp: new Date(),
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function send(question: string) {
    if (!question.trim() || loading) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: question,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);
    setError('');

    try {
      const result: QueryResult = await runQuery(
        connection.connection_id,
        question,
        sessionId
      );

      const assistantMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: result.answer,
        queryResult: result,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, assistantMsg]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  }

  return (
    <div className="flex flex-col h-full bg-gray-950">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.map(msg => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {loading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center flex-shrink-0">
              <Bot className="w-4 h-4 text-gray-300" />
            </div>
            <div className="bg-gray-800 rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-2">
              <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
              <span className="text-sm text-gray-400">Analyzing and querying...</span>
            </div>
          </div>
        )}

        {error && (
          <div className="flex items-start gap-3 bg-red-950/40 border border-red-800 rounded-xl px-4 py-3">
            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
            <p className="text-red-300 text-sm">{error}</p>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Suggested questions (only when no user messages yet) */}
      {messages.length === 1 && (
        <div className="px-6 pb-4">
          <p className="text-xs text-gray-600 mb-2">Try asking:</p>
          <div className="flex flex-wrap gap-2">
            {SUGGESTED_QUESTIONS.map(q => (
              <button
                key={q}
                onClick={() => send(q)}
                className="text-xs bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white
                           border border-gray-700 rounded-lg px-3 py-1.5 transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="border-t border-gray-800 p-4">
        <div className="flex items-end gap-3 bg-gray-900 border border-gray-700 rounded-xl px-4 py-3
                        focus-within:border-blue-500 transition-colors">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about your data..."
            rows={1}
            className="flex-1 bg-transparent text-white text-sm placeholder-gray-600
                       focus:outline-none resize-none leading-relaxed"
            style={{ maxHeight: '120px' }}
            disabled={loading}
          />
          <button
            onClick={() => send(input)}
            disabled={!input.trim() || loading}
            className="p-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500
                       text-white rounded-lg transition-colors flex-shrink-0"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        <p className="text-[10px] text-gray-700 mt-1.5 text-center">
          All queries are read-only and logged for audit. Generated SQL is always shown.
        </p>
      </div>
    </div>
  );
}
