import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import type { RequestSummary } from "../types";

function statusBadge(status: string, step: string) {
  const base = "inline-block rounded px-2 py-0.5 text-xs font-medium";
  if (status === "awaiting_approval")
    return <span className={`${base} bg-amber-900/60 text-amber-200`}>Awaiting approval</span>;
  if (status === "done") return <span className={`${base} bg-emerald-900/60 text-emerald-200`}>Done</span>;
  if (status === "failed") return <span className={`${base} bg-red-900/60 text-red-200`}>Failed</span>;
  return <span className={`${base} bg-slate-800 text-slate-300`}>{step}</span>;
}

export function RequestList() {
  const [items, setItems] = useState<RequestSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setItems(await api.listRequests());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, [load]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-medium">Requests</h2>
        <Link
          to="/submit"
          className="rounded bg-sky-600 px-3 py-1.5 text-sm hover:bg-sky-500"
        >
          New request
        </Link>
      </div>
      {error && <p className="text-sm text-red-400">{error}</p>}
      {items.length === 0 ? (
        <p className="text-slate-400">No requests yet.</p>
      ) : (
        <ul className="divide-y divide-slate-800 rounded-lg border border-slate-800">
          {items.map((r) => (
            <li key={r.id} className="flex items-center justify-between gap-4 px-4 py-3 hover:bg-slate-900/50">
              <Link to={`/requests/${r.id}`} className="min-w-0 flex-1">
                <div className="font-medium truncate">{r.title}</div>
                <div className="text-xs text-slate-500">
                  {new Date(r.created_at).toLocaleString()} · {r.agent_type === "doc_to_sheets" ? "Doc→Sheets" : "Workflow"}
                  {r.file_name ? ` · ${r.file_name}` : ""} · {r.priority}
                </div>
              </Link>
              {statusBadge(r.status, r.current_step)}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
