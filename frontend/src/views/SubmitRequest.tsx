import { Check, Send } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { FileDropzone } from "../components/FileDropzone";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { PageHeader } from "../components/ui/PageHeader";
import { AgentTopologyBuilder } from "../components/topology/AgentTopologyBuilder";
import { AgentTypeIcons } from "../lib/icons";
import {
  defaultTopology,
  topologyForApi,
  validateTopology,
  type AgentTopology,
} from "../components/topology/topologyTypes";
import { api, type ProviderCatalogItem } from "../api";
import { useWorkflowPreferences } from "../context/WorkflowPreferencesContext";
import type { AgentInfo, AgentType, Priority, WorkflowTemplate } from "../types";

const AGENT_META: Record<AgentType, { title: string; blurb: string }> = {
  doc_to_sheets: {
    title: "Document → Sheets",
    blurb: "Upload a file, preview extracted rows, approve, then append to Google Sheets.",
  },
  workflow: {
    title: "General workflow",
    blurb: "Multi-step agent with planning, execution, and human approval gates.",
  },
};

const PRIORITIES: { value: Priority; label: string; hint: string }[] = [
  { value: "low", label: "Low", hint: "When you can wait" },
  { value: "normal", label: "Normal", hint: "Default" },
  { value: "high", label: "High", hint: "Needs attention soon" },
];

