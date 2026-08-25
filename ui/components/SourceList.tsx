"use client";
import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

interface Source {
  id?: string;
  chunk_id?: string;
  document_id: string;
  score?: number | null;
  text?: string;
  source_type?: string;
}

interface SourceListProps {
  sources: Source[];
  title?: string;
}

function SourceItem({ source }: { source: Source }) {
  const [open, setOpen] = useState(false);
  const label = source.document_id || source.id || "source";
  const score = source.score != null ? ` — score: ${source.score}` : "";

  return (
    <div className="rounded-md border text-sm">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left font-mono text-xs hover:bg-muted/50"
      >
        {open ? <ChevronDown className="h-3 w-3 shrink-0" /> : <ChevronRight className="h-3 w-3 shrink-0" />}
        <span className="truncate">{label}{score}</span>
      </button>
      {open && source.text && (
        <div className="border-t px-3 py-2 text-xs text-muted-foreground whitespace-pre-wrap">
          {source.text}
        </div>
      )}
    </div>
  );
}

export function SourceList({ sources, title = "Sources retrieved" }: SourceListProps) {
  if (!sources.length) return null;
  return (
    <div className="space-y-2">
      <p className="text-sm font-medium">{title}</p>
      {sources.map((s, i) => (
        <SourceItem key={i} source={s} />
      ))}
    </div>
  );
}
