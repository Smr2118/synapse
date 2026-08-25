"""Typed LLM API with document ingestion for RAG."""

import logging
import os
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO)

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pinecone import Pinecone
from pydantic import BaseModel, Field, ValidationError

# Load .env from this folder so the key is found regardless of shell working directory.
_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(_ENV_PATH)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://synapse-ui-gamma.vercel.app",
        "http://localhost:3000",
    ],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)

client = OpenAI()
_pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
_index = _pc.Index(os.getenv("PINECONE_INDEX", "synapse"))

DEFAULT_MODEL = "gpt-4o"
EMBEDDING_MODEL = "text-embedding-3-small"
CHUNK_SIZE = 200  # words per chunk
CHUNK_OVERLAP = 20  # words of overlap between chunks

# Stage 5 — per-1K-token input/output USD (derived from OpenAI list prices).
MODEL_PRICES_PER_1K: dict[str, tuple[float, float]] = {
    "gpt-4o": (0.0025, 0.01),
    "gpt-4o-mini": (0.00015, 0.0006),
    "o3-mini": (0.0011, 0.0044),
}


class Answer(BaseModel):
    """Structured model output — this is what turns a chatbot into a component."""

    answer: str
    confidence: float = Field(ge=0.0, le=1.0)
    sources_needed: bool


class AskRequest(BaseModel):
    """Typed request body so bad input is rejected before we spend tokens."""

    question: str
    force_bad: bool = False  # Stage 3 demo knob — first attempt breaks schema on purpose.
    model: str | None = None  # Stage 4 — optional override to swap models live.


class Source(BaseModel):
    chunk_id: str
    document_id: str
    score: float


class AskResponse(BaseModel):
    """Typed response so callers always get the same shape back."""

    answer: Answer
    sources: list[Source]
    tokens_used: int
    model: str
    latency_ms: int
    cost_usd: float


class AgentSource(BaseModel):
    source_type: str  # "pinecone" or "pubmed"
    id: str
    document_id: str
    score: float | None
    text: str


class AgentAskResponse(BaseModel):
    answer: Answer
    sources: list[AgentSource]
    pinecone_chunks: int
    pubmed_results: int
    tokens_used: int
    model: str
    latency_ms: int
    cost_usd: float
    strategy: str  # pinecone_only | pubmed_only | pinecone+pubmed | refused


class AgenticAskResponse(BaseModel):
    answer: Answer
    sources: list[AgentSource]
    pinecone_chunks: int
    pubmed_results: int
    nih_results: int
    exercise_results: int
    tool_calls: list[dict]  # which tools the LLM chose to invoke and with what args
    tokens_used: int
    model: str
    latency_ms: int
    cost_usd: float
    strategy: str


class IngestRequest(BaseModel):
    document_id: str
    text: str


class IngestResponse(BaseModel):
    document_id: str
    chunks: int
    tokens_used: int


def chunk_text(text: str) -> list[str]:
    words = text.split()
    result = []
    for i in range(0, len(words), CHUNK_SIZE - CHUNK_OVERLAP):
        chunk = " ".join(words[i : i + CHUNK_SIZE])
        if chunk:
            result.append(chunk)
    return result


RAG_TOP_K = 5
RAG_SCORE_THRESHOLD = 0.30  # below this score, chunks are too weak to be useful

SYSTEM_PROMPT = """You are Synapse, a research-grounded fitness and nutrition assistant.

Answer the question using ONLY the context provided below.
- Be specific and grounded — your answer must be supported by the context.
- If the context does not contain enough information, say so clearly and set sources_needed=true.
- Do not fabricate facts not present in the context.
- Set confidence based on how well the context supports your answer."""

AGENTIC_SYSTEM_PROMPT = """You are Synapse, a research-grounded fitness and nutrition assistant.

You MUST call at least one tool before answering any fitness, nutrition, supplementation,
or exercise question. Do not answer from your training data alone — every substantive
answer must be grounded in evidence retrieved from the tools.

Available tools:
- search_pubmed: peer-reviewed research abstracts. Use for 'what does research show'.
- search_nih: official NIH guidelines and recommendations. Use for 'what is the recommended intake / is it safe'.
- search_exercises: exercise database. Use for 'which exercises target X' or 'how to train Y'.

Rules:
- Always call at least one tool for fitness or nutrition questions, even if you think you know the answer.
- You may call more than one tool if the question spans multiple domains.
- Set sources_needed=true if the retrieved content was insufficient to fully answer the question.
- Only skip tools if the question is clearly out of scope (not about fitness, nutrition, or exercise).
- Ground your answer in the retrieved content. Do not add facts not present in the tool results.

Writing style:
- Write in plain, simple English. Avoid jargon.
- Use short sentences. One idea per sentence.
- Break the answer into short paragraphs — no more than 2-3 sentences each.
- Use a blank line between paragraphs so the answer is easy to scan.
- Do not use bullet points or numbered lists unless the question explicitly asks for steps."""


