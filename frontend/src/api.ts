import type {
  AgentInfo,
  CreateRequestBody,
  RequestDetail,
  RequestSummary,
} from "./types";

export interface ProviderCatalogItem {
  id: string;
  name: string;
  description: string;
  auth_type: string;
  status: string;
  env_vars: string[];
  docs_url: string;
  models: { id: string; label: string }[];
  is_default: boolean;
}

export interface ProviderSettings {
  default_provider_id: string;
  default_model_id: string;
  ollama_host: string;
  lm_studio_base_url: string;
  api_keys_configured: Record<string, boolean>;
}

export interface ChatGPTOAuthConnect {
  session_id: string;
  authorize_url: string;
  redirect_uri: string;
  callback_port: number;
}

export interface ChatGPTOAuthStatus {
  connected: boolean;
  account?: { connected: boolean; account_id?: string; expires_at?: number } | null;
  pending_sessions?: string[];
}

const API = "/api";

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => fetch(`${API}/health`).then((r) => json<{ status: string }>(r)),

  listAgents: () => fetch(`${API}/agents`).then((r) => json<AgentInfo[]>(r)),

  listRequests: () => fetch(`${API}/requests`).then((r) => json<RequestSummary[]>(r)),

  getRequest: (id: string) =>
    fetch(`${API}/requests/${id}`).then((r) => json<RequestDetail>(r)),

  createRequest: (body: CreateRequestBody) =>
    fetch(`${API}/requests`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) => json<RequestSummary>(r)),

  createRequestWithFile: (form: FormData) =>
    fetch(`${API}/requests/upload`, {
      method: "POST",
      body: form,
    }).then((r) => json<RequestSummary>(r)),

  resumeRequest: (id: string, decision: "approved" | "rejected", comment = "") =>
    fetch(`${API}/requests/${id}/resume`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, comment }),
    }).then((r) => json<RequestSummary>(r)),

  eventsUrl: (id: string) => `${API}/requests/${id}/events`,

  getProviders: () =>
    fetch(`${API}/providers`).then((r) =>
      json<{ providers: ProviderCatalogItem[]; settings: ProviderSettings }>(r),
    ),

  updateProviderSettings: (body: {
    default_provider_id?: string;
    default_model_id?: string;
    api_keys?: Record<string, string>;
    ollama_host?: string;
    lm_studio_base_url?: string;
  }) =>
    fetch(`${API}/providers/settings`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) =>
      json<{ providers: ProviderCatalogItem[]; settings: ProviderSettings }>(r),
    ),

  testProvider: (providerId: string, modelId?: string) =>
    fetch(`${API}/providers/test`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider_id: providerId, model_id: modelId || null }),
    }).then((r) => json<{ ok: boolean; message: string }>(r)),

  getChatGPTOAuthStatus: () =>
    fetch(`${API}/providers/chatgpt-oauth/status`).then((r) => json<ChatGPTOAuthStatus>(r)),

  connectChatGPTOAuth: () =>
    fetch(`${API}/providers/chatgpt-oauth/connect`, { method: "POST" }).then((r) =>
      json<ChatGPTOAuthConnect>(r),
    ),

  pollChatGPTOAuthSession: (sessionId: string) =>
    fetch(`${API}/providers/chatgpt-oauth/session/${sessionId}`).then((r) =>
      json<{ status: string; error?: string; account?: ChatGPTOAuthStatus["account"] }>(r),
    ),

  submitChatGPTOAuthCallback: (sessionId: string, callbackUrl: string) =>
    fetch(`${API}/providers/chatgpt-oauth/callback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, callback_url: callbackUrl }),
    }).then((r) => json<{ status: string; error?: string }>(r)),

  disconnectChatGPTOAuth: () =>
    fetch(`${API}/providers/chatgpt-oauth/disconnect`, { method: "POST" }).then((r) =>
      json<{ ok: boolean }>(r),
    ),
};
