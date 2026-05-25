import type { GenericWorkflowAgent } from "../types";

interface WorkflowAgentTogglesProps {
  catalog: GenericWorkflowAgent[];
  enabled: Set<string>;
  onToggle: (id: string) => void;
  disabled?: boolean;
  hint?: string;
}

export function WorkflowAgentToggles({
  catalog,
  enabled,
  onToggle,
  disabled,
  hint,
}: WorkflowAgentTogglesProps) {
  if (catalog.length === 0) {
    return <p className="oma-hint">Loading workflow agents…</p>;
  }
  return (
    <div className="space-y-2">
      {hint && <p className="oma-hint">{hint}</p>}
      <div className="space-y-2">
        {catalog.map((agent) => (
          <label
            key={agent.id}
            className={[
              "flex cursor-pointer items-start gap-3 rounded-lg border px-3 py-2.5 transition",
              disabled ? "cursor-not-allowed opacity-50" : "",
            ].join(" ")}
            style={{
              borderColor: enabled.has(agent.id) ? "var(--oma-primary)" : "var(--oma-border)",
              backgroundColor: enabled.has(agent.id)
                ? "color-mix(in srgb, var(--oma-primary) 8%, var(--oma-surface))"
                : "var(--oma-surface-elevated)",
            }}
          >
            <input
              type="checkbox"
              className="mt-1"
              checked={enabled.has(agent.id)}
              disabled={disabled}
              onChange={() => onToggle(agent.id)}
            />
            <span className="min-w-0 flex-1">
              <span className="font-medium" style={{ color: "var(--oma-text)" }}>
                {agent.name}
              </span>
              <span className="oma-hint mt-0.5 block">{agent.description}</span>
            </span>
          </label>
        ))}
      </div>
    </div>
  );
}
