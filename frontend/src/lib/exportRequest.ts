import type { RequestDetail } from "../types";

export function buildRequestMarkdown(detail: RequestDetail): string {
  const lines = [
    `# ${detail.title}`,
    "",
    `- **Status:** ${detail.status} (${detail.current_step})`,
    `- **Agent:** ${detail.agent_type}`,
    `- **Priority:** ${detail.priority}`,
    `- **Created:** ${new Date(detail.created_at).toLocaleString()}`,
  ];
  if (detail.llm_display_name) lines.push(`- **Model:** ${detail.llm_display_name}`);
  if (detail.file_name) lines.push(`- **File:** ${detail.file_name}`);
  lines.push("", "## Description", "", detail.description);
  if (detail.plan_summary) {
    lines.push("", "## Plan", "", detail.plan_summary);
  }
  if (detail.result_summary) {
    lines.push("", "## Result", "", detail.result_summary);
  }
  if (detail.latest_output && detail.latest_output !== detail.result_summary) {
    lines.push("", "## Latest output", "", detail.latest_output);
  }
  if (detail.error_message) {
    lines.push("", "## Error", "", detail.error_message);
  }
  return lines.join("\n");
}

export async function copyText(text: string): Promise<void> {
  await navigator.clipboard.writeText(text);
}

export function downloadMarkdown(filename: string, content: string): void {
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
