import type { RequestSummary } from "../types";

export type RequestFilter = "all" | "needs_approval" | "running" | "done_today" | "failed";

export function isDoneToday(createdAt: string): boolean {
  const d = new Date(createdAt);
  const now = new Date();
  return (
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate()
  );
}

export function matchesFilter(r: RequestSummary, filter: RequestFilter): boolean {
  if (filter === "all") return true;
  if (filter === "needs_approval") return r.status === "awaiting_approval";
  if (filter === "running") return r.status === "active";
  if (filter === "failed") return r.status === "failed";
  if (filter === "done_today") return r.status === "done" && isDoneToday(r.created_at);
  return true;
}

export function sortRequests(items: RequestSummary[]): RequestSummary[] {
  const priority = (r: RequestSummary) => {
    if (r.status === "awaiting_approval") return 0;
    if (r.status === "active") return 1;
    if (r.status === "failed") return 2;
    return 3;
  };
  return [...items].sort((a, b) => {
    const pa = priority(a);
    const pb = priority(b);
    if (pa !== pb) return pa - pb;
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });
}

export function countAwaitingApproval(items: RequestSummary[]): number {
  return items.filter((r) => r.status === "awaiting_approval").length;
}
