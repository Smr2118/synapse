"""True agentic ask: LLM decides whether to call the PubMed MCP tool.

Unlike the orchestrator (which hardcodes Pinecone + PubMed always), this
module gives the LLM a tool definition and lets it invoke search_pubmed
only when it judges the local context insufficient.

Flow:
  1. Build messages with Pinecone context + tool definition
  2. Agentic loop — LLM may call search_pubmed zero or more times
  3. Final parse call to get structured Answer output
"""

from __future__ import annotations

import json
import time

from mcp_server.pubmed import search_pubmed

PUBMED_TOOL = {
    "type": "function",
    "function": {
        "name": "search_pubmed",
        "description": (
            "Search PubMed for peer-reviewed research abstracts on fitness, "
            "nutrition, supplementation, and recovery. Call this when the local "
            "knowledge base context does not fully answer the question, or when "
            "more recent evidence would strengthen the answer."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search terms describing the topic, e.g. 'creatine strength training'.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of abstracts to return. Default 3, max 10.",
                    "default": 3,
                },
            },
            "required": ["query"],
        },
    },
}

_TOOLS = [PUBMED_TOOL]
_MAX_TOOL_ROUNDS = 3  # prevent runaway loops


def run(
    question: str,
    pinecone_chunks: list[dict],
    build_context_fn,
    model: str,
    client,
    system_prompt: str,
    answer_schema,
    compute_cost_fn,
) -> dict:
    """Run the agentic loop and return a result dict.

    Args:
        question:         User question.
        pinecone_chunks:  Retrieved chunks from Pinecone (may be empty).
        build_context_fn: build_context(chunks) → str
        model:            LLM model name.
        client:           OpenAI client instance.
        system_prompt:    Base system prompt.
        answer_schema:    Pydantic model for structured output (Answer).
        compute_cost_fn:  compute_cost_usd(model, prompt_tokens, completion_tokens) → float

    Returns:
        dict with keys: answer, sources, pinecone_chunks, pubmed_results,
                        tool_calls, tokens_used, model, latency_ms, cost_usd, strategy
    """
    start = time.perf_counter()

    pinecone_context = build_context_fn(pinecone_chunks) if pinecone_chunks else ""

    system_content = (
        f"{system_prompt}\n\n"
        "You have access to a search_pubmed tool. Use it when the local context "
        "below is insufficient to answer confidently or is missing recent evidence.\n\n"
    )
    if pinecone_context:
        system_content += f"Local knowledge base context:\n{pinecone_context}"
    else:
        system_content += "Local knowledge base returned no relevant chunks for this question."

    messages: list[dict] = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": question},
    ]

    tool_calls_log: list[dict] = []
    pubmed_results: list[dict] = []
    total_prompt_tokens = 0
    total_completion_tokens = 0

    # ── Agentic loop ───────────────────────────────────────────────────────────
    for _ in range(_MAX_TOOL_ROUNDS):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=_TOOLS,
            tool_choice="auto",
        )

        if response.usage:
            total_prompt_tokens += response.usage.prompt_tokens
            total_completion_tokens += response.usage.completion_tokens

        choice = response.choices[0]

        if choice.finish_reason != "tool_calls":
            break

        # Append assistant message with tool_calls so the thread stays valid
        messages.append(choice.message)

        for tc in choice.message.tool_calls:
            fn_name = tc.function.name
            fn_args = json.loads(tc.function.arguments)
            tool_calls_log.append({"tool": fn_name, "args": fn_args})

            if fn_name == "search_pubmed":
                results = search_pubmed(**fn_args)
                pubmed_results.extend(r for r in results if r.get("abstract"))
                tool_result = results
            else:
                tool_result = {"error": f"Unknown tool: {fn_name}"}

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(tool_result),
            })

    # ── Final structured output ────────────────────────────────────────────────
    final = client.chat.completions.parse(
        model=model,
        messages=messages,
        response_format=answer_schema,
    )

    if final.usage:
        total_prompt_tokens += final.usage.prompt_tokens
        total_completion_tokens += final.usage.completion_tokens

    answer = final.choices[0].message.parsed
    latency_ms = int((time.perf_counter() - start) * 1000)
    total_tokens = total_prompt_tokens + total_completion_tokens
    cost_usd = compute_cost_fn(model, total_prompt_tokens, total_completion_tokens)

    # ── Strategy label ─────────────────────────────────────────────────────────
    used_pinecone = bool(pinecone_chunks)
    used_pubmed = bool(pubmed_results)
    if used_pinecone and used_pubmed:
        strategy = "pinecone+pubmed"
    elif used_pubmed:
        strategy = "pubmed_only"
    elif used_pinecone:
        strategy = "pinecone_only"
    else:
        strategy = "refused"

    # ── Sources ────────────────────────────────────────────────────────────────
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
        "tool_calls": tool_calls_log,
        "tokens_used": total_tokens,
        "model": model,
        "latency_ms": latency_ms,
        "cost_usd": round(cost_usd, 6),
        "strategy": strategy,
    }
