export type Priority = "low" | "normal" | "high";
export type AgentType = "workflow" | "doc_to_sheets";

export interface AgentInfo {
  id: AgentType;
  name: string;
  description: string;
}

export interface RequestSummary {
  id: string;
  user_id: string;
  session_id: string;
  agent_type: AgentType;
  llm_provider_id?: string;
  llm_model_id?: string;
  llm_display_name?: string;
  title: string;
  description: string;
  priority: Priority;
  file_name: string;
  current_step: string;
  status: string;
  status_message: string;
  latest_output: string;
  created_at: string;
  updated_at: string;
}

export interface RequestDetail extends RequestSummary {
  proposed_actions: string;
  approval_summary: string;
  plan_summary: string;
  result_summary: string;
  error_message: string;
  sheet_url: string;
  sheet_result_url: string;
  columns: string[];
  preview_rows: Record<string, string>[];
  column_mapping: Record<string, string>;
  confidence_notes: string;
  rows_written: string;
  events: Array<{ kind: string; text: string; step: string }>;
}

export interface CreateRequestBody {
  title: string;
  description: string;
  priority: Priority;
  agent_type: AgentType;
  sheet_url?: string;
  provider_id?: string;
  model_id?: string;
}
