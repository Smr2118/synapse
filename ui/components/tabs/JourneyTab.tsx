"use client";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AskTab } from "@/components/tabs/AskTab";
import { AgentAskTab } from "@/components/tabs/AgentAskTab";

const STAGES = [
  {
    num: "01",
    title: "Basic RAG Ask",
    desc: "The starting point. Embed the question, retrieve the top-k chunks from Pinecone, inject them as context, and call the model with structured output. Retry once on schema failure.",
  },
  {
    num: "02",
    title: "Orchestrated Agent Ask",
    desc: "Added a strategy layer. The orchestrator scores local Pinecone evidence and decides whether to enrich with a live PubMed search — or refuse if neither source has enough signal.",
  },
  {
    num: "03",
    title: "Agentic Ask",
    desc: "The LLM itself decides which tools to call based on the question. It can invoke PubMed, NIH guidelines, or the exercise DB in any combination — or none if context is already sufficient.",
    current: true,
  },
];

export function JourneyTab({ apiUrl }: { apiUrl: string }) {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold">Pipeline journey</h2>
        <p className="text-sm text-muted-foreground mt-1">
          How the pipeline evolved from a basic RAG query to a fully agentic system.
        </p>
      </div>

      {/* Stage timeline */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {STAGES.map((s) => (
          <div
            key={s.num}
            className={`rounded-xl border p-5 space-y-2 ${
              s.current
                ? "border-primary bg-primary/10"
                : "border-border bg-card"
            }`}
          >
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono font-bold text-accent">Stage {s.num}</span>
              {s.current && (
                <span className="rounded-full bg-primary px-2 py-0.5 text-[9px] font-semibold text-primary-foreground">
                  Current
                </span>
              )}
            </div>
            <h3 className="text-sm font-semibold text-foreground">{s.title}</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">{s.desc}</p>
          </div>
        ))}
      </div>

      {/* Earlier stage interfaces */}
      <div className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-widest text-accent">Try the earlier stages</p>
        <Tabs defaultValue="ask">
          <TabsList className="h-auto gap-1 bg-card border border-border p-1">
            <TabsTrigger value="ask" className="text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
              Stage 01 — Basic RAG
            </TabsTrigger>
            <TabsTrigger value="agent" className="text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
              Stage 02 — Orchestrated Agent
            </TabsTrigger>
          </TabsList>
          <div className="mt-6">
            <TabsContent value="ask"><AskTab apiUrl={apiUrl} /></TabsContent>
            <TabsContent value="agent"><AgentAskTab apiUrl={apiUrl} /></TabsContent>
          </div>
        </Tabs>
      </div>
    </div>
  );
}
