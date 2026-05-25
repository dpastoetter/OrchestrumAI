import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import type { AgentInfo, AgentType, Priority } from "../types";

export function SubmitRequest() {
  const navigate = useNavigate();
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [useCustomLlm, setUseCustomLlm] = useState(false);
  const [providerId, setProviderId] = useState("");
  const [modelId, setModelId] = useState("");
  const [providers, setProviders] = useState<{ id: string; models: { id: string; label: string }[] }[]>([]);
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
    api.getProviders().then((d) => {
      setProviders(d.providers);
      setProviderId(d.settings.default_provider_id);
      setModelId(d.settings.default_model_id);
    }).catch(() => {});
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!title.trim() || !description.trim()) return;
    if (agentType === "doc_to_sheets" && !file) {
      setError("Please choose a document to upload (PDF, CSV, or XLSX).");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      let created;
      if (agentType === "doc_to_sheets" && file) {
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

  const isDoc = agentType === "doc_to_sheets";

  return (
    <form onSubmit={onSubmit} className="space-y-4 rounded-lg border border-slate-800 bg-slate-900/50 p-6">
      <h2 className="text-lg font-medium">Submit a request</h2>

      <label className="block space-y-1">
        <span className="text-sm text-slate-400">Agent</span>
        <select
          className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
          value={agentType}
          onChange={(e) => setAgentType(e.target.value as AgentType)}
        >
          {(agents.length ? agents : [
            { id: "workflow" as const, name: "General workflow", description: "" },
            { id: "doc_to_sheets" as const, name: "Document → Sheets", description: "" },
          ]).map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </select>
      </label>

      {isDoc && (
        <>
          <label className="block space-y-1">
            <span className="text-sm text-slate-400">Document (PDF, CSV, XLSX, image)</span>
            <input
              type="file"
              accept=".pdf,.csv,.xlsx,.xls,.png,.jpg,.jpeg,.webp"
              className="w-full text-sm text-slate-300"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              required
            />
          </label>
          <label className="block space-y-1">
            <span className="text-sm text-slate-400">Google Sheet URL or ID (optional)</span>
            <input
              className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
              value={sheetUrl}
              onChange={(e) => setSheetUrl(e.target.value)}
              placeholder="https://docs.google.com/spreadsheets/d/..."
            />
          </label>
        </>
      )}

      <label className="block space-y-1">
        <span className="text-sm text-slate-400">Title</span>
        <input
          className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          maxLength={200}
          required
        />
      </label>
      <label className="block space-y-1">
        <span className="text-sm text-slate-400">{isDoc ? "Notes / extraction hints" : "Goal / description"}</span>
        <textarea
          className="min-h-[120px] w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          required
        />
      </label>
      <label className="flex items-center gap-2 text-sm text-slate-400">
        <input
          type="checkbox"
          checked={useCustomLlm}
          onChange={(e) => setUseCustomLlm(e.target.checked)}
        />
        Override default AI provider for this request
      </label>
      {useCustomLlm && (
        <div className="grid grid-cols-2 gap-2">
          <select
            className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
            value={providerId}
            onChange={(e) => {
              setProviderId(e.target.value);
              const p = providers.find((x) => x.id === e.target.value);
              if (p?.models[0]) setModelId(p.models[0].id);
            }}
          >
            {providers.map((p) => (
              <option key={p.id} value={p.id}>
                {p.id}
              </option>
            ))}
          </select>
          <select
            className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
            value={modelId}
            onChange={(e) => setModelId(e.target.value)}
          >
            {(providers.find((p) => p.id === providerId)?.models ?? []).map((m) => (
              <option key={m.id} value={m.id}>
                {m.label}
              </option>
            ))}
          </select>
        </div>
      )}

      <label className="block space-y-1">
        <span className="text-sm text-slate-400">Priority</span>
        <select
          className="rounded border border-slate-700 bg-slate-950 px-3 py-2"
          value={priority}
          onChange={(e) => setPriority(e.target.value as Priority)}
        >
          <option value="low">Low</option>
          <option value="normal">Normal</option>
          <option value="high">High</option>
        </select>
      </label>
      {error && <p className="text-sm text-red-400">{error}</p>}
      <button
        type="submit"
        disabled={busy}
        className="rounded bg-sky-600 px-4 py-2 text-sm font-medium hover:bg-sky-500 disabled:opacity-50"
      >
        {busy ? "Submitting…" : isDoc ? "Upload & extract" : "Submit request"}
      </button>
    </form>
  );
}
