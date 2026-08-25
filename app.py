"""Streamlit UI for Synapse — fitness and nutrition research assistant.

Run:
    streamlit run app.py

Set the API base URL in the sidebar to point at local or Render.
"""

import json
import os
from pathlib import Path

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
ask_tab, agent_tab, agentic_tab, ingest_tab, docs_tab, debug_tab, evals_tab = st.tabs(["💬 Ask", "🤖 Agent Ask", "🧠 Agentic Ask", "📥 Ingest", "📚 Documents", "🔍 Debug Retrieve", "📊 Evals"])


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


# ── Agentic Ask ────────────────────────────────────────────────────────────────
with agentic_tab:
    st.header("Agentic ask")
    st.caption(
        "The LLM has three tools: search_pubmed (research), search_nih (guidelines), "
        "search_exercises (exercise DB). It decides which to call based on the question. "
        "tool_calls shows exactly what the LLM invoked and with what query."
    )

    agentic_question = st.text_input(
        "Question",
        placeholder="What does recent research say about NMN supplementation?",
        key="agentic_question",
    )
    agentic_model = st.selectbox("Model", ["gpt-4o", "gpt-4o-mini", "o3-mini"], index=0, key="agentic_model")

    if st.button("Ask (Agentic)", type="primary", disabled=not agentic_question.strip()):
        with st.spinner("LLM reasoning about which tools to call..."):
            status, data = call(
                "post",
                f"{base_url}/agentic/ask",
                json={"question": agentic_question, "model": agentic_model},
            )

        if status == 0 or "error" in (data if isinstance(data, dict) else {}):
            st.error(data.get("error", data))
        elif status != 200:
            st.error(f"HTTP {status}: {data}")
        else:
            answer = data.get("answer", {})
            sources = data.get("sources", [])
            strategy = data.get("strategy", "")
            tool_calls = data.get("tool_calls", [])

            # ── Agent loop trace (Think / Act / Observe) ───────────────────────
            ICON = {"pinecone": "📦", "pubmed": "🔬", "nih": "🏛️", "exercise": "🏋️"}
            TOOL_ICON = {"search_pubmed": "🔬", "search_nih": "🏛️", "search_exercises": "🏋️"}
            RESULT_COUNT = {
                "search_pubmed": data.get("pubmed_results", 0),
                "search_nih": data.get("nih_results", 0),
                "search_exercises": data.get("exercise_results", 0),
            }

            with st.status("Agent decision loop", expanded=True) as status_box:
                # THINK — initial reasoning
                if tool_calls:
                    tools_chosen = ", ".join(f"`{tc['tool']}`" for tc in tool_calls)
                    st.write(f"🧠 **THINK** — LLM decided to call: {tools_chosen}")
                else:
                    st.write("🧠 **THINK** — LLM judged local context sufficient, no tools needed")

                # ACT + OBSERVE — one pair per tool call
                for tc in tool_calls:
                    icon = TOOL_ICON.get(tc["tool"], "🔧")
                    st.write(f"{icon} **ACT** — `{tc['tool']}` called with query: `{tc['args'].get('query', tc['args'])}`")
                    n = RESULT_COUNT.get(tc["tool"], "?")
                    st.write(f"👁️ **OBSERVE** — `{tc['tool']}` returned **{n}** result(s)")

                # ANSWER
                confidence = answer.get("confidence", 0)
                st.write(f"✅ **ANSWER** — confidence {confidence:.0%}, synthesising from {len(sources)} source(s)")
                status_box.update(label="Agent loop complete", state="complete")

            st.divider()

            if not sources:
                st.warning(answer.get("answer", ""))
            else:
                st.success(answer.get("answer", ""))

            m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
            m1.metric("Confidence", f"{answer.get('confidence', 0):.0%}")
            m2.metric("Pinecone", data.get("pinecone_chunks", 0))
            m3.metric("PubMed", data.get("pubmed_results", 0))
            m4.metric("NIH", data.get("nih_results", 0))
            m5.metric("Exercise", data.get("exercise_results", 0))
            m6.metric("Latency", f"{data.get('latency_ms', 0)} ms")
            m7.metric("Cost", f"${data.get('cost_usd', 0):.6f}")

            pinecone_sources = [s for s in sources if s.get("source_type") == "pinecone"]
            pubmed_sources = [s for s in sources if s.get("source_type") == "pubmed"]
            nih_sources = [s for s in sources if s.get("source_type") == "nih"]
            exercise_sources = [s for s in sources if s.get("source_type") == "exercise"]

            if pinecone_sources:
                st.subheader("📦 Pinecone sources")
                for s in pinecone_sources:
                    with st.expander(f"{s['document_id']} — score: {s['score']}"):
                        st.write(s.get("text", ""))

            if pubmed_sources:
                st.subheader("🔬 PubMed live results")
                for s in pubmed_sources:
                    with st.expander(f"PMID {s['id']}"):
                        st.write(s.get("text", ""))

            if nih_sources:
                st.subheader("🏛️ NIH guidelines")
                for s in nih_sources:
                    with st.expander(s["id"] or s["document_id"]):
                        st.write(s.get("text", ""))

            if exercise_sources:
                st.subheader("🏋️ Exercises")
                for s in exercise_sources:
                    with st.expander(s["id"]):
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


