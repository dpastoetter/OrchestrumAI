import { Bot, FolderOpen, Key, Plug, Shield } from "lucide-react";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { WorkflowAgentToggles } from "../components/WorkflowAgentToggles";
import { Alert } from "../components/ui/Alert";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { PageHeader } from "../components/ui/PageHeader";
import { api, type ChatGPTOAuthStatus, type ProviderCatalogItem, type ProviderSettings } from "../api";
import { useWorkflowPreferences } from "../context/WorkflowPreferencesContext";
import type { AutomationSettings } from "../types";

const ENV_LABELS: Record<string, string> = {
  GOOGLE_API_KEY: "Google / Gemini API key",
  OPENAI_API_KEY: "OpenAI API key",
  ANTHROPIC_API_KEY: "Anthropic API key",
  OPENROUTER_API_KEY: "OpenRouter API key",
};

export function Settings() {
  const [providers, setProviders] = useState<ProviderCatalogItem[]>([]);
  const [settings, setSettings] = useState<ProviderSettings | null>(null);
  const [selectedProvider, setSelectedProvider] = useState("gemini");
  const [selectedModel, setSelectedModel] = useState("gemini-2.5-flash");
  const [apiKeys, setApiKeys] = useState<Record<string, string>>({});
  const [ollamaHost, setOllamaHost] = useState("http://127.0.0.1:11434");
  const [lmStudioUrl, setLmStudioUrl] = useState("http://127.0.0.1:1234/v1");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [chatgptOAuth, setChatgptOAuth] = useState<ChatGPTOAuthStatus | null>(null);
  const [oauthSessionId, setOauthSessionId] = useState<string | null>(null);
  const [oauthCallbackUrl, setOauthCallbackUrl] = useState("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const {
    advancedMode,
    enabledGeneric,
    catalog: genericCatalog,
    setAdvancedMode,
    setEnabledGeneric,
    saveWorkflowPreferences,
    loadError: workflowLoadError,
  } = useWorkflowPreferences();
  const [workflowBusy, setWorkflowBusy] = useState(false);
  const [automation, setAutomation] = useState<AutomationSettings | null>(null);
  const [automationBusy, setAutomationBusy] = useState(false);

  const providerApiError = (err: unknown) => {
    const msg = err instanceof Error ? err.message : String(err);
    if (msg.includes("Not Found") || msg.includes("404")) {
      return (
        "Provider API is not available on the backend. Stop the old server and run " +
        "make dev-backend from the project root, then reload this page."
      );
    }
    return msg;
  };

  const load = useCallback(async () => {
    const health = await api.health();
    if (!health.features?.includes("providers")) {
      throw new Error("STALE_BACKEND");
    }
    const data = await api.getProviders();
    setProviders(data.providers);
    setSettings(data.settings);
    setSelectedProvider(data.settings.default_provider_id);
    setSelectedModel(data.settings.default_model_id);
    setOllamaHost(data.settings.ollama_host);
    setLmStudioUrl(data.settings.lm_studio_base_url);
    const oauth = await api.getChatGPTOAuthStatus();
    setChatgptOAuth(oauth);
    try {
      const auto = await api.getAutomationSettings();
      setAutomation(auto.settings);
    } catch {
      /* automation API optional during partial deploy */
    }
  }, []);

  useEffect(() => {
    load().catch((e) => {
      const msg = String(e);
      setError(
        msg.includes("STALE_BACKEND")
          ? providerApiError(new Error("Not Found"))
          : providerApiError(e),
      );
    });
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [load]);

  const current = providers.find((p) => p.id === selectedProvider);

  async function onSave(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const data = await api.updateProviderSettings({
        default_provider_id: selectedProvider,
        default_model_id: selectedModel,
        api_keys: apiKeys,
        ollama_host: ollamaHost,
        lm_studio_base_url: lmStudioUrl,
      });
      setProviders(data.providers);
      setSettings(data.settings);
      setApiKeys({});
      setMessage("Settings saved. New requests will use this provider.");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function refreshOAuth() {
    const oauth = await api.getChatGPTOAuthStatus();
    setChatgptOAuth(oauth);
    const data = await api.getProviders();
    setProviders(data.providers);
  }

  async function onConnectChatGPT() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const conn = await api.connectChatGPTOAuth();
      setOauthSessionId(conn.session_id);
      window.open(conn.authorize_url, "_blank", "noopener,noreferrer");
      setMessage(
        `Sign in in the browser. Callback listens on port ${conn.callback_port}.`,
      );
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(async () => {
        try {
          const st = await api.pollChatGPTOAuthSession(conn.session_id);
          if (st.status === "connected") {
            if (pollRef.current) clearInterval(pollRef.current);
            setOauthSessionId(null);
            setMessage("ChatGPT account connected.");
            await refreshOAuth();
          } else if (st.status === "error") {
            if (pollRef.current) clearInterval(pollRef.current);
            setError(st.error ?? "OAuth failed");
          }
        } catch {
          /* ignore poll errors */
        }
      }, 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function onPasteCallback() {
    if (!oauthSessionId || !oauthCallbackUrl.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const st = await api.submitChatGPTOAuthCallback(oauthSessionId, oauthCallbackUrl.trim());
      if (st.status === "connected") {
        setMessage("ChatGPT account connected.");
        setOauthSessionId(null);
        setOauthCallbackUrl("");
        await refreshOAuth();
      } else {
        setError(st.error ?? "Could not complete OAuth");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  function toggleGenericAgent(id: string) {
    const next = new Set(enabledGeneric);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setEnabledGeneric(next);
  }

  async function onAdvancedModeChange(checked: boolean) {
    setWorkflowBusy(true);
    setError(null);
    setMessage(null);
    try {
      await setAdvancedMode(checked);
      setMessage(checked ? "Advanced mode enabled." : "Advanced mode disabled.");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setWorkflowBusy(false);
    }
  }

  async function onSaveWorkflowAgents() {
    setWorkflowBusy(true);
    setError(null);
    setMessage(null);
    try {
      await saveWorkflowPreferences({
        enabled_generic_agents: [...enabledGeneric],
      });
      setMessage("Default specialists saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setWorkflowBusy(false);
    }
  }

  async function onDisconnectChatGPT() {
    setBusy(true);
    setError(null);
    try {
      await api.disconnectChatGPTOAuth();
      setMessage("ChatGPT disconnected.");
      await refreshOAuth();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function onSaveAutomation(e: FormEvent) {
    e.preventDefault();
    if (!automation) return;
    setAutomationBusy(true);
    setError(null);
    setMessage(null);
    try {
      const res = await api.updateAutomationSettings({
        inbox_watch_enabled: automation.inbox_watch_enabled,
        webhook_url: automation.webhook_url,
        markdown_export_dir: automation.markdown_export_dir,
        desktop_notify: automation.desktop_notify,
      });
      setAutomation(res.settings);
      setMessage("Automation settings saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setAutomationBusy(false);
    }
  }

  async function onScanInbox() {
    setAutomationBusy(true);
    try {
      const res = await api.scanInbox();
      setMessage(`Inbox scan complete. Created ${res.created} request(s).`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setAutomationBusy(false);
    }
  }

  async function onTest() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const r = await api.testProvider(selectedProvider, selectedModel);
      setMessage(r.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  function statusBadge(status: string) {
    const variant =
      status === "connected"
        ? "done"
        : status === "needs_config"
          ? "awaiting"
          : "neutral";
    return <Badge variant={variant}>{status.replace("_", " ")}</Badge>;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings"
        description="Connect API keys, local Ollama/LM Studio, Gemini native, or ChatGPT Plus/Pro OAuth."
      />

      <Alert variant="info" title="Privacy">
        <Shield className="inline h-4 w-4 mr-1 -mt-0.5" aria-hidden />
        Requests, templates, schedules, and upload files are stored locally under{" "}
        <code className="font-mono text-xs">data/</code>. During runs, your chosen LLM provider
        receives prompts and any content the workflow needs (unless you use stub mode).
      </Alert>

      <section className="oma-section space-y-4">
        <div>
          <h3 className="oma-label">Workflow preferences</h3>
          <p className="oma-hint mt-0.5">
            Control how much agent configuration you see when submitting requests.
          </p>
        </div>

        <label
          className="flex cursor-pointer items-start gap-3 rounded-lg border p-4"
          style={{ borderColor: "var(--oma-border)", backgroundColor: "var(--oma-surface-elevated)" }}
        >
          <input
            type="checkbox"
            className="mt-1 rounded border-slate-600"
            checked={advancedMode}
            onChange={(e) => void onAdvancedModeChange(e.target.checked)}
            disabled={workflowBusy}
          />
          <span className="space-y-1">
            <span className="block text-sm font-medium" style={{ color: "var(--oma-text)" }}>
              Advanced mode
            </span>
            <span className="oma-hint block">
              Saves immediately. Shows the agent builder on New request and lets you edit template
              topology on Workflows. When off, use templates or the default specialist list below.
            </span>
          </span>
        </label>

        {workflowLoadError && (
          <Alert variant="error">
            Workflow settings could not be loaded: {workflowLoadError}. Restart the backend with{" "}
            <code className="font-mono text-xs">make dev-backend</code>.
          </Alert>
        )}

        {!advancedMode && (
          <div className="space-y-3">
            <div>
              <h4 className="text-sm font-medium flex items-center gap-2" style={{ color: "var(--oma-text)" }}>
                <Bot size={16} aria-hidden />
                Default specialists
              </h4>
              <p className="oma-hint mt-0.5">
                Used for new workflow requests when you are not using a saved template topology.
              </p>
            </div>
            <WorkflowAgentToggles
              catalog={genericCatalog}
              enabled={enabledGeneric}
              onToggle={toggleGenericAgent}
              disabled={workflowBusy}
            />
          </div>
        )}

        {!advancedMode && (
          <Button type="button" variant="secondary" disabled={workflowBusy} onClick={onSaveWorkflowAgents}>
            Save default specialists
          </Button>
        )}
      </section>

      <Card>
      <form onSubmit={onSave} className="space-y-4">
        <label className="block space-y-1">
          <span className="oma-label flex items-center gap-2">
            <Plug size={16} aria-hidden />
            Default provider
          </span>
          <select
            className="oma-input"
            value={selectedProvider}
            onChange={(e) => {
              const id = e.target.value;
              setSelectedProvider(id);
              const p = providers.find((x) => x.id === id);
              if (p?.models[0]) setSelectedModel(p.models[0].id);
            }}
          >
            {providers.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.status})
              </option>
            ))}
          </select>
        </label>

        {current && (
          <div className="flex items-center gap-2 text-sm">
            {statusBadge(current.status)}
            <span className="oma-hint">{current.description}</span>
            {current.docs_url && (
              <a className="font-medium hover:underline" style={{ color: "var(--oma-primary)" }} href={current.docs_url} target="_blank" rel="noreferrer">
                Docs
              </a>
            )}
          </div>
        )}

        <label className="block space-y-1">
          <span className="oma-label">Model</span>
          <select
            className="oma-input"
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
          >
            {(current?.models ?? []).map((m) => (
              <option key={m.id} value={m.id}>
                {m.label}
              </option>
            ))}
          </select>
        </label>

        {current?.auth_type === "api_key" &&
          current.env_vars.map((env) => (
            <label key={env} className="block space-y-1">
              <span className="oma-label flex items-center gap-2">
                <Key size={14} aria-hidden />
                {ENV_LABELS[env] ?? env}
              </span>
              <input
                type="password"
                className="oma-input"
                placeholder="Paste key (stored locally in data/llm_settings.json)"
                value={apiKeys[env] ?? ""}
                onChange={(e) => setApiKeys((k) => ({ ...k, [env]: e.target.value }))}
              />
              <span className="oma-hint">Or set {env} in .env</span>
            </label>
          ))}

        {selectedProvider === "ollama" && (
          <label className="block space-y-1">
            <span className="oma-label">Ollama host</span>
            <input
              className="oma-input"
              value={ollamaHost}
              onChange={(e) => setOllamaHost(e.target.value)}
            />
          </label>
        )}

        {selectedProvider === "lmstudio" && (
          <label className="block space-y-1">
            <span className="oma-label">LM Studio base URL</span>
            <input
              className="oma-input"
              value={lmStudioUrl}
              onChange={(e) => setLmStudioUrl(e.target.value)}
            />
          </label>
        )}

        {selectedProvider === "chatgpt_oauth" && (
          <div
            className="space-y-3 rounded-lg border p-4"
            style={{ borderColor: "var(--oma-border)", backgroundColor: "var(--oma-surface-elevated)" }}
          >
            <p className="text-sm" style={{ color: "var(--oma-text)" }}>
              Sign in with your ChatGPT Plus or Pro subscription (Codex OAuth). Opens auth in a new tab;
              localhost callback on port 1455 or 1457.
            </p>
            {chatgptOAuth?.connected ? (
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="done">Connected</Badge>
                {chatgptOAuth.account?.account_id && (
                  <span className="text-xs text-slate-500 font-mono">
                    {chatgptOAuth.account.account_id}
                  </span>
                )}
                <Button type="button" variant="secondary" size="sm" disabled={busy} onClick={onDisconnectChatGPT}>
                  Disconnect
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                <Button type="button" variant="primary" disabled={busy} onClick={onConnectChatGPT}>
                  Connect ChatGPT
                </Button>
                {oauthSessionId && (
                  <div className="space-y-2">
                    <p className="oma-hint">
                      If redirect fails, paste the full callback URL from your browser:
                    </p>
                    <input
                      className="oma-input font-mono text-xs"
                      placeholder="http://127.0.0.1:1455/auth/callback?code=..."
                      value={oauthCallbackUrl}
                      onChange={(e) => setOauthCallbackUrl(e.target.value)}
                    />
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      disabled={busy || !oauthCallbackUrl.trim()}
                      onClick={onPasteCallback}
                    >
                      Submit callback URL
                    </Button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        <div className="flex gap-2">
          <Button type="submit" variant="primary" disabled={busy}>
            Save default
          </Button>
          <Button
            type="button"
            variant="secondary"
            disabled={
              busy ||
              current?.status === "coming_soon" ||
              (selectedProvider === "chatgpt_oauth" && !chatgptOAuth?.connected)
            }
            onClick={onTest}
          >
            Test connection
          </Button>
        </div>
        {message && <Alert variant="success">{message}</Alert>}
        {error && <Alert variant="error">{error}</Alert>}
      </form>
      </Card>

      {settings && (
        <p className="oma-hint">
          Active default: {settings.default_provider_id} / {settings.default_model_id}
        </p>
      )}

      {automation && (
        <section className="oma-section space-y-4">
          <div>
            <h3 className="oma-label flex items-center gap-2">
              <FolderOpen size={16} aria-hidden />
              Automation
            </h3>
            <p className="oma-hint mt-0.5">
              Inbox folder, webhooks, markdown export, and desktop notifications (Linux notify-send).
            </p>
          </div>
          <form onSubmit={onSaveAutomation} className="space-y-3">
            <label className="flex cursor-pointer items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={automation.inbox_watch_enabled}
                onChange={(e) =>
                  setAutomation({ ...automation, inbox_watch_enabled: e.target.checked })
                }
                disabled={automationBusy}
              />
              Watch <code className="text-xs">{automation.inbox_dir}</code> for new files
            </label>
            <label className="block space-y-1">
              <span className="oma-label">Webhook URL (on done/failed)</span>
              <input
                className="oma-input"
                value={automation.webhook_url}
                onChange={(e) =>
                  setAutomation({ ...automation, webhook_url: e.target.value })
                }
                placeholder="https://..."
              />
            </label>
            <label className="block space-y-1">
              <span className="oma-label">Markdown export directory (Obsidian vault, etc.)</span>
              <input
                className="oma-input"
                value={automation.markdown_export_dir}
                onChange={(e) =>
                  setAutomation({ ...automation, markdown_export_dir: e.target.value })
                }
                placeholder="/home/you/Documents/OMA"
              />
            </label>
            <label className="flex cursor-pointer items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={automation.desktop_notify}
                onChange={(e) =>
                  setAutomation({ ...automation, desktop_notify: e.target.checked })
                }
                disabled={automationBusy}
              />
              Desktop notifications (notify-send)
            </label>
            <p className="oma-hint text-xs">
              Data: {automation.data_dir} · Uploads: {automation.uploads_dir}
            </p>
            <div className="flex flex-wrap gap-2">
              <Button type="submit" variant="secondary" disabled={automationBusy}>
                Save automation
              </Button>
              <Button type="button" variant="ghost" disabled={automationBusy} onClick={onScanInbox}>
                Scan inbox now
              </Button>
            </div>
          </form>
        </section>
      )}
    </div>
  );
}
