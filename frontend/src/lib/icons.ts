import type { LucideIcon } from "lucide-react";
import {
  Circle,
  ClipboardList,
  FileSpreadsheet,
  GitBranch,
  Globe,
  Layers,
  ListOrdered,
  Network,
  PenLine,
  PlusCircle,
  Settings,
  Shield,
  Workflow,
} from "lucide-react";

export const NavIcons = {
  requests: ClipboardList,
  workflows: GitBranch,
  submit: PlusCircle,
  settings: Settings,
  logo: Layers,
} as const;

export const AgentTypeIcons: Record<string, LucideIcon> = {
  workflow: Workflow,
  doc_to_sheets: FileSpreadsheet,
};

export const TopologyModeIcons: Record<string, LucideIcon> = {
  simple: Circle,
  sequential: ListOrdered,
  orchestrator: Network,
};

export const PaletteCategoryIcons: Record<string, LucideIcon> = {
  private_doc: Shield,
  writing: PenLine,
  web: Globe,
};