# ── Documents ──────────────────────────────────────────────────────────────────
with docs_tab:
    st.header("Indexed documents")
    st.caption("Lists every document in Pinecone with its chunk count. Delete removes all vectors for that document.")

    col_refresh, col_spacer = st.columns([1, 4])
    with col_refresh:
        refresh = st.button("Refresh", type="primary")

    if refresh:
        with st.spinner("Loading documents..."):
            status, data = call("get", f"{base_url}/documents")

        if status == 0 or "error" in (data if isinstance(data, dict) else {}):
            st.error(data.get("error", data))
        elif status != 200:
            st.error(f"HTTP {status}: {data}")
        else:
            documents = data.get("documents", [])
            m1, m2 = st.columns(2)
            m1.metric("Total documents", data.get("total_documents", 0))
            m2.metric("Total chunks", data.get("total_chunks", 0))

            if not documents:
                st.info("No documents indexed yet.")
            else:
                st.divider()
                for doc in documents:
                    col_name, col_chunks, col_del = st.columns([4, 1, 1])
                    with col_name:
                        st.text(doc["document_id"])
                    with col_chunks:
                        st.caption(f"{doc['chunks']} chunks")
                    with col_del:
                        if st.button("Delete", key=f"del_{doc['document_id']}"):
                            del_status, del_data = call("delete", f"{base_url}/documents/{doc['document_id']}")
                            if del_status == 200:
                                st.success(f"Deleted {del_data.get('deleted_chunks', 0)} chunks")
                                st.rerun()
                            else:
                                st.error(del_data.get("detail", del_data))


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


# ── Evals ──────────────────────────────────────────────────────────────────────
with evals_tab:
    st.header("Eval suite")
    st.caption(
        "Code-based assertions against collected traces. "
        "Load a traces JSON file to run all checks and see which questions pass or fail."
    )

    col1, col2 = st.columns(2)
    with col1:
        traces_path = st.text_input("Traces file", value="evals/traces.json")
    with col2:
        compare_path = st.text_input("Compare file (before/after)", placeholder="evals/traces_after.json")

    if st.button("Run checks", type="primary"):
        from evals.checks import ALL_CHECKS, run_checks

        CHECK_NAMES = list(ALL_CHECKS.keys())

        def score_traces(path: str) -> list[dict]:
            traces = json.loads(Path(path).read_text(encoding="utf-8"))
            results = []
            for trace in traces:
                checks = run_checks(trace)
                row = {
                    "id": trace["id"],
                    "question": trace["question"][:52] + "…" if len(trace["question"]) > 52 else trace["question"],
                    "expected": trace.get("expected", "?"),
                    "strategy": trace.get("response", {}).get("strategy", "n/a"),
                }
                for name, (passed, reason) in checks.items():
                    row[name] = "PASS" if passed else "FAIL"
                    row[f"{name}_reason"] = reason
                row["passed"] = sum(1 for passed, _ in checks.values() if passed)
                row["total"] = len(checks)
                results.append(row)
            return results

        def render_results(results: list[dict], label: str) -> None:
            total_checks = sum(r["total"] for r in results)
            total_passed = sum(r["passed"] for r in results)
            pct = 100 * total_passed / total_checks

            color = "normal" if pct >= 90 else "inverse"
            st.metric(label=label, value=f"{total_passed}/{total_checks} ({pct:.0f}%)")

            # Per-check pass rates
            cols = st.columns(len(CHECK_NAMES))
            for i, name in enumerate(CHECK_NAMES):
                passed = sum(1 for r in results if r[name] == "PASS")
                cols[i].metric(
                    label=name.replace("_", " "),
                    value=f"{passed}/{len(results)}",
                    delta=f"{100*passed/len(results):.0f}%",
                )

            # Results table
            table_cols = ["id", "question", "expected", "strategy"] + CHECK_NAMES
            rows = [{c: r[c] for c in table_cols} for r in results]

            def _style(val):
                if val == "PASS":
                    return "background-color: #d4edda; color: #155724; font-weight: bold"
                if val == "FAIL":
                    return "background-color: #f8d7da; color: #721c24; font-weight: bold"
                return ""

            import pandas as pd
            df = pd.DataFrame(rows)
            styled = df.style.map(_style, subset=CHECK_NAMES)
            st.dataframe(styled, use_container_width=True, hide_index=True)

            # Failure details
            failures = [
                (r["id"], r["question"], name, r[f"{name}_reason"])
                for r in results
                for name in CHECK_NAMES
                if r[name] == "FAIL"
            ]
            if failures:
                with st.expander(f"Failure details ({len(failures)})", expanded=True):
                    for fid, q, check, reason in failures:
                        st.error(f"**[{fid}] {check}** — {reason}")

        try:
            results_a = score_traces(traces_path)
            render_results(results_a, label=traces_path)

            if compare_path.strip():
                st.divider()
                results_b = score_traces(compare_path)
                render_results(results_b, label=compare_path)

                # Improvement banner
                passed_a = sum(r["passed"] for r in results_a)
                total_a = sum(r["total"] for r in results_a)
                passed_b = sum(r["passed"] for r in results_b)
                total_b = sum(r["total"] for r in results_b)
                delta_pp = (passed_b / total_b - passed_a / total_a) * 100

                st.divider()
                st.success(
                    f"**Fix impact:** {passed_a/total_a:.0%} → {passed_b/total_b:.0%} "
                    f"({delta_pp:+.0f} pp)  |  "
                    f"Failures reduced: {total_a - passed_a} → {total_b - passed_b}"
                )

        except FileNotFoundError as exc:
            st.error(f"File not found: {exc}")
        except Exception as exc:
            st.exception(exc)
