import type { LucideIcon } from "lucide-react";
import {
  ClipboardList,
  FileSearch,
  FileSpreadsheet,
  LayoutTemplate,
  Lock,
  Receipt,
  ScrollText,
  Sun,
} from "lucide-react";

const EMOJI_MAP: Record<string, LucideIcon> = {
  "📋": ClipboardList,
  "📜": ScrollText,
  "☀️": Sun,
  "🔒": Lock,
  "🧾": Receipt,
  "📊": FileSpreadsheet,
  "⚡": LayoutTemplate,
};

const NAME_MAP: Record<string, LucideIcon> = {
  "clipboard-list": ClipboardList,
  "scroll-text": ScrollText,
  sun: Sun,
  lock: Lock,
  receipt: Receipt,
  "file-spreadsheet": FileSpreadsheet,
  "file-search": FileSearch,
  "layout-template": LayoutTemplate,
};

export function resolveTemplateIcon(icon?: string | null): LucideIcon {
  if (!icon?.trim()) return LayoutTemplate;
  const trimmed = icon.trim();
  if (EMOJI_MAP[trimmed]) return EMOJI_MAP[trimmed];
  const key = trimmed.toLowerCase().replace(/\s+/g, "-");
  if (NAME_MAP[key]) return NAME_MAP[key];
  return LayoutTemplate;
}
