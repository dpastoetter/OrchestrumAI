import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { FileDropzone } from "../components/FileDropzone";
import { api, type ProviderCatalogItem } from "../api";
import type { AgentInfo, AgentType, Priority } from "../types";

const AGENT_META: Record<
  AgentType,
  { title: string; blurb: string; icon: string; accent: string }
> = {
  doc_to_sheets: {
    title: "Document → Sheets",
    blurb: "Upload a file, preview extracted rows, approve, then append to Google Sheets.",
    icon: "📊",
    accent: "border-emerald-600/50 bg-emerald-950/30 ring-emerald-500/40",
  },
  workflow: {
    title: "General workflow",
    blurb: "Multi-step agent with planning, execution, and human approval gates.",
    icon: "⚡",
    accent: "border-sky-600/50 bg-sky-950/30 ring-sky-500/40",
  },
};

const PRIORITIES: { value: Priority; label: string; hint: string }[] = [
  { value: "low", label: "Low", hint: "When you can wait" },
  { value: "normal", label: "Normal", hint: "Default" },
  { value: "high", label: "High", hint: "Needs attention soon" },
];

export function SubmitRequest() {
  const navigate = useNavigate();
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [providers, setProviders] = useState<ProviderCatalogItem[]>([]);
  const [defaultProviderId, setDefaultProviderId] = useState("");
  const [defaultModelId, setDefaultModelId] = useState("");
  const [useCustomLlm, setUseCustomLlm] = useState(false);
  const [providerId, setProviderId] = useState("");
  const [modelId, setModelId] = useState("");
  const [agentType, setAgentType] = useState<AgentType>("doc_to_sheets");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<Priority>("normal");
  const [sheetUrl, setSheetUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listAgents().then(setAgents).catch(() => {});
    api
      .getProviders()
      .then((d) => {
        setProviders(d.providers);
        setDefaultProviderId(d.settings.default_provider_id);
        setDefaultModelId(d.settings.default_model_id);
        setProviderId(d.settings.default_provider_id);
        setModelId(d.settings.default_model_id);
      })
      .catch(() => {});
  }, []);

  const agentOptions = useMemo(() => {
    if (agents.length) return agents;
    return [
      { id: "workflow" as const, name: AGENT_META.workflow.title, description: AGENT_META.workflow.blurb },
      { id: "doc_to_sheets" as const, name: AGENT_META.doc_to_sheets.title, description: AGENT_META.doc_to_sheets.blurb },
    ];
  }, [agents]);

  const isDoc = agentType === "doc_to_sheets";
  const selectedProvider = providers.find((p) => p.id === providerId);
  const defaultProvider = providers.find((p) => p.id === defaultProviderId);

  const canSubmit =
    title.trim().length > 0 &&
    description.trim().length > 0 &&
    (!isDoc || file !== null) &&
    !busy;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    if (isDoc && !file) {
      setError("Please add a document to upload.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      let created;
      if (isDoc && file) {
        const form = new FormData();
        form.append("title", title.trim());
        form.append("description", description.trim());
        form.append("priority", priority);
        form.append("agent_type", "doc_to_sheets");
        form.append("sheet_url", sheetUrl.trim());
        if (useCustomLlm && providerId) {
          form.append("provider_id", providerId);
          form.append("model_id", modelId);
        }
        form.append("file", file);
        created = await api.createRequestWithFile(form);
      } else {
        created = await api.createRequest({
          title: title.trim(),
          description: description.trim(),
          priority,
          agent_type: agentType,
          sheet_url: sheetUrl.trim() || undefined,
          provider_id: useCustomLlm ? providerId : "",
          model_id: useCustomLlm ? modelId : "",
        });
      }
      navigate(`/requests/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="space-y-1">
        <p className="text-xs font-medium uppercase tracking-wider text-sky-500/90">New request</p>
        <h2 className="text-2xl font-semibold tracking-tight text-slate-50">Submit a request</h2>
        <p className="text-sm text-slate-400 leading-relaxed">
          Choose an agent, describe what you need, and we&apos;ll run it with approval checkpoints along the way.
        </p>
      </div>

      <form onSubmit={onSubmit} className="space-y-5">
        {/* Agent picker */}
        <section className="oma-section space-y-3">
          <div>
            <h3 className="oma-label">Agent</h3>
            <p className="oma-hint mt-0.5">What should handle this request?</p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {agentOptions.map((a) => {
              const meta = AGENT_META[a.id];
              const selected = agentType === a.id;
              return (
                <button
                  key={a.id}
                  type="button"
                  onClick={() => setAgentType(a.id)}
                  className={[
                    "relative rounded-xl border p-4 text-left transition",
                    selected
                      ? `ring-2 ${meta.accent}`
                      : "border-slate-800 bg-slate-950/50 hover:border-slate-600 hover:bg-slate-900/60",
                  ].join(" ")}
                >
                  <span className="text-2xl" aria-hidden>
                    {meta.icon}
                  </span>
                  <p className="mt-2 font-medium text-slate-100">{a.name}</p>
                  <p className="mt-1 text-xs leading-relaxed text-slate-500">
                    {a.description || meta.blurb}
                  </p>
                  {selected && (
                    <span className="absolute right-3 top-3 text-sky-400" aria-hidden>
                      ✓
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </section>

        {/* Doc-specific */}
        {isDoc && (
          <section className="oma-section space-y-4">
            <div>
              <h3 className="oma-label">Document</h3>
              <p className="oma-hint mt-0.5">We&apos;ll extract tabular data for your review before writing to Sheets.</p>
            </div>
            <FileDropzone file={file} onFileChange={setFile} disabled={busy} />
            <label className="block space-y-1.5">
              <span className="oma-label">Google Sheet URL or ID</span>
              <span className="oma-hint block">Optional — leave blank to use the default spreadsheet from env.</span>
              <input
                className="oma-input"
                value={sheetUrl}
                onChange={(e) => setSheetUrl(e.target.value)}
                placeholder="https://docs.google.com/spreadsheets/d/..."
                disabled={busy}
              />
            </label>
          </section>
        )}

        {/* Core fields */}
        <section className="oma-section space-y-4">
          <div>
            <h3 className="oma-label">Details</h3>
            <p className="oma-hint mt-0.5">Give the agent enough context to do the right thing.</p>
          </div>

          <label className="block space-y-1.5">
            <div className="flex items-baseline justify-between gap-2">
              <span className="oma-label">Title</span>
              <span className="oma-hint tabular-nums">{title.length}/200</span>
            </div>
            <input
              className="oma-input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={200}
              placeholder={isDoc ? "Q1 expense report import" : "Automate weekly status summary"}
              required
              disabled={busy}
            />
          </label>

          <label className="block space-y-1.5">
            <span className="oma-label">{isDoc ? "Extraction notes" : "Goal & description"}</span>
            <span className="oma-hint block">
              {isDoc
                ? "Column names, date formats, or what to ignore help extraction quality."
                : "What outcome do you want? Include constraints and success criteria."}
            </span>
            <textarea
              className="oma-input min-h-[140px] resize-y"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={
                isDoc
                  ? "e.g. Amount column is USD; skip header rows; map Date to transaction_date."
                  : "e.g. Summarize open GitHub issues tagged bug, grouped by component, under 500 words."
              }
              required
              disabled={busy}
            />
          </label>

          <div className="space-y-2">
            <span className="oma-label">Priority</span>
            <div className="flex flex-wrap gap-2">
              {PRIORITIES.map((p) => (
                <button
                  key={p.value}
                  type="button"
                  disabled={busy}
                  onClick={() => setPriority(p.value)}
                  className={[
                    "rounded-lg border px-4 py-2 text-left text-sm transition",
                    priority === p.value
                      ? "border-sky-600/60 bg-sky-950/50 text-sky-100 ring-1 ring-sky-500/30"
                      : "border-slate-700/80 bg-slate-950/50 text-slate-400 hover:border-slate-600 hover:text-slate-200",
                  ].join(" ")}
                >
                  <span className="font-medium">{p.label}</span>
                  <span className="ml-2 text-xs opacity-70">{p.hint}</span>
                </button>
              ))}
            </div>
          </div>
        </section>

        {/* LLM override */}
        <section className="oma-section space-y-3">
          <button
            type="button"
            disabled={busy}
            onClick={() => setUseCustomLlm((v) => !v)}
            className="flex w-full items-center justify-between gap-2 text-left"
          >
            <div>
              <h3 className="oma-label">AI model</h3>
              <p className="oma-hint mt-0.5">
                {useCustomLlm
                  ? "Using a one-off override for this request"
                  : defaultProvider
                    ? `Default: ${defaultProvider.name} · ${defaultModelId}`
                    : "Using workspace default from Settings"}
              </p>
            </div>
            <span
              className={[
                "shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium",
                useCustomLlm ? "bg-sky-900/60 text-sky-300" : "bg-slate-800 text-slate-500",
              ].join(" ")}
            >
              {useCustomLlm ? "Custom" : "Default"}
            </span>
          </button>

          {useCustomLlm && (
            <div className="grid gap-3 border-t border-slate-800/80 pt-3 sm:grid-cols-2">
              <label className="space-y-1.5">
                <span className="oma-hint">Provider</span>
                <select
                  className="oma-input"
                  value={providerId}
                  disabled={busy}
                  onChange={(e) => {
                    setProviderId(e.target.value);
                    const p = providers.find((x) => x.id === e.target.value);
                    if (p?.models[0]) setModelId(p.models[0].id);
                  }}
                >
                  {providers.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                      {p.status === "needs_config" ? " (setup required)" : ""}
                    </option>
                  ))}
                </select>
              </label>
              <label className="space-y-1.5">
                <span className="oma-hint">Model</span>
                <select
                  className="oma-input"
                  value={modelId}
                  disabled={busy}
                  onChange={(e) => setModelId(e.target.value)}
                >
                  {(selectedProvider?.models ?? []).map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.label}
                    </option>
                  ))}
                </select>
              </label>
              {selectedProvider?.status === "needs_config" && (
                <p className="oma-hint sm:col-span-2">
                  This provider isn&apos;t connected yet.{" "}
                  <Link to="/settings" className="text-sky-400 hover:underline">
                    Configure in Settings
                  </Link>
                </p>
              )}
            </div>
          )}
        </section>

        {error && (
          <div
            role="alert"
            className="rounded-lg border border-red-900/50 bg-red-950/40 px-4 py-3 text-sm text-red-300"
          >
            {error}
          </div>
        )}

        <div className="flex flex-col-reverse gap-3 border-t border-slate-800/80 pt-5 sm:flex-row sm:items-center sm:justify-between">
          <Link to="/" className="text-center text-sm text-slate-500 hover:text-slate-300 sm:text-left">
            ← Back to requests
          </Link>
          <button
            type="submit"
            disabled={!canSubmit}
            className={[
              "inline-flex items-center justify-center gap-2 rounded-lg px-6 py-2.5 text-sm font-semibold transition",
              canSubmit
                ? "bg-sky-600 text-white shadow-lg shadow-sky-900/30 hover:bg-sky-500"
                : "cursor-not-allowed bg-slate-800 text-slate-500",
            ].join(" ")}
          >
            {busy && (
              <span
                className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white"
                aria-hidden
              />
            )}
            {busy ? "Starting agent…" : isDoc ? "Upload & start extraction" : "Submit request"}
          </button>
        </div>
      </form>
    </div>
  );
}
