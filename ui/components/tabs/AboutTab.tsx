interface AboutTabProps {
  apiUrl: string;
  onChangeApiUrl: (url: string) => void;
}

const FEATURES = [
  {
    icon: "💬",
    title: "RAG Ask",
    desc: "Retrieval-augmented answers grounded in PubMed abstracts stored in Pinecone. Structured output via Pydantic with confidence scoring and automatic retry on schema failure.",
  },
  {
    icon: "🤖",
    title: "Agent Ask",
    desc: "Orchestrator evaluates local Pinecone evidence quality and decides whether to fall back to a live PubMed search, use both sources, or refuse if no evidence is found.",
  },
  {
    icon: "🧠",
    title: "Agentic Ask",
    desc: "The LLM dynamically selects tools at runtime — PubMed research, NIH guidelines, or exercise DB — based on the question. Displays a full Think / Act / Observe trace.",
  },
];

const STACK = [
  { label: "FastAPI", desc: "Typed REST API with Pydantic request/response validation" },
  { label: "OpenAI GPT-4o", desc: "Structured output, tool use, and agentic reasoning" },
  { label: "Pinecone", desc: "Vector database for semantic chunk retrieval" },
  { label: "PubMed MCP", desc: "Live search of peer-reviewed research abstracts" },
  { label: "NIH MCP", desc: "Official dietary and supplementation guidelines" },
  { label: "Next.js + Vercel", desc: "Frontend deployed at the edge" },
];

export function AboutTab({ apiUrl, onChangeApiUrl }: AboutTabProps) {
  return (
    <div className="space-y-10">
      {/* Overview */}
      <div>
        <h2 className="text-2xl font-bold">About Synapse</h2>
        <p className="mt-3 text-sm text-muted-foreground max-w-2xl leading-relaxed">
          Synapse is a capstone project demonstrating an agentic RAG pipeline for fitness and nutrition research. It retrieves peer-reviewed evidence and synthesises a confidence-scored, cited answer — without hallucinating facts not present in the retrieved context.
        </p>
      </div>

      {/* Pipeline modes */}
      <div className="space-y-3">
        <h3 className="text-xs font-semibold uppercase tracking-widest text-accent">Pipeline modes</h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {FEATURES.map((f) => (
            <div key={f.title} className="rounded-xl border border-border bg-card p-5">
              <span className="text-2xl">{f.icon}</span>
              <h4 className="mt-3 text-sm font-semibold text-foreground">{f.title}</h4>
              <p className="mt-1 text-xs text-muted-foreground leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Stack */}
      <div className="space-y-3">
        <h3 className="text-xs font-semibold uppercase tracking-widest text-accent">Tech stack</h3>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {STACK.map((s) => (
            <div key={s.label} className="flex gap-3 rounded-lg border border-border bg-card px-4 py-3">
              <span className="text-xs font-semibold text-primary shrink-0 w-28">{s.label}</span>
              <span className="text-xs text-muted-foreground">{s.desc}</span>
            </div>
          ))}
        </div>
      </div>

      {/* API config */}
      <div className="space-y-3">
        <h3 className="text-xs font-semibold uppercase tracking-widest text-accent">API configuration</h3>
        <div className="flex items-center gap-3 max-w-md">
          <label htmlFor="about-api-url" className="text-xs text-muted-foreground shrink-0">Base URL</label>
          <input
            id="about-api-url"
            value={apiUrl}
            onChange={(e) => onChangeApiUrl(e.target.value.replace(/\/$/, ""))}
            className="flex-1 h-8 rounded-md border border-border bg-background px-3 text-xs font-mono text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
          />
          <a
            href={`${apiUrl}/docs`}
            target="_blank"
            rel="noreferrer"
            className="text-xs text-primary hover:text-primary/80 underline underline-offset-2 shrink-0"
          >
            API docs ↗
          </a>
        </div>
      </div>
    </div>
  );
}
