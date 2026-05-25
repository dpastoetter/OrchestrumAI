import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Alert } from "./ui/Alert";
import { Button } from "./ui/Button";

const STORAGE_KEY = "orchestrumai_onboarding_done";

export function OnboardingBanner() {
  const [visible, setVisible] = useState(false);
  const [stubOk, setStubOk] = useState(false);

  useEffect(() => {
    if (localStorage.getItem(STORAGE_KEY)) return;
    setVisible(true);
    api.health().then((h) => setStubOk(h.features?.includes("requests") ?? false)).catch(() => {});
  }, []);

  if (!visible) return null;

  function dismiss() {
    localStorage.setItem(STORAGE_KEY, "1");
    setVisible(false);
  }

  return (
    <div className="mb-6">
    <Alert
      variant="info"
      title="Welcome"
      action={
        <Button variant="secondary" size="sm" onClick={dismiss}>
          Got it
        </Button>
      }
    >
      <p>
        Workflow history, templates, and uploads are stored locally. When a run executes, prompts
        and relevant document excerpts go to your chosen LLM (not in stub mode). Connect a provider
        in Settings, pick a workflow template, and approve plans before anything runs.
      </p>
      <ol className="mt-2 list-decimal list-inside space-y-1 text-sm">
        <li>
          <Link to="/settings" className="font-medium hover:underline" style={{ color: "var(--oma-primary)" }}>
            Configure AI provider
          </Link>{" "}
          (or use stub mode: ORCHESTRUMAI_STUB_RUN=1)
        </li>
        <li>
          <Link to="/workflows" className="font-medium hover:underline" style={{ color: "var(--oma-primary)" }}>
            Open My workflows
          </Link>{" "}
          and run a built-in template
        </li>
        <li>Approve the plan when prompted, then review the result</li>
      </ol>
      {stubOk && (
        <p className="mt-2 text-xs" style={{ color: "var(--oma-muted)" }}>
          Backend is reachable. Stub mode works without API keys.
        </p>
      )}
    </Alert>
    </div>
  );
}
