# Synapse

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-412991?logo=openai&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063?logo=pydantic&logoColor=white)
![Pinecone](https://img.shields.io/badge/Pinecone-Vector%20DB-000000?logo=pinecone&logoColor=white)

Fitness advice online is mostly opinion. Synapse is a research-grounded assistant that answers questions about diet, exercise, and supplementation by retrieving evidence from PubMed abstracts, NIH guidelines, and an exercise database before it speaks. Every answer comes with sources and a confidence score. If the evidence is not there, it says so.

**Live UI:** https://synapse-ui.onrender.com/ · **API docs:** https://synapse-5w9z.onrender.com/docs

> Free tier on Render — first request after inactivity may take ~30s to wake up.

---

## What this project demonstrates

- **Structured output** — OpenAI `completions.parse` enforces a Pydantic schema at the model level. Malformed responses are caught and retried before reaching the client.
- **RAG pipeline** — question is embedded, top-5 chunks retrieved from Pinecone by cosine similarity, passed as grounded context to the LLM.
- **Source citations** — every response includes chunk ID, document ID, and similarity score for each retrieved chunk.
- **Observability** — every response includes token usage, latency, model name, and cost in USD.
- **MCP servers** — three FastMCP tools: PubMed live search, NIH MedlinePlus guidelines, Wger exercise database.
- **Agentic tool use** — raw-SDK agent loop using OpenAI function calling. The LLM decides which tools to call at runtime. Think / Act / Observe trace is visible in the UI and logs.
- **Persistent memory** — SQLite-backed user profiles and conversation history. The agent knows your goals and restrictions without being told again.
- **Evals** — code-based assertion suite across 20 questions measuring grounding, tool deduplication, sources consistency, and strategy label accuracy.

---

## Architecture

```
User question
      │
      ▼
User profile loaded from SQLite (goal, dietary, fitness level)
      │
      ▼
System prompt built: base instructions + profile context
      │
      ▼
Agentic loop — LLM decides which tools to call
  ├── search_pubmed  →  PubMed API  →  peer-reviewed abstracts
  ├── search_nih     →  NIH MedlinePlus  →  official guidelines
  └── search_exercises  →  Wger API  →  exercise database
      │
      ▼
LLM synthesises answer from tool results
      │
      ▼
Structured output parsed and validated by Pydantic
      │
      ▼
Turn saved to SQLite (session memory)
      │
      ▼
Response returned with answer, sources, confidence, latency, cost
```

**Three architecture decisions worth noting:**

**Pinecone over a local vector store.** Local options like FAISS are fast to set up but require the index to be rebuilt on every deploy. Pinecone persists independently of the application, which means the 457 ingested abstracts survive redeployments without any re-ingestion step.

**OpenAI structured output over prompt-engineered JSON.** Asking the LLM to return JSON and then parsing it breaks silently when the model drifts. `completions.parse` enforces the schema at the API level and returns a typed Pydantic object. Validation failures surface as exceptions, not as bad data reaching the client.

**SQLite over an external database for memory.** For a single-user demo, SQLite is the right choice. No connection string, no managed service, no cost. The path is environment-variable-driven so it can be pointed at a Render Persistent Disk without code changes if the deployment grows.

---

## Evals

The eval suite runs four code-based assertions against 20 traced questions.

| Check | What it catches |
|-------|----------------|
| `grounded` | In-scope question answered with no sources and no tool calls |
| `sources_needed_consistent` | Tools called, nothing returned, but `sources_needed=false` |
| `no_duplicate_tools` | Same tool called more than once in a single request |
| `strategy_label_accurate` | `strategy=refused` on a question the LLM actually answered |

**Before/after a targeted prompt fix:**

| | Pass rate |
|-|-----------|
| Before | 72/80 (90%) |
| After | 78/80 (98%) |

The fix strengthened the system prompt to require at least one tool call before answering any fitness or nutrition question. This eliminated ungrounded answers (grounded check: 17/20 to 19/20) and mislabelled strategy fields (strategy label check: 17/20 to 19/20).

Run the suite locally:

```bash
streamlit run app.py
# Open the Evals tab, set traces file to evals/traces.json
```

---

## Memory

Synapse stores two things in SQLite: a user profile (username, fitness goal, dietary restrictions, fitness level, and free-text notes) and conversation turns (every question and answer, timestamped and keyed to a session). Both are written immediately after a successful response, the user message first and the assistant answer second, so the store is never left half-written if the process restarts. The database lives in `synapse_memory.db` at the project root, overridable via `MEMORY_DB_PATH` for a persistent-disk mount. Retrieval happens two ways: the user profile is loaded by username and injected into the system prompt on every request so the agent knows your goals without being told again; prior conversation turns are loaded by session ID and prepended to the LLM message array as real turns so the agent can follow up naturally across sessions. Forgetting is explicit. A delete call removes a profile or a conversation. There is no automatic expiry yet, which is acceptable for a single-user demo but would need a TTL or retention policy at scale.

### Memory API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/memory/sessions` | Create a new session, returns `session_id` |
| `GET` | `/memory/sessions/{id}` | Return all messages for a session |
| `DELETE` | `/memory/sessions/{id}` | Delete a session and all its messages |
| `GET` | `/profile/{username}` | Load a user profile |
| `POST` | `/profile/{username}` | Create or update a user profile |
| `DELETE` | `/profile/{username}` | Delete a user profile |

---

## Setup

```bash
git clone https://github.com/Smr2118/synapse.git
cd synapse
cp .env.example .env          # add OPENAI_API_KEY and PINECONE_API_KEY
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**API server:**
```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

**Streamlit UI** (second terminal):
```bash
streamlit run app.py
```

Open `http://localhost:8501`. Set the API base URL in the sidebar to `http://127.0.0.1:8000` for local or `https://synapse-5w9z.onrender.com` for the live deployment.

---

## Streamlit UI tabs

| Tab | What it does |
|-----|-------------|
| 💬 **Ask** | Basic RAG — question, model selector, sources with scores |
| 🤖 **Agent Ask** | Pinecone retrieval plus live PubMed search, synthesised answer |
| 🧠 **Agentic Ask** | True agentic tool use — LLM decides which of three MCP tools to call. Think / Act / Observe trace shown |
| 🧠 **Memory Chat** | Persistent multi-turn chat keyed to a session ID |
| 📥 **Ingest** | Chunk, embed, and store plain text in Pinecone |
| 📚 **Documents** | List and delete indexed documents |
| 🔍 **Debug Retrieve** | Raw Pinecone query with similarity scores, no LLM call |
| 📊 **Evals** | Run assertion suite against trace files, with before/after comparison |

---

## API reference

### `POST /agentic/ask`

True agentic tool use. The LLM receives three MCP tool definitions and decides at runtime which to call. Pass `username` to activate personalisation and `session_id` to activate conversation memory.

```bash
curl -s -X POST https://synapse-5w9z.onrender.com/agentic/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What does research say about creatine?", "username": "smitha", "session_id": "abc123"}'
```

### `POST /ask`

Basic RAG. Retrieves top-5 Pinecone chunks and answers grounded in that context.

```bash
curl -s -X POST https://synapse-5w9z.onrender.com/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How much protein do I need to build muscle?"}'
```

### `POST /ingest`

Chunks plain text, embeds via `text-embedding-3-small`, stores in Pinecone.

```bash
curl -s -X POST https://synapse-5w9z.onrender.com/ingest \
  -H "Content-Type: application/json" \
  -d '{"document_id": "nih-protein-fact-sheet", "text": "Protein is essential..."}'
```

### `GET /debug/retrieve`

Embeds a query and returns top-k Pinecone chunks with no LLM call.

```bash
curl -s "https://synapse-5w9z.onrender.com/debug/retrieve?q=creatine+strength&top_k=5"
```

---

## Data sources

457 PubMed abstracts collected across 12 fitness and nutrition topics.

| Source | Type | Access |
|--------|------|--------|
| [PubMed](https://pubmed.ncbi.nlm.nih.gov) | Research abstracts | Free API |
| [NIH Office of Dietary Supplements](https://ods.od.nih.gov/factsheets/list-all/) | Fact sheets | Free PDFs |
| [USDA Dietary Guidelines](https://www.dietaryguidelines.gov) | Official guidelines | Free PDF |
| [WHO Physical Activity Guidelines](https://www.who.int/publications/i/item/9789240015128) | Official guidelines | Free PDF |

---

## Tech stack

- [FastAPI](https://fastapi.tiangolo.com/) — API framework
- [OpenAI Python SDK](https://github.com/openai/openai-python) — structured output, embeddings, function calling
- [Pydantic v2](https://docs.pydantic.dev/) — request and response validation
- [Pinecone](https://www.pinecone.io/) — managed vector database
- [FastMCP](https://github.com/jlowin/fastmcp) — MCP server framework
- [SQLite](https://www.sqlite.org/) — persistent memory store
- [Streamlit](https://streamlit.io/) — local and demo UI
- [Next.js](https://nextjs.org/) — production frontend on Vercel

---

## Roadmap

- [x] Structured output with Pydantic schema enforcement
- [x] Validation guardrails and retry on malformed responses
- [x] Token usage, latency, and cost tracking on every response
- [x] Document ingestion — chunking, embeddings, Pinecone storage
- [x] RAG pipeline with source citations and similarity scores
- [x] Retrieval debugger — `GET /debug/retrieve`
- [x] Refusal guard — out-of-scope questions refused before calling the LLM
- [x] Three MCP servers — PubMed, NIH MedlinePlus, Wger exercise database
- [x] Multi-agent pipeline — Pinecone retrieval plus PubMed search, synthesised answer
- [x] Agentic tool use — LLM-driven tool selection with Think / Act / Observe trace
- [x] Evals — code-based assertion suite, before/after metric from prompt fix
- [x] Persistent memory — SQLite user profiles and conversation history
