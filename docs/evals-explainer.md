# Evals and Traces — What We Did and Why

## The core idea in one sentence

You built a system. Now how do you know it works?

With a web app, you can click around and see if the UI looks right. With an AI system, the output is text — and "does this look right" is subjective and slow. Evals are the automated answer to that question.

---

## The generic process (theory)

Every serious AI team runs some version of this loop:

```
1. COLLECT   — run real queries, save the inputs and outputs
2. LABEL     — read through the outputs and categorise what went wrong
3. ASSERT    — turn those categories into automated pass/fail checks
4. FIX       — change something in the system to address the failures
5. MEASURE   — run the checks again and see if the number went up
```

This is called an **eval loop**. The goal is to turn "I think it's working" into "I have evidence it's working."

The output of step 1 is called a **trace** — a complete record of one request: the input question, every tool the agent called, what those tools returned, and the final answer. You save traces so you can replay and analyse them without re-running the live system.

---

## What we actually did, step by step

### Step 1 — Collect traces (`evals/run_traces.py`)

We wrote a script that sent 20 pre-written questions to the live `/agentic/ask` endpoint and saved every response to `traces.json`.

Each saved trace looks like this:

```json
{
  "id": 13,
  "expected": "answer",
  "question": "What is the difference between compound and isolation exercises?",
  "status": "ok",
  "wall_ms": 4821,
  "response": {
    "strategy": "refused",
    "answer": { "answer": "...", "confidence": 0.95, "sources_needed": false },
    "sources": [],
    "tool_calls": []
  }
}
```

The `expected` field is something we added ourselves — it says what the correct behaviour *should* be for each question. In-scope fitness questions should be answered (`"answer"`). Out-of-scope questions like "who won the World Cup" should be refused (`"refuse"`). This is called a **ground truth label** — the human-decided correct answer that checks compare against.

We collected 20 questions:
- 16 in-scope (nutrition, exercise, supplementation)
- 3 out-of-scope (should be refused)
- 1 edge case (creatine safety dose)

---

### Step 2 — Label failures (open-coding)

We read through the traces and categorised what was going wrong. This is called **open-coding** — you read outputs with fresh eyes and write down the failure types you see.

We found four categories:

| # | Failure type | What it looks like | Example |
|---|---|---|---|
| 1 | **Ungrounded answer** | No tools called, no sources, but confident answer | Q13: answered "compound exercises are..." from memory |
| 2 | **Silent tool miss** | Tools called, returned nothing, answered anyway | Q15/Q20: tools ran but sources=[], answer appeared |
| 3 | **sources_needed contradiction** | Field says false but tools found nothing | Q20: `sources_needed=false` when no sources returned |
| 4 | **Strategy mislabel** | `strategy=refused` but there's a real answer in the response | Q13, Q15: LLM answered but strategy field says refused |

This step is intentionally manual. The point is to understand *why* the system is failing, not just that it is.

---

### Step 3 — Write assertions (`evals/checks.py`)

Each failure category became a Python function that takes a trace and returns `(True/False, reason)`.

```python
def assert_grounded(trace):
    # Skip out-of-scope questions — refusing is correct for those
    if trace.get("expected") == "refuse":
        return True, "out-of-scope — grounding not required"

    # Fail if tools ran but returned nothing and an answer appeared anyway
    if tool_calls and not sources:
        return False, "tools called but sources=[] — ungrounded answer after tool miss"

    # Fail if no tools at all, no sources, but confident answer (answered from memory)
    if not tool_calls and not sources and confidence >= 0.5:
        return False, "answered from training data without grounding"

    return True, "ok"
```

These checks embody your understanding of what the system *should* do. Each one is a testable claim about correct behaviour.

The important thing: **checks are not LLM calls**. They are deterministic code — same input, same output, every time. This makes them fast and cheap to run.

---

### Step 4 — Fix the system

The most common failure was the LLM answering from memory without calling any tools (ungrounded answer). The root cause: the system prompt said *"Answer using ONLY the context provided"* — so when no context was pre-loaded, the LLM just used its training data.

The fix was changing the system prompt to:

> "You MUST call at least one tool before answering any fitness, nutrition, supplementation, or exercise question."

That one instruction changed the agent's behaviour across all in-scope questions.

---

### Step 5 — Measure the improvement

We collected a second set of traces *after* the fix (`traces_after.json`) and ran the same checks on both.

```
Before fix:  72/80 checks passed  (90%)   — 8 failures
After fix:   78/80 checks passed  (98%)   — 2 failures
```

Per-check breakdown:

| Check | Before | After |
|---|---|---|
| grounded | 17/20 | 19/20 |
| sources_needed_consistent | 19/20 | 20/20 |
| no_duplicate_tools | 19/20 | 20/20 |
| strategy_label_accurate | 17/20 | 19/20 |

The 2 remaining failures are both Q20 (creatine 10g safety question) — tools ran but returned empty results, and the LLM answered anyway. That's a real open issue, not a false alarm.

---

## How the generic theory maps to what we built

| Theory term | What it is | What we built |
|---|---|---|
| **Trace** | Saved record of one request+response | Each JSON object in `traces.json` |
| **Ground truth label** | Human-decided correct behaviour | The `expected` field ("answer" / "refuse") |
| **Open-coding** | Reading outputs to find failure patterns | Manual review of traces.json |
| **Failure taxonomy** | Named categories of failures | The 4 check types in checks.py |
| **Assertion / eval check** | Automated pass/fail test | Each function in checks.py |
| **Eval runner** | Runs all checks, reports results | `runner.py`, also the Streamlit Evals tab |
| **Before/after comparison** | Metric movement from a fix | 90% → 98% across traces.json vs traces_after.json |

---

## Why not just use an LLM to judge the outputs?

You can — this is called **LLM-as-judge** and many teams do it. The tradeoff:

| Code-based checks | LLM-as-judge |
|---|---|
| Fast and free to run | Costs tokens every run |
| Deterministic — same answer every time | Can vary between runs |
| Can only check structural properties (did tools run? are sources empty?) | Can check semantic quality ("is this answer factually correct?") |
| Easy to debug when they fail | Hard to know why the judge decided what it did |

For structural failures (the ones we found: no grounding, wrong strategy label, duplicate tools), code-based checks are better. LLM-as-judge is useful for things like "is this answer medically accurate" — which requires understanding content, not just structure.

---

## What this gives you going forward

Every time you change the system, you can:

1. Run `python -m evals.run_traces` to collect fresh traces
2. Run `python -m evals.runner --traces evals/traces_new.json --compare evals/traces_after.json`
3. See immediately if your change helped, hurt, or did nothing

This is how real AI teams prevent regressions. You add features, the eval suite tells you if anything broke.
