interface PreviewTableProps {
  columns: string[];
  rows: Record<string, string>[];
}

export function PreviewTable({ columns, rows }: PreviewTableProps) {
  if (!columns.length || !rows.length) {
    return <p className="oma-hint text-sm">No preview rows yet.</p>;
  }
  const displayRows = rows.slice(0, 50);
  return (
    <div
      className="overflow-x-auto rounded-lg border"
      style={{ borderColor: "var(--oma-border)" }}
    >
      <table className="min-w-full text-left text-sm">
        <thead style={{ backgroundColor: "var(--oma-surface-elevated)" }}>
          <tr>
            {columns.map((col) => (
              <th
                key={col}
                className="px-3 py-2 font-medium"
                style={{ color: "var(--oma-text)" }}
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody style={{ backgroundColor: "var(--oma-surface)" }}>
          {displayRows.map((row, i) => (
            <tr key={i} className="border-t" style={{ borderColor: "var(--oma-border)" }}>
              {columns.map((col) => (
                <td key={col} className="px-3 py-2" style={{ color: "var(--oma-muted)" }}>
                  {row[col] ?? ""}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > 50 && (
        <p className="oma-hint px-3 py-2">Showing 50 of {rows.length} rows</p>
      )}
    </div>
  );
}
