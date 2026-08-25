"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { MetricCard } from "@/components/MetricCard";
import { SourceList } from "@/components/SourceList";
import { callApi } from "@/lib/api";

const MODELS = ["gpt-4o", "gpt-4o-mini", "o3-mini"];

const STRATEGY_LABELS: Record<string, string> = {
  "pinecone+pubmed": "Pinecone + PubMed",
  pinecone_only: "Pinecone only",
  pubmed_only: "PubMed only",
  refused: "Refused",
};

const STRATEGY_VARIANT: Record<string, "default" | "secondary" | "outline" | "destructive"> = {
  "pinecone+pubmed": "default",
  pinecone_only: "secondary",
  pubmed_only: "outline",
  refused: "destructive",
};

export function AgentAskTab({ apiUrl }: { apiUrl: string }) {
  const [question, setQuestion] = useState("");
  const [model, setModel] = useState("gpt-4o");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleAsk() {
    setLoading(true);
    setError(null);
    setResult(null);
    const { status, data } = await callApi("POST", `${apiUrl}/agent/ask`, { question, model });
    setLoading(false);
    if (status === 200) setResult(data);
    else setError((data as Record<string, string>).detail ?? JSON.stringify(data));
  }

  const answer = result?.answer as Record<string, unknown> | undefined;
  const sources = (result?.sources as unknown[]) ?? [];
  const strategy = result?.strategy as string | undefined;
  const pinecone = sources.filter((s: unknown) => (s as Record<string, string>).source_type === "pinecone");
  const pubmed = sources.filter((s: unknown) => (s as Record<string, string>).source_type === "pubmed");

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Agent ask</h2>
        <p className="text-sm text-muted-foreground">
          Orchestrator runs Pinecone retrieval + live PubMed search, then synthesises a grounded answer.
        </p>
      </div>

      <div className="space-y-3">
        <div className="space-y-1">
          <Label>Question</Label>
          <Input
            placeholder="Does creatine help with strength?"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && question.trim() && handleAsk()}
          />
        </div>
        <div className="flex items-end gap-4">
          <div className="space-y-1">
            <Label>Model</Label>
            <Select value={model} onValueChange={(v) => v && setModel(v)}>
              <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
              <SelectContent>{MODELS.map((m) => <SelectItem key={m} value={m}>{m}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <Button onClick={handleAsk} disabled={!question.trim() || loading} className="mb-1">
            {loading ? "Running…" : "Ask Agent"}
          </Button>
        </div>
      </div>

      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

      {result && answer && (
        <div className="space-y-4">
          {strategy && (
            <Badge variant={STRATEGY_VARIANT[strategy] ?? "outline"}>
              Strategy: {STRATEGY_LABELS[strategy] ?? strategy}
            </Badge>
          )}

          <Alert className={sources.length ? "border-green-500 bg-green-50 dark:bg-green-950" : "border-yellow-500 bg-yellow-50 dark:bg-yellow-950"}>
            <AlertDescription>{answer.answer as string}</AlertDescription>
          </Alert>

          <div className="grid grid-cols-2 gap-2 sm:grid-cols-6">
            <MetricCard label="Confidence" value={`${((answer.confidence as number) * 100).toFixed(0)}%`} />
            <MetricCard label="Pinecone chunks" value={result.pinecone_chunks as number} />
            <MetricCard label="PubMed results" value={result.pubmed_results as number} />
            <MetricCard label="Tokens" value={result.tokens_used as number} />
            <MetricCard label="Latency" value={`${result.latency_ms as number} ms`} />
            <MetricCard label="Cost" value={`$${(result.cost_usd as number).toFixed(6)}`} />
          </div>

          {pinecone.length > 0 && (
            <SourceList
              title="Pinecone sources"
              sources={pinecone as Parameters<typeof SourceList>[0]["sources"]}
            />
          )}
          {pubmed.length > 0 && (
            <SourceList
              title="PubMed live results"
              sources={pubmed as Parameters<typeof SourceList>[0]["sources"]}
            />
          )}
        </div>
      )}
    </div>
  );
}
