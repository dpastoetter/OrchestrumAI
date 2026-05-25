import { FileText, Upload, X } from "lucide-react";
import { useCallback, useRef, useState } from "react";

const ACCEPT = ".pdf,.csv,.xlsx,.xls,.png,.jpg,.jpeg,.webp,.txt,.md";
const ACCEPT_LABEL = "PDF, CSV, XLSX, TXT, PNG, JPG, WebP";

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
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
        <div
          className="flex items-start gap-3 rounded-xl border p-4"
          style={{
            borderColor: "color-mix(in srgb, var(--oma-success) 40%, var(--oma-border))",
            backgroundColor: "color-mix(in srgb, var(--oma-success) 8%, var(--oma-surface))",
          }}
        >
          <div
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg"
            style={{
              backgroundColor: "var(--oma-surface-elevated)",
              color: "var(--oma-primary)",
            }}
          >
            <FileText size={22} aria-hidden />
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate font-medium" style={{ color: "var(--oma-text)" }}>
              {file.name}
            </p>
            <p className="oma-hint">{formatBytes(file.size)}</p>
          </div>
          <button
            type="button"
            disabled={disabled}
            onClick={() => onFileChange(null)}
            className="rounded-lg p-1 transition hover:opacity-80 disabled:opacity-50"
            style={{ color: "var(--oma-muted)" }}
            aria-label="Remove file"
          >
            <X size={18} />
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
            disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer",
          ].join(" ")}
          style={{
            borderColor: dragOver ? "var(--oma-primary)" : "var(--oma-border)",
            backgroundColor: dragOver
              ? "color-mix(in srgb, var(--oma-primary) 8%, var(--oma-surface))"
              : "var(--oma-surface-elevated)",
          }}
        >
          <span
            className="flex h-12 w-12 items-center justify-center rounded-full transition"
            style={{
              backgroundColor: "var(--oma-surface)",
              color: "var(--oma-muted)",
            }}
          >
            <Upload className="h-6 w-6 group-hover:opacity-90" style={{ color: "var(--oma-primary)" }} />
          </span>
          <span className="text-sm font-medium" style={{ color: "var(--oma-text)" }}>
            Drop your document here, or{" "}
            <span style={{ color: "var(--oma-primary)" }}>browse</span>
          </span>
          <span className="oma-hint">{ACCEPT_LABEL}</span>
        </button>
      )}
    </div>
  );
}
