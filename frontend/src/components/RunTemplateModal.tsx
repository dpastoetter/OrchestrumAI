import { FormEvent, useEffect, useState } from "react";
import type { WorkflowTemplate } from "../types";
import { extractCustomVars } from "../lib/templateVars";
import { Button } from "./ui/Button";

export function RunTemplateModal({
  template,
  onCancel,
  onRun,
  busy,
}: {
  template: WorkflowTemplate;
  onCancel: () => void;
  onRun: (vars: Record<string, string>, title: string) => void;
  busy: boolean;
}) {
  const customVars = extractCustomVars(template.description_template);
  const [title, setTitle] = useState(template.name);
  const [values, setValues] = useState<Record<string, string>>({});

  useEffect(() => {
    const init: Record<string, string> = {};
    for (const v of customVars) init[v] = "";
    setValues(init);
  }, [template.id]);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    onRun(values, title.trim() || template.name);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-md space-y-4 rounded-xl border p-6 shadow-xl"
        style={{ borderColor: "var(--oma-border)", backgroundColor: "var(--oma-surface)" }}
      >
        <h3 className="text-lg font-medium" style={{ color: "var(--oma-text)" }}>
          Run: {template.name}
        </h3>
        <p className="oma-hint text-sm line-clamp-3">{template.description_template}</p>
        <label className="block space-y-1">
          <span className="oma-label">Run title</span>
          <input className="oma-input" value={title} onChange={(e) => setTitle(e.target.value)} />
        </label>
        {customVars.map((v) => (
          <label key={v} className="block space-y-1">
            <span className="oma-label">{`{{${v}}}`}</span>
            <input
              className="oma-input"
              value={values[v] ?? ""}
              onChange={(e) => setValues((prev) => ({ ...prev, [v]: e.target.value }))}
            />
          </label>
        ))}
        <p className="oma-hint text-xs">
          Built-in placeholders (date, week, etc.) are filled automatically.
        </p>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy}>
            Run
          </Button>
        </div>
      </form>
    </div>
  );
}
