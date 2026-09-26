import type {
  AgentInfo,
  CreateRequestBody,
  GenericWorkflowAgent,
  RequestDetail,
  RequestSummary,
  AutomationSettings,
  WorkflowSchedule,
  WorkflowScheduleBody,
  WorkflowSettings,
  WorkflowTemplate,
  WorkflowTemplateBody,
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
const API_TOKEN = (import.meta.env.VITE_ORCHESTRUMAI_API_TOKEN as string | undefined)?.trim() || "";

function apiHeaders(extra?: HeadersInit): Headers {
  const headers = new Headers(extra);
  if (API_TOKEN) {
    headers.set("X-OrchestrumAI-Token", API_TOKEN);
  }
  return headers;
}

function apiFetch(input: string, init?: RequestInit): Promise<Response> {
  const headers = apiHeaders(init?.headers);
  return fetch(input, { ...init, headers });
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () =>
    apiFetch(`${API}/health`).then((r) =>
      json<{ status: string; service?: string; features?: string[] }>(r),
    ),

  listAgents: () => apiFetch(`${API}/agents`).then((r) => json<AgentInfo[]>(r)),

  listRequests: () => apiFetch(`${API}/requests`).then((r) => json<RequestSummary[]>(r)),

  getRequest: (id: string) =>
    apiFetch(`${API}/requests/${id}`).then((r) => json<RequestDetail>(r)),

  deleteRequest: (id: string) =>
    apiFetch(`${API}/requests/${id}`, { method: "DELETE" }).then((r) => {
      if (!r.ok) {
        return r.text().then((text) => {
          throw new Error(text || r.statusText);
        });
      }
    }),

  createRequest: (body: CreateRequestBody) =>
    apiFetch(`${API}/requests`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) => json<RequestSummary>(r)),

  createRequestWithFile: (form: FormData) =>
    apiFetch(`${API}/requests/upload`, {
      method: "POST",
      body: form,
    }).then((r) => json<RequestSummary>(r)),

  resumeRequest: (id: string, decision: "approved" | "rejected", comment = "") =>
    apiFetch(`${API}/requests/${id}/resume`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, comment }),
    }).then((r) => json<RequestSummary>(r)),

  eventsUrl: (id: string) => `${API}/requests/${id}/events`,

  getProviders: () =>
    apiFetch(`${API}/providers`).then((r) =>
      json<{ providers: ProviderCatalogItem[]; settings: ProviderSettings }>(r),
    ),

  updateProviderSettings: (body: {
    default_provider_id?: string;
    default_model_id?: string;
    api_keys?: Record<string, string>;
    ollama_host?: string;
    lm_studio_base_url?: string;
  }) =>
    apiFetch(`${API}/providers/settings`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) =>
      json<{ providers: ProviderCatalogItem[]; settings: ProviderSettings }>(r),
    ),

  testProvider: (providerId: string, modelId?: string) =>
    apiFetch(`${API}/providers/test`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider_id: providerId, model_id: modelId || null }),
    }).then((r) => json<{ ok: boolean; message: string }>(r)),

  getChatGPTOAuthStatus: () =>
    apiFetch(`${API}/providers/chatgpt-oauth/status`).then((r) => json<ChatGPTOAuthStatus>(r)),

  connectChatGPTOAuth: () =>
    apiFetch(`${API}/providers/chatgpt-oauth/connect`, { method: "POST" }).then((r) =>
      json<ChatGPTOAuthConnect>(r),
    ),

  pollChatGPTOAuthSession: (sessionId: string) =>
    apiFetch(`${API}/providers/chatgpt-oauth/session/${sessionId}`).then((r) =>
      json<{ status: string; error?: string; account?: ChatGPTOAuthStatus["account"] }>(r),
    ),

  submitChatGPTOAuthCallback: (sessionId: string, callbackUrl: string) =>
    apiFetch(`${API}/providers/chatgpt-oauth/callback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, callback_url: callbackUrl }),
    }).then((r) => json<{ status: string; error?: string }>(r)),

  disconnectChatGPTOAuth: () =>
    apiFetch(`${API}/providers/chatgpt-oauth/disconnect`, { method: "POST" }).then((r) =>
      json<{ ok: boolean }>(r),
    ),

  getWorkflowGenericAgents: () =>
    apiFetch(`${API}/workflow/generic-agents`).then((r) =>
      json<{ agents: GenericWorkflowAgent[] }>(r),
    ),

  getWorkflowSettings: () =>
    apiFetch(`${API}/workflow/settings`).then((r) =>
      json<{ settings: WorkflowSettings }>(r),
    ),

  updateWorkflowSettings: (body: {
    enabled_generic_agents?: string[];
    advanced_mode?: boolean;
  }) =>
    apiFetch(`${API}/workflow/settings`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) => json<{ settings: WorkflowSettings }>(r)),

  listWorkflowTemplates: () =>
    apiFetch(`${API}/workflow-templates`).then((r) =>
      json<{ templates: WorkflowTemplate[] }>(r),
    ),

  getWorkflowTemplate: (id: string) =>
    apiFetch(`${API}/workflow-templates/${id}`).then((r) => json<WorkflowTemplate>(r)),

  createWorkflowTemplate: (body: WorkflowTemplateBody) =>
    apiFetch(`${API}/workflow-templates`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) => json<WorkflowTemplate>(r)),

  updateWorkflowTemplate: (id: string, body: WorkflowTemplateBody) =>
    apiFetch(`${API}/workflow-templates/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) => json<WorkflowTemplate>(r)),

  deleteWorkflowTemplate: (id: string) =>
    apiFetch(`${API}/workflow-templates/${id}`, { method: "DELETE" }).then((r) => {
      if (!r.ok) throw new Error(r.statusText);
    }),

  runWorkflowTemplate: (id: string, body?: { title?: string; description_vars?: Record<string, string> }) =>
    apiFetch(`${API}/workflow-templates/${id}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body ?? {}),
    }).then((r) => json<RequestSummary>(r)),

  saveRequestAsTemplate: (
    requestId: string,
    body: { name: string; description_template?: string; icon?: string; category?: string },
  ) =>
    apiFetch(`${API}/requests/${requestId}/save-as-template`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) => json<WorkflowTemplate>(r)),

  exportWorkflowTemplateUrl: (id: string) => `${API}/workflow-templates/${id}/export`,

  importWorkflowTemplate: (body: WorkflowTemplateBody) =>
    apiFetch(`${API}/workflow-templates/import`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) => json<WorkflowTemplate>(r)),

  listWorkflowSchedules: () =>
    apiFetch(`${API}/workflow-schedules`).then((r) =>
      json<{ schedules: WorkflowSchedule[] }>(r),
    ),

  createWorkflowSchedule: (body: WorkflowScheduleBody) =>
    apiFetch(`${API}/workflow-schedules`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) => json<WorkflowSchedule>(r)),

  updateWorkflowSchedule: (id: string, body: WorkflowScheduleBody) =>
    apiFetch(`${API}/workflow-schedules/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) => json<WorkflowSchedule>(r)),

  deleteWorkflowSchedule: (id: string) =>
    apiFetch(`${API}/workflow-schedules/${id}`, { method: "DELETE" }).then((r) => {
      if (!r.ok) throw new Error(r.statusText);
    }),

  triggerWorkflowSchedule: (id: string) =>
    apiFetch(`${API}/workflow-schedules/${id}/trigger`, { method: "POST" }).then((r) =>
      json<RequestSummary>(r),
    ),

  getAutomationSettings: () =>
    apiFetch(`${API}/automation/settings`).then((r) =>
      json<{ settings: AutomationSettings }>(r),
    ),

  updateAutomationSettings: (body: Partial<AutomationSettings>) =>
    apiFetch(`${API}/automation/settings`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) => json<{ settings: AutomationSettings }>(r)),

  scanInbox: () =>
    apiFetch(`${API}/automation/scan-inbox`, { method: "POST" }).then((r) =>
      json<{ created: number }>(r),
    ),
};
