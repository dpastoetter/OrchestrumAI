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
  enabled_generic_agents?: string[];
  agent_topology_type?: string;
  agent_topology_labels?: string[];
  workflow_template_id?: string;
  workflow_schedule_id?: string;
  run_source?: string;
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

export type TopologyType = "simple" | "sequential" | "orchestrator";

export interface TopologyNode {
  id: string;
  kind: "catalog" | "custom";
  catalog_id?: string;
  name?: string;
  instruction?: string;
}

export interface TopologyEdge {
  from: string;
  to: string;
}

export interface AgentTopology {
  type: TopologyType;
  nodes: TopologyNode[];
  edges?: TopologyEdge[];
}

export interface CreateRequestBody {
  title: string;
  description: string;
  priority: Priority;
  agent_type: AgentType;
  sheet_url?: string;
  provider_id?: string;
  model_id?: string;
  enabled_generic_agents?: string[];
  agent_topology?: AgentTopology;
}

export type AgentCatalogCategory = "private_doc" | "writing" | "web";

export interface GenericWorkflowAgent {
  id: string;
  name: string;
  description: string;
  default_enabled: boolean;
  category?: AgentCatalogCategory;
}

export interface WorkflowSettings {
  enabled_generic_agents: string[];
  advanced_mode: boolean;
}

export interface WorkflowTemplate {
  id: string;
  user_id: string;
  name: string;
  description_template: string;
  agent_type: AgentType;
  agent_topology: AgentTopology | null;
  default_priority: Priority;
  provider_id?: string;
  model_id?: string;
  require_plan_approval: boolean;
  icon: string;
  category: string;
  bundled: boolean;
  created_at: string;
  updated_at: string;
}

export interface WorkflowTemplateBody {
  name: string;
  description_template: string;
  agent_type: AgentType;
  agent_topology?: AgentTopology;
  default_priority?: Priority;
  provider_id?: string;
  model_id?: string;
  require_plan_approval?: boolean;
  icon?: string;
  category?: string;
}

export interface WorkflowSchedule {
  id: string;
  user_id: string;
  template_id: string;
  template_name: string;
  cron_expression: string;
  timezone: string;
  enabled: boolean;
  description_vars: Record<string, string>;
  on_approval: string;
  last_run_at: string | null;
  next_run_at: string | null;
  last_request_id: string;
  created_at: string;
  updated_at: string;
}

export interface AutomationSettings {
  inbox_watch_enabled: boolean;
  webhook_url: string;
  markdown_export_dir: string;
  desktop_notify: boolean;
  inbox_dir: string;
  uploads_dir: string;
  data_dir: string;
}

export interface WorkflowScheduleBody {
  template_id: string;
  cron_expression: string;
  timezone?: string;
  enabled?: boolean;
  description_vars?: Record<string, string>;
  on_approval?: "pause" | "skip_plan";
}
