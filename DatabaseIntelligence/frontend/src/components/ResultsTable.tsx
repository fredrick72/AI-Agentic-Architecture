import { useState } from 'react';
import { AlertTriangle } from 'lucide-react';

interface Props {
  columns: string[];
  rows: (string | number | boolean | null)[][];
  rowCount: number;
  truncated: boolean;
}

const PAGE_SIZE = 50;

export function ResultsTable({ columns, rows, rowCount, truncated }: Props) {
  const [page, setPage] = useState(0);

  if (columns.length === 0) return null;

  const pageCount = Math.ceil(rows.length / PAGE_SIZE);
  const pageRows = rows.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  function formatCell(value: string | number | boolean | null): string {
    if (value === null) return 'NULL';
    if (typeof value === 'boolean') return value ? 'true' : 'false';
    return String(value);
  }

  function cellClass(value: string | number | boolean | null): string {
    if (value === null) return 'text-gray-600 italic';
    if (typeof value === 'number') return 'text-blue-300 text-right font-mono';
    if (typeof value === 'boolean') return value ? 'text-green-400' : 'text-red-400';
    return 'text-gray-300';
  }

  return (
    <div className="rounded-xl border border-gray-700 overflow-hidden">
      {/* Truncation warning */}
      {truncated && (
        <div className="flex items-center gap-2 px-4 py-2 bg-yellow-950/40 border-b border-yellow-800/40">
          <AlertTriangle className="w-4 h-4 text-yellow-500 flex-shrink-0" />
          <span className="text-yellow-400 text-xs">
            Results capped at {rowCount.toLocaleString()} rows. Refine your question for a smaller result set.
          </span>
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-gray-800">
              {columns.map(col => (
                <th
                  key={col}
                  className="px-4 py-2.5 text-left font-semibold text-gray-400 whitespace-nowrap border-r border-gray-700 last:border-0"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pageRows.map((row, ri) => (
              <tr
                key={ri}
                className={`border-t border-gray-800 ${ri % 2 === 0 ? 'bg-gray-900' : 'bg-gray-900/50'} hover:bg-gray-800/70`}
              >
                {row.map((cell, ci) => (
                  <td
                    key={ci}
                    className={`px-4 py-2 whitespace-nowrap border-r border-gray-800 last:border-0 max-w-xs truncate ${cellClass(cell)}`}
                    title={cell !== null ? String(cell) : 'NULL'}
                  >
                    {formatCell(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {pageCount > 1 && (
        <div className="flex items-center justify-between px-4 py-2.5 border-t border-gray-700 bg-gray-900">
          <span className="text-xs text-gray-500">
            Showing {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, rows.length)} of {rows.length.toLocaleString()}
          </span>
          <div className="flex gap-1.5">
            <button
              onClick={() => setPage(p => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-3 py-1 rounded-lg text-xs bg-gray-800 text-gray-400 hover:text-white
                         disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Prev
            </button>
            <button
              onClick={() => setPage(p => Math.min(pageCount - 1, p + 1))}
              disabled={page >= pageCount - 1}
              className="px-3 py-1 rounded-lg text-xs bg-gray-800 text-gray-400 hover:text-white
                         disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
