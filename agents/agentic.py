"""True agentic ask: LLM decides which tools to call from two MCP sources.

Unlike the orchestrator (which hardcodes Pinecone + PubMed always), this
module gives the LLM two tool definitions and lets it invoke either or both
based on what the question needs:
  - search_pubmed  → peer-reviewed research abstracts
  - search_nih     → official NIH guidelines and recommendations

Flow:
  1. Build messages with Pinecone context + both tool definitions
  2. Agentic loop — LLM may call tools zero or more times
  3. Final parse call to get structured Answer output
"""

from __future__ import annotations

import json
import logging
import time

logger = logging.getLogger(__name__)

from mcp_server.pubmed import search_pubmed
from mcp_server.nih import search_nih
from mcp_server.exercise import search_exercises

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

NIH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_nih",
        "description": (
            "Search NIH MedlinePlus for official health guidelines, dietary "
            "recommendations, and safe intake levels. Use this when the question "
            "asks about recommended amounts, safety thresholds, or official dietary "
            "guidance — not just what research studies show. Complements search_pubmed."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search terms, e.g. 'vitamin D recommended daily intake'.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of results to return. Default 3.",
                    "default": 3,
                },
            },
            "required": ["query"],
        },
    },
}

EXERCISE_TOOL = {
    "type": "function",
    "function": {
        "name": "search_exercises",
        "description": (
            "Search the Wger exercise database for exercises by name or muscle group. "
            "Use this when the question asks which exercises to perform, what muscles "
            "an exercise targets, equipment needed, or how to structure a workout. "
            "For research evidence on training, use search_pubmed instead."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Exercise name or muscle group, e.g. 'bicep curl', 'chest', 'squat'.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of exercises to return. Default 5.",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
}

_TOOLS = [PUBMED_TOOL, NIH_TOOL, EXERCISE_TOOL]
_TOOL_FNS = {
    "search_pubmed": search_pubmed,
    "search_nih": search_nih,
    "search_exercises": search_exercises,
}
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
        "You have access to three tools:\n"
        "- search_pubmed: peer-reviewed research abstracts. Use for 'what does research show'.\n"
        "- search_nih: official NIH guidelines and recommendations. Use for 'what is the recommended intake / is it safe'.\n"
        "- search_exercises: exercise database. Use for 'which exercises target X' or 'how to train Y'.\n"
        "Use whichever tools are relevant. You may call more than one.\n\n"
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
    nih_results: list[dict] = []
    exercise_results: list[dict] = []
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

            if fn_name in _TOOL_FNS:
                logger.info("TOOL CALL: %s | args: %s", fn_name, fn_args)
                tool_result = _TOOL_FNS[fn_name](**fn_args)
                logger.info("TOOL RESULT: %s | returned %d items", fn_name, len(tool_result) if isinstance(tool_result, list) else 1)
                if fn_name == "search_pubmed":
                    pubmed_results.extend(r for r in tool_result if r.get("abstract"))
                elif fn_name == "search_nih":
                    nih_results.extend(r for r in tool_result if r.get("summary"))
                elif fn_name == "search_exercises":
                    exercise_results.extend(r for r in tool_result if r.get("name"))
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
    used_nih = bool(nih_results)
    used_exercise = bool(exercise_results)
    active_sources = (
        (["pinecone"] if used_pinecone else [])
        + (["pubmed"] if used_pubmed else [])
        + (["nih"] if used_nih else [])
        + (["exercise"] if used_exercise else [])
    )
    strategy = "+".join(active_sources) if active_sources else "refused"
    logger.info("STRATEGY: %s | pinecone=%d pubmed=%d nih=%d exercise=%d latency=%dms",
                strategy, len(pinecone_chunks), len(pubmed_results),
                len(nih_results), len(exercise_results), int((time.perf_counter() - start) * 1000))

    # ── Sources ────────────────────────────────────────────────────────────────
    sources = (
        [
            {
                "source_type": "pinecone",
                "id": c["chunk_id"],
                "document_id": c["document_id"],
                "score": c["score"],
                "text": c["text"],
            }
            for c in pinecone_chunks
        ]
        + [
            {
                "source_type": "pubmed",
                "id": r["pmid"],
                "document_id": f"pubmed_{r['pmid']}",
                "score": None,
                "text": r["abstract"],
            }
            for r in pubmed_results
        ]
        + [
            {
                "source_type": "nih",
                "id": r["url"],
                "document_id": f"nih_{r['title'][:40].replace(' ', '_').lower()}",
                "score": None,
                "text": r["summary"],
            }
            for r in nih_results
        ]
        + [
            {
                "source_type": "exercise",
                "id": r["name"],
                "document_id": f"exercise_{r['name'].replace(' ', '_').lower()}",
                "score": None,
                "text": (
                    f"{r['name']} — {r['category']} | "
                    f"Primary: {', '.join(r['muscles_primary']) or 'N/A'} | "
                    f"Secondary: {', '.join(r['muscles_secondary']) or 'N/A'} | "
                    f"Equipment: {', '.join(r['equipment']) or 'bodyweight'}\n"
                    f"{r['description']}"
                ),
            }
            for r in exercise_results
        ]
    )

    return {
        "answer": answer,
        "sources": sources,
        "pinecone_chunks": len(pinecone_chunks),
        "pubmed_results": len(pubmed_results),
        "nih_results": len(nih_results),
        "exercise_results": len(exercise_results),
        "tool_calls": tool_calls_log,
        "tokens_used": total_tokens,
        "model": model,
        "latency_ms": latency_ms,
        "cost_usd": round(cost_usd, 6),
        "strategy": strategy,
    }
