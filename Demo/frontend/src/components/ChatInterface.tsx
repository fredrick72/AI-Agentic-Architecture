/**
 * Chat Interface - Main chat UI with message history
 */
import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, User, Bot, Wrench, DollarSign, Zap } from 'lucide-react';
import { sendQuery } from '../api/agent';
import ClarificationWidget from './ClarificationWidget';
import type { Message, QueryResponse, ClarificationUI } from '../types';

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [pendingClarification, setPendingClarification] = useState<{
    ui: ClarificationUI;
    intentData: Record<string, any>;
  } | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim() || loading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setLoading(true);

    try {
      const response = await sendQuery({
        message: inputValue,
        conversation_id: conversationId || undefined,
      });

      handleResponse(response);
    } catch (error) {
      console.error('Query error:', error);
      const errorMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleClarificationSubmit = async (selection: any) => {
    if (!pendingClarification || loading) return;

    const clarificationMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: `Selected: ${selection.user_selection.selected_label || selection.user_selection.value}`,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, clarificationMessage]);
    setPendingClarification(null);
    setLoading(true);

    try {
      const response = await sendQuery({
        message: messages[messages.length - 1].content, // Original message
        conversation_id: conversationId || undefined,
        clarification_response: selection,
      });

      handleResponse(response);
    } catch (error) {
      console.error('Clarification error:', error);
      const errorMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your clarification. Please try again.',
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleResponse = (response: QueryResponse) => {
    // Save conversation ID
    if (!conversationId) {
      setConversationId(response.conversation_id);
    }

    if (response.type === 'result') {
      // Final answer
      const assistantMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: response.data.answer,
        timestamp: new Date().toISOString(),
        metadata: response.metadata,
      };
      setMessages(prev => [...prev, assistantMessage]);
      setPendingClarification(null);
    } else if (response.type === 'clarification_needed') {
      // Need clarification
      setPendingClarification({
        ui: response.data,
        intentData: response.metadata.intent_data,
      });
    } else if (response.type === 'error') {
      // Error
      const errorMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: response.data.message || 'An error occurred.',
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMessage]);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow-md border border-gray-200">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 bg-gradient-to-r from-primary-600 to-primary-700">
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <Bot className="w-6 h-6" />
          Healthcare Claims Assistant
        </h2>
        <p className="text-primary-100 text-sm mt-1">
          Ask me about patients and claims. I'll clarify if I need more info!
        </p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-12">
            <Bot className="w-16 h-16 mx-auto text-gray-300 mb-4" />
            <h3 className="text-lg font-medium text-gray-600 mb-2">Welcome!</h3>
            <p className="text-gray-500 text-sm max-w-md mx-auto">
              Try asking: "Find claims for John" or "What is the total for patient PAT-12345?"
            </p>
          </div>
        )}

        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {/* Pending clarification */}
        {pendingClarification && !loading && (
          <ClarificationWidget
            clarificationUI={pendingClarification.ui}
            intentData={pendingClarification.intentData}
            onSubmit={handleClarificationSubmit}
            disabled={loading}
          />
        )}

        {/* Loading indicator */}
        {loading && (
          <div className="flex items-center gap-2 text-gray-500">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">Thinking...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-gray-200 bg-gray-50">
        <div className="flex gap-2">
          <textarea
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-none"
            placeholder="Ask me anything about claims..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            rows={1}
            disabled={loading}
          />
          <button
            className="btn-primary flex items-center gap-2 px-6"
            onClick={handleSendMessage}
            disabled={loading || !inputValue.trim()}
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

interface MessageBubbleProps {
  message: Message;
}

function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
        isUser ? 'bg-primary-600' : 'bg-gray-200'
      }`}>
        {isUser ? (
          <User className="w-5 h-5 text-white" />
        ) : (
          <Bot className="w-5 h-5 text-gray-600" />
        )}
      </div>

      {/* Message content */}
      <div className={`flex-1 max-w-3xl ${isUser ? 'flex flex-col items-end' : ''}`}>
        <div className={`px-4 py-3 rounded-lg ${
          isUser
            ? 'bg-primary-600 text-white'
            : 'bg-gray-100 text-gray-900'
        }`}>
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        </div>

        {/* Metadata (for assistant messages) */}
        {!isUser && message.metadata && (
          <div className="mt-2 flex flex-wrap gap-2 text-xs text-gray-500">
            {message.metadata.iterations && (
              <div className="flex items-center gap-1 px-2 py-1 bg-gray-100 rounded">
                <Wrench className="w-3 h-3" />
                <span>{message.metadata.iterations} iterations</span>
              </div>
            )}

            {message.metadata.tool_calls && message.metadata.tool_calls.length > 0 && (
              <div className="flex items-center gap-1 px-2 py-1 bg-gray-100 rounded">
                <Wrench className="w-3 h-3" />
                <span>{message.metadata.tool_calls.length} tools used</span>
              </div>
            )}

            {message.metadata.tokens_used && (
              <div className="flex items-center gap-1 px-2 py-1 bg-gray-100 rounded">
                <Zap className="w-3 h-3" />
                <span>{message.metadata.tokens_used.input + message.metadata.tokens_used.output} tokens</span>
              </div>
            )}

            {message.metadata.cost_usd !== undefined && (
              <div className="flex items-center gap-1 px-2 py-1 bg-gray-100 rounded">
                <DollarSign className="w-3 h-3" />
                <span>${message.metadata.cost_usd.toFixed(4)}</span>
              </div>
            )}

            {message.metadata.cache_hit && (
              <div className="px-2 py-1 bg-green-100 text-green-800 rounded">
                ⚡ Cached
              </div>
            )}

            {message.metadata.model_used && (
              <div className="px-2 py-1 bg-blue-100 text-blue-800 rounded">
                {message.metadata.model_used}
              </div>
            )}
          </div>
        )}

        {/* Timestamp */}
        <p className="text-xs text-gray-400 mt-1">
          {new Date(message.timestamp).toLocaleTimeString()}
        </p>
      </div>
    </div>
  );
}
