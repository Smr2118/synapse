"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { MetricCard } from "@/components/MetricCard";
import { SourceList } from "@/components/SourceList";
import { callApi } from "@/lib/api";

const MODELS = ["gpt-4o", "gpt-4o-mini", "o3-mini"];

const TOOL_ICON: Record<string, string> = {
  search_pubmed: "🔬",
  search_nih: "🏛️",
  search_exercises: "🏋️",
};

interface ToolCall {
  tool: string;
  args: Record<string, string>;
}

export function AgenticAskTab({ apiUrl }: { apiUrl: string }) {
  const [question, setQuestion] = useState("");
  const [model, setModel] = useState("gpt-4o");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleAsk() {
    setLoading(true);
    setError(null);
    setResult(null);
    const { status, data } = await callApi("POST", `${apiUrl}/agentic/ask`, { question, model });
    setLoading(false);
    if (status === 200) setResult(data);
    else setError((data as Record<string, string>).detail ?? JSON.stringify(data));
  }

  const answer = result?.answer as Record<string, unknown> | undefined;
  const sources = (result?.sources as unknown[]) ?? [];
  const toolCalls = (result?.tool_calls as ToolCall[]) ?? [];
  const resultCounts: Record<string, number> = {
    search_pubmed: (result?.pubmed_results as number) ?? 0,
    search_nih: (result?.nih_results as number) ?? 0,
    search_exercises: (result?.exercise_results as number) ?? 0,
  };

  const pinecone = sources.filter((s) => (s as Record<string, string>).source_type === "pinecone");
  const pubmed = sources.filter((s) => (s as Record<string, string>).source_type === "pubmed");
  const nih = sources.filter((s) => (s as Record<string, string>).source_type === "nih");
  const exercise = sources.filter((s) => (s as Record<string, string>).source_type === "exercise");

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Agentic ask</h2>
        <p className="text-sm text-muted-foreground">
          The LLM dynamically selects tools — PubMed research, NIH guidelines, exercise DB — based on your question.
        </p>
      </div>

      <div className="space-y-3">
        <div className="space-y-1">
          <Label>Question</Label>
          <Input
            placeholder="What does recent research say about NMN supplementation?"
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
            {loading ? "Reasoning…" : "Ask (Agentic)"}
          </Button>
        </div>
      </div>

      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

      {result && answer && (
        <div className="space-y-4">
          {/* Think / Act / Observe trace */}
          <div className="rounded-lg border border-border bg-card p-4 space-y-2 text-sm font-mono">
            <p className="font-semibold text-[10px] uppercase tracking-widest text-accent mb-3">Agent decision loop</p>
            {toolCalls.length > 0 ? (
              <p className="text-muted-foreground">🧠 <span className="font-semibold text-foreground">THINK</span> — LLM decided to call: <span className="text-primary">{toolCalls.map((tc) => tc.tool).join(", ")}</span></p>
            ) : (
              <p className="text-muted-foreground">🧠 <span className="font-semibold text-foreground">THINK</span> — LLM judged local context sufficient, no tools needed</p>
            )}
            {toolCalls.map((tc, i) => (
              <div key={i} className="space-y-1 pl-4 border-l-2 border-accent/40">
                <p className="text-muted-foreground">{TOOL_ICON[tc.tool] ?? "🔧"} <span className="font-semibold text-accent">ACT</span> — <code className="text-primary">{tc.tool}</code> → <code className="text-xs">{tc.args?.query ?? JSON.stringify(tc.args)}</code></p>
                <p className="text-muted-foreground">👁️ <span className="font-semibold text-foreground">OBSERVE</span> — returned <strong className="text-primary">{resultCounts[tc.tool] ?? "?"}</strong> result(s)</p>
              </div>
            ))}
            <p className="text-muted-foreground">✅ <span className="font-semibold text-foreground">ANSWER</span> — confidence <span className="text-primary">{((answer.confidence as number) * 100).toFixed(0)}%</span>, from {sources.length} source(s)</p>
          </div>

          <Alert className={sources.length ? "border-green-500 bg-green-50 dark:bg-green-950" : "border-yellow-500 bg-yellow-50 dark:bg-yellow-950"}>
            <AlertDescription>{answer.answer as string}</AlertDescription>
          </Alert>

          <div className="grid grid-cols-2 gap-2 sm:grid-cols-7">
            <MetricCard label="Confidence" value={`${((answer.confidence as number) * 100).toFixed(0)}%`} />
            <MetricCard label="Pinecone" value={result.pinecone_chunks as number} />
            <MetricCard label="PubMed" value={result.pubmed_results as number} />
            <MetricCard label="NIH" value={result.nih_results as number} />
            <MetricCard label="Exercise" value={result.exercise_results as number} />
            <MetricCard label="Latency" value={`${result.latency_ms as number} ms`} />
            <MetricCard label="Cost" value={`$${(result.cost_usd as number).toFixed(6)}`} />
          </div>

          {pinecone.length > 0 && <SourceList title="📦 Pinecone sources" sources={pinecone as Parameters<typeof SourceList>[0]["sources"]} />}
          {pubmed.length > 0 && <SourceList title="🔬 PubMed results" sources={pubmed as Parameters<typeof SourceList>[0]["sources"]} />}
          {nih.length > 0 && <SourceList title="🏛️ NIH guidelines" sources={nih as Parameters<typeof SourceList>[0]["sources"]} />}
          {exercise.length > 0 && <SourceList title="🏋️ Exercises" sources={exercise as Parameters<typeof SourceList>[0]["sources"]} />}
        </div>
      )}
    </div>
  );
}
