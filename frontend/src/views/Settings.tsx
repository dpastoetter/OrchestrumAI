import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import {
  api,
  type ChatGPTOAuthStatus,
  type ProviderCatalogItem,
  type ProviderSettings,
} from "../api";

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

  const load = useCallback(async () => {
    const data = await api.getProviders();
    setProviders(data.providers);
    setSettings(data.settings);
    setSelectedProvider(data.settings.default_provider_id);
    setSelectedModel(data.settings.default_model_id);
    setOllamaHost(data.settings.ollama_host);
    setLmStudioUrl(data.settings.lm_studio_base_url);
    const oauth = await api.getChatGPTOAuthStatus();
    setChatgptOAuth(oauth);
  }, []);

  useEffect(() => {
    load().catch((e) => setError(String(e)));
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
    const colors: Record<string, string> = {
      connected: "bg-emerald-900/60 text-emerald-200",
      available: "bg-slate-700 text-slate-300",
      needs_config: "bg-amber-900/60 text-amber-200",
      coming_soon: "bg-slate-800 text-slate-500",
    };
    return (
      <span className={`rounded px-2 py-0.5 text-xs ${colors[status] ?? colors.available}`}>
        {status.replace("_", " ")}
      </span>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-medium">AI providers</h2>
        <p className="text-sm text-slate-400 mt-1">
          Connect API keys, local Ollama/LM Studio, Gemini native, or ChatGPT Plus/Pro OAuth.
        </p>
      </div>

      <form onSubmit={onSave} className="space-y-4 rounded-lg border border-slate-800 bg-slate-900/50 p-6">
        <label className="block space-y-1">
          <span className="text-sm text-slate-400">Default provider</span>
          <select
            className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
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
            <span className="text-slate-500">{current.description}</span>
            {current.docs_url && (
              <a className="text-sky-400 hover:underline" href={current.docs_url} target="_blank" rel="noreferrer">
                Docs
              </a>
            )}
          </div>
        )}

        <label className="block space-y-1">
          <span className="text-sm text-slate-400">Model</span>
          <select
            className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
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
              <span className="text-sm text-slate-400">{ENV_LABELS[env] ?? env}</span>
              <input
                type="password"
                className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
                placeholder="Paste key (stored locally in data/llm_settings.json)"
                value={apiKeys[env] ?? ""}
                onChange={(e) => setApiKeys((k) => ({ ...k, [env]: e.target.value }))}
              />
              <span className="text-xs text-slate-600">Or set {env} in .env</span>
            </label>
          ))}

        {selectedProvider === "ollama" && (
          <label className="block space-y-1">
            <span className="text-sm text-slate-400">Ollama host</span>
            <input
              className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
              value={ollamaHost}
              onChange={(e) => setOllamaHost(e.target.value)}
            />
          </label>
        )}

        {selectedProvider === "lmstudio" && (
          <label className="block space-y-1">
            <span className="text-sm text-slate-400">LM Studio base URL</span>
            <input
              className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
              value={lmStudioUrl}
              onChange={(e) => setLmStudioUrl(e.target.value)}
            />
          </label>
        )}

        {selectedProvider === "chatgpt_oauth" && (
          <div className="space-y-3 rounded border border-slate-700 bg-slate-950/80 p-4">
            <p className="text-sm text-slate-300">
              Sign in with your ChatGPT Plus or Pro subscription (Codex OAuth). Opens auth in a new tab;
              localhost callback on port 1455 or 1457.
            </p>
            {chatgptOAuth?.connected ? (
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm text-emerald-400">Connected</span>
                {chatgptOAuth.account?.account_id && (
                  <span className="text-xs text-slate-500 font-mono">
                    {chatgptOAuth.account.account_id}
                  </span>
                )}
                <button
                  type="button"
                  disabled={busy}
                  onClick={onDisconnectChatGPT}
                  className="rounded border border-slate-600 px-3 py-1 text-sm hover:bg-slate-800"
                >
                  Disconnect
                </button>
              </div>
            ) : (
              <div className="space-y-2">
                <button
                  type="button"
                  disabled={busy}
                  onClick={onConnectChatGPT}
                  className="rounded bg-emerald-700 px-4 py-2 text-sm hover:bg-emerald-600 disabled:opacity-50"
                >
                  Connect ChatGPT
                </button>
                {oauthSessionId && (
                  <div className="space-y-2">
                    <p className="text-xs text-slate-500">
                      If redirect fails, paste the full callback URL from your browser:
                    </p>
                    <input
                      className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-xs font-mono"
                      placeholder="http://127.0.0.1:1455/auth/callback?code=..."
                      value={oauthCallbackUrl}
                      onChange={(e) => setOauthCallbackUrl(e.target.value)}
                    />
                    <button
                      type="button"
                      disabled={busy || !oauthCallbackUrl.trim()}
                      onClick={onPasteCallback}
                      className="rounded border border-slate-600 px-3 py-1 text-sm hover:bg-slate-800"
                    >
                      Submit callback URL
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        <div className="flex gap-2">
          <button
            type="submit"
            disabled={busy}
            className="rounded bg-sky-600 px-4 py-2 text-sm hover:bg-sky-500 disabled:opacity-50"
          >
            Save default
          </button>
          <button
            type="button"
            disabled={
              busy ||
              current?.status === "coming_soon" ||
              (selectedProvider === "chatgpt_oauth" && !chatgptOAuth?.connected)
            }
            onClick={onTest}
            className="rounded border border-slate-600 px-4 py-2 text-sm hover:bg-slate-800 disabled:opacity-50"
          >
            Test connection
          </button>
        </div>
        {message && <p className="text-sm text-emerald-400">{message}</p>}
        {error && <p className="text-sm text-red-400">{error}</p>}
      </form>

      {settings && (
        <p className="text-xs text-slate-600">
          Active default: {settings.default_provider_id} / {settings.default_model_id}
        </p>
      )}
    </div>
  );
}
