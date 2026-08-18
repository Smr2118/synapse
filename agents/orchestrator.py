"""Multi-agent orchestrator for Synapse.

Flow:
  1. Retrieval Agent  — query Pinecone for locally ingested chunks
  2. PubMed Agent     — call search_pubmed MCP tool for live research
                        (always runs when the question is in scope)
  3. Synthesis Agent  — ground the final answer in combined context

Strategy labels:
  pinecone+pubmed — both sources returned results (normal in-scope path)
  pubmed_only     — Pinecone found nothing but PubMed did
  refused         — no evidence found anywhere
"""

from __future__ import annotations

import time

from mcp_server.pubmed import search_pubmed


def run(
    question: str,
    retrieve_fn,
    build_context_fn,
    call_model_fn,
    compute_cost_fn,
    model: str,
) -> dict:
    """Orchestrate retrieval, optional PubMed escalation, and synthesis.

    Args:
        question:        User's question.
        retrieve_fn:     retrieve_chunks(question) → list[dict]
        build_context_fn: build_context(chunks) → str
        call_model_fn:   call_model_structured(question, model, context) → (Answer, total, prompt, completion)
        compute_cost_fn: compute_cost_usd(model, prompt_tokens, completion_tokens) → float
        model:           LLM model name.

    Returns:
        dict with keys: answer, sources, pinecone_chunks, pubmed_results,
                        tokens_used, model, latency_ms, cost_usd, strategy
    """
    start = time.perf_counter()

    # ── Step 1: Retrieval Agent (Pinecone) ─────────────────────────────────────
    pinecone_chunks = retrieve_fn(question)

    # ── Step 2: PubMed Agent (MCP tool) — always runs when in scope ────────────
    pubmed_results = []
    if pinecone_chunks:
        raw = search_pubmed(question, max_results=3)
        pubmed_results = [r for r in raw if r.get("abstract")]

    # ── Step 3: Determine strategy label ───────────────────────────────────────
    if pinecone_chunks and pubmed_results:
        strategy = "pinecone+pubmed"
    elif pubmed_results:
        strategy = "pubmed_only"
    elif pinecone_chunks:
        strategy = "pinecone_only"
    else:
        strategy = "refused"

    # ── Step 4: Refusal if no evidence at all ──────────────────────────────────
    if strategy == "refused":
        from main import Answer  # local import to avoid circular dep
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {
            "answer": Answer(
                answer=(
                    "Synapse is designed to answer questions about fitness, nutrition, "
                    "supplementation, and recovery grounded in peer-reviewed research. "
                    "This question falls outside that scope. Please consult a qualified "
                    "nutritionist or fitness professional for personalised advice."
                ),
                confidence=0.0,
                sources_needed=True,
            ),
            "sources": [],
            "pinecone_chunks": 0,
            "pubmed_results": 0,
            "tokens_used": 0,
            "model": model,
            "latency_ms": latency_ms,
            "cost_usd": 0.0,
            "strategy": strategy,
        }

    # ── Step 5: Build combined context ─────────────────────────────────────────
    context_parts = []

    if pinecone_chunks:
        context_parts.append(build_context_fn(pinecone_chunks))

    if pubmed_results:
        pubmed_blocks = [
            f"[pubmed_{r['pmid']}]\n{r['title']}\n\n{r['abstract']}"
            for r in pubmed_results
        ]
        context_parts.append("\n\n---\n\n".join(pubmed_blocks))

    context = "\n\n===\n\n".join(context_parts)

    # ── Step 6: Synthesis Agent (LLM) ──────────────────────────────────────────
    answer, tokens_used, prompt_tokens, completion_tokens = call_model_fn(
        question, model, context
    )
    latency_ms = int((time.perf_counter() - start) * 1000)
    cost_usd = compute_cost_fn(model, prompt_tokens, completion_tokens)

    # ── Step 7: Assemble sources ────────────────────────────────────────────────
    sources = [
        {
            "source_type": "pinecone",
            "id": c["chunk_id"],
            "document_id": c["document_id"],
            "score": c["score"],
            "text": c["text"],
        }
        for c in pinecone_chunks
    ] + [
        {
            "source_type": "pubmed",
            "id": r["pmid"],
            "document_id": f"pubmed_{r['pmid']}",
            "score": None,
            "text": r["abstract"],
        }
        for r in pubmed_results
    ]

    return {
        "answer": answer,
        "sources": sources,
        "pinecone_chunks": len(pinecone_chunks),
        "pubmed_results": len(pubmed_results),
        "tokens_used": tokens_used,
        "model": model,
        "latency_ms": latency_ms,
        "cost_usd": round(cost_usd, 6),
        "strategy": strategy,
    }
