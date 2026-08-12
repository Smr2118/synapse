# Synapse

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-412991?logo=openai&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063?logo=pydantic&logoColor=white)
![Pinecone](https://img.shields.io/badge/Pinecone-Vector%20DB-000000?logo=pinecone&logoColor=white)

A research-grounded fitness and nutrition assistant — answers questions about diet, exercise, and supplementation grounded in PubMed abstracts, NIH fact sheets, and USDA dietary guidelines. Not opinion. Not vibes. Sources.

## What this project demonstrates

- **Structured output** — OpenAI's `completions.parse` enforces a Pydantic schema at the model level
- **Validation guardrails** — malformed responses are caught and retried before reaching the client
- **RAG pipeline** — question is embedded, top-5 chunks retrieved from Pinecone, passed as context to the LLM
- **Source citations** — every response includes `chunk_id`, `document_id`, and similarity score for each retrieved chunk
- **Observability** — every response includes token usage, latency, model name, and cost in USD
- **Document ingestion** — plain text is chunked, embedded via `text-embedding-3-small`, and stored in Pinecone
- **Retrieval debugger** — `GET /debug/retrieve` inspects what Pinecone returns without calling the LLM
- **Agentic reasoning** — contradiction detection, refusal tool, PubMed live search *(coming)*
- **Evals** — TRACE suite measuring grounding, hallucination, and refusal accuracy *(coming)*

## How RAG works in this project

```
User question
      │
      ▼
Embed with text-embedding-3-small (1536 dimensions)
      │
      ▼
Query Pinecone — top-5 chunks by cosine similarity (threshold: 0.30)
      │
      ▼
Build context block with chunk IDs + text
      │
      ▼
Call GPT-4o with system prompt + context + question
      │
      ▼
Return structured answer + source citations
```

## Setup

```bash
git clone https://github.com/Smr2118/synapse.git
cd synapse
cp .env.example .env          # add OPENAI_API_KEY and PINECONE_API_KEY
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running

```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

## Live API

Deployed on Render — interactive docs: https://synapse-5w9z.onrender.com/docs

> **Note:** Free tier spins down after inactivity — first request may take ~30s to wake up.

---

### `POST /ask`

Retrieves relevant chunks from Pinecone and answers grounded in the retrieved context.

```bash
curl -s -X POST https://synapse-5w9z.onrender.com/ask -H "Content-Type: application/json" -d '{"question": "How much protein do I need to build muscle?"}'
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `question` | `str` | Yes | Fitness or nutrition question |
| `model` | `str` | No | Model override — `gpt-4o`, `gpt-4o-mini`, `o3-mini` |
| `force_bad` | `bool` | No | Demo knob — triggers the validation guardrail |

Example response:
```json
{
  "answer": {
    "answer": "To build muscle, a daily protein intake of 1.4–2.0g per kg of body weight is sufficient for most exercising individuals. Higher intakes of 2.3–3.1g/kg/d may be needed during caloric restriction to preserve lean mass.",
    "confidence": 0.95,
    "sources_needed": false
  },
  "sources": [
    {"chunk_id": "pubmed_28642676#2", "document_id": "pubmed_28642676", "score": 0.5916},
    {"chunk_id": "pubmed_27215586#0", "document_id": "pubmed_27215586", "score": 0.519},
    {"chunk_id": "pubmed_32824200#0", "document_id": "pubmed_32824200", "score": 0.5142},
    {"chunk_id": "pubmed_19057193#0", "document_id": "pubmed_19057193", "score": 0.5087},
    {"chunk_id": "pubmed_29182451#0", "document_id": "pubmed_29182451", "score": 0.5021}
  ],
  "tokens_used": 1947,
  "model": "gpt-4o",
  "latency_ms": 3937,
  "cost_usd": 0.00603
}
```

---

### `POST /ingest`

Chunks plain text, creates embeddings via `text-embedding-3-small`, and stores them in Pinecone.

```bash
curl -s -X POST https://synapse-5w9z.onrender.com/ingest -H "Content-Type: application/json" -d '{"document_id": "nih-protein-fact-sheet", "text": "Protein is essential for building and repairing muscle tissue..."}'
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `document_id` | `str` | Yes | Unique identifier for the document |
| `text` | `str` | Yes | Plain text to chunk, embed, and store |

Returns `400` if either field is empty.

Example response:
```json
{"document_id": "nih-protein-fact-sheet", "chunks": 4, "tokens_used": 312}
```

---

### Refusal — out of scope

When no retrieved chunks pass the similarity threshold, Synapse refuses without calling the LLM — zero cost, no hallucination:

```bash
curl -s -X POST https://synapse-5w9z.onrender.com/ask -H "Content-Type: application/json" -d '{"question": "What is the best programming language to learn in 2025?"}'
```

```json
{
  "answer": {
    "answer": "Synapse is designed to answer questions about fitness, nutrition, supplementation, and recovery grounded in peer-reviewed research. This question falls outside that scope. Please consult a qualified nutritionist or fitness professional for personalised advice.",
    "confidence": 0.0,
    "sources_needed": true
  },
  "sources": [],
  "tokens_used": 0,
  "model": "gpt-4o",
  "latency_ms": 0,
  "cost_usd": 0.0
}
```

---

### `GET /debug/retrieve`

Embeds a query and returns top-k chunks from Pinecone — **no LLM call**. Use this to verify retrieval quality before trusting `/ask`.

```bash
curl -s "https://synapse-5w9z.onrender.com/debug/retrieve?q=does+creatine+help+with+strength"
```

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `q` | `str` | required | Query to embed and search |
| `top_k` | `int` | `5` | Number of chunks to return |

Returns `400` if `q` is empty.

---

## Roadmap

- [x] Typed LLM endpoint with structured output
- [x] Validation guardrails + retry
- [x] Token usage, latency, and cost tracking
- [x] Document ingestion — chunking, embeddings, Pinecone storage
- [x] RAG — retrieve from Pinecone and ground answers in context
- [x] Source citations — chunk IDs and similarity scores in every response
- [x] Retrieval debugger — `GET /debug/retrieve`
- [x] Refusal guard — out-of-scope questions return a clear message without calling the LLM
- [ ] Source type tagging — research paper vs official guideline vs fact sheet
- [ ] Agent — contradiction detection, refusal tool, PubMed live search
- [ ] Memory — remember user goals and dietary restrictions across sessions
- [ ] Evals — TRACE suite: grounding, hallucination, refusal accuracy

## Data sources

457 PubMed abstracts collected across 12 fitness and nutrition topics via `scripts/collect_pubmed.py`.

| Source | Type | Access |
|--------|------|--------|
| [PubMed](https://pubmed.ncbi.nlm.nih.gov) | Research abstracts | Free API |
| [NIH Office of Dietary Supplements](https://ods.od.nih.gov/factsheets/list-all/) | Fact sheets | Free PDFs |
| [USDA Dietary Guidelines](https://www.dietaryguidelines.gov) | Official guidelines | Free PDF |
| [WHO Physical Activity Guidelines](https://www.who.int/publications/i/item/9789240015128) | Official guidelines | Free PDF |

## Tech stack

- [FastAPI](https://fastapi.tiangolo.com/) — async API framework
- [OpenAI Python SDK](https://github.com/openai/openai-python) — structured output + embeddings
- [Pydantic v2](https://docs.pydantic.dev/) — request/response validation
- [Pinecone](https://www.pinecone.io/) — managed vector database
