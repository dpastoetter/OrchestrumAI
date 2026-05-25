import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { PreviewTable } from "../components/PreviewTable";
import { api } from "../api";
import type { RequestDetail as RequestDetailType } from "../types";

export function RequestDetail() {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<RequestDetailType | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [comment, setComment] = useState("");

  const load = useCallback(async () => {
    if (!id) return;
    try {
      setDetail(await api.getRequest(id));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [id]);

  useEffect(() => {
    load();
    const t = setInterval(load, 2000);
    return () => clearInterval(t);
  }, [load]);

  async function resume(decision: "approved" | "rejected") {
    if (!id) return;
    setBusy(true);
    setError(null);
    try {
      await api.resumeRequest(id, decision, comment);
      setComment("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  if (!id) return null;
  if (!detail) {
    return <p className="text-slate-400">{error ?? "Loading…"}</p>;
  }

  const awaiting = detail.current_step === "AWAITING_APPROVAL";
  const isDoc = detail.agent_type === "doc_to_sheets";

  return (
    <div className="space-y-6">
      <Link to="/" className="text-sm text-sky-400 hover:underline">
        ← All requests
      </Link>
      <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-6 space-y-3">
        <div className="flex items-center gap-2">
          <h2 className="text-xl font-semibold">{detail.title}</h2>
          <span className="rounded bg-slate-800 px-2 py-0.5 text-xs text-slate-400">
            {isDoc ? "Doc → Sheets" : "Workflow"}
          </span>
        </div>
        {detail.file_name && (
          <p className="text-sm text-slate-500">File: {detail.file_name}</p>
        )}
        <p className="text-slate-300 whitespace-pre-wrap">{detail.description}</p>
        <dl className="grid grid-cols-2 gap-2 text-sm">
          <dt className="text-slate-500">Step</dt>
          <dd>{detail.current_step}</dd>
          <dt className="text-slate-500">Status</dt>
          <dd>{detail.status_message}</dd>
          <dt className="text-slate-500">Priority</dt>
          <dd>{detail.priority}</dd>
          {detail.llm_display_name && (
            <>
              <dt className="text-slate-500">Model</dt>
              <dd>{detail.llm_display_name}</dd>
            </>
          )}
        </dl>
        {detail.confidence_notes && (
          <p className="text-xs text-slate-500">{detail.confidence_notes}</p>
        )}
        {detail.plan_summary && (
          <div>
            <h3 className="text-sm font-medium text-slate-400">Plan</h3>
            <p className="text-sm">{detail.plan_summary}</p>
          </div>
        )}
        {detail.latest_output && (
          <div>
            <h3 className="text-sm font-medium text-slate-400">Latest output</h3>
            <p className="text-sm whitespace-pre-wrap">{detail.latest_output}</p>
          </div>
        )}
        {detail.sheet_result_url && (
          <div>
            <h3 className="text-sm font-medium text-slate-400">Google Sheet</h3>
            <a
              href={detail.sheet_result_url.startsWith("http") ? detail.sheet_result_url : "#"}
              className="text-sm text-sky-400 hover:underline break-all"
              target="_blank"
              rel="noreferrer"
            >
              {detail.sheet_result_url}
            </a>
            {detail.rows_written && (
              <p className="text-xs text-slate-500 mt-1">{detail.rows_written} rows written</p>
            )}
          </div>
        )}
        {detail.result_summary && (
          <div>
            <h3 className="text-sm font-medium text-slate-400">Result</h3>
            <p className="text-sm whitespace-pre-wrap">{detail.result_summary}</p>
          </div>
        )}
        {detail.error_message && (
          <p className="text-sm text-red-400">{detail.error_message}</p>
        )}
      </div>

      {isDoc && detail.preview_rows.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-slate-400">Extracted data preview</h3>
          <PreviewTable columns={detail.columns} rows={detail.preview_rows} />
        </div>
      )}

      {awaiting && (
        <div className="rounded-lg border border-amber-900/50 bg-amber-950/30 p-4 space-y-3">
          <h3 className="font-medium text-amber-200">
            {isDoc ? "Review rows before writing to Sheets" : "Human approval required"}
          </h3>
          <p className="text-sm text-amber-100/80">{detail.approval_summary}</p>
          {detail.proposed_actions && (
            <p className="text-sm text-amber-100/60">{detail.proposed_actions}</p>
          )}
          <textarea
            className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
            placeholder="Optional comment"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />
          <div className="flex gap-2">
            <button
              type="button"
              disabled={busy}
              onClick={() => resume("approved")}
              className="rounded bg-emerald-700 px-4 py-2 text-sm hover:bg-emerald-600 disabled:opacity-50"
            >
              {isDoc ? "Approve & write to Sheets" : "Approve"}
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => resume("rejected")}
              className="rounded bg-red-800 px-4 py-2 text-sm hover:bg-red-700 disabled:opacity-50"
            >
              Reject
            </button>
          </div>
        </div>
      )}

      {detail.events.length > 0 && (
        <div className="rounded-lg border border-slate-800 p-4">
          <h3 className="text-sm font-medium text-slate-400 mb-2">Event log</h3>
          <ul className="space-y-1 text-xs text-slate-500 max-h-48 overflow-y-auto">
            {detail.events.map((ev, i) => (
              <li key={i}>
                [{ev.kind}] {ev.step}: {ev.text?.slice(0, 120)}
              </li>
            ))}
          </ul>
        </div>
      )}

      {error && <p className="text-sm text-red-400">{error}</p>}
    </div>
  );
}