def retrieve_chunks(question: str, top_k: int = RAG_TOP_K) -> list[dict]:
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=[question])
    query_vector = response.data[0].embedding
    results = _index.query(vector=query_vector, top_k=top_k, include_metadata=True)
    return [
        {
            "chunk_id": match.id,
            "document_id": match.metadata.get("document_id", ""),
            "score": round(match.score, 4),
            "text": match.metadata.get("text", ""),
        }
        for match in results.matches
        if match.score >= RAG_SCORE_THRESHOLD
    ]


def build_context(chunks: list[dict]) -> str:
    parts = [f"[{c['chunk_id']}]\n{c['text']}" for c in chunks]
    return "\n\n---\n\n".join(parts)


def compute_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Turn real usage into dollars — same prompt, different model, different cost."""

    prices = MODEL_PRICES_PER_1K.get(model, MODEL_PRICES_PER_1K[DEFAULT_MODEL])
    input_per_1k, output_per_1k = prices
    return (prompt_tokens / 1000 * input_per_1k) + (completion_tokens / 1000 * output_per_1k)


def call_model_structured(question: str, model: str, context: str = "") -> tuple[Answer, int, int, int]:
    messages = []
    if context:
        messages.append({
            "role": "system",
            "content": f"{SYSTEM_PROMPT}\n\nContext:\n{context}",
        })
    messages.append({"role": "user", "content": question})

    completion = client.chat.completions.parse(
        model=model,
        messages=messages,
        response_format=Answer,
    )

    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise ValueError("Model returned no parseable structured output")

    usage = completion.usage
    total = usage.total_tokens if usage else 0
    prompt_tokens = usage.prompt_tokens if usage else 0
    completion_tokens = usage.completion_tokens if usage else 0
    return parsed, total, prompt_tokens, completion_tokens


def call_model_unsafe(question: str, model: str) -> tuple[Answer, int, int, int]:
    """
    Stage 3 demo path: free-form JSON call, then validate locally.
    The bad instruction makes confidence a string so Pydantic rejects it reliably.
    """

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": (
                    f"{question}\n\n"
                    "Reply with ONLY a JSON object using keys answer, confidence, sources_needed. "
                    "Set confidence to the string 'very high' (not a number)."
                ),
            }
        ],
    )

    raw = completion.choices[0].message.content or ""
    # Guardrail: refuse malformed output instead of passing it through to clients.
    answer = Answer.model_validate_json(raw)

    usage = completion.usage
    total = usage.total_tokens if usage else 0
    prompt_tokens = usage.prompt_tokens if usage else 0
    completion_tokens = usage.completion_tokens if usage else 0
    return answer, total, prompt_tokens, completion_tokens


@app.post("/ask")
def ask(body: AskRequest) -> AskResponse:
    """Retrieve relevant chunks from Pinecone, then answer with grounded context."""

    model = body.model or DEFAULT_MODEL
    last_error: str | None = None

    chunks = retrieve_chunks(body.question)
    sources = [Source(chunk_id=c["chunk_id"], document_id=c["document_id"], score=c["score"]) for c in chunks]

    if not chunks:
        return AskResponse(
            answer=Answer(
                answer="Synapse is designed to answer questions about fitness, nutrition, supplementation, and recovery grounded in peer-reviewed research. This question falls outside that scope. Please consult a qualified nutritionist or fitness professional for personalised advice.",
                confidence=0.0,
                sources_needed=True,
            ),
            sources=[],
            tokens_used=0,
            model=model,
            latency_ms=0,
            cost_usd=0.0,
        )

    context = build_context(chunks)

    for attempt in range(2):
        try:
            start = time.perf_counter()

            use_bad_path = body.force_bad and attempt == 0
            if use_bad_path:
                answer, tokens_used, prompt_tokens, completion_tokens = call_model_unsafe(
                    body.question, model
                )
            else:
                answer, tokens_used, prompt_tokens, completion_tokens = call_model_structured(
                    body.question, model, context=context
                )

            latency_ms = int((time.perf_counter() - start) * 1000)
            cost_usd = compute_cost_usd(model, prompt_tokens, completion_tokens)

            return AskResponse(
                answer=answer,
                sources=sources,
                tokens_used=tokens_used,
                model=model,
                latency_ms=latency_ms,
                cost_usd=round(cost_usd, 6),
            )
        except (ValidationError, ValueError) as exc:
            last_error = str(exc)
            continue

    raise HTTPException(
        status_code=502,
        detail=f"Model response failed schema validation after retry: {last_error}",
    )


@app.post("/agent/ask")
def agent_ask(body: AskRequest) -> AgentAskResponse:
    """Multi-agent ask: Pinecone retrieval first, PubMed live search as fallback.

    Strategy is chosen automatically:
    - pinecone_only   — local chunks are sufficient
    - pubmed_only     — no local chunks passed threshold
    - pinecone+pubmed — local chunks exist but evidence is thin
    - refused         — no evidence found anywhere
    """
    from agents.orchestrator import run as orchestrate

    model = body.model or DEFAULT_MODEL

    result = orchestrate(
        question=body.question,
        retrieve_fn=retrieve_chunks,
        build_context_fn=build_context,
        call_model_fn=call_model_structured,
        compute_cost_fn=compute_cost_usd,
        model=model,
    )

    return AgentAskResponse(
        answer=result["answer"],
        sources=[AgentSource(**s) for s in result["sources"]],
        pinecone_chunks=result["pinecone_chunks"],
        pubmed_results=result["pubmed_results"],
        tokens_used=result["tokens_used"],
        model=result["model"],
        latency_ms=result["latency_ms"],
        cost_usd=result["cost_usd"],
        strategy=result["strategy"],
    )


@app.post("/agentic/ask")
def agentic_ask(body: AskRequest) -> AgenticAskResponse:
    """True agentic ask: the LLM decides at runtime whether to call search_pubmed.

    The model receives Pinecone context and a tool definition. It invokes the
    PubMed MCP tool only when it judges the local context insufficient.
    tool_calls in the response shows exactly what the LLM chose to call.
    """
    from agents.agentic import run as agentic_run

    model = body.model or DEFAULT_MODEL

    result = agentic_run(
        question=body.question,
        pinecone_chunks=[],  # LLM drives retrieval via tools — no pre-loading
        build_context_fn=build_context,
        model=model,
        client=client,
        system_prompt=AGENTIC_SYSTEM_PROMPT,
        answer_schema=Answer,
        compute_cost_fn=compute_cost_usd,
    )

    return AgenticAskResponse(
        answer=result["answer"],
        sources=[AgentSource(**s) for s in result["sources"]],
        pinecone_chunks=result["pinecone_chunks"],
        pubmed_results=result["pubmed_results"],
        nih_results=result["nih_results"],
        exercise_results=result["exercise_results"],
        tool_calls=result["tool_calls"],
        tokens_used=result["tokens_used"],
        model=result["model"],
        latency_ms=result["latency_ms"],
        cost_usd=result["cost_usd"],
        strategy=result["strategy"],
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


class DocumentInfo(BaseModel):
    document_id: str
    chunks: int


class DocumentsResponse(BaseModel):
    documents: list[DocumentInfo]
    total_documents: int
    total_chunks: int


@app.get("/documents")
def list_documents() -> DocumentsResponse:
    """List all documents indexed in Pinecone with chunk counts."""
    doc_chunks: dict[str, int] = {}
    for page in _index.list():
        for item in page.vectors:
            doc_id = item.id.rsplit("#", 1)[0]
            doc_chunks[doc_id] = doc_chunks.get(doc_id, 0) + 1

    documents = sorted(
        [DocumentInfo(document_id=d, chunks=c) for d, c in doc_chunks.items()],
        key=lambda x: x.document_id,
    )
    return DocumentsResponse(
        documents=documents,
        total_documents=len(documents),
        total_chunks=sum(d.chunks for d in documents),
    )


class DeleteResponse(BaseModel):
    document_id: str
    deleted_chunks: int


@app.delete("/documents/{document_id}")
def delete_document(document_id: str) -> DeleteResponse:
    """Delete all vectors for a document from Pinecone."""
    ids_to_delete = [
        item.id
        for page in _index.list(prefix=f"{document_id}#")
        for item in page.vectors
    ]

    if not ids_to_delete:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found")

    _index.delete(ids=ids_to_delete)
    return DeleteResponse(document_id=document_id, deleted_chunks=len(ids_to_delete))


class RetrievedChunk(BaseModel):
    document_id: str
    score: float
    text: str


@app.get("/debug/retrieve")
def debug_retrieve(q: str, top_k: int = 5) -> list[RetrievedChunk]:
    """Embed a query and return top-k chunks from Pinecone — no LLM call."""

    if not q.strip():
        raise HTTPException(status_code=400, detail="q must not be empty")

    response = client.embeddings.create(model=EMBEDDING_MODEL, input=[q])
    query_vector = response.data[0].embedding

    results = _index.query(vector=query_vector, top_k=top_k, include_metadata=True)

    return [
        RetrievedChunk(
            document_id=match.metadata.get("document_id", ""),
            score=round(match.score, 4),
            text=match.metadata.get("text", ""),
        )
        for match in results.matches
    ]


@app.post("/ingest")
def ingest(body: IngestRequest) -> IngestResponse:
    """Chunk plain text and store embeddings for later retrieval."""

    if not body.document_id.strip():
        raise HTTPException(status_code=400, detail="document_id must not be empty")
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="text must not be empty")

    chunks = chunk_text(body.text)

    response = client.embeddings.create(model=EMBEDDING_MODEL, input=chunks)
    embeddings = [e.embedding for e in response.data]
    tokens_used = response.usage.total_tokens if response.usage else 0

    vectors = [
        {
            "id": f"{body.document_id}#{i}",
            "values": embedding,
            "metadata": {"text": chunk, "document_id": body.document_id},
        }
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))
    ]
    _index.upsert(vectors=vectors)

    return IngestResponse(
        document_id=body.document_id,
        chunks=len(chunks),
        tokens_used=tokens_used,
    )
