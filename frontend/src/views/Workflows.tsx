import {
  Calendar,
  Clock,
  Copy,
  Download,
  Network,
  Pin,
  Play,
  Plus,
  Trash2,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { AgentTopologyBuilder } from "../components/topology/AgentTopologyBuilder";
import {
  defaultTopology,
  topologyForApi,
  validateTopology,
  type AgentTopology,
} from "../components/topology/topologyTypes";
import { useWorkflowPreferences } from "../context/WorkflowPreferencesContext";
import { RunTemplateModal } from "../components/RunTemplateModal";
import { getPinnedTemplateIds, togglePinned } from "../lib/pinnedTemplates";
import { resolveTemplateIcon } from "../lib/templateIcon";
import { statusToBadgeVariant } from "../components/ui/Badge";
import type {
  GenericWorkflowAgent,
  RequestSummary,
  WorkflowSchedule,
  WorkflowTemplate,
} from "../types";
import { Alert } from "../components/ui/Alert";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { PageHeader } from "../components/ui/PageHeader";

const CRON_PRESETS: { label: string; cron: string }[] = [
  { label: "Daily at 8:00", cron: "0 8 * * *" },
  { label: "Weekdays at 8:00", cron: "0 8 * * 1-5" },
  { label: "Monday at 8:00", cron: "0 8 * * 1" },
  { label: "1st of month at 8:00", cron: "0 8 1 * *" },
];

function formatNextRun(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

function lastRunForTemplate(requests: RequestSummary[], templateId: string): RequestSummary | null {
  const matches = requests.filter((r) => r.workflow_template_id === templateId);
  if (!matches.length) return null;
  return matches.sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  )[0];
}

function topologyFromTemplate(t: WorkflowTemplate, catalog: GenericWorkflowAgent[]): AgentTopology {
  if (t.agent_topology) {
    return {
      type: t.agent_topology.type,
      nodes: t.agent_topology.nodes,
      edges: t.agent_topology.edges ?? [],
    };
  }
  return defaultTopology("orchestrator", catalog);
}

export function Workflows() {
  const navigate = useNavigate();
  const { advancedMode, catalog } = useWorkflowPreferences();
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [schedules, setSchedules] = useState<WorkflowSchedule[]>([]);
  const [requests, setRequests] = useState<RequestSummary[]>([]);
  const [pinned, setPinned] = useState<Set<string>>(() => getPinnedTemplateIds());
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [scheduleFor, setScheduleFor] = useState<string | null>(null);
  const [cronPreset, setCronPreset] = useState(CRON_PRESETS[0].cron);
  const [scheduleOnApproval, setScheduleOnApproval] = useState<"pause" | "skip_plan">("pause");
  const [timezone, setTimezone] = useState(
    Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
  );
  const [runModalTemplate, setRunModalTemplate] = useState<WorkflowTemplate | null>(null);
  const [topologyEditId, setTopologyEditId] = useState<string | null>(null);
  const [editTopology, setEditTopology] = useState<AgentTopology | null>(null);

  const load = useCallback(async () => {
    try {
      const [tplRes, schedRes, reqList] = await Promise.all([
        api.listWorkflowTemplates(),
        api.listWorkflowSchedules(),
        api.listRequests(),
      ]);
      setTemplates(tplRes.templates);
      setSchedules(schedRes.schedules);
      setRequests(reqList);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [load]);

  async function runTemplate(id: string, body?: { title?: string; description_vars?: Record<string, string> }) {
    setBusyId(id);
    try {
      const summary = await api.runWorkflowTemplate(id, body);
      setRunModalTemplate(null);
      navigate(`/requests/${summary.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyId(null);
    }
  }

  function openTopologyEdit(t: WorkflowTemplate) {
    setTopologyEditId(topologyEditId === t.id ? null : t.id);
    setEditTopology(topologyFromTemplate(t, catalog));
  }

  async function saveTemplateTopology(t: WorkflowTemplate) {
    if (!editTopology) return;
    const topoErr = validateTopology(editTopology);
    if (topoErr) {
      setError(topoErr);
      return;
    }
    setBusyId(t.id);
    try {
      await api.updateWorkflowTemplate(t.id, {
        name: t.name,
        description_template: t.description_template,
        agent_type: t.agent_type,
        agent_topology: topologyForApi(editTopology),
        default_priority: t.default_priority,
        provider_id: t.provider_id,
        model_id: t.model_id,
        require_plan_approval: t.require_plan_approval,
        icon: t.icon,
        category: t.category,
      });
      setTopologyEditId(null);
      setEditTopology(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyId(null);
    }
  }

  async function duplicateTemplate(t: WorkflowTemplate) {
    setBusyId(t.id);
    try {
      await api.createWorkflowTemplate({
        name: `${t.name} (copy)`,
        description_template: t.description_template,
        agent_type: t.agent_type,
        agent_topology: t.agent_topology ?? undefined,
        default_priority: t.default_priority,
        provider_id: t.provider_id,
        model_id: t.model_id,
        require_plan_approval: t.require_plan_approval,
        icon: t.icon,
        category: t.category,
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyId(null);
    }
  }

  async function deleteTemplate(id: string) {
    if (!confirm("Delete this workflow template and its schedules?")) return;
    setBusyId(id);
    try {
      await api.deleteWorkflowTemplate(id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyId(null);
    }
  }

  async function onCreateSchedule(e: FormEvent, templateId: string) {
    e.preventDefault();
    setBusyId(templateId);
    try {
      await api.createWorkflowSchedule({
        template_id: templateId,
        cron_expression: cronPreset,
        timezone,
        enabled: true,
        on_approval: scheduleOnApproval,
      });
      setScheduleFor(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyId(null);
    }
  }

  async function toggleSchedule(sched: WorkflowSchedule) {
    setBusyId(sched.id);
    try {
      await api.updateWorkflowSchedule(sched.id, {
        template_id: sched.template_id,
        cron_expression: sched.cron_expression,
        timezone: sched.timezone,
        enabled: !sched.enabled,
        description_vars: sched.description_vars,
        on_approval: sched.on_approval as "pause" | "skip_plan",
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyId(null);
    }
  }

  async function triggerSchedule(schedId: string) {
    setBusyId(schedId);
    try {
      const summary = await api.triggerWorkflowSchedule(schedId);
      navigate(`/requests/${summary.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyId(null);
    }
  }

  const sortedTemplates = useMemo(() => {
    return [...templates].sort((a, b) => {
      const ap = pinned.has(a.id) ? 0 : 1;
      const bp = pinned.has(b.id) ? 0 : 1;
      if (ap !== bp) return ap - bp;
      return a.name.localeCompare(b.name);
    });
  }, [templates, pinned]);

  const byCategory = sortedTemplates.reduce<Record<string, WorkflowTemplate[]>>((acc, t) => {
    const cat = t.category || "general";
    (acc[cat] ??= []).push(t);
    return acc;
  }, {});

  return (
    <div className="space-y-8">
      <PageHeader
        title="My workflows"
        description={
          advancedMode
            ? "Saved templates — run, schedule, or edit agent topology inline."
            : "Saved templates for personal automation — run now or on a schedule."
        }
        actions={
          <Link to="/submit" className="oma-btn-primary !no-underline">
            <Plus size={16} aria-hidden />
            New one-off request
          </Link>
        }
      />

      {error && <Alert variant="error">{error}</Alert>}

      {templates.length === 0 ? (
        <EmptyState
          title="No workflows yet"
          description="Bundled templates import on first backend start, or save a completed request as a template."
        />
      ) : (
        Object.entries(byCategory).map(([category, items]) => (
          <section key={category} className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--oma-muted)" }}>
              {category}
            </h3>
            <div className="grid gap-3 sm:grid-cols-2">
              {items.map((t) => {
                const TplIcon = resolveTemplateIcon(t.icon);
                const last = lastRunForTemplate(requests, t.id);
                const isPinned = pinned.has(t.id);
                return (
                  <Card key={t.id} className="space-y-3">
                    <div className="flex items-start gap-3">
                      <span
                        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg"
                        style={{
                          backgroundColor: "var(--oma-surface-elevated)",
                          color: "var(--oma-primary)",
                        }}
                      >
                        <TplIcon size={20} aria-hidden />
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <h4 className="font-medium" style={{ color: "var(--oma-text)" }}>
                            {t.name}
                          </h4>
                          {isPinned && <Pin size={14} style={{ color: "var(--oma-primary)" }} />}
                        </div>
                        {t.bundled && <Badge variant="neutral">Built-in</Badge>}
                        <p className="oma-hint mt-1 line-clamp-2">{t.description_template}</p>
                        {last ? (
                          <p className="mt-1 text-xs">
                            <span className="oma-hint">Last run: </span>
                            <Link
                              to={`/requests/${last.id}`}
                              className="font-medium hover:underline"
                              style={{ color: "var(--oma-primary)" }}
                            >
                              {new Date(last.created_at).toLocaleString()}
                            </Link>
                            {" · "}
                            <Badge variant={statusToBadgeVariant(last.status)}>
                              {last.status === "awaiting_approval"
                                ? "Awaiting approval"
                                : last.status}
                            </Badge>
                          </p>
                        ) : (
                          <p className="oma-hint mt-1 text-xs">No runs yet</p>
                        )}
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        variant="primary"
                        size="sm"
                        icon={Play}
                        disabled={busyId === t.id}
                        onClick={() => setRunModalTemplate(t)}
                      >
                        Run
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        icon={Pin}
                        onClick={() => setPinned(togglePinned(t.id))}
                      >
                        {isPinned ? "Unpin" : "Pin"}
                      </Button>
                      <Link to={`/submit?template=${t.id}`} className="oma-btn-secondary !text-xs !py-1">
                        Customize
                      </Link>
                      {advancedMode && t.agent_type === "workflow" && (
                        <Button
                          variant="secondary"
                          size="sm"
                          icon={Network}
                          onClick={() => openTopologyEdit(t)}
                        >
                          {topologyEditId === t.id ? "Hide agents" : "Edit agents"}
                        </Button>
                      )}
                      <Button
                        variant="secondary"
                        size="sm"
                        icon={Calendar}
                        onClick={() => setScheduleFor(scheduleFor === t.id ? null : t.id)}
                      >
                        Schedule
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        icon={Copy}
                        disabled={busyId === t.id}
                        onClick={() => duplicateTemplate(t)}
                      >
                        Duplicate
                      </Button>
                      <a
                        href={api.exportWorkflowTemplateUrl(t.id)}
                        className="oma-btn-secondary !text-xs !py-1 !no-underline inline-flex items-center gap-1"
                        download
                      >
                        <Download size={14} aria-hidden />
                        Export
                      </a>
                      {!t.bundled && (
                        <Button
                          variant="danger"
                          size="sm"
                          icon={Trash2}
                          disabled={busyId === t.id}
                          onClick={() => deleteTemplate(t.id)}
                        >
                          Delete
                        </Button>
                      )}
                    </div>
                    {topologyEditId === t.id && editTopology && advancedMode && (
                      <div
                        className="space-y-3 border-t pt-3"
                        style={{ borderColor: "var(--oma-border)" }}
                      >
                        <AgentTopologyBuilder
                          catalog={catalog}
                          value={editTopology}
                          onChange={setEditTopology}
                          disabled={busyId === t.id}
                        />
                        <Button
                          variant="primary"
                          size="sm"
                          disabled={busyId === t.id}
                          onClick={() => saveTemplateTopology(t)}
                        >
                          Save template topology
                        </Button>
                      </div>
                    )}
                    {scheduleFor === t.id && (
                      <form
                        onSubmit={(e) => onCreateSchedule(e, t.id)}
                        className="space-y-2 border-t pt-3"
                        style={{ borderColor: "var(--oma-border)" }}
                      >
                        <label className="block text-xs" style={{ color: "var(--oma-muted)" }}>
                          Preset
                          <select
                            className="oma-input mt-1"
                            value={cronPreset}
                            onChange={(e) => setCronPreset(e.target.value)}
                          >
                            {CRON_PRESETS.map((p) => (
                              <option key={p.cron} value={p.cron}>
                                {p.label} ({p.cron})
                              </option>
                            ))}
                          </select>
                        </label>
                        <label className="block text-xs" style={{ color: "var(--oma-muted)" }}>
                          Timezone
                          <input
                            className="oma-input mt-1"
                            value={timezone}
                            onChange={(e) => setTimezone(e.target.value)}
                          />
                        </label>
                        <label className="block text-xs" style={{ color: "var(--oma-muted)" }}>
                          When plan approval is needed
                          <select
                            className="oma-input mt-1"
                            value={scheduleOnApproval}
                            onChange={(e) =>
                              setScheduleOnApproval(e.target.value as "pause" | "skip_plan")
                            }
                          >
                            <option value="pause">Pause for my approval</option>
                            <option value="skip_plan">Auto-run (skip plan approval)</option>
                          </select>
                        </label>
                        <Button type="submit" variant="primary" size="sm" disabled={busyId === t.id}>
                          Add schedule
                        </Button>
                      </form>
                    )}
                  </Card>
                );
              })}
            </div>
          </section>
        ))
      )}

      <section className="space-y-3">
        <h3 className="text-sm font-medium" style={{ color: "var(--oma-muted)" }}>
          Scheduled runs
        </h3>
        <p className="oma-hint">
          Cron runs while the backend is running (see README for systemd setup).
        </p>
        {schedules.length === 0 ? (
          <p className="text-sm" style={{ color: "var(--oma-muted)" }}>
            No schedules yet.
          </p>
        ) : (
          <ul
            className="divide-y rounded-xl border overflow-hidden"
            style={{ borderColor: "var(--oma-border)", backgroundColor: "var(--oma-surface)" }}
          >
            {schedules.map((s) => (
              <li
                key={s.id}
                className="flex flex-wrap items-center justify-between gap-3 px-4 py-3"
              >
                <div className="flex items-start gap-2">
                  <Clock size={16} className="mt-0.5 shrink-0" style={{ color: "var(--oma-muted)" }} />
                  <div>
                    <div className="text-sm font-medium" style={{ color: "var(--oma-text)" }}>
                      {s.template_name}
                    </div>
                    <div className="oma-hint">
                      {s.cron_expression} · {s.timezone} · next {formatNextRun(s.next_run_at)}
                    </div>
                    <Badge variant={s.on_approval === "skip_plan" ? "done" : "awaiting"}>
                      {s.on_approval === "skip_plan" ? "Auto-run" : "Pause for approval"}
                    </Badge>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant={s.enabled ? "primary" : "secondary"}
                    size="sm"
                    disabled={busyId === s.id}
                    onClick={() => toggleSchedule(s)}
                  >
                    {s.enabled ? "On" : "Off"}
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    icon={Play}
                    disabled={busyId === s.id}
                    onClick={() => triggerSchedule(s.id)}
                  >
                    Run now
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {runModalTemplate && (
        <RunTemplateModal
          template={runModalTemplate}
          busy={busyId === runModalTemplate.id}
          onCancel={() => setRunModalTemplate(null)}
          onRun={(vars, title) =>
            runTemplate(runModalTemplate.id, { description_vars: vars, title })
          }
        />
      )}
    </div>
  );
}
