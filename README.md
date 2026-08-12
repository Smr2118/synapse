# Synapse

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-412991?logo=openai&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063?logo=pydantic&logoColor=white)

An extensible LLM API built for production — typed, validated, and fully observable. Starting from a structured OpenAI endpoint, with RAG, agents, and evals planned as future extensions.

## What this project demonstrates

- **Structured output** — OpenAI's `completions.parse` enforces a Pydantic schema at the model level
- **Validation guardrails** — malformed responses are caught and retried before reaching the client
- **Observability** — every response includes token usage, latency, model name, and cost in USD
- **Extensible design** — built to grow into RAG, agents, and evaluation pipelines

## Setup

```bash
git clone https://github.com/Smr2118/synapse.git
cd synapse
cp .env.example .env          # add your OPENAI_API_KEY
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running

```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

## Live API

Deployed on Render:

```bash
curl -s -X POST https://synapse-5w9z.onrender.com/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Retrieval-Augmented Generation in one sentence?"}'
```

Interactive docs: https://synapse-5w9z.onrender.com/docs

> **Note:** Free tier spins down after inactivity — first request may take ~30s to wake up.

## Example response

```json
{
  "answer": {
    "answer": "RAG enhances LLMs by retrieving relevant documents at query time and including them in the prompt.",
    "confidence": 0.97,
    "sources_needed": false
  },
  "tokens_used": 142,
  "model": "gpt-4o",
  "latency_ms": 834,
  "cost_usd": 0.000965
}
```

## Request fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `question` | `str` | Yes | The question to ask |
| `model` | `str` | No | Model override — `gpt-4o`, `gpt-4o-mini`, `o3-mini` |
| `force_bad` | `bool` | No | Demo knob — triggers the validation guardrail |

## Roadmap

- [x] Typed LLM endpoint with structured output
- [x] Validation guardrails + retry
- [x] Token usage, latency, and cost tracking
- [ ] RAG — document ingestion and vector retrieval
- [ ] Agents — multi-step reasoning and tool use
- [ ] Evals — automated response quality scoring

## Tech stack

- [FastAPI](https://fastapi.tiangolo.com/) — async API framework
- [OpenAI Python SDK](https://github.com/openai/openai-python) — structured output via `completions.parse`
- [Pydantic v2](https://docs.pydantic.dev/) — request/response validation
