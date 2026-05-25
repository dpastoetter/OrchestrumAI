const STORAGE_KEY = "orchestrumai_pinned_templates";

export function getPinnedTemplateIds(): Set<string> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return new Set();
    const arr = JSON.parse(raw) as unknown;
    if (!Array.isArray(arr)) return new Set();
    return new Set(arr.filter((x) => typeof x === "string"));
  } catch {
    return new Set();
  }
}

export function setPinnedTemplateIds(ids: Set<string>): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify([...ids]));
}

export function togglePinned(id: string): Set<string> {
  const next = getPinnedTemplateIds();
  if (next.has(id)) next.delete(id);
  else next.add(id);
  setPinnedTemplateIds(next);
  return next;
}
