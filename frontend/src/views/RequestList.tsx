import { Bell, BellOff, Plus, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useInbox } from "../context/InboxContext";
import { AgentTypeIcons } from "../lib/icons";
import {
  type RequestFilter,
  matchesFilter,
  sortRequests,
} from "../lib/requestFilters";
import { Badge, statusToBadgeVariant } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { Alert } from "../components/ui/Alert";
import { PageHeader } from "../components/ui/PageHeader";

const FILTERS: { id: RequestFilter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "needs_approval", label: "Needs approval" },
  { id: "running", label: "Running" },
  { id: "done_today", label: "Done today" },
  { id: "failed", label: "Failed" },
];

export function RequestList() {
  const { requests, setRequests, refresh, notifyEnabled, setNotifyEnabled, awaitingCount } =
    useInbox();
  const [filter, setFilter] = useState<RequestFilter>(
    awaitingCount > 0 ? "needs_approval" : "all",
  );
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const visible = useMemo(
    () => sortRequests(requests.filter((r) => matchesFilter(r, filter))),
    [requests, filter],
  );

  async function removeRequest(id: string, title: string) {
    if (!window.confirm(`Delete "${title}"? This cannot be undone.`)) return;
    setDeletingId(id);
    setError(null);
    try {
      await api.deleteRequest(id);
      setRequests(requests.filter((r) => r.id !== id));
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Requests"
        description="Track workflow runs, approvals, and outcomes."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              icon={notifyEnabled ? Bell : BellOff}
              onClick={() => setNotifyEnabled(!notifyEnabled)}
              title="Browser notifications when approval is needed"
            >
              {notifyEnabled ? "Alerts on" : "Alerts off"}
            </Button>
            <Link to="/submit" className="oma-btn-primary !no-underline">
              <Plus size={16} aria-hidden />
              New request
            </Link>
          </div>
        }
      />

      <div className="flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            type="button"
            onClick={() => setFilter(f.id)}
            className={[
              "rounded-lg border px-3 py-1.5 text-sm font-medium transition",
              filter === f.id ? "shadow-sm" : "opacity-80 hover:opacity-100",
            ].join(" ")}
            style={
              filter === f.id
                ? {
                    borderColor: "var(--oma-primary)",
                    backgroundColor: "color-mix(in srgb, var(--oma-primary) 10%, var(--oma-surface))",
                    color: "var(--oma-primary)",
                  }
                : {
                    borderColor: "var(--oma-border)",
                    backgroundColor: "var(--oma-surface)",
                    color: "var(--oma-muted)",
                  }
            }
          >
            {f.label}
            {f.id === "needs_approval" && awaitingCount > 0 && (
              <span className="ml-1.5">({awaitingCount})</span>
            )}
          </button>
        ))}
      </div>

      {error && <Alert variant="error">{error}</Alert>}

      {visible.length === 0 ? (
        <EmptyState
          title={filter === "all" ? "No requests yet" : "No matching requests"}
          description={
            filter === "all"
              ? "Submit a workflow or document job to get started."
              : "Try another filter or submit a new request."
          }
          action={
            <Link to="/submit" className="oma-btn-primary !no-underline">
              <Plus size={16} aria-hidden />
              New request
            </Link>
          }
        />
      ) : (
        <ul
          className="divide-y rounded-xl border overflow-hidden"
          style={{ borderColor: "var(--oma-border)", backgroundColor: "var(--oma-surface)" }}
        >
          {visible.map((r) => {
            const AgentIcon = AgentTypeIcons[r.agent_type] ?? AgentTypeIcons.workflow;
            return (
              <li
                key={r.id}
                className="flex items-center justify-between gap-4 px-4 py-3 transition hover:opacity-95"
                style={{ backgroundColor: "var(--oma-surface)" }}
              >
                <Link to={`/requests/${r.id}`} className="flex min-w-0 flex-1 items-start gap-3">
                  <span
                    className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg"
                    style={{
                      backgroundColor: "var(--oma-surface-elevated)",
                      color: "var(--oma-primary)",
                    }}
                  >
                    <AgentIcon size={18} aria-hidden />
                  </span>
                  <div className="min-w-0">
                    <div className="truncate font-medium" style={{ color: "var(--oma-text)" }}>
                      {r.title}
                    </div>
                    <div className="oma-hint mt-0.5">
                      {new Date(r.created_at).toLocaleString()} ·{" "}
                      {r.agent_type === "doc_to_sheets" ? "Doc → Sheets" : "Workflow"}
                      {r.file_name ? ` · ${r.file_name}` : ""} · {r.priority}
                      {r.run_source === "scheduled" ? " · scheduled" : ""}
                    </div>
                  </div>
                </Link>
                <div className="flex shrink-0 flex-col items-end gap-2">
                  <div className="flex flex-wrap justify-end gap-1">
                    {r.run_source === "scheduled" && (
                      <Badge variant="scheduled">Scheduled</Badge>
                    )}
                    <Badge variant={statusToBadgeVariant(r.status)}>
                      {r.status === "awaiting_approval"
                        ? "Awaiting approval"
                        : r.status === "done"
                          ? "Done"
                          : r.status === "failed"
                            ? "Failed"
                            : r.current_step}
                    </Badge>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    icon={Trash2}
                    disabled={deletingId === r.id}
                    onClick={() => removeRequest(r.id, r.title)}
                    className="!text-[var(--oma-danger)]"
                  >
                    {deletingId === r.id ? "Deleting…" : "Delete"}
                  </Button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