export function SubmitRequest() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const templateParam = searchParams.get("template");
  const { advancedMode, catalog: genericCatalog, refresh: refreshWorkflowPrefs } =
    useWorkflowPreferences();
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
  const [agentTopology, setAgentTopology] = useState<AgentTopology | null>(null);
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState("");

  function applyTemplate(tpl: WorkflowTemplate) {
    setAgentType(tpl.agent_type);
    setTitle(tpl.name);
    setDescription(tpl.description_template);
    setPriority(tpl.default_priority);
    if (tpl.agent_topology) {
      setAgentTopology({
        type: tpl.agent_topology.type,
        nodes: tpl.agent_topology.nodes,
        edges: tpl.agent_topology.edges ?? [],
      });
    }
    if (tpl.provider_id) {
      setUseCustomLlm(true);
      setProviderId(tpl.provider_id);
      setModelId(tpl.model_id ?? "");
    }
  }

  useEffect(() => {
    void refreshWorkflowPrefs();
  }, [location.pathname, refreshWorkflowPrefs]);

  useEffect(() => {
    api.listAgents().then(setAgents).catch(() => {});
    Promise.all([api.getProviders(), api.listWorkflowTemplates()])
      .then(([prov, tplRes]) => {
        setProviders(prov.providers);
        setDefaultProviderId(prov.settings.default_provider_id);
        setDefaultModelId(prov.settings.default_model_id);
        setProviderId(prov.settings.default_provider_id);
        setModelId(prov.settings.default_model_id);
        setTemplates(tplRes.templates);
        const tid = templateParam || "";
        if (tid) {
          const tpl = tplRes.templates.find((t) => t.id === tid);
          if (tpl) {
            setSelectedTemplateId(tid);
            applyTemplate(tpl);
          }
        }
      })
      .catch(() => {});
  }, [templateParam]);

  useEffect(() => {
    if (!genericCatalog.length) return;
    setAgentTopology((prev) => prev ?? defaultTopology("orchestrator", genericCatalog));
  }, [genericCatalog]);

  useEffect(() => {
    if (advancedMode && agentType === "doc_to_sheets" && !templateParam) {
      setAgentType("workflow");
    }
  }, [advancedMode, agentType, templateParam]);

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

  const sendTopology =
    !isDoc &&
    !!agentTopology &&
    (advancedMode || !!selectedTemplateId);

  const topologyPayload = sendTopology && agentTopology ? topologyForApi(agentTopology) : undefined;

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
    if (sendTopology && agentTopology) {
      const topoErr = validateTopology(agentTopology);
      if (topoErr) {
        setError(topoErr);
        return;
      }
    }
    setBusy(true);
    setError(null);
    try {
      let created;
      if (file && (isDoc || agentType === "workflow")) {
        const form = new FormData();
        form.append("title", title.trim());
        form.append("description", description.trim());
        form.append("priority", priority);
        form.append("agent_type", agentType);
        if (isDoc) {
          form.append("sheet_url", sheetUrl.trim());
        }
        if (topologyPayload) {
          form.append("agent_topology_json", JSON.stringify(topologyPayload));
        }
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
          agent_topology: topologyPayload,
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
      <PageHeader
        title="Submit a request"
        description="Choose an agent, describe what you need, and run it with approval checkpoints along the way."
      />

      <form onSubmit={onSubmit} className="space-y-5">
        {templates.length > 0 && (
          <section className="oma-section space-y-2">
            <label className="oma-label block">Start from workflow template</label>
            <select
              className="oma-input"
              value={selectedTemplateId}
              onChange={(e) => {
                const id = e.target.value;
                setSelectedTemplateId(id);
                const tpl = templates.find((t) => t.id === id);
                if (tpl) applyTemplate(tpl);
              }}
            >
              <option value="">None (custom)</option>
              {templates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
            <p className="oma-hint">
              Use {"{{date}}"} or {"{{week}}"} in descriptions — filled when you run from Workflows.
            </p>
          </section>
        )}

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
              const Icon = AgentTypeIcons[a.id];
              return (
                <button
                  key={a.id}
                  type="button"
                  onClick={() => setAgentType(a.id)}
                  className={[
                    "relative rounded-xl border p-4 text-left transition",
                    selected ? "ring-2" : "hover:opacity-90",
                  ].join(" ")}
                  style={{
                    borderColor: selected ? "var(--oma-primary)" : "var(--oma-border)",
                    backgroundColor: selected
                      ? "color-mix(in srgb, var(--oma-primary) 8%, var(--oma-surface))"
                      : "var(--oma-surface)",
                    ...(selected ? { boxShadow: "0 0 0 1px var(--oma-primary)" } : {}),
                  }}
                >
                  <span
                    className="flex h-10 w-10 items-center justify-center rounded-lg"
                    style={{
                      backgroundColor: "var(--oma-surface-elevated)",
                      color: "var(--oma-primary)",
                    }}
                  >
                    <Icon size={22} aria-hidden />
                  </span>
                  <p className="mt-2 font-medium" style={{ color: "var(--oma-text)" }}>
                    {a.name}
                  </p>
                  <p className="oma-hint mt-1 leading-relaxed">{a.description || meta.blurb}</p>
                  {selected && (
                    <Check
                      className="absolute right-3 top-3"
                      size={18}
                      style={{ color: "var(--oma-primary)" }}
                      aria-hidden
                    />
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
                  className="rounded-lg border px-4 py-2 text-left text-sm transition"
                  style={
                    priority === p.value
                      ? {
                          borderColor: "var(--oma-primary)",
                          backgroundColor:
                            "color-mix(in srgb, var(--oma-primary) 10%, var(--oma-surface))",
                          color: "var(--oma-text)",
                        }
                      : {
                          borderColor: "var(--oma-border)",
                          backgroundColor: "var(--oma-surface)",
                          color: "var(--oma-muted)",
                        }
                  }
                >
                  <span className="font-medium">{p.label}</span>
                  <span className="ml-2 text-xs opacity-70">{p.hint}</span>
                </button>
              ))}
            </div>
          </div>
        </section>

        {!isDoc && (
          <section className="oma-section space-y-3">
            <div>
              <h3 className="oma-label">Document (optional)</h3>
              <p className="oma-hint mt-0.5">
                Upload a PDF, spreadsheet, or text file for private-doc specialists. Copies are
                stored under data/uploads; excerpts may be sent to your LLM when the workflow runs.
              </p>
            </div>
            <FileDropzone file={file} onFileChange={setFile} disabled={busy} />
          </section>
        )}

        {!isDoc && advancedMode && agentTopology && (
          <AgentTopologyBuilder
            catalog={genericCatalog}
            value={agentTopology}
            onChange={setAgentTopology}
            disabled={busy}
          />
        )}

        {!isDoc && !advancedMode && (
          <p
            className="rounded-lg border px-4 py-3 text-sm"
            style={{
              borderColor: "var(--oma-border)",
              backgroundColor: "var(--oma-surface-elevated)",
              color: "var(--oma-muted)",
            }}
          >
            Agent builder is hidden. Enable{" "}
            <Link to="/settings" className="font-medium hover:underline" style={{ color: "var(--oma-primary)" }}>
              Advanced mode
            </Link>{" "}
            in Settings to customize specialists on the canvas, or pick a workflow template above.
          </p>
        )}

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
              className="shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium"
              style={
                useCustomLlm
                  ? {
                      backgroundColor: "color-mix(in srgb, var(--oma-primary) 15%, var(--oma-surface))",
                      color: "var(--oma-primary)",
                    }
                  : {
                      backgroundColor: "var(--oma-surface-elevated)",
                      color: "var(--oma-muted)",
                    }
              }
            >
              {useCustomLlm ? "Custom" : "Default"}
            </span>
          </button>

          {useCustomLlm && (
            <div
              className="grid gap-3 border-t pt-3 sm:grid-cols-2"
              style={{ borderColor: "var(--oma-border)" }}
            >
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
                  <Link to="/settings" className="font-medium hover:underline" style={{ color: "var(--oma-primary)" }}>
                    Configure in Settings
                  </Link>
                </p>
              )}
            </div>
          )}
        </section>

        {error && <Alert variant="error">{error}</Alert>}

        <div
          className="flex flex-col-reverse gap-3 border-t pt-5 sm:flex-row sm:items-center sm:justify-between"
          style={{ borderColor: "var(--oma-border)" }}
        >
          <Link to="/" className="oma-hint text-center text-sm hover:underline sm:text-left">
            ← Back to requests
          </Link>
          <Button
            type="submit"
            variant="primary"
            icon={Send}
            disabled={!canSubmit}
            className="!px-6 !py-2.5 !font-semibold"
          >
            {busy ? "Starting agent…" : isDoc ? "Upload & start extraction" : "Submit request"}
          </Button>
        </div>
      </form>
    </div>
  );
}
