"use client";
import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AskTab } from "@/components/tabs/AskTab";
import { AgentAskTab } from "@/components/tabs/AgentAskTab";
import { AgenticAskTab } from "@/components/tabs/AgenticAskTab";
import { IngestTab } from "@/components/tabs/IngestTab";
import { DocumentsTab } from "@/components/tabs/DocumentsTab";
import { DebugTab } from "@/components/tabs/DebugTab";
import { SamplesTab } from "@/components/tabs/SamplesTab";
import { DEFAULT_API_URL } from "@/lib/api";

const STACK = ["FastAPI", "OpenAI", "Pinecone", "Pydantic", "Next.js"];

const FEATURES = [
  {
    icon: "💬",
    title: "RAG Ask",
    desc: "Retrieval-augmented answers grounded in PubMed abstracts stored in Pinecone.",
  },
  {
    icon: "🤖",
    title: "Agent Ask",
    desc: "Orchestrator picks Pinecone, live PubMed search, or both based on evidence quality.",
  },
  {
    icon: "🧠",
    title: "Agentic Ask",
    desc: "LLM dynamically selects tools — PubMed, NIH guidelines, or exercise DB — at runtime.",
  },
];

export default function Home() {
  const [apiUrl, setApiUrl] = useState(DEFAULT_API_URL);
  const [activeTab, setActiveTab] = useState("ask");
  const [prefilledQuestion, setPrefilledQuestion] = useState("");

  function handleTrySample(question: string) {
    setPrefilledQuestion(question);
    setActiveTab("ask");
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="mx-auto max-w-6xl px-6 py-4 flex items-center justify-between gap-6">
          <div className="flex items-center gap-3 shrink-0">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground text-xl font-bold select-none">
              S
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-foreground leading-none">
                Synapse
              </h1>
              <p className="text-xs text-muted-foreground mt-1">
                Fitness &amp; nutrition research assistant
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 min-w-0 flex-1 max-w-xs">
            <Label htmlFor="api-url" className="text-xs shrink-0 text-muted-foreground">API</Label>
            <Input
              id="api-url"
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value.replace(/\/$/, ""))}
              className="text-xs h-7 font-mono bg-background border-border"
            />
          </div>
        </div>

        {/* Stack pills */}
        <div className="mx-auto max-w-6xl px-6 pb-3 flex items-center gap-2">
          {STACK.map((s) => (
            <span key={s} className="rounded-full border border-border px-2.5 py-0.5 text-[10px] font-medium text-muted-foreground">
              {s}
            </span>
          ))}
          <span className="text-muted-foreground/40 text-[10px] mx-1">·</span>
          <a href={`${apiUrl}/docs`} target="_blank" rel="noreferrer"
            className="text-[10px] text-primary hover:text-primary/80 transition-colors underline underline-offset-2">
            API docs ↗
          </a>
        </div>
      </header>

      {/* Hero */}
      <section className="border-b border-border bg-card/50">
        <div className="mx-auto max-w-6xl px-6 py-10">
          <p className="text-sm font-semibold uppercase tracking-widest text-accent mb-3">
            Agentic RAG Pipeline
          </p>
          <h2 className="text-4xl font-bold text-foreground leading-tight max-w-2xl">
            Research-grounded answers to your fitness &amp; nutrition questions
          </h2>
          <p className="mt-4 text-base text-muted-foreground max-w-xl">
            Synapse retrieves peer-reviewed evidence from PubMed, NIH guidelines, and an exercise database — then synthesises a cited, confidence-scored answer.
          </p>

          <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
            {FEATURES.map((f) => (
              <div key={f.title} className="rounded-xl border border-border bg-card p-5">
                <span className="text-2xl">{f.icon}</span>
                <h3 className="mt-3 text-sm font-semibold text-foreground">{f.title}</h3>
                <p className="mt-1 text-xs text-muted-foreground leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Tabs */}
      <main className="mx-auto max-w-6xl px-6 py-8">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="mb-8 h-auto gap-1 bg-card border border-border p-1">
            <TabsTrigger value="ask" className="text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">💬 Ask</TabsTrigger>
            <TabsTrigger value="agent" className="text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">🤖 Agent Ask</TabsTrigger>
            <TabsTrigger value="agentic" className="text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">🧠 Agentic Ask</TabsTrigger>
            <TabsTrigger value="samples" className="text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">✨ Samples</TabsTrigger>
            <TabsTrigger value="ingest" className="text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">📥 Ingest</TabsTrigger>
            <TabsTrigger value="documents" className="text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">📚 Documents</TabsTrigger>
            <TabsTrigger value="debug" className="text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">🔍 Debug</TabsTrigger>
          </TabsList>

          <TabsContent value="ask">
            <AskTab apiUrl={apiUrl} initialQuestion={prefilledQuestion} />
          </TabsContent>
          <TabsContent value="agent"><AgentAskTab apiUrl={apiUrl} /></TabsContent>
          <TabsContent value="agentic"><AgenticAskTab apiUrl={apiUrl} /></TabsContent>
          <TabsContent value="samples"><SamplesTab onTry={handleTrySample} /></TabsContent>
          <TabsContent value="ingest"><IngestTab apiUrl={apiUrl} /></TabsContent>
          <TabsContent value="documents"><DocumentsTab apiUrl={apiUrl} /></TabsContent>
          <TabsContent value="debug"><DebugTab apiUrl={apiUrl} /></TabsContent>
        </Tabs>
      </main>

      {/* Footer */}
      <footer className="border-t border-border bg-card mt-16">
        <div className="mx-auto max-w-6xl px-6 py-8">
          <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
            {/* Brand */}
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground text-sm font-bold select-none">
                  S
                </div>
                <span className="font-bold text-foreground">Synapse</span>
              </div>
              <p className="text-xs text-muted-foreground max-w-xs leading-relaxed">
                A research-grounded fitness &amp; nutrition assistant built on an agentic RAG pipeline with dynamic tool selection.
              </p>
            </div>

            {/* Links */}
            <div className="flex gap-12 text-xs">
              <div className="space-y-2">
                <p className="font-semibold text-accent uppercase tracking-widest text-[10px]">Project</p>
                <ul className="space-y-1.5 text-muted-foreground">
                  <li><a href={`${apiUrl}/docs`} target="_blank" rel="noreferrer" className="hover:text-primary transition-colors">API Docs</a></li>
                  <li><a href="https://github.com/Smr2118/synapse" target="_blank" rel="noreferrer" className="hover:text-primary transition-colors">GitHub</a></li>
                  <li><a href="https://synapse-5w9z.onrender.com" target="_blank" rel="noreferrer" className="hover:text-primary transition-colors">Backend (Render)</a></li>
                </ul>
              </div>

              <div className="space-y-2">
                <p className="font-semibold text-accent uppercase tracking-widest text-[10px]">Stack</p>
                <ul className="space-y-1.5 text-muted-foreground">
                  <li>FastAPI · Pydantic</li>
                  <li>OpenAI · Pinecone</li>
                  <li>Next.js · Vercel</li>
                </ul>
              </div>
            </div>
          </div>

          <div className="mt-8 border-t border-border pt-4 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between text-[10px] text-muted-foreground">
            <p>Built by Smitha Rajasenan · Capstone Project 2026</p>
            <p>Powered by OpenAI GPT-4o &amp; Pinecone</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
