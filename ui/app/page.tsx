"use client";
import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AgenticAskTab } from "@/components/tabs/AgenticAskTab";
import { JourneyTab } from "@/components/tabs/JourneyTab";
import { IngestTab } from "@/components/tabs/IngestTab";
import { DocumentsTab } from "@/components/tabs/DocumentsTab";
import { DebugTab } from "@/components/tabs/DebugTab";
import { SamplesTab } from "@/components/tabs/SamplesTab";
import { AboutTab } from "@/components/tabs/AboutTab";
import { DEFAULT_API_URL } from "@/lib/api";

export default function Home() {
  const [apiUrl, setApiUrl] = useState(DEFAULT_API_URL);
  const [activeTab, setActiveTab] = useState("agentic");
  const [prefilledQuestion, setPrefilledQuestion] = useState("");

  function handleTrySample(question: string) {
    setPrefilledQuestion(question);
    setActiveTab("agentic");
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="mx-auto max-w-6xl px-6 py-4 flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground text-lg font-bold select-none">
            S
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground leading-none">Synapse</h1>
            <p className="text-xs text-muted-foreground mt-0.5">Fitness &amp; nutrition research assistant</p>
          </div>
        </div>
      </header>

      {/* Hero heading */}
      <div className="border-b border-border bg-card/50">
        <div className="mx-auto max-w-6xl px-6 py-8">
          <p className="text-xs font-semibold uppercase tracking-widest text-accent mb-2">Agentic RAG Pipeline</p>
          <h2 className="text-4xl font-bold text-foreground leading-tight max-w-2xl">
            Research-grounded answers to your fitness &amp; nutrition questions
          </h2>
        </div>
      </div>

      {/* Tabs */}
      <main className="flex-1 mx-auto w-full max-w-6xl px-6 py-8">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="mb-8 h-auto gap-1 bg-card border border-border p-1 flex-wrap">
            <TabsTrigger value="agentic"  className="text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">🧠 Agentic Ask</TabsTrigger>
            <TabsTrigger value="samples"  className="text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">✨ Samples</TabsTrigger>
            <TabsTrigger value="journey"  className="text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">🛤️ Pipeline Journey</TabsTrigger>
            <TabsTrigger value="ingest"   className="text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">📥 Ingest</TabsTrigger>
            <TabsTrigger value="documents" className="text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">📚 Documents</TabsTrigger>
            <TabsTrigger value="debug"    className="text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">🔍 Debug</TabsTrigger>
            <TabsTrigger value="about"    className="text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">ℹ️ About</TabsTrigger>
          </TabsList>

          <TabsContent value="agentic"><AgenticAskTab apiUrl={apiUrl} initialQuestion={prefilledQuestion} /></TabsContent>
          <TabsContent value="samples"><SamplesTab onTry={handleTrySample} /></TabsContent>
          <TabsContent value="journey"><JourneyTab apiUrl={apiUrl} /></TabsContent>
          <TabsContent value="ingest"><IngestTab apiUrl={apiUrl} /></TabsContent>
          <TabsContent value="documents"><DocumentsTab apiUrl={apiUrl} /></TabsContent>
          <TabsContent value="debug"><DebugTab apiUrl={apiUrl} /></TabsContent>
          <TabsContent value="about"><AboutTab apiUrl={apiUrl} onChangeApiUrl={setApiUrl} /></TabsContent>
        </Tabs>
      </main>

      {/* Footer */}
      <footer className="border-t border-border bg-card">
        <div className="mx-auto max-w-6xl px-6 py-4 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between text-[10px] text-muted-foreground">
          <p>Built by Smitha Rajasenan · Capstone Project 2026</p>
          <div className="flex items-center gap-4">
            <a href={`${apiUrl}/docs`} target="_blank" rel="noreferrer" className="hover:text-primary transition-colors">API Docs</a>
            <a href="https://github.com/Smr2118/synapse" target="_blank" rel="noreferrer" className="hover:text-primary transition-colors">GitHub</a>
            <a href="https://synapse-5w9z.onrender.com" target="_blank" rel="noreferrer" className="hover:text-primary transition-colors">Backend</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
