import { useState } from 'react';
import { ChevronDown, ChevronRight, Copy, Check, ShieldAlert, ShieldCheck } from 'lucide-react';

interface Props {
  sql: string | null;
  blocked: boolean;
  blockedReason: string | null;
  executionTimeMs: number;
  rowCount: number;
  truncated: boolean;
  costUsd: number;
  tokensUsed: number;
}

export function SQLViewer({
  sql,
  blocked,
  blockedReason,
  executionTimeMs,
  rowCount,
  truncated,
  costUsd,
  tokensUsed,
}: Props) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  async function copy() {
    if (!sql) return;
    await navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className={`rounded-xl border text-sm ${
      blocked
        ? 'border-red-800 bg-red-950/30'
        : 'border-gray-700 bg-gray-900'
    }`}>
      {/* Summary bar — always visible */}
      <div
        className="flex items-center gap-3 px-4 py-2.5 cursor-pointer select-none"
        onClick={() => setOpen(o => !o)}
      >
        {blocked ? (
          <ShieldAlert className="w-4 h-4 text-red-400 flex-shrink-0" />
        ) : (
          <ShieldCheck className="w-4 h-4 text-green-400 flex-shrink-0" />
        )}

        <span className={`font-medium ${blocked ? 'text-red-300' : 'text-gray-300'}`}>
          {blocked ? 'Query blocked by guardrails' : 'Generated SQL'}
        </span>

        {!blocked && sql && (
          <div className="flex items-center gap-3 ml-auto text-xs text-gray-500">
            <span>{rowCount.toLocaleString()} rows{truncated ? ' (capped)' : ''}</span>
            <span>{executionTimeMs}ms</span>
            <span>${costUsd.toFixed(5)}</span>
            <span>{tokensUsed.toLocaleString()} tokens</span>
          </div>
        )}

        <span className="ml-auto flex-shrink-0">
          {open
            ? <ChevronDown className="w-4 h-4 text-gray-500" />
            : <ChevronRight className="w-4 h-4 text-gray-500" />
          }
        </span>
      </div>

      {/* Expandable body */}
      {open && (
        <div className="border-t border-gray-700">
          {blocked && blockedReason && (
            <div className="px-4 py-3 text-red-300 text-sm">
              <strong>Reason:</strong> {blockedReason}
            </div>
          )}

          {sql && (
            <div className="relative">
              <button
                onClick={copy}
                className="absolute top-3 right-3 p-1.5 rounded-lg bg-gray-800 hover:bg-gray-700
                           text-gray-400 hover:text-white transition-colors"
                title="Copy SQL"
              >
                {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
              <pre className="px-4 py-3 overflow-x-auto text-xs font-mono text-gray-300 leading-relaxed">
                {sql}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
