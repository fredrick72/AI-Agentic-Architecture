import { useState, useEffect } from 'react';
import { ChevronRight, ChevronDown, Table2, Key, Link, Loader2, RefreshCw } from 'lucide-react';
import { listTables, getTableSchema } from '../api/agent';
import type { Connection, TableSchema, ColumnInfo } from '../types';

interface Props {
  connection: Connection;
  onTableClick?: (tableName: string) => void;
}

function ColumnRow({ col, isPk }: { col: ColumnInfo; isPk: boolean }) {
  return (
    <div className="flex items-start gap-2 py-1 pl-4 text-xs">
      <span className={`mt-0.5 font-mono ${isPk ? 'text-yellow-400' : 'text-gray-400'}`}>
        {isPk ? <Key className="w-3 h-3 inline" /> : '·'}
      </span>
      <div className="min-w-0">
        <span className={`font-medium ${isPk ? 'text-yellow-300' : 'text-gray-300'}`}>
          {col.name}
        </span>
        <span className="text-gray-500 ml-2">{col.type}</span>
        {!col.nullable && <span className="text-orange-500/70 ml-1 text-[10px]">NOT NULL</span>}
        {col.sample_values && col.sample_values.length > 0 && (
          <div className="text-gray-600 text-[10px] mt-0.5 truncate">
            {col.sample_values.slice(0, 4).map(v => `"${v}"`).join(', ')}
          </div>
        )}
      </div>
    </div>
  );
}

function TableRow({
  connectionId,
  tableName,
  onTableClick,
}: {
  connectionId: string;
  tableName: string;
  onTableClick?: (t: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [schema, setSchema] = useState<TableSchema | null>(null);
  const [loading, setLoading] = useState(false);

  async function toggle() {
    setOpen(o => !o);
    if (!schema && !loading) {
      setLoading(true);
      try {
        const s = await getTableSchema(connectionId, tableName);
        setSchema(s);
      } finally {
        setLoading(false);
      }
    }
  }

  return (
    <div className="border-b border-gray-800 last:border-0">
      <button
        onClick={toggle}
        className="w-full flex items-center gap-2 px-3 py-2 hover:bg-gray-800/50 transition-colors text-left"
      >
        {open ? (
          <ChevronDown className="w-3.5 h-3.5 text-gray-500 flex-shrink-0" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 text-gray-500 flex-shrink-0" />
        )}
        <Table2 className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />
        <span
          className="text-sm text-gray-300 hover:text-white truncate flex-1 cursor-pointer"
          onClick={(e) => { e.stopPropagation(); onTableClick?.(tableName); }}
        >
          {tableName}
        </span>
        {schema && (
          <span className="text-[10px] text-gray-600 flex-shrink-0">
            {schema.row_count >= 0 ? schema.row_count.toLocaleString() + ' rows' : ''}
          </span>
        )}
      </button>

      {open && (
        <div className="bg-gray-900/50 pb-1">
          {loading && (
            <div className="flex items-center gap-2 px-4 py-2 text-xs text-gray-500">
              <Loader2 className="w-3 h-3 animate-spin" />
              Loading...
            </div>
          )}
          {schema && (
            <>
              {schema.description && (
                <p className="text-[11px] text-gray-500 px-4 py-1.5 italic border-b border-gray-800">
                  {schema.description}
                </p>
              )}
              {schema.columns.map(col => (
                <ColumnRow
                  key={col.name}
                  col={col}
                  isPk={schema.primary_key.includes(col.name)}
                />
              ))}
              {schema.foreign_keys.length > 0 && (
                <div className="px-4 py-1.5 border-t border-gray-800">
                  {schema.foreign_keys.map((fk, i) => (
                    <div key={i} className="flex items-center gap-1.5 text-[10px] text-blue-400/70 py-0.5">
                      <Link className="w-2.5 h-2.5" />
                      {fk.constrained_columns.join(', ')} → {fk.referred_table}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

export function SchemaExplorer({ connection, onTableClick }: Props) {
  const [tables, setTables] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    loadTables();
  }, [connection.connection_id]);

  async function loadTables() {
    setLoading(true);
    try {
      const result = await listTables(connection.connection_id);
      setTables(result.tables);
    } finally {
      setLoading(false);
    }
  }

  const filtered = tables.filter(t =>
    t.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex flex-col h-full bg-gray-900 border-r border-gray-800">
      {/* Header */}
      <div className="p-3 border-b border-gray-800">
        <div className="flex items-center justify-between mb-2">
          <div>
            <h2 className="text-sm font-semibold text-white truncate">{connection.name}</h2>
            <p className="text-[11px] text-gray-500 uppercase tracking-wide">{connection.db_type}</p>
          </div>
          <button
            onClick={loadTables}
            className="p-1.5 text-gray-500 hover:text-gray-300 rounded-lg hover:bg-gray-800"
            title="Refresh"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Search */}
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search tables..."
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-xs
                     text-white placeholder-gray-600 focus:outline-none focus:border-blue-500"
        />
        {!loading && (
          <p className="text-[10px] text-gray-600 mt-1.5">
            {filtered.length} of {tables.length} tables
          </p>
        )}
      </div>

      {/* Table list */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center h-24 gap-2 text-gray-500 text-sm">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading tables...
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center text-gray-600 text-sm py-8">No tables found</div>
        ) : (
          filtered.map(table => (
            <TableRow
              key={table}
              connectionId={connection.connection_id}
              tableName={table}
              onTableClick={onTableClick}
            />
          ))
        )}
      </div>
    </div>
  );
}
