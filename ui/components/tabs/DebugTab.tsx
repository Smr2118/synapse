"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { callApi } from "@/lib/api";
import { ChevronDown, ChevronRight } from "lucide-react";

interface Chunk {
  document_id: string;
  score: number;
  text: string;
}

function ChunkItem({ chunk, index }: { chunk: Chunk; index: number }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-md border text-sm">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-muted/50"
      >
        {open ? <ChevronDown className="h-3 w-3 shrink-0" /> : <ChevronRight className="h-3 w-3 shrink-0" />}
        <span className="font-medium">#{index}</span>
        <span className="font-mono text-xs text-muted-foreground truncate flex-1">{chunk.document_id}</span>
        <span className="text-xs text-muted-foreground shrink-0">score: {chunk.score}</span>
      </button>
      {open && (
        <div className="border-t px-3 py-2 text-xs text-muted-foreground whitespace-pre-wrap">
          {chunk.text}
        </div>
      )}
    </div>
  );
}

export function DebugTab({ apiUrl }: { apiUrl: string }) {
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const [loading, setLoading] = useState(false);
  const [chunks, setChunks] = useState<Chunk[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleRetrieve() {
    setLoading(true);
    setError(null);
    setChunks(null);
    const url = `${apiUrl}/debug/retrieve?q=${encodeURIComponent(query)}&top_k=${topK}`;
    const { status, data } = await callApi("GET", url);
    setLoading(false);
    if (status === 200) {
      setChunks(data as unknown as Chunk[]);
    } else {
      setError((data as Record<string, string>).detail ?? JSON.stringify(data));
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Debug retrieval</h2>
        <p className="text-sm text-muted-foreground">
          Embeds a query and returns top-k chunks from Pinecone — no LLM call.
        </p>
      </div>

      <div className="space-y-4 max-w-2xl">
        <div className="space-y-1">
          <Label>Query</Label>
          <Input
            placeholder="does creatine help with strength?"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && query.trim() && handleRetrieve()}
          />
        </div>

        <div className="space-y-2">
          <Label>Top K: {topK}</Label>
          <Slider
            min={1}
            max={10}
            step={1}
            value={[topK]}
            onValueChange={(vals) => setTopK(Array.isArray(vals) ? vals[0] : vals)}
            className="max-w-xs"
          />
        </div>

        <Button onClick={handleRetrieve} disabled={!query.trim() || loading}>
          {loading ? "Retrieving…" : "Retrieve"}
        </Button>
      </div>

      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

      {chunks !== null && (
        <div className="space-y-2">
          {chunks.length === 0 ? (
            <Alert>
              <AlertDescription>No chunks returned — query may be out of scope.</AlertDescription>
            </Alert>
          ) : (
            <>
              <p className="text-sm text-muted-foreground">{chunks.length} chunk(s) retrieved</p>
              {chunks.map((c, i) => <ChunkItem key={i} chunk={c} index={i + 1} />)}
            </>
          )}
        </div>
      )}
    </div>
  );
}
