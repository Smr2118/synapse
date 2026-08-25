"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { MetricCard } from "@/components/MetricCard";
import { callApi } from "@/lib/api";

export function IngestTab({ apiUrl }: { apiUrl: string }) {
  const [docId, setDocId] = useState("");
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleIngest() {
    setLoading(true);
    setError(null);
    setResult(null);
    const { status, data } = await callApi("POST", `${apiUrl}/ingest`, {
      document_id: docId,
      text,
    });
    setLoading(false);
    if (status === 200) setResult(data);
    else setError((data as Record<string, string>).detail ?? JSON.stringify(data));
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Ingest a document</h2>
        <p className="text-sm text-muted-foreground">
          Text is chunked, embedded via text-embedding-3-small, and stored in Pinecone.
        </p>
      </div>

      <div className="space-y-3 max-w-2xl">
        <div className="space-y-1">
          <Label htmlFor="doc-id">Document ID</Label>
          <Input
            id="doc-id"
            placeholder="e.g. nih-protein-fact-sheet"
            value={docId}
            onChange={(e) => setDocId(e.target.value)}
          />
        </div>

        <div className="space-y-1">
          <Label htmlFor="doc-text">Text</Label>
          <Textarea
            id="doc-text"
            placeholder="Paste plain text here…"
            rows={8}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
        </div>

        <Button
          onClick={handleIngest}
          disabled={!docId.trim() || !text.trim() || loading}
        >
          {loading ? "Ingesting…" : "Ingest"}
        </Button>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {result && (
        <div className="space-y-4">
          <Alert className="border-green-500 bg-green-50 dark:bg-green-950">
            <AlertDescription>
              Ingested <strong>{result.document_id as string}</strong> successfully.
            </AlertDescription>
          </Alert>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            <MetricCard label="Document ID" value={result.document_id as string} />
            <MetricCard label="Chunks" value={result.chunks as number} />
            <MetricCard label="Tokens used" value={result.tokens_used as number} />
          </div>
        </div>
      )}
    </div>
  );
}
