"""Streamlit UI for Synapse — fitness and nutrition research assistant.

Run:
    streamlit run app.py

Set the API base URL in the sidebar to point at local or Render.
"""

import os

import httpx
import streamlit as st

DEFAULT_URL = os.getenv("API_BASE_URL", "https://synapse-5w9z.onrender.com")


def call(method: str, url: str, **kwargs) -> tuple[int, dict | str]:
    try:
        response = getattr(httpx, method)(url, timeout=120.0, **kwargs)
        try:
            return response.status_code, response.json()
        except Exception:
            return response.status_code, response.text
    except httpx.ConnectError:
        return 0, {"error": f"Cannot reach {url} — is the server running?"}
    except httpx.HTTPError as exc:
        return 0, {"error": str(exc)}


st.set_page_config(page_title="Synapse", layout="wide", page_icon="🧠")

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🧠 Synapse")
    st.caption("Research-grounded fitness & nutrition assistant")
    st.divider()
    base_url = st.text_input("API base URL", DEFAULT_URL)
    st.markdown(f"**Docs:** [{base_url}/docs]({base_url}/docs)")
    st.divider()
    st.markdown("**Stack**")
    st.markdown("FastAPI · OpenAI · Pinecone · Pydantic")

# ── Tabs ───────────────────────────────────────────────────────────────────────
ask_tab, agent_tab, ingest_tab, debug_tab = st.tabs(["💬 Ask", "🤖 Agent Ask", "📥 Ingest", "🔍 Debug Retrieve"])


# ── Ask ────────────────────────────────────────────────────────────────────────
with ask_tab:
    st.header("Ask a fitness or nutrition question")
    st.caption("Answers are grounded in PubMed abstracts and official guidelines.")

    question = st.text_input("Question", placeholder="How much protein do I need to build muscle?")

    col1, col2 = st.columns([2, 1])
    with col1:
        model = st.selectbox("Model", ["gpt-4o", "gpt-4o-mini", "o3-mini"], index=0)
    with col2:
        force_bad = st.checkbox("force_bad (guardrail demo)")

    if st.button("Ask", type="primary", disabled=not question.strip()):
        with st.spinner("Retrieving and answering..."):
            status, data = call(
                "post",
                f"{base_url}/ask",
                json={"question": question, "model": model, "force_bad": force_bad},
            )

        if status == 0 or "error" in (data if isinstance(data, dict) else {}):
            st.error(data.get("error", data))
        elif status != 200:
            st.error(f"HTTP {status}: {data}")
        else:
            answer = data.get("answer", {})
            sources = data.get("sources", [])

            # Answer
            if not sources:
                st.warning(answer.get("answer", ""))
            else:
                st.success(answer.get("answer", ""))

            # Metrics
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Confidence", f"{answer.get('confidence', 0):.0%}")
            m2.metric("Sources needed", "Yes" if answer.get("sources_needed") else "No")
            m3.metric("Tokens", data.get("tokens_used", 0))
            m4.metric("Latency", f"{data.get('latency_ms', 0)} ms")
            m5.metric("Cost", f"${data.get('cost_usd', 0):.6f}")

            # Sources
            if sources:
                st.subheader("Sources retrieved")
                for s in sources:
                    with st.expander(f"{s['document_id']} — score: {s['score']}"):
                        st.code(s["chunk_id"])
            else:
                st.info("No relevant sources found — question is outside the knowledge base.")


