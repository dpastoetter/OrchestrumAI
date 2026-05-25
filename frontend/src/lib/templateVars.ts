const BUILTIN = new Set(["date", "week", "datetime", "month", "year"]);

export function extractCustomVars(template: string): string[] {
  const found = new Set<string>();
  const re = /\{\{(\w+)\}\}/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(template)) !== null) {
    const name = m[1];
    if (!BUILTIN.has(name)) found.add(name);
  }
  return [...found];
}
