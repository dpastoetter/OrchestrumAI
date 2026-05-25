import { FormEvent, useEffect, useState } from "react";

interface CustomAgentDialogProps {
  open: boolean;
  initialName?: string;
  initialInstruction?: string;
  title?: string;
  onCancel: () => void;
  onSave: (name: string, instruction: string) => void;
}

export function CustomAgentDialog({
  open,
  initialName = "",
  initialInstruction = "",
  title = "Custom agent",
  onCancel,
  onSave,
}: CustomAgentDialogProps) {
  const [name, setName] = useState(initialName);
  const [instruction, setInstruction] = useState(initialInstruction);

  useEffect(() => {
    if (open) {
      setName(initialName);
      setInstruction(initialInstruction);
    }
  }, [open, initialName, initialInstruction]);

  if (!open) return null;

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim() || !instruction.trim()) return;
    onSave(name.trim(), instruction.trim());
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-md space-y-4 rounded-lg border border-slate-700 bg-slate-900 p-6 shadow-xl"
      >
        <h3 className="text-lg font-medium text-slate-100">{title}</h3>
        <label className="block space-y-1">
          <span className="text-sm text-slate-400">Name</span>
          <input
            className="oma-input w-full"
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={80}
            required
          />
        </label>
        <label className="block space-y-1">
          <span className="text-sm text-slate-400">Instruction</span>
          <textarea
            className="oma-input min-h-[120px] w-full"
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            maxLength={4000}
            required
          />
        </label>
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded border border-slate-600 px-3 py-1.5 text-sm hover:bg-slate-800"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="rounded bg-sky-600 px-3 py-1.5 text-sm hover:bg-sky-500"
          >
            Save
          </button>
        </div>
      </form>
    </div>
  );
}
