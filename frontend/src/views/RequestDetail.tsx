import { Check, ChevronLeft, Copy, Download, ExternalLink, Save, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { PreviewTable } from "../components/PreviewTable";
import { Alert } from "../components/ui/Alert";
import { Badge, statusToBadgeVariant } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { api } from "../api";
import {
  buildRequestMarkdown,
  copyText,
  downloadMarkdown,
} from "../lib/exportRequest";
import type { RequestDetail as RequestDetailType } from "../types";

export function RequestDetail() {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<RequestDetailType | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [comment, setComment] = useState("");
  const [saveName, setSaveName] = useState("");
  const [showSaveTemplate, setShowSaveTemplate] = useState(false);
  const [copyMsg, setCopyMsg] = useState<string | null>(null);

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
    return <p className="oma-hint">{error ?? "Loading…"}</p>;
  }

  const awaiting = detail.current_step === "AWAITING_APPROVAL";
  const isDoc = detail.agent_type === "doc_to_sheets";
  const canSaveTemplate =
    detail.status === "done" && detail.agent_type === "workflow" && !!detail.agent_topology_type;

  async function saveAsTemplate() {
    if (!id || !saveName.trim()) return;
    setBusy(true);
    try {
      await api.saveRequestAsTemplate(id, { name: saveName.trim() });
      setShowSaveTemplate(false);
      setSaveName("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <Link
        to="/"
        className="inline-flex items-center gap-1 text-sm font-medium hover:underline"
        style={{ color: "var(--oma-primary)" }}
      >
        <ChevronLeft size={16} aria-hidden />
        All requests
      </Link>

      <Card className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-xl font-semibold" style={{ color: "var(--oma-text)" }}>
            {detail.title}
          </h2>
          <Badge variant="neutral">{isDoc ? "Doc → Sheets" : "Workflow"}</Badge>
          <Badge variant={statusToBadgeVariant(detail.status)}>
            {detail.status === "awaiting_approval"
              ? "Awaiting approval"
              : detail.status === "done"
                ? "Done"
                : detail.status === "failed"
                  ? "Failed"
                  : detail.current_step}
          </Badge>
          {!isDoc && detail.agent_topology_type && (
            <Badge variant="scheduled">{detail.agent_topology_type}</Badge>
          )}
          {!isDoc &&
            (detail.agent_topology_labels ?? []).map((label) => (
              <Badge key={label} variant="neutral">
                {label}
              </Badge>
            ))}
        </div>
        <div className="flex flex-wrap gap-2">
          {detail.plan_summary && (
            <Button
              variant="secondary"
              size="sm"
              icon={Copy}
              onClick={async () => {
                await copyText(detail.plan_summary);
                setCopyMsg("Plan copied");
                setTimeout(() => setCopyMsg(null), 2000);
              }}
            >
              Copy plan
            </Button>
          )}
          {(detail.result_summary || detail.latest_output) && (
            <Button
              variant="secondary"
              size="sm"
              icon={Copy}
              onClick={async () => {
                await copyText(detail.result_summary || detail.latest_output);
                setCopyMsg("Result copied");
                setTimeout(() => setCopyMsg(null), 2000);
              }}
            >
              Copy result
            </Button>
          )}
          <Button
            variant="secondary"
            size="sm"
            icon={Download}
            onClick={() =>
              downloadMarkdown(
                `${detail.title.replace(/[^\w.-]+/g, "_").slice(0, 40)}.md`,
                buildRequestMarkdown(detail),
              )
            }
          >
            Download .md
          </Button>
          {copyMsg && <span className="oma-hint self-center text-sm">{copyMsg}</span>}
        </div>
        {detail.file_name && (
          <p className="text-sm" style={{ color: "var(--oma-muted)" }}>
            File: {detail.file_name}
          </p>
        )}
        <p className="whitespace-pre-wrap" style={{ color: "var(--oma-text)" }}>
          {detail.description}
        </p>
        <dl className="grid grid-cols-2 gap-3 text-sm">
          <dt style={{ color: "var(--oma-muted)" }}>Step</dt>
          <dd>{detail.current_step}</dd>
          <dt style={{ color: "var(--oma-muted)" }}>Status</dt>
          <dd>{detail.status_message}</dd>
          <dt style={{ color: "var(--oma-muted)" }}>Priority</dt>
          <dd>{detail.priority}</dd>
          {detail.llm_display_name && (
            <>
              <dt style={{ color: "var(--oma-muted)" }}>Model</dt>
              <dd>{detail.llm_display_name}</dd>
            </>
          )}
        </dl>
        {detail.confidence_notes && (
          <p className="text-xs" style={{ color: "var(--oma-muted)" }}>
            {detail.confidence_notes}
          </p>
        )}
        {detail.plan_summary && (
          <div>
            <h3 className="text-sm font-medium" style={{ color: "var(--oma-muted)" }}>
              Plan
            </h3>
            <p className="text-sm">{detail.plan_summary}</p>
          </div>
        )}
        {detail.latest_output && (
          <div>
            <h3 className="text-sm font-medium" style={{ color: "var(--oma-muted)" }}>
              Latest output
            </h3>
            <p className="whitespace-pre-wrap text-sm">{detail.latest_output}</p>
          </div>
        )}
        {detail.sheet_result_url && (
          <div>
            <h3 className="text-sm font-medium" style={{ color: "var(--oma-muted)" }}>
              Google Sheet
            </h3>
            <a
              href={detail.sheet_result_url.startsWith("http") ? detail.sheet_result_url : "#"}
              className="inline-flex items-center gap-1 text-sm hover:underline break-all"
              style={{ color: "var(--oma-primary)" }}
              target="_blank"
              rel="noreferrer"
            >
              {detail.sheet_result_url}
              <ExternalLink size={14} aria-hidden />
            </a>
            {detail.rows_written && (
              <p className="mt-1 text-xs" style={{ color: "var(--oma-muted)" }}>
                {detail.rows_written} rows written
              </p>
            )}
          </div>
        )}
        {detail.result_summary && (
          <div>
            <h3 className="text-sm font-medium" style={{ color: "var(--oma-muted)" }}>
              Result
            </h3>
            <p className="whitespace-pre-wrap text-sm">{detail.result_summary}</p>
          </div>
        )}
        {detail.error_message && (
          <Alert variant="error">{detail.error_message}</Alert>
        )}
      </Card>

      {isDoc && detail.preview_rows.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium" style={{ color: "var(--oma-muted)" }}>
            Extracted data preview
          </h3>
          <PreviewTable columns={detail.columns} rows={detail.preview_rows} />
        </div>
      )}

      {awaiting && (
        <Alert variant="info" title={isDoc ? "Review rows before writing to Sheets" : "Human approval required"}>
          <p>{detail.approval_summary}</p>
          {detail.proposed_actions && <p className="mt-2 opacity-80">{detail.proposed_actions}</p>}
          <textarea
            className="oma-input mt-3 min-h-[80px]"
            placeholder="Optional comment"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />
          <div className="mt-3 flex flex-wrap gap-2">
            <Button
              variant="primary"
              icon={Check}
              disabled={busy}
              onClick={() => resume("approved")}
            >
              {isDoc ? "Approve & write to Sheets" : "Approve"}
            </Button>
            <Button variant="danger" icon={X} disabled={busy} onClick={() => resume("rejected")}>
              Reject
            </Button>
          </div>
        </Alert>
      )}

      {canSaveTemplate && (
        <Card className="space-y-3">
          <h3 className="text-sm font-medium" style={{ color: "var(--oma-muted)" }}>
            Save as workflow
          </h3>
          {!showSaveTemplate ? (
            <Button
              variant="secondary"
              icon={Save}
              onClick={() => {
                setShowSaveTemplate(true);
                setSaveName(detail.title);
              }}
            >
              Save as template
            </Button>
          ) : (
            <div className="flex flex-wrap gap-2">
              <input
                className="oma-input min-w-[12rem] flex-1"
                value={saveName}
                onChange={(e) => setSaveName(e.target.value)}
                placeholder="Template name"
              />
              <Button variant="primary" disabled={busy || !saveName.trim()} onClick={saveAsTemplate}>
                Save
              </Button>
              <Button variant="ghost" onClick={() => setShowSaveTemplate(false)}>
                Cancel
              </Button>
            </div>
          )}
        </Card>
      )}

      {detail.events.length > 0 && (
        <Card>
          <h3 className="mb-2 text-sm font-medium" style={{ color: "var(--oma-muted)" }}>
            Event log
          </h3>
          <ul className="max-h-48 space-y-1 overflow-y-auto text-xs" style={{ color: "var(--oma-muted)" }}>
            {detail.events.map((ev, i) => (
              <li key={i}>
                [{ev.kind}] {ev.step}: {ev.text?.slice(0, 120)}
              </li>
            ))}
          </ul>
        </Card>
      )}

      {error && <Alert variant="error">{error}</Alert>}
    </div>
  );
}
