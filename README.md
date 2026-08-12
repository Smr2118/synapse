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
- **Observability** — every response includes token usage, latency, model name, and cost in USD
- **Document ingestion** — plain text is chunked, embedded via `text-embedding-3-small`, and stored in Pinecone
- **Multi-source RAG** — retrieves across research papers, official guidelines, and fact sheets with source type tagging
- **Agentic reasoning** — agent checks for contradictions, refuses out-of-scope questions, and updates memory across sessions *(coming)*
- **Evals** — TRACE eval suite measuring grounding, hallucination, and refusal accuracy *(coming)*

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

### `POST /ask`

```bash
curl -s -X POST https://synapse-5w9z.onrender.com/ask -H "Content-Type: application/json" -d '{"question": "How much protein do I need per day to build muscle?"}'
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
    "answer": "Current evidence suggests 1.6–2.2g of protein per kg of bodyweight per day optimises muscle protein synthesis.",
    "confidence": 0.91,
    "sources_needed": true
  },
  "tokens_used": 156,
  "model": "gpt-4o",
  "latency_ms": 910,
  "cost_usd": 0.001021
}
```

### `POST /ingest`

Chunks plain text, creates embeddings via `text-embedding-3-small`, and stores them in Pinecone.

```bash
curl -s -X POST https://synapse-5w9z.onrender.com/ingest -H "Content-Type: application/json" -d '{"document_id": "nih-protein-fact-sheet", "text": "Protein is essential for building and repairing muscle tissue..."}'
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `document_id` | `str` | Yes | Unique identifier for the document |
| `text` | `str` | Yes | Plain text to chunk, embed, and store |

Example response:
```json
{
  "document_id": "nih-protein-fact-sheet",
  "chunks": 4,
  "tokens_used": 312
}
```

## Roadmap

- [x] Typed LLM endpoint with structured output
- [x] Validation guardrails + retry
- [x] Token usage, latency, and cost tracking
- [x] Document ingestion — chunking, embeddings, Pinecone storage
- [ ] RAG — retrieve from Pinecone and ground answers in sources
- [ ] Source type tagging — research paper vs official guideline vs fact sheet
- [ ] Agent — contradiction detection, refusal tool, PubMed live search
- [ ] Memory — remember user goals and dietary restrictions across sessions
- [ ] Evals — TRACE suite: grounding, hallucination, refusal accuracy

## Data sources

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