# ── Agent Ask ──────────────────────────────────────────────────────────────────
with agent_tab:
    st.header("Agent ask")
    st.caption(
        "Orchestrator runs Pinecone retrieval + live PubMed search via MCP tool, "
        "then synthesises a grounded answer from both sources."
    )

    agent_question = st.text_input(
        "Question",
        placeholder="Does creatine help with strength?",
        key="agent_question",
    )
    agent_model = st.selectbox("Model", ["gpt-4o", "gpt-4o-mini", "o3-mini"], index=0, key="agent_model")

    if st.button("Ask Agent", type="primary", disabled=not agent_question.strip()):
        with st.spinner("Running Pinecone retrieval + PubMed search..."):
            status, data = call(
                "post",
                f"{base_url}/agent/ask",
                json={"question": agent_question, "model": agent_model},
            )

        if status == 0 or "error" in (data if isinstance(data, dict) else {}):
            st.error(data.get("error", data))
        elif status != 200:
            st.error(f"HTTP {status}: {data}")
        else:
            answer = data.get("answer", {})
            sources = data.get("sources", [])
            strategy = data.get("strategy", "")

            STRATEGY_LABELS = {
                "pinecone+pubmed": "🔀 Pinecone + PubMed",
                "pinecone_only": "📦 Pinecone only",
                "pubmed_only": "🔬 PubMed only",
                "refused": "🚫 Refused",
            }
            st.info(f"Strategy: **{STRATEGY_LABELS.get(strategy, strategy)}**")

            if not sources:
                st.warning(answer.get("answer", ""))
            else:
                st.success(answer.get("answer", ""))

            m1, m2, m3, m4, m5, m6 = st.columns(6)
            m1.metric("Confidence", f"{answer.get('confidence', 0):.0%}")
            m2.metric("Pinecone chunks", data.get("pinecone_chunks", 0))
            m3.metric("PubMed results", data.get("pubmed_results", 0))
            m4.metric("Tokens", data.get("tokens_used", 0))
            m5.metric("Latency", f"{data.get('latency_ms', 0)} ms")
            m6.metric("Cost", f"${data.get('cost_usd', 0):.6f}")

            pinecone_sources = [s for s in sources if s.get("source_type") == "pinecone"]
            pubmed_sources = [s for s in sources if s.get("source_type") == "pubmed"]

            if pinecone_sources:
                st.subheader("Pinecone sources")
                for s in pinecone_sources:
                    with st.expander(f"{s['document_id']} — score: {s['score']}"):
                        st.code(s["id"])
                        st.write(s.get("text", ""))

            if pubmed_sources:
                st.subheader("PubMed live results")
                for s in pubmed_sources:
                    with st.expander(f"PMID {s['id']}"):
                        st.write(s.get("text", ""))


# ── Ingest ─────────────────────────────────────────────────────────────────────
with ingest_tab:
    st.header("Ingest a document")
    st.caption("Text is chunked, embedded via text-embedding-3-small, and stored in Pinecone.")

    doc_id = st.text_input("Document ID", placeholder="e.g. nih-protein-fact-sheet")
    text = st.text_area("Text", placeholder="Paste plain text here...", height=200)

    if st.button("Ingest", type="primary", disabled=not doc_id.strip() or not text.strip()):
        with st.spinner("Chunking and embedding..."):
            status, data = call(
                "post",
                f"{base_url}/ingest",
                json={"document_id": doc_id, "text": text},
            )

        if status == 400:
            st.error(f"Bad request: {data.get('detail', data)}")
        elif status != 200 or "error" in (data if isinstance(data, dict) else {}):
            st.error(data.get("error", data) if isinstance(data, dict) else data)
        else:
            st.success(f"Ingested **{data['document_id']}** — {data['chunks']} chunks, {data['tokens_used']} tokens used")


# ── Debug Retrieve ─────────────────────────────────────────────────────────────
with debug_tab:
    st.header("Debug retrieval")
    st.caption("Embeds a query and returns top-k chunks from Pinecone — no LLM call.")

    query = st.text_input("Query", placeholder="does creatine help with strength?")
    top_k = st.slider("Top K", min_value=1, max_value=10, value=5)

    if st.button("Retrieve", type="primary", disabled=not query.strip()):
        with st.spinner("Querying Pinecone..."):
            status, data = call("get", f"{base_url}/debug/retrieve", params={"q": query, "top_k": top_k})

        if status == 400:
            st.error(f"Bad request: {data.get('detail', data)}")
        elif status != 200 or "error" in (data if isinstance(data, dict) else {}):
            st.error(data.get("error", data) if isinstance(data, dict) else data)
        else:
            if not data:
                st.warning("No chunks returned — query may be out of scope.")
            else:
                st.success(f"{len(data)} chunks retrieved")
                for i, chunk in enumerate(data, 1):
                    with st.expander(f"#{i} · {chunk['document_id']} · score: {chunk['score']}"):
                        st.caption(f"Chunk ID: `{chunk['document_id']}`")
                        st.write(chunk["text"])
