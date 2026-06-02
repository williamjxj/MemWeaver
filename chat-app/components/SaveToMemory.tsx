"use client";

import { useState } from "react";

interface SaveToMemoryProps {
  question: string;
  answer: string;
  onSave: (question: string, answer: string, note: string) => Promise<boolean>;
}

type SaveStatus = "idle" | "saving" | "saved" | "error";

export function SaveToMemory({ question, answer, onSave }: SaveToMemoryProps) {
  const [checked, setChecked] = useState(false);
  const [note, setNote] = useState("");
  const [status, setStatus] = useState<SaveStatus>("idle");

  async function handleSave() {
    setStatus("saving");
    const ok = await onSave(question, answer, note);
    setStatus(ok ? "saved" : "error");
  }

  if (status === "saved") {
    return (
      <div className="text-xs text-muted-foreground">Saved ✓</div>
    );
  }

  return (
    <div className="text-xs text-muted-foreground space-y-1">
      <label className="flex items-center gap-1.5 cursor-pointer">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => setChecked(e.target.checked)}
          className="h-3 w-3"
        />
        Save to memory
      </label>

      {checked && (
        <div className="space-y-1">
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Optional note / metadata…"
            aria-label="Note for saved memory"
            rows={2}
            className="w-full border rounded px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleSave}
              disabled={status === "saving"}
              className="px-2 py-1 bg-primary text-primary-foreground rounded text-xs hover:opacity-90 disabled:opacity-50"
            >
              {status === "saving" ? "Saving…" : "Save"}
            </button>
            {status === "error" && (
              <span className="text-destructive" role="alert">Couldn&apos;t save — try again</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
