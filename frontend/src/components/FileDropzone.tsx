import { useCallback, useRef, useState } from "react";

const ACCEPT = ".pdf,.csv,.xlsx,.xls,.png,.jpg,.jpeg,.webp";
const ACCEPT_LABEL = "PDF, CSV, XLSX, PNG, JPG, WebP";

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function fileKind(name: string): string {
  const ext = name.split(".").pop()?.toLowerCase() ?? "";
  if (ext === "pdf") return "PDF";
  if (ext === "csv") return "CSV";
  if (ext === "xlsx" || ext === "xls") return "Spreadsheet";
  if (["png", "jpg", "jpeg", "webp"].includes(ext)) return "Image";
  return ext.toUpperCase() || "File";
}

interface FileDropzoneProps {
  file: File | null;
  onFileChange: (file: File | null) => void;
  disabled?: boolean;
}

export function FileDropzone({ file, onFileChange, disabled }: FileDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const pick = useCallback(
    (f: File | null) => {
      if (!f || disabled) return;
      onFileChange(f);
    },
    [disabled, onFileChange],
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const dropped = e.dataTransfer.files[0];
      if (dropped) pick(dropped);
    },
    [pick],
  );

  return (
    <div className="space-y-2">
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        className="sr-only"
        disabled={disabled}
        onChange={(e) => pick(e.target.files?.[0] ?? null)}
      />

      {file ? (
        <div className="flex items-start gap-3 rounded-xl border border-emerald-800/50 bg-emerald-950/30 p-4">
          <div
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-emerald-900/50 text-xs font-semibold text-emerald-300"
            aria-hidden
          >
            {fileKind(file.name)}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate font-medium text-slate-100">{file.name}</p>
            <p className="text-xs text-slate-500">{formatBytes(file.size)}</p>
          </div>
          <button
            type="button"
            disabled={disabled}
            onClick={() => onFileChange(null)}
            className="rounded-lg px-2 py-1 text-xs text-slate-400 hover:bg-slate-800 hover:text-slate-200 disabled:opacity-50"
          >
            Remove
          </button>
        </div>
      ) : (
        <button
          type="button"
          disabled={disabled}
          onClick={() => inputRef.current?.click()}
          onDragEnter={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={(e) => {
            e.preventDefault();
            setDragOver(false);
          }}
          onDrop={onDrop}
          className={[
            "group flex w-full flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-6 py-10 text-center transition",
            dragOver
              ? "border-sky-500 bg-sky-950/40"
              : "border-slate-700 bg-slate-900/40 hover:border-slate-500 hover:bg-slate-900/70",
            disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer",
          ].join(" ")}
        >
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-800 text-slate-400 group-hover:bg-slate-700 group-hover:text-sky-300">
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
              />
            </svg>
          </span>
          <span className="text-sm font-medium text-slate-200">
            Drop your document here, or <span className="text-sky-400">browse</span>
          </span>
          <span className="text-xs text-slate-500">{ACCEPT_LABEL}</span>
        </button>
      )}
    </div>
  );
}
