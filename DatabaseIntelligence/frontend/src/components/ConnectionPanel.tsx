import { useState } from 'react';
import { Database, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { registerConnection, getConnection } from '../api/agent';
import type { Connection } from '../types';

interface Props {
  onConnected: (connection: Connection) => void;
}

const DB_EXAMPLES: Record<string, string> = {
  PostgreSQL: 'postgresql://user:password@host:5432/database',
  MySQL: 'mysql+pymysql://user:password@host:3306/database',
  SQLite: 'sqlite:///path/to/database.db',
  'SQL Server': 'mssql+pyodbc://user:password@host/database?driver=ODBC+Driver+17+for+SQL+Server',
};

export function ConnectionPanel({ onConnected }: Props) {
  const [name, setName] = useState('');
  const [connectionString, setConnectionString] = useState('');
  const [selectedExample, setSelectedExample] = useState('PostgreSQL');
  const [phase, setPhase] = useState<'idle' | 'connecting' | 'crawling' | 'error'>('idle');
  const [error, setError] = useState('');

  async function handleConnect(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !connectionString.trim()) return;

    setPhase('connecting');
    setError('');

    try {
      const { connection_id } = await registerConnection(name.trim(), connectionString.trim());
      setPhase('crawling');

      // Poll until ready or error
      const poll = async (): Promise<Connection> => {
        await new Promise(r => setTimeout(r, 2000));
        const conn = await getConnection(connection_id);
        if (conn.status === 'ready') return conn;
        if (conn.status === 'error') throw new Error(conn.error_message || 'Crawl failed');
        return poll();
      };

      const connection = await poll();
      onConnected(connection);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setPhase('error');
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-6">
      <div className="w-full max-w-xl">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-2xl mb-4">
            <Database className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white">Database Intelligence</h1>
          <p className="text-gray-400 mt-2">
            Connect to any database and ask questions in plain English
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleConnect} className="bg-gray-900 rounded-2xl p-6 space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">
              Connection name
            </label>
            <input
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="e.g. Production DB, Sales Data"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5
                         text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
              disabled={phase === 'connecting' || phase === 'crawling'}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">
              Database type
            </label>
            <div className="flex gap-2 flex-wrap">
              {Object.keys(DB_EXAMPLES).map(db => (
                <button
                  key={db}
                  type="button"
                  onClick={() => {
                    setSelectedExample(db);
                    setConnectionString(DB_EXAMPLES[db]);
                  }}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    selectedExample === db
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-800 text-gray-400 hover:text-white'
                  }`}
                >
                  {db}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">
              Connection string
            </label>
            <input
              value={connectionString}
              onChange={e => setConnectionString(e.target.value)}
              placeholder={DB_EXAMPLES[selectedExample]}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5
                         text-white placeholder-gray-600 font-mono text-sm
                         focus:outline-none focus:border-blue-500"
              disabled={phase === 'connecting' || phase === 'crawling'}
            />
            <p className="text-xs text-gray-500 mt-1.5">
              Use a read-only database user for best security.
            </p>
          </div>

          {/* Status messages */}
          {phase === 'crawling' && (
            <div className="flex items-center gap-3 bg-blue-950 border border-blue-800 rounded-lg px-4 py-3">
              <Loader2 className="w-5 h-5 text-blue-400 animate-spin flex-shrink-0" />
              <div>
                <p className="text-blue-300 font-medium text-sm">Analyzing schema...</p>
                <p className="text-blue-400/70 text-xs mt-0.5">
                  Crawling tables, generating descriptions, building embeddings. This takes 30-90 seconds.
                </p>
              </div>
            </div>
          )}

          {phase === 'error' && (
            <div className="flex items-start gap-3 bg-red-950 border border-red-800 rounded-lg px-4 py-3">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-red-300 text-sm">{error}</p>
            </div>
          )}

          <button
            type="submit"
            disabled={!name.trim() || !connectionString.trim() || phase === 'connecting' || phase === 'crawling'}
            className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500
                       text-white font-semibold py-3 rounded-xl transition-colors flex items-center justify-center gap-2"
          >
            {phase === 'connecting' || phase === 'crawling' ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                {phase === 'connecting' ? 'Connecting...' : 'Analyzing...'}
              </>
            ) : (
              <>
                <Database className="w-4 h-4" />
                Connect & Analyze Schema
              </>
            )}
          </button>
        </form>

        <p className="text-center text-gray-600 text-xs mt-4">
          Schema analysis uses OpenAI embeddings to build a semantic map of your database.
        </p>
      </div>
    </div>
  );
}
