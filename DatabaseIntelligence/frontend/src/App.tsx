import { useState } from 'react';
import { Database, LogOut } from 'lucide-react';
import { ConnectionPanel } from './components/ConnectionPanel';
import { SchemaExplorer } from './components/SchemaExplorer';
import { ChatInterface } from './components/ChatInterface';
import type { Connection } from './types';

function generateSessionId() {
  return `sess_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

export default function App() {
  const [connection, setConnection] = useState<Connection | null>(null);
  const [sessionId] = useState(generateSessionId);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  if (!connection) {
    return <ConnectionPanel onConnected={setConnection} />;
  }

  return (
    <div className="flex flex-col h-screen bg-gray-950 text-white">
      {/* Top bar */}
      <header className="flex items-center gap-3 px-4 py-3 border-b border-gray-800 bg-gray-900 flex-shrink-0">
        <button
          onClick={() => setSidebarOpen(o => !o)}
          className="p-1.5 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-white transition-colors"
          title="Toggle schema explorer"
        >
          <Database className="w-4 h-4" />
        </button>

        <div className="flex-1 min-w-0">
          <h1 className="text-sm font-semibold text-white truncate">{connection.name}</h1>
          <p className="text-[11px] text-gray-500">
            {connection.db_type} · {connection.table_count} tables · Session: {sessionId.slice(5, 16)}
          </p>
        </div>

        <button
          onClick={() => setConnection(null)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-gray-400
                     hover:text-white hover:bg-gray-800 transition-colors"
        >
          <LogOut className="w-3.5 h-3.5" />
          Disconnect
        </button>
      </header>

      {/* Main layout */}
      <div className="flex flex-1 min-h-0">
        {/* Schema sidebar */}
        {sidebarOpen && (
          <div className="w-64 flex-shrink-0 overflow-hidden">
            <SchemaExplorer connection={connection} />
          </div>
        )}

        {/* Chat */}
        <div className="flex-1 min-w-0">
          <ChatInterface
            connection={connection}
            sessionId={sessionId}
          />
        </div>
      </div>
    </div>
  );
}
