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

export function AskTab({ apiUrl }: { apiUrl: string }) {
  const [question, setQuestion] = useState("");
  const [model, setModel] = useState("gpt-4o");
  const [forceBad, setForceBad] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleAsk() {
    setLoading(true);
    setError(null);
    setResult(null);
    const { status, data } = await callApi("POST", `${apiUrl}/ask`, {
      question,
      model,
      force_bad: forceBad,
    });
    setLoading(false);
    if (status === 200) {
      setResult(data);
    } else {
      setError((data as Record<string, string>).detail ?? JSON.stringify(data));
    }
  }

  const answer = result?.answer as Record<string, unknown> | undefined;
  const sources = (result?.sources as unknown[]) ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Ask a question</h2>
        <p className="text-sm text-muted-foreground mt-1">Answers are grounded in PubMed abstracts and official guidelines.</p>
      </div>

      <div className="space-y-3">
        <div className="space-y-1">
          <Label htmlFor="ask-question">Question</Label>
          <Input
            id="ask-question"
            placeholder="How much protein do I need to build muscle?"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && question.trim() && handleAsk()}
          />
        </div>

        <div className="flex items-end gap-4">
          <div className="space-y-1">
            <Label>Model</Label>
            <Select value={model} onValueChange={(v) => v && setModel(v)}>
              <SelectTrigger className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {MODELS.map((m) => <SelectItem key={m} value={m}>{m}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          <label className="flex items-center gap-2 text-sm text-muted-foreground mb-1 cursor-pointer">
            <input
              type="checkbox"
              checked={forceBad}
              onChange={(e) => setForceBad(e.target.checked)}
              className="rounded"
            />
            force_bad (guardrail demo)
          </label>

          <Button onClick={handleAsk} disabled={!question.trim() || loading} className="mb-1">
            {loading ? "Thinking…" : "Ask"}
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {result && answer && (
        <div className="space-y-4">
          <Alert className={sources.length ? "border-green-500 bg-green-50 dark:bg-green-950" : "border-yellow-500 bg-yellow-50 dark:bg-yellow-950"}>
            <AlertDescription className="text-sm">{answer.answer as string}</AlertDescription>
          </Alert>

          <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
            <MetricCard label="Confidence" value={`${((answer.confidence as number) * 100).toFixed(0)}%`} />
            <MetricCard label="Sources needed" value={answer.sources_needed ? "Yes" : "No"} />
            <MetricCard label="Tokens" value={result.tokens_used as number} />
            <MetricCard label="Latency" value={`${result.latency_ms as number} ms`} />
            <MetricCard label="Cost" value={`$${(result.cost_usd as number).toFixed(6)}`} />
          </div>

          <SourceList sources={sources as Parameters<typeof SourceList>[0]["sources"]} />
        </div>
      )}
    </div>
  );
}
