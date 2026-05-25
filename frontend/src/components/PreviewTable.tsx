interface PreviewTableProps {
  columns: string[];
  rows: Record<string, string>[];
}

export function PreviewTable({ columns, rows }: PreviewTableProps) {
  if (!columns.length || !rows.length) {
    return <p className="text-sm text-slate-500">No preview rows yet.</p>;
  }
  const displayRows = rows.slice(0, 50);
  return (
    <div className="overflow-x-auto rounded border border-slate-700">
      <table className="min-w-full text-left text-sm">
        <thead className="bg-slate-800/80">
          <tr>
            {columns.map((col) => (
              <th key={col} className="px-3 py-2 font-medium text-slate-300">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {displayRows.map((row, i) => (
            <tr key={i} className="border-t border-slate-800">
              {columns.map((col) => (
                <td key={col} className="px-3 py-2 text-slate-400">
                  {row[col] ?? ""}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > 50 && (
        <p className="px-3 py-2 text-xs text-slate-500">Showing 50 of {rows.length} rows</p>
      )}
    </div>
  );
}
